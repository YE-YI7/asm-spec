from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from asm_access_extension import derive_access_extension
from experiments.access_signal_shape_audit import audit, load_manifests


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads(
    (ROOT / "schema" / "asm-ai-catalog-access-v0.1.schema.json").read_text(encoding="utf-8")
)


def test_candidate_extension_validates_for_every_library_manifest():
    manifests = load_manifests()
    assert len(manifests) == 30
    for manifest in manifests:
        jsonschema.validate(derive_access_extension(manifest), SCHEMA)


def test_candidate_keeps_every_positive_price_dimension():
    for manifest in load_manifests():
        expected = [
            item
            for item in (manifest.get("pricing") or {}).get("billing_dimensions") or []
            if (item.get("cost_per_unit") or 0) > 0
        ]
        actual = derive_access_extension(manifest)["priceEchoes"]
        assert len(actual) == len(expected), manifest["service_id"]


def test_audit_exposes_free_tier_and_tier_quality_gaps():
    result = audit(load_manifests())
    projection = result["current_projection"]
    findings = result["quality_findings"]

    assert projection["free_tier_marked_count"] == 22
    assert projection["free_tier_detail_string_count"] == 8
    assert projection["machine_readable_free_tier_rule_count"] == 0
    assert findings["known_tier_conflicts"] == ["attom/property-api@current"]

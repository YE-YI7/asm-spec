"""Conformance checks for the proposed DSH Selection Facts contract seam."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import manifest_digest  # noqa: E402
from mcp_server_json_asm import validate_manifest  # noqa: E402
from tools.build_dsh_selection_fixture import (  # noqa: E402
    FIXTURE,
    META_KEY,
    SCHEMA_URI,
    bundle_tree_digest,
    build_fixture,
    load_json,
    render,
)


def test_sidecars_are_valid_asm_v03():
    for path in sorted((FIXTURE / "sidecars").glob("*.json")):
        assert validate_manifest(load_json(path)) == [], path


def test_bundle_metadata_uses_stable_namespaced_sidecar_reference():
    for path in sorted((FIXTURE / "bundles").glob("*/package.json")):
        bundle = load_json(path)
        assert bundle["dsh"]["bundle"]["patch"] == "./cordis.patch.yml"
        assert (path.parent / "cordis.patch.yml").exists()
        assert (path.parent / "index.js").exists()
        ref = bundle["metadata"][META_KEY]
        assert ref["schema_uri"] == SCHEMA_URI
        assert ref["sidecar_locator"].startswith("https://registry.asm.example/")
        assert "digest" not in ref


def test_metadata_update_changes_facts_not_artifact_identity():
    safe_bundle_path = FIXTURE / "bundles" / "search-safe"
    before_artifact = bundle_tree_digest(safe_bundle_path)
    after_artifact = bundle_tree_digest(safe_bundle_path)
    before = load_json(FIXTURE / "sidecars" / "search-safe.selection-facts.json")
    after = load_json(
        FIXTURE / "sidecars" / "search-safe.selection-facts-updated.json"
    )
    assert before["service_id"] == after["service_id"]
    assert before_artifact == after_artifact
    assert manifest_digest(before) != manifest_digest(after)


def test_receipt_pins_candidates_taxonomy_constraints_and_facts():
    receipt, result = build_fixture()
    assert receipt["selected"]["service_id"] == "dsh-fixture/search-safe@1.0.0"
    assert receipt["request"]["taxonomy"] == "tool.research.web"
    assert receipt["request"]["required_functions"] == ["web_search"]
    assert receipt["request"]["require_agent_completable_setup"] is True
    assert receipt["approval_required"] is True
    expected = {
        load_json(path)["service_id"]: manifest_digest(load_json(path))
        for path in [
            FIXTURE / "sidecars" / "search-safe.selection-facts.json",
            FIXTURE / "sidecars" / "search-fast.selection-facts.json",
        ]
    }
    assert {e["service_id"]: e["manifest_digest"] for e in receipt["evidence"]} == expected
    assert result["selection_receipt"]["candidate_set"] == sorted(expected)


def test_receipt_is_audit_only_and_generated_files_are_current():
    receipt, result = build_fixture()
    forbidden = {"signature", "authorization", "execution", "payment_mandate"}
    assert forbidden.isdisjoint(receipt)
    assert result["selection_receipt"]["verification_status"] == "unsigned"
    assert result["selection_receipt"]["authorization"] is False
    assert (FIXTURE / "selection-receipt.json").read_text(encoding="utf-8") == render(receipt)
    assert (FIXTURE / "fixture-result.json").read_text(encoding="utf-8") == render(result)

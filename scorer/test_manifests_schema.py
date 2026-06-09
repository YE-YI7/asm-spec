"""Schema validation: every manifest under manifests/ and library/ must validate against
schema/asm-v0.3.schema.json. This test catches the class of regression where
new manifests use enum values not in the schema (e.g. an invalid
verification_status string).

Run:
    pip install jsonschema pytest
    python -m pytest scorer/test_manifests_schema.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "asm-v0.3.schema.json"
MANIFESTS_DIR = ROOT / "manifests"
LIBRARY_DIR = ROOT / "library"


@pytest.fixture(scope="module")
def schema():
    if jsonschema is None:
        pytest.skip("jsonschema not installed; pip install jsonschema")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def manifest_paths():
    return sorted(MANIFESTS_DIR.glob("*.asm.json")) + sorted(LIBRARY_DIR.rglob("*.asm.json"))


def test_at_least_one_manifest():
    paths = manifest_paths()
    assert len(paths) > 0, "no manifests found under manifests/"


@pytest.mark.parametrize("manifest_path", manifest_paths(), ids=lambda p: p.name)
def test_manifest_validates(manifest_path: Path, schema):
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    jsonschema.validate(document, schema)


def test_no_extra_unknown_versions():
    """Sanity: every manifest declares asm_version 0.3."""
    for path in manifest_paths():
        d = json.loads(path.read_text(encoding="utf-8"))
        assert d.get("asm_version") == "0.3", f"{path.name} declares asm_version={d.get('asm_version')}"

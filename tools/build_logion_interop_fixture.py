"""Build or verify the bounded ASM-Logion interoperability fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import build_selection_receipt, manifest_digest, select

FIXTURE_DIR = ROOT / "examples" / "interop" / "logion"
GENERATED_FILES = ("selection-receipt.json", "source-mapping.json")


def load_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def sha256_bytes(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_outputs() -> dict[str, dict]:
    catalog_entry = load_json("ai-catalog-entry.json")
    manifest = load_json("asm-manifest.json")
    updated_manifest = load_json("asm-manifest-metadata-update.json")
    request = {
        "task": "exercise the deterministic interoperability fixture",
        "taxonomy": manifest["taxonomy"],
        "agent_reach": "cloud",
        "user_platform": "any",
        "required_functions": ["deterministic_echo"],
        "require_approval_for": [],
        "require_agent_completable_setup": True,
    }
    decision = select(
        request["task"],
        taxonomy=request["taxonomy"],
        agent_reach=request["agent_reach"],
        user_platform=request["user_platform"],
        required_functions=request["required_functions"],
        require_approval_for=request["require_approval_for"],
        require_agent_completable_setup=request["require_agent_completable_setup"],
        library=[manifest],
    )
    receipt = build_selection_receipt(
        decision,
        [manifest],
        request=request,
        selection_id="00000000-0000-4000-8000-000000000001",
        issued_at="2026-08-22T00:00:00Z",
    )
    artifact_digest = sha256_bytes(FIXTURE_DIR / "resource-artifact.json")
    base_manifest_digest = manifest_digest(manifest)
    updated_manifest_digest = manifest_digest(updated_manifest)
    mapping = {
        "mapping_version": "0.1",
        "manifest_validator": {
            "package": "asm-protocol",
            "version": "0.5.2",
            "expected_schema_status": "valid",
            "expected_selection_readiness": "ready",
            "expected_manifest_digest": base_manifest_digest,
        },
        "ai_catalog_subject": {
            "identifier": catalog_entry["identifier"],
            "version": catalog_entry["version"],
            "source_revision": "fixture-v1",
        },
        "resource_artifact": {
            "media_type": catalog_entry["type"],
            "digest": artifact_digest,
        },
        "asm_selection_descriptor": {
            "service_id": manifest["service_id"],
            "manifest_digest": base_manifest_digest,
            "metadata_update_manifest_digest": updated_manifest_digest,
        },
        "logion_binding_requirements": {
            "resource_id": None,
            "version_id": None,
            "resource_anchor": {
                "source_protocol": "ai-catalog",
                "identifier": catalog_entry["identifier"],
            },
            "resource_version_anchor": {
                "algorithm": "sha256",
                "digest": artifact_digest,
            },
            "id_assignment_authority": "logion",
        },
        "expected_behavior": {
            "metadata_update_keeps_resource": True,
            "metadata_update_keeps_resource_version": True,
            "metadata_update_changes_selection_evidence": True,
            "selection_receipt_verification_status": "unsigned",
            "usage_observation_shape_changes": False,
        },
    }
    return {
        "selection-receipt.json": receipt,
        "source-mapping.json": mapping,
    }


def render(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated fixture outputs differ from checked-in files",
    )
    args = parser.parse_args(argv)
    outputs = build_outputs()
    stale: list[str] = []
    for name in GENERATED_FILES:
        expected = render(outputs[name])
        target = FIXTURE_DIR / name
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != expected:
                stale.append(name)
        else:
            target.write_text(expected, encoding="utf-8")
            print(f"wrote {target.relative_to(ROOT)}")
    if stale:
        print("stale generated fixture files: " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print("ASM-Logion fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

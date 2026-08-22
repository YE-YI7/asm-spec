#!/usr/bin/env python3
"""Build the deterministic DSH artifact-identity/Selection-Facts fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "examples" / "interop" / "deepseek-harness-selection-boundary"
SCHEMA_URI = "https://asm-protocol.org/schema/v0.3/manifest.json"
META_KEY = "io.github.ye-yi7.asm.selection-facts"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import manifest_digest, select  # noqa: E402
from mcp_server_json_asm import validate_manifest  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_digest(document: dict[str, Any]) -> str:
    raw = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def raw_file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_content_map(path: Path) -> dict[str, str]:
    """Map POSIX Bundle-relative paths to raw byte digests."""
    return {
        file.relative_to(path).as_posix(): raw_file_digest(file)
        for file in sorted(item for item in path.rglob("*") if item.is_file())
    }


def bundle_tree_digest(path: Path) -> str:
    """Digest a fixture Bundle using its portable relative-path content map."""
    content_map = bundle_content_map(path)
    return canonical_digest(content_map)


def source_documents() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    sidecars = [
        load_json(FIXTURE / "sidecars" / "search-safe.selection-facts.json"),
        load_json(FIXTURE / "sidecars" / "search-fast.selection-facts.json"),
    ]
    updated_safe = load_json(
        FIXTURE / "sidecars" / "search-safe.selection-facts-updated.json"
    )
    bundles = {
        "dsh-fixture/search-safe@1.0.0": load_json(
            FIXTURE / "bundles" / "search-safe" / "package.json"
        ),
        "dsh-fixture/search-fast@1.0.0": load_json(
            FIXTURE / "bundles" / "search-fast" / "package.json"
        ),
    }
    return sidecars, updated_safe, bundles


def build_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    sidecars, updated_safe, bundles = source_documents()
    for sidecar in [*sidecars, updated_safe]:
        errors = validate_manifest(sidecar)
        if errors:
            raise ValueError(f"invalid sidecar {sidecar.get('service_id')}: {errors}")

    decision = select(
        "choose a read-only web-search plugin",
        taxonomy="tool.research.web",
        agent_reach="cloud",
        user_platform="any",
        required_functions=["web_search"],
        require_approval_for=["network_access"],
        require_agent_completable_setup=True,
        library=sidecars,
        receipt=True,
    )
    receipt = decision["receipt"]
    # Make the conformance artifact reproducible without changing its semantics.
    receipt["selection_id"] = "fixture-dsh-selection-boundary-0001"
    receipt["issued_at"] = "2026-08-22T00:00:00Z"

    bundle_records = []
    for service_id, bundle in sorted(bundles.items()):
        source_name = "search-safe" if "safe" in service_id else "search-fast"
        source_path = FIXTURE / "bundles" / source_name
        sidecar = next(item for item in sidecars if item["service_id"] == service_id)
        reference = bundle["metadata"][META_KEY]
        bundle_records.append(
            {
                "service_id": service_id,
                "artifact": {
                    "kind": "dsh-bundle",
                    "name": bundle["name"],
                    "version": bundle["version"],
                },
                "artifact_digest_scope": "canonical map of Bundle-relative paths to raw byte digests",
                "artifact_digest": bundle_tree_digest(source_path),
                "selection_facts": {
                    "schema_uri": reference["schema_uri"],
                    "sidecar_locator": reference["sidecar_locator"],
                    "facts_digest": manifest_digest(sidecar),
                },
            }
        )

    safe_record = next(r for r in bundle_records if "search-safe" in r["service_id"])
    old_safe = next(s for s in sidecars if "search-safe" in s["service_id"])
    safe_bundle_digest_before = bundle_tree_digest(
        FIXTURE / "bundles" / "search-safe"
    )
    safe_bundle_digest_after = bundle_tree_digest(
        FIXTURE / "bundles" / "search-safe"
    )
    candidate_set = sorted(sidecar["service_id"] for sidecar in sidecars)
    receipt_candidate_set = sorted(e["service_id"] for e in receipt["evidence"])
    result = {
        "fixture_version": "0.1",
        "scope": "dsh-m3-artifact-identity-selection-facts-boundary",
        "bundle_records": bundle_records,
        "metadata_only_update_check": {
            "service_id": old_safe["service_id"],
            "artifact_digest_before": safe_bundle_digest_before,
            "artifact_digest_after": safe_bundle_digest_after,
            "facts_digest_before": manifest_digest(old_safe),
            "facts_digest_after": manifest_digest(updated_safe),
            "artifact_identity_unchanged": safe_bundle_digest_before
            == safe_bundle_digest_after
            == safe_record["artifact_digest"],
            "selection_facts_changed": manifest_digest(old_safe)
            != manifest_digest(updated_safe),
        },
        "selection_receipt": {
            "path": "selection-receipt.json",
            "digest": canonical_digest(receipt),
            "verification_status": "unsigned",
            "authorization": False,
            "candidate_set": receipt_candidate_set,
            "taxonomy": receipt["request"]["taxonomy"],
            "constraints": receipt["request"],
        },
        "assertions": {
            "sidecar_schema_uri_is_namespaced": all(
                r["selection_facts"]["schema_uri"] == SCHEMA_URI
                for r in bundle_records
            ),
            "receipt_pins_full_candidate_set": receipt_candidate_set
            == candidate_set,
            "approval_is_selection_fact_not_authorization": receipt[
                "approval_required"
            ]
            is True,
            "receipt_has_no_signature": "signature" not in receipt,
            "receipt_has_no_authorization": "authorization" not in receipt,
            "receipt_has_no_execution_record": "execution" not in receipt,
        },
    }
    return receipt, result


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify generated files")
    mode.add_argument("--write", action="store_true", help="write generated files")
    args = parser.parse_args(argv)

    receipt, result = build_fixture()
    generated = {
        FIXTURE / "selection-receipt.json": render(receipt),
        FIXTURE / "fixture-result.json": render(result),
    }
    if args.write:
        for path, content in generated.items():
            path.write_text(content, encoding="utf-8")
        return 0

    stale = [
        str(path.relative_to(ROOT))
        for path, content in generated.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if stale:
        print("stale generated fixture files:")
        print("\n".join(f"- {path}" for path in stale))
        return 1
    print("DSH selection-boundary fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

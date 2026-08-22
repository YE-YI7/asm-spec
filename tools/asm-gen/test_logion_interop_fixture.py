"""Contract tests for the bounded ASM-Logion interoperability fixture."""

from __future__ import annotations

import json

from mcp_server_json_asm import validate_manifest
from tools.build_logion_interop_fixture import FIXTURE_DIR, build_outputs, sha256_bytes


def load_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_manifests_are_schema_valid() -> None:
    assert validate_manifest(load_json("asm-manifest.json")) == []
    assert validate_manifest(load_json("asm-manifest-metadata-update.json")) == []


def test_generated_outputs_are_current() -> None:
    expected = build_outputs()
    for name, document in expected.items():
        assert load_json(name) == document


def test_resource_and_selection_digests_have_separate_authority() -> None:
    mapping = load_json("source-mapping.json")
    descriptor = mapping["asm_selection_descriptor"]
    artifact_digest = sha256_bytes(FIXTURE_DIR / "resource-artifact.json")

    assert descriptor["manifest_digest"] != descriptor["metadata_update_manifest_digest"]
    assert mapping["resource_artifact"]["digest"] == artifact_digest
    binding = mapping["logion_binding_requirements"]
    assert binding["resource_id"] is None and binding["version_id"] is None
    assert binding["resource_version_anchor"] == {
        "algorithm": "sha256",
        "digest": artifact_digest,
    }
    assert binding["id_assignment_authority"] == "logion"
    assert mapping["expected_behavior"] == {
        "metadata_update_keeps_resource": True,
        "metadata_update_keeps_resource_version": True,
        "metadata_update_changes_selection_evidence": True,
        "selection_receipt_verification_status": "unsigned",
        "usage_observation_shape_changes": False,
    }


def test_selection_receipt_is_explicitly_unsigned_and_selection_only() -> None:
    receipt = load_json("selection-receipt.json")

    assert receipt["verification_status"] == "unsigned"
    assert receipt["selector"]["name"] == "asm-protocol/0.5.3"
    assert receipt["evidence"] == [
        {
            "service_id": load_json("asm-manifest.json")["service_id"],
            "manifest_digest": load_json("source-mapping.json")[
                "asm_selection_descriptor"
            ]["manifest_digest"],
        }
    ]
    assert not ({"execution", "payment", "authorization"} & receipt.keys())
    assert "issuer" not in receipt


def test_catalog_identity_is_stable_while_asm_service_id_is_an_alias() -> None:
    catalog_entry = load_json("ai-catalog-entry.json")
    mapping = load_json("source-mapping.json")
    manifest = load_json("asm-manifest.json")

    assert mapping["ai_catalog_subject"] == {
        "identifier": catalog_entry["identifier"],
        "version": catalog_entry["version"],
        "source_revision": "fixture-v1",
    }
    assert mapping["logion_binding_requirements"]["resource_anchor"] == {
        "source_protocol": "ai-catalog",
        "identifier": catalog_entry["identifier"],
    }
    assert mapping["asm_selection_descriptor"]["service_id"] == manifest["service_id"]


def test_public_052_validator_contract_is_separate_from_receipt_generator() -> None:
    mapping = load_json("source-mapping.json")

    assert mapping["manifest_validator"] == {
        "package": "asm-protocol",
        "version": "0.5.2",
        "expected_schema_status": "valid",
        "expected_selection_readiness": "ready",
        "expected_manifest_digest": mapping["asm_selection_descriptor"][
            "manifest_digest"
        ],
    }

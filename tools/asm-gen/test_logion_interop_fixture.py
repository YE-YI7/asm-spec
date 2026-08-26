"""Contract tests for the bounded ASM-Logion interoperability fixture."""

from __future__ import annotations

import json
import re
from copy import deepcopy

from jsonschema import Draft202012Validator

from library_select import ASM_JSON_CANONICALIZATION, HASH_ALGORITHM, document_digest
from mcp_server_json_asm import validate_manifest
from tools.build_logion_interop_fixture import (
    FIXTURE_DIR,
    ROOT,
    build_outputs,
    build_receipt,
    sha256_bytes,
)


def load_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_manifests_are_schema_valid() -> None:
    assert validate_manifest(load_json("asm-manifest.json")) == []
    assert validate_manifest(load_json("asm-manifest-metadata-update.json")) == []


def test_ai_catalog_document_has_one_stable_fixture_subject() -> None:
    catalog = load_json("ai-catalog.json")

    assert catalog["specVersion"] == "1.0"
    assert len(catalog["entries"]) == 1
    entry = catalog["entries"][0]
    assert re.fullmatch(
        r"urn:air:[a-zA-Z0-9.-]+(?::[a-zA-Z0-9._-]+)+",
        entry["identifier"],
    )
    assert entry["version"] == "1.0.0"
    assert entry["url"].startswith("https://asm-logion.example/")


def test_generated_outputs_are_current() -> None:
    expected = build_outputs()
    for name, document in expected.items():
        assert load_json(name) == document


def test_selection_receipts_match_the_machine_schema() -> None:
    schema = json.loads(
        (ROOT / "schema" / "selection-receipt-v0.2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(load_json("selection-receipt.json"))) == []
    assert list(
        validator.iter_errors(
            json.loads(
                (ROOT / "examples" / "receipts" / "selection-receipt.json").read_text(
                    encoding="utf-8"
                )
            )
        )
    ) == []


def test_schema_rejects_fabricated_attestation_fields() -> None:
    schema = json.loads(
        (ROOT / "schema" / "selection-receipt-v0.2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    receipt = load_json("selection-receipt.json")

    claimed_verified = deepcopy(receipt)
    claimed_verified["verification_status"] = "verified"
    assert list(validator.iter_errors(claimed_verified))

    invented_issuer = deepcopy(receipt)
    invented_issuer["issuer"] = "did:example:not-verified"
    assert list(validator.iter_errors(invented_issuer))

    unlabeled_digest = deepcopy(receipt)
    del unlabeled_digest["evidence"][0]["canonicalization"]
    assert list(validator.iter_errors(unlabeled_digest))


def test_resource_and_selection_digests_have_separate_authority() -> None:
    mapping = load_json("source-mapping.json")
    descriptor = mapping["asm_selection_descriptor"]
    artifact_digest = sha256_bytes(FIXTURE_DIR / "resource-artifact.json")

    assert descriptor["manifest_digest"] != descriptor["metadata_update_manifest_digest"]
    assert descriptor["hash_algorithm"] == HASH_ALGORITHM
    assert descriptor["canonicalization"] == ASM_JSON_CANONICALIZATION
    assert mapping["resource_artifact"]["digest"] == artifact_digest
    assert mapping["resource_artifact"]["hash_algorithm"] == HASH_ALGORITHM
    assert mapping["resource_artifact"]["digest_input"] == "raw-bytes"
    binding = mapping["logion_binding_requirements"]
    assert binding["resource_id"] is None and binding["version_id"] is None
    assert binding["resource_version_anchor"] == {
        "digest_algorithm": HASH_ALGORITHM,
        "digest_input": "raw-bytes",
        "digest": artifact_digest,
        "media_type": "application/json",
    }
    assert binding["id_assignment_authority"] == "logion"
    assert mapping["asm_verified_behavior"] == {
        "metadata_update_keeps_artifact_digest": True,
        "metadata_update_changes_selection_evidence": True,
        "selection_receipt_verification_status": "unsigned",
    }
    assert mapping["logion_verification"]["status"] == "pending"


def test_metadata_update_changes_receipt_evidence_not_resource_artifact() -> None:
    mapping = load_json("source-mapping.json")
    updated_receipt = build_receipt(
        load_json("asm-manifest-metadata-update.json"),
        selection_id="00000000-0000-4000-8000-000000000002",
        issued_at="2026-08-22T01:00:00Z",
    )

    assert updated_receipt["evidence"] == [
        {
            "service_id": mapping["asm_selection_descriptor"]["service_id"],
            "hash_algorithm": HASH_ALGORITHM,
            "canonicalization": ASM_JSON_CANONICALIZATION,
            "manifest_digest": mapping["asm_selection_descriptor"][
                "metadata_update_manifest_digest"
            ],
        }
    ]
    assert mapping["resource_artifact"]["digest"] == sha256_bytes(
        FIXTURE_DIR / "resource-artifact.json"
    )


def test_selection_receipt_is_explicitly_unsigned_and_selection_only() -> None:
    receipt = load_json("selection-receipt.json")

    assert receipt["verification_status"] == "unsigned"
    assert receipt["selector"]["name"] == "asm-protocol/0.5.3"
    assert receipt["evidence"] == [
        {
            "service_id": load_json("asm-manifest.json")["service_id"],
            "hash_algorithm": HASH_ALGORITHM,
            "canonicalization": ASM_JSON_CANONICALIZATION,
            "manifest_digest": load_json("source-mapping.json")[
                "asm_selection_descriptor"
            ]["manifest_digest"],
        }
    ]
    assert not ({"execution", "payment", "authorization"} & receipt.keys())
    assert "issuer" not in receipt
    receipt_artifact = load_json("source-mapping.json")["selection_receipt_artifact"]
    assert receipt_artifact == {
        "receipt_type": "selection",
        "receipt_version": "0.2",
        "verification_status": "unsigned",
        "hash_algorithm": HASH_ALGORITHM,
        "canonicalization": ASM_JSON_CANONICALIZATION,
        "digest": document_digest(receipt),
    }


def test_catalog_identity_is_stable_while_asm_service_id_is_an_alias() -> None:
    catalog = load_json("ai-catalog.json")
    catalog_entry = catalog["entries"][0]
    mapping = load_json("source-mapping.json")
    manifest = load_json("asm-manifest.json")

    assert mapping["ai_catalog_subject"] == {
        "catalog_uri": "https://asm-logion.example/.well-known/ai-catalog.json",
        "identifier": catalog_entry["identifier"],
        "version": catalog_entry["version"],
        "source_revision": "fixture-v1",
    }
    assert mapping["logion_binding_requirements"]["resource_source"] == {
        "source_kind": "ai-catalog",
        "source_uri": "https://asm-logion.example/.well-known/ai-catalog.json",
        "external_id": catalog_entry["identifier"],
    }
    assert mapping["asm_selection_descriptor"]["service_id"] == manifest["service_id"]


def test_public_052_validator_contract_is_separate_from_receipt_generator() -> None:
    mapping = load_json("source-mapping.json")

    assert mapping["manifest_validator"] == {
        "package": "asm-protocol",
        "version": "0.5.2",
        "expected_schema_status": "valid",
        "expected_selection_readiness": "ready",
        "expected_hash_algorithm": HASH_ALGORITHM,
        "expected_canonicalization": ASM_JSON_CANONICALIZATION,
        "expected_manifest_digest": mapping["asm_selection_descriptor"][
            "manifest_digest"
        ],
    }
    assert mapping["protocol_basis"] == {
        "ai_catalog_spec_version": "1.0",
        "ai_catalog_commit": "28825483143ce9f3b344ed01dc2771d4adf02d01",
        "ard_schema_commit": "5fa2f5aef790b478319f6a3b43adf4661b0ed0e0",
    }

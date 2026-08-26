from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from library_select import load_library, select


ROOT = Path(__file__).resolve().parents[2]
V01_SCHEMA = json.loads(
    (ROOT / "schema" / "selection-receipt-v0.1.schema.json").read_text(
        encoding="utf-8"
    )
)
V02_SCHEMA = json.loads(
    (ROOT / "schema" / "selection-receipt-v0.2.schema.json").read_text(
        encoding="utf-8"
    )
)
RECEIPT = json.loads(
    (
        ROOT
        / "examples"
        / "interop"
        / "deepseek-harness-selection-boundary"
        / "selection-receipt.json"
    ).read_text(encoding="utf-8")
)
PUBLIC_RECEIPT = json.loads(
    (ROOT / "examples" / "receipts" / "selection-receipt.json").read_text(
        encoding="utf-8"
    )
)
V01_VALIDATOR = Draft202012Validator(V01_SCHEMA)
V02_VALIDATOR = Draft202012Validator(V02_SCHEMA)


def test_v01_schema_is_frozen_and_accepts_deepseek_fixture() -> None:
    Draft202012Validator.check_schema(V01_SCHEMA)
    V01_VALIDATOR.validate(RECEIPT)
    schema_bytes = (
        ROOT / "schema" / "selection-receipt-v0.1.schema.json"
    ).read_bytes()
    assert hashlib.sha256(schema_bytes).hexdigest() == (
        "d84c3688c136c685eaedfd4cffbbde06616becdbc1588f8449f9bdf24a73bae9"
    )


def test_v02_schema_accepts_public_generated_example() -> None:
    Draft202012Validator.check_schema(V02_SCHEMA)
    V02_VALIDATOR.validate(PUBLIC_RECEIPT)


@pytest.mark.parametrize(
    "taxonomy",
    sorted({manifest.get("taxonomy") for manifest in load_library()}) + [None],
)
def test_selection_receipt_schema_accepts_live_producer_receipts(
    taxonomy: str | None,
) -> None:
    decision = select(
        "schema conformance probe",
        taxonomy=taxonomy,
        agent_reach="cloud",
        user_platform="any",
        receipt=True,
    )
    V02_VALIDATOR.validate(decision["receipt"])


def test_selection_receipt_schema_accepts_no_eligible_decision() -> None:
    receipt = copy.deepcopy(PUBLIC_RECEIPT)
    receipt["selected"] = None
    receipt["selection_reason"] = "no eligible tool"
    receipt["risk_class"] = None
    receipt["approval_required"] = None
    receipt["side_effects"] = []
    receipt["alternatives"] = []
    V02_VALIDATOR.validate(receipt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("receipt_type", "execution"),
        ("receipt_version", "0.3"),
        ("selection_id", "not-a-uuid"),
        ("issued_at", "2026-08-22T00:00:00+00:00"),
        ("approval_required", "yes"),
    ],
)
def test_selection_receipt_schema_rejects_invalid_contract_fields(
    field: str, value: object
) -> None:
    receipt = copy.deepcopy(PUBLIC_RECEIPT)
    receipt[field] = value
    assert list(V02_VALIDATOR.iter_errors(receipt))


def test_selection_receipt_schema_rejects_unknown_authorization_field() -> None:
    receipt = copy.deepcopy(PUBLIC_RECEIPT)
    receipt["authorization"] = True
    assert list(V02_VALIDATOR.iter_errors(receipt))


@pytest.mark.parametrize("container", ["request", "selected"])
def test_v02_preserves_closed_v01_nested_objects(container: str) -> None:
    receipt = copy.deepcopy(PUBLIC_RECEIPT)
    receipt[container]["unexpected"] = True
    assert list(V02_VALIDATOR.iter_errors(receipt))


def test_v02_requires_evidence_for_a_selected_service() -> None:
    receipt = copy.deepcopy(PUBLIC_RECEIPT)
    receipt["evidence"] = []
    assert list(V02_VALIDATOR.iter_errors(receipt))

    receipt["selected"] = None
    receipt["risk_class"] = None
    receipt["approval_required"] = None
    V02_VALIDATOR.validate(receipt)


def test_v01_and_v02_are_explicitly_distinct_contracts() -> None:
    assert list(V01_VALIDATOR.iter_errors(PUBLIC_RECEIPT))
    assert list(V02_VALIDATOR.iter_errors(RECEIPT))

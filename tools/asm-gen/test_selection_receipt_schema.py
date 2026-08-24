from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from library_select import load_library, select


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "schema" / "selection-receipt-v0.1.schema.json").read_text(
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
VALIDATOR = Draft202012Validator(SCHEMA)


def test_selection_receipt_schema_is_valid_and_accepts_fixture() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    VALIDATOR.validate(RECEIPT)


def test_selection_receipt_schema_accepts_public_generated_example() -> None:
    VALIDATOR.validate(PUBLIC_RECEIPT)


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
    VALIDATOR.validate(decision["receipt"])


def test_selection_receipt_schema_accepts_no_eligible_decision() -> None:
    receipt = copy.deepcopy(RECEIPT)
    receipt["selected"] = None
    receipt["selection_reason"] = "no eligible tool"
    receipt["risk_class"] = None
    receipt["approval_required"] = None
    receipt["side_effects"] = []
    receipt["alternatives"] = []
    VALIDATOR.validate(receipt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("receipt_type", "execution"),
        ("receipt_version", "0.2"),
        ("approval_required", "yes"),
    ],
)
def test_selection_receipt_schema_rejects_invalid_contract_fields(
    field: str, value: object
) -> None:
    receipt = copy.deepcopy(RECEIPT)
    receipt[field] = value
    assert list(VALIDATOR.iter_errors(receipt))


def test_selection_receipt_schema_rejects_unknown_authorization_field() -> None:
    receipt = copy.deepcopy(RECEIPT)
    receipt["authorization"] = True
    assert list(VALIDATOR.iter_errors(receipt))

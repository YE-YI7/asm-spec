from __future__ import annotations

from tools.build_vibes_coded_access_fixture import FIXTURE, build_fixture, render
from tools.validate_access_extension import validation_errors


def test_vibes_coded_fixture_matches_pinned_source_observation() -> None:
    document = build_fixture()
    assert document["mechanisms"] == ["x402", "prepaid-key", "day-pass"]
    assert document["pricingResolver"]["authRequired"] is False
    assert document["priceEchoes"][0]["scope"] == "/api/v1/outcomes/action-receipt"
    assert document["priceEchoes"][1]["unit"] == "per_24_hours"
    assert document["freeTierRules"][0]["limit"] == 0.15
    assert "contentDigest" not in document["source"]


def test_vibes_coded_fixture_validates_against_candidate_schema() -> None:
    assert validation_errors(build_fixture()) == []


def test_vibes_coded_fixture_excludes_runtime_payment_and_secret_fields() -> None:
    serialized = render(build_fixture()).lower()
    for forbidden in ("accepts", "payment-signature", "wallet", "settlement", "token_value"):
        assert forbidden not in serialized


def test_vibes_coded_generated_document_is_current() -> None:
    path = FIXTURE / "vibes-coded-access.example.json"
    assert path.read_text(encoding="utf-8") == render(build_fixture())

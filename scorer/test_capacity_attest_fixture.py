from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "examples" / "interop" / "capacity-attest-outcome-linkage"


def test_capacity_attest_linkage_is_reference_only_and_honest() -> None:
    fixture = json.loads((FIXTURE_DIR / "linkage.fixture.json").read_text(encoding="utf-8"))

    assert fixture["status"] == "interop_verification_only"
    assert fixture["historical_asm_use"] is False
    assert fixture["producer"]["name"] == "capacity-attest"
    assert "/holistis/tokenizen/85c8fc1f" in fixture["external_attestation"]["raw_claim_url"]
    assert fixture["external_attestation"]["verifier"] == {
        "package": "capacity-attest",
        "version": "0.2.0",
        "import": "capacity-attest/dist/signing.js",
        "function": "verifyClaim",
    }
    assert fixture["asm_mapping"]["chain_order"] == [
        "DecisionReceipt",
        "OutcomeReceipt",
        "external_attestation_reference",
    ]
    assert "historical use of ASM for the paid call" in fixture["not_independently_proven"]
    assert not (FIXTURE_DIR / "claims.jsonl").exists()

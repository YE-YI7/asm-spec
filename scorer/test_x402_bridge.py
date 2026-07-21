"""Tests for the ASM x402 bridge demo (integrations/x402)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "integrations" / "x402"))

import asm_x402_bridge as bridge  # noqa: E402


def test_amount_encoding_roundtrips_usdc_6dp():
    assert bridge.atomic(0.01) == "10000"
    assert bridge.usd("5000") == 0.005


def test_402_shape_is_spec_accurate():
    o = bridge.CATALOG[1]
    assert o["x402Version"] == 2
    pr = o["accepts"][0]
    assert pr["scheme"] == "exact" and pr["network"] == "eip155:84532"
    assert pr["asset"] == bridge.USDC_BASE_SEPOLIA
    assert "asm" in o["extensions"] and "bazaar" in o["extensions"]


def test_negotiated_has_no_payable_rail():
    neg = next(o for o in bridge.CATALOG if "mlsonly" in o["resource"]["url"])
    assert bridge.price_of(neg) is None


def test_cheapest_wins_would_violate_governance():
    naive = bridge.naive_cheapest(bridge.CATALOG)
    assert "cheapcrypto" in naive["resource"]["url"]
    why = bridge.eligibility(naive, budget_usd=0.02, forbid_training=True, autonomous=True)
    assert why and "trains on user data" in why


def test_asm_selects_eligible_best_value():
    res = bridge.select(bridge.CATALOG, budget_usd=0.02, forbid_training=True, autonomous=True)
    win = res["kept"][0][0]
    assert "datapro" in win["resource"]["url"]
    reasons = {bridge.name(o): why for o, why in res["rejected"]}
    assert "cheapcrypto.example" in reasons and "premiumfeed.example" in reasons
    assert "mlsonly.example" in reasons


def test_payment_payload_is_labelled_mock():
    win = bridge.CATALOG[1]
    p = bridge.build_x_payment(win)
    assert p["network"] == "eip155:84532"
    assert "MOCK" in p["payload"]["note"]

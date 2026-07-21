#!/usr/bin/env python3
"""ASM × x402 bridge — the "which to buy" layer above x402's "how to pay".

x402 (and its `bazaar` discovery extension) tells an agent the PRICE of an
endpoint and HOW to call it. It does not tell the agent which of several
substitutable paid endpoints to choose. Cheapest-wins is the naive default,
and it walks straight into two failures this demo makes concrete:

  1. the cheapest tool violates a hard user constraint (e.g. trains on the
     user's query data), which price alone can't see;
  2. an autonomous agent picks a `negotiated` tool it can never actually
     transact with — the select-then-402 dead end.

ASM rides the SAME extension surface x402 already exposes: value/selection
metadata travels in the 402 response's open `extensions.asm` object, next to
`extensions.bazaar`. The agent reads price from `accepts` and value from
`extensions.asm`, gates on eligibility, then ranks — and only then pays.

Self-contained: the 402 responses below are spec-accurate v2 shapes (atomic
USDC amounts, `eip155:84532` = Base Sepolia testnet, USDC asset), so this runs
with no network and no real funds. The settlement step is a clearly-labelled
testnet-shaped mock — it constructs the X-PAYMENT payload but does not submit.
"""
from __future__ import annotations

import json

USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
NETWORK = "eip155:84532"  # Base Sepolia testnet — no real money
USDC_DECIMALS = 6


def usd(atomic: str) -> float:
    return int(atomic) / 10**USDC_DECIMALS


def atomic(dollars: float) -> str:
    return str(int(round(dollars * 10**USDC_DECIMALS)))


def _402(url, desc, dollars, asm, bazaar_input, *, tier="paid"):
    """Build a spec-accurate x402 v2 PaymentRequired with an asm extension."""
    accepts = []
    if tier != "negotiated":
        accepts.append({
            "scheme": "exact", "network": NETWORK, "amount": atomic(dollars),
            "asset": USDC_BASE_SEPOLIA, "payTo": "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
            "maxTimeoutSeconds": 60, "extra": {"name": "USDC", "version": "2"},
        })
    return {
        "x402Version": 2,
        "error": "Payment required",
        "resource": {"url": url, "description": desc, "mimeType": "application/json"},
        "accepts": accepts,
        "extensions": {
            "bazaar": {"info": {"input": bazaar_input,
                                "output": {"type": "json", "example": {"price_usd": 0}}}},
            # ASM value/selection block — the layer x402 doesn't carry
            "asm": asm,
        },
    }


# --- a Bazaar-style catalog of three substitutable BTC-price endpoints -------
CATALOG = [
    _402("https://cheapcrypto.example/btc", "Spot BTC price", 0.005,
         asm={"taxonomy": "tool.data.market", "quality_score": 0.62,
              "data_governance": {"trains_on_user_data": "yes"},
              "risk_class": "low", "approval": "never"},
         bazaar_input={"type": "http", "method": "GET", "queryParams": {"symbol": "BTC"}}),
    _402("https://datapro.example/v1/price", "Spot BTC price, audited feed", 0.01,
         asm={"taxonomy": "tool.data.market", "quality_score": 0.88,
              "data_governance": {"trains_on_user_data": "no"},
              "risk_class": "low", "approval": "never"},
         bazaar_input={"type": "http", "method": "GET", "queryParams": {"symbol": "BTC"}}),
    _402("https://premiumfeed.example/quote", "Institutional BTC quote", 0.03,
         asm={"taxonomy": "tool.data.market", "quality_score": 0.95,
              "data_governance": {"trains_on_user_data": "no"},
              "risk_class": "low", "approval": "never"},
         bazaar_input={"type": "http", "method": "GET", "queryParams": {"symbol": "BTC"}}),
    _402("https://mlsonly.example/btc", "BTC via enterprise data agreement", 0.0,
         asm={"taxonomy": "tool.data.market", "quality_score": 0.90,
              "data_governance": {"trains_on_user_data": "no"},
              "risk_class": "low", "approval": "never"},
         bazaar_input={"type": "http", "method": "GET", "queryParams": {"symbol": "BTC"}},
         tier="negotiated"),
]


def price_of(offer: dict) -> float | None:
    """Lowest USD price across accepted rails, or None if not self-serve payable."""
    prices = [usd(a["amount"]) for a in offer.get("accepts", []) if a.get("scheme") == "exact"]
    return min(prices) if prices else None


def eligibility(offer: dict, *, budget_usd: float, forbid_training: bool,
                autonomous: bool) -> str | None:
    """None if eligible, else a nameable rejection reason (the gate x402 lacks)."""
    asm = offer["extensions"]["asm"]
    price = price_of(offer)
    if price is None:
        return "not self-serve payable (negotiated) — autonomous agent can't transact" \
            if autonomous else None
    if price > budget_usd:
        return f"price ${price:.3f} exceeds budget ${budget_usd:.3f}"
    if forbid_training and (asm.get("data_governance") or {}).get("trains_on_user_data") != "no":
        return "trains on user data (governance constraint)"
    if asm.get("approval") == "always":
        return "requires human approval before invocation"
    return None


def select(catalog, **gates) -> dict:
    kept, rejected = [], []
    for o in catalog:
        why = eligibility(o, **gates)
        (rejected if why else kept).append((o, why))
    # rank survivors: quality first, then cheapest
    kept.sort(key=lambda ow: (-ow[0]["extensions"]["asm"]["quality_score"], price_of(ow[0])))
    return {"kept": kept, "rejected": rejected}


def naive_cheapest(catalog) -> dict:
    payable = [o for o in catalog if price_of(o) is not None]
    return min(payable, key=price_of)


def build_x_payment(offer: dict) -> dict:
    """Testnet-shaped X-PAYMENT payload (MOCK — constructed, not submitted)."""
    pr = next(a for a in offer["accepts"] if a["scheme"] == "exact")
    return {"x402Version": 2, "scheme": "exact", "network": pr["network"],
            "payload": {"asset": pr["asset"], "amount": pr["amount"], "payTo": pr["payTo"],
                        "note": "MOCK testnet payload — not signed, not submitted"}}


def name(o: dict) -> str:
    return o["resource"]["url"].split("//")[1].split("/")[0]


def main() -> None:
    gates = dict(budget_usd=0.02, forbid_training=True, autonomous=True)
    print("Task: fetch current BTC price for an autonomous trading bot")
    print(f"Constraints: budget ${gates['budget_usd']}/call · must not train on my data · "
          "autonomous (no sales motion)\n")

    print("Discovered x402 endpoints (price from `accepts`, value from `extensions.asm`):")
    for o in CATALOG:
        p = price_of(o)
        a = o["extensions"]["asm"]
        print(f"  {name(o):24} {'$%.3f'%p if p is not None else 'negotiated':>10}  "
              f"quality={a['quality_score']}  "
              f"trains_on_data={(a['data_governance']).get('trains_on_user_data')}")

    naive = naive_cheapest(CATALOG)
    print(f"\n[x402 alone / cheapest-wins] -> {name(naive)} at ${price_of(naive):.3f}")
    nafail = eligibility(naive, **gates)
    print(f"   but ASM gate says: {nafail}  <-- price alone can't see this" if nafail
          else "   (eligible)")

    res = select(CATALOG, **gates)
    win = res["kept"][0][0]
    print(f"\n[ASM value-aware select] -> {name(win)} at ${price_of(win):.3f} "
          f"(quality {win['extensions']['asm']['quality_score']})")
    print("   rejected:")
    for o, why in res["rejected"]:
        print(f"     {name(o):24} {why}")

    print(f"\nOnly now construct payment for the chosen tool:")
    print("   " + json.dumps(build_x_payment(win)))
    print("\nResult: cheapest-wins would have paid a tool that trains on the user's data; "
          "ASM gated it out and paid the eligible best-value tool instead.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the source-linked Vibes-Coded access-signal review fixture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "examples" / "interop" / "vibes-coded-access-signals"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build_fixture() -> dict[str, Any]:
    observation = load_json(FIXTURE / "source-observation.json")
    source = observation["source"]
    facts = observation["facts"]
    mechanisms = facts["mechanisms"]
    if mechanisms != ["x402", "prepaid-key", "day-pass"]:
        raise ValueError("fixture expects the three provider-confirmation candidates")

    action_receipt = facts["action_receipt"]
    day_pass = facts["day_pass"]
    trial = facts["prepaid_trial"]
    return {
        "version": "0.1",
        "tier": "freemium",
        "mechanisms": mechanisms,
        "pricingUrl": facts["pricing_url"],
        "pricingResolver": {
            "url": facts["live_terms_url"],
            "type": "http",
            "authRequired": False,
        },
        "priceEchoes": [
            {
                "dimension": "action_receipt_call",
                "unit": "per_call",
                "amount": action_receipt["price_usd"],
                "currency": "USD",
                "asOf": source["retrieved_at"],
                "scope": action_receipt["path"],
            },
            {
                "dimension": "day_pass",
                "unit": "per_24_hours",
                "amount": day_pass["price_usd"],
                "currency": "USD",
                "asOf": source["retrieved_at"],
                "scope": day_pass["scope"],
            },
        ],
        "freeTierRules": [
            {
                "dimension": "prepaid_credit_usd",
                "limit": trial["grant_cents"] / 100,
                "period": "per_claim",
                "reset": (
                    f"expires after {trial['ttl_hours']} hours; "
                    f"claim cooldown {trial['cooldown_days']} days"
                ),
                "scope": f"prepaid trial via {trial['header']}",
            }
        ],
        "source": {
            "url": source["url"],
            "retrievedAt": source["retrieved_at"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    path = FIXTURE / "vibes-coded-access.example.json"
    expected = render(build_fixture())
    if args.write:
        path.write_text(expected, encoding="utf-8")
        return 0
    if not path.exists() or path.read_text(encoding="utf-8") != expected:
        print(f"stale generated fixture: {path.relative_to(ROOT)}")
        return 1
    print("Vibes-Coded access-signal fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

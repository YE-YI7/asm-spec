#!/usr/bin/env python3
"""Audit the 30-tool library against the ai-catalog#83 access shape.

The output is deterministic and derived only from committed manifests.  Text
review candidates are explicitly heuristic and are not counted as verified
caller-specific contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asm_access_extension import derive_access_extension, infer_access_tier


LIBRARY = ROOT / "library"
RESOLVER_HINT = re.compile(
    r"pricing via sales|pricing varies|model-dependent|tier-dependent|"
    r"quota/pricing depends|limits? .* vary|per-key rate limits",
    re.IGNORECASE,
)


def load_manifests() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(LIBRARY.rglob("*.asm.json"))
    ]


def audit(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = Counter(infer_access_tier(item) for item in manifests)
    free_marked = []
    free_detail_strings = []
    structured_free_rules = []
    multi_price = []
    resolver_candidates = []
    tier_conflicts = []

    for manifest in manifests:
        service_id = manifest["service_id"]
        pricing = manifest.get("pricing") or {}
        payment = manifest.get("payment") or {}
        provenance = manifest.get("provenance") or {}
        methods = payment.get("methods") or []
        positive = [
            item
            for item in pricing.get("billing_dimensions") or []
            if (item.get("cost_per_unit") or 0) > 0
        ]
        free_tier = pricing.get("free_tier")

        if "free_tier" in methods:
            free_marked.append(service_id)
        if isinstance(free_tier, str) and free_tier.strip():
            free_detail_strings.append(service_id)
        if isinstance(free_tier, dict) or isinstance(free_tier, list):
            structured_free_rules.append(service_id)
        if len(positive) > 1:
            multi_price.append({"service_id": service_id, "dimensions": len(positive)})

        evidence = " ".join(
            str(value or "")
            for value in (
                free_tier,
                (manifest.get("sla") or {}).get("rate_limit"),
                provenance.get("notes"),
            )
        )
        if RESOLVER_HINT.search(evidence):
            resolver_candidates.append(service_id)

        if (
            infer_access_tier(manifest) == "free"
            and "paid_signup" in ((manifest.get("invocation") or {}).get("setup_requires") or [])
        ):
            tier_conflicts.append(service_id)

        # Exercise the candidate projection for every record as part of the audit.
        derive_access_extension(manifest)

    return {
        "dataset": {
            "grain": "one committed library manifest per service",
            "manifest_count": len(manifests),
            "source": "library/**/*.asm.json",
        },
        "current_projection": {
            "tier_distribution": dict(sorted(tiers.items())),
            "free_tier_marked_count": len(free_marked),
            "free_tier_detail_string_count": len(free_detail_strings),
            "machine_readable_free_tier_rule_count": len(structured_free_rules),
            "services_with_multiple_positive_price_dimensions": multi_price,
        },
        "quality_findings": {
            "resolver_review_candidates_count": len(resolver_candidates),
            "resolver_review_candidates": resolver_candidates,
            "known_tier_conflicts": tier_conflicts,
        },
        "interpretation": {
            "scalar_price_loss": (
                "The legacy cheapest-price projection drops dimensions for every "
                "service listed under services_with_multiple_positive_price_dimensions."
            ),
            "free_tier_loss": (
                "The boolean projection marks availability but cannot express caps, "
                "reset windows, scopes, or caller-specific allowances."
            ),
            "resolver_candidates_caveat": (
                "Candidates are a text heuristic for follow-up, not verified evidence "
                "that every service exposes caller-specific pricing."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = audit(load_manifests())
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()

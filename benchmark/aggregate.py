#!/usr/bin/env python3
"""Aggregate benchmark/results/*.json into a comparison table + headline deltas.

Reads every <subject>__<condition>.json the harness wrote and prints, per
subject, the names_only vs asm contrast overall and per task type — plus the
two headline numbers: how much the ASM value layer cuts constraint violations
and lifts correct picks on the tasks where the deciding fact (price, data
governance) is invisible from names alone.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def load() -> dict:
    """subject -> condition -> metrics"""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in sorted(RESULTS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["subject"]][d["condition"]] = d["metrics"]
    return out


def _fmt(m: dict | None) -> str:
    if not m or "correct_rate" not in m:
        return "     —"
    return f"{m['correct_rate']:>4.0%}/{m['violation_rate']:>3.0%}"


def main() -> None:
    data = load()
    if not data:
        print("no results yet in benchmark/results/")
        return

    print("ToolSelect-Bench — correct% / violation% (names_only -> asm)\n")
    hdr = f"{'subject':38} {'overall':>18}  {'cheapest_eligible':>18}  {'governance':>18}"
    print(hdr)
    print("-" * len(hdr))
    deltas_viol, deltas_correct = [], []
    for subject, conds in sorted(data.items()):
        no, asm = conds.get("names_only"), conds.get("asm")

        def cell(key):
            n = (no or {}).get("by_type", {}).get(key) if key else no
            a = (asm or {}).get("by_type", {}).get(key) if key else asm
            if key is None:
                n, a = no, asm
            return f"{_fmt(n)} ->{_fmt(a)}"

        print(f"{subject:38} {cell(None):>18}  {cell('cheapest_eligible'):>18}  "
              f"{cell('governance'):>18}")

        # headline deltas on the FULL task set (robust), LLM subjects only
        if subject.startswith("llm:") and no and asm:
            deltas_viol.append(no["violation_rate"] - asm["violation_rate"])
            deltas_correct.append(asm["correct_rate"] - no["correct_rate"])

    if deltas_viol:
        n = len(deltas_viol)
        mv = sum(deltas_viol) / n
        mc = sum(deltas_correct) / n
        improved = sum(1 for d in deltas_correct if d > 0)
        cut_viol = sum(1 for d in deltas_viol if d > 0)
        print(f"\nHEADLINE (overall, {n} LLM subjects, all 50 tasks):")
        print(f"  correct picks improved with ASM in {improved}/{n} models (avg {mc:+.0%})")
        print(f"  constraint violations fell with ASM in {cut_viol}/{n} models (avg {mv:+.0%} pts)")


if __name__ == "__main__":
    main()

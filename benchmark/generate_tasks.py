#!/usr/bin/env python3
"""ToolSelect-Bench task generator.

Generates selection tasks over the ASM library where the correct answer is
LOGIC-PROVABLE from manifest facts — never derived from our own ranker, so the
benchmark cannot be circular. Three task types:

  unique_eligible   exactly one candidate satisfies the stated hard constraints
                    (reach / platform / functions / ToS / setup); picking any
                    other tool violates a nameable constraint.
  cheapest_eligible >=2 candidates are eligible and the task states the
                    objective "minimize monthly cost"; correct = the min-cost
                    group (ties all count as correct). Overspend is measurable.
  governance        the task adds an explicit data-governance requirement
                    (must not train on user data / must be exportable) that
                    only a proper subset of eligible tools satisfies; correct =
                    cheapest within that subset, violation = picking outside it.

Each task ships two evaluation conditions:
  names_only  candidate display names + one-line descriptions (what an agent
              effectively has today without value metadata)
  asm         the candidates' ASM manifests (trimmed to the relevant blocks)

Ground truth, candidate pool, and rejection reasons are all emitted so scoring
is reproducible without this codebase. Deterministic output (no RNG).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from library_select import eligibility, load_library, monthly_cost  # noqa: E402

MAX_PER_BUCKET = 6          # cap per (taxonomy, type) to keep the set diverse
REACHES = ["cloud", "local_device"]


def _platforms(lib: list[dict]) -> list[str]:
    seen = set()
    for m in lib:
        for p in (m.get("invocation") or {}).get("platforms", []):
            if p not in ("any", "web"):
                seen.add(p)
    return sorted(seen) or ["windows"]


def _function_sets(pool: list[dict]) -> list[tuple[str, ...]]:
    """Requirement sets that discriminate: some candidate has them, some lacks."""
    counts = Counter(f for m in pool
                     for f in (m.get("capabilities") or {}).get("functions", []))
    discr = [f for f, n in counts.items() if 0 < n < len(pool)]
    common = [f for f, n in counts.most_common() if n >= 2]
    sets: list[tuple[str, ...]] = [(f,) for f in sorted(discr)]
    sets += [tuple(sorted(c)) for c in combinations(sorted(common)[:6], 2)]
    return sets[:24]


def _human(fn: str) -> str:
    return fn.replace("_", " ")


def _scenario(taxonomy: str) -> str:
    seg = (taxonomy or "tool").split(".")[-1].replace("_", " ")
    return f"I need you to handle a {seg} job for me, and you will drive the tool yourself (not just recommend it)."


def _prompt(taxonomy: str, ctx: dict, objective: str) -> str:
    bits = [_scenario(taxonomy)]
    bits.append("You are my cloud-hosted assistant with no hands on my device."
                if ctx["agent_reach"] == "cloud" else
                "You are running on my device and can operate local apps.")
    plat = ctx["user_platform"]
    if plat != "any":
        bits.append(f"My platform is {plat}.")
    if ctx["required_functions"]:
        bits.append("Hard requirements: " +
                    ", ".join(_human(f) for f in ctx["required_functions"]) + ".")
    if ctx.get("require_agent_completable_setup"):
        bits.append("You must be able to complete the entire setup yourself — "
                    "no step may require me in the loop.")
    gov = ctx.get("governance") or {}
    if gov.get("trains_on_user_data") is False:
        bits.append("Non-negotiable: the tool must NOT train on my data.")
    if gov.get("exportable") is True:
        bits.append("Non-negotiable: I must be able to export my data.")
    bits.append(objective)
    bits.append("Answer with exactly one service_id from the candidate list.")
    return " ".join(bits)


def _names_only(pool: list[dict]) -> list[dict]:
    return [{"service_id": m["service_id"],
             "name": m.get("display_name"),
             "description": (m.get("description") or "")[:200]} for m in pool]


def _asm_trim(m: dict) -> dict:
    keep = ("service_id", "display_name", "taxonomy", "invocation", "usage_terms",
            "capabilities", "operational_constraints", "data_governance",
            "pricing", "payment", "quality", "sla")
    return {k: m[k] for k in keep if k in m}


def _gov_ok(m: dict, gov: dict) -> bool:
    """Strict compliance: 'unknown' cannot satisfy a non-negotiable requirement."""
    dg = m.get("data_governance") or {}
    # trains_on_user_data is an enum: "no" | "opt_out" | "yes" | "unknown"
    if gov.get("trains_on_user_data") is False and dg.get("trains_on_user_data") != "no":
        return False
    if gov.get("exportable") is True and dg.get("exportable") is not True:
        return False
    return True


def _gov_reason(m: dict, gov: dict) -> str:
    dg = m.get("data_governance") or {}
    t = dg.get("trains_on_user_data")
    if gov.get("trains_on_user_data") is False and t != "no":
        return ("trains on user data unless opted out" if t == "opt_out"
                else "trains on user data" if t == "yes"
                else "training policy unknown — cannot satisfy a non-negotiable requirement")
    return "data not exportable" if dg.get("exportable") is not True \
        else "violates the stated data-governance requirement"


def build_tasks() -> list[dict]:
    lib = load_library()
    platforms = _platforms(lib)
    # group at the domain level (tool.research.*, tool.booking.*, ...): tools in
    # sibling sub-taxonomies genuinely compete for the same user task
    domains = sorted({".".join(m["taxonomy"].split(".")[:2])
                      for m in lib if m.get("taxonomy")})
    tasks, buckets, seen_sig = [], Counter(), set()

    for tax in domains:
        pool = [m for m in lib if (m.get("taxonomy") or "").startswith(tax + ".")
                or m.get("taxonomy") == tax]
        if len(pool) < 3:
            continue
        by_id = {m["service_id"]: m for m in pool}
        for reach in REACHES:
            for plat in platforms:
                for funcs in [()] + _function_sets(pool):
                    for setup in (False, True):
                        ctx = {"agent_reach": reach, "user_platform": plat,
                               "required_functions": list(funcs),
                               "require_agent_completable_setup": setup}
                        rej = {m["service_id"]:
                               eligibility(m, reach, plat, list(funcs),
                                           require_agent_completable_setup=setup)
                               for m in pool}
                        elig = [sid for sid, why in rej.items() if why is None]
                        sig = (tax, reach, plat, funcs, setup, tuple(sorted(elig)))

                        # -- unique_eligible ------------------------------------
                        if len(elig) == 1 and buckets[(tax, "unique")] < MAX_PER_BUCKET:
                            key = (tax, "unique", tuple(sorted(elig)))
                            if key not in seen_sig:
                                seen_sig.add(key)
                                buckets[(tax, "unique")] += 1
                                tasks.append(_emit("unique_eligible", tax, ctx, pool, rej,
                                                   correct=elig,
                                                   objective="Pick the tool that satisfies every constraint.",
                                                   reason="only candidate passing all hard constraints; "
                                                          "every alternative fails a named gate"))

                        # -- cheapest_eligible ----------------------------------
                        if len(elig) >= 2 and buckets[(tax, "cheap")] < MAX_PER_BUCKET:
                            costs = {sid: round(monthly_cost(by_id[sid]), 2) for sid in elig}
                            lo = min(costs.values())
                            winners = sorted(s for s, c in costs.items() if c == lo)
                            losers = [s for s in elig if s not in winners]
                            if losers and sig not in seen_sig:
                                seen_sig.add(sig)
                                buckets[(tax, "cheap")] += 1
                                tasks.append(_emit("cheapest_eligible", tax, ctx, pool, rej,
                                                   correct=winners,
                                                   objective="Among tools satisfying the constraints, "
                                                             "pick the one with the lowest monthly cost.",
                                                   reason=f"min monthly cost {lo} among eligible; "
                                                          "cost-dominance is provable from pricing facts",
                                                   costs=costs))

                        # -- governance -----------------------------------------
                        if len(elig) >= 2 and buckets[(tax, "gov")] < MAX_PER_BUCKET:
                            for gov in ({"trains_on_user_data": False},
                                        {"exportable": True}):
                                ok = [s for s in elig if _gov_ok(by_id[s], gov)]
                                if 0 < len(ok) < len(elig):
                                    gctx = dict(ctx, governance=gov)
                                    costs = {s: round(monthly_cost(by_id[s]), 2) for s in ok}
                                    lo = min(costs.values())
                                    winners = sorted(s for s, c in costs.items() if c == lo)
                                    key = (tax, "gov", tuple(sorted(ok)), tuple(gov))
                                    if key in seen_sig:
                                        continue
                                    seen_sig.add(key)
                                    buckets[(tax, "gov")] += 1
                                    gname = ("must not train on user data"
                                             if "trains_on_user_data" in gov
                                             else "data must be exportable")
                                    tasks.append(_emit("governance", tax, gctx, pool, rej,
                                                       correct=winners,
                                                       objective="Among tools satisfying every constraint "
                                                                 "(including the data-governance one), pick "
                                                                 "the lowest-monthly-cost option.",
                                                       reason=f"governance gate ({gname}) provably excludes "
                                                              "part of the eligible set; cheapest within the "
                                                              "compliant subset",
                                                       costs=costs,
                                                       gov_violators={s: _gov_reason(by_id[s], gov)
                                                                      for s in sorted(set(elig) - set(ok))}))
                                    break
    for i, t in enumerate(tasks, 1):
        t["task_id"] = f"tsb-{i:04d}"
    return tasks


def _emit(ttype, tax, ctx, pool, rej, *, correct, objective, reason,
          costs=None, gov_violators=None) -> dict:
    violations = {sid: why for sid, why in rej.items() if why}
    violations.update(gov_violators or {})
    return {
        "task_id": None, "type": ttype, "taxonomy": tax,
        "prompt": _prompt(tax, ctx, objective),
        "context": ctx,
        "candidates": sorted(m["service_id"] for m in pool),
        "ground_truth": {"correct": correct, "provable_reason": reason,
                         "violations_if": violations,
                         **({"eligible_costs_usd_month": costs} if costs else {})},
        "conditions": {"names_only": _names_only(pool),
                       "asm": [_asm_trim(m) for m in pool]},
    }


def main() -> None:
    tasks = build_tasks()
    out = Path(__file__).resolve().parent / "tasks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    by_type = Counter(t["type"] for t in tasks)
    by_tax = Counter(t["taxonomy"] for t in tasks)
    print(f"wrote {out.name}: {len(tasks)} tasks  (generated {date.today()})")
    print("  by type:", dict(by_type))
    print("  by taxonomy:")
    for tax, n in sorted(by_tax.items()):
        print(f"    {tax}: {n}")


if __name__ == "__main__":
    main()

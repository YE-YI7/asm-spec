#!/usr/bin/env python3
"""Importable ASM tool-selector over the library/ manifests.

One selector, shared by the demo, the CLI, and the MCP server. Implements the
confirmed priority order:

  gate 1: agent can invoke it      (agent_operable; reach matches the agent env)
  gate 2: automated use is allowed (usage_terms.automation_allowed != 'no')
  gate 3: meets task requirements  (required functions present; platform fits)
  rank  : among survivors, cheapest first, then feature-richest

It also surfaces the operational policy of the pick (risk_class / approval /
side_effects) so the caller can gate high-stakes actions (send message, spend
money, mutate a repo) before invoking.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

# Default to the library/ next to this module (works from a checkout); override
# with ASM_LIBRARY_DIR so the MCP server / API can point at any library location.
LIBRARY_DIR = Path(os.environ.get("ASM_LIBRARY_DIR")
                   or (Path(__file__).resolve().parent / "library"))


def load_library(library_dir: str | Path | None = None) -> list[dict]:
    d = Path(library_dir) if library_dir else LIBRARY_DIR
    return [json.loads(Path(p).read_text(encoding="utf-8"))
            for p in glob.glob(str(d / "**" / "*.asm.json"), recursive=True)]


def monthly_cost(m: dict) -> float:
    dims = (m.get("pricing") or {}).get("billing_dimensions") or []
    free = "free_tier" in (m.get("payment") or {}).get("methods", [])
    base = 0.0 if free else 1e9
    saw_zero = False
    for d in dims:
        c, u = d.get("cost_per_unit", 0), d.get("unit", "")
        if c == 0:
            saw_zero = True
            continue
        base = min(base, c if "month" in u else c / 12 if "year" in u else c / 24)
    if base == 1e9 and saw_zero:
        return 0.0
    return 0.0 if free else base


def eligibility(m: dict, agent_reach: str, user_platform: str, required_functions,
                require_agent_completable_setup: bool = False) -> str | None:
    """Return None if the tool is eligible, else a human-readable rejection reason."""
    inv = m.get("invocation", {})
    if not inv.get("agent_operable"):
        return "not agent-operable"
    if inv.get("reach") == "local_device" and agent_reach != "local_device":
        return f"reach=local_device but agent is {agent_reach} (can't drive remotely)"
    if require_agent_completable_setup and inv.get("agent_completable_setup") is False:
        req = ", ".join(inv.get("setup_requires") or []) or "human-in-the-loop"
        return f"setup not agent-completable (requires {req})"
    if (m.get("usage_terms") or {}).get("automation_allowed") == "no":
        return "ToS forbids automated use"
    plats = inv.get("platforms", [])
    if not ({"any", "web"} & set(plats)) and user_platform not in plats:
        return f"platform {user_platform} unsupported ({plats})"
    funcs = set((m.get("capabilities") or {}).get("functions", []))
    missing = [f for f in required_functions if f not in funcs]
    if missing:
        return f"missing required functions: {missing}"
    return None


def policy_of(m: dict, require_approval_for=()) -> dict:
    ops = m.get("operational_constraints") or {}
    approval = ops.get("approval") or {}
    side = ops.get("side_effects", []) or []
    req = approval.get("required")
    approval_required = (req == "always") or bool(set(side) & set(require_approval_for or ()))
    return {
        "risk_class": ops.get("risk_class", "unknown"),
        "approval_policy": req or "unknown",
        "approval_required": approval_required,
        "side_effects": side,
    }


def rank(task: str, *, taxonomy: str | None = None, agent_reach: str = "cloud",
         user_platform: str = "any", required_functions=(),
         require_agent_completable_setup: bool = False, library=None):
    """Return (kept_manifests_sorted, rejected[{service, service_id, reason}])."""
    entries = library if library is not None else load_library()
    pool = [m for m in entries if taxonomy is None or m.get("taxonomy") == taxonomy]
    kept, rejected = [], []
    for m in pool:
        why = eligibility(m, agent_reach, user_platform, list(required_functions),
                          require_agent_completable_setup=require_agent_completable_setup)
        if why:
            rejected.append({"service": m.get("display_name"),
                             "service_id": m.get("service_id"), "reason": why})
        else:
            kept.append(m)
    kept.sort(key=lambda m: (monthly_cost(m),
                             -len((m.get("capabilities") or {}).get("functions", []))))
    return kept, rejected


def select(task: str, *, taxonomy: str | None = None, agent_reach: str = "cloud",
           user_platform: str = "any", required_functions=(),
           require_approval_for=(), require_agent_completable_setup: bool = False,
           library=None) -> dict:
    """Structured selection decision (used by the CLI, MCP server, hosted API)."""
    kept, rejected = rank(task, taxonomy=taxonomy, agent_reach=agent_reach,
                          user_platform=user_platform,
                          required_functions=required_functions,
                          require_agent_completable_setup=require_agent_completable_setup,
                          library=library)
    out = {
        "task": task, "taxonomy": taxonomy,
        "selected": None, "reason": "no eligible tool",
        "risk_class": None, "approval_required": None, "side_effects": [],
        "alternatives": [], "rejected": rejected,
    }
    if kept:
        top = kept[0]
        pol = policy_of(top, require_approval_for)
        inv = top.get("invocation") or {}
        out["selected"] = {
            "service_id": top.get("service_id"),
            "display_name": top.get("display_name"),
            "monthly_cost_usd": round(monthly_cost(top), 2),
            "interface": inv.get("interface"),
            "reach": inv.get("reach"),
            "agent_completable_setup": inv.get("agent_completable_setup"),
            "setup_requires": inv.get("setup_requires", []),
        }
        out["risk_class"] = pol["risk_class"]
        out["approval_required"] = pol["approval_required"]
        out["side_effects"] = pol["side_effects"]
        out["reason"] = (
            f"Eligible {pol['risk_class']}-risk tool with the required functions; "
            + ("approval required before invocation." if pol["approval_required"]
               else "no approval gate triggered.")
        )
        out["alternatives"] = [
            {"service_id": m.get("service_id"), "display_name": m.get("display_name"),
             "monthly_cost_usd": round(monthly_cost(m), 2)} for m in kept[1:]
        ]
    return out

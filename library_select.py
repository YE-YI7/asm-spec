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
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from asm_version import SELECTOR_VERSION

HASH_ALGORITHM = "sha256"
ASM_JSON_CANONICALIZATION = "asm-json-sort-keys-v1"
SELECTION_POLICY = ("gate: agent_operable + reach + agent_completable_setup + "
                    "usage_terms.automation_allowed + platform + required_functions; "
                    "rank: monthly_cost asc, then functions desc")

# Default to the library/ next to this module (works from a checkout); override
# with ASM_LIBRARY_DIR so the MCP server / API can point at any library location.
LIBRARY_DIR = Path(os.environ.get("ASM_LIBRARY_DIR")
                   or (Path(__file__).resolve().parent / "library"))


def load_library(library_dir: str | Path | None = None) -> list[dict]:
    d = Path(library_dir) if library_dir else LIBRARY_DIR
    manifests = [json.loads(Path(p).read_text(encoding="utf-8"))
                 for p in glob.glob(str(d / "**" / "*.asm.json"), recursive=True)]
    if manifests:
        return manifests
    # Installed context: the on-disk library/ isn't shipped alongside a flat
    # module, so fall back to the frozen bundle (see build_library_bundle.py).
    try:
        from _asm_library_data import MANIFESTS
        return [dict(m) for m in MANIFESTS]
    except ImportError:
        return manifests


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
    # deterministic tie-break (service_id): identical evidence must yield an
    # identical pick on any OS/filesystem — receipts demand reproducibility
    kept.sort(key=lambda m: (monthly_cost(m),
                             -len((m.get("capabilities") or {}).get("functions", [])),
                             m.get("service_id", "")))
    return kept, rejected


def canonical_json_bytes(document: object) -> bytes:
    """Serialize one JSON value using ASM's versioned v1 digest profile.

    This preserves array order, sorts object keys, emits no insignificant
    whitespace, keeps non-ASCII text as UTF-8, and uses Python's standard JSON
    primitive serialization. It is intentionally named and versioned rather
    than mislabeled as RFC 8785 JCS.
    """
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def document_digest(document: object) -> str:
    """Return a sha256 digest over the ASM v1 canonical JSON representation."""
    return "sha256:" + hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def manifest_digest(m: dict) -> str:
    """Pin the exact manifest evidence state consulted by a selector."""
    return document_digest(m)


def build_selection_receipt(decision: dict, pool: list[dict], *,
                            request: dict, selection_id: str | None = None,
                            issued_at: str | None = None) -> dict:
    """Selection Receipt v0.1 — the accountable record of WHY this provider.

    Upstream complement of the execution-receipt family
    (docs/integrations/akkhar-code-receipt-spec.md): an execution receipt says
    what a service did; a selection receipt says why it was chosen over the
    alternatives, on what evidence, under which constraints. Together with a
    payment mandate (AP2) and settlement (x402) they form a complete audit
    chain for autonomous, human-not-present spending.
    """
    return {
        "receipt_type": "selection",
        "receipt_version": "0.1",
        "verification_status": "unsigned",
        "selection_id": selection_id or str(uuid.uuid4()),
        "issued_at": issued_at
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selector": {"name": SELECTOR_VERSION, "policy": SELECTION_POLICY},
        "request": request,
        "evidence": [{"service_id": m.get("service_id"),
                      "hash_algorithm": HASH_ALGORITHM,
                      "canonicalization": ASM_JSON_CANONICALIZATION,
                      "manifest_digest": manifest_digest(m)} for m in pool],
        "selected": decision.get("selected"),
        "selection_reason": decision.get("reason"),
        "risk_class": decision.get("risk_class"),
        "approval_required": decision.get("approval_required"),
        "side_effects": decision.get("side_effects", []),
        "alternatives": decision.get("alternatives", []),
        "rejected": decision.get("rejected", []),
    }


def select(task: str, *, taxonomy: str | None = None, agent_reach: str = "cloud",
           user_platform: str = "any", required_functions=(),
           require_approval_for=(), require_agent_completable_setup: bool = False,
           library=None, receipt: bool = False) -> dict:
    """Structured selection decision (used by the CLI, MCP server, hosted API).
    With receipt=True the decision carries a Selection Receipt (audit record)."""
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
    if receipt:
        entries = library if library is not None else load_library()
        pool = [m for m in entries if taxonomy is None or m.get("taxonomy") == taxonomy]
        out["receipt"] = build_selection_receipt(out, pool, request={
            "task": task, "taxonomy": taxonomy, "agent_reach": agent_reach,
            "user_platform": user_platform,
            "required_functions": list(required_functions),
            "require_approval_for": list(require_approval_for or ()),
            "require_agent_completable_setup": require_agent_completable_setup,
        })
    return out

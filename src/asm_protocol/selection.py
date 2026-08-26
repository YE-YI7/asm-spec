"""Deterministic ASM eligibility, ranking, and Selection Receipt production."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .cost import Workload, coerce_workload, estimate_monthly_cost
from .version import SELECTOR_NAME

SELECTOR_VERSION = SELECTOR_NAME
SELECTION_POLICY = (
    "gate: agent_operable + reach + agent_completable_setup + "
    "usage_terms.automation_allowed + platform + required_functions; "
    "rank: monthly cost only when all candidates are comparable; otherwise no decision "
    "unless the caller explicitly requests capability_breadth fallback"
)
LEGACY_SELECTOR_VERSION = "asm-protocol/0.5.1"
LEGACY_SELECTION_POLICY = (
    "gate: agent_operable + reach + agent_completable_setup + "
    "usage_terms.automation_allowed + platform + required_functions; "
    "rank: monthly_cost asc, then functions desc"
)

_REPO_LIBRARY = Path(__file__).resolve().parents[2] / "library"
LIBRARY_DIR = Path(os.environ.get("ASM_LIBRARY_DIR") or _REPO_LIBRARY)


def load_library(library_dir: str | Path | None = None) -> list[dict]:
    directory = Path(library_dir) if library_dir else LIBRARY_DIR
    manifests = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in glob.glob(str(directory / "**" / "*.asm.json"), recursive=True)
    ]
    if manifests:
        return manifests
    try:
        from _asm_library_data import MANIFESTS

        return [dict(manifest) for manifest in MANIFESTS]
    except ImportError:
        return manifests


def legacy_monthly_cost(manifest: dict) -> float:
    """Frozen 0.5.2 scalar used only to reproduce historical benchmark/receipts."""
    dimensions = (manifest.get("pricing") or {}).get("billing_dimensions") or []
    free = "free_tier" in (manifest.get("payment") or {}).get("methods", [])
    base = 0.0 if free else 1e9
    saw_zero = False
    for dimension in dimensions:
        cost = dimension.get("cost_per_unit", 0)
        unit = dimension.get("unit", "")
        if cost == 0:
            saw_zero = True
            continue
        base = min(
            base,
            cost if "month" in unit else cost / 12 if "year" in unit else cost / 24,
        )
    if base == 1e9 and saw_zero:
        return 0.0
    return 0.0 if free else base


def monthly_cost(manifest: dict, workload: Workload | None = None) -> float:
    """Return a monthly total only when supported; unknown totals become infinity.

    New code should inspect :func:`estimate_monthly_cost` instead of discarding
    its status and assumptions.
    """
    estimate = estimate_monthly_cost(manifest, workload)
    if estimate.status == "known" and estimate.monthly_total is not None:
        return estimate.monthly_total
    return float("inf")


def eligibility(
    manifest: dict,
    agent_reach: str,
    user_platform: str,
    required_functions,
    require_agent_completable_setup: bool = False,
) -> str | None:
    """Return None when eligible, otherwise a human-readable rejection reason."""
    invocation = manifest.get("invocation", {})
    if not invocation.get("agent_operable"):
        return "not agent-operable"
    if invocation.get("reach") == "local_device" and agent_reach != "local_device":
        return f"reach=local_device but agent is {agent_reach} (can't drive remotely)"
    if (
        require_agent_completable_setup
        and invocation.get("agent_completable_setup") is False
    ):
        required = (
            ", ".join(invocation.get("setup_requires") or []) or "human-in-the-loop"
        )
        return f"setup not agent-completable (requires {required})"
    if (manifest.get("usage_terms") or {}).get("automation_allowed") == "no":
        return "ToS forbids automated use"
    platforms = invocation.get("platforms", [])
    if not ({"any", "web"} & set(platforms)) and user_platform not in platforms:
        return f"platform {user_platform} unsupported ({platforms})"
    functions = set((manifest.get("capabilities") or {}).get("functions", []))
    missing = [function for function in required_functions if function not in functions]
    if missing:
        return f"missing required functions: {missing}"
    return None


def policy_of(manifest: dict, require_approval_for=()) -> dict:
    operational = manifest.get("operational_constraints") or {}
    approval = operational.get("approval") or {}
    side_effects = operational.get("side_effects", []) or []
    required = approval.get("required")
    approval_required = required == "always" or bool(
        set(side_effects) & set(require_approval_for or ())
    )
    return {
        "risk_class": operational.get("risk_class", "unknown"),
        "approval_policy": required or "unknown",
        "approval_required": approval_required,
        "side_effects": side_effects,
    }


def rank(
    task: str,
    *,
    taxonomy: str | None = None,
    agent_reach: str = "cloud",
    user_platform: str = "any",
    required_functions=(),
    require_agent_completable_setup: bool = False,
    library=None,
    workload: Workload | dict | None = None,
    selection_profile: str = "current",
    fallback_policy: str | None = None,
):
    """Filter and rank manifests; ``task`` is audit text, not parsed input."""
    del task
    workload = coerce_workload(workload)
    entries = library if library is not None else load_library()
    pool = [m for m in entries if taxonomy is None or m.get("taxonomy") == taxonomy]
    kept, rejected = [], []
    for manifest in pool:
        reason = eligibility(
            manifest,
            agent_reach,
            user_platform,
            list(required_functions),
            require_agent_completable_setup=require_agent_completable_setup,
        )
        if reason:
            rejected.append(
                {
                    "service": manifest.get("display_name"),
                    "service_id": manifest.get("service_id"),
                    "reason": reason,
                }
            )
        else:
            kept.append(manifest)

    if selection_profile == "legacy-0.5.2":
        kept.sort(
            key=lambda manifest: (
                legacy_monthly_cost(manifest),
                -len((manifest.get("capabilities") or {}).get("functions", [])),
                manifest.get("service_id", ""),
            )
        )
    elif selection_profile == "current":
        estimates = {
            m.get("service_id"): estimate_monthly_cost(m, workload) for m in kept
        }
        comparable = (
            bool(kept)
            and all(
                estimate.status == "known" and estimate.monthly_total is not None
                for estimate in estimates.values()
            )
            and len({estimate.currency for estimate in estimates.values()}) == 1
        )
        if comparable:
            kept.sort(
                key=lambda manifest: (
                    estimates[manifest.get("service_id")].monthly_total,
                    -len((manifest.get("capabilities") or {}).get("functions", [])),
                    manifest.get("service_id", ""),
                )
            )
        elif fallback_policy == "capability_breadth":
            kept.sort(
                key=lambda manifest: (
                    -len((manifest.get("capabilities") or {}).get("functions", [])),
                    manifest.get("service_id", ""),
                )
            )
        elif fallback_policy is None:
            kept.sort(key=lambda manifest: manifest.get("service_id", ""))
        else:
            raise ValueError(f"unknown fallback_policy={fallback_policy!r}")
    else:
        raise ValueError(f"unknown selection_profile={selection_profile!r}")
    return kept, rejected


def manifest_digest(manifest: dict) -> str:
    canonical = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _receipt_candidate(candidate: dict | None, pool: list[dict]) -> dict | None:
    """Project a current decision onto the frozen Selection Receipt v0.1 shape."""
    if candidate is None:
        return None
    manifest = next(
        (
            item
            for item in pool
            if item.get("service_id") == candidate.get("service_id")
        ),
        None,
    )
    if manifest is None:
        raise ValueError("selected candidate is not present in receipt evidence pool")
    invocation = manifest.get("invocation") or {}
    return {
        "service_id": manifest.get("service_id"),
        "display_name": manifest.get("display_name"),
        "monthly_cost_usd": round(legacy_monthly_cost(manifest), 2),
        "interface": invocation.get("interface"),
        "reach": invocation.get("reach"),
        "agent_completable_setup": invocation.get("agent_completable_setup"),
        "setup_requires": invocation.get("setup_requires", []),
    }


def _receipt_alternatives(alternatives: list[dict], pool: list[dict]) -> list[dict]:
    by_id = {manifest.get("service_id"): manifest for manifest in pool}
    result = []
    for alternative in alternatives:
        manifest = by_id.get(alternative.get("service_id"))
        if manifest is not None:
            result.append(
                {
                    "service_id": manifest.get("service_id"),
                    "display_name": manifest.get("display_name"),
                    "monthly_cost_usd": round(legacy_monthly_cost(manifest), 2),
                }
            )
    return result


def build_selection_receipt(
    decision: dict,
    pool: list[dict],
    *,
    request: dict,
    selection_profile: str = "current",
) -> dict:
    """Build the frozen Selection Receipt v0.1 compatibility projection."""
    legacy = selection_profile == "legacy-0.5.2"
    return {
        "receipt_type": "selection",
        "receipt_version": "0.1",
        "selection_id": str(uuid.uuid4()),
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selector": {
            "name": LEGACY_SELECTOR_VERSION if legacy else SELECTOR_VERSION,
            "policy": LEGACY_SELECTION_POLICY if legacy else SELECTION_POLICY,
        },
        "request": request,
        "evidence": [
            {
                "service_id": manifest.get("service_id"),
                "manifest_digest": manifest_digest(manifest),
            }
            for manifest in pool
        ],
        "selected": _receipt_candidate(decision.get("selected"), pool),
        "selection_reason": decision.get("reason"),
        "risk_class": decision.get("risk_class"),
        "approval_required": decision.get("approval_required"),
        "side_effects": decision.get("side_effects", []),
        "alternatives": _receipt_alternatives(decision.get("alternatives", []), pool),
        "rejected": decision.get("rejected", []),
    }


def _selected_view(manifest: dict, workload: Workload | None) -> dict:
    invocation = manifest.get("invocation") or {}
    estimate = estimate_monthly_cost(manifest, workload)
    return {
        "service_id": manifest.get("service_id"),
        "display_name": manifest.get("display_name"),
        "monthly_cost_usd": (
            round(estimate.monthly_total, 2)
            if estimate.status == "known" and estimate.monthly_total is not None
            else None
        ),
        "cost_estimate": estimate.to_dict(),
        "interface": invocation.get("interface"),
        "reach": invocation.get("reach"),
        "agent_completable_setup": invocation.get("agent_completable_setup"),
        "setup_requires": invocation.get("setup_requires", []),
    }


def select(
    task: str,
    *,
    taxonomy: str | None = None,
    agent_reach: str = "cloud",
    user_platform: str = "any",
    required_functions=(),
    require_approval_for=(),
    require_agent_completable_setup: bool = False,
    library=None,
    receipt: bool = False,
    workload: Workload | dict | None = None,
    selection_profile: str = "current",
    fallback_policy: str | None = None,
) -> dict:
    """Return a decision from structured constraints; never parse ``task`` text."""
    workload = coerce_workload(workload)
    out = {
        "task": task,
        "task_interpreted": False,
        "taxonomy": taxonomy,
        "selection_status": "under_specified",
        "selected": None,
        "reason": (
            "structured selection constraints required: provide taxonomy or "
            "required_functions; the deterministic core does not interpret task text"
        ),
        "risk_class": None,
        "approval_required": None,
        "side_effects": [],
        "alternatives": [],
        "rejected": [],
    }
    entries = library if library is not None else load_library()
    pool = [m for m in entries if taxonomy is None or m.get("taxonomy") == taxonomy]

    if taxonomy is not None or required_functions:
        kept, rejected = rank(
            task,
            taxonomy=taxonomy,
            agent_reach=agent_reach,
            user_platform=user_platform,
            required_functions=required_functions,
            require_agent_completable_setup=require_agent_completable_setup,
            library=entries,
            workload=workload,
            selection_profile=selection_profile,
            fallback_policy=fallback_policy,
        )
        out["rejected"] = rejected
        out["selection_status"] = "no_eligible"
        out["reason"] = "no eligible tool"
        estimates = [estimate_monthly_cost(manifest, workload) for manifest in kept]
        comparable_costs = (
            bool(kept)
            and all(
                estimate.status == "known" and estimate.monthly_total is not None
                for estimate in estimates
            )
            and len({estimate.currency for estimate in estimates}) == 1
        )
        if (
            selection_profile == "current"
            and len(kept) > 1
            and not comparable_costs
            and fallback_policy is None
        ):
            out["selection_status"] = "needs_cost_facts"
            out["reason"] = (
                "multiple tools are eligible but their costs are not comparable; "
                "provide workload/free-tier facts or explicitly request a fallback policy"
            )
            out["alternatives"] = [
                _selected_view(manifest, workload) for manifest in kept
            ]
        elif kept:
            top = kept[0]
            policy = policy_of(top, require_approval_for)
            out["selected"] = _selected_view(top, workload)
            out["risk_class"] = policy["risk_class"]
            out["approval_required"] = policy["approval_required"]
            out["side_effects"] = policy["side_effects"]
            out["selection_status"] = "selected"
            cost_reason = (
                "candidate monthly costs are comparable under the resolved cost model"
                if comparable_costs
                else f"candidate costs are not fully comparable; explicit {fallback_policy} fallback was used"
            )
            if selection_profile == "legacy-0.5.2":
                out["reason"] = (
                    f"Eligible {policy['risk_class']}-risk tool with the required functions; "
                    + (
                        "approval required before invocation."
                        if policy["approval_required"]
                        else "no approval gate triggered."
                    )
                )
            else:
                out["reason"] = (
                    f"Eligible {policy['risk_class']}-risk tool with required functions; "
                    f"{cost_reason}; "
                    + (
                        "approval required before invocation."
                        if policy["approval_required"]
                        else "no approval gate triggered."
                    )
                )
            out["alternatives"] = [_selected_view(m, workload) for m in kept[1:]]

    if receipt:
        if selection_profile == "current" and fallback_policy is not None:
            raise ValueError(
                "Selection Receipt v0.1 cannot encode fallback_policy; "
                "omit the fallback or use a future receipt contract"
            )
        out["receipt"] = build_selection_receipt(
            out,
            pool,
            request={
                "task": task,
                "taxonomy": taxonomy,
                "agent_reach": agent_reach,
                "user_platform": user_platform,
                "required_functions": list(required_functions),
                "require_approval_for": list(require_approval_for or ()),
                "require_agent_completable_setup": require_agent_completable_setup,
            },
            selection_profile=selection_profile,
        )
    return out


__all__ = [
    "LIBRARY_DIR",
    "SELECTION_POLICY",
    "SELECTOR_VERSION",
    "Workload",
    "build_selection_receipt",
    "eligibility",
    "estimate_monthly_cost",
    "legacy_monthly_cost",
    "load_library",
    "manifest_digest",
    "monthly_cost",
    "policy_of",
    "rank",
    "select",
]

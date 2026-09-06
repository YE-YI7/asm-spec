"""Authorized, budget-bounded successor decisions after a failed search attempt."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from .bootstrap import build_bootstrap_decision
from .contracts import ContractValidationError, validate_contract
from .digests import digest_json


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _observed_cost(outcome: Mapping[str, Any], currency: str) -> Decimal | None:
    for field in ("settled_cost", "estimated_cost"):
        money = outcome.get(field) or {}
        if (
            money.get("status") == "known"
            and money.get("amount") is not None
            and money.get("currency") == currency
        ):
            return Decimal(str(money["amount"]))
    return None


def plan_search_fallback(
    *,
    request: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    previous_decision: Mapping[str, Any],
    previous_outcomes: Sequence[Mapping[str, Any]],
    decision_id: str,
    issued_at: str,
    valid_until: str,
    now: str,
    fallback_interface_id: str | None = None,
    issuer_id: str = "asm-local",
) -> dict[str, Any]:
    """Return a successor decision only inside the request's explicit fallback grant.

    The host may name one allowed fallback. If it does not, ASM proceeds only
    when exactly one untried fallback remains; it does not invent a ranking.
    """
    validate_contract("search_request", request)
    validate_contract("decision_receipt", previous_decision)
    outcomes = [dict(row) for row in previous_outcomes]
    for outcome in outcomes:
        validate_contract("outcome_receipt", outcome)

    request_digest = digest_json(request)
    if previous_decision.get("request_commitment") != request_digest:
        raise ContractValidationError("previous decision does not bind this search request")
    if not outcomes:
        return {"status": "not_needed", "reason_codes": ["fallback.no_failed_attempt"], "decision": None}
    latest = outcomes[-1]
    if any(row.get("request_commitment") != request_digest for row in outcomes):
        raise ContractValidationError("a prior outcome does not bind this search request")
    if len({row["outcome_id"] for row in outcomes}) != len(outcomes):
        raise ContractValidationError("prior outcomes contain a duplicate outcome_id")
    if len({row["attempt_id"] for row in outcomes}) != len(outcomes):
        raise ContractValidationError("prior outcomes contain a duplicate attempt_id")
    if latest.get("decision_id") != previous_decision.get("decision_id"):
        raise ContractValidationError("latest outcome does not bind the previous decision")
    if latest.get("decision_receipt_digest") != digest_json(previous_decision):
        raise ContractValidationError("latest outcome decision digest does not match the previous decision")
    selected = previous_decision.get("selected") or {}
    if latest["executed"]["interface_id"] != selected.get("interface_id"):
        raise ContractValidationError("latest outcome interface does not match the previous decision")
    if latest.get("tool_status") == "succeeded":
        return {"status": "not_needed", "reason_codes": ["fallback.previous_succeeded"], "decision": None}

    execution = request["execution"]
    if len(outcomes) >= execution["max_attempts"]:
        return {"status": "stopped", "reason_codes": ["fallback.max_attempts_reached"], "decision": None}
    deadline = _timestamp(request["issued_at"]) + timedelta(milliseconds=execution["deadline_ms"])
    if _timestamp(now) >= deadline or _timestamp(valid_until) > deadline:
        return {"status": "stopped", "reason_codes": ["fallback.deadline_exceeded"], "decision": None}

    authorized_rows = {
        str(row["interface_id"]): row
        for row in request["candidate_scope"]["authorized_interfaces"]
    }
    allowlist = set(execution["fallback_allowlist"])
    attempted = {str(row["executed"]["interface_id"]) for row in outcomes}
    forbidden = set(request["effective_policy"].get("forbidden_providers", []))
    available = sorted(
        interface_id
        for interface_id in (allowlist & authorized_rows.keys()) - attempted
        if authorized_rows[interface_id]["provider_id"] not in forbidden
    )
    if fallback_interface_id is not None:
        if fallback_interface_id not in available:
            return {"status": "stopped", "reason_codes": ["fallback.not_authorized"], "decision": None}
        target = fallback_interface_id
    elif len(available) == 1:
        target = available[0]
    elif not available:
        return {"status": "stopped", "reason_codes": ["fallback.no_authorized_candidate"], "decision": None}
    else:
        return {
            "status": "needs_owner_input",
            "reason_codes": ["fallback.multiple_authorized_candidates"],
            "alternatives": available,
            "decision": None,
        }

    budget = request["budget"]
    consumed = Decimal(0)
    for outcome in outcomes:
        amount = _observed_cost(outcome, budget["currency"])
        if amount is None and outcome is latest:
            estimate = previous_decision.get("cost_estimate") or {}
            if (
                estimate.get("status") == "known"
                and estimate.get("amount") is not None
                and estimate.get("currency") == budget["currency"]
            ):
                amount = Decimal(str(estimate["amount"]))
        if amount is None:
            return {"status": "needs_budget", "reason_codes": ["fallback.prior_cost_unknown"], "decision": None}
        consumed += amount
    session_remaining = budget.get("max_session_remaining")
    if session_remaining is not None:
        remaining = Decimal(str(session_remaining)) - consumed
        if remaining <= 0:
            return {"status": "stopped", "reason_codes": ["fallback.session_budget_exhausted"], "decision": None}
    else:
        remaining = None

    successor_request = copy.deepcopy(dict(request))
    successor_request["candidate_scope"]["explicit_interface_id"] = None
    successor_request["candidate_scope"]["default_interface_id"] = target
    successor_request["candidate_scope"]["default_source"] = "host_configuration"
    successor_request["budget"]["max_session_remaining"] = (
        format(remaining, "f") if remaining is not None else None
    )
    successor = build_bootstrap_decision(
        request=successor_request,
        evidence=evidence,
        decision_id=decision_id,
        issued_at=issued_at,
        valid_until=valid_until,
        issuer_id=issuer_id,
    )
    successor["request_commitment"] = digest_json(request)
    successor["predecessor_decision_id"] = previous_decision["decision_id"]
    if successor.get("selected") is not None:
        successor["selected"]["reason_codes"] = ["fallback.authorized", "policy.eligible"]
    validate_contract("decision_receipt", successor)
    return {
        "status": "selected" if successor["status"] == "selected" else successor["status"],
        "reason_codes": ["fallback.successor_decision"],
        "decision": successor,
    }


__all__ = ["plan_search_fallback"]

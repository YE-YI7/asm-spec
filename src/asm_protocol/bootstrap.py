"""Deterministic cold-start selection for the search application draft."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import validate_contract
from .digests import digest_json

_PRICE_PATH = "pricing.search_request"
_USABLE_EVIDENCE = {"current"}


def _candidate_rows(request: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list((request.get("candidate_scope") or {}).get("authorized_interfaces") or [])


def _evidence_by_interface(evidence: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in evidence:
        validate_contract("selection_evidence", item)
        interface_id = str((item.get("candidate") or {}).get("interface_id") or "")
        grouped.setdefault(interface_id, []).append(item)
    return grouped


def _money(item: Mapping[str, Any]) -> tuple[Decimal, str] | None:
    claim = item.get("claim") or {}
    if claim.get("value_kind") not in {"currency_estimate", "currency_usage"}:
        return None
    value, currency = claim.get("value"), claim.get("currency")
    if value is None or not isinstance(currency, str):
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return None
    return (amount, currency) if amount.is_finite() and amount >= 0 else None


def _candidate_facts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    digests = [{"evidence_id": row["evidence_id"], "digest": digest_json(row)} for row in rows]
    interface_digests = {
        str((row.get("candidate") or {}).get("interface_digest"))
        for row in rows
        if (row.get("candidate") or {}).get("interface_digest")
    }
    prices = [
        value
        for row in rows
        if row.get("claim_path") == _PRICE_PATH and row.get("status") in _USABLE_EVIDENCE
        if (value := _money(row)) is not None
    ]
    price_statuses = {
        str(row.get("status"))
        for row in rows
        if row.get("claim_path") == _PRICE_PATH
    }
    return {
        "evidence_refs": digests,
        "snapshot_digest": digest_json(sorted(digests, key=lambda row: row["evidence_id"])),
        "interface_digest": next(iter(interface_digests)) if len(interface_digests) == 1 else None,
        "interface_digest_conflict": len(interface_digests) > 1,
        "prices": prices,
        "price_statuses": price_statuses,
    }


def build_bootstrap_decision(
    *,
    request: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    decision_id: str,
    issued_at: str,
    valid_until: str,
    issuer_id: str = "asm-local",
) -> dict[str, Any]:
    """Choose only when authorization, evidence, and budget make it unambiguous."""
    validate_contract("search_request", request)
    grouped = _evidence_by_interface(evidence)
    candidates = _candidate_rows(request)
    candidate_ids = [str(row["interface_id"]) for row in candidates]
    facts = {interface_id: _candidate_facts(grouped.get(interface_id, [])) for interface_id in candidate_ids}
    summaries = [
        {"interface_id": interface_id, "evidence_snapshot_digest": facts[interface_id]["snapshot_digest"]}
        for interface_id in candidate_ids
    ]
    all_refs = [ref for interface_id in candidate_ids for ref in facts[interface_id]["evidence_refs"]]
    scope = request["candidate_scope"]
    explicit = scope.get("explicit_interface_id")
    default = scope.get("default_interface_id")
    target = explicit or default or (candidate_ids[0] if len(candidate_ids) == 1 else None)
    reason = "owner.explicit" if explicit else f"{scope.get('default_source')}.default" if default else "single.eligible"
    status = "selected"
    selected = None
    alternatives = []
    rejected = []
    unknowns: list[str] = []
    cost = {"status": "unknown", "amount": None, "currency": None, "basis": "unknown", "assumptions": []}
    interface_digest = None

    if request["effective_policy"]["data_egress_allowed"] is not True:
        status = "needs_authorization"
        target = None
        unknowns.append("policy.data_egress_authorization")
    elif target is None:
        status = "needs_owner_input"
        unknowns.append("owner.preferred_interface")
        alternatives = [
            {"interface_id": interface_id, "reason_codes": ["candidate.authorized"]}
            for interface_id in candidate_ids
        ]
    else:
        target_row = next(row for row in candidates if row["interface_id"] == target)
        if target_row["provider_id"] in request["effective_policy"].get("forbidden_providers", []):
            status = "no_eligible_candidate"
            rejected.append({"interface_id": target, "reason_codes": ["policy.provider_forbidden"]})
        target_facts = facts[target]
        interface_digest = target_facts["interface_digest"]
        if status == "selected" and (target_facts["interface_digest_conflict"] or interface_digest is None):
            status = "needs_evidence"
            unknowns.append("interface.digest")
        elif status == "selected" and target_facts["price_statuses"] - _USABLE_EVIDENCE:
            status = "needs_evidence"
            unknowns.append("pricing.current_evidence")
        elif status == "selected":
            request_budget = request["budget"]
            request_limit = request_budget.get("max_request_amount")
            session_limit = request_budget.get("max_session_remaining")
            declared_limits = [
                Decimal(str(value))
                for value in (request_limit, session_limit)
                if value is not None
            ]
            budget_amount = min(declared_limits) if declared_limits else None
            currency = request_budget["currency"]
            comparable = [amount for amount, unit_currency in target_facts["prices"] if unit_currency == currency]
            if len(set(comparable)) > 1:
                status = "needs_evidence"
                unknowns.append("pricing.conflicting_amounts")
            elif comparable:
                amount = comparable[0]
                cost = {
                    "status": "known",
                    "amount": format(amount, "f"),
                    "currency": currency,
                    "basis": "currency_estimate",
                    "assumptions": ["one web.search request under the evidenced account scope"],
                }
                if budget_amount is not None and amount > budget_amount:
                    status = "no_eligible_candidate"
                    reason_code = (
                        "budget.session_exhausted"
                        if session_limit is not None and amount > Decimal(str(session_limit))
                        else "budget.exceeded"
                    )
                    rejected.append({"interface_id": target, "reason_codes": [reason_code]})
            elif budget_amount is not None or request_budget["unknown_cost_action"] == "stop":
                status = "needs_budget"
                unknowns.append("pricing.comparable_currency_amount")

        if status == "selected":
            selected = {"interface_id": target, "reason_codes": [reason, "policy.eligible"]}
            alternatives = [
                {"interface_id": interface_id, "reason_codes": ["candidate.authorized"]}
                for interface_id in candidate_ids
                if interface_id != target
            ]

    decision = {
        "contract_type": "decision_receipt",
        "contract_version": "0.2-draft",
        "decision_id": decision_id,
        "request_id": request["request_id"],
        "issued_at": issued_at,
        "valid_until": valid_until,
        "request_commitment": digest_json(request),
        "effective_policy_digest": request["effective_policy"]["policy_digest"],
        "algorithm": {"name": "bootstrap-policy", "version": "1"},
        "status": status,
        "candidates": summaries,
        "evidence_refs": sorted(all_refs, key=lambda row: row["evidence_id"]),
        "selected": selected,
        "alternatives": alternatives,
        "rejected": rejected,
        "unknowns": sorted(set(unknowns)),
        "cost_estimate": cost,
        "execution_binding": {
            "authorization_granted": False,
            "interface_digest": interface_digest if selected else None,
            "mode": request["execution"]["mode"],
        },
        "issuer": {"id": issuer_id, "signature_status": "unsigned"},
    }
    validate_contract("decision_receipt", decision)
    return decision


__all__ = ["build_bootstrap_decision"]

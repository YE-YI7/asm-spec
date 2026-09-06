"""Deterministic request-to-outcome replay for the search application draft."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .bootstrap import build_bootstrap_decision
from .contracts import ContractValidationError, validate_contract
from .digests import digest_json
from .providers import (
    ProviderResponseError,
    classify_http_error,
    normalize_provider_response,
)
from .providers.search import ADAPTER_VERSION

_UNKNOWN_MONEY = {"status": "unknown", "amount": None, "currency": None, "source": "unknown"}


def _authorized_interfaces(request: Mapping[str, Any]) -> dict[str, str]:
    scope = request.get("candidate_scope") or {}
    return {
        str(row.get("interface_id")): str(row.get("provider_id"))
        for row in scope.get("authorized_interfaces") or []
        if isinstance(row, Mapping) and row.get("interface_id")
    }


def run_search_replay(
    *,
    request: Mapping[str, Any],
    decision: Mapping[str, Any],
    provider_id: str,
    provider_payload: Mapping[str, Any],
    http_status: int = 200,
    retry_after: str | None = None,
    decision_receipt_digest: str | None = None,
    outcome_id: str,
    attempt_id: str,
    started_at: str,
    ended_at: str,
    result_commitment: str | None,
    issuer_id: str = "asm-local-replay",
    current_interface_digest: str | None = None,
    provider_error: ProviderResponseError | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    """Normalize a saved provider response and emit a conforming outcome.

    This function refuses live/shadow requests. It proves deterministic wiring,
    not a live provider call or task correctness.
    """
    validate_contract("search_request", request)
    validate_contract("decision_receipt", decision)
    if not 100 <= http_status <= 599:
        raise ValueError("http_status must be between 100 and 599")
    if (request.get("execution") or {}).get("mode") != "replay":
        raise ContractValidationError("search replay requires request.execution.mode=replay")
    if (decision.get("execution_binding") or {}).get("mode") != "replay":
        raise ContractValidationError("search replay requires decision.execution_binding.mode=replay")
    if decision.get("request_id") != request.get("request_id"):
        raise ContractValidationError("decision.request_id does not match search request")
    if decision.get("request_commitment") != digest_json(request):
        raise ContractValidationError("decision request commitment does not match search request")
    if decision.get("effective_policy_digest") != (request.get("effective_policy") or {}).get("policy_digest"):
        raise ContractValidationError("decision policy digest does not match search request")
    selected = decision.get("selected")
    if not isinstance(selected, Mapping):
        raise ContractValidationError("search replay requires a selected decision")
    interface_id = str(selected.get("interface_id") or "")
    authorized = _authorized_interfaces(request)
    if interface_id not in authorized:
        raise ContractValidationError("selected interface is not authorized by the search request")
    if authorized[interface_id] != provider_id:
        raise ContractValidationError("provider id does not match the authorized interface")
    if provider_id in (request.get("effective_policy") or {}).get("forbidden_providers", []):
        raise ContractValidationError("provider is forbidden by the effective policy")

    binding = decision.get("execution_binding") or {}
    if datetime.fromisoformat(started_at.replace("Z", "+00:00")) >= datetime.fromisoformat(
        str(decision["valid_until"]).replace("Z", "+00:00")
    ):
        raise ContractValidationError("decision expired before the provider attempt started")
    if current_interface_digest is not None and current_interface_digest != binding.get("interface_digest"):
        raise ContractValidationError("current interface digest changed; a successor decision is required")
    computed_decision_digest = digest_json(decision)
    if decision_receipt_digest is not None and decision_receipt_digest != computed_decision_digest:
        raise ContractValidationError("supplied decision receipt digest does not match the decision")
    decision_receipt_digest = computed_decision_digest
    provider_request_id = next(
        (
            provider_payload.get(key)
            for key in ("request_id", "requestId", "id")
            if isinstance(provider_payload.get(key), str)
        ),
        None,
    )
    observation = None
    failure = None
    try:
        if provider_error is not None:
            raise provider_error
        if http_status != 200:
            raise classify_http_error(
                http_status,
                str(provider_payload.get("error") or f"provider HTTP {http_status}"),
                retry_after=retry_after,
            )
        observation = normalize_provider_response(provider_id, provider_payload)
        if observation.interface_id != interface_id:
            raise ContractValidationError(
                f"provider response interface {observation.interface_id!r} does not match selected {interface_id!r}"
            )
        transport_status = observation.transport_status
        tool_status = observation.tool_status
        usage = [row.to_dict() for row in observation.usage]
        estimated_cost = observation.estimated_cost.to_dict()
        settled_cost = observation.settled_cost.to_dict()
        provider_request_id = observation.provider_request_id
        if result_commitment is None:
            result_commitment = digest_json([row.to_dict() for row in observation.results])
    except ProviderResponseError as exc:
        transport_status = exc.transport_status
        tool_status = exc.tool_status
        usage = []
        estimated_cost = dict(_UNKNOWN_MONEY)
        settled_cost = dict(_UNKNOWN_MONEY)
        result_commitment = None
        failure = {"message": str(exc), "retry_after": exc.retry_after}

    check_status = (
        "pass"
        if observation is not None and observation.results
        else "fail"
        if tool_status in {"empty_result", "invalid_result", "provider_error"}
        else "unknown"
    )
    outcome = {
        "contract_type": "outcome_receipt",
        "contract_version": "0.1-draft",
        "outcome_id": outcome_id,
        "decision_id": decision["decision_id"],
        "decision_receipt_digest": decision_receipt_digest,
        "attempt_id": attempt_id,
        "supersedes": supersedes,
        "executed": {
            "interface_id": interface_id,
            "interface_digest": binding["interface_digest"],
            "adapter_version": observation.adapter_version if observation else ADAPTER_VERSION,
            "provider_request_id": provider_request_id,
        },
        "request_commitment": decision["request_commitment"],
        "started_at": started_at,
        "ended_at": ended_at,
        "transport_status": transport_status,
        "tool_status": tool_status,
        "task_check_results": [
            {
                "check_id": "result.has_http_url",
                "status": check_status,
                "method": "deterministic",
                "evidence_ref": "normalized-results" if check_status == "pass" else None,
            }
        ],
        "usage": usage,
        "estimated_cost": estimated_cost,
        "settled_cost": settled_cost,
        "result_commitment": result_commitment,
        "issuer": {"id": issuer_id, "signature_status": "unsigned"},
    }
    validate_contract("outcome_receipt", outcome)
    return {
        "observation": observation.to_dict() if observation else None,
        "failure": failure,
        "outcome": outcome,
        "replay": True,
    }


def run_bootstrap_replay(
    *,
    request: Mapping[str, Any],
    evidence: list[Mapping[str, Any]],
    provider_id: str,
    provider_payload: Mapping[str, Any],
    decision_id: str,
    outcome_id: str,
    attempt_id: str,
    issued_at: str,
    valid_until: str,
    started_at: str,
    ended_at: str,
    http_status: int = 200,
    retry_after: str | None = None,
) -> dict[str, Any]:
    """Run the shared CLI/MCP bootstrap replay application service."""
    decision = build_bootstrap_decision(
        request=request,
        evidence=evidence,
        decision_id=decision_id,
        issued_at=issued_at,
        valid_until=valid_until,
    )
    if decision["status"] != "selected":
        return {"decision": decision, "outcome": None, "observation": None, "failure": None, "replay": True}
    execution = run_search_replay(
        request=request,
        decision=decision,
        provider_id=provider_id,
        provider_payload=provider_payload,
        http_status=http_status,
        retry_after=retry_after,
        outcome_id=outcome_id,
        attempt_id=attempt_id,
        started_at=started_at,
        ended_at=ended_at,
        result_commitment=None,
    )
    return {"decision": decision, **execution}


__all__ = ["run_bootstrap_replay", "run_search_replay"]

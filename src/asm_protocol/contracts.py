"""Load and validate versioned ASM application contracts.

These contracts sit above the stable manifest schema.  They deliberately keep
selection evidence, a recommendation, and observed execution as separate
artifacts so consumers cannot mistake one for another.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

CONTRACT_SCHEMAS = {
    "search_request": "search-request-v0.1.schema.json",
    "selection_evidence": "selection-evidence-v0.1.schema.json",
    "decision_receipt": "decision-receipt-v0.2.schema.json",
    "outcome_receipt": "outcome-receipt-v0.1.schema.json",
    "search_evaluation_task": "search-evaluation-task-v0.1.schema.json",
}


class ContractValidationError(ValueError):
    """Raised when a payload does not conform to its declared contract."""


def load_contract_schema(contract: str) -> dict[str, Any]:
    """Return one packaged JSON Schema by its stable contract name."""
    try:
        filename = CONTRACT_SCHEMAS[contract]
    except KeyError as exc:
        names = ", ".join(sorted(CONTRACT_SCHEMAS))
        raise ValueError(f"unknown ASM contract {contract!r}; expected one of: {names}") from exc
    schema_text = resources.files("asm_schema").joinpath(filename).read_text(encoding="utf-8")
    return json.loads(schema_text)


def contract_errors(contract: str, payload: Mapping[str, Any]) -> list[str]:
    """Return deterministic, human-readable validation errors."""
    schema = load_contract_schema(contract)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(dict(payload)), key=lambda error: list(error.absolute_path))
    rendered = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    rendered.extend(_semantic_errors(contract, payload))
    return rendered


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _semantic_errors(contract: str, payload: Mapping[str, Any]) -> list[str]:
    """Cross-field checks JSON Schema cannot express clearly."""
    errors: list[str] = []
    if contract == "search_request":
        scope = payload.get("candidate_scope") or {}
        parameters = payload.get("parameters") or {}
        explicit = scope.get("explicit_interface_id")
        default = scope.get("default_interface_id")
        authorized = {
            row.get("interface_id")
            for row in scope.get("authorized_interfaces") or []
            if isinstance(row, Mapping)
        }
        if explicit is not None and explicit not in authorized:
            errors.append("candidate_scope.explicit_interface_id: must be in authorized_interfaces")
        if default is not None and default not in authorized:
            errors.append("candidate_scope.default_interface_id: must be in authorized_interfaces")
        if (default is None) != (scope.get("default_source") is None):
            errors.append("candidate_scope.default_source: must be present exactly when default_interface_id is present")
        if parameters.get("allowed_domains") and parameters.get("excluded_domains"):
            errors.append("parameters: allowed_domains and excluded_domains cannot both be non-empty")
    elif contract == "selection_evidence":
        observed = _timestamp(payload.get("observed_at"))
        fetched = _timestamp(payload.get("fetched_at"))
        expires = _timestamp(payload.get("expires_at"))
        if observed and fetched and observed > fetched:
            errors.append("observed_at: must not be later than fetched_at")
        if observed and expires and observed >= expires:
            errors.append("expires_at: must be later than observed_at")
    elif contract == "decision_receipt":
        issued = _timestamp(payload.get("issued_at"))
        valid_until = _timestamp(payload.get("valid_until"))
        if issued and valid_until and issued >= valid_until:
            errors.append("valid_until: must be later than issued_at")
        selected = payload.get("selected")
        candidate_ids = {
            row.get("interface_id")
            for row in payload.get("candidates") or []
            if isinstance(row, Mapping)
        }
        if isinstance(selected, Mapping) and selected.get("interface_id") not in candidate_ids:
            errors.append("selected.interface_id: must identify a listed candidate")
        if payload.get("predecessor_decision_id") == payload.get("decision_id"):
            errors.append("predecessor_decision_id: must not equal decision_id")
    elif contract == "outcome_receipt":
        started = _timestamp(payload.get("started_at"))
        ended = _timestamp(payload.get("ended_at"))
        if started and ended and started > ended:
            errors.append("ended_at: must not be earlier than started_at")
    elif contract == "search_evaluation_task":
        checks = payload.get("checks") or {}
        temporal = checks.get("temporal_requirement")
        cutoff = checks.get("cutoff")
        if (temporal in {"before_cutoff", "after_cutoff"}) != (cutoff is not None):
            errors.append("checks.cutoff: required exactly for before_cutoff or after_cutoff")
        ground_truth = payload.get("ground_truth_ref") or {}
        time_sensitive = "time_sensitive_fact" in (payload.get("coverage_tags") or [])
        verified = _timestamp(ground_truth.get("verified_at"))
        expires = _timestamp(ground_truth.get("expires_at"))
        committed = _timestamp(payload.get("committed_at"))
        if time_sensitive and (verified is None or expires is None):
            errors.append(
                "ground_truth_ref: time-sensitive tasks require verified_at and expires_at"
            )
        if verified and expires and verified >= expires:
            errors.append("ground_truth_ref.expires_at: must be later than verified_at")
        if verified and committed and verified > committed:
            errors.append("ground_truth_ref.verified_at: must not be later than committed_at")
    return errors


def validate_contract(contract: str, payload: Mapping[str, Any]) -> None:
    """Validate *payload* or raise ``ContractValidationError``."""
    errors = contract_errors(contract, payload)
    if errors:
        raise ContractValidationError("; ".join(errors))


__all__ = [
    "CONTRACT_SCHEMAS",
    "ContractValidationError",
    "contract_errors",
    "load_contract_schema",
    "validate_contract",
]

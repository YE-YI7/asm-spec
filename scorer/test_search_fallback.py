from __future__ import annotations

import json
from pathlib import Path

import pytest

from asm_protocol.bootstrap import build_bootstrap_decision
from asm_protocol.contracts import ContractValidationError, validate_contract
from asm_protocol.digests import digest_json
from asm_protocol.fallback import plan_search_fallback
from asm_protocol.providers import ProviderResponseError
from asm_protocol.search_replay import run_search_replay

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _evidence(interface: str, provider: str, marker: str, amount: str) -> dict:
    evidence = _json("evidence.tavily-price.valid.json")
    candidate = evidence["candidate"]
    candidate.update(
        provider_id=provider,
        service_id=f"{provider}/search",
        interface_id=interface,
        interface_digest="sha256:" + marker * 64,
        endpoint={
            "tavily": "https://api.tavily.com/search",
            "exa": "https://api.exa.ai/search",
            "firecrawl": "https://api.firecrawl.dev/v2/search",
        }[provider],
    )
    evidence["evidence_id"] = f"ev-{provider}-price"
    evidence["claim"]["value"] = amount
    return evidence


def _chain() -> tuple[dict, list[dict], dict, dict]:
    request = _json("request.valid.json")
    request["candidate_scope"]["authorized_interfaces"].append(
        {
            "provider_id": "exa",
            "service_id": "exa/search",
            "interface_id": "exa/search:https-api",
            "account_ref": "host-account:exa-replay",
        }
    )
    request["execution"].update(
        deadline_ms=10000,
        max_attempts=2,
        fallback_allowlist=["exa/search:https-api"],
    )
    evidence = [
        _evidence("tavily/search:https-api", "tavily", "c", "0.008"),
        _evidence("exa/search:https-api", "exa", "e", "0.010"),
    ]
    decision = build_bootstrap_decision(
        request=request,
        evidence=evidence,
        decision_id="dec-attempt-1",
        issued_at="2026-09-05T02:00:01Z",
        valid_until="2026-09-05T02:00:09Z",
    )
    failed = run_search_replay(
        request=request,
        decision=decision,
        provider_id="tavily",
        provider_payload={"error": "rate limited"},
        http_status=429,
        retry_after="5",
        outcome_id="out-attempt-1",
        attempt_id="attempt-1",
        started_at="2026-09-05T02:00:02Z",
        ended_at="2026-09-05T02:00:03Z",
        result_commitment=None,
    )["outcome"]
    return request, evidence, decision, failed


def test_authorized_failure_creates_successor_and_second_outcome() -> None:
    request, evidence, decision, failed = _chain()
    plan = plan_search_fallback(
        request=request,
        evidence=evidence,
        previous_decision=decision,
        previous_outcomes=[failed],
        decision_id="dec-attempt-2",
        issued_at="2026-09-05T02:00:04Z",
        valid_until="2026-09-05T02:00:09Z",
        now="2026-09-05T02:00:04Z",
    )
    successor = plan["decision"]
    assert plan["status"] == "selected"
    assert successor["predecessor_decision_id"] == decision["decision_id"]
    assert successor["selected"] == {
        "interface_id": "exa/search:https-api",
        "reason_codes": ["fallback.authorized", "policy.eligible"],
    }
    validate_contract("decision_receipt", successor)

    execution = run_search_replay(
        request=request,
        decision=successor,
        provider_id="exa",
        provider_payload=_json("providers/exa.response.json"),
        outcome_id="out-attempt-2",
        attempt_id="attempt-2",
        started_at="2026-09-05T02:00:05Z",
        ended_at="2026-09-05T02:00:06Z",
        result_commitment=None,
        current_interface_digest="sha256:" + "e" * 64,
        supersedes=failed["outcome_id"],
    )
    assert execution["outcome"]["supersedes"] == failed["outcome_id"]
    assert execution["outcome"]["tool_status"] == "succeeded"


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda request: request["execution"].update(max_attempts=1), "fallback.max_attempts_reached"),
        (lambda request: request["execution"].update(fallback_allowlist=[]), "fallback.no_authorized_candidate"),
        (lambda request: request["budget"].update(max_session_remaining="0.008"), "fallback.session_budget_exhausted"),
    ],
)
def test_fallback_stops_at_authorization_attempt_and_budget_boundaries(mutation, reason) -> None:
    request, evidence, decision, failed = _chain()
    mutation(request)
    decision = build_bootstrap_decision(
        request=request,
        evidence=evidence,
        decision_id="dec-mutated",
        issued_at="2026-09-05T02:00:01Z",
        valid_until="2026-09-05T02:00:09Z",
    )
    failed["decision_id"] = decision["decision_id"]
    failed["decision_receipt_digest"] = digest_json(decision)
    failed["request_commitment"] = digest_json(request)
    plan = plan_search_fallback(
        request=request,
        evidence=evidence,
        previous_decision=decision,
        previous_outcomes=[failed],
        decision_id="dec-never",
        issued_at="2026-09-05T02:00:04Z",
        valid_until="2026-09-05T02:00:09Z",
        now="2026-09-05T02:00:04Z",
    )
    assert reason in plan["reason_codes"]
    assert plan["decision"] is None


def test_deadline_and_interface_version_changes_fail_closed() -> None:
    request, evidence, decision, failed = _chain()
    plan = plan_search_fallback(
        request=request,
        evidence=evidence,
        previous_decision=decision,
        previous_outcomes=[failed],
        decision_id="dec-late",
        issued_at="2026-09-05T02:00:10Z",
        valid_until="2026-09-05T02:00:11Z",
        now="2026-09-05T02:00:10Z",
    )
    assert plan["reason_codes"] == ["fallback.deadline_exceeded"]

    with pytest.raises(ContractValidationError, match="interface digest changed"):
        run_search_replay(
            request=request,
            decision=decision,
            provider_id="tavily",
            provider_payload=_json("providers/tavily.response.json"),
            outcome_id="out-version-change",
            attempt_id="attempt-version-change",
            started_at="2026-09-05T02:00:02Z",
            ended_at="2026-09-05T02:00:03Z",
            result_commitment=None,
            current_interface_digest="sha256:" + "f" * 64,
        )


def test_timeout_is_preserved_as_an_outcome_not_hidden_by_retry() -> None:
    request, _, decision, _ = _chain()
    execution = run_search_replay(
        request=request,
        decision=decision,
        provider_id="tavily",
        provider_payload={},
        provider_error=ProviderResponseError("timeout", "not_observed", "timed out"),
        outcome_id="out-timeout",
        attempt_id="attempt-timeout",
        started_at="2026-09-05T02:00:02Z",
        ended_at="2026-09-05T02:00:03Z",
        result_commitment=None,
    )
    assert execution["outcome"]["transport_status"] == "timeout"
    assert execution["outcome"]["tool_status"] == "not_observed"
    assert execution["failure"]["message"] == "timed out"

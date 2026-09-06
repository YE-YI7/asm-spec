from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from asm_cli import main as asm_main
from asm_protocol.contracts import ContractValidationError, validate_contract
from asm_protocol.digests import digest_json
from asm_protocol.search_replay import run_search_replay

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "contracts" / "search"
PROVIDERS = FIXTURES / "providers"
DIGEST = "sha256:" + "9" * 64


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contracts(interface_id: str, provider_id: str | None = None) -> tuple[dict, dict]:
    request = _json(FIXTURES / "request.valid.json")
    decision = _json(FIXTURES / "decision.valid.json")
    request["candidate_scope"]["authorized_interfaces"][0]["interface_id"] = interface_id
    request["candidate_scope"]["authorized_interfaces"][0]["provider_id"] = provider_id or interface_id.split("/", 1)[0]
    request["candidate_scope"]["default_interface_id"] = interface_id
    decision["candidates"][0]["interface_id"] = interface_id
    decision["selected"]["interface_id"] = interface_id
    decision["request_commitment"] = digest_json(request)
    return request, decision


def _run(provider_id: str, fixture: str, interface_id: str, **overrides):
    request, decision = _contracts(interface_id)
    arguments = {
        "request": request,
        "decision": decision,
        "provider_id": provider_id,
        "provider_payload": _json(PROVIDERS / fixture),
        "decision_receipt_digest": None,
        "outcome_id": f"out-{provider_id}-replay",
        "attempt_id": f"attempt-{provider_id}-replay",
        "started_at": "2026-09-05T02:00:11Z",
        "ended_at": "2026-09-05T02:00:12Z",
        "result_commitment": DIGEST,
    }
    arguments.update(overrides)
    return run_search_replay(**arguments)


@pytest.mark.parametrize(
    "provider_id,fixture,interface_id",
    [
        ("tavily", "tavily.response.json", "tavily/search:https-api"),
        ("exa", "exa.response.json", "exa/search:https-api"),
        ("firecrawl", "firecrawl.response.json", "firecrawl/search:https-api"),
    ],
)
def test_saved_provider_response_produces_valid_outcome(provider_id, fixture, interface_id) -> None:
    result = _run(provider_id, fixture, interface_id)
    assert result["replay"] is True
    assert result["outcome"]["tool_status"] == "succeeded"
    assert result["outcome"]["executed"]["interface_id"] == interface_id
    validate_contract("outcome_receipt", result["outcome"])


def test_empty_results_are_not_reported_as_success() -> None:
    result = _run(
        "tavily",
        "tavily.empty.response.json",
        "tavily/search:https-api",
        result_commitment=None,
    )
    assert result["outcome"]["transport_status"] == "succeeded"
    assert result["outcome"]["tool_status"] == "empty_result"
    assert result["outcome"]["task_check_results"][0]["status"] == "fail"


@pytest.mark.parametrize(
    "provider_id,fixture,interface_id,http_status,transport_status,tool_status",
    [
        ("exa", "exa.authentication-failed.response.json", "exa/search:https-api", 401, "authentication_failed", "not_observed"),
        ("exa", "exa.authentication-failed.response.json", "exa/search:https-api", 402, "billing_blocked", "not_observed"),
        ("firecrawl", "firecrawl.rate-limited.response.json", "firecrawl/search:https-api", 429, "rate_limited", "not_observed"),
        ("tavily", "tavily.invalid.response.json", "tavily/search:https-api", 200, "succeeded", "invalid_result"),
    ],
)
def test_failures_produce_outcome_receipts(
    provider_id, fixture, interface_id, http_status, transport_status, tool_status
) -> None:
    result = _run(
        provider_id,
        fixture,
        interface_id,
        http_status=http_status,
        retry_after="5" if http_status == 429 else None,
    )
    assert result["observation"] is None
    assert result["failure"] is not None
    assert result["outcome"]["transport_status"] == transport_status
    assert result["outcome"]["tool_status"] == tool_status
    assert result["outcome"]["result_commitment"] is None
    validate_contract("outcome_receipt", result["outcome"])


def test_rate_limit_preserves_retry_after_without_retrying() -> None:
    result = _run(
        "firecrawl",
        "firecrawl.rate-limited.response.json",
        "firecrawl/search:https-api",
        http_status=429,
        retry_after="7",
    )
    assert result["failure"]["retry_after"] == "7"
    assert result["outcome"]["usage"] == []


def test_replay_refuses_live_request() -> None:
    request, decision = _contracts("tavily/search:https-api")
    request["execution"]["mode"] = "live"
    with pytest.raises(ContractValidationError, match="mode=replay"):
        _run(
            "tavily",
            "tavily.response.json",
            "tavily/search:https-api",
            request=request,
            decision=decision,
        )


def test_replay_refuses_policy_mismatch() -> None:
    request, decision = _contracts("exa/search:https-api")
    decision["effective_policy_digest"] = "sha256:" + "8" * 64
    with pytest.raises(ContractValidationError, match="policy digest"):
        _run("exa", "exa.response.json", "exa/search:https-api", request=request, decision=decision)


def test_replay_refuses_unselected_provider_interface() -> None:
    request, decision = _contracts("tavily/search:https-api", provider_id="exa")
    with pytest.raises(ContractValidationError, match="does not match selected"):
        _run(
            "exa",
            "exa.response.json",
            "tavily/search:https-api",
            request=copy.deepcopy(request),
            decision=copy.deepcopy(decision),
        )


def test_replay_refuses_provider_id_aliasing() -> None:
    request, decision = _contracts("tavily/search:https-api", provider_id="exa")
    with pytest.raises(ContractValidationError, match="provider id"):
        _run(
            "tavily",
            "tavily.response.json",
            "tavily/search:https-api",
            request=request,
            decision=decision,
        )


def test_replay_rechecks_forbidden_provider_policy() -> None:
    request, decision = _contracts("tavily/search:https-api")
    request["effective_policy"]["forbidden_providers"] = ["tavily"]
    decision["request_commitment"] = digest_json(request)
    with pytest.raises(ContractValidationError, match="forbidden"):
        _run(
            "tavily",
            "tavily.response.json",
            "tavily/search:https-api",
            request=request,
            decision=decision,
        )


def test_cli_runs_request_to_outcome_replay(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    request, decision = _contracts("tavily/search:https-api")
    request_path = tmp_path / "request.json"
    decision_path = tmp_path / "decision.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    exit_code = asm_main(
        [
            "search", "replay",
            "--provider", "tavily",
            "--request", str(request_path),
            "--decision", str(decision_path),
            "--response", str(PROVIDERS / "tavily.response.json"),
            "--result-digest", DIGEST,
            "--outcome-id", "out-cli-replay",
            "--attempt-id", "attempt-cli-replay",
            "--started-at", "2026-09-05T02:00:11Z",
            "--ended-at", "2026-09-05T02:00:12Z",
        ]
    )
    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["replay"] is True
    assert output["outcome"]["tool_status"] == "succeeded"

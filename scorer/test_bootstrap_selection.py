from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from asm_cli import main as asm_main
from asm_protocol.bootstrap import build_bootstrap_decision
from asm_protocol.contracts import validate_contract
from asm_protocol.digests import digest_json

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _decision(request: dict, evidence: list[dict]) -> dict:
    return build_bootstrap_decision(
        request=request,
        evidence=evidence,
        decision_id="dec-bootstrap-test",
        issued_at="2026-09-05T02:00:10Z",
        valid_until="2026-09-05T02:05:10Z",
    )


def test_host_default_selects_without_asking_for_weights() -> None:
    request = _json("request.valid.json")
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["status"] == "selected"
    assert result["selected"]["interface_id"] == "tavily/search:https-api"
    assert result["selected"]["reason_codes"] == ["host_configuration.default", "policy.eligible"]
    assert result["cost_estimate"]["amount"] == "0.008"
    assert result["request_commitment"] == digest_json(request)
    validate_contract("decision_receipt", result)


def test_explicit_choice_takes_precedence_over_default() -> None:
    request = _json("request.valid.json")
    request["candidate_scope"]["explicit_interface_id"] = "tavily/search:https-api"
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["selected"]["reason_codes"][0] == "owner.explicit"


def test_no_default_with_multiple_candidates_abstains() -> None:
    request = _json("request.valid.json")
    scope = request["candidate_scope"]
    scope["default_interface_id"] = None
    scope["default_source"] = None
    scope["authorized_interfaces"].append(
        {
            "provider_id": "exa",
            "service_id": "exa/search",
            "interface_id": "exa/search:https-api",
            "account_ref": "host-account:exa-replay",
        }
    )
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["status"] == "needs_owner_input"
    assert result["selected"] is None
    assert {row["interface_id"] for row in result["alternatives"]} == {
        "tavily/search:https-api",
        "exa/search:https-api",
    }


def test_data_egress_block_abstains_before_selection() -> None:
    request = _json("request.valid.json")
    request["effective_policy"]["data_egress_allowed"] = False
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["status"] == "needs_authorization"
    assert result["selected"] is None


def test_unknown_price_stops_when_budget_is_bounded() -> None:
    request = _json("request.valid.json")
    result = _decision(request, [])
    assert result["status"] == "needs_evidence"
    assert "interface.digest" in result["unknowns"]


def test_credit_only_evidence_is_not_treated_as_usd() -> None:
    request = _json("request.valid.json")
    evidence = _json("evidence.tavily-price.valid.json")
    evidence["claim"].update(value="1", unit="credit/request", value_kind="credit", currency=None)
    result = _decision(request, [evidence])
    assert result["status"] == "needs_budget"
    assert result["cost_estimate"]["amount"] is None


def test_expired_price_requires_evidence_refresh() -> None:
    request = _json("request.valid.json")
    evidence = _json("evidence.tavily-price.valid.json")
    evidence["status"] = "expired"
    result = _decision(request, [evidence])
    assert result["status"] == "needs_evidence"
    assert "pricing.current_evidence" in result["unknowns"]


def test_price_over_budget_rejects_candidate() -> None:
    request = _json("request.valid.json")
    request["budget"]["max_request_amount"] = "0.001"
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["status"] == "no_eligible_candidate"
    assert result["rejected"][0]["reason_codes"] == ["budget.exceeded"]


def test_effective_policy_forbidden_provider_cannot_be_selected() -> None:
    request = _json("request.valid.json")
    request["effective_policy"]["forbidden_providers"] = ["tavily"]
    result = _decision(request, [_json("evidence.tavily-price.valid.json")])
    assert result["status"] == "no_eligible_candidate"
    assert result["selected"] is None
    assert result["rejected"][0]["reason_codes"] == ["policy.provider_forbidden"]


def test_conflicting_interface_digests_require_evidence() -> None:
    request = _json("request.valid.json")
    first = _json("evidence.tavily-price.valid.json")
    second = copy.deepcopy(first)
    second["evidence_id"] = "ev-tavily-conflicting-interface"
    second["candidate"]["interface_digest"] = "sha256:" + "7" * 64
    result = _decision(request, [first, second])
    assert result["status"] == "needs_evidence"
    assert "interface.digest" in result["unknowns"]


def test_cli_builds_decision_without_caller_authored_weights(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = asm_main(
        [
            "search", "decide",
            "--request", str(FIXTURES / "request.valid.json"),
            "--evidence", str(FIXTURES / "evidence.tavily-price.valid.json"),
            "--decision-id", "dec-cli-bootstrap",
            "--issued-at", "2026-09-05T02:00:10Z",
            "--valid-until", "2026-09-05T02:05:10Z",
        ]
    )
    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "selected"
    assert result["algorithm"] == {"name": "bootstrap-policy", "version": "1"}


def test_cli_runs_full_bootstrap_replay_chain(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = asm_main(
        [
            "search", "run-replay",
            "--provider", "tavily",
            "--request", str(FIXTURES / "request.valid.json"),
            "--evidence", str(FIXTURES / "evidence.tavily-price.valid.json"),
            "--response", str(FIXTURES / "providers" / "tavily.response.json"),
            "--decision-id", "dec-full-replay",
            "--outcome-id", "out-full-replay",
            "--attempt-id", "attempt-full-replay",
            "--issued-at", "2026-09-05T02:00:10Z",
            "--valid-until", "2026-09-05T02:05:10Z",
            "--started-at", "2026-09-05T02:00:11Z",
            "--ended-at", "2026-09-05T02:00:12Z",
        ]
    )
    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["status"] == "selected"
    assert result["outcome"]["tool_status"] == "succeeded"
    assert result["outcome"]["result_commitment"].startswith("sha256:")


def test_full_replay_stops_before_response_when_budget_is_insufficient(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request = _json("request.valid.json")
    request["budget"]["max_request_amount"] = "0.001"
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    exit_code = asm_main(
        [
            "search", "run-replay",
            "--provider", "tavily",
            "--request", str(request_path),
            "--evidence", str(FIXTURES / "evidence.tavily-price.valid.json"),
            "--response", str(FIXTURES / "providers" / "tavily.response.json"),
            "--decision-id", "dec-budget-stop",
            "--outcome-id", "out-must-not-exist",
            "--attempt-id", "attempt-must-not-exist",
            "--issued-at", "2026-09-05T02:00:10Z",
            "--valid-until", "2026-09-05T02:05:10Z",
            "--started-at", "2026-09-05T02:00:11Z",
            "--ended-at", "2026-09-05T02:00:12Z",
        ]
    )
    assert exit_code == 3
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["status"] == "no_eligible_candidate"
    assert result["outcome"] is None

from __future__ import annotations

import copy
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import asm_select_api as api
from asm_cli import main as asm_main
from asm_protocol.contracts import (
    CONTRACT_SCHEMAS,
    contract_errors,
    load_contract_schema,
    validate_contract,
)
from asm_selector_mcp import validate_application_contract

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "contracts" / "search"


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


@pytest.mark.parametrize("contract", sorted(CONTRACT_SCHEMAS))
def test_application_contract_schema_is_valid(contract: str) -> None:
    filename = CONTRACT_SCHEMAS[contract]
    raw = (ROOT / "schema" / filename).read_text(encoding="utf-8")
    json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    Draft202012Validator.check_schema(load_contract_schema(contract))


@pytest.mark.parametrize(
    "contract,filename",
    [
        ("search_request", "request.valid.json"),
        ("selection_evidence", "evidence.current.valid.json"),
        ("selection_evidence", "evidence.unknown.valid.json"),
        ("selection_evidence", "evidence.conflicting.valid.json"),
        ("selection_evidence", "evidence.expired.valid.json"),
        ("decision_receipt", "decision.valid.json"),
        ("outcome_receipt", "outcome.valid.json"),
    ],
)
def test_golden_contract_fixture_is_valid(contract: str, filename: str) -> None:
    payload = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    validate_contract(contract, payload)


def test_unknown_evidence_cannot_smuggle_a_value() -> None:
    payload = json.loads((FIXTURES / "evidence.unknown.valid.json").read_text(encoding="utf-8"))
    payload["claim"]["value"] = "0.00"
    assert contract_errors("selection_evidence", payload)


def test_conflicting_evidence_requires_a_conflict_reference() -> None:
    payload = json.loads((FIXTURES / "evidence.conflicting.valid.json").read_text(encoding="utf-8"))
    payload.pop("conflicts_with")
    assert contract_errors("selection_evidence", payload)


def test_decision_is_not_execution_authorization() -> None:
    payload = json.loads((FIXTURES / "decision.valid.json").read_text(encoding="utf-8"))
    payload["execution_binding"]["authorization_granted"] = True
    assert contract_errors("decision_receipt", payload)


def test_non_selected_decision_cannot_name_a_selected_interface() -> None:
    payload = json.loads((FIXTURES / "decision.valid.json").read_text(encoding="utf-8"))
    payload["status"] = "needs_evidence"
    assert contract_errors("decision_receipt", payload)


def test_credit_usage_cannot_be_labeled_as_currency_estimate() -> None:
    payload = json.loads((FIXTURES / "evidence.current.valid.json").read_text(encoding="utf-8"))
    payload["claim"].update(value="2", unit="credit/request", value_kind="credit", currency=None)
    validate_contract("selection_evidence", payload)


def test_contract_cli_uses_packaged_schema(capsys: pytest.CaptureFixture[str]) -> None:
    path = FIXTURES / "request.valid.json"
    assert asm_main(["contract", "validate", "--type", "search_request", str(path)]) == 0
    assert capsys.readouterr().out.startswith("PASS search_request:")


def test_contract_validator_does_not_mutate_payload() -> None:
    payload = json.loads((FIXTURES / "outcome.valid.json").read_text(encoding="utf-8"))
    before = copy.deepcopy(payload)
    validate_contract("outcome_receipt", payload)
    assert payload == before


def test_mcp_contract_consumer_uses_shared_validator() -> None:
    payload = json.loads((FIXTURES / "evidence.unknown.valid.json").read_text(encoding="utf-8"))
    assert validate_application_contract("selection_evidence", payload)["valid"] is True
    payload["claim"]["value"] = "not actually unknown"
    assert validate_application_contract("selection_evidence", payload)["valid"] is False


def test_http_contract_consumer_uses_shared_validator() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.loads((FIXTURES / "outcome.valid.json").read_text(encoding="utf-8"))
        body = json.dumps({"type": "outcome_receipt", "payload": payload}).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/contracts/validate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
        assert result["valid"] is True
        assert result["meaning"].startswith("schema conformance only")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    "path,required_text",
    [
        ("/services/tavily-search", "Evidence insufficient"),
        ("/services/exa-search", "provider estimate"),
        ("/services/firecrawl-search", "search-only"),
        ("/methods/web-search-replay-v0.1", "Replay is not a live benchmark"),
        ("/runs/replay-search-example", "Replay, not live"),
    ],
)
def test_public_evidence_pages_are_served_with_honest_labels(path: str, required_text: str) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
            body = response.read().decode("utf-8")
        assert response.headers.get_content_type() == "text/html"
        assert required_text in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_explicit_interface_must_be_authorized() -> None:
    payload = json.loads((FIXTURES / "request.valid.json").read_text(encoding="utf-8"))
    payload["candidate_scope"]["explicit_interface_id"] = "unapproved/interface"
    assert contract_errors("search_request", payload)


def test_evidence_timestamp_order_is_checked() -> None:
    payload = json.loads((FIXTURES / "evidence.current.valid.json").read_text(encoding="utf-8"))
    payload["expires_at"] = "2026-09-01T00:00:00Z"
    assert contract_errors("selection_evidence", payload)


def test_selected_interface_must_be_a_candidate() -> None:
    payload = json.loads((FIXTURES / "decision.valid.json").read_text(encoding="utf-8"))
    payload["selected"]["interface_id"] = "missing/interface"
    assert contract_errors("decision_receipt", payload)


def test_outcome_timestamp_order_is_checked() -> None:
    payload = json.loads((FIXTURES / "outcome.valid.json").read_text(encoding="utf-8"))
    payload["ended_at"] = "2026-09-05T01:59:00Z"
    assert contract_errors("outcome_receipt", payload)


def test_frozen_search_evaluation_task_uses_shared_contract() -> None:
    payload = json.loads((FIXTURES / "evaluation-task.valid.json").read_text(encoding="utf-8"))
    validate_contract("search_evaluation_task", payload)
    payload["checks"]["temporal_requirement"] = "before_cutoff"
    assert contract_errors("search_evaluation_task", payload) == [
        "checks.cutoff: required exactly for before_cutoff or after_cutoff"
    ]

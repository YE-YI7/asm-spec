from __future__ import annotations

import json
from pathlib import Path

from asm_protocol.bootstrap import build_bootstrap_decision
from asm_protocol.observation_store import (
    append_private_observation,
    read_private_observations,
)
from asm_protocol.search_replay import run_search_replay

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _failed_outcome() -> dict:
    request = _json("request.valid.json")
    decision = build_bootstrap_decision(
        request=request,
        evidence=[_json("evidence.tavily-price.valid.json")],
        decision_id="dec-worker-a",
        issued_at="2026-09-05T02:00:01Z",
        valid_until="2026-09-05T02:00:09Z",
    )
    return run_search_replay(
        request=request,
        decision=decision,
        provider_id="tavily",
        provider_payload={"error": "rate limited"},
        http_status=429,
        outcome_id="out-worker-a",
        attempt_id="attempt-worker-a",
        started_at="2026-09-05T02:00:02Z",
        ended_at="2026-09-05T02:00:03Z",
        result_commitment=None,
    )["outcome"]


def test_worker_b_can_read_worker_a_failure_only_inside_same_owner_scope(tmp_path: Path) -> None:
    fixture = _json("multi-worker-failure.fixture.json")
    outcome = _failed_outcome()
    append_private_observation(
        tmp_path,
        owner_scope_id=fixture["owner_scope_id"],
        worker_id=fixture["producer"]["worker_id"],
        outcome=outcome,
    )
    same_owner = read_private_observations(
        tmp_path,
        owner_scope_id=fixture["owner_scope_id"],
        interface_id=fixture["producer"]["interface_id"],
        interface_digest=fixture["producer"]["interface_digest"],
    )
    other_owner = read_private_observations(
        tmp_path,
        owner_scope_id="opaque-owner-b",
        interface_id="tavily/search:https-api",
    )
    assert same_owner[0]["worker_id"] == fixture["producer"]["worker_id"]
    assert same_owner[0]["transport_status"] == fixture["producer"]["transport_status"]
    assert len(same_owner) == fixture["consumer"]["same_owner_expected_records"]
    assert len(other_owner) == fixture["consumer"]["different_owner_expected_records"]


def test_old_interface_observation_does_not_apply_to_new_version(tmp_path: Path) -> None:
    outcome = _failed_outcome()
    append_private_observation(
        tmp_path,
        owner_scope_id="opaque-owner-a",
        worker_id="worker-a",
        outcome=outcome,
    )
    records = read_private_observations(
        tmp_path,
        owner_scope_id="opaque-owner-a",
        interface_digest="sha256:" + "d" * 64,
    )
    assert records == []

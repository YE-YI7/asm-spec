from __future__ import annotations

import copy
import json
import stat
from pathlib import Path

import pytest

from asm_protocol.bootstrap import build_bootstrap_decision
from asm_protocol.run_store import store_run
from asm_protocol.search_replay import run_search_replay

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _run_pair() -> tuple[dict, dict]:
    request = _json("request.valid.json")
    decision = build_bootstrap_decision(
        request=request,
        evidence=[_json("evidence.tavily-price.valid.json")],
        decision_id="dec-store-test",
        issued_at="2026-09-05T02:00:10Z",
        valid_until="2026-09-05T02:05:10Z",
    )
    execution = run_search_replay(
        request=request,
        decision=decision,
        provider_id="tavily",
        provider_payload=_json("providers/tavily.response.json"),
        outcome_id="out-store-test",
        attempt_id="attempt-store-test",
        started_at="2026-09-05T02:00:11Z",
        ended_at="2026-09-05T02:00:12Z",
        result_commitment=None,
    )
    return decision, execution


def test_private_run_store_is_atomic_and_idempotent(tmp_path: Path) -> None:
    decision, execution = _run_pair()
    directory = tmp_path / "runs"
    first = store_run(
        directory,
        decision=decision,
        outcome=execution["outcome"],
        observation=execution["observation"],
    )
    second = store_run(
        directory,
        decision=decision,
        outcome=execution["outcome"],
        observation=execution["observation"],
    )
    assert first == second
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(first.stat().st_mode) == 0o600
    record = json.loads(first.read_text(encoding="utf-8"))
    assert record["outcome"]["outcome_id"] == "out-store-test"


def test_same_outcome_id_with_different_content_is_rejected(tmp_path: Path) -> None:
    decision, execution = _run_pair()
    store_run(tmp_path, decision=decision, outcome=execution["outcome"], observation=execution["observation"])
    changed = copy.deepcopy(execution["outcome"])
    changed["issuer"]["id"] = "different-issuer"
    with pytest.raises(FileExistsError, match="different content"):
        store_run(tmp_path, decision=decision, outcome=changed, observation=execution["observation"])


def test_raw_query_or_credentials_are_rejected(tmp_path: Path) -> None:
    decision, execution = _run_pair()
    observation = dict(execution["observation"])
    observation["query"] = "private query"
    with pytest.raises(ValueError, match="sensitive field"):
        store_run(tmp_path, decision=decision, outcome=execution["outcome"], observation=observation)

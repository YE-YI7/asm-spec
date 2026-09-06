from __future__ import annotations

import json
import stat

import pytest

from asm_protocol.contracts import validate_contract
from asm_protocol.evaluation_contributions import (
    commit_external_contribution,
    store_private_contribution,
    verify_private_contribution,
)


def _contribution() -> dict:
    return {
        "contribution_id": "contrib-001",
        "task_family": "external.chinese_current_fact",
        "coverage_tags": ["chinese_query", "time_sensitive_fact"],
        "language": "zh-CN",
        "ground_truth_verified_at": "2026-09-06T04:55:00Z",
        "ground_truth_expires_at": "2026-09-07T04:55:00Z",
        "query": "这是一条不会写入公开任务的真实问题吗？",
        "answer": "这是不会写入公开任务的参考答案。",
        "reference_urls": ["https://example.com/source"],
        "temporal_requirement": "current_at_run",
        "cutoff": None,
        "permission": {
            "evaluation_use_granted": True,
            "publish_commitments_granted": True,
            "submitter_has_authority": True,
            "contains_personal_data": False,
            "terms_version": "asm-search-evaluation-contribution-terms/0.1",
        },
    }


def _commit(contribution: dict | None = None) -> dict:
    return commit_external_contribution(
        contribution or _contribution(),
        batch_id="pilot-001",
        split="held_out",
        received_at="2026-09-06T05:00:00Z",
        committed_at="2026-09-06T05:05:00Z",
        judge_profile="asm-search-blinded-judge/v0.1-unfrozen",
    )


def test_external_contribution_publishes_only_commitments() -> None:
    committed = _commit()
    public_task = committed["public_task"]
    validate_contract("search_evaluation_task", public_task)
    serialized = json.dumps(public_task, ensure_ascii=False)

    assert public_task["source_provenance"]["kind"] == "external_contribution"
    assert public_task["query_ref"]["disclosure"] == "private"
    assert public_task["ground_truth_ref"]["disclosure"] == "private"
    assert "真实问题" not in serialized
    assert "参考答案" not in serialized
    assert "example.com" not in serialized
    assert "contrib-001" not in serialized
    assert "pilot-001" not in serialized
    assert committed["private_record"]["at_rest_protection"].endswith("not-encrypted")
    verify_private_contribution(public_task, committed["private_record"])


def test_external_contribution_detects_public_private_mismatch() -> None:
    committed = _commit()
    committed["private_record"]["contribution"]["answer"] = "tampered"

    with pytest.raises(ValueError, match="private payload"):
        verify_private_contribution(committed["public_task"], committed["private_record"])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("evaluation_use_granted", False, "evaluation use"),
        ("publish_commitments_granted", False, "publish commitments"),
        ("submitter_has_authority", False, "authority"),
        ("contains_personal_data", True, "personal-data"),
    ],
)
def test_external_contribution_fails_closed_on_permission(
    field: str, value: bool, message: str
) -> None:
    contribution = _contribution()
    contribution["permission"][field] = value

    with pytest.raises(ValueError, match=message):
        _commit(contribution)


def test_multi_source_contribution_requires_two_domains() -> None:
    contribution = _contribution()
    contribution["coverage_tags"].append("multi_source_verification")

    with pytest.raises(ValueError, match="at least 2"):
        _commit(contribution)


def test_time_sensitive_contribution_requires_a_valid_truth_window() -> None:
    contribution = _contribution()
    del contribution["ground_truth_verified_at"]
    with pytest.raises(TypeError, match="ground_truth_verified_at"):
        _commit(contribution)

    contribution = _contribution()
    contribution["ground_truth_expires_at"] = contribution["ground_truth_verified_at"]
    with pytest.raises(ValueError, match="must be later"):
        _commit(contribution)


def test_private_contribution_store_is_owner_only_and_idempotent(tmp_path) -> None:
    private_record = _commit()["private_record"]

    path = store_private_contribution(tmp_path / "private", private_record)
    repeated = store_private_contribution(tmp_path / "private", private_record)

    assert repeated == path
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert "真实问题" in path.read_text(encoding="utf-8")

    changed = {**private_record, "public_task_digest": "sha256:" + "0" * 64}
    with pytest.raises(FileExistsError, match="different private content"):
        store_private_contribution(tmp_path / "private", changed)

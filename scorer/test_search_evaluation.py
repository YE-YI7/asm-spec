from __future__ import annotations

import pytest

from asm_protocol.digests import digest_json
from asm_protocol.evaluation import (
    cluster_bootstrap_pass_delta,
    evaluate_frozen_quality,
    exact_answer_support,
    exact_mcnemar,
    validate_frozen_quality_plan,
)


def test_exact_answer_support_is_conservative_and_provider_blind() -> None:
    results = [
        {"rank": 1, "title": "Unrelated", "snippet": "No answer here"},
        {"rank": 2, "title": "Record", "snippet": "The answer was François de Malherbe."},
    ]
    assert exact_answer_support("François de Malherbe", results) == {
        "status": "pass",
        "method": "normalized_exact_answer",
        "rank": 2,
    }
    assert exact_answer_support("Different person", results)["status"] == "unresolved"
    assert exact_answer_support(
        "Apple", [{"rank": 1, "title": "Applewood", "snippet": "restaurant"}]
    )["status"] == "unresolved"


def test_exact_mcnemar_uses_only_discordant_pairs() -> None:
    result = exact_mcnemar([True] * 10, [False] * 10)
    assert result == {
        "baseline_only_pass": 10,
        "asm_only_pass": 0,
        "discordant_pairs": 10,
        "two_sided_exact_p": 0.001953125,
    }


def test_cluster_bootstrap_is_seeded_and_clustered() -> None:
    rows = [
        {"task_family": "docs", "baseline_pass": False, "asm_pass": True},
        {"task_family": "docs", "baseline_pass": True, "asm_pass": True},
        {"task_family": "news", "baseline_pass": False, "asm_pass": False},
        {"task_family": "news", "baseline_pass": True, "asm_pass": False},
    ]
    first = cluster_bootstrap_pass_delta(rows, iterations=1000, seed=7)
    second = cluster_bootstrap_pass_delta(rows, iterations=1000, seed=7)
    assert first == second
    assert first["delta"] == 0.0
    assert first["ci95_lower"] <= 0 <= first["ci95_upper"]


REQUIRED_TAGS = [
    "official_documentation",
    "time_sensitive_fact",
    "multi_source_verification",
    "chinese_query",
    "english_query",
]
JUDGE = "asm-search-blinded-judge/v1.0"


def _plan(task_set_digest: str) -> dict:
    return {
        "status": "frozen",
        "frozen_at": "2026-09-06T02:00:00Z",
        "primary_objective": "pass_rate_improvement",
        "task_set_digest": task_set_digest,
        "budget_authorized": True,
        "provider_versions": {"baseline": "api-2026-09-01", "asm": "adapter-0.1"},
        "judge_profile": JUDGE,
        "required_coverage_tags": REQUIRED_TAGS,
        "minimum_external_contribution_rows": 1,
    }


def _task(index: int, split: str) -> dict:
    digest = "sha256:" + f"{index:064x}"[-64:]
    if index == 0:
        source_provenance = {
            "kind": "external_contribution",
            "contribution_digest": digest,
            "batch_digest": digest,
            "private_payload_digest": digest,
            "permission_digest": digest,
            "reference_set_digest": digest,
            "received_at": "2026-09-06T00:30:00Z",
        }
    else:
        source_provenance = {
            "kind": "benchmark_dataset",
            "name": "synthetic test fixture",
            "version": "fixture-v1",
            "source_url": "https://example.com/fixture.csv",
            "license": "test-only",
            "snapshot_digest": digest,
            "row_id": str(index),
        }
    return {
        "contract_type": "search_evaluation_task",
        "contract_version": "0.1",
        "task_id": f"task-{index}",
        "task_family": f"family-{index % 10}",
        "split": split,
        "coverage_tags": REQUIRED_TAGS,
        "language": "en",
        "query_ref": {"digest": digest, "disclosure": "private"},
        "source_provenance": source_provenance,
        "ground_truth_ref": {
            "digest": digest,
            "disclosure": "private",
            "verified_at": "2026-09-06T00:50:00Z",
            "expires_at": "2026-09-06T04:00:00Z",
        },
        "checks": {
            "reference_domains": [],
            "domain_requirement": "none",
            "minimum_independent_sources": 1,
            "temporal_requirement": "current_at_run",
            "cutoff": None,
            "judge_profile": JUDGE,
        },
        "committed_at": "2026-09-06T01:00:00Z",
    }


def _row(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "task_family": task["task_family"],
        "baseline_pass": False,
        "asm_pass": True,
        "split": task["split"],
        "constraint_violations": 0,
        "observed_at": "2026-09-06T02:30:00Z",
    }


def test_unfrozen_or_small_plan_cannot_emit_quality_result() -> None:
    one_task = [_task(0, "held_out")]
    rows = [_row(one_task[0])]
    digest = digest_json({"tasks": one_task})
    with pytest.raises(ValueError, match="must be frozen"):
        validate_frozen_quality_plan(
            {"status": "draft_unfrozen", "primary_objective": None},
            rows,
            task_snapshot={"tasks": one_task, "task_set_digest": digest},
            evaluated_at="2026-09-06T03:00:00Z",
        )
    with pytest.raises(ValueError, match="at least 60"):
        validate_frozen_quality_plan(
            _plan(digest),
            rows,
            task_snapshot={"tasks": one_task, "task_set_digest": digest},
            evaluated_at="2026-09-06T03:00:00Z",
        )


def test_frozen_plan_must_bind_exact_task_set() -> None:
    tasks = [
        _task(index, "held_out" if index < 20 else "development")
        for index in range(60)
    ]
    rows = [_row(task) for task in tasks]
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan = _plan("sha256:" + "1" * 64)
    with pytest.raises(ValueError, match="exact task-set digest"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )
    plan["task_set_digest"] = snapshot["task_set_digest"]
    validate_frozen_quality_plan(
        plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
    )


def test_frozen_plan_rejects_missing_external_or_coverage() -> None:
    tasks = [_task(index, "held_out" if index < 20 else "development") for index in range(60)]
    rows = [_row(task) for task in tasks]
    tasks[0]["source_provenance"]["kind"] = "benchmark_dataset"
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan = _plan(snapshot["task_set_digest"])
    with pytest.raises(ValueError, match="external contribution"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )

    tasks[0]["source_provenance"]["kind"] = "external_contribution"
    for task in tasks:
        task["coverage_tags"] = ["english_query"]
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan["task_set_digest"] = snapshot["task_set_digest"]
    with pytest.raises(ValueError, match="missing required coverage"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )


def test_frozen_plan_rejects_postdated_freeze_and_late_task_commit() -> None:
    tasks = [_task(index, "held_out" if index < 20 else "development") for index in range(60)]
    rows = [_row(task) for task in tasks]
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan = _plan(snapshot["task_set_digest"])
    plan["frozen_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="later than evaluated_at"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )

    plan["frozen_at"] = "2026-09-06T02:00:00Z"
    tasks[0]["committed_at"] = "2026-09-06T02:30:00Z"
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan["task_set_digest"] = snapshot["task_set_digest"]
    with pytest.raises(ValueError, match="committed no later"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )


def test_quality_report_runs_only_through_validated_bound_snapshot() -> None:
    tasks = [_task(index, "held_out" if index < 20 else "development") for index in range(60)]
    rows = [_row(task) for task in tasks]
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    report = evaluate_frozen_quality(
        _plan(snapshot["task_set_digest"]),
        rows,
        task_snapshot=snapshot,
        evaluated_at="2026-09-06T03:00:00Z",
        bootstrap_iterations=1000,
        bootstrap_seed=7,
    )
    assert report["task_set_digest"] == snapshot["task_set_digest"]
    assert report["sample_size"] == 60
    assert report["asm_pass_rate"] == 1.0


def test_frozen_plan_binds_result_observation_time() -> None:
    tasks = [_task(index, "held_out" if index < 20 else "development") for index in range(60)]
    rows = [_row(task) for task in tasks]
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan = _plan(snapshot["task_set_digest"])

    rows[0]["observed_at"] = "2026-09-06T04:30:00Z"
    with pytest.raises(ValueError, match="between frozen_at and evaluated_at"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )


def test_frozen_plan_rejects_stale_or_post_committed_time_sensitive_truth() -> None:
    tasks = [_task(index, "held_out" if index < 20 else "development") for index in range(60)]
    rows = [_row(task) for task in tasks]

    tasks[0]["ground_truth_ref"]["expires_at"] = "2026-09-06T02:20:00Z"
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan = _plan(snapshot["task_set_digest"])
    with pytest.raises(ValueError, match="valid when the task result is observed"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )

    tasks[0]["ground_truth_ref"]["expires_at"] = "2026-09-06T04:00:00Z"
    tasks[0]["ground_truth_ref"]["verified_at"] = "2026-09-06T01:30:00Z"
    snapshot = {"tasks": tasks, "task_set_digest": digest_json({"tasks": tasks})}
    plan["task_set_digest"] = snapshot["task_set_digest"]
    with pytest.raises(ValueError, match="must not be later than committed_at"):
        validate_frozen_quality_plan(
            plan, rows, task_snapshot=snapshot, evaluated_at="2026-09-06T03:00:00Z"
        )

import pytest

from benchmark.aggregate import (
    bootstrap_ci,
    mcnemar_exact,
    paired_stats,
    validate_result_documents,
)


def test_mcnemar_exact_uses_only_discordant_pairs():
    result = mcnemar_exact([False] * 10, [True] * 10)
    assert result == {
        "left_only": 0,
        "right_only": 10,
        "discordant": 10,
        "p_value": pytest.approx(0.001953125),
    }


def test_bootstrap_ci_is_exact_for_constant_task_effect():
    assert bootstrap_ci([1.0] * 8, seed="constant") == (1.0, 1.0)


def test_paired_stats_respects_task_pairing():
    tasks = [
        {"task_id": "a", "ground_truth": {"correct": ["x"], "violations_if": {}}},
        {"task_id": "b", "ground_truth": {"correct": ["y"], "violations_if": {}}},
    ]
    stats = paired_stats(
        tasks,
        {"a": "no", "b": "y"},
        {"a": "x", "b": "y"},
        "correct",
        seed="paired",
        )
    assert stats["left_rate"] == 0.5
    assert stats["right_rate"] == 1.0
    assert stats["delta"] == 0.5
    assert stats["mcnemar"]["right_only"] == 1


def test_result_validation_rejects_partial_runs():
    tasks = [{"task_id": "a"}, {"task_id": "b"}]
    data = {"llm:x": {"asm": {"picks": {"a": "service"}}}}
    with pytest.raises(ValueError, match="complete 2-task dataset"):
        validate_result_documents(data, tasks)

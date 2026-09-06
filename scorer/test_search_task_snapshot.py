from __future__ import annotations

import csv
from pathlib import Path

from asm_protocol.contracts import validate_contract
from experiments.search_evaluation.build_simpleqa_snapshot import build_snapshot


def _source(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metadata", "problem", "answer"])
        writer.writeheader()
        for index in range(12):
            writer.writerow(
                {
                    "metadata": repr(
                        {
                            "topic": "History" if index % 2 else "Science",
                            "urls": [f"https://source{index % 3}.example/item/{index}"],
                        }
                    ),
                    "problem": f"Question {index}?",
                    "answer": f"Answer {index}",
                }
            )


def test_simpleqa_snapshot_is_deterministic_stratified_and_content_committed(tmp_path: Path) -> None:
    source = tmp_path / "simpleqa.csv"
    _source(source)
    first = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")
    second = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")
    assert first == second
    assert first["task_count"] == 9
    assert first["held_out_count"] == 3
    assert first["build_algorithm"].endswith("/v1")
    assert first["task_set_digest"].startswith("sha256:")
    assert {task["task_family"] for task in first["tasks"]} == {"simpleqa.history", "simpleqa.science"}
    assert sorted(
        sum(task["split"] == "held_out" for task in first["tasks"] if task["task_family"] == family)
        for family in {task["task_family"] for task in first["tasks"]}
    ) == [1, 2]
    assert all("problem" not in task and "answer" not in task for task in first["tasks"])
    for task in first["tasks"]:
        validate_contract("search_evaluation_task", task)

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from asm_protocol.benchmark_control import load_committed_simpleqa_rows
from experiments.search_evaluation.build_simpleqa_snapshot import build_snapshot


def _source(path: Path, *, answer_suffix: str = "") -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metadata", "problem", "answer"])
        writer.writeheader()
        for index in range(12):
            writer.writerow(
                {
                    "metadata": repr(
                        {"topic": f"Topic {index % 3}", "urls": [f"https://source.example/{index}"]}
                    ),
                    "problem": f"Question {index}?",
                    "answer": f"Answer {index}{answer_suffix}",
                }
            )


def test_controlled_loader_recovers_only_matching_committed_rows(tmp_path: Path) -> None:
    source = tmp_path / "simpleqa.csv"
    _source(source)
    snapshot = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")

    rows = load_committed_simpleqa_rows(snapshot, source)

    assert len(rows) == 9
    assert all(set(row) == {"task_id", "task_family", "split", "query", "answer"} for row in rows)
    assert [row["task_id"] for row in rows] == [task["task_id"] for task in snapshot["tasks"]]


def test_controlled_loader_rejects_changed_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "simpleqa.csv"
    _source(source)
    snapshot = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")
    _source(source, answer_suffix=" changed")

    with pytest.raises(ValueError, match="source bytes"):
        load_committed_simpleqa_rows(snapshot, source)


def test_controlled_loader_preserves_source_whitespace_for_commitments(tmp_path: Path) -> None:
    source = tmp_path / "simpleqa.csv"
    _source(source, answer_suffix=" ")
    snapshot = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")

    rows = load_committed_simpleqa_rows(snapshot, source)

    assert all(row["answer"].endswith(" ") for row in rows)


def test_controlled_loader_rejects_task_snapshot_tampering(tmp_path: Path) -> None:
    source = tmp_path / "simpleqa.csv"
    _source(source)
    snapshot = build_snapshot(source, count=9, held_out=3, committed_at="2026-09-06T04:00:00Z")
    snapshot["tasks"][0]["task_family"] = "simpleqa.tampered"

    with pytest.raises(ValueError, match="task set"):
        load_committed_simpleqa_rows(snapshot, source)

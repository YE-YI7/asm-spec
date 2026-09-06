"""Fail-closed access to content-committed benchmark rows.

Raw questions and answers stay in memory. The public snapshot contains only
commitments, allowing an evaluator to prove it used the declared source bytes
without publishing benchmark answers in derived artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import validate_contract
from .digests import digest_json


def load_committed_simpleqa_rows(
    snapshot: Mapping[str, Any],
    source: Path,
) -> list[dict[str, Any]]:
    """Recover declared SimpleQA rows only after every commitment verifies."""
    tasks = snapshot.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("snapshot tasks must be a non-empty list")

    source_bytes = source.read_bytes()
    actual_source_digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    if snapshot.get("source_digest") != actual_source_digest:
        raise ValueError("source bytes do not match the committed source digest")
    actual_task_set_digest = digest_json({"tasks": tasks})
    if snapshot.get("task_set_digest") != actual_task_set_digest:
        raise ValueError("task set does not match its commitment")
    if snapshot.get("snapshot_format") != "asm-search-task-snapshot/0.1":
        raise ValueError("unsupported task snapshot format")
    if snapshot.get("build_algorithm") != "simpleqa-topic-round-robin+proportional-topic-split/v1":
        raise ValueError("unsupported task snapshot build algorithm")
    if snapshot.get("task_count") != len(tasks):
        raise ValueError("snapshot task_count does not match its tasks")
    if snapshot.get("held_out_count") != sum(task.get("split") == "held_out" for task in tasks):
        raise ValueError("snapshot held_out_count does not match its tasks")

    tasks_by_row_id: dict[str, Mapping[str, Any]] = {}
    task_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, Mapping):
            raise TypeError("every snapshot task must be an object")
        validate_contract("search_evaluation_task", task)
        task_id = task["task_id"]
        provenance = task["source_provenance"]
        if provenance.get("kind") != "benchmark_dataset":
            raise ValueError(f"task {task_id} is not backed by a benchmark dataset")
        row_id = provenance["row_id"]
        if task_id in task_ids or row_id in tasks_by_row_id:
            raise ValueError("snapshot task_id and source row_id values must be unique")
        if provenance["snapshot_digest"] != actual_source_digest:
            raise ValueError(f"task {task_id} is bound to a different source snapshot")
        task_ids.add(task_id)
        tasks_by_row_id[row_id] = task

    recovered: dict[str, dict[str, Any]] = {}
    with io.StringIO(source_bytes.decode("utf-8"), newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            query = row.get("problem") or ""
            answer = row.get("answer") or ""
            if not query.strip() or not answer.strip():
                continue
            query_digest = digest_json({"query": query})
            row_id = query_digest.removeprefix("sha256:")[:20]
            task = tasks_by_row_id.get(row_id)
            if task is None:
                continue
            if row_id in recovered:
                raise ValueError(f"source row id collision at CSV line {line_number}: {row_id}")
            if task["query_ref"]["digest"] != query_digest:
                raise ValueError(f"query commitment mismatch for task {task['task_id']}")
            if task["ground_truth_ref"]["digest"] != digest_json({"answer": answer}):
                raise ValueError(f"answer commitment mismatch for task {task['task_id']}")
            recovered[row_id] = {
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "split": task["split"],
                "query": query,
                "answer": answer,
            }

    missing = sorted(set(tasks_by_row_id) - set(recovered))
    if missing:
        raise ValueError(f"source is missing {len(missing)} committed benchmark rows")
    return [recovered[task["source_provenance"]["row_id"]] for task in tasks]


__all__ = ["load_committed_simpleqa_rows"]

#!/usr/bin/env python3
"""Build a deterministic, content-committed SimpleQA search-task candidate pool."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from asm_protocol.contracts import validate_contract
from asm_protocol.digests import digest_json

SOURCE_URL = "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"


def _family(topic: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in topic)
    return "simpleqa." + "_".join(part for part in normalized.split("_") if part)


def _eligible_rows(source_bytes: bytes) -> dict[str, deque[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with io.StringIO(source_bytes.decode("utf-8"), newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                metadata = ast.literal_eval(row["metadata"])
            except (SyntaxError, ValueError, TypeError) as exc:
                raise ValueError(f"invalid SimpleQA metadata on CSV line {line_number}") from exc
            if not isinstance(metadata, dict):
                raise TypeError(f"SimpleQA metadata must be an object on CSV line {line_number}")
            domains = sorted(
                {
                    urlparse(url).netloc.lower().removeprefix("www.")
                    for url in metadata.get("urls", [])
                    if urlparse(url).scheme == "https"
                    and urlparse(url).netloc
                    and "google." not in urlparse(url).netloc.lower()
                }
            )
            if not row["problem"].strip() or not row["answer"].strip() or not domains:
                continue
            groups[str(metadata.get("topic") or "other")].append(
                {**row, "metadata_parsed": metadata, "domains": domains}
            )
    return {
        topic: deque(sorted(rows, key=lambda row: hashlib.sha256(row["problem"].encode()).hexdigest()))
        for topic, rows in groups.items()
    }


def _stratified_held_out_indexes(selected: list[dict[str, Any]], held_out: int) -> set[int]:
    """Allocate held-out rows proportionally per topic with deterministic tie-breaking."""
    by_topic: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(selected):
        by_topic[str(row["metadata_parsed"].get("topic") or "other")].append(index)

    total = len(selected)
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for topic, indexes in by_topic.items():
        exact = len(indexes) * held_out / total
        quotas[topic] = math.floor(exact)
        remainders.append((exact - quotas[topic], topic))
    remaining = held_out - sum(quotas.values())
    for _, topic in sorted(remainders, key=lambda item: (-item[0], item[1]))[:remaining]:
        quotas[topic] += 1

    chosen: set[int] = set()
    for topic, indexes in by_topic.items():
        ranked = sorted(
            indexes,
            key=lambda index: hashlib.sha256(
                f"asm-simpleqa-heldout-v1\0{selected[index]['problem']}".encode()
            ).hexdigest(),
        )
        chosen.update(ranked[: quotas[topic]])
    if len(chosen) != held_out:
        raise AssertionError("stratified split did not allocate the requested held-out count")
    return chosen


def build_snapshot(source: Path, *, count: int, held_out: int, committed_at: str) -> dict[str, Any]:
    if not 0 < held_out < count:
        raise ValueError("held_out must be greater than zero and smaller than count")
    source_bytes = source.read_bytes()
    groups = _eligible_rows(source_bytes)
    topics = sorted(groups)
    selected: list[dict[str, Any]] = []
    while len(selected) < count and any(groups.values()):
        for topic in topics:
            if groups[topic] and len(selected) < count:
                selected.append(groups[topic].popleft())
    if len(selected) != count:
        raise ValueError(f"source provides only {len(selected)} eligible rows; requested {count}")

    source_digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    held_out_indexes = _stratified_held_out_indexes(selected, held_out)
    tasks = []
    row_ids: set[str] = set()
    for index, row in enumerate(selected):
        query_digest = digest_json({"query": row["problem"]})
        answer_digest = digest_json({"answer": row["answer"]})
        row_id = query_digest.removeprefix("sha256:")[:20]
        if row_id in row_ids:
            raise ValueError(f"duplicate committed row id: {row_id}")
        row_ids.add(row_id)
        task = {
            "contract_type": "search_evaluation_task",
            "contract_version": "0.1",
            "task_id": f"simpleqa-{row_id}",
            "task_family": _family(str(row["metadata_parsed"].get("topic") or "other")),
            "coverage_tags": ["english_query"],
            "split": "held_out" if index in held_out_indexes else "development",
            "language": "en",
            "query_ref": {"digest": query_digest, "disclosure": "benchmark_controlled"},
            "source_provenance": {
                "kind": "benchmark_dataset",
                "name": "OpenAI SimpleQA",
                "version": source_digest,
                "source_url": SOURCE_URL,
                "license": "MIT",
                "snapshot_digest": source_digest,
                "row_id": row_id,
            },
            "ground_truth_ref": {"digest": answer_digest, "disclosure": "benchmark_controlled"},
            "checks": {
                "reference_domains": row["domains"],
                "domain_requirement": "none",
                # These tasks measure single-search answer support, not multi-source verification.
                "minimum_independent_sources": 1,
                "temporal_requirement": "none",
                "cutoff": None,
                "judge_profile": "asm-search-blinded-judge/v0.1-unfrozen",
            },
            "committed_at": committed_at,
        }
        validate_contract("search_evaluation_task", task)
        tasks.append(task)
    task_set_digest = digest_json({"tasks": tasks})
    return {
        "snapshot_format": "asm-search-task-snapshot/0.1",
        "build_algorithm": "simpleqa-topic-round-robin+proportional-topic-split/v1",
        "status": "candidate_incomplete_coverage",
        "source_digest": source_digest,
        "task_set_digest": task_set_digest,
        "task_count": len(tasks),
        "held_out_count": sum(task["split"] == "held_out" for task in tasks),
        "missing_coverage": ["chinese_query", "time_sensitive_fact", "external_task_contribution"],
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--held-out", type=int, default=20)
    parser.add_argument("--committed-at", required=True)
    args = parser.parse_args()
    snapshot = build_snapshot(
        args.source,
        count=args.count,
        held_out=args.held_out,
        committed_at=args.committed_at,
    )
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Aggregate benchmark/results/*.json into a comparison table + headline deltas.

Reads every <subject>__<condition>.json and reports paired task-level contrasts.
McNemar's exact test is computed per model; a task-clustered bootstrap summarizes
the mean effect without pretending the six models are independent replications.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


TASKS = HERE / "tasks.jsonl"
PUBLISHED_V0_TASKS_DIGEST = (
    "sha256:625e6787fbe50f873510cc044f03af458d1b28d2b10f2747dac64049cca4c7ac"
)


def load(results_dir: Path = RESULTS) -> dict:
    """subject -> condition -> complete result document"""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in sorted(results_dir.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["subject"]][d["condition"]] = d
    return out


def load_tasks(tasks_path: Path = TASKS) -> list[dict]:
    return [json.loads(line) for line in tasks_path.open(encoding="utf-8")]


def validate_result_documents(
    data: dict, tasks: list[dict], tasks_path: Path = TASKS
) -> None:
    """Reject partial or cross-dataset files before paired inference."""
    expected_ids = {task["task_id"] for task in tasks}
    expected_digest = "sha256:" + hashlib.sha256(tasks_path.read_bytes()).hexdigest()
    for subject, conditions in data.items():
        for condition, document in conditions.items():
            observed_ids = set(document.get("picks", {}))
            if observed_ids != expected_ids:
                raise ValueError(
                    f"{subject}/{condition}: result covers {len(observed_ids)} tasks; "
                    f"expected the complete {len(expected_ids)}-task dataset"
                )
            observed_digest = document.get("tasks_digest")
            if observed_digest is None and expected_digest != PUBLISHED_V0_TASKS_DIGEST:
                raise ValueError(
                    f"{subject}/{condition}: legacy result has no tasks_digest and "
                    "cannot be verified against this dataset"
                )
            if observed_digest is not None and observed_digest != expected_digest:
                raise ValueError(
                    f"{subject}/{condition}: tasks_digest does not match {tasks_path.name}"
                )


def _outcome(task: dict, pick: str | None, metric: str) -> bool:
    if metric == "correct":
        return pick in task["ground_truth"]["correct"]
    if metric == "violation":
        return pick in task["ground_truth"]["violations_if"]
    raise ValueError(f"unknown paired metric: {metric}")


def mcnemar_exact(left: list[bool], right: list[bool]) -> dict:
    """Two-sided exact McNemar test over paired binary outcomes."""
    if len(left) != len(right):
        raise ValueError("paired outcomes must have equal length")
    left_only = sum(a and not b for a, b in zip(left, right))
    right_only = sum(b and not a for a, b in zip(left, right))
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k)
                   for k in range(min(left_only, right_only) + 1)) / (2 ** discordant)
        p_value = min(1.0, 2 * tail)
    return {"left_only": left_only, "right_only": right_only,
            "discordant": discordant, "p_value": p_value}


def bootstrap_ci(values: list[float], *, seed: str,
                 samples: int = 20_000) -> tuple[float, float]:
    """Deterministic percentile bootstrap CI over task-level values."""
    if not values:
        raise ValueError("cannot bootstrap an empty sample")
    if len(set(values)) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(
        sum(values[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(samples)
    )
    return draws[int(0.025 * (samples - 1))], draws[int(0.975 * (samples - 1))]


def paired_stats(tasks: list[dict], left_picks: dict, right_picks: dict,
                 metric: str, *, seed: str) -> dict:
    left = [_outcome(task, left_picks.get(task["task_id"]), metric) for task in tasks]
    right = [_outcome(task, right_picks.get(task["task_id"]), metric) for task in tasks]
    deltas = [float(b) - float(a) for a, b in zip(left, right)]
    low, high = bootstrap_ci(deltas, seed=seed)
    return {
        "n": len(tasks),
        "left_rate": sum(left) / len(left),
        "right_rate": sum(right) / len(right),
        "delta": sum(deltas) / len(deltas),
        "ci95": (low, high),
        "mcnemar": mcnemar_exact(left, right),
        "task_deltas": deltas,
    }


def _fmt(m: dict | None) -> str:
    if not m or "correct_rate" not in m:
        return "     —"
    return f"{m['correct_rate']:>4.0%}/{m['violation_rate']:>3.0%}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=TASKS)
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--left", default="names_only")
    parser.add_argument("--right", default="asm")
    args = parser.parse_args()

    data = load(args.results_dir)
    tasks = load_tasks(args.tasks)
    if not data:
        print(f"no results yet in {args.results_dir}")
        return
    validate_result_documents(data, tasks, args.tasks)

    print(
        f"ToolSelect-Bench — correct% / violation% "
        f"({args.left} -> {args.right})\n"
    )
    hdr = f"{'subject':38} {'overall':>18}  {'cheapest_eligible':>18}  {'governance':>18}"
    print(hdr)
    print("-" * len(hdr))
    deltas_viol, deltas_correct = [], []
    is_published_v0_contrast = args.left == "names_only" and args.right == "asm"
    for subject, conds in sorted(data.items()):
        left_doc, right_doc = conds.get(args.left), conds.get(args.right)
        left = (left_doc or {}).get("metrics")
        right = (right_doc or {}).get("metrics")

        def cell(key):
            n = (left or {}).get("by_type", {}).get(key) if key else left
            a = (right or {}).get("by_type", {}).get(key) if key else right
            if key is None:
                n, a = left, right
            return f"{_fmt(n)} ->{_fmt(a)}"

        print(f"{subject:38} {cell(None):>18}  {cell('cheapest_eligible'):>18}  "
              f"{cell('governance'):>18}")

        # headline deltas on the FULL task set (robust), LLM subjects only
        if subject.startswith("llm:") and left and right:
            deltas_viol.append(left["violation_rate"] - right["violation_rate"])
            deltas_correct.append(right["correct_rate"] - left["correct_rate"])
            for metric in ("correct", "violation"):
                paired = paired_stats(
                    tasks, left_doc["picks"], right_doc["picks"], metric,
                    seed=(f"{subject}:{metric}" if is_published_v0_contrast
                          else f"{args.left}:{args.right}:{subject}:{metric}"),
                )
                low, high = paired["ci95"]
                mc = paired["mcnemar"]
                print(
                    f"    paired {metric:9} Δ={paired['delta']:+.1%} "
                    f"95% CI [{low:+.1%}, {high:+.1%}] "
                    f"McNemar p={mc['p_value']:.4f} "
                    f"({args.left} wins={mc['left_only']}, "
                    f"{args.right} wins={mc['right_only']})"
                )

    if deltas_viol:
        n = len(deltas_viol)
        mv = sum(deltas_viol) / n
        mc = sum(deltas_correct) / n
        improved = sum(1 for d in deltas_correct if d > 0)
        cut_viol = sum(1 for d in deltas_viol if d > 0)
        print(f"\nDESCRIPTIVE SUMMARY (same 50 tasks reused across {n} models):")
        print(
            f"  correct picks improved from {args.left} to {args.right} "
            f"in {improved}/{n} models (avg {mc:+.0%})"
        )
        print(
            f"  constraint violations fell from {args.left} to {args.right} "
            f"in {cut_viol}/{n} models (avg {mv:+.0%} pts)"
        )
        print("  These are not independent replications; use the paired per-model tests above.")

        for metric in ("correct", "violation"):
            per_task = []
            for task in tasks:
                deltas = []
                for subject, conds in data.items():
                    if not subject.startswith("llm:"):
                        continue
                    left_doc, right_doc = conds.get(args.left), conds.get(args.right)
                    if not left_doc or not right_doc:
                        continue
                    left = _outcome(
                        task, left_doc["picks"].get(task["task_id"]), metric
                    )
                    right = _outcome(
                        task, right_doc["picks"].get(task["task_id"]), metric
                    )
                    deltas.append(float(right) - float(left))
                if deltas:
                    per_task.append(sum(deltas) / len(deltas))
            low, high = bootstrap_ci(
                per_task,
                seed=(f"cluster:{metric}" if is_published_v0_contrast
                      else f"cluster:{args.left}:{args.right}:{metric}"),
            )
            mean = sum(per_task) / len(per_task)
            print(f"  task-clustered {metric:9} mean Δ={mean:+.1%} "
                  f"95% bootstrap CI [{low:+.1%}, {high:+.1%}]")


if __name__ == "__main__":
    main()

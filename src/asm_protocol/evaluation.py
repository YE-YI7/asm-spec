"""Pre-registered paired evaluation utilities; synthetic tests are not product evidence."""

from __future__ import annotations

import math
import random
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from .contracts import validate_contract
from .digests import digest_json


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(character if character.isalnum() else " " for character in normalized).split())


def _aware_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def exact_answer_support(answer: str, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Conservative deterministic anchor over returned titles and snippets."""
    needle = _normalized_text(answer)
    if not needle:
        raise ValueError("answer must contain searchable text")
    for result in results:
        text = _normalized_text(f"{result.get('title') or ''} {result.get('snippet') or ''}")
        # SimpleQA is English. Token boundaries avoid false positives such as
        # "Apple" in "Applewood" while still allowing punctuation differences.
        if f" {needle} " in f" {text} ":
            return {"status": "pass", "method": "normalized_exact_answer", "rank": result.get("rank")}
    return {"status": "unresolved", "method": "normalized_exact_answer", "rank": None}


def exact_mcnemar(baseline_pass: Sequence[bool], asm_pass: Sequence[bool]) -> dict[str, Any]:
    """Return the two-sided exact McNemar result for paired binary outcomes."""
    if len(baseline_pass) != len(asm_pass) or not baseline_pass:
        raise ValueError("paired outcomes must have the same non-zero length")
    baseline_only = sum(left and not right for left, right in zip(baseline_pass, asm_pass, strict=True))
    asm_only = sum(right and not left for left, right in zip(baseline_pass, asm_pass, strict=True))
    discordant = baseline_only + asm_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(min(baseline_only, asm_only) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {
        "baseline_only_pass": baseline_only,
        "asm_only_pass": asm_only,
        "discordant_pairs": discordant,
        "two_sided_exact_p": p_value,
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cluster_bootstrap_pass_delta(
    rows: Sequence[Mapping[str, Any]],
    *,
    iterations: int,
    seed: int,
) -> dict[str, float]:
    """Bootstrap ASM-minus-baseline pass-rate delta by task family."""
    if iterations < 1000:
        raise ValueError("cluster bootstrap requires at least 1000 iterations")
    families: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        family = row.get("task_family")
        if not isinstance(family, str) or not family:
            raise ValueError("every row requires a non-empty task_family")
        if not isinstance(row.get("baseline_pass"), bool) or not isinstance(row.get("asm_pass"), bool):
            raise TypeError("baseline_pass and asm_pass must be booleans")
        families[family].append(row)
    if len(families) < 2:
        raise ValueError("cluster bootstrap requires at least two task families")
    clusters = list(families.values())
    observed = sum(int(row["asm_pass"]) - int(row["baseline_pass"]) for row in rows) / len(rows)
    generator = random.Random(seed)
    draws = []
    for _ in range(iterations):
        sampled = [generator.choice(clusters) for _ in clusters]
        differences = [
            int(row["asm_pass"]) - int(row["baseline_pass"])
            for cluster in sampled
            for row in cluster
        ]
        draws.append(sum(differences) / len(differences))
    return {
        "delta": observed,
        "ci95_lower": _percentile(draws, 0.025),
        "ci95_upper": _percentile(draws, 0.975),
    }


def validate_frozen_quality_plan(
    plan: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    task_snapshot: Mapping[str, Any],
    evaluated_at: str,
) -> None:
    """Fail closed before evaluating an underspecified or post-hoc experiment."""
    if plan.get("status") != "frozen" or not plan.get("frozen_at"):
        raise ValueError("evaluation plan must be frozen before results are inspected")
    frozen_at = _aware_timestamp(plan["frozen_at"], "frozen_at")
    evaluation_time = _aware_timestamp(evaluated_at, "evaluated_at")
    if frozen_at > evaluation_time:
        raise ValueError("frozen_at must not be later than evaluated_at")
    if plan.get("primary_objective") != "pass_rate_improvement":
        raise ValueError("this evaluator requires pass_rate_improvement as the pre-registered primary objective")
    if plan.get("budget_authorized") is not True:
        raise ValueError("live comparison budget must be explicitly authorized")
    provider_versions = plan.get("provider_versions")
    if not isinstance(provider_versions, Mapping) or not provider_versions:
        raise ValueError("frozen evaluation requires exact provider versions")
    if any(not isinstance(key, str) or not key or not isinstance(value, str) or not value for key, value in provider_versions.items()):
        raise ValueError("provider version names and values must be non-empty strings")
    judge_profile = plan.get("judge_profile")
    if not isinstance(judge_profile, str) or not judge_profile or judge_profile.endswith("unfrozen"):
        raise ValueError("frozen evaluation requires an exact frozen judge profile")
    tasks = task_snapshot.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("task snapshot must contain a non-empty tasks list")
    computed_task_set_digest = digest_json({"tasks": tasks})
    if task_snapshot.get("task_set_digest") != computed_task_set_digest:
        raise ValueError("task snapshot does not match its task-set digest")
    if plan.get("task_set_digest") != computed_task_set_digest:
        raise ValueError("evaluation plan must be bound to the exact task-set digest")
    if len(rows) < 60:
        raise ValueError("quality evaluation requires at least 60 independent task rows")
    required_tags = plan.get("required_coverage_tags")
    if not isinstance(required_tags, list) or not required_tags or any(
        not isinstance(tag, str) or not tag for tag in required_tags
    ):
        raise ValueError("frozen evaluation requires explicit coverage tags")
    observed_tags = {
        tag
        for task in tasks
        if isinstance(task, Mapping)
        for tag in task.get("coverage_tags", [])
        if isinstance(tag, str)
    }
    missing_tags = sorted(set(required_tags) - observed_tags)
    if missing_tags:
        raise ValueError(f"task snapshot is missing required coverage: {missing_tags}")
    minimum_external = plan.get("minimum_external_contribution_rows")
    if not isinstance(minimum_external, int) or isinstance(minimum_external, bool) or minimum_external < 1:
        raise ValueError("frozen evaluation requires at least one external contribution row")
    external_rows = sum(
        isinstance(task, Mapping)
        and isinstance(task.get("source_provenance"), Mapping)
        and task["source_provenance"].get("kind") == "external_contribution"
        for task in tasks
    )
    if external_rows < minimum_external:
        raise ValueError("task snapshot does not contain enough external contribution rows")
    for task in tasks:
        if not isinstance(task, Mapping):
            raise TypeError("every task snapshot row must be an object")
        validate_contract("search_evaluation_task", task)
    if any(
        not isinstance(task, Mapping)
        or not isinstance(task.get("checks"), Mapping)
        or task["checks"].get("judge_profile") != judge_profile
        for task in tasks
    ):
        raise ValueError("every task must bind the frozen judge profile")
    if any(
        _aware_timestamp(task.get("committed_at"), "task committed_at") > frozen_at
        for task in tasks
        if isinstance(task, Mapping)
    ):
        raise ValueError("every task must be committed no later than frozen_at")
    if any(row.get("split") not in {"development", "held_out"} for row in rows):
        raise ValueError("every evaluation row must use the development or held_out split")
    task_ids = [row.get("task_id") for row in rows]
    if any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
        raise ValueError("every evaluation row requires a non-empty task_id")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("evaluation task_ids must be unique")
    expected_splits = {
        task.get("task_id"): task.get("split")
        for task in tasks
        if isinstance(task, Mapping)
    }
    actual_splits = {row["task_id"]: row["split"] for row in rows}
    if actual_splits != expected_splits:
        raise ValueError("evaluation rows must match every committed task_id and split exactly")
    observation_times: dict[str, datetime] = {}
    for row in rows:
        observed_at = _aware_timestamp(row.get("observed_at"), "row observed_at")
        if observed_at < frozen_at or observed_at > evaluation_time:
            raise ValueError("every row observed_at must fall between frozen_at and evaluated_at")
        observation_times[row["task_id"]] = observed_at
    for task in tasks:
        if "time_sensitive_fact" not in task.get("coverage_tags", []):
            continue
        ground_truth = task.get("ground_truth_ref")
        if not isinstance(ground_truth, Mapping):
            raise TypeError("time-sensitive tasks require a ground-truth commitment")
        verified_at = _aware_timestamp(ground_truth.get("verified_at"), "ground truth verified_at")
        expires_at = _aware_timestamp(ground_truth.get("expires_at"), "ground truth expires_at")
        committed_at = _aware_timestamp(task.get("committed_at"), "task committed_at")
        observed_at = observation_times[task["task_id"]]
        if verified_at > committed_at:
            raise ValueError("time-sensitive ground truth must be verified before task commitment")
        if expires_at <= verified_at or expires_at < observed_at:
            raise ValueError(
                "time-sensitive ground truth must be valid when the task result is observed"
            )
    held_out = sum(row.get("split") == "held_out" for row in rows)
    if held_out < 20:
        raise ValueError("quality evaluation requires at least 20 held-out tasks")
    if any(row.get("constraint_violations", 0) != 0 for row in rows):
        raise ValueError("authorization, budget, or privacy violations must be zero")


def evaluate_frozen_quality(
    plan: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    task_snapshot: Mapping[str, Any],
    evaluated_at: str,
    bootstrap_iterations: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    """Emit paired quality statistics only after all pre-registration gates pass."""
    validate_frozen_quality_plan(
        plan,
        rows,
        task_snapshot=task_snapshot,
        evaluated_at=evaluated_at,
    )
    baseline = [row["baseline_pass"] for row in rows]
    asm = [row["asm_pass"] for row in rows]
    return {
        "task_set_digest": task_snapshot["task_set_digest"],
        "evaluated_at": evaluated_at,
        "sample_size": len(rows),
        "baseline_pass_rate": sum(baseline) / len(baseline),
        "asm_pass_rate": sum(asm) / len(asm),
        "paired_test": exact_mcnemar(baseline, asm),
        "cluster_bootstrap": cluster_bootstrap_pass_delta(
            rows,
            iterations=bootstrap_iterations,
            seed=bootstrap_seed,
        ),
    }


__all__ = [
    "cluster_bootstrap_pass_delta",
    "evaluate_frozen_quality",
    "exact_answer_support",
    "exact_mcnemar",
    "validate_frozen_quality_plan",
]

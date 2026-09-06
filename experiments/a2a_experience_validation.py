"""Deterministic feasibility checks for task-bound A2A experience evidence.

This is a synthetic mechanism test. It does not measure real agent quality and
must not be reported as external adoption or market validation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any

# Test controls chosen only to make the synthetic cases distinguishable. They are
# not a proposed production scoring algorithm and require empirical calibration.
SYNTHETIC_EVIDENCE_WEIGHT = {
    "opinion": 0.0,
    "client_bound": 0.25,
    "interaction_bound": 0.7,
    "bilateral": 0.85,
    "verified": 1.0,
}
SYNTHETIC_MAX_CHECKS_PER_EVALUATOR = 3.0


def _canonical_digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _opaque_digest(scope: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _canonical_digest({"scope": scope, "value": value})


def event_from_a2a(
    *,
    event_id: str,
    task: dict[str, Any],
    agent_card: dict[str, Any],
    configuration: dict[str, Any],
    evaluator_id: str,
    taxonomy: str,
    passed: int,
    failed: int,
    evidence_level: str,
    observed_at: str,
) -> dict[str, Any]:
    """Project an A2A-shaped task into a redacted experience event."""
    if evidence_level not in SYNTHETIC_EVIDENCE_WEIGHT:
        raise ValueError(f"unknown evidence level: {evidence_level}")
    if not task.get("id") or not (task.get("status") or {}).get("state"):
        raise ValueError("A2A task id and status.state are required")
    if passed < 0 or failed < 0 or passed + failed == 0:
        raise ValueError("at least one objective check is required")

    artifacts = task.get("artifacts") or []
    interfaces = (
        agent_card.get("supportedInterfaces")
        or agent_card.get("supported_interfaces")
        or []
    )
    agent_ref = agent_card.get("url") or (
        interfaces[0].get("url") if interfaces else None
    )
    if not agent_ref:
        raise ValueError("Agent Card must expose at least one interface URL")
    event = {
        "schema": "asm.experience/v0.1-draft",
        "event_id": event_id,
        "subject": {
            "agent_ref": agent_ref,
            "agent_card_digest": _canonical_digest(agent_card),
            "configuration_digest": _canonical_digest(configuration),
        },
        "evaluator": {"id": evaluator_id, "type": "caller"},
        "interaction": {
            "protocol": "A2A",
            "task_id_hash": _opaque_digest(agent_ref, task["id"]),
            "context_id_hash": _opaque_digest(
                agent_ref, task.get("contextId")
            ),
            "artifact_digest": _canonical_digest(artifacts) if artifacts else None,
        },
        "task_profile": {"taxonomy": taxonomy},
        "outcome": {
            "state": task["status"]["state"],
            "objective_checks": {"passed": passed, "failed": failed},
        },
        "evidence_level": evidence_level,
        "observed_at": observed_at,
    }
    validate_event(event)
    return event


def validate_event(event: dict[str, Any]) -> None:
    required = {
        "schema",
        "event_id",
        "subject",
        "evaluator",
        "interaction",
        "task_profile",
        "outcome",
        "evidence_level",
        "observed_at",
    }
    missing = sorted(required - set(event))
    if missing:
        raise ValueError(f"missing event fields: {missing}")
    subject = event["subject"]
    if not subject.get("agent_card_digest") or not subject.get("configuration_digest"):
        raise ValueError("agent card and configuration digests are required")
    if event["evidence_level"] not in SYNTHETIC_EVIDENCE_WEIGHT:
        raise ValueError("unknown evidence level")
    checks = event["outcome"].get("objective_checks") or {}
    passed, failed = checks.get("passed"), checks.get("failed")
    if not isinstance(passed, int) or not isinstance(failed, int):
        raise TypeError("objective check counts must be integers")
    if passed < 0 or failed < 0 or passed + failed == 0:
        raise ValueError("objective check counts must be non-negative and non-empty")
    datetime.fromisoformat(event["observed_at"].replace("Z", "+00:00"))


def _wilson(successes: float, trials: float) -> tuple[float, float]:
    if trials <= 0:
        return 0.0, 1.0
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize(
    events: Iterable[dict[str, Any]],
    *,
    agent_card_digest: str,
    configuration_digest: str,
    taxonomy: str,
    exact_version: bool = True,
    protected: bool = True,
) -> dict[str, Any]:
    rows = [
        event
        for event in events
        if event["subject"]["agent_card_digest"] == agent_card_digest
        and event["task_profile"]["taxonomy"] == taxonomy
        and (
            not exact_version
            or event["subject"]["configuration_digest"] == configuration_digest
        )
    ]
    evaluator_usage: dict[str, float] = defaultdict(float)
    evidence_mix: Counter[str] = Counter()
    successes = 0.0
    trials = 0.0
    for event in sorted(rows, key=lambda item: (item["observed_at"], item["event_id"])):
        level = event["evidence_level"]
        base_weight = SYNTHETIC_EVIDENCE_WEIGHT[level] if protected else 1.0
        if base_weight == 0:
            continue
        checks = event["outcome"]["objective_checks"]
        raw_trials = float(checks["passed"] + checks["failed"])
        weighted_trials = raw_trials * base_weight
        evaluator = event["evaluator"]["id"]
        if protected:
            remaining = max(
                SYNTHETIC_MAX_CHECKS_PER_EVALUATOR - evaluator_usage[evaluator], 0.0
            )
            weighted_trials = min(weighted_trials, remaining)
        if weighted_trials <= 0:
            continue
        pass_fraction = checks["passed"] / raw_trials
        successes += weighted_trials * pass_fraction
        trials += weighted_trials
        evaluator_usage[evaluator] += weighted_trials
        evidence_mix[level] += 1

    estimate = successes / trials if trials else None
    interval = _wilson(successes, trials) if trials else (0.0, 1.0)
    distinct_evaluators = sum(value > 0 for value in evaluator_usage.values())
    concentration = max(evaluator_usage.values(), default=0.0) / trials if trials else 1.0
    warnings = []
    if trials < 5:
        warnings.append("insufficient_evidence")
    if distinct_evaluators < 2:
        warnings.append("insufficient_evaluator_diversity")
    if concentration > 0.6:
        warnings.append("evaluator_concentration")
    return {
        "events_matched": len(rows),
        "effective_checks": round(trials, 3),
        "distinct_evaluators": distinct_evaluators,
        "objective_pass_rate": (
            {
                "estimate": round(estimate, 4),
                "interval_95": [round(interval[0], 4), round(interval[1], 4)],
            }
            if estimate is not None
            else None
        ),
        "evidence_mix": dict(sorted(evidence_mix.items())),
        "evaluator_concentration": round(concentration, 4),
        "warnings": warnings,
    }


def select_with_evidence(candidates: list[dict[str, Any]]) -> str:
    """Select by conservative observed quality, falling back to declared order."""
    usable = [
        candidate
        for candidate in candidates
        if candidate["summary"]["objective_pass_rate"] is not None
        and "insufficient_evidence" not in candidate["summary"]["warnings"]
        and "insufficient_evaluator_diversity" not in candidate["summary"]["warnings"]
    ]
    if not usable:
        return min(candidate["service_id"] for candidate in candidates)
    usable.sort(
        key=lambda candidate: (
            -candidate["summary"]["objective_pass_rate"]["interval_95"][0],
            candidate["service_id"],
        )
    )
    return usable[0]["service_id"]


def select_with_owner_policy(
    candidates: list[dict[str, Any]], *, require_private_execution: bool
) -> str:
    """Apply a private hard gate before the shared evidence ranking."""
    eligible = [
        candidate
        for candidate in candidates
        if not require_private_execution or candidate.get("private_execution") is True
    ]
    if not eligible:
        raise ValueError("owner policy leaves no eligible candidate")
    return select_with_evidence(eligible)


def _card(service_id: str) -> dict[str, Any]:
    return {
        "name": service_id,
        "url": f"https://{service_id}.example/a2a",
        "version": "1.0.0",
        "skills": [{"id": "code-review", "name": "Code review"}],
    }


def _config(service_id: str, version: str) -> dict[str, Any]:
    return {"service_id": service_id, "runtime_version": version, "model": "synthetic"}


def _task(service_id: str, index: int, state: str = "completed") -> dict[str, Any]:
    return {
        "id": f"{service_id}-task-{index}",
        "contextId": f"{service_id}-context-{index}",
        "status": {"state": state},
        "artifacts": [{"artifactId": f"artifact-{index}", "parts": [{"text": "private"}]}],
        "history": [{"parts": [{"text": "secret prompt"}]}],
    }


def _series(
    service_id: str,
    version: str,
    outcomes: list[tuple[int, int]],
    evaluators: list[str],
    *,
    level: str = "verified",
    start: int = 1,
) -> list[dict[str, Any]]:
    card = _card(service_id)
    config = _config(service_id, version)
    return [
        event_from_a2a(
            event_id=f"{service_id}-{version}-{start + index}",
            task=_task(service_id, start + index),
            agent_card=card,
            configuration=config,
            evaluator_id=evaluators[index % len(evaluators)],
            taxonomy="software.code_review",
            passed=passed,
            failed=failed,
            evidence_level=level,
            observed_at=f"2026-08-{10 + start + index:02d}T00:00:00Z",
        )
        for index, (passed, failed) in enumerate(outcomes)
    ]


def _summary_for(
    events: list[dict[str, Any]], service_id: str, version: str, **kwargs: Any
) -> dict[str, Any]:
    return summarize(
        events,
        agent_card_digest=_canonical_digest(_card(service_id)),
        configuration_digest=_canonical_digest(_config(service_id, version)),
        taxonomy="software.code_review",
        **kwargs,
    )


def run_validation() -> dict[str, Any]:
    cases = []

    # 1. Provider declarations tie; observed evidence identifies the better peer.
    peer_events = _series("peer-a", "v1", [(1, 0)] * 4 + [(0, 1)] * 4, ["e1", "e2", "e3"])
    peer_events += _series("peer-b", "v1", [(1, 0)] * 7 + [(0, 1)], ["e4", "e5", "e6"])
    declared_pick = "peer-a"
    evidence_pick = select_with_evidence(
        [
            {"service_id": name, "summary": _summary_for(peer_events, name, "v1")}
            for name in ("peer-a", "peer-b")
        ]
    )
    cases.append(
        {
            "case": "cross_org_a2a_selection",
            "declared_only": declared_pick,
            "declared_plus_observed": evidence_pick,
            "expected": "peer-b",
            "passed": evidence_pick == "peer-b" and declared_pick != "peer-b",
        }
    )

    # 2. Strong old-version history must not launder a weak new configuration.
    version_events = _series("legacy-a", "v1", [(1, 0)] * 10, ["v1", "v2", "v3"])
    version_events += _series("legacy-a", "v2", [(1, 0), (0, 1)], ["v4", "v5"], start=11)
    version_events += _series("current-b", "v1", [(1, 0)] * 7 + [(0, 1)], ["v6", "v7", "v8"])
    naive_a = _summary_for(version_events, "legacy-a", "v2", exact_version=False, protected=False)
    strict_candidates = [
        {"service_id": "legacy-a", "summary": _summary_for(version_events, "legacy-a", "v2")},
        {"service_id": "current-b", "summary": _summary_for(version_events, "current-b", "v1")},
    ]
    strict_pick = select_with_evidence(strict_candidates)
    cases.append(
        {
            "case": "version_binding",
            "naive_all_version_rate": naive_a["objective_pass_rate"]["estimate"],
            "strict_pick": strict_pick,
            "expected": "current-b",
            "passed": strict_pick == "current-b",
        }
    )

    # 3. Many weak reviews from one evaluator cannot beat diverse evidence.
    sybil_events = _series("sybil-c", "v1", [(1, 0)] * 20, ["one-wallet"], level="client_bound")
    sybil_events += _series("trusted-b", "v1", [(1, 0)] * 5 + [(0, 1)], ["t1", "t2", "t3"])
    protected_pick = select_with_evidence(
        [
            {"service_id": name, "summary": _summary_for(sybil_events, name, "v1")}
            for name in ("sybil-c", "trusted-b")
        ]
    )
    cases.append(
        {
            "case": "sybil_resistance",
            "raw_sybil_reviews": 20,
            "protected_pick": protected_pick,
            "expected": "trusted-b",
            "passed": protected_pick == "trusted-b",
        }
    )

    # 4. A failed primary can be replaced with the better-evidenced fallback.
    fallback_events = _series("fallback-a", "v1", [(1, 0)] * 3 + [(0, 1)] * 3, ["f1", "f2", "f3"])
    fallback_events += _series("fallback-b", "v1", [(1, 0)] * 5 + [(0, 1)], ["f4", "f5", "f6"])
    fallback_pick = select_with_evidence(
        [
            {"service_id": name, "summary": _summary_for(fallback_events, name, "v1")}
            for name in ("fallback-a", "fallback-b")
        ]
    )
    cases.append(
        {
            "case": "multi_agent_failure_replacement",
            "failed_primary": "primary-agent",
            "replacement": fallback_pick,
            "expected": "fallback-b",
            "passed": fallback_pick == "fallback-b",
        }
    )

    # 5. One worker's objective failure changes a later worker's choice.
    shared_events = _series("shared-a", "v1", [(1, 0)] * 6, ["s1", "s2", "s3"])
    shared_events += _series("shared-b", "v1", [(1, 0)] * 5 + [(0, 1)], ["s4", "s5", "s6"])
    before = select_with_evidence(
        [
            {"service_id": name, "summary": _summary_for(shared_events, name, "v1")}
            for name in ("shared-a", "shared-b")
        ]
    )
    shared_events += _series("shared-a", "v1", [(0, 10)], ["worker-one"], start=20)
    after = select_with_evidence(
        [
            {"service_id": name, "summary": _summary_for(shared_events, name, "v1")}
            for name in ("shared-a", "shared-b")
        ]
    )
    cases.append(
        {
            "case": "cross_agent_shared_experience",
            "worker_one_prior_pick": before,
            "worker_two_after_observation": after,
            "expected": "shared-b",
            "passed": before == "shared-a" and after == "shared-b",
        }
    )

    # 6. Public evidence is an input; a private owner hard constraint still wins.
    policy_events = _series(
        "cloud-high-quality", "v1", [(1, 0)] * 6, ["p1", "p2", "p3"]
    )
    policy_events += _series(
        "local-private", "v1", [(1, 0)] * 5 + [(0, 1)], ["p4", "p5", "p6"]
    )
    policy_candidates = [
        {
            "service_id": name,
            "private_execution": name == "local-private",
            "summary": _summary_for(policy_events, name, "v1"),
        }
        for name in ("cloud-high-quality", "local-private")
    ]
    quality_pick = select_with_owner_policy(
        policy_candidates, require_private_execution=False
    )
    privacy_pick = select_with_owner_policy(
        policy_candidates, require_private_execution=True
    )
    cases.append(
        {
            "case": "owner_policy_consistency",
            "quality_default": quality_pick,
            "privacy_constrained": privacy_pick,
            "expected": "local-private",
            "passed": privacy_pick == "local-private" and privacy_pick != quality_pick,
        }
    )

    # Redaction property: raw prompt/artifact content is hashed, not copied.
    redaction_event = _series("redaction", "v1", [(1, 0)], ["r1"])[0]
    serialized = json.dumps(redaction_event, sort_keys=True)
    redaction_passed = "secret prompt" not in serialized and '"private"' not in serialized
    cases.append(
        {
            "case": "raw_content_redaction",
            "passed": redaction_passed,
        }
    )

    return {
        "status": "PASS" if all(case["passed"] for case in cases) else "FAIL",
        "scope": "synthetic mechanism validation only",
        "cases": cases,
        "passed": sum(case["passed"] for case in cases),
        "total": len(cases),
    }


if __name__ == "__main__":
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)

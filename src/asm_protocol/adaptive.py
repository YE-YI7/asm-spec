"""Experimental owner-aligned selector over canonical ASM eligibility gates."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable, Literal, Mapping

from .cost import Workload, coerce_workload, estimate_monthly_cost
from .freshness import (
    FreshnessPolicy,
    assess_manifest_freshness,
    freshness_rejection,
    invocation_surface,
    selection_claim_freshness,
)
from .preferences import BayesianLinearPreferenceModel, DEFAULT_FEATURES
from .selection import eligibility, load_library


AdaptivePolicy = Literal["posterior_mean", "linucb", "thompson"]
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": 4}
_FEATURE_LABELS = {
    "cost_benefit": "成本",
    "quality": "质量",
    "speed": "速度",
    "reliability": "可靠性",
    "privacy": "隐私",
    "familiarity": "已有账号和使用习惯",
    "low_human_effort": "配置与人工成本",
    "observed_success": "历史成功率",
}


@dataclass(frozen=True)
class OwnerContext:
    """Private decision context supplied by an agent, not published by tools."""

    explicit_service_id: str | None = None
    installed_service_ids: tuple[str, ...] = ()
    authenticated_service_ids: tuple[str, ...] = ()
    forbidden_service_ids: tuple[str, ...] = ()
    forbidden_side_effects: tuple[str, ...] = ()
    max_risk: str = "critical"
    allow_unknown_risk: bool = False
    reversible: bool = True
    interruption_cost: float | None = None
    monthly_budget: float | None = None
    budget_currency: str = "USD"
    latency_target_seconds: float | None = None
    observed_success: Mapping[str, float] = field(default_factory=dict)
    context_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_risk not in _RISK_ORDER:
            raise ValueError(f"unknown max_risk: {self.max_risk}")
        if self.interruption_cost is not None and (
            not math.isfinite(self.interruption_cost) or self.interruption_cost < 0
        ):
            raise ValueError("interruption_cost must be finite and non-negative")
        if self.monthly_budget is not None and (
            not math.isfinite(self.monthly_budget) or self.monthly_budget < 0
        ):
            raise ValueError("monthly_budget must be finite and non-negative")
        if not self.budget_currency:
            raise ValueError("budget_currency is required")
        if self.latency_target_seconds is not None and (
            not math.isfinite(self.latency_target_seconds)
            or self.latency_target_seconds <= 0
        ):
            raise ValueError("latency_target_seconds must be finite and positive")
        for service_id, value in self.observed_success.items():
            if not math.isfinite(float(value)) or not -1 <= float(value) <= 1:
                raise ValueError(f"observed_success[{service_id!r}] must be in [-1, 1]")


@dataclass
class AdaptiveCandidate:
    service_id: str
    display_name: str
    manifest: dict[str, Any] = field(repr=False)
    features: dict[str, float] = field(default_factory=dict)
    known_features: tuple[str, ...] = ()
    freshness: dict[str, Any] = field(default_factory=dict)
    risk_class: str = "unknown"
    side_effects: tuple[str, ...] = ()
    preference_mean: float = 0.0
    preference_variance: float = 0.0

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("manifest", None)
        value["side_effects"] = list(self.side_effects)
        value["known_features"] = list(self.known_features)
        return value


def _parse_latency(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower().lstrip("~<>")
    try:
        if text.endswith("ms"):
            return float(text[:-2]) / 1000
        if text.endswith("s"):
            return float(text[:-1])
        if text.endswith("min"):
            return float(text[:-3]) * 60
        return float(text)
    except ValueError:
        return None


def _quality_metrics(manifest: Mapping) -> dict[tuple[str, str, str], float]:
    metrics = (manifest.get("quality") or {}).get("metrics") or []
    result: dict[tuple[str, str, str], float] = {}
    maxima = {
        "0-1": 1.0,
        "0..1": 1.0,
        "1": 1.0,
        "0-5": 5.0,
        "5": 5.0,
        "5.0": 5.0,
        "0-10": 10.0,
        "10": 10.0,
        "10.0": 10.0,
        "0-100": 100.0,
        "100": 100.0,
        "100.0": 100.0,
    }
    for metric in metrics:
        name = metric.get("name")
        score = metric.get("score")
        scale = str(metric.get("scale") or "").lower().strip()
        maximum = maxima.get(scale)
        if not isinstance(name, str) or not isinstance(score, (int, float)) or maximum is None:
            continue
        benchmark = str(metric.get("benchmark") or "unspecified").strip().lower()
        identity = (name.strip().lower(), benchmark, scale)
        result[identity] = max(-1.0, min(2 * float(score) / maximum - 1, 1.0))
    return result


def _bounded_relative(value: float, target: float) -> float:
    """Stable target-relative feature independent of the current candidate set."""
    return max(-1.0, min((target - value) / max(target, 1.0), 1.0))


def _privacy_feature(manifest: Mapping) -> float | None:
    governance = manifest.get("data_governance") or {}
    if not governance:
        return None
    score = 0.0
    evidence = 0
    training = governance.get("trains_on_user_data")
    if training in {"no", "opt_out", "yes"}:
        score += {"no": 1.0, "opt_out": 0.0, "yes": -1.0}[training]
        evidence += 1
    owner = governance.get("data_owner")
    if owner in {"user", "shared", "provider"}:
        score += {"user": 1.0, "shared": 0.0, "provider": -1.0}[owner]
        evidence += 1
    if isinstance(governance.get("exportable"), bool):
        score += 1.0 if governance["exportable"] else -1.0
        evidence += 1
    return score / evidence if evidence else None


def _build_features(
    candidates: list[AdaptiveCandidate],
    *,
    context: OwnerContext,
    workload: Workload,
) -> None:
    estimates = [estimate_monthly_cost(row.manifest, workload) for row in candidates]
    quality_maps = [_quality_metrics(row.manifest) for row in candidates]
    shared_quality = set(quality_maps[0]) if quality_maps else set()
    for metrics in quality_maps[1:]:
        shared_quality &= set(metrics)
    quality_identity = next(iter(shared_quality)) if len(shared_quality) == 1 else None
    latencies = [_parse_latency((row.manifest.get("sla") or {}).get("latency_p50")) for row in candidates]
    uptimes = [
        float(value) if isinstance(value := (row.manifest.get("sla") or {}).get("uptime"), (int, float)) else None
        for row in candidates
    ]
    installed = set(context.installed_service_ids)
    authenticated = set(context.authenticated_service_ids)
    for index, candidate in enumerate(candidates):
        feature_values: dict[str, float | None] = {
            "cost_benefit": (
                _bounded_relative(float(estimates[index].monthly_total), context.monthly_budget)
                if context.monthly_budget is not None
                and estimates[index].status == "known"
                and estimates[index].monthly_total is not None
                and estimates[index].currency == context.budget_currency
                else None
            ),
            "quality": quality_maps[index].get(quality_identity) if quality_identity else None,
            "speed": (
                _bounded_relative(latencies[index], context.latency_target_seconds)
                if latencies[index] is not None and context.latency_target_seconds is not None
                else None
            ),
            "reliability": (
                max(-1.0, min(2 * uptimes[index] - 1, 1.0))
                if uptimes[index] is not None else None
            ),
            "privacy": _privacy_feature(candidate.manifest),
            "familiarity": (
                1.0 if candidate.service_id in authenticated
                else 0.5 if candidate.service_id in installed
                else -1.0 if installed or authenticated
                else None
            ),
            "low_human_effort": (
                1.0 if (candidate.manifest.get("invocation") or {}).get("agent_completable_setup") is True
                else -1.0 if (candidate.manifest.get("invocation") or {}).get("agent_completable_setup") is False
                else None
            ),
            "observed_success": (
                float(context.observed_success[candidate.service_id])
                if candidate.service_id in context.observed_success else None
            ),
        }
        candidate.known_features = tuple(name for name, value in feature_values.items() if value is not None)
        candidate.features = {name: float(value) if value is not None else 0.0 for name, value in feature_values.items()}


def _dot(features: Mapping[str, float], weights: Mapping[str, float]) -> float:
    return sum(float(features.get(name, 0.0)) * float(value) for name, value in weights.items())


def _argmax(candidates: Iterable[AdaptiveCandidate], utility) -> AdaptiveCandidate:
    """Highest utility with stable ascending service_id tie-breaking."""
    return sorted(candidates, key=lambda row: (-utility(row), row.service_id))[0]


def _dominant_candidate(candidates: list[AdaptiveCandidate]) -> AdaptiveCandidate | None:
    """Return a candidate that Pareto-dominates every alternative on shared facts."""
    for candidate in candidates:
        dominates_all = True
        for other in candidates:
            if other is candidate:
                continue
            candidate_known = set(candidate.known_features)
            other_known = set(other.known_features)
            if not other_known or candidate_known != other_known:
                dominates_all = False
                break
            shared = candidate_known
            weakly_better = all(candidate.features[name] >= other.features[name] for name in shared)
            strictly_better = any(candidate.features[name] > other.features[name] for name in shared)
            if not (weakly_better and strictly_better):
                dominates_all = False
                break
        if dominates_all:
            return candidate
    return None


def _question_for(first: AdaptiveCandidate, second: AdaptiveCandidate) -> str:
    differing = sorted(
        set(first.known_features) & set(second.known_features),
        key=lambda name: abs(first.features[name] - second.features[name]),
        reverse=True,
    )
    dimension = _FEATURE_LABELS.get(differing[0], differing[0]) if differing else "长期使用体验"
    return f"这次在 {first.display_name} 和 {second.display_name} 之间，{dimension} 哪个对你更重要？"


def _seed(task: str, model: BayesianLinearPreferenceModel) -> int:
    digest = hashlib.sha256(f"{task}|{model.digest()}".encode()).hexdigest()
    return int(digest[:16], 16)


def _posterior_analysis(
    candidates: list[AdaptiveCandidate],
    model: BayesianLinearPreferenceModel,
    *,
    task: str,
    samples: int = 256,
) -> tuple[AdaptiveCandidate, float, float, dict[str, int]]:
    means = []
    for candidate in candidates:
        mean, variance = model.predict(candidate.features)
        candidate.preference_mean = mean
        candidate.preference_variance = variance
        means.append((mean, candidate.service_id, candidate))
    means.sort(key=lambda row: (-row[0], row[1]))
    chosen = means[0][2]
    rng = random.Random(_seed(task, model))
    regret = 0.0
    wins = {candidate.service_id: 0 for candidate in candidates}
    for _ in range(samples):
        weights = model.sample_weights(rng=rng)
        utilities = [(_dot(candidate.features, weights), candidate.service_id, candidate) for candidate in candidates]
        utilities.sort(key=lambda row: (-row[0], row[1]))
        best_utility, _, best = utilities[0]
        chosen_utility = next(value for value, _, candidate in utilities if candidate is chosen)
        regret += max(best_utility - chosen_utility, 0.0)
        wins[best.service_id] += 1
    return chosen, regret / samples, wins[chosen.service_id] / samples, wins


def adaptive_select(
    task: str,
    *,
    taxonomy: str | None,
    required_functions: Iterable[str] = (),
    agent_reach: str = "cloud",
    user_platform: str = "any",
    require_agent_completable_setup: bool = False,
    library: list[dict] | None = None,
    workload: Workload | Mapping | None = None,
    owner_context: OwnerContext | None = None,
    preference_model: BayesianLinearPreferenceModel | None = None,
    freshness_policy: FreshnessPolicy = "require_fresh",
    now: datetime | None = None,
    policy: AdaptivePolicy = "posterior_mean",
) -> dict[str, Any]:
    """Select, validate an explicit choice, explore safely, or request context."""
    required_functions = tuple(required_functions)
    if not task:
        raise ValueError("task is required")
    if not taxonomy and not required_functions:
        raise ValueError("taxonomy or required_functions is required")
    if policy not in {"posterior_mean", "linucb", "thompson"}:
        raise ValueError(f"unknown adaptive policy: {policy}")
    context = owner_context or OwnerContext()
    model = preference_model or BayesianLinearPreferenceModel(DEFAULT_FEATURES)
    if tuple(model.feature_names) != tuple(DEFAULT_FEATURES):
        raise ValueError("adaptive selector currently requires DEFAULT_FEATURES")
    workload_value = coerce_workload(workload)
    entries = library if library is not None else load_library()
    scoped = [row for row in entries if taxonomy is None or row.get("taxonomy") == taxonomy]
    candidates: list[AdaptiveCandidate] = []
    rejected = []
    forbidden_services = set(context.forbidden_service_ids)
    forbidden_side_effects = set(context.forbidden_side_effects)
    for manifest in scoped:
        service_id = manifest.get("service_id")
        reason = eligibility(
            manifest,
            agent_reach,
            user_platform,
            required_functions,
            require_agent_completable_setup=require_agent_completable_setup,
        )
        assessment = assess_manifest_freshness(manifest, now=now)
        claim_freshness = selection_claim_freshness(manifest, now=now)
        for claim_path, claim_assessment in claim_freshness.items():
            claim_reason = freshness_rejection(claim_assessment, policy=freshness_policy)
            if not reason and claim_reason:
                reason = f"{claim_path}: {claim_reason}"
        operational = manifest.get("operational_constraints") or {}
        risk = operational.get("risk_class", "unknown")
        side_effects = tuple(operational.get("side_effects") or ())
        if not reason and service_id in forbidden_services:
            reason = "owner or organization policy forbids this service"
        if not reason and risk == "unknown" and not context.allow_unknown_risk:
            reason = "risk_class is unknown; explicit allow_unknown_risk is required"
        if not reason and risk != "unknown" and _RISK_ORDER.get(risk, 4) > _RISK_ORDER[context.max_risk]:
            reason = f"risk_class={risk} exceeds owner/organization maximum {context.max_risk}"
        blocked_effects = sorted(set(side_effects) & forbidden_side_effects)
        if not reason and blocked_effects:
            reason = f"forbidden side effects: {blocked_effects}"
        if reason:
            rejected.append({
                "service_id": service_id,
                "reason": reason,
                "freshness": {
                    "manifest": assessment.to_dict(),
                    "claims": {name: value.to_dict() for name, value in claim_freshness.items()},
                },
            })
            continue
        surface = invocation_surface(manifest)
        candidates.append(
            AdaptiveCandidate(
                service_id=surface.service_id,
                display_name=manifest.get("display_name") or surface.service_id,
                manifest=manifest,
                freshness={
                    "manifest": assessment.to_dict(),
                    "claims": {name: value.to_dict() for name, value in claim_freshness.items()},
                },
                risk_class=risk,
                side_effects=side_effects,
            )
        )

    result: dict[str, Any] = {
        "task": task,
        "taxonomy": taxonomy,
        "task_interpretation": {
            "status": "caller_structured",
            "raw_task_used_for_semantic_ranking": False,
            "required_functions": list(required_functions),
        },
        "decision_policy": "adaptive-selection-v0.1-experimental",
        "requested_policy": policy,
        "effective_policy": "hard-gates",
        "preference_model": {
            "digest": model.digest(),
            "observations": model.observations,
            "raw_history_included": False,
        },
        "freshness_policy": freshness_policy,
        "selection_status": "no_eligible",
        "selected": None,
        "reason": "no candidate passed eligibility, policy, and freshness gates",
        "expected_regret": None,
        "preference_confidence": None,
        "voi": {
            "status": "available" if context.interruption_cost is not None else "not_calibrated",
            "interruption_cost": context.interruption_cost,
        },
        "question": None,
        "alternatives": [],
        "rejected": rejected,
    }
    if context.explicit_service_id:
        explicit = next((row for row in candidates if row.service_id == context.explicit_service_id), None)
        if explicit is None:
            result["selection_status"] = "explicit_unavailable"
            result["reason"] = "the owner-specified tool did not pass hard or freshness gates"
            return result
        _build_features(candidates, context=context, workload=workload_value)
        result["selection_status"] = "validated_explicit"
        result["effective_policy"] = "explicit-owner-choice-validation"
        result["selected"] = explicit.public()
        result["reason"] = "owner-specified tool passed eligibility, policy, and freshness validation"
        result["alternatives"] = [row.public() for row in candidates if row is not explicit]
        return result
    if not candidates:
        return result

    _build_features(candidates, context=context, workload=workload_value)
    if len(candidates) == 1:
        result["selection_status"] = "selected_only_eligible"
        result["effective_policy"] = "only-eligible"
        result["selected"] = candidates[0].public()
        result["reason"] = "only one candidate passed the hard and freshness gates"
        return result

    dominant = _dominant_candidate(candidates)
    if dominant is not None:
        result["selection_status"] = "selected_pareto_dominant"
        result["effective_policy"] = "pareto-dominance"
        result["selected"] = dominant.public()
        result["reason"] = "candidate Pareto-dominates every alternative on shared known facts"
        result["alternatives"] = [row.public() for row in candidates if row is not dominant]
        return result

    chosen, regret, confidence, wins = _posterior_analysis(candidates, model, task=task)
    ranked = sorted(candidates, key=lambda row: (-row.preference_mean, row.service_id))
    result["expected_regret"] = round(regret, 6)
    result["preference_confidence"] = round(confidence, 6)
    result["posterior_wins"] = wins
    result["alternatives"] = [row.public() for row in ranked if row is not chosen]

    highest_risk = max((_RISK_ORDER.get(row.risk_class, 4) for row in candidates), default=4)
    consequential = not context.reversible or highest_risk >= _RISK_ORDER["high"]
    if model.observations == 0 and consequential:
        result["selection_status"] = "needs_preference"
        result["effective_policy"] = "clarification-cold-start"
        result["reason"] = "owner preference is unobserved and the decision is consequential"
        result["question"] = _question_for(ranked[0], ranked[1])
        return result
    if (
        context.interruption_cost is not None
        and regret > context.interruption_cost
        and consequential
    ):
        result["selection_status"] = "needs_preference"
        result["effective_policy"] = "clarification-positive-voi"
        result["reason"] = (
            "expected regret of acting exceeds the estimated interruption cost; "
            "clarification has positive value of information"
        )
        result["question"] = _question_for(ranked[0], ranked[1])
        return result

    if model.observations == 0:
        weights = model.sample_weights(rng=random.Random(_seed(task, model)))
        chosen = _argmax(candidates, lambda row: _dot(row.features, weights))
        mode = "cold-start bounded Thompson exploration"
        result["effective_policy"] = "thompson-cold-start"
    elif consequential and policy in {"linucb", "thompson"}:
        chosen = ranked[0]
        mode = "posterior-mean exploitation; exploration disabled by risk policy"
        result["effective_policy"] = "posterior_mean"
    elif policy == "linucb":
        chosen = _argmax(
            candidates,
            lambda row: row.preference_mean + math.sqrt(max(row.preference_variance, 0.0)),
        )
        mode = "bounded LinUCB exploration"
        result["effective_policy"] = "linucb"
    elif policy == "thompson":
        weights = model.sample_weights(rng=random.Random(_seed(task, model)))
        chosen = _argmax(candidates, lambda row: _dot(row.features, weights))
        mode = "bounded Thompson exploration"
        result["effective_policy"] = "thompson"
    else:
        mode = "posterior-mean exploitation"
        result["effective_policy"] = "posterior_mean"
    result["selected"] = chosen.public()
    result["selection_status"] = "selected_exploration" if model.observations == 0 else "selected"
    result["reason"] = (
        f"{mode}; uncertainty is recorded and exploration is allowed only because the action is reversible"
        if not model.observations
        else f"{mode}; owner evidence and uncertainty are recorded in the decision"
    )
    result["alternatives"] = [row.public() for row in ranked if row is not chosen]
    return result


__all__ = ["AdaptiveCandidate", "AdaptivePolicy", "OwnerContext", "adaptive_select"]

"""Experimental per-unit utility scorer for Agent Service Manifest.

v0.2: Weighted average scoring (demo-ready)
v1.0: Filter (hard constraints) + TOPSIS (multi-criteria ranking)
v1.1: Trust delta scoring with exponential decay (Signed Receipts integration)

This module is not the canonical workload-aware selector. Its ``cost_per_unit``
vector compares like units inside curated model sets. Production eligibility,
workload cost, policy gates, and Selection Receipts live in
``asm_protocol.selection``. The legacy API remains importable for compatibility.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────

@dataclass
class ServiceVector:
    """Extracted numeric vector from an ASM manifest for scoring."""
    service_id: str
    display_name: str
    taxonomy: str
    cost_per_unit: float          # representative cost (primary billing dimension)
    quality_score: float          # primary quality metric, normalized to [0, 1]
    latency_seconds: float        # p50 latency in seconds
    uptime: float                 # 0-1
    raw_manifest: dict = field(default_factory=dict, repr=False)


@dataclass
class Constraints:
    """Hard constraints — services that violate any constraint are filtered out."""
    min_quality: float | None = None      # e.g., 0.7
    max_cost: float | None = None         # e.g., 0.10
    max_latency_s: float | None = None    # e.g., 5.0
    min_uptime: float | None = None       # e.g., 0.99
    required_taxonomy: str | None = None  # e.g., "ai.llm.chat"


@dataclass
class Preferences:
    """Soft preferences — weights for scoring dimensions. Must sum to 1.
    
    io_ratio controls how input vs output token costs are blended:
      cost_repr = io_ratio * input_cost + (1 - io_ratio) * output_cost
    Typical values:
      0.3 = chat scenario (short prompts, long responses) — default
      0.8 = RAG scenario (long context, short answers)
      0.1 = creative writing (short prompts, very long outputs)
      0.5 = balanced / translation tasks
    """
    cost: float = 0.4
    quality: float = 0.35
    speed: float = 0.15
    reliability: float = 0.10
    io_ratio: float = 0.3  # input token ratio, default 0.3 (typical chat scenario)

    def __post_init__(self):
        total = self.cost + self.quality + self.speed + self.reliability
        if not math.isclose(total, 1.0, abs_tol=0.01):
            raise ValueError(f"Preference weights must sum to 1.0, got {total:.3f}")
        if not (0.0 <= self.io_ratio <= 1.0):
            raise ValueError(f"io_ratio must be in [0, 1], got {self.io_ratio}")


@dataclass
class ScoredService:
    """A service with its computed score and breakdown."""
    service: ServiceVector
    total_score: float
    breakdown: dict[str, float]
    rank: int = 0
    reasoning: str = ""


# ──────────────────────────────────────────────
# Manifest Parsing
# ──────────────────────────────────────────────

def _parse_latency(s: str | None) -> float:
    """Parse latency string like '800ms', '3s', '~15s' into seconds."""
    if not s:
        return float("inf")
    s = s.strip().lstrip("~").lstrip("<").lstrip(">")
    if s.endswith("ms"):
        return float(s[:-2]) / 1000
    if s.endswith("s"):
        return float(s[:-1])
    if s.endswith("min"):
        return float(s[:-3]) * 60
    try:
        return float(s)
    except ValueError:
        return float("inf")


def _extract_primary_cost(pricing: dict, io_ratio: float = 0.3) -> float:
    """Extract a representative cost from billing_dimensions.
    
    For multi-dimension services (e.g., LLM with input+output tokens),
    uses a weighted estimate:
      cost = io_ratio * input_cost + (1 - io_ratio) * output_cost
    
    Args:
        pricing: The pricing dict from an ASM manifest.
        io_ratio: Input token cost weight (0-1). Default 0.3 (chat scenario).
                  Higher values favor input-heavy workloads (e.g., RAG = 0.8).
    """
    dims = pricing.get("billing_dimensions", [])
    if not dims:
        return 0.0

    # Special handling for LLM input+output token pricing
    input_cost = None
    output_cost = None
    for d in dims:
        dim = d.get("dimension", "")
        cost = d.get("cost_per_unit", 0)
        unit = d.get("unit", "per_1")

        # Normalize to per-unit cost
        if unit == "per_1M":
            cost = cost / 1_000_000
        elif unit == "per_1K":
            cost = cost / 1_000

        if dim == "input_token":
            input_cost = cost
        elif dim == "output_token":
            output_cost = cost

    if input_cost is not None and output_cost is not None:
        return io_ratio * input_cost + (1 - io_ratio) * output_cost

    # Single dimension — use first
    d = dims[0]
    cost = d.get("cost_per_unit", 0)
    unit = d.get("unit", "per_1")
    if unit == "per_1M":
        cost = cost / 1_000_000
    elif unit == "per_1K":
        cost = cost / 1_000
    return cost


def _extract_primary_quality(quality: dict) -> float:
    """Extract primary quality score, normalized to [0, 1]."""
    metrics = quality.get("metrics", [])
    if not metrics:
        return 0.5  # unknown quality → neutral

    m = metrics[0]
    score = m.get("score", 0)
    scale = m.get("scale", "")

    # Normalize based on scale
    if scale == "Elo":
        # LMSYS Elo: roughly 800-1400 range, map to [0, 1]
        return min(max((score - 800) / 600, 0), 1)
    elif scale == "0-100":
        return score / 100
    elif scale == "0-1":
        return score
    elif scale == "1-5":
        return (score - 1) / 4
    elif scale == "lower_is_better":
        # FID-like metrics: lower is better, map 0→1, 50→0
        return max(1 - score / 50, 0)
    else:
        # Best guess: if score > 1, assume 0-100 or similar
        if score > 1:
            return min(score / 100, 1)
        return score


def parse_manifest(manifest: dict, io_ratio: float = 0.3) -> ServiceVector:
    """Parse an ASM manifest JSON into a scoreable ServiceVector.
    
    Args:
        manifest: ASM manifest dict.
        io_ratio: Input token cost weight for multi-dimension pricing.
    """
    pricing = manifest.get("pricing", {})
    quality = manifest.get("quality", {})
    sla = manifest.get("sla", {})

    return ServiceVector(
        service_id=manifest["service_id"],
        display_name=manifest.get("display_name", manifest["service_id"]),
        taxonomy=manifest["taxonomy"],
        cost_per_unit=_extract_primary_cost(pricing, io_ratio=io_ratio),
        quality_score=_extract_primary_quality(quality),
        latency_seconds=_parse_latency(sla.get("latency_p50")),
        uptime=sla.get("uptime", 0.5),
        raw_manifest=manifest,
    )


# ──────────────────────────────────────────────
# Stage 1: Filter (hard constraints)
# ──────────────────────────────────────────────

def filter_services(
    services: list[ServiceVector],
    constraints: Constraints,
) -> list[ServiceVector]:
    """Filter out services that violate hard constraints."""
    result = []
    for s in services:
        if constraints.required_taxonomy:
            if not s.taxonomy.startswith(constraints.required_taxonomy):
                continue
        if constraints.min_quality is not None and s.quality_score < constraints.min_quality:
            continue
        if constraints.max_cost is not None and s.cost_per_unit > constraints.max_cost:
            continue
        if constraints.max_latency_s is not None and s.latency_seconds > constraints.max_latency_s:
            continue
        if constraints.min_uptime is not None and s.uptime < constraints.min_uptime:
            continue
        result.append(s)
    return result


# ──────────────────────────────────────────────
# Stage 2a: Weighted Average Scorer (v0.2)
# ──────────────────────────────────────────────

def _min_max_normalize(values: list[float], invert: bool = False) -> list[float]:
    """Min-max normalize to [0, 1]. If invert, lower raw = higher normalized."""
    if not values:
        return []
    finite_values = [v for v in values if math.isfinite(v)]
    if not finite_values:
        return [1.0] * len(values)
    vmin, vmax = min(finite_values), max(finite_values)
    if vmin == vmax:
        return [1.0 if math.isfinite(v) else 0.0 for v in values]
    if invert:
        return [0.0 if not math.isfinite(v) else (vmax - v) / (vmax - vmin) for v in values]
    return [0.0 if not math.isfinite(v) else (v - vmin) / (vmax - vmin) for v in values]


def score_weighted_average(
    services: list[ServiceVector],
    preferences: Preferences,
) -> list[ScoredService]:
    """Score services using weighted average (ASM v0.2 method)."""
    if not services:
        return []

    costs = [s.cost_per_unit for s in services]
    qualities = [s.quality_score for s in services]
    latencies = [s.latency_seconds for s in services]
    uptimes = [s.uptime for s in services]

    norm_cost = _min_max_normalize(costs, invert=True)       # lower cost → higher score
    norm_quality = _min_max_normalize(qualities, invert=False)  # higher quality → higher score
    norm_speed = _min_max_normalize(latencies, invert=True)     # lower latency → higher score
    norm_uptime = _min_max_normalize(uptimes, invert=False)     # higher uptime → higher score

    results = []
    for i, s in enumerate(services):
        breakdown = {
            "cost": norm_cost[i],
            "quality": norm_quality[i],
            "speed": norm_speed[i],
            "reliability": norm_uptime[i],
        }
        total = (
            preferences.cost * breakdown["cost"]
            + preferences.quality * breakdown["quality"]
            + preferences.speed * breakdown["speed"]
            + preferences.reliability * breakdown["reliability"]
        )
        results.append(ScoredService(
            service=s,
            total_score=round(total, 4),
            breakdown={k: round(v, 4) for k, v in breakdown.items()},
        ))

    results.sort(key=lambda x: x.total_score, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1
        r.reasoning = _generate_reasoning(r, preferences)
    return results


def _generate_reasoning(scored: ScoredService, prefs: Preferences) -> str:
    """Generate a human-readable reasoning for the score."""
    s = scored.service
    top_dim = max(scored.breakdown, key=lambda k: getattr(prefs, k) * scored.breakdown[k])
    return (
        f"{s.display_name} scored {scored.total_score:.3f} "
        f"(cost={scored.breakdown['cost']:.2f}, "
        f"quality={scored.breakdown['quality']:.2f}, "
        f"speed={scored.breakdown['speed']:.2f}, "
        f"reliability={scored.breakdown['reliability']:.2f}). "
        f"Strongest weighted dimension: {top_dim}."
    )


# ──────────────────────────────────────────────
# Stage 2b: TOPSIS Scorer (v1.0)
# ──────────────────────────────────────────────

def score_topsis(
    services: list[ServiceVector],
    preferences: Preferences,
) -> list[ScoredService]:
    """Score services using TOPSIS (Technique for Order Preference by
    Similarity to Ideal Solution).

    Steps:
    1. Build decision matrix (m services × 4 criteria)
    2. Normalize using vector normalization
    3. Apply weights
    4. Find positive ideal (A+) and negative ideal (A-) solutions
    5. Calculate distance to A+ and A- for each service
    6. Compute closeness coefficient: C = d- / (d+ + d-)
    7. Rank by C (higher = better)
    """
    if not services:
        return []

    n = len(services)

    # Step 1: Decision matrix — columns: cost(minimize), quality(maximize), speed(minimize latency), reliability(maximize)
    # For TOPSIS, we need to know which criteria are benefit (higher=better) vs cost (lower=better)
    raw = []
    for s in services:
        raw.append([
            s.cost_per_unit,        # cost → minimize
            s.quality_score,        # quality → maximize
            s.latency_seconds,      # latency → minimize
            s.uptime,               # uptime → maximize
        ])

    # Benefit criteria (True = higher is better, False = lower is better)
    is_benefit = [False, True, False, True]
    weights = [preferences.cost, preferences.quality, preferences.speed, preferences.reliability]
    raw = _sanitize_decision_matrix(raw, is_benefit)

    # Step 2: Vector normalization
    num_criteria = 4
    norm = [[0.0] * num_criteria for _ in range(n)]
    for j in range(num_criteria):
        col_sum_sq = math.sqrt(sum(raw[i][j] ** 2 for i in range(n)))
        if col_sum_sq == 0:
            for i in range(n):
                norm[i][j] = 0
        else:
            for i in range(n):
                norm[i][j] = raw[i][j] / col_sum_sq

    # Step 3: Weighted normalized matrix
    weighted = [[norm[i][j] * weights[j] for j in range(num_criteria)] for i in range(n)]

    # Step 4: Ideal solutions
    a_pos = []
    a_neg = []
    for j in range(num_criteria):
        col = [weighted[i][j] for i in range(n)]
        if is_benefit[j]:
            a_pos.append(max(col))
            a_neg.append(min(col))
        else:
            a_pos.append(min(col))
            a_neg.append(max(col))

    # Step 5: Distances
    d_pos = []
    d_neg = []
    for i in range(n):
        dp = math.sqrt(sum((weighted[i][j] - a_pos[j]) ** 2 for j in range(num_criteria)))
        dn = math.sqrt(sum((weighted[i][j] - a_neg[j]) ** 2 for j in range(num_criteria)))
        d_pos.append(dp)
        d_neg.append(dn)

    # Step 6: Closeness coefficient
    results = []
    for i, s in enumerate(services):
        denom = d_pos[i] + d_neg[i]
        c = d_neg[i] / denom if denom > 0 else 0.5

        # Build breakdown from weighted normalized values
        labels = ["cost", "quality", "speed", "reliability"]
        breakdown = {}
        for j, label in enumerate(labels):
            # Convert to 0-1 benefit score for display
            col = [weighted[k][j] for k in range(n)]
            finite_col = [v for v in col if math.isfinite(v)]
            if not finite_col:
                breakdown[label] = 1.0
                continue
            vmin, vmax = min(finite_col), max(finite_col)
            if not math.isfinite(weighted[i][j]):
                breakdown[label] = 0.0
                continue
            if vmax == vmin:
                breakdown[label] = 1.0
            elif is_benefit[j]:
                breakdown[label] = round((weighted[i][j] - vmin) / (vmax - vmin), 4)
            else:
                breakdown[label] = round((vmax - weighted[i][j]) / (vmax - vmin), 4)

        results.append(ScoredService(
            service=s,
            total_score=round(c, 4),
            breakdown=breakdown,
        ))

    results.sort(key=lambda x: x.total_score, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1
        r.reasoning = _generate_reasoning(r, preferences)
    return results


def _sanitize_decision_matrix(raw: list[list[float]], is_benefit: list[bool]) -> list[list[float]]:
    """Replace non-finite criteria before TOPSIS vector normalization.

    Unknown values should not produce NaN scores. If an entire criterion is
    unknown, it becomes neutral (all zeros). If only some services are unknown,
    unknown cost criteria are treated as worst finite values and unknown benefit
    criteria as worst finite values.
    """
    if not raw:
        return raw
    cleaned = [row[:] for row in raw]
    num_criteria = len(raw[0])
    for j in range(num_criteria):
        finite = [row[j] for row in raw if math.isfinite(row[j])]
        if not finite:
            replacement = 0.0
        elif is_benefit[j]:
            replacement = min(finite)
        else:
            replacement = max(finite)
        for row in cleaned:
            if not math.isfinite(row[j]):
                row[j] = replacement
    return cleaned


# ──────────────────────────────────────────────
# Stage 3: Trust Delta Scoring (v1.1)
# ──────────────────────────────────────────────

@dataclass
class ReceiptRecord:
    """A single execution receipt recording actual service delivery metrics."""
    service_id: str
    timestamp: float                  # Unix timestamp of execution
    actual_latency_seconds: float     # Measured p50 latency
    actual_quality_score: float       # Measured quality (normalized 0-1)
    actual_uptime: float              # Observed availability (0-1)
    actual_cost_per_unit: float       # Actual billed cost per unit

@dataclass
class TrustScore:
    """Computed trust score for a service based on receipt history."""
    service_id: str
    trust_score: float                # Overall trust score (0-1, higher = more trustworthy)
    delta_breakdown: dict[str, float] # Per-dimension trust deltas
    num_receipts: int                 # Number of receipts used
    confidence: float                 # Confidence level (0-1, based on sample size)
    reasoning: str


def compute_trust_delta(
    declared: float,
    actual: float,
) -> float:
    """Compute trust delta between declared and actual values.

    trust_delta = |declared - actual| / declared

    Returns 0.0 for perfect match, >1.0 for severe deviation.
    A delta of 0.5 means 50% deviation from declared value.
    """
    if declared == 0:
        return 0.0 if actual == 0 else 1.0
    return abs(declared - actual) / abs(declared)


def cost_delta_from_receipt(
    manifest: dict,
    receipt: dict,
) -> dict:
    """Recompute the receipt's cost from the manifest's published pricing,
    and surface the aggregate delta as a first-class Trust Delta signal.

    Per RFC v0.1 (docs/rfcs/trust-delta-receipt-extension-v0.1.md) §2.4:
    the trust signal is the AGGREGATE delta across all billing dimensions,
    not per-dimension. Per-dimension breakdown is preserved as a diagnostic.

    Args:
        manifest: ASM manifest dict (must contain `pricing.billing_dimensions`).
        receipt: Receipt body matching the envelope schema. Reads
            `billing.cost`, `billing.observed_input_tokens`,
            `billing.observed_output_tokens`, `billing.dimension`,
            `billing.quantity` as available.

    Returns:
        dict with:
          - `claimed_cost`: receipt.billing.cost
          - `recomputed_cost`: sum across billing_dimensions of
                               (observed_quantity * manifest_unit_cost)
          - `cost_delta`: claimed_cost - recomputed_cost (signed)
          - `per_dimension`: diagnostic dict mapping dimension -> recomputed cost
          - `note`: free-form string explaining any missing fields / fallbacks

    The delta is signed (not absolute): a positive delta means the publisher
    over-claims relative to the manifest rate; negative means under-claims.
    Trust Delta's downstream scoring decides what to do with the sign.
    """
    billing = (receipt or {}).get("billing") or {}
    claimed_cost = float(billing.get("cost", 0) or 0)

    pricing = (manifest or {}).get("pricing") or {}
    dimensions = pricing.get("billing_dimensions") or []
    if not dimensions:
        return {
            "claimed_cost": claimed_cost,
            "recomputed_cost": 0.0,
            "cost_delta": claimed_cost,
            "per_dimension": {},
            "note": "manifest pricing.billing_dimensions missing or empty",
        }

    # Map observed quantity for each manifest dimension. Receipt fields are:
    #   billing.observed_input_tokens / observed_output_tokens (LLM-shaped)
    #   billing.quantity (single-dimension shaped, e.g. pipeline_run)
    obs_input = float(billing.get("observed_input_tokens", 0) or 0)
    obs_output = float(billing.get("observed_output_tokens", 0) or 0)
    obs_quantity = float(billing.get("quantity", 0) or 0)
    primary_dim = billing.get("dimension")

    per_dimension: dict[str, float] = {}
    total = 0.0
    note_parts: list[str] = []

    for entry in dimensions:
        dim_name = entry.get("dimension")
        unit = (entry.get("unit") or "").lower()
        cost_per_unit = float(entry.get("cost_per_unit", 0) or 0)

        # Resolve observed quantity for this dimension.
        if dim_name == "input_token":
            qty = obs_input
            multiplier = 1.0 / 1_000_000 if unit in ("per_1m", "per_1m_tokens") else 1.0
        elif dim_name == "output_token":
            qty = obs_output
            multiplier = 1.0 / 1_000_000 if unit in ("per_1m", "per_1m_tokens") else 1.0
        elif dim_name == primary_dim:
            qty = obs_quantity
            multiplier = 1.0
        else:
            note_parts.append(f"no observed quantity for dimension '{dim_name}'")
            continue

        contribution = qty * cost_per_unit * multiplier
        per_dimension[dim_name] = contribution
        total += contribution

    cost_delta = claimed_cost - total
    return {
        "claimed_cost": claimed_cost,
        "recomputed_cost": total,
        "cost_delta": cost_delta,
        "per_dimension": per_dimension,
        "note": "; ".join(note_parts) if note_parts else "ok",
    }


def exponential_decay_weight(
    timestamp: float,
    now: float | None = None,
    half_life_seconds: float = 7 * 24 * 3600,  # 1 week default
) -> float:
    """Compute exponential decay weight for a receipt based on age.

    More recent receipts have higher weight. The weight halves every
    `half_life_seconds`.

    w(t) = exp(-ln(2) * age / half_life)

    Args:
        timestamp: Unix timestamp of the receipt
        now: Current time (defaults to time.time())
        half_life_seconds: Time for weight to halve (default: 1 week)

    Returns:
        Weight in (0, 1], where 1.0 = just now, 0.5 = one half-life ago
    """
    if now is None:
        now = time.time()
    age = max(now - timestamp, 0)
    decay_constant = math.log(2) / half_life_seconds
    return math.exp(-decay_constant * age)


def compute_trust_score(
    service: ServiceVector,
    receipts: list[ReceiptRecord],
    half_life_seconds: float = 7 * 24 * 3600,
    now: float | None = None,
) -> TrustScore:
    """Compute trust score for a service using receipt history with
    exponential decay weighting.

    For each dimension (cost, quality, latency, uptime), computes:
    1. Trust delta per receipt: |declared - actual| / declared
    2. Weighted average delta using exponential decay (recent receipts matter more)
    3. Overall trust score: 1 - mean(dimension_deltas), clamped to [0, 1]

    Confidence increases with more receipts (asymptotic to 1.0).

    Args:
        service: The service's declared values (from manifest)
        receipts: Historical execution receipts for this service
        half_life_seconds: Decay half-life (default: 1 week)
        now: Current time for decay calculation

    Returns:
        TrustScore with overall score, per-dimension breakdown, and reasoning
    """
    if not receipts:
        return TrustScore(
            service_id=service.service_id,
            trust_score=0.5,  # Neutral — no data
            delta_breakdown={},
            num_receipts=0,
            confidence=0.0,
            reasoning=f"{service.display_name} has no receipt history. Trust score is neutral (0.5).",
        )

    if now is None:
        now = time.time()

    # Compute per-dimension weighted deltas
    dimensions = {
        "cost": ("cost_per_unit", "actual_cost_per_unit"),
        "quality": ("quality_score", "actual_quality_score"),
        "latency": ("latency_seconds", "actual_latency_seconds"),
        "uptime": ("uptime", "actual_uptime"),
    }

    delta_breakdown: dict[str, float] = {}

    for dim_name, (declared_attr, actual_attr) in dimensions.items():
        declared_val = getattr(service, declared_attr)
        weighted_delta_sum = 0.0
        weight_sum = 0.0

        for receipt in receipts:
            actual_val = getattr(receipt, actual_attr)
            delta = compute_trust_delta(declared_val, actual_val)
            weight = exponential_decay_weight(receipt.timestamp, now, half_life_seconds)
            weighted_delta_sum += delta * weight
            weight_sum += weight

        avg_delta = weighted_delta_sum / weight_sum if weight_sum > 0 else 0.0
        delta_breakdown[dim_name] = round(avg_delta, 4)

    # Overall trust score: 1 - mean(deltas), clamped to [0, 1]
    mean_delta = sum(delta_breakdown.values()) / len(delta_breakdown) if delta_breakdown else 0.0
    trust_score = max(0.0, min(1.0, 1.0 - mean_delta))

    # Confidence: asymptotic based on receipt count
    # confidence = 1 - exp(-n / 5), reaches ~0.86 at 10 receipts, ~0.98 at 20
    confidence = 1.0 - math.exp(-len(receipts) / 5.0)

    # Generate reasoning
    worst_dim = max(delta_breakdown, key=delta_breakdown.get) if delta_breakdown else "N/A"
    best_dim = min(delta_breakdown, key=delta_breakdown.get) if delta_breakdown else "N/A"
    reasoning = (
        f"{service.display_name} trust={trust_score:.3f} "
        f"(confidence={confidence:.2f}, {len(receipts)} receipts). "
        f"Most accurate: {best_dim} (delta={delta_breakdown.get(best_dim, 0):.3f}). "
        f"Least accurate: {worst_dim} (delta={delta_breakdown.get(worst_dim, 0):.3f})."
    )

    return TrustScore(
        service_id=service.service_id,
        trust_score=round(trust_score, 4),
        delta_breakdown=delta_breakdown,
        num_receipts=len(receipts),
        confidence=round(confidence, 4),
        reasoning=reasoning,
    )


def adjust_scores_with_trust(
    scored_services: list[ScoredService],
    trust_scores: dict[str, TrustScore],
    trust_weight: float = 0.2,
) -> list[ScoredService]:
    """Adjust service rankings by incorporating trust scores.

    Final score = (1 - trust_weight) * original_score + trust_weight * trust_score * confidence

    Services with high trust (accurate declarations) get a boost.
    Services with low trust (inflated claims) get penalized.
    Services with no receipt data are unaffected (trust=0.5, confidence=0).

    Args:
        scored_services: Original scored services from TOPSIS or weighted average
        trust_scores: Map of service_id → TrustScore
        trust_weight: How much trust affects the final score (0-1, default 0.2)

    Returns:
        Re-ranked list of ScoredService with trust-adjusted scores
    """
    adjusted = []
    for scored in scored_services:
        sid = scored.service.service_id
        ts = trust_scores.get(sid)

        if ts and ts.confidence > 0:
            trust_adjustment = ts.trust_score * ts.confidence
            new_score = (1 - trust_weight) * scored.total_score + trust_weight * trust_adjustment
            new_breakdown = dict(scored.breakdown)
            new_breakdown["trust"] = round(trust_adjustment, 4)
            adjusted.append(ScoredService(
                service=scored.service,
                total_score=round(new_score, 4),
                breakdown=new_breakdown,
                reasoning=f"{scored.reasoning} Trust: {ts.reasoning}",
            ))
        else:
            adjusted.append(scored)

    adjusted.sort(key=lambda x: x.total_score, reverse=True)
    for i, r in enumerate(adjusted):
        r.rank = i + 1
    return adjusted


# ──────────────────────────────────────────────
# High-level API
# ──────────────────────────────────────────────

def select_service(
    manifests: list[dict],
    constraints: Constraints | None = None,
    preferences: Preferences | None = None,
    method: str = "topsis",
) -> list[ScoredService]:
    """Run the experimental TOPSIS/weighted-average utility pipeline.

    Do not use this function as a monthly-cost selector across unlike billing
    units. Use ``asm_protocol.selection.select`` for the canonical contract.
    
    Args:
        manifests: List of ASM manifest dicts
        constraints: Hard constraints for filtering (optional)
        preferences: Soft preference weights (optional, defaults to balanced)
        method: Scoring method — 'weighted_average' or 'topsis'
    
    Returns:
        Ranked list of ScoredService objects
    """
    if preferences is None:
        preferences = Preferences()
    if constraints is None:
        constraints = Constraints()

    # Parse manifests（pass io_ratio to support configurable cost normalization）
    services = [parse_manifest(m, io_ratio=preferences.io_ratio) for m in manifests]

    # Stage 1: Filter
    filtered = filter_services(services, constraints)

    if not filtered:
        return []

    # Stage 2: Score
    if method == "topsis":
        return score_topsis(filtered, preferences)
    else:
        return score_weighted_average(filtered, preferences)


def load_manifests(directory: str | Path) -> list[dict]:
    """Load all .asm.json files from a directory."""
    path = Path(directory)
    manifests = []
    for f in sorted(path.glob("*.asm.json")):
        with open(f, encoding="utf-8") as fp:
            manifests.append(json.load(fp))
    return manifests


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

def _print_results(results: list[ScoredService], title: str):
    """Pretty-print scoring results."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    for r in results:
        marker = " ← BEST" if r.rank == 1 else ""
        print(f"\n  #{r.rank} {r.service.display_name} — score: {r.total_score:.4f}{marker}")
        print(f"     {r.reasoning}")
        print(f"     cost=${r.service.cost_per_unit:.6f}/unit | "
              f"quality={r.service.quality_score:.3f} | "
              f"latency={r.service.latency_seconds:.2f}s | "
              f"uptime={r.service.uptime:.3f}")
    print()


def main():
    """Demo: load manifests and run through multiple preference scenarios."""
    import sys

    # Determine manifest directory
    script_dir = Path(__file__).parent
    manifest_dir = script_dir.parent / "manifests"

    if not manifest_dir.exists():
        print(f"Error: manifest directory not found at {manifest_dir}")
        sys.exit(1)

    manifests = load_manifests(manifest_dir)
    if not manifests:
        print(f"No .asm.json files found in {manifest_dir}")
        sys.exit(1)

    print(f"Loaded {len(manifests)} ASM manifests from {manifest_dir}")
    for m in manifests:
        print(f"  • {m.get('display_name', m['service_id'])} ({m['taxonomy']})")

    # ── Scenario 1: Cost-first (same taxonomy) ──
    llm_manifests = [m for m in manifests if m["taxonomy"].startswith("ai.llm")]
    if len(llm_manifests) >= 2:
        results = select_service(
            llm_manifests,
            preferences=Preferences(cost=0.5, quality=0.3, speed=0.15, reliability=0.05),
            method="topsis",
        )
        _print_results(results, "Scenario: LLM — Cost Priority (TOPSIS)")

    # ── Scenario 2: Quality-first (same taxonomy) ──
    if len(llm_manifests) >= 2:
        results = select_service(
            llm_manifests,
            preferences=Preferences(cost=0.1, quality=0.7, speed=0.15, reliability=0.05),
            method="topsis",
        )
        _print_results(results, "Scenario: LLM — Quality Priority (TOPSIS)")

    # ── Scenario 3: Cross-category (all services, balanced) ──
    results_wa = select_service(
        manifests,
        preferences=Preferences(cost=0.3, quality=0.3, speed=0.2, reliability=0.2),
        method="weighted_average",
    )
    _print_results(results_wa, "Scenario: Cross-Category — Balanced (Weighted Average)")

    results_topsis = select_service(
        manifests,
        preferences=Preferences(cost=0.3, quality=0.3, speed=0.2, reliability=0.2),
        method="topsis",
    )
    _print_results(results_topsis, "Scenario: Cross-Category — Balanced (TOPSIS)")

    # ── Scenario 4: With constraints ──
    results_filtered = select_service(
        manifests,
        constraints=Constraints(max_latency_s=10),
        preferences=Preferences(cost=0.4, quality=0.4, speed=0.1, reliability=0.1),
        method="topsis",
    )
    _print_results(results_filtered, "Scenario: Filtered (latency ≤ 10s) — Cost+Quality (TOPSIS)")


if __name__ == "__main__":
    main()

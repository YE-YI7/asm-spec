"""Workload-aware cost estimation for ASM manifests.

The estimator intentionally refuses to turn unlike billing dimensions into a
made-up monthly scalar.  Callers must supply usage for metered dimensions and
an amortization period for one-time purchases.  Unstructured free-tier prose
is recorded as an uncertainty, never silently treated as unlimited free use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isfinite

_UNIT_SCALE = {"per_1": 1.0, "per_1K": 1_000.0, "per_1M": 1_000_000.0}
_ONE_TIME_DIMENSIONS = {"license", "purchase", "one_time", "one-time"}


@dataclass(frozen=True)
class Workload:
    """Expected monthly usage by manifest billing-dimension name."""

    monthly_units: Mapping[str, float] | None = None
    amortization_months: int | None = None


def coerce_workload(value: Workload | Mapping | None) -> Workload:
    """Accept the typed SDK object or its JSON/API mapping form."""
    if value is None:
        return Workload()
    if isinstance(value, Workload):
        return value
    if isinstance(value, Mapping):
        allowed = {"monthly_units", "amortization_months"}
        extra = set(value) - allowed
        if extra:
            raise ValueError(f"unknown workload fields: {sorted(extra)}")
        monthly_units = value.get("monthly_units")
        if monthly_units is not None and not isinstance(monthly_units, Mapping):
            raise ValueError("workload.monthly_units must be an object")
        months = value.get("amortization_months")
        if months is not None and (
            isinstance(months, bool) or not isinstance(months, int)
        ):
            raise ValueError("workload.amortization_months must be an integer")
        return Workload(monthly_units=monthly_units, amortization_months=months)
    raise TypeError("workload must be Workload, a mapping, or None")


@dataclass(frozen=True)
class CostEstimate:
    """A monthly estimate plus the evidence boundary behind it."""

    status: str
    monthly_total: float | None
    currency: str | None
    assumptions: tuple[str, ...] = ()
    unknown_dimensions: tuple[str, ...] = ()
    lower_bound: float | None = None

    def to_dict(self) -> dict:
        value = asdict(self)
        value["assumptions"] = list(self.assumptions)
        value["unknown_dimensions"] = list(self.unknown_dimensions)
        return value


def _valid_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number >= 0 and isfinite(number) else None


def estimate_monthly_cost(
    manifest: dict,
    workload: Workload | Mapping | None = None,
) -> CostEstimate:
    """Estimate monthly cost without inventing workload or free-tier limits."""
    workload = coerce_workload(workload)
    usage = dict(workload.monthly_units or {})
    pricing = manifest.get("pricing") or {}
    dimensions = pricing.get("billing_dimensions") or []
    has_unstructured_free_tier = bool(pricing.get("free_tier")) or (
        "free_tier" in ((manifest.get("payment") or {}).get("methods") or [])
    )

    if not dimensions:
        return CostEstimate(
            status="unknown",
            monthly_total=None,
            currency=None,
            assumptions=("no billing dimensions were declared",),
            unknown_dimensions=("pricing",),
        )

    currencies = {d.get("currency") for d in dimensions if d.get("currency")}
    if len(currencies) != 1:
        return CostEstimate(
            status="unknown",
            monthly_total=None,
            currency=None,
            assumptions=("billing dimensions do not declare one comparable currency",),
            unknown_dimensions=tuple(
                str(d.get("dimension") or "unnamed") for d in dimensions
            ),
        )

    currency = next(iter(currencies))
    known_total = 0.0
    unknown: list[str] = []
    assumptions: list[str] = []

    for entry in dimensions:
        dimension = str(entry.get("dimension") or "unnamed")
        unit = str(entry.get("unit") or "")
        cost = _valid_number(entry.get("cost_per_unit"))
        if cost is None:
            unknown.append(dimension)
            continue

        if unit == "per_month":
            quantity = _valid_number(usage.get(dimension, 1.0))
            if quantity is None:
                unknown.append(dimension)
            else:
                known_total += cost * quantity
                if dimension not in usage:
                    assumptions.append(f"{dimension}: one billed unit per month")
            continue

        if unit == "per_year":
            quantity = _valid_number(usage.get(dimension, 1.0))
            if quantity is None:
                unknown.append(dimension)
            else:
                known_total += cost * quantity / 12.0
                if dimension not in usage:
                    assumptions.append(f"{dimension}: one billed unit per year")
            continue

        if dimension.lower() in _ONE_TIME_DIMENSIONS and unit == "per_1":
            months = workload.amortization_months
            quantity = _valid_number(usage.get(dimension, 1.0))
            if not months or months <= 0 or quantity is None:
                unknown.append(dimension)
                assumptions.append(f"{dimension}: amortization period required")
            else:
                known_total += cost * quantity / months
                assumptions.append(f"{dimension}: amortized over {months} months")
            continue

        scale = _UNIT_SCALE.get(unit)
        quantity = _valid_number(usage.get(dimension))
        if cost == 0 and not has_unstructured_free_tier and scale is not None:
            # A declared uncapped zero-price usage dimension stays zero at any
            # workload. Free-tier zeroes are excluded because their cap is unknown.
            continue
        if scale is None or quantity is None:
            unknown.append(dimension)
            assumptions.append(
                f"{dimension}: expected monthly usage required for {unit or 'unknown unit'}"
            )
        else:
            known_total += cost * quantity / scale

    if has_unstructured_free_tier:
        assumptions.append(
            "unstructured free-tier claim not applied; allowance and reset rules are unknown"
        )
        unknown.append("free_tier_allowance")

    unknown = list(dict.fromkeys(unknown))
    if unknown:
        lower_bound = 0.0 if has_unstructured_free_tier else known_total
        return CostEstimate(
            status="partial"
            if known_total > 0
            or any(_valid_number(d.get("cost_per_unit")) == 0 for d in dimensions)
            else "unknown",
            monthly_total=None,
            currency=currency,
            assumptions=tuple(dict.fromkeys(assumptions)),
            unknown_dimensions=tuple(unknown),
            lower_bound=round(lower_bound, 12),
        )
    return CostEstimate(
        status="known",
        monthly_total=round(known_total, 12),
        currency=currency,
        assumptions=tuple(dict.fromkeys(assumptions)),
        lower_bound=round(known_total, 12),
    )


def cost_sort_key(estimate: CostEstimate) -> tuple[int, float]:
    """Known comparable totals rank first; uncertainty never masquerades as zero."""
    if estimate.status == "known" and estimate.monthly_total is not None:
        return (0, estimate.monthly_total)
    if estimate.status == "partial" and estimate.lower_bound is not None:
        return (1, estimate.lower_bound)
    return (2, float("inf"))

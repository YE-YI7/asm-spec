"""Cost-estimation contract tests: no invented workload or free allowance."""

from __future__ import annotations

from asm_protocol.cost import Workload, estimate_monthly_cost


def manifest(*dimensions: dict, free_tier: bool = False) -> dict:
    value = {
        "pricing": {"billing_dimensions": list(dimensions)},
        "payment": {"methods": []},
    }
    if free_tier:
        value["pricing"]["free_tier"] = "limits vary by plan"
        value["payment"]["methods"] = ["free_tier"]
    return value


def test_monthly_and_yearly_recurring_costs_normalize_without_fake_divisors():
    result = estimate_monthly_cost(
        manifest(
            {
                "dimension": "seat",
                "unit": "per_month",
                "cost_per_unit": 10,
                "currency": "USD",
            },
            {
                "dimension": "support",
                "unit": "per_year",
                "cost_per_unit": 120,
                "currency": "USD",
            },
        )
    )
    assert result.status == "known"
    assert result.monthly_total == 20


def test_metered_cost_requires_workload_then_scales_monotonically():
    value = manifest(
        {
            "dimension": "api_call",
            "unit": "per_1K",
            "cost_per_unit": 2,
            "currency": "USD",
        }
    )
    unknown = estimate_monthly_cost(value)
    low = estimate_monthly_cost(value, Workload(monthly_units={"api_call": 1_000}))
    high = estimate_monthly_cost(value, Workload(monthly_units={"api_call": 3_000}))
    assert unknown.status == "unknown" and unknown.monthly_total is None
    assert low.monthly_total == 2
    assert high.monthly_total == 6
    assert high.monthly_total >= low.monthly_total


def test_one_time_license_requires_explicit_amortization():
    value = manifest(
        {
            "dimension": "license",
            "unit": "per_1",
            "cost_per_unit": 120,
            "currency": "USD",
        }
    )
    assert estimate_monthly_cost(value).status == "unknown"
    result = estimate_monthly_cost(value, Workload(amortization_months=12))
    assert result.status == "known" and result.monthly_total == 10


def test_unstructured_free_tier_never_becomes_known_zero():
    value = manifest(
        {
            "dimension": "api_call",
            "unit": "per_1",
            "cost_per_unit": 0,
            "currency": "USD",
        },
        free_tier=True,
    )
    result = estimate_monthly_cost(value)
    assert result.status in {"partial", "unknown"}
    assert result.monthly_total is None
    assert "free_tier_allowance" in result.unknown_dimensions
    assert result.lower_bound == 0


def test_zero_cost_without_a_free_tier_cap_is_known_zero():
    value = manifest(
        {
            "dimension": "api_call",
            "unit": "per_1",
            "cost_per_unit": 0,
            "currency": "USD",
        }
    )
    result = estimate_monthly_cost(value)
    assert result.status == "known" and result.monthly_total == 0


def test_multiple_currencies_are_not_silently_compared():
    value = manifest(
        {
            "dimension": "seat",
            "unit": "per_month",
            "cost_per_unit": 10,
            "currency": "USD",
        },
        {
            "dimension": "support",
            "unit": "per_month",
            "cost_per_unit": 10,
            "currency": "EUR",
        },
    )
    result = estimate_monthly_cost(value)
    assert result.status == "unknown" and result.currency is None

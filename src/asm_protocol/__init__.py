"""Canonical Python SDK surface for Agent Service Manifest."""

from .cost import CostEstimate, Workload, coerce_workload, estimate_monthly_cost
from .adaptive import OwnerContext, adaptive_select
from .freshness import assess_manifest_freshness, freshness_rejection, invocation_surface
from .preferences import BayesianLinearPreferenceModel, PreferenceEvent, PreferenceLedger
from .selection import select
from .version import SELECTOR_NAME, __version__

__all__ = [
    "SELECTOR_NAME",
    "CostEstimate",
    "OwnerContext",
    "BayesianLinearPreferenceModel",
    "PreferenceEvent",
    "PreferenceLedger",
    "Workload",
    "__version__",
    "coerce_workload",
    "adaptive_select",
    "assess_manifest_freshness",
    "estimate_monthly_cost",
    "freshness_rejection",
    "invocation_surface",
    "select",
]

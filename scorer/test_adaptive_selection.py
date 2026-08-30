from __future__ import annotations

from datetime import datetime, timezone

from asm_protocol.adaptive import OwnerContext, adaptive_select
from asm_protocol.preferences import BayesianLinearPreferenceModel, DEFAULT_FEATURES


NOW = datetime(2026, 8, 31, tzinfo=timezone.utc)


def _manifest(
    service_id: str,
    *,
    monthly_cost: float,
    privacy: str,
    risk: str = "low",
    interface: str = "mcp",
    verified: str = "2026-08-30T00:00:00Z",
    quality_name: str = "same_benchmark",
    quality_score: float = 0.8,
) -> dict:
    return {
        "asm_version": "0.3",
        "service_id": service_id,
        "taxonomy": "tool.research.web",
        "display_name": service_id.split("/")[-1].split("@")[0],
        "provenance": {
            "source_url": "https://example.test/tool",
            "retrieved_at": verified,
            "last_verified_at": verified,
            "verification_status": "manual_verified",
        },
        "capabilities": {"functions": ["web_search"]},
        "invocation": {
            "interface": interface,
            "reach": "cloud",
            "agent_operable": True,
            "agent_completable_setup": True,
            "platforms": ["any"],
        },
        "usage_terms": {"automation_allowed": "yes"},
        "pricing": {
            "billing_dimensions": [
                {
                    "dimension": "subscription",
                    "unit": "per_month",
                    "cost_per_unit": monthly_cost,
                    "currency": "USD",
                }
            ]
        },
        "quality": {
            "metrics": [
                {"name": quality_name, "score": quality_score, "scale": "0-1"}
            ]
        },
        "sla": {"latency_p50": "500ms", "uptime": 0.99},
        "data_governance": {
            "data_owner": "user" if privacy == "private" else "provider",
            "exportable": privacy == "private",
            "trains_on_user_data": "no" if privacy == "private" else "yes",
        },
        "operational_constraints": {
            "risk_class": risk,
            "side_effects": ["read_only"],
            "approval": {"required": "never"},
        },
    }


def _library():
    return [
        _manifest("example/private@1", monthly_cost=20, privacy="private"),
        _manifest("example/cheap@1", monthly_cost=2, privacy="cloud"),
    ]


def _select(**kwargs):
    return adaptive_select(
        "research current agent tooling",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=_library(),
        now=NOW,
        **kwargs,
    )


def test_explicit_owner_choice_is_validated_not_overridden_by_price():
    result = _select(
        owner_context=OwnerContext(explicit_service_id="example/private@1")
    )
    assert result["selection_status"] == "validated_explicit"
    assert result["selected"]["service_id"] == "example/private@1"


def test_stale_explicit_choice_is_not_silently_replaced():
    library = [
        _manifest(
            "example/private@1",
            monthly_cost=20,
            privacy="private",
            verified="2026-01-01T00:00:00Z",
        ),
        _manifest("example/cheap@1", monthly_cost=2, privacy="cloud"),
    ]
    result = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=library,
        now=NOW,
        owner_context=OwnerContext(explicit_service_id="example/private@1"),
    )
    assert result["selection_status"] == "explicit_unavailable"
    assert result["selected"] is None


def test_unseen_owner_is_not_interrupted_for_low_risk_reversible_exploration():
    result = _select(owner_context=OwnerContext(reversible=True, monthly_budget=20))
    assert result["selection_status"] == "selected_exploration"
    assert result["question"] is None
    assert result["preference_model"]["observations"] == 0
    assert result["task_interpretation"]["raw_task_used_for_semantic_ranking"] is False


def test_unseen_owner_is_asked_for_consequential_choice():
    result = _select(owner_context=OwnerContext(reversible=False, monthly_budget=20))
    assert result["selection_status"] == "needs_preference"
    assert result["selected"] is None
    assert result["question"]


def test_owner_evidence_changes_the_selected_tool():
    model = BayesianLinearPreferenceModel(DEFAULT_FEATURES)
    for _ in range(5):
        model.update({"privacy": 1.0}, 1.0)
    result = _select(
        owner_context=OwnerContext(reversible=True, monthly_budget=20),
        preference_model=model,
    )
    assert result["selection_status"] == "selected"
    assert result["selected"]["service_id"] == "example/private@1"
    assert result["preference_model"]["observations"] == 5


def test_incomparable_quality_benchmarks_are_not_coerced():
    library = [
        _manifest("example/a@1", monthly_cost=2, privacy="private", quality_name="metric_a"),
        _manifest("example/b@1", monthly_cost=3, privacy="cloud", quality_name="metric_b"),
    ]
    result = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=library,
        now=NOW,
        owner_context=OwnerContext(reversible=True),
    )
    rows = [result["selected"]] + result["alternatives"]
    assert all("quality" not in row["known_features"] for row in rows)


def test_strict_freshness_gate_refuses_historical_fixture():
    old = [_manifest("example/old@1", monthly_cost=1, privacy="private", verified="2026-01-01T00:00:00Z")]
    result = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=old,
        now=NOW,
    )
    assert result["selection_status"] == "no_eligible"
    assert "freshness=expired" in result["rejected"][0]["reason"]


def test_unknown_risk_requires_an_explicit_machine_policy_override():
    unknown = _manifest("example/unknown@1", monthly_cost=1, privacy="private")
    unknown["operational_constraints"].pop("risk_class")
    refused = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=[unknown],
        now=NOW,
    )
    assert "risk_class is unknown" in refused["rejected"][0]["reason"]
    allowed = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=[unknown],
        now=NOW,
        owner_context=OwnerContext(allow_unknown_risk=True),
    )
    assert allowed["selection_status"] == "selected_only_eligible"


def test_consequential_task_disables_requested_exploration_policy():
    model = BayesianLinearPreferenceModel(DEFAULT_FEATURES)
    model.update({"privacy": 1.0}, 1.0)
    result = _select(
        owner_context=OwnerContext(
            reversible=False,
            interruption_cost=999,
            monthly_budget=20,
        ),
        preference_model=model,
        policy="thompson",
    )
    assert result["selection_status"] == "selected"
    assert result["effective_policy"] == "posterior_mean"
    assert result["requested_policy"] == "thompson"
    assert result["decision_policy"] == "adaptive-selection-v0.1-experimental"
    assert "disabled by risk" in result["reason"]


def test_value_of_information_is_not_guessed_without_calibrated_interruption_cost():
    model = BayesianLinearPreferenceModel(DEFAULT_FEATURES)
    model.update({"privacy": 1.0}, 1.0)
    result = _select(
        owner_context=OwnerContext(reversible=False, monthly_budget=20),
        preference_model=model,
    )
    assert result["voi"] == {"status": "not_calibrated", "interruption_cost": None}
    assert result["selection_status"] == "selected"


def test_features_do_not_change_when_an_unrelated_candidate_is_added():
    context = OwnerContext(reversible=True, monthly_budget=20, latency_target_seconds=1)
    base = _select(owner_context=context)
    expanded = adaptive_select(
        "research current agent tooling",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=_library() + [_manifest("example/other@1", monthly_cost=200, privacy="cloud")],
        now=NOW,
        owner_context=context,
    )
    before = {
        row["service_id"]: row["features"]
        for row in [base["selected"], *base["alternatives"]]
    }
    after = {
        row["service_id"]: row["features"]
        for row in [expanded["selected"], *expanded["alternatives"]]
    }
    assert after["example/private@1"] == before["example/private@1"]
    assert after["example/cheap@1"] == before["example/cheap@1"]


def test_missing_facts_cannot_win_by_pareto_dominance_on_shared_subset_only():
    incomplete = _manifest("example/incomplete@1", monthly_cost=1, privacy="private")
    incomplete["sla"].pop("uptime")
    result = adaptive_select(
        "research",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=[incomplete, _manifest("example/complete@1", monthly_cost=2, privacy="cloud")],
        now=NOW,
        owner_context=OwnerContext(reversible=True, monthly_budget=20),
    )
    assert result["selection_status"] != "selected_pareto_dominant"


def test_cli_and_gui_variants_remain_separate_candidates():
    library = [
        _manifest("wecom/cli@1", monthly_cost=0, privacy="private", interface="cli"),
        _manifest("wecom/gui@current", monthly_cost=0, privacy="cloud", interface="gui"),
    ]
    result = adaptive_select(
        "send a message",
        taxonomy="tool.research.web",
        required_functions=("web_search",),
        library=library,
        now=NOW,
        owner_context=OwnerContext(explicit_service_id="wecom/cli@1"),
    )
    assert result["selected"]["service_id"] == "wecom/cli@1"
    assert result["alternatives"][0]["service_id"] == "wecom/gui@current"

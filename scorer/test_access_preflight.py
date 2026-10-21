"""Consumer access boundaries, including a formerly selectable auth-only tool."""
from copy import deepcopy

import pytest

from asm_protocol.integrations.access_preflight import access_preflight
from asm_protocol.selection import select

NOW = "2026-10-21T12:00:00Z"


def manifest(sid="example/search@1", auth="none", setup=True):
    return {
        "asm_version": "0.3", "service_id": sid, "display_name": sid,
        "taxonomy": "tool.data.search", "ttl": 3600,
        "capabilities": {"functions": ["search"]},
        "invocation": {"interface": "mcp", "reach": "cloud", "platforms": ["any"],
                       "agent_operable": True, "auth_to_invoke": auth,
                       "agent_completable_setup": setup},
        "provenance": {"source_url": "https://example.org/docs",
                       "retrieved_at": NOW, "last_verified_at": NOW,
                       "verification_status": "self_reported"},
    }


def evaluate(items, **kwargs):
    return access_preflight(items, required_functions=["search"], evaluated_at=NOW, **kwargs)


def test_anonymous_path_survives_and_optional_credentials_do_not_become_required():
    item = manifest()
    item["extensions"] = {"org.asm.access-pilot": {"optional_credentials_effect": "higher_limits"}}
    before = deepcopy(item)
    result = evaluate([item])
    assert result["decision"]["selected"]["service_id"] == item["service_id"]
    assert result["decision"]["selected"]["cost_estimate"]["status"] == "unknown"
    assert result["execution_authorized"] is False
    assert result["considered"][0]["runtime_access_verified"] is False
    assert item == before


def test_required_auth_is_filtered_before_the_existing_selector_can_choose_it():
    item = manifest(auth="api_token_or_oauth", setup=False)
    baseline = select("structured request", required_functions=["search"], library=[item])
    assert baseline["selected"] is not None  # Existing selector alone does not check caller auth.
    result = evaluate([item])
    assert result["decision"]["selected"] is None
    assert result["considered"][0]["status"] == "requires_authentication"


def test_credential_presence_never_becomes_verified_access():
    result = evaluate([manifest(auth="oauth", setup=False)], auth_context="configured_unverified")
    assert result["decision"]["selected"] is None
    assert result["considered"][0]["status"] == "needs_account_verification"


@pytest.mark.parametrize("mutation", [
    {"last_verified_at": "2026-10-20T00:00:00Z"},
    {"last_verified_at": "2026-10-22T00:00:00Z"},
    {"last_verified_at": "2026-10-21T12:00:00"},
    {"source_url": "https://example.org/docs?token=redacted"},
])
def test_stale_future_ambiguous_or_credential_bearing_sources_cannot_select(mutation):
    item = manifest()
    item["provenance"].update(mutation)
    item["updated_at"] = NOW  # Publication never renews source verification.
    assert evaluate([item])["decision"]["selected"] is None


@pytest.mark.parametrize("missing", ["auth_to_invoke", "agent_completable_setup"])
def test_absence_is_not_anonymous(missing):
    item = manifest()
    del item["invocation"][missing]
    result = evaluate([item])
    assert result["considered"][0]["status"] == "unknown"
    assert result["decision"]["selected"] is None


def test_two_unknown_prices_do_not_produce_a_cheapest_claim():
    result = evaluate([manifest("a/search@1"), manifest("b/search@1")])
    assert result["decision"]["selection_status"] == "needs_cost_facts"
    assert result["decision"]["selected"] is None


def test_duplicate_identity_and_unstructured_task_are_rejected():
    with pytest.raises(ValueError):
        evaluate([manifest(), manifest()])
    with pytest.raises(ValueError):
        access_preflight([manifest()], required_functions="search")
    with pytest.raises(ValueError):
        evaluate([manifest()], auth_context="some-secret-key")

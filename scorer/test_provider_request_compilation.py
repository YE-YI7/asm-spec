from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from asm_protocol.contracts import ContractValidationError, contract_errors
from asm_protocol.digests import digest_query
from asm_protocol.providers import compile_provider_request

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search" / "request.valid.json"


def _request(provider_id: str, interface_id: str) -> dict:
    request = json.loads(FIXTURE.read_text(encoding="utf-8"))
    interface = request["candidate_scope"]["authorized_interfaces"][0]
    interface["provider_id"] = provider_id
    interface["service_id"] = f"{provider_id}/search"
    interface["interface_id"] = interface_id
    request["candidate_scope"]["default_interface_id"] = interface_id
    return request


@pytest.mark.parametrize(
    "provider_id,interface_id,expected",
    [
        ("tavily", "tavily/search:https-api", {"search_depth": "basic", "max_results": 5, "include_domains": ["example.com"]}),
        ("exa", "exa/search:https-api", {"type": "auto", "numResults": 5, "includeDomains": ["example.com"]}),
        ("firecrawl", "firecrawl/search:https-api", {"sources": ["web"], "limit": 5, "includeDomains": ["example.com"]}),
    ],
)
def test_provider_request_compiles_without_credentials(provider_id, interface_id, expected) -> None:
    compiled = compile_provider_request(provider_id, _request(provider_id, interface_id), "ASM protocol")
    assert compiled.endpoint.startswith("https://")
    assert compiled.method == "POST"
    assert compiled.auth_header in {"Authorization", "x-api-key"}
    assert "api_key" not in compiled.payload
    assert "language" in compiled.omitted_preferences
    for key, value in expected.items():
        assert compiled.payload[key] == value


def test_query_commitment_is_checked_before_provider_payload_is_created() -> None:
    request = _request("tavily", "tavily/search:https-api")
    assert request["query_ref"]["digest"] == digest_query("ASM protocol")
    with pytest.raises(ContractValidationError, match="query"):
        compile_provider_request("tavily", request, "different private query")


def test_provider_interface_must_be_authorized() -> None:
    request = _request("tavily", "tavily/search:https-api")
    with pytest.raises(ContractValidationError, match="not authorized"):
        compile_provider_request("exa", request, "ASM protocol")


def test_allowed_and_excluded_domains_cannot_both_apply() -> None:
    request = _request("tavily", "tavily/search:https-api")
    request["parameters"]["excluded_domains"] = ["blocked.example"]
    assert contract_errors("search_request", request)


@pytest.mark.parametrize(
    "provider_id,interface_id,field,value",
    [
        ("tavily", "tavily/search:https-api", "time_range", "week"),
        ("exa", "exa/search:https-api", "startPublishedDate", "2026-08-29T02:00:00.000Z"),
        ("firecrawl", "firecrawl/search:https-api", "tbs", "qdr:w"),
    ],
)
def test_week_window_maps_deterministically(provider_id, interface_id, field, value) -> None:
    request = _request(provider_id, interface_id)
    request["parameters"]["time_window"] = "week"
    compiled = compile_provider_request(provider_id, request, "ASM protocol")
    assert compiled.payload[field] == value


def test_compiler_does_not_mutate_request() -> None:
    request = _request("exa", "exa/search:https-api")
    before = copy.deepcopy(request)
    compile_provider_request("exa", request, "ASM protocol")
    assert request == before

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asm_protocol.providers import (
    ProviderResponseError,
    classify_http_error,
    normalize_exa,
    normalize_firecrawl,
    normalize_tavily,
)

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "contracts" / "search" / "providers"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "filename,normalizer,provider",
    [
        ("tavily.response.json", normalize_tavily, "tavily"),
        ("exa.response.json", normalize_exa, "exa"),
        ("firecrawl.response.json", normalize_firecrawl, "firecrawl"),
    ],
)
def test_replay_response_normalizes_to_same_result_shape(filename, normalizer, provider) -> None:
    result = normalizer(_load(filename))
    assert result.provider_id == provider
    assert result.results[0].to_dict() == {
        "rank": 1,
        "url": "https://example.com/asm",
        "title": "ASM",
        "snippet": "A selection-layer example.",
    }


def test_tavily_credits_do_not_become_dollars() -> None:
    result = normalize_tavily(_load("tavily.response.json"))
    assert result.usage[0].unit == "credit"
    assert result.estimated_cost.status == "unknown"
    assert result.settled_cost.status == "unknown"


def test_exa_cost_dollars_is_estimated_not_settled() -> None:
    result = normalize_exa(_load("exa.response.json"))
    assert result.estimated_cost.to_dict() == {
        "status": "known", "amount": "0.007", "currency": "USD", "source": "provider_estimate"
    }
    assert result.settled_cost.status == "unknown"


def test_firecrawl_credits_do_not_become_dollars() -> None:
    result = normalize_firecrawl(_load("firecrawl.response.json"))
    assert result.usage[0].to_dict()["unit"] == "credit"
    assert result.estimated_cost.amount is None


@pytest.mark.parametrize("normalizer", [normalize_tavily, normalize_exa])
def test_missing_result_array_is_invalid_response(normalizer) -> None:
    with pytest.raises(ProviderResponseError, match="array") as error:
        normalizer({})
    assert error.value.transport_status == "succeeded"
    assert error.value.tool_status == "invalid_result"


def test_firecrawl_success_false_is_provider_error() -> None:
    with pytest.raises(ProviderResponseError) as error:
        normalize_firecrawl({"success": False, "error": "upstream unavailable"})
    assert error.value.transport_status == "succeeded"
    assert error.value.tool_status == "provider_error"


@pytest.mark.parametrize(
    "code,transport_status,tool_status",
    [
        (401, "authentication_failed", "not_observed"),
        (403, "authentication_failed", "not_observed"),
        (429, "rate_limited", "not_observed"),
        (500, "succeeded", "provider_error"),
        (400, "succeeded", "provider_error"),
    ],
)
def test_http_errors_map_to_both_outcome_axes(code: int, transport_status: str, tool_status: str) -> None:
    error = classify_http_error(code, retry_after="3" if code == 429 else None)
    assert error.transport_status == transport_status
    assert error.tool_status == tool_status
    if code == 429:
        assert error.retry_after == "3"


def test_invalid_url_never_enters_normalized_result() -> None:
    payload = _load("tavily.response.json")
    payload["results"][0]["url"] = "file:///etc/passwd"
    with pytest.raises(ProviderResponseError) as error:
        normalize_tavily(payload)
    assert error.value.transport_status == "succeeded"
    assert error.value.tool_status == "invalid_result"

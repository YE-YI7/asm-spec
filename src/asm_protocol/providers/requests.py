"""Compile one validated ASM SearchRequest into fixed provider API payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ..contracts import ContractValidationError, validate_contract
from ..digests import digest_query


@dataclass(frozen=True)
class CompiledProviderRequest:
    provider_id: str
    interface_id: str
    endpoint: str
    method: str
    auth_header: str
    payload: dict[str, Any]
    omitted_preferences: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["omitted_preferences"] = list(self.omitted_preferences)
        return value


def _issued_at(request: Mapping[str, Any]) -> datetime:
    value = str(request["issued_at"]).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone(timezone.utc)


def _relative_start(request: Mapping[str, Any], window: str) -> str:
    days = {"day": 1, "week": 7, "month": 30, "year": 365}[window]
    return (_issued_at(request) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _common(request: Mapping[str, Any], query: str) -> tuple[dict[str, Any], list[str]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if request["query_ref"]["digest"] != digest_query(query):
        raise ContractValidationError("query does not match request.query_ref commitment")
    params = request.get("parameters") or {}
    omitted = ["language"] if params.get("language") else []
    return params, omitted


def compile_tavily_request(request: Mapping[str, Any], query: str) -> CompiledProviderRequest:
    validate_contract("search_request", request)
    params, omitted = _common(request, query)
    payload: dict[str, Any] = {
        "query": query,
        "search_depth": "basic",
        "max_results": params.get("result_limit", 5),
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }
    if params.get("allowed_domains"):
        payload["include_domains"] = params["allowed_domains"]
    if params.get("excluded_domains"):
        payload["exclude_domains"] = params["excluded_domains"]
    if params.get("time_window"):
        payload["time_range"] = params["time_window"]
    return CompiledProviderRequest(
        "tavily", "tavily/search:https-api", "https://api.tavily.com/search", "POST", "Authorization", payload, tuple(omitted)
    )


def compile_exa_request(request: Mapping[str, Any], query: str) -> CompiledProviderRequest:
    validate_contract("search_request", request)
    params, omitted = _common(request, query)
    payload: dict[str, Any] = {"query": query, "type": "auto", "numResults": params.get("result_limit", 5)}
    if params.get("allowed_domains"):
        payload["includeDomains"] = params["allowed_domains"]
    if params.get("excluded_domains"):
        payload["excludeDomains"] = params["excluded_domains"]
    if params.get("time_window"):
        payload["startPublishedDate"] = _relative_start(request, params["time_window"])
    return CompiledProviderRequest(
        "exa", "exa/search:https-api", "https://api.exa.ai/search", "POST", "x-api-key", payload, tuple(omitted)
    )


def compile_firecrawl_request(request: Mapping[str, Any], query: str) -> CompiledProviderRequest:
    validate_contract("search_request", request)
    params, omitted = _common(request, query)
    payload: dict[str, Any] = {"query": query, "limit": params.get("result_limit", 5), "sources": ["web"]}
    if params.get("allowed_domains"):
        payload["includeDomains"] = params["allowed_domains"]
    if params.get("excluded_domains"):
        payload["excludeDomains"] = params["excluded_domains"]
    if params.get("time_window"):
        payload["tbs"] = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}[
            params["time_window"]
        ]
    return CompiledProviderRequest(
        "firecrawl", "firecrawl/search:https-api", "https://api.firecrawl.dev/v2/search", "POST", "Authorization", payload, tuple(omitted)
    )


COMPILERS = {
    "tavily": compile_tavily_request,
    "exa": compile_exa_request,
    "firecrawl": compile_firecrawl_request,
}


def compile_provider_request(provider_id: str, request: Mapping[str, Any], query: str) -> CompiledProviderRequest:
    try:
        compiler = COMPILERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"unsupported search provider: {provider_id}") from exc
    compiled = compiler(request, query)
    authorized = {
        (row["provider_id"], row["interface_id"])
        for row in request["candidate_scope"]["authorized_interfaces"]
    }
    if (compiled.provider_id, compiled.interface_id) not in authorized:
        raise ContractValidationError("compiled provider interface is not authorized by the request")
    return compiled


__all__ = [
    "CompiledProviderRequest",
    "compile_exa_request",
    "compile_firecrawl_request",
    "compile_provider_request",
    "compile_tavily_request",
]

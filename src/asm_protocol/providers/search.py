"""Normalize provider search responses without hiding billing semantics."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

ADAPTER_VERSION = "0.1.0"


class ProviderResponseError(ValueError):
    """A provider response that cannot safely enter the common contract."""

    def __init__(
        self,
        transport_status: str,
        tool_status: str,
        message: str,
        *,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.transport_status = transport_status
        self.tool_status = tool_status
        self.retry_after = retry_after


@dataclass(frozen=True)
class SearchResult:
    rank: int
    url: str
    title: str | None
    snippet: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsageObservation:
    dimension: str
    quantity: str
    unit: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class MoneyObservation:
    status: str
    amount: str | None
    currency: str | None
    source: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class SearchObservation:
    provider_id: str
    interface_id: str
    adapter_version: str
    provider_request_id: str | None
    results: tuple[SearchResult, ...]
    usage: tuple[UsageObservation, ...]
    estimated_cost: MoneyObservation
    settled_cost: MoneyObservation
    provider_mode: str | None = None
    warning: str | None = None

    @property
    def transport_status(self) -> str:
        return "succeeded"

    @property
    def tool_status(self) -> str:
        return "succeeded" if self.results else "empty_result"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["results"] = [row.to_dict() for row in self.results]
        value["usage"] = [row.to_dict() for row in self.usage]
        value["estimated_cost"] = self.estimated_cost.to_dict()
        value["settled_cost"] = self.settled_cost.to_dict()
        value["transport_status"] = self.transport_status
        value["tool_status"] = self.tool_status
        return value


def _unknown_money() -> MoneyObservation:
    return MoneyObservation("unknown", None, None, "unknown")


def _decimal(value: Any, field: str) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProviderResponseError("succeeded", "invalid_result", f"{field} must be numeric") from exc
    if not number.is_finite() or number < 0:
        raise ProviderResponseError("succeeded", "invalid_result", f"{field} must be finite and non-negative")
    return format(number, "f")


def _results(rows: Any, snippet: Callable[[Mapping[str, Any]], Any]) -> tuple[SearchResult, ...]:
    if not isinstance(rows, list):
        raise ProviderResponseError("succeeded", "invalid_result", "search results must be an array")
    normalized = []
    for rank, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            raise ProviderResponseError("succeeded", "invalid_result", f"result {rank} must be an object")
        url = row.get("url")
        if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
            raise ProviderResponseError("succeeded", "invalid_result", f"result {rank} has no valid HTTP(S) URL")
        title = row.get("title") if isinstance(row.get("title"), str) else None
        raw_snippet = snippet(row)
        normalized.append(SearchResult(rank, url, title, raw_snippet if isinstance(raw_snippet, str) else None))
    return tuple(normalized)


def normalize_tavily(payload: Mapping[str, Any]) -> SearchObservation:
    results = _results(payload.get("results"), lambda row: row.get("content"))
    usage = payload.get("usage") or {}
    credits = usage.get("credits") if isinstance(usage, Mapping) else None
    observations = () if credits is None else (UsageObservation("search", _decimal(credits, "usage.credits"), "credit", "provider_response"),)
    mode = (payload.get("auto_parameters") or {}).get("search_depth") if isinstance(payload.get("auto_parameters"), Mapping) else None
    return SearchObservation(
        "tavily", "tavily/search:https-api", ADAPTER_VERSION,
        payload.get("request_id") if isinstance(payload.get("request_id"), str) else None,
        results, observations, _unknown_money(), _unknown_money(), mode,
    )


def normalize_exa(payload: Mapping[str, Any]) -> SearchObservation:
    results = _results(payload.get("results"), lambda row: row.get("summary") or row.get("text") or ((row.get("highlights") or [None])[0] if isinstance(row.get("highlights"), list) else None))
    cost = payload.get("costDollars")
    total = cost.get("total") if isinstance(cost, Mapping) else None
    estimated = _unknown_money() if total is None else MoneyObservation("known", _decimal(total, "costDollars.total"), "USD", "provider_estimate")
    search_time = payload.get("searchTime")
    usage = () if search_time is None else (UsageObservation("search_time", _decimal(search_time, "searchTime"), "ms", "provider_response"),)
    return SearchObservation(
        "exa", "exa/search:https-api", ADAPTER_VERSION,
        payload.get("requestId") if isinstance(payload.get("requestId"), str) else None,
        results, usage, estimated, _unknown_money(),
        payload.get("resolvedSearchType") if isinstance(payload.get("resolvedSearchType"), str) else None,
    )


def normalize_firecrawl(payload: Mapping[str, Any]) -> SearchObservation:
    if payload.get("success") is not True:
        raise ProviderResponseError("succeeded", "provider_error", str(payload.get("error") or "Firecrawl returned success=false"))
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ProviderResponseError("succeeded", "invalid_result", "data must be an object")
    results = _results(data.get("web"), lambda row: row.get("description") or row.get("markdown"))
    credits = payload.get("creditsUsed")
    usage = () if credits is None else (UsageObservation("search", _decimal(credits, "creditsUsed"), "credit", "provider_response"),)
    return SearchObservation(
        "firecrawl", "firecrawl/search:https-api", ADAPTER_VERSION,
        payload.get("id") if isinstance(payload.get("id"), str) else None,
        results, usage, _unknown_money(), _unknown_money(), None,
        payload.get("warning") if isinstance(payload.get("warning"), str) else None,
    )


def classify_http_error(status_code: int, message: str = "", *, retry_after: str | None = None) -> ProviderResponseError:
    if status_code in {401, 403}:
        transport_status, tool_status = "authentication_failed", "not_observed"
    elif status_code == 402:
        transport_status, tool_status = "billing_blocked", "not_observed"
    elif status_code == 429:
        transport_status, tool_status = "rate_limited", "not_observed"
    elif 400 <= status_code <= 599:
        transport_status, tool_status = "succeeded", "provider_error"
    else:
        transport_status, tool_status = "invalid_response", "not_observed"
    return ProviderResponseError(
        transport_status,
        tool_status,
        message or f"provider HTTP {status_code}",
        retry_after=retry_after,
    )


NORMALIZERS = {
    "tavily": normalize_tavily,
    "exa": normalize_exa,
    "firecrawl": normalize_firecrawl,
}


def normalize_provider_response(provider_id: str, payload: Mapping[str, Any]) -> SearchObservation:
    """Normalize one supported provider response by explicit provider id."""
    try:
        normalizer = NORMALIZERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"unsupported search provider: {provider_id}") from exc
    return normalizer(payload)

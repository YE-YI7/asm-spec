"""Fail-closed HTTP transport for compiled search-provider requests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .requests import CompiledProviderRequest
from .search import ProviderResponseError

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
ENDPOINT_ALLOWLIST = {
    ("tavily", "https://api.tavily.com/search"),
    ("exa", "https://api.exa.ai/search"),
    ("firecrawl", "https://api.firecrawl.dev/v2/search"),
}
AUTH_HEADERS = {"tavily": "Authorization", "exa": "x-api-key", "firecrawl": "Authorization"}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class RawProviderResponse:
    http_status: int
    payload: dict[str, Any]
    retry_after: str | None


def _decode_json(response) -> dict[str, Any]:
    content_type = str(response.headers.get("Content-Type") or "").lower()
    if "json" not in content_type:
        raise ProviderResponseError("invalid_response", "not_observed", "provider response is not JSON")
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProviderResponseError("invalid_response", "not_observed", "provider response exceeds 2 MiB")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderResponseError("invalid_response", "not_observed", "provider response contains invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ProviderResponseError("invalid_response", "not_observed", "provider response root must be an object")
    return payload


def execute_provider_request(
    compiled: CompiledProviderRequest,
    *,
    api_key: str,
    allow_live: bool = False,
    timeout_seconds: float = 15.0,
    opener=None,
) -> RawProviderResponse:
    """Execute exactly one authorized request; no retries and no redirects."""
    if not allow_live:
        raise PermissionError("live provider calls are disabled; explicit allow_live=True is required")
    if (compiled.provider_id, compiled.endpoint) not in ENDPOINT_ALLOWLIST:
        raise PermissionError("provider endpoint is not in the fixed allowlist")
    if compiled.method != "POST" or compiled.auth_header != AUTH_HEADERS[compiled.provider_id]:
        raise PermissionError("compiled request method or authentication header is not allowed")
    if not api_key or not api_key.strip():
        raise PermissionError("a non-empty provider API key is required")
    if not 0 < timeout_seconds <= 60:
        raise ValueError("timeout_seconds must be in (0, 60]")

    credential = api_key if compiled.provider_id == "exa" else f"Bearer {api_key}"
    request = Request(
        compiled.endpoint,
        data=json.dumps(compiled.payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", compiled.auth_header: credential},
        method="POST",
    )
    client = opener or build_opener(_NoRedirect())
    try:
        with client.open(request, timeout=timeout_seconds) as response:
            return RawProviderResponse(
                int(response.status),
                _decode_json(response),
                response.headers.get("Retry-After"),
            )
    except HTTPError as exc:
        return RawProviderResponse(int(exc.code), _decode_json(exc), exc.headers.get("Retry-After"))
    except TimeoutError as exc:
        raise ProviderResponseError("timeout", "not_observed", "provider request timed out") from exc
    except URLError as exc:
        raise ProviderResponseError("network_failed", "not_observed", "provider network request failed") from exc


__all__ = [
    "AUTH_HEADERS",
    "ENDPOINT_ALLOWLIST",
    "MAX_RESPONSE_BYTES",
    "RawProviderResponse",
    "execute_provider_request",
]

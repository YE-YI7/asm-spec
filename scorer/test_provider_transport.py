from __future__ import annotations

import io
import json
from email.message import Message

import pytest

from asm_protocol.providers import CompiledProviderRequest, execute_provider_request
from asm_protocol.providers.search import ProviderResponseError


class FakeResponse:
    def __init__(self, payload, *, status=200, content_type="application/json", retry_after=None):
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if retry_after:
            self.headers["Retry-After"] = retry_after
        self._body = io.BytesIO(json.dumps(payload).encode())

    def read(self, size=-1):
        return self._body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.seen_request = None

    def open(self, request, timeout):
        self.seen_request = request
        return self.response


def _compiled(endpoint="https://api.tavily.com/search"):
    return CompiledProviderRequest(
        provider_id="tavily",
        interface_id="tavily/search:https-api",
        endpoint=endpoint,
        method="POST",
        auth_header="Authorization",
        payload={"query": "private"},
        omitted_preferences=(),
    )


def test_live_transport_is_disabled_by_default() -> None:
    with pytest.raises(PermissionError, match="disabled"):
        execute_provider_request(_compiled(), api_key="secret")


def test_arbitrary_endpoint_is_rejected_before_network() -> None:
    with pytest.raises(PermissionError, match="allowlist"):
        execute_provider_request(
            _compiled("https://attacker.example/search"),
            api_key="secret",
            allow_live=True,
            opener=FakeOpener(FakeResponse({})),
        )


def test_fake_transport_executes_once_and_never_returns_credential() -> None:
    opener = FakeOpener(FakeResponse({"results": []}))
    result = execute_provider_request(
        _compiled(), api_key="secret", allow_live=True, opener=opener
    )
    assert result.http_status == 200
    assert result.payload == {"results": []}
    assert "secret" not in repr(result)
    assert opener.seen_request.get_header("Authorization") == "Bearer secret"


def test_non_json_response_fails_closed() -> None:
    opener = FakeOpener(FakeResponse({}, content_type="text/html"))
    with pytest.raises(ProviderResponseError) as error:
        execute_provider_request(
            _compiled(), api_key="secret", allow_live=True, opener=opener
        )
    assert error.value.transport_status == "invalid_response"


def test_missing_key_fails_before_network() -> None:
    with pytest.raises(PermissionError, match="API key"):
        execute_provider_request(
            _compiled(), api_key="", allow_live=True, opener=FakeOpener(FakeResponse({}))
        )

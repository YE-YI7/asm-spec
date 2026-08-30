from __future__ import annotations

import io
import json
from urllib.parse import parse_qs, urlparse

import pytest

from asm_protocol.federation import MCPRegistryClient, MCPRegistryRecord


def _row(name: str, version: str, *, latest: bool, description: str = "") -> dict:
    return {
        "server": {
            "name": name,
            "version": version,
            "title": name.split("/")[-1],
            "description": description,
            "remotes": [{"type": "streamable-http", "url": "https://example.test/mcp"}],
        },
        "_meta": {
            "io.modelcontextprotocol.registry/official": {
                "status": "active",
                "isLatest": latest,
                "updatedAt": "2026-08-30T00:00:00Z",
            }
        },
    }


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _opener(pages):
    def open_request(request, timeout):
        assert timeout == 3
        cursor = (parse_qs(urlparse(request.full_url).query).get("cursor") or [None])[0]
        return _Response(json.dumps(pages[cursor]).encode())

    return open_request


def test_iter_servers_uses_opaque_cursor_and_keeps_latest_only():
    pages = {
        None: {
            "servers": [
                _row("io.example/search", "1.0.0", latest=False),
                _row("io.example/search", "1.1.0", latest=True, description="web research"),
            ],
            "metadata": {"count": 2, "nextCursor": "opaque:cursor/1"},
        },
        "opaque:cursor/1": {
            "servers": [_row("io.example/calendar", "2.0.0", latest=True)],
            "metadata": {"count": 1},
        },
    }
    client = MCPRegistryClient("https://registry.test", timeout=3, opener=_opener(pages))
    records = list(client.iter_servers())
    assert [(row.name, row.version) for row in records] == [
        ("io.example/search", "1.1.0"),
        ("io.example/calendar", "2.0.0"),
    ]


def test_search_is_retrieval_only_and_does_not_fabricate_selection_facts():
    record = MCPRegistryRecord.from_api(
        _row("io.example/research", "1.0.0", latest=True, description="Search the web")
    )
    assert record.retrieval_score("web search") > 0
    candidate = record.to_discovery_candidate()
    assert candidate["selection_ready"] is False
    assert "pricing/workload" in candidate["missing_selection_facts"]
    assert "taxonomy" not in candidate


def test_repeated_registry_cursor_fails_instead_of_looping_forever():
    page = {
        "servers": [_row("io.example/search", "1.0.0", latest=True)],
        "metadata": {"count": 1, "nextCursor": "same"},
    }
    pages = {None: page, "same": page}
    client = MCPRegistryClient("https://registry.test", timeout=3, opener=_opener(pages))
    with pytest.raises(RuntimeError, match="repeated pagination cursor"):
        list(client.iter_servers())


def test_page_limit_is_bounded_by_official_api_contract():
    client = MCPRegistryClient("https://registry.test")
    with pytest.raises(ValueError, match="between 1 and 100"):
        client.list_page(limit=101)
    with pytest.raises(ValueError, match="max_pages must be between 1 and 100"):
        client.search("search", max_pages=0)

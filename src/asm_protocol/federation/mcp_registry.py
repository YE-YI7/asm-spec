"""Read-only adapter for the official MCP Registry REST API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_REGISTRY_URL = "https://registry.modelcontextprotocol.io"
_OFFICIAL_META = "io.modelcontextprotocol.registry/official"
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


@dataclass(frozen=True)
class MCPRegistryRecord:
    """Normalized discovery metadata for one published server version."""

    name: str
    version: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    is_latest: bool = False
    published_at: str | None = None
    updated_at: str | None = None
    transports: tuple[dict[str, Any], ...] = ()
    packages: tuple[dict[str, Any], ...] = ()
    repository: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> "MCPRegistryRecord":
        server = row.get("server") or {}
        meta = (row.get("_meta") or {}).get(_OFFICIAL_META) or {}
        name = server.get("name")
        version = server.get("version")
        if not isinstance(name, str) or not name:
            raise ValueError("registry row is missing server.name")
        if not isinstance(version, str) or not version:
            raise ValueError(f"registry row {name!r} is missing server.version")
        return cls(
            name=name,
            version=version,
            title=server.get("title"),
            description=server.get("description"),
            status=meta.get("status"),
            is_latest=bool(meta.get("isLatest")),
            published_at=meta.get("publishedAt"),
            updated_at=meta.get("updatedAt"),
            transports=tuple(server.get("remotes") or ()),
            packages=tuple(server.get("packages") or ()),
            repository=server.get("repository"),
            raw=row,
        )

    def retrieval_score(self, query: str) -> float:
        """Small deterministic lexical score used only for candidate retrieval."""
        query_tokens = _tokens(query)
        if not query_tokens:
            return 0.0
        name_tokens = _tokens(self.name.replace("/", " "))
        title_tokens = _tokens(self.title or "")
        description_tokens = _tokens(self.description or "")
        exact = 3.0 if query.lower() in " ".join(
            filter(None, (self.name, self.title or "", self.description or ""))
        ).lower() else 0.0
        return (
            exact
            + 3.0 * len(query_tokens & name_tokens)
            + 2.0 * len(query_tokens & title_tokens)
            + 1.0 * len(query_tokens & description_tokens)
        )

    def to_discovery_candidate(self) -> dict[str, Any]:
        """Return an honest discovery record, not a fabricated ASM manifest."""
        return {
            "source": "mcp-official-registry",
            "registry_name": self.name,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "is_latest": self.is_latest,
            "updated_at": self.updated_at,
            "transports": list(self.transports),
            "packages": list(self.packages),
            "repository": self.repository,
            "selection_ready": False,
            "missing_selection_facts": [
                "taxonomy",
                "capabilities",
                "invocation eligibility",
                "pricing/workload",
                "operational risk",
                "fresh provenance",
            ],
        }


@dataclass(frozen=True)
class RegistryPage:
    records: tuple[MCPRegistryRecord, ...]
    next_cursor: str | None
    count: int


class MCPRegistryClient:
    """Cursor-safe client for a Generic MCP Registry compatible endpoint."""

    def __init__(
        self,
        base_url: str = DEFAULT_REGISTRY_URL,
        *,
        timeout: float = 15.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener

    def _get_json(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "asm-protocol/0.7-dev (+https://github.com/YE-YI7/asm-spec)",
            },
        )
        with self._opener(request, timeout=self.timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError("registry response must be a JSON object")
        return payload

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> RegistryPage:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = {"limit": str(limit)}
        if cursor:
            query["cursor"] = cursor
        payload = self._get_json("/v0.1/servers", query)
        rows = payload.get("servers") or []
        if not isinstance(rows, list):
            raise ValueError("registry response servers must be an array")
        records = tuple(MCPRegistryRecord.from_api(row) for row in rows)
        metadata = payload.get("metadata") or {}
        next_cursor = metadata.get("nextCursor") or None
        count = metadata.get("count", len(records))
        return RegistryPage(records, next_cursor, int(count))

    def iter_servers(
        self,
        *,
        latest_only: bool = True,
        page_size: int = 100,
        max_pages: int | None = None,
        max_records: int | None = None,
    ) -> Iterator[MCPRegistryRecord]:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        pages = 0
        emitted = 0
        while True:
            page = self.list_page(limit=page_size, cursor=cursor)
            pages += 1
            for record in page.records:
                if latest_only and not record.is_latest:
                    continue
                yield record
                emitted += 1
                if max_records is not None and emitted >= max_records:
                    return
            cursor = page.next_cursor
            if not cursor:
                return
            if cursor in seen_cursors:
                raise RuntimeError("registry returned a repeated pagination cursor")
            seen_cursors.add(cursor)
            if max_pages is not None and pages >= max_pages:
                return

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        max_pages: int = 10,
        latest_only: bool = True,
    ) -> list[MCPRegistryRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not 1 <= max_pages <= 100:
            raise ValueError("max_pages must be between 1 and 100")
        scored = []
        for record in self.iter_servers(
            latest_only=latest_only,
            max_pages=max_pages,
        ):
            score = record.retrieval_score(query)
            if score > 0:
                scored.append((score, record.name, record.version, record))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [item[-1] for item in scored[:limit]]

    def get_latest(self, server_name: str) -> MCPRegistryRecord:
        encoded = quote(server_name, safe="")
        payload = self._get_json(f"/v0.1/servers/{encoded}/versions/latest")
        row = payload.get("server")
        if isinstance(row, dict) and "server" in row:
            return MCPRegistryRecord.from_api(row)
        return MCPRegistryRecord.from_api(payload)

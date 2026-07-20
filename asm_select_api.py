#!/usr/bin/env python3
"""Hosted ASM selector API — stdlib-only HTTP wrapper around library_select.

Endpoints:
  POST /select          body: {task, taxonomy?, agent_reach?, user_platform?,
                               required_functions?, require_approval_for?,
                               require_agent_completable_setup?}
                        -> structured selection decision (same shape as library_select.select)
  GET  /tools           ?taxonomy=...  -> list of selectable tools
  GET  /.well-known/asm -> ASM catalog: one re-stampable generated_at + per-manifest
                           links (the inline-vs-link convention, applied to ourselves)
  GET  /.well-known/ai-catalog.json -> AI Catalog (Agent-Card/ai-catalog) document:
                           every library tool as a catalog entry carrying its ASM
                           value/selection block in the ADR-0012 `metadata` object
  GET  /manifest/{service_id} -> full ASM manifest for one tool
  GET  /healthz         -> {"ok": true, "tools": N}

Run:    python asm_select_api.py            (default 127.0.0.1:8787)
        ASM_API_HOST=0.0.0.0 ASM_API_PORT=8080 python asm_select_api.py
Deploy: any host that runs a Python process (Railway/Fly/render). No dependencies.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from library_select import load_library, monthly_cost, select

_LIBRARY = load_library()
_BY_ID = {m.get("service_id"): m for m in _LIBRARY}
_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _urn_part(s: str) -> str:
    """RFC 8141 urn:air segment: only [a-zA-Z0-9._-] survives."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", s)


def _ai_catalog_entry(m: dict, base: str) -> dict:
    """AI Catalog entry (schema v1.0, ARD-conformance-tested): static ASM
    eligibility/selection signals inline under metadata.asm; the full mutable
    manifest behind url. service_id org/tool@version maps to URN + version."""
    sid = m.get("service_id")
    inv = m.get("invocation") or {}
    ops = m.get("operational_constraints") or {}
    base_id, _, ver = sid.partition("@")
    org, _, tool = base_id.partition("/")
    # metadata values must be flat primitives (schema v1.0), so namespaced keys
    asm_meta = {"asm:version": m.get("asm_version", "0.3"),
                "asm:taxonomy": m.get("taxonomy"),
                "asm:manifestUrl": f"{base}/manifest/{sid}"}
    for k in ("interface", "reach", "agent_operable", "agent_completable_setup"):
        if inv.get(k) is not None:
            asm_meta[f"asm:{k}"] = inv[k]
    if inv.get("setup_requires"):
        asm_meta["asm:setup_requires"] = ",".join(inv["setup_requires"])
    if ops.get("risk_class"):
        asm_meta["asm:risk_class"] = ops["risk_class"]
    if (ops.get("approval") or {}).get("required"):
        asm_meta["asm:approval"] = ops["approval"]["required"]
    entry = {
        "identifier": f"urn:air:asm-spec:{_urn_part(org)}:{_urn_part(tool or org)}",
        "displayName": m.get("display_name"),
        "type": "application/asm+json",
        "url": f"{base}/manifest/{sid}",
        "tags": (m.get("taxonomy") or "tool").split("."),
        "updatedAt": _GENERATED_AT,
        "metadata": asm_meta,
    }
    if ver:
        entry["version"] = ver
    desc = (m.get("description") or "").strip()
    if desc:
        entry["description"] = desc[:300]
    return entry


def _tools_listing(taxonomy: str | None) -> list[dict]:
    out = []
    for m in _LIBRARY:
        if taxonomy and m.get("taxonomy") != taxonomy:
            continue
        inv = m.get("invocation") or {}
        out.append({
            "service_id": m.get("service_id"),
            "display_name": m.get("display_name"),
            "taxonomy": m.get("taxonomy"),
            "interface": inv.get("interface"),
            "reach": inv.get("reach"),
            "agent_operable": inv.get("agent_operable"),
            "agent_completable_setup": inv.get("agent_completable_setup"),
            "monthly_cost_usd": round(monthly_cost(m), 2),
        })
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "asm-select-api/0.1"

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self._send(204, {})

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/healthz":
            self._send(200, {"ok": True, "tools": len(_LIBRARY)})
        elif url.path == "/tools":
            taxonomy = (parse_qs(url.query).get("taxonomy") or [None])[0]
            self._send(200, _tools_listing(taxonomy))
        elif url.path == "/.well-known/asm":
            # Dogfooding the inline-vs-link convention: one catalog with a single
            # re-stampable generated_at; mutable detail lives behind per-manifest links.
            self._send(200, {
                "asm_catalog_version": "0.1",
                "publisher": "asm-spec tool-value library",
                "generated_at": _GENERATED_AT,
                "schema": "https://github.com/YE-YI7/asm-spec/blob/main/schema/asm-v0.3.schema.json",
                "count": len(_LIBRARY),
                "manifests": [
                    {"service_id": m.get("service_id"), "taxonomy": m.get("taxonomy"),
                     "display_name": m.get("display_name"),
                     "url": f"/manifest/{m.get('service_id')}"}
                    for m in _LIBRARY
                ],
            })
        elif url.path == "/.well-known/ai-catalog.json":
            # Cross-protocol discovery: the same library as an AI Catalog document,
            # value/selection metadata riding the ADR-0012 `metadata` extension point.
            host = self.headers.get("Host", "asm-spec.onrender.com")
            scheme = "http" if host.split(":")[0] in ("localhost", "127.0.0.1") else "https"
            base = f"{scheme}://{host}"
            # Root is closed (specVersion/host/entries only); freshness moves to
            # per-entry updatedAt, provenance note into host.displayName.
            self._send(200, {
                "specVersion": "1.0",
                "host": {
                    "displayName": "ASM tool-value library (demonstration registry; "
                                   "value/selection metadata rides entry.metadata.asm)",
                    "identifier": "asm-spec.onrender.com",
                    "documentationUrl": "https://github.com/YE-YI7/asm-spec",
                },
                "entries": [_ai_catalog_entry(m, base) for m in _LIBRARY],
            })
        elif url.path.startswith("/manifest/"):
            sid = unquote(url.path[len("/manifest/"):])
            m = _BY_ID.get(sid)
            if m:
                self._send(200, m)
            else:
                self._send(404, {"error": f"no manifest with service_id={sid}"})
        else:
            self._send(404, {"error": "unknown path; use POST /select, GET /tools, GET /.well-known/asm, GET /manifest/{service_id}, GET /healthz"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/select":
            self._send(404, {"error": "unknown path; POST /select"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return
        task = req.get("task")
        if not task:
            self._send(400, {"error": "'task' is required"})
            return
        result = select(
            task,
            taxonomy=req.get("taxonomy"),
            agent_reach=req.get("agent_reach", "cloud"),
            user_platform=req.get("user_platform", "any"),
            required_functions=req.get("required_functions") or [],
            require_approval_for=req.get("require_approval_for") or [],
            require_agent_completable_setup=bool(req.get("require_agent_completable_setup", False)),
            library=_LIBRARY,
        )
        self._send(200, result)

    def log_message(self, fmt, *args):  # quiet default logging
        pass


def main() -> None:
    # PaaS hosts (Render/Railway/Heroku) inject PORT and need 0.0.0.0 binding.
    paas_port = os.environ.get("PORT")
    host = os.environ.get("ASM_API_HOST", "0.0.0.0" if paas_port else "127.0.0.1")
    port = int(os.environ.get("ASM_API_PORT", paas_port or "8787"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"asm-select-api serving {len(_LIBRARY)} tools on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

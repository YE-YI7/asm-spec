#!/usr/bin/env python3
"""Hosted ASM selector API — stdlib-only HTTP wrapper around library_select.

Endpoints:
  POST /select   body: {task, taxonomy?, agent_reach?, user_platform?,
                        required_functions?, require_approval_for?,
                        require_agent_completable_setup?}
                 -> structured selection decision (same shape as library_select.select)
  GET  /tools    ?taxonomy=...  -> list of selectable tools
  GET  /healthz  -> {"ok": true, "tools": N}

Run:    python asm_select_api.py            (default 127.0.0.1:8787)
        ASM_API_HOST=0.0.0.0 ASM_API_PORT=8080 python asm_select_api.py
Deploy: any host that runs a Python process (Railway/Fly/render). No dependencies.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from library_select import load_library, monthly_cost, select

_LIBRARY = load_library()


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
        else:
            self._send(404, {"error": "unknown path; use POST /select, GET /tools, GET /healthz"})

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

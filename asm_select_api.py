#!/usr/bin/env python3
"""Hosted ASM selector API — stdlib-only HTTP wrapper around library_select.

Endpoints:
  POST /select          body: {task, taxonomy?, agent_reach?, user_platform?,
                               required_functions?, require_approval_for?,
                               require_agent_completable_setup?, workload?: {
                                 monthly_units?, amortization_months?}}
                        -> structured selection decision (same shape as library_select.select)
  POST /contracts/validate body: {type, payload} -> draft application-contract
                        conformance result; never an authorization or certification
  GET  /tools           ?taxonomy=...  -> list of selectable tools
  GET  /.well-known/asm -> ASM catalog: one re-stampable generated_at + per-manifest
                           links (the inline-vs-link convention, applied to ourselves)
  GET  /.well-known/ai-catalog.json -> AI Catalog (Agent-Card/ai-catalog) document:
                           every library tool as a catalog entry carrying its ASM
                           value/selection block in a namespaced `extensions` entry
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
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from asm_protocol.contracts import CONTRACT_SCHEMAS, contract_errors
from library_select import estimate_monthly_cost, load_library, select

_LIBRARY = load_library()
_BY_ID = {m.get("service_id"): m for m in _LIBRARY}
_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Static launch assets (agent-commerce showcase): served from public/ if present.
_SOURCE_PUBLIC = Path(__file__).resolve().parent / "public"
_PUBLIC = _SOURCE_PUBLIC if _SOURCE_PUBLIC.is_dir() else resources.files("asm_public")
_AI_CATALOG_EXTENSION = "io.github.ye-yi7.asm.selection"
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/showcase": ("showcase.html", "text/html; charset=utf-8"),
    "/showcase.html": ("showcase.html", "text/html; charset=utf-8"),
    "/showcase-data.json": ("showcase-data.json", "application/json; charset=utf-8"),
    "/services/tavily-search": ("services/tavily-search.html", "text/html; charset=utf-8"),
    "/services/exa-search": ("services/exa-search.html", "text/html; charset=utf-8"),
    "/services/firecrawl-search": ("services/firecrawl-search.html", "text/html; charset=utf-8"),
    "/methods/web-search-replay-v0.1": ("methods/web-search-replay-v0.1.html", "text/html; charset=utf-8"),
    "/runs/replay-search-example": ("runs/replay-search-example.html", "text/html; charset=utf-8"),
}


def _urn_part(s: str) -> str:
    """RFC 8141 urn:air segment: only [a-zA-Z0-9._-] survives."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", s)


def _access_signal(m: dict) -> dict:
    """Derive the discovery-time access/monetization signal (ai-catalog#83)
    from real manifest pricing/payment. Flat namespaced primitives only
    (schema v1.0). Kept under our own `asm:` namespace — not squatting a generic
    `access:` prefix before the WG blesses one; renames trivially when it does."""
    pricing = m.get("pricing") or {}
    payment = m.get("payment") or {}
    dims = pricing.get("billing_dimensions") or []
    methods = payment.get("methods") or []
    has_free = "free_tier" in methods
    paid = [d for d in dims if (d.get("cost_per_unit") or 0) > 0]
    if has_free and paid:
        tier = "freemium"
    elif has_free:
        tier = "free"
    elif paid:
        tier = "subscription" if "subscription" in methods else "paid"
    else:
        tier = "negotiated"  # no free tier, no public priced dimension
    out = {"asm:accessTier": tier, "asm:freeTier": has_free}
    if paid:
        cheapest = min(paid, key=lambda d: d["cost_per_unit"])
        out["asm:priceEchoAmount"] = cheapest["cost_per_unit"]
        out["asm:priceEchoCurrency"] = cheapest.get("currency", "USD")
        out["asm:priceEchoUnit"] = cheapest.get("unit", "")
    url = payment.get("signup_url") or (m.get("provenance") or {}).get("source_url")
    if url:
        out["asm:pricingUrl"] = url
    asof = (m.get("provenance") or {}).get("last_verified_at")
    if asof:
        out["asm:priceEchoAsOf"] = asof
    # coarse mechanism, only where the manifest states it unambiguously
    mech = {"api_key_prepaid": "prepaid-key", "subscription": "subscription"}
    for k, v in mech.items():
        if k in methods:
            out["asm:accessMechanism"] = v
            break
    return out


def _ai_catalog_entry(m: dict, base: str) -> dict:
    """AI Catalog entry (schema v1.0): static ASM eligibility/selection signals
    inline under a namespaced extension; the full mutable
    manifest behind url. service_id org/tool@version maps to URN + version."""
    sid = m.get("service_id")
    inv = m.get("invocation") or {}
    ops = m.get("operational_constraints") or {}
    base_id, _, ver = sid.partition("@")
    org, _, tool = base_id.partition("/")
    # Keep the payload flat; the outer key follows the spec's required
    # reverse-DNS/URL namespace convention.
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
    asm_meta.update(_access_signal(m))  # discovery-time access/monetization signal
    entry = {
        "identifier": f"urn:air:github.com:ye-yi7:asm:{_urn_part(org)}:{_urn_part(tool or org)}",
        "displayName": m.get("display_name"),
        "type": "application/asm+json",
        "url": f"{base}/manifest/{sid}",
        "tags": (m.get("taxonomy") or "tool").split("."),
        "updatedAt": _GENERATED_AT,
        "extensions": {_AI_CATALOG_EXTENSION: asm_meta},
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
        estimate = estimate_monthly_cost(m)
        out.append({
            "service_id": m.get("service_id"),
            "display_name": m.get("display_name"),
            "taxonomy": m.get("taxonomy"),
            "interface": inv.get("interface"),
            "reach": inv.get("reach"),
            "agent_operable": inv.get("agent_operable"),
            "agent_completable_setup": inv.get("agent_completable_setup"),
            "monthly_cost_usd": estimate.monthly_total,
            "cost_estimate": estimate.to_dict(),
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

    def _send_static(self, filename: str, content_type: str) -> None:
        path = _PUBLIC / filename
        if not path.is_file():
            self._send(404, {"error": f"static asset not found: {filename}"})
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path in _STATIC:
            self._send_static(*_STATIC[url.path])
        elif url.path == "/healthz":
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
            # with value/selection metadata in a namespaced extension.
            host = self.headers.get("Host", "asm-spec.onrender.com")
            scheme = "http" if host.split(":")[0] in ("localhost", "127.0.0.1") else "https"
            base = f"{scheme}://{host}"
            # Root is closed (specVersion/host/entries only); freshness moves to
            # per-entry updatedAt, provenance note into host.displayName.
            self._send(200, {
                "specVersion": "1.0",
                "host": {
                    "displayName": "ASM tool-value library (demonstration registry; "
                                   "selection metadata rides a namespaced entry extension)",
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
        path = urlparse(self.path).path
        if path not in {"/select", "/contracts/validate"}:
            self._send(404, {"error": "unknown path; POST /select or /contracts/validate"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return
        if path == "/contracts/validate":
            contract = req.get("type") if isinstance(req, dict) else None
            payload = req.get("payload") if isinstance(req, dict) else None
            if contract not in CONTRACT_SCHEMAS or not isinstance(payload, dict):
                self._send(400, {"error": "'type' must name an ASM contract and 'payload' must be an object"})
                return
            errors = contract_errors(contract, payload)
            self._send(200 if not errors else 422, {
                "valid": not errors,
                "contract": contract,
                "errors": errors,
                "meaning": "schema conformance only; not source truth, authorization, execution, or certification",
            })
            return
        task = req.get("task")
        if not task:
            self._send(400, {"error": "'task' is required"})
            return
        try:
            result = select(
                task,
                taxonomy=req.get("taxonomy"),
                agent_reach=req.get("agent_reach", "cloud"),
                user_platform=req.get("user_platform", "any"),
                required_functions=req.get("required_functions") or [],
                require_approval_for=req.get("require_approval_for") or [],
                require_agent_completable_setup=bool(req.get("require_agent_completable_setup", False)),
                workload=req.get("workload"),
                fallback_policy=req.get("fallback_policy"),
                selection_profile=req.get("selection_profile", "current"),
                library=_LIBRARY,
                receipt=bool(req.get("receipt", False)),
            )
        except (TypeError, ValueError) as error:
            self._send(400, {"error": str(error)})
            return
        self._send(422 if result["selection_status"] == "under_specified" else 200, result)

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

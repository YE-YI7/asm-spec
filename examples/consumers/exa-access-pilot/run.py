#!/usr/bin/env python3
"""A no-credential, no-tool-execution consumer trial; refresh public sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from asm_protocol.integrations.access_preflight import access_preflight


def read_public(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "asm-access-pilot/0.1", "Accept": "application/json,text/plain"})
    with urlopen(request, timeout=15) as response:
        data = response.read(1_048_577)
        if len(data) > 1_048_576:
            raise ValueError("source exceeds bounded public-read size")
        return data


def refresh() -> dict:
    start = perf_counter()
    commit = json.loads(read_public("https://api.github.com/repos/exa-labs/exa-mcp-server/commits/main"))["sha"]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("invalid source revision")
    raw = read_public(f"https://raw.githubusercontent.com/exa-labs/exa-mcp-server/{commit}/README.md")
    text = raw.decode("utf-8")
    # A bounded provider adapter, not a universal natural-language auth parser.
    # Fail closed when the reviewed statements disappear; do not re-stamp old facts.
    required = [
        "The hosted MCP server works anonymously with rate limits.",
        "Exa Agent requires authentication", "`web_search_exa`", "`agent_run`",
        "For higher limits and access to Exa Agent, use either OAuth or an API key.",
    ]
    if any(statement not in text for statement in required):
        raise ValueError("provider documentation changed; access facts need review")
    now = datetime.now(timezone.utc).isoformat()
    source = f"https://github.com/exa-labs/exa-mcp-server/blob/{commit}/README.md"
    manifests = []
    for tool, function, auth, setup in [
        ("web_search_exa", "web_search", "none", True),
        ("agent_run", "multi_step_research", "api_token_or_oauth", False),
    ]:
        manifests.append({
            "asm_version": "0.3", "service_id": f"exa/{tool}@{commit[:12]}",
            "display_name": tool, "taxonomy": "tool.data.search",
            "capabilities": {"functions": [function]},
            "invocation": {"interface": "mcp", "reach": "cloud", "platforms": ["any"],
                           "agent_operable": True, "auth_to_invoke": auth,
                           "agent_completable_setup": setup},
            "provenance": {"source_url": source, "retrieved_at": now, "last_verified_at": now,
                           "verification_status": "self_reported",
                           "notes": "Adapter author interpretation of provider documentation; not provider-endorsed metadata or observed account access."},
            "ttl": 86400,
            "extensions": {"org.asm.access-pilot": {"scope": "tool", "optional_credentials_effect": "higher_limits" if setup else None}},
        })
    return {"source_commit": commit, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "captured_at": now, "source_http_reads": 2,
            "endpoint_access_declaration": {
                "authentication": "anonymous_with_rate_limits",
                "credential_options": ["oauth", "api_token"],
                "effects": ["higher_limits", "tool_specific_access"],
                "basis": "provider_documentation", "account_grants": "unknown",
            },
            "source_refresh_elapsed_ms": round((perf_counter() - start) * 1000, 3),
            "tool_calls": 0, "api_cost_usd": None, "manifests": manifests}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["web_search", "multi_step_research"], default="web_search")
    parser.add_argument("--auth-context", choices=["anonymous", "configured_unverified"], default="anonymous")
    parser.add_argument("--bundle", type=Path, help="reuse the original source snapshot without changing dates")
    parser.add_argument("--write-bundle", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text()) if args.bundle else refresh()
    if args.write_bundle:
        args.write_bundle.write_text(json.dumps(bundle, indent=2) + "\n")
    start = perf_counter()
    receipt = access_preflight(bundle["manifests"], required_functions=[args.task], auth_context=args.auth_context)
    print(json.dumps({"source": {k:v for k,v in bundle.items() if k != "manifests"},
                      "source_http_reads_this_run": 0 if args.bundle else 2,
                      "preflight_elapsed_ms": round((perf_counter()-start)*1000, 3),
                      "receipt": receipt}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

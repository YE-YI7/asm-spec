#!/usr/bin/env python3
"""Map ASM library entries into AI Catalog (Agent-Card/ai-catalog) entries.

ADR-0012 (accepted): the AI Catalog entry core schema is closed; all custom
properties live in an optional `metadata` object, and "registries can define
their own metadata schemas for entries they host without requiring changes to
the core specification." ASM's value/selection layer is therefore a natural
`metadata.asm` namespace — no core-schema change required.

We follow ASM's own inline-vs-link convention inside the entry: `metadata.asm`
carries the STATIC eligibility/selection signals an agent gates on (taxonomy,
invocation, operational risk); `url` points at the full, mutable ASM manifest
served by the live instance, so pricing/quality/SLA have a single fresh source.

Spec is evolving (PR #37 mediaType->type, PR #36 urn:air: identifiers); fields
here use the current ADR-0012 shape and are annotated in docs/integrations/ai-catalog.md.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from library_select import load_library  # noqa: E402

HOSTED = "https://asm-spec.onrender.com/manifest"
PICK = ["todoist/todoist@current", "culturedcode/things-3@current",
        "amadeus/self-service-api@current", "us-census/data-api@current"]
LIB = {m["service_id"]: m for m in load_library()}


def to_entry(m: dict) -> dict:
    inv = m.get("invocation") or {}
    ops = m.get("operational_constraints") or {}
    # static eligibility/selection signals inline; mutable value behind url
    asm_meta = {
        "asm_version": m.get("asm_version", "0.3"),
        "taxonomy": m.get("taxonomy"),
        "invocation": {k: inv.get(k) for k in
                       ("interface", "reach", "agent_operable",
                        "agent_completable_setup", "setup_requires") if inv.get(k) is not None},
        "manifest_url": f"{HOSTED}/{m['service_id']}",
    }
    if ops:
        asm_meta["operational"] = {"risk_class": ops.get("risk_class"),
                                   "approval": (ops.get("approval") or {}).get("required")}
    import re
    base_id, _, ver = m["service_id"].partition("@")
    org, _, tool = base_id.partition("/")
    part = lambda s: re.sub(r"[^A-Za-z0-9._-]", "-", s)
    entry = {
        "identifier": f"urn:air:asm-spec:{part(org)}:{part(tool or org)}",
        "displayName": m.get("display_name"),
        "type": "application/asm+json",
        "url": f"{HOSTED}/{m['service_id']}",
        "metadata": {"asm": asm_meta},
    }
    if ver:
        entry["version"] = ver
    return entry


catalog = {
    "$comment": "Illustrative AI Catalog document carrying ASM value/selection metadata "
                "via the `metadata` extension point. Not an official ASM<->AI-Catalog "
                "binding; a runnable demonstration that the value layer fits the upstream "
                "cross-protocol standard without core-schema changes.",
    "specVersion": "1.0",
    "entries": [to_entry(LIB[sid]) for sid in PICK if sid in LIB],
}

out = Path(__file__).resolve().parent / "catalog.example.json"
out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out} with {len(catalog['entries'])} entries")
for e in catalog["entries"]:
    a = e["metadata"]["asm"]
    print(f"  {e['displayName']:24} reach={a['invocation'].get('reach')} "
          f"setup_ok={a['invocation'].get('agent_completable_setup')} "
          f"risk={a.get('operational',{}).get('risk_class')}")

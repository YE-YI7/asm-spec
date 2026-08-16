#!/usr/bin/env python3
"""Map ASM library entries into AI Catalog (Agent-Card/ai-catalog) entries.

The current AI Catalog entry schema puts custom properties in `extensions`.
Extension keys must be a valid URL or reverse-DNS string, so ASM uses the
`io.github.ye-yi7.asm.selection` namespace without changing the core schema.

We follow ASM's own inline-vs-link convention inside the entry: the extension
carries the STATIC eligibility/selection signals an agent gates on (taxonomy,
invocation, operational risk); `url` points at the full, mutable ASM manifest
served by the live instance, so pricing/quality/SLA have a single fresh source.

Fields here follow the public specification checked on 2026-08-16 and are
annotated in docs/integrations/ai-catalog.md.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from library_select import load_library  # noqa: E402

HOSTED = "https://asm-spec.onrender.com/manifest"
EXTENSION_KEY = "io.github.ye-yi7.asm.selection"
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
        "identifier": f"urn:air:github.com:ye-yi7:asm:{part(org)}:{part(tool or org)}",
        "displayName": m.get("display_name"),
        "type": "application/asm+json",
        "url": f"{HOSTED}/{m['service_id']}",
        "extensions": {EXTENSION_KEY: asm_meta},
    }
    if ver:
        entry["version"] = ver
    return entry


catalog = {
    "$comment": "Illustrative AI Catalog document carrying ASM value/selection metadata "
                "via a namespaced `extensions` entry. Not an official ASM<->AI-Catalog "
                "binding; a runnable demonstration that the value layer fits the upstream "
                "cross-protocol standard without core-schema changes.",
    "specVersion": "1.0",
    "entries": [to_entry(LIB[sid]) for sid in PICK if sid in LIB],
}

out = Path(__file__).resolve().parent / "catalog.example.json"
out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out} with {len(catalog['entries'])} entries")
for e in catalog["entries"]:
    a = e["extensions"][EXTENSION_KEY]
    print(f"  {e['displayName']:24} reach={a['invocation'].get('reach')} "
          f"setup_ok={a['invocation'].get('agent_completable_setup')} "
          f"risk={a.get('operational',{}).get('risk_class')}")

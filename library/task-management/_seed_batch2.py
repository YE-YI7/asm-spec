#!/usr/bin/env python3
"""Library batch 2 (task-management): Notion, Motion, Any.do.

Verified this pass (2026-06): invocation (incl. that Any.do has NO direct public
API, only Zapier), pricing, no-AI-training stances. Unverified fields omitted, not
faked. Validates against the schema and writes *.asm.json here.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
R = "2026-06-08T00:00:00Z"
TAX = "tool.productivity.task_management"

entries = {
  "notion": {
    "asm_version": "0.3", "service_id": "notion/notion@current", "taxonomy": TAX,
    "display_name": "Notion",
    "capabilities": {"description": "Workspace combining notes, databases, tasks, projects and wiki; usable as a planner.",
        "functions": ["tasks","databases","projects","notes","wiki","calendar_view","recurring_tasks","collaboration"]},
    "invocation": {"interface": "rest_api", "reach": "cloud", "agent_operable": True, "auth_to_invoke": "oauth",
        "platforms": ["web","macos","windows","ios","android"], "docs_url": "https://developers.notion.com/"},
    "pricing": {"billing_dimensions": [{"dimension":"user","unit":"per_month","cost_per_unit":10,"currency":"USD"}]},
    "payment": {"methods": ["free_tier","subscription"], "auth_type": "account", "signup_url": "https://notion.com"},
    "usage_terms": {"automation_allowed": "yes", "license": "Public REST API, free on all plans (~3 req/s)",
        "tos_url": "https://notion.com/terms"},
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "retention": "Non-Enterprise: 3rd-party LLM providers retain data <=30 days; Enterprise: zero retention. SOC 2 certified.",
        "lock_in_notes": "Notion AI sends data to 3rd-party LLMs (OpenAI/Anthropic) under contractual no-train agreements; export available."},
    "provenance": {"source_url": "https://developers.notion.com/", "retrieved_at": R, "last_verified_at": R,
        "verification_status": "self_reported",
        "notes": "Verified 2026-06: free REST API, Plus $10 / Business $18, no-AI-training (Notion AI security docs), SOC 2. App-store rating not separately verified."},
  },
  "motion": {
    "asm_version": "0.3", "service_id": "usemotion/motion@current", "taxonomy": TAX,
    "display_name": "Motion (usemotion.com)",
    "capabilities": {"description": "AI calendar/scheduler that auto-plans tasks and meetings; paid, no free tier.",
        "functions": ["tasks","projects","ai_scheduling","auto_prioritization","calendar","recurring_tasks"]},
    "invocation": {"interface": "rest_api", "reach": "cloud", "agent_operable": True, "auth_to_invoke": "api_token",
        "platforms": ["web","macos","windows","ios","android"], "docs_url": "https://docs.usemotion.com/"},
    "pricing": {"billing_dimensions": [{"dimension":"user","unit":"per_month","cost_per_unit":19,"currency":"USD"}]},
    "payment": {"methods": ["subscription"], "auth_type": "account", "signup_url": "https://usemotion.com"},
    "usage_terms": {"automation_allowed": "yes", "license": "Public REST API via X-API-Key header"},
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "lock_in_notes": "Motion and its LLM providers (incl. OpenAI) do not train on user inputs/outputs. SOC 2 Type II."},
    "provenance": {"source_url": "https://docs.usemotion.com/", "retrieved_at": R, "last_verified_at": R,
        "verification_status": "self_reported",
        "notes": "Verified 2026-06: REST API (X-API-Key), $34/mo or $19/mo annual, NO free tier (7-day trial), no-AI-training + SOC 2 (usemotion.com/security). Distinct from themotionapp.com (a golf app)."},
  },
  "any-do": {
    "asm_version": "0.3", "service_id": "any-do/any-do@current", "taxonomy": TAX,
    "display_name": "Any.do",
    "capabilities": {"description": "Cross-platform task/reminder app; reachable by agents only through Zapier, not a direct API.",
        "functions": ["tasks","reminders","lists","recurring_tasks","calendar","collaboration"]},
    "invocation": {"interface": "zapier", "reach": "cloud", "agent_operable": False, "auth_to_invoke": "oauth",
        "automation_paths": ["zapier"], "platforms": ["web","macos","windows","ios","android"],
        "docs_url": "https://support.any.do/en/articles/8619416-any-do-zapier"},
    "pricing": {"billing_dimensions": [{"dimension":"user","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment": {"methods": ["free_tier","subscription"], "auth_type": "account", "signup_url": "https://any.do"},
    "usage_terms": {"automation_allowed": "conditional",
        "notes": "No standalone public REST API; automation only via Zapier (an intermediary), not direct agent calls."},
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "lock_in_notes": "States it does not use data obtained via Google Workspace APIs to train ML/AI models (statement is API-scoped, not necessarily all data)."},
    "provenance": {"source_url": "https://support.any.do/en/articles/8619416-any-do-zapier", "retrieved_at": R, "last_verified_at": R,
        "verification_status": "self_reported",
        "notes": "Verified 2026-06: NO direct public REST API -> agent-operable only via Zapier (agent_operable=False for direct calls). Freemium; Premium price not verified this pass. Google-API no-train statement is scoped."},
  },
}

validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for slug, m in entries.items():
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {slug}: {errs[0].message}", file=sys.stderr); continue
    (HERE / f"{slug}.asm.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    print(f"OK {slug:10} interface={m['invocation']['interface']:9} agent_operable={m['invocation']['agent_operable']}")
print(f"\n{ok}/{len(entries)} batch-2 entries valid + written")

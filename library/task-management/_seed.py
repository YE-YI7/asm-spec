#!/usr/bin/env python3
"""Seed the first ASM library batch: personal task / reminder managers.

Each entry captures the FULL value picture an agent needs to pick a tool, NOT a
single axis. Only verified dimensions are populated (pricing, invocation,
platform, usage-terms-automation); quality benchmarks and data_governance are
left out where unverified rather than fabricated, and flagged in provenance.

Run: python library/task-management/_seed.py   (validates + writes *.json here)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
RETRIEVED = "2026-06-08T00:00:00Z"
PENDING = ("Verified this pass: pricing, invocation (reach/interface), platforms, "
           "usage_terms.automation_allowed. Pending research: quality benchmarks, "
           "data_governance (ownership/training/retention). Not fabricated.")

TAX = "tool.productivity.task_management"

def free_pricing():
    return {"billing_dimensions": [
        {"dimension": "user", "unit": "per_1", "cost_per_unit": 0, "currency": "USD"}]}

entries = {
  "todoist": {
    "asm_version": "0.3", "service_id": "todoist/todoist@current", "taxonomy": TAX,
    "display_name": "Todoist",
    "capabilities": {"description": "Cross-platform task manager with natural-language capture, recurring tasks, filters.",
        "functions": ["tasks","recurring_tasks","reminders","sub_tasks","labels","filters","natural_language_capture","calendar_view","collaboration"]},
    "invocation": {"interface": "rest_api", "reach": "cloud", "agent_operable": True,
        "auth_to_invoke": "oauth", "platforms": ["web","macos","ios","windows","android","linux"],
        "docs_url": "https://developer.todoist.com/api/v1/"},
    "pricing": {"billing_dimensions": [{"dimension": "user","unit":"per_month","cost_per_unit":5,"currency":"USD"}]},
    "payment": {"methods": ["free_tier","subscription"], "auth_type": "account", "signup_url": "https://todoist.com"},
    "usage_terms": {"automation_allowed": "yes", "license": "Public developer REST API (free tier rate-limited)",
        "tos_url": "https://todoist.com/terms"},
    "provenance": {"source_url": "https://developer.todoist.com/api/v1/", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported", "notes": "Free tier + Pro $5/mo. " + PENDING},
  },
  "microsoft-to-do": {
    "asm_version": "0.3", "service_id": "microsoft/to-do@current", "taxonomy": TAX,
    "display_name": "Microsoft To Do",
    "capabilities": {"description": "Free cross-platform task manager, deep Microsoft 365 / Outlook integration.",
        "functions": ["tasks","lists","due_dates","reminders","recurring_tasks","my_day","steps","m365_integration"]},
    "invocation": {"interface": "graph_api", "reach": "cloud", "agent_operable": True,
        "auth_to_invoke": "oauth", "platforms": ["web","macos","ios","windows","android"],
        "docs_url": "https://learn.microsoft.com/en-us/graph/api/resources/todo-overview"},
    "pricing": free_pricing(),
    "payment": {"methods": ["free_tier"], "auth_type": "account", "signup_url": "https://to-do.office.com"},
    "usage_terms": {"automation_allowed": "yes", "license": "Microsoft Graph API (delegated + application permissions)",
        "tos_url": "https://www.microsoft.com/servicesagreement"},
    "provenance": {"source_url": "https://learn.microsoft.com/en-us/graph/api/resources/todo-overview", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported", "notes": "Fully free. " + PENDING},
  },
  "google-tasks": {
    "asm_version": "0.3", "service_id": "google/tasks@current", "taxonomy": TAX,
    "display_name": "Google Tasks",
    "capabilities": {"description": "Free lightweight task manager integrated with Gmail and Google Calendar.",
        "functions": ["tasks","sub_tasks","due_dates","gmail_integration","calendar_integration"]},
    "invocation": {"interface": "rest_api", "reach": "cloud", "agent_operable": True,
        "auth_to_invoke": "oauth", "platforms": ["web","android","ios"],
        "docs_url": "https://developers.google.com/tasks"},
    "pricing": free_pricing(),
    "payment": {"methods": ["free_tier"], "auth_type": "account", "signup_url": "https://tasks.google.com"},
    "usage_terms": {"automation_allowed": "yes", "license": "Google Tasks API (OAuth)",
        "tos_url": "https://policies.google.com/terms"},
    "provenance": {"source_url": "https://developers.google.com/tasks", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported", "notes": "Fully free. " + PENDING},
  },
  "ticktick": {
    "asm_version": "0.3", "service_id": "ticktick/ticktick@current", "taxonomy": TAX,
    "display_name": "TickTick",
    "capabilities": {"description": "Feature-complete task manager bundling pomodoro timer, habit tracking, calendar.",
        "functions": ["tasks","recurring_tasks","reminders","pomodoro_timer","habit_tracking","calendar_view","sub_tasks"]},
    "invocation": {"interface": "rest_api", "reach": "cloud", "agent_operable": True,
        "auth_to_invoke": "oauth", "platforms": ["web","macos","ios","windows","android"],
        "docs_url": "https://developer.ticktick.com/"},
    "pricing": {"billing_dimensions": [{"dimension":"user","unit":"per_year","cost_per_unit":35.99,"currency":"USD"}]},
    "payment": {"methods": ["free_tier","subscription"], "auth_type": "account", "signup_url": "https://ticktick.com"},
    "usage_terms": {"automation_allowed": "conditional", "license": "Open API (OAuth, limited scope)",
        "notes": "Public Open API exists but with a narrower scope than the app's full feature set."},
    "provenance": {"source_url": "https://developer.ticktick.com/", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported",
        "notes": "Free tier + Premium $35.99/yr. Has pomodoro built-in (relevant to study-plan tasks). " + PENDING},
  },
  "things-3": {
    "asm_version": "0.3", "service_id": "culturedcode/things-3@current", "taxonomy": TAX,
    "display_name": "Things 3",
    "capabilities": {"description": "Award-winning Apple-only task manager; no cloud API, local automation only.",
        "functions": ["tasks","projects","areas","reminders","recurring_tasks","today_view","this_evening"]},
    "invocation": {"interface": "applescript", "reach": "local_device", "agent_operable": True,
        "auth_to_invoke": "device_local", "automation_paths": ["applescript","url_scheme","shortcuts"],
        "platforms": ["macos","ios"], "docs_url": "https://culturedcode.com/things/support/articles/2803573/"},
    "pricing": {"billing_dimensions": [{"dimension":"license","unit":"per_1","cost_per_unit":49.99,"currency":"USD"}]},
    "payment": {"methods": ["one_time_purchase"], "auth_type": "none", "signup_url": "https://culturedcode.com/things/"},
    "usage_terms": {"automation_allowed": "conditional",
        "notes": "No public cloud API. Driveable only by an agent running on the user's own Apple device via AppleScript / URL scheme / Shortcuts."},
    "provenance": {"source_url": "https://culturedcode.com/things/support/articles/2967034/", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported",
        "notes": "One-time $49.99 (macOS); iOS/iPad sold separately. Apple-only; a CLOUD agent cannot drive it (reach=local_device). " + PENDING},
  },
  "apple-reminders": {
    "asm_version": "0.3", "service_id": "apple/reminders@current", "taxonomy": TAX,
    "display_name": "Apple Reminders",
    "capabilities": {"description": "Free Apple-ecosystem reminders app; automatable on-device via Shortcuts / Siri / EventKit.",
        "functions": ["reminders","lists","due_dates","location_reminders","recurring_tasks","siri_capture"]},
    "invocation": {"interface": "shortcuts", "reach": "local_device", "agent_operable": True,
        "auth_to_invoke": "device_local", "automation_paths": ["shortcuts","siri","eventkit"],
        "platforms": ["macos","ios"], "docs_url": "https://support.apple.com/guide/shortcuts/welcome/ios"},
    "pricing": free_pricing(),
    "payment": {"methods": ["free_tier"], "auth_type": "none"},
    "usage_terms": {"automation_allowed": "conditional",
        "notes": "No developer cloud API. On-device automation only via Shortcuts/Siri/EventKit; requires an agent resident on the user's Apple device."},
    "provenance": {"source_url": "https://support.apple.com/guide/shortcuts/welcome/ios", "retrieved_at": RETRIEVED,
        "last_verified_at": RETRIEVED, "verification_status": "self_reported",
        "notes": "Free, Apple-only; reach=local_device (a cloud agent cannot drive it). " + PENDING},
  },
}

import jsonschema
validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for slug, m in entries.items():
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {slug}: {errs[0].message}", file=sys.stderr); continue
    (OUT / f"{slug}.asm.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    ok += 1
    print(f"OK  {slug}  reach={m['invocation']['reach']:12} agent_operable={m['invocation']['agent_operable']}")
print(f"\n{ok}/{len(entries)} entries valid + written to {OUT}")

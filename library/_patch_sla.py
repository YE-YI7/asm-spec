#!/usr/bin/env python3
"""Patch verified, published SLAs into library entries (sourced 2026-06-09).

- Slack: 99.99% uptime SLA — paid Business+/Enterprise Grid tiers (slack.com SLA).
- GitHub: 99.9% quarterly uptime SLA — Enterprise Cloud only (github.com/customer-terms).
- Google Workspace SLA: 99.9% monthly uptime; covered services explicitly include
  Gmail AND Google Tasks (workspace.google.com/terms/sla) — applies to paid Workspace.

Free tiers carry no SLA; the tier scoping is recorded in provenance notes rather
than silently implying the free tier is covered.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))

PATCH = {
  "library/communication/slack-api.asm.json": {
    "sla": {"uptime": 0.9999},
    "note_append": " SLA verified 2026-06: 99.99% uptime guarantee applies to paid Business+/Enterprise Grid plans (not the free tier); 100x credit policy.",
  },
  "library/developer-tools/github-api.asm.json": {
    "sla": {"uptime": 0.999},
    "note_append": " SLA verified 2026-06: 99.9% quarterly uptime SLA applies to GitHub Enterprise Cloud customers only (github.com/customer-terms/github-online-services-sla).",
  },
  "library/communication/gmail-api.asm.json": {
    "sla": {"uptime": 0.999},
    "note_append": " SLA verified 2026-06: Google Workspace SLA 99.9% monthly uptime; Gmail is a covered service (paid Workspace tiers).",
  },
  "library/task-management/google-tasks.asm.json": {
    "sla": {"uptime": 0.999},
    "note_append": " SLA verified 2026-06: Google Tasks is an explicitly covered service under the Google Workspace 99.9% SLA (paid Workspace tiers).",
  },
}

validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for rel, patch in PATCH.items():
    p = ROOT / rel
    m = json.loads(p.read_text(encoding="utf-8"))
    m.setdefault("sla", {}).update(patch["sla"])
    m["provenance"]["notes"] = m["provenance"].get("notes", "").rstrip() + patch["note_append"]
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {rel}: {errs[0].message}", file=sys.stderr); continue
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    print(f"OK {p.name:28} uptime={m['sla']['uptime']}")
print(f"\n{ok}/{len(PATCH)} SLA patches applied + revalidated")

#!/usr/bin/env python3
"""Patch verified data_governance into design-domain entries (sourced 2026-06).

Figma / Canva: AI content-training is opt-out (with enterprise tiers never trained).
Adobe Photoshop: Firefly trained on licensed content, not customer content.
Photopea + Google Tasks remain 'unknown' elsewhere (no clear source) — not touched here.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))

PATCH = {
  "figma": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "opt_out",
        "lock_in_notes": "AI content-training is a per-team setting: ON by default for Starter/Professional (admin can opt out), OFF by default for Organization/Enterprise."},
    "note": "Verified 2026-06: REST + plugin API, free Starter + paid ~$15/seat; AI content-training opt-out (default on Starter/Pro, off Org/Enterprise — Figma AI settings docs).",
  },
  "canva": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "opt_out",
        "lock_in_notes": "Free/Pro: AI training on by default, opt-out available. Teams/Business/Enterprise/Education: content is NEVER used for training and cannot be opted in."},
    "note": "Verified 2026-06: Connect API, free Starter + paid ~$15/mo; AI-training opt-out for Free/Pro, never for Enterprise tiers (Canva AI Product Terms).",
  },
  "photoshop": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "lock_in_notes": "Adobe Firefly is trained on licensed / Adobe Stock / public-domain content, not customer content; IP indemnification on enterprise. ISO 27001."},
    "note": "Verified 2026-06: local scripting (UXP/ExtendScript) + cloud API; ~$22.99/mo, no free tier; Firefly trained on licensed content, not customer content (Adobe).",
  },
}

validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for slug, patch in PATCH.items():
    p = HERE / f"{slug}.asm.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m["data_governance"] = patch["data_governance"]
    m["provenance"]["notes"] = patch["note"]
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {slug}: {errs[0].message}", file=sys.stderr); continue
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    print(f"OK {slug:10} trains_on_user_data={m['data_governance']['trains_on_user_data']}")
print(f"\n{ok}/{len(PATCH)} design-governance patches applied + revalidated")

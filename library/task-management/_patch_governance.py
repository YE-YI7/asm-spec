#!/usr/bin/env python3
"""Patch verified quality + data_governance into the task-management library batch.

Only sourced facts are written. Where a provider does not clearly state a
practice (e.g. Google re: Tasks data training), the field is 'unknown' rather
than guessed. Re-validates each entry against the schema and rewrites in place.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))

def rating(name, score, store, url=None):
    m = {"name": name, "score": score, "scale": "0-5", "benchmark": store, "self_reported": False}
    if url: m["benchmark_url"] = url
    return m

PATCH = {
  "todoist": {
    "quality": {"metrics": [
        rating("app_store_rating_ios", 4.8, "Apple App Store user rating", "https://apps.apple.com/app/id572688855"),
        rating("play_store_rating", 4.6, "Google Play user rating")]},
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "retention": "GDPR-compliant; user retains all rights to their data",
        "lock_in_notes": "Provider owns code/DB infrastructure; user data is exportable and user-owned."},
    "note": "Verified 2026-06: pricing, invocation, platforms, automation, app-store quality, and no-AI-training (Doist security/privacy docs).",
  },
  "ticktick": {
    "quality": {"metrics": [
        rating("app_store_rating_ios", 4.8, "Apple App Store user rating"),
        rating("play_store_rating", 4.5, "Google Play user rating")]},
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "retention": "GDPR-compliant; user retains rights to their data",
        "lock_in_notes": "Provider owns code/DB; AI limited to feature delivery, not shared with 3rd-party AI nor used for training."},
    "note": "Verified 2026-06: pricing, invocation, platforms, app-store quality, and no-AI-training (TickTick privacy policy). Open API scope narrower than full app.",
  },
  "microsoft-to-do": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "no",
        "residency": ["us", "eu"],
        "lock_in_notes": "Microsoft states M365 subscription data is not used to train its AI models; data within the Microsoft Graph."},
    "note": "Verified 2026-06: free, invocation (Graph API), platforms, no-AI-training on M365 data. App-store rating not separately verified.",
  },
  "google-tasks": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "unknown",
        "lock_in_notes": "Google does not specifically state whether Tasks data is used for AI training; consumer smart-features are opt-out. Treat as unverified."},
    "note": "Verified 2026-06: free, invocation (Tasks API), Gmail/Calendar integration. Data-training stance for Tasks NOT clearly documented -> unknown, not assumed.",
  },
  "things-3": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "unknown",
        "lock_in_notes": "Apple-only; data in Things Cloud. No public cloud export API; export via app only."},
    "note": "Verified 2026-06: one-time $49.99 (macOS), local-only invocation, Apple platforms. Governance lightly sourced; training stance unknown.",
  },
  "apple-reminders": {
    "data_governance": {"data_owner": "user", "exportable": True, "trains_on_user_data": "unknown",
        "residency": ["us"], "lock_in_notes": "Apple ecosystem; data in iCloud. Apple's general posture is on-device privacy, but no Reminders-specific training statement was verified."},
    "note": "Verified 2026-06: free, Apple-only, local-only invocation. System app (no store rating). Training stance not specifically documented -> unknown.",
  },
}

validator = jsonschema.Draft202012Validator(SCHEMA) if (jsonschema := __import__("jsonschema")) else None
ok = 0
for slug, patch in PATCH.items():
    p = HERE / f"{slug}.asm.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    if "quality" in patch: m["quality"] = patch["quality"]
    if "data_governance" in patch: m["data_governance"] = patch["data_governance"]
    if "note" in patch: m["provenance"]["notes"] = patch["note"]
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {slug}: {errs[0].message}", file=sys.stderr); continue
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    gov = m["data_governance"]
    print(f"OK {slug:16} trains_on_user_data={gov['trains_on_user_data']:8} quality={'yes' if 'quality' in m else '-'}")
print(f"\n{ok}/{len(PATCH)} entries patched + revalidated")

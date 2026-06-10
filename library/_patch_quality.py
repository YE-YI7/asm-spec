#!/usr/bin/env python3
"""Patch sourced public ratings into library entries (researched 2026-06-11).

Sources: Apple App Store listings, G2 review pages, Trustpilot. Only entries with
a citable score are patched. Deliberately skipped (no solid public rating):
Any.do (only a 35-review AppSumo score), Google Tasks (bundled, unrated),
Apple Reminders (system app), Photopea (no store/G2 listing), and the four
real-estate APIs (not consumer apps; store ratings do not exist — their quality
needs domain metrics like coverage/freshness, tracked in the coverage report).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))

def m(name, score, benchmark, url):
    return {"name": name, "score": score, "scale": "0-5",
            "benchmark": benchmark, "benchmark_url": url, "self_reported": False}

PATCH = {
  "library/task-management/things-3.asm.json": [
      m("app_store_rating_ios", 4.8, "Apple App Store user rating (~27K ratings, 2026-06)",
        "https://apps.apple.com/us/app/things-3/id904237743")],
  "library/task-management/notion.asm.json": [
      m("g2_rating", 4.6, "G2 verified-review rating (2026-06)",
        "https://www.g2.com/products/notion/reviews")],
  "library/task-management/motion.asm.json": [
      m("trustpilot_rating", 3.8, "Trustpilot user rating (2026-06)",
        "https://www.trustpilot.com/review/www.usemotion.com")],
  "library/task-management/microsoft-to-do.asm.json": [
      m("g2_rating", 4.4, "G2 verified-review rating (90 reviews, 2026-06)",
        "https://www.g2.com/products/microsoft-to-do/reviews")],
  "library/creative-design/figma.asm.json": [
      m("g2_rating", 4.6, "G2 verified-review rating (~1.9K reviews, 2026-06)",
        "https://www.g2.com/products/figma/reviews")],
  "library/creative-design/canva.asm.json": [
      m("g2_rating", 4.7, "G2 verified-review rating (~6.4K reviews, 2026-06)",
        "https://www.g2.com/products/canva/reviews")],
  "library/creative-design/photoshop.asm.json": [
      m("g2_rating", 4.6, "G2 verified-review rating (~13K reviews, 2026-06)",
        "https://www.g2.com/products/adobe-photoshop/reviews")],
  "library/creative-design/gimp.asm.json": [
      m("g2_rating", 4.3, "G2 verified-review rating (2026-06)",
        "https://www.g2.com/products/gimp/reviews")],
  "library/creative-design/procreate.asm.json": [
      m("app_store_rating_ios", 4.4, "Apple App Store user rating (~49K ratings, 2026-06)",
        "https://apps.apple.com/us/app/procreate/id425073498")],
  "library/creative-design/affinity-designer.asm.json": [
      m("g2_rating", 4.6, "G2 verified-review rating (246 reviews, 2026-06)",
        "https://www.g2.com/products/affinity-designer/reviews")],
}

validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for rel, metrics in PATCH.items():
    p = ROOT / rel
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["quality"] = {"metrics": metrics}
    errs = list(validator.iter_errors(doc))
    if errs:
        print(f"INVALID {rel}: {errs[0].message}", file=sys.stderr); continue
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    q = metrics[0]
    print(f"OK {p.name:30} {q['name']}={q['score']}")
print(f"\n{ok}/{len(PATCH)} quality patches applied + revalidated")

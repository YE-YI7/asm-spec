#!/usr/bin/env python3
"""Library domain 2: creative / design tools.

Chosen to stress the invocability axis the task domain barely exercised: the
candidates span clean cloud APIs -> local desktop scripting -> GUI-only tools an
agent cannot programmatically drive at all. Verified this pass (2026-06):
invocation + pricing. Data-governance verified only for local/open-source tools;
cloud-tool training stance left 'unknown' (not fabricated).

Run: python library/creative-design/_seed.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
R = "2026-06-08T00:00:00Z"
TAX = "tool.creative.design"
PEND = "Governance training-stance not verified this pass -> unknown, not assumed."

def prov(url, note):
    return {"source_url": url, "retrieved_at": R, "last_verified_at": R,
            "verification_status": "self_reported", "notes": note}

entries = {
  "figma": {
    "asm_version":"0.3","service_id":"figma/figma@current","taxonomy":TAX,"display_name":"Figma",
    "capabilities":{"description":"Collaborative interface/vector design; cloud, scriptable via REST + plugin APIs.",
        "functions":["vector_design","ui_design","components","collaboration","dev_mode","export"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"oauth",
        "platforms":["web","macos","windows"],"docs_url":"https://developers.figma.com/docs/rest-api/"},
    "pricing":{"billing_dimensions":[{"dimension":"seat","unit":"per_month","cost_per_unit":15,"currency":"USD"}]},
    "payment":{"methods":["free_tier","subscription"],"auth_type":"account","signup_url":"https://figma.com"},
    "usage_terms":{"automation_allowed":"yes","license":"Public REST API + plugin API"},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"unknown"},
    "provenance":prov("https://developers.figma.com/docs/rest-api/","Verified 2026-06: REST+plugin API, free Starter + paid ~$15/seat. "+PEND),
  },
  "canva": {
    "asm_version":"0.3","service_id":"canva/canva@current","taxonomy":TAX,"display_name":"Canva",
    "capabilities":{"description":"Template-first graphic design; cloud, scriptable via the Connect API.",
        "functions":["templates","graphic_design","presentations","brand_kit","ai_design","export"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"oauth",
        "platforms":["web","ios","android"],"docs_url":"https://www.canva.dev/docs/connect/"},
    "pricing":{"billing_dimensions":[{"dimension":"seat","unit":"per_month","cost_per_unit":15,"currency":"USD"}]},
    "payment":{"methods":["free_tier","subscription"],"auth_type":"account","signup_url":"https://canva.com"},
    "usage_terms":{"automation_allowed":"yes","license":"Canva Connect API"},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"unknown"},
    "provenance":prov("https://www.canva.dev/docs/connect/","Verified 2026-06: Connect API, free Starter + paid ~$15/mo. "+PEND),
  },
  "photoshop": {
    "asm_version":"0.3","service_id":"adobe/photoshop@current","taxonomy":TAX,"display_name":"Adobe Photoshop",
    "capabilities":{"description":"Professional raster editor; drivable via local UXP/ExtendScript scripting and a cloud Photoshop API.",
        "functions":["photo_editing","layers","retouching","generative_fill","batch_actions","export"]},
    "invocation":{"interface":"sdk","reach":"hybrid","agent_operable":True,"auth_to_invoke":"api_token",
        "automation_paths":["uxp","extendscript","photoshop_api"],"platforms":["macos","windows"],
        "docs_url":"https://developer.adobe.com/photoshop/"},
    "pricing":{"billing_dimensions":[{"dimension":"seat","unit":"per_month","cost_per_unit":22.99,"currency":"USD"}]},
    "payment":{"methods":["subscription"],"auth_type":"account","signup_url":"https://adobe.com/products/photoshop"},
    "usage_terms":{"automation_allowed":"yes","license":"Local scripting (UXP/ExtendScript) + cloud Photoshop API (Firefly Services)"},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"unknown",
        "lock_in_notes":"Adobe publicly states it does not train generative AI on customer content; not re-verified this pass."},
    "provenance":prov("https://developer.adobe.com/photoshop/","Verified 2026-06: local scripting + cloud API; subscription ~$22.99/mo, no free tier. "+PEND),
  },
  "gimp": {
    "asm_version":"0.3","service_id":"gimp/gimp@current","taxonomy":TAX,"display_name":"GIMP",
    "capabilities":{"description":"Free open-source raster editor; local automation via Script-Fu / Python-Fu.",
        "functions":["photo_editing","layers","scripting","batch_processing","export"]},
    "invocation":{"interface":"cli","reach":"local_device","agent_operable":True,"auth_to_invoke":"none",
        "automation_paths":["script-fu","python-fu"],"platforms":["macos","windows","linux"],
        "docs_url":"https://www.gimp.org/docs/"},
    "pricing":{"billing_dimensions":[{"dimension":"license","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["free_tier"],"auth_type":"none"},
    "usage_terms":{"automation_allowed":"yes","license":"GPL (open source)"},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"no",
        "lock_in_notes":"Local desktop, open-source (GPL); no cloud — data never leaves the machine."},
    "provenance":prov("https://www.gimp.org/docs/","Verified 2026-06: free/GPL, local Script-Fu/Python-Fu automation; data fully local (reach=local_device)."),
  },
  "photopea": {
    "asm_version":"0.3","service_id":"photopea/photopea@current","taxonomy":TAX,"display_name":"Photopea",
    "capabilities":{"description":"Free web-based Photoshop-compatible editor; scriptable in JavaScript (v2.9+).",
        "functions":["photo_editing","psd_support","layers","scripting","export"]},
    "invocation":{"interface":"sdk","reach":"cloud","agent_operable":True,"auth_to_invoke":"none",
        "automation_paths":["javascript_scripts","embed_api"],"platforms":["web"],
        "docs_url":"https://www.photopea.com/learn/scripts"},
    "pricing":{"billing_dimensions":[{"dimension":"user","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["free_tier"],"auth_type":"none","signup_url":"https://photopea.com"},
    "usage_terms":{"automation_allowed":"yes","license":"In-app JavaScript scripting + embeddable API"},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"unknown",
        "lock_in_notes":"Browser-based; files can be kept local. Free (ad-supported)."},
    "provenance":prov("https://www.photopea.com/learn/scripts","Verified 2026-06: free, web, JS scripting since v2.9. "+PEND),
  },
  "affinity-designer": {
    "asm_version":"0.3","service_id":"serif/affinity-designer@current","taxonomy":TAX,"display_name":"Affinity Designer",
    "capabilities":{"description":"One-time-purchase pro design suite; NO scripting/automation API — GUI only.",
        "functions":["vector_design","photo_editing","publishing","export"]},
    "invocation":{"interface":"gui","reach":"local_device","agent_operable":False,"auth_to_invoke":"device_local",
        "automation_paths":["computer_use"],"platforms":["macos","windows","ios"],
        "docs_url":"https://affinity.serif.com/"},
    "pricing":{"billing_dimensions":[{"dimension":"license","unit":"per_1","cost_per_unit":69.99,"currency":"USD"}]},
    "payment":{"methods":["one_time_purchase"],"auth_type":"none","signup_url":"https://affinity.serif.com/"},
    "usage_terms":{"automation_allowed":"no","notes":"No public scripting or automation API; only fragile pixel-level GUI control."},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"no",
        "lock_in_notes":"Local desktop app, files local; one-time purchase, no subscription."},
    "provenance":prov("https://affinity.serif.com/","Verified 2026-06: one-time ~$69.99/app (suite ~$164), NO automation API -> agent_operable=False (only computer-use clicking)."),
  },
  "procreate": {
    "asm_version":"0.3","service_id":"procreate/procreate@current","taxonomy":TAX,"display_name":"Procreate",
    "capabilities":{"description":"iPad illustration app; one-time purchase, NO automation/scripting API — pure GUI.",
        "functions":["illustration","painting","brushes","layers","animation","export"]},
    "invocation":{"interface":"gui","reach":"local_device","agent_operable":False,"auth_to_invoke":"device_local",
        "automation_paths":["computer_use"],"platforms":["ios"],
        "docs_url":"https://procreate.com/"},
    "pricing":{"billing_dimensions":[{"dimension":"license","unit":"per_1","cost_per_unit":12.99,"currency":"USD"}]},
    "payment":{"methods":["one_time_purchase"],"auth_type":"none","signup_url":"https://procreate.com/"},
    "usage_terms":{"automation_allowed":"no","notes":"iPad-only GUI app; no automation/scripting interface at all."},
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"no",
        "lock_in_notes":"On-device iPad app; artwork stays local. One-time purchase."},
    "provenance":prov("https://procreate.com/","Verified 2026-06: one-time $12.99, iPad GUI only, no automation API -> agent_operable=False."),
  },
}

validator = jsonschema.Draft202012Validator(SCHEMA)
ok = 0
for slug, m in entries.items():
    errs = list(validator.iter_errors(m))
    if errs:
        print(f"INVALID {slug}: {errs[0].message}", file=sys.stderr); continue
    (HERE / f"{slug}.asm.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); ok += 1
    inv = m["invocation"]
    print(f"OK {slug:18} interface={inv['interface']:9} reach={inv['reach']:12} agent_operable={inv['agent_operable']}")
print(f"\n{ok}/{len(entries)} creative-design entries valid + written")

#!/usr/bin/env python3
"""Library domain (Bruce/Pipeworx stress test): real-estate data sources.

Built to exercise the invocability-SETUP axis Bruce asked for: distinguishing
tools that are immediately usable from tools that technically accept credentials
but still need a human-in-the-loop step (signup, payment, OAuth consent, MLS
approval) an agent cannot complete unattended. Verified 2026-06 from each
provider's developer docs.

Spectrum:
  Census Data API  -> keyless for low volume (free key optional)     -> agent_completable_setup=true
  HUD USER API     -> free, but account + bearer token (signup)       -> false: free_api_key_signup
  ATTOM Property   -> 30-day trial key, paid for production           -> false: paid_signup
  RESO Web API     -> OAuth2 + per-MLS membership + licensing         -> false: licensing + oauth
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
R = "2026-06-09T00:00:00Z"
TAX = "tool.data.real_estate"
READ_ONLY_OPS = {"risk_class": "low",
                 "side_effects": ["external_api_call", "network_access", "read_only"],
                 "approval": {"required": "never"}}

def prov(url, note):
    return {"source_url": url, "retrieved_at": R, "last_verified_at": R,
            "verification_status": "self_reported", "notes": note}

entries = {
  "us-census-data-api": {
    "asm_version":"0.3","service_id":"us-census/data-api@current","taxonomy":TAX,
    "display_name":"US Census Bureau Data API",
    "capabilities":{"description":"Free US demographic, economic and housing statistics API.",
        "functions":["real_estate_data","demographics","housing_stats","geography"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"none",
        "agent_completable_setup":True,"setup_requires":[],
        "platforms":["web"],"docs_url":"https://www.census.gov/data/developers.html"},
    "pricing":{"billing_dimensions":[{"dimension":"request","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["free_tier"],"auth_type":"none"},
    "usage_terms":{"automation_allowed":"yes","license":"US Government public data"},
    "operational_constraints":READ_ONLY_OPS,
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"no",
        "lock_in_notes":"Public-domain government data."},
    "provenance":prov("https://www.census.gov/data/developers.html",
        "Verified 2026-06: works keyless for low volume (immediately usable); a free API key lifts rate limits but is optional. agent_completable_setup=true."),
  },
  "hud-user-api": {
    "asm_version":"0.3","service_id":"hud/hud-user-api@current","taxonomy":TAX,
    "display_name":"HUD USER API",
    "capabilities":{"description":"US HUD housing data: Fair Market Rents, ZIP crosswalks, CHAS.",
        "functions":["real_estate_data","fair_market_rent","zip_crosswalk","housing_stats"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"api_token",
        "agent_completable_setup":False,"setup_requires":["account_creation","api_key_request"],
        "platforms":["web"],"docs_url":"https://www.huduser.gov/portal/dataset/fmr-api.html"},
    "pricing":{"billing_dimensions":[{"dimension":"request","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["free_tier"],"auth_type":"account","signup_url":"https://www.huduser.gov/hudapi/public/login"},
    "usage_terms":{"automation_allowed":"yes","license":"Free; account + bearer token required"},
    "operational_constraints":READ_ONLY_OPS,
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"no",
        "lock_in_notes":"Public government data; free account required."},
    "provenance":prov("https://www.huduser.gov/portal/dataset/fmr-api.html",
        "Verified 2026-06: free, but requires creating an account and generating a bearer token first -> agent_completable_setup=false (free_api_key_signup)."),
  },
  "attom-property-api": {
    "asm_version":"0.3","service_id":"attom/property-api@current","taxonomy":TAX,
    "display_name":"ATTOM Property Data API",
    "capabilities":{"description":"Commercial property/real-estate data: details, AVM, comps, sales history.",
        "functions":["real_estate_data","property_details","avm","comps","sales_history"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"api_token",
        "agent_completable_setup":False,"setup_requires":["paid_signup","api_key_request"],
        "platforms":["web"],"docs_url":"https://api.developer.attomdata.com/home"},
    "pricing":{"billing_dimensions":[{"dimension":"request","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["free_tier","subscription"],"auth_type":"api_key","signup_url":"https://api.developer.attomdata.com/signup"},
    "usage_terms":{"automation_allowed":"yes","license":"30-day free trial key; production requires a paid plan (pricing via sales)"},
    "operational_constraints":READ_ONLY_OPS,
    "data_governance":{"data_owner":"user","exportable":True,"trains_on_user_data":"unknown"},
    "provenance":prov("https://api.developer.attomdata.com/signup",
        "Verified 2026-06: 30-day free trial API key via signup; production is paid (pricing via sales, not public) -> agent_completable_setup=false (paid_signup). Pricing left at 0 (trial); production price unverified."),
  },
  "reso-web-api": {
    "asm_version":"0.3","service_id":"reso/web-api@current","taxonomy":TAX,
    "display_name":"RESO Web API (MLS-class)",
    "capabilities":{"description":"Standardized MLS listing data via the RESO Web API; access is per-MLS.",
        "functions":["real_estate_data","mls_listings","property_search","listing_data"]},
    "invocation":{"interface":"rest_api","reach":"cloud","agent_operable":True,"auth_to_invoke":"oauth",
        "agent_completable_setup":False,"setup_requires":["mls_membership_approval","licensing_agreement","oauth_consent"],
        "platforms":["web"],"docs_url":"https://www.reso.org/reso-web-api/"},
    "pricing":{"billing_dimensions":[{"dimension":"request","unit":"per_1","cost_per_unit":0,"currency":"USD"}]},
    "payment":{"methods":["account"],"auth_type":"oauth"},
    "usage_terms":{"automation_allowed":"conditional","license":"Per-MLS data-use/licensing agreement; OAuth2 credentials issued by each MLS"},
    "operational_constraints":READ_ONLY_OPS,
    "data_governance":{"data_owner":"shared","exportable":True,"trains_on_user_data":"unknown",
        "lock_in_notes":"Listing data licensed per-MLS; redistribution restricted by MLS rules."},
    "provenance":prov("https://www.reso.org/reso-web-api/",
        "Verified 2026-06: access via each local MLS — requires membership approval + licensing agreement + OAuth2 credentials -> agent_completable_setup=false (heaviest human-in-the-loop). Per-MLS pricing varies."),
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
    print(f"OK {slug:22} agent_completable_setup={inv['agent_completable_setup']!s:5} setup_requires={inv['setup_requires']}")
print(f"\n{ok}/{len(entries)} real-estate entries valid + written")

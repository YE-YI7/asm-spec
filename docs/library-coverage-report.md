# Tool Library Coverage Report

Snapshot: 2026-06-09.

## Summary

The product-facing ASM library now has 30 source-linked tool manifests across 12 taxonomies:

| Taxonomy | Count |
|---|---:|
| `tool.productivity.task_management` | 9 |
| `tool.creative.design` | 7 |
| `tool.booking.travel` | 2 |
| `tool.booking.scheduling` | 1 |
| `tool.communication.email` | 1 |
| `tool.communication.chat` | 1 |
| `tool.development.repository` | 1 |
| `tool.development.issue_tracking` | 1 |
| `tool.research.web` | 1 |
| `tool.research.academic` | 1 |
| `tool.research.reference_manager` | 1 |
| `tool.data.real_estate` | 4 |

This is no longer only a task-manager/design demo. The added domains test the parts of ASM that matter for agents:

- research: source/citation portability
- communication: message-sending approval boundaries
- developer tools: code/workflow mutation
- booking/travel: financial charge, PII, and irreversible booking risk
- real-estate data: the invocability *setup* axis — keyless vs free-signup vs paid vs OAuth/MLS-approval, via the new `invocation.agent_completable_setup` field (added from a production gateway operator's feedback)

## Known Gaps

The library deliberately marks unverified fields instead of filling them with invented values.

| Field | Missing or contains `unknown` | Notes |
|---|---:|---|
| `invocation` | 0 / 26 | Strongest coverage. Every entry says how an agent can or cannot operate the tool. |
| `usage_terms` | 0 / 26 | Every entry has a terms/automation stance. |
| `data_governance` | 9 / 26 | Training-use verified this pass for Figma & Canva (opt-out) and Photoshop (no), on top of the task/research/comms/dev/booking sets. Remaining `unknown`s are per-entry where official terms make no clear statement (e.g. Google Tasks, Photopea). |
| `operational_constraints` | 16 / 26 | New booking/communication/dev/research entries carry it; older task/design entries still need it. |
| `quality` | 8 / 30 | Sourced public ratings added 2026-06-11 (App Store / G2 / Trustpilot, each with benchmark_url) for 10 more tools. The remaining 8 have no solid public rating by design: Any.do (only a 35-review score found), Google Tasks (bundled/unrated), Apple Reminders (system app), Photopea (no store/G2 listing), and the four real-estate APIs — API quality needs domain metrics (coverage, freshness), not store stars. Not faked. |
| `sla` | 19 / 30 | Published SLAs verified 2026-06-09 where they exist: Slack 99.99% (paid Business+/Enterprise), GitHub 99.9% (Enterprise Cloud), Gmail + Google Tasks 99.9% (Google Workspace covered services; paid tiers) — tier scoping recorded per entry. Most consumer tools publish no SLA; absence is recorded, not invented. |

## Next Cleanup Batch

1. Add `operational_constraints` to all 16 pre-existing task/design entries.
2. Replace `data_governance.trains_on_user_data=unknown` where official privacy/product terms make a clear statement. (Done 2026-06-09: Figma, Canva, Photoshop.)
3. Normalize quality metrics:
   - task/design: public app-store rating or documented automation/API coverage
   - research: citation/source portability and corpus coverage
   - communication: send/read API coverage plus rate-limit transparency
   - developer tools: repo/issue/write workflow API coverage
   - booking: search vs order creation completeness, not "best travel service"
4. Add selector output for approval warnings and high-risk actions.

## Product Interpretation

The coverage report should be shown publicly. It makes the project more credible because it distinguishes:

- verified value metadata
- self-reported metadata
- unknown metadata
- policy fields that clients must enforce locally

ASM's claim is not that every value field is already known. The claim is that agents need a place to put, compare, and audit these fields before taking action.

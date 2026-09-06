# ASM execution baseline

Captured: 2026-09-05 (Asia/Shanghai)

## Repository state

- Worktree: `.worktrees/adaptive-selection-v07`
- Branch: `codex/adaptive-selection-v07-20260831`
- Starting commit: `d8974110b74c185b9596df69f7eaf75ee1e5606a`
- Upstream at capture: same commit
- Package version: `0.6.0`
- Python baseline: `.venv/bin/python` 3.12.13
- Test baseline before T1 edits: `243 passed, 1 skipped in 6.98s`
- The macOS system `python3` is 3.9.6 and is outside the package's declared
  `>=3.10` range. It must not be used as the release test interpreter.

The worktree already contained untracked research, validation, and experiment
files. They are preserved. This execution record does not claim they are part
of a release or external adoption.

## Capability boundary

| Capability | State | Evidence and limit |
|---|---|---|
| Manifest validation and deterministic eligibility | stable 0.6 | `schema/asm-v0.3.schema.json`, `src/asm_protocol/selection.py`; caller still supplies taxonomy/functions |
| Workload-aware cost representation | stable 0.6 | `src/asm_protocol/cost.py`; unknown costs remain explicit |
| Legacy Selection Receipt | stable compatibility surface | `selection-receipt-v0.1`; does not represent the newer cost-safe decision path or execution outcome |
| MCP/CLI selection entry points | stable with experimental commands alongside | Existing entry points select from checked-in/library or discovered metadata; no controlled search invocation exists yet |
| Owner preference ledger and Bayesian model | experimental 0.7 | `preferences.py`; no held-out real-owner result supports making it default |
| LinUCB/Thompson selection | experimental 0.7 | `adaptive.py`; not production policy and not independently validated |
| Claim freshness and invocation identity | experimental 0.7 | `freshness.py`; field evidence convention exists, live refresh loop does not |
| MCP registry discovery | experimental 0.7 | discovery metadata is not selection-ready evidence |
| Web-search request/evidence/decision/outcome contracts | T1 draft | Schemas and replay fixtures added after this baseline; no live adapters yet |
| Three-provider search adapters and automatic invocation | planned T2-T4 | No provider credentials or paid calls were used |
| Public service cards and independent outcome evidence | planned T6-T7 | Existing manifests and self-authored fixtures do not establish adoption |
| Assurance, liability, settlement, or certification | out of scope | No legal, underwriting, or commercial validation exists |

## Data status

The deterministic 2026-08-16 audit reports 105 schema-valid local records:

- `manifests/`: 75/75 valid and expired; fixture/benchmark use only.
- `library/`: 30/30 valid and stale; exclude from current-fact claims.

This is a data-validity result, not proof that the provider facts remain true.
The 2026-08-31 Linear/Product Hunt sample is untracked research and supports
only a metadata-completeness hypothesis.

## T0 decision

Build the new search product as a versioned application layer. Keep stable
manifest behavior and legacy receipts intact. Treat adaptive selection as a
research candidate until the evaluation gates in the execution PRD are met.

## Local implementation progress through 2026-09-06

This section records local implementation only; it is not deployment, live
provider evidence, external adoption, or commercial validation.

| Task | Local state | Remaining boundary |
|---|---|---|
| T1 contracts | implemented and shared by CLI/MCP/HTTP | draft versions are not a published standard |
| T2 adapters | Tavily, Exa and Firecrawl request/response replay paths implemented | no authenticated provider measurement |
| T3 bootstrap | explicit/default/single-candidate choice, JCS commitments, policy/evidence/budget gates implemented | no learned owner policy claim |
| T4 entry | CLI and MCP replay, safe one-call transport boundary, private run storage implemented | live account run remains unverified |
| T5 closure | successor decision, authorized fallback, attempt/deadline/budget/version checks, failure states and owner-scoped two-worker fixture implemented | cross-organization identity remains out of scope |
| T6 public surface | three source-labeled cards, method page, noindex replay page and opt-in local activation events implemented | cards correctly show live quality evidence as insufficient |
| T7 evaluation | primary quality objective selected before results; 60 SimpleQA rows are content-committed with a proportional 10-family held-out split; source/task/result/time-window binding, exact McNemar, seeded task-family cluster bootstrap, and a local-only consented external-task intake are implemented | no real external contribution has been received; snapshot still lacks Chinese/time-sensitive coverage; dated FreshQA answers require current re-verification; judge model/version, accounts, budget and external trials remain absent |

Latest local verification at this point: `372 passed, 1 skipped`; targeted Ruff
and JSON parsing passed. Re-run after packaging changes before any review or push.

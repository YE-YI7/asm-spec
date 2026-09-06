# A2A and Multi-Agent validation v0.1

**Date:** 2026-08-31
**Result:** 7/7 synthetic mechanism checks passed
**Claim boundary:** no real-agent quality, demand, security, or adoption claim

The evidence weights, minimum sample size, and per-evaluator cap in this fixture
are test controls, not a proposed production algorithm. They require empirical
calibration against real tasks and attacks.

## What was tested

| Case | Question | Result |
|---|---|---|
| Cross-organization A2A choice | Can observed evidence break a declared-fact tie correctly? | `peer-a` baseline changed to expected `peer-b` |
| Version binding | Can old reputation be prevented from laundering a new configuration? | naive `legacy-a` history was 0.9167; exact-version selection chose `current-b` |
| Review inflation | Can 20 weak reviews from one evaluator beat diverse verified evidence? | no; `trusted-b` remained selected |
| Failure replacement | Can the evidence summary select the better fallback after primary failure? | selected expected `fallback-b` |
| Cross-agent learning | Can one worker's objective failure alter a later worker's selection? | selection changed from `shared-a` to `shared-b` |
| Owner-policy consistency | Does a private hard constraint remain above public quality evidence? | quality default chose cloud; privacy policy chose local |
| Redaction | Does the event omit raw prompt and artifact content? | raw strings absent; only digests retained |

## What this validates

- A2A-shaped tasks can be projected into a compact, redacted evidence event.
- Task-conditioned, version-bound evidence can affect selection.
- The same evidence contract supports A2A discovery and Multi-Agent runtime
  learning/fallback without becoming an orchestrator.
- Owner policy remains a private eligibility gate rather than a public score.

## What remains unvalidated

1. real A2A SDK compatibility and signature/canonicalization interoperability;
2. whether objective checks exist for useful real tasks;
3. whether producers expose attempts, including failures, rather than cherry-pick;
4. whether task cohorts are comparable at useful sample sizes;
5. privacy review against realistic traces, prompts, and artifacts;
6. coordinated multi-identity attacks beyond one-evaluator influence caps;
7. external producer/caller willingness to generate or consume the event.
8. calibration of evidence weights, sample thresholds, confidence method, and
   evaluator influence limits.

## Next validation gates

| Gate | Minimum acceptance |
|---|---|
| SDK feasibility | one normal A2A Python SDK task produces the event without modifying A2A core types |
| Real outcome | two agents perform the same objectively checkable task at least five times each |
| Multi-Agent reuse | a second worker consumes the first worker's event and avoids one reproduced failure |
| Negative evidence | provider can inspect, dispute, or counter one failed outcome without deleting it |
| External review | one producer and two independent callers review or run the event contract |

Run:

```bash
python3 experiments/a2a_experience_validation.py
```

Repository regression check (Python 3.12 with MCP test extra): **243 passed,
1 skipped**.

The next SDK gate is now complete on deterministic local agents. See
`docs/validation/a2a-sdk-live-validation-v0.1.md`. External endpoints, independent
callers, open-ended tasks, and dispute handling remain unvalidated.

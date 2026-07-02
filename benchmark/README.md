# ToolSelect-Bench

**Question:** when an agent must choose among substitutable real-world tools
(task apps, design tools, booking APIs, data sources), how often does it
violate the user's hard constraints or overpay — and does machine-readable
value metadata (ASM manifests) close the gap?

This directly tests the premise of the ASM protocol. It is designed to be
**falsifiable**: if subjects choose well from names and descriptions alone,
the premise that agents need a value/selection metadata layer is weakened —
and we will report that.

## Design

50 tasks over the [30-tool ASM library](../library/), 5 domains
(productivity, creative, booking, research, real-estate data). Three task
types, each with **logic-provable ground truth** derived from manifest facts
at generation time — never from our own ranker, so the benchmark cannot be
circular:

| type | correct answer is provable because | n |
|---|---|---|
| `unique_eligible` | exactly one candidate passes the stated hard constraints (reach / platform / functions / ToS / setup); every alternative fails a *named* gate | 21 |
| `cheapest_eligible` | the task states "minimize monthly cost"; the min-cost group among eligible tools is arithmetic over pricing facts (ties all count correct) | 18 |
| `governance` | a non-negotiable data-governance requirement (must not train on user data / must be exportable) excludes a provable subset; correct = cheapest compliant tool | 11 |

Governance compliance is **strict**: `trains_on_user_data: "unknown"` cannot
satisfy a non-negotiable requirement. (That "unknown" is itself the point —
today this metadata is not published in machine-readable form anywhere.)

### Conditions

- **`names_only`** — candidate names + one-line descriptions. Approximates an
  agent choosing today, without value metadata.
- **`asm`** — the candidates' ASM manifests (invocation, pricing, usage terms,
  governance, operational constraints).
- *(planned, v1)* **`raw_pages`** — real pricing/marketing page text, to
  separate "information missing" from "information unstructured".

### Metrics (pre-registered)

1. **correct rate** — pick ∈ ground-truth correct set
2. **violation rate** — pick breaches a nameable constraint (`violations_if`)
3. **mean overspend** — picked cost − min eligible cost, USD/month (cost-typed tasks)

### Reference floor

`random` subject (seeded): **24% correct, 56% violation, $6.45/mo overspend** —
identical across conditions by construction.

## Honesty rules

- Metrics and task types are pre-registered in this file before any LLM run;
  results are reported for **all** runs, including ones unfavorable to ASM.
- `library_select` (our ranker) is **not** a subject or an oracle.
- The full dataset (`tasks.jsonl`) including ground truth, violations, and
  costs is open; every subject's raw picks are saved under `results/` so all
  scores are independently re-checkable.
- Known limits: 30 tools and 50 templated tasks is small; prompts are
  template-generated (v1: human paraphrases); manifests were researched and
  written by the ASM authors (sources cited per entry in `library/`).

## Run it

```bash
python benchmark/generate_tasks.py                  # rebuild tasks.jsonl (deterministic)
python benchmark/harness.py --subject random        # floor
OPENROUTER_API_KEY=... python benchmark/harness.py --subject llm:openai/gpt-4o-mini
```

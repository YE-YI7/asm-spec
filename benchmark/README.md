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

50 tasks using 26 candidates from the [30-tool ASM library](../library/), 5 domains
(productivity, creative, booking, research, real-estate data). Three task
types, each with deterministic ground truth produced by applying the stated
eligibility and cost rules to manifest facts at generation time. The ranker's
scores are not used, but the facts and their semantics are author-maintained;
this benchmark therefore does **not** independently validate that a manifest's
claims are true:

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
- **`raw_pages`** — versioned text snapshots of official provider pages. This
  condition is admitted only when every task-relevant manifest fact for every
  candidate has a cited page, content hash, retrieval timestamp, and reviewed
  fact-path mapping. No complete v1 bundle has been published yet.

### Metrics (pre-registered)

1. **correct rate** — pick ∈ ground-truth correct set
2. **violation rate** — pick breaches a nameable constraint (`violations_if`)
3. **mean overspend** — picked cost − min eligible cost, USD/month (cost-typed tasks)

Inference is paired at the task level. We report an exact two-sided McNemar
test and task-bootstrap interval for each model. A task-clustered bootstrap
summarizes the fixed six-model panel without treating the models as six
independent replications. Per-model p-values and intervals are unadjusted for
multiple comparisons and should be read as descriptive follow-up evidence.

### Reference floor

`random` subject (seeded): **24% correct, 56% violation, $6.45/mo overspend** —
identical across conditions by construction.

## Honesty rules

- Metrics and task types are pre-registered in this file before any LLM run;
  results are reported for **all** runs, including ones unfavorable to ASM.
- `library_select` (our ranker) is **not** a subject. Its deterministic
  eligibility and cost semantics are used when generating ground truth; that
  coupling is disclosed and tested separately from model behavior.
- The full dataset (`tasks.jsonl`) including ground truth, violations, and
  costs is open; every subject's parsed picks are saved under `results/` so all
  scores are independently re-checkable. Legacy v0 result files do not contain
  the original response text; future runs save both raw responses and a task-file
  digest.
- Known limits: 30 tools and 50 templated tasks is small; prompts are
  template-generated. The v1 generator can vary surface forms, but that is not
  a substitute for human-authored natural tasks. Manifests were researched and
  written by the ASM authors (sources cited per entry in `library/`).
- Provider text may be mutable or copyrighted. Raw-page snapshot bundles are
  research artifacts: use only official sources, preserve hashes and retrieval
  times, and do not commit text without permission or a compatible license.

## Run it

```bash
python benchmark/generate_tasks.py                  # rebuild from the current library (stable order)
python benchmark/harness.py --subject random        # floor
OPENROUTER_API_KEY=... python benchmark/harness.py --subject llm:openai/gpt-4o-mini

# Build a separate v1 dataset; fail closed unless raw-page evidence is complete.
python benchmark/build_raw_pages_template.py \
  --output /path/to/raw-pages-review.json
# A reviewer now fills pages[], verifies each fact-path mapping, and hashes text.
python benchmark/generate_tasks.py --prompt-style varied \
  --raw-page-bundle /path/to/reviewed-snapshots.json \
  --output benchmark/tasks-v1.jsonl
python benchmark/harness.py --tasks benchmark/tasks-v1.jsonl \
  --results-dir benchmark/results-v1 --subject llm:<model-id>
python benchmark/aggregate.py --tasks benchmark/tasks-v1.jsonl \
  --results-dir benchmark/results-v1 --left raw_pages --right asm
```

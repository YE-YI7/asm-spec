# ToolSelect-Bench — Results (v0)

**Question.** When an agent must choose among substitutable real-world tools,
does giving it machine-readable value/selection metadata (ASM manifests) change
how well it chooses — versus seeing only tool names + one-line descriptions?

**Setup.** 50 tasks using 26 candidates from the 30-tool library, 5 domains, 3 task types with
deterministic ground truth over author-maintained manifest facts (see
[README](README.md)). Each task run under two
conditions — `names_only` and `asm` — against 6 models via an OpenAI-compatible
endpoint (AIML API), temperature 0. Ground truth is derived from manifest facts,
not ranker scores. There was 1 unparsed response across 600 model-task calls.

## Headline

Descriptively, ASM metadata improved correct tool selection in **6/6** models
(panel mean **+17 points**) and reduced constraint violations in **5/6**
(panel mean **−12 points**). These are six measurements on the **same** 50
tasks, not six independent replications. A task-clustered bootstrap for this
fixed model panel gives **+8.0 to +25.3 points** for correct selection and
**−20.3 to −3.3 points** for violations (95% intervals).

| Model | correct: names→asm | violations: names→asm |
|---|---|---|
| **OpenAI GPT-5-chat** | 64% → **92%** | 36% → **8%** |
| **Llama-3.3-70B** | 66% → **90%** | 34% → **10%** |
| OpenAI GPT-4.1-mini | 60% → 72% | 34% → 28% |
| DeepSeek-chat | 62% → 68% | 28% → 32% |
| Gemini-2.5-flash-lite | 48% → 68% | 40% → 32% |
| Qwen-max | 54% → 66% | 44% → 34% |
| *random floor* | 24% → 24% | 56% → 56% |

### Paired inference by model

Exact two-sided McNemar tests compare each model's task-level outcomes. Only
GPT-5 and Llama clear p < .05 for both metrics; Gemini's correct-selection
result is borderline under the exact test. Bootstrap intervals resample tasks.
These per-model p-values and intervals are unadjusted for multiple comparisons.

| Model | correct delta (95% task-bootstrap CI; McNemar p) | violation delta (95% CI; p) |
|---|---|---|
| GPT-5-chat | +28pp (+14, +42); .0005 | −28pp (−42, −14); .0005 |
| Llama-3.3-70B | +24pp (+10, +38); .0042 | −24pp (−38, −10); .0042 |
| Gemini-2.5-flash-lite | +20pp (+2, +38); .0525 | −8pp (−24, +8); .4545 |
| GPT-4.1-mini | +12pp (−4, +28); .2101 | −6pp (−20, +8); .5811 |
| Qwen-max | +12pp (−2, +26); .1460 | −10pp (−22, +2); .2266 |
| DeepSeek-chat | +6pp (−12, +24); .6636 | +4pp (−12, +20); .8036 |

## What the effect is — and isn't (honest read)

- **Strongest, cleanest win: eligibility.** On `unique_eligible` tasks (reach /
  platform / functions / ToS — facts invisible in a name but explicit in a
  manifest) every model improved, e.g. Llama 71%→90% correct. This is ASM's
  clearest contribution: making *machine-checkable* what agents otherwise guess.
- **Price & governance are noisier.** On isolated `cheapest_eligible` and
  `governance` slices the effect is smaller and occasionally negative for weaker
  models (GPT-4.1-mini governance 73%→64%; DeepSeek/Qwen cheapest regressed).
  The frontier models still gained sharply here (GPT-5-chat cheapest 50%→100%,
  governance 64%→82%). Reading structured pricing / `trains_on_user_data`
  correctly appears to be a *capability* threshold.
- **Interpretation.** Some capable models exploited the structured metadata
  strongly. This run was not designed to estimate a capability-by-treatment
  interaction, so the apparent ordering is a hypothesis, not a conclusion.

## Caveats (do not oversell)

1. **No raw-page control.** The result supports “structured manifest data helps
   relative to names and descriptions.” It does **not** yet establish that ASM's
   specific format beats giving the model the same facts in official page text,
   or that ASM is uniquely the missing layer.
2. **n = 50 templated tasks.** Prompts are template-generated; per-type slices
   are n=11–21, and sentence patterns may be learnable. Multiple deterministic
   surface forms help only partially; human-authored or logged natural tasks are
   still needed for transportability.
3. **Cost ground truth** uses our `monthly_cost` normalization; a model reading
   raw billing dimensions may reasonably compute "cheapest" differently.
4. **Fact validity is outside this test.** Ground truth reuses the project's
   eligibility/cost semantics over author-researched manifests. A separately
   reviewed source-to-fact audit is required to test whether those facts are
   current and correct.
5. Single endpoint (AIML API), single run per cell (temperature 0). Per-model
   paired intervals and exact tests are reported above; model-to-model
   generalization is not estimated.
6. Brand priors are uncontrolled. We do not assume whether that biases the ASM
   effect upward or downward without a long-tail or anonymized-candidate study.

## Reproduce

```bash
python benchmark/generate_tasks.py
ASM_BENCH_BASE_URL=<openai-compatible-url> ASM_BENCH_API_KEY=<key> \
  python benchmark/harness.py --subject llm:<model-id>
python benchmark/aggregate.py
```

Parsed per-run picks + metrics are in `benchmark/results/` for independent
re-scoring. Legacy v0 files do not preserve complete raw response text.

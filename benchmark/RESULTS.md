# ToolSelect-Bench — Results (v0)

**Question.** When an agent must choose among substitutable real-world tools,
does giving it machine-readable value/selection metadata (ASM manifests) change
how well it chooses — versus seeing only tool names + one-line descriptions?

**Setup.** 50 tasks over the 30-tool library, 5 domains, 3 task types with
logic-provable ground truth (see [README](README.md)). Each task run under two
conditions — `names_only` and `asm` — against 6 models via an OpenAI-compatible
endpoint (AIML API), temperature 0. Ground truth is derived from manifest facts,
never from our own ranker. Unparsed responses: 1 across all 26 runs.

## Headline

Across **6/6** models, ASM metadata **improved** correct tool selection
(avg **+17 points**); constraint violations **fell in 5/6** (avg **−12 points**).
The two most capable models gained most.

| Model | correct: names→asm | violations: names→asm |
|---|---|---|
| **OpenAI GPT-5-chat** | 64% → **92%** | 36% → **8%** |
| **Llama-3.3-70B** | 66% → **90%** | 34% → **10%** |
| OpenAI GPT-4.1-mini | 60% → 72% | 34% → 28% |
| DeepSeek-chat | 62% → 68% | 28% → 32% |
| Gemini-2.5-flash-lite | 48% → 68% | 40% → 32% |
| Qwen-max | 54% → 66% | 44% → 34% |
| *random floor* | 24% → 24% | 56% → 56% |

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
- **Interpretation.** The more capable the model, the more it exploits
  structured metadata — consistent with metadata being a lever, not a crutch.

## Caveats (do not oversell)

1. **Priors confound.** The library skews to well-known tools (Todoist, Notion),
   so a model's brand knowledge substitutes for metadata and *understates* the
   value on long-tail/obscure tools where priors don't exist. A long-tail
   follow-up would likely show a larger gap — this run is conservative.
2. **n = 50 templated tasks.** Prompts are template-generated; per-type slices
   are n=11–21, so single-model per-slice numbers are noisy. The 6-model overall
   trend is the robust signal.
3. **Cost ground truth** uses our `monthly_cost` normalization; a model reading
   raw billing dimensions may reasonably compute "cheapest" differently.
4. Single endpoint (AIML API), single run per cell (temperature 0). No CIs.

## Reproduce

```bash
python benchmark/generate_tasks.py
ASM_BENCH_BASE_URL=<openai-compatible-url> ASM_BENCH_API_KEY=<key> \
  python benchmark/harness.py --subject llm:<model-id>
python benchmark/aggregate.py
```

Raw per-run picks + metrics are in `benchmark/results/` for independent re-scoring.

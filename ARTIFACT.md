# ASM — Artifact Description

This document maps every empirical claim in `paper/asm-paper-draft.md` to the script that produces it and the file the result is written to. Reviewers should be able to reproduce every table and number in the paper from a clean checkout in a single run.

## TL;DR — one-shot reproduction

```bash
git clone https://github.com/YE-YI7/asm-spec.git && cd asm-spec
docker build -f Dockerfile.artifact -t asm-artifact .
docker run --rm -v "$PWD/experiments/results:/app/experiments/results" asm-artifact make reproduce
```

The repository ships two Docker images: `Dockerfile` (production registry + payment services) and `Dockerfile.artifact` (this one — Python + Node + every experiment). Use `-f Dockerfile.artifact` for reproduction.

Or without Docker (Python 3.10+):

```bash
pip install -r requirements.txt
make reproduce
```

`make reproduce` runs every experiment that does not require external API calls or paid services. Live-API and external-LLM evaluations are gated behind separate targets that require API keys.

Developer-facing adoption checks are separate from paper reproduction:

```bash
pip install -e .
asm score "cheap reliable TTS under 1s"
make validate-mcp-examples
```

## Environment

- **Python**: 3.10 or newer (tested on 3.13 Windows + 3.11 Linux Docker).
- **Node.js**: 18 or newer (only required for `make test-ts`).
- **Disk**: ~50 MB for cached raw HTML used by §6.7. ~13 MB for MCPCorpus dataset.
- **Network**: required at first run to fetch HTML caches (§6.7) and MCPCorpus (§6.0a). Cached afterward.
- **No GPU required.** All experiments are CPU-only.

## Claim-to-artifact map

Each row links a paper claim → the command → the output file. "Output file" is the canonical location after `make reproduce`. Numbers in the paper are pulled from the `*.json` summaries.

### §6.0 — 50-repo GitHub audit

| Claim | Command | Output |
|---|---|---|
| 0/50 GitHub repositories expose ASM-style structured value metadata | `make audit` | `experiments/results/mcp_ecosystem_audit.{csv,json,md}` |
| 0/50 expose all four core value classes simultaneously | same | same |

### §6.0a — Registry-level audit (n=600+ across five sources)

| Claim | Command | Output |
|---|---|---|
| 0/N entries across MCP Registry + Glama + MCP Atlas + MCPCorpus + FindMCP expose pricing+SLA+quality+payment | `make value-audit` | `experiments/results/mcp_value_metadata_audit.{csv,json,md}` |

The `--mcpcorpus-limit` flag controls sample size; `make value-audit` defaults to 600. For the headline n=14,519 number, run:
```bash
python experiments/mcp_value_metadata_audit.py \
  --mcpcorpus-limit 14000 --official-limit 300 --glama-limit 300 --atlas-limit 100 --sample-size 15000 --seed 2026
```
Or via Make: `make value-audit-full`.

### §6.1 — Pricing heterogeneity over 75 manifests

| Claim | Source |
|---|---|
| 75 manifests across 47 taxonomies, 8 distinct billing models | `manifests/*.asm.json` (`grep '"taxonomy"' manifests/*.asm.json \| awk '{print $NF}' \| sort -u`) |

### §6.2 — Scoring across preference profiles

| Claim | Command | Output |
|---|---|---|
| Same candidate set -> different optimal selection under different profiles | embedded in `make eval` | `experiments/results/ab_test_results.csv` |

### §6.3 — Trust delta + §6.3a — Component ablations

| Claim | Command | Output |
|---|---|---|
| Removing trust delta: tau = 0.94, top-1 agreement 97.0% | `make ablations` | `experiments/results/ablation_trust.{csv,json,md}` |
| TOPSIS vs weighted average: tau 0.63, top-1 disagreement 23.0% | same | `experiments/results/ablation_aggregator.{csv,json,md}` |
| io_ratio sensitivity: stable across [0.1, 1.0] | same | `experiments/results/ablation_io_ratio.{csv,json,md,_pairwise.csv}` |

### §6.4 — Protocol overhead

Numerical claims are drawn from the same `make eval` run:
- Token cost per manifest: ~300
- Scoring overhead: < 5 ms per task

These are reported in `experiments/results/ab_test_analysis.json` under `selectors.asm.scoring_ms_mean`.

### §6.5 — A/B comparison vs random + most-expensive

| Claim | Command | Output |
|---|---|---|
| 23.1% utility gain vs random ($p < 10^{-6}$) | `make eval` | `experiments/results/ab_test_analysis.json` |
| 59.2% cost reduction vs most-expensive ($p < 10^{-6}$) | same | same |

### §6.5b — Live-API execution (30 tasks, Chinese-LLM gateway)

| Claim | Command | Output |
|---|---|---|
| Naive 5-candidate run exposes MiniMax/MMLU quality-normalisation failure | shipped result snapshot | `experiments/live_execution/results_naive_5candidate/live_summary.json` |
| Same-benchmark 4-candidate run restores ASM-TOPSIS to 9.27 judge mean at $0.0064 execution cost | `python experiments/live_execution/compare_runs.py` | `experiments/live_execution/results/comparison.{csv,md}` |

The underlying live calls require TokenDance gateway credentials and are not part of `make reproduce`. The checked-in `results/` and `results_naive_5candidate/` directories preserve the paper runs.

### §6.6 — Selection regret (200 tasks, 7 baselines)

| Claim | Command | Output |
|---|---|---|
| ASM-TOPSIS zero-regret by construction | `python experiments/selection_baselines.py` | `experiments/results/selection_baselines.{csv,json,md}` |
| Weighted average leaves 0.0720 mean regret | same | same |

### §6.6a — Preference alignment (20 NL requests)

| Claim | Command | Output |
|---|---|---|
| ASM 100% zero-regret on 20 NL user requests | `make preference-alignment` | `experiments/results/preference_alignment.{csv,json,md}` |
| Weighted-avg 95%, single-axis 35-75% | same | same |

### §6.7 — LLM-as-selector across 3 LLMs (36 tasks)

| Claim | Command | Output |
|---|---|---|
| Manifest surface -> 100% top-1 across all three LLMs | `make llm-eval-live` (per LLM) | `experiments/expert_annotation/results_objective*/` |
| Raw-doc surface -> 63.9-72.2% top-1 | same | same |
| Quality-axis profile sensitivity (5/5 with pure-quality vs 0/5 with quality-leaning) | reproduced by switching `AXIS_TO_PREFS` weights in `run_ranking_experiment.py` | – |

`make llm-eval-live` requires API credentials. The headline run used the TokenDance gateway with three models; provider/model/base-url are env-configurable:

```bash
DEEPSEEK_API_KEY=sk-... \
LLM_PROVIDER=deepseek-v4-flash LLM_MODEL=deepseek-v4-flash \
LLM_BASE_URL=https://tokendance.space/gateway/v1 LLM_API_KEY_ENV=DEEPSEEK_API_KEY \
make llm-eval-live
```

The LLM dry-run (`make llm-eval`) generates prompts and runs only `asm_topsis` deterministically — useful for reviewers without API credentials.

### §6.8 — External preference correlation (LM Arena Elo)

| Claim | Command | Output |
|---|---|---|
| Pooled heterogeneous quality metrics are uninformative (rho = -0.2143) | `python experiments/external_validation/correlate_arena_elo.py --elo-pkl path/to/arena_elo.pkl` | `experiments/results/external_validation/arena_elo_correlation.{csv,json,md}` |
| Within-metric LMSYS_Elo subset aligns with Arena Elo (n=3, rho = 1.0) | same | same |
| OpenRouter usage correlation is weak, as expected for a usage signal | `python experiments/external_validation/correlate_openrouter.py` | `experiments/results/external_validation/openrouter_correlation.{csv,json,md}` |

The Arena pickle is not committed because it is an external LM Arena artifact. Reviewers can alternatively pass `--arena-csv model,elo,battles,rank` with the same mapped model names documented in the output JSON.

## Adoption artifact checks

| Claim | Command | Output |
|---|---|---|
| MCP `server.json` can carry valid ASM metadata under publisher-provided `_meta` | `make validate-mcp-examples` | validator pass/fail output |
| Embedded ASM can be extracted to a standalone manifest | `asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json --write-out /tmp/remote-search.asm.json` | extracted `.asm.json` |
| The README 60-second scoring demo runs from an editable install | `asm score "cheap reliable TTS under 1s"` | ranked + rejected services |

## File layout

```
asm-spec/
├── manifests/                              # 75 ASM manifests (JSON)
├── schema/asm-v0.3.schema.json             # protocol spec
├── scorer/                                 # Python TOPSIS engine + tests
├── registry/                               # TypeScript MCP server + tests
examples/mcp-server-json/             # MCP Registry server.json examples with ASM _meta
docs/integrations/                    # MCP Registry and aggregator adoption docs
├── experiments/
│   ├── ab_test.py                          # §6.5
│   ├── analyze.py                          # §6.5 stats
│   ├── ablation_experiments.py             # §6.3a
│   ├── selection_baselines.py              # §6.6
│   ├── preference_alignment.py             # §6.6a
│   ├── preference_alignment_tasks.json     # 20 NL requests
│   ├── mcp_ecosystem_audit.py              # §6.0
│   ├── mcp_value_metadata_audit.py         # §6.0a
│   ├── live_execution/                     # §6.5b live API execution snapshots
│   ├── external_validation/                # §6.8 Arena Elo correlation
│   └── expert_annotation/
│       ├── run_ranking_experiment.py       # §6.7 runner
│       ├── tasks_objective.yaml            # 36 single-axis tasks
│       ├── generate_objective_tasks.py     # task auto-generator
│       └── results_objective*/             # per-LLM results (DeepSeek/Qwen/Kimi)
├── paper/asm-paper-draft.md                # the paper
├── ARTIFACT.md                             # this file
├── CONTRIBUTING.md                         # contribution + per-experiment usage
├── Makefile                                # one-shot targets
├── Dockerfile                              # reproducible env
├── requirements.txt                        # pinned deps
└── README.md
```

## What `make reproduce` does (full target list)

```bash
make audit                # §6.0 GitHub audit (n=50)
make value-audit          # §6.0a registry audit (default n=600; pass --mcpcorpus-limit for full)
make eval                 # §6.5 A/B
make ablations            # §6.3a component ablations
make preference-alignment # §6.6a NL request alignment
make llm-eval             # §6.7 dry-run (no API)
```

The `make llm-eval-live` target is **not** included in `make reproduce` — it requires API credentials and costs ~¥0.5–10 per LLM. To reproduce §6.7 numbers exactly, run it separately for DeepSeek-V4-flash, Qwen3-Max, and Kimi K2.5 with the appropriate `LLM_*` env vars.

## Long-term archival

A snapshot of the repository at the paper's submission commit will be deposited at Zenodo with a citable DOI. Until then, cite the GitHub commit SHA from `paper/asm-paper-draft.md`.

## Notes on non-reproducible elements

- **HTML cache for §6.7 raw-doc surface.** The first run of `make llm-eval-live --raw-doc` fetches and caches public provider pages at `experiments/expert_annotation/cache/raw_docs/`. Provider HTML changes over time, so a fresh fetch is not byte-identical to the snapshot used in the paper. The cached snapshot used for the paper's 72.2 / 63.9 / 69.4% numbers is **shipped in the repo** for exact reproduction; subsequent runs reuse it unless you delete the cache directory.
- **LLM determinism.** Calls use `temperature=0`. With `temperature=0` and a fixed model, providers should return deterministic outputs, but provider-side updates can change behaviour. The exact responses used in the paper are at `experiments/expert_annotation/results_objective*/ranking_results.csv`.

## Troubleshooting

- `pytest: command not found` → `pip install -r requirements.txt`.
- `make: command not found` (Windows) → use Git Bash or run the underlying commands directly (each Make target is one Python invocation).
- `urlopen` timeouts on first run → ensure the machine has internet access; rerun with the same seed.
- Encoding errors on Windows: `set PYTHONIOENCODING=utf-8` before running.

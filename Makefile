.PHONY: test test-py test-ts validate-mcp-examples data-quality-audit eval ablations selection-baselines preference-alignment adaptive-replay llm-eval llm-eval-live audit value-audit value-audit-full paper-tables reproduce refresh-elo clean clean-cache help

LLM_PROVIDER ?= deepseek
LLM_MODEL ?= deepseek-chat
LLM_BASE_URL ?= https://api.deepseek.com
LLM_API_KEY_ENV ?= DEEPSEEK_API_KEY
PYTHON ?= python3

help:
	@echo "ASM Build & Experiment Targets"
	@echo ""
	@echo "  make test          Run all tests (Python + TypeScript)"
	@echo "  make test-py       Run Python scorer tests only"
	@echo "  make test-ts       Run TypeScript MCP server tests only"
	@echo "  make validate-mcp-examples  Validate ASM metadata embedded in MCP server.json examples"
	@echo "  make data-quality-audit  Audit checked-in manifest freshness, schema, and provenance"
	@echo "  make eval          Run A/B evaluation (Section 6.5)"
	@echo "  make ablations     Run ablation studies (Section 6.3a)"
	@echo "  make selection-baselines  Run 7-policy regret analysis (Section 6.6)"
	@echo "  make preference-alignment  Run natural-language preference evaluation (Section 6.6a)"
	@echo "  make adaptive-replay  Run stationary and preference-drift mechanism tests"
	@echo "  make llm-eval      LLM-as-selector dry-run (no API calls)"
	@echo "  make llm-eval-live LLM-as-selector with live LLM (override LLM_PROVIDER/LLM_MODEL/LLM_BASE_URL/LLM_API_KEY_ENV)"
	@echo "  make audit         Run MCP ecosystem audit (Section 2)"
	@echo "  make value-audit   Run expanded MCP registry/directory value metadata audit (n=600)"
	@echo "  make value-audit-full  Same audit on full MCPCorpus (~14K entries; first run downloads ~13MB)"
	@echo "  make paper-tables  Generate paper tables from experiment results"
	@echo "  make reproduce     Run every offline experiment in one command (Section 6 audit/eval/ablations/alignment + LLM dry-run)"
	@echo "  make refresh-elo   Refresh the LMArena Elo snapshot (OpenRouter value router quality axis)"
	@echo "  make clean         Remove cache artifacts"
	@echo "  make clean-cache   Remove raw-doc cache (large)"
	@echo ""

# ---------------------------------------------------------------------------
# Test targets
# ---------------------------------------------------------------------------

test: test-py test-ts
	@echo "[OK] All tests passed."

test-py:
	$(PYTHON) -m pytest -v

test-ts:
	cd registry && npm test

validate-mcp-examples:
	$(PYTHON) mcp_server_json_asm.py examples/mcp-server-json/basic-with-asm.server.json

data-quality-audit:
	@$(PYTHON) tools/audit_manifest_data.py

refresh-elo:
	$(PYTHON) tools/refresh_arena_elo.py
	$(PYTHON) mcp_server_json_asm.py examples/mcp-server-json/remote-with-asm.server.json
	$(PYTHON) mcp_server_json_asm.py examples/mcp-server-json/package-with-asm.server.json

# ---------------------------------------------------------------------------
# Experiment targets
# ---------------------------------------------------------------------------

eval:
	$(PYTHON) experiments/ab_test.py
	$(PYTHON) experiments/analyze.py

ablations:
	$(PYTHON) experiments/ablation_experiments.py --seed 2024

selection-baselines:
	$(PYTHON) experiments/selection_baselines.py

preference-alignment:
	$(PYTHON) experiments/preference_alignment.py --seed 2024

adaptive-replay:
	$(PYTHON) experiments/adaptive_selection_replay.py --seed 20260831 --rounds 300 --holdout 100
	$(PYTHON) experiments/adaptive_selection_replay.py --seed 20260831 --rounds 300 --holdout 100 --preference-drift --reward-noise 0.05

llm-eval:
	$(PYTHON) experiments/expert_annotation/run_ranking_experiment.py \
	  --tasks-file experiments/expert_annotation/tasks_objective.yaml \
	  --dry-run

llm-eval-live:
	@if [ -z "$${$(LLM_API_KEY_ENV)}" ]; then \
		echo "Error: set $(LLM_API_KEY_ENV), or override LLM_API_KEY_ENV=<ENV_NAME>"; \
		exit 1; \
	fi
	$(PYTHON) experiments/expert_annotation/run_ranking_experiment.py \
	  --tasks-file experiments/expert_annotation/tasks_objective.yaml \
	  --provider $(LLM_PROVIDER) \
	  --model $(LLM_MODEL) \
	  --base-url $(LLM_BASE_URL) \
	  --api-key-env $(LLM_API_KEY_ENV)

audit:
	$(PYTHON) experiments/mcp_ecosystem_audit.py

value-audit:
	$(PYTHON) experiments/mcp_value_metadata_audit.py --sample-size 600 --seed 2026

value-audit-full:
	$(PYTHON) experiments/mcp_value_metadata_audit.py \
	  --sample-size 15000 \
	  --mcpcorpus-limit 14000 \
	  --official-limit 300 \
	  --glama-limit 300 \
	  --atlas-limit 100 \
	  --seed 2026

paper-tables:
	$(PYTHON) experiments/generate_paper_tables.py

reproduce:
	@echo "==> [1/7] §6.0  GitHub repository audit (n=50)"
	$(PYTHON) experiments/mcp_ecosystem_audit.py
	@echo "==> [2/7] §6.0a Registry-level value-metadata audit (n=600)"
	$(PYTHON) experiments/mcp_value_metadata_audit.py --sample-size 600 --seed 2026
	@echo "==> [3/7] §6.5  Controlled A/B vs random/most-expensive"
	$(PYTHON) experiments/ab_test.py
	$(PYTHON) experiments/analyze.py
	@echo "==> [4/7] §6.3a Component ablations (trust delta, TOPSIS vs WA, io_ratio)"
	$(PYTHON) experiments/ablation_experiments.py --seed 2024
	@echo "==> [5/7] §6.6 Selection regret over 200 tasks"
	$(PYTHON) experiments/selection_baselines.py
	@echo "==> [6/7] §6.6a Preference alignment over 20 NL requests"
	$(PYTHON) experiments/preference_alignment.py --seed 2024
	@echo "==> [7/7] §6.7  LLM-as-selector dry-run (deterministic; no API)"
	$(PYTHON) experiments/expert_annotation/run_ranking_experiment.py \
	  --tasks-file experiments/expert_annotation/tasks_objective.yaml \
	  --dry-run
	@echo ""
	@echo "==> Generating paper-table snippets from results"
	$(PYTHON) experiments/generate_paper_tables.py
	@echo ""
	@echo "[OK] Reproduction complete. See experiments/results/ and experiments/expert_annotation/results/."
	@echo "    For live LLM (§6.7 headline numbers): make llm-eval-live with API credentials."

# ---------------------------------------------------------------------------
# Clean targets
# ---------------------------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -path "*/registry/node_modules" -exec rm -rf {} + 2>/dev/null || true
	@echo "[OK] Cleaned build artifacts."

clean-cache:
	rm -rf experiments/expert_annotation/cache/raw_docs
	@echo "[OK] Removed raw-doc cache."

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from asm_cli import main as asm_main
from openrouter_adapter import (
    load_openrouter_manifests,
    openrouter_models_to_manifests,
)
from scorer import parse_manifest
from scorer import Preferences, ServiceVector, score_topsis


SAMPLE_MODELS = {
    "data": [
        {
            "id": "openai/gpt-test",
            "name": "OpenAI: GPT Test",
            "context_length": 128000,
            "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
            "top_provider": {"context_length": 128000, "max_completion_tokens": 16000},
            "architecture": {
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"],
            },
        },
        {
            "id": "cheap/free-model:free",
            "name": "Cheap: Free Model",
            "context_length": 8192,
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
        },
        {
            "id": "router/special",
            "name": "Router: Special",
            "pricing": {"prompt": "-1", "completion": "-1"},
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
        },
    ]
}


SAMPLE_RANKINGS = {
    "generated_at": "2026-05-04T00:00:00Z",
    "source": "fixture",
    "n_models": 2,
    "models": [
        {
            "permaslug": "openai/gpt-test-20260501",
            "slug": "openai/gpt-test",
            "author": "openai",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
            "count": 10,
            "rank_by_prompt_tokens": 1,
        },
        {
            "permaslug": "other/model-20260501",
            "slug": "other/model",
            "author": "other",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "count": 2,
            "rank_by_prompt_tokens": 2,
        },
    ],
}


def test_openrouter_models_to_ephemeral_manifests():
    manifests = openrouter_models_to_manifests(
        SAMPLE_MODELS["data"],
        models_source="https://openrouter.ai/api/v1/models",
        retrieved_at="2026-05-10T00:00:00Z",
        ranking_by_slug={"openai/gpt-test": SAMPLE_RANKINGS["models"][0]},
        ranking_count=2,
        ranking_generated_at=SAMPLE_RANKINGS["generated_at"],
    )

    assert len(manifests) == 2
    first = manifests[0]
    schema = json.loads((Path(__file__).resolve().parent.parent / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for manifest in manifests:
        assert list(validator.iter_errors(manifest)) == []

    assert first["service_id"] == "openrouter/openai/gpt-test@current"
    assert first["taxonomy"] == "ai.llm.chat"
    assert first["ttl"] == 300
    assert first["provenance"]["verification_status"] == "self_reported"
    assert "usage signal" in first["provenance"]["notes"]
    assert first["pricing"]["billing_dimensions"][0]["cost_per_unit"] == pytest.approx(0.15)
    assert first["pricing"]["billing_dimensions"][1]["cost_per_unit"] == pytest.approx(0.6)
    assert first["quality"]["metrics"][0]["name"] == "openrouter_usage_signal"
    assert first["quality"]["metrics"][0]["score"] == pytest.approx(1.0)

    vector = parse_manifest(first, io_ratio=0.5)
    assert vector.cost_per_unit == pytest.approx(0.375 / 1_000_000)
    assert vector.quality_score == pytest.approx(1.0)


def test_load_openrouter_manifests_from_cached_json(tmp_path: Path):
    models_path = tmp_path / "models.json"
    rankings_path = tmp_path / "rankings.json"
    models_path.write_text(json.dumps(SAMPLE_MODELS), encoding="utf-8")
    rankings_path.write_text(json.dumps(SAMPLE_RANKINGS), encoding="utf-8")

    manifests, metadata = load_openrouter_manifests(
        models_json=models_path,
        rankings_json=rankings_path,
    )

    assert metadata["n_models"] == 3
    assert metadata["n_manifests"] == 2
    assert metadata["ranking_snapshot"] == "2026-05-04T00:00:00Z"
    assert manifests[1]["quality"]["metrics"][0]["score"] == pytest.approx(0.5)


def test_cli_openrouter_source_with_cached_json(tmp_path: Path, capsys):
    models_path = tmp_path / "models.json"
    rankings_path = tmp_path / "rankings.json"
    models_path.write_text(json.dumps(SAMPLE_MODELS), encoding="utf-8")
    rankings_path.write_text(json.dumps(SAMPLE_RANKINGS), encoding="utf-8")

    code = asm_main([
        "score",
        "--source",
        "openrouter",
        "--openrouter-models-json",
        str(models_path),
        "--openrouter-rankings-json",
        str(rankings_path),
        "cheap LLM under $1 per 1M tokens under 1s",
    ])
    output = capsys.readouterr().out

    assert code == 0
    assert "OpenRouter ephemeral manifests" in output
    assert "ignored latency hard constraint" in output
    assert "representative cost <= $1.0000/1M blended tokens" in output
    assert "Selected:" in output


def test_cli_openrouter_subcommand_with_cached_json(tmp_path: Path, capsys):
    models_path = tmp_path / "models.json"
    rankings_path = tmp_path / "rankings.json"
    models_path.write_text(json.dumps(SAMPLE_MODELS), encoding="utf-8")
    rankings_path.write_text(json.dumps(SAMPLE_RANKINGS), encoding="utf-8")

    code = asm_main([
        "openrouter",
        "--openrouter-models-json",
        str(models_path),
        "--openrouter-rankings-json",
        str(rankings_path),
        "cheap coding model under $1 per 1M tokens",
    ])
    output = capsys.readouterr().out

    assert code == 0
    assert "OpenRouter ephemeral manifests" in output
    assert "Model: cheap/free-model:free" in output
    assert "Selected:" in output


def test_cli_openrouter_json_format(tmp_path: Path, capsys):
    models_path = tmp_path / "models.json"
    rankings_path = tmp_path / "rankings.json"
    models_path.write_text(json.dumps(SAMPLE_MODELS), encoding="utf-8")
    rankings_path.write_text(json.dumps(SAMPLE_RANKINGS), encoding="utf-8")

    code = asm_main([
        "openrouter",
        "--format",
        "json",
        "--openrouter-models-json",
        str(models_path),
        "--openrouter-rankings-json",
        str(rankings_path),
        "cheap coding model under $1 per 1M tokens",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["selected"]["model"] == "cheap/free-model:free"
    assert payload["ranked"][0]["cost_per_1m_blended_tokens"] == 0
    assert payload["source"]["n_manifests"] == 2


def test_cli_openrouter_route_litellm_format(tmp_path: Path, capsys):
    models_path = tmp_path / "models.json"
    rankings_path = tmp_path / "rankings.json"
    models_path.write_text(json.dumps(SAMPLE_MODELS), encoding="utf-8")
    rankings_path.write_text(json.dumps(SAMPLE_RANKINGS), encoding="utf-8")

    code = asm_main([
        "openrouter",
        "route",
        "--format",
        "litellm",
        "--openrouter-models-json",
        str(models_path),
        "--openrouter-rankings-json",
        str(rankings_path),
        "cheap coding model under $1 per 1M tokens",
    ])
    output = capsys.readouterr().out

    assert code == 0
    assert "model_list:" in output
    assert "model: openrouter/cheap/free-model:free" in output
    assert "asm_score:" in output


def test_topsis_handles_unknown_latency_without_nan():
    services = [
        ServiceVector("a", "A", "ai.llm.chat", 1.0, 0.5, float("inf"), 0.5),
        ServiceVector("b", "B", "ai.llm.chat", 2.0, 0.8, float("inf"), 0.5),
    ]
    results = score_topsis(services, Preferences(cost=0.4, quality=0.3, speed=0.2, reliability=0.1))

    assert len(results) == 2
    for result in results:
        assert result.total_score == result.total_score
        assert result.breakdown["speed"] == 1.0

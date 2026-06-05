#!/usr/bin/env python3
"""OpenRouter-to-ASM ephemeral manifest adapter.

This adapter is intentionally opportunistic: it maps OpenRouter model metadata
into temporary ASM manifests so the normal ASM scorer can rank LLM APIs without
requiring providers to publish manifests first.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_RANKINGS_URL = "https://openrouter.ai/rankings"
DEFAULT_RANKINGS_JSON = ROOT / "experiments" / "results" / "external_validation" / "openrouter_rankings.json"

# LMArena Elo (benchmark-backed quality signal). Snapshot built from
# huggingface.co/datasets/lmarena-ai/leaderboard-dataset (text/latest).
# Canonical location is inside the scorer package so it ships in the wheel;
# ROOT/scorer resolves in both editable dev and installed layouts. The old
# data/lmarena path is kept as a fallback.
def _default_elo_snapshot() -> Path:
    packaged = ROOT / "scorer" / "data" / "elo_snapshot.json"
    return packaged if packaged.exists() else ROOT / "data" / "lmarena" / "elo_snapshot.json"


ARENA_ELO_SNAPSHOT = _default_elo_snapshot()
ARENA_ELO_ANCHOR_LOW = 1000.0
ARENA_ELO_ANCHOR_HIGH = 1500.0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_openrouter_models(models_json: str | Path | None = None, timeout: int = 20) -> tuple[list[dict], str, str]:
    """Load OpenRouter model records from a JSON cache or the public API."""
    retrieved_at = utc_now()
    if models_json:
        path = Path(models_json)
        data = json.loads(path.read_text(encoding="utf-8"))
        source = f"file:{path}"
    else:
        req = Request(OPENROUTER_MODELS_URL, headers={"User-Agent": "asm-openrouter-adapter/0.1"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        source = OPENROUTER_MODELS_URL

    if isinstance(data, dict):
        models = data.get("data", [])
    elif isinstance(data, list):
        models = data
    else:
        raise ValueError("OpenRouter models payload must be an object with data[] or a model list")

    return list(models), source, retrieved_at


def load_openrouter_rankings(rankings_json: str | Path | None = None) -> tuple[dict[str, dict], int, str | None]:
    """Load cached OpenRouter usage rankings keyed by normalized model id."""
    path = Path(rankings_json) if rankings_json else DEFAULT_RANKINGS_JSON
    if not path.exists():
        return {}, 0, None

    data = json.loads(path.read_text(encoding="utf-8"))
    models = data.get("models", [])
    by_slug: dict[str, dict] = {}
    for model in models:
        for key in _ranking_keys(model):
            if key and key not in by_slug:
                by_slug[key] = model
    return by_slug, int(data.get("n_models") or len(models)), data.get("generated_at")


def openrouter_models_to_manifests(
    models: list[dict],
    *,
    models_source: str,
    retrieved_at: str,
    ranking_by_slug: dict[str, dict] | None = None,
    ranking_count: int = 0,
    ranking_generated_at: str | None = None,
    elo_index: dict | None = None,
    elo_meta: dict | None = None,
) -> list[dict]:
    """Convert OpenRouter model records into ephemeral ASM manifests."""
    ranking_by_slug = ranking_by_slug or {}
    manifests: list[dict] = []
    for model in models:
        manifest = openrouter_model_to_manifest(
            model,
            models_source=models_source,
            retrieved_at=retrieved_at,
            ranking_by_slug=ranking_by_slug,
            ranking_count=ranking_count,
            ranking_generated_at=ranking_generated_at,
            elo_index=elo_index,
            elo_meta=elo_meta,
        )
        if manifest is not None:
            manifests.append(manifest)
    return manifests


def openrouter_model_to_manifest(
    model: dict,
    *,
    models_source: str,
    retrieved_at: str,
    ranking_by_slug: dict[str, dict],
    ranking_count: int,
    ranking_generated_at: str | None,
    elo_index: dict | None = None,
    elo_meta: dict | None = None,
) -> dict | None:
    model_id = str(model.get("id") or "").strip()
    if not model_id:
        return None

    pricing = model.get("pricing") or {}
    prompt_cost = _parse_float(pricing.get("prompt"))
    completion_cost = _parse_float(pricing.get("completion"))
    if prompt_cost is None and completion_cost is None:
        return None

    dims = []
    if prompt_cost is not None:
        dims.append({
            "dimension": "input_token",
            "unit": "per_1M",
            "cost_per_unit": prompt_cost * 1_000_000,
            "currency": "USD",
        })
    if completion_cost is not None:
        dims.append({
            "dimension": "output_token",
            "unit": "per_1M",
            "cost_per_unit": completion_cost * 1_000_000,
            "currency": "USD",
        })

    ranking = _find_ranking(model_id, ranking_by_slug)
    usage_metric, usage_board = _usage_quality(model_id, ranking, ranking_count, ranking_generated_at)
    arena_metric, arena_board = _arena_quality(model_id, elo_index, elo_meta)
    if arena_metric is not None:
        # Benchmark-backed quality available -> primary axis.
        quality_metrics = [arena_metric, usage_metric]
        leaderboard = arena_board
    elif elo_index:
        # Elo mode active but this model has no benchmark match. Do NOT let the
        # usage-popularity signal masquerade as quality on the same scale as Elo
        # (mixing incomparable quality scales is a documented failure mode).
        quality_metrics = [_unknown_quality(), usage_metric]
        leaderboard = usage_board
    else:
        quality_metrics = [usage_metric]
        leaderboard = usage_board
    architecture = model.get("architecture") or {}
    top_provider = model.get("top_provider") or {}
    context_length = model.get("context_length") or top_provider.get("context_length")

    notes = [
        "Ephemeral manifest generated from OpenRouter model metadata.",
        "Pricing is OpenRouter-reported and may change.",
        "OpenRouter does not expose per-model latency or uptime in /api/v1/models.",
    ]
    if arena_metric is not None:
        notes.append("Primary quality = LMArena overall Elo (benchmark-backed); usage signal kept as secondary.")
    else:
        notes.append("Quality metric is a usage signal, not benchmark quality.")
    if ranking_generated_at:
        notes.append(f"Usage ranking snapshot: {ranking_generated_at}.")
    else:
        notes.append("No cached usage ranking snapshot was available; neutral usage score used.")

    manifest = {
        "asm_version": "0.3",
        "service_id": f"openrouter/{model_id}@current",
        "taxonomy": "ai.llm.chat",
        "display_name": str(model.get("name") or model_id),
        "provider": {
            "name": "OpenRouter",
            "url": "https://openrouter.ai",
            "verified_by": ["openrouter-public-api"],
        },
        "capabilities": {
            "description": f"OpenRouter model endpoint for {model_id}",
            "input_modalities": _schema_modalities(architecture.get("input_modalities")),
            "output_modalities": _schema_modalities(architecture.get("output_modalities")),
        },
        "pricing": {
            "billing_dimensions": dims,
            "estimated": False,
        },
        "quality": {
            "metrics": quality_metrics,
        },
        "provenance": {
            "source_url": models_source if models_source.startswith("http") else OPENROUTER_MODELS_URL,
            "retrieved_at": retrieved_at,
            "last_verified_at": retrieved_at,
            "verification_status": "self_reported",
            "notes": " ".join(notes),
        },
        "updated_at": retrieved_at,
        "ttl": 300,
    }
    if context_length:
        manifest["capabilities"]["context_window"] = int(context_length)
    if leaderboard:
        manifest["quality"]["leaderboard_rank"] = leaderboard
    return manifest


def load_openrouter_manifests(
    *,
    models_json: str | Path | None = None,
    rankings_json: str | Path | None = None,
    arena_elo: bool = True,
    arena_category: str = "overall",
    arena_snapshot_json: str | Path | None = None,
    timeout: int = 20,
) -> tuple[list[dict], dict]:
    models, source, retrieved_at = load_openrouter_models(models_json=models_json, timeout=timeout)
    rankings, ranking_count, ranking_generated_at = load_openrouter_rankings(rankings_json=rankings_json)
    elo_index, elo_meta = load_arena_elo(arena_snapshot_json, arena_category) if arena_elo else ({}, {})
    manifests = openrouter_models_to_manifests(
        models,
        models_source=source,
        retrieved_at=retrieved_at,
        ranking_by_slug=rankings,
        ranking_count=ranking_count,
        ranking_generated_at=ranking_generated_at,
        elo_index=elo_index,
        elo_meta=elo_meta,
    )
    elo_matched = sum(
        1 for m in manifests
        if (m.get("quality") or {}).get("metrics")
        and m["quality"]["metrics"][0].get("name") == "lmarena_elo"
    )
    metadata = {
        "source": source,
        "retrieved_at": retrieved_at,
        "n_models": len(models),
        "n_manifests": len(manifests),
        "ranking_snapshot": ranking_generated_at,
        "ranking_count": ranking_count,
        "arena_elo_snapshot": elo_meta.get("publish_date"),
        "arena_elo_matched": elo_matched,
    }
    return manifests, metadata


def _normalize_model_key(name: str) -> str:
    """Normalize an OpenRouter id or Arena model name to a comparable key."""
    n = (name or "").lower().strip().lstrip("~")
    if "/" in n:
        n = n.split("/", 1)[1]            # drop provider prefix on OpenRouter ids
    n = n.split(":", 1)[0]                 # drop :free / :nitro serving variants
    n = re.sub(r"[ ._]+", "-", n)          # unify separators
    n = re.sub(r"-+", "-", n).strip("-")
    for suffix in ("-fast", "-turbo", "-nitro", "-high", "-low", "-online"):
        if n.endswith(suffix):             # serving variants share the base model's Elo
            n = n[: -len(suffix)]
    return n


def load_arena_elo(
    snapshot_path: str | Path | None = None,
    category: str = "overall",
) -> tuple[dict[str, dict], dict]:
    """Load the LMArena Elo snapshot, indexed by normalized model key."""
    path = Path(snapshot_path) if snapshot_path else ARENA_ELO_SNAPSHOT
    if not path.exists():
        return {}, {}
    snap = json.loads(path.read_text(encoding="utf-8"))
    cat = (snap.get("categories") or {}).get(category) or {}
    index: dict[str, dict] = {}
    for row in cat.get("models", []):
        index.setdefault(_normalize_model_key(row.get("model", "")), row)
    meta = {
        "category": category,
        "source": snap.get("source"),
        "retrieved_at": snap.get("retrieved_at"),
        "publish_date": cat.get("leaderboard_publish_date"),
        "elo_min": cat.get("elo_min"),
        "elo_max": cat.get("elo_max"),
    }
    return index, meta


def _arena_quality(
    model_id: str,
    elo_index: dict[str, dict] | None,
    elo_meta: dict | None,
) -> tuple[dict, dict] | tuple[None, None]:
    """Return (quality_metric, leaderboard) from LMArena Elo, or (None, None)."""
    if not elo_index:
        return None, None
    row = elo_index.get(_normalize_model_key(model_id))
    if not row:
        return None, None
    elo = float(row.get("elo", 0.0))
    score = max(0.0, min(1.0, (elo - ARENA_ELO_ANCHOR_LOW) / (ARENA_ELO_ANCHOR_HIGH - ARENA_ELO_ANCHOR_LOW)))
    publish_date = (elo_meta or {}).get("publish_date")
    metric = {
        "name": "lmarena_elo",
        "score": round(score, 4),
        "scale": "0-1",
        "benchmark": f"LMArena overall Elo {int(elo)} (snapshot {publish_date})",
        "benchmark_url": "https://lmarena.ai/leaderboard",
        "self_reported": False,
    }
    leaderboard = {
        "name": f"LMArena overall ({publish_date})",
        "rank": row.get("rank"),
        "elo": elo,
        "votes": row.get("votes"),
        "url": "https://lmarena.ai/leaderboard",
    }
    return metric, leaderboard


def _unknown_quality() -> dict:
    """Neutral quality for models with no benchmark Elo (avoids mixing scales)."""
    return {
        "name": "quality_unknown",
        "score": 0.5,
        "scale": "0-1",
        "benchmark": "No LMArena Elo match; quality scored neutral (not benchmark-backed).",
        "self_reported": True,
    }


def _usage_quality(
    model_id: str,
    ranking: dict | None,
    ranking_count: int,
    ranking_generated_at: str | None,
) -> tuple[dict, dict | None]:
    if ranking and ranking_count > 1:
        rank = int(ranking.get("rank_by_prompt_tokens") or ranking_count)
        score = max(0.0, min(1.0, 1 - ((rank - 1) / (ranking_count - 1))))
        metric = {
            "name": "openrouter_usage_signal",
            "score": score,
            "scale": "0-1",
            "benchmark": "OpenRouter 7-day prompt-token usage rank",
            "benchmark_url": OPENROUTER_RANKINGS_URL,
            "self_reported": False,
        }
        leaderboard = {
            "name": "OpenRouter 7-day prompt-token usage",
            "rank": rank,
            "total": ranking_count,
            "url": OPENROUTER_RANKINGS_URL,
        }
        if ranking_generated_at:
            leaderboard["snapshot_date"] = ranking_generated_at[:10]
        return metric, leaderboard

    return {
        "name": "openrouter_usage_signal",
        "score": 0.5,
        "scale": "0-1",
        "benchmark": "No cached OpenRouter ranking match; neutral usage placeholder",
        "benchmark_url": OPENROUTER_RANKINGS_URL,
        "self_reported": True,
    }, None


def _find_ranking(model_id: str, ranking_by_slug: dict[str, dict]) -> dict | None:
    for key in _model_keys(model_id):
        if key in ranking_by_slug:
            return ranking_by_slug[key]
    return None


def _model_keys(model_id: str) -> list[str]:
    normalized = model_id.lower()
    keys = [normalized]
    if ":" in normalized:
        keys.append(normalized.split(":", 1)[0])
    return list(dict.fromkeys(keys))


def _ranking_keys(model: dict) -> list[str]:
    keys = []
    for field in ("slug", "permaslug"):
        value = str(model.get(field) or "").lower()
        if value:
            keys.append(value)
    return list(dict.fromkeys(keys))


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _schema_modalities(values: Any) -> list[str]:
    allowed = {"text", "image", "audio", "video", "file"}
    if not isinstance(values, list):
        return ["text"]
    result = [str(v) for v in values if str(v) in allowed]
    return result or ["text"]

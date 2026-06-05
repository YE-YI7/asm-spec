#!/usr/bin/env python3
"""Small public CLI for trying ASM from a checkout or editable install."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from openrouter_adapter import load_openrouter_manifests
from scorer import Constraints, Preferences, filter_services, load_manifests, parse_manifest, score_topsis


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST_DIR = ROOT / "manifests"


TAXONOMY_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("ai.audio.tts", ("tts", "text to speech", "voiceover", "voice over", "voice", "speech")),
    ("ai.audio.stt", ("stt", "speech to text", "transcription", "transcribe")),
    ("ai.llm.chat", ("llm", "chat", "model", "reasoning", "assistant")),
    ("ai.vision.image_generation", ("image", "picture", "illustration", "generate image")),
    ("ai.video.generation", ("video", "clip", "movie")),
    ("tool.data.search", ("search", "web search", "research")),
    ("tool.communication.email", ("email", "mail")),
]


def infer_taxonomy(query: str) -> str | None:
    q = query.lower()
    for taxonomy, hints in TAXONOMY_HINTS:
        if any(h in q for h in hints):
            return taxonomy
    return None


def infer_constraints(query: str, taxonomy: str | None) -> Constraints:
    q = query.lower()
    max_latency_s = None

    match = re.search(r"(?:under|below|less than|<=|<)\s*(\d+(?:\.\d+)?)\s*(ms|s|sec|second|seconds)", q)
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        max_latency_s = value / 1000 if unit == "ms" else value

    min_uptime = 0.99 if any(word in q for word in ("reliable", "reliability", "uptime")) else None
    max_cost = None
    cost_match = re.search(
        r"(?:under|below|less than|<=|<)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:/|per)?\s*(?:1m|1 m|million|m)\s*(?:tokens?)?",
        q,
    )
    if cost_match:
        max_cost = float(cost_match.group(1)) / 1_000_000

    return Constraints(required_taxonomy=taxonomy, max_latency_s=max_latency_s, min_uptime=min_uptime, max_cost=max_cost)


def infer_preferences(query: str) -> Preferences:
    q = query.lower()
    weights = {
        "cost": 0.30,
        "quality": 0.30,
        "speed": 0.20,
        "reliability": 0.20,
    }
    if any(word in q for word in ("cheap", "cheapest", "low cost", "budget")):
        weights.update(cost=0.50, quality=0.20, speed=0.15, reliability=0.15)
    if any(word in q for word in ("best", "highest quality", "quality", "accurate")):
        weights.update(cost=0.15, quality=0.55, speed=0.15, reliability=0.15)
    if any(word in q for word in ("fast", "latency", "under", "below", "low latency")):
        weights["speed"] += 0.10
    if any(word in q for word in ("reliable", "uptime", "stable")):
        weights["reliability"] += 0.10

    total = sum(weights.values())
    normalized = {key: value / total for key, value in weights.items()}
    return Preferences(**normalized)


def rejection_reason(service, constraints: Constraints) -> str | None:
    if constraints.required_taxonomy and not service.taxonomy.startswith(constraints.required_taxonomy):
        return f"taxonomy {service.taxonomy} does not match {constraints.required_taxonomy}"
    if constraints.max_latency_s is not None and service.latency_seconds > constraints.max_latency_s:
        return f"latency {service.latency_seconds:.2f}s > max {constraints.max_latency_s:.2f}s"
    if constraints.min_uptime is not None and service.uptime < constraints.min_uptime:
        return f"uptime {service.uptime:.3f} < min {constraints.min_uptime:.3f}"
    if constraints.min_quality is not None and service.quality_score < constraints.min_quality:
        return f"quality {service.quality_score:.3f} < min {constraints.min_quality:.3f}"
    if constraints.max_cost is not None and service.cost_per_unit > constraints.max_cost:
        return f"cost {format_cost(service.cost_per_unit, service.taxonomy)} > max {format_cost(constraints.max_cost, service.taxonomy)}"
    return None


_QUALITY_TAGS = {
    "lmarena_elo": "Elo",
    "quality_unknown": "no-bench",
    "openrouter_usage_signal": "usage",
}


def _quality_source_map(manifests: list[dict]) -> dict:
    out = {}
    for m in manifests:
        mets = (m.get("quality") or {}).get("metrics") or []
        name = mets[0].get("name") if mets else None
        out[m.get("service_id")] = _QUALITY_TAGS.get(name, "")
    return out


def _format_ranked_row(item, q_source: dict, hide_sla: bool) -> str:
    tag = q_source.get(getattr(item.service, "service_id", None), "")
    qtag = f" {tag}" if tag else ""
    row = (
        f"{item.rank}. {item.service.display_name} "
        f"(score={item.total_score:.4f}, "
        f"cost={format_cost(item.service.cost_per_unit, item.service.taxonomy)}, "
        f"quality={item.service.quality_score:.3f}{qtag}"
    )
    if not hide_sla:
        row += f", latency={format_latency(item.service.latency_seconds)}, uptime={item.service.uptime:.3f}"
    return row + ")"


def _arena_category_for(query: str) -> str:
    return "coding" if re.search(r"\bcod(?:e|ing)\b|program", query.lower()) else "overall"


def cmd_score(args: argparse.Namespace) -> int:
    source_metadata = None
    openrouter_latency_ignored = False
    openrouter_uptime_ignored = False
    if args.source == "openrouter":
        manifests, source_metadata = load_openrouter_manifests(
            models_json=args.openrouter_models_json,
            rankings_json=args.openrouter_rankings_json,
            arena_category=_arena_category_for(args.query),
            timeout=args.openrouter_timeout,
        )
        taxonomy = args.taxonomy or "ai.llm.chat"
        manifest_dir = None
    else:
        manifest_dir = Path(args.manifests)
        manifests = load_manifests(manifest_dir)
        taxonomy = args.taxonomy or infer_taxonomy(args.query)

    constraints = infer_constraints(args.query, taxonomy)
    preferences = infer_preferences(args.query)
    if args.source == "openrouter" and constraints.max_latency_s is not None and not args.strict_latency:
        constraints.max_latency_s = None
        openrouter_latency_ignored = True
    if args.source == "openrouter" and constraints.min_uptime is not None:
        constraints.min_uptime = None
        openrouter_uptime_ignored = True

    candidate_manifests = [
        m for m in manifests
        if not taxonomy or str(m.get("taxonomy", "")).startswith(taxonomy)
    ]
    if not candidate_manifests:
        location = source_metadata["source"] if source_metadata else str(manifest_dir)
        print(f"No candidate manifests found for taxonomy={taxonomy or 'any'} in {location}")
        return 1

    services = [parse_manifest(m, io_ratio=preferences.io_ratio) for m in candidate_manifests]
    selected = filter_services(services, constraints)
    ranked = score_topsis(selected, preferences)

    print(f"Query: {args.query}")
    print(f"Taxonomy: {taxonomy or 'any'}")
    if source_metadata:
        print(
            "Source: OpenRouter ephemeral manifests "
            f"({source_metadata['n_manifests']} scoreable / {source_metadata['n_models']} models, "
            f"retrieved_at={source_metadata['retrieved_at']})"
        )
        if source_metadata.get("arena_elo_snapshot"):
            print(
                f"Quality: LMArena Elo (snapshot {source_metadata['arena_elo_snapshot']}), "
                f"benchmark-backed for {source_metadata.get('arena_elo_matched', 0)}/{source_metadata['n_manifests']} models; "
                "the rest scored neutral (quality unknown)."
            )
        if source_metadata.get("ranking_snapshot"):
            print(f"Usage signal (secondary): cached OpenRouter ranking snapshot {source_metadata['ranking_snapshot']}")
        print("Caveat: Elo is human-preference quality; OpenRouter usage is a revealed-preference signal, not quality.")
    if openrouter_latency_ignored:
        print("Warning: OpenRouter /api/v1/models does not expose latency; ignored latency hard constraint.")
    if openrouter_uptime_ignored:
        print("Warning: OpenRouter /api/v1/models does not expose uptime; ignored uptime hard constraint.")
    print(
        "Preferences: "
        f"cost={preferences.cost:.2f}, quality={preferences.quality:.2f}, "
        f"speed={preferences.speed:.2f}, reliability={preferences.reliability:.2f}"
    )
    if constraints.max_latency_s is not None or constraints.min_uptime is not None or constraints.max_cost is not None:
        parts = []
        if constraints.max_latency_s is not None:
            parts.append(f"latency <= {constraints.max_latency_s:.2f}s")
        if constraints.min_uptime is not None:
            parts.append(f"uptime >= {constraints.min_uptime:.3f}")
        if constraints.max_cost is not None:
            parts.append(f"representative cost <= {format_cost(constraints.max_cost, taxonomy)}")
        print(f"Hard constraints: {', '.join(parts)}")

    if not ranked:
        print("\nNo service satisfies the hard constraints.")
    else:
        winner = ranked[0]
        print(f"\nSelected: {winner.service.display_name}")
        print(f"Reason: {winner.reasoning}")
        print("\nRanked services:")
        q_source = _quality_source_map(candidate_manifests)
        hide_sla = args.source == "openrouter"
        for item in ranked[: args.limit]:
            print(_format_ranked_row(item, q_source, hide_sla))
        if args.source == "openrouter":
            print(f'\nTip: turn this into a router config -> asm openrouter route --format litellm "{args.query}"')

    rejected = []
    for service in services:
        reason = rejection_reason(service, constraints)
        if reason:
            rejected.append((service.display_name, reason))

    if rejected:
        print("\nRejected by hard constraints:")
        for name, reason in rejected[: args.limit]:
            print(f"- {name}: {reason}")
    else:
        print("\nRejected by hard constraints: none")

    return 0 if ranked else 2


def cmd_openrouter(args: argparse.Namespace) -> int:
    query_parts = list(args.query)
    mode = "score"
    if query_parts and query_parts[0] == "route":
        mode = "route"
        query_parts = query_parts[1:]
    query = " ".join(query_parts).strip()
    if not query:
        print('OpenRouter query is required. Example: asm openrouter "cheap coding model under $0.50/1M tokens"')
        return 1

    manifests, source_metadata = load_openrouter_manifests(
        models_json=args.openrouter_models_json,
        rankings_json=args.openrouter_rankings_json,
        arena_category=_arena_category_for(query),
        timeout=args.openrouter_timeout,
    )
    preferences = infer_preferences(query)
    constraints = infer_constraints(query, "ai.llm.chat")
    latency_ignored = False
    uptime_ignored = False
    if constraints.max_latency_s is not None and not args.strict_latency:
        constraints.max_latency_s = None
        latency_ignored = True
    if constraints.min_uptime is not None:
        constraints.min_uptime = None
        uptime_ignored = True

    services = [parse_manifest(m, io_ratio=preferences.io_ratio) for m in manifests]
    selected = filter_services(services, constraints)
    ranked = score_topsis(selected, preferences)

    if args.format == "json":
        print(json.dumps(
            _openrouter_json_payload(query, ranked, services, constraints, preferences, source_metadata, latency_ignored, args.limit),
            indent=2,
        ))
        return 0 if ranked else 2

    output_format = "litellm" if mode == "route" and args.format == "text" else args.format
    if mode == "route" or output_format != "text":
        if not ranked:
            print("No OpenRouter model satisfies the hard constraints.")
            return 2
        print(_format_route_config(output_format, ranked[: args.limit], query))
        return 0

    _print_selection(
        query=query,
        taxonomy="ai.llm.chat",
        source_metadata=source_metadata,
        preferences=preferences,
        constraints=constraints,
        ranked=ranked,
        services=services,
        limit=args.limit,
        openrouter_latency_ignored=latency_ignored,
        openrouter_uptime_ignored=uptime_ignored,
        quality_tags=_quality_source_map(manifests),
    )
    return 0 if ranked else 2


def _print_selection(
    *,
    query: str,
    taxonomy: str | None,
    source_metadata: dict | None,
    preferences: Preferences,
    constraints: Constraints,
    ranked: list,
    services: list,
    limit: int,
    openrouter_latency_ignored: bool = False,
    openrouter_uptime_ignored: bool = False,
    quality_tags: dict | None = None,
) -> None:
    print(f"Query: {query}")
    print(f"Taxonomy: {taxonomy or 'any'}")
    if source_metadata:
        print(
            "Source: OpenRouter ephemeral manifests "
            f"({source_metadata['n_manifests']} scoreable / {source_metadata['n_models']} models, "
            f"retrieved_at={source_metadata['retrieved_at']})"
        )
        if source_metadata.get("arena_elo_snapshot"):
            print(
                f"Quality: LMArena Elo (snapshot {source_metadata['arena_elo_snapshot']}), "
                f"benchmark-backed for {source_metadata.get('arena_elo_matched', 0)}/{source_metadata['n_manifests']} models; "
                "the rest scored neutral (quality unknown)."
            )
        if source_metadata.get("ranking_snapshot"):
            print(f"Usage signal (secondary): cached OpenRouter ranking snapshot {source_metadata['ranking_snapshot']}")
        print("Caveat: Elo is human-preference quality; OpenRouter usage is a revealed-preference signal, not quality.")
    if openrouter_latency_ignored:
        print("Warning: OpenRouter /api/v1/models does not expose latency; ignored latency hard constraint.")
    if openrouter_uptime_ignored:
        print("Warning: OpenRouter /api/v1/models does not expose uptime; ignored uptime hard constraint.")
    print(
        "Preferences: "
        f"cost={preferences.cost:.2f}, quality={preferences.quality:.2f}, "
        f"speed={preferences.speed:.2f}, reliability={preferences.reliability:.2f}"
    )
    if constraints.max_latency_s is not None or constraints.min_uptime is not None or constraints.max_cost is not None:
        parts = []
        if constraints.max_latency_s is not None:
            parts.append(f"latency <= {constraints.max_latency_s:.2f}s")
        if constraints.min_uptime is not None:
            parts.append(f"uptime >= {constraints.min_uptime:.3f}")
        if constraints.max_cost is not None:
            parts.append(f"representative cost <= {format_cost(constraints.max_cost, taxonomy)}")
        print(f"Hard constraints: {', '.join(parts)}")

    if not ranked:
        print("\nNo service satisfies the hard constraints.")
    else:
        winner = ranked[0]
        print(f"\nSelected: {winner.service.display_name}")
        print(f"Model: {_openrouter_model_id(winner.service) or winner.service.service_id}")
        print(f"Reason: {winner.reasoning}")
        print("\nRanked services:")
        q_source = quality_tags or {}
        for item in ranked[:limit]:
            print(_format_ranked_row(item, q_source, hide_sla=True))
        print(f'\nTip: turn this into a router config -> asm openrouter route --format litellm "{query}"')

    rejected = []
    for service in services:
        reason = rejection_reason(service, constraints)
        if reason:
            rejected.append((service.display_name, reason))

    if rejected:
        print("\nRejected by hard constraints:")
        for name, reason in rejected[:limit]:
            print(f"- {name}: {reason}")
    else:
        print("\nRejected by hard constraints: none")


def format_cost(cost_per_unit: float, taxonomy: str | None) -> str:
    if taxonomy and taxonomy.startswith("ai.llm"):
        return f"${cost_per_unit * 1_000_000:.4f}/1M blended tokens"
    return f"${cost_per_unit:.8f}/unit"


def format_latency(latency_seconds: float) -> str:
    if latency_seconds == float("inf"):
        return "unknown"
    return f"{latency_seconds:.2f}s"


def _openrouter_model_id(service) -> str | None:
    prefix = "openrouter/"
    suffix = "@current"
    service_id = service.service_id
    if service_id.startswith(prefix) and service_id.endswith(suffix):
        return service_id[len(prefix):-len(suffix)]
    return None


def _openrouter_json_payload(
    query: str,
    ranked: list,
    services: list,
    constraints: Constraints,
    preferences: Preferences,
    source_metadata: dict,
    latency_ignored: bool,
    limit: int,
) -> dict:
    rejected = []
    for service in services:
        reason = rejection_reason(service, constraints)
        if reason:
            rejected.append({"service": service.display_name, "model": _openrouter_model_id(service), "reason": reason})

    return {
        "query": query,
        "source": source_metadata,
        "caveat": "OpenRouter usage is a revealed-preference signal, not benchmark quality.",
        "warnings": ["OpenRouter /api/v1/models does not expose latency; latency hard constraint ignored."] if latency_ignored else [],
        "preferences": {
            "cost": preferences.cost,
            "quality": preferences.quality,
            "speed": preferences.speed,
            "reliability": preferences.reliability,
            "io_ratio": preferences.io_ratio,
        },
        "selected": _scored_to_dict(ranked[0]) if ranked else None,
        "ranked": [_scored_to_dict(item) for item in ranked[:limit]],
        "rejected": rejected[:limit],
    }


def _scored_to_dict(item) -> dict:
    return {
        "rank": item.rank,
        "model": _openrouter_model_id(item.service),
        "service_id": item.service.service_id,
        "display_name": item.service.display_name,
        "score": item.total_score,
        "cost_per_1m_blended_tokens": round(item.service.cost_per_unit * 1_000_000, 6),
        "quality": item.service.quality_score,
        "latency_seconds": None if item.service.latency_seconds == float("inf") else item.service.latency_seconds,
        "uptime": item.service.uptime,
        "reason": item.reasoning,
    }


def _format_route_config(fmt: str, ranked: list, query: str) -> str:
    models = [(_openrouter_model_id(item.service) or item.service.service_id, item) for item in ranked]
    if fmt == "litellm":
        lines = [
            "# Generated by ASM from OpenRouter value metadata.",
            f"# Query: {query}",
            "model_list:",
        ]
        for idx, (model_id, item) in enumerate(models, start=1):
            alias = "asm-primary" if idx == 1 else f"asm-fallback-{idx - 1}"
            lines.extend([
                f"  - model_name: {alias}",
                "    litellm_params:",
                f"      model: openrouter/{model_id}",
                f"    asm_score: {item.total_score:.4f}",
            ])
        lines.extend([
            "router_settings:",
            "  routing_strategy: usage-based-routing",
        ])
        if len(models) > 1:
            lines.append("  fallbacks:")
            lines.append("    - asm-primary:")
            for idx in range(1, len(models)):
                lines.append(f"        - asm-fallback-{idx}")
        return "\n".join(lines)

    if fmt == "vercel-ai-sdk":
        primary = models[0][0]
        fallbacks = [model_id for model_id, _ in models[1:]]
        return "\n".join([
            "// Generated by ASM from OpenRouter value metadata.",
            f"// Query: {query}",
            "import { openrouter } from '@openrouter/ai-sdk-provider';",
            "",
            f"export const model = openrouter('{primary}');",
            f"export const fallbackModels = {json.dumps(fallbacks)}.map((id) => openrouter(id));",
        ])

    if fmt == "langchain":
        primary = models[0][0]
        fallbacks = [model_id for model_id, _ in models[1:]]
        return "\n".join([
            "# Generated by ASM from OpenRouter value metadata.",
            f"# Query: {query}",
            "import os",
            "from langchain_openai import ChatOpenAI",
            "",
            "primary = ChatOpenAI(",
            f"    model=\"{primary}\",",
            "    base_url=\"https://openrouter.ai/api/v1\",",
            "    api_key=os.environ[\"OPENROUTER_API_KEY\"],",
            ")",
            f"fallback_model_ids = {json.dumps(fallbacks)}",
        ])

    raise ValueError(f"Unsupported route format: {fmt}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asm", description="Agent Service Manifest CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    score = sub.add_parser("score", help="Rank services for a natural-language service request")
    score.add_argument("query", help='Example: "cheap reliable TTS under 1s"')
    score.add_argument("--taxonomy", help="Override inferred taxonomy, e.g. ai.audio.tts")
    score.add_argument("--manifests", default=str(DEFAULT_MANIFEST_DIR), help="Directory of .asm.json manifests")
    score.add_argument("--source", choices=["local", "openrouter"], default="local",
                       help="Manifest source. 'openrouter' builds ephemeral manifests from OpenRouter model metadata.")
    score.add_argument("--openrouter-models-json", help="Use a cached OpenRouter /api/v1/models JSON file")
    score.add_argument("--openrouter-rankings-json", help="Use a cached OpenRouter rankings JSON file")
    score.add_argument("--openrouter-timeout", type=int, default=20, help="Timeout for OpenRouter models API fetch")
    score.add_argument("--strict-latency", action="store_true",
                       help="Do not ignore latency constraints for sources with unknown latency")
    score.add_argument("--limit", type=int, default=5, help="Maximum ranked/rejected rows to print")
    score.set_defaults(func=cmd_score)

    openrouter = sub.add_parser("openrouter", help="Rank live OpenRouter models and optionally emit router configs")
    openrouter.add_argument(
        "query",
        nargs="+",
        help='Query, optionally prefixed with route. Example: asm openrouter "cheap coding model under $0.50/1M tokens"',
    )
    openrouter.add_argument("--format", choices=["text", "json", "litellm", "vercel-ai-sdk", "langchain"], default="text")
    openrouter.add_argument("--openrouter-models-json", help="Use a cached OpenRouter /api/v1/models JSON file")
    openrouter.add_argument("--openrouter-rankings-json", help="Use a cached OpenRouter rankings JSON file")
    openrouter.add_argument("--openrouter-timeout", type=int, default=20, help="Timeout for OpenRouter models API fetch")
    openrouter.add_argument("--strict-latency", action="store_true",
                            help="Do not ignore latency constraints for sources with unknown latency")
    openrouter.add_argument("--limit", type=int, default=5, help="Maximum ranked models or route entries to print")
    openrouter.set_defaults(func=cmd_openrouter)
    return parser


def build_openrouter_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asm openrouter", description="Rank live OpenRouter models")
    parser.add_argument("--format", choices=["text", "json", "litellm", "vercel-ai-sdk", "langchain"], default="text")
    parser.add_argument("--openrouter-models-json", help="Use a cached OpenRouter /api/v1/models JSON file")
    parser.add_argument("--openrouter-rankings-json", help="Use a cached OpenRouter rankings JSON file")
    parser.add_argument("--openrouter-timeout", type=int, default=20, help="Timeout for OpenRouter models API fetch")
    parser.add_argument("--strict-latency", action="store_true",
                        help="Do not ignore latency constraints for sources with unknown latency")
    parser.add_argument("--limit", type=int, default=5, help="Maximum ranked models or route entries to print")
    parser.add_argument(
        "query",
        nargs="*",
        help='Query, optionally prefixed with route. Example: asm openrouter route --format litellm "cheap coding model"',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "openrouter":
        parser = build_openrouter_parser()
        args, query_parts = parser.parse_known_args(argv[1:])
        args.query = args.query + query_parts
        return cmd_openrouter(args)

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Small public CLI for trying ASM from a checkout or editable install."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from asm_protocol.adaptive import OwnerContext, adaptive_select
from asm_protocol.federation import MCPRegistryClient
from asm_protocol.preferences import PreferenceLedger, model_from_ledger
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


def cmd_select(args: argparse.Namespace) -> int:
    """Tool selection over the library/ manifests (the agent-tool-selection wedge)."""
    from library_select import select  # stdlib-only; lazy to keep CLI startup lean

    result = select(
        args.task,
        taxonomy=args.taxonomy,
        agent_reach=args.reach,
        user_platform=args.platform,
        required_functions=[f for f in (args.requires or "").split(",") if f],
        require_approval_for=[s for s in (args.approval_for or "").split(",") if s],
        require_agent_completable_setup=args.agent_setup_only,
        fallback_policy=args.fallback_policy,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["selected"] else 2

    sel = result["selected"]
    if not sel:
        print(f"No selection ({result['selection_status']}): {result['reason']}")
        for candidate in result["alternatives"][: args.limit]:
            print(f"  candidate: {candidate['display_name']} ({candidate['cost_estimate']['status']} cost)")
        for r in result["rejected"][: args.limit]:
            print(f"  - {r['service']}: {r['reason']}")
        return 2
    print(f"Selected: {sel['display_name']} ({sel['service_id']})")
    estimate = sel["cost_estimate"]
    cost = (f"${sel['monthly_cost_usd']}/mo" if sel["monthly_cost_usd"] is not None
            else f"{estimate['status']} (workload or allowance facts required)")
    print(f"  cost={cost}, interface={sel['interface']}, reach={sel['reach']}")
    if sel.get("agent_completable_setup") is not None:
        print(f"  setup: agent_completable={sel['agent_completable_setup']}, requires={sel.get('setup_requires', [])}")
    print(f"  risk={result['risk_class']}, approval_required={result['approval_required']}, side_effects={result['side_effects']}")
    print(f"  reason: {result['reason']}")
    for alt in result["alternatives"][: args.limit]:
        alt_cost = (f"${alt['monthly_cost_usd']}/mo"
                    if alt["monthly_cost_usd"] is not None
                    else alt["cost_estimate"]["status"])
        print(f"  alt: {alt['display_name']} ({alt_cost})")
    if result["rejected"]:
        print("  filtered out:")
        for r in result["rejected"][: args.limit]:
            print(f"   - {r['service']}: {r['reason']}")
    return 0


def _csv(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in (value or "").split(",") if item.strip())


def cmd_adaptive_select(args: argparse.Namespace) -> int:
    """Experimental owner-aligned decision over the canonical tool library."""
    ledger = PreferenceLedger(args.preference_ledger)
    model = model_from_ledger(ledger)
    context = OwnerContext(
        explicit_service_id=args.explicit_tool,
        installed_service_ids=_csv(args.installed),
        authenticated_service_ids=_csv(args.authenticated),
        forbidden_service_ids=_csv(args.forbidden),
        forbidden_side_effects=_csv(args.forbidden_side_effects),
        max_risk=args.max_risk,
        allow_unknown_risk=args.allow_unknown_risk,
        reversible=not args.non_reversible,
        interruption_cost=args.interruption_cost,
        monthly_budget=args.monthly_budget,
        budget_currency=args.budget_currency,
        latency_target_seconds=args.latency_target_seconds,
    )
    result = adaptive_select(
        args.task,
        taxonomy=args.taxonomy,
        required_functions=_csv(args.requires),
        agent_reach=args.reach,
        user_platform=args.platform,
        require_agent_completable_setup=args.agent_setup_only,
        owner_context=context,
        preference_model=model,
        freshness_policy=args.freshness_policy,
        policy=args.policy,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Status: {result['selection_status']}")
        print(f"Policy: {result['decision_policy']}")
        print(f"Owner evidence: {result['preference_model']['observations']} observations")
        if result["selected"]:
            selected = result["selected"]
            print(f"Selected: {selected['display_name']} ({selected['service_id']})")
        print(f"Reason: {result['reason']}")
        if result.get("question"):
            print(f"Clarify only because VoI is positive: {result['question']}")
        if result.get("expected_regret") is not None:
            print(
                f"Expected regret: {result['expected_regret']:.4f}; "
                f"preference confidence: {result['preference_confidence']:.2%}"
            )
        for row in result["rejected"][: args.limit]:
            print(f"  rejected: {row['service_id']}: {row['reason']}")
    return 0 if result["selected"] else 2


def cmd_discover(args: argparse.Namespace) -> int:
    """Retrieve candidate MCP servers without fabricating ASM selection facts."""
    client = MCPRegistryClient(args.registry_url, timeout=args.timeout)
    records = client.search(
        args.query,
        limit=args.limit,
        max_pages=args.max_pages,
        latest_only=not args.all_versions,
    )
    rows = [record.to_discovery_candidate() for record in records]
    payload = {
        "query": args.query,
        "count": len(rows),
        "scan_scope": {
            "bounded": True,
            "max_pages": args.max_pages,
            "max_registry_records_scanned": args.max_pages * 100,
        },
        "candidates": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Discovery candidates for {args.query!r}: {len(rows)}")
        print("These records are not selection-ready until ASM facts are fetched and verified.")
        for row in rows:
            print(f"- {row['registry_name']}@{row['version']}: {row.get('description') or ''}")
    return 0 if rows else 2


def _feature_json(value: str) -> dict[str, float]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"features must be a JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("features must be a JSON object")
    try:
        return {str(name): float(number) for name, number in parsed.items()}
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("feature values must be numbers") from exc


def cmd_preference_choice(args: argparse.Namespace) -> int:
    event = PreferenceLedger(args.ledger).record_pairwise(
        chosen_service_id=args.chosen_id,
        chosen_features=args.chosen_features,
        rejected_service_id=args.rejected_id,
        rejected_features=args.rejected_features,
        context_tags=_csv(args.context_tags),
        reversible=not args.non_reversible,
    )
    print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_preference_outcome(args: argparse.Namespace) -> int:
    event = PreferenceLedger(args.ledger).record_outcome(
        service_id=args.service_id,
        features=args.features,
        reward=args.reward,
        context_tags=_csv(args.context_tags),
        reversible=not args.non_reversible,
    )
    print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_preference_show(args: argparse.Namespace) -> int:
    model = model_from_ledger(PreferenceLedger(args.ledger))
    print(json.dumps({
        "observations": model.observations,
        "posterior_mean": model.mean,
        "model_digest": model.digest(),
        "raw_history_included": False,
    }, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asm", description="Agent Service Manifest CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sel = sub.add_parser("select", help="Pick a TOOL from the ASM library for an agent task")
    sel.add_argument("task", help='Example: "find and book a refundable flight"')
    sel.add_argument("--taxonomy", help="Scope candidates, e.g. tool.booking.travel")
    sel.add_argument("--reach", default="cloud", choices=["cloud", "local_device"],
                     help="Where the agent runs (default: cloud)")
    sel.add_argument("--platform", default="any", help="User platform: windows, macos, ios, android, web, any")
    sel.add_argument("--requires", help="Comma-separated required functions, e.g. flight_search,flight_order_create")
    sel.add_argument("--approval-for", dest="approval_for",
                     help="Comma-separated side-effects that force approval, e.g. financial_charge,sends_message")
    sel.add_argument("--agent-setup-only", action="store_true",
                     help="Drop tools needing human-in-the-loop setup (paid signup, OAuth consent, approval)")
    sel.add_argument("--fallback-policy", choices=["capability_breadth"],
                     help="Explicit fallback when eligible candidate costs are not comparable")
    sel.add_argument("--json", action="store_true", help="Emit the structured decision as JSON")
    sel.add_argument("--limit", type=int, default=5, help="Maximum alternatives/rejections to print")
    sel.set_defaults(func=cmd_select)

    adaptive = sub.add_parser(
        "adaptive-select",
        help="EXPERIMENTAL: owner-aligned selection with freshness and VoI",
    )
    adaptive.add_argument("task")
    adaptive.add_argument("--taxonomy", required=True)
    adaptive.add_argument("--requires", help="Comma-separated required functions")
    adaptive.add_argument("--reach", default="cloud", choices=["cloud", "local_device"])
    adaptive.add_argument("--platform", default="any")
    adaptive.add_argument("--agent-setup-only", action="store_true")
    adaptive.add_argument("--explicit-tool", help="Owner-specified service_id to validate")
    adaptive.add_argument("--installed", help="Comma-separated installed service_ids")
    adaptive.add_argument("--authenticated", help="Comma-separated authenticated service_ids")
    adaptive.add_argument("--forbidden", help="Comma-separated forbidden service_ids")
    adaptive.add_argument("--forbidden-side-effects", help="Comma-separated blocked side effects")
    adaptive.add_argument("--max-risk", choices=["low", "medium", "high", "critical"], default="critical")
    adaptive.add_argument("--allow-unknown-risk", action="store_true")
    adaptive.add_argument("--non-reversible", action="store_true")
    adaptive.add_argument(
        "--interruption-cost",
        type=float,
        help="Learned/estimated cost of asking, in the same [-1,1] reward units; no guessed default",
    )
    adaptive.add_argument("--monthly-budget", type=float, help="Known owner budget for stable cost comparison")
    adaptive.add_argument("--budget-currency", default="USD")
    adaptive.add_argument("--latency-target-seconds", type=float)
    adaptive.add_argument(
        "--freshness-policy",
        choices=["require_fresh", "allow_stale", "allow_unknown"],
        default="require_fresh",
    )
    adaptive.add_argument("--policy", choices=["posterior_mean", "linucb", "thompson"], default="posterior_mean")
    adaptive.add_argument(
        "--preference-ledger",
        default=str(Path.home() / ".asm" / "owner-preferences.jsonl"),
        help="Owner-controlled local JSONL evidence; raw prompts are never written",
    )
    adaptive.add_argument("--json", action="store_true")
    adaptive.add_argument("--limit", type=int, default=5)
    adaptive.set_defaults(func=cmd_adaptive_select)

    discover = sub.add_parser(
        "discover",
        help="Search federated MCP discovery metadata (not selection-ready ASM facts)",
    )
    discover.add_argument("query")
    discover.add_argument("--registry-url", default="https://registry.modelcontextprotocol.io")
    discover.add_argument("--limit", type=int, default=10)
    discover.add_argument("--max-pages", type=int, default=3)
    discover.add_argument("--timeout", type=float, default=15)
    discover.add_argument("--all-versions", action="store_true")
    discover.add_argument("--json", action="store_true")
    discover.set_defaults(func=cmd_discover)

    preference = sub.add_parser(
        "preference",
        help="Agent integration hooks for a local owner preference ledger",
    )
    preference_sub = preference.add_subparsers(dest="preference_command", required=True)
    pref_default = str(Path.home() / ".asm" / "owner-preferences.jsonl")

    choice = preference_sub.add_parser("record-choice", help="Record an owner correction or explicit pairwise choice")
    choice.add_argument("--ledger", default=pref_default)
    choice.add_argument("--chosen-id", required=True)
    choice.add_argument("--rejected-id", required=True)
    choice.add_argument("--chosen-features", required=True, type=_feature_json)
    choice.add_argument("--rejected-features", required=True, type=_feature_json)
    choice.add_argument("--context-tags")
    choice.add_argument("--non-reversible", action="store_true")
    choice.set_defaults(func=cmd_preference_choice)

    outcome = preference_sub.add_parser("record-outcome", help="Record observed success or failure for the selected tool")
    outcome.add_argument("--ledger", default=pref_default)
    outcome.add_argument("--service-id", required=True)
    outcome.add_argument("--features", required=True, type=_feature_json)
    outcome.add_argument("--reward", required=True, type=float)
    outcome.add_argument("--context-tags")
    outcome.add_argument("--non-reversible", action="store_true")
    outcome.set_defaults(func=cmd_preference_outcome)

    show = preference_sub.add_parser("show", help="Show posterior summary without exposing raw owner history")
    show.add_argument("--ledger", default=pref_default)
    show.set_defaults(func=cmd_preference_show)

    score = sub.add_parser("score", help="LEGACY BASELINE: rank services with static TOPSIS preferences")
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

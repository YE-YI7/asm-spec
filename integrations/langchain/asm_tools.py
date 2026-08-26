"""ASM LangChain Tools — Query ASM Registry 并对比Service。

提供三个 LangChain BaseTool 实现:
  - ASMToolSelectorTool: agent 工具选择 — 任务 → 资格门(可调用/许可/适配) → 价值排序 → 选定工具 + 风险/审批策略
  - ASMRegistryTool:   自然语言Query → filter + TOPSIS Scoring → top 3 结果
  - ASMComparisonTool: 两个 service_id 的 manifest 对比表
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, ClassVar, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# ── 将 repo root + scorer 加入 sys.path，复用选择/Scoring逻辑 ──────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCORER_DIR = str(_REPO_ROOT / "scorer")
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if _SCORER_DIR not in sys.path:
    sys.path.insert(0, _SCORER_DIR)

from library_select import select as _library_select  # noqa: E402

from scorer import (  # noqa: E402
    Constraints,
    Preferences,
    ScoredService,
    load_manifests,
    parse_manifest,
    select_service,
)

# ── 默认 manifests 目录 ─────────────────────────────────
_DEFAULT_MANIFESTS_DIR = str(
    Path(__file__).resolve().parent.parent.parent / "manifests"
)


# ============================================================
# 自然语言Query解析
# ============================================================

# taxonomy 关键词映射
_TAXONOMY_KEYWORDS: dict[str, list[str]] = {
    "ai.llm.chat": ["llm", "chat", "language model", "gpt", "claude", "gemini", "text generation", "对话", "聊天"],
    "ai.llm.embedding": ["embedding", "向量", "vector", "嵌入"],
    "ai.vision.image_generation": ["image", "图片", "图像", "text-to-image", "dall-e", "flux", "imagen", "生图"],
    "ai.audio.tts": ["tts", "text-to-speech", "语音合成", "speech synthesis"],
    "ai.audio.stt": ["stt", "speech-to-text", "语音识别", "transcription"],
    "ai.video.generation": ["video", "视频", "sora", "veo", "kling"],
    "ai.compute.gpu": ["gpu", "compute", "算力"],
}

# 偏好关键词
_PREFERENCE_KEYWORDS: dict[str, str] = {
    "cheap": "cost", "cheapest": "cost", "budget": "cost", "affordable": "cost",
    "便宜": "cost", "低价": "cost", "省钱": "cost", "经济": "cost",
    "best": "quality", "quality": "quality", "accurate": "quality", "最好": "quality",
    "高质量": "quality", "精确": "quality",
    "fast": "speed", "fastest": "speed", "quick": "speed", "low latency": "speed",
    "快": "speed", "低延迟": "speed", "速度": "speed",
    "reliable": "reliability", "stable": "reliability", "稳定": "reliability",
    "可靠": "reliability",
}


def _parse_natural_query(query: str) -> tuple[Constraints, Preferences]:
    """从自然语言Query中解析出 Constraints 和 Preferences。"""
    query_lower = query.lower()

    # 1. 推断 taxonomy
    taxonomy = None
    for tax, keywords in _TAXONOMY_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                taxonomy = tax
                break
        if taxonomy:
            break

    # 2. 推断偏好方向
    emphasis = None
    for kw, dim in _PREFERENCE_KEYWORDS.items():
        if kw in query_lower:
            emphasis = dim
            break

    # 3. 解析数值约束
    max_cost = None
    cost_match = re.search(r"(?:cost|price|价格)\s*[<≤]\s*\$?([\d.]+)", query_lower)
    if cost_match:
        max_cost = float(cost_match.group(1))

    max_latency = None
    lat_match = re.search(r"(?:latency|延迟)\s*[<≤]\s*([\d.]+)\s*(?:s|秒|ms)?", query_lower)
    if lat_match:
        val = float(lat_match.group(1))
        if "ms" in query_lower[lat_match.start():lat_match.end() + 5]:
            val /= 1000
        max_latency = val

    # 4. 构建 Constraints
    constraints = Constraints(
        required_taxonomy=taxonomy,
        max_cost=max_cost,
        max_latency_s=max_latency,
    )

    # 5. 构建 Preferences（根据偏好方向调整Weight）
    if emphasis == "cost":
        prefs = Preferences(cost=0.55, quality=0.25, speed=0.10, reliability=0.10)
    elif emphasis == "quality":
        prefs = Preferences(cost=0.15, quality=0.55, speed=0.15, reliability=0.15)
    elif emphasis == "speed":
        prefs = Preferences(cost=0.15, quality=0.25, speed=0.50, reliability=0.10)
    elif emphasis == "reliability":
        prefs = Preferences(cost=0.15, quality=0.25, speed=0.10, reliability=0.50)
    else:
        prefs = Preferences(cost=0.30, quality=0.35, speed=0.20, reliability=0.15)

    return constraints, prefs


# ============================================================
# 格式化输出
# ============================================================

def _format_scored_service(r: ScoredService, index: int) -> str:
    """将 ScoredService 格式化为可读字符串。"""
    svc = r.service
    lines = [
        f"#{index} {svc.display_name}",
        f"  Service ID : {svc.service_id}",
        f"  Taxonomy   : {svc.taxonomy}",
        f"  Score      : {r.total_score:.4f}",
        f"  Breakdown  : cost={r.breakdown.get('cost', 0):.2f}, "
        f"quality={r.breakdown.get('quality', 0):.2f}, "
        f"speed={r.breakdown.get('speed', 0):.2f}, "
        f"reliability={r.breakdown.get('reliability', 0):.2f}",
        f"  Cost/unit  : ${svc.cost_per_unit:.6f}",
        f"  Quality    : {svc.quality_score:.3f}",
        f"  Latency p50: {svc.latency_seconds:.2f}s",
        f"  Uptime     : {svc.uptime:.3f}",
    ]
    if r.reasoning:
        lines.append(f"  Reasoning  : {r.reasoning}")
    return "\n".join(lines)


def _format_comparison_table(manifests: list[dict]) -> str:
    """生成两个或多个 manifest 的对比表。"""
    if len(manifests) < 2:
        return "至少需要 2 个Service才能对比。"

    # 对比维度
    rows: list[tuple[str, list[str]]] = []
    names = [m.get("display_name", m["service_id"]) for m in manifests]

    rows.append(("Service ID", [m["service_id"] for m in manifests]))
    rows.append(("Taxonomy", [m.get("taxonomy", "—") for m in manifests]))
    rows.append(("Provider", [m.get("provider", {}).get("name", "—") for m in manifests]))

    # Pricing
    def _cost_str(m: dict) -> str:
        dims = m.get("pricing", {}).get("billing_dimensions", [])
        if not dims:
            return "—"
        parts = []
        for d in dims:
            parts.append(f"${d['cost_per_unit']}/{d['unit']} ({d['dimension']})")
        return " + ".join(parts)

    rows.append(("Pricing", [_cost_str(m) for m in manifests]))

    # Batch discount
    rows.append(("Batch discount", [
        f"{m.get('pricing', {}).get('batch_discount', 0) * 100:.0f}%"
        if m.get("pricing", {}).get("batch_discount") else "—"
        for m in manifests
    ]))

    # Quality
    def _quality_str(m: dict) -> str:
        metrics = m.get("quality", {}).get("metrics", [])
        if not metrics:
            return "—"
        q = metrics[0]
        return f"{q['name']}={q['score']} ({q.get('scale', '')})"

    rows.append(("Quality", [_quality_str(m) for m in manifests]))

    # Leaderboard
    def _lb_str(m: dict) -> str:
        lb = m.get("quality", {}).get("leaderboard_rank")
        if not lb:
            return "—"
        return f"#{lb['rank']}/{lb['total']} on {lb['name']}"

    rows.append(("Leaderboard", [_lb_str(m) for m in manifests]))

    # SLA
    rows.append(("Latency p50", [m.get("sla", {}).get("latency_p50", "—") for m in manifests]))
    rows.append(("Latency p99", [m.get("sla", {}).get("latency_p99", "—") for m in manifests]))
    rows.append(("Uptime", [
        f"{m.get('sla', {}).get('uptime', 0) * 100:.1f}%"
        if m.get("sla", {}).get("uptime") else "—"
        for m in manifests
    ]))
    rows.append(("Rate limit", [m.get("sla", {}).get("rate_limit", "—") for m in manifests]))

    # Payment
    rows.append(("Payment methods", [
        ", ".join(m.get("payment", {}).get("methods", [])) or "—"
        for m in manifests
    ]))
    rows.append(("Auth type", [m.get("payment", {}).get("auth_type", "—") for m in manifests]))

    # Receipt support
    rows.append(("Receipt endpoint", [
        "✅ Yes" if m.get("receipt_endpoint") else "—"
        for m in manifests
    ]))

    # 构建 Markdown 表格
    header = "| Dimension | " + " | ".join(names) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(names)) + " |"
    body_lines = []
    for dim, vals in rows:
        body_lines.append(f"| {dim} | " + " | ".join(vals) + " |")

    return "\n".join([header, sep] + body_lines)


# ============================================================
# ASMToolSelectorTool — agent 工具选择 (library/)
# ============================================================

class ASMToolSelectorInput(BaseModel):
    """ASMToolSelectorTool 的输入 schema。"""
    task: str = Field(
        description="Natural-language description of the task the agent must perform, "
        "e.g. 'find and book a refundable flight' or 'store a study plan with daily reminders'."
    )
    taxonomy: Optional[str] = Field(
        default=None,
        description="Optional ASM taxonomy to scope candidates, e.g. 'tool.booking.travel', "
        "'tool.productivity.task_management', 'tool.data.real_estate'.",
    )
    agent_reach: str = Field(
        default="cloud",
        description="Where this agent runs: 'cloud' (remote/headless) or 'local_device' "
        "(on the user's own machine — required to drive local-only tools).",
    )
    user_platform: str = Field(
        default="any",
        description="The user's platform: windows, macos, ios, android, web, or any.",
    )
    required_functions: str = Field(
        default="",
        description="Comma-separated capability names the tool must have, "
        "e.g. 'flight_search,flight_order_create' or 'reminders,recurring_tasks'.",
    )
    require_approval_for: str = Field(
        default="financial_charge,sends_message,executes_code",
        description="Comma-separated side-effects that force approval before invocation.",
    )
    require_agent_completable_setup: bool = Field(
        default=False,
        description="If true, drop tools whose onboarding needs a human (paid signup, "
        "OAuth consent, manual approval) — keep only tools usable unattended right now.",
    )


class ASMToolSelectorTool(BaseTool):
    """从 ASM tool-value library 中为任务选择工具。

    资格门(能否调用 / 是否许可 / 平台与能力适配) → 成本排序 →
    返回选定工具 + 操作策略(risk / approval / side-effects),供调用方
    在执行前做审批闸口。
    """

    name: str = "asm_tool_selector"
    description: str = (
        "Pick the right TOOL (real product/API, not a model) for an agent task from the "
        "ASM tool-value library. Filters out tools the agent cannot drive (GUI-only, "
        "local-only, ToS-forbidden, missing capabilities), ranks the rest by cost, and "
        "returns the pick with its risk class, approval requirement, and side effects. "
        "Use before invoking any external tool on a user's behalf."
    )
    args_schema: Type[BaseModel] = ASMToolSelectorInput

    def _run(
        self,
        task: str,
        taxonomy: Optional[str] = None,
        agent_reach: str = "cloud",
        user_platform: str = "any",
        required_functions: str = "",
        require_approval_for: str = "financial_charge,sends_message,executes_code",
        require_agent_completable_setup: bool = False,
    ) -> str:
        result = _library_select(
            task,
            taxonomy=taxonomy,
            agent_reach=agent_reach,
            user_platform=user_platform,
            required_functions=[f.strip() for f in required_functions.split(",") if f.strip()],
            require_approval_for=[s.strip() for s in require_approval_for.split(",") if s.strip()],
            require_agent_completable_setup=require_agent_completable_setup,
        )
        sel = result["selected"]
        if not sel:
            lines = [
                f"No selection for: {task}",
                f"Status: {result['selection_status']}",
                f"Reason: {result['reason']}",
            ]
            if result["alternatives"]:
                lines.append("Eligible candidates needing comparable cost facts:")
                lines += [
                    f"  - {a['display_name']}: {a['cost_estimate']['status']} cost"
                    for a in result["alternatives"][:6]
                ]
            lines.append("Rejected candidates:")
            lines += [f"  - {r['service']}: {r['reason']}" for r in result["rejected"]]
            return "\n".join(lines)

        lines = [
            f"Selected tool: {sel['display_name']} ({sel['service_id']})",
            (f"  cost: ${sel['monthly_cost_usd']}/mo"
             if sel["monthly_cost_usd"] is not None
             else f"  cost: {sel['cost_estimate']['status']} (workload facts required)")
            + f" | interface: {sel['interface']} | reach: {sel['reach']}",
            f"  risk_class: {result['risk_class']} | approval_required: {result['approval_required']}",
            f"  side_effects: {', '.join(result['side_effects']) or 'none declared'}",
        ]
        if sel.get("agent_completable_setup") is not None:
            lines.append(
                f"  setup: agent_completable={sel['agent_completable_setup']}, "
                f"requires={sel.get('setup_requires', [])}"
            )
        lines.append(f"  reason: {result['reason']}")
        if result["alternatives"]:
            lines.append("Alternatives: " + ", ".join(
                (f"{a['display_name']} (${a['monthly_cost_usd']}/mo)"
                 if a["monthly_cost_usd"] is not None
                 else f"{a['display_name']} ({a['cost_estimate']['status']} cost)")
                for a in result["alternatives"][:4]))
        if result["rejected"]:
            lines.append("Filtered out:")
            lines += [f"  - {r['service']}: {r['reason']}" for r in result["rejected"][:6]]
        return "\n".join(lines)


# ============================================================
# ASMRegistryTool
# ============================================================

class ASMRegistryInput(BaseModel):
    """ASMRegistryTool 的输入 schema。"""
    query: str = Field(
        description="Natural language query describing what kind of AI service you need. "
        "Examples: 'cheapest LLM for chat', 'best image generation service', "
        "'fast text-to-speech', 'reliable embedding model'"
    )


class ASMRegistryTool(BaseTool):
    """Query ASM Registry，返回符合条件的 top 3 Service列表。

    解析自然语言Query，Load本地 manifests，
    使用 scorer.py 的 filter + TOPSIS 逻辑Scoring排序。
    """

    name: str = "asm_registry"
    description: str = (
        "Query the ASM registry to find AI services matching criteria. "
        "Input a natural language query describing your needs (e.g., "
        "'cheapest LLM', 'best image generation', 'fast TTS'). "
        "Returns top 3 ranked services with scores and reasoning."
    )
    args_schema: Type[BaseModel] = ASMRegistryInput

    manifests_dir: str = _DEFAULT_MANIFESTS_DIR
    top_k: int = 3

    # 缓存已Load的 manifests
    _manifests_cache: ClassVar[dict[str, list[dict]]] = {}

    def _load_manifests(self) -> list[dict]:
        """Load并缓存 manifests。"""
        if self.manifests_dir not in self._manifests_cache:
            self._manifests_cache[self.manifests_dir] = load_manifests(self.manifests_dir)
        return self._manifests_cache[self.manifests_dir]

    def _run(self, query: str) -> str:
        """执行Query：解析 → 过滤 → TOPSIS Scoring → 返回 top K。"""
        manifests = self._load_manifests()
        if not manifests:
            return f"Error: 在 {self.manifests_dir} 中未找到 .asm.json 文件。"

        # 解析自然语言Query
        constraints, preferences = _parse_natural_query(query)

        # 使用 scorer.py 的 select_service 进行 filter + TOPSIS
        results = select_service(
            manifests,
            constraints=constraints,
            preferences=preferences,
            method="topsis",
        )

        if not results:
            # 放宽约束重试（移除 taxonomy 限制）
            relaxed = Constraints(
                max_cost=constraints.max_cost,
                max_latency_s=constraints.max_latency_s,
                min_uptime=constraints.min_uptime,
            )
            results = select_service(
                manifests,
                constraints=relaxed,
                preferences=preferences,
                method="topsis",
            )
            if not results:
                return (
                    f"未找到匹配的Service。\n"
                    f"Query: {query}\n"
                    f"约束: taxonomy={constraints.required_taxonomy}, "
                    f"max_cost={constraints.max_cost}, "
                    f"max_latency={constraints.max_latency_s}s\n"
                    f"total有 {len(manifests)} 个Service可用。"
                )

        # 取 top K
        top_results = results[: self.top_k]

        # 格式化输出
        lines = [
            f"ASM Registry Query结果 (query: \"{query}\")",
            f"total {len(results)} 个Service匹配，展示 Top {len(top_results)}:",
            f"Scoring方法: TOPSIS | 偏好Weight: cost={preferences.cost}, "
            f"quality={preferences.quality}, speed={preferences.speed}, "
            f"reliability={preferences.reliability}",
            "",
        ]

        for i, r in enumerate(top_results, 1):
            lines.append(_format_scored_service(r, i))
            lines.append("")

        return "\n".join(lines)


# ============================================================
# ASMComparisonTool
# ============================================================

class ASMComparisonInput(BaseModel):
    """ASMComparisonTool 的输入 schema。"""
    service_ids: str = Field(
        description="Comma-separated service IDs to compare. "
        "Example: 'openai/gpt-4o@2024-11-20, anthropic/claude-sonnet-4@4.0'"
    )


class ASMComparisonTool(BaseTool):
    """对比两个或多个Service的 manifest 差异。"""

    name: str = "asm_comparison"
    description: str = (
        "Compare two or more ASM services side by side. "
        "Input comma-separated service_ids. "
        "Returns a comparison table with pricing, quality, SLA, and payment info."
    )
    args_schema: Type[BaseModel] = ASMComparisonInput

    manifests_dir: str = _DEFAULT_MANIFESTS_DIR

    # 复用 ASMRegistryTool 的缓存
    _manifests_cache: ClassVar[dict[str, list[dict]]] = {}

    def _load_manifests_map(self) -> dict[str, dict]:
        """Load manifests 并构建 service_id → manifest 映射。"""
        if self.manifests_dir not in self._manifests_cache:
            self._manifests_cache[self.manifests_dir] = load_manifests(self.manifests_dir)
        return {m["service_id"]: m for m in self._manifests_cache[self.manifests_dir]}

    def _run(self, service_ids: str) -> str:
        """输入逗号分隔的 service_id，输出对比表。"""
        ids = [s.strip() for s in service_ids.split(",") if s.strip()]

        if len(ids) < 2:
            return "请提供至少 2 个 service_id（逗号分隔）。"

        manifest_map = self._load_manifests_map()

        found: list[dict] = []
        not_found: list[str] = []
        for sid in ids:
            if sid in manifest_map:
                found.append(manifest_map[sid])
            else:
                not_found.append(sid)

        if len(found) < 2:
            available = "\n".join(f"  • {k}" for k in sorted(manifest_map.keys()))
            return (
                f"至少需要 2 个有效的 service_id 进行对比。\n"
                f"未找到: {', '.join(not_found)}\n\n"
                f"可用的 service_id:\n{available}"
            )

        result = _format_comparison_table(found)

        if not_found:
            result += f"\n\n⚠️ 未找到: {', '.join(not_found)}"

        return result

"""LangChain adapter for deterministic ASM selection.

The tool exposes a short model-facing summary and keeps the complete structured
decision in ``ToolMessage.artifact``.  Selection Receipts are produced by the
canonical ASM selector; this adapter never reconstructs a receipt by parsing
human-readable tool output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from asm_protocol.selection import select


class ASMToolSelectorInput(BaseModel):
    """Structured pre-call constraints for the ASM selector."""

    task: str = Field(
        description=(
            "Audit text describing the task. The deterministic selector does not "
            "infer constraints from this text; provide taxonomy or required_functions."
        )
    )
    taxonomy: str | None = Field(
        default=None,
        description="Optional ASM taxonomy used to scope candidates.",
    )
    agent_reach: str = Field(
        default="cloud",
        description="Where the agent runs: cloud or local_device.",
    )
    user_platform: str = Field(
        default="any",
        description="User platform: windows, macos, ios, android, web, or any.",
    )
    required_functions: str = Field(
        default="",
        description="Comma-separated capabilities every eligible tool must expose.",
    )
    require_approval_for: str = Field(
        default="financial_charge,sends_message,executes_code",
        description="Comma-separated side effects that require approval before use.",
    )
    require_agent_completable_setup: bool = Field(
        default=False,
        description="Drop tools whose setup cannot be completed by the agent.",
    )
    monthly_units: dict[str, float] = Field(
        default_factory=dict,
        description="Optional expected monthly usage keyed by billing dimension.",
    )
    amortization_months: int | None = Field(
        default=None,
        ge=1,
        description="Months over which one-time purchases should be amortized.",
    )
    fallback_policy: Literal["capability_breadth"] | None = Field(
        default=None,
        description=(
            "Explicit fallback when eligible costs are not comparable. Omit it to "
            "receive needs_cost_facts instead of a guessed winner."
        ),
    )
    selection_profile: Literal["current", "legacy-0.5.2"] = Field(
        default="current",
        description=(
            "Use current for v0.6 cost-safe selection. Use legacy-0.5.2 only "
            "when reproducing the frozen Selection Receipt v0.1 contract."
        ),
    )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _content_for(decision: dict[str, Any]) -> str:
    selected = decision["selected"]
    if selected is None:
        lines = [
            f"No selection for: {decision['task']}",
            f"Status: {decision['selection_status']}",
            f"Reason: {decision['reason']}",
        ]
        if decision["alternatives"]:
            lines.append("Eligible candidates needing comparable cost facts:")
            lines.extend(
                f"  - {candidate['display_name']}: "
                f"{candidate['cost_estimate']['status']} cost"
                for candidate in decision["alternatives"][:6]
            )
        if decision["rejected"]:
            lines.append("Rejected candidates:")
            lines.extend(
                f"  - {candidate['service']}: {candidate['reason']}"
                for candidate in decision["rejected"][:6]
            )
    else:
        cost = (
            f"${selected['monthly_cost_usd']}/mo"
            if selected["monthly_cost_usd"] is not None
            else f"{selected['cost_estimate']['status']} (workload facts required)"
        )
        lines = [
            f"Selected tool: {selected['display_name']} ({selected['service_id']})",
            f"  cost: {cost} | interface: {selected['interface']} | reach: {selected['reach']}",
            (
                f"  risk_class: {decision['risk_class']} | "
                f"approval_required: {decision['approval_required']}"
            ),
            f"  side_effects: {', '.join(decision['side_effects']) or 'none declared'}",
            f"  reason: {decision['reason']}",
        ]
        if decision["alternatives"]:
            lines.append(
                "Alternatives: "
                + ", ".join(
                    candidate["display_name"]
                    for candidate in decision["alternatives"][:4]
                )
            )
        if decision["rejected"]:
            lines.append("Filtered out:")
            lines.extend(
                f"  - {candidate['service']}: {candidate['reason']}"
                for candidate in decision["rejected"][:6]
            )

    if "receipt" in decision:
        lines.append(
            "Selection Receipt v0.1 is attached as an unsigned audit artifact; "
            "it is not execution authorization."
        )
    elif decision.get("receipt_unavailable_reason"):
        lines.append(
            "No Selection Receipt was issued: "
            + decision["receipt_unavailable_reason"]
        )
    return "\n".join(lines)


class ASMToolSelectorTool(BaseTool):
    """Select an eligible service without executing or authorizing it."""

    name: str = "asm_tool_selector"
    description: str = (
        "Select a service from structured ASM facts before invocation. The caller "
        "must supply a taxonomy or required functions; task text is audit context, "
        "not an inferred policy. The tool never executes or authorizes the result."
    )
    args_schema: type[BaseModel] = ASMToolSelectorInput
    response_format: Literal["content", "content_and_artifact"] = (
        "content_and_artifact"
    )

    def _run(
        self,
        task: str,
        taxonomy: str | None = None,
        agent_reach: str = "cloud",
        user_platform: str = "any",
        required_functions: str = "",
        require_approval_for: str = (
            "financial_charge,sends_message,executes_code"
        ),
        require_agent_completable_setup: bool = False,
        monthly_units: dict[str, float] | None = None,
        amortization_months: int | None = None,
        fallback_policy: Literal["capability_breadth"] | None = None,
        selection_profile: Literal["current", "legacy-0.5.2"] = "current",
    ) -> tuple[str, dict[str, Any]]:
        workload = None
        if monthly_units or amortization_months is not None:
            workload = {
                "monthly_units": monthly_units or {},
                "amortization_months": amortization_months,
            }

        receipt_representable = (
            selection_profile == "legacy-0.5.2"
            and workload is None
            and fallback_policy is None
        )
        decision = select(
            task,
            taxonomy=taxonomy,
            agent_reach=agent_reach,
            user_platform=user_platform,
            required_functions=_csv(required_functions),
            require_approval_for=_csv(require_approval_for),
            require_agent_completable_setup=require_agent_completable_setup,
            workload=workload,
            fallback_policy=fallback_policy,
            selection_profile=selection_profile,
            receipt=receipt_representable,
        )
        if not receipt_representable:
            decision["receipt_unavailable_reason"] = (
                "Selection Receipt v0.1 is frozen to selection_profile=legacy-0.5.2 "
                "without workload or fallback_policy; the structured tool artifact "
                "is authoritative for this decision."
            )
        return _content_for(decision), decision


class ASMReceiptCallback(BaseCallbackHandler):
    """Persist exact Selection Receipts from LangChain tool artifacts.

    The callback ignores strings and malformed artifacts. It never creates a
    second receipt representation or claims that an unsigned receipt is a
    verifiable credential.
    """

    def __init__(self, output_dir: str = "./receipts", verbose: bool = True):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.verbose = verbose

    @staticmethod
    def _receipt_from_output(output: Any) -> dict[str, Any] | None:
        artifact = getattr(output, "artifact", None)
        if artifact is None and isinstance(output, tuple) and len(output) == 2:
            artifact = output[1]
        if not isinstance(artifact, dict):
            return None
        receipt = artifact.get("receipt")
        if not isinstance(receipt, dict):
            return None
        if (
            receipt.get("receipt_type") != "selection"
            or receipt.get("receipt_version") != "0.1"
            or not receipt.get("selection_id")
        ):
            return None
        return receipt

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        receipt = self._receipt_from_output(output)
        if receipt is None:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"selection_{receipt['selection_id']}.json"
        path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if self.verbose:
            print(f"ASM Selection Receipt saved: {path}")


__all__ = ["ASMReceiptCallback", "ASMToolSelectorInput", "ASMToolSelectorTool"]

"""Real A2A SDK transport validation for the ASM experience-event draft.

The agents are deterministic local fixtures. The HTTP discovery, JSON-RPC task
lifecycle, Agent Cards, Tasks, Artifacts, and caller signatures are real. This
does not validate external agents, market demand, or production security.
"""

from __future__ import annotations

import asyncio
import base64
import json
import socket
from collections.abc import Callable
from importlib.metadata import version
from typing import Any

import httpx
import uvicorn
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import (
    get_artifact_text,
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import Role, SendMessageRequest, Task, TaskState
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from a2a_experience_validation import (
    _canonical_digest,
    event_from_a2a,
    select_with_evidence,
    summarize,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from google.protobuf.json_format import MessageToDict
from starlette.applications import Starlette


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_event(event: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    signed = json.loads(json.dumps(event))
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    signed["evaluator"]["id"] = "urn:asm:ed25519:" + _canonical_digest(
        _b64url(public_bytes)
    ).split(":", 1)[1]
    signed["evaluator"]["public_key"] = _b64url(public_bytes)
    signature = private_key.sign(_canonical_bytes(signed))
    signed["signature"] = {"alg": "Ed25519", "value": _b64url(signature)}
    return signed


def verify_event_signature(event: dict[str, Any]) -> None:
    unsigned = json.loads(json.dumps(event))
    signature = unsigned.pop("signature")
    if signature.get("alg") != "Ed25519":
        raise ValueError("unexpected signature algorithm")
    public_key = _b64url_decode(unsigned["evaluator"]["public_key"])
    Ed25519PublicKey.from_public_bytes(public_key).verify(
        _b64url_decode(signature["value"]), _canonical_bytes(unsigned)
    )


def _parse_numbers(text: str) -> list[int]:
    return [int(part.strip()) for part in text.split(",") if part.strip()]


class SumAgentExecutor(AgentExecutor):
    def __init__(self, transform: Callable[[int, int], int]) -> None:
        self._transform = transform
        self._calls = 0

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if context.current_task is None:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(TaskState.TASK_STATE_WORKING)
        numbers = _parse_numbers(get_message_text(context.message))
        expected = sum(numbers)
        self._calls += 1
        result = self._transform(expected, self._calls)
        await updater.add_artifact(
            parts=[new_text_part(text=str(result), media_type="text/plain")],
            name="sum-result",
        )
        await updater.update_status(TaskState.TASK_STATE_COMPLETED)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported in this fixture")


def _card(base_url: str, path: str, name: str) -> AgentCard:
    return AgentCard(
        name=name,
        description="Sums comma-separated integers for an objective A2A test.",
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=f"{base_url}{path}",
            )
        ],
        skills=[
            AgentSkill(
                id="integer-sum",
                name="Integer sum",
                description="Sum comma-separated integers.",
                input_modes=["text/plain"],
                output_modes=["text/plain"],
                tags=["objective-test", "arithmetic"],
            )
        ],
    )


def build_app(base_url: str) -> tuple[Starlette, dict[str, AgentCard]]:
    cards = {
        "stable-agent": _card(base_url, "/stable", "stable-agent"),
        "drifting-agent": _card(base_url, "/drifting", "drifting-agent"),
    }
    executors = {
        "stable-agent": SumAgentExecutor(lambda expected, _call: expected),
        "drifting-agent": SumAgentExecutor(
            lambda expected, _call: expected + 1 if expected % 2 else expected
        ),
    }
    paths = {"stable-agent": "/stable", "drifting-agent": "/drifting"}
    routes = []
    for name, card in cards.items():
        path = paths[name]
        handler = DefaultRequestHandler(
            agent_executor=executors[name],
            task_store=InMemoryTaskStore(),
            agent_card=card,
        )
        routes.extend(
            create_agent_card_routes(
                card, card_url=f"{path}{AGENT_CARD_WELL_KNOWN_PATH}"
            )
        )
        routes.extend(create_jsonrpc_routes(handler, rpc_url=path))
    return Starlette(routes=routes), cards


async def _wait_until_ready(base_url: str) -> None:
    async with httpx.AsyncClient() as http:
        for _ in range(100):
            try:
                response = await http.get(
                    f"{base_url}/stable{AGENT_CARD_WELL_KNOWN_PATH}"
                )
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.02)
    raise RuntimeError("local A2A server did not become ready")


async def _discover(base_url: str, path: str) -> AgentCard:
    async with httpx.AsyncClient() as http:
        resolver = A2ACardResolver(httpx_client=http, base_url=f"{base_url}{path}")
        return await resolver.get_agent_card()


async def _call(card: AgentCard, numbers: list[int]) -> Task:
    client = await create_client(
        agent=card,
        client_config=ClientConfig(streaming=False),
    )
    task = None
    try:
        request = SendMessageRequest(
            message=new_text_message(
                ",".join(str(number) for number in numbers), role=Role.ROLE_USER
            )
        )
        async for response in client.send_message(request):
            if response.WhichOneof("payload") == "task":
                task = response.task
    finally:
        await client.close()
    if task is None:
        raise RuntimeError("A2A client did not receive a Task")
    return task


def _task_result(task: Task) -> int:
    if task.status.state != TaskState.TASK_STATE_COMPLETED:
        raise ValueError(f"task did not complete: {task.status.state}")
    if not task.artifacts:
        raise ValueError("completed task has no artifact")
    return int(get_artifact_text(task.artifacts[-1]))


async def run_live_validation() -> dict[str, Any]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    app, _declared_cards = build_app(base_url)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    server_task = asyncio.create_task(server.serve())
    try:
        await _wait_until_ready(base_url)
        cards = {
            "stable-agent": await _discover(base_url, "/stable"),
            "drifting-agent": await _discover(base_url, "/drifting"),
        }
        signer_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        workloads = [[1, 2, 3], [5, 8], [-2, 7, 9], [10, 20], [4, 4, 4], [100, -3]]
        events = []
        task_ids = set()
        for name, card in cards.items():
            card_dict = MessageToDict(card)
            for index, numbers in enumerate(workloads):
                task = await _call(card, numbers)
                task_dict = MessageToDict(task)
                task_ids.add(task.id)
                passed = int(_task_result(task) == sum(numbers))
                event = event_from_a2a(
                    event_id=f"live-{name}-{index + 1}",
                    task=task_dict,
                    agent_card=card_dict,
                    configuration={
                        "agent": name,
                        "agent_card_version": card.version,
                        "fixture_revision": "1",
                    },
                    evaluator_id="pending-signature",
                    taxonomy="math.integer_sum",
                    passed=passed,
                    failed=1 - passed,
                    evidence_level="verified",
                    observed_at=f"2026-08-{20 + index:02d}T00:00:00Z",
                )
                signed = sign_event(event, signer_keys[index % len(signer_keys)])
                verify_event_signature(signed)
                events.append(signed)

        candidates = []
        summaries = {}
        for name, card in cards.items():
            card_dict = MessageToDict(card)
            configuration = {
                "agent": name,
                "agent_card_version": card.version,
                "fixture_revision": "1",
            }
            summary = summarize(
                events,
                agent_card_digest=_canonical_digest(card_dict),
                configuration_digest=_canonical_digest(configuration),
                taxonomy="math.integer_sum",
            )
            summaries[name] = summary
            candidates.append({"service_id": name, "summary": summary})

        selected = select_with_evidence(candidates)
        next_worker_numbers = [11, 2]
        selected_task = await _call(cards[selected], next_worker_numbers)
        task_ids.add(selected_task.id)
        selected_result_passed = _task_result(selected_task) == sum(next_worker_numbers)
        counterfactual_task = await _call(cards["drifting-agent"], next_worker_numbers)
        task_ids.add(counterfactual_task.id)
        counterfactual_failed = _task_result(counterfactual_task) != sum(
            next_worker_numbers
        )
        serialized_events = json.dumps(events, sort_keys=True)
        checks = {
            "two_agent_cards_discovered": len(cards) == 2,
            "fourteen_unique_a2a_tasks": len(task_ids) == 14,
            "twelve_signatures_verified": len(events) == 12,
            "raw_task_content_redacted": all(
                token not in serialized_events
                for token in ["secret prompt", '"parts"', '"artifacts"']
            ),
            "cross_agent_evidence_selects_stable": selected == "stable-agent",
            "next_worker_selected_call_passed": selected_result_passed,
            "unselected_failure_reproduced": counterfactual_failed,
            "drift_failures_observed": (
                summaries["drifting-agent"]["objective_pass_rate"]["estimate"]
                < summaries["stable-agent"]["objective_pass_rate"]["estimate"]
            ),
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "scope": "real A2A SDK transport with deterministic local agents",
            "a2a_sdk_version": version("a2a-sdk"),
            "protocol": "A2A 1.0 JSON-RPC over HTTP",
            "protocol_calls": len(task_ids),
            "evidence_events_before_reuse": len(events),
            "selected_for_next_worker": selected,
            "summaries": summaries,
            "checks": checks,
        }
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    result = asyncio.run(run_live_validation())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)

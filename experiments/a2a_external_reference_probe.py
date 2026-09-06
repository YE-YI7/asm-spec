"""Probe one public A2A endpoint through its declared and legacy JSON-RPC methods.

This performs two benign live requests. It is intentionally excluded from the
default test suite and should not be run repeatedly against third-party services.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest

ENDPOINT = "https://tasks.a2a-testbed.com"
CARD_PATH = "/.well-known/agent-card.json"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


async def _official_sdk_probe() -> dict[str, Any]:
    client = await create_client(
        ENDPOINT,
        client_config=ClientConfig(streaming=False),
    )
    try:
        request = SendMessageRequest(
            message=new_text_message(
                "ASM interoperability probe count: 2", role=Role.ROLE_USER
            )
        )
        async for response in client.send_message(request):
            return {"result": "pass", "payload": response.WhichOneof("payload")}
        return {"result": "fail", "error_type": "empty_response"}
    except Exception as exc:  # noqa: BLE001 - probe records the public error class
        return {
            "result": "fail",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        await client.close()


async def _legacy_wire_probe() -> dict[str, Any]:
    request_id = f"asm-probe-{uuid.uuid4()}"
    message_id = f"asm-message-{uuid.uuid4()}"
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "ASM interoperability probe count: 2",
                    }
                ],
            }
        },
    }
    async with httpx.AsyncClient(timeout=20) as http:
        response = await http.post(ENDPOINT, json=payload)
        response.raise_for_status()
        body = response.json()
    result = body.get("result") or {}
    state = (result.get("status") or {}).get("state")
    return {
        "result": "pass" if state == "TASK_STATE_COMPLETED" else "fail",
        "state": state,
        "task_id_digest": _digest(result.get("id")),
        "artifact_count": len(result.get("artifacts") or []),
    }


async def run_probe() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as http:
        response = await http.get(ENDPOINT + CARD_PATH)
        response.raise_for_status()
        card = response.json()
    interface = (card.get("supportedInterfaces") or [{}])[0]
    official = await _official_sdk_probe()
    legacy = await _legacy_wire_probe()
    mismatch = (
        interface.get("protocolBinding") == "JSONRPC"
        and interface.get("protocolVersion") == "1.0"
        and official["result"] == "fail"
        and official.get("error_type") == "MethodNotFoundError"
        and legacy["result"] == "pass"
    )
    return {
        "probe_status": "COMPLETE",
        "scope": "one public reference endpoint; two benign calls",
        "subject": {
            "endpoint": ENDPOINT,
            "agent_card_digest": _digest(card),
            "declared_interface": interface,
        },
        "checks": {
            "official_a2a_sdk_1_x": official,
            "legacy_message_send": legacy,
        },
        "observed_interface_mismatch": mismatch,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_probe()), indent=2, sort_keys=True))

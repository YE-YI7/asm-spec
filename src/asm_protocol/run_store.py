"""Private, idempotent local storage for ASM decision/outcome pairs."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import validate_contract
from .digests import digest_json

_FORBIDDEN_KEYS = {"api_key", "apikey", "authorization", "query", "secret", "token"}


def _assert_private_shape(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _FORBIDDEN_KEYS:
                raise ValueError(f"private run record rejects raw sensitive field {path}.{key}")
            _assert_private_shape(child, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for index, child in enumerate(value):
            _assert_private_shape(child, f"{path}[{index}]")


def store_run(
    directory: str | Path,
    *,
    decision: Mapping[str, Any],
    outcome: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
) -> Path:
    """Store one private run atomically; identical repeats are idempotent."""
    validate_contract("decision_receipt", decision)
    validate_contract("outcome_receipt", outcome)
    if outcome["decision_id"] != decision["decision_id"]:
        raise ValueError("outcome decision_id does not match decision")
    record = {
        "store_format": "asm-private-run/0.1",
        "decision": dict(decision),
        "outcome": dict(outcome),
        "observation": dict(observation) if observation is not None else None,
    }
    _assert_private_shape(record)
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    destination = root / f"{outcome['outcome_id']}.json"
    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if digest_json(existing) == digest_json(record):
            return destination
        raise FileExistsError(f"outcome_id already exists with different content: {outcome['outcome_id']}")

    temporary = root / f".{outcome['outcome_id']}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            existing = json.loads(destination.read_text(encoding="utf-8"))
            if digest_json(existing) != digest_json(record):
                raise FileExistsError(
                    f"outcome_id already exists with different content: {outcome['outcome_id']}"
                ) from None
        os.chmod(destination, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return destination


__all__ = ["store_run"]

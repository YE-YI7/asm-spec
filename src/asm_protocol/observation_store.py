"""Owner-scoped private outcome index for cooperating local workers."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import validate_contract
from .digests import digest_json


def _scope_directory(root: Path, owner_scope_id: str) -> Path:
    if not owner_scope_id:
        raise ValueError("owner_scope_id must be a non-empty opaque host identifier")
    return root / digest_json({"owner_scope_id": owner_scope_id}).removeprefix("sha256:")


def append_private_observation(
    directory: str | Path,
    *,
    owner_scope_id: str,
    worker_id: str,
    outcome: Mapping[str, Any],
) -> Path:
    """Persist a redacted outcome index visible only within one owner scope."""
    if not worker_id:
        raise ValueError("worker_id must be non-empty")
    validate_contract("outcome_receipt", outcome)
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    scope = _scope_directory(root, owner_scope_id)
    scope.mkdir(mode=0o700)
    os.chmod(scope, 0o700)
    record = {
        "store_format": "asm-private-observation/0.1",
        "worker_id": worker_id,
        "outcome_id": outcome["outcome_id"],
        "outcome_digest": digest_json(outcome),
        "decision_id": outcome["decision_id"],
        "request_commitment": outcome["request_commitment"],
        "interface_id": outcome["executed"]["interface_id"],
        "interface_digest": outcome["executed"]["interface_digest"],
        "ended_at": outcome["ended_at"],
        "transport_status": outcome["transport_status"],
        "tool_status": outcome["tool_status"],
    }
    destination = scope / f"{outcome['outcome_id']}.json"
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    temporary = scope / f".{outcome['outcome_id']}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != encoded:
                raise FileExistsError(f"observation already exists with different content: {outcome['outcome_id']}") from None
        os.chmod(destination, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return destination


def read_private_observations(
    directory: str | Path,
    *,
    owner_scope_id: str,
    interface_id: str | None = None,
    interface_digest: str | None = None,
) -> list[dict[str, Any]]:
    """Read only records in the caller-supplied owner scope and current interface version."""
    scope = _scope_directory(Path(directory).expanduser(), owner_scope_id)
    if not scope.exists():
        return []
    records = []
    for path in sorted(scope.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if interface_id is not None and record["interface_id"] != interface_id:
            continue
        if interface_digest is not None and record["interface_digest"] != interface_digest:
            continue
        records.append(record)
    return records


__all__ = ["append_private_observation", "read_private_observations"]

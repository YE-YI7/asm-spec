"""Opt-in, query-free local activation events for the search product funnel."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .digests import digest_json

STAGES = (
    "view",
    "install",
    "authorized_first_run",
    "second_day_use",
    "retained_project",
)
SUBJECT_KINDS = {"anonymous_session", "project"}


def record_activation_event(
    directory: str | Path,
    *,
    event_id: str,
    stage: str,
    occurred_at: str,
    subject_kind: str,
    subject_ref: str,
    telemetry_opt_in: bool = False,
) -> Path:
    """Record one local event; raw subject identifiers are never persisted."""
    if not telemetry_opt_in:
        raise PermissionError("activation telemetry is disabled until the host explicitly opts in")
    if stage not in STAGES:
        raise ValueError(f"unknown activation stage: {stage}")
    if subject_kind not in SUBJECT_KINDS:
        raise ValueError(f"unknown subject kind: {subject_kind}")
    if not event_id or not subject_ref:
        raise ValueError("event_id and subject_ref must be non-empty")
    datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    if stage in {"view", "install"} and subject_kind != "anonymous_session":
        raise ValueError(f"{stage} events require an anonymous_session subject")
    if stage in {"authorized_first_run", "second_day_use", "retained_project"} and subject_kind != "project":
        raise ValueError(f"{stage} events require a project subject")

    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    record = {
        "event_format": "asm-activation/0.1",
        "event_digest": digest_json({"event_id": event_id}),
        "stage": stage,
        "occurred_at": occurred_at,
        "subject_kind": subject_kind,
        "subject_digest": digest_json({"subject_kind": subject_kind, "subject_ref": subject_ref}),
        "contains_query": False,
        "upload": "local_only",
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    name = record["event_digest"].removeprefix("sha256:") + ".json"
    destination = root / name
    temporary = root / f".{name}.{uuid.uuid4().hex}.tmp"
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
                raise FileExistsError("event_id already exists with different content") from None
        os.chmod(destination, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return destination


def summarize_activation(directory: str | Path) -> dict[str, dict[str, int]]:
    """Return raw event and unique-subject counts without inferring conversion."""
    summary: dict[str, dict[str, Any]] = {
        stage: {"events": 0, "subjects": set()} for stage in STAGES
    }
    root = Path(directory).expanduser()
    if root.exists():
        for path in root.glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            stage = record.get("stage")
            if stage in summary:
                summary[stage]["events"] += 1
                summary[stage]["subjects"].add(record["subject_digest"])
    return {
        stage: {"events": values["events"], "unique_subjects": len(values["subjects"])}
        for stage, values in summary.items()
    }


__all__ = ["STAGES", "record_activation_event", "summarize_activation"]

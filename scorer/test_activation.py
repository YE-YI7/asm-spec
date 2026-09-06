from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from asm_protocol.activation import record_activation_event, summarize_activation


def test_activation_is_opt_in_local_and_does_not_store_raw_subject(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="explicitly opts in"):
        record_activation_event(
            tmp_path,
            event_id="event-1",
            stage="view",
            occurred_at="2026-09-06T01:00:00Z",
            subject_kind="anonymous_session",
            subject_ref="raw-session-id",
        )
    path = record_activation_event(
        tmp_path,
        event_id="event-1",
        stage="view",
        occurred_at="2026-09-06T01:00:00Z",
        subject_kind="anonymous_session",
        subject_ref="raw-session-id",
        telemetry_opt_in=True,
    )
    text = path.read_text(encoding="utf-8")
    assert "raw-session-id" not in text
    assert json.loads(text)["upload"] == "local_only"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_activation_summary_keeps_anonymous_and_project_stages_separate(tmp_path: Path) -> None:
    for event_id, stage, kind, subject in [
        ("view-1", "view", "anonymous_session", "session-a"),
        ("view-2", "view", "anonymous_session", "session-a"),
        ("run-1", "authorized_first_run", "project", "project-a"),
    ]:
        record_activation_event(
            tmp_path,
            event_id=event_id,
            stage=stage,
            occurred_at="2026-09-06T01:00:00Z",
            subject_kind=kind,
            subject_ref=subject,
            telemetry_opt_in=True,
        )
    summary = summarize_activation(tmp_path)
    assert summary["view"] == {"events": 2, "unique_subjects": 1}
    assert summary["authorized_first_run"] == {"events": 1, "unique_subjects": 1}
    assert summary["retained_project"] == {"events": 0, "unique_subjects": 0}


def test_stage_identity_boundary_is_enforced(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project subject"):
        record_activation_event(
            tmp_path,
            event_id="bad",
            stage="retained_project",
            occurred_at="2026-09-06T01:00:00Z",
            subject_kind="anonymous_session",
            subject_ref="session-a",
            telemetry_opt_in=True,
        )

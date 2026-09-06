"""Local-only intake for externally contributed search evaluation tasks."""

from __future__ import annotations

import json
import os
import re
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts import validate_contract
from .digests import digest_json

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FIELDS = {
    "contribution_id",
    "task_family",
    "coverage_tags",
    "language",
    "query",
    "answer",
    "reference_urls",
    "temporal_requirement",
    "cutoff",
    "permission",
}
_OPTIONAL_FIELDS = {"ground_truth_verified_at", "ground_truth_expires_at"}
_PERMISSION_FIELDS = {
    "evaluation_use_granted",
    "publish_commitments_granted",
    "submitter_has_authority",
    "contains_personal_data",
    "terms_version",
}
_TERMS_VERSION = "asm-search-evaluation-contribution-terms/0.1"


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _validate_permission(payload: Mapping[str, Any]) -> dict[str, Any]:
    permission = payload.get("permission")
    if not isinstance(permission, Mapping) or set(permission) != _PERMISSION_FIELDS:
        raise ValueError("permission must contain exactly the required consent fields")
    normalized = {key: permission[key] for key in sorted(_PERMISSION_FIELDS)}
    if normalized["terms_version"] != _TERMS_VERSION:
        raise ValueError(f"permission terms_version must equal {_TERMS_VERSION}")
    boolean_values = {key: value for key, value in normalized.items() if key != "terms_version"}
    if any(not isinstance(value, bool) for value in boolean_values.values()):
        raise TypeError("permission values must be booleans")
    if not normalized["evaluation_use_granted"]:
        raise ValueError("evaluation use permission is required")
    if not normalized["publish_commitments_granted"]:
        raise ValueError("permission to publish commitments is required")
    if not normalized["submitter_has_authority"]:
        raise ValueError("submitter authority confirmation is required")
    if normalized["contains_personal_data"]:
        raise ValueError("personal-data contributions are not accepted")
    return normalized


def _aware_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def commit_external_contribution(
    contribution: Mapping[str, Any],
    *,
    batch_id: str,
    split: str,
    received_at: str,
    committed_at: str,
    judge_profile: str,
) -> dict[str, dict[str, Any]]:
    """Build one public task commitment and its private, local-only source record."""
    unknown = set(contribution) - _FIELDS - _OPTIONAL_FIELDS
    missing = _FIELDS - set(contribution)
    if unknown or missing:
        raise ValueError(f"contribution fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    contribution_id = _required_text(contribution, "contribution_id")
    if not _ID.fullmatch(contribution_id) or not _ID.fullmatch(batch_id):
        raise ValueError("contribution_id and batch_id must be opaque safe identifiers")
    query = _required_text(contribution, "query")
    answer = _required_text(contribution, "answer")
    task_family = _required_text(contribution, "task_family")
    language = _required_text(contribution, "language")
    permission = _validate_permission(contribution)

    reference_urls = contribution.get("reference_urls")
    if not isinstance(reference_urls, list) or not reference_urls:
        raise ValueError("reference_urls must be a non-empty list")
    if any(not isinstance(url, str) or not url.strip() for url in reference_urls):
        raise TypeError("reference_urls must contain non-empty strings")
    normalized_urls = sorted(set(reference_urls))
    domains: set[str] = set()
    for url in normalized_urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("every reference URL must use HTTPS, contain a hostname, and omit credentials")
        domains.add(parsed.hostname.lower())

    coverage_tags = contribution.get("coverage_tags")
    if not isinstance(coverage_tags, list):
        raise TypeError("coverage_tags must be a list")
    minimum_sources = 2 if "multi_source_verification" in coverage_tags else 1
    if len(domains) < minimum_sources:
        raise ValueError(f"this task requires at least {minimum_sources} independent reference domains")

    ground_truth_ref = {"digest": digest_json({"answer": answer}), "disclosure": "private"}
    if "time_sensitive_fact" in coverage_tags:
        verified_at = _aware_timestamp(
            contribution.get("ground_truth_verified_at"), "ground_truth_verified_at"
        )
        expires_at = _aware_timestamp(
            contribution.get("ground_truth_expires_at"), "ground_truth_expires_at"
        )
        if expires_at <= verified_at:
            raise ValueError("ground_truth_expires_at must be later than ground_truth_verified_at")
        ground_truth_ref.update(
            {
                "verified_at": contribution["ground_truth_verified_at"],
                "expires_at": contribution["ground_truth_expires_at"],
            }
        )

    task_id_suffix = digest_json(
        {"batch_id": batch_id, "contribution_id": contribution_id}
    ).removeprefix("sha256:")[:20]
    public_task = {
        "contract_type": "search_evaluation_task",
        "contract_version": "0.1",
        "task_id": f"external-{task_id_suffix}",
        "task_family": task_family,
        "coverage_tags": coverage_tags,
        "split": split,
        "language": language,
        "query_ref": {"digest": digest_json({"query": query}), "disclosure": "private"},
        "source_provenance": {
            "kind": "external_contribution",
            "contribution_digest": digest_json({"contribution_id": contribution_id}),
            "batch_digest": digest_json({"batch_id": batch_id}),
            "private_payload_digest": digest_json({"contribution": contribution}),
            "permission_digest": digest_json({"permission": permission}),
            "reference_set_digest": digest_json({"reference_urls": normalized_urls}),
            "received_at": received_at,
        },
        "ground_truth_ref": ground_truth_ref,
        "checks": {
            "reference_domains": [],
            "domain_requirement": "none",
            "minimum_independent_sources": minimum_sources,
            "temporal_requirement": contribution["temporal_requirement"],
            "cutoff": contribution["cutoff"],
            "judge_profile": judge_profile,
        },
        "committed_at": committed_at,
    }
    validate_contract("search_evaluation_task", public_task)
    private_record = {
        "store_format": "asm-private-search-evaluation-contribution/0.1",
        "at_rest_protection": "filesystem-permissions-only-not-encrypted",
        "task_id": public_task["task_id"],
        "contribution": dict(contribution),
        "public_task_digest": digest_json(public_task),
    }
    return {"public_task": public_task, "private_record": private_record}


def verify_private_contribution(
    public_task: Mapping[str, Any], private_record: Mapping[str, Any]
) -> None:
    """Verify that a retained raw contribution is exactly the source of a public task."""
    validate_contract("search_evaluation_task", public_task)
    if private_record.get("task_id") != public_task.get("task_id"):
        raise ValueError("private contribution task_id does not match public task")
    if private_record.get("public_task_digest") != digest_json(public_task):
        raise ValueError("private contribution does not bind this public task")
    contribution = private_record.get("contribution")
    if not isinstance(contribution, Mapping):
        raise TypeError("private contribution payload must be an object")
    provenance = public_task["source_provenance"]
    if provenance.get("kind") != "external_contribution":
        raise ValueError("public task is not an external contribution")
    if provenance["private_payload_digest"] != digest_json({"contribution": contribution}):
        raise ValueError("private payload does not match its public commitment")
    if public_task["query_ref"]["digest"] != digest_json({"query": contribution.get("query")}):
        raise ValueError("private query does not match its public commitment")
    if public_task["ground_truth_ref"]["digest"] != digest_json({"answer": contribution.get("answer")}):
        raise ValueError("private answer does not match its public commitment")
    if "time_sensitive_fact" in contribution.get("coverage_tags", []) and (
        public_task["ground_truth_ref"].get("verified_at") != contribution.get(
            "ground_truth_verified_at"
        )
        or public_task["ground_truth_ref"].get("expires_at")
        != contribution.get(
            "ground_truth_expires_at"
        )
    ):
        raise ValueError("private ground-truth validity window does not match public task")
    permission = _validate_permission(contribution)
    if provenance["permission_digest"] != digest_json({"permission": permission}):
        raise ValueError("private permission does not match its public commitment")
    reference_urls = contribution.get("reference_urls")
    if not isinstance(reference_urls, list):
        raise TypeError("private reference_urls must be a list")
    if provenance["reference_set_digest"] != digest_json(
        {"reference_urls": sorted(set(reference_urls))}
    ):
        raise ValueError("private references do not match their public commitment")


def store_private_contribution(directory: str | Path, private_record: Mapping[str, Any]) -> Path:
    """Atomically retain one raw contribution with owner-only permissions."""
    task_id = _required_text(private_record, "task_id")
    if not _ID.fullmatch(task_id):
        raise ValueError("private contribution task_id is unsafe")
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    destination = root / f"{task_id}.json"
    record = dict(private_record)
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if digest_json(existing) == digest_json(record):
            return destination
        raise FileExistsError(f"task_id already exists with different private content: {task_id}")

    temporary = root / f".{task_id}.{uuid.uuid4().hex}.tmp"
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
                    f"task_id already exists with different private content: {task_id}"
                ) from None
        os.chmod(destination, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return destination


__all__ = [
    "commit_external_contribution",
    "store_private_contribution",
    "verify_private_contribution",
]

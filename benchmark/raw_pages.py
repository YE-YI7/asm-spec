"""Validation and attachment of raw provider-page snapshot bundles.

Snapshots are external research artifacts because provider text may be
copyrighted or mutable. The benchmark accepts a bundle only when every page is
hashed and every manifest fact used by a task is covered by an official page.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PROFILE = "toolselect-raw-pages/0.1"
MAX_CHARS_PER_SERVICE = 16_000
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class RawPageBundleError(ValueError):
    pass


def required_fact_paths(task: dict) -> set[str]:
    """Manifest paths that must be independently supported for this task."""
    ctx = task["context"]
    required = {
        "invocation.agent_operable",
        "invocation.reach",
        "invocation.platforms",
        "usage_terms.automation_allowed",
        "capabilities.functions",
    }
    if ctx.get("require_agent_completable_setup"):
        required.update({"invocation.agent_completable_setup", "invocation.setup_requires"})
    if task["type"] in {"cheapest_eligible", "governance"}:
        required.update({"pricing.billing_dimensions", "payment.methods"})
    governance = ctx.get("governance") or {}
    if "trains_on_user_data" in governance:
        required.add("data_governance.trains_on_user_data")
    if "exportable" in governance:
        required.add("data_governance.exportable")
    return required


def load_snapshot_bundle(path: str | Path) -> dict:
    bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    if bundle.get("profile") != PROFILE:
        raise RawPageBundleError(f"snapshot bundle profile must equal {PROFILE!r}")
    if not isinstance(bundle.get("services"), dict):
        raise RawPageBundleError("snapshot bundle services must be an object")
    if not isinstance(bundle.get("extraction_profile"), str):
        raise RawPageBundleError("snapshot bundle extraction_profile must be a string")
    return bundle


def bundle_digest(bundle: dict) -> str:
    canonical = json.dumps(
        bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def build_review_template(tasks: list[dict], manifests: list[dict]) -> dict:
    """Create a source-review checklist; it is intentionally not runnable yet."""
    by_id = {manifest["service_id"]: manifest for manifest in manifests}
    required_by_service: dict[str, set[str]] = {}
    for task in tasks:
        requirements = required_fact_paths(task)
        for service_id in task["candidates"]:
            required_by_service.setdefault(service_id, set()).update(requirements)

    services = {}
    for service_id in sorted(required_by_service):
        manifest = by_id.get(service_id, {})
        quality_urls = [
            metric.get("benchmark_url")
            for metric in (manifest.get("quality") or {}).get("metrics", [])
        ]
        suggested = [
            (manifest.get("provenance") or {}).get("source_url"),
            (manifest.get("invocation") or {}).get("docs_url"),
            (manifest.get("usage_terms") or {}).get("tos_url"),
            (manifest.get("payment") or {}).get("signup_url"),
            *quality_urls,
        ]
        services[service_id] = {
            "required_fact_paths": sorted(required_by_service[service_id]),
            "suggested_urls": list(dict.fromkeys(url for url in suggested if url)),
            "pages": [],
        }
    return {
        "profile": PROFILE,
        "extraction_profile": "visible-text-reviewed/0.1",
        "services": services,
    }


def attach_raw_pages(tasks: list[dict], bundle: dict) -> list[dict]:
    """Attach raw-page materials only when the full paired dataset is covered."""
    if bundle.get("profile") != PROFILE:
        raise RawPageBundleError(f"snapshot bundle profile must equal {PROFILE!r}")
    services = bundle.get("services")
    if not isinstance(services, dict):
        raise RawPageBundleError("snapshot bundle services must be an object")
    if not isinstance(bundle.get("extraction_profile"), str):
        raise RawPageBundleError("snapshot bundle extraction_profile must be a string")

    prepared_services = {}
    for service_id, service in services.items():
        pages = service.get("pages") if isinstance(service, dict) else None
        if not isinstance(pages, list) or not pages:
            raise RawPageBundleError(f"{service_id}: pages must be a non-empty array")
        covered, materials, service_chars = set(), [], 0
        for index, page in enumerate(pages):
            label = f"{service_id}: pages[{index}]"
            required_keys = {"source_url", "retrieved_at", "text", "text_sha256", "supports"}
            if not isinstance(page, dict) or not required_keys <= set(page):
                raise RawPageBundleError(f"{label}: missing required snapshot fields")
            if not str(page["source_url"]).startswith("https://"):
                raise RawPageBundleError(f"{label}: source_url must use https")
            if page.get("source_kind") != "official_provider":
                raise RawPageBundleError(
                    f"{label}: source_kind must equal 'official_provider'"
                )
            if not isinstance(page["retrieved_at"], str) or not _UTC_TIMESTAMP.fullmatch(
                page["retrieved_at"]
            ):
                raise RawPageBundleError(
                    f"{label}: retrieved_at must be UTC YYYY-MM-DDTHH:MM:SSZ"
                )
            text = page["text"]
            if not isinstance(text, str) or not text.strip():
                raise RawPageBundleError(f"{label}: text must be non-empty")
            observed = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
            if observed != page["text_sha256"]:
                raise RawPageBundleError(f"{label}: text_sha256 mismatch")
            if not isinstance(page["supports"], list):
                raise RawPageBundleError(f"{label}: supports must be an array")
            if not all(
                isinstance(path, str) and path for path in page["supports"]
            ):
                raise RawPageBundleError(
                    f"{label}: supports must contain fact-path strings"
                )
            service_chars += len(text)
            covered.update(page["supports"])
            materials.append({
                "source_url": page["source_url"],
                "retrieved_at": page["retrieved_at"],
                "text_sha256": page["text_sha256"],
                "text": text,
            })
        if service_chars > MAX_CHARS_PER_SERVICE:
            raise RawPageBundleError(
                f"{service_id}: {service_chars} page-text chars exceeds the "
                f"fixed {MAX_CHARS_PER_SERVICE}-char service budget"
            )
        prepared_services[service_id] = {
            "covered": covered,
            "material": {"service_id": service_id, "pages": materials},
        }

    missing = []
    for task in tasks:
        requirements = required_fact_paths(task)
        for service_id in task["candidates"]:
            prepared = prepared_services.get(service_id)
            absent = requirements if prepared is None else requirements - prepared["covered"]
            if absent:
                missing.append((task["task_id"], service_id, sorted(absent)))
    if missing:
        preview = "; ".join(
            f"{task_id}/{service_id}: {', '.join(paths)}"
            for task_id, service_id, paths in missing[:8]
        )
        raise RawPageBundleError(
            f"raw_pages coverage incomplete for {len(missing)} task/candidate pairs; {preview}"
        )

    digest = bundle_digest(bundle)
    for task in tasks:
        task["conditions"]["raw_pages"] = [
            prepared_services[service_id]["material"]
            for service_id in task["candidates"]
        ]
        task.setdefault("condition_provenance", {})["raw_pages"] = {
            "profile": PROFILE,
            "extraction_profile": bundle["extraction_profile"],
            "max_chars_per_service": MAX_CHARS_PER_SERVICE,
            "snapshot_bundle_digest": digest,
        }
    return tasks

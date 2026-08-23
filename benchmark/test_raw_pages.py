import hashlib

import pytest

from benchmark.raw_pages import (
    MAX_CHARS_PER_SERVICE,
    PROFILE,
    RawPageBundleError,
    attach_raw_pages,
    build_review_template,
)


def _page(text, supports):
    return {
        "source_url": "https://provider.example/docs",
        "source_kind": "official_provider",
        "retrieved_at": "2026-08-23T00:00:00Z",
        "text": text,
        "text_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
        "supports": supports,
    }


def _task():
    return {
        "task_id": "task-1",
        "type": "unique_eligible",
        "context": {
            "agent_reach": "cloud",
            "user_platform": "linux",
            "required_functions": ["search"],
            "require_agent_completable_setup": False,
        },
        "candidates": ["example/service@1"],
        "conditions": {"names_only": [], "asm": []},
    }


BASE_SUPPORT = [
    "invocation.agent_operable",
    "invocation.reach",
    "invocation.platforms",
    "usage_terms.automation_allowed",
    "capabilities.functions",
]


def test_attach_raw_pages_requires_complete_field_coverage():
    bundle = {
        "profile": PROFILE,
        "extraction_profile": "visible-text-reviewed/0.1",
        "services": {"example/service@1": {"pages": [_page("official text", BASE_SUPPORT)]}},
    }
    [task] = attach_raw_pages([_task()], bundle)
    assert task["conditions"]["raw_pages"][0]["service_id"] == "example/service@1"
    assert task["condition_provenance"]["raw_pages"]["snapshot_bundle_digest"].startswith(
        "sha256:"
    )


def test_attach_raw_pages_fails_closed_on_missing_fact_source():
    bundle = {
        "profile": PROFILE,
        "extraction_profile": "visible-text-reviewed/0.1",
        "services": {"example/service@1": {"pages": [_page("official text", [])]}},
    }
    with pytest.raises(RawPageBundleError, match="coverage incomplete"):
        attach_raw_pages([_task()], bundle)


def test_attach_raw_pages_rejects_tampered_snapshot_text():
    page = _page("original", BASE_SUPPORT)
    page["text"] = "changed"
    bundle = {
        "profile": PROFILE,
        "extraction_profile": "visible-text-reviewed/0.1",
        "services": {"example/service@1": {"pages": [page]}},
    }
    with pytest.raises(RawPageBundleError, match="text_sha256 mismatch"):
        attach_raw_pages([_task()], bundle)


def test_attach_raw_pages_enforces_fixed_per_service_budget():
    text = "x" * (MAX_CHARS_PER_SERVICE + 1)
    bundle = {
        "profile": PROFILE,
        "extraction_profile": "visible-text-reviewed/0.1",
        "services": {"example/service@1": {"pages": [_page(text, BASE_SUPPORT)]}},
    }
    with pytest.raises(RawPageBundleError, match="service budget"):
        attach_raw_pages([_task()], bundle)


def test_review_template_lists_required_paths_and_deduplicated_urls():
    manifest = {
        "service_id": "example/service@1",
        "provenance": {"source_url": "https://provider.example/docs"},
        "invocation": {"docs_url": "https://provider.example/docs"},
        "usage_terms": {"tos_url": "https://provider.example/terms"},
    }
    template = build_review_template([_task()], [manifest])
    service = template["services"]["example/service@1"]
    assert service["required_fact_paths"] == sorted(BASE_SUPPORT)
    assert service["suggested_urls"] == [
        "https://provider.example/docs",
        "https://provider.example/terms",
    ]
    assert service["pages"] == []

#!/usr/bin/env python3
"""Audit ASM manifest freshness, schema conformance, provenance, and sources.

The audit is read-only. It treats checked-in files as a versioned dataset, not
as live provider truth, and emits inspectable JSON suitable for CI or review.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import jsonschema
except ImportError:  # pragma: no cover - handled by main
    jsonschema = None


ROOT = Path(__file__).resolve().parent.parent
FRESH_DAYS = 30
STALE_DAYS = 90
VERIFICATION_STATUSES = {"manual_verified", "self_reported", "benchmark_verified"}


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def freshness_status(last_verified_at: str | None, as_of: datetime) -> tuple[str, int | None]:
    """Classify claim age independently of the live-manifest cache TTL."""
    if not last_verified_at:
        return "unknown", None
    try:
        verified = parse_datetime(last_verified_at)
    except (TypeError, ValueError):
        return "invalid", None
    age_days = max(0, (as_of - verified).days)
    if age_days <= FRESH_DAYS:
        return "fresh", age_days
    if age_days <= STALE_DAYS:
        return "stale", age_days
    return "expired", age_days


def manifest_paths(root: Path = ROOT) -> list[tuple[str, Path]]:
    paths = [("manifests", p) for p in sorted((root / "manifests").glob("*.asm.json"))]
    paths += [("library", p) for p in sorted((root / "library").rglob("*.asm.json"))]
    return paths


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: tuple(str(x) for x in error.absolute_path))
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in errors
    ]


def audit_document(
    path: Path, collection: str, schema: dict[str, Any], as_of: datetime, root: Path = ROOT
) -> dict[str, Any]:
    relative = str(path.relative_to(root))
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "path": relative,
            "collection": collection,
            "schema_status": "invalid",
            "schema_errors": [str(exc)],
            "freshness_status": "unknown",
            "provenance_issues": ["document could not be parsed"],
        }

    provenance = document.get("provenance")
    issues: list[str] = []
    if not isinstance(provenance, dict):
        provenance = {}
        issues.append("missing provenance object")
    for field in ("source_url", "retrieved_at", "last_verified_at", "verification_status"):
        if not provenance.get(field):
            issues.append(f"missing provenance.{field}")
    verification = provenance.get("verification_status")
    if verification and verification not in VERIFICATION_STATUSES:
        issues.append(f"unknown verification_status: {verification}")

    freshness, age_days = freshness_status(provenance.get("last_verified_at"), as_of)
    errors = _schema_errors(document, schema)
    return {
        "path": relative,
        "collection": collection,
        "service_id": document.get("service_id"),
        "schema_status": "valid" if not errors else "invalid",
        "schema_errors": errors,
        "freshness_status": freshness,
        "verification_age_days": age_days,
        "verification_status": verification or "missing",
        "source_url": provenance.get("source_url"),
        "last_verified_at": provenance.get("last_verified_at"),
        "provenance_issues": issues,
    }


@dataclass(frozen=True)
class SourceCheck:
    url: str
    status: str
    http_status: int | None = None
    final_url: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def check_source_url(url: str, timeout: float = 10.0) -> SourceCheck:
    """Probe a source without treating authentication or bot blocking as death."""
    request = Request(
        url,
        headers={
            "User-Agent": "ASM-data-audit/0.1 (+https://github.com/YE-YI7/asm-spec)",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            code = response.getcode()
            status = "reachable" if 200 <= code < 400 else "unexpected_response"
            return SourceCheck(url, status, code, response.geturl())
    except HTTPError as exc:
        if exc.code in {401, 403, 407, 418, 429}:
            status = "access_restricted"
        elif exc.code in {404, 410}:
            status = "not_found"
        elif 500 <= exc.code < 600:
            status = "server_error"
        else:
            status = "http_error"
        return SourceCheck(url, status, exc.code, exc.geturl())
    except (TimeoutError, socket.timeout) as exc:
        return SourceCheck(url, "timeout", error=str(exc))
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return SourceCheck(url, "timeout", error=str(exc.reason))
        return SourceCheck(url, "network_error", error=str(exc.reason))
    except (ValueError, ssl.SSLError) as exc:
        return SourceCheck(url, "invalid_or_tls_error", error=str(exc))


def check_sources(urls: Iterable[str], timeout: float, workers: int) -> list[dict[str, Any]]:
    results: list[SourceCheck] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(check_source_url, url, timeout) for url in sorted(set(urls))]
        for future in as_completed(futures):
            results.append(future.result())
    return [item.as_dict() for item in sorted(results, key=lambda item: item.url)]


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "missing")) for row in rows).items()))


def build_report(
    root: Path,
    as_of: datetime,
    check_urls: bool = False,
    timeout: float = 10.0,
    workers: int = 12,
) -> dict[str, Any]:
    if jsonschema is None:
        raise RuntimeError("jsonschema is required; install it with python3 -m pip install jsonschema")
    schema = json.loads((root / "schema" / "asm-v0.3.schema.json").read_text(encoding="utf-8"))
    entries = [audit_document(path, name, schema, as_of, root) for name, path in manifest_paths(root)]

    collections: dict[str, Any] = {}
    for name in ("manifests", "library"):
        rows = [row for row in entries if row["collection"] == name]
        collections[name] = {
            "entries": len(rows),
            "schema": _counts(rows, "schema_status"),
            "freshness": _counts(rows, "freshness_status"),
            "verification": _counts(rows, "verification_status"),
            "provenance_complete": sum(not row["provenance_issues"] for row in rows),
            "source_urls_present": sum(bool(row.get("source_url")) for row in rows),
        }

    sources = (
        check_sources((row["source_url"] for row in entries if row.get("source_url")), timeout, workers)
        if check_urls
        else []
    )
    return {
        "report_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "policy": {
            "fresh": f"verification age <= {FRESH_DAYS} days",
            "stale": f"{FRESH_DAYS + 1}-{STALE_DAYS} days; exclude from current-fact claims until reviewed",
            "expired": f"> {STALE_DAYS} days; fixture/benchmark use only until re-verified",
            "unknown_or_invalid": "do not use for selection without an explicit override",
            "cache_ttl_note": "Manifest ttl is a client cache directive, not evidence that checked-in claims are fresh.",
            "url_note": "401/403/429 mean access_restricted, not dead. Only 404/410 are not_found.",
        },
        "summary": {
            "entries": len(entries),
            "schema": _counts(entries, "schema_status"),
            "freshness": _counts(entries, "freshness_status"),
            "verification": _counts(entries, "verification_status"),
            "provenance_complete": sum(not row["provenance_issues"] for row in entries),
            "source_urls_present": sum(bool(row.get("source_url")) for row in entries),
            "unique_source_urls": len({row["source_url"] for row in entries if row.get("source_url")}),
            "source_reachability": _counts(sources, "status") if check_urls else {"not_checked": len(entries)},
        },
        "collections": collections,
        "entries": entries,
        "sources": sources,
    }


def parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if len(value) == 10:
        value += "T23:59:59Z"
    return parse_datetime(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", help="ISO date/datetime for deterministic freshness checks")
    parser.add_argument("--check-urls", action="store_true", help="probe unique provenance URLs")
    parser.add_argument("--timeout", type=float, default=10.0, help="per-source URL timeout")
    parser.add_argument("--workers", type=int, default=12, help="parallel URL checks")
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    parser.add_argument("--fail-on", choices=("none", "invalid", "expired", "stale"), default="none")
    args = parser.parse_args(argv)
    try:
        report = build_report(ROOT, parse_as_of(args.as_of), args.check_urls, args.timeout, args.workers)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)
    summary = report["summary"]
    print(
        f"entries={summary['entries']} schema={summary['schema']} "
        f"freshness={summary['freshness']} verification={summary['verification']}",
        file=sys.stderr,
    )
    if args.fail_on == "invalid" and summary["schema"].get("invalid", 0):
        return 1
    if args.fail_on == "expired" and summary["freshness"].get("expired", 0):
        return 1
    if args.fail_on == "stale" and (
        summary["freshness"].get("expired", 0) or summary["freshness"].get("stale", 0)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

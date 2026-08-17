# ASM lint and CI

`asm-lint` turns an ASM manifest into a deterministic, reviewable report. It
does not certify a service and it does not assign a universal quality score.
The same manifest and `--as-of` time produce the same statuses and digest.

## Install and run

```bash
python -m pip install "asm-protocol==0.5.2"
asm-lint path/to/server.json
```

Both input shapes are supported:

- a standalone ASM JSON document; or
- an MCP Registry `server.json` with ASM under
  `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.

Generate a machine-readable or review-friendly artifact:

```bash
asm-lint server.json --format json --output asm-lint-report.json
asm-lint server.json --format markdown --output asm-lint-report.md
```

## Statuses

| Check | Meaning |
|---|---|
| `schema` | The document is present and valid against the packaged ASM v0.3 schema. |
| `provenance` | `source_url`, retrieval time, verification time, and verification status are present. |
| `freshness` | `fresh` is 0–30 days, `stale` is 31–90 days, and `expired` is over 90 days. |
| `selection_readiness` | The manifest is valid, sourced, declares invocation eligibility, and includes at least one pricing, quality, or SLA dimension. |

Freshness is evidence age, not cache lifetime. A manifest's `ttl` does not
make an old claim current.

The default CI policy fails only when the ASM block is missing or schema
invalid. Repositories can raise the threshold:

```bash
asm-lint server.json --fail-on not-ready
asm-lint server.json --fail-on expired
asm-lint server.json --fail-on stale
```

Use `--as-of 2026-08-17` in fixtures and conformance tests so time-dependent
results remain reproducible.

## GitHub Action

```yaml
name: ASM metadata

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  asm-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: YE-YI7/asm-spec/.github/actions/asm-lint@v0.5.2
        with:
          path: server.json
          fail-on: invalid
```

The composite Action installs the pinned PyPI release, runs locally, and adds
the Markdown report to the GitHub job summary. It neither calls an ASM-hosted
API nor uploads the inspected manifest.

## What counts as adoption

An external repository keeping this check enabled, with a report tied to a
manifest digest, is an observable adoption receipt. A self-owned workflow,
README badge, star, or verbal expression of interest is not.

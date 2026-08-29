# Ten-minute producer adoption package

This package adds one publisher-owned ASM artifact and one deterministic CI
check. It does not add ranking logic, execute a tool, authorize a payment, or
claim that publisher-provided facts were independently verified.

## 1. Add the smallest honest metadata block

If the repository publishes an MCP Registry `server.json`, add ASM at:

```text
_meta.io.modelcontextprotocol.registry/publisher-provided.asm
```

Start with the shape in
[`examples/mcp-server-json/operational-envelope-with-asm.server.json`](../../examples/mcp-server-json/operational-envelope-with-asm.server.json),
then replace every service-specific value with a fact the publisher can defend.
Sparse metadata is valid. Omit unknown pricing, quality, or SLA fields rather
than inventing them. Keep `verification_status` as `self_reported` unless an
independent verification actually occurred.

The minimum schema fields are:

```json
{
  "asm_version": "0.3",
  "service_id": "your-org/your-service@1.0",
  "taxonomy": "tool.data.search"
}
```

This minimum is schema-valid but intentionally not selection-ready. Add
provenance, invocation eligibility, and at least one supported value dimension
before using a stricter CI threshold.

## 2. Produce the local receipt

```bash
python -m pip install "asm-protocol==0.6.0"
asm-lint server.json --format markdown --output asm-lint-report.md
```

Review the report. The manifest digest identifies the exact metadata inspected;
it is not a quality score or third-party attestation.

## 3. Keep the check enabled

Add `.github/workflows/asm-lint.yml`:

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
      - uses: YE-YI7/asm-spec/.github/actions/asm-lint@v0.6.0
        with:
          path: server.json
          fail-on: invalid
```

`fail-on: invalid` allows an honest, partial manifest while rejecting missing or
malformed ASM. Move to `not-ready`, `expired`, or `stale` only when the
repository wants those stronger policies.

## Acceptance evidence

The bounded integration is complete when an external repository retains:

1. a valid publisher-owned ASM block or standalone manifest;
2. the pinned `asm-lint` workflow; and
3. a passing run whose job summary contains the manifest digest.

That is observable producer adoption. It is not evidence of runtime selection,
official MCP endorsement, commercial validation, or independently verified
service claims.

# A2A external reference probe

**Date:** 2026-08-31
**Reproduced:** 2026-09-01
**Endpoint:** `https://tasks.a2a-testbed.com`
**Scope:** one public test endpoint; two benign task attempts
**Relationship:** independent observation only; no adoption or partnership

## Observed facts

The public Agent Card returned HTTP 200 and declared:

```json
{
  "url": "https://tasks.a2a-testbed.com",
  "protocolBinding": "JSONRPC",
  "protocolVersion": "1.0"
}
```

Two calls were compared:

| Client path | Method shape | Result |
|---|---|---|
| official `a2a-sdk 1.1.2` | `SendMessage`, ProtoJSON v1 roles/parts | `MethodNotFoundError: method not implemented: SendMessage` |
| raw compatibility probe | `message/send`, legacy `user` + `kind:text` | completed Task with two echo artifacts |

The A2A 1.0 specification maps JSON-RPC send-message to PascalCase
`SendMessage`, while `message/send` is an older JSON-RPC shape. Therefore the
live endpoint was callable through the older method but did not satisfy its
declared JSON-RPC 1.0 interface in this probe.

Specification:

- https://a2a-protocol.org/dev/specification/#531-method-mapping-reference
- https://a2a-protocol.org/dev/specification/#94-core-methods

## Product consequence

This is the first external example in this branch showing why provider-declared
Agent Card facts are insufficient:

- liveness was true;
- a legacy task completed successfully;
- declared-interface compatibility was false for the official v1 client.

A single `completed/failed` rating would lose this distinction. Experience
evidence needs named check results such as interface conformance, reachability,
task correctness, latency, and policy compliance rather than one universal score.

## Boundary

- This does not assess the broader a2a-testbed project or its 58-test suite.
- Only one endpoint and one SDK version were checked.
- The endpoint may be intentionally retaining legacy compatibility or may have
  changed after this observation.
- The finding should be offered to the maintainer for confirmation before being
  used in any public ecosystem-quality claim.

Reproducer: `experiments/a2a_external_reference_probe.py`.

## Maintainer feedback

The maintainer confirmed that the reference agent needs migration to PascalCase
v1.0 JSON-RPC methods, requested the reproducer, and stated an intention to add
the case to the conformance suite. The same mismatch was reproduced again on
2026-09-01 before delivery.

Status: external maintainer confirmed the fix direction; fix not yet observed.
Initial report: https://github.com/a2aproject/A2A/discussions/1826#discussioncomment-18216328
Maintainer reply: https://github.com/a2aproject/A2A/discussions/1826#discussioncomment-18222053
Reproducer delivery: https://github.com/a2aproject/A2A/discussions/1826#discussioncomment-18226134
Standalone script: https://gist.github.com/YE-YI7/25d4e2bf1a136277c4c6c7f67a24566c

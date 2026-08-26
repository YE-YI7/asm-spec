# Vibes-Coded access-signal review fixture

This is the pinned mapping/validator shape requested by `doteyeso-ops` in
[Agent-Card/ai-catalog#83](https://github.com/Agent-Card/ai-catalog/issues/83#issuecomment-5427764722).

It maps a small, source-linked observation from the public
`GET /api/v1/outcomes/meta` response into the candidate access-extension value
from [`schema/asm-ai-catalog-access-v0.1.schema.json`](../../../schema/asm-ai-catalog-access-v0.1.schema.json).
The three coarse mechanism identifiers are `x402`, `prepaid-key`, and
`day-pass`.

## Files

- `source-observation.json` pins the inspected source URL, retrieval time, and
  only the facts used by this fixture. The live response is dynamic and its full
  raw snapshot is not retained, so this review fixture does not claim a
  reproducible source-body digest. The status remains
  `live_observed_not_provider_confirmed` until the producer checks the mapping.
- `mapping-v0.1.json` records every source-to-target pointer and the runtime
  payment fields deliberately excluded from discovery.
- `vibes-coded-access.example.json` is generated from the observation and
  validates as one extension **value**. Vibes-Coded retains ownership of its
  extension namespace and publication location.

The example treats `/api/v1/outcomes/meta` as a public live-terms resolver and
therefore sets `authRequired: false`. It does not assert that this endpoint
returns caller-specific terms. If Vibes-Coded exposes an authenticated
caller-specific resolver, the producer should replace this reference and set
`authRequired: true`.

## Reproduce

From the ASM repository root:

```bash
python3 tools/build_vibes_coded_access_fixture.py --check
python3 tools/validate_access_extension.py \
  examples/interop/vibes-coded-access-signals/vibes-coded-access.example.json
python3 -m pytest -q scorer/test_vibes_coded_access_fixture.py
```

## Evidence boundary

The two non-authoritative price echoes are deliberately scoped to the observed
`action-receipt` call and the 24-hour guard pass. They are not a scalar price for
the whole catalog. The prepaid trial is an allowance rule, not a promise of
future eligibility.

This fixture contains no `402 accepts[]`, payment signature, wallet/chain
address, settlement result, caller balance, or access-token value. It does not
claim WG endorsement, settlement conformance, cross-vendor conformance, or a
Vibes-Coded integration. A producer-published, retained sidecar is required
before any external-adoption claim.

# Search application contracts v0.1 draft

Status: local implementation draft, not a published ASM standard.

This application profile separates four facts that older receipts could blur:

1. `SearchRequest`: what the host authorized ASM to decide or run.
2. `SelectionEvidence`: one sourced, scoped, expiring claim about one exact
   provider/interface/mode.
3. `DecisionReceipt`: what was recommended and why. It always states that the
   receipt itself grants no execution authorization.
4. `OutcomeReceipt`: what interface was actually called and what was observed.
   Transport success, tool success, and task checks remain separate.

Schemas live in `schema/`; valid replay fixtures live in
`examples/contracts/search/`. Validate a fixture with:

```bash
asm contract validate --type search_request examples/contracts/search/request.valid.json
```

The checked-in Tavily fixtures form the first end-to-end, no-network path. The
command creates the decision itself; the caller does not provide weights or a
handwritten DecisionReceipt:

```bash
asm search run-replay \
  --provider tavily \
  --request examples/contracts/search/request.valid.json \
  --evidence examples/contracts/search/evidence.tavily-price.valid.json \
  --response examples/contracts/search/providers/tavily.response.json \
  --decision-id dec-demo --outcome-id out-demo --attempt-id attempt-demo \
  --issued-at 2026-09-05T02:00:10Z --valid-until 2026-09-05T02:05:10Z \
  --started-at 2026-09-05T02:00:11Z --ended-at 2026-09-05T02:00:12Z
```

Request, decision, evidence, and normalized-result commitments use RFC 8785 JCS
plus SHA-256. A digest proves byte-stable commitment only; it does not prove the
underlying provider claim or result is true.

Replay failure fixtures also cover empty results, authentication failure,
billing blockage, rate limits, timeouts, and malformed result URLs. These paths emit an `OutcomeReceipt` with
separate transport and tool statuses; they do not retry or call the network.

## Required invariants

- An explicitly requested interface must occur in the host's authorized scope.
- `credits`, estimated currency cost, observed usage-derived cost, and settled
  currency cost are different value kinds. Credits never acquire a currency.
- Unknown evidence has a null value. Conflicts retain references to the other
  evidence records; consumers do not vote conflicts away.
- Evidence binds provider, service, interface, operation, service version,
  adapter version, interface digest, scope, source, and time window.
- A selected decision must point at a listed candidate. A non-selected status
  cannot name a selected candidate.
- Outcome timestamps and evidence timestamps are order-checked by the shared
  Python validator in addition to JSON Schema validation.
- New application commitments are produced with RFC 8785 canonicalization and
  SHA-256. Validators also check cross-document commitments at execution time.
- A cross-provider fallback requires an explicit request allowlist, attempt,
  deadline, budget, authorization, evidence, and interface-version checks. It
  creates a successor decision rather than rewriting the original receipt.
- Private worker observations are indexed by an opaque host-provided owner
  scope. A changed interface digest and a different owner scope do not match.

## Compatibility and migration

`selection-receipt-v0.1` remains unchanged. It is a legacy, unsigned selection
record and has no automatic conversion to `decision-receipt-v0.2`: the old
shape lacks evidence status, interface digest, cost basis, validity, policy
commitment, and execution binding.

Consumers must opt into the new contract names. During migration they may keep
legacy receipts for existing integrations, but a new decision/outcome pair is
the only supported representation for the search execution path. A legacy
receipt must never be relabeled as an outcome receipt.

## Known draft limits

- Schemas cannot establish source truth, issuer trust, authorization, or task
  correctness.
- They do not compare timestamps to wall-clock time; a consumer decides whether
  a structurally valid `expired` record may be retained for replay.
- Signed envelopes, authenticated cross-organization identity, and live
  provider quality evidence remain outside this local implementation.
- CLI, MCP, and HTTP validation surfaces consume the same packaged schemas and
  semantic validator. Search selection and adapters must use it when T2/T3 add
  actual producers; these validation endpoints alone do not create outcomes.

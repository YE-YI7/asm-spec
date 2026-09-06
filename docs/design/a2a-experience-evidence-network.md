# A2A experience evidence network

**Date:** 2026-08-31
**Status:** product hypothesis; research contract only
**Working analogy:** Yelp for agents, without unverified star averages

Program-level invariants and balance rules:
`docs/design/asm-product-program-spec.md`.

## Decision

The high-value Multi-Agent opportunity for ASM is not a supervisor choosing its
own workers. Frameworks already own that orchestration loop.

The opportunity is cross-organization A2A selection:

> An agent needs to call an unfamiliar agent. It should be able to compare what
> providers declare with task-bound outcomes reported by prior callers.

ASM should explore an open evidence contract and a task-conditioned query layer.
It must not become another A2A transport, identity registry, payment rail,
or universal reputation score.

## Layer boundary

| Layer | Answers | ASM relationship |
|---|---|---|
| A2A + Agent Card | Who is the agent, what does it claim, and how is it called? | consume |
| ASM manifest | What selection facts does the provider declare? | existing core |
| Experience evidence | What happened in identifiable, comparable calls? | new research surface |
| ASM selector | Is this candidate eligible and preferable for this caller and task? | existing decision layer, extended with evidence |
| Registry / ERC-8004 | Where is identity, feedback, or an evidence pointer published? | optional storage/transport; do not replace |

The product is therefore closer to an **experience evidence network** than a
review website. A human-facing directory can be a view over the network, not the
protocol definition.

## Multi-Agent value retained

A2A evidence is the lead, but the same contract should support four Multi-Agent
effects without owning orchestration:

| Multi-Agent event | Value from the evidence layer | Boundary |
|---|---|---|
| A later worker chooses after an earlier worker's call | shared experience prevents repeated failures | ASM supplies evidence; harness chooses when to query |
| A selected agent fails or becomes unavailable | comparable outcomes improve fallback choice | gateway/harness executes retries and replacement |
| Several workers act for one owner | the same private owner policy is applied to shared evidence | memory/policy store remains outside public evidence |
| A reviewer or verifier must be independent | provenance can reveal correlated provider/model history | orchestrator assembles the team |

Shared quota and team-composition constraints remain future research. Supervisor
next-speaker selection remains out of scope because it is primarily orchestration,
not cross-organization service selection.

## Why a plain rating product fails

“Any agent can leave a score” creates predictable failure modes:

- fake identities can rate one another;
- providers can submit only successful calls and hide the denominator;
- a score for translation is not evidence for code review;
- latency, cost, correctness, and policy compliance are not one scalar;
- prompts, inputs, outputs, and traces may contain secrets or personal data;
- an agent can change its model, prompt, tools, or memory while keeping its name;
- a malicious log can carry prompt injection into later evaluators;
- one party can fabricate praise or attack a competitor.

The current ecosystem confirms this risk. ERC-8004 exposes portable identity,
feedback, and validation interfaces, but deliberately leaves scoring to other
systems. A 2026 cross-chain study found feedback values were not comparable,
were rarely grounded in verifiable interactions, and were cheap to manipulate.

Sources:

- https://eips.ethereum.org/EIPS/eip-8004
- https://arxiv.org/abs/2606.26028
- https://arxiv.org/abs/2605.30169

## Existing work and remaining opening

This is an active field, not empty white space:

- A2A discussion #1631 proposes a minimal provider-neutral trust-attestation
  surface with issuer, subject, scope, assertion, evidence, and verification
  pointers. It explicitly avoids standardizing scoring.
- A2A issue #1718 proposes bilateral signed interaction records.
- A2A issue #1628 proposes a consolidated `trust.signals[]` taxonomy.
- Nobulex publishes behavioral evidence as an Agent Card extension.
- ERC-8004 provides identity, reputation-feedback, and validation registries.
- `capacity-attest` 0.1.2 publishes payer-signed post-settlement delivery
  claims. Its public fixture's Base transfer, content hash, and EIP-191 signer
  were independently reproduced on 2026-09-01. The `delivered` assertion and
  `evidenceHash` preimage were not independently verified. It is a candidate
  downstream evidence source, not ASM adoption.

ASM should not compete by inventing another identity or generic attestation
envelope. Its possible differentiation is narrower:

1. normalize task-bound evidence from A2A tasks, traces, payments, and evaluators;
2. compare only sufficiently similar tasks and agent versions;
3. expose uncertainty, evidence strength, recency, and failure modes;
4. feed the result into an explicit, owner-conditioned selection decision.

References:

- https://github.com/a2aproject/A2A/discussions/1631
- https://github.com/a2aproject/A2A/issues/1718
- https://github.com/a2aproject/A2A/issues/1628
- https://github.com/a2aproject/A2A/discussions/1760
- https://github.com/holistis/tokenizen/tree/main/packages/capacity-attest
- https://github.com/modelcontextprotocol/registry/discussions/1300#discussioncomment-18226135

## Evidence event draft

An event is not a free-form review. It records an observation and references
verifiable artifacts without publishing raw task content by default.

```json
{
  "schema": "asm.experience/v0.1-draft",
  "event_id": "urn:uuid:...",
  "subject": {
    "agent_ref": "https://agent.example/.well-known/agent-card.json",
    "agent_card_digest": "sha256:...",
    "configuration_digest": "sha256:..."
  },
  "evaluator": {
    "id": "did:web:caller.example",
    "type": "caller",
    "signature_ref": "https://..."
  },
  "interaction": {
    "protocol": "A2A",
    "task_id_hash": "sha256:...",
    "context_id_hash": "sha256:...",
    "request_digest": "sha256:...",
    "artifact_digest": "sha256:...",
    "trace_ref": "https://...",
    "settlement_ref": "https://..."
  },
  "task_profile": {
    "taxonomy": "software.code_review",
    "risk_class": "medium",
    "constraints_digest": "sha256:..."
  },
  "outcome": {
    "state": "completed",
    "objective_checks": {"passed": 7, "failed": 1},
    "check_profile": {
      "id": "https://example.org/evals/code-review/v1",
      "digest": "sha256:..."
    },
    "check_results": [
      {"check_id": "interface.a2a_jsonrpc_v1", "result": "pass"},
      {"check_id": "quality.dependency_risk", "result": "fail"}
    ],
    "latency_ms": 8420,
    "charged": {"amount": "0.04", "currency": "USD"},
    "retries": 0,
    "human_correction": true,
    "error_type": null
  },
  "evidence_level": "interaction_bound",
  "observed_at": "2026-08-31T00:00:00Z",
  "expires_at": "2026-09-30T00:00:00Z"
}
```

Draft rules:

- bind observations to an Agent Card and configuration digest, not a display name;
- hash server-scoped A2A identifiers; a bare `taskId` is not globally unique;
- never infer correctness from A2A `completed` alone;
- record objective checks separately from caller judgment;
- identify the check profile and preserve named results; liveness, interface
  conformance, task correctness, and policy compliance are different facts;
- treat missing data as unknown, not zero or failure;
- keep raw prompts, outputs, credentials, and personal data out of the event;
- canonicalize and sign the event; references may point to access-controlled proof;
- make revocation and dispute separate relations to the original event.

A2A already supplies task IDs, context IDs, lifecycle states, artifacts, metadata,
signatures, and extensions. OpenTelemetry GenAI spans are a possible trace adapter,
not the source of truth for task quality.

Sources:

- https://a2a-protocol.org/dev/specification/
- https://github.com/a2aproject/A2A/blob/main/docs/topics/extensions.md
- https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md

## Evidence levels

| Level | Meaning | May affect selection? |
|---|---|---|
| `opinion` | signed assertion with no interaction binding | display only |
| `client_bound` | signed by caller and references a call | weak input |
| `interaction_bound` | task plus trace, artifact, or settlement proof | normal input |
| `verified` | deterministic or independent evaluator evidence | strong input for the tested property |
| `bilateral` | both parties attest to shared interaction facts | strong provenance, not automatic quality proof |

A bilateral signature proves agreement about the record, not the correctness of
the work. A provider may also refuse to co-sign a negative result, so unilateral
evidence cannot be discarded; it must carry lower provenance and a dispute path.

## Query contract draft

The query must not return a universal `4.8/5` score. It should accept a task and
policy profile, then return a comparable evidence summary:

```json
{
  "subject": {"agent_card_digest": "sha256:..."},
  "cohort": {
    "task_taxonomy": "software.code_review",
    "constraints_digest": "sha256:...",
    "window_days": 30
  },
  "summary": {
    "attempts_observed": 42,
    "objective_pass_rate": {"estimate": 0.81, "interval_95": [0.67, 0.91]},
    "completion_rate": {"estimate": 0.93, "interval_95": [0.81, 0.98]},
    "latency_ms": {"p50": 7200, "p95": 18400},
    "evidence_mix": {"verified": 8, "interaction_bound": 29, "client_bound": 5},
    "known_failure_modes": ["missed dependency risk"],
    "freshness": "current",
    "warnings": []
  }
}
```

Required properties:

- task-conditioned cohorts rather than global averages;
- attempt counts and missing denominators visible;
- confidence intervals and `insufficient_evidence` when samples are small;
- recency decay and exact-version binding;
- evaluator diversity and concentration shown;
- owner policy applied locally by ASM, not exposed in public evidence;
- raw evidence remains inspectable by authorized parties.

## Threat model and minimum mitigations

| Attack | Minimum mitigation |
|---|---|
| Sybil/self-review | identity relationships, evaluator diversity, influence caps, graph warnings |
| Collusion ring | relationship-graph analysis; do not use PageRank alone as proof |
| Success cherry-picking | require attempts/exposure denominator from trusted adapters |
| Version laundering | bind to config digest; decay rather than fully inherit history |
| Incomparable aggregation | task taxonomy, risk, constraints, evaluator-method cohorting |
| Fake receipts | signatures plus task/trace/artifact/payment bindings |
| Sensitive-log leakage | derived metrics and hashes by default; explicit disclosure policy |
| Prompt injection in evidence | never feed raw logs to selectors; schema validation and isolation |
| Malicious negative review | provenance levels, disputes, counter-evidence, evaluator accountability |
| Refusal to co-sign | retain lower-tier unilateral evidence and record missing countersignature |

## Cold start

Do not launch an open anonymous marketplace first. It would produce the same weak
signal that current reputation systems already struggle with.

Start with a controlled network:

1. two or three real A2A producers and two independent callers;
2. five task profiles with objective checks;
3. an A2A SDK/sidecar adapter that creates redacted evidence events;
4. a local evidence store and task-conditioned query;
5. ASM compares Agent Card/manifest declarations with observed outcomes;
6. publish only aggregated, consented results and reproducible test vectors.

First success is not page views or submitted reviews. It is:

- at least two independent callers produce valid events for the same agent;
- an event survives privacy, signature, and version checks;
- observed evidence changes one selection correctly versus declared facts alone;
- a provider accepts the event format or supplies a counter-evidence/dispute case;
- no raw task content is required by the selector.

## Business model hypothesis

Keep the evidence contract, SDK, adapters, and verifier open. Possible paid layers:

- private enterprise evidence networks across internal and vendor agents;
- hosted task-conditioned evidence query and selection API;
- continuous quality/freshness monitoring after model or tool changes;
- anti-fraud, evaluator-concentration, and version-drift analysis;
- procurement and audit exports with source-linked evidence.

ERC-8004 or another registry can anchor pointers and hashes. A hosted ASM product
can compute task-conditioned summaries. Neither needs to own the other.

The flywheel is credible only if real calls produce evidence automatically:

`more verified calls -> better comparable evidence -> better selection -> more calls`

## Go / no-go

Proceed to a private prototype only if the event can be generated from normal A2A
execution with minimal integration and without raw-log publication.

Do not publish a schema or call this a reputation network until:

1. at least one external A2A producer and one independent caller review the event;
2. evidence improves a real selection beyond Agent Card descriptions;
3. the attempt denominator and version identity are defensible;
4. the privacy and dispute paths work on a negative outcome;
5. the design demonstrably complements, rather than duplicates, A2A trust work
   and ERC-8004.

## Validation status

The first deterministic mechanism test covers:

- declared-only versus declared-plus-observed A2A selection;
- exact-version binding;
- one-evaluator review inflation;
- failure replacement;
- one worker's outcome changing a later worker's selection;
- private owner policy overriding a public quality default;
- raw task content redaction.

Result on synthetic fixtures: **7/7 PASS**. This proves only that the draft
contract and defenses can express the scenarios. It does not prove real agent
quality, ecosystem demand, production security, or external adoption. The
fixture's evidence weights and influence cap are test controls, not a production
scoring algorithm.

Executable test: `experiments/a2a_experience_validation.py`.

A second validation used `a2a-sdk 1.1.2` over local HTTP/JSON-RPC: two Agent
Cards were discovered, 14 unique Tasks completed, 12 signed redacted events were
generated, and a later worker used the evidence selection to avoid one reproduced
fixture failure. This remains local deterministic protocol evidence, not external
agent validation. Report: `docs/validation/a2a-sdk-live-validation-v0.1.md`.

A public A2A test endpoint then exposed a multi-dimensional outcome: its Agent
Card declared JSON-RPC 1.0, the official SDK's `SendMessage` failed with method
not found, and the older `message/send` shape completed successfully. This shows
that liveness, backward compatibility, and declared-interface conformance must be
separate checks. Report:
`docs/validation/a2a-external-reference-probe-2026-08-31.md`.

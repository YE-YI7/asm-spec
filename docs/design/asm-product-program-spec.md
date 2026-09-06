# ASM product program spec

**Version:** 0.1-draft  
**Date:** 2026-08-31  
**Audience:** ASM maintainers and coding agents  
**Purpose:** keep core ASM, A2A evidence, and Multi-Agent value moving together

## 1. Product invariant

ASM is the protocol and decision layer for selecting callable tools, services,
and externally owned agents under task constraints and owner policy.

ASM does not become:

- an orchestrator or supervisor framework;
- an A2A/MCP transport;
- an agent identity registry;
- an authorization gateway;
- a payment or settlement rail;
- a universal reputation score;
- a general-purpose user-memory product.

## 2. Three workstreams

| Workstream | Owns | Must preserve |
|---|---|---|
| A. Core selection protocol | declared facts, eligibility, owner-conditioned selection, freshness, receipts, lint/conformance | tools/services remain first-class; deterministic hard gates |
| B. A2A experience evidence | task-bound observations, evidence strength, task cohorts, version identity, disputes | A2A/registries remain upstream; no global star score |
| C. Multi-Agent runtime value | shared experience, fallback choice, owner-policy consistency, verifier independence | harness owns planning, topology, scheduling, retries, and execution |

Priority is not equal effort on every turn. It is preservation of all three
contracts:

1. A change may advance one workstream.
2. It must not silently break or redefine the other two.
3. Every milestone review must state the impact on A, B, and C.

## 3. System model

```text
MCP / Agent Card / source docs
          |
          v
provider-declared selection facts -----------+
                                              |
A2A Task / Artifact / trace / receipt         v
          |                              ASM candidate view
          v                                    |
task-bound experience evidence ----------------+
                                              |
private owner policy --------------------------+
                                              v
                                    eligibility + comparison
                                              |
                                              v
                               selection result + decision receipt
                                              |
                                              v
                                   harness / agent executes
```

Declared facts, observed evidence, and owner policy are separate inputs. None may
be presented as another.

## 4. Required contracts

### 4.1 Declared candidate facts

Must preserve:

- stable service/interface identity;
- callable capabilities and required functions;
- reach, platform, setup, automation terms, risk, approval, and side effects;
- structured cost only when units and workloads are comparable;
- source lineage, freshness, and unknown values.

### 4.2 Experience event

Minimum fields:

- subject Agent Card/interface digest and configuration/version digest;
- evaluator identity and verification material;
- task profile and comparable-constraint digest;
- A2A task plus artifact/trace/settlement bindings when available;
- named check profile and named check results;
- observation time, expiry, revocation, and dispute relations;
- evidence level and disclosure policy.

Raw prompts, outputs, credentials, and personal data are excluded by default.
A2A `TASK_STATE_COMPLETED` is not proof of task correctness.

### 4.3 Evidence query

Must return:

- comparable cohort definition;
- attempts and missing-denominator warning;
- estimate plus uncertainty;
- evidence-level mix and evaluator concentration;
- recency and exact version;
- named failure modes;
- `insufficient_evidence` when the data cannot support a decision.

Must not return one context-free universal score.

### 4.4 Owner policy

Owner policy remains private and is applied before or alongside ranking:

- explicit tool/service selection overrides ranking when eligible;
- privacy, authorization, side-effect, risk, and budget hard constraints gate first;
- learned preferences influence ranking only after hard gates;
- evidence summaries do not reveal the owner's preference memory.

### 4.5 Selection result

Must distinguish:

- selected candidate;
- alternatives;
- rejected candidates and exact reasons;
- facts used and facts missing;
- declared versus observed evidence;
- owner-policy effects;
- uncertainty or `needs_facts`;
- fallback/reselection linkage when used by a Multi-Agent runtime.

## 5. Multi-Agent value contract

ASM supports these events:

| Event | ASM contribution | External owner |
|---|---|---|
| later worker reuses earlier outcome | task-bound evidence query | harness decides when workers run |
| chosen agent fails | evidence-informed fallback candidates and chained receipt | runtime performs retry/replacement |
| multiple workers serve one owner | consistent private policy input | memory/policy system stores preferences |
| independent reviewer is required | provenance/diversity facts | orchestrator assembles the team |
| agents contend for quota/capacity | consume live availability signal | scheduler allocates resources |

Supervisor next-speaker selection and team topology are benchmark cases, not the
product lead.

## 6. Algorithm rules

No production weights, thresholds, evidence multipliers, decay curve, or
evaluator cap may be chosen only because it works on synthetic fixtures.

An algorithm change requires:

1. an explicit decision objective;
2. hard constraints separated from soft preferences;
3. baseline and ablation;
4. task-level paired evaluation where possible;
5. uncertainty and calibration reporting;
6. adversarial cases for Sybil, cherry-picking, version laundering, and missing data;
7. failure behavior that returns unknown rather than false confidence.

The current synthetic evidence weights are test controls, not product defaults.

## 7. Evidence ladder and claim language

| Level | Evidence | Allowed claim |
|---|---|---|
| E0 | design document | hypothesis only |
| E1 | synthetic fixture | mechanism can express the case |
| E2 | real local SDK/protocol call | technical feasibility in controlled environment |
| E3 | external endpoint observation | narrow independently hosted behavior observed |
| E4 | external maintainer reviews or runs artifact | external technical validation |
| E5 | external repository retains and runs integration | adoption |
| E6 | qualified user repeatedly relies on it | product validation |
| E7 | paid, retained use | commercial validation |

Never upgrade evidence language without crossing the corresponding gate.
Replies, likes, local demos, merged self-owned code, and willingness to discuss do
not equal adoption.

## 8. Current state

| Workstream | Current evidence | Level |
|---|---|---:|
| Core selection | released SDK, lint, manifests, receipts, adaptive experiments | mixed E1–E4 by artifact; verify each named claim separately |
| A2A evidence | event/query draft plus synthetic 7/7 mechanism test | E1 |
| A2A SDK feasibility | two local agents, 14 Task calls, 12 signed redacted events | E2 |
| External A2A behavior | one public endpoint showed declared-v1/legacy-method mismatch | E3 |
| Multi-Agent reuse | later local worker avoided one reproduced fixture failure | E2 |
| A2A evidence adoption | no external project retains or runs the contract | not reached |
| MCP producer adoption | Context7 PR #3105 was closed because ASM lacks formal MCP acceptance or broad ecosystem adoption; maintainers may reconsider after that changes | explicit Gate 3 blocker, not a technical rejection |

## 9. Validation gates

### Gate 1: controlled protocol feasibility — passed

- real A2A Agent Cards and Task lifecycles;
- redacted event generation;
- caller signature verification;
- evidence changes a later worker's choice;
- repository regression suite remains green.

### Gate 2: external technical validation — active

Required:

- one independently hosted producer;
- two independently controlled callers/evaluators;
- one useful task with deterministic or independently reviewed acceptance;
- all attempts represented, not selected successes only;
- one negative result with counter-evidence or dispute handling;
- one version/configuration change.

### Gate 3: retained adoption

Required:

- external repository retains an event adapter, query, lint artifact, or receipt;
- it runs in CI or runtime for at least one real workflow;
- maintainer confirms the integration removes work or improves a decision.

Observed blocker: a large producer may refuse even valid namespaced metadata
until either MCP formally accepts the extension or smaller external producers
create meaningful retained adoption. Context7 PR #3105 is direct evidence of
this gate; do not reopen or pursue that repository until the stated condition
changes.

### Gate 4: product validation

Required:

- repeated decisions, not a one-off demo;
- measurable reduction in invalid choices, repeated failures, or investigation time;
- clear buyer and budget owner;
- willingness to pay tested without calling free use commercial validation.

## 10. Work-in-progress rules

At most one item may be active in each workstream. Before starting a new item:

1. close, stop, or explicitly park the previous item;
2. record the evidence level reached;
3. state what remains unknown;
4. link one executable artifact or external receipt;
5. check that core ASM behavior still passes.

Do not add a public schema field because one local experiment needs it. Use an
experimental event/profile until an external counterpart validates the shape.

Before sending external technical messages or pushing integration code:

- re-open the exact issue/PR and check for duplication;
- verify every version, endpoint, commit, test, and claim boundary;
- request an independent review pass from the configured local reviewer when
  available;
- do not send if the review is incomplete or the evidence link is not reproducible.

## 11. Near-term sequence

1. obtain confirmation on the external A2A method-version mismatch;
2. convert named conformance outcomes into an experimental check-result profile;
3. run one useful deterministic task against two independently hosted endpoints;
4. test negative evidence, dispute, and version change;
5. ask one producer and two callers to review/run the minimal contract;
6. only then decide whether to publish an A2A evidence profile or keep it private.

Core selection maintenance continues throughout: no regression in lint,
eligibility, owner policy, freshness, cost comparability, or receipt generation.

## 12. Required milestone report

Every future milestone report must answer, in this order:

1. What externally or technically changed?
2. What evidence level was reached?
3. What did this improve in core selection?
4. What Multi-Agent value was demonstrated?
5. What remains unvalidated?
6. Was anything committed, pushed, deployed, paid for, or sent externally?

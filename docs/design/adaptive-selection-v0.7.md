# Adaptive selection v0.7: research and implementation plan

**Status:** experimental design and prototype. This document does not change
the stable ASM schema or the default selector.

## Problem statement

ASM v0.6 has two intentionally separated but confusing paths:

- `asm_protocol.selection` is the canonical workload-aware eligibility and
  cost selector used by `asm select`;
- `scorer.score_topsis` is a legacy experimental scorer still used by
  `asm score`, OpenRouter demos, the TypeScript registry, and older studies.

Neither path learns an owner's preferences. Static preference weights are
provided by a caller or inferred from keywords, and the checked-in manifests
are research fixtures rather than a live catalog. As of 2026-08-31, the local
audit classifies all 75 `manifests/` entries as expired and all 30 `library/`
entries as stale.

The v0.7 question is therefore not “which new scalar scoring formula replaces
TOPSIS?” It is:

> How can an agent select from an evolving tool set on behalf of an owner,
> learn from revealed preferences without requiring a settings questionnaire,
> ask only when clarification is worth the interruption, and preserve an
> auditable decision boundary?

## Evidence informing the prototype

- The official MCP Registry exposes a cursor-paginated discovery API and
  version history. ASM should federate it instead of presenting a hand-curated
  list as the tool universe:
  <https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/generic-registry-api.md>
- RAG-MCP reports that retrieving a small relevant tool set before prompting
  reduces prompt volume and improves selection accuracy. Retrieval is a
  candidate-generation step, not permission to execute:
  <https://arxiv.org/abs/2505.03275>
- ToolSpectrum separates user profile from environmental context and finds
  that current models struggle to reason about both jointly:
  <https://aclanthology.org/2025.findings-acl.1063/>
- Preference-conditioned bandit routing provides a useful model for changing
  candidate sets and unseen services, but its trained policy and user-supplied
  preference vector are not directly reusable as an ASM default:
  <https://arxiv.org/abs/2502.02743>
- Value of Information (VoI) frames clarification as a decision: ask only when
  the expected utility improvement exceeds the cognitive cost of interrupting
  the user:
  <https://aclanthology.org/2026.acl-long.1987/>

## Product boundary

The owner model is private consumer state. It is not published in an ASM
manifest. Manifests describe service facts; the selector consumes task facts,
environment facts, owner evidence, and policy. A Selection Receipt may record
the digest and evidence class of the owner model, but not raw private history.

The decision order is:

1. non-overridable organization, safety, and authorization constraints;
2. an explicit owner tool instruction, treated as a forced candidate that must
   still pass the hard gates;
3. task capability and runtime eligibility;
4. manifest freshness and claim comparability;
5. owner-conditioned expected utility;
6. clarification or bounded exploration when uncertainty is material;
7. a deterministic identifier only for a true utility tie.

The current prototype is deliberately not a goal planner. Raw `task` text is
recorded for audit and deterministic sampling, but it is not treated as a
trusted semantic ranking signal. A harness or planner must compile the goal
into taxonomy, required functions, environment, and reversibility before ASM
applies hard gates and owner-conditioned selection. A later task compiler must
be evaluated separately against natural goals; keyword inference is not
silently presented as understanding.

## Candidate algorithms

The prototype keeps multiple named policies so evaluation can choose a default:

| Policy | Role | Known limitation |
|---|---|---|
| workload-cost | v0.6 compatibility baseline | ignores owner utility |
| TOPSIS | historical benchmark baseline | static weights; candidate-set-sensitive normalization |
| LLM-only | semantic baseline | nondeterministic; can ignore policy and stale facts |
| posterior-mean | exploitation-only learned utility | can lock into early evidence |
| LinUCB | online contextual baseline | optimism can be unsafe without a risk gate |
| Thompson | Bayesian contextual candidate | exploration must be limited to reversible actions |

The initial implementation uses Bayesian linear regression over pairwise choice
and observed-outcome events. It exposes posterior-mean and uncertainty rather
than declaring them the new default. LinUCB/Thompson evaluation can reuse the
same sufficient statistics.

Each candidate has normalized, higher-is-better features whose provenance is
kept alongside the value:

- task and environment fit;
- workload-aware cost benefit;
- comparable quality only (heterogeneous benchmark names are not coerced);
- latency and reliability;
- data-governance/privacy properties;
- setup effort and owner familiarity;
- observed success/trust;
- freshness coverage and uncertainty.

Features used for longitudinal learning must not depend on the current
candidate set. Adding a new tool must not change an existing tool's feature
vector. The prototype therefore uses an owner-known monthly budget for cost, an
owner/agent-known latency target for speed, absolute uptime for reliability,
and only one shared `(metric, benchmark, scale)` identity for quality. Missing
targets or incomparable evidence remain unknown. Candidate-relative min-max
normalization is retained only in legacy TOPSIS baselines.

## Cold start without a settings questionnaire

The selector consumes evidence already available to the agent:

- explicit tool instructions and corrections;
- installed, authenticated, or subscribed services;
- accepted/rejected recommendations and owner replacements;
- execution success, retries, undo, and measured cost/latency;
- environment and organization policy.

With no owner history, the system does not invent a personal preference vector.
It may select a Pareto-dominant candidate, honor a valid explicit choice, or use
bounded exploration for a low-risk reversible action. For consequential or
irreversible actions, it computes VoI and asks only when the expected regret of
acting exceeds the estimated interruption cost.

The prototype does not assign a universal interruption-cost constant. If an
agent has not learned or estimated that cost in the same reward units, the
result marks VoI as `not_calibrated`; it still exposes posterior regret and
uncertainty rather than turning an arbitrary threshold into product policy.
Context tags in the local ledger are bounded machine identifiers, not prose,
and the ledger file is owner-readable only.

## Federated discovery and freshness

Discovery records and ASM selection facts are different artifacts. The MCP
adapter normalizes server identity, version, description, transports, status,
and update time, while marking pricing, risk, quality, and owner compatibility
as unknown. It must never fabricate a selection-ready manifest from discovery
metadata.

The target funnel is:

1. installed/authorized tools plus federated registries;
2. lexical/semantic retrieval of a bounded candidate set;
3. fetch the latest producer-owned ASM manifest or adapter evidence;
4. apply eligibility and freshness gates;
5. rank with an explicitly named policy;
6. revalidate the selected interface immediately before execution.

GUI, CLI, REST, and MCP surfaces are separately selectable variants under a
shared provider identity. For example, a WeCom GUI surface and a WeCom CLI
surface may share a provider but have distinct capabilities, versions, auth,
side effects, and freshness clocks.

## Evaluation before promotion

No adaptive policy becomes the default until it beats the baselines on an
external-outcome objective. TOPSIS score cannot be its own ground truth.

Required suites:

1. replay of explicit choice, rejection, replacement, and outcome histories;
2. cold-start and multi-turn owner profiles inspired by ToolSpectrum;
3. dynamic-catalog tests where tools are added, deprecated, or change surface;
4. stale-fact tests that require refresh or refuse selection;
5. scale tests over federated registry pages;
6. high-risk tests where exploration is forbidden;
7. counterfactual/off-policy evaluation when logged propensities exist.

Primary metrics are task success, owner correction rate, preference regret
against held-out choices, clarification rate and interruption cost, stale-fact
selection rate, hard-constraint violations, and coverage. Safety and stale-fact
violations are gates, not weighted score dimensions.

## Promotion gates

- one canonical public decision result shape;
- legacy algorithms are explicitly labeled and never silently selected;
- no stale or unknown critical fact is represented as current;
- raw owner history stays local and out of receipts;
- the adaptive policy improves held-out owner choice/outcome metrics over
  workload-cost, TOPSIS, and LLM-only baselines;
- at least one external agent consumes the adaptive result or receipt before
  adoption is claimed.

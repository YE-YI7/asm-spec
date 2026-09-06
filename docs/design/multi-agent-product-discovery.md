# Multi-Agent product discovery

**Date:** 2026-08-31  
**Status:** research only; no protocol or adapter commitment

Program-level invariants and balance rules:
`docs/design/asm-product-program-spec.md`.

## Decision today

ASM remains the protocol layer for selecting callable tools and services.
Multi-Agent does not replace that positioning; it multiplies the places where the
same selection problem occurs.

In current frameworks, specialist agents are commonly exposed as tools or handoff
targets, but frameworks already own that orchestration loop. ASM's larger
Multi-Agent opportunity begins when an agent must compare unfamiliar, externally
owned A2A services and can reuse task-bound outcomes observed by prior callers.
ASM can combine those observations with provider-declared selection facts without
owning orchestration, communication, authorization, identity, tracing, or settlement.

The near-term question is therefore not "should ASM become an agent protocol?"
It is "can A2A interactions produce trustworthy, privacy-safe evidence that
improves the ASM selection decision?"

## Multi-Agent selection surface map

| Selection event | Example | Value | ASM relationship | Current gap |
|---|---|---:|---|---|
| Worker chooses a tool | research agent chooses search/MCP provider | High | existing core | natural-language goal still needs structured constraint extraction |
| Supervisor chooses a specialist | manager calls coding, research, or finance agent as a tool | Medium | possible adapter surface | primarily an orchestration/framework concern, not the lead opportunity |
| Supervisor assembles a team | choose researcher + analyst + reviewer under one budget | Medium | useful benchmark case | team topology and scheduling belong to the orchestrator |
| Agent chooses a remote peer | local agent delegates to an A2A service from another vendor | Very high | select an invocation surface before A2A execution | no Agent Card adapter or caller-specific commercial/quality facts |
| Future agents reuse prior outcomes | agents publish task-bound experience evidence; later agents query it before selecting a peer | Very high | observed evidence can improve the ASM selection decision | no trusted cross-agent evidence network, task-conditioned aggregation, or anti-gaming layer |
| Runtime replaces a failed choice | rate limit, stale capability, outage, or permission mismatch | Very high | re-selection plus chained receipt | no runtime signal input or fallback-chain receipt |
| Multiple agents share scarce tools | parallel agents contend for quota, budget, or concurrency | High | selection under dynamic capacity | manifests are mostly static; no lease/capacity semantics |
| Owner policy follows delegation | every subagent honors privacy, approval, and cost preferences | High | policy-conditioned eligibility/ranking | preference evidence is local/experimental; no private policy handle |
| Reviewer/verifier is selected | choose an independent critic with different failure modes | Medium-high | set selection with independence constraints | no provenance/diversity constraint |
| Next speaker is selected | group chat chooses which participant acts next | Medium | ASM may filter eligible speakers | turn order and conversation state belong to orchestrator |
| Architecture/topology is selected | single agent vs centralized/decentralized team | Low | useful upstream signal only | not a tool-selection protocol responsibility |

The largest adjacent opportunity is **A2A observed evidence**: Agent Cards describe
what a remote agent claims; independent callers can contribute task-bound outcomes,
and later agents can use those outcomes as one input to ASM selection. Set-valued
selection remains an algorithm research case, not the product lead.

## Research evidence for the larger surface

- OpenAI Agents SDK and LangChain both model specialist agents as tools, while
  handoffs are also presented to the model as callable tool choices. This makes
  tool selection and agent delegation structurally adjacent:
  https://openai.github.io/openai-agents-python/multi_agent/
  https://openai.github.io/openai-agents-python/handoffs/
  https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- Microsoft Agent Framework explicitly supports prompt-based or custom selection
  of the next group-chat speaker. ASM should not own the conversation loop, but a
  selector can supply eligible candidates and decision evidence:
  https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/group-chat
- A2A 1.0 Agent Cards already standardize agent identity, skills, interfaces,
  security requirements, signatures, and extensions. ASM must complement the
  card with selection facts rather than duplicate it:
  https://a2a-protocol.org/dev/specification/
- Google Agent Registry now inventories and searches agents, MCP servers, tools,
  endpoints, and skills. Discovery is becoming platform infrastructure; selection
  across the returned candidates remains a separate decision:
  https://docs.cloud.google.com/agent-registry/overview
  https://docs.cloud.google.com/agent-registry/search-agents-and-tools
- Google Research found multi-agent architectures help parallelizable work but
  can degrade sequential tasks by 39-70%; independent teams amplified errors up
  to 17.2x. A useful selector must be allowed to choose one agent, not reward
  larger teams by default:
  https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Recent research frames routing as set-valued prediction and agent selection as
  choosing complete model+toolkit configurations. These are promising evidence,
  not yet product validation:
  https://arxiv.org/abs/2606.28925
  https://arxiv.org/abs/2603.03761

## Framework selection-event corpus v0.1

| Framework surface | Selection event already present | Inputs used today | Missing portable layer |
|---|---|---|---|
| OpenAI Agents SDK manager | choose a specialist exposed with `Agent.as_tool()` | tool name, description, conversation | eligibility, policy, cost/quality facts, alternatives, receipt |
| OpenAI/LangChain handoff | choose which specialist takes control | handoff description, history/state | comparable candidate facts and cross-framework decision record |
| LangChain supervisor | dynamically call one or several subagents as tools | subagent spec and ongoing context | set-level coverage/budget constraints and candidate freshness |
| AutoGen `SelectorGroupChat` | choose the next speaker | participant names/descriptions, history, optional candidate function | reusable eligibility filter and evidence for why a speaker was eligible |
| Microsoft Group Chat | choose one participant with round-robin, prompt, or custom function | participants and conversation state | framework-neutral selector request/result boundary |
| Google ADK | transfer to a subagent or call an `AgentTool` | hierarchy, descriptions, LLM routing | selection facts shared across transfer and agent-as-tool modes |
| A2A + cloud Agent Registry | search remote agents by skill/description, then call one | Agent Card skills/tags/interfaces/security | policy-aware choice among results, live value facts, alternatives, receipt |

This corpus exposes two distinct contracts:

1. **Capability selection:** choose tool, agent-as-tool, or remote service for a
   task or subtask. This is ASM's direct scope.
2. **Conversation scheduling:** decide who speaks next from workflow state. ASM
   can filter candidates, but the orchestrator owns timing and state transitions.

## Current implementation fit

The repository is not yet capable of the larger contract:

- `src/asm_protocol/selection.py` deliberately ignores natural-language `task`
  and requires callers to provide taxonomy or required functions;
- `select()` returns one selected service plus alternatives, not a minimal set;
- eligibility already covers reach, platform, setup, automation terms, required
  functions, risk, and approval, which are reusable across agent-as-tool calls;
- the manifest has no explicit subject type, composition dependency, shared
  budget/capacity, or caller/delegator context;
- Selection Receipt v0.1 records one service decision and cannot represent the
  current v0.6 structured-cost decision, much less a team or fallback chain.

Therefore the first technical experiment should be an internal A2A evidence
adapter and query prototype, not a public schema change. It must prove that real
A2A task outcomes can be version-bound, redacted, verified, and used to improve a
selection beyond Agent Card descriptions. The agent-as-tool benchmark remains
secondary algorithm research.

## Benchmark design v0.1

The first evaluation must cover decisions that the current top-one benchmark
cannot represent:

| Case | Required decision | Failure to measure |
|---|---|---|
| Single specialist | choose exactly one eligible agent-as-tool | ordinary routing error |
| Complementary team | choose the minimal set covering research + analysis + review | missing capability or unnecessary agent cost |
| Sequential task | prefer one capable agent over a larger team | coordination over-selection |
| Remote A2A peer | reject incompatible interface/security/input mode | invocation incompatibility |
| Stale capability | exclude an expired claim despite semantic match | freshness violation |
| Runtime outage/quota | replace the chosen candidate with a valid alternative | recovery failure and delay |
| Shared budget | allocate candidates across parallel workers without overspend | global budget violation |
| Owner policy | apply learned privacy/approval preferences consistently across workers | policy inconsistency |
| Independent reviewer | choose a verifier without shared provider/model provenance | correlated-failure risk |
| Under-specified goal | return `needs_facts`, not a confident team | unsafe false certainty |

Baselines:

1. names/descriptions-only LLM routing;
2. current ASM deterministic single selection;
3. experimental constrained set selection.

Primary metrics: hard-constraint violations, capability coverage, exact-set/Jaccard,
unnecessary team size, cost/regret where comparable, recovery success, and receipt
completeness. Report single-agent and multi-agent tasks separately; a gain from
adding more agents is not itself success.

Seed suite: `experiments/multi_agent_selection_tasks.v0.1.json` (10 synthetic,
source-linked cases; constraint logic only, no claims about real provider quality).

## Open-source instrumentation targets

Repository activity was checked on 2026-08-31; stars are discovery signals, not
evidence that maintainers want ASM.

| Target | Stars | Concrete selection seam | Research priority |
|---|---:|---|---|
| [A2A Python SDK](https://github.com/a2aproject/a2a-python) | — | task IDs, status, artifacts, metadata, Agent Cards | P0: generate an evidence event from a real call |
| [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai) | — | invoke-agent and tool execution spans | P0: optional trace binding; never equate a trace with quality |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | 29,088 | `Agent.as_tool(is_enabled=...)` plus MCP `tool_filter` | P2: selector-consumer experiment only |
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | 13,236 | `selection_func` and multi-selection edge groups | P2: set-valued benchmark only |
| [AutoGen](https://github.com/microsoft/autogen) | 60,714 | selector group chat supports `candidate_func` and custom selection | P2: instrumentation source; do not own speaker loop |
| [Google ADK](https://github.com/google/adk-python) | 21,338 | subagent transfer and `AgentTool` modes | P2: instrumentation source |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 40,756 | supervisors call subagents as tools | P2: instrumentation source |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 57,857 | crew delegation and tool use | P3: inspect only after A2A evidence is validated |

The first compatibility spike should not alter those frameworks. It should expose:

- an A2A call adapter that binds an Agent Card/configuration digest to a redacted
  outcome event;
- optional A2A task, artifact, trace, and settlement references;
- a task-conditioned evidence query with sample size, uncertainty, recency,
  version, evidence mix, and known failure modes;
- an ASM decision artifact showing how declared and observed facts affected the
  selected candidate.

Success means observed evidence changes a real decision correctly without exposing
raw task content. A working local adapter is still not external adoption.

## Trend thesis

The useful signal is not today's number of Multi-Agent applications. It is the
speed at which common infrastructure is becoming necessary:

| 2026 movement | Implication |
|---|---|
| March: A2A 1.0 becomes stable | cross-stack agent communication is standardizing |
| April: AWS launches Agent Registry preview | enterprises expect governed agent inventories |
| July: MCP adds stateless discovery, cache hints, and first-class extensions | catalogs become dynamic and extension-friendly |
| August: Google Agent Registry indexes A2A agents, MCP servers, and skills | discovery is becoming cloud infrastructure, not an ASM product |
| August: MCP group debates progressive discovery and selection separately | tool/agent abundance is producing a measurable selection problem |

Direction: discovery and orchestration will commoditize. ASM remains between
discovery and execution: a portable protocol for choosing one or more callable
capabilities from heterogeneous candidates, using fresh facts and caller policy.

## Picks-and-shovels ranking

| Infrastructure product | Trend fit | ASM fit | Decision |
|---|---:|---:|---|
| Tool/service selection contract + conformance/lint | High | High | Core |
| A2A task-bound experience event and query contract | Very high | Very high | Validate first; do not invent a universal score |
| A2A / trace / receipt evidence adapters | Very high | High | Validate without duplicating source protocols |
| Task-conditioned aggregation and anti-gaming analysis | Very high | High | Validate before an open network |
| MCP and Agent Card declared-fact adapters | High | High | Continue without duplicating source protocols |
| Selector evaluation kit | High | High | Compare declared facts with declared + observed evidence |
| Set-valued tool and agent-as-tool selection | High | Medium | Secondary algorithm research |
| Cross-registry normalization and freshness feed | High | High but data-heavy | Research commercial feasibility |
| Owner/org policy portability | High | Medium | Later; avoid authorization overlap |
| Fallback-chain Selection Receipt export | High | High | Extend only after runtime experiment |
| Hosted registry, gateway, or orchestrator | High market activity | Low | Do not build |

Possible product ladder, subject to evidence:

1. open protocol, lint, declared-fact adapters, evidence event/verifier, and benchmark;
2. paid private experience network and task-conditioned selection/evaluation API;
3. paid continuous freshness, quality-drift, and anti-fraud monitoring.

## Partner screen: Slack, Linear, Product Hunt

| Candidate | Current movement | ASM relevance | Role | Next research |
|---|---|---|---|---|
| Slack | AgentExchange browser, Slackbot MCP client, request routing, Add to Slack ecosystem | many agents/tools must be discovered and routed in one work surface | strategic upstream; high barrier | inspect marketplace metadata and routing inputs |
| Linear | agent API preview, explicit delegation, Agent Sessions, personal/team guidance, MCP connections, 250+ integration directory | its listings are descriptive and tell users to research owners/permissions themselves | reachable directory-audit and evaluation partner | audit the agent subset; inspect AIG contribution path |
| Product Hunt | AI/developer newsletters, product forums, collections, public GraphQL API | turn a subset of API/MCP/CLI launches from human-discoverable into agent-assessable | distribution/data partner, not technical adopter | manually compare a small public sample; seek API permission before commercial use |

Priority by purpose:

- trend and platform importance: Slack;
- near-term product discovery: Linear;
- report distribution and launch: Product Hunt.

Concrete downstream scenarios:

| Surface | Selection ASM could support | ASM does not own |
|---|---|---|
| Slack | for one user request, filter and choose eligible Slackbot agents/MCP tools under workspace, channel, data, approval, and owner policy; select replacements when a provider is unavailable | Slack UI, request routing loop, permissions, execution |
| Linear | for one issue, choose a coding agent or minimal coding+review+security team based on repository fit, permissions, risk, queue/capacity, and user policy | issue lifecycle, Agent Session, code execution, PR merge |
| Product Hunt | turn launched API/MCP/CLI products into candidate sources and measure whether they expose enough selection facts | runtime adoption, verification, commercial API rights |

Slack and Linear are therefore possible high-volume consumers of the protocol,
not reasons to redefine ASM as a directory. Product Hunt is a supply/distribution
source, not the first runtime integration target.

Observed first-pass result:

- Linear's first ten agent listings explain capability well, but none disclose
  comparable price, quality/SLA evidence, freshness, or a machine-readable card.
- In a purposive sample of eight agent-operable Product Hunt pages, interface and
  price disclosure are stronger, while quality/SLA evidence, freshness, and
  machine-readable selection metadata remain absent.
- Therefore these directories are candidate sources, not the product definition.
  ASM's product remains the selection contract; source-linked facts, conformance,
  and evaluation make that contract usable.
- A three-provider documentation pilot found objective auth, interface, retention,
  rate-limit, and unit-price facts, but not independent quality evidence, total
  execution cost, or a safe expiry date. A feed is technically plausible only
  with source lineage and explicit recheck policy.

Audit: `docs/data-quality/linear-agent-directory-audit-2026-08-31.md`

Do not send a generic partnership pitch. A credible Product Hunt proposal is an
"Agent-Ready Product Index": a small study/collection of launches that expose an
API, MCP server, or CLI, scored on machine operability, auth, pricing disclosure,
freshness, and evidence. Product Hunt gets editorial material and a useful
collection; makers get actionable gaps; ASM gets distribution and real metadata.
Product Hunt's API forbids commercial use by default, so any dataset or paid
product using it requires written permission first.

Evidence:

- Slack says AgentExchange is now available from its Agents & tools surface and
  Slackbot can act as an MCP client:
  https://slack.com/help/articles/33076000248851-Work-with-AI-agents-in-Slack
  https://slack.com/help/articles/48855576908307-Guide-to-Model-Context-Protocol-in-Slack
- Slack opened an Add to Slack deployment path with ten agent-building partners
  on 2026-08-20:
  https://v2.slack.com/blog/news/add-to-slack
- Linear's agent APIs remain in developer preview; delegation, session state,
  agent activities, guidance, and MCP connections are already concrete:
  https://linear.app/developers/agents
  https://linear.app/developers/agent-interaction
  https://linear.app/changelog/2026-04-23-linear-agent-mcp-support
- Linear reports over 250 third-party integrations and explicitly recommends
  that users research integration owners and requested permissions:
  https://linear.app/docs/integration-directory
- Product Hunt supports forums and AI/developer newsletters. Its API is public
  but commercial use requires contacting Product Hunt:
  https://help.producthunt.com/en/articles/11432379-maker-s-guide-to-product-forums
  https://help.producthunt.com/en/articles/484983-stay-in-the-loop-with-product-hunt-newsletters
  https://api.producthunt.com/v2/docs

## Market boundary

| Existing layer | Already owns | ASM must not duplicate |
|---|---|---|
| A2A / Agent Cards | agent identity, skills, interfaces, auth, extensions | agent protocol or registry |
| A2A AGP draft | capability routing, cost, policy constraints, stale routes | another routing protocol |
| Agent frameworks | supervisor, handoff, parallelism, state, retries | workflow execution |
| AgentCore / memory products | extracting and storing user preferences | general-purpose memory |
| Agent and AI gateways | auth, allow/deny policy, budgets, retries, model/tool routing | enforcement gateway |
| Tracing systems | what actually ran | execution trace |

Current evidence:

- A2A shipped its first stable v1.0 on 2026-03-12:
  https://a2a-protocol.org/dev/blog/2026/03/12/a2a-protocol-ships-v10-production-ready-standard-for-agent-to-agent-communication/
- MCP's 2026-07-28 release added stateless discovery, cache hints, and a formal
  extension track:
  https://blog.modelcontextprotocol.io/posts/2026-07-28/
- A2A Agent Cards already describe capabilities and support extensions:
  https://a2a-protocol.org/dev/specification/
- The official A2A samples repository contains an AGP V1 proposal with cost,
  policy, routing tables, and stale-route handling:
  https://github.com/a2aproject/a2a-samples/blob/main/extensions/agp/spec.md
- OpenAI Agents SDK and Microsoft Agent Framework already implement the common
  multi-agent orchestration patterns:
  https://openai.github.io/openai-agents-python/multi_agent/
  https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- AWS AgentCore already offers user-preference memory and Cedar authorization:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/long-term-configuring-built-in-strategies.html
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
- Portkey already markets an Agent Gateway spanning registry, policy, budgets,
  routing, reliability, and observability:
  https://portkey.ai/docs/product/ai-gateway
- AWS and Google now ship governed enterprise agent registries. Google indexes
  A2A skills and supports cross-project registration; this removes any rationale
  for ASM to become an agent registry:
  https://aws.amazon.com/about-aws/whats-new/2026/04/aws-agent-registry-in-agentcore-preview/
  https://docs.cloud.google.com/agent-registry/register-agents
- Salesforce AgentExchange already combines discovery, procurement, private
  pricing, and A2A/MCP distribution:
  https://help.salesforce.com/s/articleView?id=005387252&language=en_US&type=1
- A2A's roadmap now prioritizes validation tooling and a compatibility kit;
  this supports conformance/evaluation as a shovel rather than a new runtime:
  https://a2a-protocol.org/latest/roadmap/
- MCP maintainers explicitly separate discovery from selection and ask for
  quantitative evidence before standardizing another mechanism:
  https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/3264

## Scenario screen

| Scenario | Pain | ASM fit | Competition | Current call |
|---|---:|---:|---:|---|
| Supervisor chooses agents exposed as tools | Real | Medium | frameworks own the decision loop | Benchmark only; not the product lead |
| Minimal team assembly under coverage/budget/risk constraints | Real for parallel goals | Medium | orchestrators and routing research | Algorithm research only |
| Cross-organization A2A delegation | High when agents are dynamic and externally owned | Very high | trust/reputation proposals are fragmented | Lead product-discovery scenario |
| Cross-agent observed outcome network | High once unknown agents transact repeatedly | Very high | ERC-8004 and A2A trust proposals exist but evidence quality is unresolved | Lead differentiation hypothesis |
| Failure replacement and fallback chain | High in long-running tasks | High | gateways handle retries, not portable decision evidence | Lead runtime hypothesis |
| Shared quota/capacity across workers | High at scale | Medium-high | schedulers/gateways | Consume live signals; do not schedule |
| Owner-aligned choices shared across agents | Real personalization problem | Medium-high | High from memory products | Differentiate on policy, not memory |
| Delegation decision receipts | Useful for audits and disputes | Medium-high | High from tracing/gateways | Complement trace; never replace it |
| Group-chat next-speaker choice | Real | Medium | orchestrators own state and turn order | Eligibility input only |
| Cheapest/resilient agent routing | Real | Low | Very high | Do not enter |
| Multi-agent payment and settlement | Early | Low | Crowded and outside current boundary | Do not enter |

## Strongest unresolved problem

The strongest possible gap is portable, task-conditioned observed evidence for
selecting unfamiliar A2A services:

> Agent Cards say what agents claim they can do. What did independently identified
> callers observe on comparable tasks, how strong is that evidence, which version
> did it describe, and should this owner rely on it now?

A2A answers how agents describe and call each other. Its core `AgentSkill` is
largely descriptive and has no standard pricing or quality fields. AGP proposes
how gateways route capabilities. Cloud registries own inventory and governance.
Authorization engines decide whether a call is allowed. ASM may add value by
combining provider-declared facts with caller-observed evidence at selection time,
without becoming another A2A transport, identity system, registry, orchestrator,
or universal trust score.

## What ASM already has

- canonical eligibility gates;
- experimental owner-conditioned preference evidence kept locally;
- per-claim freshness and interface-surface identity;
- Selection Receipt and an early `delegates_to` concept.

These are components, not Multi-Agent product evidence. Current selector still
depends on structured taxonomy/functions, returns one winner, treats candidates
as independent services, and has no external Multi-Agent outcome benchmark.

## Hypotheses to test before building

1. Agent Card descriptions alone are insufficient for choosing unfamiliar A2A
   services on real, comparable tasks.
2. Normal A2A calls can produce privacy-safe, version-bound evidence events
   without publishing raw prompts, outputs, or traces.
3. Task-conditioned observed evidence improves at least one real selection beyond
   provider-declared facts alone.
4. Attempt denominators, evaluator diversity, disputes, and version changes can
   be represented without collapsing everything into a universal score.
5. Owner policy can remain private and consume public/private evidence summaries
   without exposing preference memory.
6. At least one external A2A producer and one independent caller want to generate
   or consume the evidence contract rather than another generic rating field.

## Go / no-go gate

Do not change ASM's tool-selection identity. Add an A2A evidence profile only
after hypotheses 1–5 have reproducible evidence and hypothesis 6 has external
counterparts. Otherwise keep the work as research and do not publish a speculative
rating schema.

## Research execution sequence

1. **Landscape audit:** map A2A trust/attestation proposals, ERC-8004, and existing
   marketplaces so ASM does not duplicate identity, storage, or generic scoring.
2. **Evidence contract:** define a minimal task-bound event, evidence levels,
   version identity, privacy rules, revocation, and disputes.
3. **A2A adapter:** generate the event from real A2A task/status/artifact data;
   attach trace or settlement proof only when available.
4. **Query value:** compare Agent Card/manifest facts with facts plus comparable
   observed evidence; expose uncertainty and insufficient evidence.
5. **Adversarial test:** simulate Sybil reviews, cherry-picking, version laundering,
   prompt injection, and refusal to co-sign.
6. **External validation:** ask one A2A producer and two independent callers to
   review or run the contract before any public schema proposal.
7. **Distribution:** only then use Product Hunt/Linear as research/distribution
   surfaces and Slack as a high-bar downstream scenario.

Stop if evidence cannot be bound to real interactions, comparable cohorts cannot
be formed, privacy requires raw-log publication, or observed evidence fails to
improve decisions. Do not approach Slack first: it is the largest trend signal
but the highest-bar distribution surface.

Detailed product hypothesis: `docs/design/a2a-experience-evidence-network.md`.

Current mechanism validation and its limits:
`docs/validation/a2a-multi-agent-validation-v0.1.md`.

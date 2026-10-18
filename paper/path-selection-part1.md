# Evidence-Informed Path Selection for Resource-Constrained Agents

Working manuscript, Part I: introduction and problem formulation.
2026-09-22. No new empirical result is claimed. This is a prospective research
framing, separate from the historical `asm-paper-draft.md`; its numerical claims
and adoption descriptions are not carried into this manuscript without re-audit.

## 1. Introduction

An agent pursuing a goal must choose not only its next action, but also how to
obtain the capabilities and information needed to act. A task may be completed
through a local program, a hosted tool, a different execution environment, or
delegation. These alternatives differ in availability, compatibility, cost and
observed effectiveness. Choosing a technically capable option is therefore not
sufficient: a useful path must also fit the current account, environment, task
requirements and resource limits.

The implementation boundary of a capability is unstable. A procedure implemented
as a tool may later become a model capability; a workflow may move into a harness
or be delegated to another agent. This motivates describing alternatives as
execution paths rather than assuming a permanent taxonomy of tools. The broader
question is how a system should allocate its next unit of resources among acting,
acquiring information, obtaining external assistance and changing its own methods.
The present investigation addresses only the first practical instance: choosing
among available execution paths for a specified task.

This framing has precedents. Rational metareasoning evaluates computation by its
expected contribution to subsequent decisions [1]. Intelligent delegation treats
task allocation together with authority, responsibility and verification [2].
Research on self-improving agents studies the generation and evaluation of modified
agents, including changes to the improvement procedure itself [3]. These works
motivate a broad choice space. They do not establish demand for an additional
selection product or demonstrate that such a product benefits ordinary workloads.

### 1.1 Reasoning quality and decision evidence

A capable host may already reason well over the information it has. Its difficulty
can instead be obtaining sufficiently relevant evidence before committing to a
path. Documentation may describe a capability without establishing account access;
a posted price may not match the actual route; a successful trial may have used a
different environment. Repeating discovery, setup and trial execution can consume
resources even when the final decision is straightforward.

The proposed ASM hypothesis is that attributable, reusable path evidence can make
some choices less expensive or reduce subsequent correction. Relevant observations
include availability, access conditions, price, task outcomes and switching effort.
This is distinct from assuming that ASM possesses a stronger reasoning model.
However, evidence has acquisition and maintenance costs. Reuse is beneficial only
when applicable observations remain useful often enough to offset those costs.
Stronger models, better host tooling, or inexpensive live trials may eliminate the
advantage. Whether the hypothesis holds is an empirical question.

### 1.2 Relationship to adaptation and memory

Existing systems already learn or reuse procedures. LangMem describes updating
agent instructions from interaction feedback [4]. ACE develops contexts through
incremental generation, reflection and curation [5]. GEPA proposes, evaluates and
selects prompt changes using execution feedback [6]. Thus neither external memory,
experience reuse nor improvement selection is claimed as a novel ASM capability.

The intended distinction to investigate is operational: can evidence about
alternative execution paths, qualified by its applicable conditions, improve a
host's real decisions at acceptable total cost? This manuscript does not propose
a general memory system, parameter-training method, or complete self-improvement
architecture. It also does not claim that any neighboring system lacks the ability
to perform this function.

## 2. Problem formulation and scope

Let a decision instance contain a task goal g, environment e, user constraints c,
remaining resource budget b, and a set of candidate paths P. A path describes an
executable way to pursue the goal using specified capabilities and prerequisites.
Evidence E consists of observations associated with their sources, times, task
conditions and relevant versions. Missing or incompatible evidence remains unknown;
it is not converted into a favorable default.

Selection may return a feasible path, a request for additional evidence or necessary
authorization, or an explicit inability to select. Preference comparisons must not
silently override hard constraints. Estimated plan cost is distinct from a host's
monetary reservation and from eventual billed cost. The conceptual formulation
does not assume a single scalar objective or a universal ranking algorithm.

Evidence collection and verification themselves consume budget. Consequently,
selection overhead and preparation cannot be excluded from an economic evaluation.
A successful artifact does not alone establish correct selection, while an accurate
decision record does not establish successful execution. Both must be assessed
against the same task acceptance criteria and an independent execution record.

### 2.1 Research question

For matched tasks, models, permissions and acceptance criteria, does supplying
reusable, environment-qualified path evidence improve the net outcomes of path
selection relative to an ordinary agent with search or appropriate host rules?

Relevant outcomes are accepted completion, total resource cost, elapsed time and
owner intervention. Fewer corrections cannot compensate for unreported quality
losses or acquisition costs. The first cycle charges all preparation effort;
subsequent reuse, if observed, is a separate analysis rather than hypothetical
amortization across future customers.

### 2.2 Falsifiable hypotheses and exclusions

H1: in workloads with repeated evidence-acquisition or path-selection errors,
reusable evidence reduces correction effort or total accepted-completion cost
without reducing acceptance or violating the predefined constraints.

H2: any benefit depends on evidence applicability and freshness; stale or mismatched
observations can remove or reverse it. This is a proposed mechanism to investigate,
not a result established by the current development experiment.

The null remains viable: ordinary search and native host rules may be sufficient,
or ASM's overhead may exceed its benefit. A package comparison cannot independently
identify the effects of evidence representation, acquisition and selection logic;
that requires controlled ablations. Small author-owned development cases cannot
establish generalization, willingness to pay, or a defensible data advantage.

Capability acquisition and allocation of recursive-improvement budgets are
long-term extensions outside the present evaluation. The existing development
contract and reporting schedule remain unchanged. This Part I contains no abstract
claiming results, no validated contribution list, and no conclusion of superiority.

## References

[1] Stuart Russell. Bounded Optimality and Rational Metareasoning. Author's research
overview. https://people.eecs.berkeley.edu/~russell/research-bo.html

[2] Nenad Tomašev, Matija Franklin, Simon Osindero. Intelligent AI Delegation. 2026.
https://arxiv.org/abs/2602.11865

[3] Jenny Zhang et al. Hyperagents. 2026. https://arxiv.org/abs/2603.19461

[4] LangChain. LangMem SDK for agent long-term memory. 2025.
https://www.langchain.com/blog/langmem-sdk-launch

[5] Qizheng Zhang et al. Agentic Context Engineering: Evolving Contexts for
Self-Improving Language Models. v3, 2026. https://arxiv.org/html/2510.04618v3

[6] Lakshya A. Agrawal et al. GEPA: Reflective Prompt Evolution Can Outperform
Reinforcement Learning. v2, 2026. https://arxiv.org/abs/2507.19457v2

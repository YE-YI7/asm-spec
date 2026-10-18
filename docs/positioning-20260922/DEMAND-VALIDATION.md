# Demand validation: public problem evidence

2026-09-22. Desk research, not interviews or a market-size estimate.

## Decision

There is credible public evidence of people spending resources on unsuitable
execution methods and manually changing methods. There is not yet evidence that
they will adopt or pay for ASM, or that shared historical evidence is the missing
ingredient. Continue narrow validation; do not declare product-market fit or
freeze the product as an evidence marketplace.

The best-supported question is when to continue, switch, or test an alternative
as the task reveals new information. It occurs both before a batch and during a
run. This broadens the previous preflight-only scenario hypothesis without adding
new scope to DEV6.

## Method and evidence quality

Used agent-reach GitHub CLI and Exa search, supplemented by web search/open.
Read six issue bodies with their comment histories across Firecrawl, Crawl4AI,
Docling and Claude Code; inspected a browser-use vision-cost request, an n8n
discussion, two related PR states, and supplier documentation. Sampling was
deliberately pain-seeking, not random. Search hits and comment counts are not
independent customer counts. Public handles are leads, not verified identities,
roles, companies or customers.

Issue reports below are first-person accounts, not reproduced outcomes or audited
bills. Dates distinguish historical failures from current product behavior.
Reddit OpenCLI read of `1tjgsiq` returned HTTP 403 and no content; excluded from
the evidence supporting the decision. No interviews, external messages, installs,
paid task runs or production changes were made. Agent Reach reported v1.5.0 current.
Primary-source references and concise findings are recorded below.
No private workspace records or complete discussion dumps are published.

## Evidence ledger

### 1. Batch web extraction: resource loss and an actual change of method

[Firecrawl #3552](https://github.com/firecrawl/firecrawl/issues/3552), opened
2026-05-18 by `brandon-charles-novice-developer`, reports failed extraction across
SPA careers pages and roughly 900 credits consumed without output. The author
changed to search followed by individual scrapes, losing pagination/unindexed
coverage. The stated 15-call count does not align cleanly with the table; do not
derive a failure rate or average cost from it. Credits are not a verified invoice.
Later commenters propose diagnostics and alternative acquisition paths; their
success claims are not independent replication. One later example page had no
jobs, which cannot establish what it contained at the original failure date.

Signal: real task, resource complaint, implemented workaround and explicit tradeoff.
ASM opportunity: detect an unsuitable acquisition method before repeating it.
Countercase: a vendor bug fix or existing fallback may remove the need entirely.

### 2. Cross-site collection: generalized behavior versus site-specific patches

[Crawl4AI #731](https://github.com/unclecode/crawl4ai/issues/731), opened 2025-02-20.
In March 2026, `IbrahimLaeeq` described wanting a solution across websites instead
of per-site scroll settings, asked whether to wait for a release or write custom
code, and reported about 20 minutes of scrolling on skills.sh with only bottom
content captured. Maintainer release guidance was subsequently qualified; a
proposed fix is not the same as a shipped verified fix. [PR #1868](https://github.com/unclecode/crawl4ai/pull/1868)
was open and unmerged when checked.

Signal: repeated follow-up, a concrete time cost and an explicit build/wait choice.
Countercase: this user primarily asks for a better crawler, not a neutral selector.
The thread also shows an ordinary coding agent suggesting a similar workaround.

### 3. Endpoint compatibility: nominal success without usable output

[Firecrawl #4252](https://github.com/firecrawl/firecrawl/issues/4252), opened
2026-08-06 by `geertvanzoest`, reports JSON extraction failing over a self-hosted
LiteLLM/llama.cpp path while markdown extraction works. The author varied endpoint
and schema, found a working Chat Completions path, and requested configurable
fallback plus clearer failure reporting. These are the reporter's experiments,
not ours.

Signal: environment-specific comparative evidence can matter more than model name.
Countercase: fixing endpoint configuration or the SDK is a strong simpler solution.

### 4. Document processing: explicit requests for conditional escalation

[Docling #2963](https://github.com/docling-project/docling/issues/2963), opened
2026-02-08 by `zwangjacket`, requests detection of corrupted text layers and OCR
fallback; forced OCR is the reported workaround. No monetary loss is supplied.
Only the original request is counted as demand evidence; later prototype offers
are supply-side proposals, not additional customer demand.

[Docling #3464](https://github.com/docling-project/docling/issues/3464), opened
2026-05-17 by `drukpa1455`, asks to skip unnecessary OCR on usable native-text
pages while retaining it on scanned pages. A document-wide toggle is too coarse
for mixed PDFs. The same author submitted [PR #3465](https://github.com/docling-project/docling/pull/3465),
which was closed and unmerged at inspection. This shows implementation effort,
not paid demand; no reason for closure is inferred.

Signal: choosing the method based on the actual input is explicitly requested.
Countercase: both requests seek native Docling behavior. Simple quality heuristics
could be sufficient; neither establishes the need for a cross-provider evidence store.

### 5. Coding agents: a decision that becomes clear only during execution

[Claude Code #27665](https://github.com/anthropics/claude-code/issues/27665), opened
2026-02-22, asks for model-routing controls. Its usage-cost table is explicitly
virtual cost, not a bill; historical claims about v2.1.50 are not current product facts.
[stefmf's September 3 comment](https://github.com/anthropics/claude-code/issues/27665#issuecomment-5521409138)
describes manually escalating after failed attempts and wanting execution-aware
switching. [warku123's May 13 comment](https://github.com/anthropics/claude-code/issues/27665#issuecomment-4439151702)
reports building a proxy whose economics suffer from model-specific caching.
That is an unreplicated implementation report, not a universal routing impossibility.

Signal: users explicitly want allocation help and some invest in workarounds.
Countercase: useful signals may live in the current transcript, not shared history;
native model controls or simple rules may win. Switching overhead belongs in cost.

## Alternatives and negative evidence

- [n8n discussion](https://community.n8n.io/t/agent-not-using-correct-tools-and-sending-wrong-mismatched-inputs/290395):
  the original poster reports wrong tools despite prompt changes, then success after
  recreating the node. Replies dispute an asserted corruption diagnosis. Treat the
  root cause as unresolved. This is a configuration/registration counterexample,
  not evidence that better semantic tool ranking is required.
- [Stagehand caching](https://www.browserbase.com/blog/stagehand-caching): the vendor
  already documents reuse of resolved actions with page-state validation and fallback
  on mismatch. Its performance claims were not independently tested. Native reuse
  competes with the proposed benefit; it is not an empty market.
- [Firecrawl enhanced mode](https://docs.firecrawl.dev/features/enhanced-mode): native
  acquisition options exist. A universal selector must beat relevant native behavior,
  not an artificially weak no-fallback baseline.
- [browser-use #450](https://github.com/browser-use/browser-use/issues/450): a historical
  request for separate vision models is a weak cost-preference signal, without
  quantified workload, verified expenditure or adoption commitment.
- Promotional Reddit/search results and supplier migration pitches were excluded
  from customer-demand counts. They can identify alternatives, not prove buying intent.

## What is and is not supported

| Hypothesis | Current judgment |
|---|---|
| Unsuitable methods cause real wasted work | Supported by multiple first-person reports; magnitude unaudited |
| People actively try changing methods | Supported by reported workarounds and implementation effort |
| Some want conditional method/model selection | Explicitly requested in document and coding cases |
| These users want another standalone product | Unproven; many ask existing maintainers to fix native behavior |
| Shared comparable past evidence is the missing input | Unproven; live state and deterministic rules may suffice |
| ASM lowers total cost at equal acceptance | Untested here |
| Users will pay ASM or retain its integration | No evidence collected |

## Concrete leads and follow-up instrument

Not contacted. Highest-information public leads are:

1. `brandon-charles-novice-developer`: recurring extraction workload, credit loss,
   fallback tradeoff. Ask for a sanitized failed run, current workaround and whether
   the problem persists after upgrades. Do not infer a business from the workload.
2. `IbrahimLaeeq`: cross-site requirement and custom-code versus waiting decision.
   Ask which facts would actually have changed that decision and which patches remain.
3. `stefmf`: mid-task escalation pain. Ask for a trace around the switch and how
   success, retries and manual attention are measured.
4. `zwangjacket` / `drukpa1455`: input-conditioned processing. Ask whether native
   detection solves the whole need or whether multiple engines are actually compared.

For any later authorized interview, reconstruct the last incident before describing
ASM: goal/acceptance, available alternatives, failed work, current fix, frequency,
resource records, and what information existed before commitment. End with a
behavioral request for a bounded trial, not "would you use an AI router?".

A later trial should compare native defaults, a simple explicit rule and a
state/evidence-informed choice. If no relevant previous observations exist, do not
manufacture an evidence advantage. Include setup, verification, switching and
retries; measure accepted output and human correction. A useful discriminator is
whether the user retains the recommendation or integration on another real task.

This is a proposed next validation step, not a launched trial or a replacement for
the existing DEV6 contract. No new metric, deadline, spending or outreach authorized.

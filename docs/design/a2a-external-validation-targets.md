# A2A external validation targets

**Date:** 2026-08-31  
**Status:** shortlist; no partnership or adoption claim

| Target | What it actually does | Validation role | Current action |
|---|---|---|---|
| [a2a-testbed](https://github.com/a2aproject/A2A/discussions/1826) | public A2A reference endpoint, conformance runner, multi-agent scenarios, wire observer | external producer plus protocol observer | maintainer confirmed a migration is needed and requested the reproducer; [standalone script delivered](https://github.com/a2aproject/A2A/discussions/1826#discussioncomment-18226134) |
| [OpenClaw Research](https://github.com/a2aproject/A2A/discussions/1762) | reports controlled agent-to-agent quality experiments and asks for test partners | independent caller/evaluator candidate | [requested one redacted experiment record or schema](https://github.com/a2aproject/A2A/discussions/1762#discussioncomment-18217352) |
| [a2a-overture](https://github.com/kapil8811/a2a-overture) | cross-SDK A2A conformance suite | independent conformance evidence adapter | [requested one machine-readable output schema or fixture](https://github.com/a2aproject/A2A/discussions/1654#discussioncomment-18217353) |
| [NEXUS](https://github.com/Francosimon53/nexus) | A2A marketplace with task routing and outcome-based trust | external producer candidate | verify repository and live-service freshness |
| [MoltBridge](https://api.moltbridge.ai) | bilateral Ed25519 task attestations and credibility packets | signature/interoperability reviewer | inspect current Agent Card and attestation shape |

Preferred first validation triangle:

1. one producer exposes real Agent Cards and all task attempts;
2. a2a-testbed or a2a-overture supplies interface/conformance observations;
3. an independent task evaluator supplies objective outcome checks;
4. ASM combines those dimensions for selection without replacing any source.

Do not send a generic ASM pitch. Each approach must carry one reproduced fact,
one minimal artifact, and one narrow question the target is qualified to answer.

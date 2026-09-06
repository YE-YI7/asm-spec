# A2A SDK live validation v0.1

**Date:** 2026-08-31
**Result:** PASS
**SDK:** `a2a-sdk 1.1.2`
**Transport:** A2A 1.0 JSON-RPC over local HTTP

## Result

Two deterministic local agents were exposed through real A2A Agent Cards and
JSON-RPC endpoints. A real A2A client discovered both cards and completed 14
unique Task lifecycles.

The first 12 calls produced task-bound, redacted, Ed25519-signed experience
events. The evidence query selected `stable-agent` for a second worker. That
worker's selected call passed; a real counterfactual call to the unselected
`drifting-agent` reproduced the expected failure.

| Check | Result |
|---|---|
| two Agent Cards discovered | PASS |
| 14 unique A2A Tasks returned | PASS |
| 12 evidence-event signatures verified | PASS |
| raw task and artifact content absent from events | PASS |
| stable agent selected from prior outcomes | PASS |
| second worker's selected call passed | PASS |
| unselected agent's failure reproduced | PASS |

Observed fixture summaries:

| Agent | Objective pass estimate | 95% Wilson interval | Events |
|---|---:|---:|---:|
| `stable-agent` | 1.0000 | 0.6097–1.0000 | 6 |
| `drifting-agent` | 0.6667 | 0.3000–0.9032 | 6 |

The wide intervals are intentional evidence that six calls are not enough for a
production quality claim.

## Compatibility finding

A2A v1 Agent Cards do not expose a top-level `url`; invocation endpoints live in
`supportedInterfaces`. The event adapter was corrected to accept ProtoJSON
`supportedInterfaces` and Python-style `supported_interfaces`, while retaining
compatibility with the earlier top-level fixture field.

The SDK's JSON-RPC routes require its `http-server` extra in this environment;
the base package alone raised a missing `sse_starlette` import. This remains an
experiment dependency and was not added to ASM's public package requirements.

## Claim boundary

This validates protocol and mechanism feasibility only:

- the agents are deterministic local fixtures, not independent external agents;
- the three evaluator keys were generated in one process, not by independent
  organizations;
- signatures are caller-side Ed25519 signatures, not Agent Card JWS or bilateral
  server attestations;
- the objective evaluator is simple arithmetic, not an open-ended agent task;
- the scoring controls remain uncalibrated synthetic controls;
- no external adoption, security review, or market demand is established.

## Next gate

1. replace arithmetic with one useful task that has deterministic acceptance;
2. run two independently operated A2A endpoints;
3. obtain caller and provider identity/signature material independently;
4. test one negative event, counter-evidence, and dispute relation;
5. confirm the producer can emit all attempts rather than selected successes.

Run:

```bash
uv run --isolated --python 3.12 \
  --with 'a2a-sdk[http-server]>=1.0.3' \
  --with uvicorn --with starlette --with httpx --with cryptography \
  python experiments/a2a_sdk_live_validation.py
```

# Draft: ASM → Logion interoperability outreach

**Status:** owner-review draft only. Do not post without explicit approval.

Suggested location: a dedicated issue in `nicolasmelo1/logion`, not a comment
on an unrelated ASM or Logion issue.

Suggested title:

> Explore one ASM–Logion fixture: selection decision → native payment receipt → observed evidence

Suggested body:

```md
Hi Nicolas — I found Logion's public [ASM collaboration and protocol
convergence plan](https://github.com/nicolasmelo1/logion/blob/main/future-roadmap/asm-collaboration-and-protocol-convergence.md)
and the accompanying [implementation gate](https://github.com/nicolasmelo1/logion/blob/main/plans/asm-logion-collaboration-and-protocol-convergence-gate.md).
Thank you for stating the overlap plainly and, especially, for preferring to
remove duplicate protocol work rather than add another adapter.

I am open to a bounded interoperability check. My current working boundary is:

- AI Catalog / ARD / MCP surfaces discover the artifact or service;
- ASM normalizes declared selection inputs, applies a reproducible local
  policy, and emits a **selection receipt**;
- MPP, x402, Stripe, or another chosen rail remains authoritative for its own
  runtime quote and **payment receipt**;
- Logion records consented observed evidence and declared-versus-observed
  reconciliation, referencing the earlier artifacts by subject/version and
  digest.

The distinction between selection and payment receipts matters because MPP now
defines a native Payment-Receipt. I do not want ASM and Logion to duplicate a
settlement fact that the selected rail already proves. “One receipt” may be
best expressed as **one authoritative receipt per event**, linked into one
trace.

For a first fixture, I suggest one harmless resource and five artifacts:

1. one AI Catalog/MCP identity plus immutable version/digest;
2. one small ASM selection descriptor with declared eligibility/value facts;
3. one local policy decision and ASM selection receipt;
4. one native execution/payment result, if payment is involved;
5. one Logion observation that preserves issuer, consent, timestamp, and links
   the preceding digests without merging them into a universal score.

Before implementation, could we compare a one-page ownership matrix covering:
canonical subject identity, declared vs observed claims, local policy,
selection receipt, payment receipt, and evidence/improvement events?

ASM can contribute the selection fixture, schema validation, deterministic
policy/receipt checks, and an MCP/AI Catalog adapter. It would help if Logion
could bring the smallest concrete current usage/evidence artifact that already
exists in code, so the seam is designed against reality rather than both
roadmaps.

This is an exploration, not an adoption, partnership, endorsement, or shared
governance announcement. If the fixture reveals duplicate identities, duplicate
payment facts, or more translation than user value, remaining independent is a
valid result.

Would you be open to using this issue for the ownership matrix and then deciding
whether the single fixture is worth building?
```

## Owner checks before posting

- Confirm the author name and preferred form of address.
- Replace `main` links with commit-pinned links if the plan may move.
- Confirm that ASM's public docs consistently call its artifact a “selection
  receipt,” not a settlement/payment receipt.
- Do not promise a call, deadline, co-maintenance, or code delivery unless the
  owner wants that commitment.
- If Logion has already opened a dedicated thread, reply there instead of
  creating a duplicate issue.

# ASM–Logion bounded interoperability fixture

This offline fixture tests one identity and digest boundary. It does not claim
Logion adoption, partnership, production traffic, a deployed service, or a
cryptographic attestation.

The ASM tests prove only ASM-owned behavior. The mapping marks Logion-owned
resource binding, usage-observation compatibility, and later evidence linking
as `pending` until they run in Logion's public fixture and local devrig.

## Authority split

- The AI Catalog `identifier` and `version` name the source artifact.
- The SHA-256 of `resource-artifact.json` represents the immutable content that
  a Logion `ResourceVersion` may bind to together with its media type.
- Logion remains authoritative for assigning the opaque `resource_id` and
  `version_id`; this fixture leaves both unset.

`ai-catalog.json` is a complete one-entry catalog rather than a detached entry.
The mapping records the exact AI Catalog and ARD commits pinned by Logion when
this fixture was prepared. Its `.example` URLs are reserved documentation
identities and are intentionally not network endpoints.

Protocol basis:

- [AI Catalog commit `2882548`](https://github.com/Agent-Card/ai-catalog/commit/28825483143ce9f3b344ed01dc2771d4adf02d01)
- [ARD commit `5fa2f5a`](https://github.com/ards-project/ard-spec/commit/5fa2f5aef790b478319f6a3b43adf4661b0ed0e0)

The fixture is licensed under the adjacent `LICENSE`. A copy placed in another
repository must retain that copyright and permission notice. Contributions to
Logion must also follow its DCO sign-off requirement.
- ASM `service_id` is a source alias.
- The ASM manifest digest pins the selection metadata consulted at decision
  time. It does not define the Logion resource version.
- The Selection Receipt has its own digest so a later evidence event can refer
  to the exact unsigned receipt without copying its potentially sensitive task
  or selection fields.
- Selection Receipt v0.2 is unsigned. Its `selector.name` is a claimed producer
  label, not a verified issuer.

`asm-manifest-metadata-update.json` changes only selection metadata. The
resource artifact stays byte-for-byte identical while the ASM manifest digest
changes. Logion still has to verify that this produces no new
`ResourceVersion`; the ASM mapping records that check as pending.

`approval_required` is a policy result, not proof that authorization occurred.
Real systems must not upload a raw Selection Receipt without an explicit
privacy policy and consent; the task text may contain sensitive user intent.

## Verify

The public `asm-protocol==0.5.2` release is pinned only for manifest linting:

```bash
python3 -m pip install "asm-protocol==0.5.2"
asm-lint examples/interop/logion/asm-manifest.json \
  --as-of 2026-08-22 --format json
```

The released 0.5.2 receipt generator emits the frozen v0.1 shape and still
identifies itself as 0.5.1. This branch moves the enriched receipt to v0.2 for
0.5.3, adding the machine-readable unsigned status without silently changing
the already-consumed v0.1 contract. The checked-in v0.2 receipt is not
reproducible from the unmodified public 0.5.2 generator.

The 0.5.2 lint implementation already used the canonical bytes now named
`asm-json-sort-keys-v1`, but its report did not emit the hash and
canonicalization labels separately. Version 0.5.3 and receipt v0.2 add
`hash_algorithm: sha256` and the canonicalization label without changing the
manifest digest bytes.

From this source checkout:

```bash
python3 tools/build_logion_interop_fixture.py --check
python3 -m pytest tools/asm-gen/test_logion_interop_fixture.py
```

The generator owns `selection-receipt.json` and `source-mapping.json`. Run it
without `--check` only when intentionally refreshing those generated outputs.

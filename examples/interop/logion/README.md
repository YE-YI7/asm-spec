# ASM–Logion bounded interoperability fixture

This offline fixture tests one identity and digest boundary. It does not claim
Logion adoption, partnership, production traffic, a deployed service, or a
cryptographic attestation.

## Authority split

- The AI Catalog `identifier` and `version` name the source artifact.
- The SHA-256 of `resource-artifact.json` represents the immutable content that
  a Logion `ResourceVersion` may bind to.
- Logion remains authoritative for assigning the opaque `resource_id` and
  `version_id`; this fixture leaves both unset.
- ASM `service_id` is a source alias.
- The ASM manifest digest pins the selection metadata consulted at decision
  time. It does not define the Logion resource version.
- Selection Receipt v0.1 is unsigned. Its `selector.name` is a claimed producer
  label, not a verified issuer.

`asm-manifest-metadata-update.json` changes only selection metadata. The
resource artifact stays byte-for-byte identical, so the expected Logion
resource version key stays unchanged while the ASM manifest digest changes.

## Verify

The public `asm-protocol==0.5.2` release is pinned only for manifest linting:

```bash
python3 -m pip install "asm-protocol==0.5.2"
asm-lint examples/interop/logion/asm-manifest.json \
  --as-of 2026-08-22 --format json
```

The released 0.5.2 receipt generator still identifies itself as 0.5.1 and does
not emit the machine-readable unsigned status. This branch fixes that behavior
for 0.5.3. It must not claim that the checked-in receipt is reproducible from
the unmodified public 0.5.2 generator.

From this source checkout:

```bash
python3 tools/build_logion_interop_fixture.py --check
python3 -m pytest tools/asm-gen/test_logion_interop_fixture.py
```

The generator owns `selection-receipt.json` and `source-mapping.json`. Run it
without `--check` only when intentionally refreshing those generated outputs.

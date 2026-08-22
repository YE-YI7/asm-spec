# DeepSeek Harness selection-boundary fixture

This synthetic fixture exercises one proposed M3 contract seam for DeepSeek
Harness (DSH): an immutable Bundle identity can point to mutable Selection
Facts without absorbing the current facts digest into the artifact identity.

It is intentionally narrow:

- `bundles/*/` are minimal, synthetic DSH Bundles with `package.json`, a Cordis
  patch, and an entry point. Each package carries a provisional, namespaced
  Selection Facts reference.
- `sidecars/*.selection-facts.json` are ASM v0.3 manifests used as registry
  sidecars. They carry compatibility, reachability, setup, cost, risk,
  provenance, expiry, and evidence references.
- `selection-receipt.json` records one deterministic choice, its full candidate
  set, taxonomy, constraints, and the digest of every sidecar considered.
- `fixture-result.json` proves that updating the `search-safe` sidecar changes
  the Selection Facts digest while leaving its Bundle metadata digest unchanged.

The field placement under `metadata.io.github.ye-yi7.asm.selection-facts` is a
fixture encoding, not an accepted DSH package field. It exists to make the
identity boundary executable while upstream contract placement is discussed.

## Reproduce

From the repository root:

```bash
python3 tools/build_dsh_selection_fixture.py --check
python3 -m pytest tools/asm-gen/test_dsh_selection_fixture.py
```

Use `--write` after intentionally editing a source Bundle document or sidecar.
The builder validates every sidecar against ASM v0.3 before generating the
receipt and result document.

## Trust and scope

The receipt is an **unsigned audit record**. It is not authorization, an
execution mandate, a payment instruction, or evidence that either candidate
ran. `approval_required: true` remains a selection fact for an independent
permission boundary to enforce.

ASM 0.5.2 does not yet encode `verification_status` inside Selection Receipt
v0.1, so `fixture-result.json` records `unsigned` alongside the receipt digest.
That explicit limitation must remain until the receipt contract itself grows a
machine-readable verification field.

This fixture is not a task planner, installer, evaluator, CommitDecision,
security sandbox, official DSH standard, official DeepSeek integration, or
adoption claim. The installable DSH adapter in
`integrations/deepseek-harness/` remains a separate working prototype.

# ASM → guarded HCL evidence fixture

This independent consumer fixture validates one exact ASM Selection Receipt and
one exact synthetic DSH Bundle against the generic contracts merged in
[`Jstn-1g/dsh-guarded-hcl#11`](https://github.com/Jstn-1g/dsh-guarded-hcl/pull/11).

It proves only this deterministic identity and rejection chain:

```text
ASM Selection Receipt v0.1
  + exact Git Bundle blobs and modes
  → RunnerBinding v0.1
  → EvaluationEvidence v0.2
  → CommitDecision v0.1
```

The dependency is integrity-locked to upstream merge commit
`2c1eede7af4928afca422ff034fcf1fa622609e6`. Artifact bytes and executable
modes are read from the current Git tree, not from a checkout that may apply
line-ending filters or infer permissions. The committed attributes also pin
the generated JSON and receipt-schema files to LF for byte-stable Windows
checks.

## Reproduce

```bash
cd examples/interop/deepseek-harness-guarded-evidence
npm ci --ignore-scripts
npm run check
```

`npm run check` verifies the committed generated documents and runs the
positive chain plus independent mutations of the receipt schema/content,
selected service and evidence set, exact Bundle bytes and modes, RunnerBinding
digest, candidate identity, artifact identity, and the ASM receipt-schema URI.

The earlier selection-boundary fixture uses its own canonical content-map
digest. This fixture intentionally recomputes the same immutable Git blobs and
modes under the domain-separated guarded-HCL
`artifact-jcs-sha256:v0.1` profile, so the two artifact digest strings differ.

## Boundary

The evidence metric is `contract_conformance`. It does not report task quality,
real execution, authorization, a signature, official DeepSeek integration, or
ecosystem adoption. The fixture does not activate a Bundle. It shows that a
caller can join ASM selection evidence to the implementation-neutral guarded
HCL contract and fail before CommitDecision when a bound identity changes.

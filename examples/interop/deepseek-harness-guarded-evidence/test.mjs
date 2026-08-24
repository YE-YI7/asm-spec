import assert from 'node:assert/strict'
import test from 'node:test'

import { digestArtifact } from 'dsh-guarded-hcl/artifact'
import { evaluateCandidate } from 'dsh-guarded-hcl/gate'
import { digestRunnerBinding } from 'dsh-guarded-hcl/runner-binding'

import {
  FixtureBindingError,
  buildFixture,
  verifyFixtureInputs,
} from './build.mjs'

function clone(value) {
  return structuredClone(value)
}

function expectCode(fn, ErrorType, code) {
  assert.throws(fn, (error) => {
    assert.equal(error instanceof ErrorType, true)
    assert.equal(error.code, code)
    return true
  })
}

test('accepts the exact ASM receipt, Git artifact, binding, and evidence chain', async () => {
  const fixture = await buildFixture()
  assert.equal(fixture.decision.accepted, true)
  assert.deepEqual(fixture.decision.reasons, [])
})

test('rejects an unknown Selection Receipt field at the schema boundary', async () => {
  const fixture = await buildFixture()
  const receipt = clone(fixture.receipt)
  receipt.authorization = true
  expectCode(
    () =>
      verifyFixtureInputs({
        ...fixture,
        receipt,
      }),
    FixtureBindingError,
    'SELECTION_RECEIPT_SCHEMA_INVALID',
  )
})

test('rejects Selection Receipt byte/content mutation', async () => {
  const fixture = await buildFixture()
  const receipt = clone(fixture.receipt)
  receipt.selection_reason += ' tampered'
  expectCode(
    () => verifyFixtureInputs({ ...fixture, receipt }),
    FixtureBindingError,
    'SELECTION_RECEIPT_DIGEST_MISMATCH',
  )
})

test('rejects Selection Receipt candidate substitution', async () => {
  const fixture = await buildFixture()
  const receipt = clone(fixture.receipt)
  receipt.selected.service_id = 'dsh-fixture/search-fast@1.0.0'
  expectCode(
    () => verifyFixtureInputs({ ...fixture, receipt }),
    FixtureBindingError,
    'SELECTION_RECEIPT_CANDIDATE_MISMATCH',
  )
})

test('rejects a selected service absent from the receipt evidence set', async () => {
  const fixture = await buildFixture()
  const receipt = clone(fixture.receipt)
  receipt.evidence = receipt.evidence.filter(
    (item) => item.service_id !== receipt.selected.service_id,
  )
  expectCode(
    () => verifyFixtureInputs({ ...fixture, receipt }),
    FixtureBindingError,
    'SELECTION_RECEIPT_EVIDENCE_MISSING',
  )
})

test('rejects a valid but wrong Selection Receipt schema URI', async () => {
  const fixture = await buildFixture()
  const runnerBinding = clone(fixture.runnerBinding)
  runnerBinding.selectionReceipt.schemaUri =
    'https://example.org/schemas/selection-receipt-v0.1.json'
  expectCode(
    () => verifyFixtureInputs({ ...fixture, runnerBinding }),
    FixtureBindingError,
    'SELECTION_RECEIPT_SCHEMA_URI_MISMATCH',
  )
})

test('rejects exact artifact byte mutation before CommitDecision', async () => {
  const fixture = await buildFixture()
  const artifact = clone(fixture.artifact)
  artifact.entries[0].bytes = Buffer.concat([
    artifact.entries[0].bytes,
    Buffer.from('\nmutation', 'utf8'),
  ])
  assert.notEqual(digestArtifact(artifact), fixture.runnerBinding.artifact.digest)
  expectCode(
    () => verifyFixtureInputs({ ...fixture, artifact }),
    FixtureBindingError,
    'ARTIFACT_DIGEST_MISMATCH',
  )
})

test('rejects exact artifact mode mutation before CommitDecision', async () => {
  const fixture = await buildFixture()
  const artifact = clone(fixture.artifact)
  artifact.entries[0].mode =
    artifact.entries[0].mode === '100644' ? '100755' : '100644'
  assert.notEqual(digestArtifact(artifact), fixture.runnerBinding.artifact.digest)
  expectCode(
    () => verifyFixtureInputs({ ...fixture, artifact }),
    FixtureBindingError,
    'ARTIFACT_DIGEST_MISMATCH',
  )
})

test('gate rejects a resolved RunnerBinding mutation under the old reference', async () => {
  const fixture = await buildFixture()
  const runnerBinding = clone(fixture.runnerBinding)
  runnerBinding.selectionReceipt.digest = `sha256:${'0'.repeat(64)}`
  expectCode(
    () =>
      evaluateCandidate(fixture.policy, fixture.evidence, { runnerBinding }),
    TypeError,
    'RUNNER_BINDING_DIGEST_MISMATCH',
  )
})

test('gate rejects candidate substitution even with a recomputed binding reference', async () => {
  const fixture = await buildFixture()
  const runnerBinding = clone(fixture.runnerBinding)
  runnerBinding.candidateId = 'dsh-fixture/search-fast@1.0.0'
  const evidence = clone(fixture.evidence)
  evidence.runnerBindingRef.digest = digestRunnerBinding(runnerBinding)
  expectCode(
    () => evaluateCandidate(fixture.policy, evidence, { runnerBinding }),
    TypeError,
    'RUNNER_BINDING_CANDIDATE_MISMATCH',
  )
})

test('gate rejects artifact substitution even with a recomputed binding reference', async () => {
  const fixture = await buildFixture()
  const runnerBinding = clone(fixture.runnerBinding)
  runnerBinding.artifact.digest = `sha256:${'1'.repeat(64)}`
  const evidence = clone(fixture.evidence)
  evidence.runnerBindingRef.digest = digestRunnerBinding(runnerBinding)
  expectCode(
    () => evaluateCandidate(fixture.policy, evidence, { runnerBinding }),
    TypeError,
    'RUNNER_BINDING_ARTIFACT_MISMATCH',
  )
})

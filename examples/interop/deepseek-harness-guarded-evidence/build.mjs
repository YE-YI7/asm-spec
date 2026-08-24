import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

import Ajv2020 from 'ajv/dist/2020.js'
import {
  ARTIFACT_SHA256_PROFILE,
  digestArtifact,
} from 'dsh-guarded-hcl/artifact'
import { evaluateCandidate } from 'dsh-guarded-hcl/gate'
import {
  JCS_SHA256_PROFILE,
  digestJcs,
  parseIJson,
} from 'dsh-guarded-hcl/jcs'
import {
  RUNNER_BINDING_SCHEMA_URI,
  digestRunnerBinding,
} from 'dsh-guarded-hcl/runner-binding'

export const UPSTREAM_CONTRACT_COMMIT =
  '2c1eede7af4928afca422ff034fcf1fa622609e6'
export const UPSTREAM_CONTRACT_ARCHIVE =
  `https://github.com/Jstn-1g/dsh-guarded-hcl/archive/${UPSTREAM_CONTRACT_COMMIT}.tar.gz`
export const SELECTION_RECEIPT_SCHEMA_URI =
  'https://raw.githubusercontent.com/YE-YI7/asm-spec/main/schema/selection-receipt-v0.1.schema.json'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '../../..')
const SELECTION_FIXTURE = resolve(
  HERE,
  '../deepseek-harness-selection-boundary',
)
const GENERATED = resolve(HERE, 'generated')
const RECEIPT_PATH = resolve(SELECTION_FIXTURE, 'selection-receipt.json')
const PACKAGE_LOCK_PATH = resolve(HERE, 'package-lock.json')
const RECEIPT_SCHEMA_PATH = resolve(
  ROOT,
  'schema/selection-receipt-v0.1.schema.json',
)
const SELECTED_BUNDLE_PATH = resolve(
  SELECTION_FIXTURE,
  'bundles/search-safe',
)

const OUTPUTS = {
  'runner-binding-v0.1.json': 'runnerBinding',
  'evaluation-evidence-v0.2.json': 'evidence',
  'policy.json': 'policy',
  'commit-decision.json': 'decision',
  'validation-result.json': 'result',
}

function posixRelative(from, to) {
  return relative(from, to).split('\\').join('/')
}

export class FixtureBindingError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'FixtureBindingError'
    this.code = code
  }
}

function runGit(args, encoding = null) {
  const result = spawnSync('git', args, {
    cwd: ROOT,
    encoding,
    maxBuffer: 10 * 1024 * 1024,
  })
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(' ')} failed: ${String(result.stderr).trim()}`,
    )
  }
  return result.stdout
}

export function readGitTreeArtifact(path) {
  const rootPath = posixRelative(ROOT, path)
  const listing = runGit(['ls-tree', '-rz', 'HEAD', '--', `${rootPath}/`])
  const records = listing.subarray(0, -1).toString('utf8').split('\0')
  const entries = records.map((record) => {
    const tab = record.indexOf('\t')
    const [mode, type, sha] = record.slice(0, tab).split(' ')
    const fullPath = record.slice(tab + 1)
    if (type !== 'blob' || !fullPath.startsWith(`${rootPath}/`)) {
      throw new Error(`unsupported Git artifact entry: ${record}`)
    }
    return {
      path: fullPath.slice(rootPath.length + 1),
      mode,
      bytes: runGit(['cat-file', 'blob', sha]),
    }
  })
  if (entries.length === 0) {
    throw new Error(`no tracked artifact entries under ${rootPath}`)
  }
  return { kind: 'tree', entries }
}

function sha256Bytes(bytes) {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`
}

function compileReceiptValidator(schema) {
  const ajv = new Ajv2020({ allErrors: true, strict: true })
  return ajv.compile(schema)
}

function assertValidReceipt(receipt, validate) {
  if (!validate(receipt)) {
    throw new FixtureBindingError(
      'SELECTION_RECEIPT_SCHEMA_INVALID',
      ajvErrors(validate.errors),
    )
  }
}

function failFixture(code, message) {
  throw new FixtureBindingError(code, message)
}

function ajvErrors(errors) {
  return (errors ?? [])
    .map((error) => `${error.instancePath || '/'} ${error.message}`)
    .join('; ')
}

export function verifyFixtureInputs({
  receipt,
  runnerBinding,
  artifact,
  validateReceipt,
}) {
  assertValidReceipt(receipt, validateReceipt)
  if (runnerBinding.selectionReceipt.schemaUri !== SELECTION_RECEIPT_SCHEMA_URI) {
    failFixture(
      'SELECTION_RECEIPT_SCHEMA_URI_MISMATCH',
      'RunnerBinding selectionReceipt.schemaUri does not identify the ASM Selection Receipt v0.1 schema.',
    )
  }
  if (runnerBinding.selectionReceipt.digestProfile !== JCS_SHA256_PROFILE) {
    failFixture(
      'SELECTION_RECEIPT_DIGEST_PROFILE_MISMATCH',
      'RunnerBinding selectionReceipt.digestProfile is not the supported JCS + SHA-256 profile.',
    )
  }
  if (receipt.selected?.service_id !== runnerBinding.candidateId) {
    failFixture(
      'SELECTION_RECEIPT_CANDIDATE_MISMATCH',
      'Selection Receipt selected.service_id does not match RunnerBinding candidateId.',
    )
  }
  if (
    !receipt.evidence.some(
      (item) => item.service_id === receipt.selected.service_id,
    )
  ) {
    failFixture(
      'SELECTION_RECEIPT_EVIDENCE_MISSING',
      'Selection Receipt selected.service_id is absent from the consulted evidence set.',
    )
  }
  const receiptDigest = digestJcs(receipt)
  if (receiptDigest !== runnerBinding.selectionReceipt.digest) {
    failFixture(
      'SELECTION_RECEIPT_DIGEST_MISMATCH',
      'Selection Receipt JCS digest does not match RunnerBinding selectionReceipt.digest.',
    )
  }
  if (artifact.kind !== runnerBinding.artifact.kind) {
    failFixture(
      'ARTIFACT_KIND_MISMATCH',
      'Immutable Git artifact kind does not match RunnerBinding artifact.kind.',
    )
  }
  const artifactDigest = digestArtifact(artifact)
  if (artifactDigest !== runnerBinding.artifact.digest) {
    failFixture(
      'ARTIFACT_DIGEST_MISMATCH',
      'Immutable Git artifact digest does not match RunnerBinding artifact.digest.',
    )
  }
  return { receiptDigest, artifactDigest }
}

export async function buildFixture() {
  const [receiptText, receiptSchemaText, packageLockText] = await Promise.all([
    readFile(RECEIPT_PATH, 'utf8'),
    readFile(RECEIPT_SCHEMA_PATH, 'utf8'),
    readFile(PACKAGE_LOCK_PATH, 'utf8'),
  ])
  const receipt = parseIJson(receiptText)
  const receiptSchema = parseIJson(receiptSchemaText)
  const packageLock = parseIJson(packageLockText)
  const pinnedPackage = packageLock.packages?.['node_modules/dsh-guarded-hcl']
  assert.equal(pinnedPackage?.resolved, UPSTREAM_CONTRACT_ARCHIVE)
  assert.match(pinnedPackage?.integrity ?? '', /^sha512-[A-Za-z0-9+/]+={0,2}$/u)
  const validateReceipt = compileReceiptValidator(receiptSchema)
  assertValidReceipt(receipt, validateReceipt)
  assert.equal(receipt.selected.service_id, 'dsh-fixture/search-safe@1.0.0')

  const artifact = readGitTreeArtifact(SELECTED_BUNDLE_PATH)
  const artifactDigest = digestArtifact(artifact)
  const receiptDigest = digestJcs(receipt)
  const runnerBinding = {
    schemaVersion: '0.1',
    candidateId: receipt.selected.service_id,
    artifact: {
      profile: ARTIFACT_SHA256_PROFILE,
      kind: artifact.kind,
      digest: artifactDigest,
    },
    selectionReceipt: {
      schemaUri: SELECTION_RECEIPT_SCHEMA_URI,
      digestProfile: JCS_SHA256_PROFILE,
      digest: receiptDigest,
    },
  }
  const runnerBindingDigest = digestRunnerBinding(runnerBinding)
  const evidence = {
    schemaVersion: '0.2',
    candidateId: runnerBinding.candidateId,
    baselineDigest: 'urn:asm-fixture:baseline:not-executed',
    candidateDigest: artifactDigest,
    runnerBindingRef: {
      schemaUri: RUNNER_BINDING_SCHEMA_URI,
      digestProfile: JCS_SHA256_PROFILE,
      digest: runnerBindingDigest,
    },
    currentTask: {
      metric: 'contract_conformance',
      baselineScore: 0,
      candidateScore: 1,
    },
    requiredAnchorIds: [],
    retention: [],
    validity: [
      {
        checkId: 'selection-receipt-schema-valid',
        passed: true,
        severity: 'critical',
      },
      {
        checkId: 'git-artifact-byte-source-pinned',
        passed: true,
        severity: 'critical',
      },
      {
        checkId: 'candidate-receipt-artifact-join-valid',
        passed: true,
        severity: 'critical',
      },
    ],
    cost: null,
  }
  const policy = {
    minimumCurrentImprovement: 0,
    maximumWeightedRetentionLoss: 0,
    requireEveryRequiredAnchor: true,
    failOnValiditySeverities: ['critical', 'high'],
    maximumCostIncreaseRatio: null,
  }

  verifyFixtureInputs({ receipt, runnerBinding, artifact, validateReceipt })
  const decision = evaluateCandidate(policy, evidence, { runnerBinding })
  assert.equal(decision.accepted, true)

  const result = {
    fixtureVersion: '0.1',
    scope: 'contract-conformance-only',
    upstreamContract: {
      repository: 'Jstn-1g/dsh-guarded-hcl',
      mergeCommit: UPSTREAM_CONTRACT_COMMIT,
      archive: UPSTREAM_CONTRACT_ARCHIVE,
      archiveIntegrity: pinnedPackage.integrity,
    },
    sources: {
      artifactByteSource: 'Git blobs and modes at this repository HEAD',
      selectedBundle: posixRelative(ROOT, SELECTED_BUNDLE_PATH),
      selectionReceipt: posixRelative(ROOT, RECEIPT_PATH),
      selectionReceiptSchema: {
        uri: SELECTION_RECEIPT_SCHEMA_URI,
        sourceDigest: sha256Bytes(Buffer.from(receiptSchemaText, 'utf8')),
      },
    },
    identities: {
      candidateId: runnerBinding.candidateId,
      artifactDigest,
      selectionReceiptDigest: receiptDigest,
      runnerBindingDigest,
      decisionDigest: decision.decisionDigest,
    },
    assertions: {
      selectionReceiptSchemaValid: true,
      candidateJoinValid: true,
      artifactIdentityValid: true,
      runnerBindingResolvedBeforeDecision: true,
      commitDecisionAccepted: true,
      authorizationClaimed: false,
      executionClaimed: false,
      deepSeekAdoptionClaimed: false,
    },
  }

  return {
    receipt,
    receiptSchema,
    validateReceipt,
    artifact,
    runnerBinding,
    evidence,
    policy,
    decision,
    result,
  }
}

function render(document) {
  return `${JSON.stringify(document, null, 2)}\n`
}

async function main() {
  const mode = process.argv[2]
  if (mode !== '--write' && mode !== '--check') {
    throw new Error('usage: node build.mjs --write|--check')
  }
  const fixture = await buildFixture()
  await mkdir(GENERATED, { recursive: true })
  const stale = []
  for (const [filename, key] of Object.entries(OUTPUTS)) {
    const path = resolve(GENERATED, filename)
    const content = render(fixture[key])
    if (mode === '--write') {
      await writeFile(path, content, 'utf8')
      continue
    }
    let current
    try {
      current = await readFile(path, 'utf8')
    } catch {
      current = null
    }
    if (current !== content) stale.push(filename)
  }
  if (stale.length > 0) {
    throw new Error(`stale generated fixture files: ${stale.join(', ')}`)
  }
  console.log('ASM -> dsh-guarded-hcl evidence fixture: PASS')
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}

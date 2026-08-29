/**
 * DeepSeek Harness adapter for the ASM hosted/local selector.
 *
 * The plugin exposes one model-facing decision tool. It never invokes the
 * selected service and never treats an approval requirement as authorization.
 */
import type { Context } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'
import { defineTool, type JsonValue, type ToolDefinition } from '@deepseek-ai/dsh-tools'

export const name = 'asm-selector'
export const inject = ['tools']

export const DEFAULT_ENDPOINT = 'http://127.0.0.1:8787'
export const DEFAULT_TIMEOUT_MS = 15_000
export const DEFAULT_TOOL_NAME = 'asm_select'
export const DEFAULT_LIST_TOOL_NAME = 'asm_list_services'

export interface Config {
  /** Base URL of an ASM selector API. Task text is sent to this endpoint. */
  endpoint?: string
  /** Cooperative request timeout in milliseconds. */
  timeoutMs?: number
  /** Model-facing tool name. */
  toolName?: string
  /** Model-facing catalog-listing tool name. */
  listToolName?: string
  /** Explicitly reproduce the frozen 0.5.2 selector and v0.1 receipt contract. */
  legacyReceipt?: boolean
}

export const Config: z<Config> = z.object({
  endpoint: z.string().default(DEFAULT_ENDPOINT),
  timeoutMs: z.number().default(DEFAULT_TIMEOUT_MS),
  toolName: z.string().default(DEFAULT_TOOL_NAME),
  listToolName: z.string().default(DEFAULT_LIST_TOOL_NAME),
  legacyReceipt: z.boolean().default(false),
})

interface ResolvedConfig {
  endpoint: string
  timeoutMs: number
  toolName: string
  listToolName: string
  legacyReceipt: boolean
}

export interface SelectRequest {
  task: string
  taxonomy: string
  agent_reach?: string
  user_platform?: string
  required_functions?: string[]
  require_approval_for?: string[]
  require_agent_completable_setup?: boolean
}

function resolveConfig(config: Config): ResolvedConfig {
  const endpoint = (config.endpoint ?? DEFAULT_ENDPOINT).replace(/\/$/, '')
  let parsed: URL
  try {
    parsed = new URL(endpoint)
  } catch {
    throw new Error('asm-selector: endpoint must be an absolute http(s) URL')
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('asm-selector: endpoint must be an http(s) URL without embedded credentials')
  }

  const timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1) {
    throw new Error('asm-selector: timeoutMs must be a positive integer')
  }

  const toolName = config.toolName ?? DEFAULT_TOOL_NAME
  const listToolName = config.listToolName ?? DEFAULT_LIST_TOOL_NAME
  for (const [field, value] of [['toolName', toolName], ['listToolName', listToolName]]) {
    if (!/^[A-Za-z0-9_-]+$/.test(value)) {
      throw new Error(`asm-selector: ${field} must contain only letters, digits, underscores, or hyphens`)
    }
  }
  if (toolName === listToolName) {
    throw new Error('asm-selector: toolName and listToolName must be different')
  }
  return {
    endpoint,
    timeoutMs,
    toolName,
    listToolName,
    legacyReceipt: config.legacyReceipt ?? false,
  }
}

function assertDecision(value: unknown): asserts value is JsonValue {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('asm-selector: selector returned a non-object response')
  }
  const decision = value as Record<string, unknown>
  if (!Object.hasOwn(decision, 'selected') || typeof decision.reason !== 'string') {
    throw new Error('asm-selector: selector response is missing selected/reason')
  }
}

function linkedSignal(parent: AbortSignal, timeoutMs: number): { signal: AbortSignal; dispose: () => void } {
  const controller = new AbortController()
  const onAbort = () => controller.abort(parent.reason)
  if (parent.aborted) onAbort()
  else parent.addEventListener('abort', onAbort, { once: true })
  const timeout = setTimeout(() => controller.abort(new Error('ASM selector request timed out')), timeoutMs)
  return {
    signal: controller.signal,
    dispose: () => {
      clearTimeout(timeout)
      parent.removeEventListener('abort', onAbort)
    },
  }
}

export async function requestSelection(
  endpoint: string,
  request: SelectRequest,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
  legacyReceipt = false,
): Promise<JsonValue> {
  let response: Response
  try {
    response = await fetchImpl(`${endpoint}/select`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(legacyReceipt
        ? { ...request, receipt: true, selection_profile: 'legacy-0.5.2' }
        : request),
      signal,
    })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`asm-selector: request failed: ${message}`)
  }

  if (!response.ok) {
    const detail = (await response.text()).replace(/\s+/g, ' ').slice(0, 300)
    throw new Error(`asm-selector: HTTP ${response.status}${detail ? `: ${detail}` : ''}`)
  }

  let value: unknown
  try {
    value = await response.json()
  } catch {
    throw new Error('asm-selector: selector returned invalid JSON')
  }
  assertDecision(value)
  return value
}

export async function requestServices(
  endpoint: string,
  taxonomy: string | undefined,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<JsonValue> {
  const url = new URL(`${endpoint}/tools`)
  if (taxonomy) url.searchParams.set('taxonomy', taxonomy)
  let response: Response
  try {
    response = await fetchImpl(url, { signal })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`asm-selector: catalog request failed: ${message}`)
  }
  if (!response.ok) {
    const detail = (await response.text()).replace(/\s+/g, ' ').slice(0, 300)
    throw new Error(`asm-selector: catalog HTTP ${response.status}${detail ? `: ${detail}` : ''}`)
  }
  let value: unknown
  try {
    value = await response.json()
  } catch {
    throw new Error('asm-selector: catalog returned invalid JSON')
  }
  if (!Array.isArray(value) || value.some(item => item === null || typeof item !== 'object'
    || typeof (item as Record<string, unknown>).service_id !== 'string'
    || typeof (item as Record<string, unknown>).taxonomy !== 'string')) {
    throw new Error('asm-selector: catalog returned an invalid service list')
  }
  return value as JsonValue
}

export function createAsmSelectTool(config: Config = {}): ToolDefinition {
  const resolved = resolveConfig(config)
  return defineTool({
    name: resolved.toolName,
    description:
      'Choose within one explicit ASM taxonomy before a consequential service call. Returns eligibility, risk, approval requirement, and alternatives. The current cost-safe selector does not emit the frozen v0.1 receipt unless legacyReceipt is explicitly configured. It does not infer taxonomy from task text, does not execute any service, and does not grant authorization. Call the catalog-listing tool first if the taxonomy is unknown.',
    parameters: {
      task: {
        type: 'string',
        required: true,
        description: 'Concrete task the selected service must perform. This text is sent to the configured ASM endpoint.',
      },
      taxonomy: {
        type: 'string',
        required: true,
        description: 'Exact ASM taxonomy that bounds the candidate pool; task text does not infer this value.',
      },
      agent_reach: { type: 'string', description: 'Runtime reach, for example cloud or local.' },
      user_platform: { type: 'string', description: 'User platform constraint, for example macos, windows, or any.' },
      required_functions: {
        type: 'array',
        items: { type: 'string' },
        description: 'Capabilities every eligible candidate must provide.',
      },
      require_approval_for: {
        type: 'array',
        items: { type: 'string' },
        description: 'Side effects that require approval before later execution, such as financial_charge.',
      },
      require_agent_completable_setup: {
        type: 'boolean',
        description: 'Exclude candidates whose setup cannot be completed by the agent.',
      },
    },
    output: {
      schema: { type: 'json' },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: resolved.timeoutMs,
    async execute(args, exec) {
      const linked = linkedSignal(exec.signal, resolved.timeoutMs)
      try {
        return await requestSelection(
          resolved.endpoint,
          args,
          linked.signal,
          fetch,
          resolved.legacyReceipt,
        )
      } finally {
        linked.dispose()
      }
    },
  })
}

export function createAsmListTool(config: Config = {}): ToolDefinition {
  const resolved = resolveConfig(config)
  return defineTool({
    name: resolved.listToolName,
    description:
      'List services and taxonomies in the configured ASM catalog. Use this before asm_select when the exact taxonomy is unknown. This is a bounded catalog listing, not web search or proof that unlisted services are ineligible.',
    parameters: {
      taxonomy: { type: 'string', description: 'Optional exact taxonomy filter.' },
    },
    output: {
      schema: { type: 'json' },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: resolved.timeoutMs,
    async execute(args, exec) {
      const linked = linkedSignal(exec.signal, resolved.timeoutMs)
      try {
        return await requestServices(resolved.endpoint, args.taxonomy, linked.signal)
      } finally {
        linked.dispose()
      }
    },
  })
}

export function apply(ctx: Context, config: Config): void {
  ctx.tools.register(createAsmSelectTool(config))
  ctx.tools.register(createAsmListTool(config))
}

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

export interface Config {
  /** Base URL of an ASM selector API. Task text is sent to this endpoint. */
  endpoint?: string
  /** Cooperative request timeout in milliseconds. */
  timeoutMs?: number
  /** Model-facing tool name. */
  toolName?: string
}

export const Config: z<Config> = z.object({
  endpoint: z.string().default(DEFAULT_ENDPOINT),
  timeoutMs: z.number().default(DEFAULT_TIMEOUT_MS),
  toolName: z.string().default(DEFAULT_TOOL_NAME),
})

interface ResolvedConfig {
  endpoint: string
  timeoutMs: number
  toolName: string
}

export interface SelectRequest {
  task: string
  taxonomy?: string
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
  if (!/^[A-Za-z0-9_-]+$/.test(toolName)) {
    throw new Error('asm-selector: toolName must contain only letters, digits, underscores, or hyphens')
  }
  return { endpoint, timeoutMs, toolName }
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
): Promise<JsonValue> {
  let response: Response
  try {
    response = await fetchImpl(`${endpoint}/select`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ ...request, receipt: true }),
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

export function createAsmSelectTool(config: Config = {}): ToolDefinition {
  const resolved = resolveConfig(config)
  return defineTool({
    name: resolved.toolName,
    description:
      'Choose among ASM-described services before a consequential call. Returns eligibility, risk, approval requirement, alternatives, and an unsigned Selection Receipt. It does not execute a service or grant authorization. Use it only when the configured ASM catalog covers the candidate category.',
    parameters: {
      task: {
        type: 'string',
        required: true,
        description: 'Concrete task the selected service must perform. This text is sent to the configured ASM endpoint.',
      },
      taxonomy: { type: 'string', description: 'Optional ASM taxonomy used to bound the candidate pool.' },
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
        return await requestSelection(resolved.endpoint, args, linked.signal)
      } finally {
        linked.dispose()
      }
    },
  })
}

export function apply(ctx: Context, config: Config): void {
  ctx.tools.register(createAsmSelectTool(config))
}

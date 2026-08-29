import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { createAsmListTool, createAsmSelectTool, requestSelection, requestServices } from '../src/index.ts'

const openSignal = new AbortController().signal

describe('ASM DeepSeek Harness plugin', () => {
  it('maps tool arguments to the current selector without requesting a legacy receipt', async () => {
    let capturedUrl = ''
    let capturedInit: RequestInit | undefined
    const decision = {
      selected: { service_id: 'example/service@1', display_name: 'Example' },
      reason: 'eligible',
    }
    const fetchImpl: typeof fetch = async (input, init) => {
      capturedUrl = String(input)
      capturedInit = init
      return new Response(JSON.stringify(decision), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }

    const result = await requestSelection(
      'http://127.0.0.1:8787',
      {
        task: 'book a refundable flight',
        taxonomy: 'tool.booking.travel',
        required_functions: ['flight_search'],
      },
      openSignal,
      fetchImpl,
    )

    assert.deepEqual(result, decision)
    assert.equal(capturedUrl, 'http://127.0.0.1:8787/select')
    assert.equal(capturedInit?.method, 'POST')
    assert.deepEqual(JSON.parse(String(capturedInit?.body)), {
      task: 'book a refundable flight',
      taxonomy: 'tool.booking.travel',
      required_functions: ['flight_search'],
    })
  })

  it('requests the frozen receipt only with an explicit legacy profile', async () => {
    let capturedInit: RequestInit | undefined
    const fetchImpl: typeof fetch = async (_input, init) => {
      capturedInit = init
      return new Response(JSON.stringify({
        selected: { service_id: 'example/service@1' },
        reason: 'legacy selection',
        receipt: { receipt_type: 'selection', receipt_version: '0.1' },
      }), { status: 200 })
    }
    await requestSelection(
      'http://127.0.0.1:8787',
      { task: 'x', taxonomy: 'tool.example' },
      openSignal,
      fetchImpl,
      true,
    )
    assert.deepEqual(JSON.parse(String(capturedInit?.body)), {
      task: 'x',
      taxonomy: 'tool.example',
      receipt: true,
      selection_profile: 'legacy-0.5.2',
    })
  })

  it('registers a non-executing decision tool with the configured name', () => {
    const tool = createAsmSelectTool({ endpoint: 'https://example.test/', toolName: 'choose_service' })
    assert.equal(tool.name, 'choose_service')
    assert.match(tool.description, /does not execute/i)
    assert.equal(tool.timeoutMs, 15_000)
    assert.deepEqual((tool.parameters as { required?: string[] }).required, ['task', 'taxonomy'])
  })

  it('lists the bounded catalog without sending task text', async () => {
    let capturedUrl = ''
    const fetchImpl: typeof fetch = async input => {
      capturedUrl = String(input)
      return new Response(JSON.stringify([
        { service_id: 'example/service@1', taxonomy: 'tool.example' },
      ]), { status: 200 })
    }
    const result = await requestServices(
      'https://example.test',
      'tool.example',
      openSignal,
      fetchImpl,
    )
    assert.equal(capturedUrl, 'https://example.test/tools?taxonomy=tool.example')
    assert.equal((result as Array<Record<string, unknown>>)[0]?.service_id, 'example/service@1')
    assert.equal(createAsmListTool().name, 'asm_list_services')
  })

  it('rejects embedded endpoint credentials', () => {
    assert.throws(
      () => createAsmSelectTool({ endpoint: 'https://secret@example.test' }),
      /without embedded credentials/,
    )
  })

  it('fails closed on malformed selector responses', async () => {
    const fetchImpl: typeof fetch = async () => new Response(JSON.stringify({ selected: null }), { status: 200 })
    await assert.rejects(
      requestSelection('https://example.test', { task: 'x', taxonomy: 'tool.example' }, openSignal, fetchImpl),
      /missing selected\/reason/,
    )
  })

  it('fails closed on malformed catalog responses', async () => {
    const fetchImpl: typeof fetch = async () => new Response(JSON.stringify([{ name: 'missing ids' }]), { status: 200 })
    await assert.rejects(
      requestServices('https://example.test', undefined, openSignal, fetchImpl),
      /invalid service list/,
    )
  })

  it('surfaces bounded HTTP errors', async () => {
    const fetchImpl: typeof fetch = async () => new Response('bad '.repeat(200), { status: 503 })
    await assert.rejects(
      requestSelection('https://example.test', { task: 'x', taxonomy: 'tool.example' }, openSignal, fetchImpl),
      (error: unknown) => error instanceof Error
        && error.message.startsWith('asm-selector: HTTP 503:')
        && error.message.length < 340,
    )
  })
})

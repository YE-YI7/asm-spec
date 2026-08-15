import assert from "node:assert/strict";
import { Client, InMemoryTransport } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import * as path from "node:path";

import { buildMcpServer } from "./index.js";

async function testLegacyServerSurface(): Promise<void> {
  // The in-memory transport covers the v2 package migration and the legacy
  // 2025 wire surface. Modern 2026-07-28 stdio negotiation is provided by the
  // `serveStdio(buildMcpServer)` entrypoint in index.ts.
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const server = buildMcpServer();
  const client = new Client(
    { name: "asm-registry-test", version: "1.0.0" },
    { versionNegotiation: { mode: "legacy" } },
  );

  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);

  try {
    const tools = await client.listTools();
    const names = new Set(tools.tools.map((tool) => tool.name));
    for (const expected of ["asm_list", "asm_get", "asm_query", "asm_compare", "asm_score", "asm_taxonomies"]) {
      assert(names.has(expected), `missing MCP tool: ${expected}`);
    }

    const result = await client.callTool({ name: "asm_taxonomies", arguments: {} });
    assert.equal(result.isError, undefined);
    assert(result.content.length > 0);
  } finally {
    await client.close();
    await server.close();
  }
}

async function testModernStdioNegotiation(): Promise<void> {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [path.resolve(__dirname, "..", "dist", "index.js")],
    cwd: path.resolve(__dirname, ".."),
    stderr: "pipe",
  });
  const client = new Client(
    { name: "asm-modern-test", version: "1.0.0" },
    { versionNegotiation: { mode: { pin: "2026-07-28" } } },
  );

  await client.connect(transport);
  try {
    assert.equal(client.getProtocolEra(), "modern");
    assert.equal(client.getNegotiatedProtocolVersion(), "2026-07-28");
    const tools = await client.listTools();
    assert(tools.tools.some((tool) => tool.name === "asm_score"));
  } finally {
    await client.close();
  }
}

Promise.all([testLegacyServerSurface(), testModernStdioNegotiation()])
  .then(() => console.log("MCP SDK v2 registry smoke test passed."))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

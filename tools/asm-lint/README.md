# asm-lint

Quality detection CLI for MCP Servers — scan, probe, and score any MCP Server.

Part of the [ASM Protocol](https://github.com/YE-YI7/asm-spec) (Agent Service Manifest).

## Install

```bash
npm install -g asm-lint
```

Or run directly:

```bash
npx asm-lint <mcp-server-command>
```

## Usage

```bash
# Lint any MCP Server
asm-lint npx @anthropic-ai/mcp-server-resend

# Output as JSON
asm-lint --json npx @modelcontextprotocol/server-filesystem /tmp

# Generate x-asm metadata template
asm-lint --init
```

## What it checks

| Check | Points | Description |
|-------|:------:|-------------|
| Tool Definitions | 20 | Are all tools properly described? |
| Input Schemas | 15 | Do tools have valid JSON Schema inputs? |
| Description Quality | 10 | Are descriptions detailed with examples? |
| Naming Conventions | 5 | Do tool names follow snake_case? |
| x-asm Metadata | 20 | Does the server include ASM quality metadata? |
| Error Documentation | 10 | Do descriptions document error behavior? |
| Security Patterns | 10 | Are risky operations flagged? |
| Idempotency Hints | 10 | Are read-only tools marked? |

**Total: 100 points**

## Grading

| Score | Grade |
|:-----:|:-----:|
| 90+ | A+ |
| 80-89 | A |
| 70-79 | B+ |
| 60-69 | B |
| 50-59 | C |
| 40-49 | D |
| <40 | F |

## Badge

After running `asm-lint`, it generates a README badge you can add to your project:

```markdown
[![ASM Score](https://img.shields.io/badge/ASM_Score-72%2F100_B+-brightgreen)](https://github.com/YE-YI7/asm-spec)
```

## x-asm Metadata

Run `asm-lint --init` to generate a template for adding quality metadata to your MCP Server:

```json
{
  "x-asm": {
    "service_id": "<provider>/<service>@<version>",
    "taxonomy": "<domain>.<category>.<subcategory>",
    "pricing": {
      "model": "per_call",
      "price_per_call": 0.001,
      "currency": "USD"
    },
    "sla": {
      "latency_p50_ms": 200,
      "latency_p99_ms": 800,
      "uptime": 0.999
    }
  }
}
```

## License

MIT

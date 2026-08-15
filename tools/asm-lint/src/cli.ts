#!/usr/bin/env node
/**
 * asm-lint — MCP Server 质量检测 CLI
 *
 * 扫描任意 MCP Server，生成质量报告：
 *   - 工具定义完整性
 *   - Schema 有效性
 *   - 延迟探测
 *   - x-asm metadata 检查
 *   - 综合评分
 *
 * Usage:
 *   npx asm-lint <mcp-server-command>
 *   npx asm-lint --json <mcp-server-command>
 *   npx asm-lint --init  (生成 x-asm metadata 模板)
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { spawn } from "child_process";

// ── 颜色输出（轻量级，不依赖 chalk） ──────────────────────

const c = {
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`,
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string) => `\x1b[1m${s}\x1b[0m`,
  white: (s: string) => `\x1b[37m${s}\x1b[0m`,
};

const CHECK = c.green("✅");
const WARN = c.yellow("⚠️");
const FAIL = c.red("❌");
const INFO = c.cyan("ℹ️");

// ── 类型定义 ────────────────────────────────────────────

interface ToolDef {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

interface LintResult {
  serverName: string;
  serverVersion: string;
  tools: ToolDef[];
  checks: Check[];
  score: number;
  grade: string;
  latencyMs?: number;
}

interface Check {
  name: string;
  status: "pass" | "warn" | "fail";
  message: string;
  points: number;
  maxPoints: number;
}

// ── 核心检测逻辑 ─────────────────────────────────────────

function checkToolDefinitions(tools: ToolDef[]): Check {
  if (tools.length === 0) {
    return { name: "Tool Definitions", status: "fail", message: "No tools found", points: 0, maxPoints: 20 };
  }
  const wellDefined = tools.filter(t => t.description && t.description.length > 10);
  if (wellDefined.length === tools.length) {
    return { name: "Tool Definitions", status: "pass", message: `${tools.length} tools, all with descriptions`, points: 20, maxPoints: 20 };
  }
  const missing = tools.filter(t => !t.description || t.description.length <= 10);
  return {
    name: "Tool Definitions",
    status: "warn",
    message: `${tools.length} tools, ${missing.length} missing/short descriptions: ${missing.map(t => t.name).join(", ")}`,
    points: Math.round(20 * wellDefined.length / tools.length),
    maxPoints: 20,
  };
}

function checkInputSchemas(tools: ToolDef[]): Check {
  if (tools.length === 0) {
    return { name: "Input Schemas", status: "fail", message: "No tools to check", points: 0, maxPoints: 15 };
  }
  const withSchema = tools.filter(t => t.inputSchema && typeof t.inputSchema === "object");
  const withProperties = withSchema.filter(t => {
    const schema = t.inputSchema as Record<string, unknown>;
    return schema.properties && typeof schema.properties === "object";
  });

  if (withProperties.length === tools.length) {
    return { name: "Input Schemas", status: "pass", message: `All ${tools.length} tools have valid JSON Schema`, points: 15, maxPoints: 15 };
  }
  if (withSchema.length === tools.length) {
    return { name: "Input Schemas", status: "warn", message: `All tools have schemas but ${tools.length - withProperties.length} lack 'properties'`, points: 10, maxPoints: 15 };
  }
  return {
    name: "Input Schemas",
    status: "warn",
    message: `${withSchema.length}/${tools.length} tools have input schemas`,
    points: Math.round(15 * withSchema.length / tools.length),
    maxPoints: 15,
  };
}

function checkDescriptionQuality(tools: ToolDef[]): Check {
  if (tools.length === 0) {
    return { name: "Description Quality", status: "fail", message: "No tools", points: 0, maxPoints: 10 };
  }
  let score = 0;
  const issues: string[] = [];

  for (const t of tools) {
    const desc = t.description || "";
    if (desc.length > 30) score += 2;
    else if (desc.length > 10) score += 1;
    else issues.push(t.name);

    // 检查是否包含使用示例或参数说明
    if (desc.includes("e.g.") || desc.includes("example") || desc.includes("returns")) score += 1;
  }

  const maxScore = tools.length * 3;
  const normalized = Math.round(10 * score / maxScore);

  if (normalized >= 8) {
    return { name: "Description Quality", status: "pass", message: "Descriptions are detailed and helpful", points: normalized, maxPoints: 10 };
  }
  if (normalized >= 5) {
    return { name: "Description Quality", status: "warn", message: `Some descriptions could be more detailed${issues.length > 0 ? `: ${issues.join(", ")}` : ""}`, points: normalized, maxPoints: 10 };
  }
  return { name: "Description Quality", status: "fail", message: `Descriptions are too short or missing: ${issues.join(", ")}`, points: normalized, maxPoints: 10 };
}

function checkNamingConventions(tools: ToolDef[]): Check {
  const snakeCase = /^[a-z][a-z0-9_]*$/;
  const wellNamed = tools.filter(t => snakeCase.test(t.name));
  if (wellNamed.length === tools.length) {
    return { name: "Naming Conventions", status: "pass", message: "All tool names follow snake_case", points: 5, maxPoints: 5 };
  }
  const bad = tools.filter(t => !snakeCase.test(t.name)).map(t => t.name);
  return { name: "Naming Conventions", status: "warn", message: `Non-snake_case names: ${bad.join(", ")}`, points: Math.round(5 * wellNamed.length / tools.length), maxPoints: 5 };
}

function checkXAsmMetadata(tools: ToolDef[]): Check {
  // 检查工具是否包含 x-asm 扩展元数据
  const withXAsm = tools.filter(t => {
    const schema = t.inputSchema as Record<string, unknown> | undefined;
    if (!schema) return false;
    return Object.keys(schema).some(k => k.startsWith("x-asm"));
  });

  if (withXAsm.length > 0) {
    return { name: "x-asm Metadata", status: "pass", message: `${withXAsm.length}/${tools.length} tools have x-asm quality metadata`, points: 20, maxPoints: 20 };
  }
  return {
    name: "x-asm Metadata",
    status: "warn",
    message: "No x-asm metadata found. Run 'asm-lint --init' to generate a template.",
    points: 0,
    maxPoints: 20,
  };
}

function checkErrorHandling(tools: ToolDef[]): Check {
  // 检查工具描述中是否提到错误处理
  const mentionsErrors = tools.filter(t => {
    const desc = (t.description || "").toLowerCase();
    return desc.includes("error") || desc.includes("fail") || desc.includes("invalid") || desc.includes("throw");
  });

  if (mentionsErrors.length > 0) {
    return { name: "Error Documentation", status: "pass", message: `${mentionsErrors.length}/${tools.length} tools document error behavior`, points: 10, maxPoints: 10 };
  }
  return { name: "Error Documentation", status: "warn", message: "No tools document error behavior in descriptions", points: 3, maxPoints: 10 };
}

function checkSecurityPatterns(tools: ToolDef[]): Check {
  // 检查是否有潜在安全风险的工具（如文件系统访问、命令执行）
  const riskyPatterns = ["exec", "shell", "command", "file_system", "write_file", "delete", "rm ", "sudo"];
  const riskyTools = tools.filter(t => {
    const name = t.name.toLowerCase();
    const desc = (t.description || "").toLowerCase();
    return riskyPatterns.some(p => name.includes(p) || desc.includes(p));
  });

  if (riskyTools.length === 0) {
    return { name: "Security Patterns", status: "pass", message: "No high-risk tool patterns detected", points: 10, maxPoints: 10 };
  }
  return {
    name: "Security Patterns",
    status: "warn",
    message: `${riskyTools.length} potentially risky tools: ${riskyTools.map(t => t.name).join(", ")}. Consider adding confirmation prompts.`,
    points: 5,
    maxPoints: 10,
  };
}

function checkIdempotency(tools: ToolDef[]): Check {
  // 检查工具描述中是否标注了幂等性
  const readOnly = tools.filter(t => {
    const desc = (t.description || "").toLowerCase();
    const name = t.name.toLowerCase();
    return name.startsWith("get") || name.startsWith("list") || name.startsWith("search") || name.startsWith("read") ||
      desc.includes("read-only") || desc.includes("idempotent") || desc.includes("does not modify");
  });

  if (readOnly.length > 0) {
    return { name: "Idempotency Hints", status: "pass", message: `${readOnly.length}/${tools.length} tools indicate read-only/idempotent behavior`, points: 10, maxPoints: 10 };
  }
  return { name: "Idempotency Hints", status: "warn", message: "No tools indicate idempotency. Consider marking read-only tools.", points: 3, maxPoints: 10 };
}

function computeGrade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B+";
  if (score >= 60) return "B";
  if (score >= 50) return "C";
  if (score >= 40) return "D";
  return "F";
}

// ── 主流程 ───────────────────────────────────────────────

async function lint(command: string, args: string[]): Promise<LintResult> {
  console.log(`\n${c.bold("🔍 ASM Lint")} — MCP Server Quality Report\n`);
  console.log(`${c.dim("Target:")} ${command} ${args.join(" ")}\n`);

  // 连接 MCP Server
  const transport = new StdioClientTransport({
    command,
    args,
  });

  const client = new Client({
    name: "asm-lint",
    version: "0.1.0",
  });

  const startTime = Date.now();
  await client.connect(transport);
  const connectLatency = Date.now() - startTime;

  // 获取服务器信息
  const serverInfo = client.getServerVersion();
  const serverName = serverInfo?.name || "unknown";
  const serverVersion = serverInfo?.version || "unknown";

  console.log(`${c.dim("Server:")} ${serverName} v${serverVersion}`);
  console.log(`${c.dim("Connect:")} ${connectLatency}ms\n`);

  // 获取工具列表
  const toolsResult = await client.listTools();
  const tools = toolsResult.tools as ToolDef[];

  console.log(`${c.dim("Tools:")} ${tools.length} found\n`);
  console.log(c.dim("─".repeat(60)) + "\n");

  // 运行所有检查
  const checks: Check[] = [
    checkToolDefinitions(tools),
    checkInputSchemas(tools),
    checkDescriptionQuality(tools),
    checkNamingConventions(tools),
    checkXAsmMetadata(tools),
    checkErrorHandling(tools),
    checkSecurityPatterns(tools),
    checkIdempotency(tools),
  ];

  // 输出检查结果
  for (const check of checks) {
    const icon = check.status === "pass" ? CHECK : check.status === "warn" ? WARN : FAIL;
    const scoreStr = c.dim(`[${check.points}/${check.maxPoints}]`);
    console.log(`${icon} ${c.bold(check.name)} ${scoreStr}`);
    console.log(`   ${c.dim(check.message)}\n`);
  }

  // 计算总分
  const totalPoints = checks.reduce((sum, ch) => sum + ch.points, 0);
  const maxPoints = checks.reduce((sum, ch) => sum + ch.maxPoints, 0);
  const score = Math.round(100 * totalPoints / maxPoints);
  const grade = computeGrade(score);

  // 输出总分
  console.log(c.dim("─".repeat(60)));
  console.log(`\n📊 ${c.bold("ASM Score")}: ${score >= 70 ? c.green(String(score)) : score >= 50 ? c.yellow(String(score)) : c.red(String(score))}/100 (Grade: ${c.bold(grade)})`);
  console.log(`   ${c.dim(`${totalPoints}/${maxPoints} points across ${checks.length} checks`)}\n`);

  // 输出工具清单
  console.log(c.bold("📋 Tool Inventory:"));
  for (const t of tools) {
    const paramCount = t.inputSchema && (t.inputSchema as Record<string, unknown>).properties
      ? Object.keys((t.inputSchema as Record<string, unknown>).properties as Record<string, unknown>).length
      : 0;
    const required = t.inputSchema && (t.inputSchema as Record<string, unknown>).required
      ? ((t.inputSchema as Record<string, unknown>).required as string[]).length
      : 0;
    console.log(`   ${c.cyan(t.name)} — ${paramCount} params (${required} required)`);
    if (t.description) {
      const short = t.description.length > 80 ? t.description.slice(0, 77) + "..." : t.description;
      console.log(`   ${c.dim(short)}`);
    }
  }

  // 改进建议
  const warnings = checks.filter(ch => ch.status === "warn");
  const failures = checks.filter(ch => ch.status === "fail");
  if (warnings.length > 0 || failures.length > 0) {
    console.log(`\n${c.bold("💡 Suggestions:")}`);
    for (const ch of [...failures, ...warnings]) {
      const potential = ch.maxPoints - ch.points;
      console.log(`   → Fix "${ch.name}" to gain up to +${potential} points`);
    }
    console.log(`   → Run ${c.cyan("asm-lint --init")} to generate x-asm metadata template`);
  }

  // 断开连接
  await client.close();

  return {
    serverName,
    serverVersion,
    tools,
    checks,
    score,
    grade,
    latencyMs: connectLatency,
  };
}

// ── --init 命令：生成 x-asm metadata 模板 ──────────────────

function generateInitTemplate() {
  const template = {
    "x-asm": {
      "service_id": "<provider>/<service>@<version>",
      "taxonomy": "<domain>.<category>.<subcategory>",
      "pricing": {
        "model": "per_call",
        "price_per_call": 0.001,
        "currency": "USD",
      },
      "sla": {
        "latency_p50_ms": 200,
        "latency_p99_ms": 800,
        "uptime": 0.999,
      },
      "quality": {
        "benchmark": "<benchmark_name>",
        "score": 0.9,
        "scale": "0-1",
      },
      "trust": {
        "score": null,
        "confidence": null,
        "reports": 0,
        "note": "Trust scores are auto-populated by ASM after real usage data is collected.",
      },
    },
  };

  console.log(`\n${c.bold("📝 x-asm Metadata Template")}\n`);
  console.log(c.dim("Add this to your MCP Server's tool annotations:"));
  console.log();
  console.log(JSON.stringify(template, null, 2));
  console.log();
  console.log(c.dim("See: https://github.com/YE-YI7/asm-spec for the current specification"));
}

// ── CLI 入口 ─────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    console.log(`
${c.bold("asm-lint")} — MCP Server Quality Detection CLI

${c.bold("Usage:")}
  asm-lint <command> [args...]     Lint an MCP Server
  asm-lint --init                  Generate x-asm metadata template
  asm-lint --json <command>        Output results as JSON

${c.bold("Examples:")}
  asm-lint npx @anthropic-ai/mcp-server-resend
  asm-lint node ./my-server.js
  asm-lint python my_server.py
  asm-lint --json npx @modelcontextprotocol/server-filesystem /tmp

${c.bold("What it checks:")}
  • Tool definitions completeness (descriptions, schemas)
  • Input schema validity (JSON Schema compliance)
  • Description quality (detail, examples, error docs)
  • Naming conventions (snake_case)
  • x-asm quality metadata (pricing, SLA, trust)
  • Security patterns (risky operations detection)
  • Idempotency hints (read-only markers)

${c.dim("Experimental prototype — not an ASM conformance certificate")}
${c.dim("https://github.com/YE-YI7/asm-spec")}
`);
    process.exit(0);
  }

  if (args.includes("--init")) {
    generateInitTemplate();
    process.exit(0);
  }

  const jsonMode = args.includes("--json");
  const cmdArgs = args.filter(a => a !== "--json");

  if (cmdArgs.length === 0) {
    console.error(c.red("Error: No MCP server command specified"));
    process.exit(1);
  }

  const command = cmdArgs[0];
  const serverArgs = cmdArgs.slice(1);

  try {
    const result = await lint(command, serverArgs);

    if (jsonMode) {
      console.log("\n" + JSON.stringify(result, null, 2));
    } else {
      console.log(c.yellow("Experimental heuristic only; do not publish this score as an ASM certification."));
    }

    // 退出码：0=pass(>=60), 1=fail(<60)
    process.exit(result.score >= 60 ? 0 : 1);
  } catch (err) {
    console.error(`\n${FAIL} ${c.bold("Connection failed")}`);
    console.error(`   ${c.dim(String(err))}`);
    console.error(`\n${c.dim("Make sure the MCP server command is correct and the server starts via stdio.")}`);
    process.exit(1);
  }
}

main();

# ASM 本轮研究记录

2026-09-05；内部来源与决策记录。面向执行模型的正式交付是相邻的 ../asm-execution-prd-2026-09-05.md；此文件不对外宣传。

研究问题：如何在不要求供应商先采纳新协议的情况下，使发现、测评、owner 选择与结果证据形成反复使用的产品？

结论：以重复研究任务中的 web.search 为第一组可替代操作，公共服务卡与结果回执共用事实和运行记录。大规模目录及自适应算法按结果逐步扩大。

方法：检查 stable 发布说明、工作分支 selection/adaptive/preferences/freshness 接口；核验 MCP、三个供应商、JCS、OpenTelemetry 原始文档；独立子任务检视首个场景与公平对照。当前工具无 update_plan，采用研究→合同→评审→交付顺序，未创建额外 goal。

## Claim-to-source ledger

| 判断 | 原始来源，发布者 | 访问与证据限制 |
|---|---|---|
| 必须区分 tools/list 元数据与可信授权 | https://modelcontextprotocol.io/specification/2025-06-18/server/tools ，MCP | 2026-09-05；固定历史协议版，当前 SDK 另核验 |
| 搜索参数与实际 credits 影响比较 | https://docs.tavily.com/documentation/api-reference/endpoint/search ，Tavily | 2026-09-05；文档可读，未发起收费调用 |
| 返回的 costDollars 不等于最终账单 | https://exa.ai/docs/reference/search ，Exa | 2026-09-05；原文明确 estimated / usage counters |
| Search 与 scrape、留存模式必须分开 | https://docs.firecrawl.dev/features/search ，Firecrawl | 2026-09-05；文档费用不等于具体账户合同 |
| 新 receipt 要有明确 canonicalization profile | https://www.rfc-editor.org/info/rfc8785/ ，RFC Editor | 2026-09-05；标准方案，不能据此推断事实真实性 |
| trace adapter 需版本锁定 | https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/ ，OpenTelemetry | 2026-09-05；页面为迁移提示，未据此设计具体 span schema |
| 供应商先采用协议的摩擦真实存在 | https://github.com/upstash/context7/pull/3105 ，项目维护者回复 | 上一轮已实时核验；单项目拒绝不外推市场比例 |
| stable 无 owner 学习、新成本不能直接用旧 receipt | ../adaptive-selection-v0.7.md 与 ../../release-v0.6.0.md ，ASM | 当前本地文件；实验不能冒充线上能力 |

## 尚未解决

- 供应商真实质量差异、特定账户成本、试点客户是否有重复选择需求：待 T2/T7。
- 是否先做 known-URL extraction：独立评审认为它更容易确定真值；本次先保留 search，明确不混算全文抓取。若 search 的公平真值无法冻结，先以 extraction 子任务验证测量链路，但更换首个对外场景须记录产品理由。
- 原生 auto 对照不可缺失；已加入正式规范。
- 统计功效、偏好学习收益、风险阈值未验证；执行任务不以这些为前置。

停止继续广搜的原因：首个可执行链路、公开接口与关键成本/证据边界已有直接来源；更多市场材料不会替代 live 运行与用户试用。

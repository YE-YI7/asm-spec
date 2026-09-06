# ASM：从可运行选择到可验证服务网络

版本：0.1 · 2026-09-05 · 状态：执行规范，能力与收入尚未验收。
读者：后续执行模型、算法研究模型、项目负责人。
本文是本轮实施入口；覆盖旧 program spec 中与公共发现、测评、调用回执接入相冲突的产品范围。既有协议兼容性不因本文自动改变。

## 1. 目标与首个产品

长期目标：Agent 能发现服务，依据真实表现与 owner 偏好选择，并用可核验记录说明选择依据与执行结果。ASM 同时建设公共发现、测评、选择和证据能力。公共宣传不得出现竞品名称，也不得声称尚未实现的责任承担、认证或商业采用。

首个产品：为研究 Agent 选择网页搜索服务，返回可引用来源，并记录选择和调用结果。核心用户是已经使用两个以上搜索服务、经常处理研究任务的 Agent 开发者。潜在付费方是维护此类 Agent 的团队。

用户第一次使用应获得有效搜索结果；接入时不需要填写偏好问卷、维护 manifest 或认同新协议。已有账户和服务由 host 显式授权接入。

首批 adapter 候选：Tavily Search、Exa Search、Firecrawl Search。它们是待实测的服务候选，不代表合作。MVP 比较 search→URL/title/snippet；抓取正文、答案生成另立操作及费用，不能混进同一指标。

选择此场景的理由：调用重复、存在替代服务、失败可见、可以测试来源是否支撑答案。公开网页查询不修改目标业务数据，但仍会产生费用、外发查询并可能被供应商留存。

独立评审建议先做 known-URL 内容获取，因为更容易统一输入和 ground truth。本次取舍：公开入口保留 search，以验证服务发现到实际使用的完整链路；T2 的 adapter 故障与结果校验可用固定 URL 证据集。若 T7 无法在看见候选结果前冻结搜索任务判据，则暂停搜索效果宣传，先完成独立的 web.extract 评估，不混合两种操作。此取舍需用首批用户的真实任务校准。

该场景是首批验证队列，通用协议仍保留 API、MCP、CLI 与外部 A2A Agent。暂不实现任意 SaaS 自动注册、写操作通用代理、结算网络、保险赔付。

## 2. 成功条件

交付以用户价值为准，以下数字是本次试点的决策阈值，不是行业基准或已有成绩。

| 层次 | 验收 |
|---|---|
| 可用 | 干净安装后，无密钥可跑带明显 replay 标签的示例；已有授权账户可完成一次 live search 并得到结果及回执 |
| 易用 | 5 名非项目维护者试用，至少 4 名在 10 分钟内首次成功；分别记录安装、授权、首调用耗时和失败原因 |
| 复用 | 3 个独立外部项目，连续 4 周每周均有使用；每项目每周至少 10 个非演示真实任务，排除 CI 与合成 benchmark |
| 效果 | 预先冻结的配对评估满足第 10 节，不以自家评分作 ground truth |
| 商业 | 至少一位明确预算持有人确认付费试点范围与价格；只有实际付款才记为收入 |

一个项目达到持续使用即可记为单项目采用；三个项目是本轮扩大建设的门槛。社区回复、安装、星标和评审分别记录，不替代使用。

## 3. 当前真实基线与复用

本轮读取：主仓 main cf2276c（v0.6.0 发布记录）；工作分支 codex/adaptive-selection-v07-20260831，HEAD d897411。执行前再次核验远端、dirty 状态与 AGENTS.md。

| 当前文件/能力 | 可复用 | 必须补齐 |
|---|---|---|
| src/asm_protocol/selection.py、cost.py | 显式能力筛选、工作量成本、unknown 状态 | 新操作合同与选中时证据快照 |
| adaptive.py、preferences.py | 实验性偏好模型及事件接口 | 尚无真实 held-out 效果，不能设为默认 |
| freshness.py | 证据年龄与 cache TTL 分离 | 按 claim/操作配置时效、变更后失效 |
| federation/mcp_registry.py | 注册表读取与候选发现 | 去重、来源追踪、分页及失败恢复 |
| asm_selector_mcp.py、LangChain 集成 | 工具暴露和结构化返回 | 单一入口贯通受控调用与 outcome |
| Selection Receipt v0.1 | legacy 兼容 fixture | v0.6 成本路径无法表达于旧 receipt，需要显式新版本 |
| library/、manifests/ | 回归示例 | 不能当实时目录；8 月 31 日审计记录为 30 stale、75 expired |
| A2A experience 设计及实验 | 任务、版本、证据类型设计 | 运行时消费与真实任务质量验证未完成 |

保留 legacy 行为与 fixture；新协议使用单独版本和显式入口。不要通过修改旧 fixture 的数值来让新行为通过。

## 4. 完整使用链路

```text
公开服务卡 / 安装入口
        ↓
host 提供任务 + 已授权账户 + 有效 owner/组织约束
        ↓
任务合同 → 候选发现 → 字段证据补全/刷新
        ↓
权限/能力/费用/数据外发硬门槛 → 选择或明确弃权
        ↓
冻结 DecisionReceipt → host/可选 adapter 重验并调用
        ↓
结果标准化 → 返回搜索结果 + OutcomeReceipt
        ↓
私有历史改善选择；经明确同意的聚合测量更新公共服务卡
```

对最终用户只展示结果、关键选择理由、异常及真正需要确认的事项。技术证明供开发者展开，默认不阻塞结果阅读。

明确指定服务时先验证该服务；通过后按指定执行，不擅自换工具。失败时返回原因和候选替代；后续是否可自动换服务由 host 的 fallback 授权决定。

## 5. 请求、状态与数据合同

以下名称是拟新增的应用合同，不是已实现 API。T1 必须产出 JSON Schema、正反例和版本迁移说明。

### 5.1 请求 SearchRequest / DecisionRequest

- request_id、operation（MVP 为 web.search）、query_ref（私有）、task_profile_id/version。
- language、time_window、allowed/excluded_domains、result_limit；未声明的约束保持 unknown。
- candidate_scope：host 已授权的 service/interface/account 引用；explicit_service 可选。
- effective_policy_ref/digest：组织限制、owner 明示约束、host 授权及其来源。模型推断不能扩大授权。
- cost_budget：本次与会话剩余预算、币种、估算允许规则；超预算或金额不可界定时不可发起可能收费的调用。
- deadline_ms、fallback_allowlist、max_attempts；默认仅调用一项，fallback 须有授权且计入总预算。
- execution_mode：replay / shadow / live；shadow 只记录决策，额外供应商调用仍须额外预算授权。

任务编译由 host 将 goal 转成合同。首版只实现明确 search 字段映射与校验；不把关键词匹配宣传为 goal 理解。复杂自然语言编译单独评估。

### 5.2 候选与证据

Candidate：provider_id、service_id、interface_id、operation、interface/schema digest、版本、endpoint、adapter_version。

Evidence：evidence_id、claim_path、value/unit、source_url/issuer、method、observed_at、fetched_at、expires_at、scope（地域/账户套餐/任务类型/操作/版本）、snapshot_ref/digest、strength、status。

- method 至少区分 producer_declared、registry_observed、http_probe、authenticated_call、independent_eval、caller_report。
- 同一事实出现冲突保留各来源；关键冲突导致 needs_evidence，不由 LLM 自动投票抹平。
- homepage 存活不能变成 API 成功率；HTTP 200 不能变成任务正确；schema 合法不能变成安全认证。
- 每个 claim 独立保鲜，重新抓取不自动更新 last_verified。版本变化使不适用的旧证据失效。
- 金额用十进制定点表达，currency 和 unit 必填。credits 不等于美元；估算、usage 与结算三类金额分开。

### 5.3 决策状态

selected、under_specified、no_eligible_candidate、needs_evidence、needs_authorization、needs_budget、needs_owner_input。

结果携带 selected/alternatives/rejected、明确 reason codes、unknowns、policy_version、evidence_refs、cost_estimate、decision_receipt_ref。selected 仅表示完成推荐，不证明调用已获授权或已经执行。

### 5.4 决策与结果回执

DecisionReceipt v0.2-draft：decision_id、issued_at、request_commitment、候选集合与证据快照摘要、effective_policy_digest、算法名称/版本、已选及淘汰原因、金额状态/假设、有效期、执行绑定、issuer。

OutcomeReceipt v0.1-draft：outcome_id、decision_id/receipt_digest、attempt_id、执行 adapter/接口版本、实际请求承诺、provider request_id（如有）、起止时间、transport_status、tool_status、task_check_results、usage、estimated_cost、settled_cost（如可验证）、result_commitment、issuer、supersedes。

用 RFC 8785 JCS + SHA-256 命名摘要 profile；采用成熟库，禁止手写跨语言 canonicalization。旧 receipt 摘要 profile 继续独立保留。

哈希证明快照一致性，不证明事实真实。签名是可选 envelope；未签名明确标注。验证方必须配置可信 issuer/key，不能把任意有效签名当可信质量。公证/法律效力不在产品承诺中。

原始查询、密钥、结果正文、owner 历史默认留在本地。低熵查询不能直接公开 SHA-256；公开分享使用经过脱敏的导出，必要承诺用私有随机盐且不随公开导出泄漏。删除私有记录后标明相应证据已不可重放。

## 6. 选择策略与 owner 冷启动

执行模型可实现的确定性顺序：

1. 组织/授权/外发限制及明确操作能力门槛。
2. 用户指定服务；不满足门槛则返回原因。
3. 时效、接口版本、成本可界定性及剩余预算检查。
4. 优先使用 host 已给出的有效默认服务；明确记录 default 来源。
5. 没有默认时，在可比较事实下识别 Pareto 支配关系；缺值不能视作 0，证据不足不能伪造支配。
6. 多项无法区分时返回合格短名单，由 host 在既有授权内选取，并记录 host_choice。不得偷偷以最便宜、service_id 或自造权重解决有意义的取舍。

正常用户无需设置评分权重。安装状态、已订阅账户、明确替换行为可以作为偏好证据，但不能因此推断其他权限。用户未反对不算正向偏好标签。

这套策略可直接编码并标为 bootstrap-policy/v1。它不声称能学习 owner。完整推荐结果仍需承认信息不足。

## 7. 调用、故障与保鲜

新增薄 adapter，仅负责该场景的授权调用与结果归一化。协议内核继续独立运行；任何外部 harness 都能消费决策并回传 outcome。

- API 超时、429、认证失败、空结果、结构错误、内容不满足任务分开记录。
- 认证失败不自动注册账户；429 遵守 Retry-After；无 fallback 授权则停止。MVP 每请求最多两次供应商尝试，总预算和 deadline 优先。
- 执行前核对 interface digest、有效 policy 与 receipt 时效。失配必须重新决策，不得用旧凭证说明新调用。
- 保留 request/attempt 幂等键；写回回执可重试，供应商 search 重试可能再次计费，不能宣称跨供应商 exactly-once。
- 可选故障回退需同时满足：剩余预算、外发范围、候选授权与时间限制。新 attempt 关联原 decision；换候选生成 successor decision。
- 缓存结果需记录来源时间与查询参数；缓存命中不能当新 benchmark。策略失效时不得因旧缓存继续允许调用。
- 保鲜优先级：真实调用触发、schema 变更触发、按用量轮询；初始刷新间隔是配置，须通过试点校准，不宣传毫秒级实时。
- 首版仅请求显式列出的公开服务端点；任意 URL 抓取须实现 DNS/redirect 重验、阻断私网与 metadata IP、响应大小/时间上限。抓取内容不得作为执行指令。

## 8. 公共产品与增长入口

第一批发布 3 张有来源和真实测量的服务卡；扩展队列先覆盖一个类别约 20 个候选，再按使用需求扩大。目录条目数量与经过测试的数量分开显示。

服务卡展示：操作能力、认证要求、价格事实及未知项、版本、最近测试时间、样本量、延迟分位数、具名任务检查结果、方法版本、可复现运行入口。没有足够样本则显示 evidence insufficient。

新增页面建议：/services/{id}、/methods/{profile}、/runs/{public_id}。服务卡可被搜索引擎和 Agent 读取；private run 默认不可公开。只对有独立证据内容的页面开放索引，不生成无数据长尾页面。

入口：一句用户收益 + 真实 search 示例 + 安装命令 + 检查自家服务入口。badge 只表达具体检查、版本和时间，不发万能“可信 92 分”。

衡量 view → install → authorized_first_run → second_day_use → retained_project。匿名访问统计与用户/项目身份分开；本地遥测 opt-in，不上传 query 或 owner 偏好。

外部传播只讲 ASM、真实方法与结果。不给未回复者催促；新 outreach 面向已经需要多搜索服务的项目，提供可运行接入补丁或适配示例，发出前按用户要求经 OpenCode 独立审查。

## 9. 多 Agent 与跨组织价值

同 owner 的 Agent 使用相同有效政策，但数据访问仍按身份区分。一个 worker 的失败与结果可被授权的后续 worker 查询。失败建议由 ASM 返回，重试和调度由 harness 执行。

同一 evidence event 可由 REST/MCP/A2A 调用产生；A2A Task ID 必须绑定 server 身份和版本。completed 不是正确性标签。

MVP 加一个两 worker fixture：A 观测供应商失败，B 在同一 scope/时效下参考该证据；不同 owner 默认读不到私有事件。它是互操作验证，不是外部采用。

跨组织公共证据增加身份、任务/版本绑定、样本分母、来源集中度、争议与撤销。首版开放读取经过审核的公开测量，匿名提交仅进入隔离待审队列，不影响正式选择。

## 10. 评估：防止自证

两条实验分开：任务编译是否正确；给定相同合同和候选时，选择是否改善结果。

候选对照：host 当前固定服务、在训练集上选好的最佳固定服务、供应商原生 auto 模式、最便宜可用服务、强模型读取相同最新原始文档、强模型读取相同规范化事实、ASM bootstrap 策略。历史 TOPSIS 仅作额外诊断。服务原生 auto 也可能按任务改变检索配置和费用，必须记录实际模式，不能用弱配置人为制造 ASM 优势。

固定模型版本、提示词、服务配置、结果数量、内容抓取范围和调用预算；所有路径记录编译/选择/重试/结果处理的总延迟与总成本。不要把搜索摘要和全文抓取直接比较。任务通过率的真值需要全文核验时，用独立且相同的评审流程查看冻结来源，不把评审过程的额外信息喂回选择器。

等信息量实验检验格式与决策方法；另设实际可用数据实验检验整个产品。后者允许 ASM 提供新的观测，但其收益不得全部归因于算法。预先记录服务/模式/API 或 SDK 版本、区域及缓存策略，避免把不同配置合成品牌平均分。

初步目标 60 个独立任务，涵盖官方文档检索、时间敏感事实、多来源查证、中英文查询；按任务家族/域名分组保留至少 20 个未用于调参的 held-out 任务。至少一部分题目由外部试用者提供。60 是试点规模，不是统计效力保证。

同一时间窗口随机化服务调用顺序，保留结果快照；随机型选择至少 3 个 seed，seed 与同模板改写不是独立样本。只在预算已授权时执行多服务 live 对照。

任务判定先冻结：官方域名命中、时间条件满足、所需事实证据、来源支持程度。模型 judge 只作辅助，评审隐藏服务身份；高分歧项人工审查，不能使用 eligibility 或自家 utility 作为答案。

报告覆盖率/弃权率、来源支持的任务通过率、用户纠正、p50/p95 总耗时、实际/估算费用分栏、约束违反、失效证据使用。二元配对使用 exact McNemar；差值区间按任务家族 cluster bootstrap；多对照声明主比较并处理多重比较。统计实现由算法研究者复核。

扩大默认路由门槛：相对 host 现有基线，通过率提高至少 5 个百分点且差值 95% 区间下界大于 0；或通过率差值区间下界高于 -3 个百分点且每成功任务成本降低至少 15%，成本节省区间下界大于 0。小样本不满足时记 inconclusive，不能宣称提升。两类门槛预先选主目标，不能看完结果再选赢家。算法研究者在试点前根据可接受差值和预估方差制定功效/样本量计划；60 题不足时不降低置信门槛，可在授权预算内补样本。

强制授权/预算/隐私边界违规在故障测试中必须为 0；报告样本数，不把零观测外推为零风险。owner 不同意替换时尊重其现有方案。

## 11. 顺序、任务包和验收

下列路径为建议新增位置；执行者先检查现有模块并避免重复实现。

| 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|
| T0 现状锁定 | 无 | docs/validation/current-state.md；分支/SHA/测试基线/能力状态 | 区分 stable、experimental、planned；保留现有未提交内容 |
| T1 合同 | T0 | schema/ 下 request/evidence/decision/outcome draft；golden fixtures | 三个跨模块消费者使用同一合同；unknown、冲突、过期有反例 |
| T2 服务事实与 adapter | T1 | src/asm_protocol/providers/；3 份有日期来源的 search facts；脱敏 replay | 3 种响应和错误映射；credits/估算/实际费用不混淆；无自动收费 |
| T3 bootstrap 选择与回执 | T1,T2 | selection service、JCS 校验、legacy 兼容 | 指定工具、未知成本、外发限制、证据失效均符合合同 |
| T4 实际使用入口 | T3 | asm search/现有 MCP 新工具（拟议）；本地结果及回执存储 | 干净安装 replay 贯通；有授权才 live；用户拿到搜索结果 |
| T5 观测与故障闭环 | T4 | outcome 写入、失效与回退、双 worker fixture | 429/timeout/账额耗尽/跨 owner/版本变化故障注入通过 |
| T6 页面与激活测量 | T4,T5 | 3 张可索引服务卡、方法页、明确分享页面、漏斗事件 | 无假评分、无私有内容泄漏、回放不冒充 live |
| T7 评估及外部试点 | T5,T6 | 冻结实验协议、结果表、安装观察、每周使用证据 | 第 2、10 节；不以 outreach 数量验收 |
| T8 扩展 | T7 达标 | 更多候选/类别、第三方 evidence ingest、付费试点 | 持续使用和效果支持扩展；未达标先诊断原因 |

每任务一个可审查变更，先模块测试，再端到端；文档改动不必跑整个套件。不要一次重写全部架构。T1–T6 不依赖新算法发布。

## 12. 算法研究单独交接

执行模型不得自行更改：默认效用函数、全局分数、偏好标签权重、探索率、风险容忍阈值、bandit 默认策略、缺失数据插补、质量置信区间的选择含义。

给研究模型的输入：版本化候选特征、owner 明示选择/替换、曝光分母、采样策略/propensity（若有）、任务家族、observed outcomes、预算与风险条件。历史缺少 propensity 时，不能假装可以无偏离线评估新策略。

研究输出：问题定义、可比基线、特征稳定性、冷启动/非平稳条件、反事实局限、预注册指标、held-out 结果、代码审查及建议。Bayesian、LinUCB、Thompson 都是候选，不能凭模型新旧或公式复杂度决定上线。

原型中缺失特征默认转零、reward 合并 choice/outcome 等行为必须专项审查。质量差、拒绝使用、权限不足、无账户和模型不熟悉工具分别建模；不能把成功返回当 owner 喜欢。

在线探索只有可逆任务、明确外发授权与探索预算内允许；先 shadow。复杂算法获益未证实时，bootstrap 保持可用。

## 13. 商业假设与停止条件

初期 SDK 与公开事实免费；潜在付费项是团队私有历史、持续测量、变更提醒、审计导出。价格先访谈和试点验证，付费重测不得购买更高评级。

证据需求与责任承担分开验收：先证明谁决定、谁执行、哪些检查通过；有合同与独立风控后才考虑有限保证。

如果 5 次观察式安装中超过 2 次失败，优先修安装/授权链路；如果激活后不重复使用，访谈任务频率和替代成本；如果不存在服务间可预测差异，不继续开发复杂路由，评估测量/审计是否单独有价值。四周试点未形成持续使用时冻结目录扩张，记录应调整的人群、场景或收益假设。

## 14. 给执行模型的启动指令

> 以本文为任务入口，从 T0 开始，按依赖交付至 T6；遇到缺少账户或费用授权，完成其余本地/replay/adapter 工作并列出精确阻塞。保留 stable 和实验分支边界。新 schema 先冻结 golden examples，再实现生产者和消费者。所有费用保持在用户已授权范围内；不创建付费资源。外部消息、push 与发布前按用户已有要求交由 OpenCode 可用模型独立审查，记录审查范围、结论和修复；没有完成审查不绕过。每次报告只说交付、验证、阻塞。涉及第 12 节决策先形成可重现实验问题交给研究模型，不凭感觉补公式。对外素材使用 ASM 自身叙事，不出现竞品名。

## 15. 研究依据与局限

访问日期均为 2026-09-05；下面是产品判断所依据的原始文档，API 实际收费与质量需 live 验证。

- [MCP Tools，2025-06-18 版本](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)：工具列表可变，annotations 需按来源信任，结构化结果支持校验。本版用于边界研究，实现时与安装 SDK 的协商协议匹配。
- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)：公开请求参数、usage credits、request_id；支持按实际配置归一化，不直接假定单位美元价格。
- [Exa Search](https://exa.ai/docs/reference/search)：costDollars 文档明确是估算，账单来自 usage counters。因此 receipt 区分估算与结算。
- [Firecrawl Search](https://docs.firecrawl.dev/features/search)：搜索与抓取附加费用不同，数据留存模式不同；因此操作/账户配置必须进证据 scope。
- [RFC 8785](https://www.rfc-editor.org/info/rfc8785/)：可复现 JSON 表示；本规范选择它定义新的摘要 profile。
- [OpenTelemetry GenAI 文档迁移页](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)：语义约定正在迁移，adapter 应锁定版本，不能把 trace 当任务质量证明。
- 本仓 docs/release-v0.6.0.md、docs/specs/selection-receipt.md、docs/design/adaptive-selection-v0.7.md：稳定能力与实验边界。
- [Context7 PR #3105](https://github.com/upstash/context7/pull/3105)：维护者认为标准或采用不足，不愿承担元数据维护；支持先交付独立使用价值的判断，不代表整个市场的统计结论。

本轮做了来源文档、源码接口与既有反馈核验，没有购买 API 调用、验证真实质量优劣或完成客户访谈。首个场景、试点阈值和收费模型都是明确待验证的产品决策。

# 🎬 ASM Demo Video — 完整录制指南

> 目标时长：2-3 分钟
> 提交截止：2026-04-26 08:00 北京时间
> 本文档包含：环境准备、分镜脚本、旁白/字幕文案、技术检查清单、后期处理

---

## 一、录制前准备

### 1.1 环境配置

```bash
# 确保在 asm 项目根目录
cd /Users/guoyi/Desktop/asm

# 确认 .env 配置
cat payments/.env | grep -E "PAYMENT_MODE|GEMINI"
# PAYMENT_MODE=live     ← 必须是 live（链上真实交易）
# GEMINI_API_KEY=xxx    ← 如果有，填上；没有也行（规则引擎兜底）
```

### 1.2 启动服务

```bash
# Terminal 1: 启动 ASM Registry + Payment Server
cd /Users/guoyi/Desktop/asm/payments
npm run dev:all

# 等待看到:
#   🚀 ASM Payment Server started
#   Mode: 🟢 LIVE (x402 + Circle Gateway)
```

### 1.3 确认服务正常

```bash
# Terminal 2: 健康检查
curl -s http://localhost:4402/api/health | python3 -m json.tool

# 应该看到:
#   "status": "ok"
#   "mode": "live (x402 + Circle Gateway)"
#   "ledger.totalTransactions": 0  ← 重要：确保是 0（干净状态）
```

### 1.4 录屏工具

| 工具 | 推荐度 | 说明 |
|------|:---:|------|
| **QuickTime** (Cmd+Shift+5) | ⭐⭐⭐ | macOS 原生，最简单 |
| **OBS Studio** | ⭐⭐⭐⭐ | 可同时录屏+摄像头+音频 |
| **ScreenFlow** | ⭐⭐⭐⭐⭐ | 最专业，自带剪辑 |

### 1.5 屏幕设置

```
分辨率：1920×1080（或 2560×1440 降采样）
终端字体：16-18pt（确保视频里看得清）
终端主题：深色背景（与项目 UI 一致）
浏览器：Chrome，关掉书签栏和扩展图标
桌面：清空，只留需要的窗口
```

### 1.6 窗口布局

```
┌────────────────────────────────┐
│                                │
│    浏览器（Marketplace UI）     │
│    http://localhost:4402/       │
│                                │
├────────────────────────────────┤
│                                │
│    终端（命令 + Demo 输出）     │
│                                │
└────────────────────────────────┘

或者全屏切换模式（每个 Scene 切一次）
```

---

## 二、分镜脚本（8 个场景）

### 🎬 Scene 1: 开场 — 一句话 Pitch (0:00 - 0:10)

**画面**：浏览器全屏，显示 Marketplace 首页

**字幕/旁白**：
> "ASM — the first protocol that lets AI agents discover, evaluate, and pay for services autonomously."

**操作**：
1. 展示 Marketplace 标题
2. 鼠标缓慢滚动，展示 Onboarding Prompt 区域
3. 停留 2 秒

---

### 🎬 Scene 2: 问题陈述 (0:10 - 0:25)

**画面**：白色文字 + 深色背景（可以用终端 echo 或者提前做好的图片）

**字幕/旁白**：
> "Today, when an AI agent needs to call an external API — an LLM, an image generator, an email service — it has zero structured data to compare providers."
>
> "It either hardcodes one, or burns tokens searching. This is the API discovery problem."

**操作**（终端里展示）：
```bash
echo ""
echo "  ❌ Agent today: hardcode OpenAI, hope for the best"
echo "  ❌ No pricing comparison, no quality data, no trust scores"
echo "  ❌ Result: 3-10x cost overruns or quality mismatches"
echo ""
echo "  ✅ ASM: structured manifests + algorithmic ranking + per-call payment"
echo ""
```

---

### 🎬 Scene 3: 70 个服务 Manifest (0:25 - 0:40)

**画面**：终端

**操作**：
```bash
# 展示服务数量
curl -s http://localhost:4402/api/services | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  📦 {d[\"count\"]} real-world services across multiple categories')
cats = {}
for s in d['services']:
    t = s['taxonomy'].split('.')[1] if '.' in s['taxonomy'] else s['taxonomy']
    cats[t] = cats.get(t, 0) + 1
for cat, count in sorted(cats.items(), key=lambda x:-x[1])[:8]:
    print(f'     {cat}: {count} services')
"
```

**字幕/旁白**：
> "ASM Registry holds 70 real-world services across 47 categories — from LLMs to databases, email APIs to deployment platforms. Each one has a machine-readable manifest with pricing, quality benchmarks, and SLA data."

---

### 🎬 Scene 4: Agent 自然语言决策 (0:40 - 1:10)

**画面**：终端

**操作**：
```bash
# Agent 用自然语言描述需求
curl -s -X POST http://localhost:4402/api/agent-decide \
  -H "Content-Type: application/json" \
  -H "X-Buyer-Address: 0xDemoAgent001" \
  -H "X-Agent-Name: DemoAgent" \
  -d '{"request": "I need a cheap and fast LLM for customer service chatbot"}' \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
print()
print('  🤖 Agent request: \"I need a cheap and fast LLM for customer service chatbot\"')
print()
i = d.get('intent', {})
print(f'  📊 Parsed intent:')
print(f'     Taxonomy: {i.get(\"taxonomy\")}')
w = i.get('weights', {})
print(f'     Weights: cost={w.get(\"w_cost\",0):.0%} quality={w.get(\"w_quality\",0):.0%} speed={w.get(\"w_speed\",0):.0%} reliability={w.get(\"w_reliability\",0):.0%}')
print()
r = d.get('scoring', {}).get('ranking', [])
print(f'  🏆 Top 3 (from {d.get(\"scoring\",{}).get(\"count\",0)} candidates):')
for s in r[:3]:
    print(f'     #{s[\"rank\"]} {s[\"display_name\"]:30s} score={s[\"total_score\"]:.4f}')
rec = d.get('recommendation', {})
print()
print(f'  ✅ Recommendation: {rec.get(\"display_name\")}')
p = d.get('payment', {})
print(f'  💰 Payment: {p.get(\"amount\")} USDC on {p.get(\"chain\")}')
t = d.get('trust', {})
if t:
    print(f'  🔒 Trust: {t.get(\"serviceId\",\"\")[:30]} score={t.get(\"trustScore\",0):.3f} ({t.get(\"numReceipts\",0)} receipts)')
print()
"
```

**字幕/旁白**：
> "The agent describes what it needs in plain English. ASM parses the intent, maps it to a service category, runs TOPSIS multi-criteria scoring across all matching services, and returns a ranked recommendation."
>
> "Each call costs $0.005 USDC — paid through Circle Nanopayments on Arc."

**⚡ 关键**：让观众看到完整的 intent → ranking → recommendation → payment 链路。

---

### 🎬 Scene 5: 不同偏好 → 不同结果 (1:10 - 1:30)

**操作**：
```bash
# 同一类别，但偏好质量
curl -s -X POST http://localhost:4402/api/agent-decide \
  -H "Content-Type: application/json" \
  -H "X-Buyer-Address: 0xDemoAgent002" \
  -d '{"request": "Find the highest quality LLM for complex reasoning, cost does not matter"}' \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('scoring', {}).get('ranking', [])
print()
print('  🎯 Quality-first agent picks:')
for s in r[:3]:
    print(f'     #{s[\"rank\"]} {s[\"display_name\"]:30s} score={s[\"total_score\"]:.4f}')
rec = d.get('recommendation', {})
print(f'  → Winner: {rec.get(\"display_name\")} (quality-optimized)')
print()
"
```

**字幕/旁白**：
> "Different preference weights produce different rankings. A budget-conscious agent picks DeepSeek. A quality-focused agent picks Claude. The TOPSIS algorithm finds the optimal tradeoff for each agent's unique needs."

---

### 🎬 Scene 6: E2E Demo — 50+ 笔交易 (1:30 - 2:00)

**操作**：
```bash
# 运行完整 E2E Demo
npm run demo
```

**字幕/旁白**：
> "Now let's simulate a real agent marketplace. 14 independent agents — each with their own wallet, preferences, and service needs — making autonomous decisions."

**等 Demo 跑完后指出**：
1. 55+ 笔交易完成
2. 14 个独立 Agent 地址
3. 多个 taxonomy 类别覆盖
4. Trust Delta 分数已更新

---

### 🎬 Scene 7: Arc Block Explorer 验证 (2:00 - 2:20)

**操作**（如果 live 模式有真实 txHash）：
```bash
# Demo 输出中会有 Block Explorer 链接
# 点击打开浏览器，展示链上交易
open "https://testnet.arcscan.app/tx/<txHash>"
```

**如果是 mock 模式**，展示之前 live 模式的截图或链接：
```bash
# 之前 live demo 的真实交易
open "https://testnet.arcscan.app/address/0x2bC6aa5b4b0e3A7B9C5e3f7c6D8e9F0a1B2c32998D"
```

**字幕/旁白**：
> "Every transaction is verifiable on Arc Testnet Block Explorer. Real USDC, real settlement, real on-chain evidence."

---

### 🎬 Scene 8: 为什么传统 Gas 做不到 + 结尾 (2:20 - 2:50)

**画面**：终端或提前准备的对比图

**操作**：
```bash
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  Why traditional gas models can't do this:      │"
echo "  │                                                 │"
echo "  │  Ethereum L1:  ~\$2-50 per tx   (400x payment)  │"
echo "  │  L2 rollups:   ~\$0.01-0.10     (2-20x payment) │"
echo "  │  Arc + Nano:   ~\$0.0001        (0.02x payment) │"
echo "  │                                                 │"
echo "  │  Our payment: \$0.005 per call                   │"
echo "  │  50 calls = \$0.25 total, gas = \$0.005           │"
echo "  │  → 47x margin between payment and gas           │"
echo "  └─────────────────────────────────────────────────┘"
echo ""
```

**字幕/旁白**：
> "When the gas fee exceeds the payment itself, micro-payments are impossible. Circle Nanopayments on Arc achieve a 47x margin — making sub-cent agent commerce economically viable for the first time."

**结尾画面**：

```bash
echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║                                                   ║"
echo "  ║   ASM — Agent Service Manifest Protocol           ║"
echo "  ║                                                   ║"
echo "  ║   OpenAPI describes what a service CAN DO.        ║"
echo "  ║   ASM describes what a service IS WORTH.          ║"
echo "  ║   Nanopayments make evaluation self-sustaining.   ║"
echo "  ║                                                   ║"
echo "  ║   github.com/YE-YI7/asm-spec                 ║"
echo "  ║   70 services • 47 categories • 50+ transactions  ║"
echo "  ║                                                   ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""
```

---

## 三、Circle Developer Console 截图（比赛要求）

在视频中或视频之外，需要展示 Circle Developer Console：

1. 打开 https://console.circle.com
2. 登录你的账号
3. 截图展示：
   - API Key 管理页面（Testnet Key）
   - 如果有交易监控页面，截图
4. 可以在视频的 Scene 7 之后快速切到浏览器展示

---

## 四、旁白录制建议

### 4.1 如果自己录旁白

- 用 AirPods / 有线耳机的麦克风即可
- 安静环境，关窗关空调
- 语速适中，每句话后停顿 1 秒
- 不需要完美，自然即可

### 4.2 如果不想录旁白

- 用字幕代替（上面每个 Scene 的字幕文案已写好）
- 可以用 CapCut/剪映 自动生成字幕
- 背景音乐：轻快的电子乐，音量调低（推荐 YouTube Audio Library 免费曲库）

### 4.3 如果想用 AI 配音

```bash
# 可以用 ElevenLabs / OpenAI TTS
# 把旁白文案丢进去生成音频，然后和录屏合并
```

---

## 五、后期处理

### 5.1 剪辑要点

1. **去掉等待时间**：Demo 跑 50+ 笔交易可能要 30-60 秒，剪辑加速到 5 秒
2. **加速打字**：curl 命令可以提前准备好，复制粘贴，不需要现场手打
3. **关键数据放大**：用框/箭头标注重要数字（交易数、金额、Trust Score）
4. **转场**：简单的淡入淡出即可，不需要花哨效果

### 5.2 时间控制

| Scene | 时长 | 内容 |
|:---:|:---:|------|
| 1 | 10s | 开场 Pitch |
| 2 | 15s | 问题陈述 |
| 3 | 15s | 70 个服务展示 |
| 4 | 30s | Agent 自然语言决策（核心） |
| 5 | 20s | 不同偏好不同结果 |
| 6 | 30s | E2E Demo 50+ 笔交易 |
| 7 | 20s | Block Explorer 验证 |
| 8 | 30s | Gas 对比 + 结尾 |
| **总计** | **~170s** | **≈ 2:50** |

### 5.3 导出设置

```
格式：MP4 (H.264)
分辨率：1920×1080
帧率：30fps
比特率：8-10 Mbps
音频：AAC 128kbps
文件大小：< 100MB
```

---

## 六、提前准备的命令（复制粘贴用）

把以下命令保存到一个文件，录制时直接复制粘贴：

```bash
# Scene 3: 服务列表
curl -s http://localhost:4402/api/services | python3 -c "import json,sys;d=json.load(sys.stdin);print(f'📦 {d[\"count\"]} services');cats={};[cats.update({s['taxonomy'].split('.')[1]:cats.get(s['taxonomy'].split('.')[1],0)+1}) for s in d['services']];[print(f'  {k}: {v}') for k,v in sorted(cats.items(),key=lambda x:-x[1])[:8]]"

# Scene 4: Agent 决策（成本优先）
curl -s -X POST http://localhost:4402/api/agent-decide -H "Content-Type: application/json" -H "X-Buyer-Address: 0xDemoAgent001" -d '{"request":"I need a cheap and fast LLM for customer service chatbot"}' | python3 -m json.tool | head -40

# Scene 5: Agent 决策（质量优先）
curl -s -X POST http://localhost:4402/api/agent-decide -H "Content-Type: application/json" -H "X-Buyer-Address: 0xDemoAgent002" -d '{"request":"Find the highest quality LLM for complex reasoning"}' | python3 -m json.tool | head -40

# Scene 6: E2E Demo
npm run demo
```

---

## 七、录制前检查清单

- [ ] `.env` 中 `PAYMENT_MODE=live`（如果要展示真实链上交易）
- [ ] 服务已启动且健康（`curl localhost:4402/api/health`）
- [ ] Ledger 为空（重启服务清空，或确认是干净状态）
- [ ] 终端字体 ≥ 16pt
- [ ] 浏览器无多余标签页和书签栏
- [ ] 桌面干净
- [ ] 通知已关闭（macOS: System Settings → Focus → Do Not Disturb）
- [ ] 录屏工具已就绪
- [ ] 旁白文案已打印/放在旁边
- [ ] 准备好的命令已保存到文件

---

## 八、如果出错了

1. **服务连接失败**：重启 `npm run dev:all`，等 3 秒
2. **Demo 中途报错**：不要慌，直接重新运行 `npm run demo`
3. **链上交易失败**：切换到 mock 模式（改 `.env` 中 `PAYMENT_MODE=mock`），mock 模式下一切正常运行，只是 txHash 是模拟的
4. **忘词了**：用字幕代替旁白，后期加
5. **录制时间超了**：Scene 2（问题陈述）和 Scene 8（Gas 对比）可以缩短

---

## 九、提交到 lablab.ai

1. 视频上传到 YouTube（Unlisted）或 Loom
2. 复制链接填入 lablab.ai 提交表单
3. 同时提交：
   - GitHub 仓库链接：https://github.com/YE-YI7/asm-spec
   - Demo URL（如果已部署）
   - Circle Product Feedback（已写好在 CIRCLE-PRODUCT-FEEDBACK.md）

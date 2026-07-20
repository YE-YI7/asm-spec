# 🎬 ASM × Nanopayments — 录屏脚本

> 目标时长：2-3 分钟
> 工具：QuickTime (Cmd+Shift+5) 或 OBS
> 分辨率：1920×1080，字体放大到 16pt

---

## 准备工作（录屏前）

```bash
# 1. 确保两个服务已启动
cd /Users/guoyi/Desktop/asm/payments
npm run dev:all

# 2. 打开浏览器，访问 Dashboard
open http://localhost:4402/api/dashboard

# 3. 清空终端
clear
```

---

## 录屏流程

### 🎬 Scene 1: 开场 — Dashboard（0:00 - 0:15）

**画面**：浏览器全屏，显示 Dashboard

**旁白/字幕**：
> "ASM — the first protocol that lets AI agents discover, evaluate, and pay for services autonomously."

**操作**：
1. 展示 Dashboard 标题 "ASM × Circle Nanopayments"
2. 指出 "MOCK — Development Mode" 标签
3. 此时统计数字应该是 0

---

### 🎬 Scene 2: 服务发现 — 70 个真实服务（0:15 - 0:35）

**画面**：切换到终端

**操作**：
```bash
# 展示有多少服务
curl -s http://localhost:4402/api/services | python3 -m json.tool | head -25
```

**旁白/字幕**：
> "ASM Registry holds 70 real-world services across 47 categories — LLM, image generation, video, TTS, embedding, and GPU compute."

---

### 🎬 Scene 3: Agent 付费评分（0:35 - 1:15）

**画面**：终端

**操作**：
```bash
# 一个 Agent 需要找最便宜的 LLM
curl -s -X POST http://localhost:4402/api/score \
  -H "Content-Type: application/json" \
  -d '{
    "taxonomy": "ai.llm.chat",
    "w_cost": 0.6,
    "w_quality": 0.2,
    "w_speed": 0.15,
    "w_reliability": 0.05
  }' | python3 -m json.tool
```

**旁白/字幕**：
> "An agent sends a scoring request with its preference weights. It pays $0.005 USDC per call through Circle Nanopayments."

**指出响应中的关键字段**：
1. `payment.amount` — "$0.005"
2. `payment.txHash` — 链上交易哈希
3. `scoring.ranking` — TOPSIS 排名结果
4. `receipt` — 支付收据

---

### 🎬 Scene 4: 不同偏好 → 不同结果（1:15 - 1:35）

**操作**：
```bash
# 同一个 taxonomy，但偏好质量
curl -s -X POST http://localhost:4402/api/score \
  -H "Content-Type: application/json" \
  -d '{
    "taxonomy": "ai.llm.chat",
    "w_cost": 0.1,
    "w_quality": 0.7,
    "w_speed": 0.1,
    "w_reliability": 0.1
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  #{r[\"rank\"]} {r[\"display_name\"]:30s} score={r[\"total_score\"]:.4f}') for r in d['scoring']['ranking'][:5]]"
```

**旁白/字幕**：
> "Different preference weights → different rankings. Cost-optimized agents pick DeepSeek. Quality-focused agents pick Claude. The TOPSIS algorithm finds the optimal tradeoff."

---

### 🎬 Scene 5: E2E Demo — 50+ 笔交易（1:35 - 2:15）

**操作**：
```bash
# 运行完整 E2E Demo
npm run demo
```

**旁白/字幕**：
> "Now let's simulate 6 different AI agents — a ChatBot, a Creative Agent, a Voice Agent, a RAG Agent, a DevOps Agent, and a Multi-Modal Agent — each with their own service needs and budget preferences."

**等待 Demo 跑完，指出**：
1. 51 笔交易完成
2. 总金额 0.243 USDC
3. 按 taxonomy 和 endpoint 的统计

---

### 🎬 Scene 6: Dashboard 实时更新（2:15 - 2:35）

**画面**：切回浏览器 Dashboard

**操作**：
1. 展示 Dashboard 现在显示 51 笔交易
2. 展示 Total Volume
3. 展示 Recent Transactions 表格
4. 展示 By Endpoint 和 By Taxonomy 统计

**旁白/字幕**：
> "All 51 transactions are recorded in real-time. Each one is a sub-cent USDC payment on Arc — something traditional gas models simply can't do."

---

### 🎬 Scene 7: 为什么传统 Gas 模型做不到（2:35 - 2:50）

**画面**：终端或字幕

**展示对比**：
```
Traditional gas model:
  Gas per tx:     ~$0.01 - $0.50
  Our tx amount:  $0.002 - $0.005
  → Gas > Payment amount ❌

Circle Nanopayments on Arc:
  Batched settlement, near-zero marginal cost
  51 transactions, total cost: $0.243 USDC
  → Economically viable ✅
```

**旁白/字幕**：
> "When the gas fee exceeds the payment itself, micro-payments are impossible. Circle Nanopayments solve this by batching settlements on Arc."

---

### 🎬 Scene 8: 结尾（2:50 - 3:00）

**画面**：Dashboard 或 Logo

**旁白/字幕**：
> "ASM — OpenAPI describes what a service CAN DO. ASM describes what a service IS WORTH. Nanopayments make the evaluation self-sustaining."

**展示**：
- GitHub: github.com/YE-YI7/asm-spec
- 70 services • 47 categories • 51 transactions • $0.243 USDC

---

## 录屏技巧

1. **字体大小**：终端字体调到 16-18pt，确保视频里看得清
2. **窗口布局**：终端占左半屏，浏览器占右半屏（或全屏切换）
3. **打字速度**：不要太快，让观众能跟上命令
4. **暂停**：每个关键输出后停 2-3 秒，让观众消化
5. **错误处理**：如果命令出错，不要慌，直接重新输入
6. **背景音乐**：可选，轻快的电子乐，音量调低

## 如果用 Live 模式录

如果你搞定了 MetaMask 钱包，切换到 live 模式后：
1. 修改 `.env` 中 `PAYMENT_MODE=live`
2. 所有 txHash 会变成真实的链上哈希
3. 可以在 Demo 中加一步：打开 Arc Block Explorer 验证交易
   ```
   open https://testnet.arcscan.app/tx/<txHash>
   ```
4. 这会是一个巨大的加分项

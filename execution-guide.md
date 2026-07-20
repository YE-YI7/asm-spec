# ASM 落地执行指南（手把手版）

> 写给自己看的，不是给别人看的。每一步都写清楚"打开什么→点什么→写什么"。
> 时间窗口：4/18 - 5/7

---

## 任务一：真实 A/B 测试（4/18-4/20，预算 $10-15）

### 为什么先做这个
没有真实数据，后面的博客、论文、社区发帖全是空话。这是所有后续任务的弹药。

### 需要准备的 API Key

你需要以下三个的任意一个免费 tier 或付费 key：

| 平台 | 注册地址 | 免费额度 |
|------|---------|---------|
| OpenAI | https://platform.openai.com/signup | 新用户 $5 免费 |
| Google AI Studio | https://aistudio.google.com/ | Gemini 2.5 Pro 免费调用（有 rate limit） |
| Anthropic | https://console.anthropic.com/ | 新用户 $5 免费 |

**注册步骤（以 OpenAI 为例）：**
1. 打开 https://platform.openai.com/signup
2. 用 Google 账号或邮箱注册
3. 注册完进入 Dashboard → 左侧菜单 "API keys" → "Create new secret key"
4. 复制这个 key，在终端里运行：
   ```bash
   echo 'export OPENAI_API_KEY="sk-你的key"' >> ~/.zshrc
   source ~/.zshrc
   ```
5. 同样的流程对 Google 和 Anthropic 各做一次：
   ```bash
   echo 'export GOOGLE_API_KEY="你的key"' >> ~/.zshrc
   echo 'export ANTHROPIC_API_KEY="你的key"' >> ~/.zshrc
   source ~/.zshrc
   ```

### 安装依赖

```bash
cd /Users/guoyi/Desktop/asm
pip3 install openai anthropic google-generativeai
```

### 准备测试 Prompt

不需要自己想 50 个 prompt。用这些来源：

1. **MMLU 数据集**（大学考试题，有标准答案）：
   - 打开 https://huggingface.co/datasets/cais/mmlu
   - 随便挑 30 个不同学科的选择题

2. **或者更简单** — 让 Claude 帮你生成：

   给另一个 agent 这个 prompt：
   ```
   生成 50 个多样化的 LLM 测试 prompt，保存为 JSON 文件。要求：
   - 10 个简单问答（"法国的首都是什么"这种）
   - 10 个数学/逻辑题（有明确答案的）
   - 10 个代码生成题（"写一个 Python 函数计算斐波那契"这种）
   - 10 个创意写作题（"写一首关于春天的诗"这种）
   - 10 个长文本摘要题（给一段 500 字的文本让它总结）
   
   每个 prompt 包含：id, category, prompt, expected_answer（如果有的话）
   保存到 /Users/guoyi/Desktop/asm/experiments/test_prompts.json
   ```

### 运行测试

项目里已经有 `experiments/real_ab_test.py`。检查一下它是否直接能跑：

```bash
cd /Users/guoyi/Desktop/asm
python3 experiments/real_ab_test.py --help
```

如果需要改动，核心逻辑是这样的：

```
对每个 prompt：
  1. 用 ASM scorer 根据 prompt 类型选择最优模型
     - 简单问答 → 偏好 cost（选便宜的）
     - 代码生成 → 偏好 quality（选最好的）
     - 创意写作 → 偏好 quality + speed
  2. 同时用固定的 GPT-4o 调用
  3. 同时用固定的最贵模型调用
  4. 记录：真实延迟、真实 token 数、真实成本、回答内容
```

### 质量评分（LLM-as-Judge）

跑完之后，用一个 LLM 给所有回答打分：

```python
# 伪代码，让 agent 帮你实现
for each (prompt, response_a, response_b, response_c):
    judge_prompt = f"""
    Rate the following response on a scale of 1-10.
    Question: {prompt}
    Response: {response}
    Score (just the number):
    """
    score = call_gpt4o_mini(judge_prompt)  # 用最便宜的模型当评委
```

### 最终产出

一张这样的表：

```
| 策略 | 平均成本/次 | 平均延迟 | 平均质量分 | 总成本 |
|------|-----------|---------|----------|--------|
| ASM 选择 | $0.003 | 1.2s | 8.1/10 | $0.15 |
| 固定 GPT-4o | $0.005 | 0.8s | 8.3/10 | $0.25 |
| 固定最贵 | $0.008 | 1.5s | 8.4/10 | $0.40 |
```

关键结论："ASM 选择在质量仅下降 2% 的情况下节省了 40% 成本。"

---

## 任务二：写博客发社区（4/21-4/23）

### 在哪写

用 **dev.to**（开发者博客平台，免费，不需要审核）。

1. 打开 https://dev.to
2. 用 GitHub 账号登录（点 "Log in" → "Continue with GitHub"）
3. 点右上角 "Create Post"

### 写什么

标题不要提 ASM。写用户关心的问题。

**推荐标题（选一个）：**
- "How to Make Your AI Agent Choose the Cheapest API Automatically"
- "I Built a TOPSIS-Based Service Selector for LangChain Agents"
- "Stop Hardcoding API Keys: Let Your Agent Pick the Best Service at Runtime"

**文章结构（直接照着写）：**

```markdown
---
title: How to Make Your AI Agent Choose the Cheapest API Automatically
published: true
tags: ai, langchain, python, opensource
---

## The Problem

（2-3 句话描述问题）
When you build an AI agent with LangChain, you hardcode which LLM to use.
But what if GPT-4o is cheaper for simple tasks and Claude is better for coding?
Your agent should pick the best service for each task automatically.

## The Solution

（贴代码，展示 ASMRegistryTool 的用法）
```python
from asm_tools import ASMRegistryTool

tool = ASMRegistryTool()
result = tool._run("cheapest LLM for simple Q&A")
print(result)
```

## Real Results

（贴你的 A/B 测试数据表）

## How It Works

（简单解释 TOPSIS 算法，不要写公式，用类比）
"Think of it like choosing a restaurant: you care about price, 
food quality, wait time, and reliability. TOPSIS finds the option 
that's closest to your ideal across all dimensions."

## Try It

```bash
git clone https://github.com/YE-YI7/asm-spec
cd asm-spec
python3 integrations/langchain/demo_notebook.py
```

## Links

- GitHub: [asm-spec](https://github.com/YE-YI7/asm-spec)
- Paper (coming soon): [arXiv link]
```

### 发到哪些社区

写完博客后，把链接发到这些地方：

**Reddit（最重要）：**

1. 打开 https://reddit.com（需要账号，没有的话注册一个）
2. 去这些 subreddit 发帖：
   - r/LangChain — https://reddit.com/r/LangChain
     - 标题："[Show] Auto-select the cheapest LLM per task with ASM + LangChain"
     - 内容：简短描述 + 博客链接 + GitHub 链接
   - r/LocalLLaMA — https://reddit.com/r/LocalLLaMA
   - r/MachineLearning — https://reddit.com/r/MachineLearning
     - 用 [Project] tag

**注意事项：**
- Reddit 反感纯推广。先在这些 subreddit 里回复别人的帖子，混个脸熟，3-5 天后再发自己的
- 发帖时用"我做了一个东西，想要反馈"的语气，不要用"我发明了一个革命性的协议"

**LangChain Discord：**

1. 加入：https://discord.gg/langchain
2. 找 #showcase 或 #community-projects 频道
3. 发一条简短消息 + demo 截图 + GitHub 链接

**Hacker News（难度高但回报大）：**

1. 打开 https://news.ycombinator.com
2. 注册账号（如果没有）
3. 点 "submit"
4. Title: "Show HN: ASM – Open protocol for AI agents to choose services automatically"
5. URL: 你的 GitHub 链接
6. **发帖时间很重要**：美国西海岸早上 8-10 点（北京时间晚上 11 点 - 凌晨 1 点）

---

## 任务三：联系中小 API 平台（4/24-4/27）

### 找谁

不要找 OpenAI/Google/Anthropic。找这些**中小平台**，它们有被发现的需求：

| 平台 | 做什么的 | Discord/联系方式 |
|------|---------|-----------------|
| Replicate | 模型推理平台 | https://discord.gg/replicate |
| fal.ai | 快速推理 API | https://discord.gg/fal-ai |
| Together AI | 开源模型 API | https://discord.gg/together-ai |
| Fireworks AI | 高速推理 | https://discord.gg/fireworks-ai |
| Voyage AI | Embedding API | 网站有联系表单 |
| Deepgram | 语音转文字 | https://discord.gg/deepgram |

### 怎么联系

**步骤 1：加入他们的 Discord**

点上面的链接加入。每个 Discord 都有 #general 或 #feedback 频道。

**步骤 2：先混一天**

不要上来就推销。先在频道里回答别人的问题，或者问一个关于他们 API 的真实问题。

**步骤 3：发消息**

在 #feedback 或 #feature-requests 频道发：

```
Hi! I'm building an open protocol called ASM (Agent Service Manifest) 
that helps AI agents programmatically discover and compare API services 
— kind of like Schema.org but for AI APIs.

I've already created a draft manifest for [平台名], based on your 
public pricing page. Here's what it looks like:

[贴一个精简版的 manifest JSON，5-6 行就够]

Would you be interested in:
1. Reviewing this to make sure the data is accurate?
2. Maybe hosting an official .asm.json on your docs site?

The whole spec is open source: https://github.com/YE-YI7/asm-spec

No pressure at all — just thought it might help your API get discovered 
by autonomous agents more easily. Happy to answer any questions!
```

**步骤 4：如果有人回复**

大概率的回复是："Cool, what exactly do we need to do?"

你的回答：
```
Nothing complicated! Just:
1. I'll send you a .asm.json file (it's a simple JSON file, ~30 lines)
2. You review it, tell me if any numbers are wrong
3. If it looks good, I add it to the registry with a "provider-verified" tag

That's it. You don't need to change anything on your end.
Here's the draft: [贴完整 manifest]
```

### 如果没人回复

很正常。发完等 3 天，没回复就换下一家。5 家里能成 1 家就是胜利。

### 用 asm-gen 提前准备好 manifest

在联系之前，先用你的工具生成好他们的 manifest：

```bash
# 如果他们有 OpenAPI spec
python3 tools/asm-gen/asm_gen.py --input their-openapi.json --output replicate.asm.json

# 如果没有，手动写（参考现有的 14 个 manifest）
cp manifests/replicate-gpu.asm.json manifests/fireworks-llama3.asm.json
# 然后编辑里面的字段
```

---

## 任务四：Scopeblind 联合 Demo（4/28-4/30）

### 现状

你们在 Discord 聊了 3 轮，确认了技术方案。但还没有可展示的联合成果。

### 要做的

**步骤 1：发消息催一下 field alignment**

在 Discord 给 Scopeblind 发：

```
Hey! Quick check-in — any progress on the field alignment draft? 

On our side, we've made some updates since we last talked:
- Fixed receipt verification (TOPSIS reasoning bug)
- Added configurable io_ratio for cost normalization
- Python and TypeScript scorers are now fully aligned

Happy to start building the joint demo whenever you're ready. 
I'm thinking a simple GIF showing:
  Agent query → ASM selection → API call → Signed Receipt → Trust Score update

Would that be useful for both of us?
```

**步骤 2：不等他们，先自己做 demo GIF**

用你已有的 verify_demo.py 就够了。

录屏工具：
- Mac 自带：Cmd+Shift+5 → 选择录制区域
- 或者用 asciinema（终端录屏）：
  ```bash
  brew install asciinema
  asciinema rec demo.cast
  # 跑你的 demo
  python3 demo/verify_demo.py
  # 按 Ctrl+D 结束
  # 转成 GIF
  pip3 install agg
  agg demo.cast demo.gif
  ```

**步骤 3：demo 脚本**

录屏时跑这个流程：

```
1. 展示一个 manifest（cat manifests/openai-gpt4o.asm.json | head -20）
2. 跑 scorer 选择服务（python3 demo/e2e_demo.py）
3. 跑 receipt 验证（python3 demo/verify_demo.py）
4. 展示 trust score 更新
```

终端里显示的文字就是 demo 内容，不需要做幻灯片。

---

## 任务五：arXiv 预印本（5/1-5/7）

### 为什么要尽快上 arXiv

- 占时间戳 — 证明你是第一个做这个的
- 被搜到 — 别人搜 "AI agent service selection" 能找到你
- 引用 — 有 arXiv ID 别人就能 cite 你

### 怎么投 arXiv

**步骤 1：注册 arXiv 账号**

1. 打开 https://arxiv.org/user/register
2. 填信息（用学校邮箱，.edu 邮箱更容易通过）
3. 需要一个 endorser — 如果你是第一次投 cs.AI 类目，需要一个已经在 arXiv 上发过论文的人背书
4. **如果找不到 endorser**：投到 cs.MA（Multi-Agent Systems）或 cs.SE（Software Engineering）类目，这些有时不需要 endorsement

**步骤 2：准备 LaTeX**

你的论文草稿在 paper/asm-paper-draft.md。需要转成 LaTeX。

让 agent 做：
```
把 /Users/guoyi/Desktop/asm/paper/asm-paper-draft.md 转成 LaTeX 格式。
使用 ACM 或 IEEE 双栏模板。
保存到 /Users/guoyi/Desktop/asm/paper/latex/ 目录下。
包含 main.tex, references.bib, figures/ 目录。
```

**步骤 3：上传**

1. 打开 https://arxiv.org/submit
2. 选类目：cs.AI（人工智能）或 cs.MA（多 Agent 系统）
3. 上传 .tar.gz 包（包含 main.tex + bib + figures）
4. 填 abstract、作者、标题
5. 提交后 1-2 天上线

### 论文里必须更新的内容

在投之前，确保论文里有：

1. **A/B 测试的真实数据**（任务一的产出）
2. **不要把 TOPSIS 当创新点** — 写成"我们采用 TOPSIS 作为评分方法，因为它在 MCDM 领域经过充分验证且可解释性好"
3. **核心创新点写成**：
   - 第一个完整的 AI agent 服务发现协议
   - 结合 Signed Receipt 的可验证信任积累机制
   - 跨品类、多维度的服务选择框架
4. **Limitations 要诚实写**：质量指标依赖 self-report、冷启动问题、taxonomy 粒度不够

---

## 每日 Checklist

### 4/18（周六）
- [ ] 注册 OpenAI / Google / Anthropic API（如果还没有）
- [ ] 安装依赖（pip3 install openai anthropic google-generativeai）
- [ ] 准备 50 个测试 prompt
- [ ] 开始跑 A/B 测试

### 4/19（周日）
- [ ] A/B 测试跑完
- [ ] 用 LLM-as-Judge 打分
- [ ] 整理数据表

### 4/20（周一）
- [ ] 注册 dev.to 账号
- [ ] 开始写博客

### 4/21（周二）
- [ ] 博客写完发布
- [ ] 注册 Reddit 账号（如果没有）
- [ ] 在 r/LangChain 和 r/LocalLLaMA 发帖

### 4/22（周三）
- [ ] 加入 Replicate / fal.ai / Together AI 的 Discord
- [ ] 先混一天，回复别人的问题

### 4/23（周四）
- [ ] 用 asm-gen 给 3 个平台生成 manifest
- [ ] 在 Discord 发联系消息

### 4/24-4/27
- [ ] 跟进 Discord 回复
- [ ] 给 Scopeblind 发 check-in 消息
- [ ] 录制 demo GIF

### 4/28-4/30
- [ ] Scopeblind 联合 demo（如果他们回了）
- [ ] 更新论文（加入 A/B 数据 + 社区反馈）

### 5/1-5/7
- [ ] LaTeX 排版
- [ ] arXiv 提交

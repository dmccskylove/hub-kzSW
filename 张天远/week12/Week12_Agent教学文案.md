# Week12 Agent 教案 — ReAct 金融分析 Agent 实战

> **受众**：已完成 Week03-11 全部课程，掌握 LLM API 调用、Function Call、RAG、FAISS
> **时长**：约 2.5 小时（理论 40min + 代码走读 70min + 动手实验 40min）
> **核心产出**：理解 ReAct 循环机制，能解释手写 Prompt 解析与 Function Calling 的本质差异

---

## 前置回顾（5 分钟速览）

| 概念 | 来源 | 一句话 |
|------|------|--------|
| LLM API 调用 | 📎 Week05/10 | `client.chat.completions.create(model=..., messages=...)` |
| Function Call | 📎 Week11 | 工具名+参数以 JSON Schema 注册，模型返回 `tool_calls` |
| FAISS 检索 | 📎 Week08/10 | `index.search(vec, top_k)` 余弦相似度取 top_k |
| System Prompt | 📎 Week05 | 对话开头注入的指令，约束模型行为边界 |
| SSE 流式 | 📎 Week10 | `text/event-stream`，服务端逐步推送数据 |

> 以上概念本周仍会用到，但不再展开。需要重读的请回顾对应周次教案。

---

## 目录

1. [总纲：一张图建立全部心智模型](#一总纲)
2. [Agent 是什么：从 Prompt 到自主循环](#二agent-是什么)
3. [ReAct 循环核心：Thought → Action → Observation](#三react-循环核心)
4. [两种实现对比：手写解析 vs Function Calling](#四两种实现对比)
5. [工具集设计：异构工具的协同](#五工具集设计)
6. [Web 服务与完整演示](#六web-服务与完整演示)
7. [总结与实验](#七总结)
8. [附录 A：概念速查表](#附录-a概念速查表)
9. [附录 B：学生自检参考答案](#附录-b学生自检参考答案)

---

## 一、总纲

### 一句话定义

**ReAct Agent** = 让 LLM 在「思考→行动→观察→再思考」的循环中自主调用工具、直到产出最终答案的系统。本项目的落地场景：A 股年报金融分析。

### 贯穿全文的主线示例：医生问诊 🏥

本文从头到尾用一个场景帮你理解 Agent：

> 你去医院看病，医生不会听你说一句话就开药。他会：**问症状→让你做检查→看化验单→再问→开药方**。
>
> 这个「思考→行动(开检查单)→观察结果(化验单)→再思考→最终行动(开药)」的循环，就是 ReAct 的核心机制。

后面每节的新概念，你都可以回到医生问诊这个场景来理解。

### 核心主线图

```
用户提问："茅台和五粮液2023年毛利率谁高？差多少？"
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                 ReAct 循环（最多 10 步）                  │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐      │
│  │ Thought  │───▶│  Action  │───▶│ Observation  │      │
│  │ 先查代码  │    │ 工具调用  │    │ 返回股票代码  │      │
│  └──────────┘    └──────────┘    └──────┬───────┘      │
│       ▲                                 │              │
│       └────────── 循环 ─────────────────┘              │
│                                                         │
│  Step 1: company_lookup("贵州茅台") → "600519"          │
│  Step 2: financial_indicator("600519") → "毛利率91.96%" │
│  Step 3: calculator("91.96 - 75.79") → 16.17           │
│  Final:  "茅台高出五粮液 16.17 个百分点"                 │
└─────────────────────────────────────────────────────────┘
```

> 🏥 类比：医生问了症状→开化验单→看化验单→再问→开药方。Agent 问了 LLM→调工具→看结果→再问 LLM→最终回答。

### 文件-阶段对照表

| 文件 | 对应 PPT 概念 | 职责 |
|------|-------------|------|
| `src/tools.py` | 执行层 | 5 个工具实现 + TOOLS_SCHEMA |
| `src/react_manual.py` | ReAct 循环★新 | 手写 Prompt 解析版核心循环 |
| `src/react_function_calling.py` | ReAct + Function Call | Function Calling 版 |
| `src/agent.py` | — | CLI 统一入口，`--mode manual/fc` |
| `src/serve.py` | — | FastAPI SSE 流式服务 |
| `src/evaluate.py` | — | 两版对比评估 |
| `index.html` | — | Web UI 可视化 |

### 两种实现的本质区别

| 维度 | 手写 Prompt 解析 | Function Calling API |
|------|-----------------|---------------------|
| Thought 可见性 | ✅ 完全可见，正则提取 | ✅ reasoning_content 可见（DeepSeek） |
| 格式稳定性 | ~95%（偶有漂移） | ~100%（API 保证） |
| 实现方式 | System Prompt 约束 + `stop=["Observation:"]` + 正则 | `tools=TOOLS_SCHEMA` + `tool_calls` |
| 教学价值 ★新 | 高——能看到每一步"怎么想的" | 次之——适合生产 |
| 代码行数 | ~250 行 | ~180 行 |

---

## 二、Agent 是什么

> 📍 位置：主线图的外围——在讲 ReAct 之前，先理解"Agent"这个概念是怎么来的。

### 第 1 层：问题动机

你已经用了好几周的 LLM API 了——`client.chat.completions.create(messages=...)` 一问一答。但现实中的任务不是这样的。

以「茅台和五粮液 2023 年毛利率谁高」为例：

- 模型不认识"茅台"对应的股票代码 → 需要查映射表
- 模型没有毛利率数据 → 需要调 AkShare 接口
- 毛利率要算差值 → 需要计算器

**如果你只能一问一答，你得手动完成上面三步，把中间结果拼成 Prompt 再喂给模型——这不是智能，是人在替模型打工。**

> 🏥 类比：如果医生不能开检查单，只能靠你口述症状来诊断——这叫什么赤脚医生。Agent 给了医生开检查单、看化验单的能力。

### 第 2 层：PPT 定义的演化路径

PPT 把 Agent 拆成了五个能力阶段，每次加上一个新能力：

```
2022 提示词 Agent     = 模型 + System Prompt       （一问一答）
2023 记忆 Agent       = 模型 + 记忆                （跨轮记住上下文）
2023 工具 Agent       = 模型 + 记忆 + 工具          （能查实时数据）
2024 规划 Agent       = 模型 + 记忆 + 工具 + 规划    （自主分解多步任务）
2025 自主 Agent       = 模型 + 记忆 + 工具 + 规划 + 循环  （完整自主执行）
```

**本周项目落地的位置：第四/五阶段**——我们实现了「模型 + 工具 + 规划 + 循环」的完整 Agent。

### 第 3 层：PPT 四层架构在本项目的映射

PPT 讲了 Agent 的四层架构。本项目每一层都有对应的代码：

| PPT 架构层 | 本项目落地代码 | 做了什么 |
|-----------|-------------|---------|
| **感知层** Perception | `react_manual.py:49-74` System Prompt 组装 | 把工具描述、规则、历史对话拼成完整 Prompt |
| **规划层** Planning | `react_manual.py:133-138` LLM 推理 | `client.chat.completions.create()` 让模型决定下一步 |
| **执行层** Execution | `tools.py:201-207` TOOLS_MAP 路由 | `tool_fn(**tool_args)` 执行真实操作 |
| **记忆层** Memory | `react_manual.py:183-187` messages 追加 | 每轮 Observation 追加到对话历史 |

> 🔙 回到主线图：四层架构是 Agent 的"骨架"。下面进入本周核心——ReAct 循环，它让这四层**动起来**。

---

## 三、ReAct 循环核心

> 📍 位置：主线图的正中央——整个项目的心跳。

### 第 1 层：问题动机

**为什么不能一次性调完所有工具？**

因为第 2 步需要第 1 步的结果。

回到茅台毛利率问题：
1. 你不知道茅台的股票代码 → 必须先 `company_lookup`
2. 拿到代码 600519 后才能调 `financial_indicator`
3. 拿到毛利率数字后才能用 `calculator` 算差值

**ReAct 解决了"我不知道下一步做什么，直到看到了上一步的结果"这个问题。**

### 第 2 层：直觉类比

> 🏥 医生问诊的 TAO 循环：
>
> **Thought**（医生思考）：病人说头疼，我需要先量血压、做血常规
> ↓
> **Action**（开检查单）：开化验单，让病人去抽血
> ↓
> **Observation**（看化验单）：血压 145/95，白细胞偏高
> ↓
> **Thought**（再思考）：高血压 + 感染迹象，开降压药 + 抗生素
> ↓
> **Final Answer**（开药方）：处方开出

ReAct 完全是同一套逻辑，只是把"医生"换成"LLM"，把"化验单"换成"工具返回"。

### 第 3 层：代码走读——手写版核心循环

> ⚠️ **这是本周最重要的代码片段，请逐行阅读。**

```python
# react_manual.py — ReAct 核心循环（精简版）

# Step 0: 初始化对话（感知层 + 记忆层）
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},  # 工具描述 + 格式约束
    {"role": "user",   "content": question},        # 用户问题
]

for step in range(1, max_steps + 1):  # 最多 10 步，防止死循环

    # Step 1: 调用 LLM（规划层）
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        stop=["Observation:"],  # ★关键：让模型停在"该执行工具"的地方
    )
    llm_output = response.choices[0].message.content.strip()
    # llm_output 示例:
    # "Thought: 需要先获取茅台股票代码
    #  Action: company_lookup
    #  Action Input: {\"name\": \"贵州茅台\"}"

    # Step 2: 解析 LLM 输出（正则提取 Thought / Action / Action Input）
    parsed = _parse_step(llm_output)

    # 如果模型认为已有足够信息 → 终止循环
    if parsed["type"] == "final":
        yield {"type": "final", "answer": parsed["answer"]}
        return

    # Step 3: 执行工具（执行层）
    tool_name = parsed["action"]           # "company_lookup"
    tool_args = parsed["action_input"]     # {"name": "贵州茅台"}
    tool_fn   = TOOLS_MAP.get(tool_name)   # 从工具注册表取函数
    observation = tool_fn(**tool_args)     # 执行！→ "贵州茅台 的股票代码为 600519"

    # Step 4: 将 Observation 追加到对话历史（记忆层）
    messages.append({"role": "assistant", "content": llm_output})
    messages.append({"role": "user",      "content": f"Observation: {observation}"})
    #                   ↑ 注意：Observation 以 user 角色注入，
    #                   让模型以为"用户告诉了我结果"
    # 然后循环回到 Step 1——模型看到 Observation 后继续推理
```

**关键 shape 追踪**：

```
messages list: [] → [system, user] → [system, user, assistant, user(obs)] → ...
每次循环增加 2 条消息（assistant + Observation），最多 10 轮 = 最多 22 条消息
```

### 第 4 层：设计理由

**为什么用 `stop=["Observation:"]`？**

这是手写版最精妙的设计。System Prompt 要求模型输出：
```
Thought: ...
Action: company_lookup
Action Input: {"name": "贵州茅台"}
```

如果不用 `stop`，模型会自己编造 Observation（幻觉）：
```
Observation: 贵州茅台的股票代码是 600519  ← 模型编的！
```

用了 `stop=["Observation:"]` 后，模型输出到 `Action Input` 就停住了。**Python 代码拿到 Action 去真正执行，再以 `Observation:` 前缀把真实结果注入对话**。这样 Observation 永远是真实数据，不是模型编的。

> ⚠️ **常见误解**：`stop=["Observation:"]` 不是让模型「不输出 Observation」——是让模型在输出 Observation 之前就停住，由代码接管执行。
>
> 💡 我第一次看这段代码时以为 `stop` 只是格式化工具，没意识到它实际上是**幻觉防火墙**——正因为模型停在了 `Action Input` 后面，它永远没机会自己编造 Observation。

> 🔙 回到主线图：现在你看到了 ReAct 循环的核心机制。但同样是 ReAct，PPT 讲了另一种实现方式——Function Calling。下面对比它们。

> 📊 打开 `sequence.html` 查看本章对应的完整请求时序图——从用户提问到 Final Answer 的每一步消息传递。

### 学生自检

关上文档，画出 ReAct 循环的核心流程：Thought → ？→ ？→ 回到 Thought。每一步谁做的？（LLM 还是 Python 代码？）`stop=["Observation:"]` 的作用是什么？

> 🔑 参考答案见附录 B。

---

## 四、两种实现对比

> 📍 位置：主线图中 ReAct 循环的两种"引擎"——同一辆车，两种变速箱。

### 第 1 层：问题动机

上周（Week11）你已经学过 Function Call——模型通过 `tool_calls` 字段返回结构化工具调用指令。**那既然有 Function Call 了，为什么还要手写 Prompt 解析？**

答案：**手写版让你在 Prompt 文本中看到 Thought。Function Call 版通过 API 的 `reasoning_content` 字段也能获取——只是形态不同，一个是纯文本解析，一个是 API 字段。**

> 💡 DeepSeek 模型（包括 v4-flash）默认启用思考模式，`reasoning_content` 字段会携带 CoT 推理链。本项目 FC 版代码已支持提取此字段。

这在教学场景是致命的——你看不到模型的推理过程，怎么知道它"为什么"调这个工具？怎么判断中间推理有没有逻辑错误？

### 第 2 层：直觉类比

> 🏥 两种医生：
>
> **手写版医生**（老中医）：望闻问切每一步都说出来——"舌苔白腻，属寒湿，我先开个祛湿方，三天后再看"→ 你完全理解他的思路。
>
> **FC 版医生**（会写病历的西医）：直接开化验单，同步在病历上写下判断逻辑——效率高，推理过程也能查到，只是不是口头说出来的。
>
> 老中医适合教学（你知道他为什么这样治），西医适合生产（快、标准化、不容易出错）。

### 第 3 层：代码对比

**手写版**——Prompt 约束格式 + 正则解析：

```python
# System Prompt 强制格式
SYSTEM_PROMPT = """
你必须严格按照以下格式输出：
Thought: 分析当前状态...
Action: 工具名称
Action Input: {"参数名": "参数值"}
"""

# 正则提取
_THOUGHT_RE      = re.compile(r"Thought:\s*(.+?)(?=\nAction:|$)", re.DOTALL)
_ACTION_RE       = re.compile(r"Action:\s*(\w+)")
_ACTION_INPUT_RE = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL)

# LLM 调用时加 stop
response = client.chat.completions.create(
    stop=["Observation:"],  # ★ 关键：防止模型自己编造 Observation
)
```

**FC 版**——JSON Schema 注册 + tool_calls：

```python
# 工具以 JSON Schema 注册
TOOLS_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "company_lookup",
        "description": "将公司名称转换为A股股票代码",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "公司名"}
            },
            "required": ["name"]
        }
    }
}]

# LLM 调用时传入 tools
response = client.chat.completions.create(
    tools=TOOLS_SCHEMA,
    tool_choice="auto",  # 模型自己决定是否调工具
)

# 判断：模型要调工具还是直接回答？
msg = response.choices[0].message
if msg.tool_calls:    # 模型返回了工具调用请求
    for tc in msg.tool_calls:
        tool_name = tc.function.name      # "company_lookup"
        tool_args = json.loads(tc.function.arguments)  # {"name": "贵州茅台"}
        observation = TOOLS_MAP[tool_name](**tool_args)
else:                 # 模型直接给了 Final Answer
    yield {"type": "final", "answer": msg.content}
```

### 第 4 层：各有利弊

| 场景 | 用手写版 | 用 FC 版 |
|------|---------|---------|
| 教学演示、理解 Agent 机制 | ✅ Thought 在 Prompt 文本中显式可见 | ✅ Thought 在 `reasoning_content` 字段中（DeepSeek） |
| 生产环境、需要格式稳定 | ❌ ~5% 概率解析失败 | ✅ API 保证格式 |
| 需要精确控制 stop 位置 | ✅ 可定制 | ❌ 依赖 API 实现 |
| 开发效率 | ❌ 多写 ~70 行解析代码 | ✅ 少写代码 |

> 🔙 回到主线图：无论哪种实现，它们调用的工具集是完全一样的。下面看这 5 个工具怎么设计的。

### 学生自检

手写版和 FC 版的核心差异是什么？手写版的 `thought` 从正则解析获取，FC 版的 `thought` 从哪里获取？`stop=["Observation:"]` 在 FC 版需要吗？为什么？

> 🔑 参考答案见附录 B。

---

## 五、工具集设计

> 📍 位置：主线图中的 Action 环节——模型决定调哪个工具、传什么参数。

### 第 1 层：问题动机

Agent 的能力边界由工具集决定。工具太少 → Agent 做不了复杂任务。工具太像 → 模型容易选错。工具参数描述不清晰 → 模型传错参数。

**设计工具集 = 设计 Agent 的"手脚"。**

### 第 2 层：直觉类比

> 🏥 医生的工具箱：
>
> - **听诊器**（company_lookup）：基础检查——每个病人都要先用，把症状对应到身体部位
> - **化验单**（financial_indicator）：结构化数据——血糖 6.2、血脂 2.1，精确可对比
> - **病历本**（rag_search）：非结构化文本——"患者自述三周前开始…"，有丰富描述
> - **血压计**（stock_price）：实时测量——当前状态
> - **计算器**（calculator）：心算不准，用计算器——血糖差了多少？心率变化率是多少？

### 第 3 层：5 工具一览

```python
# tools.py — 工具注册表
TOOLS_MAP = {
    "company_lookup":      tool_company_lookup,       # 公司名 → 股票代码
    "financial_indicator": tool_financial_indicator,  # AkShare 近3年财务指标
    "stock_price":         tool_stock_price,          # AkShare 历史股价
    "rag_search":          tool_rag_search,           # FAISS 年报语义检索
    "calculator":          tool_calculator,           # 受限 eval 计算
}
```

| 工具 | 数据来源 | 类型 | 为什么这样设计 |
|------|---------|------|--------------|
| `company_lookup` | 静态字典 | 映射 | **必须第一步**——没有它，模型会把"茅台"直接传给股价接口报错 |
| `financial_indicator` | AkShare API | 结构化 | 精确数字，跨年可对比。与 rag_search 互补：一个给数字，一个给文字 |
| `stock_price` | AkShare API | 结构化 | 区间涨跌幅需要精确计算，不能靠年报里的文字描述 |
| `rag_search` | FAISS 10353条 | 语义 | 定性内容（风险因素、战略规划、管理层讨论），结构化数据没有的东西 |
| `calculator` | Python eval 沙箱 | 计算 | ★关键设计——LLM 做小数运算容易出错，强制走工具确保准确 |

### 第 4 层：设计原则

**① company_lookup 是"强制第一步"**

不是可选的——System Prompt 里明确写了规则："必须先用 company_lookup 获取股票代码"。这是从踩坑中学到的：早期版本没这个工具，模型直接传"贵州茅台"给 `financial_indicator("贵州茅台")`，AkShare 不认识，报错。

**② rag_search 与 financial_indicator 的张力**

两者都能查到财务数字（年报里有毛利率，AkShare 也有），但：
- `rag_search`：来自 PDF 原文，含上下文解释（"毛利率下降主要因为原材料涨价"）
- `financial_indicator`：裸数字，精度高，跨年对比方便

**Agent 自主选择哪个**——这正是 ReAct 推理价值的体现。如果 Agent 要分析"为什么毛利率下降"，它会选 rag_search；如果要算"三年毛利率变化率"，它会选 financial_indicator + calculator。

**③ calculator 防心算漂移**

```python
# ❌ 如果不强制用 calculator
# 模型会自己算：91.96 - 75.79 = "约16个百分点"
# 实际上 91.96 - 75.79 = 16.17，不是"约16"

# ✅ 强制走工具
# calculator("91.96 - 75.79") → "16.17"
# Agent 拿到精确结果再写入 Final Answer
```

> 🔙 回到主线图：工具集 = Agent 的"手脚"。下面把整个系统包成 Web 服务，让它真正可以被"使用"。

> 📊 打开 `dataflow.html` 查看本章对应的 RAG 数据管线图——从 15 份年报 PDF 到 FAISS 检索的完整数据流。

### 学生自检

为什么 `company_lookup` 必须作为独立的工具而不是写在 System Prompt 里？如果去掉 `calculator`，Agent 会有什么行为变化？

> 🔑 参考答案见附录 B。

---

## 六、Web 服务与完整演示

> 📍 位置：主线图的外层——把 Agent 包成可交互的服务。

### 整体架构（之前用 archify 画的三张图）

```
architecture.html  → 系统组件全景图
sequence.html      → 完整请求时序图
dataflow.html      → RAG 数据管线图
```

### FastAPI SSE 流式服务

```python
# serve.py 核心设计：异步队列实现边思考边推送
async def _stream_react(question, max_steps, mode):
    queue: asyncio.Queue = asyncio.Queue()

    def _worker():
        for step_data in react_run(question, max_steps=max_steps):
            queue.put_nowait(step_data)   # 每步结果立即入队
        queue.put_nowait(_SENTINEL)

    loop.run_in_executor(None, _worker)   # 同步生成器跑在独立线程

    while True:
        step_data = await queue.get()     # 异步等待
        if step_data is _SENTINEL: break
        yield _sse(step_data)             # SSE 推送到前端
```

**为什么用 asyncio.Queue + 独立线程？**

ReAct 循环是同步的 Generator（`yield step_data`），但 FastAPI SSE 需要异步。如果直接在 async 函数里跑同步循环，会阻塞事件循环。解决方案：同步生成器跑在独立线程，通过 `asyncio.Queue` 把结果传给异步 SSE 生成器——真正的"边思考边推送"。

> 🔙 回到主线图：完整系统已经跑通了——用户提问 → Agent 循环 → 流式展示每一步 Thought/Action/Observation → Final Answer。

### 学生自检

`serve.py` 的 lifespan 函数里预加载了 FAISS 索引。如果去掉这行，每次请求会发生什么？为什么不在工具函数 `tool_rag_search` 里做懒加载（`_load_rag()` 已经在工具函数里了，那 lifespan 里的预加载是为了什么）？

> 🔑 参考答案见附录 B。

---

## 七、总结

### 核心知识体系

```
本周你学到的：
  Agent 概念：从「Prompt 驱动的一问一答」到「自主循环的多步推理」
  ReAct 循环：Thought → Action → Observation，推理与行动交织
  两种实现：
    手写 Prompt 解析 — 格式约束 + stop token + 正则，Thought 在文本中可见
    Function Calling — JSON Schema + tool_calls，Thought 在 reasoning_content 中（DeepSeek）
  工具异构设计：映射 + 结构化 + 语义 + 计算 + 实时，各司其职
```

### PPT 核心概念落地对照

| PPT 讲的 | 本项目落的 | 代码位置 |
|---------|----------|---------|
| Agent = 模型+记忆+工具+规划+循环 | ✅ 全部落地 | `react_manual.py` |
| TAO 三元组 | ✅ Thought/Action/Observation 完整可见 | `react_manual.py:116-194` |
| 手写 Prompt 格式约束 | ✅ System Prompt + `stop=["Observation:"]` | `react_manual.py:49-74` |
| Function Calling | ✅ `tools=TOOLS_SCHEMA` + `tool_calls` | `react_function_calling.py:67-121` |
| 执行层工具路由 | ✅ `TOOLS_MAP` 字典路由 | `tools.py:201-207` |
| Format Error Fallback | ✅ `unparseable` 类型 yield 而非崩溃 | `react_manual.py:99,151-157` |
| max_steps 终止保护 | ✅ `max_steps=10` 默认 | `react_manual.py:116` |

### 本周与 PPT 的差异

| PPT 内容 | 本项目未覆盖 | 原因 |
|---------|------------|------|
| OTAC 循环 | ❌ 未实现 Check 步骤 | 当前项目聚焦 ReAct 教学，OTAC 属于进阶 |
| 长期记忆（向量库） | ❌ 只有短期记忆（messages 列表） | 金融分析场景不需要跨会话记忆 |
| Multi-Agent | ❌ 单 Agent | 单 Agent + 多工具已经足够展示核心概念 |
| 任务分解（Planner） | ❌ 未实现 | 当前问题不需要层级分解 |

### 🛠 动手实验

#### 实验 1：去掉 `stop=["Observation:"]`

**目标**：亲眼看到模型自己编造 Observation（幻觉）。

**步骤**：
1. 打开 `src/react_manual.py`，找到第 137 行
2. 把 `stop=["Observation:"]` 改为 `stop=None`
3. 运行 `python src/agent.py --mode manual --question "茅台2023年毛利率是多少？"`
4. 观察输出——模型是否自己编造了 Observation？

**预期**：模型会在 Thought/Action/Action Input 之后自己补上 `Observation: ...`——这个 Observation 是编的，不是真实数据。

**恢复**：把 `stop` 改回 `["Observation:"]`。

#### 实验 2：切换 DeepSeek 模型

**目标**：对比不同 LLM 的格式稳定性。

**步骤**：
1. 确保 `DEEPSEEK_API_KEY` 环境变量已设置
2. 打开 `src/react_manual.py`，注释第 36-40 行（DashScope），取消注释第 41-45 行（DeepSeek）
3. 运行 `python src/agent.py --mode manual --question "海康威视2023年年报提到了哪些风险？"`
4. 观察解析是否成功（有无 `unparseable` 错误）

**预期**：DeepSeek 的格式稳定性可能略差于 qwen-max，但功能正常。

**恢复**：换回 DashScope 配置。

#### 实验 3：去掉 `company_lookup` 工具

**目标**：观察 Agent 如何处理"必需的中间步骤缺失"。

**步骤**：
1. 打开 `src/tools.py`，把 `"company_lookup"` 从 `TOOLS_MAP` 中注释掉
2. 同时把 `SYSTEM_PROMPT` 中关于 `company_lookup` 的描述删掉
3. 运行 `python src/agent.py --mode manual --question "茅台2023年营收是多少？"`
4. 观察 Agent 的行为——它是直接传"茅台"给 `financial_indicator` 了吗？报了什么错？

**预期**：Agent 可能直接把"茅台"传给 `financial_indicator("茅台")`，AkShare 报错（不认识这个代码）。Agent 可能重试或放弃。

**恢复**：取消注释，恢复 System Prompt。

---

## 附录 A：概念速查表

| 概念 | 英文 | 分级 | 一句话 | 位置 |
|------|------|------|--------|------|
| **Agent** | Agent | ★新 核心 | 能自主调用工具完成多步任务的 LLM 系统 | 第二节 |
| **ReAct** | Reasoning+Acting | ★新 核心 | Thought→Action→Observation 循环，推理与行动交织 | 第三节 |
| **TAO 三元组** | TAO | ★新 核心 | Thought(思考)+Action(行动)+Observation(观察) | 第三节 |
| **OTAC** | Observe-Think-Act-Check | ★新 辅助 | ReAct + Check 验证步骤，出现错误可回退 | PPT 第四部分 |
| **四层架构** | 4-Layer Architecture | ★新 辅助 | 感知→规划→执行→记忆 | 第二节 |
| **手写 Prompt 解析** | Manual Prompt Parsing | ★新 核心 | System Prompt 约束格式 + 正则提取 TAO | 第三/四节 |
| **Function Calling** | Function Calling | 📎 Week11 | 模型通过 JSON Schema 注册工具，返回 tool_calls | 第四节 |
| **stop token** | Stop Token | ★新 辅助 | 让 LLM 在指定文本前停止生成，防止幻觉 | 第三节 |
| **tool_calls** | Tool Calls | 📎 Week11 | FC 版模型返回的工具调用指令字段 | 第四节 |
| **SSE** | Server-Sent Events | 📎 Week10 | HTTP 流式推送，text/event-stream | 第六节 |
| **FAISS** | FAISS | 📎 Week08/10 | 向量相似度检索引擎 | 第五节 |
| **幻觉防火墙** | Hallucination Firewall | ★新 辅助 | stop token + 代码接管执行，防止模型编造数据 | 第三节 |
| **工具异构性** | Tool Heterogeneity | ★新 辅助 | 不同工具用不同数据源（API/向量库/字典），Agent 自主选择 | 第五节 |
| **max_steps** | Max Steps | ★新 辅助 | 循环最大步数限制，防止死循环 | 第三节 |

## 附录 B：学生自检参考答案

### 第三节自检：ReAct 循环流程

**画出流程**：Thought(LLM) → Action(LLM 输出指令，Python 解析) → Observation(Python 执行工具，真实数据) → 回到 Thought(LLM 看到 Observation 后继续推理)。

**`stop=["Observation:"]` 的作用**：防止 LLM 自己编造 Observation。让 LLM 在 "Action Input" 之后停住，由 Python 代码真正执行工具拿到真实结果，再以 "Observation:" 前缀注入对话。这是手写版的**幻觉防火墙**——Observation 永远是真实数据，不是模型编的。

---

### 第四节自检：手写 vs FC

**核心差异**：
- 手写版：System Prompt 强制格式 → 模型输出纯文本 → Python 正则解析。Thought 从正则匹配的文本中获取。
- FC 版：JSON Schema 注册工具 → 模型返回 `tool_calls` 结构体。Thought 从 `reasoning_content`（DeepSeek）或 `msg.content` 字段获取。

**为什么手写版 `thought` 有内容**：因为 System Prompt 要求模型输出 `Thought: ...`，Python 用正则提取出来。

**FC 版 `thought` 从哪里获取**：DeepSeek 模型默认启用思考模式，API 返回的 `reasoning_content` 字段包含了 CoT 推理链。代码通过 `getattr(msg, "reasoning_content", None) or msg.content` 提取。

**`stop=["Observation:"]` 在 FC 版需要吗？**：不需要。FC 版不靠文本格式控制——模型通过 `tool_calls` 字段返回工具调用，`finish_reason="tool_calls"` 表示需要执行工具。没有"模型自己编造 Observation"的风险，因为工具结果是代码注入的 `role: "tool"` 消息。

---

### 第五节自检：工具设计

**为什么 `company_lookup` 必须是独立工具**：如果写在 System Prompt 里（如"茅台=600519"），只能覆盖已知公司，不具备泛化能力。作为工具，模型可以在 Thought 里明确推理"我需要先查代码"，让 ReAct 循环更自然。更重要的是——如果未来知识库扩展到 500 家公司，改字典就行，不用改 Prompt。

**去掉 `calculator` 的行为变化**：LLM 会自己心算。对于简单计算（91.96-75.79=16.17）大概率正确，但对于多位小数、百分比换算、CAGR 复合增长等复杂计算，LLM 的心算错误率显著上升。计算器工具的另一个价值是**让计算步骤可见**——你可以验证每一步的数值是否正确。

---

### 第六节自检：Web 服务

**如果去掉 lifespan 预加载**：FAISS 索引（41MB）会在第一次 `tool_rag_search` 调用时才加载（懒加载）。这对首次请求的用户来说是额外的 ~2-3 秒等待。lifespan 预加载把这份开销放在了服务启动时——之后的每次请求都是即时响应。

**为什么不只靠懒加载**：两者不冲突。`_load_rag()` 内部的懒加载（`if _faiss_index is not None: return`）已经保证了只加载一次。lifespan 的预加载只是在"服务启动时"触发第一次加载，而不是等到"第一个用户请求时"——本质上是把延迟从用户身上转移到运维身上。

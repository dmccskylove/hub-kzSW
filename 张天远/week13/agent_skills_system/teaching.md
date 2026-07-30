# Agent 记忆系统 + Skills 渐进式加载 —— 从零入门

> 📍 面向读者：学过 Python 基础、了解 LLM 基本概念、没碰过 Agent 开发

---

## 前置要求

| 已知 | 未知 | 学完能做什么 |
|------|------|------------|
| Python 基础语法、HTTP 请求 | Agent 架构、ReAct 循环、Function Calling、Context 管理 | 理解 Agent 核心机制，能自己实现带记忆和工具调用的 LLM Agent |

---

## 一、总纲：一张图建立全部心智模型

### 一句话定义

这个项目是一个 **LLM Agent**：你发消息给它，它不是简单回复——而是加载记忆、匹配合适的技能、调用工具（读写文件/执行命令），在"思考→行动→观察"的循环中完成任务。

> 🏠 **贯穿全文的主线示例**：把它想象成一个新来的助理。第一天你告诉它"我叫张三，喜欢 TypeScript"——它记住了（Memory Flush）。第二天你说"帮我做英语闪卡"——它知道闪卡怎么做（Skill），并且真的能写 HTML 文件出来（工具调用）。

### 核心主线图

```
用户消息
  │
  ▼
[Step 1] Skill 匹配 ─── 命中 Skill？→ 加载完整定义（渐进式披露）
  │
  ▼
[Step 2] Context 组装 ─── 记忆(MD文件) + Skill 定义 + 对话历史 → System Prompt
  │
  ▼
[Step 3] 预加载 ─── 服务器自动读 PROJECT.md + 目录结构，注入 Prompt（不让 LLM 自己找）
  │
  ▼
[Step 4] ReAct 循环 ─── LLM 思考 → 有工具要调？→ 执行 → 观察结果 → 回到思考
  │                        │
  │                        └── 没有工具要调 → 输出最终答案
  ▼
[Step 5] 回复用户 + 释放 Skill + 自动 Flush 记忆
```

5 步，每一步对应后续一个章节。**每个章节标题里都有 📍 锚点，帮你时刻知道自己在哪里。**

### 文件-阶段对照表

| 步骤 | 核心文件 | 一句话 |
|------|---------|--------|
| ⓪ 配置 | `memory/SOUL.md` `AGENTS.md` `USER.md` `MEMORY.md` | Agent 人格、规则、用户画像、长期记忆 |
| ① Skill 匹配 | `src/skill_loader.py` | 触发词命中 → 加载 Skill |
| ② Context 组装 | `src/context_engine.py` `src/memory_loader.py` | 记忆 + Skill + 历史 → System Prompt |
| ③ 预加载 | `src/server.py`（`_preload_project_context`） | 自动读 PROJECT.md 注入 |
| ④ ReAct 循环 | `src/server.py` `src/tool_executor.py` `src/llm_config.py` | "思考→行动→观察" 直到完成 |
| ⑤ 持久化 | `src/memory_flush.py` `src/session_db.py` | 提取关键信息写入 MD 文件 |

---

## 二、步骤 ①：Skill 匹配 —— 渐进式披露

> 📍 位置：主线图 Step 1。这一步决定"用哪个技能来处理用户的请求"。

### 第 1 层 —— 解决什么问题？

LLM 默认只能聊天。要让它"写教案"或"做闪卡"，需要把操作流程告诉它。但如果把所有技能定义都塞进 Prompt，65%+ 的 Context 会被当前用不上的内容占满。

### 第 2 层 —— 用类比建立直觉

就像你不会把整本词典带进考场——你只带那一页小抄。Agent 也一样：平时只记住"有哪些技能"，用时才翻出详细说明。

```
常驻层（始终在 Prompt 里）          触发层（用户说了触发词才加载）
skills/index.md                     skills/teaching-project-deepdive.md
~200 tokens                          78KB / 1025 行
"闪卡、教案、代码审查..."            （完整的工作流、规则、模板）
```

### 第 3 层 —— 带标注的代码走读

```python
# src/skill_loader.py — 核心类
class SkillLoader:
    def match(self, user_input: str) -> list[SkillMatch]:
        """触发词匹配"""
        user_lower = user_input.lower()                # "帮我写教案" → "帮我写教案"
        for skill in self._skills.values():            # 遍历所有已注册 Skill
            matched = [t for t in skill.triggers       # skill.triggers = ["写教案","教程",...]
                       if t.lower() in user_lower]     # "教案" in "帮我写教案" → True!
            if matched:
                confidence = len(matched) / len(skill.triggers)  # 命中数/总数 = 置信度
                # 多触发词命中 → +0.2 加成
```

> ⚠️ **常见误解**：触发匹配不是 AI 语义理解，是**子串匹配**。"帮我写一份教程"能匹配到"教程"，匹配不到"做教程"——所以我们把常用短词（"教程""教案"）都加进触发词列表。

### 第 4 层 —— 设计理由

为什么不直接用 LLM 判断"用户是不是想做闪卡"？（1）慢——每次多一次 API 调用；（2）贵——判断一次消耗 token。子串匹配零成本、毫秒级，而且触发词列表由人维护，可预期、可调试。

### 学生自检

关上文档，能不能画出"用户说'做个闪卡' → Skill 匹配 → 加载定义"的数据流？如果画不出来，回本节重读——这张图是整个 Agent 的入口。

---

## 三、步骤 ②：Context 组装 —— LLM 看到的"世界"

> 📍 位置：主线图 Step 2。决定 LLM 在回复之前"知道什么"。

### 第 1 层 —— 解决什么问题？

LLM 本身是**无状态**的。每次 API 调用都是一张白纸。你需要在这张白纸上写好：你是谁、用户是谁、有什么技能可用、之前聊了什么。

### 第 2 层 —— 用类比建立直觉

把 LLM 想象成一个失忆症患者——每次醒来都不知道自己是谁。`Context 组装` 就是在他醒来时递给他一张纸条：

```
你是灵枢，一个专业编程助手。
用户叫张三，喜欢 TypeScript。
现在有 2 个技能可用：闪卡、教案。
以下是你们之前的 3 轮对话...
```

### 第 3 层 —— 带标注的代码走读

```python
# src/context_engine.py
class ContextEngine:
    def assemble(self, messages: list[dict]) -> AssembledContext:
        mem = self.memory_loader.load_all()   # 读 SOUL/USER/MEMORY/AGENTS.md
        system_parts = [mem.assemble()]       # 拼成 "## Agent人格\n...## 用户画像\n..."
        system_parts.append(self.skill_loader.index_prompt)  # "可用 Skills: flash-card, teaching..."
        if self.skill_loader._active_skill:                  # 如果有命中的 Skill
            system_parts.append(self.skill_loader.active_skill_prompt)  # 加载完整定义
        system_prompt = "\n\n".join(system_parts)  # 合并 → 发给 LLM
```

### 第 4 层 —— 设计理由

为什么用 Markdown 文件而不是数据库？因为 LLM 原生理解 Markdown——不需要额外的序列化/反序列化。用户也可以直接打开 `USER.md` 编辑，不需要 SQL。

### 学生自检

Context 组装时，哪些内容是"每次都必须加载"的？哪些是"按需加载"的？标准答案：SOUL/AGENTS 永远加载（人格和边界不能丢），Skill 按触发加载，USER/MEMORY 每次加载（但内容少）。

---

## 四、步骤 ③：预加载上下文 —— 不让 LLM"找"，让它"写"

> 📍 位置：主线图 Step 3。这是一个工程优化，解决"LLM 花 18 轮读文件、一字不写"的问题。

### 第 1 层 —— 解决什么问题？

ReAct 循环给 LLM 提供了 `read_file`、`list_files` 等工具。LLM 拿到教案 Skill 后，会忠实地执行"阶段1：研究吸收"——逐文件阅读，18 轮还没开始写。

### 第 2 层 —— 用类比建立直觉

你让助理写项目总结。聪明的做法是**直接把项目文档、目录结构打印好放他桌上**，而不是让他自己翻遍每个文件夹。

### 第 3 层 —— 代码

```python
# src/server.py — ReAct 循环前自动执行
def _preload_project_context() -> str:
    parts = []
    # 1. 读 PROJECT.md（核心架构文档，8000字）
    with open("PROJECT.md") as f:
        parts.append(f.read()[:8000])
    # 2. 列目录结构
    for item in os.listdir(root):
        parts.append(f"  {item}/" if is_dir else f"  {item}")
    # 3. 列源文件
    parts.append("src/server.py  src/skill_loader.py  ...")
    return "\n\n".join(parts)  # → 注入 System Prompt
```

### 第 4 层 —— 设计理由

这是学习 Hermes 的关键经验：**Context 应该在 LLM 调用之前就组装好，而不是让 LLM 在循环中自己构建。** Hermes 在对话前就把 MEMORY.md、SOUL.md、Skills 全部注入——Agent 不需要"发现"这些信息，直接开始工作。

---

## 五、步骤 ④：ReAct 循环 —— Agent 的"大脑"

> 📍 位置：主线图 Step 4。这是整个系统的核心引擎。

### 第 1 层 —— 解决什么问题？

聊天模型只会"说"，不会"做"。ReAct 循环让模型在"思考 → 行动 → 观察"中反复迭代，直到任务完成。

### 第 2 层 —— 用类比建立直觉

你让助理"统计这个月销售额"。他不会直接报数字——而是：打开 Excel → 看数据 → 发现缺 3 月数据 → 打电话问财务 → 拿到数据 → 更新 Excel → 报数字。这个过程就是 ReAct。

### 第 3 层 —— 带标注的代码走读

```python
# src/server.py — ReAct 循环核心
tools = tool_exec.get_schemas()  # [write_file, read_file, list_files, shell_exec]
messages = history.copy()        # 对话历史
turn = 0

while turn < MAX_REACT_TURNS:           # 最多 12 轮
    turn += 1
    result = chat_with_tools(           # ★ 调用 LLM，传入工具定义
        messages,
        system=ctx.system_prompt,       # ← 第2步组装的 Context
        tools=tools                     # ← "你可以用这些工具"
    )

    if result.tool_calls:               # LLM 说"我需要调工具"
        for tc in result.tool_calls:    # 可能一次调多个
            obs = tool_exec.execute(    # ★ 真正执行工具
                tc["name"], tc["arguments"]
            )
            messages.append({           # 工具结果追加到对话历史
                "role": "tool",
                "content": obs          # "文件写入成功: thrill.html (3280 bytes)"
            })

    elif result.content:                # LLM 说"我完成了"
        full_reply = result.content     # → 这就是最终回复
        break
```

关键：`reasoning_content` 的处理。

```python
# DeepSeek v4-flash 的思考过程必须回传，否则下一轮 400 报错
if result.reasoning_content:                              # ★
    asst_msg["reasoning_content"] = result.reasoning_content  # 原样回传
```

> ⚠️ **常见误解**：ReAct 循环不需要 AI 判断"是否该退出"——退出条件是纯机制判断：LLM 返回了文本内容（不是工具调用）= 它认为任务完成了。

### 第 4 层 —— 设计理由

为什么不用流式 API 做 ReAct？工具调用需要解析完整的 JSON——流式 API 的增量 token 无法拼出完整的 `tool_calls`。所以循环内用非流式 `chat_with_tools`，只在最终回复时流式输出。

### 学生自检

"如果 LLM 在第一轮就返回了 content（没有 tool_calls），ReAct 循环会执行几次？" 答案：1 次——`elif result.content` 直接 break。

---

## 六、步骤 ④ 续：工具执行器 —— Agent 的"双手"

### 第 1 层 —— 解决什么问题？

LLM 输出的工具调用只是 JSON 文本——`{"name": "write_file", "arguments": {...}}`。需要有人真正执行它。

### 第 2 层 —— 用类比建立直觉

LLM 是老板，说"把这个文件存到桌面"。工具执行器是秘书——打开文件夹、写入内容、告诉老板"存好了"。

### 第 3 层 —— 带标注的代码走读

```python
# src/tool_executor.py — 4 个内置工具
class ToolExecutor:
    def _register_builtins(self):
        # 1. write_file — 写文件（闪卡输出 HTML、教案输出 MD）
        self.register(ToolDef(
            name="write_file",
            parameters={"path": "文件路径", "content": "内容"},
            execute=self._write_file,
        ))
        # 2. read_file — 读文件（3000 字自动截断）
        # 3. list_files — 列目录（纯 Python，跨平台）
        # 4. shell_exec — Windows→PowerShell, Linux→bash
```

关键细节：`shell_exec` 的跨平台处理：

```python
def _shell_exec(self, params):
    if os.name == "nt":                                    # Windows
        subprocess.run(["powershell", "-Command", cmd])   # → PowerShell
    else:                                                   # Linux/Mac
        subprocess.run(cmd, shell=True)                    # → bash
```

> ⚠️ **踩坑**：最初用 `shell=True` 默认调 `cmd.exe`，导致 `ls` 和 `Get-ChildItem` 都失败，白白浪费了 3 轮 ReAct。

---

## 七、步骤 ⑤：Memory Flush —— 对话结束后的记忆提取

> 📍 位置：主线图 Step 5。让 Agent 真正"记住"你。

### 第 1 层 —— 解决什么问题？

LLM 每次调用都是无状态的。下次对话它不会记得你今天说了什么。Memory Flush 在对话结束后自动提取关键信息写入文件。

### 第 2 层 —— 用类比建立直觉

每次会议后，秘书把重点整理成会议纪要（MEMORY.md），把你提到的偏好更新到档案（USER.md）。下次开会前，秘书先把纪要和档案放你桌上——你就像从来没离开过一样。

### 第 3 层 —— 代码

```python
# src/memory_flush.py — Two-Pass 设计
def flush(self, messages):
    # Pass 1: 提取用户信息 → USER.md
    #   对话 → LLM → JSON [{field:"称呼", value:"张三", confidence:0.9}]
    #   → 写入 USER.md

    # Pass 2: 提取记忆条目 → MEMORY.md
    #   对话 → LLM → JSON [{category:"preference", title:"喜欢Rust", content:"..."}]
    #   → 追加 MEMORY.md
```

为什么分两次调 LLM？如果一次让它同时提取用户信息 + 记忆条目，LLM 容易混淆任务边界——要么漏掉信息，要么格式混乱。Two-Pass 每次只做一件事，稳定得多。

### 第 4 层 —— 设计理由

为什么用 LLM 提取而不是写正则规则？用户不会说"我的偏好是咖啡"，会说"最近天气热，每天来一杯美式"。LLM 能识别隐式偏好——规则只能处理显式格式，覆盖不到 30% 的真实对话。

---

## 八、三个最有价值的踩坑

### 坑 1：Prompt 里的花括号被 `.format()` 吃了

Flush 的 Prompt 里有 JSON 示例 `{"field": "字段名"}`。Python 的 `.format()` 把 `{field}` 当占位符，找不到就抛 KeyError。**修法**：`{{"field": "字段名"}}` 双花括号转义。**教训**：任何含花括号的模板字符串用 `.format()` 都要检查——f-string 也一样。

### 坑 2：DeepSeek v4-flash 的 `reasoning_content` 必须回传

v4-flash 自带思考模式（CoT），API 返回的 `reasoning_content` 如果不在下一轮原样回传，直接 400。**修法**：在 `ToolCallResult` 中捕获 `reasoning_content`，构造 assistant 消息时附上。

### 坑 3：ReAct 循环中 LLM 逐文件探索，18 轮还没开始写

LLM 忠实执行 Skill 的"阶段1：研究吸收"——逐个文件读，耗尽轮次。**修法**：Step 4.5 预加载上下文——在 ReAct 启动前就把 PROJECT.md 注入 Prompt，不让 LLM 自己找。**教训**：Context 应该在 LLM 调用前组装好，这是 Hermes 的核心经验。

---

## 九、概念速查表

| 概念 | 英文 | 一句话 | 位置 |
|------|------|--------|------|
| 渐进式披露 | Progressive Disclosure | 平时只加载 Skill 索引，用时才加载完整定义 | `src/skill_loader.py` |
| ReAct 循环 | ReAct Loop | 思考→行动→观察，反复直到任务完成 | `src/server.py` |
| Function Calling | Tool Use | LLM 输出 JSON 指定要调的工具和参数 | `src/llm_config.py:chat_with_tools` |
| Context 组装 | Context Assembly | 记忆+Skill+历史→System Prompt | `src/context_engine.py` |
| Memory Flush | Memory Extraction | 对话结束 LLM 提取关键信息→写文件 | `src/memory_flush.py` |
| reasoning_content | Chain of Thought | DeepSeek 的思考过程，多轮必须回传 | `src/llm_config.py:ToolCallResult` |

---

## 十、一句话总结

这个项目把 LLM 从"聊天机器人"升级为"能做事的 Agent"——它有记忆、会选技能、能调工具，并且通过渐进式披露在 1M Context 里高效运转。理解了这个项目，你就理解了 Hermes、Claude Code、Cursor 这类 Agent 产品的核心机制。

> 🔙 回到主线图：整个管线从用户消息出发，经 Skill 匹配 → Context 组装 → 预加载 → ReAct 循环 → 持久化，5 步形成一个完整的"感知→决策→执行→记忆"闭环。这就是一个 Agent 的骨架。

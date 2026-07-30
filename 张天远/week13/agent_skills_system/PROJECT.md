# Week13 作业：Agent 记忆系统 + Skills 渐进式加载 + ReAct 工具调用

> 设计文档 · 踩坑记录 · 技术亮点 · 最终版

---

## 一、项目目标

实现一个 LLM Agent，具备三大核心能力：

1. **多层记忆**（参考 Hermes Agent）——跨会话记住用户信息，对话结束自动提取持久化
2. **Skills 渐进式加载**——按需加载技能定义，任务完成后释放 Context
3. **ReAct 循环 + Function Calling**——LLM 自主调用工具（读写文件、执行命令），真正完成任务

交付形态：**前后端分离**（FastAPI + SSE 后端，CLI 前端），模型 `deepseek-v4-flash`，1M Context。

---

## 二、架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────┐
│                   CLI 前端 (cli.py)                │
│          HTTP/SSE 消费，--port 可配                │
└──────────────────────┬───────────────────────────┘
                       │ HTTP + SSE
┌──────────────────────▼───────────────────────────┐
│              FastAPI 后端 (server.py)              │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ skill_loader │  │context_engine│               │
│  │ 渐进式加载 ★  │  │ Context 组装  │               │
│  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐               │
│  │  预加载上下文  │  │ ReAct 循环   │               │
│  │ PROJECT.md等  │  │ (最多12轮)   │               │
│  └──────────────┘  └──────┬───────┘               │
│         │                 │                       │
│  ┌──────▼─────────────────▼───────┐               │
│  │   LLM (deepseek-v4-flash)       │               │
│  │   + 4 个工具                    │               │
│  └──────┬─────────────────┬───────┘               │
│         │                 │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐               │
│  │ tool_executor│  │ memory_flush │               │
│  │ write/read/  │  │ LLM提取写入  │               │
│  │ list/shell   │  │ USER/MEMORY  │               │
│  └──────────────┘  └──────────────┘               │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  session_db  │  │memory_loader │               │
│  │  SQLite历史  │  │ MD文件记忆   │               │
│  └──────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────┘
```

### 2.2 Skills 渐进式披露

```
常驻层                  触发层                   执行层
skills/index.md         匹配触发条件             完整 SKILL.md
~200 tokens             命中后加载定义           flash-card: ~1K tokens
始终注入 System Prompt  显示匹配置信度           teaching: 78KB (1025行)
                                                任务完成后释放
```

### 2.3 ReAct 循环 + Function Calling

```
用户输入 → Skill匹配 → 预加载Context → ReAct循环 ─┐
  ↑                                                  │
  │    ┌─ 有tool_calls → 执行工具 → 观察结果 → 继续 ─┤
  │    │                                              │
  └────┼─ 有content → 最终回答 → 释放Skill → done    │
       │                                              │
       └─ 空回复 → 退出                               │
                                             最多12轮
```

**可用工具（4个）**：

| 工具 | 用途 | 跨平台 |
|------|------|--------|
| `write_file` | 写文件（HTML、脚本、教案） | ✅ |
| `read_file` | 读文件内容（自动截断>3000字） | ✅ |
| `list_files` | 列目录（避免 Windows/Linux 命令差异） | ✅ |
| `shell_exec` | 执行命令（Windows→PowerShell, Linux→bash） | ✅ |

### 2.4 核心优化：预加载上下文（Step 4.5）

**问题**：LLM 在 ReAct 循环中逐文件探索，18轮还在读文件，从未开始写。

**根因**：Hermes 写教案时是一次性规划+输出（Context 已包含项目全貌），而 ReAct 循环是"读→执行→观察→再读"的低效模式。

**修复**：在 ReAct 启动前，服务器自动读取 PROJECT.md + 目录结构 + 源文件列表，注入 System Prompt。LLM 拿到预加载的上下文后直接开始写，不绕弯。

```
Step 4: Context 组装（记忆+Skills+历史）
Step 4.5: 预加载项目上下文（PROJECT.md + 目录 + 源文件列表）★
Step 5: ReAct 循环（LLM 已有全貌，最多12轮）
```

### 2.5 Context 窗口保护

| 配置项 | 值 | 作用 |
|--------|-----|------|
| `MAX_REACT_TURNS` | 12 | 防止无限循环 |
| `MAX_CONTEXT_CHARS` | 60,000 | 超阈值自动裁剪旧轮次，保留最近8条+所有用户消息 |

### 2.6 记忆模型（参考 Hermes）

| 层级 | 内容 | 存储 | 加载时机 |
|------|------|------|---------|
| **SOUL.md** | Agent 人格 | 文件 | 永远注入 System Prompt |
| **AGENTS.md** | 操作规范（含 ReAct 约束） | 文件 | 永远注入 |
| **USER.md** | 用户画像 | 文件 | 每次会话注入，Flush 自动更新 |
| **MEMORY.md** | 长期记忆 | 文件 | 每次会话注入，Flush 自动追加 |
| **短期记忆** | 对话历史 | SQLite | 当前会话全部注入 |
| **Memory Flush** | 对话→LLM→提取→文件 | LLM 驱动 | 手动 / 20条自动 |

---

## 三、关键模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **Skill 渐进式加载 ★** | `src/skill_loader.py` | 索引常驻→触发匹配→加载→释放 |
| **Context 组装** | `src/context_engine.py` | 记忆+Skills+历史→完整 System Prompt |
| **ReAct 循环** | `src/server.py` | 工具调度、异常保护、Context 裁剪 |
| **工具执行器** | `src/tool_executor.py` | 4 个工具的注册与执行 |
| **Memory Flush** | `src/memory_flush.py` | Two-Pass LLM 提取→写入文件 |
| **LLM 配置** | `src/llm_config.py` | `chat_with_tools` 支持 Function Calling |
| **会话管理** | `src/session_db.py` | SQLite 存储会话历史 |
| **CLI 前端** | `src/cli.py` | SSE 消费、命令解析、--port 可配 |

---

## 四、踩坑记录

### 坑 1：Prompt 中的花括号被 `.format()` 吃掉

**现象**：Memory Flush 一直报 `KeyError: '"field"'`。

**根因**：Prompt 中 `{"field": "字段名"}` 被 `.format()` 当成占位符。

**修复**：`{{"field": "字段名"}}` 双花括号转义。

### 坑 2：`__pycache__` 导致代码修改不生效

**现象**：多次 patch 后服务行为不变。**修复**：`rm -rf src/__pycache__ && find . -name "*.pyc" -delete` + 杀进程 + 重启，三步缺一不可。

### 坑 3：端口被僵尸 uvicorn 进程占死

**现象**：`taskkill` 杀不掉。**修复**：`powershell "Stop-Process -Id <pid> -Force"`。

### 坑 4：sandbox 无环境变量

**现象**：沙箱里 `DEEPSEEK_API_KEY not set`。**修复**：通过 `subprocess` 读注册表注入。

### 坑 5：触发词精度不足

**现象**："写一份Rust教程" 没匹配。**修复**：增加 `"教程"` 作为独立触发词。

### 坑 6：ReAct 循环无限探索文件

**现象**：LLM 花 18 轮读文件，一字未写，API 超时崩溃。

**根因**：Skill 的"阶段1：研究吸收" + ReAct 逐文件循环 = 灾难。Hermes 写教案是一次性规划+输出，不是文件级增量探索。

**修复**：(1) Step 4.5 预加载上下文；(2) AGENTS.md 加 ReAct 约束（探索 ≤5 轮）；(3) try/except 保护防止服务崩溃。

### 坑 7：shell_exec 跨平台

**现象**：`ls` 在 Windows 失败，`Get-ChildItem` 在 cmd.exe 下失败。

**修复**：Windows 自动切 `powershell -Command`；新增 `list_files` 纯 Python 工具避免命令差异。

---

## 五、技术亮点

### 5.1 Context 可视化管道

前端实时展示完整 SSE 事件流：
```
🔍 匹配 → 🔧 命中 → 📥 加载 → 📦 预加载 → 🧠 组装 → 🔄 ReAct → 🛠️ 工具 → 👁️ 观察 → 💬 回复 → 📤 释放
```

### 5.2 兼容多种 LLM 输出格式

`_extract_json()` 支持代码块、数组、单对象、中英文 key，正则分层尝试。

### 5.3 轻量 Frontmatter 解析器

自行实现，零依赖。支持字符串值、内联数组、多行列表。

### 5.4 前后端分离 + 可配端口

后端 `run_server.ps1 -Port 8080`，CLI `run_cli.ps1 -Port 8080`，全部使用相对路径。

---

## 六、Skills

| Skill | 来源 | 大小 | 形态 |
|-------|------|------|------|
| `flash-card` | 课程课件 | ~3K chars + 脚本+数据 | 代码工具型 |
| `teaching-project-deepdive` | Hermes 原版 | 78KB / 1025行 | 工作流+知识复合型 |

添加新 Skill：创建 `skills/<name>.md`（含 frontmatter 的 triggers）+ 在 `skills/index.md` 加一行即可。

---

## 七、启动指南

```powershell
# 1. 设置 API Key（从注册表读取或手动设置）
$env:DEEPSEEK_API_KEY=*** 'HKCU:\Environment' -Name DEEPSEEK_API_KEY).DEEPSEEK_API_KEY

# 2. 安装依赖
pip install httpx fastapi uvicorn pydantic openai

# 3. 启动后端（终端1）
cd E:\npl\workspaces\npl_tran\agent_skills_system
.\run_server.ps1

# 4. 启动 CLI（终端2）
.\run_cli.ps1
```

CLI 命令：`/status` `/skills` `/flush` `/new` `/help` `/exit`

---

*项目位置：`E:\npl\workspaces\npl_tran\agent_skills_system`*  
*最终验证：2026-07-31 · deepseek-v4-flash · ReAct + Function Calling 全流程通过*  
*Skills 验证：flash-card 成功生成 HTML，teaching 成功输出教案*

# ARCHITECTURE.md — Subagent 并行执行系统（Week15 作业）

> 基于 Week13 agent_skills_system 扩展：主 agent 自主拆分任务 → 派发多个 subagent 并行执行 → 回收汇总
> 范式对应 PPT 6.3 **Orchestrator-Workers（动态）**：主管派发 + 回收合成，拓扑在运行时生长

---

## 1. 项目定位

**场景**：用户给主 agent 一个含多个独立工作项的任务（如"生成一个项目，含 3 个文件"），
主 agent 自主决定是否调用 `dispatch_subagents` 拆分并行，收齐后综合成最终交付。

**核心设计**（与老师示例 `market_research_subagents` 对齐）：
- 主 agent = 原有 ReAct+FC 循环，工具集 = 4 个基础工具 + **`dispatch_subagents`**（LLM 自主决策用哪个）
- subagent = 轻量 ReAct 循环（**无记忆/skills/派发能力**），工具集 = 4 个基础工具（**禁 dispatch，防递归**）
- 多个 subagent 用 `ThreadPoolExecutor` **并行**执行（fan-out），结果截短回灌主 agent（fan-in）
- 事件桥接：subagent 运行在线程池 → 事件入 thread-safe `queue.Queue` → SSE 主循环 drain 推送
- 可视化：左拓扑图（派发时动态生长 subagent 节点）+ 右侧实时过程流（可点节点过滤）

## 2. 整体流水线

```
用户问题
   ↓
主 agent ReAct 循环（5 工具: write/read/list/shell + dispatch_subagents）
   ├─ 单任务 → 直接自己写/做 → Final Answer
   └─ 多独立工作项 → dispatch_subagents(["子任务1", "子任务2", ...])
                        ↓ ThreadPoolExecutor 并行
              ┌─ subagent0 ReAct(4工具, 无dispatch) ─┐
              ├─ subagent1 ReAct(4工具, 无dispatch) ─┤ 并行
              └─ subagent2 ReAct(4工具, 无dispatch) ─┘
                        ↓ 汇总（各结果截短 500 字 + 并行统计）
              主 agent 综合 → Final Answer
```

模块：`tool_executor.py`(工具注册+dispatch钩子) → `subagent.py`(SubAgent+并行+事件) → `server.py`(SSE 桥接) → `static/`(可视化) → `cli.py`(CLI 前端)

## 3. 关键设计决策

### 3.1 dispatch_subagents 工具（tool_executor.py）
- 仅主 agent 的 ToolExecutor 注册（构造时传 `dispatch_callback`），subagent 的实例**不含**该工具 → 防递归天然保证
- 参数 `subtasks`：JSON 数组字符串（LLM 生成），`parse_subtasks` 兜底支持 `|`/换行分隔
- 上限 `MAX_SUBAGENTS=5`，防 LLM 拆爆

### 3.2 SubAgent（subagent.py）
- 独立 `ToolExecutor(work_dir=同一目录)` 实例（工具集自动排除 dispatch）
- `SUB_SYSTEM`：任务导向 prompt，含 **并行竞争提示**（依赖文件可能未生成 → 基于自包含描述独立完成，不死等）
- `SUB_MAX_TURNS=8`（比主 agent 12 少，防失控）
- 结果 `SUB_RESULT_MAX_CHARS=500` 截短回灌（防撑爆主 agent context；完整 trace 仍走 SSE 供可视化）
- ★ 必须回传 `reasoning_content`（DeepSeek 多轮约束，Week12/13 踩过的坑）

### 3.3 SSE 实时桥接（server.py，★ 老师示例模式）
```
POST /chat
  ├─ threading.Thread(daemon) 后台线程跑完整任务（_run_full_task）
  │    ├─ 主 agent ReAct（每步 q.put：react_turn/act/observe）
  │    ├─ dispatch_subagents → ThreadPool 并行 subagent
  │    │    └─ subagent 每步经请求级队列 q.put（subagent_step/done）
  │    └─ 收尾（done / auto_flush）
  └─ SSE 主循环：q.get() 阻塞 → 拿到即 yield（SENTINEL 哨兵结束）
```
- **关键**：整个任务在后台线程执行，事件产生即入队即推送 → 浏览器实时看到过程流
- **踩坑教训**：最初实现在 async generator 里同步执行 dispatch（execute 阻塞等所有 subagent 跑完），
  SSE 在 10-30s 内完全沉默，浏览器只能"最后一次性"收到全部事件——必须线程化 + 队列实时桥接
- 请求级队列（非全局），并发请求互不串流；subagent 事件与主 agent 事件同队列按到达顺序推送
- ★ 事件 type 覆盖坑：subagent step 自带 `"type":"react_act"`，put 时必须 `{"sid":sid, **step, "type":"subagent_step"}` 强制覆盖

**实时性配套措施**（对抗缓冲环境）：
| 措施 | 位置 | 作用 |
|------|------|------|
| 抗缓冲响应头 | server.py StreamingResponse | `Cache-Control: no-cache, no-transform` + `X-Accel-Buffering: no`，禁止代理转换/缓冲 SSE |
| ts 时间戳 | `_sse()` 统一注入 `ts` | 每个事件带生成时刻 |
| 前端回放兜底 | index.html `enqueueEvent/replayTick` | 若事件仍被缓冲成一次性到达，按 ts 原始间隔逐条回放渲染（50-800ms clamp），任何环境都呈现"实时"效果 |

### 3.4 主 agent 决策规则（server.py DISPATCH_RULES）
- 注入 System Prompt：多独立工作项 → **必须** dispatch；单任务 → 直接做
- 含 worked example（光说"必须派发"无效，要教格式——老师示例踩坑同款）
- `shell_exec` 描述明确 **Windows PowerShell 语法**（`Get-ChildItem` 而非 `ls -la`），消除 LLM 用 bash 语法导致的"工具不可用"误判

### 3.5 安全护栏（★ 本周实测暴露后新增）
| 风险 | 实测事故 | 防护 |
|------|---------|------|
| subagent 自主删除项目文件 | 浏览器演示中 subagent `Remove-Item` 删掉了 PROJECT.md/run_*.ps1 等 5 个文件 | 删除类命令全拦（rm -rf / Remove-Item / del /s / rmdir /s 等黑名单 + 正则兜底单文件删除），返回中文提示 |
| PowerShell 输出 GBK 解码崩溃 | `text=True` 默认 utf-8 解码报 UnicodeDecodeError | `encoding="utf-8", errors="replace"` + `-NoProfile` |

## 4. 实验结果（真实跑出，5 轮）

| 轮次 | 场景 | subagent 数 | 并行墙钟 | 串行基线 | 加速 | 结果 |
|------|------|------------|---------|---------|------|------|
| 1 | 计算器项目（首次联调） | 3 | 21.78s | 58.43s | **2.68×** | 1 个 subagent 超轮次，主 agent 兜底补写 |
| 2 | 计算器项目（type 修复后） | 3 | 31.53s | 71.09s | **2.25×** | 3/3 成功 ✅ |
| 3 | 计算器项目（浏览器 UI） | 3 | — | — | — | 3/3 成功，文件生成（subagent 自作主张建子目录+删文件 → 触发安全加固） |
| 4 | 计算器项目（最终版） | 3 | 24.51s | 55.41s | **2.26×** | 3/3 成功 ✅ + 9 个单测全过 |
| 5 | 计算器项目（SSE 实时推送重构后） | 3 | 43.26s | — | — | 3/3 成功 ✅ + 13 个单测全过；**事件逐步实时到达**（dispatch 24.1s → subagent 步骤 24-53s 穿插 → dispatch_done 65.5s → done 101.4s） |

**结果解读**（教学点）：
- dispatch 加速 ~2.2-2.7×：3 个独立子任务并行，墙钟从 sum 压到 ≈max
- 总墙钟加速 < dispatch 加速：主 agent 自身串行段（规划+综合+兜底）不并行化——**Amdahl 定律**（老师示例同款结论）
- 主 agent 的兜底能力是 Orchestrator-Workers 的价值：subagent 失败/漏做时主管回收补位
- 轮次 4→5 墙钟差异主要来自 LLM 推理耗时波动（deepseek 单次调用 20-30s 常见），非系统退化
- **派发决策不稳定**：同一种问题主 agent 多数派 3 个 subagent，偶发只派 1 个（LLM 自主性）——规则兜底见 §6 优化方向

## 5. 与 PPT 对应

| PPT 概念 | 本项目落点 |
|----------|-----------|
| 6.3 Orchestrator-Workers | 主 agent 派发 + 回收合成；动态拓扑（运行时生长） |
| 6.3 Diamond fan-out/fan-in | dispatch（fan-out）→ ThreadPool 并行 → 汇总 Observation（fan-in） |
| 6.4 用图理由 | 多异构节点协作 ✓、可并行分支 ✓、需独立验证 ✓ |
| 6.4 落地要点 | Schema-first（子任务描述自包含）、节点级可观测（SSE trace）、模型分层（同模型，轻量 prompt 降本） |

## 6. 优化方向

| 层面 | 方向 |
|------|------|
| 并行收益 | 主 agent 规划/综合异步化；或便宜模型做路由（PPT 6.4 模型分层） |
| subagent | 失败重试、结果去重、依赖任务串行化（如 test 依赖主文件时） |
| 决策 | dispatch 决策加规则兜底（query 含"多个/并行/分别"强制派发） |
| 安全 | write_file 路径白名单（限制只能在 outputs/ 写）、shell 白名单命令 |
| 工程 | subagent 上限可配、trace 持久化回放、serial A/B 一键对比 |

## 7. 目录结构

```
agent_subagents/
├── src/
│   ├── subagent.py        # ★ SubAgent + run_subagents 并行 + 事件回调 + parse_subtasks
│   ├── tool_executor.py   # ★ 工具注册（+dispatch_subagents 钩子）+ 安全护栏
│   ├── server.py          # ★ SSE 事件桥接 + DISPATCH_RULES 注入 + 静态挂载
│   ├── cli.py             # ★ CLI 前端（subagent 事件展示）
│   ├── llm_config.py      # DeepSeek 客户端（unchanged from Week13）
│   └── ...                # context_engine/memory_*/skill_loader/session_db（unchanged）
├── static/
│   ├── index.html         # ★ 左拓扑右 trace 可视化
│   └── viz/topology.js    # SVG 拓扑动画（参考老师示例）
├── outputs/demo_calculator*   # 演示产物（多轮）
├── ARCHITECTURE.md / USAGE_GUIDE.md / RESUME_GUIDE.md
└── PROJECT.md             # Week15 项目说明
```

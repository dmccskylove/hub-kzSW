# Week15 作业：Subagent 并行执行系统（Graph Engineering / Orchestrator-Workers）

> 设计文档 · 踩坑记录 · 技术亮点 · 最终版
> 基于 Week13 agent_skills_system 扩展

---

## 一、项目目标

在 Week13 Agent（记忆 + Skills + ReAct 工具调用）基础上，实现 **可下发 subagent 的并行编排 Agent**：

1. **主 agent 自主拆分**：收到多独立工作项任务时，调用 `dispatch_subagents` 拆分并行（单任务直接做）
2. **subagent 并行执行**：多个 subagent（轻量 ReAct，无记忆/skills/派发能力）用 ThreadPoolExecutor 并行
3. **回收汇总**：结果截短回灌主 agent，综合成最终交付 + 并行统计（墙钟 vs 串行基线 vs 加速比）
4. **全程可视化**：SSE 实时流 → 左拓扑（节点随派发生长）右 trace（可点节点过滤）

范式对应 PPT 6.3 **Orchestrator-Workers（动态）**，与老师示例 `market_research_subagents` 对齐，场景改为文件/代码任务。

## 二、架构

```
用户任务
  ↓
主 agent ReAct 循环（5 工具: write/read/list/shell + dispatch_subagents）
  ├─ 单任务 → 直接做
  └─ 多工作项 → dispatch_subagents(["子任务1", ...]) → ThreadPoolExecutor 并行
        ├─ subagent0 ReAct(4工具) ─┐
        ├─ subagent1 ReAct(4工具) ─┤ 事件经 queue.Queue 桥接 → SSE
        └─ subagent2 ReAct(4工具) ─┘
  ↓ 汇总（500 字截短 + 并行统计）
主 agent 综合 → Final Answer
```

## 三、关键实现

| 模块 | 职责 | 亮点 |
|------|------|------|
| `src/subagent.py` | SubAgent + 并行 + 事件回调 | 防递归（无 dispatch 工具）、并行竞争提示、reasoning_content 回传 |
| `src/tool_executor.py` | 工具注册 + dispatch 钩子 + 安全护栏 | 删除类命令全拦、PowerShell 语法提示、GBK 输出编码加固 |
| `src/server.py` | SSE 桥接 + DISPATCH_RULES | queue drain 按序推送、worked example 引导决策 |
| `static/` | 可视化 | 左拓扑右 trace、节点脉冲/变绿、并行统计卡片 |
| `src/cli.py` | CLI 前端 | subagent 事件逐条展示 |

## 四、实测结果（4 轮，均真实运行）

| 轮次 | 并行墙钟 | 串行基线 | 加速 | 说明 |
|------|---------|---------|------|------|
| 1（首联调） | 21.78s | 58.43s | 2.68× | 1 subagent 超轮次，主 agent 兜底 |
| 2（type 修复） | 31.53s | 71.09s | 2.25× | 3/3 成功 |
| 3（浏览器 UI） | — | — | — | 3/3 成功；subagent 删文件 → 触发安全加固 |
| 4（最终版） | 24.51s | 55.41s | 2.26× | 3/3 成功 + 9 单测全过 |
| 5（SSE 实时推送重构后） | 43.26s | — | — | 3/3 成功 + 13 单测全过；事件逐步实时到达（实时推送验证） |

## 五、踩坑记录（详细见 ARCHITECTURE.md §3.3/3.5）

1. **SSE 沉默 → 最后一次性送达**（★ 最重要的架构坑）：最初在 async generator 里同步执行 dispatch，execute 阻塞等所有 subagent 跑完（10-30s），期间 SSE 不推任何事件，浏览器只能最后一次性显示。**修复**：照老师示例重构——整个任务放后台线程（threading.Thread），事件产生即入请求级队列，SSE 主循环 q.get() 阻塞拿到即 yield（SENTINEL 哨兵结束）。配套：抗缓冲响应头 + 前端 ts 回放兜底。
2. **subagent 事件 type 被覆盖**：step 自带 `type:react_act` 覆盖外层 `subagent_step` → 必须 `{"sid":sid, **step, "type":"subagent_step"}`
3. **残留进程跑旧代码**：Windows kill 不彻底，修复后不生效的元凶（症状：改代码无效）→ 启动前必须确认端口无监听
4. **subagent 自主删除项目文件**（实测事故）：`Remove-Item` 删掉 5 个项目文件 → 删除类命令全拦 + 正则兜底
5. **PowerShell 输出 GBK 崩溃**：text=True 默认 utf-8 解码炸 → errors="replace" + -NoProfile
6. **LLM 用 bash 语法调 PowerShell**：`ls -la`/`grep` 全失败 → 工具描述明确 PowerShell 语法后主 agent 轮次 10→8
7. **Amdahl 诚实呈现**：总加速比 < dispatch 加速比（串行段不并行化），教学点非 bug

## 六、与 PPT 对应

- **6.3 Orchestrator-Workers**：主管派发 + 回收合成，动态拓扑
- **6.3 Diamond fan-out/fan-in**：dispatch → 并行 → 汇总
- **6.4 落地要点**：Schema-first（子任务自包含）、节点级可观测（SSE trace）、模型分层（轻量 subagent prompt）

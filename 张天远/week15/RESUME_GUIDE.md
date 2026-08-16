# RESUME_GUIDE.md — 简历素材提取

> 用途：把本项目的技术亮点转成简历可用的表述。所有数字来自真实运行（见 ARCHITECTURE.md §4）。
> 简历写作规则：不暴露课程痕迹，写"独立开发"；量化指标 + 方法论要点。

## 一句话定位

**LLM Agent 并行编排系统（Orchestrator-Workers）**：主 Agent 自主拆分任务、派发多个 Subagent 并行执行（ThreadPoolExecutor）、回收汇总，实测并行加速 2.26~2.68×。

## 简历可用要点

### 量化指标
| 指标 | 数值 | 来源 |
|------|------|------|
| 并行加速比 | 2.26×~2.68×（wall 21.8~31.5s vs 串行 55.4~71.1s） | 真实运行统计 |
| subagent 任务成功率 | 3/3 成功（最终版） | 真实运行 |
| 端到端任务 | 主 agent 8 轮收尾（规划→派发→自检→综合） | 真实运行 |
| 可视化 | SSE 实时拓扑 + 步骤流（左拓扑右 trace） | 交付形态 |
| 事件流 | dispatch / subagent_step / subagent_done / dispatch_done 全链路 | 协议设计 |

### 技术要点（方法论）
1. **动态 Orchestrator-Workers 拓扑**：LLM 自主决策派发（多独立工作项→拆分，单任务→直做），拓扑运行时生长，非固定流程
2. **并行执行**：ThreadPoolExecutor fan-out/fan-in，结果截短回灌防 Context 膨胀；量化 Amdahl 定律（串行段不并行化）
3. **防递归与资源保护**：subagent 工具集排除派发工具（防递归）、回合上限 8、派发上限 5、结果 500 字截短
4. **SSE 线程化实时桥接**（★ 亮点）：任务整体在后台线程执行 + 请求级 queue 逐事件实时推送（替代同步阻塞——同步执行会导致 SSE 沉默、浏览器最后一次性收到）；SENTINEL 哨兵收尾；抗缓冲响应头 + 前端 ts 时间戳回放兜底
5. **多线程事件桥接**：subagent 事件与主 agent 事件同队列按到达顺序推送，实时可视化（拓扑生长/节点脉冲/步骤流）
6. **安全护栏**：危险命令黑名单 + 正则兜底（实测拦截 subagent 自主删除项目文件），PowerShell 输出编码加固
7. **ReAct + Function Calling**：DeepSeek reasoning_content 多轮回传、工具 schema 驱动、worked example 引导决策

### 涉及技术栈
Python · FastAPI · SSE · ThreadPoolExecutor · DeepSeek API · Function Calling · ReAct · queue 桥接 · SVG 可视化

## 面试可能追问

**Q: 为什么 dispatch 加速 2.26× 而不是 3×？**
A: 3 个子任务并行理论上限 3×，但主 agent 串行段（规划+综合+兜底）不并行化，总墙钟 = 串行段 + max(并行段)。这是 Amdahl 定律：加速比上限 = 1/(1-p+p/n)。诚实呈现并行收益边界。

**Q: subagent 之间如何协作？**
A: 不直接协作（隔离执行），依赖通过主 agent 拆解时保证（子任务描述自包含）；文件依赖场景（test 依赖主文件）通过"并行竞争提示"让 subagent 基于描述独立完成 + 主 agent 回收时交叉校验兜底。

**Q: 怎么防止 subagent 失控？**
A: 三层：工具集（无派发能力=防递归）、轮次/数量上限（8 轮/5 个）、命令护栏（删除类命令全拦）。实测发生过 subagent 自主删除项目文件，已加固。

**Q: SSE 实时流怎么实现的？踩过什么坑？**
A: 任务整体放后台线程（threading.Thread + daemon），每个事件（主 agent 步骤/subagent 每步/统计）产生即入请求级 queue.Queue，SSE 主循环 q.get() 阻塞拿到即 yield，SENTINEL 哨兵收尾。坑：最初在 async generator 里同步执行 dispatch（阻塞等 subagent 跑完 10-30s），SSE 完全沉默，浏览器最后一次性收到——必须线程化 + 队列实时桥接；再加抗缓冲响应头和前端 ts 回放兜底，双保险。

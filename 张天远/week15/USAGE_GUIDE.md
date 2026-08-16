# USAGE_GUIDE.md — 使用与测试指南

## 1. 环境准备

```powershell
cd E:\npl\workspaces\npl_tran\agent_subagents
pip install -r requirements.txt        # openai + fastapi + uvicorn + httpx
$env:DEEPSEEK_API_KEY = "sk-your-key-here"   # LLM 推理（主/subagent 共用）
```

## 2. 启动

### 后端（FastAPI + SSE）
```powershell
.\run_server.ps1 -Port 8015
# 或
python -m uvicorn src.server:app --host 0.0.0.0 --port 8015
```

### 前端可视化
浏览器打开 `http://localhost:8015/static/index.html`
- 左侧：任务拓扑（主 agent 节点；派发时 subagent 节点动态生长，运行脉冲、完成变绿）
- 右侧：实时过程流（全部实时流 / 点节点只看该节点）
- 下方：最终交付 + 并行统计（墙钟 vs 串行基线 vs 加速比）

### CLI 前端
```powershell
python -m src.cli --port 8015
```
直接输入任务描述。CLI 会打印 dispatch/subagent_step/subagent_done/dispatch_done 事件。

## 3. 演示任务

```text
生成一个 Python 计算器项目：需要 calculator.py（四则运算+历史记录）、
test_calculator.py（单元测试）、README.md（用法说明），三个文件请并行完成
```
预期：主 agent 调用 `dispatch_subagents` 拆 3 个子任务 → 3 个 subagent 并行 → 加速 ~2.2×。

**单文件对照**（不派发）：
```text
生成一个待办事项 todo.py：单文件即可，支持添加/列出/完成/删除
```

## 4. 作为模块调用

```python
import sys; sys.path.insert(0, "src")
from subagent import run_subagents, parse_subtasks, format_dispatch_observation

# 直接并行跑子任务（不带 SSE，纯逻辑）
def on_step(sid, step): print(f"[sub{sid}] {step['type']} {step.get('tool','')}")
def on_done(sid, dur, summary): print(f"[sub{sid}] done {dur}s")
results, stats = run_subagents(
    ["写 a.py", "写 b.py", "写 c.py"], work_dir=".",
    on_step=on_step, on_done=on_done)
print(format_dispatch_observation(results, stats))

# 解析 LLM 生成的 subtasks
print(parse_subtasks('["任务1", "任务2"]'))   # -> ['任务1', '任务2']
```

## 5. API 说明

| 接口 | 说明 |
|------|------|
| `GET /status` | 会话/技能/记忆状态 |
| `POST /new` | 新会话 |
| `POST /chat {session_id, message}` | SSE 流：`context_assembly → react_act/observe(主) → dispatch → subagent_step → subagent_done → dispatch_done → token → done` |
| `GET /static/*` | 可视化前端 |

## 6. 调试与常见问题

**Q: 主 agent 不派发，自己串行写？**
A: 确认任务含 2+ 独立工作项且描述明确（如"三个文件并行完成"）。仍偶发可强化 DISPATCH_RULES 的 worked example。

**Q: subagent 超轮次（8 轮）？**
A: 多见于子任务间存在文件依赖（如 test 依赖 calculator.py）。已内置"并行竞争提示"（基于描述独立完成）。若频繁出现，把依赖型子任务在拆分时描述得足够自包含，或 SUB_MAX_TURNS 调大。

**Q: subagent 找不到/删除了文件？**
A: 删除类命令已被安全护栏拦截（返回中文错误提示）。若仍担心，可在 tool_executor 的 write_file 加路径白名单。

**Q: 为什么总加速比（~1.4×）小于 dispatch 加速（~2.2×）？**
A: Amdahl 定律——主 agent 串行段（规划+综合+兜底）不并行化。这是诚实的教学点，不是 bug。

**Q: SSE 里 subagent 事件 type 变成 react_act？**
A: 已知坑：`{"sid": sid, **step, "type": "subagent_step"}` 中 `"type"` 必须放 `**step` **之后**覆盖内层。改回来即可。

**Q: 前端报 `SyntaxError: Unexpected token 'I', "Internal S"...`？**
A: 服务器在 SSE 流中途抛了未捕获异常（多为 Step1-4 上下文准备阶段：memory 文件缺失 / SQLite 锁 / 文件被删），uvicorn 把 "Internal Server Error" 塞进流。已修复：后端 Step1-4/6-9 全部兜底转 SSE error 事件、_sse 序列化兜底、前端显示 error 事件和非 200 响应体。若仍出现，把前端显示的 error 内容（现在可读了）发我。

**Q: UI 不实时显示，任务完成后才一次性全部出现？**
A: 已修复（根因：dispatch 同步阻塞导致 SSE 沉默）。现方案：整个任务在后台线程执行（threading.Thread），事件产生即入请求级队列，SSE 主循环 q.get() 拿到即 yield——逐事件实时推送；配套抗缓冲响应头（no-transform）+ 前端 ts 时间戳回放兜底（极端缓冲环境按原始间隔回放）。验证：curl 逐事件到达时间戳与执行节奏一致，浏览器 30s/60s/90s 中间态逐步渲染。

**Q: 服务器起不来 / 端口占用？**
A: `netstat -ano | findstr 8015` 找到 PID 后 `Stop-Process -Id <pid> -Force`。注意 Windows 下 kill 可能不彻底，残留进程会跑旧代码（症状：修复不生效）——务必确认端口无监听再启动。

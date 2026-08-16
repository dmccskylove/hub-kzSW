"""FastAPI 后端 — Agent 记忆 + Skills 系统（含 ReAct + Function Calling）

提供 REST API + SSE 流式接口，管理会话生命周期。
"""
import json
import asyncio
import os
import queue
import time
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from .session_db import SessionDB
from .memory_loader import MemoryLoader
from .skill_loader import SkillLoader
from .context_engine import ContextEngine
from .memory_flush import MemoryFlusher
from .llm_config import chat_stream, chat_with_tools
from .tool_executor import ToolExecutor
from .subagent import build_dispatch_handler
from .models import ChatRequest, FlushResponse, SkillInfo, SystemStatus

MAX_REACT_TURNS = 12  # 预加载 Context 后不需要太多轮次
MAX_CONTEXT_CHARS = 60000  # Context 保护：超此阈值裁剪旧轮次

# 主 agent 并行派发决策规则（注入 System Prompt，教 LLM 何时用 dispatch_subagents）
DISPATCH_RULES = """
## 并行派发规则（dispatch_subagents）★
当用户任务包含 2 个及以上相对独立的工作项时（如生成多个文件、并行分析多个主题、批量处理多个数据文件），
【必须】使用 dispatch_subagents 工具并行完成，而不是自己逐个串行写/做。

- 参数 subtasks：JSON 数组字符串，每个元素是一个子任务的完整描述
- 每个子任务描述必须包含：目标 + 输出文件路径 + 关键要求（subagent 无额外上下文，描述要自包含）
- ★ 依赖型子任务（如测试依赖源码）：必须在描述中写明依赖文件的【接口规格】
  （类名/方法签名/返回类型/异常类型），让 subagent 独立完成，不要依赖读源码
- 示例（用户要"生成一个计算器项目"）：
  ["编写 calculator.py：实现四则运算、历史记录、main 入口，保存到 calculator.py",
   "编写 test_calculator.py：对 calculator.py 的四则运算做单元测试，保存到 test_calculator.py",
   "编写 README.md：介绍项目功能、用法、示例，保存到 README.md"]
- 单文件/单任务（只写一个文件或只做一件事）时自己直接做，不要派发
"""


def _estimate_chars(messages: list[dict]) -> int:
    """估算 messages 的总字符数"""
    return sum(len(str(m.get("content", ""))) + len(json.dumps(m.get("tool_calls", []))) for m in messages)


def _trim_messages(messages: list[dict], keep_recent: int = 8) -> list[dict]:
    """裁剪旧消息，保留最近 N 条 + 所有 user 消息"""
    if len(messages) <= keep_recent:
        return messages
    user_msgs = [m for m in messages if m["role"] == "user"]
    non_user = [m for m in messages if m["role"] != "user"]
    return user_msgs[:-1] + non_user[-keep_recent:]


def _preload_project_context() -> str:
    """自动收集项目关键信息，注入 System Prompt
    像 Hermes 在对话开始前就加载 MEMORY.md / AGENTS.md 一样，
    这里提前读 PROJECT.md + 目录结构，让 LLM 不需要自己探索。
    """
    import glob as glob_mod
    parts = []

    # 1. PROJECT.md — 最核心的架构文档
    project_md = os.path.join(os.path.dirname(os.path.dirname(__file__)), "PROJECT.md")
    if os.path.exists(project_md):
        with open(project_md, "r", encoding="utf-8") as f:
            parts.append(f.read()[:8000])  # 取前 8000 字足够

    # 2. 项目目录结构
    root = os.path.dirname(os.path.dirname(__file__))
    items = sorted(os.listdir(root))
    dirs = [f"  {d}/" for d in items if os.path.isdir(os.path.join(root, d)) and not d.startswith(".") and d not in ("__pycache__", "outputs", "data")]
    files = [f"  {f}" for f in items if os.path.isfile(os.path.join(root, f)) and not f.startswith(".")]
    if dirs or files:
        parts.append("## 项目目录结构\n" + "\n".join(dirs + files))

    # 3. src/ 文件列表
    src_dir = os.path.join(root, "src")
    if os.path.isdir(src_dir):
        src_files = sorted(
            f for f in os.listdir(src_dir)
            if f.endswith(".py") and not f.startswith("_")
        )
        parts.append("## 核心源文件\n" + "\n".join(f"  src/{f}" for f in src_files))

    return "\n\n".join(parts) if parts else ""

# ── 单例 ──────────────────────────
db: SessionDB
mem_loader: MemoryLoader
skill_loader: SkillLoader
ctx_engine: ContextEngine
flusher: MemoryFlusher
tool_exec: ToolExecutor
current_session_id: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, mem_loader, skill_loader, ctx_engine, flusher, tool_exec, current_session_id
    db = SessionDB()
    mem_loader = MemoryLoader()
    skill_loader = SkillLoader()
    ctx_engine = ContextEngine(mem_loader, skill_loader)
    flusher = MemoryFlusher()
    # Work dir for file operations（请求内创建带 dispatch 的 ToolExecutor，全局实例仅用于状态展示）
    work_dir = os.path.dirname(os.path.dirname(__file__))
    tool_exec = ToolExecutor(work_dir=work_dir)
    current_session_id = db.new_session()
    print(f"[server] Session {current_session_id} started")
    print(f"[server] {len(skill_loader.list_skills())} skills, {len(tool_exec._tools)} tools loaded")
    yield
    db.close_session(current_session_id)
    print(f"[server] Session {current_session_id} closed")


app = FastAPI(lifespan=lifespan)

# 静态资源（Web 可视化前端）
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
async def index():
    """Web 可视化入口"""
    return JSONResponse(
        {"message": "Agent Subagent API. Open /static/index.html for visualization."}
    )


# ── SSE 辅助 ──────────────────────

def _sse(data: dict) -> str:
    data = dict(data)
    data.setdefault("ts", time.time())  # ★ 时间戳：前端检测缓冲后按原始节奏回放
    try:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    except TypeError:
        # 序列化兜底：不可序列化内容降级为 str（防断流 500）
        safe = {k: (str(v) if not isinstance(v, (dict, list, str, int, float, bool, type(None))) else v)
                for k, v in data.items()}
        return f"data: {json.dumps(safe, ensure_ascii=False)}\n\n"


# ── API 路由 ──────────────────────

@app.get("/status")
async def status():
    mem = mem_loader.load_all()
    skills = [
        SkillInfo(
            name=s.name,
            description=s.description,
            triggers=s.triggers,
            size_tokens=s.size_chars // 4,
        )
        for s in skill_loader.list_skills()
    ]
    return SystemStatus(
        session_id=current_session_id,
        message_count=db.get_message_count(current_session_id),
        skills_available=skills,
        memory_chars=mem.total_chars,
    )


@app.get("/skills")
async def list_skills():
    return [
        {"name": s.name, "description": s.description, "triggers": s.triggers}
        for s in skill_loader.list_skills()
    ]


def _run_full_task(req: ChatRequest, q: queue.Queue):
    """后台线程执行完整任务（★ 老师示例模式：threading + 队列实时桥接）

    所有事件 q.put → SSE 主循环实时 yield。subagent 事件经请求级队列同样实时推送，
    彻底解决"同步阻塞 execute 导致 SSE 沉默、最后一次性送达"的问题。
    """
    sid = req.session_id
    user_msg = req.message
    work_dir = os.path.dirname(os.path.dirname(__file__))
    # 请求级 ToolExecutor：dispatch_callback 绑定本请求队列（subagent 事件实时入队）
    req_tool_exec = ToolExecutor(work_dir=work_dir,
                                 dispatch_callback=build_dispatch_handler(work_dir, q))

    # ── Step 1-4.5: Skill 匹配 + 加载 / DB / Context 组装 / 预加载 ──
    # ★ 全程兜底：任何异常转成 SSE error 事件，而不是 500 "Internal Server Error"
    try:
        matches = skill_loader.match(user_msg)
        if matches:
            best = matches[0]
            q.put({"type": "skill_match", "name": best.skill.name,
                    "confidence": best.confidence, "triggers": best.matched_triggers})
            skill_loader.load_skill(best.skill.name)
            q.put({"type": "skill_loaded", "name": best.skill.name,
                    "size_chars": best.skill.size_chars})

        db.add_message(sid, "user", user_msg)

        # ── Step 4: Context 组装 ──
        history = db.get_session_messages(sid)
        ctx = ctx_engine.assemble(history)
        q.put({"type": "context_assembly", "total_chars": ctx.total_chars,
                "history_turns": len(history), "skills_loaded": ctx.skills_loaded})

        # ── Step 4.5: 预加载项目上下文 ──
        if ctx.skills_loaded:
            preload_context = _preload_project_context()
            if preload_context:
                ctx.system_prompt += "\n\n## 预加载的项目上下文（已包含项目结构和核心文档，无需再读取）\n" + preload_context
                ctx.system_prompt += "\n\n**重要：上下文已预加载完毕。立即开始写教案，用 write_file 直接输出。不要再用 read_file 或 list_files 探索项目。**"
                q.put({"type": "context_preloaded", "chars": len(preload_context)})
    except Exception as e:
        import traceback as _tb
        q.put({"type": "error", "message": f"context preparation error: {e}\n{_tb.format_exc()[:500]}"})
        return

    # ── Step 5: ReAct 循环 ──
    # 注入并行派发决策规则（无条件，教 LLM 何时拆分子任务）
    ctx.system_prompt += "\n\n" + DISPATCH_RULES
    tools = req_tool_exec.get_schemas()
    messages = history.copy()
    full_reply = ""
    turn = 0

    try:
        while turn < MAX_REACT_TURNS:
            turn += 1
            result = chat_with_tools(messages, system=ctx.system_prompt, tools=tools)

            if result.tool_calls:
                # ── 有工具调用 ──
                q.put({"type": "react_turn", "turn": turn})

                for tc in result.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    q.put({"type": "react_act", "turn": turn,
                            "tool": tool_name, "args": tool_args})
                    obs = req_tool_exec.execute(tool_name, tool_args)
                    # ★ subagent 事件已实时入队（dispatch 执行期间每个 subagent 步骤即入队），
                    #   无需 drain —— SSE 主循环会按到达顺序 yield
                    q.put({"type": "react_observe", "turn": turn,
                            "tool": tool_name, "result": obs[:1000]})
                    # 构造 assistant tool_calls 消息（★ 必须回传 reasoning_content）
                    asst_msg = {
                        "role": "assistant", "content": None,
                        "tool_calls": [{
                            "id": tc["id"], "type": "function",
                            "function": {"name": tool_name,
                                "arguments": json.dumps(tool_args, ensure_ascii=False)},
                        }]}
                    if result.reasoning_content:
                        asst_msg["reasoning_content"] = result.reasoning_content
                    messages.append(asst_msg)
                    messages.append({
                        "role": "tool", "tool_call_id": tc["id"], "content": obs,
                    })

                # Context 保护
                total_chars = _estimate_chars(messages) + len(ctx.system_prompt)
                if total_chars > MAX_CONTEXT_CHARS:
                    messages = _trim_messages(messages)
                    q.put({"type": "context_trimmed",
                            "before_chars": total_chars, "after_msgs": len(messages)})

            elif result.content:
                full_reply = result.content
                for line in full_reply.split("\n"):
                    q.put({"type": "token", "content": line + "\n"})
                break
            else:
                break

    except Exception as e:
        full_reply = f"(ReAct loop error: {e})"
        q.put({"type": "error", "message": str(e)})

    if turn >= MAX_REACT_TURNS and not full_reply:
        full_reply = "(ReAct loop reached max turns without final answer)"

    # ── Step 6: 保存回复 ──
    try:
        db.add_message(sid, "assistant", full_reply)
    except Exception as e:
        q.put({"type": "error", "message": f"save reply error: {e}"})

    # ── Step 7: 释放 Skill ──
    if skill_loader._active_skill:
        skill_loader.release()
        q.put({"type": "skill_released", "message": "Skill context released"})

    # ── Step 8-9: Flush 检查 ──
    msg_count = db.get_message_count(sid)
    auto_flush = msg_count >= 20
    q.put({"type": "done", "content": full_reply,
            "message_count": msg_count, "react_turns": turn,
            "auto_flush_triggered": auto_flush})

    if auto_flush:
        try:
            result = flusher.flush(history)
            db.mark_flushed(sid)
            q.put({"type": "auto_flush", "user_updates": result["user_updates"],
                    "memory_entries": result["memory_entries"]})
        except Exception as e:
            q.put({"type": "error", "message": f"auto flush error: {e}"})


@app.post("/chat")
def chat(req: ChatRequest):
    """SSE 流式对话（★ 老师示例模式：后台线程跑任务，队列实时桥接）

    整个任务在 daemon 线程执行，每个事件（主 agent 步骤 / dispatch / subagent 步骤 / done）
    产生即入队；SSE 主循环 q.get() 阻塞拿到即 yield —— 浏览器实时收到，无缓冲。
    """
    def event_stream():
        q = queue.Queue()
        SENTINEL = object()

        def run():
            try:
                _run_full_task(req, q)
            except Exception as e:
                q.put({"type": "error", "message": f"{type(e).__name__}: {str(e)[:300]}"})
            finally:
                q.put(SENTINEL)

        threading.Thread(target=run, daemon=True).start()

        yield _sse({"type": "start", "message": req.message})
        while True:
            ev = q.get()
            if ev is SENTINEL:
                break
            yield _sse(ev)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={
            # ★ 抗缓冲：no-transform 禁止代理转换/缓冲 SSE；X-Accel-Buffering 禁 nginx 类缓冲
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        })


@app.post("/flush")
async def flush():
    messages = db.get_session_messages(current_session_id)
    if not messages:
        return FlushResponse(summary="No messages to flush")
    result = flusher.flush(messages)
    db.mark_flushed(current_session_id)
    return FlushResponse(**result)


@app.post("/new")
async def new_session():
    global current_session_id
    db.close_session(current_session_id)
    messages = db.get_session_messages(current_session_id)
    if messages:
        flusher.flush(messages)
    current_session_id = db.new_session()
    return {"session_id": current_session_id}

"""
FastAPI HTTP 服务，提供流式 SSE 接口给 Web UI

接口：
  POST /query/manual       - 手写版 ReAct（一次性，向后兼容）
  POST /query/fc           - Function Calling 版（一次性，向后兼容）
  POST /session            - 创建新会话 → {session_id}
  POST /chat/{session_id}  - 多轮对话，SSE 流式返回每步
  GET  /sessions           - 列出所有会话
  GET  /session/{session_id} - 查看会话详情
  DELETE /session/{session_id} - 删除会话
  GET  /health             - 健康检查

使用方式：
  uvicorn serve:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── 预加载 FAISS（启动时执行一次）────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("预加载 FAISS 索引和 Embedding 模型...")
    from tools import _load_rag
    await asyncio.to_thread(_load_rag)
    logger.info("预加载完成，服务就绪")
    yield


app = FastAPI(title="ReAct Financial Agent", lifespan=lifespan)


# ── 请求模型 ────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question:  str
    max_steps: int = 10


class SessionCreateRequest(BaseModel):
    mode: str = "manual"  # "manual" or "fc"


class ChatRequest(BaseModel):
    question:  str
    max_steps: int = 10


# ── SSE 工具函数 ─────────────────────────────────────────────────────────────
def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_from_generator(react_gen, extra_start: dict | None = None):
    """通用：把同步 Generator 包装为异步 SSE 流"""
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()

    def _worker():
        try:
            for step_data in react_gen:
                queue.put_nowait(step_data)
        finally:
            queue.put_nowait(_SENTINEL)

    if extra_start:
        yield _sse(extra_start)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _worker)

    while True:
        step_data = await queue.get()
        if step_data is _SENTINEL:
            break
        yield _sse(step_data)

    yield _sse({"type": "done"})


# ── 一次性问答（向后兼容） ───────────────────────────────────────────────────
async def _stream_react(question: str, max_steps: int, mode: str):
    if mode == "manual":
        from react_manual import run as react_run
    else:
        from react_function_calling import run as react_run

    extra = {"type": "start", "question": question, "mode": mode}
    async for chunk in _stream_from_generator(react_run(question, max_steps=max_steps), extra):
        yield chunk


@app.post("/query/manual")
async def query_manual(req: QueryRequest):
    return StreamingResponse(
        _stream_react(req.question, req.max_steps, "manual"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/query/fc")
async def query_fc(req: QueryRequest):
    return StreamingResponse(
        _stream_react(req.question, req.max_steps, "fc"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 多轮对话会话管理 ─────────────────────────────────────────────────────────
from session import AgentSession


@app.post("/session")
async def create_session(req: SessionCreateRequest):
    """创建新会话，返回 session_id"""
    sess = AgentSession(mode=req.mode)

    if req.mode == "manual":
        from react_manual import SYSTEM_PROMPT
    else:
        from react_function_calling import FC_SYSTEM_PROMPT as SYSTEM_PROMPT

    sess.initialize(SYSTEM_PROMPT)
    sess.save()
    logger.info(f"会话已创建: {sess.session_id} (mode={req.mode})")
    return {
        "session_id": sess.session_id,
        "mode": sess.mode,
        "created_at": sess.created_at,
    }


@app.post("/chat/{session_id}")
async def chat(session_id: str, req: ChatRequest):
    """多轮对话：基于已有会话继续 Agent 循环"""
    sess = AgentSession.load(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

    # 追加用户问题到 messages
    sess.add_user_message(req.question)

    # 选择对应的 chat_from_messages
    if sess.mode == "manual":
        from react_manual import chat_from_messages
    else:
        from react_function_calling import chat_from_messages

    # 收集 step_data 以记录轮次历史
    collected_steps: list[dict] = []
    final_answer = ""

    async def _chat_stream():
        nonlocal final_answer

        # 先发 start 事件（含 session_id 和当前轮次）
        yield _sse({
            "type": "start",
            "session_id": session_id,
            "question": req.question,
            "mode": sess.mode,
            "turn": len(sess.history) + 1,
        })

        # 用 asyncio.Queue + 独立线程避免阻塞事件循环
        queue: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()

        def _worker():
            try:
                for step_data in chat_from_messages(sess.messages, req.max_steps):
                    queue.put_nowait(step_data)
            finally:
                queue.put_nowait(_SENTINEL)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _worker)

        while True:
            step_data = await queue.get()
            if step_data is _SENTINEL:
                break

            collected_steps.append(step_data)
            if step_data.get("type") == "final":
                final_answer = step_data.get("answer", "")
            yield _sse(step_data)

        # 记录本轮对话
        sess.record_turn(req.question, final_answer, collected_steps)
        sess.save()

        yield _sse({"type": "done"})

    return StreamingResponse(
        _chat_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/sessions")
async def list_sessions():
    """列出所有会话"""
    return AgentSession.list_sessions()


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """查看会话详情（含历史）"""
    sess = AgentSession.load(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return {
        "session_id": sess.session_id,
        "mode": sess.mode,
        "created_at": sess.created_at,
        "turns": len(sess.history),
        "history": sess.history,
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if AgentSession.delete(session_id):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")


@app.get("/health")
async def health():
    return {"status": "ok", "model": os.getenv("AGENT_MODEL", "qwen-max")}


# ── 托管 index.html ──────────────────────────────────────────────────────────
HTML_PATH = Path(__file__).parent.parent / "index.html"

@app.get("/")
async def root():
    if HTML_PATH.exists():
        return HTMLResponse(HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>index.html not found</h2>")

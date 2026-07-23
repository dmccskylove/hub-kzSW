"""
会话管理模块 — 支持多轮对话和记忆系统

- AgentSession: 管理单次会话的 messages 列表和对话历史
- 文件持久化: 每个会话保存为 sessions/{session_id}.json
- 支持: 创建、加载、列表、删除会话

使用方式:
  from session import AgentSession
  sess = AgentSession(mode="manual")
  sess.initialize(SYSTEM_PROMPT)
  sess.add_user_message("茅台2023年毛利率？")
  # ... ReAct 循环，追加 assistant 和 observation ...
  sess.save()
"""

import json
import uuid
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"


class AgentSession:
    """多轮对话会话管理器"""

    def __init__(self, mode: str = "manual", session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.mode = mode
        self.created_at = datetime.now().isoformat()
        self.messages: list[dict] = []
        self.history: list[dict] = []  # [{question, answer, steps, timestamp}]

    # ── 消息管理 ──────────────────────────────────────────────────────────

    def initialize(self, system_prompt: str):
        """初始化 system prompt（会话创建时调用一次）"""
        if not self.messages:
            self.messages = [{"role": "system", "content": system_prompt}]

    def add_user_message(self, question: str):
        """追加用户问题"""
        self.messages.append({"role": "user", "content": question})

    def add_assistant_message(self, content: str):
        """追加助手消息"""
        self.messages.append({"role": "assistant", "content": content})

    def add_observation(self, observation: str):
        """追加工具观察结果（以 user 角色注入，保持与手写版兼容）"""
        self.messages.append(
            {"role": "user", "content": f"Observation: {observation}"}
        )

    def add_tool_result(self, tool_call_id: str, content: str):
        """追加工具结果（FC 版 role=tool 格式）"""
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        )

    def append_raw_message(self, msg: dict):
        """直接追加原始消息对象（用于 FC 版 SDK 返回的 message 对象）"""
        self.messages.append(msg)

    # ── 轮次记录 ──────────────────────────────────────────────────────────

    def record_turn(self, question: str, answer: str, steps: list[dict]):
        """记录一轮完整对话"""
        self.history.append(
            {
                "question": question,
                "answer": answer,
                "steps": steps,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # ── 持久化 ────────────────────────────────────────────────────────────

    def _serialize_messages(self) -> list[dict]:
        """将 messages 列表转为可 JSON 序列化的格式（处理 dict 和 SDK 对象）"""
        result = []
        for m in self.messages:
            # 处理 OpenAI SDK 对象 (ChatCompletionMessage)
            if hasattr(m, "role"):
                d = {"role": m.role}
                if hasattr(m, "content") and m.content:
                    d["content"] = m.content
                if hasattr(m, "tool_calls") and m.tool_calls:
                    d["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in m.tool_calls
                    ]
                if hasattr(m, "reasoning_content") and m.reasoning_content:
                    d["reasoning_content"] = m.reasoning_content
                result.append(d)
                continue

            # 处理普通 dict
            d = {"role": m.get("role", "")}
            if m.get("content"):
                d["content"] = m["content"]
            if "tool_calls" in m:
                d["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in m["tool_calls"]
                ]
            if m.get("tool_call_id"):
                d["tool_call_id"] = m["tool_call_id"]
            if m.get("reasoning_content"):
                d["reasoning_content"] = m["reasoning_content"]
            result.append(d)
        return result

    def save(self):
        """保存会话到文件"""
        SESSIONS_DIR.mkdir(exist_ok=True)
        data = {
            "session_id": self.session_id,
            "mode": self.mode,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
            "messages": self._serialize_messages(),
            "history": self.history,
        }
        path = SESSIONS_DIR / f"{self.session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"会话已保存: {path}")

    # ── 类方法：加载 / 列表 / 删除 ─────────────────────────────────────────

    @classmethod
    def load(cls, session_id: str) -> "AgentSession | None":
        """从文件加载会话"""
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            session = cls(mode=data.get("mode", "manual"), session_id=data["session_id"])
            session.created_at = data.get("created_at", "")
            session.messages = data.get("messages", [])
            session.history = data.get("history", [])
            logger.info(f"会话已加载: {session_id}，{len(session.history)} 轮历史")
            return session
        except Exception as e:
            logger.error(f"加载会话失败 {session_id}: {e}")
            return None

    @classmethod
    def list_sessions(cls) -> list[dict]:
        """列出所有会话（按时间倒序）"""
        if not SESSIONS_DIR.exists():
            return []
        sessions = []
        for f in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                sessions.append(
                    {
                        "session_id": data.get("session_id", f.stem),
                        "mode": data.get("mode", "manual"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "turns": len(data.get("history", [])),
                    }
                )
            except Exception:
                pass
        return sessions

    @classmethod
    def delete(cls, session_id: str) -> bool:
        """删除会话文件"""
        path = SESSIONS_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"会话已删除: {session_id}")
            return True
        return False


def get_turn_summary(history: list[dict], max_turns: int = 5) -> str:
    """生成历史对话摘要，注入 System Prompt 作为长期记忆"""
    if not history:
        return ""
    recent = history[-max_turns:]
    lines = ["\n## 历史对话摘要\n"]
    for i, turn in enumerate(recent, 1):
        lines.append(f"第{i}轮: {turn['question']}")
        lines.append(f"回答: {turn['answer'][:200]}")
    return "\n".join(lines)


def estimate_tokens(messages: list) -> int:
    """粗略估算 messages 的 token 数（中英文混合：~2 char/token）"""
    total = 0
    for m in messages:
        content = ""
        if isinstance(m, dict):
            content = m.get("content", "") or ""
            # FC 版: tool_calls 也占 token
            if "tool_calls" in m:
                content += str(m["tool_calls"])
        elif hasattr(m, "content"):
            content = m.content or ""
        total += max(len(str(content)) // 2, 4)  # 每条消息至少 4 token 开销
    return total


def compress_context(messages: list, client, model: str, context_window: int = 32000) -> int:
    """超过 80% context window 时，对早期轮次做 LLM 摘要压缩（in-place 修改 messages）"""
    tokens = estimate_tokens(messages)
    if tokens < context_window * 0.8:
        return 0

    # 找到每轮用户提问的位置（非 Observation 的 user 消息）
    user_positions = []
    for i, m in enumerate(messages):
        role = m.get("role", "") if isinstance(m, dict) else getattr(m, "role", "")
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "") or ""
        if role == "user" and not str(content).startswith("Observation:"):
            user_positions.append(i)

    if len(user_positions) <= 2:
        return 0  # 轮次太少，不值得压缩

    keep_from = user_positions[-2]  # 保留最近 2 轮
    to_compress = messages[1:keep_from]
    recent = messages[keep_from:]

    # 构建压缩文本
    history_parts = []
    for m in to_compress:
        role = m.get("role", "") if isinstance(m, dict) else getattr(m, "role", "")
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "") or ""
        if not content:
            continue
        prefix = "Q" if role == "user" else "A" if role == "assistant" else role
        history_parts.append(f"{prefix}: {str(content)[:300]}")

    history_text = "\n".join(history_parts)

    # 调 LLM 做摘要
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    "请将以下对话历史压缩为一段简洁摘要，"
                    "保留所有关键数据（数字、代码、公司名）和重要结论：\n\n"
                    f"{history_text}\n\n摘要："
                ),
            }],
            max_tokens=500,
            temperature=0,
        )
        summary = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"上下文压缩失败: {e}")
        return 0

    # in-place 替换：system + 摘要 + 最近2轮
    new_prefix = [
        {"role": "user", "content": f"[历史对话摘要] {summary}"},
        {"role": "assistant", "content": "好的，我已了解之前的对话历史。"},
    ]
    messages[:] = [messages[0]] + new_prefix + recent

    saved = tokens - estimate_tokens(messages)
    logger.info(f"上下文压缩: {tokens}→{estimate_tokens(messages)} tokens (节省 {saved})")
    return saved

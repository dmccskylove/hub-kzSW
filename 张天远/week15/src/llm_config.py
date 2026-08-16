"""LLM 配置 — 统一管理 DeepSeek API 调用（含 Function Calling）"""
import os
import json
from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY not set")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )


def get_model() -> str:
    return "deepseek-v4-flash"


def chat_stream(messages: list[dict], system: str | None = None):
    """流式聊天，yield token 片段"""
    client = get_client()
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=get_model(),
        messages=full_messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def chat(messages: list[dict], system: str | None = None) -> str:
    """非流式聊天，返回完整回复"""
    client = get_client()
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=get_model(),
        messages=full_messages,
    )
    return response.choices[0].message.content or ""


class ToolCallResult:
    """工具调用结果"""
    def __init__(self, content: str | None, tool_calls: list | None, reasoning_content: str | None = None):
        self.content = content
        self.tool_calls = tool_calls
        self.reasoning_content = reasoning_content  # ★ DeepSeek 多轮必须回传

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


def chat_with_tools(
    messages: list[dict],
    system: str | None = None,
    tools: list[dict] | None = None,
) -> ToolCallResult:
    """带 Function Calling 的聊天（非流式）

    Returns ToolCallResult:
      - 如果有 tool_calls → content=None, tool_calls=[...]
      - 如果是普通回复 → content="...", tool_calls=None
    """
    client = get_client()
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    kwargs = dict(
        model=get_model(),
        messages=full_messages,
    )
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message

    # ★ 捕获 reasoning_content（DeepSeek 多轮必须回传）
    reasoning = getattr(msg, "reasoning_content", None)

    tool_calls = None
    if msg.tool_calls:
        tool_calls = [
            {
                "id": tc.id,
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
            for tc in msg.tool_calls
        ]

    return ToolCallResult(
        content=msg.content,
        tool_calls=tool_calls,
        reasoning_content=reasoning,
    )

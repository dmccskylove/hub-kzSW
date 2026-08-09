# OpenAI SDK ChatCompletionMessage 对象混入 dict 列表导致序列化崩溃

## 触发场景

在 Function Calling 模式下，`messages.append(msg)` 把 OpenAI SDK 返回的 `ChatCompletionMessage` 对象直接追加到了 messages 列表。后续保存会话到 JSON 时，`_serialize_messages()` 尝试用 `m["role"]` 访问对象属性，触发 `TypeError: 'ChatCompletionMessage' object is not subscriptable`。

## 错误代码

```python
# react_function_calling.py
msg = response.choices[0].message  # ChatCompletionMessage 对象
messages.append(msg)  # 追加的是对象，不是 dict
```

```python
# session.py — 序列化时崩溃
def _serialize_messages(self):
    for m in self.messages:
        d = {"role": m["role"]}  # 对象不能用下标访问 → TypeError
```

## 修复

序列化时同时处理两种类型：

```python
def _serialize_messages(self):
    for m in self.messages:
        if hasattr(m, "role"):  # SDK 对象
            d = {"role": m.role}
            if m.content: d["content"] = m.content
            if m.tool_calls:
                d["tool_calls"] = [{
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                } for tc in m.tool_calls]
            if m.reasoning_content: d["reasoning_content"] = m.reasoning_content
        else:  # 普通 dict
            d = {"role": m.get("role", "")}
            if m.get("content"): d["content"] = m["content"]
            # ...
```

## 通用原则

OpenAI SDK v1 返回的 message 是 Pydantic 模型对象，不是 dict。当需要和 dict 格式混合存储时（如 messages 列表中既有手动构造的 dict 又有 SDK 返回的对象），序列化逻辑必须处理两种类型。

# DeepSeek reasoning_content 与 Function Calling 思考过程

## 常见误解

**❌ 错误认知**：Function Calling 模式下无法获取模型的思考过程（Thought），只有手写 Prompt 解析版才能看到。

**✅ 实际情况**：DeepSeek 模型（包括 v4-flash）默认启用思考模式，API 返回的 `reasoning_content` 字段携带 CoT 推理链，即使在 Function Calling 场景下也可获取。

## 关键事实

| 事实 | 说明 |
|------|------|
| 字段名 | `reasoning_content`（非 `content`） |
| 默认行为 | v4-flash 默认开启，无需额外配置 |
| 返回时机 | 模型在输出 `tool_calls` 的同时，content 和 reasoning_content 都可能非空 |
| 控制参数 | `thinking` 对象中的 `reasoning_effort` 可设为 `high` 或 `max` |

## 多轮对话中的关键约束

**必须回传 `reasoning_content`**：在多轮对话（尤其是 function calling）场景下，必须将上一轮 assistant 消息里的 `reasoning_content` 字段原样带回，否则请求会失败并返回 400 错误：

```
"The reasoning_content in the thinking mode must be passed back to the API"
```

## 代码提取模式

```python
msg = response.choices[0].message

# 安全提取思考过程
thought = getattr(msg, "reasoning_content", None) or msg.content or ""

# 逻辑：先尝试 reasoning_content（专用字段），
# 再回退到 content（普通模型的文本输出），
# 最后回退到空字符串
```

## 教案编写注意事项

编写 Agent/Function Calling 相关教案时：

1. **不要写"FC 版 Thought 不可见"** — 这是过时的简化，对 DeepSeek 等模型不成立
2. **区分模型类型**：传统模型（GPT-4o, qwen-max）可能 content 为 null，DeepSeek 系列有 reasoning_content
3. **代码示例应包含提取逻辑**：`getattr(msg, "reasoning_content", None) or msg.content or ""`
4. **手写版 vs FC 版的对比维度修正**：
   - 旧：手写版 Thought 可见，FC 版不可见
   - 新：手写版 Thought 在 Prompt 文本中，FC 版 Thought 在 reasoning_content 字段中 — 形态不同，都能获取

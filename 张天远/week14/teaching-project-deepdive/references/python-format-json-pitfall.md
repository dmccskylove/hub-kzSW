# Python `.format()` 陷阱：Prompt 字符串中的 JSON 花括号

## 现象

调用 `.format()` 时报 `KeyError: '"field"'` 或 `KeyError: '"category"'`，但代码中并没有使用这些 key 做格式化。

## 根因

Python 的 `str.format()` 将 `{...}` 视为格式化占位符。当 prompt 字符串中包含 JSON 示例（如 `{"field": "值"}`），`.format()` 会尝试将 `field` 解析为关键字参数，找不到则抛 `KeyError`。

## 错误代码

```python
FLUSH_PROMPT = """分析对话，输出 JSON 数组。
每条格式：{"field": "字段名", "value": "内容"}

对话：
{conversation}
"""
# ↑ .format(conversation=...) 会把 {"field" 当成占位符 → KeyError
prompt = FLUSH_PROMPT.format(conversation=conv)
```

## 修复：双花括号转义

```python
FLUSH_PROMPT = """分析对话，输出 JSON 数组。
每条格式：{{"field": "字段名", "value": "内容"}}  # ← 双花括号

对话：
{conversation}
"""
prompt = FLUSH_PROMPT.format(conversation=conv)  # 只替换 {conversation}
```

## 排查时的误导信号

- **错误消息指向 `.format()` 调用行**，但 LLM 调用还没发生——说明问题在 Python 层而非 API 层
- **独立测试 JSON 解析正常**（`_extract_json` 逻辑正确），但集成到 `flush()` 就失败——因为 prompt 字符串根本没到达 LLM
- **`.format()` 报 KeyError 时**，它引用的是 prompt 文本中的 JSON key 名，不是代码中的变量名

## 关联场景

任何在 Python 字符串模板中嵌入 JSON 示例的场景都会遇到此问题：
- LLM prompt 工程中的 few-shot 示例
- API 文档中的请求/响应示例
- 配置文件模板

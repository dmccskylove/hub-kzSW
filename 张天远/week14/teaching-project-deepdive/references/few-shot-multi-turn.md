# Few-shot 多轮对话技术要点（小 LLM）

## 背景

对 Qwen2-0.5B 做文本分类 Few-shot 时，技术路线选错会从 48% 崩到 16.5%，选对可到 50%。

## 正确做法：多轮对话格式

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
# 插入多轮示例
for ex in few_shot_examples:
    messages.append({"role": "user",
        "content": f"新闻标题：{ex['text']}\n类别："})
    messages.append({"role": "assistant",
        "content": ex["label"]})
# 真实问题
messages.append({"role": "user",
    "content": build_prompt(text)})

encoding = tokenizer.apply_chat_template(messages, ...)
```

`apply_chat_template` 会转成 chat 格式：
```
<|im_start|>system
...<|im_end|>
<|im_start|>user
新闻标题：xxx\n类别：
<|im_end|>
<|im_start|>assistant
体育
<|im_end|>
<|im_start|>user
新闻标题：[真实文本]\n类别：
<|im_end|>
```

## 错误做法：往 System Prompt 塞示例

```python
# ❌ 错误
SYSTEM_PROMPT += "\n示例：\n新闻：xxx → 体育"
```

小模型会**模仿示例格式**输出 "新闻标题：xxx" 而非类别名，准确率从 48% 崩到 16.5%。

## 为什么多轮对话有效

Qwen 是在对话数据上微调过的——天生理解 "user 问 → assistant 答" 的模式。把示例套进这个格式，是在用模型已学会的对话能力来教它分类。而不是教它"新闻标题→类别"的映射，而是教它"这种问法应该这么答"。

## 实验结果

| 格式 | 示例数 | 准确率 |
|------|:------:|:-----:|
| 零样本（基线） | 0 | 48% |
| 多轮对话 k=1 | 15 | 47.5% |
| **多轮对话 k=2** | **30** | **50.0%** |
| 多轮对话 k=3 | 45 | 48.5% |
| System Prompt（错误） | 3 | 16.5% |

## 适用范围

- 对 0.5B 级小模型有效但上限有限（50% vs BERT 57%）
- 更大模型（7B+）可能效果更好
- k=2 是最优点，更多示例边际递减

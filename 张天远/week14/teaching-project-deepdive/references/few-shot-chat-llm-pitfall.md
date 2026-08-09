# Few-shot 在小型 chat-format LLM 上的实践教训

## 核心发现

对 Qwen2-0.5B（0.5B 参数）在 TNEWS 15 分类任务上做 few-shot，最关键的教训是：

**示例必须用多轮 user/assistant 对话格式插入，不能塞进 System Prompt。**

## 实验数据

| 轮次 | 方案 | 示例数 | 准确率 | 无法解析 | 结论 |
|:----:|------|:------:|:-----:|:--------:|------|
| — | 零样本 + 同义词优化 | 0 | 48.0% | 1.5% | 基线 |
| 1 | System Prompt 嵌入 | 15 | 32.0% | 30.0% | ❌ |
| 2 | System Prompt 嵌入(分隔线) | 3 | 16.5% | 69.0% | ❌ 崩塌 |
| 3 | 多轮对话 | 3 | 47.0% | 3.0% | ✅ 追上基线 |
| 4 | 多轮对话 | 15 (每类1) | 47.5% | 7.5% | ✅ |
| **5** | **多轮对话** | **30 (每类2)** | **50.0%** | 7.5% | ✅ 最优 |
| 6 | 多轮对话 | 45 (每类3) | 48.5% | 7.5% | ↓ 下降 |

## 错误做法

```python
# ❌ 错误：示例拼进 System Prompt 文本
SYSTEM_PROMPT += "\n\n示例：\n新闻：xxx -> 体育\n新闻：yyy -> 财经"
```

问题：Qwen 看到 System Prompt 中的 "新闻：xxx -> 类别" 格式后，在 assistant turn 中输出 "新闻标题：xxx" 而不是 "体育"。

## 正确做法

```python
# ✅ 正确：user/assistant 交替多轮对话
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
for ex in few_shot_examples:
    messages.append({"role": "user", "content": f"新闻标题：{ex['text']}\n类别："})
    messages.append({"role": "assistant", "content": ex["label"]})
messages.append({"role": "user", "content": build_prompt(actual_text)})
```

## 与 LoRA r 消融的相似性

Few-shot 的示例数也存在"最优点"——30 条最佳，45 条降到 48.5%。与 LoRA r 值消融规律一致：r=8 最优，r=16 下降。

## 建议

- 对 <1B chat-format 模型，few-shot 收益有限（零样本 48% -> 最佳 50%，仅 +2%）
- 零样本 + System Prompt + 同义词解析器可能已逼近能力上限
- 如必须做 few-shot，用多轮对话格式，不撒进 System Prompt

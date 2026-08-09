# 本地 LLM（LM Studio / Ollama）调试工作流

## 三步连通性验证

本地大模型（尤其是 GGUF 格式）接入项目前，按以下顺序逐级验证，避免 prompt 格式问题被误判为模型能力问题：

### 第 0 步：模型格式自查

学生在本地调用 LLM 前，先查模型格式。两种常见格式，行为不同：

| 格式 | 文件后缀 | 能推理？ | 能 SFT？ | 适用工具 |
|------|---------|:--:|:--:|------|
| GGUF | `.gguf` | ✅ | ❌ | LM Studio / Ollama / llama.cpp |
| HF safetensors | `.safetensors` | ✅ | ✅ | PyTorch / transformers / peft |

> GGUF 像 PDF——能读不能改。训练需要 Word 文档（HF 格式）。

### 第 1 步：列出可用模型 + 简单回声测试

```python
import json, urllib.request
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

# 列出模型
models = json.loads(urllib.request.urlopen("http://localhost:1234/v1/models").read())
print("可用模型:", [m["id"] for m in models["data"]])

# 用第一个模型做回声测试
model = models["data"][0]["id"]
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": '说"你好"'}],
    temperature=0.0, max_tokens=20,
)
print(f"回复: {repr(resp.choices[0].message.content)}")
```

**判断标准**：
- 回复包含"你好" → 模型正常，继续第 2 步
- 回复是空格/星号/乱码 → 模型未正常加载或有格式问题，跳到第 3 步排查
- 回复是 RAG 风格的模板文本（"根据参考信息...以下为..."） → Base 模型（未经 SFT），不会对话

### 第 2 步：多 prompt 格式对比

同一个任务用不同 prompt 结构测试，找出模型偏好的格式：

```python
tests = [
    # A: 纯 user 消息
    {"messages": [{"role": "user", "content": "NER任务：提取实体，输出JSON。文本：华为在深圳。"}]},
    # B: system + user
    {"messages": [
        {"role": "system", "content": "你是NER助手，输出JSON格式。"},
        {"role": "user", "content": "华为在深圳。"}
    ]},
    # C: 完整指令
    {"messages": [{"role": "user", "content": "识别实体，输出{\"entities\":[{\"text\":\"...\",\"type\":\"...\"}]}。文本：华为在深圳。"}]},
]

for i, test in enumerate(tests):
    resp = client.chat.completions.create(model=model, messages=test["messages"], temperature=0.0, max_tokens=100)
    print(f"\n格式 {'ABC'[i]} 输出: {repr(resp.choices[0].message.content[:200])}")
```

**判断标准**：哪种格式输出了有效的 JSON？以此为基准优化后续 prompt。

### 第 3 步：异常排查

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 输出全是空格/星号 | Base 模型，未经 SFT | 检查 HuggingFace 页面是否有多个版本（Base/SFT/Chat）；用 Chat/Instruct 版 |
| 输出"根据参考信息..." | RAG 风格的预训练数据残留 | 同上，换 Chat 版 |
| 输出正常文本但不含 JSON | prompt 格式不匹配模型模板 | `print(tokenizer.apply_chat_template(messages, tokenize=False))` 看实际发送格式 |
| OpenAI SDK 报错 `NoneType.chat` | 客户端创建失败，常见原因是 `build_local_client()` 缺 `return` | 检查 `return OpenAI(...)` 是否存在 |
| 模型名 `xxx@f16` 不工作 | LM Studio 的 `@f16` 后缀可能与 API 不兼容 | 用 `/v1/models` 返回的精确名称 |

## PowerShell 禁忌

**不要在 PowerShell 中用 `python -c` 写多行代码**。PowerShell 会把多行压成一行并破坏缩进。一律写成 `.py` 文件后用 `python script.py` 执行。

# GGUF vs HF：为什么量化模型不能直接训练

## 学生常见困惑

"我本地 LM Studio 里有个 `qwen3.5-9b-Q4_K_M.gguf` 文件，能推理。为什么不能用它做 QLoRA SFT？"

## 核心答案

GGUF 是纯推理格式——权重被量化压缩并打包成单文件，没有 `state_dict`，无法加载到 PyTorch `nn.Module` 做反向传播。

| | GGUF (Q4_K_M) | HF 格式 (safetensors/pytorch) |
|---|---|---|
| LM Studio 推理 | ✅ | ❌（需手动处理） |
| QLoRA 训练 | ❌ 无 `state_dict` | ✅ `bitsandbytes` 加载→量化→训练 |
| 全量微调 | ❌ | ❌ 9B 需 >72GB VRAM |
| 文件大小 | ~6GB（内置量化） | ~15GB（FP16 原始） |

## 类比

```
GGUF = PDF 文档    → 你可以读，但没法编辑
HF  = Word 文档    → 可以编辑，可以导出 PDF
```

在训练流程中，`bitsandbytes` 做的是"打开 Word，自动压缩成 4-bit 存内存，前向时解压，反向只更新 LoRA adapter"。

## 正确做法

**想 SFT 9B 模型**：
1. 从 HF 下载原始格式模型：`Qwen/Qwen2.5-7B-Instruct`（~15GB）
2. 用 `BitsAndBytesConfig(load_in_4bit=True)` 加载 + QLoRA
3. 训练完成后保存 LoRA adapter（~16MB）
4. **不要**尝试加载 GGUF 文件做训练

**想在本地做推理对比**：
- 用 LM Studio 的 OpenAI 兼容 API（`localhost:1234/v1`）
- 改 `llm_ner.py` 的 `base_url` 即可

## 显存预算（4090D 24GB）

| 方案 | 显存 | 可行 |
|------|------|:--:|
| GGUF 推理 | ~6GB | ✅ |
| QLoRA (7B, 4-bit) | ~14-16GB | ✅ |
| LoRA (7B, FP16) | ~22GB | ⚠️ 踩线 |
| 全量微调 (7B) | >72GB | ❌ |

## 相关踩坑

- 已在 `references/python_hf_path_trap.md` 记录：`Path(model_id).resolve()` 会把 HF 模型名转成错误的本地路径。训练脚本中对 HF 模型 ID 不能用 `Path.resolve()`。

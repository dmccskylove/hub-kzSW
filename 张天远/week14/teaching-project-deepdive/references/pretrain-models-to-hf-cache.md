# pretrain_models/ → HF Cache 迁移模式

## 问题

老师给的初始项目通常硬编码本地 `pretrain_models/` 路径：

```python
BERT_PATH = ROOT.parent.parent / "pretrain_models" / "bert-base-chinese"
MODEL_PATH = ROOT.parent.parent / "pretrain_models" / "Qwen2-0.5B-Instruct"
```

学生本地没有这个目录，模型在 `HF_HOME=M:\huggingface_cache` 下。

## 统一修复方案

### 步骤1：默认路径改为 HF 模型 ID

```python
# 改前
BERT_PATH  = ROOT.parent.parent / "pretrain_models" / "bert-base-chinese"
MODEL_PATH = ROOT.parent.parent / "pretrain_models" / "Qwen2-0.5B-Instruct"

# 改后
BERT_PATH  = "bert-base-chinese"             # HF model ID
MODEL_PATH = "Qwen/Qwen2-0.5B-Instruct"      # HF model ID
```

`from_pretrained()` 会自动走 `HF_HOME` 缓存，无需本地目录。

### 步骤2：修复 `Path().resolve()` 陷阱

部分脚本把路径包了 `Path().resolve()`，这会把 HF 模型 ID 转成错误的本地路径：

```python
# ❌ 坏：Path("Qwen/Qwen2-0.5B-Instruct").resolve() → "E:\项目\Qwen\Qwen2-0.5B-Instruct"
str(Path(args.model_path).resolve())

# ✅ 好：先判本地是否存在，HF ID 原样传递
_mp = str(Path(args.model_path).resolve()) if Path(args.model_path).exists() else args.model_path
```

### 步骤3：保留 CLI 参数覆盖能力

所有脚本保留 `--bert_path` / `--model_path` 参数，用户可通过命令行指定本地路径。默认值改为 HF ID 不影响灵活性。

## 影响文件清单（参考 Week08 text_match 项目）

| 文件 | BERT_PATH 改 | MODEL_PATH 改 | Path.resolve 修 |
|------|:---:|:---:|:---:|
| `src/explore_data.py` | ✓ | — | — |
| `src/train_biencoder.py` | ✓ | — | — |
| `src/train_crossencoder.py` | ✓ | — | — |
| `src/evaluate.py` | ✓ | — | — |
| `src/compare_methods.py` | ✓ | — | — |
| `src/analyze_badcases.py` | ✓ | — | — |
| `src_llm/train_sft.py` | — | ✓ | ✓ |
| `src_llm/evaluate_sft.py` | — | ✓ | ✓ |
| `src_llm/llm_compare.py` | — | — | —（无本地模型） |

## 验证方法

```bash
conda activate py312
cd src
python -c "from transformers import BertTokenizer; t = BertTokenizer.from_pretrained('bert-base-chinese'); print(f'OK: vocab={len(t)}')"
cd ../src_llm
python -c "from transformers import AutoTokenizer; t = AutoTokenizer.from_pretrained('Qwen/Qwen2-0.5B-Instruct', trust_remote_code=True); print(f'OK')"
```

首次运行会从 HF 下载到 `M:\huggingface_cache`，后续秒级加载。

## 注意事项

- **不要删 `--bert_path` / `--model_path` 参数**：学生可能需要指定本地路径（如 `hfl/chinese-roberta-wwm-ext`）
- **不要在教案中保留 `pretrain_models/` 路径引用**：改为 "从 HF 缓存自动加载 bert-base-chinese"
- **若项目有 `config.py` 集中管理路径**：只改 config.py 一处即可

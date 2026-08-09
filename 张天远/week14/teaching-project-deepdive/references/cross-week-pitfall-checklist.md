# 跨周隐患检查清单

## 必查六项（收到老师初始项目后逐项排查）

| # | 检查项 | 搜什么 | 修复方式 |
|---|--------|--------|---------|
| 1 | pretrain_models 硬编码 | `grep -r "pretrain_models" src/` | 改为 HF 模型 ID（如 `"bert-base-chinese"`） |
| 2 | Path.resolve() 陷阱 | `grep -r "Path.*resolve" src/ src_llm/` | 先判本地存在再 resolve，否则直接传 HF ID |
| 3 | OpenMP 冲突 | 看所有脚本顶部有无 `KMP_DUPLICATE_LIB_OK` | 加 `os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")` |
| 4 | checkpoint 命名碰撞 | 搜 `torch.save` 和 `ckpt_name` | 命名编码 pool+层数+epoch+数据集，默认配置用短名 |
| 5 | matplotlib 云上中文方框 | 搜 `set_title\|set_xlabel\|set_ylabel` 看是否中文 | 改为英文标签（云安全）或加字体降级检测 |
| 6 | 类别不均衡未处理 | 看 CrossEntropyLoss 是否加权、SFT 是否平衡采样 | 至少文档化这是一个教学点 |

## 扩展检查

| # | 检查项 | 说明 |
|---|--------|------|
| 7 | 依赖检测排除 torch/transformers | 云上 `pip install torch` 会破坏 CUDA 兼容性 |
| 8 | 数据集下载走 hf-mirror | `download_data.py` 里设 `HF_ENDPOINT=hf-mirror.com` |
| 9 | cloud_run_all.sh 不自动关机 | 增量实验场景，结尾只列 cp 命令 |
| 10 | 多数据集覆盖 | 所有实验方法必须复制到所有可用数据集 |
| 11 | HF 数据集质量（拼接污染） | 下载后跑 explore_data.py 检查 P95/最长文本，过滤 \t/\n 拼接异常（BQ Corpus 曾发现 15 条 51K 字脏数据） |

## 搜索命令速查

```bash
# 1. pretrain_models 硬编码
grep -rn "pretrain_models" src/ src_llm/ 2>/dev/null

# 2. Path.resolve 陷阱
grep -rn "Path.*\.resolve()" src/ src_llm/ 2>/dev/null

# 3. OpenMP
grep -rn "KMP_DUPLICATE_LIB_OK" src/ src_llm/ 2>/dev/null

# 4. checkpoint 命名
grep -rn "ckpt_name\|ckpt_path.*\.pt" src/ 2>/dev/null

# 5. 中文标签
grep -rn "set_title\|set_xlabel\|set_ylabel" src/ 2>/dev/null | grep -v '[\\x00-\\x7F]'

# 6. 数据质量：搜文本长度检查或 \t/\n 特殊字符
grep -rn "len(sentence\|\\\\t\|\\\\n" src/ 2>/dev/null
grep -rn "p95\|P95\|percentile.*95" src/ 2>/dev/null
```

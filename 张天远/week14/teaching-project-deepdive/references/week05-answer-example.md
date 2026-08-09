# Week05 MyGPT 参考答案 — 实战案例

> 这是「参考答案编写规范」的完整实战示例。每个实验遵循六要素格式。
> 源文件路径：`E:\npl\hub-kzSW\张天远\week05\`

## 实验规模

- 9 个动手实验，全部基于 `config.py`（115行）、`gpt_model.py`（608行）、`preprocess.py`（253行）、`train.py`（479行）、`test.py`（325行）
- 8 个只改 `config.py` 或 `gpt_model.py` 1-2 行，1 个需要训练模型

## 关键行号速查

| 文件 | 行号 | 内容 |
|------|------|------|
| `config.py:66` | `HIDDEN_SIZE = 768` | 模型宽度 |
| `config.py:68` | `NUM_HIDDEN_LAYERS = 12` | Decoder 层数 |
| `config.py:69` | `NUM_ATTENTION_HEADS = 12` | 注意力头数 |
| `config.py:75` | `USE_RMS_NORM = True` | RMSNorm/LayerNorm 开关 |
| `config.py:78` | `MAX_SEQ_LEN = 512` | 训练序列长度 |
| `config.py:84` | `WARMUP_EPOCHS = 1` | Warmup 轮数 |
| `config.py:107` | `GEN_TEMPERATURE = 0.8` | 生成温度 |
| `gpt_model.py:200` | `diagonal=1` | 因果掩码对角偏移 |
| `gpt_model.py:384` | `self.lm_head.dense.weight = self.embeddings.token_embeddings.weight` | Weight Tying |

## 实验分类

| 实验 | 改什么 | 跑什么 | 核心观察 |
|------|--------|--------|---------|
| 1. 缩模型 | config.py 3 行 | `python gpt_model.py` | 参数量 ~102M → ~25M |
| 2. 改序列长度 | config.py 1 行 | `python preprocess.py` | chunk 数翻倍 |
| 3. 观察 Embedding | gpt_model.py 插入代码 | `python gpt_model.py` | token_emb vs pos_emb 数值差异 |
| 4. 破因果掩码 | gpt_model.py 1 行 | `python gpt_model.py` | 位置 0 输出 → NaN |
| 5. RMSNorm→LayerNorm | config.py 1 行 | `python gpt_model.py` | 参数量 +18K |
| 6. 取消 Weight Tying | gpt_model.py 注释 1 行 | `python gpt_model.py` | 参数量 +16.2M |
| 7. 关 Warmup | config.py 1 行 | `python train.py --combined` | loss 剧烈震荡 |
| 8. Temperature 三档 | config.py 1 行 × 3 次 | `python train.py --combined --resume ...` | 贪心重复 / 适中通顺 / 狂乱断裂 |
| 9. Epoch 5 vs 20 | 两个 checkpoint | `python test.py --eval-only` | PPL↓ 但 Distinct-1↓ |

完整答案见：`E:\npl\hub-kzSW\张天远\参考答案-动手实验与自查任务.md`（第 324-720 行）

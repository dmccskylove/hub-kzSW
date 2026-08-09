# 手写训练/推理脚本两个高频 Bug

## Bug 1: `.detach()` 缺失 → `Can't call numpy() on Tensor that requires grad`

**场景**：在 `torch.no_grad()` 外部调用 `model.encode().cpu().numpy()`

**症状**：
```
RuntimeError: Can't call numpy() on Tensor that requires grad. Use tensor.detach().numpy() instead.
```

**根因**：`BiEncoder.encode()` 在 eval 模式下仍可能返回 `requires_grad=True` 的 Tensor。

**修复**：
```python
# ❌ 错误
vec = model.encode(**enc).cpu().numpy()

# ✅ 正确
vec = model.encode(**enc).detach().cpu().numpy()
```

**影响脚本**：`two_stage_retrieval.py`、`domain_transfer.py`、任何在 `@torch.no_grad()` 外部调用 `encode()` 的评估代码。

## Bug 2: PairDataset batch key 后缀映射不对称

**场景**：手写训练循环中直接使用 PairDataset 的 batch，但忘记去掉 `_a`/`_b` 后缀。

**症状**：
```
TypeError: BiEncoder.encode() got an unexpected keyword argument 'input_ids_a'
```

**根因**：PairDataset 返回 `input_ids_a`、`attention_mask_a` 等带后缀的 key，但 `model(enc_a, enc_b)` → `encode(**batch_a)` 期望 `input_ids`、`attention_mask` 等无后缀 key。

**修复**：
```python
# ❌ 错误——直接用 batch 字典
enc_a = {k: v.to(device) for k, v in batch.items() if k in ("input_ids_a","attention_mask_a","token_type_ids_a")}
emb_a, emb_b = model(enc_a, enc_b)

# ✅ 正确——显式映射去后缀
enc_a = {}
for k in ("input_ids_a", "attention_mask_a", "token_type_ids_a"):
    if k in batch:
        enc_a[k.replace("_a", "")] = batch[k].to(device)
enc_b = {}
for k in ("input_ids_b", "attention_mask_b", "token_type_ids_b"):
    if k in batch:
        enc_b[k.replace("_b", "")] = batch[k].to(device)
emb_a, emb_b = model(enc_a, enc_b)
```

**影响脚本**：`data_scale_ablation.py`、任何不通过 `train_biencoder.py` 而是自己写训练循环的脚本。

## Bug 3: 逐条 Python 循环调 GPU → GPU 利用率极低

**场景**：CrossEncoder 精排时，对每个候选逐个调用 tokenizer + model，而非批量输入。

**症状**：GPU 利用率 < 10%，训练/推理极慢。LCQMC 两阶段检索 43 万次 GPU 调用需要 60+ 分钟。

**根因**：`tokenizer()` 和 `model()` 都接受批量输入（`tokenizer(list_of_strs, ...)`），但代码中写成 `for cand in candidates: tokenizer(q, cand); model(...)`。

**修复**：
```python
# ❌ 错误——43 万次 GPU 调用
for cand in candidates:
    enc = tokenizer(query, cand, ...)
    scores.append(model(**enc).item())

# ✅ 正确——一次批量前向
s1_list = [query] * len(candidates)
enc = tokenizer(s1_list, candidates, ...)
probs = F.softmax(model(**enc), dim=-1)[:, 1].tolist()  # ~100x 加速
```

**影响脚本**：`two_stage_retrieval.py`（`rerank_with_crossencoder` 函数）、任何调用 CrossEncoder 的评估代码。

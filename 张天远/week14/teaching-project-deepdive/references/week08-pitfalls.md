# Week08 文本匹配 — 踩坑记录与通用模式

## 1. CrossEncoder 批量推理（通用加速模式）

**问题**：逐条 Python 循环调用 CrossEncoder = O(N×K) 次 GPU 调用，极端低效。
```python
# ❌ 慢：每对句子一次 GPU 调用，4316×100 = 43 万次
for s1, s2 in pairs:
    enc = tokenizer(s1, s2, ...)
    logits = model(**enc)
```

**修复**：tokenizer 接受 list 参数，一次 tokenize 所有 pair → 一次 forward。
```python
# ✅ 快：4316 次 GPU 调用，~100x 加速
s1_list = [query] * len(candidates)
enc = tokenizer(s1_list, candidates, ...)
logits = model(**enc)          # [N, 2]
probs = F.softmax(logits, dim=-1)[:, 1]  # [N]
```
适用于任何 Reranker / 精排场景。

## 2. Dataset batch key 映射陷阱

**问题**：`PairDataset` 返回 `input_ids_a` / `input_ids_b` 等带后缀的 key，但 `model.forward()` 期望 `input_ids`（无后缀）。

**错误做法**：
```python
# ❌ 直接传 dict，key 后缀不匹配
enc_a = {k: v.to(device) for k, v in batch.items() if k.endswith('_a')}
model(enc_a, enc_b)  # → TypeError: unexpected keyword argument 'input_ids_a'
```

**正确做法**：
```python
# ✅ 显式去后缀
enc_a = {}
for k in ("input_ids_a", "attention_mask_a", "token_type_ids_a"):
    if k in batch:
        enc_a[k.replace("_a", "")] = batch[k].to(device)
```

## 3. `.detach()` 陷阱

**问题**：在非 `@torch.no_grad()` 上下文中，`model.encode()` 输出的 tensor requires_grad=True，直接 `.cpu().numpy()` 报错。

```python
# ❌
q_vec = model.encode(**enc).cpu().numpy()  # RuntimeError

# ✅
q_vec = model.encode(**enc).detach().cpu().numpy()
```

## 4. 中文字体全局注册（matplotlib）

**问题**：单靠 `FontProperties` 逐元素设字体，matplotlib 默认字体仍会报警。
**修复**：`fontManager.addfont()` + 全局 `rcParams` 一次性解决。

```python
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 找到中文字体
candidates = [p for p in fm.findSystemFonts() if "msyh" in p.lower()]
if candidates:
    fm.fontManager.addfont(candidates[0])
    plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=candidates[0]).get_name()]
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
```

## 5. 云跑经验

- **不要通过 SSH 跑长时间脚本**：SSH 超时会杀进程。用 `tmux` 或 `nohup`。
- **marker 断点续传**：失败后清 marker 重跑，已完成自动跳过。
- **pkill 杀不干净**：`pkill -f script_name` 可能漏掉子进程，用 `ps aux | grep` 确认后 `kill`。
- **AutoDL python 路径**：`/root/miniconda3/bin/python`，不是裸 `python`。

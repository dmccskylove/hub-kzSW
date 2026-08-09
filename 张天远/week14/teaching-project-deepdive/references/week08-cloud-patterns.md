# Week08 文本匹配 — 云部署与实验模式参考

## 云部署 check-list

1. **`HF_HUB_DISABLE_MMAP=1`** — AutoDL 文件系统不兼容 safetensors 的 mmap
2. **`HF_ENDPOINT=https://hf-mirror.com`** — 国内镜像下载模型
3. **不重装 torch/transformers** — 云镜像预装版本绑死 CUDA，pip install torch 是灾难
4. **不指定 conda 环境名** — AutoDL 仅 base conda
5. **增量实验不自动打包关机** — `cloud_run_all.sh` 末尾只列拷贝命令

## cloud_run_all.sh 设计模式

```bash
# marker 断点续传
mark_done() { touch "$MARKER_DIR/$1.done"; }
is_done()  { [[ -f "$MARKER_DIR/$1.done" ]]; }

run_step() {
    local id="$1"; local desc="$2"; shift 2
    if is_done "$id"; then skip; return 0; fi
    if "$@"; then mark_done "$id"; else echo "失败——跳过"; fi
}

# 消融前存档核心 checkpoint
cp -n outputs/checkpoints/biencoder_cosine_best.pt outputs/checkpoints/biencoder_cosine_best_core.pt
# 消融后再恢复
cp outputs/checkpoints/biencoder_cosine_best_core.pt outputs/checkpoints/biencoder_cosine_best.pt
```

## checkpoint 命名防碰撞

默认配置保持短名（兼容 `compare_methods.py` 默认路径），非默认自动加后缀：

```python
_pool_tag = f"_{args.pool}" if args.pool != "mean" else ""
_layer_tag = f"_L{args.num_hidden_layers}" if args.num_hidden_layers != 4 else ""
ckpt_name = f"biencoder_{args.loss}{_pool_tag}{_layer_tag}_best.pt"
```

## LCQMC 数据规模消融

238K 训练对，五档消融（1K/5K/10K/50K/100K），每档重新初始化和训练。需要注意：
- PairDataset 返回的 batch key 带 `_a`/`_b` 后缀，自定义训练循环必须手动 `k.replace("_a","")` 映射
- 每档训练完成后 `eval_biencoder()` 在验证集上搜索阈值

## 两阶段检索的性能陷阱

修复前：
```python
def rerank_with_crossencoder(..., candidates):
    for s1, s2 in pairs:                    # 逐条 Python 循环
        enc = tokenizer(s1, s2, ...)        # 每次 1 对
        logits = model(**enc)               # 每次 1 次 GPU 调用 = 43 万次
```

修复后：
```python
def rerank_with_crossencoder(..., candidates):
    s1_list = [query] * len(candidates)
    enc = tokenizer(s1_list, candidates, ...)  # 一次 100 对
    logits = model(**enc)                      # 一次 GPU 调用 = 4316 次
```

## 云上中文 matplotlib

字体检测必须显式排除 `SimSun-ExtG`（覆盖不全），优先级 `msyh > simhei > simsun`：
```python
font_name = fp.get_name()
fm.fontManager.addfont(candidates[0])
plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams.get('font.sans-serif', [])
plt.rcParams['font.family'] = 'sans-serif'
```
不要用 `bbox_inches='tight'`——云上 Linux 会导致图片爆炸。用 `subplots_adjust(top=0.85)`。

## 相关参考

- `references/cloud-checkpoint-safety.md` — ★必读：5 条强制检查项 + 污染链分析
- `references/common-script-bugs.md` — 手写脚本高频 Bug（detach、key 映射、逐条循环）

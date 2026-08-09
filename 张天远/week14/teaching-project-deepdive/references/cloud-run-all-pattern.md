# 云端全实验跑批脚本模式

## 适用场景
Week03-08 NLP 课程项目——云端 GPU 一次性跑完所有实验，支持中断恢复和增量实验。

## 核心模板

### 1. Marker 断点续传
```bash
MARKER_DIR="$PROJ_DIR/markers"
mark_done() { touch "$MARKER_DIR/$1.done"; }
is_done()  { [[ -f "$MARKER_DIR/$1.done" ]]; }

run_step() {
    local id="$1"; local desc="$2"; shift 2
    if is_done "$id"; then skip; return 0; fi
    if "$@"; then mark_done "$id"; else echo "✗ 失败 — 跳过，继续"; fi
}
```

### 2. 优雅中断
```bash
trap 'echo "[!] 收到中断，当前实验未完成，下次从这继续。"' INT TERM
# 不要 set -e——单个实验失败不应终止整个脚本
set -o pipefail
```

### 3. 依赖检测——不重装 torch
```bash
python -c "
# 仅检测轻量纯 CPU 包，torch/transformers 用云镜像预装版
pkg_to_import = {'scikit-learn':'sklearn','matplotlib':'matplotlib',
                 'tqdm':'tqdm','peft':'peft','datasets':'datasets','faiss-cpu':'faiss'}
# 注意：scikit-learn → import sklearn（不能用 replace('-','_')）
missing = []
for pkg, mod in pkg_to_import.items():
    try: __import__(mod)
    except ImportError: missing.append(pkg)
if missing:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)
"
```

### 4. 环境变量
```bash
export HF_HUB_DISABLE_MMAP=1     # AutoDL 文件系统不兼容 safetensors mmap
export HF_ENDPOINT=https://hf-mirror.com  # 国内镜像
# 不要 conda activate py312 —— 云上只有 base conda
```

### 5. 消融前存档核心 checkpoint
消融实验（epoch/margin/pool）会覆盖默认 checkpoint 名。在核心实验和消融之间插入存档步骤：
```bash
run_step "archive_core" "存档核心 checkpoint" bash -c '
for ckpt in biencoder_cosine_best.pt crossencoder_best.pt; do
    cp -n "outputs/checkpoints/$ckpt" "outputs/checkpoints/${ckpt%.pt}_core.pt"
done
'
```

### 6. 跨数据集 checkpoint 命名
```bash
# 每个数据集跑完后立即 cp 到带数据集后缀的唯一名
run_step "lcqmc_biencoder" "LCQMC BiEncoder" bash -c '
python src/train_biencoder.py --data_dir data/lcqmc --epochs 3 && \
cp outputs/checkpoints/biencoder_cosine_best.pt outputs/checkpoints/biencoder_cosine_lcqmc_best.pt && \
cp outputs/logs/biencoder_cosine_log.json    outputs/logs/biencoder_cosine_lcqmc_log.json
'
```

### 7. 混合训练（跨数据集微调）
```bash
run_step "hybrid_train" "LCQMC 预训 → AFQMC 微调" bash -c '
# Step 1: 大数据预训练
python src/train_biencoder.py --data_dir data/lcqmc --epochs 2 && \
cp outputs/checkpoints/biencoder_cosine_best.pt outputs/checkpoints/biencoder_lcqmc_pretrain.pt

# Step 2: 加载预训权重，小数据微调
python src/train_biencoder.py --data_dir data/afqmc --epochs 1 \
    --resume_from outputs/checkpoints/biencoder_lcqmc_pretrain.pt && \
cp outputs/checkpoints/biencoder_cosine_best.pt outputs/checkpoints/biencoder_hybrid_best.pt
'
```

### 8. 结尾——不自动关机
```bash
echo "增量结果拷贝到 autodl-fs："
echo "  cp -r outputs/checkpoints/ /root/autodl-fs/text_match_checkpoints/"
echo "  cp -r outputs/logs/       /root/autodl-fs/text_match_logs/"
# 不要 shutdown -h now——增量实验场景只需手动 cp
```

## 已知踩坑

| 坑 | 根因 | 修复 |
|----|------|------|
| `conda activate py312` 失败 | 云上只有 base conda | 删掉，用默认 python |
| `pip install torch` 破坏 CUDA | 云镜像 torch 版本绑死 CUDA | 依赖检测跳过 torch |
| `scikit-learn` import 检测失败 | `replace('-','_')` 生成 `scikit_learn` | 显式 mapping → `sklearn` |
| safetensors mmap 报错 | AutoDL 文件系统限制 | `export HF_HUB_DISABLE_MMAP=1` |
| checkpoint 被消融覆盖 | 非默认配置（epoch/margin）不在 checkpoint 名中 | 核心实验后存档 + 消融后 cp 到唯一名 |

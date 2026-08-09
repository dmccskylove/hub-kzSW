# 云上运行中修复脚本 Bug 的标准流程

## 场景

cloud_run_all.sh 正在运行，某个实验因代码 bug 失败被 marker 跳过。如何在不停机的情况下修复并补跑？

## 流程（5 步）

### 1. 本地定位 + 修复 + 验证

```bash
# 在本地复现错误
python src/xxx.py ... 2>&1  # 获取完整错误栈

# 修改代码
# 验证修复
python src/xxx.py ... 2>&1  # 确认无报错
```

### 2. scp 上传到云端

```bash
scp -P <port> src/xxx.py root@host:/root/autodl-tmp/text_match/src/
```

### 3. 云上验证修复

```bash
ssh -p <port> root@host "cd /root/autodl-tmp/text_match && /root/miniconda3/bin/python src/xxx.py ..."
# 注意：AutoDL 上 python 路径是 /root/miniconda3/bin/python，不是默认 PATH 中的
```

### 4. 清除失败标记 + 补跑

```bash
rm -f markers/<failed_marker>.done
# 如果 cloud_run_all.sh 仍在运行，自动补跑
# 如果已结束，重新运行 cloud_run_all.sh（marker 机制自动跳过已完成）
```

### 5. 补跑的 3 种模式

| 模式 | 命令 | 适用场景 |
|------|------|---------|
| 单实验 | 直接 `python src/xxx.py ...` | 只需补 1-2 个 |
| marker 补跑 | `rm markers/xxx.done && bash scripts/cloud_run_all.sh` | 需要完整 pipeline 上下文 |
| tmux 手动 | `tmux new -s rerun` → `python src/xxx.py` | 需要长时间运行 + 断开 SSH |

## 云上 Python 路径

AutoDL 云镜像的 conda base 环境在 `/root/miniconda3/bin/python`，不在默认 PATH 中。

```bash
# ❌ 直接调用（找不到）
python src/xxx.py

# ✅ 完整路径
/root/miniconda3/bin/python src/xxx.py
```

## 常见云上环境问题

| 问题 | 检查方法 | 修复 |
|------|---------|------|
| torch 版本不对 | `python -c "import torch; print(torch.__version__)"` | 不重装 torch，云镜像预装绑死 CUDA |
| 缺 light-weight 包 | `import sklearn/matplotlib/peft/datasets/faiss` | `pip install scikit-learn matplotlib peft datasets faiss-cpu` |
| HF 模型下载慢 | 检查 `HF_ENDPOINT` | `export HF_ENDPOINT=https://hf-mirror.com` |
| AutoDL safetensors mmap 报错 | OSError on model load | `export HF_HUB_DISABLE_MMAP=1` |

# 跨脚本 Checkpoint 命名一致性

## 问题

当多个脚本通过自动发现机制引用 checkpoint 时（如 `domain_transfer.py` 按数据集名拼接路径），checkpoint 命名不一致会导致静默失败。

## 实例

`domain_transfer.py` 用 `f"biencoder_cosine_{src}_best.pt"` 查找 checkpoint（`src` = 数据集目录名）。

但 `cloud_run_all.sh` 中 BQ 实验用 `cp` 写成了 `biencoder_cosine_bq_best.pt`（省略了 `_corpus`），而数据集目录名是 `bq_corpus` → 找不到。

## 规则

1. **Checkpoint 存档命名 = 数据集目录名**。不要缩写（`bq` → `bq_corpus`，`lcqmc` → `lcqmc`）
2. **多数据集项目优先用完整目录名**，因为 `--data_dir` 的值就是目录名，保持一致
3. **训练脚本自身的 checkpoint 命名**可以用短名（默认配置简化），但 `cloud_run_all.sh` 中 `cp` 存档时必须用完整目录名

## 自查方法

在 `cloud_run_all.sh` 中搜索 `cp outputs/checkpoints/`，检查目标文件名是否与 `--data_dir` 的值一致：
```bash
grep "cp.*checkpoints.*best.pt" scripts/cloud_run_all.sh | grep -v "^#"
```

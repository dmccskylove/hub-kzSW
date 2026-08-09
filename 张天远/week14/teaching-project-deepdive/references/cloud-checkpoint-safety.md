# Cloud Run — Checkpoint 安全强制检查清单

> Week08 核心教训：消融实验静默污染核心 checkpoint → 后续 7 个实验拿到错误模型。

## 五条强制检查项

每次编写或审阅 `cloud_run_all.sh` 时，逐项打勾：

- [ ] 1. **每个消融实验后是否 `cp _core.pt → best.pt` 恢复核心？**
  - margin/epoch/pool 消融都会覆盖核心同名文件
  - 缺失恢复 = 后续所有实验静默拿到错误模型
  - 示例：`python src/train_biencoder.py --margin 0.1 && cp log → margin01_log.json && cp _core.pt → best.pt`

- [ ] 2. **跨数据集实验后 checkpoint 是否重命名加数据集后缀？**
  - BQ/LCQMC 训练后必须 cp 到 `_bq_corpus`/`_lcqmc` 版本
  - 否则 `biencoder_cosine_best.pt` 被覆盖为非 AFQMC 模型
  - 跨数据集训练后也应恢复核心 AFQMC checkpoint

- [ ] 3. **`run_step` 内 `&&` 链中的 cp 是否在训练成功后才执行？**
  - `&&` 确保只有训练成功（exit 0）才执行后续 cp
  - 绝不使用 `;` 分隔（会无条件执行 cp，训练失败时复制旧数据）

- [ ] 4. **新增脚本是否已 scp 到云上？**（先本地改，再上云）

- [ ] 5. **train_biencoder.py / train_crossencoder.py 是否最新版？**
  - 新增参数（如 `--hard_neg online`）需要新版脚本
  - 云上旧版会静默忽略未知参数或报 unrecognized argument

## 污染链示例

```
核心训练(step 3-5) → archive(step 6) → compare/badcase(step 7)
                                              ↓ 正常——在消融前完成
消融开始(step 8-14):
  margin=0.1 (step 13): OVERWRITE biencoder_cosine_best.pt ← 污染开始
    ❌ cp log → margin01_log.json
    ❌ 未恢复 core！
  margin=0.5 (step 14): OVERWRITE biencoder_cosine_best.pt
    ❌ 同上
扩展实验(step 15+):
  two_stage AFQMC → 加载 margin=0.5 模型 ×
  faiss_demo AFQMC → 同上 ×
  domain_transfer AFQMC行 → 同上 ×
  hard_neg_mining → 同上 ×
```

## 修复模式

```bash
# 消融实验的正确模式
python src/train_biencoder.py --margin 0.1 --epochs 3 && \
cp outputs/logs/biencoder_cosine_log.json outputs/logs/biencoder_cosine_margin01_log.json && \
cp outputs/checkpoints/biencoder_cosine_best_core.pt outputs/checkpoints/biencoder_cosine_best.pt
#                                        ↑ 立即恢复核心

# 跨数据集实验的正确模式
python src/train_biencoder.py --data_dir data/lcqmc --epochs 3 && \
cp outputs/checkpoints/biencoder_cosine_best.pt outputs/checkpoints/biencoder_cosine_lcqmc_best.pt && \
cp outputs/logs/biencoder_cosine_log.json outputs/logs/biencoder_cosine_lcqmc_log.json && \
cp outputs/checkpoints/biencoder_cosine_best_core.pt outputs/checkpoints/biencoder_cosine_best.pt
#                                        ↑ 恢复 AFQMC 核心
```

## 事后排查方法

当怀疑 checkpoint 被污染时：
1. 检查 `biencoder_cosine_best.pt` 的 epoch 数和 val_f1 是否与 `_core.pt` 一致
2. 对比受影响的实验日志——如果某个实验的 F1 与核心差太多但无明显报错，可能是污染
3. 用 `rerun_failed.sh` 模式：清理标记 → 恢复核心 → 重跑

## 相关文件

- `scripts/cloud_run_all.sh` 头部含完整检查清单
- `scripts/rerun_failed.sh` 模板

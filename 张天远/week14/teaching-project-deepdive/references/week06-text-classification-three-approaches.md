# Week06：文本分类三方案对比 — 实验参考

## 实验清单

| 实验 | 变量 | 配置 | 结果 |
|------|------|------|------|
| 池化策略 | pool={cls,mean,max} | epochs=3, batch=16 | mean 57.32% > cls 56.81% > max 56.41% |
| Loss 类型 | loss_type={plain,balanced,soft,focal,freeze} | epochs=3, pool=cls | Focal 0.5724 最高, 加权小类 Recall 最好 |
| 加权消融 | 对比普通 vs 加权 Recall | compare_class_weight.py | 证券 +0.444, 国际 -0.165 |
| LoRA r | r={4,8,16,32} | 5K 数据, 3 epochs | r=8 57.0% 最优, r>=16 下降 |
| 全量微调 | full_ft vs LoRA | 5K 数据, 3 epochs | 全量 55.0% < LoRA 57.0% |
| 零样本 | parse_prediction 优化 | Qwen2-0.5B | 原始 36% → 同义词优化后 48% |
| Few-shot | 加示例到 prompt | Qwen2-0.5B, k=1~3 | 全部低于零样本基础线 |

## 关键发现

1. **池化策略**：mean > cls（反直觉）——短文本（22 字）上每个词都重要，平均优于 [CLS] 摘要
2. **Focal Loss**：val_acc 和 Macro F1 双料最高（0.5724/0.5613），适合边界模糊的分类
3. **加权方案**：小类 Recall 最佳（证券 0.622），但国际类被牺牲 -0.165
4. **LoRA r=8**：最优，r≥16 过拟合下降（53.5%→57.0%→54.5%→55.0%）
5. **全量微调**：500 倍参数（494M vs 1.1M）但准确率更低（55% vs 57%）
6. **零样本**：瓶颈在解析器不在模型——加 60 个同义词从 36% 到 48%
7. **Few-shot**：对 0.5B 小模型不 work，示例格式污染输出

## 工程坑

- `Path(args.model_path).resolve()` 把 HF 模型名变成本地路径 → 直接用字符串
- PowerShell 中文路径编码问题 → 脚本里不写 cd，手动切目录
- 混淆矩阵 PNG 被覆盖 → 每次评估后 Copy-Item 重命名
- 云端 `trust_remote_code` 的 `generate.py` 不受 HF 镜像影响 → 本地上传全模型

## 本地 vs 云端

| | 本地 | 云端 |
|--|------|------|
| GPU | GTX 1080 Ti (11GB) | RTX 4090D (24GB) |
| 适用 | BERT 微调, LoRA 训练 | 全量微调, 大规模实验 |
| 注意 | 峰值 <8GB 才安全, DataLoader num_workers=0 | AutoDL, 4090D 参考 |

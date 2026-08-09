# Week06 Loss 对比实验设计方案

## 说明

在 BERT 文本分类项目中，四种 loss 类型在 TNEWS（15 类，极不均衡）上的实测结果。此设计模式可复用于任何需要对比训练策略的任务。

## 实验目标

| Loss 类型 | 设计意图 | 预期效果 |
|-----------|---------|---------|
| plain | 基线，所有样本等权重 | 大类准确率高，小类丢 |
| balanced | 硬加权（inverse frequency） | 小类 recall 大幅提升，大类有牺牲 |
| soft | sqrt 平滑加权 | 温和折中，不过度偏袒小类 |
| focal (gamma=2.0) | 自动聚焦难分样本 | 对边界样本聚焦，不依赖手动权重 |
| plain + freeze_bert | 两阶段训练，仅训分类头 | 验证分类头容量是否足够 |

## 实测结果

| Loss 类型 | val_acc | Macro F1 | 证券 Recall |
|-----------|:-------:|:--------:|:----------:|
| plain | 0.5681 | 0.5480 | 0.178 |
| balanced | 0.5617 | **0.5575** | **0.622** |
| soft (sqrt) | 0.5632 | 0.5574 | 0.600 |
| focal (gamma=2) | 0.5276 | 0.4932 | 0.000 |
| freeze (11.5K) | 0.5276 | 0.4932 | — |

## 结论

1. **balanced 和 soft 都可取**——Macro F1 接近但高于 plain，小类大幅受益。balanced 偏向小类更多，soft 更温和。
2. **Focal Loss 在此任务上不适用**——259 条（0.5%）的极端稀缺类别下，Focal Loss 的自动聚焦机制失效。它需要模型先有一定基线能力才能判断"哪些样本难分"，但小类本身样本不够建立基线。
3. **两阶段冻结训练也失败**——BERT 的 102M 冻结参数 + 11.5K 分类头 = 学不动 15 类分类任务。说明 BERT 需要微调让隐层特征适配分类体系。

## 可复用模式

```powershell
# train.py 已支持 --loss_type {plain,balanced,soft,focal}
# 一次跑完三个新实验的模板
python src/train.py --loss_type soft
python src/train.py --loss_type focal
python src/train.py --loss_type plain --freeze_bert
```

> train.py 通过 `build_criterion()` 工厂函数分发 loss 类型，新增 loss 类型只需扩展该函数。文件名自动标记 loss_type（`best_cls_soft.pt`、`train_log_soft.json`），互不覆盖。

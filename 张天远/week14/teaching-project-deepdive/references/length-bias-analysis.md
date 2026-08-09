# Length Bias 分析模式

Week08 文本匹配中发现的分析技巧。

## 什么是 Length Bias

数据集中如果正例对的句子长度差显著小于负例对，模型可能学到"长度接近 = 相似"的捷径，而非真正的语义匹配。

## 检测方法

在 `explore_data.py` 中统计正/负样本的长度差：
```python
pos_diff = [abs(len(r["sentence1"]) - len(r["sentence2"])) for r in rows if r["label"] == 1]
neg_diff = [abs(len(r["sentence1"]) - len(r["sentence2"])) for r in rows if r["label"] == 0]
```

- 正例长度差均值远小于负例 → **存在 length bias**
- 两者接近 → 无 length bias

## 验证方法

按 `|len(s1) - len(s2)|` 分桶评估 F1：

| 桶 | 样本数 | F1 |
|----|--------|----|
| 0-1 字差 | N1 | F1_1 |
| 2-3 字差 | N2 | F1_2 |
| 4-6 字差 | N3 | F1_3 |
| 7+ 字差 | N4 | F1_4 |

- F1 随长度差单调下降 → 模型在偷学捷径
- F1 各桶接近 → 模型学到语义

## Week08 实测

| 数据集 | 正例长度差 | 负例长度差 | bias? |
|--------|:---:|:---:|:---:|
| AFQMC | 4.2 | 4.4 | ✅ 无 |
| LCQMC | 1.5 | 2.7 | ⚠️ 有 |

LCQMC 的 bias 为报告提供了天然控制变量：与无 bias 的 AFQMC 对比，看 bias 是否导致 F1 虚高。

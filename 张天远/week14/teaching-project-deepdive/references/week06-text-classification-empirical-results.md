# Week06 文本分类三种方案 — 实测数据

## 项目描述
TNEWS 数据集（15 类新闻标题）上对比 BERT 微调 / LLM 零样本 / SFT+LoRA / 全量微调。

### 7. 五种 Loss 函数全对比\n- **Focal Loss (gamma=2): val_acc=0.5724, Macro F1=0.5613 (双料最高)**\n- 普通 (plain): 0.5681 / 0.5480\n- Soft 加权 (sqrt): 0.5632 / 0.5574\n- 硬加权 (balanced): 0.5617 / 0.5575\n- 两阶段冻结 (freeze): 0.5276 / 0.4932\n- **Focal 不牺牲大类前提下提升整体**（科技 0.514），但证券 recall 0.38 < 加权方案 0.62\n- Freeze 冻结 BERT 后 11.5K 参数不够学 — 证券 recall=0.00, val_acc=52.8%\n\n### 8. 加权 Loss 消融明细\n- 国际类 Recall 被牺牲最多: 0.592 → 0.428 (-0.165)，甚至超过科技类 (-0.075)\n- 原因：国际与财经/科技的边界模糊，加权后模型从这些"边界类"抽注意力给稀缺类\n- Macro F1 +0.01 vs Accuracy -0.006 — "公平的代价"\n\n### 9. 零样本解析器可以扩展到 Few-Shot\n- classify_llm.py 新增 `--few_shot` 和 `--few_shot_k` 参数\n- 从训练集每类选 k 条示例，追加到 System Prompt 中\n- Few-Shot 预期能进一步缩小 48%→BERT 57% 的差距\n\n## 关键实证发现

### 1. 池化策略：mean > cls（反直觉）
- mean: 57.32%
- cls: 56.81%
- max: 56.41%
- **原因**：短文本（~22 字）上所有 token 都承载信息，mean 比单个 [CLS] 稳定
- **教案教训**：不要指导性断言 "cls 最适合"，应在教案中标注 "预期" 并在实验后用实测数据修正

### 2. 加权 Loss 效果显著
- 证券 Recall: 0.18 → 0.62 (+0.444)
- 科技 Recall: 0.52 → 0.45 (-0.075)
- Macro F1: 0.548 → 0.558
- Soft 加权（sqrt 平滑）：证券权重 13.81→3.73，Recall 0.60（tradeoff 更温和）

### 3. 零样本解析器是瓶颈
- 原始 parse_prediction 只匹配 15 个硬编码类别名 → 36% acc, 29% unparseable
- 加 60+ 同义词映射 → 48% acc, 1.5% unparseable
- Qwen2-0.5B 输出了 "房地产"(→房产)、"武器"(→军事)、"政治"(→国际) 等有效但不在白名单中的词
- **课件关键洞察**：系统的瓶颈不在模型能力，在解析器设计

### 4. LoRA r 消融：r=8 最优，r>=16 过拟合
- r=4: 53.5% (容量不足)
- **r=8: 57.0% (最优)**
- r=16: 54.5%
- r=32: 55.0%
- **意义**：5K 数据下 r=8 是甜点，更大 r 导致过拟合

### 5. 全量微调 < LoRA
- 全量微调: 55.0% (494M params, 100%)
- LoRA r=8: 57.0% (1.1M, 0.22%)
- 5K 数据 + 494M 参数 → 过拟合（参数是数据的 98800 倍）
- LoRA 低秩约束 = 天然正则化 → 小数据下优于全量

### 6. BERT 过拟合（3 epoch 到顶）
- epoch 2: train 62.2%, val 56.8%（最优）
- epoch 3: train 71.8%, val 56.7%（过拟合）
- 多出的 10% train_acc = 背答案

## 云端 vs 本地

| 环境 | GPU | BERT 3 epoch | LoRA 3 epoch |
|------|-----|-------------|-------------|
| 本地 | GTX 1080 Ti 11GB | ~9 min | ~3 min/epoch |
| 云端 | RTX 4090D 24GB | ~3 min/epoch | ~2 min/epoch |

## 已知坑位

1. `train_sft.py` / `evaluate_sft.py` 中 `str(Path(args.model_path).resolve())` 会把 HF 模型名转成错误本地路径 → 直接传字符串
2. Cloud Linux PNG 无中文 → 评估图在本地重新 `python evaluate.py` 生成
3. PowerShel `\run.ps1` 特殊 Unicode 字符导致 ParseException → 脚本内只用 ASCII

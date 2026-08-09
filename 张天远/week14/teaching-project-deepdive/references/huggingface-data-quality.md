# HuggingFace 数据集质量检查

> Week08 核心教训：BQ Corpus 含 15 条污染样本（多行拼接至单字段，最长 51,842 字），导致 CrossEncoder 截断噪声。

## 触发条件

任何 NLP 项目下载 HuggingFace 数据集后，在训练/评估前必须跑此检查。

## 三步检查法

### 1. 文本长度检查

```python
def check_max_lengths(dataset, text_cols=["sentence1", "sentence2"]):
    for col in text_cols:
        lengths = [len(item[col]) for item in dataset]
        print(f"{col}: min={min(lengths)}, max={max(lengths)}, "
              f"P95={np.percentile(lengths, 95)}, P99={np.percentile(lengths, 99)}")
```

### 2. 异常样本人工审查

```python
abnormal = [item for item in dataset 
            if len(item["sentence1"]) > 200 or len(item["sentence2"]) > 200]
# BQ Corpus 发现：15 条样本 sentence2 被 \t 拼接了多行原始数据
```

### 3. 特殊字符/拼接检测

```python
for item in dataset:
    if "\t" in item["sentence1"] or "\t" in item["sentence2"]:
        # 很可能多行数据被拼进单字段
        print(f"WARN: Tab found in {item.get('id', 'unknown')}")
    if "\n" in item["sentence1"] or "\n" in item["sentence2"]:
        print(f"WARN: Newline found in {item.get('id', 'unknown')}")
```

## 修复方法

```python
# 过滤异常样本
clean_dataset = dataset.filter(
    lambda x: len(x["sentence1"]) <= 200 and len(x["sentence2"]) <= 200
)
```

## 已知受污染数据集

| 数据集 | HF ID | 污染条数 | 表现 |
|--------|-------|----------|------|
| BQ Corpus | FinanceMTEB/bq_corpus | 15 | sentence2 被 \t 拼接多行，最长 51,842 字 |

## 对齐教案的影响

- 数据探索章节的 P95/P99 报告不应包含异常样本（会严重扭曲统计）
- 分布式条图/log 尺度图可能因单条超长样本而无法阅读
- 这步必须在 `explore_data.py` 的数据处理区完成，而非事后修补

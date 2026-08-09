# 双数据集 CLI 切换模式

> 当教学项目需要支持两个不同格式的数据集、通过 `--dataset` CLI 参数一键切换时，参考此设计。

## 典型场景

- 主数据集（如 cluener2020）格式为 span annotation
- 练习数据集（如 peoples_daily）格式为 BIO 标签列表
- 需要同一个 `train.py` / `evaluate.py` 支持两者，不破坏原有行为

## 设计原则

1. **向后兼容**：不加 `--dataset` 时行为完全不变
2. **并行 Dataset 类**：不同格式用不同类，不用 if-else 撑大同一个类
3. **工厂函数分发**：`build_dataloaders()` 根据 dataset 名选择 DatasetClass
4. **路径隔离**：checkpoint/log 文件名包含数据集名（非默认时），防止覆盖

## 实现模板

### dataset.py

```python
# 1. 实体类型定义（每个数据集一套）
CLUENER_ENTITY_TYPES = [...]
PEOPLES_DAILY_ENTITY_TYPES = [...]

def get_entity_types(dataset: str) -> list[str]:
    if dataset == "peoples_daily":
        return PEOPLES_DAILY_ENTITY_TYPES
    return CLUENER_ENTITY_TYPES

def get_data_dir(dataset: str) -> Path:
    return ROOT / "data" / dataset

# 2. 标签体系动态生成
def build_label_schema(dataset: str = "cluener2020"):
    entity_types = get_entity_types(dataset)
    labels = ["O"] + [f"{p}-{e}" for e in entity_types for p in ("B", "I")]
    ...

# 3. 两个独立的 Dataset 类
class CluenerDataset(Dataset):        # span 格式
class PeoplesDailyDataset(Dataset):   # BIO 标签格式

# 4. 工厂函数分发
def build_dataloaders(..., dataset: str = "cluener2020"):
    DatasetClass = PeoplesDailyDataset if dataset == "peoples_daily" else CluenerDataset
    train_ds = DatasetClass(...)
```

### train.py / evaluate.py

```python
# --dataset 参数
parser.add_argument("--dataset", type=str, default="cluener2020",
                    choices=["cluener2020", "peoples_daily"])

# 非默认数据集时文件名含数据集名
if args.dataset == "cluener2020":
    run_tag = "crf" if args.use_crf else "linear"
else:
    run_tag = f"{args.dataset}_{'crf' if args.use_crf else 'linear'}"
```

## 踩坑

- `from_pretrained()` 相对路径问题：验证脚本用 `Path(__file__).parent` 构造绝对路径，不要用 `'../pretrain_models/...'`
- HF 缓存路径 vs 本地路径：先用 `Test-Path` 确认本地模型存在，不存在则用模型名让 HF 缓存自动查找

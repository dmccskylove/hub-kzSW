# Python 脚本路径处理陷阱（transformers 项目常见）

## 问题：str(Path(model_path).resolve()) 破坏 HF 模型名

当 `model_path` 是 HuggingFace 模型名（如 `Qwen/Qwen2-0.5B-Instruct`）时：

```python
# 错误写法：Path.resolve() 将 HF 模型名解释为文件路径
model = AutoModelForCausalLM.from_pretrained(
    str(Path(args.model_path).resolve()),  # 变成 C:\Users\xxx\Qwen\Qwen2-0.5B-Instruct
    ...
)
```

```python
# 正确写法：直接传字符串，保留 HF 模型名
model = AutoModelForCausalLM.from_pretrained(
    args.model_path,  # 保留 "Qwen/Qwen2-0.5B-Instruct"
    ...
)
```

## 模式：脚本参数的路径 vs 模型名判断

| 参数值示例 | 是路径还是模型名 | 处理方式 |
|-----------|----------------|---------|
| `E:\models\bert-base-chinese` | 本地路径 | `Path(...).resolve()` |
| `bert-base-chinese` | HF 模型名 | 直接传字符串 |
| `Qwen/Qwen2-0.5B-Instruct` | HF 模型名（带 namespace） | 直接传字符串 |

判断标准：含路径分隔符（`/` 或 `\\`） = 本地路径 → resolve；不含 = HF 模型名 → 直传。

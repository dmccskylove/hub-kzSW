# 文本分类项目已知坑位

## 1. `Path(model_path).resolve()` 把 HF 模型名转成本地路径

**症状**：`from_pretrained('Qwen/Qwen2-0.5B-Instruct')` 报 `OSError: Repo id must use alphanumeric chars`，路径被转成了 `E:\项目\Qwen\Qwen2-0.5B-Instruct`。

**根因**：代码中写了 `str(Path(args.model_path).resolve())`——Python 的 `Path().resolve()` 会将相对路径或含分隔符的字符串解析为完整本地路径。HF 模型名（如 `Qwen/Qwen2-0.5B-Instruct`）被当成了 `Qwen` 子目录下的文件。

**修复**：
```python
# 错误
tokenizer = AutoTokenizer.from_pretrained(str(Path(args.model_path).resolve()))

# 正确 — HF 模型名直接传字符串
tokenizer = AutoTokenizer.from_pretrained(args.model_path)

# 正确 — 本地路径直接传
tokenizer = AutoTokenizer.from_pretrained("/root/models/Qwen2-0.5B-Instruct")
```

**涉及文件**：`train_sft.py`（2 处）、`evaluate_sft.py`（1-2 处）。搜 `str(Path(` 定位。

## 2. HF Hub 镜像不可达

**症状**：云端（AutoDL 等）下载模型时卡在 `HEAD https://huggingface.co/...`，报 `Cannot assign requested address`。

**解决方案**：
```bash
# 方案1：设 HF 镜像
export HF_ENDPOINT=https://hf-mirror.com
# 注意：trust_remote_code=True 的文件不受镜像影响，仍需直连 HF
# 方案2：本地打包模型上传（绕过网络）
tar -czf qwen.tar.gz -C M:/huggingface_cache/hub models--Qwen--Qwen2-0.5B-Instruct
```

## 3. PowerShell 执行多行 `python -c` 失败

**症状**：粘贴带换行和嵌套引号的 `python -c "..."` 命令到 PowerShell 时报解析错误。

**解决方案**：将代码存为 `.py` 文件，然后 `python script.py` 执行。不要试图在 PowerShell 中直接写多行内联 Python。

## 4. Cloud Linux PNG 中文为方框

**症状**：云端 `evaluate.py` 生成的混淆矩阵和消融图中中文显示为方框。

**根因**：Linux 实例缺少中文字体。`evaluate.py` 和 `compare_class_weight.py` 尝试加载 `SimHei`、`Microsoft YaHei`、`PingFang SC` 等字体但均不可用。

**修复**：本地（Windows 系统有中文字体）重新跑评估命令：
```powershell
python src/evaluate.py --pool cls --bert_path bert-base-chinese
python src/compare_class_weight.py --pool cls --bert_path bert-base-chinese
```

## 5. AutoDL `libgomp: Invalid value for environment variable OMP_NUM_THREADS`

**症状**：训练开始时终端打印这个警告。不影响 CUDA 训练。

**根因**：AutoDL 镜像环境变量残留。可忽略。

## 6. 全量微调 Qwen2-0.5B 内存压力

**本地 1080 Ti 11GB**：fp16 可能勉强可跑但高温。建议上云（RTX 4090D 24GB+）。

**云上 2GB cgroup（无卡模式）**：fp32 全量微调 OOM。需带 GPU 的实例。

**云端 fp16 训练**：改写 `dtype=torch.float32` → `dtype=torch.float16` 在 `train_sft.py` 中（搜 `dtype=torch.float32`）。

## 7. `--pool` 参数不接受 checkpoint 名

**症状**：用 `--pool cls_weighted` 传递加权 Loss 的 checkpoint 时，报 `invalid choice: 'cls_weighted' (choose from 'cls', 'mean', 'max')`。

**根因**：`evaluate.py` 的 `--pool` 只接受三种池化策略名（cls/mean/max），`cls_weighted` 是 checkpoint 文件名的一部分，不是池化策略。

**修复**：不要用 `--pool` 加载不同 loss 类型的 checkpoint。用 `--ckpt_path` 直接指定：
```powershell
# 错误
python src/evaluate.py --pool cls_weighted

# 正确
python src/evaluate.py --pool cls --ckpt_path outputs/checkpoints/best_cls_weighted.pt
```

更好：给 `evaluate.py` 加 `--loss_type` 参数（自动拼接 checkpoint 路径），见 `run_loss_experiments.ps1` 的使用方式。

## 8. `evaluate.py` 默认 BERT_PATH 是本地路径而非 HF 模型名

**症状**：`python src/evaluate.py --pool cls` 报 `Repo id must use alphanumeric chars: 'E:\\...\\pretrain_models\\bert-base-chinese'`。

**根因**：`evaluate.py` 中 `BERT_PATH` 默认指向本地 `pretrain_models/bert-base-chinese` 目录，但该目录不存在。模型实际在 HF 缓存中。

**修复**：执行时加上 `--bert_path bert-base-chinese` 覆盖默认值：
```powershell
python src/evaluate.py --pool cls --bert_path bert-base-chinese
```

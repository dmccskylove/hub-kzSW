# Week07 NER 项目实现踩坑速查

## 1. BERT_PATH 不存在 → HFValidationError

**现象**：
```
HFValidationError: Repo id must use alphanumeric chars: 'E:\npl\workspaces\pretrain_models\bert-base-chinese'
```

**根因**：`train.py` 默认 `BERT_PATH` 指向本地不存在的目录，`from_pretrained()` 把它当 HF 模型名校验格式。

**修复**：改为 `BERT_PATH = Path("bert-base-chinese")`，利用 `HF_HOME=M:\huggingface_cache` 自动加载缓存。

**教训**：`from_pretrained()` 传参的两种模式——本地路径用 `Path.resolve()`，HF 模型名用裸字符串，不要混用。优先检查本地路径是否存在再决定用哪种。

## 2. data_dir 命名不匹配

**现象**：
```
FileNotFoundError: data/cluener2020/train.json
```

**根因**：`get_data_dir("cluener2020")` 返回 `data/cluener2020/`，实际目录是 `data/cluener/`。

**修复**：加映射 `dir_name = "cluener" if dataset == "cluener2020" else dataset`。

**教训**：CLI 参数名和目录名不一定相同——用显式映射表而非字符串拼接。

## 3. BERT 和 RoBERTa checkpoint 互相覆盖

**现象**：两个模型在同数据集上的 checkpoint 文件名相同（`best_linear.pt`），后训练的覆盖先训练的。

**根因**：`run_tag` 只含数据集名和模型头（linear/crf），不含模型标识。

**修复**：从 `--bert_path` 自动提取 `model_tag`（"roberta" vs ""），拼入 `run_tag`。最终命名：`best_roberta_linear.pt`、`best_roberta_peoples_daily_crf.pt` 等。

**教训**：不同模型/数据集的产物必须用独立文件名，靠参数自动生成而非手动管理。

## 4. build_local_client() 缺少 return

**现象**：
```
API 调用失败：'NoneType' object has no attribute 'chat'
```

**根因**：`build_local_client()` 创建了 OpenAI 对象但没 `return`，调用方拿到 `None`。

**修复**：加 `return OpenAI(...)` + `--local` CLI flag 在本地和云端 API 之间切换。

## 5. seqeval 未安装

**现象**：`ModuleNotFoundError: No module named 'seqeval'`

**修复**：`pip install seqeval`

## 6. ctx_edit 在大段中文替换时失败

**现象**：`ctx_edit` 对含中文引号、反引号、emoji 的大段 old_string 静默失败或只部分替换。本 session 中尝试用 `ctx_edit` 替换 50+ 行的附录D内容，三次失败后才改用 `execute_code` + raw file I/O。

**回退方案**：
```python
# execute_code 中
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# 定位 → 切片删除/插入 → 写回
new_lines = lines[:delete_start] + lines[delete_end:]
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
```

**教训**：`ctx_edit` 仅用于单行或短段落（<200 字纯 ASCII）的精确替换。大段中文操作直接走 execute_code raw I/O。

## 7. torchcrf 包名陷阱：TorchCRF ≠ pytorch-crf（API 不兼容）

**现象**：
```python
from torchcrf import CRF
CRF(3, batch_first=True)  # TypeError: unexpected keyword argument 'batch_first'
```

**根因**：PyPI 上 `pip install torchcrf` 安装的是 `TorchCRF` 包（大 T 大 C），其 `CRF.__init__()` 只接受 `num_tags` 一个参数。本仓库实际需要的是 `pytorch-crf` 包——`pip install pytorch-crf`，它提供 `torchcrf` 模块（小写），且 `CRF` 支持 `batch_first=True`。

**两个包的对比**：

| pip 装法 | 模块名 | `batch_first` | import 语句 |
|----------|--------|:---:|------|
| `pip install pytorch-crf` | `torchcrf`（小写） | ✅ | `from torchcrf import CRF` |
| `pip install torchcrf` | `TorchCRF`（大写） | ❌ | `from TorchCRF import CRF` |

**修复**：
```bash
pip uninstall TorchCRF -y
rm -f /path/to/site-packages/torchcrf  # 如果有旧的软链接
pip install pytorch-crf --no-deps
python -c "from torchcrf import CRF; c = CRF(3, batch_first=True); print('OK')"
```

**教训**：
1. **PyPI 包名 ≠ import 名**：`pip install torchcrf` 看起来就是你要的，实际装了另一个包。
2. **能 import 不等于 API 兼容**：两个包都有 `CRF` 类，但签名不同。`pip show <pkg>` 查看 `top_level.txt` 确认真正的 import 名。
3. **`--no-deps` 必须加**——见第 8 条，不然 pip 连带覆写 CUDA torch。

## 8. argparse default 陷阱：非 None 默认值使条件判断失效

**现象**：
```python
parser.add_argument("--data_dir", default=str(DATA_DIR))  # DATA_DIR = "data/cluener"
```
然后在 main() 中：
```python
data_dir = Path(args.data_dir) if args.data_dir else dataset_aware_path  # 永远走 if 分支！
```
结果 `--dataset peoples_daily` 时仍然读 `data/cluener/`，加载错误的数据集（KeyError: 'tokens'）。

**根因**：argparse 设了非 `None` 默认值后，`args.data_dir` 永远为真——即使用户期望根据 `--dataset` 自动选择路径，数据集感知的回退逻辑形同虚设。

**修复**：
```python
parser.add_argument("--data_dir", default=None,
                    help="数据目录（默认根据 --dataset 自动选择）")
```

**教训**：需要"用户没传则自动推断"的逻辑时，argparse default 必须设为 `None`。`if args.xxx` 只对 `None`/空串/`False` 为假——一个常量路径永远为真。

## 9. pip install <pkg> 覆盖 CUDA torch 为 CPU 版

**现象**：
```
Uninstalling torch-2.5.1+cu124 → Successfully uninstalled
Installing torch → 2.5.1 (CPU)
```
之后 `torch.cuda.is_available() → False`。

**根因**：`pip install <pkg>` 不加 `--no-deps` 时，pip 解析依赖 `torch>=1.0.0`，发现已有的 `torch 2.5.1+cu124`（从 `pytorch.org/whl/cu124` 安装）不在 PyPI 默认索引中，于是从 PyPI 下载 CPU 版 torch 覆盖。安装中断还可能留下 `~orch` 损坏目录，进一步污染 pip 索引。

**修复**：
1. 始终用 `pip install <pkg> --no-deps`
2. 如果已被覆盖：`pip install torch==2.5.1+cu124 --extra-index-url https://download.pytorch.org/whl/cu124 --force-reinstall --no-deps`
3. 清理残留：`rm -rf site-packages/~orch*`

**教训**：任何依赖 torch 的 pip 包（pytorch-crf、bitsandbytes 等）在已有 CUDA torch 的环境安装时，必须 `--no-deps`。

## 10. AutoDL 只有 base conda

**现象**：`conda activate py312` 静默失败，后续命令照常执行，但 pip/python 实际用的是 base 环境。

**根因**：AutoDL 官方镜像预装 miniconda3 于 `/root/miniconda3`，只有 `base` 环境。本地项目要求的 `py312` 不存在。

**修复**：脚本中去掉 `conda activate py312` 行，或加 `|| true` 容错。base 环境的 python 3.12 已满足所有依赖。

**教训**：云端脚本的环境激活应加容错。本地 conda 环境名不应硬编码在云端脚本中。

## 10. 结果持久化：autodl-fs + 自动关机

**模式**：cloud_run_all.sh 末尾三段——
1. 打包：追加 `outputs/sft_minicpm5_*/` 到 tar
2. 拷贝：`cp ner_all_results_*.tar.gz /root/autodl-fs/`（实例释放后数据不丢）
3. 关机：`sleep 30 && shutdown -h now`（30 秒倒计时，Ctrl+C 可取消）

**教训**：`/root/autodl-tmp/` 随实例释放而删除，`/root/autodl-fs/` 是 AutoDL 的持久文件存储。跑完必须把结果拷到 `autodl-fs` 再关机。

## 12. 模型在云上首次使用但本地未验证 → 全员失败

**现象**：RoBERTa (`hfl/chinese-roberta-wwm-ext`) 在本地从未跑过，直接上云。BERT 的四组实验正常，RoBERTa 的四组全部失败（无日志、无 marker、进程静默退出）。

**可能原因**（因自动关机丢失了终端输出，无法确认）：
- `BertTokenizer.from_pretrained()` 加载 RoBERTa 的 tokenizer 可能产生 shape 不匹配
- 或模型下载时 HF 连接不稳定导致部分文件损坏
- 或无 GPU 时有不同错误路径

**教训**：**云端脚本中的每一个模型/数据集/代码路径，必须先在本地至少跑通一个最小示例**（如 1 epoch + 1 batch 验证）。不能在云上首次验证模型兼容性。

**预防模式**：
```bash
# 本地快速验证每个模型
for model in bert-base-chinese hfl/chinese-roberta-wwm-ext openbmb/MiniCPM5-1B Qwen/Qwen2.5-7B-Instruct; do
    python -c "from transformers import AutoTokenizer, AutoModel; t=AutoTokenizer.from_pretrained('$model'); print('$model: OK', len(t))" || echo "FAIL: $model"
done
```

## 13. 终端输出不保存 → SSH 断开后无法查错

**现象**：cloud_run_all.sh 跑了 3/13 个实验后进程退出，没有 tmux 会话残留，`outputs/logs/` 只有训练日志 JSON，没有终端 stdout/stderr。无法判断 RoBERTa 为什么失败。

**根因**：旧版脚本没有 `tee` 日志保存，`run_step()` 内部错误信息直接输出到终端，SSH 断开或进程退出后全部丢失。

**修复**：在脚本开头加自动 tee 日志：
```bash
LOG_DIR="$PROJ_DIR/outputs/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cloud_run_$(date +%Y%m%d_%H%M).log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "日志文件: $LOG_FILE"
```

**教训**：云端长时间跑批脚本必须有自动日志——`tmux` 不可靠（异常退出后会话消失），`nohup` 需要手动重定向。`exec > >(tee ...)` 一行解决，且日志最终一并打入结果 tar。

## 14. 模型下载列表遗漏新模型

**现象**：`download_models` 步骤只预热了 `bert-base-chinese`、`roberta-wwm-ext`、`Qwen2.5-7B` 三个模型，缺少 `openbmb/MiniCPM5-1B`。MiniCPM5 训练步骤开始时才首次下载，如果此时网络不稳则失败。

**修复**：把所有实验中用到的模型都加入下载预热列表。注意 `download_models` 只下载 tokenizer 验证连通性，实际模型权重在训练时首次 `from_pretrained()` 下载。

## 15. flash 模型搞不定复杂云端环境调试

**模式**：`deepseek-v4-flash` 在需要精确命令输出（如双下划线 `__version__` 被终端渲染吞掉）、多轮环境修复、包名混淆排查（TorchCRF vs pytorch-crf）时反复出错，最终用户切回 `deepseek-v4-pro` 解决问题。

**规则**：涉及云端环境修复、包依赖排查、pip/CUDA/conda 交互的复杂调试任务，不要用 flash 模型。flash 适合简单问答和代码生成，不适合需要保持多轮状态一致性 + 精确命令输出 + 跨平台差异诊断的任务。

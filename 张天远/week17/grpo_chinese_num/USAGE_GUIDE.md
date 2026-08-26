# USAGE_GUIDE.md — GRPO 中文数字转换：代码调用与测试指南

## 1. 环境准备

### 云端（AutoDL 4090D，训练主环境）
```bash
bash cloud/setup_cloud.sh    # 装依赖 + hf-mirror 配置 + 预下载两个模型
```
| 依赖 | 版本 | 用途 |
|------|------|------|
| torch | 镜像自带 2.x+cu126 | 训练框架 |
| transformers | 5.5.3 | 模型加载（与 trl 0.21 兼容问题已由 trl_compat.py 处理） |
| trl | 0.21.0 | GRPOTrainer |
| peft / accelerate / datasets | — | 依赖组件 |

### 本机（1080Ti 11GB，最终验证）
- conda 环境 py312（已有 torch 2.10 + transformers 5.9 + 模型缓存 M:\huggingface_cache）
- 本机只做**验证**（fp16 推理），不需要 trl

## 2. 云端全流程

```bash
# 上传项目（本机执行）
scp -r grpo_chinese_num root@<AutoDL主机>:/root/

# 云端执行（AutoDL 控制台 JupyterLab 终端）
bash cloud/setup_cloud.sh      # 一次性
bash cloud/run_cloud.sh        # probe → 训练 G1~G5 → 评估 → 打包 results.tar.gz
```

**关键提示：probe 后可能需要调整 mix**。先让 run_cloud.sh 跑到 probe 完成
（约 10 分钟），查看 `logs/probe_0.5b.log` 和 `logs/probe_1.5b.log` 的
`loose_informative` 列——把结果贴给灵枢分析，确认各模型训练难度配比
（`run_cloud.sh` 里的 `MIX_0_5B` / `MIX_1_5B`）是否需要调整，
再继续训练段（训练段脚本是顺序执行的，改完重新跑即可，probe 有缓存产物不重复）。

| 参数 | 默认 | 说明 |
|------|------|------|
| `--model` | 0.5b | 0.5b / 1.5b 别名或模型路径 |
| `--think` | 关 | R1 风格 `<think>+<answer>` 格式（格式分 0.1+0.1） |
| `--beta` | 0.0 | KL 系数；0.05 时加载参考模型（G5） |
| `--mix` | 模型默认 | 训练难度配比，如 `L3:0.4,L4:0.4,L5:0.2` |
| `--max_steps` | 300 | 优化步数（每步 = 4 prompt × 8 采样） |
| `--tag` | 必填 | 输出目录后缀：`outputs/<tag>_ckpt/` + `<tag>_train_log.json` |
| `--batch` / `--accum` | 8 / 4 | OOM 时 batch 8→4、accum 4→8 |

## 3. 拉回与本机验证

```bash
# 本机：拉取并解包
scp -r root@<AutoDL主机>:/root/grpo_chinese_num/results.tar.gz "E:/npl/workspaces/npl_tran/grpo_chinese_num/"
cd "E:/npl/workspaces/npl_tran/grpo_chinese_num" && tar xzf results.tar.gz

# 本机验证（1080Ti 用 fp16）：主实验 g4 checkpoint
PYTHONPATH= S:/condaEnvs/py312/python.exe src/probe_baseline.py \
    --model outputs/g4_1.5b_think_ckpt --think --dtype fp16 --out outputs/local_verify_g4.json --seed 42 --quick

# 汇总对比表 + 曲线（自动扫描 outputs/*_probe.json 与 *_train_log.json）
PYTHONPATH= S:/condaEnvs/py312/python.exe src/compare_results.py
```

注意：`PYTHONPATH=` 前缀用于清掉 Hermes 注入的 venv 路径污染，防止 torch
版本错乱（本机 py312 环境标准做法）。

## 4. 单步调试（本机可跑的部分）

```bash
# 转换器单元测试（纯 stdlib，无 GPU 依赖）
PYTHONPATH= S:/condaEnvs/py312/python.exe tests/test_num2cn.py

# 转换器自检打印（关键用例）
PYTHONPATH= S:/condaEnvs/py312/python.exe src/num2cn.py
```

## 5. 作为模块调用（行为验证）

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ckpt = "outputs/g4_1.5b_think_ckpt"   # 或基座 "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(ckpt)
model = AutoModelForCausalLM.from_pretrained(ckpt, dtype=torch.float16, device_map="cuda")

msgs = [
    {"role": "system", "content": "你是一个中文数字转换助手。用户会给你一个阿拉伯数字，"
     "请先思考转换过程（按数位分解，注意中间零的读法），把思考过程放在 <think> 标签中，"
     "再把最终答案放在 <answer> 标签中。"},
    {"role": "user", "content": "转换：10500 = ?"},
]
text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
enc = tokenizer(text, return_tensors="pt").to("cuda")
out = model.generate(**enc, max_new_tokens=128, do_sample=False, pad_token_id=tokenizer.pad_token_id)
print(tokenizer.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True))
# 基座预期: '一万零五百'（可能无标签）
# 训练后预期: '<think>...</think><answer>一万零五百</answer>'
```

## 6. 常见问题

**Q1：`from trl import GRPOTrainer` 报 `No module named 'vllm'`？**
trl 0.21 × transformers 5.x 已知不兼容。所有脚本第一行 `import trl_compat`
已修复。确保从项目根运行、不删 src/trl_compat.py。

**Q2：训练中奖励全为 0、补全乱码？**
检查是否开了 gradient checkpointing（本项目默认关闭）。显存不够用 `--batch 4 --accum 8`。

**Q3：一步训练后模型输出全乱（NaN）？**
本地 Qwen config.json 标 fp16 → 必须显式 bf16 加载（train_grpo.py 已写死
`model_init_kwargs={"torch_dtype": "bfloat16"}`）。云端 4090D 无此问题。

**Q4：CUDA OOM（尤其 G5 beta>0，~21GB）？**
`--batch 4 --accum 8`；仍 OOM 则 G5 改用 `--lr 2e-4` + LoRA 降级方案
（需给 train_grpo.py 加 --lora 开关，参照参考项目实现）。

**Q5：probe 结果 L6 informative 很高 / L3 全对？**
正常，这正是选题依据：把配比向 informative ∈ [0.3, 0.8] 的难度倾斜，
全对（0.52+）或全错（<0.2）的难度留作泛化评估。

**Q6：训练日志里 `epoch` 显示 0.x 没跑完一整轮？**
正常。GRPO 在线采样，1000 题训练集 300 步 × 4 题/步 = 1200 题会循环采样，
题目重复无碍（每步重新采样 8 条）。

**Q7：本机验证时模型路径报错？**
本地 HF 缓存命中 `Qwen/Qwen2-0.5B-Instruct`；1.5B 的 checkpoint 已在
results.tar.gz 里（g4），直接传 `--model outputs/g4_1.5b_think_ckpt`。

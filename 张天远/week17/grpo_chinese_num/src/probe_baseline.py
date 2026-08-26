"""probe_baseline.py — 基线摸底 / 训练后评估（同一脚本，--model 切换）

评估 GRPO 可学习性的核心指标（继承参考项目方法论）：
  - greedy 正确率 / 格式遵循率（answer 标签、think 标签分开统计）
  - pass@8（温度 1.0 采样 K 条，与 GRPO 组大小一致）
  - informative group rate：组内有对有错的比例（0 < 正确数 < K）——
    全对/全错的组 advantage=0，GRPO 学不到任何东西，这是选题的核心指标

本项目扩展指标：
  - think_sample_rate：采样中 think 格式出现比例（think 模式的"顿悟"曲线基础）
  - 宽松口径：无 <answer> 标签时，取最后一个数字串或中文答案子串匹配——
    保证冷启动阶段（基线模型完全无视标签）正确信号不为 0

使用方式：
  python src/probe_baseline.py --model 0.5b                    # 基线（云端 bf16）
  python src/probe_baseline.py --model 0.5b --think            # think 格式基线
  python src/probe_baseline.py --model outputs/g1_0.5b_answer_ckpt --seed 42   # 训练后评估
  python src/probe_baseline.py --model <ckpt> --think --dtype fp16 --quick     # 本机验证
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import json
import random
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from num2cn import LEVELS, make_problem, num2cn, parse_output

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "outputs"

# 云端/本地模型别名 → HF 模型名（transformers 自动命中本地 HF 缓存或 hf-mirror 下载）
MODEL_ALIASES = {
    "0.5b": "Qwen/Qwen2-0.5B-Instruct",
    "1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
}

SYSTEM_PROMPT_ANSWER = (
    "你是一个中文数字转换助手。用户会给你一个阿拉伯数字，"
    "请把它转换成中文数字，并把最终答案放在 <answer> 标签中，"
    "例如 <answer>一百零五</answer>。不要输出其他内容。"
)
SYSTEM_PROMPT_THINK = (
    "你是一个中文数字转换助手。用户会给你一个阿拉伯数字，"
    "请先思考转换过程（按数位分解，注意中间零的读法），"
    "把思考过程放在 <think> 标签中，"
    "再把最终答案放在 <answer> 标签中。"
    "例如 <think>105 分解为 1 个百、0 个十、5 个一，十位为零要读零</think>"
    "<answer>一百零五</answer>。不要输出其他内容。"
)

NUM_RE = re.compile(r"\d+")


def resolve_model(model_arg: str) -> str:
    return MODEL_ALIASES.get(model_arg, model_arg)


def build_prompts(tokenizer, problems, think: bool):
    system = SYSTEM_PROMPT_THINK if think else SYSTEM_PROMPT_ANSWER
    texts = []
    for num_str, _ in problems:
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"转换：{num_str} = ?"},
        ]
        texts.append(
            tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        )
    return texts


@torch.no_grad()
def generate(model, tokenizer, texts, do_sample, k=1, batch_size=16, max_new_tokens=128):
    """分批生成。do_sample=True 时每条 prompt 返回 k 个样本，外层列表按 prompt 对齐。"""
    all_outputs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        enc = tokenizer(batch, return_tensors="pt", padding=True).to(model.device)
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=1.0 if do_sample else None,
            top_p=1.0 if do_sample else None,
            num_return_sequences=k if do_sample else 1,
            pad_token_id=tokenizer.pad_token_id,
        )
        gen = out[:, enc["input_ids"].shape[1] :]
        decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)
        if do_sample:  # num_return_sequences 把每条 prompt 的 k 个样本连续排列
            all_outputs.extend(
                decoded[j * k : (j + 1) * k] for j in range(len(batch))
            )
        else:
            all_outputs.extend(decoded)
    return all_outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="0.5b",
                        help="0.5b / 1.5b 别名或模型路径（训练后评估传 checkpoint 目录）")
    parser.add_argument("--think", action="store_true", help="think 格式模式（与训练 --think 一致）")
    parser.add_argument("--dtype", type=str, default="bf16", choices=["bf16", "fp16"],
                        help="模型加载精度：云端 4090D 用 bf16，本机 1080Ti 验证用 fp16")
    parser.add_argument("--quick", action="store_true", help="每难度只跑 10 题，快速验证")
    parser.add_argument("--n", type=int, default=50, help="每个难度级别的题目数")
    parser.add_argument("--k", type=int, default=8, help="pass@k 的采样数（与 GRPO group size 一致）")
    parser.add_argument("--out", type=str, default="", help="结果 JSON 输出路径（默认 outputs/auto）")
    parser.add_argument("--seed", type=int, default=42,
                        help="题目生成随机种子（评估必须与基线同 seed 才能配对比较）")
    args = parser.parse_args()
    n = 10 if args.quick else args.n
    model_id = resolve_model(args.model)
    dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float16

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if (Path(args.model) / "adapter_config.json").exists():
        from peft import PeftModel

        base = AutoModelForCausalLM.from_pretrained(
            MODEL_ALIASES["0.5b"], dtype=dtype, device_map="cuda"
        )
        model = PeftModel.from_pretrained(base, args.model)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, device_map="cuda")
    model.eval()

    rng = random.Random(args.seed)
    report = {"model": args.model, "think": args.think, "dtype": args.dtype, "seed": args.seed}

    for level in LEVELS:
        t0 = time.time()
        problems = [make_problem(level, rng) for _ in range(n)]
        texts = build_prompts(tokenizer, problems, args.think)

        # ── 1. greedy 单样本：确定性能力 + 格式遵循 ─────────────────────────
        greedy_outs = generate(model, tokenizer, texts, do_sample=False)
        g_fmt = g_think = g_strict = g_loose = 0
        for (num_str, cn), out in zip(problems, greedy_outs):
            fmt, think, strict, loose = parse_output(out, num_str, cn)
            g_fmt += fmt
            g_think += think
            g_strict += strict
            g_loose += loose

        # ── 2. 温度采样 k 条：pass@k + informative group rate（宽松口径）────
        sample_outs = generate(model, tokenizer, texts, do_sample=True, k=args.k)
        s_strict = s_loose = 0
        pass_k = loose_pass_k = 0
        mixed = loose_mixed = 0
        think_hits = 0
        for (num_str, cn), outs in zip(problems, sample_outs):
            results = [parse_output(o, num_str, cn) for o in outs]
            n_strict = sum(r[2] for r in results)
            n_loose = sum(r[3] for r in results)
            s_strict += n_strict
            s_loose += n_loose
            pass_k += n_strict > 0
            loose_pass_k += n_loose > 0
            mixed += 0 < n_strict < args.k
            loose_mixed += 0 < n_loose < args.k
            think_hits += sum(1 for r in results if r[1])

        report[level] = {
            "n": n,
            "k": args.k,
            "greedy_answer_fmt": round(g_fmt / n, 4),
            "greedy_think_fmt": round(g_think / n, 4),
            "greedy_strict_acc": round(g_strict / n, 4),
            "greedy_loose_acc": round(g_loose / n, 4),
            "sample_strict_acc": round(s_strict / (n * args.k), 4),
            "sample_loose_acc": round(s_loose / (n * args.k), 4),
            f"pass@{args.k}": round(pass_k / n, 4),
            f"loose_pass@{args.k}": round(loose_pass_k / n, 4),
            "informative_group_rate": round(mixed / n, 4),
            "loose_informative_group_rate": round(loose_mixed / n, 4),
            "think_sample_rate": round(think_hits / (n * args.k), 4),
            "elapsed_sec": round(time.time() - t0, 1),
            "examples": [
                {"num": num_str, "answer": cn, "greedy_output": out}
                for (num_str, cn), out in list(zip(problems, greedy_outs))[:3]
            ],
        }
        r = report[level]
        print(
            f"{level:<10} greedy_loose={r['greedy_loose_acc']:.2f} "
            f"ans_fmt={r['greedy_answer_fmt']:.2f} think={r['greedy_think_fmt']:.2f} "
            f"loose_acc={r['sample_loose_acc']:.2f} "
            f"loose_pass@{args.k}={r[f'loose_pass@{args.k}']:.2f} "
            f"loose_informative={r['loose_informative_group_rate']:.2f} "
            f"({r['elapsed_sec']}s)"
        )

    out_path = Path(args.out) if args.out else OUT_DIR / f"{Path(args.model).name}_probe.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    print(f"\n结果已保存：{out_path}")
    print(f"GPU 峰值显存：{peak_gb:.2f} GB")


if __name__ == "__main__":
    main()

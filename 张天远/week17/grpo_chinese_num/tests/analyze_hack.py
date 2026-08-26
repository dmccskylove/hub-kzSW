"""analyze_hack.py — 宽松/严格口径差异归因（reward hacking 来源验证）

对训练后 checkpoint 在评估集（seed=42）上 greedy 解码，逐条归因：
  - strict      : <answer> 内容 == 标准中文（真正确）
  - num_match   : 宽松对但严格错，来源 = 输出中最后一个数字串 == 原数字
                  （think/answer 里抄原数字骗分 —— 主要嫌疑）
  - substr_match: 宽松对但严格错，来源 = 输出含标准中文答案子串
                  （think 里写了正确答案但 answer 标签错）
  - none        : 全错

用法（本机 1080Ti，fp16 推理）：
  PYTHONPATH= S:/condaEnvs/py312/python.exe tests/analyze_hack.py \
      --ckpt outputs/g4_1.5b_think_ckpt --think
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from num2cn import LEVELS, make_problem, normalize, parse_output, NUM_RE, ANSWER_TAG_RE
from probe_baseline import build_prompts, generate


def attribute(text: str, num_str: str, cn: str) -> str:
    """宽松对但严格错时，判定宽松分来源。"""
    m = ANSWER_TAG_RE.search(text)
    inner = normalize(m.group(1)) if m else ""
    if m is not None and inner == cn:
        return "strict"
    nums = NUM_RE.findall(text)
    if nums and nums[-1] == num_str:
        return "num_match"       # 抄原数字（think 或 answer 中）
    if cn and normalize(text).find(cn) >= 0:
        return "substr"          # 输出含标准中文答案（think 里写对但 answer 错）
    return "other"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", type=str, required=True, help="checkpoint 目录")
    parser.add_argument("--think", action="store_true", help="think 模式（与训练一致）")
    parser.add_argument("--n", type=int, default=50, help="每难度题数（与评估一致）")
    parser.add_argument("--seed", type=int, default=42, help="评估种子（与基线一致）")
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.ckpt)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.ckpt, dtype=torch.float16, device_map="cuda")
    model.eval()

    rng = random.Random(args.seed)
    print(f"ckpt={args.ckpt} think={args.think} n={args.n} seed={args.seed}\n")
    print(f"{'难度':<6} {'严格对':>6} {'宽松对':>6} {'差异':>5} "
          f"{'num_match':>10} {'substr':>7} {'其他':>5}")
    for lv in LEVELS:
        problems = [make_problem(lv, rng) for _ in range(args.n)]
        texts = build_prompts(tokenizer, problems, args.think)
        outs = generate(model, tokenizer, texts, do_sample=False)
        cnt = {"strict": 0, "loose": 0, "num_match": 0, "substr": 0, "other": 0}
        for (num_str, cn), out in zip(problems, outs):
            _, _, strict, loose = parse_output(out, num_str, cn)
            cnt["strict"] += strict
            cnt["loose"] += loose
            if loose and not strict:
                attr = attribute(out, num_str, cn)
                cnt[attr] += 1
        diff = cnt["loose"] - cnt["strict"]
        print(f"{lv:<6} {cnt['strict']:>6} {cnt['loose']:>6} {diff:>5} "
              f"{cnt['num_match']:>10} {cnt['substr']:>7} {cnt['other']:>5}")

    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    print(f"\nGPU 峰值显存：{peak_gb:.2f} GB")


if __name__ == "__main__":
    main()

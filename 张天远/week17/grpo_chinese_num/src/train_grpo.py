"""train_grpo.py — GRPO 训练：中文数字转换（复合奖励 = 正确分 1.0 + 格式分 0.2）

教学重点（在参考项目 grpo_arithmetic 基础上升级）：
  1. 任务差异化：阿拉伯数字 → 中文数字（零规则学习，可程序化验证的 RLVR 任务）
  2. R1 风格格式奖励：--think 模式下要求 <think>思考过程</think> + <answer>答案</answer>
     （think 只校验存在与非空，不校验内容——与 DeepSeek-R1/TinyZero 同款设计），
     格式分拆为 think 0.1 + answer 0.1，TRL 分别记录曲线
  3. 双模型规模对照：Qwen2-0.5B（参考项目同款） vs Qwen2.5-1.5B（跨代际）
  4. KL 消融：--beta 0.05 加载参考模型约束漂移（参考项目 beta=0 未做的维度）
  5. 零规则强化采样：make_problem 的 zero_ratio 保证训练集中间零题足量

使用方式（云端 4090D，bf16 全量）：
  python src/train_grpo.py --model 0.5b --tag g1_0.5b_answer --max_steps 300 --mix L3:0.4,L4:0.4,L5:0.2
  python src/train_grpo.py --model 0.5b --think --tag g2_0.5b_think --max_steps 300
  python src/train_grpo.py --model 1.5b --think --beta 0.05 --tag g5_1.5b_think_kl --max_steps 400

输出：
  outputs/<tag>_ckpt/          # 最终 checkpoint（含 tokenizer）
  outputs/<tag>_train_log.json # 每步指标（reward 分量、熵、frac_reward_zero_std 等）
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import json
import random
from pathlib import Path

import torch
from datasets import Dataset

import trl_compat  # noqa: F401  必须先于 trl 导入，修复 trl 0.21 + transformers 5.x 兼容
from trl import GRPOConfig, GRPOTrainer

from num2cn import LEVELS, make_problem, parse_output
from probe_baseline import MODEL_ALIASES, SYSTEM_PROMPT_ANSWER, SYSTEM_PROMPT_THINK, resolve_model

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "outputs"

# 默认难度配比（先按预估，跑完基线 probe 后按 informative group rate 调整）：
#   0.5B: L3/L4/L5 主训（参考项目经验：太难 L6 组内全错无梯度）
#   1.5B: 能力更强，配比上探 L4/L5/L6
DEFAULT_MIX = {
    "0.5b": [("L3_3digit", 0.4), ("L4_4digit", 0.4), ("L5_5digit", 0.2)],
    "1.5b": [("L4_4digit", 0.4), ("L5_5digit", 0.4), ("L6_6digit", 0.2)],
}


def parse_mix(mix_str: str) -> list:
    """'L3:0.4,L4:0.4,L5:0.2' → [("L3_3digit", 0.4), ...]。"""
    out = []
    for item in mix_str.split(","):
        short, weight = item.split(":")
        full = next((lv for lv in LEVELS if lv.startswith(short)), short)
        out.append((full, float(weight)))
    return out


def build_dataset(n: int, seed: int, mix: list, think: bool) -> Dataset:
    """程序化生成训练集：prompt 为 chat 格式，answer=标准中文、num=原数字（reward 用）。"""
    rng = random.Random(seed)
    system = SYSTEM_PROMPT_THINK if think else SYSTEM_PROMPT_ANSWER
    rows = []
    for _ in range(n):
        r, acc, level = rng.random(), 0.0, mix[-1][0]
        for lv, p in mix:
            acc += p
            if r <= acc:
                level = lv
                break
        num_str, cn = make_problem(level, rng)
        rows.append(
            {
                "prompt": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"转换：{num_str} = ?"},
                ],
                "answer": cn,      # 标准中文答案（reward_correct 判定用）
                "num": num_str,    # 原数字串（宽松解析兜底）
                "level": level,
            }
        )
    return Dataset.from_list(rows)


# ── 复合奖励：TRL 对多个 reward func 分别记录曲线，最后求和 ──────────────────
def reward_correct(completions, answer, num=None, **kwargs):
    """正确分（宽松解析）：answer 标签内匹配标准中文 → 1.0；
    无标签时最后一个数字串或中文答案子串匹配 → 1.0（冷启动有梯度）。"""
    rewards = []
    for comp, ans, num_str in zip(completions, answer, num):
        text = comp[0]["content"]
        rewards.append(1.0 if parse_output(text, num_str, ans)[3] else 0.0)
    return rewards


def reward_answer_format(completions, **kwargs):
    """格式分（answer 部分）：输出含 <answer>...</answer> → 0.1。"""
    return [0.1 if parse_output(comp[0]["content"], "0", "")[0] else 0.0
            for comp in completions]


def reward_think_format(completions, **kwargs):
    """格式分（think 部分，think 模式）：输出含 <think>非空内容</think> → 0.1。
    只校验存在性，不校验内容（R1 同款设计；内容正确性由 answer 裁决）。"""
    return [0.1 if parse_output(comp[0]["content"], "0", "")[1] else 0.0
            for comp in completions]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="0.5b",
                        help="0.5b / 1.5b 别名或模型路径（云端 bf16 全量训练）")
    parser.add_argument("--think", action="store_true",
                        help="R1 风格格式：<think>过程</think> + <answer>答案</answer>（格式分 0.1+0.1）")
    parser.add_argument("--beta", type=float, default=0.0,
                        help="KL 系数：>0 时加载参考模型约束漂移（消融实验用，显存 +1 份模型）")
    parser.add_argument("--mix", type=str, default="",
                        help="训练难度配比 'L3:0.4,L4:0.4,L5:0.2'；空则用模型默认配比")
    parser.add_argument("--max_steps", type=int, default=300, help="优化步数")
    parser.add_argument("--n_prompts", type=int, default=1000, help="训练集 prompt 数")
    parser.add_argument("--lr", type=float, default=2e-6, help="学习率（全量 bf16）")
    parser.add_argument("--batch", type=int, default=8, help="per_device_train_batch_size")
    parser.add_argument("--accum", type=int, default=4, help="gradient_accumulation_steps")
    parser.add_argument("--tag", type=str, required=True,
                        help="输出标签：outputs/<tag>_ckpt/ 与 outputs/<tag>_train_log.json")
    parser.add_argument("--log_completions", action="store_true", help="打印每步真实采样（调试用）")
    args = parser.parse_args()

    model_id = resolve_model(args.model)
    mix = parse_mix(args.mix) if args.mix else DEFAULT_MIX.get(args.model, DEFAULT_MIX["0.5b"])
    max_comp = 128 if args.think else 64   # think 内容需要更长生成空间
    ckpt_dir = OUT_DIR / f"{args.tag}_ckpt"
    log_path = OUT_DIR / f"{args.tag}_train_log.json"

    dataset = build_dataset(args.n_prompts, seed=123, mix=mix, think=args.think)

    config = GRPOConfig(
        output_dir=str(ckpt_dir),
        # 关键坑（参考项目实测）：本地 Qwen config.json 写 torch_dtype=float16，
        # 不显式指定会被加载成 fp16 → AdamW eps=1e-8 在 fp16 下溢出为 0 → 一步训废。
        # 云端 4090D 支持 bf16，显式 bf16 加载。
        model_init_kwargs={"torch_dtype": "bfloat16"},
        # ── GRPO 核心参数 ─────────────────────────────────────────────
        num_generations=8,          # 组内采样数 K：与基线摸底的 pass@8 一致
        beta=args.beta,             # KL 系数：0=不加载参考模型；>0 加载（消融维度）
        epsilon=0.2,                # PPO-clip 裁剪范围
        temperature=1.0,            # 采样温度：保持组内多样性
        max_prompt_length=256,
        max_completion_length=max_comp,
        # ── 批次：8 completions/微批 × 累积 4 = 每步 4 prompt × 8 采样 ──
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.accum,
        # ── 训练超参 ──────────────────────────────────────────────────
        learning_rate=args.lr,
        max_steps=args.max_steps,
        bf16=True,
        # 关键坑（参考项目实测）：transformers 5.x 下 gradient checkpointing + train
        # 模式会让 generate 输出完全损坏，GRPO 必须关闭；1.5B 全量不开也够
        gradient_checkpointing=False,
        # ── 日志与保存 ────────────────────────────────────────────────
        logging_steps=5,
        save_strategy="no",         # 只保存最终 checkpoint，节省磁盘
        report_to=[],
        seed=42,
        log_completions=args.log_completions,
    )

    reward_funcs = [reward_correct, reward_answer_format]
    if args.think:
        reward_funcs = [reward_correct, reward_think_format, reward_answer_format]

    trainer = GRPOTrainer(
        model=model_id,
        args=config,
        reward_funcs=reward_funcs,
        train_dataset=dataset,
    )
    trainer.train()

    ckpt_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(ckpt_dir))
    trainer.processing_class.save_pretrained(str(ckpt_dir))

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(trainer.state.log_history, f, ensure_ascii=False, indent=2)

    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    print(f"\n训练完成。checkpoint: {ckpt_dir}")
    print(f"训练日志: {log_path}")
    print(f"GPU 峰值显存: {peak_gb:.2f} GB")


if __name__ == "__main__":
    main()

#!/bin/bash
# run_cloud.sh — GRPO 中文数字转换：云端全流程（AutoDL 4090D）
#
# 用法：
#   bash cloud/run_cloud.sh              # 全流程：probe → 训练 G1~G5 → 评估 → 打包
#   bash cloud/run_cloud.sh --skip-probe # 跳过基线摸底（mix 已确认时）
#
# 流程：
#   1) 基线 probe ×2（0.5B / 1.5B，seed=42）→ 确定各模型训练难度配比
#   2) 训练 G1~G5（每组 tee 保存日志）
#   3) 训练后评估（同一评估集 seed=42，与基线配对比较）
#   4) 打包 results.tar.gz（全部 probe/log/figures + 主实验 g4 checkpoint）
#
# 注意：
#   - 所有日志通过 tee 保存到 logs/（训练中断可查进度）
#   - 默认不自动关机（实例保留，便于补跑/排查）
#   - 0.5B 组显存 ~7GB，1.5B 组 ~18GB，G5（beta>0）~21GB；若 OOM 将 batch 降为 4
set -e
cd "$(dirname "$0")/.."
# AutoDL 非交互 shell 不加载 conda init，显式加 PATH
export PATH=/root/miniconda3/bin:$PATH
# 模型缓存走数据盘 autodl-tmp（系统盘空间有限）
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache/hub
mkdir -p "$HF_HUB_CACHE"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_MMAP=1
export PYTHONUNBUFFERED=1
mkdir -p logs

# 默认训练难度配比（已按 2026-08-26 基线 probe 实测调整）：
#   0.5B: L2 0.66 / L3 0.50 / L4 0.52 / L5 0.38（L1 0.82 太易留泛化；L6 0.26 全错区）
#   1.5B: L5 0.70 / L4 0.58 / L6 0.46（L6 可学——规模对照核心；L1~L3 已近满分留泛化）
MIX_0_5B="L2:0.3,L3:0.3,L4:0.25,L5:0.15"
MIX_1_5B="L4:0.3,L5:0.4,L6:0.3"
SEED=42   # 评估 seed 与基线一致，保证配对比较

SKIP_PROBE=0
[ "$1" = "--skip-probe" ] && SKIP_PROBE=1

run() {
    local tag="$1"; shift
    echo ""
    echo "########## [$tag] python $* ##########"
    python "$@" 2>&1 | tee "logs/${tag}.log"
}

# ── [1/2] 基线摸底（选题依据；--skip-probe 跳过，复用已有产物）──────────────
if [ $SKIP_PROBE -eq 0 ]; then
    run probe_0.5b src/probe_baseline.py --model 0.5b --out outputs/base_0.5b_probe.json --seed $SEED
    run probe_1.5b src/probe_baseline.py --model 1.5b --out outputs/base_1.5b_probe.json --seed $SEED
fi

# ── [2/2] 训练矩阵 G1~G5 ───────────────────────────────────────────────────
run g1_0.5b_answer src/train_grpo.py --model 0.5b --tag g1_0.5b_answer \
    --max_steps 300 --mix "$MIX_0_5B"
run g2_0.5b_think src/train_grpo.py --model 0.5b --think --tag g2_0.5b_think \
    --max_steps 300 --mix "$MIX_0_5B"
run g3_1.5b_answer src/train_grpo.py --model 1.5b --tag g3_1.5b_answer \
    --max_steps 400 --mix "$MIX_1_5B"
run g4_1.5b_think src/train_grpo.py --model 1.5b --think --tag g4_1.5b_think \
    --max_steps 400 --mix "$MIX_1_5B"
run g5_1.5b_think_kl src/train_grpo.py --model 1.5b --think --beta 0.05 \
    --tag g5_1.5b_think_kl --max_steps 400 --mix "$MIX_1_5B"

# ── 训练后评估（同一评估集，与基线配对）────────────────────────────────────
run eval_g1 src/probe_baseline.py --model outputs/g1_0.5b_answer_ckpt \
    --out outputs/g1_0.5b_answer_probe.json --seed $SEED
run eval_g2 src/probe_baseline.py --model outputs/g2_0.5b_think_ckpt --think \
    --out outputs/g2_0.5b_think_probe.json --seed $SEED
run eval_g3 src/probe_baseline.py --model outputs/g3_1.5b_answer_ckpt \
    --out outputs/g3_1.5b_answer_probe.json --seed $SEED
run eval_g4 src/probe_baseline.py --model outputs/g4_1.5b_think_ckpt --think \
    --out outputs/g4_1.5b_think_probe.json --seed $SEED
run eval_g5 src/probe_baseline.py --model outputs/g5_1.5b_think_kl_ckpt --think \
    --out outputs/g5_1.5b_think_kl_probe.json --seed $SEED

# ── 打包（probe/log/figures 全量 + 主实验 g4 checkpoint 供本机验证）─────────
echo ""
echo "===== 打包 results.tar.gz ====="
mkdir -p outputs/figures
python src/compare_results.py 2>&1 | tee logs/compare.log || true
tar czf results.tar.gz \
    outputs/*_probe.json outputs/*_train_log.json outputs/figures \
    outputs/g4_1.5b_think_ckpt logs

echo ""
echo "===== 全部完成 ====="
echo "拉取命令（本机执行）："
echo "  scp -r root@<AutoDL主机>:/root/grpo_chinese_num/results.tar.gz ."
echo "本机解包后验证："
echo "  tar xzf results.tar.gz"
echo "  python src/probe_baseline.py --model outputs/g4_1.5b_think_ckpt --think --dtype fp16 --quick"
echo "实例保持运行（不自动关机），确认结果后请到控制台手动关机。"

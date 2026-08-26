"""compare_results.py — 多组实验对比：汇总表 + 样例对照 + 训练曲线

自动扫描 outputs/ 下按约定命名的产物：
  <tag>_probe.json       基线或训练后评估（--out 命名）
  <tag>_train_log.json   GRPO 训练日志

输出：
  stdout 汇总表（格式率 / greedy 正确率 / pass@8，按模型分组）
  outputs/figures/train_curves_<模型>.png（正确分/格式分/熵/退化组比例/think 率）

使用方式：
  python src/compare_results.py          # 全量对比
"""
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent.parent
OUT = ROOT / "outputs"
FIG_DIR = OUT / "figures"

LEVELS = ["L1_1digit", "L2_2digit", "L3_3digit", "L4_4digit", "L5_5digit", "L6_6digit"]
LEVEL_SHORT = [lv.split("_")[0] for lv in LEVELS]


def collect_probes():
    """扫描 outputs/*_probe.json → [(tag, report), ...]，按 tag 排序。"""
    items = []
    for p in sorted(OUT.glob("*_probe.json")):
        with open(p, encoding="utf-8") as f:
            report = json.load(f)
        items.append((p.name.replace("_probe.json", ""), report))
    return items


def collect_logs():
    items = []
    for p in sorted(OUT.glob("*_train_log.json")):
        with open(p, encoding="utf-8") as f:
            items.append((p.name.replace("_train_log.json", ""), json.load(f)))
    return items


def fmt_table(reports):
    """reports: [(标签, report), ...]。输出按难度分行的对比表。"""
    header = f"{'难度':<8}" + "".join(f"{name:^34}" for name, _ in reports)
    lines = [header]
    for lv, short in zip(LEVELS, LEVEL_SHORT):
        row = f"{short:<8}"
        for name, rep in reports:
            if lv not in rep:
                row += f"{'-':^34}"
                continue
            r = rep[lv]
            cell = (
                f"F{r['greedy_answer_fmt']:.2f}/T{r['greedy_think_fmt']:.2f}/"
                f"{r['greedy_loose_acc']:.2f}/{r['loose_pass@8']:.2f}"
            )
            row += f"{cell:^34}"
        lines.append(row)
    return "\n".join(lines)


def fmt_examples(base, post, think=False, n=2):
    """取主训练难度各 n 条 greedy 输出对照。"""
    lines = []
    for lv in ["L3_3digit", "L4_4digit", "L5_5digit"]:
        if lv not in base or lv not in post:
            continue
        lines.append(f"\n--- {lv} ---")
        for eb, ep in zip(base[lv]["examples"][:n], post[lv]["examples"][:n]):
            lines.append(f"  {eb['num']} → {eb['answer']}")
            lines.append(f"    前: {eb['greedy_output']!r}")
            lines.append(f"    后: {ep['greedy_output']!r}")
    return "\n".join(lines)


def plot_curves(log_entries, tag, fig_path):
    """log_entries: [(标签, log_history), ...]，叠加对比训练曲线。"""
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    for name, log_history in log_entries:
        logs = [e for e in log_history if "rewards" in e]
        if not logs:
            continue
        steps = [e["step"] for e in logs]
        axes[0].plot(steps, [e["rewards/reward_correct/mean"] for e in logs], label=f"{name} correct")
        if "rewards/reward_answer_format/mean" in logs[0]:
            axes[0].plot(steps, [e["rewards/reward_answer_format/mean"] for e in logs],
                         linestyle="--", label=f"{name} ans_fmt")
        if "rewards/reward_think_format/mean" in logs[0]:
            axes[0].plot(steps, [e["rewards/reward_think_format/mean"] for e in logs],
                         linestyle=":", label=f"{name} think_fmt")
        axes[1].plot(steps, [e["frac_reward_zero_std"] for e in logs], label=name)
        axes[2].plot(steps, [e["entropy"] for e in logs], label=name)
        axes[3].plot(steps, [e["completion_length/mean"] for e in logs], label=name)

    axes[0].set_title("Reward components (group mean)")
    axes[0].set_xlabel("step")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_title("frac_reward_zero_std (degenerate groups)")
    axes[1].set_xlabel("step")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    axes[2].set_title("Policy entropy")
    axes[2].set_xlabel("step")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.3)
    axes[3].set_title("Completion length")
    axes[3].set_xlabel("step")
    axes[3].legend(fontsize=8)
    axes[3].grid(alpha=0.3)

    fig.tight_layout()
    fig_path.parent.mkdir(exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    print(f"训练曲线已保存：{fig_path}")


def main():
    probes = collect_probes()
    logs = collect_logs()
    FIG_DIR.mkdir(exist_ok=True)

    if not probes:
        print("未找到 outputs/*_probe.json，请先运行 probe_baseline.py")
        return

    # 分组：同一模型的实验放一起（基线在最前）
    group_key = lambda tag: "0.5b" if "0.5b" in tag else "1.5b"
    for g in ["0.5b", "1.5b"]:
        group = [(t, r) for t, r in probes if group_key(t) == g]
        if not group:
            continue
        print("=" * 100)
        print(f"模型组：{g}  （列格式：answer格式率/think格式率/greedy正确率/loose pass@8）")
        print("=" * 100)
        print(fmt_table(group))

        base = next((r for t, r in group if t.startswith("base")), None)
        if base:
            for t, r in group:
                if t.startswith("base"):
                    continue
                print(f"\n样例对照（{t}）：")
                print(fmt_examples(base, r))

        group_logs = [(t, l) for t, l in logs if group_key(t) == g]
        if group_logs:
            plot_curves(group_logs, g, FIG_DIR / f"train_curves_{g}.png")


if __name__ == "__main__":
    main()

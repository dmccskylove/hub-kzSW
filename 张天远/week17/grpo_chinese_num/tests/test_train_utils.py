"""test_train_utils.py — train_grpo.py 工具函数冒烟测试（mock trl，无需 GPU/trl）。

验证：
  1. parse_mix：难度配比字符串解析
  2. build_dataset：prompt 结构、num/answer 列与 num2cn 一致性、think 开关切换 system prompt
  3. DEFAULT_MIX 权重之和 = 1.0
"""
import sys
import types
from pathlib import Path

# ── mock trl（本机未安装，仅测工具函数）────────────────────────────────────
trl_mod = types.ModuleType("trl")
tiu = types.ModuleType("trl.import_utils")
trl_mod.import_utils = tiu
trl_mod.GRPOConfig = object
trl_mod.GRPOTrainer = object
sys.modules["trl"] = trl_mod
sys.modules["trl.import_utils"] = tiu

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import train_grpo  # noqa: E402
from num2cn import num2cn  # noqa: E402


def main():
    failed = 0

    # 1) parse_mix
    mix = train_grpo.parse_mix("L3:0.4,L4:0.4,L5:0.2")
    expect = [("L3_3digit", 0.4), ("L4_4digit", 0.4), ("L5_5digit", 0.2)]
    if mix != expect:
        print(f"[FAIL] parse_mix = {mix}")
        failed += 1
    print(f"[1] parse_mix OK: {mix}")

    # 2) DEFAULT_MIX 权重归一
    for k, v in train_grpo.DEFAULT_MIX.items():
        total = sum(w for _, w in v)
        if abs(total - 1.0) > 1e-9:
            print(f"[FAIL] DEFAULT_MIX[{k}] 权重和 = {total}")
            failed += 1
    print("[2] DEFAULT_MIX 权重归一 OK")

    # 3) build_dataset（answer 模式 + think 模式）
    for think in (False, True):
        ds = train_grpo.build_dataset(200, seed=123, mix=[("L4_4digit", 1.0)], think=think)
        assert len(ds) == 200, f"数据集大小 {len(ds)}"
        row = ds[0]
        if "prompt" not in row or "answer" not in row or "num" not in row or "level" not in row:
            print(f"[FAIL] 缺少列: {list(row.keys())}")
            failed += 1
        if row["answer"] != num2cn(int(row["num"])):
            print(f"[FAIL] answer 与 num 不一致: {row}")
            failed += 1
        sys_text = row["prompt"][0]["content"]
        if think != ("<think>" in sys_text):
            print(f"[FAIL] think={think} 但 system prompt 含 <think>: {sys_text[:60]}")
            failed += 1
        if row["prompt"][1]["content"] != f"转换：{row['num']} = ?":
            print(f"[FAIL] user prompt 格式: {row['prompt'][1]['content']}")
            failed += 1
        print(f"[3] build_dataset(think={think}) OK: 样例 {row['num']} → {row['answer']}")

    # 4) reward 函数签名可用性（不执行，仅验证可调用构造）
    assert callable(train_grpo.reward_correct)
    assert callable(train_grpo.reward_answer_format)
    assert callable(train_grpo.reward_think_format)
    print("[4] reward 函数定义 OK")

    print("\n" + ("全部通过 ✅" if failed == 0 else f"存在失败 ❌ ({failed})"))


if __name__ == "__main__":
    main()

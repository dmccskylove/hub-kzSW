"""reward 函数判定逻辑验证（mock trl，无 GPU）。"""
import sys, types
from pathlib import Path

trl_mod = types.ModuleType("trl")
tiu = types.ModuleType("trl.import_utils")
trl_mod.import_utils = tiu
trl_mod.GRPOConfig = object
trl_mod.GRPOTrainer = object
sys.modules["trl"] = trl_mod
sys.modules["trl.import_utils"] = tiu
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import train_grpo as tg

C = lambda s: [{"content": s}]

cases = [
    ("<answer>一百零五</answer>", "一百零五", "105", 1.0, 0.1, 0.0),
    ("<answer>105</answer>", "一百零五", "105", 1.0, 0.1, 0.0),
    ("一百零五", "一百零五", "105", 1.0, 0.0, 0.0),
    ("105", "一百零五", "105", 1.0, 0.0, 0.0),
    ("<answer>一百零六</answer>", "一百零五", "105", 0.0, 0.1, 0.0),
    ("<think></think><answer>一百零五</answer>", "一百零五", "105", 1.0, 0.1, 0.0),
    ("<think>105 由 1 百 0 十 5 个一组成</think><answer>一百零五</answer>", "一百零五", "105", 1.0, 0.1, 0.1),
    ("<think>百位1十位0个位5</think>答案一百零五", "一百零五", "105", 1.0, 0.0, 0.1),
    ("<answer>一万零五百</answer>", "一万零五百", "10500", 1.0, 0.1, 0.0),
    ("<answer>一萬零五百</answer>", "一万零五百", "10500", 0.0, 0.1, 0.0),
    ("<think>五千零十六</think><answer>五千零一十六</answer>", "五千零一十六", "5016", 1.0, 0.1, 0.1),
]

failed = 0
for text, ans, num, exp_c, exp_f, exp_t in cases:
    comps = [C(text)]
    c = tg.reward_correct(comps, [ans], [num])[0]
    f = tg.reward_answer_format(comps)[0]
    t = tg.reward_think_format(comps)[0]
    ok = (c == exp_c and f == exp_f and t == exp_t)
    if not ok:
        failed += 1
        print(f"[FAIL] {text[:40]!r} → correct={c}({exp_c}) fmt={f}({exp_f}) think={t}({exp_t})")
    else:
        print(f"[OK] {text[:40]!r} → {c} / {f} / {t}")

comps = [C("<answer>一万零五百</answer>"), C("随便"), C("<think>x</think><answer>一百零五</answer>")]
print("\n批量 correct:", tg.reward_correct(comps, ["一万零五百", "一百零五", "一百零五"], ["10500", "105", "105"]))
print("批量 fmt:", tg.reward_answer_format(comps))
print("批量 think:", tg.reward_think_format(comps))

print("\n" + ("全部通过 ✅" if failed == 0 else f"失败 {failed} 条 ❌"))

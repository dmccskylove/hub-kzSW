"""test_num2cn.py — num2cn 转换器与解析器的验证测试（无第三方依赖，纯 stdlib）。

运行：python tests/test_num2cn.py
覆盖：
  1. 关键边界用例表（人工核对的期望输出）
  2. 全量 1..999999 交叉验证：cn2num(num2cn(n)) == n（独立反向解析器互验）
  3. 输出合法性：无"零零"、不以零开头/结尾
  4. make_problem 各难度范围 + zero_ratio 统计
  5. parse_output 解析器用例（answer/think/宽松口径）
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from num2cn import DIGITS, LEVELS, make_problem, num2cn, parse_output

# ── 1. 关键用例表 ─────────────────────────────────────────────────────────
KEY_CASES = {
    1: "一", 9: "九", 10: "十", 15: "十五", 20: "二十", 99: "九十九",
    100: "一百", 101: "一百零一", 105: "一百零五", 110: "一百一十",
    115: "一百一十五", 120: "一百二十", 999: "九百九十九",
    1000: "一千", 1001: "一千零一", 1010: "一千零一十", 1050: "一千零五十",
    1100: "一千一百", 1500: "一千五百", 9999: "九千九百九十九",
    10000: "一万", 10001: "一万零一", 10005: "一万零五",
    10010: "一万零一十", 10050: "一万零五十", 10100: "一万零一百",
    10500: "一万零五百", 11000: "一万一千", 15000: "一万五千",
    12345: "一万二千三百四十五", 99999: "九万九千九百九十九",
    100000: "十万", 100001: "十万零一", 100005: "十万零五",
    100010: "十万零一十", 100050: "十万零五十", 100100: "十万零一百",
    100500: "十万零五百", 101000: "十万一千", 105000: "十万五千",
    110000: "十一万", 111000: "十一万一千", 123456: "十二万三千四百五十六",
    999999: "九十九万九千九百九十九",
}

# ── 2. 独立反向解析器（测试专用交叉验证）──────────────────────────────────
_DIGIT_MAP = {c: i for i, c in enumerate(DIGITS)}


def cn2num(s: str) -> int:
    """中文数字 → 整数（仅用于测试互验；只接受标准读法，忽略"零"）。"""
    total = section = num = 0
    for ch in s:
        if ch in _DIGIT_MAP:
            num = _DIGIT_MAP[ch]
        elif ch == "十":
            section += (num if num else 1) * 10
            num = 0
        elif ch == "百":
            section += (num if num else 1) * 100
            num = 0
        elif ch == "千":
            section += (num if num else 1) * 1000
            num = 0
        elif ch == "万":
            total += (section + num) * 10000
            section = num = 0
        # "零"与"亿"（范围内不出现）忽略
    return total + section + num


def main():
    failed = 0

    # 1) 关键用例
    for n, expect in KEY_CASES.items():
        got = num2cn(n)
        if got != expect:
            print(f"[FAIL] num2cn({n}) = {got!r}, expect {expect!r}")
            failed += 1
    print(f"[1] 关键用例 {len(KEY_CASES)} 条通过" if failed == 0 else f"[1] 关键用例失败 {failed} 条")

    # 2) 全量交叉验证 1..999999
    bad = 0
    for n in range(1, 1000000):
        if cn2num(num2cn(n)) != n:
            bad += 1
            if bad <= 5:
                print(f"[FAIL] roundtrip {n} → {num2cn(n)} → {cn2num(num2cn(n))}")
    print(f"[2] 全量 1..999999 交叉验证通过" if bad == 0 else f"[2] 交叉验证失败 {bad} 个")

    # 3) 合法性属性
    bad3 = 0
    for n in range(1, 1000000):
        s = num2cn(n)
        if "零零" in s or s.startswith("零") or s.endswith("零"):
            bad3 += 1
            if bad3 <= 5:
                print(f"[FAIL] 非法输出 {n} → {s!r}")
    print(f"[3] 合法性属性通过" if bad3 == 0 else f"[3] 合法性失败 {bad3} 个")

    # 4) make_problem 各难度
    rng = random.Random(42)
    for lv in LEVELS:
        lo, hi = {
            "L1_1digit": (1, 9), "L2_2digit": (10, 99), "L3_3digit": (100, 999),
            "L4_4digit": (1000, 9999), "L5_5digit": (10000, 99999),
            "L6_6digit": (100000, 999999),
        }[lv]
        zero_cnt = 0
        N = 500
        for _ in range(N):
            num_str, cn = make_problem(lv, rng)
            n = int(num_str)
            assert lo <= n <= hi, f"{lv} 越界 {n}"
            assert cn == num2cn(n), f"{lv} 答案不一致 {n}"
            zero_cnt += "0" in num_str and any(c != "0" for c in num_str.split("0", 1)[1]) or False
        # 简化 zero 统计（用 has_mid_zero）；L1/L2 无中间零，跳过
        from num2cn import has_mid_zero
        zero_cnt = 0
        if lv not in ("L1_1digit", "L2_2digit"):
            zero_cnt = sum(1 for _ in range(N) if has_mid_zero(int(make_problem(lv, rng)[0])))
        ratio = zero_cnt / N
        if lv not in ("L1_1digit", "L2_2digit") and abs(ratio - 0.5) > 0.12:
            print(f"[WARN] {lv} zero_ratio={ratio:.2f}（期望 ~0.5）")
        print(f"[4] {lv}: 范围/一致性 OK, 中间零占比 {ratio:.2f}")

    # 5) parse_output 用例
    cases = [
        # (text, num_str, cn, 期望(answer_fmt, think_fmt, strict, loose))
        ("<answer>一百零五</answer>", "105", "一百零五", (True, False, True, True)),
        ("<answer>105</answer>", "105", "一百零五", (True, False, False, True)),  # 数字答案 → 宽松对
        ("一百零五", "105", "一百零五", (False, False, False, True)),             # 无标签纯中文 → 宽松对
        ("105", "105", "一百零五", (False, False, False, True)),                  # 无标签数字 → 宽松对
        ("<answer>一百零六</answer>", "105", "一百零五", (True, False, False, False)),
        ("<think></think><answer>一百零五</answer>", "105", "一百零五", (True, False, True, True)),  # 空think
        ("<think>105 由 1 百 0 十 5 个一组成</think><answer>一百零五</answer>",
         "105", "一百零五", (True, True, True, True)),
        ("先算一下：<think>百位是1，十位0，个位5</think>最后答案一百零五。",
         "105", "一百零五", (False, True, False, True)),  # think 有、answer 无标签 → 宽松对
        ("<answer>一万零五</answer>", "10005", "一万零五", (True, False, True, True)),
    ]
    bad5 = 0
    for text, num_str, cn, expect in cases:
        got = parse_output(text, num_str, cn)
        if got != expect:
            print(f"[FAIL] parse_output({text[:30]!r}) = {got}, expect {expect}")
            bad5 += 1
    print(f"[5] parse_output 用例通过" if bad5 == 0 else f"[5] parse_output 失败 {bad5} 条")

    print("\n" + ("全部通过 ✅" if failed + bad + bad3 + bad5 == 0 else "存在失败 ❌"))


if __name__ == "__main__":
    main()

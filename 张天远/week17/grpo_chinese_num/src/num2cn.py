"""num2cn.py — 阿拉伯数字 → 中文数字转换器 + 题目生成 + 输出解析。

本模块是 GRPO 中文数字转换项目的核心：
  1. num2cn()       — 标准中文数字读法转换（含零规则），也是奖励判定的 ground truth
  2. make_problem() — 按难度级别程序化生成转换题（zero_ratio 控制零规则题占比）
  3. parse_output() — 解析模型输出，返回格式/正确性四元组（供 reward 与 probe 共用）

中文数字读法规则（本项目难点）：
  - 10~19 读"十/十一..."（十位 1 省略"一"）
  - 中间零读"零"，连续零只读一次，组尾零不读（1500 → 一千五百）
  - 跨节零要读（10005 → 一万零五，10500 → 一万零五百，100500 → 十万零五百）
"""
import random
import re

DIGITS = "零一二三四五六七八九"
UNITS_SMALL = ["", "十", "百", "千"]
UNITS_BIG = ["", "万", "亿"]

# ── 难度定义（位数即难度旋钮，零规则是真正的学习点）────────────────────────
LEVELS = [
    "L1_1digit",     # 1~9
    "L2_2digit",     # 10~99
    "L3_3digit",     # 100~999
    "L4_4digit",     # 1000~9999
    "L5_5digit",     # 10000~99999
    "L6_6digit",     # 100000~999999
]
RANGES = {
    "L1_1digit": (1, 9),
    "L2_2digit": (10, 99),
    "L3_3digit": (100, 999),
    "L4_4digit": (1000, 9999),
    "L5_5digit": (10000, 99999),
    "L6_6digit": (100000, 999999),
}
LEVEL_SHORT = {lv: lv.split("_")[0] for lv in LEVELS}  # L1/L2/...


def section_to_cn(x: int, leading: bool = False) -> str:
    """0 <= x <= 9999 的节内转换（不含"万/亿"单位）。

    leading=True 表示该节是整个数字的最高节：此时十位为 1 且千/百位为 0
    才省略"一"（10 → 十）；否则一律读"一十"（10010 → 一万零一十）。"""
    if x == 0:
        return "零"
    out = []
    q = x // 1000               # 千位
    h = (x // 100) % 10         # 百位
    t = (x // 10) % 10          # 十位
    o = x % 10                  # 个位
    if q:
        out.append(DIGITS[q] + "千")
    if h:
        out.append(DIGITS[h] + "百")
    elif q and (t or o):
        out.append("零")        # 千位后有零跨越
    if t:
        if t == 1 and leading and q == 0 and h == 0:
            out.append("十")    # 仅最高节开头省略"一"
        else:
            out.append(DIGITS[t] + "十")
    elif (h or q) and o and (not out or out[-1] != "零"):
        out.append("零")        # 十位为零、个位非零 → 补零（防重复）
    if o:
        out.append(DIGITS[o])
    return "".join(out)


def num2cn(n: int) -> str:
    """阿拉伯数字 → 中文数字（标准读法）。支持 0 ~ 8 位数（亿节内）。"""
    if n == 0:
        return "零"
    if n < 0:
        return "负" + num2cn(-n)
    sections = []               # sections[0]=个节, sections[1]=万节, sections[2]=亿节
    x = n
    while x:
        sections.append(x % 10000)
        x //= 10000
    out = []
    top = True                  # 当前节是否为整个数字的最高非零节
    for i in range(len(sections) - 1, -1, -1):
        sec = sections[i]
        if sec == 0:
            continue            # 整节为零不读（由低节衔接补"零"）
        if out and sec < 1000:
            out.append("零")    # 跨节零：低节不足千位说明节首有零
        out.append(section_to_cn(sec, leading=top))
        top = False
        if i > 0:
            out.append(UNITS_BIG[i])
    return "".join(out)


def has_mid_zero(n: int) -> bool:
    """数字串中是否存在"中间零"（0 后面还有非零位 → 读"零"）。
    尾零不算（1500 → 一千五百，无零字）。"""
    s = str(n)
    return any(s[i] == "0" and any(c != "0" for c in s[i + 1:]) for i in range(1, len(s)))


def make_problem(level: str, rng: random.Random, zero_ratio: float = 0.5):
    """生成一道转换题，返回 (阿拉伯数字串, 标准中文答案)。
    zero_ratio: 题面含"中间零"的比例——零规则是训练的核心学习信号，保证足量出现。"""
    lo, hi = RANGES[level]
    want_zero = rng.random() < zero_ratio
    for _ in range(300):
        n = rng.randint(lo, hi)
        if has_mid_zero(n) == want_zero:
            return str(n), num2cn(n)
    n = rng.randint(lo, hi)     # 保底（几乎不会走到）
    return str(n), num2cn(n)


# ── 输出解析（奖励判定与评估共用）──────────────────────────────────────────
ANSWER_TAG_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.S)
THINK_TAG_RE = re.compile(r"<think>\s*(.*?)\s*</think>", re.S)
NUM_RE = re.compile(r"\d+")


def normalize(s: str) -> str:
    """去除空白与常见标点，用于答案归一化比较。"""
    return re.sub(r"[\s，。！？、,.!?；;：:\"'“”‘’（）()《》【】\[\]\-—]+", "", s)


def parse_output(text: str, num_str: str, cn_answer: str):
    """解析模型输出，返回 (answer格式存在, think格式存在且非空, 严格正确, 宽松正确)。

    - answer_fmt: 含 <answer>...</answer> 标签
    - think_fmt : 含 <think>非空内容</think>（think 模式下使用）
    - strict_ok : answer 标签内内容 == 标准中文答案（归一化后）
    - loose_ok  : 严格成立，或（无标签时取最后一个数字串 == 原数），
                  或输出中含标准中文答案子串——宽松口径保证冷启动有梯度
    """
    m = ANSWER_TAG_RE.search(text)
    answer_fmt = m is not None
    inner = normalize(m.group(1)) if m else ""
    strict_ok = answer_fmt and inner == cn_answer
    loose_ok = strict_ok
    if not loose_ok:
        nums = NUM_RE.findall(text)
        if nums and nums[-1] == num_str:
            loose_ok = True
        elif cn_answer and normalize(text).find(cn_answer) >= 0:
            loose_ok = True
    m2 = THINK_TAG_RE.search(text)
    think_fmt = m2 is not None and len(normalize(m2.group(1))) > 0
    return answer_fmt, think_fmt, strict_ok, loose_ok


if __name__ == "__main__":
    # 简易自检：打印关键用例
    for n in [1, 9, 10, 15, 20, 99, 100, 101, 105, 110, 115, 999,
              1000, 1001, 1010, 1050, 1100, 1500, 9999,
              10000, 10001, 10005, 10010, 10050, 10100, 10500,
              11000, 15000, 12345, 99999,
              100000, 100001, 100005, 100010, 100050, 100100, 100500,
              101000, 105000, 110000, 111000, 123456, 999999]:
        print(f"{n} → {num2cn(n)}")

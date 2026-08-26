# ARCHITECTURE.md — GRPO 中文数字转换（零规则学习 + R1 风格格式奖励）

## 1. 项目定位

本周作业：参考 grpo_arithmetic（老师例子，GRPO 算术题），自己设计一个强化学习训练实验。

**本项目的差异化设计**（三个维度全部与参考项目不同）：

| 维度 | 参考项目 grpo_arithmetic | 本项目 grpo_chinese_num |
|------|--------------------------|------------------------|
| 任务 | 算术题（计算） | **中文数字转换**（阿拉伯 → 中文，零规则学习） |
| 格式 | 仅 `<answer>` 标签 | **R1 风格 `<think>` 过程 + `<answer>` 答案**（可选消融） |
| 模型 | Qwen2-0.5B（单模型） | **Qwen2-0.5B vs Qwen2.5-1.5B 跨代际规模对照** |
| 机制 | beta=0（无 KL） | **beta 消融（0 vs 0.05）** |
| 运行环境 | RTX 4060 8GB bf16 | **AutoDL 4090D 24GB 云端 bf16 + 本机 1080Ti fp16 验证** |

**为什么是中文数字转换**：

| 选型维度 | 中文数字转换的表现 |
|---------|-------------------|
| 奖励可验证 | `num2cn(n)` 程序精确判定，零成本零噪声（RLVR） |
| 难度旋钮 | 位数（L1~L6）+ **零规则**（105=一百零五 vs 1050=一千零五十） |
| 学习深度 | 零的插入规则是"规则泛化"而非背题——同型不同值必须学会规律 |
| 差异化 | 与参考项目算术完全不同任务，且是中文 NLP 特色 |
| 资源友好 | 输出 token 少（中文数字 ~15 字），生成快 |

## 2. 整体流水线

```
probe_baseline.py          train_grpo.py              probe_baseline.py          compare_results.py
（基线摸底，定难度）  →    （GRPO 训练 G1~G5）   →    （同评估集复测）        →    （对比表+曲线）
6 难度 × 50 题              0.5B 300 步 / 1.5B 400 步   --seed 42（与基线一致）     自动扫描 *_probe.json
greedy + pass@8             --think / --beta 0.05      --dtype bf16（云）/fp16（本机）
↓                           ↓                          ↓                           ↓
outputs/base_*_probe.json   outputs/<tag>_ckpt/        outputs/<tag>_probe.json    outputs/figures/
                            outputs/<tag>_train_log.json                           train_curves_*.png
```

## 3. 核心机制与设计决策

### 3.1 中文数字转换器（`src/num2cn.py`）

标准读法实现，通过 3 层验证（tests/test_num2cn.py）：
- 44 条人工核对的关键边界用例（1 / 10 / 15 / 105 / 1005 / 10010 / 100500 / 123456…）
- **全量 1..999999 交叉验证**：独立反向解析器 `cn2num(num2cn(n)) == n`
- 合法性属性：无"零零"、不以"零"开头/结尾

读法规则（本项目真正学习点）：
- 10~19 读"十/十一"（仅**整个数字最高节**省略"一"，10010 → 一万零一十）
- 中间零读"零"、连续零一次、尾零不读（1500 → 一千五百）
- 跨节零必读（10005 → 一万零五，10500 → 一万零五百）

### 3.2 复合奖励设计

```
reward = reward_correct(1.0)   # 宽松解析：answer 标签内匹配标准中文，或
                               #   无标签时取最后数字串/中文子串匹配（冷启动有梯度）
       + reward_think(0.1)     # think 模式：<think>非空内容</think>（只校验存在）
       + reward_answer(0.1)    # <answer>...</answer> 存在
```

- **think 只校验存在与非空、不校验内容** —— DeepSeek-R1 / TinyZero 同款设计：
  格式奖励管格式，正确性由 answer 裁决。这留下两个可观察现象：
  1. "顿悟时刻"：think 格式率先升、正确率后爬坡的 R1 动态是否在小模型复现
  2. "格式骗分"：模型写空 think / think 内直接抄答案来拿格式分（RL hack 检测）
- **零规则强化采样**：`make_problem(zero_ratio=0.5)` 保证训练集中间零题足量
  ——零规则是核心学习信号，不能让采样随机性稀释（参考项目没有的机制）

### 3.3 难度与选题方法论（继承参考项目）

GRPO 的梯度来源是**组内奖励方差**：全对/全错的组 advantage=0 无学习信号。
因此选题核心指标是 **informative group rate**（0 < 正确数 < K 的组比例），
基线 probe 实测后确定训练难度配比：

| 难度 | 范围 | 零规则 | 预期用途 |
|------|------|:---:|---------|
| L1 | 1~9 | 无 | 泛化评估（太易） |
| L2 | 10~99 | 无 | 泛化评估/保底 |
| L3 | 100~999 | 中间零 | 0.5B 主训候选 |
| L4 | 1000~9999 | 零组合 | 双模型主训 |
| L5 | 10000~99999 | 万位+零 | 双模型主训 |
| L6 | 100000~999999 | 多位零 | 1.5B 主训候选/能力边界 |

**双模型各自独立 probe、独立配比**（本项目新增的选题方法论）：
同一任务，不同规模模型的最优训练分布不同——0.5B 需要"降难度到可学区间"，
1.5B 可以"上探更高难度"。默认配比（probe 后按实测调整）：
- 0.5B: L3 0.4 / L4 0.4 / L5 0.2
- 1.5B: L4 0.4 / L5 0.4 / L6 0.2

### 3.4 双模型跨代际对照

| 模型 | 角色 | 理由 |
|------|------|------|
| Qwen2-0.5B-Instruct | 小模型基准 | 与参考项目完全同款（可复现对照） |
| Qwen2.5-1.5B-Instruct | 大模型主体 | 主流、hf-mirror 易得、能力显著更强 |

回答的问题：**RL 的能力边界如何随模型规模移动**（同任务同奖励同预算，
唯一变量是模型规模）——0.5B 学不动的 L6，1.5B 能否学会？

### 3.5 实验矩阵（7 组 = 2 probe + 5 训练）

| 组 | 模型 | 格式 | beta | 步数 | 回答的问题 |
|----|------|------|:---:|:---:|-----------|
| G0a/G0b | 0.5B / 1.5B | 基线 | — | — | 选题依据 |
| G1 | 0.5B | 仅 answer | 0 | 300 | 参考项目同款可复现 |
| G2 | 0.5B | think+answer | 0 | 300 | 小模型 think 顿悟观察 |
| G3 | 1.5B | 仅 answer | 0 | 400 | 规模效应（无 think 维度） |
| G4 | 1.5B | think+answer | 0 | 400 | 主实验：R1 式格式奖励 |
| G5 | 1.5B | think+answer | 0.05 | 400 | KL 约束作用（与 G4 配对） |

分析维度：规模（G1↔G3、G2↔G4）、格式（G1↔G2、G3↔G4）、KL（G4↔G5）。

## 4. 云端/本地分工

| 阶段 | 环境 | 说明 |
|------|------|------|
| 训练 | AutoDL 4090D 24GB | bf16 全量；0.5B ~7GB / 1.5B ~18GB / G5 ~21GB |
| 基线摸底 | 云端（训练前） | probe 结果决定 mix 配比 |
| 训练后评估 | 云端 | 同一评估集 seed=42 配对比较 |
| 最终验证 | 本机 1080Ti 11GB | fp16 加载 checkpoint 复测 + 行为样例检查 |
| 汇总出表 | 任意 | compare_results.py 自动扫描 |

**1080Ti 无法 bf16**（Pascal 6.1），本机验证统一 fp16；
训练全程在云端 bf16（4090D 原生支持），参考项目的 fp16 下溢坑在云端不存在。

## 5. 关键工程决策与踩坑（继承 + 新增）

| 问题 | 根因 | 解法 |
|------|------|------|
| trl 0.21 × transformers 5.x 崩 `import vllm` | transformers 5.x `_is_package_available()` 返回 `(bool, version)` 元组，非空元组恒 truthy | `src/trl_compat.py` 打补丁（复制参考项目，先于 trl 导入） |
| `warnings_issued` 属性缺失 | transformers 5.x 移除警告去重字典 | trl_compat 补类级空字典 |
| gradient checkpointing 毁 generate | transformers 5.x 下 train+checkpointing 前向损坏 | 关闭 checkpointing（0.5B/1.5B 显存够） |
| fp16 一步训废（NaN/Inf） | config.json 标 fp16 → AdamW eps=1e-8 下溢 | 云端显式 bf16 加载；本机验证 fp16 只推理不训练 |
| **10010 读"一万零十"（bug）** | "一十"省略条件过宽（`x<20`） | 改为"仅整个数字最高节"判断（测试抓到） |
| 1.5B + beta>0 显存 21GB 逼近 24GB | 参考模型额外一份权重 | 若 OOM：batch 8→4 + accum 4→8（脚本参数化） |

## 6. 目录结构

```
grpo_chinese_num/
├── src/
│   ├── num2cn.py           # 数字→中文转换器 + 题目生成 + 输出解析（核心）
│   ├── probe_baseline.py   # 基线摸底/训练后评估（--think/--dtype/--model 参数化）
│   ├── train_grpo.py       # GRPO 训练（--think/--beta/--mix/--tag/--model）
│   ├── compare_results.py  # 自动扫描 outputs 生成对比表 + 曲线
│   └── trl_compat.py       # trl 0.21 + transformers 5.x 兼容补丁（复制参考项目）
├── cloud/
│   ├── setup_cloud.sh      # AutoDL 环境初始化 + 模型预下载
│   └── run_cloud.sh        # 全流程：probe → 训练 G1~G5 → 评估 → 打包
├── tests/
│   └── test_num2cn.py      # 转换器 3 层验证（关键用例/全量交叉/合法性）
├── outputs/                # 本机验证结果（云端 results.tar.gz 解包至此）
├── ARCHITECTURE.md         # 本文件
└── USAGE_GUIDE.md          # 使用指南
```

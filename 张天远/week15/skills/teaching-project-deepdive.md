---name: teaching-project-deepdive
description: 把技术项目转成面向基础薄弱学生的结构化教学文档。触发条件：用户说"写教案"、"做教程"、"输出教学文案"、"给学生讲"、"explain this project to beginners"、"write a teaching doc"等。
triggers: [写教案, 做教程, 教学文案, 给学生讲, 出教程, 写教学文档, 教程, 教案]
---

# Teaching Project Deepdive

## 概述

把技术项目转成结构化、自上而下的教学文档。核心理念：**先见森林，再见树木，最后数叶子** (forest first, then trees, then leaves)。学生脑中如果没有心智框架，每一个细节都会变成孤岛。

## 何时使用

- 用户说"写教案"、"做教程"、"输出教学文案"、"给学生讲"
- 用户说 "write a teaching doc", "create a tutorial", "explain this project to beginners"
- 需要把代码库/项目/管线解释给基础薄弱的人

### 何时不使用

以下场景硬套此框架会适得其反：

| 场景 | 原因 | 改用 |
|------|------|------|
| API 参考文档 | 学生需要查表，不需要心智模型 | 按端点/函数组织的速查表 |
| CLI 工具使用手册 | 需要"怎么做"索引，不是"为什么"深度 | 按任务组织的命令手册 |
| 单文件脚本且概念密度低（只有 2-3 个核心概念） | 不需要主线图，逐段注释即可 | 逐段注释 + 运行示例 |

> 反例：70 行的 PyTorch 训练脚本涉及 tensor、argmax、Linear、CrossEntropyLoss、backward、Adam、ONNX 等七八个核心概念——概念密度很高，值得用本框架。行数不是标准，概念密度才是。

如果不能确定是否适用，先问用户这个文档的主要读者是谁、阅读场景是什么。

## 受众校准与分层交付

### 第一步：确定受众知识基线

开始教学前，先明确：

```
受众画像：
  已知：_______________（如：会 Python 基础语法、用过 numpy）
  未知：_______________（如：没碰过 PyTorch、不知道什么是张量）
  目标：学完后能 _______________
```

如果前置知识缺口太大（未知项超过 5 个核心概念），先产出"前置阅读清单"，不要硬讲。

### 第二步：选择交付深度

根据场景自动选择或让用户确认：

| 档位 | 长度 | 适用场景 | 特点 |
|------|------|----------|------|
| 速览版 | ~2,000 字 | 技术分享、面试准备 | 只有总纲+主线图+一句话每步 |
| 标准版 | ~8,000 字 | 新人 onboarding | 总纲 + 每步 4 层展开（精简版） |
| 深度版 | ~20,000+ 字 | 正式课程/自学教材 | 总纲 + 完整 4 层 + 技巧专题 + 动手实验 |

> 档位选在阶段 1 结束后确认。深度版执行全部规则；标准版可省略技巧专题和代码可运行性验证；速览版只产出阶段 2 内容。

## 项目规模适配

不同规模的项目采用不同的"研究吸收"策略：

| 规模 | 文件数 | 策略 |
|------|--------|------|
| 小型 | 1-3 文件 | 通读全部源文件，逐行理解 |
| 中型 | 4-10 文件 | 先读入口文件 + 数据流图，再按调用链逐文件深入 |
| 大型 | 10+ 文件 | 先读 README + 配置文件 + 目录结构，定位 3-5 个核心文件深读，其余按需查阅 |

**对中大型项目：** 阶段 1 的目标不是读完每一行，而是**画出准确的数据流图**。数据流图上每个节点标注对应文件，只对那些节点文件做深读。

### 配置文件专项处理

**如果项目有集中式配置文件（如 `config.py`、`config.yaml`），它必须作为"步骤 0"在主线图开始前单独讲解。** 配置文件不是附录材料——它是所有参数的"总开关"，学生改一个数字就会影响整个模型的行为。处理规则：

1. **识别控制面板**：阶段 1 研究时，找出哪个文件集中管理参数。常见标志：`from config import *` 出现在多个模块中。
2. **参数分组讲解**：按"模型架构 / 训练 / 生成 / 加速"分组，每组给一小段代码 + 逐行注释。不要只列一张表——学生需要理解"改这个数字会怎样"。
3. **两层配置陷阱**：有些项目在配置文件中有默认值，在模型类中另有默认值（如 `config.py` 的 `HIDDEN_SIZE=768` vs `GptConfig.__init__` 的 `hidden_size=512`）。必须在教案中解释哪个是实际生效的，否则学生看到两个数字会困惑。
4. **编入主线图**：文件-阶段对照表中，配置文件应列为第 ⓪ 步，并出现在主线图上方或旁注中。

## 分层追加工作流（标准版 → 深度版升级）

用户先生成标准版，审阅后说"追加一下"、"加深度版内容"、"把实验和实操手册补上"时，触发此流程。

**不要在初次生成时就问"要不要深度版"**——先按用户指定的档位生成，交付后告知"如需深度版可追加 X/Y/Z"，让用户自然决定。

### 追加内容清单

| 追加项 | 插入位置 | 内容 |
|--------|----------|------|
| Mermaid 架构图 | 一、总纲，紧接 ASCII 主线图之后 | 展示核心组件间的调用/依赖关系 |
| 🛠 动手实验 | 每大节的"学生自检"之后、"🔙 回到主线图"之前 | 6-8 个 L2 变式型实验，含目标/步骤/命令/预期输出/原理/恢复 |
| 全流程实操手册 | 正文最后一章之后、附录 A 之前 | 按阶段组织的 shell 命令，每条附预期输出标记；一键跑通脚本；GPU/CPU 时间预算表 |

### 追加执行方式

**不要重写整个文件。** 用 `ctx_edit` 逐处精确插入：

1. 先 `read_file` 定位每个插入点的精确上下文（前后各 3-5 行）
2. 每次 `ctx_edit` 的 `old_string` 包含插入位置前后独有的锚定文本
3. 7-8 次 `ctx_edit` 调用完成全部追加（1 次 Mermaid + 5-6 次实验 + 1 次实操手册 + 1 次目录更新）
4. 追加完成后更新目录（在目录中加"全流程实操手册"条目）

**关键原则：** 每次 `ctx_edit` 前必须 `read_file` 确认当前行号和上下文——追加过程中行号不断漂移，不能凭记忆定位。

## 三阶段流程

### 阶段 1：研究吸收 (Research & Absorb)

写任何一句教学内容之前，必须先理解项目。

1. **架构分析优先走 CodeGraph**（如项目已 `codegraph init -i`）：`codegraph_status → codegraph_files → codegraph_context`。详见 `project-architecture-analysis` skill。CodeGraph 之后再按需 `ctx_read` 读具体文件。
1.5 **读取 PPT 教材**（如有）：优先用 `python-pptx` 库；若因 `lxml` C 扩展兼容性问题失败（如 `execute_code` 沙箱 Python 版本不匹配），回退为 `zipfile + xml.etree.ElementTree` 纯标准库方案。详见 `references/pptx-extraction.md`。
2. 根据项目规模选择阅读策略（见上表）
2. 画出文件间的数据流（谁产出什么、谁消费什么）
3. 识别管线中 3-7 个关键"站点"
4. 识别 3-5 个核心架构组件
5. 记录每个设计决策及其原因
6. 记录每个 "gotcha" —— 修过的 bug、处理过的边界条件、平台相关 workaround
7. **预判常见误解**：对每个核心概念，列出学生最可能产生的 1-2 个错误理解
8. **（深度版）代码可运行性验证**：对文档中将要引用的代码片段，在目标环境中实际运行并记录 Python 版本和依赖版本
9. **画概念依赖图**：列出 4-8 个核心概念，画箭头标注"谁依赖谁"。被依赖最多的优先讲。这从根源上减少前向引用——如果 B 依赖 A，就先讲 A 再讲 B。
10. **（深度版）收集关键公式**：扫描项目中涉及的数学公式，记录每个公式的输入输出符号含义和具体数值实例，为 R8 备料。
11. **（深度版）数值声明验证**：教案中会出现的所有数值声明（参数量、训练时间、显存占用、准确率、loss 范围、PPL 范围等），必须用实际配置验证。不能直接引用代码注释中的数字——注释可能是过时的（如类默认值 vs 配置文件实际值不一致）。验证方法：优先用 `python -c "..."` 运行实际模型统计参数量；如果环境缺少依赖，用手算分组件累加。
12. **【必做】跨周隐患检查**：对照 `references/cross-week-pitfall-checklist.md` 的六项必查清单，逐项排查新项目是否存在前几周已知的坑（pretrain_models 硬编码、Path.resolve 陷阱、OpenMP 冲突、checkpoint 命名碰撞、matplotlib 云上中文方框、类别不均衡）。发现问题先修代码再写教案。
11. **（深度版）数值声明验证**：教案中会出现的所有数值声明（参数量、训练时间、显存占用、准确率、loss 范围、PPL 范围等），必须用实际配置验证。不能直接引用代码注释中的数字——注释可能是过时的（如类默认值 vs 配置文件实际值不一致）。验证方法：优先用 `python -c "..."` 运行实际模型统计参数量；如果环境缺少依赖，用手算分组件累加。
12. **【必做】跨周隐患检查**：对照 `references/cross-week-pitfall-checklist.md` 的六项必查清单，逐项排查新项目是否存在前几周已知的坑（pretrain_models 硬编码、Path.resolve 陷阱、OpenMP 冲突、checkpoint 命名碰撞、matplotlib 云上中文方框、类别不均衡）。发现问题先修代码再写教案。
13. **【必做】数据质量检查**：对每个数据集进行探索时，必须检查是否存在异常样本（如单条 >200 字、字段拼接错误、制表符混入等）。HuggingFace 原始数据集可能存在污染（本会话 BQ corpus 发现 15 条脏数据，单字段高达 51K 字）。修复方法：`len(sentence1) > 200 or len(sentence2) > 200` 过滤后写回。
14. **【深度版推荐】生产级可落地性审计**：教案初稿完成后，对 ML/LLM 项目运行六缺口+两断层+七差距的审计框架。详见 `references/production-readiness-audit.md`。这一步区分"教学案例 90 分"和"真实落地 60 分"之间的差距。

**概念依赖图示例：**
```
argmax ← 需要先理解 → 张量(tensor) ← 需要先理解 → 什么是向量
    ↓
logits ← 需要先理解 → Linear 层
    ↓
CrossEntropyLoss ← 需要先理解 → softmax + 对数
```
→ 讲解顺序应为：向量 → 张量 → Linear → argmax → softmax → logits → CrossEntropyLoss

**没理解透之前不要开始写。**

### 阶段 2：建立全局图 (Build the Big Picture)

文档的第一部分必须是自包含的全局概览，学生可以当作一个"心理块"记忆。

**必备要素：**

1. **一句话定义** —— 这个项目做什么，用大白话
2. **贯穿全文的主线示例**（推荐）—— 一个贯穿全文的场景，所有后续类比都围绕它展开，避免学生每学一个概念切换一次场景
3. **主线图** —— 流程图展示全管线（5±2 步）。每个后续章节都锚定回这张图
4. **文件-阶段对照表** —— 哪个文件对应哪个步骤
5. **架构图** —— 核心系统的内部组件
6. **关键数字** —— 总参数量、数据尺寸、关键维度

**主线示例设计原则：**
- 选一个学生肯定熟悉的日常场景（考试打分、做饭、快递分拣……）
- 这个场景的核心结构必须和项目的核心结构同构（有输入→处理→输出）
- 后续每节引入新概念时，回到这个场景来类比

**模板占位：**
```
### 贯穿全文的主线示例
本文从头到尾用一个场景帮你理解：[一句话描述场景]
后面每节的新概念，你都可以回到这个场景来理解。
```

**图表制作指导：**

- 粒度原则：图上每个节点 === 一个后续章节。不要更细（会变成代码），不要更粗（会失去锚定作用）
- 主线图用 ASCII art（终端友好，学生可抄写记忆）
- 复杂架构关系图推荐使用 Mermaid（适合展示组件间调用/依赖关系）
- ⚠️ 避免 ASCII 画大图：超过 20 行的 ASCII 图难以维护和阅读，改用 Mermaid 或分多张小图

主线图是最重要的产出物。每个章节标题必须标注它在主线图中的位置。

**章节标题模式：**
```
## 步骤 N：[名称] — [文件名]

> 📍 位置：主线图第 X → Y 格。[这一步做什么，一句话]。
```

### 阶段 3：逐层深入 (Deep Dive — Top-Down Zoom)

每个组件按严格的 4 层放大模式展开：

**第 1 层 — 解决什么问题？** 从"为什么"开始。先讲动机，再讲机制。

**第 2 层 — 用类比建立直觉。** 用日常类比（优先回到主线示例的场景）。永远不要从公式开始。（类比质量标准见 R3）

**第 3 层 — 带 shape 标注的代码走读。** 每个张量变换必须标注 输入 shape → 输出 shape。代码片段遵守最小有效片段原则（见 R2）。每行代码都要解释。

**第 4 层 — 设计理由。** 为什么选这个方案而不是其他？做了哪些权衡？

在标准版中，第 3-4 层可以精简；在速览版中，只有第 1 层。

## 八条强制规则

### R1：术语分级解释

不是所有术语都需要同等深度的解释。先分级，再处理：

**核心术语**（如果不懂这个概念，后续内容无法理解）→ **四步完整解释**：
1. **是什么** — 大白话定义。核心术语首次出现时括号标注英文，如"交叉熵损失（CrossEntropyLoss）"
2. **怎么做** — 公式、代码或具体例子
3. **优缺点** — 跟替代方案对比
4. **本项目为什么选它** — 回到项目语境

**辅助术语**（只需知道大意即可继续，如 batch_size、epoch、token）→ **两步简释**：
1. **是什么** — 一句话定义
2. **在本项目中的值/作用** — 回到本文语境

> **自查方法：** 写完每一节后，列出所有新引入的术语。标记每个是"核心"还是"辅助"。核心术语四步必须齐全；辅助术语两步即可。预期节省 20-30% 篇幅。

❌ 差例子："为什么是 learned 而非 sinusoidal？原始 Transformer 用了固定公式，但 GPT-2 发现 learned 更好。"
→ 两个术语都没解释，没公式，没直觉，没权衡。

✅ 好做法（核心术语 sinusoidal / sinusoidal positional encoding）：先讲是什么（公式+尺子类比），再讲 learned 是什么（nn.Embedding 表格随模型训练），然后各自优劣，最后说本项目为什么选 learned。

✅ 好做法（辅助术语 batch_size）："一次喂给模型多少个样本，本项目设为 18。"

### R2：每个张量必须标注 shape

代码走读中，每个张量操作后标注维度：

```python
Q = self.query(hidden_states)    # (batch=18, seq=512, hidden=768)
Q = self._split_heads(Q)         # (18, 12, 512, 64)  — 拆成 12 个头
```

#### R2 补充：最小有效片段原则

展示代码时，只保留当前要讲的那几行。用 `# ...` 省略无关部分，用注释标注隐藏了什么。代码片段本身就是教学 UI，要让学生视线自然落在关键行上。

```
❌ 贴 50 行完整函数，只讲解其中 3 行
✅ 贴 8 行：3 行关键代码 + 2 行上下文 + 3 处 `# ... 省略了 XXX`
```

**例子：**
```python
def forward(self, hidden_states):
    # ... 省略了 LayerNorm 和 Dropout（详见步骤 4）

    Q = self.query(hidden_states)     # (18, 512, 768)
    K = self.key(hidden_states)       # (18, 512, 768)
    V = self.value(hidden_states)     # (18, 512, 768)

    # 👆 上面三行是本节重点：Q/K/V 三个投影
    # ... 省略了 split_heads 和 attention 计算（详见步骤 5）
```

### R3：类比先于抽象

对每个抽象概念（注意力、归一化、残差连接），先给一个具体的日常类比，再给技术定义。学生记住的是类比；公式背了就忘。

**类比质量 checklist（使用前自查）：**

- [ ] 学生是否熟悉类比源？（别用"像期货市场"给不懂金融的人讲）
- [ ] **核心机制是否精准映射？**（不只是表面相似）
- [ ] 类比是否可能引入新的误解？（如果是，加一句"⚠️ 这个类比的局限是..."）
- [ ] 是否一句话能说完？（超过三句话的类比 = 类比本身成了学习负担）
- [ ] 是否出自贯穿全文的主线示例？（如果是，优先使用——减少场景切换）

**反例：**
```
❌ "Linear 层像一个评分委员会，每个评委给不同维度打分"
   → 引入"评委""打分"等无关概念，核心的矩阵乘法机制完全没体现

✅ "nn.Linear 就是一个矩阵乘法 y = xW + b。想象你把一个向量 x 通过一个变换矩阵 W 映射到新空间——就像通过一副眼镜看同一个东西，不同镜片（W 的行）让你看到不同特征。"
   → 精准映射"线性变换"的核心：映射到新空间、不同维度提取不同特征

✅ "ONNX 像 PDF——源代码（.docx 即 .py）在不同平台打开效果不一样，ONNX（即 .pdf）固定了布局，到哪都是一样的计算图。"
   → 精准映射"平台无关的中间表示"核心机制
```

### R4：学习自检点

每完成一个大节，插入自检问题，检验学生是否理解了核心思想：

```
**学生自检**：关上文档，能不能画出 XXX 的流程图？如果画不出来，回第 X 节重读。
```

### R5：常见误解预判与前置解答

不要让等学生踩坑再纠正。在阶段 1 研究项目时，对每个核心概念预判"学生最可能产生的 1-2 个错误理解"，在正文中主动破除。

**预判方法：**
- 同一个术语在不同框架/语境下有不同含义（如 `dim` 在 PyTorch 和 NumPy 中的语义）
- "隐形操作"——看起来没发生但实际发生了（如 CrossEntropyLoss 内含 softmax）
- "看起来像但实际不是"——两个概念长得像但本质不同（如 LayerNorm vs BatchNorm）

**正文格式（陈述式）：**
```
> ⚠️ **常见误解**：[错误理解]
> ✅ **实际情况**：[正确理解]
```

**叙事技巧：** 对最容易踩的 1-2 个坑，考虑用第一人称"我踩过"的叙事。自我参照效应（self-reference effect）让记忆效果显著更好。这不是风格偏好——是认知科学。

```
> 💡 我第一次学这个的时候以为 CrossEntropyLoss 输入该是概率，
> 所以在 forward 里多写了一个 softmax，结果 loss 降不下去，
> 查了半天才发现 PyTorch 已经内置了 softmax。把它写在这，帮你省两小时。
```

### R6：概念速查表

文档末尾附术语表：概念 → 英文 → 分级 → 一句话解释 → 文件位置。既当复习又当快速检索。

> 中英对照的重要性：学生学懂了"注意力"，但打开论文看到 "attention mechanism" 不认识。加一列英文的成本极低，对学生查资料的收益很大。

**格式：**
| 概念 | 英文 | 分级 | 一句话 | 位置 |
|------|------|------|--------|------|
| 交叉熵损失 | CrossEntropyLoss | 核心 | 衡量预测和真实标签的差距 | 步骤 6 / `loss.py:42` |

### R7：前向引用协议

教学中不可避免会提前提到后续才深入讲解的概念。处理规则：

**格式：**
```
🔜 后详：[概念名]
[一句话最小定义，够撑过当前段落即可]
→ 深入讲解见 第 X 节：[章节名]
```

**三条约束：**
1. **最小定义必须自洽** — 不能引入另一个尚未解释的术语
2. **一句话封顶** — 超过一句说明不该在这里提，应该重组讲述顺序
3. **必须锚定章节号** — 不能写"后面会讲"，得让学生知道到哪找
4. ⚠️ **禁止"详见本节"** — `→ 详见本节的代码走读部分。` 是最危险的承诺：无编号、无关键词可搜索、极易遗忘。必须改为 `→ 详见下方的 🔜回收 部分。` 并在后续内容中显式标注 `**🔜 回收：XXX**`

**例子：**
```
❌ "Embedding 之后加上 Positional Encoding，位置编码可以用 sinusoidal
    或 learned，GPT-2 用的 learned..." 
    → 学生：sinusoidal 是什么？learned 是什么？为什么选？全卡住了。

✅ "Embedding 之后加上 Positional Encoding，给每个词注入位置信息。
    🔜 后详：Positional Encoding
    一句话：让模型知道"第一个词"和"第二个词"的区别。
    → 两种实现（sinusoidal vs learned）及本项目的选择，见 步骤 3：Positional Encoding。"
```

#### R7 补充：后向锚定

讲完一个概念后，主动回到主线图，让学生重新建立位置感。前后锚定形成闭环：🔜 预告 → 正文 → 🔙 归位。

> ⚠️ **必须在初次起草时写入 🔙 锚定，不要留到事后修补。** 事后编辑文档（尤其是 patch/sed 修改已生成的文件）在 Windows 环境下经常因路径问题失败，且逐节定位容易遗漏。交付前自检清单会发现遗漏，但补救成本远高于一次写对。

**格式：**
```
> 🔙 回到主线图：现在第 X 格的输出已经 [一句话总结当前状态]。
> 它即将进入下一步 [步骤名]，这一步会 [一句话预告]。
```

**例子：**
```
> 🔙 回到主线图：现在 Embedding 层的输出是一个 (batch, seq, hidden)
> 的张量，每个 token 都是一个 768 维向量。它即将进入步骤 3 Self-Attention，
> 这一步会让每个 token "看到"序列中所有其他 token 的信息。
```

### R8：数学公式展示规范

深度学习教学文档中公式不可避免。不要从公式开始（R3），但公式出现时按此规范展示：

1. **公式前一句话**：说明"这个公式在算什么"
2. **逐符注释**：公式下方逐行注释每个符号的含义和形状（不要让学生猜字母）
3. **数值代入实例**：给一组具体数字代入计算过程，让学生看到"这是实在的"
4. **公式后一句话**：总结"这个结果意味着什么"

**例子：**
```
Attention 的核心计算：对 Value 做加权平均，权重由 Query 和 Key 的相似度决定。

    Attention(Q, K, V) = softmax(QKᵀ / √dₖ) · V

    其中：
    - Q：Query 矩阵，形状 (seq, dₖ)    — "我想查什么"
    - K：Key 矩阵，形状 (seq, dₖ)      — "我有什么标签"
    - V：Value 矩阵，形状 (seq, dᵥ)    — "我的实际内容"
    - √dₖ：缩放因子                    — 防止点积过大导致 softmax 梯度消失

    数值实例：假设 dₖ=64，两个 token 的 Q·K 点积 = 45，
    则 45/√64 = 45/8 = 5.625，softmax 后这个 token 的注意力权重 = 0.73。

    结果意味着：这个 token 会把 73% 的注意力放在那个 token 上。
```

## 动手实验设计

每个大节结束时，除了 R4 的自检题，还应提供动手练习。三个层次：

| 层次 | 类型 | 示例 | 适用 |
|------|------|------|------|
| L1 验证型 | 关上文档能不能画出来 | R4 自检题 | 标准版+ |
| L2 变式型 | 改参数/输入看效果怎么变 | "把 dim=1 改成 dim=0，输出 shape 变成什么？跑一下验证。" | 深度版 |
| L3 创造型 | 自己实现简化版 | "不看源码，用 numpy 实现一个单头 Attention" | 深度版 |

**L2 练习格式：**
```
**🛠 动手实验**
修改 `config.py` 中的 `hidden_size` 从 768 改为 384，重新跑一遍前向传播。
问题：哪些张量的 shape 变了？哪些没变？为什么？
预期：`Q, K, V` 的最后一维从 64 → 32，但 `batch` 和 `seq` 维度不变。
```

**原则：** L2 练习的成功率应该 >80%（不能让学生卡在练习本身）。如果实验需要超过 3 步操作，说明太复杂，拆成更小的实验。

## 学习报告：教学文案的回顾变体

与教学文案（面向未来，解释学生还没学的内容）不同，学习报告（面向过去，记录已经学完的内容）是一种**完全不同的文体**。

### 何时使用

- 用户说"写学习报告"、"写总结"、"做复盘"、"总结这几周的经验"
- 用户完成了多个互相关联的项目/周次，需要串联成一条学习曲线
- 核心变化：写作文体从"教学文"切换为"回忆录"

### 与教学文案的核心区别

| 维度 | 教学文案 (教案) | 学习报告 |
|------|---------------|---------|
| 时间指向 | 未来（学生还没学） | 过去（已经学完了） |
| 人称 | 第三人称（"学生"、"模型"） | **第一人称（"我"）** |
| 语气 | 解释、类比、引导 | **叙述、反思、总结** |
| 数据 | 预期值 + 占位符 | **实验真实数据，含理论 vs 实测偏差** |
| 结构 | 总纲 → 步骤展开 → 实验 → 附录 | **迭代演进 → 每轮收获 → 跨轮共性** |
| 失败 | 不写（怕误导学生） | **写（失败是最有价值的学习）** |

### 写作方法

**从"我做了什么"开始，而不是"这个项目是什么"。**

```
❌ 教学文案风格：
"本项目用 BERT 进行文本分类，池化策略有 cls/mean/max 三种。"

✅ 学习报告风格：
"我第一次跑完池化对比实验后，发现 mean 比 cls 高了 0.5 个点。
我以为代码写错了，查了两遍——结果没写错，是我关于 cls 的直觉错了。"
```

**每节必须包含三样东西：**
1. **具体实验数据**（不仅仅是准确率，还有对比表和交互样本）
2. **当时的感受**（"我以为 → 实际 → 我学到了"的叙事弧线）
3. **跨周回链**（Week03 的 5 次迭代 → Week06 的 LoRA 消融，两个"参数更多不一定更好"的案例互相印证）

**必须有三处"理论推导 vs 实证结果"的偏差分析**——如果所有实验都只验证了预期，要么实验设计有 bias，要么报告没写真实的东西。

### 常见的五个章节结构

```
一、Week N：第一个项目（具体数字 + 初印象）
二、Week N+1：第二个项目（迭代对比 + 新发现）
三、Week N+2：第三个项目（范式切换 + 对比的顿悟）
四、Week N+3：最新的项目（多方案多维度对比）
五、跨周总结：
  5.1 模型规模 vs 数据规模的匹配
  5.2 训练范式的演进（从头训练 → 预训练+微调 → 零样本 → LoRA）
  5.3 "更多参数"不总是好事
  5.4 实验才是真理
  5.5 一句总结
```

### 写完之后

学习报告本身不是终点。它应当触达一个"如果再给我一次机会，我会怎么分配资源"的结论——这是四周实验的终极产出。

### 常见错误表补充

| 错误 | 修正 |
|------|------|
| Function Calling 版 "Thought 不可见" | 这是错误结论。DeepSeek 全系模型（包括 v4-flash、R1 等）默认启用思考模式，API 返回的 `reasoning_content` 字段包含 CoT 推理链，即使 FC 模式下也能获取。Qwen 等模型可能在 `msg.content` 字段中同时输出推理文本。教案中应写"FC 版通过 `reasoning_content` 获取思考过程"而非"不可见"。 |
| 池化策略结论基于理论推导而非实测 | 在教案中标注 "预期值" 或 "基于通用经验"，避免声称未验证的结论为事实。如 cls 池化未必是最优——实测中 mean 可能更好。 |
| 数值声明（准确率/Loss/参数量）只写预期范围，不填写实测数字 | 教案交付时，如果学生已完成实验，回到教案填入真实数据替代占位符。写 "实际数据" 而非 "预期"。——实证结果比理论推导更有教学价值。 |

### 学习报告风格规范（用户偏好）

当用户要求写"学习报告"而非"教案"时：

1. **从学习者第一人称视角写。** 隐藏助手的痕迹，用"我做了""我发现了""我试了"代替"实验设计""实验结论""实验方案"等结构化标签。用户明确说过"不要教案式的写法"。

2. **用真实实验数据说话，不要理论推导占主导。** 每个观点后面跟实际数字（如"证券 Recall 从 0.18 飙升到 0.62，+0.444"），而不是"理论上加权 loss 可以提升小类"。用户对 trade-off 敏感——用"gain vs lose"的数字表达平衡。

3. **避免模板化的"动机→方案→结论"三段式。** 改用自然叙事：先写做什么，再写看到什么，最后写自己的感受。用户接受信息的方式是故事而不是框架。

4. **对比结果用表格，但表格以外的文字用个人口吻。** 表头直接写数据列，不用"实验设计""实验方法"等 meta 标签。

5. **失败经验同样有价值。** Focal Loss 效果不好、Few-shot 反而更差——这些负结果要记录，用户认为它们和成功结果一样有教学意义。

## 多周系列教学文档（Week03-06 跨周经验合并）

当需要为一个课程生成多周循序渐进的教案时（如 Week01→Week02→Week03），遵循以下附加规则。

### 跨周知识链设计

将连续几周的学习视为一条演进链，而不是独立的模块。在教案和学习报告中，应显式回溯前几周的知识：

| 维度 | Week03→Week06 演进的共通主线 | 说明 |
|------|---------------------------|------|
| 任务不变 | 文本分类 | 从 LSTM → BERT → MyGPT → LLM 零样本/SFT |
| 范式演进 | 从零训练→预训练微调→零样本→参数高效微调 | 数据量和参数量的匹配关系 |
| 评估维度 | 从只关注准确率→多维度（Macro F1、Recall分布、推理速度） | 每过一周增加一个评估视角 |
| 直觉纠偏 | 每轮都有"我以为→实际不是"的发现 | cls不是最好、全量微调不如LoRA、Focal胜出 |

### 跨周用语

在 WeekN 的文档中引用 WeekM 的内容时，标准格式：

```
📎 复习：WeekM 第Y节讲过 [概念名]。
这里只回顾关键点：[1-2 句核心]。如需重读，回 WeekM 教案。
```

避免在同一套文档中重复讲解前几周已经覆盖的基础概念（如 Tokenization、训练循环等），默认用户已掌握。

## 参考答案编写规范

当用户要求为教案中的动手实验和自查任务编写参考答案时，遵循此规范。

> ⚠️ **核心教训**：参考答案不能只给"概念解释"——学生拿着答案必须能**逐行执行**。每个实验的答案必须包含精确到行号的代码修改、可复制粘贴的命令、以及带具体数值的预期输出。

### 前置研究：读源文件，不靠记忆

写参考答案前，**必须**读取项目的实际源文件来获取：
- 精确的行号（不能凭记忆写"第 XX 行附近"）
- 实际的参数名和默认值（教案中的代码注释可能已过时）
- 文件的实际结构（函数签名、类定义位置）

**工具链**：`ctx_read(path, mode="map")` 获取文件结构 → `ctx_read(path, mode="lines:N-M")` 读取具体行 → `search_files` 搜索关键符号定位行号。

### 参考答案六要素

每个实验的答案必须包含以下全部要素（按顺序）：

| 要素 | 说明 | 示例 |
|------|------|------|
| **目标** | 一句话：这个实验要观察什么现象或验证什么原理 | "理解模型规模由哪些参数控制，亲眼看到参数量变化" |
| **步骤** | 编号的详细操作，含精确行号和代码 | "打开 `config.py`，改第 66 行：`HIDDEN_SIZE = 384`" |
| **命令** | 可复制粘贴的 shell 命令 | `python gpt_model.py` |
| **预期输出** | 带具体数值/文本的终端输出示例 | `模型参数量: 25,xxx,xxx  (约 25M)` |
| **原理** | 为什么是这个结果（1-3 句话，不需要长篇） | "HIDDEN_SIZE 控制宽度（平方效应于 FFN），两者各减半 → 参数量 ≈ 原值 1/4" |
| **恢复** | 如何把改动改回去 | "把上面 3 个参数改回原值" |

### 附加要素（按需）

- **踩坑提示**：如果某步容易出错（如改了 MAX_SEQ_LEN 后必须重跑 preprocess），用 `> ⚠️` 标注
- **可选深究**：如果实验有延伸价值（如"可选：用这个配置训练 2 个 epoch"），用"（可选）"标注

### 完整示例

```
#### 实验1：把 102M 模型缩小到 25M

**目标**：理解模型规模由哪些参数控制，亲眼看到参数量变化。

**步骤**：

1. 打开 `config.py`，改 3 个参数：
   # 第 66 行：HIDDEN_SIZE = 768  →  384
   HIDDEN_SIZE = 384

   # 第 68 行：NUM_HIDDEN_LAYERS = 12  →  6
   NUM_HIDDEN_LAYERS = 6

   # 第 69 行：NUM_ATTENTION_HEADS = 12  →  6
   NUM_ATTENTION_HEADS = 6

2. 运行模型自测：
   python gpt_model.py

3. **预期输出**：
   模型参数量: 25,xxx,xxx  (约 25M)
   可训练参数: 25,xxx,xxx

**原理**：`HIDDEN_SIZE` 控制宽度（平方效应于 FFN），`NUM_HIDDEN_LAYERS` 控制深度（线性效应）。两者各减半 → 参数量 ≈ 原值的 1/4。

**恢复**：把上面 3 个参数改回原值。
```

### 自查清单（参考答案交付前）

- [ ] 每个实验的代码修改有精确行号？
- [ ] 每个实验有可复制粘贴的命令？
- [ ] 预期输出包含具体数值/文本（不是"大概 XX 左右"）？
- [ ] 每个实验有恢复步骤（让学生能回到干净状态）？
- [ ] 所有行号和参数名与实际源文件一致（已通过读文件验证）？

### 自检题的答案规范

自检题（学生自检）的答案更灵活，但必须：
1. 直接回答问题（不要绕弯子）
2. 如果涉及计算，给出具体数值和计算过程
3. 如果涉及"为什么"，给出 2-3 句原理 + 1 个具体例子
4. 如果是 Week N 引用 Week M 的内容，用 `📎 复习` 格式回链

## 文档结构模板

```markdown
# [项目名] 从零入门 — 教学文案

## 前置要求
  已知：... | 未知：... | 目标：...

## 目录（带锚点链接）

## 一、总纲：一张图建立全部心智模型
  - 一句话定义
  - ### 贯穿全文的主线示例
    本文从头到尾用一个场景帮你理解：[一句话描述场景]
  - 核心主线图（5±2 步，ASCII 或 Mermaid）
  - 文件-阶段对照表
  - 核心架构图（3-5 组件，复杂关系用 Mermaid）
  - 关键参数表

## 二～N：按主线顺序逐步深入
  每节结构：
    > 📍 位置：主线图第 X → Y 格
    ⚠️ 常见误解（如有）
    第 1 层：问题动机
    第 2 层：直觉 + 类比（优先用主线示例场景）
    第 3 层：代码走读 + shape 标注 + 最小有效片段
    第 4 层：设计理由 + 替代方案对比
    > 🔙 回到主线图：[当前状态] → [下一步预告]
    学生自检
    🛠 动手实验（深度版）

## 全流程实操手册
  按顺序的 Shell 命令，附预期输出

## 附录 A：概念速查表
  | 概念 | 英文 | 分级 | 一句话 | 位置 |

## 附录 B：常见问题 Q&A
  学生视角的问题 + 解答

## 附录 C：[核心组件] 可视化数据流图
  Mermaid 或 ASCII art 图

## 附录 D：教学反馈记录与修订流程
  | 日期 | 学生反馈 | 根因 | 修订内容 |

## 扩展阅读（可选，深度版，适合训练相关项目）

> ⚠️ 扩展阅读不是附录——附录是\"查资料用的\"，扩展阅读是\"有兴趣深入时才读\"。两者在学生心理中的定位完全不同。

**扩展阅读与主文档的关系：**
- 主文档的章节编号在扩展阅读之前结束（如一~十、附录 A-D）
- 扩展阅读独立成篇，不加数字编号前缀（不叫\"十一\"），用描述性标题
- 扩展阅读中可引用主文档步骤号，但主文档不依赖扩展阅读——学生跳过扩展阅读仍能理解全部核心原理

**什么内容适合放扩展阅读：**
- 训练加速技巧（AMP / compile / grad-ckpt / 混合精度）
- 多环境实战对比（本地卡 vs 云端 GPU）
- 上云训练入门
- 踩坑记录
- 硬件升级建议
- 下一步学习方向

**什么内容不适合放扩展阅读（应在主文档中）：**
- 配置文件导读（config.py）—— 这是\"总开关\"，属于步骤 0
- Next-Token Prediction 训练机制
- 采样策略详解
- 评估指标（PPL / Distinct-N）

每个扩展阅读小节：问题 → 方案 → 代码/命令 → 为什么有效 / 真实数据。
```

## 附录 D 修订流程

收到"某处没懂"的反馈后，按以下流程修订：

1. **定位** — 通过📍锚点找到对应章节
2. **诊断根因** — 检查四种可能：
   - a. 缺少前置概念 → 补 R7 前向引用，或按概念依赖图重组讲解顺序
   - b. 术语解释不足 → 检查是否核心术语误标为辅助，升级并补四步
   - c. 类比不精准 → 跑 R3 quality checklist，替换或补充主线示例类比
   - d. 缺少具体例子 → 补一个数值代入实例（R8 第 3 步）或 L2 动手实验
3. **修正**
4. **记录** — 在该章节末尾加修订标记：`> 📝 修订记录：202x-xx-xx 根据反馈改进了 XXX`

### 用户交互契约（学习/代码类任务）

当用户要求做教学文档或代码相关任务时：
- **只提供步骤，不主动执行命令**。除非用户明确要求助手来执行。
- 用户使用 conda 环境 `py312`（路径 `S:\condaEnvs\py312`），命令中需指定环境。
- 用户使用 PowerShell 终端，中文在 .ps1 脚本中会乱码。**所有 .ps1 文件内容必须用纯英文，不能包含中文文字。**
- 用户的 HuggingFace 缓存路径为系统变量 `HF_HOME=M:\huggingface_cache`，不需要在命令行中手动设置。

## 用户偏好（学习者交付模式）

本技能的输出对象是**学习者本人**。当用户要求写教案/报告时：

### 交付模式

- 只输出可复制粘贴的命令和步骤，不直接执行。除非用户明确要求运行。
- 文档用第一人称学习者视角，不用第三人称技术文档口吻。
- 格式简洁，不堆结构化术语（"实验设计""动机""方案""核心经验"等标签）。
- 缩写处用长破折号 `——` 等简洁符号。
- 表格保持简洁，不加额外"比 cls 差距""趋势"等分析列。

### 学习报告生成

- 从学习者的真实迭代过程出发，不是罗列实验结果。
- 标题用自然语言，不用"步骤 ①""技巧 1"这种编号格式。
- 结论用"我学到了"的第一人称，不用"经验""教训"等说教式标签。

---

## 常见错误对照表

| 错误 | 修正 |
|------|------|
| 自底向上讲（先细节后全貌） | 永远从主线图开始。学生需要"挂衣服的架子"。 |
| 所有术语同等展开 | 按 R1 分级：核心走 4 步，辅助走 2 步。 |
| 缺少中英术语对照 | 概念速查表加英文列；核心术语首次出现括号标英文。 |
| 术语未解释或解释不全 | 每个术语按等级跑对应步骤。 |
| 提前引用概念但不给落脚点 | 用 R7 前向引用协议：一句话定义 + 章节锚点。 |
| 🔜锚点在附录Q&A中"回收"，但Q&A是问答体不满足R1四步 | 要么改为在正文中用"🔜回收"独立段回收，要么把附录条目改写为R1四步格式。 |
| 🔜承诺了但没兑现（"详见代码走读"但代码走读里没展开） | 交付前搜索全文 `🔜 后详`，逐一确认对应的 `🔜 回收` 或正文展开存在。数量必须相等。 |
| 讲完概念就跳到下一个，学生丢失主线位置 | 用 R7 后向锚定 🔙 回到主线图。**必须在起草时写入，不要留到事后修补。** |
| 写完文档后补 🔙 锚定（事后修补费时且易漏） | 起草每节时就把 🔙 写在 学生自检 之前。参考第3层代码走读结束后立即写。 |
| 每个概念用独立类比，学生频繁切换场景 | 设计一个贯穿全文的主线示例（阶段 2），所有类比围绕同一场景展开。 |
| 类比不精准 | 用 R3 checklist 逐项自查：核心机制是否精准映射？ |
| 代码片段贴太多，学生找不到重点 | 用 R2 最小有效片段原则：关键行 + 2-3 行上下文 + #...省略标注。 |
| 代码没有 shape 标注 | 每个张量操作后加 `# (batch, seq, hidden)`。 |
| 公式只给符号不解释 | 按 R8 四步展示：算什么 → 逐符注释 → 数值代入 → 意味着什么。 |
| 跳过了"为什么" | 每个组件必须回答：在没有它之前，存在什么问题？ |
| 不讲常见误解 | 阶段 1 预判误解，正文 R5 格式前置解答。对最易踩的坑用第一人称叙事。 |
| 没有自检题和动手实验 | 标准版每节至少自检题；深度版加 L2 动手实验。 |
| 自检题出了但没给答案 | 学生自检的答案必须随教案交付——要么紧接自检题之后写 `🔑 参考答案`，要么集中放在附录（如「附录C：学生自检参考答案」）。自查方法：搜全文 `学生自检` 和 `参考答案`，数量必须对应。 |
| 自检题描述了场景但没有明确冲突 | 学生看到"位置 5 是 B-company，位置 6 emission 是 I-name 0.85 分"会以为这是道计算题。正确做法：**先描述矛盾**——"emission 说应该接 I-name（高分），但 transition 禁止 B-company→I-name（低分）"——再问 Linear 和 CRF 各自怎么处理这个冲突。自检题的目标是让学生理解两个模型的**冲突解决机制不同**，不是算数。 |
| 讲代码不讲概念 | 代码只是概念的载体。如果一个概念离了代码就讲不清楚，说明没理解透。 |
| 脱离真实语境 | 提及硬件约束、修过的 bug、平台 workaround。 |
| 大项目试图通读全部文件 | 按规模适配表选择阅读策略。 |
| ASCII 图画太细超过 20 行 | 改用 Mermaid 或拆成多张小图。 |
| 🔜 前向引用承诺了但正文没回收 | 写完文档后搜索所有🔜标记，逐一确认对应的章节确实讲了承诺的内容。在回收处加"🔜 回收"标签显式闭合。 |
| sed 修补中文文档导致格式损坏 | Windows Git Bash 的 sed 对中文+emoji 的插入/替换不可靠。修改已生成的文档时，用 write_file 重写整个段落，不要逐行 sed patch。 |
| `patch` 工具在 Windows 路径上失败 | `patch`（原生 Read/Edit 工具）在 Windows 路径报 `NoneType` 错误。替代方案：`ctx_edit`（lean-ctx 编辑工具）是唯一可靠的单段落修补方式，支持 old_string/new_string 替换。 |
| `read_file` / `patch` 在 Windows 路径上报 `NoneType` 错误 | 原生工具 `read_file` 和 `patch` 在 Windows 绝对路径上常见此错误。读取优先用 `ctx_read(path, mode)`，修改已生成的文档用 `ctx_edit` 或 `write_file`。 |
| `ctx_edit` 在大段中文+特殊字符替换时静默失败或只部分替换 | Windows 下 `ctx_edit` 对含中文引号（「」、\""\）、反引号、emoji 的大段 old_string 匹配不稳定。**回退方案**：用 `execute_code` + Python 原生 `open().readlines()` → 切片 → `open().writelines()` 完成整段删除/替换。`ctx_edit` 仅用于单行或短段落（<200 字纯 ASCII）的精确替换。 |
| `execute_code` 沙箱报 `SyntaxError: invalid character '→' (U+2192)` | Python 沙箱对 Unicode 箭头、emoji 等特殊字符敏感，源码中出现 `→` 会直接触发 SyntaxError。**回退方案**：将含特殊字符的内容先通过 `write_file` 写入临时文件，再在 `execute_code` 中用 `open().read()` 读取后做替换。临时文件路径在 Windows 下需用原始字符串 `r"..."`。 |
| PowerShell 含中文路径的脚本执行失败 | 生成 `.ps1` 脚本时，`cd` 指令中的中文路径（如 "项目"）会因编码问题变成乱码。修复：脚本内不写 `cd`，让用户自行切目录；脚本正文全部用英文。 |
| 拿到反馈不知道怎么改 | 按附录 D 修订流程：定位 → 诊断 4 种根因 → 修正 → 记录。 |
| 配置文件（config.py）被当成附录略过 | 配置文件是"总开关"，必须作为**步骤 0**在主线图开始前单独讲解。参数分组（架构/训练/生成/加速）+ 每段代码走读 + 解释"改这个数字会怎样"。 |
| 教案中的理论推导与实验数据不一致时没有指出 | 跑完实验后必须将教案中的预期值替换为实测值，并在不一致处增加"实测纠正"说明。例如：池化策略的 cls 预期最佳但实际 mean 更好——需要在教案中解释原因。 |
| Mermaid 图中 `[[节点名]]` 内使用 `→` 箭头字符 | Mermaid 的 `[[...]]` 是 subroutine 节点形状，内部解析严格。`→` 在 `[[...]]` 内会被解析为边语法，导致 `Parse error: Expecting 'SUBROUTINEEND'`。改用纯文本如 `["[CLS] Pooler Tanh"]` 或 `["节点 A > 节点 B"]`。 |
| 生成新一周教案前不检查前几周已教内容 | 导致 40% 篇幅重复旧知识（如 Week04 BERT 基础、Week05 训练循环）。**阶段 1 研究吸收必须加一步**：搜索前几周教案的 `★新` 标记、章节标题，列出已教概念清单，在新教案中用 📎 回链替代重讲。详见 `references/multi-week-redundancy-check.md`。 |
| 把前几周已讲过的概念标记为 ★新 | 用户在教案交付后会指出来（如"分层学习率 Week06 讲过了"）。**生成时对每个标 ★新 的概念做交叉验证**：搜索前几周教案关键词 + 概念速查表，确认该概念是否真的是首次出现。已讲过的标 📎 复习。 |
| 学生自检题没有提供参考答案 | 教案里有 学生自检 但答不了。每个自检题必须附带答案——要么嵌在正文后（🔑 参考答案），要么集中在附录（附录C：学生自检参考答案）。自检答案需：直接回答问题 + 如涉及计算给数值实例 + 如涉及"为什么"给 2-3 句原理。 |
| `Path(model_path).resolve()` 把 HF 模型名转成本地路径 | 代码中 `str(Path(args.model_path).resolve())` 会把 `"Qwen/Qwen2-0.5B-Instruct"` 转成 `"E:\项目\Qwen\Qwen2-0.5B-Instruct"` 导致 `OSError: Repo id must use alphanumeric chars`。修复：对 HF 模型 ID 直接用字符串，不调 `Path().resolve()`。在阶段 1 研究吸收时检查所有 `from_pretrained()` 调用是否对 HF 模型名做了路径转换。 |
| 教案生成时把已教概念标为 ★新（如 Week07 的"分层学习率"在 Week06 已讲） | **交付前自检清单加一项**：对照前几周教案的 ★新 标记和概念速查表，逐条确认本周的 ★新 没有与已教清单重叠。重叠项降级为 📎 复习。此检查必须在初次起草时就做——事后 patch 中文文档的成本远高于一次写对。 |
| 训练/评估流程只讲机制不讲"你会看到什么" | 学生对"跑起来后屏幕上会出现什么"没有预期，容易恐慌（"PPL 2682 是不是崩了？"）。每个训练/评估章节必须附带带注释的真实终端输出示例，逐字段解释含义和判断标准。 |
| 技巧专题/加速技巧插在主流程中间 | 技巧专题会打断从步骤1到步骤7的叙事流。技巧专题应移到全文末尾作为扩展阅读，不加数字编号前缀，让学生自然读完主流程后再按需深入。 |
| 参考答案只给概念解释，没有可执行步骤 | 学生拿着答案必须能逐行执行。每个实验答案必须包含：精确行号 + 代码修改 + 可复制命令 + 带具体数值的预期输出 + 恢复步骤。详见「参考答案编写规范」。 |
| 参考答案的行号和命令凭记忆写，未验证源文件 | 写参考答案前必须读取实际源文件。代码注释中的数字可能已过时（类默认值 ≠ 配置文件实际值）。先用 `ctx_read` 读文件确认行号和默认值，再写答案。 |
| 多周系列教案中大量重复前几周已讲过的内容 | **阶段 1 研究时，必须先查前几周教案覆盖了哪些概念**（搜 session / Hindsight / 读取前几周教案文件）。列出"已教"清单，与当前项目概念做交集——交集部分只做 📎 复习引用，不重讲。本周真正的新知识用 ★新 标记。详见「新旧分离」。 |
| 教案中的准确率预期（如"BERT 57-62%"）与实际跑出的数据不一致 | 第一阶段生成教案时，对未验证的数值声明用"预期"或"基于通用经验"标注。**第二阶段（实验完成后）必须回到教案，用真实数据替换占位符**。如果实测结果与教案预期矛盾（如 cls 池化预期最佳但 mean 实测更高），在正文中增加"实测纠正"段，解释差异原因。实证结果比理论推导更有教学价值。 |
| PowerShell .ps1 脚本含 em dash 等特殊 Unicode 字符导致解析失败 | Write-Host 字符串中的 em dash（—）和 smart quotes 在 PowerShell 中会被解析错误。脚本内所有字符串只使用 ASCII 字符（连字符用 -，引号用直引号）。如果仍报错，改为 .bat 脚本或逐条命令方式。 |
| 云端 Linux 评估生成的 PNG 图表中文显示方框 | Cloud Linux 实例无中文字体（如 AutoDL 镜像），evaluate.py 生成的混淆矩阵和消融对比图中中文标签显示为方框。解决方案：本地重新跑评估（python src/evaluate.py --pool cls）即可生成正常中文图表。教案中标注此差异，说明"图表需本地生成"。 |
| 步骤顺序不合逻辑（如先讲模型再讲数据） | 数据是模型的输入——永远先讲数据，再讲基于数据的模型改动。遵循依赖链：数据特征 → 工程决策 → 模型改动。 |
| 学生不知道自己"哪些已经学过、哪些是新的" | 正文中使用 ★新 标记本周新概念，📎 WeekXX 标记复习内容。Mermaid 图中也标注 ★新。概念速查表中"分级"列使用「**新**」/「复习」标签。 |
| `train_sft.py` 中 `Path(args.model_path).resolve()` 把 HF 模型名转成错误的本地路径 | 查 `references/text-classification-pitfalls.md` 第 1 条。通用教训：传给 `from_pretrained()` 的路径要么是 HF 模型名（不加任何处理），要么是本地绝对路径——不要在两者之间做 `Path.resolve()`。|\n| 学生想用 LM Studio 的 GGUF 模型（如 `qwen3.5-9b-Q4_K_M.gguf`）做 SFT 训练 | GGUF 是纯推理格式，没有可训练权重张量，`bitsandbytes` / `peft` / `AutoModel.from_pretrained()` 都无法加载。训练必须用 HF 原始格式（safetensors 或 pytorch_model.bin）。GGUF 只适用于 LM Studio / llama.cpp 本地推理。对学生的回答：「GGUF 像 PDF——能读不能改。训练需要 Word 文档（HF 格式）。」 |\n| 训练脚本 checkpoint 命名不含所有可变参数（pool/层数/loss类型）——消融实验互相覆盖 | 默认配置（pool=mean, layers=4）保持短名兼容下游脚本；非默认参数自动加后缀。train_biencoder.py 示例：`_pool_tag = f\"_{args.pool}\" if args.pool != \"mean\" else \"\"`、`_layer_tag = f\"_L{args.num_hidden_layers}\" if args.num_hidden_layers != 4 else \"\"`。`compare_methods.py` 和 `analyze_badcases.py` 加 `--ckpt` 参数支持自定义路径。参考 `references/week08-cloud-patterns.md`。 |\n| 两阶段检索/CrossEncoder 精排时逐条 Python 循环调 GPU——GPU 利用率 8%，I/O bound | CrossEncoder 的 `tokenizer()` 和 `forward()` 都支持批量输入：传 list 而非单个字符串。`tokenizer([q]*len(cands), cands, ...)` → `model(**enc)` 一次前向处理全部候选。修复前 43 万次 GPU 调用，修复后 4316 次，~100x 加速。`two_stage_retrieval.py` 中 `encode_corpus()` 也有 `batch_size` 参数形同虚设的问题——收到 `batch_size` 但用 `for text in texts` 逐条编码。 |\n| PairDataset 返回的 batch key 带 `_a`/`_b` 后缀，自定义训练循环直接用报 `unexpected keyword argument` | `data_scale_ablation.py` 中的教训：自己写训练循环时，必须手动 `k.replace(\"_a\",\"\")` / `k.replace(\"_b\",\"\")` 把 key 映射回模型期望的 `input_ids`/`attention_mask`/`token_type_ids`。 |\n| 云上 matplotlib 中文字体：`SimSun-ExtG` 覆盖不全 + `bbox_inches='tight'` 导致图片爆炸（84335px） | 字体检测优先级：`msyh` > `simhei` > `simsun`，显式排除 `extg` 后缀。全局设 `fontManager.addfont()` + `rcParams['font.sans-serif']` 而非逐元素设 `fontproperties`。`savefig` 不用 `bbox_inches='tight'`，用 `subplots_adjust(top=0.85)` 给标题留空间。 |\n| 云上数据质量：HuggingFace 数据集合有拼接污染（多行被 `\\t` 拼进单字段，最长 51,842 字） | BQ Corpus（FinanceMTEB/bq_corpus）15 条污染样本。过滤：`len(sentence1)>200 or len(sentence2)>200` 即为异常。下载后必须跑 `explore_data.py` 检查 P95/最长。 |
| PowerShell .ps1 脚本中文路径/中文文字导致解析失败 | .ps1 脚本中 **所有文字必须用纯 ASCII**——中文路径、em dash、smart quotes 都会导致 `ParserError`。删掉脚本中的 `cd` 中文路径行，让用户手动切目录。 |
| 将当前项目源码中的概念误标为 ★新（如前几周已教过"分层学习率"，但它在当前项目代码中出现于是被标为新的） | **代码中出现 ≠ 学生未学过。** 冗余检查时，如果某个概念在当前项目代码中显式出现、但不确定前几周是否已教——先标注为"待确认"，然后问用户。不要默认"出现在这个项目的代码里 = 本周新教"。 |
| 在教案中声称"FC 版 Thought 不可见" | DeepSeek v4-flash 等模型通过 `reasoning_content` 字段返回 CoT 推理链，即使在 Function Calling 场景下也可获取。代码中用 `getattr(msg, "reasoning_content", None) or msg.content or ""` 提取。教案中应写"FC 版可通过 reasoning_content 获取思考过程"而非"不可见"。详见 `references/deepseek-reasoning-content.md`。 |
| Few-shot 对小型 chat-format LLM：把示例塞进 System Prompt 导致性能崩塌 | 正确做法是将示例作为独立 user/assistant 多轮对话插入，不拼进 System Prompt。详见 `references/few-shot-chat-llm-pitfall.md`。 |
| 用户用 PowerShell 粘贴多行 python -c 失败 | 改为存 .py 脚本文件执行。 |
| 多模型/多数据集实验时 checkpoint 和日志互相覆盖 | 当 `run_tag` 只包含 `dataset+use_crf` 而不包含模型名时，bert + cluener + Linear 和 roberta + cluener + Linear 会生成同名 `best_linear.pt`。修复：`run_tag` 必须包含模型短名（如从 `bert_path` 中提取 `bert`/`roberta` 等前缀）。参考 `Sequence_Labeling/src/train.py` 中的 `model_tag` 逻辑。 |
| Few-shot 对小型 chat-format LLM：把示例塞进 System Prompt 导致性能崩塌 | 对 <1B 参数的 chat-format 模型，正确做法是将示例作为独立 user/assistant 多轮对话插入（`messages.append(...)`），而非拼进 System Prompt 文本。后者会导致模型模仿示例格式而非遵指令输出。详见 `references/few-shot-chat-llm-pitfall.md`。 |
| 学生以为 GGUF 量化文件能直接训练 | GGUF（如 Q4_K_M.gguf）是纯推理格式，无 state_dict，无法加载到 PyTorch 做反向传播。训练必须用 HF 原始格式 + bitsandbytes 做 QLoRA。详见 references/gguf-vs-hf-for-training.md。 |
| 用户用 PowerShell 粘贴多行 python -c 失败 | PowerShell 不给多行 python -c 嵌套引号。改为存 .py 脚本文件执行。 |

| `pip install scikit-learn` 但 `import sklearn` — 包名≠模块名陷阱 | 在自动依赖检测的 Python 代码中，用 `pkg.replace('-','_')` 会把 `scikit-learn` 转成不存在的 `scikit_learn`。正确做法：用 `pkg_to_import` 字典显式映射（`{'scikit-learn': 'sklearn', ...}`），不依赖字符串替换。 |
| 手写训练/推理循环中 `.detach()` 缺失 | 非 `@torch.no_grad()` 上下文里调用 `.cpu().numpy()` 报 `RuntimeError: Can't call numpy() on Tensor that requires grad`。必须 `.detach().cpu().numpy()`。详见 `references/common-script-bugs.md`。 |
| 手写训练循环中 batch key 映射不对称 | PairDataset 的 `_a`/`_b` 后缀在自定义 epoch 函数中只给 enc_b 做 `replace(\"_b\",\"\")` 而漏掉 enc_a，导致 `TypeError: got unexpected keyword argument 'input_ids_a'`。详见 `references/common-script-bugs.md`。 |
| **教案中声称"FC 版 Thought 不可见"** | DeepSeek 模型（包括 v4-flash）默认通过 `reasoning_content` 字段返回思维链，即使在 Function Calling 场景下也可提取。错误根源：代码忽略了该字段而非 API 不支持。修正：`getattr(msg, "reasoning_content", None) or msg.content or ""`。警告：多轮对话必须将 `reasoning_content` 原样回传，否则 400。详见 `references/deepseek-reasoning-content.md`。 |
| 训练脚本 checkpoint 命名不含所有可变参数（pool/层数/loss类型）——消融实验互相覆盖 | 默认配置（pool=mean, layers=4）保持短名兼容下游脚本；非默认参数自动加后缀。train_biencoder.py 示例：`_pool_tag = f\"_{args.pool}\" if args.pool != \"mean\" else \"\"`、`_layer_tag = f\"_L{args.num_hidden_layers}\" if args.num_hidden_layers != 4 else \"\"`。`compare_methods.py` 和 `analyze_badcases.py` 加 `--ckpt` 参数支持自定义路径。参考 `references/week08-cloud-patterns.md`。 |
| 两阶段检索/CrossEncoder 精排时逐条 Python 循环调 GPU——GPU 利用率 8%，I/O bound | CrossEncoder 的 `tokenizer()` 和 `forward()` 都支持批量输入：传 list 而非单个字符串。`tokenizer([q]*len(cands), cands, ...)` → `model(**enc)` 一次前向处理全部候选。修复前 43 万次 GPU 调用，修复后 4316 次，~100x 加速。`two_stage_retrieval.py` 中 `encode_corpus()` 也有 `batch_size` 参数形同虚设的问题——收到 `batch_size` 但用 `for text in texts` 逐条编码。 |
| PairDataset 返回的 batch key 带 `_a`/`_b` 后缀，自定义训练循环直接用报 `unexpected keyword argument` | `data_scale_ablation.py` 中的教训：自己写训练循环时，必须手动 `k.replace(\"_a\",\"\")` / `k.replace(\"_b\",\"\")` 把 key 映射回模型期望的 `input_ids`/`attention_mask`/`token_type_ids`。 |
| 云上 matplotlib 中文字体：`SimSun-ExtG` 覆盖不全 + `bbox_inches='tight'` 导致图片爆炸（84335px） | 字体检测优先级：`msyh` > `simhei` > `simsun`，显式排除 `extg` 后缀。全局设 `fontManager.addfont()` + `rcParams['font.sans-serif']` 而非逐元素设 `fontproperties`。`savefig` 不用 `bbox_inches='tight'`，用 `subplots_adjust(top=0.85)` 给标题留空间。 |
| 云上数据质量：HuggingFace 数据集合有拼接污染（多行被 `\t` 拼进单字段，最长 51,842 字） | BQ Corpus（FinanceMTEB/bq_corpus）15 条污染样本。过滤：`len(sentence1)>200 or len(sentence2)>200` 即为异常。下载后必须跑 `explore_data.py` 检查 P95/最长。 |

| `pip install scikit-learn` 但 `import sklearn` — 包名≠模块名陷阱 | 在自动依赖检测的 Python 代码中，用 `pkg.replace('-','_')` 会把 `scikit-learn` 转成不存在的 `scikit_learn`。正确做法：用 `pkg_to_import` 字典显式映射（`{'scikit-learn': 'sklearn', ...}`），不依赖字符串替换。 |
| 手写训练/推理循环中 `.detach()` 缺失 | 非 `@torch.no_grad()` 上下文里调用 `.cpu().numpy()` 报 `RuntimeError: Can't call numpy() on Tensor that requires grad`。必须 `.detach().cpu().numpy()`。详见 `references/common-script-bugs.md`。 |
| 手写训练循环中 batch key 映射不对称 | PairDataset 的 `_a`/`_b` 后缀在自定义 epoch 函数中只给 enc_b 做 `replace("_b","")` 而漏掉 enc_a，导致 `TypeError: got unexpected keyword argument 'input_ids_a'`。详见 `references/common-script-bugs.md`。 |

## 新旧分离（多周系列专用）

当本周教案与之前周次有概念重叠时，必须执行此流程：

### 1. 查已教内容

在阶段 1 研究时，搜索前几周教案中已覆盖的概念：

```
方法：session_search("Week04 BERT") + session_search("Week05 训练")
     + 读取前几周教案文件（搜 "学生自检" "动手实验" 定位实际教学内容）
产出：已教概念清单（如：Tokenization、BERT架构、DataSet/DataLoader、训练循环、CrossEntropyLoss、过拟合）
```

### 2. 做交集分析

| 概念 | 状态 | 处理方式 |
|------|------|----------|
| 本周独有 | ★新 | 完整四步讲解 |
| 前几周已教 | 复习 | 📎 一句话回顾 + 回链 |

### 3. 结构体现 + 步骤顺序规则

- **零、前置回顾**（新增章节）：一页速查表列出所有复习概念 + 📎 回链。学生 5 分钟唤起记忆。
- **正文**：只讲 ★新 概念。复习概念出现时用 📎 格式（如 `📎 Week04 第 3 节`），不展开。
- **步骤顺序**：数据(EDA→工程决策) → 模型改动 → 训练技巧 → 评估。永不违反此依赖链。
- **Mermaid 图**：新组件标注 ★新，旧组件标注 `(Week04 已学)`。
- **概念速查表**："分级"列区分「**新**」和「复习」。

**四类标记格式：**

```
正文首次出现新概念：
  **分层学习率（Layer-wise LR）★新**

正文引用旧概念：
  BERT 本身 Week04 讲过了（📎 Week04 第 3 节）

Mermaid 图节点：
  A3["Pooling ★新<br/>cls / mean / max"]

概念速查表：
  | 分层学习率 | Layer-wise LR | **新** | ... |
  | Tokenization | Tokenization | 复习 | ... | 📎 Week04 |
```

## 交付前自检清单

逐项打勾，全部通过再交付：

- [ ] 文档第一页就能看到主线图？
- [ ] 选择了贯穿全文的主线示例？
- [ ] 每节标题都有📍位置锚点？
- [ ] 每个新术语都按 R1 分级处理（核心 4 步 / 辅助 2 步）？
- [ ] 所有核心术语首次出现时有英文括号标注？
- [ ] 每个🔜前向引用在目标位置有对应的回收解释（搜"回收"关键词验证）？
- [ ] 🔜指向附录时，附录条目的内容格式仍满足R1/R8要求（不能因为是Q&A就降级为问答体）？
- [ ] **所有🔜都已回收？**（搜索全文 `🔜 后详` 和 `🔜 回收`，数量必须相等。每处 `🔜 后详` 必须有对应的正文展开，并在展开处标注 `🔜 回收`）
- [ ] 每个章节结束时有一次🔙回到主线图的后向锚定？
- [ ] 代码片段遵守最小有效片段原则（关键行 + 上下文 + #...省略）？
- [ ] 每个公式都走了 R8 四步展示（算什么 → 逐符 → 代入 → 意味着）？
- [ ] 类比跑过 R3 quality checklist？
- [ ] 最容易踩的坑用了第一人称叙事？
- [ ] 深度版：每个大节至少一个 L2 动手实验？
- [ ] **所有学生自检题都有参考答案？**（正文中紧接自检题之后、或集中放在独立附录，不能只出题不给答案——学生拿着文档必须能对答案）
- [ ] 深度版：代码片段已在目标环境验证可运行？
- [ ] 概念速查表有中英对照列？
- [ ] 常见错误表里没有遗漏已预判的误解？
- [ ] （多周系列）前几周已教概念是否只做 📎 复习引用、未重复展开？
- [ ] （多周系列）本周新概念是否有 ★新 标记？Mermaid 图和速查表是否同步标记？
| `BertModel` 硬编码导致无法加载其他 BERT-like 模型 | `from transformers import BertModel` 和 `BertModel.from_pretrained()` 只能加载 BERT 架构。要对比 roberta-wwm-ext 等变体时，改用 `AutoModel.from_pretrained()`——一行改动即可兼容所有 BERT-family 模型。注意 `model.bert` 属性名在各架构下一致，不需要其他修改。 |

## 多周系列教学文档

当需要为一个课程生成多周循序渐进的教案时（如 Week01→Week02→Week03），遵循以下附加规则：

### 深度递进策略

| 周次 | 新概念 | 对旧概念的处理 |
|------|--------|---------------|
| 第 1 周 | 完整四步解释 | 无旧概念 |
| 第 2 周 | 完整四步解释 | 简要复习（2-3 句 + 回链"详见 Week X 第 Y 节"），然后快速带过 |
| 第 3+ 周 | 完整四步解释 | 一句话提及 + 锚点回链，不再展开 |

### 跨周钩子

每份教案的结尾 🔙 后向锚定中，必须预告下一周的内容：

```
> 🔙 回到课程主线：本周学会了 X。下一周（Week N），我们将学习 Y，
> Y 解决了 X 的 [某个痛点]，让你从 [当前能力] 升级到 [下一级能力]。
```

### 复习引用格式

在 Week N 引用 Week M（M < N）的内容时：

```
> 📎 复习：Week M 第 Y 节讲过 [概念名]（[一句话]）。
> 这里只回顾关键点：[1-2 句核心]。如需重读，回 Week M 教案。
```

### 概念速查表累积

Week N 的速查表应包含 Week N 的新概念 + 前几周出现但本周再次用到的旧概念（标注"复习"）。纯新概念正常标注"核心/辅助"。

### 执行顺序

生成系列文档时，必须按时间顺序（Week03 → Week04 → Week05），不能跳周。每生成一周，记录该周引入的新概念清单（写入 memory），供下一周参考。

### 跨周 🔜回收（关键步骤）

前一周的教案结尾或 Q&A 中可能留有 🔜 前向引用，承诺"下周详细讲解"。生成当前周教案时，**必须**：

1. **收集跨周承诺**：在阶段 1 研究吸收时，搜索上一周教案全文的 `🔜 后详` 标记，列出所有指向本周的承诺。常见位置：前一周的 `附录 B Q&A` 或结尾 `🔙 回到课程主线`。
2. **在正文中回收**：对每个跨周承诺，在当前周教案正文中创建独立的 `**🔜 回收：XXX（Week N Qx 的前向引用）**` 段，按 R1 四步格式完整解释。**禁止**把跨周 🔜回收 放在当前周的 Q&A 附录中（Q&A 是问答体，不满足 R1 四步格式要求）。
3. **自检验证**：交付前，搜索当前周全文的 `前向引用` 关键词，确认每个跨周承诺都有对应的正文 🔜回收 段。确认没有任何 🔜回收 留在附录 Q&A 中。

### 多周系列质量评估

产出全部周次教案后，建议运行一次跨周质量评估，检查递进是否平滑。评估框架（5 轴：概念密度/最大跳跃点/代码复杂度/隐喻一致性/认知过载风险）详见 `references/multi-week-evaluation.md`。

## 实战参考

曾用于一个 ~100M 参数的 GPT 模型项目（7 个源文件），产出 ~25,000 字教学文档。学生从"什么是 token"走到"完整前向传播 + shape 标注"再到"训练循环 + 梯度累积技巧"——全程锚定在一张 5 步管线图上，这张图出现在每个章节标题中。

## 参考文件

- `references/pretrain-models-to-hf-cache.md` — **【收到老师项目必读】** 将硬编码 `pretrain_models/` 路径迁移为 HF 模型 ID 的标准流程
- `references/cross-week-pitfall-checklist.md` — 跨周隐患检查清单：六项必查 + 扩展检查 + 搜索命令
- `references/incremental-experiment-design.md` — **【实验设计必读】** 四层递进结构 + 三角形判断法 + 典型反例
- `references/checkpoint-naming-consistency.md` — 跨脚本 checkpoint 命名一致性规则
- `references/multi-dataset-experiment-matrix.md` — 多数据集实验矩阵扩展：每个数据集独特价值 + `--resume_from` 混合训练模式
- `references/few-shot-multi-turn.md` — Few-shot 多轮对话技术要点（小 LLM 正确/错误做法对比）
- `references/week03-retro.md` — Week03 教案生成复盘（🔜回收漏洞、公式缺 R8、sed 损坏）
- `references/week05-retro.md` — Week05 教案生成复盘（跨周 🔜回收 放在 Q&A、漏 🛠实验）
- `references/week05-answer-example.md` — Week05 参考答案实战案例（九要素格式 + 关键行号速查）
- `references/multi-week-evaluation.md` — 多周系列教案质量评估框架（5 轴：概念密度/最大跳跃点/代码复杂度/隐喻一致性/过载风险）
- `references/week06-text-classification-empirical-results.md` — Week06 文本分类三种方案实测数据池，含池化反直觉发现、LoRA r 消融、零样本解析器优化等结果
- `references/python_hf_path_trap.md` — HuggingFace 模型名与本地路径的 Path.resolve() 冲突陷阱文档
- `references/multi-week-redundancy-check.md` — 多周教案冗余检查（生成前必须先搜索前几周已教内容，用 📎 回链替代重讲）
- `references/few-shot-chat-llm-pitfall.md` — 小型 chat-format LLM 的 Few-shot 提示工程陷阱：示例不应塞进 System Prompt，应用多轮 user/assistant 对话格式
- `references/text-classification-experiments.md` — 文本分类多方案对比项目的 6 个 L2 实验设计模板 + 4 种 loss 对比实验（plain/balanced/soft/focal）
- `references/text-classification-pitfalls.md` — 文本分类项目已知坑位（`train_sft.py` Path.resolve() bug、HF 镜像不可达、PowerShell 多行 python -c 等）
- `references/multi-week-evaluation.md` — 多周系列教案质量评估框架（5 轴：概念密度/最大跳跃点/代码复杂度/隐喻一致性/过载风险）
- `references/local-llm-debugging.md` — 本地 LLM（LM Studio / Ollama）三步连通性验证：模型格式自查→回声测试→多 prompt 格式对比→异常排查矩阵
- `references/cloud-bug-fix-on-the-fly.md` — 云上运行中修复脚本 bug 的模式（scp + marker 补跑）
- `references/depth-upgrade-execution.md` — 标准版→深度版 5 步升级工作流
- `references/common-script-bugs.md` — **手写训练/推理脚本两个高频 Bug**（detach 缺失、batch key 映射不对称）
- `templates/实操手册-stage-template.md` — 全流程实操手册模板
- `references/deepseek-reasoning-content.md` — **【写 Agent/FC 教案必读】** DeepSeek 模型 Function Calling 下 reasoning_content 字段的真相：FC 版并非"Thought 不可见"
- `references/production-readiness-audit.md` — **【深度版推荐】** ML/RAG 项目教案的生产级可落地性审计框架（六缺口 + 两断层 + 七差距）
- `references/sse-async-blocking-pitfall.md` — FastAPI SSE：async 函数中直接消费同步 Generator 导致事件循环阻塞，修复用 run_in_executor + asyncio.Queue
- `references/openai-sdk-object-serialization.md` — OpenAI SDK ChatCompletionMessage 对象混入 dict 列表导致 JSON 序列化 TypeError
- `references/multi-dataset-experiment-matrix.md` — Multi-dataset experiment design: matrix expansion, what each dataset uniquely enables, `--resume_from` pattern for hybrid training
- `references/text-classification-experiments.md` — Week06 TNEWS 文本分类实验数据汇总（池化/LoRA 消融/Loss 对比/零样本优化等实测结果）

- `references/cloud-run-all-pattern.md` — 云端多实验跑批 + 断点续传模式（marker 文件 + `run_step` 封装）
- `references/cloud-experiment-patterns.md` — 云端多实验跑批模式：marker 断点续传、checkpoint 命名防碰撞、GGUF vs HF 格式陷阱
- `references/cloud-checkpoint-safety.md` — 【★必读】云端 checkpoint 安全强制检查清单：5 条规则 + 污染链分析 + 修复模式
- `references/huggingface-data-quality.md` — HF 数据集质量检查：三步法 + 已知污染数据集 + 对教案影响
- `references/deepseek-reasoning-content.md` — **【教案必读】** DeepSeek FC 模式下思考过程可见性：`reasoning_content` 字段提取 + 多轮回传 400 陷阱 + 教案中正确/错误表述对照
- `references/pptx-extraction.md` — **【读取 PPT 必读】** Python-pptx 因 lxml C 扩展兼容性失败时的回退方案：zipfile + ElementTree 纯标准库提取 PPTX 文本
- `references/gguf-vs-hf-for-training.md` — GGUF（LM Studio 推理用）vs HF 格式（训练用）的区别：为什么 Q4_K_M 文件不能直接做 QLoRA、正确做法、显存预算

## 图形生成常见问题

### matplotlib 中文字体（Windows + 云端通用）

```python
# 模块级全局字体设置（必须在任何 plt.subplots() 之前调用）
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def setup_cjk_font():
    """自动检测中文字体并全局注册。优先级：微软雅黑 > 黑体 > 宋体"""
    all_fonts = fm.findSystemFonts()
    for keyword in ("msyh", "simhei", "simsun"):
        candidates = [p for p in all_fonts
                      if keyword in p.lower() and "extg" not in p.lower()]
        if candidates:
            fm.fontManager.addfont(candidates[0])
            font_name = fm.FontProperties(fname=candidates[0]).get_name()
            plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams.get('font.sans-serif', [])
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['axes.unicode_minus'] = False
            return True
    return False
```

关键点：
- `fontManager.addfont()` 注册字体文件，`rcParams` 设全局默认 → 不再需要每个元素单独设 `fontproperties=`
- 排除 `SimSun-ExtG`（覆盖不全），优先 `msyh`（微软雅黑完整 CJK）
- 云端无中文字体时返回 False，调用方改用英文标签（参考 evaluate.py 已做）

### tight_layout 失败导致图被拉长

当 `fig.suptitle()` 存在时，`tight_layout()` 可能因标题空间不足失败，导致 `savefig(bbox_inches='tight')` 把图垂直拉长。
修复：`fig.tight_layout(rect=[0, 0, 1, 0.92])` — rect 给 suptitle 预留顶部 8% 空间。

## 代码编写常见 Bug

### Model.encode() 返回带 grad 的 Tensor → .cpu().numpy() 报错

`BiEncoder.encode()` 在 eval 模式下仍可能返回 requires_grad=True 的 Tensor。
修复：`.detach().cpu().numpy()`（不能省略 `.detach()`）。
影响脚本：`two_stage_retrieval.py`、任何在 `torch.no_grad()` 外部调用 encode 的评估代码。

### PairDataset batch 的 key 后缀映射

PairDataset 返回 `input_ids_a` / `input_ids_b` 等带后缀的 key，但 `model(enc_a, enc_b)` 期望 `input_ids` 等无后缀 key。
修复：显式遍历映射，用 `.replace("_a","")` / `.replace("_b","")` 去后缀。
影响脚本：`data_scale_ablation.py`、任何直接构造 enc_a/enc_b 的训练代码。

## 执行提示

0. **【收到老师初始项目时必做】将 `pretrain_models/` 路径迁移为 HF 模型 ID**：搜索全项目 `pretrain_models` 引用，改为 HF 模型 ID（如 `"bert-base-chinese"`、`"Qwen/Qwen2-0.5B-Instruct"`），同时修复 `Path().resolve()` 陷阱。详见 `references/pretrain-models-to-hf-cache.md`。
1. 加载此 skill 后，优先用 CodeGraph 获取项目架构全景（`codegraph_status → codegraph_files → codegraph_context`），再按需用 `ctx_read` 读文件（详见 `project-architecture-analysis` skill）。Windows 环境下优先用 lean-ctx MCP 工具：`ctx_read(path, mode)` 替代 `read_file`（后者在 Windows 路径上常返回 `'NoneType' object has no attribute 'join'`），`ctx_edit` 替代 `patch`（同样会 NoneType 失败）。`write_file` 适用于整段/整文件重写。
   **多周系列：额外搜索上一周教案全文的 `🔜 后详`，收集所有指向本周的跨周承诺。**
2. **【多周系列必做】执行冗余检查**：搜索前几周教案的章节标题、★新标记、概念速查表，画出重叠矩阵，决定砍掉还是 📎 回链。详见 `references/multi-week-redundancy-check.md`。
3. 确定受众知识基线、选择交付深度
4. 画出概念依赖图、确定讲解顺序
5. **检查 `Path().resolve()` 陷阱**：搜索项目中所有 `from_pretrained()` 调用，确认 HF 模型 ID（如 `"Qwen/Qwen2-0.5B-Instruct"`）没有经过 `Path().resolve()` 转换。
6. **步骤顺序铁律：数据 → 模型 → 训练 → 评估**。数据是模型的输入——永远先讲数据（EDA 发现 + 工程决策），再讲基于数据的模型改动（池化策略、分类头），最后讲训练技巧（分层 LR、类别权重、梯度累积）。不要先讲模型架构再讲数据——违反依赖链，学生无法建立前置上下文。
7. 在脑中画完主线图再动笔写任何一个字
7. 写完后逐项跑交付前自检清单（特别注意搜索所有🔜标记，确保每个都有对应的🔜回收）
8. 交付后提示用户：如果学生反馈"某处没懂"，按附录 D 修订流程处理
9. **修改已生成的教案时**：Windows 下原生 `patch` 也报 NoneType。优先用 `ctx_edit(path, old_string, new_string)` 做单处替换；多段/整段修改用 `ctx_edit` 逐段或 `write_file` 重写整个文件。不要用 sed 逐行 patch（`\n` 变字面 `n`、行号偏移）。
   **追加模式下**：用 `ctx_edit` 做 7-8 次精确插入（每次前 `read_file` 确认行号），不要重写整个文件——追加后文件可能超过 1000 行，重写代价太高。
10. **用户信任边界——步骤清单，不自动执行**：用户明确要求学习/实验类任务只提供步骤清单，**不主动运行任何命令**。交付格式为逐关清单（关卡 | 命令 | 预期 | □状态），每条命令独立成行，不嵌套 `&&` 连接。即使是"帮我准备"也不应默认执行——除非用户明确说"帮我执行"或"你运行"。此规则已在 memory 记录为用户偏好，任何时候自检：当前是在"给步骤"还是在"代执行"？
    - ❌ 看到"帮我准备一下"就默认去执行
    - ✅ 列出步骤 + 命令 + 预期输出，留由用户执行
    - 特殊情况：确认脚本可用的验证性命令（如 `ls`、`nvidia-smi`）可以代为查看结果后报告，但不应改变环境状态。

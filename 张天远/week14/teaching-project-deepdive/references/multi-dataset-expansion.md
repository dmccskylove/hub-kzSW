# 多数据集实验扩展模式

## 原则

每个数据集必须有**独特价值**，不能简单复制实验。用"这个数据集能回答 AFQMC 回答不了的问题"来决定加哪些实验。

## BQ Corpus 的特殊定位

BQ（86K 银行金融）处于 AFQMC（34K 蚂蚁金融）和 LCQMC（238K 开放域）之间：

```
AFQMC(34K金融) → BQ(86K金融) → LCQMC(238K开放域)
    小规模           中等规模          大规模
    金融·蚂蚁        金融·银行         开放域
    正负1:2.2        正负1:1           正负1.4:1
    无bias           待测              有bias
```

BQ 的核心价值在**领域内迁移**：AFQMC↔BQ 同属金融但不同机构，迁移损失应远小于 AFQMC↔LCQMC（金融→开放域）。

## 推荐实验配置

每个数据集跑 BM25 + BiCosine + BiTriplet 三个基线（可跨数据集横向对比），但不跑整份消融（CrossEncoder、SimCSE、SFT 等只在 AFQMC 上做）。

BQ 额外价值：3×3 领域迁移矩阵中填补"金融-金融"对照位置。

## 本会话实案

Week08 text_match 项目从仅 AFQMC 扩展到三重集：

| 阶段 | AFQMC | BQ | LCQMC |
|------|:---:|:---:|:---:|
| 核心 | 7 组（BM25/BiCosine/BiTriplet/CrossEnc/对比/BadCase） | — | — |
| 消融 | 7 组（pool/layer/epoch/margin/hardNeg） | — | — |
| 扩展·跨数据集 | — | 4 组（BM25/BiCosine/BiTriplet/迁移矩阵） | 7 组（BM25/BiCosine/BiTriplet/CrossEnc/SimCSE/两阶段/FAISS） |
| 扩展·专门 | 两阶段/SimCSE/HardNeg/SFT | — | 规模消融/混合训练/Length Bias |

总计 35 组，每个数据集贡献独特分析角度。

# Splitter V2 Stage2 题目边界基线

本轮对 `_research/gen_gold_draft.py` 候选规则做了有范围的 Stage2-1 边界调整：显式栏目标题成为 section，题目起点单独识别；未修改 Gold，未实现 shared_material、answer 或 analysis 的新识别。`gold_compare.py` 是正式对照器。
正确=Gold 单元与预测单元节点集合完全相同且角色相同；漏识别=未精确匹配的 Gold 单元；错误识别=未精确匹配的预测单元；边界错误=有同角色预测与 Gold 节点相交但范围不一致。
漏识别/错误识别统计单位为单元，可与边界错误重叠。程序额外输出 body/knowledge 等角色，此表只列本轮要求的七类角色。

## 样本结果

| 样本 | GoldCompare | Gold / 预测单元 | 错误/警告/提示 | 主要失败原因 |
|---|---|---:|---:|---|
| S01 | FAIL | 85 / 50 | 14 / 24 / 0 | MISSED_STRUCTURE×24, ROLE_MISMATCH×6, MERGE×6 |
| S11 | FAIL | 102 / 97 | 13 / 16 / 0 | MISSED_STRUCTURE×15, ROLE_MISMATCH×7, MERGE×6 |
| S12 | FAIL | 124 / 119 | 1 / 21 / 0 | MISSED_STRUCTURE×15, MERGE×6, TOC_AS_BODY×1 |
| S04 | FAIL | 158 / 42 | 41 / 42 / 0 | MISSED_STRUCTURE×21, MERGE×21, UNBOUND×20 |

## 按角色统计

### S01

| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |
|---|---:|---:|---:|---:|---:|---:|---:|
| section | 17 | 16 | 11 | 6 | 5 | 1 | 0 |
| toc | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| question_group | 36 | 21 | 20 | 16 | 1 | 1 | 0 |
| shared_material | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| answer | 14 | 3 | 0 | 14 | 3 | 12 | 0 |
| analysis | 9 | 0 | 0 | 9 | 0 | 0 | 0 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### S11

| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |
|---|---:|---:|---:|---:|---:|---:|---:|
| section | 23 | 17 | 15 | 8 | 2 | 0 | 0 |
| toc | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| question_group | 57 | 66 | 53 | 4 | 13 | 3 | 0 |
| shared_material | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| answer | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| analysis | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unknown | 3 | 0 | 0 | 3 | 0 | 0 | 0 |

### S12

| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |
|---|---:|---:|---:|---:|---:|---:|---:|
| section | 27 | 33 | 21 | 6 | 12 | 0 | 0 |
| toc | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| question_group | 78 | 71 | 68 | 10 | 3 | 2 | 0 |
| shared_material | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| answer | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| analysis | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unknown | 1 | 0 | 0 | 1 | 0 | 0 | 0 |

### S04

| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |
|---|---:|---:|---:|---:|---:|---:|---:|
| section | 22 | 1 | 1 | 21 | 0 | 0 | 0 |
| toc | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| question_group | 20 | 20 | 1 | 19 | 19 | 19 | 20 |
| shared_material | 20 | 0 | 0 | 20 | 0 | 0 | 20 |
| answer | 76 | 1 | 0 | 76 | 1 | 76 | 0 |
| analysis | 20 | 0 | 0 | 20 | 0 | 0 | 0 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## 总体失败类型

- `GROUP_SPLIT`: 4
- `MERGE`: 39
- `MISSED_STRUCTURE`: 75
- `ROLE_MISMATCH`: 33
- `TOC_AS_BODY`: 1
- `UNBOUND`: 20

绑定错误（UNBOUND）：20 对。角色表中的绑定错误端点分别计入题组和材料。

## 边界结果解读

四份正式 Gold 中 question_group 精确命中 142/191；GoldCompare 的 MERGE 共 39。具体按样本及角色列于上表。
S04 的 shared_material 未作为本轮识别目标；其关联/边界差异仍留在错误清单中，不作为已支持能力。

## 可重复性

同一 runner、相同 source SHA256、相同 Gold 文件与 StructDoc 代码会生成相同预测单元和对照统计；报告不含运行耗时等非确定性字段。

# Annotation batch 01：正式 Gold

本目录保存 Luna 正式 S01–S15 基线中的四份 Gold。源文件 SHA256 写在各 JSON 的 `source` 字段；原始讲义未修改。`units` 按结构顺序列出，锚点使用 Stage1 StructDoc 节点 ID。程序生成的临时候选和早期 Gold 初稿不作为正式答案。

## 采用口径

- 独立题目按题标为完整 `question_group`，小问不拆。
- 阅读材料使用 `shared_material`，通过 `bind_to` 绑定对应题组。
- 题型/训练/提升栏目为 `section`；知识法则、技巧和方法说明保留为 `knowledge`。
- 纯答案键标为 `answer`，逐题解释标为 `analysis`；解释中的题号不作为新题组。
- 目录标 `toc`，封面/标题与正文分离；原始编号忠实保留。
- 文本抽取无法判断的图像/公式内容使用 `unknown`，并记录原因。

## Gold 与自审统计

| 样本 | section | question_group | shared_material | answer | analysis | unknown | 覆盖/自审 |
|---|---:|---:|---:|---:|---:|---:|---|
| S01 | 17 | 36 | 0 | 14 | 9 | 0 | 196/196 内容节点；PASS |
| S11 | 23 | 57 | 0 | 0 | 0 | 3 | 672/672 内容节点；PASS |
| S12 | 27 | 78 | 0 | 0 | 0 | 1 | 351/351 内容节点；PASS |
| S04 | 22 | 20 | 20 | 76 | 20 | 0 | 681/681 内容节点；PASS |

所有 4 份 Gold 均由 `gold_compare.py` 自审，0 错误、0 警告、0 提示；完整性复核确认没有覆盖缺口、Gold 区间重叠或失效共享材料绑定。S04 的 20 篇材料分别显式绑定到对应阅读题组。S11 与 S12 的 unknown 仅表示指定图像/公式对象的纯视觉内容无法由文本抽取可靠判定；其结构节点仍完整覆盖。

## 文件

- `S01_gold.json` 至 `S12_gold.json`：四份正式标注（仅 S01、S04、S11、S12）。
- `S01_selfaudit.md` 至 `S12_selfaudit.md`：对应自审报告。
- `README.md`：本说明与统计。

# Splitter 逐块复核报告

1 份样本 × 2 个模板，共 2 个样本模板组合。其中 2 个有计划，1 个走规则路径，0 个走 PARTITION，1 个走原文保留路径。0 个组合存在异常或证据不足。全部 2 个组合尚待人工评审。

哈希核对使用评估器已记录的摘要。物理核对检查块及其归属。教学语义和教师学生逐题对应均待人工验收。逐块判定请填写 review_checklist.csv。

## S01 · 1v1

源哈希 verified，物理覆盖 verified，评估器记录的源块数 4。
计划 PLAN_CREATED_NOT_SEMANTICALLY_VERIFIED，路径 SEMANTIC。

- knowledge：b1
- immediate：b2
- final：b3
- 未归类：—
- 遗漏：—
- 重复：—
- 风险及待核对项：TEACHER_STUDENT_ALIGNMENT_UNVERIFIED, TEACHING_SEMANTICS_UNREVIEWED
- 证据问题：—

| 块 ID | 原计划槽位 | 原文短摘要 | 逐块核对项 |
|---|---|---|---|
| b0 |  | 星岛课堂（虚构封面） | COVER_METADATA_PROJECTED_TO_TEMPLATE_COVER |
| b1 | knowledge | 三角形有三条边。 | REVIEW_MATH |
| b2 | immediate | 画一个三角形。 | REVIEW_IMAGE |
| b3 | final | 比较两个三角形的周长。 | REVIEW_OLE |

## S01 · class

源哈希 verified，物理覆盖 verified，评估器记录的源块数 4。
计划 PLAN_CREATED_NOT_SEMANTICALLY_VERIFIED，路径 PRESERVATION。

- knowledge：b1, b2, b3
- immediate：—
- final：—
- 未归类：—
- 遗漏：—
- 重复：—
- 风险及待核对项：TEACHER_STUDENT_ALIGNMENT_UNVERIFIED, TEACHING_SEMANTICS_UNREVIEWED, PRESERVATION
- 证据问题：—

| 块 ID | 原计划槽位 | 原文短摘要 | 逐块核对项 |
|---|---|---|---|
| b0 |  | 星岛课堂（虚构封面） | COVER_METADATA_PROJECTED_TO_TEMPLATE_COVER, PRESERVED_REVIEW_TEACHING_SLOT |
| b1 | knowledge | 三角形有三条边。 | REVIEW_MATH, PRESERVED_REVIEW_TEACHING_SLOT |
| b2 | knowledge | 画一个三角形。 | REVIEW_IMAGE, PRESERVED_REVIEW_TEACHING_SLOT |
| b3 | knowledge | 比较两个三角形的周长。 | REVIEW_OLE, PRESERVED_REVIEW_TEACHING_SLOT |

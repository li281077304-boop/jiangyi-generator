# V1.2 产品一致性修复报告

日期：2026-10-06
分支：`feature/v1.2-c4-release-engineering`
基线：`8aa513248cfd557d68583ac2cf7e210449bdd571`

## 范围与结论

本轮处理数据表题号误判、独立 metadata 解析、两种 Renderer 共用最终产品规范化，以及 Restart 时规范化输出哈希稳定性。GPT-6.1 Sol review 首轮发现表格归属逻辑未覆盖“顶层题组跨段落包住表格、表内误标 section 改写路由”；PATCH 复审又发现整题组覆盖会抹掉后续另一表的明确跨槽标题。现已将恢复范围限制在误标签影响的题组连续区间，并增加双表 fail-closed 回归。C4 Release 仍暂停；未构建 EXE、未创建 release tag，也未创建 C5 分支。

当前代码与产品门禁有充分通过证据，但**最终 GPT-6.1 Sol review 尚未完成**。因此本报告不声明 `PRODUCT_CONSISTENCY_FIX_PASS`。

## R1：数据表与路由

`_is_top_level_paragraph_node` 现在同时检查 StructDoc 节点形状和对应物理块 `Block.kind`。表格单元格内容及 table container endpoint 不会被当成普通正文题号起点；完整表格仍按原子物理块处理，真实跨槽归属继续 fail closed。

当前代码对固定 27 份来源重新运行生产 `render_slots` 门禁：

- 来源 SHA：27/27 匹配。
- XML render + package：24/27 成功。
- X011：`TABLE_SLOT_CONFLICT`，question group `u082` 横跨 `knowledge/final`；保留拒绝。
- X026、X027：`ProjectionError`，selected bookmark ID 缺失或不唯一；保留拒绝。
- 输出明细：`C:\xml-uat\v12-product-consistency-final2-20261006\scan-27-summary.json`。

X011 的阻断是题组真实跨槽，不是表格小数被提升成普通题号；本轮没有放宽这条边界。

交接现场记录的 job `72cab43961d6488c91b7a9e049265263` 与 `b251` 四行四列电压数据表已作为本轮根因背景继承，但该 job 的原始 runtime 文件没有出现在当前可访问的留存目录，因此本轮没有对该精确文件重新生成。报告不把 X011 当作该事故样本，也不声称已对 `b251` 做实机复现。

## R2：metadata 与最终产品规范化

- metadata 在 Router 选择前解析；字段可用原文或已审核的确定性规则填充。知识状态未确定或无可靠来源时，字段保留为空并提供字段级原因，不触发 whole-job fallback。
- XML 与 frozen V0.9 whole-job 输出都进入共享 `product_normalizer.py`。它在独立 staging 副本上识别模板封面与内容容器，更新封面字段并执行现有第一页锚点；不重新路由、去答案或重编号。
- 规范化后的文件才进入 Product Integrity、package validation 和最终发布 hash 检查。歧义结构 fail closed。
- 成品 ZIP entry timestamp 已固定为 1980-01-01；Renderer 只改变 ZIP 元数据时，最终规范化文件 SHA 保持稳定。对应 Restart 回归已通过。
- 字段缺失的提示沿 job warnings 持久化；未从模板示例或其他学科复制内容。

## 当前代码实跑与 WPS

使用当前工作树和固定 X008 九年级物理 teacher/student source pair，经生产 job service 生成：

| 路径 | Job | 结果 | 用时 |
|---|---|---|---:|
| 1对1 XML | `95ee31aa9ff44b7696516206559547a7` | `done`，teacher/student，package + integrity 通过 | 4.648 s |
| 班课 XML | `4ee3ad9c7a664dc0b576759bf9736b67` | `done`，teacher/student，package + integrity 通过 | 4.798 s |
| 强制 V0.9 fallback | `1f32e3939e3f46a9bfae41efea836684` | `done`，teacher/student，reason=`UNSUPPORTED_BOOKMARK_SCOPE` | 17.617 s |

三条路径的六份最终 DOCX 使用 WPS `KWps.Application` 完成 `Open → SaveAs → Close → Reopen → PDF`，6/6 PASS；DOCX 与 PDF 非空。WPS 明细：`C:\xml-uat\v12-product-consistency-final3-20261006\wps-roundtrip\report.json`。第一页 PDF 复核确认教学目标、重点难点均可见，知识回顾保持在约定位置；这不是逐页人工审阅所有题目/资源的声明。

此前误传的 X011/X012 UAT 尝试使用了错误的学科/年级选项，已排除在产品 PASS 证据之外；固定 X008 复测使用正确的物理/九年级选项。

## 回归

- 最终全量 pytest：469 passed、13 subtests passed、6 failed。
- 6 个失败：2 项 Windows launcher mutex/端口身份用例受当前机器已有实例/端口状态影响；4 项 `v1.1-stable` API 测试仍期待旧 API 行为。本轮没有改 launcher 或 V1.1 文件。它们记录为环境/冻结历史失败，不伪报全绿。
- 规范化 + Restart 稳定哈希定向组：8 passed、6 subtests passed。
- Stage2 focused：40 passed。完整 GoldCompare 仍保留既有 S01/S11 FAIL；本轮无法在当前配置重跑完整语料比较，因为 manifest 所指 ZIP 不在当前 corpus root。
- Stage3 比较器本轮重新运行，输入为冻结 checkpoint `ceaaf8b424738245fa9f6762cdb27bfd022d0905` 的预测产物；不是本轮重新执行 A-Line 预测。源 SHA 全匹配；QG 408/408，Recall/Precision 100%，exact 87.7%；sections 369/369；subquestions 328/328；MISS/FP/MERGE/SPLIT=0，errors={}。报告：`C:\xml-uat\v12-product-consistency-final2-20261006\stage3-compare.md`。
- GPT-6.1 Sol PATCH blocker 1：原 owner helper 要求 QG span 起止是同一个顶层段落，且在表内 section 已改写 routes 后才检查目的槽。针对 QG `b3..b5` 包住表格 `b4`、表内 A-Line section 为 `L1两端电压/V` 的最小回归，现改为依据顶层段落范围、唯一 QG、既有候选分槽和明确 section 边界确定 owner；只有非明确标题的表内标签跟随题组。
- GPT-6.1 Sol PATCH blocker 2：同一 QG 中 b4 测量表之后的 b6 “巩固练习”表不得被前一张表的路由恢复覆盖。现在只改写当前表及非明确 cell label 影响的连续区间，并在下一个 section 边界停止；双表回归验证仍以 `TABLE_SLOT_CONFLICT` 拒绝。`test_slot_router` 全部 22 项通过，py_compile 与 diff-check PASS。多题组共享表格跨槽及表内明确跨槽 heading 的既有 fail-closed 测试仍通过。
- Frozen V0.9 runtime：10/10 SHA 与 baseline `0922e08631226b95a77a6599bbc0ac3784e9134b` 匹配。
- Python compile、前端 JS syntax、`git diff --check`：PASS。

## C5 证据与范围

已留存的产品 corpus scan 中，S03 是一个真实原始来源：SHA-256 `bfcec1ef64ec9d6d3ade8a319cff2e0f0167aebc96a60d8fa760b4c4cab7559b`，class 模板；table block `b260` 的单行单物理单元格内有 7 个顺序段落，并含 inline image 与 OMML，因 knowledge/immediate 目标跨越原子表而拒绝。它是有限 Layout Table 候选证据，但不等于允许拆表。

在 GPT-6.1 Sol PASS 前不创建 C5 分支、不实现 Layout Table。C5 计划要求的额外 20 份日常原始 DOCX 清单尚未收集；数量不足时不得伪称覆盖率结论。

## 下一步

本次真实事故 job `72cab43961d6488c91b7a9e049265263` 的原始文件仍不可访问，故修复回归使用结构等价的最小 fixture，不宣称精确事故源已复放。最新 PATCH 提交推送后交 **Codex GPT-6.1 Sol** 再审；即使复审通过，也需如实保留事故源复放缺口。未完成独立 review 前不声明 `PRODUCT_CONSISTENCY_FIX_PASS`；不创建 C5 分支、不恢复 C4 Release、不打 tag。

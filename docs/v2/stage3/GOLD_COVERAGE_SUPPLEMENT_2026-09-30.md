# Supplemental Gold Coverage Correction — 2026-09-30

**判定：`PASS`（1 个新增 Gold 覆盖遗漏，源文证据高置信度）**

## 审核依据

E1 residual patch 把此前未进入 FP 清单的 X012 `b481`（order 557）恢复出来。独立复核确认它是一个完整题组：源节点有编号“6．计算”及公式，紧随其后是明确答案和详解，题5已经结束而题7另起。依 Splitter Business Rules v1.0 的 R2/R5，作为完整题加入 Gold。

此题在上一轮 22 题审核中未出现，是因为当时冻结的 E1 patch 尚未识别该边界。修正只添加一个 question_group，没有更改其他 Gold 语义。X012 Approved Gold 由 55 增至 56；Stage3 Gold 总数由 407 增至 408。

## 冻结与当前预测测量

| 数据 | Gold QG | Pred QG | Precision | Recall | Exact boundary | MISS | FP | MERGE/SPLIT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 冻结 Splitter（ceaaf8b） | 408 | 207 | 99.5% | 50.5% | 49.8% | 202 | 1 | 0/0 |
| E1 后预测（7be764b） | 408 | 409 | 99.5% | 99.8% | 86.8% | 1 | 2 | 0/0 |

Gold 修正后 E1=0，E2=1，E3=2，E4=14，E4_SECONDARY=3；MERGE/SPLIT=0/0。原卷 Recall 100.0%，Exact 99.4%。当前两个 FP 分别是已确认的知识定义列表条目和 X013 教学目标条目。

## 分层与校验

原卷 Gold=180、解析版 Gold=228；E1 后解析版 Recall=99.6%，Precision=99.6%，Exact=76.8%，MISS=1、FP=1。按学科分层的完整结果在 [`GOLD_COVERAGE_SUPPLEMENT_2026-09-30.json`](GOLD_COVERAGE_SUPPLEMENT_2026-09-30.json)。

`check_gold_schema.py`：8/8 样本，0 个问题。GoldCompare 在冻结 predictions 和 E1 后 predictions 上均使用同一份 Gold。Source DOCX 与预期 SHA-256 一致；修正前后 Gold 哈希和 prediction 哈希已记入 manifest。

## 文件记录

- Gold 只在外部 `C:\xml-uat\stage3-expansion\gold_preparation_01\APPROVED_GOLD\X012_APPROVED_GOLD.json` 修改，并留有本轮前备份。
- 仓库只提交 correction manifest 和本报告，不包含第三方讲义全文。
- 实施基线为 `7be764b9b005c43b6e0cc1137337f2f61e1b9fde`；该版本的 E1 后预测位于 `C:\xml-uat\stage3-e1-residual-after\`。

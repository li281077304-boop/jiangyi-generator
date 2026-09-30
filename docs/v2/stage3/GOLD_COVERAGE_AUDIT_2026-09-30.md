# Gold Coverage Audit — 2026-09-30

**判定：`PASS`（高置信度 Gold 修正已应用并重测）**

## 范围与规则

独立复核 E1 补丁后出现的 23 个新增预测 FP。按原始 StructDoc 节点、邻接内容、题号、完整题干、选项/小问、答案与解析、所在教学区块逐项审核。治理依据为 2026-09-29 V1.2 Roadmap 与 2026-09-30 Splitter Business Rules v1.0；本轮只处理 Gold 覆盖，不改 Splitter、GoldCompare 或业务规则。

## 审核结果

| 样本 | 学科/文档 | 新增 FP | Gold 补记 | 判定依据 |
|---|---|---:|---:|---|
| X006 | 物理/解析版 | 1 | 1 | 编号35是完整实验题，含(1)至(4)，答案与解答另起；原 Gold 少记该题。 |
| X012 | 数学/解析版 | 14 | 13 | 13条为完整练习题，含选项、填空、数据表或小问及随后答案；order 47 的“3.求一个非零有理数的倒数……”位于“知识点02 倒数”定义列表，不是题。 |
| X025 | 化学/解析版 | 8 | 8 | 编号1、2、5、6、15、16、24、26均在练习区块，题干完整且有选项/连续实验小问，后有答案/详解。 |
| **合计** |  | **23** | **22** | 1 个真实程序误判继续留在 FP；另有原卷 X013 历史 FP。 |

所有新增 22 题均为高置信度。Gold correction manifest 记录每题的 source node ID、flattened order、子问题 ID、适用规则、裁定、Gold 前后哈希及 DOCX / 预测文件哈希。第三方讲义正文不复制进仓库。

## GoldCompare 重建结果

所有结果使用同一批 8 份 Approved Gold 和冻结预测 / E1 后预测；解析版与原卷分开。Gold 修正后 QG 总数为 407（原卷180、解析版227）。

| 数据 | Gold QG | Pred QG | Precision | Recall | Exact boundary | MISS | FP | MERGE/SPLIT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 冻结 Splitter（ceaaf8b） | 407 | 207 | 99.5% | 50.6% | 49.9% | 201 | 1 | 0/0 |
| E1 后预测（0d20ad9） | 407 | 404 | 99.5% | 98.8% | 85.7% | 5 | 2 | 0/0 |

### 分层结果

| 数据 | 文档类型 | Gold QG | Pred QG | Precision | Recall | Exact | MISS | FP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 冻结 Splitter（ceaaf8b） | 原卷 | 180 | 181 | 99.4% | 100.0% | 99.4% | 0 | 1 |
| 冻结 Splitter（ceaaf8b） | 解析版 | 227 | 26 | 100.0% | 11.5% | 10.6% | 201 | 0 |
| E1 后预测（0d20ad9） | 原卷 | 180 | 181 | 99.4% | 100.0% | 99.4% | 0 | 1 |
| E1 后预测（0d20ad9） | 解析版 | 227 | 223 | 99.6% | 97.8% | 74.9% | 5 | 1 |

E1 后按学科分别记录在 manifest 中（数学、物理、化学）；没有用混合平均隐藏差异。E1 后剩余错误：E1=4、E2=1、E3=2、E4=14、E4_SECONDARY=16，MERGE=0，SPLIT=0。两个 E3 为 X012 知识定义误判和 X013 原有教学目标误判。

22 个新增 Gold 起点全部与补丁后预测命中；20 个边界完全一致。另两处边界保留了源文完整内容：X006 第35题包含预测遗漏的第(4)问后续步骤；X012 第3题完整价格表到 order 737，选项/答案在其后。两者属于 Gold 保留完整题界、Splitter 当前边界偏短。

## Regression gate

`check_gold_schema.py`：8/8 样本，0 个结构问题；无 Gold QG 区间重叠。 GoldCompare：MERGE=0、SPLIT=0。原卷 Recall 仍为100.0%，Exact boundary 99.4%，没有回归。

## 修改记录与可追溯路径

- 外部 Approved Gold 只新增 22 个高置信度 QG，保留原有候选及裁定；Gold 修正仅存在于 `C:\xml-uat\stage3-expansion\gold_preparation_01\APPROVED_GOLD\`。
- 源文 DOCX 哈希、Gold before/after 哈希、预测文件哈希和逐条 node/order 记录见 [`GOLD_COVERAGE_AUDIT_2026-09-30.json`](GOLD_COVERAGE_AUDIT_2026-09-30.json)。
- baseline predictions：`C:\xml-uat\stage3-expansion\STAGE3_EXPANSION_BASELINE\`；E1 后 predictions：`C:\xml-uat\stage3-e1-after\`。
- 本轮未修改算法或 Splitter Business Rules；下个优先任务由剩余 E1 / true FP 等级别重新裁定，不在本次实现中展开。

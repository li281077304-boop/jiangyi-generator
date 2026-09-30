# Stage3 E1 Patch 报告：Answer/Analysis 后恢复 Question Boundary

- 分支：`feature/splitter-v2-struct-gold`
- Patch 类型：**仅 E1**（parser 状态转移 + strong question start helper）
- Gold：`APPROVED_GOLD/`（stage3-batch-01，385 QG，含 1 处 `GOLD_CORRECTION_BEFORE_BASELINE`）
- 状态：**`E1_PATCH_PASS`**

## 1. 根因

`tools/stage2_baseline/run_baseline.py` 里有两个叠加的抑制点：

1. **状态粘滞**：`detect()` 的 zones 循环中 `answer_area` 一旦置位就不再退出，
   此后所有节点的 zone 恒为 `answer` / `analysis`（`analysis_mode` 只在局部切换）。
2. **无条件跳过**：`detect_question_runs()` 中

   ```python
   if number is None or mode in ("knowledge", "answer", "analysis"):
       ... continue
   ```

   只要 zone 是 answer/analysis，**题号一律被丢弃**。

因此解析版 `Q1 → 答案 → 解析 → Q2 → …` 中，Q2 之后的所有题界都无法建立，
整篇塌成一个 `question_group`。这解释了解析版 R=12.7%、E1=178。

## 2. 业务规则依据

Splitter Business Rules v1.0 · R5：
**Answer / Analysis 结束后出现「明确、完整的新题干」时，必须结束上一题并开启新的 question_group。**
关键限定：不是「见编号就开题」，必须是**完整新题干**，不能把解析中的编号步骤误判成题。

## 3. 实现（最小改动）

只动 parser 状态转移与新增一个 strong start helper，**未重构、未触碰 Section / 知识区例题策略 /
shared_material / subquestion 规则 / Gold / GoldCompare / StructDoc 数据模型**。

1. 新增 `_recoverable_question_start(index, order, text)`：
   - 必须是编号起始，且不是答案键（`RE_COMPACT_ANSWER_KEY`）/ 纯选项答案行（`RE_PLAIN_CHOICE_ANSWER`）；
   - 长度门槛：默认 ≥12 字；**带明确题目标记（空括号 / 填空线）时可放宽**；
   - 排除解析引导句（`RE_EXPLANATION_TEXT`）；
   - 必须有**完整性证据**之一：题目线索词（`RE_QUESTION_CUE`）、题目标记、行内选项、
     考试来源括号 + 长题干、或其后紧跟选项列表；
   - 不使用任何样例 ID、学科词或特定年份。
2. 新增 `_following_option_run()`：其后 sibling 节点是否构成 `A./B./C./D.` 选项列表。
3. `detect()` 的 zones 循环中，在 answer/analysis 区内命中该 helper 时：
   产出 `question_group` 候选（evidence「答案/解析区后恢复的完整新题干」）、
   `analysis_mode=False`、`zones[i]="exercise"`，避免与答案行候选重复。
4. `detect_question_runs(..., skip_orders=recovered_starts)`：已恢复的起点不再重复产出候选。

## 4. 失败测试（先写测试，后改实现）

`tests/test_e1_question_recovery.py`（8 项）。补丁前 **3 passed / 5 failed**，补丁后 **8 passed**：

| 用例 | 内容 | 补丁前 | 补丁后 |
|---|---|---|---|
| Case A (X004) | analysis 后 `2．（…天津河西·期末）一种家用电能表…` 必须开新题组 | FAIL | PASS |
| Case A2 (X004) | Q3/Q4/Q5 逐条都要恢复题界 | FAIL | PASS |
| Case B (X006) | answer 后 `2．（2024秋•嘉峪关校级期末）火锅…` 必须开新题组 | FAIL | PASS |
| Case C (negative) | 解析步骤 `1. 由题意…` / `2. 乙的…` / `3. 丙…` **不得**开题；同 fixture 中真新题必须开 | FAIL | PASS |
| Case C2 (negative) | 答案键行 `1．B．甲选项不符合` 不得开题（题组起点恒为 1） | PASS | PASS |
| Case D (X003 原卷) | 78 个题界不得增减 | PASS | PASS |
| Case D2 (X013 原卷) | 39 个题界不得变化 | PASS | PASS |
| X012 (解析版) | 题组数 ≥40 | FAIL (24) | PASS (53) |

**老 Gold / 原有 regression**：`tests/test_stage2_baseline.py` **26 passed**（补丁前后一致，无退化）。
`tests/test_gold_compare.py` 24 passed。

## 5. Before → After（Stage3 APPROVED_GOLD）

匹配口径：起点节点相同＝matched；起止都同＝exact。

### Overall

| 指标 | Before | After | Δ |
|---|---:|---:|---:|
| Gold QG | 385 | 385 | — |
| Pred QG | 207 | 404 | +197 |
| Precision | 99.5% | 94.1% | −5.4pp |
| Recall | 53.5% | **98.7%** | **+45.2pp** |
| Exact boundary | 52.7% | **85.5%** | **+32.8pp** |
| MISS | 179 | **5** | **−174** |
| FP | 1 | 24 | +23 |
| MERGE | 0 | **0** | 0 |
| SPLIT | 0 | **0** | 0 |
| section P/R/exact | 100% / 100% / 100% | 100% / 100% / 100% | 0 |
| 小问 in-parent | 49.3% (143/290) | **89.7% (260/290)** | +40.4pp |

### 原卷（必须保护的基线）

| 指标 | Before | After | 判定 |
|---|---:|---:|---|
| Gold QG | 180 | 180 | — |
| Pred QG | 181 | 181 | — |
| Precision | 99.4% | 99.4% | **无变化** |
| Recall | 100.0% | 100.0% | **无变化** |
| Exact boundary | 99.4% | 99.4% | **无变化** |
| MISS | 0 | 0 | **无变化** |
| FP | 1 | 1 | **无变化**（X013 学习目标条目，补丁前即存在） |

**原卷指标逐项完全相同 → 无回归。**

### 解析版

| 指标 | Before | After | Δ |
|---|---:|---:|---:|
| Gold QG | 205 | 205 | — |
| Pred QG | 26 | 382 | +356 |
| Precision | 100.0% | 89.7% | −10.3pp |
| Recall | 12.7% | **97.6%** | **+84.9pp** |
| Exact boundary | 11.7% | 73.2% | +61.5pp |
| MISS | 179 | **5** | −174 |
| FP | 0 | 23 | +23 |

### X004 / X006（本轮主目标）

| 样本 | Gold QG | Before Pred | After Pred | Before MISS | After MISS | Before exact | After exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| X004 | 78 | 1 | **78** | 77 | **0** | 1 | 62 |
| X006 | 59 | 1 | **59** | 58 | **1** | 1 | 28 |

### 其余样本（逐样本）

| 样本 | 学科 | 类型 | Gold QG | Before Pred | After Pred | Before MISS | After MISS | After FP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| X003 | physics | 原卷 | 78 | 78 | 78 | 0 | 0 | 0 |
| X013 | math | 原卷 | 38 | 39 | 39 | 0 | 0 | 1 |
| X019 | chem | 原卷 | 20 | 20 | 20 | 0 | 0 | 0 |
| X021 | chem | 原卷 | 44 | 44 | 44 | 0 | 0 | 0 |
| X012 | math | 解析版 | 42 | 24 | 53 | 18 | 3 | 14 |
| X025 | chem | 解析版 | 26 | 0 | 33 | 26 | 1 | 8 |

## 6. E1 消解量

**E1：178 → 4（消掉 174 个，97.8%）**。剩余 4 例集中在 X012(3) / X025(1) / X006(1) 的个别位置。

## 7. Regression 与新增 FP 分析

- **新增 MERGE：0**；**新增 SPLIT：0**（结构未被并块或切碎）。
- **新增 FP：23**（1 → 24，其中 1 例为补丁前既有的 X013 学习目标条目）。分布：
  X012 14 / X025 8 / X006 1。逐条抽查后的性质分布（人工判读，**待下一轮复核**）：

| 性质 | 数量 | 例证 |
|---|---:|---|
| **真实新题，但 Gold 未覆盖**（完整题号 + 考试来源 + 选项/自带【答案】） | 22 | X012 `1．（2026·四川凉山·中考真题）2026的倒数是（ ）`（下接 `【答案】A` `【分析】`）；X025 `1．（2025·湖南·中考真题）鸡蛋气室中的气体来源于空气…`；X006 `35．（2024秋•襄州区期末）在“伏安法测电阻”的实验中：`（下接 (1)(2)(3)） |
| **真实误判**（知识/定义条目被当成题） | 1 | X012 order 47 `3.求一个非零有理数的倒数，把它的分子和分母颠倒位置即可。`——位于 `知识点02 倒数` 的 `1.倒数的概念… / 2.倒数的性质… / 3.求…` 列表内，仅凭线索词「求」通过了完整性门槛 |
| 补丁前既有 FP | 1 | X013 order 9 学习目标列表第 5 条（Gate 0 已从 Gold 剔除，pred 仍判为 QG） |

> 结论：新增 FP 主要由 **Gold 覆盖面不足** 造成（Gold 的 42/26 个题组来自与原卷的逐题配对，
> 未覆盖解析版后段的额外题块），**不是把解析步骤误判成题**；但确实存在 1 例真实误判（X012 定义条目）。

## 8. Remaining errors（本轮不动，转下一轮 candidate）

| 代码 | 含义 | Before | After |
|---|---|---:|---:|
| E1 | answer/analysis 后未恢复题界 | 178 | **4** |
| E2 | 知识精讲 / 随学随练中的完整题漏识别 | 1 | 1 |
| E3 | 非题目内容被误判为 question_group（FP） | 1 | **24** |
| E4 | 父题已识别但小问越界 | 3 | 14 |
| E4_SECONDARY | 小问越界（父题未识别 → E1/E2 连带） | 144 | 16 |
| E7 | shared_material / binding（diagnostic） | 0 | 0 |

**下一轮候选（不在本 commit）**：
1. **E3-a**：X012 知识条目「3.求一个非零有理数的倒数…」被误判 —— 线索词证据过宽，
   尤其是**短陈述句 + 单独一个「求/计算/判断」**。需限定「完整题干」而不只是「含线索词」。
2. **E3-b**：Gold 覆盖面复核（22 例疑似 Gold 遗漏）→ 若确认，应补 Gold 而不是改算法。
3. E2 / E4 各自样本量小，独立一轮处理。

## 9. 测试与复现

```bash
PY="C:/Users/Administrator/Desktop/工作/讲义生成器/讲义生成器flash版/res/python/python.exe"
"$PY" tests/test_e1_question_recovery.py     # 8 passed（补丁前 3 passed / 5 failed）
"$PY" tests/test_stage2_baseline.py          # 26 passed（老 Gold 回归）
"$PY" tests/test_gold_compare.py             # 24 passed
# Before / After 测量
"$PY" tools/stage3_goldcompare/run_approved_gold_compare.py --json docs/v2/stage3/baseline_result.json
"$PY" tools/stage3_goldcompare/rerun_predictions.py --out C:/xml-uat/stage3-e1-after
"$PY" tools/stage3_goldcompare/run_approved_gold_compare.py \
      --predictions-dir C:/xml-uat/stage3-e1-after --json docs/v2/stage3/after_result.json
```

- 冻结预测未被修改；After 预测写在仓库外的 `C:\xml-uat\stage3-e1-after\`（未入库）。
- Splitter 之外的文件（StructDoc / GoldCompare 评分逻辑 / Gold / COM / Renderer / UI）均未改动。

**状态：`E1_PATCH_PASS`**

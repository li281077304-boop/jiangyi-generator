# Stage3 GoldCompare 基线报告（APPROVED_GOLD × 冻结 Splitter）

- 冻结 checkpoint：`ceaaf8b424738245fa9f6762cdb27bfd022d0905`（**Splitter / StructDoc / GoldCompare 均未修改**）
- Gold：`APPROVED_GOLD/`（stage3-batch-01，含 1 处 `GOLD_CORRECTION_BEFORE_BASELINE`）
- 预测：`STAGE3_EXPANSION_BASELINE/<sid>/prediction.json`（同一 checkpoint 的冻结预测，未重跑）
- 匹配口径：起点节点相同＝matched；起止都同＝exact；MERGE＝一个预测单元吸收 ≥2 个 gold 题组；SPLIT＝一个 gold 题组被 ≥2 个预测单元切开

## 0. 摘要（TL;DR）

- Gold QG 合计 **385**；冻结 Splitter 预测 **207** 个。
- Overall：QG precision **99.5%** / recall **53.5%** / exact boundary **52.7%**；MISS **179**；FP **1**；MERGE **0**；SPLIT **0**。
- **原卷 vs 解析版是断崖式差距**：原卷 recall **100.0%**（exact 99.4%，MISS 0），解析版 recall **12.7%**（exact 11.7%，MISS 179）。
- section 层：precision / recall / exact 全部 **100.0%**。
- 结论：**当前 Splitter 在“原卷题界”上已接近满分，失效点高度集中在解析版的题界恢复。**

## 1. Overall

| 层 | Gold QG | Pred QG | QG P | QG R | Exact boundary | MISS | FP | MERGE | SPLIT | section P / R | 小问 in-parent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| question_group | 385 | 207 | 99.5% | 53.5% | 52.7% | 179 | 1 | 0 | 0 | 100.0% / 100.0% | 49.3% (143/290) |

- **小问归属**：49.3%（143/290 落在与其父题起点匹配的预测单元内）
  - 其中 **父题本身未被识别**（连带失败）：144；**父题已识别但小问越界**（真实 E4）：3

## 2. 按学科

| 层 | Gold QG | Pred QG | QG P | QG R | Exact boundary | MISS | FP | MERGE | SPLIT | section P / R | 小问 in-parent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| mathematics | 80 | 63 | 98.4% | 77.5% | 75.0% | 18 | 1 | 0 | 0 | 100.0% / 100.0% | 65.0% (26/40) |
| physics | 215 | 80 | 100.0% | 37.2% | 37.2% | 135 | 0 | 0 | 0 | 100.0% / 100.0% | 38.6% (78/202) |
| chemistry | 90 | 64 | 100.0% | 71.1% | 70.0% | 26 | 0 | 0 | 0 | 100.0% / 100.0% | 81.2% (39/48) |

## 3. 按文档类型（**关键分层**：不使用混合平均）

| 层 | Gold QG | Pred QG | QG P | QG R | Exact boundary | MISS | FP | MERGE | SPLIT | section P / R | 小问 in-parent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 原卷 | 180 | 181 | 99.4% | 100.0% | 99.4% | 0 | 1 | 0 | 0 | 100.0% / 100.0% | 97.8% (131/134) |
| 解析版 | 205 | 26 | 100.0% | 12.7% | 11.7% | 179 | 0 | 0 | 0 | 100.0% / 100.0% | 7.7% (12/156) |

## 4. 逐样本

| 样本 | 学科 | 类型 | Gold QG | Pred QG | Exact | MISS | MERGE | SPLIT | FP | 最主要错误 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| X003 | physics | 原卷 | 78 | 78 | 78 | 0 | 0 | 0 | 0 | — |
| X004 | physics | 解析版 | 78 | 1 | 1 | 77 | 0 | 0 | 0 | E1×77 / E4_SECONDARY×72 |
| X006 | physics | 解析版 | 59 | 1 | 1 | 58 | 0 | 0 | 0 | E1×58 / E4_SECONDARY×52 |
| X012 | mathematics | 解析版 | 42 | 24 | 22 | 18 | 0 | 0 | 0 | E1×18 / E4_SECONDARY×14 |
| X013 | mathematics | 原卷 | 38 | 39 | 38 | 0 | 0 | 0 | 1 | E3×1 |
| X019 | chemistry | 原卷 | 20 | 20 | 19 | 0 | 0 | 0 | 0 | E4×3 |
| X021 | chemistry | 原卷 | 44 | 44 | 44 | 0 | 0 | 0 | 0 | — |
| X025 | chemistry | 解析版 | 26 | 0 | 0 | 26 | 0 | 0 | 0 | E1×25 / E4_SECONDARY×6 |

## 5. 错误分类统计（Error Taxonomy）

| 代码 | 含义 | 数量 |
|---|---|---:|
| E1 | Answer/analysis 后未恢复新 question boundary | 178 |
| E2 | 知识精讲 / 随学随练中的完整题漏识别 | 1 |
| E3 | 普通 body / 非题目内容被误判为 question_group（False Positive） | 1 |
| E4 | 父题已识别，但 (1)(2)(3) 小问落在父题范围之外 | 3 |
| E4_SECONDARY | 小问越界（父题本身未被识别 → E1/E2 的连带，非独立缺陷） | 144 |
| E5 | 题组 MERGE（多题被并成一个单元） | 0 |
| E6 | 题组 SPLIT（一题被切成多个单元） | 0 |
| E7 | shared_material / binding 问题（diagnostic） | 0 |
| E8 | 其他 | 0 |

## 5b. 错误分类统计（按文档类型拆分）

| 代码 | 原卷 | 解析版 |
|---|---:|---:|
| E1 | 0 | 178 |
| E2 | 0 | 1 |
| E3 | 1 | 0 |
| E4 | 3 | 0 |
| E4_SECONDARY | 0 | 144 |
| E5 | 0 | 0 |
| E6 | 0 | 0 |
| E7 | 0 | 0 |
| E8 | 0 | 0 |

## 6. 代表性错误案例（每样本 ≤5）

### X003（physics / 原卷）

- （本样本无该类错误案例）

### X004（physics / 解析版）

- `E1` #AG-X004-QG-002 order=33 role=analysis「2．（24-25九年级上·天津河西·期末）一种家用电能表上的参数如图所示，下列说法错误的是（　　）」
- `E1` #AG-X004-QG-003 order=43 role=answer「3．（24-25九年级上·广东汕头·期末）如图所示是小明家的电能表，其标定电流为      A。用1度电」
- `E1` #AG-X004-QG-004 order=49 role=answer「4．（24-25九年级上·湖北武汉·期末）如图甲所示是某款智能语音爬楼“神器”，可以帮助腿脚不便的老年人」
- `E1` #AG-X004-QG-005 order=64 role=answer「5．（24-25九年级上·四川成都·期末）如图是小明同学在家中拍到的一张电能表照片，他仔细观察照片后，得」
- `E1` #AG-X004-QG-006 order=77 role=analysis「6．（24-25九年级上·广东广州·期末）如图所示，分别用甲、乙两个电热水壶装相同质量、相同温度的水后接」

### X006（physics / 解析版）

- `E1` #AG-X006-QG-002 order=42 role=answer「2．（2024秋•嘉峪关校级期末）火锅是重庆的特色美食，涮火锅时是通过　热传递　 的方式改变食物内能；寒」
- `E1` #AG-X006-QG-003 order=49 role=answer「3．（2024秋•广元期末）图甲是在一个配有活塞的厚壁玻璃筒里放一小团蘸了乙醚的棉花，当迅速压下活塞时，」
- `E1` #AG-X006-QG-004 order=61 role=answer「4．（2024秋•宿城区期末）小明在玻璃试管内装入适量沙子，将温度计插在沙子中。用力晃动十余下，发现温度」
- `E1` #AG-X006-QG-005 order=67 role=answer「5．（2024秋•海淀区期末）已知某种物质吸收的热量Q与比热容c、质量m和温度变化量ΔT之间满足Q＝cm」
- `E1` #AG-X006-QG-006 order=81 role=answer「6．（2024秋•包河区期末）如果在一个标准大气压下，将质量为1.5kg的水烧开需吸收热量为5.04×1」

### X012（mathematics / 解析版）

- `E1` #AG-X012-QG-002 order=31 role=analysis「2．计算： ______．」
- `E1` #AG-X012-QG-003 order=34 role=answer「3．（25-26七年级上·江苏连云港·期中）计算_______．」
- `E1` #AG-X012-QG-004 order=49 role=answer「1．的倒数是（     ）」
- `E1` #AG-X012-QG-005 order=55 role=analysis「2．一个有理数a的倒数等于它本身，那么a等于（     ）」
- `E1` #AG-X012-QG-006 order=59 role=answer「3．（2026·河北邯郸·二模）若，则“”表示的数是____．」

### X013（mathematics / 原卷）

- `E3` pred=u003 order=9「5.会根据指定精确度对有理数（整数、小数、大数、科学记数法表示的数）取近似值，能反向判断近似数的精确位数」

### X019（chemistry / 原卷）

- `E4` gold=AG-X019-QG-019 order=235「(1)轻粉微溶于水，是一种白色粉末，这句话描述了轻粉的_____（填“物理”或“化学”，下同）性质；」
- `E4` gold=AG-X019-QG-019 order=236「(2)材料中提及的轻粉的主要用途是_____。」
- `E4` gold=AG-X019-QG-019 order=237「(3)轻粉的保存方法应该为_____（填“阴凉处”或“光亮处”）密封。」

### X021（chemistry / 原卷）

- （本样本无该类错误案例）

### X025（chemistry / 解析版）

- `E1` #AG-X025-QG-001 order=83 role=answer「1．用如图装置测定空气中氧气的含量。」
- `E1` #AG-X025-QG-002 order=94 role=analysis「2．用来测定空气成分的方法有很多，小梅用如下图所示的简易装置来测定空气中氧气的含量。下列对该实验的认识中」
- `E1` #AG-X025-QG-003 order=130 role=answer「1．如图表示空气的组成（体积分数），气体X为」
- `E1` #AG-X025-QG-004 order=135 role=analysis「2．中国正在加速推进稀有气体国产化。下列气体属于稀有气体的是」
- `E1` #AG-X025-QG-005 order=169 role=answer「1．（25-26九年级下·黑龙江大庆·阶段检测）下列物质属于纯净物的是」


## 7. 诊断（只统计，不作为本轮失败判据）

| 样本 | Gold shared_material | Pred shared_material | Pred QG 带 binding | Pred QG 总数 |
|---|---:|---:|---:|---:|
| X003 | 0 | 0 | 0 | 78 |
| X004 | 0 | 0 | 0 | 1 |
| X006 | 0 | 0 | 0 | 1 |
| X012 | 0 | 0 | 0 | 24 |
| X013 | 0 | 0 | 0 | 39 |
| X019 | 0 | 2 | 1 | 20 |
| X021 | 0 | 0 | 0 | 44 |
| X025 | 0 | 0 | 0 | 0 |

> Gold 侧 8 个样本的顶层 `shared_material` 均为 0（G09 后材料降为 Q20 内部子结构），
> 因此**本批无法评估 shared_material / binding 能力**，需下一批样本补测。

## 8. Gate 0：Gold 自检结果

- `check_gold_schema.py`：8/8 样本 **0 问题**（无 span 重叠、无 parent/bind 悬空、无小问越界）。
- **X013 定点剔除**（`GOLD_CORRECTION_BEFORE_BASELINE`）：起点 `b4.r0c1.n4`（order 9）经结构证据判定为**学习目标列表第 5 条**——同一单元格 `b4.r0c1` 内为连续 6 条编号教学目标（`1.理解有理数乘方的意义…` → `6.通过观察、归纳…`），n4 与前后同级同构，不构成 question_group。已从正式 QG Gold 剔除（39 → 38）并留痕，未触动其余 38 个。
- 除 X013 外**未修改任何已批准语义**；`PROPOSED_GOLD/` 原样保留。

## 9. Top 问题与下一轮 Patch 建议（不在本轮修）

按数量排序：E1=178、E4_SECONDARY=144、E4=3、E3=1、E2=1。

**最大的 1–3 个真实问题**：

1. **E1（178 例）：answer / analysis 之后没有恢复 question boundary** —— 解析版几乎全部失分于此。典型：X004 `2．（24-25九年级上·天津河西·期末）…` 落在 `analysis` 单元内；X006 `2．（2024秋•嘉峪关校级期末）火锅…` 落在 `answer` 单元内；X012 `2．计算：______．` 落在 `analysis`；X025 全程 0 个 QG。
2. **E2（1 例）：知识区 / 随学随练中的完整题漏识别** —— X025 `b14`（拉瓦锡实验题 `1．` + `(1)(2)(3)`）被判为 `body`。这是唯一一条**非解析版**的题界漏识别，对应业务规则 R3/R4（例题可调度）。
3. **E3（1 例）：非题目内容被误判为 question_group** —— X013 `b4.r0c1.n4` 学习目标条目。量小，但说明规则对「表格内教学目标编号列表」缺少排除。

**建议下一轮只做 1 个 Patch**：E1（恢复题界）。理由：

- 单类错误占全部失分的约 54%；
- 原卷侧已 100% recall，修 E1 不会破坏原卷（回归可验证）；
- E2/E3 各自样本量小（1 例），适合作为后续独立 Patch。

**注意**：E4_SECONDARY（144）不是独立缺陷——它是 E1/E2 的连带（父题没被识别，小问自然无处可放）；真正独立的 E4 只有 3 例（X019：按 G09 裁定小问应属 Q20，而预测仍把 `b179–b181` 留在材料单元内）。

## 10. 口径说明

- **正式评分**：section、question_group、boundary(exact)、subquestion、MERGE、SPLIT、MISS、FP。
- **Diagnostic only（本轮不据此判定失败）**：answer / analysis 边界与 linkage、shared_material / binding。
  原因：Gold 对 answer/analysis 的要求是「归属正确优先」，部分 linkage 仍为 provisional；
  本批 Stage3 样本也缺少真正的顶层多题 shared_material。
- 原卷与解析版**分开报告**，不使用混合平均。

## 11. 复现方式

```bash
PY="C:/Users/Administrator/Desktop/工作/讲义生成器/讲义生成器flash版/res/python/python.exe"
# Gate 0：Gold 一致性自检（只报告）
python tools/stage3_goldcompare/check_gold_schema.py
# Gate 2：基线测量（只测量，不改算法）
python tools/stage3_goldcompare/run_approved_gold_compare.py \
       --out docs/v2/stage3/STAGE3_GOLDCOMPARE_BASELINE_REPORT.md \
       --json docs/v2/stage3/baseline_result.json
```

- 数据位置：Gold 在 `C:\xml-uat\stage3-expansion\gold_preparation_01\APPROVED_GOLD\`，
  冻结预测在 `C:\xml-uat\stage3-expansion\STAGE3_EXPANSION_BASELINE\<sid>\prediction.json`。
  **这两处均在仓库之外，未随本 commit 入库**（含第三方讲义原文，且可由脚本重建）；
  本 commit 只包含测量工具与本报告，路径常量见脚本头部。
- 冻结预测由 `C:\xml-uat\stage3-expansion\run_stage3_baseline.py` 在 checkpoint `ceaaf8b` 上生成，本轮**未重跑 Splitter**（避免任何行为漂移）。


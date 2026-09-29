# Splitter V2 · 第一阶段报告：结构读取与 Document Model

> 阶段目标：**让程序完整读取 Word 讲义中的结构信息，建立稳定的内部文档模型。**
> 本阶段**不做**任何知识/例题/练习/巩固判断，不改动旧 splitter 的输入与输出行为。
> 验收口径：**原始 Word 中有用的信息是否被完整、稳定地保留下来。**

---

## 0. TL;DR

- 新增旁路模块 `app/struct_doc.py`（纯标准库，不依赖 python-docx，不 import 任何旧模块），
  把 docx 读成 `StructDoc`（块序列 + 全部原始特征）。
- **11/11 自动测试通过**，其中含与 `docutils.scan_paragraphs` 的真实文件契约回归。
- **5 类真实样本零丢失**（正文 + 文本框双通道校验均 0.00% 缺失）。
- **全语料 229 份压测：0 崩溃，平均 47ms/份**；共 51,620 块全部落模。
- 两个重要实证发现（修正了研究报告的假设）：
  1. **38% 的段落藏在表格单元格内**（31,895 / 82,873），「全文一张表」的讲义真实存在；
  2. 旧管线的主力评估样本"速度讲义"**本身就是全文一表型**（body 仅 3 段 + 1 张表，594 段全在表格里）。

---

## 1. 修改文件

| 文件 | 变更 | 说明 |
|---|---|---|
| `app/struct_doc.py` | **新增** | 结构读取模块（约 400 行）。旁路：不 import 旧模块，仅 stdlib `zipfile` + `ElementTree` |
| `app/struct_dump.py` | **新增** | 人类可读 dump CLI：`python struct_dump.py <docx> [-o out.txt] [--full] [--max-blocks N]` |
| `tests/test_struct_doc.py` | **新增** | 11 个测试；`sys.path` 正确指向 `app/`（未重复旧测试路径错误） |
| `docs/v2/*.txt` | 本地生成 | 5 份真实样本的结构 dump（见 §4）。**故意不入库**：含第三方讲义原文且可随时重生成，已在 `.gitignore` 中排除 |

**未改动**：`docutils.py`、`split_engine.py`、`toc_split.py`、`xml_engine.py`、`runner.py` 等全部旧文件。
旧生产链路（`runner._split_blocks → auto_split → fill_blocks`）的输入输出零影响。

> 注：会话期间桌面被整理，仓库从 `Desktop\jiangyi-generator` 移到 `Desktop\工作\jiangyi-generator`，
> 语料从 `Desktop\讲义生成器` 移到 `Desktop\工作\讲义生成器`。本报告所有路径均为新路径。

---

## 2. 数据结构说明（最小 Document Model）

### 2.1 顶层

```
StructDoc
├── name                        文档名
├── blocks: [Block]             body 直接子级内容单元，按文档流顺序
├── body_size                   正文字号（半磅，最高频 eff_sz；穿透表格统计）
├── size_hist / style_hist      字号/样式分布（Stage 2 标题层的原始素材）
├── num_defs / num_usage        编号列表定义与使用计数
└── stats                       文档级统计
```

### 2.2 Block（内容单元）

```
Block
├── seq: int                    body 子元素全序（0-based，含表格/未知块）
├── pno: int | None             段落号（1-based，仅 w:p）—— 与 fill_blocks 契约严格一致
├── kind                        "paragraph" | "table" | "unknown"
├── text                        段落文本 / 表格扁平文本 / 未知块文本
│
│  —— 段落原始特征（表格/未知块为空）——
├── style_id / style_name       显式样式（缺省继承不计入，避免满屏 Normal）
├── outline_lvl                 大纲级别（段落级或样式级推导）
├── sz_direct / style_sz / eff_sz   字号三态：直接格式 | 样式推导 | 生效值
├── bold                        三态：True 全部 run 显式加粗 / False 混合 / None 继承未知
├── num: NumInfo                编号引用 {num_id, ilvl, fmt, lvl_text}（已解析 numbering.xml）
├── images: [ImageRef]          {kind: inline/anchor/vml, rId, target, cx, cy}
├── oles: [OleRef]              MathType 等 {rId, target, prog_id}
├── math_count                  OMML 公式个数
├── textbox_texts: [str]        文本框/艺术字内容（与正文分离存放）
├── table: TableBlock           仅 kind="table"
└── is_empty / note
```

### 2.3 表格递归

```
TableBlock → rows[r][c] = Cell
Cell
├── text / n_paras / has_image / has_nested_table
└── blocks: [Block]             单元格内段落/嵌套表，递归为完整 Block（保留全部特征）
```

**为什么必须递归**：实测全语料 31,895 个段落（38%）位于表格单元格内；
"速度讲义"594 段全部在 1 张表里。单元格只存文本会丢失章节标题的字号/加粗特征。

### 2.4 双索引契约（与旧管线对齐的关键）

- `pno` = body 直接子级 `w:p` 的 1-based 编号，**表格/未知块不占号** —— 与
  `docutils.scan_paragraphs` 和 `xml_engine.fill_blocks` 完全一致（测试锁定）。
- `seq` = **稠密块序号**（0-based，等于 `blocks` 列表下标，无空洞）—— 未来重排
  （例题前移/练习下沉）、gold 标注区间、分块区间一律用它，可安全当数组下标。
- `body_idx` = 原始 body 子元素下标。被跳过的元素（`sectPr`、书签）仍占号，
  因此可能不连续；用于回溯原始 XML 位置。
- 表格内段落 `pno=None`：它们不可被旧契约单独寻址，随表格整体移动（与 fill_blocks 语义一致）。

> 2026-09-29 修订：`seq` 原为「body 子元素全序」（跳过书签后会跳号），
> 导致下游按 seq 取数组下标时错位。已改为稠密序号，另立 `body_idx` 保存原始位置
> （由 Stage 2 预备工具 `gold_compare` 的区间运算暴露出来的问题）。

### 2.5 设计取舍（有意保持最小）

- **不构建层级树**：`outline_lvl`/字号层/`num.ilvl` 只是原始字段，父子推断留给 Stage 2。
- **不求编号实际序号**（跨段落计数器）：只解析格式定义（`decimal "%1."` / `chineseCounting "%1、"`）。
- **书签（bookmarkStart/End）跳过**：零内容锚点，不是内容单元；`sdt` 等真未知内容仍保留为 `unknown`。
- **mc:AlternateContent 渲染冗余去重**：同一文本框内容在 Choice/Fallback 出现两次时按段去重
  （不丢任何独特内容）。

---

## 3. 旧管线丢失信息对照（现状确认）

`docutils.scan_paragraphs` 只返回 `(序号, 文本, 含图)`。对照实测，以下信息在旧管线第一步即丢失，
本模块已全部恢复：

| 信息 | 旧管线 | 本模块 | 全语料实测规模 |
|---|---|---|---|
| 字号（直接+样式继承+docDefaults） | ❌ | ✅ 三态 | 字号层>正文覆盖 56.3% 文档 |
| 样式名 / 大纲级别 | ❌ | ✅ | 58.1% / 7.0% 文档 |
| 加粗 | ❌ | ✅ 三态 | 80.3% 文档 |
| 编号列表（numId/ilvl/格式） | ❌ | ✅ | 6,450 段 |
| **表格及单元格内部内容** | ❌（整体跳过） | ✅ 递归 | 642 张表、31,895 单元格段落 |
| 图片（内嵌/浮动/尺寸/目标文件） | ⚠️ 仅 bool | ✅ 全字段 | 5,568 处 |
| OLE 对象（MathType） | ❌ | ✅ | 14,792 个 |
| OMML 公式 | ❌ | ✅ 计数 | 235 处 |
| 文本框/艺术字 | ❌（混入正文或丢失） | ✅ 分离存放 | 42 处 |
| 未知内容（sdt 等） | ❌ 静默丢弃 | ✅ unknown 块原样保留 | 按需 |

---

## 4. 真实样本验证结果

样本覆盖任务要求的四类 + 一类 unknown 场景。
dump 文件为**本地生成、不入库**（含第三方讲义原文；生成命令见文末附录），
下表中所有数字均由 `_research/run_struct_dumps.py` 复跑得到。
零丢失校验：把源 XML 全部正文段（剔除文本框）与文本框内容分别和模型比对。

| # | 样本 | 特征 | 块 | 正文段 | 缺失 | 亮点 |
|---|---|---|---|---|---|---|
| 1 | 速度讲义（原以为"普通段落型"） | **全文一表** | 4 | 594 | **0** | body 仅 3 段；章节标题（sz=14pt B）、编号（chineseCounting）、~~~~分隔线（sz=15pt+图）全部在单元格内被还原 |
| 2 | 计数原理 解析版 | 大量表格 | 952 | 913 | **0** | 17 张表、534 个 OLE（MathType）；3x3 数字表格完整落模 |
| 3 | 计数原理 学生版 | 重复题型 | 273 | 250 | **0** | 15 个「题型N」以 sz=14pt B 段落清晰可辨（正是研究报告说的"被丢掉的信号"） |
| 4 | 分层训练 U5B（英语） | 图片/对象 | 246 | 209+8 | **0** | 246 张图（anchor/vml/inline 分类 + rels 目标）；艺术字标题进 textbox_texts |
| 5 | 阅读理解精讲（教师版） | unknown 场景 | 644 | 553 | **0** | body 级书签被正确跳过；16pt/14pt 字号层可见 |

全语料压测：**229 份、0 失败、10.8s（47ms/份）**；51,620 块全部落模。

dump 样例（样本 3，「程序眼里的讲义」）：

```
[0000 p#0001] sz=18pt B st=heading 1 ol0 img3(anchor) | 专题02  计数原理与二项式定理
[0004 p#0005] sz=14pt B | 题型1  两个计数原理
[0005   --- ] TBL 1x1
      r0c0:
        │ sz=12pt st=Plain Text | 思路：(1) 弄清完成一件事是做什么…
[0006 p#0006] sz=10.5pt ole8 | 1．（2025·浙江·模拟预测）将个相同的球放入…
[0008   --- ] TBL 3x3
```

---

## 5. 已知无法读取 / 本阶段不读的信息

| 信息 | 状态 | 影响与建议 |
|---|---|---|
| 编号列表的**实际序号值**（跨段计数器） | 只解析格式，未求值 | Stage 2 需要时实现（简单计数器即可） |
| 页眉 / 页脚 / 脚注 / 尾注 / 批注 | 未读（独立 part） | 讲义正文一般不含，若未来做页眉水印检测再补 |
| 修订记录（track changes） | `w:ins` 按"最终视图"计入正文；`w:del` 自然排除 | 语义合理；若需审计再单独处理 |
| 图表（c:chart）/ SmartArt 图形内部 | 未解析（graphicData 非 blip） | 如有后备图片会被当图片捕获；否则只知其存在。需要时再扩展 ImageRef 类型 |
| OMML 公式内容（m:t） | 只计数，未提取文本 | 公式还原是独立课题，V2 分块不需要 |
| 浮动图片的**页面锚定坐标** | 只记 inline/anchor + 尺寸 | 分块不需要页面坐标 |
| 字体名 / 颜色 / 下划线 / 斜体 | 未采集 | 旧项目有"去红字"逻辑（xml_student）用颜色；若 Stage 2 需要，采集成本极低（同为 rPr 字段） |
| 表格单元格合并（gridSpan/vMerge） | 按朴素网格读取 | 对"看见内容"无影响；对"理解表头结构"有影响，需要时再加 |
| 域代码（TOC 域 / 公式域 instrText） | 未特殊处理 | 点线目录仍从正文文本可见；域结果文本正常捕获 |
| 超链接目标 | 只取文本 | 讲义分块用不到 |
| 分节 / 分栏（sectPr） | 跳过 | 单栏讲义为主；若遇分栏试卷再议 |

**一个需要明确的事实**：sdt 在本次 229 份语料中出现为 0 次真实内容块（unknown=0），
所以 unknown 保留路径目前只有合成测试覆盖——这是好事，但意味着它对真实数据的防御价值尚未被检验。

---

## 6. 对研究报告假设的修正（以真实证据为准）

1. ~~"速度讲义是普通段落型讲义"~~ → 实为**全文一表型**（body 3 段 + 1 张 6x4 表，594 段在单元格内）。
   研究报告 §3.4② 的骨架结论不变（字号层确实标记了章节），但该结论的信息来源是表格内段落——
   这反而**加强**了"必须穿透表格"的优先级。
2. 研究报告估计"无标题纯流式文档约 20~40%" → 需注意其中一部分其实是**表格封装型**，
   不是无结构，而是结构在单元格里。Stage 2 的可用锚点比原估计更多。
3. `with_num`（真实 Word 编号列表）实测仅 6,450 段 / 229 文档 —— 讲义大量用手打"1．"而非 Word 编号，
   Stage 2 不能把 numPr 当主力信号，只能当确认信号。

---

## 7. 下一阶段建议

按研究报告的实验顺序，本阶段完成了 E3（结构读取）。下一步：

1. **E0 优先：建 60 份分层 golden 语料**（数学 20 / 物化 10 / 英语 10 / 语文政史 10 / 无结构 10）。
   本模块可作为标注工具的底座：dump 输出可直接辅助人工标注块边界。
2. **E2 基线**：用本模块的 `pno` 契约，把现有引擎在 golden 上的输出与标注比对，建立量化基线。
3. **Stage 2 层级推断**时直接可用的原料（本模块已备好）：
   - `StructDoc.size_tiers()`（大于正文的字号分布）
   - 段落级 `eff_sz / bold / outline_lvl / style_name / num`
   - `iter_all_paragraphs()`（穿透表格的统一段落流）
4. 可选的小扩展（都不紧急）：字体颜色/下划线采集、表格合并（gridSpan/vMerge）、编号求值、chart/SmartArt 类型标记。
5. **不要急于做角色分类**。先把"60 份上字号层骨架 vs 人工标注"的一致率测出来，再决定规则怎么写。

---

### 附：如何自己看一份讲义的 dump

```bash
PY="C:/Users/Administrator/Desktop/工作/讲义生成器/讲义生成器flash版/res/python/python.exe"
"$PY" "C:/Users/Administrator/Desktop/工作/jiangyi-generator/app/struct_dump.py" <讲义.docx> -o dump.txt
```

验证脚本（可复跑）：`C:\Users\Administrator\WorkBuddy\2026-09-29-00-12-42\_research\run_struct_dumps.py`

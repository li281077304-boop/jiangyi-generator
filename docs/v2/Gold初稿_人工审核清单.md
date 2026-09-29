# Gold 初稿 · 人工审核清单

> 由 `_research/gen_gold_draft.py` 生成：只用 Stage 1 解析出的**原始特征**
> （字号层/加粗/板块关键词/题型N/答案标记/目录标签/连续题号段）提出候选边界，
> **不做语义理解、不做 Stage 2 识别**。每个单元在 gold 里的 `note` 字段带
> `[置信度]` 与命中依据；下表列出**需要人工确认**的边界（高置信项不列）。

## 0. 全局结论与已知边界

| 项 | 说明 |
|---|---|
| 自审结果 | 4 份初稿全部 PASS，**结构性标注缺口 0**（gold_gap_nodes=0） |
| `unknown` 角色 | **全语料 0 例**（229 份正文解析出的 unknown 块为 0）。该角色由 `tests/test_struct_nodes.py`、`tests/test_gold_compare.py` 的 fixture 覆盖，4 份真实初稿中不出现 |
| `toc` 角色 | 语料中**没有**传统点线目录（点线行经核实多为解析文本里的省略号）。唯一样本见 2 号文件：目录是**嵌在表格单元格里的嵌套表格**，节点 id 形如 `b2.r5c0.n8.r1c0.n3` |
| 表格内结构 | 2 号文件 41 个单元中 40 个位于表格/嵌套表格内部，1 号文件 0 个（纯顶层段落），3 号文件 11 个，4 号文件 0 个 |
| 置信度含义 | high=关键词精确命中；medium=字号层/目录/连续题号段推断；low=兜底或单节点猜测，**必须逐条确认** |
| 结构 dump 文件 | `docs/v2/gold_draft/*.dump.txt` 为**本地生成、不入库**（含第三方讲义原文，且可随时重生成）。生成命令见下方「复核方法」 |

### 结构覆盖矩阵（这些要素在哪份文件里能验到）

| 要素 | 1 普通段落型 | 2 全文一表型 | 3 重复题型型 | 4 阅读材料多题型 |
|---|---|---|---|---|
| 目录 / 正文 | - / ✓ | **✓（表内嵌套表）** / ✓ | - / ✓ | - / ✓ |
| section 层级 | ✓ 17 | ✓ 5 | ✓ 9 | ✓ 3 |
| question group | ✓ 46 | ✓ 31 | ✓ 23 | ✓ 2 |
| shared material 绑定 | ✓ 3（材料→题组绑定） | - | - | ✓ 4（Passage→题组绑定） |
| answer / analysis | -（学生/教师版差异见文件说明） | - | ✓ 20 | ✓ 2 |
| unknown | -（语料 0 例） | - | - | - |

### 复核方法（可直接跑）

```bash
PY="C:/Users/Administrator/Desktop/工作/讲义生成器/讲义生成器flash版/res/python/python.exe"
T="C:/Users/Administrator/Desktop/工作/jiangyi-generator/app/gold_compare.py"
# ① 重新生成本地结构 dump（不入库）：看程序眼里的节点
"$PY" "C:/Users/Administrator/Desktop/工作/jiangyi-generator/app/struct_dump.py" <讲义.docx> -o <key>.dump.txt
# ② 改完 gold 后重跑自审（要求：错误 0、缺口 0）
"$PY" "$T" --doc <解出的docx> --gold docs/v2/gold_draft/<key>.json \
      -o docs/v2/gold_draft/<key>.selfaudit.md
```


---

## 1_普通段落型_应用文写作教师版

- 源文件：`第六部分 应用文写作 解题策略精讲 教师版.docx`
- Gold 初稿：`docs/v2/gold_draft/1_普通段落型_应用文写作教师版.json`
- 结构 dump：本地生成（不入库）`python app/struct_dump.py <讲义.docx> -o 1_普通段落型_应用文写作教师版.dump.txt`
- 自审报告：`docs/v2/gold_draft/1_普通段落型_应用文写作教师版.selfaudit.md`
- 规模：内容节点 1222，gold 初稿单元 66，待确认边界 66
- 角色分布：`{"section": 17, "question_group": 46, "shared_material": 3}`
- 自审：缺口 0 ／ 错误 0 ／ 警告 0 ／ 提示 0

**请重点确认：**
- 「章节」是否真的都是章节（字号层推断可能把标题性正文当成章节）；
- 「题组」边界是否把一组题完整包住（有没有被材料/答案切断）；
- 材料与题组的绑定是否正确（相邻即绑定，跨章节时应解除）；
- 兜底 `body` / low 置信单元是否应该升级为具体角色。

### 需要人工确认的边界

| 单元 | 角色 | 关注点 | 起始文本 | 范围 |
|---|---|---|---|---|
| u001 | section | 置信=medium | 第六部分 应用文写作 解题策略精讲 教师版 | b0 → b0（1 节点） |
| u002 | section | 置信=medium | 【题源解密】 | b1 → b1（1 节点） |
| u003 | section | 置信=medium | 评分标准： | b2 → b20（19 节点） |
| u004 | section | 置信=medium | 评分标准解读： | b21 → b25（5 节点） |
| u005 | question_group | 置信=medium | 1. I can’t find any way to solve the pro | b26 → b31（6 节点） |
| u006 | question_group | 置信=medium | 1. It will be very interesting. (换作同义词：I | b32 → b47（16 节点） |
| u007 | question_group | 置信=medium | 1. Nowadays, we can easily travel from o | b48 → b59（12 节点） |
| u008 | question_group | 置信=medium | 1. We have many things to do. We believe | b60 → b71（12 节点） |
| u009 | section | 置信=medium | 写作的两种美： | b72 → b81（10 节点） |
| u010 | question_group | 置信=medium | 1．要点要齐全 | b82 → b91（10 节点） |
| u011 | section | 置信=medium | 书面表达应试要领： | b92 → b92（1 节点） |
| u012 | question_group | 置信=medium | 1. 第一步是仔细审题。重点注意内容要点，写作对象和交际目的。 | b93 → b110（18 节点） |
| u013 | section | 置信=medium | 书面表达提高措施： | b111 → b112（2 节点） |
| u014 | question_group | 置信=medium；跨度大(106节点) | 1. 经常写随笔，每日三五句。出点错误也没什么。 | b113 → b218（106 节点） |
| u015 | question_group | 置信=medium | 5. 活动安排 | b219 → b255（37 节点） |
| u016 | section | 置信=medium | 【命题分析】 | b256 → b256（1 节点） |
| u017 | section | 置信=medium | 2021年高考英语全国乙卷书面表达分析 | b257 → b258（2 节点） |
| u018 | question_group | 置信=medium | 1. 分析优势与不足； | b259 → b266（8 节点） |
| u019 | shared_material | 置信=medium | 参考范文 | b267 → b271（5 节点） |
| u020 | shared_material | 置信=medium | 参考范文共分为三段，第一段主要从大背景简单介绍网上学习的现状，第二代分别阐述网上 | b272 → b272（1 节点） |
| u021 | shared_material | 置信=medium | 参考范文重点词句：a hot spot, learning efficiency | b273 → b281（9 节点） |
| u022 | section | 置信=medium | 【题材特点】 | b282 → b289（8 节点） |
| u023 | section | 置信=medium | 【题型归纳】 | b290 → b336（47 节点） |
| u024 | section | 置信=medium | 【解题技巧】 | b337 → b337（1 节点） |
| u025 | section | 置信=medium | 写作注意事项： | b338 → b344（7 节点） |
| u026 | section | 置信=medium | 【典例剖析】 | b345 → b347（3 节点） |
| u027 | question_group | 置信=medium | 1. I'm now writing on behalf of the clas | b348 → b368（21 节点） |
| u028 | question_group | 置信=medium | 1. I am writing to ask for more informat | b369 → b388（20 节点） |
| u029 | question_group | 置信=medium | 1. I would be very grateful if you could | b389 → b408（20 节点） |
| u030 | question_group | 置信=medium | 1. I sincerely hope that my application  | b409 → b429（21 节点） |
| u031 | question_group | 置信=medium | 1. Almost perfect as it is, it should ma | b430 → b438（9 节点） |
| u032 | question_group | 置信=medium | 1. 说明你是该报的忠实读者； | b439 → b453（15 节点） |
| u033 | question_group | 置信=medium | 1. I'm writing this letter to express my | b454 → b464（11 节点） |
| u034 | question_group | 置信=medium | 1. 自我介绍； | b465 → b477（13 节点） |
| u035 | question_group | 置信=medium | 1. Taking into account all three factors | b478 → b499（22 节点） |
| u036 | question_group | 置信=medium | 1. I feel terribly sorry for missing the | b500 → b519（20 节点） |
| u037 | question_group | 置信=medium | 1. When we arrived at the farm, there ar | b520 → b539（20 节点） |
| u038 | question_group | 置信=medium | 1. He works very hard every day but he w | b540 → b555（16 节点） |
| u039 | question_group | 置信=medium | 1. 表示欢迎； | b556 → b570（15 节点） |
| u040 | question_group | 置信=medium | 1. Today I am very glad to have the chan | b571 → b580（10 节点） |
| u041 | question_group | 置信=medium | 1. 个人的优势介绍（如性格、特长等）； | b581 → b593（13 节点） |
| u042 | question_group | 置信=medium | 1. The street is to the south of Tian'an | b594 → b604（11 节点） |
| u043 | question_group | 置信=medium | 1. 简况：长 800 余米、 600 多年历史、 300 余家商铺； | b605 → b618（14 节点） |
| u044 | question_group | 置信=medium | 1. The following are our preliminary arr | b619 → b641（23 节点） |
| u045 | question_group | 置信=medium | 1. The whole journey covered five miles  | b642 → b666（25 节点） |
| u046 | question_group | 置信=medium | 1. Our school is looking for a native sp | b667 → b679（13 节点） |
| u047 | question_group | 置信=medium | 1. 教授课程：英语口语、英语写作、今日美国、今日英国等； | b680 → b692（13 节点） |
| u048 | question_group | 置信=medium | 1. Please bring your pens and notebooks  | b693 → b699（7 节点） |
| u049 | question_group | 置信=medium | 1. 短片内容：学校的发展； | b700 → b709（10 节点） |
| u050 | question_group | 置信=medium | 1. Since you were out, I have to leave t | b710 → b718（9 节点） |
| u051 | question_group | 置信=medium | 1. 外出购物 | b719 → b729（11 节点） |
| u052 | section | 置信=medium | 造句方面：句式要准确而多变，活用复合句 | b730 → b730（1 节点） |
| u053 | question_group | 置信=medium | 1、巧用非谓语动词 | b731 → b799（69 节点） |
| u054 | section | 置信=medium | 谋篇方面：结构要流畅且高级 | b800 → b869（70 节点） |
| u055 | section | 置信=medium | 【名师点拨】 | b870 → b871（2 节点） |
| u056 | question_group | 置信=medium | 1.Practice makes perfect. 熟能生巧。 | b872 → b917（46 节点） |
| u057 | question_group | 置信=medium | 2．表示好处 | b918 → b925（8 节点） |
| u058 | question_group | 置信=medium | 3．表示坏处 | b926 → b951（26 节点） |
| u059 | question_group | 置信=medium | 7．表示事实、现状 | b952 → b959（8 节点） |
| u060 | question_group | 置信=medium | 8．表示比较 | b960 → b988（29 节点） |
| u061 | question_group | 置信=medium | 12．套语 | b989 → b1033（45 节点） |
| u062 | question_group | 置信=medium | 1． 对立观点式 | b1034 → b1047（14 节点） |
| u063 | question_group | 置信=medium | 3． 社会问题（现象）式 | b1048 → b1062（15 节点） |
| u064 | question_group | 置信=medium | 1.In recent years, …is becoming increasi | b1063 → b1076（14 节点） |
| u065 | question_group | 置信=medium | 2.分析原因功能句（由原因数量决定） | b1077 → b1115（39 节点） |
| u066 | question_group | 置信=medium；跨度大(106节点) | 1.From what has been discussed above, we | b1116 → b1221（106 节点） |

---

## 2_全文一表型_速度讲义学生版

- 源文件：`2025-2026学年_高一_数学_第1 速度的测量_复习讲义_学生版.docx`
- Gold 初稿：`docs/v2/gold_draft/2_全文一表型_速度讲义学生版.json`
- 结构 dump：本地生成（不入库）`python app/struct_dump.py <讲义.docx> -o 2_全文一表型_速度讲义学生版.dump.txt`
- 自审报告：`docs/v2/gold_draft/2_全文一表型_速度讲义学生版.selfaudit.md`
- 规模：内容节点 759，gold 初稿单元 41，待确认边界 29
- 角色分布：`{"section": 5, "knowledge": 3, "toc": 1, "body": 1, "question_group": 31}`
- 自审：缺口 0 ／ 错误 0 ／ 警告 0 ／ 提示 0

**请重点确认：**
- 「章节」是否真的都是章节（字号层推断可能把标题性正文当成章节）；
- 「题组」边界是否把一组题完整包住（有没有被材料/答案切断）；
- 材料与题组的绑定是否正确（相邻即绑定，跨章节时应解除）；
- 兜底 `body` / low 置信单元是否应该升级为具体角色。

### 需要人工确认的边界

| 单元 | 角色 | 关注点 | 起始文本 | 范围 |
|---|---|---|---|---|
| u001 | section | 置信=medium；跨容器(body→b2.r4c0) | 学 科 教 师 辅 导 讲 义 | b0 → b2.r4c0.n0（16 节点） |
| u002 | section | 置信=medium | 一、课堂启动 | b2.r5c0.n0 → b2.r5c0.n2（3 节点） |
| u003 | section | 置信=medium | 二、知识回顾 | b2.r5c0.n3 → b2.r5c0.n5（3 节点） |
| u005 | toc | 置信=medium；跨容器(b2.r5c0.n8.r0c0→b2.r5c0.n8.r1c1)；请确认是否为真目录区 | 目录 | b2.r5c0.n8.r0c0.n0 → b2.r5c0.n8.r1c1.n7（17 节点） |
| u006 | body | 置信=low |  | b2.r5c0.n9 → b2.r5c0.n9（1 节点） |
| u007 | knowledge | 跨容器(b2.r5c0.n10.r0c0→b2.r5c0.n10.r0c1) | 目标导航 | b2.r5c0.n10.r0c0.n0 → b2.r5c0.n10.r0c1.n0（2 节点） |
| u008 | question_group | 置信=medium；跨容器(b2.r5c0.n10.r1c0→b2.r5c0.n10.r1c1) | 1.掌握测平均速度实验原理，认识全部实验器材及各自作用。 | b2.r5c0.n10.r1c0.n0 → b2.r5c0.n10.r1c1.n4（10 节点） |
| u012 | question_group | 置信=medium | 1．要正确的解答有关“行程问题”的应用题：必须弄清物体运动的具体情况。如运动的方 | b2.r5c0.n26 → b2.r5c0.n41（16 节点） |
| u014 | question_group | 置信=medium | 1、实验器材：小车、斜坡（长木板）、小木块、金属片挡板、刻度尺、停表（秒表）。 | b2.r5c0.n43 → b2.r5c0.n54（12 节点） |
| u015 | question_group | 置信=medium | 2．测量平均速度实验的斜面选择 | b2.r5c0.n55 → b2.r5c0.n64（10 节点） |
| u016 | question_group | 置信=medium | 1．下列关于长度、时间和速度的测量，说法正确的是（　　） | b2.r5c0.n65 → b2.r5c0.n92（28 节点） |
| u017 | question_group | 置信=medium | 2.金属片的作用 | b2.r5c0.n93 → b2.r5c0.n103（11 节点） |
| u018 | question_group | 置信=medium | 4.数据分析与结论 | b2.r5c0.n104 → b2.r5c0.n115（12 节点） |
| u020 | question_group | 置信=medium | 1．一列火车从头至尾完全通过一条长8300m的隧道时，所用的时间是2.92min | b2.r5c0.n117 → b2.r5c0.n127（11 节点） |
| u022 | question_group | 置信=medium | 4．小明在周末打车去某地游玩。如表所示是小明乘坐的出租车票的部分数据。下列说法中 | b2.r5c0.n129 → b2.r5c0.n144（24 节点） |
| u024 | question_group | 置信=medium | 7．如图所示，老鹰紧贴地面以30m/s的速度匀速追赶正前方120m处的一只兔子， | b2.r5c0.n146 → b2.r5c0.n163（18 节点） |
| u026 | question_group | 置信=medium | 10．如图是重庆东站部分列车时刻表，请根据表格判断下列说法正确的是（　　） | b2.r5c0.n165 → b2.r5c0.n178（60 节点） |
| u027 | question_group | 置信=medium | 12．家住市区的小华一家计划在“五一+春假”期间坐动车去上海旅游。经某AI助手软 | b2.r5c0.n179 → b2.r5c0.n184（54 节点） |
| u029 | question_group | 置信=medium | 13．小明一家开车去西安旅游，在途中他看到如图甲所示的交通指示牌，下列说法正确的 | b2.r5c0.n186 → b2.r5c0.n202（32 节点） |
| u031 | question_group | 置信=medium | 16．某同学看到学校中的一个水管在滴水，马上前去拧紧。在此过程中他突然想到水滴下 | b2.r5c0.n204 → b2.r5c0.n222（19 节点） |
| u033 | question_group | 置信=medium；跨容器(b2.r5c0→b2.r5c0.n276.r2c0) | 19．如图在测量小车运动的平均速度的实验中，说法正确的是（     ） | b2.r5c0.n224 → b2.r5c0.n276.r2c0.n0（65 节点） |
| u034 | question_group | 置信=medium；跨容器(b2.r5c0.n276.r2c1→b2.r5c0) | 2.0 | b2.r5c0.n276.r2c1.n0 → b2.r5c0.n331（77 节点） |
| u035 | question_group | 置信=medium | 10．G7次复兴号智能动车由北京开往上海，自北京南到上海虹桥的铁路长度为1318 | b2.r5c0.n332 → b2.r5c0.n334（23 节点） |
| u036 | section | 置信=medium | 五、归纳总结 | b2.r5c0.n335 → b2.r5c0.n337（3 节点） |
| u037 | section | 置信=medium | 六、巩固练习 | b2.r5c0.n338 → b2.r5c0.n343（26 节点） |
| u038 | question_group | 置信=medium | 11．小明一家去蒙山游玩，在路上看到如图甲所示的交通标志牌，此时车内速度表显示的 | b2.r5c0.n344 → b2.r5c0.n379（65 节点） |
| u039 | question_group | 置信=medium | 17．小慧同学利用如图所示的装置测量出小车从斜面上滑下时的平均速度。 | b2.r5c0.n380 → b2.r5c0.n400（21 节点） |
| u040 | question_group | 置信=medium | 18．如图1所示是“测量小车的平均速度”的实验装置。实验时让小车从斜面的A点由静 | b2.r5c0.n401 → b2.r5c0.n461（61 节点） |
| u041 | question_group | 置信=medium；跨容器(b2.r5c0→body) | 26．中国高铁已建成全球规模最大、技术最先进、运营场景最丰富的高铁网络，是中国自 | b2.r5c0.n462 → b3（34 节点） |

---

## 3_重复题型型_计数原理解析版

- 源文件：`专题02 计数原理与二项式定理（题型清单）（解析版）.docx`
- Gold 初稿：`docs/v2/gold_draft/3_重复题型型_计数原理解析版.json`
- 结构 dump：本地生成（不入库）`python app/struct_dump.py <讲义.docx> -o 3_重复题型型_计数原理解析版.dump.txt`
- 自审报告：`docs/v2/gold_draft/3_重复题型型_计数原理解析版.selfaudit.md`
- 规模：内容节点 1038，gold 初稿单元 52，待确认边界 23
- 角色分布：`{"question_group": 23, "answer": 20, "section": 9}`
- 自审：缺口 0 ／ 错误 0 ／ 警告 0 ／ 提示 2

**请重点确认：**
- 「章节」是否真的都是章节（字号层推断可能把标题性正文当成章节）；
- 「题组」边界是否把一组题完整包住（有没有被材料/答案切断）；
- 材料与题组的绑定是否正确（相邻即绑定，跨章节时应解除）；
- 兜底 `body` / low 置信单元是否应该升级为具体角色。

### 需要人工确认的边界

| 单元 | 角色 | 关注点 | 起始文本 | 范围 |
|---|---|---|---|---|
| u004 | question_group | 置信=medium | 2．（2025·四川·模拟预测）在如下的数阵中选出3个数，要求这3个数既不在同一 | b13 → b15（11 节点） |
| u006 | question_group | 跨容器(body→b55.r0c0) | 题型2  两个计数原理的综合应用 | b54 → b55.r0c0.n0（2 节点） |
| u007 | section | 置信=medium；跨容器(b55.r0c0→body) | 利用两个基本计数原理解决问题的步骤 | b55.r0c0.n1 → b57（6 节点） |
| u011 | question_group | 跨容器(body→b177.r0c0) | 题型4  相邻、相间问题 | b176 → b177.r0c0.n1（3 节点） |
| u012 | section | 置信=medium；跨容器(b177.r0c0→body) | 相邻、相间问题的解题策略： | b177.r0c0.n2 → b178（5 节点） |
| u017 | answer | 跨度大(91节点) | 【答案】D | b263 → b353（91 节点） |
| u018 | question_group | 跨容器(body→b355.r0c0) | 题型7  隔板法 | b354 → b355.r0c0.n0（2 节点） |
| u019 | section | 置信=medium | 对于相同元素的分配问题，可以利用分类加法计数原理分类讨论，还可以利用“隔板法”． | b355.r0c0.n1 → b355.r0c0.n1（1 节点） |
| u020 | section | 置信=medium；跨容器(b355.r0c0→body) | 把n个相同的小球放到m(m＜n)个不同盒子中，不同放法的种数的求解方法是： | b355.r0c0.n2 → b357（7 节点） |
| u027 | answer | 跨度大(81节点) | 【答案】A | b511 → b591（81 节点） |
| u030 | question_group | 置信=medium | 65．（2025·湖南益阳·模拟预测）若，则（    ） | b636 → b640（5 节点） |
| u036 | question_group | 跨容器(body→b784.r0c0) | 题型14  二项式定理的应用 | b783 → b784.r0c0.n2（4 节点） |
| u037 | section | 置信=medium | 3．二项式定理的逆用． | b784.r0c0.n3 → b784.r0c0.n3（1 节点） |
| u038 | question_group | 置信=medium；跨容器(b784.r0c0→body) | 3．二项式定理的逆用． | b784.r0c0.n3 → b786（6 节点） |
| u040 | question_group | 跨容器(body→b855.r0c0) | 题型15  杨辉三角 | b854 → b855.r0c0.n0（2 节点） |
| u041 | section | 置信=medium | 杨辉三角的性质： | b855.r0c0.n1 → b855.r0c0.n1（1 节点） |
| u042 | section | 置信=medium | 1．每一行都是对称的，且两端的数都是1. | b855.r0c0.n2 → b855.r0c0.n2（1 节点） |
| u043 | section | 置信=medium | 2．从第三行起，不在两端的任意一个数，都等于上一行中与这个数相邻的两数之和． | b855.r0c0.n3 → b855.r0c0.n3（1 节点） |
| u044 | section | 置信=medium | 3．当k<时，二项式系数是逐渐变大的；当k>时，二项式系数是逐渐变小的． | b855.r0c0.n4 → b855.r0c0.n4（1 节点） |
| u045 | question_group | 置信=medium；跨容器(b855.r0c0→body) | 3．当k<时，二项式系数是逐渐变大的；当k>时，二项式系数是逐渐变小的． | b855.r0c0.n4 → b862（12 节点） |
| u047 | question_group | 置信=medium | 88．（2025·甘肃·模拟预测）“杨辉三角”是中国古代数学文化的瑰宝之一，它揭 | b904 → b909（6 节点） |
| u049 | question_group | 置信=medium | 89．（2025高二·安徽阜阳·期末）杨辉是我国南宋末年的一位杰出的数学家，他在 | b920 → b926（7 节点） |
| u051 | question_group | 置信=medium | 90．（2025·辽宁·模拟预测）杨辉是我国古代数学史上一位著述丰富的数学家，著 | b935 → b942（8 节点） |

---

## 4_阅读材料多题型_话题七解析版

- 源文件：`话题七  文学与艺术类  (真题专项精练) -备战2022高考英语之十年真题专项精讲精练（解析版）.docx`
- Gold 初稿：`docs/v2/gold_draft/4_阅读材料多题型_话题七解析版.json`
- 结构 dump：本地生成（不入库）`python app/struct_dump.py <讲义.docx> -o 4_阅读材料多题型_话题七解析版.dump.txt`
- 自审报告：`docs/v2/gold_draft/4_阅读材料多题型_话题七解析版.selfaudit.md`
- 规模：内容节点 75，gold 初稿单元 11，待确认边界 9
- 角色分布：`{"section": 3, "shared_material": 4, "question_group": 2, "answer": 2}`
- 自审：缺口 0 ／ 错误 0 ／ 警告 0 ／ 提示 0

**请重点确认：**
- 「章节」是否真的都是章节（字号层推断可能把标题性正文当成章节）；
- 「题组」边界是否把一组题完整包住（有没有被材料/答案切断）；
- 材料与题组的绑定是否正确（相邻即绑定，跨章节时应解除）；
- 兜底 `body` / low 置信单元是否应该升级为具体角色。

### 需要人工确认的边界

| 单元 | 角色 | 关注点 | 起始文本 | 范围 |
|---|---|---|---|---|
| u001 | section | 置信=medium | 话题7  文学与艺术类 | b0 → b0（1 节点） |
| u002 | section | 置信=medium | 体裁：说明文 题材：书籍介绍 词数：298 难度：中 建议用时：4分钟 | b1 → b1（1 节点） |
| u003 | shared_material | 置信=medium | Passage1（2020•新高考Ⅰ） | b2 → b7（6 节点） |
| u004 | question_group | 置信=medium | 1.  What made Mr Bissell return to Uzbek | b8 → b20（13 节点） |
| u005 | shared_material | 置信=medium | Passage1 | b21 → b21（1 节点） |
| u007 | section | 置信=medium | 体裁：说明文 题材：文学艺术  词数：230难度：易 建议用时： 5分钟 | b37 → b37（1 节点） |
| u008 | shared_material | 置信=medium | Passage2（2015•新课标Ⅰ） | b38 → b43（6 节点） |
| u009 | question_group | 置信=medium | 1．Which of the following best describe D | b44 → b57（14 节点） |
| u010 | shared_material | 置信=medium | Passage2 | b58 → b58（1 节点） |

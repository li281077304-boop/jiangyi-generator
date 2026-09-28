#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_engine.py  ——  独立的讲义智能拆分引擎

四层降级方案（不依赖任何外部文件）：
  T0a) LLM 语义拆分 → API 驱动（llm_split.py）
  T0b) 混合拆分     → 规则+NLP（hybrid_split.py）
  T1)  TOC 目录解析 → 导航结构（toc_split.py）
  T2)  启发式规则   → 5 层兜底策略

入口：auto_split(paras, template_type)
"""
import os, re, sys, time, subprocess
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# ============================================================
TYPE_RE = re.compile(r'^(?:【)?题型\s*(\d+)')  # 同时匹配"题型1"和"【题型1"格式

# —— topic 提取：从文件名剥离修饰词，只留核心主题 ——
# 后缀修饰词库（题型词 / 版本词 / 学段词），提取时全部去掉
_TOPIC_NOISE = [
    # 题型 / 用途词
    "专题讲义", "讲义", "专题", "训练题", "练习题", "测试题", "试题",
    "试卷", "习题", "练习", "训练", "测试", "导学案", "学案", "教案",
    "复习讲义", "同步练习", "专题训练", "单元测试", "单元复习",
    "期中复习", "期末复习", "一轮复习", "二轮复习", "总复习", "综合复习",
    "期中", "期末", "复习", "综合训练", "专题复习", "模块复习",
    # 版本词
    "解析版", "答案版", "教师版", "学生版", "空白版", "原卷版",
    "解析", "答案", "教师用", "学生用", "教师", "学生", "空白", "原卷",
    # 教材版本
    "人教版", "人教A版", "人教B版", "人教2024版", "人教新目标",
    "北师大版", "苏教版", "沪教版", "鲁教版", "湘教版", "粤教版",
    "华师大版", "浙教版", "冀教版", "青岛版", "北京版", "教科版",
    "外研版", "译林版", "牛津版", "仁爱版", "科普版",
    # 学段/学科修饰（出现就剥，但作为整词剥，不破坏含这些字的真正主题）
    "高一", "高二", "高三", "初中", "高中", "小学", "七年级", "八年级",
    "九年级", "必修", "选修", "选择性必修", "上册", "下册", "全册",
    "学年", "学期", "上学期", "下学期",
    "数学", "语文", "英语", "物理", "化学", "生物", "政治", "历史", "地理",
]
# 括号内容、行首编号、年份等
_TOPIC_NOISE_RE = re.compile(
    r'[【\[][^】\]]*[】\]]'                        # 【】括号内容
    r'|[（(][^）)]*[）)]'                          # （）括号内容
    r'|^\s*\d{1,3}\s*[.．、)）]'                  # 行首题号
    r'|^\s*第\s*\d+\s+'                           # 裸"第1 "编号（无章节词）
    r'|^\s*第[一二三四五六七八九十百零\d]+[章节讲]'  # 第X章/节/讲
    r'|\d{4}\s*[-－—~]\s*\d{4}'                  # 2024-2025 学年
    r'|\d{4}\s*学年'
)
    # 残余的版本关键词（topic_from_name 旧逻辑兼容）
_TOPIC_VERSION_KW = ["教师", "解析", "答案", "教师版", "解析版", "学生", "学生版", "空白"]
# 片段内要正则剥除的结构：第N章/节/讲/课时/单元/模块
_TOPIC_PART_RE = re.compile(
    r'第[一二三四五六七八九十百零\d]+[章节讲段课单元模块部分]'
    r'|第\s*\d+\s+'
    r'|第\s*\d+\s*[章节讲段课单元模块部分]'
    r'|\b\d+\s*[章节讲段课单元模块部分]'
)


def extract_topic(filename, fallback=""):
    """
    从文件名提取核心授课主题。
    思路：去扩展名 → 剥正则噪音(括号/编号/年份) → 剥题型/版本/学段修饰词
          → 按空格/标点切分，丢弃纯噪音片段，拼回剩下的核心词。
    例：'导数的计算 专题讲义 解析版'        → '导数的计算'
        '三角函数 图象与性质 训练题 学生版'  → '三角函数 图象与性质'
        '集合与函数概念（教师版）'           → '集合与函数概念'
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    # 1) 正则噪音整体清掉
    base = _TOPIC_NOISE_RE.sub(" ", base)
    # 2) 按常见分隔符切词
    parts = re.split(r'[\s·\-－—_/,，、;；:：]+', base)
    # 3) 逐片段剥修饰词：先整体匹配噪音词，再剥片段内的修饰词
    kept = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 整个片段就是噪音词 → 丢
        if p in _TOPIC_NOISE:
            continue
        # 片段含噪音词 → 剥掉（如 "数学专题" → "数学"，但避免误伤）
        cleaned = p
        for kw in sorted(_TOPIC_NOISE, key=len, reverse=True):  # 长词先剥
            cleaned = cleaned.replace(kw, "")
        # 剥 "第N章/节/讲" 这类片段内结构
        cleaned = _TOPIC_PART_RE.sub("", cleaned)
        cleaned = cleaned.strip("（）()【】[] -_·").strip()
        if cleaned and cleaned not in _TOPIC_NOISE:
            kept.append(cleaned)
    topic = " ".join(kept).strip()
    # 剥前导噪音：所有数字编号、考点/专题前缀、年份、纯数字、标点符号
    topic = re.sub(r'^\s*\d+\s*[.．、)）:：]?\s*', '', topic)                    # "1．速度的测量" → "速度的测量"
    topic = re.sub(r'^第\s*\d+(\.\d+)?\s*[章节讲段课单元模块部分]?\s*', '', topic)                                    # "第1 速度的测量" → "速度的测量"
    topic = re.sub(r'^\d{1,3}\s+', '', topic)                                   # "02 计数原理"
    topic = re.sub(r'^(考点|知识点|专题|题型|第[一二三]\s*讲)\s*\d*\s*', '', topic)    # "考点01 速度"
    topic = re.sub(r'[（(]\d{4}\s*[-－—~]\s*\d{4}[）)]', '', topic)             # "（2024-2025）"
    topic = re.sub(r'\d{4}\s*[-－—~]\s*\d{4}', '', topic)                       # "2024-2025" 无括号
    topic = re.sub(r'[（(]\d{4}[）)]', '', topic)                               # "（2024）" 单独年份
    # 干掉任何残余标点符号（只留汉字和空格）
    topic = re.sub(r'[^一-鿿\w\s]', '', topic)
    topic = topic.strip("（）()【】[] -_·，,。.：:！!？?、").strip()
    # 兜底：全剥光了就用 fallback
    if not topic:
        topic = fallback or os.path.splitext(os.path.basename(filename))[0]
    return topic


def current_academic_year():
    """
    返回当前学年字符串，如 '2024-2025学年'。
    以9月为学年分界（中国学年惯例）。
    """
    now = datetime.now()
    if now.month >= 9:
        return f"{now.year}-{now.year + 1}学年"
    return f"{now.year - 1}-{now.year}学年"


def build_filename(subject, grade, handout_type, topic, version, academic_year=None):
    """
    生成完整详细的长文件名（用于输出 .docx 文件）。

    格式：{学年}_{年级}_{学科}_{专题名}_{讲义类型}_{版本}.docx
    例：2024-2025学年_高一_数学_三角函数的概念_复习讲义_教师版.docx

    参数：
        subject       — 学科（数学/语文/…）
        grade         — 年级（高一/七年级/三年级/…）
        handout_type  — 讲义类型（复习讲义/同步练习/专题训练/…）
        topic         — 核心专题名（已去掉噪声的短标题）
        version       — 版别（教师版/学生版）
        academic_year — 学年字符串，None 则自动生成
    """
    if not academic_year:
        academic_year = current_academic_year()
    parts = [academic_year]
    if grade:
        parts.append(grade)
    if subject:
        parts.append(subject)
    if topic:
        parts.append(topic)
    if handout_type:
        parts.append(handout_type)
    parts = [p for p in parts if p]  # 过滤空串
    base = "_".join(parts)
    return f"{base}_{version}.docx"


def detect_type_positions(paras):
    """从 _body_paragraphs 结果里找题型标记，返回 {题型号: 段落序号}"""
    pos = {}
    for idx, txt in paras:
        m = TYPE_RE.match(txt.strip())
        if m:
            pos[int(m.group(1))] = idx
    return pos


# ============================================================
#  段落分类器：判断每个段落"多像题目"vs"多像知识"
#  不靠单一标记，用加权打分，穷举所有常见特征
# ============================================================

# 题目特征（分越高越像题目）
_QUESTION_SIGNALS = [
    # --- 选择题特征（高置信度 3分） ---
    (re.compile(r'[A-D][.．、]\s*\S'), 3),           # "A. 5m/s"
    (re.compile(r'[（(]\s*[）)]\s*$'), 3),            # 段尾有填空括号 "(  )"
    (re.compile(r'__+'), 2),                          # 填空题横线 ___
    (re.compile(r'^[A-D]\s*[.．、]?\s*[①②③④]?'), 3), # 行首纯 "A. " 或 "B、"
    # --- 多选题特征 ---
    (re.compile(r'【多选】'), 2),                      # 61．【多选】...
    # --- 题干特征（1-2分） ---
    (re.compile(r'[（(]\s*\d{4}\s*[.·]\s*'), 2),     # "（2026·云南昆明·二模）" 年份真题标记
    (re.compile(r'[（(]\s*\d{4}\s*年\s*'), 1),        # "（2026年 北京）"
    (re.compile(r'以下(说法|选项|正确|错误|正确的|错误的是)'), 1),
    (re.compile(r'(正确的是|错误的是|正确的是\s*[（(])'), 1),
    (re.compile(r'[（(]\s*填\s*[）)]'), 1),            # "（填""或""）"
    (re.compile(r'(如图所示|如图|下图|如图所示).{0,20}(正确的是|正确)', re.I), 1),
    # --- 题号特征 ---
    # 带考试来源的编号题目（高置信度 3分）
    (re.compile(r'^\s*\d{1,3}\s*[.．]\s*[（(]\s*\d{4}'), 3),  # "1．（2025·...）" 标准学科网格式
    (re.compile(r'^\s*\d{1,3}\s*[.．]\s*[（(]'), 2),            # "1．（24-25...）" 或带括号的题目
    # 普通编号题目弱信号（1分，避免知识点内"1）xxx""2）定义"被误判）
    (re.compile(r'^\s*\d{1,3}\s*[.．、)）]\s*\S'), 1),
]

# 知识点特征（分越高越像知识）
_KNOWLEDGE_SIGNALS = [
    # --- 小标题/概念词（2-3分） ---
    (re.compile(r'^(知识点|考点|知识要点|知识梳理|核心知识|重难点)\s*\d*'), 3),
    (re.compile(r'^[一二三四五六七八九十]+[、.．]\s*\D'), 3),  # "一、xxx" "二、xxx"
    (re.compile(r'\(\d+\)\s*(定义|公式|概念|性质|定理|法则|方法)'), 3),
    # --- 定义/公式特征 ---
    (re.compile(r'(等于|表示|其中|单位是|叫做|称为|即为|定义为)'), 1),
    (re.compile(r'(公式|规律|原理|定律|概念|性质)'), 1),
    (re.compile(r'[=＝]\s*\S+\s*[/÷]'), 2),  # v=s/t 公式
    # --- 方法/技巧 ---
    (re.compile(r'^(口诀|注意|说明|提醒|易错|技巧|方法)'), 2),
    # --- 例题特征（例题归知识区，不触发题目分界） ---
    (re.compile(r'【例\s*\d+】'), 3),           # 【例1】含讲解的例题
    (re.compile(r'^例\s*\d+\s*[.．]\s*'), 3),   # 例1．实际算例/讲解
    (re.compile(r'^例\s*\d+\s*'), 3),           # 例1 （含解题步骤）
    (re.compile(r'^【典例】'), 3),               # 【典例】典型例题讲解
    (re.compile(r'^【典例精讲】'), 3),           # 【典例精讲】= 知识讲解区
    (re.compile(r'^【深化点拨】'), 3),           # 深化点拨 = 知识深入讲解
    (re.compile(r'^【角度\d+】'), 2),            # 【角度1】【角度2】知识点多角度分析
    # --- 题型标题（同类题型归类标记，属于教学结构） ---
    (re.compile(r'^【题型\s*\d+\s*'), 2),          # 【题型4 标题】
    (re.compile(r'^【题型[一二三四五六七八九十]+】'), 2),  # 【题型四】
    # --- 学科网结构化章节标题（"01 本节导航" "02 教材精研"=知识区） ---
    (re.compile(r'^0[123]\s+[^\s]+·[^\s]+'), 2),   # 01/02/03 开头的学科网章节
    # --- 英语/通用知识区标记 ---
    (re.compile(r'^重难\d+'), 3),                    # 重难01 重难02 = 核心突破讲解
    (re.compile(r'^(课标单词|目标短语|常考句型|重点语法|知识清单)'), 3),  # 帮课堂知识区
    # --- 解题教学区（知识范畴，不触发分界） ---
    (re.compile(r'^【解题技巧】'), 2),
    (re.compile(r'^【考法预测】'), 2),
    (re.compile(r'^【答案与解析】'), 2),
    (re.compile(r'^【语篇导读】'), 2),
    (re.compile(r'^【长难句分析】'), 2),
    # --- 答案/解析区域（教学讲解，归知识区） ---
    (re.compile(r'^【答案】'), 1),
    (re.compile(r'^【详解】'), 1),
    (re.compile(r'^【分析】'), 1),
    (re.compile(r'^【解析】'), 1),
    (re.compile(r'^【解答】'), 1),
    # --- 长段落（通常不是题目） ---
    (re.compile(r'.{100,}'), 1),  # 超过100字，不太像题目
]

# ── 通用章节/分区标记库（覆盖中英文讲义、教辅、试卷的 100+ 种分区方式）──
# 每个条目: (compiled_regex, section_type, level)
#   section_type: "knowledge" | "practice" | "toc" | "separator" | "mixed" | "header"
#   level: 1=主章节, 2=子章节, 3=子子章节/练习单元
_SECTION_CLASSIFIER = [
    # ══════════════════════════════════════════════════════════
    # 中文数字序号分区：第一部分～第N部分 / 第X章/节/讲/课时/单元/模块/板块/环节/篇
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^第[一二三四五六七八九十\d]+部分'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+章'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+节'), "mixed", 2),
    (re.compile(r'^第[一二三四五六七八九十\d]+讲'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+课时'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+单元'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+模块'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+板块'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+环节'), "mixed", 2),
    (re.compile(r'^第[一二三四五六七八九十\d]+篇'), "mixed", 1),
    (re.compile(r'^第[一二三四五六七八九十\d]+段'), "mixed", 3),
    # 专题/考点/题型 前缀
    (re.compile(r'^专题\s*\d+'), "mixed", 1),
    (re.compile(r'^考点\s*\d+'), "knowledge", 2),
    (re.compile(r'^题型\s*\d+'), "practice", 2),
    (re.compile(r'^知识点\s*\d+'), "knowledge", 2),
    (re.compile(r'^微专题\s*\d+'), "mixed", 1),
    # 纯中文序号：一、二、三、...（带句号/顿号）
    (re.compile(r'^[一二三四五六七八九十]+[、.．]\s*\D'), "mixed", 1),
    (re.compile(r'^[一二三四五六七八九十]+$'), "mixed", 1),  # 裸序号行
    # 括号序号：(一)(二)(三)...
    (re.compile(r'^[（(][一二三四五六七八九十\d]+[）)]'), "mixed", 2),

    # ══════════════════════════════════════════════════════════
    # ── · 号连接的知识/练习区标题（覆盖考情·/基础·/重难·/拔高·/真题·/进阶·/方法·/素养·/命题·）──
    # 知识型前缀
    (re.compile(r'^(考情|基础|方法|技巧|知识|考点)[·・]'), "knowledge", 1),
    # 练习型前缀
    (re.compile(r'^(拔高|真题|进阶|能力|综合|素养|命题|考向)[·・]'), "practice", 1),
    # 重难· 可能是知识也可能是练习（含真题再现），标 mixed 让后续根据内容判断
    (re.compile(r'^(重难)[·・]'), "mixed", 1),
    # 学科网格式：01 本节导航·... / 02 教材精研·... / 03 方法探究·... / 04 真题闯关·... / 05 课后三阶·...
    (re.compile(r'^0[123]\s+[^\s]+·[^\s]+'), "knowledge", 1),
    (re.compile(r'^0[45]\s+[^\s]+·[^\s]+'), "practice", 1),
    (re.compile(r'^\d{2}\s+[^\s]+·[^\s]+'), "mixed", 1),
    # 纯标题形式（用于 TOC fallback 检测）
    (re.compile(r'^(拔高|基础|能力|进阶|重难|考情|真题)[・·].{1,20}$'), "mixed", 1),
    # 帮课堂系列：重难01、重难02...
    (re.compile(r'^重难\s*\d+'), "knowledge", 2),

    # ══════════════════════════════════════════════════════════
    # 英语分区：Part/Section/Unit/Module/Lesson/Chapter + 数字
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^Part\s+\d+', re.I), "mixed", 1),
    (re.compile(r'^Part\s+[A-F]$', re.I), "mixed", 1),
    (re.compile(r'^Section\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Section\s+[A-F]$', re.I), "mixed", 2),
    (re.compile(r'^Unit\s+\d+', re.I), "mixed", 1),
    (re.compile(r'^Module\s+\d+', re.I), "mixed", 1),
    (re.compile(r'^Lesson\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Chapter\s+\d+', re.I), "mixed", 1),
    (re.compile(r'^Topic\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Theme\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Stage\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Phase\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Level\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Round\s+\d+', re.I), "mixed", 2),
    (re.compile(r'^Step\s+\d+', re.I), "mixed", 3),
    (re.compile(r'^Task\s+\d+', re.I), "mixed", 3),
    (re.compile(r'^Activity\s+\d+', re.I), "mixed", 3),

    # ══════════════════════════════════════════════════════════
    # 练习/题目单元：Passage/Reading/Exercise/Test/Quiz/Practice
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^Passage\s+\d+', re.I), "practice", 3),
    (re.compile(r'^Passage\s+[A-F]$', re.I), "practice", 3),
    (re.compile(r'^Reading\s+\d+', re.I), "practice", 3),
    (re.compile(r'^Reading\s+Comprehension', re.I), "practice", 1),
    (re.compile(r'^Read\s+the\s+following\s+passage', re.I), "practice", 3),
    (re.compile(r'^Exercise\s+\d+', re.I), "practice", 3),
    (re.compile(r'^Practice\s+\d+', re.I), "practice", 3),
    (re.compile(r'^Test\s+\d+', re.I), "practice", 2),
    (re.compile(r'^Quiz\s+\d+', re.I), "practice", 2),
    (re.compile(r'^Cloze\s+\d+', re.I), "practice", 3),
    (re.compile(r'^Grammar\s+Focus', re.I), "knowledge", 2),
    (re.compile(r'^Writing\s+Task', re.I), "practice", 3),

    # ══════════════════════════════════════════════════════════
    # 罗马数字：I. II. III. IV. ...
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^[IVX]+[.．]\s+\D'), "mixed", 1),

    # ══════════════════════════════════════════════════════════
    # 目录/导航条目（通常出现在目录页）
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^目录$'), "toc", 0),
    (re.compile(r'^Contents$', re.I), "toc", 0),
    (re.compile(r'\.{5,}'), "toc", 0),  # 目录点线

    # ══════════════════════════════════════════════════════════
    # 分隔线/装饰线
    # ══════════════════════════════════════════════════════════
    (re.compile(r'^[~/\\\-_=*#]{10,}\s*$'), "separator", 0),
    (re.compile(r'^[◆◇★☆●○◎□■△▲▽▼◉◎⊕⊗]{3,}\s*$'), "separator", 0),
]

# ── 练习区边界标记（触发知识→练习转换）──
# 【典例精讲】【例题】【典型例题】【经典例题】属于带答案的例题示范，归知识区
_BOUNDARY_SIGNALS = [
    # ── 中文【】练习区 ──
    re.compile(r'^【真题】'),
    re.compile(r'^【题目】'),
    re.compile(r'^【对点训练】'),
    re.compile(r'^【当堂检测】'),
    re.compile(r'^【课后作业】'),
    re.compile(r'^【巩固训练】'),
    re.compile(r'^【真题演练】'),
    re.compile(r'^【即学即练】'),
    re.compile(r'^【变式训练】'),
    re.compile(r'^【拓展训练】'),
    re.compile(r'^【真题再现】'),            # 阅读理解真题区（不可拆单元起点）
    re.compile(r'^【强化训练】'),
    re.compile(r'^【综合训练】'),
    re.compile(r'^【模拟演练】'),
    re.compile(r'^【考前冲刺】'),
    re.compile(r'^【限时训练】'),
    re.compile(r'^【达标检测】'),
    re.compile(r'^【学以致用】'),
    # ── 中文序号练习区：第X部分 / 专题X / 考点X（独立成行的短标题，非文档长标题）──
    re.compile(r'^第[一二三四五六七八九十\d]+部分'),   # 第一部分/第二部分...
    re.compile(r'^专题\s*\d+\s*$'),                      # "专题1" 纯短标题（非 "专题10 长标题名"）
    re.compile(r'^专题\s*\d+[：:\s].{1,12}$'),           # "专题1：名词" 带短描述
    re.compile(r'^考点\s*\d+'),                          # 考点1/考点2...
    # ── 命名练习/测试区（· 号连接，仅练习型前缀；基础·可能是知识梳理，不在此列）──
    re.compile(r'^(真题|进阶|拔高|能力|综合|素养|考向|命题)[·・]'),   # 真题·/拔高·/进阶· 等练习区
    re.compile(r'^拔高[・·].{,6}$'),                  # 拔高・分层集训 纯标题
    re.compile(r'^(基础演练|能力进阶|综合提升|拓展延伸)$'),   # 明确的练习区词汇
    # ── 学科网章节（练习区）──
    re.compile(r'^0[45]\s+[^\s]+·[^\s]+'),            # 04 真题闯关 / 05 课后三阶
    # ── 帮课堂系列练习标记 ──
    re.compile(r'^[一二三四五六七八九十]+[、.．]\s*(完成句子|完型填空|阅读理解|短文填空|语法填空|写作|听力)'),
    # ── 英语练习区 ──
    re.compile(r'^Passage\s+\d+', re.I),
    re.compile(r'^Passage\s+[A-F]$', re.I),
    re.compile(r'^Reading\s+Comprehension', re.I),
    re.compile(r'^Read\s+the\s+following\s+passage', re.I),
    re.compile(r'^Exercise\s+\d+', re.I),
    re.compile(r'^Practice\s+\d+', re.I),
    re.compile(r'^Test\s+\d+', re.I),
    re.compile(r'^Quiz\s+\d+', re.I),
    re.compile(r'^Cloze\s+\d+', re.I),
    re.compile(r'^Writing\s+Task', re.I),
    # ── 选择题引导词（独立成段，要求后跟括号）──
    re.compile(r'^(以下(说法|正确|错误)|(下列|如下)说法)\s*[（(]'),
    # ── 常见练习区词汇 ──
    re.compile(r'^(即时训练|巩固练习|课后作业|当堂检测|出门测试|课堂练习|随堂检测)$'),
]


def classify_paragraph(txt):
    """
    对单段文本打分，返回 (question_score, knowledge_score, is_boundary, section_type)。
    question_score 高 → 像题目；knowledge_score 高 → 像知识。
    section_type: "practice"/"knowledge"/"toc"/"separator"/"mixed"/None
    """
    q = 0; k = 0; boundary = False; stype = None
    for pat, weight in _QUESTION_SIGNALS:
        if pat.search(txt):
            q += weight
    for pat, weight in _KNOWLEDGE_SIGNALS:
        if pat.search(txt):
            k += weight
    for pat in _BOUNDARY_SIGNALS:
        if pat.search(txt):
            boundary = True
            break
    stype = classify_section_type(txt)
    return q, k, boundary, stype


def classify_section_type(txt):
    """识别段落的章节类型：practice/knowledge/toc/separator/mixed/None"""
    for pat, stype, _ in _SECTION_CLASSIFIER:
        if pat.search(txt):
            return stype
    return None


def find_boundary(paras):
    """
    找到文档中知识点→题目的分界线。
    策略：
      1) 先找明确边界标记
      2) 没找到则用段落评分找题目信号开始位置
      3) 兜底用题号
    注意：找到边界后回溯包含前面的题号段落，避免拦腰截断题目。
    返回应切分的段落序号，找不到返回 None
    """
    if len(paras) < 3:
        return None

    # 题目编号模式（题号开头，如 "1．" "2、"）
    _QNUM_RE = re.compile(r'^\s*\d{1,3}\s*[.．、)）]')
    # 选择题选项模式
    _CHOICE_RE = re.compile(r'^\s*[A-D]\s*[.．、]')

    def _has_qnum(idx):
        """检查段落 idx 是否为题号开头"""
        for i, txt in paras:
            if i == idx and _QNUM_RE.match(txt.strip()):
                return True
        return False

    def _backtrack_to_qnum(boundary_idx):
        """从边界位置往回找最近的题号段落，避免切断题目"""
        found = None
        for idx, txt in paras:
            if idx >= boundary_idx:
                break
            if _QNUM_RE.match(txt.strip()):
                after = txt.strip()[_QNUM_RE.match(txt.strip()).end():].strip()
                if len(after) >= 6:  # 至少有内容，不是裸编号
                    found = idx
        # 动态回溯上限：max(15, 总段数/5)，长文档允许更远回溯
        backtrack_limit = max(15, len(paras) // 5)
        if found and boundary_idx - found <= backtrack_limit:
            # 检查中间没有知识/章节标题（中文序号、英文Section、知识标记等）
            _KNOWLEDGE_HEADER_RE = re.compile(
                r'^[一二三四五六七八九十]+[、.．]'
                r'|^(重难\d+|【解题技巧】|【考法预测】|'
                r'知识点|考点|知识要点|知识梳理|核心知识|'
                r'Part\s+\d+|Section\s+\d+|Passage\s+\d+|Unit\s+\d+|Lesson\s+\d+)'
            )
            for mid_idx, mid_txt in paras:
                if found < mid_idx < boundary_idx:
                    if _KNOWLEDGE_HEADER_RE.match(mid_txt.strip()):
                        return boundary_idx  # 有知识标题，不回溯
                if mid_idx >= boundary_idx:
                    break
            return found
        return boundary_idx

    # 1) 明确边界标记（跳过目录条目：含5个以上连续点号的为目录行，非正文标题）
    _TOC_DOTS = re.compile(r'\.{5,}')
    for idx, txt in paras:
        t = txt.strip()
        if _TOC_DOTS.search(t):
            continue  # 目录点线行，跳过
        for pat in _BOUNDARY_SIGNALS:
            if pat.search(t):
                return _backtrack_to_qnum(idx)

    # 2) 评分：找题目信号开始压倒知识信号的位置
    scores = []
    for idx, txt in paras:
        q, k, _, _ = classify_paragraph(txt.strip())
        scores.append((idx, q, k))

    # 找第一个连续3段 q>k 且 q>=2 的位置
    for i in range(len(scores) - 2):
        a, b, c = scores[i], scores[i+1], scores[i+2]
        if (a[1] > a[2] and a[1] >= 2) and (b[1] > b[2] and b[1] >= 1) and (c[1] > c[2] and c[1] >= 1):
            # 如果边界落在选择题选项上(A./B./C./D.)，回溯到前面的题号
            if _CHOICE_RE.search(dict(paras).get(a[0], '')):
                return _backtrack_to_qnum(a[0])
            return _backtrack_to_qnum(a[0])

    # 3) 兜底：按题号信号找（不要求高分，题号本身足够）
    for idx, txt in paras:
        m = NUM_RE.match(txt.strip())
        if m:
            return idx
    return None


# 通用编号题目：1. / 1、/ 1． / 1） 等（用于无"题型"标记的文档）
NUM_RE = re.compile(r'^\s*(\d{1,3})\s*[.．、)）]')


def detect_numbered_positions(paras):
    """找形如 '1.'、'2．' 的题目起点（只认句号/顿号编号，排除子编号 1）(1) 等）"""
    # 匹配主序号：全角句号 ． 顿号 、 或英文句号 .（子编号用括号）
    # 注：`.` 在字符类中表示字面量英文句号，不是元字符
    _MAIN_QNUM = re.compile(r'^\s*(\d{1,3})\s*[．、.]\s*\S')
    hits = []
    last_num = 0
    for idx, txt in paras:
        t = txt.strip()
        m = _MAIN_QNUM.match(t)
        if not m:
            continue
        num = int(m.group(1))
        after = t[m.end():].strip()
        # 排除太短的（<8字只是编号标签，不是题目）
        if len(after) < 8:
            continue
        if num == last_num + 1 or (num == 1 and last_num >= 1) or (num <= 2 and len(hits) == 0):
            hits.append(idx)
            last_num = num
    # 如果没找到句号编号，回退到兼容模式（允许括号编号）
    if len(hits) < 3:
        hits = []
        last_num = 0
        for idx, txt in paras:
            m = NUM_RE.match(txt.strip())
            if not m:
                continue
            num = int(m.group(1))
            if num == last_num + 1 or (num == 1 and last_num >= 1) or num <= 2:
                hits.append(idx)
                last_num = num
    return hits


# 中文结构标题行检测（供自动分块定位安全切分点）
_SECTION_HEADER_RE = re.compile(
    r'^[一二三四五六七八九十]+[、.．]'                        # 一、 二、 三、
    r'|^(题型|考点|知识点|专题|Part|Section|Lesson|Unit)\s*\d*\s*',
    re.I
)

# 知识章节标题（供离线目标生成扫描）
_KNOWLEDGE_SECTION_RE = re.compile(
    r'^(知识点|考点|知识要点|知识梳理|要点|概念|定义|公式|'
    r'定理|性质|法则|方法|规律|技巧|注意|说明|提醒|小结)'
    r'[\s：:、]*\d*'
)
# 学科网结构化章节标题：如 "02 教材精研·内容全解" "04 真题闯关·溯源演练"
_XUEKE_SECTION_RE = re.compile(
    r'^\d{2}\s+[^\s]+·[^\s]+'             # "02 教材精研·内容全解"
    r'|^0\d\s+[^\s]+·[^\s]+'               # "04 真题闯关·溯源演练"
)
# 练习/题目区标题（学科网常见标记）
_XUEKE_PRACTICE_KW = ['真题闯关', '课后三阶', '精准练习', '溯源演练', '即学即练', '当堂检测', '对点训练']
# 有序号知识标题（一、xxx，排除模板型锚点）
_ORDERED_HEADER_RE = re.compile(r'^[一二三四五六七八九十]+[、.． ](.+)$')


def _knowledge_question_split(points, first_para, last_para, total, template_type="1v1"):
    """
    有题型标记/编号题时：知识点放知识精讲，题目放后两板块。

    知识精讲 → 文档开头到第一个题型/编号题之前
    即时训练 → 从第一个题型/编号题开始，占题目区约 70%
    巩固练习 → 题目区后约 30%
    """
    # 模板对应的锚点名
    _KM = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
    _PM = {"1v1": "六、巩固练习", "class": "六、出门测试"}
    knowledge_marker = _KM.get(template_type, "知识精讲")
    practice_marker = _PM.get(template_type, "六、巩固练习")

    first_q = points[0]

    # —— 知识精讲：知识点内容 ——
    if first_q > first_para:
        blocks = [
            {"marker": knowledge_marker, "start": first_para, "end": first_q - 1},
        ]
    else:
        blocks = [
            {"marker": knowledge_marker, "start": 1, "end": 0},
        ]

    # —— 题目区：即时训练 + 巩固练习 ——
    if len(points) >= 2:
        n = len(points)
        cut = max(1, int(round(n * 0.7)))
        train_pts = points[:cut]
        practice_pts = points[cut:]
        if practice_pts:
            train_end = practice_pts[0] - 1
        else:
            train_end = last_para
        blocks.append({"marker": "即时训练", "start": first_q, "end": train_end})
        if practice_pts:
            blocks.append({"marker": practice_marker, "start": practice_pts[0], "end": last_para})
        else:
            blocks.append({"marker": practice_marker, "start": train_end + 1, "end": last_para})
    else:
        q_span = last_para - first_q
        train_cut = first_q + int(q_span * 0.7)
        blocks.append({"marker": "即时训练", "start": first_q, "end": train_cut})
        blocks.append({"marker": practice_marker, "start": train_cut + 1, "end": last_para})

    return blocks


def _split_points_to_blocks(points, total, ratios):
    """给定一组切分点(段落序号，升序)，按比例分成三块"""
    n = len(points)
    cut1 = max(1, int(round(n * ratios[0])))
    cut2 = max(cut1, int(round(n * ratios[1])))
    groups = [
        ("知识精讲",     points[:cut1]),
        ("即时训练",     points[cut1:cut2]),
        ("六、巩固练习", points[cut2:]),
    ]
    blocks, all_pts = [], sorted(points)
    for marker, gp in groups:
        if not gp:
            continue
        start = gp[0]
        last = gp[-1]
        later = [p for p in all_pts if p > last]
        end = (min(later) - 1) if later else total
        blocks.append({"marker": marker, "start": start, "end": end})
    return blocks


def _find_reading_spans(paras, from_idx=1):
    """找出阅读理解不可拆单元：【真题再现】到下一个知识标记之间的段落范围。
    返回 [(start, end), ...]，每个元组是一个不可拆的阅读单元。"""
    READING_START = re.compile(r'^【真题再现】')
    # 阅读单元结束信号：知识区标题、下一个阅读单元、文档结束
    KNOWLEDGE_RESUME = re.compile(
        r'^(重难\d+|【解题技巧】|【考法预测】|【答案与解析】|'
        r'【语篇导读】|【长难句分析】|'
        r'知识点|考点|知识要点|知识梳理|核心知识|'
        r'[一二三四五六七八九十]+[、.．]\s*\D)'
    )
    spans = []
    in_reading = False
    span_start = None
    for idx, txt in paras:
        if idx < from_idx:
            continue
        t = txt.strip()
        if READING_START.match(t):
            if in_reading:
                spans.append((span_start, idx - 1))
            in_reading = True
            span_start = idx
            continue
        if in_reading and KNOWLEDGE_RESUME.match(t):
            spans.append((span_start, idx - 1))
            in_reading = False
    if in_reading:
        spans.append((span_start, paras[-1][0] if paras else 1))
    return spans


def _protect_reading_spans(blocks, paras, from_idx=1):
    """修正 blocks 边界：确保即时训练/巩固练习分界不切断阅读理解单元。
    若切点落在阅读单元内，将其推到该单元末尾。"""
    reading_spans = _find_reading_spans(paras, from_idx)
    if not reading_spans or len(blocks) < 2:
        return blocks
    for i, blk in enumerate(blocks):
        if blk.get("marker") == "即时训练" and i + 1 < len(blocks):
            cut = blk["end"]
            nxt = blocks[i + 1]
            for rs, re_ in reading_spans:
                if rs <= cut < re_:
                    blk["end"] = re_
                    nxt["start"] = re_ + 1
                    break
            break
    return blocks


def auto_split(paras, ratios=(0.5, 0.85), template_type="1v1", enable_llm=True, enable_hybrid=True, api_key=""):
    """
    通用分块（四层降级方案：LLM → 混合 → TOC → 启发式）。

    参数：
        api_key: DeepSeek API key，非空时传给 T0a
    """
    _KM = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
    _PM = {"1v1": "六、巩固练习", "class": "六、出门测试"}
    k_marker = _KM.get(template_type, "知识精讲")
    p_marker = _PM.get(template_type, "六、巩固练习")

    total = len(paras)
    if total == 0:
        return []

    idx_list = [idx for idx, _ in paras]
    first, last = idx_list[0], idx_list[-1] if idx_list else 1

    # —— T0a) LLM 语义拆分（🔝最高优先级：API 驱动，最准确）——
    if enable_llm:
        try:
            from llm_split import llm_split
            llm_blocks = llm_split(paras, template_type, api_key=api_key)
            if llm_blocks is not None:
                print("[auto_split] T0a LLM split succeeded")
                return _protect_reading_spans(llm_blocks, paras, first)
            else:
                print("[auto_split] T0a LLM 拆分失败，降级到 T0b")
        except ImportError:
            print("[auto_split] 未安装 llm_split 模块，跳过 T0a")
        except Exception as e:
            print(f"[auto_split] T0a 异常: {e}，降级到 T0b")

    # —— T0b) 混合拆分（规则 + 轻量 NLP，离线可用）——
    if enable_hybrid:
        try:
            # 强制重载: 每次调用都从磁盘重读 hybrid_split 模块
            import sys as _sys, importlib as _il
            if 'hybrid_split' in _sys.modules:
                del _sys.modules['hybrid_split']
            from hybrid_split import hybrid_split
            hybrid_blocks = hybrid_split(paras, template_type)
            if hybrid_blocks is not None and len(hybrid_blocks) >= 1:
                print("[auto_split] T0b hybrid split succeeded")
                return _protect_reading_spans(hybrid_blocks, paras, first)
            else:
                print("[auto_split] T0b 混合拆分失败，降级到 T1")
        except ImportError:
            print("[auto_split] 未安装 hybrid_split 模块，跳过 T0b")
        except Exception as e:
            print(f"[auto_split] T0b 异常: {e}，降级到 T1")

    # —— T1) TOC 目录解析（权威的文档结构地图）——
    _toc_blocks = _build_toc_blocks(paras, first, last, template_type)
    if _toc_blocks is not None:
        print("[auto_split] T1 TOC split succeeded")
        return _toc_blocks

    # —— 1) 题型标记（学科网专题格式） ——
    pos = detect_type_positions(paras)
    if len(pos) >= 1:
        nums = sorted(pos.keys())
        points = [pos[x] for x in nums]
        blocks = _knowledge_question_split(points, first, last, total, template_type)
        print("[auto_split] T2 type-marker split succeeded")
        return _protect_reading_spans(blocks, paras, first)

    # —— 1.5) 分隔线检测（文档中 `~~~` `///` 等重复符号行，常标记章节分界）——
    _SEP_RE = re.compile(r'^[~/\-_=*#]{10,}\s*$')
    sep_boundary = None
    for idx, txt in paras:
        t = txt.strip().rstrip('/')
        if _SEP_RE.match(t):
            # 分隔线后的段落如果像章节标题，那就是分界
            for jdx, jtxt in paras:
                if jdx == idx + 1:
                    if _SECTION_HEADER_RE.match(jtxt.strip()) or \
                       re.match(r'^(即时训练|巩固练习|归纳总结|课堂启动|知识回顾|出门测试)', jtxt.strip()):
                        sep_boundary = jdx
                    break
                if jdx > idx + 1:
                    break
            if sep_boundary:
                break
    if sep_boundary is not None:
        # ── 分隔线降级：若前面已有明确的练习区/章节标记，分隔线只是装饰 ──
        # 避免"第二部分：非谓语动词"后的 ~~~ 分隔线误抢边界
        for idx, txt in paras:
            if idx >= sep_boundary:
                break
            t = txt.strip()
            # 检查是否已有 _SECTION_CLASSIFIER 中的 practice 型标记
            if classify_section_type(t) == "practice":
                sep_boundary = None
                break
            # 检查是否已有 _BOUNDARY_SIGNALS 中的明确边界信号
            for pat in _BOUNDARY_SIGNALS:
                if pat.search(t):
                    sep_boundary = None
                    break
            if sep_boundary is None:
                break
    if sep_boundary is not None:
        # 英语阅读理解连续性检测：如果边界前后都是英文正文，不切（防拦腰截文章）
        _EN_TEXT_RE = re.compile(r'^[A-Za-z0-9\s,.!?;:\"\'\-()]{30,}')
        prev_idx = sep_boundary - 1
        prev_txt = dict(paras).get(prev_idx, '') if prev_idx > 0 else ''
        next_idx = sep_boundary + 1 
        next_txt = dict(paras).get(next_idx, '') if next_idx < last else ''
        if _EN_TEXT_RE.match(prev_txt.strip()) and _EN_TEXT_RE.match(next_txt.strip()):
            # 前后都是英文正文→可能是同一篇文章，跳过此边界
            sep_boundary = None
    
    if sep_boundary is not None:
        blocks = []
        if sep_boundary > first:
            blocks.append({"marker": k_marker, "start": first, "end": sep_boundary - 1})
        else:
            blocks.append({"marker": k_marker, "start": 1, "end": 0})
        num_pts = detect_numbered_positions(paras)
        boundary_pts = [p for p in num_pts if p >= sep_boundary]
        if len(boundary_pts) >= 2:  # 降低阈值：2 题即可按题切，不盲切段落
            n = len(boundary_pts)
            cut = max(1, int(round(n * 0.7)))
            if cut < n:
                cut2 = boundary_pts[cut] - 1
            else:
                cut2 = last
        else:
            cut2 = sep_boundary + int((last - sep_boundary) * 0.7)
        if cut2 < sep_boundary: cut2 = sep_boundary
        blocks.append({"marker": "即时训练", "start": sep_boundary, "end": cut2})
        if cut2 < last:
            blocks.append({"marker": p_marker, "start": cut2 + 1, "end": last})
        print("[auto_split] T2 separator split succeeded")
        return _protect_reading_spans(blocks, paras, sep_boundary)

    # —— 2) 评分边界检测（通用：不管文档怎么命名） ——
    boundary = find_boundary(paras)
    if boundary is not None:
        # 边界之前 = 知识精讲
        # 边界及之后 = 题目区
        blocks = []
        if boundary > first:
            blocks.append({"marker": k_marker, "start": first, "end": boundary - 1})
        else:
            blocks.append({"marker": k_marker, "start": 1, "end": 0})
        
        # 用题目编号定位安全切点（避免 70% 数学切分拦腰截断题目）
        q_span = last - boundary
        num_pts = detect_numbered_positions(paras)
        boundary_pts = [p for p in num_pts if p >= boundary]
        if len(boundary_pts) >= 2:  # 降低阈值：2 题即可按题切
            # 按题目数 70% 切：切在题目之间，不是段落之间
            n = len(boundary_pts)
            cut = max(1, int(round(n * 0.7)))
            if cut < n:
                cut2 = boundary_pts[cut] - 1  # 即时训练到第 70% 题的前一段
            else:
                cut2 = last
        else:
            cut2 = boundary + int(q_span * 0.7)  # 兜底：段落比例切
        if cut2 < boundary: cut2 = boundary
        blocks.append({"marker": "即时训练", "start": boundary, "end": cut2})
        if cut2 < last:
            blocks.append({"marker": p_marker, "start": cut2 + 1, "end": last})
        print("[auto_split] T2 scoring split succeeded")
        return _protect_reading_spans(blocks, paras, boundary)

    # —— 3) 编号题兜底 ——
    num_pts = detect_numbered_positions(paras)
    if len(num_pts) >= 3:
        blocks = _knowledge_question_split(num_pts, first, last, total, template_type)
        print("[auto_split] T2 numbering split succeeded")
        return _protect_reading_spans(blocks, paras, first)

    # —— 4) 纯段落比例切 ——
    blank = {idx for idx, txt in paras if not txt.strip()}
    headers = {idx for idx, txt in paras if _SECTION_HEADER_RE.match(txt.strip())}
    num_paras = {idx for idx, txt in paras if NUM_RE.match(txt.strip())}

    def _safe_split(target_pos):
        def _closest(cs): return min((abs(c - target_pos), c) for c in cs)[1] if cs else target_pos
        tol1, tol2 = max(3, total // 20), max(5, total // 10)
        if blank:
            b = _closest(blank)
            if abs(b - target_pos) <= tol1: return b
        if headers:
            h = _closest(headers)
            if abs(h - target_pos) <= tol2: return h
        return target_pos

    p1 = _safe_split(first + int((last - first) * ratios[0]))
    p2 = _safe_split(first + int((last - first) * ratios[1]))
    p1 = max(first, min(p1, last)); p2 = max(p1 + 1, min(p2, last))
    blocks = [
        {"marker": k_marker, "start": first,  "end": p1 - 1 if p1 > first else first},
        {"marker": "即时训练", "start": p1,   "end": p2 - 1 if p2 > p1 else p1},
        {"marker": p_marker, "start": p2,     "end": last},
    ]
    print("[auto_split] T2 proportional fallback")
    return _protect_reading_spans(blocks, paras)


def _is_red_hex(hex_color):
    """判断 hex 颜色是否属于红色系（用于答案文字识别）
    格式 RRGGBB，纯红 = FF0000。
    要求红色通道 > 90，且远大于绿/蓝通道，排除黄/紫/白。
    """
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return r >= 100 and g <= 70 and b <= 70
    except (ValueError, IndexError):
        return False


# ============================================================
#  TOC 目录拆分适配层
# ============================================================

_toc_split_loaded = False
def _get_toc_split():
    global _toc_split_loaded
    if not _toc_split_loaded:
        _toc_split_loaded = True
    from toc_split import detect_toc_structure, find_toc_in_body
    return detect_toc_structure, find_toc_in_body

def _build_toc_blocks(paras, first, last, template_type="1v1"):
    """TOC驱动的权威分块。成功返回blocks，失败返回None。"""
    try:
        from toc_split import build_toc_blocks
        blocks = build_toc_blocks(paras, first, last, template_type)
        if blocks:
            return _protect_reading_spans(blocks, paras)
        return None
    except Exception:
        return None

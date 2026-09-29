#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repeatable Stage 2 structural baseline, adapted from the Gold draft rules.

The deterministic pass recognizes question-group boundaries, shared-material
bindings, and answer/analysis regions. It does not classify unknown content or
change the approved Gold annotations.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import Counter

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                   "v1.2-xml-experiment", "res", "app"))
sys.path.insert(0, APP)

from gold_compare import compare, render_report, _norm  # noqa: E402
from struct_doc import read_struct_doc_bytes  # noqa: E402
from struct_nodes import NodeIndex, ROOT  # noqa: E402


BLOCK_ROLES = [
    (re.compile(r"^(知识精讲|例题讲解|知识讲解|知识回顾|课堂启动|知识点|归纳总结|课堂小结|高妙技法|"
                r"方法指导|目标导航|知识导图|考点梳理|技法指导|技法点拨|题型解读|考点解读|"
                r"典例剖析|典例精讲|例题精讲|思维导图|要点梳理)"), "knowledge"),
    (re.compile(r"^(即时训练|基础巩固|基础速刷|能力提升|能力跃升|思维挑战|巩固练习|"
                r"提升专练|真题感知|真题闯关|课堂检测|出门测试|当堂检测|达标检测|"
                r"实战演练|写作训练|强化训练|课后作业|随堂练习|变式训练|考点突破|专项训练)"),
     "section"),
    (re.compile(r"^(答案与点拨|答案详解|试题解析|解析与答案|【答案】)"), "answer"),
]
RE_ANSWER_SECTION = re.compile(
    r"^(?:参考答案|参考解答|答案|答案解析|答案与解析|答案及解析|解析与答案|答案详解|"
    r"答案与点拨|试题解析)(?:\s*[:：]?)$"
)
RE_ANALYSIS_START = re.compile(
    r"^(?:【\s*(?P<bracket>解析|分析|详解|解答说明)\s*】|"
    r"(?P<plain>解析|分析|详解|解答说明)\s*[:：])"
)
RE_ANSWER_GROUP_START = re.compile(
    r"^\s*[一二三四五六七八九十]+[、．.]\s*\d{1,3}\s*[．.、]"
)
RE_SECTION_HEAD = re.compile(
    r"^(?:知识点\s*\d+.*|知识篇\s*\d+.*|第\s*\d+(?:\.\d+)*\s*(?:节|章).*|"
    r"教学内容|知识精讲.*|知识回顾.*|"
    r"课堂启动.*|知识导图.*|深化点拨|速度.{0,30}综合应用.{0,30}|.*解题步骤)$"
)
RE_INLINE_KNOWLEDGE_LABEL = re.compile(
    r"^(?:常见的|常用的|注意|说明|定义|性质|例子|举例|思考|提示).*[：:]$"
)
RE_NUMBERED_ANSWER = re.compile(r"^\s*\d{1,3}\s*[．.、]\s*\S")
RE_COMPACT_ANSWER_KEY = re.compile(
    r"^\s*(?:[一二三四五六七八九十]+[、．.]\s*)?"
    r"(?:\d{1,3}\s*[．.、]\s*[A-J](?:\s*[\d、，,；;．.]*\s*[A-J]){0,12}"
    r"|\d{1,3}(?:\s+[A-J\d]){2,30})\s*$", re.I
)
RE_READING_MATERIAL_HEAD = re.compile(r"^(?:Passage\s*\d+|阅读(?:材料|短文)|材料\s*\d+|语篇\s*\d+|【材料】)", re.I)
RE_SOURCE_CITATION = re.compile(r"^\s*[（(]\s*(?:19|20)\d{2}\s*[·•.．]")
RE_NUMERIC_SECTION = re.compile(r"^\s*\d{1,2}\s*$")
RE_TYPE_HEAD = re.compile(r"^[【\[（(]?(题型|类型|角度|考点|考向|专题)\s*\d+")
RE_TOC_LINE = re.compile(r"(\.{5,}|·{5,}|．{5,})")
RE_TOC_ENTRY = re.compile(r"(\.{3,}|·{3,}|．{3,})\s*\d{1,4}\s*$")
RE_OPTION = re.compile(r"^\s*[A-D][.．、]\s*\S")
RE_QNUM = re.compile(r"^\s*\d{1,3}\s*[．.、]")
RE_TOC_WORD = re.compile(r"^(?:目\s*录|Contents|内容导航|目录导读|目录导航|本讲目录)$", re.I)
RE_EXAMPLE_HEAD = re.compile(r"^[【\[（(]?(例题?|例|变式|练习)\s*\d+(?:[-－.．]\d+)?")
RE_ORDERED_SECTION = re.compile(r"^[一二三四五六七八九十]+[、．.]\s*\S")
RE_ANGLE_SECTION = re.compile(r"^角度\s*\d+")
RE_INSTRUCTION_LEAD = re.compile(
    r"^(?:要|需|必须|掌握|熟练|了解|理解|认识|通过|能|能够|实验器材|实验原理|实验步骤|"
    r"实验操作|注意事项|数据分析|解题步骤|解题策略|方法|技巧|性质|公式|法则|定理|"
    r"首先|其次|最后|本题|句意|故选|答案|解析|规范)"
)
RE_CONCEPTUAL_INSTRUCTION = re.compile(
    r"^(?:应用.{0,12}(?:时|中)|利用.{0,40}(?:概念|定理|公式)|"
    r"作图.{0,60}(?:规范|步骤|实验|数据)|对比.{0,60}(?:归纳|总结)|"
    r".{0,24}(?:解题|实验|数据).{0,16}(?:注意事项|误差|分析|图像|结论))"
)
RE_INLINE_OPTIONS = re.compile(r"(?:^|[\s|])A[.．、]\s*\S", re.I)
RE_EXPLICIT_QUESTION_MARKER = re.compile(
    r"(?:[?？]|_{2,}|＿{2,}|\(\s*\)|（\s*）|（\s*[A-D]\s*[）)]|\([A-D]\))", re.I
)
OBJECTIVE_HEADINGS = ("目标导航", "方法指导", "教学目标", "学习目标", "教学要求", "学习要求")
RE_EXPLANATION_TEXT = re.compile(
    r"^(?:\d{1,3}\s*[．.、]\s*)?(?:句意|故选|因此|所以|符合题意|根据.{0,18}(?:可知|答语)|由此可知)"
)
RE_QUESTION_CUE = re.compile(
    r"(?:[?？]|_{2,}|＿{2,}|\(\s*\)|（\s*）|（\s*[A-D]\s*[）)]|\([A-D]\)|\([.。?？]\)\s*$|"
    r"（[.。?？]）\s*$|下列|以下|若|已知|求|计算|化简|比较|如图|试求|判断|填入|排序|分别求|"
    r"哪一|什么|为何|为什么|怎样|求出|解答|选择|写出)"
)
RE_READING_QUESTION = re.compile(
    r"^\s*\d{1,3}\s*[．.、]\s*(?:what|which|who|why|how|where|when|whose|whom|"
    r"the author|according to|the text|the passage|by the|best title|we know|"
    r"what attitude|which method|what happened|does .{0,50} mean|did .{0,50} feel)", re.I
)
RE_PLAIN_CHOICE_ANSWER = re.compile(r"^\s*\d{1,3}\s*[．.、]\s*[A-H](?:\s*[,，、;；]\s*[A-H]){0,7}\s*$", re.I)
EXERCISE_LABELS = ("即时训练", "基础巩固", "基础速刷", "能力提升", "能力跃升", "思维挑战",
                   "巩固练习", "提升专练", "真题感知", "真题闯关", "课堂检测", "出门测试",
                   "当堂检测", "达标检测", "实战演练", "写作训练", "强化训练", "课后作业",
                   "随堂练习", "变式训练", "考点突破", "专项训练", "选择填空", "核心素养")
MERGE_ROLES = {"knowledge", "body"}
BASELINE_ID = "reading-material-answer-analysis-v1"


def _heading_text(text):
    """Remove common decorative prefixes before matching section labels."""
    return _norm(text).lstrip("⚡🚀🔥⭐★◆●▪·【[（( ")


def _toc_end_before_next_section(index, cands, start_id):
    """Bound a standalone contents/navigation block at the next structure cue."""
    start_order = index.order_of(start_id)
    future = []
    for candidate in cands:
        if candidate["role"] not in ("section", "shared_material", "question_group"):
            continue
        node_id = candidate["node"]
        order = index.order_of(node_id)
        if order is None:
            first = index.first_content(node_id)
            order = index.order_of(first) if first else None
        if order is not None and order > start_order:
            future.append(order)
    if future:
        end_order = min(future)
        if end_order > start_order:
            return index.nodes[end_order - 1].id
    # A title without a later structural cue is still bounded. The cap avoids
    # swallowing the rest of a document when a purported contents page is
    # malformed or its body headings are unrecognized.
    end_order = min(len(index.nodes) - 1, start_order + 12)
    return index.nodes[end_order].id if end_order >= start_order else start_id


def _is_instruction_or_answer_text(text):
    t = _norm(text)
    stripped = re.sub(r"^\s*(?:(?:\d{1,3}|[一二三四五六七八九十]+)\s*[．.、]|"
                       r"[（(]\s*\d{1,3}\s*[）)]\s*)", "", t)
    return bool(RE_CONCEPTUAL_INSTRUCTION.match(stripped)
                or RE_INSTRUCTION_LEAD.match(stripped)
                or RE_EXPLANATION_TEXT.match(stripped))


def _question_start_strength(text, mode, previous_number, has_formula=False):
    """Accept prompt-like starts; use sequence only inside an exercise section."""
    t = _norm(text)
    match = RE_QNUM.match(t)
    if not match or RE_PLAIN_CHOICE_ANSWER.match(t):
        return None
    number = int(match.group().strip().rstrip("．.、 "))
    stripped = re.sub(r"^\s*\d{1,3}\s*[．.、]\s*", "", t)
    if _is_instruction_or_answer_text(t) and not RE_EXPLICIT_QUESTION_MARKER.search(t):
        return None
    if RE_QUESTION_CUE.search(t):
        return number
    if RE_INLINE_OPTIONS.search(t):
        return number
    if _is_instruction_or_answer_text(t):
        return None
    if has_formula and mode == "exercise" and RE_SOURCE_CITATION.match(stripped):
        return number
    if mode == "exercise" and previous_number is not None and number == previous_number + 1:
        return number
    return None


def _objective_table_columns(index):
    """Return table columns whose heading marks objective/guidance content.

    This scopes instructional-number suppression to the structurally related
    table column instead of changing the exercise zone for the rest of a file.
    """
    table_scopes = {}
    for node in index.nodes:
        if _heading_text(node.text) not in OBJECTIVE_HEADINGS:
            continue
        cell_id = node.container
        if index.containers.get(cell_id) != "cell":
            continue
        match = re.search(r"\.r(\d+)c(\d+)$", cell_id)
        table_id = index.container_parent.get(cell_id)
        if not match or index.containers.get(table_id) != "table":
            continue
        row, col = int(match.group(1)), int(match.group(2))
        cols = table_scopes.setdefault(table_id, {})
        cols[col] = min(cols.get(col, row), row)
    # A single matching cell can be a label inside a larger page-layout table.
    # Require a paired objective/guidance header before treating table columns
    # as a local instructional region.
    return {(table_id, col): row for table_id, cols in table_scopes.items()
            if len(cols) >= 2 for col, row in cols.items()}


def _in_objective_table_column(index, node, scopes):
    """Whether a node is below an objective heading in the same table column."""
    cell_id = node.container
    while cell_id and index.containers.get(cell_id) != "cell":
        cell_id = index.container_parent.get(cell_id)
    if not cell_id:
        return False
    match = re.search(r"\.r(\d+)c(\d+)$", cell_id)
    table_id = index.container_parent.get(cell_id)
    if not match:
        return False
    row, col = int(match.group(1)), int(match.group(2))
    heading_row = scopes.get((table_id, col))
    return heading_row is not None and row > heading_row


def _is_bold_numbered_explanation_heading(index, order):
    """Recognize bold numbered knowledge headings followed by sub-explanations."""
    node = index.nodes[order]
    if not node.block or not node.block.bold or not RE_QNUM.match(_norm(node.text)):
        return False
    heading_text = re.sub(r"^\s*\d{1,3}\s*[．.、]\s*", "", _norm(node.text))
    if RE_EXAMPLE_HEAD.match(_heading_text(heading_text)) \
            or re.match(r"^(?:变式|例题?|练习)\s*\d", heading_text):
        return False
    next_node = next((n for n in index.nodes[order + 1:]
                      if n.has_content and n.container == node.container), None)
    return bool(next_node and re.match(
        r"^\s*(?:[（(]\s*\d+\s*[）)]|[①②③④⑤⑥⑦⑧⑨])", _norm(next_node.text)))


def _reading_material_gap_start(index, left_order, right_order):
    """Group consecutive reading items only when substantial prose intervenes.

    This selects question-group boundaries only; it emits no shared_material
    unit and creates no material/question relation.
    """
    middle = [_norm(n.text) for n in index.nodes[left_order + 1:right_order]]
    prose = [t for t in middle if len(t) >= 80 and not RE_QNUM.match(t)
             and not RE_OPTION.match(t) and not RE_PLAIN_CHOICE_ANSWER.match(t)]
    if len(prose) >= 3 and sum(map(len, prose)) >= 600:
        first_text = prose[0]
        for order in range(left_order + 1, right_order):
            if _norm(index.nodes[order].text) == first_text:
                return order
    return None


def detect_question_runs(index, zones, section_orders, material_orders, objective_scopes=None):
    """Identify actual prompt starts instead of one candidate per numbered run.

    Number-only lines are suppressed in knowledge/answer regions and in
    instructional/explanatory prose. Explicit example headings count as prompt
    starts. Consecutive English reading questions stay within one question group
    unless a substantial prose gap marks the next question set.
    """
    out = []
    previous_number = None
    previous_item_order = None
    reading_group = False
    section_order_set = set(section_orders)
    explicit_group_open = False
    objective_scopes = objective_scopes or {}
    for i, node in enumerate(index.nodes):
        if i in section_order_set:
            explicit_group_open = False
        t = _norm(node.text)
        if not t:
            continue
        if _in_objective_table_column(index, node, objective_scopes):
            previous_number = None
            previous_item_order = None
            reading_group = False
            continue
        if _is_bold_numbered_explanation_heading(index, i):
            previous_number = None
            previous_item_order = None
            reading_group = False
            continue
        mode = zones[i]
        if RE_EXAMPLE_HEAD.match(_heading_text(t)):
            out.append({"node": node.id, "role": "question_group", "conf": "high",
                        "evidence": "显式例题/变式题标题"})
            previous_number = None
            previous_item_order = i
            reading_group = False
            explicit_group_open = True
            continue
        block = node.block
        has_formula = bool(block and (block.math_count or block.oles))
        number = _question_start_strength(t, mode, previous_number, has_formula)
        if number is None or mode in ("knowledge", "answer", "analysis"):
            if mode in ("knowledge", "answer", "analysis"):
                previous_number = None
                previous_item_order = None
                reading_group = False
            continue
        if explicit_group_open:
            # A numbered prompt immediately after an explicit example/variant
            # heading is part of that group, not a new independent question.
            previous_number = number
            previous_item_order = i
            continue
        is_reading = bool(RE_READING_QUESTION.match(t))
        crossed_section = previous_item_order is not None and any(
            previous_item_order < p <= i for p in section_orders)
        crossed_material = previous_item_order is not None and any(
            previous_item_order < p <= i for p in material_orders)
        latest_material = max((p for p in material_orders if p <= i), default=None)
        latest_section = max((p for p in section_orders if p <= i), default=None)
        material_context = (latest_material is not None
                            and (latest_section is None or latest_material > latest_section))
        material_gap_start = None
        same_sequence = (reading_group and previous_item_order is not None
                         and not crossed_section and not crossed_material
                         and ((material_context) or
                              (is_reading and number == (previous_number or 0) + 1)))
        if same_sequence:
            material_gap_start = _reading_material_gap_start(index, previous_item_order, i)
        same_reading_group = same_sequence and material_gap_start is None
        if material_gap_start is not None:
            out.append({"node": index.nodes[material_gap_start].id, "role": "shared_material", "conf": "medium",
                        "evidence": "连续阅读题之间出现独立长文材料"})
        if not same_reading_group:
            out.append({"node": node.id, "role": "question_group", "conf": "high",
                        "evidence": "题号 + 题干特征" if RE_QUESTION_CUE.search(t)
                        else "练习区连续题号"})
        previous_number = number
        previous_item_order = i
        reading_group = is_reading or material_context
    return out


def detect(index, doc):
    """Detect section anchors and question starts for the v2 boundary pass."""
    body_sz = doc.body_size or 0
    sizes = sorted({n.block.eff_sz for n in index.nodes
                    if n.block and n.block.eff_sz and n.block.eff_sz > body_sz}, reverse=True)
    cands, toc_nodes = [], []
    zone_markers = {}
    active_zone = "body"
    answer_area_started = False
    material_orders = set()
    for i, n in enumerate(index.nodes):
        t = _norm(n.text)
        if not t:
            continue
        next_nonempty = next((candidate for candidate in index.nodes[i + 1:]
                              if _norm(candidate.text)), None)
        if RE_TOC_LINE.search(t) or RE_TOC_WORD.match(t):
            continue
        title = _heading_text(t)
        hit = None
        zone = None
        if RE_ANSWER_SECTION.match(t):
            hit, zone = ("section", "答案区标题"), "answer"
            answer_area_started = True
        elif RE_SECTION_HEAD.match(title.rstrip("】]）) ")):
            hit, zone = ("section", "显式教学栏目/知识标题"), (
                "body" if title.startswith("教学内容") else "knowledge")
        elif RE_TYPE_HEAD.match(title) or RE_ANGLE_SECTION.match(title):
            hit, zone = ("section", "栏目/题型标题"), "exercise"
        elif (RE_NUMERIC_SECTION.match(t) and next_nonempty is not None
              and RE_SOURCE_CITATION.match(_norm(next_nonempty.text))):
            hit, zone = ("section", "材料前的独立序号"), "body"
        elif (RE_READING_MATERIAL_HEAD.match(t) or RE_READING_MATERIAL_HEAD.match(title)
              or RE_SOURCE_CITATION.match(t)):
            hit = ("shared_material", "阅读材料标题/来源标记")
            material_orders.add(i)
        elif any(title.startswith(label) for label in EXERCISE_LABELS):
            hit, zone = ("section", "训练栏目标题"), "exercise"
        elif RE_INLINE_KNOWLEDGE_LABEL.match(title):
            # This is an inline explanatory label, not a section boundary. Keep
            # the caller's exercise/body state so later questions are retained.
            hit = ("knowledge", "正文内定义/提示标签")
        elif (RE_ORDERED_SECTION.match(t) and len(t) <= 80
              and active_zone not in ("knowledge", "answer")
              and not answer_area_started):
            hit = ("section", "中文序号栏目标题")
            zone = "exercise" if re.search(r"选择|排序|补全|填空|改写|计算|训练|练习|检测|题|阅读理解|写作|判断", t) else "body"
        else:
            for pat, role in BLOCK_ROLES:
                if pat.match(t) or pat.match(title):
                    hit = (role, "策略关键词: %s" % pat.pattern[:28])
                    zone = {"section": "exercise", "knowledge": "knowledge", "answer": "answer"}[role]
                    break
        if hit is None and n.block is not None and n.block.eff_sz and body_sz \
                and n.block.eff_sz > body_sz and len(t) <= 40:
            lvl = sizes.index(n.block.eff_sz) + 1 if n.block.eff_sz in sizes else 2
            hit = ("section", "字号层 %s(正文%s)%s" % (
                "%gpt" % (n.block.eff_sz / 2.0), "%gpt" % (body_sz / 2.0),
                " 加粗" if n.block.bold else ""), lvl)
            zone = "body"
        if hit:
            role, ev = hit[0], hit[1]
            if role == "answer":
                answer_area_started = True
            lvl = hit[2] if len(hit) > 2 else None
            candidate = {"node": n.id, "role": role,
                          "conf": "high" if "关键词" in ev or "题型" in ev or "材料标题" in ev else "medium",
                          "evidence": ev, "level": lvl}
            if role == "section":
                candidate["isolated"] = True
                candidate["zone"] = zone
            cands.append(candidate)
            if zone:
                # A knowledge/tip subheading inside an exercise section is
                # local guidance, not the end of the exercise sequence.
                # Preserve the exercise detection context until another
                # section explicitly changes it.
                if zone == "knowledge" and active_zone == "exercise":
                    zone = None
            if zone:
                zone_markers[i] = zone
                active_zone = zone
    for n in index.nodes:
        t = _norm(n.text)
        if RE_TOC_ENTRY.search(t):
            toc_nodes.append(n.id)
    clusters, cur = [], []
    for nid in toc_nodes:
        if cur and index.order_of(nid) - index.order_of(cur[-1]) <= 2:
            cur.append(nid)
        else:
            if cur:
                clusters.append(cur)
            cur = [nid]
    if cur:
        clusters.append(cur)
    for cl in clusters:
        if len(cl) >= 3:
            cands.append({"node": cl[0], "role": "toc", "conf": "medium",
                          "evidence": "目录行簇 %d 行（点线+页码）" % len(cl), "toc_end": cl[-1]})
    for n in index.nodes:
        if not RE_TOC_WORD.match(re.sub(r"\s+", " ", (n.text or "")).strip()):
            continue
        cid, best = n.container, None
        while cid and cid != ROOT:
            if index.descendants.get(cid) and len(index.descendants[cid]) >= 3:
                best = cid
                break
            cid = index.container_parent.get(cid)
        if best:
            cands.append({"node": best, "role": "toc", "conf": "medium",
                          "evidence": "目录标签所在容器（%s）含 %d 个条目，结构位于表格/嵌套表格内部"
                                      % (index.containers.get(best), len(index.descendants[best])),
                          "toc_container": best, "toc_end": best})
        else:
            cands.append({"node": n.id, "role": "toc", "conf": "low",
                          "evidence": "目录标题至首个正文结构标题之间的导航区",
                          "toc_end": _toc_end_before_next_section(index, cands, n.id)})
    zones = []
    current_zone = "body"
    for i in range(len(index.nodes)):
        if i in zone_markers:
            current_zone = zone_markers[i]
        zones.append(current_zone)
    # Treat answer keys and explanations as a small stateful region. Explicit
    # answer headings enter the region; answer rows and explanation labels then
    # switch roles until the next row/label. This keeps explanation numbering
    # out of question detection without relying on sample IDs or node numbers.
    answer_area = False
    analysis_mode = False
    for i, node in enumerate(index.nodes):
        t = _norm(node.text)
        if not t:
            if answer_area:
                zones[i] = "analysis" if analysis_mode else "answer"
            continue
        existing = [c for c in cands if c["node"] == node.id]
        existing_section = any(c["role"] == "section" for c in existing)
        existing_answer = any(c["role"] == "answer" for c in existing)
        if RE_ANSWER_SECTION.match(t):
            answer_area = True
            analysis_mode = False
            zones[i] = "answer"
            continue
        if not answer_area and existing_answer:
            answer_area = True
            analysis_mode = False
        if not answer_area:
            continue
        if existing_section:
            # Subsection headings inside the key retain their existing role,
            # but start the next answer group after any preceding explanation.
            analysis_mode = False
            zones[i] = "answer"
            continue
        analysis_match = RE_ANALYSIS_START.match(t)
        if analysis_match:
            label = analysis_match.group("bracket") or analysis_match.group("plain")
            # 【详解】 commonly subdivides the explanation already opened by
            # 【分析】; keep that material in one unit. A fresh 解析/分析 marker
            # starts a new explanation block, including when it directly
            # follows a prior block without an answer key between them.
            if not analysis_mode or label != "详解":
                cands.append({"node": node.id, "role": "analysis", "conf": "high",
                              "evidence": "答案区解析/分析标记"})
            analysis_mode = True
            zones[i] = "analysis"
            continue
        if analysis_mode:
            if RE_ANSWER_GROUP_START.match(t) or RE_COMPACT_ANSWER_KEY.match(t):
                cands.append({"node": node.id, "role": "answer", "conf": "medium",
                              "evidence": "解析后的新答案组/紧凑答案键"})
                analysis_mode = False
                zones[i] = "answer"
            else:
                zones[i] = "analysis"
            continue
        if RE_ANSWER_GROUP_START.match(t) or RE_COMPACT_ANSWER_KEY.match(t) \
                or RE_NUMBERED_ANSWER.match(t):
            cands.append({"node": node.id, "role": "answer", "conf": "medium",
                          "evidence": "答案区编号答案行"})
        zones[i] = "answer"
    section_orders = [i for i, c in enumerate(index.nodes)
                      if any(u["node"] == c.id and u["role"] == "section" for u in cands)]
    material_orders.update(i for i, c in enumerate(index.nodes)
                           if any(u["node"] == c.id and u["role"] == "shared_material" for u in cands))
    cands.extend(detect_question_runs(index, zones, section_orders, material_orders,
                                      _objective_table_columns(index)))
    toc_containers = [c["toc_container"] for c in cands if c.get("toc_container")]
    if toc_containers:
        cands = [c for c in cands if not (c["node"] in index.by_id and
                  any(c["node"] in index.descendants[tc] for tc in toc_containers))]
    def candidate_order(c):
        nid = c["node"]
        o = index.order_of(nid)
        if o is None:
            first = index.first_content(nid)
            o = index.order_of(first) if first else 10 ** 9
        return o
    return sorted(cands, key=candidate_order)


def build_units(index, cands):
    def first_of(nid):
        return nid if nid in index.by_id else index.first_content(nid)
    def last_of(nid):
        return nid if nid in index.by_id else index.last_content(nid)
    units = []
    for i, c in enumerate(cands):
        start = first_of(c["node"])
        if start is None:
            continue
        next_candidate = None
        if c.get("isolated"):
            end = start
        elif "toc_end" in c:
            end = last_of(c["toc_end"]) or start
        else:
            next_candidate = next(((c2, first_of(c2["node"])) for c2 in cands[i + 1:]
                                   if first_of(c2["node"]) is not None), None)
            nxt = next_candidate[1] if next_candidate else None
            if nxt is None:
                end = index.nodes[-1].id
            else:
                o = index.order_of(nxt)
                end = index.nodes[o - 1].id if o and o > 0 else start
        if index.order_of(end) < index.order_of(start):
            end = start
        if c["role"] == "question_group" and next_candidate is not None \
                and next_candidate[0]["role"] == "section" \
                and next_candidate[0].get("zone") == "exercise" \
                and index.by_id[start].container == ROOT:
            end_order = index.order_of(end)
            start_order = index.order_of(start)
            while end_order is not None and start_order is not None \
                    and end_order > start_order \
                    and not index.nodes[end_order].has_content \
                    and index.nodes[end_order].container == ROOT:
                end_order -= 1
            end = index.nodes[end_order].id
        units.append({"id": "u%03d" % (i + 1), "role": c["role"], "mode": "spans",
                      "spans": [[start, end]], "_conf": c["conf"],
                      "_evidence": c["evidence"], "level": c.get("level")})
    return units


def merge_adjacent(index, units):
    merged = []
    for u in units:
        if merged:
            prev = merged[-1]
            same_role = prev["role"] == u["role"] and u["role"] in MERGE_ROLES
            contiguous = index.order_of(u["spans"][0][0]) == index.order_of(prev["spans"][0][1]) + 1
            if same_role and contiguous:
                prev["spans"][0][1] = u["spans"][0][1]
                prev["_evidence"] += " + 合并 %s" % u["id"]
                continue
        merged.append(u)
    for i, u in enumerate(merged):
        u["id"] = "u%03d" % (i + 1)
    return merged


def fill_gaps(index, units):
    covered = set()
    for u in units:
        covered |= index.interval(*u["spans"][0])
    missing = [n.id for n in index.nodes if n.id not in covered and n.has_content]
    if not missing:
        return units
    gaps, cur = [], [missing[0]]
    for a, b in zip(missing, missing[1:]):
        if index.order_of(b) == index.order_of(a) + 1:
            cur.append(b)
        else:
            gaps.append(cur)
            cur = [b]
    gaps.append(cur)
    extra = [{"id": "gap%03d" % (i + 1), "role": "body", "mode": "spans",
              "spans": [[g[0], g[-1]]], "_conf": "low",
              "_evidence": "兜底：未被任何规则命中（%d 个节点）" % len(g)}
             for i, g in enumerate(gaps)]
    merged = sorted(units + extra, key=lambda u: index.order_of(u["spans"][0][0]))
    for i, u in enumerate(merged):
        u["id"] = "u%03d" % (i + 1)
    return merged


def assign_relations(units):
    last_section = last_material = None
    for u in units:
        role = u["role"]
        if role == "section":
            last_section = u["id"]
            u["level"] = u.get("level") or 1
        elif role in ("question_group", "answer", "analysis", "knowledge") and last_section:
            u["parent"] = last_section
        if role == "shared_material":
            last_material = u["id"]
        elif role == "question_group" and last_material:
            u["bind_to"] = last_material
            u["_evidence"] += "；绑定材料 %s（相邻）" % last_material
    return units


def predict(doc):
    """Return the exact old candidate pipeline in gold_compare-compatible form."""
    index = NodeIndex(doc)
    units = build_units(index, detect(index, doc))
    units = merge_adjacent(index, units)
    units = fill_gaps(index, units)
    units = assign_relations(units)
    return index, [{"id": u["id"], "role": u["role"], **(
        {k: u[k] for k in ("level", "parent", "bind_to") if u.get(k) is not None}),
        "spans": u["spans"], "note": "[%s] %s" % (u["_conf"], u["_evidence"])} for u in units]


def _unit_exact_role(gold, pred):
    return gold.role == pred.role


def role_metrics(cmp):
    roles = ("section", "toc", "question_group", "shared_material", "answer", "analysis", "unknown")
    result = {}
    for role in roles:
        golds = [u for u in cmp.gold_units if u.role == role]
        preds = [u for u in cmp.pred_units if u.role == role]
        # A deterministic one-to-one exact match (in document order).
        used_g, used_p, correct = set(), set(), 0
        for g in golds:
            for p in preds:
                if p.id not in used_p and g.id not in used_g and g.nodes == p.nodes:
                    correct += 1
                    used_g.add(g.id)
                    used_p.add(p.id)
                    break
        boundary = sum(1 for g in golds if g.nodes and any(
            g.nodes & p.nodes for p in preds) and g.id not in used_g)
        result[role] = {"gold": len(golds), "predicted": len(preds), "correct": correct,
                        "missed": len(golds) - correct, "erroneous": len(preds) - correct,
                        "boundary_errors": boundary, "binding_errors": 0}
    gold_by_id = {u.id: u for u in cmp.gold_units}
    for issue in cmp.issues:
        if issue.code != "UNBOUND" or "<->" not in issue.subject:
            continue
        left, right = issue.subject.split("<->", 1)
        for uid in (left, right):
            unit = gold_by_id.get(uid)
            if unit and unit.role in result:
                result[unit.role]["binding_errors"] += 1
    return result


def _read_sample(root, spec):
    path = os.path.join(root, spec["source"])
    if spec.get("member"):
        with zipfile.ZipFile(path) as zf:
            data = zf.read(spec["member"])
        name = os.path.basename(spec["member"])
    else:
        with open(path, "rb") as fh:
            data = fh.read()
        name = os.path.basename(path)
    sha = hashlib.sha256(data).hexdigest()
    if sha.lower() != spec["sha256"].lower():
        raise ValueError("%s source SHA256 mismatch: expected %s got %s" %
                         (spec["sample_id"], spec["sha256"], sha))
    return name, data


def run(manifest_path, corpus_root, out_dir):
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    summaries = []
    all_issue_counts = Counter()
    for spec in manifest["samples"]:
        sample_id = spec["sample_id"]
        name, data = _read_sample(corpus_root, spec)
        gold_path = os.path.abspath(os.path.join(os.path.dirname(manifest_path), spec["gold"]))
        with open(gold_path, encoding="utf-8") as fh:
            gold = json.load(fh)
        doc = read_struct_doc_bytes(data, name=name)
        index, predicted = predict(doc)
        cmp = compare(doc, gold, predicted)
        issues = Counter(i.code for i in cmp.issues)
        all_issue_counts.update(issues)
        role_stats = role_metrics(cmp)
        pred_doc = {"doc": name, "baseline": BASELINE_ID, "units": predicted}
        prefix = os.path.join(out_dir, sample_id)
        with open(prefix + "_pred.json", "w", encoding="utf-8") as fh:
            json.dump(pred_doc, fh, ensure_ascii=False, indent=2)
        with open(prefix + "_gold_compare.md", "w", encoding="utf-8") as fh:
            fh.write(render_report(doc, cmp, gold_path, prefix + "_pred.json"))
        with open(prefix + "_gold_compare.json", "w", encoding="utf-8") as fh:
            json.dump(cmp.as_dict(), fh, ensure_ascii=False, indent=2)
        summaries.append({"sample_id": sample_id, "name": name, "source_sha256": spec["sha256"],
                          "node_count": len(index.nodes), "gold_unit_count": cmp.summary["gold_units"],
                          "prediction_count": len(predicted), "binding_errors": issues.get("UNBOUND", 0),
                          "gold_compare_verdict": cmp.verdict, "errors": cmp.summary["errors"],
                          "warnings": cmp.summary["warns"], "infos": cmp.summary["infos"],
                          "roles": role_stats,
                          "issue_counts": dict(sorted(issues.items())),
                          "top_failure_codes": [c for c, _ in issues.most_common(3)]})
    gold_files = {}
    for spec in manifest["samples"]:
        gold_path = os.path.abspath(os.path.join(os.path.dirname(manifest_path), spec["gold"]))
        with open(gold_path, "rb") as fh:
            gold_sha = hashlib.sha256(fh.read()).hexdigest()
        gold_files[spec["sample_id"]] = {"path": spec["gold"], "sha256": gold_sha}
    roles = ("section", "toc", "question_group", "shared_material", "answer", "analysis", "unknown")
    role_totals = {
        role: {key: sum(sample["roles"][role][key] for sample in summaries)
               for key in ("gold", "predicted", "correct", "missed", "erroneous",
                           "boundary_errors", "binding_errors")}
        for role in roles
    }
    return {"baseline": BASELINE_ID, "rule_source": "_research/gen_gold_draft.py",
            "gold_files": gold_files,
            "samples": summaries, "issue_counts": dict(sorted(all_issue_counts.items())),
            "role_totals": role_totals}


def render_summary(summary):
    qg = summary["role_totals"]["question_group"]
    lines = ["# Splitter V2 Stage2 题目边界与共享材料基线", "",
             "本轮在 Stage2-1 题目边界规则上增加了通用阅读材料识别：显式材料标题或来源年份标记"
             "起始 shared_material，材料前独立序号作为 section，题干中的连续阅读题组成 question_group"
             "并绑定到最近材料；答案区按答案键行与解析标记切分 answer/analysis。"
             "未修改 Gold，`gold_compare.py` 是正式对照器。",
             "正确=Gold 单元与预测单元节点集合完全相同且角色相同；漏识别=未精确匹配的 Gold 单元；"
             "错误识别=未精确匹配的预测单元；边界错误=有同角色预测与 Gold 节点相交但范围不一致。",
             "漏识别/错误识别统计单位为单元，可与边界错误重叠。程序额外输出 body/knowledge 等角色，"
             "此表只列本轮要求的七类角色。", "",
             "## 样本结果", "",
             "| 样本 | GoldCompare | Gold / 预测单元 | 错误/警告/提示 | 主要失败原因 |",
             "|---|---|---:|---:|---|"]
    for s in summary["samples"]:
        lines.append("| %s | %s | %d / %d | %d / %d / %d | %s |" %
                     (s["sample_id"], s["gold_compare_verdict"],
                      s["gold_unit_count"],
                      s["prediction_count"], s["errors"], s["warnings"], s["infos"],
                      ", ".join("%s×%d" % (c, s["issue_counts"][c]) for c in s["top_failure_codes"]) or "无"))
    lines += ["", "## 按角色统计", ""]
    for s in summary["samples"]:
        lines += ["### %s" % s["sample_id"], "",
                  "| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for role, values in s["roles"].items():
            lines.append("| %s | %d | %d | %d | %d | %d | %d | %d |" %
                         (role, values["gold"], values["predicted"], values["correct"],
                          values["missed"], values["erroneous"], values["boundary_errors"],
                          values["binding_errors"]))
        lines.append("")
    lines += ["## 总体失败类型", ""]
    for code, count in summary["issue_counts"].items():
        lines.append("- `%s`: %d" % (code, count))
    binding_total = sum(s["binding_errors"] for s in summary["samples"])
    merge_total = summary["issue_counts"].get("MERGE", 0)
    lines += ["", "绑定错误（UNBOUND）：%d 对。角色表中的绑定错误端点分别计入题组和材料。" % binding_total,
              "", "## 边界结果解读", "",
              "四份正式 Gold 中 question_group 精确命中 %d/%d；GoldCompare 的 MERGE 共 %d。"
              "具体按样本及角色列于上表。" % (qg["correct"], qg["gold"], merge_total),
              "材料边界由文本标题/来源标记及题目起点共同确定；遇到下一材料时，上一题组在新材料前结束。", "",
              "## 可重复性", "", "同一 runner、相同 source SHA256、相同 Gold 文件与 StructDoc 代码会生成相同预测单元和对照统计；"
              "报告不含运行耗时等非确定性字段。", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Reproduce the frozen Stage2 heuristic baseline")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--corpus-root", required=True)
    ap.add_argument("--out", required=True, help="Reports/predictions directory outside repo/corpus")
    args = ap.parse_args()
    result = run(os.path.abspath(args.manifest), os.path.abspath(args.corpus_root), os.path.abspath(args.out))
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(render_summary(result))
    print(render_summary(result))


if __name__ == "__main__":
    main()

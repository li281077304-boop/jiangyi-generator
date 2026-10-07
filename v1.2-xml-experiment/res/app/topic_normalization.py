# -*- coding: utf-8 -*-
"""Deterministic display-only cleanup for lesson topics.

Pair resolution keeps its original topic identity. This helper is applied only
after source roles have been resolved and retains the unmodified topic as
provenance in the job record.
"""
from __future__ import annotations

import re


_TRAILING_PACKAGING = re.compile(
    r"\s*(?:高效培优讲义|高效培优|同步练习|复习讲义|专题讲义|练习讲义|讲义|"
    r"(?:数学|物理|化学|生物|英语|语文)?新教材|"
    r"(?:沪科|人教|北师大|苏科|鲁科|粤沪|教科|华师大|浙教|冀教|青岛|湘教|"
    r"统编|部编|外研|译林|牛津|人教版|北师大版)[^\s（）()【】]{0,12}版|"
    r"(?:七|八|九|高一|高二|高三|初一|初二|初三|\d+)年级(?:上|下)(?:学期|册)|"
    r"(?:上|下)学期|(?:期中|期末)(?:复习|备考|冲刺)?|"
    r"(?:教师版|学生版|原卷版|解析版|答案版|无答案版|空白版))\s*$",
    re.I,
)
_ROLE_SUFFIX = re.compile(r"\s*[（(【\[]?\s*(?:教师版|学生版|原卷版|解析版|答案版|无答案版|空白版)\s*[）)】\]]?\s*$", re.I)
_PACKAGING_PAREN_SUFFIX = re.compile(
    r"\s*[（(](?:高效培优讲义|高效培优|同步练习|复习讲义|专题讲义|练习讲义|讲义)[）)]\s*$",
    re.I,
)
_LEADING_REVIEW_CONTEXT = re.compile(
    r"^(?:(?:20\d{2}[-—]20\d{2}学年)?"
    r"(?:小学|初中|高中|(?:七|八|九|高一|高二|高三|初一|初二|初三)年级)?"
    r"(?:上|下)(?:学期)?(?:语文|数学|物理|化学|生物|英语|政治|历史|地理)?"
    r"(?:期中|期末)复习)"
)
_COUNTED_ERROR_SELECTION = re.compile(
    r"^[（(]?\s*易错精选\s*\d+\s*题\s*\d+\s*大考点\s*[）)]?$"
)


def normalize_display_topic(topic: str) -> str:
    """Remove recognized trailing packaging/course metadata, never rewrite core words."""
    original = str(topic or "").strip()
    value = re.sub(r"\.(?:docx?|dotx?)$", "", original, flags=re.I).strip()
    value = _ROLE_SUFFIX.sub("", value).strip()
    # Generic exam context already appears in the selected course fields.
    # For a counted "易错精选 N 题 M 大考点" document, keep a compact source-
    # grounded descriptor rather than carrying the grade/semester/count tail
    # into the cover title.
    review_context = _LEADING_REVIEW_CONTEXT.match(value)
    if review_context:
        value = value[review_context.end():].strip()
        value = re.sub(r"^[（(]", "", value)
        value = re.sub(r"[）)]$", "", value).strip()
        if _COUNTED_ERROR_SELECTION.fullmatch(value):
            return "易错题精选"
    # Remove only known packaging/course terms at the end. Internal words such
    # as “中考压轴题” may be the actual topic, and explanatory parentheses
    # such as “（定义域与值域）” are content, so neither is a cut point.
    while True:
        trimmed = _TRAILING_PACKAGING.sub("", value).strip()
        if trimmed == value:
            trimmed = _PACKAGING_PAREN_SUFFIX.sub("", value).strip()
        if trimmed == value:
            break
        value = trimmed
    value = re.sub(r"[\s_\-—:：|]+$", "", value)
    value = re.sub(r"\s+", " ", value).strip(" .。-—_")
    return value or original or "讲义"

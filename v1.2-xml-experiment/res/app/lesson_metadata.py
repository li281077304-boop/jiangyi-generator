# -*- coding: utf-8 -*-
"""Source-grounded cover metadata for the V1.2 production route.

The historical offline objective rule is reused for knowledge-point lessons.
Training-only lessons use only explicit topic/type headings from the source;
this module never calls an AI service and never reads text from a template.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from pathlib import Path

from docx import Document


class LessonMetadataUnavailable(ValueError):
    """Neither the source nor an approved offline rule can supply cover text."""

    reason_code = "OBJECTIVES_SOURCE_UNAVAILABLE"


@dataclass(frozen=True)
class LessonMetadata:
    objectives: str
    difficulties: str
    source: str
    knowledge_point_status: str
    training_titles: tuple[str, ...] = ()
    objectives_source: str = ""
    difficulties_source: str = ""

    @property
    def full_objectives(self) -> str:
        return self.objectives

    @property
    def full_difficulties(self) -> str:
        return self.difficulties


# Measured with frozen templates in WPS 12.0, Songti 10--11pt. One
# line at 40/36 CJK characters kept the original Y in 1v1/class; retain
# two CJK characters of headroom. These are display limits, not page estimates.
COVER_DISPLAY_BUDGET = {
    "1v1": {"max_logical_lines": 1, "max_display_width_units": 76},
    "class": {"max_logical_lines": 1, "max_display_width_units": 68},
}


def display_width_units(text: str) -> int:
    """Conservative half-width units; combining marks occupy no extra width."""
    return sum(0 if unicodedata.combining(char) else
               2 if unicodedata.east_asian_width(char) in "FWA" or char in "MWmw@" else 1
               for char in text)


def _clauses(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", value).strip(" ;；。") for value in
            re.split(r"[\n；;。]+|(?=[①②③④⑤⑥⑦⑧⑨⑩])", text)
            if value.strip(" ;；。\t\r\n")]


def _ellipsize(text: str, limit: int) -> str:
    if display_width_units(text) <= limit:
        return text
    result = ""
    for char in text:
        if display_width_units(result + char + "…") > limit:
            break
        result += char
    return result.rstrip() + "…"


def _select_clauses(text: str, limit: int) -> str:
    clauses = _clauses(text)
    selected: list[str] = []
    for clause in clauses:
        candidate = "；".join(selected + [clause])
        if display_width_units(candidate) <= limit:
            selected.append(clause)
    return "；".join(selected) if selected else _ellipsize(clauses[0], limit) if clauses else ""


def _select_difficulties(text: str, limit: int) -> str:
    clauses = _clauses(text)
    priority = [next((clause for clause in clauses if re.match(pattern, clause)), "")
                for pattern in (r"^(?:教学)?重点\s*[:：]", r"^(?:教学)?难点\s*[:：]")]
    if not all(priority):
        return _select_clauses(text, limit)
    joined = "；".join(priority)
    if display_width_units(joined) <= limit:
        return joined
    available = limit - display_width_units("；")
    first_width, second_width = map(display_width_units, priority)
    if first_width <= available // 2:
        allocations = (first_width, available - first_width)
    elif second_width <= available // 2:
        allocations = (available - second_width, second_width)
    else:
        allocations = (available // 2, available - available // 2)
    return "；".join(_ellipsize(clause, space) for clause, space in zip(priority, allocations))


def build_cover_display(metadata: LessonMetadata, template_type: str, *, topic: str = "") -> dict:
    """Retain full values and project deterministic, fixed-budget cover text."""
    budget = dict(COVER_DISPLAY_BUDGET[template_type])
    limit = budget["max_display_width_units"]
    values = {}
    methods = {}
    for field in ("objectives", "difficulties"):
        full = getattr(metadata, field)
        origin = getattr(metadata, field + "_source") or metadata.source
        if origin in ("TRAINING_TYPE_HEADINGS", "V09_OFFLINE_RULE"):
            if origin == "TRAINING_TYPE_HEADINGS":
                anchors = [*metadata.training_titles[:1], "本专题"]
                pattern = ("掌握{anchor}题型方法；规范分析与解答。" if field == "objectives" else
                           "重点：{anchor}题型与方法；难点：条件分析与易错辨析。")
            else:
                anchors = [topic, "本专题"] if topic else ["本专题"]
                pattern = ("掌握{anchor}概念与方法；规范推理与解答。" if field == "objectives" else
                           "重点：{anchor}基本方法；难点：综合运用与易错辨析。")
            values[field] = next(pattern.format(anchor=anchor) for anchor in anchors
                                 if display_width_units(pattern.format(anchor=anchor)) <= limit)
            methods[field] = "SHORT_OFFLINE_RULE"
        else:
            selector = _select_clauses if field == "objectives" else _select_difficulties
            values[field] = selector(full, limit)
            methods[field] = "SOURCE_CLAUSE_SELECTION"
    return {**values, "budget": budget,
            "cover_metadata_compacted": any(values[key] != getattr(metadata, key) for key in values),
            "compaction_methods": methods}


_FIELD = re.compile(r"^\s*[【\[]?\s*(教学目标|学习目标|重点难点|教学重难点|重难点|教学重点|教学难点|重点|难点)\s*[】\]]?\s*[:：]?\s*(.*?)\s*$")
_TITLE = re.compile(r"^\s*(?:题型|专题|考点)\s*(?:第\s*)?(?:\d+|[一二三四五六七八九十]+)\s*[、.．:：、\-]?\s*(.*?)\s*$")
_SECTION_BREAK = re.compile(r"^(?:第?[一二三四五六七八九十\d]+[、.．]|课堂启动|知识回顾|知识精讲|即时训练|归纳总结|巩固练习|出门测试|参考答案|答案与解析)")
_QUESTION = re.compile(r"^\s*(?:\d{1,3}[.．、)）]|[（(]\d+[）)])")
_TYPE_RE = re.compile(r"^(?:【)?题型\s*(\d+)")
_KNOWLEDGE_SECTION_RE = re.compile(
    r"^(知识点|考点|知识要点|知识梳理|要点|概念|定义|公式|定理|性质|法则|方法|规律|技巧|注意|说明|提醒|小结)[\s：:、]*\d*"
)
_ORDERED_HEADER_RE = re.compile(r"^[一二三四五六七八九十]+[、.． ](.+)$")
_NUMBERED_QUESTION_RE = re.compile(r"^\s*(\d{1,3})\s*[.．、)）]")


def _source_lines(source_path: str | Path) -> list[str]:
    document = Document(str(source_path))
    lines: list[str] = []
    body = document.element.body
    # Walk only the main story and retain the physical paragraph order, including
    # paragraphs in tables. Header/footer text is intentionally excluded.
    for paragraph in body.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        pieces = []
        for node in paragraph.iter():
            if node.tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t":
                pieces.append(node.text or "")
            elif node.tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tab":
                pieces.append("\t")
            elif node.tag in ("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br",
                              "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cr"):
                pieces.append("\n")
        text = "".join(pieces).strip()
        if text:
            lines.append(text)
    return lines


def _extract_explicit_fields(lines: list[str]) -> tuple[str, str]:
    objectives: list[str] = []
    difficulties: list[str] = []
    active: str | None = None

    def append(value: str) -> None:
        value = value.strip()
        if not value:
            return
        if active == "objectives":
            objectives.append(value)
        elif active == "difficulties":
            difficulties.append(value)

    for line in lines:
        match = _FIELD.match(line)
        if match:
            label, value = match.groups()
            if label in ("教学目标", "学习目标"):
                active = "objectives"
                append(value)
            elif label in ("重点难点", "教学重难点", "重难点"):
                active = "difficulties"
                append(value)
            elif label in ("重点", "教学重点"):
                active = "difficulties"
                append("重点：" + value if value else "")
            else:
                active = "difficulties"
                append("难点：" + value if value else "")
            continue
        if active and _SECTION_BREAK.match(line):
            active = None
            continue
        if active:
            append(line)

    return "\n".join(objectives).strip(), "\n".join(difficulties).strip()


def _training_titles(lines: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    for line in lines:
        match = _TITLE.match(line)
        if not match:
            continue
        title = re.sub(r"[\t ]+\d+$", "", match.group(1)).strip(" ：:、.-")
        if title and len(title) <= 48 and not _QUESTION.match(title) and title not in result:
            result.append(title)
    return tuple(result[:5])


def _training_metadata(topic: str, titles: tuple[str, ...]) -> tuple[str, str]:
    if not titles:
        return "", ""
    joined = "、".join(titles[:3])
    objectives = (
        f"①识别并掌握{joined}等题型的解题方法；\n"
        f"②能依据题目条件完成“{topic}”专题训练，并规范表达解题过程。"
    )
    difficulties = (
        f"重点：{joined}等题型的识别与相应方法运用。\n"
        "难点：题目条件分析、方法选择与易错点辨析。"
    )
    return objectives, difficulties


def _existing_offline_rule(topic: str, lines: list[str]) -> tuple[str, str]:
    """V1.1/V0.9 local rules, using XML main-story text without COM scanning."""
    knowledge_titles: list[str] = []
    type_titles: list[str] = []
    practice_tags: list[str] = []
    question_count = 0
    example_count = 0
    seen_q1 = False
    markers = ("基础速刷", "能力跃升", "能力提升", "提优训练", "拔高训练",
               "真题闯关", "课后三阶", "对点训练", "即学即练", "变式训练",
               "拓展训练", "强化训练", "综合训练", "模拟演练")

    for text in lines:
        value = text.strip()
        if not value:
            continue
        if _TYPE_RE.match(value):
            name = re.sub(r"^【?\s*题型\s*\d+\s*】?\s*", "", value).strip("【】 ")
            if name and len(name) < 30 and name not in type_titles:
                type_titles.append(name)
            continue
        if _KNOWLEDGE_SECTION_RE.match(value):
            name = _KNOWLEDGE_SECTION_RE.sub("", value).strip().lstrip("：:、 ")
            if name and len(name) < 30 and name not in knowledge_titles:
                knowledge_titles.append(name)
            continue
        ordered = _ORDERED_HEADER_RE.match(value)
        if ordered:
            name = ordered.group(1).strip()
            if (name and len(name) < 30 and not any(
                    word in name for word in ("题型", "练习", "训练", "巩固", "测试"))
                    and name not in knowledge_titles):
                knowledge_titles.append(name)
            continue
        numbered = _NUMBERED_QUESTION_RE.match(value)
        if numbered:
            number = int(numbered.group(1))
            if number == 1 and not seen_q1:
                seen_q1 = True
                question_count += 1
            elif number == question_count + 1:
                question_count += 1
            continue
        if re.match(r"^例\s*\d+", value):
            example_count += 1
        for marker in markers:
            if marker in value:
                if marker not in practice_tags:
                    practice_tags.append(marker)
                break

    knowledge_titles = list(dict.fromkeys(knowledge_titles))[:3]
    type_titles = list(dict.fromkeys(type_titles))[:3]
    practice_tags = list(dict.fromkeys(practice_tags))[:2]
    if knowledge_titles:
        objective_one = f"①掌握{topic}核心知识：{'、'.join(knowledge_titles)}等；"
    else:
        objective_one = f"①掌握{topic}的核心概念与基本方法；"
    question_names = type_titles or practice_tags
    question_part = ("、".join(question_names) + "等") if question_names else "本专题典型问题"
    if question_count:
        objective_two = f"②掌握{question_part}题型的解法，共{question_count}道题；"
    else:
        objective_two = f"②掌握{question_part}题型的解法，熟练求解；"
    objective_three = "③培养运算与推理能力，形成知识体系。"
    objectives = "\n".join((objective_one, objective_two, objective_three))
    if knowledge_titles:
        key_point = f"重点：{topic}核心概念（{'、'.join(knowledge_titles[:2])}）的理解与应用；"
    else:
        key_point = f"重点：{topic}核心知识点与基本方法；"
    difficulty = f"难点：{question_part}的综合运用与易错点辨析。" if question_names else \
        "难点：知识的综合运用与易错点辨析。"
    return objectives, key_point + "\n" + difficulty


def resolve_lesson_metadata(
    source_path: str | Path,
    *,
    subject: str,
    topic: str,
    knowledge_point_status: str,
) -> LessonMetadata:
    """Prefer source fields; otherwise reuse deterministic offline rules."""
    if knowledge_point_status not in ("KNOWLEDGE_POINT_PRESENT", "NO_KNOWLEDGE_POINT"):
        raise LessonMetadataUnavailable("knowledge-point status is unresolved")
    lines = _source_lines(source_path)
    objectives, difficulties = _extract_explicit_fields(lines)
    titles = _training_titles(lines)
    sources: list[str] = ["SOURCE" if objectives else "", "SOURCE" if difficulties else ""]

    missing_objectives = not objectives
    missing_difficulties = not difficulties
    if missing_objectives or missing_difficulties:
        if knowledge_point_status == "NO_KNOWLEDGE_POINT":
            derived_objectives, derived_difficulties = _training_metadata(topic, titles)
            rule_source = "TRAINING_TYPE_HEADINGS"
        else:
            # This mirrors the existing V1.1/V0.9 deterministic offline rule.
            # Its input order comes from the XML main story; no COM scan is used.
            derived_objectives, derived_difficulties = _existing_offline_rule(topic, lines)
            rule_source = "V09_OFFLINE_RULE"
        if missing_objectives:
            objectives = derived_objectives.strip()
            sources[0] = rule_source if objectives else ""
        if missing_difficulties:
            difficulties = derived_difficulties.strip()
            sources[1] = rule_source if difficulties else ""

    if not objectives or not difficulties:
        raise LessonMetadataUnavailable(
            "source fields and approved deterministic rules did not supply both cover fields")
    unique_sources = list(dict.fromkeys(item for item in sources if item))
    return LessonMetadata(
        objectives=objectives,
        difficulties=difficulties,
        source="+".join(unique_sources),
        knowledge_point_status=knowledge_point_status,
        training_titles=titles,
        objectives_source=sources[0],
        difficulties_source=sources[1],
    )

# -*- coding: utf-8 -*-
"""C1 business-rule router from frozen A-Line units to template slots.

This module consumes A-Line output without changing its classification rules.
It routes whole source blocks, keeps each physical top-level block in exactly
one slot, and rejects ambiguous or conflicting plans before the XML renderer
is called.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

from docx import Document

from renderer_xml_minimal import BlockSpan, TemplateTarget
from semantic_facade import SemanticSnapshot, analyze_source
from template_block_plan import resolve_template


SLOT_ORDER = ("knowledge", "immediate", "final")
SLOT_LABELS = {
    "1v1": {
        "knowledge": "知识精讲",
        "immediate": "即时训练",
        "final": "六、巩固练习",
    },
    "class": {
        "knowledge": "知识精讲&例题讲解",
        "immediate": "即时训练",
        "final": "六、出门测试",
    },
}
# The frozen templates use this printed anchor for slot 1 in both templates.
TEMPLATE_ANCHORS = {
    "1v1": ("知识精讲&例题讲解", "即时训练", "六、巩固练习"),
    "class": ("知识精讲&例题讲解", "即时训练", "六、出门测试"),
}

IMMEDIATE_HEADINGS = (
    "即时训练", "即学即练", "对点训练", "随堂练习", "课堂练习",
)
FINAL_HEADINGS = {
    "1v1": ("巩固练习", "课后练习", "综合练习", "达标检测"),
    "class": ("出门测试", "当堂检测", "达标检测", "课后测试"),
}
KNOWLEDGE_HEADINGS = (
    "知识精讲", "知识点", "知识篇", "考点梳理", "概念", "定义", "方法",
    "技巧", "例题讲解", "知识讲解", "知识回顾", "题型讲解", "典例精讲",
    "典例剖析", "例题精讲", "方法指导", "技法指导", "技法点拨",
)
ANSWER_HEADINGS = (
    "参考答案", "参考解答", "答案", "答案解析", "答案与解析", "答案及解析",
    "解析与答案", "答案详解", "答案与点拨", "试题解析",
)
_GENERIC_HEADING = re.compile(r"^(?:题型|专题|考点)\s*(?:第\s*)?\d+")
_ORDER_PREFIX = re.compile(r"^(?:第\s*)?[一二三四五六七八九十\d]+\s*[、.．)）:：-]*\s*")
_EXAMPLE = re.compile(r"^(?:经典)?(?:例题?|典例)\s*\d+")
_QUESTION_NUMBER = re.compile(r"^\s*(\d{1,3})\s*[.．、)）]\s*\S")
_COMPOSITE_QUESTION = re.compile(r"^(?:变式|例题|典例|练习)\s*(\d+)\s*[-－]\s*(\d+)")
_LABELED_QUESTION_NUMBER = re.compile(r"^(?:变式|练习|习题)\s*(\d{1,3})(?:\D|$)")
_WS = re.compile(r"\s+")


class SlotRoutingError(ValueError):
    """A slot plan cannot be produced without violating the approved rules."""

    def __init__(self, reason_code: str, detail: str):
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail


def validate_training_pair_routes(plans: dict[str, "SlotRoutingPlan"]) -> None:
    """Require teacher/student training plans to share question-slot routes."""
    if len(plans) < 2:
        return
    signatures = [tuple(getattr(plan, "training_question_routes", ()))
                  for plan in plans.values()]
    if any(not signature for signature in signatures):
        raise SlotRoutingError(
            "TEACHER_STUDENT_ROUTE_SIGNATURE_UNAVAILABLE",
            "paired training-only plans need visible question-start route signatures",
        )
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise SlotRoutingError(
            "TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH",
            "teacher and student question numbers route to different teaching slots",
        )


@dataclass(frozen=True)
class SlotRoutingPlan:
    source_path: Path
    source_sha256: str
    template_type: str
    template_path: Path
    template_sha256: str
    target: TemplateTarget
    slots: dict[str, tuple[BlockSpan, ...]]
    slot_labels: dict[str, str]
    template_anchors: tuple[str, str, str]
    block_records: tuple[dict[str, Any], ...]
    units: tuple[dict[str, Any], ...]
    explicit_final_heading: bool
    knowledge_point_status: str
    omitted_slots: tuple[str, ...]
    training_split_strategy: str = "NOT_APPLICABLE"
    training_question_routes: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class _Unit:
    raw: dict[str, Any]
    role: str
    unit_id: str
    seqs: frozenset[int]
    node_ids: frozenset[str]
    start_seq: int
    end_seq: int
    order: int
    text: str


def _clean(text: str) -> str:
    value = _WS.sub(" ", text or "").strip()
    value = value.lstrip("⚡🚀🔥⭐★◆●▪·▌■□◇○※【[（( ")
    return _ORDER_PREFIX.sub("", value).strip()


def _top_seq(node_id: str) -> int | None:
    root = str(node_id).split(".", 1)[0]
    if root.startswith("b") and root[1:].isdigit():
        return int(root[1:])
    return None


def _unit_text(snapshot: SemanticSnapshot, spans: list) -> str:
    index = snapshot.node_index
    ids: set[str] = set()
    for start, end in spans:
        ids.update(index.interval(str(start), str(end)))
    return " ".join(index.text_of(node_id) for node_id in sorted(
        ids, key=lambda item: (index.order_of(item) is None, index.order_of(item) or 0))
        if index.text_of(node_id))


def _make_units(snapshot: SemanticSnapshot) -> list[_Unit]:
    out: list[_Unit] = []
    total = len(snapshot.document.blocks)
    for raw in snapshot.units:
        spans = raw.get("spans")
        if not isinstance(spans, list) or not spans:
            raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS",
                                   "A-Line unit %s has no source spans" % raw.get("id"))
        seqs: set[int] = set()
        node_ids: set[str] = set()
        orders: list[int] = []
        for pair in spans:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS", "malformed A-Line span")
            start, end = str(pair[0]), str(pair[1])
            first, last = _top_seq(start), _top_seq(end)
            start_order, end_order = snapshot.node_index.order_of(start), snapshot.node_index.order_of(end)
            if (first is None or last is None or first > last or last >= total
                    or start_order is None or end_order is None or start_order > end_order):
                raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS",
                                       "unprojectable A-Line span %s..%s" % (start, end))
            interval_ids = snapshot.node_index.interval(start, end)
            if not interval_ids:
                raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS",
                                       "empty StructDoc node interval %s..%s" % (start, end))
            node_ids.update(interval_ids)
            seqs.update(_top_seq(node_id) for node_id in interval_ids)
            orders.append(start_order)
        out.append(_Unit(raw, str(raw.get("role") or ""), str(raw.get("id") or ""),
                         frozenset(seqs), frozenset(node_ids), min(seqs), max(seqs), min(orders),
                         _WS.sub(" ", _unit_text(snapshot, spans) or "").strip()))
    return sorted(out, key=lambda item: (item.start_seq, item.order, item.unit_id))


def _balanced_slots(count: int) -> list[str]:
    """Deterministically divide ordered units among the three teaching slots."""
    if count < 1:
        return []
    return [SLOT_ORDER[min(2, (index * 3) // count)] for index in range(count)]


def _training_only_node_routes(
    snapshot: SemanticSnapshot,
    units: list[_Unit],
    sections: list[_Unit],
    template_type: str,
) -> tuple[dict[int, str], str, tuple[tuple[int, str], ...]]:
    """Route training-only exercises from reliable physical question starts.

    Teacher and student A-Line groups may differ after answer removal. Natural
    numbered starts are the shared coordinate when they cover every semantic
    question group. A multi-question group can then cross slots only at distinct
    physical paragraph boundaries; one paragraph or table cannot be split.
    """
    qgs = sorted((unit for unit in units if unit.role == "question_group"),
                 key=lambda unit: (unit.order, unit.unit_id))
    if not qgs:
        raise SlotRoutingError("TRAINING_QUESTIONS_UNRESOLVED",
                               "NO_KNOWLEDGE_POINT source has no reliable question groups")
    by_id = {unit.unit_id: unit for unit in units}
    grouped: dict[str, list[_Unit]] = {}
    unowned: list[_Unit] = []
    for qg in qgs:
        owner = _section_for(qg, by_id, sections)
        owner_route = _heading_route(owner.text, template_type) if owner is not None else None
        explicit_knowledge_heading = owner is not None and any(
            _clean(owner.text).startswith(label) for label in KNOWLEDGE_HEADINGS)
        if (owner is not None and not explicit_knowledge_heading
                and owner_route not in ("immediate", "final", "answer_area")):
            grouped.setdefault(owner.unit_id, []).append(qg)
        else:
            unowned.append(qg)

    index = snapshot.node_index
    order_ids = index.order_ids
    section_by_id = {section.unit_id: section for section in sections}
    section_items: dict[str, list[tuple[int, int, int | None]]] = {}
    for section_id, group in grouped.items():
        section = section_by_id[section_id]
        next_sections = [item.order for item in sections
                         if (item.order, item.unit_id) > (section.order, section.unit_id)]
        section_start = min((index.order_of(node_id) for node_id in section.node_ids
                             if index.order_of(node_id) is not None), default=section.order)
        section_end = min(next_sections) if next_sections else len(order_ids)
        markers = []
        for position in range(section_start, section_end):
            node_id = order_ids[position]
            number = _visible_question_number(index.text_of(node_id))
            seq = _top_seq(node_id)
            if number is not None and seq is not None:
                markers.append((position, seq, number))
        covered = sum(1 for qg in group if any(qg.start_seq <= seq <= qg.end_seq
                                              for _position, seq, _number in markers))
        if markers and covered == len(group):
            # Numbering can legitimately restart within a section. Source
            # order, rather than numeric monotonicity, is the deterministic key.
            section_items[section_id] = markers
        else:
            section_items[section_id] = [(qg.order, qg.start_seq, None) for qg in group]

    if unowned and (grouped or sections):
        raise SlotRoutingError("TRAINING_QUESTIONS_UNRESOLVED",
                               "question group has no generic training-section owner")

    all_items = sorted(
        ((section_id, item) for section_id, items in section_items.items() for item in items),
        key=lambda entry: (entry[1][0], entry[0]),
    )
    singleton_sections = sum(len(items) == 1 for items in section_items.values())
    grouped_degraded = bool(section_items) and singleton_sections * 2 > len(section_items)
    strategy = ("GROUPED_DEGRADED" if grouped_degraded else "GROUPED_VERTICAL") if section_items else "SEQUENTIAL_DEGRADED"
    item_slots: dict[str, list[tuple[int, int, int | None, str]]] = {}
    if strategy == "GROUPED_VERTICAL":
        counts = {slot: 0 for slot in SLOT_ORDER}
        deferred = []
        for section_id, items in section_items.items():
            if len(items) == 1:
                deferred.append((section_id, items[0]))
                continue
            routed = [(*item, SLOT_ORDER[min(i, 2)]) for i, item in enumerate(items)]
            item_slots[section_id] = routed
            for _position, _seq, _number, slot in routed:
                counts[slot] += 1
        for section_id, item in sorted(deferred, key=lambda entry: entry[1][0]):
            slot = min(SLOT_ORDER, key=lambda candidate: (counts[candidate], SLOT_ORDER.index(candidate)))
            item_slots[section_id] = [(*item, slot)]
            counts[slot] += 1
    elif strategy == "GROUPED_DEGRADED":
        for (section_id, item), slot in zip(all_items, _balanced_slots(len(all_items))):
            item_slots.setdefault(section_id, []).append((*item, slot))
    else:
        markers = []
        for position, node_id in enumerate(order_ids):
            number = _visible_question_number(index.text_of(node_id))
            seq = _top_seq(node_id)
            if number is not None and seq is not None:
                markers.append((position, seq, number))
        covered = sum(1 for qg in qgs if any(qg.start_seq <= seq <= qg.end_seq
                                            for _position, seq, _number in markers))
        if markers and covered == len(qgs):
            global_items = [(*item, slot) for item, slot in zip(markers, _balanced_slots(len(markers)))]
        else:
            global_items = [ (qg.order, qg.start_seq, None, slot)
                             for qg, slot in zip(qgs, _balanced_slots(len(qgs))) ]

    marker_signature: list[tuple[int, str]] = []
    node_routes: dict[int, str] = {}
    marker_positions: list[tuple[int, str]] = []
    if strategy == "SEQUENTIAL_DEGRADED":
        ordered = sorted(global_items, key=lambda item: item[0])
        marker_signature.extend((int(number), slot) for _position, _seq, number, slot in ordered
                                if number is not None)
        marker_positions.extend((position, slot) for position, _seq, _number, slot in ordered)
        for position, node_id in enumerate(order_ids):
            preceding = [item for item in ordered if item[0] <= position]
            slot = preceding[-1][3] if preceding else ordered[0][3]
            seq = _top_seq(node_id)
            if seq is not None:
                previous = node_routes.get(seq)
                if previous is not None and previous != slot:
                    block = snapshot.document.blocks[seq]
                    code = "TABLE_SLOT_CONFLICT" if block.kind == "table" else "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT"
                    raise SlotRoutingError(code,
                                           "physical block b%d contains question starts routed to %s and %s" %
                                           (seq, previous, slot))
                node_routes[seq] = slot
    else:
        for section in sections:
            items = item_slots.get(section.unit_id)
            if not items:
                continue
            items.sort(key=lambda item: item[0])
            marker_signature.extend((int(number), slot) for _position, _seq, number, slot in items
                                    if number is not None)
            marker_positions.extend((position, slot) for position, _seq, _number, slot in items)
            next_sections = [item.order for item in sections
                             if (item.order, item.unit_id) > (section.order, section.unit_id)]
            section_start = min((index.order_of(node_id) for node_id in section.node_ids
                                 if index.order_of(node_id) is not None), default=section.order)
            section_end = min(next_sections) if next_sections else len(order_ids)
            for position in range(section_start, section_end):
                if position >= len(order_ids):
                    break
                node_id = order_ids[position]
                preceding = [item for item in items if item[0] <= position]
                slot = (preceding[-1] if preceding else items[0])[3]
                seq = _top_seq(node_id)
                if seq is None:
                    continue
                previous = node_routes.get(seq)
                if previous is not None and previous != slot:
                    block = snapshot.document.blocks[seq]
                    code = "TABLE_SLOT_CONFLICT" if block.kind == "table" else "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT"
                    raise SlotRoutingError(code,
                                           "physical block b%d contains question starts routed to %s and %s" %
                                           (seq, previous, slot))
                node_routes[seq] = slot

    routes = {seq: "knowledge" for seq in range(len(snapshot.document.blocks))}
    routes.update(node_routes)
    # Keep examples in the explanatory slot and reject any shared material
    # whose connected question groups request different destinations.
    for qg in qgs:
        if _is_example(qg):
            for seq in qg.seqs:
                if routes.get(seq) not in ("knowledge", None):
                    raise SlotRoutingError("SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT",
                                           "example %s overlaps a routed practice question" % qg.unit_id)
                routes[seq] = "knowledge"
    materials = {unit.unit_id: unit for unit in units if unit.role == "shared_material"}
    targets_by_material: dict[str, set[str]] = {}
    for qg in qgs:
        material_id = str(qg.raw.get("bind_to") or "")
        if not material_id:
            continue
        material = materials.get(material_id)
        if material is None:
            raise SlotRoutingError("SHARED_MATERIAL_BINDING_UNRESOLVED",
                                   "question group %s binds missing material %s" % (qg.unit_id, material_id))
        targets_by_material.setdefault(material_id, set()).update(routes[seq] for seq in qg.seqs)
    for material_id, targets in targets_by_material.items():
        if len(targets) != 1:
            raise SlotRoutingError("SHARED_MATERIAL_SLOT_CONFLICT",
                                   "shared material %s serves question groups in multiple slots" % material_id)
        for seq in materials[material_id].seqs:
            routes[seq] = next(iter(targets))

    # A top-level table remains atomic in the renderer. It may belong to one
    # slot, but a route boundary inside it is a hard capability refusal.
    for seq, block in enumerate(snapshot.document.blocks):
        if block.kind == "table":
            descendants = index.descendants.get("b%d" % seq, [])
            positions = [index.order_of(node_id) for node_id in descendants]
            intents = set()
            for position in positions:
                if position is None:
                    continue
                preceding = [item for item in marker_positions if item[0] <= position]
                if preceding:
                    intents.add(max(preceding, key=lambda item: item[0])[1])
            if len(intents) > 1:
                raise SlotRoutingError("TABLE_SLOT_CONFLICT",
                                       "table b%d contains question content routed across slots %s" %
                                       (seq, sorted(intents)))
    return routes, strategy, tuple(marker_signature)

def _heading_route(text: str, template_type: str) -> str | None:
    title = _clean(text)
    if not title:
        return None
    if any(title.startswith(label) for label in ANSWER_HEADINGS):
        return "answer_area"
    # “题型讲解” is explanatory; numbered generic type/topic headings are not.
    if title.startswith("题型讲解"):
        return "knowledge"
    if _GENERIC_HEADING.match(title):
        return "generic"
    if any(title.startswith(label) for label in FINAL_HEADINGS[template_type]):
        return "final"
    if any(title.startswith(label) for label in IMMEDIATE_HEADINGS):
        return "immediate"
    if any(title.startswith(label) for label in KNOWLEDGE_HEADINGS):
        return "knowledge"
    # Other section units can still be unambiguous if their heading is a
    # numbered title whose text explicitly says it is a training/test section.
    if any(token in title for token in ("出门测试", "当堂检测", "课后测试", "达标检测")):
        return "final" if any(title.startswith(label) for label in FINAL_HEADINGS[template_type]) else None
    if any(token in title for token in ("即时训练", "即学即练", "随堂练习", "课堂练习", "对点训练")):
        return "immediate"
    if any(token in title for token in ("训练", "练习", "检测", "测试", "作业")):
        return None
    return "knowledge" if title else None


def _section_for(unit: _Unit, by_id: dict[str, _Unit], sections: list[_Unit]) -> _Unit | None:
    parent = str(unit.raw.get("parent") or "")
    if parent in by_id and by_id[parent].role == "section":
        return by_id[parent]
    previous = [section for section in sections
                if (section.start_seq, section.order) <= (unit.start_seq, unit.order)]
    return previous[-1] if previous else None


def _number(text: str) -> tuple[int | None, tuple[int, int] | None]:
    # Keep a leading question number here. _clean() intentionally strips
    # editorial/order prefixes for heading classification, which would erase
    # the very numbering needed to find natural exercise-block boundaries.
    title = _WS.sub(" ", text or "").strip()
    title = title.lstrip("⚡🚀🔥⭐★◆●▪·▌■□◇○※【[（( ")
    composite = _COMPOSITE_QUESTION.match(title)
    if composite:
        return None, (int(composite.group(1)), int(composite.group(2)))
    labeled = _LABELED_QUESTION_NUMBER.match(title)
    if labeled:
        return int(labeled.group(1)), None
    match = _QUESTION_NUMBER.match(title)
    return (int(match.group(1)), None) if match else (None, None)


def _visible_question_number(text: str) -> int | None:
    """Parse a top-level numbered exercise without mistaking (1)/(2) subparts."""
    title = _WS.sub(" ", text or "").strip()
    title = title.lstrip("⚡🚀🔥⭐★◆●▪·▌■□◇○※【[ ")
    match = _QUESTION_NUMBER.match(title)
    return int(match.group(1)) if match else None


def _is_example(unit: _Unit) -> bool:
    note = str(unit.raw.get("note") or unit.raw.get("evidence") or "")
    return bool(_EXAMPLE.match(unit.text) or "例1默认保留在知识讲解" in note)


def _generic_practice_blocks(
    section: _Unit,
    section_units: list[_Unit],
    section_end: int,
) -> list[tuple[int, int, tuple[str, ...]]]:
    """Return natural numbered blocks after the first teaching example.

    The A-Line question_group is only a boundary hint. Adjacent groups stay in
    one block until numbering naturally restarts at 1. Runs with an invalid
    start or numbering gap are omitted from the schedule and remain in the
    knowledge slot; they are never cut to make a smaller candidate.
    """
    qgs = sorted((unit for unit in section_units if unit.role == "question_group"),
                 key=lambda unit: (unit.start_seq, unit.order))
    if not qgs:
        return []
    example = next((unit for unit in qgs if _is_example(unit)), None)
    if example is not None:
        qgs = [unit for unit in qgs if unit is not example and unit.start_seq > example.end_seq]
    if not qgs:
        return []

    blocks: list[list[_Unit]] = []
    current: list[_Unit] = []
    previous_number: int | None = None
    for unit in qgs:
        number, composite = _number(unit.text)
        starts_natural_one = number == 1 or (composite is not None and composite[1] == 1)
        if current and starts_natural_one and previous_number is not None and previous_number >= 2:
            blocks.append(current)
            current = []
            previous_number = None
        current.append(unit)
        if number is not None:
            previous_number = number
        elif composite is not None:
            previous_number = composite[1]
    if current:
        blocks.append(current)

    result = []
    for index, block in enumerate(blocks):
        start = min(unit.start_seq for unit in block)
        end = (min(unit.start_seq for unit in blocks[index + 1]) - 1
               if index + 1 < len(blocks) else section_end)
        # A parseable natural block may start at 1, or composite variant 1-1.
        number, composite = _number(block[0].text)
        if number != 1 and not (composite and composite[1] == 1):
            continue
        # If sequential numbers are visible, do not accept a hole inside a block.
        parsed = [(_number(unit.text)[0]) for unit in block]
        parsed = [value for value in parsed if value is not None]
        if parsed and any(right > left + 1 for left, right in zip(parsed, parsed[1:])):
            continue
        result.append((start, max(start, end), tuple(unit.unit_id for unit in block)))
    return result


def build_slot_routing_plan(
    source_path: str | Path,
    template_type: str,
    *,
    split_mode: str = "smart",
    snapshot: SemanticSnapshot | None = None,
) -> SlotRoutingPlan:
    """Route one source snapshot to three template-specific slots.

    Unsupported ownership, an indivisible physical block requested in more
    than one slot, or an ambiguous connected material component fails closed.
    """
    source = Path(source_path).resolve()
    if template_type not in SLOT_LABELS:
        raise SlotRoutingError("XML_RENDER_FAILED", "unsupported template type: %s" % template_type)
    if not source.is_file():
        raise SlotRoutingError("XML_RENDER_FAILED", "source DOCX is missing: %s" % source)
    if split_mode not in ("smart", "full"):
        raise SlotRoutingError("XML_RENDER_FAILED", "unsupported split mode: %s" % split_mode)
    template, template_digest = resolve_template(template_type)
    snapshot = snapshot or analyze_source(source)
    if not snapshot.units:
        raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS", "A-Line returned no semantic units")
    total = len(snapshot.document.blocks)
    if not total:
        raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS", "source has no main-story blocks")

    units = _make_units(snapshot)
    by_id = {unit.unit_id: unit for unit in units}
    units_by_seq: dict[int, list[str]] = {seq: [] for seq in range(total)}
    for unit in units:
        for seq in unit.seqs:
            units_by_seq[seq].append(unit.unit_id)
    tocs = [unit for unit in units if unit.role == "toc"]
    sections = [unit for unit in units if unit.role == "section"
                and not any(unit.order >= toc.order and unit.order <= max(
                    (snapshot.node_index.order_of(end) or toc.order) for _, end in toc.raw["spans"])
                    for toc in tocs)]
    sections.sort(key=lambda item: (item.start_seq, item.order))
    section_routes = {section.unit_id: _heading_route(section.text, template_type)
                      for section in sections}
    explicit_final = any(route == "final" for route in section_routes.values())
    has_explicit_knowledge = any(
        any(section.text.lstrip().startswith(label) for label in KNOWLEDGE_HEADINGS)
        for section in sections
    )
    has_knowledge_unit = any(unit.role == "knowledge" or
                             (unit.role == "question_group" and _is_example(unit))
                             for unit in units)
    has_training_units = any(unit.role == "question_group" for unit in units)
    knowledge_point_status = (
        "NO_KNOWLEDGE_POINT"
        if has_training_units and not has_explicit_knowledge and not has_knowledge_unit
        else "KNOWLEDGE_POINT_PRESENT"
    )
    training_only = knowledge_point_status == "NO_KNOWLEDGE_POINT"
    training_split_strategy = "NOT_APPLICABLE"
    training_routes: dict[int, str] | None = None
    training_question_routes: tuple[tuple[int, str], ...] = ()
    if (split_mode == "smart" and training_only
            and not any(route in ("immediate", "final") for route in section_routes.values())):
        training_routes, training_split_strategy, training_question_routes = _training_only_node_routes(
            snapshot, units, sections, template_type)

    # No semantic units means no reason to route content. Full mode deliberately
    # retains the ordered source as slot 1, preserving its established meaning.
    if split_mode == "full":
        full_slot = "immediate" if training_only else "knowledge"
        routes = {seq: full_slot for seq in range(total)}
    elif training_routes is not None:
        routes = training_routes
    else:
        owner_by_seq: dict[int, _Unit | None] = {}
        for seq in range(total):
            preceding = [section for section in sections if section.start_seq <= seq]
            owner_by_seq[seq] = preceding[-1] if preceding else None

        routes: dict[int, str] = {}
        for seq, owner in owner_by_seq.items():
            route = "knowledge" if owner is None else section_routes.get(owner.unit_id)
            if training_only:
                if route == "answer_area":
                    raise SlotRoutingError("ANSWER_OWNERSHIP_UNRESOLVED",
                                           "global answer/analysis section has no reliable question owner at b%d" % seq)
                # In a training-only source, generic/topic headings describe
                # practice context. Preserve the complete source sequence in
                # the training slot unless explicit training/final headings
                # or natural complete-block boundaries provide a better route.
                route = route if route in ("immediate", "final") else "immediate"
            if route is None:
                # A-Line section wording is not a destination rule. Do not
                # guess if it looks like exercise/test material.
                raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS",
                                       "unclassified section at b%d: %s" %
                                       (seq, owner.text if owner else ""))
            if route == "answer_area":
                raise SlotRoutingError("ANSWER_OWNERSHIP_UNRESOLVED",
                                       "global answer/analysis section has no reliable question owner at b%d" % seq)
            routes[seq] = "knowledge" if route == "generic" else route

        # Route whole generic-topic practice blocks. The only implicit final
        # slot is the final complete block, and only when no explicit final
        # heading already governs the source.
        generic_sections = [section for section in sections
                            if section_routes.get(section.unit_id) == "generic"]
        all_candidates: list[tuple[int, int, tuple[str, ...], str]] = []
        for section_index, section in enumerate(generic_sections):
            next_sections = [item.start_seq for item in sections
                             if (item.start_seq, item.order) > (section.start_seq, section.order)]
            section_end = min(next_sections) - 1 if next_sections else total - 1
            section_units = [unit for unit in units if _section_for(unit, by_id, sections) == section]
            for start, end, qg_ids in _generic_practice_blocks(section, section_units, section_end):
                all_candidates.append((start, end, qg_ids, section.unit_id))

        all_candidates.sort(key=lambda entry: entry[0])
        candidate_routes: dict[int, str] = {}
        for index, (start, end, qg_ids, section_id) in enumerate(all_candidates):
            route = "immediate"
            if not explicit_final and len(all_candidates) >= 2 and index == len(all_candidates) - 1:
                route = "final"
            for seq in range(start, end + 1):
                owner = owner_by_seq[seq]
                if owner is None or owner.unit_id != section_id:
                    # Explicit headings override a generic section's implicit
                    # practice candidate; do not cross that boundary.
                    continue
                existing = candidate_routes.get(seq)
                if existing is not None and existing != route:
                    code = ("TABLE_SLOT_CONFLICT" if snapshot.document.blocks[seq].kind == "table"
                            else "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT")
                    raise SlotRoutingError(
                        code,
                        "one physical source block is requested by practice units in %s and %s: b%d" %
                        (existing, route, seq),
                    )
                if snapshot.document.blocks[seq].kind == "table":
                    if any(section.start_seq == seq for section in sections):
                        raise SlotRoutingError(
                            "TABLE_SLOT_CONFLICT",
                            "generic heading and practice content share atomic table b%d" % seq,
                        )
                    if any(unit.role == "knowledge" and seq in unit.seqs for unit in units):
                        raise SlotRoutingError(
                            "TABLE_SLOT_CONFLICT",
                            "knowledge and practice content share atomic table b%d" % seq,
                        )
                candidate_routes[seq] = route
                routes[seq] = route

        # Example/knowledge units are never moved out of slot 1 by generic
        # practice ranges. This also protects A-Line's E2 example-one outcome.
        for unit in units:
            if unit.role == "knowledge" or (unit.role == "question_group" and _is_example(unit)):
                for seq in unit.seqs:
                    owner = owner_by_seq.get(seq)
                    if owner is not None and section_routes.get(owner.unit_id) == "generic":
                        if snapshot.document.blocks[seq].kind == "table" and routes.get(seq) != "knowledge":
                            raise SlotRoutingError(
                                "TABLE_SLOT_CONFLICT",
                                "teaching example and practice share atomic table b%d" % seq,
                            )
                        routes[seq] = "knowledge"

        # Shared material follows its bound question groups. If a material
        # connects groups assigned to different slots, fail instead of copy.
        material_units = {unit.unit_id: unit for unit in units if unit.role == "shared_material"}
        material_targets: dict[str, set[str]] = {}
        material_qgs: dict[str, list[str]] = {}
        for unit in units:
            if unit.role != "question_group":
                continue
            material_id = str(unit.raw.get("bind_to") or "")
            if not material_id:
                continue
            material = material_units.get(material_id)
            if material is None:
                raise SlotRoutingError("SHARED_MATERIAL_BINDING_UNRESOLVED",
                                       "question group %s binds missing material %s" %
                                       (unit.unit_id, material_id))
            targets = {routes[seq] for seq in unit.seqs if seq in routes}
            if not targets:
                raise SlotRoutingError("SHARED_MATERIAL_BINDING_UNRESOLVED",
                                       "question group %s has no routed source blocks" % unit.unit_id)
            material_targets.setdefault(material_id, set()).update(targets)
            material_qgs.setdefault(material_id, []).append(unit.unit_id)
        for material_id, targets in material_targets.items():
            if len(targets) != 1:
                raise SlotRoutingError("SHARED_MATERIAL_SLOT_CONFLICT",
                                       "shared material %s serves question groups in multiple slots" % material_id)
            route = next(iter(targets))
            material = material_units[material_id]
            for seq in material.seqs:
                routes[seq] = route

        # Every semantic unit with question ownership must agree with its
        # containing slot. Answer/analysis under knowledge sections remain in
        # knowledge even when their A-Line role is misleading.
        for unit in units:
            if unit.role not in ("question_group", "answer", "analysis", "knowledge"):
                continue
            owner = _section_for(unit, by_id, sections)
            if owner is None:
                continue
            section_route = section_routes.get(owner.unit_id)
            if training_only and section_route not in ("immediate", "final"):
                section_route = "immediate"
            if section_route == "answer_area":
                raise SlotRoutingError("ANSWER_OWNERSHIP_UNRESOLVED",
                                       "answer/analysis role has no reliable question owner: %s" % unit.unit_id)
            if section_route in ("knowledge", "immediate", "final"):
                for seq in unit.seqs:
                    if routes.get(seq) != section_route:
                        # A connected bound material is allowed to follow its
                        # question; all other section ownership conflicts fail.
                        if not (unit.role == "shared_material" and seq in routes):
                            raise SlotRoutingError("SLOT_ROUTING_SECTION_CONFLICT",
                                                   "unit %s crosses its explicit section boundary" % unit.unit_id)

        # One question group is an indivisible semantic block. Role overlap
        # must never leave some of its physical paragraphs in another slot.
        for unit in units:
            if unit.role != "question_group":
                continue
            targets = {routes[seq] for seq in unit.seqs}
            if len(targets) > 1:
                code = ("TABLE_SLOT_CONFLICT"
                        if any(snapshot.document.blocks[seq].kind == "table" for seq in unit.seqs)
                        else "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT")
                raise SlotRoutingError(
                    code,
                    "question group %s crosses destination slots: %s" %
                    (unit.unit_id, sorted(targets)),
                )

        # A top-level table is one physical block, but its cells can contain
        # multiple headings. Preserve every heading's routing intent before
        # collapsing that table to one destination.
        for seq, block in enumerate(snapshot.document.blocks):
            if block.kind != "table":
                continue
            intents: set[str] = set()
            for section in sections:
                if seq not in section.seqs:
                    continue
                section_route = section_routes.get(section.unit_id)
                if section_route == "answer_area":
                    raise SlotRoutingError(
                        "TABLE_SLOT_CONFLICT",
                        "table b%d contains an unowned answer/analysis heading" % seq,
                    )
                if section_route is not None:
                    if training_only:
                        intents.add(section_route if section_route in ("immediate", "final") else "immediate")
                    else:
                        intents.add("knowledge" if section_route == "generic" else section_route)
            if seq in candidate_routes:
                intents.add(candidate_routes[seq])
            if len(intents) > 1:
                raise SlotRoutingError(
                    "TABLE_SLOT_CONFLICT",
                    "table b%d contains content requesting multiple slots: %s" %
                    (seq, sorted(intents)),
                )

        # A natural practice block covers all physical content between its
        # first and next natural question-number restart. It remains atomic
        # after semantic role corrections above.
        for index, (start, end, _qg_ids, section_id) in enumerate(all_candidates):
            intended = "immediate"
            if not explicit_final and len(all_candidates) >= 2 and index == len(all_candidates) - 1:
                intended = "final"
            for seq in range(start, end + 1):
                if owner_by_seq[seq] != by_id[section_id]:
                    continue
                if routes[seq] != intended:
                    code = ("TABLE_SLOT_CONFLICT" if snapshot.document.blocks[seq].kind == "table"
                            else "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT")
                    raise SlotRoutingError(
                        code,
                        "natural practice block b%d..b%d crosses slots at b%d" %
                        (start, end, seq),
                    )

    # An indivisible table or overlapping semantic component cannot belong to
    # multiple destinations. A top-level table is one physical block/seq.
    blocks_by_slot = {slot: [] for slot in SLOT_ORDER}
    block_records = []
    for seq in range(total):
        route = routes[seq]
        if route not in blocks_by_slot:
            raise SlotRoutingError("SLOT_ROUTING_AMBIGUOUS", "invalid destination at b%d" % seq)
        block_id = "b%d" % seq
        blocks_by_slot[route].append(BlockSpan(block_id, block_id))
        block = snapshot.document.blocks[seq]
        block_records.append({
            "block_id": block_id,
            "source_index": seq,
            "kind": block.kind,
            "destination_slot": route,
            "unit_contributors": tuple(dict.fromkeys(units_by_seq.get(seq, []))),
        })

    # Verify span uniqueness and per-slot source order before exposing the plan.
    flattened = [span.start for slot in SLOT_ORDER for span in blocks_by_slot[slot]]
    if len(flattened) != total or len(set(flattened)) != total:
        raise SlotRoutingError("SLOT_ROUTING_DUPLICATE_OR_MISSING_BLOCK",
                               "physical source blocks are not assigned exactly once")
    for slot, spans in blocks_by_slot.items():
        seqs = [int(span.start[1:]) for span in spans]
        if seqs != sorted(seqs):
            raise SlotRoutingError("SLOT_ROUTING_ORDER_VIOLATION",
                                   "slot %s does not preserve source order" % slot)

    # All six template modules are product invariants. Empty content slots
    # retain their template headings; source absence never deletes modules.
    omitted_slots = ()

    template_body = Document(str(template)).element.body
    from struct_doc import W_SECTPR
    section_tail = next((index for index, child in enumerate(template_body)
                         if child.tag == W_SECTPR), len(template_body))
    if not any(child.tag.endswith("}tbl") for child in template_body[:section_tail]):
        raise SlotRoutingError("XML_RENDER_FAILED", "validated template has no content table")
    return SlotRoutingPlan(
        source_path=source,
        source_sha256=snapshot.source_sha256,
        template_type=template_type,
        template_path=template,
        template_sha256=template_digest,
        target=TemplateTarget(section_tail),
        slots={slot: tuple(blocks_by_slot[slot]) for slot in SLOT_ORDER},
        slot_labels=dict(SLOT_LABELS[template_type]),
        template_anchors=TEMPLATE_ANCHORS[template_type],
        block_records=tuple(block_records),
        units=tuple({
            "unit_id": unit.unit_id,
            "role": unit.role,
            "parent": unit.raw.get("parent"),
            "bind_to": unit.raw.get("bind_to"),
            "source_block_ids": tuple("b%d" % seq for seq in sorted(unit.seqs)),
        } for unit in units),
        explicit_final_heading=explicit_final,
        knowledge_point_status=knowledge_point_status,
        omitted_slots=omitted_slots,
        training_split_strategy=training_split_strategy,
        training_question_routes=training_question_routes,
    )

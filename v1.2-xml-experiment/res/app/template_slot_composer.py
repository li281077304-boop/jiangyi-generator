# -*- coding: utf-8 -*-
"""Place already-imported XML blocks into the frozen template slot anchors.

The B-Line renderer remains unchanged: it performs the package-safe source
block import into a staging DOCX. This C-Line composer moves those imported
physical blocks from the temporary body tail into the template's three merged
content-cell anchors, then validates the final package again.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Callable

from docx import Document
from docx.oxml import OxmlElement

from package_validator import validate_package
from renderer_xml_minimal import BlockSpan, ProjectionError, RenderResult
from slot_router import SLOT_ORDER, SlotRoutingError, SlotRoutingPlan
from struct_doc import W_P, W_SECTPR, W_T, W_TBL, W_TC


@dataclass(frozen=True)
class SlotRenderResult:
    output_path: str
    inserted_nodes: int
    slot_nodes: dict[str, int]
    resource_report: dict
    package_report: dict


def _paragraph_text(paragraph) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W_T)).strip()


def _set_paragraph_text(paragraph, value: str) -> None:
    text_nodes = list(paragraph.iter(W_T))
    if not text_nodes:
        raise SlotRoutingError("TEMPLATE_SLOT_ANCHOR_UNRESOLVED",
                               "template slot anchor has no editable text run")
    text_nodes[0].text = value
    for node in text_nodes[1:]:
        node.text = ""


def _clear_paragraph_numbering(paragraph) -> None:
    word_namespace = W_P[1:].split("}", 1)[0]
    p_pr = paragraph.find("{%s}pPr" % word_namespace)
    if p_pr is None:
        return
    num_pr = p_pr.find("{%s}numPr" % word_namespace)
    if num_pr is not None:
        p_pr.remove(num_pr)


_TRAINING_ONLY_TEMPLATE_HEADINGS = {
    "一、课堂启动", "二、知识回顾", "知识精讲", "知识精讲&例题讲解",
    "即时训练", "五、归纳总结", "六、巩固练习", "六、出门测试",
}


def _compact_training_only_template(cell, immediate_anchor) -> str:
    """Remove only known empty template placeholders around a training stream."""
    paragraphs = list(cell.findall(W_P))
    try:
        anchor_index = paragraphs.index(immediate_anchor)
    except ValueError as exc:
        raise SlotRoutingError("TEMPLATE_SLOT_ANCHOR_UNRESOLVED",
                               "training slot anchor is outside the teaching cell") from exc

    def is_known_placeholder(paragraph) -> bool:
        text = _paragraph_text(paragraph)
        return (not text or text in _TRAINING_ONLY_TEMPLATE_HEADINGS
                or (text and set(text) <= {"~"}))

    before = paragraphs[:anchor_index]
    after = paragraphs[anchor_index + 1:]
    if any(not is_known_placeholder(paragraph) for paragraph in before + after):
        raise SlotRoutingError("TRAINING_TEMPLATE_PLACEHOLDER_UNRESOLVED",
                               "training-only template has non-placeholder content outside its routed slot")
    for paragraph in before + after:
        parent = paragraph.getparent()
        if parent is not None:
            parent.remove(paragraph)
    _set_paragraph_text(immediate_anchor, "一、即时训练")
    _clear_paragraph_numbering(immediate_anchor)
    return "一、即时训练"


def _set_cover_cell_value(cell, value: str) -> None:
    """Replace the value portion of a known cover cell while keeping its label.

    Template cover labels and formatting are part of the frozen template. The
    metadata projection only changes the final non-empty text node in the
    selected value cell; an empty value cell receives a run using its existing
    paragraph properties.
    """
    value = str(value or "").strip()
    paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    text_nodes = list(paragraph._p.iter(W_T))
    value_node = next((node for node in reversed(text_nodes)
                       if (node.text or "").strip()), None)
    if value_node is None:
        if text_nodes:
            value_node = text_nodes[-1]
        else:
            paragraph.add_run(value)
            return
    old_text = value_node.text or ""
    separators = [position for mark in (":", "：")
                  if (position := old_text.rfind(mark)) >= 0]
    label = old_text[:max(separators) + 1] if separators else ""
    pieces = (label + value).splitlines() or [""]
    run = value_node.getparent()
    if run.tag != "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r":
        value_node.text = "；".join(piece for piece in pieces if piece)
        return
    for node in list(run):
        if node.tag == W_T and node is not value_node:
            node.text = ""
    value_node.text = pieces[0]
    insertion_index = run.index(value_node) + 1
    for piece in pieces[1:]:
        run.insert(insertion_index, OxmlElement("w:br"))
        insertion_index += 1
        text_node = OxmlElement("w:t")
        text_node.text = piece
        run.insert(insertion_index, text_node)
        insertion_index += 1


def _fill_cover_metadata(document, template_type: str, metadata: dict) -> None:
    """Project selected job metadata into existing validated template cells."""
    if template_type not in ("1v1", "class"):
        raise SlotRoutingError("TEMPLATE_COVER_METADATA_UNRESOLVED",
                               "unsupported template type: %s" % template_type)
    if not document.tables:
        raise SlotRoutingError("TEMPLATE_COVER_METADATA_UNRESOLVED",
                               "template has no cover table")
    table = document.tables[0]
    required_rows = 2
    required_columns = 4 if template_type == "1v1" else 3
    if len(table.rows) < required_rows or len(table.columns) < required_columns:
        raise SlotRoutingError("TEMPLATE_COVER_METADATA_UNRESOLVED",
                               "template cover table dimensions do not match %s" % template_type)

    if template_type == "1v1":
        # The one-to-one cover has explicit subject, grade, topic, and course
        # type cells. Labels remain in their original runs.
        coordinates = {
            "subject": (0, 0), "grade": (0, 2), "topic": (1, 1),
            "handout_type": (1, 3), "objectives": (2, 1),
            "difficulty": (3, 1),
        }
        values = {key: metadata.get(key, "") for key in coordinates}
        values["difficulty"] = metadata.get("difficulties", metadata.get("difficulty", ""))
    else:
        # The class cover has no separate course-type cell. Keep all selected
        # information visible in its existing class-topic value cell.
        topic = str(metadata.get("topic") or "").strip()
        handout_type = str(metadata.get("handout_type") or "").strip()
        topic_value = topic
        if handout_type:
            topic_value = (topic + "（" + handout_type + "）") if topic else handout_type
        coordinates = {
            "grade": (0, 0), "subject": (0, 2), "topic": (1, 1),
            # The frozen class template contains example text from a math
            # lesson in these fields. No selected-job metadata supplies them,
            # so blank the stale defaults instead of shipping false content.
            "objectives": (2, 1), "difficulty": (3, 1),
        }
        values = {"grade": metadata.get("grade", ""),
                  "subject": metadata.get("subject", ""), "topic": topic_value,
                  "objectives": metadata.get("objectives", ""),
                  "difficulty": metadata.get("difficulties", metadata.get("difficulty", ""))}

    for key, (row, column) in coordinates.items():
        try:
            cell = table.cell(row, column)
        except IndexError as exc:
            raise SlotRoutingError("TEMPLATE_COVER_METADATA_UNRESOLVED",
                                   "cover cell %s is missing for %s" % (key, template_type)) from exc
        _set_cover_cell_value(cell, values[key])


def _find_anchor_paragraphs(document, plan: SlotRoutingPlan) -> dict[str, object]:
    anchors = dict(zip(SLOT_ORDER, plan.template_anchors))
    matches: dict[str, list[object]] = {slot: [] for slot in SLOT_ORDER}
    body = document.element.body
    # Keep the element objects themselves alive in this set. Storing only
    # hash(cell) lets lxml release a proxy and reuse its address while walking
    # merged-cell aliases, which can make distinct cells collide and hide all
    # three anchors.
    seen_cells = set()
    for cell in body.iter(W_TC):
        # Merged cells may be surfaced repeatedly by high-level wrappers; only
        # one physical w:tc in the package is an insertion target.
        if cell in seen_cells:
            continue
        seen_cells.add(cell)
        for paragraph in cell.findall(W_P):
            text = _paragraph_text(paragraph)
            for slot, anchor in anchors.items():
                if text == anchor:
                    matches[slot].append(paragraph)
    missing_or_ambiguous = {slot: len(items) for slot, items in matches.items() if len(items) != 1}
    if missing_or_ambiguous:
        raise SlotRoutingError(
            "TEMPLATE_SLOT_ANCHOR_UNRESOLVED",
            "template %s slot anchor counts are not unique: %s" %
            (plan.template_type, missing_or_ambiguous),
        )
    return {slot: items[0] for slot, items in matches.items()}


def render_slots(
    source_doc: str,
    plan: SlotRoutingPlan,
    output_path: str,
    *,
    cover_metadata: dict | None = None,
    render_minimal_fn: Callable = None,
) -> SlotRenderResult:
    """Use the frozen importer, then place each slot stream at its template anchor."""
    if render_minimal_fn is None:
        from renderer_xml_minimal import render_minimal
        render_minimal_fn = render_minimal
    output = Path(output_path).resolve()
    if output.exists():
        raise FileExistsError("slot composer requires a fresh staging output")
    blocks_by_slot = {slot: tuple(plan.slots[slot]) for slot in SLOT_ORDER}
    flat_blocks: list[BlockSpan] = [span for slot in SLOT_ORDER for span in blocks_by_slot[slot]]
    total = sum(len(items) for items in blocks_by_slot.values())
    if not total or total != len(plan.block_records):
        raise SlotRoutingError("SLOT_ROUTING_DUPLICATE_OR_MISSING_BLOCK",
                               "slot streams do not cover the complete physical source sequence")
    ids = [span.start for span in flat_blocks]
    if len(ids) != len(set(ids)):
        raise SlotRoutingError("SLOT_ROUTING_DUPLICATE_OR_MISSING_BLOCK",
                               "slot streams contain duplicate physical source blocks")

    rendered = render_minimal_fn(source_doc, str(plan.template_path), flat_blocks,
                                 str(output), plan.target)
    try:
        document = Document(str(output))
        if cover_metadata is not None:
            _fill_cover_metadata(document, plan.template_type, cover_metadata)
        anchors = _find_anchor_paragraphs(document, plan)
        for slot in plan.omitted_slots:
            anchor = anchors[slot]
            parent = anchor.getparent()
            if parent is None:
                raise SlotRoutingError("TEMPLATE_SLOT_ANCHOR_UNRESOLVED",
                                       "omitted template slot has no parent: %s" % slot)
            parent.remove(anchor)
        training_only_label = None
        if getattr(plan, "knowledge_point_status", "") == "NO_KNOWLEDGE_POINT":
            immediate_anchor = anchors["immediate"]
            cell = immediate_anchor.getparent()
            if cell is None:
                raise SlotRoutingError("TEMPLATE_SLOT_ANCHOR_UNRESOLVED",
                                       "training slot anchor has no teaching cell")
            training_only_label = _compact_training_only_template(cell, immediate_anchor)
        body = document.element.body
        insert_at = plan.target.body_child_index
        sectpr_index = next((i for i, child in enumerate(body) if child.tag == W_SECTPR), len(body))
        if insert_at < 0 or insert_at + total > sectpr_index:
            raise SlotRoutingError("TEMPLATE_SLOT_PAYLOAD_UNRESOLVED",
                                   "rendered body tail does not match the slot plan")
        payloads = list(body)[insert_at:insert_at + total]
        if any(element.tag not in (W_P, W_TBL) for element in payloads):
            raise SlotRoutingError("TEMPLATE_SLOT_PAYLOAD_UNRESOLVED",
                                   "renderer tail contains a non-paragraph/table block")
        offsets: dict[str, list[object]] = {}
        cursor = 0
        for slot in SLOT_ORDER:
            count = len(blocks_by_slot[slot])
            offsets[slot] = payloads[cursor:cursor + count]
            cursor += count
        if cursor != len(payloads):
            raise SlotRoutingError("TEMPLATE_SLOT_PAYLOAD_UNRESOLVED",
                                   "renderer imported a different number of physical blocks")

        for element in payloads:
            body.remove(element)
        for slot in SLOT_ORDER:
            if slot in plan.omitted_slots:
                continue
            anchor = anchors[slot]
            # The 1v1 template shares the class template's printed knowledge
            # heading. Keep the frozen template file intact, but project the
            # user-approved template-specific label into this output copy.
            label = training_only_label if slot == "immediate" and training_only_label else plan.slot_labels[slot]
            _set_paragraph_text(anchor, label)
            for element in offsets[slot]:
                anchor.addnext(element)
                anchor = element

        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".slot-composer-", suffix=".docx",
                                         dir=str(output.parent))
        os.close(fd)
        try:
            document.save(temp_name)
            package_report = validate_package(temp_name)
            if not package_report.get("valid"):
                raise SlotRoutingError("PACKAGE_VALIDATION_FAILED",
                                       "; ".join(package_report.get("errors", [])[:5]))
            os.replace(temp_name, output)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return SlotRenderResult(
            output_path=str(output),
            inserted_nodes=total,
            slot_nodes={slot: len(offsets[slot]) for slot in SLOT_ORDER},
            resource_report=rendered.resource_report,
            package_report=package_report,
        )
    except Exception:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        raise

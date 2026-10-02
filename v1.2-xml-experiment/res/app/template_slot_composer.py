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
    value_node.text = label + value


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
            "handout_type": (1, 3),
        }
        values = {key: metadata.get(key, "") for key in coordinates}
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
                  "subject": metadata.get("subject", ""), "topic": topic_value}
        values.update({"objectives": "", "difficulty": ""})

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
            anchor = anchors[slot]
            # The 1v1 template shares the class template's printed knowledge
            # heading. Keep the frozen template file intact, but project the
            # user-approved template-specific label into this output copy.
            _set_paragraph_text(anchor, plan.slot_labels[slot])
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

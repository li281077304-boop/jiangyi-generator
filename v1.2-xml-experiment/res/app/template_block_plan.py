# -*- coding: utf-8 -*-
"""C-Line's explicit A-Line-to-B-Line single-stream placement plan.

The supported C0 target is one ``main_content`` stream inserted at a structural
body-child position in the immutable B4-validated template. Semantic units and
their relationships remain in the plan; overlapping unit spans contribute to
one ordered physical-block list so source content is never copied twice.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from docx import Document

from renderer_xml_minimal import BlockSpan, TemplateTarget
from semantic_facade import REPO_ROOT, SemanticSnapshot, analyze_source


TEMPLATES = {
    "1v1": {
        "relative_path": Path("v1.1-stable/res/app/2025+1v1讲义模板(2).docx"),
        "sha256": "1318fceabaa957b12e371310902fd81a0db08be09cee2121f6cd2606d8fd6a1a",
    },
    "class": {
        "relative_path": Path("v1.1-stable/res/app/2025班课模板.docx"),
        "sha256": "f51046d841699645b1b49f49f481c559e8502b98589d20b0c7e97cf2f7ba8f13",
    },
}
SLOT_ID = "main_content"
W_SECTPR = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr"


class PlanUnsupported(ValueError):
    """A source or template cannot be represented by the C0 single-slot plan."""


@dataclass(frozen=True)
class TemplateBlockPlan:
    source_path: Path
    source_sha256: str
    template_type: str
    template_path: Path
    template_sha256: str
    target: TemplateTarget
    units: tuple[dict[str, Any], ...]
    blocks: tuple[BlockSpan, ...]
    block_records: tuple[dict[str, Any], ...]
    structural_gap_count: int


def resolve_template(template_type: str) -> tuple[Path, str]:
    spec = TEMPLATES.get(template_type)
    if spec is None:
        raise PlanUnsupported("unsupported template type: %s" % template_type)
    path = (REPO_ROOT / spec["relative_path"]).resolve()
    if not path.is_file():
        raise PlanUnsupported("validated template is missing: %s" % path)
    digest = sha256(path.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        raise PlanUnsupported("validated template identity changed: %s" % path)
    return path, digest


def _top_level_seq(node_id: str) -> int | None:
    root = str(node_id).split(".", 1)[0]
    if not root.startswith("b") or not root[1:].isdigit():
        return None
    return int(root[1:])


def _is_contentful(block: Any) -> bool:
    return bool(
        block.kind == "table"
        or (block.text or "").strip()
        or block.images
        or block.oles
        or block.math_count
        or block.textbox_texts
    )


def _full_units(snapshot: SemanticSnapshot) -> list[dict[str, Any]]:
    count = len(snapshot.document.blocks)
    if not count:
        raise PlanUnsupported("source has no main-story blocks")
    return [{
        "id": "full_document",
        "role": "body",
        "parent": None,
        "bind_to": None,
        "spans": [["b0", "b%d" % (count - 1)]],
        "evidence": "full mode explicitly retains the complete source sequence",
    }]


def build_template_block_plan(
    source_path: str | Path,
    template_type: str,
    *,
    split_mode: str = "smart",
) -> TemplateBlockPlan:
    """Project real A-Line units to ordered, unique, atomic top-level blocks.

    A table or a cell-paragraph endpoint expands to the owning top-level table
    because the frozen renderer only supports atomic top-level table payloads.
    Every uncovered contentful source block fails closed. Uncovered empty
    structural paragraphs are retained once in source order as separators.
    """
    source = Path(source_path).resolve()
    if not source.is_file():
        raise PlanUnsupported("source DOCX is missing: %s" % source)
    template, template_digest = resolve_template(template_type)
    snapshot = analyze_source(source)
    blocks = snapshot.document.blocks
    if split_mode == "smart":
        units = snapshot.units
    elif split_mode == "full":
        units = _full_units(snapshot)
    else:
        raise PlanUnsupported("unsupported split mode: %s" % split_mode)
    if not units:
        raise PlanUnsupported("A-Line returned no semantic units")

    contributors: dict[int, list[str]] = {i: [] for i in range(len(blocks))}
    planned_units: list[dict[str, Any]] = []
    for unit in units:
        unit_id = str(unit.get("id") or "")
        spans = unit.get("spans")
        if not unit_id or not isinstance(spans, list) or not spans:
            raise PlanUnsupported("semantic unit lacks an ID or source spans")
        projected: set[int] = set()
        span_records = []
        for pair in spans:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise PlanUnsupported("malformed span in semantic unit %s" % unit_id)
            start, end = str(pair[0]), str(pair[1])
            if snapshot.node_index.resolve_ref(start) is None or snapshot.node_index.resolve_ref(end) is None:
                raise PlanUnsupported("unresolved semantic span %s..%s" % (start, end))
            start_order = snapshot.node_index.order_of(start)
            end_order = snapshot.node_index.order_of(end)
            start_seq, end_seq = _top_level_seq(start), _top_level_seq(end)
            if (start_order is None or end_order is None or start_order > end_order
                    or start_seq is None or end_seq is None or start_seq > end_seq
                    or end_seq >= len(blocks)):
                raise PlanUnsupported("reversed or unprojectable span %s..%s" % (start, end))
            for seq in range(start_seq, end_seq + 1):
                if blocks[seq].seq != seq or blocks[seq].kind not in ("paragraph", "table"):
                    raise PlanUnsupported("unknown or misordered source block b%d" % seq)
                projected.add(seq)
            span_records.append({
                "source_ids": [start, end],
                "node_order": [start_order, end_order],
                "projected_top_level": [start_seq, end_seq],
            })
        if not projected:
            raise PlanUnsupported("semantic unit has no projectable source blocks: %s" % unit_id)
        for seq in projected:
            contributors[seq].append(unit_id)
        planned_units.append({
            "unit_id": unit_id,
            "role": str(unit.get("role") or ""),
            "level": unit.get("level"),
            "parent": unit.get("parent"),
            "bind_to": unit.get("bind_to"),
            "evidence": unit.get("evidence"),
            "spans": span_records,
            "projected_block_ids": ["b%d" % i for i in sorted(projected)],
            "destination_slot": SLOT_ID,
        })

    structural_gaps = 0
    for seq, block in enumerate(blocks):
        if contributors[seq]:
            continue
        if _is_contentful(block):
            raise PlanUnsupported(
                "A-Line spans leave source content unassigned at b%d" % seq
            )
        # Retain empty paragraphs once. Their numbering/page structure can be
        # meaningful even though they are not semantic content units.
        contributors[seq].append("__structural_empty_gap__")
        structural_gaps += 1

    # Canonical source-order union. Each physical source block is emitted once,
    # including table blocks selected through cell-level semantic spans.
    block_records = tuple({
        "block_id": "b%d" % seq,
        "source_index": seq,
        "kind": block.kind,
        "unit_contributors": tuple(contributors[seq]),
    } for seq, block in enumerate(blocks))
    renderer_blocks = tuple(BlockSpan(item["block_id"], item["block_id"])
                            for item in block_records)

    template_body = Document(str(template)).element.body
    section_tail = next((i for i, child in enumerate(template_body)
                         if child.tag == W_SECTPR), len(template_body))
    if not any(child.tag.endswith("}tbl") for child in template_body[:section_tail]):
        raise PlanUnsupported("validated template has no table before section properties")
    target = TemplateTarget(section_tail)
    return TemplateBlockPlan(
        source_path=source,
        source_sha256=snapshot.source_sha256,
        template_type=template_type,
        template_path=template,
        template_sha256=template_digest,
        target=target,
        units=tuple(planned_units),
        blocks=renderer_blocks,
        block_records=block_records,
        structural_gap_count=structural_gaps,
    )

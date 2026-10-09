"""Independent-source XML routing with ordered, conservative degradation.

No pair alignment or peer-source text is consumed here. Every emitted plan
is still rendered and validated by the existing composer/product gates.
"""
import hashlib
from pathlib import Path

from docx import Document
from semantic_facade import SemanticSnapshot
from struct_doc import read_struct_doc_bytes, W_P, W_TBL
from struct_nodes import NodeIndex
from slot_router import (SlotRoutingError, analyze_source, build_slot_routing_plan,
                         _heading_route, _make_units, _is_explicit_section_heading)


def structural_snapshot(source):
    source = Path(source)
    payload = source.read_bytes()
    document = read_struct_doc_bytes(payload, name=source.name)
    total = len(document.blocks)
    if not total:
        raise SlotRoutingError('EMPTY_SOURCE_BODY', 'source has no main-story content')
    units = [dict(id='preserved-body', role='body', parent=None,
                  spans=[['b0', 'b%d' % (total - 1)]])]
    return SemanticSnapshot(hashlib.sha256(payload).hexdigest(), source.name,
                            document, NodeIndex(document), units)


def heading_projection(source, snapshot, template_type, *, navigation):
    doc = Document(source)
    nodes = [node for node in doc.element.body if node.tag in (W_P, W_TBL)]
    if len(nodes) != len(snapshot.document.blocks):
        raise SlotRoutingError('STRUCTURAL_INDEX_MISMATCH', 'body index cannot be proven')
    headings = []
    for seq, node in enumerate(nodes):
        if node.tag != W_P:
            continue
        if navigation:
            style_ids = node.xpath('./w:pPr/w:pStyle/@w:val')
            outlined = node.xpath('./w:pPr/w:outlineLvl/@w:val')
            styled = any(value.lower().startswith(('heading', '标题')) for value in style_ids)
            if not styled and not any(value.isdigit() and int(value) < 9 for value in outlined):
                continue
        text = snapshot.node_index.text_of('b%d' % seq)
        if not _is_explicit_section_heading(text, template_type):
            continue
        destination = _heading_route(text, template_type)
        if destination == 'answer_area':
            raise SlotRoutingError('ANSWER_OWNERSHIP_UNRESOLVED', 'global answers must stay in source order')
        if destination in ('knowledge', 'immediate', 'final'):
            headings.append((seq, destination))
    if not headings:
        raise SlotRoutingError('NO_RELIABLE_TEACHING_HEADINGS', 'no explicit teaching-slot boundary')
    # No block inside a table is examined as a standalone routing boundary.
    projection, current = {}, 'knowledge'
    boundaries = dict(headings)
    for seq in range(len(nodes)):
        current = boundaries.get(seq, current)
        projection[seq] = current
    # The existing canonical projection tolerates broad A-Line ranges. This
    # independent route deliberately refuses to split any established group.
    for unit in _make_units(snapshot):
        if unit.role == 'section' and snapshot.document.blocks[unit.start_seq].kind == 'table':
            destination = _heading_route(unit.text, template_type)
            if destination in ('knowledge', 'immediate', 'final') and destination != projection[unit.start_seq]:
                raise SlotRoutingError('TABLE_BOUNDARY_UNRESOLVED', unit.unit_id)
        if unit.role in ('question_group', 'answer', 'analysis', 'shared_material'):
            if len({projection[seq] for seq in unit.seqs}) > 1:
                raise SlotRoutingError('TEACHING_BOUNDARY_CROSSES_GROUP', unit.unit_id)
    return projection


def build_degraded_plan(source, template_type, *, snapshot=None, image_role_evidence=None,
                        preserve_only=False, navigation_only=False):
    attempts = []
    if snapshot is None:
        try:
            snapshot = analyze_source(source)
        except Exception as exc:
            attempts.append(dict(tier='SEMANTIC_ANALYSIS', status='UNAVAILABLE',
                                 reason_code='SEMANTIC_ANALYSIS_FAILED', detail=str(exc)))
            snapshot = structural_snapshot(source)
    for tier in ('NAVIGATION', 'SEMANTIC', 'RULES', 'PARTITION', 'PRESERVATION'):
        if navigation_only and tier != 'NAVIGATION':
            continue
        if preserve_only and tier != 'PRESERVATION':
            continue
        try:
            if tier in ('NAVIGATION', 'RULES'):
                projection = heading_projection(source, snapshot, template_type,
                                                navigation=tier == 'NAVIGATION')
                plan = build_slot_routing_plan(source, template_type, snapshot=snapshot,
                                              canonical_projection_routes=projection,
                                              image_role_evidence=image_role_evidence)
            elif tier == 'SEMANTIC':
                plan = build_slot_routing_plan(source, template_type, snapshot=snapshot,
                                              image_role_evidence=image_role_evidence)
                if plan.training_split_strategy.endswith('_DEGRADED'):
                    raise SlotRoutingError('SLOT_ROUTING_AMBIGUOUS', 'degraded question splitting requires preservation')
            elif tier == 'PARTITION':
                from exercise_partition import partition_exercises
                plan, partition = partition_exercises(Path(source), template_type, snapshot)
            else:
                # Preserve the original complete body order when semantic
                # ownership is uncertain; do not carry uncertain deletion or
                # knowledge/image classification into this last XML attempt.
                plan = build_slot_routing_plan(source, template_type, split_mode='full',
                                              snapshot=structural_snapshot(source))
            attempts.append(dict(tier=tier, status='SELECTED'))
            return plan, dict(selected_tier=tier, attempts=attempts,
                              partition=partition if tier == 'PARTITION' else None,
                              pair_alignment='NOT_REQUIRED_NOT_VERIFIED',
                              source_sha256=plan.source_sha256)
        except SlotRoutingError as exc:
            attempts.append(dict(tier=tier, status='DEGRADED', reason_code=exc.reason_code,
                                 detail=exc.detail))
    raise SlotRoutingError('XML_PRESERVATION_UNAVAILABLE', str(attempts))

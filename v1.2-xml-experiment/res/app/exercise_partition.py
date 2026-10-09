"""Whole-question/connected-material 70:30 routing, without peer-source alignment."""
from dataclasses import replace
import re

from slot_router import (SLOT_ORDER, SLOT_LABELS, TEMPLATE_ANCHORS, SlotRoutingPlan,
                         SlotRoutingError, _clean, _heading_route, _make_units,
                         _cover_metadata_sequences)
from template_block_plan import resolve_template
from renderer_xml_minimal import BlockSpan, TemplateTarget
from struct_doc import W_SECTPR
from docx import Document

PASSAGE = re.compile(r'^(?:Passage|Text|阅读材料|阅读理解|完形填空)\s*[A-Z\d一二三四五六七八九十]+\s*$', re.I)
QUESTION = re.compile(r'^\s*(?:第\s*)?(\d{1,3})\s*[.．、)）]\s*\S')
DECIMAL = re.compile(r'^\s*\d+\.\d+(?:\s*(?:V|A|m|cm|秒|伏|安)|\s*$)', re.I)
KNOWLEDGE_FAMILY = re.compile(r'^(?:基础|重难|考情|知识|方法|技巧)[·・]')
PRACTICE_FAMILY = re.compile(r'^(?:拔高|训练|练习|真题|进阶|能力|综合|素养|优题精练)[·・]')
PRACTICE_TITLE = re.compile(r'^(?:基础演练|能力进阶|分层集训|综合训练|综合练习|专项训练|巩固训练|习题|练习题)\s*$')


def partition_exercises(source, template_type, snapshot):
    """Return a complete physical partition; uncertain connected units stay whole."""
    blocks = snapshot.document.blocks
    units = _make_units(snapshot)
    cover = set(_cover_metadata_sequences(snapshot))
    contexts, heads, starts = {}, {}, []
    context = 'unknown'
    in_passage = False
    in_answers = False
    for i, block in enumerate(blocks):
        text = block.text.strip()
        cleaned = _clean(text)
        if block.kind == 'paragraph':
            intent = _heading_route(text, template_type)
            # Inline 【答案】/【解析】 belongs to the preceding question, not
            # a global answer section that suppresses every later question.
            if (len(text) <= 35 and intent == 'answer_area'
                    and re.fullmatch(r'(?:参考)?(?:答案|解析|答案解析|答案与解析)[：:]?',
                                     text.strip().strip('【】[]').strip())):
                in_answers = True
            # Long narrative sentences and incidental words are not boundaries.
            if len(text) <= 90 and KNOWLEDGE_FAMILY.match(text):
                context = 'knowledge'; in_passage = False; heads[i] = 'knowledge'
            elif len(text) <= 90 and (PRACTICE_FAMILY.match(text) or PRACTICE_TITLE.fullmatch(cleaned)):
                context = 'practice'; in_passage = False; in_answers = False; heads[i] = 'practice'
            elif len(text) <= 70 and intent in ('immediate', 'final'):
                context = intent; in_passage = False; in_answers = False; heads[i] = intent
            elif len(text) <= 70 and any(cleaned.startswith(t) for t in
                    ('知识精讲', '知识点', '知识讲解', '例题讲解', '题型讲解', '知识回顾')):
                context = 'knowledge'; in_passage = False; heads[i] = 'knowledge'
            if PASSAGE.fullmatch(text):
                if context != 'knowledge':
                    starts.append(i); in_passage = True; in_answers = False
            elif (context != 'knowledge' and not in_passage and not in_answers and QUESTION.match(text)
                  and not DECIMAL.fullmatch(text)
                  and not re.match(r'^\s*\d+[.．、)）]\s*(?:答案|解析|解答|解：)', text)):
                starts.append(i)
        contexts[i] = context
    starts = sorted(set(starts) - cover)
    if not starts:
        raise SlotRoutingError('NO_COMPLETE_EXERCISE_BOUNDARY', 'no independent question or passage boundary')

    # Material bindings produce closed intervals. No legal cut may cross them.
    materials = {u.unit_id: u for u in units if u.role == 'shared_material'}
    protected = []
    for key, material in materials.items():
        bound = [u for u in units if str(u.raw.get('bind_to') or '') == key]
        seqs = set(material.seqs)
        for u in bound:
            seqs.update(u.seqs)
        if bound and seqs:
            protected.append((min(seqs), max(seqs), key))
    material_starts = [lo for lo, hi, _ in protected if any(lo <= s <= hi for s in starts)
                       and contexts.get(lo) != 'knowledge']
    starts = [s for s in starts if not any(lo < s <= hi for lo, hi, _ in protected)] + material_starts
    # A leading shared text belongs with the first question even if its source
    # paragraph isn't itself numbered.
    starts = sorted(set(next((lo for lo, hi, _ in protected if lo < s <= hi), s)
                        for s in starts))
    if not starts:
        raise SlotRoutingError('NO_COMPLETE_EXERCISE_BOUNDARY', 'all boundaries absorbed by shared material')
    groups = []
    for n, start in enumerate(starts):
        end = starts[n + 1] - 1 if n + 1 < len(starts) else len(blocks) - 1
        # A section heading introducing the next exercise travels with it.
        if n + 1 < len(starts):
            next_start = starts[n + 1]
            preceding = [h for h in heads if start < h < next_start and heads[h] != 'knowledge']
            if preceding:
                end = max(preceding) - 1
        weight = sum(1 for seq in range(start, end + 1)
                     if blocks[seq].kind == 'paragraph' and QUESTION.match(blocks[seq].text)
                     and not re.match(r'^\s*\d+[.．、)）]\s*(?:答案|解析|解答)', blocks[seq].text))
        groups.append({'start': start, 'end': end, 'weight': max(1, weight),
                       'intent': contexts.get(start, 'unknown')})
    proven_knowledge = any(route == 'knowledge' for route in heads.values())
    example_start = None
    if not proven_knowledge:
        if len(groups) < 3:
            raise SlotRoutingError('INSUFFICIENT_COMPLETE_GROUPS_FOR_THREE_SLOTS',
                                   'one source example and two training slots require three whole groups')
        example_start = groups[0]['start']
    candidates = [g for g in groups if g['intent'] not in ('knowledge', 'immediate', 'final')
                  and g['start'] != example_start]
    fixed = {g['start']: g['intent'] for g in groups if g['intent'] in ('knowledge', 'immediate', 'final')}
    if example_start is not None:
        fixed[example_start] = 'knowledge'
    if len(candidates) >= 2:
        weights = [g['weight'] for g in candidates]
        total = sum(weights)
        cut = min(range(1, len(weights)), key=lambda k: (abs(sum(weights[:k]) - .7 * total), k))
        fixed.update({g['start']: 'immediate' if n < cut else 'final' for n, g in enumerate(candidates)})
    elif candidates:
        fixed[candidates[0]['start']] = 'immediate'
    # Preamble only constitutes knowledge when it contains an actual knowledge
    # section. Otherwise it follows the first exercise, without inventing text.
    current = 'knowledge'
    routes = {}
    for seq in range(len(blocks)):
        if seq in fixed:
            current = fixed[seq]
        if seq in heads and heads[seq] in ('knowledge', 'immediate', 'final'):
            current = heads[seq]
        routes[seq] = current
    # Move each introducing practice heading with its following complete group.
    for g in groups:
        previous_end = max((p['end'] for p in groups if p['end'] < g['start']), default=-1)
        heading = max((h for h in heads if previous_end < h < g['start']
                       and heads[h] == 'practice'), default=None)
        if heading is not None:
            for seq in range(heading, g['start']):
                routes[seq] = fixed[g['start']]
    for lo, hi, key in protected:
        if len({routes[s] for s in range(lo, hi + 1) if s not in cover}) > 1:
            raise SlotRoutingError('CONNECTED_COMPONENT_CROSSES_EXPLICIT_SECTION', key)
    template, digest = resolve_template(template_type)
    body = Document(template).element.body
    tail = next((i for i, node in enumerate(body) if node.tag == W_SECTPR), len(body))
    slot_blocks = {slot: tuple(BlockSpan('b%d' % s, 'b%d' % s) for s in range(len(blocks))
                              if s not in cover and routes[s] == slot) for slot in SLOT_ORDER}
    signatures = tuple((int(QUESTION.match(blocks[g['start']].text).group(1)), fixed[g['start']])
                       for g in groups if QUESTION.match(blocks[g['start']].text))
    plan = SlotRoutingPlan(source_path=source, source_sha256=snapshot.source_sha256,
        template_type=template_type, template_path=template, template_sha256=digest,
        target=TemplateTarget(tail), slots=slot_blocks, slot_labels=dict(SLOT_LABELS[template_type]),
        template_anchors=TEMPLATE_ANCHORS[template_type],
        block_records=tuple({'block_id':'b%d'%s, 'source_index':s, 'kind':b.kind,
                             'destination_slot':None if s in cover else routes[s],
                             'exclusion_reason':'COVER_METADATA_PROJECTED_TO_TEMPLATE_COVER' if s in cover else None}
                            for s,b in enumerate(blocks)),
        units=tuple({'unit_id':u.unit_id,'role':u.role,'parent':u.raw.get('parent'),
                     'bind_to':u.raw.get('bind_to'),'source_block_ids':tuple('b%d'%s for s in sorted(u.seqs))}
                    for u in units),
        explicit_final_heading=any(v=='final' for v in heads.values()),
        knowledge_point_status='KNOWLEDGE_POINT_PRESENT' if proven_knowledge else 'NO_KNOWLEDGE_POINT',
        omitted_slots=(),
        cover_metadata_blocks=tuple('b%d'%s for s in sorted(cover)),
        training_split_strategy='WHOLE_COMPONENT_70_30', training_question_routes=signatures)
    evidence={'selected_tier':'RULES','method':'WHOLE_COMPONENT_70_30','groups':groups,
              'group_routes':fixed,'protected_components':protected,
              'pair_alignment':'NOT_REQUIRED_NOT_VERIFIED','source_sha256':snapshot.source_sha256,
              'knowledge_content_mode':'SOURCE_KNOWLEDGE' if proven_knowledge else 'SOURCE_EXAMPLE',
              'source_example_group':groups[0] if example_start is not None else None}
    return plan, evidence

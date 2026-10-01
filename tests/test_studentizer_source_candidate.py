"""Packet shape/pending authority checks; real content review is separate."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / 'docs/v2/integration/fixtures/c3-r5-source-candidates'


def packet(sid):
    return json.loads((PACKETS / (sid+'-source-candidate.json')).read_text(encoding='utf-8'))


def test_every_packet_is_pending_and_not_a_production_provider():
    for sid in ('X008', 'X014', 'X018'):
        p = packet(sid)
        assert p['approved'] is False and p['production_provider'] is False
        assert p['chief_verdict'] == 'PENDING'
        assert [r['index'] for r in p['body']] == list(range(len(p['body'])))
        assert all(len(r['sha256']) == 64 and r['rationale'] for r in p['body'])


def test_physics_full_source_manual_ranges_preserve_all_prompts_and_boundaries():
    p = packet('X008')
    assert p['full_content_review'] and p['visually_reviewed_pages'] == list(range(1, 15))
    assert len(p['questions']) == 34 and len(p['frozen_units']) == 114
    assert len(p['proposed_removed_indices']) == 118 and len(p['expected_retained_body_sha256']) == 146
    assert [q['source_question_number'] for q in p['questions']] == list(range(1, 35))
    assert [q['source_question_number'] for q in p['questions'] if not q['frozen_qg_ids']] == [3,4,10,16,24]
    for q in p['questions']:
        assert all(p['body'][i]['decision'] == 'RETAIN' for i in range(q['prompt_start'], q['prompt_end']+1))
        assert all(p['body'][i]['owner'] == q['id'] and p['body'][i]['decision'] == 'PROPOSE_REMOVE'
                   for i in range(q['answer_start'], q['answer_end']+1))
    assert all(p['body'][i]['decision'] == 'RETAIN' for i in (4,8,57,262,263))


def test_unreviewed_math_and_chemistry_cannot_have_expected_gold_or_removals():
    for sid, count in [('X014',656), ('X018',399)]:
        p = packet(sid)
        assert not p['full_content_review'] and p['visually_reviewed_pages'] == [1,2]
        assert len(p['body']) == count and not p['questions']
        assert all(r['decision'] == 'UNRESOLVED' for r in p['body'])
        assert 'candidate_docx_path' not in p and 'proposed_removed_indices' not in p


def test_physics_all_four_ole_are_retained_in_q23_and_q11_is_plain_text():
    p = packet('X008')
    objects = [(r, n) for r in p['body'] for n in r['nontext_and_boundary_structures']
               if n['tag'] == 'OLEObject']
    assert len(objects) == 4
    assert all(r['index'] == 164 and r['owner'] == 'candidate-question-23'
               and r['decision'] == n['decision'] == 'RETAIN' for r, n in objects)
    assert all(p['body'][i]['decision'] == 'PROPOSE_REMOVE'
               and not p['body'][i]['nontext_and_boundary_structures'] for i in (75,76,77))
    assert 'Answer-OLE deletion is not exercised by this source' in p['unresolved']
    assert p['approved'] is False and p['production_provider'] is False

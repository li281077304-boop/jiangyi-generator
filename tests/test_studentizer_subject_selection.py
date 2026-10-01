"""Selection evidence is reproducible diagnostics, never content approval."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    return json.loads((ROOT/'docs/v2/integration/fixtures/c3-r8-subject-selection.json').read_text(encoding='utf-8'))


def test_selection_has_no_golden_authority_or_production_activation():
    e = evidence()
    assert len(e['corpus_hashes_verified']) == len(set(e['corpus_hashes_verified'])) == 27
    assert e['authority'] == 'CANDIDATE_ONLY' and e['performance'] == 'NOT_RUN'
    assert set(e['selected']) == {'X012','X023'}
    for row in e['selected'].values():
        assert not row['approved'] and not row['full_content_review'] and not row['production_provider']
        assert row['physical_question_total'] == row['complete_answer_ownership'] == 'NOT_ESTABLISHED'
        assert row['current_capability'] == 'BLOCKED'
        assert 'expected_document_sha256' not in row and 'removed_indices' not in row
        assert row['source_page_count_evidence']['source_unchanged']
        assert row['source_page_count_evidence']['source_sha256'].lower() == row['provenance']['source_sha256'] == row['source_sha256']


def test_frozen_spans_and_subject_blockers_remain_explicit():
    e = evidence()['selected']
    for sid,endpoints,complex_count,qgs,sections in [('X012',486,7,56,34),('X023',370,28,43,29)]:
        r = e[sid]
        assert r['validated_endpoint_count'] == endpoints and r['complex_endpoint_count'] == complex_count
        assert r['endpoint_missing'] == 0
        assert r['role_counts']['question_group'] == qgs and r['role_counts']['section'] == sections
        assert sum(2*len(u['spans']) for u in r['frozen_spans']) == endpoints
        assert all(len(u['spans']) == len(u['top_body_spans']) for u in r['frozen_spans'])
        assert r['marked_plain_count'] == 0
    assert e['X012']['marked_nontext_count'] == 95 and e['X012']['features']['oMath'] == 786
    assert len(e['X023']['dedicated_markers']) == 112 and e['X023']['marked_nontext_count'] == 0
    assert e['X023']['field_instructions'] == [' = 6 \\* GB3 ']
    assert e['X023']['features']['txbxContent'] == 0
    assert not any(role=='question_group' for row in e['X023']['dedicated_markers']
                   for chain in row['parent_chains'] for _,role in chain)

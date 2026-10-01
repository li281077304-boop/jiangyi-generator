"""Real approved-source contract refusal; no production provider or manual splice."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/studentizer_audit'))
from probe_approved_source import approved_ledger, probe

PACKET = ROOT / 'docs/v2/integration/fixtures/c3-r5-source-candidates/X008-source-candidate.json'
APPROVAL = ROOT / 'docs/v2/integration/C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md'


def test_approval_exactly_matches_all_34_physical_owners():
    packet = json.loads(PACKET.read_text(encoding='utf-8'))
    ledger = approved_ledger(APPROVAL, packet)
    assert len(ledger) == 34
    assert sum(b - a + 1 for _q, _s, _e, a, b in ledger) == 118


def test_approval_identity_mismatch_is_not_authority():
    packet = json.loads(PACKET.read_text(encoding='utf-8'))
    packet['source_sha256'] = '0' * 64
    with pytest.raises(AssertionError, match='approval identity mismatch'):
        approved_ledger(APPROVAL, packet)


def test_approval_coordinate_mismatch_is_not_authority():
    packet = json.loads(PACKET.read_text(encoding='utf-8'))
    packet['questions'][0]['answer_end'] += 1
    with pytest.raises(AssertionError, match='approval ledger mismatch'):
        approved_ledger(APPROVAL, packet)


def test_current_public_api_refuses_approved_x008_without_any_output(tmp_path):
    evidence = probe(PACKET, APPROVAL, tmp_path / 'student.docx')
    assert evidence['gate'] == 'STUDENTIZER_CAPABILITY_BLOCKED'
    assert evidence['result']['reason_code'] == 'STUDENTIZER_FIELD_SCOPE_UNSUPPORTED'
    assert evidence['first_rejected_structure']['tag'] == 'fldChar'
    assert evidence['first_rejected_structure']['physical_body_index'] == 3
    assert evidence['first_rejected_structure']['xml_path'] == '/w:document/w:body/w:p[4]/w:r[2]/w:fldChar'
    assert evidence['first_rejected_structure']['approved_decision'] == 'RETAIN'
    assert evidence['requested_remove_paragraphs'] == 118
    assert evidence['protected_source_children'] == 146
    assert evidence['request_owner_kind'] == 'physical_question'
    assert evidence['frozen_qg_ids_invented'] is False
    assert evidence['source_unchanged'] and evidence['expected_draft_unchanged']
    assert evidence['derived_output_exists'] is False
    assert evidence['derived_wps_uat'] == 'NOT_RUN_NO_STUDENTIZER_OUTPUT'
    assert evidence['performance_benchmark'] == 'NOT_RUN'
    assert evidence['production_provider_created'] is False

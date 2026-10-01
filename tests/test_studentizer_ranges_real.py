"""One exact independently approved real source; no production provider."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/studentizer_audit'))
from run_approved_range import transform


def test_approved_source_transforms_through_public_api(tmp_path):
    record = transform(ROOT/'docs/v2/integration/fixtures/c3-r5-source-candidates/X008-source-candidate.json',
                       ROOT/'docs/v2/integration/C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md',
                       tmp_path/'student.docx')
    assert record['result']['status'] == 'XML_PREPARED'
    assert record['after_root_matches_golden'] and record['non_document_package_parts_exact']
    assert record['retained_fingerprints_order_exact'] and record['package_members_order_exact']
    assert record['removed_paragraphs'] == 118 and record['retained_children'] == 146
    assert record['source_unchanged'] and record['golden_unchanged']
    assert record['production_provider_created'] is False
    packet = json.loads((ROOT/'docs/v2/integration/fixtures/c3-r5-source-candidates/X008-source-candidate.json').read_text(encoding='utf-8'))
    assert record['result']['output_sha256'] == packet['candidate_docx_sha256']

"""Standalone real-Golden UAT harness, not a production provider or splice."""
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import re
import sys
import zipfile

from lxml import etree

from probe_approved_source import approved_ledger, ROOT
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
from studentizer import prepare_student, element_sha256, TAG
from studentizer_ranges import ReviewedPhysicalBody, ReviewedAnswerRange, PhysicalRangeSemantics


def transform(packet_path, approval_path, output):
    packet = json.loads(Path(packet_path).read_text(encoding='utf-8'))
    ledger = approved_ledger(approval_path, packet)
    source = Path(packet['source_path'])
    before = source.read_bytes()
    expected = Path(packet['candidate_docx_path'])
    golden = expected.read_bytes()
    assert sha256(before).hexdigest() == packet['source_sha256']
    assert sha256(golden).hexdigest() == packet['candidate_docx_sha256']
    with zipfile.ZipFile(BytesIO(before)) as package:
        parts = {n: package.read(n) for n in package.namelist()}
        names = package.namelist()
    with zipfile.ZipFile(BytesIO(golden)) as package:
        golden_root = etree.fromstring(package.read('word/document.xml'))
    assert element_sha256(golden_root) == packet['candidate_expected_document_sha256']
    source_root = etree.fromstring(parts['word/document.xml'])
    # Acknowledgement derives from the independently approved exact source;
    # core revalidates and requires the identical post-transform dependencies.
    bookmark_names = {n.get(TAG('name')) for n in source_root.iter(TAG('bookmarkStart'))}
    targets = {n.get(TAG('anchor')) for n in source_root.iter(TAG('hyperlink')) if n.get(TAG('anchor'))}
    for n in source_root.iter(TAG('instrText')):
        text = n.text or ''
        m = re.search(r'\b(?:PAGEREF|REF)\s+("[^"]+"|[^\s\\]+)', text, re.I)
        if not m:
            m = re.search(r'\bHYPERLINK\s+\\l\s+("[^"]+"|[^\s\\]+)', text, re.I)
        if m:
            targets.add(m.group(1).strip('"'))
    missing = tuple(sorted(targets - bookmark_names))
    review_id = 'C3-X008-CHIEF-FULL'
    semantics = PhysicalRangeSemantics(
        packet['source_sha256'], review_id,
        tuple(ReviewedPhysicalBody(r['index'], r['sha256'],
                                  'REMOVE' if r['decision'] == 'PROPOSE_REMOVE' else 'RETAIN',
                                  r['rationale'], review_id, r['owner']) for r in packet['body']),
        tuple(ReviewedAnswerRange(q['id'], start, end, a, b,
                                 'Independently approved complete answer and explanation range', review_id)
              for q, (_number, start, end, a, b) in zip(packet['questions'], ledger)),
        packet['candidate_expected_document_sha256'], missing)
    result = prepare_student(source, semantics, output)
    assert source.read_bytes() == before and expected.read_bytes() == golden
    record = {'entrypoint': 'studentizer.prepare_student', 'contract': 'PhysicalRangeSemantics',
              'result': asdict(result), 'source_unchanged': True, 'golden_unchanged': True,
              'production_provider_created': False, 'performance_benchmark': 'NOT_RUN',
              'inherited_missing_bookmark_targets': missing}
    if result.status == 'XML_PREPARED':
        with zipfile.ZipFile(output) as generated:
            actual = {n: generated.read(n) for n in generated.namelist()}
            assert generated.namelist() == names
        after = etree.fromstring(actual['word/document.xml'])
        record['after_root_sha256'] = element_sha256(after)
        assert record['after_root_sha256'] == packet['candidate_expected_document_sha256']
        assert [element_sha256(n) for n in after.find(TAG('body'))] == packet['expected_retained_body_sha256']
        assert all(actual[n] == parts[n] for n in names if n != 'word/document.xml')
        record.update(after_root_matches_golden=True, retained_children=146,
                      retained_fingerprints_order_exact=True, non_document_package_parts_exact=True,
                      package_members_order_exact=True, removed_paragraphs=len(result.mutations))
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    record = transform(args.packet, args.approval, args.output)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'result'}, ensure_ascii=False))
    print(record['result']['status'], record['result']['reason_code'], record['result']['reason_detail'])

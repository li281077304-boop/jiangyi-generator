"""Verify an unapproved manual source packet; no production provider/output."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import sys
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
from semantic_facade import analyze_source
from studentizer import TAG, element_sha256


def verify(packet):
    assert packet['approved'] is False and packet['production_provider'] is False
    source = Path(packet['source_path']); data = source.read_bytes()
    assert sha256(data).hexdigest() == packet['source_sha256']
    snapshot = analyze_source(data)
    assert [row['unit'] for row in packet['frozen_units']] == snapshot.units
    with zipfile.ZipFile(BytesIO(data)) as package:
        parts = {info.filename: package.read(info.filename) for info in package.infolist()}
    assert {k: sha256(v).hexdigest() for k, v in parts.items()} == packet['package_part_sha256']
    root = etree.fromstring(parts['word/document.xml'], etree.XMLParser(resolve_entities=False, no_network=True))
    body = root.find(TAG('body')); children = list(body)
    records = packet['body']
    assert [r['index'] for r in records] == list(range(len(children)))
    mapping = {b.body_idx: 'b'+str(b.seq) for b in snapshot.document.blocks}
    for record, node in zip(records, children):
        assert record['sha256'] == element_sha256(node)
        assert record['physical_address'] == 'body[%d]' % record['index']
        assert record['structdoc_top_node'] == mapping.get(record['index'])
        assert record['rationale'] and record['review_state']
        assert record['decision'] in {'RETAIN', 'PROPOSE_REMOVE', 'UNRESOLVED'}
    complete = packet['full_content_review']
    assert set(packet['visually_reviewed_pages']).issubset(set(range(1, packet['source_pages']+1)))
    if complete:
        assert packet['visually_reviewed_pages'] == list(range(1, packet['source_pages']+1))
        assert all(r['decision'] != 'UNRESOLVED' for r in records)
        removed = set(packet['proposed_removed_indices'])
        assert removed == {r['index'] for r in records if r['decision'] == 'PROPOSE_REMOVE'}
        owned = set()
        for question in packet['questions']:
            a, b = question['answer_start'], question['answer_end']
            assert question['prompt_start'] <= question['prompt_end'] < a <= b
            assert question['owner_start_sha256'] == element_sha256(children[question['prompt_start']])
            for i in range(a, b+1):
                assert i not in owned and records[i]['owner'] == question['id']
                owned.add(i)
            assert all(records[i]['decision'] == 'RETAIN' for i in range(question['prompt_start'], question['prompt_end']+1))
        assert owned == removed
        retained = [element_sha256(n) for i, n in enumerate(children) if i not in removed]
        assert retained == packet['expected_retained_body_sha256']
        for i in sorted(removed, reverse=True):
            body.remove(children[i])
        assert element_sha256(root) == packet['candidate_expected_document_sha256']
        candidate = Path(packet['candidate_docx_path'])
        assert sha256(candidate.read_bytes()).hexdigest() == packet['candidate_docx_sha256']
        with zipfile.ZipFile(candidate) as generated:
            assert all(generated.read(k) == v for k, v in parts.items() if k != 'word/document.xml')
            check = etree.fromstring(generated.read('word/document.xml'))
        assert element_sha256(check) == packet['candidate_expected_document_sha256']
    else:
        assert not packet['questions'] and all(r['decision'] == 'UNRESOLVED' for r in records)
        assert 'candidate_expected_document_sha256' not in packet
    assert source.read_bytes() == data
    return {'sample_id': packet['sample_id'], 'inventory_valid': True,
            'full_content_review': complete, 'approved': False,
            'status': 'WORKER_CANDIDATE_CHIEF_PENDING' if complete else 'INCOMPLETE_FAIL_CLOSED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.packet.read_text(encoding='utf-8')))))

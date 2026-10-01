"""Standalone approved-Golden API probe; never a production evidence provider.

The approval ledger supplies physical ownership, which is deliberately NOT
renamed to frozen QG identity. The current public DTO is asked to represent the
whole reviewed removal request faithfully; a refusal must remain a refusal.
No manual splice, _plan call, source mutation or COM invocation is performed.
"""
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
from studentizer import (AnswerBinding, StudentizerSemantics, prepare_student,
                         element_sha256, TAG, FALLBACK)


def approved_ledger(approval, packet):
    """Verify explicit content authority and exact independently reviewed ranges."""
    text = Path(approval).read_text(encoding='utf-8')
    assert '**X008_GOLDEN_APPROVED**' in text
    assert 'chief_model = Codex GPT-6.1 Sol' in text
    for key in ('source_sha256', 'candidate_expected_document_sha256', 'candidate_docx_sha256'):
        assert packet[key] in text, 'approval identity mismatch: ' + key
    ranges = []
    for line in text.splitlines():
        m = re.match(r'^\| (\d+) \| [^|]+ \| (\d+)(?:–(\d+))? \| (\d+)–(\d+) \|', line)
        if m:
            q, start, end, a, b = m.groups()
            ranges.append((int(q), int(start), int(end or start), int(a), int(b)))
    actual = [(q['source_question_number'], q['prompt_start'], q['prompt_end'],
               q['answer_start'], q['answer_end']) for q in packet['questions']]
    assert ranges == actual and len(ranges) == 34, 'independent approval ledger mismatch'
    assert packet['approved'] is False and packet['production_provider'] is False
    return ranges


def probe(packet_path, approval_path, output_path):
    packet = json.loads(Path(packet_path).read_text(encoding='utf-8'))
    ledger = approved_ledger(approval_path, packet)
    source = Path(packet['source_path'])
    data = source.read_bytes()
    digest = sha256(data).hexdigest()
    assert digest == packet['source_sha256']
    expected_path = Path(packet['candidate_docx_path'])
    expected_data = expected_path.read_bytes()
    assert sha256(expected_data).hexdigest() == packet['candidate_docx_sha256']
    with zipfile.ZipFile(BytesIO(data)) as package:
        source_parts = {n: package.read(n) for n in package.namelist()}
    with zipfile.ZipFile(BytesIO(expected_data)) as package:
        expected_parts = {n: package.read(n) for n in package.namelist()}
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(source_parts['word/document.xml'], parser)
    expected_root = etree.fromstring(expected_parts['word/document.xml'], parser)
    assert element_sha256(expected_root) == packet['candidate_expected_document_sha256']
    assert source_parts.keys() == expected_parts.keys()
    assert all(source_parts[n] == expected_parts[n] for n in source_parts if n != 'word/document.xml')
    children = list(root.find(TAG('body')))
    assert [element_sha256(n) for n in children] == [r['sha256'] for r in packet['body']]
    remove = {i for _q, _s, _e, a, b in ledger for i in range(a, b + 1)}
    assert remove == set(packet['proposed_removed_indices']) and len(remove) == 118
    # This preserves the independently approved physical owner type; claiming
    # question_group here would invent authority for five missing frozen QGs.
    bindings = tuple(AnswerBinding('approved-physical-question-' + str(q),
                                  'physical_question', start, b, i,
                                  element_sha256(children[i]),
                                  'reviewed_question_answer', 'C3-X008-CHIEF-FULL')
                     for q, start, _end, a, b in ledger for i in range(a, b + 1))
    semantics = StudentizerSemantics(digest, bindings,
                                    tuple(i for i in range(len(children)) if i not in remove))
    output = Path(output_path)
    assert not output.exists() and output.resolve() != source.resolve()
    result = prepare_student(source, semantics, output)
    source_unchanged = source.read_bytes() == data
    expected_unchanged = expected_path.read_bytes() == expected_data
    assert source_unchanged and expected_unchanged
    evidence = {'entrypoint': 'studentizer.prepare_student',
                'source_sha256': digest, 'approved_expected_document_sha256': element_sha256(expected_root),
                'approved_expected_draft_sha256': sha256(expected_data).hexdigest(),
                'approved_ledger_questions': len(ledger), 'requested_remove_paragraphs': len(bindings),
                'protected_source_children': len(semantics.protected_indices),
                'request_owner_kind': 'physical_question', 'frozen_qg_ids_invented': False,
                'source_unchanged': source_unchanged, 'expected_draft_unchanged': expected_unchanged,
                'result': asdict(result), 'derived_output_exists': output.exists(),
                'performance_benchmark': 'NOT_RUN', 'derived_wps_uat': 'NOT_RUN_NO_STUDENTIZER_OUTPUT',
                'production_provider_created': False}
    if result.status == FALLBACK:
        assert not output.exists() and not result.mutations and result.output_path is None
        evidence['gate'] = 'STUDENTIZER_CAPABILITY_BLOCKED'
        evidence['after_root_comparison'] = 'NOT_RUN_NO_STUDENTIZER_OUTPUT'
        if result.reason_code in {'STUDENTIZER_FIELD_SCOPE_UNSUPPORTED', 'STUDENTIZER_BOOKMARK_SCOPE_UNSUPPORTED'}:
            first = next(n for n in root.find(TAG('body')).iter()
                         if isinstance(n.tag, str) and etree.QName(n).localname == result.reason_detail)
            top = first
            while top.getparent() is not root.find(TAG('body')):
                top = top.getparent()
            evidence['first_rejected_structure'] = {
                'tag': result.reason_detail, 'xml_path': root.getroottree().getpath(first),
                'physical_body_index': children.index(top),
                'approved_decision': packet['body'][children.index(top)]['decision']}
    else:
        with zipfile.ZipFile(output) as generated:
            actual = {n: generated.read(n) for n in generated.namelist()}
        evidence['after_root_comparison'] = element_sha256(etree.fromstring(actual['word/document.xml'], parser)) == element_sha256(expected_root)
        evidence['non_document_parts_unchanged'] = actual.keys() == source_parts.keys() and all(actual[n] == source_parts[n] for n in source_parts if n != 'word/document.xml')
        evidence['gate'] = 'XML_TRANSFORMED_REAL_APP_UAT_PENDING'
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    evidence = probe(args.packet, args.approval, args.output)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, ensure_ascii=False))

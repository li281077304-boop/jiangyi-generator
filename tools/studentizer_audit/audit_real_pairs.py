"""Read-only exact-structure pair audit; never creates deletion authority/Gold.

All addresses are direct main-body indices, not COM indices. Fingerprints are
full C14N subtrees. Matching summaries diagnose gaps, not answer ownership.
"""
from collections import Counter, defaultdict
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
from semantic_facade import analyze_source
from studentizer import TAG, element_sha256

MARKER = re.compile(r'【(?:答案|解析|详解|解答)】')


def expanded_fingerprint(node):
    """Exact expanded-name tree, ignoring xmlns declarations only, no fuzzy text."""
    def tree(n):
        return [n.tag, sorted(n.attrib.items()), n.text, n.tail, [tree(c) for c in n]]
    return sha256(json.dumps(tree(node), ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def source_identity(name):
    stem = Path(name).stem
    match = re.search(r'(?:[（(](原卷版|解析版|答案版)[）)]|(原卷版|解析版|答案版))$', stem)
    if not match:
        return None, None
    version = match[1] or match[2]
    return stem[:match.start()].strip(), 'student' if version == '原卷版' else 'teacher'


def describe(path, meta):
    data = path.read_bytes(); digest = sha256(data).hexdigest()
    with zipfile.ZipFile(BytesIO(data)) as package:
        parts = {i.filename: package.read(i.filename) for i in package.infolist()}
    root = etree.fromstring(parts['word/document.xml'], etree.XMLParser(resolve_entities=False, no_network=True))
    body = root.find(TAG('body')); nodes = list(body)
    rows = []
    for index, node in enumerate(nodes):
        text = ''.join(node.itertext())
        rows.append({'index': index, 'physical_address': 'body[%d]' % index,
                     'tag': etree.QName(node).localname, 'sha256': element_sha256(node),
                     'expanded_name_sha256': expanded_fingerprint(node),
                     'text_sha256': sha256(text.encode('utf-8')).hexdigest(),
                     'text_preview': text[:180], 'answer_marker_candidate': bool(MARKER.search(text)),
                     'has_nontext': any(etree.QName(n).localname in ('drawing', 'pict', 'object', 'oMath', 'txbxContent') for n in node.iter())})
    scope = defaultdict(list)
    for index, node in enumerate(nodes):
        for child in node.iter():
            local = etree.QName(child).localname
            if local == 'tbl':
                scope['STUDENTIZER_TABLE_SCOPE_UNSUPPORTED'].append(index)
            if local == 'txbxContent':
                scope['STUDENTIZER_TEXTBOX_SCOPE_UNSUPPORTED'].append(index)
            if local in ('bookmarkStart', 'bookmarkEnd', 'hyperlink'):
                scope['STUDENTIZER_BOOKMARK_SCOPE_UNSUPPORTED'].append(index)
            if local in ('fldChar', 'instrText', 'fldSimple'):
                scope['STUDENTIZER_FIELD_SCOPE_UNSUPPORTED'].append(index)
            if local in ('ins', 'del', 'moveFrom', 'moveTo', 'sdt', 'customXml', 'commentReference', 'footnoteReference', 'endnoteReference') or local.endswith('Change'):
                scope['STUDENTIZER_REVISION_SCOPE_UNSUPPORTED'].append(index)
    units = analyze_source(data).units
    features = Counter(etree.QName(n).localname for block in nodes for n in block.iter())
    manifest = {'sample_id': meta['sample_id'], 'subject': meta['subject'],
                'source_sha256': digest, 'manifest_sha_ok': digest == meta['source_sha256'],
                'body_count': len(nodes), 'body': rows, 'units': units,
                'scope_blockers': {key: sorted(set(values)) for key, values in scope.items()},
                'document_sha256': element_sha256(root),
                'features': {tag: features[tag] for tag in ('p', 'tbl', 'oMath', 'drawing', 'pict', 'OLEObject', 'txbxContent', 'numPr', 'bookmarkStart', 'fldChar')},
                'package_part_sha256': {name: sha256(value).hexdigest() for name, value in parts.items()},
                'authority': 'DIAGNOSTIC_ONLY_NOT_REVIEWED_GOLDEN'}
    return manifest, nodes


def exact_subsequence_count(teacher, student):
    """Count exact ordered embeddings, capped at 2; never select one mapping."""
    count = [1] + [0] * len(student)
    for fingerprint in teacher:
        for index in range(len(student), 0, -1):
            if fingerprint == student[index-1]:
                count[index] = min(2, count[index] + count[index-1])
    return count[-1]


def compare(teacher, student):
    th = [n['sha256'] for n in teacher['body']]
    sh = [n['sha256'] for n in student['body']]
    tc, sc = Counter(th), Counter(sh)
    tables_t = [n for n in teacher['body'] if n['tag'] == 'tbl']
    tables_s = [n for n in student['body'] if n['tag'] == 'tbl']
    same_tables = [n['sha256'] for n in tables_t] == [n['sha256'] for n in tables_s]
    same_expanded_tables = [n['expanded_name_sha256'] for n in tables_t] == [n['expanded_name_sha256'] for n in tables_s]
    answer_candidates = [n['index'] for n in teacher['body'] if n['answer_marker_candidate']]
    parts_t, parts_s = teacher['package_part_sha256'], student['package_part_sha256']
    common = set(parts_t) & set(parts_s)
    return {'teacher': teacher['sample_id'], 'student': student['sample_id'],
            'subject': teacher['subject'], 'teacher_body_count': len(th), 'student_body_count': len(sh),
            'exact_student_subsequence_embeddings_capped2': exact_subsequence_count(th, sh),
            'exact_expanded_name_student_subsequence_embeddings_capped2': exact_subsequence_count(
                [n['expanded_name_sha256'] for n in teacher['body']], [n['expanded_name_sha256'] for n in student['body']]),
            'student_blocks_absent_from_teacher': [n['index'] for n in student['body'] if n['sha256'] not in tc],
            'exact_common_multiset_blocks': sum((tc & sc).values()),
            'duplicate_teacher_fingerprints': sum(c > 1 for c in tc.values()),
            'teacher_table_count': len(tables_t), 'student_table_count': len(tables_s),
            'ordered_table_subtrees_byte_equivalent_c14n': same_tables,
            'ordered_table_subtrees_expanded_name_equal': same_expanded_tables,
            'table_hashes_teacher': [n['sha256'] for n in tables_t],
            'table_hashes_student': [n['sha256'] for n in tables_s],
            'answer_marker_candidate_indices': answer_candidates,
            'source_scope_blockers': teacher['scope_blockers'],
            'teacher_features': teacher['features'], 'student_features': student['features'],
            'teacher_semantic_roles': dict(Counter(u['role'] for u in teacher['units'])),
            'student_semantic_roles': dict(Counter(u['role'] for u in student['units'])),
            'student_marker_candidates': sum(n['answer_marker_candidate'] for n in student['body']),
            'shared_parts_differing': sorted(n for n in common if n != 'word/document.xml' and parts_t[n] != parts_s[n]),
            'parts_only_teacher': sorted(set(parts_t)-set(parts_s)),
            'parts_only_student': sorted(set(parts_s)-set(parts_t)),
            'selection': 'REJECTED_NO_COMPLETE_APPROVED_DELETION_ALIGNMENT',
            'authority': 'DIAGNOSTIC_ONLY_NO_DELETION_PLAN'}


def legacy_audit(runtime, corpus_meta, out):
    byhash = {m['source_sha256']: m for m in corpus_meta}
    rows = []
    for derived in sorted(runtime.rglob('derived-student-source.docx')):
        job_path = derived.parent.parent / 'job.json'
        record = json.loads(job_path.read_text(encoding='utf-8'))
        teacher = Path(record['teacher_source_path'])
        before_teacher, before_student = teacher.read_bytes(), derived.read_bytes()
        meta = byhash.get(sha256(before_teacher).hexdigest())
        if meta is None:
            continue
        tm, _ = describe(teacher, meta)
        sm, _ = describe(derived, dict(sample_id=meta['sample_id']+'-V09', subject=meta['subject'],
                                     source_sha256=sha256(before_student).hexdigest()))
        row = compare(tm, sm)
        row.update(job_id=record['job_id'], teacher_path=str(teacher), student_path=str(derived),
                   case=job_path.parent.parent.name, oracle_kind='V09_LEGACY_DERIVATIVE_NOT_REVIEWED_GOLD',
                   teacher_unchanged=teacher.read_bytes() == before_teacher,
                   student_unchanged=derived.read_bytes() == before_student)
        rows.append(row)
        (out / (meta['sample_id']+'-'+record['job_id']+'-legacy-diagnostic.json')).write_text(
            json.dumps(sm, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'legacy_pair_audit.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--legacy-runtime', type=Path)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((args.corpus / 'baseline_inputs.json').read_text(encoding='utf-8'))['samples']
    groups = defaultdict(list); manifests = {}; rows = []
    for sample in meta:
        path = args.corpus / sample['source_path']
        before = path.read_bytes()
        manifest, _nodes = describe(path, sample)
        manifest['source_unchanged'] = path.read_bytes() == before
        (args.out / (sample['sample_id'] + '-diagnostic.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        manifests[sample['sample_id']] = manifest
        topic, role = source_identity(sample['name'])
        if topic and role:
            groups[(sample['subject'], topic)].append((role, sample['sample_id']))
    for (_subject, topic), members in groups.items():
        teachers = [sid for role, sid in members if role == 'teacher']
        students = [sid for role, sid in members if role == 'student']
        if len(students) != 1:
            continue
        for sid in teachers:
            row = compare(manifests[sid], manifests[students[0]])
            row['topic'] = topic; rows.append(row)
    summary = {'definition': 'Read-only exact C14N/ordered subsequence audit; fingerprints and text previews are not removal authority.',
               'source_count': len(meta), 'source_hash_matches': sum(m['manifest_sha_ok'] for m in manifests.values()),
               'source_unchanged': sum(m['source_unchanged'] for m in manifests.values()),
               'pairs': rows, 'selected': 0, 'derived_outputs': 0, 'wps_derived_uat': 'NOT_RUN_NO_APPROVED_DERIVATIVE'}
    (args.out / 'pair_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.legacy_runtime:
        legacy_audit(args.legacy_runtime, meta, args.out)
    for row in rows:
        print(row['teacher'], row['student'], row['subject'], row['teacher_body_count'], row['student_body_count'],
              'exact embeddings', row['exact_student_subsequence_embeddings_capped2'],
              'tables same', row['ordered_table_subtrees_byte_equivalent_c14n'],
              'unmatched student', len(row['student_blocks_absent_from_teacher']))


if __name__ == '__main__':
    main()

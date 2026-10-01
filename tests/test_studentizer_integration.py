"""Synthetic complete Golden evidence; no real-source/COM support claims."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import zipfile

from lxml import etree
import pytest

from test_batch_job_service import client, renderer, docx, post, service, app
from job_service import JobService
from semantic_facade import analyze_source
from studentizer import AnswerBinding, TAG, element_sha256
from studentizer_planner import (CompleteStudentEvidence, ReviewedBody,
                                prepare_complete_student, semantic_fingerprint)


def source():
    return docx("知识点：加法", "即时训练", "1．求 2+3？", "【答案】5",
                "2．求 3+4？", "【答案】7")


def evidence(snapshot, data):
    with zipfile.ZipFile(BytesIO(data)) as package:
        root = etree.fromstring(package.read("word/document.xml"))
    body = root.find(TAG("body")); children = list(body)
    questions = [u for u in snapshot.units if u.get("role") == "question_group"]
    # Fixture truth is declared independently: known prompts 2/4, answers 3/5.
    assert [u['spans'] for u in questions] == [[['b2', 'b2']], [['b4', 'b4']]]
    review = "synthetic-golden-review"
    entries = tuple(ReviewedBody(i, element_sha256(n),
        "answer" if i in (3, 5) else "question" if i in (2, 4) else "knowledge",
        "remove" if i in (3, 5) else None) for i, n in enumerate(children))
    bindings = tuple(AnswerBinding(u['id'], 'question_group', start, answer, answer,
        element_sha256(children[answer]), 'reviewed_question_answer', review)
        for u, start, answer in zip(questions, (2, 4), (3, 5)))
    for i in (5, 3):
        body.remove(children[i])
    return CompleteStudentEvidence(sha256(data).hexdigest(), semantic_fingerprint(snapshot),
        review, entries, tuple(u['id'] for u in questions), bindings, element_sha256(root))


def test_exact_complete_golden_uses_real_studentizer_without_com(client, renderer):
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = evidence
    original = source()
    final = post(client, [("专题 教师版.docx", original)])
    assert final['status'] == 'done', final.get('error')
    assert final['renderer'] == 'XML'
    prep = final['student_preparation']
    assert prep['status'] == 'XML_PREPARED' and prep['package_valid']
    assert prep['coverage']['answer_paragraphs'] == 2
    assert prep['coverage']['question_groups'] == 2
    assert not prep['make_student_called'] and not prep['wps_com_started']
    assert not renderer['fallback'] and not renderer['make_student']
    assert renderer['xml'][0] == original
    with zipfile.ZipFile(BytesIO(renderer['xml'][1])) as package:
        text = ''.join(etree.fromstring(package.read('word/document.xml')).itertext())
    assert '【答案】' not in text and '1．求 2+3？' in text and '2．求 3+4？' in text
    assert renderer['xml'][1] != original
    recovered = JobService(app.config['RESULT_ROOT'], runtime_root=app.config['RUNTIME_ROOT']).get(final['job_id'])
    assert recovered['student_preparation'] == prep


def incomplete(e):
    return replace(e, body=e.body[:-1])


def unanswered(e):
    return replace(e, bindings=e.bindings[:1])


def unreviewed_candidate(e):
    return replace(e, body=tuple(replace(b, candidate_review=None) if b.index == 5 else b for b in e.body))


@pytest.mark.parametrize('mutation,reason', [
    (incomplete, 'STUDENTIZER_COVERAGE_INCOMPLETE'),
    (unanswered, 'STUDENTIZER_COVERAGE_INCOMPLETE'),
    (unreviewed_candidate, 'STUDENTIZER_UNHANDLED_ANSWER_CANDIDATE'),
    (lambda e: replace(e, question_ids=e.question_ids[:1]), 'STUDENTIZER_COVERAGE_INCOMPLETE'),
    (lambda e: replace(e, semantic_sha256='stale'), 'STUDENTIZER_SOURCE_IDENTITY_MISMATCH'),
    (lambda e: replace(e, source_sha256='stale'), 'STUDENTIZER_SOURCE_IDENTITY_MISMATCH'),
    (lambda e: replace(e, golden_document_sha256='wrong'), 'STUDENTIZER_GOLDEN_COMPARISON_FAILED'),
    (lambda e: replace(e, coverage_basis='ROLE_ONLY'), 'STUDENTIZER_COVERAGE_UNPROVEN'),
    (lambda e: replace(e, bindings=(replace(e.bindings[0], owner_id='section'), *e.bindings[1:])), 'STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN'),
])
def test_incomplete_or_stale_evidence_invokes_whole_job_fallback(client, renderer, mutation, reason):
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = lambda s, d: mutation(evidence(s, d))
    final = post(client, [("专题 教师版.docx", source())])
    assert final['status'] == 'done', final.get('error')
    assert final['renderer'] == 'V0.9' and final['fallback_reason'] == 'XML_RENDER_FAILED'
    prep = final['student_preparation']
    assert prep['reason_code'] == reason and reason in final['fallback_detail']
    assert prep['make_student_called'] and prep['wps_com_started']
    assert prep['fallback_engine'] == 'V0.9_WHOLE_JOB'
    assert prep['make_student_elapsed_seconds'] >= 0 and prep['fallback_elapsed_seconds'] >= 0
    assert len(renderer['make_student']) == 1 and not renderer['xml']
    assert len(final['output_paths']) == 2
    assert not list(Path(app.config['RUNTIME_ROOT']).rglob('derived-student-source.docx'))


def test_default_missing_evidence_is_explicit_and_nonmutating(tmp_path):
    data = source(); source_file = tmp_path / 'original.docx'; source_file.write_bytes(data)
    output = tmp_path / 'student.docx'
    result, coverage = prepare_complete_student(source_file, output)
    assert result.reason_code == 'STUDENTIZER_COVERAGE_UNPROVEN'
    assert coverage is None and not output.exists() and source_file.read_bytes() == data


@pytest.mark.parametrize('paired', [True, False])
def test_supplied_student_never_calls_provider(client, renderer, paired):
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = lambda *_: pytest.fail('provider must be bypassed')
    student = docx('保留用户学生版')
    files = [('专题 学生版.docx', student)]
    if paired:
        files.insert(0, ('专题 教师版.docx', source()))
    final = post(client, files)
    assert final['status'] == 'done' and final['renderer'] == 'XML'
    assert renderer['xml'][-1] == student
    assert not renderer['make_student'] and not renderer['fallback']
    assert final['student_preparation']['status'] == 'STUDENT_SOURCE_BYPASS'


def test_mixed_batch_keeps_xml_and_fallback_independent_and_persistent(client, renderer):
    original = source()
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = lambda s, d: evidence(s, d) if d == original else None
    final = post(client, [('A 教师版.docx', original), ('B 教师版.docx', docx('unknown')),
                          ('C 学生版.docx', docx('supplied'))])
    assert final['status'] == 'done' and final['produced'] == 5
    assert [i['renderer'] for i in final['items']] == ['XML', 'V0.9', 'XML']
    assert len(renderer['make_student']) == 1 and len(renderer['fallback']) == 1
    recovered = JobService(app.config['RESULT_ROOT'], runtime_root=app.config['RUNTIME_ROOT']).get(final['job_id'])
    assert [i['student_preparation'] for i in recovered['items']] == [i['student_preparation'] for i in final['items']]


@pytest.mark.parametrize('fail', [False, True])
def test_later_xml_failure_fallback_starts_original_and_restores_observer(client, renderer, monkeypatch, fail):
    import renderer_orchestrator
    import template_slot_composer
    engine = renderer_orchestrator._load_v09_engine()
    original_callable = engine.make_student
    seen = []
    original_fallback = renderer_orchestrator.render_v09_whole_job
    def fallback(job, reason):
        seen.append(job)
        assert job.student_source_doc is None
        if fail:
            engine.make_student(job.source_doc, job.student_output_doc)
            raise RuntimeError('safe fallback failure')
        return original_fallback(job, reason)
    def render(*_args):
        raise RuntimeError('safe XML failure')
    monkeypatch.setattr(renderer_orchestrator, 'render_v09_whole_job', fallback)
    monkeypatch.setattr(template_slot_composer, 'render_slots', render)
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = evidence
    original = source()
    final = post(client, [('专题 教师版.docx', original)])
    assert final['status'] == ('error' if fail else 'done')
    assert seen and Path(seen[0].source_doc).read_bytes() == original
    assert engine.make_student is original_callable
    assert final['student_preparation']['make_student_called']
    assert final['student_preparation']['status'] == 'XML_PREPARED'
    assert final['student_preparation']['reason_code'] is None
    assert final['fallback_reason'] == 'XML_RENDER_FAILED'


def rewrite(data, change):
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as old, zipfile.ZipFile(out, 'w') as new:
        for item in old.infolist():
            value = old.read(item.filename)
            if item.filename == 'word/document.xml':
                root = etree.fromstring(value); change(root.find(TAG('body')))
                value = etree.tostring(root)
            new.writestr(item, value)
    return out.getvalue()


@pytest.mark.parametrize('kind,reason', [
    ('tbl', 'STUDENTIZER_TABLE_SCOPE_UNSUPPORTED'),
    ('textbox', 'STUDENTIZER_TEXTBOX_SCOPE_UNSUPPORTED')])
def test_complex_body_scope_fails_closed(tmp_path, kind, reason):
    def change(body):
        if kind == 'tbl':
            node = etree.Element(TAG('tbl'))
            etree.SubElement(etree.SubElement(etree.SubElement(node, TAG('tr')), TAG('tc')), TAG('p'))
            body.insert(len(body)-1, node)
        else:
            etree.SubElement(body[0], TAG('txbxContent'))
    data = rewrite(source(), change)
    result, _ = prepare_complete_student(data, tmp_path / 'student.docx', evidence)
    assert result.reason_code == reason
    assert not (tmp_path / 'student.docx').exists()


def test_reviewed_red_knowledge_is_preserved_without_color_inference(tmp_path):
    def change(body):
        props = etree.Element(TAG('rPr'))
        etree.SubElement(props, TAG('color')).set(TAG('val'), 'FF0000')
        body[0].find(TAG('r')).insert(0, props)
    data = rewrite(source(), change)
    def reviewed(snapshot, raw):
        e = evidence(snapshot, raw)
        return replace(e, body=tuple(replace(b, candidate_review='preserve') if b.index == 0 else b for b in e.body))
    result, _ = prepare_complete_student(data, tmp_path / 'student.docx', reviewed)
    assert result.status == 'XML_PREPARED'
    with zipfile.ZipFile(result.output_path) as output:
        root = etree.fromstring(output.read('word/document.xml'))
    assert root.find(TAG('body'))[0].find('.//' + TAG('color')).get(TAG('val')) == 'FF0000'


def test_provider_cannot_mutate_semantic_snapshot_to_authorize_plan(tmp_path):
    def mutate(snapshot, data):
        e = evidence(snapshot, data)
        snapshot.units[0]['role'] = 'question_group'
        return replace(e, semantic_sha256=semantic_fingerprint(snapshot))
    result, _ = prepare_complete_student(source(), tmp_path / 'student.docx', mutate)
    assert result.reason_code == 'STUDENTIZER_SOURCE_IDENTITY_MISMATCH'
    assert not (tmp_path / 'student.docx').exists()


def test_concurrent_teacher_fallbacks_are_serial_and_observer_is_restored(client, renderer, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time
    import app as app_module
    import renderer_orchestrator
    app.config['C0_DISABLE_JOB_SUBMISSION'] = True
    jobs = [post(client, [(f'专题{i} 教师版.docx', docx('unknown'))]) for i in range(3)]
    engine = renderer_orchestrator._load_v09_engine()
    initial = engine.make_student
    fallback = renderer_orchestrator.render_v09_whole_job
    guard = threading.Lock(); counts = {'active': 0, 'maximum': 0}
    def observe(job, reason):
        with guard:
            counts['active'] += 1
            counts['maximum'] = max(counts['maximum'], counts['active'])
        try:
            time.sleep(.02)
            return fallback(job, reason)
        finally:
            with guard:
                counts['active'] -= 1
    monkeypatch.setattr(renderer_orchestrator, 'render_v09_whole_job', observe)
    with ThreadPoolExecutor(max_workers=3) as workers:
        list(workers.map(app_module._execute_job, [j['job_id'] for j in jobs]))
    assert counts == {'active': 0, 'maximum': 1}
    assert engine.make_student is initial and len(renderer['make_student']) == 3
    assert all(service().get(j['job_id'])['student_preparation']['make_student_called'] for j in jobs)
    assert all(service().get(j['job_id'])['status'] == 'done' for j in jobs)

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
def test_incomplete_or_stale_evidence_uses_v09_preparation_then_xml(client, renderer, mutation, reason):
    app.config['STUDENTIZER_EVIDENCE_PROVIDER'] = lambda s, d: mutation(evidence(s, d))
    final = post(client, [("专题 教师版.docx", source())])
    assert final['status'] == 'done', final.get('error')
    assert final['renderer'] == 'XML' and final['fallback_reason'] is None
    prep = final['student_preparation']
    assert prep['reason_code'] == reason and prep['student_preparation'] == 'V09_MAKE_STUDENT'
    assert prep['make_student_called']
    assert prep['wps_com_started'] is None and prep['com_used'] is None
    assert prep['com_observation'] == 'UNKNOWN_AFTER_MAKE_STUDENT_ENTRY'
    assert prep['make_student_elapsed_seconds'] >= 0
    assert len(renderer['make_student']) == 1 and len(renderer['xml']) == 2
    assert not renderer['fallback']
    assert len(final['output_paths']) == 2
    assert list(Path(app.config['RUNTIME_ROOT']).rglob('derived-student-source.docx'))


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
    assert [i['renderer'] for i in final['items']] == ['XML', 'XML', 'XML']
    assert len(renderer['make_student']) == 1 and len(renderer['fallback']) == 0
    assert final['items'][1]['student_preparation']['student_preparation'] == 'V09_MAKE_STUDENT'
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
    assert not final['student_preparation']['make_student_called']
    assert final['student_preparation']['status'] == 'XML_PREPARED'
    assert final['student_preparation']['reason_code'] is None
    assert final['student_preparation']['com_used'] is False
    assert final['fallback_reason'] == 'XML_RENDER_FAILED'
    fallback_prep = final['renderer_fallback_preparation']
    assert fallback_prep['route'] == 'V09_WHOLE_JOB'
    assert fallback_prep['make_student_called'] is True
    assert fallback_prep['com_used'] is None
    assert fallback_prep['wps_com_started'] is None
    assert fallback_prep['com_observation'] == 'UNKNOWN_AFTER_MAKE_STUDENT_ENTRY'
    assert fallback_prep['reason_code'] == 'XML_RENDER_FAILED'
    assert fallback_prep['elapsed_seconds'] >= fallback_prep['make_student_elapsed_seconds']


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


def test_concurrent_teacher_preparation_is_serial_and_observer_is_restored(client, renderer, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time
    import app as app_module
    import renderer_orchestrator
    app.config['C0_DISABLE_JOB_SUBMISSION'] = True
    jobs = [post(client, [(f'专题{i} 教师版.docx', docx('unknown'))]) for i in range(3)]
    engine = renderer_orchestrator._load_v09_engine()
    guard = threading.Lock(); counts = {'active': 0, 'maximum': 0}
    original_make_student = engine.make_student
    def observe_make_student(*args, **kwargs):
        with guard:
            counts['active'] += 1
            counts['maximum'] = max(counts['maximum'], counts['active'])
        try:
            time.sleep(.02)
            return original_make_student(*args, **kwargs)
        finally:
            with guard:
                counts['active'] -= 1
    engine.make_student = observe_make_student
    monkeypatch.setattr(renderer_orchestrator, '_load_v09_engine', lambda: engine)
    with ThreadPoolExecutor(max_workers=3) as workers:
        list(workers.map(app_module._execute_job, [j['job_id'] for j in jobs]))
    assert counts == {'active': 0, 'maximum': 1}
    assert len(renderer['make_student']) == 3
    assert engine.make_student == observe_make_student
    assert all(service().get(j['job_id'])['student_preparation']['make_student_called'] for j in jobs)
    assert all(service().get(j['job_id'])['status'] == 'done' for j in jobs)


@pytest.mark.parametrize('role', ['teacher', 'student'])
def test_publication_uses_target_volume_temp_for_cross_volume_safe_replace(
        tmp_path, monkeypatch, role):
    import app as app_module

    staging = tmp_path / 'staging'
    results = tmp_path / 'redirected-desktop'
    staging.mkdir(); results.mkdir()
    source_path = staging / (role + '-stage.docx')
    source_path.write_bytes(docx('cross-volume publication fixture'))
    target_path = results / (role + '-final.docx')
    expected = sha256(source_path.read_bytes()).hexdigest()
    real_replace = app_module.os.replace
    replacements = []

    def reject_cross_volume(source, target):
        source, target = Path(source), Path(target)
        if source == source_path:
            raise OSError(17, 'simulated cross-volume rename')
        assert source.parent == target.parent == results
        assert source.name.startswith('.jiangyi-publish-job-%s-' % role)
        replacements.append((source, target))
        return real_replace(source, target)

    monkeypatch.setattr(app_module.os, 'replace', reject_cross_volume)
    from package_validator import validate_package
    digest = app_module._publish_staged_output(
        source_path, target_path, job_id='job-%s' % role, role=role,
        expected_sha256=expected, package_validator=validate_package)

    assert digest == expected
    assert len(replacements) == 1
    assert replacements[0][1] == target_path
    assert target_path.read_bytes() == source_path.read_bytes()
    assert list(results.iterdir()) == [target_path]


def test_failed_publication_validation_cleans_temp_and_preserves_successful_sibling(tmp_path):
    import app as app_module

    results = tmp_path / 'results'; results.mkdir()
    staging = tmp_path / 'staging'; staging.mkdir()
    source_path = staging / 'student.docx'
    source_path.write_bytes(docx('invalid copy fixture'))
    target_path = results / 'student.docx'
    sibling = results / 'teacher.docx'
    sibling.write_bytes(docx('previously published teacher'))

    def reject_package(_path):
        return {'valid': False, 'errors': ['simulated package validation failure']}

    with pytest.raises(RuntimeError, match='package validation failed'):
        app_module._publish_staged_output(
            source_path, target_path, job_id='failed-job', role='student',
            expected_sha256=sha256(source_path.read_bytes()).hexdigest(),
            package_validator=reject_package)

    assert not target_path.exists()
    assert sibling.is_file() and sibling.stat().st_size > 0
    assert list(results.iterdir()) == [sibling]


@pytest.mark.parametrize('crash_after', ['teacher', 'student'])
def test_publication_restart_reuses_valid_final_roles_without_deleting_them(
        tmp_path, client, renderer, monkeypatch, crash_after):
    from package_validator import validate_package
    import app as app_module

    app.config['C0_DISABLE_JOB_SUBMISSION'] = True
    teacher = docx('X008-like retained teacher source')
    student = docx('X008-like already supplied student source')
    created = post(client, [('专题 教师版.docx', teacher), ('专题 学生版.docx', student)])
    job_id = created['job_id']
    fired = {'done': False}

    def interrupt(_job_id, stage):
        expected = 'published %s; before next role' % crash_after
        if stage == expected and not fired['done']:
            fired['done'] = True
            raise SystemExit('simulated abrupt process termination')

    app.config['C35_TEST_STAGE_HOOK'] = interrupt
    with pytest.raises(SystemExit, match='simulated abrupt process termination'):
        app_module._execute_job(job_id)
    assert fired['done']
    interrupted = service().get(job_id)
    assert interrupted['status'] == 'running'
    first_paths = [Path(path) for path in interrupted['publication']['role_paths'].values()]
    persisted = [p for p in first_paths if p.exists()]
    expected_count = 1 if crash_after == 'teacher' else 2
    assert len(persisted) == expected_count
    original_hashes = {p: sha256(p.read_bytes()).hexdigest() for p in persisted}
    assert all(validate_package(str(p)).get('valid') is True for p in persisted)

    # Constructing a fresh service exercises the actual startup recovery path.
    recovered_service = JobService(app.config['RESULT_ROOT'], runtime_root=app.config['RUNTIME_ROOT'])
    assert recovered_service.get(job_id)['status'] == 'queued'
    app.extensions.pop('c0_job_services', None)
    app.config['C35_TEST_STAGE_HOOK'] = None
    result_dir = Path(interrupted['result_dir'])
    orphan = result_dir / ('.jiangyi-publish-%s-orphan.tmp' % job_id)
    orphan.write_bytes(b'abandoned partial publication copy')
    app_module._execute_job(job_id)
    assert not orphan.exists()
    final = service().get(job_id)
    assert final['status'] == 'done', final.get('error')
    assert len(final['output_paths']) == 2
    assert all(Path(path).is_file() and Path(path).stat().st_size > 0 for path in final['output_paths'])
    assert all(validate_package(path).get('valid') is True for path in final['output_paths'])
    assert all(sha256(path.read_bytes()).hexdigest() == digest for path, digest in original_hashes.items())
    assert set(Path(final['result_dir']).iterdir()) == set(Path(path) for path in final['output_paths'])
    assert final['publication']['published'].keys() == {'teacher', 'student'}


def test_restart_rebinds_only_unpublished_role_after_valid_docx_zip_metadata_changes(
        client, renderer, monkeypatch):
    import app as app_module
    import template_slot_composer

    app.config['C0_DISABLE_JOB_SUBMISSION'] = True
    created = post(client, [('专题 教师版.docx', docx('teacher fixture')),
                           ('专题 学生版.docx', docx('student fixture'))])
    job_id = created['job_id']
    interrupted_once = {'done': False}

    def interrupt_after_teacher(_job_id, stage):
        if stage == 'published teacher; before next role' and not interrupted_once['done']:
            interrupted_once['done'] = True
            raise SystemExit('simulated abrupt process termination')

    app.config['C35_TEST_STAGE_HOOK'] = interrupt_after_teacher
    with pytest.raises(SystemExit, match='simulated abrupt process termination'):
        app_module._execute_job(job_id)
    interrupted = service().get(job_id)
    assert interrupted['status'] == 'running'
    published_teacher = Path(interrupted['publication']['role_paths']['teacher'])
    teacher_bytes_before = published_teacher.read_bytes()
    teacher_hash_before = sha256(teacher_bytes_before).hexdigest()
    old_expected = dict(interrupted['publication']['expected_sha256'])
    assert interrupted['publication']['published']['teacher']['sha256'] == teacher_hash_before
    assert not Path(interrupted['publication']['role_paths']['student']).exists()

    # Startup recovery clears staging; the renderer then regenerates valid DOCX
    # packages with different ZIP timestamps and therefore different byte hashes.
    JobService(app.config['RESULT_ROOT'], runtime_root=app.config['RUNTIME_ROOT'])
    app.extensions.pop('c0_job_services', None)
    app.config['C35_TEST_STAGE_HOOK'] = None
    original_render = template_slot_composer.render_slots
    regenerate = {'with_new_zip_metadata': True}
    regenerated_hashes = {}

    def render_with_new_zip_metadata(source_path, plan, output_path):
        result = original_render(source_path, plan, output_path)
        if regenerate['with_new_zip_metadata']:
            output = Path(output_path)
            temp = output.with_suffix('.rewritten.docx')
            with zipfile.ZipFile(output, 'r') as source_package:
                entries = [(info.filename, source_package.read(info.filename), info.compress_type)
                           for info in source_package.infolist()]
            with zipfile.ZipFile(temp, 'w') as target_package:
                for name, data, compression in entries:
                    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                    info.compress_type = compression
                    target_package.writestr(info, data)
            temp.replace(output)
            role = 'student' if output.name.startswith('student-stage-') else 'teacher'
            regenerated_hashes[role] = sha256(output.read_bytes()).hexdigest()
        return result

    monkeypatch.setattr(template_slot_composer, 'render_slots', render_with_new_zip_metadata)
    app_module._execute_job(job_id)

    final = service().get(job_id)
    assert final['status'] == 'done', final.get('error')
    assert old_expected['student'] != regenerated_hashes['student']
    assert final['publication']['expected_sha256']['student'] == regenerated_hashes['student']
    assert final['publication']['expected_sha256']['teacher'] == old_expected['teacher']
    assert sha256(published_teacher.read_bytes()).hexdigest() == teacher_hash_before
    assert published_teacher.read_bytes() == teacher_bytes_before
    assert set(Path(final['result_dir']).iterdir()) == set(Path(path) for path in final['output_paths'])
    assert final['publication']['published'].keys() == {'teacher', 'student'}

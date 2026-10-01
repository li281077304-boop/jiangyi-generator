"""Synthetic backend batch integration; these tests do not claim real COM UAT."""
import io
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import zipfile

from docx import Document
import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "v1.2-xml-experiment" / "res" / "app" / "webapp"
sys.path.insert(0, str(WEBAPP))
sys.path.insert(0, str(WEBAPP.parent))
import app as app_module
from app import app
from job_service import JobService


def docx(*texts):
    buffer = io.BytesIO()
    document = Document()
    for text in texts or ("题目",):
        document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def archive(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for name, data in entries:
            package.writestr(name, data)
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, RESULT_ROOT=tmp_path / "results",
                      RUNTIME_ROOT=tmp_path / "runtime",
                      C0_DISABLE_JOB_SUBMISSION=False, C0_RUN_JOBS_SYNCHRONOUSLY=True,
                      C0_FORCE_FALLBACK_REASON=None, STUDENTIZER_EVIDENCE_PROVIDER=None,
                      OPEN_FOLDER=lambda _folder: None)
    return app.test_client()


def service():
    return app_module._jobs()


def post(client, files, **options):
    data = {"subject": "数学", "grade": "高一", "handout_type": "复习讲义",
            "academic_year": "2026-2027学年", "template_type": "1v1",
            "docx_mode": "auto", **options,
            "files": [(io.BytesIO(content), name) for name, content in files]}
    response = client.post("/api/jobs", data=data, content_type="multipart/form-data")
    assert response.status_code == 202, response.get_json()
    return client.get("/api/jobs/" + response.get_json()["job_id"]).get_json()


@pytest.fixture
def renderer(monkeypatch):
    import renderer_orchestrator
    import slot_router
    import template_slot_composer
    calls = {"xml": [], "fallback": [], "make_student": []}
    plan = SimpleNamespace(template_sha256="fixture-template", slots={
        name: () for name in ("knowledge", "immediate", "final")}, units=(),
        slot_labels={"knowledge": "知识精讲", "immediate": "即时训练", "final": "六、巩固练习"},
        explicit_final_heading=True)

    def build(source, *_args, **_kwargs):
        if "FORCED_UNSUPPORTED" in " ".join(p.text for p in Document(source).paragraphs):
            raise slot_router.SlotRoutingError("UNSUPPORTED_BOOKMARK_SCOPE", "safe forced fixture")
        return plan

    def render(source, _plan, output):
        calls["xml"].append(Path(source).read_bytes())
        Path(output).write_bytes(Path(source).read_bytes())
        return SimpleNamespace(output_path=str(output), resource_report={"unsupported": []},
                               package_report={"valid": True, "errors": []})

    def fallback(job, reason):
        calls["fallback"].append((job.topic, reason))
        outputs = [job.output_doc]
        Path(job.output_doc).write_bytes(Path(job.source_doc).read_bytes())
        if job.student_source_doc:
            Path(job.student_output_doc).write_bytes(Path(job.student_source_doc).read_bytes())
            outputs.append(job.student_output_doc)
        elif not job.student_only:
            engine.make_student(job.source_doc, job.student_output_doc)
            outputs.append(job.student_output_doc)
        return {"output_paths": outputs, "whole_job": True,
                "baseline_sha": renderer_orchestrator.V09_BASELINE_SHA}

    def make_student(source, output):
        calls["make_student"].append(source)
        Path(output).write_bytes(docx("已由测试替身去答案的学生版"))

    monkeypatch.setattr(slot_router, "build_slot_routing_plan", build)
    monkeypatch.setattr(template_slot_composer, "render_slots", render)
    monkeypatch.setattr(renderer_orchestrator, "render_v09_whole_job", fallback)
    engine = SimpleNamespace(make_student=make_student)
    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine", lambda: engine)
    return calls


def assert_clean(job):
    folder = Path(job["result_dir"])
    files = list(folder.rglob("*"))
    assert all("_" not in path.name for path in files)
    assert all(path.is_dir() or path.suffix == ".docx" for path in files)
    assert len([path for path in files if path.is_file()]) == len(job["output_paths"])


def test_three_supplied_pairs_are_independent_xml_items(client, renderer):
    teacher, student = docx("教师独有内容"), docx("学生独有内容")
    files = [(f"专题{i} 教师版.docx", teacher) for i in (1, 2, 3)]
    files += [(f"专题{i} 学生版.docx", student) for i in (3, 1, 2)]
    final = post(client, files)
    assert final["status"] == "done" and final["batch_outcome"] == "ALL_SUCCESS"
    assert (final["total"], final["completed"], final["failed"], final["produced"]) == (3, 3, 0, 6)
    assert all(item["renderer"] == "XML" and item["input_version"] == "TEACHER_AND_STUDENT"
               for item in final["items"])
    assert not renderer["fallback"] and not renderer["make_student"]
    assert renderer["xml"] == [teacher, student] * 3
    assert all(not item["student_preparation"]["make_student_called"] for item in final["items"])
    assert len(client.get("/api/jobs").get_json()["jobs"]) == 1  # child jobs are internal
    assert_clean(final)


def test_corrupt_item_does_not_remove_two_successful_outputs(client, renderer):
    final = post(client, [("正常A 学生版.docx", docx()), ("损坏 教师版.docx", b"broken"),
                          ("正常B 学生版.docx", docx())])
    assert final["status"] == "partial" and final["batch_outcome"] == "PARTIAL_SUCCESS"
    assert (final["completed"], final["failed"], len(final["output_paths"])) == (2, 1, 2)
    assert final["has_result"] and "download_available" not in final
    assert all(Path(path).is_file() for path in final["output_paths"])
    assert client.get("/api/open/" + final["job_id"]).status_code == 200
    assert client.get("/api/download/" + final["job_id"]).status_code == 404
    restarted = JobService(app.config["RESULT_ROOT"], runtime_root=app.config["RUNTIME_ROOT"])
    assert restarted.get(final["job_id"])["status"] == "partial"
    assert len(restarted.list()) == 1
    assert_clean(final)


def test_mixed_renderer_falls_back_only_for_one_item(client, renderer):
    final = post(client, [(f"专题{i} 学生版.docx", docx("FORCED_UNSUPPORTED" if i == 4 else "XML"))
                          for i in range(1, 5)])
    assert final["status"] == "done"
    assert [item["renderer"] for item in final["items"]] == ["XML", "XML", "XML", "V0.9"]
    assert renderer["fallback"] == [("专题4", "XML_RENDER_FAILED")]
    fallback_item = final["items"][-1]
    assert fallback_item["fallback_reason"] == "XML_RENDER_FAILED"
    assert "UNSUPPORTED_BOOKMARK_SCOPE" in fallback_item["fallback_detail"]
    assert not renderer["make_student"]


def test_failed_generation_keeps_fallback_intent_and_valid_siblings(client, renderer, monkeypatch):
    import renderer_orchestrator
    def fail(_job, _reason):
        raise RuntimeError("fixture COM failure")
    monkeypatch.setattr(renderer_orchestrator, "render_v09_whole_job", fail)
    final = post(client, [("A 学生版.docx", docx()),
                          ("B 学生版.docx", docx("FORCED_UNSUPPORTED")),
                          ("C 学生版.docx", docx())])
    assert final["status"] == "partial"
    assert [item["status"] for item in final["items"]] == ["done", "error", "done"]
    assert final["items"][1]["renderer"] == "V0.9"
    assert final["items"][1]["fallback_reason"] == "XML_RENDER_FAILED"
    assert all(Path(path).is_file() for path in final["output_paths"])


def test_zip_mixed_input_versions_preserves_user_student(client, renderer):
    student = docx("用户提供的学生内容")
    package = archive([("第一层/专题A 教师用.docx", docx()),
                       ("第一层/第二层/专题B 学生用.docx", student),
                       ("第一层/专题C 解析版.docx", docx()),
                       ("另一层/专题C 原卷版.docx", student),
                       ("第一层/~$专题C 解析版.docx", b"temporary")])
    final = post(client, [("中文混合输入.zip", package)])
    assert final["status"] == "done" and final["total"] == 3
    assert [item["input_version"] for item in final["items"]] == [
        "TEACHER_ONLY", "STUDENT_ONLY", "TEACHER_AND_STUDENT"]
    assert final["produced"] == 5 and len(renderer["make_student"]) == 1
    assert final["items"][0]["student_preparation"]["elapsed_seconds"] >= 0
    assert final["items"][0]["student_preparation"]["make_student_called"] is True
    assert final["items"][0]["student_preparation"]["wps_com_started"] is True
    assert all(not item["student_preparation"]["make_student_called"] for item in final["items"][1:])
    assert renderer["xml"].count(student) == 2
    assert_clean(final)


def test_all_bad_items_are_all_failed_without_local_outputs(client, renderer):
    final = post(client, [(f"损坏{i} 教师版.docx", b"broken") for i in range(3)])
    assert final["status"] == "error" and final["batch_outcome"] == "ALL_FAILED"
    assert final["failed"] == 3 and final["completed"] == 0
    assert final["output_paths"] == [] and not final["has_result"]
    assert client.get("/api/download/" + final["job_id"]).status_code == 404
    assert not renderer["xml"] and not renderer["fallback"]


def test_recovery_loses_only_item_with_missing_final_output(client, renderer):
    final = post(client, [(f"专题{i} 学生版.docx", docx()) for i in range(3)])
    Path(final["items"][1]["output_paths"][0]).unlink()
    restarted = JobService(app.config["RESULT_ROOT"], runtime_root=app.config["RUNTIME_ROOT"])
    recovered = restarted.get(final["job_id"])
    assert recovered["status"] == "partial"
    assert recovered["completed"] == 2 and recovered["failed"] == 1
    assert all(Path(path).is_file() for path in recovered["output_paths"])


def test_batch_parent_restart_skips_already_completed_child(client, renderer):
    app.config["C0_DISABLE_JOB_SUBMISSION"] = True
    final = post(client, [(f"专题{i} 学生版.docx", docx()) for i in range(3)])
    parent = service().start_job(final["job_id"])
    app_module._execute_job(parent["items"][0]["child_job_id"])
    # Fresh service marks interrupted parent queued; completed child stays done.
    restarted = JobService(app.config["RESULT_ROOT"], runtime_root=app.config["RUNTIME_ROOT"])
    recovered = restarted.get(final["job_id"])
    assert recovered["status"] == "queued" and recovered["completed"] == 1
    app_module._execute_batch(final["job_id"])
    assert service().get(final["job_id"])["status"] == "done"
    assert len(renderer["xml"]) == 3  # the first child wasn't rendered twice


def test_local_outputs_have_no_name_collisions_for_same_topic_separate_mode(client, renderer):
    final = post(client, [("专题 学生版.docx", docx())] * 3, docx_mode="separate")
    assert final["status"] == "done" and final["total"] == 3
    paths = [Path(path) for path in final["output_paths"]]
    assert len(paths) == len(set(paths)) == 3
    assert len({path.parent for path in paths}) == 3
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)
    assert_clean(final)


def test_batch_metadata_exposes_current_topic_and_serial_order(client, renderer, monkeypatch):
    import template_slot_composer
    original = template_slot_composer.render_slots
    seen = []
    def observe(source, plan, output):
        parent = service().list()[0]
        seen.append((parent["current_topic"], parent["completed"], parent["total"]))
        return original(source, plan, output)
    monkeypatch.setattr(template_slot_composer, "render_slots", observe)
    final = post(client, [(f"专题{i} 学生版.docx", docx()) for i in range(1, 4)])
    assert final["status"] == "done"
    assert seen == [("专题1", 0, 3), ("专题2", 1, 3), ("专题3", 2, 3)]
    assert final["current_topic"] is None


def test_child_creation_failure_does_not_abort_batch(client, renderer, monkeypatch):
    jobs = service()
    original = jobs.create_inputs
    def fail_one(files, options, **kwargs):
        if kwargs.get("_topic") == "专题B":
            raise OSError("safe fixture write failure")
        return original(files, options, **kwargs)
    monkeypatch.setattr(jobs, "create_inputs", fail_one)
    final = post(client, [(f"专题{letter} 学生版.docx", docx()) for letter in "ABC"])
    assert final["status"] == "partial" and final["completed"] == 2 and final["failed"] == 1
    assert [item["status"] for item in final["items"]] == ["done", "error", "done"]
    assert all(Path(path).is_file() for path in final["output_paths"])


def test_concurrent_first_submissions_share_one_serial_executor(client, monkeypatch):
    """Real async queue, deliberately held during first construction and work."""
    from concurrent.futures import ThreadPoolExecutor

    app.config.update(C0_DISABLE_JOB_SUBMISSION=False, C0_RUN_JOBS_SYNCHRONOUSLY=False)
    # Isolate this test's executor/pending registry and restore the app afterward.
    monkeypatch.setattr(app, "extensions", {})
    barrier = threading.Barrier(9)
    constructor_started = threading.Event()
    second_constructor_started = threading.Event()
    release_constructor = threading.Event()
    first_callback_started = threading.Event()
    release_callbacks = threading.Event()
    guard = threading.Lock()
    executors, observed, failures = [], [], []
    active = {"current": 0, "maximum": 0}
    constructors = {"count": 0}

    def make_executor(**kwargs):
        with guard:
            constructors["count"] += 1
            if constructors["count"] > 1:
                second_constructor_started.set()
        constructor_started.set()
        if not release_constructor.wait(5):
            raise RuntimeError("test constructor timed out")
        executor = ThreadPoolExecutor(**kwargs)
        with guard:
            executors.append(executor)
        return executor

    def callback(job_id):
        with guard:
            active["current"] += 1
            active["maximum"] = max(active["maximum"], active["current"])
        first_callback_started.set()
        try:
            if not release_callbacks.wait(5):
                raise RuntimeError("test callback timed out")
            with guard:
                observed.append(job_id)
        finally:
            with guard:
                active["current"] -= 1

    def submit(index):
        try:
            barrier.wait(timeout=5)
            app_module._submit_job(str(index))
        except Exception as exc:
            with guard:
                failures.append(exc)

    monkeypatch.setattr(app_module, "ThreadPoolExecutor", make_executor)
    monkeypatch.setattr(app_module, "_execute_job", callback)
    threads = [threading.Thread(target=submit, args=(index,)) for index in range(8)]
    try:
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        assert constructor_started.wait(5)
        # Under the old code, another entrant can begin constructing a second
        # executor while the first is deliberately held. The fixed lock blocks
        # all entrants until registration completes.
        assert not second_constructor_started.wait(0.2)
        release_constructor.set()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()
        assert first_callback_started.wait(5)
        with guard:
            assert constructors["count"] == 1 and active["maximum"] == 1
    finally:
        release_constructor.set()
        release_callbacks.set()
        for thread in threads:
            thread.join(timeout=5)
        for executor in executors:
            executor.shutdown(wait=True)
    assert not failures
    assert set(observed) == set(map(str, range(8))) and len(observed) == 8
    assert active["maximum"] == 1 and active["current"] == 0
    assert app.extensions["c0_job_pending"] == set()

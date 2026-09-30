import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import zipfile

import pytest
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "v1.2-xml-experiment" / "res" / "app" / "webapp"
APP_DIR = WEBAPP.parent
sys.path.insert(0, str(WEBAPP))
sys.path.insert(0, str(APP_DIR))

from app import app  # noqa: E402
import app as app_module  # noqa: E402
from job_service import JobService  # noqa: E402


def make_docx() -> bytes:
    buf = io.BytesIO()
    document = Document()
    document.add_paragraph("C0 validator fixture")
    document.save(buf)
    return buf.getvalue()


def corrupt_document_xml(path: Path) -> None:
    replacement = path.with_suffix(".broken.docx")
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(replacement, "w") as target:
        for info in source.infolist():
            target.writestr(info, b"<w:document" if info.filename == "word/document.xml"
                            else source.read(info.filename))
    replacement.replace(path)


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, RESULT_ROOT=tmp_path / "results",
                      C0_DISABLE_JOB_SUBMISSION=True,
                      C0_RUN_JOBS_SYNCHRONOUSLY=False,
                      C0_FORCE_FALLBACK_REASON=None)
    app.config.pop("OPEN_FOLDER", None)
    return app.test_client()


def post_one(client, name="课件.docx", content=None):
    form = {key: value for key, value in {
        "subject": "数学", "grade": "七年级", "handout_type": "课时讲义",
        "academic_year": "2026", "template_type": "class",
        "split_mode": "smart", "docx_mode": "auto",
    }.items()}
    form["files"] = (io.BytesIO(content or make_docx()), name)
    return client.post("/api/jobs", data=form, content_type="multipart/form-data")


def test_post_persists_single_docx_and_get_recovers_after_service_restart(client, tmp_path):
    response = post_one(client)
    assert response.status_code == 202
    created = response.get_json()
    assert created["status"] == "queued"
    assert isinstance(created["created_at"], (int, float))
    assert isinstance(created["updated_at"], (int, float))
    assert created["created_at_iso"].endswith("+00:00")
    assert created["total"] == 2
    assert created["has_result"] is False
    assert created["download_available"] is False
    root = tmp_path / "results"
    record_path = root / created["job_id"] / "job.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert Path(record["source_path"]).read_bytes() == make_docx()
    assert Path(record["result_dir"]) == record_path.parent
    assert record["options"]["template_type"] == "class"
    assert record["options"]["handoutType"] == "课时讲义"

    # A fresh service instance simulates process restart; it reads disk state.
    restarted = JobService(root)
    assert restarted.get(created["job_id"])["status"] == "queued"
    assert [item["job_id"] for item in restarted.list()] == [created["job_id"]]
    assert client.get("/api/jobs/" + created["job_id"]).get_json()["status"] == "queued"


def test_upload_rejects_multiple_files_zip_and_non_docx(client):
    one = make_docx()
    multi = client.post("/api/jobs", data={"files": [(io.BytesIO(one), "a.docx"),
                                                        (io.BytesIO(one), "b.docx")]},
                        content_type="multipart/form-data")
    assert multi.status_code == 415
    assert "多文件" in multi.get_json()["error"]
    assert post_one(client, "source.zip", one).status_code == 415
    assert post_one(client, "source.docx", b"not a package").status_code == 415
    assert list((Path(app.config["RESULT_ROOT"])).glob("*/job.json")) == []


def test_open_route_resolves_and_opens_result_folder(client, tmp_path):
    opened = []
    app.config["OPEN_FOLDER"] = lambda folder: opened.append(folder)
    created = post_one(client).get_json()
    response = client.get("/api/open/" + created["job_id"])
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["result_dir"] == str((tmp_path / "results" / created["job_id"]).resolve())
    assert opened == [Path(payload["result_dir"])]
    assert client.get("/api/open/" + "0" * 32).status_code == 404


def test_download_not_ready_is_conflict_and_does_not_change_generation_state(client):
    created = post_one(client).get_json()
    response = client.get("/api/download/" + created["job_id"])
    assert response.status_code == 409
    assert response.get_json()["generation_status"] == "queued"
    assert client.get("/api/jobs/" + created["job_id"]).get_json()["status"] == "queued"


def test_complete_job_uses_frozen_package_validator_and_downloads_role_outputs(client):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    outputs = [job_dir / "教师版.docx", job_dir / "学生版.docx"]
    for path in outputs:
        path.write_bytes(make_docx())
    service = JobService(Path(app.config["RESULT_ROOT"]))
    completed = service.complete_job(created["job_id"], outputs[0], outputs[1])
    assert completed["status"] == "done"
    assert set(completed["package_validation"]) == {"teacher", "student"}
    assert all(report["valid"] for report in completed["package_validation"].values())
    assert completed["output_roles"] == {"teacher": str(outputs[0]), "student": str(outputs[1])}
    response = client.get("/api/download/" + created["job_id"])
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert set(archive.namelist()) == {"教师版.docx", "学生版.docx"}
    snapshot = client.get("/api/jobs/" + created["job_id"]).get_json()
    assert snapshot["status"] == "done"
    assert snapshot["download_available"] is True
    restarted = JobService(Path(app.config["RESULT_ROOT"]))
    recovered = restarted.get(created["job_id"])
    assert recovered["result_dir"] == str(job_dir)
    assert recovered["output_paths"] == [str(path) for path in outputs]
    assert recovered["download_available"] is True
    assert recovered["delivery_status"] == "zip_ready"
    assert recovered["created_at"] == created["created_at"]


def test_zip_delivery_failure_does_not_fail_validated_local_generation(client, monkeypatch):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    outputs = [job_dir / "教师版.docx", job_dir / "学生版.docx"]
    for path in outputs:
        path.write_bytes(make_docx())
    JobService(Path(app.config["RESULT_ROOT"])).complete_job(created["job_id"], *outputs)

    original_zip = app_module.zipfile.ZipFile

    def fail_zip(file, *args, **kwargs):
        if hasattr(file, "write"):
            raise OSError("simulated response archive failure")
        return original_zip(file, *args, **kwargs)

    monkeypatch.setattr(app_module.zipfile, "ZipFile", fail_zip)
    response = client.get("/api/download/" + created["job_id"])
    assert response.status_code == 503
    assert response.get_json()["error_code"] == "DELIVERY_DOWNLOAD_FAILED"
    snapshot = client.get("/api/jobs/" + created["job_id"]).get_json()
    assert snapshot["status"] == "done"
    assert snapshot["has_result"] is True
    assert snapshot["result_dir"] == str(job_dir.resolve())
    assert snapshot["output_paths"] == [str(path.resolve()) for path in outputs]
    assert snapshot["download_available"] is False
    assert snapshot["delivery_status"] == "failed"
    assert snapshot["delivery_error_code"] == "DELIVERY_DOWNLOAD_FAILED"


def test_student_plan_unsupported_uses_fallback_without_stale_teacher_summary(
        client, tmp_path, monkeypatch):
    import shutil
    import renderer_orchestrator
    import template_block_plan

    root = tmp_path / "results"
    app.config.update(C0_DISABLE_JOB_SUBMISSION=False,
                      C0_RUN_JOBS_SYNCHRONOUSLY=True)
    engine = SimpleNamespace(make_student=lambda source, target: shutil.copyfile(source, target),
                             CLASS_TEMPLATE="unused-class-template.docx",
                             DEFAULT_TEMPLATE="unused-1v1-template.docx")
    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine", lambda: engine)
    teacher_plan = SimpleNamespace(template_sha256="teacher-template", blocks=(), units=(), target=None)
    plan_calls = 0

    def build_plan(*_args, **_kwargs):
        nonlocal plan_calls
        plan_calls += 1
        if plan_calls == 1:
            return teacher_plan
        raise template_block_plan.PlanUnsupported("student source unsupported")

    monkeypatch.setattr(template_block_plan, "build_template_block_plan", build_plan)
    fallback_observed = {}

    def successful_fallback(job, reason):
        record = JobService(root).list()[0]
        fallback_observed.update({
            "renderer": record["renderer"],
            "fallback_reason": record["fallback_reason"],
            "baseline_sha": record["baseline_sha"],
            "reason_arg": reason,
            "plan_summary": record.get("plan_summary"),
        })
        outputs = [Path(job.output_doc), Path(job.student_output_doc)]
        for output in outputs:
            output.write_bytes(make_docx())
        return {"output_paths": [str(path) for path in outputs], "whole_job": True,
                "baseline_sha": renderer_orchestrator.V09_BASELINE_SHA}

    monkeypatch.setattr(renderer_orchestrator, "render_v09_whole_job", successful_fallback)
    response = post_one(client)
    assert response.status_code == 202
    job_id = response.get_json()["job_id"]
    final = JobService(root).get(job_id)
    assert plan_calls == 2
    assert fallback_observed == {
        "renderer": "V0.9",
        "fallback_reason": "XML_RENDER_FAILED",
        "baseline_sha": renderer_orchestrator.V09_BASELINE_SHA,
        "reason_arg": "XML_RENDER_FAILED",
        "plan_summary": None,
    }
    assert final["status"] == "done"
    assert final["renderer"] == "V0.9"
    assert final["fallback_reason"] == "XML_RENDER_FAILED"
    assert final["baseline_sha"] == renderer_orchestrator.V09_BASELINE_SHA
    assert final.get("plan_summary") is None
    assert len(final["output_paths"]) == 2
    assert all(Path(path).is_file() for path in final["output_paths"])


def test_failed_fallback_attempt_is_persisted_before_runtime_failure(client, tmp_path, monkeypatch):
    import shutil
    import renderer_orchestrator

    root = tmp_path / "results"
    app.config.update(C0_DISABLE_JOB_SUBMISSION=False,
                      C0_RUN_JOBS_SYNCHRONOUSLY=True,
                      C0_FORCE_FALLBACK_REASON="UNSUPPORTED_REVISION_MARKUP")
    engine = SimpleNamespace(make_student=lambda source, target: shutil.copyfile(source, target),
                             CLASS_TEMPLATE="unused-class-template.docx",
                             DEFAULT_TEMPLATE="unused-1v1-template.docx")
    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine", lambda: engine)
    observed = {}

    def fail_fallback(_job, reason):
        record = JobService(root).list()[0]
        observed.update({"renderer": record["renderer"],
                         "fallback_reason": record["fallback_reason"],
                         "baseline_sha": record["baseline_sha"],
                         "reason_arg": reason})
        raise RuntimeError("simulated whole-job fallback failure")

    monkeypatch.setattr(renderer_orchestrator, "render_v09_whole_job", fail_fallback)
    response = post_one(client)
    job_id = response.get_json()["job_id"]
    final = JobService(root).get(job_id)
    expected = renderer_orchestrator.V09_BASELINE_SHA
    assert observed == {"renderer": "V0.9",
                        "fallback_reason": "UNSUPPORTED_REVISION_MARKUP",
                        "baseline_sha": expected,
                        "reason_arg": "UNSUPPORTED_REVISION_MARKUP"}
    assert final["status"] == "error"
    assert final["renderer"] == "V0.9"
    assert final["fallback_reason"] == "UNSUPPORTED_REVISION_MARKUP"
    assert final["baseline_sha"] == expected


def test_plan_summary_is_only_published_for_successful_paired_xml_plans(
        client, tmp_path, monkeypatch):
    import shutil
    import renderer_orchestrator
    import template_block_plan
    import renderer_xml_minimal

    root = tmp_path / "results"
    app.config.update(C0_DISABLE_JOB_SUBMISSION=False,
                      C0_RUN_JOBS_SYNCHRONOUSLY=True)
    engine = SimpleNamespace(make_student=lambda source, target: shutil.copyfile(source, target),
                             CLASS_TEMPLATE="unused-class-template.docx",
                             DEFAULT_TEMPLATE="unused-1v1-template.docx")
    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine", lambda: engine)
    plan = SimpleNamespace(template_sha256="paired-template", template_path="unused-template.docx",
                           blocks=(), units=(), target=None)
    monkeypatch.setattr(template_block_plan, "build_template_block_plan",
                        lambda *_args, **_kwargs: plan)

    def render(_source, _template, _blocks, output, _target):
        Path(output).write_bytes(make_docx())
        return SimpleNamespace(output_path=str(output), resource_report={"unsupported": []},
                               package_report={"valid": True, "errors": []})

    monkeypatch.setattr(renderer_xml_minimal, "render_minimal", render)
    response = post_one(client)
    job_id = response.get_json()["job_id"]
    final = JobService(root).get(job_id)
    assert final["status"] == "done", final.get("error")
    assert final["renderer"] == "XML"
    assert final["plan_summary"] == {
        "destination_slot": "main_content",
        "teacher_units": 0,
        "student_units": 0,
        "teacher_blocks": 0,
        "student_blocks": 0,
        "template_sha256": "paired-template",
    }


def test_restart_reconciles_done_job_when_a_final_docx_is_missing(client):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    teacher = job_dir / "教师版.docx"
    student = job_dir / "学生版.docx"
    teacher.write_bytes(make_docx())
    student.write_bytes(make_docx())
    service = JobService(Path(app.config["RESULT_ROOT"]))
    service.complete_job(created["job_id"], teacher, student)
    student.unlink()
    recovered = service.get(created["job_id"])
    assert recovered["status"] == "error"
    assert recovered["download_available"] is False
    assert recovered["has_result"] is False


def test_duplicate_role_path_never_completes_job(client):
    created = post_one(client).get_json()
    output = Path(app.config["RESULT_ROOT"]) / created["job_id"] / "教师版.docx"
    output.write_bytes(make_docx())
    service = JobService(Path(app.config["RESULT_ROOT"]))
    with pytest.raises(ValueError, match="different files"):
        service.complete_job(created["job_id"], output, output)
    assert service.get(created["job_id"])["status"] == "queued"
    assert service.get(created["job_id"])["has_result"] is False


def test_corrupt_document_xml_is_rejected_on_complete_recovery_and_download(client):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    teacher, student = job_dir / "教师版.docx", job_dir / "学生版.docx"
    teacher.write_bytes(make_docx())
    student.write_bytes(make_docx())
    service = JobService(Path(app.config["RESULT_ROOT"]))
    corrupt_document_xml(student)
    with pytest.raises(ValueError, match="package validation failed"):
        service.complete_job(created["job_id"], teacher, student)
    assert service.get(created["job_id"])["status"] == "queued"
    student.write_bytes(make_docx())
    service.complete_job(created["job_id"], teacher, student)
    corrupt_document_xml(student)
    recovered = service.get(created["job_id"])
    assert recovered["status"] == "error"
    assert recovered["has_result"] is False
    assert recovered["download_available"] is False
    response = client.get("/api/download/" + created["job_id"])
    assert response.status_code == 409
    assert response.status_code != 200


def test_workspace_javascript_handles_queued_and_running_states():
    js = (WEBAPP / "static" / "workspace.js").read_text(encoding="utf-8")
    assert 'function isActiveStatus(status) { return status === "queued" || status === "running"; }' in js
    assert "if (isActiveStatus(job.status)) state.pollTimer" in js
    assert 'job.status === "queued" ? "排队中"' in js
    assert 'localStorage.setItem("handout_current_job", response.job_id)' in js
    template = (WEBAPP / "templates" / "index.html").read_text(encoding="utf-8")
    assert '<option value="queued">排队中</option>' in template
    assert 'id="resultDelivery"' in template
    assert 'id="openResult"' in template and "打开成品文件夹" in template
    assert "本地输出路径：" in js and "下载 ZIP" in template


def test_semantic_facade_hashes_one_source_snapshot_and_returns_same_units():
    from semantic_facade import analyze_source, PREDICTOR_PATH

    source = make_docx()
    snapshot = analyze_source(source)
    assert snapshot.source_sha256 == __import__("hashlib").sha256(source).hexdigest()
    # Identity and semantic-unit shape are stable against the authoritative
    # predictor directly; the facade does not implement new rules.
    spec = importlib.util.spec_from_file_location("test_authoritative_predictor", PREDICTOR_PATH)
    predictor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predictor)
    expected_index, expected_units = predictor.predict(snapshot.document)
    assert snapshot.node_index.order_ids == expected_index.order_ids
    assert snapshot.node_index.order_ids
    assert snapshot.units == expected_units
    assert isinstance(snapshot.units, list)

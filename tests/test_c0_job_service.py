import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "v1.2-xml-experiment" / "res" / "app" / "webapp"
APP_DIR = WEBAPP.parent
sys.path.insert(0, str(WEBAPP))
sys.path.insert(0, str(APP_DIR))

from app import app  # noqa: E402
from job_service import JobService  # noqa: E402


def make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>内容</w:t></w:r></w:p><w:sectPr/></w:body></w:document>")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, RESULT_ROOT=tmp_path / "results")
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


def test_download_zips_teacher_and_student_without_changing_job_status(client):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    outputs = [job_dir / "教师版.docx", job_dir / "学生版.docx"]
    for path in outputs:
        path.write_bytes(make_docx())
    record_path = job_dir / "job.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update(status="done", output_paths=[str(path) for path in outputs],
                  result_dir=str(job_dir), download_available=True, has_result=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
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


def test_restart_reconciles_done_job_when_a_final_docx_is_missing(client):
    created = post_one(client).get_json()
    job_dir = Path(app.config["RESULT_ROOT"]) / created["job_id"]
    teacher = job_dir / "教师版.docx"
    student = job_dir / "学生版.docx"
    teacher.write_bytes(make_docx())
    student.write_bytes(make_docx())
    record_path = job_dir / "job.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update(status="done", output_paths=[str(teacher), str(student)],
                  download_available=True, has_result=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    student.unlink()
    recovered = JobService(Path(app.config["RESULT_ROOT"])).get(created["job_id"])
    assert recovered["status"] == "error"
    assert recovered["download_available"] is False
    assert recovered["has_result"] is False


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

"""Synthetic coverage for the C3.5 hardening harness helpers.

These cases never start COM or touch the real corpus; the real stress,
stability and recovery evidence is produced by the harness itself.
"""
from pathlib import Path
import json
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
HARDEN = ROOT / "tools" / "c35_hardening"
sys.path.insert(0, str(HARDEN))
sys.path.insert(0, str(APP))

from run_hardening import (_result_inventory, case_traversal, make_empty_zip_docx,  # noqa: E402
                           make_minimal_docx, make_mixed_zip, make_nested_chinese_zip,
                           make_traversal_zip, FORBIDDEN_NAMES)
from job_service import JobService  # noqa: E402


def synthetic_source(name="合成专题 教师版.docx"):
    return (name, make_minimal_docx(["知识精讲", "本节知识点：加法运算", "1．求 2+3 的值？", "【答案】5"]))


def test_minimal_docx_is_a_valid_package():
    data = make_minimal_docx(["第一段"])
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as package:
        assert "word/document.xml" in package.namelist()


def test_empty_zip_docx_lacks_the_main_part():
    data = make_empty_zip_docx()
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as package:
        assert "word/document.xml" not in package.namelist()


def test_nested_and_mixed_archives_keep_members():
    source_name, source_data = synthetic_source()
    name, payload = make_nested_chinese_zip([("资料/子目录/" + source_name, source_data)])
    assert name.endswith(".zip")
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as package:
        assert any(member.startswith("资料/") for member in package.namelist())
    name, payload = make_mixed_zip([synthetic_source(), ("损坏 教师版.docx", b"broken")])
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as package:
        assert package.testzip() is None
        assert len(package.namelist()) == 2


def test_path_traversal_member_is_rejected_and_writes_nothing(tmp_path):
    source = synthetic_source()
    with zipfile.ZipFile(__import__("io").BytesIO(make_traversal_zip(source)[1])) as package:
        assert any(".." in member for member in package.namelist())
    report = case_traversal(tmp_path)
    assert report["http_status"] == 415
    assert "UNSAFE_ZIP_PATH" in report["json"]["error"]
    assert report["files_written_outside"] == []
    assert not list((tmp_path / "results").rglob("*docx"))


def test_restart_requeues_running_job_and_clears_only_private_intermediates(tmp_path):
    runtime = tmp_path / "runtime"
    results = tmp_path / "results"
    job_id = "a4b8821146f448f98de6f41a04597d8d"
    work = runtime / job_id / "work"
    work.mkdir(parents=True)
    input_docx = work / "input-1.docx"
    input_docx.write_bytes(b"source")
    stale = [
        work / ("teacher-output-%s.docx" % job_id),
        work / ("student-stage-%s.docx" % job_id),
        work / (".teacher-output-%s.v09-student-0123456789abcdef0123456789abcdef.docx" % job_id),
        work / (".teacher-output-%s.xml-stage-0123456789abcdef0123456789abcdef.docx" % job_id),
    ]
    for path in stale:
        path.write_bytes(b"incomplete scratch")
    published = results / "批量讲义" / "专题01" / "专题01 学生版.docx"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"completed sibling")
    record = {"job_id": job_id, "status": "running", "progress": 1,
              "result_dir": str(published.parent), "items": [], "output_paths": []}
    (runtime / job_id / "job.json").write_text(json.dumps(record), encoding="utf-8")

    recovered = JobService(results, runtime_root=runtime).get(job_id)

    assert recovered["status"] == "queued"
    assert recovered["recovered_after_restart"] is True
    assert input_docx.read_bytes() == b"source"
    assert published.read_bytes() == b"completed sibling"
    assert all(not path.exists() for path in stale)


def test_result_inventory_flags_internal_artifacts(tmp_path):
    clean = tmp_path / "results" / "函数专题"
    clean.mkdir(parents=True)
    (clean / "函数专题 教师版.docx").write_bytes(b"x")
    (clean / "函数专题 学生版.docx").write_bytes(b"x")
    inventory = _result_inventory(tmp_path / "results")
    assert inventory["file_count"] == 2 and inventory["docx_count"] == 2
    assert inventory["non_docx"] == [] and inventory["underscore_names"] == []

    dirty = tmp_path / "results" / "脏专题"
    dirty.mkdir(parents=True)
    (dirty / "job.json").write_text("{}", encoding="utf-8")
    (dirty / "teacher-stage-abc.docx").write_bytes(b"x")
    (dirty / "输出.zip").write_bytes(b"x")
    inventory = _result_inventory(tmp_path / "results")
    assert inventory["file_count"] == 5
    flagged = (set(inventory["non_docx"]) | set(inventory["underscore_names"])
               | set(inventory["internal_artifacts"]))
    assert {"job.json", "teacher-stage-abc.docx", "输出.zip"} <= flagged
    assert set(FORBIDDEN_NAMES) & {"job.json"}


def test_delivery_scan_reports_no_violations_for_clean_outputs(tmp_path):
    """A clean run directory must contain only natural DOCX names."""
    from run_hardening import case_delivery
    run_root = tmp_path / "run-x" / "results" / "函数专题"
    run_root.mkdir(parents=True)
    (run_root / "函数专题 教师版.docx").write_bytes(b"x")
    (tmp_path / "run-x" / "runtime").mkdir(parents=True)
    report = case_delivery(tmp_path)
    assert report["violation_count"] == 0
    assert report["checked_files"] == 1

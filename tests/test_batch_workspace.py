"""Executed JS/DOM state tests; real browser/product UAT is a separate C2 gate."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "v1.2-xml-experiment" / "res" / "app" / "webapp"
HARNESS = Path(__file__).with_name("batch_workspace_harness.js")


def evaluate(**payload):
    node = shutil.which("node")
    assert node, "Node is required to execute the workspace JS state gate"
    completed = subprocess.run([node, str(HARNESS), str(WEBAPP / "static" / "workspace.js")],
                               input=json.dumps(payload, ensure_ascii=False), text=True,
                               encoding="utf-8", capture_output=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def batch(status="running", **changes):
    return {"job_id": "fixture", "is_batch": True, "status": status,
            "total": 3, "completed": 1, "failed": 1, "progress": 2,
            "current_topic": "专题B", "created_at": 1, "produced": 1,
            "result_dir": "C:/结果/本次任务", "has_result": True,
            "filenames": ["专题.zip"],
            "items": [
                {"topic": "专题A", "teacher": "未提供", "student": "完成", "status": "done", "renderer": "XML"},
                {"topic": "专题B", "teacher": "处理中", "student": "处理中", "status": "running", "renderer": "V0.9", "fallback_reason": "XML_RENDER_FAILED"},
                {"topic": "专题C", "teacher": "失败", "student": "失败", "status": "error", "error": "损坏 DOCX"}],
            **changes}


def test_running_batch_has_counts_current_topic_and_per_item_states():
    result = evaluate(job=batch())
    assert not result["batchHidden"]
    assert (result["total"], result["completed"], result["failed"], result["current"]) == ("3", "1", "1", "专题B")
    assert result["title"] == "正在生成" and result["percent"] == "67%"
    assert result["rows"] == [["专题A", "未提供", "完成", "XML", "成功"],
                              ["专题B", "处理中", "处理中", "fallback（V0.9）", "处理中"],
                              ["专题C", "失败", "失败", "未执行", "失败"]]
    assert result["configDisabled"] and result["startDisabled"]
    assert not result["openHidden"]


def test_partial_success_keeps_valid_local_delivery():
    result = evaluate(job=batch("partial", completed=2, failed=1, progress=3,
                                current_topic=None))
    assert result["title"] == "部分讲义已生成" and result["percent"] == "100%"
    assert "2 个专题，1 个失败" in result["delivery"]
    assert "C:/结果/本次任务" in result["delivery"] and "不受失败项影响" in result["delivery"]
    assert not result["deliveryHidden"] and not result["openHidden"]
    assert not result["downloadElements"]
    assert result["historyStatuses"] == ["部分完成"]
    assert not result["currentStored"]


def test_obsolete_download_failure_is_ignored_by_local_result_ui():
    result = evaluate(job=batch("partial", completed=2, failed=1, progress=3,
                                delivery_error_code="DELIVERY_DOWNLOAD_FAILED"))
    assert result["title"] == "部分讲义已生成" and not result["openHidden"]
    assert "ZIP" not in result["delivery"] and not result["downloadElements"]
    assert "生成未完成" not in result["delivery"]


def test_all_failed_batch_has_no_success_delivery_actions():
    result = evaluate(job=batch("error", completed=0, failed=3, progress=3,
                                current_topic=None, has_result=False, produced=0))
    assert result["title"] == "全部专题生成失败"
    assert result["completed"] == "0" and result["failed"] == "3"
    assert result["deliveryHidden"] and result["openHidden"]
    assert not result["configDisabled"]


def test_single_c1_job_keeps_role_output_and_hides_batch_summary():
    result = evaluate(job={"job_id": "single", "status": "done", "total": 2, "progress": 2,
                           "has_result": True, "renderer": "XML",
                           "produced": 1, "items": [{"topic": "学生讲义", "teacher": "未提供", "student": "完成"}]})
    assert result["batchHidden"] and result["title"] == "讲义已生成"
    assert result["rows"] == [["学生讲义", "未提供", "完成", "XML", "成功"]]
    assert not result["openHidden"]


@pytest.mark.parametrize("mode,needle", [("auto", "可靠配对"), ("separate", "每份 DOCX 各自生成")])
def test_zip_grouping_guidance_matches_selected_mode(mode, needle):
    result = evaluate(files=["中文多层素材.zip"], mode=mode)
    assert needle in result["pairing"] and "临时文件会忽略" in result["pairing"]
    assert "尚未开放" not in result["pairing"]


@pytest.mark.parametrize("mode,needle", [("auto", "按专题名称配对"), ("separate", "每份 DOCX 各自生成")])
def test_multiple_docx_guidance_matches_selected_mode(mode, needle):
    result = evaluate(files=["A教师版.docx", "B学生版.docx", "C教师用.docx"], mode=mode)
    assert needle in result["pairing"]


def test_c1_two_file_auto_pair_keeps_supplied_student_priority():
    result = evaluate(files=["函数教师版.docx", "函数学生版.docx"])
    assert "已有学生版优先使用，不会再次去答案" in result["pairing"]
    separate = evaluate(files=["函数教师版.docx", "函数学生版.docx"], mode="separate")
    assert "请使用“按专题配对”" in separate["pairing"]


def test_multifile_submission_sends_all_docx_and_zip_inputs():
    names = ["函数 教师版.docx", "函数 学生版.docx", "中文素材.zip"]
    result = evaluate(files=names, submitResponse=batch("queued", completed=0, failed=0,
                                                       progress=0, has_result=False, items=[]))
    assert result["requests"] == [{"url": "/api/jobs", "files": names}]
    assert result["title"] == "任务排队中" and result["currentStored"]


def test_partial_history_filter_retains_partial_batch():
    done = {"job_id": "other", "status": "done", "items": []}
    result = evaluate(job=batch("partial"), extraJobs=[done], historyFilter="partial")
    assert result["historyStatuses"] == ["部分完成"]


def test_open_folder_is_primary_and_file_control_supports_batch():
    html = (WEBAPP / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="fileInput" accept=".zip,.docx" multiple' in html
    assert 'class="primary-button" id="openResult"' in html
    assert 'id="downloadResult"' not in html
    assert "下载 ZIP" not in html
    assert all(label in html for label in ("总数", "已完成", "失败数", "当前处理专题", "生成方式"))

# -*- coding: utf-8 -*-
"""Flash 1.2 workbench HTTP shell and durable C0 job boundary."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
import os
import sys
import threading
import zipfile

from flask import Flask, jsonify, render_template, request, send_file


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from job_service import JobNotFound, JobService, UnsupportedInput  # noqa: E402


app = Flask(__name__)
app.config.setdefault("RESULT_ROOT", Path.home() / "Desktop" / "生成讲义结果")
app.config.setdefault("C0_RUN_JOBS_SYNCHRONOUSLY", False)
app.config.setdefault("C0_FORCE_FALLBACK_REASON", None)  # integration-test hook only
app.config.setdefault("C0_DISABLE_JOB_SUBMISSION", False)


def _jobs() -> JobService:
    root = Path(app.config["RESULT_ROOT"]).expanduser().resolve()
    opener = app.config.get("OPEN_FOLDER")
    services = app.extensions.setdefault("c0_job_services", {})
    key = (str(root), id(opener) if opener is not None else None)
    if key not in services:
        services[key] = JobService(root, opener=opener)
    return services[key]


def _submit_job(job_id: str) -> None:
    if app.config.get("C0_DISABLE_JOB_SUBMISSION"):
        return
    if app.config.get("C0_RUN_JOBS_SYNCHRONOUSLY"):
        _execute_job(job_id)
        return
    lock = app.extensions.setdefault("c0_job_submit_lock", threading.Lock())
    pending = app.extensions.setdefault("c0_job_pending", set())
    with lock:
        if job_id in pending:
            return
        pending.add(job_id)
    executor = app.extensions.get("c0_job_executor")
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="c0-render")
        app.extensions["c0_job_executor"] = executor
    executor.submit(_run_scheduled_job, job_id)


def _run_scheduled_job(job_id: str) -> None:
    try:
        _execute_job(job_id)
    finally:
        lock = app.extensions.get("c0_job_submit_lock")
        pending = app.extensions.get("c0_job_pending", set())
        if lock is not None:
            with lock:
                pending.discard(job_id)


def _resume_queued_jobs(records) -> None:
    for record in records:
        if record.get("status") == "queued":
            _submit_job(record["job_id"])


def _execute_job(job_id: str) -> None:
    """Run one durable teacher/student job; only validated outputs become done."""
    from renderer_orchestrator import (
        RenderJob, V09_BASELINE_SHA, _load_v09_engine, render_v09_whole_job,
        render_xml_or_fallback,
    )
    from renderer_xml_minimal import render_minimal
    from package_validator import validate_package
    from template_block_plan import PlanUnsupported, build_template_block_plan

    service = _jobs()
    try:
        record = service.start_job(job_id)
        if record.get("status") != "running":
            return
        job_dir = Path(record["result_dir"]).resolve()
        source = Path(record["source_path"]).resolve()
        work_dir = job_dir / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        base = Path(record["filenames"][0]).stem or "讲义"
        teacher_output = job_dir / (base + "-教师版.docx")
        student_output = job_dir / (base + "-学生版.docx")
        if teacher_output.exists() or student_output.exists():
            raise FileExistsError("任务结果路径已存在，拒绝覆盖")

        options = record.get("options", {})
        template_type = options.get("template_type") or options.get("templateType") or "1v1"
        split_mode = options.get("split_mode") or options.get("splitMode") or "smart"
        if template_type not in ("1v1", "class"):
            raise ValueError("不支持的模板类型：%s" % template_type)

        service.update_progress(job_id, 0, "准备 V0.9 学生版源文件")
        student_source = work_dir / (base + "-学生版源文件.docx")
        engine = _load_v09_engine()
        engine.make_student(str(source), str(student_source))
        if not student_source.is_file() or student_source.stat().st_size == 0:
            raise RuntimeError("V0.9 make_student 未生成有效学生版源文件")

        template_path = None
        plans = {}
        student_stage = work_dir / (".%s.student-xml-%s.docx" % (base, job_id))

        def xml_preflight(_job):
            forced_reason = app.config.get("C0_FORCE_FALLBACK_REASON")
            if forced_reason:
                return {"supported": False, "reason_code": forced_reason,
                        "detail": "C0 forced unsupported integration fixture"}
            try:
                plans["teacher"] = build_template_block_plan(source, template_type,
                                                              split_mode=split_mode)
                plans["student"] = build_template_block_plan(student_source, template_type,
                                                              split_mode=split_mode)
            except PlanUnsupported as exc:
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": str(exc)}
            return {"supported": True,
                    "template_sha256": plans["teacher"].template_sha256}

        def xml_render(xml_job):
            teacher_plan, student_plan = plans["teacher"], plans["student"]
            service.update_progress(job_id, 1, "A-Line 分块完成，正在生成教师版和学生版")
            teacher_result = render_minimal(
                str(source), str(teacher_plan.template_path), list(teacher_plan.blocks),
                xml_job.output_doc, teacher_plan.target,
            )
            student_result = render_minimal(
                str(student_source), str(student_plan.template_path), list(student_plan.blocks),
                str(student_stage), student_plan.target,
            )
            package_reports = (teacher_result.package_report, student_result.package_report)
            package_errors = [error for report in package_reports
                              for error in report.get("errors", [])]
            return {
                "output_path": teacher_result.output_path,
                "student_output_path": student_result.output_path,
                "resource_report": {
                    "unsupported": (teacher_result.resource_report.get("unsupported", []) +
                                    student_result.resource_report.get("unsupported", []))
                },
                "package_report": {
                    "valid": all(report.get("valid") is True for report in package_reports),
                    "errors": package_errors,
                },
            }

        render_job = RenderJob(
            source_doc=str(source), output_doc=str(teacher_output),
            template_type=template_type, topic=base,
            grade=options.get("grade", ""), subject=options.get("subject", ""),
            handout_type=options.get("handout_type", options.get("handoutType", "")),
            student_source_doc=str(student_source), student_output_doc=str(student_output),
        )

        def fallback(original_job, reason_code):
            # This callback receives the original source and no V1.2 spans.
            # Capture locale-decoded PowerShell output from the frozen runtime;
            # replacement characters can otherwise fail when printed to GBK.
            with redirect_stdout(StringIO()):
                return render_v09_whole_job(original_job, reason_code)

        try:
            outcome = render_xml_or_fallback(
                render_job,
                xml_preflight=xml_preflight,
                xml_render=xml_render,
                fallback=fallback,
                package_validator=validate_package,
            )
            if outcome.renderer == "XML":
                if not student_stage.is_file() or student_stage.stat().st_size == 0:
                    raise RuntimeError("XML renderer did not produce the student DOCX")
                os.replace(student_stage, student_output)
            service.update_progress(job_id, 2, "验证教师版和学生版成品")
            plan_summary = None
            if plans:
                plan_summary = {
                    "destination_slot": "main_content",
                    "teacher_units": len(plans["teacher"].units),
                    "student_units": len(plans["student"].units),
                    "teacher_blocks": len(plans["teacher"].blocks),
                    "student_blocks": len(plans["student"].blocks),
                    "template_sha256": plans["teacher"].template_sha256,
                }
            service.complete_job(
                job_id, teacher_output, student_output,
                renderer=outcome.renderer,
                fallback_reason=outcome.fallback_reason,
                baseline_sha=(V09_BASELINE_SHA if outcome.renderer == "V0.9" else None),
                plan_summary=plan_summary,
            )
        finally:
            try:
                student_stage.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception as exc:
        # Remove only the known outputs from this UUID-isolated job directory.
        for candidate in job_dir.glob("*-教师版.docx") if "job_dir" in locals() else ():
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
        for candidate in job_dir.glob("*-学生版.docx") if "job_dir" in locals() else ():
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
        service.fail_job(job_id, "%s: %s" % (type(exc).__name__, exc))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/jobs")
def list_jobs():
    records = _jobs().list()
    _resume_queued_jobs(records)
    return jsonify({"jobs": records})


@app.post("/api/jobs")
def create_job():
    uploaded = request.files.getlist("files")
    if len(uploaded) != 1:
        return jsonify({"error": "当前仅支持单个 DOCX 文件；ZIP 和多文件输入暂不支持"}), 415
    file = uploaded[0]
    try:
        created = _jobs().create(file.filename or "source.docx", file.read(), request.form)
    except UnsupportedInput as exc:
        return jsonify({"error": str(exc)}), 415
    _submit_job(created["job_id"])
    return jsonify(created), 202


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    try:
        record = _jobs().get(job_id)
        if record.get("status") == "queued":
            _submit_job(job_id)
        return jsonify(record)
    except JobNotFound:
        return jsonify({"error": "找不到该任务"}), 404


@app.get("/api/open/<job_id>")
def open_result(job_id: str):
    try:
        folder = _jobs().open_result(job_id)
    except JobNotFound:
        return jsonify({"error": "找不到该任务结果目录"}), 404
    except OSError as exc:
        return jsonify({"error": "无法打开本地结果目录：%s" % exc}), 503
    return jsonify({"job_id": job_id, "result_dir": str(folder), "opened": True})


@app.get("/api/download/<job_id>")
def download_result(job_id: str):
    service = _jobs()
    try:
        record, outputs = service.outputs_for_download(job_id)
    except JobNotFound:
        return jsonify({"error": "找不到该任务"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "job_id": job_id,
                        "generation_status": record_status(service, job_id)}), 409
    try:
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for output in outputs:
                package.write(output, arcname=output.name)
        archive.seek(0)
        response = send_file(archive, mimetype="application/zip", as_attachment=True,
                             download_name="讲义成品-%s.zip" % job_id[:8])
        service.record_download_succeeded(job_id)
        return response
    except Exception as exc:
        # Download is secondary: keep the validated local DOCX job marked done.
        failed = service.record_download_failed(job_id, "%s: %s" % (type(exc).__name__, exc))
        return jsonify({
            "error": "ZIP 下载暂不可用，已生成的 DOCX 仍保存在本地结果目录",
            "error_code": "DELIVERY_DOWNLOAD_FAILED",
            "generation_status": failed.get("status"),
            "result_dir": failed.get("result_dir"),
            "output_paths": failed.get("output_paths", []),
        }), 503


def record_status(service: JobService, job_id: str) -> str:
    """Best-effort status for a not-ready delivery response; never mutates it."""
    try:
        return service.get(job_id).get("status", "unknown")
    except JobNotFound:
        return "unknown"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5128)

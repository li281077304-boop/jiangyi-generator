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
import re
import time


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from job_service import JobNotFound, JobService, UnsupportedInput  # noqa: E402


app = Flask(__name__)
app.config.setdefault("RESULT_ROOT", Path.home() / "Desktop" / "生成讲义结果")
_LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
app.config.setdefault("RUNTIME_ROOT", _LOCAL_APP_DATA / "讲义生成器" / "jobs")
app.config.setdefault("C0_RUN_JOBS_SYNCHRONOUSLY", False)
app.config.setdefault("C0_FORCE_FALLBACK_REASON", None)  # integration-test hook only
app.config.setdefault("C0_DISABLE_JOB_SUBMISSION", False)


def _jobs() -> JobService:
    root = Path(app.config["RESULT_ROOT"]).expanduser().resolve()
    runtime_root = Path(app.config["RUNTIME_ROOT"]).expanduser().resolve()
    opener = app.config.get("OPEN_FOLDER")
    services = app.extensions.setdefault("c0_job_services", {})
    key = (str(root), str(runtime_root), id(opener) if opener is not None else None)
    if key not in services:
        services[key] = JobService(root, runtime_root=runtime_root, opener=opener)
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


def _visible_output_name(options: dict, topic: str, role: str) -> str:
    fields = [options.get("academic_year"), options.get("grade"), options.get("subject"),
              topic, options.get("handout_type"), role]
    parts = []
    for field in fields:
        value = re.sub(r"[_\\/]+", " ", str(field or ""))
        value = re.sub(r"[<>:\"|?*]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .")
        if value:
            parts.append(value)
    return (" ".join(parts) or ("讲义 " + role)) + ".docx"


def _execute_job(job_id: str) -> None:
    """Run a classified teacher/student job with isolated runtime staging."""
    from renderer_orchestrator import (
        RenderJob, V09_BASELINE_SHA, _load_v09_engine, render_v09_whole_job,
        render_xml_or_fallback,
    )
    from package_validator import validate_package
    from renderer_orchestrator import FallbackRequired
    from slot_router import SlotRoutingError, build_slot_routing_plan
    from template_slot_composer import render_slots

    service = _jobs()
    result_dir = None
    try:
        record = service.start_job(job_id)
        if record.get("status") != "running":
            return
        runtime_dir = service._job_dir(job_id)
        result_dir = Path(record["result_dir"]).resolve()
        work_dir = runtime_dir / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        options = record.get("options", {})
        input_version = record.get("input_version")
        topic = (record.get("items") or [{}])[0].get("topic") or Path(record["filenames"][0]).stem or "讲义"
        teacher_source = Path(record["teacher_source_path"]).resolve() if record.get("teacher_source_path") else None
        student_source = Path(record["student_source_path"]).resolve() if record.get("student_source_path") else None
        if input_version == "TEACHER_ONLY":
            student_source = work_dir / "derived-student-source.docx"
        elif input_version not in ("TEACHER_AND_STUDENT", "STUDENT_ONLY"):
            raise ValueError("UNKNOWN_INPUT_VERSION: 不允许生成")
        if teacher_source is None and student_source is None:
            raise ValueError("没有可用于生成的教师版或学生版源文件")

        teacher_output = (result_dir / _visible_output_name(options, topic, "教师版")
                          if teacher_source else None)
        student_output = (result_dir / _visible_output_name(options, topic, "学生版")
                          if student_source else None)
        for candidate in (teacher_output, student_output):
            if candidate is not None and candidate.exists():
                raise FileExistsError("任务结果路径已存在，拒绝覆盖")

        template_type = options.get("template_type") or "1v1"
        split_mode = options.get("split_mode") or "smart"
        if template_type not in ("1v1", "class"):
            raise ValueError("不支持的模板类型：%s" % template_type)

        preparation = {"make_student_called": False, "input_version": input_version,
                       "elapsed_seconds": 0.0, "wps_com_started": False,
                       "package_valid": None, "output_package_valid": None}
        if input_version == "TEACHER_ONLY":
            service.update_progress(job_id, 0, "正在从教师版准备学生版")
            engine = _load_v09_engine()
            started = time.perf_counter()
            preparation.update({"make_student_called": True, "wps_com_started": True})
            service.update_student_preparation(job_id, preparation)
            try:
                engine.make_student(str(teacher_source), str(student_source))
            finally:
                preparation["elapsed_seconds"] = round(time.perf_counter() - started, 3)
                service.update_student_preparation(job_id, preparation)
            if not student_source.is_file() or student_source.stat().st_size == 0:
                raise RuntimeError("V0.9 make_student 未生成有效学生版源文件")
            preparation["package_valid"] = validate_package(str(student_source)).get("valid") is True
            if not preparation["package_valid"]:
                raise RuntimeError("V0.9 make_student 输出未通过 DOCX 包校验")
        elif student_source is not None:
            preparation["package_valid"] = validate_package(str(student_source)).get("valid") is True
        service.update_student_preparation(job_id, preparation)

        active_sources = {role: path for role, path in (("teacher", teacher_source),
                                                        ("student", student_source)) if path is not None}
        plans = {}
        fallback_detail = {"value": None}
        student_stage = work_dir / ("student-stage-%s.docx" % job_id)
        teacher_stage = work_dir / ("teacher-stage-%s.docx" % job_id)

        def xml_preflight(_job):
            forced_reason = app.config.get("C0_FORCE_FALLBACK_REASON")
            if forced_reason:
                return {"supported": False, "reason_code": forced_reason,
                        "detail": "forced unsupported integration fixture"}
            try:
                for role, source_path in active_sources.items():
                    plans[role] = build_slot_routing_plan(source_path, template_type,
                                                          split_mode=split_mode)
            except SlotRoutingError as exc:
                plans.clear()
                fallback_detail["value"] = "%s: %s" % (exc.reason_code, exc.detail)
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": fallback_detail["value"]}
            return {"supported": True,
                    "template_sha256": next(iter(plans.values())).template_sha256}

        def xml_render(xml_job):
            service.update_progress(job_id, 1, "结构分析完成，正在生成教学槽位")
            results = {}
            try:
                for role, source_path in active_sources.items():
                    staging = xml_job.output_doc if role == "teacher" or "teacher" not in active_sources else str(student_stage)
                    results[role] = render_slots(str(source_path), plans[role], staging)
            except SlotRoutingError as exc:
                fallback_detail["value"] = "%s: %s" % (exc.reason_code, exc.detail)
                raise FallbackRequired("XML_RENDER_FAILED", fallback_detail["value"]) from exc
            reports = [result.package_report for result in results.values()]
            primary = results.get("teacher") or results.get("student")
            return {
                "output_path": primary.output_path,
                "student_output_path": results["student"].output_path if "student" in results else None,
                "resource_report": {"unsupported": [item for result in results.values()
                                                      for item in result.resource_report.get("unsupported", [])]},
                "package_report": {"valid": all(report.get("valid") is True for report in reports),
                                   "errors": [error for report in reports
                                              for error in report.get("errors", [])]},
            }

        internal_teacher = teacher_output and work_dir / ("teacher-output-%s.docx" % job_id)
        internal_student = student_output and work_dir / ("student-output-%s.docx" % job_id)
        primary_source = teacher_source or student_source
        primary_output = internal_teacher or internal_student
        render_job = RenderJob(
            source_doc=str(primary_source), output_doc=str(primary_output),
            template_type=template_type, topic=topic,
            grade=options.get("grade", ""), subject=options.get("subject", ""),
            handout_type=options.get("handout_type", ""),
            student_source_doc=(str(student_source) if teacher_source and student_source else None),
            student_output_doc=(str(internal_student) if teacher_source and internal_student else None),
            student_only=teacher_source is None, label=("学生版" if teacher_source is None else "教师版"),
        )

        def fallback(original_job, reason_code):
            service.record_fallback_attempt(job_id, reason_code, V09_BASELINE_SHA,
                                             detail=fallback_detail["value"])
            with redirect_stdout(StringIO()):
                return render_v09_whole_job(original_job, reason_code)

        outcome = render_xml_or_fallback(
            render_job, xml_preflight=xml_preflight, xml_render=xml_render,
            fallback=fallback, package_validator=validate_package)
        if outcome.renderer == "XML":
            generated = []
            if teacher_source:
                generated.append((outcome.output_paths[0], teacher_output))
                if student_source:
                    generated.append((str(student_stage), student_output))
            else:
                generated.append((outcome.output_paths[0], student_output))
        else:
            targets = ([teacher_output, student_output] if teacher_source else [student_output])
            if len(outcome.output_paths) != len(targets):
                raise RuntimeError("Renderer outputs do not match classified input roles")
            generated = list(zip(outcome.output_paths, targets))
        for source_path, target_path in generated:
            if target_path is None or not Path(source_path).is_file() or Path(source_path).stat().st_size == 0:
                raise RuntimeError("Renderer did not produce a non-empty classified output")
            os.replace(source_path, target_path)

        if student_output:
            preparation["output_package_valid"] = validate_package(str(student_output)).get("valid") is True
        plan_summary = None
        if outcome.renderer == "XML" and plans:
            plan = next(iter(plans.values()))
            teacher_plan, student_plan = plans.get("teacher"), plans.get("student")
            plan_summary = {
                "destination_slots": {slot: {
                    "label": plan.slot_labels[slot],
                    "teacher_blocks": len(teacher_plan.slots[slot]) if teacher_plan else 0,
                    "student_blocks": len(student_plan.slots[slot]) if student_plan else 0,
                } for slot in ("knowledge", "immediate", "final")},
                "teacher_units": len(teacher_plan.units) if teacher_plan else 0,
                "student_units": len(student_plan.units) if student_plan else 0,
                "explicit_final_heading": plan.explicit_final_heading,
                "template_sha256": plan.template_sha256,
            }
        service.complete_job(
            job_id, teacher_output, student_output, renderer=outcome.renderer,
            fallback_reason=outcome.fallback_reason,
            baseline_sha=V09_BASELINE_SHA if outcome.renderer == "V0.9" else None,
            plan_summary=plan_summary, student_preparation=preparation)
    except Exception as exc:
        for candidate in result_dir.glob("*.docx") if result_dir is not None else ():
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
    if not 1 <= len(uploaded) <= 2:
        return jsonify({"error": "本轮只支持一个 DOCX，或一组教师版和学生版 DOCX"}), 415
    try:
        created = _jobs().create_inputs(
            [(file.filename or "source.docx", file.read()) for file in uploaded], request.form)
    except Exception as exc:
        from input_versions import UnknownInputVersion
        if isinstance(exc, UnknownInputVersion):
            return jsonify({"error": str(exc), "error_code": "UNKNOWN_INPUT_VERSION"}), 422
        if isinstance(exc, UnsupportedInput):
            return jsonify({"error": str(exc)}), 415
        raise
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
                             download_name=Path(record["result_dir"]).name + ".zip")
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

# -*- coding: utf-8 -*-
"""Flash 1.2 workbench HTTP shell and durable C0 job boundary."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import os
import shutil
import sys
import hashlib
import tempfile
import threading
import secrets
import uuid

from flask import Flask, jsonify, render_template, request
import re
import time


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from job_service import JobNotFound, JobService, UnsupportedInput  # noqa: E402


app = Flask(__name__)
app.config.setdefault("RESULT_ROOT", Path(os.environ.get(
    "JIANGYI_RESULT_ROOT", str(Path.home() / "Desktop" / "生成讲义结果"))))
_LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
app.config.setdefault("RUNTIME_ROOT", Path(os.environ.get(
    "JIANGYI_RUNTIME_ROOT", str(_LOCAL_APP_DATA / "讲义生成器" / "jobs"))))
app.config.setdefault("C0_RUN_JOBS_SYNCHRONOUSLY", False)
app.config.setdefault("C0_FORCE_FALLBACK_REASON", None)  # integration-test hook only
app.config.setdefault("C0_DISABLE_JOB_SUBMISSION", False)
app.config.setdefault("STUDENTIZER_EVIDENCE_PROVIDER", None)  # trusted server config only; no upload/UI API
app.config.setdefault("STUDENTIZER_REVIEWED_MANIFEST_DIR", None)  # None => packaged reviewed evidence
_V09_FALLBACK_LOCK = threading.RLock()


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
        # First submissions must share the same one-worker queue. Checking and
        # registering outside this lock could create competing COM executors.
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


def _persist_job_stage(service: JobService, job_id: str, progress: int, stage: str) -> None:
    """Persist an observable stage before entering a potentially long phase."""
    service.update_progress(job_id, progress, stage)
    hook = app.config.get("C35_TEST_STAGE_HOOK")
    if app.testing and callable(hook):
        hook(job_id, stage)


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


def _publication_temp_pattern(job_id: str) -> str:
    return ".jiangyi-publish-%s-*.tmp" % job_id


def _cleanup_publication_temps(result_dir: Path, job_id: str) -> None:
    """Remove only this job's abandoned same-volume publication copies."""
    prefix = ".jiangyi-publish-%s-" % job_id
    for candidate in result_dir.glob(_publication_temp_pattern(job_id)):
        if candidate.name.startswith(prefix) and candidate.is_file():
            candidate.unlink(missing_ok=True)


def _publish_staged_output(source_path: str | Path, target_path: str | Path, *,
                           job_id: str, role: str, expected_sha256: str,
                           package_validator) -> str:
    """Copy, validate, then atomically publish from a temp on the target volume.

    Staging may live under LocalAppData while the user's Desktop is redirected
    to another volume. Only the target-local temporary file is passed to
    ``os.replace`` so Windows never attempts a cross-volume rename.
    """
    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    if not source.is_file() or source.stat().st_size <= 0:
        raise RuntimeError("Renderer staged an empty %s artifact" % role)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=".jiangyi-publish-%s-%s-%s-" % (job_id, role, uuid.uuid4().hex),
        suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        shutil.copyfile(source, temp)
        if not temp.is_file() or temp.stat().st_size != source.stat().st_size:
            raise RuntimeError("Copied %s artifact size does not match staging" % role)
        digest = hashlib.sha256(temp.read_bytes()).hexdigest()
        if not expected_sha256 or digest != expected_sha256:
            raise RuntimeError("Copied %s artifact SHA-256 does not match publication plan" % role)
        validation = package_validator(str(temp))
        if validation.get("valid") is not True:
            raise RuntimeError("Copied %s artifact package validation failed: %s" %
                               (role, "; ".join(validation.get("errors", [])[:5])))
        os.replace(temp, target)
        return digest
    finally:
        temp.unlink(missing_ok=True)


def _reviewed_provider():
    """Resolve the teacher-only reviewed evidence provider for this process.

    Explicit server configuration wins. Otherwise the packaged reviewed
    manifest directory is used. A registry that cannot be loaded never
    authorizes anything: the provider becomes ``None`` and every item fails
    closed into the V0.9 whole-job fallback.
    """
    configured = app.config.get("STUDENTIZER_EVIDENCE_PROVIDER")
    if configured is not None:
        return configured, None, None
    from reviewed_studentizer import ReviewedManifestError, registry
    try:
        loaded = registry(app.config.get("STUDENTIZER_REVIEWED_MANIFEST_DIR"))
    except ReviewedManifestError as exc:
        return None, None, str(exc)
    return loaded.evidence_provider(), loaded, None


def _execute_job(job_id: str) -> None:
    """Run a classified teacher/student job with isolated runtime staging."""
    service = _jobs()
    if service.get(job_id).get("is_batch"):
        _execute_batch(job_id)
        return
    from renderer_orchestrator import (
        RenderJob, V09_BASELINE_SHA, _load_v09_engine, render_v09_whole_job,
        render_xml_or_fallback,
    )
    from package_validator import validate_package
    from renderer_orchestrator import FallbackRequired
    from slot_router import SlotRoutingError, build_slot_routing_plan
    from template_slot_composer import render_slots
    from studentizer_planner import prepare_complete_student

    result_dir = None
    try:
        record = service.start_job(job_id)
        if record.get("status") != "running":
            return
        runtime_dir = service._job_dir(job_id)
        result_dir = Path(record["result_dir"]).resolve()
        _cleanup_publication_temps(result_dir, job_id)
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
        template_type = options.get("template_type") or "1v1"
        split_mode = options.get("split_mode") or "smart"
        if template_type not in ("1v1", "class"):
            raise ValueError("不支持的模板类型：%s" % template_type)

        preparation = {"make_student_called": False, "input_version": input_version,
                       "elapsed_seconds": 0.0, "wps_com_started": False,
                       "student_preparation": "BYPASS", "student_preparation_route": None,
                       "com_used": False, "com_observation": "NOT_ENTERED",
                       "package_valid": None, "output_package_valid": None,
                       "engine": "BYPASS", "status": "STUDENT_SOURCE_BYPASS",
                       "reason_code": None, "reason_detail": None,
                       "reviewed_evidence": None, "registry_error": None,
                       "studentizer_fallback": False}
        studentizer_rejected = False
        if input_version == "TEACHER_ONLY":
            _persist_job_stage(service, job_id, 0, "Studentizer preparation")
            provider, reviewed, registry_error = _reviewed_provider()
            preparation["registry_error"] = registry_error
            started = time.perf_counter()
            prepared, coverage = prepare_complete_student(teacher_source, student_source, provider)
            preparation.update({"engine": prepared.engine, "status": prepared.status,
                                "reason_code": prepared.reason_code, "reason_detail": prepared.reason_detail,
                                "source_sha256": prepared.source_sha256, "output_sha256": prepared.output_sha256,
                                "coverage": coverage, "studentizer_elapsed_seconds": round(time.perf_counter()-started, 6),
                                "elapsed_seconds": round(time.perf_counter()-started, 6)})
            studentizer_rejected = prepared.status != "XML_PREPARED"
            preparation["studentizer_fallback"] = studentizer_rejected
            if studentizer_rejected:
                # Studentizer capability refusal is a preparation decision,
                # not a renderer decision. Use the frozen V0.9 preparation
                # step to create a student source, then continue through the
                # shared A-Line / Slot Router / XML Renderer route.
                _persist_job_stage(service, job_id, 0, "V0.9 make_student preparation")
                make_started = time.perf_counter()
                preparation.update({"student_preparation": "V09_MAKE_STUDENT",
                                    "student_preparation_route": "V09_MAKE_STUDENT",
                                    "preparation_error_code": None,
                                    "preparation_error_detail": None})
                service.update_student_preparation(job_id, preparation)
                try:
                    with _V09_FALLBACK_LOCK:
                        engine = _load_v09_engine()
                        original_make_student = engine.make_student

                        def observed_make_student(*args, **kwargs):
                            # The frozen callable can fail in its python-docx
                            # phase before attempting a PowerShell/COM script.
                            preparation.update({
                                "make_student_called": True,
                                "com_used": None,
                                "wps_com_started": None,
                                "com_observation": "UNKNOWN_AFTER_MAKE_STUDENT_ENTRY",
                            })
                            service.update_student_preparation(job_id, preparation)
                            return original_make_student(*args, **kwargs)

                        engine.make_student = observed_make_student
                        try:
                            engine.make_student(str(teacher_source), str(student_source))
                        finally:
                            engine.make_student = original_make_student
                except Exception as exc:
                    preparation["preparation_error_code"] = "V09_MAKE_STUDENT_FAILED"
                    preparation["preparation_error_detail"] = "%s: %s" % (type(exc).__name__, exc)
                    raise
                finally:
                    make_elapsed = round(time.perf_counter() - make_started, 6)
                    preparation.update({"make_student_elapsed_seconds": make_elapsed,
                                        "elapsed_seconds": round(
                                            preparation["studentizer_elapsed_seconds"] + make_elapsed, 6)})
                    service.update_student_preparation(job_id, preparation)
                if not student_source.is_file() or student_source.stat().st_size == 0:
                    raise RuntimeError("V0.9 make_student did not produce a non-empty student source")
                validation = validate_package(str(student_source))
                if validation.get("valid") is not True:
                    raise RuntimeError("V0.9 make_student produced an invalid student source: %s" %
                                       "; ".join(validation.get("errors", [])[:5]))
                preparation["student_source_package_valid"] = True
            else:
                preparation["package_valid"] = prepared.validation.get("valid") is True
                preparation["student_preparation"] = "XML_STUDENTIZER"
                preparation["com_used"] = False
                manifest = reviewed.lookup(prepared.source_sha256) if reviewed is not None else None
                preparation["reviewed_evidence"] = manifest.describe() if manifest is not None else None
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
            except Exception as exc:
                # Any unexpected planning refusal must still persist a reason.
                plans.clear()
                fallback_detail["value"] = "%s: %s" % (type(exc).__name__, exc)
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
            except FallbackRequired:
                raise
            except Exception as exc:
                # The renderer refused this source (for example an inherited
                # unresolvable bookmark/hyperlink target). Record the exact
                # refusal before the orchestrator falls back, so the persisted
                # fallback reason is never an unexplained blank.
                fallback_detail["value"] = "%s: %s" % (type(exc).__name__, exc)
                raise
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
            renderer_fallback_preparation = {
                "route": "V09_WHOLE_JOB", "make_student_called": False,
                "reason_code": reason_code, "reason_detail": fallback_detail["value"],
                "com_used": None, "wps_com_started": None,
                "com_observation": "NOT_ENTERED", "elapsed_seconds": None,
            }
            service.update_renderer_fallback_preparation(job_id, renderer_fallback_preparation)
            # Teacher-only fallback always starts from the original teacher,
            # even if a later renderer gate rejected a validated XML derivative.
            if input_version == "TEACHER_ONLY":
                original_job = replace(original_job, student_source_doc=None)
            with _V09_FALLBACK_LOCK:
                engine = _load_v09_engine() if input_version == "TEACHER_ONLY" else None
                original_make_student = engine.make_student if engine else None
                original_build_version = getattr(engine, "build_version", None) if engine else None

                def observed_build_version(label, *args, **kwargs):
                    role = "student" if str(label).lower().startswith("学生") else "teacher"
                    _persist_job_stage(service, job_id, 1,
                                       "V0.9 %s renderer" % role)
                    return original_build_version(label, *args, **kwargs)

                def observed_make_student(*args, **kwargs):
                    _persist_job_stage(service, job_id, 1,
                                       "V0.9 make_student preparation")
                    stamp = time.perf_counter()
                    renderer_fallback_preparation.update({
                        "make_student_called": True, "com_used": None,
                        "wps_com_started": None,
                        "com_observation": "UNKNOWN_AFTER_MAKE_STUDENT_ENTRY",
                    })
                    service.update_renderer_fallback_preparation(job_id, renderer_fallback_preparation)
                    try:
                        return original_make_student(*args, **kwargs)
                    finally:
                        renderer_fallback_preparation["make_student_elapsed_seconds"] = round(
                            time.perf_counter()-stamp, 6)
                        service.update_renderer_fallback_preparation(job_id, renderer_fallback_preparation)
                stamp = time.perf_counter()
                if engine:
                    engine.make_student = observed_make_student
                    if original_build_version is not None:
                        engine.build_version = observed_build_version
                try:
                    with redirect_stdout(StringIO()):
                        return render_v09_whole_job(original_job, reason_code)
                finally:
                    if engine:
                        engine.make_student = original_make_student
                        if original_build_version is not None:
                            engine.build_version = original_build_version
                    renderer_fallback_preparation["elapsed_seconds"] = round(time.perf_counter()-stamp, 6)
                    service.update_renderer_fallback_preparation(job_id, renderer_fallback_preparation)

        outcome = render_xml_or_fallback(
            render_job, xml_preflight=xml_preflight, xml_render=xml_render,
            fallback=fallback, package_validator=validate_package)
        if outcome.renderer == "XML":
            generated = []
            if teacher_source:
                generated.append(("teacher", outcome.output_paths[0], teacher_output))
                if student_source:
                    generated.append(("student", str(student_stage), student_output))
            else:
                generated.append(("student", outcome.output_paths[0], student_output))
        else:
            targets = ([teacher_output, student_output] if teacher_source else [student_output])
            if len(outcome.output_paths) != len(targets):
                raise RuntimeError("Renderer outputs do not match classified input roles")
            roles = (["teacher", "student"] if teacher_source else ["student"])
            generated = [(role, source, target) for role, source, target in zip(roles, outcome.output_paths, targets)]
        _persist_job_stage(service, job_id, 1, "outputs ready; before publication")
        planned_paths = {role: str(Path(target).resolve()) for role, _source, target in generated}
        staged_hashes = {role: hashlib.sha256(Path(source).read_bytes()).hexdigest()
                         for role, source, _target in generated}
        service.record_publication_plan(job_id, planned_paths, staged_hashes)
        publication = service.get(job_id).get("publication") or {}
        expected_hashes = publication.get("expected_sha256", {})
        # Validate every staged artifact before publishing any role.
        for role, source_path, target_path in generated:
            source = Path(source_path)
            if target_path is None or not source.is_file() or source.stat().st_size == 0:
                raise RuntimeError("Renderer did not produce a non-empty classified output")
            validation = validate_package(str(source))
            if validation.get("valid") is not True:
                raise RuntimeError("Renderer staged an invalid %s package: %s" %
                                   (role, "; ".join(validation.get("errors", [])[:5])))
        for role, source_path, target_path in generated:
            target = Path(target_path).resolve()
            if target.exists():
                # The unique job directory and persisted publication plan make
                # this an interrupted retry. Adopt only a complete valid DOCX;
                # never overwrite or delete an already published role.
                if not target.is_file() or target.stat().st_size == 0:
                    raise RuntimeError("Interrupted publication target is not a non-empty file")
                existing_validation = validate_package(str(target))
                if existing_validation.get("valid") is not True:
                    raise RuntimeError("Interrupted publication target failed validation")
                existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                published_record = publication.get("published", {}).get(role)
                expected_hash = (published_record or {}).get("sha256") or expected_hashes.get(role)
                if not expected_hash or existing_hash != expected_hash:
                    raise RuntimeError("Existing result path is not the persisted publication artifact")
            else:
                expected_hash = expected_hashes.get(role) or staged_hashes.get(role)
                if not expected_hash:
                    raise RuntimeError("Publication plan is missing the expected %s artifact hash" % role)
                _publish_staged_output(source_path, target, job_id=job_id, role=role,
                                       expected_sha256=expected_hash,
                                       package_validator=validate_package)
            final_validation = validate_package(str(target))
            if final_validation.get("valid") is not True:
                raise RuntimeError("Published %s package failed validation" % role)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            service.mark_publication_role(job_id, role, target, digest)
            _persist_job_stage(service, job_id, 1, "published %s; before next role" % role)

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
        # Published role DOCX files are durable progress. A failed/restarted
        # item may resume against its recorded publication plan; never clean
        # successful finals as a side effect of a later stage error.
        service.fail_job(job_id, "%s: %s" % (type(exc).__name__, exc))


def _execute_batch(job_id: str) -> None:
    """Run isolated existing C1 jobs serially, including COM preparation/fallback.

    The production executor already has a single worker. A batch never passes
    new spans to COM and never changes the renderer decision for its siblings.
    Restarted parents skip validated completed children and retain item errors.
    """
    service = _jobs()
    record = service.start_job(job_id)
    if record.get("status") != "running":
        return
    for item in record["items"]:
        if item.get("child_job_id") and item["status"] not in ("done", "error"):
            progress = service.get(job_id)["progress"]
            service.update_progress(job_id, progress, "正在处理专题：" + item["topic"],
                                    current_topic=item["topic"])
            try:
                _execute_job(item["child_job_id"])
            except Exception as exc:
                service.fail_job(item["child_job_id"], "%s: %s" % (type(exc).__name__, exc))
        # Refresh and persist the aggregate after every item; no batch-wide
        # cleanup can remove successful children.
        service.get(job_id)


@app.get("/")
def index():
    return render_template("index.html", launcher_token=app.config.get("LAUNCHER_TOKEN", ""))


@app.get("/api/launcher/ready")
def launcher_ready():
    token = app.config.get("LAUNCHER_TOKEN")
    if not token or not secrets.compare_digest(
            request.headers.get("X-Launcher-Token", ""), str(token)):
        return jsonify({"error": "not found"}), 404
    identity = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    return jsonify({"ready": True, "identity": identity})


@app.post("/api/launcher/shutdown")
def launcher_shutdown():
    token = app.config.get("LAUNCHER_TOKEN")
    shutdown = app.config.get("LAUNCHER_SHUTDOWN")
    if not token or not shutdown or not secrets.compare_digest(
            request.headers.get("X-Launcher-Token", ""), str(token)):
        return jsonify({"error": "launcher control unavailable"}), 404
    threading.Thread(target=shutdown, name="launcher-shutdown", daemon=True).start()
    return jsonify({"stopping": True})


@app.get("/api/jobs")
def list_jobs():
    records = _jobs().list()
    _resume_queued_jobs(records)
    return jsonify({"jobs": records})


@app.post("/api/jobs")
def create_job():
    uploaded = request.files.getlist("files")
    if not uploaded:
        return jsonify({"error": "请选择 DOCX 或 ZIP 文件"}), 415
    try:
        files = [(file.filename or "source.docx", file.read()) for file in uploaded]
        is_batch = len(files) > 2 or any(Path(name).suffix.lower() == ".zip" for name, _data in files)
        created = (_jobs().create_batch(files, request.form) if is_batch else
                   _jobs().create_inputs(files, request.form))
    except Exception as exc:
        from input_versions import UnknownInputVersion
        from batch_inputs import BatchInputError
        if isinstance(exc, UnknownInputVersion):
            return jsonify({"error": str(exc), "error_code": "UNKNOWN_INPUT_VERSION"}), 422
        if isinstance(exc, (UnsupportedInput, BatchInputError)):
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5128)

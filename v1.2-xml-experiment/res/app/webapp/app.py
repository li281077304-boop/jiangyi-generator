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
from lesson_metadata import (build_cover_display, read_lesson_source_lines,
                             resolve_lesson_metadata)  # noqa: E402
from disk_preflight import DiskSpaceError, check_disk_space


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
app.config.setdefault("LOCAL_OCR_MODEL_DIR", Path(os.environ.get(
    "JIANGYI_OCR_MODEL_DIR", str(APP_DIR / "ocr_models"))))
# Ordinary jobs use automatic XML degradation followed by compatibility only
# on technical XML failure. Legacy modes remain internal diagnostic seams.
_V09_FALLBACK_LOCK = threading.RLock()
_JOB_SERVICE_LOCK = threading.RLock()


def _jobs() -> JobService:
    root = Path(app.config["RESULT_ROOT"]).expanduser().resolve()
    runtime_root = Path(app.config["RUNTIME_ROOT"]).expanduser().resolve()
    opener = app.config.get("OPEN_FOLDER")
    services = app.extensions.setdefault("c0_job_services", {})
    key = (str(root), str(runtime_root), id(opener) if opener is not None else None)
    # Initialization performs restart recovery; concurrent browser requests
    # must never initialize another service while a live job is running.
    with _JOB_SERVICE_LOCK:
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


def _lesson_metadata_record(metadata, template_type: str, topic: str) -> tuple[dict, str | None]:
    cover = build_cover_display(metadata, template_type, topic=topic)
    missing = []
    if not metadata.objectives:
        missing.append("教学目标")
    if not metadata.difficulties:
        missing.append("重点难点")
    status = "UNAVAILABLE" if len(missing) == 2 else "PARTIAL" if missing else "RESOLVED"
    warning = None
    if missing:
        warning = "原文及现有规则无法可靠确定%s，已留空，请使用前补充。" % "、".join(missing)
    return ({
        "status": status,
        "objectives": metadata.objectives,
        "difficulties": metadata.difficulties,
        "full_objectives": metadata.full_objectives,
        "full_difficulties": metadata.full_difficulties,
        "objectives_source": metadata.objectives_source,
        "difficulties_source": metadata.difficulties_source,
        "objectives_reason": metadata.objectives_reason,
        "difficulties_reason": metadata.difficulties_reason,
        "cover_display": cover,
        "source": metadata.source,
        "knowledge_point_status": metadata.knowledge_point_status,
        "training_titles": list(metadata.training_titles),
        "warning": warning,
    }, warning)


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
        RenderJob, RenderOutcome, XmlUnsupportedError, V09_BASELINE_SHA, _load_v09_engine,
        render_v09_selected, render_v09_whole_job,
        render_xml_or_fallback,
    )
    from package_validator import validate_package
    from renderer_orchestrator import FallbackRequired
    from slot_router import (SlotRoutingError, analyze_source, build_slot_routing_plan,
                             classify_knowledge_point_status, cover_metadata_sequences_with_images,
                             validate_training_pair_routes)
    from canonical_pair_alignment import (PairAlignmentError, align_teacher_student,
                                          project_pair_routes)
    from template_slot_composer import render_slots, build_display_renumbering
    from studentizer_planner import prepare_complete_student

    result_dir = None
    try:
        record = service.start_job(job_id)
        if record.get("status") != "running":
            return
        queued_input_size = sum(Path(p).stat().st_size for p in
                                set((record.get('input_paths') or {}).values()))
        check_disk_space(service.runtime_root, service.result_root, queued_input_size)
        runtime_dir = service._job_dir(job_id)
        result_dir = Path(record["result_dir"]).resolve()
        _cleanup_publication_temps(result_dir, job_id)
        work_dir = runtime_dir / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        attempt = int(record.get("generation_attempts", 1))
        attempt_suffix = "" if attempt <= 1 else "-attempt-%d" % attempt
        options = record.get("options", {})
        input_version = record.get("input_version")
        topic = (record.get("items") or [{}])[0].get("topic") or Path(record["filenames"][0]).stem or "讲义"
        teacher_source = Path(record["teacher_source_path"]).resolve() if record.get("teacher_source_path") else None
        student_source = Path(record["student_source_path"]).resolve() if record.get("student_source_path") else None
        from product_integrity import (ProductIntegrityError, inspect_input_provenance,
                                       validate_product_integrity)
        source_metadata = record.get("source_provenance") or {}
        source_inspections = {}
        for role, source_path in (("teacher", teacher_source), ("student", student_source)):
            if source_path is None:
                continue
            metadata = next((value for value in source_metadata.values()
                             if Path(value.get("runtime_path", "")).resolve() == source_path), {})
            try:
                inspection = inspect_input_provenance(source_path)
            except ProductIntegrityError as exc:
                inspection = {"path": str(source_path),
                              "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                              "metrics": None, "errors": [exc.reason_code], "accepted": False,
                              "detail": exc.detail}
            source_inspections[role] = {
                **metadata, "role": role, "runtime_path": str(source_path),
                "inspection": inspection,
            }
            recorded_sha = metadata.get("sha256")
            if not recorded_sha or recorded_sha != inspection.get("sha256"):
                inspection["accepted"] = False
                inspection["errors"] = list(inspection.get("errors", []))
                inspection["errors"].append("INPUT_PROVENANCE_HASH_MISMATCH")
                inspection["detail"] = "runtime input bytes do not match the accepted upload snapshot SHA-256"
            if not inspection["accepted"]:
                service.update_product_integrity(job_id, {
                    "gate": "PRODUCT_INTEGRITY_GATE", "accepted": False,
                    "input_sources": source_inspections,
                    "errors": [{"reason_code": reason,
                                "detail": inspection.get("detail") or
                                "input may be a previously generated lecture output"}
                               for reason in inspection["errors"]],
                })
                raise ValueError("PRODUCT_INTEGRITY_GATE: %s" % ", ".join(inspection["errors"]))
        integrity_record = {"gate": "PRODUCT_INTEGRITY_GATE", "accepted": True,
                            "input_sources": source_inspections, "staged_outputs": [], "errors": []}
        service.update_product_integrity(job_id, integrity_record)
        if input_version == "TEACHER_ONLY":
            derived_name = ("derived-student-source.docx" if attempt <= 1 else
                            "derived-student-source-attempt-%d-%s.docx" % (attempt, job_id))
            student_source = work_dir / derived_name
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
        engine_mode = options.get("engine_mode") or "auto"
        if engine_mode not in ("auto", "stable_v09", "xml_restricted"):
            raise ValueError("不支持的生成引擎模式：%s" % engine_mode)
        if template_type not in ("1v1", "class"):
            raise ValueError("不支持的模板类型：%s" % template_type)

        preparation = {"make_student_called": False, "input_version": input_version,
                       "elapsed_seconds": 0.0, "wps_com_started": False,
                       "student_preparation": "BYPASS", "student_preparation_route": "BYPASS",
                       "com_used": False, "com_observation": "NOT_ENTERED",
                       "package_valid": None, "output_package_valid": None,
                       "engine": "BYPASS", "status": "STUDENT_SOURCE_BYPASS",
                       "reason_code": None, "reason_detail": None,
                       "reviewed_evidence": None, "registry_error": None,
                       "studentizer_fallback": False}
        studentizer_rejected = False
        if input_version == "TEACHER_ONLY" and engine_mode == "auto":
            provider, reviewed, registry_error = _reviewed_provider()
            started = time.perf_counter()
            prepared, coverage = prepare_complete_student(teacher_source, student_source, provider)
            preparation.update({"engine": prepared.engine, "status": prepared.status,
                                "reason_code": prepared.reason_code, "reason_detail": prepared.reason_detail,
                                "registry_error": registry_error, "coverage": coverage,
                                "elapsed_seconds": round(time.perf_counter()-started, 6)})
            if prepared.status == "XML_PREPARED":
                preparation.update({"student_preparation": "XML_STUDENTIZER",
                                    "student_preparation_route": "XML_STUDENTIZER",
                                    "package_valid": prepared.validation.get("valid") is True})
            else:
                # Unproven answer removal is not a deliverable student source.
                student_source = None
                student_output = None
                preparation.update({"student_preparation": "NOT_GENERATED_SAFETY_UNPROVEN",
                                    "student_preparation_route": "NOT_GENERATED_SAFETY_UNPROVEN"})
                service.add_warning(job_id, "仅生成教师版：无法安全确认自动去答案结果，请提供原始学生版并复核后生成。")
        elif input_version == "TEACHER_ONLY" and engine_mode == "stable_v09":
            _persist_job_stage(service, job_id, 0, "V0.9 make_student preparation")
            make_started = time.perf_counter()
            preparation.update({"engine": "V09_MAKE_STUDENT", "status": "V09_STUDENT_PREPARED",
                                "student_preparation": "V09_MAKE_STUDENT",
                                "student_preparation_route": "V09_MAKE_STUDENT",
                                "make_student_called": False, "com_used": None,
                                "wps_com_started": None, "com_observation": "NOT_ENTERED"})
            service.update_student_preparation(job_id, preparation)
            try:
                with _V09_FALLBACK_LOCK:
                    engine = _load_v09_engine()
                    original_make_student = engine.make_student

                    def observed_stable_make_student(*args, **kwargs):
                        preparation.update({"make_student_called": True, "com_used": None,
                                            "wps_com_started": None,
                                            "com_observation": "UNKNOWN_AFTER_MAKE_STUDENT_ENTRY"})
                        service.update_student_preparation(job_id, preparation)
                        return original_make_student(*args, **kwargs)

                    engine.make_student = observed_stable_make_student
                    try:
                        engine.make_student(str(teacher_source), str(student_source))
                    finally:
                        engine.make_student = original_make_student
            except Exception as exc:
                preparation.update({"preparation_error_code": "V09_MAKE_STUDENT_FAILED",
                                    "preparation_error_detail": "%s: %s" % (type(exc).__name__, exc)})
                raise
            finally:
                preparation["make_student_elapsed_seconds"] = round(time.perf_counter()-make_started, 6)
                preparation["elapsed_seconds"] = preparation["make_student_elapsed_seconds"]
                service.update_student_preparation(job_id, preparation)
            if not student_source.is_file() or student_source.stat().st_size == 0:
                raise RuntimeError("V0.9 make_student did not produce a non-empty student source")
            validation = validate_package(str(student_source))
            if validation.get("valid") is not True:
                raise RuntimeError("V0.9 make_student produced an invalid student source: %s" %
                                   "; ".join(validation.get("errors", [])[:5]))
            preparation["student_source_package_valid"] = True
        elif input_version == "TEACHER_ONLY" and engine_mode == "xml_restricted":
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
                reason = prepared.reason_code or "STUDENTIZER_UNSUPPORTED"
                detail = prepared.reason_detail or "XML Studentizer capability gate rejected input"
                preparation.update({"student_preparation": "XML_UNSUPPORTED",
                                    "student_preparation_route": "XML_UNSUPPORTED",
                                    "preparation_error_code": reason,
                                    "preparation_error_detail": detail})
                service.update_student_preparation(job_id, preparation)
                service.update_route_evidence(job_id, {
                    "renderer_route": "XML_UNSUPPORTED",
                    "renderer_reason_code": reason,
                    "renderer_reason_detail": detail,
                })
                raise XmlUnsupportedError(reason, detail)
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
        source_snapshots = {}
        source_image_evidence = {}
        original_sources = dict(active_sources)
        metadata_source = teacher_source or student_source
        metadata_lines = read_lesson_source_lines(metadata_source)
        resolved_lesson_metadata = {}
        role_lesson_metadata = {}
        display_renumbering = {}
        canonical_state = {"occurrences": None}
        fallback_detail = {"value": None, "phase": "PREFLIGHT"}
        student_stage = work_dir / ("student-stage%s-%s.docx" % (attempt_suffix, job_id))
        teacher_stage = work_dir / ("teacher-stage%s-%s.docx" % (attempt_suffix, job_id))

        def persist_lesson_metadata(knowledge_status: str) -> None:
            metadata = resolve_lesson_metadata(
                metadata_source, subject=options.get("subject", ""), topic=topic,
                knowledge_point_status=knowledge_status, source_lines=metadata_lines,
            )
            resolved_lesson_metadata.clear()
            resolved_lesson_metadata.update({
                "objectives": metadata.objectives,
                "difficulties": metadata.difficulties,
                "full_objectives": metadata.full_objectives,
                "full_difficulties": metadata.full_difficulties,
                "cover_display": build_cover_display(metadata, template_type, topic=topic),
                "source": metadata.source,
                "knowledge_point_status": knowledge_status,
                "training_titles": list(metadata.training_titles),
            })
            details, warning = _lesson_metadata_record(metadata, template_type, topic)
            if engine_mode == "auto":
                for role, role_source in active_sources.items():
                    role_metadata = resolve_lesson_metadata(
                        role_source, subject=options.get("subject", ""), topic=topic,
                        knowledge_point_status=knowledge_status,
                        source_lines=(metadata_lines if role_source == metadata_source else
                                      read_lesson_source_lines(role_source)))
                    role_details, _ = _lesson_metadata_record(role_metadata, template_type, topic)
                    role_lesson_metadata[role] = role_details
                details["by_role"] = dict(role_lesson_metadata)
            service.update_lesson_metadata(job_id, details, warning=warning)

        persist_lesson_metadata("UNKNOWN")

        def xml_preflight(_job):
            if engine_mode == "auto":
                from xml_degradation import build_degraded_plan, structural_snapshot
                from xml_source_projection import project_equivalent_textboxes
                degradation = {}
                forced_reason = app.config.get("C0_FORCE_FALLBACK_REASON")
                if forced_reason:
                    return {"supported": False, "reason_code": forced_reason,
                            "detail": "forced unsupported integration fixture"}
                for role, source_path in active_sources.items():
                    source_path, projection = project_equivalent_textboxes(
                        source_path, work_dir / ("xml-source-%s-%s.docx" % (role, job_id)))
                    active_sources[role] = source_path
                    if projection['status'] == 'PROJECTED':
                        service.update_route_evidence(job_id, {
                            'xml_source_projection': {**(service.get(job_id).get('xml_source_projection') or {}),
                                                      role: projection}})
                    preserve_only = split_mode == "full"
                    try:
                        snapshot = analyze_source(source_path)
                    except Exception:
                        snapshot = structural_snapshot(source_path)
                        preserve_only = True
                    source_snapshots[role] = snapshot
                    if not preserve_only:
                        try:
                            plans[role], degradation[role] = build_degraded_plan(
                                source_path, template_type, snapshot=snapshot, navigation_only=True)
                            continue
                        except SlotRoutingError:
                            pass
                    if not preserve_only and any(block.images for block in snapshot.document.blocks):
                        try:
                            from image_role_evidence import (get_local_ocr_recognizer,
                                                             inspect_document_images, requires_local_ocr)
                            recognizer = (get_local_ocr_recognizer(Path(app.config["LOCAL_OCR_MODEL_DIR"]))
                                          if requires_local_ocr(snapshot) else None)
                            source_image_evidence[role] = inspect_document_images(source_path, snapshot, recognizer)
                        except Exception as exc:
                            preserve_only = True
                            degradation[role] = {"image_inspection_unavailable": str(exc)}
                            service.add_warning(job_id, "图片内文字未能可靠识别，已按原文顺序完整保留，请复核。")
                    plans[role], routing = build_degraded_plan(
                        source_path, template_type, snapshot=snapshot,
                        image_role_evidence=source_image_evidence.get(role), preserve_only=preserve_only)
                    degradation[role] = {**degradation.get(role, {}), **routing}
                statuses = {classify_knowledge_point_status(snapshot, source_image_evidence.get(role))
                            for role, snapshot in source_snapshots.items()}
                persist_lesson_metadata(next(iter(statuses)) if len(statuses) == 1 else "UNKNOWN")
                display_renumbering.update({"status": "DISPLAY_RENUMBER_SKIPPED_INDEPENDENT_SOURCES",
                                           "slots": {}, "warning": "原文题号保留，未执行双版本对应重编号。"})
                service.update_route_evidence(job_id, {
                    "xml_degradation": degradation, "pair_alignment_status": "NOT_REQUIRED_NOT_VERIFIED",
                    "display_renumbering": display_renumbering,
                    "image_role_evidence": source_image_evidence})
                if len(active_sources) == 2:
                    service.add_warning(job_id, "教师版、学生版按各自原稿生成，未验证逐题对应，请使用前核对。")
                if any(value["selected_tier"] == "PRESERVATION" for value in degradation.values()):
                    service.add_warning(job_id, "部分资料无法可靠分槽，已按原文顺序完整保留，未重排题目。")
                return {"supported": True, "template_sha256": next(iter(plans.values())).template_sha256}
            try:
                fallback_detail["phase"] = "ROUTER"
                for role, source_path in active_sources.items():
                    source_snapshots[role] = analyze_source(source_path)
            except Exception as exc:
                fallback_detail["value"] = "%s: %s" % (type(exc).__name__, exc)
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": fallback_detail["value"]}
            if any(block.images for snapshot in source_snapshots.values()
                   for block in snapshot.document.blocks):
                try:
                    from image_role_evidence import (LocalOCRError, get_local_ocr_recognizer,
                                                     inspect_document_images, requires_local_ocr)
                    needs_ocr = any(requires_local_ocr(snapshot)
                                    for snapshot in source_snapshots.values())
                    recognizer = (get_local_ocr_recognizer(Path(app.config["LOCAL_OCR_MODEL_DIR"]))
                                  if needs_ocr else None)
                    for role, source_path in active_sources.items():
                        snapshot = source_snapshots[role]
                        if any(block.images for block in snapshot.document.blocks):
                            source_image_evidence[role] = inspect_document_images(
                                source_path, snapshot, recognizer)
                except LocalOCRError as exc:
                    fallback_detail["value"] = str(exc)
                    return {"supported": False, "reason_code": "LOCAL_OCR_UNAVAILABLE",
                            "detail": fallback_detail["value"]}
                except Exception as exc:
                    fallback_detail["value"] = "%s: %s" % (type(exc).__name__, exc)
                    return {"supported": False, "reason_code": "LOCAL_OCR_FAILED",
                            "detail": fallback_detail["value"]}
                service.update_route_evidence(job_id, {
                    "image_role_evidence": source_image_evidence,
                })
            statuses = {
                classify_knowledge_point_status(
                    snapshot, source_image_evidence.get(role))
                for role, snapshot in source_snapshots.items()
            }
            if len(statuses) != 1 and not ("teacher" in source_snapshots and "student" in source_snapshots):
                fallback_detail["value"] = "teacher/student knowledge-point status differs"
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": fallback_detail["value"]}
            knowledge_point_status = (classify_knowledge_point_status(
                source_snapshots["teacher"], source_image_evidence.get("teacher"))
                if "teacher" in source_snapshots else next(iter(statuses)))
            fallback_detail["phase"] = "METADATA"
            persist_lesson_metadata(knowledge_point_status)
            forced_reason = app.config.get("C0_FORCE_FALLBACK_REASON")
            if forced_reason:
                return {"supported": False, "reason_code": forced_reason,
                        "detail": "forced unsupported integration fixture"}
            fallback_detail["phase"] = "ROUTER"
            try:
                if "teacher" in active_sources and "student" in active_sources:
                    alignment = align_teacher_student(
                        source_snapshots["student"], source_snapshots["teacher"],
                        student_source_path=active_sources["student"],
                        teacher_source_path=active_sources["teacher"],
                    )
                    service.update_route_evidence(job_id, {"canonical_alignment": alignment})
                    # The student skeleton chooses each destination once;
                    # paired teacher content is projected from that map.
                    student_base = build_slot_routing_plan(
                        active_sources["student"], template_type, split_mode=split_mode,
                        snapshot=source_snapshots["student"],
                        image_role_evidence=source_image_evidence.get("student"))
                    student_block_routes = {
                        int(item["block_id"][1:]): (
                            "cover" if item["destination_slot"] is None
                            else item["destination_slot"])
                        for item in student_base.block_records
                    }
                    student_cover_nodes = {
                        int(block_id[1:]) for block_id in student_base.cover_metadata_blocks}
                    teacher_cover_nodes = set(cover_metadata_sequences_with_images(
                        source_snapshots["teacher"], source_image_evidence.get("teacher")))
                    projection = project_pair_routes(
                        source_snapshots["student"], source_snapshots["teacher"],
                        alignment, student_block_routes,
                        student_cover_nodes=student_cover_nodes,
                        teacher_cover_nodes=teacher_cover_nodes,
                        student_source_path=active_sources["student"],
                        teacher_source_path=active_sources["teacher"])
                    student_projection = {int(seq): slot for seq, slot in
                                          projection["student_block_routes"].items()}
                    teacher_projection = {int(seq): slot for seq, slot in
                                          projection["teacher_block_routes"].items()}
                    plans["student"] = build_slot_routing_plan(
                        active_sources["student"], template_type, split_mode=split_mode,
                        snapshot=source_snapshots["student"],
                        canonical_projection_routes=student_projection,
                        image_role_evidence=source_image_evidence.get("student"))
                    plans["teacher"] = build_slot_routing_plan(
                        active_sources["teacher"], template_type, split_mode=split_mode,
                        snapshot=source_snapshots["teacher"],
                        canonical_projection_routes=teacher_projection,
                        image_role_evidence=source_image_evidence.get("teacher"))
                    service.update_route_evidence(job_id, {
                        "canonical_occurrence_routes": projection["occurrences"],
                        "canonical_projection": projection,
                        "canonical_route_source": "STUDENT_PLAN_ONCE",
                    })
                    canonical_state["occurrences"] = projection["occurrences"]
                else:
                    for role, source_path in active_sources.items():
                        plans[role] = build_slot_routing_plan(
                            source_path, template_type, split_mode=split_mode,
                            snapshot=source_snapshots[role],
                            image_role_evidence=source_image_evidence.get(role))
                    if len(plans) > 1:
                        alignment = align_teacher_student(
                            source_snapshots["student"], source_snapshots["teacher"],
                            student_source_path=active_sources["student"],
                            teacher_source_path=active_sources["teacher"],
                        )
                        service.update_route_evidence(job_id, {"canonical_alignment": alignment})
            except SlotRoutingError as exc:
                plans.clear()
                fallback_detail["value"] = "%s: %s" % (exc.reason_code, exc.detail)
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": fallback_detail["value"]}
            except PairAlignmentError as exc:
                plans.clear()
                fallback_detail["value"] = "%s: %s" % (exc.reason_code, exc.detail)
                service.update_route_evidence(job_id, {"canonical_alignment": {
                    "status": "UNRESOLVED", "reason_code": exc.reason_code,
                    "detail": exc.detail, "evidence": exc.evidence,
                }})
                return {"supported": False, "reason_code": exc.reason_code,
                        "detail": fallback_detail["value"]}
            except Exception as exc:
                plans.clear()
                fallback_detail["value"] = "%s: %s" % (type(exc).__name__, exc)
                return {"supported": False, "reason_code": "XML_RENDER_FAILED",
                        "detail": fallback_detail["value"]}
            if (knowledge_point_status == "NO_KNOWLEDGE_POINT" and split_mode == "smart"
                    and canonical_state["occurrences"] is None):
                try:
                    validate_training_pair_routes(plans)
                except SlotRoutingError as exc:
                    plans.clear()
                    fallback_detail["value"] = "%s: %s" % (exc.reason_code, exc.detail)
                    return {"supported": False, "reason_code": exc.reason_code,
                            "detail": fallback_detail["value"]}
            route_plan = plans.get("teacher") or next(iter(plans.values()))
            display_renumbering.update(build_display_renumbering(
                plans, canonical_occurrences=canonical_state["occurrences"]))
            service.update_route_evidence(job_id, {
                "display_renumbering": display_renumbering,
                "training_split_strategy": getattr(route_plan, "training_split_strategy", "NOT_APPLICABLE"),
                "training_question_routes": [
                    {"question_number": number, "slot": slot}
                    for number, slot in getattr(route_plan, "training_question_routes", ())
                ],
            })
            return {"supported": True,
                    "template_sha256": next(iter(plans.values())).template_sha256}

        def xml_render(xml_job):
            fallback_detail["phase"] = "RENDER"
            service.update_route_evidence(job_id, {
                "renderer_route": "XML",
                "xml_renderer_attempted": True,
            })
            service.update_progress(job_id, 1, "结构分析完成，正在生成教学槽位")
            results = {}
            try:
                for role, source_path in active_sources.items():
                    staging = xml_job.output_doc if role == "teacher" or "teacher" not in active_sources else str(student_stage)
                    metadata = {
                        "subject": options.get("subject", ""),
                        "grade": options.get("grade", ""),
                        "topic": topic,
                        "handout_type": options.get("handout_type", ""),
                        "objectives": resolved_lesson_metadata["objectives"],
                        "difficulties": resolved_lesson_metadata["difficulties"],
                        "cover_display": resolved_lesson_metadata["cover_display"],
                    }
                    if role in role_lesson_metadata:
                        metadata.update(role_lesson_metadata[role])
                    # Keep the existing three-argument renderer seam usable by
                    # injected test doubles and compatible integrations. The
                    # production Slot Composer advertises cover_metadata.
                    import inspect
                    parameters = inspect.signature(render_slots).parameters
                    supports_metadata = ("cover_metadata" in parameters or any(
                        parameter.kind is inspect.Parameter.VAR_KEYWORD
                        for parameter in parameters.values()))
                    if supports_metadata:
                        presentation_args = {}
                        for key, value in (("display_renumbering", display_renumbering), ("source_role", role)):
                            if key in parameters or any(parameter.kind is inspect.Parameter.VAR_KEYWORD
                                                        for parameter in parameters.values()):
                                presentation_args[key] = value
                        try:
                            results[role] = render_slots(
                                str(source_path), plans[role], staging,
                                cover_metadata=metadata, **presentation_args)
                        except Exception as first_error:
                            if engine_mode != "auto":
                                raise
                            previous = service.get(job_id).get("xml_degradation", {})
                            if previous.get(role, {}).get("selected_tier") == "PRESERVATION":
                                raise
                            from xml_degradation import build_degraded_plan
                            plans[role], routing = build_degraded_plan(
                                source_path, template_type, preserve_only=True)
                            previous.setdefault(role, {}).setdefault("attempts", []).append({
                                "tier": "XML_RENDER", "status": "DEGRADED",
                                "reason_code": getattr(first_error, "reason_code", "XML_RENDER_FAILED"),
                                "detail": str(first_error)})
                            previous[role]["attempts"].extend(routing["attempts"])
                            previous[role]["selected_tier"] = "PRESERVATION"
                            service.update_route_evidence(job_id, {"xml_degradation": previous})
                            service.add_warning(job_id, "分槽渲染未能完成，已尝试按原文顺序完整保留，请复核。")
                            results[role] = render_slots(
                                str(source_path), plans[role], staging,
                                cover_metadata=metadata, **presentation_args)
                    else:
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
            page_layout = {role: result.page_layout for role, result in results.items()}
            service.update_route_evidence(job_id, {"page_layout": page_layout})
            return {
                "output_path": primary.output_path,
                "student_output_path": results["student"].output_path if "student" in results else None,
                "page_layout": page_layout,
                "resource_report": {"unsupported": [item for result in results.values()
                                                      for item in result.resource_report.get("unsupported", [])]},
                "package_report": {"valid": all(report.get("valid") is True for report in reports),
                                   "errors": [error for report in reports
                                              for error in report.get("errors", [])]},
            }

        # A process can stop after writing an internal renderer output but
        # before publication metadata is persisted.  Recovery cleanup is
        # best-effort (for example, a crashed COM host may still hold a file),
        # so every retry must render to a fresh, attempt-scoped private path.
        internal_teacher = teacher_output and work_dir / (
            "teacher-output%s-%s.docx" % (attempt_suffix, job_id))
        internal_student = student_output and work_dir / (
            "student-output%s-%s.docx" % (attempt_suffix, job_id))
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
            teacher_only_output=bool(teacher_source and student_source is None),
        )

        def fallback(original_job, reason_code):
            fallback_phase = fallback_detail.get("phase", "PREFLIGHT")
            if reason_code in ("PACKAGE_VALIDATION_FAILED", "UNSUPPORTED_RELATIONSHIP"):
                fallback_phase = "PACKAGE"
            if fallback_detail.get("value") and "could not publish validated XML output" in fallback_detail["value"]:
                fallback_phase = "PUBLISH"
            service.record_fallback_attempt(job_id, reason_code, V09_BASELINE_SHA,
                                             detail=fallback_detail["value"],
                                             phase=fallback_phase)
            renderer_fallback_preparation = {
                "route": "V09_WHOLE_JOB", "make_student_called": False,
                "fallback_phase": fallback_phase,
                "reason_code": reason_code, "reason_detail": fallback_detail["value"],
                "com_used": None, "wps_com_started": None,
                "com_observation": "NOT_ENTERED", "elapsed_seconds": None,
            }
            service.update_renderer_fallback_preparation(job_id, renderer_fallback_preparation)
            # Teacher-only fallback always starts from the original teacher,
            # even if a later renderer gate rejected a validated XML derivative.
            if input_version == "TEACHER_ONLY" and engine_mode != "auto":
                original_job = replace(original_job, student_source_doc=None)
            original_job = replace(
                original_job,
                objectives=resolved_lesson_metadata.get("objectives", ""),
                difficulties=resolved_lesson_metadata.get("difficulties", ""),
            )
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

        if engine_mode == "stable_v09":
            service.update_route_evidence(job_id, {
                "selected_engine": "V0.9", "renderer_route": "STABLE_V09",
                "xml_renderer_attempted": False, "fallback_reason_code": None,
            })
            _persist_job_stage(service, job_id, 1, "稳定模式（V0.9 引擎）生成中")
            with _V09_FALLBACK_LOCK:
                with redirect_stdout(StringIO()):
                    stable_result = render_v09_selected(render_job)
            outcome = RenderOutcome(
                "V0.9", tuple(stable_result.get("output_paths", ())),
                details={"selected_engine": "V0.9", "route": "STABLE_V09",
                         "baseline_sha": V09_BASELINE_SHA},
            )
        else:
            service.update_route_evidence(job_id, {
                "selected_engine": "XML", "renderer_route": "XML_AUTO" if engine_mode == "auto" else "XML_RESTRICTED",
                "xml_renderer_attempted": False,
            })
            outcome = render_xml_or_fallback(
                render_job, xml_preflight=xml_preflight, xml_render=xml_render,
                fallback=fallback, package_validator=validate_package,
                allow_v09_fallback=engine_mode == "auto")
        if outcome.renderer == "XML":
            generated = []
            if teacher_source:
                generated.append(("teacher", outcome.output_paths[0], teacher_output))
                if student_source:
                    generated.append(("student", str(student_stage), student_output))
            else:
                generated.append(("student", outcome.output_paths[0], student_output))
        else:
            targets = ([teacher_output] + ([student_output] if student_source else [])
                       if teacher_source else [student_output])
            if len(outcome.output_paths) != len(targets):
                raise RuntimeError("Renderer outputs do not match classified input roles")
            roles = (["teacher"] + (["student"] if student_source else [])
                     if teacher_source else ["student"])
            generated = [(role, source, target) for role, source, target in zip(roles, outcome.output_paths, targets)]

        from product_normalizer import normalize_product_docx
        normalized_generated = []
        normalization_outputs = {}
        for role, renderer_path, final_target in generated:
            normalized_path = work_dir / ("normalized-%s%s-%s.docx" %
                                          (role, attempt_suffix, job_id))
            normalization_metadata = {
                "subject": options.get("subject", ""),
                "grade": options.get("grade", ""),
                "topic": topic,
                "handout_type": options.get("handout_type", ""),
                "objectives": resolved_lesson_metadata.get("objectives", ""),
                "difficulties": resolved_lesson_metadata.get("difficulties", ""),
                "cover_display": resolved_lesson_metadata.get("cover_display", {}),
            }
            if role in role_lesson_metadata:
                normalization_metadata.update(role_lesson_metadata[role])
                missing = [label for field, label in (("objectives", "教学目标"), ("difficulties", "重点难点"))
                           if not role_lesson_metadata[role].get(field)]
                if missing:
                    service.add_warning(job_id, ("教师版" if role == "teacher" else "学生版") +
                                        "原文缺少可靠的" + "、".join(missing) + "，已留空，请使用前补充。")
            evidence = normalize_product_docx(
                renderer_path, normalized_path, template_type=template_type,
                metadata=normalization_metadata,
            )
            normalization_outputs[role] = evidence
            normalized_generated.append((role, str(normalized_path), final_target))
        generated = normalized_generated
        service.update_product_normalization(job_id, {
            "status": "NORMALIZED", "version": "V1.2_PRODUCT_NORMALIZATION_V1",
            "renderer": outcome.renderer, "outputs": normalization_outputs,
        })
        _persist_job_stage(service, job_id, 1, "outputs ready; before publication")
        integrity_reports = []
        for role, staged_path, _target in generated:
            source_for_role = original_sources[role]
            try:
                report = validate_product_integrity(
                    source_for_role, staged_path,
                    plan=plans.get(role) if outcome.renderer == "XML" else None,
                )
            except ProductIntegrityError as exc:
                report = {"gate": "PRODUCT_INTEGRITY_GATE", "accepted": False,
                          "errors": [{"reason_code": exc.reason_code, "detail": exc.detail}],
                          "warnings": [], "source_sha256": hashlib.sha256(
                              Path(source_for_role).read_bytes()).hexdigest(),
                          "output_sha256": hashlib.sha256(Path(staged_path).read_bytes()).hexdigest()}
            integrity_reports.append({"role": role, **report})
        integrity_record["staged_outputs"] = integrity_reports
        integrity_record["accepted"] = all(item["accepted"] for item in integrity_reports)
        integrity_record["errors"] = [error for item in integrity_reports for error in item["errors"]]
        integrity_record["warnings"] = [warning for item in integrity_reports for warning in item["warnings"]]
        service.update_product_integrity(job_id, integrity_record)
        if not integrity_record["accepted"]:
            codes = sorted({item["reason_code"] for item in integrity_record["errors"]})
            message = "PRODUCT_INTEGRITY_GATE: " + ", ".join(codes)
            if "PRODUCT_TEXTBOX_CONTENT_UNPROVEN" in codes:
                message = ("原文文本框中的部分正文未能完整保留，已停止交付以避免漏内容。"
                           "请保留原稿，等待修复。 " + message)
            raise ValueError(message)
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
            try:
                final_integrity = validate_product_integrity(
                    original_sources[role], target,
                    plan=plans.get(role) if outcome.renderer == "XML" else None,
                )
            except ProductIntegrityError as exc:
                final_integrity = {
                    "gate": "PRODUCT_INTEGRITY_GATE", "accepted": False,
                    "errors": [{"reason_code": exc.reason_code, "detail": exc.detail}],
                    "warnings": [], "output_sha256": digest,
                }
            final_record = {"role": role, **final_integrity}
            integrity_output_sha = (final_integrity.get("output") or {}).get("sha256") or \
                final_integrity.get("output_sha256")
            current_output_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            hash_binding_matches = (digest == expected_hash == integrity_output_sha == current_output_sha)
            if not hash_binding_matches:
                final_integrity["accepted"] = False
                final_integrity.setdefault("errors", []).append({
                    "reason_code": "PRODUCT_OUTPUT_HASH_CHANGED",
                    "detail": "publication candidate, integrity inspection, and current result bytes differ",
                })
                final_record["accepted"] = False
                final_record["errors"] = final_integrity["errors"]
            integrity_record.setdefault("final_outputs", []).append(final_record)
            if not final_integrity["accepted"]:
                integrity_record["accepted"] = False
                integrity_record["errors"].extend(final_integrity["errors"])
                service.update_product_integrity(job_id, integrity_record)
                # Remove only this job's hash-bound publication candidate. An
                # unrelated or modified result file is never deleted here.
                immediate_sha = (hashlib.sha256(target.read_bytes()).hexdigest()
                                 if target.is_file() else None)
                if (hash_binding_matches and immediate_sha == expected_hash
                        and target.is_relative_to(result_dir)):
                    target.unlink(missing_ok=True)
                codes = sorted({item["reason_code"] for item in final_integrity["errors"]})
                raise ValueError("PRODUCT_INTEGRITY_GATE_FINAL: " + ", ".join(codes))
            integrity_record["warnings"].extend(final_integrity.get("warnings", []))
            service.update_product_integrity(job_id, integrity_record)
            service.mark_publication_role(job_id, role, target, current_output_sha)
            _persist_job_stage(service, job_id, 1, "published %s; before next role" % role)

        if student_output:
            preparation["output_package_valid"] = validate_package(str(student_output)).get("valid") is True
        plan_summary = None
        if plans:
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
                "knowledge_point_status": getattr(plan, "knowledge_point_status", "UNKNOWN"),
                "omitted_slots": list(getattr(plan, "omitted_slots", ())),
                "cover_metadata_blocks": list(getattr(plan, "cover_metadata_blocks", ())),
                "training_split_strategy": getattr(plan, "training_split_strategy", "NOT_APPLICABLE"),
                "training_question_routes": [
                    {"question_number": number, "slot": slot}
                    for number, slot in getattr(plan, "training_question_routes", ())
                ],
                "routing_applied": outcome.renderer == "XML",
                "template_sha256": plan.template_sha256,
            }
        service.complete_job(
            job_id, teacher_output, student_output, renderer=outcome.renderer,
            fallback_reason=outcome.fallback_reason,
            baseline_sha=V09_BASELINE_SHA if outcome.renderer == "V0.9" else None,
            plan_summary=plan_summary, student_preparation=preparation)
    except XmlUnsupportedError as exc:
        service.update_route_evidence(job_id, {
            "renderer_route": "XML_UNSUPPORTED",
            "selected_engine": "XML",
            "renderer_reason_code": exc.reason_code,
            "renderer_reason_detail": exc.detail,
        })
        service.fail_job(job_id, "XML 模式暂不支持此文件（%s）。请手动选择“稳定模式（V0.9 引擎）”后重新提交。" % exc)
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


@app.errorhandler(500)
def internal_server_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "本地服务处理请求失败，请重新连接查看任务状态。",
                        "error_code": "LOCAL_SERVICE_ERROR"}), 500
    return error


@app.get("/api/jobs")
def list_jobs():
    records = _jobs().list()
    _resume_queued_jobs(records)
    return jsonify({"jobs": records})


@app.post("/api/jobs")
def create_job():
    try:
        # Check before accessing request.files: multipart spooling itself needs disk.
        check_disk_space(app.config['RUNTIME_ROOT'], app.config['RESULT_ROOT'], request.content_length or 0)
    except DiskSpaceError as exc:
        return jsonify(error=str(exc), error_code='INSUFFICIENT_DISK_SPACE', disk_space=exc.details), 507
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
        if isinstance(exc, DiskSpaceError):
            return jsonify(error=str(exc), error_code='INSUFFICIENT_DISK_SPACE', disk_space=exc.details), 507
        if isinstance(exc, OSError) and (exc.errno == 28 or getattr(exc, 'winerror', None) == 112):
            return jsonify(error='写入空间不足，任务未接收。请释放磁盘空间后重试。',
                           error_code='INSUFFICIENT_DISK_SPACE'), 507
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

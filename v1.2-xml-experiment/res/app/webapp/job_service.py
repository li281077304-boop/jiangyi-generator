# -*- coding: utf-8 -*-
"""File-backed job records and validated local result delivery for C0."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import threading
import uuid
import zipfile

from werkzeug.utils import secure_filename
from package_validator import validate_package
from input_versions import classify_inputs, UnknownInputVersion, InputClassification
from batch_inputs import resolve_batch


JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
FORM_FIELDS = (
    "subject", "grade", "handout_type", "academic_year", "template_type",
    "split_mode", "docx_mode",
)


class JobNotFound(KeyError):
    pass


class UnsupportedInput(ValueError):
    pass


class JobService:
    def __init__(self, result_root: str | Path, *, runtime_root: str | Path | None = None,
                 opener=None):
        self.result_root = Path(result_root).expanduser().resolve()
        self.runtime_root = (Path(runtime_root).expanduser().resolve() if runtime_root else
                             self.result_root.parent / "runtime-jobs")
        self.result_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.opener = opener or self._open_folder
        self._lock = threading.RLock()
        self._recover_interrupted_jobs()

    def _recover_interrupted_jobs(self) -> None:
        """Requeue an interrupted running job when a new service instance starts."""
        with self._lock:
            for metadata in self.runtime_root.glob("*/job.json"):
                try:
                    record = self._read_json(metadata)
                    if record.get("status") != "running":
                        continue
                    self._clear_interrupted_work(metadata.parent, record.get("job_id"))
                    now = datetime.now(timezone.utc)
                    record.update({
                        "status": "queued",
                        "progress": 0,
                        "stage": "服务重启后已重新排队",
                        "updated_at": now.timestamp(),
                        "updated_at_iso": now.isoformat(timespec="seconds"),
                        "recovered_after_restart": True,
                    })
                    self._write_json(metadata, record)
                except (OSError, ValueError, KeyError, json.JSONDecodeError):
                    continue

    @staticmethod
    def _clear_interrupted_work(job_dir: Path, job_id: str | None) -> None:
        """Remove only renderer intermediates from a job that will be rerun.

        Uploaded inputs and published result files are outside this private
        workspace and are deliberately preserved.  V0.9 can leave an output
        behind if the host process is killed between generation and publish;
        the next attempt needs fresh renderer paths.
        """
        if not job_id or not re.fullmatch(r"[0-9a-f]{32}", str(job_id)):
            return
        root = job_dir.resolve()
        work_dir = (root / "work").resolve()
        if not work_dir.is_relative_to(root) or not work_dir.is_dir():
            return

        candidates = [work_dir / "derived-student-source.docx"]
        candidates.extend(work_dir.glob("*-%s.docx" % job_id))
        candidates.extend(work_dir.glob(".*.v09-student-*.docx"))
        candidates.extend(work_dir.glob(".*.xml-stage-*.docx"))
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
                if (candidate.is_symlink() or not resolved.is_relative_to(work_dir)
                        or not resolved.is_file()):
                    continue
                resolved.unlink()
            except OSError:
                continue

    def queued_jobs(self) -> list[dict]:
        return [record for record in self.list() if record.get("status") == "queued"]

    @staticmethod
    def _open_folder(path: Path) -> None:
        if not path.is_dir():
            raise FileNotFoundError(str(path))
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif os.name == "darwin":
            import subprocess
            subprocess.Popen(["open", str(path)])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(path)])

    @staticmethod
    def validate_docx(filename: str, data: bytes) -> str:
        original = filename or "source.docx"
        if Path(original).suffix.lower() != ".docx":
            raise UnsupportedInput("当前仅支持 DOCX 文件；ZIP 和其他格式暂不支持")
        safe = secure_filename(original)
        if Path(safe).suffix.lower() != ".docx":
            safe = "source.docx"
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as package:
                names = set(package.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise UnsupportedInput("上传文件不是有效的 DOCX 包")
                if package.testzip() is not None:
                    raise UnsupportedInput("DOCX 包完整性校验失败")
        except zipfile.BadZipFile as exc:
            raise UnsupportedInput("上传文件不是有效的 DOCX 包") from exc
        return safe

    def _job_dir(self, job_id: str) -> Path:
        if not JOB_ID_RE.fullmatch(job_id or ""):
            raise JobNotFound(job_id)
        path = (self.runtime_root / job_id).resolve()
        if path.parent != self.runtime_root:
            raise JobNotFound(job_id)
        return path

    @staticmethod
    def _read_json(path: Path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        temp = path.with_suffix(".json.tmp")
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    @staticmethod
    def _display_part(value: str) -> str:
        text = re.sub(r"[_\\/]+", " ", str(value or ""))
        text = re.sub(r"[<>:\"|?*]+", " ", text)
        return re.sub(r"\s+", " ", text).strip(" .")

    @classmethod
    def _topic_name(cls, filename: str) -> str:
        topic = Path(filename).stem
        topic = re.sub(r"(?:[\s_-]*)(?:教师版|教师|老师|学生版|学生|答案版|解析版|空白版|原卷|无答案|teacher|student|answer|solution|blank)$",
                       "", topic, flags=re.I)
        return cls._display_part(topic) or "讲义"

    def _allocate_result_dir(self, options: dict, topic: str) -> Path:
        parts = [options.get("academic_year"), options.get("grade"), options.get("subject"),
                 topic, options.get("handout_type")]
        base = " ".join(filter(None, (self._display_part(part) for part in parts))) or "讲义成品"
        candidate = self.result_root / base
        suffix = 2
        while True:
            try:
                candidate.mkdir()
                return candidate.resolve()
            except FileExistsError:
                candidate = self.result_root / (base + "（%d）" % suffix)
                suffix += 1

    def create_inputs(self, files: list[tuple[str, bytes]], options: dict, *,
                      _classification: InputClassification | None = None,
                      _topic: str | None = None, _result_dir: Path | None = None,
                      _parent_job_id: str | None = None) -> dict:
        if not files or len(files) > 2:
            raise UnsupportedInput("本轮只支持一个 DOCX，或一组教师版和学生版 DOCX")
        validated = [(filename or "source.docx", self.validate_docx(filename or "source.docx", data), data)
                     for filename, data in files]
        form_options = {field: str(options.get(field, "")) for field in FORM_FIELDS}
        try:
            classification = _classification or classify_inputs(
                [(name, data) for name, _safe, data in validated], form_options["docx_mode"] or "auto")
        except UnknownInputVersion:
            raise
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        work_dir = job_dir / "work"
        work_dir.mkdir(parents=True)
        input_paths = []
        for index, (original_name, safe_name, data) in enumerate(validated):
            # Internal snapshots use opaque fixed names; original names remain
            # metadata and are not exposed in the user result directory.
            source_path = work_dir / ("input-%d.docx" % (index + 1))
            source_path.write_bytes(data)
            input_paths.append((original_name, source_path))
        now = datetime.now(timezone.utc)
        created_at = now.timestamp()
        # workspace.js history currently reads the camelCase spellings below.
        form_options.update({
            "handoutType": form_options["handout_type"],
            "academicYear": form_options["academic_year"],
            "templateType": form_options["template_type"],
            "splitMode": form_options["split_mode"],
            "docxMode": form_options["docx_mode"],
        })
        topic_source = (input_paths[classification.teacher_index][0] if classification and
                        classification.teacher_index is not None else input_paths[0][0])
        topic = _topic or self._topic_name(topic_source)
        result_dir = _result_dir or self._allocate_result_dir(form_options, topic)
        teacher_source = (str(input_paths[classification.teacher_index][1]) if classification and
                          classification.teacher_index is not None else None)
        student_source = (str(input_paths[classification.student_index][1]) if classification and
                          classification.student_index is not None else None)
        version = classification.input_version
        record = {
            "job_id": job_id,
            "parent_job_id": _parent_job_id,
            "status": "queued",
            "progress": 0,
            "total": 2,
            "stage": "任务已接收，等待生成",
            "created_at": created_at,
            "created_at_iso": now.isoformat(timespec="seconds"),
            "updated_at": created_at,
            "updated_at_iso": now.isoformat(timespec="seconds"),
            "filenames": [Path(name).name for name, _path in input_paths],
            "input_version": version,
            "input_classification_evidence": classification.evidence if classification else "ambiguous",
            "input_paths": {key: value for key, value in (
                ("teacher_source", teacher_source), ("student_source", student_source)) if value},
            "source_path": teacher_source or student_source,
            "teacher_source_path": teacher_source,
            "student_source_path": student_source,
            "options": form_options,
            "items": [{"topic": topic,
                       "teacher": "处理中" if teacher_source else "未提供",
                       "student": "处理中" if student_source or version == "TEACHER_ONLY" else "未提供"}],
            "warnings": [],
            "produced": 0,
            "result_dir": str(result_dir),
            "output_paths": [],
            "has_result": False,
            "renderer": None,
            "fallback_reason": None,
            "fallback_detail": None,
            "baseline_sha": None,
            "recovered_after_restart": False,
            "generation_attempts": 0,
            "student_preparation": {"make_student_called": False,
                                     "input_version": version,
                                     "elapsed_seconds": None,
                                     "wps_com_started": False,
                                     "student_preparation_route": None,
                                     "com_used": False,
                                     "com_observation": "NOT_ENTERED",
                                     "package_valid": None},
            "renderer_fallback_preparation": None,
            "publication": None,
        }
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

    def create_batch(self, files: list[tuple[str, bytes]], options: dict) -> dict:
        """Persist a parent plus isolated C1 jobs; never route a whole batch to COM."""
        logical = resolve_batch(files, str(options.get("docx_mode") or "auto"))
        form_options = {field: str(options.get(field, "")) for field in FORM_FIELDS}
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=True)
        result_dir = self._allocate_result_dir(form_options, "批量讲义")
        items = []
        for index, item in enumerate(logical):
            entry = {
                "item_id": str(index + 1), "topic": item.topic,
                "input_version": item.input_version,
                "teacher_source": None, "student_source": None,
                "status": "error" if item.error else "queued",
                "renderer": None, "fallback_reason": None,
                "output_paths": [], "error": item.error,
                "teacher": "失败" if item.error else "未提供",
                "student": "失败" if item.error else "未提供",
                "source_origins": [source.origin for source in item.sources],
            }
            if not item.error:
                try:
                    # Allocate only readable topic folders; never use ZIP directories.
                    folder = result_dir / (self._display_part(item.topic) or "专题")
                    number = 2
                    while folder.exists():
                        folder = result_dir / ((self._display_part(item.topic) or "专题") + "（%d）" % number)
                        number += 1
                    folder.mkdir()
                    teacher_index = next((i for i, source in enumerate(item.sources)
                                          if source is item.teacher_source), None)
                    student_index = next((i for i, source in enumerate(item.sources)
                                          if source is item.student_source), None)
                    classification = InputClassification(item.input_version, teacher_index,
                                                         student_index, item.evidence)
                    child = self.create_inputs([(source.name, source.data) for source in item.sources],
                                               form_options, _classification=classification,
                                               _topic=item.topic, _result_dir=folder,
                                               _parent_job_id=job_id)
                    entry.update({"child_job_id": child["job_id"],
                                  "teacher_source": child["teacher_source_path"],
                                  "student_source": child["student_source_path"],
                                  "teacher": child["items"][0]["teacher"],
                                  "student": child["items"][0]["student"],
                                  "result_dir": str(folder)})
                except Exception as exc:
                    entry.update(status="error", error="GENERATION_FAILED: %s: %s" %
                                 (type(exc).__name__, exc), teacher="失败", student="失败")
            items.append(entry)
        now = datetime.now(timezone.utc)
        record = {
            "job_id": job_id, "is_batch": True, "status": "queued",
            "total": len(items), "progress": 0, "completed": 0,
            "failed": sum(item["status"] == "error" for item in items),
            "current_topic": None, "items": items, "options": form_options,
            "filenames": [Path(name).name for name, _data in files],
            "created_at": now.timestamp(), "created_at_iso": now.isoformat(timespec="seconds"),
            "updated_at": now.timestamp(), "updated_at_iso": now.isoformat(timespec="seconds"),
            "stage": "批量任务已接收，等待生成", "result_dir": str(result_dir),
            "output_paths": [], "produced": 0, "has_result": False,
            "generation_attempts": 0, "warnings": [],
        }
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

    def _recover_batch(self, record: dict) -> dict:
        """Refresh only successful child outputs; failures cannot erase siblings."""
        result_dir = Path(record.get("result_dir") or "").resolve()
        if not result_dir.is_relative_to(self.result_root):
            raise ValueError("batch result directory escaped result root")
        for item in record.get("items", []):
            if not item.get("child_job_id"):
                continue
            try:
                child = self._recover(item["child_job_id"])
                if child.get("parent_job_id") != record["job_id"]:
                    raise ValueError("child does not belong to this batch")
                if not Path(child["result_dir"]).resolve().is_relative_to(result_dir):
                    raise ValueError("child result directory escaped batch")
                roles = child.get("items", [{}])[0]
                item.update({key: child.get(key) for key in (
                    "status", "renderer", "fallback_reason", "fallback_detail", "output_paths",
                    "error", "plan_summary", "student_preparation", "package_validation",
                    "started_at", "updated_at", "elapsed_seconds")})
                item["teacher"], item["student"] = roles.get("teacher"), roles.get("student")
            except (JobNotFound, OSError, ValueError, KeyError) as exc:
                item.update(status="error", error="GENERATION_FAILED: " + str(exc), output_paths=[])
        successes = [item for item in record["items"] if item["status"] == "done"]
        failures = [item for item in record["items"] if item["status"] == "error"]
        record["completed"], record["failed"] = len(successes), len(failures)
        record["progress"] = len(successes) + len(failures)
        record["output_paths"] = [path for item in successes for path in item["output_paths"]]
        record["produced"] = len(record["output_paths"])
        record["has_result"] = bool(record["output_paths"])
        # Preserve queued/running state until the executor starts the parent.
        if record.get("status") != "queued" and record["progress"] == record["total"]:
            record["status"] = "done" if not failures else "partial" if successes else "error"
            record["batch_outcome"] = "ALL_SUCCESS" if not failures else "PARTIAL_SUCCESS" if successes else "ALL_FAILED"
            record["current_topic"] = None
            record["stage"] = "批量生成完成：%d 个成功，%d 个失败" % (len(successes), len(failures))
            if record["status"] == "error":
                record["error"] = "GENERATION_FAILED: 所有专题均生成失败"
            if record.get("started_at"):
                record.setdefault("elapsed_seconds", round(datetime.now(timezone.utc).timestamp() - record["started_at"], 3))
        now = datetime.now(timezone.utc)
        record["updated_at"], record["updated_at_iso"] = now.timestamp(), now.isoformat(timespec="seconds")
        self._write_json(self._job_dir(record["job_id"]) / "job.json", record)
        return record

    def create(self, filename: str, data: bytes, options: dict) -> dict:
        """Compatibility wrapper for a single DOCX submission."""
        return self.create_inputs([(filename, data)], options)

    def start_job(self, job_id: str) -> dict:
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") == "done":
                return self.snapshot(record)
            if record.get("status") not in ("queued", "running"):
                return self.snapshot(record)
            now = datetime.now(timezone.utc)
            record.update({
                "status": "running",
                "stage": "准备 Splitter 与 Renderer",
                "started_at": now.timestamp(),
                "started_at_iso": now.isoformat(timespec="seconds"),
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
                "generation_attempts": int(record.get("generation_attempts", 0)) + 1,
            })
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def update_progress(self, job_id: str, progress: int, stage: str, *,
                        current_topic: str | None = None) -> dict:
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            now = datetime.now(timezone.utc)
            record.update({
                "progress": max(0, min(int(progress), int(record.get("total", 2)))),
                "stage": str(stage),
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
            })
            if record.get("is_batch"):
                record["current_topic"] = current_topic
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def record_fallback_attempt(self, job_id: str, reason: str, baseline_sha: str,
                                *, detail: str | None = None) -> dict:
        """Persist whole-job fallback intent before entering the fallback runtime."""
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            now = datetime.now(timezone.utc)
            record.update({
                "renderer": "V0.9",
                "fallback_reason": str(reason),
                "fallback_detail": str(detail) if detail else None,
                "baseline_sha": str(baseline_sha),
                "stage": "XML 不支持（%s），正在调用 V0.9 全任务回退" % reason,
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
            })
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def update_student_preparation(self, job_id: str, details: dict) -> dict:
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            record["student_preparation"] = dict(details)
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def record_publication_plan(self, job_id: str, role_paths: dict[str, str],
                                expected_sha256: dict[str, str]) -> dict:
        """Persist final paths and safely rebind hashes for unpublished retries."""
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            normalized = {str(role): str(Path(path).resolve())
                          for role, path in role_paths.items() if path is not None}
            if not normalized or not set(normalized).issubset({"teacher", "student"}):
                raise ValueError("publication plan must contain a classified output role")
            expected_hashes = {str(role): str(value) for role, value in expected_sha256.items()}
            if set(expected_hashes) != set(normalized):
                raise ValueError("publication plan must bind every role to staged output bytes")
            existing = record.get("publication")
            if existing and existing.get("role_paths") != normalized:
                raise ValueError("publication plan changed across an interrupted retry")
            now = datetime.now(timezone.utc)
            publication = existing or {"role_paths": normalized,
                                       "expected_sha256": expected_hashes, "published": {}}
            if existing:
                bound_hashes = dict(publication.get("expected_sha256", {}))
                published = publication.get("published", {})
                for role, final_path in normalized.items():
                    # A restart may regenerate byte-equivalent DOCX content
                    # with different ZIP metadata after private work files
                    # were cleared. Rebind only an unpublished role whose
                    # final path is absent. Existing outputs and published
                    # hashes stay immutable and use strict adoption checks.
                    if role not in published and not Path(final_path).exists():
                        bound_hashes[role] = expected_hashes[role]
                publication["expected_sha256"] = bound_hashes
            record["publication"] = publication
            record["updated_at"], record["updated_at_iso"] = now.timestamp(), now.isoformat(timespec="seconds")
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def mark_publication_role(self, job_id: str, role: str, path: str | Path, sha256: str) -> dict:
        """Record a final file only after it exists and package validation passed."""
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            publication = record.get("publication") or {}
            expected = publication.get("role_paths", {}).get(role)
            resolved = str(Path(path).resolve())
            if expected != resolved:
                raise ValueError("published path does not match the persisted role plan")
            published = dict(publication.get("published", {}))
            prior = published.get(role)
            if prior and prior.get("sha256") != sha256:
                raise ValueError("published role changed across an interrupted retry")
            published[role] = {"path": resolved, "sha256": str(sha256)}
            publication["published"] = published
            record["publication"] = publication
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def update_renderer_fallback_preparation(self, job_id: str, details: dict) -> dict:
        """Store make_student observations caused by renderer fallback separately."""
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "running":
                return self.snapshot(record)
            record["renderer_fallback_preparation"] = dict(details)
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def fail_job(self, job_id: str, detail: str) -> dict:
        """Persist failure of the local DOCX generation job."""
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") == "done":
                return self.snapshot(record)
            now = datetime.now(timezone.utc)
            error = str(detail)
            if not error.startswith("GENERATION_FAILED"):
                error = "GENERATION_FAILED: " + error
            record.update({
                "status": "error",
                "error": error,
                "stage": error,
                "has_result": False,
                "progress": 0,
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
                "elapsed_seconds": round(now.timestamp() - record.get("started_at", now.timestamp()), 3),
            })
            for item in record.get("items", []):
                item["teacher"] = "未提供" if record.get("input_version") == "STUDENT_ONLY" else "失败"
                item["student"] = "失败" if record.get("input_version") != "STUDENT_ONLY" else "失败"
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def _recover(self, job_id: str) -> dict:
        path = self._job_dir(job_id) / "job.json"
        if not path.is_file():
            raise JobNotFound(job_id)
        record = self._read_json(path)
        # Migrate obsolete output-download metadata without changing generation.
        legacy_keys = ("download_available", "delivery_status", "delivery_error_code", "delivery_error")
        legacy_changed = any(key in record for key in legacy_keys)
        for key in legacy_keys:
            record.pop(key, None)
        if record.get("is_batch"):
            with self._lock:
                return self._recover_batch(record)
        job_dir = self._job_dir(job_id)
        result_dir = Path(record.get("result_dir") or "").resolve()
        metadata_changed = not result_dir.is_relative_to(self.result_root)
        if metadata_changed:
            record["result_dir"] = str(self.result_root)
        # Never retain a successful status when its final output is gone.
        valid, _outputs, reports = self._validate_recorded_outputs(record)
        validation_changed = record.get("status") == "done" and record.get("package_validation") != reports
        if record.get("status") == "done":
            record["package_validation"] = reports
        if record.get("status") == "done" and not valid:
            record["status"] = "error"
            record["error"] = "GENERATION_FAILED: 已记录的成品缺失、为空或未通过包校验"
            record["stage"] = record["error"]
            record["has_result"] = False
            now = datetime.now(timezone.utc)
            record["updated_at"] = now.timestamp()
            record["updated_at_iso"] = now.isoformat(timespec="seconds")
            self._write_json(path, record)
        else:
            has_result = record.get("status") == "done" and valid
            changed = metadata_changed or validation_changed or legacy_changed or record.get("has_result") != has_result
            record["has_result"] = has_result
            if changed:
                self._write_json(path, record)
        return record

    def _validate_recorded_outputs(self, record: dict) -> tuple[bool, list[Path], dict]:
        """Validate every published role file inside the clean user result folder."""
        if record.get("is_batch"):
            result_dir = Path(record.get("result_dir") or "").resolve()
            paths = [Path(raw).resolve() for raw in record.get("output_paths", [])]
            if (not paths or not result_dir.is_relative_to(self.result_root)
                    or len(set(paths)) != len(paths)
                    or any(not path.is_relative_to(result_dir) or path.suffix.lower() != ".docx" for path in paths)):
                return False, [], {}
            reports = {str(path): validate_package(str(path)) for path in paths}
            return all(report.get("valid") is True for report in reports.values()), paths, reports
        try:
            roles = record.get("output_roles") or {}
            if not roles or not set(roles).issubset({"teacher", "student"}):
                return False, [], {}
            result_dir = Path(record.get("result_dir", "")).resolve()
            if not result_dir.is_relative_to(self.result_root):
                return False, [], {}
            paths = {role: Path(raw).resolve() for role, raw in roles.items()}
        except (OSError, RuntimeError, TypeError, ValueError):
            return False, [], {}
        if len(set(map(str, paths.values()))) != len(paths) or any(
                not path.is_relative_to(result_dir) or path.suffix.lower() != ".docx"
                for path in paths.values()):
            return False, [], {}
        try:
            listed = [Path(p).resolve() for p in record.get("output_paths", [])]
        except (OSError, RuntimeError, TypeError, ValueError):
            return False, [], {}
        if len(listed) != len(paths) or set(map(str, paths.values())) != set(map(str, listed)):
            return False, [], {}
        reports = {role: validate_package(str(path)) for role, path in paths.items()}
        return all(report.get("valid") is True for report in reports.values()), list(paths.values()), reports

    def complete_job(self, job_id: str, teacher_output_path: str | Path | None = None,
                     student_output_path: str | Path | None = None, *, renderer: str = "XML",
                     fallback_reason: str | None = None,
                     baseline_sha: str | None = None,
                     plan_summary: dict | None = None,
                     student_preparation: dict | None = None) -> dict:
        """Record done after all supplied role outputs validate."""
        job_dir = self._job_dir(job_id)
        record = self._recover(job_id)
        result_dir = Path(record["result_dir"]).resolve()
        paths = {role: Path(path).resolve() for role, path in (
            ("teacher", teacher_output_path), ("student", student_output_path)) if path is not None}
        if not paths:
            raise ValueError("at least one user-facing DOCX output is required")
        if len(set(map(str, paths.values()))) != len(paths):
            raise ValueError("teacher and student outputs must be different files")
        if any(not path.is_relative_to(result_dir) or path.suffix.lower() != ".docx"
               for path in paths.values()):
            raise ValueError("outputs must be DOCX files inside this job's clean result directory")
        reports = {role: validate_package(str(path)) for role, path in paths.items()}
        failures = {role: report for role, report in reports.items()
                    if report.get("valid") is not True}
        if failures:
            raise ValueError("package validation failed: %s" % json.dumps(failures, ensure_ascii=False))
        now = datetime.now(timezone.utc)
        output_roles = {role: str(path) for role, path in paths.items()}
        output_names = {role: path.name for role, path in paths.items()}
        has_teacher, has_student = "teacher" in paths, "student" in paths
        record.update({
            "status": "done",
            "progress": record.get("total", 2),
            "stage": "成品 DOCX 已生成并通过包校验",
            "updated_at": now.timestamp(),
            "updated_at_iso": now.isoformat(timespec="seconds"),
            "output_paths": [str(path) for path in paths.values()],
            "teacher_output_path": output_roles.get("teacher"),
            "student_output_path": output_roles.get("student"),
            "output_roles": output_roles,
            "output_filenames": output_names,
            "has_result": True,
            "produced": len(paths),
            "renderer": renderer,
            "fallback_reason": fallback_reason,
            "baseline_sha": baseline_sha,
            "package_validation": reports,
            "plan_summary": plan_summary,
            "student_preparation": student_preparation or record.get("student_preparation", {}),
            "elapsed_seconds": round(now.timestamp() - record.get("started_at", now.timestamp()), 3),
        })
        for item in record.get("items", []):
            item["teacher"] = "完成" if has_teacher else "未提供"
            item["student"] = "完成" if has_student else "未提供"
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

    def get(self, job_id: str) -> dict:
        with self._lock:
            return self.snapshot(self._recover(job_id))

    def list(self) -> list[dict]:
        records = []
        with self._lock:
            for path in self.runtime_root.glob("*/job.json"):
                try:
                    record = self._recover(path.parent.name)
                except (OSError, ValueError, KeyError, json.JSONDecodeError):
                    continue
                if record.get("parent_job_id"):
                    continue
                records.append(record)
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return [self.snapshot(record) for record in records]

    def result_directory(self, job_id: str) -> Path:
        record = self._recover(job_id)
        folder = Path(record["result_dir"]).resolve()
        if not folder.is_relative_to(self.result_root) or not folder.is_dir():
            raise JobNotFound(job_id)
        return folder

    def open_result(self, job_id: str) -> Path:
        folder = self.result_directory(job_id)
        self.opener(folder)
        return folder

    @staticmethod
    def snapshot(record: dict) -> dict:
        public = dict(record)
        public["has_result"] = bool(record.get("has_result", False))
        return public

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
from input_versions import classify_inputs, UnknownInputVersion


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

    def create_inputs(self, files: list[tuple[str, bytes]], options: dict) -> dict:
        if not files or len(files) > 2:
            raise UnsupportedInput("本轮只支持一个 DOCX，或一组教师版和学生版 DOCX")
        validated = [(filename or "source.docx", self.validate_docx(filename or "source.docx", data), data)
                     for filename, data in files]
        form_options = {field: str(options.get(field, "")) for field in FORM_FIELDS}
        try:
            classification = classify_inputs([(name, data) for name, _safe, data in validated],
                                              form_options["docx_mode"] or "auto")
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
        topic = self._topic_name(topic_source)
        result_dir = self._allocate_result_dir(form_options, topic)
        teacher_source = (str(input_paths[classification.teacher_index][1]) if classification and
                          classification.teacher_index is not None else None)
        student_source = (str(input_paths[classification.student_index][1]) if classification and
                          classification.student_index is not None else None)
        version = classification.input_version
        record = {
            "job_id": job_id,
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
            "download_available": False,
            "has_result": False,
            "renderer": None,
            "fallback_reason": None,
            "fallback_detail": None,
            "baseline_sha": None,
            "delivery_status": "not_attempted",
            "delivery_error_code": None,
            "delivery_error": None,
            "recovered_after_restart": False,
            "generation_attempts": 0,
            "student_preparation": {"make_student_called": False,
                                     "input_version": version,
                                     "elapsed_seconds": None,
                                     "wps_com_started": False,
                                     "package_valid": None},
        }
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

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

    def update_progress(self, job_id: str, progress: int, stage: str) -> dict:
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

    def fail_job(self, job_id: str, detail: str) -> dict:
        """Persist generation failure without conflating it with ZIP delivery."""
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
                "download_available": False,
                "progress": 0,
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
            })
            for item in record.get("items", []):
                item["teacher"] = "未提供" if record.get("input_version") == "STUDENT_ONLY" else "失败"
                item["student"] = "失败" if record.get("input_version") != "STUDENT_ONLY" else "失败"
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def record_download_succeeded(self, job_id: str) -> dict:
        # The server prepared a ZIP response. This does not claim that the
        # browser persisted it; local DOCX files remain the source of truth.
        return self._update_delivery(job_id, "zip_ready", None, None)

    def record_download_failed(self, job_id: str, detail: str) -> dict:
        return self._update_delivery(job_id, "failed", "DELIVERY_DOWNLOAD_FAILED", str(detail))

    def _update_delivery(self, job_id: str, status: str, code: str | None,
                         detail: str | None) -> dict:
        with self._lock:
            record = self._recover(job_id)
            if record.get("status") != "done":
                return self.snapshot(record)
            now = datetime.now(timezone.utc)
            record.update({
                "delivery_status": status,
                "download_available": status == "zip_ready",
                "delivery_error_code": code,
                "delivery_error": detail,
                "updated_at": now.timestamp(),
                "updated_at_iso": now.isoformat(timespec="seconds"),
            })
            self._write_json(self._job_dir(job_id) / "job.json", record)
            return self.snapshot(record)

    def _recover(self, job_id: str) -> dict:
        path = self._job_dir(job_id) / "job.json"
        if not path.is_file():
            raise JobNotFound(job_id)
        record = self._read_json(path)
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
            record["download_available"] = False
            now = datetime.now(timezone.utc)
            record["updated_at"] = now.timestamp()
            record["updated_at_iso"] = now.isoformat(timespec="seconds")
            self._write_json(path, record)
        else:
            has_result = record.get("status") == "done" and valid
            default_download_available = record.get("delivery_status") not in ("failed", "unavailable")
            download_available = bool(record.get("download_available", default_download_available)) if has_result else False
            changed = metadata_changed or validation_changed or (record.get("has_result") != has_result or
                       record.get("download_available") != download_available)
            record["has_result"] = has_result
            record["download_available"] = download_available
            if changed:
                self._write_json(path, record)
        return record

    def _validate_recorded_outputs(self, record: dict) -> tuple[bool, list[Path], dict]:
        """Validate every published role file inside the clean user result folder."""
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
            "download_available": True,
            "delivery_status": "available",
            "delivery_error_code": None,
            "delivery_error": None,
            "has_result": True,
            "produced": len(paths),
            "renderer": renderer,
            "fallback_reason": fallback_reason,
            "baseline_sha": baseline_sha,
            "package_validation": reports,
            "plan_summary": plan_summary,
            "student_preparation": student_preparation or record.get("student_preparation", {}),
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

    def outputs_for_download(self, job_id: str) -> tuple[dict, list[Path]]:
        record = self._recover(job_id)
        valid, outputs, _reports = self._validate_recorded_outputs(record)
        if record.get("status") != "done" or not valid:
            raise ValueError("任务尚无已验证的 DOCX 成品")
        return record, outputs

    @staticmethod
    def snapshot(record: dict) -> dict:
        public = dict(record)
        public["has_result"] = bool(record.get("has_result", False))
        public["download_available"] = bool(record.get("download_available", False))
        return public

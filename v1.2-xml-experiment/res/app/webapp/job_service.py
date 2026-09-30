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
    def __init__(self, result_root: str | Path, *, opener=None):
        self.result_root = Path(result_root).expanduser().resolve()
        self.result_root.mkdir(parents=True, exist_ok=True)
        self.opener = opener or self._open_folder
        self._lock = threading.RLock()
        self._recover_interrupted_jobs()

    def _recover_interrupted_jobs(self) -> None:
        """Requeue an interrupted running job when a new service instance starts."""
        with self._lock:
            for metadata in self.result_root.glob("*/job.json"):
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
            raise UnsupportedInput("当前仅支持单个 .docx 文件；ZIP 和其他格式暂不支持")
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
        path = (self.result_root / job_id).resolve()
        if path.parent != self.result_root:
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

    def create(self, filename: str, data: bytes, options: dict) -> dict:
        safe_name = self.validate_docx(filename, data)
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        (job_dir / "work").mkdir(parents=True)
        source_path = job_dir / "work" / safe_name
        source_path.write_bytes(data)
        now = datetime.now(timezone.utc)
        created_at = now.timestamp()
        form_options = {field: str(options.get(field, "")) for field in FORM_FIELDS}
        # workspace.js history currently reads the camelCase spellings below.
        form_options.update({
            "handoutType": form_options["handout_type"],
            "academicYear": form_options["academic_year"],
            "templateType": form_options["template_type"],
            "splitMode": form_options["split_mode"],
            "docxMode": form_options["docx_mode"],
        })
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
            "filenames": [safe_name],
            "source_path": str(source_path),
            "options": form_options,
            "items": [{"topic": Path(safe_name).stem, "teacher": "处理中", "student": "处理中"}],
            "warnings": [],
            "produced": 0,
            "result_dir": str(job_dir),
            "output_paths": [],
            "download_available": False,
            "has_result": False,
            "renderer": None,
            "fallback_reason": None,
            "baseline_sha": None,
            "delivery_status": "not_attempted",
            "delivery_error_code": None,
            "delivery_error": None,
            "recovered_after_restart": False,
            "generation_attempts": 0,
        }
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

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
                item["teacher"] = "失败"
                item["student"] = "失败"
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
        metadata_changed = record.get("result_dir") != str(job_dir)
        if metadata_changed:
            record["result_dir"] = str(job_dir)
        # Never retain a successful status when its final output is gone.
        valid, _outputs, reports = self._validate_recorded_outputs(record, job_dir)
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

    @staticmethod
    def _validate_recorded_outputs(record: dict, job_dir: Path) -> tuple[bool, list[Path], dict]:
        """Require explicit, distinct role paths and B-Line package validation."""
        try:
            roles = record.get("output_roles") or {}
            teacher_field = record.get("teacher_output_path")
            student_field = record.get("student_output_path")
            teacher_role = roles.get("teacher")
            student_role = roles.get("student")
            if teacher_field and teacher_role and Path(teacher_field).resolve() != Path(teacher_role).resolve():
                return False, [], {}
            if student_field and student_role and Path(student_field).resolve() != Path(student_role).resolve():
                return False, [], {}
            raw_teacher = teacher_field or teacher_role
            raw_student = student_field or student_role
            if not raw_teacher or not raw_student:
                return False, [], {}
            teacher, student = Path(raw_teacher).resolve(), Path(raw_student).resolve()
        except (OSError, RuntimeError, TypeError, ValueError):
            return False, [], {}
        if teacher == student or not teacher.is_relative_to(job_dir) or not student.is_relative_to(job_dir):
            return False, [], {}
        try:
            listed = [Path(p).resolve() for p in record.get("output_paths", [])]
        except (OSError, RuntimeError, TypeError, ValueError):
            return False, [], {}
        if len(listed) != 2 or set(map(str, [teacher, student])) != set(map(str, listed)):
            return False, [], {}
        reports = {"teacher": validate_package(str(teacher)),
                   "student": validate_package(str(student))}
        return all(report.get("valid") is True for report in reports.values()), [teacher, student], reports

    def complete_job(self, job_id: str, teacher_output_path: str | Path,
                     student_output_path: str | Path, *, renderer: str = "XML",
                     fallback_reason: str | None = None,
                     baseline_sha: str | None = None,
                     plan_summary: dict | None = None) -> dict:
        """Record done only after distinct teacher/student packages validate."""
        job_dir = self._job_dir(job_id)
        teacher, student = Path(teacher_output_path).resolve(), Path(student_output_path).resolve()
        if teacher == student:
            raise ValueError("teacher and student outputs must be different files")
        if not teacher.is_relative_to(job_dir) or not student.is_relative_to(job_dir):
            raise ValueError("teacher/student outputs must be inside this job result directory")
        if teacher.suffix.lower() != ".docx" or student.suffix.lower() != ".docx":
            raise ValueError("teacher/student outputs must be DOCX files")
        reports = {"teacher": validate_package(str(teacher)),
                   "student": validate_package(str(student))}
        failures = {role: report for role, report in reports.items()
                    if report.get("valid") is not True}
        if failures:
            raise ValueError("package validation failed: %s" % json.dumps(failures, ensure_ascii=False))
        record = self._recover(job_id)
        now = datetime.now(timezone.utc)
        record.update({
            "status": "done",
            "progress": record.get("total", 2),
            "stage": "教师版和学生版 DOCX 已生成并通过包校验",
            "updated_at": now.timestamp(),
            "updated_at_iso": now.isoformat(timespec="seconds"),
            "output_paths": [str(teacher), str(student)],
            "teacher_output_path": str(teacher),
            "student_output_path": str(student),
            "output_roles": {"teacher": str(teacher), "student": str(student)},
            "download_available": True,
            "delivery_status": "available",
            "delivery_error_code": None,
            "delivery_error": None,
            "has_result": True,
            "produced": 2,
            "renderer": renderer,
            "fallback_reason": fallback_reason,
            "baseline_sha": baseline_sha,
            "package_validation": reports,
            "plan_summary": plan_summary,
        })
        for item in record.get("items", []):
            item["teacher"] = "完成"
            item["student"] = "完成"
        with self._lock:
            self._write_json(job_dir / "job.json", record)
        return self.snapshot(record)

    def get(self, job_id: str) -> dict:
        with self._lock:
            return self.snapshot(self._recover(job_id))

    def list(self) -> list[dict]:
        records = []
        with self._lock:
            for path in self.result_root.glob("*/job.json"):
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
        if folder != self._job_dir(job_id) or not folder.is_dir():
            raise JobNotFound(job_id)
        return folder

    def open_result(self, job_id: str) -> Path:
        folder = self.result_directory(job_id)
        self.opener(folder)
        return folder

    def outputs_for_download(self, job_id: str) -> tuple[dict, list[Path]]:
        record = self._recover(job_id)
        valid, outputs, _reports = self._validate_recorded_outputs(record, self._job_dir(job_id))
        if record.get("status") != "done" or not valid:
            raise ValueError("任务尚无已验证的教师版和学生版 DOCX 成品")
        return record, outputs

    @staticmethod
    def snapshot(record: dict) -> dict:
        public = dict(record)
        public["has_result"] = bool(record.get("has_result", False))
        public["download_available"] = bool(record.get("download_available", False))
        return public

# -*- coding: utf-8 -*-
"""Small file-backed job repository for the C0 HTTP boundary.

This round deliberately persists jobs as ``job.json`` and uploaded sources,
but does not execute a renderer or mark jobs complete. C0 outputs are reserved
under each job's stable result directory for the next integration round.
"""
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
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
            "stage": "任务已接收，等待生成流程接入",
            "created_at": now,
            "updated_at": now,
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
        }
        with self._lock:
            self._write_json(job_dir / "job.json", record)
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
        outputs = [Path(p) for p in record.get("output_paths", [])]
        try:
            confined = all(output.resolve().is_relative_to(job_dir) for output in outputs)
        except OSError:
            confined = False
        valid = confined and self._valid_final_outputs(outputs)
        if record.get("status") == "done" and not valid:
            record["status"] = "error"
            record["error"] = "GENERATION_FAILED: 已记录的成品缺失或为空"
            record["stage"] = record["error"]
            record["has_result"] = False
            record["download_available"] = False
            record["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._write_json(path, record)
        else:
            has_result = record.get("status") == "done" and valid
            changed = metadata_changed or (record.get("has_result") != has_result or
                       record.get("download_available") != has_result)
            record["has_result"] = has_result
            record["download_available"] = has_result
            if changed:
                self._write_json(path, record)
        return record

    @staticmethod
    def _is_valid_docx(path: Path) -> bool:
        if path.suffix.lower() != ".docx" or not path.is_file() or path.stat().st_size <= 0:
            return False
        try:
            with zipfile.ZipFile(path) as package:
                names = set(package.namelist())
                return ("[Content_Types].xml" in names and
                        "word/document.xml" in names and package.testzip() is None)
        except (OSError, zipfile.BadZipFile):
            return False

    @classmethod
    def _valid_final_outputs(cls, outputs: list[Path]) -> bool:
        if len(outputs) != 2 or not all(cls._is_valid_docx(path) for path in outputs):
            return False
        names = [path.name.casefold() for path in outputs]
        return any("教师" in name or "teacher" in name for name in names) and any(
            "学生" in name or "student" in name for name in names
        )

    def get(self, job_id: str) -> dict:
        with self._lock:
            return self.snapshot(self._recover(job_id))

    def list(self) -> list[dict]:
        records = []
        with self._lock:
            for path in self.result_root.glob("*/job.json"):
                try:
                    record = self._recover(path.parent.name)
                except (OSError, ValueError, json.JSONDecodeError):
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
        outputs = [Path(p).resolve() for p in record.get("output_paths", [])]
        job_dir = self._job_dir(job_id)
        if (record.get("status") != "done" or
                any(not p.is_relative_to(job_dir) for p in outputs) or
                not self._valid_final_outputs(outputs)):
            raise ValueError("任务尚无已验证的教师版和学生版 DOCX 成品")
        return record, outputs

    @staticmethod
    def snapshot(record: dict) -> dict:
        public = dict(record)
        public["has_result"] = bool(record.get("has_result", False))
        public["download_available"] = bool(record.get("download_available", False))
        return public

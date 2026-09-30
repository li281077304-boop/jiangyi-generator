# -*- coding: utf-8 -*-
"""Flash 1.2 workbench HTTP shell and durable C0 job boundary."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
import zipfile

from flask import Flask, jsonify, render_template, request, send_file


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from job_service import JobNotFound, JobService, UnsupportedInput  # noqa: E402


app = Flask(__name__)
app.config.setdefault("RESULT_ROOT", Path.home() / "Desktop" / "生成讲义结果")


def _jobs() -> JobService:
    root = Path(app.config["RESULT_ROOT"]).expanduser().resolve()
    opener = app.config.get("OPEN_FOLDER")
    services = app.extensions.setdefault("c0_job_services", {})
    key = (str(root), id(opener) if opener is not None else None)
    if key not in services:
        services[key] = JobService(root, opener=opener)
    return services[key]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/jobs")
def list_jobs():
    return jsonify({"jobs": _jobs().list()})


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
    # Round 2 creates and persists an honest queued job. A later integration
    # round installs the executor; this route must not imply generation success.
    return jsonify(created), 202


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    try:
        return jsonify(_jobs().get(job_id))
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
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for output in outputs:
            package.write(output, arcname=output.name)
    archive.seek(0)
    return send_file(archive, mimetype="application/zip", as_attachment=True,
                     download_name="讲义成品-%s.zip" % job_id[:8])


def record_status(service: JobService, job_id: str) -> str:
    """Best-effort status for a not-ready delivery response; never mutates it."""
    try:
        return service.get(job_id).get("status", "unknown")
    except JobNotFound:
        return "unknown"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5128)

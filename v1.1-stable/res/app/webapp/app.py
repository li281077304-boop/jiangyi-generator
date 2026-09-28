# -*- coding: utf-8 -*-
"""
app.py —— 讲义生成器 Web 后端（Flask 路由层）

职责：HTTP 路由（页面 / 配置 / 任务创建与查询 / 下载 / 退出），
      业务逻辑在 jobs.py（任务服务），配置在 config.py。

启动：python app.py  → 自动打开浏览器，Waitress 服务在 127.0.0.1:5000
"""
import os
import sys
import time
import uuid
import socket
import threading
import copy

# ------------------------------------------------------------
# 路径准备：把引擎目录（res/app）加入 sys.path
# ------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))          # res/app/webapp
ENGINE_DIR = os.path.dirname(APP_DIR)                          # res/app
# 注意：嵌入版 Python 处于隔离模式（python312._pth），脚本所在目录不会自动进 sys.path，
# 必须显式加入 webapp 目录（jobs.py）和引擎目录（handout.py 等）。
for _d in (APP_DIR, ENGINE_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

# 启动自检：引擎依赖缺失时给出明确提示，而不是一闪而过
_startup_errors = []
try:
    import handout
    import config
except Exception as e:
    _startup_errors.append(f"导入引擎失败: {e}")

for mod, label in (("flask", "flask"), ("waitress", "waitress"),
                   ("docx", "docx (python-docx)")):
    try:
        __import__(mod)
    except ImportError as e:
        _startup_errors.append(f"缺少依赖 {label}: {e}")

if _startup_errors:
    print("=" * 50)
    print("  [启动错误] 以下问题需要修复：")
    print("=" * 50)
    for err in _startup_errors:
        print(f"    ! {err}")
    print("=" * 50)
    print("  请检查文件是否完整解压，或重新解压本程序。")
    sys.exit(1)

from flask import Flask, request, jsonify, send_file, render_template

import jobs

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500MB 上限
CREATE_LOCK = threading.Lock()


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify({"error": "文件总大小超过 500 MB，请分批上传"}), 413


def public_job(job_id, job):
    """Return a stable, JSON-safe snapshot for the UI."""
    result = copy.deepcopy({k: v for k, v in job.items() if k != "result_zip"})
    result.update(job_id=job_id, has_result=bool(
        job.get("result_zip") and os.path.isfile(job["result_zip"])))
    return result


# ============================================================
#  路由
# ============================================================
@app.route("/")
def index():
    cfg = config.load_config()
    return render_template("index.html", has_key=bool(cfg.get("api_key")))


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        # Flash 1.1：API 已停用，忽略前端提交的 api_key，不落盘
        return jsonify({"ok": True, "has_key": False, "api_enabled": config.API_ENABLED})
    cfg = config.load_config()
    return jsonify({"has_key": False, "api_enabled": config.API_ENABLED,
                    "subject": cfg.get("subject", "数学")})


@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    with jobs.JOBS_LOCK:
        ordered = reversed(list(jobs.JOBS.items()))
        return jsonify({"jobs": [public_job(key, value) for key, value in ordered]})


@app.route("/api/jobs", methods=["POST"])
def create_job():
    # Word COM uses shared desktop resources. One generation at a time is safer
    # and gives the UI a useful existing job to reconnect to.
    with CREATE_LOCK:
        with jobs.JOBS_LOCK:
            running = next((key for key, value in jobs.JOBS.items()
                            if value.get("status") == "running"), None)
        if running:
            return jsonify({"error": "已有讲义正在生成", "job_id": running}), 409
        return _create_job()


def _create_job():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "未收到文件"}), 400

    subject = request.form.get("subject", "数学")
    grade = request.form.get("grade", "")
    handout_type = request.form.get("handout_type", "")
    academic_year = request.form.get("academic_year", "")
    template_type = request.form.get("template_type", "1v1")
    split_mode = request.form.get("split_mode", "smart")
    docx_mode = request.form.get("docx_mode", "auto")
    if (template_type not in ("1v1", "class") or
            split_mode not in ("smart", "candidate", "ideal", "full") or
            docx_mode not in ("auto", "separate")):
        return jsonify({"error": "不支持的生成配置"}), 400

    filenames = []
    for f in files:
        name = (f.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        if (not name or name.startswith("~$") or
                not name.lower().endswith((".zip", ".docx"))):
            return jsonify({"error": "仅支持 ZIP 和 DOCX，请移除无效文件"}), 400
        if name.casefold() in {item.casefold() for item in filenames}:
            return jsonify({"error": "存在同名文件，请先重命名，避免素材覆盖"}), 400
        filenames.append(name)

    job_id = uuid.uuid4().hex[:12]
    work = os.path.join(jobs.JOBS_DIR, job_id)
    in_dir = os.path.join(work, "inputs")
    os.makedirs(in_dir, exist_ok=True)

    zip_paths = []
    docx_paths = []
    for f, fname in zip(files, filenames):
        dest = os.path.join(in_dir, os.path.basename(fname))
        f.save(dest)
        if fname.lower().endswith(".zip"):
            zip_paths.append((dest, fname))
        elif jobs._is_docx(fname):
            docx_paths.append((dest, fname))

    # 组装输入项：每个 zip 一项；docx 按"成对"分组
    inputs = []
    for path, fname in zip_paths:
        inputs.append({"kind": "zip", "paths": [path], "label": fname})

    if docx_paths:
        if len(docx_paths) == 2 and docx_mode == "auto":
            pair_label = " + ".join(os.path.basename(n) for _, n in docx_paths)
            inputs.append({"kind": "docx", "paths": [p for p, _ in docx_paths], "label": pair_label})
        else:
            for path, fname in docx_paths:
                inputs.append({"kind": "docx", "paths": [path], "label": os.path.basename(fname)})

    if not inputs:
        return jsonify({"error": "未发现 zip 或 docx 文件"}), 400

    with jobs.JOBS_LOCK:
        jobs.JOBS[job_id] = {
            "status": "running", "progress": 0, "total": len(inputs),
            "current": "", "stage": "", "items": [], "result_zip": None, "error": None,
            "created_at": time.time(), "filenames": filenames,
            "options": {"subject": subject, "grade": grade,
                        "handoutType": handout_type, "academicYear": academic_year,
                        "templateType": template_type, "splitMode": split_mode,
                        "docxMode": docx_mode},
        }
    cfg = config.load_config()
    threading.Thread(
        target=jobs.process_job,
        args=(job_id, inputs, cfg, subject, grade, handout_type,
              academic_year, template_type, split_mode),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id, "total": len(inputs)})


@app.route("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs.JOBS_LOCK:
        job = jobs.JOBS.get(job_id)
        if not job:
            return jsonify({"error": "任务不存在，服务可能已重启"}), 404
        return jsonify(public_job(job_id, job))


@app.route("/api/download/<job_id>")
def download(job_id):
    job = jobs.JOBS.get(job_id)
    if not job or not job.get("result_zip") or not os.path.exists(job["result_zip"]):
        return jsonify({"error": "结果不存在"}), 404
    return send_file(job["result_zip"], as_attachment=True,
                     download_name=os.path.basename(job["result_zip"]))


@app.route("/api/open/<job_id>")
def api_open(job_id):
    """打开已生成成品的输出文件夹（并选中 zip），供前端"打开成品"按钮调用。"""
    import subprocess as _sp
    job = jobs.JOBS.get(job_id)
    if not job or not job.get("result_zip") or not os.path.exists(job["result_zip"]):
        return jsonify({"error": "结果不存在"}), 404
    target = job["result_zip"]
    try:
        _sp.Popen(["explorer", "/select,", os.path.normpath(target)])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """浏览器关闭时通知，服务延迟优雅退出（不阻止浏览器卸载）"""
    print("浏览器已关闭，服务 2 秒后退出")

    def _delayed_shutdown():
        time.sleep(2)
        os._exit(0)

    threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return jsonify({"ok": True})


def _open_browser_when_ready(url, port):
    """后台等服务端口就绪后再打开浏览器，避免过早打开连不上"""
    import webbrowser
    for _ in range(60):   # 最多等 30 秒
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    # Flash 1.1 使用独立端口 5127，与原版 V1.0（5000）隔离，
    # 避免端口被旧版占用导致启动错乱（曾出现"打开两个窗口/托盘异常"）。
    PORT = 5127
    URL = f"http://127.0.0.1:{PORT}"

    # 防止重复启动：如果端口已被占用（说明已有进程在服务），只打开浏览器
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        print(f"检测到已有服务运行在 {URL}，打开浏览器")
        import webbrowser
        try:
            webbrowser.open(URL)
        except Exception:
            pass
        sys.exit(0)
    except (OSError, ConnectionRefusedError):
        pass  # 端口空闲，正常启动

    print(f"讲义生成器（flash 版）启动中... 访问 {URL}")
    # 后台等待端口就绪后自动打开浏览器（替代原版 exe 启动器的行为，
    # 这样无论用 vbs / 命令行 / 双击脚本启动，浏览器都会自动弹出）
    threading.Thread(target=_open_browser_when_ready, args=(URL, PORT), daemon=True).start()
    from waitress import serve
    serve(app, host="127.0.0.1", port=PORT, threads=4)

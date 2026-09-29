# -*- coding: utf-8 -*-
"""
讲义生成器 Web 后端（Flask）
上传 zip/docx → 自动生成教师版+学生版 → 打包下载。
"""
import os, sys, json, zipfile, tempfile, threading, uuid, shutil, traceback, time, re

# ============================================================
#  启动诊断（所有 import 异常在此暴露，不会一闪而过）
# ============================================================
_startup_errors = []

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(APP_DIR)

# 寻找 handout.py
_handout_found = False
for cand in (ENGINE_DIR, APP_DIR, os.path.join(ENGINE_DIR, "app")):
    hp = os.path.join(cand, "handout.py")
    if os.path.exists(hp):
        sys.path.insert(0, cand)
        ENGINE_DIR = cand
        _handout_found = True
        break
if not _handout_found:
    _startup_errors.append(f"找不到 handout.py（搜索路径: {ENGINE_DIR}, {APP_DIR}）")

try:
    import handout
except Exception as e:
    _startup_errors.append(f"导入 handout 失败: {e}")

_required_pkgs = {
    "flask": "flask",
    "waitress": "waitress",
    "docx": "docx (python-docx)",
}
for mod, label in _required_pkgs.items():
    try:
        __import__(mod)
    except ImportError as e:
        _startup_errors.append(f"缺少依赖 {label}: {e}")

if _startup_errors:
    print("=" * 50)
    print("  [启动错误] 以下问题需要修复：")
    print("=" * 50)
    for err in _startup_errors:
        print(f"    ❌ {err}")
    print("=" * 50)
    print("  请检查文件是否完整解压，或重新解压本程序。")
    print("=" * 50)
    sys.exit(1)

from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500MB 上限

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
JOBS_DIR = os.path.join(tempfile.gettempdir(), "handout_jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

# 内存中的任务表：job_id -> {status, progress, total, items, result_zip, error}
JOBS = {}
JOBS_LOCK = threading.Lock()

# 版本识别关键词
TEACHER_KW = ["教师", "解析", "答案", "教师版", "解析版"]
STUDENT_KW = ["学生", "学生版", "空白", "原卷", "原卷版"]


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": "", "subject": "数学"}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _is_docx(name):
    """识别 .docx（排除 .doc 旧格式与临时锁文件 ~$）"""
    base = os.path.basename(name)
    if base.startswith("~$"):
        return False
    return base.lower().endswith(".docx")


def classify_docx(names_sizes):
    """
    输入 [(文件名, 大小), ...]，返回 (教师版名, 学生版名)。
    先按关键词，识别不出按文件大小兜底（大的=含答案=教师版）。
    """
    docx = [(n, s) for n, s in names_sizes if _is_docx(n)]
    if not docx:
        return None, None
    teacher = student = None
    for n, s in docx:
        base = os.path.basename(n)
        if teacher is None and any(k in base for k in TEACHER_KW):
            teacher = n
        elif student is None and any(k in base for k in STUDENT_KW):
            student = n
    # 兜底：按大小，大的当教师版
    if teacher is None or student is None:
        ordered = sorted(docx, key=lambda x: x[1], reverse=True)
        if teacher is None:
            teacher = ordered[0][0]
        if student is None:
            # 取一个不同于 teacher 的
            for n, s in ordered:
                if n != teacher:
                    student = n
                    break
    return teacher, student


def topic_from_name(zip_name, docx_name):
    """授课主题提取，委托给引擎层 handout.extract_topic（去修饰词只留核心主题）"""
    fallback = os.path.splitext(os.path.basename(zip_name))[0] if zip_name else ""
    return handout.extract_topic(docx_name, fallback=fallback)


def _resolve_pair(item, work):
    """
    把一个输入项归约为 (教师版源, 学生版源, topic, 源标签)。
    item: {"kind": "zip"|"docx", "paths": [...], "label": 原始名}
    - zip：解压后 classify_docx 配对；只有一个 docx 时学生版源=None（由调用方 make_student）
    - docx 单个：teacher=该文件，student=None（make_student 去答案）
    - docx 多个：classify_docx 配对
    学生版源 None 表示"由教师版生成"。
    """
    kind = item["kind"]
    label = item["label"]
    if kind == "zip":
        extract_dir = os.path.join(work, "zip_" + uuid.uuid4().hex[:8])
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(item["paths"][0]) as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            raise RuntimeError(f"解压失败: {e}")
        names_sizes = []
        for root, _, files in os.walk(extract_dir):
            for fn in files:
                fp = os.path.join(root, fn)
                names_sizes.append((fp, os.path.getsize(fp)))
        teacher, student = classify_docx(names_sizes)
        if not teacher:
            raise RuntimeError("zip 内未找到 docx")
        topic = topic_from_name(label, teacher)
        # student 为 None 或等于 teacher → 标记由教师版生成
        stu_src = student if (student and student != teacher) else None
        return teacher, stu_src, topic, extract_dir
    else:
        # docx 直传
        paths = item["paths"]
        if len(paths) == 1:
            teacher = paths[0]
            topic = topic_from_name(label, teacher)
            return teacher, None, topic, os.path.dirname(teacher)
        else:
            names_sizes = [(p, os.path.getsize(p)) for p in paths]
            teacher, student = classify_docx(names_sizes)
            if not teacher:
                raise RuntimeError("未识别到 docx")
            topic = topic_from_name(label, teacher)
            stu_src = student if (student and student != teacher) else None
            return teacher, stu_src, topic, os.path.dirname(teacher)


def process_job(job_id, inputs, cfg, subject="数学", grade="", handout_type="", academic_year="", template_type="1v1"):
    """后台线程：逐个输入项处理，统一输出 教师版+学生版 两份，更新进度"""
    job = JOBS[job_id]
    work = os.path.join(JOBS_DIR, job_id)
    out_dir = os.path.join(work, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    api_key = cfg.get("api_key", "")
    produced = []
    # 按模板类型选模板文件
    if template_type == "class":
        template = handout.CLASS_TEMPLATE
    else:
        template = handout.DEFAULT_TEMPLATE

    try:
        for ii, item in enumerate(inputs):
            label = item["label"]
            with JOBS_LOCK:
                job["progress"] = ii
                job["current"] = label
            item_label = {"zip": label, "docx": label}[item["kind"]]
            row = {"zip": item_label, "topic": "", "teacher": "处理中", "student": "—"}
            with JOBS_LOCK:
                job["items"].append(row)

            try:
                teacher, student_src, topic, base_dir = _resolve_pair(item, work)
            except Exception as e:
                row["teacher"] = f"失败: {e}"
                row["student"] = f"失败: {e}"
                row["topic"] = "（识别失败）"
                job.setdefault("warnings", []).append(f"{label}: {e}")
                continue

            row["topic"] = topic

            # —— 教师版 ——
            try:
                paras_t = handout._body_paragraphs(teacher)
                obj, diff = handout.make_objectives(subject, topic, api_key, paras=paras_t)
                # 短标题用于文档表头，长文件名用于输出文件
                t_out_name = handout.build_filename(subject, grade, handout_type, topic, "教师版", academic_year)
                t_out = os.path.join(out_dir, t_out_name)
                handout.build_version("教师版", teacher, t_out, topic,
                                      paras=paras_t, objectives=obj, difficulties=diff,
                                      template=template, template_type=template_type,
                                      grade=grade, subject=subject, handout_type=handout_type)
                if not os.path.exists(t_out) or os.path.getsize(t_out) < 1024:
                    raise RuntimeError(f"输出文件未正确生成或太小: {t_out}")
                produced.append(t_out)
                row["teacher"] = "完成"
            except Exception as e:
                row["teacher"] = f"失败: {e}"
                job.setdefault("warnings", []).append(f"{label} 教师版: {e}")

            time.sleep(1)   # 让 Word 进程释放

            # —— 学生版（永远输出） ——
            try:
                if student_src:
                    stu_src = student_src
                else:
                    # 由教师版生成：去红色答案 + 删答案/解析标记段（覆盖黑/灰底）
                    stu_src = os.path.join(base_dir, "_stu_src.docx")
                    n_red, n_del, n_q, n_blk, mlog = handout.make_student(teacher, stu_src)
                    print(f"[{label}] 学生版生成：清红色 {n_red} 段，删标记 {n_del} 段，简答 {n_q} 题 +{n_blk} 空行")
                paras_s = handout._body_paragraphs(stu_src)
                s_out_name = handout.build_filename(subject, grade, handout_type, topic, "学生版", academic_year)
                s_out = os.path.join(out_dir, s_out_name)
                handout.build_version("学生版", stu_src, s_out, topic,
                                      paras=paras_s, objectives=obj, difficulties=diff,
                                      template=template, template_type=template_type,
                                      grade=grade, subject=subject, handout_type=handout_type)
                if not os.path.exists(s_out) or os.path.getsize(s_out) < 1024:
                    raise RuntimeError(f"输出文件未正确生成或太小: {s_out}")
                produced.append(s_out)
                row["student"] = "完成"
            except Exception as e:
                row["student"] = f"失败: {e}"
                job.setdefault("warnings", []).append(f"{label} 学生版: {e}")

            time.sleep(1)

        # 打包——下载包用第一个源文件的标题命名
        if produced:
            first_label = inputs[0].get("label", "讲义") if inputs else "讲义"
            first_label = os.path.splitext(os.path.basename(first_label))[0]  # 去扩展名
            # 只保留核心名，去"教师版/解析版/学生版"等噪音词
            for kw in TEACHER_KW + STUDENT_KW:
                first_label = first_label.replace(kw, "")
            first_label = re.sub(r'[（(][^）)]*[）)]', '', first_label)  # 去括号
            first_label = first_label.strip("_- ·").strip() or "讲义"
            result_zip = os.path.join(work, f"{first_label}.zip")
            missing = [f for f in produced if not os.path.exists(f)]
            if missing:
                warn = f"以下 {len(missing)} 个文件打包时未找到: {', '.join(os.path.basename(m) for m in missing)}"
                job.setdefault("warnings", []).append(warn)
            existing = [f for f in produced if os.path.exists(f)]
            if existing:
                with zipfile.ZipFile(result_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in existing:
                        zf.write(f, os.path.basename(f))
                with JOBS_LOCK:
                    job["result_zip"] = result_zip
                    job["progress"] = len(inputs)
                    job["status"] = "done"
                    job["produced"] = len(existing)
            else:
                with JOBS_LOCK:
                    job["status"] = "error"
                    job["error"] = "所有生成的文件均未找到，可能 Word 处理失败。请检查是否有 Word/WPS 安装在当前电脑。"
        else:
            with JOBS_LOCK:
                job["status"] = "error"
                job["error"] = "没有成功生成任何讲义，请检查上传内容"
    except Exception as e:
        traceback.print_exc()
        with JOBS_LOCK:
            job["status"] = "error"
            job["error"] = str(e)


# ============================================================
#  路由
# ============================================================
@app.route("/")
def index():
    cfg = load_config()
    return render_template("index.html", has_key=bool(cfg.get("api_key")))


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        cfg = load_config()
        data = request.get_json(force=True)
        cfg["api_key"] = data.get("api_key", "").strip()
        save_config(cfg)
        return jsonify({"ok": True, "has_key": bool(cfg["api_key"])})
    cfg = load_config()
    return jsonify({"has_key": bool(cfg.get("api_key")), "subject": cfg.get("subject", "数学")})


@app.route("/api/jobs", methods=["POST"])
def create_job():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "未收到文件"}), 400

    subject = request.form.get("subject", "数学")
    grade = request.form.get("grade", "")
    handout_type = request.form.get("handout_type", "")
    academic_year = request.form.get("academic_year", "")
    template_type = request.form.get("template_type", "1v1")

    job_id = uuid.uuid4().hex[:12]
    work = os.path.join(JOBS_DIR, job_id)
    in_dir = os.path.join(work, "inputs")
    os.makedirs(in_dir, exist_ok=True)

    zip_paths = []
    docx_paths = []
    for f in files:
        fname = f.filename or ""
        dest = os.path.join(in_dir, os.path.basename(fname))
        f.save(dest)
        if fname.lower().endswith(".zip"):
            zip_paths.append((dest, fname))
        elif _is_docx(fname):
            docx_paths.append((dest, fname))

    # 组装输入项：每个 zip 一项；docx 按"成对"分组
    inputs = []
    for path, fname in zip_paths:
        # label = zip 原始文件名（teacher/student 会从 zf 内文件名重新定位，只是包名用）
        inputs.append({"kind": "zip", "paths": [path], "label": fname})

    if docx_paths:
        if len(docx_paths) == 2:
            pair_label = " + ".join(os.path.basename(n) for _, n in docx_paths)
            inputs.append({"kind": "docx", "paths": [p for p, _ in docx_paths], "label": pair_label})
        else:
            for path, fname in docx_paths:
                inputs.append({"kind": "docx", "paths": [path], "label": os.path.basename(fname)})

    if not inputs:
        return jsonify({"error": "未发现 zip 或 docx 文件"}), 400

    JOBS[job_id] = {"status": "running", "progress": 0, "total": len(inputs),
                    "current": "", "items": [], "result_zip": None, "error": None}
    cfg = load_config()
    threading.Thread(target=process_job, args=(
        job_id, inputs, cfg, subject, grade, handout_type, academic_year, template_type
    ), daemon=True).start()
    return jsonify({"job_id": job_id, "total": len(inputs)})


@app.route("/api/jobs/<job_id>")
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "任务不存在"}), 404
    with JOBS_LOCK:
        return jsonify({k: v for k, v in job.items() if k != "result_zip"} |
                       {"has_result": bool(job.get("result_zip"))})


@app.route("/api/download/<job_id>")
def download(job_id):
    job = JOBS.get(job_id)
    if not job or not job.get("result_zip") or not os.path.exists(job["result_zip"]):
        return jsonify({"error": "结果不存在"}), 404
    return send_file(job["result_zip"], as_attachment=True, download_name=os.path.basename(job["result_zip"]))


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """浏览器关闭时通知，服务延迟优雅退出（不阻止浏览器卸载）"""
    print("浏览器已关闭，服务 2 秒后退出")
    import threading
    def _delayed_shutdown():
        import time, os as _os
        time.sleep(2)
        _os._exit(0)
    threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return jsonify({"ok": True})


def _open_browser_when_ready(url, port):
    """后台等服务端口就绪后再打开浏览器，避免过早打开连不上"""
    import socket, webbrowser
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
    import socket
    PORT = 5000
    URL = f"http://127.0.0.1:{PORT}"

    # 防止重复启动：如果端口已被占用（说明已有进程在服务），只打开浏览器
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        print(f"检测到已有服务运行在 {URL}，打开浏览器")
        import webbrowser
        try: webbrowser.open(URL)
        except: pass
        sys.exit(0)
    except (OSError, ConnectionRefusedError):
        pass  # 端口空闲，正常启动

    print(f"讲义生成器启动中... 访问 {URL}")
    from waitress import serve
    serve(app, host="127.0.0.1", port=PORT, threads=4)


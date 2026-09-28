# -*- coding: utf-8 -*-
"""
jobs.py —— 后台任务服务（与 Flask 路由分离）

职责：
  1. 任务表管理（JOBS：job_id → 状态/进度/结果）
  2. 输入解析（zip 解压 / docx 配对 → 教师版+学生版源）
  3. 后台线程逐项生成（教师版 → 学生版 → 打包 zip → 输出到桌面）

与旧版差异：
  - 不再往桌面写 api_debug.txt，统一走 logger（logs/ 目录）
  - 文件配对、打包等纯逻辑与路由完全解耦
"""
import os
import re
import sys
import json
import time
import uuid
import shutil
import zipfile
import tempfile
import threading
import traceback

import handout          # 引擎层（res/app 已在 sys.path）
import docutils
import config
import logger

log = logger.get_logger("jobs")

# ------------------------------------------------------------
# 任务表
# ------------------------------------------------------------
JOBS = {}
JOBS_LOCK = threading.Lock()

JOBS_DIR = os.path.join(tempfile.gettempdir(), "handout_jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

# 版本识别关键词
TEACHER_KW = ["教师", "解析", "答案", "教师版", "解析版"]
STUDENT_KW = ["学生", "学生版", "空白", "原卷", "原卷版"]


def _is_docx(name: str) -> bool:
    """识别 .docx（排除 .doc 旧格式与临时锁文件 ~$）"""
    base = os.path.basename(name)
    if base.startswith("~$"):
        return False
    return base.lower().endswith(".docx")


def _kill_orphan_word():
    """杀掉所有残留的 WINWORD 进程（Web 服务场景下无用户编辑风险）"""
    try:
        r = __import__("subprocess").run(
            ["taskkill", "/f", "/im", "WINWORD.EXE"],
            capture_output=True, timeout=10)
        if r.returncode == 0:
            log.info("已清理残留 Word 进程")
        time.sleep(1.5)  # 等进程完全退出、文件锁释放
    except Exception:
        pass


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
            for n, s in ordered:
                if n != teacher:
                    student = n
                    break
    return teacher, student


def topic_from_name(zip_name, docx_name):
    """授课主题提取：去修饰词只留核心主题，委托引擎层实现。"""
    fallback = os.path.splitext(os.path.basename(zip_name))[0] if zip_name else ""
    return handout.extract_topic(docx_name, fallback=fallback)


def _stage_docx_for_word(src_path, stage_dir, index):
    """Copy an archive member to an ASCII path before passing it to Word COM."""
    os.makedirs(stage_dir, exist_ok=True)
    staged_path = os.path.join(stage_dir, f"source_{index:02d}.docx")
    shutil.copy2(src_path, staged_path)
    return staged_path


def _resolve_pair(item, work):
    """
    把一个输入项归约为 (教师版源, 学生版源, topic, 源目录)。
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
        # Some legacy archives expose filenames that PowerShell/Word cannot encode
        # (for example, a replacement character from a GBK zip filename). Stage
        # selected sources under stable ASCII names without changing the archive.
        word_sources = os.path.join(extract_dir, "_word_sources")
        staged_teacher = _stage_docx_for_word(teacher, word_sources, 1)
        staged_student = None
        if student and student != teacher:
            staged_student = _stage_docx_for_word(student, word_sources, 2)
        return staged_teacher, staged_student, topic, extract_dir
    else:
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


def _build_one_version(label, src_path, out_path, topic, obj, diff, template,
                       template_type, grade, subject, handout_type, split_mode, api_key):
    """生成一份讲义（教师版/学生版通用），校验输出文件存在且非空。"""
    # 用完整扫描（含图片标志），让 build_version 做图片标题归属修正
    paras = docutils.scan_paragraphs(src_path)
    v, _ = handout.build_version(
        label, src_path, out_path, topic,
        paras=paras, objectives=obj, difficulties=diff,
        template=template, template_type=template_type,
        grade=grade, subject=subject, handout_type=handout_type,
        split_mode=split_mode, api_key=api_key)
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise RuntimeError(f"输出文件未正确生成或太小: {out_path}")
    extras = [out_path]
    if v.get("split_debug_path") and os.path.exists(v["split_debug_path"]):
        extras.append(v["split_debug_path"])
    return extras


def _prep_ideal(src_path: str, work: str) -> str:
    """
    整理模式预处理：抽例题（每个题型第一题移出题区）+ 题号重编。
    返回整理后 docx 路径（教师版/学生版源通用）。
    依赖 Word COM（_idealize / _renumber 两个 PS1），失败抛异常。
    """
    import subprocess
    import locale as _locale
    ps = docutils.POWERSHELL
    noex = os.path.join(work, "prep_noex.docx")
    renum = os.path.join(work, "prep_renum.docx")
    for f in (noex, renum, noex + ".summary.txt"):
        if os.path.exists(f):
            os.remove(f)
    r1 = subprocess.run(
        [ps, "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", config.PS_IDEALIZE,
         "-SrcPath", os.path.abspath(src_path), "-OutPath", os.path.abspath(noex)],
        capture_output=True, text=True, encoding=_locale.getpreferredencoding(),
        errors="replace", timeout=300)
    if r1.returncode != 0 or not os.path.exists(noex):
        raise RuntimeError(f"抽例题失败: {(r1.stderr or r1.stdout or '').strip()[:200]}")
    r2 = subprocess.run(
        [ps, "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", config.PS_RENUMBER,
         "-SrcPath", os.path.abspath(noex), "-OutPath", os.path.abspath(renum)],
        capture_output=True, text=True, encoding=_locale.getpreferredencoding(),
        errors="replace", timeout=300)
    if r2.returncode != 0 or not os.path.exists(renum):
        raise RuntimeError(f"题号重编失败: {(r2.stderr or r2.stdout or '').strip()[:200]}")
    return renum


def _set_stage(job, text: str):
    """更新阶段进度（前端进度条下方显示）。"""
    with JOBS_LOCK:
        job["stage"] = text


def process_job(job_id, inputs, cfg, subject="数学", grade="", handout_type="",
                academic_year="", template_type="1v1", split_mode="smart"):
    """后台线程：逐个输入项处理，统一输出 教师版+学生版 两份，更新进度。"""
    job = JOBS[job_id]
    work = os.path.join(JOBS_DIR, job_id)
    out_dir = os.path.join(work, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    api_key = ""
    # Flash 1.1：API 默认停用（API_ENABLED=False 时不读取、不设置环境变量，纯离线）
    if config.API_ENABLED and cfg.get("api_key"):
        api_key = cfg["api_key"]
        os.environ["DEEPSEEK_API_KEY"] = api_key  # 传给 llm_split
    produced = []
    template = handout.CLASS_TEMPLATE if template_type == "class" else handout.DEFAULT_TEMPLATE

    try:
        for ii, item in enumerate(inputs):
            label = item["label"]
            with JOBS_LOCK:
                job["progress"] = ii
                job["current"] = label
            row = {"zip": label, "topic": "", "teacher": "处理中", "student": "—"}
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
                _set_stage(job, f"读取 {label}")
                t_src = teacher
                if split_mode == "ideal":
                    _set_stage(job, f"抽例题+重编号：{topic}")
                    t_src = _prep_ideal(teacher, work)
                _set_stage(job, f"生成教师版：{topic}")
                paras_t = handout._body_paragraphs(t_src)
                obj, diff = handout.make_objectives(subject, topic, api_key, paras=paras_t)
                t_out_name = handout.build_filename(subject, grade, handout_type, topic, "教师版", academic_year)
                t_out = os.path.join(out_dir, t_out_name)
                produced.extend(_build_one_version(
                    "教师版", t_src, t_out, topic, obj, diff, template,
                    template_type, grade, subject, handout_type, split_mode, api_key))
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
                    _set_stage(job, f"生成学生版源：{topic}")
                    stu_src = os.path.join(base_dir, "_stu_src.docx")
                    n_red, n_del, n_q, n_blk, mlog = handout.make_student(teacher, stu_src)
                    log.info("[%s] 学生版生成：清红色 %s 段，删标记 %s 段，简答 %s 题 +%s 空行",
                             label, n_red, n_del, n_q, n_blk)
                if split_mode == "ideal":
                    _set_stage(job, f"抽例题+重编号（学生版）：{topic}")
                    stu_src = _prep_ideal(stu_src, work)
                _set_stage(job, f"生成学生版：{topic}")
                s_out_name = handout.build_filename(subject, grade, handout_type, topic, "学生版", academic_year)
                s_out = os.path.join(out_dir, s_out_name)
                produced.extend(_build_one_version(
                    "学生版", stu_src, s_out, topic, obj, diff, template,
                    template_type, grade, subject, handout_type, split_mode, api_key))
                row["student"] = "完成"
            except Exception as e:
                row["student"] = f"失败: {e}"
                job.setdefault("warnings", []).append(f"{label} 学生版: {e}")

            time.sleep(1)

        # —— 打包：下载包用第一个源文件的标题命名 ——
        if produced:
            first_label = inputs[0].get("label", "讲义") if inputs else "讲义"
            first_label = os.path.splitext(os.path.basename(first_label))[0]  # 去扩展名
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

                # 自动输出到桌面「生成讲义结果」，无需下载
                try:
                    desk_dir = os.path.join(os.path.expanduser("~"), "Desktop", "生成讲义结果")
                    os.makedirs(desk_dir, exist_ok=True)
                    for f in existing:
                        shutil.copy2(f, os.path.join(desk_dir, os.path.basename(f)))
                    log.info("[job %s] 已输出到桌面: %s", job_id, desk_dir)
                except Exception as e:
                    log.warning("[job %s] 桌面输出失败: %s", job_id, e)
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

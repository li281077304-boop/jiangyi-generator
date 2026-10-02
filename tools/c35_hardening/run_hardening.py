"""C3.5 pre-release hardening harness: stress, stability, recovery, bad input.

This harness adds no product capability. It only exercises the existing
production path under load, interruption and hostile input, and reports what
actually happened.

Subcommands (``--case``):

- ``batch10`` / ``batch20``  — 10 / 20 logical item batches, real sources
- ``consecutive``            — N batch jobs in one process, no restart
- ``restart-a|b|c``          — queued / running / partially done interruption
- ``abnormal``               — corrupt, empty, ``~$``, long/duplicate names, ZIPs
- ``collision``              — the same topic generated twice
- ``serial-fallback``        — XML items plus two COM fallbacks in one batch
- ``delivery``               — user result directory cleanliness

Usage:
    python run_hardening.py --case batch10 --out <json>
"""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import argparse
import ctypes
import json
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "v1.2-xml-experiment" / "res" / "app"
PERF_DIR = ROOT / "tools" / "c3_performance"
sys.path.insert(0, str(PERF_DIR))
sys.path.insert(0, str(APP_DIR / "webapp"))
sys.path.insert(0, str(APP_DIR))

from wps_monitor import (DEFAULT_NAMES, ProcessMonitor, own_rss_bytes, settle,  # noqa: E402
                         snapshot)
from run_c3_performance import (C2_CASE_A_SOURCES, C2_CASE_B_SOURCES, Instrumentation,  # noqa: E402
                                corpus_files, x008_files)

CORPUS = Path(r"C:\xml-uat\stage3-expansion")
DEFAULT_WORK = Path(r"C:\xml-uat\c35-hardening")
FORBIDDEN_NAMES = ("job.json", "runtime", "work", "staging", "logs", "diagnostic", "temp")
FORBIDDEN_SUFFIXES = (".zip", ".json", ".log", ".tmp")


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


def configure(results_root: Path, runtime_root: Path, **extra):
    import app as shell
    results_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    shell.app.config.update(TESTING=True, RESULT_ROOT=results_root, RUNTIME_ROOT=runtime_root,
                            C0_DISABLE_JOB_SUBMISSION=False, C0_RUN_JOBS_SYNCHRONOUSLY=True,
                            C0_FORCE_FALLBACK_REASON=None, STUDENTIZER_EVIDENCE_PROVIDER=None,
                            STUDENTIZER_REVIEWED_MANIFEST_DIR=None,
                            OPEN_FOLDER=lambda _path: None)
    shell.app.config.update(extra)
    return shell


def submit(shell, files, template="1v1", **form):
    client = shell.app.test_client()
    payload = {"template_type": template, "split_mode": "smart", "docx_mode": "auto",
               "files": [(BytesIO(data), name) for name, data in files]}
    payload.update(form)
    started = time.perf_counter()
    with redirect_stdout(StringIO()):
        response = client.post("/api/jobs", data=payload, content_type="multipart/form-data")
    elapsed = round(time.perf_counter() - started, 3)
    if response.status_code != 202:
        raise SystemExit("submission rejected: %s" % response.get_json())
    job_id = response.get_json()["job_id"]
    final = client.get("/api/jobs/" + job_id).get_json()
    return final, elapsed, client


def item_rows(final):
    rows = []
    for item in final.get("items", []):
        preparation = item.get("student_preparation") or {}
        rows.append({"item_id": item.get("item_id"), "topic": item.get("topic"),
                     "status": item.get("status"), "renderer": item.get("renderer"),
                     "fallback_reason": item.get("fallback_reason"),
                     "teacher": item.get("teacher"), "student": item.get("student"),
                     "error": item.get("error"),
                     "studentizer_status": preparation.get("status"),
                     "studentizer_reason": preparation.get("reason_code"),
                     "make_student_called": bool(preparation.get("make_student_called")),
                     "outputs": len(item.get("output_paths") or [])})
    return rows


def summarise(final, elapsed, monitor, instrumentation):
    rows = item_rows(final)
    return {
        "status": final.get("status"), "batch_outcome": final.get("batch_outcome"),
        "total_items": final.get("total"),
        "done": sum(row["status"] == "done" for row in rows),
        "failed": sum(row["status"] == "error" for row in rows),
        "xml_items": sum(row["renderer"] == "XML" for row in rows),
        "fallback_items": sum(row["renderer"] == "V0.9" for row in rows),
        "fallback_reasons": sorted({row["fallback_reason"] for row in rows
                                    if row["fallback_reason"]}),
        "elapsed_seconds": elapsed,
        "seconds_per_item": round(elapsed / max(final.get("total") or 1, 1), 3),
        "outputs": len(final.get("output_paths", [])),
        "items": rows,
        "process_monitor": monitor,
        "instrumentation": instrumentation,
    }


def run_batch(case, files, template, work: Path, note=""):
    run_root = work / ("run-%s" % stamp())
    shell = configure(run_root / "results", run_root / "runtime")
    instrumentation = Instrumentation().install()
    monitor = ProcessMonitor().start()
    rss_before = own_rss_bytes()
    started_utc = utc()
    try:
        final, elapsed, _client = submit(shell, files, template)
    finally:
        monitor_result = monitor.stop()
        metrics = instrumentation.summary()
        instrumentation.uninstall()
    rss_after = own_rss_bytes()
    result = summarise(final, elapsed, monitor_result, metrics)
    result.update({"case": case, "note": note, "template": template,
                   "started_utc": started_utc, "ended_utc": utc(),
                   "work_dir": str(run_root),
                   "result_dir": final.get("result_dir"),
                   "rss_bytes_before": rss_before, "rss_bytes_after": rss_after})
    result["result_files"] = _result_inventory(Path(final["result_dir"])) if final.get("result_dir") else {}
    result["residual_after_settle"] = settle(set(monitor_result.get("baseline_live") or []))
    return result


def _result_inventory(result_dir: Path):
    if not result_dir.is_dir():
        return {}
    files = [path for path in result_dir.rglob("*") if path.is_file()]
    internal = lambda name: (name.startswith(".") or "-stage-" in name.lower()
                             or "-output-" in name.lower() or "v09-student" in name.lower())
    return {"file_count": len(files),
            "docx_count": sum(path.suffix.lower() == ".docx" for path in files),
            "non_docx": sorted(path.name for path in files if path.suffix.lower() != ".docx")[:20],
            "internal_artifacts": sorted(path.name for path in files if internal(path.name))[:20],
            "underscore_names": sorted(path.name for path in files if "_" in path.name)[:20],
            "folder_names": sorted({path.parent.name for path in files})[:30]}


def build_batch_files(count):
    """Stress workload of ``count`` distinct logical items.

    Half are repeats of the single approved X008 source and half are cycled real
    sources. Every item gets its own natural topic name so the batch resolver
    never sees an ambiguous same-topic duplicate: duplicated *input names* are a
    legitimate fail-closed case, but they would silently reduce the item count
    this stress run is supposed to reach.
    """
    files = []
    repeated = x008_files(count // 2)
    files.extend(repeated)
    real = corpus_files(C2_CASE_A_SOURCES)
    remainder = count - len(repeated)
    for index in range(remainder):
        name, data = real[index % len(real)]
        files.append(("专题%02d 教师版.docx" % (len(repeated) + index + 1), data))
    return files


def case_batch(count, work):
    return run_batch("batch%d" % count, build_batch_files(count), "1v1", work,
                     ("稳定性/压力 workload：%d 个 teacher-only item，由已批准 X008 与真实样本循环组成。"
                      "含重复源文件，仅用于压力与性能，不代表语料覆盖率。" % count))


def case_consecutive(jobs, items, work):
    """Run N batch jobs in one process without any restart."""
    run_root = work / ("consecutive-%s" % stamp())
    shell = configure(run_root / "results", run_root / "runtime")
    per_job = []
    monitor = ProcessMonitor(interval=0.2).start()
    rss_samples = []
    for index in range(jobs):
        # Fewer than three files is a single (paired) submission, not a batch,
        # so even-indexed jobs always use three teacher-only items.
        files = (x008_files(max(items, 3)) if index % 2 == 0 else
                 corpus_files(C2_CASE_B_SOURCES))
        template = "1v1" if index % 2 == 0 else "class"
        instrumentation = Instrumentation().install()
        try:
            final, elapsed, _client = submit(shell, files, template)
        finally:
            metrics = instrumentation.summary()
            instrumentation.uninstall()
        rows = item_rows(final)
        per_job.append({"job": index + 1, "elapsed_seconds": elapsed,
                        "status": final.get("status"),
                        "done": sum(row["status"] == "done" for row in rows),
                        "failed": sum(row["status"] == "error" for row in rows),
                        "xml_items": sum(row["renderer"] == "XML" for row in rows),
                        "fallback_items": sum(row["renderer"] == "V0.9" for row in rows),
                        "outputs": len(final.get("output_paths", [])),
                        "com_script_invocations": metrics.get("com_script_invocations", 0),
                        "rss_bytes": own_rss_bytes()})
        rss_samples.append(own_rss_bytes())
    monitor_result = monitor.stop()
    half = max(len(per_job) // 2, 1)
    first_avg = sum(job["elapsed_seconds"] for job in per_job[:half]) / half
    last_avg = sum(job["elapsed_seconds"] for job in per_job[half:]) / max(len(per_job) - half, 1)
    valid_rss = [value for value in rss_samples if value]

    def drift(kind):
        """Per-kind elapsed drift: comparing mixed kinds would be meaningless."""
        chosen = [job for job in per_job if (job["fallback_items"] > 0) == (kind == "com")]
        if len(chosen) < 2:
            return None
        middle = max(len(chosen) // 2, 1)
        head = sum(job["elapsed_seconds"] for job in chosen[:middle]) / middle
        tail = sum(job["elapsed_seconds"] for job in chosen[middle:]) / (len(chosen) - middle)
        return {"jobs": len(chosen), "first_half_avg": round(head, 3),
                "second_half_avg": round(tail, 3),
                "ratio": round(tail / head, 3) if head else None,
                "min": round(min(job["elapsed_seconds"] for job in chosen), 3),
                "max": round(max(job["elapsed_seconds"] for job in chosen), 3)}

    return {"case": "consecutive", "jobs": jobs, "items_per_job": items,
            "started_utc": utc(), "ended_utc": utc(), "work_dir": str(run_root),
            "jobs_detail": per_job,
            "first_half_avg_seconds": round(first_avg, 3),
            "second_half_avg_seconds": round(last_avg, 3),
            "mixed_slowdown_ratio": round(last_avg / first_avg, 3) if first_avg else None,
            "drift_com_fallback_jobs": drift("com"),
            "drift_xml_jobs": drift("xml"),
            "rss_first": valid_rss[0] if valid_rss else None,
            "rss_last": valid_rss[-1] if valid_rss else None,
            "rss_growth_bytes": (valid_rss[-1] - valid_rss[0]) if len(valid_rss) > 1 else None,
            "process_monitor": monitor_result,
            "residual_after_settle": settle(set(monitor_result.get("baseline_live") or [])),
            "result_files": _result_inventory(run_root / "results")}


def case_abnormal(work):
    """One batch containing every hostile input; a bad item must not kill others."""
    good = corpus_files(["X001"])[0]
    valid = make_minimal_docx(["知识点：加法", "1．求 2+3？", "【答案】5"])
    files = [
        ("损坏 教师版.docx", b"C35 deliberately broken DOCX safe fixture"),
        ("空文档 教师版.docx", make_empty_zip_docx()),
        ("~$临时讲义 教师版.docx", valid),
        ("专题02 电压 电阻＆欧姆定律（期末复习讲义）解析版.docx", good[1]),
        ("这是一个非常非常长的中文文件名称用于验证超长中文路径在批量解析与结果目录命名中的行为" * 3 + " 教师版.docx", valid),
        ("重复名称 教师版.docx", valid),
        ("重复名称 教师版.docx", valid),
        ("同名 教师版.docx", valid),
        ("同名 学生版.docx", valid),
    ]
    nested = make_nested_chinese_zip([good, ("资料/子目录/第二层/" + good[0], good[1])])
    files.append((nested[0], nested[1]))
    mixed = make_mixed_zip([good, ("损坏 教师版.docx", b"broken inside zip")])
    files.append((mixed[0], mixed[1]))
    result = run_batch("abnormal", files, "1v1", work,
                       "异常输入批次：损坏、空包、~$、超长中文名、重复名、同名师生、嵌套中文 ZIP、"
                       "ZIP 内部分损坏。")
    result["zip_path_traversal"] = case_traversal(work)
    return result


def case_traversal(work):
    """A path-traversal member is rejected at submission and writes nothing."""
    good = corpus_files(["X001"])[0]
    run_root = work / ("traversal-%s" % stamp())
    shell = configure(run_root / "results", run_root / "runtime")
    client = shell.app.test_client()
    name, payload = make_traversal_zip(good)
    with redirect_stdout(StringIO()):
        response = client.post("/api/jobs", data={
            "template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
            "files": [(BytesIO(payload), name)]}, content_type="multipart/form-data")
    escaped = sorted(str(path) for path in (Path(r"C:\xml-uat\c35-path-traversal-evil.docx"),
                                            ROOT / "c35-path-traversal-evil.docx") if path.exists())
    return {"http_status": response.status_code, "json": response.get_json(),
            "work_dir": str(run_root), "files_written_outside": escaped}


def make_minimal_docx(paragraphs):
    from docx import Document
    buffer = BytesIO()
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def make_empty_zip_docx():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        package.writestr("no-document.xml", b"<empty/>")
    return buffer.getvalue()


def make_nested_chinese_zip(entries):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for name, data in entries:
            package.writestr(name, data)
    return "中文多层专题素材.zip", buffer.getvalue()


def make_traversal_zip(good):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("../../c35-path-traversal-evil.docx", good[1])
        package.writestr("资料/" + good[0], good[1])
    return "穿越测试.zip", buffer.getvalue()


def make_mixed_zip(entries):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for name, data in entries:
            package.writestr(name, data)
    return "部分损坏专题素材.zip", buffer.getvalue()


def case_collision(work):
    """Generate the same topic twice; the second must not overwrite the first."""
    same = corpus_files(["X001"])
    results = []
    directories = []
    for attempt in (1, 2, 3):
        result = run_batch("collision-%d" % attempt, same, "1v1", work,
                           "第 %d 次生成同一专题，验证不静默覆盖旧成品。" % attempt)
        results.append({"attempt": attempt, "status": result["status"],
                        "elapsed_seconds": result["elapsed_seconds"],
                        "result_dir": result["result_dir"],
                        "outputs": result["outputs"]})
        directories.append(result["result_dir"])
    return {"case": "collision", "note": "连续三次生成同一专题", "runs": results,
            "distinct_result_dirs": sorted(set(directories)),
            "all_distinct": len(set(directories)) == len(directories),
            "started_utc": utc(), "ended_utc": utc()}


def case_serial_fallback(work):
    """XML items plus two COM fallbacks in one batch; fallbacks must serialise."""
    files = list(corpus_files(C2_CASE_B_SOURCES))  # three XML teacher+student pairs
    files += x008_files(2)  # two teacher-only reviewed items -> COM fallback
    result = run_batch("serial-fallback", files, "class", work,
                       "混合批次：多个 XML 支持的教师+学生对 + 两个必须走 COM 回退的 teacher-only item。")
    result["fallback_detail"] = {
        "fallback_items": result["fallback_items"],
        "xml_items": result["xml_items"],
        "failed": result["failed"],
        "all_successful_items_done": result["done"] == result["total_items"],
    }
    return result


def case_delivery(work):
    """Scan every generated result directory for internal artefacts."""
    violations = []
    scanned = 0
    checked_dirs = 0
    for result_root in sorted(work.glob("*/results")):
        for result_dir in sorted(p for p in result_root.rglob("*") if p.is_dir()):
            files = [path for path in result_dir.rglob("*") if path.is_file()]
            checked_dirs += 1
            scanned += len(files)
            for path in files:
                lowered = path.name.lower()
                if (lowered in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES
                        or "_" in path.name):
                    violations.append({"dir": str(result_dir), "name": path.name})
    return {"case": "delivery", "work_dir": str(work), "checked_dirs": checked_dirs,
            "checked_files": scanned, "violations": violations[:50],
            "violation_count": len(violations), "started_utc": utc(), "ended_utc": utc()}


CHILD_PHASES = ("prepare", "resume")


def child_prepare(scenario, work, target_stage=None):
    """Create the job state, then stay alive so the driver can kill this process."""
    run_root = work / ("restart-%s-%s" % (scenario.lower(), stamp()))
    shell = configure(run_root / "results", run_root / "runtime")
    state = {"work_dir": str(run_root), "phase": "prepare", "scenario": scenario}
    if scenario == "A":
        shell.app.config["C0_DISABLE_JOB_SUBMISSION"] = True
        final, _elapsed, _client = submit(shell, build_batch_files(3), "1v1")
        state["job_ids"] = [final["job_id"]]
        state["statuses_before_kill"] = [final["status"]]
    elif scenario == "B":
        # A single (non-batch) teacher-only job interrupted mid-generation.
        shell.app.config["C0_DISABLE_JOB_SUBMISSION"] = True
        created, _elapsed, _client = submit(shell, build_batch_files(1), "1v1")
        state["job_ids"] = [created["job_id"]]
        state["statuses_before_kill"] = [created["status"]]
        state["is_batch"] = bool(created.get("is_batch"))
        shell.app.config["C0_DISABLE_JOB_SUBMISSION"] = False
        if target_stage:
            marker_path = Path(run_root) / "stage-hit.json"

            def hold_at_target(_job_id, stage):
                if stage == target_stage:
                    marker_path.write_text(json.dumps({"stage": stage, "utc": utc()},
                                                      ensure_ascii=False), encoding="utf-8")
                    time.sleep(600)

            shell.app.config["C35_TEST_STAGE_HOOK"] = hold_at_target
        import threading
        worker = threading.Thread(target=shell._execute_job, args=(created["job_id"],), daemon=True)
        worker.start()
        state["worker_started"] = True
    else:
        # A batch interrupted while some items are already finished.
        shell.app.config["C0_DISABLE_JOB_SUBMISSION"] = True
        created, _elapsed, _client = submit(shell, build_batch_files(3), "1v1")
        state["job_ids"] = [created["job_id"]]
        state["statuses_before_kill"] = [created["status"]]
        state["is_batch"] = bool(created.get("is_batch"))
        shell.app.config["C0_DISABLE_JOB_SUBMISSION"] = False
        import threading
        worker = threading.Thread(target=shell._execute_job, args=(created["job_id"],), daemon=True)
        worker.start()
        state["worker_started"] = True
    (Path(run_root) / "marker.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False), flush=True)
    time.sleep(600)
    return 0


def child_resume(scenario, work_dir):
    """New process: recovery must requeue or complete without losing successes."""
    from job_service import JobService
    run_root = Path(work_dir)
    marker = run_root / "marker.json"
    before = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    shell = configure(run_root / "results", run_root / "runtime")
    service = JobService(run_root / "results", runtime_root=run_root / "runtime",
                         opener=lambda _path: None)
    queued = [record["job_id"] for record in service.list() if record.get("status") == "queued"]
    recovered = []
    preserved_before = {}
    for job_id in queued:
        record = service.get(job_id)
        recovered.append(record["status"])
        if record.get("is_batch"):
            preserved_before[job_id] = [
                {"topic": item.get("topic"), "output_paths": item.get("output_paths") or [],
                 "sha256": [sha256(Path(path).read_bytes()).hexdigest()
                            for path in (item.get("output_paths") or []) if Path(path).is_file()]}
                for item in record.get("items", []) if item.get("status") == "done"]
    with redirect_stdout(StringIO()):
        client = shell.app.test_client()
        client.get("/api/jobs")  # triggers resume of queued jobs
    final_statuses = []
    for job_id in before.get("job_ids", []):
        final_statuses.append(service.get(job_id))
    rows = []
    preserved_after = {}
    for record in final_statuses:
        if record.get("is_batch"):
            preserved_after[record["job_id"]] = [
                {"topic": item.get("topic"), "output_paths": item.get("output_paths") or [],
                 "sha256": [sha256(Path(path).read_bytes()).hexdigest()
                            for path in (item.get("output_paths") or []) if Path(path).is_file()]}
                for item in record.get("items", []) if item.get("status") == "done"]
            for item in record.get("items", []):
                rows.append({"topic": item.get("topic"), "status": item.get("status"),
                             "renderer": item.get("renderer"),
                             "outputs": len(item.get("output_paths") or [])})
        else:
            item = (record.get("items") or [{}])[0]
            rows.append({"topic": item.get("topic"), "status": record.get("status"),
                         "renderer": record.get("renderer"),
                         "outputs": len(record.get("output_paths") or []),
                         "output_paths": record.get("output_paths") or []})
    def done_by_topic(groups):
        return {job_id: {item["topic"]: item["sha256"] for item in items}
                for job_id, items in groups.items()}
    before_hashes, after_hashes = done_by_topic(preserved_before), done_by_topic(preserved_after)
    preserved = all(after_hashes.get(job_id, {}).get(topic) == hashes
                    for job_id, topics in before_hashes.items()
                    for topic, hashes in topics.items())
    return {"case": "restart-%s" % scenario.lower(), "work_dir": str(run_root),
            "statuses_before_kill": before.get("statuses_before_kill", []),
            "queued_after_recovery": queued,
            "recovered_statuses": recovered,
            "final_status": [record.get("status") for record in final_statuses],
            "batch_outcome": [record.get("batch_outcome") for record in final_statuses],
            "items": rows,
            "done_items": sum(row["status"] == "done" for row in rows),
            "failed_items": sum(row["status"] == "error" for row in rows),
            "outputs": sum(row["outputs"] for row in rows),
            "completed_outputs_before_resume": preserved_before,
            "completed_outputs_after_resume": preserved_after,
            "completed_outputs_preserved": preserved,
            "result_files": _result_inventory(run_root / "results"),
            "started_utc": utc(), "ended_utc": utc()}


def case_restart(scenario, work, wait_seconds=None, target_stage=None):
    """Driver: start a child, kill it, then start a fresh process to resume."""
    here = Path(__file__).resolve()
    python = sys.executable
    child_out = work / "child-state.json"
    prepare = subprocess.Popen([python, str(here), "--case", "_child", "--out", str(child_out),
                                "--scenario", scenario, "--work", str(work), "--phase", "prepare",
                                "--target-stage", target_stage or ""],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    state = None
    deadline = time.time() + 120
    while time.time() < deadline:
        line = prepare.stdout.readline()
        if not line:
            break
        if line.startswith("{"):
            state = json.loads(line)
            break
    if state is None:
        prepare.kill()
        prepare.wait(timeout=30)
        raise SystemExit("restart-%s: prepare child produced no state: %s"
                         % (scenario, (prepare.stdout.read() or "").strip()[:400]))
    stage_marker = None
    if target_stage:
        marker_path = Path(state["work_dir"]) / "stage-hit.json"
        deadline = time.time() + 240.0
        while time.time() < deadline and prepare.poll() is None:
            try:
                stage_marker = json.loads(marker_path.read_text(encoding="utf-8"))
                if stage_marker.get("stage") == target_stage:
                    break
                stage_marker = None
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        if not stage_marker:
            prepare.kill()
            prepare.wait(timeout=30)
            raise SystemExit("restart-%s: target stage was not reached: %s"
                             % (scenario, target_stage))
        wait_seconds = round(time.time() - (deadline - 240.0), 3)
    elif scenario == "C" and wait_seconds is None:
        # Stop at the first real partial-progress boundary: a completed sibling
        # is published and the parent has advanced to another item.
        deadline = time.time() + 240.0
        while time.time() < deadline:
            path = Path(state["work_dir"]) / "runtime" / state["job_ids"][0] / "job.json"
            try:
                parent = json.loads(path.read_text(encoding="utf-8"))
                done = sum(item.get("status") == "done" for item in parent.get("items", []))
                if done >= 1 and parent.get("current_topic"):
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        else:
            raise SystemExit("restart-C: no completed sibling followed by an active topic within 240s")
        wait_seconds = round(time.time() - (deadline - 240.0), 3)
    elif wait_seconds is None:
        wait_seconds = {"A": 8.0, "B": 25.0}.get(scenario, 60.0)
        time.sleep(wait_seconds)
    else:
        time.sleep(wait_seconds)
    persisted_at_kill = []
    runtime_root = Path(state["work_dir"]) / "runtime"
    for job_id in state.get("job_ids", []):
        path = runtime_root / job_id / "job.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            persisted_at_kill.append({"job_id": job_id, "status": record.get("status"),
                                      "stage": record.get("stage"),
                                      "progress": record.get("progress"),
                                      "current_topic": record.get("current_topic"),
                                      "completed": record.get("completed"),
                                      "items": [{"topic": item.get("topic"),
                                                 "status": item.get("status"),
                                                 "outputs": item.get("output_paths", [])}
                                                for item in record.get("items", [])]})
        except (OSError, ValueError):
            persisted_at_kill.append({"job_id": job_id, "error": "unable to read persisted job state"})
    killed_at = utc()
    prepare.kill()
    prepare.wait(timeout=30)
    time.sleep(2.0)
    work_dir = Path(state["work_dir"])
    private_work = work_dir / "runtime" / state["job_ids"][0] / "work"
    scratch_at_kill = sorted(str(path.relative_to(private_work)) for path in private_work.iterdir()
                             if path.is_file() and not path.name.startswith("input-")) if private_work.is_dir() else []
    resume = subprocess.run([python, str(here), "--case", "_child", "--out", str(child_out),
                             "--scenario", scenario, "--work", str(work), "--phase", "resume",
                             "--work-dir", str(state["work_dir"])],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            timeout=1800)
    payload = None
    for line in resume.stdout.splitlines():
        if line.strip().startswith("{"):
            payload = json.loads(line)
    return {"case": "restart-%s" % scenario.upper(), "killed_at_utc": killed_at,
            "wait_seconds": wait_seconds, "target_stage": target_stage,
            "stage_marker": stage_marker,
            "killed_while": (persisted_at_kill[0].get("status") if persisted_at_kill else None),
            "persisted_at_kill": persisted_at_kill,
            "private_scratch_at_kill": scratch_at_kill,
            "prepare_state": state, "resume": payload,
            "resume_returncode": resume.returncode,
            "started_utc": utc(), "ended_utc": utc()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument("--items", type=int, default=3)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--phase", default=None)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--wait-seconds", type=float, default=None)
    parser.add_argument("--target-stage", default=None)
    args = parser.parse_args(argv)

    if args.case == "_child":
        if args.phase == "prepare":
            raise SystemExit(child_prepare(args.scenario, args.work, args.target_stage))
        if args.phase == "resume":
            payload = child_resume(args.scenario, Path(args.work_dir))
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            return 0

    cases = {
        "batch10": lambda: case_batch(10, args.work),
        "batch20": lambda: case_batch(20, args.work),
        "consecutive": lambda: case_consecutive(args.jobs, args.items, args.work),
        "restart-a": lambda: case_restart("A", args.work, args.wait_seconds),
        "restart-b": lambda: case_restart("B", args.work, args.wait_seconds, args.target_stage),
        "restart-c": lambda: case_restart("C", args.work, args.wait_seconds),
        "abnormal": lambda: case_abnormal(args.work),
        "collision": lambda: case_collision(args.work),
        "serial-fallback": lambda: case_serial_fallback(args.work),
        "delivery": lambda: case_delivery(args.work),
    }
    if args.case not in cases:
        raise SystemExit("unknown case: %s" % args.case)
    result = cases[args.case]()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("case", "status", "total_items", "done", "failed", "xml_items",
                       "fallback_items", "elapsed_seconds", "outputs")
                      if key in result}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

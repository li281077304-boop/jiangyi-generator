"""C3 real teacher-only / XML batch performance harness.

Drives the production HTTP path with the real A-Line, real C1 Slot Router, real
B-Line renderer, real templates and the real frozen V0.9 runtime. Only
observation wrappers are installed; no production decision is replaced.

Measured per case:

- Studentizer time (production-persisted ``studentizer_elapsed_seconds``)
- A-Line time (wrapper around the exact ``slot_router.analyze_source`` call)
- Slot Router time (plan total minus A-Line)
- XML Renderer time (wrapper around ``template_slot_composer.render_slots``)
- package validation time (wrapper around every ``validate_package`` entry point)
- total wall time, COM script invocations, ``make_student`` calls and
  ``make_student`` time, newly started office process instances

Usage:
    python run_c3_performance.py --case all --out <json> [--report <md>]
"""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "v1.2-xml-experiment/res/app"
sys.path.insert(0, str(APP_DIR / "webapp"))
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wps_monitor import ProcessMonitor  # noqa: E402

CORPUS = Path(r"C:\xml-uat\stage3-expansion")
C2_INPUTS = Path(r"C:\xml-uat\c2-round6-20261001-0822\inputs")
X008_APPROVED_SHA = "56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4"
C2_CASE_A_SECONDS = 121.330
C2_CASE_A_ITEMS = 5
C2_CASE_B_SECONDS = 13.975
C2_CASE_B_ITEMS = 3

C2_CASE_A_SOURCES = ("X001", "X004", "X006", "X023", "X025")
C2_CASE_B_SOURCES = ("X001", "X002", "X020", "X019", "X023", "X021")


class Instrumentation:
    """Observation-only wrappers around the real production callables."""

    def __init__(self):
        self.counters: dict[str, int] = {}
        self.seconds: dict[str, float] = {}
        self.events: list[dict] = []
        self._undo: list = []
        self._in_router = False

    def _add(self, count_key, seconds_key, seconds, **values):
        self.counters[count_key] = self.counters.get(count_key, 0) + 1
        self.seconds[seconds_key] = round(self.seconds.get(seconds_key, 0.0) + seconds, 6)
        if values:
            self.events.append({"kind": count_key, "seconds": round(seconds, 6), **values})

    def install(self):
        import package_validator
        import job_service
        import renderer_orchestrator
        import slot_router
        import studentizer
        import studentizer_planner
        import template_slot_composer

        original_run = subprocess.run

        def tracked_run(args, *positional, **kwargs):
            script = None
            if isinstance(args, (list, tuple)) and "-File" in args:
                candidate = str(args[args.index("-File") + 1])
                script = candidate if candidate.endswith(".ps1") else None
            start = time.perf_counter()
            try:
                return original_run(args, *positional, **kwargs)
            finally:
                if script:
                    self._add("com_script_invocations", "com_script_seconds",
                              time.perf_counter() - start, script=script)

        subprocess.run = tracked_run
        self._undo.append(lambda: setattr(subprocess, "run", original_run))

        engine = renderer_orchestrator._load_v09_engine()
        original_make_student = engine.make_student

        def tracked_make_student(source, output):
            start = time.perf_counter()
            try:
                return original_make_student(source, output)
            finally:
                self._add("make_student_calls", "make_student_seconds", time.perf_counter() - start)

        engine.make_student = tracked_make_student
        self._undo.append(lambda: setattr(engine, "make_student", original_make_student))

        original_analyze = slot_router.analyze_source

        def tracked_analyze(*args, **kwargs):
            start = time.perf_counter()
            try:
                return original_analyze(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                self._add("aline_calls", "aline_seconds", elapsed)
                if self._in_router:
                    self._add("slot_router_aline_calls", "slot_router_aline_seconds", elapsed)

        slot_router.analyze_source = tracked_analyze
        self._undo.append(lambda: setattr(slot_router, "analyze_source", original_analyze))
        # The reviewed coverage gate calls A-Line through its own module-level
        # binding; time that too so the A-Line figure is not understated.
        original_gate_analyze = studentizer_planner.analyze_source
        studentizer_planner.analyze_source = tracked_analyze
        self._undo.append(lambda: setattr(studentizer_planner, "analyze_source", original_gate_analyze))

        original_build = slot_router.build_slot_routing_plan

        def tracked_build(*args, **kwargs):
            start = time.perf_counter()
            self._in_router = True
            try:
                return original_build(*args, **kwargs)
            finally:
                self._in_router = False
                self._add("slot_router_total_calls", "slot_router_total_seconds",
                          time.perf_counter() - start)

        slot_router.build_slot_routing_plan = tracked_build
        self._undo.append(lambda: setattr(slot_router, "build_slot_routing_plan", original_build))

        original_render = template_slot_composer.render_slots

        def tracked_render(*args, **kwargs):
            start = time.perf_counter()
            try:
                return original_render(*args, **kwargs)
            finally:
                self._add("xml_renderer_calls", "xml_renderer_seconds", time.perf_counter() - start)

        template_slot_composer.render_slots = tracked_render
        self._undo.append(lambda: setattr(template_slot_composer, "render_slots", original_render))

        original_validate = package_validator.validate_package

        def tracked_validate(*args, **kwargs):
            start = time.perf_counter()
            try:
                return original_validate(*args, **kwargs)
            finally:
                self._add("package_validation_calls", "package_validation_seconds",
                          time.perf_counter() - start)

        for module in (package_validator, studentizer, template_slot_composer, job_service):
            if getattr(module, "validate_package", None) is original_validate:
                self._undo.append(lambda m=module: setattr(m, "validate_package", original_validate))
                module.validate_package = tracked_validate
        return self

    def uninstall(self):
        for undo in reversed(self._undo):
            undo()
        self._undo.clear()

    def summary(self):
        keys = ("com_script_invocations", "make_student_calls", "aline_calls",
                "slot_router_total_calls", "slot_router_aline_calls", "xml_renderer_calls",
                "package_validation_calls")
        result = {key: self.counters.get(key, 0) for key in keys}
        for key, value in self.counters.items():
            result.setdefault(key, value)
        seconds = {key: round(self.seconds.get(key, 0.0), 6) for key in
                   ("aline_seconds", "slot_router_aline_seconds", "slot_router_total_seconds",
                    "xml_renderer_seconds", "package_validation_seconds", "make_student_seconds",
                    "com_script_seconds")}
        result["seconds"] = seconds
        result["slot_router_seconds"] = round(
            seconds["slot_router_total_seconds"] - seconds["slot_router_aline_seconds"], 6)
        return result


def make_synthetic_source():
    from docx import Document
    buffer = BytesIO()
    document = Document()
    for text in ("知识精讲", "本节知识点：加法运算", "即时训练", "1．求 2+3 的值？", "【答案】5",
                 "2．求 3+4 的值？", "【答案】7", "六、巩固练习", "3．求 5+6 的值？", "【答案】11"):
        document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def synthetic_evidence_provider(source: bytes, review_id: str = "C3-R11-SYNTHETIC-WIRING-PROOF"):
    """Trusted-config provider for the synthetic wiring proof only."""
    from studentizer import TAG, element_sha256
    from studentizer_ranges import (PhysicalRangeSemantics, ReviewedAnswerRange,
                                    ReviewedPhysicalBody)
    with zipfile.ZipFile(BytesIO(source)) as package:
        root = etree.fromstring(package.read("word/document.xml"),
                                etree.XMLParser(resolve_entities=False, no_network=True))
    children = list(root.find(TAG("body")))
    answers = [index for index, node in enumerate(children)
               if "".join(node.itertext()).strip().startswith("【答案】")]
    if len(answers) != 3:
        raise RuntimeError("synthetic fixture must contain exactly three answers")
    ranges = []
    for number, answer in enumerate(answers, start=1):
        ranges.append(ReviewedAnswerRange("syn-q%d" % number, answer - 1, answer - 1, answer, answer,
                                          "synthetic wiring proof range", review_id))
    owners = {scope.owner_id: scope for scope in ranges}
    body = []
    for index, node in enumerate(children):
        owner = next((scope.owner_id for scope in ranges
                      if index in (scope.prompt_start, scope.answer_start)), None)
        body.append(ReviewedPhysicalBody(index, element_sha256(node),
                                        "REMOVE" if index in answers else "RETAIN",
                                        "synthetic wiring proof decision", review_id, owner))
    del owners
    expected_root = None
    with zipfile.ZipFile(BytesIO(source)) as package:
        expected_root = etree.fromstring(package.read("word/document.xml"),
                                        etree.XMLParser(resolve_entities=False, no_network=True))
    expected_children = list(expected_root.find(TAG("body")))
    for index in sorted(answers, reverse=True):
        expected_root.find(TAG("body")).remove(expected_children[index])
    semantics = PhysicalRangeSemantics(sha256(source).hexdigest(), review_id, tuple(body),
                                       tuple(ranges), element_sha256(expected_root))
    return lambda _snapshot, data: semantics if sha256(data).hexdigest() == semantics.source_sha256 else None


def corpus_files(sample_ids):
    baseline = json.loads((CORPUS / "baseline_inputs.json").read_text(encoding="utf-8"))
    index = {sample["sample_id"]: sample for sample in baseline["samples"]}
    files = []
    for sample_id in sample_ids:
        entry = index[sample_id]
        data = (CORPUS / entry["source_path"]).read_bytes()
        if sha256(data).hexdigest() != entry["source_sha256"]:
            raise SystemExit("corpus hash changed for " + sample_id)
        files.append((entry["name"], data))
    return files


def x008_files(count, prefix="专题"):
    data = (CORPUS / "sources/X008.docx").read_bytes()
    if sha256(data).hexdigest() != X008_APPROVED_SHA:
        raise SystemExit("approved X008 source digest changed")
    return [("%s%02d 教师版.docx" % (prefix, index + 1), data) for index in range(count)]


def run_case(case, files, template, out_root, provider=None, note=""):
    import app as shell
    from package_validator import validate_package

    # A fresh unique run directory per invocation: nothing is ever deleted, so a
    # bulk-delete guard can never interrupt a measurement halfway through.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    run_root = out_root / ("run-%s" % stamp)
    results_root = run_root / "results" / case
    runtime_root = run_root / "runtime" / case
    results_root.mkdir(parents=True)
    runtime_root.mkdir(parents=True)
    shell.app.config.update(TESTING=True, RESULT_ROOT=results_root, RUNTIME_ROOT=runtime_root,
                            C0_DISABLE_JOB_SUBMISSION=False, C0_RUN_JOBS_SYNCHRONOUSLY=True,
                            C0_FORCE_FALLBACK_REASON=None,
                            STUDENTIZER_EVIDENCE_PROVIDER=provider,
                            STUDENTIZER_REVIEWED_MANIFEST_DIR=None,
                            OPEN_FOLDER=lambda _path: None)
    client = shell.app.test_client()
    instrumentation = Instrumentation().install()
    monitor = ProcessMonitor().start()
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    try:
        with redirect_stdout(StringIO()):
            response = client.post("/api/jobs", data={
                "template_type": template, "split_mode": "smart", "docx_mode": "auto",
                "files": [(BytesIO(data), name) for name, data in files],
            }, content_type="multipart/form-data")
        elapsed = round(time.perf_counter() - started, 3)
        if response.status_code != 202:
            raise SystemExit("submission rejected: %s" % response.get_json())
        job_id = response.get_json()["job_id"]
        final = client.get("/api/jobs/" + job_id).get_json()
    finally:
        processes = monitor.stop()
        metrics = instrumentation.summary()
        instrumentation.uninstall()
    outputs = [{"path": path, "bytes": Path(path).stat().st_size,
                "validation": validate_package(path)} for path in final.get("output_paths", [])]
    if final.get("is_batch"):
        units = final.get("items", [])
    else:
        # A single submission keeps its renderer/preparation metadata on the job
        # record itself rather than on a per-item row.
        units = [{"renderer": final.get("renderer"),
                  "fallback_reason": final.get("fallback_reason"),
                  "fallback_detail": final.get("fallback_detail"),
                  "student_preparation": final.get("student_preparation") or {},
                  "elapsed_seconds": final.get("elapsed_seconds")}]
    preparations = [unit.get("student_preparation") or {} for unit in units]
    record = {
        "case": case, "note": note, "template": template,
        "is_batch": bool(final.get("is_batch")),
        "files": [name for name, _data in files],
        "distinct_source_sha256": sorted({sha256(data).hexdigest() for _name, data in files}),
        "items": final.get("total") if final.get("is_batch") else 1,
        "started_utc": started_utc,
        "ended_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed, "status": final.get("status"),
        "batch_outcome": final.get("batch_outcome"),
        "xml_items": sum(unit.get("renderer") == "XML" for unit in units),
        "fallback_items": sum(unit.get("renderer") == "V0.9" for unit in units),
        "fallback_reasons": sorted({unit.get("fallback_reason") for unit in units
                                    if unit.get("fallback_reason")}),
        "fallback_details": sorted({(unit.get("fallback_detail") or "")[:200] for unit in units
                                    if unit.get("fallback_detail")}),
        "studentizer_statuses": sorted({prep.get("status") for prep in preparations}),
        "student_preparation_modes": sorted({prep.get("student_preparation") for prep in preparations
                                               if prep.get("student_preparation")}),
        "renderer_routes": sorted({unit.get("renderer") for unit in units if unit.get("renderer")}),
        "studentizer_reason_codes": sorted({prep.get("reason_code") for prep in preparations
                                            if prep.get("reason_code")}),
        "studentizer_seconds": round(sum(prep.get("studentizer_elapsed_seconds") or 0
                                         for prep in preparations), 6),
        "reviewed_evidence": sorted({(prep.get("reviewed_evidence") or {}).get("sample_id")
                                     for prep in preparations if prep.get("reviewed_evidence")}),
        "make_student_called_items": sum(bool(prep.get("make_student_called")) for prep in preparations),
        "wps_com_started_items": sum(bool(prep.get("wps_com_started")) for prep in preparations),
        "outputs": len(outputs), "all_packages_valid": all(o["validation"].get("valid") for o in outputs),
        "item_seconds": [unit.get("elapsed_seconds") for unit in units],
        "instrumentation": metrics,
        "process_monitor": processes,
    }
    if record["items"]:
        record["seconds_per_item"] = round(elapsed / record["items"], 3)
    return record


def build_cases(suite):
    cases: dict[str, dict] = {}
    synthetic = make_synthetic_source()
    cases["synthetic-wiring-proof"] = {
        "files": [("合成专题 教师版.docx", synthetic)],
        "template": "1v1",
        "provider": synthetic_evidence_provider(synthetic),
        "note": ("SYNTHETIC reviewed source: proves the reviewed-supported teacher-only path "
                 "reaches XML with zero COM and zero fallback. Not a real-corpus measurement."),
    }
    for count in (1, 3, 5):
        cases["x008-teacher-only-%d" % count] = {
            "files": x008_files(count), "template": "1v1", "provider": None,
            "note": ("SAME-SOURCE performance workload: %d item(s) built from the single approved "
                     "X008 source under distinct names. Same-source timing does not represent "
                     "multi-sample coverage." % count),
        }
    cases["c2-case-a-teacher-only"] = {
        "files": corpus_files(C2_CASE_A_SOURCES), "template": "1v1", "provider": None,
        "note": ("Identical workload to C2 Case A (X001, X004, X006, X023, X025; 1v1) for a direct "
                 "comparison with the recorded 121.330 s."),
    }
    cases["c2-case-b-teacher-student"] = {
        "files": corpus_files(C2_CASE_B_SOURCES), "template": "class", "provider": None,
        "note": ("Identical workload to C2 Case B (X001, X002, X020, X019, X023, X021; class) for a "
                 "direct teacher+student XML batch regression check against the recorded 13.975 s."),
    }
    return {name: cases[name] for name in suite} if suite else cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--work", type=Path, default=Path(r"C:\xml-uat\c3-r11-performance"))
    args = parser.parse_args(argv)
    cases = build_cases(args.case)
    records = []
    for name, spec in cases.items():
        print("running", name, flush=True)
        records.append(run_case(name, spec["files"], spec["template"], args.work,
                                spec["provider"], spec["note"]))
        print("  ", json.dumps({key: records[-1][key] for key in
                                ("elapsed_seconds", "status", "xml_items", "fallback_items",
                                 "make_student_called_items", "wps_com_started_items")},
                               ensure_ascii=False), flush=True)
    payload = {"utc": datetime.now(timezone.utc).isoformat(),
               "c2_baselines": {"case_a_teacher_only_5": C2_CASE_A_SECONDS,
                                "case_b_teacher_student_3": C2_CASE_B_SECONDS},
               "python": sys.version.split()[0], "records": records}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.write_text(render_report(payload), encoding="utf-8")
    return 0


def render_report(payload):
    lines = ["# C3 R13 — layered fallback real performance", "",
             "All cases run the production HTTP path with the real A-Line, C1 Slot Router, B-Line",
             "renderer, templates and frozen V0.9 runtime. Only observation wrappers are installed.", ""]
    for record in payload["records"]:
        metrics = record["instrumentation"]
        seconds = metrics["seconds"]
        lines += ["## %s" % record["case"], "", record["note"], "",
                  "| Metric | Value |", "|---|---:|",
                  "| items | %s |" % record["items"],
                  "| total wall time | %s s |" % record["elapsed_seconds"],
                  "| per item | %s s |" % record.get("seconds_per_item", "-"),
                  "| XML items | %s |" % record["xml_items"],
                  "| fallback items | %s |" % record["fallback_items"],
                  "| renderer routes | %s |" % (", ".join(record.get("renderer_routes", [])) or "-"),
                  "| student preparation modes | %s |" % (", ".join(record.get("student_preparation_modes", [])) or "-"),
                  "| fallback reasons | %s |" % (", ".join(record["fallback_reasons"]) or "none"),
                  "| Studentizer time | %s s |" % record["studentizer_seconds"],
                  "| A-Line time | %s s |" % seconds.get("aline_seconds", 0.0),
                  "| Slot Router time | %s s |" % metrics.get("slot_router_seconds", 0.0),
                  "| XML Renderer time | %s s |" % seconds.get("xml_renderer_seconds", 0.0),
                  "| package validation time | %s s |" % seconds.get("package_validation_seconds", 0.0),
                  "| COM script invocations | %s |" % metrics.get("com_script_invocations", 0),
                  "| make_student calls | %s |" % metrics.get("make_student_calls", 0),
                  "| make_student time | %s s |" % seconds.get("make_student_seconds", 0.0),
                  "| COM script time | %s s |" % seconds.get("com_script_seconds", 0.0),
                  "| newly started office processes | %s |" % record["process_monitor"]["new_instances"],
                  "| items reporting make_student | %s |" % record["make_student_called_items"],
                  "| outputs | %s (all valid: %s) |" % (record["outputs"], record["all_packages_valid"]),
                  "| studentizer status | %s |" % (", ".join(record["studentizer_statuses"]) or "-"),
                  "| studentizer reason | %s |" % (", ".join(record["studentizer_reason_codes"]) or "-"),
                  "| reviewed evidence | %s |" % (", ".join(record["reviewed_evidence"]) or "-"),
                  ""]
    lines += ["## C2 comparison", "",
              "| Workload | C2 | C3 |", "|---|---:|---:|"]
    for record in payload["records"]:
        if record["case"] == "c2-case-a-teacher-only":
            lines.append("| 5 teacher-only items (identical sources, 1v1) | %s s | %s s |"
                         % (payload["c2_baselines"]["case_a_teacher_only_5"], record["elapsed_seconds"]))
        if record["case"] == "c2-case-b-teacher-student":
            lines.append("| 3 teacher+student XML items (identical sources, class) | %s s | %s s |"
                         % (payload["c2_baselines"]["case_b_teacher_student_3"], record["elapsed_seconds"]))
    lines += ["", "Same-source X008 timings are a workload measurement, not a coverage statement.",
              "Machine-readable detail: `fixtures/c3-r13-layered-performance.json`."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

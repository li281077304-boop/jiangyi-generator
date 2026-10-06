"""Synthetic coverage for the C3 performance harness.

Only the reviewed-supported synthetic wiring proof is executed here: it proves
the production route reaches XML with zero COM and zero fallback. Real
corpus/COM workloads are collected by the tool, not inside the unit suite.
"""
from hashlib import sha256
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
PERF = ROOT / "tools" / "c3_performance"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(PERF))

from run_c3_performance import (C2_CASE_A_SECONDS, C2_CASE_B_SECONDS,  # noqa: E402
                                X008_APPROVED_SHA, build_cases, render_report,
                                run_case, x008_files)


def test_x008_workload_uses_the_approved_source_bytes():
    files = x008_files(3)
    assert len(files) == 3
    assert len({name for name, _data in files}) == 3  # distinct topics, one source
    assert all(sha256(data).hexdigest() == X008_APPROVED_SHA for _name, data in files)


def test_synthetic_wiring_proof_reaches_xml_without_com(tmp_path):
    spec = build_cases(["synthetic-wiring-proof"])["synthetic-wiring-proof"]
    record = run_case("synthetic-wiring-proof", spec["files"], spec["template"],
                      tmp_path / "work", spec["provider"], spec["note"])
    assert record["status"] == "done", record.get("error") or record
    assert record["items"] == 1
    assert record["xml_items"] == 1 and record["fallback_items"] == 0
    assert record["fallback_reasons"] == []
    assert record["studentizer_statuses"] == ["XML_PREPARED"]
    assert record["student_preparation_modes"] == ["XML_STUDENTIZER"]
    assert record["renderer_routes"] == ["XML"]
    assert record["studentizer_reason_codes"] == []
    assert record["make_student_called_items"] == 0
    assert record["wps_com_started_items"] == 0
    assert record["instrumentation"]["com_script_invocations"] == 0
    assert record["instrumentation"]["make_student_calls"] == 0
    assert record["instrumentation"]["xml_renderer_calls"] == 2
    assert record["instrumentation"]["slot_router_seconds"] >= 0
    assert record["process_monitor"]["new_instances"] == 0
    assert record["outputs"] == 2 and record["all_packages_valid"]


def test_harness_restores_every_wrapped_callable(tmp_path):
    import package_validator
    import slot_router
    import studentizer_planner
    import subprocess
    import template_slot_composer
    import renderer_orchestrator

    before = (subprocess.run, slot_router.analyze_source, slot_router.build_slot_routing_plan,
              studentizer_planner.analyze_source, template_slot_composer.render_slots,
              package_validator.validate_package,
              renderer_orchestrator._load_v09_engine().make_student)
    spec = build_cases(["synthetic-wiring-proof"])["synthetic-wiring-proof"]
    run_case("synthetic-wiring-proof", spec["files"], spec["template"], tmp_path / "work",
             spec["provider"], spec["note"])
    after = (subprocess.run, slot_router.analyze_source, slot_router.build_slot_routing_plan,
             studentizer_planner.analyze_source, template_slot_composer.render_slots,
             package_validator.validate_package,
             renderer_orchestrator._load_v09_engine().make_student)
    assert before == after


def test_report_carries_baselines_and_per_case_metrics(tmp_path):
    spec = build_cases(["synthetic-wiring-proof"])["synthetic-wiring-proof"]
    record = run_case("synthetic-wiring-proof", spec["files"], spec["template"],
                      tmp_path / "work", spec["provider"], spec["note"])
    payload = {"records": [record], "python": "3.12",
               "c2_baselines": {"case_a_teacher_only_5": C2_CASE_A_SECONDS,
                                "case_b_teacher_student_3": C2_CASE_B_SECONDS}}
    report = render_report(payload)
    for required in ("## synthetic-wiring-proof", "| A-Line time |", "| Slot Router time |",
                     "| XML Renderer time |", "| package validation time |",
                     "| COM script invocations | 0 |", "| newly started office processes | 0 |",
                     "| studentizer status | XML_PREPARED |"):
        assert required in report
    assert report.count("# C3 R13") == 1

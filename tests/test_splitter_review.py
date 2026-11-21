"""Exercise the public CLI with fictional evaluator outputs only."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/splitter_review.py"
sys.path.insert(0, str(ROOT / "examples/splitter_review"))
from make_example import make_example, save


@pytest.fixture
def run_dir(tmp_path):
    folder = tmp_path / "input"
    make_example(folder)
    return folder


def run(folder, output=None, code=0):
    output = output or folder.parent / "review"
    proc = subprocess.run([sys.executable, str(CLI), str(folder), str(output)],
                          text=True, capture_output=True)
    assert proc.returncode == code, (proc.stderr, output)
    if code != 2:
        return json.loads((output / "review_summary.json").read_text())


def get(path):
    return json.loads(path.read_text())


def change(folder, *, plan=None, source=None):
    # Keep the evaluator's three copies in agreement unless testing stale evidence.
    entry = get(folder / "S01/assessment.json")
    if source:
        source(entry)
    if plan:
        item = entry["templates"]["1v1"]
        plan(item)
        save(folder / "S01/1v1.json", item)
    save(folder / "S01/assessment.json", entry)
    save(folder / "report.json", {"sources": [entry]})


def test_review_counts_and_checklist(run_dir):
    report = run(run_dir)
    semantic, preserved = report["rows"]
    assert [semantic["template"], preserved["template"]] == ["1v1", "class"]
    assert all(r["physical_status"] == r["hash_status"] == "verified" for r in report["rows"])
    assert "PRESERVATION" in preserved["risks"]
    assert all("TEACHER_STUDENT_ALIGNMENT_UNVERIFIED" in r["risks"] for r in report["rows"])
    assert report["counts"] == dict(samples=1, template_reviews=2, plans_created=2,
                                    rule_paths=1, partition=0, preserved=1,
                                    pending_review=2, rows_with_findings=0)
    assert report["teaching_gold"] == "unavailable"
    assert "accuracy" not in json.dumps(report).lower()
    rows = list(csv.DictReader((run_dir.parent / "review/review_checklist.csv").open(encoding="utf-8-sig")))
    assert [(r["template"], r["block_id"]) for r in rows] == [
        (template, f"b{i}") for template in ("1v1", "class") for i in range(4)]
    assert all(not r["human_decision"] and not r["notes"] for r in rows)
    for i, token in enumerate(("COVER", "MATH", "IMAGE", "OLE")):
        assert token in rows[i]["review_flags"].upper()


def test_partition_and_fallback_are_review_risks(run_dir):
    change(run_dir, plan=lambda p: p["evidence"].update(selected_tier="PARTITION"),
           source=lambda s: s.update(analysis_mode="STRUCTURAL_FALLBACK",
                                     semantic_exception=dict(message="fictional parse anomaly")))
    report = run(run_dir)
    assert report["counts"]["partition"] == 1
    assert "PARTITION" in report["rows"][0]["risks"]
    assert "fictional parse anomaly" in str(report["rows"][0]["risks"])


def test_duplicate_and_missing_records(run_dir):
    def damage(plan):
        plan["block_records"][2] = plan["block_records"][1]
    change(run_dir, plan=damage)
    row = run(run_dir, code=1)["rows"][0]
    assert row["physical_status"] == "failed"
    assert row["duplicate"] == ["b1"]
    assert "b2" in row["missing"]


def test_wrong_hash_is_separate_from_physical_coverage(run_dir):
    change(run_dir, source=lambda s: s.update(expected_sha256="f" * 64))
    row = run(run_dir, code=1)["rows"][0]
    assert (row["hash_status"], row["physical_status"]) == ("failed", "verified")


def test_plan_error_keeps_blocks_for_human_review(run_dir):
    def failed(p):
        p.clear()
        p.update(status="ERROR", exception={"reason_code": "FICTIONAL_ERROR"})
    change(run_dir, plan=failed, source=lambda s: s.update(status="PARTIAL_OR_FAILED"))
    report = run(run_dir, code=1)
    row = report["rows"][0]
    assert row["physical_status"] == "unknown" and len(row["blocks"]) == 4
    assert "FICTIONAL_ERROR" in str(row["errors"])
    assert report["rows"][1]["physical_status"] == "verified"


@pytest.mark.parametrize("damage", ["missing", "malformed", "missing_field", "stale_copy"])
def test_bad_evidence_is_localized(run_dir, damage):
    target = run_dir / "S01/1v1.json"
    if damage == "missing":
        target.unlink()
    elif damage == "malformed":
        target.write_text("{broken")
    elif damage == "missing_field":
        change(run_dir, plan=lambda p: p.pop("block_records"))
    else:
        plan = get(target)
        plan["evidence"]["selected_tier"] = "NAVIGATION"
        save(target, plan)
    bad, good = run(run_dir, code=1)["rows"]
    assert bad["errors"] and not good["errors"]


def test_parse_failure_without_dump(run_dir):
    change(run_dir, source=lambda s: s.update(status="ERROR", exception={"type": "SyntheticParseError"},
                                              templates={}))
    for name in ("source_dump.json", "1v1.json", "class.json"):
        (run_dir / "S01" / name).unlink()
    report = run(run_dir, code=1)
    assert report["counts"]["plans_created"] == 0
    assert all("SyntheticParseError" in str(r["errors"]) and not r["blocks"] for r in report["rows"])


def test_reproducibility_and_read_only(run_dir):
    def snapshot(folder):
        return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    before = snapshot(run_dir)
    first, second = (run_dir.parent / name for name in ("first", "second"))
    run(run_dir, first)
    run(run_dir, second)
    assert snapshot(first) == snapshot(second)
    run(run_dir, first, code=2)
    run(run_dir, run_dir / "nested", code=2)
    assert before == snapshot(run_dir) and not (run_dir / "nested").exists()


@pytest.mark.parametrize("sources", [[], [{"id": "../outside"}], [{"id": "S01"}, {"id": "S01"}]])
def test_unusable_index_creates_no_package(run_dir, sources):
    save(run_dir / "report.json", {"sources": sources})
    run(run_dir, code=2)
    assert not (run_dir.parent / "review").exists()


@pytest.mark.parametrize("case", ["same_slot_twice", "wrong_slot", "extra_index", "fake_cover"])
def test_inconsistent_slot_ownership(run_dir, case):
    def mutate(plan):
        if case == "same_slot_twice":
            plan["slots"]["knowledge"]["spans"].append({"start": "b1", "end": "b1"})
        elif case == "wrong_slot":
            plan["block_records"][1]["destination_slot"] = "final"
        elif case == "extra_index":
            plan["block_records"].append({"block_id": "b999", "source_index": 999})
        else:
            plan["block_records"][0]["exclusion_reason"] = None
    change(run_dir, plan=mutate)
    bad, good = run(run_dir, code=1)["rows"]
    assert bad["physical_status"] == "failed"
    assert good["physical_status"] == "verified"
    if case == "same_slot_twice":
        assert bad["duplicate"] == ["b1"]
    if case == "fake_cover":
        assert "b0" in bad["unclassified"]


def test_hash_evidence_is_partial_when_a_digest_is_missing(run_dir):
    change(run_dir, source=lambda s: s.pop("sha256_after"))
    assert run(run_dir, code=1)["rows"][0]["hash_status"] == "unknown"


def test_missing_source_id_on_every_block(run_dir):
    path = run_dir / "S01/source_dump.json"
    dump = get(path)
    for block in dump["blocks"]:
        del block["id"]
    save(path, dump)
    assert run(run_dir, code=1)["rows"][0]["physical_status"] != "verified"


def test_symlinked_artifact_outside_run_is_rejected(run_dir):
    path = run_dir / "S01/1v1.json"
    outside = run_dir.parent / "other-plan.json"
    path.rename(outside)
    path.symlink_to(outside)
    bad, good = run(run_dir, code=1)["rows"]
    assert any("outside input" in e for e in bad["errors"])
    assert good["physical_status"] == "verified"

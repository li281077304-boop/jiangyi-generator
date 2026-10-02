"""Drive the real V1.2 product pipeline from source (no EXE) over real corpus files.

The Flask job API is the same code path the packaged EXE uses, so results here
are the product's own behaviour, not a unit-test approximation.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\Administrator\Desktop\工作\jiangyi-generator-splitter-audit")
APP = REPO / "v1.2-xml-experiment" / "res" / "app"
WEBAPP = APP / "webapp"
sys.path.insert(0, str(WEBAPP))
sys.path.insert(0, str(APP))

RUN_ROOT = Path(r"C:\xml-uat\c4-product-recovery\run-source-%s" % time.strftime("%Y%m%dT%H%M%S"))
RESULT_ROOT = RUN_ROOT / "results"
RUNTIME_ROOT = RUN_ROOT / "runtime"
RESULT_ROOT.mkdir(parents=True, exist_ok=True)
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["JIANGYI_RESULT_ROOT"] = str(RESULT_ROOT)
os.environ["JIANGYI_RUNTIME_ROOT"] = str(RUNTIME_ROOT)

from app import app  # noqa: E402

CORPUS = Path(r"C:\xml-uat\c4-product-recovery\corpus")
MANIFEST = json.loads(Path(r"C:\xml-uat\c4-product-recovery\PRODUCT_SOURCE_CORPUS.json")
                      .read_text(encoding="utf-8"))
BY_ID = {s["sample_id"]: s for s in MANIFEST["samples"]}

SCENARIOS = [
    {"id": "U01", "label": "X012 数学 1v1 teacher-only", "files": ["S01"],
     "form": {"template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
              "subject": "数学", "grade": "七年级", "handout_type": "复习讲义",
              "academic_year": "2026-2027"}},
    {"id": "U02", "label": "数学小升初 1v1 teacher+student", "files": ["S02T", "S02S"],
     "form": {"template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
              "subject": "数学", "grade": "六年级", "handout_type": "真题汇编",
              "academic_year": "2026"}},
    {"id": "U03", "label": "数学高中班课 class teacher-only", "files": ["S03"],
     "form": {"template_type": "class", "split_mode": "smart", "docx_mode": "auto",
              "subject": "数学", "grade": "高二", "handout_type": "题型清单",
              "academic_year": "2026-2027"}},
    {"id": "U04", "label": "物理九年级 1v1 teacher+student", "files": ["S04T", "S04S"],
     "form": {"template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
              "subject": "物理", "grade": "九年级", "handout_type": "同步讲义",
              "academic_year": "2026-2027"}},
    {"id": "U05", "label": "化学高一 class teacher+student", "files": ["S05S", "S05T"],
     "form": {"template_type": "class", "split_mode": "smart", "docx_mode": "auto",
              "subject": "化学", "grade": "高一", "handout_type": "题型专练",
              "academic_year": "2026-2027"}},
    {"id": "U01F", "label": "X012 1v1 split_mode=full", "files": ["S01"],
     "form": {"template_type": "1v1", "split_mode": "full", "docx_mode": "auto",
              "subject": "数学", "grade": "七年级", "handout_type": "复习讲义",
              "academic_year": "2026-2027"}},
    {"id": "U01C", "label": "X012 class template", "files": ["S01"],
     "form": {"template_type": "class", "split_mode": "smart", "docx_mode": "auto",
              "subject": "数学", "grade": "七年级", "handout_type": "复习讲义",
              "academic_year": "2026-2027"}},
    {"id": "U02F", "label": "数学小升初 pair split_mode=full", "files": ["S02T", "S02S"],
     "form": {"template_type": "1v1", "split_mode": "full", "docx_mode": "auto",
              "subject": "数学", "grade": "六年级", "handout_type": "真题汇编",
              "academic_year": "2026"}},
    {"id": "U04S", "label": "物理解析版 single teacher-only", "files": ["S04T"],
     "form": {"template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
              "subject": "物理", "grade": "九年级", "handout_type": "同步讲义",
              "academic_year": "2026-2027"}},
    {"id": "U06", "label": "英语四年级 1v1 teacher-only", "files": ["S06"],
     "form": {"template_type": "1v1", "split_mode": "smart", "docx_mode": "auto",
              "subject": "英语", "grade": "四年级", "handout_type": "期末复习讲义",
              "academic_year": "2025-2026"}},
]


def submit(client, scenario: dict) -> dict:
    payload = {}
    data = {}
    uploads = []
    for index, sample_id in enumerate(scenario["files"]):
        record = BY_ID[sample_id]
        path = Path(record["corpus_path"])
        uploads.append((path.open("rb"), path.name))
    data["files"] = uploads
    for key, value in scenario["form"].items():
        data[key] = value
    response = client.post("/api/jobs", data=data, content_type="multipart/form-data")
    body = response.get_json()
    if response.status_code >= 400:
        return {"scenario": scenario["id"], "http_error": response.status_code, "body": body}
    return {"scenario": scenario["id"], "job_id": body.get("job_id"), "created": body}


def wait(client, job_id: str, timeout: float = 900.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get("/api/jobs/%s" % job_id)
        record = response.get_json()
        status = (record or {}).get("status")
        if status in ("done", "error", "partial", "failed"):
            return record
        time.sleep(1.0)
    return {"status": "timeout"}


def main() -> int:
    client = app.test_client()
    wanted = set(sys.argv[1:])
    report = {"run_root": str(RUN_ROOT), "scenarios": []}
    for scenario in SCENARIOS:
        if wanted and scenario["id"] not in wanted:
            continue
        entry = {"id": scenario["id"], "label": scenario["label"],
                 "inputs": [{"sample_id": sid, "sha256": BY_ID[sid]["sha256"],
                             "corpus_path": BY_ID[sid]["corpus_path"]}
                            for sid in scenario["files"]],
                 "form": scenario["form"]}
        created = submit(client, scenario)
        entry["submission"] = created
        if created.get("job_id"):
            entry["job"] = wait(client, created["job_id"])
        report["scenarios"].append(entry)
        status = entry.get("job", {}).get("status", created.get("http_error"))
        renderer = entry.get("job", {}).get("renderer")
        fallback = entry.get("job", {}).get("fallback_reason")
        print("%s  status=%s  renderer=%s  fallback=%s" % (
            scenario["id"], status, renderer, fallback))
    out = RUN_ROOT / "source_product_uat.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("report ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

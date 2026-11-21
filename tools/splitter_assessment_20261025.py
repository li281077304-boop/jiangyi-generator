#!/usr/bin/env python3
"""Local, read-only source assessment; not an end-to-end or semantic-gold test.

Usage: python tools/splitter_assessment_20261025.py manifest.json output_directory
Manifest: {"sources": [{"id": "S01", "path": "/path/source.docx", "sha256": "..."}]}
Relative source paths resolve against the manifest directory. No API calls,
source copies, document rendering, package installation or product changes.
The default auto routing sequence is inspected on original source snapshots;
production textbox projection, student preparation and image-role evidence are
not reproduced. Thus routing results are diagnostics, not product acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "v1.2-xml-experiment/res/app"))

LIMITATIONS = [
    "SOURCE_ROUTING_DIAGNOSTIC_NOT_END_TO_END",
    "NO_INDEPENDENT_SEMANTIC_GOLD_NO_ACCURACY_CLAIM",
    "NO_RENDERING_OR_VISUAL_ACCEPTANCE",
    "NO_PRODUCTION_TEXTBOX_PROJECTION_STUDENT_PREPARATION_OR_IMAGE_ROLE_EVIDENCE",
    "TEACHER_STUDENT_SOURCES_ASSESSED_INDEPENDENTLY_NO_PAIR_ALIGNMENT",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def error_record(exc):
    return {"type": type(exc).__name__, "message": str(exc),
            "reason_code": getattr(exc, "reason_code", None), "traceback": traceback.format_exc()}


def assess(entry, manifest_dir, folder):
    from semantic_facade import analyze_source
    from xml_degradation import build_degraded_plan, structural_snapshot
    from slot_router import SlotRoutingError

    started = time.perf_counter()
    source = Path(entry["path"]).expanduser()
    if not source.is_absolute():
        source = manifest_dir / source
    source = source.resolve()
    result = {"id": entry["id"], "source_path": str(source),
              "expected_sha256": entry["sha256"], "limitations": LIMITATIONS, "templates": {}}
    try:
        result["sha256_before"] = digest(source)
        if result["sha256_before"].lower() != str(entry["sha256"]).lower():
            raise ValueError("SOURCE_HASH_MISMATCH: refusing to assess a different source")
        analysis_start = time.perf_counter()
        try:
            snapshot = analyze_source(source)
            result["analysis_mode"] = "SEMANTIC"
        except Exception as exc:
            result["semantic_exception"] = error_record(exc)
            snapshot = structural_snapshot(source)
            result["analysis_mode"] = "STRUCTURAL_FALLBACK"
        result["analysis_seconds"] = time.perf_counter() - analysis_start
        result["snapshot_sha256"] = snapshot.source_sha256
        if snapshot.source_sha256 != result["sha256_before"]:
            raise ValueError("SOURCE_CHANGED_DURING_ANALYSIS")
        result["unit_role_counts"] = dict(Counter(u.get("role", "unknown") for u in snapshot.units))
        result["block_count"] = len(snapshot.document.blocks)
        blocks = [{"id": "b%d" % i, "kind": b.kind, "text": b.text,
                   "textbox_texts": b.textbox_texts, "images_count": len(b.images),
                   "oles_count": len(b.oles), "math_count": b.math_count}
                  for i, b in enumerate(snapshot.document.blocks)]
        write_json(folder / "source_dump.json", {"sha256": snapshot.source_sha256,
                   "blocks": blocks, "units": snapshot.units,
                   "nodes": [{"id": n.id, "text": n.text} for n in snapshot.node_index.nodes]})
        for template in ("1v1", "class"):
            timer = time.perf_counter()
            item = {}
            try:
                try:
                    plan, evidence = build_degraded_plan(source, template, snapshot=snapshot, navigation_only=True)
                    item["navigation_first"] = "SELECTED"
                except SlotRoutingError as exc:
                    item["navigation_first"] = {"status": "DEGRADED", "exception": error_record(exc)}
                    plan, evidence = build_degraded_plan(source, template, snapshot=snapshot)
                item.update({"status": "PLAN_CREATED_NOT_SEMANTICALLY_VERIFIED", "evidence": evidence,
                             "training_split_strategy": plan.training_split_strategy,
                             "knowledge_point_status": plan.knowledge_point_status,
                             "template_sha256": plan.template_sha256,
                             "slots": {}, "block_records": plan.block_records})
                for slot, spans in plan.slots.items():
                    records = [r for r in plan.block_records if r.get("destination_slot") == slot]
                    snippets = [{"block_id": r["block_id"],
                                 "text": snapshot.document.blocks[r["source_index"]].text[:320]}
                                for r in records]
                    item["slots"][slot] = {"spans": [asdict(s) for s in spans],
                                           "block_count": len(records), "text_summaries": snippets}
            except Exception as exc:
                item.update({"status": "ERROR", "exception": error_record(exc)})
            item["seconds"] = time.perf_counter() - timer
            result["templates"][template] = item
            write_json(folder / (template + ".json"), item)
        result["status"] = "ASSESSED" if all(v["status"] != "ERROR" for v in result["templates"].values()) else "PARTIAL_OR_FAILED"
    except Exception as exc:
        result.update({"status": "ERROR", "exception": error_record(exc)})
    finally:
        try:
            result["sha256_after"] = digest(source)
            result["source_unchanged"] = result["sha256_after"] == result.get("sha256_before")
            if not result["source_unchanged"]:
                result["status"] = "SOURCE_CHANGED"
        except Exception as exc:
            result["source_unchanged"] = None
            result["hash_after_exception"] = str(exc)
        result["total_seconds"] = time.perf_counter() - started
        write_json(folder / "assessment.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    entries = data["sources"]
    if not isinstance(entries, list) or not entries:
        parser.error("manifest sources must be a non-empty list")
    seen = set()
    for entry in entries:
        if not all(k in entry for k in ("id", "path", "sha256")):
            parser.error("each source requires id, path and sha256")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", str(entry["id"])) or entry["id"] in seen:
            parser.error("source ids must be unique and contain only letters, digits, _ or -")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(entry["sha256"])):
            parser.error("sha256 must be 64 hex characters")
        seen.add(entry["id"])
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output directory must be absent or empty; existing evidence is not overwritten")
    output.mkdir(parents=True, exist_ok=True)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "repository_head": revision.stdout.strip(),
              "manifest": str(manifest), "manifest_sha256": digest(manifest),
              "runner_sha256": digest(Path(__file__)), "limitations": LIMITATIONS, "sources": []}
    for entry in entries:
        folder = output / str(entry["id"])
        folder.mkdir()
        result = assess(entry, manifest.parent, folder)
        report["sources"].append(result)
        write_json(output / "report.json", report)
        print(json.dumps({"id": entry["id"], "status": result["status"],
                          "source_unchanged": result["source_unchanged"],
                          "tiers": {k: v.get("evidence", {}).get("selected_tier") for k, v in result["templates"].items()}}, ensure_ascii=False), flush=True)
    (output / "README.md").write_text("# Splitter 本地诊断\n\n本报告不是端到端测试或语义金标评测；PLAN_CREATED 不代表分区正确。\n"
        "未渲染成品、未验证教师学生对应、未调用 API。未执行生产预处理（文本框投影、学生加工、图片角色证据）。\n"
        "查看 report.json 汇总；每个样本的 source_dump.json 为本地文本/节点转储，1v1.json、class.json 为分槽证据。\n", encoding="utf-8")
    return 0 if all(r["status"] == "ASSESSED" and r["source_unchanged"] for r in report["sources"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Isolated static prototype for five-topic teaching-module synchronization.

This is an experiment only. It reads each immutable DOCX once through the
checked-in semantic snapshot API, inventories top-level physical blocks, and
emits conservative role-owned maps. It intentionally does not invoke the
production paired aligner or renderer: question-envelope proof and safe
role-specific rendering remain explicit gates in the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from semantic_facade import analyze_source  # noqa: E402

REPO = APP.parents[2]
MANIFEST = REPO / "docs/v2/integration/fixtures/v12-finalization-evaluation/teaching_module_sync_experiment_manifest.json"
OUT = REPO / "docs/v2/integration/fixtures/teaching-module-sync-20261008"
HEADING = re.compile(r"^(?:第[一二三四五六七八九十\d]+(?:章|节|讲|单元)|[一二三四五六七八九十]+[、.．])\s*\S|^(?:专题|题型|知识点|考点|知识精讲|例题|典例|即时训练|巩固练习|课后练习|参考答案|答案解析|答案与解析)")
QUESTION = re.compile(r"^\s*\d{1,3}\s*[.．、)）]\s*\S")
ANSWER = re.compile(r"(?:参考答案|答案解析|答案与解析|答案及解析|试题解析)")
KNOWLEDGE = re.compile(r"(?:知识点|考点梳理|知识精讲|知识讲解|概念|定义|方法指导)")
EXAMPLE = re.compile(r"(?:例题|典例|例\s*\d+)")
PRACTICE = re.compile(r"(?:训练|练习|测试|检测|习题)")


def classify(text: str, kind: str) -> str:
    if kind == "table":
        return "atomic_table_unclassified"
    if ANSWER.search(text):
        return "teacher_answer_or_analysis_candidate"
    if KNOWLEDGE.search(text):
        return "knowledge_candidate"
    if EXAMPLE.search(text):
        return "example_candidate"
    if QUESTION.match(text):
        return "question_start_candidate"
    if PRACTICE.search(text):
        return "practice_heading_candidate"
    return "continuation_or_unclassified"


def load_snapshot(path: Path, expected_hash: str, role: str) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_hash:
        raise ValueError(f"SOURCE_HASH_MISMATCH:{role}:{path.name}:{digest}")
    snap = analyze_source(data)
    blocks = snap.document.blocks
    rows = []
    for b in blocks:
        text = re.sub(r"\s+", " ", b.text or "").strip()
        resources = [{"kind": "image", "target": x.target, "rid": x.rId} for x in b.images]
        resources += [{"kind": "ole", "target": x.target, "rid": x.rId} for x in b.oles]
        identity = f"b{b.seq}"
        rows.append({
            "source_id": identity, "seq": b.seq, "body_idx": b.body_idx,
            "kind": b.kind, "pno": b.pno, "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "classification": classify(text, b.kind), "outline_lvl": b.outline_lvl,
            "resource_owner": identity if resources else None, "resources": resources,
            "table_atomic": b.kind == "table",
        })
    if [r["seq"] for r in rows] != list(range(len(rows))):
        raise ValueError("PHYSICAL_SEQUENCE_NOT_DENSE")
    heading_idxs = [r["seq"] for r in rows if r["kind"] == "paragraph" and
                    (r["outline_lvl"] is not None or HEADING.search(r["text"]))]
    # Maps are diagnostic candidates. Every source block receives exactly one
    # nearest preceding heading owner (or document-frontmatter packet).
    starts = [0] + [i for i in heading_idxs if i > 0]
    starts = sorted(set(starts))
    modules = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(rows)
        title = rows[start]["text"][:180] if rows else ""
        mids = f"{role}-m{n + 1:02d}"
        modules.append({"module_id": mids, "start_seq": start,
                        "end_seq_exclusive": end, "anchor_text": title,
                        "anchor_sha256": hashlib.sha256(title.encode("utf-8")).hexdigest(),
                        "anchor_confidence": "candidate_only",
                        "mapping_evidence": ["student-boundary-model" if role == "student" else "teacher-local-heading-candidate"]})
    module_intervals = sorted((m["start_seq"], m["end_seq_exclusive"]) for m in modules)
    cursor = 0
    exactly_once = True
    for start, end in module_intervals:
        if start != cursor or end <= start:
            exactly_once = False
            break
        cursor = end
    exactly_once = exactly_once and cursor == len(rows)

    packets = []
    for module in modules:
        start_seq = module["start_seq"]
        end_seq = module["end_seq_exclusive"]
        current_start = start_seq
        current_label = rows[start_seq]["classification"] if start_seq < end_seq else None
        for seq in range(start_seq + 1, end_seq):
            label = rows[seq]["classification"]
            if label != current_label:
                packets.append({"packet_id": f"{module['module_id']}-p{len(packets) + 1:03d}",
                                "module_id": module["module_id"],
                                "classification": current_label,
                                "start_seq": current_start,
                                "end_seq_exclusive": seq,
                                "block_count": seq - current_start})
                current_start, current_label = seq, label
        if current_label is not None:
            packets.append({"packet_id": f"{module['module_id']}-p{len(packets) + 1:03d}",
                            "module_id": module["module_id"],
                            "classification": current_label,
                            "start_seq": current_start,
                            "end_seq_exclusive": end_seq,
                            "block_count": end_seq - current_start})
    packet_intervals = sorted((p["start_seq"], p["end_seq_exclusive"]) for p in packets)
    cursor = 0
    packet_exactly_once = True
    for start, end in packet_intervals:
        if start != cursor or end <= start:
            packet_exactly_once = False
            break
        cursor = end
    packet_exactly_once = packet_exactly_once and cursor == len(rows)
    resource_rows = [(r["source_id"], x["kind"], x["rid"], x["target"])
                     for r in rows for x in r["resources"]]
    resource_owner_ok = all(owner in {r["source_id"] for r in rows}
                            for owner, _kind, _rid, _target in resource_rows)
    return {"role": role, "path": str(path), "sha256": digest,
            "snapshot_sha256": snap.source_sha256,
            "inventory_counts": dict(Counter(r["kind"] for r in rows)),
            "physical_block_count": len(rows), "resource_count": sum(len(r["resources"]) for r in rows),
            "blocks": rows, "modules": modules, "ownership_exactly_once": exactly_once,
            "ownership_count": len(rows) if exactly_once else sum(end - start for start, end in module_intervals),
            "packets": packets,
            "packet_ownership_exactly_once": packet_exactly_once,
            "resource_reference_count": len(resource_rows),
            "resource_owner_conservation": resource_owner_ok}


def run() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = []
    for case in manifest["topics"]:
        roles = {}
        for inp in case["inputs"]:
            role = "student" if inp["role"] == "student_or_original_paper" else "teacher"
            p = Path(inp["path"])
            roles[role] = load_snapshot(p, inp["sha256"], role)
        reasons = []
        if any(not v["ownership_exactly_once"] for v in roles.values()):
            reasons.append("PHYSICAL_SOURCE_OWNERSHIP_NOT_EXACTLY_ONCE")
        if any(not v["packet_ownership_exactly_once"] for v in roles.values()):
            reasons.append("PACKET_SOURCE_OWNERSHIP_NOT_EXACTLY_ONCE")
        if any(not v["resource_owner_conservation"] for v in roles.values()):
            reasons.append("RESOURCE_OWNER_CONSERVATION_FAILED")
        if any(any(b["kind"] == "unknown" for b in v["blocks"]) for v in roles.values()):
            reasons.append("UNKNOWN_PHYSICAL_BLOCK_PRESENT")
        # Heading text and local contexts are emitted for review, but cannot
        # establish full module identity or question-envelope consistency.
        s_mods, t_mods = roles["student"]["modules"], roles["teacher"]["modules"]
        normalized = lambda x: re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", x.lower())
        t_by_anchor = {}
        for m in t_mods:
            t_by_anchor.setdefault(normalized(m["anchor_text"]), []).append(m)
        maps = []
        for sm in s_mods:
            key = normalized(sm["anchor_text"])
            matches = t_by_anchor.get(key, [])
            maps.append({"student_module": sm["module_id"],
                         "teacher_candidates": [m["module_id"] for m in matches],
                         "status": "UNIQUE_TEXT_CANDIDATE" if len(matches) == 1 else "UNRESOLVED",
                         "confidence": "candidate_only",
                         "evidence": ["normalized-heading-text"],
                         "reason": None if len(matches) == 1 else "ANCHOR_NOT_UNIQUE_OR_ABSENT"})
            if len(matches) != 1:
                reasons.append("MODULE_ANCHOR_NOT_UNIQUELY_PROVEN")
        reasons += ["QUESTION_GROUP_ENVELOPE_GATE_NOT_IMPLEMENTED_IN_PROTOTYPE",
                    "ATOMIC_TABLE_AND_SHARED_RESOURCE_DEPENDENCIES_NOT_VALIDATED",
                    "ROLE_SPECIFIC_RENDER_AND_PRODUCT_INTEGRITY_GATES_NOT_RUN"]
        cases.append({"case_id": case["case_id"], "topic_identity": case["topic_identity"],
                      "evidence_note": case["evidence_note"], "roles": roles,
                      "module_maps": maps, "packet_classification_counts": {
                          role: dict(Counter(b["classification"] for b in data["blocks"]))
                          for role, data in roles.items()},
                      "cross_role_question_group_identity": "NOT_VALIDATED",
                      "status": "PLAN_ONLY_FAIL_CLOSED", "fail_closed_reasons": sorted(set(reasons))})
    return {"schema_version": 1, "status": "FIVE_TOPIC_PLAN_ONLY_BLOCKED",
            "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "production_gates_called": [], "protected_production_files_modified": False,
            "downstream_interface_assessment": {
                "router": "build_slot_routing_plan accepts a complete seq-to-slot map whose destinations are only knowledge/immediate/final; it does not accept module IDs or unresolved ownership.",
                "composer": "render_slots consumes that plan and applies existing display renumbering before output inspection.",
                "stop_reason": "No proof-backed complete block-to-slot routes exist: heading/module matches and packet labels are candidates, and complete question/answer envelopes have not been validated. Passing candidate routes would violate fail-closed policy; no synthetic routes were supplied.",
                "package_validator_and_product_integrity": "Not called because no output was generated."
            },
            "cases": cases,
            "summary": {"topics": len(cases), "rendered_outputs": 0,
                        "new_full_topic_successes": 0,
                        "baseline10_preserved": "NOT_EVALUATED",
                        "baseline11_preserved": "NOT_EVALUATED",
                        "next_gate": "Implement bounded question-envelope verification and establish safe role-specific renderer support before any DOCX generation."}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT / "module_sync_experiment.json")
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))

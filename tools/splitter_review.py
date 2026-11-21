#!/usr/bin/env python3
"""从已有评估输出生成仅供本机核对的 Splitter 复核包。"""
import argparse
import csv
import html
import json
from pathlib import Path
import re
import sys

from splitter_review_blocks import audit_blocks

TEMPLATES = ("1v1", "class")
RULE_TIERS = ("NAVIGATION", "SEMANTIC", "RULES")
PLAN_CREATED = "PLAN_CREATED_NOT_SEMANTICALLY_VERIFIED"


def read_object(path, root):
    """Never follow an evaluator artifact outside its run directory."""
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"{path.name}: path outside input")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{path.name}: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected JSON object")
    return value


def artifact(folder, name, root, errors):
    try:
        return read_object(folder / name, root)
    except (ValueError, RuntimeError, OSError) as exc:
        errors.append(str(exc))
        return {}


def exception_text(record):
    if isinstance(record, dict):
        return " ".join(str(record[k]) for k in ("type", "reason_code", "message")
                        if record.get(k)) or "未记录异常原因"
    return str(record or "未记录异常原因")


def check_hashes(assessment, dump, evidence):
    hashes = {k: assessment.get(k) for k in
              ("expected_sha256", "sha256_before", "snapshot_sha256", "sha256_after")}
    hashes.update(dump_sha256=dump.get("sha256"), plan_sha256=evidence.get("source_sha256"))
    valid = [v.lower() for v in hashes.values()
             if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v)]
    unchanged = assessment.get("source_unchanged")
    if len(set(valid)) > 1 or unchanged is False:
        return "failed", hashes
    if len(valid) != len(hashes) or unchanged is not True:
        return "unknown", hashes
    return "verified", hashes


def review_sample(root, entry):
    sample = entry["id"]
    folder = root / sample
    common = []
    assessment = artifact(folder, "assessment.json", root, common)
    if assessment != entry:
        fields = sorted(k for k in entry.keys() | assessment.keys()
                        if k not in entry or k not in assessment or entry[k] != assessment[k])
        common.append("report.json 与 assessment.json 不一致: " + ", ".join(fields))
    if assessment.get("id") != sample:
        common.append("assessment.id 缺失或不匹配")
    status = assessment.get("status")
    if status not in ("ASSESSED", "PARTIAL_OR_FAILED"):
        common.append(f"样本状态 {status}: {exception_text(assessment.get('exception'))}")
    dump = artifact(folder, "source_dump.json", root, common)
    embedded = assessment.get("templates")
    if not isinstance(embedded, dict):
        common.append("assessment.templates 缺失或损坏")
        embedded = {}
    for template in TEMPLATES:
        errors = list(common)
        plan = artifact(folder, template + ".json", root, errors)
        if embedded.get(template) != plan:
            errors.append(f"assessment.templates.{template} 与模板文件不一致")
        plan_status = plan.get("status")
        created = plan_status == PLAN_CREATED
        risks = ["TEACHER_STUDENT_ALIGNMENT_UNVERIFIED", "TEACHING_SEMANTICS_UNREVIEWED"]
        if not created:
            errors.append(f"计划状态 {plan_status}: {exception_text(plan.get('exception'))}")
        evidence = plan.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        tier = evidence.get("selected_tier")
        if created and tier not in (*RULE_TIERS, "PARTITION", "PRESERVATION"):
            errors.append("selected_tier 缺失或无法识别")
        if tier in ("PRESERVATION", "PARTITION"):
            risks.append(tier)
        if assessment.get("semantic_exception") or assessment.get("analysis_mode") == "STRUCTURAL_FALLBACK":
            risks.append("解析降级: " + exception_text(assessment.get("semantic_exception")))
        if status == "ERROR" or plan_status == "ERROR":
            risks.append("ASSESSMENT_EXCEPTION")
        hash_status, hashes = check_hashes(assessment, dump, evidence)
        if hash_status != "verified":
            errors.append("源哈希不一致" if hash_status == "failed" else "源哈希证据不全")
            risks.append("SOURCE_HASH_MISMATCH" if hash_status == "failed" else "SOURCE_HASH_UNVERIFIED")
        result = audit_blocks(dump or None, plan if created else None, assessment.get("block_count"))
        yield dict(result, sample_id=sample, template=template, sample_status=status,
                   plan_status=plan_status, selected_tier=tier, source_hashes=hashes,
                   hash_status=hash_status, declared_block_count=assessment.get("block_count"),
                   risks=risks, errors=errors + result["errors"])


def summarize(root):
    entries = read_object(root / "report.json", root).get("sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError("report.json: sources must be a nonempty list")
    seen = set()
    rows = []
    for entry in entries:
        sample = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(sample, str) or not re.fullmatch("[a-zA-Z0-9_-]+", sample) or sample in seen:
            raise ValueError("report.json: invalid or duplicate sample id")
        seen.add(sample)
        rows.extend(review_sample(root, entry))
    plans = [r for r in rows if r["plan_status"] == PLAN_CREATED]
    counts = dict(samples=len(entries), template_reviews=len(rows), plans_created=len(plans),
                  rule_paths=sum(r["selected_tier"] in RULE_TIERS for r in plans),
                  preserved=sum(r["selected_tier"] == "PRESERVATION" for r in plans),
                  partition=sum(r["selected_tier"] == "PARTITION" for r in plans),
                  pending_review=len(rows),
                  rows_with_findings=sum(has_findings(r) for r in rows))
    return dict(schema_version=1, counts=counts, teaching_gold="unavailable", rows=rows)


def has_findings(row):
    return bool(row["errors"] or row["physical_status"] != "verified")


def cell(value):
    if isinstance(value, list):
        value = ", ".join(map(str, value))
    return html.escape(str(value if value is not None else "未知")).replace("|", "&#124;").replace("\n", " ")


def markdown(report):
    c = report["counts"]
    lines = ["# Splitter 逐块复核报告", "",
             f"{c['samples']} 份样本 × 2 个模板，共 {c['template_reviews']} 个样本模板组合。"
             f"其中 {c['plans_created']} 个有计划，{c['rule_paths']} 个走规则路径"
             f"，{c['partition']} 个走 PARTITION，{c['preserved']} 个走原文保留路径。"
             f"{c['rows_with_findings']} 个组合存在异常或证据不足。"
             f"全部 {c['pending_review']} 个组合尚待人工评审。", "",
             "哈希核对使用评估器已记录的摘要。物理核对检查块及其归属。"
             "教学语义和教师学生逐题对应均待人工验收。逐块判定请填写 review_checklist.csv。"]
    for row in report["rows"]:
        lines.extend(["", f"## {row['sample_id']} · {row['template']}", "",
                      f"源哈希 {cell(row['hash_status'])}，物理覆盖 {cell(row['physical_status'])}，"
                      f"评估器记录的源块数 {cell(row['declared_block_count'])}。",
                      f"计划 {cell(row['plan_status'])}，路径 {cell(row['selected_tier'])}。", ""])
        for slot, ids in row["slots"].items():
            lines.append(f"- {cell(slot)}：{cell(ids) or '—'}")
        for label, key in (("未归类", "unclassified"), ("遗漏", "missing"), ("重复", "duplicate"),
                           ("风险及待核对项", "risks"), ("证据问题", "errors")):
            lines.append(f"- {label}：{cell(row[key]) or '—'}")
        lines.extend(["", "| 块 ID | 原计划槽位 | 原文短摘要 | 逐块核对项 |",
                      "|---|---|---|---|"])
        for block in row["blocks"]:
            lines.append("| " + " | ".join(cell(block[k]) for k in
                         ("block_id", "original_slots", "summary", "review_flags")) + " |")
    return "\n".join(lines) + "\n"


def spreadsheet_text(value):
    # Keep source snippets literal when a reviewer opens the CSV in a spreadsheet.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def write_package(report, output):
    output.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        payloads = {"review_summary.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    "review_summary.md": markdown(report)}
        for name, payload in payloads.items():
            with (output / name).open("x", encoding="utf-8") as handle:
                created.append(output / name)
                handle.write(payload)
        with (output / "review_checklist.csv").open("x", encoding="utf-8-sig", newline="") as handle:
            created.append(output / "review_checklist.csv")
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("sample_id", "template", "block_id", "selected_tier", "original_slots",
                             "summary", "review_flags", "human_decision", "notes"))
            for row in report["rows"]:
                for block in row["blocks"]:
                    values = (row["sample_id"], row["template"], block["block_id"], row["selected_tier"] or "",
                              ", ".join(block["original_slots"]), block["summary"],
                              ", ".join(block["review_flags"]), "", "")
                    writer.writerow([spreadsheet_text(str(v)) for v in values])
    except BaseException:
        for path in created:
            path.unlink()
        output.rmdir()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        root, output = args.input.resolve(), args.output.resolve()
        if output.exists() or output.is_relative_to(root):
            raise ValueError("请选择诊断目录外的全新输出目录")
        report = summarize(root)
        write_package(report, output)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"无法生成复核包: {exc}\n")
    return int(bool(report["counts"]["rows_with_findings"]))


if __name__ == "__main__":
    sys.exit(main())

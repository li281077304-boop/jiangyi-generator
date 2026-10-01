"""Read-only capability scan of the real corpus against the final Studentizer.

This tool reports; it never expands capability and never publishes a derivative
that survives the process.

Two deliberately separated layers are recorded per source:

1. ``production_gate`` — the authoritative answer. It runs the real production
   entry point ``studentizer_planner.prepare_complete_student`` with the real
   reviewed-evidence registry. This is the exact decision the application makes
   for a teacher-only item.
2. ``diagnostics`` — read-only structure inventory plus a *boundary-system*
   verdict obtained by calling the Studentizer's own boundary validator with an
   empty removal set. It explains why a source could or could not ever reach the
   reviewed capability, but it is not evidence that a complete reviewed answer
   ledger exists.

Nothing here infers answer ownership, and no low coverage figure is treated as a
reason to add OOXML capability.

Usage:
    python scan_capability.py --corpus C:\\xml-uat\\stage3-expansion \
        --out <scan.json> [--report <report.md>]
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import sys
import tempfile
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "v1.2-xml-experiment/res/app"
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
sys.path.insert(0, str(AUDIT))

from build_reviewed_manifest import referenced_targets  # noqa: E402
from reviewed_studentizer import ReviewedManifestError, registry  # noqa: E402
from studentizer import TAG  # noqa: E402
from studentizer_planner import prepare_complete_student  # noqa: E402
from studentizer_ranges import _boundaries  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_PLAIN_REMOVABLE = {TAG(name) for name in (
    "p", "pPr", "pStyle", "jc", "spacing", "ind", "keepNext", "keepLines", "widowControl",
    "r", "rPr", "rStyle", "b", "bCs", "i", "iCs", "u", "color", "sz", "szCs", "rFonts",
    "lang", "t", "textAlignment", "vertAlign")}
_REVISION = {"ins", "del", "moveFrom", "moveTo", "commentRangeStart", "commentRangeEnd",
             "commentReference", "footnoteReference", "endnoteReference", "sdt", "customXml",
             "txbxContent"}


def _counts(root, parts):
    body = root.find(TAG("body"))
    children = list(body)
    local = {}
    for node in body.iter():
        if not isinstance(node.tag, str):
            continue
        name = etree.QName(node).localname
        local[name] = local.get(name, 0) + 1
    starts_by_name = {}
    for node in body.iter(TAG("bookmarkStart")):
        starts_by_name.setdefault(node.get(TAG("name")), []).append(node)
    links = list(body.iter(TAG("hyperlink")))
    unresolved = 0
    ambiguous = 0
    for node in links:
        anchor = node.get(TAG("anchor"))
        if not anchor:
            continue
        matches = starts_by_name.get(anchor, [])
        if not matches:
            unresolved += 1
        elif len(matches) != 1:
            ambiguous += 1
    plain_removable = sum(1 for child in children
                          if child.tag == TAG("p") and all(n.tag in _PLAIN_REMOVABLE for n in child.iter()))
    return {
        "body_blocks": len(children),
        "paragraphs": local.get("p", 0),
        "tables": local.get("tbl", 0),
        "textbox_contents": local.get("txbxContent", 0),
        "omml": local.get("oMath", 0) + local.get("oMathPara", 0),
        "ole_objects": local.get("object", 0),
        "drawings": local.get("drawing", 0),
        "pictures": local.get("pict", 0),
        "bookmark_starts": local.get("bookmarkStart", 0),
        "hyperlinks": len(links),
        "hyperlink_anchors_unresolved": unresolved,
        "hyperlink_anchors_ambiguous": ambiguous,
        "field_chars": local.get("fldChar", 0),
        "field_instructions": local.get("instrText", 0),
        "simple_fields": local.get("fldSimple", 0),
        "revision_or_reference_markup": sum(local.get(name, 0) for name in _REVISION)
                                    + sum(value for name, value in local.items() if name.endswith("Change")),
        "plain_removable_paragraphs": plain_removable,
        "cross_story_parts": sum(1 for name in parts if name.startswith("word/")
                                 and name.endswith(".xml") and name != "word/document.xml"),
    }


def boundary_verdict(root, parts):
    """Read-only boundary-system capability verdict from the real validator."""
    acknowledged = referenced_targets(root, parts)
    try:
        _boundaries(root, set(), parts, acknowledged)
    except Exception as exc:  # noqa: BLE001 - the refusal code is the finding
        return {"verdict": getattr(exc, "code", type(exc).__name__),
                "detail": str(getattr(exc, "detail", exc)),
                "acknowledged_missing_targets": len(acknowledged)}
    return {"verdict": "NO_BOUNDARY_SYSTEM_BLOCKER", "detail": "",
            "acknowledged_missing_targets": len(acknowledged)}


def scan(corpus, baseline, manifest_dir=None, limit=None):
    baseline_path = Path(baseline)
    corpus_root = Path(corpus)
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    samples = data["samples"][: limit or len(data["samples"])]
    try:
        loaded = registry(manifest_dir)
        provider = loaded.evidence_provider()
        registry_error = None
    except ReviewedManifestError as exc:
        loaded, provider, registry_error = None, None, str(exc)
    records = []
    with tempfile.TemporaryDirectory() as scratch:
        for sample in samples:
            source = corpus_root / sample["source_path"]
            record = {"sample_id": sample["sample_id"], "subject": sample.get("subject"),
                      "name": sample.get("name"), "origin_chain": sample.get("origin_chain")}
            if not source.is_file():
                record.update(missing=True, production_gate={"status": "MISSING_SOURCE"})
                records.append(record)
                continue
            raw = source.read_bytes()
            digest = sha256(raw).hexdigest()
            record["source_bytes"] = len(raw)
            record["source_sha256"] = digest
            record["source_manifest_sha_ok"] = digest == sample.get("source_sha256")
            output = Path(scratch) / (sample["sample_id"] + "-student.docx")
            result, coverage = prepare_complete_student(raw, output, provider)
            record["production_gate"] = {
                "status": result.status, "engine": result.engine,
                "reason_code": result.reason_code, "reason_detail": result.reason_detail,
                "elapsed_seconds": result.elapsed_seconds,
                "removed_paragraphs": len(result.mutations) if result.mutations else 0,
                "coverage": coverage,
            }
            record["reviewed_evidence"] = (loaded.lookup(digest).sample_id
                                           if loaded is not None and loaded.lookup(digest) else None)
            if output.exists():
                output.unlink()
            with zipfile.ZipFile(BytesIO(raw)) as package:
                parts = {name: package.read(name) for name in package.namelist()}
            root = etree.fromstring(parts["word/document.xml"],
                                    etree.XMLParser(resolve_entities=False, no_network=True))
            record["diagnostics"] = _counts(root, parts)
            record["diagnostics"].update(boundary_verdict(root, parts))
            records.append(record)
    supported = [r for r in records if r.get("production_gate", {}).get("status") == "XML_PREPARED"]
    fallback = [r for r in records if r.get("production_gate", {}).get("status") == "STUDENTIZER_FALLBACK_REQUIRED"]
    others = [r for r in records if r not in supported and r not in fallback]
    reasons, verdicts, details = {}, {}, {}
    for record in fallback:
        code = record["production_gate"]["reason_code"]
        reasons[code] = reasons.get(code, 0) + 1
    for record in records:
        if "diagnostics" in record:
            verdict = record["diagnostics"]["verdict"]
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
            if verdict != "NO_BOUNDARY_SYSTEM_BLOCKER":
                detail = record["diagnostics"]["detail"]
                details[detail] = details.get(detail, 0) + 1
    renderer_blocked = [record["sample_id"] for record in records
                        if record.get("diagnostics", {}).get("hyperlink_anchors_unresolved")]
    return {
        "corpus_root": str(corpus_root), "baseline": str(baseline_path),
        "baseline_commit": data.get("baseline_commit"),
        "registry_error": registry_error,
        "reviewed_manifests": [manifest.sample_id for manifest in loaded.manifests()] if loaded else [],
        "total_samples": len(records),
        "xml_studentizer_supported": len(supported),
        "fallback": len(fallback),
        "other_outcomes": len(others),
        "fallback_reason_distribution": reasons,
        "boundary_verdict_distribution": verdicts,
        "boundary_verdict_detail_distribution": details,
        "renderer_projection_blocked_samples": renderer_blocked,
        "xml_route_samples": [record["sample_id"] for record in supported],
        "fallback_samples": [{"sample_id": record["sample_id"],
                              "reason_code": record["production_gate"].get("reason_code"),
                              "boundary_verdict": record.get("diagnostics", {}).get("verdict"),
                              "boundary_detail": record.get("diagnostics", {}).get("detail")}
                             for record in fallback],
        "coverage_note": ("Reviewed-evidence coverage is %d/%d. Low coverage is the expected "
                          "result and was not treated as a reason to add OOXML capability."
                          % (len(supported), len(records))),
        "records": records,
    }


def render_report(scan_result):
    lines = ["# C3 R10 — 27-source Studentizer capability scan", "",
             "Read-only scan against the final Studentizer capability. Coverage is stated as",
             "measured; nothing was expanded to raise it.", "",
             "## Method and authority", "",
             "Two layers are recorded and must not be conflated:", "",
             "- **Production gate (authoritative).** Each source is passed through the real",
             "  production entry point `studentizer_planner.prepare_complete_student` with the",
             "  real reviewed-evidence registry. This is the exact decision the application",
             "  makes for a teacher-only item.",
             "- **Boundary verdict (diagnostic).** A read-only call into the Studentizer's own",
             "  boundary validator with an empty removal set. It states whether the boundary",
             "  systems of that document are inside the reviewed capability. It is **not**",
             "  evidence that a complete reviewed answer ledger exists, and it authorizes",
             "  nothing.",
             "",
             "`Unresolved anchors` counts main-body hyperlinks whose bookmark anchor does not",
             "resolve to exactly one bookmark start. The frozen B-Line projection refuses any",
             "selected hyperlink with an unresolvable anchor, so a non-zero value means the",
             "XML renderer will refuse that source even when preparation succeeds.", "",
             "| Metric | Value |", "|---|---:|",
             "| total samples | %d |" % scan_result["total_samples"],
             "| XML Studentizer supported | %d |" % scan_result["xml_studentizer_supported"],
             "| fallback | %d |" % scan_result["fallback"],
             "| other outcomes | %d |" % scan_result["other_outcomes"],
             "| reviewed manifests mounted | %s |" % (", ".join(scan_result["reviewed_manifests"]) or "none"),
             "| registry error | %s |" % (scan_result["registry_error"] or "none"), "",
             "## Production gate reason distribution", "",
             "| Reason code | samples |", "|---|---:|"]
    for code, count in sorted(scan_result["fallback_reason_distribution"].items(),
                              key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (code, count))
    lines += ["", "## Boundary-system verdict distribution (diagnostic)", "",
              "| Verdict | samples |", "|---|---:|"]
    for code, count in sorted(scan_result["boundary_verdict_distribution"].items(),
                              key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (code, count))
    lines += ["", "| First boundary refusal detail | samples |", "|---|---:|"]
    for code, count in sorted(scan_result["boundary_verdict_detail_distribution"].items(),
                              key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (code, count))
    lines += ["", "| Samples with an unresolvable hyperlink anchor | count |", "|---|---:|",
              "| %s | %d |" % (", ".join(scan_result["renderer_projection_blocked_samples"]) or "none",
                               len(scan_result["renderer_projection_blocked_samples"])), "",
              "## Per-source result", "",
              "| Sample | Subject | Route | Production reason | Boundary verdict | Blocks | Tables | Textboxes | Fields | Bookmarks | Unresolved anchors | Plain removable |",
              "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for record in scan_result["records"]:
        gate = record.get("production_gate", {})
        diag = record.get("diagnostics", {})
        route = "XML" if gate.get("status") == "XML_PREPARED" else "FALLBACK"
        lines.append("| %s | %s | %s | `%s` | `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
            record["sample_id"], record.get("subject") or "-", route,
            gate.get("reason_code") or "-", diag.get("verdict", "-"),
            diag.get("body_blocks", "-"), diag.get("tables", "-"), diag.get("textbox_contents", "-"),
            diag.get("field_chars", "-"), diag.get("bookmark_starts", "-"),
            diag.get("hyperlink_anchors_unresolved", "-"), diag.get("plain_removable_paragraphs", "-")))
    lines += ["", "## Scope statement", "",
              "The boundary verdict is a read-only capability statement about boundary systems only.",
              "It does not prove that a complete reviewed answer ledger exists for that source, and it is",
              "not a removal authorization. Low reviewed coverage is the expected outcome of this round;",
              "no OOXML feature was added to improve the figure.",
              "Machine-readable detail: `fixtures/c3-r10-capability-scan.json`."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--manifest-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    baseline = args.baseline or (args.corpus / "baseline_inputs.json")
    result = scan(args.corpus, baseline, args.manifest_dir, args.limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("total_samples", "xml_studentizer_supported", "fallback", "other_outcomes",
                       "fallback_reason_distribution", "boundary_verdict_distribution",
                       "xml_route_samples", "registry_error")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

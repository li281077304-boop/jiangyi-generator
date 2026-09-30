"""Reproducible B4 real-source XML/package render gate.

Creates a fresh output folder per run under C:\\xml-uat\\b4-real-renders,
verifies source hashes against the frozen Stage3 manifest, and renders every
top-level StructDoc block to both current DOCX templates through the minimal
renderer. This is not Word/WPS visual or open/save/reopen UAT.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from docx import Document  # noqa: E402
from package_validator import validate_package  # noqa: E402
from renderer_xml_minimal import BlockSpan, ProjectionError, TemplateTarget, render_minimal  # noqa: E402
from struct_doc import read_struct_doc  # noqa: E402

MANIFEST_PATH = Path(r"C:\xml-uat\stage3-expansion\baseline_inputs.json")
SOURCE_ROOT = Path(r"C:\xml-uat\stage3-expansion")
OUTPUT_ROOT = Path(r"C:\xml-uat\b4-real-renders")
TEMPLATES = {
    "1v1": ROOT / "v1.1-stable" / "res" / "app" / "2025+1v1讲义模板(2).docx",
    "class": ROOT / "v1.1-stable" / "res" / "app" / "2025班课模板.docx",
}
SAMPLE_IDS = ("X006", "X012", "X021")
GUARDED_TAGS = {
    "bookmarkStart", "bookmarkEnd", "commentRangeStart", "commentRangeEnd",
    "commentReference", "footnoteReference", "endnoteReference", "permStart",
    "permEnd", "sdt", "customXml", "ins", "del", "moveFrom", "moveTo",
    "moveFromRangeStart", "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd",
    "cellIns", "cellDel", "cellMerge", "conflictIns", "conflictDel",
}


class B4HarnessFatalError(RuntimeError):
    """A harness or source-validation failure that must abort the B4 run."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_run_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUTPUT_ROOT / ("run-" + stamp + "-" + uuid4().hex[:8])
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def inspect_guarded_blocks(source: Path, struct) -> list[dict]:
    document = Document(str(source))
    body = document.element.body
    found = []
    for block in struct.blocks:
        if block.body_idx < 0 or block.body_idx >= len(body):
            continue
        element = body[block.body_idx]
        tags = sorted({node.tag.split("}", 1)[1] for node in element.iter()
                       if node.tag.startswith("{%s}" %
                           "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
                       and (node.tag.split("}", 1)[1] in GUARDED_TAGS
                            or node.tag.split("}", 1)[1].endswith("Change"))})
        if tags:
            found.append({"node_id": "b%d" % block.seq, "tags": tags})
    return found


def run() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {item["sample_id"]: item for item in manifest["samples"]}
    for template in TEMPLATES.values():
        if not template.is_file():
            raise FileNotFoundError("required template is missing: %s" % template)

    run_dir = make_run_dir()
    results = []
    for sample_id in SAMPLE_IDS:
        entry = entries[sample_id]
        source = SOURCE_ROOT / entry["source_path"]
        actual_hash = sha256(source)
        if actual_hash.lower() != entry["source_sha256"].lower():
            raise ValueError("source hash mismatch for %s: expected %s got %s" %
                             (sample_id, entry["source_sha256"], actual_hash))

        try:
            struct = read_struct_doc(str(source))
            spans = [BlockSpan("b%d" % block.seq, "b%d" % block.seq)
                     for block in struct.blocks]
            block_kinds = {kind: sum(1 for block in struct.blocks if block.kind == kind)
                           for kind in ("paragraph", "table", "unknown")}
            guarded_blocks = inspect_guarded_blocks(source, struct)
            source_package_report = validate_package(str(source))
            source_capabilities = dict(struct.stats)
        except Exception as exc:
            raise B4HarnessFatalError(
                "source preparation failed for %s: %s: %s" %
                (sample_id, type(exc).__name__, exc)
            ) from exc

        if not source_package_report.get("valid", False):
            raise B4HarnessFatalError(
                "source package validation failed for %s: %s" %
                (sample_id, json.dumps(source_package_report, ensure_ascii=False, sort_keys=True))
            )

        for template_type, template in TEMPLATES.items():
            output = run_dir / ("%s-%s.docx" % (sample_id.lower(), template_type))
            record = {
                "sample_id": sample_id,
                "subject": entry["subject"],
                "source": str(source),
                "source_sha256": actual_hash,
                "template_type": template_type,
                "template": str(template),
                "template_sha256": sha256(template),
                "block_count": len(spans),
                "block_kinds": block_kinds,
                "source_capabilities": source_capabilities,
                "guarded_top_level_blocks": guarded_blocks,
                "source_package_report": source_package_report,
                "output": str(output),
            }
            try:
                result = render_minimal(str(source), str(template), spans, str(output),
                                        TemplateTarget(0))
                record.update({
                    "status": "XML_AND_PACKAGE_SUPPORTED",
                    "inserted_nodes": result.inserted_nodes,
                    "resource_report": result.resource_report,
                    "package_report": result.package_report,
                    "output_package_validation": "PASS",
                    "word_wps_uat": "PENDING",
                })
            except ProjectionError as exc:
                record.update({
                    "status": "FALLBACK_REQUIRED",
                    "reason": str(exc),
                    "reason_type": type(exc).__name__,
                    "output_created": output.exists(),
                    "output_package_validation": "NOT_RUN_NO_OUTPUT",
                    "word_wps_uat": "NOT_RUN_FOR_REJECTED_CASE",
                })
            except Exception as exc:
                raise B4HarnessFatalError(
                    "unexpected renderer failure for %s/%s: %s: %s" %
                    (sample_id, template_type, type(exc).__name__, exc)
                ) from exc
            results.append(record)

    report = {
        "gate": "B4_REAL_XML_PACKAGE_RENDER",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "approved_code_base": "9c29c1363cd5b9b13bab33643ec87d8d050f4dc1",
        "stage3_manifest": str(MANIFEST_PATH),
        "stage3_baseline_commit": manifest["baseline_commit"],
        "run_dir": str(run_dir),
        "template_target": {"body_child_index": 0},
        "real_com_uat": {
            "status": "REAL_COM_UAT_PENDING",
            "reason": "Codex Computer Use inventory returned apps=[] and native-app controls are unavailable in this environment.",
            "steps_passed": [],
        },
        "samples": results,
        "summary": {
            "xml_package_supported": sum(r["status"] == "XML_AND_PACKAGE_SUPPORTED" for r in results),
            "fallback_required": sum(r["status"] == "FALLBACK_REQUIRED" for r in results),
            "word_wps_uat_passed": 0,
            "word_wps_uat_pending": len(results),
            "word_wps_uat_not_run_due_to_fallback": sum(
                r["word_wps_uat"] == "NOT_RUN_FOR_REJECTED_CASE" for r in results),
        },
    }
    manifest_out = run_dir / "run_manifest.json"
    manifest_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))

# -*- coding: utf-8 -*-
"""Explicit, isolated corpus runner for Windows v1.2 XML UAT.

Default behavior is a metadata-only dry run. Real source DOCX packages are not
opened unless ``--run`` is explicitly supplied. Outputs and reports must live
outside both the corpus and the repository, and the tool rejects paths under
v1.1-stable.
"""
from __future__ import annotations

import argparse
import csv
import datetime
from collections import Counter
import json
import os
import re
from pathlib import Path
import sys
import statistics
import time
import zipfile


SCRIPT_PATH = Path(__file__).resolve()
EXPERIMENT_DIR = SCRIPT_PATH.parents[2]
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
APP_DIR = EXPERIMENT_DIR / "res" / "app"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(SCRIPT_PATH.parent))

from docx import Document

import xml_engine
from package_evidence import collect_package_evidence, collect_selected_block_evidence


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_META_FIELDS = ("subject", "grade", "topic", "handout_type", "objectives", "difficulties")


def _is_within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_sample(sample, corpus_root, repository_root):
    sample_id = sample.get("id")
    if not isinstance(sample_id, str) or not _ID_RE.fullmatch(sample_id):
        raise ValueError("sample id must contain only letters, digits, '.', '_' or '-'")
    source_relative = sample.get("source")
    template_relative = sample.get("template")
    if not isinstance(source_relative, str) or not source_relative:
        raise ValueError("sample %s has no relative source path" % sample_id)
    if Path(source_relative).is_absolute():
        raise ValueError("sample %s source must be relative to --corpus-root" % sample_id)
    source = (corpus_root / source_relative).resolve()
    if not _is_within(source, corpus_root):
        raise ValueError("sample %s source escapes --corpus-root" % sample_id)
    if not isinstance(template_relative, str) or not template_relative:
        raise ValueError("sample %s has no relative template path" % sample_id)
    template_path = Path(template_relative)
    template = (template_path if template_path.is_absolute()
                else repository_root / template_path).resolve()
    if source.suffix.lower() != ".docx":
        raise ValueError("sample %s source must be .docx" % sample_id)
    if template.suffix.lower() != ".docx":
        raise ValueError("sample %s template must be .docx" % sample_id)
    meta = sample.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("sample %s must specify meta" % sample_id)
    missing_meta = [key for key in _META_FIELDS if not isinstance(meta.get(key), str)]
    if missing_meta:
        raise ValueError("sample %s meta must specify string fields: %s" %
                          (sample_id, ", ".join(missing_meta)))
    return {"id": sample_id, "source": source, "template": template,
            "meta": {key: meta[key] for key in _META_FIELDS}}


def _load_manifest(path, corpus_root, repository_root):
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError("manifest schema_version must be 1")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("manifest samples must be a non-empty list")
    resolved = [_resolve_sample(sample, corpus_root, repository_root)
                for sample in samples]
    ids = [sample["id"] for sample in resolved]
    if len(ids) != len(set(ids)):
        raise ValueError("sample ids must be unique")
    return resolved


def _check_isolated_directory(path, label, corpus_root, repository_root):
    if _is_within(path, repository_root):
        raise ValueError("%s must be outside the repository: %s" % (label, path))
    if _is_within(repository_root / "v1.1-stable", path) or \
            _is_within(path, (repository_root / "v1.1-stable").resolve()):
        raise ValueError("%s must not overlap v1.1-stable: %s" % (label, path))
    if _is_within(path, corpus_root) or _is_within(corpus_root, path):
        raise ValueError("%s must be separate from the read-only corpus: %s" %
                         (label, path))


def _dry_run(samples):
    print("DRY RUN: manifest/file metadata only; DOCX packages were not opened.")
    missing = False
    for sample in samples:
        source = sample["source"]
        template = sample["template"]
        source_size = source.stat().st_size if source.is_file() else None
        template_size = template.stat().st_size if template.is_file() else None
        if source_size is None or template_size is None:
            missing = True
        print("%s: source=%s (%s bytes), template=%s (%s bytes)" %
              (sample["id"], source, source_size, template, template_size))
    return 1 if missing else 0


def _failure_category(error):
    report = getattr(error, "report", {}) or {}
    code = report.get("code")
    if code in ("split_failed", "invalid_block_range"):
        return "SPLIT_BUG"
    if code == "missing_template_anchor":
        return "TEMPLATE_BUG"
    migration = report.get("migration", {})
    if migration.get("unsupported"):
        return "UNSUPPORTED_WORD_FEATURE"
    if report.get("package_validation"):
        return "VALIDATOR_GAP"
    if isinstance(error, (zipfile.BadZipFile, EOFError)) or \
            type(error).__name__ in ("PackageNotFoundError", "PartNotFoundError"):
        return "INPUT_CORRUPTION"
    return "ENGINE_BUG"


def _ole_preservation(source_parts, template_parts, output_parts):
    expected = Counter(item["sha256"] for item in source_parts)
    template = Counter(item["sha256"] for item in template_parts)
    output = Counter(item["sha256"] for item in output_parts)
    added = output - template
    missing = expected - added
    return {
        "applicable": bool(expected),
        "expected_source_embedding_parts": len(source_parts),
        "preserved_embedding_parts": sum(expected.values()) - sum(missing.values()),
        "missing_sha256_counts": dict(sorted(missing.items())),
        "binary_sha256_preserved": (not expected) or (not missing),
        "source_embedding_sha256": sorted(expected.elements()),
        "output_added_embedding_sha256": sorted(added.elements()),
    }


def _run_sample(sample, corpus_root, output_root, repository_root):
    source, template = sample["source"], sample["template"]
    record = {
        "sample_id": sample["id"],
        "source": str(source.relative_to(corpus_root)),
        "template": str(template.relative_to(repository_root))
        if _is_within(template, repository_root) else str(template),
        "source_bytes": source.stat().st_size if source.is_file() else None,
        "status": "FAILED",
        "failure_category": None,
        "error": None,
        "blocks": [],
        "selected_source": None,
        "source_package": None,
        "template_package": None,
        "output_package": None,
        "ole_preservation": None,
        "generation_seconds": None,
        "output_bytes": None,
        "validator": None,
        "word_uat": "NOT_RUN",
    }
    if not source.is_file():
        record["failure_category"] = "INPUT_CORRUPTION"
        record["error"] = "source DOCX does not exist"
        return record
    if not template.is_file():
        record["failure_category"] = "TEMPLATE_BUG"
        record["error"] = "template DOCX does not exist"
        return record
    output_directory = output_root / sample["id"]
    output_directory.mkdir(parents=True, exist_ok=False)
    output = output_directory / (sample["id"] + "_xml.docx")
    start = time.perf_counter()
    try:
        record["source_package"] = collect_package_evidence(source)
        record["template_package"] = collect_package_evidence(template)
        source_paragraphs, source_children = xml_engine.scan(str(source))
        block_candidates = xml_engine.split_ideal(source_paragraphs)
        if isinstance(block_candidates, (list, tuple)) and block_candidates:
            valid_candidates = all(
                isinstance(block, (list, tuple)) and len(block) == 3 and
                isinstance(block[0], str) and
                isinstance(block[1], int) and not isinstance(block[1], bool) and
                isinstance(block[2], int) and not isinstance(block[2], bool) and
                1 <= block[1] <= block[2] <= len(source_paragraphs)
                for block in block_candidates)
            if valid_candidates:
                adjusted = xml_engine.image_attach_fix(block_candidates, source_paragraphs)
                valid_adjusted = all(
                    1 <= block[1] <= block[2] <= len(source_paragraphs)
                    for block in adjusted)
                if valid_adjusted:
                    source_doc = Document(str(source))
                    record["selected_source"] = collect_selected_block_evidence(
                        source_doc, source_children, adjusted)
                    record["blocks"] = [list(block) for block in adjusted]

        blocks_used, stats = xml_engine.build(
            str(source), str(template), str(output), meta=sample["meta"])
        record["blocks"] = [list(block) for block in blocks_used]
        record["migration"] = stats.get("migration", {})
        record["validator"] = stats.get("package_validation", {})
        record["generation_seconds"] = stats.get("elapsed_s")
        record["output_bytes"] = output.stat().st_size
        record["output_package"] = collect_package_evidence(output)
        selected_embeddings = (record["selected_source"] or {}).get("embedding_parts", [])
        record["ole_preservation"] = _ole_preservation(
            selected_embeddings,
            record["template_package"]["embedding_parts"],
            record["output_package"]["embedding_parts"],
        )
        if record["migration"].get("stats", {}).get("ole_references_copied", 0) != \
                (record["selected_source"] or {}).get("ole_references", 0):
            record["failure_category"] = "ENGINE_BUG"
            record["error"] = "OLE reference count differs between selected source blocks and importer stats"
            return record
        if record["ole_preservation"]["applicable"] and not \
                record["ole_preservation"]["binary_sha256_preserved"]:
            record["failure_category"] = "BLOCKER"
            record["error"] = "one or more selected OLE embedding SHA256 values are missing from output"
            return record
        if not record["validator"].get("valid", False):
            record["failure_category"] = "VALIDATOR_GAP"
            record["error"] = "output package validator did not report valid"
            return record
        record["status"] = "XML_PACKAGE_PASS_WORD_UAT_PENDING"
        return record
    except Exception as error:
        record["failure_category"] = _failure_category(error)
        record["error"] = "%s: %s" % (type(error).__name__, error)
        if hasattr(error, "report"):
            record["error_report"] = error.report
        if output.exists():
            output.unlink()
        return record
    finally:
        if record["generation_seconds"] is None:
            record["generation_seconds"] = round(time.perf_counter() - start, 6)


def _write_reports(records, report_root):
    report_root.mkdir(parents=True, exist_ok=True)
    timed_records = [record for record in records
                     if isinstance(record.get("generation_seconds"), (int, float))]
    duration_values = [record["generation_seconds"] for record in timed_records]
    payload = {
        "schema_version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "corpus_uat": "NOT_CONFIRMED",
        "word_uat": "NOT_RUN",
        "benchmark": {
            "samples_timed": len(duration_values),
            "total_seconds": round(sum(duration_values), 6),
            "p50_seconds": round(statistics.median(duration_values), 6)
            if duration_values else None,
            "slowest_sample_id": max(timed_records,
                                      key=lambda record: record["generation_seconds"])["sample_id"]
            if timed_records else None,
            "slowest_seconds": round(max(duration_values), 6) if duration_values else None,
        },
        "results": records,
    }
    json_path = report_root / "corpus_uat.json"
    with open(json_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)

    fields = ("sample_id", "source", "template", "status", "failure_category",
              "source_bytes", "output_bytes", "generation_seconds",
              "paragraphs", "tables", "image_references", "vml_image_references",
              "ole_references", "ole_preview_image_references", "embedding_parts", "relationship_count",
              "validator_valid", "validator_errors", "ole_sha256_preserved", "word_uat")
    csv_path = report_root / "corpus_uat.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            selected = record.get("selected_source") or {}
            output_package = record.get("output_package") or {}
            validator = record.get("validator") or {}
            ole = record.get("ole_preservation") or {}
            writer.writerow({
                **record,
                "paragraphs": selected.get("paragraphs"),
                "tables": selected.get("tables"),
                "image_references": selected.get("image_references"),
                "vml_image_references": selected.get("vml_image_references"),
                "ole_references": selected.get("ole_references"),
                "ole_preview_image_references": selected.get("ole_preview_image_references"),
                "embedding_parts": len(selected.get("embedding_parts", [])),
                "relationship_count": output_package.get("relationship_count"),
                "validator_valid": validator.get("valid"),
                "validator_errors": " | ".join(validator.get("errors", [])),
                "ole_sha256_preserved": ole.get("binary_sha256_preserved"),
            })
    return json_path, csv_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="JSON list of explicitly selected samples")
    parser.add_argument("--corpus-root", required=True, help="Root for read-only source paths in manifest")
    parser.add_argument("--repo-root", default=str(REPOSITORY_ROOT))
    parser.add_argument("--run", action="store_true",
                        help="Open selected source packages, generate isolated outputs, and write evidence")
    parser.add_argument("--output-dir", help="Required with --run; must be outside repository and corpus")
    parser.add_argument("--report-dir", help="Required with --run; must be separate from output and corpus")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).resolve()
    corpus_root = Path(args.corpus_root).resolve()
    repository_root = Path(args.repo_root).resolve()
    samples = _load_manifest(manifest_path, corpus_root, repository_root)
    if not args.run:
        return _dry_run(samples)
    if os.name != "nt":
        parser.error("real-corpus generation is gated to the supplied Windows UAT host; Mac mode is dry-run only")
    if not args.output_dir or not args.report_dir:
        parser.error("--run requires both --output-dir and --report-dir")

    output_root = Path(args.output_dir).resolve()
    report_root = Path(args.report_dir).resolve()
    _check_isolated_directory(output_root, "output directory", corpus_root, repository_root)
    _check_isolated_directory(report_root, "report directory", corpus_root, repository_root)
    if _is_within(output_root, report_root) or _is_within(report_root, output_root):
        raise ValueError("output and report directories must be separate")
    if (output_root.exists() and any(output_root.iterdir())) or \
            (report_root.exists() and any(report_root.iterdir())):
        raise ValueError("output and report directories must be empty or not yet exist")

    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    records = [_run_sample(sample, corpus_root, output_root, repository_root)
               for sample in samples]
    json_path, csv_path = _write_reports(records, report_root)
    failed = [record for record in records if record["status"] != "XML_PACKAGE_PASS_WORD_UAT_PENDING"]
    print("Generated %d outputs; %d require investigation." % (len(records), len(failed)))
    print("JSON evidence: %s" % json_path)
    print("CSV summary: %s" % csv_path)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthetic coverage for the read-only capability scan.

These cases use synthetic DOCX packages. They make no real-corpus, reviewed
coverage, renderer or COM claim.
"""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import copy
import json
import sys
import zipfile

from lxml import etree
import pytest

from test_batch_job_service import docx

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
AUDIT = ROOT / "tools" / "studentizer_audit"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(AUDIT))

from reviewed_studentizer import CONTRACT  # noqa: E402
from scan_capability import boundary_verdict, render_report, scan  # noqa: E402
from studentizer import TAG, element_sha256  # noqa: E402

REVIEW_ID = "synthetic-scan-review"


def _root(data: bytes):
    with zipfile.ZipFile(BytesIO(data)) as package:
        return etree.fromstring(package.read("word/document.xml"),
                                etree.XMLParser(resolve_entities=False, no_network=True))


def _parts(data: bytes):
    with zipfile.ZipFile(BytesIO(data)) as package:
        return {name: package.read(name) for name in package.namelist()}


def _rewrite(data: bytes, change) -> bytes:
    root = _root(data)
    change(root.find(TAG("body")))
    buffer = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as old, zipfile.ZipFile(buffer, "w") as new:
        for item in old.infolist():
            value = old.read(item.filename)
            if item.filename == "word/document.xml":
                value = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
            new.writestr(item, value)
    return buffer.getvalue()


def source_bytes():
    return docx("知识点：加法", "1．求 2+3？", "【答案】5", "2．求 3+4？", "【答案】7")


def manifest_for(data: bytes) -> dict:
    root = _root(data)
    children = list(root.find(TAG("body")))
    prompts, answers = [1, 3], [2, 4]
    body = []
    for index, node in enumerate(children):
        owner = next((("q%d" % (n + 1)) for n, (prompt, answer) in enumerate(zip(prompts, answers))
                      if index == prompt or index == answer), None)
        body.append({"index": index, "sha256": element_sha256(node),
                     "decision": "REMOVE" if index in answers else "RETAIN",
                     "reason": "reviewed synthetic decision", "owner_id": owner})
    expected_root = _root(data)
    expected_children = list(expected_root.find(TAG("body")))
    for index in sorted(answers, reverse=True):
        expected_root.find(TAG("body")).remove(expected_children[index])
    ranges = [{"owner_id": "q%d" % (n + 1), "prompt_start": prompt, "prompt_end": prompt,
               "answer_start": answer, "answer_end": answer,
               "reason": "reviewed synthetic range"}
              for n, (prompt, answer) in enumerate(zip(prompts, answers))]
    return {"manifest_version": 1, "contract": CONTRACT, "sample_id": "SYN001", "subject": "test",
            "review_id": REVIEW_ID, "source_sha256": sha256(data).hexdigest(),
            "expected_document_sha256": element_sha256(expected_root),
            "inherited_missing_bookmark_targets": [], "approval_document": "synthetic",
            "removed_blocks": len(answers), "retained_blocks": len(children) - len(answers),
            "reviewed_ranges": len(ranges), "body": body, "ranges": ranges}


def build_corpus(tmp_path, entries):
    corpus = tmp_path / "corpus"
    sources = corpus / "sources"
    sources.mkdir(parents=True)
    samples = []
    for index, data in enumerate(entries):
        name = "SYN%03d.docx" % (index + 1)
        (sources / name).write_bytes(data)
        samples.append({"sample_id": "SYN%03d" % (index + 1), "subject": "test", "name": name,
                        "source_path": "sources/" + name,
                        "source_sha256": sha256(data).hexdigest(), "origin_chain": "synthetic"})
    baseline = corpus / "baseline_inputs.json"
    baseline.write_text(json.dumps({"baseline_commit": "synthetic", "corpus_root": str(corpus),
                                    "samples": samples}, ensure_ascii=False), encoding="utf-8")
    return corpus, baseline


def write_manifests(directory: Path, manifests):
    directory.mkdir(parents=True, exist_ok=True)
    for index, manifest in enumerate(manifests):
        (directory / ("MAN%03d.json" % (index + 1))).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory


def test_scan_separates_supported_route_from_fallback(tmp_path):
    plain = source_bytes()
    boxed = _rewrite(plain, lambda body: etree.SubElement(body[0], TAG("txbxContent")))
    corpus, baseline = build_corpus(tmp_path, [plain, boxed])
    manifests = write_manifests(tmp_path / "manifests", [manifest_for(plain)])
    result = scan(corpus, baseline, manifests)

    assert result["total_samples"] == 2
    assert result["xml_studentizer_supported"] == 1 and result["xml_route_samples"] == ["SYN001"]
    assert result["fallback"] == 1 and result["other_outcomes"] == 0
    assert result["fallback_reason_distribution"] == {"STUDENTIZER_COVERAGE_UNPROVEN": 1}
    assert result["fallback_samples"] == [{"sample_id": "SYN002",
                                           "reason_code": "STUDENTIZER_COVERAGE_UNPROVEN",
                                           "boundary_verdict": "STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED",
                                           "boundary_detail": "unsupported boundary system: txbxContent"}]
    assert result["boundary_verdict_detail_distribution"] == {"unsupported boundary system: txbxContent": 1}
    assert result["renderer_projection_blocked_samples"] == []
    assert result["reviewed_manifests"] == ["SYN001"] and result["registry_error"] is None
    assert all(record["source_manifest_sha_ok"] for record in result["records"])
    supported = result["records"][0]
    assert supported["reviewed_evidence"] == "SYN001"
    assert supported["production_gate"]["status"] == "XML_PREPARED"
    assert supported["production_gate"]["removed_paragraphs"] == 2
    assert supported["production_gate"]["coverage"]["reviewed_ranges"] == 2
    assert supported["production_gate"]["coverage"]["coverage_basis"] == "EXACT_REVIEWED_GOLDEN_PHYSICAL_RANGE"
    assert not list(Path(result["corpus_root"]).rglob("*student.docx"))


def test_scan_reports_unresolvable_anchors_and_missing_sources(tmp_path):
    linked = source_bytes()

    def add_broken_link(body):
        hyperlink = etree.SubElement(body[0], TAG("hyperlink"))
        hyperlink.set(TAG("anchor"), "_TocMissing")

    linked = _rewrite(linked, add_broken_link)
    corpus, baseline = build_corpus(tmp_path, [linked])
    data = json.loads(baseline.read_text(encoding="utf-8"))
    data["samples"].append({"sample_id": "SYN999", "subject": "test", "name": "absent.docx",
                            "source_path": "sources/absent.docx", "source_sha256": "0" * 64})
    baseline.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    result = scan(corpus, baseline, tmp_path / "absent-manifests")
    assert result["registry_error"]
    assert result["total_samples"] == 2 and result["fallback"] == 1 and result["other_outcomes"] == 1
    assert result["records"][0]["diagnostics"]["hyperlink_anchors_unresolved"] == 1
    assert result["renderer_projection_blocked_samples"] == ["SYN001"]
    assert result["records"][1]["production_gate"]["status"] == "MISSING_SOURCE"


def test_scan_does_not_mutate_the_corpus(tmp_path):
    plain = source_bytes()
    corpus, baseline = build_corpus(tmp_path, [plain])
    write_manifests(tmp_path / "manifests", [manifest_for(plain)])
    before = {path.name: sha256(path.read_bytes()).hexdigest()
              for path in (corpus / "sources").rglob("*")}
    scan(corpus, baseline, tmp_path / "manifests")
    after = {path.name: sha256(path.read_bytes()).hexdigest()
             for path in (corpus / "sources").rglob("*")}
    assert before == after


def test_boundary_verdict_uses_the_real_production_validator():
    plain = source_bytes()
    assert boundary_verdict(_root(plain), _parts(plain))["verdict"] == "NO_BOUNDARY_SYSTEM_BLOCKER"
    boxed = _rewrite(plain, lambda body: etree.SubElement(body[0], TAG("txbxContent")))
    verdict = boundary_verdict(_root(boxed), _parts(boxed))
    assert verdict["verdict"] == "STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED"
    assert verdict["detail"] == "unsupported boundary system: txbxContent"


def test_generated_report_states_method_and_scope(tmp_path):
    plain = source_bytes()
    corpus, baseline = build_corpus(tmp_path, [plain])
    write_manifests(tmp_path / "manifests", [manifest_for(plain)])
    report = render_report(scan(corpus, baseline, tmp_path / "manifests"))
    for required in ("Production gate (authoritative)", "Boundary verdict (diagnostic)",
                     "## Production gate reason distribution", "## Scope statement",
                     "fixtures/c3-r10-capability-scan.json"):
        assert required in report
    assert "| total samples | 1 |" in report

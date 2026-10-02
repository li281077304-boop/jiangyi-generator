"""Production reviewed-evidence registry and teacher-only routing.

The real approved X008 source and its approved artifact are used where present;
those cases skip when the externally reviewed artifacts are not mounted. No COM
is invoked: the V0.9 runtime is substituted, never started.
"""
from hashlib import sha256
from pathlib import Path
import copy
import json
import sys

import pytest

from test_batch_job_service import client, docx, renderer, post, service  # noqa: F401
import app as app_module

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from reviewed_studentizer import (CONTRACT, DEFAULT_MANIFEST_DIR,  # noqa: E402
                                 ReviewedManifestError, ReviewedRegistry, registry)
from studentizer import prepare_student  # noqa: E402
from studentizer_planner import prepare_complete_student  # noqa: E402

PACKET = ROOT / "docs/v2/integration/fixtures/c3-r5-source-candidates/X008-source-candidate.json"
APPROVAL = ROOT / "docs/v2/integration/C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md"
X008_SOURCE_SHA = "56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4"
X008_GOLDEN_ROOT = "6b93cfc1594afc35bfa7801a4a73768185058fb2101e41e9f3d363173f31e0a2"
X008_GOLDEN_DOCX = "67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9"


def approved_source() -> Path:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    path = Path(packet["source_path"])
    if not path.is_file():
        pytest.skip("approved X008 source is not mounted")
    if sha256(path.read_bytes()).hexdigest() != X008_SOURCE_SHA:
        pytest.skip("mounted X008 source no longer matches the approved digest")
    return path


def approved_artifact() -> Path:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    path = Path(packet["candidate_docx_path"])
    if not path.is_file():
        pytest.skip("approved X008 expected artifact is not mounted")
    return path


def test_packaged_reviewed_evidence_binds_the_approved_x008_golden(tmp_path):
    loaded = ReviewedRegistry(DEFAULT_MANIFEST_DIR)
    manifest = loaded.lookup(X008_SOURCE_SHA)
    assert manifest is not None and manifest.sample_id == "X008"
    assert manifest.expected_document_sha256 == X008_GOLDEN_ROOT
    assert manifest.reviewed_ranges == 34 and manifest.removed_blocks == 118
    assert manifest.retained_blocks == 146 and len(manifest.body) == 264
    assert manifest.inherited_missing_bookmark_targets == (
        "_Toc21406", "_Toc22623", "_Toc29290", "_Toc3947", "_Toc67", "_Toc9")
    described = manifest.describe()
    assert described["coverage_basis"] == "EXACT_REVIEWED_GOLDEN_PHYSICAL_RANGE"
    assert described["contract"] == CONTRACT and len(described["manifest_sha256"]) == 64
    source = approved_source()
    before = source.read_bytes()
    output = tmp_path / "registry-verification-student.docx"
    result = prepare_student(source, manifest.semantics(), output)
    assert result.status == "XML_PREPARED", (result.reason_code, result.reason_detail)
    assert result.output_sha256 == X008_GOLDEN_DOCX
    assert len(result.mutations) == 118
    assert source.read_bytes() == before


def test_registry_provider_answers_only_for_the_exact_source_digest():
    loaded = ReviewedRegistry(DEFAULT_MANIFEST_DIR)
    provider = loaded.evidence_provider()
    source = approved_source()
    data = source.read_bytes()
    evidence = provider(None, data)
    assert evidence is not None and evidence.source_sha256 == X008_SOURCE_SHA
    assert provider(None, data + b" ") is None
    assert provider(None, b"not a docx") is None


def base_manifest():
    return {
        "manifest_version": 1, "contract": CONTRACT, "sample_id": "SYNTH", "subject": "test",
        "review_id": "synthetic-review",
        "source_sha256": "a" * 64, "expected_document_sha256": "b" * 64,
        "inherited_missing_bookmark_targets": [],
        "approval_document": "synthetic",
        "removed_blocks": 1, "retained_blocks": 1, "reviewed_ranges": 1,
        "body": [{"index": 0, "sha256": "c" * 64, "decision": "RETAIN", "reason": "prompt",
                  "owner_id": "q1"},
                 {"index": 1, "sha256": "d" * 64, "decision": "REMOVE", "reason": "answer",
                  "owner_id": "q1"}],
        "ranges": [{"owner_id": "q1", "prompt_start": 0, "prompt_end": 0,
                    "answer_start": 1, "answer_end": 1, "reason": "reviewed"}],
    }


def write_manifest(directory: Path, manifest: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SYNTH.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def mutate(fn):
    manifest = copy.deepcopy(base_manifest())
    fn(manifest)
    return manifest


@pytest.mark.parametrize("bad", [
    lambda m: m.update(contract="ROLE_INFERENCE"),
    lambda m: m.update(manifest_version=99),
    lambda m: m.update(review_id=""),
    lambda m: m.update(source_sha256="not-a-digest"),
    lambda m: m.update(expected_document_sha256=""),
    lambda m: m.update(body=m["body"][:-1]),
    lambda m: m.update(body=[{"index": 0, "sha256": "c" * 64, "decision": "MAYBE",
                              "reason": "unsure", "owner_id": "q1"}, m["body"][1]]),
    lambda m: m.update(body=[m["body"][0], dict(m["body"][1], reason="  ")]),
    lambda m: m.update(body=[m["body"][0], dict(m["body"][1], sha256="short")]),
    lambda m: m.update(inherited_missing_bookmark_targets=["_Toc1", "_Toc1"]),
    lambda m: m.update(ranges=[]),
    lambda m: m.update(ranges=[{"owner_id": "", "prompt_start": 0, "prompt_end": 0,
                                "answer_start": 1, "answer_end": 1, "reason": "x"}]),
    lambda m: m.update(ranges=[{"owner_id": "q1", "prompt_start": "0", "prompt_end": 0,
                                "answer_start": 1, "answer_end": 1, "reason": "x"}]),
    lambda m: m.update(removed_blocks=7),
])
def test_manifest_loader_refuses_incomplete_or_tampered_evidence(tmp_path, bad):
    write_manifest(tmp_path, mutate(bad))
    with pytest.raises(ReviewedManifestError):
        ReviewedRegistry(tmp_path)


def test_manifest_loader_accepts_a_complete_ledger(tmp_path):
    write_manifest(tmp_path, base_manifest())
    loaded = ReviewedRegistry(tmp_path)
    manifest = loaded.lookup("a" * 64)
    assert manifest is not None and manifest.sample_id == "SYNTH"
    assert loaded.lookup("e" * 64) is None


def test_duplicate_reviewed_evidence_for_one_source_is_refused(tmp_path):
    write_manifest(tmp_path, base_manifest())
    (tmp_path / "COPY.json").write_text(json.dumps(base_manifest(), indent=2), encoding="utf-8")
    with pytest.raises(ReviewedManifestError):
        ReviewedRegistry(tmp_path)


def test_missing_evidence_directory_is_refused(tmp_path):
    with pytest.raises(ReviewedManifestError):
        ReviewedRegistry(tmp_path / "absent")


def test_unloadable_registry_falls_back_and_reports_the_reason(client, renderer, tmp_path):  # noqa: F811
    write_manifest(tmp_path, mutate(lambda m: m.update(contract="ROLE_INFERENCE")))
    app_module.app.config["STUDENTIZER_REVIEWED_MANIFEST_DIR"] = str(tmp_path)
    try:
        final = post(client, [("专题 教师版.docx", docx("知识点"))])
        assert final["status"] == "done", final.get("error")
        preparation = final["student_preparation"]
        assert preparation["status"] == "STUDENTIZER_FALLBACK_REQUIRED"
        assert preparation["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
        assert preparation["registry_error"]
        assert preparation["reviewed_evidence"] is None
        assert final["renderer"] == "XML" and final["fallback_reason"] is None
        assert preparation["student_preparation"] == "V09_MAKE_STUDENT"
        assert preparation["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
    finally:
        app_module.app.config["STUDENTIZER_REVIEWED_MANIFEST_DIR"] = None


def test_production_teacher_only_supported_path_never_calls_make_student(client, renderer):  # noqa: F811
    data = approved_source().read_bytes()
    final = post(client, [("专题 教师版.docx", data)])
    assert final["status"] == "done", final.get("error")
    preparation = final["student_preparation"]
    assert preparation["status"] == "XML_PREPARED"
    assert preparation["engine"] == "XML" and preparation["package_valid"]
    assert preparation["reason_code"] is None and preparation["registry_error"] is None
    assert preparation["studentizer_fallback"] is False
    evidence = preparation["reviewed_evidence"]
    assert evidence["sample_id"] == "X008" and evidence["reviewed_ranges"] == 34
    assert evidence["removed_blocks"] == 118
    assert preparation["coverage"]["coverage_basis"] == "EXACT_REVIEWED_GOLDEN_PHYSICAL_RANGE"
    assert preparation["make_student_called"] is False
    assert preparation["wps_com_started"] is False
    assert final["renderer"] == "XML" and final["produced"] == 2
    assert not renderer["make_student"] and not renderer["fallback"]
    assert len(renderer["xml"]) == 2
    assert renderer["xml"][1] != data  # the student source is the derived one


def test_unreviewed_source_uses_v09_student_preparation_then_xml_renderer(client, renderer):  # noqa: F811
    final = post(client, [("专题 教师版.docx", docx("知识点：加法", "1．求 2+3？", "【答案】5"))])
    assert final["status"] == "done", final.get("error")
    preparation = final["student_preparation"]
    assert preparation["status"] == "STUDENTIZER_FALLBACK_REQUIRED"
    assert preparation["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
    assert preparation["reviewed_evidence"] is None
    assert final["renderer"] == "XML" and final["produced"] == 2
    assert preparation["student_preparation"] == "V09_MAKE_STUDENT"
    assert preparation["student_preparation_route"] == "V09_MAKE_STUDENT"
    assert preparation["make_student_called"]
    assert preparation["wps_com_started"] is None
    assert preparation["com_used"] is None
    assert preparation["com_observation"] == "UNKNOWN_AFTER_MAKE_STUDENT_ENTRY"
    assert len(renderer["make_student"]) == 1
    assert not renderer["fallback"] and len(renderer["xml"]) == 2


def test_v09_engine_loader_failure_records_selected_route_without_claiming_call_or_com(
        client, renderer, monkeypatch):  # noqa: F811
    import renderer_orchestrator

    def fail_loader():
        raise ImportError("fixture engine loader failure")

    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine", fail_loader)
    final = post(client, [("专题 教师版.docx", docx("知识点"))])
    assert final["status"] == "error"
    preparation = final["student_preparation"]
    assert preparation["student_preparation_route"] == "V09_MAKE_STUDENT"
    assert preparation["make_student_called"] is False
    assert preparation["com_used"] is False and preparation["wps_com_started"] is False
    assert preparation["com_observation"] == "NOT_ENTERED"
    assert preparation["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
    assert preparation["preparation_error_code"] == "V09_MAKE_STUDENT_FAILED"
    assert "fixture engine loader failure" in preparation["preparation_error_detail"]
    assert preparation["make_student_elapsed_seconds"] >= 0


def test_v09_make_student_entry_failure_marks_call_but_not_observed_com(
        client, renderer, monkeypatch):  # noqa: F811
    from types import SimpleNamespace
    import renderer_orchestrator

    def fail_before_com(*_args, **_kwargs):
        raise ValueError("fixture strip_red failed before COM")

    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine",
                        lambda: SimpleNamespace(make_student=fail_before_com))
    final = post(client, [("专题 教师版.docx", docx("知识点"))])
    assert final["status"] == "error"
    preparation = final["student_preparation"]
    assert preparation["student_preparation_route"] == "V09_MAKE_STUDENT"
    assert preparation["make_student_called"] is True, repr(preparation)
    assert preparation["com_used"] is None and preparation["wps_com_started"] is None
    assert preparation["com_observation"] == "UNKNOWN_AFTER_MAKE_STUDENT_ENTRY"
    assert preparation["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
    assert preparation["preparation_error_code"] == "V09_MAKE_STUDENT_FAILED"
    assert "fixture strip_red failed before COM" in preparation["preparation_error_detail"]
    assert preparation["make_student_elapsed_seconds"] >= 0


def test_renderer_failure_after_v09_student_preparation_uses_whole_job_fallback(
        client, renderer, monkeypatch):
    import template_slot_composer

    def fail_render(*_args):
        raise RuntimeError("renderer fixture refusal")

    monkeypatch.setattr(template_slot_composer, "render_slots", fail_render)
    final = post(client, [("专题 教师版.docx", docx("知识点"))])
    assert final["status"] == "done" and final["renderer"] == "V0.9"
    assert final["fallback_reason"] == "XML_RENDER_FAILED"
    prep = final["student_preparation"]
    assert prep["student_preparation"] == "V09_MAKE_STUDENT"
    assert prep["reason_code"] == "STUDENTIZER_COVERAGE_UNPROVEN"
    assert prep["com_used"] is None
    assert prep["wps_com_started"] is None
    assert len(renderer["fallback"]) == 1 and len(final["output_paths"]) == 2


def test_real_renderer_refusal_persists_exact_reason_and_uses_original_teacher(
        client, monkeypatch):
    """The only approved source has an inherited unresolvable TOC anchor.

    The frozen renderer must refuse it, and the whole-job fallback must receive
    the original teacher source rather than the prepared derivative.
    """
    from types import SimpleNamespace
    import renderer_orchestrator
    data = approved_source().read_bytes()
    seen = []
    com_entries = []

    def make_student(*args, **kwargs):
        com_entries.append(args)
        raise AssertionError("substituted fallback must not enter the COM-capable path")

    def fallback(job, reason):
        seen.append((job, reason, Path(job.source_doc).read_bytes()))
        assert job.student_source_doc is None
        outputs = [job.output_doc]
        Path(job.output_doc).write_bytes(Path(job.source_doc).read_bytes())
        student = Path(job.student_output_doc)
        student.write_bytes(Path(job.source_doc).read_bytes())
        outputs.append(str(student))
        return {"output_paths": outputs, "whole_job": True,
                "baseline_sha": renderer_orchestrator.V09_BASELINE_SHA}

    monkeypatch.setattr(renderer_orchestrator, "render_v09_whole_job", fallback)
    monkeypatch.setattr(renderer_orchestrator, "_load_v09_engine",
                        lambda: SimpleNamespace(make_student=make_student))
    final = post(client, [("专题 教师版.docx", data)])
    assert final["status"] == "done", final.get("error")
    preparation = final["student_preparation"]
    assert preparation["status"] == "XML_PREPARED"
    assert preparation["reviewed_evidence"]["sample_id"] == "X008"
    assert final["renderer"] == "V0.9"
    assert final["fallback_reason"] == "UNSUPPORTED_BOOKMARK_SCOPE"
    detail = final["fallback_detail"] or ""
    assert "selected hyperlink anchor is missing or ambiguous" in detail
    assert "_Toc9" in detail
    assert seen and seen[0][0].student_source_doc is None
    assert seen[0][2] == data
    assert not com_entries
    assert preparation["make_student_called"] is False
    assert final["produced"] == 2


def test_registry_cache_is_shared_and_resettable():
    first = registry()
    assert registry() is first
    assert first.lookup(X008_SOURCE_SHA) is not None

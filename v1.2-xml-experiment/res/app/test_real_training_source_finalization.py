"""Fixed real-source regressions for the V1.2 finalization work."""
from pathlib import Path
import sys
import zipfile

import pytest

APP = Path(__file__).resolve().parent
REPO = APP.parents[2]
sys.path.insert(0, str(APP))

from lesson_metadata import read_lesson_source_lines, resolve_lesson_metadata
from semantic_facade import analyze_source
from slot_router import (SlotRoutingError, classify_knowledge_point_status,
                         build_slot_routing_plan)
from topic_normalization import normalize_display_topic


FIXTURE = REPO / "docs" / "v2" / "integration" / "fixtures" / "linear-function-12.4"


def _source(role):
    matches = list(FIXTURE.glob("*%s版*.docx" % role))
    assert len(matches) == 1
    return matches[0]


def test_real_source_numbered_table_metadata_is_source_owned_not_offline_generated():
    source = _source("原卷")
    snapshot = analyze_source(source)
    metadata = resolve_lesson_metadata(
        source, subject="数学", topic="专题12.4 一次函数的实际应用",
        knowledge_point_status=classify_knowledge_point_status(snapshot),
        source_lines=read_lesson_source_lines(source),
    )

    assert metadata.objectives_source == "SOURCE"
    assert metadata.difficulties_source == "SOURCE"
    assert "V09_OFFLINE_RULE" not in metadata.source
    assert "实际情境" in metadata.objectives
    assert "重点" in metadata.difficulties
    assert "难点" in metadata.difficulties


def test_real_source_display_topic_removes_marketing_and_edition_tail():
    assert normalize_display_topic(
        "专题12.4 一次函数的实际应用（高效培优讲义）数学新教材沪科版八年级上册 期末复习"
    ) == "专题12.4 一次函数的实际应用"


def test_real_source_knowledge_list_image_evidence_routes_image_to_knowledge():
    source = _source("原卷")
    snapshot = analyze_source(source)
    evidence = {
        "source_sha256": snapshot.source_sha256,
        "images": [{
            "source_node_id": "b6",
            "role": "KNOWLEDGE_ASSET",
            "confidence": "HIGH_CONFIDENCE_CUE",
            "actionable": True,
        }],
    }
    assert classify_knowledge_point_status(snapshot, evidence) == "KNOWLEDGE_POINT_PRESENT"
    plan = build_slot_routing_plan(
        source, "1v1", snapshot=snapshot, image_role_evidence=evidence)

    image_blocks = [record for record in plan.block_records
                    if record["block_id"] == "b6"
                    and snapshot.document.blocks[record["source_index"]].images]
    assert len(image_blocks) == 1
    assert image_blocks[0]["destination_slot"] == "knowledge"


def test_adjacent_cover_metadata_title_image_is_owned_by_cover_not_teaching_slot():
    import hashlib
    import zipfile

    source = _source("原卷")
    snapshot = analyze_source(source)
    evidence = {
        "source_sha256": snapshot.source_sha256,
        "images": [{
            "source_node_id": "b3",
            "role": "TEACHING_METADATA",
            "confidence": "HIGH_CONFIDENCE_CUE",
            "actionable": False,
        }],
    }

    plan = build_slot_routing_plan(
        source, "1v1", snapshot=snapshot, image_role_evidence=evidence)
    routes = {record["block_id"]: record["destination_slot"]
              for record in plan.block_records}

    assert plan.cover_metadata_blocks == ("b3", "b4")
    assert routes["b3"] is None
    assert routes["b4"] is None
    assert routes["b6"] == "knowledge"

    from template_slot_composer import render_slots
    image_target = snapshot.document.blocks[3].images[0].target
    with zipfile.ZipFile(source) as source_package:
        image_sha = hashlib.sha256(source_package.read(image_target)).hexdigest()
    output = source.parent / "test-cover-image-projection.docx"
    try:
        render_slots(
            str(source), plan, str(output),
            cover_metadata={
                "subject": "数学",
                "topic": "专题12.4 一次函数的实际应用",
                "objectives": "掌握一次函数实际应用",
                "difficulties": "重点：建模；难点：求解",
            },
        )
        with zipfile.ZipFile(output) as package:
            output_image_hashes = {
                hashlib.sha256(package.read(name)).hexdigest()
                for name in package.namelist()
                if name.startswith("word/media/")
            }
        assert image_sha in output_image_hashes
    finally:
        output.unlink(missing_ok=True)


def test_confirmed_knowledge_image_conflicting_with_training_heading_fails_closed():
    source = _source("原卷")
    snapshot = analyze_source(source)
    evidence = {
        "source_sha256": snapshot.source_sha256,
        "images": [{
            "source_node_id": "b17",
            "role": "KNOWLEDGE_ASSET",
            "confidence": "HIGH_CONFIDENCE_CUE",
            "actionable": True,
        }],
    }

    try:
        build_slot_routing_plan(
            source, "1v1", snapshot=snapshot, image_role_evidence=evidence)
    except SlotRoutingError as error:
        assert error.reason_code == "IMAGE_ROLE_SECTION_CONFLICT"
    else:
        raise AssertionError("knowledge image inside immediate-training content was routed silently")


def test_real_source_embedded_image_ocr_evidence_is_bound_without_replacing_image(tmp_path):
    import hashlib
    import zipfile

    from image_role_evidence import LocalOCRRecognizer, inspect_document_images, MODEL_FILES

    source = _source("原卷")
    snapshot = analyze_source(source)
    models = tmp_path / "models"
    models.mkdir()
    for name in MODEL_FILES:
        (models / name).write_bytes(name.encode("ascii"))
    expected = "667f9bd7088a49d3f93010698b23bcb91606cf6b25f136b854b5b1e957ba2a17"

    def factory(_paths):
        def engine(image_bytes):
            text = "知识清单" if hashlib.sha256(image_bytes).hexdigest() == expected else ""
            detections = ([[[0, 0, 1, 1], text, 0.99]] if text else [])
            return detections, 0.01
        return engine

    before_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    report = inspect_document_images(
        source, snapshot, LocalOCRRecognizer(models, engine_factory=factory))
    row = next(image for image in report["images"] if image["source_node_id"] == "b6")

    assert row["role"] == "KNOWLEDGE_ASSET"
    assert row["actionable"] is True
    assert row["image_sha256"] == expected
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_sha
    assert snapshot.document.blocks[6].images[0].target == "word/media/image6.png"


def test_conflicting_ocr_role_cues_fail_closed_before_slot_routing():
    import hashlib

    from image_role_evidence import OCRLine, classify_image_role

    source = _source("原卷")
    snapshot = analyze_source(source)
    image = snapshot.document.blocks[6].images[0]
    with zipfile.ZipFile(source) as package:
        image_bytes = package.read(image.target)
    classification = classify_image_role(
        image_sha256=hashlib.sha256(image_bytes).hexdigest(),
        source_node_id="b6",
        lines=(
            OCRLine("知识清单", 0.99),
            OCRLine("题型训练", 0.99),
        ),
    )
    assert classification.role == "AMBIGUOUS"
    evidence = {
        "source_sha256": snapshot.source_sha256,
        "images": [{
            "source_node_id": classification.source_node_id,
            "image_sha256": classification.image_sha256,
            "role": classification.role,
            "confidence": classification.confidence,
            "actionable": classification.actionable,
        }],
    }

    with pytest.raises(SlotRoutingError) as error:
        build_slot_routing_plan(
            source, "1v1", snapshot=snapshot, image_role_evidence=evidence)
    assert error.value.reason_code == "IMAGE_ROLE_AMBIGUOUS"

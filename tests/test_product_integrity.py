from pathlib import Path
import sys

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from product_integrity import (  # noqa: E402
    inspect_input_provenance,
    inspect_product_docx,
    validate_product_integrity,
)


TITLE = "学科教师辅导讲义"
SECTIONS = ("课堂启动", "知识回顾", "知识精讲", "即时训练", "归纳总结", "巩固练习")


def make_docx(path: Path, paragraphs: list[str]) -> Path:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(path)
    return path


def template_cycle(prefix: str) -> list[str]:
    return [TITLE, *[prefix + heading for heading in SECTIONS]]


def test_input_provenance_rejects_recursive_generated_output(tmp_path):
    source = make_docx(tmp_path / "generated.docx", template_cycle("七年级数学 ") * 2)
    result = inspect_input_provenance(source)
    assert result["accepted"] is False
    assert result["errors"] == ["POSSIBLE_GENERATED_OUTPUT_REINGESTION"]
    assert result["sha256"]
    assert result["metrics"]["template_cycles"] == 2


def test_single_template_source_is_not_rejected_as_recursive(tmp_path):
    source = make_docx(tmp_path / "original.docx", template_cycle("高一数学 "))
    result = inspect_input_provenance(source)
    assert result["accepted"] is True
    assert result["metrics"]["template_cycles"] == 1


def test_product_gate_rejects_second_template_and_repeated_long_sequence(tmp_path):
    source = make_docx(tmp_path / "source.docx", ["原始知识点"])
    repeated = ["重复内容块 %02d %s" % (i, "数学题干" * 30) for i in range(12)]
    output = make_docx(tmp_path / "output.docx", template_cycle("数学 ") * 2 + repeated * 2)
    report = validate_product_integrity(source, output)
    codes = {item["reason_code"] for item in report["errors"]}
    assert report["accepted"] is False
    assert "PRODUCT_TEMPLATE_RECURSION" in codes
    assert "PRODUCT_REPEATED_BLOCK_SEQUENCE" in codes
    assert report["output"]["main_story_paragraphs"] > 0
    assert report["output"]["text_chars"] > report["source"]["text_chars"]


def test_expansion_is_reported_and_slot_overlap_fails_closed(tmp_path):
    source = make_docx(tmp_path / "source.docx", ["短源文"])
    output = make_docx(tmp_path / "output.docx", ["扩展正文" * 100])
    plan = type("Plan", (), {"slots": {
        "knowledge": (type("Span", (), {"start": "b1", "end": "b2"})(),),
        "final": (type("Span", (), {"start": "b2", "end": "b2"})(),),
    }})()
    report = validate_product_integrity(source, output, plan=plan)
    codes = {item["reason_code"] for item in report["errors"]}
    assert report["accepted"] is False
    assert "PRODUCT_SLOT_OVERLAP" in codes
    assert report["warnings"][0]["reason_code"] == "PRODUCT_EXPANSION_SUSPECTED"

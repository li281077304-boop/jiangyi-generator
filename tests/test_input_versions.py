import io
from pathlib import Path
import sys

import pytest
from docx import Document

APP_DIR = Path(__file__).resolve().parents[1] / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP_DIR))

from input_versions import UnknownInputVersion, classify_inputs


def make_docx(*paragraphs):
    buf = io.BytesIO()
    doc = Document()
    for value in paragraphs:
        doc.add_paragraph(value)
    doc.save(buf)
    return buf.getvalue()


def test_single_teacher_only_uses_explicit_name_or_answer_structure():
    content = make_docx("题目", "【答案】A", "【解析】过程")
    assert classify_inputs([("unit.docx", content)]).input_version == "TEACHER_ONLY"
    assert classify_inputs([("老师答案版.docx", make_docx("题目"))]).input_version == "TEACHER_ONLY"


def test_single_student_only_uses_explicit_name():
    result = classify_inputs([("单元测试学生版.docx", make_docx("题目"))])
    assert result.input_version == "STUDENT_ONLY"
    assert result.student_index == 0 and result.teacher_index is None


def test_paired_sources_preserve_the_supplied_student_file():
    result = classify_inputs([
        ("课时学生版.docx", make_docx("题目")),
        ("课时教师答案版.docx", make_docx("题目", "【答案】A", "【解析】过程")),
    ])
    assert result.input_version == "TEACHER_AND_STUDENT"
    assert result.teacher_index == 1 and result.student_index == 0


def test_generic_pair_uses_answer_structure_but_never_file_size():
    result = classify_inputs([
        ("input.docx", make_docx("题目", "【答案】A", "【解析】过程")),
        ("input.docx", make_docx("题目")),
    ])
    assert result.teacher_index == 0 and result.student_index == 1


def test_pair_identity_must_match_for_explicit_and_content_classified_pairs():
    teacher = make_docx("题目", "【答案】A", "【解析】过程")
    student = make_docx("题目")
    with pytest.raises(UnknownInputVersion):
        classify_inputs([("math teacher.docx", teacher), ("chem student.docx", student)])
    with pytest.raises(UnknownInputVersion):
        classify_inputs([("math.docx", teacher), ("chem.docx", student)])


def test_ambiguous_versions_and_separate_mode_fail_closed():
    with pytest.raises(UnknownInputVersion) as raised:
        classify_inputs([("课件.docx", make_docx("题目"))])
    assert raised.value.code == "UNKNOWN_INPUT_VERSION"
    with pytest.raises(UnknownInputVersion):
        classify_inputs([("a教师版.docx", make_docx("x")),
                         ("b学生版.docx", make_docx("y"))], "separate")

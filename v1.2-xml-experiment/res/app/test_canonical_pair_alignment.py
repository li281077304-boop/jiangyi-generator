from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
import zipfile
import xml.etree.ElementTree as ET
import pytest

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))

from canonical_pair_alignment import (PairAlignmentError, align_teacher_student,
                                     project_pair_routes, _match_stems,
                                     _resource_identities_match,
                                     _subquestion_text_match,
                                     _augment_with_unique_raw_matches,
                                     _block_projection_signature,
                                     _fingerprint,
                                     _complete_occurrence_tail_match,
                                     _omml_is_between_ideographic_delimiters,
                                     _raw_subquestion_text_with_underlined_blanks,
                                     _grouped_subquestion_spans,
                                     _question_groups,
                                     _require_matching_subquestion_sets,
                                     QuestionOccurrence)  # noqa: E402
from semantic_facade import analyze_source  # noqa: E402
from slot_router import build_slot_routing_plan  # noqa: E402


FIXTURE = (APP.parents[2] / "docs" / "v2" / "integration" / "fixtures" /
           "incident-72cab43961d6488c91b7a9e049265263")


@pytest.mark.parametrize("template_type", ["1v1", "class"])
def test_incident_pair_aligns_using_raw_student_question_missed_by_a_line(template_type):
    student_path = next(FIXTURE.glob("*原卷版*.docx"))
    teacher_path = next(FIXTURE.glob("*解析版*.docx"))
    student = analyze_source(student_path)
    teacher = analyze_source(teacher_path)

    result = align_teacher_student(student, teacher,
                                   student_source_path=student_path,
                                   teacher_source_path=teacher_path)

    assert result["status"] == "ALIGNED"
    assert result["student_occurrence_count"] == 60
    assert result["teacher_occurrence_count"] == 60
    assert result["unmatched_real_question_count"] == 0
    assert result["ambiguous_real_question_count"] == 0
    question_35 = result["occurrences"][34]
    assert question_35["question_number"] == 35
    assert question_35["student_node"] == "b198"
    assert question_35["student_origin"] == "RAW_NUMBERED_PARAGRAPH"
    assert question_35["teacher_node"] == "b444"
    question_6 = result["occurrences"][5]
    assert question_6["fingerprint_match"] == "ANSWER_FILLED_EXPLICIT_STUDENT_BLANKS"
    assert question_6["teacher_moved_supplement"] == {
        "text": "[已知水的比热容为4.2×103J/(kg•°C)]",
        "teacher_node": "b82",
        "relation": "EXACT_BRACKETED_TEXT_MOVED_TO_ADJACENT_PARAGRAPH",
    }
    question_35 = result["occurrences"][34]
    assert question_35["student_raw_range"] == {
        "start": "b198", "end": "b208",
        "boundary": "ANSWER_OR_SECTION_OR_NEXT_CANONICAL_QUESTION",
        "block_count": 11, "resource_blocks": ["b199"],
    }
    question_38 = next(item for item in result["occurrences"]
                       if item["question_number"] == 38)
    assert question_38["fingerprint_match"] == "EXACT_WITH_PROVEN_MULTIPLE_CHOICE_BLANK"
    question_48 = next(item for item in result["occurrences"]
                       if item["question_number"] == 48)
    subquestion_48_3 = next(item for item in question_48["teacher_subquestion_matches"]
                            if item["label"] == "(3)")
    assert subquestion_48_3["student_nodes"] == ["b295", "b296"]
    assert subquestion_48_3["teacher_nodes"] == ["b707", "b708"]
    assert subquestion_48_3["resource_relation"] == \
        "SIDE_LOCAL_IMAGE_SLOTS_EXACT_TABLE_OMML_OLE_WHEN_PRESENT"
    question_49 = next(item for item in result["occurrences"]
                       if item["question_number"] == 49)
    subquestion_49_3 = next(item for item in question_49["teacher_subquestion_matches"]
                            if item["label"] == "(3)")
    assert subquestion_49_3["relation"] == "TEACHER_VALUE_IN_EXPLICIT_IDEOGRAPHIC_GAP"

    base = build_slot_routing_plan(student_path, template_type, snapshot=student)
    base_block_routes = {int(item["block_id"][1:]): (
                             "cover" if item["destination_slot"] is None else item["destination_slot"])
                         for item in base.block_records}
    student_cover_nodes = {int(node[1:]) for node in base.cover_metadata_blocks}
    projection = project_pair_routes(student, teacher, result, base_block_routes,
                                     student_cover_nodes=student_cover_nodes)
    assert projection["status"] == "PROJECTED"
    assert projection["source_block_counts"] == {"student": 356, "teacher": 860}
    question_27 = next(item for item in projection["occurrences"]
                       if item["question_number"] == 27)
    assert question_27["teacher_only_option_extension"] == {
        "nodes": ["b319", "b320"],
        "labels": ["A", "B", "C", "D"],
        "relation": "COMPLETE_AD_OPTIONS_BETWEEN_CHOICE_STEM_AND_OWNED_ANSWER",
    }
    assert question_27["destination_slot"] == projection["student_block_routes"]["149"]
    assert projection["teacher_block_routes"]["319"] == question_27["destination_slot"]
    assert projection["teacher_block_routes"]["320"] == question_27["destination_slot"]
    for role, source_path, snapshot, key in (
            ("student", student_path, student, "student_block_routes"),
            ("teacher", teacher_path, teacher, "teacher_block_routes")):
        projected_routes = {int(seq): slot for seq, slot in projection[key].items()}
        canonical_plan = build_slot_routing_plan(
            source_path, template_type, snapshot=snapshot,
            canonical_projection_routes=projected_routes)
        plan_routes = {int(item["block_id"][1:]): item["destination_slot"]
                       for item in canonical_plan.block_records}
        assert plan_routes == projected_routes, role
    assert {item["destination_slot"] for item in projection["occurrences"]} <= {
        "knowledge", "immediate", "final"
    }
    assert all(item["destination_slot"] == projection["student_block_routes"][
        item["student_node"][1:]] for item in projection["occurrences"])


def test_filled_blank_requires_explicit_answer_structure_and_exact_context():
    student = "题干的结果为　  　 V；功率为　  　 W。"
    teacher = "题干的结果为　4.5　 V；功率为　20　 W。"
    assert _match_stems(student, teacher, answer_structure_proven=True) == \
        "ANSWER_FILLED_EXPLICIT_STUDENT_BLANKS"
    assert _match_stems(student, teacher, answer_structure_proven=False) is None
    assert _match_stems("题干[不相同的旧注]", "题干", answer_structure_proven=True) is None


def test_teacher_filled_gap_requires_explicit_student_blank_evidence():
    assert _subquestion_text_match(
        "实际功率为W；",
        "实际功率为　0.05　 W；",
        answer_structure_proven=True,
    ) is None
    assert _subquestion_text_match(
        "实际功率为　  　W；",
        "实际功率为　0.05　W；",
        answer_structure_proven=True,
    ) == "ANSWER_FILLED_EXPLICIT_SUBQUESTION_BLANKS"
    assert _subquestion_text_match(
        "实际功率为W；",
        "实际功率为　0.05　 W并改了题干；",
        answer_structure_proven=True,
    ) is None


def test_question_body_signature_includes_omml_presence():
    base = SimpleNamespace(text="公式见下", kind="paragraph", images=(), math_count=1,
                           table=None, oles=(), textbox_texts=())
    changed = SimpleNamespace(text="公式见下", kind="paragraph", images=(), math_count=2,
                              table=None, oles=(), textbox_texts=())
    assert _block_projection_signature(base) != _block_projection_signature(changed)


def test_cross_document_equal_block_ordinal_is_not_a_duplicate_key():
    blocks = [SimpleNamespace(seq=i, kind="paragraph", text="") for i in range(6)]
    blocks[5].text = "1. unique source question"
    snapshot = SimpleNamespace(document=SimpleNamespace(blocks=blocks))
    number, stem, digest = _fingerprint(blocks[5].text)
    reference = [QuestionOccurrence(number, 5, "b5", "other-document-unit", stem,
                                    digest, "A_LINE_QUESTION_GROUP", ("b5",))]
    additions = _augment_with_unique_raw_matches(snapshot, reference, covered=set())
    assert [item.start_seq for item in additions] == [5]


def test_teacher_extra_explicit_subquestion_is_not_silently_ignored():
    with pytest.raises(PairAlignmentError) as error:
        _require_matching_subquestion_sets(
            {"(1)": {}, "(2)": {}}, {"(1)": {}, "(2)": {}, "(3)": {}},
            "q-test", 33)
    assert error.value.reason_code == "ALIGNMENT_UNRESOLVED"
    assert "subquestion" in error.value.detail


def test_ordinary_continuation_number_change_fails_exact_body_check():
    student_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="continued value=2", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    teacher_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="continued value=20", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    student = QuestionOccurrence(1, 0, "b0", "s", "stem", "s", "test", ("b0", "b1"))
    teacher = QuestionOccurrence(1, 0, "b0", "t", "stem", "t", "test", ("b0", "b1"))
    assert not _complete_occurrence_tail_match(
        student_snapshot, teacher_snapshot, student, teacher, None, None,
        answer_structure_proven=False)


def test_image_resources_align_by_unique_ordered_subquestion_slots():
    # Images are side-local assets owned by an already matched complete
    # subquestion; paired copies may encode or place them differently.
    assert _resource_identities_match(
        ((1, "image_slot", 0),), ((1, "image_slot", 0),))
    assert _resource_identities_match(
        ((1, "image_slot", 0),), ())
    assert not _resource_identities_match(
        ((1, "table", (("A", 1),)),), ((1, "table", (("B", 1),)),))
    assert not _resource_identities_match(
        ((1, "ole", "teacher-hash"),), ((1, "ole", "student-hash"),))
    assert not _resource_identities_match(
        ((1, "omml", "<math>x=2</math>"),),
        ((1, "omml", "<math>x=20</math>"),))


def test_complete_tail_preserves_explicit_student_blank_evidence():
    student_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="结果为　  　W", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    teacher_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="结果为　0.05　W", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    student = QuestionOccurrence(1, 0, "b0", "s", "stem", "s", "test", ("b0", "b1"))
    teacher = QuestionOccurrence(1, 0, "b0", "t", "stem", "t", "test", ("b0", "b1"))
    assert _complete_occurrence_tail_match(
        student_snapshot, teacher_snapshot, student, teacher, None, None,
        answer_structure_proven=True)


def test_teacher_omml_blank_fill_must_be_between_xml_delimiters():
    teacher_path = next(FIXTURE.glob("*解析版*.docx"))
    teacher = analyze_source(teacher_path)
    block = teacher.document.blocks[431]
    assert block.math_count == 1
    assert _omml_is_between_ideographic_delimiters(block, teacher_path)

    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    m = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
    with zipfile.ZipFile(teacher_path, "r") as source_zip:
        members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]
    xml = next(data for info, data in members if info.filename == "word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(w + "body")
    paragraphs = [child for child in body if child.tag == w + "p"]
    paragraph = paragraphs[block.pno - 1]
    formula = next(node for node in paragraph if any(
        child.tag == m + "oMath" for child in node.iter()))
    paragraph.remove(formula)
    insert_at = 1 if paragraph and paragraph[0].tag == w + "pPr" else 0
    paragraph.insert(insert_at, formula)
    changed_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        changed_path = Path(temp_dir) / "formula-outside-blank.docx"
        with zipfile.ZipFile(changed_path, "w", zipfile.ZIP_DEFLATED) as changed_zip:
            for info, data in members:
                changed_zip.writestr(
                    info, changed_xml if info.filename == "word/document.xml" else data)
        assert not _omml_is_between_ideographic_delimiters(block, changed_path)


def test_incident_student_underlined_blank_is_recovered_from_source_xml():
    student_path = next(FIXTURE.glob("*原卷版*.docx"))
    teacher_path = next(FIXTURE.glob("*解析版*.docx"))
    student = analyze_source(student_path)
    teacher = analyze_source(teacher_path)
    student_span = _grouped_subquestion_spans(student, {307, 308})["(3)"]
    teacher_span = _grouped_subquestion_spans(teacher, {733, 734})["(3)"]
    raw_student = _raw_subquestion_text_with_underlined_blanks(
        student, student_span, student_path)
    raw_teacher = _raw_subquestion_text_with_underlined_blanks(
        teacher, teacher_span, teacher_path)
    assert raw_student and raw_student[1]
    assert raw_teacher
    assert _subquestion_text_match(
        raw_student[0][raw_student[0].find("若将"):],
        raw_teacher[0][raw_teacher[0].find("若将"):],
        answer_structure_proven=True) == "ANSWER_FILLED_EXPLICIT_SUBQUESTION_BLANKS"


def test_math_pair_repeated_numbers_align_as_ordered_occurrences():
    fixture = (APP.parents[2] / "docs" / "v2" / "integration" / "fixtures" /
               "linear-function-12.4")
    student_path = next(fixture.glob("*原卷版*.docx"))
    teacher_path = next(fixture.glob("*解析版*.docx"))
    result = align_teacher_student(
        analyze_source(student_path), analyze_source(teacher_path),
        student_source_path=student_path, teacher_source_path=teacher_path)

    assert result["status"] == "ALIGNED"
    assert result["student_occurrence_count"] == 21
    assert result["teacher_occurrence_count"] == 21
    assert result["unmatched_real_question_count"] == 0
    assert result["ambiguous_real_question_count"] == 0
    assert [item["question_number"] for item in result["occurrences"]] == [
        1, 2, 3, *range(1, 11), *range(1, 9)]
    assert len({item["canonical_occurrence_id"] for item in result["occurrences"]}) == 21


def test_explicit_subquestion_mismatch_cannot_be_reported_as_aligned():
    student_path = next(FIXTURE.glob("*原卷版*.docx"))
    teacher_path = next(FIXTURE.glob("*解析版*.docx"))
    student = analyze_source(student_path)
    teacher = analyze_source(teacher_path)

    # In occurrence 13, the second physical subquestion is a real numbered
    # question-body block. Alter only its quantity; the leading stem and
    # outer question label remain unchanged, matching the previously missed
    # corruption case.
    block = student.document.blocks[70]
    assert "40kg" in block.text
    block.text = block.text.replace("40kg", "41kg", 1)

    with pytest.raises(PairAlignmentError) as error:
        align_teacher_student(student, teacher,
                              student_source_path=student_path,
                              teacher_source_path=teacher_path)
    assert error.value.reason_code == "ALIGNMENT_UNRESOLVED"
    occurrence = next(item for item in _question_groups(student)[0]
                      if "b70" in item.source_nodes)
    paired = _question_groups(teacher)[0][_question_groups(student)[0].index(occurrence)]
    assert not _complete_occurrence_tail_match(
        student, teacher, occurrence, paired, student_path, teacher_path,
        answer_structure_proven=False)

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
                                     _occurrence_tail_payload,
                                     _omml_is_between_ideographic_delimiters,
                                     _omml_expression_roots,
                                     _raw_subquestion_text_with_underlined_blanks,
                                     _table_semantic_signature,
                                     _visually_empty_white_image_identity,
                                     _visually_equivalent_rasters,
                                     _grouped_subquestion_spans,
                                     _question_groups,
                                     _require_ordered_residual_projection,
                                     _require_student_residual_consumption,
                                     _require_matching_subquestion_sets,
                                     QuestionOccurrence)  # noqa: E402
from semantic_facade import analyze_source  # noqa: E402
from slot_router import (build_slot_routing_plan,
                         cover_metadata_sequences_with_images)  # noqa: E402


FIXTURE = (APP.parents[2] / "docs" / "v2" / "integration" / "fixtures" /
           "incident-72cab43961d6488c91b7a9e049265263")


def test_omml_paragraph_wrapper_counts_as_one_logical_expression():
    math_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    paragraph = ET.fromstring(
        f'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        f'xmlns:m="{math_ns}">'
        '<w:r><w:t>left</w:t></w:r>'
        '<m:oMathPara><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara>'
        '<m:oMath><m:r><m:t>y</m:t></m:r></m:oMath>'
        '</w:p>')

    roots = _omml_expression_roots(paragraph)

    assert [node.tag.rsplit("}", 1)[-1] for node in roots] == ["oMathPara", "oMath"]
    assert len(roots) == 2


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
    assert subquestion_49_3["relation"] == "ANSWER_FILLED_STUDENT_XML_UNDERLINE_BLANK"
    question_26 = next(item for item in result["occurrences"]
                       if item["question_number"] == 26)
    assert question_26["teacher_only_option_extension"] == {
        "nodes": ["b308", "b309"],
        "labels": ["A", "B", "C", "D"],
        "relation": "COMPLETE_AD_OPTIONS_BETWEEN_CHOICE_STEM_AND_OWNED_ANSWER",
    }
    assert question_26["student_only_option_extension"] == {
        "nodes": ["b147", "b148"],
        "labels": ["A", "B", "C", "D"],
        "relation": "EXACT_ORDERED_TEXT_MATCH_TO_TEACHER_OPTIONS",
    }

    base = build_slot_routing_plan(student_path, template_type, snapshot=student)
    base_block_routes = {int(item["block_id"][1:]): (
                             "cover" if item["destination_slot"] is None else item["destination_slot"])
                         for item in base.block_records}
    student_cover_nodes = {int(node[1:]) for node in base.cover_metadata_blocks}
    projection = project_pair_routes(student, teacher, result, base_block_routes,
                                     student_cover_nodes=student_cover_nodes,
                                     student_source_path=student_path,
                                     teacher_source_path=teacher_path)
    assert projection["status"] == "PROJECTED"
    section_heading = next(item for item in projection["teacher_student_residual_block_map"]
                           if item.get("fingerprint_match") ==
                           "EXACT_CONTEXTUAL_EXERCISE_SECTION_HEADING"
                           and item.get("student_node") == "b60"
                           and item.get("teacher_node") == "b111")
    assert section_heading["destination_slot"] == "knowledge"
    assert projection["student_block_routes"]["60"] == "knowledge"
    assert projection["teacher_block_routes"]["111"] == "knowledge"
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
        if role == "teacher":
            split_units = {item["unit_id"]: item for item in canonical_plan.canonical_unit_splits}
            assert split_units["u035"]["blocks_by_slot"] == {
                "knowledge": ("b48",),
                "immediate": ("b43", "b44", "b45", "b46", "b47"),
            }
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
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    m = "http://schemas.openxmlformats.org/officeDocument/2006/math"

    def signature(formula):
        xml = (f'<w:document xmlns:w="{w}" xmlns:m="{m}"><w:body><w:p>'
               '<w:r><w:t>公式见下</w:t></w:r>'
               f'<m:oMath><m:r><m:t>{formula}</m:t></m:r></m:oMath>'
               '</w:p></w:body></w:document>')
        block = SimpleNamespace(seq=0, pno=1, kind="paragraph", text="公式见下",
                                images=(), math_count=1, table=None, oles=(),
                                textbox_texts=())
        snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[block]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "formula.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", xml)
                package.writestr(
                    "word/_rels/document.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            return _block_projection_signature(snapshot, 0, path)

    assert signature("x=1") != signature("x=2")


def test_exact_residual_signature_rejects_different_image_bytes():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    image = SimpleNamespace(kind="inline", target="word/media/image1.png",
                            cx=100, cy=200)
    block = SimpleNamespace(seq=0, pno=1, kind="paragraph", text="same caption",
                            images=(image,), math_count=0, table=None, oles=(),
                            textbox_texts=())
    snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[block]))

    def signatures(image_bytes, target="word/media/image1.png", *, include_image=True,
                   extent=(100, 200)):
        xml = (f'<w:document xmlns:w="{w}"><w:body>'
               '<w:p><w:r><w:t>same caption</w:t></w:r></w:p>'
               '</w:body></w:document>')
        block.images = (SimpleNamespace(kind="inline", target=target,
                                        cx=extent[0], cy=extent[1]),)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", xml)
                if include_image:
                    package.writestr(target, image_bytes)
            return (
                _block_projection_signature(snapshot, 0, path),
                _block_projection_signature(snapshot, 0, path, exact_images=True),
            )

    default_a, strict_a = signatures(b"image-a")
    default_b, strict_b = signatures(b"image-b")
    assert default_a == default_b  # Question-owned image policy is unchanged.
    assert strict_a != strict_b   # Residual/group identity binds actual media bytes.
    _default_same, strict_same = signatures(
        b"image-a", target="word/media/renamed-image.png")
    assert strict_a == strict_same  # Relationship target names are not image identity.
    _default_scaled, strict_scaled = signatures(b"image-a", extent=(300, 400))
    assert strict_a == strict_scaled  # Side-local display extents are preserved, not identity.
    _default_missing, strict_missing = signatures(
        b"", target="word/media/missing.png", include_image=False)
    assert strict_missing is None


def test_residual_signature_includes_word_symbol_font_and_glyph():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    block = SimpleNamespace(seq=0, pno=1, kind="paragraph", text="symbol",
                            images=(), math_count=0, table=None, oles=(),
                            textbox_texts=())
    snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[block]))

    def signature(char):
        xml = (f'<w:document xmlns:w="{w}"><w:body><w:p><w:r><w:t>symbol</w:t></w:r>'
               f'<w:r><w:sym w:font="Wingdings" w:char="{char}"/></w:r>'
               '</w:p></w:body></w:document>')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbol.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", xml)
            return _block_projection_signature(snapshot, 0, path)

    assert signature("F061") != signature("F062")


def test_only_visually_empty_white_prefix_images_normalize_across_media_bytes():
    from io import BytesIO
    from PIL import Image

    def png(size, color):
        stream = BytesIO()
        Image.new("RGBA", size, color).save(stream, format="PNG")
        return stream.getvalue()

    student_placeholder = png((35, 27), (255, 255, 254, 255))
    teacher_placeholder = png((32, 24), (255, 255, 255, 255))
    content_image = png((32, 24), (230, 230, 230, 255))
    sixteen_bit = BytesIO()
    high_depth = Image.new("I;16", (2, 1))
    high_depth.putdata([256, 32768])
    high_depth.save(sixteen_bit, format="PNG")

    assert student_placeholder != teacher_placeholder
    assert _visually_empty_white_image_identity(student_placeholder) == \
        _visually_empty_white_image_identity(teacher_placeholder)
    assert _visually_empty_white_image_identity(content_image) is None
    assert _visually_empty_white_image_identity(sixteen_bit.getvalue()) is None


def test_pair_projection_rejects_different_prefix_omml_content():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    m = "http://schemas.openxmlformats.org/officeDocument/2006/math"

    def source(formula):
        xml = (f'<w:document xmlns:w="{w}" xmlns:m="{m}"><w:body>'
               '<w:p><w:r><w:t>公式</w:t></w:r>'
               f'<m:oMath><m:r><m:t>{formula}</m:t></m:r></m:oMath></w:p>'
               '<w:p><w:r><w:t>1. question stem</w:t></w:r></w:p>'
               '</w:body></w:document>')
        blocks = [
            SimpleNamespace(seq=0, pno=1, kind="paragraph", text="公式", images=(),
                            math_count=1, table=None, oles=(), textbox_texts=()),
            SimpleNamespace(seq=1, pno=2, kind="paragraph", text="1. question stem",
                            images=(), math_count=0, table=None, oles=(), textbox_texts=()),
        ]
        snapshot = SimpleNamespace(document=SimpleNamespace(blocks=blocks))
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "pair.docx"
        with zipfile.ZipFile(path, "w") as package:
            package.writestr("word/document.xml", xml)
            package.writestr(
                "word/_rels/document.xml.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        return directory, path, snapshot

    student_dir, student_path, student = source("x=1")
    teacher_dir, teacher_path, teacher = source("x=2")
    try:
        occurrence = {
            "canonical_occurrence_id": "q-001",
            "student_node": "b1",
            "student_nodes": ["b1"],
            "teacher_nodes": ["b1"],
            "teacher_annotation_nodes": [],
        }
        alignment = {"status": "ALIGNED", "occurrences": [occurrence]}
        with pytest.raises(PairAlignmentError) as error:
            project_pair_routes(
                student, teacher, alignment, {0: "knowledge", 1: "knowledge"},
                student_source_path=student_path, teacher_source_path=teacher_path)
        assert error.value.reason_code == "ALIGNMENT_UNRESOLVED"
        assert "prefix" in error.value.detail
        # Missing source paths yield unverifiable signatures, never a match.
        with pytest.raises(PairAlignmentError) as unverifiable:
            project_pair_routes(student, teacher, alignment,
                                {0: "knowledge", 1: "knowledge"})
        assert unverifiable.value.reason_code == "ALIGNMENT_UNRESOLVED"
        assert "prefix" in unverifiable.value.detail
    finally:
        student_dir.cleanup()
        teacher_dir.cleanup()


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


def test_explicit_answer_ownership_stops_before_next_teaching_heading():
    from canonical_pair_alignment import (_answer_continuation_boundary,
                                          _clip_annotation_before_teaching_heading)

    snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="【答案】2"),
        SimpleNamespace(text="三、知识精讲"),
        SimpleNamespace(text="欧姆定律知识说明"),
        SimpleNamespace(text="2. 下一题"),
    ]))
    assert _clip_annotation_before_teaching_heading(snapshot, 0, 3) == (0, 0)
    continuation = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. question"),
        SimpleNamespace(text="【答案】2"),
        SimpleNamespace(text="知识精讲"),
        SimpleNamespace(text="欧姆定律知识说明"),
        SimpleNamespace(text="故答案为：定理应用所得结果。"),
    ]))
    assert _answer_continuation_boundary(continuation, 1, 5) == 2


def test_ordinary_continuation_number_change_fails_exact_body_check():
    student_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", pno=1, images=(), math_count=0,
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


def test_table_semantic_signature_compares_cell_grid_and_omml_content():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    m = "http://schemas.openxmlformats.org/officeDocument/2006/math"

    def signature(formula, first_span="1", second_span="1", merge_xml=""):
        xml = (f'<w:document xmlns:w="{w}" xmlns:m="{m}"><w:body>'
               '<w:tbl><w:tblGrid><w:gridCol w:w="100"/><w:gridCol w:w="100"/>'
               '<w:gridCol w:w="100"/></w:tblGrid><w:tr>'
               f'<w:tc><w:tcPr><w:gridSpan w:val="{first_span}"/></w:tcPr>'
               '<w:p><w:r><w:t>结果</w:t></w:r>'
               f'<m:oMath><m:r><m:t>{formula}</m:t></m:r></m:oMath>'
               f'</w:p></w:tc><w:tc><w:tcPr><w:gridSpan w:val="{second_span}"/>{merge_xml}</w:tcPr>'
               '<w:p><w:r><w:t>单位</w:t></w:r></w:p></w:tc>'
               '</w:tr></w:tbl></w:body></w:document>')
        block = SimpleNamespace(table=object(), body_idx=0)
        snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[block]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", xml)
                package.writestr(
                    "word/_rels/document.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            return _table_semantic_signature(snapshot, block, path)

    left = signature("U")
    assert left == signature("U")
    assert left != signature("I")
    assert left[0] == "table-grid-v1"
    # Same text and formula, different logical cell widths must not align.
    assert left != signature("U", "2", "1")
    assert left != signature("U", merge_xml="<w:vMerge/>")
    assert left != signature("U", merge_xml="<w:hMerge/>")
    assert signature("U", merge_xml="<w:hMerge/>") != signature(
        "U", merge_xml='<w:hMerge w:val="restart"/>')


def test_nested_table_signature_preserves_symbols_rejects_wrappers_and_hashes_ole():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    o = "urn:schemas-microsoft-com:office:office"
    v = "urn:schemas-microsoft-com:vml"
    pkg_rel = "http://schemas.openxmlformats.org/package/2006/relationships"

    def signature(cell_content, *, row_wrapper="", rels="", payloads=None):
        table = (f'<w:tbl><w:tblGrid><w:gridCol w:w="100"/></w:tblGrid>{row_wrapper}'
                 f'<w:tr><w:tc><w:tcPr/>{cell_content}</w:tc></w:tr>{"</w:sdtContent></w:sdt>" if row_wrapper else ""}'
                 '</w:tbl>')
        xml = (f'<w:document xmlns:w="{w}" xmlns:r="{r}" xmlns:o="{o}" '
               f'xmlns:v="{v}"><w:body>'
               f'{table}</w:body></w:document>')
        block = SimpleNamespace(table=object(), body_idx=0)
        snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[block]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.docx"
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", xml)
                package.writestr("word/_rels/document.xml.rels",
                                 f'<Relationships xmlns="{pkg_rel}">{rels}</Relationships>')
                for name, content in (payloads or {}).items():
                    package.writestr(name, content)
            return _table_semantic_signature(snapshot, block, path)

    symbol_a = signature('<w:p><w:r><w:sym w:font="Wingdings" w:char="F061"/>'
                         '</w:r></w:p>')
    symbol_b = signature('<w:p><w:r><w:sym w:font="Wingdings" w:char="F062"/>'
                         '</w:r></w:p>')
    assert symbol_a is not None and symbol_a != symbol_b

    wrapped = signature('<w:p><w:r><w:t>content</w:t></w:r></w:p>',
                        row_wrapper='<w:sdt><w:sdtContent>')
    assert wrapped is None

    rel = (f'<Relationship Id="rIdOle" Type="{o}/oleObject" '
           'Target="embeddings/oleObject1.bin"/>')
    ole_xml = ('<w:p><w:object><o:OLEObject r:id="rIdOle"/></w:object></w:p>')
    ole_a = signature(ole_xml, rels=rel,
                      payloads={"word/embeddings/oleObject1.bin": b"ole-a"})
    ole_b = signature(ole_xml, rels=rel,
                      payloads={"word/embeddings/oleObject1.bin": b"ole-b"})
    assert ole_a is not None and ole_a != ole_b

    image_rel = (f'<Relationship Id="rIdImg" Type="{o}/image" '
                 'Target="media/table.png"/>')
    vml_prefix = ('<w:p><w:pict><v:group><v:shape><v:imagedata r:id="rIdImg"/>'
                  '</v:shape><v:shape><v:textbox><w:txbxContent><w:p><w:r><w:t>')
    vml_suffix = ('</w:t></w:r></w:p></w:txbxContent></v:textbox></v:shape>'
                  '</v:group></w:pict></w:p>')
    vml_a = signature(vml_prefix + "voltage 2V" + vml_suffix, rels=image_rel,
                      payloads={"word/media/table.png": b"image"})
    vml_b = signature(vml_prefix + "voltage 200V" + vml_suffix, rels=image_rel,
                      payloads={"word/media/table.png": b"image"})
    assert vml_a is None and vml_b is None


def test_complete_tail_preserves_explicit_student_blank_evidence():
    student_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="结果为　  　W", kind="paragraph", pno=2, images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    teacher_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[
        SimpleNamespace(text="1. stem", kind="paragraph", pno=1, images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
        SimpleNamespace(text="结果为　0.05　W", kind="paragraph", pno=2, images=(), math_count=0,
                        table=None, oles=(), textbox_texts=()),
    ]))
    student = QuestionOccurrence(1, 0, "b0", "s", "stem", "s", "test", ("b0", "b1"))
    teacher = QuestionOccurrence(1, 0, "b0", "t", "stem", "t", "test", ("b0", "b1"))
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "source.docx"
        with zipfile.ZipFile(source, "w") as package:
            package.writestr("word/document.xml",
                             f'<w:document xmlns:w="{w}"><w:body><w:p/><w:p/></w:body></w:document>')
        assert _complete_occurrence_tail_match(
            student_snapshot, teacher_snapshot, student, teacher, source, source,
            answer_structure_proven=True)


def test_occurrence_tail_uses_physical_source_order_after_projection_extensions():
    from docx import Document

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "ordered.docx"
        document = Document()
        document.add_paragraph("1. stem")
        document.add_paragraph("A continuation")
        document.add_paragraph("B continuation")
        document.save(source)
        snapshot = analyze_source(source)
        occurrence = QuestionOccurrence(
            1, 0, "b0", "u0", "1. stem", "stem", "test", ("b0", "b2", "b1"))

        payload = _occurrence_tail_payload(snapshot, occurrence, source)

    assert payload == ("AcontinuationBcontinuation", ())


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


def test_normalized_visual_image_identity_accepts_resolution_variant_only():
    from io import BytesIO
    from PIL import Image, ImageDraw

    source = Image.new("RGB", (64, 56), "white")
    draw = ImageDraw.Draw(source)
    draw.line((5, 49, 5, 5, 58, 5), fill="black", width=2)
    draw.line((10, 42, 24, 29, 36, 34, 53, 12), fill="black", width=2)
    source_bytes = BytesIO()
    source.save(source_bytes, format="PNG")
    high_resolution = source.resize((256, 224), Image.Resampling.LANCZOS)
    high_bytes = BytesIO()
    high_resolution.save(high_bytes, format="PNG")

    different = Image.new("RGB", (256, 224), "white")
    ImageDraw.Draw(different).line((10, 210, 240, 10), fill="black", width=3)
    different_bytes = BytesIO()
    different.save(different_bytes, format="PNG")

    assert _visually_equivalent_rasters(source_bytes.getvalue(), high_bytes.getvalue())
    assert not _visually_equivalent_rasters(source_bytes.getvalue(),
                                            different_bytes.getvalue())


def test_unpaired_student_residual_fails_but_empty_layout_is_recorded():
    substantive = SimpleNamespace(
        kind="paragraph", text="学生侧额外练习内容", images=[], oles=[],
        math_count=0, table=None, textbox_texts=())
    snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[substantive]))
    residuals = {(("q-001", "q-002"), "signature"): [0]}
    residual_map = []

    with pytest.raises(PairAlignmentError) as error:
        _require_student_residual_consumption(
            snapshot, residuals, set(), {0: "immediate"}, residual_map)
    assert error.value.reason_code == "ALIGNMENT_UNRESOLVED"
    assert error.value.evidence["student_node"] == "b0"

    blank = SimpleNamespace(
        kind="paragraph", text="  ", images=[], oles=[], math_count=0,
        table=None, textbox_texts=())
    blank_snapshot = SimpleNamespace(document=SimpleNamespace(blocks=[blank]))
    _require_student_residual_consumption(
        blank_snapshot, residuals, set(), {0: "immediate"}, residual_map)
    assert residual_map == [{
        "student_node": "b0", "destination_slot": "immediate",
        "fingerprint_match": "UNPAIRED_EMPTY_LAYOUT_ONLY_PARAGRAPH",
    }]


def test_residual_projection_rejects_crossed_source_order():
    _require_ordered_residual_projection([
        (10, 10, 20, 20), (14, 14, 25, 25), (20, 20, 31, 31),
    ])

    with pytest.raises(PairAlignmentError) as error:
        _require_ordered_residual_projection([
            (10, 10, 20, 20), (14, 14, 19, 19),
        ])
    assert error.value.reason_code == "ALIGNMENT_AMBIGUOUS"
    assert "cross or nest differently" in str(error.value)


def test_residual_projection_rejects_crossing_between_section_residual_and_group():
    # Student order: section S -> residual A -> unnumbered group G.
    # Teacher order crosses the latter two: section S -> G -> A.
    with pytest.raises(PairAlignmentError) as error:
        _require_ordered_residual_projection([
            (10, 10, 20, 20),  # paired section S
            (14, 14, 31, 31),  # residual A
            (20, 25, 25, 30),  # unnumbered group G
        ])

    assert error.value.reason_code == "ALIGNMENT_AMBIGUOUS"
    assert error.value.evidence["teacher_relation"] == "before"
    assert error.value.evidence["student_relation"] == "after"


def test_residual_projection_allows_corresponding_nested_scopes():
    _require_ordered_residual_projection([
        (10, 30, 20, 40),  # outer explicit exercise scope
        (14, 18, 24, 28),  # paired unnumbered group inside it
        (20, 20, 30, 30),  # paired section heading, still ordered
        (30, 35, 40, 45),  # same partial-overlap relation in both sources
        (34, 39, 44, 49),
    ])

    with pytest.raises(PairAlignmentError) as error:
        _require_ordered_residual_projection([
            (10, 30, 20, 40),
            (14, 18, 35, 42),  # same teacher containment, student partial overlap
        ])
    assert error.value.reason_code == "ALIGNMENT_AMBIGUOUS"
    assert error.value.evidence["teacher_relation"] == "contains"
    assert error.value.evidence["student_relation"] == "partial_before"


def test_residual_projection_rejects_inverse_partial_overlap_order():
    # Both pairs overlap, but their directed order is reversed across sources.
    with pytest.raises(PairAlignmentError) as error:
        _require_ordered_residual_projection([
            (10, 20, 25, 35),
            (15, 25, 20, 30),
        ])

    assert error.value.reason_code == "ALIGNMENT_AMBIGUOUS"
    assert error.value.evidence["teacher_relation"] == "partial_before"
    assert error.value.evidence["student_relation"] == "partial_after"


@pytest.mark.parametrize("template_type", ["1v1", "class"])
def test_math_pair_repeated_numbers_align_as_ordered_occurrences(template_type):
    fixture = (APP.parents[2] / "docs" / "v2" / "integration" / "fixtures" /
               "linear-function-12.4")
    student_path = next(fixture.glob("*原卷版*.docx"))
    teacher_path = next(fixture.glob("*解析版*.docx"))
    student_snapshot = analyze_source(student_path)
    teacher_snapshot = analyze_source(teacher_path)
    result = align_teacher_student(
        student_snapshot, teacher_snapshot,
        student_source_path=student_path, teacher_source_path=teacher_path)

    assert result["status"] == "ALIGNED"
    assert result["student_occurrence_count"] == 21
    assert result["teacher_occurrence_count"] == 21
    assert result["unmatched_real_question_count"] == 0
    assert result["ambiguous_real_question_count"] == 0
    assert [item["question_number"] for item in result["occurrences"]] == [
        1, 2, 3, *range(1, 11), *range(1, 9)]
    assert len({item["canonical_occurrence_id"] for item in result["occurrences"]}) == 21
    student_plan = build_slot_routing_plan(student_path, template_type, snapshot=student_snapshot)
    student_routes = {
        int(item["block_id"][1:]): (
            "cover" if item["destination_slot"] is None else item["destination_slot"])
        for item in student_plan.block_records
    }
    projection = project_pair_routes(
        student_snapshot, teacher_snapshot, result, student_routes,
        student_cover_nodes={int(node[1:]) for node in student_plan.cover_metadata_blocks},
        teacher_cover_nodes=set(cover_metadata_sequences_with_images(teacher_snapshot, None)),
        student_source_path=student_path, teacher_source_path=teacher_path)
    assert projection["status"] == "PROJECTED"
    assert len(projection["occurrences"]) == 21
    assert projection["source_block_counts"] == {"student": 298, "teacher": 1113}
    evidence = projection["teacher_student_residual_block_map"]
    assert any(item.get("fingerprint_match") ==
               "EXACT_TABLE_STRUCTURE_CONTENT_AND_VISUAL_IMAGE_IDENTITY"
               for item in evidence)
    assert any(item.get("fingerprint_match") ==
               "EXPLICIT_ANSWER_ANALYSIS_ATTACHED_TO_EXACT_PAIRED_EXERCISE"
               for item in evidence)
    assert any(item.get("fingerprint_match") ==
               "NORMALIZED_VISUAL_IMAGE_IDENTITY_IN_EXACT_EXERCISE_SCOPE"
               for item in evidence)
    student_projection = {int(seq): slot for seq, slot in
                         projection["student_block_routes"].items()}
    teacher_projection = {int(seq): slot for seq, slot in
                         projection["teacher_block_routes"].items()}
    student_canonical_plan = build_slot_routing_plan(
        student_path, template_type, snapshot=student_snapshot,
        canonical_projection_routes=student_projection)
    teacher_canonical_plan = build_slot_routing_plan(
        teacher_path, template_type, snapshot=teacher_snapshot,
        canonical_projection_routes=teacher_projection)
    for plan, expected in ((student_canonical_plan, student_projection),
                           (teacher_canonical_plan, teacher_projection)):
        actual = {int(item["block_id"][1:]): (
                      "cover" if item["destination_slot"] is None
                      else item["destination_slot"])
                  for item in plan.block_records}
        assert actual == expected


def test_unmatched_student_numbered_candidate_fails_closed():
    student_path = next(FIXTURE.glob("*原卷版*.docx"))
    teacher_path = next(FIXTURE.glob("*解析版*.docx"))
    student = analyze_source(student_path)
    teacher = analyze_source(teacher_path)
    _groups, covered = _question_groups(student)
    # The incident source contains an A-Line-missed numbered question start.
    candidate = next(block for block in student.document.blocks if block.seq == 198)
    assert candidate.seq not in covered
    number = _fingerprint(candidate.text)[0]
    assert number is not None
    candidate.text = f"{number}. 独立学生侧题目内容用于配对拒绝回归"

    with pytest.raises(PairAlignmentError) as error:
        align_teacher_student(student, teacher,
                              student_source_path=student_path,
                              teacher_source_path=teacher_path)
    assert error.value.reason_code == "ALIGNMENT_UNRESOLVED"
    assert "numbered source candidate" in str(error.value)


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

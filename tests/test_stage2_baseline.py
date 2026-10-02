# -*- coding: utf-8 -*-
"""Regression tests for the question-boundary Stage2 baseline."""
import json
import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "v1.2-xml-experiment", "res", "app")
BASELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "tools", "stage2_baseline")
sys.path.insert(0, os.path.abspath(APP_DIR))
sys.path.insert(0, os.path.abspath(BASELINE_DIR))

from run_baseline import predict, schedule_e2_examples  # noqa: E402
from struct_doc import Block, Cell, OleRef, StructDoc, TableBlock  # noqa: E402
from gold_compare import compare  # noqa: E402


def _fixture(texts):
    doc = StructDoc(name="baseline-fixture")
    doc.body_size = 21
    doc.blocks = [Block(seq=i, pno=i + 1, kind="paragraph", text=text,
                        eff_sz=32 if i == 0 else 21, is_empty=False)
                  for i, text in enumerate(texts)]
    return doc


def _table_fixture(rows):
    doc = StructDoc(name="baseline-table-fixture")
    doc.body_size = 21
    table_rows = []
    seq = 0
    for row in rows:
        cells = []
        for text in row:
            blocks = [Block(seq=seq, pno=None, kind="paragraph", text=text,
                            eff_sz=21, is_empty=not bool(text.strip()))]
            seq += 1
            cells.append(Cell(text=text, n_paras=len(blocks), blocks=blocks))
        table_rows.append(cells)
    doc.blocks = [
        Block(seq=0, pno=1, kind="paragraph", text="提升专练", eff_sz=21),
        Block(seq=1, pno=None, kind="table", text="", table=TableBlock(rows=table_rows)),
        Block(seq=2, pno=2, kind="paragraph", text="即时训练", eff_sz=21),
        Block(seq=3, pno=3, kind="paragraph", text="3.计算下列小车通过 AB 段的平均速度是多少？", eff_sz=21),
    ]
    return doc


def test_baseline_is_deterministic():
    doc = _fixture(["第一单元", "即时训练", "1．题干？", "A. 选项", "B. 选项", "【答案】A"])
    idx1, first = predict(doc)
    idx2, second = predict(doc)
    assert idx1.order_ids == idx2.order_ids
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == \
        json.dumps(second, ensure_ascii=False, sort_keys=True)
    assert [u["role"] for u in first] == ["section", "section", "question_group", "answer"]


def test_answer_and_analysis_numbering_does_not_create_questions():
    _, units = predict(_fixture(["即时训练", "1．求 x？", "【答案】A"]))
    assert len([u for u in units if u["role"] == "question_group"]) == 1
    assert units[-1]["role"] == "answer"


def test_answer_key_and_explanation_states_switch_without_number_leakage():
    index, units = predict(_fixture([
        "即时训练", "1．求 x？", "参考答案", "一、1.A  2.B  3.C",
        "【解析】", "1．根据题意，第一题选A。", "【详解】", "第二题的条件说明选B。",
        "二、1.D  2.C", "【分析】此题考查基础概念。", "2．解析中的编号不是题目。",
    ]))
    roles = [u["role"] for u in units]
    assert roles.count("question_group") == 1
    answer_units = [u for u in units if u["role"] == "answer"]
    analysis_units = [u for u in units if u["role"] == "analysis"]
    assert len(answer_units) == 2
    assert len(analysis_units) == 2
    assert index.text_of(analysis_units[0]["spans"][0][0]) == "【解析】"
    assert index.text_of(analysis_units[0]["spans"][0][1]) == "第二题的条件说明选B。"
    assert index.text_of(answer_units[1]["spans"][0][0]) == "二、1.D  2.C"
    assert index.text_of(analysis_units[1]["spans"][0][0]).startswith("【分析】")


def test_column_headings_are_sections_not_questions():
    labels = ["题型1 整数运算", "考点2：方程", "提升专练", "真题感知",
              "能力提升", "即时训练", "巩固练习"]
    doc = _fixture(labels)
    _, units = predict(doc)
    assert [u["role"] for u in units if u["role"] != "body"] == ["section"] * len(labels)
    assert not any(u["role"] == "question_group" for u in units)


def test_independent_consecutive_questions_get_separate_groups():
    doc = _fixture(["提升专练", "13．求方程的根？", "14．计算下列各式。",
                    "15．判断结论是否正确？"])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 3
    anchors = [index.text_of(u["spans"][0][0]) for u in groups]
    assert anchors == ["13．求方程的根？", "14．计算下列各式。", "15．判断结论是否正确？"]


def test_subquestions_stay_inside_their_parent_question():
    doc = _fixture(["巩固练习", "1．解方程，并回答下列问题：", "（1）求出两个根。",
                    "（2）比较两根的大小。", "2．计算 2+3。"])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 2
    first_nodes = index.interval(*groups[0]["spans"][0])
    assert {"（1）求出两个根。", "（2）比较两根的大小。"}.issubset(
        {index.by_id[nid].text for nid in first_nodes})


def test_inline_shared_material_stays_distinct_while_following_subquestions_return_to_parent():
    doc = _fixture(["20．阅读下列材料，回答问题。", "材料1：第一段。", "材料2：第二段。",
                    "（1）判断材料中的性质。", "（2）说明材料的用途。", "【答案】答案"])
    index, units = predict(doc)
    group = next(u for u in units if u["role"] == "question_group")
    materials = [u for u in units if u["role"] == "shared_material"]
    assert len(materials) == 1
    assert materials[0]["spans"] == [["b1", "b2"]]
    assert group["spans"] == [["b0", "b4"]]
    assert group["bind_to"] == materials[0]["id"]
    assert "（1）判断材料中的性质。" not in {
        index.by_id[nid].text for nid in index.interval(*materials[0]["spans"][0])}


def test_empty_parentheses_mark_consecutive_choice_questions():
    doc = _fixture(["一、选择正确图片/词句。",
                    "1.He's going by bike. (    )", "A.B.",
                    "2.I'm going to buy a dictionary. (    )", "A.B.",
                    "3.My brother is going to fly a kite. (    )", "A.B."])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 3
    assert [index.text_of(u["spans"][0][0]) for u in groups] == [
        "1.He's going by bike. (    )",
        "2.I'm going to buy a dictionary. (    )",
        "3.My brother is going to fly a kite. (    )",
    ]


def test_numbered_teaching_instructions_do_not_become_question_groups():
    _, units = predict(_fixture([
        "实验探究", "1.观察图像并归纳小车速度变化的规律。",
        "2.作图，根据实验数据对比各组的变化，再总结实验结论。",
        "3.根据图像求小车在 AB 段的平均速度？",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    assert groups[0]["spans"][0][0]  # The explicit prompt remains detectable.


def test_instruction_prefix_wins_over_embedded_weak_question_cue():
    _, units = predict(_fixture([
        "提升专练", "1.应用计算时，单位要统一；", "2.求下列小车的平均速度是多少？",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    assert groups[0]["spans"][0][0] == "b2"


def test_bold_numbered_topic_with_subparts_is_instructional_heading():
    doc = _fixture(["提升专练", "2．测量平均速度实验的斜面选择", "（1）斜面应选择较小的坡度。"])
    doc.blocks[1].bold = True
    _, units = predict(doc)
    assert not any(u["role"] == "question_group" for u in units)


def test_formula_question_is_not_suppressed_as_explanatory_prose():
    index, units = predict(_fixture([
        "提升专练", "1.利用平方差公式计算 x²-9，当 x=4 时结果是多少？",
        "2.利用概念和公式展开解题时，先观察结构，再归纳方法。",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    assert index.text_of(groups[0]["spans"][0][0]).startswith("1.")


def test_numbered_subparts_after_explicit_example_heading_stay_in_group():
    _, units = predict(_fixture([
        "提升专练", "例题1 计算并说明理由", "1.先化简表达式。", "2.再求 x 的值。",
        "变式1 求另一个方程的根？",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 2


def test_suixuesuilian_heading_needs_a_complete_parent_question():
    _, units = predict(_fixture([
        "随学随练", "1．下图是某实验装置。", "(1)写出实验现象____。",
        "(2)说明该实验的目的____。", "【答案】现象如图所示。",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    assert groups[0]["spans"][0][0] == "b1"


def test_suixuesuilian_heading_or_numbering_alone_does_not_make_question_groups():
    _, units = predict(_fixture([
        "随学随练", "1.第一步先检查装置。", "2.第二步再记录实验结果。",
    ]))
    assert not any(u["role"] == "question_group" for u in units)


def test_multipart_prompt_without_solution_boundary_is_not_dispatchable():
    _, units = predict(_fixture([
        "随学随练", "1．下图是某实验装置。", "(1)写出实验现象____。",
        "(2)说明该实验的目的____。",
    ]))
    assert not any(u["role"] == "question_group" for u in units)


def test_incomplete_example_two_cannot_borrow_example_three_answer():
    starts = _question_group_start_texts(_fixture([
        "知识精讲", "经典例题2 计算2+2等于多少？",
        "经典例题3 计算3+3等于多少？", "【答案】6", "随学随练",
    ]))
    assert starts == ["经典例题3 计算3+3等于多少？"]


def test_two_complete_multipart_questions_can_be_dispatched_in_one_section():
    doc = _fixture([
        "随学随练",
        "1．下图是第一个实验装置。", "(1)记录第一个现象____。", "(2)写出第一个结论____。",
        "【答案】第一题答案。",
        "2．下表是第二个实验数据。", "(1)计算第二个结果____。", "(2)说明第二个结论____。",
        "【答案】第二题答案。",
    ])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert [index.text_of(u["spans"][0][0]) for u in groups] == [
        "1．下图是第一个实验装置。", "2．下表是第二个实验数据。"]
    assert [u["spans"] for u in groups] == [[['b1', 'b3']], [['b5', 'b7']]]


def test_example_one_outside_knowledge_module_is_not_promoted_from_numbering():
    for text in ("例1 计算1+1等于多少？", "经典例题1 通过观察理解实验步骤。"):
        continuation = (["1.先计算中间结果，再写出结论？"]
                        if text.startswith("例1") else [])
        _, units = predict(_fixture([text] + continuation + ["【答案】内容说明。"]))
        assert not any(u["role"] == "question_group" for u in units), text


def test_extra_examples_outside_module_are_not_qgs_without_shortage_evidence():
    starts = _question_group_start_texts(_fixture([
        "例题2 计算2+2等于多少？", "【答案】4",
        "例题3 计算3+3等于多少？", "【答案】6",
        "例题4 计算4+4等于多少？", "【答案】8",
    ]))
    assert starts == []


def _e2_dispatch_fixture(formal_count, second_module_formal_count=None):
    def module(title, count):
        rows = [title, "经典例题1 计算1+1等于多少？", "【答案】2",
                "经典例题2 计算2+2等于多少？", "【答案】4",
                "经典例题3 计算3+3等于多少？", "【答案】6", "随学随练"]
        for number in range(1, count + 1):
            rows.extend(["%d．如图所示，计算第%d题？" % (number, number), "【答案】完成"])
        return rows
    rows = module("知识精讲", formal_count)
    if second_module_formal_count is not None:
        rows.extend(module("知识精讲第二模块", second_module_formal_count))
    return _fixture(rows)


def _question_group_start_texts(doc):
    index, units = predict(doc)
    return [index.text_of(u["spans"][0][0]) for u in units
            if u["role"] == "question_group"]


def test_e2_dispatch_tops_up_zero_formal_groups_with_examples_two_then_three():
    starts = _question_group_start_texts(_e2_dispatch_fixture(0))
    assert starts == ["经典例题2 计算2+2等于多少？", "经典例题3 计算3+3等于多少？"]


def test_e2_dispatch_tops_up_one_formal_group_with_example_two_only():
    starts = _question_group_start_texts(_e2_dispatch_fixture(1))
    assert starts == ["经典例题2 计算2+2等于多少？", "1．如图所示，计算第1题？"]


def test_e2_dispatch_keeps_extra_examples_when_two_formal_groups_exist():
    starts = _question_group_start_texts(_e2_dispatch_fixture(2))
    assert starts == ["1．如图所示，计算第1题？", "2．如图所示，计算第2题？"]


def test_e2_formal_example_groups_after_practice_heading_count_toward_target():
    doc = _fixture([
        "知识精讲", "经典例题1 计算1+1等于多少？", "【答案】2",
        "经典例题2 计算2+2等于多少？", "【答案】4",
        "经典例题3 计算3+3等于多少？", "【答案】6", "随学随练",
        "例题1 如图所示，完成练习甲？", "【答案】甲",
        "例题2 如图所示，完成练习乙？", "【答案】乙",
    ])
    starts = _question_group_start_texts(doc)
    assert starts == ["例题1 如图所示，完成练习甲？", "例题2 如图所示，完成练习乙？"]


def test_e2_dispatch_is_module_local_and_preserves_example_one():
    starts = _question_group_start_texts(_e2_dispatch_fixture(2, 0))
    assert starts == ["1．如图所示，计算第1题？", "2．如图所示，计算第2题？",
                      "经典例题2 计算2+2等于多少？",
                      "经典例题3 计算3+3等于多少？"]
    assert all(not text.startswith("经典例题1") for text in starts)


def test_e2_dispatch_ignores_unindexed_toc_container_candidates():
    index, _ = predict(_fixture(["知识精讲", "经典例题1 计算1+1等于多少？"]))
    candidates = [
        {"node": "b0", "role": "section", "zone": "knowledge"},
        {"node": "b2.r5c0.n8", "role": "toc", "toc_container": "b2.r5c0.n8"},
    ]

    scheduled = schedule_e2_examples(index, candidates)

    assert scheduled == candidates


def test_numbered_learning_objectives_are_filtered_before_weak_question_cues():
    doc = _table_fixture([
        ["目标导航", "方法指导"],
        ["1.掌握平均速度的计算方法。", "1.通过实验测量并记录数据。"],
        ["2.理解实验图像与误差分析。", "2.归纳实验误差的来源。"],
    ])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    assert index.text_of(groups[0]["spans"][0][0]).startswith("3.")


def test_existing_formula_metadata_can_anchor_numbered_exercise_questions():
    for signal in ("omml", "mathtype"):
        doc = _fixture(["提升专练", "1．（2025·模拟题）式子的平方根是        。"])
        question = next(b for b in doc.blocks if "式子的平方根" in b.text)
        if signal == "omml":
            question.math_count = 1
        else:
            question.oles.append(OleRef(rId="rId1", target="word/embeddings/oleObject1.bin",
                                        prog_id="Equation.DSMT4"))
        index, units = predict(doc)
        groups = [u for u in units if u["role"] == "question_group"]
        assert len(groups) == 1, signal
        assert index.text_of(groups[0]["spans"][0][0]).startswith("1．"), signal


def test_formula_metadata_does_not_promote_numbered_knowledge_explanations():
    doc = _fixture(["知识精讲", "1.利用公式进行讲解时，先说明对应概念。"])
    paragraph = next(b for b in doc.blocks if "利用公式" in b.text)
    paragraph.math_count = 1
    _, units = predict(doc)
    assert not any(u["role"] == "question_group" for u in units)


def test_trailing_blank_nodes_do_not_extend_question_group_boundaries():
    doc = _fixture(["提升专练", "1.计算 2+3？", "A. 5", "B. 6", "", "",
                    "题型2 继续练习", "2.计算 4+5？", "A. 9", "B. 10"])
    index, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 2
    blank_ids = {n.id for n in index.nodes if not n.has_content}
    assert blank_ids
    for group in groups:
        members = index.interval(*group["spans"][0])
        assert members
        assert all(index.by_id[nid].has_content for nid in members)
    assert blank_ids.issubset(set(index.order_ids))


def test_trailing_blank_before_answer_section_remains_in_source_span():
    index, units = predict(_fixture(["提升专练", "1.计算 2+3？", "", "参考答案", "1.A"]))
    group = next(u for u in units if u["role"] == "question_group")
    assert group["spans"][0][1] == "b2"
    assert "b2" in index.order_ids


def test_numbered_instruction_and_answer_lines_are_not_questions():
    doc = _fixture(["知识精讲", "1．首先观察等式两边的结构。", "2．方法：利用公式变形。",
                    "目标导航", "一、掌握平方差公式。", "方法指导", "一、首先提取公因式。",
                    "即时训练", "1．求 x？", "答案与解析", "1．B", "一、1.B  2.A  3.C",
                    "解析：根据题意可知。"])
    _, units = predict(doc)
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 1
    answer_units = [u for u in units if u["role"] == "answer"]
    assert answer_units
    assert not any("一、1.B" in u.get("note", "") for u in units if u["role"] == "section")


def test_toc_detection_remains_intact():
    doc = _fixture(["目录", "第一章 .......... 1", "第二章 .......... 2",
                    "第三章 .......... 3", "即时训练", "1．计算 1+1。"])
    _, units = predict(doc)
    assert any(u["role"] == "toc" for u in units)
    assert any(u["role"] == "question_group" for u in units)


def test_contents_navigation_runs_to_first_body_heading():
    index, units = predict(_fixture([
        "专题01 实数", "内容导航", "考点聚焦：核心考点+高考考点",
        "重点速记：知识点和关键点梳理", "知识点 1 算术平方根",
        "定义：", "正数 x 的平方等于 a。",
    ]))
    toc = [u for u in units if u["role"] == "toc"]
    sections = [u for u in units if u["role"] == "section"]
    assert len(toc) == 1
    toc_nodes = sorted(index.interval(*toc[0]["spans"][0]), key=index.order_of)
    assert [index.text_of(nid) for nid in toc_nodes] == [
        "内容导航", "考点聚焦：核心考点+高考考点", "重点速记：知识点和关键点梳理"]
    assert index.text_of(sections[1]["spans"][0][0]) == "知识点 1 算术平方根"
    assert any(u["role"] == "knowledge" for u in units)


def test_explicit_teaching_heading_family_is_section():
    labels = ["教学内容", "知识精讲&例题讲解", "知识导图", "【深化点拨】",
              "第1.4节 速度的测量", "速度测量的综合应用及解题步骤"]
    _, units = predict(_fixture(labels))
    sections = [u for u in units if u["role"] == "section"]
    assert len(sections) == len(labels)


def test_knowledge_tip_inside_exercise_does_not_end_question_sequence():
    _, units = predict(_fixture([
        "题型1 求平方根", "高妙技法", "注意不同数值的根式处理。",
        "1．求 x 的平方根？", "2．计算下列式子。",
    ]))
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(groups) == 2


def test_cited_reading_materials_bind_only_to_their_question_groups():
    doc = _fixture(["阅读理解", "01", "（2024·省级模拟）First article paragraph.",
                    "More article text.", "1. What is the first question?", "A. Answer one.",
                    "2. Which statement is correct?", "B. Answer two.", "02",
                    "（2023·校级模拟）Second article paragraph.",
                    "3. Who is mentioned in the text?", "A. A student."])
    index, units = predict(doc)
    materials = [u for u in units if u["role"] == "shared_material"]
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(materials) == 2
    assert len(groups) == 2
    assert groups[0]["bind_to"] == materials[0]["id"]
    assert groups[1]["bind_to"] == materials[1]["id"]
    second_material_start = index.order_of(materials[1]["spans"][0][0])
    first_group_end = index.order_of(groups[0]["spans"][0][1])
    assert first_group_end < second_material_start
    gold = {"units": [
        {"id": "m1", "role": "shared_material", "start": 2, "end": 3},
        {"id": "q1", "role": "question_group", "start": 4, "end": 7, "bind_to": "m1"},
        {"id": "m2", "role": "shared_material", "start": 9, "end": 9},
        {"id": "q2", "role": "question_group", "start": 10, "end": 11, "bind_to": "m2"},
    ]}
    comparison = compare(doc, gold, units)
    assert not any(issue.code in ("UNBOUND", "GROUP_SPLIT", "DUPLICATION")
                   for issue in comparison.issues)


def test_cited_chinese_reading_questions_share_one_group():
    doc = _fixture(["阅读理解", "01", "（2024·省级模拟）中文阅读材料。",
                    "1. 下列哪项正确？", "A. 第一项。", "2. 哪项符合文意？", "B. 第二项。"])
    _, units = predict(doc)
    assert len([u for u in units if u["role"] == "shared_material"]) == 1
    assert len([u for u in units if u["role"] == "question_group"]) == 1


def test_explicit_reading_material_heading_starts_material():
    doc = _fixture(["阅读理解", "【材料】一段阅读文字。", "1. Which choice is right?"])
    _, units = predict(doc)
    materials = [u for u in units if u["role"] == "shared_material"]
    groups = [u for u in units if u["role"] == "question_group"]
    assert len(materials) == len(groups) == 1
    assert groups[0]["bind_to"] == materials[0]["id"]


def test_real_corpus_manifest_has_exact_gold_set():
    path = os.path.join(BASELINE_DIR, "manifest.json")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    assert [s["sample_id"] for s in manifest["samples"]] == ["S01", "S11", "S12", "S04"]
    assert all(len(s["sha256"]) == 64 for s in manifest["samples"])


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    failures = []
    for test in ALL:
        try:
            test()
            print("PASS %s" % test.__name__)
        except Exception as exc:
            failures.append((test.__name__, exc))
            print("FAIL %s: %s: %s" % (test.__name__, type(exc).__name__, exc))
    print("\n%d passed, %d failed" % (len(ALL) - len(failures), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

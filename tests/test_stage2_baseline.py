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

from run_baseline import predict  # noqa: E402
from struct_doc import Block, StructDoc  # noqa: E402
from gold_compare import compare  # noqa: E402


def _fixture(texts):
    doc = StructDoc(name="baseline-fixture")
    doc.body_size = 21
    doc.blocks = [Block(seq=i, pno=i + 1, kind="paragraph", text=text,
                        eff_sz=32 if i == 0 else 21, is_empty=False)
                  for i, text in enumerate(texts)]
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

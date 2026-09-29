# -*- coding: utf-8 -*-
"""
test_gold_compare.py —— 「人工 Gold vs 程序结果」对照工具自动测试

用**人工构造 fixture**（内存 StructDoc + gold/pred dict）覆盖每一类判定：
内容遗漏 / 无意重复 / 题组被拆 / 目录误当正文 / 正文误当目录 / 章节关系错误 /
共享材料解绑 / gold 有而程序未识别 / 独立单元被合并 / 顺序变化不判错 /
gold 标注缺口 / 锚点重复文本的顺序解析。
外加一个真实文件集成自审（存在才跑）。

运行：python tests/test_gold_compare.py
      或 python -m pytest tests/test_gold_compare.py
"""
import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "v1.2-xml-experiment", "res", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

from gold_compare import compare, render_report  # noqa: E402
from struct_doc import Block, StructDoc  # noqa: E402

# ---------------------------------------------------------------
# fixture 构造
# ---------------------------------------------------------------
FIXTURE_TEXTS = [
    "话题7 文学与艺术类",              # 0  section
    "体裁：说明文 词数：298 难度：中",   # 1  (section 内部信息行)
    "Passage1（2020•新高考Ⅰ）",        # 2  shared_material 起
    "In the mid-1990s Tom Bissell...",   # 3  材料正文
    "His visit however ended up...",     # 4  材料正文
    "1. What made Mr Bissell return?",   # 5  question_group 起
    "A. His friends' invitation.",       # 6
    "2. What does the word that refer to?",  # 7
    "B. Taking a guided tour.",          # 8
    "参考答案 B D",                      # 9  answer
    "【解析】根据第一段...",              # 10 analysis
    "Passage2（2015•新课标Ⅰ）",          # 11 shared_material 起
    "Salvador Dali was one of...",       # 12 材料正文
    "1. Which best describes Dali?",     # 13 question_group 起
    "A. Optimistic.",                    # 14
    "【答案】A",                          # 15 answer
]


def _doc(texts=None):
    texts = texts if texts is not None else FIXTURE_TEXTS
    blocks = []
    for i, t in enumerate(texts):
        blocks.append(Block(seq=i, pno=i + 1, kind="paragraph", text=t,
                            eff_sz=28 if t.startswith("话题") else 21,
                            is_empty=not t.strip()))
    d = StructDoc(name="fixture")
    d.blocks = blocks
    d.body_size = 21
    return d


def gold_units():
    """一份「完整、正确」的 gold：2 个材料 + 2 个题组 + 2 处答案/解析 + 1 个章节。"""
    return {
        "doc": "fixture",
        "units": [
            {"id": "s1", "role": "section", "level": 1, "anchor": "话题7 文学与艺术类"},
            {"id": "m1", "role": "shared_material", "anchor": "Passage1",
             "end_anchor": "1. What made"},
            {"id": "g1", "role": "question_group", "anchor": "1. What made",
             "end_anchor": "参考答案", "parent": "s1", "bind_to": "m1"},
            {"id": "a1", "role": "answer", "anchor": "参考答案",
             "end_anchor": "Passage2", "parent": "s1"},
            {"id": "m2", "role": "shared_material", "anchor": "Passage2",
             "end_anchor": "1. Which best"},
            {"id": "g2", "role": "question_group", "anchor": "1. Which best",
             "end_anchor": "【答案】A", "parent": "s1", "bind_to": "m2"},
            {"id": "a2", "role": "answer", "anchor": "【答案】A", "parent": "s1"},
        ],
    }


def pred_perfect():
    """与 gold 完全对应的程序结果（区间覆盖一致，角色一致，父子/绑定一致）。"""
    return [
        {"id": "P1", "role": "section", "level": 1, "start": 0, "end": 1},
        {"id": "P2", "role": "shared_material", "start": 2, "end": 4},
        {"id": "P3", "role": "question_group", "start": 5, "end": 8,
         "parent": "P1", "bind_to": "P2"},
        {"id": "P4", "role": "answer", "start": 9, "end": 10, "parent": "P1"},
        {"id": "P5", "role": "shared_material", "start": 11, "end": 12},
        {"id": "P6", "role": "question_group", "start": 13, "end": 14,
         "parent": "P1", "bind_to": "P5"},
        {"id": "P7", "role": "answer", "start": 15, "end": 15, "parent": "P1"},
    ]


def codes(cmp):
    return [i.code for i in cmp.issues]


def hard(cmp):
    return [i.code for i in cmp.by_level("error")]


# ---------------------------------------------------------------
# 测试
# ---------------------------------------------------------------
def test_anchor_resolution_and_perfect_match():
    """锚点解析正确（含顺序推进）且完美对照零错误。"""
    doc = _doc()
    cmp = compare(doc, gold_units(), pred_perfect())
    assert cmp.verdict == "PASS", (cmp.verdict, hard(cmp))
    assert "OMISSION" not in codes(cmp)
    assert "GROUP_SPLIT" not in codes(cmp)
    assert "UNBOUND" not in codes(cmp)
    assert "HIERARCHY" not in codes(cmp)
    # 单元区间解析结果
    by_id = {u.id: u for u in cmp.gold_units}
    assert by_id["m1"].spans == [("b2", "b4")], by_id["m1"].spans
    assert by_id["g1"].spans == [("b5", "b8")], by_id["g1"].spans
    assert by_id["a1"].spans == [("b9", "b10")], by_id["a1"].spans
    assert by_id["a2"].spans == [("b15", "b15")], by_id["a2"].spans


def test_duplicate_anchor_text_resolves_sequentially():
    """同名锚点（'1. ' 出现在多个题组）按文档顺序依次解析，不串位。"""
    doc = _doc()
    cmp = compare(doc, gold_units(), pred_perfect())
    by_id = {u.id: u for u in cmp.gold_units}
    assert by_id["g1"].spans[0][0] == "b5"
    assert by_id["g2"].spans[0][0] == "b13"


def test_omission_detected():
    """程序漏掉一段材料 → OMISSION（内容遗漏）。"""
    doc = _doc()
    pred = pred_perfect()
    pred[1] = {"id": "P2", "role": "shared_material", "start": 2, "end": 3}   # 少了块 4
    cmp = compare(doc, gold_units(), pred)
    assert "OMISSION" in hard(cmp)
    iss = [i for i in cmp.issues if i.code == "OMISSION"][0]
    assert "b4" in iss.nodes


def test_omission_does_not_also_report_group_split():
    """遗漏的块不应被同时报成 GROUP_SPLIT（避免同一问题双重报错）。"""
    doc = _doc()
    pred = pred_perfect()
    pred[1] = {"id": "P2", "role": "shared_material", "start": 2, "end": 3}  # m1(=2-4) 漏掉块 4
    cmp = compare(doc, gold_units(), pred)
    assert "OMISSION" in hard(cmp)
    assert "b4" in [n for i in cmp.issues if i.code == "OMISSION" for n in i.nodes]
    assert not [i for i in cmp.issues if i.code == "GROUP_SPLIT" and i.subject == "m1"], \
        "遗漏不应同时报 GROUP_SPLIT：%s" % [i.detail for i in cmp.issues
                                            if i.code == "GROUP_SPLIT"]


def test_duplication_detected():
    """程序两个单元区间重叠 → DUPLICATION（无意重复）。"""
    doc = _doc()
    pred = pred_perfect()
    pred.append({"id": "P8", "role": "answer", "start": 9, "end": 11})
    cmp = compare(doc, gold_units(), pred)
    assert "DUPLICATION" in hard(cmp)


def test_group_split_detected():
    """一个完整题组被程序切成两个单元 → GROUP_SPLIT。"""
    doc = _doc()
    pred = pred_perfect()
    pred[2] = {"id": "P3a", "role": "question_group", "start": 5, "end": 6,
               "parent": "P1", "bind_to": "P2"}
    pred.insert(3, {"id": "P3b", "role": "question_group", "start": 7, "end": 8,
                    "parent": "P1", "bind_to": "P2"})
    cmp = compare(doc, gold_units(), pred)
    assert "GROUP_SPLIT" in hard(cmp)
    iss = [i for i in cmp.issues if i.code == "GROUP_SPLIT"][0]
    assert iss.subject == "g1"


def test_equal_coverage_tie_uses_earliest_predicted_unit():
    """Set/hash iteration must not change a Gold unit's primary prediction."""
    doc = _doc(["题目第一段", "题目第二段"])
    gold = {"units": [{"id": "g1", "role": "question_group", "start": 0, "end": 1}]}
    pred = [
        {"id": "P1", "role": "body", "start": 0, "end": 0},
        {"id": "P2", "role": "question_group", "start": 1, "end": 1},
    ]
    cmp = compare(doc, gold, pred)
    assert any(i.code == "MISSED_STRUCTURE" and i.subject == "g1->P1" for i in cmp.issues)
    assert not any(i.code == "ROLE_MISMATCH" and i.subject.startswith("g1->")
                   for i in cmp.issues)


def test_toc_as_body_and_body_as_toc():
    """目录误当正文 / 正文误当目录，两个方向都要报。"""
    texts = ["目录", "第一章 实数......3", "第二章 方程......9",
             "第一章 实数", "1. 计算下列各题"]
    doc = _doc(texts)
    gold = {"units": [
        {"id": "t1", "role": "toc", "anchor": "目录"},
        {"id": "s1", "role": "section", "anchor": "第一章 实数", "level": 1},
    ]}
    # a) gold 目录被程序判成 body
    cmp = compare(doc, gold, [
        {"id": "Q1", "role": "body", "start": 0, "end": 2},
        {"id": "Q2", "role": "section", "level": 1, "start": 3, "end": 4},
    ])
    assert "TOC_AS_BODY" in hard(cmp)
    # b) gold 正文被程序判成 toc
    cmp2 = compare(doc, gold, [
        {"id": "Q1", "role": "toc", "start": 0, "end": 2},
        {"id": "Q2", "role": "toc", "start": 3, "end": 4},
    ])
    assert "BODY_AS_TOC" in hard(cmp2)


def test_hierarchy_error_detected():
    """子单元未被父单元包含 → HIERARCHY。"""
    doc = _doc()
    pred = pred_perfect()
    pred[0] = {"id": "P1", "role": "section", "level": 1, "start": 0, "end": 0}  # 父不再包含子
    pred[2]["parent"] = "P9"                                                    # 且声明错父
    cmp = compare(doc, gold_units(), pred)
    assert "HIERARCHY" in hard(cmp)


def test_hierarchy_level_mismatch():
    """层级不一致 → HIERARCHY。"""
    doc = _doc()
    pred = pred_perfect()
    pred[0] = {"id": "P1", "role": "section", "level": 2, "start": 0, "end": 1}
    cmp = compare(doc, gold_units(), pred)
    assert "HIERARCHY" in hard(cmp)


def test_unbound_shared_material():
    """材料与题组被拆到不同单元、且程序未声明绑定 → UNBOUND。"""
    doc = _doc()
    pred = pred_perfect()
    pred[1] = {"id": "P2", "role": "shared_material", "start": 2, "end": 2}
    pred[2] = {"id": "P3", "role": "question_group", "start": 3, "end": 8,
               "parent": "P1"}          # 故意不给 bind_to：绑定关系丢失
    cmp = compare(doc, gold_units(), pred)
    assert "UNBOUND" in hard(cmp)


def test_unbound_declared_wrong_material():
    """程序声明了绑定，但指向了错误材料 → UNBOUND。"""
    doc = _doc()
    pred = pred_perfect()
    pred[2] = {"id": "P3", "role": "question_group", "start": 5, "end": 8,
               "parent": "P1", "bind_to": "P5"}   # P5 是第二篇材料，绑定错位
    cmp = compare(doc, gold_units(), pred)
    assert "UNBOUND" in hard(cmp)


def test_missed_structure_detected():
    """gold 有章节结构而程序未识别（降级为 body）→ MISSED_STRUCTURE(warn)，不判 FAIL。"""
    doc = _doc()
    pred = pred_perfect()
    pred[0] = {"id": "P1", "role": "body", "start": 0, "end": 1}   # 章节被降级为 body
    cmp = compare(doc, gold_units(), pred)
    assert "MISSED_STRUCTURE" in codes(cmp)
    assert "MISSED_STRUCTURE" in [i.code for i in cmp.by_level("warn")]
    assert cmp.verdict == "PASS"          # 降级是 warn，不判 FAIL
    assert not hard(cmp)


def test_hierarchy_relation_lost_when_parent_not_declared():
    """程序完全不声明父子关系 → HIERARCHY(error)，关系视为丢失。"""
    doc = _doc()
    pred = pred_perfect()
    for p in pred:
        p.pop("parent", None)
    cmp = compare(doc, gold_units(), pred)
    assert "HIERARCHY" in hard(cmp)


def test_missed_structure_hard_when_uncovered():
    """gold 单元完全没被覆盖 → MISSED_STRUCTURE(error)。"""
    doc = _doc()
    pred = [p for p in pred_perfect() if p["id"] != "P7"]   # 最后一个答案单元缺失
    cmp = compare(doc, gold_units(), pred)
    assert "MISSED_STRUCTURE" in hard(cmp)


def test_merge_warning():
    """两个独立 gold 单元被合并进同一个程序单元 → MERGE(warn)。"""
    doc = _doc()
    pred = pred_perfect()
    pred[3] = {"id": "P4", "role": "answer", "start": 9, "end": 10, "parent": "P1"}
    # 把 m2/g2/a2 合成一个大单元
    pred = pred[:4] + [{"id": "P9", "role": "question_group", "start": 11, "end": 15,
                        "parent": "P1", "bind_to": "P9"}]
    cmp = compare(doc, gold_units(), pred)
    assert "MERGE" in [i.code for i in cmp.by_level("warn")]


def test_order_change_not_error():
    """顺序变化本身不判错：只出 ORDER_CHANGE(info)，无 error。"""
    doc = _doc()
    # 程序把两个材料/题组对调输出顺序（片段集合仍正确）
    pred = [
        {"id": "P1", "role": "section", "level": 1, "start": 0, "end": 1},
        {"id": "P5", "role": "shared_material", "start": 11, "end": 12},
        {"id": "P6", "role": "question_group", "start": 13, "end": 14,
         "parent": "P1", "bind_to": "P5"},
        {"id": "P2", "role": "shared_material", "start": 2, "end": 4},
        {"id": "P3", "role": "question_group", "start": 5, "end": 8,
         "parent": "P1", "bind_to": "P2"},
        {"id": "P4", "role": "answer", "start": 9, "end": 10, "parent": "P1"},
        {"id": "P7", "role": "answer", "start": 15, "end": 15, "parent": "P1"},
    ]
    cmp = compare(doc, gold_units(), pred)
    assert "ORDER_CHANGE" in codes(cmp)
    assert cmp.verdict == "PASS", hard(cmp)


def test_reorder_via_multi_segment_spans():
    """单元重排用多片段 spans 表达时，题组仍视为完整（不误报拆分）。"""
    doc = _doc()
    gold = {"units": [
        {"id": "g", "role": "question_group", "spans": [[5, 6], [7, 8]]},
    ]}
    pred = [{"id": "P", "role": "question_group", "spans": [[5, 6], [7, 8]]}]
    cmp = compare(doc, gold, pred)
    assert "GROUP_SPLIT" not in hard(cmp)


def test_gold_gap_is_info_only():
    """gold 没标到的内容只报 GOLD_GAP(info)，不影响结论。"""
    doc = _doc()
    gold = {"units": [{"id": "s1", "role": "section", "anchor": "话题7",
                       "end_anchor": "Passage1"}]}
    cmp = compare(doc, gold, [{"id": "P1", "role": "section", "level": 1,
                               "start": 0, "end": 1}])
    assert "GOLD_GAP" in codes(cmp)
    assert cmp.summary["gold_gap_nodes"] > 0
    assert cmp.verdict == "PASS"


def test_gold_self_audit_without_pred():
    """不给程序结果时只做 gold 自审：不产生程序侧错误。"""
    doc = _doc()
    cmp = compare(doc, gold_units(), None)
    assert cmp.summary["pred_units"] == 0
    assert not hard(cmp)


def test_anchor_not_found_reported():
    """锚点找不到 → GOLD_ANCHOR(info)，并且不崩溃。"""
    doc = _doc()
    gold = {"units": [{"id": "x", "role": "section", "anchor": "根本不存在的标题"}]}
    cmp = compare(doc, gold, [{"id": "P1", "role": "body", "start": 0, "end": 1}])
    assert "GOLD_ANCHOR" in codes(cmp)


def test_unknown_role_roundtrip():
    """unknown 角色可表达且能正常对照。"""
    doc = _doc(["正文一", "结构化标签内容", "正文二"])
    gold = {"units": [
        {"id": "b1", "role": "body", "anchor": "正文一"},
        {"id": "u1", "role": "unknown", "anchor": "结构化标签内容"},
        {"id": "b2", "role": "body", "anchor": "正文二"},
    ]}
    cmp = compare(doc, gold, [
        {"id": "P1", "role": "body", "start": 0, "end": 0},
        {"id": "P2", "role": "unknown", "start": 1, "end": 1},
        {"id": "P3", "role": "body", "start": 2, "end": 2},
    ])
    assert cmp.verdict == "PASS", hard(cmp)


def test_report_renders():
    """报告渲染：包含结论、统计表、判分口径说明。"""
    doc = _doc()
    pred = pred_perfect()
    pred[1] = {"id": "P2", "role": "shared_material", "start": 2, "end": 3}
    cmp = compare(doc, gold_units(), pred)
    md = render_report(doc, cmp, "gold.json", "pred.json")
    for token in ["对照报告", "结论", "问题统计", "单元对照表", "判分口径说明",
                  "顺序变化不判错", "内容遗漏"]:
        assert token in md, token
    assert "| OMISSION |" in md


def test_real_doc_gold_selfaudit():
    """真实文件集成：示例 gold 能在真实 StructDoc 上解析且无 error。"""
    real = (r"C:\Users\Administrator\Desktop\工作\讲义生成器\训练文件"
            r"\章宇琪资料.zip")
    gold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "docs", "v2", "gold_example_话题七解析版.json")
    if not os.path.exists(gold_path):
        print("  [SKIP] 示例 gold 不存在")
        return
    if not os.path.exists(real):
        print("  [SKIP] 真实语料 zip 不存在")
        return
    import io
    import json
    import zipfile
    from struct_doc import read_struct_doc_bytes
    with zipfile.ZipFile(real) as z:
        member = next((n for n in z.namelist()
                       if "话题七" in n and "解析版" in n and n.lower().endswith(".docx")), None)
        if member is None:
            print("  [SKIP] 语料 zip 中没有示例 gold 对应的‘话题七解析版’源文件")
            return
        doc = read_struct_doc_bytes(z.read(member), name=member)
    with open(gold_path, "r", encoding="utf-8") as fh:
        gold = json.load(fh)
    cmp = compare(doc, gold, None)
    assert not hard(cmp), hard(cmp)
    assert cmp.summary["gold_units"] > 0
    # 锚点必须全部解析成功
    assert "GOLD_ANCHOR" not in codes(cmp), [i.detail for i in cmp.issues
                                            if i.code == "GOLD_ANCHOR"]


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    ok = fail = 0
    for fn in ALL:
        try:
            fn()
            print("PASS %s" % fn.__name__)
            ok += 1
        except AssertionError as e:
            print("FAIL %s: %s" % (fn.__name__, e))
            fail += 1
        except Exception as e:
            print("ERROR %s: %s: %s" % (fn.__name__, type(e).__name__, e))
            fail += 1
    print("\n%d passed, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""E1 regression: recover the question boundary after an answer/analysis block.

Business rule (Splitter Business Rules v1.0, R5):
    After the answer/analysis of the previous question ends, an **explicit and
    complete** new prompt reopens a question_group. Short numbered explanation
    steps must NOT reopen one.

Cases:
  A  X004 解析版: the analysis of Q1 ends, `2．（…天津河西·期末）…` must open a QG.
  B  X006 解析版: the answer of Q1 ends, `2．（2024秋•嘉峪关校级期末）火锅…` must open a QG.
  C  negative : numbered explanation steps (`1. 由题意…` / `2. 乙的…`) stay suppressed.
  D  原卷回归 : X003 keeps its 78 question groups (no new/missing boundaries).

Real sources are read from the frozen Stage3 staging tree and skipped when absent.
Run: python tests/test_e1_question_recovery.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "v1.2-xml-experiment", "res", "app"))
sys.path.insert(0, os.path.join(ROOT, "tools", "stage2_baseline"))

from run_baseline import predict  # noqa: E402
from struct_doc import Block, StructDoc, read_struct_doc_bytes  # noqa: E402

STAGE3 = r"C:\xml-uat\stage3-expansion"
SOURCES = os.path.join(STAGE3, "sources")
APPROVED = os.path.join(STAGE3, "gold_preparation_01", "APPROVED_GOLD")


def _load(sid):
    """Parse a staged real source; return (index, units) or None when unavailable."""
    path = os.path.join(SOURCES, "%s.docx" % sid)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        doc = read_struct_doc_bytes(fh.read(), name="%s.docx" % sid)
    index, units = predict(doc)
    return index, units


def _qg_starts(index, units):
    out = set()
    for u in units:
        if u["role"] != "question_group":
            continue
        o = index.order_of(u["spans"][0][0])
        if o is not None:
            out.add(o)
    return out


def _find_order(index, needle):
    for n in index.nodes:
        if needle in (n.text or ""):
            return n.order
    return None


def _approved_gold_starts(sid):
    path = os.path.join(APPROVED, "%s_APPROVED_GOLD.json" % sid)
    if not os.path.exists(path):
        return None
    doc = json.load(open(path, encoding="utf-8"))
    return doc


def _fixture(texts):
    """Synthetic document: body-level paragraphs only (same shape as legacy tests)."""
    doc = StructDoc(name="e1-fixture")
    doc.body_size = 21
    doc.blocks = [Block(seq=i, pno=i + 1, kind="paragraph", text=t, eff_sz=21,
                        is_empty=not bool(t.strip()))
                  for i, t in enumerate(texts)]
    return doc


# ---------------------------------------------------------------
# Case A — X004（解析版）：analysis 之后恢复题界
# ---------------------------------------------------------------
def test_case_a_x004_recovers_after_analysis():
    loaded = _load("X004")
    if loaded is None:
        print("  [SKIP] X004 源文件不可用")
        return
    index, units = _load("X004")
    starts = _qg_starts(index, units)
    o = _find_order(index, "一种家用电能表上的参数如图所示")
    assert o is not None, "未找到 X004 第 2 题题干"
    assert o in starts, "E1: analysis 之后未恢复题界（order=%s）" % o
    assert len(starts) >= 60, "E1: 解析版题组数仍被吞并（%d 个）" % len(starts)


def test_case_a2_x004_all_following_questions_open():
    """Q2 之后每一道新题都应恢复题界（抽查 Q3/Q4/Q5）。"""
    loaded = _load("X004")
    if loaded is None:
        print("  [SKIP] X004 源文件不可用")
        return
    index, units = loaded
    starts = _qg_starts(index, units)
    for needle in ("3．（24-25九年级上·广东汕头·期末）",
                   "4．（24-25九年级上·湖北武汉·期末）",
                   "5．（24-25九年级上·四川成都·期末）"):
        o = _find_order(index, needle)
        assert o is not None, "未找到题干: %s" % needle
        assert o in starts, "E1: %s 未恢复题界" % needle


# ---------------------------------------------------------------
# Case B — X006（解析版）：answer 之后恢复题界
# ---------------------------------------------------------------
def test_case_b_x006_recovers_after_answer():
    loaded = _load("X006")
    if loaded is None:
        print("  [SKIP] X006 源文件不可用")
        return
    index, units = loaded
    starts = _qg_starts(index, units)
    o = _find_order(index, "火锅是重庆的特色美食")
    assert o is not None, "未找到 X006 第 2 题题干"
    assert o in starts, "E1: answer 之后未恢复题界（order=%s）" % o
    assert len(starts) >= 40, "E1: 题组数仍被吞并（%d 个）" % len(starts)


# ---------------------------------------------------------------
# Case C — negative：解析步骤的编号不得开启新题组
# ---------------------------------------------------------------
def test_case_c_explanation_numbering_is_not_a_question():
    doc = _fixture([
        "1．下列做法正确的是（　　）",
        "A．甲同学的做法",
        "B．乙同学的做法",
        "【答案】A",
        "解析：本题考查基本概念与判据。",
        "1. 由题意可知甲符合条件，故选 A。",
        "2. 乙的说法与定义不符。",
        "3. 丙需要额外条件才能成立。",
        "2．下列说法错误的是（　　）",
        "A．甲",
        "B．乙",
    ])
    _index, units = predict(doc)
    starts = _qg_starts(_index, units)
    def order_of(text):
        for n in _index.nodes:
            if n.text == text:
                return n.order
        return None
    for step in ("1. 由题意可知甲符合条件，故选 A。",
                 "2. 乙的说法与定义不符。",
                 "3. 丙需要额外条件才能成立。"):
        o = order_of(step)
        assert o is not None
        assert o not in starts, "解析步骤被误判为题组：%s" % step
    # 同一份 fixture 里，真正的新题仍必须开启
    o2 = order_of("2．下列说法错误的是（　　）")
    assert o2 in starts, "完整新题干未开启题组"


def test_case_c2_answer_key_rows_are_not_questions():
    doc = _fixture([
        "1．下列说法正确的是（　　）",
        "A．甲",
        "B．乙",
        "【答案】1．B 2．C 3．D",
        "解析：逐项分析如下。",
        "1．B．甲选项不符合",
        "2．C．乙选项符合题意",
    ])
    index, units = predict(doc)
    starts = _qg_starts(index, units)
    assert len([s for s in starts]) == 1, "答案键/解析行被误判为题组（%d 个起点）" % len(starts)


# ---------------------------------------------------------------
# Case D — 原卷回归：X003 题界不得变化
# ---------------------------------------------------------------
def test_case_d_x003_original_regression():
    loaded = _load("X003")
    if loaded is None:
        print("  [SKIP] X003 源文件不可用")
        return
    index, units = loaded
    starts = _qg_starts(index, units)
    assert len(starts) == 78, "X003 原卷题组数变化：%d（期望 78）" % len(starts)
    gold = _approved_gold_starts("X003")
    if gold is not None:
        gold_starts = set()
        for u in gold["units"]["question_groups"]:
            o = index.order_of(u["spans"][0][0])
            if o is not None:
                gold_starts.add(o)
        extra = starts - gold_starts
        assert not extra, "X003 原卷出现 %d 个新题界（回归）" % len(extra)
        missing = gold_starts - starts
        assert not missing, "X003 原卷丢失 %d 个题界（回归）" % len(missing)


def test_case_d2_x013_original_regression():
    """第二份原卷回归：X013 题界数不得因 E1 补丁而变化。"""
    loaded = _load("X013")
    if loaded is None:
        print("  [SKIP] X013 源文件不可用")
        return
    index, units = loaded
    starts = _qg_starts(index, units)
    assert len(starts) == 39, "X013 原卷题组数变化：%d（期望 39）" % len(starts)


# ---------------------------------------------------------------
# 额外：X012 / X025（同为解析版，E1 的另两个受害者）
# ---------------------------------------------------------------
def test_x012_recovers_missing_questions():
    loaded = _load("X012")
    if loaded is None:
        print("  [SKIP] X012 源文件不可用")
        return
    index, units = loaded
    starts = _qg_starts(index, units)
    assert len(starts) >= 40, "X012 题组数未提升（%d，期望 ≥40）" % len(starts)


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

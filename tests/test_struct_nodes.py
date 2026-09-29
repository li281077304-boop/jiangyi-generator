# -*- coding: utf-8 -*-
"""
test_struct_nodes.py —— 表格单元格内部节点的稳定寻址 + Gold 对照（Splitter V2 预备）

覆盖本次变更（用户需求）：
  1. 表格单元格内部节点的稳定、可重复 id（含嵌套表格）
  2. 「同一张表中，前半部分是知识、后半部分是题组」的标注与判定
  3. 容器端点自动展开（整数区间向后兼容）
  4. scope + anchor 在单元格内定位
  5. nested table 场景：节点 id、gold 标注、题组拆分 / 遗漏 / 合并判定

运行：python tests/test_struct_nodes.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "app")))
sys.path.insert(0, HERE)

from gold_compare import compare  # noqa: E402
from struct_doc import read_struct_doc_bytes  # noqa: E402
from struct_nodes import NodeIndex  # noqa: E402
from test_struct_doc import make_docx  # noqa: E402  （复用 docx 构造器）

# ---------------------------------------------------------------
# 合成讲义：body = [段落, 表格(2x2，含嵌套表), 段落]
# ---------------------------------------------------------------
BODY = """
<w:p><w:r><w:t>封面标题</w:t></w:r></w:p>
<w:tbl>
  <w:tr>
    <w:tc>
      <w:p><w:r><w:t>知识精讲</w:t></w:r></w:p>
      <w:p><w:r><w:t>知识点一：定义</w:t></w:r></w:p>
    </w:tc>
    <w:tc>
      <w:p><w:r><w:t>右侧共享材料：阅读短文</w:t></w:r></w:p>
    </w:tc>
  </w:tr>
  <w:tr>
    <w:tc>
      <w:p><w:r><w:t>题型1 判断题</w:t></w:r></w:p>
      <w:p><w:r><w:t>1. 下列说法正确的是</w:t></w:r></w:p>
      <w:p><w:r><w:t>A. 对</w:t></w:r></w:p>
      <w:p><w:r><w:t>B. 错</w:t></w:r></w:p>
    </w:tc>
    <w:tc>
      <w:tbl>
        <w:tr><w:tc><w:p><w:r><w:t>嵌套单元格文本</w:t></w:r></w:p></w:tc></w:tr>
      </w:tbl>
    </w:tc>
  </w:tr>
</w:tbl>
<w:p><w:r><w:t>文末说明</w:t></w:r></w:p>
"""


def doc():
    return read_struct_doc_bytes(make_docx(BODY), name="table_fixture")


def index():
    return NodeIndex(doc())


def codes(cmp):
    return [i.code for i in cmp.issues]


def hard(cmp):
    return [i.code for i in cmp.by_level("error")]


# ---------------------------------------------------------------
# A. 节点身份
# ---------------------------------------------------------------
def test_body_and_cell_node_ids():
    """顶层块 = b{seq}；单元格内 = b{i}.r{r}c{c}.n{k}。"""
    idx = index()
    assert [n.id for n in idx.nodes][:3] == ["b0", "b1.r0c0.n0", "b1.r0c0.n1"], \
        [n.id for n in idx.nodes]
    assert idx.text_of("b0") == "封面标题"
    assert idx.text_of("b1.r0c0.n0") == "知识精讲"
    assert idx.text_of("b1.r1c0.n1") == "1. 下列说法正确的是"
    assert idx.text_of("b2") == "文末说明"
    # 表格与单元格都是容器，不是内容节点
    assert idx.is_container("b1") and idx.is_container("b1.r0c0")
    assert not idx.is_container("b1.r0c0.n0")
    assert "b1" not in [n.id for n in idx.nodes]


def test_nested_table_node_ids():
    """嵌套表格：b1.r1c1.n0 是嵌套表，其单元格 = b1.r1c1.n0.r0c0。"""
    idx = index()
    assert idx.is_container("b1.r1c1.n0"), "嵌套表应为容器"
    assert idx.is_container("b1.r1c1.n0.r0c0"), "嵌套表单元格应为容器"
    assert idx.text_of("b1.r1c1.n0.r0c0.n0") == "嵌套单元格文本"
    # 容器父子关系
    assert idx.container_parent["b1.r1c1.n0"] == "b1.r1c1"
    assert idx.container_parent["b1.r1c1"] == "b1"
    assert idx.container_parent["b1"] == "body"


def test_container_expansion_and_legacy_int_spans():
    """容器端点自动展开；整数区间（旧 gold 写法）语义不变。"""
    idx = index()
    all_in_table = idx.interval("b1", "b1")
    assert "b1.r0c0.n0" in all_in_table
    assert "b1.r1c0.n3" in all_in_table
    assert "b1.r1c1.n0.r0c0.n0" in all_in_table        # 嵌套表也被展开
    assert "b0" not in all_in_table and "b2" not in all_in_table
    # 整数区间 [1,1] == 整张表（含单元格内全部内容）
    assert idx.interval(1, 1) == all_in_table
    # 单个节点展开为自身
    assert idx.expand("b1.r0c0.n0") == {"b1.r0c0.n0"}


def test_node_order_is_document_order():
    """节点文档序：body 顺序 + 表格行优先 + 单元格内子块顺序。"""
    idx = index()
    ids = [n.id for n in idx.nodes]
    assert ids.index("b0") < ids.index("b1.r0c0.n0")
    assert ids.index("b1.r0c0.n1") < ids.index("b1.r0c1.n0")
    assert ids.index("b1.r0c1.n0") < ids.index("b1.r1c0.n0")
    assert ids.index("b1.r1c0.n3") < ids.index("b1.r1c1.n0.r0c0.n0")
    assert ids.index("b1.r1c1.n0.r0c0.n0") < ids.index("b2")


# ---------------------------------------------------------------
# B. 「同一张表内，前半知识 / 后半题组」的标注与判定
# ---------------------------------------------------------------
def gold_table_split():
    """把表格拆成：知识（左上）／材料（右上）／题组（左下，绑定材料）／知识（嵌套格）／正文。"""
    return {"units": [
        {"id": "b0", "role": "body", "node": "b0"},
        {"id": "k1", "role": "knowledge", "node": "b1.r0c0",
         "note": "表格左上是知识精讲"},
        {"id": "m1", "role": "shared_material", "node": "b1.r0c1",
         "note": "表格右上是共享材料"},
        {"id": "g1", "role": "question_group", "node": "b1.r1c0",
         "bind_to": "m1", "note": "表格左下是题组（整体不可拆）"},
        {"id": "k2", "role": "knowledge", "node": "b1.r1c1.n0.r0c0",
         "note": "嵌套表格单元格"},
        {"id": "b2", "role": "body", "node": "b2"},
    ]}


def pred_table_partition():
    """程序结果：与 gold 一一对应的分块（同一张表被正确切开）。"""
    return [
        {"id": "P0", "role": "body", "node": "b0"},
        {"id": "P1", "role": "knowledge", "node": "b1.r0c0"},
        {"id": "P2", "role": "shared_material", "node": "b1.r0c1"},
        {"id": "P3", "role": "question_group", "node": "b1.r1c0", "bind_to": "P2"},
        {"id": "P4", "role": "knowledge", "node": "b1.r1c1.n0.r0c0"},
        {"id": "P5", "role": "body", "node": "b2"},
    ]


def test_table_internal_split_pass():
    """同一张表被正确切成 知识/材料/题组/嵌套格 → 无错误、无缺口。"""
    cmp = compare(doc(), gold_table_split(), pred_table_partition())
    assert cmp.verdict == "PASS", hard(cmp)
    assert cmp.summary["gold_gap_nodes"] == 0, codes(cmp)
    assert cmp.summary["content_nodes"] == 10     # b0 + 2 + 1 + 4 + 1(嵌套) + b2
    by_id = {u.id: u for u in cmp.gold_units}
    assert by_id["g1"].nodes == {"b1.r1c0.n0", "b1.r1c0.n1", "b1.r1c0.n2", "b1.r1c0.n3"}
    assert by_id["k2"].nodes == {"b1.r1c1.n0.r0c0.n0"}


def test_scope_anchor_inside_cell():
    """scope + anchor：在指定单元格内按文本定位。"""
    idx = index()
    gold = {"units": [
        {"id": "k", "role": "knowledge", "scope": "b1.r0c0", "anchor": "知识点一"},
        {"id": "g", "role": "question_group", "scope": "b1.r1c0", "anchor": "1. 下列说法"},
    ]}
    cmp = compare(doc(), gold, None)
    by_id = {u.id: u for u in cmp.gold_units}
    assert by_id["k"].anchor_matched == "b1.r0c0.n1"
    assert by_id["g"].anchor_matched == "b1.r1c0.n1"
    assert not [i for i in cmp.issues if i.code == "GOLD_ANCHOR"], codes(cmp)


def test_cell_split_detected_when_pred_merges_whole_table():
    """程序把整张表当一个块 → 题组与知识/材料被合并 → MERGE(warn) + 角色降级。"""
    cmp = compare(doc(), gold_table_split(), [
        {"id": "P0", "role": "body", "node": "b0"},
        {"id": "P1", "role": "body", "node": "b1"},        # 整张表一个块
        {"id": "P2", "role": "body", "node": "b2"},
    ])
    assert "MERGE" in [i.code for i in cmp.by_level("warn")], codes(cmp)
    assert "MISSED_STRUCTURE" in codes(cmp)
    # 整表覆盖，因此不应有遗漏
    assert "OMISSION" not in hard(cmp)


def test_question_group_split_inside_table_cell():
    """题组在单元格内被拆成两块 → GROUP_SPLIT。"""
    pred = pred_table_partition()
    pred = [p for p in pred if p["id"] != "P3"]
    pred.insert(3, {"id": "P3a", "role": "question_group",
                    "spans": [["b1.r1c0.n0", "b1.r1c0.n1"]], "bind_to": "P2"})
    pred.insert(4, {"id": "P3b", "role": "question_group",
                    "spans": [["b1.r1c0.n2", "b1.r1c0.n3"]], "bind_to": "P2"})
    cmp = compare(doc(), gold_table_split(), pred)
    assert "GROUP_SPLIT" in hard(cmp), codes(cmp)
    assert [i for i in cmp.issues if i.code == "GROUP_SPLIT"][0].subject == "g1"


def test_omission_inside_nested_table():
    """嵌套表格单元格被程序漏掉 → OMISSION（涉及节点是嵌套路径）。"""
    pred = [p for p in pred_table_partition() if p["id"] != "P4"]
    cmp = compare(doc(), gold_table_split(), pred)
    assert "OMISSION" in hard(cmp)
    iss = [i for i in cmp.issues if i.code == "OMISSION"][0]
    assert iss.subject == "k2"
    assert "b1.r1c1.n0.r0c0.n0" in iss.nodes


def test_unbound_inside_table():
    """材料与题组被分到不同程序单元且未声明绑定 → UNBOUND（表格内部场景）。"""
    pred = pred_table_partition()
    pred[3].pop("bind_to")           # 程序不再声明绑定
    cmp = compare(doc(), gold_table_split(), pred)
    # 材料(P2: b1.r0c1) 与题组(P3: b1.r1c0) 在相邻单元格、分属两个程序单元
    assert "UNBOUND" in hard(cmp), codes(cmp)


def test_reorder_inside_table_not_error():
    """表格内部单元被重排（多片段/乱序输出）→ 不判错，只提示 ORDER_CHANGE。"""
    pred = pred_table_partition()
    # 把题组与材料对调输出顺序（节点集合不变）
    pred = [pred[0], pred[1], pred[3], pred[2], pred[4], pred[5]]
    cmp = compare(doc(), gold_table_split(), pred)
    assert cmp.verdict == "PASS", hard(cmp)
    assert "ORDER_CHANGE" in codes(cmp)


def test_gold_node_ref_error_reported():
    """gold 引用了不存在的节点 → GOLD_ANCHOR(info)，不崩溃。"""
    gold = {"units": [{"id": "x", "role": "knowledge", "node": "b99.r0c0"}]}
    cmp = compare(doc(), gold, None)
    assert "GOLD_ANCHOR" in codes(cmp)


def test_pred_bad_ref_is_hard_error():
    """程序单元引用不存在/引用失败 → PRED_ANCHOR(error)。"""
    cmp = compare(doc(), gold_table_split(), [
        {"id": "P0", "role": "body", "node": "b0"},
        {"id": "P1", "role": "body", "spans": [["b1.r9c9.n0", "b1.r9c9.n1"]]},
    ])
    assert "PRED_ANCHOR" in hard(cmp)


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

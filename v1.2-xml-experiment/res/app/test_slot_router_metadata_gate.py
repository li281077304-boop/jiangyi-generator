from pathlib import Path
import sys
from types import SimpleNamespace

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))

from slot_router import _is_cover_metadata_table, _make_units  # noqa: E402
from struct_doc import Block, Cell, TableBlock  # noqa: E402


def _table(rows):
    table_rows = [[Cell(text=value) for value in row] for row in rows]
    text = "\n".join(" | ".join(cell.text for cell in row) for row in table_rows)
    return Block(seq=0, pno=None, kind="table", text=text,
                 table=TableBlock(rows=table_rows, text=text))


def _snapshot(blocks, unit_span):
    class Index:
        def order_of(self, node_id):
            return int(str(node_id).split(".", 1)[0][1:])

        def interval(self, start, end):
            return ["b%d" % seq for seq in range(
                self.order_of(start), self.order_of(end) + 1)]

        def text_of(self, node_id):
            return blocks[self.order_of(node_id)].text

    return SimpleNamespace(
        document=SimpleNamespace(blocks=blocks), node_index=Index(),
        units=[{"id": "u1", "role": "question_group", "spans": [unit_span]}],
    )


def test_only_exact_two_field_cover_table_is_excluded():
    assert _is_cover_metadata_table(_table([
        ["教学目标", "能掌握本专题的核心方法。"],
        ["教学重难点", "重点：方法；难点：应用。"],
    ]))


def test_full_difficulty_label_alias_is_excluded_consistently():
    assert _is_cover_metadata_table(_table([
        ["教学目标", "能掌握本专题的核心方法。"],
        ["教学重点难点", "函数建模与应用。"],
    ]))


def test_question_table_that_mentions_metadata_labels_is_not_excluded():
    assert not _is_cover_metadata_table(_table([
        ["实验数据", "请阅读教学目标与重点难点评价表，回答问题。"],
        ["1.9", "2.9"],
    ]))


def test_mixed_body_rows_prevent_whole_table_metadata_exclusion():
    assert not _is_cover_metadata_table(_table([
        ["教学目标", "了解电路规律。"],
        ["教学重难点", "分析实验方法。"],
        ["问题", "根据下表计算电压。"],
    ]))


def test_cover_table_shape_inside_body_is_not_reclassified_as_cover_group():
    blocks = [
        Block(seq=0, pno=1, kind="paragraph", text="1. source question"),
        _table([
            ["教学目标", "能掌握本专题的核心方法。"],
            ["教学重难点", "重点：方法；难点：应用。"],
        ]),
    ]
    blocks[1].seq = 1
    snapshot = _snapshot(blocks, ["b1", "b1"])

    units = _make_units(snapshot)

    assert units[0].role == "question_group"

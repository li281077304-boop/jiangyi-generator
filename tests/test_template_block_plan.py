from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

import template_block_plan as planner  # noqa: E402


def _block(seq, text="", kind="paragraph"):
    return SimpleNamespace(seq=seq, kind=kind, text=text, images=[], oles=[],
                           math_count=0, textbox_texts=[])


def _snapshot(blocks, units):
    orders = {"b%d" % i: i for i in range(len(blocks))}
    index = SimpleNamespace(resolve_ref=lambda node_id: node_id if node_id in orders else None,
                            order_of=lambda node_id: orders.get(node_id))
    return SimpleNamespace(document=SimpleNamespace(blocks=blocks), units=units,
                           node_index=index, source_sha256="source-hash")


def _setup_plan_inputs(tmp_path, monkeypatch, blocks, units):
    source = tmp_path / "source.docx"
    source.write_bytes(b"source fixture")
    template = tmp_path / "template.docx"
    document = Document()
    document.add_table(rows=1, cols=1)
    document.save(template)
    monkeypatch.setattr(planner, "resolve_template", lambda _kind: (template, "template-hash"))
    monkeypatch.setattr(planner, "analyze_source", lambda _source: _snapshot(blocks, units))
    return source


def test_projection_unions_overlapping_units_once_in_source_order(tmp_path, monkeypatch):
    blocks = [_block(0, "one"), _block(1, "two"), _block(2, "table", "table"), _block(3, "four")]
    units = [
        {"id": "unit-a", "role": "question_group", "parent": "section-a",
         "bind_to": "material-a", "spans": [["b0", "b2"]], "evidence": "a"},
        {"id": "unit-b", "role": "body", "parent": None,
         "bind_to": None, "spans": [["b2", "b3"]], "evidence": "b"},
    ]
    source = _setup_plan_inputs(tmp_path, monkeypatch, blocks, units)

    plan = planner.build_template_block_plan(source, "class")

    assert [span.start for span in plan.blocks] == ["b0", "b1", "b2", "b3"]
    assert [span.end for span in plan.blocks] == ["b0", "b1", "b2", "b3"]
    assert len({span.start for span in plan.blocks}) == 4
    assert plan.block_records[2]["unit_contributors"] == ("unit-a", "unit-b")
    assert plan.units[0]["role"] == "question_group"
    assert plan.units[0]["parent"] == "section-a"
    assert plan.units[0]["bind_to"] == "material-a"
    assert plan.target.body_child_index == 1


def test_uncovered_empty_structural_paragraph_is_retained_once(tmp_path, monkeypatch):
    blocks = [_block(0, "covered"), _block(1, ""), _block(2, "covered too")]
    units = [
        {"id": "first", "role": "body", "spans": [["b0", "b0"]]},
        {"id": "last", "role": "body", "spans": [["b2", "b2"]]},
    ]
    source = _setup_plan_inputs(tmp_path, monkeypatch, blocks, units)

    plan = planner.build_template_block_plan(source, "1v1")

    assert [span.start for span in plan.blocks] == ["b0", "b1", "b2"]
    assert plan.block_records[1]["unit_contributors"] == ("__structural_empty_gap__",)
    assert plan.structural_gap_count == 1


def test_unassigned_contentful_block_fails_closed(tmp_path, monkeypatch):
    blocks = [_block(0, "covered"), _block(1, "not covered"), _block(2, "covered too")]
    units = [
        {"id": "first", "role": "body", "spans": [["b0", "b0"]]},
        {"id": "last", "role": "body", "spans": [["b2", "b2"]]},
    ]
    source = _setup_plan_inputs(tmp_path, monkeypatch, blocks, units)

    with pytest.raises(planner.PlanUnsupported, match="content unassigned at b1"):
        planner.build_template_block_plan(source, "1v1")

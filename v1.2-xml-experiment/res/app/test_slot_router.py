# -*- coding: utf-8 -*-
"""Focused C1 Slot Router business-rule regressions."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from docx import Document

from semantic_facade import SemanticSnapshot
from slot_router import (
    SLOT_LABELS,
    SlotRoutingError,
    _number,
    build_slot_routing_plan,
)
from template_slot_composer import render_slots
from struct_doc import read_struct_doc_bytes
from struct_nodes import NodeIndex


class SlotRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c1-slot-router-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def _snapshot(self, blocks, units):
        path = self.root / "source.docx"
        document = Document()
        for block in blocks:
            if isinstance(block, tuple) and block[0] == "table":
                table = document.add_table(rows=0, cols=1)
                for value in block[1]:
                    table.add_row().cells[0].text = value
            else:
                document.add_paragraph(block)
        document.save(path)
        source = path.read_bytes()
        struct = read_struct_doc_bytes(source, name=path.name)
        index = NodeIndex(struct)
        return path, SemanticSnapshot(hashlib.sha256(source).hexdigest(), path.name,
                                      struct, index, units)

    @staticmethod
    def _unit(unit_id, role, start, end=None, *, parent=None, note=None,
              bind_to=None):
        return {
            "id": unit_id,
            "role": role,
            "spans": [[start, end or start]],
            "parent": parent,
            "note": note,
            "bind_to": bind_to,
        }

    def _practice_fixture(self, *, table=False, shared=False):
        if table:
            qtext = ["1. A", "2. B", "3. C", "4. D", "5. E",
                     "6. F", "7. G", "8. H", "9. I", "10. J",
                     "1. K", "2. L", "3. M", "4. N", "5. O"]
            blocks = ["题型01 练习讲解", "例题1：讲解", ("table", qtext)]
            node_ids = ["b2.r%d c0.n0" % index for index in range(15)]
            # StructDoc cell IDs use the row and column without whitespace.
            node_ids = [item.replace(" ", "") for item in node_ids]
            practice_ids = node_ids
        else:
            blocks = ["题型01 练习讲解", "例题1：讲解", "方法说明"] + [
                "%d. practice" % n for n in list(range(1, 11)) + list(range(1, 6))
            ]
            practice_ids = ["b%d" % seq for seq in range(3, 18)]
        units = [self._unit("s0", "section", "b0")]
        units.append(self._unit("e0", "question_group", "b1", parent="s0",
                                note="例1默认保留在知识讲解"))
        if shared:
            units.append(self._unit("m0", "shared_material", "b2", parent="s0"))
        qg_start = 0
        if shared:
            # The ordinary fixture reserves b2 for shared material and shifts
            # both practice blocks by one physical paragraph.
            blocks.insert(3, "材料：共用材料")
            practice_ids = ["b%d" % seq for seq in range(4, 19)]
            units[1] = self._unit("e0", "question_group", "b1", parent="s0",
                                  note="例1默认保留在知识讲解")
            units.append(self._unit("m0", "shared_material", "b3", parent="s0"))
            qg_start = 0
        for offset, node_id in enumerate(practice_ids):
            number = (offset % 10) + 1 if offset < 10 else (offset - 10) + 1
            units.append(self._unit("q%d" % offset, "question_group", node_id,
                                    parent="s0", bind_to="m0" if shared and offset in (0, 10) else None))
        return self._snapshot(blocks, units)

    def test_template_slot_labels_are_not_mixed(self):
        self.assertEqual(SLOT_LABELS["1v1"]["final"], "六、巩固练习")
        self.assertEqual(SLOT_LABELS["class"]["final"], "六、出门测试")
        self.assertEqual(SLOT_LABELS["1v1"]["knowledge"], "知识精讲")
        self.assertEqual(SLOT_LABELS["class"]["knowledge"], "知识精讲&例题讲解")

    def test_explicit_headings_override_implicit_selection_and_keep_mislabelled_answer(self):
        blocks = [
            "知识点01 有理数", "【答案】这里实际是知识讲解正文", "即时训练",
            "训练说明跟随即时训练", "1. 即时训练题", "六、巩固练习", "1. 巩固题", "2. 巩固题",
        ]
        units = [
            self._unit("s0", "section", "b0"),
            self._unit("a0", "answer", "b1", parent="s0"),
            self._unit("s1", "section", "b2"),
            self._unit("body1", "body", "b3"),
            self._unit("q1", "question_group", "b4", parent="s1"),
            self._unit("s2", "section", "b5"),
            self._unit("q2", "question_group", "b6", "b7", parent="s2"),
        ]
        path, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertTrue(plan.explicit_final_heading)
        self.assertEqual([s.start for s in plan.slots["knowledge"]], ["b0", "b1"])
        self.assertEqual([s.start for s in plan.slots["immediate"]], ["b2", "b3", "b4"])
        self.assertEqual([s.start for s in plan.slots["final"]], ["b5", "b6", "b7"])

    def test_composer_places_each_stream_after_its_template_anchor(self):
        for template_type in ("1v1", "class"):
            final_heading = ("六、巩固练习" if template_type == "1v1" else "六、出门测试")
            blocks = ["知识点01 有理数", "即时训练", "1. 即时训练题",
                      final_heading, "1. 巩固题"]
            units = [
                self._unit("s0", "section", "b0"),
                self._unit("s1", "section", "b1"),
                self._unit("q1", "question_group", "b2", parent="s1"),
                self._unit("s2", "section", "b3"),
                self._unit("q2", "question_group", "b4", parent="s2"),
            ]
            source, snapshot = self._snapshot(blocks, units)
            plan = build_slot_routing_plan(source, template_type, snapshot=snapshot)
            output = self.root / (template_type + ".docx")
            result = render_slots(str(source), plan, str(output))
            self.assertTrue(result.package_report["valid"])
            saved = Document(str(output))
            anchors = set(plan.slot_labels.values())
            found = {}
            for table in saved.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for index, paragraph in enumerate(cell.paragraphs):
                            text = paragraph.text.strip()
                            if text in anchors:
                                following = []
                                for candidate in cell.paragraphs[index + 1:]:
                                    candidate_text = candidate.text.strip()
                                    if candidate_text in anchors:
                                        break
                                    if candidate_text in {
                                        "知识点01 有理数", "即时训练", "1. 即时训练题",
                                        final_heading, "1. 巩固题",
                                    }:
                                        following.append(candidate_text)
                                found[text] = following
            self.assertIn("知识点01 有理数", found[plan.slot_labels["knowledge"]])
            self.assertEqual(found["即时训练"], ["1. 即时训练题"])
            self.assertEqual(found[plan.slot_labels["final"]], ["1. 巩固题"])
            self.assertEqual(set(found), set(plan.slot_labels.values()))

    def test_two_naturally_complete_blocks_route_whole_1_to_10_and_1_to_5(self):
        path, snapshot = self._practice_fixture()
        plan = build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        final = [span.start for span in plan.slots["final"]]
        immediate = [span.start for span in plan.slots["immediate"]]
        self.assertEqual(immediate, ["b%d" % seq for seq in range(3, 13)])
        self.assertEqual(final, ["b%d" % seq for seq in range(13, 18)])
        self.assertNotIn("b8", final)  # no split-off 6-10 fragment

    def test_number_gap_stays_whole_in_knowledge_and_later_complete_run_can_train(self):
        blocks = ["题型01 标题", "1. first candidate", "4. gapped candidate",
                  "变式1-1. variant A", "变式1-2. variant B"]
        units = [self._unit("s0", "section", "b0")]
        units.extend(self._unit("q%d" % seq, "question_group", "b%d" % seq,
                                parent="s0") for seq in range(1, 5))
        path, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertIn("b1", [span.start for span in plan.slots["knowledge"]])
        self.assertIn("b2", [span.start for span in plan.slots["knowledge"]])
        self.assertEqual([span.start for span in plan.slots["immediate"]], ["b3", "b4"])
        self.assertEqual(plan.slots["final"], ())

    def test_leading_number_parser_preserves_natural_question_numbers(self):
        self.assertEqual(_number("1. question"), (1, None))
        self.assertEqual(_number("10、 question"), (10, None))

    def test_shared_material_cannot_connect_practice_blocks_across_slots(self):
        path, snapshot = self._practice_fixture(shared=True)
        with self.assertRaises(SlotRoutingError) as raised:
            build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertEqual(raised.exception.reason_code, "SHARED_MATERIAL_SLOT_CONFLICT")

    def test_atomic_table_cannot_be_split_between_training_slots(self):
        path, snapshot = self._practice_fixture(table=True)
        with self.assertRaises(SlotRoutingError) as raised:
            build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertEqual(raised.exception.reason_code, "TABLE_SLOT_CONFLICT")

    def test_question_group_with_overlapping_knowledge_unit_fails_closed(self):
        blocks = ["题型01 练习讲解", "例题1：讲解", "1. question prompt",
                  "question knowledge paragraph", "question subpart", "2. next question",
                  "1. next natural block", "2. following question"]
        units = [
            self._unit("s0", "section", "b0"),
            self._unit("e0", "question_group", "b1", parent="s0",
                       note="例1默认保留在知识讲解"),
            self._unit("q1", "question_group", "b2", "b4", parent="s0"),
            self._unit("k1", "knowledge", "b3", parent="s0"),
            self._unit("q2", "question_group", "b5", parent="s0"),
            self._unit("q3", "question_group", "b6", parent="s0"),
            self._unit("q4", "question_group", "b7", parent="s0"),
        ]
        path, snapshot = self._snapshot(blocks, units)
        with self.assertRaises(SlotRoutingError) as raised:
            build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertEqual(raised.exception.reason_code, "SLOT_ROUTING_ATOMIC_BLOCK_CONFLICT")

    def test_mixed_destination_headings_inside_one_table_fail_closed(self):
        path, snapshot = self._snapshot(
            [("table", ["知识点01 有理数", "概念说明", "即时训练", "1. 训练题"])],
            [
                self._unit("s0", "section", "b0.r0c0.n0"),
                self._unit("body0", "body", "b0.r1c0.n0", parent="s0"),
                self._unit("s1", "section", "b0.r2c0.n0"),
                self._unit("q0", "question_group", "b0.r3c0.n0", parent="s1"),
            ],
        )
        with self.assertRaises(SlotRoutingError) as raised:
            build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertEqual(raised.exception.reason_code, "TABLE_SLOT_CONFLICT")


if __name__ == "__main__":
    unittest.main()

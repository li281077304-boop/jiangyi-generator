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
    _is_top_level_paragraph_node,
    build_slot_routing_plan,
    validate_training_pair_routes,
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

    def test_training_only_keeps_six_modules_and_routes_questions_across_three_slots(self):
        blocks = ["题型分组练", "题型01 物质的构成", "1. 题目一", "2. 题目二",
                  "题型02 分子热运动", "3. 题目三"]
        units = [self._unit("s0", "section", "b0")]
        units.append(self._unit("s1", "section", "b4"))
        units.extend(self._unit("q%d" % seq, "question_group", "b%d" % seq,
                                parent="s0" if seq in (2, 3) else "s1")
                      for seq in (2, 3, 5))
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        self.assertEqual(plan.knowledge_point_status, "NO_KNOWLEDGE_POINT")
        self.assertEqual(plan.omitted_slots, ())
        self.assertEqual(plan.training_split_strategy, "GROUPED_VERTICAL")
        self.assertEqual([span.start for span in plan.slots["knowledge"]], ["b0", "b1", "b2"])
        self.assertEqual([span.start for span in plan.slots["immediate"]], ["b3"])
        self.assertEqual([span.start for span in plan.slots["final"]], ["b4", "b5"])
        all_spans = [span.start for slot in SLOT_LABELS["1v1"] for span in plan.slots[slot]]
        self.assertEqual(len(all_spans), len(blocks))
        self.assertEqual(len(set(all_spans)), len(blocks))

        output = self.root / "training-only.docx"
        render_slots(str(source), plan, str(output))
        saved_text = "\n".join(paragraph.text for paragraph in Document(str(output)).paragraphs)
        saved_text += "\n" + "\n".join(cell.text for table in Document(str(output)).tables
                                               for row in table.rows for cell in row.cells)
        for module in ("一、课堂启动", "二、知识回顾", "知识精讲",
                       "即时训练", "五、归纳总结", "六、巩固练习"):
            self.assertIn(module, saved_text)
        self.assertIn("1. 题目一", saved_text)
        self.assertIn("1. 题目三", saved_text)

    def test_training_only_class_template_keeps_class_specific_final_heading(self):
        blocks = ["题型01 专题", "1. question one", "2. question two", "3. question three"]
        units = [self._unit("s0", "section", "b0")]
        units.extend(self._unit("q%d" % seq, "question_group", "b%d" % seq,
                                parent="s0") for seq in (1, 2, 3))
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "class", snapshot=snapshot)
        output = self.root / "training-only-class.docx"
        render_slots(str(source), plan, str(output))
        saved = Document(str(output))
        saved_text = "\n".join(p.text for p in saved.paragraphs)
        saved_text += "\n" + "\n".join(cell.text for table in saved.tables
                                            for row in table.rows for cell in row.cells)
        self.assertIn("知识精讲&例题讲解", saved_text)
        self.assertIn("即时训练", saved_text)
        self.assertIn("六、出门测试", saved_text)
        self.assertNotIn("六、巩固练习", saved_text)

    def test_atomic_measurement_table_decimals_are_not_question_starts(self):
        blocks = ["题型01 电压规律", "1. 说明测量目的",
                  ("table", ["L1两端电压/V", "1.9", "1.0", "2.9"]),
                  "根据表格说明测量结果", "2. 根据表格回答", "3. 比较两组数据"]
        units = [self._unit("s0", "section", "b0"),
                 self._unit("q1", "question_group", "b1", "b3", parent="s0"),
                 self._unit("table_heading", "section", "b2.r0c0.n0"),
                 self._unit("q2", "question_group", "b4", parent="s0"),
                 self._unit("q3", "question_group", "b5", parent="s0")]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        path, snapshot = self._snapshot(["paragraph", ("table", ["1.9"])], [])
        self.assertTrue(_is_top_level_paragraph_node(snapshot, "b0"))
        self.assertFalse(_is_top_level_paragraph_node(snapshot, "b1"))
        self.assertFalse(_is_top_level_paragraph_node(snapshot, "b1.r0c0.n0"))
        owners = [slot for slot, spans in plan.slots.items()
                  if any(span.start == "b2" for span in spans)]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0], "knowledge")

    def test_measurement_table_cell_label_follows_unique_enclosing_question(self):
        blocks = ["知识精讲", "电路基础", "即时训练", "实验题题干",
                  ("table", ["L1两端电压/V", "1.9", "1.0", "2.9"]),
                  "根据表格回答问题"]
        units = [self._unit("s_knowledge", "section", "b0"),
                 self._unit("s_immediate", "section", "b2"),
                 self._unit("q1", "question_group", "b3", "b5", parent="s_immediate"),
                 self._unit("cell_label", "section", "b4.r0c0.n0")]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        self.assertTrue(any(span.start == "b4" for span in plan.slots["immediate"]))
        self.assertFalse(any(span.start == "b4" for slot in ("knowledge", "final")
                             for span in plan.slots[slot]))

    def test_training_only_two_question_group_keeps_whole_questions_without_fabricating_final(self):
        blocks = ["题型01 物质构成", "1. question one", "2. question two"]
        units = [self._unit("s0", "section", "b0"),
                 self._unit("q1", "question_group", "b1", parent="s0"),
                 self._unit("q2", "question_group", "b2", parent="s0")]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "class", snapshot=snapshot)
        self.assertEqual(plan.training_split_strategy, "GROUPED_VERTICAL")
        self.assertEqual([span.start for span in plan.slots["knowledge"]], ["b0", "b1"])
        self.assertEqual([span.start for span in plan.slots["immediate"]], ["b2"])
        self.assertEqual(plan.slots["final"], ())
        self.assertEqual(plan.slot_labels["final"], "六、出门测试")

    def test_mostly_singleton_type_groups_use_stable_degraded_balance(self):
        blocks = []
        units = []
        for number in range(1, 7):
            section_seq = len(blocks)
            blocks.append("题型%02d 专题" % number)
            units.append(self._unit("s%d" % number, "section", "b%d" % section_seq))
            question_seq = len(blocks)
            blocks.append("%d. question" % number)
            units.append(self._unit("q%d" % number, "question_group", "b%d" % question_seq,
                                    parent="s%d" % number))
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        self.assertEqual(plan.training_split_strategy, "GROUPED_DEGRADED")
        self.assertEqual(len(plan.slots["knowledge"]), 4)
        self.assertEqual(len(plan.slots["immediate"]), 4)
        self.assertEqual(len(plan.slots["final"]), 4)
        assigned_questions = [span.start for slot in ("knowledge", "immediate", "final")
                              for span in plan.slots[slot] if span.start in
                              {"b%d" % i for i in (1, 3, 5, 7, 9, 11)}]
        self.assertEqual(len(assigned_questions), 6)
        self.assertEqual(len(set(assigned_questions)), 6)

    def test_unheaded_question_groups_use_sequential_degraded_routing(self):
        blocks = ["1. q1", "2. q2", "3. q3", "4. q4", "5. q5", "6. q6"]
        units = [self._unit("q%d" % index, "question_group", "b%d" % index)
                 for index in range(len(blocks))]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        self.assertEqual(plan.training_split_strategy, "SEQUENTIAL_DEGRADED")
        self.assertEqual([len(plan.slots[slot]) for slot in ("knowledge", "immediate", "final")],
                         [2, 2, 2])
        self.assertEqual(sum(len(plan.slots[slot]) for slot in ("knowledge", "immediate", "final")), 6)

    def test_unheaded_sequential_route_carries_each_question_body_with_its_start(self):
        blocks = ["1. first", "continuation one", "2. second", "continuation two",
                  "3. third", "continuation three"]
        units = [self._unit("q1", "question_group", "b0", "b1"),
                 self._unit("q2", "question_group", "b2", "b3"),
                 self._unit("q3", "question_group", "b4", "b5")]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        routed = {int(span.start[1:]): slot for slot, spans in plan.slots.items()
                  for span in spans}
        self.assertEqual(plan.training_split_strategy, "SEQUENTIAL_DEGRADED")
        self.assertEqual([routed[index] for index in range(6)],
                         ["knowledge", "knowledge", "immediate", "immediate", "final", "final"])

    def test_teacher_student_routes_use_shared_question_markers_when_qg_counts_differ(self):
        blocks = ["题型01 专题", "1. question one", "2. question two",
                  "3. question three", "4. question four"]
        teacher_units = [self._unit("s0", "section", "b0")]
        teacher_units.extend(self._unit("t%d" % number, "question_group", "b%d" % number,
                                        parent="s0") for number in range(1, 5))
        student_units = [self._unit("s0", "section", "b0"),
                         self._unit("s1", "question_group", "b1", parent="s0"),
                         self._unit("s2", "question_group", "b2", "b3", parent="s0"),
                         self._unit("s3", "question_group", "b4", parent="s0")]
        teacher_path, teacher_snapshot = self._snapshot(blocks, teacher_units)
        student_path, student_snapshot = self._snapshot(blocks, student_units)
        teacher = build_slot_routing_plan(teacher_path, "1v1", snapshot=teacher_snapshot)
        student = build_slot_routing_plan(student_path, "1v1", snapshot=student_snapshot)
        self.assertEqual(teacher.training_split_strategy, "GROUPED_VERTICAL")
        self.assertEqual(student.training_split_strategy, "GROUPED_VERTICAL")
        self.assertEqual(teacher.training_question_routes, student.training_question_routes)
        self.assertEqual(teacher.training_question_routes,
                         ((1, "knowledge"), (2, "immediate"),
                          (3, "final"), (4, "final")))
        validate_training_pair_routes({"teacher": teacher, "student": student})

    def test_paired_training_route_mismatch_fails_closed(self):
        from types import SimpleNamespace
        plans = {
            "teacher": SimpleNamespace(training_question_routes=((1, "knowledge"),)),
            "student": SimpleNamespace(training_question_routes=((1, "immediate"),)),
        }
        with self.assertRaises(SlotRoutingError) as raised:
            validate_training_pair_routes(plans)
        self.assertEqual(raised.exception.reason_code, "TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH")

    def test_explicit_knowledge_section_remains_knowledge_point_lesson(self):
        blocks = ["知识点 一元一次方程", "1. 解方程", "即时训练", "1. 练习题"]
        units = [self._unit("s0", "section", "b0"),
                 self._unit("q0", "question_group", "b1", parent="s0"),
                 self._unit("s1", "section", "b2"),
                 self._unit("q1", "question_group", "b3", parent="s1")]
        source, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(source, "1v1", snapshot=snapshot)
        self.assertEqual(plan.knowledge_point_status, "KNOWLEDGE_POINT_PRESENT")
        self.assertEqual(plan.omitted_slots, ())
        self.assertIn("b0", [span.start for span in plan.slots["knowledge"]])

    def test_two_naturally_complete_blocks_route_whole_1_to_10_and_1_to_5(self):
        path, snapshot = self._practice_fixture()
        plan = build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        final = [span.start for span in plan.slots["final"]]
        immediate = [span.start for span in plan.slots["immediate"]]
        self.assertEqual(immediate, ["b%d" % seq for seq in range(3, 13)])
        self.assertEqual(final, ["b%d" % seq for seq in range(13, 18)])
        self.assertNotIn("b8", final)  # no split-off 6-10 fragment

    def test_number_gap_without_knowledge_point_stays_whole_in_training_slot(self):
        blocks = ["题型01 标题", "1. first candidate", "4. gapped candidate",
                  "变式1-1. variant A", "变式1-2. variant B"]
        units = [self._unit("s0", "section", "b0")]
        units.extend(self._unit("q%d" % seq, "question_group", "b%d" % seq,
                                parent="s0") for seq in range(1, 5))
        path, snapshot = self._snapshot(blocks, units)
        plan = build_slot_routing_plan(path, "1v1", snapshot=snapshot)
        self.assertEqual(plan.knowledge_point_status, "NO_KNOWLEDGE_POINT")
        self.assertEqual(plan.training_split_strategy, "GROUPED_VERTICAL")
        self.assertEqual([span.start for span in plan.slots["knowledge"]], ["b0", "b1"])
        self.assertEqual([span.start for span in plan.slots["immediate"]], ["b2"])
        self.assertEqual([span.start for span in plan.slots["final"]], ["b3", "b4"])

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

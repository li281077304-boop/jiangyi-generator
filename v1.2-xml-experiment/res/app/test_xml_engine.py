# -*- coding: utf-8 -*-
"""Programmatic build-path checks for the v1.2 XML experiment."""
import os
import sys
import tempfile
import unittest
from unittest import mock

from docx import Document

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xml_engine


class XmlEngineBuildTests(unittest.TestCase):
    def _documents(self, directory):
        source_path = os.path.join(directory, "source.docx")
        template_path = os.path.join(directory, "template.docx")
        output_path = os.path.join(directory, "output.docx")

        source = Document()
        source.add_paragraph("SOURCE FIRST")
        table = source.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "SOURCE TABLE"
        source.add_paragraph("SOURCE LAST")
        source.save(source_path)

        template = Document()
        template.add_paragraph("知识精讲")
        template.save(template_path)
        return source_path, template_path, output_path

    def test_build_uses_block_importer_and_validates_saved_package(self):
        with tempfile.TemporaryDirectory() as directory:
            source, template, output = self._documents(directory)
            blocks = [("知识精讲", 1, 2)]
            with mock.patch.object(xml_engine, "split_ideal", return_value=blocks):
                used, stats = xml_engine.build(source, template, output)

            self.assertEqual(used, blocks)
            self.assertTrue(os.path.isfile(output))
            generated = Document(output)
            body_text = "".join(
                "".join(node.itertext())
                for node in generated.element.body.iter()
                if node.tag.endswith("}t")
            )
            self.assertIn("SOURCE FIRST", body_text)
            self.assertIn("SOURCE TABLE", body_text)
            self.assertIn("SOURCE LAST", body_text)
            self.assertEqual(stats["migration"]["unsupported"], [])
            self.assertTrue(stats["package_validation"]["valid"])

    def test_build_raises_and_removes_output_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source, template, output = self._documents(directory)
            blocks = [("知识精讲", 1, 2)]
            failed_report = {
                "valid": False, "errors": ["fixture dangling relationship"],
                "warnings": [], "stats": {},
            }
            with mock.patch.object(xml_engine, "split_ideal", return_value=blocks), \
                    mock.patch.object(xml_engine, "validate_package", return_value=failed_report):
                with self.assertRaises(xml_engine.PackageValidationError) as error:
                    xml_engine.build(source, template, output)

            self.assertFalse(os.path.exists(output))
            self.assertEqual(
                error.exception.report["package_validation"]["errors"],
                ["fixture dangling relationship"],
            )

    def test_build_fails_closed_when_split_returns_none_or_empty_blocks(self):
        for split_result in (None, [], [("知识精讲", 1)]):
            with self.subTest(split_result=split_result), tempfile.TemporaryDirectory() as directory:
                source, template, output = self._documents(directory)
                with mock.patch.object(xml_engine, "split_ideal", return_value=split_result), \
                        mock.patch.object(xml_engine, "validate_package") as validate:
                    with self.assertRaises(xml_engine.XMLGenerationError) as error:
                        xml_engine.build(source, template, output)

                self.assertEqual("split_failed", error.exception.report["code"])
                self.assertFalse(os.path.exists(output))
                validate.assert_not_called()

    def test_split_ideal_returns_failure_when_questions_have_no_recognized_numbers(self):
        paragraphs = [
            ("知识内容", None),
            ("【题型1】题型标题", None),
            ("未按编号格式标记的题目", None),
        ]

        self.assertIsNone(xml_engine.split_ideal(paragraphs))

        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source.docx")
            template = os.path.join(directory, "template.docx")
            output = os.path.join(directory, "output.docx")
            source_doc = Document()
            for text, _ in paragraphs:
                source_doc.add_paragraph(text)
            source_doc.save(source)
            template_doc = Document()
            template_doc.add_paragraph("知识精讲")
            template_doc.save(template)

            with mock.patch.object(xml_engine, "validate_package") as validate:
                with self.assertRaises(xml_engine.XMLGenerationError) as error:
                    xml_engine.build(source, template, output)

            self.assertEqual("split_failed", error.exception.report["code"])
            self.assertFalse(os.path.exists(output))
            validate.assert_not_called()

    def test_split_ideal_omits_empty_blocks_for_short_question_sets(self):
        for question_count in (1, 10, 11):
            with self.subTest(question_count=question_count):
                paragraphs = [("知识内容", None), ("【题型1】练习", None)]
                paragraphs.extend(
                    ("%s.（2024）题目%s" % (index, index), None)
                    for index in range(1, question_count + 1)
                )
                blocks = xml_engine.split_ideal(paragraphs, block_size=10)

                self.assertTrue(blocks)
                self.assertTrue(all(1 <= start <= end <= len(paragraphs)
                                    for _, start, end in blocks))
                if question_count <= 10:
                    self.assertEqual(["知识精讲", "即时训练"],
                                     [marker for marker, _, _ in blocks])
                    self.assertEqual(len(paragraphs), blocks[-1][2])
                else:
                    self.assertEqual(["知识精讲", "即时训练", "六、巩固练习"],
                                     [marker for marker, _, _ in blocks])

        heading_first = [("【题型1】练习", None), ("1.（2024）题目", None)]
        first_blocks = xml_engine.split_ideal(heading_first)
        self.assertEqual([("即时训练", 1, 2)], first_blocks)
        self.assertIsNone(xml_engine.split_ideal(heading_first, block_size=0))

    def test_build_fails_closed_when_template_anchor_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            source, template, output = self._documents(directory)
            blocks = [("缺失锚点", 1, 2)]
            with mock.patch.object(xml_engine, "split_ideal", return_value=blocks), \
                    mock.patch.object(xml_engine, "validate_package") as validate:
                with self.assertRaises(xml_engine.XMLGenerationError) as error:
                    xml_engine.build(source, template, output)

            self.assertEqual("missing_template_anchor", error.exception.report["code"])
            self.assertEqual("缺失锚点", error.exception.report["marker"])
            self.assertFalse(os.path.exists(output))
            validate.assert_not_called()

    def test_build_fails_closed_when_block_range_exceeds_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source, template, output = self._documents(directory)
            blocks = [("知识精讲", 1, 99)]
            with mock.patch.object(xml_engine, "split_ideal", return_value=blocks), \
                    mock.patch.object(xml_engine, "validate_package") as validate:
                with self.assertRaises(xml_engine.XMLGenerationError) as error:
                    xml_engine.build(source, template, output)

            self.assertEqual("invalid_block_range", error.exception.report["code"])
            self.assertEqual({
                "marker": "知识精讲", "start": 1, "end": 99,
                "available_paragraph_count": 2,
            }, {key: error.exception.report[key] for key in (
                "marker", "start", "end", "available_paragraph_count")})
            self.assertFalse(os.path.exists(output))
            validate.assert_not_called()


if __name__ == "__main__":
    unittest.main()

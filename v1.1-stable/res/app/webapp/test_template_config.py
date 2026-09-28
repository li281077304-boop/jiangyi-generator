# -*- coding: utf-8 -*-
import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import jobs


class TemplateConfigTests(unittest.TestCase):
    def test_class_template_points_to_existing_docx(self):
        self.assertTrue(os.path.isfile(config.CLASS_TEMPLATE))
        self.assertEqual(os.path.splitext(config.CLASS_TEMPLATE)[1].lower(), ".docx")

    def test_class_mode_selects_configured_class_template(self):
        self.assertEqual(jobs._select_template("class"), config.CLASS_TEMPLATE)


if __name__ == "__main__":
    unittest.main()

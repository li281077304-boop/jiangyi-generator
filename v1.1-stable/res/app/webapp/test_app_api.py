# -*- coding: utf-8 -*-
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
import jobs


class _IdleThread:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def start(self):
        return None


class AppApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_jobs_dir = jobs.JOBS_DIR
        jobs.JOBS_DIR = self.tempdir.name
        jobs.JOBS.clear()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def tearDown(self):
        jobs.JOBS.clear()
        jobs.JOBS_DIR = self.old_jobs_dir
        self.tempdir.cleanup()

    def _post_pair(self, mode="auto"):
        data = {
            "files": [
                (io.BytesIO(b"teacher"), "chapter_teacher.docx"),
                (io.BytesIO(b"student"), "chapter_student.docx"),
            ],
            "subject": "数学",
            "grade": "高一",
            "handout_type": "复习讲义",
            "academic_year": "2026-2027学年",
            "template_type": "1v1",
            "split_mode": "smart",
            "docx_mode": mode,
        }
        with mock.patch.object(app_module.threading, "Thread", _IdleThread):
            return self.client.post("/api/jobs", data=data,
                                    content_type="multipart/form-data")

    def test_two_docx_can_be_paired_or_processed_separately(self):
        paired = self._post_pair("auto")
        self.assertEqual(paired.status_code, 200)
        self.assertEqual(paired.get_json()["total"], 1)
        job_id = paired.get_json()["job_id"]
        self.assertEqual(jobs.JOBS[job_id]["options"]["docxMode"], "auto")
        self.assertEqual(len(jobs.JOBS[job_id]["filenames"]), 2)

        jobs.JOBS.clear()
        separate = self._post_pair("separate")
        self.assertEqual(separate.status_code, 200)
        self.assertEqual(separate.get_json()["total"], 2)

    def test_rejects_invalid_files_and_duplicate_names(self):
        invalid = self.client.post(
            "/api/jobs", data={"files": (io.BytesIO(b"x"), "notes.txt")},
            content_type="multipart/form-data")
        self.assertEqual(invalid.status_code, 400)

        duplicate = self.client.post(
            "/api/jobs", data={"files": [
                (io.BytesIO(b"a"), "same.docx"),
                (io.BytesIO(b"b"), "SAME.docx"),
            ]}, content_type="multipart/form-data")
        self.assertEqual(duplicate.status_code, 400)

    def test_running_job_is_returned_instead_of_starting_another(self):
        jobs.JOBS["active-job"] = {"status": "running", "result_zip": None}
        response = self.client.post(
            "/api/jobs", data={"files": (io.BytesIO(b"x"), "new.docx")},
            content_type="multipart/form-data")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["job_id"], "active-job")

    def test_job_list_hides_server_path(self):
        jobs.JOBS["finished"] = {
            "status": "done", "result_zip": os.path.join(self.tempdir.name, "out.zip"),
            "filenames": ["chapter.docx"], "items": [],
        }
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        item = response.get_json()["jobs"][0]
        self.assertNotIn("result_zip", item)
        self.assertFalse(item["has_result"])


class JobCompatibilityTests(unittest.TestCase):
    def test_stages_archive_member_under_ascii_name_for_word(self):
        with tempfile.TemporaryDirectory() as tempdir:
            source = os.path.join(tempdir, "legacy\ufffdname.docx")
            with open(source, "wb") as stream:
                stream.write(b"docx payload")

            staged = jobs._stage_docx_for_word(source, os.path.join(tempdir, "stage"), 1)

            self.assertEqual(os.path.basename(staged), "source_01.docx")
            self.assertNotIn("\ufffd", staged)
            with open(staged, "rb") as stream:
                self.assertEqual(stream.read(), b"docx payload")


if __name__ == "__main__":
    unittest.main()

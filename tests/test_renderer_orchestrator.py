from pathlib import Path
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from renderer_orchestrator import (  # noqa: E402
    FallbackRequired,
    RenderJob,
    render_xml_or_fallback,
)


def _write_bad_package(output_path):
    output = Path(output_path)
    output.write_bytes(b"bad-package")
    return {"output_path": str(output)}


class RendererOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "xml.docx"
        self.job = RenderJob("source.docx", str(self.output))
        self.calls = []

    def _fallback(self, job, reason):
        self.calls.append((job, reason))
        requested_output = Path(job.output_doc)
        requested_output.write_bytes(b"V0.9 whole-job output")
        return {"output_path": str(requested_output)}

    def test_supported_case_stays_xml_and_never_invokes_v09(self):
        def xml_render(_job):
            stage = Path(_job.output_doc)
            stage.write_bytes(b"XML output")
            return {"output_path": str(stage),
                    "resource_report": {"unsupported": []},
                    "package_report": {"valid": True, "errors": []}}

        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: {"supported": True},
            xml_render=xml_render,
            fallback=self._fallback,
            package_validator=lambda _path: {"valid": True, "errors": []},
        )
        self.assertEqual(result.renderer, "XML")
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(self.calls, [])

    def test_preexisting_destination_is_never_overwritten(self):
        self.output.write_bytes(b"keep-existing-file")
        with self.assertRaises(FileExistsError):
            render_xml_or_fallback(
                self.job,
                xml_preflight=lambda _job: True,
                xml_render=lambda _job: self.fail("render must not start for occupied output"),
                fallback=self._fallback,
            )
        self.assertEqual(self.output.read_bytes(), b"keep-existing-file")
        self.assertEqual(self.calls, [])

    def test_forced_unsupported_preflight_invokes_fallback_and_records_reason(self):
        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: {
                "supported": False,
                "reason_code": "UNSUPPORTED_REVISION_MARKUP",
                "detail": "fixture revision markup",
            },
            xml_render=lambda _job: self.fail("XML render must not run after unsupported preflight"),
            fallback=self._fallback,
        )
        self.assertEqual(result.renderer, "V0.9")
        self.assertEqual(result.fallback_reason, "UNSUPPORTED_REVISION_MARKUP")
        self.assertTrue(result.details["fallback_invoked"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1], "UNSUPPORTED_REVISION_MARKUP")

    def test_relationship_failure_routes_with_explicit_reason(self):
        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: True,
            xml_render=lambda _job: (_ for _ in ()).throw(
                FallbackRequired("UNSUPPORTED_RELATIONSHIP", "missing rId")),
            fallback=self._fallback,
        )
        self.assertEqual(result.fallback_reason, "UNSUPPORTED_RELATIONSHIP")
        self.assertEqual(self.calls[0][1], "UNSUPPORTED_RELATIONSHIP")

    def test_package_validator_failure_routes_to_v09(self):
        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: True,
            xml_render=lambda _job: _write_bad_package(_job.output_doc),
            fallback=self._fallback,
            package_validator=lambda _path: {"valid": False, "errors": ["invalid ZIP"]},
        )
        self.assertEqual(result.fallback_reason, "PACKAGE_VALIDATION_FAILED")
        self.assertTrue(self.output.is_file())
        self.assertEqual(self.output.read_bytes(), b"V0.9 whole-job output")

    def test_relationship_integrity_failure_has_relationship_reason(self):
        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: True,
            xml_render=lambda _job: _write_bad_package(_job.output_doc),
            fallback=self._fallback,
            package_validator=lambda _path: {
                "valid": False, "errors": ["dangling internal relationship rId8"]},
        )
        self.assertEqual(result.fallback_reason, "UNSUPPORTED_RELATIONSHIP")

    def test_render_fail_closed_routes_to_v09(self):
        result = render_xml_or_fallback(
            self.job,
            xml_preflight=lambda _job: True,
            xml_render=lambda _job: (_ for _ in ()).throw(ValueError("unexpected XML renderer failure")),
            fallback=self._fallback,
        )
        self.assertEqual(result.fallback_reason, "XML_RENDER_FAILED")


if __name__ == "__main__":
    unittest.main()

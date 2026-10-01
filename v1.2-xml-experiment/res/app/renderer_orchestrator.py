"""XML-first rendering with an explicit V0.9 whole-job fallback.

The fallback deliberately starts from the original source document. It does
not accept or forward V1.2 StructDoc spans. The frozen V0.9 engine scans and
splits the source itself before invoking its archived Writer path.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Optional
import importlib.util
import contextlib
import io
import json
import os
import sys
import uuid


APP_DIR = Path(__file__).resolve().parent
V09_RUNTIME_DIR = APP_DIR / "v09_fallback_runtime"
V09_BASELINE_SHA = "0922e08631226b95a77a6599bbc0ac3784e9134b"

REASON_CODES = {
    "UNSUPPORTED_REVISION_MARKUP",
    "UNSUPPORTED_BOOKMARK_SCOPE",
    "UNSUPPORTED_RELATIONSHIP",
    "PACKAGE_VALIDATION_FAILED",
    "XML_RENDER_FAILED",
}


class FallbackRequired(RuntimeError):
    """A known XML limitation that requires the V0.9 route."""

    def __init__(self, reason_code: str, detail: str = ""):
        if reason_code not in REASON_CODES:
            raise ValueError("unknown fallback reason code: %s" % reason_code)
        self.reason_code = reason_code
        self.detail = detail
        super().__init__("%s%s" % (reason_code, ": " + detail if detail else ""))


@dataclass(frozen=True)
class RenderJob:
    """Original user/job inputs required by either renderer."""

    source_doc: str
    output_doc: str
    template_type: str = "1v1"
    template_path: Optional[str] = None
    topic: str = ""
    objectives: str = ""
    difficulties: str = ""
    grade: str = ""
    subject: str = ""
    handout_type: str = ""
    label: str = "教师版"
    student_source_doc: Optional[str] = None
    student_output_doc: Optional[str] = None
    student_only: bool = False


@dataclass(frozen=True)
class RenderOutcome:
    renderer: str
    output_paths: tuple[str, ...]
    fallback_reason: Optional[str] = None
    xml_error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


def render_xml_or_fallback(
    job: RenderJob,
    *,
    xml_preflight: Callable[[RenderJob], Any],
    xml_render: Callable[[RenderJob], Any],
    fallback: Callable[[RenderJob, str], Any],
    package_validator: Optional[Callable[[str], dict[str, Any]]] = None,
) -> RenderOutcome:
    """Run XML if supported; otherwise invoke the V0.9 whole-job callback.

    ``xml_preflight`` may raise ``FallbackRequired`` or return ``False`` / a
    ``{"supported": false, "reason_code": ...}`` result. The XML callback
    must return an object with ``output_path`` (and may include
    ``resource_report`` / ``package_report``). Any fallback is recorded with
    its reason before the V0.9 callback is called.
    """
    final_output = Path(job.output_doc).resolve()
    if final_output.exists():
        raise FileExistsError("renderer requires a fresh output path: %s" % final_output)
    final_output.parent.mkdir(parents=True, exist_ok=True)
    staging_output = final_output.with_name(
        ".%s.xml-stage-%s.docx" % (final_output.stem, uuid.uuid4().hex))
    xml_job = replace(job, output_doc=str(staging_output))
    try:
        try:
            preflight = xml_preflight(job)
        except FallbackRequired:
            raise
        except Exception as exc:
            raise FallbackRequired("XML_RENDER_FAILED", "preflight error: %s" % exc) from exc
        if preflight is False:
            raise FallbackRequired("UNSUPPORTED_REVISION_MARKUP", "XML capability preflight rejected input")
        if isinstance(preflight, dict) and not preflight.get("supported", True):
            reason = preflight.get("reason_code", "UNSUPPORTED_REVISION_MARKUP")
            raise FallbackRequired(reason, str(preflight.get("detail", "XML capability preflight rejected input")))

        try:
            result = xml_render(xml_job)
        except FallbackRequired:
            raise
        except Exception as exc:
            raise FallbackRequired(_classify_xml_error(exc), str(exc)) from exc

        output = str(getattr(result, "output_path", "") or (result.get("output_path", "") if isinstance(result, dict) else ""))
        resource_report = getattr(result, "resource_report", None)
        package_report = getattr(result, "package_report", None)
        if isinstance(result, dict):
            resource_report = result.get("resource_report", resource_report)
            package_report = result.get("package_report", package_report)
        if not output or Path(output).resolve() != staging_output:
            raise FallbackRequired("XML_RENDER_FAILED", "XML renderer did not use its isolated staging output")
        if not staging_output.is_file() or staging_output.stat().st_size == 0:
            raise FallbackRequired("XML_RENDER_FAILED", "XML renderer did not produce a non-empty output")
        if resource_report and resource_report.get("unsupported"):
            raise FallbackRequired("UNSUPPORTED_RELATIONSHIP", json.dumps(resource_report["unsupported"], ensure_ascii=False))
        if package_report and not package_report.get("valid", False):
            raise FallbackRequired("PACKAGE_VALIDATION_FAILED", "; ".join(package_report.get("errors", [])[:5]))
        if package_validator is not None:
            try:
                validation = package_validator(str(staging_output))
            except Exception as exc:
                raise FallbackRequired("PACKAGE_VALIDATION_FAILED", str(exc)) from exc
            if not isinstance(validation, dict) or not validation.get("valid", False):
                validation = validation if isinstance(validation, dict) else {}
                errors = validation.get("errors", [])
                code = "UNSUPPORTED_RELATIONSHIP" if _relationship_integrity_error(errors) else "PACKAGE_VALIDATION_FAILED"
                raise FallbackRequired(code, "; ".join(errors[:5]))
        try:
            os.rename(staging_output, final_output)
        except OSError as exc:
            raise FallbackRequired("XML_RENDER_FAILED", "could not publish validated XML output: %s" % exc) from exc
        return RenderOutcome("XML", (str(final_output),), details={"preflight": preflight})
    except FallbackRequired as failure:
        # Only this unique per-call staging path is ours to remove. The final
        # requested destination was verified absent before starting.
        try:
            if staging_output.exists():
                staging_output.unlink()
        except OSError:
            pass
        # The reason is passed into the callback and returned on the outcome;
        # callers can persist it in a job event/log before exposing completion.
        result = fallback(job, failure.reason_code)
        paths = _output_paths(result)
        if not paths or any(not Path(path).is_file() or Path(path).stat().st_size == 0 for path in paths):
            raise RuntimeError("V0.9 whole-job fallback did not produce non-empty outputs (%s): %s" %
                               (failure.reason_code, failure))
        metadata = result if isinstance(result, dict) else {}
        return RenderOutcome("V0.9", paths, failure.reason_code, str(failure),
                             details={"fallback_invoked": True,
                                      "whole_job": bool(metadata.get("whole_job", False)),
                                      "baseline_sha": metadata.get("baseline_sha")})


def _classify_xml_error(exc: Exception) -> str:
    """Map the current XML renderer's fail-closed diagnostics to stable codes."""
    code = getattr(exc, "reason_code", None)
    if code in REASON_CODES:
        return code
    message = str(exc).lower()
    if "bookmark" in message or "hyperlink anchor" in message:
        return "UNSUPPORTED_BOOKMARK_SCOPE"
    if "relationship" in message or "resource import" in message or "package part" in message:
        return "UNSUPPORTED_RELATIONSHIP"
    if "package" in message or "validation" in message or "zip" in message:
        return "PACKAGE_VALIDATION_FAILED"
    if "tracked-change" in message or "revision" in message:
        return "UNSUPPORTED_REVISION_MARKUP"
    return "XML_RENDER_FAILED"


def _relationship_integrity_error(errors: list[str]) -> bool:
    return any(any(token in error.lower() for token in (
        "relationship", "relationship reference", "missing media", "embedding part")) for error in errors)


def _output_paths(result: Any) -> tuple[str, ...]:
    if isinstance(result, RenderOutcome):
        return result.output_paths
    if isinstance(result, dict):
        paths = result.get("output_paths") or ([result["output_path"]] if result.get("output_path") else [])
    elif isinstance(result, (tuple, list)):
        paths = list(result)
    else:
        paths = [getattr(result, "output_path", "")] if getattr(result, "output_path", "") else []
    return tuple(str(path) for path in paths if path)


def _load_v09_engine():
    """Load the byte-preserved V0.9 engine and its sibling TOC splitter."""
    if not (V09_RUNTIME_DIR / "handout.py").is_file():
        raise FileNotFoundError("frozen V0.9 fallback assets are missing: %s" % V09_RUNTIME_DIR)
    runtime_text = str(V09_RUNTIME_DIR)
    added_path = runtime_text not in sys.path
    if added_path:
        sys.path.insert(0, runtime_text)
    module_name = "_jiangyi_frozen_v09_handout"
    module = sys.modules.get(module_name)
    if module is None:
        spec = importlib.util.spec_from_file_location(module_name, V09_RUNTIME_DIR / "handout.py")
        if spec is None or spec.loader is None:
            raise ImportError("cannot load frozen V0.9 handout engine")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return module


def render_v09_whole_job(job: RenderJob, reason_code: str) -> dict[str, Any]:
    """Run the archived V0.9 source scan, split, and Writer for the full job.

    An optional paired student source is rendered as supplied by the user. If
    absent, the frozen V0.9 ``make_student`` path prepares it from the original
    source in a unique output-local scratch path, then the same V0.9
    scan/split/Writer chain renders it. No V1.2 block/span data is accepted.
    """
    if reason_code not in REASON_CODES:
        raise ValueError("fallback reason code is required")
    source = Path(job.source_doc).resolve()
    output = Path(job.output_doc).resolve()
    if not source.is_file():
        raise FileNotFoundError("original source document is missing: %s" % source)
    if source == output:
        raise ValueError("fallback output must not overwrite original source")
    if job.template_type not in ("1v1", "class"):
        raise ValueError("unsupported V0.9 template type: %s" % job.template_type)
    engine = _load_v09_engine()
    template = Path(job.template_path).resolve() if job.template_path else Path(
        engine.CLASS_TEMPLATE if job.template_type == "class" else engine.DEFAULT_TEMPLATE).resolve()
    if not template.is_file():
        raise FileNotFoundError("V0.9 template is missing: %s" % template)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError("V0.9 fallback requires a fresh output path: %s" % output)

    if job.student_only:
        with contextlib.redirect_stdout(io.StringIO()):
            _version, log = engine.build_version(
                "学生版", str(source), str(output), job.topic,
                template=str(template), template_type=job.template_type,
                objectives=job.objectives, difficulties=job.difficulties,
                grade=job.grade, subject=job.subject, handout_type=job.handout_type,
                fmt=True)
        _require_v09_output(output, log)
        return {"output_paths": [str(output)], "fallback_reason": reason_code,
                "logs": [str(log)], "baseline_sha": V09_BASELINE_SHA, "whole_job": True}

    student_output = Path(job.student_output_doc).resolve() if job.student_output_doc else output.with_name(
        output.stem + "-学生版.docx")
    if student_output in (source, output):
        raise ValueError("student fallback output must not alias source or teacher output")
    if student_output.exists():
        raise FileExistsError("V0.9 fallback requires a fresh student output path: %s" % student_output)

    outputs = []
    logs = []
    with contextlib.redirect_stdout(io.StringIO()):
        _version, log = engine.build_version(
            job.label, str(source), str(output), job.topic,
            template=str(template), template_type=job.template_type,
            objectives=job.objectives, difficulties=job.difficulties,
            grade=job.grade, subject=job.subject, handout_type=job.handout_type,
            fmt=True,
        )
    _require_v09_output(output, log)
    outputs.append(str(output))
    logs.append(str(log))

    if job.student_source_doc:
        student_source = Path(job.student_source_doc).resolve()
        if not student_source.is_file():
            raise FileNotFoundError("paired student source is missing: %s" % student_source)
        _version, student_log = engine.build_version(
            "学生版", str(student_source), str(student_output), job.topic,
            template=str(template), template_type=job.template_type,
            objectives=job.objectives, difficulties=job.difficulties,
            grade=job.grade, subject=job.subject, handout_type=job.handout_type, fmt=True)
        _require_v09_output(student_output, student_log)
        outputs.append(str(student_output))
        logs.append(str(student_log))
    else:
        # Preserve the V0.9 student preparation flow without editing the source.
        # Keep the derived input beside the isolated outputs: the host's TEMP
        # provider may return an 8.3/virtualized path that python-docx cannot
        # reopen after PowerShell COM has run.
        student_source = output.with_name(
            ".%s.v09-student-%s.docx" % (output.stem, uuid.uuid4().hex))
        with contextlib.redirect_stdout(io.StringIO()):
            engine.make_student(str(source), str(student_source))
        if not student_source.is_file() or student_source.stat().st_size == 0:
            raise RuntimeError("V0.9 make_student did not produce a source document")
        with contextlib.redirect_stdout(io.StringIO()):
            _version, student_log = engine.build_version(
                "学生版", str(student_source), str(student_output), job.topic,
                template=str(template), template_type=job.template_type,
                objectives=job.objectives, difficulties=job.difficulties,
                grade=job.grade, subject=job.subject, handout_type=job.handout_type, fmt=True)
        _require_v09_output(student_output, student_log)
        try:
            student_source.unlink()
        except OSError:
            pass
        outputs.append(str(student_output))
        logs.append(str(student_log))
    return {"output_paths": outputs, "fallback_reason": reason_code, "logs": logs,
            "baseline_sha": V09_BASELINE_SHA, "whole_job": True}


def _require_v09_output(path: Path, log: Any) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("V0.9 Writer did not produce a non-empty output: %s; log=%s" % (path, log))

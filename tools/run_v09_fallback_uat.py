r"""Force XML capability rejection and exercise archived V0.9 whole-job flow.

Example (PowerShell):
  C:\xml-uat\.venv\Scripts\python.exe tools\run_v09_fallback_uat.py `
    C:\xml-uat\stage3-expansion\sources\X006.docx 1v1 C:\xml-uat\b5-v09-fallback

The tool writes only into a new output directory. The source document is read
by the original V0.9 COM scanner and is never modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1] / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from package_validator import validate_package  # noqa: E402
from renderer_orchestrator import (  # noqa: E402
    FallbackRequired,
    RenderJob,
    render_v09_whole_job,
    render_xml_or_fallback,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_doc")
    parser.add_argument("template_type", choices=("1v1", "class"))
    parser.add_argument("output_dir")
    args = parser.parse_args()
    source = Path(args.source_doc).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not source.is_file():
        parser.error("source_doc does not exist")
    if output_dir.exists() and any(output_dir.iterdir()):
        parser.error("output_dir must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem
    output = output_dir / (stem + "-teacher.docx")
    student_output = output_dir / (stem + "-student.docx")
    job = RenderJob(
        source_doc=str(source), output_doc=str(output),
        template_type=args.template_type, topic=stem,
        label="教师版", student_output_doc=str(student_output),
    )

    result = render_xml_or_fallback(
        job,
        xml_preflight=lambda _job: {
            "supported": False,
            "reason_code": "UNSUPPORTED_REVISION_MARKUP",
            "detail": "B5 forced unsupported fixture; source remains unchanged",
        },
        xml_render=lambda _job: (_ for _ in ()).throw(AssertionError("XML path must not execute")),
        fallback=render_v09_whole_job,
        package_validator=validate_package,
    )
    report = {
        "gate": "FORCED_V09_WHOLE_JOB_FALLBACK",
        "source_doc": str(source),
        "template_type": args.template_type,
        "renderer": result.renderer,
        "fallback_reason": result.fallback_reason,
        "xml_error": result.xml_error,
        "outputs": [
            {"path": path, "bytes": Path(path).stat().st_size,
             "package_validation": validate_package(path)}
            for path in result.output_paths
        ],
        "details": result.details,
    }
    report_path = output_dir / "fallback_uat.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.renderer == "V0.9" and result.fallback_reason and all(
        item["package_validation"]["valid"] for item in report["outputs"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())

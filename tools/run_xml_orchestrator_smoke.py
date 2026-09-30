"""Run a real source through the XML-first orchestration without fallback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1] / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from package_validator import validate_package  # noqa: E402
from renderer_orchestrator import RenderJob, render_xml_or_fallback  # noqa: E402
from renderer_xml_minimal import BlockSpan, TemplateTarget, render_minimal  # noqa: E402
from struct_doc import read_struct_doc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_doc")
    parser.add_argument("template_doc")
    parser.add_argument("output_doc")
    args = parser.parse_args()
    source = Path(args.source_doc).resolve()
    template = Path(args.template_doc).resolve()
    output = Path(args.output_doc).resolve()
    if not source.is_file() or not template.is_file():
        parser.error("source and template must exist")
    struct = read_struct_doc(str(source))
    spans = [BlockSpan("b%d" % block.seq, "b%d" % block.seq) for block in struct.blocks]
    job = RenderJob(str(source), str(output), template_type="1v1", template_path=str(template))

    def xml_render(xml_job):
        return render_minimal(str(source), str(template), spans, xml_job.output_doc, TemplateTarget(0))

    result = render_xml_or_fallback(
        job,
        xml_preflight=lambda _job: {"supported": True},
        xml_render=xml_render,
        fallback=lambda _job, reason: (_ for _ in ()).throw(
            AssertionError("supported XML run unexpectedly invoked V0.9: %s" % reason)),
        package_validator=validate_package,
    )
    report = {
        "renderer": result.renderer,
        "fallback_reason": result.fallback_reason,
        "output": str(output),
        "bytes": output.stat().st_size,
        "package_validation": validate_package(str(output)),
        "fallback_invoked": False,
    }
    report_path = output.with_suffix(".orchestration.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.renderer == "XML" and result.fallback_reason is None and report["package_validation"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

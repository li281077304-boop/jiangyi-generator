# V0.9 Whole-Job Fallback

## Scope and preserved boundary

The XML path remains primary. `renderer_orchestrator.render_xml_or_fallback`
accepts the original source/job inputs, runs XML capability preflight and
rendering into a unique staging output, validates it, and only then publishes
the XML file at the requested path. A failed stage is removed before routing
the untouched requested path to
`render_v09_whole_job`. The fallback does not accept `BlockSpan`, StructDoc
IDs, V1.2 ranges, or any Splitter result.

The fallback loads the frozen V0.9 `handout.py` and calls its existing
`build_version` once for each requested output. With no user-supplied student
source, it also calls V0.9 `make_student` to prepare the student source. The
archived implementation then performs its own `_body_paragraphs` PowerShell
COM scan, V0.9 `auto_split`, `_run_version`, and original 1v1/class writer.
The original source is checked against the output path and is never used as an
output. Existing output destinations are rejected.

Copied V0.9 application assets, writer scripts, and templates are byte-preserved from commit
`0922e08631226b95a77a6599bbc0ac3784e9134b`; source Git blob IDs, SHA-256,
size, and original path are listed in
[`ASSET_MANIFEST.json`](../../../v1.2-xml-experiment/res/app/v09_fallback_runtime/ASSET_MANIFEST.json).
The runtime folder's `.gitattributes` preserves those bytes across Windows
line-ending settings and allows the archived source's pre-existing trailing
whitespace to remain intact.
The archived `_fill_com.ps1` and `_fill_class.ps1` are not edited. This
fallback uses the host's V1.2 Python runtime and its installed
`python-docx`; the V0.9 binary `res/python/**` runtime was excluded from Git by
the baseline archive and is not covered by this asset hash manifest. Archived
application-asset integrity can be reproduced with
`python tools/verify_v09_fallback_assets.py`; it compares each target file's
SHA-256 with the corresponding Git blob from the manifest's baseline commit.

## Stable fallback reasons

| Reason code | Trigger |
| --- | --- |
| `UNSUPPORTED_REVISION_MARKUP` | XML capability preflight rejects tracked/revision markup or explicitly signals unsupported input |
| `UNSUPPORTED_BOOKMARK_SCOPE` | XML rejects an incomplete/ambiguous bookmark or dependent anchor |
| `UNSUPPORTED_RELATIONSHIP` | XML resource migration or relationship/resource integrity check fails |
| `PACKAGE_VALIDATION_FAILED` | XML output package validation fails for a non-relationship package error |
| `XML_RENDER_FAILED` | XML renderer fails closed or produces no non-empty output |

`RenderOutcome.fallback_reason` is returned to the caller, and the fallback
callback receives the same code. Job orchestration must persist this field in
its job event/log; fallback is not silent.

## Verification

- Unit tests exercise the XML-success/no-fallback route, forced unsupported
  preflight, relationship failure, package validation failure, and renderer
  fail-closed routing.
- `tools/run_v09_fallback_uat.py` forces unsupported preflight and invokes the
  actual frozen V0.9 whole-job function on a caller-supplied real source. It
  creates teacher and student outputs under a new isolated directory and
  records package validation per output. This requires Windows PowerShell and
  a functioning registered Word/WPS COM provider; it is separate from XML
  normal-path operation.
- The current workbench's `/api/jobs` endpoint still returns HTTP 501 because
  its production job submission pipeline is not implemented. The orchestration
  function is the service boundary for that pipeline; connecting the endpoint
  is outside this fallback-only round.

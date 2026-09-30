# B5 Whole-Job Fallback UAT

**Result:** forced unsupported XML routed to the archived V0.9 whole-job flow
for both 1v1 and class templates.

## Actual application invocation

The UAT forced capability preflight to return
`UNSUPPORTED_REVISION_MARKUP`. The XML renderer callback was an assertion that
must not run. Each run returned `renderer=V0.9`, recorded the same reason code,
and generated both teacher and student outputs from the original X006 source.
The V0.9 engine's `build_version` performed the original COM paragraph scan,
V0.9 `auto_split`, and the archived writer call. With no paired student input,
the run also called the archived `make_student` workflow before scanning and
rendering the student document.

| Template | Output | Bytes | Package validation |
| --- | --- | ---: | --- |
| 1v1 | `X006-teacher.docx` | 2,909,775 | PASS |
| 1v1 | `X006-student.docx` | 2,254,757 | PASS |
| class | `X006-teacher.docx` | 3,635,362 | PASS |
| class | `X006-student.docx` | 3,006,029 | PASS |

Evidence reports and generated outputs are in isolated local UAT directories:

- `C:\xml-uat\b5-v09-fallback-x006-1v1-final3\fallback_uat.json`
- `C:\xml-uat\b5-v09-fallback-x006-class\fallback_uat.json`

The source was `C:\xml-uat\stage3-expansion\sources\X006.docx`; it was not
used as an output. The archived V0.9 application assets, writer scripts, and
templates match Git blobs from `0922e08631226b95a77a6599bbc0ac3784e9134b`,
verified by the repository-local `ASSET_MANIFEST.json` and an independent
SHA-256 comparison. The call used the host V1.2 Python runtime with
`python-docx` 1.2.0; the V0.9 binary `res/python/**` runtime is excluded from
Git and is not part of this hash claim.

The initial attempt exposed a GBK stdout encoding failure in archived
`_run_version` after the teacher output had been generated. The adapter now
captures the archived writer's console output in memory, without modifying the
V0.9 files. A follow-up attempt showed the host temporary path could not be
used for the derived student document; the adapter now places that uniquely
named derived source beside the isolated outputs and removes it after render.
The complete 1v1 and class runs passed after these adapter-only adjustments.

A separate real-source orchestration smoke used the same X006 source with the
XML callback bound to `render_minimal`. It returned `renderer=XML`, no fallback
reason, wrote a 2,833,183-byte DOCX, and passed package validation. The fallback
callback was an assertion and was not invoked. Its report is
`C:\xml-uat\b5-normal-path-x006-1v1.orchestration.json`.

This gate confirms actual V0.9 invocation and valid output packages. It is not
a separate WPS open/save/reopen/PDF cycle for these four fallback outputs;
Round 18's real application UAT evidence covers the six XML outputs.

## Protected regressions

- `tests/test_stage2_baseline.py`: **39 passed, 0 failed**.
- Stage3 approved GoldCompare on the protected Round 7 predictions: QG
  **408/408**, recall **100%**, `MISS=0`, `FP=0`, `MERGE=0`, `SPLIT=0`;
  sections **369/369** exact; subquestions **328/328** inside parents; no
  errors.
- Stage3 source predictions remain the protected A-Line baseline; this B-Line
  round changed no Splitter, StructDoc, Gold, or Stage3 files.

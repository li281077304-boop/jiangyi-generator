# Final Polish — first page and safe display renumbering

## STATUS

PASS for the requested XML DOCX / real WPS product gate. Base: `687fd9d650533edbc320227cdd6934f8d6a6abc9`, branch: `feature/v1.2-c4-release-engineering`. Two actual production Flask jobs generated the same clean paired physics sources through XML. Four physics outputs and eight page-one corpus outputs completed WPS Open → SaveAs → Close → Reopen → PDF. This is a scoped product result, not a release or Chief verdict.

## FIRST PAGE BEFORE → AFTER

Coordinates below are PDF text bounding-box Y from the top of page 1, in points, extracted directly by PyMuPDF without OCR. Frozen templates were opened read-only and exported by `KWPS.Application`, WPS 12.0.

| Template / evidence | Baseline Y | Before Y | Final generated Y | Delta from baseline |
|---|---:|---:|---:|---:|
| 1v1, real physics teacher and student | 396.928 | 443.728 | 396.928 | 0.000 |
| Class, real physics teacher and student | 453.449 | 477.689 in controlled two-line probe | 453.449 | 0.000 |
| 1v1, short / long source fields | 396.928 | — | 396.928 | 0.000 |
| Class, short / long source fields | 453.449 | — | 453.449 | 0.000 |
| 1v1, real X012 knowledge lesson | 396.928 | — | 398.369 | +1.441 |
| Class, real X012 knowledge lesson | 453.449 | — | 453.449 | 0.000 |

The original templates place this title around the middle of the first page, rather than at the page's bottom edge. The implementation follows the user's A2 definition: the actual frozen template coordinate is the reference. The final physics output matches it exactly. All 12 outputs keep the title on page 1; the largest observed deviation is 1.441pt, approximately 0.51mm. No runtime line-count or page-height prediction is used.

### Why fixed cover display budget

Full objectives/difficulties previously expanded the cover rows and shifted the first-page body. Runtime XML cannot reliably predict WPS wrapping. We measured the actual template cells and fonts, tested CJK text lengths and mixed text, and fixed a conservative display budget. Full semantic values remain separately stored.

| Template | Value-cell width | Formal font/size | Maximum logical lines per field | Maximum display-width units per line |
|---|---:|---|---:|---:|
| 1v1 | 446.3pt | 宋体 10.5pt | 1 | 76 |
| Class | 413.2pt | 宋体 11pt objectives / 10pt difficulties | 1 | 68 |

Chinese/fullwidth and ambiguous-width characters count as 2 units, ordinary narrow characters as 1, combining marks as 0; wide Latin `M/W/m/w/@` conservatively count as 2. WPS probes at 40 CJK characters for 1v1 and 36 for class retained the baseline. Wrapping at 42/38 characters changed it. The limits retain two CJK characters of headroom. Explicit two-line probes also shifted the baseline. Probe sources, WPS SaveAs copies, PDFs and exact measured results are retained.

The output copy locks only the two metadata row heights to their original WPS-rendered border geometry: 23.9/23.9pt (1v1) and 25.7/27.8pt (class). The template XML's `atLeast` minima are smaller than those rendered heights; locking the minima would shrink the layout. Font sizes, character spacing, page size and margins are preserved.

## FULL METADATA AND DISPLAY METADATA

The Job's `lesson_metadata` retains `objectives`, `difficulties`, `full_objectives`, and `full_difficulties`. `cover_display` contains the two projected values, the budget, `cover_metadata_compacted`, and per-field compaction methods. The XML cover uses only display values; it independently enforces the fixed budget even if a caller supplies a larger budget.

Existing offline rules produce a short display version directly. The real training source displays:

- Objectives: `掌握物质的构成题型方法；规范分析与解答。`
- Difficulties: `重点：物质的构成题型与方法；难点：条件分析与易错辨析。`

Explicit source fields use deterministic clause selection in source order, split on newline, semicolon, Chinese full stop and circled list markers. Complete clauses that fit are retained. Priority `重点：` and `难点：` clauses are selected before other material. If those clauses cannot fit, both labels remain and the abbreviated clauses end in `…`; the full originals remain in evidence. No AI summary is used.

## REAL WPS / PDF RESULT

Final production jobs:

- 1v1: `8b6884578b9b44cda4b3cbdabde8d31f`.
- Class: `712d44b306474bb483946268300bd705`.

Both finished `done`, `renderer_route=XML`, `student_preparation_route=BYPASS`, `fallback_phase=NONE`, `display_renumbering.status=DISPLAY_RENUMBER_APPLIED`. These jobs used the real Flask submission/service/generation path without mocked rendering. The uploads were a paired teacher/student source, so no student-preparation generation or COM generation was required. WPS COM was used afterward as the validation tool.

The page-one corpus comprised short explicit objectives, the actual training rule, a real X012 knowledge lesson, long explicit source objectives and long explicit priority difficulties, in both template types. Physics included both teacher and student; the other cases produced eight additional outputs. Direct PDF checks found the full display strings within their original metadata-cell bounds in 12/12 cases, in one line, with no clipping or overlap. First-page images and representative long-field/knowledge pages were visually inspected. The four physics picture-page snapshots also showed intact figures and answer relationships.

Every physics output, and its WPS SaveAs copy, passed package validation. Each published DOCX retained the exact bytes of every source main-story image/OLE resource. Source header/footer logos are not imported into the new template. WPS re-encodes/downsamples some PNGs during SaveAs, so post-WPS image byte/pixel equality is not claimed. WPS copies retained the original OLE bytes and the same 30 drawing-image references, 4 VML references and 4 OLE references as the published outputs; sampled exported pages showed the pictures normally.

## RENUMBER BEFORE → AFTER

The training route signature remains exactly the previous 34-question signature. Display renumbering occurs only after routing and paired signature validation, in the composer. A canonical source-occurrence map is built once for the pair, with role-specific source nodes and shared slot-local ordinals. Repeated original numbers are not used as unique IDs.

| Slot | Original visible numbers in source order | Display numbers |
|---|---|---|
| 3 | 1, 5, 10, 15, 18, 22, 26, 31 | 1–8 |
| 4 | 2, 6, 11, 16, 19, 23, 27, 32 | 1–8 |
| 6 | 3, 4, 7, 8, 9, 12, 13, 14, 17, 20, 21, 24, 25, 28, 29, 30, 33, 34 | 1–18 |

The Job persists `display_renumbering.status` and the full map for every slot. Each row records `source_occurrence`, `source_question_number`, `source_order`, `destination_slot`, `new_number`, and the teacher/student `source_nodes`.

If a later XML gate enters V0.9 whole-job fallback, the canonical map remains available for diagnosis, but its status becomes `DISPLAY_RENUMBER_NOT_APPLIED_FALLBACK`, with `applied=false` and the original status retained as `planned_status`. This avoids claiming that the untouched fallback writer applied XML presentation numbering. The job-service regression verifies this evidence correction; no new fallback generation or WPS run is claimed for it.

## TEACHER / STUDENT CONSISTENCY

The teacher source is clean corpus X008, SHA-256 `56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`; student source is X007, SHA-256 `fb08ccae04b5140607a67d3e80526efa7d9a96f787c9c558b1c9b6bd3ab26e2a`. Both hashes matched the immutable source manifest before upload.

An independent evidence check compared the complete source block stream in each slot with the published payload and with the WPS SaveAs payload, allowing only the mapped prefix digit replacement. All 260 teacher blocks and 141 student blocks matched exactly in each template, with no missing or repeated source block. Both presentations had the same 1–8 / 1–8 / 1–18 numbers and 34 questions total. Teacher answer labels remained 34; student answer labels remained 0, as in its original student source. Topic labels, child-question numbers, years, formulas and other body text were preserved. This paired-source test does not claim new Studentizer coverage.

## CROSS-REFERENCE / UNSAFE CASES

`第N题` references, including the obvious Chinese-numeral equivalent, disable renumbering for the entire paired job and record `DISPLAY_RENUMBER_SKIPPED_CROSS_REFERENCE`. The original numbers and references remain unchanged.

Question starts inside an atomic table, textbox, field, revision, hyperlink or otherwise unsupported prefix structure disable the paired transformation with `DISPLAY_RENUMBER_PARTIAL_UNSAFE_STRUCTURE`, `applied=false`. The implementation conservatively retains the whole document's original numbers; it does not perform a partial edit. A changed source SHA fails closed. The imported prefix is checked against its recorded original number before any digit edit.

Only the digits of a reliable direct top-level question prefix are replaced, including prefixes split across text runs. No paragraph-wide text replacement is used. `(1)` child questions, circled numbers, `题型01`, `例1`, `变式1-1`, years and ordinary table numbers are not renumbered. Knowledge-point lessons return `NOT_APPLICABLE`.

## WHAT CHANGED / WHAT WAS NOT CHANGED

Changes are limited to `lesson_metadata.py`, the existing `template_slot_composer.py`, and small job evidence/persistence integration in the web service, plus focused tests. A-Line, StructDoc, the training-only allocation algorithm, the XML importer, V0.9 assets and the frozen DOCX template files remain unchanged. Six modules remain present; modules 1, 2 and 5 retain their blank template regions. Class and 1v1 final labels remain distinct.

## TESTS

Final focused selection: **60 passed**. It covers full metadata preservation, deterministic compaction, priority difficulty clauses, caller budget enforcement, unchanged fonts/margins, six modules, unchanged route signatures, slot-local and paired numbering, repeated numbering starts, fragmented prefixes, subquestion/title exclusions, cross-reference refusal, field/table refusal, ordinary knowledge behavior, persistence and existing Product Integrity checks. Changed Python files compile; `git diff --check` passes. No new full Stage2/Stage3, release, EXE, restart or performance run is claimed.

## EVIDENCE / HEAD

Raw baseline/probe artifacts: `C:\xml-uat\final-polish-20261005`. Final UAT artifacts: `C:\xml-uat\final-polish-20261005\final`, including `production-jobs.json`, `all-wps.json`, `content-conservation.json`, `page1-positions.json`, `cover-bounds.json`, DOCX/PDF files and PNG snapshots. The compact checked-in evidence index is `docs/v2/integration/fixtures/FINAL_POLISH_GATE_2026-10-05.json`.

The implementation/report commit and final remote HEAD are recorded in the following Run Journal entry and completion response. No release tag is created. No independent Chief review was performed in this request; no Chief PASS is claimed.

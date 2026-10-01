# C2 Round 6 — Real Batch, WPS Product and Performance Evidence

Worker: GPT-6.1 (`gpt-6.1-sol`, actual invocation). Base:
`0dd1391ad2e003bef4ac2ab7e00cd4f44bcf494a`.
Round 5 received independent Codex GPT-6.1 Sol PASS. This evidence candidate
requires its own independent Chief review before `C2_BATCH_PASS` or a tag.
No production source, frozen core, approved Business Rules or source DOCX was
changed in this round.

## Evidence scope

Raw evidence, original-name input copies, outputs, scripts and WPS PDFs are
isolated under `C:\xml-uat\c2-round6-20261001-0822`. Corpus provenance is
`C:\xml-uat\stage3-expansion\baseline_inputs.json`. All 27 staged source
hashes still match that manifest. Files use their genuine original corpus
filenames and teacher/student pairs, not renamed copies of one topic.

`batch_uat.py` posts real multipart uploads through the production Flask API
and runs the real resolver, router, XML renderer and frozen COM functions.
Synchronous submission allows measurement. Logging wrappers forward original
functions. Only Case E injects one declared capability rejection for unchanged
X024 bytes. This is production API/integration evidence, not browser UI UAT.

## Cases A–F

| Case | Real sources / template | Outcome | XML / V0.9 items | DOCX outputs | Seconds | make_student calls | Exact COM script calls | Observed WPS starts |
|---|---|---|---|---:|---:|---:|---:|---:|
| A | X001/X004/X006/X023/X025 teachers; 1v1 | done, 5 items | 5 / 0 | 5 teacher + 5 student | 121.330 | 5 | 10 | 20 |
| B | X001+X002, X020+X019, X023+X021 genuine pairs; class | done, 3 items | 3 / 0 | 3 teacher + 3 student | 13.975 | 0 | 0 | 0 |
| C | X004 teacher, X009 student, X025+X024 pair; class | done, 3 items | 2 / 1 | 2 teacher + 3 student | 37.597 | 1 | 4 | 8 |
| D | X006 teacher, X019 student, X001+X002 pair in Chinese nested ZIP; 1v1 | done, 3 items | 3 / 0 | 2 teacher + 3 student | 29.154 | 1 | 2 | 4 |
| E | X003/X013/X021/X024 students; 1v1 | done, 4 items | 3 / 1 | 4 student | 16.025 | 0 | 2 | 4 |
| F | X002/X019 students + safe corrupt DOCX fixture; class | partial, 2 successful siblings + 1 error | 2 / 0 | 2 student | 3.811 | 0 | 0 | 0 |

All **32 output DOCX packages validate**. Case D recursively handles Chinese
names and two nested directories, pairs the genuine sources and ignores its
`~$` temporary entry. Case F preserves both successful files and the partial
job's Open/Download actions. Every result tree contains only readable topic
folders and DOCX files; no underscores or internal JSON/work/log directories.

Case C naturally rejects X009's bookmark scope and records
`UNSUPPORTED_BOOKMARK_SCOPE`; the other two items remain XML. Case E's external
hook raises a slot capability error labeled `UNSUPPORTED_REVISION_MARKUP`;
the existing orchestration classifies that generic preflight exception as
`XML_RENDER_FAILED` and records the underlying detail. The **actual frozen
V0.9 whole-job flow runs only for X024**. This evidence does not claim the
fixture's label is the final persisted reason code. No source was damaged to
force fallback, and no StructDoc ranges enter V0.9.

make_student times (seconds): A **24.015, 17.068, 17.349, 14.841, 13.899**;
C **17.831**; D **16.983**. Supplied pairs and student-only items invoke none.
Per-item total times and forwarding-call traces are in `case-A.json` through
`case-F.json` and `events-A.json` through `events-F.json`.

The script-call counts above are exact recorded invocations of frozen
PowerShell scripts. WPS counts are distinct PID/start-time instances observed
by 100 ms polling. WMI ProcessStartTrace was denied (`0x80041003`), so these
are sampled process starts, **not exact COM object activations**. Initial
processes are recorded separately; no process was killed for the measurement.

## Delivery

All six real ZIP download requests return HTTP 200 with nonempty ZIP bytes.
Open requests resolve the parent local results folder, including partial F.
The batch harness originally used an injected folder-opener recorder; a
separate Case B `/api/open` request subsequently invoked production
`os.startfile` and returned HTTP 200. This verifies the Windows open call,
not a visually inspected Explorer window. Outputs remain available independently
of ZIP delivery. This report makes no access-control/security claim about the
read-only `result_dir` API.

## Product / WPS UAT

`KWps.Application` performs normal open (no repair-mode request), SaveAs2 to a
new isolated DOCX, close, reopen and PDF export for **11 products**:

- 1v1: X001 teacher/derived student; X006 teacher/derived student;
  X023 teacher/derived student; X013 supplied student.
- class: X001 teacher/supplied X002 student;
  X023 teacher/supplied X021 student.

**11/11 round trips and readable nonempty PDFs pass. 11/11 saved DOCX packages
validate.** WPS paragraph, table, InlineShapes and Shapes counts are unchanged
between initial open and reopen. OMML/OLE package evidence is reported
separately from visible equations; WPS's OMaths API returns zero for these
selected files and is not used to claim all formula rendering is proved.
No observed automation error or repair path occurred; DisplayAlerts was
disabled, so this is not a human attestation about every possible dialog.

`pdf-inspection.json` records page/text/image counts and slot heading pages.
21 selected PDF pages were rendered and visually inspected in
`wps/contact-1.png` through `contact-3.png`, including physics circuit diagrams,
math equations/fractions, chemistry tables and teacher/student differences.
The three additional full-page inspections are `A-6-inspect-2.png`,
`B-4-inspect-2.png` and `A-7-inspect-34.png`: both template-specific knowledge
headings and the derived student's complete final practice block are visible.
Chemistry 1v1 and class products visibly place content under their respective
knowledge/immediate/final anchors; final chemistry blocks begin at
`变式1-1`, not a midway question number. Teacher answers/analysis are visible;
student counterparts show answer blanks and retain the question/table content.
No obvious missing diagram, broken table or garbled formula was seen on the
inspected pages. This is a page sample, not a human classroom-readiness verdict
or a visual check of every page.

`content_audit.py` independently examines all **30 XML outputs** at the known
structural slot positions. Each expected physical source block matches its
output block in tag, ordered text, formula text, paragraph/table and
drawing/pict/OLE counts. Every source block appears once; slot-internal source
order is retained. Whole-document counts equal source plus frozen template,
including merged content cells shared by multiple anchors. Thus supplied
teacher/student sources and derived student sources are preserved independently;
shared materials/tables are not duplicated, omitted or split by batching.
The semantic fingerprint verifies structural ordinal positions; it does not
search for the first matching text.

Some frozen-C1 plans legitimately have empty training/final slots (one
indivisible teaching/practice block). These are **not** relabeled as nonempty
three-slot examples or split midway to satisfy a ratio. X023 provides actual
nonempty three-slot evidence for both templates and both output versions.

## Same-machine V0.9 comparison

The same Case B sources and class teacher/student workload were run serially
through untouched `render_v09_whole_job`: **76.801 seconds** total;
per pair **35.255 / 17.371 / 23.566 seconds**, six valid outputs, zero
make_student calls, **12 exact COM script invocations / 24 observed WPS starts**.
XML Case B: **13.975 seconds**, six valid outputs, zero COM scripts/process
starts. Measured workload ratio is approximately **5.50×**. This comparison is
direct frozen whole-job sequential batching, not the old browser-upload flow.
It is one same-machine observation without a general speed guarantee. In
teacher-only A, frozen student conversion remains the measured COM cost.

## Protected regression and limits

Fresh Round 6 Stage2: **39/39**. Fresh Stage3 evidence under `stage3/`:
QG **408/408**, sections **369/369**, subquestions **328/328**, original-paper
recall **100%**, E1/E2/E3/E4 and MISS/FP/MERGE/SPLIT **0**; eight source hashes
match. Overall teacher/analysis QG exact-boundary rate remains **87.7%** and
is not presented as 100%. Frozen V0.9 assets **10/10** hash-match their baseline.
The combined focused resolver/backend/C1/Stage2/executed-JS gate was rerun:
**123 passed in 36.51 seconds**. The staged evidence diff check passes.
The diff from the C1 checkpoint contains only reviewed C2 resolver/backend/UI,
tests and evidence/journal, with no A-Line/B-Line/V0.9/C1 rules changes.

Remaining approval: independent **Codex GPT-6.1 Sol** review of this evidence
and overall C2 completion. No EXE, installer, release or updater work is included.

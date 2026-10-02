# C3 R15 — Scoped Chief PATCH follow-up

**Base:** `4a8ea86aeb95313e54cac74121c240dacbaa5d05`  
**Implementation commit:** `effa4f56859a53b808736561ea0ad9c18ef9b74f`  
**Branch:** `feature/v1.2-c3-studentizer-performance`

This report closes only the Chief's PATCH blockers. It does not claim the C3
final gate or repeat large stress, restart, corpus, Golden, or OOXML audits.

## Interrupted publication recovery

Before publishing, the job now persists the exact role-to-final-path plan and
the expected SHA-256 of each fully validated staged DOCX. Each role is
published with `os.replace`, package-validated, hashed, and marked in the job
record. If the process stops after a final file appears but before the job is
marked done, restart requeues the item, regenerates only its uncompleted
internal work, and adopts an existing final only when it is non-empty, package
valid, and matches the persisted publication hash. Previously published role
files are never overwritten or removed by exception cleanup. Completion still
requires all classified final outputs to pass package validation.

New interruption tests terminate the worker after the teacher final is
published and after both teacher/student finals are published but before
`done`. Startup recovery then completes the job in both cases, retaining the
pre-restart DOCX hashes and leaving only final DOCX files in the result folder.

## Preparation vs renderer fallback telemetry

Renderer refusal still invokes the untouched whole-job V0.9 route, but its
`make_student` call and telemetry now live in a separate
`renderer_fallback_preparation` record. The original `student_preparation`
route, elapsed timing, and COM/WPS observations remain unchanged. The focused
X008-like case verifies `XML_STUDENTIZER` remains `make_student_called=false`
and `com_used=false`, while renderer fallback separately records V0.9 route,
renderer reason, callable entry, elapsed time, and COM/WPS as unknown after
callable entry.

## Existing 27-source renderer denominator

No scan or manual audit was rerun. From the already observed exact IDs: 8 XML
logical items (5 C2 Case A items and 3 C2 Case B teacher+student pairs) cover
9 unique source IDs; the repeated X008 1/3/5 runs are 9 V0.9 logical-item
executions but only 1 unique source ID. On the 27 unique source denominator the
reported participation is **XML 9 / V0.9 1 / unmeasured 17**. Case B's three
logical items contain six source IDs; they are not counted as six logical
items. See the revised R13 and final machine-gate reports for the exact ID
list and limits.

## Machine checks

- Studentizer integration + existing restart harness: **30 passed**
- New publication boundary cases: teacher final published, and both role finals
  published before completion; both restart-and-complete successfully
- X008-like Studentizer then renderer refusal: preparation telemetry preserved
  separately from whole-job fallback telemetry
- `py_compile`: PASS
- `git diff --check`: PASS
- Broad final gate, Stage2/Stage3, performance, batch10/20, and continuous-job
  stress were not rerun in this scoped follow-up.

Independent Chief re-review of this PATCH follow-up is pending.

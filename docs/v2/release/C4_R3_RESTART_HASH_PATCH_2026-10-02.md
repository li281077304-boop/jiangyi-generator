# C4-R3 restart publication hash PATCH — 2026-10-02

## Chief blocker

Independent Chief review of implementation `8a71d19` found a restart edge
case. Startup recovery clears private renderer staging. A retry can regenerate
a valid DOCX package with identical document content but different ZIP entry
timestamps, which changes the package SHA-256. The old publication plan then
rejected the still-unpublished role even though its final path did not exist.

## Scoped repair

`JobService.record_publication_plan()` now refreshes the expected hash for an
existing publication plan only when both conditions hold:

1. the role is absent from the persisted `published` map; and
2. the planned final path does not exist.

Roles with a final file or a persisted published record keep their previous
hashes. The normal adoption path still validates the existing final DOCX and
requires its bytes to match the published hash (or the previously bound
expected hash). The patch does not change renderer behavior or any A/B/C-line
core.

## Focused restart evidence

The new test interrupts a paired job after the teacher DOCX is published. On
restart, the test regenerates valid teacher and student DOCX ZIP packages with
different timestamps. It verifies:

- the unpublished student hash differs from its original publication plan;
- only the missing student role is rebound to the new validated staging hash;
- the published teacher file and its hash remain byte-for-byte unchanged;
- the student role publishes and the job reaches `done`;
- the result directory contains only the two final DOCX files, with no
  publication temp files.

## Machine gate and limits

- C0 job service, batch job service, and Studentizer integration tests:
  **59 passed**.
- Changed Python `py_compile`: PASS.
- `workspace.js` Node syntax check: PASS.
- `git diff --check`: PASS.
- No EXE build, packaged run, browser, Word/WPS, or whole-job UAT was run.

The original cross-volume failure evidence and target-volume publication repair
are documented in `C4_R3_PUBLICATION_PATCH_2026-10-02.md`. The original Chief
verdict remains `PATCH`; this hash-recovery follow-up awaits Codex GPT-6.1 Sol
re-review. No C4/RC PASS is claimed.

- Base: `b09df4676db7d07b14b53835960c2efda62e623f`
- Implementation commit: `6ec7b6a2ec0d168ac874a0359f961b24ed56df39`

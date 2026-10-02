# C4 P0 — Recursive Output Integrity Fix

Date: 2026-10-02
Base: `e44c78260762ca09224630a4f1c890c00a3a7e11`

## Root cause carried forward

The Chief-reviewed root-cause report found a mixed failure: V0.9 whole-job generation expanded an input with one lecture-template sequence to an output with two; Restart C then re-ingested that published generated output and produced three sequences. The specific lineage and hashes are in `C4_P0_RECURSIVE_OUTPUT_ROOT_CAUSE_REPORT.md`. This fix does not modify the frozen V0.9 assets, Splitter, Slot Router rules, Studentizer, or rendering behavior.

## Changes

- Every accepted input snapshot now records original filename, direct-upload or ZIP-entry origin, runtime path, byte length, and SHA-256 in the job record. Batch children preserve the ZIP entry path.
- Before Studentizer/A-Line/Renderer work, input DOCX files are inspected. Multiple lecture-template title fingerprints or two complete template cycles fail closed with `POSSIBLE_GENERATED_OUTPUT_REINGESTION`; the job record retains the inspection evidence.
- Before publication, each staged teacher/student DOCX passes `PRODUCT_INTEGRITY_GATE`. The gate records source/output SHA-256, main-story paragraph and top-level block counts, text lengths, template fingerprints, repeated long paragraph sequences, source-block slot overlap, and expansion ratio.
- A second template title or a second complete template cycle fails with `PRODUCT_TEMPLATE_RECURSION`; repeated sequences of at least 12 non-empty paragraphs and 1,200 characters fail with `PRODUCT_REPEATED_BLOCK_SEQUENCE`; unresolved or cross-slot block overlap fails closed. Expansion above 2.0x is recorded as `PRODUCT_EXPANSION_SUSPECTED` warning for investigation, not an automatic rejection.
- Rejected outputs do not enter the publication plan and cannot be marked `done`.

## Scoped machine gate

Command:

```text
C:\xml-uat\.venv\Scripts\python.exe -m pytest tests/test_product_integrity.py tests/test_batch_job_service.py tests/test_c0_job_service.py tests/test_studentizer_integration.py -q
```

Result: **66 passed**. Coverage includes one-template source acceptance, recursive input rejection before renderer invocation, duplicated staged output rejection before publication, direct and ZIP-entry provenance, overlap rejection, expansion warning, and the C0/Batch/Studentizer integration regression set.

`py_compile` for the changed runtime and focused test files: PASS. `git diff --check`: PASS.

## Limits and release status

- No real DOCX was regenerated and no WPS/Word, restart, package build, or large/full regression was run in this fix round.
- The new gate is conservative and structural. It detects repeated template fingerprints and exact long paragraph runs; it does not prove semantic correctness of every individual block or stale metadata that lacks those structural signals. A real source/output review is still required before C4 can be restored.
- This fix blocks the confirmed recursive-template signatures from being published. It does not establish that V0.9 whole-job output is otherwise semantically correct.
- C1/C2/C3 package, batching, recovery, or XML mechanics evidence remains within its prior technical scope. Their evidence does not certify product-content integrity/release readiness until this gate is reviewed and applicable outputs are revalidated.
- C4 remains blocked pending independent Codex GPT-6.1 Sol review and later specifically authorized release work. No EXE, tag, WPS UAT, or Release PASS is claimed.

## Chief PATCH follow-up

The first implementation commit `d1a1cf60bdfa996dd5a86af44d404952386a0b4a` received a scoped Chief PATCH. The follow-up closes its four blockers:

- At execution start, the current input SHA-256 must equal the upload snapshot SHA-256. A missing or changed binding is persisted as `INPUT_PROVENANCE_HASH_MISMATCH` and rejected before Studentizer or rendering.
- Template title count is based on literal normalized occurrences, including multiple occurrences inside one paragraph.
- Every slot endpoint, including a single-point span, must resolve to the supported `bN` block coordinate; unresolved single points fail with `PRODUCT_SLOT_OVERLAP`.
- The actual final result file, including an interrupted publication target being adopted, is checked by `PRODUCT_INTEGRITY_GATE` after package/hash checks and before its publication record is accepted. If it fails, only a result file under this job's result directory whose bytes match the hash-bound publication candidate is removed.

New regressions cover input SHA mismatch, two title occurrences in one paragraph, unresolved single-point endpoint, and rejection/removal of an invalid pre-existing publication target. The scoped suites now report **70 passed**. `py_compile` and `git diff --check` pass. No WPS, restart pressure, release/package, or full repository suite was run.

A second Chief PATCH identified a final-file time-of-check/time-of-use window. The publication path now compares the staged/adoption candidate SHA, the SHA captured by the final integrity inspection, and a fresh SHA of the current result file before recording publication. Failure cleanup performs an immediate additional SHA check and leaves any file that no longer matches the hash-bound candidate untouched. Two regressions replace the file during the integrity call and verify both acceptance and rejection paths fail closed without deleting the replacement.

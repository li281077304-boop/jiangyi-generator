# C3 final machine gates — 2026-10-02

**Candidate:** `021d98903707eb022650acf961047f373c20e552`  
**Base:** `99c243cfd05790d2ab640d9ea93e1a5e87a8449b`  
**Branch:** `feature/v1.2-c3-studentizer-performance`

This is a machine-gate handoff, not the C3 final verdict. No R1–R8 audits,
Golden review, new OOXML work, or C3.5 large load tests were repeated. The only
code change in this gate is an evaluation-runner guard for an unindexed TOC
container in Stage2; production Splitter, StructDoc, Gold, and Business Rules
are unchanged.

## Final candidate gates

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | **397 passed, 7 subtests passed, 4 failed** in 219.16 s. The four failures are the known `v1.1-stable` API expectations: `has_result`, three upload status expectations (`400`/`409`/`200` vs actual `415`). R13 recorded the same four failures on both its base and candidate. Do not call the full suite green. | Full pytest run after the Stage2 guard |
| Studentizer focused | **143 passed** | `tests/test_studentizer*.py` focused selection |
| C2 batch / ZIP-input / partial / local delivery | **85 passed** on serial rerun | `test_c0_job_service`, `test_batch_inputs`, `test_batch_workspace`, `test_batch_job_service`, `test_input_versions` |
| Restart recovery focused | **7 passed** | `tests/test_c35_hardening_harness.py`; implementation and scenario evidence below |
| Stage2 tests | **40 passed** (39 existing tests plus the new guard regression) | `tests/test_stage2_baseline.py` |
| Stage2 full four-source run | Completed after the guard; all four source hashes validated. QG gold/predicted/correct = **191/204/179**, missed 12, erroneous 25, boundary errors 2; issue counts: GROUP_SPLIT 3, MERGE 4, MISSED_STRUCTURE 27, ROLE_MISMATCH 2. This is reported as observed comparison output, not an accuracy PASS. | `C:\xml-uat\c3-final-stage2-20261002` |
| Stage3 full protected regression | **PASS:** 8/8 source hashes; QG **408/408**, P/R **100%**, exact 87.7%; sections **369/369**; subquestions **328/328**; errors `{}`; MISS/FP/MERGE/SPLIT all 0. | `C:\xml-uat\c3-final-stage3-20261002-final\compare.md` and `compare.json` |
| V0.9 frozen assets | **10/10 match** frozen baseline `0922e08631226b95a77a6599bbc0ac3784e9134b` | `tools/verify_v09_fallback_assets.py` |
| 27 source hashes | **27/27 match** `baseline_inputs.json` | Read-only SHA256 verification against `C:\xml-uat\stage3-expansion\sources` |
| Python compilation | PASS (`compileall` on `tools` and `v1.2-xml-experiment/res/app`) | Final candidate |
| JavaScript syntax | PASS (`workspace.js`) | Final candidate |
| `git diff --check` | PASS | Final candidate changes |

## Stage2 failure diagnosis and narrow fix

The pre-fix Stage2 full-corpus run failed on sample S11 in
`schedule_e2_examples`: a TOC table container candidate (`b2.r5c0.n8`) has no
content-node ordinal in `NodeIndex`, so `order_of(...)` returned `None` during
an integer range comparison. The same input and same runner/StructDoc blobs at
R12 base `71b50740ebb785d77f2db01b15d5db4e42ffaed2` reproduced the same error;
the relevant file blob IDs were identical at R12 and pre-fix HEAD.

The evaluation runner now omits candidates without a `NodeIndex` ordinal from
the local E2 range scheduler. The TOC candidate itself remains in the returned
candidate list and this guard does not alter production Splitter code, StructDoc,
Gold, or business rules. The focused regression verifies an unindexed TOC
container can coexist with a knowledge module without crashing scheduling.
Afterward, the Stage2 focused tests passed 40/40 and the full four-source run
completed with all source hashes verified.

## C3 capability and production route evidence

The already-reviewed exact-digest scan remains **1/27 Studentizer-supported**
and **26/27 fail closed** with `STUDENTIZER_COVERAGE_UNPROVEN`. This is the
Studentizer capability rate; it is not a renderer-route rate. The existing
boundary diagnostic is 15 clear / 12 unsupported (8 `txbxContent`, 2
`clrChange`, 2 unsupported field parameters). Exact renderer routes for all 27
sources remain **not fully established**; the prior capability scan was not a
full renderer preflight.

R13 production measurements remain the comparable performance evidence:

| Workload | C2 | C3 | Route evidence |
|---|---:|---:|---|
| Same C2 Case A: 5 teacher-only 1v1 items | 121.330 s | 122.553 s (+1.01%) | Student preparation: V0.9 `make_student` 5/5; renderer: XML 5/5; whole-job fallback 0/5; 10 COM script invocations, 21 newly started office-process instances |
| Same C2 Case B: 3 teacher+student class items | 13.975 s | 13.809 s (−1.2%) | XML renderer 3/3; COM/WPS 0 |

For X008, the **Studentizer preparation stage itself** was
`XML_STUDENTIZER`: `make_student=0`, COM/WPS=0, and the approved Studentizer
output matched its Golden. The later XML renderer refused the inherited frozen
B-Line `_Toc9` bookmark anchor, so the **whole-job renderer fallback** ran. The
R13 row's aggregate `make_student`, COM-script, and office-process counts include
that later fallback; they are not Studentizer-stage counters. No B-Line change
was made. End-to-end COM-free X008 completion remains unproven.

The already-recorded same-source X008 teacher-only 1/3/5-item timings are
27.960 / 82.630 / 137.585 seconds, each including that renderer fallback; they
are not multi-source coverage evidence.

## Reused C3.5 stability and recovery evidence

No large workloads were rerun. Reuse the committed machine evidence in
`docs/v2/integration/C3_C35_STABILITY_REPORT_2026-10-02.md` and
`docs/v2/integration/fixtures/c3-c35/`:

- Batch10: 10/10 done, 20 DOCX, 433.722 s; Batch20: 20/20, 40 DOCX, 904.617 s.
- Ten consecutive 3-item jobs completed; RSS 83.3 MB → 112.9 MB; fallback/XML
  timing drift 0.995 / 1.000. Four settle WPS PIDs matched pre-run baseline.
- Abnormal input checks covered corrupt/empty DOCX, duplicates/mixed input,
  Chinese path, ZIP traversal (no outside write), clean output inventory.
- Mixed fallback was serialized (`max-active=1`); no newly residual WPS process
  was observed at serial-fallback settle.
- Restart A (queued), B (three persisted stages: Student preparation, teacher
  renderer, before publication), and C (one completed sibling plus active and
  queued siblings) recovered. Completed sibling DOCX hashes remained identical;
  interrupted jobs finished without remaining `running` or direct recovery to
  `error`.

## Machine-gate disposition

The Stage2 evaluation-runner crash is fixed without changing production
Splitter rules. Focused C2, Studentizer, restart, Stage2 tests, protected
Stage3, source/asset integrity, compile, syntax, and diff checks pass. The
repository-wide suite still has the same four recorded V1.1 legacy API failures,
so this report is **not** a full-suite PASS and does not authorize the C3 tag.
Final verdict remains with the independent Codex GPT-6.1 Sol Chief.

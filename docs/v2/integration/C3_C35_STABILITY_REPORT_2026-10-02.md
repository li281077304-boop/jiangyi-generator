# C3.5 stability and restart recovery report — 2026-10-02

**Scope:** carry forward completed C3.5 load evidence and close the observed
restart-recovery failure. No C3 R1–R8 audit, Golden, or OOXML exploration was
repeated. No 10-item or 20-item load was rerun.

## Inherited C3.5 evidence

The existing machine reports in `fixtures/c3-c35/` were produced on the prior
candidate before this restart fix. They remain applicable because the fix only
cleans per-job renderer scratch after a persisted `running` job is found during
service startup.

| Gate | Existing result | Evidence |
|---|---|---|
| 10-item batch | 10/10 done; 20 DOCX; 433.722 s; result directory contains DOCX only | `batch10.json` |
| 20-item batch | 20/20 done; 40 DOCX; 904.617 s; result directory contains DOCX only | `batch20.json` |
| 10 consecutive jobs | 10/10 done, 3 items each; fallback-job drift 0.995; XML-job drift 1.000; RSS 83.3 MB → 112.9 MB (+29.6 MB) | `consecutive.json` |
| Abnormal inputs | corrupt and empty DOCX rejected, duplicate/mixed inputs fail closed, long Chinese path completed, ZIP traversal rejected with no outside write; final result inventory has 4 DOCX and no internal files | `abnormal.json` |
| Serial fallback | mixed 3 XML + 2 V0.9 items all done; 12 COM scripts; result inventory has only 10 DOCX; settle observed the original 4 WPS processes and no additional residual | `serial-fallback.json` |

The consecutive-job monitor reported four office processes at settle, matching
the pre-run baseline PIDs. The saved monitor summary labels these as residual;
they are the same four baseline processes, so this is not evidence of four newly
orphaned WPS instances. The separate serial-fallback settle reports zero new
residual processes. The focused concurrent-fallback gate observed
`max-active=1` and verified observer restoration; the real mixed batch also
used the existing serialized batch executor and `_V09_FALLBACK_LOCK`.

## Restart recovery

| Case | Interruption point | Recovery result |
|---|---|---|
| A | queued before execution | Existing run completed all 3 items after restart, with 6 final DOCX. This fix only applies to persisted `running` records, so A was not rerun. |
| B, 5 s | persisted `running`, V0.9 fallback stage | Requeued and completed; 2 final DOCX, clean result folder. |
| B, 20 s | persisted `running`, V0.9 fallback stage | Requeued and completed; 2 final DOCX, clean result folder. |
| B, 30 s | persisted `running`; `teacher-output-<job_id>.docx` existed in private work at kill | Recovery removed the stale private renderer output, requeued, and completed; 2 final DOCX, clean result folder. This reproduces and closes the prior `FileExistsError` blocker. |
| C | batch parent had item 1 `done`, item 2 active, item 3 queued | Restart completed all 3 items (6 DOCX). Item 1 remained `done`; both of its output hashes were identical before and after restart. Items 2 and 3 completed after resume. |

The three B interruptions span early running, later running, and a persisted
private output artifact. In all three, the job recovered to `done`; no
interrupted job remained `running` and no job transitioned directly to
`error` on recovery. Batch C retained its completed sibling and generated the
remaining items.

## Recovery implementation and machine gate

On service startup, each persisted running single-job record is requeued after
removing known renderer-generated intermediates from that job's private
`runtime/<job_id>/work` directory. Uploaded `input-*.docx` and published user
result files are preserved. Cleanup is restricted to renderer output names,
studentizer output, and renderer staging patterns within the resolved private
work directory.

Machine gate: `tests/test_c35_hardening_harness.py` plus
`tests/test_batch_job_service.py` — **19 passed**; focused concurrent fallback
gate — **1 passed** with max-active=1. Python compilation and `git diff --check`
passed for the scoped changes.

## Remaining limits

- These restart cases exercise V0.9 fallback because X008 still encounters the
  inherited frozen B-Line missing-bookmark boundary. No B-Line scope was changed.
- This report does not claim the teacher-only performance target, complete
  C3 regression, or final Chief review. Those gates remain separate.
- Existing inherited batch and consecutive evidence was collected before the
  restart fix and was not rerun after it; the targeted A/B/C restart cases were
  run against the working candidate containing the fix.

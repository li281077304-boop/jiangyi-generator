# C4 Final RC UAT Evidence — 2026-10-02

## Status

This report retains the earlier candidate evidence for history. The current
final candidate and superseding closeout are in “Final Candidate d3511a0”.

**Current disposition: FINAL_CHIEF_REVIEW_PENDING.** The latest onedir package
is bound to source/remote commit
`d3511a07aeb5e981733750cc5d21db350029f229`; fresh browser and WPS UAT, restart
recovery, package audit, and post-UAT regression evidence are recorded below.
The earlier stale-header and queued-snapshot gaps are superseded by that
candidate's evidence. Do not claim `C4_WINDOWS_RC_PASS` or create the release
tag until Codex GPT-6.1 Sol returns Final Chief PASS.

## Build and startup evidence

Evidence root: `C:\xml-uat\c4-final-rc`.

| Check | Recorded result | Evidence |
|---|---|---|
| Build form | PyInstaller onedir; CPython 3.12.10 x64 | `build\build.log`, `output\PACKAGE_INVENTORY.json` |
| Candidate build commit | `f095147ab09a6ded718443e03c42f473766a2b38` was the branch HEAD before the build/UAT window; the build inventory itself does not embed this SHA, so this is a timeline-based attribution, not an independently attested build input. | `git log` chronology; `evidence\isolated_startup.json` |
| Inventory | 194 files; 36,171,362 bytes; package tree SHA-256 `c8ac99fd49d55e48665b386f6336eca94272346baff065a1e94bf1e03e688cf8`; frozen V0.9 assets verified 10/10 | `output\PACKAGE_INVENTORY.json` |
| EXE | SHA-256 `b0ec692ebc3b0eb62a0a8a1e2e17ca68a8ca944edb09210ffbc0b0813a9b59e8` | `evidence\isolated_startup.json` |
| Isolation and launch | Launched from a Chinese path on D: with working directory `C:\Windows\System32`; Python, PYTHONPATH, and virtual-environment variables unset; LocalAppData on C:, redirected Desktop/result directory on D: | `evidence\isolated_startup.json` |
| Web ready | `http://127.0.0.1:5128` ready; root/CSS/JS returned 200; correct product title; browser window observed | `evidence\isolated_startup.json` |
| Console | No application console main window recorded. One `conhost.exe` process was observed; this file alone does not establish whether it was a short-lived or persistent console host. | `evidence\isolated_startup.json` |
| RC archive | No deliverable RC ZIP is present under `output`; the only ZIP there is PyInstaller's `_internal\base_library.zip`. | `C:\xml-uat\c4-final-rc\output` inventory |

The package inventory establishes what was included and its hashes. A retained,
separate audit proving that the final distributable excludes all forbidden
content (corpus, Golden sources, dev logs, temporary UAT files, credentials,
and the development environment) was not found. The final release ZIP and its
size/SHA-256 therefore remain unverified.

## Browser-submitted generation scenarios

Job records are under
`C:\xml-uat\c4-final-rc\localappdata\讲义生成器\jobs\<job_id>\job.json`.
These are application-persisted results from the packaged UI runs. They prove
job state, output paths, route metadata, and package validation; they do not
prove correct visual template content.

| Scenario | Evidence / result |
|---|---|
| 1. Teacher + student pair, class template | Job `86b44f70659243848a2f812fb49673b0`; `done`; renderer `XML`; teacher and student DOCX both package-valid; two files published to D: result directory. |
| 2. Teacher-only, class template | Job `7324ae3a40d948ae8d4aaf4b20167b59`; `done`; renderer `XML`; teacher and prepared student outputs package-valid and published. |
| 3. Student-only, class template | Job `03926b61cf1e4d068e3a30531a2b2070`; `done`; renderer `V0.9`, reason `XML_RENDER_FAILED`; one student DOCX package-valid and published. |
| 4. Multiple DOCX batch | Job `9d19e95b04d14d0ab2eaaa7fe87e6341`; three logical items completed, six DOCX paths published; per-item routes include XML and V0.9 with `XML_RENDER_FAILED`. Child/item records are in the same job directory and its referenced child job records. |
| 5. Chinese ZIP with nested paths | Job `da14e3ae58b14277be151831a8598d06`; input `中文专题_含损坏条目.zip`; two valid items produced outputs in separate topic folders using XML. |
| 6. Partial success with corrupt ZIP item | Same ZIP job `da14e3ae58b14277be151831a8598d06`; final status `partial`, two items `done`, corrupt item `损坏的讲义` `error` with `无效或损坏的 DOCX`; completed sibling outputs remain listed. This is a distinct acceptance scenario within the ZIP submission, not a separate upload. |
| 7. Real V0.9 fallback | Exercised by items in job `9d19e95b04d14d0ab2eaaa7fe87e6341` (`X006` and `X012-fallback-teacher-saved`, renderer `V0.9`, reason `XML_RENDER_FAILED`); output pairs were published and package validation is recorded in the child jobs. Restart batch `0f8e7f6dced342568fca2673e98b10c8` also records a V0.9-routed X006 item. |

Cross-volume publication evidence: the isolated startup record places runtime
and job work under C: and Desktop/results under D:. The completed jobs above
record final output paths on D:. The restart batch job `0f8e7f6dced342568fca2673e98b10c8`
lists five final DOCX outputs. The persisted job records show successful
publication and package validation; no dedicated machine-readable publication
temp-residue scan report was found in the evidence root. The known prior
`WinError 17` was not reproduced in these completed jobs, but this evidence
should not be represented as a separately instrumented assertion that the
error can never occur.

## Restart recovery

| Scenario | Evidence / result |
|---|---|
| A — exit while queued, then restart | **Not verified.** No retained evidence captures a job durably in `queued` before termination. A bounded attempt observed it already running; do not count this as a pass. |
| B — exit while running, then restart | Job `4c060205086f46198ffe1de0c3593e83`; persisted final status `done`, `recovered_after_restart=true`, `generation_attempts=2`, two final output paths. |
| C — batch partly completed, then restart | Job `0f8e7f6dced342568fca2673e98b10c8`; final `done`, `recovered_after_restart=true`, `generation_attempts=2`, three items done and five final DOCX outputs. The inherited evidence review reports already-published sibling DOCX hashes unchanged and no duplicate final outputs. The job record itself confirms the final routes/status/output paths, but the cited hash comparison details are not embedded in that JSON. |

No retained evidence demonstrates three repetitions of the interrupted stages;
do not claim the user-requested restart repetition criterion as satisfied.

## WPS roundtrip and visual content blocker

WPS COM evidence identifies `KWps.Application` (provider reports Word 12.0).
`C:\xml-uat\c4-final-rc\wps-roundtrip-r3\report.json` records five outputs
with `open=PASS`, `saveas=PASS`, `close=PASS`, `reopen=PASS`, and `pdf=PASS`;
the corresponding DOCX/PDF files are non-empty. `content_audit.json` records
readable PDFs and matching paragraph/table/OMML/image counts across source and
WPS-saved packages for the audited documents. The separate 1v1 XML check at
`wps-1v1-xml\report.json` records teacher and student both passing the same
roundtrip steps.

These structural and roundtrip checks **do not pass visual/template correctness**:

* Class output page image: `wps-roundtrip-r3\visual\chem-class-teacher-page1-01.png`.
  The input job selected high-school chemistry; the rendered page visibly says
  `五年级`, `数学`, and `第二单元 因数与倍数`.
* 1v1 output page image: `wps-1v1-xml\visual\page1-01.png`. The input job
  selected high-school chemistry; the rendered page visibly says `数学` and
  `高三`.

Therefore WPS open/save/reopen/PDF package behavior passed for the sampled
outputs, but the sampled outputs fail the requested selected-subject/grade/topic
header correctness. This is a release blocker requiring Chief judgment and, if
directed, a narrowly scoped fix and fresh RC UAT.

Earlier incomplete WPS attempt `wps-roundtrip\report.json` stopped after open
and SaveAs because the test process could not hash files while they were still
open. It is superseded for roundtrip completion by `wps-roundtrip-r3`, but its
failure is retained here to distinguish the attempts.

## Startup/exit cycles and regression evidence

* `start-exit-cycles.json`: 10/10 cycles recorded ready HTTP 200, page/CSS/JS
  HTTP 200, shutdown stopping, port released, no app-process residual, and a
  fresh instance ID. Browser window presence is recorded each cycle.
* Stage3 final after UAT: `final-gates\stage3-final-after-all-uat\compare.md`
  and `compare.json`; reported QG 408/408, sections 369/369, subquestions
  328/328, Recall 100%, and MISS/FP/MERGE/SPLIT all zero.
* Stage2 final: `final-gates\stage2-final-after-all-uat\summary.md` and
  `summary.json`; per-source predictions and comparisons are retained. The
  inherited review reports outputs match the C3 baseline for S04/S12, while
  S01/S11 retain known differences; this is not a blanket 39/39 Stage2 claim.
* The prior full pytest record is 415 passed plus 7 subtests, with four failures
  identified as legacy V1.1 API assertions; launcher focused tests are
  recorded as 12 passed. Current final-after-UAT regression logs for every
  requested suite (C2, C3, frozen hashes, 27 source hashes, py_compile, JS,
  diff-check) were not all found under this evidence root, so those gates are
  not re-certified here.

## Gate disposition / next action

* **Passed evidence:** startup readiness in isolation; 194-file onedir
  inventory; browser-submitted output generation and package validation for
  the cases above; cross-volume outputs recorded on D:; restart B and C final
  records; WPS roundtrip mechanics for sampled output; 10/10 startup/exit
  records; Stage3 protected comparison.
* **Failed / incomplete at initial closeout:** stale template header values in
  both templates; Restart A; repeated restart-stage criterion; official final
  RC ZIP; full named regression suite recertification after all UAT. Later
  follow-ups below added the candidate archive/path audit, selected test
  rerun, and Restart A attempt evidence.
* **Pending:** independent final review by Codex GPT-6.1 Sol, then only if it
  returns PASS may the final RC tag be created. No final tag exists as part of
  this evidence report.

## Post-UAT verification on candidate HEAD `f095147...`

Verification was run after the browser/WPS UAT against code HEAD
`f095147ab09a6ded718443e03c42f473766a2b38`, using the existing build Python
at `C:\xml-uat\c4-final-rc\build\venv\Scripts\python.exe`. These are
post-UAT machine checks; they do not resolve the visible template-header
failure or Restart A evidence gap.

### Pytest gates not executable in the specified environment

Attempted:

```powershell
& 'C:\xml-uat\c4-final-rc\build\venv\Scripts\python.exe' -m pytest -q tests\test_windows_launcher.py tests\test_c0_job_service.py tests\test_batch_inputs.py tests\test_batch_workspace.py tests\test_batch_job_service.py tests\test_input_versions.py tests\test_c35_hardening_harness.py tests\test_studentizer.py tests\test_studentizer_approved_source_probe.py tests\test_studentizer_capability_scan.py tests\test_studentizer_integration.py tests\test_studentizer_pair_audit.py tests\test_studentizer_production_registry.py tests\test_studentizer_ranges.py tests\test_studentizer_ranges_real.py tests\test_studentizer_source_candidate.py tests\test_studentizer_subject_selection.py tests\test_stage2_baseline.py
```

Result: process exits before test collection with
`No module named pytest`. The same specified interpreter also has no
`pytest.exe` entry under `Scripts`. Consequently launcher-focused,
publication/restart-focused, C2 batch/ZIP/partial/local-delivery, C3
Studentizer, and Stage2 pytest groups are **not run / unverified** in this
round. No package installation and no substitute Python environment was used.
Existing historical test counts in earlier C3 reports are not recertified as
post-UAT results here.

### Executable structural and protected regression checks

| Gate | Command / evidence | Result |
|---|---|---|
| Stage2 four-source run | `python tools\stage2_baseline\run_baseline.py --manifest tools\stage2_baseline\manifest.json --corpus-root C:\Users\Administrator\Desktop\工作\讲义生成器 --out C:\xml-uat\c4-final-rc\regression-after-uat\stage2` using the specified build Python | Completed. QG Gold/predicted/correct = 191/204/179; missed 12, erroneous 25, boundary errors 2. GoldCompare S01/S11 remain FAIL and S12/S04 PASS, with the previously known issue counts. All four generated prediction-unit arrays are structurally identical to `final-gates\stage2-final-after-all-uat\*_pred.json`; this is unchanged known comparison output, not an accuracy PASS. Report: `regression-after-uat\stage2\summary.md` / `.json`. |
| Stage3 protected regression | `python tools\stage3_goldcompare\rerun_predictions.py --out C:\xml-uat\c4-final-rc\regression-after-uat\stage3-predictions`, then `python tools\stage3_goldcompare\run_approved_gold_compare.py --predictions-dir ... --out ...\stage3-compare.md --json ...\stage3-compare.json` | All 8 source hashes match. QG 408/408, precision/recall 100%, exact 87.7%; sections 369/369; subquestions 328/328; MISS/FP/MERGE/SPLIT all zero; `errors={}`. Per-sample metrics equal `final-gates\stage3-final-after-all-uat\compare.json`. Artifacts: `regression-after-uat\stage3-predictions\` and `stage3-compare.md` / `.json`. |
| Frozen V0.9 assets | `python tools\verify_v09_fallback_assets.py` | 10/10 verified against frozen baseline commit `0922e08631226b95a77a6599bbc0ac3784e9134b`; zero failures. |
| 27 source hashes | SHA-256 each `sources/<source_path>` in `C:\xml-uat\stage3-expansion\baseline_inputs.json` and compare with the manifest | 27/27 match; zero mismatches. |
| Python compilation | `python -X pycache_prefix=C:\xml-uat\c4-final-rc\regression-after-uat\pycache -m compileall -q v1.2-xml-experiment\res\app tools\stage2_baseline tools\stage3_goldcompare` | Exit 0; `PY_COMPILE_PASS`. Compiled cache was directed outside the repository. |
| JavaScript syntax | `node --check v1.2-xml-experiment\res\app\webapp\static\workspace.js` | Exit 0; `JS_SYNTAX_PASS`. |
| Diff whitespace | `git diff --check` after this report/journal update | Exit 0; no whitespace errors. |

### Read-only package path and archive check

The onedir tree at `C:\xml-uat\c4-final-rc\output\dist\讲义生成器`
contains 194 files and 36,171,362 bytes, matching
`output\PACKAGE_INVENTORY.json`. A path-segment audit over those entries found
zero matches for `.git`, tests/corpus/Gold originals, `.pytest_cache`, UAT or
diagnostic/staging/temp directories, credentials/secrets/tokens, `.env`/log
files, or development virtual environments. This was a path/name audit; it did
not inspect arbitrary file contents for embedded secrets.

The four `.docx` files in the tree are packaged templates:

* `_internal/docx/templates/default.docx`
* `_internal/v1.1-stable/res/app/2025+1v1讲义模板(2).docx`
* `_internal/v1.1-stable/res/app/2025班课模板.docx`
* `_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/2025+1v1讲义模板(2).docx`

The frozen V0.9 runtime assets remain intentionally included and passed the
10/10 manifest-to-Git-blob hash verification above.

A candidate archive has since been placed externally at
`C:\xml-uat\c4-final-rc\release-candidate\讲义生成器_V1.2_RC1_Windows_x64_candidate_f095147.zip`.
Read-only verification records 19,013,293 bytes, SHA-256
`b8b1f458564f0f18bd11573f525acc8fc680ab56ca7df3bdc8231c432104ea69`, 194
entries, zero size/hash mismatches against the package inventory, and zero
forbidden path-segment matches. This is explicitly a **candidate archive, not
the final RC ZIP**. The inventory/archive does not independently attest which
Git SHA was used to build the executable.

### Updated gate disposition

The new Stage2/Stage3, frozen asset, source hash, compile, JavaScript, package
inventory/archive path checks passed as recorded above. The build venv lacked
pytest, but a later selected test run in the existing UAT venv passed 293/293.
Stage2 GoldCompare includes known FAIL results and is reported as measured
output, not correctness approval. Restart A was later exercised; its queued
pre-shutdown observation lacks a retained raw snapshot. The WPS stale-header
blocker remains. Do not claim `C4_WINDOWS_RC_PASS`, do not tag, and do not treat
the candidate archive as a release artifact pending final Chief review and all
remaining gates.

### Follow-up: focused pytest rerun in existing UAT venv

The preceding pytest limitation applied only to the PyInstaller build venv.
After locating the existing `C:\xml-uat\.venv`, the same requested focused
selection was run without installing packages:

```powershell
& 'C:\xml-uat\.venv\Scripts\python.exe' -m pytest -q tests\test_windows_launcher.py tests\test_c0_job_service.py tests\test_batch_inputs.py tests\test_batch_workspace.py tests\test_batch_job_service.py tests\test_input_versions.py tests\test_c35_hardening_harness.py tests\test_studentizer.py tests\test_studentizer_approved_source_probe.py tests\test_studentizer_capability_scan.py tests\test_studentizer_integration.py tests\test_studentizer_pair_audit.py tests\test_studentizer_production_registry.py tests\test_studentizer_ranges.py tests\test_studentizer_ranges_real.py tests\test_studentizer_source_candidate.py tests\test_studentizer_subject_selection.py tests\test_stage2_baseline.py
```

Result: **293 passed in 91.06s; zero failures**. The selected launcher,
publication/restart, C2 batch/ZIP/partial/local delivery, C3 Studentizer,
C3.5 restart, and Stage2 test groups had no baseline-known failures and no new
regressions in this run. This supersedes the earlier “pytest-focused gates
remain unverified” statement for these selected groups only. It does not
include the full repository suite or turn the known Stage2 GoldCompare S01/S11
observations into accuracy PASS. The build venv still lacks pytest; this test
rerun used the already-existing `C:\xml-uat\.venv` on the same code HEAD.

### Follow-up: Restart A final recovery evidence

New retained evidence: `C:\xml-uat\c4-final-rc\evidence\restart-A-final.json`
(captured 2026-10-02 17:06:40 +08:00). It records two jobs:

| Job | Pre-shutdown observation | Final after restart | Final outputs |
|---|---|---|---|
| `4e09ef191dfc414baa638500fd3e1a1d` | `running`, observed before 17:02:11 +08:00. The observation source is the prior worker handoff record; no raw pre-stop snapshot is retained. | `done`; `generation_attempts=2`; `recovered_after_restart=true`. | `D:\Documents\生成讲义结果\2026-2027学年 高一 化学 X006 复习讲义（3）`: teacher DOCX 3,823,405 bytes, SHA-256 `f90fb13685b7c80f37002e80db8febb4631c1c69f80ff5574db127cfc74cfdc2`; student DOCX 1,612,502 bytes, SHA-256 `919588ce022a0681e1db186b30468539016dd59164fd6b6c0d16011166c3e5e5`. |
| `af94bfbd89164024b59fd6e820b6adec` | `queued`, observed at 17:02:09 +08:00 immediately before package shutdown. This observation is documented in a prior worker handoff record, not a retained raw status snapshot. | `done`; `generation_attempts=1`; `recovered_after_restart=false` (the job completed after restart without a recorded second generation attempt). | `D:\Documents\生成讲义结果\2026-2027学年 高一 化学 化学实验与科学探究 复习讲义（6）`: student DOCX 2,983,737 bytes, SHA-256 `059cf32a3051c04baab404823eca43336b3d216805086854583003096488f991`. |

The corresponding persisted job records are under
`localappdata\讲义生成器\jobs\<job_id>\job.json`. Both output directories
were inspected: each contained exactly the expected non-empty DOCX file(s),
with no duplicate DOCX, temp file, or other artifact. Job validation records
show teacher/student/student package validation `valid=true`, zero errors,
zero warnings; the restart evidence's independent CRC/required-entry check
reports 3/3 files passed. Shutdown evidence records the launcher shutdown
accepted, port 5128 no longer listening, and zero RC processes remaining.

**Disposition:** Restart A has now been exercised for both a running job and
a queued job, with final successful recovery/output evidence. The queued
pre-shutdown state is strong handoff-record evidence but is not backed by a
retained raw pre-shutdown status snapshot; keep that evidence limitation
visible. This supersedes the earlier statement that Restart A was not
executed, but does not erase the raw-snapshot limitation.

### Follow-up: candidate archive and bounded secret-pattern scan

The candidate archive and path audit described above now exist and are
verified. The archive remains a candidate only; it is not the official final
RC ZIP and its build commit is not independently attested. Thus the earlier
“package exclusion audit pending” disposition is superseded only for the
recorded archive inventory/path audit; no comprehensive binary-content secret
analysis is claimed.

A separate literal-secret pattern scan run in this turn scanned **43 text
assets, 0 matches**. This was a limited literal-pattern scan, not a
comprehensive binary or encoded-secret analysis. Its command result is not
retained as a separate raw output file.

The focused pytest follow-up remains **293 passed, zero failures**; only the
full repository suite was not run. Earlier interim wording that the selected
pytest groups were unverified is superseded by that result.

## Final Candidate d3511a0

This section supersedes the earlier candidate-specific blockers above where
fresh evidence exists. It does not erase the historical evidence. The final
candidate was built from branch HEAD
`d3511a07aeb5e981733750cc5d21db350029f229` and its build attestation is
`C:\xml-uat\c4-final-rc-final\evidence\build-attestation-d3511a0.json`.
The package was PyInstaller onedir, Windows x64, and was tested from a Chinese
path on D: with runtime/staging on C: and results on D:.

### Build, launch, and package

* EXE SHA-256: `a781e0c80db0c4d3594afd1ad7bae9326df3c7ec433b8ce26b27c3491ac474db`.
* Onedir tree SHA-256: `fb548acaa81651564b1a6865a551fa7b8175b1723668abf2bf6fdbed5d60ee3e`.
* The fresh EXE reached Flask ready; root, CSS, and JS returned HTTP 200, the
  product title was correct, and the browser opened. Evidence:
  `C:\xml-uat\c4-final-rc-final\evidence\startup-d3511a0.json`.
* Ten consecutive launch → ready → normal-exit cycles passed. Each cycle
  recorded port release and no surviving application process; a fresh
  instance identity prevented reuse of an old service.
* The final archive is
  `C:\xml-uat\c4-final-rc-final\release-candidate\讲义生成器_V1.2_RC1_Windows_x64_d3511a0_FINAL.zip`,
  19,017,363 bytes, SHA-256
  `a5c5be3d791707a7fcaaca0cf3d0dbd4062576d6bb2b1e78af00d15a6288fadd`.
  Its 194 entries match the d3511a0 package inventory hashes. The forbidden
  path audit found zero `.git`, corpus/Gold source, pytest cache, UAT/log/temp,
  credential, or development-environment paths; required runtime assets were
  present. The bounded content scan checked 43 text assets and found no
  literal secret-pattern matches; this was not a comprehensive binary-secret
  analysis.

### Real browser generation and cross-volume publication

All scenarios below were submitted through the packaged EXE's browser UI.
Runtime/staging remained on C:, and final files were written to the D: Desktop
results directory. Teacher/student DOCX files were non-empty and passed their
package validation. The result directories contained only final DOCX outputs;
no publication temporary files remained. No `WinError 17` recurred.

| Scenario | Outcome |
|---|---|
| Teacher + student pair | Job completed; both outputs published and validated. |
| Teacher-only | Job completed; teacher output and prepared student output published and validated. |
| Student-only | Job completed through the recorded renderer route; student output published and validated. |
| Multi-DOCX batch | Three logical items completed with six final DOCX outputs; item routes recorded XML and V0.9 fallback. |
| Chinese ZIP with nested folders | Two valid items completed from Chinese multi-level paths. |
| Partial success with corrupt item | The corrupt input item failed validation while two good siblings completed and remained published; final state was legitimate partial. |
| Real V0.9 fallback | A known unsupported/render-failure case invoked the frozen whole-job route and published validated output. |

Job ids, input classification, Studentizer/renderer routes, fallback reasons,
and package results are in the persisted job records under
`C:\xml-uat\c4-final-rc-final\localappdata\讲义生成器\jobs` and the associated
browser UAT evidence. ZIP was tested as an input format only; the product
delivery remains the local result folder.

### Restart recovery

The retained interruption snapshot
`evidence\restart-AB-interrupt-d3511a0.json` captured one job at `running`
(stage `准备 Splitter 与 Renderer`, attempt 1) and a sibling at `queued`
(attempt 0), then confirmed both candidate processes stopped and port 5128
was released. After restart, `restart-AB-final-d3511a0.json` records both jobs
done: the interrupted running job recovered on attempt 2; the queued job
completed on attempt 1. The separate batch restart evidence completed all
4/4 items while preserving completed siblings. No duplicate output or
publication temp was found. DOCX package validation passed. Restart evidence
files are under `C:\xml-uat\c4-final-rc-final\evidence`.

### WPS output acceptance

The latest candidate outputs passed WPS Open → SaveAs → Close → Reopen → PDF
for 1v1 teacher/student, class teacher/student, and a real V0.9 fallback
teacher output. All five roundtrips completed; files and PDFs were non-empty.
The content audit found all three expected slots, correct physics/high-school
headers on the X006 outputs, and correct mathematics/high-school headers on
the X012 fallback. Images and tables remained present; formula-bearing
fallback content was detected after reopen. Evidence is in
`evidence\wps-final-d3511a0\report.json`, `class-roundtrip.json`,
`fallback-x012-roundtrip.json`, and `wps-slot-content-d3511a0.json`.
This supersedes the prior candidate's stale-header failure for the tested
latest outputs; it does not claim visual inspection of every page or every
generated item.

### Final regression disposition

* Selected C4 regression: **293 passed, 0 failed**. This covers launcher,
  publication/restart, C2 batch/ZIP/partial/local delivery, C3 Studentizer,
  C3.5 restart, and Stage2 focused tests.
* Full repository pytest: **418 passed, 4 failed, 7 subtests passed**. The four
  failures are in frozen `v1.1-stable/res/app/webapp/test_app_api.py` and
  assert obsolete V1.1 result ZIP/API behavior, including old status codes.
  These are baseline-known failures, not silently counted as passes. Full log:
  `C:\xml-uat\c4-final-rc-final\evidence\regression-after-uat-final\full-pytest.log`.
* Stage2 completed and matches the inherited prediction outputs. Its GoldCompare
  remains S01/S11 FAIL and S04/S12 PASS; this is not a blanket Stage2 accuracy
  pass.
* Stage3 protected regression: QG 408/408, sections 369/369, subquestions
  328/328, Recall 100%, E1/E2/E3/E4 = 0, MISS/FP/MERGE/SPLIT = 0.
* Frozen V0.9 assets 10/10; 27 source hashes 27/27; Python compilation,
  JavaScript syntax, and `git diff --check` passed.

**Current disposition: FINAL_CHIEF_REVIEW_PENDING.** Fresh candidate evidence
resolves the stale-header and restart snapshot gaps for the tested flows. The
four frozen V1.1 tests and known Stage2 GoldCompare observations remain
explicitly disclosed. No final tag exists. Create the tag only after Codex
GPT-6.1 Sol independently returns PASS.

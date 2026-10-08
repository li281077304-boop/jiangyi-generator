# Product rescue P0 — real Windows EXE task recovery

Status: **P0_REAL_EXE_PASS**. This is a stage checkpoint, not release approval.

Base: `ca5e825d4b43e7359d7c42a948c1bd29548a27a1`, branch `feature/v1.2-c4-release-engineering`.

## Confirmed defects and changes

- Completing a task deleted `handout_current_job`; refreshing then lost the result view. The latest viewed task now stays persisted until the user starts a new task.
- Reconnect did nothing without a current job ID. It now requests the persisted job list, resumes the active/stored job, polls its status, and explicitly reports success/failure. An initial connection failure also exposes this action.
- Requests could remain pending without a timeout. GET requests now time out after 15 seconds; submissions after 120 seconds. A lost submission response asks the user to recover task state to avoid duplicate submission.
- State-rendering/API errors previously appeared as disconnection. Transport failures are now marked independently; task restoration errors have their own feedback. API internal failures return JSON.
- Concurrent first requests could initialize multiple JobService objects. Initialization invokes restart recovery, so this was unsafe for live jobs. A process-wide initialization lock ensures one service per runtime. This is a confirmed race in code and regression testing; it is not claimed as the proven cause of the earlier user incident.
- Engine selection and engine preference were removed from the ordinary UI. The P0 checkpoint uses the existing V0.9 default while P1 prepares the automatic XML chain. The UI reports simple standard/compatibility processing; technical route evidence stays in job reports.

## Actual packaged EXE evidence

Normal launcher entry was started, without `--server`. Its isolated runtime is `C:\xml-uat\product-rescue-p0-20261008\localappdata`; final files were published to the real D: result directory. Browser interaction used Playwright against the EXE's HTTP service, not a source Flask process.

EXE: `C:\xml-uat\product-rescue-p0-20261008\dist\讲义生成器\讲义生成器.exe`.

SHA-256: `b7c2c4e67b2ef9d7a6c767afcc3d865d214097d05b4352cecb536f5a25fe5344`.

Sources: immutable incident original-paper/answer-rich pair from `incident-72cab43961d6488c91b7a9e049265263`. Correct cover selection: physics, grade 9.

| Case | Actual job | Result |
| --- | --- | --- |
| 1v1, running refresh, browser offline, failed/successful reconnect, completion refresh, reopened tab, open folder | `e58f8bde256348afa71446b68949b1b4` | done; generation_attempts=1; teacher/student published |
| Class, browser offline, failed/successful reconnect, completion refresh, reopened tab, open folder | `ab02b472ebf0409f815552119be4fdee` | done; teacher/student published |
| Disconnection with no current task ID | no new generation | offline failure message; online reconnect succeeds |
| Corrupt DOCX submission | no phantom job | HTTP 415; explicit invalid-package feedback |

In both generation cases the browser was put offline, while independent HTTP polling proved the backend completed the task. The page then recovered the real completed task. Browser disconnection did not cancel generation. Every final file was nonempty and revalidated from disk; both result directories contained only final DOCX files. There were no JavaScript page errors. Expected network errors were caused by deliberate browser offline emulation.

Raw assertions, final paths/hashes, warnings, package reports, and launcher metadata are in `fixtures/product-rescue-20261008/p0_real_exe_evidence.json`. Screenshots and CLI logs remain in `C:\xml-uat\product-rescue-p0-20261008`.

## Machine checks and remaining scope

- Job-service/C0/batch/launcher/concurrency tests: **56 passed** after the prior QA service was normally shut down. The two initial launcher failures were live-instance/mutex interference, not silently counted as passing.
- Existing Final Polish test maintenance: **17 passed**. It now exercises the V1.2 subprocess proxy instead of importing a nonexistent helper from frozen V0.9; stale metadata assertions were updated to the existing reviewed rule.
- V0.9 frozen assets: **10/10**; JavaScript syntax and diff whitespace checks passed.
- No full regression or new WPS claim is made for this checkpoint. No source-content algorithm changed in P0.
- Automatic XML degradation, teacher-only safety, 33-topic evaluation, real WPS acceptance, and final EXE delivery remain P1/final gates. P0 results do not establish their success.
- Main is unchanged. No release tag or merge was created.

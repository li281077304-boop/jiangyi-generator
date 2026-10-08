# V1.2 Release Recovery — QA EXE and WPS Evidence

Date: 2026-10-08 (Asia/Shanghai)
Branch: `feature/v1.2-c4-release-engineering`
Application build commit: `3d1d017b27204a544ca329b7298119808c7846d3`
Status: **QA RC PACKAGE BUILT; FORMAL RELEASE GATES INCOMPLETE**

## Build and package

- Built a fresh Windows x64 PyInstaller onedir with CPython 3.12.10 and the pinned C4/OCR locks.
- Onedir inventory: **1,273 files / 288,157,077 bytes**. Frozen V0.9 assets: **10/10** verified.
- The packaging audit rejects test corpus, user documents, development artifacts, and unapproved DOCX/PDF/ZIP files. Its narrow runtime allowlist covers Python's `base_library.zip`, python-docx's default template, the two template-preview PDFs, and the two verified V0.9 templates.
- Final QA archive: `C:\xml-uat\release-recovery-20261008-qa-package-r3\讲义生成器_V1.2_稳定模式_QA_RC.zip`
- ZIP size: **133,630,441 bytes**; SHA-256: `4634e09eca1d439cdae062476ee3b1549eda406d7a35e053c591b1b317362c54`.
- EXE SHA-256: `0bd870c562a23325e6e1cfca0402c53a1b4b27373a21bed8506c2507d6a01664`.
- Package report: `C:\xml-uat\release-recovery-20261008-qa-package-r3\RC_PACKAGE_REPORT.json`. It records `excluded_content_scan=PASS`, `source_to_stage_hash_comparison=PASS`, and **2/2** frozen V0.9 templates verified. The corrected manifest total matches the independently inventoried onedir bytes.

## Real EXE generation

To avoid desktop GUI control, the packaged executable was started through its hidden `--server` entry point and tested with headless Playwright. The workbench page returned HTTP 200 and visibly selected **稳定模式（V0.9 引擎）**. This exercises the packaged service and real browser form, but does not claim that the normal launcher opened a visible browser window.

The immutable incident teacher/original-paper pair was uploaded through the workbench for both templates:

| Job | Template | Status | Renderer | Elapsed | Output validation |
|---|---|---|---|---:|---|
| `ef63034db1e3467c8cfc4c75ecb5e725` | 1v1 | `done` | V0.9 | 29.106 s | Teacher and student packages PASS |
| `06d8755d935745f69ee639982957860e` | Class | `done` | V0.9 | 29.057 s | Teacher and student packages PASS |

Both jobs published their two final DOCX files to unique Desktop result folders on `D:` while runtime and staging were under `C:`. Each result folder contained only the teacher and student DOCX. The UI showed the local output path and a missing objectives/difficulties warning.

The QA ZIP was extracted and run from `C:\xml-uat\release-recovery-20261008-qa-extracted-r2`. The final corrected-manifest r3 ZIP was also extracted separately; its manifest reports **1,273 onedir files / 288,157,077 bytes**, and its EXE SHA-256 matches the tested onedir EXE exactly. A fresh headless browser submission from the byte-identical extracted EXE completed:

- Job `695b19cae71b4b80baaa70910bd8d3f6`: `done`, V0.9 renderer, 29.465 s.
- Teacher and student package validation: PASS; only the two final DOCX files were published.
- Extracted-package teacher and student DOCX each completed the WPS round trip below.

## WPS round trip and page review

The real Windows WPS COM ProgID `KWPS.Application` was used. Its compatibility interface reports `Name=Microsoft Word`, `Version=12.0`. For each file the verified sequence was:

`Open → SaveAs DOCX → Close → Reopen → SaveAs PDF`

The older WPS interface failed when the test harness called newer `SaveAs2` and `ExportAsFixedFormat` methods. Using its supported `SaveAs` formats 16 (DOCX) and 17 (PDF) completed the requested round trip. All six WPS-saved DOCX packages passed package validation and all six PDFs were nonempty.

The four onedir-generated files produced these WPS page counts:

| Template / role | WPS pages |
|---|---:|
| 1v1 teacher | 50 |
| 1v1 student | 25 |
| Class teacher | 62 |
| Class student | 29 |

The package-extracted teacher/student pair reopened in WPS and exported to PDF at 50/25 pages. Rendered pages showed the circuit figures and the three-row measurement table (`1.9 / 1.0 / 2.9`) intact. The student pages retained answer blanks; teacher answers remained visible in the teacher output. WPS opened each file and completed the round trip without a COM exception or package validation error.

Known V0.9 presentation limits remain visible: objective and difficulty fields are blank when no reliable source text exists; the template retains the legacy heading `知识精讲&例题讲解`; the first page contains substantial empty space; and sampled final pages can contain only the legacy divider. The workbench reports the blank metadata warning. These are not represented as XML output or as V1.2 module-placement success.

Raw job JSON, DOCX/PDF, WPS report, and rendered page images are under:

`C:\xml-uat\release-recovery-20261008-exe-qa-localappdata`
`C:\xml-uat\release-recovery-20261008-package-qa-localappdata`

No user documents or generated outputs were added to Git.

## Regression and release boundary

- Focused stable/renderer/C0/batch tests: **60 passed**.
- Windows launcher tests: **12 passed** after the QA service released port 5128.
- Frozen V0.9 asset verifier: **10/10**; selected Python compilation, JavaScript syntax, and `git diff --check`: PASS.
- Full `pytest -q` collection stopped because `v1.2-xml-experiment/res/app/test_final_polish.py` imports `_run_hidden_process` from the frozen V0.9 module, where that helper does not exist.
- Retrying the suite without that module reached 38%, then stalled in a COM scan that launched `_scan_com.ps1` against a user sample under `做讲义`. The run was interrupted and its two test-owned WPS processes were stopped. Four test failures had appeared before interruption; they were not triaged and are not called baseline-known.
- Normal launcher auto-open behavior was not exercised; the user requested that desktop GUI automation stop. The packaged service, headless browser workflow, generation, publication, and WPS document round trips were exercised.

Therefore this is a **QA RC candidate**, not `C4_WINDOWS_RC_PASS`. No tag or release claim is made. Formal closeout still needs the full regression blocker addressed or isolated and the normal launcher opening behavior verified through a noninteractive method.

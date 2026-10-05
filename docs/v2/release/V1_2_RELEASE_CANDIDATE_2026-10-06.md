# V1.2 Release Candidate — build, EXE UAT and WPS gate

## STATUS

Release Candidate produced from a clean Git HEAD with the existing C4 / Windows
onedir flow. Real EXE UAT: **3/3 cases done with `renderer_route=XML`** and no
fallback. WPS Product Gate: **6/6 PASS** (Open → SaveAs DOCX → Close → Reopen →
Export PDF). Page-one knowledge-review anchor measured at **0.000pt** deviation
on every packaged output. No tag, no GitHub Release, no installer.

## BUILD

| Item | Value |
|---|---|
| Source HEAD | `c2691632480d1c7b681fd3cb02d09e2a43b3d1f2` |
| Branch | `feature/v1.2-c4-release-engineering` |
| Build base | `ddfab91e5dff75b5f371da8e23d971b864e6f58a` |
| Spec | `packaging/windows/v1.2_onedir.spec` (unchanged) |
| Build script | `tools/release/build_c4_onedir.ps1` (+1 packaging fix, below) |
| Interpreter | CPython 3.12.10 x64 (AMD64), isolated build venv |
| Bundled | Python 3.12.10 / Flask 3.1.3 / lxml 6.1.1 / python-docx 1.2.0 / PyInstaller 6.22.3 |
| Package root | `%LOCALAPPDATA%\C4\v1.2-onedir-output\dist\讲义生成器` |
| Files / bytes | 192 files / 36,147,708 bytes |
| Package tree SHA-256 | `a09214619799960e311621b74f1914841fd539a194a3ebc7a57228e49506916a` |
| `讲义生成器.exe` SHA-256 | `cc13931a15041e92a307ec32fe6b41feb16367b09a67157529ed7229467309ff` |
| RC ZIP | `讲义生成器-V1.2-RC-c269163.zip`, 18,829,332 bytes, SHA-256 `d9716071e2e6bc2fe73a5655a51bbc5a288ba5a37a8c673407f1f135fff0e0b3` |

Runtime is self-contained: the onedir package carries its own interpreter and
dependencies and does not use a system Python. WPS is the default office target
for the COM preparation/fallback path.

### Package validation (script-enforced)

- Forbidden content (`tests/`, `corpus/`, `gold/`, `.git/`, `__pycache__/`,
  `private/`, `uat/`): **none found**.
- Required resources (webapp templates/static, `X008.json` reviewed evidence,
  `tools/stage2_baseline/run_baseline.py`, both frozen templates): **present**.
- Frozen V0.9 runtime assets: **10/10 hash-verified** against
  `ASSET_MANIFEST.json` (baseline `0922e08631226b95a77a6599bbc0ac3784e9134b`).

## EXE REAL UAT

Launched as a real user would: double-click `讲义生成器.exe` (no arguments,
launcher GUI path, published `recovery/current-instance.json` + ready file),
then real HTTP uploads of real handouts, real parameter form, real generation,
real "open result directory" through `/api/open/<job_id>`.

| Case | Input | Template | `renderer_route` | `student_preparation_route` | `fallback_phase` | `fallback_reason_code` | Renumbering |
|---|---|---|---|---|---|---|---|
| Case1 training-only physics `X008.docx` | 1 file | 1v1 | **XML** | `BYPASS` (XML_STUDENTIZER, reviewed `C3-X008-CHIEF-FULL`) | **NONE** | — | `DISPLAY_RENUMBER_APPLIED` |
| Case2 ordinary knowledge lesson `X001.docx` | 1 file | 1v1 | **XML** | `V09_MAKE_STUDENT` (no reviewed Golden for X001) | **NONE** | — | `NOT_APPLICABLE` (no knowledge-point-free training split) |
| Case3 training-only physics `X008.docx` | 1 file | class | **XML** | `BYPASS` (XML_STUDENTIZER) | **NONE** | — | `DISPLAY_RENUMBER_APPLIED` |

All 3: `status=done`, `fallback_detail_reason_code=null`, teacher + student DOCX
published, `/api/open` returned `opened=true`.

Reading of Case2: `student_preparation_route=V09_MAKE_STUDENT` is the **frozen
Studentizer** decision for a sample with no reviewed Golden evidence, not a
renderer fallback — `renderer_route` is `XML` and `fallback_phase` is `NONE`.
Fallback success and XML success are recorded separately on purpose.

## WPS PRODUCT GATE

Every EXE output (3 cases × teacher/student = 6 files) went through
Open → SaveAs DOCX → Close → Reopen → Export PDF: **6/6 PASS**.

| Case | Role | Pages | SaveAs DOCX | Reopen | Export PDF |
|---|---|---:|---|---|---|
| Case1 | 教师版 | 17 | yes | yes | yes |
| Case1 | 学生版 | 11 | yes | yes | yes |
| Case2 | 教师版 | 62 | yes | yes | yes |
| Case2 | 学生版 | 77 | yes | yes | yes |
| Case3 | 教师版 | 20 | yes | yes | yes |
| Case3 | 学生版 | 13 | yes | yes | yes |

## PAGE-ONE ANCHOR ON PACKAGED OUTPUT

Measured from the WPS PDF exports of the packaged outputs.

| Case | Template | Target y1 | Measured y1 | Deviation | Clearance to footer band | Page 1 |
|---|---|---:|---:|---:|---:|---|
| Case1 teacher/student | 1v1 | 768.219 | 768.219 | **0.000** | 24.031pt | yes |
| Case2 teacher/student | 1v1 | 768.219 | 768.219 | **0.000** | 24.031pt | yes |
| Case3 teacher/student | class | 745.899 | 745.899 | **0.000** | 24.001pt | yes |

## PACKAGING ENVIRONMENT NOTES (not product defects)

This machine has Windows PowerShell 5.1 only (no PowerShell 7), which exposed
two environment-level blockers in the existing flow:

1. PyInstaller 6.x writes its INFO log to **stderr**; under
   `$ErrorActionPreference='Stop'` PowerShell 5.1 turns native stderr into a
   terminating error. The PyInstaller step was therefore driven directly (same
   spec, same distpath/workpath, `C4_REPO_ROOT` set) and the script itself was
   then run with `-SkipBuild` for validation and inventory.
2. The venv's Flask 3.1.3 prints a `DeprecationWarning` to stderr, hitting the
   same PowerShell behaviour. Suppressed for the run with
   `PYTHONWARNINGS=ignore`; no script change.

One real packaging fix was committed: `[Security.Cryptography.SHA256]::HashData`
and `[Convert]::ToHexString` require .NET 5+, and PowerShell 5.1 runs on .NET
Framework 4.x, so the package tree hash now uses `SHA256.Create()` +
per-byte hex. Algorithm and output are unchanged.

## KNOWN LIMITATIONS

- `X012真实数学讲义.docx` (SHA `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779`)
  is fail-closed at routing (`generic heading and practice content share atomic
  table b2`) and falls back to the frozen V0.9 whole-job path with a persisted
  reason. Documented P0 `TABLE_SLOT_CONFLICT`, not fixed this round.
- Physics 热量比热容 解析版 is fail-closed (`unclassified section at b192:
  【巩固训练】`) and falls back the same way.
- Release corpus XML success rate is unchanged at 22/27 on the production
  `render_slots` path; the 5 failures are pre-existing routing refusals, not
  regressions.
- The EXE UI does not surface `renderer_route`; route evidence is in the job
  record and in this report only.

## POST_V1.2_BACKLOG

1. `X012` atomic-table slot conflict (`TABLE_SLOT_CONFLICT`).
2. Unclassified `【巩固训练】` section handling for 热量比热容-style handouts.
3. UI surfacing of `renderer_route` / fallback reason for end users.
4. 6 PRE_EXISTING test failures (2 in `tests/`, 4 in
   `v1.1-stable/res/app/webapp/test_app_api.py` when the whole repository is
   collected).
5. Launcher port robustness: Windows `SO_REUSEADDR` allows a second bind on
   5128, so a squatter process can answer before the launcher's own server.
   Observed with a stale UAT server during this round.
6. `tools/release/build_c4_onedir.ps1` is UTF-8 without BOM and contains Chinese
   paths; PowerShell 5.1 parses it as ANSI. Consider adding a BOM or removing
   the non-ASCII literals.

## EVIDENCE

- `C:\xml-uat\v12-closeout-20261006\exe-uat-result.json` — EXE UAT, all route
  fields.
- `C:\xml-uat\v12-closeout-20261006\exe-wps-gate.json` — WPS gate, 6/6.
- `C:\xml-uat\v12-closeout-20261006\exe-layout.json` — page-one measurements.
- `C:\xml-uat\v12-closeout-20261006\exe-wps-page1\*.png` — page-one snapshots.
- `%LOCALAPPDATA%\C4\v1.2-onedir-output\PACKAGE_INVENTORY.json` — full file
  inventory with per-file SHA-256.
- `docs/v2/integration/fixtures/V1_2_RELEASE_CANDIDATE_2026-10-06.json` —
  machine-readable index of this round.

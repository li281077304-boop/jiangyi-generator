# Product defect closeout — migrated environment checkpoint

Status: TEST_PACKAGE_BUILT; real EXE acceptance remains BLOCKED. No release PASS, tag, main merge or coverage claim.

## Recovered environment

- Repository: `H:\AI-Workspace\work\jiangyi-generator`, branch `feature/v1.2-c4-release-engineering`.
- Verified remote/build commit: `92dce149302c73fafef49b9eddac63a100b1edab`.
- Python: `H:\AI-Workspace\uat\xml-uat\release-recovery-20261008-build\venv\Scripts\python.exe`; PyInstaller 6.22.3.
- Build/work/output, temp, Python scratch, pip/PyInstaller caches, logs and new UAT profile use H. Existing D/C sources and evidence were not deleted or relocated.
- `tools/product_rescue/closeout_h_env.ps1` configures only the invoking process and its children. This does not move AppData or reconfigure Codex globally.
- Playwright uses Chrome explicitly. The launcher selects installed Chrome without a system-default browser fallback. No Edge/account login.
- Immutable frozen evaluation manifest unchanged: SHA-256 `c3efed7b9cd135f4b45c7092d9070013878badfcddc08ee872a2b06a9b6273b1`.
- All 66 canonical case configurations resolved and original input hashes verified. Additional ZIP members 40/40 and fixed sources 27/27 verified; this is source verification, not generation coverage.

## Built test package

- ZIP: `H:\AI-Workspace\build\closeout-20261009\package\讲义生成器_V1.2_缺陷修复测试版_20261009.zip`.
- Size: 133652128 bytes.
- ZIP SHA-256: `ef0b1c2750f9c07dc81449ca086d42f4176ff1e55ee294ccae3200d1cb253ebe`.
- EXE SHA-256: `4a6c55d06e11c342428d6d025c6e86c13c97997052db196988de48c98a340757`.
- Build commit: `92dce149302c73fafef49b9eddac63a100b1edab`. Subsequent checkpoint changes concern evidence/tools only; they are not a newer binary build.
- Package audit: 1276 files / 288203722 onedir bytes; forbidden content scan and source-to-stage hashes PASS. No user documents/corpus/dev caches included. Frozen V0.9 templates verified.
- Packaging status is not EXE/WPS acceptance.

## Gates verified in this resumed round

- Launcher + defect tests: 19 passed, including the two formerly affected by a live service/mutex.
- Stage2 unit checks: 40 passed. Do not substitute this for real corpus boundary accuracy.
- Stage3 regenerated predictions: QG 408/408; sections 369/369; subquestions 328/328; MISS/FP/MERGE/SPLIT zero; QG exact 358/408 (87.745%), not 100% exact.
- V0.9 frozen assets 10/10; original sources 27/27 unchanged.
- Python compilation, workspace/browser runner JavaScript syntax and diff checks passed.
- Full regression attempt is recorded separately; no full PASS is claimed.

## Inherited evidence, not repeated

Oxygen repair at `53d0e709a1ec4dd8b55afc707cb90f957374b074` selects one equivalent MC textbox representation in a separate XML projection, preserving immutable raw sources. Original-content integrity remains enforced. Both templates produced XML teacher/student through source API; four WPS Open/SaveAs/Close/Reopen/PDF outputs retain the missing reminders. Evidence remains in `D:\product-defect-closeout-20261008\gate1`.

Disk preflight runs before multipart spooling, job allocation and queued execution, with expanded input estimates and explicit 507 errors; no cleanup of user files. Prior real EXE insufficient-space refusal evidence remains in `D:\product-defect-closeout-20261008\low-space-refused.log`.

Geometry pair refusal is due to 4219 teacher package entries exceeding the 4000-entry batch cap; it is not the expanded byte size. Limits remain unchanged. A teacher-only XML output was observed earlier; final two-template independent teacher/student EXE/WPS acceptance is pending. Do not count supplemental singles as canonical pair success.

## Current blocker and next action

Automatic approval rejected the operation to start the EXE and open its workbench, returning only a policy block without a specific reason. No alternative shell/tool was used to bypass it. User was asked to open the test EXE; no confirmation was received at this checkpoint.

Until actual EXE startup is available, new Chrome task/reconnect/restart evidence, oxygen final-binary checks, geometry singles, all 33 topics × both templates, and current-package WPS/content comparisons remain pending. Historical 22 XML / 10 compatibility / 1 rejection and 31/33 shared safety results are references only, not updated counts.

Resume with the built candidate and H profile; complete the original defect gates. Do not repeat the already approved Golden/capability research, expand alignment/OOXML scope, create tags, or merge main.

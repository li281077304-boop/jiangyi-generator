# OCR-free test package + mandatory knowledge content — 2026-10-09

STATUS: SCOPED_IMPLEMENTATION_AND_PACKAGED_CHROME_UAT_PASS. Test package, not formal release.

## Package

- Build commit: `b8d773a09433e8dc67c39ce57e6ee996da41f2c8`.
- ZIP: `H:/AI-Workspace/build/slim-knowledge-20261009/package/讲义生成器_V1.2_无OCR测试版_20261009.zip`.
- ZIP bytes:21,268,740 (20.28 MiB).
- Onedir bytes:40,684,102; full ZIP extracted files including README/manifest:40,732,696 (38.85 MiB).
- Old onedir288,203,722 bytes; onedir reduction85.88%.
- ZIP SHA256:`87bf5334fa0c70aaa29938bfbd0cbe50382082bdc1657c963ecc74bab686be11`.
- EXE SHA256:`86b96187238892b335d6a79e392e6c8cd1f0aaeae2b15b7f5a53b0cc6858e513`.
- Runtime files209. ZIP entries211; manifest inventories210 files (excludes manifest itself). All210 ZIP member size/hash values verified.
- OCR models/RapidOCR/ONNX Runtime/OpenCV/NumPy/Shapely/pyclipper/experimental image_role_evidence absent from package. Production OCR calls/config removed; OCR lock no longer installed by build script. Historic experiment code/models/evidence remain outside the product package. No model downloads or OCR installation workflow.
- Ordinary Pillow and structural image/table/formula/OLE preservation retained. AVIF decoding plugin excluded; source resources are copied structurally rather than decoded. No unsupported AVIF recognition claim.
- Fresh CPython3.12.10/PyInstaller6.22.3 venv from non-OCR lock; pip check, build/package forbidden-content audits and V0.9 asset verification pass. No system Python or repository is needed to run the onedir.

## Knowledge contract

Original knowledge material retained. With no independent source knowledge, reserve first complete question/group as source example, then split remaining whole groups about70:30. This is not AI-created knowledge or a duplicate of a training question; warning and evidence explicitly record SOURCE_EXAMPLE. Subquestions/shared passages/answers remain together, student consumes its own source. With fewer than three usable groups, use explicitly marked source preservation, not fake three-slot success. Knowledge section never omitted; empty final knowledge refuses publication. Pure20-question contract is now1 example+13 immediate+6 final, superseding20-question14+6 with an empty knowledge slot.

## Scoped machine gate

88 tests passed+8 subtests,29.77s. Includes whole-group partition, empty-slot degradation, both templates, original knowledge, source example/shared answers, no duplicate question text, concentrated answer areas, media provenance, package exclusions, product normalization/integrity, batch/partial/restart lifecycle mocks, workspace feedback and refresh initialization. Lifecycle renderer test doubles now populate synthetic knowledge content under the new contract; they are not evidence of semantic recognition. No production guard is disabled for tests.

Python compile/PowerShell script parsing/diff check pass; frozen V0.9 assets10/10 unchanged. Full regression and35-topic evaluation have NOT been rerun on this build.

## Normal EXE + Chrome UAT

Normal launcher executed with no server-only switch, owned new EXE processes5148/10972. Flask ready authenticated, page200, Chrome opened. Prior old test service was shut down via authenticated endpoint only after zero active jobs and matching executable ownership. No user output/job files deleted. Development/build/venv/temp/cache/logs/browser profile onH; publication uses actual Desktop result directory `D:/Documents/生成讲义结果` as product contract.

Chrome CLI actual DOM uploads, English original grammar/cloze pairs, both templates:

| Case | Job | Result |
|---|---|---|
| grammar1v1 |686757c2243c4509bd002267903f68ea|XML/done/SLOTTED, teacher+student|
| grammarclass |6418b9d1903c4ca28e869a7942c946f6|XML/done/SLOTTED, teacher+student|
| cloze1v1 |870418abed3e47e580da43554681a0a8|XML/done/SLOTTED, teacher+student|
| clozeclass |3f2a1e0205184d52b3c9949caa62dd73|XML/done/SLOTTED, teacher+student|

8 final DOCX, knowledge and two training sections verified; final Product Integrity accepted, recorded final SHA matches current bytes. Uploaded raw hashes8/8 match immutable English originals. Refresh restores latest completed job; UI shows讲义已生成/已分槽 and engine control is not visible. Final screenshot saved separately from initial screenshots taken before UI polling caught up.

Actual finished artifacts are listed in `fixtures/slotted-closeout-20261009/slim_exe_browser_evidence.json`; directory `D:/Documents/生成讲义结果/`, with高三/英语 metadata. Current test service remains available at127.0.0.1:5128; CLI automation browser closed after evidence capture.

## Acceptance limits

- Current candidate WPS Open/SaveAs/Close/Reopen/PDF and document visual/page acceptance not completed. Prior WPS RPC0x800706BA is unresolved; no repeated WPS stress test or Word substitution.
-35-topic>=32 final evaluation, representative oxygen/geometry/incident/X12.4 UAT, final full regression/Stage3 remain pending under original plan. This report does not infer those from the8 English outputs.
- Compatibility now also rejects an empty knowledge section; no new actual COM fallback UAT on this candidate. Preserve originals, inspect warnings.
- Actual Worker model identity not exposed. Chief not invoked:CHIEF_UNAVAILABLE. No independent Chief or formal release PASS claimed.
- No tag, main merge, Installer or release continuation.

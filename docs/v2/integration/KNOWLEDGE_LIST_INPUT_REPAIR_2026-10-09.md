# English knowledge-list input repair — 2026-10-09

Status: source production-path and updated normal EXE / Chrome ZIP checks PASS. Not release acceptance.

## Real failure

Original browser batch `893a7d68cb644a358b87af4d226c317d` rejected the dictation source and treated recitation as teacher-only. Its child `50ce77af74ae44228760b0a2ea31cad3` switched to V0.9 on `UNSUPPORTED_BOOKMARK_SCOPE`, then failed package validation with duplicate drawing IDs. Pronoun upload reproduced the version-grouping defect.

Sources recovered from the user's H-drive temporary uploads, not generated outputs. Adverb recitation original SHA `7af222717b88dd606304bb732a68ef539dfdd44a3119a213530fdd9e9d946958` matches the failed job provenance. Four original source hashes and ZIP member chains are in `fixtures/knowledge-list-repair-20261009/sources.json`.

## Bounded changes

- Treat explicit 背诵版/默写版 suffixes as filled teacher/student sources and strip only version markers when grouping. Different topics remain independent. Student consumes only its own source.
- Broken internal navigation targets absent from the entire source no longer force whole-job fallback. Remove only the dangling anchor, retaining visible runs/resources and other relationship attributes. Missing IDs, ambiguous targets, cut bookmark pairs and existing targets outside selection still reject. Counters record removed anchors.
- Recognize the explicit 优题精练 column as practice. Inline answer/analysis paragraphs remain attached to their question; only standalone global answer headings suppress answer-list question enumeration.
- Frozen Writer, OCR-free packaging, product checks and source originals unchanged. The V0.9 duplicate-drawing defect remains a separate limitation; no validator bypass or frozen Writer patch.

## Checks

72 focused tests + 7 subtests PASS; 18 additional product integrity / degradation checks PASS. Diff whitespace check PASS.

Real sources: adverb and pronoun × 1v1/class × teacher/student = 8 DOCX, all done / XML / SLOTTED. Metadata chosen explicitly as 高三 / 英语; the first diagnostic run used an older runner's 九年级/物理 default and is superseded by final evidence. Each final artifact passed package and Product Integrity checks. Teacher inline answers stay with each whole exercise; original student source used directly. Evidence includes original provenance, final slot counts/hashes and degradation attempts.

WPS visual acceptance not performed this round. Frozen 35-topic acceptance not rerun; these two real cases do not imply 32/35 PASS. Chief not invoked: CHIEF_UNAVAILABLE. No release tag, main merge or Installer.

## Updated Windows test package and real browser

Build commit: `b3b1e660bcb06a2c98e1d20d32924632e436e54c`, pushed and remote verified.

ZIP: `H:/AI-Workspace/build/knowledge-list-repair-20261009/package/讲义生成器_V1.2_知识清单修复测试版_20261009.zip`, 21,268,472 bytes; SHA256 `13b7c0347036dd31424792c01170fe8ea7680c61b0a6a116681803312d04bf0f`. Reused the existing exact-pinned OCR-free build environment, with fresh PyInstaller output/work directories. Forbidden-content package audit PASS.

Runtime onedir: 40,685,304 bytes. EXE SHA256: `acef8a3d16983c7713b93da2788b6e3774d3d1a0ccf6e20fb49ac0a7028f0cc0`.

Authenticated safe shutdown of old service after no active jobs; normal new launcher started with the same H profile, preserving job history. Service owner verified and authenticated readiness PASS. Combined launch command was rejected by automatic execution review; separated, explicit normal-launch command succeeded. Normal launcher remains on port5128, no hidden server-only substitute.

Chrome actual uploads: original adverb/pronoun ZIP × 1v1/class, four batches each resolved to one teacher/student pair, all done / XML / SLOTTED with eight final DOCX on the real Desktop D drive. Refresh restores completed task and displays one slotted topic, zero failures. Missing metadata remains an explicit warning, not invented content. Evidence: `packaged-browser-evidence.json`, `completed-after-refresh.png`, `test-package-report.json`. No packaged WPS visual claim.

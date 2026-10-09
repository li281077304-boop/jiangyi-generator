# English knowledge-list input repair — 2026-10-09

Status: source production-path checks PASS; updated packaged browser checks pending. Not release acceptance.

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

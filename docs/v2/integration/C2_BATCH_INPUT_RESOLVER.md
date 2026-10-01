# C2 Round 1 — Batch Input Resolver

Worker: GPT-6.1 (`gpt-6.1-sol`). Chief review is pending; this report does not claim `C2_BATCH_PASS`.

Base: `7daa519bb804d5cb5fd4328636b2346e166ba81c`.

The C1 annotated checkpoint `v1.2-c1-uat-fix-2026-10-01` has object SHA
`a106901d757b171d226a802d56e66de8daadf1c6`; local and remote dereference both
point to the base above. `feature/v1.2-c2-batch` was created and pushed from it.

## Scope

`res/app/batch_inputs.py` adds an independent upload resolver. It does not
change approved C1 routing rules, invoke a renderer, or modify frozen code.
HTTP submission still has the C1 single/pair restriction until the next round.

- Direct DOCX and ZIP inputs expand to source records; ZIP entry directories
  remain provenance metadata. No archive-controlled filesystem path is written.
- Chinese filenames and nested directories are supported. `~$*.docx`, non-DOCX
  entries, and `__MACOSX` files are ignored.
- Absolute paths, `..`, Windows drive/UNC/alternate-stream paths, symbolic links,
  and duplicate archive entries are rejected. Limits are 200 DOCX files, 4,000
  archive entries, and 200 MiB of expanded DOCX upload bytes. The DOCX package's
  own expanded size also has a 200 MiB safety limit.
- Strong teacher/student labels and recognized revision/version suffixes are
  removed before topic comparison. Meaningful numbers such as `专题12` remain.
- Automatic pairing requires the same normalized topic and the approved C1
  filename/content classification. File size and upload/archive ordering are
  never pairing criteria. The exact supplied student bytes are retained.
- Separate mode produces independent items. Duplicate/contradictory roles,
  unknown versions, and damaged DOCX are item errors; other topics remain usable.
- Each logical input carries topic, input version, original source references,
  source provenance, classification evidence, and error. Per-item generation
  status, renderer, fallback reason and output paths belong to orchestration in
  the next round.

## Machine Gate

Executed with `C:\xml-uat\.venv\Scripts\python.exe`:

`pytest tests/test_batch_inputs.py tests/test_input_versions.py tests/test_stage2_baseline.py -q`

Result: **68 passed** (23 batch cases, 6 C1 classification tests, Stage2 39/39).

Batch tests cover five teacher items, three shuffled pairs, mixed versions,
Chinese ZIP directories, all required strong keywords, unchanged student bytes,
version normalization, damaged-source isolation, duplicate-role ambiguity,
explicit separate mode, and archive security/limits.

Frozen A-Line, B-Line renderer core, V0.9 runtime and the approved C1 Business
Rules have no diff against the base. Real batch generation, COM serialization,
WPS product UAT, performance comparison and fresh Stage3 regression remain
required before final C2 acceptance. No UAT or performance result is inferred
from resolver tests.

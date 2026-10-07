# V1.2 XML Finalization Progress — 2026-10-07

## Status

`V1_2_XML_FINAL_BLOCKED`

The working candidate is not release-ready. This report records current evidence and the blocking gates; it does not claim a final product pass.

## Baseline and working tree

- Branch: `feature/v1.2-c4-release-engineering`
- Baseline/local/remote HEAD at start: `cd7e4019ca3dcb8f0d95427e8300d72d7ae29031`
- Remote branch matched the local HEAD at start.
- The checkout already contained the uncommitted finalization implementation. It was preserved. Additional uncommitted changes in this turn are also still present; no commit or push was made because pair-alignment gates remain failing.

## Work completed in this turn

- Added a strict metadata-table predicate: a cover table must be exactly two rows by two cells, with the two expected field labels in the label column, nonempty values, and no embedded resource/table content. A question/data table that merely mentions the labels is no longer excluded.
- Added a regression test for a label-mentioning question table and a mixed-content table.
- Made image-role evidence preserve every image occurrence at a node instead of overwriting earlier images from the same paragraph.
- Bound a high-confidence `TEACHING_METADATA` image to a validated cover table only when it occurs before that table with no intervening nonempty content. In the real X12.4 source, OCR identifies b3 as the metadata-title image and b6 as `KNOWLEDGE_ASSET`; the current single-document route assigns b3/b4 to cover and b6 to `knowledge`.
- Added explicit subquestion-body comparison, including answer-filled blank matching and resource identity checks. An altered question body now fails closed instead of being silently accepted as aligned. Resource checks require exact table cell structure/text, exact OLE bytes, or single-frame image pixels with the same dimensions and at most one channel-value difference. Unsupported resource forms fail closed.
- Added a cover-route sentinel to the pair projection interface so `cover` ownership is distinct from teaching slots. This new pair-cover path has not yet passed a complete paired real-source integration test.
- Confirmed the app's normal user mode has automatic V0.9 fallback disabled by default; V0.9 is reachable only through explicit diagnostic configuration.

## Machine gates

- Focused metadata / OCR evidence / topic tests: `14 passed` before the latest paired-projection changes.
- Real source finalization and metadata ownership tests: `8 passed` after the metadata/image ownership changes.
- Canonical alignment tests: `2 passed, 2 failed` after strict whole-subquestion/resource checks. The two parameterized incident-pair tests (1v1 and class) fail closed before XML rendering. The negative altered-subquestion regression passes.
- `git diff --check`: passed at initial inspection; rerun is required after the latest edits.
- Full regression, browser UAT, packaged EXE UAT, and the fixed 48-topic coverage evaluation have not been run.

## OCR evidence

- Offline RapidOCR CPU inference ran against the original X12.4 student source using the already available local runtime environment and the checked-in ONNX models. No external API or network inference was used.
- The real source contains 35 image occurrences. The image-role pass recognized b3 as `TEACHING_METADATA` and b6 as `KNOWLEDGE_ASSET`; original DOCX bytes were not changed.
- Checked-in ONNX model files total 16,189,007 bytes. An external runtime-probe archive available under `C:\xml-uat\v12-ocr-eval` is 104,576,740 bytes. This probe archive is not the final PyInstaller package, so the actual RC ZIP delta remains unmeasured.
- No Windows EXE was built.

## Chief review

Codex GPT-6.1 Sol returned `PATCH` for the current alignment/OCR implementation. Confirmed blockers:

1. Previous logic could claim `ALIGNED` when a numbered student subquestion had no unique teacher counterpart. The fail-closed path and a negative regression were added, but the real incident pair now exposes additional supported-source differences that still need a correct structural mapping.
2. The X12.4 pair's repeated labels cannot be identified by number alone. The existing number-indexed algorithm still rejects repeated numbering; the pair has not been given a unique canonical occurrence map.
3. The previous cover metadata predicate could exclude an arbitrary question table. The predicate is now narrower, but paired cover ownership has not passed full end-to-end projection.
4. The X12.4 b3 metadata-title image previously routed into `knowledge`. A structurally bounded cover association was added and verified for single-source routing. The paired production path is not yet verified.

The Chief also confirmed that the old 2-versus-20 A-Line question-group counts do not prove 18 missing questions. The real source has corresponding complete question ranges; duplicate labels and structure must be resolved by ordered context, complete text, and asset identity.

## Coverage and release gates

- Fixed evaluation denominator: **not yet run**. Required set is 27 fixed topics + the incident topic + 20 distinct additional raw topics.
- Current measured XML coverage: **not available**; no numerator/denominator result is claimed. It must not be reported as 0% or as a conditional success rate.
- Incident pair direct DOCX/ZIP × both templates has not been re-run against a candidate that passes the current strict alignment checks.
- Topic normalization tests pass, but no fresh paired generation verifies teacher/student display topic consistency.
- Metadata source resolution is verified on X12.4 in isolation; cover-only ownership and no metadata leakage into paired teacher/student output remain unverified.
- EXE build/UAT is correctly gated off until alignment, fixed-set coverage, and source product gates pass.

## Next blocker to solve

Build an ordered, unique canonical map that validates each complete question occurrence and its subquestions/resources without treating repeated question numbers as global keys. It must accept only proven teacher/student counterparts and fail closed on genuine mismatch. Then pass cover ownership separately from teaching-slot routing and rerun the real incident and X12.4 pairs before starting the 48-topic audit.

## Alignment safety patch update — 2026-10-07

### Independent Chief review

- Verdict: `PASS` for the narrowly scoped student-blank provenance and OMML-location safety patch only.
- Chief independently verified the original student DOCX XML for incident question 49: underlined U+3000 whitespace exists across source paragraphs `b307/p304` and `b308/p305`; the StructDoc text projection had trimmed that evidence. The new raw-XML recovery is bounded to underlined whitespace runs and source paragraph ordinals.
- Chief independently verified the OMML placement guard: a teacher formula is accepted as a filled student blank only when one teacher OMML node is physically between U+3000 delimiters; moving the formula to the start of the paragraph is rejected.
- Focused non-pair safety tests: **11 passed**. This review does not approve complete pairing or product output.

### Current real-pair gate

- Incident pair remains `ALIGNMENT_UNRESOLVED` at question 27. Student nodes `b149-b150` contain the stem and one graph image; teacher nodes `b317-b320` contain the stem and A-D textual options. Offline OCR on the student image recognized circuit-graph labels/values (`I/A`, `U/V`, `R`, `R2`, `S`, numeric values), not A-D options. The pair does not currently prove the same complete question content. This is retained as a fail-closed blocker, not routed around.
- Incident question 49's cross-paragraph student blank is now recovered from original XML, but this does not clear the later question-27 blocker.
- X12.4 remains `ALIGNMENT_UNRESOLVED` at canonical occurrence `q-004`, repeated question number 1. Student blocks `b200-b203` and teacher blocks `b730-b731` do not yet have a complete ordered continuation mapping.
- Full alignment suite: **11 passed, 3 failed** (incident 1v1, incident class, X12.4 pair). The three failures are the two incident template parametrizations and the X12.4 real-pair gate. They must not be counted as XML product successes.
- `py_compile`: PASS for the alignment module and focused test module. `git diff --check`: PASS (Git emitted only existing LF-to-CRLF working-copy warnings).

### Remaining gates

- Pair projection and Route Once production path: blocked by the real source mismatches above.
- Fixed 48-topic coverage, OCR production ownership proof, Direct DOCX/ZIP browser UAT, WPS generation round trips, complete regression, Windows EXE build/UAT: not run; release remains gated off.
- No C4 release, EXE, tag, Installer, or V0.9 normal fallback was used.

### Run Journal — alignment safety round (2026-10-07)

- Worker: primary Codex agent; the active runtime did not expose a verifiable model label, so this entry does not claim GPT-6 Luna.
- Base SHA: `cd7e4019ca3dcb8f0d95427e8300d72d7ae29031`.
- Machine gate: focused alignment **11 passed / 3 failed**; `py_compile` PASS; `git diff --check` PASS (line-ending warnings only).
- Chief: Codex GPT-6.1 Sol, limited review verdict `PASS` for student XML underline-blank provenance and OMML placement checks only. Pair alignment/product verdict remains BLOCKED.
- Next action: resolve or formally retain the question 27 image-vs-options mismatch and X12.4 occurrence tail mismatch from source evidence; do not weaken fail-closed.
- Commit/push: implementation and evidence checkpoint `3ed8f6d424cedaeb65f36b260231c5ef8aa27fd4` pushed to `origin/feature/v1.2-c4-release-engineering`; remote HEAD verified equal. Other pre-existing working-tree edits remain uncommitted and preserved.

# C3 R8 — math/chem teacher source selection

**Recommendation: X012 mathematics + X023 chemistry. CANDIDATE_ONLY;
CURRENT_CAPABILITY_BLOCKED.** No full Golden review, transformation, derivative
UAT, performance benchmark or production provider is approved by this round.
Worker: actual GPT-6.1 (`gpt-6.1-sol`). Chief: Codex GPT-6.1 Sol, **PENDING**.

## Selection and review burden

| Teacher | Source WPS pages | Body children | Frozen QG / section | Dedicated answer-marker children | Marked nontext children | Main tables / OMML / OLE / drawings / textboxes |
|---|---:|---:|---:|---:|---:|---|
| **X012 math** | 30 | 794 | 56 / 34 | 136 | 95 | 9 / 786 / 9 / 18 / 0 |
| X014 math | 26 | 656 | 63 / 42 | 148 | 103 | 1 / 628 / 23 / 34 / 0 |
| X016 math | 48 | 1114 | 43 / 14 | 96 | 69 | 29 / 1549 / 0 / 39 / 0 |
| X020 chemistry | 18 | 399 | 25 / 12 | 76 | 0 | 5 / 0 / 9 / 38 / 16 |
| **X023 chemistry** | 32 | 630 | 43 / 29 | 112 | 0 | 12 / 0 / 1 / 220 / 0 |
| X025 chemistry | Not counted this round | 614 | 34 / 18 | 100 | 10 | 6 / 0 / 65 / 86 / 28 |

X012 already has complete approved Stage3 boundary Gold. It has fewer QGs,
marked answer-object paragraphs, OLE and drawings than X014; four fewer pages
alone do not make X014 safer. X016's 48 pages, 29 OOXML tables and 1549 OMML
increase whole-source review burden. X012 still requires manual review of
all 30 pages / 794 children, 56 frozen QGs and 136 marked paragraphs, including
knowledge fills, table-internal answers and missing physical-question coverage.
Stage3 boundary Gold is not Studentizer business Golden.

X023 avoids X020's current global textbox refusal and X025's marked OLE,
textboxes and numerous fields. X025 has approved Stage3 Gold but its object
burden is greater. X018/X027 are not expanded here (known global textboxes);
X022 is answer-only, not a complete teacher source. X023 review must cover all
32 pages / 630 children, 43 QGs, 112 markers, 12 tables and 220 drawings;
no elapsed-time estimate is asserted.

## Exact identity, spans and ownership limits

- X012: `专题1.5 有理数的乘除（高效培优讲义）…（解析版）.docx`;
  SHA256 `c9b31fe98b0ede8b0cefc5c3a11d8deab62c85c8a1181a54db25c7ca368b57a1`.
- X023: `1.2 化学实验与科学探究（题型专练）（解析版）.docx`;
  SHA256 `19fe81bd43f19e9acb2170b2d431452690c179cbecb4e4ee773f8e024eef0163`.
- Corpus authority: `C:\xml-uat\stage3-expansion\baseline_inputs.json`;
  genuine nested-ZIP provenance and exact names retained in evidence. Fresh
  corpus source hashes: **27/27 match**. No source was altered.
- Evidence `fixtures/c3-r8-subject-selection.json` contains **all frozen units
  and spans**, including every QG/section. Endpoints exist: X012 **486/486**
  (7 complex), X023 **370/370** (28 complex). Full node IDs are preserved;
  `bN → Block.seq → body_idx` is top-body context only, never deletion authority
  or a table-subnode flattening contract.
- Number/explicit-example text candidates: X012 **54**, including **18** outside
  frozen QG coverage; X023 **15**, including **13** outside. Automatic numbering
  and non-question numbered content make these diagnostic counts incomplete.
  **Physical question total and complete answer ownership: NOT_ESTABLISHED.**
- X023's 112 markers lie in answer/analysis + section spans (97 / 15);
  their frozen parent chains contain **no QG**. Thus they cannot be claimed as
  complete QG answer regions. Text previews suggest question answers (e.g.
  body[36] `【答案】D`, body[37] drug-amount explanation), but knowledge-fill versus
  complete question ownership still requires independent whole-source review.

## Blockers and evidence scope

X012: every marked paragraph has unsupported `w:shd`; 95 contain nontext and
142 marked OMML structures require future reviewed object-answer capability.
No main field; paired `_GoBack` bookmark. X023: no nontext in the 112 dedicated
marked paragraphs, but unsupported shading/paragraph formatting makes **0/112**
currently whitelist-plain; retained body[322] field ` = 6 \* GB3 ` is unsupported
by the current main-field boundary guard. Paired `_GoBack` at body[0] is not a
blanket bookmark approval. Both have retained header/footer graphics and page
fields requiring exact non-document preservation; no main revisions, comments,
content controls, note references or textboxes were detected. Inline/table
answers, material binding and cross-story dependencies still need full review.

Existing X011 (X012 student companion) and X021 (X023 companion) are references
only: prior R4 exact-pair audit did not establish a complete structural-subsequence
oracle. It was not rerun. No new expected DOCX/removal ledger is created.

Real KWps.Application read-only opens/counts, 2026-10-01 13:26:38–13:26:42 UTC,
returned the five listed page counts; sources unchanged. WPS counted X016 28
tables versus 29 OOXML `w:tbl`; these are different inventory scopes, not a
mapping proof. **Source page counting is not derived open/save/reopen/PDF or
visual UAT. Performance: NOT_RUN.**

Reproduce: `tools/studentizer_audit/select_subject_candidates.py --corpus
C:\xml-uat\stage3-expansion --pages
C:\xml-uat\c3-round8-selection\source-wps-pages.json --out <diagnostic.json>`.
This only reads sources and writes diagnostic JSON. No renderer/Studentizer
invocation or production/frozen change. Next: Chief selection review, then
separately authorized full source Golden and capability work; no C3 completion.

## Machine Gate — 2026-10-01

**PASS, selection diagnostics only:** focused suite **235/235 in 52.70s**, including
Stage2 **39/39**; fresh eight-source Stage3 QG **408/408**, sections **369/369**,
subquestions **328/328**, original Recall **100%**, E1–E4/MISS/FP/MERGE/SPLIT **0**.
Overall exact QG boundary remains **87.7%**, not 100%. Frozen V0.9 assets **10/10**
match baseline `0922e08631226b95a77a6599bbc0ac3784e9134b`. Compile/diff checks
pass. No production source or frozen core changes; new files are diagnostic
script, evidence, two focused tests and this report. Chief verdict remains PENDING.

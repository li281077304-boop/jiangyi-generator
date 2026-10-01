# C3 Round 4 — real Golden candidate audit

Base: `8a8b1724bc6bdae6506483084973e8b084d5f7fd`.
Worker: actual GPT-6.1 (`gpt-6.1-sol`). Chief: Codex GPT-6.1 Sol,
independent review pending. **0 approved complete manifests, 0 XML Studentizer
derivatives, no C3 completion or real zero-COM/performance claim.**

Final combined machine gate: **177 passed in 49.46s**, including Stage2 **39/39**,
all existing 174 Studentizer/C2 focused checks and 3 exact-audit checks. Fresh
Stage3: QG **408/408**, sections **369/369**, subquestions **328/328**, original
Recall **100%**, E1–E4/MISS/FP/MERGE/SPLIT **0**, source hashes **8/8**. Overall
exact QG boundary rate remains **87.7%**. Frozen V0.9 assets **10/10**.
Python compilation/diff checks pass; production Studentizer, orchestration,
A-Line/C1/B-Line/V0.9 core remain unchanged in this audit round.

## Scope and method

Fresh read-only evidence: `C:\xml-uat\c3-round4-real-pairs\`.
The repeatable `tools/studentizer_audit/audit_real_pairs.py` inspects the 27
genuine corpus sources and their exact-topic explicit original/solution suffixes.
It inventories every main-body child, complete source/semantic identities,
physical addresses, C14N fingerprints, preserved feature/resource inventories
and all existing frozen A-Line QG/section/span units. Diagnostics are marked
`DIAGNOSTIC_ONLY_NOT_REVIEWED_GOLDEN`; they cannot be loaded as approved
`CompleteStudentEvidence`.

The tool counts exact ordered structural subsequence embeddings, capped at 2.
It refuses to choose the first equal node when duplicates occur. It also checks
an exact expanded-name XML tree digest that ignores namespace declarations only
and retains every attribute, text, child order and tail. No text similarity,
question-string matching, color/role deletion or offset correction is used.
Neither digest authorizes deletion; the audit is narrower than semantic
equivalence and does not classify a formatting difference as a lost question.

All **27/27** original source hashes match the inventory and remain unchanged.
Fourteen exact-topic filename candidates were inspected: thirteen full
original/solution pairs and one chemistry answer-only companion. **All 14**
have zero full ordered student-subsequence embeddings under both exact tree
definitions. This disproves simple whole-unchanged-paragraph deletion as an
exact oracle transformation; it does not prove content corruption.

## Genuine corpus candidates

| Teacher / original | Subject | Direct body blocks | Exact C14N student blocks absent from teacher | Ordered table subtrees identical |
| --- | --- | --- | --- | --- |
| X001 / X002 | physics | 928 / 494 | 151 | No (17 tables) |
| X004 / X003 | physics | 859 / 396 | 152 | No (6) |
| X006 / X005 | physics | 862 / 357 | 328 | No (4) |
| X008 / X007 | physics | 264 / 145 | 43 | No tables |
| X010 / X009 | physics | 302 / 168 | 57 | Yes (1) |
| X012 / X011 | mathematics | 794 / 221 | 14 | No (9) |
| X014 / X013 | mathematics | 656 / 223 | 9 | Yes (1) |
| X016 / X015 | mathematics | 1114 / 299 | 23 | No (29 / 28) |
| X018 / X017 | chemistry | 399 / 207 | 205 | No (8) |
| X020 / X019 | chemistry | 399 / 192 | 192 | No (5) |
| X022 / X021 | chemistry | 120 / 334 | 334 | Answer-only companion, not a full teacher oracle |
| X023 / X021 | chemistry | 630 / 334 | 159 | No (12) |
| X025 / X024 | chemistry | 614 / 328 | 328 | No (6) |
| X027 / X026 | chemistry | 530 / 278 | 273 | No (7) |

### Physics X008 / X007 — no-table candidate still unsupported

Teacher direct-body indices `3/5/9/15` contain field systems; bookmarks or
hyperlinks occur at `3/4/6/7/8/9/10/11/12/13/18/19/57/158`.
The current standalone policy refuses these boundary systems globally. Source
title drawing geometry and TOC cached pages differ before any question answers.
The first dedicated answer at `body[24]` is followed by a multi-paragraph `【详解】`
region. Current one-terminal-plain-answer bindings cannot remove its complete
analysis region. The original also has differing knowledge-fill paragraphs,
not just inserted whole answer paragraphs. Frozen QG counts 29 versus 32 are
diagnostics, not an independent content-equivalence certificate.

No complete answer-only deletion plan is invented. X010's immutable table is
positive local evidence, but its field/boundary/inline-answer and full-region
coverage remain unproved.

### Mathematics — immutable table is possible locally, insufficient globally

X014/X013's single table at teacher `body[4]` has an **identical full C14N subtree**
and expanded-name tree, including its formatting/content. This is concrete
support for a future narrow Studentizer policy that treats that table as one
unchanged physical block. It does not require any B-Line change.

The pair still cannot use today's approved paragraph-only mutations. Original
knowledge paragraphs `body[9]/body[10]/body[14]` contain blanks where the teacher includes
answers within retained knowledge content. Whole-paragraph deletion would
remove teaching text. The source has a bookmark at `body[654]`; all answer/analysis
regions would still require exact reviewed ownership. Nine original body nodes
are absent as exact teacher subtrees. X012/X011 and X016/X015 additionally have
different table content/structure; X016 has 29 versus 28 tables.

### Chemistry — no complete in-scope original/solution pair

Full teacher candidates have table differences and several contain textboxes.
X022 is a separate answers-only companion with 120 body nodes and no tables,
whereas X021 is a 334-node full original with 12 tables; matching topic does not
turn the companion into a full teacher source or answer ownership manifest.
No forced pairing/deletion plan is created.

## Existing C2/C1 generated sources as migration oracles

Inspected actual **pre-render derived student source** files under runtime,
not slotted final DOCX. Final output-to-output shape comparisons cannot prove
source answer removal, since C1 intentionally moves content between slots.

C2 Round 6 Case A supplies five distinct teacher conversions: X001/X004/X006
(physics) and X023/X025 (chemistry); **no mathematics input** is present.
Case C/D add two repeated X004/X006 conversions. C1 adds X012 mathematics and
two X021 chemistry conversions. The audit therefore inspected **10 existing
derivatives**, representing seven distinct input hashes (including X021).

| Distinct source | Example legacy body count | Diagnostic feature changes |
| --- | --- | --- |
| X001 | 928 → 1486 | OLE 332→99; drawing 101→91; frozen QG 62→24 |
| X004 | 859 → 1222 | OLE 497→147; drawing 73→64; QG 78→78 |
| X006 | 862 → 1170 | OMML 127→105; drawing 81→62; QG 60→58 |
| X023 | 630 → 660 | OLE 1→0; numbering 48→60; QG 43→44 |
| X025 | 614 → 734 | OLE 65→18; drawing 86→84; QG 34→25 |
| X012 (C1) | 794 → 1067 | OMML 786→662; drawing 18→17; QG 56→42 |
| X021 (C1) | 334 → 364 | numbering 48→60; QG 44→44 |

All ten have zero exact full expanded-name ordered student embeddings, changed
table subtrees and zero remaining explicit marker candidates. Blank insertion,
color stripping and WPS normalization change physical paragraphs, relationships,
styles and numbering. Counts alone cannot establish whether a removed object
was an answer or preserved material. Marker absence alone cannot prove complete
answer treatment; residual unmarked answers have not been independently reviewed.

X021 is a genuine **student original** in the corpus, renamed teacher for that
C1 input-semantic UAT. It is not a valid teacher/student business oracle; its
nonanswer red content must not become deletion authority.

Legacy WPS/package/selected-page observations remain historically valid for
their original purpose, but none provides a complete reviewed classification
of every answer/removal and retained question/material/media object. No existing
C1/C2 pair is promoted to trusted Gold. All 10 legacy source/oracle files remain
unchanged. Global counts in this table are **audit signals**, not claims of
missing classroom questions or new frozen V0.9 bugs.

## Immutable table decision

A future independent scoped round may permit tables only if every table is an
immutable subtree, no deletion/owner interval intersects or crosses it, bound
materials remain attached, all original table/resource relationships survive,
and the independently reviewed complete Golden agrees. Existing Studentizer
already validates retained fingerprints and unchanged non-document parts, so
this can be implemented there without changing A-Line or B-Line.

The X014 and X010 table evidence supports that isolated capability. **It does
not solve inline knowledge blanks, multi-paragraph analysis, answer formulas or
boundary systems.** Lifting the blanket table restriction now would not create
a valid complete real Golden for any inspected pair. No production policy is
expanded in this audit round.

## UAT and next action

**No approved derivative exists, so real WPS derivative open/save/reopen/PDF and
visual UAT were not run.** The environment is not represented as blocked; there
is simply no safe complete XML Studentizer output to test. No staged source was
modified to manufacture a successful fixture.

The current production remains fail closed per item with untouched whole-job
V0.9 fallback when complete coverage is absent. This round is an evidence/gap
gate, not real XML Studentizer PASS or C3 completion. The next independent Chief
decision must select narrowly reviewed immutable/partial-answer/boundary scope
work or obtain a suitable genuinely simple paired source. No source fuzzy
matching, unreviewed Gold, frozen-core change, UI, release or installer work
is authorized by this report.

### Concrete manual-Golden approach for a separately reviewed next round

Zero accepted pre-existing pairs is **not proof that manually reviewed real
Golden is impossible**, nor a reason to claim C3 complete. A source-authored
Golden may be built independently of strict paragraph equality with an oracle:

1. Select X014 (math), X008 (physics) and X023 (chemistry) as review candidates,
   without declaring them supported. Freeze original hashes and inventory every
   direct physical `body[index]`, every frozen QG/section/span and each XML leaf
   and resource. Direct body indices are not inferred StructDoc `bN` coordinates;
   body-level nonparagraph bookmark nodes can make the two sequences differ.
2. Independently inspect all source/original pages and each answer-region diff.
   Classify knowledge, prompts/options, bound material, tables/media/formula and
   every answer/analysis range. Exact physical location plus full fingerprint
   supplies the address; original-file content is business-review evidence,
   not a text-search locator. Mark every mismatch as retained layout difference,
   proven answer edit or unresolved; unresolved means no approval.
3. Construct expected student XML by only those explicitly reviewed operations
   on the **original teacher bytes**. Keep tables, resource parts, relationships
   and all undeleted content exact. Include full-coverage classifications,
   each mutation's owning teaching/question component, protected content,
   exact expected before/after fingerprints and whole resulting document hash.
   Compare its pedagogic content to the known original, listing every allowed
   layout/field difference. Independently approve the full Golden before use.
4. Separately review the required Studentizer capability changes: immutable
   tables, exact disjoint multi-paragraph answer ranges, precise inline
   knowledge-fill removal and preserved boundary systems. These are new scope,
   beyond today's approved paragraph-only module; annotation alone cannot make
   the current module execute unsupported edits. No A-Line/B-Line/V0.9 changes.
5. Gate actual teacher-only preparation, complete source-to-student preservation,
   all answer removal, normal XML/no-V0.9 path and real WPS open/save/reopen/PDF
   with relevant-page visual inspection. Stop any sample whose review is not
   complete rather than inventing a deletion plan.

This concrete review plan keeps exact structural addresses and independent
content approval. The current round supplies diagnostic inventories for it,
not a falsely approved Golden or a human-content-review PASS.

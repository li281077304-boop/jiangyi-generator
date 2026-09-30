# Stage3 E4 Boundary Recovery — 2026-09-30

**Gate: PASS** — the focused parent-span recovery removes the independent E4 case while preserving the protected Stage3 metrics.

## Root cause and rule

For some question groups, the detector emitted an ordinary parent interval ending at an internal candidate (for example, a shared-material or child-content boundary). Numbered child prompts after that point were therefore outside the parent question span, even though a later reliable question boundary closed the group. In X019 this also caused `b177–b178` shared material to absorb the following subquestions.

The builder now extends a parent interval only when its ordinary cutoff is an internal candidate, at least two numbered subquestions occur in the candidate-to-boundary range, a subquestion occurs after the ordinary cutoff, and the next non-nested candidate is a reliable closing boundary. Table content and shared material remain separate role units. Inline shared material stops before the first numbered subquestion; the question group retains its full parent span and binds to the material unit. A regression fixture covers this overlap and binding behavior.

## Acceptance evidence

Fresh eight-sample output: `C:\xml-uat\stage3-e4-after\goldcompare.json` and `goldcompare.md`.

- QG: precision 100.0%, recall 99.8%, exact boundary 357/408 (87.5%); MISS 1, FP 0, MERGE 0, SPLIT 0.
- Sections: precision, recall, and exact boundary all 100.0%.
- E4: 0 (down from 1); E2 remains 1; E4_SECONDARY remains 3; E3 remains 0.
- Original-paper recall remains 100.0%.
- Against the immediately preceding E3 output, exact boundaries improved from 354/408 to 357/408: X004 +1, X006 +1, X019 +1; the other five samples were unchanged.
- `tests/test_stage2_baseline.py`: 27 passed (all zero-argument test functions invoked directly because `pytest` is unavailable in the active Python environments).
- `tests/test_e1_question_recovery.py`: 13 passed; `tests/test_gold_compare.py`: 24 passed.
- Gold schema: 8/8 samples, 0 issues. `py_compile` and `git diff --check` passed.

## Scope and limits

No Gold annotations, E1/E2/E3 logic, renderer, UI, COM, V1.1, or release artifacts changed. E2=1 and E4_SECONDARY=3 remain outside this E4 patch. The eight-sample comparison is the measured corpus gate; it does not establish behavior on unmeasured documents.

## Stratified results and source-integrity checks

The same GoldCompare output reports these exact-boundary counts by subject:

| Subject | E3 before | E4 after | Gold QG | Precision | Recall | Exact boundary |
|---|---:|---:|---:|---:|---:|---:|
| Mathematics | 90 | 90 | 94 | 100.0% | 100.0% | 90/94 (95.7%) |
| Physics | 169 | 171 | 216 | 100.0% | 100.0% | 171/216 (79.2%) |
| Chemistry | 95 | 96 | 98 | 100.0% | 99.0% | 96/98 (98.0%) |

By document type:

| Type | Gold QG | Precision | Recall | Exact boundary |
|---|---:|---:|---:|---:|
| Original paper | 180 | 100.0% | 100.0% | 180/180 (100.0%) |
| Parsed solution | 228 | 100.0% | 99.6% | 177/228 (77.6%) |

The eight staged source DOCX files were independently checked against their expected SHA-256 values: 8/8 matched. No source or Gold files were changed.

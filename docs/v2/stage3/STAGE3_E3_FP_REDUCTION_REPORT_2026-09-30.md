# Stage3 E3 False-Positive Reduction — 2026-09-30

**Gate:** `PASS` — both remaining E3 false positives removed with structural, generalizable exclusions.

## Findings and correction

- **X012 / b34 / order 47:** `3.` is the third item in a numbered explanatory list below an explicit `知识点` heading. It describes how to form a reciprocal and ends as an instructional note; it has no question marker, formula object, options, or answer. The recovery gate now suppresses this procedural note only when the nearby source structure confirms the preceding numbered knowledge list. Complete prompts under R2/R5 remain eligible.
- **X013 / b4.r0c1.n4 / order 9:** this is item 5 in a six-item learning-objectives cell beside the `教学目标` label. The table reader now excludes a same-row sibling cell only when it contains a sequential, verb-led objective list. X013 now matches all 38 approved QG starts.

The two changes address only E3. No Gold, E1, E2, E4, section, or shared-material logic changed in this round.

## Machine gate

- `tests/test_e1_question_recovery.py`: 13 passed, 0 failed (includes a protection case for a complete dispatchable example inside a knowledge list).
- `tests/test_stage2_baseline.py`: 26 passed, 0 failed.
- `tests/test_gold_compare.py`: 24 passed, 0 failed.
- `check_gold_schema.py`: 8/8 samples, 0 problems.
- Stage3 source hashes: 8/8 matched.
- GoldCompare with the same corrected Gold: Gold QG 408; Pred QG 407; P=100.0%; R=99.8%; exact=86.8%; MISS=1; FP=0; MERGE=0; SPLIT=0.
- E3: 2 → 0. Remaining taxonomy: E2=1; E4=14; E4_SECONDARY=3.
- Original papers: P=100.0%, R=100.0%, exact=99.4%; X003 78/78 and X013 38/38.
- Explanations: E1 remains 0. No content was moved in the test or production corpus.

## Reproduction

Predictions for this commit were written outside the repository to `C:\xml-uat\stage3-e3-after\`. The GoldCompare result is `C:\xml-uat\gold-corrected-e3-after.json`; the Approved Gold set is unchanged from the supplemental correction at base SHA `33e0afa`.

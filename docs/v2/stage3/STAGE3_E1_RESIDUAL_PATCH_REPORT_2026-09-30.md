# Stage3 E1 Residual Patch Report — 2026-09-30

**Gate:** `PASS` for R5 recovery of the four audited residual E1 boundaries. Follow-up Gold coverage item recorded separately below.

## Root cause and scoped change

The four residual Gold starts sat inside existing answer/analysis zones, but the prompt-completeness gate only inspected the start node and required a long stem or an inline marker. It therefore rejected (a) a cited Chinese reading task with a compact “read and answer” lead-in, (b) a short calculation prompt whose formula is embedded in the node, and (c) short calculation prompts whose `(1)…(n)` body is distributed over sibling nodes.

The helper now accepts those compact forms only with structural evidence: citation plus a complete reading-task cue, a calculation cue plus formula metadata, or a calculation cue plus a multi-part sibling run. Numbered explanation steps remain suppressed. No sample IDs, subjects, year values, or exact source strings were added to production logic.

## Machine gate

- `tests/test_e1_question_recovery.py`: 11 passed, 0 failed (new cases cover X006 #39, X012 #6/#8/#9, and a negative short calculation step).
- `tests/test_stage2_baseline.py`: 26 passed, 0 failed.
- `tests/test_gold_compare.py`: 24 passed, 0 failed.
- `check_gold_schema.py`: 8/8 samples, 0 schema problems.
- Stage3 source hashes: 8/8 matched expected hashes.
- GoldCompare on the current corrected Gold and new predictions: Gold QG 407, Pred QG 409, P 99.3%, R 99.8% (406/407), Exact boundary 86.7%, MISS=1, FP=3, MERGE=0, SPLIT=0. One FP is the independently confirmed Gold coverage item below.
- Error taxonomy before -> after: E1 4 -> 0; E2 1 -> 1; E3 2 -> 3 (one newly surfaced candidate is independently confirmed below as a Gold omission, not a parser false positive); E4 14 -> 14; E4_SECONDARY 16 -> 3.
- Original-paper recall remains 100.0%; X003 remains 78/78 and X013 39 QGs; MERGE/SPLIT remain 0/0.

## New Gold coverage candidate for the next round

The expanded evidence exposed X012 node `b481`, order 557: a numbered “6．计算” prompt followed by an explicit answer and worked solution. This is a complete standalone question under R2/R5 and was not in the earlier 22-item audit because the pre-patch splitter had not proposed it. It is currently counted as one of the three E3/FP entries only because Approved Gold lacks that start. Gold was not edited in this implementation commit; record this as a separate high-confidence Gold correction round before using the updated metrics as the final baseline.

## Files and boundaries

This round changes only the R5 question-boundary helper and its regression coverage. It does not adjust Gold, E2, E3 logic, E4, or shared-material behavior. Stage3 predictions are stored outside the repository at `C:\xml-uat\stage3-e1-residual-after\`.

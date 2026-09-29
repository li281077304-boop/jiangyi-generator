# Stage2 frozen baseline

This runner reproduces the candidate rules formerly used by `_research/gen_gold_draft.py` to create Gold drafts. It does not tune, repair, or reinterpret those rules. `gold_compare.py` performs the formal comparison against the four approved Gold files.

## Run

From the repository root, with the original corpus tree available:

```powershell
python tools/stage2_baseline/run_baseline.py `
  --manifest tools/stage2_baseline/manifest.json `
  --corpus-root 'C:\Users\Administrator\Desktop\工作\讲义生成器' `
  --out 'C:\xml-uat\stage2-baseline-round1'
```

The `--out` directory receives per-sample predictions, full `gold_compare` Markdown/JSON reports, and a summary. The runner verifies each source DOCX SHA256 before parsing. Change only `--corpus-root` when the corpus is located elsewhere; do not edit the original corpus or Gold files.

## Frozen behavior

The copied rules are the original `BLOCK_ROLES`, `RE_TYPE_HEAD`, `RE_MATERIAL_HEAD`, TOC signature/cluster detection, numbered-run detection, candidate-to-next-candidate span construction, adjacent-role merge, uncovered-node `body` fallback, and simple sequential parent/material binding. The Stage2 implementation deliberately preserves known behaviors, including treating `题型N` as `question_group`; that mismatch is measured, not pre-corrected.

Metric definitions and failure analysis are in `docs/v2/stage2_baseline/round1_report.md`. The checked-in report omits document excerpts; full evidence stays under the external `--out` path.

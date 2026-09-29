# Stage2 question-boundary baseline

This runner adapts the prior candidate rules from `_research/gen_gold_draft.py` into a repeatable question-boundary pass. The current pass maps explicit exercise/type headings to `section`, detects independent numbered question starts, and suppresses numbering in knowledge and answer contexts. It deliberately does not infer `shared_material` bindings or add answer/analysis recognition. It does not modify the four approved Gold files. `gold_compare.py` performs the formal comparison.

## Run

From the repository root, with the original corpus tree available:

```powershell
python tools/stage2_baseline/run_baseline.py `
  --manifest tools/stage2_baseline/manifest.json `
  --corpus-root 'C:\Users\Administrator\Desktop\工作\讲义生成器' `
  --out 'C:\xml-uat\stage2-boundary-final'
```

The `--out` directory receives per-sample predictions, full `gold_compare` Markdown/JSON reports, and a summary. The runner verifies each source DOCX SHA256 before parsing. Change only `--corpus-root` when the corpus is located elsewhere; do not edit the original corpus or Gold files.

## Scope and repeatability

The report records predictions and `gold_compare` results for the four approved samples. Every question boundary is based on general text cues, numbering context, and explicit heading families; no sample IDs or sample-specific text are used by the recognition rules. The same source SHA256 values, Gold files, and code produce the same prediction units and comparison statistics.

The current checked-in report is `docs/v2/stage2_baseline/round2_report.md`. It omits long document excerpts; full evidence stays under the external `--out` path. `round1_report.md` is retained as the historical pre-change baseline.

# Stage3 E2 Local Practice Dispatch — 2026-09-30

**Gate: PASS.** The patch resolves the only Stage3 E2 miss while preserving every protected boundary and section metric.

## E2 rule implemented

- Dispatch is evaluated within each detected knowledge module. Count formal practice QGs after the module's practice heading and before the next knowledge module.
- Keep example 1 in knowledge. When practice QGs are below two, consider complete numbered extra examples in source order; incomplete examples do not dispatch.
- A dispatchable example needs prompt evidence and a following answer/analysis boundary. The local `随学随练` heading only scopes the E2 recovery; it does not enable general sequential-number QG detection.
- The `随学随练` parent-question recovery requires a question cue, at least two numbered subquestions, and a following answer/analysis boundary. The heading and numbering alone never create a QG.
- Stage3 has one approved E2 miss: X025 `b14–b18`, a complete `1．` parent with `(1)(2)(3)` under `随学随练`, followed by its answer/analysis. No approved extra-example dispatch case occurs in this eight-sample gate; the 0/1/2+ scheduler cases are covered with focused fixtures.

## Full Stage3 regression

Baseline was `b94b0366f451513a233c19ca23149fd9e74be892`; comparison uses the same eight approved Gold samples and staged source files.

| Metric | b94 baseline | E2 patch | Result |
|---|---:|---:|---|
| QG Gold / predicted | 408 / 407 | 408 / 408 | E2 resolved |
| Original-paper recall | 100.0% | 100.0% | preserved |
| E1 / E2 / E3 / E4 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | pass |
| FP / MERGE / SPLIT | 0 / 0 / 0 | 0 / 0 / 0 | pass |
| Section precision / recall / exact | 100.0% / 100.0% / 100.0% | 100.0% / 100.0% / 100.0% | unchanged |
| Subquestions inside parent | 99.1% (325/328) | 100.0% (328/328) | pass |
| Source hashes | — | 8/8 matched | pass |

GoldCompare reports QG precision/recall 100.0%/100.0%, exact boundary 87.7% (358/408), MISS 0, FP 0, MERGE 0, SPLIT 0. Original-paper exact boundary is 100.0%.

## Focused machine gate

- `tests/test_stage2_baseline.py`: 35 passed, 0 failed. Includes local module counts 0, 1, and 2; example 1 protection; example 2 then 3 ordering; module isolation; formal example-labeled groups counted after the practice heading; incomplete-structure rejection; and the X025-style practice case.
- `tests/test_e1_question_recovery.py`: 13 passed, 0 failed.
- `tests/test_gold_compare.py`: 24 passed, 0 failed.
- Full Stage3 prediction and GoldCompare outputs: `C:\xml-uat\stage3-e2-after-round6\` (`goldcompare.md`, `goldcompare.json`, and eight per-sample `prediction.json` files).

Reproduction:

```powershell
& 'C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器flash版\res\python\python.exe' tests/test_stage2_baseline.py
& 'C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器flash版\res\python\python.exe' tests/test_e1_question_recovery.py
& 'C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器flash版\res\python\python.exe' tests/test_gold_compare.py
& 'C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器flash版\res\python\python.exe' tools/stage3_goldcompare/rerun_predictions.py --out C:/xml-uat/stage3-e2-after-round6
& 'C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器flash版\res\python\python.exe' tools/stage3_goldcompare/run_approved_gold_compare.py --predictions-dir C:/xml-uat/stage3-e2-after-round6 --out C:/xml-uat/stage3-e2-after-round6/goldcompare.md --json C:/xml-uat/stage3-e2-after-round6/goldcompare.json
```

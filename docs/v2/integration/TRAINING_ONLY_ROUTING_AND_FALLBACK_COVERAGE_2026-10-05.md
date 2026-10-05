# Training-only deterministic routing and XML fallback coverage

**Branch:** `feature/v1.2-c4-release-engineering`  
**Base:** `d89b2abeb19f5394b2257c3d515d0784f031948a`  
**Evidence date:** 2026-10-05

## Status

The training-only route and persisted route evidence are implemented. The current real paired physics source generated teacher and student DOCX through the XML renderer, passed `PRODUCT_INTEGRITY_GATE` and package validation, and completed WPS open / SaveAs / close / reopen / PDF export. Six template modules remained present; modules 1, 2 and 5 were left blank, and questions were routed into modules 3, 4 and 6.

The 27-source scan is an observed route/capability audit. It did not invoke V0.9 fallback. Four sources were rejected before renderer entry; two that entered the renderer were classified as whole-job fallback candidates after XML rendering failed. These counts must not be read as a production probability or as proof that fallback generation itself passed.

## Before

The prior `NO_KNOWLEDGE_POINT` path treated the absence of knowledge blocks as a reason not to populate the explanatory and final practice slots. The available regression fixture showed that all source blocks were directed to the immediate-training slot while the knowledge and final slots were empty. Paired teacher and student files also had different A-Line question-group counts (29 versus 32 for this real pair), so raw QG ordinal was not a stable shared coordinate for routing.

Large layout tables remain physical atomic blocks in the current renderer. If a requested route boundary crosses one, the plan fails closed as `TABLE_SLOT_CONFLICT`; the implementation does not split or rewrite the table.

## Root cause

The previous router had no deterministic training-only strategy keyed to stable visible question starts. It could not distribute a no-knowledge-point source among slots 3, 4 and 6 while keeping teacher and student plans aligned when answer removal changed QG segmentation. Treating the complete top-level table as one physical block is a separate, intentional safety boundary and still rejects a cross-slot table boundary.

## What changed

- Training-only classification now routes reliable question starts without generating knowledge text or using AI.
- Generic question headings act as training groups; groups with multiple questions use a vertical route: first question to knowledge/explanatory slot (3), second to immediate slot (4), remaining questions to final slot (6). Singleton-heavy sets use deterministic `GROUPED_DEGRADED` balancing; unheaded questions use `SEQUENTIAL_DEGRADED` in source order. Unresolvable question structure remains fail-closed.
- Visible question starts are used as the shared teacher/student route signature where their group segmentation differs. If paired signatures cannot be established or disagree, the paired job fails closed.
- Physical source blocks, question groups, and shared-material bindings remain subject to conflict checks. A top-level table is never split by this router.
- Six template modules remain in the template. The composer keeps slot contents in source order and keeps the 1v1 `六、巩固练习` and class `六、出门测试` labels distinct.
- Job records persist `training_split_strategy`, question-to-slot routes, student preparation route, renderer route, fallback phase/reason/detail code, and whether XML rendering was attempted. Student preparation and whole-job renderer fallback remain separate facts.

## Real training-source example

The real paired inputs were uploaded directly:

- Teacher: `分子动理论训练 教师版.docx`, SHA-256 `56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`.
- Student: `分子动理论训练 学生版.docx`, SHA-256 `fb08ccae04b5140607a67d3e80526efa7d9a96f787c9c558b1c9b6bd3ab26e2a`.

The production job recorded `GROUPED_VERTICAL` and 34 visible question routes. Teacher and student A-Line segmentation had 29 and 32 QGs respectively, while both routed the same visible question starts:

| Template slot | Questions | Count |
|---|---|---:|
| 3 — knowledge / explanatory | 1, 5, 10, 15, 18, 22, 26, 31 | 8 |
| 4 — immediate training | 2, 6, 11, 16, 19, 23, 27, 32 | 8 |
| 6 — final practice | 3, 4, 7–9, 12–14, 17, 20–21, 24–25, 28–30, 33–34 | 18 |

Questions 1–34 each had one persisted destination. The route signature matched across teacher and student despite different QG counts. The route was not a claim that all 34 questions independently form 34 A-Line QGs.

## XML versus V0.9 on the real production job

Job `39c712dc65e4421cb00f0e62de3a2abb` finished `done` with:

```text
student_preparation_route = BYPASS
renderer_route = XML
training_split_strategy = GROUPED_VERTICAL
fallback_phase = NONE
xml_renderer_attempted = true
COM/WPS generation path = not entered
```

`BYPASS` is correct because teacher and student files were both supplied. This job did not use Studentizer or V0.9. Both final DOCX passed `PRODUCT_INTEGRITY_GATE` and package validation with no errors or warnings. The source inputs had no template-title cycle or long repeated sequence. The output character expansion ratios were 1.0798 (teacher) and 1.1646 (student), with one expected template title/cycle in each generated template document. The final outputs were opened, saved as new DOCX, reopened, and exported to nonempty PDFs by WPS. Visual checks confirmed cover, module order and images. The embedded source TOC still contains `错误！未定义书签`; this source defect was not changed by this task.

Raw job, staged/final gate evidence, WPS documents and PDFs are under `C:\xml-uat\training-only-production-final-20261005`. The job record is `runtime\39c712dc65e4421cb00f0e62de3a2abb\job.json` beneath that folder.

## Observed clean source corpus audit

The scan used the existing clean Product Source Corpus (`C:\xml-uat\stage3-expansion\baseline_inputs.json`). All 27 source hashes matched the corpus manifest.

| Measure | Count |
|---|---:|
| `TOTAL_SUBMITTED` | 27 |
| `RENDERER_ENTERED` | 23 |
| `XML_SUCCESS` | 21 |
| `PRE_RENDER_REJECTED` | 4 |
| `V09_WHOLE_JOB_FALLBACK` route candidates | 2 |
| `OBSERVED_CORPUS` XML success (`21 / 23`) | 91.3% |
| `OBSERVED_CORPUS` whole-job fallback (`2 / 23`) | 8.7% |

These are observed corpus rates only. Pre-render rejects are excluded from both renderer rates. The audit is read-only route/render coverage and did not execute any V0.9 whole-job generation or COM.

Top observed reasons, sorted by count:

1. `TABLE_SLOT_CONFLICT` — 3 pre-render rejects: X005, X006, X011.
2. `XML_RENDER_FAILED` — 2 renderer-entered fallback candidates: X026 and X027, both `ProjectionError` because the selected bookmark ID was missing or ambiguous (IDs 26 and 18 respectively).
3. `OBJECTIVES_SOURCE_UNAVAILABLE` — 1 pre-render reject: X022.

X012 (mathematics; 793 top-level blocks, including 9 tables) rendered successfully in the corpus audit. Current training-only sources X003, X004, X007–X010, X021 and X023 were also XML successes. A table conflict remains a fail-closed limitation; no claim is made that the cell-level table boundary problem was generally solved.

Raw audit: `C:\xml-uat\training-only-corpus-audit-20261005-3b4424ff\audit.json`.

## Regression and gates

- Fresh focused tests after the latest template regression test: **40 passed** (`test_slot_router.py` and `test_c0_job_service.py`). Coverage includes grouped vertical splits, two-question groups, singleton degraded balance, unheaded sequential routing, teacher/student signature agreement and mismatch refusal, class-specific final heading, and persisted route/fallback evidence.
- Existing Stage3 evidence for this candidate: QG 408/408, sections 369/369, subquestions 328/328, with zero MISS/FP/MERGE/SPLIT.
- Existing Stage2 and GoldCompare focused result: 64 passed. A separate Stage2 runner still reports the known S01/S11 failures; this task did not change A-Line or claim to repair those observations.
- The complete repository test suite, an actual V0.9 fallback execution, and general cell-level routing inside a cross-slot table were not performed in this round.

## Limits and next

Keep table/shared-material conflicts fail-closed. If future work adds cell-level table routing, it must prove table structure, relationships/resources, question-group atomicity, shared-material ownership and original order; this report is not that proof. The corpus scan's two V0.9 classifications are fallback candidates only until an explicitly authorized fallback UAT runs them through the whole-job V0.9 runtime and Product Integrity Gate.

Current source changes and this report are to be committed and pushed on `feature/v1.2-c4-release-engineering`; no C4 release, EXE, tag, or A-Line change is part of this work.

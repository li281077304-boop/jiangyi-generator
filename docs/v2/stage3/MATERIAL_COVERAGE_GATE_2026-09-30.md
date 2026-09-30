# Material Coverage Gate — 2026-09-30

**Scope:** Validate `shared_material` recognition and its binding to one or multiple question groups with three small, explicit cases. No QG Splitter, Renderer, COM, or UI changes were made. The Stage3 Gold set was not expanded.

**Governance reviewed:**

- `docs/decisions/2026-09-29-v1.1-stop-v1.2-roadmap.md` — V1.2 A-line scope is the Splitter; Renderer/COM/UI remain outside this gate.
- `docs/decisions/2026-09-30-splitter-business-rules.md` — R6 permits one material to bind multiple QGs; R7 merges continuous `材料1/材料2` unless there is explicit evidence they serve different groups.

These governance documents were read from the project working copy at `C:\Users\Administrator\Desktop\工作\jiangyi-generator-github`; the audit checkout at this report's base does not contain them.

## Cases and evidence

1. **One shared passage, two independent QGs.** A short explicit fixture contains one `【材料】` paragraph followed by two separate numbered questions and answers. Prediction contains exactly one `shared_material` (`b1–b1`) and two QGs (`b2–b3`, `b5–b6`); both QGs bind to the same material (`u002`). GoldCompare against the six expected units (section, material, two QGs, two answers) returned **zero issues**.
2. **Inline `材料1/材料2` inside a parent QG.** Existing focused fixture `test_inline_shared_material_stays_distinct_while_following_subquestions_return_to_parent` confirms the two material nodes form one separate material span (`b1–b2`), while the parent group retains the prompt and subquestions (`b0–b4`) and binds to that material.
3. **Two cited materials with separate QGs.** Existing focused fixture `test_cited_reading_materials_bind_only_to_their_question_groups` confirms two materials and two QGs, each QG bound only to its corresponding material; the first QG ends before the second material begins. Its GoldCompare diagnostic has no `UNBOUND`, `GROUP_SPLIT`, or `DUPLICATION` issue.

## Machine gate

- `tests/test_stage2_baseline.py`: **39 passed, 0 failed**.
- `tests/test_gold_compare.py`: **24 passed, 0 failed**.
- The explicit one-material/two-QG fixture: **PASS**, both QGs share one binding target and GoldCompare reports zero issues.
- No approved Stage3 Gold sample contains a top-level shared-material case, so this gate uses the three explicit/focused cases above and does not add Gold samples.

## Independent Chief review

- `chief_model`: **Codex GPT-6 Sol** (CODEX ONLY; explicitly invoked for this review).
- `chief_verdict`: **PASS**.
- The Chief independently ran the three focused material fixtures and the one-material/two-QG case. The in-memory case produced exactly one material, two QGs both bound to it, and zero GoldCompare issues. The other fixtures confirm inline material grouping and separate cited-material bindings.
- The Stage3 approved Gold set remains unchanged. No QG Splitter, Renderer, COM, or UI code was changed.

**Gate result: PASS.**

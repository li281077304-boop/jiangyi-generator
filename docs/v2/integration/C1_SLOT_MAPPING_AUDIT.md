# C1 A-Line to Class Template Slot Mapping Audit

Date: 2026-10-01  
Branch: `feature/v1.2-c1-uat-fixes`  
Base checkpoint: `v1.2-c0-end-to-end-2026-09-30` (`7bb7f303d36bc14b6b68cb0d2629616d4a30cf2c`)

## Gate result

`HUMAN_REQUIRED`

The current A-Line semantic output does not uniquely determine the requested three destinations for every unit. This audit stops before implementing slot routing. It does not modify Splitter rules or infer a new teaching policy.

## Existing A-Line information

`semantic_facade.analyze_source()` returns ordered units with `id`, `role`, source `spans`, and, when present, `parent`, `bind_to`, and evidence text. These fields describe structural classification and local relationships. They do not contain a destination slot.

The current Stage2 implementation reinforces this limitation:

- `BLOCK_ROLES` recognizes “即时训练”, “巩固练习”, “出门测试”, “当堂检测” and related headings as the same `section` role.
- `EXERCISE_LABELS` combines immediate-training and later-test labels in one list; detection emits the same `section` role and `训练栏目标题` evidence for them.
- `question_group` is attached to the nearest preceding section through `parent`; that relation does not distinguish the three requested slots.
- `answer` and `analysis` are attached to the current/last section by `parent`, not to a specific question group. No unique question ownership is emitted for repeated question numbers or answer-key layouts.
- The predictor serializes evidence under `note`, but C0's `template_block_plan.py` reads `unit.get("evidence")`; planned-unit evidence is therefore `None`. The route planner cannot use the existing classifier evidence without a separately reviewed contract change.
- `question_group.bind_to` identifies a related `shared_material` unit (and a material may support multiple question groups), but does not decide which slot the connected material/question-group component should occupy if its groups would otherwise be routed differently.
- generic `body` units can remain unparented, so their destination cannot be recovered from role and parent alone.
- Unit spans can overlap (for example, inline material contained within a question-group span). Copying units independently can duplicate physical source blocks; the existing C0 plan instead takes an ordered union of top-level blocks. A three-slot plan must assign each physical block once and reject a connected material/QG or atomic-table component if its members request conflicting slots.

## Real-source evidence

The audit used the exact source snapshots saved by C0, without changing them:

| Case | SHA-256 | A-Line inventory | Mapping evidence |
|---|---|---|---|
| X021 class chemistry | `e10818f40e99da4234051b1beeac852f4e8090475cdb96283fbf1bcb5b44a6f4` | 333 top-level blocks; 103 units: 29 `section`, 30 `body`, 44 `question_group` | The 44 question groups are parented to generic `题型01`–`题型14` sections. For example, `u017` is `题型01 实验室安全及处理`, and `u022`–`u024` are its three variant question groups; no unit designates immediate training versus exit test. `u018`–`u021` are unparented `body` spans covering instructional/table content. No unit is classified as knowledge, answer, or analysis. |
| X012 1v1 mathematics | `c9b31fe98b0ede8b0cefc5c3a11d8deab62c85c8a1181a54db25c7ca368b57a1` | 793 top-level blocks; 243 units: 34 `section`, 9 `body`, 56 `question_group`, 78 `answer`, 66 `analysis` | Knowledge headings, `【即学即练】`, and `题型` sections are present, but answer/analysis units point to section parents rather than question groups. In the `知识点02 倒数` area, units `u017`–`u019` are classified as `answer` although their text is teaching content (“倒数的概念/性质/求倒数”). Role-only slot routing would misplace them. |

The X021 work snapshot is `C:\xml-uat\c0-http-class-uAT-20261001\86d185f098ec445e85fb870e4e5a50fb\work\X021.docx`. The X012 work snapshot is `C:\xml-uat\c0-http-math-1v1-20261001\3a147f342e2f4ec2a6353a2afbe11a5a\work\X012.docx`.

## Template and renderer boundary

The frozen class template does contain the three requested headings: `知识精讲&例题讲解`, `即时训练`, and `六、出门测试`. They are in the same merged content cell of the main table, separated by divider paragraphs; they must not be treated as three copies of the same merged-cell insertion point. The C0 `template_block_plan.py` nevertheless deliberately assigns every physical source block to `main_content`, and the XML renderer receives one ordered block stream. Thus these headings are not yet wired to three independently routed semantic streams.

The template anchors are discoverable, but the current C0 plan does not represent per-slot streams. The critical unresolved contract is semantic unit → slot; the renderer integration must also ensure each heading maps to exactly one insertion point within the merged content cell.

## Required decision before implementation

Please define or approve the routing policy for at least these cases:

1. Which explicit section labels are authoritative for “即时训练” and which are authoritative for “六、出门测试”? Existing Stage2 business rules group both label families together.
2. Where should a `question_group` under a generic `题型`/`专题` section go when the source has no explicit immediate-training or test heading?
3. How should unparented `body` content be placed, and should an ambiguous unit fail the whole job for manual review?
4. What is the exact ownership policy for `answer`/`analysis` and for a `shared_material` bound to question groups that would land in different slots?
5. Does “不得破坏源文档顺序” mean preserve global order across all units, or preserve order within each destination after the intentional three-slot grouping?
6. Should a connected shared-material/QG component or table spanning units assigned to different destinations fail closed, or is there an approved single-slot precedence?

Until these decisions exist in the Business Rules, implementation would require inventing teaching rules and could duplicate, omit, reorder, or misplace source content. The safe result is `HUMAN_REQUIRED`.

## Scope preserved

This was a read-only source/template audit. No Splitter, StructDoc, Gold, Stage2/Stage3 metrics, B-Line renderer, or V0.9 runtime files were changed. No three-slot renderer, input-version classifier, or result-directory change was implemented in this audit round.

# V1.2 C1 Slot Routing Business Rules

Status: approved by user and independently reviewed by Codex GPT-6.1 Sol (PASS)
Branch: `feature/v1.2-c1-uat-fixes`  
Rules source: user-approved C1 decision supplied 2026-10-01

## 1. Responsibilities

- A-Line identifies what content is: semantic roles, spans, and structural relationships.
- The C1 Slot Router decides which teaching slot receives that content.
- Slot routing must not change the frozen A-Line Splitter rules.
- A routing ambiguity that could duplicate, omit, split, or misplace content fails closed through the existing V0.9 whole-job fallback with a reason code.

## 2. Template slots

The slot names are template-specific and must not be mixed:

| Order | 1v1 template | Class template |
|---:|---|---|
| 1 | `知识精讲` | `知识精讲&例题讲解` |
| 2 | `即时训练` | `即时训练` |
| 3 | `六、巩固练习` | `六、出门测试` |

## 3. Explicit source headings take priority

When the source has a clear section heading, that heading is the highest-priority routing signal. A recognized third-slot heading means the source already defines the ending practice/test region; do not additionally split or supplement question groups into that slot.

### Knowledge headings → slot 1

Examples include knowledge points, exam points, concepts, definitions, methods, techniques, examples, and explanatory type sections (`题型讲解`).

### Immediate-training headings → slot 2

Examples include `即时训练`, `即学即练`, `对点训练`, `随堂练习`, and `课堂练习`.

### Third-slot headings → slot 3

For 1v1: `巩固练习`, `课后练习`, `综合练习`, `达标检测`.  
For class: `出门测试`, `当堂检测`, `达标检测`, `课后测试`.

The destination slot name still comes from the selected template; a class heading must not cause the 1v1 third-slot name to be used, or vice versa.

## 4. Generic type/topic/exam-point sections

`题型XX`, `专题XX`, or `考点XX` alone does not mean immediate training or third-slot test.

- The heading, its explanation, method, formula, table, and the first complete example that teaches the type/topic belong in slot 1.
- Subsequent complete practice blocks within that section are training candidates.
- A practice block remains indivisible and keeps its original order and numbering.

## 5. Atomic complete practice blocks

A complete practice block is a naturally delimited exercise unit with its own natural question-number start, ordinarily `1`, and its original continuous numbering. It is not synonymous with one A-Line `question_group`.

Natural boundaries may be established, in priority order, by:

1. An explicit section heading;
2. A question-number sequence restarting at `1`;
3. A new question type, module, or topic;
4. Other structural evidence that the exercise unit is independently complete.

Keep each block whole. For example, if one block is `1–10` and the following block is `1–5`, the whole `1–10` block may go to slot 2 and the whole `1–5` block to slot 3. It is forbidden to cut the `1–10` block into `1–5` and `6–10` across slots. The third slot must never begin midway through a block (such as at question 3, 5, or 6).

## 6. Selecting slot 3 without an explicit third-slot heading

Do not split a block to balance question counts or hit a proportion. The prior “last 30% of question groups” rule is retired.

Prefer the last naturally complete practice block or contiguous last blocks as the third-slot payload. A small third slot is acceptable; structural integrity takes priority over balanced quantity. If the source has only one complete block and no safe whole-block split, preserve it whole and leave slot 3 empty or fail closed. Never split midway merely to make slot 3 non-empty.

## 7. Body content

Do not route `body` by role alone. Inherit the destination from its owning section, nearest explicit section, or enclosing complete teaching block. Ordinary introductory body text before any explicit owner defaults to slot 1. Explanations, formulas, tables, and method summaries after a generic type heading and before its first example stay with that type in slot 1.

## 8. Answers and analysis

Do not route solely by `role == answer` or `role == analysis`.

- An answer or analysis reliably owned by a question follows that question's complete practice block and destination.
- Content in a knowledge/explanation section remains in slot 1 even if A-Line assigned an answer/analysis role.
- If ownership cannot be established reliably, do not move that answer/analysis independently across slots. If the containing complete unit cannot be routed safely, fail closed to the existing V0.9 fallback.

## 9. Shared material and atomic tables

A shared material and its bound question groups form a connected component. Treat a table as an atomic physical source block.

If one connected material component or indivisible table would have to span multiple destination slots, do not duplicate it or split it. Fail closed to the existing V0.9 whole-job fallback and record an explicit reason.

## 10. Ordering and no-loss requirements

Three-slot grouping is intentional instructional organization; global order across all slots need not match the source. Within each slot, preserve source order. Within every complete practice block, preserve block order and continuous numbering absolutely. Do not reorder questions, interleave separate practice blocks, or split a question group across slots.

Every source physical block must be assigned exactly once or cause a fail-closed result. Shared spans must not be copied twice.

## 11. Required examples and gates

The Slot Router must use the correct target names for both template types and support explicit headings, generic type sections, body inheritance, and complete-block routing.

Special regression fixture: two adjacent natural blocks numbered `1–10` and `1–5`. Expected: the full first block may remain in slot 2 and the full second block goes to slot 3. The output must not contain a third-slot fragment beginning at `6` or any other mid-block number.

Required checks also cover shared-material uniqueness, table atomicity, answer/analysis ownership, body inheritance, slot-internal order, and continuous numbering.

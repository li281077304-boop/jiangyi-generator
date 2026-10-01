# C3 Round 2 — Standalone Reviewed Studentizer Gate

Worker: GPT-6.1 (`gpt-6.1-sol`, actual invocation).
Base: `36636ffbafbf891cff094c3b86558b774f84b00e`.
Round 1 capability audit received independent Codex GPT-6.1 Sol **PASS**.
Round 2 Chief review is **PENDING**; this is not a C3 completion claim.

## Implemented scope

New standalone module: `res/app/studentizer.py`. No production job, renderer,
slot router, input resolver or frozen V0.9 code imports or calls it.

`prepare_student(source_snapshot, semantic_snapshot, output_path, policy)`
returns explicit status/engine, source/output hashes, output path, mutations,
validation, reason code/detail, elapsed time and COM invocation count.

- Teacher mode requires `StudentizerSemantics` on the exact source SHA256.
- Each `AnswerBinding` has owner ID/kind/start/end, an exact direct-body answer
  address, full structural fingerprint, `reviewed_question_answer` relation and
  review ID. These are **trusted reviewed caller allowlists**, not automatically
  inferred A-Line roles. The module does not authenticate a reviewer or create
  ownership evidence. Production currently has no reviewed-plan supplier and
  remains on the frozen student conversion path.
- A-Line `SemanticSnapshot`, section-only parents, role-only/unreviewed bindings,
  stale source digest or address fingerprint cannot authorize deletion.
- Initial policy `reviewed-plain-answer-v1` supports **only one terminal,
  dedicated plain-text answer paragraph per approved question binding**. A
  question-shaped owner start and an answer marker are corroboration, not the
  source of removal authority. The owner interval must contain no intervening
  numbered prompt or nonparagraph block. No partial text/run clearing, broad
  marker-to-section deletion, color stripping or blank insertion is implemented.
- Explicit protected physical addresses represent shared material, knowledge
  and prompts; their overlap with removals is rejected. Table/cell ownership,
  mixed/unknown answer XML, section breaks, formula/object/textbox answers and
  uncertain boundaries fail closed.
- Bookmarks/hyperlinks, fields, basic revisions/content controls/comments/
  footnote/endnote references in the main body conservatively reject teacher
  preparation. This is a narrow supported scope, not complete DOCX capability.
- Supplied student mode requires both the preserved C1 input version
  (`STUDENT_ONLY` or `TEACHER_AND_STUDENT`) and explicit student source side.
  It bypasses ownership/removal and preserves the DOCX **byte for byte**.
  Teacher-side bytes in a paired policy do not silently bypass conversion.

Results are `XML_PREPARED`, `STUDENT_SOURCE_BYPASS` or
`STUDENTIZER_FALLBACK_REQUIRED`. The module **does not invoke** V0.9 fallback.
Unsupported results contain no usable partial output. Caller orchestration and
actual fallback behavior are deferred to a separately reviewed round.

## Preservation and failure behavior

Source bytes are read once and hashed. Operations use zero-based direct children
of the same `w:body`; fingerprints verify exact XML elements, never text-first
search or COM paragraph offsets. Repeated text cannot relocate a binding.

For approved removal, the retained body blocks must match their original full
structural fingerprints in the same order. Every ZIP member except
`word/document.xml` retains its original bytes and member order; there is no
resource cleanup. Thus preserved prompt diagrams/media/relationships remain
present. Serialization is followed by preservation checks and frozen package
validation. A fresh staged DOCX is published using an atomic, exclusive hard
link so existing output/source paths cannot be overwritten. Temporary staging
is cleaned on the owned path. Publication remains standalone runtime work,
not a user result-directory or job-state change.

Specific reasons include source identity mismatch, unproven answer ownership,
unsupported table/textbox/formula-object/field/bookmark/revision/mixed scope,
preservation failure, package validation failure and XML preparation failure.
They are recorded as distinct `STUDENTIZER_*` codes, never a silent success.

## Scoped machine evidence

**29 synthetic Studentizer tests** pass. They use minimal DOCX/OOXML packages and
explicit reviewed fixture annotations; they are not real source deletion Gold.

| Case | Evidence |
|---|---|
| Approved teacher source → derived student | Exactly the approved first answer paragraph disappears |
| Adjacent knowledge/next question/unreviewed second answer | Full XML structure and source order remain unchanged |
| Duplicate text/red knowledge | Both repeated paragraphs and red explanatory content remain intact |
| Prompt picture/resource relationship | Drawing remains; media, rels and all other untouched package member bytes match |
| Supplied student alone / paired student side | Exact original DOCX bytes preserved, no mutation |
| Wrong pair/source side | Refused explicitly rather than bypassing teacher bytes |
| Source/address fingerprint mismatch | Refused; no output and no source edit |
| Role-only, section parent, no review / frozen predictions | Cannot authorize removal |
| Shared-material protected overlap / duplicate deletion | Preservation failure, no output |
| Table/cell answer | Atomic table scope refused |
| Formula/object/textbox/field/bookmark/revision/section break | Explicit unsupported scope and no partial file |
| Inline prompt before answer marker | Mixed paragraph refused |
| Existing output/source alias | Original bytes never overwritten |
| Broken media relationship | Package validation prevents publication |
| Missing source | Explicit failure result without output |

Focused combined gate: **153 passed in 36.74 s** (Studentizer 29 + existing
C2/C1/input/Stage2/workspace 124). Stage2 **39/39** is included.
Fresh Stage3 evidence: `C:\xml-uat\c3-round2-studentizer\stage3\`;
all eight source hashes match; QG **408/408**, sections **369/369**,
subquestions **328/328**, original recall **100%**, E1/E2/E3/E4 and
MISS/FP/MERGE/SPLIT **0**. Overall teacher/analysis exact QG boundary remains
**87.7%**. Frozen V0.9 manifest **10/10**. Python compile and diff checks pass.

## Explicit limits and next action

No real-corpus reviewed deletion plan was authored or accepted this round.
No real sample is declared XML-Studentizer-supported. No new WPS application UAT,
production performance result, real zero-COM claim or completed C3 gate is made.
Existing C1/C2 WPS/browser/performance evidence remains referenced in the
approved capability audit and unchanged. Renderer preservation of a derived
source still does not independently establish original-teacher deletion safety.

Known deferred capabilities include multiline/unmarked answers, inline partial
answers, answer equations/images/OLE, answer-bearing tables/textboxes, section
answer sets, styled/theme colors and blank insertion. They require reliable
reviewed ownership and additional preservation evidence, not role/color rules.

The scoped change is this independent module, its tests, report and Journal.
A-Line, C1 Business Rules, B-Line renderer core, V0.9 and C2 production behavior
are frozen. Commit and push precede independent **Codex GPT-6.1 Sol** review.
Stop before routing production jobs through Studentizer.

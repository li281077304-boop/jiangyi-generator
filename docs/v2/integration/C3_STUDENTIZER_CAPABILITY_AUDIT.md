# C3 Round 1 — Studentizer Capability Audit

Status: audit candidate; independent **Codex GPT-6.1 Sol** review pending.
Worker: **GPT-6.1 (`gpt-6.1-sol`, actual invocation)**. Audit only: no Studentizer
production implementation, source mutation or frozen behavior changes.

## Verified start and boundaries

- C2 branch local/remote: `f3fc31ab10f32673afc1398c98df124971b0cd13`.
- Annotated `v1.2-c2-batch-2026-10-01` object, local/remote:
  `887693acfc670150c4c37c943a821ec69f480af2`.
- Tag target, local/remote: `f3fc31ab10f32673afc1398c98df124971b0cd13`.
- Created/pushed `feature/v1.2-c3-studentizer-performance` from that tag.
- V0.9 baseline: `0922e08631226b95a77a6599bbc0ac3784e9134b`.
  All ten manifest assets exist and hash-match; no missing runtime app assets.

A-Line identifies semantic units; C1 routes complete teaching/practice units to
template slots; B-Line renders XML packages or invokes whole-job V0.9 fallback;
C2 groups inputs and runs isolated items serially. These boundaries are frozen.
Current `webapp/app.py` calls frozen `make_student` **before** semantic plans for
TEACHER_ONLY, saves a runtime derived input, validates it, then builds teacher
and student plans independently. Supplied TEACHER_AND_STUDENT and STUDENT_ONLY
skip student conversion. C2 delivery is now local DOCX/Open Folder only; ZIP is
an input format, not result delivery. This audit changes none of that behavior.

## 1. What V0.9 answer removal actually does

Authoritative files are `res/app/v09_fallback_runtime/handout.py`,
`_strip_answer_com.ps1`, `_add_blanks_com.ps1`, verified against the frozen
manifest, not V1.1 copies.

`make_student(source, output)` performs these operations in order:

1. `strip_red`: opens via python-docx and writes the output. It scans
   `Document.paragraphs`, **not table paragraphs**. Explicit RGB counts as red
   when R≥100, G≤70, B≤70; inherited/theme color is not resolved. The first pass
   sets qualifying `run.text = ""`; a second XML descendant-run pass clears
   descendant `w:t` when a red `w:color` is found under those top-level paragraphs.
   This can include nested content inside a top-level paragraph. The first
   assignment clears other run children too: its “preserve formulas/OLE” comment
   is not a proof that a mixed text/object run survives. Tables/headers/footers
   are outside the top-level paragraph iteration.
2. `_strip_answer_markers`: calls PowerShell on that derived output, in place.
   COM scans `Document.Paragraphs` and matches `【答案】`, `【详解】`, `【解析】`,
   `【解答】`, `参考答案/参考解析` followed by punctuation, or parenthesized
   答案/详解/解析. The match may occur anywhere in the paragraph.
3. For **every** marker paragraph it deletes from that paragraph through the
   paragraph before the next later Chinese numbered section heading or heading
   starting 题型/考点/知识点/专题/Part/Section/Lesson/Unit, or to document end.
   Overlapping ranges are combined and paragraphs deleted in reverse order.
   Ordinary next question numbers, subnumbers and choice letters are **not**
   deletion boundaries. Individual deletion exceptions are swallowed. A reverse
   pass compresses consecutive empty paragraphs (skipping paragraph 1).
4. `_add_blanks`: scans the remaining COM paragraph sequence. A paragraph
   starting 1–3 decimal digits plus `. / ． / 、`, or parenthesized digits, is a
   question header. Each candidate runs to the next such header or document end.
   `A–D` options at paragraph start classify it as choice; underscores or empty
   parentheses classify it as fill-in. Otherwise it inserts `3 * subCount`
   empty paragraphs at its computed end, working in reverse. Parenthesized
   subquestions also enter the global header list, so this heuristic is not a
   reliable semantic question/subquestion classifier. It does not gate on a
   teaching section or distinguish numbered knowledge from exercises.

Both COM scripts create Word.Application, open read-only, SaveAs format16, close,
Quit/release and their original PID cleanup. Python wrappers run each with the
frozen 300-second timeout and parse counters from stdout; they do not robustly
reject every nonzero return code. `make_student` returns red/deleted/question/
blank counts plus log. C1 adds nonempty/package validation, not deletion safety.

**Documentation discrepancy:** Python `_strip_answer_markers` says individual
answers delete only the marker paragraph and late concentrated answers delete
to end. The actual frozen PowerShell uses marker→next section for all markers.
The script behavior is authoritative; no correction to frozen code is proposed.
Also, red stripping may remove red marker text before the COM scan: Round 6
logs show NO_ANSWER_MARK on conversions despite source marker features. Thus a
source marker inventory is not the actual post-red COM deletion list.

## 2. Behaviors that can safely be XMLized

These are **conditional capability candidates**, not a Studentizer PASS:

| Operation | Required proof before XML support |
|---|---|
| Clear a dedicated answer text leaf/run | Exact source snapshot, structural node/run identity, independently reliable answer ownership; text-only edit retaining paragraph/run properties and all nontext children |
| Remove a whole answer-only paragraph | Entire physical paragraph is confirmed removable; no question/material/knowledge, section properties, table boundary, bookmark/field dependency or preserved object occupies it |
| Remove a dedicated answer section | Proven complete answer-only interval and next preserved structural boundary; no following exercise or knowledge paragraph included merely because COM would delete it |
| Insert answer space | Proven question/subquestion end and type, allowed plain paragraph location, template/section formatting and no table/cell/section boundary damage; conservative unsupported decision otherwise |
| No-op on confirmed student source | Keep C1 semantics: use supplied student directly without invoking any Studentizer |

Exact RGB inspection and structural XML edits are mechanically feasible. RGB
alone is not answer authorization. Theme/inherited color, equations with answers
inside OMML, OLE internals, pictures of answers, fields and table geometry need
separate capability decisions; this round proves none of them removable.
Do not port COM paragraph ordinals, its marker→section deletion rule or its
number-only blank classifier as XML truth. XML should use structural addresses
on one byte snapshot and reject uncertainty without offsets/text search.

## 3. Behaviors needing A-Line semantic binding

- Distinguish red knowledge/emphasis/question text from red answer content.
- Establish the owner and complete extent of a question's answer/analysis;
  preserve the next question, shared material and explanatory first example.
- Disambiguate answer marker words quoted in a prompt or teaching explanation.
- Preserve body/formula/table explanations and section ownership under C1.
- Locate genuine full question/subquestion ends for answer space; numbered
  instructional steps and option paragraphs are not automatic question headers.

Existing `assign_relations` gives QG/answer/analysis/knowledge `parent` equal to
the latest **section**, not an owning QG. QG `bind_to` concerns shared material.
It does not supply a general answer→question ownership contract. Stage3 treats
answer/analysis linkage as diagnostic, and its actual teacher QG exact boundary
rate is 87.7% overall. A role alone cannot authorize deletion: C1 explicitly
protects knowledge content misidentified as answer/analysis. Frozen semantics
may be consumed as evidence; do not add or alter A-Line rules to make C3 pass.
When existing evidence cannot prove ownership, return a reason and use the
approved fallback rather than inventing binding or deleting by nearest text.

## 4. Real samples likely requiring fallback and coverage

Fresh read-only `word/document.xml` inventory inspected **27** available sources
from `C:\xml-uat\stage3-expansion\baseline_inputs.json`; **27/27 source hashes**
match. External diagnostic: `C:\xml-uat\c3-round1-capability\features.json`
and `inventory_features.py`. Counts are main-body XML feature occurrences,
not COM indices, effective Word colors, confirmed answers or Studentizer tests.
Main-story paragraph collection excludes textbox paragraph nodes; feature
descendants include textboxes hosted by those body paragraphs. Table cells are
included. Drawing/OLE counts are XML elements, not unique displayed objects.

| Sample | Tables | OMML | Drawing | OLE | Textbox | Explicit-red runs | Red runs in tables | Red runs hosting objects | Marker paragraphs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| X001 physics teacher | 17 | 0 | 101 | 332 | 0 | 1777 | 0 | 243 | 127 |
| X004 physics teacher | 6 | 0 | 73 | 497 | 0 | 2055 | 10 | 359 | 146 |
| X006 physics teacher | 4 | 127 | 81 | 0 | 0 | 2122 | 0 | 19 | 108 |
| X012 mathematics teacher | 9 | 786 | 18 | 9 | 0 | 792 | 0 | 1 | 136 |
| X013 mathematics student | 1 | 191 | 32 | 23 | 0 | 12 | 0 | 5 | 0 |
| X018 chemistry teacher | 8 | 0 | 80 | 6 | 16 | 256 | 21 | 6 | 74 |
| X020 chemistry teacher | 5 | 0 | 38 | 9 | 16 | 346 | 15 | 3 | 76 |
| X021 chemistry student | 12 | 0 | 220 | 0 | 0 | 183 | 84 | 0 | 0 |
| X023 chemistry teacher | 12 | 0 | 220 | 1 | 0 | 434 | 83 | 1 | 112 |
| X025 chemistry teacher | 6 | 0 | 86 | 65 | 28 | 831 | 82 | 49 | 100 |

All-source inventory also covers X002–X003, X005, X007–X011, X014–X017,
X019, X022, X024, X026–X027. Textboxes occur in X017–X020 and X024–X027.
Raw explicit red appears even in genuine student originals such as X013/X021:
it cannot be assumed to be unwanted answers.

Conservative initial fallback candidates (feature risk, not final decisions):

- X001/X004: red runs physically contain object children; direct run clearing
  can affect diagrams/OLE. Require identity-preserving edits and ownership proof.
- X006/X012: answer regions contain formula-heavy content; w:t-only stripping
  cannot certify all answer equations removed. X012 already had a real C1
  TABLE_SLOT_CONFLICT whole-job fallback, independently of Studentizer support.
- X018/X020/X025/X027: table-red/textbox content or embedded objects have a
  different scope from V0.9 top-level red iteration; broad descendant removal
  would extend behavior without evidence. Initial unsupported or tightly scoped
  preservation is safer than silently deleting them.
- X009: C2 already observed UNSUPPORTED_BOOKMARK_SCOPE in rendering. It is a
  supplied student and skips Studentizer; do not call it a Studentizer failure.
- Any unbound marker→section interval that includes a following question or
  knowledge unit must be refused; repeated text does not resolve the owner.

**Explicit gaps:** the inventory found zero marker paragraphs inside tables,
zero marker paragraphs with preceding inline text, and zero occurrences of the
six inspected basic revision tags (`ins/del/moveFrom/moveTo/rPrChange/pPrChange`)
or footnote/endnote/comment-reference markers across these 27 bodies. This does
not prove every possible revision tag/package construct absent. Real coverage
for these cases is missing; add safe fixtures and seek real examples. Inherited
theme red, all answer-only image/OMML/OLE cases, fields, nested table deletion,
run-mixed question+answer, exact deletion ownership and answer-space parity are
not established by this inventory. It is not a new Gold corpus or accuracy claim.

## 5. Tests/evidence that can prove no over-deletion

Package validation and rendering derived student bytes correctly are insufficient:
Round 6 content audit compares renderer output to the **already derived** student
source. It cannot detect mistakes introduced by frozen conversion before that
point. Frozen V0.9 output is a compatibility reference, not sole deletion truth.

Before enabling an XML capability, require:

1. Human-reviewed small teacher/student examples establish allowed answer
   deletions and preserved question/knowledge/material content. Genuine pairs
   are useful references but editorial version differences prevent treating a
   full text diff as automatic deletion Gold.
2. Every mutation has exact source SHA, node/XML/run address, before/after
   fingerprint, owner evidence and reason. No text-first positioning, QG role
   blanket deletion or ordinal guessing. The mutation allowlist is auditable.
3. Compare **teacher source→derived student**, not just derived source→render:
   all non-authorized text, question numbers/options, formula markup, diagrams,
   OLE binaries, tables/cell order/merges, section properties and shared material
   survive in source order. Untouched package parts retain exact bytes; live
   relationships stay valid; any change outside the allowlist fails closed.
4. Small fixtures include numbered knowledge with red emphasis, mixed prompt/
   answer paragraph, marker before another question, wrong answer role in
   knowledge, duplicate text, table answers/material, textbox marker, red run
   with drawing/OLE/field, OMML answers, bookmarks straddling removal, revision/
   comment/footnote markers, no-marker document, genuine student bypass and
   repeated preparation. Verify preserved structures as well as removed text.
5. Prove selective fallback with explicit reasons and successful sibling
   preservation in mixed batches; pair/student paths still call no conversion.
6. Validate nonempty DOCX plus package/relationship integrity, then actual WPS
   open→SaveAs→close→reopen→PDF and selected teacher/student visual comparison.
   Check diagrams/equations/table layout, answer removal and blank spacing;
   WPS OMaths returning zero is not visual formula evidence. Record exact
   conversion invocations, elapsed time and sampled/exact process metrics.

No XML Studentizer output or no-over-deletion PASS is claimed in this audit.

## Proposed API / fail-closed contract (not implemented)

`prepare_student(source_snapshot, semantic_snapshot, output_path, policy)`
returns `status`, `engine`, `output_path`, `source_sha256`, `output_sha256`,
`mutation_report`, `validation`, `reason_code`, `reason_detail`, `elapsed_seconds`
and actual COM invocation metrics. Policy is versioned and conservative; it must
not silently reinterpret frozen Splitter roles as removal authority.

Status: `XML_PREPARED`, `FALLBACK_REQUIRED`, or `FAILED`. A supplied student
continues to bypass preparation at orchestration. On unsupported capability,
return no usable partial output; the future orchestration wrapper may call the
untouched V0.9 `make_student` on the **original teacher snapshot** into a fresh
runtime output. That preparation fallback remains distinct from the existing
renderer whole-job fallback; it is never a StructDoc→COM paragraph adapter.
Fallback output also requires validation and truthful metrics, and must not be
described as proof of semantic answer correctness merely because it generated.
Routing integration details await implementation review; no new process
lifecycle, retry, PID, timeout or Writer code is authorized by this proposal.

Proposed explicit reason codes (not existing production enums):

- `STUDENTIZER_SOURCE_IDENTITY_MISMATCH`
- `STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN`
- `STUDENTIZER_MIXED_CONTENT_UNSUPPORTED`
- `STUDENTIZER_TABLE_SCOPE_UNSUPPORTED`
- `STUDENTIZER_TEXTBOX_SCOPE_UNSUPPORTED`
- `STUDENTIZER_FORMULA_OBJECT_UNSUPPORTED`
- `STUDENTIZER_FIELD_SCOPE_UNSUPPORTED`
- `STUDENTIZER_BOOKMARK_SCOPE_UNSUPPORTED`
- `STUDENTIZER_REVISION_SCOPE_UNSUPPORTED`
- `STUDENTIZER_BLANK_INSERTION_UNPROVEN`
- `STUDENTIZER_PRESERVATION_CHECK_FAILED`
- `STUDENTIZER_PACKAGE_VALIDATION_FAILED`
- `STUDENTIZER_XML_PREPARATION_FAILED`

Source identity/preservation/package failures return FAILED or fallback intent
without publishing output; the orchestrator must not swallow them. Persist both
Studentizer engine/reason and renderer engine/reason separately.

### Source/output preservation approach

Read source once into immutable bytes, hash them and create frozen semantic
snapshot from those same bytes. Require semantic digest equality. Stage a new
derived source under internal job runtime, reject source/output aliases and
existing paths, and never edit user originals. For an XML implementation preserve
all untouched ZIP member bytes and package relationships; mutate document.xml
only under an approved allowlist initially. Do not rebuild with python-docx or
garbage-collect orphaned resources as an unrelated optimization. Verify semantic
preservation and package integrity before atomic publication to a fresh runtime
DOCX, then run existing C1 plans/renderer and validated local-result publication.
Discard failed staging safely within that job; do not delete successful siblings.

## Referenced completed integration evidence

- `C1_UAT_FIX_REPORT.md`: real six-output WPS round trips; X021 both templates,
  X012 fallback; approved C1 slot/role/table rules remain intact.
- `C2_BATCH_REAL_UAT.md`: real Cases A–F, 32 packages, 30 renderer content audits,
  11 WPS products and selected visual evidence. Teacher-only conversions cost
  24.015/17.068/17.349/14.841/13.899 seconds in Case A; 10 exact COM script calls
  and 20 sampled WPS starts. Paired XML class workload 13.975 s vs frozen V0.9
  76.801 s. These are previous measured workloads, not C3 performance results.
- `C2_LOCAL_DELIVERY_BROWSER_UAT.md`: actual Edge uploads/polling/partial success,
  eight local DOCX packages and two Explorer Open Folder interactions; removed
  download API/UI. Historical C1/C2 output-download observations are superseded.

Those existing external artifacts remain accessible; no UI/renderer/batch/WPS
implementation or new application UAT was done in this audit round.

## Round 1 machine gate

Fresh external evidence: `C:\xml-uat\c3-round1-capability\stage3\`.
Stage2 **39/39**. Stage3 all eight source hashes match, QG **408/408**, sections
**369/369**, subquestions **328/328**, original recall **100%**,
E1/E2/E3/E4/MISS/FP/MERGE/SPLIT **0**. Overall exact teacher/analysis QG boundary
rate remains **87.7%**. V0.9 manifest **10/10**. `git diff --check` passes;
the round diff is documentation/Journal only. No production implementation or
new tests added. Commit/push precedes independent Chief review; stop here until
Codex GPT-6.1 Sol returns PASS.

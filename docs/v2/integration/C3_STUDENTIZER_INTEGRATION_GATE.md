# C3 Round 3 — complete-scope Studentizer orchestration gate

Base: `dddcd8185f3de4f42345f577d3f4dad844772608`.
Worker: actual GPT-6.1 (`gpt-6.1-sol`). Chief: Codex GPT-6.1 Sol,
independent review pending. No C3 completion or real XML Studentizer support
claim is made by this report.

## Production authority and complete coverage

`studentizer_planner.py` wraps the Round 2 standalone module. A trusted server
configuration callable may supply `CompleteStudentEvidence`; there is no
upload/API/filename switch that grants removal authority. No real-source
evidence provider or reviewed Golden manifest is shipped.

Evidence must bind the exact source bytes, the canonical complete frozen
A-Line semantic-unit manifest, every direct `w:body` child fingerprint and
classification, all A-Line question-group IDs, exact reviewed answer ownership,
and an independently reviewed whole Golden document C14N digest. Every
classified answer must have a bound removal. Each color/marker candidate must
explicitly be reviewed for removal or preservation. A provider may not mutate
the frozen semantic manifest. The actual predicted QG start and end must agree
with the ownership interval; question identity cannot be a section parent.

Before creating any derivative, the complete projected in-memory document is
compared to that Golden digest. The standalone module then applies its existing
plain terminal answer rules and byte/structure/package preservation gate.
Initially any main-body table or textbox is unsupported. Other standalone
bookmark/field/revision/object/ownership restrictions remain in effect.

Human correctness of the independently reviewed Golden and classifications is
a **trusted caller boundary**, not authenticated by this module. A fabricated
Golden supplied by a trusted server operator cannot be distinguished from an
approved one. These checks prove identity, completeness of the supplied review
manifest and exact approved transformation; they do not create business review
authority from role, color or marker predictions.

## Routing and fallback

- `TEACHER_ONLY`: try complete-scope Studentizer; only `XML_PREPARED` enters
  ordinary C1 plans and B-Line XML generation.
- No evidence, incomplete coverage or unsupported construction fails closed
  per item. The precise `STUDENTIZER_*` reason is persisted separately in
  `student_preparation` and fallback detail. The existing frozen renderer reason
  enum carries `XML_RENDER_FAILED`; its core is unchanged.
- Any later renderer failure also sends the **original teacher** to untouched
  V0.9 whole-job flow, with `student_source_doc=None`. A partially or successfully
  prepared derivative is never supplied to teacher-only fallback.
- Supplied pair/student-only sources bypass the planner/provider completely;
  source bytes are used unchanged and do not call `make_student`.
- A process-local orchestration lock serializes V0.9 fallback. A forward-only
  temporary observer records actual entry into frozen `make_student`, calls the
  exact original callable and restores it in `finally`. Frozen files, COM
  provider and process lifecycle are untouched. The lock does not coordinate
  separate server processes; existing C2 uses one serial submission executor.

Child and batch/recovered metadata include preparation engine/status/reason,
source/output identities, coverage, Studentizer time, observed make_student
time and fallback total. Failed fallback intent remains persisted.

`wps_com_started` is a legacy **COM-capable make_student entry** indicator,
not an OS process probe. `wps_com_evidence=COM_CAPABLE_MAKE_STUDENT_ENTRY_ONLY`
states this explicitly. If the function fails before its PowerShell step, no
actual WPS process start can be inferred. No new real COM start counts are
claimed. XML-supported synthetic cases do not load the V0.9 engine at all.

## Machine evidence

Fresh external evidence: `C:\xml-uat\c3-round3-integration\`.

Final combined focused gate: **174 passed in 49.59s** (existing 124 checks,
29 standalone checks and 21 integration checks). Python compilation and Git
diff whitespace checks pass. Existing unrelated plan-summary tests use explicit
supplied pairs; fallback test substitutes now perform whole-job preparation,
so the new conservative teacher-only path cannot silently skip student output.

Synthetic integration tests exercise actual standalone derivative production
and validation using actual frozen A-Line QGs, with renderer/fallback substitutes
to avoid claiming real COM execution. Cases include complete Golden success;
missing body/QG/binding coverage; stale source/semantic identity; unreviewed
candidate; wrong Golden; section identity; provider mutation; table/textbox
refusal; red knowledge preservation; supplied-source bypass; mixed batch and
restart metadata; later renderer failure reset; callable restoration after
success/error; and concurrent fallback serialization.

Fresh protected Stage3: QG **408/408**, sections **369/369**, subquestions
**328/328**, original-document Recall **100%**, E1–E4/MISS/FP/MERGE/SPLIT **0**.
Overall exact QG boundaries remain **87.7%**, not 100%. Source SHA checks **8/8**.
Stage2 **39/39** is included in the combined focused gate. Frozen V0.9 app
assets **10/10** match `0922e08631226b95a77a6599bbc0ac3784e9134b`.

Read-only real coverage audit inspected all **27** locally available sources:
**27/27** source hashes match and remain unchanged; **27/27** correctly return
`STUDENTIZER_COVERAGE_UNPROVEN` without a configured provider; **0** student
derivatives are published. See `real_coverage_audit.json`. This is a truthful
coverage gap audit, not an XML Studentizer PASS or real application UAT.

## Consequence and remaining gate

Default teacher-only production now uses conservative per-item whole-job V0.9
fallback because no real complete reviewed evidence exists. Earlier C2 eager
COM-prepare-plus-XML teacher-only timing is **not current C3 performance**.
This round makes no speedup claim; teacher-only performance may regress. Paired
and student-only supported XML paths are preserved.

The next gate requires narrowly selected real, independently reviewed complete
Golden evidence, actual teacher-to-student preservation/content checks and WPS
open/save/reopen/visual evidence. Universal real-corpus support, zero COM and
C3 performance completion remain unproved. No release/installer/UI work or
frozen A-Line/C1/B-Line/V0.9 core changes are included.

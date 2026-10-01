# V1.2 C1 UAT Fix Gate

**Status: PASS — `C1_UAT_FIX_PASS`**
**Branch:** `feature/v1.2-c1-uat-fixes`
**Rules:** [C1 Slot Routing Business Rules](C1_SLOT_ROUTING_BUSINESS_RULES.md), user-approved and independently reviewed by **Codex GPT-6.1 Sol** (PASS).
**Scope:** three-slot routing, paired/teacher-only/student-only input semantics, clean per-job results, and real WPS round-trip evidence. A-Line, B-Line renderer core, and V0.9 runtime remain frozen.

## Machine gates

- Focused C1/application/renderer/regression suite: **102 passed, 7 subtests passed**.
- Stage2 baseline: **39/39 passed**.
- Fresh Stage3 full rerun: all eight approved source hashes matched; **408/408 QGs**, **369/369 sections**, **328/328 subquestions**; original-paper recall **100%**; E1/E2/E3/E4, MISS/FP/MERGE/SPLIT all **0**.
- `git diff --check`: PASS. Changed-file review found no A-Line Splitter/StructDoc/Gold/Stage3 implementation, B-Line renderer core, or frozen V0.9 runtime files changed.

Fresh Stage3 output: `C:\xml-uat\c1-stage3-final-20261001\` (`compare.md`, `compare.json`, and eight prediction directories).

## Slot Router and input behavior

- The router uses template-specific labels: 1v1 ends at `六、巩固练习`; class ends at `六、出门测试`.
- Practice blocks remain atomic and internally ordered. The focused `1–10` plus `1–5` fixture routes the complete final `1–5` block to slot 3 and does not create a `6–10` fragment.
- Shared-material/table conflicts fail closed to the whole-job V0.9 path with a reason. X012 paired input exercised this behavior: `TABLE_SLOT_CONFLICT` for `u124`, spanning `final` and `knowledge`; no table split or duplicated component was used.
- X021 paired input exercised XML routing with both templates. X021 1v1 and class outputs expose their respective three labels. X012 exercises the fallback route.
- Paired `TEACHER_AND_STUDENT` input does not call `make_student`; teacher-only and student-only paths were also checked. Student-only produces only the student DOCX and does not invoke the student conversion step.
- Per-job result directories contain nonempty teacher/student DOCX files using user-facing names without underscores. `/api/open` located the result directory; ZIP download independently returned HTTP 200 for both paired integration jobs.

## Real WPS round trip

WPS automation (`KWps.Application`) completed open → SaveAs → close → reopen → PDF export for the four X021 outputs (1v1 and class, teacher and student), and both X012 fallback outputs. All six saved DOCX packages validated; all six PDFs were nonempty and readable, with text on every exported page. The X021 WPS reports detected the appropriate three template labels in all four documents. This is WPS evidence, not Microsoft Word evidence.

Evidence directories:

- `C:\xml-uat\c1-x021-1v1-20261001\`
- `C:\xml-uat\c1-paired-rerun-20261001\`
- `C:\xml-uat\c1-wps-rerun-20261001\`
- `C:\xml-uat\c1-x012-fallback-wps-20261001\`
- `C:\xml-uat\c1-stage3-final-20261001\`

## Limits

XML routing is not claimed for every document. A connected table/material that cannot be assigned wholly to one slot intentionally uses the existing V0.9 whole-job fallback. No Renderer, COM, or UI roadmap work is authorized by this gate.

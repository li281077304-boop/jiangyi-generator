# V1.2 XML Finalization — Topic Title Projection Checkpoint

Date: 2026-10-07 (Asia/Shanghai)
Branch: `feature/v1.2-c4-release-engineering`
Base: `599b1393c6cd16b7d260acf630a38105fa4d4fe8`

## Change

The shared post-render normalizer now shortens only the first source title
paragraph immediately after the unique knowledge-slot heading. It applies the
deterministic topic normalizer and changes the paragraph only when its result
exactly equals the already selected cover topic. It does not search and replace
matching text elsewhere. The evidence records the original and display title.

The 1v1 knowledge anchor is `知识精讲`; the class anchor is
`知识精讲&例题讲解`. The original source document is untouched.

For the incident training source, the body title changed from
`九年级上学期物理期末复习（易错精选60题27大考点）` to `易错题精选`, matching
the cover and output name.

## Metadata source

The recovered teacher source has no explicit “教学目标” or “重点难点” fields.
Its 27 ordered section headings support deterministic classification as a
training-type handout. The current displayed objective/difficulty sentences are
short rule-generated wording for that handout type; they are not quotations or
verbatim extraction from the source. No free-form AI text generation was used.

This distinction remains important for product acceptance: if the displayed
generic wording is not suitable, a source-grounded value or an explicitly
approved product rule is still needed. This checkpoint does not claim that the
generic wording has been accepted by the user.

## Evidence

- Real browser direct upload of the recovered teacher/student pair, 1v1:
  job `e98b52e401b94f45a6e021170acaed89`, status `done`, renderer `XML`,
  elapsed `31.751s`.
- Teacher/student alignment: 60 canonical occurrences, 0 unmatched, 0
  ambiguous. Canonical slots: knowledge 25, immediate 24, final 11.
- Display renumbering: applied from the same canonical route map.
- Product Integrity and package validation: PASS for teacher and student.
- Normalizer evidence: `source_title_projection=APPLIED`, exact source title to
  `易错题精选`.
- `KWps.Application` open/SaveAs/reopen/PDF round trip: PASS for both; PDF pages
  51 teacher / 26 student. Word paragraph, table, OMML, and inline-image counts
  were unchanged through the round trip.
- Visual check of pages 1–2: cover metadata fits; body heading on page 2 is
  `易错题精选`; module 3 remains on page 2.
- Focused regression: 59 passed, 8 subtests passed.
- `git diff --check`: PASS.

Detailed external evidence is under
`C:\xml-uat\v12-finalization-20261007-meta-title-r2\`.

## Limits and next action

- This is a 1v1 incident-pair rerun. Class title behavior is covered by the
  focused normalizer regression but was not regenerated in this checkpoint.
- Fixed evaluation set XML success remains unmeasured; the 33-topic frozen
  denominator must still run. OCR/image-role and final full-regression reviews
  remain separate gates.
- No EXE was built. Overall status remains `V1_2_XML_FINAL_BLOCKED`.

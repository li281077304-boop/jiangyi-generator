# V1.2 XML Finalization Plan

Date: 2026-10-07
Branch: `feature/v1.2-c4-release-engineering`
Baseline: `cd7e4019ca3dcb8f0d95427e8300d72d7ae29031`

## Phase 0 status

The remote branch and local `HEAD` match the baseline. The working tree is not clean: it contains an in-progress canonical alignment, routing, metadata, topic normalization, and image-role change set. These changes are retained for review; no reset, checkout, or cleanup is permitted. A previous handoff already recovered and fixed the recursive-output incident source pair, so recovery is not repeated.

The current diff is not accepted as correct merely because it exists. Before further implementation, focused tests and evidence must validate each changed boundary. The two known unresolved issues remain explicit: the real math pair has repeated question numbers and no proven one-to-one canonical mapping; and the OCR/image-role evidence helper is not yet demonstrated to influence production routing. Browser direct-pair UAT and ZIP UAT also remain unverified on a service proven to run this checkout.

## A. Teacher/student canonical alignment

Use the student/original source to propose an ordered question skeleton, then align teacher occurrences by structural order, normalized stem evidence, question context, and attached resource relations. A canonical occurrence is accepted only when each real question maps uniquely in both documents. Teacher-only answer, analysis, method, or annotation material attaches to an aligned occurrence; it is not promoted to an independent question without an independently verifiable stem. Duplicate numbers are allowed only when contextual evidence yields a unique order-preserving alignment. Missing or ambiguous real questions fail closed as `ALIGNMENT_UNRESOLVED`.

Record source hashes, occurrence ids, source node ids, evidence used, confidence/status, unmatched and ambiguous counts. Never align by ordinal alone, raw block id alone, unbounded fuzzy text, or by dropping unmatched questions.

## B. Route once, project twice

After canonical alignment, compute one destination slot per canonical occurrence. Attach teacher answers, analysis, and bound assets to that occurrence's slot; project the corresponding student question/assets to the same slot. Preserve each document's physical block order within each slot. Validate explicit source section headings, shared-material connected components, atomic tables, and asset bindings before rendering. Both projections must provide evidence from canonical occurrence to teacher/student source nodes and destination slot. Any conflicting or incomplete projection fails closed; it must not fall back to independent routing.

## C. Local OCR selection and package budget

Evaluate a CPU-only, offline Windows OCR stack with bundled lightweight Chinese models (RapidOCR/ONNX Runtime is the first candidate). Do not add a dependency until a reproducible local build confirms Chinese recognition, no network/API use, and attribution/license requirements. Measure the actual compressed RC package delta, separately reporting runtime and model sizes. Target <=30 MB where quality is comparable; <=50 MB is the preferred ceiling. If no candidate is validated, keep OCR status unsupported and route image-dependent ambiguity to fail-closed rather than guessing.

## D. Image role and source preservation

Classify images as `DECORATIVE`, `QUESTION_ASSET`, `KNOWLEDGE_ASSET`, or `TEXT_IMAGE` from structural context plus OCR evidence. OCR is classification evidence, not a replacement for the embedded image. Preserve original image relationships and bytes. A question asset follows its canonical question; a knowledge asset follows its knowledge section; decorative content cannot create metadata or question boundaries. If image ownership is ambiguous or its relocation would lose content, fail closed. Store image SHA, source node, OCR text/confidence, assigned role, and canonical/section owner in audit evidence.

## E. Topic normalization

Keep the full source topic as provenance. Produce the display topic deterministically by preserving meaningful topic/section numbers and the core subject while removing role labels, file extensions, promotional phrases, redundant grade/book/version strings, and separately represented exam-period tails. Do not paraphrase the core topic with AI. Add table-driven tests for the reported `专题12.4 一次函数的实际应用` case and ensure the same topic is shared by teacher/student outputs.

## F. Frozen capabilities and boundaries

- Frozen A-Line Splitter semantics, StructDoc meaning, Gold, and V0.9 runtime assets are not modified.
- V0.9 remains available only to explicit developer/diagnostic or human emergency paths; normal production XML failure is an explicit failure, never a V0.9 success.
- Existing Product Integrity and package validation remain mandatory.
- Page-one divider coordinates/structure are frozen. Module 1/2 and module 5 may be empty under current rules; module 3 must begin on page two.
- No text-fingerprint-only matching, guessed metadata, image replacement by OCR text, partial renumbering, or success-rate optimization by weakening validation.
- No EXE build until source gates pass; no tag, GitHub release, or installer in this task.

## G. XML coverage denominator

Freeze the evaluation set before running: the 27 fixed raw source topics, the recovered incident pair counted as one topic, and the first 20 distinct additional raw topics in deterministic corpus order. Teacher/student members and alternate input packaging for one topic are not additional topics. Exclude generated outputs, copies, and result/runtime paths; retain every eligible topic in the denominator, including rejects and failures. Record source SHA and roles, XML outcome, failure phase and exact reason, OCR participation, pair alignment, package validation, and Product Integrity. Report `XML_SUCCESS / ALL_TOPICS`, plus whole-job-independent phase/reason counts. A topic counts as XML success only if the final XML-produced teacher/student deliverables pass the required validations; V0.9 output never counts.

## H. Mandatory fail-closed cases

Fail closed on unmatched/ambiguous real questions; conflicting teacher/student structure; unresolved shared material across slots; atomic table spanning destinations; unsupported revisions/bookmark/relationship or resource behavior; loss or uncertain ownership of image/OMML/OLE; incomplete or non-unique block projection; metadata with no reliable source (leave empty and warn); cross-question references that make renumbering unsafe (skip renumbering for the whole pair with warning); product-integrity or package failure; ambiguous template/container structure; and any OCR-dependent decision below the validated confidence/ownership contract. XML failure is visible as `XML_UNSUPPORTED` or `XML_FAILED` with a reason and does not invoke V0.9 automatically.

## Execution order and gates

1. Review and focused-test the inherited dirty diff; preserve all work and write a delta inventory.
2. Complete and validate canonical alignment and route-once projection on the incident pair and real math pair. Ambiguous pairs remain rejected.
3. Validate metadata ownership and deterministic topic normalization.
4. Integrate OCR/image-role evidence in the production routing path only after offline runtime/model/package measurement and regression tests.
5. Run the complete frozen denominator: 27 + incident topic + 20 additional distinct topics; retain all failures.
6. Run Direct 2 DOCX and ZIP × both templates on the incident pair, product/layout/integrity checks, and representative WPS round trips.
7. Run final full regression and packaged Windows EXE UAT only after XML coverage and product gates qualify. Report blocked status without an EXE build if any earlier required gate fails.
8. Request independent Codex GPT-6.1 Sol reviews at the alignment architecture, OCR/image ownership, coverage result, and final packaged candidate gates. If unavailable, record `CHIEF_UNAVAILABLE`; do not infer Chief PASS from machine tests.

## Current evidence inherited from handoff (not yet re-certified on this worktree)

- The incident pair has a fixed fixture and earlier WPS Open → SaveAs → Reopen → PDF evidence for four XML-generated template/role outputs; module 3 was recorded as starting on page two.
- The math pair is recovered from original training-corpus input, not generated output. Its hashes and provenance are in its fixture manifest.
- Earlier direct browser upload of the incident pair returned HTTP 422 for teacher/student topic mismatch. The service revision was not proven to match this worktree; ZIP browser UAT was not run.
- Earlier focused tests were 92 passed plus 6 subtests before the latest metadata/alignment changes. That result is stale and must not be reported as current.
- No XML full-denominator result, OCR production-routing proof, current packaged EXE UAT, or Chief PASS is established by this plan.

# C3 Round 7 — standalone reviewed physical-range Studentizer

Base: `a7ced4bc615c7d9641557ab05a35e1a2a2340e46`.
Worker: actual GPT-6.1 (`gpt-6.1-sol`).
Chief: **Codex GPT-6.1 Sol**; independent implementation verdict **PENDING**.

## Scope and trust contract

The public `studentizer.prepare_student` now accepts a separate
`PhysicalRangeSemantics` contract. It is a **standalone capability**, with no
production provider, orchestration route or A-Line change. The old
`StudentizerSemantics` / `_plan` path and supplied-student bypass remain intact.
Source hashes validate identity; they never select a sample-specific algorithm.
No sample name, subject or X008 hash is embedded in the capability module.

An independently reviewed caller must provide:

- Identical source SHA, one review ID and the independently approved whole-root
  after-document C14N hash.
- One exact-address/full-subtree fingerprint entry for **every direct `w:body`
  child**, each with exactly one RETAIN/REMOVE decision, reason and review ID.
- Disjoint contiguous complete answer/analysis ranges with actual physical owner
  IDs, full retained prompt intervals and reviewed reasons. Owner IDs are not
  invented frozen QGs. Duplicate owners, ambiguous/overlapping ranges,
  mismatched ownership and incomplete ledger coverage fail closed.
- Explicit acknowledgement of the exact source's inherited missing bookmark
  targets, if any. The API independently validates the same source/after
  dependency inventory; the acknowledgement cannot add or hide changed targets.

Authority is the exhaustive independent content review, not marker, role,
numbering or color. The UAT harness consumes the separately Chief-approved
X008 ledger; the existing packet still has `approved=false` and
`production_provider=false`. This API does not make that packet production policy.

## Preservation and fail-closed rules

Only complete plain-text `w:p` subtrees with known text/formatting children can
be removed. Any table, object, formula, drawing, bookmark, field, hyperlink,
revision or unknown child in a deletion range refuses the request.
Retained child subtree fingerprints and order remain exact, including physical
tables/objects that stay intact; this is not table/answer-object deletion support.

Main-story fields must have balanced begin/separate/end scope and known
TOC/REF/PAGEREF/local-HYPERLINK dependencies. A deletion cannot intersect any
field's physical interval. Bookmark IDs/names must be unique, endpoints paired
and retained. A referenced bookmark's interval cannot intersect deletion.
Unreferenced paired bookmarks may surround removed answers: exact endpoints and
order survive, and the dependency inventory proves no reference targets them.

Local hyperlink anchors are checked against bookmarks or the exact acknowledged
inherited missing set. Relationship hyperlinks must resolve to explicit external
targets without ambiguous fragments. Cross-story local anchors participate in
bookmark dependency checks; cross-story relationship hyperlinks refuse.
Other-story fields support only fully unchanged balanced PAGE/NUMPAGES scalar
counters (optional MERGEFORMAT). Cross-story REF/PAGEREF/unknown field dependency,
unbalanced counters, unsupported revision/content-control/comment/note/textbox
systems and missing relationships fail closed.

Source/after boundary dependency signatures must match. All non-document package
members retain original bytes and member order. The whole after-root must equal
the independent Golden both before and after serialization. Package validation
then precedes the existing atomic no-overwrite publication; failure publishes
no DOCX. No WPS/COM code was added to this capability.

## Actual approved X008 transformation

Actual public `prepare_student` result: **XML_PREPARED**.

- Source SHA: `56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`.
- After-root: `6b93cfc1594afc35bfa7801a4a73768185058fb2101e41e9f3d363173f31e0a2`.
- Derived DOCX SHA: `67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9`.
- 34 physical owner ranges; **118** complete answer/analysis paragraphs removed.
- **146** retained direct children; full fingerprints/order exact.
- Non-document package parts and member order exact; output/root/package match
  the independent Golden. Source and Golden bytes remain unchanged.

The output was made by the actual Studentizer API, not manual splicing in the
UAT harness. The harness builds the reviewed contract, calls the public entrypoint
and independently compares its output. Five physical questions lacking frozen
QGs remain physical owners, without modifying frozen semantics.

## Real derived-output WPS evidence

Final evidence is from **the repaired capability's new verified output**, under
`C:\xml-uat\c3-round7-physical-ranges\verified-wps\`.
Actual provider: `KWps.Application`, processes at
`D:\Program Files\WPS Office\12.1.0.28505\office6\wps.exe`.
Compatibility Name reports Microsoft Word; this is **WPS**, not Word evidence.

With alerts enabled, ordinary Open → SaveAs2 **new DOCX** → Close → Reopen →
PDF export all returned successfully. DOCX **7,067,486 bytes** and PDF
**2,127,287 bytes** are readable/nonempty; both pre-WPS and saved packages validate.
Before/after COM counts are identical: 142 paragraphs, 27 inline shapes
(4 embedded OLE and 23 pictures), 1 floating shape, 0 tables, 0 OMML, 9 pages.
Saved XML has all **142 paragraph text values in exact source order**, 24 drawing
elements and all 4 OLE payloads byte-identical. Source/Golden/input hashes did
not change.

All **9 PDF pages** render and have readable extracted content. All **34 question
numbers** extract in original 1–34 order. The approved deletion, rather than
marker absence, establishes answer elimination; PDF answer/analysis markers
are additionally zero. Actual visual inspection covered **pages 1, 5, 6, 9**:

- Page 1: retained title/TOC, including the same two undefined-bookmark errors.
- Page 5: complete Q15–Q20 prompts/options/state-model figures and blanks.
- Page 6: Q21–Q24 figures/prompts; Q23 four OLE temperatures remain visible
  (0°C, 4°C, 20°C, 30°C), including experiment options and blanks.
- Page 9: Q33–Q34 models/cooling graph, both subquestions, all options/blanks.

No new visible content/layout damage was found in these **four inspected pages**.
This is not a claim of full nine-page visual/human classroom-readiness review.
All-page automated readability plus exact all-paragraph/object preservation is
recorded separately from sampled visual evidence.

**Repair observation limit:** normal alerts-enabled synchronous Open/Reopen
returned without an unresolved blocking modal or exception; repair was not
requested. Modal prompts were **not directly instrumented**, and automatic
repair without a prompt **cannot be excluded**. No claim of proved repair
absence or universally corruption-free behavior is made.

Original PDF and derived PDF each display **2** undefined-bookmark errors.
Cached XML `w:t` counts are **0** because WPS's evaluated field display differs
from cached XML text; actual PDF observation governs this finding. Existing
cached TOC page numbers remain stale after answer removal and are not repaired.

## Machine gates and limitations

37 new capability tests (36 generic cases plus 1 real approved transformation)
cover exhaustive ownership, stale hashes, mismatched Golden, atomic refusal,
nonplain deletion, boundary pairing/dependencies, cross-story fields/links,
preserved inherited defects, package preservation and no-overwrite publication.
Final focused suite **222 passed in 52.49s**, including Stage2 **39/39**.
Fresh Stage3: source hashes **8/8**, QG **408/408**, sections **369/369**,
subquestions **328/328**, original Recall **100%**, E1–E4/MISS/FP/MERGE/SPLIT
**0**; overall exact QG boundaries **87.7%**. Frozen V0.9 assets **10/10**.

During implementation an overbroad cross-story guard refused unchanged footer
PAGE/NUMPAGES fields (216 pass/1 fail). It was corrected with balanced scalar-only
support and explicit tests; a fresh output and fresh WPS UAT replaced the earlier
trial. No failed trial is represented as the final gate.

Durable evidence: `fixtures/c3-r7-physical-range-evidence.json`.
External full transform/mutation/protected/WPS/PDF/page records:
`C:\xml-uat\c3-round7-physical-ranges\`.
Performance benchmark **NOT_RUN**: preparation elapsed and UAT timestamps are
diagnostic timings, not whole-job/V0.9 speed comparison or OS zero-COM evidence.
API `com_invocations=0` is not an OS process probe.

This one approved physics source has no OMML/table and tests no answer-object
deletion. Mathematics/chemistry remain unapproved; there is no general real-corpus
coverage, production activation or C3 completion claim. A-Line/C1/B-Line/V0.9,
production planner/provider/orchestrator and UI remain unchanged. Stop for
Codex GPT-6.1 Sol independent implementation/UAT review.

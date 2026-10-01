# C3 Round 6 — approved X008 versus current Studentizer API

Base: `dbcd5a60145a171ca72117b257a1a6e99eba91e2`.
Worker: actual GPT-6.1 (`gpt-6.1-sol`).
Chief: **Codex GPT-6.1 Sol**; independent Round 6 verdict **PENDING**.

## Gate result

**STUDENTIZER_CAPABILITY_BLOCKED**.

The actual public `studentizer.prepare_student` entrypoint returned:

```json
{
  "status": "STUDENTIZER_FALLBACK_REQUIRED",
  "reason_code": "STUDENTIZER_FIELD_SCOPE_UNSUPPORTED",
  "reason_detail": "fldChar",
  "output_path": null,
  "mutations": []
}
```

The first rejected structure is at **physical zero-based `body[3]`**, XML path
`/w:document/w:body/w:p[4]/w:r[2]/w:fldChar`. This block is **RETAIN** in the
independently approved Golden. `_plan` scans the whole body for prohibited
boundary systems before processing any deletion request; the first field alone
prevents every requested mutation, even though it is outside the deletion ranges.

This is a **product capability boundary**, not a WPS/Windows environment block.
No Studentizer derivative exists. Derived-output WPS open/SaveAs/close/reopen/PDF
and content inspection are **NOT_RUN_NO_STUDENTIZER_OUTPUT**. The earlier manual
expected DOCX was neither opened as a substitute nor reported as Studentizer UAT.
No C3 completion, real Studentizer transformation PASS or speedup is claimed.

## Independently approved exact source and oracle

Authority: `C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md`, exclusively
`chief_model = Codex GPT-6.1 Sol`.

- Source SHA256: `56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`.
- Expected whole-root C14N: `6b93cfc1594afc35bfa7801a4a73768185058fb2101e41e9f3d363173f31e0a2`.
- Expected draft package SHA256: `67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9`.

The probe reads the Chief's 34 independently authored prompt/removal coordinate
tuples and checks them against the packet. Exact source bytes, every original
body fingerprint and expected draft/root hashes are checked. Source and expected
package member sets are equal; every non-document member is byte-identical.
The 118 approved removals and 146 protected retained children are requested at
their exact physical addresses. Source and existing expected draft bytes remain
unchanged before/after the call. The draft packet itself continues to have
`approved=false` and `production_provider=false`; the separate Chief report is
content authority, not a production provider.

## Public API compatibility

The standalone probe is `tools/studentizer_audit/probe_approved_source.py`.
It does not call `_plan`, splice XML, invent frozen QG IDs, install a provider or
invoke COM. It submits the complete approved request through existing DTOs with
truthful `owner_kind=physical_question`; this is deliberately outside the
current `question_group` owner contract. The refusal above occurs earlier at
the global field check. No claim is made that the current DTO faithfully
**supports execution** of a contiguous multi-paragraph removal range.

Static API review identifies additional independent incompatibilities:

1. Bookmarks/hyperlinks and fields anywhere in the document are globally refused,
   including approved unchanged front matter and retained prompt structures.
2. Each binding supports only one dedicated marked answer paragraph at its owner
   interval's terminal address, rather than an approved contiguous answer plus
   complete analysis range. Unmarked explanation continuations are unsupported.
3. Only `owner_kind=question_group` is accepted; the complete planner also
   requires a real frozen QG identity. Five approved physical questions
   (3, 4, 10, 16, 24) lack that identity. Renaming their physical owners to QGs
   would fabricate A-Line authority.

These are separate contract observations, not extra runtime results produced
by stripping the first blocker. The source was never altered to bypass checks.
All four OLE are in retained Q23 `body[164]`; the removed 118 paragraphs have no
nontext/boundary subtrees per the Chief approval. Answer-OLE deletion remains
untested. No physical table occurs in this source, so this probe does not extend
table support or mathematical/chemistry coverage.

## Executed evidence and protected gates

Durable actual public-call evidence:
`fixtures/c3-r6-approved-probe.json`.
External fresh protected evidence: `C:\xml-uat\c3-round6-approved-source\`.

Four new tests verify the independently approved full ledger, source-identity
and coordinate mismatch refusal, and the actual real-source fail-closed public
call with no output/mutations/source changes. Focused suite **185 passed in
49.26s**, including Stage2 **39/39**; final four probe tests rerun after adding
the exact first-rejection address assertion. Fresh Stage3 source checks **8/8**:
QG **408/408**, sections **369/369**, subquestions **328/328**, original Recall
**100%**, E1–E4/MISS/FP/MERGE/SPLIT **0**. Overall exact QG boundary remains
**87.7%**. Frozen V0.9 assets **10/10**; compilation and diff checks pass.

Performance benchmark: **NOT_RUN**. `elapsed_seconds=0.087998` in the captured
public-call record measures only one refused preparation attempt; it is not
Studentizer generation speed, a comparison against V0.9, or zero-COM product
evidence. The existing result's `com_invocations=0` is an API field, not an OS
process/startup measurement. No benchmark was added.

## Minimal next capability proposal — not implemented

A separately authorized capability round could add a generic **standalone**
reviewed physical-range contract, without changing A-Line classification:

- Bind the entire identical source, independently approved after-root and
  exhaustive body ledger to one review ID. Accept exact reviewed physical
  owner IDs without pretending they are frozen QG IDs.
- Support disjoint, contiguous complete answer/analysis ranges, each with
  exactly one reviewed physical owner and every paragraph fingerprint. Preserve
  all approved retained children and every non-document package byte/order.
- Replace the blanket refusal of **unchanged** bookmarks/fields with structural
  boundary validation. Permit only boundaries wholly preserved outside removed
  regions; validate bookmark pairing, field begin/separate/end scope, hyperlinks
  and any references that could cross the removed region. Do not merely remove
  the global guard or strip/rewrite these structures.
- Remain fail closed for unknown ownership, overlapping/crossing ranges,
  source/fingerprint mismatch, answer regions containing any object or table,
  split boundary scope, external references that cannot be proved safe,
  unsupported revision/content-control systems, expected-root mismatch,
  changed retained structures/resources, or package validation failure.
- Require exact approved after-root/package preservation plus derived WPS
  open/SaveAs/close/reopen/PDF and full content checks before any supported
  real-source claim. Preserve inherited TOC errors as explicit source limits.

No proposal above is implemented here. Production Studentizer/planner/provider,
job flow, A-Line, C1 rules/Router, B-Line Renderer, V0.9 runtime and UI remain
unchanged. Worker stops after publication for independent Chief review.

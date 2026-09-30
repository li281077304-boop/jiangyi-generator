# C0 Round 3 Template Plan Evidence

**Branch/base:** `feature/v1.2-c-line-integration` / `f96f47cb189e941f411d0365f38134d417fe96cc`
**Worker:** GPT-6 Luna
**Scope:** Define and exercise the smallest A-Line-to-B-Line plan accepted for C0. The independent Chief review accepted one physical `main_content` slot with semantic roles and relationships preserved in the plan. This supersedes the preliminary `INTEGRATION_ARCHITECTURE_BLOCKED` conclusion below; that conclusion was based on the stricter, unapproved assumption that C0 had to target named section cells.

## Accepted C0 target

The immutable B4 template files are used without modification. C0 inserts one source-order stream at the validated body's direct-child location after the template content table and before section properties. The named teaching sections remain within table cells, and the frozen B-Line renderer does not address individual cells. C0 therefore does not claim to populate `知识精讲`, `即时训练`, or the practice cells separately.

The plan preserves each A-Line unit's ID, role, level, parent, `bind_to`, source spans, and evidence. It projects node endpoints through the current StructDoc node index to top-level blocks. For overlapping units, it emits the union of selected top-level blocks once in source order. A cell paragraph endpoint resolves to its owning top-level table, which is the smallest atomic table payload supported by the frozen renderer. A contentful block not covered by any unit fails closed; empty structural paragraphs not covered by units are retained once as separators. Full mode explicitly selects the complete source sequence.

Template identity is pinned to the B4-validated assets:

| Template | Repo path | SHA-256 | Frozen B-Line blob |
|---|---|---|---|
| 1v1 | `v1.1-stable/res/app/2025+1v1讲义模板(2).docx` | `1318fceabaa957b12e371310902fd81a0db08be09cee2121f6cd2606d8fd6a1a` | `e4b2b4b6ff9833f1c1167388ea3f060431226a39` |
| Class | `v1.1-stable/res/app/2025班课模板.docx` | `f51046d841699645b1b49f49f481c559e8502b98589d20b0c7e97cf2f7ba8f13` | `2f52b2034a911e06cb62a8d85006ee82169e3a7e` |

## Direct projection and application evidence

The earlier direct-render assessment used the same unique-block plan for X012 math 1v1 and X021 chemistry class. Teacher and student packages validated, and WPS open/SaveAs/reopen/PDF passed for both roles in both samples. This evidence justified continuing with the Chief-approved slot scope rather than treating missing named-cell targeting as a core-change blocker.

The final HTTP run exercised the same plan through POST, student preparation, A-Line analysis, paired XML rendering, durable job completion, local folder opening, and separate ZIP delivery:

- X012 math / 1v1: both files valid; job done as XML; open and ZIP passed.
- X021 chemistry / class: both files valid; job done as XML; open and ZIP passed; WPS round trip passed for teacher and student, with structural counts unchanged.
- X012 forced unsupported: XML fail-closed; original-source V0.9 whole-job fallback invoked; both files valid; fallback reason and baseline SHA persisted.

Full route and WPS evidence is in `C0_ROUND3_HTTP_UAT.md` and `C:\xml-uat\c0-http-class-uAT-20261001\kwps-http-roundtrip-final.json`.

## Protected regressions

- Expanded machine suite: 120 passed, 7 subtests passed in 164.16s (C0, plan, renderer, importer, validator, StructDoc/NodeIndex, Stage2). Stage2-only: 39 passed.
- Stage3: eight source hashes matched; QG 408/408; sections 369/369; subquestions 328/328 inside parents; MISS/FP/MERGE/SPLIT=0; errors empty.
- The A-Line Splitter, StructDoc, Gold, Stage3 metrics, B-Line XML renderer, package validator, and frozen V0.9 runtime are unchanged. V0.9 manifest asset hashes: 10/10 PASS. Remote frozen tag targets: A-Line `df3825d3a78f34537689af36136dd2588bcd73bc`; B-Line `eae89ea8720b94d29a94fc652830de628f373cd9`.

## Limits

`main_content` is a single stream, not a mapping to each named table section. The C0-approved boundary is sufficient for the first end-to-end integration and is documented in the output rather than inferred as a section-level layout capability. No renderer core change, template edit, COM paragraph projection, or second section insertion mechanism was added.

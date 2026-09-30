# B1 — XML Renderer Spike Recovery Audit

**Round:** 11 (audit only)  
**Active branch/base:** `feature/v1.2-renderer-baseline` / `5372641b99a69d35ed9113ac0c147cf73e2511b4`  
**Audited source:** `feature/jiangyi-v1.2-xml-spike` at `e511790a0a9fa7a251c2be3aed3693d2e5f86eb6`  
**A-Line:** read-only; no Splitter, StructDoc, Gold, or business-rule edits were made.  
**Scope:** inspect old XML-rendering assets and their evidence; do not merge the spike branch or change the B-Line renderer.

## Recommendation

**`PARTIAL_REUSE`** — retain the spike's block importer and package validator as candidate components for a future V1.2 XML renderer, subject to porting them as individual files and running them against the current B-Line contract. Do not reuse the old `xml_engine.build()` end-to-end path: it performs its own legacy split, expects paragraph-number ranges and text markers, and does not accept A-Line StructDoc spans. Rebuild the current-branch orchestration and capability/fallback policy around the preserved A-Line block identities.

The existing code is a useful package-copy prototype with substantial synthetic fixture coverage. It does **not** establish real-corpus rendering or Microsoft Word/WPS visual fidelity. This audit does not authorize formal renderer implementation or any V0.9 fallback changes.

## Source integrity and test gate

- `origin/feature/jiangyi-v1.2-xml-spike` resolved to the requested `e511790a0a9fa7a251c2be3aed3693d2e5f86eb6`.
- The source was exported to an isolated directory for inspection/test execution; no branch checkout, merge, cherry-pick, or edit of that branch occurred.
- Tests ran with the archived V0.9 embedded Python 3.12.10 (`lxml 6.1.1`, `python-docx 1.2.0`):
  - `res/app`: **23 passed** (BlockImporter, package validator, and xml engine fixtures).
  - `tools/uat`: **11 passed, 1 skipped** (the skipped test is a Mac-only guard).
  - Total: **34 passed, 1 platform-specific skip**.
- These tests create synthetic DOCX fixtures. They do not open/render a real generated DOCX in Word or WPS.

## Capability audit

| Capability | Spike evidence | Recovery assessment |
|---|---|---|
| Paragraph cloning | `BlockImporter.import_blocks(elements)` deep-copies selected XML elements; fixture checks preserved text/paragraph content. | Reuse candidate; pass source `w:p` elements resolved from current A-Line spans. |
| Table cloning | A selected `w:tbl` subtree is deep-copied. A fixture checks a basic table. | Reuse candidate for tables as atomic blocks. Nested-table and real-template visual behavior still need targeted tests. |
| Relationships / package parts | Relationship attributes in the Office relationship namespace are remapped. Internal targets are recursively copied; external relationships are recreated. Missing IDs and copy errors are reported as unsupported. | Reuse candidate; retain fail-closed unsupported reporting. |
| Images | DrawingML image relationships and VML image preview references are copied through the relationship graph. Synthetic image fixtures exercise both paths. | Fixture-supported; real Word/WPS visual verification remains required. |
| OMML | Raw paragraph cloning preserves inline OOXML not specially rewritten by the importer. No dedicated native OMML test or Word visual test was found. | Structurally plausible only; classify as `FALLBACK_REQUIRED` until a real OMML UAT passes. |
| OLE / embeddings | Recursive relationship copying carries embedding parts. A dummy OLE payload is checked by SHA256 and a VML preview relationship is tested. | Package-byte preservation is fixture-supported; real MathType/OLE activation and rendering are unverified, so `FALLBACK_REQUIRED` pending UAT. |
| Drawings / shapes | Selected XML is preserved; `wp:docPr` and picture `cNvPr` IDs are normalized/remapped. Fixtures cover VML and selected DrawingML relationship cases. | Partial reuse. Not a guarantee for arbitrary drawing/SmartArt/shape semantics. |
| Styles | Referenced paragraph/run/table styles and their dependencies are migrated; conflicting IDs are assigned safe IDs. Tests exercise style collisions and linked/based-on dependencies. | Reuse candidate; run current-source/template regression after port. |
| Numbering | `num` and `abstractNum` definitions are migrated with collision remapping. Tests check conflicting numbering IDs and definitions. | Reuse candidate; retain fixture tests and add current B-Line cases. |
| Content types | New package parts retain their declared content type through the python-docx `Part` package path. Validator requires `[Content_Types].xml`, but does not fully validate every part's default/override declaration or OPC schema conformance. | Partial; close validator coverage before relying on this as a complete content-type gate. |
| Relationship ID remapping | Direct `r:*` attributes are rewritten to destination relationship IDs; recursively copied part relationships are retained. Tests check external hyperlinks, image/OLE, and nested synthetic package relationships. | Reuse candidate, with current validator run on every output. |
| Template anchors / insertion | Legacy `xml_engine` finds marker paragraphs by text prefix through the template body (including tables/text boxes), then inserts cloned blocks after the matching paragraph. Missing markers fail closed. | Do not reuse its text-marker/legacy split orchestration as the A-Line contract. Build explicit marker-to-template targets in the current B-Line. |
| Package validation | Checks ZIP CRC, required parts, relationship owners/targets, dangling `r:id`, numbering/style references, duplicate drawing IDs, and image/OLE relationship targets. Tests exercise the main failure paths. It explicitly is not an ECMA-376 schema validator. | Reuse candidate as a focused validator; add content-type and current-output invariants where required. |

The importer explicitly reports several unsupported structures: footnote/endnote/comment references and ranges, custom XML/data-binding wrappers, relationship copy failures, and hyperlinks whose bookmark anchor is omitted from the selected blocks. Bookmark handling has a separate limitation: `_remap_bookmarks()` repairs IDs and drops unmatched bookmark starts/ends or clears orphan hyperlink anchors while recording statistics; a split bookmark range is not necessarily added to the `unsupported` list. The current capability check must treat any bookmark-loss/drop statistics as `FALLBACK_REQUIRED` unless a separately tested policy proves the selected span safe.

## Existing pipeline boundary

`xml_engine.scan()` walks direct `w:body` children and collects direct `w:p` / `w:tbl`; its paragraph list is not StructDoc. `xml_engine.build()` calls legacy `split_ideal()`, validates integer paragraph ranges, finds textual template markers, imports the corresponding raw body-child slice, and validates the saved package. It therefore cannot be moved wholesale into the A-Line main path. A current implementation must resolve A-Line spans to the same source package's XML elements without altering Splitter semantics, then pass selected paragraph/table elements to a package-import layer.

The old builder is also not a whole-job V0.9 fallback. The Long Goal's fallback remains a separate, explicit whole-job route to the untouched V0.9 flow when current XML capability checks reject a source.

If the importer is reused, retain `THIRD_PARTY_NOTICES.md` and `LICENSES/docxcompose-MIT.txt`; its selected relationship/style/numbering migration algorithms are attributed as adapted from docxcompose under MIT.

## Historical success evidence and its limits

The spike README contains an **2026-08-10 historical experiment note** claiming that a prior XML experiment copied paragraphs, tables, images, formulas/OLE, and styles, including a stated 1,116 MathType/OLE relationship count. The README explicitly says those Word display results were not regenerated or reverified in the later spike. No generated real-source DOCX or Windows Word/WPS UAT log was present in the audited spike tree.

The 2026-09-28 spike README describes the current fixture coverage and explicitly sets `REAL_OLE_UAT_REQUIRED: YES` and `WINDOWS_WORD_UAT_REQUIRED: YES`. Its UAT preparation docs say they contain no copied real user documents and keep Word open/save/reopen and visual review pending. Treat the August note as historical direction only, not as a pass for the `e511790` code.

## Chief disposition

**`PARTIAL_REUSE`** (Chief audit verdict: **PASS for the recovery decision only**). Reuse only the isolated package importer, focused package validator, and appropriate fixture tests after current-branch adaptation. Reimplement the A-Line extraction/orchestration, stable template targeting, capability check, and explicit whole-job fallback. No code was moved in Round 11. This verdict is not an XML Renderer or real UAT pass.

## Next action

Begin the next authorized implementation round from the current B-Line head. Port only the minimum importer/validator assets approved above, add current StructDoc/span-to-OOXML block extraction and tests, and keep unsupported structures fail-closed for later fallback integration. Do not change A-Line or V0.9 core behavior.

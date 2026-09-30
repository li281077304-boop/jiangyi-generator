# B2 Minimal XML Renderer

## Scope

The B2 structural extraction and explicit-target clone primitive is now connected to a narrow resource importer and package check. It is not the production Renderer, does not invoke COM, and does not change A-Line or V0.9 behavior. B3 evidence and limits are recorded separately in `B3_PACKAGE_RESOURCE_INTEGRITY.md`.

`BlockSpan(start, end)` addresses current StructDoc content-node IDs. `TemplateTarget(body_child_index)` identifies the zero-based direct child position in the template `w:body`; insertion occurs before that child. The index counts physical body children, including a terminal `w:sectPr`, so the terminal section properties remain last. No anchor text is searched.

The renderer reads the source DOCX once and passes the same immutable bytes to both the OOXML parser and StructDoc parser. Top-level `body_idx`, block kinds, table rows/cells, and nested cell block order are checked against the OOXML tree before any selection is cloned. IDs such as `b7` or `b7.r0c1.n2` therefore resolve by structural ordinal, not paragraph text, text fingerprint, or COM paragraph number. Empty paragraphs remain nodes in that walk.

## Supported payloads

- A body paragraph, cloned as raw `w:p` XML.
- A top-level table selected as one atomic block, cloned as its entire `w:tbl` subtree, including nested tables and cell paragraphs.
- A paragraph span whose endpoints are StructDoc leaves and whose selected leaves all map to body-level paragraphs outside tables.
- Inline OMML within cloned paragraphs is preserved as raw XML. Direct run/paragraph formatting travels with the clone.
- The template target is explicit and structural. Multiple selected blocks are inserted in input order at that target.

## Fail-closed boundaries

- A table cell paragraph cannot be emitted by itself. It must be selected through its owning top-level table as one atomic block.
- A paragraph range that crosses a physical top-level table block is rejected, even if that table has no paragraph leaves. Nested tables cannot be selected independently. A cross-table-range flattening could discard table structure.
- Relationship-bearing content is delegated to the adapted BlockImporter. A nonempty importer `unsupported` report or a failing post-save package check rejects the output before atomic replacement.
- Package-scoped bookmarks, bookmark hyperlink anchors, comment/footnote/endnote references and ranges, permission ranges, tracked insert/delete/move content and range markers, table-cell revisions (`cellIns`, `cellDel`, `cellMerge`), conflict revisions, and WordprocessingML revision-property tags ending in `Change` are rejected. Content controls and custom XML are also rejected because IDs, ranges, bindings, or related package parts may not survive isolated cloning.
- Unknown StructDoc blocks, structural count mismatches, absent template parts, and unsupported resource/relationship graphs are rejected.
- Package checking covers selected structural references, but is not ECMA-376 schema validation and does not prove Word/WPS fidelity, real-corpus coverage, or a user-facing renderer contract.

The output begins as the template package; the importer adds dependencies required by selected content. A focused validator checks the saved temporary package before the output path is atomically replaced. The output path must differ from both inputs.

## Machine evidence

Eighteen isolated Renderer fixture tests cover duplicate-text ID selection with a formatting fingerprint, empty paragraph selection, atomic table insertion, nested-table and empty-cell-paragraph preservation, raw OMML preservation, image and external hyperlink remapping, dummy OLE embedding copy, fail-closed unresolved relationships, bookmark-anchor and tracked-change rejection, output/input alias protection, nested-table selection rejection, physical spans crossing regular or empty table blocks, and single-read source snapshot use. The adapted importer contributes 9 tests and package validator 6 tests. Synthetic DOCX evidence does not constitute Word/WPS UAT.

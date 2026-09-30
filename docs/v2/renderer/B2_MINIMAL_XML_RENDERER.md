# B2 Minimal XML Renderer

## Scope

This round adds an isolated structural extraction and OOXML clone primitive. It is not the production Renderer, does not invoke COM, and does not change A-Line or V0.9 behavior.

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
- Any relationship-bearing element (images, hyperlinks, OLE, and similar references) is rejected until relationship/package-part migration is added and separately validated.
- Package-scoped bookmarks, bookmark hyperlink anchors, comment/footnote/endnote references and ranges, permission ranges, tracked insert/delete/move content and range markers, table-cell revisions (`cellIns`, `cellDel`, `cellMerge`), conflict revisions, and WordprocessingML revision-property tags ending in `Change` are rejected. Content controls and custom XML are also rejected because IDs, ranges, bindings, or related package parts may not survive isolated cloning.
- Unknown StructDoc blocks, structural count mismatches, absent template parts, and missing style/numbering IDs are rejected.
- This round does not establish cross-package style/numbering semantic equivalence, content-type/OPC validation, image/OLE integrity, real-corpus coverage, Word/WPS visual fidelity, or a user-facing renderer contract.

The output retains the template package parts and replaces only `word/document.xml`; the requested payload is inserted only after all selected nodes pass local checks. The output path must differ from both inputs. Output creation uses a temporary file followed by an atomic replace.

## Machine evidence

Fifteen isolated fixture tests cover duplicate-text ID selection with a formatting fingerprint, empty paragraph selection, atomic table insertion, nested-table and empty-cell-paragraph preservation, raw OMML preservation, rejection of relationship-bearing, bookmark-anchor, tracked-change, and table-cell revision content, output/input alias protection, rejection of nested-table selection and spans crossing regular or empty table blocks, and single-read source snapshot use. A table-driven check covers representative `Change`, cell, and conflict revision tags. These synthetic DOCX tests do not constitute Word/WPS UAT.

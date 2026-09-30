# B0 — StructDoc to COM Paragraph Projection Gate

**Result: `RENDERER_CORE_CHANGE_REQUIRED`**  
**Round:** 10  
**Branch/base:** `feature/v1.2-renderer-baseline` / `b7ba4a7b21ae215c7f0988169bb42372f1de47b9`  
**Scope:** Read-only projection audit. No Renderer Adapter, V0.9 Writer, Splitter, StructDoc semantics, Gold, UI, or generated handout was changed.

## Finding

The simplest proposed mapping is false in the active V0.9 automation environment. For every Stage3 source below, the count of main-story OOXML `w:p` elements differs from `Document.Paragraphs.Count`. The entire count difference is in paragraphs that COM reports as being inside tables. This changes the ordinal of following paragraphs and prevents using the OOXML `w:p` ordinal as the V0.9 COM paragraph index.

The current StructDoc node IDs include cell-content endpoints such as `b2.r0c0.n0`. Stage3 predictions contain 2,376 span endpoint occurrences (1,785 unique endpoint IDs). No exact structural mapping for those endpoints to the extra COM table paragraphs was established. Consequently **0/2,376 endpoints are proven to project** by this audit; this is a proof-coverage result, not a claim that a different structural mapping is impossible. Text search, fixed offsets, and per-sample corrections were not used.

Whole-table boundaries may still be representable by the first and last COM paragraphs in a table, but the observed per-cell sequence mismatch and lack of a validated table/container-to-COM mapping mean that this exception is not proven here. Cell-level nodes can be Renderer boundaries in the Stage3 outputs, so they cannot be scoped away.

There is also a downstream boundary constraint in the frozen V0.9 writer: both `_fill_com.ps1` and `_fill_class.ps1` detect when either endpoint is in a table and expand that endpoint to the first or last paragraph of the whole table before copying. Therefore even an exact cell-level COM ordinal would not preserve a cell-level Renderer boundary through the current writer. The core remains untouched; this is recorded as a compatibility limit, not changed in this round.

## Paragraph sequence definitions

### OOXML / StructDoc-side candidate

The audit enumerated `w:p` elements under `word/document.xml` → `w:body` in recursive document order, including paragraphs in table rows/cells and nested tables, and preserving empty paragraphs. Paragraphs inside `w:txbxContent` were excluded from the main-story sequence. Header/footer, footnote, and endnote parts were not included. A formula, image, or OLE object inside a paragraph remains part of that one paragraph and does not create a separate `w:p` ordinal.

This sequence is the candidate OOXML order; it is **not** asserted to equal `Document.Paragraphs`.

### COM sequence

Each same-source DOCX was opened read-only through the active `Word.Application` ProgID. For every `Document.Paragraphs.Item(i)`, the probe recorded the 1-based index, `Range.Start`, `Range.End`, normalized `Range.Text`, `Range.Information(12)` table status, and cell row/column where available. Paragraph ranges were monotone by start/end in all eight documents.

The ProgID did not activate Microsoft Word on this machine. It reported `Name=Microsoft Word`, `Version=12.0`, while the launched automation process was `wps.exe` at `D:\PROGRA~2\WPSOFF~1\1210~1.285\office6\wps.exe /Automation`. This is the provider V0.9's generic `Word.Application` call resolves to in the current user environment. No Microsoft Word behavior is claimed.

## Stage3 results

All eight frozen Stage3 source files were hash-checked against `C:\xml-uat\stage3-expansion\baseline_inputs.json` before opening. The detailed read-only COM paragraph records were written outside the repository to `C:\xml-uat\stage3-expansion\b0_com_paragraphs.json`.

| Sample | OOXML main `w:p` | OOXML in-table | COM Paragraphs | COM in-table | Delta | Prediction endpoint occurrences / unique IDs |
|---|---:|---:|---:|---:|---:|---:|
| X003 | 445 | 56 | 469 | 80 | +24 | 226 / 181 |
| X004 | 908 | 56 | 932 | 80 | +24 | 272 / 222 |
| X006 | 905 | 49 | 919 | 63 | +14 | 764 / 535 |
| X012 | 909 | 125 | 931 | 147 | +22 | 406 / 299 |
| X013 | 238 | 17 | 240 | 19 | +2 | 186 / 111 |
| X019 | 247 | 61 | 263 | 77 | +16 | 92 / 76 |
| X021 | 475 | 154 | 525 | 204 | +50 | 206 / 170 |
| X025 | 715 | 108 | 746 | 139 | +31 | 224 / 191 |
| **Total** | **4,842** | **626** | **5,025** | **809** | **+183** | **2,376 / 1,785** |

For each sample, the number of COM paragraphs outside tables equals the number of OOXML main-story paragraphs outside tables. Every mismatch is in the table portion: `COM in-table - OOXML in-table = COM total - OOXML total`. Thus a global direct ordinal mapping shifts at table content, even though the non-table totals match.

X003 illustrates the table behavior directly: COM item 3 is at `Range.Start/End=14..150` in table row 1, column 1; item 4 is `150..281` in row 1, column 2; item 5 is an empty range `281..282` still reported in row 1, column 2. The corresponding raw OOXML table sequence has 56 `w:p`, whereas COM reports 80 table paragraphs. `Information(12)` and `Cell.RowIndex`/`ColumnIndex` were available; the attempted table-index property did not return a usable index.

Empty paragraphs were retained by both enumerations. COM also returned empty table-cell ranges beyond the OOXML paragraph count. X003 has one section: COM reports its range as `0..24498`; its final paragraph is index 469 at `24497..24498`. This confirms the final section marker is observable in COM, but does not reconcile the table ordinals.

## Special content and scope

- **Tables:** All eight samples have table content. Table/cell location is exposed for COM ranges, but the table paragraph sequence has 2–50 additional COM entries per file. Current StructDoc `pno` is direct-body-paragraph numbering, while table cell paragraphs use `pno=None`; neither that field nor `NodeIndex.order` is a COM ordinal.
- **Textbox:** X019 and X025 contain respectively 48 and 80 `w:p` nodes inside `w:txbxContent`, excluded from the candidate main-story walk. On X019, all 263 enumerated COM paragraphs reported `Range.StoryType=1`; no text-frame (`StoryType=5`) paragraph appeared. The X025 follow-up StoryType probe disconnected during WPS shutdown, so textbox inclusion is not generalized beyond X019. Textbox content is not used to repair any ordinal mismatch.
- **Empty paragraphs:** The OOXML walk did not drop empty `w:p`. COM returns empty ranges too, including additional ranges in tables. Text equality was only a fingerprint and never used to choose an ordinal.
- **Formula/image/OLE:** Every such object remains nested in its containing OOXML paragraph. Paragraphs containing OMML occur in X006 (105), X012 (553), and X013 (107); image-bearing paragraphs occur in all samples (X003 114, X004 334, X006 78, X012 23, X013 33, X019 30, X021 119, X025 119); OLE-bearing paragraphs occur in X003 (52), X004 (263), X012 (6), X013 (8), X019 (4), and X025 (50). Since table ordinals already diverge, these features cannot establish a global COM ordinal through text fingerprints.
- **Sections:** X003's final COM paragraph covers the terminal section range as above. No fixed offset was applied around section boundaries.
- **Nested tables:** Recursive OOXML traversal is defined and supported by the enumerator. The eight selected files did not require a demonstrated nested-table-to-COM reconciliation, so nested-table projection remains unproven.
- **V0.9 real source examples:** The archived package and manifest are present, but the package contains its 1v1 template and no previously validated 1v1/class source DOCX files. The Stage3 source documents were used; no unverified historical output was substituted as V0.9 evidence.

## StructDoc endpoint mapping assessment

`Block.pno` counts direct body `w:p` only. Table cell paragraphs have `pno=None`; `NodeIndex.order` is a content-node order that does not include the COM-only in-table entries. A structural parallel walk could map a StructDoc identity to an OOXML element, but the current evidence does not supply a proven mapping from that OOXML element to the corresponding COM ordinal inside the table. The fact that cell row/column is available is insufficient by itself: the extra COM paragraph(s) in each table need an exact, stable structural identity and boundary rule, including empty paragraphs and nested tables.

Because Stage3 span endpoints include cell-node IDs, the unresolved mismatch affects possible Renderer boundaries. Do not proceed to Adapter implementation on this evidence. The projection layer must remain blocked until a deterministic, non-text-based structural mapping is demonstrated against the actual V0.9 provider without changing `_fill_com.ps1` or `_fill_class.ps1`.

## Machine gate

`RENDERER_CORE_CHANGE_REQUIRED` — direct OOXML `w:p` ordinal is not the V0.9 COM ordinal: 8/8 sample count mismatches, +183 COM table paragraphs overall, and no validated endpoint projection. Chief review is required before recording the final round verdict.

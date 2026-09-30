# B4 Real XML Render UAT

## Result

**`B4_XML_PACKAGE_GATE_PASS — REAL_COM_UAT_PENDING`**

Round 17 added a selection-scope preflight for bookmark pairs and internal hyperlink anchors. The renderer was invoked for all three verified real sources against both current B-Line DOCX templates. All six attempts imported every StructDoc block and produced package-valid DOCX files. For X006 only, the `_GoBack` bookmark starts in selected block `b855`, while its matching end is a standalone direct `w:body` child excluded from StructDoc. The preflight permits this structural case only when the omitted counterpart is itself a direct body bookmark marker, IDs/names resolve uniquely, and no selected hyperlink depends on the bookmark. BlockImporter explicitly drops the orphaned imported marker; the resource report records `standalone_body_bookmark_markers_dropped=1`. This does not apply to an end inside another paragraph or table. The six generated packages have not been opened in Word/WPS, so B4 is not complete.

## Inputs and reproduction

- B-Line tested working tree: based on `9c29c1363cd5b9b13bab33643ec87d8d050f4dc1` on `feature/v1.2-renderer-baseline`.
- Stage3 manifest: `C:\xml-uat\stage3-expansion\baseline_inputs.json` (baseline commit `ceaaf8b424738245fa9f6762cdb27bfd022d0905`).
- Template target for each call: physical direct child index `0` in template `w:body`.
- The helper resolves every top-level StructDoc block to a singleton `bN` span, preserving each table as an atomic block.
- The helper verifies each source SHA-256, creates a fresh unique run folder, records input package checks and renderer outcomes in `run_manifest.json`, and does not overwrite prior runs.

Run from the repository root:

```powershell
& 'C:\xml-uat\.venv\Scripts\python.exe' tools\b4_real_render_uat.py
```

Round 17 machine run: `C:\xml-uat\b4-real-renders\run-20260930T111921Z-e7bd776b\run_manifest.json`. Earlier Round 16 attempts used their own unique directories and created no DOCX outputs.

Templates:

| Type | File | SHA-256 |
|---|---|---|
| 1v1 | `v1.1-stable/res/app/2025+1v1讲义模板(2).docx` | `1318fceabaa957b12e371310902fd81a0db08be09cee2121f6cd2606d8fd6a1a` |
| Class | `v1.1-stable/res/app/2025班课模板.docx` | `f51046d841699645b1b49f49f481c559e8502b98589d20b0c7e97cf2f7ba8f13` |

## Real-source results

All three source hashes match `baseline_inputs.json`. Source package validation passed for every sample with zero errors and zero warnings. Every renderer output passed package validation.

| Sample | SHA-256 | StructDoc top-level blocks (paragraph / table / unknown) | Source capabilities | Input package parts / validation | First guarded node | 1v1 and class result |
|---|---|---:|---|---|---|---|
| X006 physics | `9395c5bddf78dff2edd087a30212ad40b40e17a3e5c14b224b2043ade3a60410` | 860 (856 / 4 / 0) | 78 image paragraphs; 105 OMML paragraphs; 0 OLE; 0 numbered | 99 parts; PASS, 0 errors | `_GoBack` ID `0`: start in `b855`, end as standalone direct `w:body` child 859; no internal anchors | Both templates: 860 nodes imported; package validation PASS; one marker dropped and recorded |
| X012 mathematics | `c9b31fe98b0ede8b0cefc5c3a11d8deab62c85c8a1181a54db25c7ca368b57a1` | 793 (784 / 9 / 0) | 17 image paragraphs; 553 OMML paragraphs; 6 OLE paragraphs; 8 numbered | 58 parts; PASS, 0 errors | `b792`: balanced start/end pair | Both templates: 793 nodes imported; package validation PASS |
| X021 chemistry | `e10818f40e99da4234051b1beeac852f4e8090475cdb96283fbf1bcb5b44a6f4` | 333 (321 / 12 / 0) | 119 image paragraphs; 0 OMML; 0 OLE; 48 numbered | 189 parts; PASS, 0 errors | `b0`: balanced start/end pair | Both templates: 333 nodes imported; package validation PASS |

The X006 pair is named `_GoBack`; its end is not within `sectPr`. It is a standalone direct body child between paragraphs and is omitted from StructDoc content blocks. This exact structural shape can be safely dropped when there is one unique counterpart and no selected anchor reference. The renderer verifies the importer dropped exactly the number of markers authorized by preflight and exposes `standalone_body_bookmark_markers_dropped` in the resource report. Other partial pairs and unresolved or ambiguous references still fail before output replacement.

## Word/WPS evidence

**`REAL_COM_UAT_PENDING`**. The Codex Computer Use inventory returned `apps=[]`, and native-app controls are unavailable in this environment. A read-only process check observed background WPS processes, but none was controlled or tied to a B4 output; no `WINWORD.exe` process was observed. No document was opened in an application, so the active Word.Application provider could not be identified for this run. The six generated packages were not opened, saved, reopened, or exported to PDF; none of those steps is marked PASS.

## Gate boundary

- Round 17 renderer calls: 6 attempted; all 6 XML/package-supported and package-validated.
- Source DOCX package checks: 3 passed.
- Output DOCX package checks: 6 passed.
- Real Word/WPS UAT: pending and unavailable here.
- Round 17 focused suites: **35 passed, 7 subtests passed** (renderer, importer, and package validator).
- A-Line protected Stage3 regression used `C:\xml-uat\stage3-e2-after-round7` predictions: QG **408/408**, `MISS=0, FP=0, MERGE=0, SPLIT=0`; sections **369/369** exact; subquestions **328/328** inside parents; E1-E4 all zero. Stage2 focused tests: **39/39 passed**. No A-Line or Stage3 code/data changed.
- An earlier diagnostic GoldCompare call used the tool's default frozen prediction directory (207 predictions) and is not the protected regression result. The reported Stage3 gate above uses the approved post-Round-7 A-Line predictions explicitly.
- No A-Line, V0.9, Gold, Stage3, UI, or fallback code was changed.

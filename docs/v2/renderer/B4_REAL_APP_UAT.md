# B4 Real WPS Application UAT

## Result

**`REAL_APP_UAT_PASS` for the six Round 17 XML-rendered DOCX outputs in WPS Office.** This is WPS evidence, not a claim of Microsoft Word testing. No repair prompt or COM error was recorded.

The UAT used `KWps.Application` on the installed WPS Office 12.1.0.28505 server (`wps.exe /prometheus /wps /Automation`). The compatibility object reported `Microsoft Word` 12.0; provider identity is based on the ProgID and registered server, not those compatibility fields. The separate `Word.Application` route had previously resolved to WPS but failed PDF export with `0x800706BE`; direct `KWps.Application` completed this run.

## Reproduction and evidence

- XML-rendered inputs: `C:\xml-uat\b4-real-renders\run-20260930T111921Z-e7bd776b\`
- UAT outputs and machine reports: `C:\xml-uat\b4-final-uat\run-20260930T125200Z\`
- Primary evidence: `uat_report.json`
- Independent post-save package/PDF checks: `post_wps_validation.json`
- UAT started at `2026-09-30T12:52:21Z`; post-save validation completed at `2026-09-30T13:00:55Z`.

For each original output, the visible WPS automation performed **open → SaveAs to a new DOCX → close → reopen saved DOCX → export PDF**. Every action passed for all six documents. Each saved DOCX passed ZIP/package validation and was non-empty. Every PDF was non-empty, parsed with `pypdf`, and had extractable text on every page. Reopened paragraph/table/OMath/shape/text counts matched counts captured on initial open. No source DOCX was modified.

| Sample | Template | Open / SaveAs / reopen / PDF | WPS content counts (paragraphs / tables / OMaths / inline shapes / shapes) | PDF pages with text |
|---|---|---|---:|---:|
| X006 physics | 1v1 | PASS / PASS / PASS / PASS | 975 / 5 / 127 / 86 / 1 | 50 / 50 |
| X006 physics | class | PASS / PASS / PASS / PASS | 984 / 5 / 127 / 86 / 1 | 61 / 61 |
| X012 mathematics | 1v1 | PASS / PASS / PASS / PASS | 987 / 10 / 786 / 31 / 2 | 34 / 34 |
| X012 mathematics | class | PASS / PASS / PASS / PASS | 996 / 10 / 786 / 31 / 2 | 40 / 40 |
| X021 chemistry | 1v1 | PASS / PASS / PASS / PASS | 581 / 13 / 0 / 218 / 8 | 24 / 24 |
| X021 chemistry | class | PASS / PASS / PASS / PASS | 590 / 13 / 0 / 218 / 8 | 28 / 28 |

## Content preservation checks

- **X006 physics:** both outputs opened without a repair prompt. The saved/reopened files retained 127 OMaths, five tables, 86 inline shapes, and one shape each. The selected `_GoBack` marker was absent from the WPS bookmark collection after import/save; this is consistent with the explicitly recorded standalone marker drop in the Round 17 package report and caused no repair prompt. Sampled PDF pages showed the physics content, formulas, images, and tables.
- **X012 mathematics:** both outputs retained 786 OMaths, ten tables, 31 inline shapes, and two shapes across reopen. The package reports show nine OLE objects before and after SaveAs; hashes of all nine embedded payloads match exactly. Sampled PDF pages showed formulas, OLE-backed content, and tables.
- **X021 chemistry:** both outputs retained 218 inline shapes, eight shapes, 13 tables, and the source numbering payloads through package validation. Sampled PDF pages showed chemistry images and tables.

PDF inspection sampled page 2 from all six PDFs plus content pages covering X006 physics, X012 formulas/OLE, and X021 chemistry. No obvious content loss or layout break was observed in those pages. This is a targeted visual check, not a page-by-page visual review.

## Scope

This closes the real-application UAT for the six Round 17 XML outputs only. It does not prove whole-job fallback routing, Microsoft Word behavior, or B-Line completion. Whole-job V0.9 fallback remains a separate gate. No V0.9 source, A-Line code/data, XML renderer code, or production COM path was changed for this UAT.

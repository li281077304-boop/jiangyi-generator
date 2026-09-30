# B4 Real XML Render UAT

## Result

**`FALLBACK_REQUIRED` — `REAL_COM_UAT_PENDING`**

The current renderer was invoked for all three verified real sources against both current B-Line DOCX templates. Every attempt failed closed on a selected source bookmark before saving a DOCX. No source blocks were skipped and no output package is claimed as validated. The rejected cases were not sent to Word/WPS.

## Inputs and reproduction

- B-Line code base: `aeccaa9db057e0cb2827fc67570da48c33d80be8` on `feature/v1.2-renderer-baseline`.
- Stage3 manifest: `C:\xml-uat\stage3-expansion\baseline_inputs.json` (baseline commit `ceaaf8b424738245fa9f6762cdb27bfd022d0905`).
- Template target for each call: physical direct child index `0` in template `w:body`.
- The helper resolves every top-level StructDoc block to a singleton `bN` span, preserving each table as an atomic block.
- The helper verifies each source SHA-256, creates a fresh unique run folder, records input package checks and renderer outcomes in `run_manifest.json`, and does not overwrite prior runs.

Run from the repository root:

```powershell
& 'C:\xml-uat\.venv\Scripts\python.exe' tools\b4_real_render_uat.py
```

Latest machine run: `C:\xml-uat\b4-real-renders\run-20260930T110420Z-e6ef2f77\run_manifest.json`. Earlier attempts used their own unique directories; they created no DOCX outputs.

Templates:

| Type | File | SHA-256 |
|---|---|---|
| 1v1 | `v1.1-stable/res/app/2025+1v1讲义模板(2).docx` | `1318fceabaa957b12e371310902fd81a0db08be09cee2121f6cd2606d8fd6a1a` |
| Class | `v1.1-stable/res/app/2025班课模板.docx` | `f51046d841699645b1b49f49f481c559e8502b98589d20b0c7e97cf2f7ba8f13` |

## Real-source results

All three source hashes match `baseline_inputs.json`. Source package validation passed for every sample with zero errors and zero warnings. The package validator was not run on renderer outputs because no output DOCX was saved.

| Sample | SHA-256 | StructDoc top-level blocks (paragraph / table / unknown) | Source capabilities | Input package parts / validation | First guarded node | 1v1 and class result |
|---|---|---:|---|---|---|---|
| X006 physics | `9395c5bddf78dff2edd087a30212ad40b40e17a3e5c14b224b2043ade3a60410` | 860 (856 / 4 / 0) | 78 image paragraphs; 105 OMML paragraphs; 0 OLE; 0 numbered | 99 parts; PASS, 0 errors | `b855`: `bookmarkStart` | `FALLBACK_REQUIRED`; no output |
| X012 mathematics | `c9b31fe98b0ede8b0cefc5c3a11d8deab62c85c8a1181a54db25c7ca368b57a1` | 793 (784 / 9 / 0) | 17 image paragraphs; 553 OMML paragraphs; 6 OLE paragraphs; 8 numbered | 58 parts; PASS, 0 errors | `b792`: `bookmarkStart` and `bookmarkEnd` | `FALLBACK_REQUIRED`; no output |
| X021 chemistry | `e10818f40e99da4234051b1beeac852f4e8090475cdb96283fbf1bcb5b44a6f4` | 333 (321 / 12 / 0) | 119 image paragraphs; 0 OMML; 0 OLE; 48 numbered | 189 parts; PASS, 0 errors | `b0`: `bookmarkStart` and `bookmarkEnd` | `FALLBACK_REQUIRED`; no output |

The exact renderer rejection for each of the six attempts was:

`unsupported package-scoped construct: bookmarkStart`

The selected node has no text-based replacement or omission path. Output package validation and open/save/reopen checks therefore remain unrun for all six cases.

## Word/WPS evidence

**`REAL_COM_UAT_PENDING`**. The Codex Computer Use inventory returned `apps=[]`, and native-app controls are unavailable in this environment. A read-only process check observed background WPS processes, but none was controlled or tied to a B4 output; no `WINWORD.exe` process was observed. No document was opened in an application, so the active Word.Application provider could not be identified for this run. No output was available to open, SaveAs, close/reopen, or export to PDF; none of those steps is marked PASS.

## Gate boundary

- Renderer calls: 6 attempted; 0 XML/package-supported; 6 `FALLBACK_REQUIRED`.
- Source DOCX package checks: 3 passed.
- Output DOCX package checks: 0 run because output files were not created.
- Real Word/WPS UAT: pending and unavailable here.
- Focused machine suites after tightening harness error handling: **33 passed, 7 subtests passed** (renderer, importer, and package validator); helper `py_compile` and `git diff --check` passed.
- No A-Line, V0.9, Gold, Stage3, UI, or fallback code was changed.

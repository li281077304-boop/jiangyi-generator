# B3 Package and Resource Integrity Gate

## Source and adaptation

- Approved source ref: `origin/feature/jiangyi-v1.2-xml-spike` at `e511790a0a9fa7a251c2be3aed3693d2e5f86eb6`.
- The source ref was verified without checkout/merge. The extracted importer, validator, their focused test modules, MIT license, and third-party notice were each hash-checked against that exact commit before porting.
- `block_importer.py` and `package_validator.py` were copied as isolated modules into `v1.2-xml-experiment/res/app`. Their focused fixture tests were copied beside them. The MIT attribution and license text remain at the paths cited by the importer.
- The old `xml_engine.build()` orchestration was not reused.

## Renderer integration

The existing structural walk resolves selected current StructDoc IDs to source body `w:p`/`w:tbl` elements. Those elements are passed to `BlockImporter(source_document, destination_document)`; the selected node boundary and explicit template child index remain controlled by the current renderer. The importer deep-copies selected elements and remaps supported relationships, recursively copies reachable package parts, migrates referenced styles and numbering, and remaps supported document-local IDs.

The renderer stops before output replacement if the importer reports any unsupported item. It saves the destination template to a temporary DOCX, runs `validate_package` on that saved package, and atomically replaces the requested destination only if validation returns `valid: true`. The result exposes importer statistics and package validation statistics. Source bytes are read once and supplied to both StructDoc and python-docx parsing.

## Fixture capability evidence

| Capability | Evidence in this round | Scope |
|---|---|---|
| Internal image relationship and media part | Renderer integration test; output media bytes match source; package validator passes | Fixture verified; no Word/WPS visual claim |
| External hyperlink relationship | Renderer integration test; destination relationship resolves to original URI; package validator passes | Fixture verified |
| OLE embedding dependency | Renderer integration test copies dummy binary byte-for-byte; package validator passes | Package integrity only; dummy is not a real OLE/MathType object |
| Styles and numbering | Adapted BlockImporter fixture tests exercise dependency copy and ID collision remapping | Fixture verified; no template-wide style fidelity claim |
| Recursive relationships, VML image references, drawing IDs | Adapted BlockImporter tests | Fixture verified |
| Package references | Validator checks ZIP CRC, required parts, relationship owners/targets and references, style/numbering references, image/OLE relationship kinds/targets, and duplicate drawing IDs | Focused reference validator, not ECMA-376 schema validation |
| Unsupported relationship | Renderer fixture uses a missing `rId`; importer reports it and no output is committed | Fail closed |

## Machine gate

- Renderer integration suite: **18 passed**.
- Adapted BlockImporter suite: **9 passed**.
- Package validator suite: **6 passed**.
- `py_compile` and `git diff --check`: passed.
- Real Word/WPS open, save, reopen, repair-prompt, image/formula/OLE visual checks were not run and are not claimed.

## Remaining limits

- Relationship/content migration is limited to behavior exercised by the copied fixtures and importer report. Any reported unsupported structure rejects the render.
- The validator does not fully validate content-type declarations or ECMA-376 conformance and cannot establish application visual behavior.
- The renderer preflight allows selected bookmark ranges only when their IDs/names are unique and the pair is selected in full. A counterpart may be omitted only when it is itself a standalone direct `w:body` bookmark marker, has no selected hyperlink dependency, and the importer reports the corresponding orphan marker drop; this count is also exposed as `standalone_body_bookmark_markers_dropped`. Partial paragraph/table ranges, unresolved anchors, duplicate IDs/names, comments/notes, custom XML/content controls, tracked changes, and revision constructs remain fail-closed.
- No whole-job fallback, real source corpus UAT, COM Adapter, UI, or release behavior is part of this gate.

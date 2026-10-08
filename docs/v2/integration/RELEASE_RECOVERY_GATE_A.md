# V1.2 Release Recovery — Gate A Original V0.9 Stability Control

Status: **ORIGINAL_V09_PAIR_CONTROL_COMPLETE; WPS VISUAL REVIEW PENDING**  
Run date: 2026-10-08 (Asia/Shanghai)  
Product repository HEAD at run start: `a7c37d8e0c55322b3d90246aa1117eb0065c02f2`  
Evidence root: `C:\xml-uat\release-recovery-20261008`

## Engine and source integrity

- The user-confirmed package root was `C:\Users\Administrator\Desktop\工作\讲义生成器\讲义生成器V0.9\讲义生成器V0.9`.
- Every original package file matched `0922e086:known-good-v0.9/KNOWN_GOOD_V0.9_MANIFEST.json`: **2,416 / 2,416**, 56,013,394 bytes, zero missing files, size mismatches, or SHA-256 mismatches. Full record: `v09_original_manifest_audit.json`.
- Generation called `res/app/handout.py::build_version` from that original package with its bundled `res/python/python.exe` (Python 3.12.10; runtime executable SHA-256 `4D6F5F81A4BCA11191C4C7C6B43632694D0A4CE74E068619D8FDC161D469859A`). The engine file SHA-256 is `e35a45e871acbacb8f3e3c8da297c141e9bcf6e083fa1136171480dced92ce6d`, matching the frozen V0.9 source manifest.
- Copied frozen V0.9 assets were rechecked after the asset restoration: **10 / 10** match the baseline Git blobs (`tools/verify_v09_fallback_assets.py`).
- Input sources were the immutable X005/X006 incident pair and X015/X016 X12.4 pair. Their SHA-256 values match the frozen evaluation manifest; source files were not modified.
- Outputs and all run evidence are outside the repository and outside user result directories. No output was reused as input.

## Paired generation results

| Source topic | Template | Teacher pages / SHA-256 | Student pages / SHA-256 | Pair elapsed |
|---|---|---|---|---:|
| Incident physics X005/X006 | 1v1 | 50 / `36e0e3acdc35e25d951b0a8cc7c628acfcb8f6e0a6f4624f482abf34316690aa` | 25 / `feed5e6a1afcfe74e25fce44e1b9eed7ef6d3aac91e28ad0ab24058f1bdd0084` | 34.40 s |
| Incident physics X005/X006 | class | 62 / `096d18790d489f1926f20e8186c460d6b308bc92f6bfa9a56e80589f8444ee96` | 29 / `d87b5f85614e537f3efcb5caf6e62754d03b35fcb3a99bc005847a1c723c51b4` | 25.49 s |
| Math X12.4 X015/X016 | 1v1 | 53 / `160802e13160b8834ad7d8bfb76e36004bac72ee444850ef4a3c5cffcc4a5218` | 23 / `094d350b729888d9de11c02d2a95222cefa2466e0b99cb59bf3b850f2b2bd522` | 40.79 s |
| Math X12.4 X015/X016 | class | 74 / `e07346757c62df3c3e66ab02fc94115b7c5c428337efef3a7c0e0dd2996a83c3` | 29 / `ea8c446d7c5160b05be103bc34a333b3cc0aa8d2a0c596182dc38f1a96355985` | 45.21 s |

All eight output DOCX packages passed ZIP CRC and `word/document.xml` parsing. All referenced image relationships resolve. Evidence includes each pair's input/output SHA, source block ranges, metadata, output byte size and engine/template identity in each `v09_original/<topic>/<template>/pair_evidence.json`; per-role raw PowerShell build output is in the corresponding `*_build_version.log`. Console logs are retained for incident class and both X12.4 runs.

## Content and structure comparison

`gate_a_original_v09_structural_report.json` and `gate_a_referenced_media_report.json` contain the per-file measurements.

- Every nonempty source body paragraph was found in the output in the same order for all eight files: **100% ordered exact paragraph match**.
- Every referenced source image byte hash was present in the output: incident teacher **81/81**, student **62/62**; X12.4 teacher **39/39**, student **37/37**. There are no unresolved image relationships. Extra image parts/references come from the original templates.
- Tables were retained alongside the template table: incident teacher/student **4 → 5**; X12.4 teacher **29 → 30**, student **28 → 29**.
- The section sequence occurs once per output. The original V0.9 1v1 template labels section 3 `知识精讲&例题讲解` and section 6 `巩固练习`; class uses `知识精讲&例题讲解` and `出门测试`. No `学科教师辅导讲义` recursive template title was found in output body text. The legacy 1v1 section-3 title is a known difference from the V1.2 product wording and needs the stable-mode normalization layer.
- OMML node counts are unchanged on the 1v1 template: incident teacher/student **127/2 → 127/2**; X12.4 teacher/student **1,549/370 → 1,549/370**. The original class `.doc` route converts equations away from OMML in the output package (OMML **127/2 → 0/0** for incident; **1,549/370 → 0/0** for X12.4). Word COM logs inline-shape totals of **213/69** and **1,592/411** respectively. These class outputs require WPS visual confirmation that equations remain readable; the OOXML count is not treated as proof of visual correctness.
- Answer/solution-term counts were preserved from each selected source. Incident teacher: **138 → 138**, student: **0 → 0**. X12.4 teacher: **250 → 250**, student: **16 → 16**. The 16 X12.4 student-source term hits pre-exist in the frozen original-paper source and are not introduced by the engine; their semantic meaning still needs content review.

## Decision boundary

The original V0.9 pair control demonstrates that the frozen engine generates both templates from these real immutable paired inputs without losing or reordering visible source paragraph text, and preserves every referenced source image. This is a structural baseline result, not a WPS/visual pass. It does not establish that V1.2 stable mode is behaviorally equivalent, that teacher-only generated student copies are safe, or that class-template equations are visually correct.

Next: run the same inputs through V1.2 stable mode and compare final content/normalization against these baseline artifacts; then review representative final files in WPS. Do not use these generated V0.9 outputs as later test inputs.

## V1.2 HTTP stable-engine handoff comparison

Status: **HTTP PRODUCT PATHS COMPLETED; WPS VISUAL REVIEW PENDING**. These submissions exercised the V1.2 workbench HTTP API with the explicitly selected `stable_v09` engine. They are not XML-route coverage and are not EXE UAT.

Durable repository evidence index: `docs/v2/integration/fixtures/release-recovery-20261008/gate_a_http_evidence_index.json`. Raw HTTP terminal snapshots, input/output DOCX, and per-file comparison JSON remain under `C:\xml-uat\release-recovery-20261008`; the evidence index binds final output paths, byte lengths and SHA-256 without adding user documents to Git.

| HTTP case | Job | Result / engine | Time | Product result |
|---|---|---|---:|---|
| X12.4 pair, 1v1 | `12c76457c42f46e7b317dee2c1658716` | done / `STABLE_V09` | 51.276 s | Teacher and student files produced |
| X12.4 pair, class | `d6581397b2444abd824227e8d8366db1` | done / `STABLE_V09` | 62.391 s | Teacher and student files produced |
| X008 teacher-only | `8dfc97faa08b4c06af30b5352d0cd050` | done / `STABLE_V09` | 30.725 s | Teacher plus generated student; `V09_MAKE_STUDENT` took 8.982 s |
| X015 student-only | `1d53c4bf5cbe4d99ad94cd03466bc35b` | done / `STABLE_V09` | 16.791 s | Student file produced |
| Chinese nested-directory ZIP (first observed submission) | `845916fce28f419a90915e00a19bb38e` | partial / `STABLE_V09` | 57.383 s | 2 valid topic items done; deliberately corrupt third DOCX isolated as item error |
| Chinese nested-directory ZIP (repeat submission) | `4c22848bf6ff47119d7cd916c6b316d8` | partial / `STABLE_V09` | 51.479 s | Same expected 2 done + 1 corrupt item error |

The ZIP inputs contain the incident X005/X006 physics pair, the S04T/S04S specific-heat pair and a deliberately corrupt DOCX. Both submissions kept the valid items, rejected the corrupt item with `无效或损坏的 DOCX`, and package validation passed for all four produced DOCX files. No ZIP output delivery was involved.

### Text, table, image and equation comparison

`C:\xml-uat\release-recovery-20261008\gate_a_stable_mode_structural_report.json` compares source and HTTP outputs; `gate_a_stable_media_report.json` checks exact referenced-image payload hashes and relationship resolution.

- X12.4 pair: source paragraphs are an exact ordered subsequence in all four outputs: teacher **1,315/1,315** and student **501/501** under both templates. Both templates add one template table (teacher **29 → 30**, student **28 → 29**). All source image payloads match exactly (**39/39** teacher, **37/37** student) with no unresolved image relationships. The 1v1 package retains source OMML (`1,591` teacher and `401` student); the legacy class `.doc` path serializes OMML as inline shapes (`0` OMML nodes), so visual equation readability remains a WPS check.
- Incident physics class ZIP item: original title paragraph is replaced by the normalized product title; every other source paragraph remains in order (teacher **851/852**, student **319/320**). All source image payloads match exactly (**81/81** teacher, **62/62** student), with no unresolved relationships. The source has **4** tables and each output has **5** including the template table. The `.doc` conversion emits zero OMML nodes; WPS visual inspection remains required.
- S04 teacher/student outputs have valid package validation, including the large OLE/image resources. Their output hashes and validation records are in the raw terminal snapshots and evidence index.
- X008's exact source SHA matches the previously approved content review: **29 frozen QGs / 34 manually reviewed physical questions**. This HTTP run used V0.9 `make_student`, not the approved-but-nonproduction XML Studentizer. The UI/job carries the warning “自动生成的学生版可能仍含有答案或解析，请在使用前检查。” This run does not establish exact answer-removal accuracy, and its COM observation is unknown.
- X015's 16 answer/analysis keyword hits are pre-existing legitimate `函数解析式`/prompt text, including “根据以上信息，解答下列问题”; no answer-label marker was found. Its student-only output preserves all **501/501** nonempty source paragraphs in order. Do not count these keyword hits as newly leaked answers.

The HTTP job outputs report the actual selected engine and renderer as `V0.9` / `STABLE_V09`; no XML coverage is claimed. The teacher-only job explicitly surfaces the student-review warning and leaves missing objectives/difficulties blank with a separate warning. Next gate is actual packaged-EXE use followed by WPS Open → SaveAs → Close → Reopen → PDF and visual review; this Gate A comparison did not launch WPS or COM automation.

# V1.2 Final Closeout — recovered incident pair UAT

Date: 2026-10-06 (Asia/Shanghai)
Branch: `feature/v1.2-c4-release-engineering`
Base commit: `4ccc8643203e97dd8b1b2e5c61378963744cb415`
Status: `V1_2_FINAL_CLOSEOUT_BLOCKED`

## Result first

| Product check | Result |
|---|---|
| Two DOCX direct upload | Both templates generated teacher/student output; both used V0.9 whole-job fallback after `TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH`. |
| Same pair as ZIP input | Both templates generated teacher/student output; both used the same V0.9 fallback reason. |
| Modules 1 and 2 fully populated on page 1 | **FAIL.** Their headings and reserved areas are present, but their content areas are empty in the fallback output. |
| Module 2 end divider at page-one safe target | PASS by WPS PDF measurement: 1v1 `760.16pt` vs `760.30pt` target; class `740.12pt` vs `740.10pt` target. |
| Module 3 begins on page 2 | PASS for both templates and both roles in the inspected representative outputs. |
| Display renumbering | NOT APPLIED because both real paired-source routes fell back. No renumbering pass is claimed. |
| Teacher/student display numbering matches | NOT VERIFIED; fallback records `DISPLAY_RENUMBER_NOT_APPLIED_FALLBACK`/`NOT_APPLICABLE`. |
| Objectives/difficulties | No reliable source fields exist in this recovered exam pair. Both remain blank with the explicit user warning; this pair cannot prove metadata retention for sources that do contain those fields. |
| XML normal path | **FAIL.** All four browser submissions routed to V0.9. |
| PowerShell console | No console window was observed during the hidden-server browser UAT or WPS automation. The packaged EXE gate was not rerun, so this is not an EXE-level PASS. |

These results do not meet the Final Closeout acceptance criteria. No EXE was built, no release ZIP or tag was created, and C5 was not started.

## Original source recovery

The pair was recovered by recursively scanning the training corpus and nested ZIP members. The committed recovery manifest records 254 ZIP archives and 988 members scanned, 2,948,814,507 extracted bytes, and zero path-traversal entries written. Two members with a `.zip` extension were malformed and were recorded as rejected. No file under `生成讲义结果`, publication output, or runtime output was used as source.

Source chain:

```text
C:\Users\Administrator\Desktop\工作\讲义生成器\训练文件\【上好课】2025-2026学年九年级物理上学期期末考点大串讲（新教材，人教版）-3.zip
  → 期末模拟卷/期末复习（易错精选60题27大考点）九年级物理上学期新教材人教版.zip
  → 九年级上学期物理期末复习（易错精选60题27大考点）（原卷版）.docx
  → 九年级上学期物理期末复习（易错精选60题27大考点）（解析版）.docx
```

The immutable pair is checked in at `docs/v2/integration/fixtures/incident-72cab43961d6488c91b7a9e049265263/` for future regression runs.

| File | Role | SHA-256 | Source evidence |
|---|---|---|---|
| `九年级上学期物理期末复习（易错精选60题27大考点）（原卷版）.docx` | student / original paper | `c66f88d26f1fae9306442ef8e1f55a807d3e705edaa37e57334d4499d3c6a009` | 401 paragraphs, 77 question-start markers, 4 tables, 62 images, 2 OMML formulas; no answer tags. |
| `九年级上学期物理期末复习（易错精选60题27大考点）（解析版）.docx` | teacher / answer-rich | `9395c5bddf78dff2edd087a30212ad40b40e17a3e5c14b224b2043ade3a60410` | 905 paragraphs, 78 question-start markers, 27 exam-point headings, 4 tables, 81 images, 127 OMML formulas, 49 answer tags. |

Both files contain the exact topic title and the “易错精选60题27大考点” content. The four source tables have dimensions 4×4, 3×5, 2×4, and 5×2. The accident table is the 4×4 voltage measurement table; its `1.9`, `1.0`, and `2.9` values are data, not standalone question boundaries.

## Real browser submissions

The source app was opened in a real browser against an isolated local result/runtime root. Form values were `物理 / 九年级 / 2025-2026学年 / 期末复习`; each template received the exact same source hashes. The ZIP contained only the two recovered DOCX files.

| Input route | Template | Job / item | Status | Renderer | Fallback | Pair classification |
|---|---|---|---|---|---|---|
| Direct two DOCX | 1v1 | `8e1eb590b5974268a1ed6e09c34dc253` | done | V0.9 | `TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH` at Router | paired filenames; correct teacher/student SHA |
| Direct two DOCX | class | `824b5c4c83e0424bab0eb2ac84f3d8bd` | done | V0.9 | `TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH` at Router | paired filenames; correct teacher/student SHA |
| ZIP input | 1v1 | parent `9f44d07abdbd4d16942185c4bfebfdd5`, item `45c859f390ea4752bcee130b2c12f489` | done | V0.9 | `TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH` at Router | ZIP member provenance and hashes match the direct pair |
| ZIP input | class | parent `94c5593bbec644b1aba90a48ab92799e`, item `a2b2a76b17b14d118ceea514b0d72df5` | done | V0.9 | `TEACHER_STUDENT_TRAINING_ROUTE_MISMATCH` at Router | ZIP member provenance and hashes match the direct pair |

All four item records have `input_version=TEACHER_AND_STUDENT`, correct teacher/student source roles, two final output paths, accepted `PRODUCT_INTEGRITY_GATE`, and `package_validation.valid=true` for both output DOCX files. The recorded `lesson_metadata.status` is `UNAVAILABLE`, with `NO_RELIABLE_OBJECTIVES_SOURCE` and `NO_RELIABLE_DIFFICULTIES_SOURCE`; the warning is shown in the job record.

## First divergence and fallback boundary

The independent route-signature comparison bound to the recovered source hashes produced 59 student question routes and 60 teacher routes. Comparing the first 59 route positions gives 39 slot differences; the first is question 2 (`student=immediate`, `teacher=knowledge`). This is not an OOXML-to-COM issue. The production job fails closed at the teacher/student route-consistency gate and uses the whole-job V0.9 path. Do not bypass this gate or declare XML successful until both source roles share a proven occurrence map.

In the resulting 1v1 and class DOCX packages, all four original source tables remain present alongside the template carrier table. The voltage strings `1.9`, `1.0`, and `2.9` remain in the teacher and student content. Teacher outputs retain 49 `【答案】` markers; student outputs contain zero. WPS before/after SaveAs counts are unchanged. These structural checks do not establish that the first two modules contain routed teaching content; visual inspection shows that they do not.

## WPS Open / SaveAs / Reopen / PDF

The `KWps.Application` ProgID resolved to `D:\Program Files\WPS Office\12.1.0.28505\office6`; its compatibility properties reported `Microsoft Word` / `12.0`. The registered ProgID and executable path identify WPS Office. Each tested file completed Open → SaveAs to a new DOCX → Close → Reopen → PDF. No repair prompt or COM error occurred.

| Template / job | Role | Pages | Before → after SaveAs | Divider bottom Y / target |
|---|---|---:|---|---|
| 1v1 / forced fallback `b67fae19cce24277ad8e9c1140eadc8e` | teacher | 50 | 968 paragraphs, 1 table, 127 OMML, 86 inline images → unchanged | `760.16pt / 760.30pt` |
| 1v1 / forced fallback `b67fae19cce24277ad8e9c1140eadc8e` | student | 25 | 442 paragraphs, 1 table, 2 OMML, 67 inline images → unchanged | `760.16pt / 760.30pt` |
| class / ZIP item `a2b2a76b17b14d118ceea514b0d72df5` | teacher | 62 | 962 paragraphs, 1 COM table, 213 inline images → unchanged | `740.12pt / 740.10pt` |
| class / ZIP item `a2b2a76b17b14d118ceea514b0d72df5` | student | 29 | 436 paragraphs, 1 COM table, 69 inline images → unchanged | `740.12pt / 740.10pt` |

The PDFs show the module 2 divider at the defined safe target and the module 3 heading at the top of page 2. The first page contains the module 1 and module 2 headings and blank content areas. This is a product failure even though the divider coordinate is correct. Full-page PDFs and round-trip JSON remain in `C:\xml-uat\v12-recovered-pair-final-uat-20261006\wps-r2\` and `...\browser-gap-fill\wps-class\`.

## Machine checks and remaining blockers

- `tests/test_input_versions.py` + `v1.2-xml-experiment/res/app/test_final_polish.py`: 24 passed.
- Fixture SHA-256 values match the committed recovery manifest.
- Full Final Closeout regression was not run after this failed XML/product gate. No new Stage2/Stage3 or EXE evidence is claimed.
- The production V0.9 PowerShell helper uses both `CREATE_NO_WINDOW` and `STARTUPINFO/SW_HIDE`; no console was observed in the source-browser run. The packaged EXE was not exercised in this run.
- `git diff --check`, final commit/push identity, and independent Chief review are recorded in the Run Journal after the implementation checkpoint.

Blocking items:

1. Resolve the 59-vs-60 teacher/student route occurrence mismatch for these immutable source files without guessing or weakening fail-closed behavior; then all four browser paths must take XML or a justified, explicitly accepted product fallback policy.
2. Populate modules 1 and 2 with their intended content on page 1. A correct divider position with empty module bodies does not satisfy the acceptance criteria.
3. Prove display numbering and teacher/student numbering consistency on an XML-routed final output.
4. Re-run the final relevant regression and packaged EXE UAT only after blockers 1–3 pass; inspect for console windows during both XML and fallback execution.

No C4 Final Closeout PASS is claimed.

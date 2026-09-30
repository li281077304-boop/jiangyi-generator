# C0 Round 3 — HTTP Integration and Local Result Delivery

- Branch: `feature/v1.2-c-line-integration`
- Base: `f96f47cb189e941f411d0365f38134d417fe96cc`
- Worker: GPT-6 Luna
- Scope: connect the accepted single `main_content` plan to the existing XML-first renderer, V0.9 whole-job fallback, durable job service, and local result delivery. The frozen A-Line, B-Line renderer, and V0.9 runtime were not edited.

## Implementation

`POST /api/jobs` now persists the uploaded DOCX under a UUID-isolated result directory and schedules generation. The worker prepares a student source through the frozen V0.9 `make_student` routine, builds an A-Line-backed source-order plan for teacher and student, and asks the existing B-Line XML renderer to produce both outputs. Any unsupported plan, renderer failure, or package/resource validation failure routes the original source through the V0.9 whole-job callback with an explicit reason code; no V1.2 spans are sent to the fallback.

Teacher and student DOCX files are written to the job's stable local result directory. `JobService.complete_job` marks the record `done` only after both distinct files exist and the B-Line package validator accepts both. The record persists `result_dir`, role paths, `output_paths`, `download_available`, `renderer`, `fallback_reason`, and `baseline_sha`.

`GET /api/open/<job_id>` resolves and opens the job directory. ZIP creation is a separate delivery operation. ZIP errors persist `delivery_status=failed` and `delivery_error_code=DELIVERY_DOWNLOAD_FAILED`, set `download_available=false`, and leave valid outputs and `status=done` intact. Recovery preserves that delivery state rather than resetting it from `has_result`.

The workspace states that the handouts were generated, shows the exact local output path, and offers “打开成品文件夹” and “下载 ZIP”. When ZIP delivery has failed, the folder action remains available and the UI explains that the DOCX files are still on disk.

## Accepted template plan

C0 uses one physical `main_content` target, accepted in the independent Chief scope review. The plan preserves every A-Line unit's role, parent, binding, spans, and evidence metadata; overlapping semantic spans contribute each top-level source block once, in source order. Contentful blocks without semantic coverage fail closed; uncovered empty structural paragraphs are retained once. Table and cell endpoints project to their owning top-level table because the frozen renderer imports tables atomically.

This target is the body insertion point after the validated template's content table and before `sectPr`. C0 does not claim to populate the templates' individual `知识精讲`, `即时训练`, or practice cells. That placement limit is recorded in `C0_ROUND3_TEMPLATE_PLAN_EVIDENCE.md` and is part of the accepted C0 scope.

## Real HTTP integration UAT

The tests used Flask's HTTP client against the actual `/api/jobs`, job polling, `/api/open`, and `/api/download` routes. Results and sources are outside the repository under `C:\xml-uat`.

| Case | Outcome | Evidence |
|---|---|---|
| X012 math, 1v1, normal XML | PASS; `status=done`, `renderer=XML`, no fallback; both DOCX packages valid; local open route and ZIP both returned 200; final status remained done | `C:\xml-uat\c0-http-math-1v1-20261001`; job `3a147f342e2f4ec2a6353a2afbe11a5a` |
| X021 chemistry, class, normal XML | PASS; `status=done`, `renderer=XML`, no fallback; both DOCX packages valid; open route resolved the exact result directory; ZIP returned 200 (5,950,997 bytes) | `C:\xml-uat\c0-http-class-uAT-20261001`; job `86d185f098ec445e85fb870e4e5a50fb` |
| Forced unsupported X012, 1v1 | PASS; XML preflight failed closed; V0.9 whole-job path produced teacher and student DOCX; both package validations passed; persisted `UNSUPPORTED_REVISION_MARKUP` and baseline `0922e08631226b95a77a6599bbc0ac3784e9134b`; ZIP returned 200 | `C:\xml-uat\c0-http-v09-fallback-20261001-r3`; job `4f8854a3881d4d13a161d16b78d6a6f4` |
| ZIP packaging failure | PASS; simulated archive failure returned HTTP 503 with `DELIVERY_DOWNLOAD_FAILED`; subsequent job read remained `done`, retained both output paths and result directory, and recorded `download_available=false` | automated case `test_zip_delivery_failure_does_not_fail_validated_local_generation` |

For the X021 class XML outputs, both teacher and student completed WPS `open → SaveAs DOCX → close → reopen → PDF`. All files were nonempty. Paragraph/table/OMath/InlineShapes/Shapes counts were unchanged across the round trip:

- Teacher: 590 / 13 / 0 / 218 / 8 before and after.
- Student: 638 / 13 / 0 / 218 / 8 before and after.
- Provider evidence: `KWps.Application`, with live `wps.exe` at `D:\Program Files\WPS Office\12.1.0.28505\office6\wps.exe`. WPS reports the compatibility application name “Microsoft Word”; this report identifies the provider as WPS from its ProgID and executable.
- Full evidence: `C:\xml-uat\c0-http-class-uAT-20261001\kwps-http-roundtrip-final.json`.

## Machine gates

- Expanded C0, plan, XML renderer/orchestrator, importer, package-validator, StructDoc, NodeIndex, and Stage2 machine suite: **120 passed, 7 subtests passed in 164.16s**. Stage2-only regression: **39 passed**.
- Fresh protected Stage3 run used all eight staged source hashes successfully: QG 408/408, recall 100%; sections 369/369 exact; subquestions 328/328 in parent; MISS/FP/MERGE/SPLIT=0; error counts empty.
- GoldCompare output: `C:\xml-uat\c0-round3-stage3-after-20261001\goldcompare.md` and `.json`.
- `py_compile`, `node --check`, and `git diff --check` passed after implementation.
- V0.9 `ASSET_MANIFEST.json` identities: 10/10 SHA-256 matches; baseline commit `0922e08631226b95a77a6599bbc0ac3784e9134b` exists. `v09_fallback_runtime/**` and `renderer_orchestrator.py` have no worktree changes; GBK stdout capture is in the C0 callback only.
- Remote tag dereferences were verified: A-Line `v1.2-a-line-complete-2026-09-30` → `df3825d3a78f34537689af36136dd2588bcd73bc`; B-Line `v1.2-b-line-complete-2026-09-30` → `eae89ea8720b94d29a94fc652830de628f373cd9`.

## Final scope notes

Only one normal XML template slot is supported in C0. ZIP availability describes the server-side ZIP response operation; the validated teacher/student DOCX files in the result directory remain the durable success condition. No A-Line or B-Line behavior, student answer-removal rules, renderer internals, template files, UI platform shell, or release packaging was changed.

## Round 4 closure

The independent `Codex GPT-6.1 Sol` review found two C0 job-boundary cases in Round 3 and returned PATCH. Round 4 now publishes teacher/student plans atomically, so a student-plan rejection cannot leave a partial summary that breaks a successful V0.9 fallback. The fallback attempt's renderer, reason code, and frozen baseline SHA are persisted before entering V0.9, so a failed fallback still leaves an auditable reason.

The regression suite covers both a successful fallback after student-plan rejection and a failing fallback with its attempt metadata retained. A pre-existing upload-persistence assertion was made deterministic by comparing the exact same generated `source_bytes` used for upload. The final full repository run passed **145 tests and 7 subtests**. `Codex GPT-6.1 Sol` returned **PASS** on `f1ffba963732152ee2b65508c7e35be934d29af6`.

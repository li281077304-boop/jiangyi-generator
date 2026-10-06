# Run Journal

| Round | Start (UTC) | End (UTC) | Worker model | base_sha | head_sha | machine_gate result | chief_model | chief_verdict | next_action | commit/push |
|---:|---|---|---|---|---|---|---|---|---|---|
| 6 | 2026-09-30 04:53:27 | 2026-09-30 05:35:37 | gpt-6-luna | b94b0366f451513a233c19ca23149fd9e74be892 | 5b33e09a3b0cc4698aa936466d71e6761700c05a | PASS: Stage3 408/408; original recall 100%; E1/E2/E3/E4=0; FP/MERGE/SPLIT=0; section 369/369 | Codex GPT-6 Sol | PATCH | Fix incomplete-example boundary, allow multiple complete multipart QGs in one section, and keep example 1 from becoming a QG outside recognized modules; rerun full Stage3 and review | Yes: code commit 5b33e09 pushed; journal commit follows |
| 7 | 2026-09-30 05:35:37 | 2026-09-30 05:53:14 | gpt-6-luna | d1463c6a52a4b79a56105680651344dcf63fd662 | d4bff1bd7d3341fd24f5c1f8676c431f75eebb9a | PASS: Stage3 408/408; original recall 100%; E1/E2/E3/E4=0; FP/MERGE/SPLIT=0; section 369/369; subquestions 328/328 | Codex GPT-6 Sol | PASS | A_CORE_COMPLETE; enter MATERIAL_COVERAGE_GATE only | Yes: E2 code commit pushed; this journal entry is the following metadata commit/push |
| 8 | 2026-09-30 05:56:09 | 2026-09-30 06:11:36 | gpt-6-luna | c8420c696c50f6cec17bb20a85180a31f8abdc1b | 9120964a3f4309137f6235219d5e07a08f17d7f9 | PASS: 3 material cases; Stage2 39/39; GoldCompare 24/24; one shared material to two QGs GoldCompare 0 issues; no Gold expansion | Codex GPT-6 Sol | PASS | A_LINE_COMPLETE; stop A-Line and wait for next Roadmap stage | Yes: gate report commit 9120964; Journal metadata commit and both pushed |
| 9 | 2026-09-30 06:44:22 | 2026-09-30 06:52:26 | gpt-6-luna | df3825d3a78f34537689af36136dd2588bcd73bc | 445242fff79c0f92307f5bafa89afece5ebe0462 | PASS (source audit only): V0.9 commit/manifest verified; 8 interface items audited; no code/tests/COM; StructDoc-to-COM projection unresolved; B1 pending | Codex GPT-6 Sol | PASS | B_LINE_READY; next round prove exact projection then implement minimal adapter and run B1 | Yes: audit report commit 445242f pushed; Journal metadata commit and both pushed |
| 10 | ~2026-09-30 07:05 | 2026-09-30 07:43 | GPT-6 Luna (StructDoc audit) | b7ba4a7b21ae215c7f0988169bb42372f1de47b9 | 39e4a33288a57f76283e43120f809928673c57eb | FAIL: 8/8 Stage3 samples; OOXML main w:p 4,842 vs COM Paragraphs 5,025 (+183, all in tables); 0/2,376 endpoint occurrences validated; WPS provider; V0.9 expands table endpoints to whole tables | Codex GPT-6 Sol | FAIL — RENDERER_CORE_CHANGE_REQUIRED | Stop before Adapter; request a separately scoped decision on table-aware projection and V0.9 cell-boundary compatibility; keep A-Line frozen | Yes: B0 failure report 39e4a33 and this Journal metadata commit pushed; no Adapter/core changes |
| C4 Final RC closeout | 2026-10-02 13:02 UTC (handoff evidence review) | 2026-10-02 13:14 UTC | GPT-6 (handoff closeout; UAT evidence inherited from GPT-6 Luna) | d3511a07aeb5e981733750cc5d21db350029f229 | d3511a07aeb5e981733750cc5d21db350029f229 | Conditional: latest EXE browser/WPS/restart/package evidence consolidated; selected regressions 293 passed; full pytest 418 passed, 4 frozen V1.1 API failures, 7 subtests; Stage3 protected metrics PASS; Stage2 S01/S11 GoldCompare remain known FAIL; diff-check PASS | Codex GPT-6.1 Sol | PENDING — independent final review not yet performed | Review final report/evidence; create RC tag only after Chief PASS | Report and Run Journal closeout will be committed and pushed before Chief review; no tag yet |

Round 10 start time is approximate because the turn-start timestamp was not exposed. GPT-6 Luna inspected StructDoc/NodeIndex; the lead gathered the read-only COM evidence. Codex GPT-6 Sol independently reviewed the report and raw COM records, including an X013 spot check.
| 11 | ~2026-09-30 08:00 UTC (approx; exact start not captured) | 2026-09-30 09:42 UTC | GPT-6 Luna | 5372641b99a69d35ed9113ac0c147cf73e2511b4 | 6e906eba7e01079745e7701a64eec804ec2b6812 | PASS (audit only: 34 passed, 1 skipped; no real-document Word/WPS UAT) | Codex GPT-6 Sol | PASS — PARTIAL_REUSE (recovery decision only) | Begin B2 on corrected pushed B-Line head; port only approved importer/validator assets and implement current StructDoc extraction/orchestration | Yes: report commits 2b75d19 and 6e906eb; Journal metadata commit and push follow |

Round 11 start time is approximate because the exact turn-start timestamp was not captured. The Chief verdict applies only to recovery asset selection, not renderer behavior or real-document UAT.
| 12 | ~2026-09-30 09:40 UTC (approx; exact start not captured) | 2026-09-30 10:07 UTC | GPT-6 Luna | e68a9704dbda239bc309903b5b7b8871c087156c | d0dacc2c4bb63c14b36a83772293831a7e241588 | FAIL: renderer 9/9, StructDoc non-COM 10/10, struct_nodes 13/13, Stage2 39/39, Stage3 408/408 with zero errors; diff-check fails at EOF; legacy COM contract test stopped after >90s stall | Codex GPT-6 Sol | PATCH | Fix source single-read consistency, physical block continuity including empty tables, top-level-only table selection, tracked-change ID safety, and EOF whitespace; rerun focused gates and Chief review | Yes: renderer commit d0dacc2 pushed; this Journal commit follows |

Round 12 start time is approximate because the exact turn-start timestamp was not captured. Chief independently reran the renderer fixtures and found uncovered projection cases; real Word/WPS UAT remains out of scope.
| 13 | ~2026-09-30 10:07 UTC (approx; exact start not captured) | 2026-09-30 10:18 UTC | GPT-6 Luna | c744a9a81258241aa26868e34a3ea08afaf7f393 | c0948522b9a30cb8fe718e214d257ea79144ecc4 | PASS: renderer 13/13; StructDoc non-COM 10/10; struct_nodes 13/13; Stage2 39/39; Stage3 408/408, sections 369/369, zero E1-E4/FP/MERGE/SPLIT; py_compile and diff-check pass | Codex GPT-6 Sol | PATCH | Fail closed on all relevant OOXML revision markup including table-cell revision elements; add fixture and repeat gates | Yes: renderer fix commit c094852 pushed; this Journal commit follows |

Round 13 start time is approximate because the exact turn-start timestamp was not captured. Chief independently reproduced that w:cellIns is accepted; the renderer fixture set did not yet cover this markup. Real Word/WPS UAT remains unverified.
| 14 | ~2026-09-30 10:18 UTC (approx; exact start not captured) | 2026-09-30 10:25 UTC | GPT-6 Luna | 18ea8e649b2903a6185640d03bbe9e6bb8f3dd1a | d32e83ffd1cc0c0098d1466ea6882318b40a22b1 | PASS: renderer 15/15; StructDoc non-COM 10/10; struct_nodes 13/13; Stage2 39/39; Stage3 408/408, sections 369/369, zero E1-E4/FP/MERGE/SPLIT; py_compile and diff-check pass | Codex GPT-6 Sol | PASS | Continue with B3 package/resource integrity and validator capability gate; keep unsupported cases fail-closed; no real Word/WPS UAT claim | Yes: renderer guard commit d32e83f pushed; this Journal commit follows |

Round 14 start time is approximate because the exact turn-start timestamp was not captured. Chief independently verified the revision guard and its fixtures; the gate remains synthetic and real Word/WPS UAT is pending.
| 15 | ~2026-09-30 10:25 UTC (approx; exact start not captured) | 2026-09-30 10:43 UTC | GPT-6 Luna | 8b68381f4927b009953ac7dfe789bd63a67694cc | ae444ac6c4bee0cdeb3303beb33d6333bf8dc4a3 | PASS: renderer 18/18; importer 9/9; validator 6/6; StructDoc non-COM 10/10; struct_nodes 13/13; Stage2 39/39; Stage3 408/408 and zero E1-E4/FP/MERGE/SPLIT; six assets match e511790; py_compile/diff-check pass | Codex GPT-6 Sol | PASS (scoped B3 gate) | Begin B4 planning: validate real 1v1/class XML rendering paths and design explicit capability/fallback status; preserve the untouched V0.9 fallback boundary | Yes: resource integration commit ae444ac pushed; this Journal commit follows |

Round 15 start time is approximate because the exact turn-start timestamp was not captured. Imported assets match the approved spike blobs; fixture UAT does not establish real Word/WPS rendering.

| 16 | ~2026-09-30 10:44 UTC (approx; exact start not captured) | 2026-09-30 11:08 UTC | GPT-6 Luna | aeccaa9db057e0cb2827fc67570da48c33d80be8 | 806011125e2ba1576f1580f5618971d8e8b0dd41 | PASS: 33 focused tests + 7 subtests; helper py_compile/diff-check pass; 3/3 source packages valid; 6/6 real-source renders correctly fail closed at bookmarkStart with no output DOCX; Word/WPS UAT pending | Codex GPT-6 Sol | PASS (scoped to B4 evidence harness only; render gate remains open) | Address safe bookmark preservation or fallback classification within remaining implementation-round budget; rerun B4, then perform actual Word/WPS UAT on generated files; do not claim B-Line complete | Yes: B4 helper/report commit 8060111 pushed; this Journal metadata commit follows |

Round 16's Chief was launched with the explicit `gpt-6-sol` model override and independently verified the committed harness, source/template hashes, and latest run manifest. The PASS applies only to truthful evidence capture and fail-closed harness behavior; all six B4 real-source renders remain `FALLBACK_REQUIRED` and application UAT remains pending.

| 17 | ~2026-09-30 11:09 UTC (approx; exact start not captured) | 2026-09-30 11:30 UTC | GPT-6 Luna | 9c29c1363cd5b9b13bab33643ec87d8d050f4dc1 | 7777917eecbb26cdd1d0bbc7c6765cca34d88f44 | PASS: renderer/importer/validator 35 passed + 7 subtests; Stage2 39/39; protected Stage3 408/408 QGs, 369/369 sections, 328/328 subquestions, E1-E4/FP/MERGE/SPLIT=0; B4 6/6 real-source XML/package renders and independent package validation pass; Word/WPS UAT pending | Codex GPT-6 Sol | PASS (scoped to B4 XML projection/package gate; not B-Line completion) | SAFE_STOP_AFTER_MAX_ROUNDS; stop implementation at six rounds; B-Line remains incomplete pending real Word/WPS open/save/reopen/PDF UAT and whole-job V0.9 fallback integration | Yes: implementation commit 21a10c3 and evidence correction 7777917 pushed; this Journal metadata commit follows |

Round 17's Chief was launched with the explicit `gpt-6-sol` model override. It independently verified the selected bookmark-scope behavior, real-source hashes, package validation for all six outputs, protected Stage3 regression, and Stage2 tests. The verdict covers only XML projection/package integrity. Real Word/WPS UAT was not performed, and the B-Line completion gates remain open.

| 18 | 2026-09-30 12:52:21 UTC | 2026-09-30 13:14:06 UTC | GPT-6 Luna | 0e2b1e0d028908f5cb6c29dc7cca8ff64ada10b7 | 7fb9cee31993f8d28658de2754116411a3447910 | PASS: WPS `KWps.Application` open/SaveAs/reopen/PDF for 6/6 outputs; all saved DOCX packages and PDFs valid/readable; reopen counts match; all 9 X012 OLE payload hashes preserved | Codex GPT-6 Sol | PASS (scoped to Round 17 real-output WPS UAT; no B-Line completion claim) | Implement and gate explicit whole-job V0.9 fallback; keep XML as normal path and frozen V0.9 core untouched | Yes: UAT report commit 7fb9cee pushed; this Journal metadata commit follows |

Round 18 Chief review was launched with the explicit `gpt-6-sol` model override. The Chief independently checked all six files and the UAT JSON; WPS evidence is not represented as Microsoft Word evidence. PDF visual inspection was targeted, not page-by-page. Fallback remains unimplemented.

| 19 | 2026-09-30 13:18:24 UTC | 2026-09-30 13:57:05 UTC | GPT-6 Luna | c45b07354448c1061458c99180f29f0907e9e712 | 33d547169cfe43be95111ff0bd71a37a795e6ff6 | FAIL: real X006 V0.9 forced fallback 1v1/class teacher+student packages passed and normal XML path passed; protected Stage2/Stage3 and 10/10 app asset hashes passed; however `renderer_orchestrator.py` had literal EOF `\\n`, causing SyntaxError and preventing import/tests; published fallback JSON details were stale | Codex GPT-6 Sol | PATCH | Remove syntax artifact, refresh actual fallback UAT JSON, precheck both outputs before teacher generation, rerun focused and protected gates | Yes: fallback commit 33d5471 pushed; Chief PATCH; correction follows |
| 20 | 2026-09-30 14:00:36 UTC | 2026-09-30 14:08:36 UTC | GPT-6 Luna | 33d547169cfe43be95111ff0bd71a37a795e6ff6 | e6409c814fdc040df97613e26358f0e43d41334e | PASS: orchestrator 8/8; importer 9/9; package validator 6/6; Stage2 39/39; protected Stage3 408/408 QGs recall 100%, sections 369/369, subquestions 328/328, MISS/FP/MERGE/SPLIT=0; 10/10 V0.9 asset hashes; refreshed real XML-normal and forced V0.9 1v1/class teacher+student package-valid UAT; py_compile/diff-check pass | Codex GPT-6 Sol | PASS | Run overall B-Line final gate review; if PASS, create and verify the authorized final B-Line annotated tag, then stop at the C-Line boundary | Yes: syntax/evidence patch e6409c8 pushed; this Journal metadata commit follows |

Round 19 Chief review used the explicit `gpt-6-sol` model override and returned PATCH. The fallback and regression evidence did not override the import SyntaxError; the claimed test pass was not accepted. Round 20 Chief review independently confirmed the syntax repair, eight orchestrator tests, preflight against student-output collision before teacher generation, refreshed 1v1/class UAT reports with `whole_job=true` and the frozen baseline SHA, four valid packages, and 10/10 asset hashes. Chief identity for both reviews: `Codex GPT-6 Sol`.

| C0-R1 | ~2026-09-30 15:06:21 UTC (first observation; actual start unknown) | 2026-09-30 15:28:05 UTC | GPT-6 Luna (contract audit) | eae89ea8720b94d29a94fc652830de628f373cd9 | cc3b20033a3f34bc5209003419068538e22290cf | PASS: source-only integration contract audit; delivery architecture addendum recorded; diff-check clean; no implementation gates run | Codex GPT-6.1 Sol | CHIEF_UNAVAILABLE (model invocation rejected for account usage limit; no review performed) | Stop before Round 2; obtain actual GPT-6.1 Sol review of the audit, then proceed only on its PASS/PATCH verdict | Yes: audit commit e971417 pushed; result-delivery addendum cc3b200 pushed; Journal metadata commit follows |

| C0-R1-final | ~2026-09-30 15:31 UTC (Chief retry kickoff; exact review start not captured) | 2026-09-30 15:49:58 UTC | GPT-6 Luna (contract patch) | eae89ea8720b94d29a94fc652830de628f373cd9 | 8f660f8aaba2877f7d0a81dcd6d64fad251887af | PASS: contract audit aligned to frozen A/B surfaces; file-backed job recovery, single-DOCX scope, GET open route, local validated outputs before done, required ZIP delivery, and download/generation failure separation documented; diff-check clean | Codex GPT-6.1 Sol | PASS (after PATCH corrections; scoped to Round 1 audit only) | Begin Round 2 minimal persistent job API and production A-Line facade; keep frozen cores unchanged | Yes: audit contract commit 8f660f8 pushed; Journal metadata commit follows |

| 2 | ~2026-09-30 15:50 UTC (worker start after Round 1; exact start not captured) | 2026-09-30 16:30:53 UTC | GPT-6 Luna | da1d16ff0a90550e4b3b6e52b461cc127bfd5691 | 99cca1a5d11566bc6e7d52207b765daafdd88a79 | PASS: 38 C0/renderer tests + 7 subtests; independent Chief: C0 10/10 + package validator 6/6; restart persistence, valid DOCX completion/download/open, invalid XML and duplicate-path rejection; py_compile, node --check, diff-check pass; frozen cores unchanged | Codex GPT-6.1 Sol | PASS (after PATCH; scoped to persistent job boundary and A-Line facade) | Round 3: connect A-Line semantics to documented block plan and B-Line XML/fallback; deliver teacher/student to stable result dir and run HTTP integration cases | Yes: implementation commit 3376d4e and PATCH 99cca1a pushed; Journal metadata commit follows |

| 3 | ~2026-09-30 16:42 UTC (first evidence capture; actual kickoff not captured) | ~2026-09-30 18:05 UTC (Chief PATCH; minute approximate) | GPT-6 Luna | f96f47cb189e941f411d0365f38134d417fe96cc | 7d4a00b40c71096b03efe2adb1167332779fd84d | PASS machine gates: 120 tests + 7 subtests; Stage2 39/39; protected Stage3 QG 408/408, sections 369/369, subquestions 328/328, MISS/FP/MERGE/SPLIT=0; 3 HTTP cases and WPS class round trip pass; 10/10 V0.9 assets | Codex GPT-6.1 Sol | PATCH: atomic paired plans and persist fallback renderer/reason/baseline before V0.9 invocation | Round 4: fix both fallback branches and add focused regressions; keep A/B/V0.9 frozen | Yes: candidate 7d4a00b pushed; Round 4 correction commits followed |
| 4 | ~2026-09-30 18:05 UTC (PATCH follow-up; approximate) | 2026-09-30 18:21:29 UTC | GPT-6 Luna | 7d4a00b40c71096b03efe2adb1167332779fd84d | f1ffba963732152ee2b65508c7e35be934d29af6 | PASS: focused C0/renderer 45 tests + 7 subtests; full repository 145 tests + 7 subtests; Stage2 39/39; protected Stage3 retained 408/408 QGs, 369/369 sections, 328/328 subquestions, zero error classes; 10/10 V0.9 asset hashes; real HTTP XML/fallback/local-open/ZIP and WPS round trip pass | Codex GPT-6.1 Sol | PASS | Create and verify `v1.2-c0-end-to-end-2026-09-30`; stop at the C1 boundary | Yes: implementation `a20fcca` and deterministic-test fix `f1ffba9` pushed; Journal/evidence commit and checkpoint tag follow |

| C1-R1 | 2026-10-01 00:35:58 UTC | 2026-10-01 00:42:34 UTC | Codex GPT-6 (worker; exact variant unavailable in session metadata) | 7bb7f303d36bc14b6b68cb0d2629616d4a30cf2c | c8d5d103bff5588cf12199c51777c04b2effc7b0 | PASS: read-only A-Line/template audit and Chief factual review; `git diff --check` clean; mapping gate `HUMAN_REQUIRED`; no implementation/tests run by design | Codex GPT-6.1 Sol | PASS (audit report accuracy); HUMAN_REQUIRED (slot mapping gate) | Await approved rules for generic QG/body routing, answer/analysis ownership, intentional slot ordering, and material/table conflicts; resume implementation only after decision | Yes: audit report commit `c8d5d10` pushed; this Journal metadata commit follows |

| C1-R2 | 2026-10-01 00:59:02 UTC | 2026-10-01 01:01:42 UTC | Codex GPT-6 (worker; exact variant unavailable in session metadata) | 87e02df7d67f089874a84cb5739513f04b77e827 | 6c9e9350384a73caa9ebfce1da1c0b7a1e0b6ff2 | PASS: approved Business Rules recorded; `git diff --check` clean; no code gate run in this rules-only round | Codex GPT-6.1 Sol | PASS (after PATCH: table atomicity made unconditional) | Begin Slot Router implementation under `C1_SLOT_ROUTING_BUSINESS_RULES.md`; keep A-Line, B-Line and V0.9 frozen | Yes: rules commit `6c9e935` pushed; this Journal metadata commit follows |

| C1-R3 | ~2026-10-01 02:30 UTC (inherited round; exact kickoff not captured) | 2026-10-01 03:06:54 UTC | Codex GPT-6 (worker variant unavailable in inherited execution metadata) | 87e02df7d67f089874a84cb5739513f04b77e827 | 1de6cb08c83d2eee5634b44c30247088c6d4cff6 | PASS: focused C1/application/renderer/regression suite 102 passed + 7 subtests; Stage2 39/39; fresh Stage3 8/8 source hashes, QG 408/408, sections 369/369, subquestions 328/328, original recall 100%, E1/E2/E3/E4/MISS/FP/MERGE/SPLIT=0; real WPS open/SaveAs/reopen/PDF and package checks 6/6; diff/compile/JS checks pass | Codex GPT-6.1 Sol | PASS (independent implementation/UAT review; no remaining PATCH finding) | `C1_UAT_FIX_PASS`; stop C1 work and wait for the next authorized roadmap phase | Yes: implementation commit `1de6cb0` pushed and remote SHA verified; Journal metadata commit follows |

Round 3 Chief review was performed by Codex GPT-6.1 Sol only. It independently reviewed the Slot Router and final UI wording, confirming the correct template labels, explicit-heading priority, atomic practice blocks, slot-internal ordering, fail-closed material/table behavior, and the scoped X012 `TABLE_SLOT_CONFLICT` fallback. Real WPS evidence is from `KWps.Application`; it is not represented as Microsoft Word evidence. The inherited kickoff time and worker model variant were not available, so the start is approximate and the worker variant is explicitly marked unavailable rather than guessed.

| C2-R1 | 2026-10-01 07:25:08 UTC (implementation timestamp captured; branch/tag setup preceded it) | 2026-10-01 07:30:12 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 7daa519bb804d5cb5fd4328636b2346e166ba81c | 9096402e5377447364bf5d312e08ae4acfdd263b | PASS scoped resolver gate: 23 batch tests + 6 C1 input tests + Stage2 39/39 = 68 passed; compile and staged diff-check pass; no frozen core or approved Business Rules diff; real batch/WPS/performance/Stage3 final gate pending | Codex GPT-6.1 Sol (actual independent review) | PATCH: isolate zlib decompression errors; preserve meaningful role words in topic names; support or explicitly reject legacy GBK ZIP names | Round 2: fix all three findings, add real compressed-member/GBK fixtures, rerun gates and submit for independent review | Yes: implementation `9096402` and Journal `3f0c79a` pushed and remote verified before review |

| C2-R2 | 2026-10-01 07:34:31 UTC | 2026-10-01 07:38:39 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 3f0c79ad9be93eb573c0a19a934c733debde6c81 | fb3803386614b6c1eb1c7d913b2fd09551ce567a | PASS scoped PATCH gate: 34 batch tests + 6 C1 input tests + Stage2 39/39 = 79 passed; actual malformed DEFLATE item isolation and GBK-no-UTF8-flag fixtures pass; role-word topic preservation pass; compile/diff checks pass; frozen cores/Business Rules unchanged | Codex GPT-6.1 Sol (actual independent review) | PASS for the three-finding resolver remediation; C2 final gates remain pending | Round 3: connect the reviewed resolver to persistent serial per-item backend jobs and API | Yes: patch `fb38033` and Journal `c44b227` pushed and remote verified before review |

| C2-R3 | 2026-10-01 07:42:49 UTC | 2026-10-01 07:56:23 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | c44b2279fd7e516f770edf8128500d57b9970d16 | cf68fcf117692985682eae6273181c8fffd9edbf | PASS scoped backend gate: 109 focused tests including Stage2 39/39, plus 11 backend cases rerun after final progress correction; compile/staged diff-check pass; serial per-item synthetic XML/fallback, successful-sibling preservation, restart and clean local/ZIP delivery; frozen cores/Business Rules unchanged; real UAT/performance/Stage3 final gate pending | Codex GPT-6.1 Sol (actual independent review) | PATCH: simultaneous first submissions create separate executors outside the submission lock, allowing concurrent jobs/COM | Round 4: atomically register the single executor under the lock; add a real async concurrency regression and rerun gates | Yes: implementation `cf68fcf` and Journal `f0fe42f` pushed and remote verified before review |

| C2-R4 | 2026-10-01 08:02:13 UTC | 2026-10-01 08:03:47 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | f0fe42f1b53c5ba7ebe71dc252584f83ec15d787 | 77b0ae56a8ef64ce15ffe0f0d751ce1b1b3d1e66 | PASS scoped serial-safety PATCH: 110 focused tests including Stage2 39/39; real async eight-first-submission test creates one executor, max in-flight one, all callbacks complete and pending state clears; compile/staged diff-check pass; no frozen core/C1 Rules changes; real batch/WPS/performance/Stage3 final gate pending | Codex GPT-6.1 Sol (actual independent review) | PASS for atomic serial executor registration and async concurrency regression; C2 final gates remain pending | Round 5: minimal frontend batch counters/item outcomes/local delivery controls, then real C2 evidence gates | Yes: repair `77b0ae5` and Journal `cd7264b` pushed and remote verified before review |

| C2-R5 | 2026-10-01 08:06:57 UTC | 2026-10-01 08:17:18 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | cd7264b0c4f0d304a027478849c35e02762fade4 | 684a3a6589dc8bb55ff841fda71d692106e6f6cc | PASS scoped workspace gate: 123 focused tests (backend 110 + executed synthetic JS/DOM UI 13) including Stage2 39/39; final UI 13 rerun passes; production/test JS node checks and staged diff-check pass; total/completed/failed/current topic and per-item roles/renderer/status shown; partial local delivery preserved; no backend/frozen core/C1 Rules changes; real browser/product/WPS/performance/Stage3 final gate pending | Codex GPT-6.1 Sol (actual independent review) | PASS for minimal batch UI slice; final C2 UAT/evidence gates remain pending | Round 6: collect real batch Cases A–F, WPS product checks, same-machine V0.9 timing and fresh protected regression | Yes: UI `684a3a6` and Journal `0dd1391` pushed and remote verified before independent review |

| C2-R6 | ~2026-10-01 08:22 UTC (first evidence directory timestamp; exact kickoff not captured) | 2026-10-01 08:51 UTC (minute rounded) | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 0dd1391ad2e003bef4ac2ab7e00cd4f44bcf494a | ea3b2927c0f01772cacda8a91bb8beb1b15cf32a | PASS evidence candidate: 123 focused tests; real Cases A-F, 32/32 packages; 30/30 XML ordinal content audits; 11/11 WPS open/SaveAs/reopen/PDF and saved packages; 21 PDF pages inspected; XML 13.975s versus same-source frozen V0.9 76.801s; genuine paired input has zero make_student/COM; isolated fallback and corrupt-item partial success; all six ZIP downloads HTTP200; real Windows folder-open call HTTP200; Stage2 39/39; fresh Stage3 QG408/408, sections369/369, subquestions328/328, original recall100%, all specified errors0; frozen V0.9 assets10/10 and source hashes27/27 | Codex GPT-6.1 Sol (actual independent review) | PASS for real batch/WPS/performance/protected evidence; real browser interaction remained pending | Complete the user-directed local-only delivery revision and real browser gate; then submit for independent review before any C2 completion/tag | Yes: evidence `ea3b292` committed; this Journal metadata commit and both pushes follow, then remote SHA verification |

Round 6 process counts are sampled distinct WPS PID/start-time instances at 100ms; WMI StartTrace was denied. Frozen PowerShell script invocation counts are exact and recorded separately. Product evidence is actual WPS (`KWps.Application`), not Microsoft Word, and sampled page inspection is not a human classroom-readiness verdict. No production source or frozen Business Rules/core changed in this evidence round.

| C2-R7 | 2026-10-01 09:28 UTC (minute approximate; continuation verification preceded implementation) | 2026-10-01 09:43:00 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 9eeb159e41ee285f5f8bb6bcc86f3517fe7a96f2 | 6f5daac9bdbc842f1c29606ecc7225b66dfa3123 | PASS scoped local-delivery revision: 124 focused tests including Stage2 39/39; fresh Stage3 QG408/408 sections369/369 subquestions328/328 original recall100% specified errors0; V0.9 assets10/10; real headed Edge multi-DOCX class3success/5DOCX and Chinese nested ZIP1v1 partial2success/1failure/3DOCX; 8/8 package-valid clean local outputs; actual Open Folder2/2 confirmed Explorer; result/history download controls0, obsolete route404, legacy download fields removed; Python/JS/diff checks pass; frozen boundaries unchanged | Codex GPT-6.1 Sol (required; independent Round 7 review pending) | PENDING; no Chief verdict fabricated | Stop Worker edits; submit pushed delivery revision plus browser/regression evidence for independent Chief review; no C2 completion/tag yet | Yes: implementation/evidence 6f5daac committed and pushed; Journal metadata commit/push follows |

Round 7 implements the user's revised product requirement: keep input ZIP,
remove output ZIP delivery entirely. Earlier R7 pre-revision browser/download
observations are preserved externally and superseded; they are not committed as
a current download PASS. First local focused attempt exposed an orphan JS brace
after download-control removal; it was fixed before the passing 124-test rerun.
The independent Round 6 actual PASS is now recorded above. Fresh Round 7 browser
evidence lives under `C:\xml-uat\c2-browser-round7\delivery-revision`; actual
Explorer accessibility and headed browser screenshots confirm local delivery.
Chief identity is exclusively `Codex GPT-6.1 Sol`; Round 7 review has not yet
been performed. A-Line/B-Line/V0.9/C1 frozen code and Business Rules are unchanged.

| C3-R1 | ~2026-10-01 10:10 UTC (first fresh regression evidence; branch/tag verification preceded it, exact kickoff not captured) | 2026-10-01 10:16:55 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | f3fc31ab10f32673afc1398c98df124971b0cd13 | 397e7ba002d388f84f5907b1c088b16d63b8749e | PASS audit-only machine gate: C2 annotated tag object887693a and targetf3fc31a verified local/remote; C3 branch created/pushed from tag; frozen V0.9 app assets10/10; read-only27-real-source feature inventory/hash27/27; Stage2 39/39; fresh Stage3 QG408/408 sections369/369 subquestions328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0; existing C1 WPS/C2 batch/browser evidence locations confirmed; staged diff-check PASS; documentation-only diff | Codex GPT-6.1 Sol (actual independent review) | PASS for capability audit only; no real Studentizer support claimed | Round 2: implement conservative standalone reviewed-allowlist Studentizer and synthetic preservation fixtures; no production routing | Yes: audit397e7ba committed/pushed; Journal metadata commit/push follows |

C3 Round 1 audits the real frozen red/marker/blank conversion flow. The report
separates observed behavior from proposed XML capabilities, documents the Python
docstring/PowerShell deletion-range discrepancy, section-level rather than
question-level answer parentage, and real table/textbox/object/red-color risks.
Raw feature presence is not removal authorization. It explicitly records absent
fixture coverage and does not claim an XML Studentizer output or no-over-deletion
gate. Source files remain unchanged. External fresh evidence is
`C:\xml-uat\c3-round1-capability\`; existing C1/C2 WPS/browser/performance evidence
is referenced, not reimplemented or represented as newly executed C3 UAT.
Chief model for this round is exclusively `Codex GPT-6.1 Sol`; actual scoped PASS is recorded in the Round 1 row.

| C3-R2 | ~2026-10-01 10:25 UTC (first implementation file timestamp; exact kickoff/initial design time not captured) | 2026-10-01 10:32:40 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 36636ffbafbf891cff094c3b86558b774f84b00e | f6d058b52f7be85cbfee9dae122238affc6a8b4d | PASS scoped standalone machine gate: 29 synthetic Studentizer fixtures; combined153 tests including existing124/Stage2 39/39; reviewed exact-source/body-address/fingerprint terminal answer removal, supplied-student byte bypass, role/section/stale binding/mixed/table/object/bookmark/revision ambiguity failclosed, adjacent body/next question/duplicate/red knowledge unchanged, preserved image/media/rels/package members; fresh Stage3QG408/408 sections369/369 subquestions328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0; V0.9 assets10/10; compile/staged diff-check PASS; existing frozen files unchanged | Codex GPT-6.1 Sol (actual independent review) | PASS scoped standalone preservation; allowlist does not prove complete answer coverage | Round 3: integrate only with complete reviewed Golden coverage; otherwise per-item whole-job V0.9 fallback; real support/performance pending | Yes: implementation/tests/report f6d058b committed/pushed; Journal metadata commit/push follows |

C3 Round 1 actual independent Chief PASS is recorded above. Round 2 is standalone:
the trusted reviewed ownership allowlist is a caller contract, not newly inferred
A-Line binding. The production app cannot supply it and remains untouched. Only
dedicated plain-text terminal answer paragraphs with reviewed structural identity
can be removed; no color stripping, partial text deletion or blank insertion is
implemented. Synthetic tests exercise actual file creation/validation with source
and adjacent content preservation; they are not real-corpus XML Studentizer or
WPS UAT. No real sample support/performance/zero-COM conclusion or C3 completion
is claimed. Report: `C3_STUDENTIZER_STANDALONE_GATE.md`; fresh external regression
evidence: `C:\xml-uat\c3-round2-studentizer\stage3\`.

Round 2 actual independent Chief reviewed candidate `f6d058b` and remote tip
`dddcd81`, independently reran 29 Studentizer tests and Stage2 (68 total), checked
8 concurrent publication attempts, fresh protected evidence and frozen assets,
and returned PASS. Its caveat is mandatory: exact approved deletion/preservation
is not whole-document answer completeness. No real support or zero COM was proved.

| C3-R3 | ~2026-10-01 10:42:12 UTC (planner file creation; exact kickoff not captured) | 2026-10-01 10:56 UTC (minute rounded) | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | dddcd8185f3de4f42345f577d3f4dad844772608 | deee628047c42ca7dceb332fa8c5134408ff3fdd | PASS scoped integration machine gate: 174 focused tests in49.59s (existing124 + standalone29 + integration21), Stage2 39/39; complete reviewed Golden manifest and frozen semantic/source/body identities; incomplete/stale/candidate/table/textbox/provider-mutation failclosed; supplied student bypass; later XML failure whole-job fallback resets original teacher; observed make_student restoration on success/error; concurrent fallback max active1; mixed batch/restart metadata; fresh Stage3QG408/408 sections369/369 subq328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0, exact QG boundaries87.7%, source8/8; V0.9assets10/10; real27-source coverage audit27/27 COVERAGE_UNPROVEN, source hashes unchanged,0 derivatives; compile/diff checks PASS; frozen C2 boundaries unchanged | Codex GPT-6.1 Sol (actual independent review) | PASS scoped complete-coverage orchestration; real Golden/WPS/performance remain pending | Round 4: audit genuine paired and existing legacy student sources for narrowly reviewed real Golden; no broad support or performance claim | Yes: implementation/report deee628 committed and pushed; this Journal metadata commit/push follows |

Round 3 changes only orchestration, a complete-evidence planner, focused tests
and this report/Journal. Human-reviewed Golden authority is trusted server-only
configuration; no real provider is shipped. Default teacher-only now conservatively
uses per-item whole-job V0.9 fallback and may be slower than prior eager COM
preparation plus XML; earlier C2 teacher-only timing is not current C3 performance.
No new real speed/COM-start measurements were made. Legacy `wps_com_started`
records observed entry into the COM-capable frozen make_student, with explicit
`wps_com_evidence=COM_CAPABLE_MAKE_STUDENT_ENTRY_ONLY`; it is not an OS process
probe or proof of actual process start on failure. Paired/student-only XML is
preserved. Fresh evidence: `C:\xml-uat\c3-round3-integration\`. Chief exclusively
Codex GPT-6.1 Sol; actual Round 3 scoped PASS confirmed by the parent after independent review.

| C3-R4 | ~2026-10-01 11:07:51 UTC (audit tool creation; actual pair inspection began earlier, exact kickoff not captured) | 2026-10-01 11:20:55 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 8a8b1724bc6bdae6506483084973e8b084d5f7fd | 472f90924ca17bb9feb259ad576433a02e4e53aa | PASS truthful audit/gap machine gate: 177 focused tests in49.46s (existing174+exactaudit3), Stage2 39/39; fresh Stage3QG408/408 sections369/369 subq328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7%, source8/8; V0.9assets10/10; read-only27-source hashes27/27 unchanged; exact-topic14 candidates inspected, full C14N and expanded-name student subsequence embeddings0; existingC2 7/C1 3 legacy derivatives inspected,10/10 source/oracle unchanged; X014/X010 immutable tables exact-positive but other complete answer/inline/boundary gaps remain; approved manifests0, XMLStudentizer outputs0, new derived WPS/PDF UAT NOT_RUN; compile/diff-checkPASS; production/frozen code unchanged | Codex GPT-6.1 Sol (actual independent review) | PASS scoped truthful pair/gap audit; no real Golden or C3 completion | Round 5: independently annotate real source candidates and review original full pages; incomplete subjects stay unresolved; no production provider before Chief approval | Yes: audit/report/diagnostic fixture472f909 committed/pushed; this Journal metadata commit/push follows |

Round 4 produces a small durable read-only structural audit and diagnostic
summary, not approved Golden or new Studentizer policy. All full-body exact
fingerprint comparisons are stricter than business content equivalence; changed
OMML/OLE/QG counts are diagnostic signals, not claims of lost classroom content.
Legacy marker absence/WPS/package UAT does not review every answer or protected
object. C1 X021 was a student original renamed teacher, not a valid teacher
business oracle. C2 CaseA contains no math input, but C1 X012 was additionally
inspected. No suitable current complete paragraph-only transformation was proved.
The report gives a concrete manual-Golden path based on full original source
annotation and exact structural addresses, requiring separately reviewed scope
for immutable tables/inline knowledge fills/multi-paragraph answers/boundaries.
Physical body indices are explicitly distinct from StructDoc bN where main-body
bookmark siblings occur. No derivatives exist, so new WPS derivative UAT was not
run; the environment is not marked unavailable. No new speedup/zeroCOM/performance
result is claimed. Evidence: `C:\xml-uat\c3-round4-real-pairs\`; report
`C3_REAL_GOLDEN_CANDIDATE_GATE.md`. Chief exclusively Codex GPT-6.1 Sol,
actual independent Round 4 scoped PASS confirmed by the parent.

| C3-R5 | ~2026-10-01 11:28:45 UTC (first original WPS export timestamp; kickoff preceded export, exact kickoff not captured) | 2026-10-01 11:47:50 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 001b3f9856e21dbfff7edb0fd2c890b3fcbadc3b | a819f01f066254ef6cbbec16656de21fd60b6f9a | PASS scoped candidate-packet machine integrity/protected gate: 180 tests in48.53s including Stage2 39/39; live exact-source/body-fingerprint/body_idx/full-semantic-unit/package-member checks for3 packets; X008 all14 original pages and264body blocks Worker reviewed,34 manual physical questions,146 retained/118 proposed complete answer/analysis removals,114 frozenunits incl29QGs/5missing-QG prompts explicitly recorded; independently manually assembled expected draft package valid, all non-document bytes preserved, notStudentizer-generated; X01426pages/X01820pages rendered but only pages1-2 reviewed each, all656/399blocks UNRESOLVED; approvedGold0/productionproviders0/realStudentizercoverageNOT_ESTABLISHED; fresh Stage3QG408/408 sections369/369 subq328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7% source8/8; corpus hashes27/27; V0.9assets10/10; source-WPSreadonlyopen/export3/3 with original/snapshot hashes unchanged; compile/diff-checkPASS; frozen+production code unchanged | Codex GPT-6.1 Sol (actual independent Round 5 review) | PATCH: report incorrectly claimed Q11 answer/analysis OLE removal; all four OLE are retained Q23 prompt objects | Correct X008 OLE report/packet/script narrative and add exact regression; keep all candidate approvals/providers false; submit corrected evidence for independent Chief re-review | Yes: candidate/report/fixtures/verifier/tests a819f01 committed/pushed; this Journal metadata commit/push follows |

Round 5 authors an independent original-source candidate, not the production
Studentizer's output or paired-file difference. Physics original14pages were
actually viewed, and the entire physical body text was read. Thirty-four manual
ownership ranges include all multi-paragraph explanations; every retained and
proposed removed block has its exact source address/fingerprint/rationale, and
all nontext structures and frozen units are accounted for. The unapproved expected
DOCX is an external manual XML-splice draft, package validation only. Five
physical questions have no frozen QG at their start; no QG IDs are invented.
Current Studentizer boundary/multi-paragraph/missing-QG ownership restrictions remain.
All four main-body OLE are retained Q23 prompt objects at body[164]; Q11
body[75..77] proposed removal contains plain text and no nontext/object.
This source does not exercise answer-OLE deletion; that capability is untested.
No real production Studentizer or derived-output WPS save/reopen/PDF UAT occurred.
Math/Chemistry full-source review is incomplete:60pages rendered,18pages viewed
in total (physics14/math2/chemistry2). All math/chem physical blocks remain
UNRESOLVED; no deletions/expected Gold for those subjects. Chief approval for
all packets is pending; zero providers are shipped. Source-only WPS open/export/
close times were2.542s/2.848s/3.770s, excluding application startup and review;
these are not production Studentizer performance/zeroCOM results. WPS provenance
is actual KWps/wps.exe despite the compatibilityName reportingMicrosoftWord.
Report: `C3_INDEPENDENT_SOURCE_GOLDEN_CANDIDATES.md`; external original-page and
candidate evidence: `C:\xml-uat\c3-round5-source-review\`. Chief exclusively
Codex GPT-6.1 Sol: actual independent Round 5 review returned PATCH for the
incorrect Q11/OLE narrative. Corrected candidate content approval remains pending.


| C3-R5-PATCH | Before 2026-10-01 11:55:12 UTC (first inherited patch verification timestamp; exact kickoff not captured) | 2026-10-01 11:58:31 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | f6c5d59ef35a418c227b02a702ce54dfea641deb | 44d8a55a459e1a0b825913a8013d7029a544ca33 | PASS surgical evidence correction: 181 focused tests in49.59s incl Stage2 39/39; exact four-RETAIN-OLE/Q23 body164 and plain-text-Q11 body75-77 regression; live three-source candidate verifiers PASS, approved/provider false; fresh Stage3QG408/408 sections369/369 subq328/328 original recall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7%, source8/8; V0.9assets10/10; compile/diff-checkPASS; candidate DOCX/hash/manual ranges unchanged; no production/frozen code changed | Codex GPT-6.1 Sol (required; independent correction re-review pending) | PENDING; no new Chief verdict fabricated | Stop Worker edits and submit corrected evidence for independent Chief re-review; keep all candidates unapproved, math/chem unresolved; no real Studentizer coverage/C3 complete/zeroCOM claim | Yes: correction44d8a55 committed/pushed and local/remote full SHA verified; this Journal metadata commit/push follows |

R5 PATCH only corrects the report, packet description and external assembly
script, and adds the explicit OLE evidence regression. No splice range, candidate
DOCX bytes, source fingerprint or production policy changed. Original R5 Chief
PATCH is now recorded above; corrected candidate re-review is PENDING. Answer-OLE
deletion is untested, and all candidate approval/provider values remain false.
No new production Studentizer timing, speedup or zero-COM measurement was made;
prior source-only WPS times remain source preparation measurements. No derived
WPS save/reopen/PDF UAT or new subject coverage was added. External fresh
protected evidence: `C:\xml-uat\c3-round5-source-review\patch-ole\`.

| C3-R5-CHIEF-FULL | Before 2026-10-01 12:05:48 UTC (first recorded Chief clock; all-page inspection began earlier, exact kickoff not captured) | 2026-10-01 12:09:40 UTC (content review/report completed, before metadata publication) | N/A — Chief-only content review; no Worker implementation | 12ebfac84d77ca0dffdd99b211fbdd8638751f47 | 12ebfac84d77ca0dffdd99b211fbdd8638751f47 (reviewed content/code HEAD; subsequent metadata commit contains this record) | PASS exact-source Golden comparison: all14 original WPS pages/264physical body records independently read;34 physical owners;118 disjoint answer/analysis paragraphs;146 retained full fingerprints/order; independently enumerated coordinates reconstruct exact expected root6b93cfc1594afc35bfa7801a4a73768185058fb2101e41e9f3d363173f31e0a2; expected candidate package67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9; exact source SHA56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4; all package members accounted/non-document bytes identical;4OLE in retained Q23 body164;Q11 body75-77 text only; no source/candidate/executable edits; preceding same-base independently executed181tests inclStage2 39/39/freshStage3 408/369/328 zero errors/V09assets10/10 evidence retained, not falsely rerun as UAT | Codex GPT-6.1 Sol (actual independent full-content review) | X008_GOLDEN_APPROVED exact source content/after-document only; no provider or production support approval | Separate Studentizer capability review/implementation and derived WPS/UAT;5missing frozen QGs remain unresolved production compatibility;math/chem remain unapproved;no C3 completion/zeroCOM/performance PASS | Yes: Chief-only report/Journal metadata committed and pushed after stating verdict; publication SHA/remote verification supplied in Chief reply |

This Chief-only entry is distinct from R5 packet integrity. Report:
`C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md`. The Chief personally inspected every
original page and each complete owner/removal region, including unmarked
explanation continuations. The approval binds only the exact source hash and
expected after-root hash above; it creates no color/role/numbering deletion
rule and does not authorize a production provider or frozen-core change.
Existing draft packets retain `approved=false`/`production_provider=false`;
this report supplies independent content authority for a separately gated
capability step. All14pages reviewed does not mean new derived-output WPS UAT:
none was run. No new performance/zeroCOM result or C3 completion is claimed.

| C3-R6 | Before 2026-10-01 12:14:16 UTC (first recorded Worker clock; API review began earlier, exact kickoff not captured) | 2026-10-01 12:19:28 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | dbcd5a60145a171ca72117b257a1a6e99eba91e2 | be8ff91e3f25f31cf64c099798b03de32d68c1e6 | PASS truthful capability-refusal/protected machine gate:185focused tests in49.26s inclStage2 39/39;4final exact-address probes in0.70s; approved34physical owner ledger/118removals/146protected blocks verified; actual publicprepare_student returnedSTUDENTIZER_FIELD_SCOPE_UNSUPPORTED(fldChar),first RETAIN body3 at/w:document/w:body/w:p[4]/w:r[2]/w:fldChar;0mutations/nooutput/source+expected unchanged; freshStage3source8/8 QG408/408 sections369/369 subq328/328 originalrecall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7%; V09assets10/10 compile/stageddiffchecksPASS; production/frozen unchanged; derivedWPSUAT NOT_RUN_NO_STUDENTIZER_OUTPUT; performancebenchmark NOT_RUN | Codex GPT-6.1 Sol (required; independent Round 6 review pending) | PENDING; no Chief verdict fabricated; STUDENTIZER_CAPABILITY_BLOCKED is the actual Worker capability result | Stop Worker after publication for independent review; separately authorize/review generic exact physical contiguous answer ranges with unchanged-boundary validation; no production provider or C3completion | Yes: probereport/harness/tests/fixture be8ff91 committed/pushed and remote fullSHA verified; this Journal metadata commit/push follows |

Round 6 audits the actual public API against the independently approved X008
Golden; it does not manufacture an execution capability. Its exact physical
owner request uses `owner_kind=physical_question`, never invented frozen QG
identities. Global field rejection occurs before processing these bindings;
terminal-single-marked-answer/QG-owner restrictions are additional static API
incompatibilities, not runtime results after stripping source structures.
This is a product capability boundary, not `REAL_APP_UAT_ENVIRONMENT_BLOCKED`.
No derivative exists, so derived WPS open/SaveAs/close/reopen/PDF and expected
after-root comparison are NOT_RUN. The external manual expected draft was not
substituted for Studentizer output. Four OLE remain in the unchanged source's
Q23; answer-OLE removal and table support remain untested. Math/chem remain
unapproved. Performance evidence is NOT_RUN: captured0.087998s measures one
refused preparation attempt only, and com_invocations=0 is an API field rather
than an OS process probe or product zeroCOM proof. Report:
`C3_APPROVED_X008_STUDENTIZER_PROBE.md`; captured actual call:
`fixtures/c3-r6-approved-probe.json`; external protected evidence:
`C:\xml-uat\c3-round6-approved-source\`. Minimal future capability proposal is
documented but not implemented. Chief exclusively Codex GPT-6.1 Sol, PENDING.

| C3-R7 | Before 2026-10-01 12:25:51 UTC (first recorded Worker clock; API inspection preceded it, exact kickoff not captured) | 2026-10-01 12:54:13 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | a7ced4bc615c7d9641557ab05a35e1a2a2340e46 | 3fe390a4edf087ec68f8aa47219de93a7a047cf2 | PASS scoped standalone physical-range capability/protected gate:222focused tests in52.49s inclStage2 39/39;37new cases inclrealapproved transform; exhaustive264-child ledger/34physical owners/118plainanswer removals/146retained fullfingerprints/order; actual publicprepare_student XML_PREPARED after-root6b93cf... and fullDOCX67e0bc... equalChiefGolden; non-documentparts/memberorderexact; revisedcross-story PAGE/NUMPAGEScounter testsPASS, REF/PAGEREF/unknown/fragmentlinksfailclosed; final freshStage3source8/8 QG408/408 sections369/369 subq328/328 originalrecall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7%; V09assets10/10 compile/stageddiffchecksPASS; actualKWps alerts-enabledOpen/SaveAsnew/Close/Reopen/PDFcallsPASS onfreshverifiedoutput; bothpackagesvalid,142paragraphtexts/orderexact,4OLEpayloadsbyteidentical,9PDFpagesreadable,34questionnumbers1-34ordered,visualpages1/5/6/9inspected; source/Golden/inputunchanged; inheritedTOCerrors2→2; repairabsenceNOT_PROVEN; wholejobperformancebenchmarkNOT_RUN; productionprovider/planner/orchestrator/frozencoresunchanged | Codex GPT-6.1 Sol (actual independent Round 7 implementation review) | PATCH: retained TOC bookmark switch was not tracked, allowing removal within its referenced bookmark interval | Track generic TOC bookmark dependency and fail closed on unsupported parameters; reproduce refusal, preserve approved X008, rerun real derived WPS/protected gates, then independent re-review; no production activation | Yes: implementation/harness/tests/report/evidence3fe390a committed/pushed and fullremoteSHA verified; this Journal metadata commit/push follows |

Round 7 implements a separate standalone `PhysicalRangeSemantics` dispatch;
legacy marked-single-answer semantics/_plan and supplied-student bypass are
unchanged. It never invents frozen QGs, routes by sample ID/hash or installs a
production provider. The real UAT harness only constructs reviewed evidence and
calls `studentizer.prepare_student`; it does not manually splice the output.
An intermediate too-broad cross-story field guard refused unchanged footer page
counters (216pass/1fail). It was corrected to support only balanced PAGE/NUMPAGES
with optional MERGEFORMAT; a new verified output, final222-test rerun and fresh
WPS roundtrip supersede all prior trials. Other cross-story field dependencies
and ambiguous hyperlink relationships continue to fail closed.

Final WPS input SHA equals the independent Golden67e0bc...; actual provider is
KWps.Application/wps.exe, not Microsoft Word despite compatibilityName. Saved
DOCX7067486bytes/PDF2127287bytes are nonempty/readable. PDF all9pages receive
automated readability/content evidence; actual visual inspection is4pages
(1/5/6/9), not a nine-page visual/classroom-readiness verdict. No OMML/table
exists in this source; all4OLE stay inQ23, and answer-object removal remains
untested. OriginalPDF/derivedPDF both display2undefined-bookmark errors; cached
XMLw:t counts0use a different field-evaluation statistic and do not override
PDF observations. Source TOC page caches are intentionally not repaired.

Alerts-enabled synchronous ordinaryOpen/Reopen returned without an unresolved
blocking modal or exception; repair was not requested. Modal dialogs were not
directly instrumented, and automatic repair without a prompt cannot be excluded;
repairabsence is NOT_PROVEN. Performancebenchmark is NOT_RUN: API elapsed/WPS
timestamps are diagnostics, not whole-job speed or OSzeroCOM measurements.
Source and independentGolden hashes remain unchanged. Report:
`C3_REVIEWED_PHYSICAL_RANGE_GATE.md`; durableevidence:
`fixtures/c3-r7-physical-range-evidence.json`; fresh external evidence:
`C:\xml-uat\c3-round7-physical-ranges\verified-wps\` plus parent directory
transform/protected reports. Chief exclusively Codex GPT-6.1 Sol; original
Round 7 implementation review returned PATCH for the missing TOC bookmark
dependency. That scoped machine/UAT evidence did not authorize production use.


| C3-R7-PATCH | Before 2026-10-01 13:00:12 UTC (first recorded Worker clock; exact kickoff not captured) | 2026-10-01 13:07:40 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 7e5959fddb1694d19b989e23185d8bb1790fd6d4 | 9bf784e050c93d1ed6254ec6ddffd7fba5e8327d (reviewed HEAD; implementation e93e695) | PASS scoped TOC dependency correction:233focused tests in55.11s inclStage2 39/39;oldbug reproduced beforefix;11newTOC tests(simple+complex field/bookmark overlap refusal withnooutput/sourceunchanged,8ambiguous/unknown/repeatedparameter refusals,legitimatebookmarkoutsideremoval preserves);fresh actual publicprepare_student X008after-root6b93cf.../DOCX67e0bc... exactChiefGolden,118removals/146retained+non-documentparts/orderunchanged;freshStage3source8/8 QG408/408 sections369/369 subq328/328 originalrecall100% E1-E4/MISS/FP/MERGE/SPLIT0 exactboundary87.7%;V09assets10/10 compile/stageddiffchecksPASS;newoutput actualKWps alerts=-1 Open/SaveAsnew/Close/Reopen/PDFcallsPASS,packagesvalid,142para text/order/4OLEpayloadsexact,9PDFpagesreadable/34numbersordered,visualpages1/5/6/9inspected;source/Golden/inputunchanged;inheritedTOCerrors2→2;repairabsenceNOT_PROVEN;performancebenchmarkNOT_RUN;production/frozenunchanged | Codex GPT-6.1 Sol (actual independent correction re-review;2026-10-01 13:18:36 UTC) | PASS scoped standalone physical-range capability + exact X008 WPS UAT;performance NOT_RUN;repair/modal absence NOT_PROVEN;original R7 PATCH retained | Continue C3 math/chem evidence, safe production integration and real workload performance gates under already authorized C3 goal;no C3complete/zeroCOM/performanceclaim | Yes: small parser/tests/report/diagnosticfix e93e695 committed/pushed and remoteSHA verified; this Journal metadata commit/push follows |

### C3-R7-PATCH independent Chief re-review — 2026-10-01 13:18:36 UTC

`chief_model = Codex GPT-6.1 Sol` (actual independent Chief invocation).
`reviewed_head_sha = 9bf784e050c93d1ed6254ec6ddffd7fba5e8327d`;
local/remote matched and worktree was clean at review. The Round row records
this reviewed HEAD and preserves implementation SHA
`e93e69513877c70e5519a8344dc540d7dd6107be` in its implementation note.

**Chief verdict: PASS, scoped to standalone reviewed physical-range capability
and the exact approved X008 derived-output WPS UAT.** This replaces the corrected
implementation's PENDING verdict only; original Round 7 Chief PATCH remains.
Independent machine gate: **233/233 in 52.40s**, including Stage2 **39/39**;
simple and split-instrText complex TOC bookmark dependency reproduced as refusal,
without publication/mutations. New public API output exactly matches approved
package/root hashes, 118 removals and 146 retained children. All eight Stage3
predictions independently recomputed and matched; independent GoldCompare QG
408/408, sections369/369, subquestions328/328, original Recall100%,
E1-E4/MISS/FP/MERGE/SPLIT0; QG exact boundaries87.7%. Frozen V0.9 assets10/10
independently byte-identical. New WPS input provenance/timestamps verified;
open/SaveAs-new/close/reopen/PDF calls pass, both packages valid,142 paragraph
w:t values/order and4 OLE payloads exact,9 PDF pages readable,Q1-34 ordered,
source/current undefined-bookmark errors2->2. Chief again visually inspected
pages1/5/6/9; no all-page visual/classroom claim.

`performance = NOT_RUN`; `repair/modal_absence = NOT_PROVEN`.
No production provider, general math/chem coverage, product zero-COM proof,
performance improvement or C3 completion is approved by this verdict.
Next action: continue C3 math/chem evidence, safe production integration and
real workload performance gates under the user's already authorized C3 goal.
Commit/push: this metadata-only Chief Journal update is committed and pushed;
verify its resulting local/remote SHA and clean worktree after publication.

R7 PATCH changes only the generic TOC parameter/dependency handler and related
regressions/evidence. It does not special-case X008 or change frozen/production
routing. Original Chief PATCH is truthfully recorded above; corrected review is
scoped PASS as recorded in the independent re-review entry above. The actual updated public Studentizer newly generated
`C:\xml-uat\c3-round7-toc-patch\X008-studentizer-verified.docx` before the
fresh complete WPS roundtrip in that directory's `verified-wps` folder. Its
identical Golden package SHA demonstrates this dependency guard does not change
the approved transformation bytes; new savedDOCX7067505bytes/PDF2127287bytes
are current WPS outputs, not borrowed earlier artifacts. All9pages automated,
4pages1/5/6/9actually visually inspected again; no full visual/classroom claim.
PDFsource/current undefinedbookmark errors2→2; cached XMLcounts0are a separate
statistic. Repairabsence remains NOT_PROVEN: actual alerts=-1 but modal prompts
not directly instrumented/automatic repair cannot be excluded. Performance
benchmark remains NOT_RUN. New durable evidence:
`fixtures/c3-r7-toc-patch-evidence.json`; report patch section:
`C3_REVIEWED_PHYSICAL_RANGE_GATE.md`. Source/Golden and frozenassets unchanged;
math/chem remain unapproved, no provider or new production activation.

| C3-R8 | Before 2026-10-01 13:20:20 UTC (first recorded Worker clock; exact kickoff unavailable) | 2026-10-01 13:38:35 UTC | GPT-6.1 (`gpt-6.1-sol`, actual Worker invocation) | 9493423e62db0f7e0f29ef6e99ae8e2453a7d530 | cd6ccadaea8fba082a84a08bfc1be68c0d932e5a (selection report/evidence implementation HEAD) | PASS selection-only: corpus SHA27/27; selected X012486/486 and X023370/370 endpoints valid; read-only source WPS page counts30/32, hashesunchanged; focused235/235 in52.70s inclStage2 39/39; fresh8-source Stage3 QG408/408 sections369/369 subq328/328 originalRecall100% E1-E4/MISS/FP/MERGE/SPLIT0 exact87.7%; V09assets10/10; compile/stageddiffcheckPASS; production/frozenunchanged; performanceNOT_RUN; no math/chem Golden, Studentizer or derived WPS UAT approval | Codex GPT-6.1 Sol (required independent review; not yet invoked by Worker) | PENDING | Independent Chief selection review, then separate full source Golden/capability work; no production activation or C3 completion | Yes: cd6ccad committed/pushed and remote fullSHA verified; Journal metadata commit/push follows |

### C3-R8 selection evidence boundary

`chief_model = Codex GPT-6.1 Sol` (required; actual independent review PENDING).
Worker does not impersonate a Chief. `performance = NOT_RUN`.
Report: `docs/v2/integration/C3_R8_SUBJECT_CANDIDATE_SELECTION.md`;
durable evidence: `fixtures/c3-r8-subject-selection.json`.
Recommendation X012 mathematics / X023 chemistry is CANDIDATE_ONLY and both
CURRENT_CAPABILITY_BLOCKED. All three genuine math teacher sources were compared;
X012 retains formula-answer/shading blockers. X023 has112 dedicated marker
paragraphs without nontext, but no QG parent chain proves question ownership,
unsupported formatting remains and retained ` = 6 \* GB3 ` field is blocked.
Physical question total/full answer ownership remain NOT_ESTABLISHED. Existing
student companions are reference-only, not independent Golden. All frozen unit
spans are recorded, including7/28 complex endpoints; top-body context does not
flatten table ownership or authorize mutation. No full Golden, new expected DOCX,
removal ledger, source transformation, real derived UAT or broad pair inventory
was performed. Read-only source page counts are not open/save/reopen/PDF or visual
UAT. Current suite includes existing approved X008 API protection only.

| C3-R9 | 2026-10-01 14:00 UTC (first implementation file timestamp; predecessor rounds ended 2026-10-01 13:38:35 UTC) | 2026-10-01 14:27:27 UTC (commit `a836f2e`) | DeepSeek V4.1 Flash | fd5377bfb0d48125aba94f43fe11ed0a54a97936 | a836f2e6a1e415cfb24b0f6e8939af712fdaa7be | PASS: full `tests/` 351 passed + 7 subtests in 213.17s (327 before the round, +24 new); packaged manifest binds the approved X008 Golden and reproduces approved DOCX `67e0bc36…`; provider answers only for the exact digest; 14 malformed evidence variants refused; duplicate evidence for one digest refused; missing directory refused; unloadable registry fails closed and reports; supported path never calls `make_student`; unreviewed source falls back with no half-student; real renderer refusal persists the exact reason and hands the original teacher to the fallback; corpus 27/27 unchanged; no stray artifact in the corpus directory; `py_compile` and `git diff --check` (working tree and staged) clean | Codex GPT-6.1 Sol (required; PENDING) | PENDING | Item 2 (27-source capability scan) and item 3 (performance); no production activation change beyond the reviewed registry | Yes: implementation `a836f2e` committed and pushed; remote SHA verified equal |

Round 9 wires the already verified reviewed physical-range Studentizer into the
real production teacher-only route: reviewed coverage gate → XML Studentizer →
derived student source → A-Line → C1 Slot Router → B-Line XML Renderer, and
whole-job V0.9 fallback otherwise with a persisted reason. **New blocking
finding:** X008's retained front matter (`w:body` 3–13) holds 8 hyperlinks to 5
bookmark names that do not exist in the document (`_Toc9`, `_Toc67`, `_Toc3947`,
`_Toc21406`, `_Toc22623`, `_Toc29290`); the same inherited missing anchors the
Chief approval already recorded. The frozen B-Line projection refuses any
selected hyperlink with an unresolvable anchor and C1 routes that front matter
into `knowledge`, so the renderer refuses and the item correctly falls back. No
end-to-end COM-free teacher-only run is reachable on the only approved source.
This round makes no zero-COM, speed or completion claim.

| C3-R10 | 2026-10-01 14:30 UTC (scan tool creation; exact kickoff not captured) | 2026-10-01 15:01:54 UTC (commit `13f8e4b`) | DeepSeek V4.1 Flash | a836f2e6a1e415cfb24b0f6e8939af712fdaa7be | 13f8e4b386b3900a56a513ab05e71af7a87685ef | PASS: 5 new focused scan tests; total simulated/measured 27/27 sources read; production gate 1 supported / 26 fail closed with `STUDENTIZER_COVERAGE_UNPROVEN`; boundary verdicts 15 clear / 12 `STUDENTIZ_BOUNDARY_DEPENDENCY_UNSUPPORTED` (8 `txbxContent`, 2 `clrChange`, 2 unsupported field parameter); 4 sources carry unresolvable hyperlink anchors that the frozen renderer refuses; corpus hashes unchanged after the scan; `py_compile` and `git diff --check` clean | Codex GPT-6.1 Sol (required; PENDING) | PENDING | Item 3 (real performance), then full regression | Yes: scan tool, tests, evidence and report `13f8e4b` committed and pushed; remote SHA verified equal |

Round 10 is read-only statistics only. The scan deliberately separates the
authoritative production gate result from a diagnostic boundary-system verdict
obtained by calling the Studentizer's own validator with an empty removal set.
Measured reviewed coverage is 1/27. Low coverage is the expected outcome and was
not treated as a reason to add TOC/bookmark/OLE/textbox/table/field/hyperlink or
formula capability.

| C3-R11 | 2026-10-01 15:05 UTC (harness creation; exact kickoff not captured) | 2026-10-01 15:59:26 UTC (commit `af87809`) | DeepSeek V4.1 Flash | 13f8e4b386b3900a56a513ab05e71af7a87685ef | af87809a2ca6f62a407953f0d0795c5e2333b19c | PASS: 4 new harness tests (including a real end-to-end synthetic reviewed teacher-only run with 0 COM scripts, 0 `make_student`, 0 new office processes, `XML_PREPARED`, 2/2 packages valid); real production measurements for 6 cases; Stage2 39/39; fresh Stage3 QG 408/408 (P/R 100%, exact 87.7%), sections 369/369 exact 100%, subquestions 328/328, errors `{}` (E1–E4 0), MISS/FP/MERGE/SPLIT 0; full `tests/` 360 passed + 7 subtests in 199.78s; V0.9 frozen assets 10/10; corpus 27/27; `py_compile` and `git diff --check` clean | Codex GPT-6.1 Sol (required; PENDING) | PENDING | Chief/product decision on the teacher-only fallback route; no further scope | Yes: harness, sampler, tests, evidence and reports `af87809` committed and pushed; remote SHA verified equal |

Round 11 measures, it does not optimise. Reviewed-supported teacher-only path:
0.749 s, Studentizer 0.411 s, A-Line 0.064 s, Slot Router 0.011 s, renderer
0.155 s, validation 0.145 s, **COM 0, fallback 0** (synthetic reviewed source;
no approved source can complete the renderer). X008 teacher-only, same-source
workload: 1 item 25.568 s, 3 items 77.202 s, 5 items 129.138 s, all falling back
with `UNSUPPORTED_BOOKMARK_SCOPE` / `ProjectionError: selected hyperlink anchor
is missing or ambiguous: _Toc9`; 6 COM scripts and ~12 new office processes per
item. **Identical C2 Case A workload: 274.791 s versus the recorded 121.330 s
(+126%)**, because unreviewed teacher-only now runs the whole-job V0.9 fallback
(6 COM scripts per item) instead of C2's one-COM prepare plus XML render; the
`make_student` phase itself is unchanged (84.1 s versus ~87.2 s). **Identical
C2 Case B teacher+student XML batch: 11.768 s versus 13.975 s, no regression.**
One earlier full-suite run once reported 128 fixture errors; two subsequent
clean runs (356 and 360 passed) did not reproduce it, and this environment's
bulk-delete guard was observed to fail closed during pytest temporary-directory
cleanup, which is the most likely cause. No `C3_STUDENTIZER_PERFORMANCE_PASS`,
no tag, no EXE/installer/release work.

| C3-R12 | ~2026-10-02 01:25 UTC (restart-recovery repair; exact kickoff not captured) | 2026-10-02 01:54 UTC | GPT-6 Luna | 9fe4002c4dcf4a6da3be5781bc1afd13ff3a768e | 71b50740ebb785d77f2db01b15d5db4e42ffaed2 | PASS scoped restart/C3.5 gate: startup recovery clears only renderer intermediates inside an interrupted job's private work directory and requeues it; preserves uploaded inputs and published sibling results. Focused hardening + batch-service tests 19 passed; concurrent fallback max-active=1 gate 1 passed; py_compile and diff-check clean. Existing batch10, batch20, 10-job consecutive, abnormal-input, serial-fallback and queued restart-A evidence reused. Fresh restart-B killed 3 times at 5/20/30 seconds while persisted running; all resumed to done with 2 DOCX and clean output; the 30s interruption captured stale `teacher-output-<job_id>.docx` and resumed successfully after cleanup. Fresh batch restart-C killed with item 1 done and item 2 active/item 3 queued; all 3 completed, and item 1's two DOCX hashes were byte-identical before/after. No batch10/20 rerun. Independent Chief review pending; full final regression remains pending. | Codex GPT-6.1 Sol (required; PENDING) | PENDING | Continue full candidate gates and independent final review; no C3 final PASS/tag | Yes: scoped recovery/harness/report/evidence commit `71b5074` pushed; journal metadata follows |

Round 12 fixes the reproduced restart-B failure. The job service now removes
known generated renderer scratch from that interrupted job's private workspace
before requeue; it never targets uploaded inputs or published user results.
The restart harness records the persisted job state at kill time rather than
reusing the initial queued API response. The concurrent fallback gate observed
max-active=1 and restored the instrumented callable. C3.5 load evidence is inherited from
the prior candidate and preserved in `integration/fixtures/c3-c35/`; no large
load was repeated. No layered fallback or Studentizer production route changes
were made. C3 final gates and Chief review are still pending.

| C3-R12-PATCH | 2026-10-02 02:01 UTC (Chief PATCH follow-up) | 2026-10-02 02:20 UTC | GPT-6 Luna | 24477e2ddb6dc7e6915d3af2970381343d7d2e99 | 024f75b35c609a714cf6a632fa83f4b2921ba3ee | PASS scoped machine gate: replaced elapsed-only restart-B evidence with three persisted stage checkpoints. Killed while `V0.9 make_student preparation`, `V0.9 teacher renderer`, and `outputs ready; before publication`; all three recovered to done with two DOCX and clean user result folders. The before-publication case had both private outputs present at kill. Test-only hold hook is enabled only with Flask TESTING. Focused selection 20 passed; py_compile and diff-check clean. A, C, and prior load evidence reused. | Codex GPT-6.1 Sol | Initial PATCH; re-review PASS after the distinct-stage correction | Proceed with remaining final gates; no scope expansion | Yes: implementation/report/evidence commit `024f75b` pushed; this row records the PATCH follow-up |

The elapsed-only B@5/20/30 records remain archived but do not satisfy the
distinct-phase requirement. This follow-up adds persisted renderer/preparation/
publication stage names and a test-only checkpoint hook so the real process can
be killed at each phase after the job record is written. No generation or
fallback decision changed. No batch10, batch20, or consecutive stress case was
rerun. Do not repeat completed R1–R8 audits or Golden work.

R12 PATCH re-review: **Codex GPT-6.1 Sol — PASS**, scoped to the distinct-stage
restart-B evidence and recovery patch above. The initial R12 review remains
recorded as PATCH; this is the follow-up verdict, not a C3 final review.

| C3-R13 | ~2026-10-02 02:20 UTC (first implementation action; exact kickoff not captured) | 2026-10-02 02:59 UTC | GPT-6 Luna Goal Mode | 76ff54d3ce21b98c7d272c56a1276f632d7ced91 | c0ba484544ef8b2cea1c67a484313b48db174d8d | PASS: layered-route focus 51 passed; current full suite 394 passed + 7 subtests and 4 V1.1 legacy API failures; disposable base full suite 393 passed + 7 subtests and the exact same 4 failures. C2 Case A 5 teacher-only items 122.553s vs 121.330s (+1.01%), V09_MAKE_STUDENT 5/5 → XML 5/5, whole-job fallback 0, 10/10 packages valid, 10 COM scripts / 21 new office process instances; Case B 13.809s vs 13.975s (−1.2%), XML 3/3, COM/WPS 0; X008 approved Studentizer preparation remained XML/COM-free but frozen `_Toc` anchor caused renderer fallback; same-source 1/3/5 totals 27.960/82.630/137.585s (whole-job V0.9 after that refusal). Inherited capability 1/27 supported, no corpus sweep; py_compile and diff-check PASS. Stage2/Stage3 and C2 full regression remain final-gate work | Codex GPT-6.1 Sol | PENDING | Chief scoped R13 review, then continue final gates | Yes: implementation commit `c0ba484` pushed; remote full SHA verified equal |

R13 preserves the frozen Studentizer scope. Unsupported Studentizer sources now
use V0.9 `make_student` only to produce the student source, then share A-Line,
Slot Router, and XML Renderer. Whole-job V0.9 remains reserved for renderer / package
refusal. Per-source renderer totals across all 27 are not fully established by
the existing non-mutating capability scan. The R13 detailed performance report
separates student preparation mode from renderer route and states this limit.

| C3-R13-PATCH | 2026-10-02 03:05 UTC (approximate; scoped Chief PATCH repair start) | 2026-10-02 03:13 UTC | GPT-6 Luna Goal Mode | e20256837fe9f747665f5958ffdb4920d59314bc | 5fe77b68cfeb05bd174117e59a15bb4bd4aeed44 | PASS scoped metadata gate: production-registry, Studentizer integration, batch job and C0 job-service selections 80 passed; added engine-loader failure and pre-COM callable-entry failure coverage; app/job_service py_compile and diff-check clean. No performance, stress, broad corpus or OOXML work rerun. | Codex GPT-6.1 Sol | Original R13 PATCH; scoped re-review PENDING | Submit only the metadata truthfulness patch for independent review; no further Worker edits pending verdict | Yes: implementation `5fe77b6` committed/pushed; Journal metadata commit follows |

R13 PATCH distinguishes the selected `V09_MAKE_STUDENT` route from actual
`make_student` callable entry. A loader failure records the selected route while
leaving callable and COM/WPS flags false. After callable entry, COM/WPS is recorded
as unknown because entry can precede a failing non-COM `strip_red` phase; the
Studentizer refusal reason and elapsed timing remain persisted on exceptions.
No claim of observed COM/WPS startup is made by this patch.

| C3-R14 Final Machine Gates | ~2026-10-02 03:00 UTC (initial validation; exact kickoff not captured) | 2026-10-02 03:37 UTC | GPT-6 Luna Goal Mode | 99c243cfd05790d2ab640d9ea93e1a5e87a8449b | 021d98903707eb022650acf961047f373c20e552 | Scoped Stage2 runner fix: skip unindexed TOC container from local E2 ordinal scheduling; Stage2 focused 40/40; full four-source run completed with source hashes valid; Studentizer 143 passed; C2 batch/ZIP-input/partial/local delivery 85 passed; restart 7 passed; Stage3 QG 408/408, sections 369/369, subquestions 328/328, Recall 100%, E1-E4/MISS/FP/MERGE/SPLIT=0; V0.9 assets 10/10; corpus hashes 27/27; compile/JS/diff-check pass. Full suite 397 passed + 7 subtests with the same 4 known V1.1 legacy API failures recorded on R13 base/current; not full-suite PASS. C3.5 large stress/restart evidence reused from `C3_C35_STABILITY_REPORT_2026-10-02.md`; no rerun | Codex GPT-6.1 Sol | PENDING — submit machine evidence for final independent review | Review final gates and decide; no tag unless Chief PASS | Yes: scoped Stage2 evaluation-runner/test commit `021d989` pushed and remote SHA verified; machine report and Journal metadata commit follow |

R14 diagnosis: the S11 Stage2 runner crash also reproduced at R12 base
`71b50740ebb785d77f2db01b15d5db4e42ffaed2`; it was an unindexed TOC table
container candidate (`b2.r5c0.n8`) with no content-node ordinal, not a new C3
Splitter regression. Only the Stage2 evaluation runner and its test changed.
Final evidence is in `docs/v2/integration/C3_FINAL_MACHINE_GATE_2026-10-02.md`.
X008 Studentizer-stage counters are separated there from later whole-job V0.9
renderer fallback counters. Final Chief review remains pending; no C3 tag or
completion claim is made.

| C3-R15 Chief PATCH follow-up | ~2026-10-02 03:40 UTC (exact kickoff not captured) | 2026-10-02 03:56 UTC | GPT-6 Luna Goal Mode | 4a8ea86aeb95313e54cac74121c240dacbaa5d05 | effa4f56859a53b808736561ea0ad9c18ef9b74f | PASS scoped machine gate: Studentizer integration + restart harness 30 passed, including interruption after teacher publication and after both finals before done; X008-like XML Studentizer/refusal test proves preparation telemetry immutable and renderer fallback telemetry separate; `py_compile` and `git diff --check` PASS. No broad final gate, large stress, capability scan, Golden, or OOXML audit rerun. Existing exact-ID renderer participation deduplicated as XML 9 / V0.9 1 / unmeasured 17 across 27 source IDs; 8 XML logical items and 9 repeated X008 V0.9 item executions are separately identified | Codex GPT-6.1 Sol | PATCH follow-up re-review PENDING | Submit only scoped PATCH evidence for independent review; do not begin final gate until verdict | Yes: implementation commit `effa4f5` pushed and remote SHA verified; report/Journal metadata commit follows |

C3-R15 follow-up report: `docs/v2/integration/C3_R15_CHIEF_PATCH_2026-10-02.md`. The
renderer source denominator is derived only from previously measured C2 Case A/B
and X008 exact IDs; the C2 Case B denominator remains three logical pairs, not
six jobs. No broad gate was repeated and no final C3 PASS/tag is claimed.

| C3-R16 Post-PATCH final machine gates | ~2026-10-02 04:00 UTC (exact kickoff not captured) | 2026-10-02 04:12 UTC | GPT-6 Luna Goal Mode | 216a280a0bd0a3cc5d4da34f561d3e9f5005bcad | 216a280a0bd0a3cc5d4da34f561d3e9f5005bcad (candidate tested; no code change) | PASS scoped machine gates: full suite 399 passed + 7 subtests, with the same four pre-existing V1.1 API expectation failures; Studentizer 145 passed; C2 Batch/ZIP-input/partial/local 85 passed; restart recovery 7 passed; Stage2 tests 40 passed and four-source comparison completed (191/204/179 QG gold/predicted/correct; observed errors retained in report); protected Stage3 408/408 QG, 369/369 sections, 328/328 subquestions, Recall 100%, E1-E4/MISS/FP/MERGE/SPLIT=0; V0.9 assets 10/10; source hashes 27/27; py_compile, JS syntax, diff-check PASS. Reused R13 performance and C3.5 load evidence; no performance or large load rerun | Codex GPT-6.1 Sol | Pending final independent review; no C3 verdict claimed in this round | Submit current machine evidence and report for final Chief decision; no tag unless final Chief PASS | Yes: documentation-only report/Journal commit `1d615fddd0c824cae175ea1d47796a06790b8594` committed and pushed; remote matched |

Full post-PATCH details: `docs/v2/integration/C3_FINAL_MACHINE_GATE_2026-10-02.md`.
The four full-suite failures are the same V1.1 legacy API expectations seen on
the R13 base/candidate; the repository-wide suite is not reported as all-green.
This round made no production change and did not repeat R1-R8, any Golden,
performance workload, or C3.5 large stability workload.

| C4-R1 Release Audit | ~2026-10-02 04:40 UTC (audit start approximate) | 2026-10-02 04:44:30 UTC | GPT-6 Luna Goal Mode | 8009f9a40afdce912647e8ed391d2d4fe381bc72 | 3ceb3a4dd9337530faa25885ae405fba5ae112cb | PASS (documentation/static consistency only): `git diff --check`; 11/11 cited source paths exist; V0.9 manifest parses and lists 10 assets; no build or tests run. Audit identified unresolved onedir resource-root and `%TEMP%` redirection requirements. | Codex GPT-6.1 Sol | PENDING — not invoked in this Worker round; audit requires independent review before packaging | Submit `docs/v2/release/C4_RELEASE_AUDIT.md` for Chief review; do not build/package before PASS | Yes: audit report commit `3ceb3a4` pushed and remote verified; Journal metadata commit follows |

C4-R1 is a read-only source/runtime audit. Current Python shell resolved to a
Hermes-managed CPython 3.11.15 with no Flask installed; PyInstaller was not
available. These are environment observations, not a release package result.
The report distinguishes verified code paths from packaging recommendations
and records that no EXE/package, launch, port-conflict, Chinese-path, or RC UAT
gate has yet run.

| C4-R1 PATCH follow-up | 2026-10-02 04:49 UTC | 2026-10-02 04:50 UTC | GPT-6 Luna Goal Mode | 1c0e31111484ecf71f44ff271825517af3c5dff5 | 2e1a37a3faeeaf6db9e45cf3fccef22f103eade4 | PASS scoped documentation gate: `git diff --check`; corrected bytecode-cache write risk for both dynamic source-file loaders and exact V0.9 manifest provenance. No code, build, or tests changed/run. | Codex GPT-6.1 Sol | Initial PATCH; correction pushed; re-review PENDING | Submit corrected audit for GPT-6.1 Sol re-review; do not package until verdict | Yes: audit correction commit `2e1a37a` pushed and remote verified; Journal metadata commit follows |

C4-R1 initial Chief verdict was PATCH on two audit inaccuracies: packaged
resources were described as unconditionally read-only despite `.pyc` cache
writes possible from `semantic_facade._load_predictor()` and
`renderer_orchestrator._load_v09_engine()`, and `.gitattributes` was incorrectly
presented as part of the ten-entry V0.9 asset manifest. The audit now records
both facts and requires disabling Python bytecode writes before app imports or
dynamic loads. Chief re-review is pending; no implementation, build, or test
work was authorized or performed in this PATCH follow-up.

| C4-R2 Launcher/runtime boundary | 2026-10-02 04:57 UTC (launcher implementation file created) | 2026-10-02 05:04 UTC | GPT-6 Luna Goal Mode | b423a783ce42d573762e5081e96b9c7cd5486101 | 616c352a51f22e9ff19f6199ff82989f457522cf (implementation; journal metadata commit follows) | PASS focused gate: 8 launcher tests passed, including actual server child startup/identity probe/ready/explicit shutdown; mutex single-instance on Windows; occupied-port fallback selects the actual bound alternate port; Known Folder redirect path; LOCALAPPDATA TEMP/TMP/TMPDIR, result/jobs roots, bytecode disabled before app import; py_compile, JS syntax, staged diff-check pass. No EXE build, full package, RC UAT, WPS test, or C4 PASS. | Codex GPT-6.1 Sol | PENDING — independent C4-R2 review required | After Chief PASS, continue release-engineering work within reviewed boundaries; do not claim package/RC readiness from source smoke | Yes: implementation commit `616c352` pushed and remote verified; Journal metadata commit follows |

C4-R2 adds a `.pyw` GUI-mode bootstrap suitable as a future windowed/onedir
entry, with single-instance mutex, loopback bind at 5128 or the server's actual
OS-assigned fallback port, nonce-authenticated ready identity, browser open,
and a token-gated Settings exit action that gracefully stops the backend.
Before importing the Flask app or dynamic loaders, the server process redirects
TEMP/TMP/TMPDIR and runtime roots to `%LOCALAPPDATA%\讲义生成器`, disables
bytecode writes, and resolves the actual Desktop Known Folder for final results.
The server-child smoke starts without requiring WPS; it does not exercise a
WPS-dependent fallback job. No A/B/C3 or V0.9 asset was changed. The Journal
metadata commit follows implementation `616c352`.

| C4-R2 PATCH (launcher bind/reuse) | 2026-10-02 05:08 UTC | 2026-10-02 05:14 UTC | GPT-6 Luna Goal Mode | 25aba023fde43a4e0d1c218150956dc7257a1dbc | e38b507be0fe505bc05581f8a6a8905e01e0ed8c | PASS scoped machine gate: 11 launcher tests passed, including real Werkzeug occupied-port SystemExit fallback to the actual alternate port without contacting the unrelated listener; authenticated second-launch URL reuse; stale and unavailable-state feedback. py_compile, workspace.js Node syntax check, and diff-check PASS. No EXE build or full UAT. | Codex GPT-6.1 Sol | PATCH implementation pushed; scoped re-review PENDING | Obtain independent Chief re-review of only these two blockers; do not build/package until PASS | Yes: implementation `e38b507` committed, pushed, and remote verified; journal metadata commit follows |

C4-R2 PATCH addresses only the two Chief blockers. Werkzeug bind `SystemExit` now falls back only when a separate loopback bind probe confirms the requested port is unavailable; other startup failures propagate. The mutex owner atomically publishes a private current-instance record under LocalAppData, and a second launcher opens only the ready URL authenticated by that record's token. Stale process state and missing/not-ready state produce explicit feedback. Windows process liveness uses `OpenProcess`/`GetExitCodeProcess`, avoiding signal-based termination semantics. No EXE build, package, or full UAT was run; no frozen V0.9 or business behavior changed. Chief re-review is pending.

| C4-R3 Windows onedir build + startup smoke | ~2026-10-02 05:13 UTC | 2026-10-02 05:50 UTC | GPT-6 Luna Goal Mode | 59b074b17e842fd57f6484b9176d476dcafe3274 | 9213977649fce8e2f5f6047c90bd2ef0323f8b1d | PASS scoped packaging gate: CPython 3.12.10 x64 clean venv; exact pinned Flask/lxml/python-docx/PyInstaller closure; 194-file onedir inventory, 36,167,421 bytes, tree SHA-256 ac70b3bfe8950b33ae5a80b316a8ec7b84b73609f1651c74e91bacea7f0a6fcd; EXE SHA-256 d51bf225233f8de173bb64ed3457cafa62cb1aab0496994ec5ea019eb7a00e7f; V0.9 assets 10/10 preserved. Desktop Chinese+spaces copy started outside repository/C:\xml-uat with Python/venv absent from PATH; authenticated ready at 127.0.0.1:5128, root/CSS/JS/jobs HTTP 200, authenticated exit 0 and ready record removed. Launcher focused tests 12 passed; py_compile launcher/spec, JS syntax, diff-check passed. Edge tab visual verification unavailable because browser connector fetch failed; no generation/WPS/RC gates run. | Codex GPT-6.1 Sol | PASS — scoped review of commit 9213977; this is not an RC PASS | Proceed with the next C4 release-engineering gate; retain the recorded limits and do not infer RC readiness | Yes: implementation commit 9213977 pushed; remote branch SHA matched; this Journal row is a documentation follow-up |

C4-R3 details are in `docs/v2/release/C4_R3_ONEDIR_BUILD_AND_STARTUP.md`. The external package and per-file inventory remain at `C:\xml-uat\c4-r3-output\`; the isolated Desktop smoke copy is retained for inspection. This round proves launcher startup and packaged web resource serving only. It does not prove generation, WPS/Word, browser visual/UAT, fallback jobs, restart or RC readiness.

| C4-R4 release identity correction | 2026-10-02 06:58 UTC (approximate; user-authorized final RC work) | 2026-10-02 07:05 UTC | GPT-6 Luna Goal Mode | bdbbd497820f809ed04578083d7699166dcddd69 | 5646dfad6675e7c04de2d438fca7eb2123cfee55 | PASS scoped identity gate: `tests/test_windows_launcher.py` 12 passed, covering rendered page title, sidebar brand, and settings version as `讲义生成器 V1.2`; `git diff --check` PASS. No build or UAT in this round. | Codex GPT-6.1 Sol | NOT REVIEWED — worker implementation commit only | Build a new final RC package from `5646dfa` into a separate output root; do not reuse R3 EXE | Yes: implementation commit `5646dfa` pushed; remote branch matched |

| C4-R3 PATCH — cross-volume final DOCX publication | 2026-10-02 06:10 UTC (approximate; patch work began after supplied EXE failure evidence) | 2026-10-02 06:18 UTC | GPT-6 Luna Goal Mode | 9f7569b3a28d09a59e844a4bc5131ba5acfc23cf | 8a71d197037e40b32b15942418808f138fc3541a | PASS scoped machine gate: publication/restart cases 5 passed; C0 job service + Batch + Studentizer integration 58 passed; changed Python `py_compile`, `workspace.js` Node syntax, and diff-check PASS. Simulated direct cross-volume `WinError 17`; verified target-directory temp replace for teacher/student, failed package validation cleanup, successful sibling retention, and orphan temp cleanup on restart. No package build or EXE/browser/Word/WPS/whole-run UAT. | Codex GPT-6.1 Sol | Original PATCH; re-review PENDING | Submit publication-only fix and evidence for independent Chief re-review | Yes: implementation `8a71d19` and report/Journal `330b6bb` pushed; remote branch verified at `330b6bb6d8ed08ccb2af126c1c6e48a2b414b993` |

C4-R3 PATCH responds to the supplied job `ee4a1afacb6b46d39d9fa414569d16a5`
failure: Windows rejected moving staged output from `C:` to redirected Desktop
results on `D:` with `WinError 17`. The final publisher now copies into a
job/role-specific temporary file inside the result directory, checks size,
SHA-256, and DOCX package validity, then atomically replaces the final target
from that same directory. Failed copies are cleaned; restart removes only
job-specific orphan publication temps and preserves valid published siblings.
Evidence is in `docs/v2/release/C4_R3_PUBLICATION_PATCH_2026-10-02.md`. The
worker did not run packaged, browser, Word/WPS, or whole-run UAT in this patch.

| C4-R3 PATCH follow-up — restart hash rebinding | 2026-10-02 06:19 UTC (approximate; Chief blocker received after prior push) | 2026-10-02 06:27 UTC | GPT-6 Luna Goal Mode | b09df4676db7d07b14b53835960c2efda62e623f | 6ec7b6a2ec0d168ac874a0359f961b24ed56df39 | PASS scoped machine gate: C0 job service + Batch + Studentizer integration 59 passed; added valid DOCX ZIP-metadata-change restart case; changed Python `py_compile`, `workspace.js` Node syntax, and `git diff --check` PASS. Published teacher sibling remained byte-identical; absent student target rebound to new validated staging SHA; no temp remained. No EXE/package/browser/Word/WPS/whole-run UAT. | Codex GPT-6.1 Sol | PASS — scoped review by Codex GPT-6.1 Sol | Await user direction on whether to resume remaining C4 package/browser/WPS UAT; no UAT or tag without user direction | Yes: implementation `6ec7b6a` and evidence/Journal `6f2252e` pushed; remote branch verified at `6f2252ef6a074f6c20397f864435d6cede1dc29f` |

This follow-up addresses only the restart hash blocker from Chief review. The
publication plan refreshes an expected SHA only for a role not listed as
published whose final path is absent. Existing final files and published
hashes remain immutable and subject to strict adoption checks. Evidence is in
`docs/v2/release/C4_R3_RESTART_HASH_PATCH_2026-10-02.md`.

| C4 Final RC UAT evidence closeout | 2026-10-02 07:07 UTC (package build began; evidence timestamps are local +08:00) | 2026-10-02 08:34 UTC (latest retained UAT evidence) | GPT-6 Luna Goal Mode | bdbbd497820f809ed04578083d7699166dcddd69 | f095147ab09a6ded718443e03c42f473766a2b38 | BLOCKED: onedir startup/package inventory and UI generation records exist; pair, teacher-only, student-only, multi-DOCX, Chinese ZIP/partial-corrupt, and V0.9 fallback paths have browser-submitted job records; cross-volume outputs on D: and package validation recorded; restart B/C final records; WPS open/save/close/reopen/PDF passes for sampled outputs; 10/10 start/exit records; Stage3 408/408, 369/369, 328/328, Recall 100%, zero MISS/FP/MERGE/SPLIT. Release gate fails because WPS page images show stale math/grade/topic template headers for selected high-school chemistry; Restart A queued-state capture absent; RC ZIP/exclusion audit and complete post-UAT regression recertification absent. Package inventory evidence does not bind a source SHA, so binary-to-HEAD identity is not independently attested. | Codex GPT-6.1 Sol | PENDING — final independent review not yet performed | Resolve the stale template header blocker and Restart A evidence status through Chief direction; do not create release tag without Chief PASS and remaining release gates | No: this evidence/reporting turn made no commit or push |

C4 final UAT evidence report: `docs/v2/release/C4_FINAL_RC_UAT_2026-10-02.md`. Raw package, job, WPS and startup-cycle artifacts remain under `C:\xml-uat\c4-final-rc`. This record does not claim `C4_WINDOWS_RC_PASS`; the report distinguishes WPS roundtrip mechanics from failed visual template correctness. The 7 acceptance dimensions include ZIP input and partial success as separate checks on the same ZIP submission; the explicit V0.9 fallback was exercised inside the multi-DOCX batch, not as an eighth upload. No source fix, new UAT, RC ZIP, commit, push, Chief review, or tag was performed in this closeout.

| C4 post-UAT regression and package path audit | 2026-10-02 08:36 UTC (approximate; exact kickoff not captured) | 2026-10-02 08:50 UTC | GPT-6 Luna Goal Mode | f095147ab09a6ded718443e03c42f473766a2b38 | f095147ab09a6ded718443e03c42f473766a2b38 | PASS for executable non-pytest checks: Stage2 four-source output reproduced prior prediction units (QG Gold/pred/correct 191/204/179; known S01/S11 GoldCompare FAIL retained); Stage3 all hashes match, QG 408/408, sections 369/369, subquestions 328/328, zero MISS/FP/MERGE/SPLIT; V0.9 frozen assets 10/10; source hashes 27/27; py_compile, JS syntax; onedir 194/194 files with zero forbidden paths; candidate archive 194 entries match inventory size/hash, zero forbidden paths. Pytest launcher/publication+restart/C2/C3/Stage2 suites NOT RUN: mandated build venv lacks pytest and command exits before collection. No code changes, new UAT, packaging, commit or push. | Codex GPT-6.1 Sol | PENDING — final review not performed | Preserve the outstanding WPS header blocker, Restart A evidence gap and unverified pytest groups; proceed only through authorized Chief review and remaining release gates | No: evidence-only updates to report and journal; no commit/push |

Supplemental machine evidence and exact command outcomes are recorded in `docs/v2/release/C4_FINAL_RC_UAT_2026-10-02.md` under “Post-UAT verification”. Candidate archive details: 19,013,293 bytes, SHA-256 `b8b1f458564f0f18bd11573f525acc8fc680ab56ca7df3bdc8231c432104ea69`; it is not the final RC ZIP and its build SHA remains unattested. No final PASS or tag is authorized by this row.

| C4 focused pytest follow-up | 2026-10-02 08:50 UTC | 2026-10-02 08:52 UTC | GPT-6 Luna Goal Mode | f095147ab09a6ded718443e03c42f473766a2b38 | f095147ab09a6ded718443e03c42f473766a2b38 | PASS: same combined launcher, C0 publication/restart, C2 batch/ZIP/partial/local, C3 Studentizer, C3.5 restart, and Stage2 focused selection executed with the existing `C:\xml-uat\.venv`; 293 passed in 91.06s, zero failures. No baseline-known or new regressions in this selected suite. This supersedes the interim note that pytest was unavailable in the PyInstaller build venv; the build venv itself remains without pytest. | Codex GPT-6.1 Sol | PENDING — final review not performed | Retain earlier limits: full repository suite not run, Stage2 GoldCompare S01/S11 observations remain, WPS template header blocker and Restart A gap remain; no tag without all release gates and Chief PASS | No: evidence-only report and journal additions; no code change/commit/push |

Exact command and scope are recorded in `docs/v2/release/C4_FINAL_RC_UAT_2026-10-02.md` under “Follow-up: focused pytest rerun in existing UAT venv”.

| C4 Restart A and package-audit evidence follow-up | 2026-10-02 09:02 UTC (queued observation; inherited handoff record) | 2026-10-02 09:07 UTC (Restart A evidence captured; approximate) | GPT-6 Luna Goal Mode | f095147ab09a6ded718443e03c42f473766a2b38 | f095147ab09a6ded718443e03c42f473766a2b38 | PASS scoped Restart A outcome: running job `4e09ef191dfc414baa638500fd3e1a1d` recovered to done, attempts=2, recovered_after_restart=true; queued job `af94bfbd89164024b59fd6e820b6adec` observed queued immediately before shutdown then done, attempts=1. Both final result directories contained only expected non-empty, DOCX-package-valid files; CRC/required-entry validation 3/3; no duplicate/temp; port 5128 released and zero RC processes remained. Queue pre-stop observation is from handoff record, not raw retained snapshot. Candidate ZIP/path audit exist; limited secret pattern scan 43 text assets, 0 matches (not comprehensive binary analysis). | Codex GPT-6.1 Sol | PENDING — final review not performed | Restart A executed with noted evidence limitation; retain the stale WPS header blocker, candidate-not-release status, and full repository suite not run; no tag without remaining gates and Chief PASS | No: evidence-only report and journal additions; no code changes/commit/push |

Restart A, candidate archive/path audit, and limited secret-scan disposition are detailed in `docs/v2/release/C4_FINAL_RC_UAT_2026-10-02.md`. The previous interim notes that Restart A was not executed and the selected pytest groups were unverified are superseded; the full repository test suite remains unrun. Candidate archive is not an official RC ZIP; no release PASS or tag is claimed.


| C4-P0-R1 recursive output root-cause report | 2026-10-02 14:12:29 UTC | 2026-10-02 14:30:47 UTC | Codex GPT-6 | 8c3a3d595e903570575a85ff497d6ddc5a91234b | ad472c58237ae7a435d3d5bdc77aef42b8a1b59d | PASS: read-only lineage reconciled Restart C job/ZIP/input/output hashes and paragraph/template counts; report-only `git diff --check` PASS. No new generation, WPS, restart, or regression tests run. Chief PASS applies to root-cause report only. | Codex GPT-6.1 Sol | PASS — mixed cause confirmed: prior V0.9 generation added template sequence 1→2, then Restart C re-ingested the published output and produced 3; release remains blocked | Begin only a scoped provenance/content-integrity fix after root-cause approval; keep C4 Release paused and do not create a tag | Yes: report commits `555b554`, `97f6404`, `ad472c5` pushed; remote branch verified at `ad472c58237ae7a435d3d5bdc77aef42b8a1b59d`; this journal record is committed separately |

| C4-P0-R2 product integrity implementation | ~2026-10-02 14:43 UTC | ~2026-10-02 15:07 UTC | Codex GPT-6 | e44c78260762ca09224630a4f1c890c00a3a7e11 | d1a1cf60bdfa996dd5a86af44d404952386a0b4a | PASS scoped machine gate: 66 focused C0/Batch/Studentizer/product-integrity tests; py_compile and diff-check PASS. No release, WPS, restart, or full-suite work. | Codex GPT-6.1 Sol | PATCH — final/adopted output hash binding, input SHA recheck, title occurrence count, and single endpoint resolution required | Fix only the four Chief blockers; keep C4 paused | Yes: implementation commit pushed; remote matched at d1a1cf60bdfa996dd5a86af44d404952386a0b4a |

| C4-P0-R3 Chief PATCH closure | ~2026-10-02 15:07 UTC | ~2026-10-02 15:15 UTC | Codex GPT-6 | d1a1cf60bdfa996dd5a86af44d404952386a0b4a | 0a6843529681ef81b5176846da8ced02cdfb75c9 | PASS scoped machine gate: 70 focused C0/Batch/Studentizer/product-integrity tests; py_compile and diff-check PASS. Covered provenance binding, literal title occurrences, bN single endpoints, and final/adopted output validation. | Codex GPT-6.1 Sol | PATCH — close final output hash time-of-check/time-of-use window | Verify candidate, gate-reported, and current output hashes; preserve changed files on cleanup | Yes: implementation commit pushed; remote matched at 0a6843529681ef81b5176846da8ced02cdfb75c9 |

| C4-P0-R4 final hash binding | ~2026-10-02 15:16 UTC | 2026-10-02 15:20:48 UTC | Codex GPT-6 | 0a6843529681ef81b5176846da8ced02cdfb75c9 | e6c921aa84994aba27acbb511eac4872f5c1fb31 | PASS scoped machine gate: 72 focused C0/Batch/Studentizer/product-integrity tests; py_compile and diff-check PASS. Added two mutation-window tests. No WPS, restart pressure, package/release, or full repository suite. | Codex GPT-6.1 Sol | PASS — final file must match candidate hash, gate-observed hash, and fresh current hash; changed files are retained | P0 implementation reviewed; keep C4 Release paused pending separate authorized release work | Yes: implementation commit pushed; remote matched at e6c921aa84994aba27acbb511eac4872f5c1fb31 |

P0 repair report: `docs/v2/release/C4_P0_RECURSIVE_OUTPUT_FIX.md`. These review verdicts cover only the cited implementation commits and scoped gates; the C4 release gate remains blocked.

| C4-P0-R5 retained real incident file gate audit | ~2026-10-02 15:21 UTC | 2026-10-02 15:26 UTC | Codex GPT-6 | 0eab118766964becde726268216f6bdf96f3c973 | 71f1abc8ec0acde07356f5d9904cb3066f54a080 | PASS read-only evidence gate: verified current SHA-256 and PRODUCT_INTEGRITY_GATE metrics on original X012, prior V0.9 output, Restart C input, and actual Restart C teacher/student outputs. Clean source accepted; prior/generated inputs and both incident outputs rejected. No regeneration, WPS, Restart execution, package, or regression suite. | Codex GPT-6.1 Sol | PASS — file hashes and counts agree with root-cause evidence; report states the limits and keeps C4 paused | Close P0 root-cause task; do not resume C4 Release or create a tag | Yes: evidence report commit pushed; remote matched at 71f1abc8ec0acde07356f5d9904cb3066f54a080; this Journal update follows |

| Training-only deterministic routing + XML fallback coverage | 2026-10-05 14:28:23 UTC (handoff verification start; implementation was inherited) | 2026-10-05 14:31:52 UTC | GPT-6 continuation; original implementation worker unverified | d89b2abeb19f5394b2257c3d515d0784f031948a | 50263a2d9cadf2037747392eecc356a06d7795c3 | PASS scoped machine gate: router/job-service focused tests 40 passed; changed Python py_compile and `git diff --check` passed. Inherited real paired-source XML + Product Integrity + package validation + WPS roundtrip evidence; 27-source observed audit 21 XML success / 2 fallback candidates / 4 pre-render rejects, no V0.9 fallback execution. Existing Stage3 408/408 QG, 369/369 sections, 328/328 subquestions, zero MISS/FP/MERGE/SPLIT; Stage2+GoldCompare focused 64 passed, separate runner S01/S11 observations retained. | Codex GPT-6.1 Sol | CHIEF_UNAVAILABLE — no GPT-6.1 Sol review was performed; no Chief PASS is claimed | Continue only with an explicitly scoped follow-up; preserve fail-closed table boundary and do not interpret corpus route candidates as fallback UAT | Yes: implementation/report commit `50263a2` pushed; remote verified at `50263a2d9cadf2037747392eecc356a06d7795c3`; journal metadata commit follows |

| Final Polish R1 — fixed first-page cover and safe display numbering | approximately 2026-10-05 14:57:24 UTC (earliest retained WPS helper timestamp; exact implementation start unavailable) | 2026-10-05 15:46:29 UTC | Codex GPT-6 (continuation; inherited implementation model not independently attested) | 687fd9d650533edbc320227cdd6934f8d6a6abc9 | 198509971a0d338d2dfc3790cfe8e3dadecabf04 | PASS scoped machine/product gate: final focused tests 60 passed in 11.93s; changed Python py_compile and diff-check PASS. Retained actual production paired-source jobs for both templates; 12/12 DOCX WPS Open/SaveAs/Close/Reopen/PDF PASS; all review titles on page 1, maximum baseline delta 1.441pt; all 260 teacher / 141 student payload blocks conserved, identical slot numbering 1–8 / 1–8 / 1–18, 34 questions. Continuation corrected fallback numbering evidence only and reran focused tests; no repeated real UAT. | Codex GPT-6.1 Sol | CHIEF_UNAVAILABLE — no independent Chief invocation or verdict; product PASS is not Chief PASS | Await user direction; retain frozen boundaries and do not enter release/tag/EXE work | Yes: implementation/tests/report/evidence commit `1985099` pushed; local and remote verified at `198509971a0d338d2dfc3790cfe8e3dadecabf04`; this Journal metadata commit follows |

Evidence: `docs/v2/integration/FINAL_POLISH_FIRST_PAGE_AND_RENUMBER_2026-10-05.md`
and `docs/v2/integration/fixtures/FINAL_POLISH_GATE_2026-10-05.json`.
The real frozen templates place the review title around mid-page; the implementation
retains that measured baseline rather than inventing a footer position. WPS
re-encodes some images on SaveAs, so post-WPS image byte/pixel identity is not
claimed. No full Stage2/Stage3, new Studentizer coverage, release, EXE, restart,
performance test, or tag is claimed in this round. Later V0.9 fallback preserves
the canonical diagnostic numbering map but records `applied=false` with
`DISPLAY_RENUMBER_NOT_APPLIED_FALLBACK`.

| Product consistency R1-R3 continuation closeout | ~2026-10-06 03:50 UTC (inherited implementation; exact start not retained) | 2026-10-06 05:43 UTC | Codex GPT-6 continuation; inherited implementation author not independently attested | 8aa513248cfd557d68583ac2cf7e210449bdd571 | b802ce074bd2744fd1a0cec30b60fb6093beb142 | PASS scoped: full pytest 469 passed + 13 subtests, 6 known environment/frozen V1.1 failures; final focused 8 passed + 6 subtests; Stage2 focused 40 passed (GoldCompare S01/S11 known FAIL; source corpus absent for fresh GoldCompare); Stage3 QG408/408, sections369/369, subquestions328/328, zero MISS/FP/MERGE/SPLIT; current 27-source hashes 27/27 and XML/package 24/27; WPS current XML/V0.9 routes 6/6; V0.9 hashes 10/10; py_compile, JS syntax, diff-check PASS. Exact incident job 72cab source was not replayed. | Codex GPT-6.1 Sol | PENDING — independent review dispatched | Review commit b802ce0; no PRODUCT_CONSISTENCY_FIX_PASS, no C5 branch, and no C4 release/tag until Chief verdict and incident-source evidence boundary are resolved | Yes: implementation/report commit b802ce0 pushed; remote verified equal; this Journal entry is metadata follow-up |
| Product consistency R1 PATCH: table ownership from top-level QG | 2026-10-06 05:45 UTC | 2026-10-06 05:54 UTC | Codex GPT-6 continuation (GPT-6 Luna worker variant unavailable in this continuation) | f0e650ea6124f679c6811d0d90a08f43c1e836cf | 2c84aa4b1f6f91239f428f1f604e0afdb1d50843 | PASS focused: new measurement-table/false-section regression plus existing table conflict cases; test_slot_router 21/21; py_compile and diff-check PASS. No full 27-source rerun or exact incident-source replay claimed. | Codex GPT-6.1 Sol | PATCH received on b802ce0; PATCH commit pushed; re-review pending | Chief to independently review 2c84aa4; if PASS, resolve original incident-source evidence gap before any final status; no C5, C4 release, or tag | Yes: code/report commit 2c84aa4 pushed; Run Journal follow-up remains to commit/push |
| Product consistency R1 PATCH 2: bound route repair to cell-label interval | 2026-10-06 05:55 UTC | 2026-10-06 06:00 UTC | Codex GPT-6 continuation (GPT-6 Luna worker variant unavailable in this continuation) | 395668d9172bd344d2cefcfbbc7fdaf9d5261e89 | 6bd968b1b4e07b07b2b94e4124c5e19198a84128 | PASS focused: single-table owner fixture, double-table explicit-final conflict fixture, atomic multi-slot and mixed-heading fail-closed; test_slot_router 22/22; py_compile and diff-check PASS. No full 27-source rerun or exact incident-source replay claimed. | Codex GPT-6.1 Sol | PATCH received on 2c84aa4; second PATCH commit pushed; re-review pending | Chief to review 6bd968b; then keep incident-source replay and broad-gate gaps explicit; no C5, C4 release, or tag | Yes: code/report commit 6bd968b pushed; Run Journal follow-up remains to commit/push |

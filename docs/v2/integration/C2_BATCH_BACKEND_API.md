# C2 Round 3 — Persistent Backend Batch Integration

Worker: GPT-6.1 (`gpt-6.1-sol`). Base:
`c44b2279fd7e516f770edf8128500d57b9970d16`.
Round 2 Input Resolver Chief review returned PASS. Round 3 Chief returned PATCH
for a concurrent first-submission executor race. Round 4 fixes that race;
independent review is pending. This scoped backend gate is not `C2_BATCH_PASS`.

## Production behavior

`POST /api/jobs` retains the C1 path for one DOCX or an explicit teacher/student
pair. Three or more uploaded files, or any ZIP input, use the reviewed batch
resolver. A ZIP containing one or two logical topics is also a batch.

The service persists a batch parent and one internal child job per valid logical
item. Each child uses the existing C1 input semantics, Slot Router, XML-first
rendering and item-specific V0.9 whole-job fallback. Resolver failures and
child-creation failures are persisted as failed items. A fallback never changes
the renderer decision for other items. Children are hidden from the job-list
endpoint to avoid duplicate user tasks.

Items run **serially**, including teacher-only `make_student` and V0.9 fallback.
The production job executor has one worker. No concurrent XML optimization is
introduced in this round, and frozen COM code is untouched.

Round 4 makes executor lookup, creation and registration atomic under the
existing submission lock. Concurrent first submissions cannot create separate
one-worker executors and overlap COM jobs.

Each item exposes topic, input version, teacher/student source paths, status,
renderer, fallback reason/detail, output paths, error, original ZIP provenance,
student preparation events, elapsed seconds, and slot/package reports. Aggregate
metadata includes total, completed, failed, current topic, produced files,
result directory, output paths and download availability.

Final outcomes are:

| Status | `batch_outcome` | Delivery |
|---|---|---|
| `done` | `ALL_SUCCESS` | All validated item outputs |
| `partial` | `PARTIAL_SUCCESS` | Valid successful item outputs remain available |
| `error` | `ALL_FAILED` | No successful outputs to download |

Done/partial is established from validated child outputs. Read/restart recovery
checks children independently. An output missing from one item invalidates that
item and leaves valid siblings intact. An interrupted parent is requeued and
skips completed children when resumed.

The parent directory contains readable topic subfolders with DOCX only. ZIP
input directory structure stays in runtime metadata. Same-topic separate items
receive unique readable folder suffixes; ZIP delivery preserves those result
subfolders, preventing duplicate archive entry names. `/api/open/<job_id>` opens
the parent result folder. Download is available for done and partial batches;
download failure cannot turn valid generated files into generation failures.

## Machine Gate

`pytest tests/test_batch_job_service.py tests/test_c0_job_service.py tests/test_batch_inputs.py tests/test_input_versions.py tests/test_stage2_baseline.py -q`

Result: **109 passed** (11 batch backend API/service cases, 19 existing C0/C1
service cases, 34 resolver cases, 6 input classification cases, Stage2 39/39).

Round 4 result: **110 passed**, adding an actual asynchronous concurrent-first-
submission test. Eight simultaneous entrants share one real executor. The test
holds construction to expose the old race, then holds the first callback while
all submissions complete. It proves one executor was created, maximum in-flight
callbacks is one, all eight jobs run, and pending state is cleared. The test
controls scheduling with barriers/events; it does not invoke COM.

API tests use valid DOCX packages with **synthetic renderer/COM callbacks**.
They prove persistence and per-item orchestration through the real HTTP/job
boundary; they do not claim real XML rendering, WPS or V0.9 execution.

Covered cases: three supplied teacher/student pairs; two successes beside a
damaged DOCX; three XML items plus one forced fallback; failed fallback beside
valid siblings; Chinese nested ZIP with all three input versions; all-failed;
missing-output recovery; interrupted-parent recovery skipping completed work;
same-topic separate mode with unique ZIP entries; current topic/progress in
serial source order; and isolated child-creation failure.

Paired and student-only items never invoke the synthetic `make_student` callback;
teacher-only calls it once and records elapsed time and invocation flags. The
forced fallback fixture records explicit `XML_RENDER_FAILED` plus the precise
`UNSUPPORTED_BOOKMARK_SCOPE` detail for the affected item only.

The C0 test formerly asserting three-file rejection now asserts the authorized
batch acceptance. All single/pair classification, invalid single-input handling,
local result validation and delivery tests continue to pass.

## Remaining C2 Gates

Frontend batch controls/progress, real Cases A–F, real WPS product UAT, the
V0.9 performance comparison, actual WPS/COM process counts and fresh protected
Stage3 regression remain outstanding. This round changes no A-Line source,
B-Line renderer core, V0.9 frozen asset or C1 Business Rules file.

# C0 Integration Contract Audit

**Round:** C0 Round 1 — Integration Contract Audit
**Audited branch / base:** `feature/v1.2-c-line-integration` / `eae89ea8720b94d29a94fc652830de628f373cd9`
**Audit type:** source-only contract audit; no pipeline implementation and no frozen component changes.

## Finding

The current tree does **not** expose a production-callable V1.2 A-Line Splitter/StructDoc entry from `v1.2-xml-experiment/res/app`. There is a callable `predict(doc)` in `tools/stage2_baseline/run_baseline.py`, but the Stage3 evaluator imports it from the tools directory to generate evaluation predictions. The V1.2 webapp does not import or invoke it. Therefore it is usable Python code, but it is not yet a production application entry and must not be represented as one.

`predict(doc)` returns semantic units with `id`, `role`, optional `level` / `parent` / `bind_to`, node-ID `spans`, and an evidence note. Span endpoints use StructDoc/NodeIndex node IDs, not Word COM paragraph numbers. The labels are content semantics (`section`, `question_group`, `shared_material`, `answer`, `analysis`, etc.); there is no implemented mapping from those units to template slot markers or `TemplateTarget` positions.

The B-Line renderer and orchestration code are individually callable, but there is no application route connecting uploaded files → StructDoc → prediction units → a renderer block plan → XML/fallback → job state and result delivery. The current v1.2 `/api/jobs` POST route explicitly returns HTTP 501.

## A-Line / StructDoc surface

### Existing callable components

- `struct_doc.read_struct_doc(path)` and `read_struct_doc_bytes(data, name)` parse a DOCX to a `StructDoc`; see `v1.2-xml-experiment/res/app/struct_doc.py:463-485`.
- `NodeIndex(doc)` builds addressable nodes and table/cell containers. IDs include top-level `b{seq}`, cells such as `b12.r1c0`, and nested cell blocks such as `b12.r1c0.n2`; see `v1.2-xml-experiment/res/app/struct_nodes.py:14-42,62-67,220`.
- The candidate splitter is `tools/stage2_baseline/run_baseline.py::predict(doc)` at line 1187. It runs `detect` → `build_units` → `merge_adjacent` → `fill_gaps` → `assign_relations`, and returns `(index, units)`. Its docstring calls this the old candidate pipeline in GoldCompare-compatible form. `tools/stage3_goldcompare/rerun_predictions.py:23-25,47-57` imports and invokes it only in the Stage3 re-run tool.
- Stage3 prediction JSON uses `{"sample_id", "baseline_commit", "units": [...]}`; each unit uses node-ID spans. This is an evaluation interchange format, not a renderer plan.

### Semantic unit and span implications

StructDoc top-level blocks use a dense zero-based `seq`; direct body paragraphs additionally carry a 1-based `pno`, while tables are one top-level block and cell paragraphs have no top-level `pno`. NodeIndex gives table cells and nested contents addressable IDs, and container spans expand to their descendant content nodes. These are logical StructDoc coordinates. Do not translate them to COM paragraph indices or use their integers as XML renderer child offsets.

`predict(doc)` emits semantic ranges as one or more pairs in `spans`. That is not yet a placement plan: it does not provide the XML renderer's template file, destination slot, or the V0.9 writer's `marker/start/end` structure. Roles such as `question_group` and `shared_material` also do not on their own specify which template section receives them.

### Thin facade required for Round 2

Add a production-layer facade under `v1.2-xml-experiment/res/app` (name to be selected during Round 2) that wraps the existing A-Line implementation without changing its split rules. Its minimum contract should:

1. Accept an original source path or immutable source bytes and read that same snapshot once.
2. Call `read_struct_doc_bytes(...)`, construct `NodeIndex`, and invoke the approved `predict(doc)` implementation through an explicit, packaged/importable dependency. The Stage3-only tool path must not be silently added to production `sys.path` as an undocumented dependency.
3. Return typed semantic units with stable node-ID spans and unit relationships, plus the source identity/hash used for the parse.
4. Convert semantic units into a renderer-specific plan only through an explicit template mapping. Each planned XML block must identify source span(s), template type/path, destination slot/target, and a stable failure when no supported mapping exists. Preserve order and avoid duplicating overlapping shared-material/QG content unless the plan explicitly encodes a supported binding policy.
5. Keep split recognition independent from renderer placement: no new A-Line rules or metric changes as part of the facade.

This audit does not add the facade because Round 1 is contract discovery only.

## B-Line renderer contract

### Orchestrator API

`v1.2-xml-experiment/res/app/renderer_orchestrator.py:46-63` defines `RenderJob` with:

- required: `source_doc`, `output_doc`;
- template: `template_type` (`1v1` default), optional `template_path`;
- metadata: `topic`, `objectives`, `difficulties`, `grade`, `subject`, `handout_type`, `label`;
- optional paired student inputs/outputs: `student_source_doc`, `student_output_doc`.

It does **not** contain a StructDoc, semantic units, a block plan, split mode, or a renderer destination map. `render_xml_or_fallback(job, xml_preflight=..., xml_render=..., fallback=..., package_validator=...)` receives renderer functions by injection. The orchestrator changes the XML job's output to a unique staging path; the XML callback must return that exact path plus optional resource/package reports. A successful XML outcome is `RenderOutcome(renderer="XML", output_paths=(final_path,), ...)`.

The normal XML path currently publishes one requested output. The `student_*` fields are not used by that XML branch. C0 must explicitly decide whether a job invokes the XML orchestration separately for teacher and student sources, and how student material is prepared, before claiming paired teacher/student support.

### XML renderer API

`renderer_xml_minimal.render_minimal(source_doc, template_doc, blocks, output_path, target)` takes `blocks: list[BlockSpan]`, each `BlockSpan(start, end)` containing StructDoc IDs, and one `TemplateTarget(body_child_index)` insertion offset. It validates source/model ordinal alignment and imports the selected XML payload, but all selected blocks in that call are inserted at the same target position. This API has no semantic-role-to-template-slot mapping and cannot by itself turn A-Line units into a multi-section handout plan.

The XML capability and package/resource checks are enforced in the orchestrator (`renderer_orchestrator.py:73-177`): unsupported preflight, renderer exception/fail-closed result, unsupported relationship report, package report failure, or validator failure invokes the fallback with a reason code. Reason codes currently include `UNSUPPORTED_REVISION_MARKUP`, `UNSUPPORTED_BOOKMARK_SCOPE`, `UNSUPPORTED_RELATIONSHIP`, `PACKAGE_VALIDATION_FAILED`, and `XML_RENDER_FAILED`.

### Whole-job V0.9 fallback

`render_v09_whole_job(job, reason_code)` at `renderer_orchestrator.py:221` loads the vendored frozen runtime under `res/app/v09_fallback_runtime`, pinned in code to `0922e08631226b95a77a6599bbc0ac3784e9134b`. It validates the original source, template, output, and optional paired-student paths. It does **not** accept V1.2 units or spans.

For teacher output it calls the untouched archived `handout.build_version(...)` on `job.source_doc`. The archived `build_version` path performs the V0.9 scan/split and writer selection itself. If `student_source_doc` is supplied, the same V0.9 path renders that paired source. If absent, the adapter calls archived `handout.make_student(original_source, scratch_path)`, then calls `build_version("学生版", ...)` on that derived full document. The selected template path/type and job metadata are passed through. The result declares `whole_job=True`, returns all output paths, the fallback reason, and baseline SHA.

The orchestration callback is invoked as `fallback(job, reason_code)`, and the final `RenderOutcome` exposes `renderer="V0.9"`, `fallback_reason`, `xml_error`, and details including `fallback_invoked`, `whole_job`, and `baseline_sha`. The caller must persist this outcome/reason in job state; the orchestrator comment says it should be recorded, but the current webapp route does not yet do so because it is only a stub.

## Webapp / workspace contract

### Current v1.2 backend

`v1.2-xml-experiment/res/app/webapp/app.py` currently has only:

- `GET /` → render `index.html`;
- `GET /api/jobs` → `{"jobs": []}`;
- `POST /api/jobs` → HTTP 501 with `{"error": "Flash 1.2 的 XML 生成任务接口尚未接入"}`.

There are no v1.2 routes yet for job detail/polling, download, or open-result.

### Workspace JavaScript expectations

`v1.2-xml-experiment/res/app/webapp/static/workspace.js` submits `FormData` to `POST /api/jobs` with repeated `files` plus `subject`, `grade`, `handout_type`, `academic_year`, `template_type`, `split_mode`, and `docx_mode` (function `startJob`, around lines 288-300). The UI has `split_mode` values `smart` and `full`; `docx_mode` values `auto` and `separate`.

On success the POST response must contain `job_id` and `total`. The client stores `job_id` in local storage and then polls `GET /api/jobs/<job_id>` every 1.2 seconds while `status == "running"` (`pollJob`, around lines 271-282). `GET /api/jobs` is expected to return `{"jobs": [...]}` for history/reconnect (`loadJobs`, around lines 305-313).

For job snapshots, `showJob` consumes `job_id`, `status` (`running`/`done`/`error`), `progress`, `total`, `stage` or `current`, `created_at`, `items[]` (`topic`, `teacher`, `student`), `warnings[]`, `produced`, and `has_result`. When `has_result` is true, download points to `/api/download/<job_id>` and open-result calls `/api/open/<job_id>` (`showJob` and `openJob`, around lines 249-269 and 345). History also reads `filenames[]`, `options.grade`, `options.subject`, `options.handoutType`, and status.

The previous v1.1 backend provides a nearby, concrete API precedent in `v1.1-stable/res/app/webapp/app.py`: multipart job creation returns `job_id`/`total`; public snapshots add `job_id`/`has_result`; status, download, and open routes exist. That route is only a schema precedent. Its worker is a different legacy generation pipeline and must not be copied wholesale into C-Line.

### C0 result delivery requirement (user addition, 2026-09-30)

Browser ZIP download is a convenience channel and must not be the only delivery path. Successful teacher/student DOCX files must first be written to a stable, per-job local result directory that does not overwrite another job. A job may become `done` only after each required final DOCX exists, is non-empty, and passes the corresponding package validation. Persist `result_dir`, `output_paths`, and `download_available` in job metadata.

`POST /api/open/<job_id>` or the existing compatible open route must locate/open the job result folder directly. The UI must show that generation succeeded, the local output path, an “open output folder” action, and an optional ZIP download action. A ZIP/download failure after validated files are on disk is `DELIVERY_DOWNLOAD_FAILED`; it must not change a successful generation to `GENERATION_FAILED` or remove the DOCX outputs. The class-template integration UAT must prove HTTP job creation → class XML or whole-job fallback → validated teacher/student files on disk → `done` snapshot → open endpoint resolves the result directory, and test ZIP download separately.

## Integration gaps and risks

1. **No production A-Line entry:** `predict(doc)` is in `tools/`, used by Stage3 evaluation scripts, and is not called by v1.2 app code. C0 cannot wire the app to a presumed packaged splitter API.
2. **No semantic-to-renderer mapping:** A-Line units have role + node spans; XML rendering needs spans plus template path and target. No slot map exists, and one `render_minimal` call inserts everything at one body offset.
3. **Orchestrator cannot receive a plan:** `RenderJob` contains source/output/template metadata but no units or blocks. The XML callback is injected and is not bound to a production plan builder.
4. **Student semantics differ by route:** XML normal path returns one output and does not use the student fields. V0.9 fallback does full-document student preparation/rendering. The C0 worker needs explicit pair/separate behavior so fallback and XML produce compatible job items/results.
5. **No job service or result endpoints in v1.2:** UI contract cannot complete an end-to-end request until create/status/list/download/open and durable-enough per-process job state are implemented.
6. **Batch input behavior needs preservation:** UI allows DOCX/ZIP, auto pairing or separate mode, and returns per-item teacher/student statuses, while the renderer orchestrator is a single-source RenderJob abstraction. An orchestration layer must resolve inputs and create explicit per-output jobs without silently merging unrelated documents.
7. **Fallback reason visibility:** reason codes exist internally, but job snapshots/UI currently have only generic `stage`/`warnings`; C0 should preserve `renderer`, fallback reason, and baseline identity in server-side job details/logs for diagnosis.
8. **Fallback is intentionally independent of A-Line:** unsupported XML must run V0.9 on the original teacher/student source, not the V1.2 block plan. Do not add a StructDoc→COM projection.

## Round 2 contract checklist

Before calling C0 end-to-end, require a worker-level boundary equivalent to:

```text
uploaded inputs + UI options
  -> input resolver (ZIP/DOCX, auto-pair/separate)
  -> production A-Line facade (source snapshot -> StructDoc -> semantic units)
  -> explicit semantic-unit-to-template block plan
  -> per-source RenderJob + XML capability/render/validation
       or explicit-reason V0.9 whole-job fallback on the original source
  -> teacher/student output records + job snapshot fields consumed by workspace.js
  -> download/open routes
```

The plan contract must define supported template targets, role/module mapping, span/order behavior, and fail-closed cases. Machine tests should exercise one supported XML path and one forced fallback path through the actual job service, not only through injected orchestrator callbacks. Keep the V0.9 runtime assets and A-Line rules unchanged; record the renderer choice and fallback reason in observable job state.

## Machine audit result

**`C0_ROUND1_AUDIT_PASS`** — the integration surfaces and gaps above are evidenced in the current checkout. This is not an end-to-end generation pass. No runtime code, A-Line, B-Line renderer, V0.9 asset, or webapp behavior was modified in this round.

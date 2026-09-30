# V0.9 Renderer Interface Audit

**Status:** read-only source audit; no V0.9 source changes and no COM execution.

## Audited baseline and scope

- B-Line checkout: `feature/v1.2-renderer-baseline`, HEAD `df3825d3a78f34537689af36136dd2588bcd73bc`.
- Known-Good commit: `0922e08631226b95a77a6599bbc0ac3784e9134b` (`chore: archive known-good v0.9 baseline`), available on `origin/baseline/known-good-v0.9`.
- `known-good-v0.9/KNOWN_GOOD_V0.9_MANIFEST.json` exists at that commit. It identifies `KNOWN_GOOD_V0.9_BASELINE`, says the archived runtime is excluded from Git (`res/python/**`), and records the user report that both 1v1 and class exports work.
- The archived `known-good-v0.9/` source tree is not in the B-Line HEAD tree. Audit findings below are from the separate archived commit. The webapp searches `ENGINE_DIR` before `APP_DIR` when importing `handout`, so its active engine is top-level `res/app/handout.py`; the duplicate `res/app/webapp/handout.py` is not the active import. The active writer scripts are likewise top-level `res/app/_fill_com.ps1` and `res/app/_fill_class.ps1`. The webapp route is `res/app/webapp/app.py`.

## V0.9 generation chain

### 1. 1v1 teacher entry

The production application entry is the Flask upload route in `res/app/webapp/app.py`, which dispatches the background `process_job(...)` worker. For each teacher source it gets COM-indexed paragraphs, then calls the imported `handout.build_version("教师版", ...)` with the selected template and `template_type="1v1"`. The import resolves to top-level `res/app/handout.py` because `ENGINE_DIR` is searched before `APP_DIR`. In that module, `build_version` calls `auto_split(...)`, constructs a version dictionary, then calls `_run_version(v, template)`. `_run_version` dispatches to top-level `_fill_com.ps1` for 1v1.

There is also a command-line `handout.py` entry. `simple` makes two knowledge-only outputs; `plan` accepts caller-supplied versions/ranges and can select `template_type`. The Flask webapp flow is the actual paired teacher/student production path; it is not the same as invoking CLI `simple`.

### 2. Class teacher entry

The production entry is the same webapp upload route and `process_job(...)`, with the submitted template type set to `class`. `process_job` selects the imported top-level engine's `handout.CLASS_TEMPLATE`, calls the same `build_version(...)` path, and passes `template_type="class"`. `_run_version` then selects top-level `_fill_class.ps1`. The CLI can reach this writer through `plan` by setting `template_type: "class"` and supplying a template; CLI `simple` is hard-wired to the 1v1 default template.

### 3. Student version creation

The webapp always creates a separate student output after the teacher attempt. When an uploaded pair contains a student source, that source is used directly. Otherwise it calls `handout.make_student(teacher, stu_src)`, which strips red answer runs, removes answer/analysis markers using the archived COM helper, and adds short-answer blanks using the archived COM helper. It then scans the resulting student source, calls `build_version("学生版", ...)`, and renders it through the same selected writer/template path. There is no `student` boolean in the COM writer contract: student processing is upstream and produces a source document to render.

### 4. Blocks and ranges

`build_version` accepts `paras` (or obtains them from `_body_paragraphs`), and computes `blocks` through V0.9 `auto_split`. The V0.9 scanner obtains `(paragraph_index, text)` rows through Word COM, aligned to that Word document's `Document.Paragraphs`; the V0.9 writer consumes those COM indices. This existing V0.9 path does not establish a mapping from current V1.2 StructDoc positions to COM indices.

The writer-facing block shape is a JSON array of objects:

```json
[
  {"marker": "知识精讲", "start": 5, "end": 437},
  {"marker": "即时训练", "start": 438, "end": 855}
]
```

`start` and `end` are **1-based, inclusive Word COM paragraph indices**. The PowerShell writer uses `Paragraphs.Item(start).Range.Start` through `Paragraphs.Item(end).Range.End`. Ranges must be positive and ordered (`end >= start`); invalid/empty ranges are skipped. If either endpoint is inside a Word table, the writer expands the copied range to cover that table. Blocks are sorted by the built-in marker order, back to front, before insertion. The writer does not receive V1.2 structured blocks or infer their boundaries.

Current V1.2 StructDoc exposes body `pno` for top-level `w:p` nodes. A table is represented as one top-level block; its cell paragraphs carry `pno=None`. Textboxes are captured as metadata. This representation does **not** prove a total 1:1 mapping from StructDoc node spans to Word COM `Document.Paragraphs` indices. Producing and validating an exact node-span → COM-index projection for the specific source document is an unresolved prerequisite to implementation. The adapter must stop with `RENDERER_CORE_CHANGE_REQUIRED` if it cannot produce that exact projection; it must not guess indices or alter the V0.9 writer to compensate.

### 5. Template path

The Python `_run_version(v, template)` receives the template path separately from the version object, makes it absolute, and serializes it as `template` in a temporary UTF-8 JSON parameter file. In the production webapp, `process_job` chooses `handout.DEFAULT_TEMPLATE` for 1v1 or `handout.CLASS_TEMPLATE` for class. The CLI `plan` path obtains `plan["template"]` (relative paths resolve under `WORK_DIR`) or uses the default 1v1 template. The archived 1v1 template is DOCX; the class template is legacy DOC.

### 6. Output path

The caller creates the output directory before rendering. The webapp uses a per-job `outputs` directory and builds separate teacher/student filenames there. CLI callers provide each version's `output` path. `_run_version` normalizes it to an absolute path and sends it as `output_doc`. Both scripts use that path in `SaveAs(..., 16)`, producing DOCX, including for the class DOC template.

### 7. PowerShell / COM chain

`build_version` → `_run_version` → serialize parameters as a temporary JSON file → launch Windows PowerShell with `-NonInteractive -ExecutionPolicy Bypass -File <selected script> -ParamsJson <json>` → top-level `_fill_com.ps1` (1v1) or `_fill_class.ps1` (class) reads the JSON → creates `Word.Application`, opens source and template, replaces supported header placeholders, sorts blocks in reverse template order, copies each source Word paragraph range and pastes it after the matching template anchor paragraph, optionally applies formatting, optionally trims trailing empty paragraphs, and saves the output DOCX. The scripts contain their own existing Word cleanup/close behavior. `_run_version` returns captured stdout and may log some stderr, but it does not expose a structured, reliable render-success result. This audit only traced source and did not execute that chain.

### 8. Minimum input required by the Writer

The writer requires a valid readable source document and template path; an output path; a `label`; and a `blocks` array whose items contain `marker`, positive 1-based inclusive `start`, and `end >= start` within the Word COM paragraph collection. Each marker must be represented in that writer's `$ORDER` table and must be findable as an anchor in the chosen template. Both writers recognize the six module positions (startup, review, knowledge, immediate practice, summary, consolidation) with the aliases encoded in their source. Optional header fields (`topic_name`, `objectives`, `difficulties`, `grade`, `subject`, `handout_type`) and flags (`fmt`, `trim_blanks`) are supplied in the same parameter JSON. A structured block adapter therefore needs to supply final module assignment and exact COM paragraph ranges; it must not expect the Writer to reclassify blocks or detect question boundaries. Because `_run_version` does not return a structured success result, the adapter must independently validate that this invocation newly produced the requested output (for example, by rendering to a unique per-invocation staging path and confirming the resulting file exists and is non-empty). That validation belongs in the adapter and must not change COM-core behavior.

## Thinnest justified Renderer Contract

The V0.9 Writer does not accept structured blocks directly: it accepts source-document COM paragraph ranges mapped to template markers. The smallest wrapper can accept the V1.2 source document, already-resolved V1.2 blocks, template type, and output path; project their node spans exactly to V0.9's marker/start/end records; call the existing V0.9 Python invocation path; and return adapter-validated status and output path. Student rendering should pass the already-prepared student source through the same contract, because V0.9's student transformation is a separate upstream operation, not a writer flag. Exact StructDoc-to-COM projection is a gate before implementing the adapter; if unavailable, stop with `RENDERER_CORE_CHANGE_REQUIRED` rather than editing the baseline.

```python
render(
    source_doc, blocks, template_type, output_path, *, label,
    template_path=None,
    topic_name="", objectives="", difficulties="",
    grade="", subject="", handout_type="",
    fmt=True, trim_blanks=True,
) -> RenderResult(ok: bool, output_path: str, log: str)
```

`label` is required by `_run_version`. `blocks` at this boundary must be converted to V0.9's exact records:
`{"marker": str, "start": int, "end": int}`. Indices are absolute 1-based inclusive Word COM paragraph indices for that exact `source_doc`; they cannot be inferred from isolated block-local text. The exact StructDoc-node-span → COM-index projection is not established by this audit and must be solved and validated before implementing this conversion. If it cannot be produced without modifying the V0.9 core, stop with `RENDERER_CORE_CHANGE_REQUIRED`. `template_type` chooses the existing 1v1 versus class writer and its matching template. Supply an explicit `template_path` to match `_run_version(v, template)`, or resolve the existing V0.9 default for that `template_type`. Pass the existing header metadata (`topic_name`, `objectives`, `difficulties`, `grade`, `subject`, and `handout_type`) through, defaulting each to an empty string. Preserve the production `build_version` defaults `fmt=True` and `trim_blanks=True`. There is no `student` flag: pass the already-prepared teacher or student source document as `source_doc`. The wrapper should delegate through the archived top-level `res/app/handout.py` `handout._run_version` path or its equivalent parameter construction, without changing either PowerShell script or the COM behavior. Since `_run_version` returns text rather than reliable structured success, `RenderResult.ok` must be based on adapter-side confirmation that a newly generated output exists at the requested destination (or a unique staging destination) and is non-empty; do not treat stdout alone as success.

**Recommended adapter entry:** wrap `handout._run_version(v, template)` from the archived top-level `res/app/handout.py` engine (or a thin B-Line adapter that constructs the same `v` dictionary and invokes this entry). This is the narrowest existing seam: it accepts one fully prepared version and keeps writer selection, parameter JSON, and PowerShell dispatch inside the preserved V0.9 path. Do not use the Flask route as the adapter API; it also owns uploads, job state, pairing, filenames, and student preparation.

## Audit conclusion

The baseline supports both 1v1 and class rendering from precomputed Word COM paragraph ranges, with teacher and student documents rendered as separate calls. V1.2 must establish an exact StructDoc node-span → COM-index projection before adapting its block representation, then preserve the baseline's selected template and writer route. If that projection cannot be produced without touching V0.9 core behavior, stop with `RENDERER_CORE_CHANGE_REQUIRED`. No adapter or rendering run was performed in this audit; it makes no claim about B1 or real Word/WPS COM UAT.

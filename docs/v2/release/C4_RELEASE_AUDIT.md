# C4 Release Audit (read-only source/runtime audit)

Audit base: `8009f9a40afdce912647e8ed391d2d4fe381bc72` on
`feature/v1.2-c4-release-engineering`; local and `origin` HEAD matched before
this documentation-only round. No build, package, production edit, or release
UAT was performed.

This report separates **verified repository behavior** from **packaging
recommendations**. Paths below are repository-relative.

## 1. Production entry and user flow

**Verified:** The production HTTP entry currently is
`v1.2-xml-experiment/res/app/webapp/app.py`. Direct execution reaches
`app.run(host="127.0.0.1", port=5128)` at the end of that file. It serves the
Flask `index.html`, accepts job submissions, starts asynchronous job work, and
has `/api/open/<job_id>` to open the local result folder. Batch ZIP input is
resolved through `batch_inputs.py` / `job_service.py`.

There is no V1.2 native launcher, PyInstaller spec, C4 package manifest, or
release dependency lock in this branch. The source app does not itself open a
browser, select an alternate port, detect an existing process, or provide a
launcher-controlled graceful shutdown. It assumes port 5128. Therefore the
requested “double-click → ready service → browser opens → clean exit” flow is
not established by the current entry point.

**Packaging recommendation (not implemented):** add a small Windows GUI-mode
bootstrap that owns a single app instance and child server lifetime, probes the
default port before binding, chooses a safe alternate port only after proving
the port is free, waits for a ready response, opens the actual URL, and shuts
down the child on user exit. The server must bind loopback only. It must never
open an occupied 5128 port without verifying that it belongs to this app.

## 2. Python and dependencies

**Verified repository facts:** No top-level `requirements.txt`, PyInstaller
spec, or C4 build lock exists. The only checked-in runtime lock is
`v1.2-xml-experiment/res/app/v09_fallback_runtime/KNOWN_GOOD_V0.9_RUNTIME_REQUIREMENTS.lock`;
its header says CPython `3.12.10` and pins the archived environment, including
Flask `3.1.3`, lxml `6.1.1`, python-docx `1.2.0`, and other distributions.
That file is not a V1.2 build lock and the corresponding `res/python` runtime
is not present in this checkout.

The current shell's `python` resolves to a Hermes-managed CPython `3.11.15`;
Flask import fails there, and no `pyinstaller` command was found. This only
describes the audit environment; it is not evidence about a release machine.

**Active application dependency set inferred from imports:** Flask and its
runtime dependencies (Werkzeug, Jinja2, MarkupSafe, itsdangerous, click,
blinker), lxml, and python-docx. The frozen fallback uses `docx.Document` and
the same lxml stack. The Stage2 predictor is loaded dynamically from
`tools/stage2_baseline/run_baseline.py`; that file imports the app's
`gold_compare`, `struct_doc`, and `struct_nodes` modules. Python standard
library modules are also used. `waitress` and `anthropic` occur in the V0.9
environment lock, but the current web entry calls Flask's `app.run` and no
active job route calls the archived objective-generation API; their inclusion
should be based on final import collection, not assumed from the broad lock.

**Packaging recommendation:** build with a pinned x64 CPython and separately
pinned PyInstaller/build dependencies in a clean build environment. Bundle the
interpreter and active dependency closure into an onedir package. Do not make
the user's machine install Python or run `pip`. A frozen import/resource
smoke in an isolated directory is still required; source import inspection
does not prove PyInstaller collected dynamic imports or lxml native DLLs.

## 3. Web resources

**Verified required web resources:**

- `v1.2-xml-experiment/res/app/webapp/templates/index.html`
- `v1.2-xml-experiment/res/app/webapp/static/workspace.js`
- `v1.2-xml-experiment/res/app/webapp/static/workspace.css`
- `static/vendor/lucide.min.js`, `app-icon.svg`, and `chevron-down.svg`
- `static/previews/1v1.png`, `1v1.pdf`, `class.png`, and `class.pdf`

The template references the CSS, JavaScript, icon, and preview images; the
JavaScript builds the matching 1v1/class preview PDF URL. These are runtime
resources, not optional documentation. Preserve Flask's `templates` and
`static` layout or explicitly configure the equivalent paths in the eventual
launcher/package.

## 4. 1v1 and class templates

The XML/Slot Router path reads immutable templates through
`v1.2-xml-experiment/res/app/template_block_plan.py` → `semantic_facade.py`'s
`REPO_ROOT`. The exact hashed inputs currently live at:

- `v1.1-stable/res/app/2025+1v1讲义模板(2).docx` — SHA-256
  `1318fceabaa957b12e371310902fd81a0db08be09cee2121f6cd2606d8fd6a1a`
- `v1.1-stable/res/app/2025班课模板.docx` — SHA-256
  `f51046d841699645b1b49f49f481c559e8502b98589d20b0c7e97cf2f7ba8f13`

These two files must be included at the same relative paths under the packaged
resource root (or the resource resolver must be deliberately adapted in a
later reviewed packaging round). If the package drops the repository-relative
tree, `resolve_template()` cannot find the files. The app also verifies their
hashes before use.

The frozen V0.9 fallback has its own template pair in
`v1.2-xml-experiment/res/app/v09_fallback_runtime/`: 1v1 DOCX and class DOC
(the latter is not the XML class DOCX). Keep both pairs distinct; do not
substitute the fallback `.doc` for the XML renderer's `.docx`.

## 5. Studentizer manifest

The production registry defaults to the sibling directory
`v1.2-xml-experiment/res/app/reviewed_studentizer/`, which currently contains
`X008.json`. The reviewed manifest is source-hash-bound and contains the
approved range/evidence metadata; it is not the original teacher document or a
Golden source sample. The whole `reviewed_studentizer` directory must be
packaged, preserving the sibling relationship to `reviewed_studentizer.py`.
If the manifest is absent/unreadable or source evidence does not match, the
application uses the existing Studentizer fallback route; package startup
should not fail solely because WPS is absent.

## 6. B-Line XML assets and A-Line dynamic dependency

The active slot route imports the V1.2 files in
`v1.2-xml-experiment/res/app/`: `slot_router.py`, `template_block_plan.py`,
`template_slot_composer.py`, `renderer_xml_minimal.py`, `renderer_orchestrator.py`,
`block_importer.py`, `package_validator.py`, `struct_doc.py`, `struct_nodes.py`,
`semantic_facade.py`, `studentizer.py`, `studentizer_planner.py`,
`studentizer_ranges.py`, and `reviewed_studentizer.py`; job intake also uses
`batch_inputs.py` and `input_versions.py`. Preserve Python module adjacency
because imports are top-level sibling imports.

A-Line is a dynamic source-file load, not an ordinary package import:
`semantic_facade.py` calculates `REPO_ROOT` and loads
`tools/stage2_baseline/run_baseline.py` by file path. That predictor imports
`gold_compare.py`, `struct_doc.py`, and `struct_nodes.py`. Include the predictor
at the expected `tools/stage2_baseline/` relative path and all reachable app
modules at the corresponding `v1.2-xml-experiment/res/app/` path, or a later
reviewed change must replace this repository-root assumption. The package
must not depend on an external Git checkout.

Do not include test modules, Stage2/Stage3 gold data, corpus fixtures, private
UAT output, `.git`, caches, or the full research/test `tools/` tree. Only the
runtime-reachable predictor resource is required from `tools/` by the audited
production route.

## 7. Frozen V0.9 fallback assets

`renderer_orchestrator.py` loads frozen
`v1.2-xml-experiment/res/app/v09_fallback_runtime/handout.py` by path, and
`handout.py` imports sibling `toc_split.py`. It builds paths relative to its
own `WORK_DIR` for both fallback templates and the five scripts below. The
current asset manifest ties this folder to baseline commit
`0922e08631226b95a77a6599bbc0ac3784e9134b` and lists ten files. Keep the
manifest-listed runtime snapshot byte-identical; use
`tools/verify_v09_fallback_assets.py` as a build-time provenance check, not as
a production dependency.

Files required by the checked manifest/runtime are `handout.py`, `toc_split.py`,
`2025+1v1讲义模板(2).docx`, `2025班课模板.doc`, `_fill_com.ps1`,
`_fill_class.ps1`, `_scan_com.ps1`, `_strip_answer_com.ps1`,
`_add_blanks_com.ps1`, plus `ASSET_MANIFEST.json`, the pinned requirements
lock, and `.gitattributes` if retaining the exact ten-entry manifest layout.
The `.gitattributes` file is provenance metadata rather than an application
runtime dependency. `_doc2docx.ps1` from `v1.1-stable` is not referenced by the
current frozen fallback runtime and is not in its manifest; do not copy the
entire old application directory into the RC.

## 8. PowerShell / WPS COM boundary

`handout.py` discovers Windows PowerShell under `%SystemRoot%` or from PATH,
then invokes it with `-NonInteractive -ExecutionPolicy Bypass -File`. Its
paragraph scan calls `_scan_com.ps1`; render calls `_fill_com.ps1` or
`_fill_class.ps1`; V0.9 student preparation may invoke `_strip_answer_com.ps1`
and `_add_blanks_com.ps1`. Those scripts create `Word.Application` via COM,
which is the compatibility boundary used with installed Word/WPS providers.
The V0.9 `make_student` function also has a Python/python-docx red-text pass
before those COM operations.

**No WPS/Word needed:** supported XML Studentizer, A-Line, Slot Router, XML
Renderer, package validation, Flask UI, job persistence, output publication,
and opening the result folder. The currently approved X008 source is the
proven Studentizer example; this is not a claim that all sources are supported.

**WPS/Word COM needed:** V0.9 `make_student` operations that invoke the strip
or blank scripts, V0.9 paragraph scan, and V0.9 Writer rendering. The exact
COM provider present is environment-specific. PowerShell availability alone
does not prove a registered Word/WPS COM provider. With no provider, supported
XML work should remain available; a job that requires fallback needs a clear
item/job error and must not prevent app startup.

## 9. Runtime reads and writes

**Verified current defaults:**

- Application code/resources: sibling files beneath the package resource
  tree (read-only at runtime).
- Reviewed manifest: `res/app/reviewed_studentizer/` (read-only).
- Durable job state: `%LOCALAPPDATA%\讲义生成器\jobs\<job-id>\job.json`.
- Uploaded source snapshots and staging: each job's `work/` directory under
  that LocalAppData job root. It may contain `input-N.docx`, derived student
  source, renderer stages, and intermediate generated DOCX files.
- User deliverables: `~/Desktop/生成讲义结果/<unique task name>/`, with final
  DOCX files and batch topic subdirectories only.
- Renderer temporary files: created beside their staged destination and
  cleaned/replaced by renderer code.
- Frozen V0.9 scan/parameter files: `tempfile.mkstemp()` currently uses the
  process default OS temp directory (`%TEMP%`), not the configured jobs root.

That last behavior conflicts with the C4 requirement that all internal runtime
data live under `%LOCALAPPDATA%`. **Release blocker/design item:** before RC
UAT, the launcher must direct Python and child PowerShell temp variables
(`TEMP`, `TMP`, and Python's temp resolution) to a private
`%LOCALAPPDATA%\讲义生成器\temp` directory before starting the app, or a
reviewed change must route these scratch files there. Do not write job records,
logs, temp files, source inputs, or runtime state into the portable install
directory; it may be read-only or moved. The source app currently has no
separate durable logs/diagnostics roots, so those should only be introduced
under LocalAppData if later required.

`Path.home()/Desktop` assumes a conventional Desktop path. Known Folder
redirection/OneDrive Desktop behavior is not verified; RC UAT must test the
actual Windows Desktop location. This audit does not claim that source code
already resolves redirected Known Folders.

## 10. Onedir package map, exclusions, and release blockers

**Required in the proposed onedir resource tree:**

1. A new GUI-mode launcher/server bootstrap and its config/branding assets.
2. The V1.2 production module closure and dynamic A-Line predictor at the
   relative paths identified above.
3. Flask template, all referenced static CSS/JS/SVG/PNG/PDF assets.
4. Both XML renderer DOCX templates at their expected relative paths.
5. `reviewed_studentizer/X008.json` and future reviewed manifests only.
6. The complete manifest-verified frozen V0.9 runtime folder, byte-identical.
7. Bundled x64 CPython, Flask/Jinja/Werkzeug and dependency closure, lxml
   native components, python-docx dependencies, and Windows runtime DLLs.

**Must not be in or written into the install directory:** user uploads/results,
job JSON, derived sources, temporary files, logs/diagnostics, tests, corpus or
Golden samples, private UAT artifacts, `.git`, developer virtual environments,
API keys/tokens, or a dependency on source checkout paths. The user's final
DOCX files belong only under Desktop `生成讲义结果`; mutable internal state
belongs under LocalAppData. A portable onedir can be extracted into a Chinese
path with spaces, but successful operation there is not yet tested.

**Known C3 test baseline:**
`docs/v2/integration/C3_FINAL_MACHINE_GATE_2026-10-02.md` records the same four
pre-existing `v1.1-stable` API expectation failures on base and candidate:
`has_result` expectation and three upload-status expectations (`400`/`409`/`200`
versus actual `415`). Do not call the full suite green and do not attribute
these unchanged failures to C4. Compare every C4 test run against that recorded
baseline so genuinely new failures remain visible.

**Not verified / blockers before packaging or RC claims:** no PyInstaller
configuration or pinned clean build environment; no launch/instance/port/exit
bootstrap; active app import fails under the current `python` command because
Flask is missing; packaged dynamic A-Line resource resolution untested;
LocalAppData redirection of V0.9 `%TEMP%` scratch unimplemented; Desktop Known
Folder redirection unverified; no installed-without-Python smoke; Chinese path,
EXE browser startup/port-conflict/10-cycle lifecycle, packaged XML/fallback,
restart, result-directory, and WPS output UAT all remain pending. This is an
audit checkpoint, not a package-readiness PASS.

## Recommended next action

Submit this source-only audit for **Codex GPT-6.1 Sol** independent review.
Only after Chief PASS, start a separate implementation round for the minimal
GUI bootstrap, pinned onedir build recipe, explicit package-data map, and
LocalAppData/temp path isolation. Keep A-Line, C1 rules, C2 rules, C3 Studentizer
scope, and frozen V0.9 runtime unchanged.

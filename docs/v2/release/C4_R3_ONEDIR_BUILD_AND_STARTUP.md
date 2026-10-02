# C4-R3 onedir build and startup evidence

Round status: **build and isolated startup/resource smoke passed; not RC PASS**.

## Build inputs and output

- Branch/base: `feature/v1.2-c4-release-engineering`, `59b074b17e842fd57f6484b9176d476dcafe3274`.
- Build runtime: CPython `3.12.10`, Windows `AMD64` (64-bit).
- Locked app/runtime dependencies: Flask `3.1.3`, Werkzeug `3.1.3`, Jinja2 `3.1.6`, lxml `6.1.1`, python-docx `1.2.0`.
- Locked builder: PyInstaller `6.22.3`, hooks-contrib `2026.7`; all transitive build/runtime packages are exact-pinned in `tools/release/C4_ONEDIR_REQUIREMENTS-WIN64.lock`.
- Build recipe: `packaging/windows/v1.2_onedir.spec` and `tools/release/build_c4_onedir.ps1`.
- Build output (external to the repository): `C:\xml-uat\c4-r3-output\dist\讲义生成器\`.
- Binary: `讲义生成器.exe`, 5,880,639 bytes, SHA-256 `d51bf225233f8de173bb64ed3457cafa62cb1aab0496994ec5ea019eb7a00e7f`.
- Onedir package: 194 files, 36,167,421 bytes; deterministic inventory tree SHA-256 `ac70b3bfe8950b33ae5a80b316a8ec7b84b73609f1651c74e91bacea7f0a6fcd`.
- Full per-file path/size/SHA-256 inventory: `C:\xml-uat\c4-r3-output\PACKAGE_INVENTORY.json` (external build evidence; binary and private UAT data are not committed).
- The V0.9 source provenance check passed `10/10`; the build script also checked all ten packaged V0.9 assets against the frozen manifest hashes.

The package preserves the audited repository-relative `_internal` layout for
the V1.2 app source/resources, XML templates, reviewed `X008.json` manifest,
Stage2 dynamic predictor, web resources, and the unchanged V0.9 runtime
snapshot. Test modules, corpus/Gold data, `.git`, caches, and developer
environments are excluded. The launcher now resolves frozen resources from
`sys._MEIPASS` so the existing path-based runtime loaders do not depend on a
source checkout or `C:\xml-uat`.

## Isolated startup smoke

The built onedir package was copied to
`C:\Users\Administrator\Desktop\C4 中文隔离 Smoke R3` and started with the
working directory set to `C:\Users\Administrator\Desktop`. `PATH` was limited
to `%SystemRoot%\System32;%SystemRoot%`; `PYTHONPATH` and `PYTHONHOME` were
empty. The packaged child used a separate LocalAppData test root.

- Launcher published a ready record and bound `http://127.0.0.1:5128`.
- Authenticated `/api/launcher/ready`: `ready=true`.
- `/`: HTTP `200`; Flask template rendered its expected title.
- `/static/workspace.css`: HTTP `200`.
- `/static/workspace.js`: HTTP `200`.
- `/api/jobs`: HTTP `200`.
- Authenticated `/api/launcher/shutdown`: `stopping=true`; launcher exit code `0`; ready file removed.
- Startup and HTTP checks ran from the copied package, outside the source checkout and outside `C:\xml-uat`; no Python/venv was available on `PATH`.
- The launcher handed the actual ready URL to the registered system browser without raising. Independent browser-tab/visual confirmation is **not verified**: the Edge browser connector returned `nodeRepl.fetch request failed` during read-only inspection.
- The temporary Desktop package copy is retained for handoff inspection. The authoritative external build output and inventory are also retained.

`tests/test_windows_launcher.py`: `12 passed`. This includes the frozen
resource-root regression check. V0.9 asset verification was `10/10`. This round
did not run generation, WPS/Word, XML/fallback job UAT, full UI cases,
port-conflict UAT, restart/batch cycles, or RC gates. Package startup success
does not establish those behaviors.

Two early disposable package attempts exposed missing frozen import closure
(first the XML standard-library dependency, then Flask). The spec was corrected
to analyze the production runtime module closure while keeping `app.py`
source-loaded for Flask's package-relative template/static root. The final
clean build and isolated smoke above use that corrected spec.

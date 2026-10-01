# C2 Round 7 — Local-only Result Delivery and Real Browser UAT

Worker: GPT-6.1 (`gpt-6.1-sol`). Base:
`9eeb159e41ee285f5f8bb6bcc86f3517fe7a96f2`.
Independent Chief: Codex GPT-6.1 Sol, pending this pushed candidate.

## User decision and implementation

The user's latest product decision removes **output ZIP delivery** entirely and
keeps **ZIP input**. Formal rules: `C2_LOCAL_RESULT_DELIVERY_RULES.md`.
The Flask output-download route, output ZIP response construction, workspace
and history download controls, download availability and failure-state handling
are removed. Historical runtime metadata is stripped on recovery; local output
validation, `done`/`partial` semantics and `/api/open` remain intact.

Only delivery service/routes/UI, associated tests and C2 documents changed.
Input resolver, A-Line, B-Line renderer core, C1 Business Rules, student
preparation and frozen V0.9 runtime are unchanged.

## Real headed browser evidence

The revised production app ran asynchronously at `127.0.0.1:5129`, with isolated
results/runtime under `C:\xml-uat\c2-browser-round7`. The user's port 5128 app
was left untouched. Installed Microsoft Edge was driven by Playwright CLI.
File chooser upload and Generate/Open Folder buttons were actually clicked;
this is not only a test-client/API gate.

| Input / template | Logical items | Outcome | Valid local DOCX | Time |
|---|---:|---|---:|---:|
| Four real DOCX: X004 teacher-only, X013 student-only, genuine X023/X021 pair / class | 3 | done, 3 success / 0 failure | 5/5 | 42.558 s |
| Chinese nested ZIP: genuine X023/X021 pair, X019 student-only, corrupt DOCX fixture, ignored `~$` entry / 1v1 | 3 | partial, 2 success / 1 failure | 3/3 | 6.302 s |

Job IDs: `53ee915a34244b72a70cfef25edbde27` and
`30326674d057444b873bf8b506616d50`. Both successful pipelines remain XML.
The direct batch invokes frozen student preparation only for X004 teacher-only;
supplied pairs and student-only topics never invoke it. These timings are one
real browser observation; the Round 6 matched V0.9 performance evidence remains
the benchmark, not a comparison against different inputs here.

Observed real polling updates include running state, totals, completed/failed
counts and current topic. Screens show each topic's role, XML and outcome.
Class guidance uses `六、出门测试`; 1v1 uses `六、巩固练习`.
Final success/partial screens show local paths and only Open Folder delivery.
The history view also contains no download links.

Both Open Folder clicks returned HTTP 200 and actually opened Windows Explorer.
Computer Use accessibility confirms the exact result paths ending in `（3）`
and `（4）`, with three and two topic folders respectively. Successful sibling
DOCX files remain accessible despite the corrupt ZIP member.

The eight outputs are nonempty and pass the frozen package validator. Recursive
directory audit finds exactly the recorded DOCX outputs, no ZIP/internal JSON
or runtime files, no underscore names, and unique task/topic paths. Earlier
task folders remain intact. The obsolete API returns HTTP 404 for both jobs.
Job snapshots contain none of the four obsolete delivery/download fields.
Real DOM inspection reports **0 download elements and 0 download labels**.

## Evidence locations

External evidence (no copyrighted source/output packages added to Git):
`C:\xml-uat\c2-browser-round7\delivery-revision\`:

- `success-running.txt`, `success-final.txt`, `partial-running.txt`,
  `partial-final.txt`, `history.txt`, `no-download-dom.txt`.
- `success-folder.txt`, `partial-folder.txt`: actual Explorer accessibility.
- `local-results.json`: API snapshots, eight package reports and output hashes.
- `stage3/summary.json`, `stage3/compare.json`, `stage3/compare.md`.

Actual screenshots visually inspected:
`cli-output/page-2026-10-01T09-37-40-572Z.png` (success) and
`cli-output/page-2026-10-01T09-39-19-701Z.png` (partial).
Trace and HTTP polling/Open Folder evidence:
`cli-output/traces/trace-1790847307766.trace` and `.network`.
The standalone CLI network listing commands were unavailable; the recorded
trace network is used instead. No output-download action was attempted in this
revised run.

Earlier pre-revision R7 browser/download observations remain external. They are
superseded and are not claimed as the current product's download gate PASS.
Historical reports retain their original dated observations with a supersession
notice. Output downloads are no longer a product requirement.

## Machine gate

Focused suite: **124 passed in 36.08 s**, including Stage2 **39/39**. It covers
the removed route (404), validated role files, clean unique local folders,
legacy metadata cleanup for both single and batch jobs, partial success, input
ZIP safety/grouping and executed JS state/history behavior. The first local
test attempt exposed a leftover JS closing brace during download-control
removal; it was repaired before the passing full focused rerun.

Fresh Stage3: eight source hashes match; QG **408/408**, sections **369/369**,
subquestions **328/328**, original-paper recall **100%**, E1/E2/E3/E4 and
MISS/FP/MERGE/SPLIT **0**. Overall teacher/analysis exact QG boundary rate is
**87.7%**, unchanged, not represented as 100%. Frozen V0.9 app assets **10/10**.
Python/JS syntax and diff checks pass. No frozen core/Business Rules diff.

Round 6 real WPS, content, mixed fallback and same-machine performance evidence
was independently reviewed PASS. This revision changes no generated content
logic. Its fresh browser/local-delivery candidate now awaits independent
Codex GPT-6.1 Sol review. No C2 completion/tag is created by the Worker.

# C2 Round 5 — Minimal Batch Workspace UI

> Historical Round 5 report (Chief subsequently PASS). The user's latest
> 2026-10-01 decision removed output ZIP UI/API and download state entirely;
> ZIP input remains. The download descriptions below are historical only.
> Current rules/evidence: `C2_LOCAL_RESULT_DELIVERY_RULES.md` and
> `C2_LOCAL_DELIVERY_BROWSER_UAT.md`.

Worker: GPT-6.1 (`gpt-6.1-sol`). Base:
`cd7264b0c4f0d304a027478849c35e02762fade4`.
Round 4 Chief returned PASS for the shared serial executor repair. This round's
Chief review is pending; it is not a real batch/product UAT or `C2_BATCH_PASS`.

## Changes

The existing workbench and DOCX/ZIP multi-select upload control are retained.
The obsolete “batch processing is not open” guidance is removed. Automatic mode
describes reliable topic pairing; separate mode accurately describes independent
DOCX items for ZIP and three-or-more direct files. The C1 explicit two-file auto
pair keeps supplied-student priority. Direct two-file separate mode remains
unsupported by the preserved C1 route, so its guidance explicitly directs users
to pairing, ZIP, or three-or-more independent inputs.

Running batches show total, completed, failed and current topic. Each item row
shows topic, teacher/student roles, XML or `fallback（V0.9）`, and success/failure
or pending/running status. A rejected item without a renderer says “未执行”;
unknown pending routes say “待确定”. Fallback reason and item error are available
as row tooltips, without exposing internal runtime files in the results folder.

Partial batches show “部分讲义已生成”, retain the successful local directory and
state that failed items do not invalidate successful outputs. All-failed batches
show an explicit failure title and no result/download buttons. History supports
the partial outcome and an explicit partial filter.

“打开成品文件夹” is the first primary action; ZIP download is secondary. Delivery
text prioritizes validated local results and preserves them when ZIP delivery is
unavailable. Finished partial jobs stop polling/elapsed updates and release the
form, just like completed C1 jobs. Single/pair jobs hide batch counters and keep
their existing teacher/student role behavior and template-specific guidance.

## Machine Gate

- `node --check` for the production workspace script and JS test harness.
- **13 focused UI tests** execute the actual private `workspace.js` functions
  against a minimal synthetic DOM under Node. The harness adds test access only
  to its in-memory source copy; production has no debug/test globals.
- Backend/resolver/C1/Stage2 gate: **110 passed**. Combined focused gate with UI:
  **123 passed**, including Stage2 39/39.

UI cases cover running batch counts/current topic and all item columns;
partial success/local ZIP delivery; download failure retaining local generation;
all-failed; C1 student-only role display; ZIP/multi-DOCX auto/separate guidance;
explicit C1 two-file pairing; posting every selected DOCX/ZIP; partial history
filter; and primary Open Folder plus multi-select input attributes.

These are executed JS/DOM state tests, **not browser/visual UAT**, real XML batch
rendering, WPS open-save-reopen checks or a performance benchmark. Final Cases
A–F, product UAT, V0.9 timing comparison, process-start counts and fresh Stage3
regression remain outstanding. A-Line, B-Line renderer core, V0.9 runtime and
approved C1 Business Rules have no changes.

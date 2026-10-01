# C2 Local Result Delivery Rules

User decision, 2026-10-01. This supersedes the earlier C0/C2 auxiliary output
ZIP requirement. Approved C1 input and slot-routing Business Rules remain frozen.

## Input

Keep single DOCX, explicit teacher/student pairs, multiple DOCX and ZIP upload.
Input ZIP safety, recursive discovery, ignored temporary files and topic pairing
remain unchanged. An input ZIP is not an output archive delivery request.

## Result

- Publish validated, nonempty DOCX to the existing stable local result directory.
- Mark an item `done` only after its required role outputs pass validation.
- Keep readable topic directories, unique task/topic suffixes and role filenames.
- Preserve successful siblings when another item fails; expose `partial`.
- Show topic total, successful/failed counts, each item outcome, local path and
  **打开成品文件夹**. C1 single/pair jobs keep their existing role display.
- `/api/open/<job_id>` opens the local task folder, including partial results.
- Remove output ZIP creation, download buttons/links and `/api/download/<job_id>`.
  The former route returns the normal 404 response.
- Remove `download_available`, `delivery_status`, `delivery_error_code` and
  `delivery_error`; strip these obsolete fields when recovering historical jobs.
  An old download failure has no bearing on valid local DOCX results.

No browser download, external download manager or output ZIP is part of this
product's result delivery gate. Internal runtime records remain outside the
user's DOCX directory. Generation failures continue to use `GENERATION_FAILED`.

## Gate

Re-test real multi-DOCX and Chinese nested ZIP submissions in a headed browser:
polling, correct grouping and roles, successful/partial outcomes, clean local
DOCX directories and actual Open Folder. Assert no output-download UI or route,
and no obsolete download fields. Re-run focused, Stage2/Stage3 and frozen-asset
gates. Independent Chief is Codex GPT-6.1 Sol only.

# C4-R3 publication PATCH — 2026-10-02

## Trigger

The supplied real packaged-job evidence for job
`ee4a1afacb6b46d39d9fa414569d16a5` showed XML rendering completed, but teacher
DOCX publication failed when staging was on `C:` and the redirected Desktop
result folder was on `D:`. Windows raised `WinError 17` while the application
called `os.replace(staged_path, final_path)`:

```text
OSError: [WinError 17] 系统无法将文件移到不同的磁盘驱动器。
'C:\Users\Administrator\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\讲义生成器\jobs\ee4a1afacb6b46d39d9fa414569d16a5\work\teacher-output-ee4a1afacb6b46d39d9fa414569d16a5.docx'
->
'D:\Documents\生成讲义结果\2026-2027学年 高一 化学 化学实验与科学探究 复习讲义\2026-2027学年 高一 化学 化学实验与科学探究 复习讲义 教师版.docx'
```

The result directory was empty after failure. The source files were unchanged.
The supplied job was a renamed teacher/student pair classified as
`TEACHER_AND_STUDENT`; student preparation was `BYPASS`, and the renderer was
XML. No packaged, browser, Word/WPS, or end-to-end UAT was run for this PATCH.

## Change

Final publication now copies the validated staged bytes to a uniquely named
temporary file created in the final result directory. Before publication, the
temporary copy must be non-empty, match the staged size and SHA-256, and pass
the existing DOCX package validator. Only then does `os.replace` rename that
same-directory temporary file to the final name. A `finally` block removes a
temporary file after copy or validation failure. The final target is not
overwritten if an existing artifact fails the prior recovery/adoption checks.

At job restart, abandoned temporary publication copies matching that job ID
are removed from its result directory before work resumes. Already published
teacher/student siblings continue through the existing hash/package validation
and adoption flow; cleanup is restricted to the job-specific temporary-name
prefix.

## Machine evidence

- Focused cross-volume publication, validation-failure cleanup, teacher/student
  role, and restart selection: **5 passed**.
- C0 job service, batch job service, and Studentizer integration selections:
  **58 passed**.
- `py_compile` for the changed Python files: PASS.
- `node --check` for `workspace.js`: PASS.
- `git diff --check`: PASS.
- No EXE build, packaged startup, browser run, Word/WPS run, or whole-job UAT
  was performed.

The tests simulate the Windows cross-volume failure boundary by making a direct
staged-source-to-final `os.replace` raise WinError 17, then assert that the
implementation replaces a verified temporary file whose parent is the final
result directory. Teacher and student role cases both pass.

## Scope and review

This patch changes only final DOCX publication and its focused regression
coverage. It does not change A-Line, C1, B-Line, Studentizer, Renderer, frozen
V0.9 assets, launcher, or package contents. The original Chief verdict was
`PATCH`; this implementation is awaiting Codex GPT-6.1 Sol re-review. No C4
release or RC pass is claimed.

- Base: `9f7569b3a28d09a59e844a4bc5131ba5acfc23cf`
- Implementation commit: `8a71d197037e40b32b15942418808f138fc3541a`

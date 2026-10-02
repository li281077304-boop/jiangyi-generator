# C4 P0 — Recursive Output Root Cause Report

Date: 2026-10-02

## Decision

**P0 confirmed. C4 Release remains blocked.** The two high-school-labelled files
in the incident are the outputs of Restart C item 1. Their actual input was not
an immutable source handout: it was a previously published V1.2 teacher
output copied into the Restart C fixture and submitted again. That re-ingestion
added another full template/body sequence. The input already contained two
template sequences; the latest output contains three.

This is not safe to classify as fixture selection alone. The retained job for
the earlier V1.2 generation shows an input with one template sequence and a
V0.9 whole-job fallback output with two. Therefore the evidence shows two
contributing failures:

1. **Core generation duplication:** the earlier V0.9 fallback generation
   turned one template-bearing input sequence into two.
2. **UAT fixture recursive re-ingestion:** Restart C selected that earlier
   generated output as its input, increasing the count from two to three.

The immediate incident is `UAT_FIXTURE_RECURSIVE_REINGESTION`; the earliest
observed duplication is `CORE_GENERATION_RECURSIVE_DUPLICATION`. The available
records do not prove that a no-template immutable source has ever completed
one production pass safely. Do not treat this report as a release clearance.

## Incident identity and lineage

User-confirmed outputs:

| Role | Published path | Size | SHA-256 |
|---|---|---:|---|
| Teacher | `D:\Documents\生成讲义结果\2026-2027学年 高一 数学 批量讲义 复习讲义（2）\恢复单元1 数学专题A\2026-2027学年 高一 数学 恢复单元1 数学专题A 复习讲义 教师版.docx` | 1,144,362 bytes | `642410d183aada285c6f9aaffcf5a4ec55c1a1e1aae1074732c7210238ed694e` |
| Student | `D:\Documents\生成讲义结果\2026-2027学年 高一 数学 批量讲义 复习讲义（2）\恢复单元1 数学专题A\2026-2027学年 高一 数学 恢复单元1 数学专题A 复习讲义 学生版.docx` | 610,485 bytes | `375ab0e646daef7510fd6d0a0a514e4782ae56c5753da33ed85247b4bc1620bc` |

The paths, sizes, timestamps and SHA-256 values match the persisted Restart C
parent and child publication records exactly.

| Field | Evidence |
|---|---|
| Parent batch job | `c5082aea3ee346f7bc1d99ce496a47aa` |
| Batch item | `1`, topic `恢复单元1 数学专题A` |
| Child job | `1e66041e74df4a6085f0e0601a314cd5` |
| Generation attempt | `1` |
| Classification | `TEACHER_ONLY`, evidence `teacher_filename` |
| Teacher input used by child | `%LOCALAPPDATA%\讲义生成器\jobs\1e66041e74df4a6085f0e0601a314cd5\work\input-1.docx` |
| Student input | None; student source was prepared by `V09_MAKE_STUDENT` |
| Upload origin | `中文两项批次.zip:专题批次/恢复单元1 数学专题A 教师版.docx` |
| Uploaded ZIP SHA-256 | `8547428ac7aee90641989eeec527461f24c591f520b528f69036ed3c0ad196d5` |
| Item renderer | `V0.9`, whole-job fallback |
| Fallback reason | `XML_RENDER_FAILED` |
| Fallback detail | `TABLE_SLOT_CONFLICT: generic heading and practice content share atomic table b2` |
| Student preparation reason | `STUDENTIZER_COVERAGE_UNPROVEN` |

## Input identity and provenance

The ZIP entry, `restart-C-fixture` copy, `restart-C-minimal-staging` copy, and
the child job's staged teacher input are byte-identical:

- Filename: `恢复单元1 数学专题A 教师版.docx`
- Size: 1,107,127 bytes
- SHA-256: `8c3561df2bb560cb12aaf5c76a39bc1b517cfa6580413cd576211d2c1806cca4`
- Original prior published path:
  `D:\Documents\生成讲义结果\2026-2027学年 七年级 数学 X012真实数学讲义 复习讲义\2026-2027学年 七年级 数学 X012真实数学讲义 复习讲义 教师版.docx`

The prior path is a generated-results directory. The retained earlier job record
confirms that this SHA was a published teacher output:

- Prior job: `302596d864a2455b8cfd44da048fca8a`
- Input filename: `X012真实数学讲义.docx`
- Input SHA-256: `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779`
- Job options: 七年级 / 数学 / 1v1
- Renderer: `V0.9`, reason `XML_RENDER_FAILED`
- Output SHA-256: `8c3561df2bb560cb12aaf5c76a39bc1b517cfa6580413cd576211d2c1806cca4`
- Output path: the prior published path above

Thus the exact immediate Restart C input was a previously generated output, not
the original `X012真实数学讲义.docx` and not a teacher source selected from an
immutable corpus. It carries old 七年级 content while Restart C metadata labels
the new output 高一. The Restart C fixture was made from a file under
`D:\Documents\生成讲义结果`, and the submitted ZIP contains the same hash.

## First observed contamination and per-stage counts

Counts below use main-story `word/document.xml` paragraphs, retaining empty
paragraphs. Text lengths count extracted `w:t` text. The section/template
fingerprints are evidence of repeated content, not the sole identity proof.

| Stage | SHA-256 | Main-story paragraphs | Text chars | Template title | 课堂启动 | 知识回顾 | 知识精讲 | 即时训练 | 归纳总结 | 巩固练习 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Earlier job 302596 input | `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779` | 952 | 14,768 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Earlier job 302596 teacher output / Restart C source | `8c3561df2bb560cb12aaf5c76a39bc1b517cfa6580413cd576211d2c1806cca4` | 1,411 | 22,787 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |
| Restart C teacher output | `642410d183aada285c6f9aaffcf5a4ec55c1a1e1aae1074732c7210238ed694e` | 1,870 | 30,800 | 3 | 3 | 3 | 3 | 5 | 5 | 5 |
| Restart C student output | `375ab0e646daef7510fd6d0a0a514e4782ae56c5753da33ed85247b4bc1620bc` | 478 | 5,957 | 0 | 3 | 3 | 3 | 2 | 5 | 5 |

The first observed extra full sequence is already present at the earlier
job's published output: its input has one complete section sequence and its
teacher output has two. The Restart C output contains one more. The
teacher-output paragraph count rises from 1,411 to 1,870 and extracted text
from 22,787 to 30,800 characters. This identifies the first added sequence in
Restart C at its `V0.9` whole-job renderer stage; it was not introduced by
Restart recovery, which did not resume item 1 (attempt 1, completed before the
kill).

## Executed generation path

For Restart C item 1, the persisted job fields show `TEACHER_ONLY`,
`V09_MAKE_STUDENT`, then `renderer=V0.9` after XML failed closed on
`TABLE_SLOT_CONFLICT`. The route in `webapp/app.py` records the fallback and
calls `render_v09_whole_job`; `renderer_orchestrator.py` passes the original
teacher source to the frozen `engine.build_version` and separately calls
`engine.make_student` / `engine.build_version` for the derived student source.
The frozen V0.9 `build_version` scans the supplied source into `paras`, splits
those paragraphs, and invokes its template Writer. The XML preflight and
Slot Router did not produce the published Restart C files.

In the earlier job 302596 the same fallback route ran on the one-template
input SHA `79d925...`. The output SHA `8c3561...` is an exact published artifact
and was then selected as the Restart C source. This establishes both the
copy-through of an already templated source by the whole-job Writer and the
fixture's recursive source selection. V0.9 assets themselves have not been
modified in this investigation.

## Why existing gates missed it

- Package validation checks OOXML/package integrity, not whether a complete
  template appears multiple times. Both Restart C outputs passed package
  validation and were marked done.
- The retained WPS roundtrip record `evidence\wps-final\fallback-math-roundtrip.json`
  contains a `cover_sample` with two `学 科 教 师 辅 导 讲 义` sequences and
  repeated sections. Its PASS fields certify Open → SaveAs → Close → Reopen →
  PDF and structural counts; they did not evaluate product-level template
  recursion. This was evidence available to the prior gate but not a rejection
  condition.
- The Restart C source was selected from the generated-results directory,
  then copied into a fixture and ZIP without immutable-source provenance.
- No product-integrity gate checked repeated long block sequences, template
  fingerprints, stale grade/topic text, or source-to-output expansion.

## Classification, scope, and next action

- Immediate incident classification: `UAT_FIXTURE_RECURSIVE_REINGESTION`.
- Earliest observed duplication classification: `CORE_GENERATION_RECURSIVE_DUPLICATION`.
- This is therefore a **mixed cause**, not a justified Case A-only closure.
- Do not modify the Renderer, V0.9 Writer, Splitter, Router, or Studentizer in
  this diagnosis round. Chief review must decide whether the evidence is
  sufficient to enter a narrowly scoped fix and whether C1/C2/C3 trust must be
  downgraded.
- Minimum next step after Chief PASS: add source provenance and input/output
  product-integrity rejection, then test immutable source, the one-template
  source, and the prior generated artifact through their applicable routes.

Evidence files read (no new generation, WPS UAT, or regression was run):

- `C:\xml-uat\c4-final-rc-final\evidence\restart-C-d3511a0\prekill-parent.job.json`
- `C:\xml-uat\c4-final-rc-final\evidence\restart-C-d3511a0\prekill-child-1.job.json`
- `%LOCALAPPDATA%\講義生成器\jobs\302596d864a2455b8cfd44da048fca8a\job.json`
- `C:\xml-uat\c4-final-rc-final\evidence\wps-final\fallback-math-roundtrip.json`
- `C:\xml-uat\c4-final-rc-final\inputs\restart-C-minimal\中文两项批次.zip`

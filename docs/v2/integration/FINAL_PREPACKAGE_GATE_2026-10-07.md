# FINAL PRE-PACKAGE GATE — 2026-10-07

Evaluated code HEAD: `c4f2a8805137959725db0703569abd426d93016d`. Production code was not modified.

**Result: XML 2/33 (6.06%), FAIL.** The required 90% threshold needs at least 30/33. No V0.9 result is counted; V0.9 diagnostic mode was disabled for all submissions.

## Denominator and method

The unchanged frozen manifest contains 13 role-deduplicated fixed topics and 20 additional topics. All 67 source member SHA-256 values matched the manifest before execution. Each topic used the first teacher/answer-rich and first student/original-paper member in frozen order. No topic was excluded, including the upload safety rejection.

Each pair was submitted through the current Flask `/api/jobs` production boundary with `template_type=1v1`, `split_mode=smart`, `docx_mode=auto`; synchronous scheduling changed only the test execution timing. XML-only mode remained enabled. This is an HTTP application evaluation via Flask test client, not real-browser or EXE evidence. Class/browser/package gates were not reached. Cover grade/year selection is evaluation metadata and is not a claim of correct per-topic visual UAT.

A success requires status done, renderer XML, both published final DOCX nonempty, Product Integrity accepted, exact publication/actual final SHA-256 agreement, and a fresh package validator PASS. All four DOCX for the two successful topics passed these checks.

## Exact results

| # | Frozen topic | Result | Exact production reason |
|---|---|---|---|
| 1 | 1.1 物质的变化和性质 第1课时(讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: explicit student subquestion has no unique complete teacher counterpart |
| 2 | 1.1 物质的变化和性质 第2课时(讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 3 | 1.2 化学实验与科学探究(题型专练) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired input has no question-group sequence |
| 4 | 2.1 我们周围的空气 第1课时(讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrence labels/order differ |
| 5 | 2.2 氧气(讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: explicit student subquestion has no unique complete teacher counterpart |
| 6 | 专题02 电压 电阻&欧姆定律(期末复习讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 7 | 专题04 电功率(期末专项训练) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrences contain different explicit subquestion sets |
| 8 | 专题1.5 有理数的乘除(高效培优讲义)数学新教材沪科版七年级上册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrences contain different explicit subquestion sets |
| 9 | 专题1.6 有理数的乘方与近似数(高效培优讲义)数学新教材沪科版七年级上册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: ordered question occurrence stems do not match by an allowed exact relation |
| 10 | 专题12.4 一次函数的实际应用(高效培优讲义)数学新教材沪科版八年级上册 | PASS | XML done; both final DOCX package/Product Integrity/publication hash PASS |
| 11 | 九年级上学期物理期末复习(易错精选60题27大考点) | PASS | XML done; both final DOCX package/Product Integrity/publication hash PASS |
| 12 | 第2节 分子动理论的初步知识(培优考点练) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: teacher continuation has multiple exact structural counterparts |
| 13 | 第3节 串联和并联 (培优考点练) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: teacher continuation has multiple exact structural counterparts |
| 14 | 专题05 二元一次方程组 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 15 | 专题10 新定义型答案 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrences contain different explicit subquestion sets |
| 16 | 专题06 二元一次方程组的应用 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrences contain different explicit subquestion sets |
| 17 | 专题08 不等式与不等式组应用 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 18 | 专题02 平行线模型和辅助线 专题专练【重难点培优:知识梳理+8大题型+压轴真题】2025-2026学年人教版数学七年级下册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired sources contain different real question occurrence counts |
| 19 | 专题07 不等式与不等式组 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 20 | 专题04 平面直角坐标系 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 21 | 专题01 相交线与平行线中的几何综合 专题专练【重难点培优:知识梳理+7大题型+压轴真题】2025-2026学年人教版数学七年级下册 | FAIL | DOCX 展开大小超过安全上限 |
| 22 | 专题09 规律探索型 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired sources contain different real question occurrence counts |
| 23 | 专题11 存在性问题 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: paired question occurrences contain different explicit subquestion sets |
| 24 | 专题03 实数相关 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: student numbered source candidate lacks one unique teacher occurrence |
| 25 | 2026-2027年人教版物理九年级第十三章第二节 分子动理论的初步知识 (讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: teacher annotation piece has no unique preceding canonical question |
| 26 | 15.2 电流和电路(讲义)2026-2027年人教版物理九年级全一册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 27 | 15.4 电流的测量(讲义)2026-2027年人教版物理九年级全一册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 28 | 2026-2027年人教版物理九年级第十三章第三节 内能 (讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: teacher annotation piece has no unique preceding canonical question |
| 29 | 15.3 串联电路和并联电路(讲义)2026-2027年人教版物理九年级全一册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 30 | 2026-2027年人教版物理九年级第十三章第一节 热量 比热容 (讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 31 | 13.3 热机效率(讲义)2026-2027年人教版物理九年级全一册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 32 | 15.1 两种电荷(讲义)2026-2027年人教版物理九年级全一册 | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_AMBIGUOUS: ALIGNMENT_AMBIGUOUS: recovered question range contains another top-level question start |
| 33 | 2026-2027年人教版物理九年级第十四章第二节 热机 (讲义) | FAIL | GENERATION_FAILED: XML_UNSUPPORTED: ALIGNMENT_UNRESOLVED: ALIGNMENT_UNRESOLVED: teacher annotation piece has no unique preceding canonical question |

## Failure distribution

- ALIGNMENT_UNRESOLVED: 22 topics.
- ALIGNMENT_AMBIGUOUS: 8 topics.
- Input DOCX expanded-size safety limit: 1 topic.
- Total unsuccessful topics: 31/33; safe rejection, no V0.9 invocation.

Full exact node/candidate evidence, selected source roles/hashes, job IDs, successful final file hashes, and package checks: `fixtures/final-prepackage-20261007/coverage_summary.json`. Raw job snapshots and runtime/source/output evidence remain under `C:\xml-uat\final-prepackage-20261007\`; the summary binds their SHA-256.

## Ordered stop

The coverage gate failed. Direct DOCX/ZIP browser matrix, representative visual checks, WPS round trips, final full regression, Windows build/RC ZIP, and real EXE UAT were NOT RUN in this gate. Prior sample checks are not substituted for these missing current-candidate gates. No feature, algorithm, alignment rule, or frozen boundary was changed. No tag, release, new branch, EXE, or package was created.

# C4 P0 — Real Incident Content Gate Evidence

Date: 2026-10-02
Production integrity implementation: `e6c921aa84994aba27acbb511eac4872f5c1fb31`

This is a read-only check against retained real DOCX files. No document was regenerated; no WPS, restart, or release activity was run. The metrics come from the new `product_integrity` functions and the SHA-256 values are computed from the exact files below.

| Evidence | SHA-256 | Main-story paragraphs | Text chars | Template titles / complete cycles | Gate result |
|---|---|---:|---:|---:|---|
| Original `X012真实数学讲义.docx` | `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779` | 952 | 14,768 | 1 / 1 | accepted as an input |
| Previous published V0.9 teacher output, also Restart C input | `8c3561df2bb560cb12aaf5c76a39bc1b517cfa6580413cd576211d2c1806cca4` | 1,411 | 22,787 | 2 / 2 | input rejected as `POSSIBLE_GENERATED_OUTPUT_REINGESTION`; output against the original source rejected as `PRODUCT_TEMPLATE_RECURSION`, `PRODUCT_TEMPLATE_RESIDUE`, and `PRODUCT_REPEATED_BLOCK_SEQUENCE` |
| Restart C final teacher output | `642410d183aada285c6f9aaffcf5a4ec55c1a1e1aae1074732c7210238ed694e` | 1,870 | 30,800 | 3 / 3 | input rejected; product gate rejected with all three recursive/repeated-content codes |
| Restart C final student output | `375ab0e646daef7510fd6d0a0a514e4782ae56c5753da33ed85247b4bc1620bc` | 478 | 5,957 | 3 / 2 | input rejected; product gate rejected with all three recursive/repeated-content codes |

The Restart C input was the exact prior V0.9 teacher artifact (`8c3561...`), verified by hash. The new pre-generation input gate rejects it before Studentizer or Renderer. The retained Restart C teacher and student outputs are independently rejected by the output gate. The preceding clean original is accepted as a source, while its retained V0.9 output is rejected as a product; this separates the original-source path from re-ingestion.

This validates the new detection logic against the actual incident source and both actual incident outputs without rerunning the Restart C workload. It does not certify what a fresh real renderer invocation would produce for a clean source; controlled runtime output validation, WPS, and release UAT remain outside this P0 repair. C4 Release remains paused.

Evidence paths on this machine:

- `C:\xml-uat\c4-final-rc-final\inputs\X012真实数学讲义.docx`
- `C:\xml-uat\c4-final-rc-final\inputs\restart-C-minimal-staging\专题批次\恢复单元1 数学专题A 教师版.docx`
- `D:\Documents\生成讲义结果\2026-2027学年 七年级 数学 X012真实数学讲义 复习讲义\2026-2027学年 七年级 数学 X012真实数学讲义 复习讲义 教师版.docx`
- `D:\Documents\生成讲义结果\2026-2027学年 高一 数学 批量讲义 复习讲义（2）\恢复单元1 数学专题A\2026-2027学年 高一 数学 恢复单元1 数学专题A 复习讲义 教师版.docx`
- `D:\Documents\生成讲义结果\2026-2027学年 高一 数学 批量讲义 复习讲义（2）\恢复单元1 数学专题A\2026-2027学年 高一 数学 恢复单元1 数学专题A 复习讲义 学生版.docx`

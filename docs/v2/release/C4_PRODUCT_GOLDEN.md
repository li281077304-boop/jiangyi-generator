# C4 PRODUCT_GOLDEN (minimal, first version)

Purpose: stop "408/408 green but the final DOCX is visibly broken". A golden
entry binds a source SHA to what the finished handout must contain, so a future
regression is caught by content, not by package validity.

Not byte-identical. Content-level expectations only.

## Entry format

| field | meaning |
|---|---|
| `source_sha256` | SHA-256 of the immutable corpus source |
| `role` | `teacher` / `student` |
| `expected_sections` | ordered section headings that must appear |
| `critical_source_presence` | substrings that must survive from the source |
| `forbidden_duplicate_template` | max allowed `学科教师辅导讲义` titles / complete cycles in the output |
| `forbidden_residual_metadata` | template placeholders that must not survive (示例/示例专题/待填写) |
| `expected_studentization` | answer-marker count expected in this role |
| `acceptable_expansion` | output text chars ÷ source text chars range |

## Established entries (measured 2026-10-03)

### G1 — 化学 高一 解析版 (XML route)
```
source_sha256        19fe81bd43f19e9acb2170b2d431452690c179cbecb4e4ee773f8e024eef0163
role                 teacher
expected_sections    一、课堂启动, 二、知识回顾, 知识精讲&例题讲解, 即时训练, 五、归纳总结, 六、出门测试
critical_source_presence   题型01 实验室安全及处理, 【详解】, 故选
forbidden_duplicate_template   template_titles <= 1, template_cycles <= 1
forbidden_residual_metadata    示例专题, 示例年级
expected_studentization        teacher: 113 answer markers;  student: 0
acceptable_expansion           0.8 – 1.5   (measured 20389 -> 20938 = 1.03)
```

### G2 — 数学 高中 计数原理 解析版 (XML route)
```
source_sha256        bfcec1ef64ec9d6d…   (see PRODUCT_SOURCE_CORPUS.json S03)
role                 teacher
expected_sections    一、课堂启动, 二、知识回顾, 知识精讲&例题讲解, 即时训练, 五、归纳总结, 六、出门测试
critical_source_presence   题型1  两个计数原理, 故选
forbidden_duplicate_template   template_titles <= 1, template_cycles <= 1
forbidden_residual_metadata    示例专题, 示例年级
expected_studentization        teacher: 270 answer markers;  student: 0
acceptable_expansion           0.8 – 1.5   (measured 23186 -> 23752 = 1.02)
KNOWN DEFECT: immediate=0, final=0 — 即时训练/归纳总结/出门测试 are empty shells.
This entry is recorded with the defect flagged, not as a clean baseline.
```

### G3 — 物理 九年级 解析版 (V0.9 fallback route)
```
source_sha256        b5e217e9a2311d39…
role                 teacher
expected_sections    一、课堂启动, 二、知识回顾, 知识精讲&例题讲解, 即时训练, 五、归纳总结, 六、巩固练习
critical_source_presence   【答案】, 【详解】, 比热容
forbidden_duplicate_template   template_titles <= 1, template_cycles <= 1
forbidden_residual_metadata    示例专题, 示例年级
expected_studentization        teacher: 58 answer markers;  student: 0
acceptable_expansion           0.8 – 1.5   (measured 11609 -> 12267 = 1.06)
```

### G4 — X012 数学 (BLOCKED, target entry)
```
source_sha256        79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779
role                 teacher AND student
expected_sections    一、课堂启动, 二、知识回顾, 知识精讲&例题讲解, 即时训练, 五、归纳总结, 六、出门测试
critical_source_presence   【变式3】, 【答案】, 【分析】
forbidden_duplicate_template   template_titles <= 1, template_cycles <= 1
forbidden_residual_metadata    示例专题, 示例年级
expected_studentization        teacher > 0 answer markers;  student: 0
acceptable_expansion           0.8 – 1.5
CURRENT STATUS: NO OUTPUT. XML route raises TABLE_SLOT_CONFLICT; the V0.9
fallback produces template_titles=2, template_cycles=2 and a 373-paragraph
repeated block, so the gate rejects it. This entry must move from BLOCKED to
measured before C4 can be restored.
```

## How to re-check a golden

```
python tools/c4_product_recovery/repro_table_layout_block.py <source.docx>
```
for routing, then read the finished DOCX with `inspect_content.py` (first/last
paragraphs, section order) and count answer markers per role.

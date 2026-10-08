# XML rescue — first real failed topic

Status: **P1_FIRST_REAL_TOPIC_XML_PASS**. Broader corpus and WPS/final EXE gates remain pending.

Base checkpoint: `9c646b4b87c1c4cd637c978f99aef21044bd5e47`. Main is unchanged.

Ordinary submissions now default to automatic XML processing. The UI has no engine selector. Internal legacy modes are retained for reproducible diagnostics; they are not ordinary UI choices.

## Actual chain

1. NAVIGATION: explicit teaching headings with Word heading/outline information. Physical tables are never used as independent cell boundaries.
2. SEMANTIC: existing A-Line snapshot and Slot Router. A degraded question-splitting strategy does not qualify as reliable semantic routing.
3. RULES: explicit plain-text teaching headings, validated against existing complete question/shared-material ownership. Ordinary question/body paragraphs are not interpreted as headings.
4. PRESERVATION: an internal structural snapshot routes the complete original body in source order into the template; no uncertain splitting or display renumbering. This uses the existing XML importer/composer, not renamed source bytes.
5. V0.9: only after XML technical rendering/package/capability failure. Rendering a structured plan can first retry original-body preservation. Both renderers still pass shared product normalization and final product/package/publication gates.

Each role uses only its own source and its own extracted cover metadata. Pair alignment is recorded as `NOT_REQUIRED_NOT_VERIFIED`; source numbering stays unchanged. Global unowned answer sections and ambiguous group/table boundaries degrade to preservation rather than crossing modules. Teacher-only preparation supplies a student source only when the reviewed complete Studentizer proves it safe. Otherwise the teacher is delivered with an explicit missing-student warning; compatibility rendering also supports teacher-only output without calling unsafe make_student.

## Real first-case improvement

Frozen topic: X017/X018, “1.1 物质的变化与性质 第1课时（讲义）”. Previously refused with `ALIGNMENT_UNRESOLVED: explicit student subquestion has no unique complete teacher counterpart`.

Current production app submissions with the pinned C4 runtime dependencies produced **XML teacher/student for both 1v1 and class**. All four actual outputs passed product integrity and package validation. This stage used the production API in a synchronous test-client runner, not a packaged EXE; that evidence distinction is explicit.

Source hashes were verified against the frozen manifest before submission. Selected tiers, job IDs, final paths/hashes/sizes and warnings are committed in `fixtures/product-rescue-20261008/p1_first_real_topic.json`. Raw per-job evidence and DOCX outputs are under `C:\xml-uat\product-rescue-p1-candidate-first-20261008`.

## Tests and limits

- Existing C0/batch plus degradation checks: **46 passed**.
- Additional actual production composition tests: **2 passed**; unrelated paired text and metadata stay isolated, and an unproven teacher-only input produces only a validated teacher.
- Frozen V0.9 assets remain **10/10**. No A-Line, canonical alignment, frozen Writer, template or OCR algorithm was changed.
- The 33-topic evaluation, independent single-input statistics, new-content WPS round trips and rebuilt final EXE remain pending. No release or general XML coverage PASS is claimed.

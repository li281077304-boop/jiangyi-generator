# V1.2 Closeout — knowledge-review first-page anchor

## STATUS

Layout fix verified at source level on real production rendering. The
"二、知识回顾" separator heading now sits in the bottom safe area of page one in
both templates, with **0.000pt** deviation from the measured target on the real
rendered DOCX. Frozen features (cover budget, display renumbering, six modules,
1/2/5 blanks, Product Integrity) show no regression. EXE build and EXE UAT are
recorded separately.

Base: `ddfab91e5dff75b5f371da8e23d971b864e6f58a`
Branch: `feature/v1.2-c4-release-engineering`

## ROOT CAUSE OF THE PREVIOUS ROUND

The previous round restored the frozen template's own Y (1v1 396.928pt /
class 453.449pt) and correctly reported that position as *stable*. It could not
report it as *correct*: the frozen templates themselves draw that heading near
the middle of page one. See
`FINAL_POLISH_FIRST_PAGE_AND_RENUMBER_2026-10-05.md`, which states the templates
"place this title around the middle of the first page, rather than at the page's
bottom edge".

Structurally, `一、课堂启动` and `二、知识回顾` are consecutive paragraphs of the
**same** merged content cell (`table.rows[5].cells[0]`, paragraphs `p00` and
`p05`). The gap between them is a run of four spacer paragraphs `p01..p04`
(two empty paragraphs, one line of spaces, one line of `~`). That spacer block
is the only lever needed, and it is **not** part of any routed slot span — the
slot payload is inserted after the `知识精讲…` anchor at `p20` (1v1) / `p17`
(class).

## MEASURED PAGE GEOMETRY

Measured from the frozen templates read-only, and from WPS 12.0 PDF exports.

| Item | 1v1 | class |
|---|---:|---:|
| Page height | 841.90pt | 841.90pt |
| Top margin | 28.80pt | 101.20pt |
| Bottom margin | 49.65pt | 72.00pt |
| Footer distance | 14.20pt | 49.60pt |
| **Footer band top (body usable bottom)** | **792.25pt** | **769.90pt** |
| Heading font | 14pt (sz=28) | 14pt (sz=28) |

## FINAL LAYOUT

The clamp fixes the exact line height of each existing spacer interval. Each
spacer is a separate `w:p` whose `w:spacing` after `w:lineRule="exact"` governs
the distance to the next paragraph; setting all four intervals produces a clean
1:1 relationship to the heading Y.

| Template | **KNOWLEDGE_REVIEW_TARGET_Y** | Spacer pt | Measured heading y0 | **Measured heading y1** | Footer band top | Clearance | Page 1 |
|---|---:|---:|---:|---:|---:|---:|---|
| 1v1 | **768.219** | 120.5 | 754.169 | **768.219** | 792.25 | 24.031pt | yes |
| class | **745.899** | 100.8 | 731.849 | **745.899** | 769.90 | 24.001pt | yes |

Target Y is the PDF text bottom (y1) of the heading, held 24pt above the footer
band top so it never touches the footer rule or the page number. Values differ
per template because the two templates have different top/bottom margins and
different content-cell start offsets — the anchor is genuinely
template-specific, not a relative offset.

Measured on the real rendered production DOCX (17 pages / 20 pages of content):

| Case | Template | Target y1 | Measured y1 | Deviation |
|---|---|---:|---:|---:|
| training-1v1 | 1v1 | 768.219 | 768.219 | **0.000** |
| training-class | class | 745.899 | 745.899 | **0.000** |

Probe series retained in `anchor-probe-result.json`; the class spacer block
overflowed to page two at 104pt, so 100.8pt sits inside the template's own
capacity rather than on a page-break edge.

## IMPLEMENTATION SCOPE

Changed: `v1.2-xml-experiment/res/app/template_slot_composer.py`
(`KNOWLEDGE_REVIEW_TARGET_Y`, `KNOWLEDGE_REVIEW_SPACER_PT`,
`_resolve_content_carrier`, `_anchor_knowledge_review`,
`_set_exact_interval`, plus a `knowledge_anchor` field on
`SlotRenderResult`) and `v1.2-xml-experiment/res/app/test_final_polish.py`.

`_resolve_content_carrier` exists because `render_slots` runs on the *rendered
output*, which already carries the imported source blocks at the body tail. A
"exactly one table" test therefore fails closed on every source that contains a
table. The frozen template carrier is identified by its own structure instead:
row 5 is one merged cell whose first paragraph is `一、课堂启动` and whose sixth
paragraph is `二、知识回顾`. Imported tables are ignored and a moved template
still fails closed with `TEMPLATE_KNOWLEDGE_ANCHOR_UNRESOLVED`.

The anchor runs on the **output copy only**, before the slot payload is
inserted, and:

- adds **no** paragraph (verified: paragraph list length is unchanged and only
  indices 1..4 differ);
- changes **no** page size, margin, footer, header distance, font or font size;
- changes **no** cover row height (the `EXACTLY` lock on rows 2/3 is untouched);
- never writes to the frozen template file.

It is deterministic, template-specific, and WPS-verified. No pagination engine,
no renderer refactor, no A-Line change.

## FROZEN FEATURE REGRESSION

| Feature | Result |
|---|---|
| Cover display budget (1 line / 76 & 68 units) | unchanged; rows 2/3 still `EXACTLY` 23.9/23.9 and 25.7/27.8 |
| Display renumbering, module 3 | source 1,5,10,… → display 1–8 |
| Display renumbering, module 4 | source 2,6,11,… → display 1–8 |
| Display renumbering, module 6 | source 3,4,7,… → display 1–18 |
| Total questions | 34, no loss, no duplication, identical in both templates |
| Teacher/student source-node map | present for every row, both roles |
| Six modules | present in both templates |
| 1/2/5 blank regions | present (placeholder runs retained) |
| Product Integrity | accepted, no errors |

## SOURCE PRODUCT GATE

| Case | Template | Route | Result |
|---|---|---|---|
| training-only real physics pair (X008/X007) | 1v1 | XML | PASS |
| training-only real physics pair (X008/X007) | class | XML | PASS |
| `X012真实数学讲义.docx` SHA-256 `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779` | 1v1 | fail-closed | `SlotRoutingError: generic heading and practice content share atomic table b2` |
| Physics 热量比热容 knowledge lesson (解析版) | class | fail-closed | `SlotRoutingError: unclassified section at b192: 【巩固训练】` |

Both fail-closed cases are pre-existing XML limitations of this round's frozen
scope, not regressions: `X012` is the documented `TABLE_SLOT_CONFLICT` P0 sample,
and the 热量比热容 case is an unclassified-section refusal. Neither is a P0/P1
release blocker for this round; both fall back to the frozen V0.9 whole-job path
with a persisted reason. See `POST_V1.2_BACKLOG`.

## TESTS

- Focused: `test_final_polish.py` **16 passed** (6 new anchor tests, including
  one that appends an imported table to the body and asserts the anchor still
  resolves the frozen carrier).
- Full regression at the repository root: **460 passed, 6 failed, 7 subtests
  passed**.
- All 6 failures are **PRE_EXISTING**: a detached worktree at the unmodified
  `ddfab91` tree produces **the same 6 failures** (454 passed).
  - `tests/test_studentizer_production_registry.py::test_real_renderer_refusal_persists_exact_reason_and_uses_original_teacher`
  - `tests/test_windows_launcher.py::test_server_child_starts_with_isolated_runtime_and_exits_via_control_api`
  - `v1.1-stable/res/app/webapp/test_app_api.py` (4 tests; this tree is never
    touched by this change, and the file passes 5/5 when run in isolation)
- XML coverage sweep over the release corpus (`X001`–`X027`, 1v1, production
  `render_slots` path): **22/27 XML_OK before and 22/27 after**, with an
  identical failing set (`X005`, `X006`, `X011`, `X026`, `X027`). No XML
  coverage regression.
- `py_compile` clean for both changed files; `git diff --check` clean.

## EVIDENCE

Round evidence root: `C:\xml-uat\v12-closeout-20261006`
(`target-measurement.json`, `anchor-probe-result.json`, `source-gate-result.json`,
`source-gate-layout.json`, `source-gate-product.json`, `renumber-result.json`,
WPS PDFs and page-one PNG snapshots).

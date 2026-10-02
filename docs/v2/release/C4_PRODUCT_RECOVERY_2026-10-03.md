# C4 Product Recovery — 2026-10-03

**STATUS: `C4_PRODUCT_BLOCKED`**

Branch: `feature/v1.2-c4-release-engineering`
Base of this round: `ab3127bb3fa1b63cdff0bb09212cb2ee614fef7a`
P0 fix commit in history: `e6c921aa84994aba27acbb511eac4872f5c1fb31`

P0 gate hardening works. That is not the same thing as a correct product: on a
clean, immutable source corpus the current source build still cannot produce a
usable handout for three of six real sources, and the P0 sample X012 itself
produces **no file at all**.

---

## 1. Blocker (one sentence)

A real 讲义 whose body lives inside one large layout table cannot be routed by
the XML path, and the V0.9 whole-job fallback then duplicates the source's own
template, so `PRODUCT_INTEGRITY_GATE` rejects the result and the user receives
nothing.

---

## 2. Source corpus (immutable, provenance verified)

Built by `tools/c4_product_recovery/` + the corpus manifest recorded in this
round. Every byte is a 学科网 download or the documented original X012. Every
file was cross-checked against **all** DOCX under
`D:\Documents\生成讲义结果` and `C:\xml-uat` (1389 files scanned): no corpus
SHA-256 collides with a generated result file, so no corpus entry is a product
of this tool.

| id | subject | SHA-256 | paras | top-level blocks | template cycles in source |
|---|---|---|---|---|---|
| S01 | X012 数学（P0 核心） | `79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779` | 952 | **4** | 1 |
| S02T | 数学 小升初 教师版 | `16b2c90c623952d5…` | 819 | **4** | 1 |
| S02S | 数学 小升初 学生版 | `2c48eef9c1030aaf…` | 313 | **4** | 1 |
| S03 | 数学 高中 计数原理 解析版 | `bfcec1ef64ec9d6d…` | 1038 | 952 | 0 |
| S04T | 物理 九年级 解析版 | `b5e217e9a2311d39…` | 399 | 350 | 0 |
| S04S | 物理 九年级 原卷版 | `755f20a000e5bfa9…` | 211 | 162 | 0 |
| S05S | 化学 高一 原卷版 | `e10818f40e99da42…` | 475 | 333 | 0 |
| S05T | 化学 高一 解析版 | `19fe81bd43f19e9a…` | 770 | 629 | 0 |
| S06 | 英语 四年级 | `6f034c306fd52eeb…` | 323 | **4** | 1 |

`top-level blocks == 4` means the document is a **single-table layout**: hundreds
of paragraphs inside one borderless layout table. This is a normal 学科网
format, not a corrupted file.

---

## 3. Real generation results (source build, no EXE)

Driven through the production Flask job API — the same code path the packaged
EXE uses.

| scenario | source | route | outcome for the user |
|---|---|---|---|
| U01 | X012, 1v1 smart | XML fails → V0.9 | **no file** — gate rejects |
| U01C | X012, class | XML fails → V0.9 | **no file** |
| U01F | X012, 1v1 full | XML fails → V0.9 | **no file** |
| U02 / U02F | 数学小升初 pair | XML fails → V0.9 | **no file** |
| U03 | 数学 计数原理, class | XML | file produced, but practice slots empty |
| U04 | 物理 pair | — | **no file** — pair identity rejected |
| U04S | 物理 解析版 single | XML fails → V0.9 | file produced, content OK |
| U05 | 化学 pair, class | XML | file produced, content OK |
| U06 | 英语 single | — | **no file** — role cannot be classified |

XML failure codes observed on clean inputs:

```
X012        smart : TABLE_SLOT_CONFLICT: generic heading and practice content share atomic table b2
X012        full  : TEMPLATE_SLOT_ANCHOR_UNRESOLVED: template 1v1 slot anchor counts are not unique:
                    {'knowledge': 2, 'immediate': 2, 'final': 2}
物理        smart : SLOT_ROUTING_AMBIGUOUS: unclassified section at b192: 【巩固训练】
数学小升初  smart : TABLE_SLOT_CONFLICT (same shape as X012)
```

---

## 4. X012 — first corruption point (§8)

Source `X012真实数学讲义.docx`
`79d925a724da75fbb7aee78b2add7fa390390f44eca46b346495e9437cd6e779`:

```
paragraphs=952  top_level_blocks=4  table_blocks=1  chars=14768
template_titles=1  template_cycles=1        <-- the source already carries one 讲义 template
```

Chain:

1. **XML route** — `build_slot_routing_plan` refuses the source:
   the single top-level table `b2` simultaneously holds a section heading start
   and practice-candidate content, and a top-level table is treated as one
   indivisible physical block → `TABLE_SLOT_CONFLICT`.
2. **V0.9 whole-job fallback** renders. Because the source itself already
   contains one complete `学科教师辅导讲义` cycle, the result contains the
   template twice:
   ```
   teacher output: paragraphs=1411  chars=22787
                   template_titles=2  template_cycles=2
                   one repeated sequence: 373 paragraphs / 6949 chars
                   (first at paragraph 22, repeats at paragraph 419)
   ```
   Template title paragraph indexes in the output: **0** and **34**.
3. **`PRODUCT_INTEGRITY_GATE`** rejects it → `status=error`, `output_paths=[]`.
   The user gets **no teacher edition and no student edition**.

So the answer to §8's question — *why does the fallback itself produce two
templates?* — is: the V0.9 whole-job path injects the source body wholesale into
the destination template without removing the source's own template header, and
X012 (like every single-table 讲义 in the corpus) already carries that header.
Blocking the output is correct; it is **not** a fix, because a legal clean input
still yields no product. Per §8 this is `PRODUCT_GATE = FAIL` and C4 must not be
restored.

---

## 5. Second defect (gate PASSES, user sees it immediately)

U03 — 数学高中班课, XML route, `product_integrity accepted = true`:

```
slot spans: knowledge=952  immediate=0  final=0
output    : 即时训练 (para 1067) -> heading + separator only
            五、归纳总结 (1069)   -> empty
            六、出门测试 (1094)   -> empty
```

All 952 source blocks were routed into 知识精讲; every practice/consolidation
section is an empty shell. A teacher sees this on the first page flip, while the
integrity gate reports success. (Chemistry U05 routed 249/354/26 and filled its
sections, so the router is inconsistent across sources of the same kind.)

---

## 6. What genuinely works (verified content, not just package-valid)

| output | sections in natural order | cover metadata | answers |
|---|---|---|---|
| 化学 教师版 (XML) | 课堂启动 → 知识回顾 → 知识精讲&例题 → 即时训练 → 归纳总结 → 出门测试 | 年级/科目/主题 filled, no residue | teacher 113 markers |
| 化学/数学 学生版 | same | same | **0** answer markers |
| 数学 教师版 (XML) | order fine, practice sections empty | fine | teacher 270 markers |
| 物理 教师版 (V0.9) | 课堂启动 → 知识回顾 → 知识精讲 → 即时训练 → 归纳总结 → 巩固练习 | fine | teacher 58 markers |

Studentization is real: every student edition carries **0** answer markers while
teacher editions keep 58–270. Expansion ratios 1.02–1.06 (no abnormal growth).
No 套娃, no residual template tail, no broken tables in any accepted output.

---

## 7. Minimal reproducer

```
python tools/c4_product_recovery/repro_table_layout_block.py \
    "C:/xml-uat/c4-product-recovery/corpus/X012真实数学讲义.docx"
```

prints

```
paragraphs=952 top_level_blocks=4 table_blocks=1 chars=14768 template_titles=1 template_cycles=1
1v1/smart   SLOT_ROUTING -> TABLE_SLOT_CONFLICT: generic heading and practice content share atomic table b2
1v1/full    SLOT_ROUTING -> ok, spans per slot: {'knowledge': 4, 'immediate': 0, 'final': 0}
class/smart SLOT_ROUTING -> TABLE_SLOT_CONFLICT: generic heading and practice content share atomic table b2
class/full  SLOT_ROUTING -> ok, spans per slot: {'knowledge': 4, 'immediate': 0, 'final': 0}
```

---

## 8. Fix status and next highest-value action

Not fixed in this round. Both defects sit inside frozen C1 (Slot Router) and
frozen V0.9, and the user's own rule allows touching them when real product
evidence proves the router is wrong — it now does — but the fix is a design
change, not a patch:

1. **Route cell-level content.** `struct_doc` already exposes recursive
   `Cell.blocks`; the router treats a top-level table as one atomic block. The
   minimal correct change is to route by cell-level block sequence instead of
   top-level block index, which unblocks X012 / 数学小升初 / 英语 in one move.
2. **Strip the source template header before V0.9 injection** so a source that
   already carries a 讲义 template cannot produce two cycles.
3. **Re-check practice slot distribution** for sources that produce
   `immediate=0, final=0` (U03) — decide whether empty practice sections are
   acceptable and, if not, why the router differs from chemistry.

Until (1) and (2) land, packaging / EXE / Restart / performance work stays
stopped per §7: there is no point certifying a build that cannot produce the
P0 sample.

---

## 9. Known limitations of this round

* Physics and English coverage is thin (one source each); chemistry is one real
  source reused as 原卷版/解析版.
* Pair rejection for 物理 (`教师版和学生版主题不一致`) is a filename-identity
  limitation of the classifier, not a content defect; the same file works as a
  single submission.
* 英语 S06 cannot be classified at all (filename has no 教师版/学生版 marker and
  no answer structure is detected). This is pre-existing C1 behaviour.
* No EXE, WPS, or Restart work was performed — correctly, because §10/§13 gate
  them behind a source-level Product PASS that does not exist yet.

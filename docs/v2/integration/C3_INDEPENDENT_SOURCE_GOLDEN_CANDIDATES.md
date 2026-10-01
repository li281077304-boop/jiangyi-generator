# C3 Round 5 — independent full-source Golden candidates

Base: `001b3f9856e21dbfff7edb0fd2c890b3fcbadc3b`.
Worker: actual GPT-6.1 (`gpt-6.1-sol`). Chief: **Codex GPT-6.1 Sol**.
Chief verdict: **PENDING**. This is a candidate-packet gate; **no approved
Golden, real Studentizer coverage PASS, production provider, zero COM or C3
completion is claimed**.

## New source-review evidence

Selected the smallest full teacher source in each subject from the prior
inventory: X008 physics, X014 mathematics and X018 chemistry. Three exact-byte
working snapshots were opened read-only through actual `KWps.Application` and
exported to PDF. Actual processes are WPS at
`D:\Program Files\WPS Office\12.1.0.28505\office6\wps.exe`; compatibility COM
reports `Name=Microsoft Word`, `Version=12.0`. This is **WPS evidence**, not
Microsoft Word UAT. Original and snapshot SHA checks pass for all three.

External evidence: `C:\xml-uat\c3-round5-source-review\`.
It contains the source DOCX snapshots, original PDFs, every page's PNG/text and
hashes, the read-only export record, source-body dump and independent manual
candidate assembly script. Neither production Studentizer nor a paired-file
diff produced the expected candidate.

| Source | Subject | WPS pages | Pages actually visually reviewed | Physical body records | Frozen units | Content status |
| --- | --- | --- | --- | --- | --- | --- |
| X008 | physics | 14 | **1–14, all** | 264 | 114 | Full Worker content review; Chief approval pending |
| X014 | mathematics | 26 | **1–2 only** | 656 | 268 | Incomplete; every block UNRESOLVED; fail closed |
| X018 | chemistry | 20 | **1–2 only** | 399 | 128 | Incomplete; every block UNRESOLVED; fail closed |

All **60** pages were rendered and are available. Only **18** pages were
actually inspected: 14 physics, 2 math, 2 chemistry. Rendering a page is not
content review. No math/chemistry deletion proposal or expected Golden is created.

Source SHA:

- X008: `56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`
- X014: `1c6aace1947016c0d03a531dac2811ca582be6286824d4eb76ced4b32eecaede`
- X018: `c2ca52c3967b650fd16aad965fa46687cce309a8b03905b57757da4fcb247e8c`

## Physics independent content decisions

The Worker read all original physics pages and the entire **264-child** source
body text/address listing. The source is a type-grouped practice document with
**34** physical questions, followed by their dedicated answer and explanatory
paragraphs. It has title/contents/type headings and no separate knowledge-fill
lesson area. Question wording, options, fill-in blanks, subquestions, captions
and diagrams stay intact. Standalone answer and complete explanation ranges are
proposed for removal because their **reviewed content answers the named physical
question**, not because of color, role or marker matching.

Every physical child receives a source-hash-bound full C14N fingerprint,
`RETAIN` or `PROPOSE_REMOVE`, owner/rationale and pending review state. The draft
has **146 retained blocks** and **118 proposed answer/analysis deletions**.
Every source nontext/boundary subtree has its exact XML path/fingerprint and
proposed decision. Source title, all headings, layouts, bookmark siblings,
section properties and question diagrams are retained.

### Page review ledger

| Original page | Reviewed content |
| --- | --- |
| 1 | Title/TOC and type sections retained; original WPS field display includes “错误！未定义书签。” |
| 2 | Q1–Q3; options, mixing-liquid diagram, molecular-scale blanks; full answer explanations |
| 3 | Q3 continuation, Q4–Q7; cold/hot diffusion and gas bottle diagrams |
| 4 | Q7 continuation, Q8–Q11; poetry options, liquid experiment, force question/subquestions |
| 5 | Q11 spring-scale diagram and explanation; Q12 space-water image, Q13 tape-removal image |
| 6 | Q14 four diagrams/options/explanation; Q15 molecular-state model and partial explanation |
| 7 | Q15 continuation, Q16/Q17 state models, Q18 smoking question |
| 8 | Q18 continuation, Q19/Q20 options/explanations, Q21 ammonia-bottle diagram |
| 9 | Q21 continuation; new section Q22/Q23 model/gas experiment and multi-part answers |
| 10 | Q23 continuation; Q24 two space images/subquestions; Q25 experiment images/prompts |
| 11 | Q25 model and explanations; exam section Q26/Q27/Q28 |
| 12 | Q28 continuation; Q29/Q30; new section Q31 and Q32 beginning |
| 13 | Q32 mixing-liquid diagram/explanation; Q33 phase-change models and answer |
| 14 | Q33 explanation continuation; Q34 cooling graph, subquestion options and full explanations |

The source's TOC/field issue is already visible in the **original** WPS export.
The candidate preserves those source field structures; it does not repair or
reinterpret them. This is a known source-display limitation, not a new Renderer
bug or permission to remove front matter.

### Frozen semantics remain diagnostic and unchanged

All **114** frozen semantic units, every original span and the exact top-level
`Block.body_idx` mapping are recorded. `bN` means dense StructDoc block sequence,
not direct physical body index: e.g. `b17` maps to `body[19]`. Nonparagraph
bookmark siblings are retained and explicitly accounted for.

There are **29** frozen QGs. Five independently reviewed physical questions
(3, 4, 10, 16, 24) have no frozen QG at their start. The packet records their
independent physical ownership and **does not invent frozen QG IDs**. The
remaining 29 QGs are linked to reviewed physical questions; answer/analysis-role
spans may contain retained question paragraphs, and their role does not decide
deletion. All spans and these discrepancies are visible to Chief.

This is unresolved **production compatibility**, not a reason to modify the
frozen A-Line. Current planner requires actual QG ownership and cannot consume
this packet unchanged. Boundary systems, multi-paragraph analysis and answer
OLE also exceed current approved Studentizer scope. Those restrictions remain.

## Independently authored expected candidate

An explicit manual list of the 34 reviewed prompt/answer ranges was applied to
the **original source XML** in the separate candidate-assembly script. It does
not call `prepare_student`, `_plan`, an evidence provider, COM Writer or a paired
oracle diff. Its draft DOCX is external:

`C:\xml-uat\c3-round5-source-review\X008-candidate-expected-student.docx`.

The packet binds its full expected document C14N hash and candidate package SHA;
all 146 retained source child fingerprints/order and every non-document package
part are exact. Package validation is valid. The source has four main-body OLE
objects: question-owned content is retained; explanation-owned content is
proposed for removal in the Q11 range with explicit nontext records. Resources
are retained byte-for-byte, including unused answer resources; none are silently
rewritten or garbage-collected.

This DOCX is an **unapproved expected Golden draft**, not a production Studentizer
output. No real derived-output WPS save/reopen/PDF gate was performed. It must
receive independent full-content/ownership approval before it can authorize
future production mutations. Package validity alone supplies no such authority.

## Mathematics and chemistry remain uncovered

X014 pages 1–2 show the overview, teaching-goal table and knowledge definitions.
Red words such as “结果／底数／指数／正号／负号” occur within teaching statements;
their desired student treatment is not inferred from color or role. Subsequent
24 pages have not been individually inspected. Full semantic/table/formula
inventory is supplied, but all 656 physical blocks remain **UNRESOLVED**.

X018 pages 1–2 show lesson aims, chemistry/physics-change overview, lab-safety
explanations, diagrams and tables containing red teaching terms. Whether each
term is a teaching statement or student fill-in is unresolved. The subsequent
18 pages, bound questions, 8 tables and 16 textboxes lack full business review.
All 399 physical records remain **UNRESOLVED**. No deletion ranges or fake Golden
are created for either subject; no partial manifest is approved.

## Verification and performance scope

Machine gate: **180 passed in 48.53s** (existing 177 plus 3 packet-shape
checks), including Stage2 **39/39**. Fresh Stage3: QG **408/408**, sections
**369/369**, subquestions **328/328**, original Recall **100%**,
E1–E4/MISS/FP/MERGE/SPLIT **0**, source hashes **8/8**; overall exact QG
boundaries **87.7%**. Fresh corpus hashes **27/27** and V0.9 assets **10/10**.
Compilation/diff checks pass. These are candidate integrity/protected gates,
not independent approval of the Worker content decisions.

`tools/studentizer_audit/verify_source_candidate.py` re-reads identical source
bytes, verifies every block/hash/body-index mapping, all frozen units and package
parts, then independently reconstructs the physics expected root from explicit
draft records and checks the candidate. Incomplete math/chemistry packets must
have only unresolved decisions and no expected-Golden artifact. It **never
approves a candidate or writes a production provider**.

WPS source-only open/export/close times, from the actual timestamp records:
X008 **2.542s**, X014 **2.848s**, X018 **3.770s**. These are source preparation
measurements, excluding WPS startup and review time. They do not measure a
Studentizer job, zero COM, classroom readiness or production speedup.

The normal app is unchanged; absence of approved complete evidence still causes
teacher-only per-item whole-job V0.9 fallback. No A-Line/C1/B-Line/V0.9 core or
production Studentizer/orchestration behavior changes in this round.

## Chief next action

Independently inspect X008's complete original pages, 34 ownership ranges,
retained nontext/boundaries, 5 missing-QG cases and the expected draft. A scoped
candidate-packet PASS must not be confused with production compatibility or
real Studentizer UAT. If full content authority is established, select the
next separately reviewed capability scope. Mathematics and chemistry need
complete independent source review or clearer real sources; remain fail closed.

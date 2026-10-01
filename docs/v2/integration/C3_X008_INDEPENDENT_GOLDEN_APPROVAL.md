# C3 X008 — independent full-content Golden approval

## Verdict and authority

**X008_GOLDEN_APPROVED** — exact source content and exact expected after-document only.

`chief_model = Codex GPT-6.1 Sol`

This Chief-only review is separate from the Round 5 packet-integrity PASS.
Review base: `12ebfac84d77ca0dffdd99b211fbdd8638751f47` (local and remote,
clean working tree before this report). No Worker implementation is included.
The verdict was stated before creating/pushing this report commit.

Approved source SHA256:
`56065cbf98af67818ae2c83e3169a3b932a6868be45b282dd51c71f0d5e16fe4`.

Source: `C:\xml-uat\stage3-expansion\sources\X008.docx`.
Exact-byte read-only snapshot and original WPS PDF/page evidence:
`C:\xml-uat\c3-round5-source-review\`.

Approved expected `word/document.xml` whole-root C14N SHA256:
`6b93cfc1594afc35bfa7801a4a73768185058fb2101e41e9f3d363173f31e0a2`.

Expected candidate DOCX SHA256:
`67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9`.

Artifact: `C:\xml-uat\c3-round5-source-review\X008-candidate-expected-student.docx`.
This is an independently reviewed expected Golden artifact, **not a production
Studentizer output**. The existing candidate packet remains `approved=false`
and `production_provider=false`; this report grants content approval only and
does not convert that draft into consumable production evidence.

## Independent method and actual review coverage

The Chief personally inspected **all 14 original WPS-export page PNGs**, not
only the earlier spot-check. Pages were viewed as 1/3/4, 6/7/8, 9/10/11,
12/13 and 2/5/14. Every page's question continuation, diagrams, captions,
options and answer/explanation content was read. The Chief also read the full
264-child physical body listing and checked the source XML and packet at exact
addresses. All 60 packet page hashes and exact source/unit/nontext mappings
were independently verified in the preceding packet review; X008's 14 pages
and the candidate artifact have not changed since then.

Ownership is determined from each problem's actual meaning and its subsequent
solution: the proposed region fills that problem's blanks, selects/explains its
options, or resolves its experimental subquestions. Color, A-Line answer role,
marker presence or paragraph adjacency alone did not authorize removal.
Scientific propositions inside correct/incorrect **options and prompts remain**.
The explanatory paragraphs contain teaching facts, but here they are specific
solutions to named questions, rather than a separate knowledge lesson.
There is no independently headed knowledge-fill section in this source.

The Chief separately authored the 34 exact prompt/answer coordinate tuples
below after the source review, then compared them with the draft. Using this
independent coordinate list, a read-only in-memory reconstruction from original
source bytes produced the approved whole-root hash above. It did not call
Studentizer, `_plan`, a provider, the Worker assembly script or V0.9.

All addresses below are **zero-based direct children of `w:body`, inclusive**.
They are not Word COM ordinals or dense StructDoc `bN` addresses.

## Full question-by-question ownership ledger

Each retained range includes its entire prompt, options, subquestions, blanks
and bound physical figures/layout. Each removal range includes the full answer
and all its explanation continuations, stopping before the next prompt or heading.

| Q | Original pages | Retain body range | Remove body range | Independent content finding |
| --- | --- | --- | --- | --- |
| 1 | 2 | 19–23 | 24–29 | Molecular-size choice D; four option-specific explanations and final choice belong to Q1. |
| 2 | 2 | 30–31 | 32–33 | Water/alcohol mixing blanks; keep apparatus image, remove volume/gap answers and explanation. |
| 3 | 2–3 | 34 | 35–37 | Molecular diameter and mixing-gap blanks; both explanatory paragraphs, including page-3 continuation, resolve Q3. |
| 4 | 3 | 38 | 39–40 | Sand/water analogy blanks; discontinuity/molecule solution is separate from the retained analogy prompt. |
| 5 | 3 | 42–43 | 44–45 | Cold/hot ink experiment; figure retained, speed/temperature solution removed. |
| 6 | 3 | 46–49 | 50–51 | Two gas bottles and four options retained; D and its diffusion explanation removed. |
| 7 | 3–4 | 52–54 | 55–56 | Poem question/options cross pages; B and the complete poem-specific explanation are separate solution content. |
| 8 | 4 | 58–59 | 60–62 | Diffusion examples/options retained; A plus explanations of A and B/C/D all belong to Q8. |
| 9 | 4 | 63–64 | 65–66 | Month-long ink/alcohol experiment and illustration retained; motion/gap answers removed. |
| 10 | 4 | 68 | 69–70 | Spring/dew force blanks retained; repulsion/attraction answers and both applications removed. |
| 11 | 4–5 | 71–74 | 75–77 | Both glass-plate subquestions and force-meter image retained; both answer/analysis subparts removed. |
| 12 | 5 | 78–81 | 82–83 | Space water-ball photo/options retained; C and attraction explanation removed. |
| 13 | 5 | 84–86 | 87–88 | Tape photo and options retained; B and tape adhesion explanation removed. |
| 14 | 6 | 89–95 | 96–101 | All four phenomenon figures, labels and options retained; A and all option analyses removed. |
| 15 | 6–7 | 103–108 | 109–115 | Three-state model and all options retained; A and full cross-page explanation through final choice removed. |
| 16 | 7 | 116–117 | 118–119 | Three models and state blank retained; solid-state answer and model interpretation removed. |
| 17 | 7 | 120–122 | 123–125 | Three models/labels and three blanks retained; both complete compression/gas explanations removed. |
| 18 | 7–8 | 127–129 | 130–131 | Smoking scenario and options retained; C and passive-smoking solution on page 8 removed. |
| 19 | 8 | 132–136 | 137–142 | Four natural-phenomenon options retained, including correct B; solution judgments for every option removed. |
| 20 | 8 | 143–145 | 146–151 | Negative-choice prompt/options retained; B plus all four option analyses/final choice removed. |
| 21 | 8–9 | 152–155 | 156–157 | Ammonia apparatus and all options retained across pages; A and test-paper explanation removed. |
| 22 | 9 | 159–160 | 161–163 | State-change model and blanks retained; all three answers and both explanation paragraphs removed. |
| 23 | 9–10 | 164–165 | 166–170 | Entire gas experiment, four temperature OLE objects, all blanks and bottle diagram retained; all experiment answers and four explanations removed. |
| 24 | 10 | 171–174 | 175–177 | Introductory space-class context, two photos and both prompts retained; both attraction/diffusion solutions removed. |
| 25 | 10–11 | 178–184 | 185–189 | All five apparatus illustrations, state model on page 11 and four prompts retained; all four answers/explanations removed. |
| 26 | 11 | 191–192 | 193–194 | Exam source label, zongzi scenario and four options retained; D and cooking-smell explanation removed. |
| 27 | 11 | 195–199 | 200–205 | Liangmian scenario/options retained; B and all option analyses/final choice removed. |
| 28 | 11–12 | 206–207 | 208–210 | Lead-block problem and options retained across pages; D and adhesion analysis/final choice removed. |
| 29 | 12 | 211–212 | 213–218 | Four motion examples retained; A and all option explanations/final choice removed. |
| 30 | 12 | 219 | 220–222 | Chengdu poems/context and both blanks retained; diffusion/temperature answers and both poem explanations removed. |
| 31 | 12 | 224–228 | 229–231 | Salted-egg comparison and options retained; A and full heating/diffusion explanation/final choice removed. |
| 32 | 12–13 | 232–237 | 238–243 | Complete copper-sulfate scenario, diagram and four options retained; B and all option explanations/final choice removed. |
| 33 | 13–14 | 244–246 | 247–248 | Three phase-change models and all blanks retained; model answers and full page-14 explanation continuation removed. |
| 34 | 14 | 249–257 | 258–261 | Cooling graph, numeric labels and both option sets retained; both answers and explanations/final choice removed. |

The independently enumerated removals total **118** physical paragraphs.
They are disjoint, each has exactly one physical owner, and no removal includes
the next question, option list, drawing, heading, material or structural boundary.
All 34 physical questions retain their original numbers and complete order.
No additional answer content was found in retained source-body regions on the
full page/text review; answer-like propositions inside options are intentional
problem content, not residual teacher solutions.

## All retained physical blocks and preservation

The **146** retained children are precisely the complement of the approved
removal ranges in original indices `0..263`. Every child retains its complete
C14N fingerprint and source order. This includes all prompt ranges above and
the following exhaustive remaining indices:

`0..18, 41, 57, 67, 102, 126, 158, 190, 223, 262, 263`.

These remaining blocks are title, contents, type/section headings, layout,
bookmarks and section properties. Direct bookmark siblings at `4`, `8` and
`57` and final section properties at `263` survive unchanged. All other
bookmark/field/hyperlink structures embedded in retained blocks survive with
their original subtree fingerprints. No physical table occurs in this source.

Every question diagram, caption and option remains attached to its original
question; no figure is moved, copied or duplicated. All four main-body OLE
objects are in retained Q23 prompt `body[164]` and preserve the temperature
choices visible on page 9. Q11 removed `body[75..77]` contains only text and
formatting. In fact **all 118 removed blocks lack nontext/boundary subtrees**.
This approval does not demonstrate formula/object-answer deletion.

The expected DOCX has exactly the same package member set as the source; all
members except `word/document.xml` are byte-identical. Retained root children
have exactly the independently approved fingerprints/order, and the complete
candidate root equals the independently reconstructed after-root C14N hash.
Header/footer, relationships, media, OLE payloads, styles and numbering parts
are preserved rather than regenerated or garbage-collected.

Original page 1 already displays two undefined-bookmark errors. Original
field/TOC structures and cached page numbers are preserved. They are not
repaired or promised to display newly correct page numbers after deletion.
This inherited source limitation remains relevant to future application UAT.

## Exact scope and remaining gates

This approves the **content ownership and exact expected source-to-student
transformation for this one source hash**. It is not a general rule that all
red text, answer roles, numbered paragraphs or similarly named files can be
removed. A different source/hash or transformation needs new evidence.

Five physical prompts (3, 4, 10, 16, 24) lack frozen QGs at their starts.
Their physical ownership is established here; no frozen IDs are invented.
There are still 29 frozen QGs and 114 frozen semantic units. The current
planner's ownership and boundary/multi-paragraph restrictions remain unchanged
and cannot consume this candidate directly. This report does **not** authorize
a provider, a production route, frozen A-Line changes or a sample-specific
production bypass. Any future capability requires its own implementation and
independent gates.

Mathematics X014 and chemistry X018 remain incomplete/unapproved. No real
Studentizer derivative was generated or opened by WPS in this review. No
derived-output open/save/reopen/PDF or visual UAT, zero-COM measurement,
performance PASS, classroom-readiness conclusion or C3 completion is claimed.

The preceding independent corrected-packet gate at the same source/code base
passed 181 focused tests (including Stage2 39/39), independently reproduced
eight protected Stage3 predictions (408 QGs/369 sections/328 subquestions,
zero MISS/FP/MERGE/SPLIT/error counts, exact QG boundaries 87.7%), and checked
27 corpus hashes plus 10/10 frozen V0.9 assets. This Chief-only report records
that already executed evidence; it does not pretend to rerun it as a new
production/UAT round. No executable or candidate/source bytes are modified.

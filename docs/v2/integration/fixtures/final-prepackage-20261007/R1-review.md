# R1 Coverage Recovery Review

## Decision

Both candidate iterations fail the value gate and were not retained. Production code and tests are restored to the tested code baseline. The evidence-only checkpoint does not include a candidate code patch.

## Frozen 33-topic results

| Evidence | XML PASS | New PASS | Lost baseline PASS |
|---|---:|---:|---:|
| Tested code `c4f2a8805137959725db0703569abd426d93016d`; evidence HEAD `cd75f34db45dd174c550d1f681a8ab2ea51c4d67` | 2/33 | — | — |
| R1-A candidate | 1/33 | 0 | topic 10 |
| R1-B candidate | 0/33 | 0 | topics 10 and 11 |

R1-B processed all 33 frozen entries and verified all 67 source hashes. Independent raw review classifies the final set as 30 UNRESOLVED, 2 AMBIGUOUS, and 1 SIZE rejection. The independent output is `C:\xml-uat\final-prepackage-20261007-r1b\evaluation.json`; its SHA-256 is `6edb657f0c1641d5a0e7d30fc76ff7d8722c0dfd50867ef22fe5614248470d1f`. No R1-B topic passed; the report's `XML_PASS` is not treated as sufficient proof of package acceptance.

Failure counts in R1-B: 15 occurrence-count mismatches, 5 numbered-source-candidate failures, 5 explicit-subquestion-set mismatches, 2 teacher-continuation ambiguities, and 1 each for missing question groups, ordered stem mismatch, unnumbered continuation/resource mismatch, size limit, label/order mismatch, and annotation ownership. Per-topic details are in `R1-B-outcome.json`.

## Audited evidence

- X019/X020, `1.1 物质的变化和性质 第2课时`: student `b183` and teacher `b380` Q21 stems and option blocks match exactly; teacher's `【答案】D` follows the options. The diagnostic helper output is in `R1-q21-physical-start-evidence.json`. This proves exact raw-start extraction only, not full pair alignment. R1-A's earlier Q2 resource diagnostic stopped because textbox identity was unprovable. Separately, R1-B's frozen evaluation reports 28 student vs 27 teacher occurrences for this pair (`R1-B-outcome.json`, topic index 2). The temporary textbox-equivalence experiment was removed; it is not evidence for the R1-B count and is not a PASS.
- Topic 17, `专题08 不等式与不等式组应用`: answer and analysis subpart labels repeat after canonical subquestions. Even after the local annotation-boundary candidate, the full pair continued to fail on later question/resource/subquestion boundaries. Topic 7's comparable case still failed explicit subquestion-set matching.
- X12.4 regression: R1-A promoted numbered knowledge blocks `b8`/`b9` into raw occurrences. R1-B reports student 21 vs teacher 20 occurrences (per-topic orders are stored in `R1-B-outcome.json`).
- Topic 11 regression: R1-B reports a question-20 subquestion-set mismatch: student `(1),(2)` versus teacher `(2)`. This is the observed mismatch; the evidence does not establish which individual candidate branch caused it.
- The textbox reader intentionally returns unprovable for textbox content. The temporary equivalence change was removed and is not part of the retained implementation.

## Validation and source record

The candidate family command returned `7 passed, 31 deselected`:

`python -m pytest v1.2-xml-experiment/res/app/test_canonical_pair_alignment.py -k 'answer_explanation_subparts or section_heading_closes or subquestion_identity_normalizes_only_inline_cjk_spacing or frozen_q21 or numbered_knowledge_items or explicit_subquestion_mismatch or teacher_filled_gap' -q`

Those tests validated local candidate rules only. They did not produce a full-pair PASS. The R1-B tested base was evidence HEAD `cd75f34db45dd174c550d1f681a8ab2ea51c4d67`, whose frozen evaluated code was `c4f2a8805137959725db0703569abd426d93016d`. R1-B candidate source SHA-256 and patch SHA-256 (`1b3ff7e4747d5a13fa73dc93fedc8519957a656360cfcee582dea5d64ce151d9`) are stored in `R1-B-outcome.json`; the patch is preserved outside the repository at `C:\xml-uat\final-prepackage-20261007-r1b\r1b-candidate.patch`.

## Abstraction review before more coding

This attempt confirms that physical numbered starts, A-Line question groups, and teacher annotation/section spans cannot be mixed as if they were one occurrence list: raw-start recovery was followed by 15 occurrence-count mismatches; the X12.4 knowledge-list false positives destabilized counts. The incident pair shows a subquestion-set mismatch (student `(1),(2)`, teacher `(2)`), but this evidence does not identify one unique branch as its cause. Chief independently confirmed the final 0/33 result and the exact topic 10 and 11 regressions.

A further design review should define the canonical student question skeleton first, with physical boundaries and resource/subquestion ownership. Teacher occurrences should map uniquely by exact core stem, ordered labels/options/subquestions, and resource evidence; answers and analysis attach within the bounded canonical occurrence. Duplicate labels alone cannot identify an occurrence, and unequal real counts remain fail-closed. Do not resume code changes until the model explains at least two frozen real pairs through the complete production XML path without changing the two baseline PASS results. The >=30/33 goal is not met.

# Teaching Module Synchronization: Architecture Review

**Status: architecture PASS; five-topic static prototype executed, product rendering blocked.** The isolated experiment is recorded under `fixtures/teaching-module-sync-20261008/`. It performs source inventory and candidate planning only; it produced no DOCX and claims no topic success. `canonical_pair_alignment.py` remains frozen for this work; no case rules were added there.

## Problem statement

The current alignment model treats different physical structures as if they were the same question-occurrence sequence. A worksheet has nested teaching structure: modules contain knowledge explanations, examples, practice groups, shared stimuli, questions, and teacher annotations. Student and teacher documents may distribute these pieces differently. Matching one flat list of question starts cannot represent that structure safely.

The control plane should be **module synchronization**. The student source defines the ordered module skeleton. The teacher source is segmented independently, then mapped to those modules using reliable headings and local structural context. Within a synchronized module, a separate **question consistency check** validates actual question groups. A matching module heading is never evidence that different questions are equivalent.

## Proposed model

1. **Extract an ordered physical inventory per role.** Each paragraph, table, drawing, textbox, and media resource receives a stable source identity and document order. Keep source text and relationships intact. Extraction is read-only; metadata handling, layout, OCR, and rendering behavior stay frozen.
2. **Build student modules first.** Reliable title/heading evidence and surrounding content form an ordered module tree. The student tree defines the student output boundaries and ownership of student-only instructional content. A repeated heading is not an anchor by itself; qualify it with parent heading path, neighboring unique content, numbering context, and associated resource identities. If two occurrences remain indistinguishable, synchronization is unresolved.
3. **Segment teacher content independently.** Use teacher heading evidence and local structure to form teacher packets. Map a packet to one student module only when the anchor is unique. A teacher-only knowledge/example packet may belong to a module without occupying the same physical block as in the student source. It remains teacher-only and must not be fabricated into the student output.
4. **Classify content within each module.** Preserve distinct roles for knowledge explanation, real practice/question groups, and teacher-only answer/analysis. Answers and analysis attach to a bounded teacher question occurrence, not to a nearby number alone. Unclassified physical content remains visible in the inventory and blocks a completeness claim.
5. **Keep semantic tables and shared material atomic.** A table, shared passage, diagram, or other resource used by several questions remains one indivisible source object with explicit links to its dependent groups. Do not split it across module or question boundaries. If ownership crosses a proposed boundary, resolve the owner from structure or fail closed.
6. **Validate question groups inside synchronized modules.** Aggregate a full question with its choices, subquestions, continuation paragraphs, and resources before comparing roles. Compare ordered group structure and reliable stem/resource evidence; do not compare entire module text. A heading match may route the comparison, but cannot make a question match pass. Genuine mismatches, missing groups, ambiguous counterpart mappings, and unexplained counts remain unresolved.
7. **Project outputs from role-safe ownership.** Each output is sourced only from its own input role. The student plan contains student-owned modules and practice; the teacher plan contains teacher-source knowledge/examples, questions, and answer/analysis. Synchronizing module destinations never copies student text over teacher text or teacher answers into the student output. Physical placement can differ between the two source documents when module attribution is proven.

## Required invariants

- **Physical coverage conservation:** within each input role, every source object is owned exactly once by one module/content packet or an explicit document-level region. No dropped, duplicated, or multiply owned paragraphs, tables, images, textboxes, or relationships. Report object counts and source identities before and after projection.
- **Unique anchors:** every cross-role module mapping resolves to one and only one module. Duplicate headings require enough parent/neighbor/resource context to establish uniqueness; otherwise stop.
- **Atomic shared material:** tables and shared stimulus/resource units remain whole and retain their dependency links.
- **Teacher-only packet ownership:** an additional teacher knowledge/example packet is retained in the teacher output only when it has one proven module owner. It need not mirror a student physical block.
- **Question aggregation:** validate complete question groups, including choices and subquestions, after module routing. Never promote a numbered knowledge-list item into a question solely because it resembles a question number.
- **Student-only protection:** student-only instructional or practice content remains in the student output and is not dropped because the teacher source lacks a counterpart.
- **Answer isolation:** answer/analysis objects are teacher-owned. No teacher-origin answer or analysis may enter the student projection, including through shared-resource closure or duplicate labels.
- **Fail closed:** ambiguous boundaries, uncertain module ownership, incomplete group aggregation, lost source objects, or unproven teacher/student counterparts cannot produce a verified pair.
- **Frozen peripheral behavior:** metadata, OCR, layout, and rendering are outside this redesign and remain unchanged.

## Why the earlier approach failed

The first real failures are structural, not a shortage of number-normalization exceptions:

- For topic 10 (X12.4), the frozen pair has repeated numbering across modules. R1-A promoted numbered knowledge blocks `b8`/`b9` and caused a canonical section conflict, losing a baseline PASS. R1-B added a knowledge filter but reported 21 student versus 20 teacher occurrences; it also lost the other baseline topic. Neither candidate established a safe reusable module boundary.
- Topic 11 is one of the original baseline successes. R1-B's attempted extraction reported question 20 as student `(1),(2)` versus teacher `(2)`, but this candidate-only span is not proof that the source pair has a real missing subquestion. The architecture check must preserve the baseline product result and inspect the original question envelopes before treating this as a content discrepancy.
- Topic 6 has a numbered knowledge section before practice. Its raw candidates include knowledge-list entries; number-only matching admits false question identities. This is precisely why question extraction must be scoped by structural content type and validated as a complete group.
- Topic 7 reports a different explicit subquestion set at question 9: the student occurrence has `(1),(2),(3)` while the teacher occurrence has none in the attempted extraction. The observed symptom is consistent with the parser splitting subquestions/choices across physical paragraphs; it is not evidence that the topic heading or number is sufficient to align them.
- Topic 26 has visibly different role distributions: the verified snapshot has 115 student and 179 teacher top-level physical blocks, and the teacher has 17 `【答案】` plus 17 `【详解】` markers while the student has none. The teacher contains knowledge sections and practice; those teacher-only packets need module ownership and answer isolation. Treating physical block parity as a requirement would reject valid material, while merging by broad heading alone could leak answers or hide missing practice.

R1-A and R1-B were rejected candidate iterations, not retained product evidence. Their 33-topic outcomes were respectively 1/33 and 0/33, with zero new PASS; R1-A lost topic 10 and R1-B lost topics 10 and 11. R1-B's audit found 15 occurrence-count mismatches and multiple distinct group mismatch classes. The family-specific check returned 7 passed/31 deselected, which only tested local rules and produced no full-pair PASS. The earlier external “4/33” attempts are not retained with verifiable source/evaluation lineage and may have counted knowledge-list entries as questions; they are excluded from the current baseline and all benefit claims.

## Five-topic experiment set

The experiment set is deliberately limited to the two accepted-baseline topics and the three requested failure shapes. Input identity is frozen in [`fixtures/v12-finalization-evaluation/teaching_module_sync_experiment_manifest.json`](fixtures/v12-finalization-evaluation/teaching_module_sync_experiment_manifest.json). The hashes are from the frozen R1-B evaluation record and the extracted DOCX files were read for static structure only.

| Case | Frozen topic | Structural question | Inputs | Current evidence boundary |
|---|---|---|---|---|
| Baseline 10 | Topic 10, X12.4 | Can repeated question numbering be scoped by student modules without promoting numbered knowledge blocks? | X015 student + X016 teacher | One of the original 2/33 baseline PASS; R1 candidates regressed it. |
| Baseline 11 | Topic 11, incident pair | Can the original question envelopes be inspected and the accepted baseline XML result preserved despite R1-B's candidate-only `(1),(2)` vs `(2)` report? | X005 student + X006 teacher | One of the original 2/33 baseline PASS; R1-B reports question 20 mismatch. |
| Failure 6 | Topic 6, voltage/resistance/Ohm law | Can knowledge-list numbered items remain knowledge while practice question groups are recovered? | X002 student + X001 teacher | R1-B unresolved; no accepted complete-pair success is claimed for this topic. |
| Failure 7 | Topic 7, electric power | Can question, choices, and subquestions be aggregated before comparing the roles? | X003 student + X004 teacher | R1-B unresolved; the reported q9 empty teacher subquestion set came from an attempted extraction and is not treated as source truth; compare full question/choice envelopes. |
| Failure 26 | Topic 26, current and circuits | Can teacher-only knowledge/example packets and practice be retained with one module owner while answers remain teacher-only? | Raw recovered student + teacher pair | Static structure confirms role asymmetry; no package or teaching-accuracy claim. |

The five cases are sufficient to challenge repeated headings/numbering, differing physical segmentation, multi-part questions, teacher-only packets, and answer isolation. Do not substitute a merely convenient topic without recording the change and its reason. Do not expand this sample set until the design is reviewed.

## Prototype acceptance gate (for a later, separately authorized step)

Build a new isolated module-sync experiment component, not a patch or growing overlay in `canonical_pair_alignment.py`. For these five topics only, it must emit inspectable source inventories, module maps, packet ownership, question-group maps, projection ownership, and an explicit fail-closed reason wherever proof is missing.

### Frozen production interface boundary

The current web job pair path in `webapp/app.py` runs `align_teacher_student` and then `project_pair_routes`. That projection deliberately requires every remaining physical block to have a strict one-to-one counterpart. It cannot represent teacher-only knowledge packets honestly, and the new planner must not fabricate old `alignment.occurrences` records to pass that gate.

An isolated harness can sit **before the existing per-role planning/render boundary**. It should make two complete, independent physical-block-to-slot maps from proven module/content ownership, then pass each map to `build_slot_routing_plan(..., canonical_projection_routes=...)` separately. The router already rejects incomplete maps and invalid destinations. For rendering, call the existing `template_slot_composer.render_slots` on each role plan; that path uses the frozen XML importer. The prototype must report and respect any inability of the existing display-renumbering path to represent a role-specific teacher-only packet safely. It must not silently omit renumbering checks or call the production paired-job route to bypass this interface limitation.

This experiment would reuse the checked-in router, composer/importer, package validator, and `ProductIntegrity` as unchanged downstream components. It would not alter `webapp/app.py`, `project_pair_routes`, `canonical_pair_alignment.py`, or production routing. That means the prototype evaluates whether complete role-owned plans can be rendered safely through the frozen downstream path; it does not claim the product's normal paired web workflow is integrated. Integrating module sync into that workflow would be a separate design and implementation decision after this experiment.

A later package check and `ProductIntegrity` check are necessary but insufficient. The harness must inspect complete teacher and student outputs to verify source-object conservation, real question grouping, table/resource ownership, module placement, student-only content, and absence of teacher answers from student output. These output inspections are live experiment gates; source inventory and module-map review are static input gates. Require at least two additional complete-topic successes and no baseline regression before anyone proposes a 33-topic run. No packaging or tagging is part of this step.

## Executed five-topic prototype (2026-10-08)

The approved small prototype ran once against the five frozen pairs. The harness used `semantic_facade.analyze_source` on each manifest path and verified each source hash before parsing. It recorded every top-level block with a stable `b{seq}` identity, text digest, kind, table atomicity, image/OLE references linked to their owning block, and a conservative content-role candidate. It formed ordered student-boundary and teacher-local heading candidates and emitted normalized heading matches with evidence and confidence. Every physical top-level block was assigned exactly once in each role for all ten inputs.

| Case | Input physical blocks (student / teacher) | Block ownership | Module mapping | Outcome |
|---|---:|---|---|---|
| Baseline 10 | 298 / 1113 | Exact once | Ambiguous heading candidate(s) | `PLAN_ONLY_FAIL_CLOSED` |
| Baseline 11 | 356 / 860 | Exact once | Ambiguous heading candidate(s) | `PLAN_ONLY_FAIL_CLOSED` |
| Failure 6 | 493 / 927 | Exact once | Ambiguous heading candidate(s) | `PLAN_ONLY_FAIL_CLOSED` |
| Failure 7 | 395 / 858 | Exact once | Candidate headings only | `PLAN_ONLY_FAIL_CLOSED` |
| Failure 26 | 115 / 179 | Exact once | Candidate headings only | `PLAN_ONLY_FAIL_CLOSED` |

Exact per-role block-kind counts, resource-owner references, module candidates, packet-candidate counts, source hashes, and fail-closed reasons are in `fixtures/teaching-module-sync-20261008/module_sync_experiment.json`. `fixtures/teaching-module-sync-20261008/EXPERIMENT_REPORT.md` records the evidence boundary and stop reason.

No existing product gate or renderer was called. This is deliberate: the current map contains candidate module ownership and does not prove complete question envelopes, cross-role question identity, unique teacher-only packet ownership, or answer boundaries. Sending it to `build_slot_routing_plan` would falsely treat unresolved candidate ownership as a complete canonical block-to-slot map; rendering now would turn unproven boundaries into DOCX output. The prototype therefore stops before routing/rendering and before package validation or `ProductIntegrity`. It does not demonstrate a product API defect; it identifies the evidence missing to call the existing router safely. No old aligner occurrences were fabricated.

Result: 0 generated outputs, 0 new complete-topic successes, baseline 10 and 11 preservation not evaluated, no full-33 run. The two-success/no-baseline-regression gate is unmet; stop at the five-topic experiment. The next independent step would need bounded question-envelope and answer-attachment proof plus an unambiguous role-owned route for every block before invoking the unchanged product gates.

## Independent review and current decision

Codex GPT-6.1 Sol returned **PASS** for the architecture and five-topic case selection, then separately returned **PASS scoped to static evidence** after reviewing the prototype artifacts and manifest provenance. This does not approve module synchronization as a complete product path.

The prototype failed closed on all five pairs before routing/rendering. It produced no DOCX and did not call package validation or `ProductIntegrity`; baseline preservation and complete question/answer/resource validation remain unverified. The requested threshold of two additional complete-topic passes with both baseline topics preserved is not met, so no 33-topic run is authorized. Use this report and the five-topic artifact as the architecture handoff; further work must prove question envelopes, answer ownership, complete route maps, and product-output gates on these five topics first.
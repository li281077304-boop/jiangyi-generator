# Teaching module sync prototype: five-topic run

**Run date:** 2026-10-08
**Scope:** Frozen manifest's five pairs only
**Status:** Static plan evidence produced; all five stopped before routing/rendering.

**Independent review:** Codex GPT-6.1 Sol, PASS scoped to static prototype evidence. This is not a product or coverage PASS.

## What ran

The standalone experiment verified the manifest SHA-256 for every DOCX, parsed each immutable byte snapshot with `semantic_facade.analyze_source`, and confirmed the parser snapshot hash matched those bytes. For every top-level source block it recorded `b{seq}`, body index, kind, text digest, table atomicity, role-candidate classification, and image/OLE references under their physical block owner. Candidate segment boundaries exclude ordinary Arabic-numbered question starts and use explicit heading text or outline level. Teacher/student heading matches use normalized anchor text and remain candidate-only; they are not treated as validated module boundaries.

All ten input inventories have dense source sequence, exactly-once candidate-segment ownership, and exactly-once candidate-packet ownership. Each image/OLE reference is retained under its owning physical block; reference counts by role are 35/37, 62/81, 186/429, 204/563, and 25/53 in manifest order. No nested image or table-cell content was re-counted as a separate top-level block. Atomic table counts appear in the JSON; this experiment does not claim semantic table dependency closure or shared-stimulus group validation.

## Exact outcomes

| Case | Student blocks | Teacher blocks | Student / teacher heading segments | Outcome |
|---|---:|---:|---:|---|
| baseline-10 | 298 (271 paragraphs, 27 tables) | 1113 (1085 paragraphs, 28 tables) | 9 / 8 | `PLAN_ONLY_FAIL_CLOSED` |
| baseline-11 | 356 (352 paragraphs, 4 tables) | 860 (856 paragraphs, 4 tables) | 55 / 55 | `PLAN_ONLY_FAIL_CLOSED` |
| failure-6 | 493 (476 paragraphs, 17 tables) | 927 (910 paragraphs, 17 tables) | 29 / 29 | `PLAN_ONLY_FAIL_CLOSED` |
| failure-7 | 395 (389 paragraphs, 6 tables) | 858 (852 paragraphs, 6 tables) | 17 / 17 | `PLAN_ONLY_FAIL_CLOSED` |
| failure-26 | 115 (114 paragraphs, 1 unknown) | 179 (178 paragraphs, 1 unknown) | 8 / 8 | `PLAN_ONLY_FAIL_CLOSED` |

All ten roles had exactly-once top-level and candidate-packet ownership and retained every listed resource reference with a source-block owner. The 5 cases now yield 9/8, 55/55, 29/29, 17/17, and 8/8 student/teacher heading segments. Several anchors are absent or nonunique; every one-to-one text match remains only a candidate because parent path, ordered neighborhood, and question-boundary ownership are not yet validated. Every case is blocked because complete question envelopes, question identity across roles, atomic table/shared-resource dependencies, and bounded teacher-answer attachments were not validated. Topic 26 contains one unknown physical block in each role, retained in inventory and treated as a blocker.

## Downstream stop point

The checked-in `build_slot_routing_plan` accepts a complete mapping from every physical sequence number to one of the fixed `knowledge`, `immediate`, or `final` destinations. It cannot consume unresolved candidate ownership or module IDs. `render_slots` renders that fixed three-slot plan and applies the existing display-renumbering path. This prototype has no proof-backed complete source-block-to-slot maps; generating them from heading and role-label candidates would fabricate authority the experiment has not established. Therefore it passed no candidate map to the router and generated no DOCX. The package validator and `ProductIntegrity` were consequently not called.

This is a fail-closed evidence boundary, not a claim that the router failed. It means this run cannot safely evaluate output placement or teacher-only knowledge retention through the downstream production gates. Adding a separate module destination to the production interfaces would exceed the authorized isolated prototype.

| Case | DOCX generated | Package validator | ProductIntegrity | New success |
|---|---|---|---|---|
| baseline-10 | No | Not run | Not run | No |
| baseline-11 | No | Not run | Not run | No |
| failure-6 | No | Not run | Not run | No |
| failure-7 | No | Not run | Not run | No |
| failure-26 | No | Not run | Not run | No |

No baseline preservation result was evaluated. There are zero new complete-topic successes, so the two-success/no-baseline-regression gate is unmet. Stop at five topics; do not run full33. The complete inventories, candidate module maps, resource-owner evidence, classification counts, source hashes, and per-case fail-closed reasons are in [`module_sync_experiment.json`](module_sync_experiment.json).

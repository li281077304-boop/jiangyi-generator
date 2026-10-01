# C3 R9 — production teacher-only reviewed-evidence route

Base: `fd5377bfb0d48125aba94f43fe11ed0a54a97936` (local and remote, clean tree).
Worker: DeepSeek V4.1 Flash. Chief review: **PENDING** (this round never claims a
Chief PASS). No C3 completion, tag or `C3_STUDENTIZER_PERFORMANCE_PASS` is issued.

Scope of this round is exactly the user-directed item 1: connect the already
verified Studentizer capability to the real production teacher-only route.

## What is now routed

```
input_version == TEACHER_ONLY
        |
        v
reviewed coverage gate  (studentizer_planner.prepare_complete_student)
        |
   reviewed evidence for the exact source SHA256 ?
        |                                   |
      yes                                  no
        |                                   |
        v                                   v
  XML Studentizer                   fail closed, per item
  -> derived student source         (STUDENTIZER_COVERAGE_UNPROVEN)
        |                                   |
        v                                   v
  A-Line -> Slot Router -> XML Renderer   V0.9 whole-job fallback
        |                                   (original teacher, fresh student)
        v
  teacher + student DOCX        (renderer refusal also falls back)
```

- Supported path: `prepare_student` produces the derived student source; A-Line,
  the C1 Slot Router and the B-Line XML renderer then run over the **original
  teacher** and the **derived student** independently. The frozen
  `make_student()` conversion is **not** called anywhere on this path.
- Unsupported path: preparation refuses with a precise `STUDENTIZER_*` reason and
  the item goes to the untouched V0.9 whole-job fallback, which always starts
  from the original teacher source. `student_source_doc` is reset to `None`, so a
  partially prepared derivative can never become a half-student document.
- Every refusal and every render refusal now persists a reason:
  `student_preparation.reason_code` / `reason_detail`, `fallback_detail` and
  `student_preparation.xml_failure`. The frozen renderer reason enum is
  unchanged.

## New production surfaces

`res/app/reviewed_studentizer.py` — trusted server-side reviewed evidence
registry, the production "reviewed coverage gate" data source.

- Indexed by **exact source SHA256**. No filename, role, colour, marker, upload
  or UI switch can enable the XML Studentizer.
- Each manifest carries an exhaustive per-`w:body` ledger, every reviewed
  prompt/answer range, the independently approved expected after-root digest and
  the acknowledged inherited missing bookmark targets. The Studentizer
  revalidates all of them against the real document before creating anything.
- Malformed, incomplete, duplicated or tampered evidence raises
  `ReviewedManifestError`; `app.py` then uses **no** provider, records
  `student_preparation.registry_error`, and every item fails closed.
- Evidence is a human-reviewed artifact. Correctness of the review remains a
  trusted operator boundary; the module proves only exact identity, exhaustive
  ledger coverage and an exact approved transformation.

`res/app/reviewed_studentizer/X008.json` — the reviewed manifest for the only
currently approved source (X008, physics). Generated deterministically by
`tools/studentizer_audit/build_reviewed_manifest.py` from the Chief approval
document and the reviewed candidate packet, and verified by running the public
`studentizer.prepare_student` contract against the exact source bytes and
requiring `XML_PREPARED` with the approved candidate DOCX digest
`67e0bc3617dfbf4e282cce4d0036fda61d42fd8192de96b533a60fbf4400ade9`.
1 `RETAIN`/118 `REMOVE` over 264 blocks, 34 reviewed ranges, 6 acknowledged
inherited missing bookmark targets.

`studentizer_planner.reviewed_range_plan` — accepts `PhysicalRangeSemantics`
(the capability verified in R7) as a second reviewed contract alongside the
existing frozen-QG `CompleteStudentEvidence`. Both fail closed; neither can
create removal authority.

Production activation is server configuration only:
`STUDENTIZER_REVIEWED_MANIFEST_DIR` (defaults to the packaged directory) or an
explicit `STUDENTIZER_EVIDENCE_PROVIDER` callable.

## Verified behaviour on the approved source

End-to-end through the real production HTTP path with the reviewed registry:

| Stage | Result |
|---|---|
| reviewed coverage gate | pass, exact source digest |
| XML Studentizer | `XML_PREPARED`, 118 reviewed removals, package valid, **no COM** |
| `make_student` on the supported path | **not called** |
| A-Line + C1 Slot Router | pass, 114 units |
| B-Line XML renderer | **refuses**: `selected hyperlink anchor is missing or ambiguous: _Toc9` |
| resulting route | V0.9 whole-job fallback, reason `UNSUPPORTED_BOOKMARK_SCOPE`, original teacher source |

**New, blocking finding.** X008's retained front matter (`w:body` 3–13) contains
8 hyperlinks to 5 bookmark names that do not exist in the document —
`_Toc9`, `_Toc67`, `_Toc3947`, `_Toc21406`, `_Toc22623`, `_Toc29290`. These are
the same inherited missing targets the Chief approval already recorded, and the
original file also displays two undefined-bookmark errors on page 1. The frozen
B-Line projection requires every **selected** hyperlink anchor to resolve, and
the C1 router routes that front matter into the `knowledge` slot, so the
renderer refuses this source and the item correctly falls back.

Consequences, stated plainly:

- The reviewed-supported branch is wired and exercised, but **no end-to-end
  COM-free teacher-only run is currently reachable on the only approved source**.
  The blocker is a frozen B-Line bookmark/anchor limitation triggered by an
  inherited source defect, not the Studentizer and not this wiring.
- Fixing it means new bookmark/anchor capability in the B-Line projection or a
  C1 routing change. Both are explicitly out of scope for this round
  ("不能安全证明：直接 fallback"), so this round only documents it and lets the
  item fail closed.
- Therefore this round makes **no** zero-COM, speed or completion claim.

## Machine gate

- Full `tests/` suite: **351 passed, 7 subtests passed** in 213.17s
  (327 before this round, +24 new in `tests/test_studentizer_production_registry.py`).
- New coverage: packaged manifest binds the approved Golden and reproduces the
  approved DOCX digest; provider answers only for the exact digest; 14 malformed
  evidence variants refused; duplicate evidence for one digest refused; missing
  directory refused; unloadable registry fails closed and reports the reason;
  supported path never calls `make_student`; unreviewed source falls back with no
  half-student; real renderer refusal persists the exact reason and hands the
  original teacher to the fallback.
- Fresh corpus hash check: **27/27** unchanged; no stray artifact was left in the
  corpus directory.
- `py_compile` on every changed file and `git diff --check` (working tree and
  staged) pass.

The real X008 source and its approved artifact live outside the repository; the
two cases that need them skip when they are not mounted. No COM was started by
this round: the V0.9 runtime is substituted in tests, never invoked.

## Frozen boundaries

Unchanged: frozen A-Line (`semantic_facade`, `tools/stage2_baseline`), the C1
Slot Router and business rules, the B-Line renderer and package validator, the
V0.9 `v09_fallback_runtime` assets, and the Studentizer's own reviewed-allowlist
semantics. No tag, no installer, no EXE, no release work.

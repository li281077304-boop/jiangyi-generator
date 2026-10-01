# C3 R11 — performance findings and the teacher-only regression

Base: `13f8e4b386b3900a56a513ab05e71af7a87685ef` (local and remote, clean tree).
Worker: DeepSeek V4.1 Flash. Chief review: **PENDING**; no C3 completion or
`C3_STUDENTIZER_PERFORMANCE_PASS` is issued by this round.

Machine evidence: `fixtures/c3-r11-performance.json`, tables in
`C3_R11_PERFORMANCE.md`. Every case below ran the production HTTP path with the
real A-Line, real C1 Slot Router, real B-Line renderer, the real validated
templates and the real frozen V0.9 runtime. Only observation wrappers were
installed; no production decision was replaced or stubbed.

## 1. The reviewed-supported teacher-only path starts no COM

`studentizer → A-Line → Slot Router → XML Renderer` on a reviewed source:

| Metric | Value |
|---|---:|
| total wall time | 0.749 s |
| Studentizer | 0.411 s |
| A-Line | 0.064 s |
| Slot Router | 0.011 s |
| XML Renderer | 0.155 s |
| package validation | 0.145 s |
| COM script invocations | **0** |
| `make_student` calls | **0** |
| newly started office processes | **0** |
| fallback items | **0** |
| route | XML, `XML_PREPARED`, 2/2 packages valid |

This case uses a **synthetic** reviewed source (identified as
`C3-R11-SYNTHETIC-WIRING-PROOF`). It is the only way to demonstrate a
*completing* COM-free teacher-only run this round, and it is a wiring proof, not
a real-corpus measurement. The synthetic source passes the real A-Line, the real
router and the real renderer; only the reviewed evidence is synthetic.

On the real approved source, the Studentizer stage is equally COM-free
(0.88 s for X008, `XML_PREPARED`, 118 reviewed removals, package valid). The
COM below belongs to the fallback, not to the reviewed path.

## 2. X008 teacher-only is blocked downstream and must fall back

Same-source workload: 1, 3 and 5 items built from the single approved X008
source under distinct names. **Same-source performance test; it does not
represent multi-sample coverage.**

| Items | Total | Per item | COM scripts | COM time | `make_student` time | new office processes | fallback |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 25.568 s | 25.568 s | 6 | 23.675 s | 7.666 s | 12 | 1/1 |
| 3 | 77.202 s | 25.734 s | 18 | 70.490 s | 22.667 s | 36 | 3/3 |
| 5 | 129.138 s | 25.828 s | 30 | 117.102 s | 37.988 s | 60 | 5/5 |

Per-item cost is flat (~25.6–25.8 s), so the workload scales linearly.

Every item reports `XML_PREPARED` from the reviewed gate and reviewed evidence
`X008`, then falls back with reason `UNSUPPORTED_BOOKMARK_SCOPE` and detail
`ProjectionError: selected hyperlink anchor is missing or ambiguous: _Toc9`.
**No item reaches the XML renderer**, so no end-to-end COM-free teacher-only run
exists on the only approved source. The cause is the inherited source defect
documented in R9, not this wiring and not the Studentizer. Per the user's
instruction ("不能安全证明：直接 fallback"), this round documents it and lets
the item fail closed instead of adding bookmark/anchor capability.

## 3. The honest comparison with C2

| Workload | C2 | C3 | change |
|---|---:|---:|---:|
| **5 teacher-only items**, identical sources (X001, X004, X006, X023, X025; 1v1) | 121.330 s | **274.791 s** | **+126%** |
| **3 teacher+student XML items**, identical sources (X001, X002, X020, X019, X023, X021; class) | 13.975 s | **11.768 s** | −16% |

- **Teacher+student XML batch: no regression.** 11.768 s versus 13.975 s, same
  6 real sources, XML route 3/3, COM 0, all 6 packages valid. The C3 planner and
  rendered-slot path add no measurable cost here.
- **Teacher-only: 2.27× slower.** Both runs have the same outcome shape (5
  items, 10 valid outputs, 5 `make_student` calls) so the difference is
  behaviour, not measurement noise.

Root cause, from the stage attribution:

| Stage | C2 case A | C3 case A |
|---|---:|---:|
| COM script invocations | 10 (2 per item) | **30 (6 per item)** |
| `make_student` time | ~87.2 s | 84.1 s |
| COM script wall time | — | 258.0 s of 274.8 s (94%) |
| newly started office processes | 20 | 60 |

`make_student` itself is unchanged (84.1 s versus ~87.2 s). C2's teacher-only
path prepared the student with one COM call per item and then rendered teacher
and student through XML. C3 R3 replaced that for **unreviewed** sources with the
per-item whole-job V0.9 fallback, which additionally performs two full V0.9
scan/split/Writer runs per item (teacher and student). That is the observed
+153 s.

This is exactly the consequence C3 R3 predicted in writing ("teacher-only
performance may regress") and the independent Chief PASSed. It is **not** a bug
introduced by R9/R10/R11, and no performance work was attempted, so nothing was
"optimised" at the expense of behaviour.

## 4. Decision requested (not taken unilaterally)

For an unreviewed teacher-only item there are two defensible routes:

1. Keep whole-job V0.9 fallback — maximum conservatism, ~2.3× slower than C2 on
   the identical workload.
2. Restore C2's eager `make_student` + XML render route as the fallback — roughly
   C2 speed, but it reintroduces the frozen `make_student` COM conversion that
   R3 deliberately removed from the default teacher-only path.

Both are product-route decisions that touch an already reviewed C3 decision, so
this round reports the measurement and does **not** change the route. The Chief
or the product owner should choose; `HUMAN_REQUIRED` is not raised because the
current behaviour is already the reviewed behaviour and nothing blocks the
handoff.

## 5. Method and caveats

- Timings come from one process; each case is a separate submission.
- A-Line time sums every `analyze_source` call, including the one inside the
  reviewed gate; the X008/Case A Studentizer figures also contain that A-Line
  time, so those two rows overlap.
- Slot Router time is plan total minus A-Line. Package validation time sums every
  `validate_package` entry point, including post-publication revalidation.
- COM script invocations count exact `powershell -File *.ps1` invocations through
  the frozen V0.9 runtime. Office process counts are distinct
  `(pid, creation-time)` instances sampled at 100 ms and exclude the 4 `wps.exe`
  instances already running before each measurement.
- Absolute numbers depend on this machine and on WPS already being resident; the
  ratio between C2 and C3 is the meaningful figure because both were measured
  here on identical source bytes.
- `C:\xml-uat\c3-r11-performance\` holds the fresh run directories (320 MB for
  one full sweep) and is not part of the repository.

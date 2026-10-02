# C3 R13 — layered fallback real performance

## Route separation and inherited 27-source evidence

Production now records the preparation method independently from renderer:

- `student_preparation=XML_STUDENTIZER` or `V09_MAKE_STUDENT` (plus reason,
  elapsed time, and `com_used` for this preparation step).
- `renderer=XML` or `V0.9` with its own fallback reason.

The already-reviewed, unchanged exact-digest capability scan remains **1/27
XML Studentizer supported and 26/27 unsupported**. The resulting policy
assignment is 1 source to `XML_STUDENTIZER` and 26 to `V09_MAKE_STUDENT`; those
26 make_student invocations were not repeated as a corpus sweep. The measured
R13 workloads confirm five actual V0.9 student preparations in C2 Case A and
five XML Studentizer preparations for the same approved X008 source used at
1/3/5 item sizes. X008 then reaches the separately measured whole-job renderer
fallback because of the known frozen bookmark-anchor refusal.

Renderer route totals for all 27 sources are **not fully established**: the
capability scan is not a full renderer preflight for each source. In these
actual R13 workloads, C2 Case A was XML 5/5, C2 Case B was XML 3/3, and X008
was whole-job V0.9 5/5. No renderer denominator is inferred for the remaining
corpus sources.

All cases run the production HTTP path with the real A-Line, C1 Slot Router, B-Line
renderer, templates and frozen V0.9 runtime. Only observation wrappers are installed.

## x008-teacher-only-1

SAME-SOURCE performance workload: 1 item(s) built from the single approved X008 source under distinct names. Same-source timing does not represent multi-sample coverage.

| Metric | Value |
|---|---:|
| items | 1 |
| total wall time | 27.96 s |
| per item | 27.96 s |
| XML items | 0 |
| fallback items | 1 |
| renderer routes | V0.9 |
| student preparation modes | XML_STUDENTIZER |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 0.749263 s |
| A-Line time | 0.169168 s |
| Slot Router time | 0.020006 s |
| XML Renderer time | 0.090426 s |
| package validation time | 0.237304 s |
| COM script invocations | 6 |
| make_student calls | 1 |
| make_student time | 8.398926 s |
| COM script time | 26.203108 s |
| newly started office processes | 12 |
| items reporting make_student | 1 |
| outputs | 2 (all valid: True) |
| studentizer status | XML_PREPARED |
| studentizer reason | - |
| reviewed evidence | X008 |

## x008-teacher-only-3

SAME-SOURCE performance workload: 3 item(s) built from the single approved X008 source under distinct names. Same-source timing does not represent multi-sample coverage.

| Metric | Value |
|---|---:|
| items | 3 |
| total wall time | 82.63 s |
| per item | 27.543 s |
| XML items | 0 |
| fallback items | 3 |
| renderer routes | V0.9 |
| student preparation modes | XML_STUDENTIZER |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 2.143369 s |
| A-Line time | 0.47132 s |
| Slot Router time | 0.058822 s |
| XML Renderer time | 0.22792 s |
| package validation time | 1.692089 s |
| COM script invocations | 18 |
| make_student calls | 3 |
| make_student time | 24.924233 s |
| COM script time | 76.686567 s |
| newly started office processes | 37 |
| items reporting make_student | 3 |
| outputs | 6 (all valid: True) |
| studentizer status | XML_PREPARED |
| studentizer reason | - |
| reviewed evidence | X008 |

## x008-teacher-only-5

SAME-SOURCE performance workload: 5 item(s) built from the single approved X008 source under distinct names. Same-source timing does not represent multi-sample coverage.

| Metric | Value |
|---|---:|
| items | 5 |
| total wall time | 137.585 s |
| per item | 27.517 s |
| XML items | 0 |
| fallback items | 5 |
| renderer routes | V0.9 |
| student preparation modes | XML_STUDENTIZER |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 3.482026 s |
| A-Line time | 0.78306 s |
| Slot Router time | 0.117447 s |
| XML Renderer time | 0.376423 s |
| package validation time | 3.702226 s |
| COM script invocations | 30 |
| make_student calls | 5 |
| make_student time | 40.913976 s |
| COM script time | 126.823372 s |
| newly started office processes | 60 |
| items reporting make_student | 5 |
| outputs | 10 (all valid: True) |
| studentizer status | XML_PREPARED |
| studentizer reason | - |
| reviewed evidence | X008 |

## c2-case-a-teacher-only

Identical workload to C2 Case A (X001, X004, X006, X023, X025; 1v1) for a direct comparison with the recorded 121.330 s.

| Metric | Value |
|---|---:|
| items | 5 |
| total wall time | 122.553 s |
| per item | 24.511 s |
| XML items | 5 |
| fallback items | 0 |
| renderer routes | XML |
| student preparation modes | V09_MAKE_STUDENT |
| fallback reasons | none |
| Studentizer time | 1.100704 s |
| A-Line time | 2.762541 s |
| Slot Router time | 0.182372 s |
| XML Renderer time | 17.511829 s |
| package validation time | 15.618274 s |
| COM script invocations | 10 |
| make_student calls | 5 |
| make_student time | 87.716468 s |
| COM script time | 85.764851 s |
| newly started office processes | 21 |
| items reporting make_student | 5 |
| outputs | 10 (all valid: True) |
| studentizer status | STUDENTIZER_FALLBACK_REQUIRED |
| studentizer reason | STUDENTIZER_COVERAGE_UNPROVEN |
| reviewed evidence | - |

## c2-case-b-teacher-student

Identical workload to C2 Case B (X001, X002, X020, X019, X023, X021; class) for a direct teacher+student XML batch regression check against the recorded 13.975 s.

| Metric | Value |
|---|---:|
| items | 3 |
| total wall time | 13.809 s |
| per item | 4.603 s |
| XML items | 3 |
| fallback items | 0 |
| renderer routes | XML |
| student preparation modes | STUDENT_SOURCE_BYPASS |
| fallback reasons | none |
| Studentizer time | 0 s |
| A-Line time | 0.753209 s |
| Slot Router time | 0.094282 s |
| XML Renderer time | 7.830558 s |
| package validation time | 5.530311 s |
| COM script invocations | 0 |
| make_student calls | 0 |
| make_student time | 0.0 s |
| COM script time | 0.0 s |
| newly started office processes | 0 |
| items reporting make_student | 0 |
| outputs | 6 (all valid: True) |
| studentizer status | STUDENT_SOURCE_BYPASS |
| studentizer reason | - |
| reviewed evidence | - |

## C2 comparison

| Workload | C2 | C3 |
|---|---:|---:|
| 5 teacher-only items (identical sources, 1v1) | 121.33 s | 122.553 s |
| 3 teacher+student XML items (identical sources, class) | 13.975 s | 13.809 s |

Same-source X008 timings are a workload measurement, not a coverage statement.
Machine-readable detail: `fixtures/c3-r13-layered-performance.json`.

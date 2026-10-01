# C3 R11 — real teacher-only and XML batch performance

All cases run the production HTTP path with the real A-Line, C1 Slot Router, B-Line
renderer, templates and frozen V0.9 runtime. Only observation wrappers are installed.

## synthetic-wiring-proof

SYNTHETIC reviewed source: proves the reviewed-supported teacher-only path reaches XML with zero COM and zero fallback. Not a real-corpus measurement.

| Metric | Value |
|---|---:|
| items | 1 |
| total wall time | 0.749 s |
| per item | 0.749 s |
| XML items | 1 |
| fallback items | 0 |
| fallback reasons | none |
| Studentizer time | 0.411047 s |
| A-Line time | 0.063804 s |
| Slot Router time | 0.011303 s |
| XML Renderer time | 0.15505 s |
| package validation time | 0.144577 s |
| COM script invocations | 0 |
| make_student calls | 0 |
| make_student time | 0.0 s |
| COM script time | 0.0 s |
| newly started office processes | 0 |
| items reporting make_student | 0 |
| outputs | 2 (all valid: True) |
| studentizer status | XML_PREPARED |
| studentizer reason | - |
| reviewed evidence | - |

## x008-teacher-only-1

SAME-SOURCE performance workload: 1 item(s) built from the single approved X008 source under distinct names. Same-source timing does not represent multi-sample coverage.

| Metric | Value |
|---|---:|
| items | 1 |
| total wall time | 25.568 s |
| per item | 25.568 s |
| XML items | 0 |
| fallback items | 1 |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 0.883855 s |
| A-Line time | 0.152716 s |
| Slot Router time | 0.017018 s |
| XML Renderer time | 0.076315 s |
| package validation time | 0.217832 s |
| COM script invocations | 6 |
| make_student calls | 1 |
| make_student time | 7.666381 s |
| COM script time | 23.675436 s |
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
| total wall time | 77.202 s |
| per item | 25.734 s |
| XML items | 0 |
| fallback items | 3 |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 2.67257 s |
| A-Line time | 0.492638 s |
| Slot Router time | 0.068092 s |
| XML Renderer time | 0.24152 s |
| package validation time | 1.504059 s |
| COM script invocations | 18 |
| make_student calls | 3 |
| make_student time | 22.66731 s |
| COM script time | 70.489938 s |
| newly started office processes | 36 |
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
| total wall time | 129.138 s |
| per item | 25.828 s |
| XML items | 0 |
| fallback items | 5 |
| fallback reasons | UNSUPPORTED_BOOKMARK_SCOPE |
| Studentizer time | 4.403428 s |
| A-Line time | 0.773077 s |
| Slot Router time | 0.087685 s |
| XML Renderer time | 0.394052 s |
| package validation time | 3.441891 s |
| COM script invocations | 30 |
| make_student calls | 5 |
| make_student time | 37.988011 s |
| COM script time | 117.102218 s |
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
| total wall time | 274.791 s |
| per item | 54.958 s |
| XML items | 0 |
| fallback items | 5 |
| fallback reasons | XML_RENDER_FAILED |
| Studentizer time | 1.074216 s |
| A-Line time | 0.988311 s |
| Slot Router time | 0.0 s |
| XML Renderer time | 0.0 s |
| package validation time | 12.417804 s |
| COM script invocations | 30 |
| make_student calls | 5 |
| make_student time | 84.114764 s |
| COM script time | 258.031246 s |
| newly started office processes | 60 |
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
| total wall time | 11.768 s |
| per item | 3.923 s |
| XML items | 3 |
| fallback items | 0 |
| fallback reasons | none |
| Studentizer time | 0 s |
| A-Line time | 0.732494 s |
| Slot Router time | 0.095041 s |
| XML Renderer time | 6.083927 s |
| package validation time | 5.281574 s |
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
| 5 teacher-only items (identical sources, 1v1) | 121.33 s | 274.791 s |
| 3 teacher+student XML items (identical sources, class) | 13.975 s | 11.768 s |

Same-source X008 timings are a workload measurement, not a coverage statement.
Machine-readable detail: `fixtures/c3-r11-performance.json`.

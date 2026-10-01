# C3 R10 — 27-source Studentizer capability scan

Read-only scan against the final Studentizer capability. Coverage is stated as
measured; nothing was expanded to raise it.

## Method and authority

Two layers are recorded and must not be conflated:

- **Production gate (authoritative).** Each source is passed through the real
  production entry point `studentizer_planner.prepare_complete_student` with the
  real reviewed-evidence registry. This is the exact decision the application
  makes for a teacher-only item.
- **Boundary verdict (diagnostic).** A read-only call into the Studentizer's own
  boundary validator with an empty removal set. It states whether the boundary
  systems of that document are inside the reviewed capability. It is **not**
  evidence that a complete reviewed answer ledger exists, and it authorizes
  nothing.

`Unresolved anchors` counts main-body hyperlinks whose bookmark anchor does not
resolve to exactly one bookmark start. The frozen B-Line projection refuses any
selected hyperlink with an unresolvable anchor, so a non-zero value means the
XML renderer will refuse that source even when preparation succeeds.

| Metric | Value |
|---|---:|
| total samples | 27 |
| XML Studentizer supported | 1 |
| fallback | 26 |
| other outcomes | 0 |
| reviewed manifests mounted | X008 |
| registry error | none |

## Production gate reason distribution

| Reason code | samples |
|---|---:|
| `STUDENTIZER_COVERAGE_UNPROVEN` | 26 |

## Boundary-system verdict distribution (diagnostic)

| Verdict | samples |
|---|---:|
| `NO_BOUNDARY_SYSTEM_BLOCKER` | 15 |
| `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 12 |

| First boundary refusal detail | samples |
|---|---:|
| `unsupported boundary system: txbxContent` | 8 |
| `unsupported boundary system: clrChange` | 2 |
| `unsupported field dependency: =` | 2 |

| Samples with an unresolvable hyperlink anchor | count |
|---|---:|
| X007, X008, X009, X010 | 4 |

## Per-source result

| Sample | Subject | Route | Production reason | Boundary verdict | Blocks | Tables | Textboxes | Fields | Bookmarks | Unresolved anchors | Plain removable |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| X001 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 928 | 17 | 0 | 6 | 1 | 0 | 1 |
| X002 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 494 | 17 | 0 | 6 | 1 | 0 | 2 |
| X003 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 396 | 6 | 0 | 0 | 1 | 0 | 26 |
| X004 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 859 | 6 | 0 | 0 | 1 | 0 | 3 |
| X005 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 357 | 4 | 0 | 3 | 1 | 0 | 251 |
| X006 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 862 | 4 | 0 | 3 | 1 | 0 | 630 |
| X007 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 145 | 0 | 0 | 15 | 4 | 8 | 87 |
| X008 | physics | XML | `-` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 264 | 0 | 0 | 15 | 4 | 8 | 206 |
| X009 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 168 | 1 | 0 | 15 | 8 | 10 | 81 |
| X010 | physics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 302 | 1 | 0 | 15 | 8 | 10 | 201 |
| X011 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 221 | 9 | 0 | 0 | 1 | 0 | 30 |
| X012 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 794 | 9 | 0 | 0 | 1 | 0 | 29 |
| X013 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 223 | 1 | 0 | 0 | 1 | 0 | 35 |
| X014 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 656 | 1 | 0 | 0 | 1 | 0 | 33 |
| X015 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 299 | 28 | 0 | 0 | 3 | 0 | 18 |
| X016 | mathematics | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 1114 | 29 | 0 | 0 | 3 | 0 | 19 |
| X017 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 207 | 8 | 16 | 0 | 1 | 0 | 0 |
| X018 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 399 | 8 | 16 | 0 | 1 | 0 | 0 |
| X019 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 192 | 5 | 16 | 0 | 1 | 0 | 83 |
| X020 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 399 | 5 | 16 | 0 | 1 | 0 | 278 |
| X021 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 334 | 12 | 0 | 3 | 1 | 0 | 5 |
| X022 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `NO_BOUNDARY_SYSTEM_BLOCKER` | 120 | 0 | 0 | 0 | 1 | 0 | 0 |
| X023 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 630 | 12 | 0 | 3 | 1 | 0 | 5 |
| X024 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 328 | 6 | 20 | 15 | 1 | 0 | 173 |
| X025 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 614 | 6 | 28 | 15 | 1 | 0 | 0 |
| X026 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 278 | 7 | 24 | 0 | 49 | 0 | 0 |
| X027 | chemistry | FALLBACK | `STUDENTIZER_COVERAGE_UNPROVEN` | `STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED` | 530 | 7 | 36 | 0 | 41 | 0 | 0 |

## Scope statement

The boundary verdict is a read-only capability statement about boundary systems only.
It does not prove that a complete reviewed answer ledger exists for that source, and it is
not a removal authorization. Low reviewed coverage is the expected outcome of this round;
no OOXML feature was added to improve the figure.
Machine-readable detail: `fixtures/c3-r10-capability-scan.json`.

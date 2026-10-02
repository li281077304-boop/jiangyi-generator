# C4 product recovery tools (2026-10-03)

These tools exist to answer one question with real files:

> is the DOCX the user finally receives actually correct?

They are deliberately separate from the unit tests. Nothing here changes
product behaviour.

| tool | what it does |
|---|---|
| `repro_table_layout_block.py` | Minimal reproducer for the blocker: reports A-Line metrics plus the slot-router outcome for every template/split-mode combination on a real source. |
| `build_corpus.py` | Rebuilds the immutable `PRODUCT_SOURCE_CORPUS` from declared original 学科网 downloads, preserving original Chinese filenames and verifying with `inspect_input_provenance` that no generated handout can enter. |
| `run_product_uat.py` | Drives the real production pipeline (Flask job API, same code path as the packaged EXE) over corpus samples and records route / fallback / integrity / published paths. |
| `inspect_content.py` | Prints a finished DOCX the way a user reads it: first paragraphs (cover), section headings in document order, last paragraphs. |
| `check_answers.py` | Counts answer markers per published teacher/student output to verify studentization. |

Paths inside the copied scripts point at the machine that produced the evidence
(`C:\xml-uat\c4-product-recovery`). Change the roots at the top of each script
before running elsewhere.

The corpus manifest is stored at `docs/v2/release/PRODUCT_SOURCE_CORPUS.json`;
the findings are in `docs/v2/release/C4_PRODUCT_RECOVERY_2026-10-03.md` and the
first golden entries in `docs/v2/release/C4_PRODUCT_GOLDEN.md`.

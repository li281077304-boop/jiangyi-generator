"""Minimal reproducer for the C4 product blocker found on 2026-10-03.

Symptom
-------
A real, clean 学科网 handout whose body lives inside one large layout table
(``top_level_blocks == 4`` while ``paragraphs`` is in the hundreds or more)
cannot be produced at all:

  1. the XML route raises ``SlotRoutingError`` before any rendering
     (``TABLE_SLOT_CONFLICT: generic heading and practice content share
     atomic table b2`` for X012);
  2. the V0.9 whole-job fallback then renders, but because the source itself
     already carries one complete 讲义 template cycle the result contains two
     template titles, two complete section cycles and one 373-paragraph
     repeated block;
  3. ``PRODUCT_INTEGRITY_GATE`` rejects it and the user receives no file.

Usage
-----
    python tools/c4_product_recovery/repro_table_layout_block.py <source.docx> [more.docx ...]

Exit code 0 means the source routed; 1 means the blocker reproduced.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from product_integrity import inspect_product_docx  # noqa: E402
from slot_router import SlotRoutingError, build_slot_routing_plan  # noqa: E402
from struct_doc import read_struct_doc  # noqa: E402


def probe(path: str) -> int:
    metrics = inspect_product_docx(path)
    struct = read_struct_doc(path)
    table_blocks = sum(1 for block in struct.blocks if block.kind == "table")
    print("%s" % Path(path).name)
    print("  paragraphs=%d top_level_blocks=%d table_blocks=%d chars=%d "
          "template_titles=%d template_cycles=%d" % (
              metrics.main_story_paragraphs, metrics.top_level_blocks, table_blocks,
              metrics.text_chars, metrics.template_title_count, metrics.template_cycles))
    failed = 0
    for template_type in ("1v1", "class"):
        for split_mode in ("smart", "full"):
            try:
                plan = build_slot_routing_plan(path, template_type, split_mode=split_mode,
                                               snapshot=None)
            except SlotRoutingError as exc:
                print("  %s/%s SLOT_ROUTING -> %s: %s" % (
                    template_type, split_mode, exc.reason_code, exc))
                failed = 1
                continue
            slots = {slot: len(spans) for slot, spans in (getattr(plan, "slots", {}) or {}).items()}
            print("  %s/%s SLOT_ROUTING -> ok, spans per slot: %s" % (
                template_type, split_mode, slots))
    return failed


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    failed = 0
    for argument in sys.argv[1:]:
        failed |= probe(argument)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

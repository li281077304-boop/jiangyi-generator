"""Check the physical inventory recorded by splitter_assessment_20261025."""
from collections import Counter, defaultdict
import re

SLOTS = ("knowledge", "immediate", "final")
COVER = "COVER_METADATA_PROJECTED_TO_TEMPLATE_COVER"
RESOURCES = {"math_count": "MATH", "oles_count": "OLE", "images_count": "IMAGE"}


def inventory(dump, declared_count, errors):
    raw = dump.get("blocks") if dump else None
    if not isinstance(raw, list):
        errors.append("DUMP_BLOCKS_UNAVAILABLE")
        return []
    if type(declared_count) is not int or len(raw) != declared_count:
        errors.append("DECLARED_BLOCK_COUNT_MISSING_OR_INCONSISTENT")
    blocks = []
    for pos, item in enumerate(raw):
        item = item if isinstance(item, dict) else {}
        block_id = item.get("id")
        flags = []
        if not isinstance(block_id, str) or not re.fullmatch(r"b(0|[1-9][0-9]*)", block_id):
            flags.append("MISSING_OR_INVALID_SOURCE_ID")
            block_id = f"dump.blocks[{pos}]"
        if block_id != f"b{pos}":
            errors.append(f"dump.blocks[{pos}]: expected b{pos}, found {block_id}")
        for key, label in RESOURCES.items():
            count = item.get(key)
            if type(count) is not int or count < 0:
                errors.append(f"{block_id}: invalid {key}")
                flags.append(f"{label}_COUNT_UNKNOWN")
            elif count:
                flags.append(f"REVIEW_{label}")
        text, boxes = item.get("text"), item.get("textbox_texts")
        if not isinstance(text, str):
            errors.append(f"{block_id}: missing or malformed text")
            text = ""
        if isinstance(boxes, list) and boxes:
            flags.append("REVIEW_TEXTBOX")
            text = " ".join([text] + [s for s in boxes if isinstance(s, str)])
        snippet = " ".join(text.split())
        blocks.append(dict(block_id=block_id, source_position=pos, kind=item.get("kind"),
                           summary=snippet[:120] + ("…" if len(snippet) > 120 else ""),
                           original_slots=[], review_flags=flags))
    return blocks


def slot_spans(plan, known, errors):
    """The fixed evaluator emits one singleton span per routed physical block."""
    slots = {slot: [] for slot in SLOTS}
    raw = plan.get("slots")
    if not isinstance(raw, dict):
        errors.append("PLAN_SLOTS_UNAVAILABLE")
        return slots
    if set(raw) != set(SLOTS):
        errors.append("PLAN_SLOT_KEYS_MISSING_OR_UNEXPECTED")
    for slot, ids in slots.items():
        detail = raw.get(slot)
        if not isinstance(detail, dict) or not isinstance(detail.get("spans"), list):
            errors.append(f"{slot}: missing spans")
            continue
        for i, span in enumerate(detail["spans"]):
            start = span.get("start") if isinstance(span, dict) else None
            if not isinstance(start, str) or span.get("end") != start or start not in known:
                errors.append(f"{slot}.spans[{i}]: invalid physical span {span!r}")
            else:
                ids.append(start)
        if type(detail.get("block_count")) is not int or detail["block_count"] != len(ids):
            errors.append(f"{slot}: block_count disagrees with physical spans")
        snippets = detail.get("text_summaries")
        if not isinstance(snippets, list) or [
                s.get("block_id") if isinstance(s, dict) else None for s in snippets] != ids:
            errors.append(f"{slot}: text_summaries IDs disagree with physical spans")
    return slots


def audit_blocks(dump, plan, declared_count):
    errors = []
    blocks = inventory(dump, declared_count, errors)
    known = {b["block_id"] for b in blocks}
    result = dict(physical_status="unknown", blocks=blocks, slots={s: [] for s in SLOTS},
                  missing=[], duplicate=[], unclassified=[], errors=errors)
    if plan is None or not dump or not isinstance(dump.get("blocks"), list):
        for b in blocks:
            b["review_flags"].append("PLAN_UNAVAILABLE")
        return result
    slots = result["slots"] = slot_spans(plan, known, errors)
    memberships = defaultdict(list)
    for slot, ids in slots.items():
        for block_id in ids:
            memberships[block_id].append(slot)
    records = defaultdict(list)
    raw = plan.get("block_records")
    if not isinstance(raw, list):
        errors.append("BLOCK_RECORDS_UNAVAILABLE")
        raw = []
    for i, record in enumerate(raw):
        if not isinstance(record, dict):
            errors.append(f"block_records[{i}]: expected object")
            continue
        idx, block_id = record.get("source_index"), record.get("block_id")
        if type(idx) is int and idx >= 0 and block_id == f"b{idx}" and block_id not in known:
            if type(declared_count) is int and idx < declared_count:
                result["missing"].append(block_id)
        if type(idx) is not int or idx < 0 or block_id != f"b{idx}" or block_id not in known:
            errors.append(f"block_records[{i}]: inconsistent index {idx!r} and ID {block_id!r}")
            continue
        records[block_id].append(record)
    counts = Counter(b["block_id"] for b in blocks)
    for b in blocks:
        block_id = b["block_id"]
        owners, spans = records[block_id], memberships[block_id]
        b["original_slots"] = spans
        # Keep contradictory records visible next to the actual span destinations.
        destinations = [r.get("destination_slot") for r in owners]
        b["record_destinations"] = destinations
        flags = b["review_flags"]
        cover = (len(owners) == 1 and "destination_slot" in owners[0]
                 and destinations == [None] and owners[0].get("exclusion_reason") == COVER)
        if cover:
            flags.append(COVER)
        if not owners or (not spans and not cover):
            result["missing"].append(block_id)
            flags.append("MISSING_RECORD_OR_SPAN")
        if max(len(owners), len(spans), counts[block_id]) > 1:
            result["duplicate"].append(block_id)
            flags.append("MULTIPLE_RECORDS_SPANS_OR_SOURCE_IDS")
        if owners and not cover and any(s not in SLOTS for s in destinations):
            result["unclassified"].append(block_id)
            flags.append("UNCLASSIFIED")
        if (cover and spans) or (not cover and destinations != spans):
            errors.append(f"{block_id}: destinations {destinations!r} disagree with spans {spans!r}")
            flags.append("RECORD_SPAN_CONFLICT")
    for key in ("missing", "duplicate", "unclassified"):
        result[key] = list(dict.fromkeys(result[key]))
    evidence = plan.get("evidence")
    if isinstance(evidence, dict) and evidence.get("selected_tier") == "PRESERVATION":
        for b in blocks:
            b["review_flags"].append("PRESERVED_REVIEW_TEACHING_SLOT")
    result["physical_status"] = "failed" if any(
        result[key] for key in ("missing", "duplicate", "unclassified", "errors")) else "verified"
    return result

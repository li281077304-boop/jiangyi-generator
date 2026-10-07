# -*- coding: utf-8 -*-
"""Strict, order-preserving alignment of paired teacher/student occurrences.

This module produces evidence only. A source-number match is never sufficient:
the normalized stem fingerprint and document order must also agree. A raw
numbered student paragraph may repair a missing A-Line question-group boundary
only when it uniquely matches one teacher occurrence; it does not modify A-Line
semantics or split the source paragraph.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import xml.etree.ElementTree as ET
import re
import unicodedata
import json
import posixpath
import zipfile
from typing import Any


_QUESTION = re.compile(r"^\s*(\d{1,3})\s*[.．、)）]\s*(.*)$", re.S)
_SPACE = re.compile(r"\s+")
_EMPTY_BLANK = re.compile(
    r"\u3000[^\u3000]{0,64}\u3000|\u3000[ \t]{1,64}(?=[A-Za-z0-9%°℃Ω\u4e00-\u9fff])")
_CHOICE_MARKER = re.compile(r"(?:^|\s)([A-D])[\.．、]\s*\S", re.I)
_CHOICE_STEM = re.compile(
    r"(?:下列|以下).{0,16}(?:正确|不正确|符合|不符合|错误).{0,10}(?:是|的是|的一项|选项)"
)


class PairAlignmentError(ValueError):
    def __init__(self, reason_code: str, detail: str, evidence: dict[str, Any] | None = None):
        self.reason_code = reason_code
        self.detail = detail
        self.evidence = evidence or {}
        super().__init__("%s: %s" % (reason_code, detail))


@dataclass(frozen=True)
class QuestionOccurrence:
    number: int
    start_seq: int
    node_id: str
    unit_id: str | None
    stem: str
    fingerprint: str
    origin: str
    source_nodes: tuple[str, ...]


def _top_seq(node_id: str) -> int | None:
    match = re.fullmatch(r"b(\d+)", str(node_id))
    return int(match.group(1)) if match else None


def _physical_seq(node_id: str) -> int | None:
    """Return the containing top-level block for a StructDoc subnode ref."""
    match = re.match(r"^b(\d+)(?:\.|$)", str(node_id))
    return int(match.group(1)) if match else None


def _fingerprint(text: str) -> tuple[int, str, str]:
    raw = str(text or "")
    # Preserve ideographic blank delimiters so pair matching can distinguish
    # an empty student blank from a teacher-inserted value. NFKC otherwise
    # turns U+3000 into an ordinary space and erases that evidence.
    sentinel = "\ue000"
    normalized = unicodedata.normalize("NFKC", raw.replace("\u3000", sentinel)).replace(sentinel, "\u3000")
    match = _QUESTION.match(normalized)
    if not match:
        return 0, "", ""
    number = int(match.group(1))
    # In teacher sources, answer values are commonly inserted between the
    # original ideographic-space blank delimiters. Canonicalize that bounded
    # answer span to the same marker as the student blank; never fuzzy-match
    # changed digits, symbols, formulae, or wording.
    stem = re.sub(r"[\t\r\n ]+", " ", match.group(2)).strip()
    digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()
    return number, stem, digest


def _match_answer_filled_blanks(student_stem: str, teacher_stem: str,
                                *, answer_structure_proven: bool) -> bool:
    """Match only explicit student blank spans filled in the teacher source.

    Text outside blank spans must remain byte-for-text identical after the
    already-applied NFKC normalization. Each insertion is bounded to 256
    characters and the complete teacher question must have independent
    answer/analysis structure evidence.
    """
    if not answer_structure_proven:
        return False
    spans = list(_EMPTY_BLANK.finditer(student_stem))
    if not spans or any(match.group(0).replace("\u3000", "").strip() for match in spans):
        return False
    literals = []
    cursor = 0
    for match in spans:
        literals.append(student_stem[cursor:match.start()].rstrip())
        cursor = match.end()
    literals.append(student_stem[cursor:].lstrip())
    if any(not piece for piece in literals[1:-1]):
        return False

    # Count bounded exact segmentations. Repeated context can make insertion
    # points ambiguous even when one regex backtracking result happens to fit.
    solutions: list[list[str]] = []

    def walk(index: int, position: int, values: list[str]) -> None:
        if len(solutions) > 1:
            return
        next_literal = literals[index + 1]
        # One explicit student blank can contain a full worked explanation in
        # the answer-rich copy. Keep the insertion bounded and require a
        # unique exact segmentation between unchanged literal anchors.
        limit = min(len(teacher_stem), position + 257)
        search = position + 1
        while search <= limit:
            found = teacher_stem.find(next_literal, search)
            if found < 0 or found > limit:
                break
            value = teacher_stem[position:found]
            answer_value = value.strip("\u3000 ")
            if answer_value and not any(marker in answer_value for marker in ("\u3000", "\n", "\r")):
                if teacher_stem.startswith(next_literal, found):
                    if index + 1 == len(spans):
                        if found + len(next_literal) == len(teacher_stem):
                            solutions.append(values + [value])
                    else:
                        walk(index + 1, found + len(next_literal), values + [value])
            search = found + 1

    if not teacher_stem.startswith(literals[0]):
        return False
    walk(0, len(literals[0]), [])
    return len(solutions) == 1


def _match_stems(left: str, right: str, *, answer_structure_proven: bool = False) -> str | None:
    """Return a deterministic relation, never a fuzzy similarity score."""
    if left == right:
        return "EXACT_NORMALIZED"
    if _match_answer_filled_blanks(left, right,
                                   answer_structure_proven=answer_structure_proven):
        return "ANSWER_FILLED_EXPLICIT_STUDENT_BLANKS"
    def blank_fields(stem):
        return list(re.finditer(r"\u3000(?P<value>[^\u3000]{0,64})\u3000", stem))

    left_fields, right_fields = blank_fields(left), blank_fields(right)
    if len(left_fields) and len(left_fields) == len(right_fields):
        def field_is_empty(value):
            return not value.strip()

        if all(field_is_empty(match.group("value")) for match in left_fields):
            values = [match.group("value").strip() for match in right_fields]
            # A-Line answer structure must independently prove that the
            # teacher-side values are answer fills. Without that proof, only
            # values explicitly present as choices in the student stem pass.
            right_without_fills = right
            for match in reversed(right_fields):
                right_without_fills = (right_without_fills[:match.start()]
                                       + "<BLANK>" + right_without_fills[match.end():])
            left_without_blanks = left
            for match in reversed(left_fields):
                left_without_blanks = (left_without_blanks[:match.start()]
                                       + "<BLANK>" + left_without_blanks[match.end():])
            normalized_context = unicodedata.normalize("NFKC", left_without_blanks)
            values_proven = answer_structure_proven or all(
                value and unicodedata.normalize("NFKC", value) in normalized_context
                for value in values)
            if values_proven and left_without_blanks == right_without_fills:
                return ("ANSWER_FILLED_BLANK_WITH_ANSWER_UNIT" if answer_structure_proven
                        else "ANSWER_FILLED_BLANK_MATCHED_TO_EXPLICIT_CHOICE")
    return None


def _trailing_bracketed_supplement(stem: str) -> str | None:
    """Return a bounded trailing note only when the whole note is explicit."""
    match = re.search(r"(\[[^\[\]]{1,160}\])\s*$", stem, re.S)
    return match.group(1) if match else None


def _normalized_block_text(text: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", text or "")).strip()


def _answer_filled_subquestion_match(student_block, teacher_block, *,
                                     answer_structure_proven: bool) -> bool:
    """Match an unchanged subquestion stem whose blank contains teacher OMML.

    Both sides must retain an explicitly empty ideographic blank, and all
    visible text outside it must be identical. The teacher paragraph must carry
    one OMML object and the containing canonical teacher question must have an
    independent answer/analysis unit.
    """
    if (not answer_structure_proven or student_block.math_count != 0
            or teacher_block.math_count not in (0, 1)):
        return False
    if any((student_block.images, student_block.oles, student_block.table,
            student_block.textbox_texts, teacher_block.images, teacher_block.oles,
            teacher_block.table, teacher_block.textbox_texts)):
        return False
    marker = re.compile(r"^\s*((?:[（(]\d+[）)]|[①-⑳]))(.*)$", re.S)
    student_match = marker.match(student_block.text or "")
    teacher_match = marker.match(teacher_block.text or "")
    if not student_match or not teacher_match or student_match.group(1) != teacher_match.group(1):
        return False
    if _match_stems(student_match.group(2), teacher_match.group(2),
                    answer_structure_proven=True) in (
                        "ANSWER_FILLED_EXPLICIT_STUDENT_BLANKS",
                        "ANSWER_FILLED_BLANK_WITH_ANSWER_UNIT",
                    ):
        return True

    def blank_skeleton(value: str) -> tuple[str, int]:
        value, count = re.subn(r"\u3000[ \t\u00a0\u3000]{0,64}\u3000", "<BLANK>", value)
        value = unicodedata.normalize("NFKC", value)
        return _SPACE.sub(" ", value).strip(), count

    student_skeleton, student_blanks = blank_skeleton(student_match.group(2))
    teacher_skeleton, teacher_blanks = blank_skeleton(teacher_match.group(2))
    return (student_blanks > 0 and student_blanks == teacher_blanks
            and student_skeleton == teacher_skeleton)


_SUBQUESTION_MARKER = re.compile(r"^\s*([（(]\d+[）)]|[①-⑳])")
_EXPLICIT_ANSWER_MARKER = re.compile(r"^\s*(?:【(?:答案|解答)】|答案与点拨|答案详解|试题解析)")


def _grouped_subquestion_spans(snapshot, node_seqs: set[int]) -> dict[str, dict[str, Any]]:
    """Collect each explicit subquestion with immediately following body blocks."""
    spans: list[dict[str, Any]] = []
    current = None
    for seq in sorted(node_seqs):
        block = snapshot.document.blocks[seq]
        text = block.text or ""
        if _EXPLICIT_ANSWER_MARKER.match(text):
            if current is not None:
                spans.append(current)
            current = None
            continue
        match = _SUBQUESTION_MARKER.match(text)
        if match:
            if current is not None:
                spans.append(current)
            current = {"label": _normalized_block_text(match.group(1)),
                       "nodes": [seq], "text": text[match.end():]}
        elif current is not None:
            current["nodes"].append(seq)
            current["text"] += text
    if current is not None:
        spans.append(current)
    labels = [span["label"] for span in spans]
    if len(labels) != len(set(labels)):
        return {}
    return {span["label"]: span for span in spans}


def _require_matching_subquestion_sets(student_subparts, teacher_subparts,
                                       occurrence_id: str, question_number: int) -> None:
    if set(student_subparts) != set(teacher_subparts):
        raise PairAlignmentError(
            "ALIGNMENT_UNRESOLVED",
            "paired question occurrences contain different explicit subquestion sets",
            {"canonical_occurrence_id": occurrence_id,
             "question_number": question_number,
             "student_subquestions": sorted(student_subparts),
             "teacher_subquestions": sorted(teacher_subparts)},
        )


def _subquestion_text_match(student_text: str, teacher_text: str, *,
                            answer_structure_proven: bool) -> str | None:
    sentinel = "\ue000"
    left = unicodedata.normalize("NFKC", (student_text or "").replace("\u3000", sentinel))
    right = unicodedata.normalize("NFKC", (teacher_text or "").replace("\u3000", sentinel))
    left = _SPACE.sub(" ", left).strip().replace(sentinel, "\u3000")
    right = _SPACE.sub(" ", right).strip().replace(sentinel, "\u3000")
    if left == right:
        return "EXACT_ORDERED_SUBQUESTION_TEXT"
    if _match_stems(left, right, answer_structure_proven=answer_structure_proven):
        return "ANSWER_FILLED_EXPLICIT_SUBQUESTION_BLANKS"
    # Do not infer an answer line from a teacher-only filled gap. The student
    # source must itself contain an explicit blank before a teacher value can
    # be accepted by _match_stems above.
    return None


def _raw_subquestion_text_with_underlined_blanks(snapshot, span, source_path):
    """Recover only explicit underlined whitespace blanks from main-story XML."""
    if source_path is None:
        return None
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(source_path, "r") as package:
            root = ET.fromstring(package.read("word/document.xml"))
        body = root.find(w + "body")
        if body is None:
            return None
        paragraphs = [child for child in body if child.tag == w + "p"]
        text_parts = []
        has_blank = False
        for seq in span["nodes"]:
            block = snapshot.document.blocks[seq]
            if block.kind != "paragraph" or not block.pno:
                return None
            if not 1 <= int(block.pno) <= len(paragraphs):
                return None
            paragraph = paragraphs[int(block.pno) - 1]
            for run in paragraph.iter(w + "r"):
                value = "".join(node.text or "" for node in run.iter(w + "t"))
                rpr = run.find(w + "rPr")
                underline = rpr.find(w + "u") if rpr is not None else None
                underline_value = (underline.get(w + "val") if underline is not None else None)
                is_underlined = underline is not None and underline_value != "none"
                if is_underlined and value and not value.strip():
                    text_parts.append("<EXPLICIT_BLANK>")
                    has_blank = True
                else:
                    text_parts.append(value)
        text = "".join(text_parts)
        text = re.sub(r"(?:<EXPLICIT_BLANK>)+", "\u3000\u3000", text)
        return text, has_blank
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
        return None


def _subquestion_resource_identity(snapshot, span: dict[str, Any], source_path) -> tuple | None:
    """Describe ordered resources attached to an already matched subquestion.

    Images are paired by their unique structural slot (relative block order and
    image order within that block), not by raster equality. Teacher and student
    copies commonly re-encode the same diagram at different resolutions. This
    function does not locate or match questions: it only validates the resource
    topology after the complete subquestion text and label have matched.
    """
    resource_rows = []
    for seq in span["nodes"]:
        block = snapshot.document.blocks[seq]
        if block.textbox_texts:
            return None
        if block.math_count:
            if block.kind != "paragraph" or not block.pno:
                return None
            resource_rows.append((seq, "omml", int(block.pno), int(block.math_count)))
        if block.table is not None:
            table_rows = []
            for row in block.table.rows:
                cell_rows = []
                for cell in row:
                    if cell.has_image or cell.has_nested_table or any(
                            nested.images or nested.oles or nested.math_count or
                            nested.table is not None or nested.textbox_texts
                            for nested in cell.blocks):
                        return None
                    cell_rows.append((_normalized_block_text(cell.text), cell.n_paras))
                table_rows.append(tuple(cell_rows))
            resource_rows.append((seq, "table", tuple(table_rows)))
        for image_index, _image in enumerate(block.images):
            resource_rows.append((seq, "image_slot", image_index))
        for ole in block.oles:
            resource_rows.append((seq, "ole", str(ole.target or "")))
    if not resource_rows:
        return ()
    if source_path is None:
        return None
    result = []
    try:
        with zipfile.ZipFile(source_path, "r") as package:
            members = set(package.namelist())
            main_body_paragraphs = None
            if any(row[1] == "omml" for row in resource_rows):
                root = ET.fromstring(package.read("word/document.xml"))
                body = root.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body")
                if body is None:
                    return None
                main_body_paragraphs = body.findall(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")

            def xml_shape(element):
                return (element.tag.split("}")[-1],
                        tuple(sorted((key.split("}")[-1], value)
                                     for key, value in element.attrib.items())),
                        (element.text or "").strip(),
                        tuple(xml_shape(child) for child in list(element)))

            for row in resource_rows:
                seq, kind, *details = row
                if kind == "table":
                    result.append((seq - span["nodes"][0], kind, details[0]))
                    continue
                if kind == "image_slot":
                    result.append((seq - span["nodes"][0], kind, *details))
                    continue
                if kind == "omml":
                    pno, expected_count = details
                    if (main_body_paragraphs is None or pno < 1
                            or pno > len(main_body_paragraphs)):
                        return None
                    paragraph = main_body_paragraphs[pno - 1]
                    math_nodes = [node for node in paragraph.iter()
                                  if node.tag in {
                                      "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath",
                                      "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara",
                                  }]
                    if len(math_nodes) != expected_count:
                        return None
                    result.append((seq - span["nodes"][0], kind,
                                   tuple(xml_shape(node) for node in math_nodes)))
                    continue
                target = details[0]
                normalized = posixpath.normpath(target.replace("\\", "/"))
                if (not target or normalized in (".", "..") or normalized.startswith("../")
                        or normalized.startswith("/") or ":" in normalized
                        or normalized not in members):
                    return None
                data = package.read(normalized)
                result.append((seq - span["nodes"][0], kind,
                               hashlib.sha256(data).hexdigest()))
    except (OSError, zipfile.BadZipFile):
        return None
    return tuple(result)


def _resource_identities_match(left: tuple, right: tuple) -> bool:
    # Images remain attached to their own explicit subquestion span. Teacher
    # editions may omit, redraw, or move an image into the answer/analysis
    # stream; side-local images are not used to locate the paired occurrence.
    # Every image node is still retained in projection evidence. Tables,
    # OMML, and OLE content must match exactly when both sides place them in
    # the question span because those resources can carry answer semantics.
    left = tuple(item for item in left if item[1] != "image_slot")
    right = tuple(item for item in right if item[1] != "image_slot")
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a[:2] != b[:2] or len(a) != len(b):
            return False
        if a[1] == "omml":
            if a[2:] != b[2:]:
                return False
        elif a[1] == "image":
            if a[2] != b[2] or len(a[3]) != len(b[3]):
                return False
            if any(abs(x - y) > 1 for x, y in zip(a[3], b[3])):
                return False
        elif a[2] != b[2]:
            return False
    return True


def _teacher_omml_is_explicit_blank_fill(left_resources: tuple,
                                         right_resources: tuple,
                                         teacher_block, teacher_source_path) -> bool:
    """Allow one teacher formula only when the paired student subquestion has a blank."""
    left_math = [item for item in left_resources if item[1] == "omml"]
    right_math = [item for item in right_resources if item[1] == "omml"]
    if left_math or len(right_math) != 1 or not _omml_is_between_ideographic_delimiters(
            teacher_block, teacher_source_path):
        return False
    left_other = tuple(item for item in left_resources if item[1] != "omml")
    right_other = tuple(item for item in right_resources if item[1] != "omml")
    return _resource_identities_match(left_other, right_other)


def _omml_is_between_ideographic_delimiters(block, source_path) -> bool:
    """Prove one teacher OMML node sits between explicit U+3000 text runs."""
    if source_path is None or not block.pno or block.math_count != 1:
        return False
    try:
        with zipfile.ZipFile(source_path, "r") as package:
            root = ET.fromstring(package.read("word/document.xml"))
        body = root.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body")
        if body is None:
            return False
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        math_tags = {
            "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath",
            "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara",
        }
        paragraphs = [child for child in body if child.tag == w + "p"]
        if not 1 <= int(block.pno) <= len(paragraphs):
            return False
        paragraph = paragraphs[int(block.pno) - 1]
        math_nodes = [node for node in paragraph.iter() if node.tag in math_tags]
        if len(math_nodes) != 1:
            return False
        math_node = math_nodes[0]
        top_child = next((child for child in list(paragraph)
                          if child is math_node or math_node in list(child.iter())), None)
        if top_child is None:
            return False
        children = list(paragraph)
        pivot = children.index(top_child)

        def wtext(elements):
            return "".join(node.text or "" for element in elements
                           for node in element.iter(w + "t"))

        before = wtext(children[:pivot]).rstrip(" \t")
        after = wtext(children[pivot + 1:]).lstrip(" \t")
        return before.endswith("\u3000") and after.startswith("\u3000")
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError, ValueError):
        return False


def _occurrence_tail_payload(snapshot, occurrence, source_path):
    """Return ordered tail text/resources, independent of paragraph wrapping."""
    text_parts = []
    resources_all = []
    answer_stream = False
    for node in occurrence.source_nodes:
        seq = _top_seq(node)
        if seq is None or seq == occurrence.start_seq:
            continue
        block = snapshot.document.blocks[seq]
        if _EXPLICIT_ANSWER_MARKER.match(block.text or ""):
            answer_stream = True
        if answer_stream:
            continue
        resources = _subquestion_resource_identity(
            snapshot, {"nodes": [seq]}, source_path)
        if resources is None:
            return None
        sentinel = "\ue000"
        text = unicodedata.normalize(
            "NFKC", (block.text or "").replace("\u3000", sentinel))
        if text:
            # Paragraph wrapping and ordinary layout spaces are not content
            # identity. Keep ideographic spaces because they can mark blanks.
            text_parts.append(_SPACE.sub("", text).replace(sentinel, "\u3000"))
        if _SUBQUESTION_MARKER.match(block.text or ""):
            resources_all.extend(item for item in resources if item[1] != "omml")
        else:
            resources_all.extend(resources)
    return "".join(text_parts), tuple(resources_all)


def _complete_occurrence_tail_match(student_snapshot, teacher_snapshot,
                                    student_occurrence, teacher_occurrence,
                                    student_source_path, teacher_source_path,
                                    *, answer_structure_proven: bool) -> bool:
    """Compare every unnumbered occurrence continuation in order."""
    student_rows = _occurrence_tail_payload(student_snapshot, student_occurrence,
                                            student_source_path)
    teacher_rows = _occurrence_tail_payload(teacher_snapshot, teacher_occurrence,
                                            teacher_source_path)
    if student_rows is None or teacher_rows is None:
        return False
    student_text, student_resources = student_rows
    teacher_text, teacher_resources = teacher_rows
    text_matches = student_text == teacher_text or bool(_match_stems(
        student_text, teacher_text,
        answer_structure_proven=answer_structure_proven))
    return text_matches and _resource_identities_match(student_resources,
                                                       teacher_resources)


def _has_explicit_choice_options(snapshot, occurrence: QuestionOccurrence) -> bool:
    labels = set()
    for node in occurrence.source_nodes:
        seq = _top_seq(node)
        if seq is None or seq == occurrence.start_seq:
            continue
        text = snapshot.document.blocks[seq].text or ""
        match = re.match(r"^\s*([A-D])[\.．、]\s*\S", text, re.I)
        if match:
            labels.add(match.group(1).upper())
    return len(labels) >= 2


def _normalize_proven_choice_blank(stem: str) -> str:
    return re.sub(r"[（(][ \u3000]{1,}[）)]", "(<CHOICE_BLANK>)", stem)


def _question_groups(snapshot) -> tuple[list[QuestionOccurrence], set[int]]:
    # A-Line sometimes wraps a complete numbered exercise set in one
    # question_group span (for example, two blocks numbered 1-10 and 1-8).
    # Treat each explicit top-level numbered paragraph inside that validated
    # span as an occurrence. The span establishes scope; question text,
    # resource topology, and order are still verified during pair alignment.
    occurrences_by_start: dict[int, QuestionOccurrence] = {}
    covered: set[int] = set()
    for unit in snapshot.units:
        if unit.get("role") != "question_group":
            continue
        spans = unit.get("spans") or []
        if not spans:
            continue
        unit_seqs: set[int] = set()
        resolved_spans = []
        for first, last in spans:
            start_ref = snapshot.node_index.resolve_ref(first) or ""
            end_ref = snapshot.node_index.resolve_ref(last) or ""
            start_seq, end_seq = _physical_seq(start_ref), _physical_seq(end_ref)
            physical_start, physical_end = start_seq, end_seq
            # A-Line may assign numbered objective/difficulty rows in the
            # validated cover table to question_group units. Skip only that
            # exact cover-table shape. Other table endpoints fail closed.
            table_seq = physical_start if physical_start is not None else physical_end
            if (start_seq is None or end_seq is None):
                if table_seq is not None and table_seq < len(snapshot.document.blocks):
                    block = snapshot.document.blocks[table_seq]
                    text = str(block.text or "")
                    if (block.kind == "table"
                            and re.search(r"(?:教学目标|学习目标)", text)
                            and re.search(r"(?:教学重难点|重点难点|重难点)", text)):
                        continue
                raise PairAlignmentError(
                    "ALIGNMENT_UNRESOLVED",
                    "question-group endpoint has no physical block envelope",
                    {"unit_id": unit.get("id"), "start": start_ref, "end": end_ref},
                )
            lo, hi = sorted((start_seq, end_seq))
            if hi >= len(snapshot.document.blocks):
                raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                         "question-group endpoint exceeds the document",
                                         {"unit_id": unit.get("id"), "end": end_ref})
            resolved_spans.append((lo, hi))
            unit_seqs.update(range(lo, hi + 1))
            covered.update(range(lo, hi + 1))
        ordered_seqs = sorted(unit_seqs)
        starts = []
        for seq in ordered_seqs:
            block = snapshot.document.blocks[seq]
            if block.kind != "paragraph":
                continue
            number, stem, digest = _fingerprint(block.text)
            if number and stem:
                starts.append((seq, number, stem, digest))
        if not starts:
            # Section/example groups without an explicit top-level question
            # remain residual content and are checked by projection later.
            continue
        unit_id = str(unit.get("id") or "")
        for index, (seq, number, stem, digest) in enumerate(starts):
            next_seq = starts[index + 1][0] if index + 1 < len(starts) else None
            # A non-numbered prefix before the first explicit question may be
            # a shared/project material component. Keep it outside the
            # numbered occurrence so it can be independently paired and
            # routed; do not silently absorb it into question 1.
            lower = seq
            upper = (next_seq - 1 if next_seq is not None else ordered_seqs[-1])
            # Include only physical nodes that the same A-Line unit actually
            # claims; this preserves gaps when a unit has disjoint spans.
            node_seqs = tuple(n for n in ordered_seqs if lower <= n <= upper)
            occurrence = QuestionOccurrence(
                number, seq, "b%d" % seq,
                "%s@b%d" % (unit_id, seq), stem, digest,
                "A_LINE_QUESTION_GROUP" if index == 0
                else "NUMBERED_PARAGRAPH_IN_A_LINE_GROUP",
                tuple("b%d" % n for n in node_seqs),
            )
            previous = occurrences_by_start.get(seq)
            if previous is not None and (previous.number, previous.fingerprint) != (
                    occurrence.number, occurrence.fingerprint):
                raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                         "overlapping A-Line groups disagree on a question start",
                                         {"node": "b%d" % seq,
                                          "first_unit": previous.unit_id,
                                          "second_unit": occurrence.unit_id})
            if previous is None or len(occurrence.source_nodes) > len(previous.source_nodes):
                occurrences_by_start[seq] = occurrence
    result = sorted(occurrences_by_start.values(),
                    key=lambda item: (item.start_seq, item.unit_id or ""))
    return result, covered


def _augment_with_unique_raw_matches(snapshot, reference, covered):
    """Recover uncategorized numbered starts with one exact pair counterpart.

    Labels may repeat across independent sections, so candidate identity is
    the exact normalized stem plus an unambiguous counterpart in the other
    source. The sequence/order checks run after recovery; number alone is never
    used as an identity.
    """
    candidates: list[QuestionOccurrence] = []
    for block in snapshot.document.blocks:
        if block.seq in covered or block.kind != "paragraph":
            continue
        number, stem, digest = _fingerprint(block.text)
        if not number or not stem:
            continue
        candidates.append(QuestionOccurrence(
            number, block.seq, "b%d" % block.seq, None, stem, digest,
            "RAW_NUMBERED_PARAGRAPH", ("b%d" % block.seq,)))
    by_fingerprint: dict[tuple[int, str], list[QuestionOccurrence]] = {}
    for item in candidates:
        by_fingerprint.setdefault((item.number, item.fingerprint), []).append(item)
    additions = []
    for candidate in candidates:
        identity = (candidate.number, candidate.fingerprint)
        targets = [item for item in reference
                   if (item.number, item.fingerprint) == identity]
        if len(by_fingerprint[identity]) != 1 or len(targets) != 1:
            continue
        additions.append(candidate)
    return additions


def align_teacher_student(student_snapshot, teacher_snapshot, *,
                          student_source_path=None, teacher_source_path=None) -> dict[str, Any]:
    """Build a strict canonical map; any real unmatched/ambiguous question fails."""
    student, student_covered = _question_groups(student_snapshot)
    teacher, teacher_covered = _question_groups(teacher_snapshot)
    if not student or not teacher:
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED", "paired input has no question-group sequence")

    student_numbers = [item.number for item in student]
    teacher_numbers = [item.number for item in teacher]
    student += _augment_with_unique_raw_matches(student_snapshot, teacher, student_covered)
    teacher += _augment_with_unique_raw_matches(teacher_snapshot, student, teacher_covered)
    student.sort(key=lambda item: (item.start_seq, item.unit_id or ""))
    teacher.sort(key=lambda item: (item.start_seq, item.unit_id or ""))

    if len(student) != len(teacher):
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "paired sources contain different real question occurrence counts",
                                 {"student_count": len(student), "teacher_count": len(teacher),
                                  "student_order": [item.number for item in student],
                                  "teacher_order": [item.number for item in teacher]})
    ordered_numbers = [item.number for item in student]
    teacher_order = [item.number for item in teacher]
    if ordered_numbers != teacher_order:
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "paired question occurrence labels/order differ",
                                 {"student_order": ordered_numbers, "teacher_order": teacher_order})

    def has_unique_teacher_answer_structure(occurrence, ordered_teacher):
        positions = ordered_teacher.index(occurrence)
        nodes = [_top_seq(node) for node in occurrence.source_nodes]
        if not nodes or any(node is None for node in nodes):
            return False
        q_end = max(nodes)
        next_nodes = ([_top_seq(node) for node in ordered_teacher[positions + 1].source_nodes]
                      if positions + 1 < len(ordered_teacher) else [])
        next_nodes = [node for node in next_nodes if node is not None]
        next_start = min(next_nodes) if next_nodes else len(teacher_snapshot.document.blocks)
        owners = 0
        for unit in teacher_snapshot.units:
            if unit.get("role") not in ("answer", "analysis"):
                continue
            for first, last in unit.get("spans") or []:
                a = _physical_seq(teacher_snapshot.node_index.resolve_ref(first) or "")
                b = _physical_seq(teacher_snapshot.node_index.resolve_ref(last) or "")
                if a is None or b is None:
                    continue
                lo, hi = sorted((a, b))
                if lo > q_end and hi < next_start:
                    owners += 1
        return owners > 0

    answer_evidence_by_start = {item.start_seq: has_unique_teacher_answer_structure(item, teacher)
                                for item in teacher}
    mapping = []
    for ordinal, (left, right) in enumerate(zip(student, teacher), 1):
        number = left.number
        # A short source note may be kept inline in the student edition but
        # moved to a standalone teacher paragraph. Accept that difference only
        # when the entire bracketed text is byte-for-text equal after NFKC and
        # whitespace normalization to the immediately adjacent teacher node.
        # The note remains in the canonical occurrence span; it is never
        # silently stripped from either output.
        moved_supplement = None
        student_suffix = _trailing_bracketed_supplement(left.stem)
        teacher_start = _top_seq(right.node_id)
        if student_suffix and teacher_start is not None:
            adjacent_seq = teacher_start + 1
            if adjacent_seq < len(teacher_snapshot.document.blocks):
                adjacent = teacher_snapshot.document.blocks[adjacent_seq]
                if (_normalized_block_text(adjacent.text) == _normalized_block_text(student_suffix)
                        and not adjacent.images and not adjacent.oles and not adjacent.math_count
                        and adjacent.table is None):
                    moved_supplement = {"text": student_suffix,
                                        "teacher_node": "b%d" % adjacent_seq,
                                        "relation": "EXACT_BRACKETED_TEXT_MOVED_TO_ADJACENT_PARAGRAPH"}
        match_left = left.stem
        match_right = right.stem
        choice_blank_proven = (_has_explicit_choice_options(student_snapshot, left)
                               and _has_explicit_choice_options(teacher_snapshot, right))
        if choice_blank_proven:
            match_left = _normalize_proven_choice_blank(match_left)
            match_right = _normalize_proven_choice_blank(match_right)
        if moved_supplement:
            # The choice-blank normalization can change code-point length; the
            # exact paired note must be removed before that presentation-only
            # normalization is applied.
            match_left = left.stem[:-len(student_suffix)]
            if choice_blank_proven:
                match_left = _normalize_proven_choice_blank(match_left)
        fingerprint_match = _match_stems(
            match_left, match_right,
            answer_structure_proven=answer_evidence_by_start.get(right.start_seq, False))
        if fingerprint_match == "EXACT_NORMALIZED" and choice_blank_proven:
            fingerprint_match = "EXACT_WITH_PROVEN_MULTIPLE_CHOICE_BLANK"
        if fingerprint_match is None:
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "ordered question occurrence stems do not match by an allowed exact relation",
                                     {"question_number": number,
                                      "occurrence_ordinal": ordinal,
                                      "student_node": left.node_id, "teacher_node": right.node_id,
                                      "student_fingerprint": left.fingerprint,
                                      "teacher_fingerprint": right.fingerprint})
        student_head_resources = _subquestion_resource_identity(
            student_snapshot, {"nodes": [left.start_seq]}, student_source_path)
        teacher_head_resources = _subquestion_resource_identity(
            teacher_snapshot, {"nodes": [right.start_seq]}, teacher_source_path)
        if (student_head_resources is None or teacher_head_resources is None
                or not _resource_identities_match(student_head_resources,
                                                  teacher_head_resources)):
            raise PairAlignmentError(
                "ALIGNMENT_UNRESOLVED",
                "question-start resources differ or cannot be proven equivalent",
                {"question_number": number, "student_node": left.node_id,
                 "teacher_node": right.node_id,
                 "student_resource_count": len(student_head_resources or ()),
                 "teacher_resource_count": len(teacher_head_resources or ())},
            )
        identity = hashlib.sha256(("%d\0%s" % (number, left.fingerprint)).encode("utf-8")).hexdigest()[:16]
        mapping.append({
            "canonical_occurrence_id": "q-%03d-%s" % (ordinal, identity),
            "ordinal": ordinal,
            "question_number": number,
            "student_node": left.node_id,
            "student_nodes": list(left.source_nodes),
            "student_unit_id": left.unit_id,
            "student_origin": left.origin,
            "teacher_node": right.node_id,
            "teacher_nodes": list(right.source_nodes) +
                             ([moved_supplement["teacher_node"]] if moved_supplement else []),
            "teacher_unit_id": right.unit_id,
            "teacher_origin": right.origin,
            "fingerprint_match": fingerprint_match,
            "student_fingerprint": left.fingerprint,
            "teacher_fingerprint": right.fingerprint,
            "teacher_moved_supplement": moved_supplement,
        })

    # Raw numbered occurrences on either side get a structural envelope.
    # Stop at the next canonical question, an explicit answer marker, or a
    # recognized section boundary. This lets a teacher raw occurrence retain
    # its complete subquestions without swallowing later annotations.
    for index, item in enumerate(mapping):
        for role, snapshot, origin_key, node_key in (
                ("student", student_snapshot, "student_origin", "student_nodes"),
                ("teacher", teacher_snapshot, "teacher_origin", "teacher_nodes")):
            if item.get(origin_key) != "RAW_NUMBERED_PARAGRAPH":
                continue
            start_seq = _top_seq(item.get(role + "_node") or "")
            if start_seq is None:
                raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                         "recovered raw question start is not a physical paragraph",
                                         {"canonical_occurrence_id": item.get("canonical_occurrence_id"),
                                          "role": role})
            next_starts = [_top_seq(candidate.get(role + "_node") or "")
                           for candidate in mapping[index + 1:]]
            next_starts = [seq for seq in next_starts if seq is not None and seq > start_seq]
            next_question_start = min(next_starts) if next_starts else len(snapshot.document.blocks)
            boundaries = [next_question_start]
            for unit in snapshot.units:
                if (unit.get("role") != "section" or
                        "中文序号栏目标题" not in str(unit.get("note") or "")):
                    continue
                for first, _last in unit.get("spans") or []:
                    section_seq = _physical_seq(snapshot.node_index.resolve_ref(first) or "")
                    if section_seq is not None and start_seq < section_seq < next_question_start:
                        boundaries.append(section_seq)
            for seq in range(start_seq + 1, next_question_start):
                if re.match(r"^\s*【(?:答案|解答)】|^\s*(?:答案与点拨|答案详解|试题解析)",
                            snapshot.document.blocks[seq].text or ""):
                    boundaries.append(seq)
                    break
            end_seq = min(boundaries) - 1
            if end_seq < start_seq:
                raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                         "recovered raw question has an empty physical range",
                                         {"canonical_occurrence_id": item.get("canonical_occurrence_id"),
                                          "role": role})
            claimed = set(range(start_seq, end_seq + 1))
            for other in mapping:
                if other is item:
                    continue
                other_nodes = {_top_seq(node) for node in other.get(node_key, [])}
                if claimed & {seq for seq in other_nodes if seq is not None}:
                    raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                             "recovered raw question range overlaps another occurrence",
                                             {"canonical_occurrence_id": item.get("canonical_occurrence_id"),
                                              "role": role, "start": start_seq, "end": end_seq,
                                              "other_occurrence_id": other.get("canonical_occurrence_id")})
            for seq in range(start_seq + 1, end_seq + 1):
                number, _stem, _digest = _fingerprint(snapshot.document.blocks[seq].text)
                if number:
                    raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                             "recovered question range contains another top-level question start",
                                             {"canonical_occurrence_id": item.get("canonical_occurrence_id"),
                                              "role": role, "nested_start": "b%d" % seq,
                                              "question_number": number})
            item[node_key] = ["b%d" % seq for seq in range(start_seq, end_seq + 1)]
            item[role + "_raw_range"] = {
                "start": "b%d" % start_seq,
                "end": "b%d" % end_seq,
                "boundary": "ANSWER_OR_SECTION_OR_NEXT_CANONICAL_QUESTION",
                "block_count": end_seq - start_seq + 1,
                "resource_blocks": ["b%d" % seq for seq in range(start_seq, end_seq + 1)
                                    if (snapshot.document.blocks[seq].images or
                                        snapshot.document.blocks[seq].oles or
                                        snapshot.document.blocks[seq].math_count or
                                        snapshot.document.blocks[seq].table is not None)],
            }

    # A-Line sometimes attaches an answer/analysis block to an intervening
    # section heading rather than to its question group. Treat it as an
    # annotation only when the semantic role is explicit and its complete
    # physical span lies strictly between exactly one question occurrence and
    # the next occurrence in document order. Parent-chain ownership remains
    # accepted when it resolves to one matched occurrence. Role by itself is
    # never enough, and an annotation that crosses a question boundary fails.
    teacher_unit_to_occurrence = {
        item["teacher_unit_id"]: item for item in mapping if item.get("teacher_unit_id")
    }
    qg_intervals: list[tuple[int, int, dict[str, Any]]] = []
    for item in mapping:
        seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        if not seqs or any(seq is None for seq in seqs):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "teacher occurrence has invalid physical source nodes",
                                     {"teacher_unit_id": item.get("teacher_unit_id")})
        qg_intervals.append((min(seqs), max(seqs), item))
    qg_intervals.sort(key=lambda entry: (entry[0], entry[1]))
    # A-Line can truncate either edition's question group before explicit
    # subquestion paragraphs that remain in the paired source. Recover only
    # exact, unique, order-preserving text/resource matches within that same
    # occurrence's bounded interval. Answer-filled OMML blanks need independent
    # answer/analysis evidence and exact visible text outside the blank.
    def bounded_subquestions(snapshot, end_seq, next_start, *, stop_at_answer):
        if stop_at_answer:
            return []
        found = []
        for seq in range(end_seq + 1, next_start):
            block = snapshot.document.blocks[seq]
            if re.match(r"^\s*【(?:答案|解答)】", block.text or ""):
                break
            if re.match(r"^\s*(?:[（(]\d+[）)]|[①-⑳])", block.text or ""):
                found.append(seq)
        return found

    teacher_subquestion_evidence = {}
    student_intervals = []
    for item in mapping:
        student_seqs = [_top_seq(node) for node in item.get("student_nodes", [])]
        teacher_seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        if not student_seqs or not teacher_seqs or any(
                seq is None for seq in (*student_seqs, *teacher_seqs)):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "paired occurrence has an invalid bounded interval",
                                     {"canonical_occurrence_id": item.get("canonical_occurrence_id")})
        student_intervals.append((min(student_seqs), max(student_seqs), item))
    student_intervals.sort(key=lambda entry: entry[0])

    for index, (_student_start, student_end, item) in enumerate(student_intervals):
        teacher_interval_index = next(
            i for i, entry in enumerate(qg_intervals)
            if entry[2]["canonical_occurrence_id"] == item["canonical_occurrence_id"])
        _teacher_start, teacher_end, _ = qg_intervals[teacher_interval_index]
        next_student_start = (student_intervals[index + 1][0]
                              if index + 1 < len(student_intervals)
                              else len(student_snapshot.document.blocks))
        next_teacher_start = (qg_intervals[teacher_interval_index + 1][0]
                              if teacher_interval_index + 1 < len(qg_intervals)
                              else len(teacher_snapshot.document.blocks))
        existing_student_nodes = {_top_seq(node) for node in item.get("student_nodes", [])}
        existing_teacher_nodes = {_top_seq(node) for node in item.get("teacher_nodes", [])}
        student_has_inline_answer = any(
            re.match(r"^\s*【(?:答案|解答)】", student_snapshot.document.blocks[seq].text or "")
            for seq in existing_student_nodes if seq is not None)
        teacher_has_inline_answer = any(
            re.match(r"^\s*【(?:答案|解答)】", teacher_snapshot.document.blocks[seq].text or "")
            for seq in existing_teacher_nodes if seq is not None)
        # Internal numbered occurrences extracted from a broad A-Line span
        # already have exact physical ranges. Do not let the residual gap
        # between A-Line units leak subquestions into those occurrences.
        if item.get("student_origin") == "A_LINE_QUESTION_GROUP":
            student_candidates = bounded_subquestions(
                student_snapshot, student_end, next_student_start,
                stop_at_answer=student_has_inline_answer)
        else:
            student_candidates = []
        if item.get("teacher_origin") == "A_LINE_QUESTION_GROUP":
            teacher_candidates = bounded_subquestions(
                teacher_snapshot, teacher_end, next_teacher_start,
                stop_at_answer=teacher_has_inline_answer)
        else:
            teacher_candidates = []
        # Include explicit subquestions that A-Line left just outside a broad
        # question_group span. These are recovered only within the bounded
        # interval above, before comparing the complete occurrence bodies.
        student_q_subparts = _grouped_subquestion_spans(
            student_snapshot, existing_student_nodes | set(student_candidates))
        teacher_q_subparts = _grouped_subquestion_spans(
            teacher_snapshot, existing_teacher_nodes | set(teacher_candidates))
        verified_student_subparts: set[int] = set()
        verified_teacher_subparts: set[int] = set()
        paired_subparts = []
        _require_matching_subquestion_sets(
            student_q_subparts, teacher_q_subparts,
            item["canonical_occurrence_id"], item["question_number"])
        if student_q_subparts and teacher_q_subparts:
            for label in student_q_subparts:
                left_span = student_q_subparts[label]
                right_span = teacher_q_subparts[label]
                left_blocks = [student_snapshot.document.blocks[seq]
                               for seq in left_span["nodes"]]
                right_blocks = [teacher_snapshot.document.blocks[seq]
                                for seq in right_span["nodes"]]
                left_resources = _subquestion_resource_identity(
                    student_snapshot, left_span, student_source_path)
                right_resources = _subquestion_resource_identity(
                    teacher_snapshot, right_span, teacher_source_path)
                answer_structure_for_item = answer_evidence_by_start.get(
                    _top_seq(item.get("teacher_node") or ""), False)
                resources_match = (left_resources is not None and right_resources is not None
                                   and (_resource_identities_match(left_resources, right_resources)
                                        or (len(left_blocks) == len(right_blocks) == 1
                                            and answer_structure_for_item
                                            and left_blocks[0].math_count == 0
                                            and right_blocks[0].math_count == 1
                                            and _answer_filled_subquestion_match(
                                                left_blocks[0], right_blocks[0],
                                                answer_structure_proven=True)
                                            and _teacher_omml_is_explicit_blank_fill(
                                                left_resources, right_resources,
                                                right_blocks[0], teacher_source_path))))
                if not resources_match:
                    raise PairAlignmentError(
                        "ALIGNMENT_UNRESOLVED",
                        "subquestion resources are missing, unsupported, or do not match by exact content identity",
                        {"canonical_occurrence_id": item["canonical_occurrence_id"],
                         "question_number": item["question_number"],
                         "subquestion_label": label,
                         "student_nodes": ["b%d" % seq for seq in left_span["nodes"]],
                         "teacher_nodes": ["b%d" % seq for seq in right_span["nodes"]],
                         "student_resource_count": len(left_resources or ()),
                         "teacher_resource_count": len(right_resources or ())},
                    )
                relation = _subquestion_text_match(
                    left_span["text"], right_span["text"],
                    answer_structure_proven=answer_evidence_by_start.get(
                        _top_seq(item.get("teacher_node") or ""), False))
                if relation is None:
                    raw_student = _raw_subquestion_text_with_underlined_blanks(
                        student_snapshot, left_span, student_source_path)
                    raw_teacher = _raw_subquestion_text_with_underlined_blanks(
                        teacher_snapshot, right_span, teacher_source_path)
                    if raw_student and raw_teacher and raw_student[1]:
                        student_marker = _SUBQUESTION_MARKER.match(raw_student[0])
                        teacher_marker = _SUBQUESTION_MARKER.match(raw_teacher[0])
                        if (student_marker and teacher_marker
                                and _normalized_block_text(student_marker.group(1))
                                == _normalized_block_text(teacher_marker.group(1))
                                and _subquestion_text_match(
                                    raw_student[0][student_marker.end():],
                                    raw_teacher[0][teacher_marker.end():],
                                    answer_structure_proven=answer_evidence_by_start.get(
                                        _top_seq(item.get("teacher_node") or ""), False))):
                            relation = "ANSWER_FILLED_STUDENT_XML_UNDERLINE_BLANK"
                if (relation == "EXACT_ORDERED_SUBQUESTION_TEXT"
                        and len(left_blocks) == len(right_blocks) == 1
                        and left_blocks[0].math_count == 0
                        and right_blocks[0].math_count == 1
                        and resources_match):
                    relation = "ANSWER_FILLED_SUBQUESTION_WITH_BOUND_ANSWER_STRUCTURE"
                if relation is None:
                    raise PairAlignmentError(
                        "ALIGNMENT_UNRESOLVED",
                        "complete explicit subquestion text differs between paired sources",
                        {"canonical_occurrence_id": item["canonical_occurrence_id"],
                         "question_number": item["question_number"],
                         "subquestion_label": label,
                         "student_nodes": ["b%d" % seq for seq in left_span["nodes"]],
                         "teacher_nodes": ["b%d" % seq for seq in right_span["nodes"]]},
                    )
                verified_student_subparts.update(left_span["nodes"])
                verified_teacher_subparts.update(right_span["nodes"])
                paired_subparts.append({
                    "label": label,
                    "student_nodes": ["b%d" % seq for seq in left_span["nodes"]],
                    "teacher_nodes": ["b%d" % seq for seq in right_span["nodes"]],
                    "relation": relation,
                    "resource_relation": "SIDE_LOCAL_IMAGE_SLOTS_EXACT_TABLE_OMML_OLE_WHEN_PRESENT",
                    "student_resources": [list(row) for row in left_resources],
                    "teacher_resources": [list(row) for row in right_resources],
                })
        if paired_subparts:
            teacher_subquestion_evidence.setdefault(item["canonical_occurrence_id"], []).extend(
                paired_subparts)
        teacher_question_subparts = [
            seq for seq in sorted(existing_teacher_nodes)
            if seq is not None and re.match(
                r"^\s*(?:[（(]\d+[）)]|[①-⑳])",
                teacher_snapshot.document.blocks[seq].text or "")
        ]
        teacher_start_seq = _top_seq(item.get("teacher_node") or "")
        answer_structure_for_item = answer_evidence_by_start.get(teacher_start_seq, False)
        existing_teacher_signatures = {
            _block_projection_signature(teacher_snapshot.document.blocks[seq])
            for seq in existing_teacher_nodes if seq is not None
        }
        unmatched_in_group = []
        for seq in sorted(existing_student_nodes):
            block = student_snapshot.document.blocks[seq]
            if seq in verified_student_subparts:
                continue
            if not re.match(r"^\s*(?:[（(]\d+[）)]|[①-⑳])", block.text or ""):
                continue
            if _block_projection_signature(block) not in existing_teacher_signatures:
                unmatched_in_group.append(seq)
        student_candidates = sorted(set(unmatched_in_group + student_candidates))
        additions = []
        used_teacher = set()
        for student_seq in student_candidates:
            student_block = student_snapshot.document.blocks[student_seq]
            # First align to explicit subquestions inside the paired teacher
            # question group. These are question bodies, not the teacher's
            # later answer/solution paragraphs. A body difference may be
            # accepted only through the bounded blank-fill relation below.
            exact = [seq for seq in teacher_question_subparts if seq not in used_teacher
                     and _block_projection_signature(student_block) ==
                     _block_projection_signature(teacher_snapshot.document.blocks[seq])]
            relation = "EXACT_ORDERED_SUBQUESTION_TEXT_AND_RESOURCE_SIGNATURE"
            candidates = exact
            if not candidates:
                candidates = [
                    seq for seq in teacher_question_subparts if seq not in used_teacher
                    and _answer_filled_subquestion_match(
                        student_block, teacher_snapshot.document.blocks[seq],
                        answer_structure_proven=answer_structure_for_item)
                ]
                relation = "ANSWER_FILLED_SUBQUESTION_WITH_BOUND_ANSWER_STRUCTURE"
            if not candidates:
                exact = [seq for seq in teacher_candidates if seq not in used_teacher
                         and _block_projection_signature(student_block) ==
                         _block_projection_signature(teacher_snapshot.document.blocks[seq])]
                candidates = exact
                relation = "EXACT_ORDERED_SUBQUESTION_TEXT_AND_RESOURCE_SIGNATURE"
            if not candidates:
                candidates = [
                    seq for seq in teacher_candidates if seq not in used_teacher
                    and _answer_filled_subquestion_match(
                        student_block, teacher_snapshot.document.blocks[seq],
                        answer_structure_proven=answer_structure_for_item)
                ]
                relation = "ANSWER_FILLED_SUBQUESTION_WITH_BOUND_ANSWER_STRUCTURE"
            if len(candidates) != 1:
                raise PairAlignmentError(
                    "ALIGNMENT_AMBIGUOUS" if candidates else "ALIGNMENT_UNRESOLVED",
                    "explicit student subquestion has no unique complete teacher counterpart",
                    {"canonical_occurrence_id": item["canonical_occurrence_id"],
                     "question_number": item["question_number"],
                     "student_node": "b%d" % student_seq,
                     "candidate_teacher_nodes": ["b%d" % seq for seq in candidates],
                     "required_relation": relation},
                )
            teacher_seq = candidates[0]
            if additions and (student_seq <= additions[-1][0] or
                              teacher_seq <= additions[-1][1]):
                raise PairAlignmentError(
                    "ALIGNMENT_AMBIGUOUS",
                    "paired subquestion matches do not preserve source order",
                    {"canonical_occurrence_id": item["canonical_occurrence_id"],
                     "question_number": item["question_number"],
                     "student_node": "b%d" % student_seq,
                     "teacher_node": "b%d" % teacher_seq},
                )
            used_teacher.add(teacher_seq)
            additions.append((student_seq, teacher_seq, relation))
        if additions:
            item["student_nodes"] = sorted(
                set(item["student_nodes"]) | {"b%d" % student_seq
                                             for student_seq, _teacher_seq, _relation in additions},
                key=lambda node: int(node[1:]))
            item["teacher_nodes"] = sorted(
                set(item["teacher_nodes"]) | {"b%d" % teacher_seq
                                             for _student_seq, teacher_seq, _relation in additions},
                key=lambda node: int(node[1:]))
            teacher_subquestion_evidence[item["canonical_occurrence_id"]] = [
                {"student_node": "b%d" % student_seq,
                 "teacher_node": "b%d" % teacher_seq,
                 "relation": relation}
                for student_seq, teacher_seq, relation in additions
            ]
    qg_intervals = []
    for item in mapping:
        seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        qg_intervals.append((min(seqs), max(seqs), item))
    qg_intervals.sort(key=lambda entry: (entry[0], entry[1]))
    annotation_owners: dict[str, set[str]] = {}
    annotation_units_by_owner: dict[str, set[str]] = {}
    units_by_id = {str(unit.get("id")): unit for unit in teacher_snapshot.units}

    for unit in teacher_snapshot.units:
        if unit.get("role") not in ("answer", "analysis"):
            continue
        spans = unit.get("spans") or []
        if not spans:
            continue
        unit_owner_ids: set[str] = set()
        for first, last in spans:
            start_id = teacher_snapshot.node_index.resolve_ref(first) or ""
            end_id = teacher_snapshot.node_index.resolve_ref(last) or ""
            start_seq, end_seq = _physical_seq(start_id), _physical_seq(end_id)
            if start_seq is None or end_seq is None:
                raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                         "teacher annotation does not resolve to physical source blocks",
                                         {"unit_id": unit.get("id"), "start": start_id,
                                          "end": end_id})
            lo, hi = sorted((start_seq, end_seq))
            # A-Line may label one broad annotation range across the end of
            # one answer and the next explicit question. Question-owned nodes
            # are already assigned by the canonical occurrence map; only the
            # remaining physical pieces need annotation ownership.
            question_owned = {}
            for q_start, q_end, occurrence in qg_intervals:
                for seq in range(max(lo, q_start), min(hi, q_end) + 1):
                    question_owned[seq] = occurrence
            unowned = [seq for seq in range(lo, hi + 1) if seq not in question_owned]
            if not unowned:
                continue
            pieces = []
            piece_start = piece_end = unowned[0]
            for seq in unowned[1:]:
                if seq == piece_end + 1:
                    piece_end = seq
                    continue
                pieces.append((piece_start, piece_end))
                piece_start = piece_end = seq
            pieces.append((piece_start, piece_end))

            # First accept an explicit parent/bind chain for the unowned
            # pieces, provided the same unit does not cross another canonical
            # question's physical range.
            parent = str(unit.get("parent") or unit.get("bind_to") or "")
            seen: set[str] = set()
            owner_unit_id = None
            while parent and parent not in seen:
                if parent in teacher_unit_to_occurrence:
                    owner_unit_id = parent
                    break
                seen.add(parent)
                parent_unit = units_by_id.get(parent)
                if parent_unit is None:
                    break
                parent = str(parent_unit.get("parent") or parent_unit.get("bind_to") or "")
            if owner_unit_id is not None:
                owner_occurrence = teacher_unit_to_occurrence[owner_unit_id]
                occurrence_id = str(owner_occurrence["canonical_occurrence_id"])
                conflicting = {str(item["canonical_occurrence_id"])
                               for item in question_owned.values()
                               if str(item["canonical_occurrence_id"]) != occurrence_id}
                if conflicting:
                    raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                             "teacher annotation parent conflicts with an enclosed question",
                                             {"unit_id": unit.get("id"),
                                              "parent_owner": occurrence_id,
                                              "question_owners": sorted(conflicting)})
                unit_owner_ids.add(occurrence_id)
                annotation_owners.setdefault(occurrence_id, set()).update(
                    "b%d" % seq for piece_lo, piece_hi in pieces
                    for seq in range(piece_lo, piece_hi + 1))
                annotation_units_by_owner.setdefault(occurrence_id, set()).add(str(unit.get("id")))
                continue

            # Otherwise each annotation piece must be wholly inside one
            # unambiguous gap following a canonical question.
            for piece_lo, piece_hi in pieces:
                gap_owners = []
                for interval_index, (_q_start, q_end, occurrence) in enumerate(qg_intervals):
                    next_start = (qg_intervals[interval_index + 1][0]
                                  if interval_index + 1 < len(qg_intervals)
                                  else len(teacher_snapshot.document.blocks))
                    if q_end < piece_lo and piece_hi < next_start:
                        gap_owners.append(occurrence)
                if len(gap_owners) != 1:
                    raise PairAlignmentError(
                        "ALIGNMENT_UNRESOLVED",
                        "teacher annotation piece has no unique preceding canonical question",
                        {"unit_id": unit.get("id"), "start": piece_lo, "end": piece_hi,
                         "candidate_count": len(gap_owners)})
                owner_occurrence = gap_owners[0]
                occurrence_id = str(owner_occurrence["canonical_occurrence_id"])
                unit_owner_ids.add(occurrence_id)
                owner_nodes = annotation_owners.setdefault(occurrence_id, set())
                owner_nodes.update("b%d" % seq for seq in range(piece_lo, piece_hi + 1))
                annotation_units_by_owner.setdefault(occurrence_id, set()).add(str(unit.get("id")))

        if len(unit_owner_ids) > 1:
            raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                     "one teacher annotation unit spans multiple canonical questions",
                                     {"unit_id": unit.get("id"),
                                      "owners": sorted(unit_owner_ids)})

    # A paired answer-rich edition may store the remaining multiple-choice
    # options in separate paragraphs that A-Line leaves outside the question
    # group. Attach them only when the in-group options plus the complete
    # ordered gap form A-D and the gap ends at that occurrence's owned answer.
    for item in mapping:
        occurrence_id = str(item["canonical_occurrence_id"])
        owned_answers = annotation_owners.get(occurrence_id, set())
        question_seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        if not owned_answers or not question_seqs or any(seq is None for seq in question_seqs):
            continue
        q_end = max(question_seqs)
        answer_starts = [int(node[1:]) for node in owned_answers if re.fullmatch(r"b\d+", node)]
        if not answer_starts:
            continue
        answer_start = min(answer_starts)
        if answer_start <= q_end + 1:
            continue
        interval = next((i for i, entry in enumerate(qg_intervals)
                         if entry[2]["canonical_occurrence_id"] == occurrence_id), None)
        if interval is None:
            continue
        next_question_start = (qg_intervals[interval + 1][0]
                               if interval + 1 < len(qg_intervals)
                               else len(teacher_snapshot.document.blocks))
        option_seqs = list(range(q_end + 1, answer_start))
        if not option_seqs or answer_start >= next_question_start:
            continue
        stem_text = " ".join(
            teacher_snapshot.document.blocks[seq].text or ""
            for seq in question_seqs
        )
        if not _CHOICE_STEM.search(stem_text):
            continue
        option_labels = []
        safe_option_group = True
        for seq in option_seqs:
            block = teacher_snapshot.document.blocks[seq]
            if (block.kind != "paragraph" or block.images or block.oles or
                    block.math_count or block.table is not None or block.textbox_texts):
                safe_option_group = False
                break
            matches = _CHOICE_MARKER.findall(block.text or "")
            if not matches:
                safe_option_group = False
                break
            option_labels.extend(label.upper() for label in matches)
        prefix_labels = []
        for seq in question_seqs:
            prefix_labels.extend(label.upper() for label in _CHOICE_MARKER.findall(
                teacher_snapshot.document.blocks[seq].text or ""))
        complete_labels = prefix_labels + option_labels
        if (not safe_option_group or not option_labels
                or complete_labels != ["A", "B", "C", "D"]):
            continue
        owner_nodes = annotation_owners.setdefault(occurrence_id, set())
        option_nodes = ["b%d" % seq for seq in option_seqs]
        if any(node in owner_nodes for node in option_nodes):
            raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                     "teacher option paragraph already has another annotation owner",
                                     {"canonical_occurrence_id": occurrence_id,
                                      "option_nodes": option_nodes})
        owner_nodes.update(option_nodes)
        item["teacher_only_option_extension"] = {
            "nodes": option_nodes,
            "labels": complete_labels,
            "relation": "COMPLETE_AD_OPTIONS_BETWEEN_CHOICE_STEM_AND_OWNED_ANSWER",
        }

    # Validate complete question bodies only after raw-range and proven
    # teacher-only option recovery have finalized the occurrence projections.
    # Checking earlier would reject valid occurrences merely because A-Line
    # left a continuation outside the question_group span.
    for item, left, right in zip(mapping, student, teacher):
        student_nodes = list(item.get("student_nodes") or [])
        teacher_nodes = list(item.get("teacher_nodes") or [])
        extension = item.get("teacher_only_option_extension") or {}
        teacher_nodes.extend(extension.get("nodes") or [])
        moved = item.get("teacher_moved_supplement") or {}
        if moved.get("teacher_node"):
            teacher_nodes = [node for node in teacher_nodes
                             if node != moved["teacher_node"]]
        student_start = _top_seq(item.get("student_node") or "")
        teacher_start = _top_seq(item.get("teacher_node") or "")
        if student_start is None or teacher_start is None:
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "complete body check has no physical occurrence start",
                                     {"canonical_occurrence_id": item["canonical_occurrence_id"]})
        left_final = replace(left, start_seq=student_start,
                             source_nodes=tuple(student_nodes))
        right_final = replace(right, start_seq=teacher_start,
                              source_nodes=tuple(dict.fromkeys(teacher_nodes)))
        if not _complete_occurrence_tail_match(
                student_snapshot, teacher_snapshot, left_final, right_final,
                student_source_path, teacher_source_path,
                answer_structure_proven=answer_evidence_by_start.get(
                    right.start_seq, False)):
            raise PairAlignmentError(
                "ALIGNMENT_UNRESOLVED",
                "complete unnumbered question continuation or resource sequence differs",
                {"canonical_occurrence_id": item["canonical_occurrence_id"],
                 "question_number": item["question_number"],
                 "student_nodes": student_nodes,
                 "teacher_nodes": right_final.source_nodes},
            )

    # Some reviewed A-Line outputs omit the answer role even though the raw
    # teacher source has an explicit standalone answer/solution marker. Attach
    # that marker only when it is the first substantive block immediately
    # after one canonical question and before the next canonical question.
    for index, (_q_start, q_end, item) in enumerate(qg_intervals):
        occurrence_id = str(item["canonical_occurrence_id"])
        if annotation_owners.get(occurrence_id):
            continue
        next_start = (qg_intervals[index + 1][0]
                      if index + 1 < len(qg_intervals)
                      else len(teacher_snapshot.document.blocks))
        answer_markers = [
            seq for seq in range(q_end + 1, next_start)
            if re.match(r"^\s*【(?:答案|解答)】",
                        teacher_snapshot.document.blocks[seq].text or "")
        ]
        if len(answer_markers) != 1:
            continue
        answer_start = answer_markers[0]
        prefix_seqs = list(range(q_end + 1, answer_start))
        prefix_is_empty = all(
            not (teacher_snapshot.document.blocks[seq].text or "").strip()
            and not teacher_snapshot.document.blocks[seq].images
            and not teacher_snapshot.document.blocks[seq].oles
            and not teacher_snapshot.document.blocks[seq].math_count
            and teacher_snapshot.document.blocks[seq].table is None
            and not teacher_snapshot.document.blocks[seq].textbox_texts
            for seq in prefix_seqs
        )
        teacher_prefix_images = [
            seq for seq in prefix_seqs
            if teacher_snapshot.document.blocks[seq].images
            and not (teacher_snapshot.document.blocks[seq].text or "").strip()
            and not teacher_snapshot.document.blocks[seq].oles
            and not teacher_snapshot.document.blocks[seq].math_count
            and teacher_snapshot.document.blocks[seq].table is None
            and not teacher_snapshot.document.blocks[seq].textbox_texts
        ]
        prefix_is_bounded = all(
            seq in teacher_prefix_images
            or (not (teacher_snapshot.document.blocks[seq].text or "").strip()
                and not teacher_snapshot.document.blocks[seq].images
                and not teacher_snapshot.document.blocks[seq].oles
                and not teacher_snapshot.document.blocks[seq].math_count
                and teacher_snapshot.document.blocks[seq].table is None
                and not teacher_snapshot.document.blocks[seq].textbox_texts)
            for seq in prefix_seqs
        )
        question_seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        stem = " ".join(teacher_snapshot.document.blocks[seq].text or ""
                        for seq in question_seqs if seq is not None)
        student_images = [
            seq for node in item.get("student_nodes", [])
            if (seq := _top_seq(node)) is not None
            and student_snapshot.document.blocks[seq].images
        ]
        prefix_is_bound_question_image = (
            prefix_is_bounded and len(teacher_prefix_images) == 1
            and teacher_prefix_images == [seq for seq in prefix_seqs
                                         if teacher_snapshot.document.blocks[seq].images]
            and len(student_images) == 1 and "图" in stem
        )
        if prefix_is_empty or prefix_is_bound_question_image:
            annotation_owners[occurrence_id] = {"b%d" % answer_start}
            item["teacher_detached_answer_start"] = {
                "node": "b%d" % answer_start,
                "relation": ("EXPLICIT_ANSWER_MARKER_AFTER_CANONICAL_QUESTION"
                             if prefix_is_empty else
                             "EXPLICIT_ANSWER_MARKER_AFTER_UNIQUE_QUESTION_IMAGE"),
            }

    # Some answer sections continue beyond the A-Line answer span through a
    # worked solution and an explicit terminal closure. Admit that bounded
    # answer chain only when it starts from an explicit answer/analysis marker,
    # ends before the next question/topic heading, and contains whole physical
    # blocks. Images, equations, OLEs, and atomic tables remain attached to the
    # same occurrence; none is split or reinterpreted.
    unit_by_id = {str(unit.get("id")): unit for unit in teacher_snapshot.units}
    explicit_topic_heading = re.compile(r"^\s*[一二三四五六七八九十百]+[、.．]\s*\S")
    answer_close = re.compile(r"^\s*(?:故答案为|故答案：|故选[：:]?|答：|答案：)")
    terminal_answer_close = re.compile(r"^\s*(?:故答案为|故答案：|故选[：:]?)")
    subquestion_start = re.compile(r"^\s*(?:答：)?[（(](\d+)[）)]")
    for item in mapping:
        occurrence_id = str(item["canonical_occurrence_id"])
        answer_nodes = annotation_owners.get(occurrence_id, set())
        question_seqs = [_top_seq(node) for node in item.get("teacher_nodes", [])]
        if not question_seqs or any(seq is None for seq in question_seqs):
            continue
        inline_answer_marker = any(
            re.search(r"【(?:答案|解答)】", teacher_snapshot.document.blocks[seq].text or "")
            for seq in question_seqs
        )
        if not answer_nodes and not inline_answer_marker:
            continue
        current_end = max(question_seqs)
        current_interval = next((i for i, entry in enumerate(qg_intervals)
                                 if entry[2]["canonical_occurrence_id"] == occurrence_id), None)
        next_question = (qg_intervals[current_interval + 1][0]
                         if current_interval is not None and current_interval + 1 < len(qg_intervals)
                         else len(teacher_snapshot.document.blocks))
        boundary = next_question
        for seq in range(current_end + 1, next_question):
            block = teacher_snapshot.document.blocks[seq]
            if explicit_topic_heading.match(block.text or ""):
                boundary = seq
                break

        expected_parts = []
        for node in item.get("teacher_nodes", []):
            seq = _top_seq(node)
            if seq is None:
                continue
            match = subquestion_start.match(teacher_snapshot.document.blocks[seq].text or "")
            if match:
                expected_parts.append(match.group(1))
        answer_parts = []
        for seq in range(current_end + 1, boundary):
            match = subquestion_start.match(teacher_snapshot.document.blocks[seq].text or "")
            if match:
                answer_parts.append((seq, match.group(1)))
        terminal_closures = [seq for seq in range(current_end + 1, boundary)
                             if terminal_answer_close.match(
                                 teacher_snapshot.document.blocks[seq].text or "")]
        if terminal_closures:
            end_seq = terminal_closures[-1]
        elif expected_parts:
            suffix = answer_parts[-len(expected_parts):]
            if [label for _seq, label in suffix] == expected_parts:
                end_seq = suffix[-1][0]
            else:
                summary_starts = [seq for seq in range(current_end + 1, boundary)
                                  if re.match(r"^\s*(?:答：|答案：)",
                                              teacher_snapshot.document.blocks[seq].text or "")]
                end_seq = (boundary - 1) if summary_starts else None
        else:
            closures = [seq for seq in range(current_end + 1, boundary)
                        if answer_close.match(teacher_snapshot.document.blocks[seq].text or "")]
            summary_starts = [seq for seq in closures
                              if re.match(r"^\s*(?:答：|答案：)",
                                          teacher_snapshot.document.blocks[seq].text or "")]
            end_seq = ((boundary - 1) if summary_starts else
                       (closures[-1] if closures else None))
        if end_seq is None:
            continue
        continuation = list(range(current_end + 1, end_seq + 1))
        safe_chain = all(
            teacher_snapshot.document.blocks[seq].kind in ("paragraph", "table")
            for seq in continuation)
        if continuation and safe_chain:
            owner_nodes = annotation_owners.setdefault(occurrence_id, set())
            owner_nodes.update("b%d" % seq for seq in continuation)
            item["teacher_answer_continuation_nodes"] = ["b%d" % seq for seq in continuation]

    for item in mapping:
        occurrence_id = item["canonical_occurrence_id"]
        if occurrence_id in teacher_subquestion_evidence:
            item["teacher_subquestion_matches"] = teacher_subquestion_evidence[occurrence_id]
        item["teacher_annotation_nodes"] = sorted(
            annotation_owners.get(occurrence_id, set()), key=lambda node: int(node[1:]))
        item["teacher_annotation_units"] = sorted(
            annotation_units_by_owner.get(occurrence_id, set()))
    return {
        "status": "ALIGNED",
        "student_sha256": student_snapshot.source_sha256,
        "teacher_sha256": teacher_snapshot.source_sha256,
        "student_occurrence_count": len(student),
        "teacher_occurrence_count": len(teacher),
        "unmatched_real_question_count": 0,
        "ambiguous_real_question_count": 0,
        "occurrences": mapping,
    }


def _block_projection_signature(block) -> str:
    """Strict residual-block fingerprint; answer blanks are bounded above."""
    normalized = unicodedata.normalize("NFKC", block.text or "")
    normalized = _SPACE.sub("", normalized)
    image_signature = tuple((image.kind, image.cx, image.cy) for image in block.images)
    table_signature = None
    if block.table is not None:
        table_signature = (block.table.n_rows, block.table.n_cols_max)
    payload = (block.kind, normalized, image_signature, block.math_count,
               len(block.oles), table_signature, len(block.textbox_texts))
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def _paired_prefix_signature(block) -> str:
    """Exact ordered prefix identity, allowing different image dimensions."""
    normalized = unicodedata.normalize("NFKC", block.text or "")
    image_signature = tuple(image.kind for image in block.images)
    table_signature = None if block.table is None else (block.table.n_rows, block.table.n_cols_max)
    payload = (block.kind, normalized, image_signature, block.math_count,
               len(block.oles), table_signature, len(block.textbox_texts))
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def _exact_option_subblock(teacher_text: str, student_blocks) -> list[tuple[str, int]]:
    """Find exact teacher A-D option segments in student question blocks."""
    option_pattern = re.compile(
        r"(?<![A-Za-z0-9])([A-D])[\.．、]\s*(.*?)(?=(?:\s*[A-D][\.．、])|$)", re.S | re.I)

    def entries(text):
        return [(match.group(1).upper(),
                 _normalized_block_text(match.group(1) + "．" + match.group(2)))
                for match in option_pattern.finditer(text or "")]

    teacher_entries = entries(teacher_text)
    if not teacher_entries:
        return []
    student_entries = []
    for seq, block in student_blocks:
        student_entries.extend((label, text, seq) for label, text in entries(block.text))
    result = []
    for label, text in teacher_entries:
        candidates = [(seq, student_text) for student_label, student_text, seq in student_entries
                      if student_label == label and student_text == text]
        unique_nodes = sorted({seq for seq, _text in candidates})
        if len(unique_nodes) != 1:
            return []
        result.append((label, unique_nodes[0]))
    return result


def project_pair_routes(student_snapshot, teacher_snapshot, alignment: dict[str, Any],
                        student_routes: dict[int, str], *,
                        student_cover_nodes: set[int] | None = None,
                        teacher_cover_nodes: set[int] | None = None) -> dict[str, Any]:
    """Project a complete student routing plan onto its aligned teacher source.

    Canonical question spans receive one student-chosen destination. All
    remaining physical blocks must align one-to-one in source order with an
    identical strict structural fingerprint. Any unbound teacher annotation,
    missing block, resource-shape mismatch, or ambiguous occurrence refuses
    projection instead of invoking a second router.
    """
    total_student = len(student_snapshot.document.blocks)
    total_teacher = len(teacher_snapshot.document.blocks)
    student_cover_nodes = set(student_cover_nodes or ())
    teacher_cover_nodes = set(teacher_cover_nodes or ())
    if set(student_routes) != set(range(total_student)):
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "student canonical plan does not route every physical block")
    if any(not 0 <= seq < total_student for seq in student_cover_nodes) or any(
            not 0 <= seq < total_teacher for seq in teacher_cover_nodes):
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "cover metadata ownership includes an invalid source block")
    if any(student_routes.get(seq) not in (None, "cover") for seq in student_cover_nodes):
        raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                 "student cover metadata block also has a teaching-slot route")
    student_q_nodes: set[int] = set()
    teacher_q_nodes: set[int] = set()
    canonical_student_routes = dict(student_routes)
    for seq in student_cover_nodes:
        canonical_student_routes[seq] = "cover"
    teacher_routes: dict[int, str] = {}
    for seq in teacher_cover_nodes:
        teacher_routes[seq] = "cover"
    occurrence_evidence = []
    for occurrence in alignment.get("occurrences", []):
        student_nodes = tuple(occurrence.get("student_nodes") or ())
        teacher_nodes = tuple(occurrence.get("teacher_nodes") or ())
        if not student_nodes or not teacher_nodes:
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "canonical occurrence lacks complete source spans",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id")})
        if any(not re.fullmatch(r"b\d+", node) for node in (*student_nodes, *teacher_nodes)):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "canonical occurrence includes non-top-level endpoints",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id")})
        student_seqs = {int(node[1:]) for node in student_nodes}
        teacher_seqs = {int(node[1:]) for node in teacher_nodes}
        if student_q_nodes & student_seqs or teacher_q_nodes & teacher_seqs:
            raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                     "question source spans overlap across occurrences",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id")})
        canonical_start = str(occurrence.get("student_node") or "")
        if not re.fullmatch(r"b\d+", canonical_start):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "canonical student question start is not a top-level block",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id"),
                                      "student_node": canonical_start})
        start_seq = int(canonical_start[1:])
        destination = student_routes.get(start_seq)
        if destination not in ("knowledge", "immediate", "final"):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "canonical student question start has no destination",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id"),
                                      "student_node": occurrence.get("student_node")})
        student_q_nodes.update(student_seqs)
        teacher_q_nodes.update(teacher_seqs)
        annotation_nodes = tuple(occurrence.get("teacher_annotation_nodes") or ())
        if any(not re.fullmatch(r"b\d+", node) for node in annotation_nodes):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "teacher annotation includes non-top-level endpoints",
                                     {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id")})
        for node in annotation_nodes:
            seq = int(node[1:])
            if not 0 <= seq < total_teacher:
                raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                         "teacher annotation endpoint is outside the source document",
                                         {"canonical_occurrence_id": occurrence.get("canonical_occurrence_id"),
                                          "node": node})
            if seq in teacher_seqs:
                # Already covered by this canonical question span.
                continue
            if seq in teacher_q_nodes:
                raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                         "teacher annotation overlaps another canonical occurrence",
                                         {"block_id": node})
            teacher_q_nodes.add(seq)
            existing = teacher_routes.get(seq)
            if existing is not None and existing != destination:
                raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                         "teacher annotation block has multiple canonical owners",
                                         {"block_id": node})
            teacher_routes[seq] = destination
        for seq in student_seqs:
            canonical_student_routes[seq] = destination
        for seq in teacher_seqs:
            existing = teacher_routes.get(seq)
            if existing is not None and existing != destination:
                raise PairAlignmentError("ALIGNMENT_AMBIGUOUS",
                                         "teacher physical block is shared by canonical questions in different slots",
                                         {"block_id": "b%d" % seq})
            teacher_routes[seq] = destination
        occurrence_evidence.append({
            **occurrence,
            "destination_slot": destination,
            "source_teacher_nodes": ["b%d" % seq for seq in sorted(teacher_seqs)],
            "source_student_nodes": ["b%d" % seq for seq in sorted(student_seqs)],
            "source_teacher_annotation_nodes": list(annotation_nodes),
        })

    # Map the document prefix before the first canonical question only when
    # both peers have the same ordered physical topology and exact per-block
    # text/resource signature. This is provenance evidence for front matter,
    # not question identity or question routing.
    student_intervals = []
    teacher_intervals = []
    for occurrence in alignment.get("occurrences", []):
        student_seqs = [_top_seq(node) for node in occurrence.get("student_nodes", [])]
        teacher_seqs = [_top_seq(node) for node in occurrence.get("teacher_nodes", [])]
        student_intervals.append((min(student_seqs), max(student_seqs), occurrence))
        teacher_intervals.append((min(teacher_seqs), max(teacher_seqs), occurrence))
    student_intervals.sort(key=lambda item: item[0])
    teacher_intervals.sort(key=lambda item: item[0])
    residual_map = []
    student_prefix_end = student_intervals[0][0]
    teacher_prefix_end = teacher_intervals[0][0]
    student_prefix_nodes = [seq for seq in range(student_prefix_end)
                            if seq not in student_cover_nodes]
    teacher_prefix_nodes = [seq for seq in range(teacher_prefix_end)
                            if seq not in teacher_cover_nodes]
    if len(student_prefix_nodes) != len(teacher_prefix_nodes):
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "paired non-metadata prefixes differ before the first canonical question",
                                 {"student_prefix_blocks": len(student_prefix_nodes),
                                  "teacher_prefix_blocks": len(teacher_prefix_nodes)})
    if any(seq >= student_prefix_end for seq in student_cover_nodes) or any(
            seq >= teacher_prefix_end for seq in teacher_cover_nodes):
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "cover metadata must precede the first canonical question")
    for student_seq, teacher_seq in zip(student_prefix_nodes, teacher_prefix_nodes):
        if _paired_prefix_signature(student_snapshot.document.blocks[student_seq]) != \
                _paired_prefix_signature(teacher_snapshot.document.blocks[teacher_seq]):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "paired source prefix blocks do not match exactly in order",
                                     {"student_block": "b%d" % student_seq,
                                      "teacher_block": "b%d" % teacher_seq})
        destination = canonical_student_routes[student_seq]
        if destination == "cover":
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "cover ownership was not excluded from paired prefix projection")
        teacher_routes[teacher_seq] = destination
        residual_map.append({"student_node": "b%d" % student_seq,
                             "teacher_node": "b%d" % teacher_seq,
                             "destination_slot": canonical_student_routes[student_seq],
                             "fingerprint_match": "EXACT_ORDERED_PREFIX_STRUCTURE"})

    # Residual blocks require both canonical neighboring-question context and
    # a unique structural signature match. Never assign an unknown block just
    # because it falls between two question starts.
    def context_for(seq: int, intervals: list[tuple[int, int, dict[str, Any]]]):
        previous = [entry for entry in intervals if entry[1] < seq]
        following = [entry for entry in intervals if entry[0] > seq]
        previous_id = (max(previous, key=lambda entry: entry[1])[2]["canonical_occurrence_id"]
                       if previous else None)
        next_id = (min(following, key=lambda entry: entry[0])[2]["canonical_occurrence_id"]
                   if following else None)
        return previous_id, next_id

    student_residuals: dict[tuple, list[int]] = {}
    prefix_student = set(range(student_prefix_end))
    for seq in range(total_student):
        if seq in student_q_nodes or seq in prefix_student:
            continue
        key = (context_for(seq, student_intervals),
               _block_projection_signature(student_snapshot.document.blocks[seq]))
        student_residuals.setdefault(key, []).append(seq)

    teacher_residuals: dict[tuple, list[int]] = {}
    prefix_teacher = set(range(teacher_prefix_end))
    for seq in range(total_teacher):
        if seq in teacher_routes or seq in prefix_teacher:
            continue
        key = (context_for(seq, teacher_intervals),
               _block_projection_signature(teacher_snapshot.document.blocks[seq]))
        teacher_residuals.setdefault(key, []).append(seq)

    for key, teacher_nodes in teacher_residuals.items():
        student_nodes = student_residuals.get(key, [])
        if len(teacher_nodes) == 1 and not student_nodes:
            teacher_seq = teacher_nodes[0]
            previous_id, next_id = key[0]
            possible_owners = [entry for entry in occurrence_evidence
                               if entry["canonical_occurrence_id"] == previous_id]
            option_matches = []
            teacher_block = teacher_snapshot.document.blocks[teacher_seq]
            for entry in possible_owners:
                if (teacher_block.images or teacher_block.oles or teacher_block.math_count
                        or teacher_block.table is not None or teacher_block.textbox_texts):
                    continue
                source_seqs = [int(node[1:]) for node in entry["source_student_nodes"]]
                matched_options = _exact_option_subblock(
                    teacher_block.text,
                    [(seq, student_snapshot.document.blocks[seq]) for seq in source_seqs])
                if matched_options:
                    option_matches.append((entry, matched_options))
            if len(option_matches) == 1:
                owner, matched_options = option_matches[0]
                teacher_routes[teacher_seq] = owner["destination_slot"]
                residual_map.append({"student_node": "b%d" % matched_options[0][1],
                                     "teacher_node": "b%d" % teacher_seq,
                                     "source_student_nodes": sorted({"b%d" % seq
                                                                      for _label, seq in matched_options},
                                                                     key=lambda node: int(node[1:])),
                                     "option_labels": [label for label, _seq in matched_options],
                                     "canonical_occurrence_id": owner["canonical_occurrence_id"],
                                     "destination_slot": owner["destination_slot"],
                                     "fingerprint_match": "EXACT_OPTION_SUBBLOCK_IN_CANONICAL_STUDENT_OCCURRENCE"})
                continue
            # A teacher diagram may sit just outside its A-Line question span,
            # immediately before that question's explicit answer section. Bind
            # it only when the canonical stem explicitly references a figure,
            # the student occurrence owns exactly one image, and this is the
            # sole unassigned teacher image in that same canonical interval.
            if len(teacher_nodes) == 1 and not student_nodes:
                teacher_seq = teacher_nodes[0]
                block = teacher_snapshot.document.blocks[teacher_seq]
                previous_id, next_id = key[0]
                owners = [entry for entry in occurrence_evidence
                          if entry["canonical_occurrence_id"] == previous_id]
                if (len(owners) == 1 and next_id is None
                        and teacher_seq == total_teacher - 1
                        and not (block.text or "").strip() and not block.images
                        and not block.oles and not block.math_count and block.table is None
                        and not block.textbox_texts):
                    owner = owners[0]
                    terminal_student_nodes = [
                        node for node in (owner.get("source_student_nodes") or [])
                        if int(node[1:]) == total_student - 1
                        and not (student_snapshot.document.blocks[int(node[1:])].text or "").strip()
                        and not student_snapshot.document.blocks[int(node[1:])].images
                        and not student_snapshot.document.blocks[int(node[1:])].oles
                        and not student_snapshot.document.blocks[int(node[1:])].math_count
                        and student_snapshot.document.blocks[int(node[1:])].table is None
                        and not student_snapshot.document.blocks[int(node[1:])].textbox_texts
                    ]
                    if len(terminal_student_nodes) == 1:
                        teacher_routes[teacher_seq] = owner["destination_slot"]
                        residual_map.append({
                            "student_node": terminal_student_nodes[0],
                            "teacher_node": "b%d" % teacher_seq,
                            "canonical_occurrence_id": previous_id,
                            "destination_slot": owner["destination_slot"],
                            "fingerprint_match": "EXACT_UNIQUE_TERMINAL_EMPTY_BLOCK_IN_PAIRED_SOURCE",
                        })
                        continue
                if len(owners) == 1 and block.images and not (
                        block.text.strip() or block.oles or block.math_count or
                        block.table is not None or block.textbox_texts):
                    owner = owners[0]
                    source_occurrence = next(
                        (item for item in alignment.get("occurrences", [])
                         if item["canonical_occurrence_id"] == previous_id), None)
                    teacher_images_in_interval = [
                        seq for (context, _signature), nodes in teacher_residuals.items()
                        if context == key[0]
                        for seq in nodes if teacher_snapshot.document.blocks[seq].images
                    ]
                    student_image_nodes = [
                        node for node in (owner.get("source_student_nodes") or [])
                        if student_snapshot.document.blocks[int(node[1:])].images
                    ]
                    stem = " ".join(
                        teacher_snapshot.document.blocks[int(node[1:])].text or ""
                        for node in (owner.get("source_teacher_nodes") or [])
                    )
                    next_teacher_block = (teacher_snapshot.document.blocks[teacher_seq + 1]
                                          if teacher_seq + 1 < total_teacher else None)
                    before_answer = bool(
                        next_teacher_block and
                        re.match(r"^\s*【(?:答案|解答)】", next_teacher_block.text or "") and
                        teacher_routes.get(teacher_seq + 1) == owner["destination_slot"]
                    )
                    if (source_occurrence is not None and "图" in stem
                            and len(student_image_nodes) == 1
                            and teacher_images_in_interval == [teacher_seq]
                            and before_answer):
                        teacher_routes[teacher_seq] = owner["destination_slot"]
                        residual_map.append({
                            "student_node": student_image_nodes[0],
                            "teacher_node": "b%d" % teacher_seq,
                            "canonical_occurrence_id": previous_id,
                            "destination_slot": owner["destination_slot"],
                            "fingerprint_match": "QUESTION_IMAGE_BOUND_BY_CANONICAL_STEM_AND_UNIQUE_OCCURRENCE_ASSET",
                        })
                        continue
        if len(teacher_nodes) != 1 or len(student_nodes) != 1:
            block = teacher_snapshot.document.blocks[teacher_nodes[0]]
            raise PairAlignmentError("ALIGNMENT_AMBIGUOUS" if student_nodes else "ALIGNMENT_UNRESOLVED",
                                     "teacher residual has no unique structurally identical student peer",
                                     {"teacher_nodes": ["b%d" % seq for seq in teacher_nodes],
                                      "student_candidates": ["b%d" % seq for seq in student_nodes],
                                      "context": key[0], "block_kind": block.kind,
                                      "block_text": block.text[:120],
                                      "resource_counts": {"images": len(block.images),
                                                          "oles": len(block.oles),
                                                          "math": block.math_count,
                                                          "table": block.table is not None}})
        teacher_seq, student_seq = teacher_nodes[0], student_nodes[0]
        destination = canonical_student_routes.get(student_seq)
        if destination not in ("knowledge", "immediate", "final"):
            raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                     "unique residual peer has no canonical student route",
                                     {"student_node": "b%d" % student_seq,
                                      "teacher_node": "b%d" % teacher_seq})
        teacher_routes[teacher_seq] = destination
        residual_map.append({"student_node": "b%d" % student_seq,
                             "teacher_node": "b%d" % teacher_seq,
                             "destination_slot": destination,
                             "fingerprint_match": "UNIQUE_CONTEXT_AND_STRUCTURAL_SIGNATURE"})

    if set(teacher_routes) != set(range(total_teacher)):
        missing = sorted(set(range(total_teacher)) - set(teacher_routes))
        raise PairAlignmentError("ALIGNMENT_UNRESOLVED",
                                 "teacher canonical projection leaves physical blocks unassigned",
                                 {"unassigned_teacher_blocks": ["b%d" % seq for seq in missing[:12]],
                                  "count": len(missing)})
    return {
        "status": "PROJECTED",
        "student_block_routes": {str(seq): slot for seq, slot in sorted(canonical_student_routes.items())},
        "teacher_block_routes": {str(seq): slot for seq, slot in sorted(teacher_routes.items())},
        "teacher_student_residual_block_map": residual_map,
        "occurrences": occurrence_evidence,
        "source_block_counts": {"student": total_student, "teacher": total_teacher},
    }

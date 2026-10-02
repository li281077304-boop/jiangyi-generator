"""Fail-closed product-content checks for generated handout DOCX files.

These checks are deliberately structural and conservative. They do not alter
source content or the V0.9 writer; they prevent repeated template/body content
from being published as a successful product.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
import zipfile


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_BODY = "{%s}body" % W_NS
W_P = "{%s}p" % W_NS
W_T = "{%s}t" % W_NS
W_TBL = "{%s}tbl" % W_NS
W_TXBX = "{%s}txbxContent" % W_NS

TEMPLATE_TITLE = "学科教师辅导讲义"
TEMPLATE_SECTION_SEQUENCE = (
    "课堂启动", "知识回顾", "知识精讲", "即时训练", "归纳总结", "巩固练习",
)
MIN_REPEAT_PARAGRAPHS = 12
MIN_REPEAT_TEXT_CHARS = 1200
EXPANSION_WARNING_RATIO = 2.0


class ProductIntegrityError(ValueError):
    def __init__(self, reason_code: str, detail: str):
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail


@dataclass(frozen=True)
class ProductDocumentMetrics:
    main_story_paragraphs: int
    top_level_blocks: int
    text_chars: int
    template_title_count: int
    template_cycles: int
    repeated_sequences: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "main_story_paragraphs": self.main_story_paragraphs,
            "top_level_blocks": self.top_level_blocks,
            "text_chars": self.text_chars,
            "template_title_count": self.template_title_count,
            "template_cycles": self.template_cycles,
            "repeated_sequences": [dict(item) for item in self.repeated_sequences],
        }


def _main_paragraphs(body: ET.Element) -> list[ET.Element]:
    paragraphs: list[ET.Element] = []

    def visit(node: ET.Element) -> None:
        if node.tag == W_TXBX:
            return
        if node.tag == W_P:
            paragraphs.append(node)
            return
        for child in list(node):
            visit(child)

    visit(body)
    return paragraphs


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []

    def visit(node: ET.Element) -> None:
        if node.tag == W_TXBX:
            return
        if node.tag == W_T:
            parts.append(node.text or "")
            return
        for child in list(node):
            visit(child)

    visit(paragraph)
    return "".join(parts)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_heading(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _template_title(value: str) -> bool:
    return TEMPLATE_TITLE in _normalize_heading(value)


def _template_heading(value: str, heading: str) -> bool:
    normalized = _normalize_heading(value)
    return heading in normalized and len(normalized) <= max(48, len(heading) + 24)


def _count_template_cycles(paragraphs: list[str]) -> tuple[int, int]:
    title_count = sum(_normalize_heading(text).count(TEMPLATE_TITLE) for text in paragraphs)
    titles = [index for index, text in enumerate(paragraphs) if _template_title(text)]
    cycles = 0
    for title_index in titles:
        cursor = title_index + 1
        complete = True
        for heading in TEMPLATE_SECTION_SEQUENCE:
            match = next((index for index in range(cursor, len(paragraphs))
                          if _template_heading(paragraphs[index], heading)), None)
            if match is None:
                complete = False
                break
            cursor = match + 1
        if complete:
            cycles += 1
    return title_count, cycles


def _repeated_sequences(paragraphs: list[str]) -> tuple[dict[str, Any], ...]:
    texts = [_normalize_text(text) for text in paragraphs]
    texts = [text for text in texts if text]
    window = MIN_REPEAT_PARAGRAPHS
    if len(texts) < window * 2:
        return ()
    candidates: dict[bytes, list[int]] = {}
    sequences: list[dict[str, Any]] = []
    consumed: list[tuple[int, int]] = []
    for start in range(len(texts) - window + 1):
        chunk = texts[start:start + window]
        digest = hashlib.sha256("\x1f".join(chunk).encode("utf-8")).digest()
        prior = candidates.setdefault(digest, [])
        for other in prior:
            if start < other + window or any(a <= start < b or a <= other < b for a, b in consumed):
                continue
            length = window
            while (start + length < len(texts) and other + length < len(texts)
                   and texts[start + length] == texts[other + length]):
                length += 1
            text_chars = sum(len(item) for item in texts[start:start + length])
            if length >= window and text_chars >= MIN_REPEAT_TEXT_CHARS:
                first, second = sorted((other, start))
                sequences.append({
                    "first_nonempty_paragraph": first,
                    "second_nonempty_paragraph": second,
                    "paragraphs": length,
                    "text_chars": text_chars,
                })
                consumed.append((second, second + length))
                break
        if len(prior) < 8:
            prior.append(start)
    return tuple(sequences)


def inspect_product_docx(path: str | Path) -> ProductDocumentMetrics:
    source = Path(path)
    try:
        with zipfile.ZipFile(source) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ProductIntegrityError("PRODUCT_DOCX_UNREADABLE", str(exc)) from exc
    body = root.find(W_BODY)
    if body is None:
        raise ProductIntegrityError("PRODUCT_DOCX_UNREADABLE", "word/document.xml has no w:body")
    paragraphs = [_paragraph_text(item) for item in _main_paragraphs(body)]
    title_count, cycles = _count_template_cycles(paragraphs)
    # Preserve the paragraph boundary representation used by the audit: one LF
    # between every paragraph, including empty paragraphs.
    text_chars = len("\n".join(paragraphs))
    top_level_blocks = sum(child.tag in (W_P, W_TBL) for child in list(body))
    return ProductDocumentMetrics(
        main_story_paragraphs=len(paragraphs),
        top_level_blocks=top_level_blocks,
        text_chars=text_chars,
        template_title_count=title_count,
        template_cycles=cycles,
        repeated_sequences=_repeated_sequences(paragraphs),
    )


def inspect_input_provenance(path: str | Path) -> dict[str, Any]:
    metrics = inspect_product_docx(path)
    errors = []
    if metrics.template_cycles >= 2 or metrics.template_title_count >= 2:
        errors.append("POSSIBLE_GENERATED_OUTPUT_REINGESTION")
    return {
        "path": str(Path(path).resolve()),
        "sha256": _sha256(path),
        "metrics": metrics.as_dict(),
        "errors": errors,
        "accepted": not errors,
    }


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slot_overlaps(plan: Any) -> list[dict[str, str]]:
    if plan is None:
        return []
    owners: dict[str, str] = {}
    overlaps: list[dict[str, str]] = []
    for slot, spans in (getattr(plan, "slots", {}) or {}).items():
        for span in spans:
            first = str(getattr(span, "start", ""))
            last = str(getattr(span, "end", ""))
            # Slot Router currently emits top-level bN leaf spans. Any other
            # coordinate must be resolved before this product gate can certify it.
            match_first = re.fullmatch(r"b(\d+)", first)
            match_last = re.fullmatch(r"b(\d+)", last)
            if not match_first or not match_last or int(match_first.group(1)) > int(match_last.group(1)):
                overlaps.append({"block_id": first + ".." + last, "first_slot": slot,
                                 "second_slot": "UNRESOLVED_RANGE"})
                continue
            blocks = ["b%d" % index for index in
                      range(int(match_first.group(1)), int(match_last.group(1)) + 1)]
            for block_id in blocks:
                prior = owners.get(block_id)
                if prior is not None and prior != slot:
                    overlaps.append({"block_id": block_id, "first_slot": prior, "second_slot": slot})
                else:
                    owners[block_id] = slot
    return overlaps


def validate_product_integrity(source_path: str | Path, output_path: str | Path,
                               *, plan: Any = None) -> dict[str, Any]:
    source_metrics = inspect_product_docx(source_path)
    output_metrics = inspect_product_docx(output_path)
    source_chars = source_metrics.text_chars
    expansion_ratio = (output_metrics.text_chars / source_chars) if source_chars else None
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if output_metrics.template_cycles > 1 or output_metrics.template_title_count > 1:
        errors.append({"reason_code": "PRODUCT_TEMPLATE_RECURSION",
                       "detail": "output contains %d template titles and %d complete lecture-template sequences" %
                       (output_metrics.template_title_count, output_metrics.template_cycles)})
        errors.append({"reason_code": "PRODUCT_TEMPLATE_RESIDUE",
                       "detail": "a complete source/template sequence remains in generated body"})
    if output_metrics.repeated_sequences:
        errors.append({"reason_code": "PRODUCT_REPEATED_BLOCK_SEQUENCE",
                       "detail": "one or more long paragraph sequences repeat in the output"})
    overlaps = _slot_overlaps(plan)
    if overlaps:
        errors.append({"reason_code": "PRODUCT_SLOT_OVERLAP",
                       "detail": "source blocks are assigned to multiple destination slots",
                       "blocks": overlaps})
    if expansion_ratio is not None and expansion_ratio > EXPANSION_WARNING_RATIO:
        warnings.append({"reason_code": "PRODUCT_EXPANSION_SUSPECTED",
                         "detail": "output text length exceeds %.1fx source length" %
                         EXPANSION_WARNING_RATIO})
    return {
        "gate": "PRODUCT_INTEGRITY_GATE",
        "accepted": not errors,
        "errors": errors,
        "warnings": warnings,
        "source": {"sha256": _sha256(source_path), **source_metrics.as_dict()},
        "output": {"sha256": _sha256(output_path), **output_metrics.as_dict()},
        "expansion_ratio": round(expansion_ratio, 4) if expansion_ratio is not None else None,
    }

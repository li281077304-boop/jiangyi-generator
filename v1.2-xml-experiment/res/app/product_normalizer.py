"""Shared V1.2 product rules applied after every renderer has finished."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import uuid
import zipfile

from docx import Document

from package_validator import validate_package


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W_P = W + "p"
W_TC = W + "tc"


def inspect_delivered_slots(path: str | Path, template_type: str, *,
                            source_path: str | Path | None = None) -> dict:
    """Inspect final template sections rather than trusting a pre-render plan."""
    from template_slot_composer import _paragraph_text
    document = Document(str(path))
    source_media = set()
    if source_path is not None:
        with zipfile.ZipFile(source_path) as source:
            source_media = {hashlib.sha256(source.read(name)).hexdigest()
                            for name in source.namelist() if name.startswith('word/media/')}

    def source_image_present(node):
        # Verify origin without recognizing image text. Template decorations
        # alone cannot substantiate a populated training section.
        for element in node.iter():
            for attribute, value in element.attrib.items():
                if attribute in ('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed',
                                  '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'):
                    part = document.part.related_parts.get(value)
                    if part is not None and hashlib.sha256(part.blob).hexdigest() in source_media:
                        return True
        return False
    paragraphs = list(document.element.body.iter(W_P))
    labels = {
        "immediate": {"即时训练", "三、即时训练", "四、即时训练"},
        "final": {"六、巩固练习", "五、巩固练习"} if template_type == "1v1"
                 else {"六、出门测试", "五、出门测试"},
    }
    stops = {"归纳总结", "四、归纳总结", "五、归纳总结"} | labels["final"]
    sections = {}
    for slot, names in labels.items():
        anchors = [p for p in paragraphs if _paragraph_text(p) in names]
        if len(anchors) != 1:
            sections[slot] = {"verified": False, "reason": "ANCHOR_NOT_UNIQUE"}
            continue
        node = anchors[0].getnext()
        substantive = []
        while node is not None:
            if node.tag == W_P and _paragraph_text(node) in stops:
                break
            # A template divider contains an ornamental picture. Media alone
            # therefore cannot prove that a training section was populated.
            if (any((t.text or "").strip().strip('~') for t in node.iter(W + "t")) or
                    source_image_present(node)):
                substantive.append(node)
            node = node.getnext()
        sections[slot] = {"verified": bool(substantive), "content_blocks": len(substantive)}
    return {"verified": all(section["verified"] for section in sections.values()),
            "sections": sections, "sha256": _sha256(Path(path))}
_KNOWLEDGE_ANCHOR = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
_NEXT_SLOT_HEADINGS = {
    "即时训练", "六、巩固练习", "六、出门测试",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonicalize_package_timestamps(source: Path, destination: Path) -> None:
    """Write a stable DOCX ZIP so renderer timestamp changes do not alter output SHA."""
    with zipfile.ZipFile(source, "r") as package:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as normalized:
            normalized.comment = package.comment
            for entry in package.infolist():
                stable = zipfile.ZipInfo(entry.filename, date_time=(1980, 1, 1, 0, 0, 0))
                stable.compress_type = entry.compress_type
                stable.create_system = entry.create_system
                stable.external_attr = entry.external_attr
                stable.internal_attr = entry.internal_attr
                stable.comment = entry.comment
                normalized.writestr(stable, package.read(entry.filename))


def _project_short_source_title(document, display_topic: str, template_type: str) -> dict:
    """Shorten only a source-derived title immediately under the knowledge slot.

    The source heading is preserved unless deterministic topic normalization
    produces the same title already selected for the cover. This ties the edit
    to the known slot structure and avoids global text replacement.
    """
    from template_slot_composer import _paragraph_text, _set_paragraph_text
    from topic_normalization import normalize_display_topic

    anchors = [paragraph for cell in document.element.body.iter(W_TC)
               for paragraph in cell.findall(W_P)
               if _paragraph_text(paragraph) == _KNOWLEDGE_ANCHOR.get(template_type)]
    if len(anchors) != 1:
        return {"status": "NOT_APPLICABLE", "reason": "KNOWLEDGE_ANCHOR_NOT_UNIQUE",
                "anchor_count": len(anchors)}

    node = anchors[0].getnext()
    while node is not None:
        if node.tag == W_P:
            source_title = _paragraph_text(node)
            if not source_title:
                node = node.getnext()
                continue
            if source_title in _NEXT_SLOT_HEADINGS:
                return {"status": "NOT_APPLICABLE", "reason": "NO_SOURCE_TITLE"}
            normalized = normalize_display_topic(source_title)
            if (normalized != source_title and normalized
                    and normalized == str(display_topic or "").strip()):
                _set_paragraph_text(node, normalized)
                return {"status": "APPLIED", "source_title": source_title,
                        "display_title": normalized}
            return {"status": "UNCHANGED", "reason": "TITLE_NOT_EXACTLY_BOUND",
                    "candidate": source_title}
        if node.tag == W_TC:
            break
        node = node.getnext()
    return {"status": "NOT_APPLICABLE", "reason": "NO_TITLE_PARAGRAPH"}


def normalize_product_docx(source_path: str | Path, output_path: str | Path, *,
                           template_type: str, metadata: dict) -> dict:
    """Apply the reviewed cover and page-one contract to an XML or V0.9 DOCX.

    The source renderer artifact stays untouched. The normalizer writes a fresh
    same-directory staging package and fails closed if the known V1.2 template
    carrier cannot be resolved or the resulting package is invalid.
    """
    source = Path(source_path).resolve()
    output = Path(output_path).resolve()
    if not source.is_file() or source.stat().st_size <= 0:
        raise ValueError("PRODUCT_NORMALIZATION_SOURCE_INVALID")
    if output.exists():
        raise FileExistsError("product normalizer requires a fresh output path")
    output.parent.mkdir(parents=True, exist_ok=True)

    # Import lazily to share the single tested structural implementation with
    # the XML composer without making Renderer selection part of this module.
    from template_slot_composer import _anchor_module2_end_divider, _fill_cover_metadata, omit_empty_knowledge

    document = Document(str(source))
    _fill_cover_metadata(document, template_type, dict(metadata))
    title_projection = _project_short_source_title(
        document, metadata.get("topic", ""), template_type)
    anchor = _anchor_module2_end_divider(document, template_type)
    omitted = omit_empty_knowledge(document, template_type)
    temporary = output.with_name(".%s.normalize-%s.docx" % (output.stem, uuid.uuid4().hex))
    canonical = output.with_name(".%s.canonical-%s.docx" % (output.stem, uuid.uuid4().hex))
    try:
        document.save(str(temporary))
        _canonicalize_package_timestamps(temporary, canonical)
        os.replace(canonical, output)
        package = validate_package(str(output))
        if package.get("valid") is not True:
            raise ValueError("PRODUCT_NORMALIZATION_PACKAGE_FAILED: %s" %
                             "; ".join(package.get("errors", [])[:5]))
        return {
            "status": "NORMALIZED",
            "empty_knowledge_module": omitted,
            "version": "V1.2_PRODUCT_NORMALIZATION_V1",
            "source_path": str(source),
            "output_path": str(output),
            "source_sha256": _sha256(source),
            "output_sha256": _sha256(output),
            "template_type": template_type,
            "cover_fields": {
                "objectives": "POPULATED" if metadata.get("objectives") else "EMPTY_WITH_WARNING",
                "difficulties": "POPULATED" if metadata.get("difficulties") else "EMPTY_WITH_WARNING",
                "cover_display": metadata.get("cover_display", {}),
            },
            "source_title_projection": title_projection,
            "module2_end_divider_anchor": anchor,
            "package_validation": package,
        }
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
        canonical.unlink(missing_ok=True)

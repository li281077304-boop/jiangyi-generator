# -*- coding: utf-8 -*-
"""Focused structural checks for DOCX packages produced by the XML engine.

This is deliberately a small, business-focused OPC/WordprocessingML validator.
It checks the references the block importer is expected to create; it is not an
ECMA-376 schema validator.
"""
from __future__ import annotations

import posixpath
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET
from urllib.parse import unquote


PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
O_NS = "urn:schemas-microsoft-com:office:office"

_BUILTIN_STYLES = {
    "Normal", "DefaultParagraphFont", "TableNormal", "NoList",
    "Heading1", "Heading2", "Heading3", "Heading4", "Heading5",
    "Heading6", "Heading7", "Heading8", "Heading9", "Title",
    "Subtitle", "ListParagraph", "FootnoteText", "EndnoteText",
    "Header", "Footer", "Caption", "TOCHeading", "Quote",
    "IntenseQuote", "Hyperlink", "FollowedHyperlink",
}


def _rels_name(source):
    """Return the OPC relationship part name for a package part."""
    if not source:
        return "_rels/.rels"
    directory, filename = posixpath.split(source)
    return posixpath.join(directory, "_rels", filename + ".rels")


def _source_for_rels(name):
    if name == "_rels/.rels":
        return ""
    marker = "/_rels/"
    if marker not in name or not name.endswith(".rels"):
        return None
    directory, leaf = name.rsplit(marker, 1)
    return posixpath.join(directory, leaf[:-5])


def _resolve_target(source, target):
    if target.startswith("/"):
        return unquote(target.lstrip("/"))
    return unquote(posixpath.normpath(
        posixpath.join(posixpath.dirname(source), target)))


def _read_xml(zf, name, errors, label):
    try:
        return ET.fromstring(zf.read(name))
    except (KeyError, ET.ParseError, OSError) as exc:
        errors.append("%s is missing or invalid XML: %s" % (label, exc))
        return None


def _is_internal(rel):
    return rel["mode"].lower() != "external"


def validate_package(path):
    """Validate package references needed by ``BlockImporter``.

    The return value is stable for callers: ``valid``, ``errors``,
    ``warnings``, and ``stats`` are always present.
    """
    errors, warnings = [], []
    stats = Counter()
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        return {"valid": False, "errors": ["invalid ZIP: %s" % exc],
                "warnings": [], "stats": dict(stats)}

    with zf:
        bad_member = zf.testzip()
        if bad_member:
            errors.append("ZIP CRC failure: %s" % bad_member)
        names = set(zf.namelist())
        stats["package_parts"] = len(names)
        for required in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
            if required not in names:
                errors.append("required package part is missing: %s" % required)

        xml_roots = {}
        for name in sorted(n for n in names if n.endswith(".xml")):
            root = _read_xml(zf, name, errors, name)
            if root is not None:
                xml_roots[name] = root
        stats["xml_parts"] = len(xml_roots)

        rels_by_source = {}
        for name in sorted(n for n in names if n.endswith(".rels")):
            source = _source_for_rels(name)
            if source is None:
                warnings.append("unrecognised relationship part path: %s" % name)
                continue
            if source and source not in names:
                errors.append("relationship owner does not exist: %s" % source)
            root = _read_xml(zf, name, errors, name)
            if root is None:
                continue
            rels = {}
            for rel in root.findall("{%s}Relationship" % PKG_REL_NS):
                rid = rel.get("Id")
                target = rel.get("Target")
                if not rid or target is None:
                    errors.append("malformed relationship in %s" % name)
                    continue
                if rid in rels:
                    errors.append("duplicate relationship ID %s in %s" % (rid, name))
                    continue
                data = {"target": target, "type": rel.get("Type", ""),
                        "mode": rel.get("TargetMode", "Internal")}
                rels[rid] = data
                stats["relationships"] += 1
                if _is_internal(data):
                    resolved = _resolve_target(source, target)
                    data["resolved"] = resolved
                    if resolved not in names:
                        errors.append("dangling internal relationship %s:%s -> %s" %
                                      (source or "package", rid, resolved))
            rels_by_source[source] = rels

        # All Office relationship attributes in every XML part must resolve in
        # the matching owning part's relationship collection.
        for part, root in xml_roots.items():
            rels = rels_by_source.get(part, {})
            for el in root.iter():
                for attr, rid in el.attrib.items():
                    if attr.startswith("{%s}" % R_NS) and rid:
                        stats["relationship_references"] += 1
                        if rid not in rels:
                            errors.append("dangling relationship reference %s in %s" %
                                          (rid, part))

        # Numbering definitions and uses. numId=0 is Word's explicit no-list.
        numbering = xml_roots.get("word/numbering.xml")
        num_ids, abstract_ids = set(), set()
        if numbering is not None:
            num_ids = {e.get("{%s}numId" % W_NS) for e in
                       numbering.findall("{%s}num" % W_NS)}
            abstract_ids = {e.get("{%s}abstractNumId" % W_NS) for e in
                            numbering.findall("{%s}abstractNum" % W_NS)}
            for num in numbering.findall("{%s}num" % W_NS):
                abstract = num.find("{%s}abstractNumId" % W_NS)
                if abstract is not None and abstract.get("{%s}val" % W_NS) not in abstract_ids:
                    errors.append("numbering numId %s references missing abstractNumId %s" %
                                  (num.get("{%s}numId" % W_NS),
                                   abstract.get("{%s}val" % W_NS)))
        for part, root in xml_roots.items():
            for el in root.iter("{%s}numId" % W_NS):
                value = el.get("{%s}val" % W_NS)
                stats["num_references"] += 1
                if value not in (None, "0") and value not in num_ids:
                    errors.append("numId %s in %s has no numbering definition" % (value, part))

        # Styles used by copied content (and story parts) need definitions.
        styles_root = xml_roots.get("word/styles.xml")
        style_ids = set()
        if styles_root is not None:
            style_ids = {e.get("{%s}styleId" % W_NS) for e in
                         styles_root.findall("{%s}style" % W_NS)}
        style_tags = ("pStyle", "rStyle", "tblStyle")
        for part, root in xml_roots.items():
            for local in style_tags:
                for el in root.iter("{%s}%s" % (W_NS, local)):
                    style = el.get("{%s}val" % W_NS)
                    if not style:
                        continue
                    stats["style_references"] += 1
                    if style not in style_ids and style not in _BUILTIN_STYLES:
                        errors.append("style %s in %s is not defined" % (style, part))

        # Word expects unique drawing IDs. Check the relevant IDs package-wide,
        # including headers, footers, comments, and copied document content.
        for tag, key in (("{%s}docPr" % WP_NS, "docPr_ids"),
                         ("{%s}cNvPr" % PIC_NS, "picture_ids")):
            seen = {}
            for part, root in xml_roots.items():
                for el in root.iter(tag):
                    ident = el.get("id")
                    stats[key] += 1
                    if not ident:
                        errors.append("drawing object without id in %s" % part)
                    elif ident in seen:
                        errors.append("duplicate drawing id %s in %s and %s" %
                                      (ident, seen[ident], part))
                    else:
                        seen[ident] = part

        # Explicit image and OLE checks make failure reports actionable even
        # though the generic relationship walk above already catches dangling
        # rIds. OLE targets should be an actual embedding package part.
        for part, root in xml_roots.items():
            rels = rels_by_source.get(part, {})

            def _check_image_reference(rid, label):
                rel = rels.get(rid)
                if rel is None:
                    # The generic relationship-reference pass already emits
                    # the missing-rId error.
                    return
                if "image" not in rel["type"].lower():
                    errors.append("%s %s in %s is not an image relationship" %
                                  (label, rid, part))
                    return
                if _is_internal(rel):
                    target = rel.get("resolved", "").lower()
                    if not target or "/media/" not in ("/" + target):
                        errors.append("%s %s in %s does not target a media part" %
                                      (label, rid, part))
                    else:
                        stats["image_media_targets"] += 1
                else:
                    stats["external_image_links"] += 1

            for blip in root.iter("{%s}blip" % A_NS):
                for attr in ("{%s}embed" % R_NS, "{%s}link" % R_NS):
                    rid = blip.get(attr)
                    if rid:
                        stats["drawing_image_references"] += 1
                        _check_image_reference(rid, "DrawingML image reference")
            for image in root.iter("{urn:schemas-microsoft-com:vml}imagedata"):
                rid = image.get("{%s}id" % R_NS)
                if rid:
                    stats["vml_image_references"] += 1
                    _check_image_reference(rid, "VML image reference")
            for ole in root.iter("{%s}OLEObject" % O_NS):
                stats["ole_references"] += 1
                rid = ole.get("{%s}id" % R_NS)
                rel = rels.get(rid) if rid else None
                if rel is None:
                    errors.append("OLE object in %s has no relationship" % part)
                elif "oleobject" not in rel["type"].lower():
                    errors.append("OLE object relationship %s in %s has an unexpected type" %
                                  (rid, part))
                elif _is_internal(rel):
                    target = rel.get("resolved")
                    if not target or target not in names:
                        errors.append("OLE relationship %s in %s has no embedding target" % (rid, part))
                    elif "/embeddings/" not in ("/" + target.lower()):
                        errors.append("OLE relationship %s in %s does not target an embedding part" %
                                      (rid, part))
                    else:
                        stats["embedding_parts"] += 1
                else:
                    warnings.append("linked OLE object %s in %s has no embedded binary" %
                                    (rid, part))

    stats["errors"] = len(errors)
    stats["warnings"] = len(warnings)
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "stats": dict(stats)}

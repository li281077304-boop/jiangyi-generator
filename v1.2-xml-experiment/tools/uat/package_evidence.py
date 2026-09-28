# -*- coding: utf-8 -*-
"""Read-only evidence collection for the v1.2 XML engine UAT.

The functions here inspect OPC/OOXML structures only.  They never save a
``Document`` or modify a source package.  A real Word/MathType rendering UAT
is still required: a dummy OLE binary can prove relationship preservation but
cannot prove MathType rendering.
"""
from __future__ import annotations

import hashlib
import os
import zipfile
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
O_NS = "urn:schemas-microsoft-com:office:office"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

W = "{%s}" % W_NS
R = "{%s}" % R_NS
A = "{%s}" % A_NS
V = "{%s}" % V_NS
O = "{%s}" % O_NS


def _xml_root(zf, name):
    try:
        return ET.fromstring(zf.read(name))
    except (KeyError, ET.ParseError):
        return None


def _relationship_count(zf):
    """Count declared relationships in every valid relationship part."""
    count = 0
    for name in zf.namelist():
        if not name.endswith(".rels"):
            continue
        root = _xml_root(zf, name)
        if root is not None:
            count += len(root.findall("{%s}Relationship" % PKG_REL_NS))
    return count


def _style_references(elements):
    refs = set()
    for element in elements:
        for local in ("pStyle", "rStyle", "tblStyle"):
            for style in element.iter(W + local):
                value = style.get(W + "val")
                if value:
                    refs.add(value)
    return sorted(refs)


def _numbering_references(elements):
    refs = set()
    for element in elements:
        for num_id in element.iter(W + "numId"):
            value = num_id.get(W + "val")
            if value is not None:
                refs.add(value)
    return sorted(refs, key=lambda value: (not value.isdigit(), value))


def _element_counts(elements):
    """Return counts for content references in an iterable of XML roots."""
    paragraphs = tables = image_references = vml_image_references = 0
    ole_references = ole_preview_image_references = 0
    for element in elements:
        paragraphs += sum(1 for _ in element.iter(W + "p"))
        tables += sum(1 for _ in element.iter(W + "tbl"))
        for blip in element.iter(A + "blip"):
            image_references += int(bool(blip.get(R + "embed")))
            image_references += int(bool(blip.get(R + "link")))
        for image_data in element.iter(V + "imagedata"):
            vml_image_references += int(bool(image_data.get(R + "id")))
            vml_image_references += int(bool(image_data.get(R + "link")))
        ole_references += sum(1 for _ in element.iter(O + "OLEObject"))
        for obj in element.iter(W + "object"):
            ole_preview_image_references += sum(
                1 for image_data in obj.iter(V + "imagedata")
                if image_data.get(R + "id") or image_data.get(R + "link"))
    return {
        "paragraphs": paragraphs,
        "tables": tables,
        "image_references": image_references,
        "vml_image_references": vml_image_references,
        "ole_references": ole_references,
        "ole_preview_image_references": ole_preview_image_references,
    }


def collect_package_evidence(docx_path):
    """Return a compact, read-only package inventory for a DOCX file.

    ``embedding_parts`` is a deterministically sorted list of dictionaries
    with ``partname`` and SHA256 ``sha256``.  Counts are references found in
    ``word/document.xml``; ``relationship_count`` is the total declared
    relationships across the package.
    """
    evidence = {
        "bytes": os.path.getsize(docx_path),
        "paragraphs": 0,
        "tables": 0,
        "image_references": 0,
        "vml_image_references": 0,
        "ole_references": 0,
        "ole_preview_image_references": 0,
        "embedding_parts": [],
        "relationship_count": 0,
        "style_references": [],
        "numbering_references": [],
    }
    with zipfile.ZipFile(docx_path) as zf:
        document = _xml_root(zf, "word/document.xml")
        if document is not None:
            elements = [document]
            evidence.update(_element_counts(elements))
            evidence["style_references"] = _style_references(elements)
            evidence["numbering_references"] = _numbering_references(elements)
        evidence["relationship_count"] = _relationship_count(zf)
        embeddings = []
        for name in zf.namelist():
            if (name.startswith("word/embeddings/") and not name.endswith("/") and
                    not name.endswith(".rels") and "/_rels/" not in name):
                embeddings.append({
                    "partname": "/" + name,
                    "sha256": hashlib.sha256(zf.read(name)).hexdigest(),
                })
        evidence["embedding_parts"] = sorted(embeddings, key=lambda item: item["partname"])
    return evidence


def _selected_elements(body_children, blocks):
    """Select block ranges using the XML engine's 1-based paragraph indexes."""
    paragraph_indexes = [index for index, element in enumerate(body_children)
                         if element.tag == W + "p"]
    selected = []
    for marker, start, end in blocks:
        if start < 1 or end < start or end > len(paragraph_indexes):
            raise ValueError("invalid block range for %s: %s..%s (available: %s)" %
                             (marker, start, end, len(paragraph_indexes)))
        selected.extend(body_children[paragraph_indexes[start - 1]:paragraph_indexes[end - 1] + 1])
    # Blocks may overlap after a caller's boundary adjustment. Keep document
    # order and count each body child once for evidence, without changing it.
    seen = set()
    return [element for element in selected
            if not (id(element) in seen or seen.add(id(element)))]


def _direct_relationship_references(elements, source_part):
    """Describe direct r:* references made by selected body XML."""
    refs = []
    seen = set()
    for element in elements:
        for descendant in element.iter():
            for attr, rid in descendant.attrib.items():
                if not attr.startswith(R) or not rid:
                    continue
                key = (rid, attr)
                if key in seen:
                    continue
                seen.add(key)
                relation = source_part.rels.get(rid)
                item = {"rId": rid, "attribute": attr, "resolved": relation is not None}
                if relation is not None:
                    item.update({"reltype": relation.reltype,
                                 "external": bool(relation.is_external),
                                 "target": relation.target_ref if relation.is_external
                                 else str(relation.target_part.partname)})
                refs.append(item)
    return sorted(refs, key=lambda item: (item["rId"], item["attribute"]))


def _reachable_relationship_count(direct_refs, source_part):
    """Count direct and recursively reachable package relationships."""
    direct_ids = {item["rId"] for item in direct_refs if item["resolved"]}
    seen_parts = set()
    seen_relations = set()

    def walk(part, relation_ids=None):
        if relation_ids is None:
            relations = list(part.rels.values())
        else:
            relations = [part.rels[rid] for rid in relation_ids if rid in part.rels]
        for relation in relations:
            relation_key = (str(part.partname), relation.rId)
            if relation_key in seen_relations:
                continue
            seen_relations.add(relation_key)
            if not relation.is_external and id(relation.target_part) not in seen_parts:
                seen_parts.add(id(relation.target_part))
                walk(relation.target_part)

    walk(source_part, direct_ids)
    return len(seen_relations)


def _reachable_embedding_parts(direct_refs, source_part):
    """Return unique embedding hashes reachable from selected relationships."""
    result = {}
    visited = set()

    def walk(part, relation_ids=None):
        if relation_ids is None:
            relations = list(part.rels.values())
        else:
            relations = [part.rels[rid] for rid in relation_ids if rid in part.rels]
        for relation in relations:
            if relation.is_external:
                continue
            target = relation.target_part
            name = str(target.partname)
            if name.startswith("/word/embeddings/"):
                result[name] = hashlib.sha256(target.blob).hexdigest()
            if id(target) not in visited:
                visited.add(id(target))
                walk(target)

    walk(source_part, {item["rId"] for item in direct_refs if item["resolved"]})
    return [{"partname": name, "sha256": result[name]} for name in sorted(result)]


def collect_selected_block_evidence(source_doc, body_children, blocks):
    """Return evidence limited to selected XML-engine source body blocks.

    The result contains paragraph/table and content-reference counts,
    ``style_references``, ``numbering_references``, direct
    ``relationship_references``, recursively reachable ``relationship_count``,
    and unique reachable ``embedding_parts`` hashes.  The source document is
    only traversed; no XML is altered.
    """
    selected = _selected_elements(body_children, blocks)
    direct_refs = _direct_relationship_references(selected, source_doc.part)
    evidence = _element_counts(selected)
    evidence.update({
        "body_blocks": len(selected),
        "style_references": _style_references(selected),
        "numbering_references": _numbering_references(selected),
        "relationship_references": direct_refs,
        "relationship_count": _reachable_relationship_count(direct_refs, source_doc.part),
        "embedding_parts": _reachable_embedding_parts(direct_refs, source_doc.part),
    })
    return evidence

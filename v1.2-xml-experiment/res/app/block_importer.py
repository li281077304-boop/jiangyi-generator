# -*- coding: utf-8 -*-
"""Copy selected Word body blocks into another python-docx document.

This module deliberately has a narrow interface: it imports a sequence of
``w:p``/``w:tbl`` XML elements, rather than presenting a document-composition
API. Adapted from docxcompose (MIT), Copyright (c) 2019 4teamwork AG:
selected relationship, style, numbering, and ID migration algorithms are
scoped to the body blocks imported here. This is not a copy of its Composer
API or implementation. The required license notice is in
``../../THIRD_PARTY_NOTICES.md`` and ``../../LICENSES/docxcompose-MIT.txt``.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Iterable

from lxml import etree
from docx.opc.packuri import PackURI
from docx.opc.part import Part


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
V_NS = "urn:schemas-microsoft-com:vml"
O_NS = "urn:schemas-microsoft-com:office:office"

W = "{%s}" % W_NS
R = "{%s}" % R_NS
WP = "{%s}" % WP_NS
PIC = "{%s}" % PIC_NS


class BlockImporter:
    """Import body elements and their reachable OPC dependencies.

    ``stats`` and ``unsupported`` are cumulative for the lifetime of an
    importer.  ``import_blocks`` returns snapshots with these exact keys::

        {"stats": {...}, "unsupported": [{"code": ..., ...}, ...]}

    An unsupported item is never silently ignored.  Callers should treat a
    non-empty list as a failed production import unless they have an explicit
    policy for the reported code.
    """

    def __init__(self, source_doc, destination_doc):
        self.source_doc = source_doc
        self.destination_doc = destination_doc
        self.source_part = source_doc.part
        self.destination_part = destination_doc.part
        self._part_map = {}
        self._style_map = {}
        self._num_map = {}
        self._abstract_num_map = {}
        self._bookmark_map = {}
        self._bookmark_name_map = {}
        self._parsed_destination_parts = {}
        self.stats = Counter()
        self.unsupported = []
        self._normalize_destination_ids(
            WP + "docPr", "destination_docPr_ids_normalized")
        self._normalize_destination_ids(
            PIC + "cNvPr", "destination_picture_ids_normalized")

    def import_blocks(self, elements: Iterable):
        """Return deep-copied body blocks with package dependencies imported."""
        cloned = [copy.deepcopy(el) for el in elements]
        self._remove_section_properties(cloned)
        self._migrate_numbering(cloned)
        self._migrate_styles(cloned)
        self._migrate_relationship_references(cloned)
        self._remap_xml_ids(cloned)
        self.stats["blocks_imported"] += len(cloned)
        return cloned, self.report()

    def report(self):
        return {"stats": dict(sorted(self.stats.items())),
                "unsupported": list(self.unsupported)}

    # ----- errors / unsupported -------------------------------------------------

    def _unsupported(self, code, **detail):
        item = {"code": code, **detail}
        if item not in self.unsupported:
            self.unsupported.append(item)
        self.stats["unsupported"] += 1

    # ----- section properties ---------------------------------------------------

    def _remove_section_properties(self, elements):
        kept = []
        for el in elements:
            if el.tag == W + "sectPr":
                self.stats["source_sectPr_removed"] += 1
                continue
            for sect_pr in list(el.iter(W + "sectPr")):
                parent = sect_pr.getparent()
                if parent is not None:
                    parent.remove(sect_pr)
                    self.stats["source_sectPr_removed"] += 1
            kept.append(el)
        elements[:] = kept

    # ----- relationship and part migration -------------------------------------

    def _migrate_relationship_references(self, elements):
        copied_bookmark_names = {b.get(W + "name") for root in elements
                                 for b in root.iter(W + "bookmarkStart") if b.get(W + "name")}
        source_bookmark_names = {b.get(W + "name") for b in self.source_doc.element.body.iter(W + "bookmarkStart")
                                 if b.get(W + "name")}
        for root in elements:
            for element in root.iter():
                if element.tag in (W + "footnoteReference", W + "endnoteReference", W + "commentReference"):
                    self._unsupported("unsupported_nonrelationship_reference", element=element.tag,
                                      reference_id=element.get(W + "id"))
                elif element.tag in (W + "commentRangeStart", W + "commentRangeEnd"):
                    self._unsupported("unsupported_comment_range", element=element.tag,
                                      reference_id=element.get(W + "id"))
                elif element.tag == W + "customXml":
                    self._unsupported("unsupported_custom_xml_wrapper")
                elif element.tag == W + "dataBinding":
                    self._unsupported("unsupported_custom_xml_data_binding",
                                      store_item_id=element.get("{%s}storeItemID" % W_NS))
                if element.tag == W + "hyperlink":
                    anchor = element.get(W + "anchor")
                    if anchor in source_bookmark_names and anchor not in copied_bookmark_names:
                        self._unsupported("unresolved_hyperlink_anchor", anchor=anchor)
                for attr, old_rid in list(element.attrib.items()):
                    if not attr.startswith(R) or not old_rid:
                        continue
                    if old_rid not in self.source_part.rels:
                        self._unsupported("missing_relationship", rId=old_rid,
                                          element=element.tag, attribute=attr)
                        continue
                    rel = self.source_part.rels[old_rid]
                    if rel.is_external:
                        new_rid = self.destination_part.relate_to(
                            rel.target_ref, rel.reltype, is_external=True)
                        self.stats["external_relationships_copied"] += 1
                    else:
                        try:
                            target = self._copy_part(rel.target_part)
                            new_rid = self.destination_part.relate_to(target, rel.reltype)
                        except Exception as exc:  # retain a structured failure, not a broken claim
                            self._unsupported("part_copy_failed", rId=old_rid,
                                              reltype=rel.reltype, error=str(exc))
                            continue
                    element.set(attr, new_rid)
                    self.stats["relationship_references_remapped"] += 1
                    self._count_special_relationship(element, rel)

    def _copy_part(self, source_part):
        """Copy an OPC part and recursively reproduce its relationship graph."""
        if source_part in self._part_map:
            return self._part_map[source_part]

        partname = self._destination_partname(source_part)
        copied = Part(partname, source_part.content_type, source_part.blob,
                      self.destination_part.package)
        # Install before recursion: relationship graphs can contain cycles.
        self._part_map[source_part] = copied
        self.stats["package_parts_copied"] += 1

        for rel in source_part.rels.values():
            try:
                if rel.is_external:
                    copied.load_rel(rel.reltype, rel.target_ref, rel.rId, is_external=True)
                    self.stats["recursive_external_relationships_copied"] += 1
                else:
                    copied_target = self._copy_part(rel.target_part)
                    copied.load_rel(rel.reltype, copied_target, rel.rId)
                    self.stats["recursive_relationships_copied"] += 1
            except Exception as exc:
                self._unsupported("recursive_relationship_copy_failed",
                                  source_part=str(source_part.partname), rId=rel.rId,
                                  reltype=rel.reltype, error=str(exc))
        return copied

    def _destination_partname(self, source_part):
        existing = {part.partname for part in self.destination_part.package.parts}
        source_name = source_part.partname
        if source_name not in existing:
            return PackURI(str(source_name))
        stem, dot, suffix = str(source_name).rpartition(".")
        # ``next_partname`` accepts exactly one %d token and guarantees no clash
        # with all currently reachable destination parts.
        template = (stem + "-imported%d." + suffix) if dot else (str(source_name) + "-imported%d")
        partname = self.destination_part.package.next_partname(template)
        self.stats["part_name_collisions_remapped"] += 1
        return partname

    def _count_special_relationship(self, element, rel):
        reltype = rel.reltype.lower()
        target_name = "" if rel.is_external else str(rel.target_part.partname).lower()
        if "oleobject" in reltype or "/embeddings/" in target_name or element.tag == "{%s}OLEObject" % O_NS:
            self.stats["ole_references_copied"] += 1
            if "/embeddings/" in target_name:
                self.stats["embedding_parts_copied"] += 1
        if "image" in reltype:
            self.stats["image_relationships_copied"] += 1
            if element.tag == "{%s}imagedata" % V_NS:
                self.stats["vml_image_relationships_copied"] += 1
                self.stats["ole_preview_relationships_copied"] += 1
        if "hyperlink" in reltype:
            self.stats["hyperlinks_copied"] += 1

    # ----- styles ---------------------------------------------------------------

    def _migrate_styles(self, elements):
        style_ids = set()
        for root in elements:
            for el in root.iter():
                if el.tag in (W + "pStyle", W + "rStyle", W + "tblStyle"):
                    style_id = el.get(W + "val")
                    if style_id:
                        style_ids.add(style_id)
        for style_id in sorted(style_ids):
            self._copy_style(style_id)
        for root in elements:
            for el in root.iter():
                if el.tag in (W + "pStyle", W + "rStyle", W + "tblStyle"):
                    old = el.get(W + "val")
                    if old in self._style_map:
                        el.set(W + "val", self._style_map[old])

    def _copy_style(self, style_id):
        if style_id in self._style_map:
            return self._style_map[style_id]
        src_style = self._find_style(self.source_doc.part._styles_part.element, style_id)
        if src_style is None:
            self._unsupported("missing_source_style", style_id=style_id)
            return
        dest_styles = self.destination_doc.part._styles_part.element
        dest_style = self._find_style(dest_styles, style_id)
        target_id = style_id
        if dest_style is not None:
            # Word's built-ins regularly occur in both documents.  A different
            # explicit definition must keep the template's definition and use a
            # unique imported name in copied blocks.
            if self._normalized_xml(dest_style) != self._normalized_xml(src_style):
                target_id = self._next_style_id(dest_styles, style_id)
                self.stats["style_id_collisions_remapped"] += 1
            else:
                self._style_map[style_id] = style_id
                return

        self._style_map[style_id] = target_id  # break cyclic basedOn/link graphs
        clone = copy.deepcopy(src_style)
        clone.set(W + "styleId", target_id)
        for child in clone.iter():
            if child.tag in (W + "basedOn", W + "next", W + "link"):
                dependency = child.get(W + "val")
                if dependency:
                    child.set(W + "val", self._copy_style(dependency) or dependency)
            elif child.tag == W + "numId":
                value = child.get(W + "val")
                if value and value != "0":
                    new_num = self._copy_num(value)
                    if new_num is not None:
                        child.set(W + "val", str(new_num))
        dest_styles.append(clone)
        self.stats["styles_copied"] += 1
        return target_id

    @staticmethod
    def _find_style(styles_element, style_id):
        for style in styles_element.findall(W + "style"):
            if style.get(W + "styleId") == style_id:
                return style
        return None

    @staticmethod
    def _normalized_xml(element):
        return etree.tostring(element, method="c14n", with_comments=False)

    @staticmethod
    def _next_style_id(styles_element, style_id):
        existing = {style.get(W + "styleId") for style in styles_element.findall(W + "style")}
        suffix = 1
        candidate = "%s_imported%s" % (style_id, suffix)
        while candidate in existing:
            suffix += 1
            candidate = "%s_imported%s" % (style_id, suffix)
        return candidate

    # ----- numbering ------------------------------------------------------------

    def _migrate_numbering(self, elements):
        for root in elements:
            for num_id in root.iter(W + "numId"):
                old = num_id.get(W + "val")
                if not old or old == "0":
                    continue
                new = self._copy_num(old)
                if new is not None:
                    num_id.set(W + "val", str(new))

    def _copy_num(self, old_num_id):
        if old_num_id in self._num_map:
            return self._num_map[old_num_id]
        src_root = self.source_doc.part.numbering_part.element
        dest_root = self.destination_doc.part.numbering_part.element
        src_num = self._find_by_val(src_root, W + "num", W + "numId", old_num_id)
        if src_num is None:
            self._unsupported("missing_source_numbering", num_id=old_num_id)
            return None
        abstract_ref = src_num.find(W + "abstractNumId")
        if abstract_ref is None or abstract_ref.get(W + "val") is None:
            self._unsupported("invalid_source_numbering", num_id=old_num_id)
            return None
        new_num = self._next_numeric_id(dest_root, W + "num", W + "numId")
        self._num_map[old_num_id] = new_num  # supports style -> num -> style cycles
        new_abstract = self._copy_abstract_num(abstract_ref.get(W + "val"))
        if new_abstract is None:
            del self._num_map[old_num_id]
            return None
        clone = copy.deepcopy(src_num)
        clone.set(W + "numId", str(new_num))
        clone.find(W + "abstractNumId").set(W + "val", str(new_abstract))
        self._insert_numbering_num(dest_root, clone)
        self.stats["numbering_nums_copied"] += 1
        return new_num

    def _copy_abstract_num(self, old_abstract_id):
        if old_abstract_id in self._abstract_num_map:
            return self._abstract_num_map[old_abstract_id]
        src_root = self.source_doc.part.numbering_part.element
        dest_root = self.destination_doc.part.numbering_part.element
        src_abstract = self._find_by_val(src_root, W + "abstractNum", W + "abstractNumId", old_abstract_id)
        if src_abstract is None:
            self._unsupported("missing_source_abstract_numbering", abstract_num_id=old_abstract_id)
            return None
        new_id = self._next_numeric_id(dest_root, W + "abstractNum", W + "abstractNumId")
        self._abstract_num_map[old_abstract_id] = new_id
        clone = copy.deepcopy(src_abstract)
        clone.set(W + "abstractNumId", str(new_id))
        # Numbering definitions can refer to paragraph/number styles.  Their
        # style dependencies must exist before the abstract definition lands.
        for reference in clone.iter():
            if reference.tag in (W + "pStyle", W + "numStyleLink"):
                old_style = reference.get(W + "val")
                if old_style:
                    reference.set(W + "val", self._copy_style(old_style) or old_style)
        self._insert_abstract_num(dest_root, clone)
        self.stats["numbering_abstracts_copied"] += 1
        return new_id

    @staticmethod
    def _find_by_val(parent, tag, attr, value):
        return next((el for el in parent.findall(tag) if el.get(attr) == str(value)), None)

    @staticmethod
    def _next_numeric_id(parent, tag, attr):
        values = [int(el.get(attr)) for el in parent.findall(tag)
                  if (el.get(attr) or "").isdigit()]
        return max(values, default=0) + 1

    @staticmethod
    def _insert_abstract_num(root, abstract_num):
        """OOXML requires abstractNum definitions before the first w:num."""
        index = next((i for i, child in enumerate(root) if child.tag == W + "num"), len(root))
        root.insert(index, abstract_num)

    @staticmethod
    def _insert_numbering_num(root, num):
        """Keep w:num in its schema sequence, before numIdMacAtCleanup."""
        index = next((i for i, child in enumerate(root) if child.tag == W + "numIdMacAtCleanup"), len(root))
        root.insert(index, num)

    # ----- document-local XML ids ----------------------------------------------

    def _remap_xml_ids(self, elements):
        self._remap_bookmarks(elements)
        self._remap_numeric_xml_id(elements, WP + "docPr", "drawing_docPr_ids_remapped")
        self._remap_numeric_xml_id(elements, PIC + "cNvPr", "picture_cNvPr_ids_remapped")

    def _remap_bookmarks(self, elements):
        used_ids = {el.get(W + "id") for el in
                    self._destination_package_elements(W + "bookmarkStart")}
        used_names = {el.get(W + "name") for el in
                      self._destination_package_elements(W + "bookmarkStart")}
        next_id = max((int(value) for value in used_ids if (value or "").isdigit()), default=0) + 1
        starts = set()
        ends = set()
        for root in elements:
            for bookmark in root.iter(W + "bookmarkStart"):
                old = bookmark.get(W + "id")
                if old is None:
                    self._unsupported("bookmark_without_id")
                    continue
                starts.add(old)
                new = self._bookmark_map.get(old)
                if new is None:
                    new = old if old not in used_ids else str(next_id)
                    if new != old:
                        next_id += 1
                        self.stats["bookmark_ids_remapped"] += 1
                    self._bookmark_map[old] = new
                bookmark.set(W + "id", new)
                used_ids.add(new)
                name = bookmark.get(W + "name")
                if name and name in used_names:
                    suffix = 1
                    new_name = "%s_imported%s" % (name, suffix)
                    while new_name in used_names:
                        suffix += 1
                        new_name = "%s_imported%s" % (name, suffix)
                    bookmark.set(W + "name", new_name)
                    self._bookmark_name_map[name] = new_name
                    self.stats["bookmark_names_remapped"] += 1
                    used_names.add(new_name)
                elif name:
                    used_names.add(name)
            for bookmark_end in root.iter(W + "bookmarkEnd"):
                old = bookmark_end.get(W + "id")
                if old is not None:
                    ends.add(old)
                if old in self._bookmark_map:
                    bookmark_end.set(W + "id", self._bookmark_map[old])
        # A partial bookmark range cannot be made valid by changing only this
        # selected body interval.  Report it explicitly instead of shipping a
        # silently broken bookmark.
        for old in sorted(starts - ends):
            self._unsupported("unmatched_bookmark_start", bookmark_id=old)
        for old in sorted(ends - starts):
            self._unsupported("unmatched_bookmark_end", bookmark_id=old)
        for root in elements:
            for hyperlink in root.iter(W + "hyperlink"):
                anchor = hyperlink.get(W + "anchor")
                if anchor in self._bookmark_name_map:
                    hyperlink.set(W + "anchor", self._bookmark_name_map[anchor])

    def _remap_numeric_xml_id(self, elements, tag, stat_key):
        used = {el.get("id") for el in self._destination_package_elements(tag)}
        next_id = max((int(value) for value in used if (value or "").isdigit()), default=0) + 1
        for root in elements:
            for el in root.iter(tag):
                old = el.get("id")
                if old is None or not old.isdigit():
                    self._unsupported("invalid_xml_id", element=tag, value=old)
                    continue
                new = old
                if new in used:
                    new = str(next_id)
                    next_id += 1
                    self.stats[stat_key] += 1
                el.set("id", new)
                used.add(new)

    def _normalize_destination_ids(self, tag, stat_key):
        """Repair pre-existing collisions across template body/story parts."""
        elements = self._destination_package_elements(tag)
        existing = [el.get("id") for el in elements]
        used = set()
        next_id = max((int(value) for value in existing
                       if value is not None and value.isdigit()), default=0) + 1
        for el in elements:
            value = el.get("id")
            if value is None or not value.isdigit():
                self._unsupported("invalid_destination_xml_id", element=tag, value=value)
                continue
            if value in used:
                value = str(next_id)
                next_id += 1
                el.set("id", value)
                self.stats[stat_key] += 1
            used.add(value)
        self._persist_parsed_destination_parts()

    def _persist_parsed_destination_parts(self):
        """Save ID changes made to XML parts without a python-docx part class."""
        for root, part in self._parsed_destination_parts.items():
            part._blob = etree.tostring(root, encoding="UTF-8", xml_declaration=True,
                                        standalone=True)
        self._parsed_destination_parts.clear()

    def _destination_package_elements(self, tag):
        """Read existing IDs across body and XML story parts (headers/footers)."""
        roots = [self.destination_doc.element.body]
        document_partname = str(self.destination_part.partname)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        for part in self.destination_part.package.iter_parts():
            if str(part.partname) == document_partname or part.partname.ext != "xml":
                continue
            try:
                # Use the live part element when python-docx knows this story
                # type, so ID normalization persists into the saved package.
                root = part.element
            except (AttributeError, NotImplementedError, ValueError):
                try:
                    root = etree.fromstring(part.blob, parser=parser)
                except (etree.XMLSyntaxError, ValueError):
                    continue
                self._parsed_destination_parts[root] = part
            roots.append(root)
        return [element for root in roots for element in root.iter(tag)]

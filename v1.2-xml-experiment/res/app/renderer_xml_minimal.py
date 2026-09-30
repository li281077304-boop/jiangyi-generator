"""Minimal, fail-closed OOXML block projection and template insertion.

This is a B2 experiment only. It maps current StructDoc IDs to elements by
walking the same source document structure in lockstep. It never searches by
paragraph text or uses COM paragraph coordinates.

Supported payloads are whole body paragraphs, whole tables, and paragraph
spans that stay outside tables. Raw XML cloning preserves paragraph/run
formatting and OMML. Any relationship-bearing content, unrecognized node,
cross-table span, or required style/numbering dependency that the template
does not already provide is rejected. Relationship migration and package
integrity handling belong to later work.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import os
import tempfile
import zipfile

from lxml import etree

_APP = Path(__file__).resolve().parent
import sys
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from struct_doc import (  # noqa: E402
    W, W_P, W_TBL, W_TR, W_TC, W_SECTPR,
    read_struct_doc_bytes,
)
from struct_nodes import NodeIndex  # noqa: E402

_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_W_STYLE = "{%s}pStyle" % W
_W_RSTYLE = "{%s}rStyle" % W
_W_TBLSTYLE = "{%s}tblStyle" % W
_W_NUMID = "{%s}numId" % W
_REL_ATTR = "{%s}" % _R
_DOC = "word/document.xml"


class ProjectionError(ValueError):
    """The requested source content cannot be projected safely."""


@dataclass(frozen=True)
class BlockSpan:
    """A StructDoc leaf range or one atomic top-level table ID."""
    start: str
    end: str


@dataclass(frozen=True)
class TemplateTarget:
    """Insert before this zero-based direct child of template w:body."""
    body_child_index: int


@dataclass(frozen=True)
class RenderResult:
    output_path: str
    inserted_nodes: int


def render_minimal(source_doc: str, template_doc: str,
                   blocks: list[BlockSpan], output_path: str,
                   target: TemplateTarget) -> RenderResult:
    """Clone selected source OOXML blocks into an explicit template position.

    Source and template are read without modification. The destination is
    written atomically after all selected nodes pass capability checks.
    """
    src_path, tpl_path, out_path = map(Path, (source_doc, template_doc, output_path))
    if not src_path.is_file() or not tpl_path.is_file():
        raise FileNotFoundError("source and template must be existing DOCX files")
    if out_path.resolve() in (src_path.resolve(), tpl_path.resolve()):
        raise ProjectionError("output path must not alias the source or template")
    if not blocks:
        raise ProjectionError("at least one StructDoc block span is required")
    source_bytes = _read_source_bytes(src_path)
    with zipfile.ZipFile(io.BytesIO(source_bytes), "r") as src_zip, zipfile.ZipFile(tpl_path, "r") as tpl_zip:
        src_xml = _read_document(src_zip)
        tpl_xml = _read_document(tpl_zip)
        src_body = src_xml.find("{%s}body" % W)
        tpl_body = tpl_xml.find("{%s}body" % W)
        if src_body is None or tpl_body is None:
            raise ProjectionError("source or template is missing w:body")

        struct = read_struct_doc_bytes(source_bytes, name=str(src_path))
        index = NodeIndex(struct)
        node_map, table_ids, top_table_ids, table_leaf_ids = _map_structdoc_to_xml(src_body, struct)
        selected = _select_nodes(blocks, index, node_map, table_ids, top_table_ids,
                                 table_leaf_ids, struct)
        template_styles = _template_ids(tpl_zip)
        clones = []
        for node in selected:
            _validate_payload(node, template_styles)
            clones.append(etree.fromstring(etree.tostring(node)))

        insert_at = target.body_child_index
        body_children = list(tpl_body)
        section_tail = next((i for i, child in enumerate(body_children)
                             if child.tag == W_SECTPR), len(body_children))
        if insert_at < 0 or insert_at > section_tail:
            raise ProjectionError("template target is outside direct w:body children")
        for offset, clone in enumerate(clones):
            tpl_body.insert(insert_at + offset, clone)

        payloads = {name: tpl_zip.read(name) for name in tpl_zip.namelist()}
        payloads[_DOC] = etree.tostring(tpl_xml, xml_declaration=True,
                                         encoding="UTF-8", standalone=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".renderer-", suffix=".docx", dir=str(out_path.parent))
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
            with zipfile.ZipFile(tpl_path, "r") as tpl_zip:
                for info in tpl_zip.infolist():
                    output_zip.writestr(info, payloads[info.filename])
        os.replace(temp_name, out_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return RenderResult(str(out_path), len(clones))


def _read_source_bytes(path):
    """Read once so XML and StructDoc parsing share one immutable snapshot."""
    return path.read_bytes()


def _read_document(zf):
    try:
        return etree.fromstring(zf.read(_DOC), parser=etree.XMLParser(resolve_entities=False,
                                                                        no_network=True))
    except (KeyError, etree.XMLSyntaxError) as exc:
        raise ProjectionError("invalid DOCX main document part") from exc


def _map_structdoc_to_xml(body, doc):
    """Build ID -> exact element map through ordinal structural traversal."""
    mapping = {"body": body}
    table_ids = set()
    top_table_ids = set()
    table_leaf_ids = set()
    body_content = [(i, child) for i, child in enumerate(body)
                    if child.tag != W_SECTPR and child.tag not in (
                        "{%s}bookmarkStart" % W, "{%s}bookmarkEnd" % W)]
    if len(body_content) != len(doc.blocks):
        raise ProjectionError("StructDoc/body top-level block count mismatch")

    def add_table(block, table_el, table_id):
        if table_el.tag != W_TBL:
            raise ProjectionError("StructDoc table ordinal does not identify w:tbl")
        mapping[table_id] = table_el
        table_ids.add(table_id)
        rows = [child for child in table_el if child.tag == W_TR]
        model_rows = block.table.rows if block.table is not None else []
        if len(rows) != len(model_rows):
            raise ProjectionError("StructDoc/table row count mismatch at %s" % table_id)
        for r, (row_el, model_row) in enumerate(zip(rows, model_rows)):
            cells = [child for child in row_el if child.tag == W_TC]
            if len(cells) != len(model_row):
                raise ProjectionError("StructDoc/table cell count mismatch at %s.r%d" % (table_id, r))
            for c, (cell_el, model_cell) in enumerate(zip(cells, model_row)):
                cell_id = "%s.r%dc%d" % (table_id, r, c)
                mapping[cell_id] = cell_el
                content = [child for child in cell_el if child.tag in (W_P, W_TBL)]
                if len(content) != len(model_cell.blocks):
                    raise ProjectionError("StructDoc/cell block count mismatch at %s" % cell_id)
                for k, (child_el, child_block) in enumerate(zip(content, model_cell.blocks)):
                    child_id = "%s.n%d" % (cell_id, k)
                    add_block(child_block, child_el, child_id)
                    if child_block.kind == "paragraph":
                        table_leaf_ids.add(child_id)

    def add_block(block, element, node_id):
        mapping[node_id] = element
        if block.kind == "paragraph":
            if element.tag != W_P:
                raise ProjectionError("StructDoc paragraph ordinal does not identify w:p at %s" % node_id)
        elif block.kind == "table":
            add_table(block, element, node_id)
        else:
            raise ProjectionError("unknown StructDoc block kind at %s: %s" % (node_id, block.kind))

    for block, (body_idx, element) in zip(doc.blocks, body_content):
        if body_idx != block.body_idx:
            raise ProjectionError("StructDoc body index mismatch at b%d" % block.seq)
        add_block(block, element, "b%d" % block.seq)
        if block.kind == "table":
            top_table_ids.add("b%d" % block.seq)
    return mapping, table_ids, top_table_ids, table_leaf_ids


def _select_nodes(spans, index, mapping, table_ids, top_table_ids,
                  table_leaf_ids, struct_doc):
    selected = []
    top_level_kinds = [block.kind for block in struct_doc.blocks]
    for span in spans:
        start, end = index.resolve_ref(span.start), index.resolve_ref(span.end)
        if start is None or end is None:
            raise ProjectionError("span endpoints must be StructDoc IDs")
        if start == end and start in top_table_ids:
            selected.append(mapping[start])
            continue
        if start in table_ids or end in table_ids:
            raise ProjectionError("only a top-level bN table can be selected atomically")
        if start in table_leaf_ids or end in table_leaf_ids:
            raise ProjectionError("cell paragraph endpoints require the owning table as an atomic block")
        if start not in index.by_id or end not in index.by_id:
            raise ProjectionError("span endpoint is not a content node: %s..%s" % (start, end))
        a, b = index.order_of(start), index.order_of(end)
        if a is None or b is None or a > b:
            raise ProjectionError("span endpoints are reversed or unresolved")
        start_top = _top_level_body_id(start)
        end_top = _top_level_body_id(end)
        if start_top is None or end_top is None:
            raise ProjectionError("paragraph span endpoints must be top-level body paragraphs")
        if int(end_top[1:]) >= len(top_level_kinds) or int(start_top[1:]) >= len(top_level_kinds):
            raise ProjectionError("span endpoint is outside top-level StructDoc blocks")
        if any(kind == "table" for kind in top_level_kinds[int(start_top[1:]) + 1:int(end_top[1:])]):
            raise ProjectionError("paragraph span crosses a top-level table block")
        ids = index.order_ids[a:b + 1]
        if any(node_id in table_leaf_ids for node_id in ids):
            raise ProjectionError("paragraph span crosses table content")
        selected_tables = [node_id for node_id in ids if node_id in table_ids]
        if selected_tables:
            raise ProjectionError("paragraph span crosses table content: %s" % selected_tables[0])
        for node_id in ids:
            element = mapping.get(node_id)
            if element is None or element.tag != W_P:
                raise ProjectionError("span cannot map to a paragraph at %s" % node_id)
            selected.append(element)
    return selected


def _top_level_body_id(node_id):
    if not node_id.startswith("b"):
        return None
    base = node_id.split(".", 1)[0]
    return base if base[1:].isdigit() else None


def _template_ids(tpl_zip):
    ids = {"style": set(), "numbering": set()}
    if "word/styles.xml" in tpl_zip.namelist():
        root = etree.fromstring(tpl_zip.read("word/styles.xml"))
        ids["style"] = {el.get("{%s}styleId" % W) for el in root if el.get("{%s}styleId" % W)}
    if "word/numbering.xml" in tpl_zip.namelist():
        root = etree.fromstring(tpl_zip.read("word/numbering.xml"))
        ids["numbering"] = {el.get("{%s}numId" % W) for el in root
                             if el.tag == "{%s}num" % W and el.get("{%s}numId" % W)}
    return ids


def _validate_payload(element, template_ids):
    if element.tag not in (W_P, W_TBL):
        raise ProjectionError("only w:p and w:tbl payloads are supported")
    if any(name.startswith(_REL_ATTR) for node in element.iter() for name in node.attrib):
        raise ProjectionError("relationship-bearing payload requires package-part migration")
    package_scoped = {
        "bookmarkStart", "bookmarkEnd", "commentRangeStart", "commentRangeEnd",
        "commentReference", "footnoteReference", "endnoteReference",
        "permStart", "permEnd", "sdt", "customXml", "ins", "del",
        "moveFrom", "moveTo", "moveFromRangeStart", "moveFromRangeEnd",
        "moveToRangeStart", "moveToRangeEnd",
        "customXmlInsRangeStart", "customXmlInsRangeEnd", "customXmlDelRangeStart",
        "customXmlDelRangeEnd", "customXmlMoveFromRangeStart",
        "customXmlMoveFromRangeEnd", "customXmlMoveToRangeStart",
        "customXmlMoveToRangeEnd", "rPrChange", "pPrChange", "tblPrChange",
        "trPrChange", "tcPrChange", "sectPrChange",
        "cellIns", "cellDel", "cellMerge", "conflictIns", "conflictDel",
    }
    revision_markers = {
        "ins", "del", "moveFrom", "moveTo", "moveFromRangeStart",
        "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd",
        "customXmlInsRangeStart", "customXmlInsRangeEnd", "customXmlDelRangeStart",
        "customXmlDelRangeEnd", "customXmlMoveFromRangeStart",
        "customXmlMoveFromRangeEnd", "customXmlMoveToRangeStart",
        "customXmlMoveToRangeEnd", "cellIns", "cellDel", "cellMerge",
        "conflictIns", "conflictDel",
    }
    for node in element.iter():
        local_name = node.tag.split("}", 1)[1] if node.tag.startswith("{%s}" % W) else ""
        is_revision_change = bool(local_name) and local_name.endswith("Change")
        if local_name in package_scoped or is_revision_change:
            category = "tracked-change" if local_name in revision_markers or is_revision_change else "package-scoped"
            raise ProjectionError("unsupported %s construct: %s" % (category, local_name))
        if node.tag == "{%s}hyperlink" % W and "{%s}anchor" % W in node.attrib:
            raise ProjectionError("bookmark hyperlink anchor requires bookmark migration")
    style_tags = (_W_STYLE, _W_RSTYLE, _W_TBLSTYLE)
    for node in element.iter():
        if node.tag in style_tags:
            style_id = node.get("{%s}val" % W)
            if style_id and style_id not in template_ids["style"]:
                raise ProjectionError("template is missing referenced style: %s" % style_id)
        if node.tag == _W_NUMID:
            num_id = node.get("{%s}val" % W)
            if num_id and num_id not in template_ids["numbering"]:
                raise ProjectionError("template is missing referenced numbering definition: %s" % num_id)

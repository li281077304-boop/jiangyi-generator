# -*- coding: utf-8 -*-
"""
struct_doc.py —— Splitter V2 第一阶段：忠实结构读取（旁路新模块）

目标：把 Word 讲义完整读成一个稳定的内部文档模型（Document Model），
**不做任何知识/例题/练习/巩固判断**。本模块只负责"看见原稿"。

与旧管线的关系（旁路保证）：
  - 不 import、不修改 docutils / split_engine / xml_engine 的任何逻辑；
  - 不依赖 python-docx，仅用标准库 zipfile + ElementTree 直读 OOXML；
  - 旧 splitter 的输入（docutils.scan_paragraphs）与输出行为完全不受影响。

段落编号契约（与 xml_engine.fill_blocks 对齐，必须永远成立）：
  - 每个 body 直接子级 w:p 有 1-based 段落号 Block.pno；
  - w:tbl 不参与 pno 编号，但作为独立 Block 占据序列位置；
  - fill_blocks 按 pno 区间复制时会连同区间内表格一起复制，
    因此 (pno, seq) 双索引可以同时服务旧契约与未来重排。

两个位置索引（都不可省）：
  - seq     ：稠密块序号，0-based，等于 blocks 列表下标，**无空洞**。
              下游（gold 标注、分块区间、重排）一律用它，可以安全地当数组下标。
  - body_idx：原始 body 子元素下标。被跳过的元素（sectPr、bookmarkStart/End）
              仍会占用它的编号，因此可能不连续。用于需要回溯原始 XML 位置的场景。

丢失信息对照（docutils.scan_paragraphs 只返回 (序号, 文本, 含图)）：
  本模块额外保留：样式/大纲级别、字号（直接+样式推导）、加粗、编号列表
  （numId/ilvl/编号格式）、表格及单元格内容、图片（内嵌/浮动/尺寸/目标）、
  OLE 对象、OMML 公式计数、文本框内容、无法识别内容（sdt 等）原样保留。

明确不做（留给后续阶段）：
  - 知识/例题/练习/巩固 角色判断；
  - 标题层级推断（outlineLvl/字号层只是**原始字段**，不构建树）；
  - 编号实际序号求值（跨段落计数器，Stage 2 再议）；
  - 页眉页脚/批注/修订内容（本阶段只记存在性）。
"""
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------
# 命名空间
# ---------------------------------------------------------------
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
V = "urn:schemas-microsoft-com:vml"
O = "urn:schemas-microsoft-com:office:office"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

def _t(ns, tag):
    return "{%s}%s" % (ns, tag)

W_P, W_TBL, W_TR, W_TC = _t(W, "p"), _t(W, "tbl"), _t(W, "tr"), _t(W, "tc")
W_T, W_R, W_PPR = _t(W, "t"), _t(W, "r"), _t(W, "pPr")
W_SDT = _t(W, "sdt")
W_SECTPR = _t(W, "sectPr")
W_TXBX = _t(W, "txbxContent")


# ---------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------
@dataclass
class ImageRef:
    """一处图片引用。kind: inline(内嵌) / anchor(浮动锚定) / vml(旧式 VML)。"""
    kind: str
    rId: str
    target: str = ""          # 解析 rels 后的包内路径，如 word/media/image1.png
    cx: int = 0               # 显示尺寸（EMU，914400 = 1 英寸）
    cy: int = 0


@dataclass
class OleRef:
    """OLE 嵌入对象（MathType 等）。"""
    rId: str
    target: str = ""
    prog_id: str = ""


@dataclass
class NumInfo:
    """段落所属的 Word 编号列表（原始引用 + 已解析的格式定义）。"""
    num_id: int
    ilvl: int
    fmt: str = ""             # decimal / chineseCounting / bullet ...
    lvl_text: str = ""        # 如 "%1." / "%1、"


@dataclass
class Cell:
    """表格单元格。

    text 是直接子级段落文本的便捷拼接；**完整结构在 blocks**——
    单元格内的段落（含字号/加粗/编号/图片等全部特征）与嵌套表格
    都递归存为 Block，因为真实讲义存在「全文一张表」的排版
    （例如封面信息表套全部教学内容的机构讲义）。"""
    text: str
    n_paras: int = 0
    has_image: bool = False
    has_nested_table: bool = False
    blocks: List["Block"] = field(default_factory=list)


@dataclass
class TableBlock:
    """表格块：rows[r][c] = Cell。"""
    rows: List[List[Cell]] = field(default_factory=list)
    text: str = ""            # 全表扁平文本（| 分隔单元格，便于检索）

    @property
    def n_rows(self):
        return len(self.rows)

    @property
    def n_cols_max(self):
        return max((len(r) for r in self.rows), default=0)


@dataclass
class Block:
    """body 直接子级的一个内容单元（段落 / 表格 / 未识别块）。"""
    seq: int                        # 稠密块序号（0-based，== blocks 列表下标；无空洞）
    pno: Optional[int]              # 段落号（1-based，仅 w:p；与 fill_blocks 契约一致）
    kind: str                       # "paragraph" | "table" | "unknown"
    text: str                       # 段落文本 / 表格扁平文本 / 未知块文本
    body_idx: int = -1              # 原始 body 子元素下标（可能不连续：书签/分节符被跳过）
    # —— 段落原始特征（表格/未知块为默认值）——
    style_id: str = ""
    style_name: str = ""
    outline_lvl: Optional[int] = None      # 0-based，OOXML 原始值
    sz_direct: Optional[int] = None        # 直接格式最大字号（半磅）
    style_sz: Optional[int] = None         # 样式表推导字号（半磅）
    eff_sz: Optional[int] = None           # 生效字号 = direct 优先，否则样式
    bold: Optional[bool] = None            # 全部 run 加粗（直接格式或样式推导）
    num: Optional[NumInfo] = None          # 编号列表引用
    images: List[ImageRef] = field(default_factory=list)
    oles: List[OleRef] = field(default_factory=list)
    math_count: int = 0                    # OMML 公式个数
    textbox_texts: List[str] = field(default_factory=list)  # 文本框内容
    # —— 表格特征 ——
    table: Optional[TableBlock] = None
    # —— 其他 ——
    is_empty: bool = False
    note: str = ""                         # unknown 原因等

    @property
    def has_image(self):
        return bool(self.images)

    @property
    def has_math(self):
        return self.math_count > 0


@dataclass
class StructDoc:
    """一份讲义的结构视图。"""
    name: str
    blocks: List[Block] = field(default_factory=list)
    body_size: Optional[int] = None        # 正文字号（最常见 eff_sz，半磅）
    size_hist: Dict[int, int] = field(default_factory=dict)
    style_hist: Dict[str, int] = field(default_factory=dict)
    num_usage: Dict[int, int] = field(default_factory=dict)
    num_defs: Dict[int, Dict[int, Tuple[str, str]]] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)

    # —— 便捷访问 ——
    @property
    def paragraphs(self) -> List[Block]:
        return [b for b in self.blocks if b.kind == "paragraph"]

    @property
    def tables(self) -> List[Block]:
        return [b for b in self.blocks if b.kind == "table"]

    def by_pno(self, pno: int) -> Optional[Block]:
        for b in self.blocks:
            if b.pno == pno:
                return b
        return None

    def size_tiers(self) -> Dict[int, int]:
        """大于正文字号的字号分布（Stage 2 标题层的原始素材，本阶段只呈现）。"""
        if not self.body_size:
            return {}
        return {s: c for s, c in sorted(self.size_hist.items(), reverse=True)
                if s > self.body_size}


# ---------------------------------------------------------------
# XML 解析辅助
# ---------------------------------------------------------------
def _val(el, tag, attr="val"):
    child = el.find(_t(W, tag)) if el is not None else None
    return child.get(_t(W, attr)) if child is not None else None


def _onoff(el):
    """w:b / w:i 类开关：存在且未显式关闭即为 True。"""
    if el is None:
        return None
    v = el.get(_t(W, "val"))
    return v not in ("0", "false", "off", "none")


def _parse_rels(zf, name):
    """word/_rels/document.xml.rels → {rId: (target, type)}"""
    out = {}
    try:
        root = ET.fromstring(zf.read(name))
    except KeyError:
        return out
    for rel in root.iter(_t(PKG_REL, "Relationship")):
        rid = rel.get("Id")
        target = rel.get("Target") or ""
        if target and not target.startswith(("http", "/")):
            target = "word/" + target
        out[rid] = (target, rel.get("Type") or "")
    return out


def _parse_styles(zf):
    """styles.xml → (styles, default_style_id, doc_default_sz)

    styles: {styleId: {name, sz, bold, outline, based_on}}
    default_style_id: w:default="1" 的段落样式（通常是 Normal）。
    doc_default_sz: w:docDefaults 的字号（半磅），缺省段落的最终兜底。
    """
    out = {}
    default_id = ""
    doc_default_sz = None
    try:
        root = ET.fromstring(zf.read("word/styles.xml"))
    except KeyError:
        return out, default_id, doc_default_sz
    dd = root.find(_t(W, "docDefaults"))
    if dd is not None:
        sz = dd.find(".//" + _t(W, "sz"))
        if sz is not None:
            try:
                doc_default_sz = int(sz.get(_t(W, "val")))
            except (TypeError, ValueError):
                pass
    for st in root.iter(_t(W, "style")):
        sid = st.get(_t(W, "styleId")) or ""
        if not sid:
            continue
        if st.get(_t(W, "default")) in ("1", "true") and st.get(_t(W, "type")) == "paragraph":
            default_id = sid
        info = {"name": _val(st, "name") or "", "sz": None, "bold": None,
                "outline": None, "based_on": _val(st, "basedOn")}
        rpr = st.find(_t(W, "rPr"))
        if rpr is not None:
            sz = rpr.find(_t(W, "sz"))
            if sz is not None:
                try:
                    info["sz"] = int(sz.get(_t(W, "val")))
                except (TypeError, ValueError):
                    pass
            info["bold"] = _onoff(rpr.find(_t(W, "b")))
        ppr = st.find(_t(W, "pPr"))
        if ppr is not None:
            ol = ppr.find(_t(W, "outlineLvl"))
            if ol is not None:
                try:
                    info["outline"] = int(ol.get(_t(W, "val")))
                except (TypeError, ValueError):
                    pass
        out[sid] = info
    return out, default_id, doc_default_sz


def _parse_numbering(zf):
    """numbering.xml → {numId: {ilvl: (fmt, lvlText)}}"""
    out = {}
    try:
        root = ET.fromstring(zf.read("word/numbering.xml"))
    except KeyError:
        return out
    abstract = {}
    for an in root.iter(_t(W, "abstractNum")):
        aid = an.get(_t(W, "abstractNumId"))
        lvls = {}
        for lvl in an.iter(_t(W, "lvl")):
            try:
                ilvl = int(lvl.get(_t(W, "ilvl")))
            except (TypeError, ValueError):
                continue
            lvls[ilvl] = (_val(lvl, "numFmt") or "", _val(lvl, "lvlText") or "")
        abstract[aid] = lvls
    for num in root.iter(_t(W, "num")):
        try:
            nid = int(num.get(_t(W, "numId")))
        except (TypeError, ValueError):
            continue
        aid = _val(num, "abstractNumId")
        out[nid] = abstract.get(aid, {})
    return out


def _para_text_main(p_el):
    """段落主文本：所有 w:t，但排除文本框（txbxContent）内部内容。"""
    parts = []
    def walk(el):
        if el.tag == W_TXBX:
            return
        if el.tag == W_T:
            parts.append(el.text or "")
            return
        for ch in el:
            walk(ch)
    walk(p_el)
    return "".join(parts).strip()


def _textbox_texts(p_el):
    """段落内所有文本框的内容（每个文本框一条，内部段落用 \\n 连接）。

    mc:AlternateContent 会让同一内容同时出现在 Choice（drawing）和
    Fallback（VML）两个文本框里——这是渲染冗余而非两份内容，
    对完全相同的文本按段去重（不丢任何独特内容）。"""
    out = []
    for tb in p_el.iter(W_TXBX):
        lines = []
        for p in tb.iter(W_P):
            t = "".join(x.text or "" for x in p.iter(W_T)).strip()
            if t:
                lines.append(t)
        if lines:
            out.append("\n".join(lines))
    deduped = []
    for t in out:
        if t not in deduped:
            deduped.append(t)
    return deduped


def _para_images(p_el, rels):
    """段落内图片引用列表（drawing inline/anchor + VML pict）。"""
    imgs = []
    for dr in p_el.iter(_t(W, "drawing")):
        for kind_tag, kind in ((_t(WP, "inline"), "inline"), (_t(WP, "anchor"), "anchor")):
            for holder in dr.iter(kind_tag):
                cx = cy = 0
                ext = holder.find(_t(WP, "extent"))
                if ext is not None:
                    try:
                        cx, cy = int(ext.get("cx", 0)), int(ext.get("cy", 0))
                    except (TypeError, ValueError):
                        pass
                for blip in holder.iter(_t(A, "blip")):
                    rid = blip.get(_t(R, "embed")) or blip.get(_t(R, "link")) or ""
                    target = rels.get(rid, ("", ""))[0] if rid else ""
                    imgs.append(ImageRef(kind=kind, rId=rid, target=target, cx=cx, cy=cy))
    for pict in p_el.iter(_t(W, "pict")):
        for im in pict.iter(_t(V, "imagedata")):
            rid = im.get(_t(R, "id")) or ""
            target = rels.get(rid, ("", ""))[0] if rid else ""
            imgs.append(ImageRef(kind="vml", rId=rid, target=target))
    return imgs


def _para_oles(p_el, rels):
    """段落内 OLE 对象。"""
    out = []
    for ole in p_el.iter(_t(O, "OLEObject")):
        rid = ole.get(_t(R, "id")) or ""
        target = rels.get(rid, ("", ""))[0] if rid else ""
        out.append(OleRef(rId=rid, target=target, prog_id=ole.get("ProgID") or ""))
    return out


def _run_features(p_el):
    """(max_direct_sz, bold) —— 仅看含文本 run 的直接格式。

    bold 三态（继承语义）：
      True  = 全部含文本 run 显式加粗；
      False = 部分 run 显式加粗（混合）；
      None  = 没有 run 携带显式加粗信息（继承样式/默认，交由样式层兜底）。
    """
    max_sz = None
    total = 0
    b_on = 0
    for r in p_el.iter(W_R):
        # 跳过文本框内的 run
        if _inside_textbox(p_el, r):
            continue
        has_text = any((t.text or "").strip() for t in r.iter(W_T))
        if not has_text:
            continue
        total += 1
        rpr = r.find(_t(W, "rPr"))
        if rpr is not None:
            sz = rpr.find(_t(W, "sz"))
            if sz is not None:
                try:
                    v = int(sz.get(_t(W, "val")))
                    max_sz = v if max_sz is None else max(max_sz, v)
                except (TypeError, ValueError):
                    pass
            if _onoff(rpr.find(_t(W, "b"))):
                b_on += 1
    if total == 0:
        return max_sz, None
    bold = True if b_on == total else (False if b_on > 0 else None)
    return max_sz, bold


def _inside_textbox(p_el, r_el):
    """判断 run 是否位于文本框内（ElementTree 无 parent 指针，重新遍历）。"""
    for tb in p_el.iter(W_TXBX):
        for r in tb.iter(W_R):
            if r is r_el:
                return True
    return False


def _table_block(tbl_el, rels, styles, num_defs, default_sid, doc_default_sz):
    """提取表格。注意必须用**直接子级**遍历（findall），
    否则嵌套表格的行/单元格/段落会被 iter 卷进外层。
    单元格内的段落/嵌套表格递归构建为完整 Block（保留全部特征）。"""
    rows = []
    flat = []
    for tr in tbl_el.findall(W_TR):
        cells = []
        for tc in tr.findall(W_TC):
            cell_blocks = []
            for i, ch in enumerate(tc):
                if ch.tag == W_P:
                    cell_blocks.append(_build_para_block(
                        ch, i, None, rels, styles, num_defs,
                        default_sid, doc_default_sz))
                elif ch.tag == W_TBL:
                    cell_blocks.append(_build_table_block_el(
                        ch, i, rels, styles, num_defs, default_sid, doc_default_sz))
            paras = tc.findall(W_P)
            txt = "\n".join(
                "".join(t.text or "" for t in p.iter(W_T)).strip() for p in paras
            ).strip()
            cell = Cell(
                text=txt,
                n_paras=len(paras),
                has_image=(tc.find(".//" + _t(W, "drawing")) is not None or
                           tc.find(".//" + _t(W, "pict")) is not None),
                has_nested_table=tc.find(W_TBL) is not None,
                blocks=cell_blocks,
            )
            cells.append(cell)
            if txt:
                flat.append(txt)
        if cells:
            rows.append(cells)
    return TableBlock(rows=rows, text=" | ".join(flat))


# ---------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------
def read_struct_doc(path: str, name: Optional[str] = None) -> StructDoc:
    """读取 docx 文件路径，返回 StructDoc。"""
    with open(path, "rb") as fh:
        data = fh.read()
    return read_struct_doc_bytes(data, name=name or path)


def read_struct_doc_bytes(data: bytes, name: str = "<bytes>") -> StructDoc:
    """从 docx 字节流读取（支持直接读 zip 内嵌 docx，无需落盘）。"""
    import io
    zf = zipfile.ZipFile(io.BytesIO(data))
    rels = _parse_rels(zf, "word/_rels/document.xml.rels")
    styles, default_sid, doc_default_sz = _parse_styles(zf)
    num_defs = _parse_numbering(zf)
    try:
        root = ET.fromstring(zf.read("word/document.xml"))
    except KeyError:
        raise ValueError("不是有效的 docx（缺少 word/document.xml）：%s" % name)
    body = root.find(_t(W, "body"))
    if body is None:
        raise ValueError("docx 缺少 w:body：%s" % name)

    doc = StructDoc(name=name)
    doc.num_defs = num_defs
    pno = 0
    seq = 0                                  # 稠密块序号（只对真正落模的块递增）
    for body_idx, el in enumerate(body):
        if el.tag == W_SECTPR:
            continue
        if el.tag in (_t(W, "bookmarkStart"), _t(W, "bookmarkEnd")):
            # 书签是零内容锚点标记，不是内容单元，跳过（sdt 等真未知块仍保留为 unknown）
            continue
        if el.tag == W_P:
            pno += 1
            blk = _build_para_block(
                el, seq, pno, rels, styles, num_defs, default_sid, doc_default_sz)
        elif el.tag == W_TBL:
            blk = _build_table_block_el(
                el, seq, rels, styles, num_defs, default_sid, doc_default_sz)
        elif el.tag == W_SDT:
            blk = _build_unknown_block(el, seq, "sdt")
        else:
            blk = _build_unknown_block(el, seq, el.tag.rsplit("}", 1)[-1])
        blk.body_idx = body_idx
        doc.blocks.append(blk)
        seq += 1

    _finalize(doc)
    return doc


def _build_para_block(p_el, seq, pno, rels, styles, num_defs,
                      default_sid="", doc_default_sz=None):
    ppr = p_el.find(W_PPR)
    style_id = _val(ppr, "pStyle") or ""
    # 缺省 pStyle 的段落继承默认段落样式（Word 语义）
    effective_sid = style_id or default_sid
    sinfo = styles.get(effective_sid, {})
    outline = None
    if ppr is not None:
        ol = ppr.find(_t(W, "outlineLvl"))
        if ol is not None:
            try:
                outline = int(ol.get(_t(W, "val")))
            except (TypeError, ValueError):
                pass
    if outline is None:
        outline = sinfo.get("outline")

    sz_direct, bold_direct = _run_features(p_el)
    style_sz = sinfo.get("sz")
    eff_sz = sz_direct if sz_direct is not None else (
        style_sz if style_sz is not None else doc_default_sz)
    if bold_direct is not None:
        bold = bold_direct
    else:
        bold = sinfo.get("bold")

    num = None
    if ppr is not None:
        numpr = ppr.find(_t(W, "numPr"))
        if numpr is not None:
            nid_s = _val(numpr, "numId")
            ilvl_s = _val(numpr, "ilvl")
            try:
                nid = int(nid_s) if nid_s is not None else 0
            except ValueError:
                nid = 0
            try:
                ilvl = int(ilvl_s) if ilvl_s is not None else 0
            except ValueError:
                ilvl = 0
            fmt, lvl_text = num_defs.get(nid, {}).get(ilvl, ("", ""))
            num = NumInfo(num_id=nid, ilvl=ilvl, fmt=fmt, lvl_text=lvl_text)

    text = _para_text_main(p_el)
    blk = Block(
        seq=seq, pno=pno, kind="paragraph", text=text,
        # style_id/style_name 只记录**显式**样式（缺省继承不计入，避免满屏 Normal）
        style_id=style_id, style_name=styles.get(style_id, {}).get("name", ""),
        outline_lvl=outline,
        sz_direct=sz_direct, style_sz=style_sz, eff_sz=eff_sz, bold=bold,
        num=num,
        images=_para_images(p_el, rels),
        oles=_para_oles(p_el, rels),
        math_count=sum(1 for _ in p_el.iter(_t(M, "oMath"))),
        textbox_texts=_textbox_texts(p_el),
        is_empty=(not text and p_el.find(".//" + _t(W, "drawing")) is None
                  and p_el.find(".//" + _t(W, "pict")) is None),
    )
    return blk


def _build_table_block_el(tbl_el, seq, rels, styles, num_defs,
                          default_sid="", doc_default_sz=None):
    tb = _table_block(tbl_el, rels, styles, num_defs, default_sid, doc_default_sz)
    return Block(seq=seq, pno=None, kind="table", text=tb.text, table=tb,
                 is_empty=not tb.text)


def _build_unknown_block(el, seq, tag):
    """无法识别的内容：完整保留其全部文本，标记 unknown，不丢弃。"""
    text = "".join(t.text or "" for t in el.iter(W_T)).strip()
    return Block(seq=seq, pno=None, kind="unknown", text=text,
                 is_empty=not text, note="unrecognized body child: %s" % tag)


def iter_all_paragraphs(blocks):
    """递归产出所有段落 Block（body 级 + 任意深度表格单元格内）。

    Stage 2 的信号统计必须用它：「全文一张表」的讲义里，
    章节标题的字号/加粗特征全部在单元格段落上。
    """
    for b in blocks:
        if b.kind == "paragraph":
            yield b
        elif b.kind == "table" and b.table is not None:
            for row in b.table.rows:
                for cell in row:
                    yield from iter_all_paragraphs(cell.blocks)


def _finalize(doc):
    """文档级统计：正文字号、字号/样式/编号分布（穿透表格单元格）。"""
    all_paras = list(iter_all_paragraphs(doc.blocks))
    for b in all_paras:
        if b.text:
            if b.eff_sz:
                doc.size_hist[b.eff_sz] = doc.size_hist.get(b.eff_sz, 0) + 1
            key = b.style_name or b.style_id
            if key:
                doc.style_hist[key] = doc.style_hist.get(key, 0) + 1
            if b.num is not None:
                doc.num_usage[b.num.num_id] = doc.num_usage.get(b.num.num_id, 0) + 1
    if doc.size_hist:
        doc.body_size = max(doc.size_hist.items(), key=lambda kv: kv[1])[0]
    paras = doc.paragraphs
    cell_paras = len(all_paras) - len(paras)
    doc.stats = {
        "blocks": len(doc.blocks),
        "paragraphs": len(paras),
        "cell_paragraphs": cell_paras,
        "nonempty_paragraphs": sum(1 for b in all_paras if b.text),
        "tables": len(doc.tables),
        "unknown": sum(1 for b in doc.blocks if b.kind == "unknown"),
        "with_image": sum(1 for b in all_paras if b.images),
        "with_math": sum(1 for b in all_paras if b.has_math),
        "with_num": sum(1 for b in all_paras if b.num is not None),
        "with_textbox": sum(1 for b in all_paras if b.textbox_texts),
        "with_ole": sum(1 for b in all_paras if b.oles),
    }

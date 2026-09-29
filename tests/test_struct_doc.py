# -*- coding: utf-8 -*-
"""
test_struct_doc.py —— StructDoc（Splitter V2 第一阶段）自动测试

运行方式（任选）：
    python tests/test_struct_doc.py          # 直接运行，输出 PASS/FAIL
    python -m pytest tests/test_struct_doc.py

覆盖：样式推导字号/加粗/大纲级别、直接格式、编号列表解析、表格及单元格、
图片（inline/anchor/VML + rels 解析）、文本框（不混入正文）、OMML 公式、
OLE、sdt 未知块原样保留、空段、缺省样式继承、body 双索引契约。
"""
import io
import os
import sys
import zipfile

# 修正旧测试的坑：模块在 app/，不在 tests/
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

from struct_doc import read_struct_doc_bytes  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NSDECL = (
    'xmlns:w="%s" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:o="urn:schemas-microsoft-com:office:office" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"'
) % W

STYLES = """<?xml version="1.0"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="20"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:rPr><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="H1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
</w:styles>
"""

NUMBERING = """<?xml version="1.0"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="1">
    <w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
    <w:lvl w:ilvl="1"><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="(%2)"/></w:lvl>
  </w:abstractNum>
  <w:num w:numId="7"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>
"""

RELS = """<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
  <Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="embeddings/oleObject1.bin"/>
</Relationships>
"""

BODY = """
<w:p><w:r><w:t>正文一 普通段落</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="H1"/></w:pPr><w:r><w:t>一、样式标题</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="7"/></w:numPr></w:pPr>
  <w:r><w:rPr><w:sz w:val="24"/><w:b/></w:rPr><w:t>1. 编号题题干</w:t></w:r></w:p>
<w:p><w:r><w:t>如图</w:t></w:r>
  <w:drawing><wp:inline><wp:extent cx="914400" cy="457200"/>
    <a:graphic><a:graphicData><a:blip xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" r:embed="rId5"/></a:graphicData></a:graphic>
  </wp:inline></w:drawing></w:p>
<w:p><w:drawing><wp:anchor><wp:extent cx="100" cy="100"/>
    <a:graphic><a:graphicData><a:blip xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" r:embed="rId6"/></a:graphicData></a:graphic>
  </wp:anchor></w:drawing></w:p>
<w:tbl>
  <w:tr><w:tc><w:p><w:r><w:t>甲</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>乙</w:t></w:r></w:p><w:p><w:r><w:t>乙二</w:t></w:r></w:p></w:tc></w:tr>
  <w:tr><w:tc><w:p><w:r><w:t>丙</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>丁</w:t></w:r></w:p>
              <w:tbl><w:tr><w:tc><w:p><w:r><w:t>嵌套</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:tc></w:tr>
</w:tbl>
<w:p><w:r><w:t>外框文字</w:t></w:r>
  <w:drawing><wp:inline><wp:extent cx="1" cy="1"/><a:graphic><a:graphicData>
    <wps:txbx><w:txbxContent><w:p><w:r><w:t>框内文字</w:t></w:r></w:p></w:txbxContent></wps:txbx>
  </a:graphicData></a:graphic></wp:inline></w:drawing></w:p>
<w:p><w:r><w:t>公式段</w:t></w:r>
  <m:oMath><m:r><m:t>x=1</m:t></m:r></m:oMath></w:p>
<w:p><w:object><o:OLEObject Type="Embed" ProgID="Equation.DSMT4" r:id="rId9"/></w:object>
  <w:r><w:t>对象段</w:t></w:r></w:p>
<w:p><w:pict><v:imagedata r:id="rId5"/></w:pict></w:p>
<w:sdt><w:sdtContent><w:p><w:r><w:t>结构化标签文本</w:t></w:r></w:p></w:sdtContent></w:sdt>
<w:p/>
"""


def make_docx(body_inner):
    document = ('<?xml version="1.0"?><w:document %s><w:body>%s<w:sectPr/></w:body></w:document>'
                % (NSDECL, body_inner))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/numbering.xml", NUMBERING)
        z.writestr("word/_rels/document.xml.rels", RELS)
    return buf.getvalue()


def build():
    return read_struct_doc_bytes(make_docx(BODY), name="synthetic.docx")


# ---------------------------------------------------------------
# 测试
# ---------------------------------------------------------------
def test_dual_index_contract():
    """表格不占用 pno；pno 连续；seq 稠密；body_idx 记录原始位置。"""
    doc = build()
    pnos = [b.pno for b in doc.paragraphs]
    assert pnos == list(range(1, len(pnos) + 1)), pnos
    tbl = doc.tables[0]
    assert tbl.pno is None
    assert [b.seq for b in doc.blocks] == list(range(len(doc.blocks)))
    assert [b.body_idx for b in doc.blocks] == list(range(len(doc.blocks)))
    # 表格前后的段落编号连续（表格不挤占编号）
    para_by_seq = {b.seq: b for b in doc.blocks}
    tseq = tbl.seq
    assert para_by_seq[tseq - 1].pno + 1 == para_by_seq[tseq + 1].pno


def test_style_inheritance():
    """样式推导字号/加粗/大纲级别；缺省段落继承默认样式与 docDefaults。"""
    doc = build()
    h = doc.by_pno(2)
    assert h.style_id == "H1" and h.style_name == "heading 1"
    assert h.eff_sz == 32 and h.bold is True and h.outline_lvl == 0
    plain = doc.by_pno(1)
    assert plain.style_id == ""          # 显式样式为空
    assert plain.eff_sz == 21            # 继承默认 Normal 样式字号
    assert plain.style_name == ""        # 缺省继承不计入 style_name（避免满屏 Normal）


def test_direct_format_and_numbering():
    """直接格式字号覆盖样式；编号引用解析出格式。"""
    doc = build()
    q = doc.by_pno(3)
    assert q.sz_direct == 24 and q.eff_sz == 24
    assert q.bold is True
    assert q.num is not None and q.num.num_id == 7 and q.num.ilvl == 0
    assert q.num.fmt == "decimal" and q.num.lvl_text == "%1."


def test_images_and_rels():
    """inline/anchor/VML 三种图片都能识别并解析 rels 目标。"""
    doc = build()
    inline = doc.by_pno(4)
    assert len(inline.images) == 1
    img = inline.images[0]
    assert img.kind == "inline" and img.target.endswith("media/image1.png")
    assert img.cx == 914400 and img.cy == 457200
    anchor = doc.by_pno(5)
    assert anchor.images and anchor.images[0].kind == "anchor"
    vml = doc.by_pno(9)   # sdt 是 unknown 块不占 pno；pict 段是第 9 段
    assert vml.images and vml.images[0].kind == "vml"
    assert vml.images[0].target.endswith("media/image1.png")


def test_table_block():
    """表格单元格内容、多段单元格、嵌套表格。"""
    doc = build()
    tb = doc.tables[0].table
    assert tb.n_rows == 2 and tb.n_cols_max == 2
    assert tb.rows[0][0].text == "甲"
    assert tb.rows[0][1].text == "乙\n乙二"
    assert tb.rows[0][1].n_paras == 2
    assert tb.rows[1][1].has_nested_table is True
    assert "甲" in doc.tables[0].text and "丁" in doc.tables[0].text


def test_cell_blocks_structured():
    """单元格内段落是完整 Block（保留特征）；嵌套表递归成 Block。"""
    from struct_doc import iter_all_paragraphs
    doc = build()
    tb = doc.tables[0].table
    cell = tb.rows[0][1]
    assert len(cell.blocks) == 2                      # 两个段落块
    assert all(b.kind == "paragraph" and b.pno is None for b in cell.blocks)
    assert cell.blocks[0].text == "乙"
    nested = tb.rows[1][1]
    kinds = [b.kind for b in nested.blocks]
    assert "table" in kinds                           # 嵌套表递归成 Block
    # 全段落迭代器穿透表格
    all_texts = [b.text for b in iter_all_paragraphs(doc.blocks)]
    for t in ["甲", "乙", "乙二", "丁"]:
        assert t in all_texts, t


def test_textbox_not_mixed():
    """文本框内容不混入段落主文本，但完整保留在 textbox_texts。"""
    doc = build()
    b = doc.by_pno(6)
    assert b.text == "外框文字"
    assert any("框内文字" in t for t in b.textbox_texts)


def test_math_ole_unknown():
    """公式计数、OLE 对象、sdt 未知块原样保留。"""
    doc = build()
    assert doc.by_pno(7).math_count == 1
    ole = doc.by_pno(8)
    assert ole.oles and ole.oles[0].prog_id == "Equation.DSMT4"
    assert ole.oles[0].target.endswith("oleObject1.bin")
    unk = [b for b in doc.blocks if b.kind == "unknown"]
    assert len(unk) == 1 and "结构化标签文本" in unk[0].text


def test_empty_and_stats():
    """空段标记与文档级统计。"""
    doc = build()
    last = doc.paragraphs[-1]
    assert last.is_empty is True
    st = doc.stats
    assert st["tables"] == 1 and st["unknown"] == 1
    assert st["with_image"] == 3 and st["with_math"] == 1 and st["with_ole"] == 1
    assert doc.body_size == 21  # 出现最多的 eff_sz（Normal 继承）


def test_no_content_loss():
    """保真性：源文档中每一段文本都能在模型中找到（不遗漏、不重复计段落）。"""
    doc = build()
    all_text = "\n".join(b.text for b in doc.blocks)
    for token in ["正文一", "一、样式标题", "编号题题干", "外框文字", "公式段",
                  "对象段", "结构化标签文本"]:
        assert token in all_text, token
    # 文本框内容单独保存，不算丢失
    assert any("框内文字" in t for b in doc.blocks for t in b.textbox_texts)
    # 表格内容在表格块中
    assert "甲" in doc.tables[0].text


def test_real_contract_with_docutils():
    """真实文件：pno/文本序列与 docutils.scan_paragraphs 完全一致（契约回归）。

    用两份：①「全文一表」型（body 段落极少，验证表格不挤占编号）；
    ②普通段落型（256+ 段，验证长文档编号一致性）。
    """
    reals = [
        (r"C:\Users\Administrator\Desktop\工作\讲义生成器"
         r"\2025-2026学年_高一_数学_第1 速度的测量_复习讲义_学生版.docx"),
        (r"C:\Users\Administrator\Desktop\工作\讲义生成器\做讲义"
         r"\专题02 计数原理与二项式定理（题型清单）（学生版）.docx"),
    ]
    try:
        import docutils
    except Exception as e:
        print("  [SKIP] docutils 不可用：%s" % e)
        return
    from struct_doc import read_struct_doc
    tested = 0
    for real in reals:
        if not os.path.exists(real):
            print("  [SKIP] 真实文件不存在：%s" % os.path.basename(real))
            continue
        doc = read_struct_doc(real)
        old = docutils.scan_paragraphs(real)
        new = [(b.pno, b.text) for b in doc.paragraphs]
        assert len(old) == len(new), (real, len(old), len(new))
        mismatch = 0
        for (oi, ot, _img), (ni, nt) in zip(old, new):
            if oi != ni or ot != nt:
                mismatch += 1
                if mismatch <= 3:
                    print("  [MISMATCH] %s p%d: %r vs %r"
                          % (os.path.basename(real), oi, ot[:30], nt[:30]))
        assert mismatch == 0, "%s 与旧契约不一致的段落数: %d" % (real, mismatch)
        tested += 1
    assert tested > 0, "没有任何真实文件可用于契约回归"


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    ok = fail = 0
    for fn in ALL:
        try:
            fn()
            print("PASS %s" % fn.__name__)
            ok += 1
        except AssertionError as e:
            print("FAIL %s: %s" % (fn.__name__, e))
            fail += 1
        except Exception as e:
            print("ERROR %s: %s: %s" % (fn.__name__, type(e).__name__, e))
            fail += 1
    print("\n%d passed, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

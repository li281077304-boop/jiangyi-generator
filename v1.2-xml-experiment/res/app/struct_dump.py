# -*- coding: utf-8 -*-
"""
struct_dump.py —— StructDoc 的人类可读 dump（「程序眼里这份讲义长什么样」）

用法：
    python struct_dump.py <讲义.docx> [-o 输出.txt] [--full] [--max-blocks N]

    --full        段落文本不截断
    --max-blocks  只显示前 N 个块（默认全部）

输出结构：
    1. 文档概要（块数/段落/表格/未知/图片/公式/编号/正文字号/字号层）
    2. 编号定义（numId → 格式）
    3. 逐块序列（seq / pno / 特征标记 / 文本）
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from struct_doc import StructDoc, read_struct_doc  # noqa: E402


def _sz(v):
    """半磅 → 磅值显示。"""
    return "%gpt" % (v / 2.0) if v else "-"


def _para_feat(b):
    """段落特征标记串。"""
    feats = []
    if b.eff_sz:
        feats.append("sz=%s" % _sz(b.eff_sz))
    if b.bold:
        feats.append("B")
    if b.style_name or b.style_id:
        feats.append("st=%s" % (b.style_name or b.style_id))
    if b.outline_lvl is not None:
        feats.append("ol%d" % b.outline_lvl)
    if b.num is not None:
        feats.append("num%d/L%d%s" % (b.num.num_id, b.num.ilvl,
                     (":" + b.num.fmt) if b.num.fmt else ""))
    if b.images:
        kinds = ",".join(sorted({i.kind for i in b.images}))
        feats.append("img%d(%s)" % (len(b.images), kinds))
    if b.oles:
        feats.append("ole%d" % len(b.oles))
    if b.math_count:
        feats.append("math%d" % b.math_count)
    if b.textbox_texts:
        feats.append("txbx%d" % len(b.textbox_texts))
    if b.is_empty:
        feats.append("empty")
    return " ".join(feats) or "-"


def _clip(text, full, limit=76):
    if full or len(text) <= limit:
        return text
    return text[:limit] + "…"


def format_dump(doc: StructDoc, full: bool = False, max_blocks: int = 0) -> str:
    out = []
    A = out.append
    st = doc.stats
    A("=" * 96)
    A("结构 DUMP: %s" % doc.name)
    A("=" * 96)
    A("[概要] 块 %d | 段落 %d（单元格内 %d，非空合计 %d）| 表格 %d | 未知 %d | "
      "含图段 %d | 含公式段 %d | 编号段 %d | 文本框段 %d | OLE段 %d"
      % (st["blocks"], st["paragraphs"], st["cell_paragraphs"],
         st["nonempty_paragraphs"], st["tables"],
         st["unknown"], st["with_image"], st["with_math"], st["with_num"],
         st["with_textbox"], st["with_ole"]))
    A("[字号] 正文 %s | 分布: %s"
      % (_sz(doc.body_size),
         " ".join("%s:%d" % (_sz(s), c) for s, c in
                  sorted(doc.size_hist.items(), key=lambda kv: -kv[1])[:8])))
    tiers = doc.size_tiers()
    if tiers:
        A("[字号层] 大于正文的字号: %s  ← Stage2 标题层的原始素材"
          % " ".join("%s:%d" % (_sz(s), c) for s, c in tiers.items()))
    if doc.style_hist:
        A("[样式] %s" % " ".join("%s:%d" % (k, v)
          for k, v in sorted(doc.style_hist.items(), key=lambda kv: -kv[1])[:8]))
    if doc.num_defs:
        A("[编号定义]")
        for nid, lvls in sorted(doc.num_defs.items()):
            used = doc.num_usage.get(nid, 0)
            lv = " ".join("L%d=%s\"%s\"" % (i, f or "?", t) for i, (f, t) in sorted(lvls.items()))
            A("  numId %d (使用 %d 段): %s" % (nid, used, lv))
    A("-" * 96)
    A("[块序列]  seq | pno | 特征 | 文本")
    shown = 0
    for b in doc.blocks:
        if max_blocks and shown >= max_blocks:
            A("  …（共 %d 块，仅显示前 %d 块）" % (len(doc.blocks), max_blocks))
            break
        shown += 1
        pno = "p#%04d" % b.pno if b.pno else "  --- "
        if b.kind == "table":
            tb = b.table
            A("[%04d %s] TBL %dx%d" % (b.seq, pno, tb.n_rows, tb.n_cols_max))
            for ri, row in enumerate(tb.rows):
                for ci, cell in enumerate(row):
                    if cell.blocks:
                        A("      r%dc%d:" % (ri, ci))
                        for cb in cell.blocks:
                            if cb.kind == "table":
                                A("        └TBL %dx%d %s"
                                  % (cb.table.n_rows, cb.table.n_cols_max,
                                     _clip(cb.text, full, 50)))
                            else:
                                A("        │ %s | %s"
                                  % (_para_feat(cb), _clip(cb.text, full, 60)))
                    else:
                        A("      r%dc%d: %s" % (ri, ci, _clip(cell.text.replace("\n", "⏎"), full, 60)))
            continue
        if b.kind == "unknown":
            A("[%04d %s] ??? (%s) %s" % (b.seq, pno, b.note, b.text[:60]))
            continue
        # 段落
        A("[%04d %s] %s | %s" % (b.seq, pno, _para_feat(b), _clip(b.text, full)))
        for tb_text in b.textbox_texts:
            A("      └txbx: %s" % tb_text.replace("\n", "⏎")[:70])
        for img in b.images:
            if full:
                A("      └img %s %s %dx%dEMU" % (img.kind, img.target, img.cx, img.cy))
    A("=" * 96)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="讲义结构 dump（只读）")
    ap.add_argument("docx", help="讲义 docx 路径")
    ap.add_argument("-o", "--out", help="输出到文件（默认打印到 stdout）")
    ap.add_argument("--full", action="store_true", help="文本不截断")
    ap.add_argument("--max-blocks", type=int, default=0, help="只显示前 N 块")
    args = ap.parse_args()

    doc = read_struct_doc(args.docx)
    text = format_dump(doc, full=args.full, max_blocks=args.max_blocks)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("已写出: %s（%d 行）" % (args.out, text.count("\n") + 1))
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        print(text)


if __name__ == "__main__":
    main()

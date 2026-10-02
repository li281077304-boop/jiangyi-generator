"""Read the real content of a finished DOCX the way a user would look at it."""
from __future__ import annotations

import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SECTIONS = ("课堂启动", "知识回顾", "知识精讲", "即时训练", "归纳总结", "巩固练习", "出门测试")


def paragraphs(path: str) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    body = root.find("{%s}body" % W)
    out: list[str] = []

    def visit(node: ET.Element) -> None:
        if node.tag == "{%s}txbxContent" % W:
            return
        if node.tag == "{%s}p" % W:
            out.append("".join(t.text or "" for t in node.iter("{%s}t" % W)))
            return
        for child in list(node):
            visit(child)

    visit(body)
    return out


def main() -> int:
    for path in sys.argv[1:]:
        texts = paragraphs(path)
        nonempty = [(i, t) for i, t in enumerate(texts) if t.strip()]
        print("=" * 78)
        print(path.split("\\")[-1])
        print("  paragraphs=%d nonempty=%d chars=%d" % (
            len(texts), len(nonempty), len("\n".join(texts))))
        print("  -- first 14 non-empty (cover) --")
        for index, text in nonempty[:14]:
            print("     %4d| %s" % (index, text[:76]))
        print("  -- section headings in document order --")
        seen = []
        for index, text in nonempty:
            flat = re.sub(r"\s+", "", text)
            for name in SECTIONS:
                if name in flat and len(flat) <= len(name) + 24:
                    seen.append((index, name, flat[:40]))
                    break
        for index, name, flat in seen:
            print("     %4d| %-6s %s" % (index, name, flat))
        print("  -- last 10 non-empty --")
        for index, text in nonempty[-10:]:
            print("     %4d| %s" % (index, text[:76]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

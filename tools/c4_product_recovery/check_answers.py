"""Count answer markers in each published teacher/student output."""
from __future__ import annotations

import glob
import re
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MARK = re.compile(r"【\s*(答案|解析|详解|分析)\s*】|参考答案|参考解析")


def texts(path: str) -> list[str]:
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


for directory in (r"run-source-20261003T010232\results", r"run-source-20261003T010811\results"):
    for path in sorted(glob.glob(directory + r"\*\*.docx")):
        count = sum(len(MARK.findall(line)) for line in texts(path))
        role = "TEACHER" if path.endswith("教师版.docx") else ("STUDENT" if path.endswith("学生版.docx") else "OTHER")
        print("%-8s %-46s answer_markers=%d" % (role, path.split("\\")[-1][:46], count))

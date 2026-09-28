# -*- coding: utf-8 -*-
"""
docutils.py —— 文档工具层

职责：
  1. 段落扫描（必须走 Word COM，段落序号与模板填充脚本一致）
  2. 主题提取 / 文件名生成 / 学年计算（单一事实来源在 split_engine，这里只 re-export）

设计约定：
  - 不重复定义 split_engine 已有的函数，避免两处实现漂移。
"""
import os
import subprocess
import tempfile
import locale

import config
import logger

log = logger.get_logger("docutils")


def _find_powershell() -> str:
    """定位 powershell.exe，便携部署时不依赖固定路径。"""
    candidates = [
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
        __import__("shutil").which("powershell"),
        __import__("shutil").which("pwsh"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "powershell.exe"  # 兜底交给 PATH


POWERSHELL = _find_powershell()


def _run_scan(docx_path: str) -> list:
    """调 PowerShell 扫描，返回原始行列表 [idx, text, has_img, ...]（最低兼容两列）。"""
    fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="scan_")
    os.close(fd)
    try:
        subprocess.run(
            [POWERSHELL, "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", config.PS_SCAN,
             "-DocPath", os.path.abspath(docx_path), "-OutPath", out_path],
            capture_output=True, text=True, encoding=locale.getpreferredencoding(),
            errors="replace", timeout=180)
        rows = []
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if parts and parts[0].strip().isdigit():
                    rows.append(parts)
        return rows
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def scan_paragraphs(docx_path: str) -> list:
    """
    返回 [(序号, 文本, 含图片标志)]，序号与 Word COM Paragraphs 完全一致。
    has_img: 1=该段含内嵌/浮动图片，0=纯文本段。
    必须走 COM（经 PowerShell），否则与填充脚本的段落索引不符
    （ZIP/XML 计数会漏掉文本框等结构内的段落，导致范围错位）。
    """
    rows = _run_scan(docx_path)
    paras = []
    for parts in rows:
        idx = int(parts[0])
        txt = parts[1] if len(parts) > 1 else ""
        has_img = 1 if len(parts) > 2 and parts[2].strip() == "1" else 0
        paras.append((idx, txt, has_img))
    return paras


def body_paragraphs(docx_path: str) -> list:
    """返回 [(序号, 文本)]（兼容旧接口，忽略图片标志）。"""
    return [(i, t) for i, t, _ in scan_paragraphs(docx_path)]


def para_count(docx_path: str) -> int:
    """返回文档段落总数。"""
    return len(body_paragraphs(docx_path))


# ------------------------------------------------------------
# 主题提取 / 文件名生成 / 学年 —— 单一事实来源在 split_engine
# ------------------------------------------------------------
from split_engine import extract_topic, current_academic_year, build_filename  # noqa: E402,F401  (re-export)

# -*- coding: utf-8 -*-
"""Conservative teacher/student input-version classification for C1."""
from __future__ import annotations

from dataclasses import dataclass
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


class UnknownInputVersion(ValueError):
    code = "UNKNOWN_INPUT_VERSION"


@dataclass(frozen=True)
class InputClassification:
    input_version: str
    teacher_index: int | None
    student_index: int | None
    evidence: str


_TEACHER_NAME = re.compile(r"(?:教师版|教师|老师|解析版|答案版|背诵版|teacher|answer|solution)", re.I)
_STUDENT_NAME = re.compile(r"(?:学生版|学生|空白版|默写版|原卷|无答案|student|blank)", re.I)
_ROLE_SUFFIX = re.compile(
    r"[\s._（(【\[\-]*(?:教师版|教师|老师|学生版|学生|空白版|默写版|背诵版|原卷版|原卷|无答案|答案版|答案|解析版|解析|"
    r"teacher|student|answer|solution|blank)[）)】\]]?$", re.I,
)
_ANSWER_MARKER = re.compile(
    r"(?:【\s*(?:答案|解析|分析)\s*】|参考答案|参考解析|答案\s*[:：]|解析\s*[:：])"
)
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _filename_signal(name: str) -> str | None:
    teacher = bool(_TEACHER_NAME.search(name or ""))
    student = bool(_STUDENT_NAME.search(name or ""))
    if teacher == student:
        return None
    return "teacher" if teacher else "student"


def _pair_identity(name: str) -> str:
    """Remove trailing version labels and compare the underlying topic name."""
    stem = Path(name or "").stem.replace("_", " ").strip()
    previous = None
    while stem != previous:
        previous = stem
        stem = _ROLE_SUFFIX.sub("", stem).strip(" ._-")
    return re.sub(r"\s+", " ", stem).casefold()


def _has_answer_structure(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            root = ET.fromstring(package.read("word/document.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
        return False
    values = [node.text or "" for node in root.iter("{%s}t" % _W_NS)]
    text = " ".join(values)
    return len(_ANSWER_MARKER.findall(text)) >= 2


def classify_inputs(files: list[tuple[str, bytes]], docx_mode: str = "auto") -> InputClassification:
    """Classify one source or a single explicit teacher/student pair.

    No file-size comparison or silent filename ordering is used.
    """
    if docx_mode not in ("auto", "separate"):
        raise UnknownInputVersion("不支持的 Word 文件分组模式")
    if not files or len(files) > 2:
        raise UnknownInputVersion("当前只支持一个来源或一组教师版/学生版文件")
    if len(files) == 2 and docx_mode != "auto":
        raise UnknownInputVersion("本轮两个 DOCX 只支持按教师版/学生版成对输入")

    signals = [_filename_signal(name) for name, _data in files]
    content_teacher = [_has_answer_structure(data) for _name, data in files]
    if len(files) == 1:
        if signals[0] == "teacher":
            return InputClassification("TEACHER_ONLY", 0, None, "teacher_filename")
        if signals[0] == "student":
            return InputClassification("STUDENT_ONLY", None, 0, "student_filename")
        if content_teacher[0]:
            return InputClassification("TEACHER_ONLY", 0, None, "answer_analysis_content")
        raise UnknownInputVersion("无法确认这是教师版还是学生版，请使用清楚标注的文件名")

    teacher_indices = [i for i, value in enumerate(signals) if value == "teacher"]
    student_indices = [i for i, value in enumerate(signals) if value == "student"]
    if len(teacher_indices) == len(student_indices) == 1:
        teacher, student = teacher_indices[0], student_indices[0]
        if not _pair_identity(files[teacher][0]) or (
                _pair_identity(files[teacher][0]) != _pair_identity(files[student][0])):
            raise UnknownInputVersion("教师版和学生版主题不一致，拒绝自动配对")
        return InputClassification("TEACHER_AND_STUDENT", teacher_indices[0], student_indices[0],
                                   "paired_filenames")
    content_indices = [i for i, value in enumerate(content_teacher) if value]
    if len(content_indices) == 1:
        teacher = content_indices[0]
        student = 1 - teacher
        if signals[teacher] != "student" and signals[student] != "teacher":
            if not _pair_identity(files[teacher][0]) or (
                    _pair_identity(files[teacher][0]) != _pair_identity(files[student][0])):
                raise UnknownInputVersion("教师版和学生版主题不一致，拒绝自动配对")
            return InputClassification("TEACHER_AND_STUDENT", teacher, student,
                                       "one_answer_rich_source")
    raise UnknownInputVersion("教师版和学生版无法可靠配对；不会按文件大小猜测")

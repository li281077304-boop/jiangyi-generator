"""C2 upload expansion and conservative topic pairing; no rendering or COM.

Archive directories stay diagnostic metadata only. DOCX bytes are expanded in
memory, never extracted to paths supplied by an archive. Damaged DOCX files and
ambiguous topic groups become failed logical items, preserving other items.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import PurePosixPath
import re
import stat
import zipfile
import zlib

from input_versions import UnknownInputVersion, classify_inputs


MAX_DOCX_FILES = 200
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4000


class BatchInputError(ValueError):
    """The upload envelope is unsafe or cannot contain a supported batch."""


@dataclass(frozen=True)
class SourceInput:
    name: str
    data: bytes
    origin: str


@dataclass(frozen=True)
class LogicalInput:
    topic: str
    input_version: str | None
    teacher_source: SourceInput | None
    student_source: SourceInput | None
    sources: tuple[SourceInput, ...]
    evidence: str
    error: str | None = None


_TEACHER_LABELS = {"教师版", "解析版", "答案版", "教师用", "教师", "老师", "teacher", "answer", "solution"}
_STRONG_LABEL = r"教师版|解析版|答案版|教师用|学生版|原卷版|空白版|学生用"
_SHORT_LABEL = r"教师|老师|学生|原卷|无答案|teacher|answer|solution|student|blank"
_SUFFIX_LABEL = re.compile(
    r"(?:[（(\[【](?P<wrapped>" + _STRONG_LABEL + "|" + _SHORT_LABEL + r")[）)\]】]"
    r"|(?P<strong>" + _STRONG_LABEL + r")|(?:^|[\s._-])(?P<short>" + _SHORT_LABEL + r"))$", re.I)
_PREFIX_LABEL = re.compile(
    r"^(?:[（(\[【](?P<wrapped>" + _STRONG_LABEL + "|" + _SHORT_LABEL + r")[）)\]】]"
    r"|(?P<plain>" + _STRONG_LABEL + "|" + _SHORT_LABEL + r")[\s._-]+)", re.I)
_VERSION_SUFFIX = re.compile(
    r"(?:[\s._-]*(?:[（(\[【]?(?:修订版|修正版|最新版|更新版|最终版|正式版|定稿版|"
    r"第[一二三四五六七八九十\d]+版|v\d+(?:\.\d+)*|版本\s*\d+)[）)\]】]?))$", re.I)


def topic_identity(name: str) -> tuple[str, str | None]:
    """Return a readable topic and role, preserving meaningful topic numbers."""
    stem = PurePosixPath(name.replace("\\", "/")).stem
    roles = set()
    previous = None
    while previous != stem:
        previous = stem
        stem = _VERSION_SUFFIX.sub("", stem).strip(" ._-")
        suffix, prefix = _SUFFIX_LABEL.search(stem), _PREFIX_LABEL.search(stem)
        marker = suffix or prefix
        if marker:
            label = next(value for value in marker.groupdict().values() if value).casefold()
            roles.add("teacher" if label in _TEACHER_LABELS else "student")
            stem = (stem[:marker.start()] + stem[marker.end():]).strip(" ._-")
    if len(roles) > 1:
        raise UnknownInputVersion("文件名同时包含教师与学生标记，拒绝猜测")
    role = next(iter(roles)) if roles else None
    stem = re.sub(r"[_\s]+", " ", stem).strip(" .-")
    if not stem:
        raise UnknownInputVersion("去除版本标记后没有可验证的专题名称")
    return stem, role


def _zip_member_name(entry: zipfile.ZipInfo) -> str:
    """Use UTF-8 flags or an explicit Windows GBK policy, never mojibake.

    Non-ASCII names without UTF-8 flags must be valid GBK with Chinese text.
    If the same bytes are also valid UTF-8, reject the ambiguous encoding.
    Archive reads still use the original ZipInfo, so local-header checks hold.
    """
    if entry.flag_bits & 0x800 or entry.filename.isascii():
        return entry.filename
    raw = entry.filename.encode("cp437")
    try:
        decoded = raw.decode("gbk")
    except UnicodeDecodeError as exc:
        raise BatchInputError("UNSUPPORTED_ZIP_NAME_ENCODING: %s" % entry.filename) from exc
    if not re.search(r"[\u3400-\u9fff]", decoded):
        raise BatchInputError("UNSUPPORTED_ZIP_NAME_ENCODING: %s" % entry.filename)
    try:
        alternative = raw.decode("utf-8")
    except UnicodeDecodeError:
        alternative = None
    if alternative is not None and alternative != decoded:
        raise BatchInputError("AMBIGUOUS_ZIP_NAME_ENCODING: %s" % entry.filename)
    return decoded


def _archive_path(raw: str) -> str:
    value = raw.replace("\\", "/")
    parts = value.split("/")
    if (not value or value.startswith("/") or any(part == ".." for part in parts)
            or any(":" in part or "\x00" in part for part in parts)):
        raise BatchInputError("UNSAFE_ZIP_PATH: %s" % raw)
    return str(PurePosixPath(value))


def expand_uploads(files: list[tuple[str, bytes]]) -> list[SourceInput]:
    """Expand nested-directory ZIP entries without accepting nested archives."""
    if not files:
        raise BatchInputError("请选择 DOCX 或 ZIP")
    expanded: list[SourceInput] = []
    total = 0

    def append(name: str, data: bytes, origin: str) -> None:
        nonlocal total
        total += len(data)
        if len(expanded) >= MAX_DOCX_FILES or total > MAX_EXPANDED_BYTES:
            raise BatchInputError("BATCH_INPUT_LIMIT_EXCEEDED")
        expanded.append(SourceInput(PurePosixPath(name).name, data, origin))

    for original, data in files:
        name = PurePosixPath((original or "source.docx").replace("\\", "/")).name
        suffix = PurePosixPath(name).suffix.lower()
        if suffix == ".docx":
            if not name.startswith("~$"):
                append(name, data, name)
        elif suffix == ".zip":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    entries = archive.infolist()
                    if len(entries) > MAX_ARCHIVE_ENTRIES:
                        raise BatchInputError("BATCH_INPUT_LIMIT_EXCEEDED")
                    seen = set()
                    for entry in entries:
                        path = _archive_path(_zip_member_name(entry))
                        if stat.S_ISLNK(entry.external_attr >> 16):
                            raise BatchInputError("UNSAFE_ZIP_SYMLINK: %s" % path)
                        if entry.is_dir():
                            continue
                        if path.casefold() in seen:
                            raise BatchInputError("DUPLICATE_ZIP_ENTRY: %s" % path)
                        seen.add(path.casefold())
                        leaf = PurePosixPath(path).name
                        if (PurePosixPath(leaf).suffix.lower() != ".docx"
                                or leaf.startswith("~$") or "__MACOSX" in PurePosixPath(path).parts):
                            continue
                        if len(expanded) >= MAX_DOCX_FILES or total + entry.file_size > MAX_EXPANDED_BYTES:
                            raise BatchInputError("BATCH_INPUT_LIMIT_EXCEEDED")
                        append(leaf, archive.read(entry), name + ":" + path)
            except (zipfile.BadZipFile, RuntimeError, OSError, zlib.error) as exc:
                raise BatchInputError("INVALID_ZIP: %s" % name) from exc
        else:
            raise BatchInputError("仅支持 DOCX 或 ZIP：%s" % name)
    if not expanded:
        raise BatchInputError("没有可处理的 DOCX（临时文件已忽略）")
    return expanded


def _validate_source(source: SourceInput) -> None:
    # Envelope validation only; production output package validation stays
    # with the existing C1 JobService and B-Line validator.
    try:
        with zipfile.ZipFile(io.BytesIO(source.data)) as package:
            entries = package.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES:
                raise ValueError("DOCX 展开大小超过安全上限")
            names = set(package.namelist())
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise ValueError("缺少 DOCX 主文档部件")
            if package.testzip() is not None:
                raise ValueError("DOCX CRC 校验失败")
    except (zipfile.BadZipFile, RuntimeError, OSError, zlib.error) as exc:
        raise ValueError("无效或损坏的 DOCX") from exc


def resolve_batch(files: list[tuple[str, bytes]], docx_mode: str = "auto") -> list[LogicalInput]:
    """Resolve stable logical units; never pair by order or size.

    In automatic mode a topic has at most one source per role. Duplicate or
    contradictory roles fail the topic closed. Explicit separate mode keeps
    each input independent. A single/pair uses the approved C1 classifier for
    content evidence, with canonical labels for the added strong keywords.
    """
    if docx_mode not in ("auto", "separate"):
        raise BatchInputError("不支持的 Word 文件分组模式")
    groups: dict[str, list[tuple[SourceInput, str, str | None]]] = {}
    immediate_errors: list[LogicalInput] = []
    for source in expand_uploads(files):
        try:
            topic, role = topic_identity(source.name)
        except UnknownInputVersion as exc:
            immediate_errors.append(LogicalInput(PurePosixPath(source.name).stem, None,
                                                None, None, (source,), "ambiguous_name", str(exc)))
            continue
        key = topic.casefold() if docx_mode == "auto" else "%d:%s" % (len(groups), topic.casefold())
        groups.setdefault(key, []).append((source, topic, role))

    items = []
    for group in groups.values():
        topic = group[0][1]
        sources = tuple(value[0] for value in group)
        try:
            for source in sources:
                _validate_source(source)
            # Identity is already established by the normalized topic key.
            # Avoid feeding meaningful topic words such as 教师素养 back into
            # C1's broad filename-role heuristics; only pass verified labels.
            canonical = [("source" + (" 教师版" if role == "teacher" else " 学生版" if role == "student" else "")
                          + ".docx", source.data) for source, _topic, role in group]
            if len(canonical) > 2:
                raise UnknownInputVersion("同专题存在多个来源，无法唯一配对")
            classification = classify_inputs(canonical, "auto")
            teacher = sources[classification.teacher_index] if classification.teacher_index is not None else None
            student = sources[classification.student_index] if classification.student_index is not None else None
            items.append(LogicalInput(topic, classification.input_version, teacher, student,
                                      sources, classification.evidence))
        except (UnknownInputVersion, ValueError) as exc:
            items.append(LogicalInput(topic, None, None, None, sources, "failed_closed", str(exc)))
    return items + immediate_errors

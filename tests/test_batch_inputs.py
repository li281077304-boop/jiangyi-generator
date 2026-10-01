import io
from pathlib import Path
import stat
import sys
import zipfile
import zlib

from docx import Document
import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP_DIR))
import batch_inputs
from batch_inputs import BatchInputError, expand_uploads, resolve_batch, topic_identity


def docx(*texts):
    buffer = io.BytesIO()
    document = Document()
    for text in texts or ("真实题目结构 fixture",):
        document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


def archive(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in entries:
            package.writestr(name, data)
    return buffer.getvalue()


def test_five_teacher_sources_are_five_independent_items():
    items = resolve_batch([(f"专题{i} 教师版.docx", docx()) for i in range(1, 6)])
    assert len(items) == 5
    assert all(item.input_version == "TEACHER_ONLY" and item.teacher_source and not item.student_source
               for item in items)


def test_three_pairs_preserve_exact_student_bytes_without_order_pairing():
    teacher, student = docx("【答案】A", "【解析】过程"), docx("学生独有内容")
    uploads = [(f"专题{i} 学生版.docx", student) for i in (3, 1, 2)]
    uploads += [(f"专题{i} 答案版.docx", teacher) for i in (2, 3, 1)]
    items = resolve_batch(uploads)
    assert len(items) == 3
    assert all(item.input_version == "TEACHER_AND_STUDENT" for item in items)
    assert all(item.student_source.data == student and item.teacher_source.data == teacher for item in items)
    assert all(item.student_source.name.startswith(item.topic) and item.teacher_source.name.startswith(item.topic)
               for item in items)


def test_mixed_single_teacher_student_and_pair():
    items = resolve_batch([(name, docx()) for name in (
        "函数 教师用.docx", "化学 学生用.docx", "力学 解析版.docx", "力学 原卷版.docx")])
    assert [(item.topic, item.input_version) for item in items] == [
        ("函数", "TEACHER_ONLY"), ("化学", "STUDENT_ONLY"), ("力学", "TEACHER_AND_STUDENT")]


def test_chinese_zip_nested_directories_and_temp_file_filter():
    package = archive([(name, docx()) for name in (
        "一层/二层/函数 教师版.docx", "学生目录/函数 学生版.docx",
        "物理/力学 教师用.docx", "化学 学生用.docx", "临时/~$函数 教师版.docx",
        "__MACOSX/._函数 教师版.docx")])
    items = resolve_batch([("中文专题包.zip", package)])
    assert len(items) == 3
    assert items[0].input_version == "TEACHER_AND_STUDENT"
    assert items[0].teacher_source.name == "函数 教师版.docx"
    assert items[0].teacher_source.origin == "中文专题包.zip:一层/二层/函数 教师版.docx"
    assert len(items[0].sources) == 2


@pytest.mark.parametrize("unsafe", ["../evil.docx", "/evil.docx", "C:/evil.docx",
                                     "folder/../../evil.docx", "..\\evil.docx",
                                     "\\\\server\\share\\evil.docx", "safe/a.docx:stream"])
def test_zip_slip_and_windows_path_aliases_rejected(unsafe):
    with pytest.raises(BatchInputError, match="UNSAFE_ZIP_PATH"):
        expand_uploads([("输入.zip", archive([(unsafe, b"x")]))])


def test_zip_symlink_rejected():
    entry = zipfile.ZipInfo("link.docx")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(BatchInputError, match="UNSAFE_ZIP_SYMLINK"):
        expand_uploads([("输入.zip", archive([(entry, b"target")]))])


def test_duplicate_zip_names_fail_closed():
    with pytest.raises(BatchInputError, match="DUPLICATE_ZIP_ENTRY"):
        expand_uploads([("输入.zip", archive([("A教师版.docx", b"1"), ("a教师版.docx", b"2")]))])


def test_zip_limits_checked_before_expanding(monkeypatch):
    monkeypatch.setattr(batch_inputs, "MAX_EXPANDED_BYTES", 20)
    with pytest.raises(BatchInputError, match="BATCH_INPUT_LIMIT_EXCEEDED"):
        expand_uploads([("输入.zip", archive([("教师版.docx", b"a" * 21)]))])


def test_corrupt_docx_is_an_item_error_and_other_topics_survive():
    items = resolve_batch([("损坏 教师版.docx", b"corrupt"), ("正常 学生版.docx", docx())])
    assert len(items) == 2 and items[0].error
    assert items[1].input_version == "STUDENT_ONLY" and items[1].error is None


def test_duplicate_roles_fail_topic_without_arbitrary_choice():
    items = resolve_batch([(name, docx()) for name in (
        "专题 教师版.docx", "专题 解析版.docx", "专题 学生版.docx", "另一专题 学生版.docx")])
    assert len(items) == 2 and items[0].error
    assert items[1].input_version == "STUDENT_ONLY"


def test_unrelated_pair_never_paired_by_size_or_position():
    items = resolve_batch([("数学 教师版.docx", docx()), ("物理 学生版.docx", docx())])
    assert [item.input_version for item in items] == ["TEACHER_ONLY", "STUDENT_ONLY"]


def test_normalized_versions_keep_meaningful_topic_number():
    items = resolve_batch([("专题12 教师版（修订版）v2.docx", docx()),
                           ("专题12 学生版.docx", docx())])
    assert len(items) == 1 and items[0].topic == "专题12"
    assert items[0].input_version == "TEACHER_AND_STUDENT"


def test_separate_mode_generates_independent_sources():
    items = resolve_batch([(name, docx()) for name in ("专题 教师版.docx", "专题 学生版.docx")], "separate")
    assert [item.input_version for item in items] == ["TEACHER_ONLY", "STUDENT_ONLY"]


def test_conflicting_filename_roles_fail_only_that_source():
    items = resolve_batch([(name, docx()) for name in ("专题 教师版学生版.docx", "专题B 学生版.docx")])
    assert len(items) == 2
    assert sum(item.error is not None for item in items) == 1


def test_unlabelled_single_uses_c1_content_evidence():
    result = resolve_batch([("专题.docx", docx("【答案】A", "【解析】步骤"))])[0]
    assert result.input_version == "TEACHER_ONLY" and result.evidence == "answer_analysis_content"


def test_no_supported_docs_and_invalid_archives_rejected():
    with pytest.raises(BatchInputError, match="没有可处理"):
        expand_uploads([("空.zip", archive([("说明.txt", b"text")]))])
    with pytest.raises(BatchInputError, match="INVALID_ZIP"):
        expand_uploads([("坏.zip", b"not-a-zip")])


def test_teacher_and_student_strong_keyword_variants():
    for teacher, student in (("教师版", "学生版"), ("解析版", "原卷版"),
                             ("答案版", "空白版"), ("教师用", "学生用")):
        items = resolve_batch([(f"专题 {teacher}.docx", docx()), (f"专题 {student}.docx", docx())])
        assert len(items) == 1 and items[0].input_version == "TEACHER_AND_STUDENT"


def test_bad_deflate_stream_fails_only_its_logical_item():
    malformed = bytearray(docx())
    with zipfile.ZipFile(io.BytesIO(malformed)) as package:
        entry = package.getinfo("word/document.xml")
        assert entry.compress_type == zipfile.ZIP_DEFLATED
        offset = entry.header_offset
        name_length = int.from_bytes(malformed[offset + 26:offset + 28], "little")
        extra_length = int.from_bytes(malformed[offset + 28:offset + 30], "little")
        payload = offset + 30 + name_length + extra_length
    # BTYPE=3 is forbidden by DEFLATE; preserve remaining bytes and ZIP tables.
    malformed[payload] = (malformed[payload] & ~7) | 7
    with zipfile.ZipFile(io.BytesIO(malformed)) as package:
        with pytest.raises(zlib.error):
            package.read("word/document.xml")
    items = resolve_batch([("损坏 教师版.docx", bytes(malformed)),
                           ("正常 学生版.docx", docx())])
    assert len(items) == 2 and items[0].error
    assert items[1].input_version == "STUDENT_ONLY" and not items[1].error


def test_role_words_inside_topics_never_create_false_pair():
    items = resolve_batch([("教师素养 教师版.docx", docx()),
                           ("学生素养 学生版.docx", docx())])
    assert [(item.topic, item.input_version) for item in items] == [
        ("教师素养", "TEACHER_ONLY"), ("学生素养", "STUDENT_ONLY")]


@pytest.mark.parametrize("name,topic,role", [
    ("教师素养.docx", "教师素养", None),
    ("学生用电安全 学生版.docx", "学生用电安全", "student"),
    ("教师版型研究 教师用.docx", "教师版型研究", "teacher"),
    ("教师版 函数.docx", "函数", "teacher"),
    ("函数（学生版）.docx", "函数", "student"),
    ("函数teacherful.docx", "函数teacherful", None),
])
def test_role_labels_require_safe_boundaries(name, topic, role):
    assert topic_identity(name) == (topic, role)


class LegacyGBKInfo(zipfile.ZipInfo):
    def _encodeFilenameFlags(self):
        return self.filename.encode("gbk"), self.flag_bits & ~0x800


def test_windows_gbk_zip_without_utf8_flag_matches_chinese_pair():
    uploads = archive([(LegacyGBKInfo("数学/导数 教师版.docx"), docx()),
                       (LegacyGBKInfo("学生/导数 学生版.docx"), docx()),
                       (LegacyGBKInfo("临时/~$导数 教师版.docx"), docx())])
    with zipfile.ZipFile(io.BytesIO(uploads)) as package:
        assert all(not entry.flag_bits & 0x800 for entry in package.infolist())
        assert package.infolist()[0].filename != "数学/导数 教师版.docx"
    items = resolve_batch([("中文旧式压缩包.zip", uploads)])
    assert len(items) == 1
    assert items[0].topic == "导数" and items[0].input_version == "TEACHER_AND_STUDENT"
    assert items[0].teacher_source.name == "导数 教师版.docx"
    assert items[0].student_source.name == "导数 学生版.docx"


def test_gbk_zip_still_rejects_traversal():
    uploads = archive([(LegacyGBKInfo("../导数 教师版.docx"), docx())])
    with pytest.raises(BatchInputError, match="UNSAFE_ZIP_PATH"):
        expand_uploads([("旧式.zip", uploads)])


class UnflaggedUTF8Info(zipfile.ZipInfo):
    def _encodeFilenameFlags(self):
        return self.filename.encode("utf-8"), self.flag_bits & ~0x800


def test_unflagged_ambiguous_encoding_fails_explicitly():
    uploads = archive([(UnflaggedUTF8Info("导数.docx"), docx())])
    with pytest.raises(BatchInputError, match="AMBIGUOUS_ZIP_NAME_ENCODING"):
        expand_uploads([("未标编码.zip", uploads)])

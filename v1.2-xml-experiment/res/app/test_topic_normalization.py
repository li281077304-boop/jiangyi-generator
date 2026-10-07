from pathlib import Path
import sys

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))

from topic_normalization import normalize_display_topic  # noqa: E402


def test_topic_keeps_core_and_strips_known_course_and_marketing_tail():
    assert normalize_display_topic(
        "专题12.4 一次函数的实际应用（高效培优讲义）数学新教材沪科版八年级上册 期末复习"
    ) == "专题12.4 一次函数的实际应用"


def test_topic_strips_roles_and_extension_without_rewriting_core():
    assert normalize_display_topic("专题12.4 一次函数的实际应用（解析版）.docx") == \
        "专题12.4 一次函数的实际应用"


def test_topic_without_recognized_metadata_is_preserved():
    assert normalize_display_topic("一次函数的实际应用专题") == "一次函数的实际应用专题"


def test_topic_preserves_exam_topic_and_content_parentheses():
    assert normalize_display_topic(
        "专题2 中考压轴题函数综合（原卷版）"
    ) == "专题2 中考压轴题函数综合"
    assert normalize_display_topic("函数性质（定义域与值域）") == \
        "函数性质（定义域与值域）"


def test_empty_topic_has_safe_display_fallback():
    assert normalize_display_topic("") == "讲义"

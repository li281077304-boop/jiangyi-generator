"""Diagnostics cannot grant review authority or guess repeated-node mapping."""
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/studentizer_audit'))
from audit_real_pairs import source_identity, exact_subsequence_count, expanded_fingerprint


def test_pair_topic_uses_explicit_suffix_without_subject_order():
    assert source_identity('目录/第2章（原卷版）.docx') == ('第2章', 'student')
    assert source_identity('第2章解析版.docx') == ('第2章', 'teacher')
    assert source_identity('未知.docx') == (None, None)
    assert source_identity('第3章（原卷版）.docx')[0] != source_identity('第2章解析版.docx')[0]


def test_exact_subsequence_counts_ambiguity_without_selecting_first():
    assert exact_subsequence_count(['q', 'a', 'r'], ['q', 'r']) == 1
    assert exact_subsequence_count(['q', 'q', 'r'], ['q', 'r']) == 2
    assert exact_subsequence_count(['q', 'r'], ['r', 'q']) == 0
    assert exact_subsequence_count(['q', 'r'], ['q', 'different']) == 0


def test_expanded_names_ignore_prefix_only_and_preserve_content_and_structure():
    a = etree.fromstring(b'<a:p xmlns:a="urn:test"><a:r val="x">same</a:r></a:p>')
    b = etree.fromstring(b'<b:p xmlns:b="urn:test"><b:r val="x">same</b:r></b:p>')
    assert expanded_fingerprint(a) == expanded_fingerprint(b)
    b[0].set('val', 'changed')
    assert expanded_fingerprint(a) != expanded_fingerprint(b)
    b[0].set('val', 'x'); b[0].text = 'different'
    assert expanded_fingerprint(a) != expanded_fingerprint(b)

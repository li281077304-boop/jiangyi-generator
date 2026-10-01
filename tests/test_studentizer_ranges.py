"""Generic exact physical owner API; independent synthetic oracle and refusal gates."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import sys
import zipfile

from docx import Document
from lxml import etree
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v1.2-xml-experiment/res/app'))
from studentizer import prepare_student, element_sha256, TAG, FALLBACK
from studentizer_ranges import ReviewedPhysicalBody, ReviewedAnswerRange, PhysicalRangeSemantics


def fixture(extra=None, missing=()):
    doc = Document()
    for text in ['Knowledge and diagram', 'Prompt with all options', 'Solution without marker',
                 'Continuation without color or role', 'Next prompt']:
        doc.add_paragraph(text)
    buf = BytesIO(); doc.save(buf)
    with zipfile.ZipFile(BytesIO(buf.getvalue())) as package:
        info = package.infolist(); parts = {i.filename: package.read(i.filename) for i in info}
    root = etree.fromstring(parts['word/document.xml'])
    body = root.find(TAG('body'))
    if extra:
        extra(body)
    source = BytesIO()
    with zipfile.ZipFile(source, 'w') as package:
        for i in info:
            package.writestr(i, etree.tostring(root, xml_declaration=True, encoding='UTF-8') if i.filename == 'word/document.xml' else parts[i.filename])
    data = source.getvalue()
    expected = deepcopy(root)
    for i in (3, 2):
        expected.find(TAG('body')).remove(expected.find(TAG('body'))[i])
    rows = tuple(ReviewedPhysicalBody(i, element_sha256(n), 'REMOVE' if i in (2, 3) else 'RETAIN',
                                     'Independent reviewed ownership', 'review-A', 'physical-A' if i in (1, 2, 3) else None)
                 for i, n in enumerate(body))
    semantics = PhysicalRangeSemantics(sha256(data).hexdigest(), 'review-A', rows,
                                      (ReviewedAnswerRange('physical-A', 1, 1, 2, 3,
                                                           'Complete solution ownership', 'review-A'),),
                                      element_sha256(expected), missing)
    return data, semantics


def refuse(tmp_path, data, semantics, code=None):
    output = tmp_path / 'student.docx'
    result = prepare_student(data, semantics, output)
    assert result.status == FALLBACK and not output.exists() and not result.mutations
    if code:
        assert result.reason_code == code
    return result


def test_generic_multi_paragraph_range_without_marker_or_qg(tmp_path):
    data, semantics = fixture()
    source = tmp_path / 'source.docx'; source.write_bytes(data)
    output = tmp_path / 'student.docx'
    result = prepare_student(source, semantics, output)
    assert result.status == 'XML_PREPARED' and len(result.mutations) == 2
    assert source.read_bytes() == data
    with zipfile.ZipFile(output) as after, zipfile.ZipFile(BytesIO(data)) as before:
        assert after.namelist() == before.namelist()
        assert all(after.read(n) == before.read(n) for n in before.namelist() if n != 'word/document.xml')
        assert element_sha256(etree.fromstring(after.read('word/document.xml'))) == semantics.expected_document_sha256


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'fingerprint', 'decision', 'reason', 'review', 'owner', 'range', 'expected', 'source'])
def test_exact_ledger_contract_failures(tmp_path, case):
    data, s = fixture(); rows = list(s.body)
    if case == 'missing': rows.pop()
    if case == 'duplicate': rows.append(rows[0])
    if case == 'fingerprint': rows[2] = replace(rows[2], sha256='0'*64)
    if case == 'decision': rows[2] = replace(rows[2], decision='MAYBE')
    if case == 'reason': rows[2] = replace(rows[2], reason='')
    if case == 'review': rows[2] = replace(rows[2], review_id='different')
    if case == 'owner': rows[2] = replace(rows[2], owner_id='different')
    s = replace(s, body=tuple(rows))
    if case == 'range': s = replace(s, ranges=(replace(s.ranges[0], answer_end=4),))
    if case == 'expected': s = replace(s, expected_document_sha256='0'*64)
    if case == 'source': s = replace(s, source_sha256='0'*64)
    refuse(tmp_path, data, s)


@pytest.mark.parametrize('tag', ['object', 'oMath', 'drawing', 'bookmarkStart', 'fldChar', 'hyperlink', 'tbl', 'sdt', 'ins'])
def test_removal_any_nonplain_structure_refuses(tmp_path, tag):
    def extra(body):
        namespace = 'http://schemas.openxmlformats.org/officeDocument/2006/math' if tag == 'oMath' else 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        etree.SubElement(body[2], '{%s}%s' % (namespace, tag))
    data, s = fixture(extra)
    refuse(tmp_path, data, s, 'STUDENTIZER_MIXED_CONTENT_UNSUPPORTED')


def bookmarks(body, referenced=False, broken=False):
    start = etree.SubElement(body[1], TAG('bookmarkStart')); start.set(TAG('id'), '9'); start.set(TAG('name'), 'topic')
    if not broken:
        end = etree.SubElement(body[4], TAG('bookmarkEnd')); end.set(TAG('id'), '9')
    if referenced:
        link = etree.SubElement(body[0], TAG('hyperlink')); link.set(TAG('anchor'), 'topic')


def test_unreferenced_paired_bookmark_endpoints_preserved(tmp_path):
    data, s = fixture(bookmarks)
    assert prepare_student(data, s, tmp_path/'student.docx').status == 'XML_PREPARED'


@pytest.mark.parametrize('kind', ['referenced', 'unpaired', 'field-crossing', 'field-unpaired', 'revision', 'unresolved-rel'])
def test_boundary_dependencies_fail_closed(tmp_path, kind):
    def extra(body):
        if kind in ('referenced', 'unpaired'):
            bookmarks(body, kind == 'referenced', kind == 'unpaired')
        elif kind.startswith('field'):
            f = etree.SubElement(body[1], TAG('fldChar')); f.set(TAG('fldCharType'), 'begin')
            etree.SubElement(body[1], TAG('instrText')).text = 'TOC \\o "1-3"'
            if kind == 'field-crossing':
                f = etree.SubElement(body[4], TAG('fldChar')); f.set(TAG('fldCharType'), 'end')
        elif kind == 'revision':
            etree.SubElement(body[0], TAG('ins'))
        else:
            link = etree.SubElement(body[0], TAG('hyperlink'))
            link.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', 'missing')
    data, s = fixture(extra)
    refuse(tmp_path, data, s, 'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')


def test_preserved_inherited_missing_target_requires_exact_acknowledgement(tmp_path):
    def extra(body):
        link = etree.SubElement(body[0], TAG('hyperlink')); link.set(TAG('anchor'), 'existing-source-defect')
    data, s = fixture(extra)
    refuse(tmp_path, data, s, 'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')
    s = replace(s, inherited_missing_bookmark_targets=('existing-source-defect',))
    assert prepare_student(data, s, tmp_path/'allowed.docx').status == 'XML_PREPARED'
    refuse(tmp_path, data, replace(s, inherited_missing_bookmark_targets=('invented',)))


def test_output_no_overwrite_and_same_source_refused(tmp_path):
    data, s = fixture()
    source = tmp_path/'source.docx'; source.write_bytes(data)
    assert prepare_student(source, s, source).status == FALLBACK and source.read_bytes() == data
    output = tmp_path/'output.docx'; output.write_bytes(b'untouched')
    assert prepare_student(source, s, output).status == FALLBACK and output.read_bytes() == b'untouched'


@pytest.mark.parametrize('kind', ['anchor', 'REF', 'PAGEREF'])
def test_cross_story_dependency_is_not_ignored(tmp_path, kind):
    data, s = fixture(bookmarks)
    other = etree.Element(TAG('hdr'))
    if kind == 'anchor':
        node = etree.SubElement(other, TAG('hyperlink')); node.set(TAG('anchor'), 'topic')
    else:
        node = etree.SubElement(other, TAG('fldSimple')); node.set(TAG('instr'), kind + ' topic')
    buffer = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(buffer, 'w') as updated:
        for item in original.infolist():
            updated.writestr(item, original.read(item.filename))
        updated.writestr('word/header1.xml', etree.tostring(other))
    data = buffer.getvalue()
    refuse(tmp_path, data, replace(s, source_sha256=sha256(data).hexdigest()),
           'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')


@pytest.mark.parametrize('broken', [False, True])
def test_cross_story_only_balanced_page_counters_survive_exactly(tmp_path, broken):
    data, s = fixture()
    other = etree.Element(TAG('ftr'))
    for instruction in [' PAGE \\* MERGEFORMAT ', 'NUMPAGES']:
        node = etree.SubElement(other, TAG('fldChar')); node.set(TAG('fldCharType'), 'begin')
        etree.SubElement(other, TAG('instrText')).text = instruction
        node = etree.SubElement(other, TAG('fldChar')); node.set(TAG('fldCharType'), 'separate')
        if not broken:
            node = etree.SubElement(other, TAG('fldChar')); node.set(TAG('fldCharType'), 'end')
    footer = etree.tostring(other)
    buffer = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(buffer, 'w') as updated:
        for item in original.infolist():
            updated.writestr(item, original.read(item.filename))
        updated.writestr('word/footer1.xml', footer)
    data = buffer.getvalue(); s = replace(s, source_sha256=sha256(data).hexdigest())
    if broken:
        refuse(tmp_path, data, s, 'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')
    else:
        output = tmp_path/'student.docx'
        assert prepare_student(data, s, output).status == 'XML_PREPARED'
        with zipfile.ZipFile(output) as package:
            assert package.read('word/footer1.xml') == footer


@pytest.mark.parametrize('cross_story', [False, True])
def test_relationship_fragment_dependency_is_not_silently_allowed(tmp_path, cross_story):
    def extra(body):
        if not cross_story:
            link = etree.SubElement(body[0], TAG('hyperlink'))
            link.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', 'fragment')
    data, s = fixture(extra)
    buffer = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(buffer, 'w') as updated:
        for item in original.infolist():
            content = original.read(item.filename)
            if item.filename == 'word/_rels/document.xml.rels' and not cross_story:
                root = etree.fromstring(content)
                rel = etree.SubElement(root, '{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')
                rel.set('Id', 'fragment'); rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink')
                rel.set('Target', '#topic'); rel.set('TargetMode', 'External')
                content = etree.tostring(root)
            updated.writestr(item, content)
        if cross_story:
            root = etree.Element(TAG('hdr')); link = etree.SubElement(root, TAG('hyperlink'))
            link.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', 'fragment')
            updated.writestr('word/header1.xml', etree.tostring(root))
    data = buffer.getvalue()
    refuse(tmp_path, data, replace(s, source_sha256=sha256(data).hexdigest()),
           'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')


@pytest.mark.parametrize('simple', [True, False])
def test_toc_bookmark_dependency_cannot_cover_removed_answers(tmp_path, simple):
    def extra(body):
        bookmarks(body)
        if simple:
            field = etree.SubElement(body[0], TAG('fldSimple')); field.set(TAG('instr'), 'TOC \\b topic')
        else:
            field = etree.SubElement(body[0], TAG('fldChar')); field.set(TAG('fldCharType'), 'begin')
            etree.SubElement(body[0], TAG('instrText')).text = 'TOC \\b topic'
            field = etree.SubElement(body[0], TAG('fldChar')); field.set(TAG('fldCharType'), 'end')
    data, s = fixture(extra)
    source = tmp_path/'source.docx'; source.write_bytes(data)
    result = refuse(tmp_path, source, s, 'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')
    assert result.reason_detail == 'deletion changes referenced bookmark scope'
    assert source.read_bytes() == data


@pytest.mark.parametrize('instruction', [
    'TOC \\b topic \\b other', 'TOC \\b', 'TOC \\b "topic',
    'TOC \\b "two names"', 'TOC \\t "Custom,1"', 'TOC \\h \\h',
    'TOC \\o "4-1"', 'TOC unexplained'])
def test_toc_ambiguous_unknown_or_complex_parameters_refuse(tmp_path, instruction):
    def extra(body):
        field = etree.SubElement(body[0], TAG('fldSimple')); field.set(TAG('instr'), instruction)
    data, s = fixture(extra)
    refuse(tmp_path, data, s, 'STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED')


def test_toc_bookmark_outside_deletion_can_be_preserved(tmp_path):
    def extra(body):
        start = etree.SubElement(body[0], TAG('bookmarkStart')); start.set(TAG('id'), '7'); start.set(TAG('name'), 'safe_topic')
        end = etree.SubElement(body[0], TAG('bookmarkEnd')); end.set(TAG('id'), '7')
        field = etree.SubElement(body[4], TAG('fldSimple')); field.set(TAG('instr'), 'TOC \\b "safe_topic" \\o "1-3" \\h \\u')
    data, s = fixture(extra)
    assert prepare_student(data, s, tmp_path/'student.docx').status == 'XML_PREPARED'

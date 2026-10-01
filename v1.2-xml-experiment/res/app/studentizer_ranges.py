"""Standalone exact reviewed physical ranges; no QG inference or provider.

Content authority is the caller's independently reviewed exhaustive ledger and
exact expected root on identical source bytes. Colors, markers and roles do not
authorize any mutation. Production orchestration does not use this contract.
"""
from dataclasses import dataclass
import re

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
TAG = lambda n: '{%s}%s' % (W, n)


@dataclass(frozen=True)
class ReviewedPhysicalBody:
    index: int
    sha256: str
    decision: str
    reason: str
    review_id: str
    owner_id: str | None = None


@dataclass(frozen=True)
class ReviewedAnswerRange:
    owner_id: str
    prompt_start: int
    prompt_end: int
    answer_start: int
    answer_end: int
    reason: str
    review_id: str


@dataclass(frozen=True)
class PhysicalRangeSemantics:
    source_sha256: str
    review_id: str
    body: tuple[ReviewedPhysicalBody, ...]
    ranges: tuple[ReviewedAnswerRange, ...]
    expected_document_sha256: str
    # Exact inherited missing targets acknowledged by independent review.
    # Never permits new missing references or any source structure repair.
    inherited_missing_bookmark_targets: tuple[str, ...] = ()


def _boundaries(root, removed, parts, inherited_missing):
    from studentizer import _refuse, element_sha256
    body = root.find(TAG('body'))
    starts, ends, names, targets, signature, fields = {}, {}, {}, [], [], []
    relationships = {}
    if 'word/_rels/document.xml.rels' in parts:
        relroot = etree.fromstring(parts['word/_rels/document.xml.rels'],
                                  etree.XMLParser(resolve_entities=False, no_network=True))
        for rel in relroot:
            identity = rel.get('Id')
            if not identity or identity in relationships:
                _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'invalid relationship identity')
            relationships[identity] = rel

    # Main-body bookmark contents can be referenced from other stories. Those
    # parts remain byte-identical, but their dependencies must not be ignored.
    # Cross-story fields support only unchanged balanced scalar page counters.
    for name, data in parts.items():
        if not name.startswith('word/') or not name.endswith('.xml') or name == 'word/document.xml':
            continue
        other = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
        stack = []
        def scalar(instruction):
            if not re.fullmatch(r'\s*(?:PAGE|NUMPAGES)(?:\s+\\\*\s+MERGEFORMAT)?\s*', instruction, re.I):
                _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'cross-story field dependency unsupported: ' + name)
            signature.append(('cross-story-pagefield', name, instruction))
        for node in other.iter():
            if node.tag == TAG('fldChar'):
                kind = node.get(TAG('fldCharType'))
                if kind == 'begin' and not stack:
                    stack.append({'instruction': '', 'separated': False})
                elif kind == 'separate' and stack and not stack[-1]['separated']:
                    stack[-1]['separated'] = True
                elif kind == 'end' and stack:
                    scalar(stack.pop()['instruction'])
                else:
                    _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'unbalanced/nested cross-story field: ' + name)
            elif node.tag == TAG('instrText'):
                if not stack or stack[-1]['separated']:
                    _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'cross-story instruction outside field: ' + name)
                stack[-1]['instruction'] += node.text or ''
            elif node.tag == TAG('fldSimple'):
                if stack:
                    _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'nested cross-story field: ' + name)
                scalar(node.get(TAG('instr'), ''))
        if stack:
            _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'unclosed cross-story field: ' + name)
        for node in other.iter(TAG('hyperlink')):
            if node.get('{%s}id' % R):
                _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', 'cross-story hyperlink relationship unsupported: ' + name)
            anchor = node.get(TAG('anchor'))
            if anchor:
                targets.append(anchor)
                signature.append(('cross-story-anchor', name, element_sha256(node)))

    def fail(detail):
        _refuse('STUDENTIZER_BOUNDARY_DEPENDENCY_UNSUPPORTED', detail)

    def field_instruction(instruction):
        tokens = re.findall(r'"[^"\r\n]*"|\S+', instruction.strip())
        if not tokens:
            fail('empty field instruction')
        command = tokens[0].upper()
        if command not in {'TOC', 'REF', 'PAGEREF', 'HYPERLINK'}:
            fail('unsupported field dependency: ' + command)
        target = None
        if command in {'REF', 'PAGEREF'}:
            if len(tokens) < 2 or tokens[1].startswith('\\'):
                fail('missing reference field target')
            target = tokens[1].strip('"')
        elif command == 'HYPERLINK':
            local = [i for i, t in enumerate(tokens) if t.lower() == '\\l']
            if len(local) != 1 or local[0] + 1 >= len(tokens):
                fail('only explicit local hyperlink fields are supported')
            target = tokens[local[0] + 1].strip('"')
        if target:
            targets.append(target)
        signature.append(('field', instruction, target))

    unsupported = {'ins', 'del', 'moveFrom', 'moveTo', 'sdt', 'customXml',
                   'commentRangeStart', 'commentRangeEnd', 'commentReference',
                   'footnoteReference', 'endnoteReference', 'txbxContent'}
    for index, child in enumerate(body):
        for node in child.iter():
            if not isinstance(node.tag, str):
                fail('non-element XML node')
            local = etree.QName(node).localname
            if local in unsupported or local.endswith('Change'):
                fail('unsupported boundary system: ' + local)
            if node.tag in {TAG('bookmarkStart'), TAG('bookmarkEnd')}:
                identity = node.get(TAG('id'))
                if not identity or index in removed:
                    fail('missing/removable bookmark endpoint')
                if node.tag == TAG('bookmarkStart'):
                    name = node.get(TAG('name'))
                    if identity in starts or not name or name in names:
                        fail('duplicate bookmark id/name')
                    starts[identity] = index
                    names[name] = identity
                else:
                    if identity not in starts or identity in ends:
                        fail('unpaired/out-of-order bookmark end')
                    ends[identity] = index
                signature.append(('bookmark', element_sha256(node)))
            elif node.tag == TAG('fldChar'):
                if index in removed:
                    fail('removable field marker')
                kind = node.get(TAG('fldCharType'))
                if kind == 'begin':
                    fields.append({'start': index, 'instruction': '', 'separated': False})
                elif kind == 'separate':
                    if not fields or fields[-1]['separated']:
                        fail('unpaired/repeated field separator')
                    fields[-1]['separated'] = True
                elif kind == 'end':
                    if not fields:
                        fail('unpaired field end')
                    field = fields.pop()
                    if any(i in removed for i in range(field['start'], index + 1)):
                        fail('deletion intersects retained field scope')
                    field_instruction(field['instruction'])
                else:
                    fail('unknown field marker')
                signature.append(('field-marker', element_sha256(node)))
            elif node.tag == TAG('instrText'):
                if not fields or fields[-1]['separated'] or index in removed:
                    fail('instruction outside preserved field-code scope')
                fields[-1]['instruction'] += node.text or ''
            elif node.tag == TAG('fldSimple'):
                if index in removed or fields:
                    fail('removable/nested simple field')
                field_instruction(node.get(TAG('instr'), ''))
                signature.append(('simple-field', element_sha256(node)))
            elif node.tag == TAG('hyperlink'):
                if index in removed:
                    fail('removable hyperlink')
                anchor, identity = node.get(TAG('anchor')), node.get('{%s}id' % R)
                if anchor:
                    targets.append(anchor)
                if identity:
                    rel = relationships.get(identity)
                    if rel is None or rel.get('Type') != R + '/hyperlink' or not rel.get('Target'):
                        fail('unresolved hyperlink relationship')
                    if rel.get('TargetMode') != 'External' or '#' in rel.get('Target'):
                        fail('internal/fragment hyperlink relationship dependency unsupported')
                if not anchor and not identity:
                    fail('hyperlink without explicit target')
                signature.append(('hyperlink', element_sha256(node)))
    if fields or starts.keys() != ends.keys():
        fail('unclosed field/bookmark')
    missing = set(targets) - names.keys()
    if len(set(inherited_missing)) != len(inherited_missing) or missing != set(inherited_missing):
        fail('unacknowledged/changed inherited missing bookmark targets')
    for target in set(targets) & names.keys():
        identity = names[target]
        if any(i in removed for i in range(starts[identity], ends[identity] + 1)):
            fail('deletion changes referenced bookmark scope')
    # Unreferenced paired bookmarks may encompass removed answers. Their exact
    # endpoint subtrees/order survive; no reference depends on changed content.
    return tuple(signature), tuple(sorted(missing))


def plan_physical_ranges(root, semantics, parts):
    from studentizer import _refuse, element_sha256
    body = root.find(TAG('body'))
    if body is None:
        _refuse('STUDENTIZER_XML_PREPARATION_FAILED', 'document body missing')
    children = list(body)
    if not semantics.review_id or not re.fullmatch('[0-9a-f]{64}', semantics.expected_document_sha256):
        _refuse('STUDENTIZER_COVERAGE_UNPROVEN', 'independent review/after-root identity missing')
    ledger = {}
    for row in semantics.body:
        if type(row.index) is not int or row.index in ledger or not 0 <= row.index < len(children):
            _refuse('STUDENTIZER_COVERAGE_INCOMPLETE', 'duplicate/invalid body address')
        if (row.decision not in {'RETAIN', 'REMOVE'} or not row.reason.strip()
                or row.review_id != semantics.review_id):
            _refuse('STUDENTIZER_COVERAGE_UNPROVEN', 'unreviewed body decision')
        if row.sha256 != element_sha256(children[row.index]):
            _refuse('STUDENTIZER_SOURCE_IDENTITY_MISMATCH', 'body fingerprint mismatch')
        ledger[row.index] = row
    if set(ledger) != set(range(len(children))) or not semantics.ranges:
        _refuse('STUDENTIZER_COVERAGE_INCOMPLETE', 'require exhaustive body ledger and reviewed removals')
    removed, owners = set(), set()
    for scope in semantics.ranges:
        addresses = (scope.prompt_start, scope.prompt_end, scope.answer_start, scope.answer_end)
        if (not scope.owner_id or scope.owner_id in owners or not scope.reason.strip()
                or scope.review_id != semantics.review_id
                or any(type(i) is not int for i in addresses)
                or not 0 <= scope.prompt_start <= scope.prompt_end < scope.answer_start <= scope.answer_end < len(children)):
            _refuse('STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN', 'invalid reviewed physical owner/range')
        owners.add(scope.owner_id)
        if any(ledger[i].decision != 'RETAIN' or ledger[i].owner_id != scope.owner_id
               for i in range(scope.prompt_start, scope.prompt_end + 1)):
            _refuse('STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN', 'complete prompt must be retained with same physical owner')
        for i in range(scope.answer_start, scope.answer_end + 1):
            if i in removed or ledger[i].decision != 'REMOVE' or ledger[i].owner_id != scope.owner_id:
                _refuse('STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN', 'overlapping/removal ownership mismatch')
            removed.add(i)
    if removed != {i for i, row in ledger.items() if row.decision == 'REMOVE'}:
        _refuse('STUDENTIZER_COVERAGE_INCOMPLETE', 'range/ledger deletion coverage mismatch')
    plain = {TAG(n) for n in ('p', 'pPr', 'pStyle', 'jc', 'spacing', 'ind', 'keepNext',
             'keepLines', 'widowControl', 'r', 'rPr', 'rStyle', 'b', 'bCs', 'i', 'iCs',
             'u', 'color', 'sz', 'szCs', 'rFonts', 'lang', 't', 'textAlignment', 'vertAlign')}
    for i in removed:
        if children[i].tag != TAG('p') or any(n.tag not in plain for n in children[i].iter()):
            _refuse('STUDENTIZER_MIXED_CONTENT_UNSUPPORTED', 'range contains non-plain paragraph subtree at body ' + str(i))
    before_boundaries = _boundaries(root, removed, parts, semantics.inherited_missing_bookmark_targets)
    retained = [element_sha256(n) for i, n in enumerate(children) if i not in removed]
    mutations = tuple({'operation': 'remove_reviewed_plain_paragraph', 'body_index': i,
                       'before_sha256': ledger[i].sha256, 'owner_id': ledger[i].owner_id,
                       'review_id': semantics.review_id, 'reason': ledger[i].reason}
                      for i in sorted(removed))
    for i in sorted(removed, reverse=True):
        body.remove(children[i])
    if _boundaries(root, set(), parts, semantics.inherited_missing_bookmark_targets) != before_boundaries:
        _refuse('STUDENTIZER_PRESERVATION_CHECK_FAILED', 'boundary dependency inventory changed')
    if element_sha256(root) != semantics.expected_document_sha256:
        _refuse('STUDENTIZER_GOLDEN_COMPARISON_FAILED', 'after-root does not match independent Golden')
    return retained, mutations

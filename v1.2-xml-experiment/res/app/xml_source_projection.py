"""Immutable projection of equivalent textbox compatibility branches only."""
from copy import deepcopy
import hashlib
from pathlib import Path
import zipfile
from lxml import etree

MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
W14 = '{http://schemas.microsoft.com/office/word/2010/wordml}'


def _identity(node):
    # These two editor identities do not encode content or formatting.
    attrs = tuple(sorted((k, v) for k, v in node.attrib.items()
                         if k not in (W14 + 'paraId', W14 + 'textId')))
    return (node.tag, attrs, node.text or '', node.tail or '',
            tuple(_identity(child) for child in node))


def project_equivalent_textboxes(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('Projection cannot overwrite original source')
    payload = source.read_bytes()
    with zipfile.ZipFile(source) as archive:
        root = etree.fromstring(archive.read('word/document.xml'))
        changed = []
        for ac in list(root.iter(MC + 'AlternateContent')):
            if ac.getroottree().getroot() is not root:
                continue
            choices, fallbacks = ac.findall(MC + 'Choice'), ac.findall(MC + 'Fallback')
            if len(choices) != 1 or len(fallbacks) != 1:
                continue
            choice, fallback = choices[0], fallbacks[0]
            cb, fb = list(choice.iter(W + 'txbxContent')), list(fallback.iter(W + 'txbxContent'))
            if not cb or len(cb) != len(fb) or any(_identity(a) != _identity(b) for a,b in zip(cb,fb)):
                continue
            # No external-to-textbox visible text or media may be discarded.
            safe = True
            for branch, boxes in ((choice, cb), (fallback, fb)):
                inside = {n for box in boxes for n in box.iter()}
                for n in branch.iter():
                    local = etree.QName(n).localname
                    if n not in inside and (n.tag == W + 't' or local in ('blip','imagedata','OLEObject')):
                        safe = False
            if not safe:
                continue
            parent = ac.getparent()
            index = parent.index(ac)
            for child in choice:
                parent.insert(index, deepcopy(child))
                index += 1
            parent.remove(ac)
            changed.append({'textbox_count': len(cb), 'content_and_formatting_equivalent': True})
        evidence = {'version': 'EQUIVALENT_TEXTBOX_BRANCH_V1', 'source_sha256': hashlib.sha256(payload).hexdigest(),
                    'changes': changed, 'source_path': str(source)}
        if not changed:
            return source, {**evidence, 'status': 'UNCHANGED'}
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
            for info in archive.infolist():
                data = (etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                        if info.filename == 'word/document.xml' else archive.read(info.filename))
                target.writestr(info, data)
    return output, {**evidence, 'status': 'PROJECTED', 'projection_path': str(output),
                    'projection_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}

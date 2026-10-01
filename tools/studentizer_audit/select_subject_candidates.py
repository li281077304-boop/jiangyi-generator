"""Read-only, non-authoritative subject screening; no Golden or transformation."""
from collections import Counter
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import re
import sys
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
from semantic_facade import analyze_source

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
TAG = lambda n: '{%s}%s' % (W, n)
MARKER = re.compile(r'^【(?:答案|解析|详解|解答)】')
PROMPT = re.compile(r'^(?:\d+[．.、]|[【（(]?例\s*\d+)')
# Screening snapshot of R7 physical-range whitelist; not content authority.
PLAIN = {TAG(n) for n in ('p','pPr','pStyle','jc','spacing','ind','keepNext',
    'keepLines','widowControl','r','rPr','rStyle','b','bCs','i','iCs','u','color',
    'sz','szCs','rFonts','lang','t','textAlignment','vertAlign')}
NON_TEXT = {'drawing','pict','object','oMath','OLEObject','txbxContent','tbl'}


def screen(data):
    snapshot = analyze_source(data)
    with zipfile.ZipFile(BytesIO(data)) as package:
        parts = {n: package.read(n) for n in package.namelist()}
    root = etree.fromstring(parts['word/document.xml'],
        etree.XMLParser(resolve_entities=False, no_network=True))
    body = list(root.find(TAG('body')))
    seq_to_body = {b.seq: b.body_idx for b in snapshot.document.blocks}
    units = {u['id']: u for u in snapshot.units}
    spans, mapped, complex_count = [], 0, 0
    for u in snapshot.units:
        physical = []
        for start, end in u.get('spans', []):
            pair = []
            for ref in (start, end):
                if not snapshot.node_index.exists(ref):
                    raise ValueError('missing frozen endpoint: ' + ref)
                seq = int(re.match(r'^b(\d+)', ref)[1])
                pair.append(seq_to_body[seq])
                mapped += 1
                complex_count += not bool(re.fullmatch(r'b\d+', ref))
            physical.append(pair)
        spans.append({'id':u['id'], 'role':u['role'], 'parent':u.get('parent'),
                      'spans':u.get('spans',[]), 'top_body_spans':physical})
    marker_rows, unsupported = [], Counter()
    for i, child in enumerate(body):
        text = ''.join(child.itertext()).strip()
        if child.tag != TAG('p') or not MARKER.match(text):
            continue
        tags = Counter(etree.QName(n).localname for n in child.iter() if isinstance(n.tag,str) and n.tag not in PLAIN)
        unsupported.update(tags)
        covering = [r for r in spans if any(a <= i <= b for a,b in r['top_body_spans'])]
        chains = []
        for r in covering:
            chain, visited, cursor = [], set(), r['id']
            while cursor in units and cursor not in visited:
                visited.add(cursor); u = units[cursor]
                chain.append([cursor,u['role']]); cursor = u.get('parent')
            chains.append(chain)
        marker_rows.append({'body_index':i, 'preview':text[:100],
            'plain_whitelist':not tags, 'has_nontext':any(t in NON_TEXT for t in tags),
            'covering_units':[r['id'] for r in covering], 'parent_chains':chains})
    prompts = []
    qg_nodes = set()
    for u in snapshot.units:
        if u['role'] == 'question_group':
            for a,b in u.get('spans',[]):
                qg_nodes.update(snapshot.node_index.interval(a,b))
    for n in snapshot.node_index.nodes:
        if n.kind == 'paragraph' and PROMPT.match(n.text.strip()):
            prompts.append({'node_id':n.id, 'body_index':seq_to_body[int(re.match(r'^b(\d+)',n.id)[1])],
                            'covered_by_frozen_qg':n.id in qg_nodes, 'preview':n.text[:100]})
    features = Counter(etree.QName(n).localname for n in root.iter() if isinstance(n.tag,str))
    cross_story = {name: Counter(etree.QName(n).localname for n in etree.fromstring(value).iter() if isinstance(n.tag,str))
        for name,value in parts.items() if re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml',name)}
    return {'source_sha256':sha256(data).hexdigest(), 'body_children':len(body),
        'role_counts':dict(Counter(u['role'] for u in snapshot.units)),
        'frozen_spans':spans, 'validated_endpoint_count':mapped,
        'complex_endpoint_count':complex_count, 'endpoint_missing':0,
        'features':{n:features[n] for n in ('p','tbl','oMath','OLEObject','drawing','txbxContent',
                    'numPr','bookmarkStart','bookmarkEnd','fldChar','sdt','ins','del','commentReference',
                    'footnoteReference','endnoteReference')},
        'field_instructions':[''.join(n.itertext()) for n in root.iter(TAG('instrText'))],
        'cross_story_features':cross_story,
        'cross_story_field_instructions':{name:[''.join(n.itertext()) for n in etree.fromstring(parts[name]).iter(TAG('instrText'))]
                                          for name in cross_story},
        'dedicated_markers':marker_rows, 'marker_unsupported_tags':dict(unsupported),
        'marked_nontext_count':sum(r['has_nontext'] for r in marker_rows),
        'marked_plain_count':sum(r['plain_whitelist'] for r in marker_rows),
        'prompt_candidates':prompts,
        'physical_question_total':'NOT_ESTABLISHED', 'complete_answer_ownership':'NOT_ESTABLISHED',
        'authority':'CANDIDATE_ONLY', 'full_content_review':False, 'approved':False,
        'current_capability':'BLOCKED', 'production_provider':False,
        'performance':'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--pages',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    manifest = json.loads((args.corpus/'baseline_inputs.json').read_text(encoding='utf-8'))
    checked = []
    for meta in manifest['samples']:
        path = args.corpus/meta['source_path']
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != meta['source_sha256']:
            raise ValueError('source provenance mismatch: '+meta['sample_id'])
        checked.append(meta['sample_id'])
    pages = json.loads(args.pages.read_text(encoding='utf-8-sig'))
    selected = {}
    for sid in ('X012','X023'):
        meta = next(m for m in manifest['samples'] if m['sample_id']==sid)
        selected[sid] = {'provenance':meta, **screen((args.corpus/meta['source_path']).read_bytes())}
        page = next(p for p in pages if p['id']==sid)
        if page['source_sha256'].lower()!=meta['source_sha256'] or not page['source_unchanged']:
            raise ValueError('page evidence provenance mismatch: '+sid)
        selected[sid]['source_page_count_evidence'] = page
    report = {'scope':'READ_ONLY_SUBJECT_SELECTION', 'authority':'CANDIDATE_ONLY',
        'corpus_hashes_verified':checked, 'selected':selected, 'wps_source_pages':pages,
        'chief_verdict':'PENDING','performance':'NOT_RUN'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({sid:{k:v for k,v in row.items() if k in ('source_sha256','body_children',
        'role_counts','validated_endpoint_count','complex_endpoint_count','features',
        'field_instructions','marked_nontext_count','marked_plain_count','marker_unsupported_tags')}
        for sid,row in selected.items()},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

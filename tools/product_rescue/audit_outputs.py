"""Post-generation resource conservation measurement; never substitutes for WPS visual review."""
import argparse, hashlib, json, posixpath, re, zipfile
from pathlib import Path
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'

def inspect(path):
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read('word/document.xml'))
        paragraphs = [''.join(n.text or '' for n in p.iter(W+'t')) for p in root.iter(W+'p')]
        # Package media may include unused resources and old header logos.
        # Measure only resources actually referenced by the source main story.
        rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
        refs = {v for n in root.iter() for k,v in n.attrib.items() if k.startswith(rns)}
        rels = etree.fromstring(z.read('word/_rels/document.xml.rels'))
        targets = {posixpath.normpath(posixpath.join('word',n.get('Target'))) for n in rels
                   if n.get('Id') in refs and n.get('TargetMode') != 'External'}
        images = {hashlib.sha256(z.read(n)).hexdigest() for n in targets if n.startswith('word/media/')}
        ole = {hashlib.sha256(z.read(n)).hexdigest() for n in targets if n.startswith('word/embeddings/')}
    normalize = lambda s: re.sub(r'\s+', '', s)
    return dict(text=normalize(''.join(paragraphs)), paragraphs=[normalize(p) for p in paragraphs],
                images=images, ole=ole, equations=len(list(root.iter(M+'oMath'))), tables=len(list(root.iter(W+'tbl'))))

def audit(source, output):
    a, b = inspect(source), inspect(output)
    missing = [dict(source_paragraph=i, sha256=hashlib.sha256(t.encode()).hexdigest(), length=len(t))
               for i,t in enumerate(a['paragraphs']) if len(t) >= 40 and t not in b['text']]
    return dict(source=str(source), output=str(output), source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                final_sha256=hashlib.sha256(Path(output).read_bytes()).hexdigest(),
                long_paragraphs_missing=missing, source_images=len(a['images']), missing_image_hashes=sorted(a['images']-b['images']),
                source_ole=len(a['ole']), missing_ole_hashes=sorted(a['ole']-b['ole']),
                source_equations=a['equations'], output_equations=b['equations'],
                source_tables=a['tables'], output_tables=b['tables'],
                evidence_scope='static content/resource conservation; not visual or pair correspondence PASS')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--resume', action='store_true')
    args = ap.parse_args()
    previous = json.loads(args.out.read_text(encoding='utf-8')) if args.resume and args.out.exists() else []
    cached = {(r['job_id'],r['role']):r for r in previous}
    rows = []
    for path in args.jobs.glob('*/job.json'):
        job = json.loads(path.read_text(encoding='utf-8'))
        if job.get('status') != 'done' or job.get('is_batch'):
            continue
        for role in ('teacher','student'):
            output = job.get(role+'_output_path')
            source = job.get(role+'_source_path')
            if source and output:
                prior = cached.get((job['job_id'],role))
                if prior and prior['final_sha256'] == hashlib.sha256(Path(output).read_bytes()).hexdigest() and prior['source_sha256'] == hashlib.sha256(Path(source).read_bytes()).hexdigest():
                    rows.append(prior)
                else:
                    rows.append(dict(job_id=job['job_id'], role=role, renderer=job.get('renderer'), **audit(source,output)))
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(outputs=len(rows), missing_images=sum(bool(r['missing_image_hashes']) for r in rows),
                         missing_ole=sum(bool(r['missing_ole_hashes']) for r in rows),
                         missing_long_text=sum(bool(r['long_paragraphs_missing']) for r in rows))))

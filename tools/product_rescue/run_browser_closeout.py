"""Frozen corpus through actual browser DOM uploads to the normal EXE."""
import argparse, hashlib, json, subprocess, time, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'docs/v2/integration/fixtures/v12-finalization-evaluation/frozen_evaluation_manifest.json'
CLI=Path(os.environ['PLAYWRIGHT_CLI_PATH'])


def source_path(member):
    original = Path(member.get('materialized_path') or member['path'])
    if original.is_file():
        return original.resolve()
    workspace = Path(os.environ.get('AI_WORKSPACE', 'H:/AI-Workspace'))
    text = str(original).replace('\\', '/')
    if text.lower().startswith('c:/xml-uat/'):
        candidate = workspace / 'uat/xml-uat' / text[len('C:/xml-uat/'):]
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError('Immutable source unavailable: ' + str(original))


def run_case(cfg,out):
    out.mkdir(parents=True,exist_ok=True)
    path=out/(cfg['id']+'.js')
    path.write_text((ROOT/'tools/product_rescue/browser_closeout_case.js').read_text(encoding='utf-8').replace('__CONFIG__',json.dumps(cfg,ensure_ascii=False)),encoding='utf-8')
    subprocess.run(['node',str(CLI),'snapshot'],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
    t=time.perf_counter()
    proc=subprocess.run(['node',str(CLI),'run-code','--filename',str(path)],cwd=ROOT,capture_output=True,encoding='utf-8',timeout=900)
    (out/(cfg['id']+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode or '### Result' not in proc.stdout:
        raise RuntimeError('Browser case failed: '+cfg['id']+' '+proc.stdout[-700:])
    row=json.loads(proc.stdout.split('### Result')[1].strip().splitlines()[0]);row['wall_seconds']=round(time.perf_counter()-t,3)
    (out/(cfg['id']+'.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    j=row.get('job',{});print(cfg['id'],row['http_status'],j.get('status',row.get('status')),j.get('renderer'),flush=True)
    return row


def frozen_cases(indices=None, singles=False):
    data=json.loads(MANIFEST.read_text(encoding='utf-8'))
    prior=json.loads((ROOT/'docs/v2/integration/fixtures/final-prepackage-20261007/coverage_summary.json').read_text(encoding='utf-8'))
    for i,t in enumerate(data['fixed_topics']+data['additional_topics']):
        if indices is not None and i not in indices:continue
        members=t['members']
        if len(members)>2 and not singles:
            hashes={m['sha256'] for m in next(x for x in prior['topics'] if x['topic']==t['topic_identity'])['sources']}
            members=[m for m in members if m['sha256'] in hashes]
        for m in members:
            path=source_path(m)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise RuntimeError('SOURCE_HASH_CHANGED')
        subject='化学' if i<5 else ('数学' if i in (7,8,9) or 13<=i<=23 else '物理')
        names=' '.join(m['filename'] for m in members)
        grade=next((g for g in ['七年级','八年级','九年级'] if g in names),'七年级' if subject=='数学' else '九年级')
        for template in ['1v1','class']:
            groups=[[m] for m in members] if singles else [members]
            for n,group in enumerate(groups):
                yield dict(id=f'topic-{i:02}-{template}'+(f'-single-{n}' if singles else ''),topic=t['topic_identity'],
                           template=template,subject=subject,grade=grade,
                           files=[str(source_path(m)) for m in group],
                           source_hashes=[m['sha256'] for m in group],wait=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--indices',type=int,nargs='+');p.add_argument('--singles',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    mh=hashlib.sha256(MANIFEST.read_bytes()).hexdigest();rows=[]
    if a.resume and (a.out/'summary.json').exists():
        old=json.loads((a.out/'summary.json').read_text(encoding='utf-8'))
        if old['head']!=head or old['manifest_sha256']!=mh:raise RuntimeError('RESUME_CANDIDATE_CHANGED')
        rows=old['results']
    for cfg in frozen_cases(a.indices,a.singles):
        if any(r['case']==cfg['id'] for r in rows):continue
        rows.append(run_case(cfg,a.out))
        (a.out/'summary.json').write_text(json.dumps(dict(head=head,manifest_sha256=mh,results=rows),ensure_ascii=False,indent=2),encoding='utf-8')

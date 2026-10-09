"""Extend the immutable 33-topic evaluation with the two confirmed raw uploads."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/v2/integration/fixtures/v12-finalization-evaluation/frozen_evaluation_manifest.json'
ENGLISH=Path('H:/AI-Workspace/uat/slotted-closeout-20261009/english_sources.json')
OUT=ROOT/'docs/v2/integration/fixtures/slotted-closeout-20261009'
base=json.loads(BASE.read_text(encoding='utf-8'))
topics=base['fixed_topics']+base['additional_topics']
members=json.loads(ENGLISH.read_text(encoding='utf-8'))
for prefix in ['专题10','专题12']:
    group=[]
    for member in members:
        p=Path(member['path'])
        if not p.name.startswith(prefix):continue
        assert hashlib.sha256(p.read_bytes()).hexdigest()==member['sha256']
        group.append({'path':str(p),'filename':p.name,'sha256':member['sha256'],
                      'role':'teacher' if '解析版' in p.name else 'student',
                      'origin':'immutable corpus recovery; matches raw upload provenance'})
    assert len(group)==2
    topics.append({'topic_identity':prefix+' '+('语法填空' if prefix=='专题10' else '完形填空'),
                   'members':group,'subject':'英语','grade':'高三'})
assert len(topics)==35
OUT.mkdir(exist_ok=True,parents=True)
(OUT/'manifest35.json').write_text(json.dumps({'base33_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
    'required_pass':32,'total_topics':35,'topics':topics},ensure_ascii=False,indent=2),encoding='utf-8')
print('35 topics frozen; required pass 32')

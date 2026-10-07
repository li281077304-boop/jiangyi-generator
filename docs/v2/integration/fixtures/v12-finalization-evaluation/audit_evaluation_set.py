import hashlib, json, re, unicodedata, zipfile, xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

OUT=Path(r'C:\xml-uat\v12-finalization-coverage-20261007')
BASE=Path(r'C:\xml-uat\stage3-expansion\baseline_inputs.json')
REC=Path(r'C:\xml-uat\incident-source-recovery-20261006\recursive_recovery_manifest.json')
EXTRACT=Path(r'C:\xml-uat\incident-source-recovery-20261006\extracted')
ROOTS=[Path(r'C:\Users\Administrator\Desktop\工作\讲义生成器\训练文件'),Path(r'C:\xml-uat\c4-product-recovery\corpus')]
FIXED=json.loads(BASE.read_text(encoding='utf-8'))['samples']
fixed_hashes={s['source_sha256'].lower() for s in FIXED}
def topic_key(name):
    n=unicodedata.normalize('NFKC',Path(name).stem)
    n=re.sub(r'[（(](?:原卷版|解析版|答案版|教师版|学生版|含答案|无答案)[）)]\s*$','',n)
    n=re.sub(r'(?:原卷版|解析版|答案版|教师版|学生版|含答案|无答案)\s*$','',n)
    n=re.sub(r'\s+',' ',n).strip(' _-—')
    return n
fixed_topics={topic_key(s['name']) for s in FIXED}
incident_key=topic_key('九年级上学期物理期末复习（易错精选60题27大考点）（原卷版）.docx')
fixed_topics.add(incident_key)

# Collect in precisely the prior recovery script order: listed roots, sorted root paths,
# ZIP infolist order, depth-first recursion. Read archives for names only; use existing extraction.
ordered=[]; traversal_errors=[]; serial=0; archive_count=0; member_count=0

def safe_member(name):
    if '\x00' in name: return False
    q=name.replace('\\','/')
    p=PurePosixPath(q)
    return not (p.is_absolute() or re.match(r'^[A-Za-z]:',q) or any(x in ('.','..') for x in p.parts))

def walk_zip(zpath, depth, chain):
    global serial,archive_count,member_count
    try:
        z=zipfile.ZipFile(zpath)
    except Exception as e:
        traversal_errors.append({'zip':str(zpath),'error':repr(e)}); return
    serial+=1; archive_id=serial; archive_count+=1
    folder=EXTRACT/(f'archive_{archive_id:05d}_d{depth:02d}')
    try:
        with z:
            for info in z.infolist():
                if info.is_dir(): continue
                member_count+=1
                if not safe_member(info.filename):
                    traversal_errors.append({'zip':str(zpath),'member':info.filename,'error':'unsafe member path'}); continue
                materialized=folder.joinpath(*PurePosixPath(info.filename.replace('\\','/')).parts)
                next_chain=chain+[{'zip_path':str(zpath),'member_name':info.filename,'materialized_path':str(materialized)}]
                suffix=materialized.suffix.lower()
                if suffix=='.zip':
                    if materialized.exists(): walk_zip(materialized,depth+1,next_chain)
                    else: traversal_errors.append({'zip':str(zpath),'member':info.filename,'error':'existing extraction missing'})
                elif suffix in ('.docx','.doc'):
                    if materialized.exists():
                        ordered.append({'path':materialized,'source_chain':next_chain,'root':str(ROOTS[0])})
                    else: traversal_errors.append({'zip':str(zpath),'member':info.filename,'error':'existing extraction missing'})
    except Exception as e:
        traversal_errors.append({'zip':str(zpath),'error':repr(e)})

for root in ROOTS:
    if not root.exists():
        traversal_errors.append({'root':str(root),'error':'root missing'}); continue
    for p in sorted(root.rglob('*')):
        try:
            if not p.is_file(): continue
            if p.suffix.lower()=='.zip':
                walk_zip(p,0,[{'corpus_root':str(root),'outer_zip':str(p)}])
            elif p.suffix.lower() in ('.docx','.doc'):
                ordered.append({'path':p,'source_chain':[{'corpus_root':str(root),'direct_path':str(p)}],'root':str(root)})
        except Exception as e: traversal_errors.append({'path':str(p),'error':repr(e)})

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def inspect(path):
    out={'docx_package_valid':False,'main_story_paragraphs':None,'text_chars':None,'title_evidence':[],'answer_marker_counts':{},'inspect_error':None}
    if path.suffix.lower()!='.docx':
        out['inspect_error']='legacy .doc is not inspected as OOXML'; return out
    try:
        with zipfile.ZipFile(path) as z:
            xml=z.read('word/document.xml')
        root=ET.fromstring(xml)
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        body=root.find('.//w:body',ns)
        paras=[] if body is None else [''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in body.findall('.//w:p',ns)]
        txt='\n'.join(paras)
        out.update(docx_package_valid=True,main_story_paragraphs=len(paras),text_chars=len(txt),title_evidence=[x.strip() for x in paras if x.strip()][:5])
        out['answer_marker_counts']={x:txt.count(x) for x in ('答案','解析','【答案】','【解析】','解：')}
    except Exception as e: out['inspect_error']=repr(e)
    return out

def role(name, text):
    n=name
    if re.search(r'(原卷版|学生版|无答案)',n): return 'student_or_original_paper'
    if re.search(r'(解析版|答案版|教师版|含答案)',n): return 'teacher_or_answer_rich'
    markers=sum(text.get('answer_marker_counts',{}).get(x,0) for x in ('答案','解析','【答案】','【解析】','解：'))
    return 'teacher_or_answer_rich' if markers>=3 else 'unknown_or_unmarked'

# Resolve unique additional topics from the deterministic corpus stream. First eligible
# appearance fixes topic order. Keep all later members for those selected topics.
records=[]; seen_hashes=set(fixed_hashes); topic_order=[]; topic_members={}; rejected=[]
for ix,item in enumerate(ordered,1):
    p=item['path']; name=p.name; h=sha(p); key=topic_key(name)
    if h in seen_hashes:
        rejected.append({'order':ix,'path':str(p),'sha256':h,'topic_key':key,'reason':'duplicate SHA already in frozen 27 or earlier corpus occurrence'}); continue
    seen_hashes.add(h)
    if key in fixed_topics:
        rejected.append({'order':ix,'path':str(p),'sha256':h,'topic_key':key,'reason':'topic belongs to frozen set or incident pair'}); continue
    if not p.suffix.lower()=='.docx':
        rejected.append({'order':ix,'path':str(p),'sha256':h,'topic_key':key,'reason':'legacy .doc excluded from DOCX evaluation population'}); continue
    info=inspect(p)
    rec={'corpus_order':ix,'path':str(p),'filename':name,'topic_identity':key,'sha256':h,'bytes':p.stat().st_size,'role':role(name,info),'source_root':item['root'],'source_chain':item['source_chain'],'eligibility':{'raw_corpus_provenance':True,'outside_generated_result_runtime_publication_and_test_fixture_roots':True,'duplicate_hash':False,'duplicate_topic':False,'docx_extension':True,'docx_package_valid':info['docx_package_valid'],'topic_not_fixed_or_incident':True},'content_evidence':info}
    if key not in topic_members:
        topic_order.append(key); topic_members[key]=[]
    topic_members[key].append(rec)
    if len(topic_order)>=20: pass

selected_topics=topic_order[:20]
selected=[]
for n,key in enumerate(selected_topics,1):
    members=topic_members[key]
    selected.append({'topic_order':n,'topic_identity':key,'members':members})
manifest={
 'schema_version':1,'audit_date':'2026-10-07','purpose':'Freeze first 20 distinct additional raw topics for V1.2 finalization; metadata-only audit, no renderer run.',
 'deterministic_order':{'roots_in_order':[str(x) for x in ROOTS],'within_root':'Python Path.rglob then lexicographic sorted path order; ZIP members in archive infolist order; depth-first nested ZIP traversal; direct files in root sorted path order. This matches the existing recover_nested_zips.py ordering.','selection':'first occurrence of each normalized filename topic key after excluding frozen source hashes/topics, incident topic, duplicates, and non-DOCX legacy files; later role variants for selected topics are retained.'},
 'frozen_set':{'baseline_manifest':str(BASE),'sample_count':len(FIXED),'distinct_filename_topic_identity_count':len(fixed_topics),'sample_ids':[x['sample_id'] for x in FIXED],'topics':[{'topic_identity':topic_key(FIXED[0]['name'])} ]},
 'incident_pair':{'counted_once':True,'topic_identity':incident_key,'sample_ids':['X005','X006'],'members':[{'role':'student_or_original_paper','sha256':'c66f88d26f1fae9306442ef8e1f55a807d3e705edaa37e57334d4499d3c6a009','origin_chain':next(x['origin_chain'] for x in FIXED if x['sample_id']=='X005')},{'role':'teacher_or_answer_rich','sha256':'9395c5bddf78dff2edd087a30212ad40b40e17a3e5c14b224b2043ade3a60410','origin_chain':next(x['origin_chain'] for x in FIXED if x['sample_id']=='X006')}]},
 'fixed_topics':[{'topic_identity':k,'sample_ids':[x['sample_id'] for x in FIXED if topic_key(x['name'])==k]} for k in sorted(fixed_topics)],
 'roots_searched':[str(x) for x in ROOTS],
 'root_scan_stats':{'source_entries_seen':len(ordered),'archives_read':archive_count,'archive_members_seen':member_count,'traversal_errors':traversal_errors,'candidate_topics_found':len(topic_order)},
 'additional_topic_target':20,'additional_topics_selected':len(selected),'additional_topics':selected,
 'shortage':max(0,20-len(selected)),
 'eligibility_and_caveats':['No DOCX generation, renderer, or input modification was performed.','Extraction materialized copies are referenced only to inspect bytes; each record points back to original corpus archive/member chain.','The selected population includes corrupt or unsupported DOCX package members if present; package validity is evidence, not a selection filter.','This audit has not established current-commit XML success rates.'],
 'excluded_candidates_summary':{'duplicate_hash_or_fixed_or_incident_or_legacy_count':len(rejected),'first_100':rejected[:100]}
}
# Populate concise fixed topic file names by normalized identities from manifest.
def fixed_role(sample):
    n=sample['name']
    if re.search(r'(原卷版|学生版|无答案)',n): return 'student_or_original_paper'
    if re.search(r'(解析版|答案版|教师版|含答案)',n): return 'teacher_or_answer_rich'
    return 'unknown_or_unmarked'
manifest['fixed_topics']=[{'topic_identity':k,'sample_ids':[x['sample_id'] for x in FIXED if topic_key(x['name'])==k], 'members':[{'sample_id':x['sample_id'],'filename':x['name'],'sha256':x['source_sha256'],'bytes':x['source_bytes'],'role':fixed_role(x),'materialized_path':str(BASE.parent/'sources'/x['source_path'].split('/')[-1]),'origin_chain':x['origin_chain']} for x in FIXED if topic_key(x['name'])==k]} for k in sorted({topic_key(x['name']) for x in FIXED})]
# Note topic identity count as actual role-deduplicated count, incident is one of it.
manifest['frozen_set']['distinct_filename_topic_identity_count']=len(manifest['fixed_topics'])
json_path=OUT/'frozen_evaluation_manifest.json'
json_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Markdown human-readable report.
lines=['# V1.2 XML Finalization — Fixed Evaluation Set Audit','',f"Audit date: 2026-10-07",'', '## Frozen baseline', '',f"- Baseline input manifest: `{BASE}`",f"- Frozen source files: {len(FIXED)} (X001–X027)",f"- Distinct topic identities after teacher/student/answer role deduplication: {len(manifest['fixed_topics'])}",f"- Incident pair: X005/X006, counted as one topic `{incident_key}`",'', 'The phrase “27 fixed raw corpus topics” is ambiguous in existing evidence: the frozen manifest has 27 source files but only 13 distinct topic identities after role variants are collapsed. This report preserves both counts instead of treating teacher/student role variants as extra topics.','', '## Additional raw topic selection', '',f"- Search roots: {', '.join('`'+str(x)+'`' for x in ROOTS)}",f"- Deterministic source entries examined: {len(ordered)}",f"- Archive members seen: {member_count} in {archive_count} ZIPs",f"- Distinct additional eligible DOCX topics selected: {len(selected)} of 20 requested",f"- Shortage: {max(0,20-len(selected))}", '', 'Order follows the listed raw corpus roots, sorted root paths, ZIP member order, and depth-first nested ZIP traversal, matching the previous recovery script. Topic order is fixed by first eligible occurrence; role variants for a selected topic are recorded as members.','', '## Frozen 13 distinct topic identities (27 source files)','']
for t in manifest['fixed_topics']:
    lines.append(f"- {t['topic_identity']} ({','.join(t['sample_ids'])})")
lines += ['', '## Additional selected topics','']
for t in selected:
    roles=', '.join(f"{m['role']} `{m['sha256']}` ({m['filename']})" for m in t['members'])
    lines.append(f"{t['topic_order']}. **{t['topic_identity']}** — {roles}")
lines += ['', '## Blockers and limits','',f"- Archive traversal errors: {len(traversal_errors)}; details are in the frozen manifest.", '- Existing extraction copies were used read-only; original sources were not altered.', '- No XML renderer was run, so this audit makes no XML success-rate claim.', '- Old route/output scans are stale relative to the current commit and are not interpreted as current candidate results.', '']
(OUT/'evaluation_set_audit.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'manifest':str(json_path),'report':str(OUT/'evaluation_set_audit.md'),'fixed_files':len(FIXED),'fixed_topics':len(manifest['fixed_topics']),'incident_topic':incident_key,'source_entries':len(ordered),'archives':archive_count,'members':member_count,'candidate_topics':len(topic_order),'selected_topics':len(selected),'shortage':max(0,20-len(selected)),'traversal_errors':len(traversal_errors),'first_topics':[x['topic_identity'] for x in selected[:20]]},ensure_ascii=False,indent=2))



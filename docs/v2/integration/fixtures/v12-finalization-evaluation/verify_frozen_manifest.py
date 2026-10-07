import hashlib,json,zipfile
from pathlib import Path
import sys
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().with_name('frozen_evaluation_manifest.json')
j=json.loads(p.read_text(encoding='utf-8'))
def sha(b): return hashlib.sha256(b).hexdigest()
checks=[]
for topic in j['additional_topics']:
 for m in topic['members']:
  final=m['source_chain'][-1]
  raw=Path(final['zip_path'])
  with zipfile.ZipFile(raw) as z: data=z.read(final['member_name'])
  extracted=Path(final['materialized_path']).read_bytes()
  checks.append({'topic':topic['topic_identity'],'member':m['filename'],'manifest_sha':m['sha256'],'archive_member_sha':sha(data),'materialized_sha':sha(extracted),'same':sha(data)==m['sha256']==sha(extracted)})
fixed=[]
base=json.loads(Path(r'C:\xml-uat\stage3-expansion\baseline_inputs.json').read_text(encoding='utf-8'))
for s in base['samples']:
 f=Path(r'C:\xml-uat\stage3-expansion')/s['source_path']
 fixed.append({'id':s['sample_id'],'expected':s['source_sha256'],'actual':sha(f.read_bytes()),'same':sha(f.read_bytes())==s['source_sha256']})
print(json.dumps({'extra_member_count':len(checks),'extra_hash_mismatches':[x for x in checks if not x['same']],'fixed_file_count':len(fixed),'fixed_hash_mismatches':[x for x in fixed if not x['same']],'manifest_sha256':sha(p.read_bytes()),'report_sha256':sha(p.with_name('evaluation_set_audit.md').read_bytes())},ensure_ascii=False,indent=2))

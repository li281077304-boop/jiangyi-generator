"""Keep the rejected three-file envelope; measure its independent sources and original frozen pair separately."""
import json
from pathlib import Path
from run_xml_rescue import ROOT, app, run_topic

out = Path(r'C:\xml-uat\product-rescue-three-source-20261008')
out.mkdir(parents=True, exist_ok=True)
app.config.update(TESTING=False, C0_RUN_JOBS_SYNCHRONOUSLY=True,
                  C0_DISABLE_JOB_SUBMISSION=False, RESULT_ROOT=out / 'results',
                  RUNTIME_ROOT=out / 'jobs', C0_FORCE_FALLBACK_REASON=None)
manifest = json.loads((ROOT / 'docs/v2/integration/fixtures/v12-finalization-evaluation/frozen_evaluation_manifest.json').read_text(encoding='utf-8'))
topic = next(t for t in manifest['fixed_topics'] if len(t['members']) > 2)
original = json.loads((ROOT / 'docs/v2/integration/fixtures/final-prepackage-20261007/coverage_summary.json').read_text(encoding='utf-8'))
prior = next(t for t in original['topics'] if t['topic'] == topic['topic_identity'])
pair_hashes = {m['sha256'] for m in prior['sources']}
rows = []
for template in ('1v1', 'class'):
    rows.append(run_topic(dict(topic, members=[m for m in topic['members'] if m['sha256'] in pair_hashes]), template, out))
    for member in topic['members']:
        mode = 'teacher' if 'teacher' in member['role'] else 'student'
        row = run_topic(dict(topic, members=[member]), template, out, mode=mode)
        row['source_sha256'] = member['sha256']
        row['source_filename'] = member['filename']
        rows.append(row)
    (out / 'summary.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')

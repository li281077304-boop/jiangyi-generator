"""Frozen-topic production evaluation; no fixture or algorithm mutation."""
from pathlib import Path
import argparse, hashlib, io, json, sys, time, subprocess

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'v1.2-xml-experiment/res/app'
sys.path[:0] = [str(APP / 'webapp'), str(APP)]
from app import app


def run_topic(topic, template, folder, *, mode='pair'):
    members = topic['members']
    if mode != 'pair':
        members = [member for member in members if ('teacher' in member['role']) == (mode == 'teacher')]
    names = ' '.join(member['filename'] for member in topic['members'])
    subject = next((name for name in ('化学', '物理', '数学', '英语', '生物') if name in names), '化学' if '物质的变化' in names else '物理')
    grade = next((name for name in ('高三', '高二', '高一', '九年级', '八年级', '七年级') if name in names), '九年级')
    uploads = []
    for member in members:
        path = Path(member['materialized_path'])
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != member['sha256']:
            raise RuntimeError('SOURCE_HASH_CHANGED: ' + str(path))
        uploads.append((io.BytesIO(payload), Path(member['filename'].replace('\\', '/')).name))
    stamp = time.perf_counter()
    client = app.test_client()
    response = client.post('/api/jobs', data={'files': uploads, 'template_type': template,
        'subject': subject, 'grade': grade, 'academic_year': '2026-2027学年',
        'handout_type': '复习讲义', 'engine_mode': 'auto'})
    created = response.get_json()
    result = dict(topic=topic['topic_identity'], template=template, mode=mode,
                  http_status=response.status_code, created=created)
    if response.status_code != 202:
        result.update(status='rejected', error=created.get('error'), renderer=None)
    if created and created.get('job_id'):
        job = client.get('/api/jobs/' + created['job_id']).get_json()
        result.update(job_id=job['job_id'], status=job['status'], renderer=job.get('renderer'),
            renderer_route=job.get('renderer_route'), fallback_reason=job.get('fallback_reason'),
            error=job.get('error'), degradation=job.get('xml_degradation'),
            student_preparation=job.get('student_preparation'), output_paths=job.get('output_paths', []),
            package_validation=job.get('package_validation'), product_integrity=job.get('product_integrity'),
            warnings=job.get('warnings', []))
    result['elapsed_seconds'] = round(time.perf_counter() - stamp, 3)
    output = folder / ('%s-%s-%s.json' % (template, mode, created.get('job_id', 'rejected')))
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: result.get(key) for key in ('topic','template','mode','status','renderer','error','elapsed_seconds')}, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--templates', nargs='+', default=['1v1', 'class'])
    parser.add_argument('--modes', nargs='+', default=['pair'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app.config.update(TESTING=False, C0_RUN_JOBS_SYNCHRONOUSLY=True,
        C0_DISABLE_JOB_SUBMISSION=False, RESULT_ROOT=args.output / 'results',
        RUNTIME_ROOT=args.output / 'jobs', C0_FORCE_FALLBACK_REASON=None)
    manifest = ROOT / 'docs/v2/integration/fixtures/v12-finalization-evaluation/frozen_evaluation_manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    rows = []
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for topic in data['fixed_topics'][:args.limit]:
        for template in args.templates:
            for mode in args.modes:
                rows.append(run_topic(topic, template, args.output, mode=mode))
                (args.output / 'summary.json').write_text(json.dumps({'head': head,
                    'denominator_topics': len(data['fixed_topics']),
                    'submitted_topics': len({row['topic'] for row in rows}),
                    'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    'results': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.output / 'summary.json').write_text(json.dumps({'head': head, 'denominator_topics': len(data['fixed_topics']),
        'submitted_topics': min(args.limit, len(data['fixed_topics'])),
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'results': rows}, ensure_ascii=False, indent=2), encoding='utf-8')

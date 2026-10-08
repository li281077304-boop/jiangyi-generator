"""Archive honest denominators, actual routes and deliverable hashes."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = Path(r'C:\xml-uat\product-rescue-final-20261008')
DEST = ROOT / 'docs/v2/integration/fixtures/product-rescue-20261008'
DEST.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def counts(rows):
    return dict(submissions=len(rows), xml=sum(r['status']=='done' and r['renderer']=='XML' for r in rows),
                compatibility=sum(r['status']=='done' and r['renderer']=='V0.9' for r in rows),
                rejected_or_failed=sum(r['status']!='done' for r in rows))

data = read(r'C:\xml-uat\product-rescue-33-20261008\summary.json')
extra = read(r'C:\xml-uat\product-rescue-three-source-20261008\summary.json')
three_topic = extra[0]['topic']
pairs = [r for r in data['results'] if r['mode']=='pair' and r['topic']!=three_topic] + [r for r in extra if r['mode']=='pair']
singles = [r for r in data['results'] if r['mode']!='pair' and r['topic']!=three_topic] + [r for r in extra if r['mode']!='pair']
combined = pairs + singles
topics = sorted({r['topic'] for r in pairs})
topic_rows = []
for topic in topics:
    rows = [r for r in pairs if r['topic']==topic]
    topic_rows.append(dict(topic=topic, both_templates_xml=all(r['status']=='done' and r['renderer']=='XML' for r in rows),
                          both_templates_delivered=all(r['status']=='done' and len(r['output_paths'])==2 for r in rows),
                          templates=[dict(template=r['template'],status=r['status'],renderer=r['renderer'],
                                          fallback_reason=r.get('fallback_reason'),error=r.get('error'),job_id=r.get('job_id')) for r in rows]))
tiers = Counter()
reasons = Counter()
details = Counter()
for row in combined:
    if row['renderer']=='XML' and row['status']=='done':
        for role, evidence in (row.get('degradation') or {}).items():
            tiers[evidence['selected_tier']] += 1
    if row.get('fallback_reason'):
        reasons[row['fallback_reason']] += 1
        raw = Path(r'C:\xml-uat\product-rescue-33-20261008\jobs') / row['job_id'] / 'job.json'
        if raw.exists():
            details[read(raw).get('fallback_detail', 'UNRECORDED')] += 1
coverage = dict(code_head=data['head'],manifest_sha256=data['manifest_sha256'],denominator_topics=33,
                raw_all_member_envelopes=counts(data['results']),supplemental_three_source_submissions=counts(extra),
                canonical_frozen_pair=counts(pairs),individual_sources=counts(singles),
                pair_by_template={t:counts([r for r in pairs if r['template']==t]) for t in ('1v1','class')},
                topics_xml_both_templates=sum(t['both_templates_xml'] for t in topic_rows),
                topics_delivered_both_templates=sum(t['both_templates_delivered'] for t in topic_rows),
                xml_tiers_per_delivered_role=dict(tiers),compatibility_reasons_per_submission=dict(reasons),topics=topic_rows,
                compatibility_exact_details=dict(details),
                evidence_scope='Actual production API submissions and final DOCX; all 33 inputs counted. Not 33-topic visual WPS acceptance.',
                parameter_limit='Batch harness inferred cover subject from filenames; ambiguous subjects defaulted to physics. This is not a subject recognition test. Browser representative cases selected their correct subject explicitly.')
print(json.dumps({k:v for k,v in coverage.items() if k not in ('topics','parameter_limit')},ensure_ascii=False,indent=2))
(DEST/'coverage_final.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
curated = []
for row in data['results'] + extra:
    item = {k:row.get(k) for k in ('topic','template','mode','http_status','job_id','status','renderer','fallback_reason','error','elapsed_seconds','degradation','warnings')}
    item['outputs'] = [dict(path=p,bytes=Path(p).stat().st_size,sha256=sha256(Path(p).read_bytes()).hexdigest()) for p in row.get('output_paths',[])]
    curated.append(item)
(DEST/'corpus_submissions.json').write_text(json.dumps(curated,ensure_ascii=False,indent=2),encoding='utf-8')
browser = []
for log in ('browser-1v1-evidence.log','browser-class-evidence.log','core-1v1-evidence.log','core-class-evidence.log','extracted-exe-evidence.log','fallback-exe-evidence.log'):
    text = (EXTERNAL/log).read_text(encoding='utf-8-sig')
    value = json.loads(text.split('### Result')[1].strip().splitlines()[0])
    browser.append(dict(log=log,evidence=value))
(DEST/'final_exe_browser.json').write_text(json.dumps(browser,ensure_ascii=False,indent=2),encoding='utf-8')
original_wps = read(EXTERNAL/'wps/wps_evidence.json')
corrected_wps = read(EXTERNAL/'wps-correct-fallback/wps_evidence.json')
(DEST/'wps_final.json').write_text(json.dumps(dict(
    roundtrip_records=original_wps[:8] + corrected_wps,
    historical_wrong_cover_parameters=original_wps[8:],
    scope='Open/SaveAs/Close/Reopen/PDF success is not complete content acceptance. Oxygen teacher textbox omissions confirmed separately; no compatibility content PASS.'
),ensure_ascii=False,indent=2),encoding='utf-8')
(DEST/'package_final.json').write_text(json.dumps(read(r'D:\讲义生成器测试包\20261008\RC_PACKAGE_REPORT.json'),ensure_ascii=False,indent=2),encoding='utf-8')
conservation = read(EXTERNAL/'textbox-conservation-final.json')
(DEST/'content_audit.json').write_text(json.dumps(dict(
    measurement_head='6cdbff191f10ce0645e9b3a4fceb32aa0959d87b',
    safeguard_head='3a76f9aaf3867dfe90f4f740025562ba4ef6103f',
    corpus_outputs_checked=len(conservation),
    rejected_on_current_safeguard=[r for r in conservation if r['unproven']],
    long_text_classification=read(EXTERNAL/'long-text-classification.json'),
    exact_source_evidence='wps-source-check/oxygen-original-teacher.pdf page 3',
    exact_output_evidence='wps-correct-fallback/correct-chemistry-v09-0.pdf page 5',
    conclusion='Confirmed omission of two substantive textbox paragraphs in oxygen 1v1 teacher compatibility outputs. Current publication gate refuses these outputs; frozen Writer unchanged.',
    limitation='Other changed V0.9 media hashes are not all individually visually proved. Corpus route counts are not complete content acceptance.'
),ensure_ascii=False,indent=2),encoding='utf-8')
safe_root = Path(r'C:\xml-uat\product-rescue-safe-20261008')
safe_browser = []
for name, head in [('browser-p0.log', '3a76f9a'), ('browser-core-class.log', '3a76f9a'),
                   ('browser-final-p0.log', '6b426d6'), ('browser-final-content-refusal.log', '6b426d6'),
                   ('browser-final-core-class-retry.log', '6b426d6')]:
    raw = (safe_root/name).read_text(encoding='utf-8-sig')
    if '### Result' not in raw:
        raise ValueError('Browser gate has no result: ' + name)
    value = json.loads(raw.split('### Result')[1].strip().splitlines()[0])
    safe_browser.append(dict(build_head=head, external_log=str(safe_root/name), evidence=value))
(DEST/'safe_exe_browser.json').write_text(json.dumps(safe_browser,ensure_ascii=False,indent=2),encoding='utf-8')

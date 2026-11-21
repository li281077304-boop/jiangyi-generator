"""Real DOCX/API checks for the ephemeral content-inspection boundary."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app/webapp'))
import app as app_module
import inspection


def docx_bytes(lines=None):
    doc = Document()
    for line in lines or [f'{n}. Independent question?' for n in range(1, 10)]:
        doc.add_paragraph(line)
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setitem(app_module.app.config, 'TESTING', True)
    monkeypatch.setitem(app_module.app.config, 'LAUNCHER_TOKEN', None)
    monkeypatch.setitem(app_module.app.config, 'RESULT_ROOT', tmp_path / 'results')
    monkeypatch.setitem(app_module.app.config, 'RUNTIME_ROOT', tmp_path / 'jobs')
    monkeypatch.setattr(app_module, '_jobs', lambda: pytest.fail('inspection must not initialize jobs'))
    with app_module.app.test_client() as client:
        yield client
    assert not (tmp_path / 'results').exists()
    assert not (tmp_path / 'jobs').exists()


def post(client, payload=None, filename='原稿.docx', template='1v1', headers=None):
    return client.post('/api/inspect', data={'file': (io.BytesIO(payload if payload is not None else docx_bytes()), filename),
                                           'template_type': template}, headers=headers or {})


def test_valid_source_is_provisional_and_temporary_copy_is_removed(client, tmp_path, monkeypatch):
    source = tmp_path / 'original.docx'
    source.write_bytes(docx_bytes())
    original = source.read_bytes()
    captured = []
    real_tempdir = inspection.tempfile.TemporaryDirectory
    def capture(*args, **kwargs):
        directory = real_tempdir(*args, **kwargs)
        captured.append(Path(directory.name))
        return directory
    monkeypatch.setattr(inspection.tempfile, 'TemporaryDirectory', capture)
    response = post(client, original, filename='../../原稿.docx')
    assert response.status_code == 200
    body = response.get_json()
    assert body['source'] == {'name': '原稿.docx', 'sha256': hashlib.sha256(original).hexdigest()}
    assert body['provisional'] is True and body['status'] == 'ready'
    assert body['method'] in ('NAVIGATION', 'SEMANTIC', 'RULES', 'PARTITION')
    assert {s['id'] for s in body['slots']} == {'knowledge', 'immediate', 'final'}
    assert all(set(b) == {'id', 'text', 'kind', 'math_count', 'image_count', 'text_truncated'} for s in body['slots'] for b in s['blocks'])
    assert captured and not any(p.exists() for p in captured)
    assert source.read_bytes() == original
    assert str(tmp_path) not in json.dumps(body)


def test_preservation_uses_unresolved_not_knowledge(client):
    response = post(client, docx_bytes(['没有可靠题目边界的原文内容。']))
    body = response.get_json()
    assert response.status_code == 200
    assert body['status'] == 'preserved' and body['method'] == 'PRESERVATION'
    assert [s['id'] for s in body['slots']] == ['unresolved']
    assert body['slots'][0]['block_count'] == 1


@pytest.mark.parametrize('template', ['', 'unknown', '../../outside'])
def test_invalid_template(client, template):
    response = post(client, template=template)
    assert response.status_code == 400
    assert response.get_json()['code'] == 'INSPECT_INVALID_TEMPLATE'


def test_missing_file(client):
    response = client.post('/api/inspect', data={'template_type': 'class'})
    assert response.status_code == 400 and response.get_json()['code'] == 'INSPECT_FILE_REQUIRED'


def test_malformed_docx(client):
    response = post(client, b'not a docx')
    assert response.status_code == 422
    assert set(response.get_json()) == {'error', 'code'}


def test_upload_limit_before_reading_document(client, monkeypatch):
    monkeypatch.setattr(inspection, 'MAX_UPLOAD_BYTES', 10)
    response = post(client, b'x' * 11)
    assert response.status_code == 413


def test_expanded_archive_limit(client, monkeypatch):
    monkeypatch.setattr(inspection, 'MAX_EXPANDED_BYTES', 100)
    response = post(client)
    assert response.status_code == 413 and response.get_json()['code'] == 'INSPECT_EXPANDED_LIMIT'


def test_structure_node_budget_is_enforced(client, monkeypatch):
    monkeypatch.setattr(inspection, 'MAX_XML_NODES', 5)
    response = post(client)
    assert response.status_code == 413
    assert response.get_json()['code'] == 'INSPECT_STRUCTURE_LIMIT'


def test_launcher_token_and_origin_are_enforced(client, monkeypatch):
    monkeypatch.setitem(app_module.app.config, 'LAUNCHER_TOKEN', 'a-long-local-token')
    assert post(client).status_code == 403
    assert post(client, headers={'X-Launcher-Token': 'wrong'}).status_code == 403
    assert post(client, headers={'X-Launcher-Token': 'a-long-local-token', 'Origin': 'https://foreign.example'}).status_code == 403
    assert post(client, headers={'X-Launcher-Token': 'a-long-local-token', 'Origin': 'http://localhost'}).status_code == 200


def test_cross_site_is_rejected_without_launcher(client):
    assert post(client, headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403


def test_display_limits_are_honest(client):
    response = post(client, docx_bytes(['长' * 2100] + ['普通原文内容。'] * 405))
    body = response.get_json()
    assert response.status_code == 200
    assert body['truncated'] is True
    assert body['slots'][0]['block_count'] == 406
    assert len(body['slots'][0]['blocks']) == 400
    assert len(body['slots'][0]['blocks'][0]['text']) == 2000
    assert body['slots'][0]['blocks'][0]['text_truncated'] is True


def test_unsafe_package_path_is_rejected(client):
    source = docx_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as old, zipfile.ZipFile(buf, 'w') as new:
        for info in old.infolist():
            new.writestr(info, old.read(info.filename))
        new.writestr('../outside.xml', '<outside/>')
    response = post(client, buf.getvalue())
    assert response.status_code == 422 and response.get_json()['code'] == 'INSPECT_INVALID_PACKAGE'


def test_unresolved_plan_shows_original_blocks_without_exception_details(client, monkeypatch):
    import xml_degradation
    def reject(*args, **kwargs):
        raise RuntimeError('/private/internal/source.docx: diagnostic detail')
    monkeypatch.setattr(xml_degradation, 'build_degraded_plan', reject)
    response = post(client)
    body = response.get_json()
    assert response.status_code == 200 and body['status'] == 'unresolved'
    assert body['method'] is None and body['slots'][0]['id'] == 'unresolved'
    assert body['slots'][0]['block_count'] == 9
    assert 'private/internal' not in json.dumps(body)


def test_parse_failure_removes_temporary_source(client, monkeypatch):
    import xml_degradation
    captured = []
    def reject(source):
        captured.append(Path(source))
        raise RuntimeError('/private/internal/source.docx: diagnostic detail')
    monkeypatch.setattr(xml_degradation, 'structural_snapshot', reject)
    response = post(client)
    assert response.status_code == 422
    assert response.get_json()['code'] == 'INSPECT_ANALYSIS_FAILED'
    assert captured and not captured[0].parent.exists()
    assert 'private/internal' not in response.get_data(as_text=True)

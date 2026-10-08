"""P0: multiple browsers must share one restart-recovery service."""
import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app'))
sys.path.insert(0, str(ROOT / 'v1.2-xml-experiment/res/app/webapp'))
web = importlib.import_module('app')


def test_simultaneous_first_requests_initialize_recovery_only_once(tmp_path, monkeypatch):
    monkeypatch.setitem(web.app.config, 'RESULT_ROOT', tmp_path / 'results')
    monkeypatch.setitem(web.app.config, 'RUNTIME_ROOT', tmp_path / 'jobs')
    monkeypatch.setitem(web.app.extensions, 'c0_job_services', {})
    starts = []
    barrier = threading.Barrier(8)

    def factory(*args, **kwargs):
        starts.append(time.monotonic())
        time.sleep(0.05)
        return object()

    monkeypatch.setattr(web, 'JobService', factory)

    def request():
        barrier.wait()
        return web._jobs()

    with ThreadPoolExecutor(max_workers=8) as pool:
        instances = list(pool.map(lambda _: request(), range(8)))
    assert len(starts) == 1
    assert all(instance is instances[0] for instance in instances)

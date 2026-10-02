from __future__ import annotations

import importlib.machinery
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid


LAUNCHER_PATH = (Path(__file__).resolve().parents[1] /
                 "v1.2-xml-experiment/res/app/webapp/windows_launcher.pyw")
loader = importlib.machinery.SourceFileLoader("windows_launcher_under_test", str(LAUNCHER_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
launcher = importlib.util.module_from_spec(spec)
loader.exec_module(launcher)


def test_occupied_unrelated_port_is_not_mistaken_for_our_app():
    class Response:
        def __init__(self, status=200, body=b'{"ready":true}'):
            self.status = status
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def read(self):
            return self.body

    identity = hashlib.sha256(b"ours").hexdigest().encode("ascii")
    our_body = b'{"ready":true,"identity":"' + identity + b'"}'
    assert launcher.owns_server_identity(
        "http://127.0.0.1:5128", "ours", opener=lambda *_a, **_k: Response(body=our_body))

    assert not launcher.owns_server_identity(
        "http://127.0.0.1:5128", "ours", opener=lambda *_a, **_k: Response())

    def unrelated(*_args, **_kwargs):
        raise OSError("HTTP 404 from unrelated process")

    assert not launcher.owns_server_identity("http://127.0.0.1:5128", "ours", opener=unrelated)


def test_busy_default_port_binds_an_actual_alternate_port():
    calls = []

    class Server:
        server_port = 49332

    def factory(host, port, app, **kwargs):
        calls.append((host, port, kwargs))
        if port == 5128:
            raise OSError("address already in use")
        assert port == 0
        return Server()

    server = launcher.bind_local_server(object(), server_factory=factory)
    assert server.server_port == 49332
    assert [call[1] for call in calls] == [5128, 0]
    assert all(call[0] == "127.0.0.1" for call in calls)


def test_named_mutex_enforces_single_instance_on_windows():
    if os.name != "nt":
        return
    first, first_exists = launcher._create_instance_mutex()
    second, second_exists = launcher._create_instance_mutex()
    try:
        assert first and not first_exists
        assert second and second_exists
    finally:
        launcher._close_instance_mutex(second, owned=False)
        launcher._close_instance_mutex(first, owned=True)


def test_runtime_environment_redirects_temp_bytecode_and_result_root():
    with tempfile.TemporaryDirectory() as folder:
        env, runtime = launcher.prepare_runtime_environment(
            {"LOCALAPPDATA": folder}, desktop_getter=lambda: Path(folder) / "OneDrive Desktop")
        expected_temp = runtime / "temp"
        assert Path(env["TEMP"]) == expected_temp
        assert Path(env["TMP"]) == expected_temp
        assert Path(env["TMPDIR"]) == expected_temp
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"
        assert env[launcher.RUNTIME_ROOT_ENV] == str(runtime / "jobs")
        assert Path(env[launcher.RESULT_ROOT_ENV]) == (Path(folder) / "OneDrive Desktop" / "生成讲义结果").resolve()
        assert expected_temp.is_dir()
        assert (runtime / "jobs").is_dir()


def test_desktop_known_folder_resolver_uses_redirected_location():
    redirected = Path("R:/OneDrive/Desktop")
    assert launcher.windows_desktop_path(lambda: redirected) == redirected.resolve()


def test_ready_file_and_identity_probe_use_bound_port():
    with tempfile.TemporaryDirectory() as folder:
        ready_path = Path(folder) / "runtime" / "ready.json"
        launcher._write_ready_file(ready_path, 49177)
        assert json.loads(ready_path.read_text(encoding="utf-8")) == {"port": 49177, "ready": True}


def test_explicit_exit_control_route_is_token_gated_and_shuts_down():
    import threading
    app_path = LAUNCHER_PATH.with_name("app.py")
    if str(app_path.parent) not in sys.path:
        sys.path.insert(0, str(app_path.parent))
    app_spec = importlib.util.spec_from_file_location("webapp_launcher_test", app_path)
    webapp = importlib.util.module_from_spec(app_spec)
    sys.modules[app_spec.name] = webapp
    app_spec.loader.exec_module(webapp)
    webapp.app.config["LAUNCHER_TOKEN"] = "secret"
    called = threading.Event()
    webapp.app.config["LAUNCHER_SHUTDOWN"] = called.set
    client = webapp.app.test_client()
    assert client.get("/api/launcher/ready").status_code == 404
    assert client.get("/api/launcher/ready", headers={"X-Launcher-Token": "secret"}).get_json() == {
        "ready": True, "identity": hashlib.sha256(b"secret").hexdigest()}
    assert client.post("/api/launcher/shutdown").status_code == 404
    response = client.post("/api/launcher/shutdown", headers={"X-Launcher-Token": "secret"})
    assert response.status_code == 200
    assert response.get_json() == {"stopping": True}
    assert called.wait(1)

    page = client.get("/")
    assert b'<meta name="launcher-token" content="secret">' in page.data


def test_server_child_starts_with_isolated_runtime_and_exits_via_control_api():
    with tempfile.TemporaryDirectory(prefix="jiangyi-launcher-smoke-") as folder:
        root = Path(folder)
        ready_file = root / "recovery" / "ready.json"
        token = uuid.uuid4().hex
        child_env = os.environ.copy()
        child_env.update({
            "LOCALAPPDATA": str(root / "localappdata"),
            launcher.TOKEN_ENV: token,
            launcher.READY_PATH_ENV: str(ready_file),
            "PYTHONDONTWRITEBYTECODE": "0",  # the child must override this before app import
        })
        process = subprocess.Popen(
            [sys.executable, str(LAUNCHER_PATH), "--server"], env=child_env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and process.poll() is None and not ready_file.exists():
                time.sleep(0.1)
            assert ready_file.exists(), "server child did not publish readiness"
            port = json.loads(ready_file.read_text(encoding="utf-8"))["port"]
            base = "http://127.0.0.1:%d" % port
            assert launcher.owns_server_identity(base, token)
            with urllib.request.urlopen(base + "/", timeout=5) as response:
                assert response.status == 200
            shutdown_request = urllib.request.Request(
                base + "/api/launcher/shutdown", method="POST",
                headers={"X-Launcher-Token": token})
            with urllib.request.urlopen(shutdown_request, timeout=5) as response:
                assert json.loads(response.read().decode("utf-8")) == {"stopping": True}
            assert process.wait(timeout=10) == 0
            assert not ready_file.exists()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

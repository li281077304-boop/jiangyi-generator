from __future__ import annotations

import importlib.machinery
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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


def test_real_werkzeug_bind_failure_uses_its_actual_alternate_port():
    import threading
    from flask import Flask
    from werkzeug.serving import make_server

    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(2)
    occupied_port = occupied.getsockname()[1]
    occupied.settimeout(0.2)
    original_default = launcher.DEFAULT_PORT
    launcher.DEFAULT_PORT = occupied_port
    app = Flask("launcher_bind_test")
    app.add_url_rule("/identity", view_func=lambda: "our alternate server")
    server = None
    thread = None
    try:
        # Werkzeug's BaseWSGIServer reports this real bind error via SystemExit.
        server = launcher.bind_local_server(app, server_factory=make_server)
        assert server.server_port != occupied_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/identity" % server.server_port, timeout=3) as response:
            assert response.read() == b"our alternate server"
        # The occupied unrelated listener must not receive a probe or browser request.
        try:
            occupied.accept()
        except TimeoutError:
            pass
        else:
            raise AssertionError("launcher connected to the unrelated listener")
    finally:
        launcher.DEFAULT_PORT = original_default
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        occupied.close()


def test_factory_startup_system_exit_is_not_misclassified_as_busy_port(monkeypatch):
    monkeypatch.setattr(launcher, "DEFAULT_PORT", 0)

    def factory(_host, _port, _app, **_kwargs):
        raise SystemExit(2)

    try:
        launcher.bind_local_server(object(), server_factory=factory)
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("non-bind SystemExit must be preserved")


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


def test_second_launcher_reuses_authenticated_current_instance_url(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="jiangyi-second-launch-") as folder:
        runtime = Path(folder) / "讲义生成器"
        recovery = runtime / "recovery"
        ready_path = recovery / "launcher-current.json"
        token = "authenticated-launcher-token-0123456789"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if (self.path != "/api/launcher/ready" or
                        self.headers.get("X-Launcher-Token") != token):
                    self.send_error(404)
                    return
                payload = json.dumps({
                    "ready": True,
                    "identity": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        import threading
        service_thread = threading.Thread(target=service.serve_forever, daemon=True)
        service_thread.start()
        port = service.server_address[1]
        recovery.mkdir(parents=True)
        launcher._write_ready_file(ready_path, port)
        launcher._write_current_instance(
            launcher._current_instance_path(runtime), token=token, ready_path=ready_path)
        opened = []
        import webbrowser
        monkeypatch.setattr(launcher, "_create_instance_mutex", lambda: (object(), True))
        monkeypatch.setattr(launcher, "_close_instance_mutex", lambda *_a, **_k: None)
        monkeypatch.setattr(launcher, "local_runtime_root", lambda: runtime)
        monkeypatch.setattr(webbrowser, "open", lambda url, **_kw: opened.append(url) or True)
        monkeypatch.setattr(subprocess, "Popen", lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("second launch must not create a server")))
        try:
            assert launcher.run_gui() == 0
            assert opened == ["http://127.0.0.1:%d" % port]
        finally:
            service.shutdown()
            service.server_close()
            service_thread.join(timeout=3)


def test_stale_or_unavailable_instance_reports_actionable_feedback():
    with tempfile.TemporaryDirectory(prefix="jiangyi-stale-launch-") as folder:
        runtime = Path(folder) / "runtime"
        recovery = runtime / "recovery"
        ready_path = recovery / "launcher-stale.json"
        recovery.mkdir(parents=True)
        launcher._write_ready_file(ready_path, 5128)
        launcher._write_current_instance(
            launcher._current_instance_path(runtime),
            token="stale-" + ("x" * 40), ready_path=ready_path, pid=987654321)
        try:
            launcher._wait_for_existing_instance(
                runtime, timeout=0.3, process_is_running=lambda _pid: False)
        except RuntimeError as exc:
            assert "现有启动实例已退出" in str(exc)
        else:
            raise AssertionError("stale instance metadata must not be reused")

        (launcher._current_instance_path(runtime)).unlink()
        try:
            launcher._wait_for_existing_instance(runtime, timeout=0.2)
        except TimeoutError as exc:
            assert "暂未就绪" in str(exc)
        else:
            raise AssertionError("missing instance state must not open a guessed URL")


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

# -*- coding: utf-8 -*-
"""GUI-mode Windows bootstrap for the V1.2 local workbench.

This file intentionally imports only the standard library until the child
runtime environment has been redirected away from the install directory.
It can be used as a pythonw entry point now and as the entry script for a
future PyInstaller windowed/onedir build.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


APP_NAME = "讲义生成器"
DEFAULT_PORT = 5128
MUTEX_NAME = r"Local\JiangyiGeneratorV12Launcher"
READY_PATH_ENV = "JIANGYI_LAUNCHER_READY_FILE"
TOKEN_ENV = "JIANGYI_LAUNCHER_TOKEN"
RESULT_ROOT_ENV = "JIANGYI_RESULT_ROOT"
RUNTIME_ROOT_ENV = "JIANGYI_RUNTIME_ROOT"


def local_runtime_root(env: dict[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    local = env.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local).expanduser().resolve() / APP_NAME


def windows_desktop_path(known_folder_getter=None) -> Path:
    """Return the actual Desktop Known Folder, including redirected desktops."""
    if known_folder_getter is not None:
        return Path(known_folder_getter()).expanduser().resolve()
    if os.name == "nt":
        class GUID(ctypes.Structure):
            _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                        ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

        desktop_id = GUID(0xFDD39AD0, 0x238F, 0x46AF,
                          (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        shell32.SHGetKnownFolderPath.argtypes = (
            ctypes.POINTER(GUID), ctypes.c_uint32, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p))
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
        path_pointer = ctypes.c_void_p()
        result = shell32.SHGetKnownFolderPath(
            ctypes.byref(desktop_id), 0, None, ctypes.byref(path_pointer))
        if result != 0:
            raise OSError(result, "SHGetKnownFolderPath(Desktop) failed")
        try:
            return Path(ctypes.wstring_at(path_pointer.value)).resolve()
        finally:
            ole32.CoTaskMemFree(path_pointer)
    return (Path.home() / "Desktop").resolve()


def prepare_runtime_environment(env: dict[str, str] | None = None,
                                desktop_getter=None) -> tuple[dict[str, str], Path]:
    """Set all mutable paths before importing Flask or dynamic app loaders."""
    child_env = dict(os.environ if env is None else env)
    runtime = local_runtime_root(child_env)
    temp = runtime / "temp"
    for directory in (runtime, runtime / "jobs", runtime / "logs",
                      runtime / "work", runtime / "recovery", temp):
        directory.mkdir(parents=True, exist_ok=True)
    child_env["TEMP"] = str(temp)
    child_env["TMP"] = str(temp)
    child_env["TMPDIR"] = str(temp)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env[RUNTIME_ROOT_ENV] = str(runtime / "jobs")
    child_env[RESULT_ROOT_ENV] = str(windows_desktop_path(desktop_getter) / "生成讲义结果")
    return child_env, runtime


def _create_instance_mutex():
    if os.name != "nt":
        return None, False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    already_exists = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    return handle, already_exists


def _close_instance_mutex(handle, owned: bool = True) -> None:
    if handle and os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        if owned:
            kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)


def owns_server_identity(url: str, token: str, timeout: float = 0.6,
                         opener=urllib.request.urlopen) -> bool:
    """Distinguish our ready service from an unrelated listener on that port."""
    request = urllib.request.Request(url.rstrip("/") + "/api/launcher/ready",
                                     headers={"X-Launcher-Token": token})
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        expected_identity = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return (payload.get("ready") is True and
                secrets.compare_digest(str(payload.get("identity", "")), expected_identity))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def bind_local_server(flask_app, server_factory=None):
    """Bind 5128 when free, otherwise bind an OS-assigned loopback port."""
    if server_factory is None:
        from werkzeug.serving import make_server
        server_factory = make_server
    try:
        return server_factory("127.0.0.1", DEFAULT_PORT, flask_app, threaded=True)
    except OSError:
        return server_factory("127.0.0.1", 0, flask_app, threaded=True)


def _write_ready_file(path: Path, port: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps({"port": port, "ready": True}), encoding="utf-8")
    temp_path.replace(path)


def run_server() -> int:
    env, runtime = prepare_runtime_environment()
    # Child process variables are set before importing the app and its dynamic loaders.
    os.environ.update(env)
    sys.dont_write_bytecode = True
    app_dir = Path(__file__).resolve().parents[1]
    webapp_dir = app_dir / "webapp"
    if str(webapp_dir) not in sys.path:
        sys.path.insert(0, str(webapp_dir))
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    from werkzeug.serving import make_server
    from app import app

    token = os.environ[TOKEN_ENV]
    ready_path = Path(os.environ[READY_PATH_ENV])
    app.config["RESULT_ROOT"] = Path(os.environ[RESULT_ROOT_ENV])
    app.config["RUNTIME_ROOT"] = Path(os.environ[RUNTIME_ROOT_ENV])
    app.config["LAUNCHER_TOKEN"] = token
    server = bind_local_server(app, make_server)
    app.config["LAUNCHER_SHUTDOWN"] = server.shutdown
    _write_ready_file(ready_path, server.server_port)
    try:
        server.serve_forever()
    finally:
        try:
            ready_path.unlink(missing_ok=True)
        except OSError:
            pass
        close = getattr(server, "server_close", None)
        if close:
            close()
    return 0


def _wait_for_ready(process, ready_path: Path, token: str, timeout: float = 45.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("讲义生成器服务提前退出")
        try:
            record = json.loads(ready_path.read_text(encoding="utf-8"))
            port = int(record["port"])
            url = "http://127.0.0.1:%d" % port
            if owns_server_identity(url, token):
                return url
        except (OSError, ValueError, KeyError, TypeError):
            pass
        time.sleep(0.15)
    raise TimeoutError("等待本地服务就绪超时")


def run_gui() -> int:
    handle, already_running = _create_instance_mutex()
    if already_running:
        _close_instance_mutex(handle, owned=False)
        return 0
    child_env, runtime = prepare_runtime_environment()
    token = secrets.token_urlsafe(32)
    ready_path = runtime / "recovery" / ("launcher-" + uuid.uuid4().hex + ".json")
    child_env[TOKEN_ENV] = token
    child_env[READY_PATH_ENV] = str(ready_path)
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--server"]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--server"]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = None
    try:
        process = subprocess.Popen(command, env=child_env, creationflags=flags,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        url = _wait_for_ready(process, ready_path, token)
        import webbrowser
        webbrowser.open(url, new=2, autoraise=True)
        while process.poll() is None:
            time.sleep(0.4)
        return int(process.returncode or 0)
    except Exception as exc:
        # Keep the .pyw / windowed build free of a persistent console while still
        # reporting launch failures to the user.
        try:
            ctypes.windll.user32.MessageBoxW(None, str(exc), APP_NAME, 0x10)
        except Exception:
            pass
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        return 1
    finally:
        try:
            ready_path.unlink(missing_ok=True)
        except OSError:
            pass
        _close_instance_mutex(handle)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--server", action="store_true")
    args, _unknown = parser.parse_known_args(argv)
    return run_server() if args.server else run_gui()


if __name__ == "__main__":
    raise SystemExit(main())

"""Exact WPS/office process-instance sampler for the performance harness.

Uses only the standard library (``ctypes``) to enumerate processes through the
Toolhelp32 snapshot API and to read each process creation time, so a count is
of distinct ``(pid, creation-time)`` instances rather than of poll hits. PID
reuse therefore cannot inflate the number, and a long-lived instance is counted
once no matter how long the run lasts.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_PATH = 260

DEFAULT_NAMES = ("wps.exe", "et.exe", "wpp.exe", "winword.exe", "excel.exe", "powerpnt.exe",
                 "wpsoffice.exe", "ksomisc.exe")


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * MAX_PATH)]


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def _kernel32():
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _creation_stamp(kernel32, pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        creation, exit_time, kernel_time, user_time = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                                        ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
        return (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel32.CloseHandle(handle)


def snapshot(names=DEFAULT_NAMES):
    """Return the set of currently live ``(name, pid, creation)`` instances."""
    kernel32 = _kernel32()
    snapshot_handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot_handle == INVALID_HANDLE_VALUE:
        return set()
    wanted = {name.lower() for name in names}
    found = set()
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        ok = kernel32.Process32First(snapshot_handle, ctypes.byref(entry))
        while ok:
            name = entry.szExeFile.decode("mbcs", "ignore")
            if name.lower() in wanted:
                found.add((name.lower(), int(entry.th32ProcessID),
                           _creation_stamp(kernel32, int(entry.th32ProcessID))))
            ok = kernel32.Process32Next(snapshot_handle, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot_handle)
    return found


class ProcessMonitor:
    """Background sampler of distinct office process instances."""

    def __init__(self, names=DEFAULT_NAMES, interval=0.1):
        self.names = tuple(names)
        self.interval = interval
        self._seen: set[tuple] = set()
        self._baseline: set[tuple] = set()
        self._peak = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.availability_error = None

    def _run(self):
        while not self._stop.is_set():
            try:
                live = snapshot(self.names)
                self._seen |= live
                self._peak = max(self._peak, len(live))
            except Exception as exc:  # noqa: BLE001 - sampling must never break the run
                self.availability_error = "%s: %s" % (type(exc).__name__, exc)
                return
            self._stop.wait(self.interval)

    def start(self):
        try:
            self._baseline = snapshot(self.names)
            self._peak = max(self._peak, len(self._baseline))
        except Exception as exc:  # noqa: BLE001
            self.availability_error = "%s: %s" % (type(exc).__name__, exc)
            self._baseline = set()
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)
        try:
            live = snapshot(self.names)
            self._seen |= live
            self._peak = max(self._peak, len(live))
        except Exception as exc:  # noqa: BLE001
            self.availability_error = "%s: %s" % (type(exc).__name__, exc)
        return self.result()

    def result(self):
        started = self._seen - self._baseline
        by_name = {}
        for name, _pid, _creation in started:
            by_name[name] = by_name.get(name, 0) + 1
        return {"new_instances": len(started), "by_name": by_name,
                "preexisting_instances": len(self._baseline),
                "observed_instances": len(self._seen),
                "peak_live_instances": self._peak,
                "baseline_live": sorted("%s#%s" % (name, pid) for name, pid, _ in self._baseline),
                "started": sorted("%s#%s" % (name, pid) for name, pid, _ in started),
                "availability_error": self.availability_error}


def own_rss_bytes():
    """Resident set size of the current process, or ``None`` if unavailable."""
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    try:
        # ``GetProcessMemoryInfo`` lives in psapi.dll; the kernel32 export is
        # only the ``K32`` alias and is not present on every build. Handle and
        # size types must be declared: a 64-bit handle returned as a 32-bit int
        # would be truncated and the call would silently fail.
        for library, name in (("psapi", "GetProcessMemoryInfo"),
                              ("kernel32", "K32GetProcessMemoryInfo")):
            try:
                entry = getattr(ctypes.WinDLL(library), name)
            except (OSError, AttributeError):
                continue
            entry.restype = wintypes.BOOL
            entry.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                              wintypes.DWORD]
            kernel32 = _kernel32()
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if entry(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return int(counters.WorkingSetSize)
    except Exception:  # noqa: BLE001 - memory observation is optional
        return None
    return None


def settle(baseline: set, seconds: float = 10.0, names=DEFAULT_NAMES):
    """After a run, wait and report office instances that are still alive.

    ``residual`` counts processes alive now that were not alive before the run;
    a non-zero value means an orphaned process survived the workload.
    """
    time.sleep(seconds)
    try:
        live = snapshot(names)
    except Exception as exc:  # noqa: BLE001
        return {"error": "%s: %s" % (type(exc).__name__, exc), "seconds": seconds}
    if baseline and all(isinstance(item, str) for item in baseline):
        base_keys = set(baseline)
    else:
        base_keys = {"%s#%s" % (name, pid) for name, pid, _ in baseline}
    live_keys = {"%s#%s" % (name, pid) for name, pid, _ in live}
    remaining = live_keys - base_keys
    return {"seconds": seconds, "live_instances": len(live),
            "baseline_instances": len(base_keys),
            "residual_instances": len(remaining),
            "residual": sorted(remaining)}


def baseline_snapshot(names=DEFAULT_NAMES):
    """Instances already running before a measurement; never counted as started."""
    try:
        return snapshot(names)
    except Exception:  # noqa: BLE001
        return set()


if __name__ == "__main__":
    monitor = ProcessMonitor().start()
    time.sleep(1.0)
    print(monitor.stop())

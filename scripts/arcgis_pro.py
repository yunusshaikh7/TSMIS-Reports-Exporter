"""Find ArcGIS Pro's own Python and run a worker script in it (v0.46.0).

The app cannot carry ArcPy: it ships with ArcGIS Pro, licensed per user, inside
Pro's `arcgispro-py3` environment. So the layer export runs as a separate
process in THAT interpreter (`arcgis_worker/export_layers.py`), the pattern the
TSMIS Project Inspector proved on the work PC (ArcGIS Pro 3.3.5 / Python
3.11.8):

  * discovery -- `SOFTWARE\\ESRI\\ArcGISPro\\InstallDir` (per user, then per
    machine), then the default install folders, to `bin\\Python\\envs\\
    arcgispro-py3\\python.exe`; a python.exe chosen in the app wins;
  * a clean environment -- no inherited PYTHON*/_PYI* variables (the frozen
    app's own interpreter state would break ArcGIS), the environment's own
    folders first on PATH, no bytecode written into Pro's install;
  * launched DIRECTLY (no shell -- restricted work PCs block cmd/PowerShell),
    without a console window, and with the frozen app's DLL search directory
    reset so ArcGIS loads its own DLLs rather than the bundle's.

Console-free; nothing here imports ArcPy.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import paths
import settings

log = logging.getLogger("tsmis.arcgis_pro")

_ENV_PYTHON = Path("bin") / "Python" / "envs" / "arcgispro-py3" / "python.exe"
_REG_KEY = r"SOFTWARE\ESRI\ArcGISPro"

WORKER_DIRNAME = "arcgis_worker"
WORKER_SCRIPT = "export_layers.py"


def _install_roots():
    """ArcGIS Pro install folders to try, registry first."""
    roots = []
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, _REG_KEY, 0,
                                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                    roots.append(Path(winreg.QueryValueEx(key, "InstallDir")[0]))
            except OSError:      # silent-ok: Pro not registered in this hive
                pass
    roots.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                 / "ArcGIS" / "Pro")
    roots.append(Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
                 / "Programs" / "ArcGIS" / "Pro")
    return roots


def find_python():
    """ArcGIS Pro's arcgispro-py3 python.exe, or "" when Pro isn't installed."""
    for root in _install_roots():
        candidate = root / _ENV_PYTHON
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:          # silent-ok: an unreadable candidate is just not this one
            continue
    return ""


def resolve_python():
    """(python.exe path, how it was found): the one chosen in the app when it
    still exists ("chosen"), else auto-detected ("detected"), else ("", "")."""
    chosen = settings.get_arcgis_python()
    if chosen and Path(chosen).is_file():
        return chosen, "chosen"
    found = find_python()
    return (found, "detected") if found else ("", "")


def status():
    """What the Layers tab shows about ArcGIS Pro. Never raises."""
    chosen = settings.get_arcgis_python()
    path, how = resolve_python()
    return {"python": path, "how": how, "found": bool(path),
            "chosen": chosen or "",
            "chosen_missing": bool(chosen) and how != "chosen"}


def worker_script():
    """The worker script on disk: beside the modules in development, under
    the bundle's `arcgis_worker/` data folder when frozen."""
    base = Path(getattr(sys, "_MEIPASS", "")) if paths.is_frozen() \
        else Path(__file__).resolve().parent
    return base / WORKER_DIRNAME / WORKER_SCRIPT


def worker_environment(python):
    """The environment for ArcGIS Pro's python.exe: the app's own Python state
    stripped, the conda environment's folders first on PATH (ArcPy's native
    DLLs), and Pro's `bin` after them."""
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("PYTHON", "_PYI"))}
    prefix = Path(python).parent
    first = [prefix, prefix / "Library" / "bin", prefix / "Scripts"]
    for parent in prefix.parents:
        if parent.name.lower() == "pro" and (parent / "bin").is_dir():
            first.append(parent / "bin")
            break
    inherited = [p for p in env.get("PATH", "").split(os.pathsep) if p]
    bundle = getattr(sys, "_MEIPASS", None)
    if paths.is_frozen() and bundle:
        # The bundle's own folders on PATH would shadow ArcGIS's DLLs.
        inherited = [p for p in inherited
                     if not os.path.normcase(p).startswith(os.path.normcase(bundle))]
    env["PATH"] = os.pathsep.join([str(p) for p in first] + inherited)
    env["CONDA_PREFIX"] = str(prefix)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


_spawn_lock = threading.Lock()


def start_external(command, **kwargs):
    """Popen `command` (an argument list -- never a shell string). When frozen,
    the bundle's DLL search directory is reset for the child and restored."""
    with _spawn_lock:
        if os.name == "nt" and paths.is_frozen():
            import ctypes
            kernel = ctypes.windll.kernel32
            old = ctypes.create_unicode_buffer(32768)
            kernel.GetDllDirectoryW(len(old), old)
            kernel.SetDllDirectoryW(None)
            try:
                return subprocess.Popen(command, **kwargs)
            finally:
                kernel.SetDllDirectoryW(old.value or None)
        return subprocess.Popen(command, **kwargs)


# --------------------------------------------------------------------------- #
# one worker session: request in, events out
# --------------------------------------------------------------------------- #
# How long the worker may take. A layer has no progress of its own (Table To
# Excel is one call), so it gets a generous wall-clock limit; outside a layer
# the worker's heartbeat must keep arriving.
START_LIMIT_S = 600            # launch -> ArcPy imported and the run under way
LAYER_LIMIT_S = 90 * 60        # one layer's export
IDLE_LIMIT_S = 600             # no event at all, outside a layer
_POLL_S = 0.25


class _ProcessHandle:
    """The default launcher's handle: ArcGIS Pro's python.exe running the
    worker, its console output kept in the session folder for diagnosis."""

    def __init__(self, python, script, request_path, events_path, log_path):
        self._log = open(log_path, "wb")
        try:
            self.proc = start_external(
                [python, "-B", "-u", str(script), "--request", str(request_path),
                 "--events", str(events_path)],
                cwd=str(script.parent), env=worker_environment(python),
                stdin=subprocess.DEVNULL, stdout=self._log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            self._log.close()
            raise

    def poll(self):
        return self.proc.poll()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)

    def close(self):
        try:
            if self.proc.poll() is None:
                self.stop()
        finally:
            self._log.close()


def subprocess_launcher(python, script, request_path, events_path, log_path):
    """The real launcher: ArcGIS Pro's python.exe runs the worker script."""
    return _ProcessHandle(python, script, request_path, events_path, log_path)


@dataclass
class SessionOutcome:
    exit_code: int | None = None
    cancelled: bool = False
    timed_out: str = ""
    fatal: str = ""
    output_tail: str = ""


def _tail_text(path, limit=1500):
    try:
        data = Path(path).read_bytes()[-limit:]
        return data.decode("utf-8", "replace").strip()
    except OSError:          # silent-ok: diagnostics only
        return ""


def _clear_session(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for p in folder.iterdir():
        try:
            if p.is_file() and not p.is_symlink():
                p.unlink()
        except OSError as e:
            log.info("arcgis_pro: could not remove %s (%s)", p, e)


def run_worker(session, request, on_event, cancel_event, python, launcher=None,
               start_limit=START_LIMIT_S, layer_limit=LAYER_LIMIT_S,
               idle_limit=IDLE_LIMIT_S):
    """Run one worker request in `session` (an app-owned folder, emptied
    first), feeding every event to `on_event(dict)` as it arrives. Returns a
    SessionOutcome. The worker is stopped on cancel and on any time limit; its
    request, events and console output stay in the folder for diagnosis.

    `launcher(python, script, request_path, events_path, log_path)` returns a
    handle with poll()/stop()/close(); the default runs ArcGIS Pro's python.exe
    (the self-test injects one that runs the worker in-process)."""
    session = Path(session)
    _clear_session(session)
    request_path = session / "request.json"
    events_path = session / "events.jsonl"
    log_path = session / "worker-output.txt"
    request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    events_path.write_text("", encoding="utf-8")
    script = worker_script()
    if not script.is_file():
        return SessionOutcome(fatal=f"The layer export worker is missing from the app ({script}).")
    out = SessionOutcome()
    clock = {"last": time.monotonic(), "started": False, "layer": None}

    def take(line):
        try:
            ev = json.loads(line)
        except ValueError:
            log.info("arcgis_pro: unreadable worker event %r", line[:200])
            return
        clock["last"] = time.monotonic()
        kind = ev.get("type")
        if kind in ("runtime", "catalog", "layer_start", "done"):
            clock["started"] = True
        if kind == "layer_start":
            clock["layer"] = time.monotonic()
        elif kind in ("layer_done", "layer_failed"):
            clock["layer"] = None
        elif kind == "fatal":
            out.fatal = out.fatal or str(ev.get("message") or "")
        on_event(ev)

    handle = (launcher or subprocess_launcher)(python, script, request_path,
                                               events_path, log_path)
    launched = time.monotonic()
    try:
        with open(events_path, encoding="utf-8") as stream:
            while True:
                pos = stream.tell()
                line = stream.readline()
                if line and line.endswith("\n"):
                    take(line)
                    continue
                stream.seek(pos)
                if handle.poll() is not None:
                    for rest in stream:            # the final events race the exit
                        if rest.strip():
                            take(rest)
                    break
                if cancel_event is not None and cancel_event.is_set():
                    out.cancelled = True
                    break
                now = time.monotonic()
                if not clock["started"] and now - launched > start_limit:
                    out.timed_out = ("ArcGIS Pro's Python did not start the run within "
                                     f"{max(start_limit // 60, 1)} minutes")
                    break
                if clock["layer"] is not None and now - clock["layer"] > layer_limit:
                    out.timed_out = (f"one layer took longer than {max(layer_limit // 60, 1)} "
                                     "minutes")
                    break
                if (clock["layer"] is None and clock["started"]
                        and now - clock["last"] > idle_limit):
                    out.timed_out = ("the worker went silent for "
                                     f"{max(idle_limit // 60, 1)} minutes")
                    break
                time.sleep(_POLL_S)
    finally:
        try:
            handle.stop()
        finally:
            handle.close()
    out.exit_code = handle.poll()
    out.output_tail = _tail_text(log_path)
    return out

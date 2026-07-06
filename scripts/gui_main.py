"""GUI entry point for the TSMIS Reports Exporter.

Run in dev:   python scripts\\gui_main.py   (or "run app (GUI preview).bat")
Packaged:     this is the PyInstaller entry (build.ps1 sets TSMIS_ENTRY here
              and TSMIS_CONSOLE=0 for a windowed app).

The window is a pywebview (Edge WebView2) shell rendering scripts/ui/; all
GUI logic lives in gui_api.py, and the browser/file work stays on the same
gui_worker threads the engines have always used. The only bootstrap here is
making the dev import paths work when run from source.
"""
import logging
import os
import sys
from pathlib import Path


def _bootstrap():
    # Dev only: make the flat scripts/ modules and the repo-root version.py
    # importable regardless of the working directory. Frozen builds bundle these.
    if not getattr(sys, "frozen", False):
        here = Path(__file__).resolve().parent          # scripts/
        sys.path.insert(0, str(here))                   # common, exporter, gui_api, ...
        sys.path.insert(0, str(here.parent))            # version.py (repo root)


_bootstrap()


def _unblock_dotnet_assemblies():
    """Frozen builds: strip the Mark-of-the-Web from the bundled .NET files.

    A release zip downloaded from the internet carries the "blocked" flag;
    extracting it without Unblock tags every file with an NTFS Zone.Identifier
    stream, and the .NET Framework then REFUSES to load those assemblies — the
    window dies at startup with "Failed to resolve Python.Runtime.Loader.
    Initialize" (seen in the field on the first v0.8.0 download; dev runs and
    CI never go through a downloaded zip, so only releases hit it). Deleting
    the stream is exactly what right-click → Properties → Unblock does. Only
    the CLR cares: plain Win32 DLL loads ignore the tag, so the .NET trees
    are the only ones that need cleaning. Best-effort — on a read-only
    install this fails and the error box explains the manual Unblock."""
    if not getattr(sys, "frozen", False):
        return
    internal = Path(sys.executable).resolve().parent / "_internal"
    removed = errors = 0
    for sub in ("pythonnet", "clr_loader", "webview"):
        root = internal / sub
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                os.remove(f"{p}:Zone.Identifier")
                removed += 1
            except FileNotFoundError:
                pass                       # not tagged (the normal case)
            except OSError:
                errors += 1                # read-only location etc.
    if removed or errors:
        logging.getLogger("tsmis.gui").info(
            "unblocked %d bundled .NET file(s) (Mark-of-the-Web removed)%s",
            removed, f"; {errors} could not be unblocked" if errors else "")


def _run_self_test():
    """``--self-test``: prove the EXACT shipped exe boots/imports before any webview.

    Runs the shared comprehensive self-test (``self_test.run``): imports every app
    module incl. the dynamically-loaded matrix modules, asserts the bundled ``ui/``
    assets, builds the GUI bridge + initial state, exercises the real
    browser/pdf/openpyxl code paths, and best-effort cycles a hidden WebView.
    Returns a process exit code (0 = ok). The import/asset/registry/runtime
    sub-checks FAIL the gate; only the hidden-window probe may skip.

    A windowed release exe has no console (``sys.stdout``/``stderr`` are ``None``),
    so output is mirrored to the log and -- if ``TSMIS_SELFTEST_OUT`` names a path
    -- written there too, which the build.ps1 ``-SelfTest`` gate reads back for CI
    diagnosability. The exit CODE is the actual gate."""
    log = logging.getLogger("tsmis.selftest")
    lines = []

    def emit(line=""):
        text = str(line)
        lines.append(text)
        if text.strip():
            log.info("%s", text)
        if sys.stderr:                         # console (dev) runs still see it
            try:
                print(text, file=sys.stderr)
            except Exception:
                pass

    code = 0
    try:
        import self_test
        code = self_test.run(emit=emit)
    except Exception as e:                      # any mandatory failure fails the gate
        emit(f"SELF-TEST FAILED: {type(e).__name__}: {e}")
        log.exception("self-test failed")
        code = 1

    out = os.environ.get("TSMIS_SELFTEST_OUT")
    if out:
        try:
            Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            log.warning("could not write TSMIS_SELFTEST_OUT=%s", out, exc_info=True)
    return code


def _arg_value(flag):
    """The value after `flag` in argv (``--evidence-dir C:\\path``), or None. Tolerates
    the flag being absent or trailing (no value)."""
    try:
        i = sys.argv.index(flag)
    except ValueError:
        return None
    return sys.argv[i + 1] if i + 1 < len(sys.argv) else None


def _run_collect_evidence():
    """``--collect-evidence``: gather a CREDENTIAL-SAFE work-PC evidence bundle (logs,
    run reports, the offline self-test output, and any real files the user explicitly
    placed via ``--evidence-dir``) into one zip — no admin / cmd / scheduled tasks
    needed. NEVER collects the saved login, the Edge profile, failure dumps, or the
    report data (RM05). Returns a process exit code (0 = the bundle was written).

    A windowed release exe has no console, so progress mirrors to the log and the
    final path is shown in a message box; dev/console runs also see it on stderr."""
    log = logging.getLogger("tsmis.evidence")

    def emit(line=""):
        text = str(line)
        if text.strip():
            log.info("%s", text)
        if sys.stderr:
            try:
                print(text, file=sys.stderr)
            except Exception:
                pass

    try:
        import evidence
        res = evidence.collect(extra_dir=_arg_value("--evidence-dir"), emit=emit)
    except Exception as e:                       # collection must not crash the exe
        log.exception("evidence collection failed")
        msg = f"Evidence collection failed: {type(e).__name__}: {e}"
        emit(msg)
        _message_box(msg)
        return 1
    ok = bool(res.get("ok"))
    _message_box(("Evidence bundle saved:\n" + res.get("path", "")
                  + "\n\nSend it to the TSMIS maintainer. It has no saved login, "
                    "profile, or report data.") if ok
                 else ("Could not save the evidence bundle.\n" + res.get("message", "")))
    return 0 if ok else 1


def _message_box(text):
    """Best-effort Windows message box (the windowed exe has no console). No-op
    where ctypes/user32 isn't available."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(text), "TSMIS Exporter", 0x40)
    except Exception:
        pass


def main():
    # Self-update swap mode (v0.10.1): the one-click update launches the
    # STAGED new exe with this flag; it swaps itself into the install folder
    # and exits. Branch BEFORE logging/paths setup — this process runs from
    # data\update\staged, so the normal path resolution would aim logs at
    # the staged tree instead of the install — and before the CLR loads
    # (no window is ever created in this mode). Never returns.
    import updater
    if updater.SWAP_FLAG in sys.argv:
        updater.run_swap_mode(sys.argv)

    from logging_setup import setup_logging
    # No faulthandler here: it intercepts the CLR's routine first-chance
    # access violations (pythonnet/WebView2) and deadlocks the window -- see
    # setup_logging's docstring. Python-level crashes are still logged by the
    # excepthooks and the GuiApi method wrapper.
    setup_logging(enable_faulthandler=False, name="gui")
    _unblock_dotnet_assemblies()           # must run BEFORE the CLR loads
    if "--self-test" in sys.argv:
        # Packaging gate (build.ps1 -SelfTest): prove THIS exact exe imports every
        # module + ui/ asset and runs every real code path, then exit before any
        # real window. Update housekeeping below is skipped -- it mutates the
        # install and is not a boot/import concern.
        raise SystemExit(_run_self_test())
    if "--collect-evidence" in sys.argv:
        # Work-PC validation (P13): gather a credential-safe evidence bundle (logs,
        # run reports, the self-test output, and any user-placed --evidence-dir files)
        # and exit — no admin/cmd/scheduled tasks, never the saved login/profile/report
        # data (RM05). Skip the update housekeeping below (not a collection concern).
        raise SystemExit(_run_collect_evidence())
    try:
        # Finish any one-click update: drop the *.old bundle pieces the swap
        # helper couldn't delete while this (new) app was already starting,
        # and any stale download staging. No-op in dev runs.
        import updater
        updater.cleanup_leftovers()
    except Exception:
        logging.getLogger("tsmis.gui").warning(
            "update leftover cleanup failed", exc_info=True)
    try:
        import gui_api
    except ImportError as e:
        # Dev runs hit this when pywebview isn't installed yet; the packaged
        # app bundles it. Print for the console case, box for the windowed one.
        msg = (f"The GUI could not start: a required component is missing "
               f"({e.name or e}).\n\nRun \"1. setup (one time).bat\" "
               f"(pip install -r requirements.txt) and try again.")
        # A windowed PyInstaller exe has sys.stderr = None -- print() would
        # raise. Console (dev) runs still get the message text.
        if sys.stderr:
            print(msg, file=sys.stderr)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "TSMIS Exporter", 0x10)
        except Exception:
            pass
        raise SystemExit(1)
    gui_api.run()


if __name__ == "__main__":
    main()

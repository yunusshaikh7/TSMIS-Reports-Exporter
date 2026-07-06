"""Application-wide file logging.

A single rotating log under LOG_DIR captures diagnostics from every entry point
(the GUI and the .bat console flow) so failures can be investigated after the
fact. File-only -- no console/stream handler -- so it never interferes with the
console flow's printed output or the windowed GUI. Call setup_logging() once at
process startup; it is safe to call again.

What lands in the log (the "no vague errors" contract):
  * a startup banner with the app version, frozen/dev, Python + OS versions,
    and every resolved path -- so any uploaded log says exactly which build
    and environment produced it;
  * every line is tagged with its thread name ([main], [export-w2], [login]),
    so fast mode's interleaved browsers stay distinguishable;
  * uncaught exceptions from ANY thread (sys.excepthook + threading.excepthook)
    are logged with a full traceback before the process dies -- a windowed app
    has no console for them to land in otherwise;
  * hard interpreter crashes (access violations etc.) get a faulthandler
    traceback in LOG_DIR/crash.log.
"""
import faulthandler
import logging
import os
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler

from paths import DATA_ROOT, LOG_DIR, OUTPUT_ROOT, is_frozen

LOG_FILE = LOG_DIR / "tsmis.log"   # the default (name-less) target; see setup_logging(name=...)
CRASH_FILE = LOG_DIR / "crash.log"
_log_file = None                    # the ACTIVE file once setup_logging ran


def active_log_file():
    """The log file THIS process actually writes (per-entry-point since E3:
    tsmis-gui.log / tsmis-cli.log / tsmis-login.log), or the legacy default
    before setup_logging has run."""
    return _log_file if _log_file is not None else LOG_FILE
_configured = False
_crash_file_handle = None      # kept alive for faulthandler


def _install_excepthooks():
    """Log uncaught exceptions (any thread) with full tracebacks. A windowed
    .exe has no stderr, so without this a crash leaves no trace at all."""
    log = logging.getLogger("tsmis.crash")
    prev_sys_hook = sys.excepthook

    def sys_hook(exc_type, exc, tb):
        log.critical("uncaught exception on the main thread",
                     exc_info=(exc_type, exc, tb))
        prev_sys_hook(exc_type, exc, tb)

    def thread_hook(args):
        log.critical("uncaught exception in thread %r",
                     args.thread.name if args.thread else "?",
                     exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = sys_hook
    threading.excepthook = thread_hook


def _enable_faulthandler():
    """Dump Python tracebacks on hard crashes (segfault/access violation) to
    crash.log -- the rotating log can't catch those. Best-effort."""
    global _crash_file_handle
    try:
        _crash_file_handle = open(CRASH_FILE, "a", encoding="utf-8")
        faulthandler.enable(file=_crash_file_handle, all_threads=True)
    except Exception as e:
        logging.getLogger("tsmis").info(
            "faulthandler disabled: crash.log unavailable (%s: %s)",
            type(e).__name__, e)


def _log_banner(log):
    """One block that pins down WHICH build ran WHERE -- the questions every
    log-based diagnosis starts with."""
    try:
        from version import __version__ as app_version
    except Exception:  # silent-ok: the banner still prints, with version 'unknown'
        app_version = "unknown"
    log.info("=== logging started (app v%s) -> %s ===", app_version, active_log_file())
    log.info("env: %s build | python %s | %s",
             "frozen" if is_frozen() else "dev",
             platform.python_version(), platform.platform())
    log.info("env: exe=%s", sys.executable)
    log.info("env: data_root=%s | output=%s", DATA_ROOT, OUTPUT_ROOT)
    overrides = {k: v for k, v in os.environ.items()
                 if k.startswith("TSMIS_") or k == "PLAYWRIGHT_BROWSERS_PATH"}
    if overrides:
        log.info("env: overrides %s", overrides)


def set_debug_logging(on):
    """Switch the root logger between DEBUG and INFO live (the Settings tab's
    'verbose logging' toggle; also applied at startup from the saved setting)."""
    logging.getLogger().setLevel(logging.DEBUG if on else logging.INFO)
    logging.getLogger("tsmis").info("file logging level set to %s",
                                    "DEBUG" if on else "INFO")


def setup_logging(level=logging.INFO, enable_faulthandler=True, name=""):
    """Configure the root logger's rotating file handler once. Returns the log
    file path. The saved 'verbose logging' setting (settings.py) upgrades the
    level to DEBUG.

    `name` picks a PER-ENTRY-POINT file (tsmis-<name>.log): the GUI, the console
    flow and the login window each write their own — two processes sharing one
    rotating file silently DROPPED records after a 2 MB rotation while the other
    process held the old inode (BUG-14). Same rotation policy per file; the
    evidence bundle collects the whole tsmis*.log* family.

    enable_faulthandler=False is for the GUI process ONLY: faulthandler's
    Windows handler intercepts access violations FIRST-chance, and the .NET CLR
    (pythonnet, which pywebview's WebView2 backend runs on) raises + handles
    such exceptions internally as routine control flow. faulthandler then dumps
    all threads mid-CLR-exception-dispatch on the GUI thread and the window
    deadlocks ("Not responding", WER AppHangB1) before the page ever loads.
    Console entry points never load the CLR and keep the crash dumps."""
    global _configured, _log_file
    if _configured:
        return active_log_file()
    try:
        import settings
        if settings.get("debug_logging"):
            level = logging.DEBUG
    except Exception:  # silent-ok: settings must never block logging setup itself
        pass
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_file = LOG_DIR / (f"tsmis-{name}.log" if name else "tsmis.log")
    handler = RotatingFileHandler(
        _log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    # Thread names tag every line; show the main thread as [main] so the common
    # case reads cleanly. Rewrite it in the LOG RECORD only -- renaming the
    # actual thread (threading.main_thread().name = ...) breaks libraries that
    # use the name to detect the main thread (pywebview's create_window treats
    # a renamed main thread as "the GUI loop is already running" and blocks).
    class _MainThreadTag(logging.Filter):
        def filter(self, record):
            if record.threadName == "MainThread":
                record.threadName = "main"
            return True

    handler.addFilter(_MainThreadTag())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _configured = True
    _log_banner(logging.getLogger("tsmis"))
    _install_excepthooks()
    if enable_faulthandler:
        _enable_faulthandler()
    else:
        logging.getLogger("tsmis").info(
            "faulthandler disabled in this process (incompatible with the "
            "CLR's first-chance exceptions; see setup_logging docstring)")
    return _log_file

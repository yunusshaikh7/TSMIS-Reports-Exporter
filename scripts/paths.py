"""Frozen-aware filesystem paths for TSMIS Reports Exporter.

One place that decides WHERE the app reads and writes, so the rest of the
code never has to care whether it is running as a dev script or as the
packaged portable .exe.

Policy ("portable by default, never break"):
  * Packaged build (sys.frozen): write next to the .exe -- the intuitive
    "my reports are right here in the folder" model. If that folder is not
    writable (e.g. unzipped into Program Files or a read-only network share),
    fall back automatically to %LOCALAPPDATA%\\TSMIS Exporter so the app
    still runs. Callers should surface DATA_ROOT in the UI so the rare
    fallback is never a mystery.
  * Dev / .bat workflow (not frozen): keep the original locations
    (./output and scripts/tsmis_auth.json) so the existing scripts and
    batch files behave exactly as before.
"""
import os
import re
import sys
from datetime import date
from pathlib import Path

APP_NAME = "TSMIS Exporter"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _writable(directory: Path) -> bool:
    """True if we can create a file in `directory` (creating it if needed)."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _localappdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_NAME


def _resolve_data_root() -> Path:
    """Base directory for everything the app writes."""
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent   # the onefolder app dir
        if _writable(exe_dir):
            return exe_dir
        fallback = _localappdata_dir()                     # read-only location
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    # Dev: repo root (this file lives in scripts/), preserving today's layout.
    return Path(__file__).resolve().parent.parent


# Resolved once at import time.
DATA_ROOT = _resolve_data_root()

# Exported reports: each report writes into its own subfolder under here.
OUTPUT_ROOT = DATA_ROOT / "output"

# User-supplied input files (currently: TSN district Highway Log PDFs). The
# TSMIS reports never read from here -- this exists for the report types whose
# source data is NOT produced by this app's exports.
INPUT_ROOT = DATA_ROOT / "input"

# Exports are grouped into RUN FOLDERS: output/<YYYY-MM-DD src-env>/<report>/
# (e.g. "2026-06-11 ssor-prod"), so a new day's run never resumes over (or
# mixes with) yesterday's files AND different data source / environment
# combinations never overwrite each other — the folder name says exactly what
# is inside, which the cross-environment comparison relies on. Folders from
# before v0.10 are bare dates ("2026-06-11"); those always meant the defaults,
# so they read as ssor-prod. The consolidators take the run-folder NAME as
# their `day` argument (an opaque string to them; newest by default).
_RUN_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?: (\w+)-(\w+))?$")


def today_str():
    return date.today().isoformat()


def run_folder_name(src, env, day=None):
    """The run-folder name for one (data source, environment) on one day."""
    return f"{day or today_str()} {src}-{env}"


def output_run_dir(src, env, day=None):
    """output/<day src-env>/ — where an export run writes. `day` is a
    YYYY-MM-DD string; None means today."""
    return OUTPUT_ROOT / run_folder_name(src, env, day)


def parse_run_folder(name):
    """(date, src, env) for a run-folder name, or None if `name` isn't one.
    Legacy bare-date folders (pre-v0.10) read as the old defaults, ssor-prod."""
    m = _RUN_RE.fullmatch(name)
    if not m:
        return None
    day, src, env = m.groups()
    return (day, src or "ssor", env or "prod")


def output_day_dir(day=None):
    """output/<day>/ — `day` is a run-folder name (or a legacy bare date);
    None means today's bare date. Kept for the consolidators, which treat the
    chosen folder name as opaque."""
    return OUTPUT_ROOT / (day or today_str())


def list_output_days():
    """Existing run folders (and legacy bare-date folders) under output/,
    newest first. The names are what the GUI day picker and the consolidators'
    `day` argument carry."""
    try:
        named = [(parse_run_folder(p.name), p.name)
                 for p in OUTPUT_ROOT.iterdir() if p.is_dir()]
        return [name for parsed, name in
                sorted(((pr, n) for pr, n in named if pr), reverse=True)]
    except OSError:
        return []


def latest_output_day():
    """Newest run folder name, or None when none exist yet (callers fall
    back to the pre-dated flat layout so old exports stay consolidatable)."""
    days = list_output_days()
    return days[0] if days else None


def resolve_day_choice(raw):
    """Map a user-supplied TSMIS_DAY value to an existing run folder: an exact
    folder name passes through; a bare date picks the newest run folder of
    that date when one exists. Anything else is returned as-is (the
    consolidators will simply find the folder empty/missing and say so)."""
    raw = (raw or "").strip()
    if not raw:
        return raw
    matches = [d for d in list_output_days() if d == raw]
    if matches:
        return matches[0]
    by_date = [d for d in list_output_days()
               if (parse_run_folder(d) or ("",))[0] == raw]
    return by_date[0] if by_date else raw

# App-private data (auth token, logs, config).
if is_frozen():
    _PRIVATE = DATA_ROOT / "data"
    AUTH = _PRIVATE / "tsmis_auth.json"
else:
    # Keep the original dev auth location so the .bat workflow is unchanged.
    _PRIVATE = DATA_ROOT
    AUTH = Path(__file__).resolve().parent / "tsmis_auth.json"   # scripts/tsmis_auth.json

LOG_DIR = _PRIVATE / "logs"
FAILURES_DIR = _PRIVATE / "failures"   # screenshot + page HTML captured when a route fails
CONFIG_FILE = _PRIVATE / "config.json"
UPDATE_DIR = _PRIVATE / "update"       # self-update download/staging area (see updater.py)
EDGE_LOGIN_PROFILE_DIR = _PRIVATE / "edge_login_profile"
WEBVIEW_PROFILE_DIR = _PRIVATE / "webview2"   # the GUI window's WebView2 user-data folder

# Built-in Chromium (the with-browser release variant): build.ps1 -BundleChromium
# ships Playwright's ms-playwright folder inside _internal. Point Playwright at
# it here -- this module is imported (via common) by every entry point before any
# sync_playwright() starts -- unless the user already pinned
# PLAYWRIGHT_BROWSERS_PATH themselves. The system-browser variant ships no such
# folder, so nothing is set and the app keeps driving the machine's Edge/Chrome.
# NOTE: next to the .exe, NOT under DATA_ROOT -- the browser is part of the
# read-only bundle, never user data.
if is_frozen() and not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    _bundled_browsers = Path(sys.executable).resolve().parent / "_internal" / "ms-playwright"
    if _bundled_browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_bundled_browsers)

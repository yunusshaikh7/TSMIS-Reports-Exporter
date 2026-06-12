"""Self-update from GitHub releases (the GUI's one-click update).

Console-free core: raises UpdateError with UI-neutral messages, reports
progress through callbacks, and logs every decision to `tsmis.update`.
gui_worker.UpdateWorker drives it from a worker thread; the Update pill in
the title bar is the only UI.

How an update happens (and why each step):

  1. check_for_update() asks the GitHub Releases API for the latest tag and
     compares it to version.__version__. The repo is public, so no token is
     involved. TLS uses ssl.create_default_context(), which trusts the
     WINDOWS certificate store -- corporate TLS inspection keeps working
     where a bundled CA list (certifi) would reject the connection; urllib
     also picks up the system proxy from the registry.
  2. download_and_stage() picks the release asset matching this install's
     variant (with-browser when _internal\\ms-playwright ships in the bundle
     -- the same probe paths.py uses), streams it into data\\update\\, and
     extracts a verified bundle tree to data\\update\\staged. Writing the
     bytes ourselves means NO Mark-of-the-Web is ever applied (browsers add
     it; zipfile does not), so the CLR-blocking field failure that motivated
     gui_main._unblock_dotnet_assemblies() cannot happen on this path.
  3. apply_update_and_restart() launches the STAGED NEW EXE in a tiny
     "apply" mode (--apply-update) and the caller exits the app: Windows
     locks a running exe's loaded DLLs, so the swap must happen from outside
     the process -- and the staged tree IS a complete copy of the app, so
     the new app applies itself. It waits for the old PID to exit, renames
     the old bundle pieces to *.old, COPIES itself into place (it is running
     from the staged tree, so it cannot move itself), relaunches the app,
     and rolls everything back if any step fails. Only bundle items are
     touched: the user's output/, input/ and data/ sit next to them and are
     never in the staged tree.
     WHY an exe and not a script (v0.10.1, field failure): v0.9.0 used a
     PowerShell helper in %TEMP% -- on locked-down PCs (no PowerShell at
     all for standard users) it was blocked silently, the app closed, and
     nothing was swapped. The one capability this design needs is "exes run
     from user-writable folders", which is already proven anywhere the app
     itself runs.
  4. cleanup_leftovers() (GUI startup) removes *.old trees and any stale
     data\\update from a previous or abandoned update.

Updates are only offered for packaged builds (sys.frozen) whose app folder
is writable; a read-only install (paths.py fell back to %LOCALAPPDATA%) gets
a "new version available" link instead -- see update_support().
"""
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from paths import DATA_ROOT, LOG_DIR, UPDATE_DIR, is_frozen
from version import APP_NAME, __version__

log = logging.getLogger("tsmis.update")

GITHUB_REPO = "yunusshaikh7/TSMIS-Reports-Exporter"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
# /releases/latest never returns prereleases or drafts — only full releases
# are ever offered.
_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_EXE_NAME = APP_NAME + ".exe"
# Bundle items the swap replaces / cleanup removes. Everything else next to
# the exe (output/, input/, data/) is user data and is never touched.
_BUNDLE_ITEMS = (_EXE_NAME, "_internal", "Start Here.txt")
_CHUNK = 256 * 1024
_API_TIMEOUT_S = 20
_DL_TIMEOUT_S = 60          # socket timeout per read while streaming the zip


class UpdateError(Exception):
    """An update step failed; the message is user-safe and UI-neutral."""


@dataclass
class UpdateInfo:
    """One available update, as resolved by check_for_update()."""
    version: str        # "0.9.0"
    tag: str            # "v0.9.0"
    asset_name: str     # "TSMIS-Exporter-v0.9.0-win64.zip"
    asset_url: str      # direct browser_download_url
    asset_size: int     # bytes (0 if the API omitted it)
    release_url: str    # human release page ("what's new")


# ------------------------------------------------------------ environment ---

def install_dir():
    """The onefolder app dir (next to the .exe). Only meaningful frozen."""
    return Path(sys.executable).resolve().parent


def update_support():
    """('ok' | 'link' | 'off', reason) -- what this installation can do.

    'ok'    packaged build, app folder writable: full one-click update.
    'link'  packaged build in a read-only spot (paths.py redirected data to
            %LOCALAPPDATA%): can only point the user at the release page.
    'off'   dev / console run: there is no bundle to replace.
    """
    if not is_frozen():
        return "off", "not a packaged build"
    if DATA_ROOT != install_dir():
        return "link", "the app folder is not writable (data redirected to %LOCALAPPDATA%)"
    return "ok", None


def current_variant():
    """Release-asset suffix for this install: the with-browser variant ships
    Playwright's Chromium inside _internal (same probe paths.py uses)."""
    if (install_dir() / "_internal" / "ms-playwright").is_dir():
        return "win64-with-browser"
    return "win64"


# ---------------------------------------------------------------- versions ---

def parse_version(text):
    """'v0.9.0' / '0.9.0' -> (0, 9, 0); None when unparseable."""
    m = re.match(r"v?(\d+(?:\.\d+)*)$", str(text or "").strip())
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def is_newer(remote, current):
    if not remote or not current:
        return False
    n = max(len(remote), len(current))
    return (remote + (0,) * (n - len(remote))) > (current + (0,) * (n - len(current)))


# -------------------------------------------------------------- the check ---

def _http_get(url, timeout):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"{APP_NAME.replace(' ', '-')}/{__version__} (self-update)",
        "Accept": "application/vnd.github+json",
    })
    # Default context = the Windows certificate store (corporate TLS
    # inspection roots included); default opener = the system proxy.
    return urllib.request.urlopen(req, timeout=timeout,
                                  context=ssl.create_default_context())


def check_for_update(current_version=None, variant=None):
    """Return an UpdateInfo when a newer release exists, else None.
    Raises UpdateError when the check itself cannot be completed.
    `current_version` / `variant` exist for testing; defaults are this build.
    """
    cur = parse_version(current_version or __version__)
    want = variant or current_variant()
    log.info("update check: current v%s, variant %s -> %s",
             current_version or __version__, want, _API_LATEST)
    try:
        with _http_get(_API_LATEST, _API_TIMEOUT_S) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:               # repo exists but has no releases yet
            log.info("update check: no releases published (HTTP 404)")
            return None
        log.warning("update check: HTTP %s from the releases API", e.code)
        raise UpdateError(f"the update service answered with an error (HTTP {e.code})") from e
    except (OSError, ValueError) as e:  # URLError/SSL/timeout/bad JSON
        log.warning("update check failed: %s: %s", type(e).__name__, e)
        raise UpdateError("could not reach github.com to check for updates "
                          "— check the internet connection") from e

    tag = data.get("tag_name") or ""
    remote = parse_version(tag)
    if remote is None:
        log.warning("update check: unrecognized release tag %r", tag)
        return None
    if not is_newer(remote, cur):
        log.info("update check: up to date (latest release is %s)", tag)
        return None

    suffix = f"-{want}.zip"
    assets = data.get("assets") or []
    asset = next((a for a in assets if (a.get("name") or "").endswith(suffix)), None)
    if asset is None:
        names = ", ".join(a.get("name") or "?" for a in assets) or "none"
        log.warning("update check: release %s has no %s asset (assets: %s)",
                    tag, suffix, names)
        raise UpdateError(f"version {tag} is out, but its download package "
                          "isn't available yet — try again later")
    info = UpdateInfo(
        version=".".join(str(p) for p in remote),
        tag=tag,
        asset_name=asset.get("name") or "",
        asset_url=asset.get("browser_download_url") or "",
        asset_size=int(asset.get("size") or 0),
        release_url=data.get("html_url") or RELEASES_PAGE,
    )
    log.info("update available: %s -> %s (%s, %.0f MB)",
             __version__, info.tag, info.asset_name, info.asset_size / 1e6)
    return info


# ------------------------------------------------------- download + stage ---

def download_and_stage(info, on_progress=None):
    """Download `info`'s zip and extract a verified bundle tree to
    UPDATE_DIR/staged (returned). Heavy — run on a worker thread.
    on_progress(done_bytes, total_bytes) is called as the stream advances."""
    mode, why = update_support()
    if mode != "ok":
        raise UpdateError(f"this installation cannot update itself ({why})")

    # Fresh staging area: never mix two versions' files.
    if UPDATE_DIR.exists():
        try:
            shutil.rmtree(UPDATE_DIR)
        except OSError as e:
            log.warning("could not clear %s: %s: %s", UPDATE_DIR, type(e).__name__, e)
            raise UpdateError("could not clear the update folder — "
                              "close any window showing it and try again") from e
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)

    if info.asset_size:
        free = shutil.disk_usage(UPDATE_DIR).free
        need = info.asset_size * 3      # zip + extracted tree + headroom
        if free < need:
            raise UpdateError("not enough free disk space for the update "
                              f"(needs about {need // 1_000_000} MB free, "
                              f"this drive has {free // 1_000_000} MB)")

    zip_path = UPDATE_DIR / (info.asset_name or "update.zip")
    log.info("downloading %s (%d bytes) -> %s", info.asset_url, info.asset_size, zip_path)
    done = 0
    try:
        with _http_get(info.asset_url, _DL_TIMEOUT_S) as resp, open(zip_path, "wb") as out:
            total = info.asset_size or int(resp.headers.get("Content-Length") or 0)
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
    except OSError as e:
        log.warning("download failed after %d bytes: %s: %s", done, type(e).__name__, e)
        raise UpdateError("the update download failed — "
                          "check the internet connection and try again") from e
    if info.asset_size and done != info.asset_size:
        raise UpdateError(f"the update download was incomplete "
                          f"({done // 1_000_000} of {info.asset_size // 1_000_000} MB) "
                          "— try again")

    extract_dir = UPDATE_DIR / "extract"
    log.info("extracting %s (%d bytes)", zip_path.name, done)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except (zipfile.BadZipFile, OSError) as e:
        log.warning("extract failed: %s: %s", type(e).__name__, e)
        raise UpdateError("the downloaded file is not a valid app package") from e
    zip_path.unlink(missing_ok=True)    # free the space before the app runs on

    root = _bundle_root(extract_dir)    # the zip wraps a "TSMIS Exporter\" folder
    staged = UPDATE_DIR / "staged"
    root.rename(staged)                 # same volume: instant
    if extract_dir.exists() and root != extract_dir:
        shutil.rmtree(extract_dir, ignore_errors=True)

    if not (staged / _EXE_NAME).is_file() or not (staged / "_internal").is_dir():
        raise UpdateError("the downloaded package is missing expected app files")
    log.info("update %s staged at %s", info.tag, staged)
    return staged


def _bundle_root(extract_dir):
    """The folder inside the extracted zip that holds the exe + _internal
    (Compress-Archive wraps the bundle in one top-level folder)."""
    if (extract_dir / _EXE_NAME).is_file():
        return extract_dir
    for child in extract_dir.iterdir():
        if child.is_dir() and (child / _EXE_NAME).is_file():
            return child
    raise UpdateError("the downloaded package does not contain the app")


# ------------------------------------------------------------- the swap -----
# v0.10.1: the swap "helper" is the STAGED NEW APP itself, launched with
# SWAP_FLAG (gui_main branches into run_swap_mode before anything heavy
# loads). v0.9.0 used a PowerShell script in %TEMP%; locked-down PCs that
# block PowerShell outright killed it silently — the app closed, nothing was
# swapped, and the staged download just sat in data\update. The replacement
# needs no PowerShell/cmd/scripts/admin: only "exes run from user folders",
# which is proven anywhere the app itself runs.

SWAP_FLAG = "--apply-update"
_SWAP_TIMEOUT_S = 120        # max wait for the old app's PID to exit
_RETRY_ATTEMPTS = 12         # Defender / slow handle release after exit
_RETRY_DELAY_S = 0.5


def apply_update_and_restart(staged_dir):
    """Launch the staged new exe in swap mode, detached. The CALLER must then
    close the app promptly — the swap process waits on this PID (up to 120 s)
    before touching anything. Returns the swap process's exe path.

    Raises UpdateError if the swap process can't start or dies immediately
    (e.g. a policy blocks running it) — the app then STAYS OPEN with the old
    version still intact."""
    mode, why = update_support()
    if mode != "ok":
        raise UpdateError(f"this installation cannot update itself ({why})")
    staged = Path(staged_dir)
    new_exe = staged / _EXE_NAME
    if not new_exe.is_file():
        raise UpdateError("the downloaded update is no longer on disk — "
                          "download it again")

    helper_log = LOG_DIR / "update_helper.log"
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        proc = subprocess.Popen(
            [str(new_exe), SWAP_FLAG, str(install_dir()), str(os.getpid()),
             str(helper_log)],
            creationflags=flags, close_fds=True, cwd=str(staged),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    except OSError as e:
        log.warning("swap process failed to start: %s: %s", type(e).__name__, e)
        raise UpdateError("the update process could not be started — "
                          "install the new version manually from the "
                          "releases page") from e
    # A blocked/broken exe dies within moments; catch that while the app is
    # still open instead of closing into a swap that never happens (the
    # silent-failure mode the PowerShell helper had).
    time.sleep(1.5)
    rc = proc.poll()
    if rc is not None:
        log.warning("swap process exited immediately (code %s)", rc)
        raise UpdateError("the update process exited before it could start "
                          "— install the new version manually from the "
                          "releases page")
    log.info("swap process launched: %s (waits for pid %d, installs into %s)",
             new_exe, os.getpid(), install_dir())
    return str(new_exe)


# ---- swap mode (runs inside the STAGED exe; never returns) -----------------

def run_swap_mode(argv):
    """Entry for `TSMIS Exporter.exe --apply-update <app_dir> <pid> <log>`.

    Called by gui_main BEFORE logging/paths/CLR setup: this process runs from
    the staged tree under the install's data\\update\\, so paths.py-derived
    locations would point at the WRONG (staged) tree — everything here takes
    explicit paths and logs by direct appends to <log>. Never returns."""
    try:
        i = argv.index(SWAP_FLAG)
        app_dir = Path(argv[i + 1])
        pid = int(argv[i + 2])
        log_file = Path(argv[i + 3])
    except (ValueError, IndexError):
        os._exit(2)
    staged = Path(sys.executable).resolve().parent
    ok = perform_swap(staged, app_dir, pid, log_file)
    os._exit(0 if ok else 1)


def _swap_log(log_file, message):
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def _wait_pid_exit(pid, timeout_s):
    """True once `pid` has exited (or never existed); False on timeout.
    ctypes only — no psutil in the bundle."""
    import ctypes
    SYNCHRONIZE = 0x00100000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
    if not handle:
        return True                      # already gone (or pid was recycled)
    try:
        WAIT_TIMEOUT = 0x00000102
        rc = kernel32.WaitForSingleObject(handle, int(timeout_s * 1000))
        return rc != WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def _retry(fn):
    """Run `fn` with the helper's retry cadence (Defender / slow handle
    release can hold files briefly after the app exits)."""
    for attempt in range(_RETRY_ATTEMPTS - 1):
        try:
            return fn()
        except OSError:
            time.sleep(_RETRY_DELAY_S)
    return fn()                          # last attempt: let the error surface


def _remove_tree(path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def perform_swap(staged, app_dir, pid, log_file, *, relaunch=True,
                 wait_timeout_s=_SWAP_TIMEOUT_S, show_dialog=True):
    """The swap itself (separated from run_swap_mode so a sandbox test can
    drive it against fake trees). Waits for `pid` to exit, then installs in
    TWO PHASES so a half-installed (mixed-version) tree is impossible:

      1. COPY every staged piece to `<name>.new` next to its target (this
         process runs FROM `staged`, so it cannot move itself). The big,
         slow, failure-prone work (a ~150 MB copytree under live Defender
         scanning) happens while the installed app is completely untouched —
         any failure here is a clean abort with the old version intact.
      2. Pure RENAMES: live -> `.old`, `.new` -> live. Instant on the same
         volume, and a failure rolls back with renames too — never by
         deleting a half-copied tree (v0.10.2 field failure: the one-phase
         copy could fail mid-`_internal`, the delete-based rollback could
         fail on a Defender-held file, and the app relaunched as a NEW exe
         with PARTIAL/old internals — "says 0.10.2 but features missing").

    User data (data\\, output\\, input\\) is never in the staged tree and is
    never touched. Leftover `.old`/`.new` pieces are removed by
    cleanup_leftovers() on the next launch. Returns True when the new
    version is in place."""
    _swap_log(log_file, f"swap started: waiting for the app (pid {pid}) to exit")
    if not _wait_pid_exit(pid, wait_timeout_s):
        _swap_log(log_file, f"app still running after {wait_timeout_s}s - "
                            "update NOT applied")
        return False
    time.sleep(0.6)                      # let file handles settle

    if not (staged / _EXE_NAME).is_file():
        _swap_log(log_file, f"staged update is incomplete (no {_EXE_NAME}) - "
                            "update NOT applied")
        return False

    # ---- phase 1: copy everything in as *.new (old app untouched) ----------
    items = sorted(staged.iterdir())
    news = []                            # (name, new_path) ready to rename in
    for item in items:
        new = app_dir / (item.name + ".new")
        try:
            _retry(lambda n=new: _remove_tree(n))
            if item.is_dir():
                shutil.copytree(item, new)
            else:
                shutil.copy2(item, new)
            news.append((item.name, new))
            _swap_log(log_file, f"prepared: {item.name}.new")
        except OSError as e:
            _swap_log(log_file, f"swap ABORTED preparing {item.name}.new: "
                                f"{type(e).__name__}: {e}")
            for _name, n in news:
                try:
                    _remove_tree(n)
                except OSError:
                    pass
            _swap_log(log_file, "nothing was changed - the installed version "
                                "is untouched; update NOT applied")
            if show_dialog:
                _message_box("The update could not be prepared, so nothing "
                             f"was changed.\nDetails: {log_file}")
            if relaunch:
                _relaunch(app_dir, log_file)
            return False

    # ---- phase 2: rename-swap each piece (instant; rollback = renames) -----
    moved = []                           # (dest, bak) pairs renamed to .old
    failed = None
    for name, new in news:
        dest = app_dir / name
        bak = app_dir / (name + ".old")
        try:
            if bak.exists():
                _retry(lambda b=bak: _remove_tree(b))
            if dest.exists():
                _retry(lambda d=dest, b=bak: d.rename(b))
                moved.append((dest, bak))
            _retry(lambda n=new, d=dest: n.rename(d))
            _swap_log(log_file, f"installed: {name}")
        except OSError as e:
            failed = f"{name}: {type(e).__name__}: {e}"
            _swap_log(log_file, f"swap FAILED on {failed}")
            break

    if failed:
        # Undo with renames only: each installed piece goes back to .new,
        # its .old back into place. No deletes of fresh trees involved.
        _swap_log(log_file, "rolling back (renames only)")
        restored = True
        for dest, bak in reversed(moved):
            try:
                if dest.exists():
                    _retry(lambda d=dest: d.rename(
                        d.with_name(d.name + ".new")))
                _retry(lambda b=bak, d=dest: b.rename(d))
            except OSError as e:
                restored = False
                _swap_log(log_file, f"rollback of {dest.name} FAILED: "
                                    f"{type(e).__name__}: {e}")
        _swap_log(log_file, "previous version restored" if restored else
                            "previous version PARTIALLY restored - reinstall "
                            "the app from the releases page")
        if show_dialog:
            _message_box("The update could not be applied, so the previous "
                         f"version was kept.\nDetails: {log_file}")

    if relaunch:
        _relaunch(app_dir, log_file)

    # Leftover *.old/*.new pieces and the staged tree THIS process runs from
    # are removed by cleanup_leftovers() at the relaunched app's next startup
    # (this process exits immediately, releasing its own files).
    _swap_log(log_file, "swap done" if not failed else "swap failed")
    return failed is None


def _relaunch(app_dir, log_file):
    """Start the app in `app_dir` detached (whichever version sits there)."""
    try:
        subprocess.Popen(
            [str(app_dir / _EXE_NAME)], cwd=str(app_dir), close_fds=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        _swap_log(log_file, "app relaunched")
    except OSError as e:
        _swap_log(log_file, f"relaunch FAILED: {type(e).__name__}: {e} - "
                            "start the app manually")


def _message_box(text):
    """Last-resort user surface for a swap failure (the app is closed)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x30)  # MB_ICONWARNING
    except Exception:
        pass


def last_swap_failure(max_age_hours=48):
    """One line describing a RECENT failed swap from update_helper.log, or
    None. The swap helper runs after the app has closed, so a rollback can
    only leave a file behind — the next launch reads it back and tells the
    user the update rolled back instead of leaving a silent mystery (field
    report: an update "applied", the app reopened on the old version, and
    nothing said why). Only the LAST helper run counts: a failure followed by
    a successful swap is history."""
    path = LOG_DIR / "update_helper.log"
    try:
        if not path.is_file():
            return None
        if time.time() - path.stat().st_mtime > max_age_hours * 3600:
            return None
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-60:]):
        if "swap done" in line:
            return None
        if "swap FAILED" in line or "update NOT applied" in line:
            return line.strip()
    return None


# --------------------------------------------------------------- cleanup ----

def _clear_webview_caches():
    """Drop the GUI's WebView2 HTTP caches (NEVER Local Storage — the theme
    choice lives there). The persistent profile (data\\webview2) can serve a
    CACHED app.js/index.html after the files on disk changed: a just-updated
    app then shows the OLD interface under the NEW version number (field
    report, v0.10.2 update — "says 0.10.2 but features missing"). The caches
    only ever hold the app's own three UI files, so clearing on every launch
    is cheap and kills the whole staleness class (manual zip-overwrite
    installs included)."""
    try:
        from paths import WEBVIEW_PROFILE_DIR
        profile = Path(WEBVIEW_PROFILE_DIR)
        if not profile.is_dir():
            return
        removed = []
        for pattern in ("Cache", "Code Cache", "GPUCache", "Service Worker",
                        "*/Cache", "*/Code Cache", "*/GPUCache",
                        "*/*/Cache", "*/*/Code Cache", "*/*/GPUCache",
                        "*/*/Service Worker"):
            for hit in profile.glob(pattern):
                if hit.is_dir():
                    shutil.rmtree(hit, ignore_errors=True)
                    removed.append(str(hit.relative_to(profile)))
        if removed:
            log.info("webview cache cleared: %s", ", ".join(removed))
    except Exception as e:                  # never block startup over a cache
        log.info("webview cache clear skipped (%s)", type(e).__name__)


def cleanup_leftovers():
    """Remove what a finished (or abandoned) update leaves behind: the
    data\\update staging area and any *.old / *.new bundle pieces the helper
    couldn't delete while the new app was already starting — and the WebView2
    HTTP caches, so the interface on screen is always the one on disk.
    Best-effort and cheap; called on every GUI launch, before the CLR loads."""
    _clear_webview_caches()
    if not is_frozen():
        return
    targets = [UPDATE_DIR] + [install_dir() / (name + suffix)
                              for name in _BUNDLE_ITEMS
                              for suffix in (".old", ".new")]
    removed, failed = [], []
    for t in targets:
        try:
            if t.is_dir():
                shutil.rmtree(t)
                removed.append(t.name)
            elif t.is_file():
                t.unlink()
                removed.append(t.name)
        except OSError as e:
            failed.append(f"{t.name} ({type(e).__name__})")
    if removed or failed:
        log.info("update cleanup: removed %s%s",
                 ", ".join(removed) or "nothing",
                 ("; could not remove " + ", ".join(failed) +
                  " (will retry next launch)") if failed else "")

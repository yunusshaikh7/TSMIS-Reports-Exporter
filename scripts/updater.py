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
from version import APP_NAME, __build__, __version__

log = logging.getLogger("tsmis.update")

GITHUB_REPO = "yunusshaikh7/TSMIS-Reports-Exporter"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
# The dev channel looks at the whole release list (newest first) because
# prereleases never appear in /releases/latest — that's exactly what keeps
# the stable channel blind to dev builds.
_API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=15"
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
    version: str        # "0.9.0" — or the dev tag itself ("dev-7")
    tag: str            # "v0.9.0" / "dev-7"
    asset_name: str     # "TSMIS-Exporter-v0.9.0-win64.zip"
    asset_url: str      # direct browser_download_url
    asset_size: int     # bytes (0 if the API omitted it)
    release_url: str    # human release page ("what's new")
    dev: bool = False   # a prerelease from the dev channel (label it so)


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


def installed_tag(build=None):
    """THIS build's identity as a release tag: a dev build carries the
    prerelease tag the dev-release workflow stamped into version.__build__
    ("dev-7"); a stable build is its version tag ("v0.10.1")."""
    b = __build__ if build is None else build
    return b or f"v{__version__}"


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


def check_for_update(current_version=None, variant=None, channel="stable",
                     build=None):
    """Return an UpdateInfo when the channel offers something this install
    doesn't run yet, else None. Raises UpdateError when the check itself
    cannot be completed.

    stable: the latest full release (prereleases never appear in
            /releases/latest), offered when strictly newer — or
            equal-versioned when THIS install is a dev build (the exit ramp
            off the dev channel).
    dev:    the newest release of ANY kind (prereleases included), offered
            whenever its tag differs from this build's identity — dev builds
            iterate without version bumps, so the test is "different", not
            "newer", and a stable release published after the dev builds
            takes the install back to stable automatically.

    `current_version` / `variant` / `build` exist for testing; defaults are
    this build.
    """
    cur = parse_version(current_version or __version__)
    bld = __build__ if build is None else build
    want = variant or current_variant()
    url = _API_RELEASES if channel == "dev" else _API_LATEST
    log.info("update check: current %s, variant %s, channel %s -> %s",
             installed_tag(bld), want, channel, url)
    try:
        with _http_get(url, _API_TIMEOUT_S) as resp:
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

    if channel == "dev":
        releases = [r for r in (data if isinstance(data, list) else [])
                    if isinstance(r, dict) and not r.get("draft")]
        if not releases:
            log.info("update check: the dev channel has no releases")
            return None
        data = releases[0]              # the API lists newest first
        tag = data.get("tag_name") or ""
        if not tag or tag == installed_tag(bld):
            log.info("update check: up to date (dev channel newest is %s)", tag)
            return None
        remote = parse_version(tag)
        version = ".".join(str(p) for p in remote) if remote else tag
        dev = bool(data.get("prerelease")) or remote is None
    else:
        tag = data.get("tag_name") or ""
        remote = parse_version(tag)
        if remote is None:
            log.warning("update check: unrecognized release tag %r", tag)
            return None
        same = remote and cur and not is_newer(remote, cur) and not is_newer(cur, remote)
        if not is_newer(remote, cur) and not (bld and same):
            # A dev-build install treats the SAME stable version as an
            # update — switching the channel back must have an exit ramp.
            log.info("update check: up to date (latest release is %s)", tag)
            return None
        version = ".".join(str(p) for p in remote)
        dev = False

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
        version=version,
        tag=tag,
        asset_name=asset.get("name") or "",
        asset_url=asset.get("browser_download_url") or "",
        asset_size=int(asset.get("size") or 0),
        release_url=data.get("html_url") or RELEASES_PAGE,
        dev=dev,
    )
    log.info("update available: %s -> %s (%s, %.0f MB%s)",
             installed_tag(bld), info.tag, info.asset_name,
             info.asset_size / 1e6, ", dev" if dev else "")
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
    drive it against fake trees). Waits for `pid` to exit, renames each old
    bundle piece in `app_dir` to *.old, COPIES the staged piece in (this
    process runs FROM `staged`, so it cannot move itself), relaunches the
    app, and rolls everything back if any step fails. User data (data\\,
    output\\, input\\) is never in the staged tree and is never touched.
    Returns True when the new version is in place."""
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

    # Old piece -> *.old (pure rename: atomic, fails clean), staged piece ->
    # COPIED into place. Tracked so a failure rolls everything back.
    moved = []                           # (dest, bak) pairs that were renamed
    failed = None
    for item in sorted(staged.iterdir()):
        dest = app_dir / item.name
        bak = app_dir / (item.name + ".old")
        try:
            if bak.exists():
                _retry(lambda b=bak: _remove_tree(b))
            if dest.exists():
                _retry(lambda d=dest, b=bak: d.rename(b))
                moved.append((dest, bak))
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            _swap_log(log_file, f"installed: {item.name}")
        except OSError as e:
            failed = f"{item.name}: {type(e).__name__}: {e}"
            _swap_log(log_file, f"swap FAILED on {failed}")
            break

    if failed:
        for dest, bak in moved:
            try:
                _remove_tree(dest)
                _retry(lambda b=bak, d=dest: b.rename(d))
            except OSError as e:
                _swap_log(log_file, f"rollback of {dest} FAILED: "
                                    f"{type(e).__name__}: {e}")
        _swap_log(log_file, "previous version restored")
        if show_dialog:
            _message_box("The update could not be applied, so the previous "
                         f"version was kept.\nDetails: {log_file}")

    if relaunch:
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

    # Leftover *.old pieces and the staged tree THIS process runs from are
    # removed by cleanup_leftovers() at the relaunched app's next startup
    # (this process exits immediately, releasing its own files).
    _swap_log(log_file, "swap done" if not failed else "swap failed")
    return failed is None


def _message_box(text):
    """Last-resort user surface for a swap failure (the app is closed)."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x30)  # MB_ICONWARNING
    except Exception:
        pass


# --------------------------------------------------------------- cleanup ----

def cleanup_leftovers():
    """Remove what a finished (or abandoned) update leaves behind: the
    data\\update staging area and any *.old bundle pieces the helper couldn't
    delete while the new app was already starting. Best-effort and cheap (a
    handful of stats); called on every GUI launch, before the CLR loads."""
    if not is_frozen():
        return
    targets = [UPDATE_DIR] + [install_dir() / (name + ".old") for name in _BUNDLE_ITEMS]
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

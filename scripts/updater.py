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
  3. apply_update_and_restart() writes a small PowerShell helper to %TEMP%
     and the caller exits the app: Windows locks a running exe and its
     loaded DLLs, so the swap must happen from outside the process. The
     helper waits for the app PID to exit, moves the old bundle pieces to
     *.old, moves the staged ones in (same volume -- instant renames),
     relaunches the app, and rolls everything back if any move fails. Only
     bundle items are touched: the user's output/, input/ and data/ sit next
     to them and are never in the staged tree.
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

# Tokens (@NAME@) are substituted by build_helper_script — a template instead
# of an f-string because the PowerShell is full of braces. PS 5.1 compatible.
_HELPER_TEMPLATE = r"""# TSMIS Exporter self-update helper (auto-generated; deletes itself when done).
# Waits for the app to exit, swaps the staged new version into the app folder
# (user data folders are not touched), relaunches the app, and rolls back if
# any move fails.
$ErrorActionPreference = 'Stop'
$appDir  = @APP_DIR@
$staged  = @STAGED@
$exeName = @EXE_NAME@
$appPid  = @PID@
$logFile = @LOG_FILE@

function Log([string]$m) {
    try {
        Add-Content -LiteralPath $logFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    } catch { }
}
function Move-WithRetry([string]$from, [string]$to) {
    # Defender / slow handle release can hold a file briefly after exit.
    for ($i = 0; $i -lt 12; $i++) {
        try { Move-Item -LiteralPath $from -Destination $to -Force; return }
        catch { Start-Sleep -Milliseconds 500 }
    }
    Move-Item -LiteralPath $from -Destination $to -Force
}
function Rename-WithRetry([string]$path, [string]$newName) {
    # A PURE rename (atomic; fails clean). Move-Item must not be used to put
    # the old bundle aside: when a rename fails on a locked file it falls
    # back to copy+delete, which can leave a stray or half-deleted tree.
    for ($i = 0; $i -lt 12; $i++) {
        try { Rename-Item -LiteralPath $path -NewName $newName -Force; return }
        catch { Start-Sleep -Milliseconds 500 }
    }
    Rename-Item -LiteralPath $path -NewName $newName -Force
}

Log ('helper started: waiting for the app (pid {0}) to exit' -f $appPid)
$exeBase  = [System.IO.Path]::GetFileNameWithoutExtension($exeName)
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    $p = Get-Process -Id $appPid -ErrorAction SilentlyContinue
    if (-not $p -or $p.ProcessName -ne $exeBase) { break }   # exited (or pid reused)
    Start-Sleep -Milliseconds 400
}
$p = Get-Process -Id $appPid -ErrorAction SilentlyContinue
if ($p -and $p.ProcessName -eq $exeBase) {
    Log 'app still running after 120s - update NOT applied'
    exit 1
}
Start-Sleep -Milliseconds 600    # let file handles settle

if (-not (Test-Path -LiteralPath (Join-Path $staged $exeName))) {
    Log ('staged update is incomplete (no {0}) - update NOT applied' -f $exeName)
    exit 1
}

# Swap: each old bundle piece -> *.old (pure rename), staged piece -> in
# place (tracked so a failure can roll everything back). Same volume.
$moved  = @()
$failed = $false
foreach ($item in (Get-ChildItem -LiteralPath $staged)) {
    $dest = Join-Path $appDir $item.Name
    $bak  = $dest + '.old'
    try {
        if (Test-Path -LiteralPath $bak)  { Remove-Item -LiteralPath $bak -Recurse -Force }
        if (Test-Path -LiteralPath $dest) {
            Rename-WithRetry $dest ($item.Name + '.old')
            $moved += @{ dest = $dest; bak = $bak; name = $item.Name }
        }
        Move-WithRetry $item.FullName $dest
        Log ('installed: ' + $item.Name)
    } catch {
        Log ('swap FAILED on ' + $item.Name + ': ' + $_.Exception.Message)
        $failed = $true
        break
    }
}

if ($failed) {
    foreach ($m in $moved) {
        try {
            if (Test-Path -LiteralPath $m.dest) { Remove-Item -LiteralPath $m.dest -Recurse -Force }
            Rename-WithRetry $m.bak $m.name
        } catch { Log ('rollback of ' + $m.dest + ' FAILED: ' + $_.Exception.Message) }
    }
    Log 'previous version restored'
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show(
            ('The update could not be applied, so the previous version was kept.' +
             [Environment]::NewLine + 'Details: ' + $logFile),
            'TSMIS Exporter', 'OK', 'Warning')
    } catch { }
}

try {
    Start-Process -FilePath (Join-Path $appDir $exeName) -WorkingDirectory $appDir
    Log 'app relaunched'
} catch {
    Log ('relaunch FAILED: ' + $_.Exception.Message + ' - start the app manually')
}

if (-not $failed) {
    # Best-effort cleanup; anything still locked is removed at next startup.
    foreach ($m in $moved) {
        try { Remove-Item -LiteralPath $m.bak -Recurse -Force } catch { Log ('cleanup: left ' + $m.bak) }
    }
    try { Remove-Item -LiteralPath (Split-Path -Parent $staged) -Recurse -Force } catch { }
}
Log 'helper done'
try { Remove-Item -LiteralPath $PSCommandPath -Force } catch { }
"""


def _ps_quote(value):
    """A PowerShell single-quoted string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def build_helper_script(app_dir, staged_dir, exe_name, pid, log_file):
    """The swap helper's PowerShell source (pure function, so it's testable
    against a sandbox install tree)."""
    script = _HELPER_TEMPLATE
    for token, value in (
        ("@APP_DIR@", _ps_quote(app_dir)),
        ("@STAGED@", _ps_quote(staged_dir)),
        ("@EXE_NAME@", _ps_quote(exe_name)),
        ("@PID@", str(int(pid))),
        ("@LOG_FILE@", _ps_quote(log_file)),
    ):
        script = script.replace(token, value)
    return script


def _powershell_exe():
    ps = (Path(os.environ.get("SystemRoot", r"C:\Windows"))
          / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
    return str(ps) if ps.is_file() else "powershell.exe"


def apply_update_and_restart(staged_dir):
    """Write the swap helper to %TEMP% and launch it detached. The CALLER must
    then close the app promptly — the helper waits on this process's PID
    (up to 120 s) before touching anything. Returns the helper script path."""
    mode, why = update_support()
    if mode != "ok":
        raise UpdateError(f"this installation cannot update itself ({why})")
    staged = Path(staged_dir)
    if not (staged / _EXE_NAME).is_file():
        raise UpdateError("the downloaded update is no longer on disk — "
                          "download it again")

    helper = (Path(tempfile.gettempdir())
              / f"tsmis_update_{os.getpid()}_{int(time.time())}.ps1")
    helper.write_text(
        build_helper_script(install_dir(), staged, _EXE_NAME, os.getpid(),
                            LOG_DIR / "update_helper.log"),
        encoding="utf-8-sig")           # BOM so PowerShell 5.1 reads it as UTF-8

    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [_powershell_exe(), "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-File", str(helper)],
        creationflags=flags, close_fds=True, cwd=tempfile.gettempdir(),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    log.info("update helper launched: %s (waits for pid %d, staged %s)",
             helper, os.getpid(), staged)
    return helper


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

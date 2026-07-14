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
import hashlib
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
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
# Full release LIST (newest-first per GitHub, but we pick by version, not order)
# -- used only to resolve the PREVIOUS release for the Settings "revert" control.
_API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100"
_EXE_NAME = APP_NAME + ".exe"
# Bundle items the swap replaces / cleanup removes. Everything else next to
# the exe (output/, input/, data/) is user data and is never touched. The two
# readmes ride the allowlist so a content edit in build/ propagates on update;
# the swap runs in the STAGED exe, so this list governs each install.
_BUNDLE_ITEMS = (_EXE_NAME, "_internal", "Start Here.txt", "IT-README.txt")
_CHUNK = 256 * 1024
_API_TIMEOUT_S = 20
_DL_TIMEOUT_S = 60          # socket timeout per read while streaming the zip
_DL_RETRY_ATTEMPTS = 3      # bounded retries for a transient network failure mid-download
# /releases is paginated (per_page=100). Follow rel="next" up to this many pages so a
# revert target older than the newest 100 releases is still found; the cap is a safety
# bound far past any real release history (50 * 100 = 5000 releases).
_RELEASES_PAGE_CAP = 50


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
    asset_digest: str = ""      # "sha256:HEX" the GitHub API reports, when present
    asset_sha256_url: str = ""  # URL of the published <asset>.sha256, when present


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


def safe_release_url(url):
    """Constrain a release URL to our own GitHub repo before it is handed to a
    browser. UpdateInfo.release_url comes from the GitHub API's html_url —
    delivered over TLS, but still EXTERNAL data: a forged or TLS-inspected /
    MITM'd API response could put an arbitrary scheme or host there, and
    webbrowser.open() on a non-https value (file:, javascript:, a custom
    handler) can launch something unexpected. Return `url` only when it is an
    https://github.com/<this repo>/… link; otherwise the releases page built
    from the hardcoded GITHUB_REPO constant — which, since updates only ever
    target the latest release, lands on the same page anyway."""
    try:
        parts = urllib.parse.urlsplit(str(url or ""))
        if (parts.scheme == "https"
                and (parts.hostname or "").lower() == "github.com"
                and parts.path.lstrip("/").lower().startswith(
                    GITHUB_REPO.lower() + "/")):
            return url
    except (ValueError, TypeError):
        pass
    return RELEASES_PAGE


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

    info = _asset_info_from_release(data, remote, tag, want)
    log.info("update available: %s -> %s (%s, %.0f MB)",
             __version__, info.tag, info.asset_name, info.asset_size / 1e6)
    return info


def _asset_info_from_release(release, remote, tag, want):
    """Build an UpdateInfo for the `want` variant from a GitHub release object,
    or raise UpdateError if that variant's zip isn't published on it. Shared by
    the latest-update check and the revert resolver, so both pick the asset and
    its companion checksum the same way."""
    suffix = f"-{want}.zip"
    assets = release.get("assets") or []
    asset = next((a for a in assets if (a.get("name") or "").endswith(suffix)), None)
    if asset is None:
        names = ", ".join(a.get("name") or "?" for a in assets) or "none"
        log.warning("release %s has no %s asset (assets: %s)", tag, suffix, names)
        raise UpdateError(f"version {tag} is out, but its download package "
                          "isn't available yet — try again later")
    # Companion checksum: the release publishes <asset>.sha256 next to each zip
    # (see .github/workflows/release.yml); the API may also carry the asset's own
    # digest. download_and_stage verifies the download against whichever exists.
    sha_name = (asset.get("name") or "") + ".sha256"
    sha_asset = next((a for a in assets if (a.get("name") or "") == sha_name), None)
    return UpdateInfo(
        version=".".join(str(p) for p in remote),
        tag=tag,
        asset_name=asset.get("name") or "",
        asset_url=asset.get("browser_download_url") or "",
        asset_size=int(asset.get("size") or 0),
        release_url=release.get("html_url") or RELEASES_PAGE,
        asset_digest=asset.get("digest") or "",
        asset_sha256_url=(sha_asset.get("browser_download_url") if sha_asset else "") or "",
    )


def _next_link(link_header):
    """The rel="next" URL from a GitHub `Link` response header, or '' when there is
    no next page. Link header form: `<url>; rel="next", <url>; rel="last"`."""
    for part in (link_header or "").split(","):
        seg = [s.strip() for s in part.split(";")]
        if len(seg) < 2:
            continue
        url = seg[0].strip("<>")
        if any(p.replace(" ", "").lower() in ('rel="next"', "rel=next") for p in seg[1:]):
            return url
    return ""


def _fetch_release_list():
    """Every published release, following GitHub's pagination past the per_page=100
    cap (releases-list-capped-100 blindspot — a revert target older than the newest
    100 releases would otherwise be invisible). Raises the same urllib/JSON errors as
    a single fetch, for the caller to translate."""
    url = _API_RELEASES
    out = []
    for _ in range(_RELEASES_PAGE_CAP):
        with _http_get(url, _API_TIMEOUT_S) as resp:
            page = json.load(resp)
            nxt = _next_link((resp.headers or {}).get("Link"))
        if not isinstance(page, list):
            break
        out.extend(page)
        if not nxt:
            break
        url = nxt
    return out


def resolve_previous_release(current_version=None, variant=None):
    """The newest FULL release strictly OLDER than this build, as an UpdateInfo
    for the current variant — the target of the Settings "revert to previous
    version" control. Lists /releases (not /latest, which never returns older
    tags), ignores drafts and prereleases, and picks by VERSION NUMBER, not
    GitHub's list order (that ordering bug once broke the dev channel). Returns
    None when there is no older release / no matching asset; raises UpdateError
    when the list itself cannot be fetched.
    `current_version` / `variant` exist for testing; defaults are this build.
    """
    cur = parse_version(current_version or __version__)
    if cur is None:
        return None
    want = variant or current_variant()
    log.info("revert: resolving newest release older than v%s, variant %s",
             current_version or __version__, want)
    try:
        data = _fetch_release_list()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        log.warning("revert: HTTP %s from the releases API", e.code)
        raise UpdateError(f"the update service answered with an error (HTTP {e.code})") from e
    except (OSError, ValueError) as e:   # URLError/SSL/timeout/bad JSON
        log.warning("revert: release list fetch failed: %s: %s", type(e).__name__, e)
        raise UpdateError("could not reach github.com to look up earlier versions "
                          "— check the internet connection") from e
    if not isinstance(data, list):
        return None
    candidates = []                      # (version_tuple, tag, release_obj)
    for rel in data:
        if not isinstance(rel, dict) or rel.get("draft") or rel.get("prerelease"):
            continue
        tag = rel.get("tag_name") or ""
        ver = parse_version(tag)
        if ver is None or not is_newer(cur, ver):     # keep only ver strictly < cur
            continue
        candidates.append((ver, tag, rel))
    # Newest-version-first; return the first that actually has THIS variant's
    # zip. A very old release may predate the with-browser variant, so skip to
    # the next-older one rather than failing with the forward check's
    # "try again later" message (which is wrong here — that release never had it).
    for ver, tag, rel in sorted(candidates, key=lambda c: c[0], reverse=True):
        try:
            info = _asset_info_from_release(rel, ver, tag, want)
        except UpdateError:
            log.info("revert: release %s has no %s package; trying an older one", tag, want)
            continue
        log.info("revert target: v%s -> %s (%s)", __version__, info.tag, info.asset_name)
        return info
    log.info("revert: no full release older than v%s has a %s package", __version__, want)
    return None


# ------------------------------------------------------- download + stage ---

def _expected_sha256(info):
    """The expected SHA-256 (lowercase hex) for info's asset, or None when none
    is published. Prefers the companion <asset>.sha256 file (which we publish and
    a user can verify by hand), then the GitHub API's own asset digest. Both
    arrive over the same TLS as the rest of the check, so this guards against a
    corrupted / truncated / wrong-asset download -- NOT against a forged release
    (that is what code-signing, the planned next step, is for)."""
    if info.asset_sha256_url:
        try:
            with _http_get(info.asset_sha256_url, _API_TIMEOUT_S) as resp:
                text = resp.read(4096).decode("utf-8", "replace")
            token = (text.strip().split() or [""])[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", token):
                return token
            log.warning("update: published .sha256 content was unrecognized")
        except (OSError, ValueError) as e:
            log.warning("update: could not fetch the .sha256 file (%s: %s)",
                        type(e).__name__, e)
    digest = (info.asset_digest or "").strip().lower()
    if digest.startswith("sha256:"):
        token = digest.split(":", 1)[1]
        if re.fullmatch(r"[0-9a-f]{64}", token):
            return token
    return None


def _sha256_file(path):
    """The SHA-256 (lowercase hex) of a file, streamed so a ~150 MB exe needn't be
    read into memory."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _bundle_digest(staged):
    """One SHA-256 over the ENTIRE launchable/installable staged bundle — every file
    under each `_BUNDLE_ITEMS` entry that exists (the exe AND the code-bearing
    `_internal/**` tree AND the readmes), folded in by sorted POSIX relative path so
    the result is order-stable. This is the trust record the swap re-verifies, so
    tampering with ANY launched/installed file in the user-writable staged folder —
    not just the exe — is detected before the swap. Returns the hex digest, or None
    when the staged tree can't be fully read (treated as unverifiable = refuse)."""
    staged = Path(staged)
    entries = []                          # (posix_relpath, abspath)
    try:
        for name in _BUNDLE_ITEMS:
            item = staged / name
            if item.is_dir():
                entries.extend((p.relative_to(staged).as_posix(), p)
                               for p in item.rglob("*") if p.is_file())
            elif item.is_file():
                entries.append((item.relative_to(staged).as_posix(), item))
    except OSError:
        return None
    entries.sort(key=lambda t: t[0])
    h = hashlib.sha256()
    try:
        for rel, p in entries:
            h.update(rel.encode("utf-8") + b"\0" + _sha256_file(p).encode("ascii") + b"\0")
    except OSError:
        return None
    return h.hexdigest()


def _write_staged_record(digest):
    """Write the staged bundle's trust digest next to (not inside) the staged tree.
    Separated so a test can force a write failure; the caller fails staging if it raises."""
    (UPDATE_DIR / "staged.sha256").write_text(digest, encoding="ascii")


def _stream_to_file(info, zip_path, on_progress):
    """One download attempt: stream info's asset into zip_path, returning
    (sha256_hex, bytes_written). The socket read timeout (_DL_TIMEOUT_S) bounds any
    single read; download_and_stage wraps this in a bounded retry."""
    done = 0
    hasher = hashlib.sha256()
    with _http_get(info.asset_url, _DL_TIMEOUT_S) as resp, open(zip_path, "wb") as out:
        total = info.asset_size or int(resp.headers.get("Content-Length") or 0)
        while True:
            chunk = resp.read(_CHUNK)
            if not chunk:
                break
            out.write(chunk)
            hasher.update(chunk)
            done += len(chunk)
            if on_progress:
                on_progress(done, total)
    return hasher.hexdigest(), done


def _safe_zip_members(zf, dest):
    """Reject a zip-slip package BEFORE any byte is written: every member must
    extract to a path contained inside `dest` (no absolute paths, drive letters, or
    `..` traversal). zipfile sanitizes most of this on modern Python, but a
    self-updater that then RUNS the extracted exe must not depend on that — validate
    explicitly and refuse the whole package on any escaping member."""
    dest_resolved = dest.resolve()
    for name in zf.namelist():
        target = (dest / name).resolve()
        try:
            target.relative_to(dest_resolved)
        except ValueError:
            log.warning("update: refusing package — member escapes the extract dir: %r", name)
            raise UpdateError("the downloaded package contains an unsafe file path "
                              "and was rejected") from None


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
    # A flaky link (corporate proxy, Wi‑Fi hiccup) gets a few bounded retries; each
    # attempt restarts the stream from scratch (fresh file + hash). The socket read
    # timeout (_DL_TIMEOUT_S) keeps any single attempt from hanging.
    actual = done = None
    last_err = None
    for attempt in range(1, _DL_RETRY_ATTEMPTS + 1):
        try:
            actual, done = _stream_to_file(info, zip_path, on_progress)
            break
        except OSError as e:
            last_err = e
            log.warning("download attempt %d/%d failed: %s: %s",
                        attempt, _DL_RETRY_ATTEMPTS, type(e).__name__, e)
            zip_path.unlink(missing_ok=True)
    if actual is None:
        log.warning("download failed after %d attempt(s): %s: %s",
                    _DL_RETRY_ATTEMPTS, type(last_err).__name__, last_err)
        raise UpdateError("the update download failed — "
                          "check the internet connection and try again") from last_err
    if info.asset_size and done != info.asset_size:
        raise UpdateError(f"the update download was incomplete "
                          f"({done // 1_000_000} of {info.asset_size // 1_000_000} MB) "
                          "— try again")

    # Verify the download against its published SHA-256 before trusting it, and
    # REFUSE to install when there is nothing to verify against — never extract and
    # swap in unverified bytes (size alone is not integrity). release.yml publishes
    # an <asset>.sha256 for every zip, so the verified path IS the normal path.
    expected = _expected_sha256(info)
    if not expected:
        zip_path.unlink(missing_ok=True)
        log.warning("update: no published checksum for %s — refusing to install "
                    "unverified bytes (download SHA-256 %s)", info.asset_name, actual)
        raise UpdateError("this update could not be verified (no published "
                          "checksum), so it was not installed — install it manually "
                          "from the releases page")
    if actual != expected:
        zip_path.unlink(missing_ok=True)
        log.warning("update: SHA-256 mismatch (expected %s, got %s)", expected, actual)
        raise UpdateError("the downloaded update didn't match its published "
                          "checksum (it may be corrupted) — please try again")
    log.info("update: SHA-256 verified (%s)", actual)

    extract_dir = UPDATE_DIR / "extract"
    log.info("extracting %s (%d bytes)", zip_path.name, done)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            _safe_zip_members(zf, extract_dir)      # zip-slip guard (raises UpdateError)
            zf.extractall(extract_dir)
    except UpdateError:
        zip_path.unlink(missing_ok=True)
        raise
    except (zipfile.BadZipFile, OSError) as e:
        log.warning("extract failed: %s: %s", type(e).__name__, e)
        raise UpdateError("the downloaded file is not a valid app package") from e
    zip_path.unlink(missing_ok=True)    # free the space before the app runs on

    root = _bundle_root(extract_dir)    # the zip wraps a "TSMIS Exporter\" folder
    staged = UPDATE_DIR / "staged"
    # Defender / the Search indexer can still hold a handle in the freshly-
    # extracted ~150 MB tree, denying the rename with WinError 5 (seen in the
    # field, both times during the ~09:20 morning scan window). The swap step
    # wraps every file op in _retry for exactly this; the stage rename had none,
    # so a transient lock aborted the whole stage and forced a re-download.
    # Retry with the same cadence rather than failing on the first denial.
    _retry(lambda: root.rename(staged))   # same volume: instant
    if extract_dir.exists() and root != extract_dir:
        # Best-effort cleanup with the same retry cadence — but a leftover
        # extract dir must never abort an otherwise-good stage.
        try:
            _retry(lambda: shutil.rmtree(extract_dir))
        except OSError as e:
            log.warning("update: could not remove extract dir %s: %s: %s",
                        extract_dir, type(e).__name__, e)
            shutil.rmtree(extract_dir, ignore_errors=True)

    if not (staged / _EXE_NAME).is_file() or not (staged / "_internal").is_dir():
        raise UpdateError("the downloaded package is missing expected app files")
    # Record a trust digest over the WHOLE staged bundle (exe + _internal/** + the
    # readmes) NEXT TO (not inside) the staged tree, so apply_update_and_restart can
    # re-verify the entire launchable/installable content in the TRUSTED original
    # process before the swap — the staged tree sits in a user-writable folder
    # between download and swap. Recording it is MANDATORY: if the digest can't be
    # computed or written, the stage FAILS and the staging area is removed, so no
    # unverifiable staged tree is ever left for apply to launch.
    digest = _bundle_digest(staged)
    if digest is None:
        shutil.rmtree(UPDATE_DIR, ignore_errors=True)
        raise UpdateError("the downloaded update could not be verified after "
                          "extraction — please try again")
    try:
        _write_staged_record(digest)
    except OSError as e:
        log.warning("update: could not record the staged trust digest: %s: %s",
                    type(e).__name__, e)
        shutil.rmtree(UPDATE_DIR, ignore_errors=True)
        raise UpdateError("the downloaded update could not be secured after "
                          "extraction — please try again") from e
    log.info("update %s staged at %s (bundle digest %s)", info.tag, staged, digest[:12])
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
_DEATH_CHECK_TOTAL_S = 2.0       # watch a freshly-launched swap process this long for an immediate death
_DEATH_CHECK_INTERVAL_S = 0.25   # poll cadence within that window


def _staged_hash(staged):
    """The bundle trust digest recorded at download time (the sibling staged.sha256
    file — see `_bundle_digest`), or None when it is absent or garbled (→ fail closed)."""
    path = Path(staged).parent / "staged.sha256"
    try:
        token = path.read_text(encoding="ascii").strip().lower()
    except OSError:
        return None
    return token if re.fullmatch(r"[0-9a-f]{64}", token) else None


def _launch_detached(cmd, cwd, flags):
    """Spawn `cmd` detached — no console, own process group, no inherited std
    streams. Separated so a test can stand in a fake process."""
    return subprocess.Popen(
        cmd, creationflags=flags, close_fds=True, cwd=str(cwd),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


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

    # Re-verify the WHOLE staged bundle (exe + _internal/** + readmes) against the
    # digest recorded at download time, in the ORIGINAL (trusted) process BEFORE the
    # staged exe is ever launched — the staged tree sat in a user-writable folder, so
    # a re-hash here catches tampering with ANY launched/installed file rather than
    # trusting the staged exe to vet itself. FAIL CLOSED: a missing or malformed trust
    # record, an unreadable tree, or any content mismatch refuses the swap (the app
    # stays on the old version; the user re-downloads).
    expected = _staged_hash(staged)
    if expected is None:
        log.warning("update: no valid staged trust record — refusing to apply")
        raise UpdateError("the staged update could not be verified (its security "
                          "record is missing) and was not applied — download it again")
    actual = _bundle_digest(staged)
    if actual != expected:
        log.warning("update: staged bundle digest changed since download "
                    "(expected %s, got %s) — refusing to launch it", expected, actual)
        raise UpdateError("the staged update changed on disk and was not "
                          "applied — download it again")
    log.info("update: staged bundle re-verified before swap (%s)", actual[:12])

    helper_log = LOG_DIR / "update_helper.log"
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        proc = _launch_detached(
            [str(new_exe), SWAP_FLAG, str(install_dir()), str(os.getpid()),
             str(helper_log)],
            staged, flags)
    except OSError as e:
        log.warning("swap process failed to start: %s: %s", type(e).__name__, e)
        raise UpdateError("the update process could not be started — "
                          "install the new version manually from the "
                          "releases page") from e
    # A blocked/broken exe dies within moments; watch for that across a short
    # WINDOW (not a single instant) while the app is still open, so a death at any
    # point in the window is caught instead of closing into a swap that never
    # happens (the silent-failure mode the PowerShell helper had). Still fail-safe:
    # only a process OBSERVED dead raises; a live one proceeds.
    polls = max(1, int(_DEATH_CHECK_TOTAL_S / _DEATH_CHECK_INTERVAL_S))
    rc = None
    for _ in range(polls):
        time.sleep(_DEATH_CHECK_INTERVAL_S)
        rc = proc.poll()
        if rc is not None:
            break
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


_HELPER_LOG_MAX_BYTES = 256 * 1024   # rotate update_helper.log past this (keep one .1 backup)


def _rotate_swap_log(log_file):
    """Keep update_helper.log bounded across many updates: once it passes the cap,
    move it aside to <log>.1 (replacing any previous backup) and start fresh.
    Best-effort — a rotation failure must never block the swap log itself."""
    try:
        if log_file.is_file() and log_file.stat().st_size >= _HELPER_LOG_MAX_BYTES:
            backup = log_file.with_name(log_file.name + ".1")
            try:
                backup.unlink()
            except OSError:
                pass
            log_file.rename(backup)
    except OSError:
        pass


def _swap_log(log_file, message):
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        _rotate_swap_log(log_file)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def _wait_pid_exit(pid, timeout_s):
    """True once `pid` has exited (or never existed); False on timeout.
    ctypes only — no psutil in the bundle.

    PID-recycle safety: apply_update_and_restart launches this swap process
    while the app (pid) is STILL RUNNING (it stays alive ~1.5 s+ after the
    launch), and OpenProcess below is the swap's very first action — so the
    handle is taken against the live ORIGINAL process. A held process handle
    keeps the kernel process object (and therefore the PID) reserved until the
    handle is closed, so the PID can't be recycled out from under the wait. If
    OpenProcess instead FAILS, the original has already exited (its PID is gone,
    or was reused by a process we can't open) — either way our app is down, so
    returning True to proceed is correct. The only residual case (the swap exe
    so slow to start that the app exits AND the PID is reused by a live process
    first) merely lets the wait time out, so the swap reports 'not applied' and
    the old version is left intact and logged — fail-safe, never a half-swap."""
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



_SWAP_JOURNAL_NAME = "swap.inprogress"


def _swap_journal_path():
    return UPDATE_DIR / _SWAP_JOURNAL_NAME


def _write_swap_journal(journal, app_dir, pieces, log_file):
    """Phase-2 intent record (E1): which pieces are about to rename-swap in
    `app_dir`. Written AFTER phase 1 (every .new staged beside its target),
    removed on ANY orderly outcome — success or the handled rename-rollback.
    Its presence at the next launch therefore means a HARD interrupt (kill /
    power loss) mid-phase-2: cleanup_leftovers then completes or rolls back
    from the .old/.new pieces instead of DELETING them (the old behavior
    destroyed the only recovery material a mixed tree had)."""
    try:
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps(
            {"version": 1, "app_dir": str(app_dir), "pieces": list(pieces)}),
            encoding="utf-8")
        _swap_log(log_file, f"swap journal written ({len(pieces)} pieces)")
    except OSError as e:
        # No journal = no recovery net; proceed anyway (pre-E1 behavior).
        _swap_log(log_file, f"swap journal NOT written ({type(e).__name__}: {e})"
                            " - proceeding without a recovery net")


def _clear_swap_journal(journal, log_file=None):
    try:
        journal.unlink(missing_ok=True)
    except OSError as e:
        if log_file is not None:
            _swap_log(log_file,
                      f"swap journal not removed ({type(e).__name__}: {e})")


def _recover_interrupted_swap(journal=None):
    """Complete-or-roll-back a phase-2 swap a hard interrupt left mixed (E1).

    Runs at the next launch, BEFORE the leftover sweep. Forward completion is
    preferred (the staged tree was digest-verified and phase 1 finished): each
    journaled piece still carrying a .new is renamed in, exactly like phase 2.
    If the tree can't be completed (a piece's .new vanished), everything is
    rolled back to the .old copies — renames only, both directions. The journal
    is cleared after ONE attempt either way; the ordinary sweep then handles
    the remnants. Returns "completed" / "rolled-back" / "failed" / None (no or
    unreadable journal)."""
    journal = journal or _swap_journal_path()
    if not journal.is_file():
        return None
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
        app_dir = Path(data["app_dir"])
        pieces = [str(n) for n in data["pieces"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("update: unreadable swap journal (%s: %s); removing it",
                    type(e).__name__, e)
        _clear_swap_journal(journal)
        return None
    # Fail CLOSED on a tampered/foreign journal (defense-in-depth, mirroring the
    # phase-1 allowlist): recovery RENAMES files, so a planted journal must not
    # point it at an arbitrary directory or a path outside the known bundle. The
    # app_dir MUST be this install, and every piece MUST be a bare _BUNDLE_ITEMS
    # name (no separators / '..').
    try:
        same_install = app_dir.resolve() == install_dir().resolve()
    except OSError:   # silent-ok: an unresolvable path fails CLOSED (rejected + logged below)
        same_install = False
    bad_pieces = [n for n in pieces
                  if n not in _BUNDLE_ITEMS or "/" in n or "\\" in n or n in ("..", ".")]
    if not same_install or bad_pieces:
        log.warning("update: REJECTING a swap journal (app_dir=%s vs %s, "
                    "bad_pieces=%s); removing it", app_dir, install_dir(), bad_pieces)
        _clear_swap_journal(journal)
        return None
    log.warning("update: an INTERRUPTED swap was found (%d pieces in %s) - "
                "recovering before the leftover sweep", len(pieces), app_dir)
    outcome = "failed"
    try:
        for name in pieces:
            dest = app_dir / name
            new = app_dir / (name + ".new")
            bak = app_dir / (name + ".old")
            if not new.exists():
                continue                     # already swapped in (or never staged)
            if dest.exists():
                if bak.exists():
                    _retry(lambda b=bak: _remove_tree(b))
                _retry(lambda d=dest, b=bak: d.rename(b))
            _retry(lambda n=new, d=dest: n.rename(d))
        still_missing = [n for n in pieces if not (app_dir / n).exists()]
        if still_missing:
            raise OSError(f"pieces missing after completion: {still_missing}")
        log.warning("update: interrupted swap COMPLETED (new version in place)")
        outcome = "completed"
    except OSError as e:
        log.warning("update: forward completion failed (%s: %s) - rolling back "
                    "to the previous version", type(e).__name__, e)
        try:
            for name in reversed(pieces):
                dest = app_dir / name
                new = app_dir / (name + ".new")
                bak = app_dir / (name + ".old")
                if not bak.exists():
                    continue                 # piece never left the old version
                if new.exists() and dest.exists():
                    continue                 # untouched piece (stale .old only)
                if dest.exists():            # dest holds a NEW piece: park it back
                    _retry(lambda d=dest, n=new: d.rename(n))
                _retry(lambda b=bak, d=dest: b.rename(d))
            missing = [n for n in pieces if not (app_dir / n).exists()]
            if missing:
                raise OSError(f"pieces missing after rollback: {missing}")
            log.warning("update: interrupted swap ROLLED BACK "
                        "(previous version restored)")
            outcome = "rolled-back"
        except OSError as e2:
            log.error("update: recovery FAILED both directions (%s: %s) - "
                      "reinstall the app from the releases page",
                      type(e2).__name__, e2)
    _clear_swap_journal(journal)
    return outcome


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

    # SEC-05 (v0.19.0): re-verify the staged bundle against the trust record ONE
    # more time HERE, after the app exited and immediately before any file is
    # installed — the tree sat in a user-writable folder for the whole pid-wait
    # since the pre-launch verification. FAIL CLOSED: a missing/garbled record
    # or any content change aborts with the old version intact.
    expected = _staged_hash(staged)
    if expected is None:
        _swap_log(log_file, "staged trust record missing/garbled - update NOT applied")
        return False
    actual = _bundle_digest(staged)
    if actual != expected:
        _swap_log(log_file, f"staged bundle changed since download (expected "
                            f"{expected[:12]}, got {actual[:12]}) - update NOT applied")
        return False
    _swap_log(log_file, f"staged bundle re-verified pre-install ({actual[:12]})")

    # ---- phase 1: copy everything in as *.new (old app untouched) ----------
    # Install ONLY the known bundle items (the same allowlist cleanup_leftovers
    # uses), never whatever else happens to sit in the staged tree -- a tampered
    # or mis-packaged extra top-level item can't ride into the install.
    try:
        present = {p.name for p in staged.iterdir()}
    except OSError:
        present = set()
    extra = sorted(present - set(_BUNDLE_ITEMS))
    if extra:
        _swap_log(log_file, f"ignoring unexpected staged item(s): {extra}")
    items = [staged / name for name in _BUNDLE_ITEMS if (staged / name).exists()]
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
    journal = _swap_journal_path()
    _write_swap_journal(journal, app_dir, [n for n, _ in news], log_file)
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
            _message_box(_rollback_dialog_text(restored, log_file))

    if relaunch:
        _relaunch(app_dir, log_file)

    # Leftover *.old/*.new pieces and the staged tree THIS process runs from
    # are removed by cleanup_leftovers() at the relaunched app's next startup
    # (this process exits immediately, releasing its own files).
    # Both orderly outcomes leave a coherent tree — the journal's job is done.
    # Only a hard interrupt (kill/power loss) skips this line, and that is
    # exactly when the next launch must find it.
    _clear_swap_journal(journal, log_file)
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


def _rollback_dialog_text(restored, log_file):
    """The swap-failure dialog text, reflecting the ACTUAL rollback outcome: a
    PARTIAL restore must not read as 'the previous version was kept' (the bug this
    closes) so the user knows to reinstall."""
    if restored:
        return ("The update could not be applied, so the previous version was "
                f"kept.\nDetails: {log_file}")
    return ("The update could not be applied, and the previous version was only "
            "partially restored. Please reinstall the app from the releases "
            f"page.\nDetails: {log_file}")


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
    only ever hold the app's own three UI files, so clearing on every FROZEN
    launch is cheap and kills the whole staleness class (manual zip-overwrite
    installs included). cleanup_leftovers only calls this for packaged builds —
    a dev launch serves scripts/ui live and never needs it."""
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


def _recover_store_promotions():
    """P2/F2: repair any interrupted Export-Everything store promotion before the GUI reads
    a store — restore `live` from its retained backup if a crash hit between the two
    renames; otherwise clean the residue. The store lives under the user-configured batch
    destination (`settings.get_batch_dest`), which may be ANY local path, so recover BOTH
    that destination AND `OUTPUT_ROOT` — deduplicated by resolved path, each isolated so
    one failure never blocks the other (P2-B03). Recovery is constrained to APP-OWNED
    promotion locations via an ownership predicate (P2-B04 / CMP-AUD-090): a store root
    under a user-chosen destination must be a known `<src>-<env>` folder carrying a CURRENT
    purpose-bound create-and-mark claim, and a journal's target must be a known export
    report subdir. The exact app-private `OUTPUT_ROOT` retains its deliberate legacy
    location/name compatibility. Best-effort + idempotent; never wedges startup."""
    try:
        import artifact_store
        import owned_dir
        from paths import OUTPUT_ROOT
    except Exception as e:                        # noqa: BLE001 — startup must not fail here
        log.warning("store-promotion recovery unavailable (%s: %s)", type(e).__name__, e)
        return
    # Ownership context: the app's Export-Everything stores live at
    # <dest>/<src>-<env>/<subdir>. A user-destination `.promote` parent must be a
    # direct child, a known src-env folder, AND currently marked as a store the
    # app created. OUTPUT_ROOT is a dedicated app output boundary and keeps the
    # pre-marker direct-child/name policy for interrupted legacy promotions.
    try:
        import common
        import reports
        owned_roots = {f"{s}-{e}" for s in common.DATA_SOURCES for e in common.ENVIRONMENTS}
        owned_targets = {getattr(spec, "subdir", None) for _l, _f, spec in reports.EXPORT_REPORTS}
    except Exception as e:                        # noqa: BLE001 — without ownership, recover nothing
        log.warning("store-promotion recovery: could not build the ownership allowlist (%s: %s); "
                    "skipping recovery", type(e).__name__, e)
        return

    try:
        private_output_root = Path(OUTPUT_ROOT).resolve()
    except OSError:
        private_output_root = Path(OUTPUT_ROOT)

    def _owned_for(recovery_root):
        # The store root must be a DIRECT child of THIS exact recovery root (P2-B04 round 4: a
        # valid `<src>-<env>` NAME nested deeper, e.g. <root>/Project/ssor-prod, is NOT owned).
        try:
            rr = Path(recovery_root).resolve()
        except OSError:
            rr = Path(recovery_root)
        app_private_root = rr == private_output_root
        claimed_identities = {}

        def _is_owned(store_root, target):
            store_root = Path(store_root)
            try:
                if store_root.parent.resolve() != rr:
                    return False
            except OSError:
                return False
            if store_root.name not in owned_roots:
                return False
            identity = owned_dir.directory_identity(store_root)
            if identity is None:
                return False
            if (not app_private_root
                    and not owned_dir.is_owned(store_root, kind="store")):
                return False
            if owned_dir.directory_identity(store_root) != identity:
                return False
            key = store_root.absolute()
            claimed = claimed_identities.get(key)
            if claimed is None:
                # recover_promotions always calls the location-only gate first;
                # a target check may only validate that already-captured lease.
                if target is not None:
                    return False
                claimed_identities[key] = identity
            elif identity != claimed:
                return False
            return target is None or target in owned_targets   # None = the location-only gate
        return _is_owned

    roots = [OUTPUT_ROOT]
    try:
        import settings
        batch_dest = settings.get_batch_dest()
        if batch_dest:
            roots.append(Path(batch_dest))
    except Exception as e:                        # noqa: BLE001
        log.warning("could not resolve the batch destination for recovery (%s: %s)",
                    type(e).__name__, e)
    seen = set()
    for root in roots:
        try:
            key = Path(root).resolve()
        except OSError:
            key = Path(root)
        if key in seen:
            continue
        seen.add(key)
        try:
            artifact_store.recover_promotions(root, _owned_for(root))
        except Exception as e:                    # noqa: BLE001 — isolate per-root failures
            log.warning("store-promotion recovery sweep failed for %s (%s: %s)",
                        root, type(e).__name__, e)


def cleanup_leftovers():
    """Remove what a finished (or abandoned) update leaves behind: the
    data\\update staging area and any *.old / *.new bundle pieces the helper
    couldn't delete while the new app was already starting — and the WebView2
    HTTP caches, so the interface on screen is always the one on disk. Also runs the P2
    store-promotion recovery sweep (artifact_store) so an interrupted Export-Everything
    swap is repaired from its backup before any store is read.
    Best-effort and cheap; called on every GUI launch, before the CLR loads."""
    # Store-promotion recovery is independent of the update mechanism and must run
    # for dev/console launches too (it repairs an interrupted Export-Everything swap
    # before any store is read), so it runs BEFORE the frozen-only gate.
    _recover_store_promotions()                  # P2/F2 — independent of the update mechanism
    if not is_frozen():
        return
    # The WebView2 cache-clear only matters for a PACKAGED build that just swapped
    # its UI files on disk (or a manual zip-overwrite install); a dev launch serves
    # scripts/ui live, so clearing it every dev launch was wasted work — frozen-only.
    _clear_webview_caches()
    # E1: an interrupted phase-2 swap is repaired FIRST — the sweep below would
    # otherwise delete the very .old/.new pieces recovery needs.
    _recover_interrupted_swap()
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

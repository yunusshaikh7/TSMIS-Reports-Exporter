"""Standalone regression checks for the WS4 updater hardening.

Pure Python, no network and no real swap of the live install -- run with the
build venv from the repo root:

    build\\.venv\\Scripts\\python.exe build\\check_updater.py

Covers:
  * version parsing / is_newer
  * _expected_sha256 (companion .sha256 + GitHub API digest, bad input -> None)
  * the staged-items ALLOWLIST in perform_swap: only known bundle items are
    installed; an unexpected extra staged file is ignored; user data is never
    touched (driven against fake trees with the pid-wait stubbed)
  * a missing staged exe aborts the swap cleanly
"""
import json
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import updater  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def test_versions():
    print("version comparison:")
    check("parse v0.10.4", updater.parse_version("v0.10.4") == (0, 10, 4))
    check("0.11.0 newer than 0.10.4",
          updater.is_newer((0, 11, 0), (0, 10, 4)))
    check("0.10.4 not newer than 0.10.4",
          not updater.is_newer((0, 10, 4), (0, 10, 4)))
    check("0.10.10 newer than 0.10.4 (numeric, not lexical)",
          updater.is_newer((0, 10, 10), (0, 10, 4)))


def test_expected_sha256():
    print("_expected_sha256:")
    Info = updater.UpdateInfo
    good = "a" * 64
    i = Info("1", "v1", "a.zip", "", 0, "", asset_digest=f"sha256:{good.upper()}")
    check("API digest parsed + lowercased", updater._expected_sha256(i) == good)
    check("bad digest -> None",
          updater._expected_sha256(Info("1", "v1", "a.zip", "", 0, "",
                                        asset_digest="sha256:nothex")) is None)
    check("no digest, no url -> None",
          updater._expected_sha256(Info("1", "v1", "a.zip", "", 0, "")) is None)


def test_safe_release_url():
    print("safe_release_url (only our github repo is ever opened):")
    repo = updater.GITHUB_REPO
    page = updater.RELEASES_PAGE
    good = f"https://github.com/{repo}/releases/tag/v0.11.1"
    check("our repo's release URL passes through",
          updater.safe_release_url(good) == good)
    check("the constant fallback is itself valid (no downgrade loop)",
          updater.safe_release_url(page) == page)
    check("empty -> releases page", updater.safe_release_url("") == page)
    check("None -> releases page", updater.safe_release_url(None) == page)
    check("a different github repo -> releases page",
          updater.safe_release_url("https://github.com/evil/repo/releases") == page)
    check("look-alike host -> releases page",
          updater.safe_release_url(f"https://github.com.evil.test/{repo}/x") == page)
    check("userinfo @-trick host -> releases page",
          updater.safe_release_url(f"https://github.com@evil.test/{repo}/x") == page)
    check("http (not https) -> releases page",
          updater.safe_release_url(f"http://github.com/{repo}/releases") == page)
    check("file: scheme -> releases page",
          updater.safe_release_url("file:///C:/Windows/System32/calc.exe") == page)
    check("javascript: scheme -> releases page",
          updater.safe_release_url("javascript:alert(1)") == page)


class _FakeReleasesResp:
    """A context-manager stand-in for _http_get's response: json.load(resp)
    reads the whole body in one call. `headers` is empty by default (no Link
    header -> a single page); a paginating test supplies its own."""
    def __init__(self, payload, link=""):
        self._b = json.dumps(payload).encode("utf-8")
        self.headers = {"Link": link} if link else {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self._b


class _StreamResp:
    """A context-manager stand-in for _http_get when DOWNLOADING bytes: read(n)
    yields the buffer in chunks, with a Content-Length header."""
    def __init__(self, data):
        self._data, self._pos = data, 0
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk


class _FakeProc:
    """A stand-in for the detached swap subprocess: poll() walks `poll_seq` and
    then repeats its last value (so [None] is 'always alive', [None, 9] is 'alive
    then exited code 9')."""
    def __init__(self, poll_seq):
        self._seq = list(poll_seq) or [None]
        self._i = 0

    def poll(self):
        v = self._seq[self._i] if self._i < len(self._seq) else self._seq[-1]
        self._i += 1
        return v


def _rel(tag, *, draft=False, prerelease=False, variants=("win64", "win64-with-browser")):
    """A minimal GitHub release object with one zip (+ .sha256) per variant."""
    assets = []
    for v in variants:
        zip_name = f"TSMIS-Exporter-{tag}-{v}.zip"
        assets.append({"name": zip_name, "browser_download_url": f"http://x/{zip_name}",
                       "size": 10, "digest": ""})
        assets.append({"name": zip_name + ".sha256",
                       "browser_download_url": f"http://x/{zip_name}.sha256"})
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease,
            "html_url": f"https://github.com/x/releases/tag/{tag}", "assets": assets}


def test_resolve_previous_release():
    print("resolve_previous_release (revert target = newest FULL release older than this build):")
    orig = updater._http_get
    try:
        # Out of list order, with a draft + a prerelease ABOVE the right answer,
        # to prove selection is by version number and ignores draft/prerelease.
        payload = [
            _rel("v0.11.0"), _rel("v0.13.0"),       # 0.13.0 == current -> excluded
            _rel("v0.12.0"),                          # <- the correct answer
            _rel("v0.12.5", draft=True),              # newer-older but a draft -> ignored
            _rel("v0.12.9", prerelease=True),         # newer-older but prerelease -> ignored
            _rel("v0.10.0"),
        ]
        updater._http_get = lambda url, timeout: _FakeReleasesResp(payload)
        info = updater.resolve_previous_release(current_version="0.13.0", variant="win64")
        check("picks newest full release strictly older (v0.12.0, not list order / draft / pre)",
              info is not None and info.tag == "v0.12.0")
        check("asset matches the requested variant",
              info is not None and info.asset_name.endswith("-win64.zip"))
        check("companion .sha256 url carried through",
              info is not None and info.asset_sha256_url.endswith("-win64.zip.sha256"))

        # The newest-older release lacks the with-browser zip -> skip to the
        # next-older one that has it (NOT the forward check's "try again later").
        payload2 = [_rel("v0.12.0", variants=("win64",)),
                    _rel("v0.11.0", variants=("win64", "win64-with-browser"))]
        updater._http_get = lambda url, timeout: _FakeReleasesResp(payload2)
        info2 = updater.resolve_previous_release(current_version="0.13.0",
                                                 variant="win64-with-browser")
        check("variant-skip: falls to the next-older release that has the variant (v0.11.0)",
              info2 is not None and info2.tag == "v0.11.0")

        # No release older than this build -> None (a clean "nothing to revert to").
        updater._http_get = lambda url, timeout: _FakeReleasesResp(
            [_rel("v0.13.0"), _rel("v0.14.0")])
        check("no older release -> None (not an error)",
              updater.resolve_previous_release(current_version="0.13.0", variant="win64") is None)
    finally:
        updater._http_get = orig


def _make_tree(base, exe_bytes, internal_bytes, extras=None):
    base.mkdir(parents=True, exist_ok=True)
    (base / updater._EXE_NAME).write_bytes(exe_bytes)
    (base / "_internal").mkdir(exist_ok=True)
    (base / "_internal" / "app.dll").write_bytes(internal_bytes)
    (base / "Start Here.txt").write_text("hi", encoding="utf-8")
    # IT-README.txt also rides the allowlist; tie its content to exe_bytes so a
    # test can prove the staged copy actually replaced the installed one.
    (base / "IT-README.txt").write_text(
        "readme-" + exe_bytes.decode("latin-1"), encoding="utf-8")
    for name, data in (extras or {}).items():
        (base / name).write_bytes(data)


def test_staged_allowlist(monkeypatch_wait):
    print("swap staged-items allowlist (fake trees):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_upd_"))
    app = tmp / "app"
    staged = tmp / "staged"
    log = tmp / "swap.log"
    _make_tree(app, b"OLD-EXE", b"OLD-DLL")
    (app / "data").mkdir()                      # user data — must survive untouched
    (app / "data" / "config.json").write_text("{}", encoding="utf-8")
    # Staged: new bundle + an UNEXPECTED extra top-level file that must NOT install.
    _make_tree(staged, b"NEW-EXE", b"NEW-DLL", extras={"evil.dll": b"PWN"})

    monkeypatch_wait(lambda pid, t: True)       # pretend the old app already exited
    ok = updater.perform_swap(staged, app, pid=1, log_file=log,
                              relaunch=False, show_dialog=False)
    check("swap reported success", ok)
    check("exe replaced with new bytes",
          (app / updater._EXE_NAME).read_bytes() == b"NEW-EXE")
    check("_internal replaced with new bytes",
          (app / "_internal" / "app.dll").read_bytes() == b"NEW-DLL")
    check("IT-README.txt refreshed with new content",
          (app / "IT-README.txt").read_text(encoding="utf-8") == "readme-NEW-EXE")
    check("unexpected staged item NOT installed", not (app / "evil.dll").exists())
    check("user data untouched",
          (app / "data" / "config.json").read_text(encoding="utf-8") == "{}")


def test_sha256_verify(monkeypatch_wait):
    print("download_and_stage SHA-256 verification:")
    import hashlib
    DATA = b"these bytes are not a real zip, but we control their hash"
    good = hashlib.sha256(DATA).hexdigest()

    class _FakeResp:
        def __init__(self, data):
            self._data, self._pos = data, 0
            self.headers = {"Content-Length": str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            chunk = self._data[self._pos:self._pos + n]
            self._pos += len(chunk)
            return chunk

    orig_http = updater._http_get
    orig_support = updater.update_support
    orig_update_dir = updater.UPDATE_DIR
    updater._http_get = lambda url, timeout: _FakeResp(DATA)
    updater.update_support = lambda: ("ok", None)
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_sha_"))
    updater.UPDATE_DIR = tmp / "update"
    Info = updater.UpdateInfo
    try:
        # Wrong published hash -> refuse, delete the zip, stage nothing.
        bad_info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "",
                        asset_digest="sha256:" + ("0" * 64))
        err = None
        try:
            updater.download_and_stage(bad_info)
        except updater.UpdateError as e:
            err = str(e)
        check("mismatch raises UpdateError", err is not None)
        check("mismatch message mentions the checksum",
              err is not None and "checksum" in err.lower())
        check("mismatched download was deleted",
              not (updater.UPDATE_DIR / "pkg.zip").exists())
        check("nothing was staged on mismatch",
              not (updater.UPDATE_DIR / "staged").exists())

        # Correct hash -> PASSES verification (then fails later at extract,
        # since DATA isn't a real zip -- a DIFFERENT error, proving the hash
        # check was cleared rather than the cause).
        good_info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "",
                         asset_digest="sha256:" + good)
        err2 = None
        try:
            updater.download_and_stage(good_info)
        except updater.UpdateError as e:
            err2 = str(e)
        check("matching hash gets PAST verification (fails later at extract)",
              err2 is not None and "checksum" not in err2.lower())
    finally:
        updater._http_get = orig_http
        updater.update_support = orig_support
        updater.UPDATE_DIR = orig_update_dir


def test_retry_recovers_transient_oserror():
    print("_retry recovers a transient OSError (the Defender/indexer lock):")
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError(5, "Access is denied")
        return "staged"

    check("returns after transient failures", updater._retry(flaky) == "staged")
    check("retried until it succeeded (3 calls)", calls["n"] == 3)


def _build_bundle_zip():
    """A valid update zip: one top-level 'TSMIS Exporter/' folder holding the exe
    + _internal, exactly what _bundle_root expects."""
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"TSMIS Exporter/{updater._EXE_NAME}", b"NEW-EXE")
        zf.writestr("TSMIS Exporter/_internal/app.dll", b"NEW-DLL")
    return buf.getvalue()


def test_stage_rename_retries():
    """The field bug: download_and_stage's extract->staged rename had no retry, so
    a transient WinError 5 (Defender/indexer holding the freshly-extracted tree)
    aborted the whole stage. Prove the rename now goes through _retry and recovers
    a one-shot denial, completing the stage."""
    print("download_and_stage rename retries past a transient WinError 5:")
    zip_bytes = _build_bundle_zip()

    class _FakeResp:
        def __init__(self, data):
            self._data, self._pos = data, 0
            self.headers = {"Content-Length": str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            chunk = self._data[self._pos:self._pos + n]
            self._pos += len(chunk)
            return chunk

    orig_http = updater._http_get
    orig_support = updater.update_support
    orig_update_dir = updater.UPDATE_DIR
    orig_retry = updater._retry
    updater._http_get = lambda url, timeout: _FakeResp(zip_bytes)
    updater.update_support = lambda: ("ok", None)
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_stage_"))
    updater.UPDATE_DIR = tmp / "update"

    state = {"first": True, "rename_wrapped": False, "rename_recovered": False}

    def spy_retry(fn):
        # The FIRST _retry call in download_and_stage is the extract->staged
        # rename; inject one transient denial into it, then let the real retry
        # recover. Later _retry calls (the cleanup rmtree) pass straight through.
        if state["first"]:
            state["first"] = False
            state["rename_wrapped"] = True
            calls = {"n": 0}

            def flaky():
                calls["n"] += 1
                if calls["n"] == 1:
                    raise OSError(5, "Access is denied")
                state["rename_recovered"] = True
                return fn()

            return orig_retry(flaky)
        return orig_retry(fn)

    updater._retry = spy_retry
    Info = updater.UpdateInfo
    try:
        # Checksum is now mandatory (fail-closed, §J), so publish the matching digest.
        good = __import__("hashlib").sha256(zip_bytes).hexdigest()
        info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "",
                    asset_digest="sha256:" + good)
        staged = updater.download_and_stage(info)
        check("staging rename went through _retry", state["rename_wrapped"])
        check("transient WinError 5 was recovered (not aborted)",
              state["rename_recovered"])
        check("staged tree completed with the exe", (staged / updater._EXE_NAME).is_file())
        check("staged tree has _internal", (staged / "_internal").is_dir())
    finally:
        updater._http_get = orig_http
        updater.update_support = orig_support
        updater.UPDATE_DIR = orig_update_dir
        updater._retry = orig_retry


def test_missing_exe_aborts(monkeypatch_wait):
    print("swap aborts on an incomplete staged tree:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_upd2_"))
    app = tmp / "app"
    staged = tmp / "staged"
    log = tmp / "swap.log"
    _make_tree(app, b"OLD-EXE", b"OLD-DLL")
    staged.mkdir(parents=True)
    (staged / "_internal").mkdir()              # staged tree with NO exe
    monkeypatch_wait(lambda pid, t: True)
    ok = updater.perform_swap(staged, app, pid=1, log_file=log,
                              relaunch=False, show_dialog=False)
    check("swap refused (missing exe)", ok is False)
    check("old exe still intact",
          (app / updater._EXE_NAME).read_bytes() == b"OLD-EXE")


def _dl_env(http_get):
    """Set update_support='ok' + a fresh temp UPDATE_DIR and a fake _http_get for a
    download test; returns (restore_fn, update_dir)."""
    orig_http = updater._http_get
    orig_support = updater.update_support
    orig_update_dir = updater.UPDATE_DIR
    updater._http_get = http_get
    updater.update_support = lambda: ("ok", None)
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_dl_"))
    updater.UPDATE_DIR = tmp / "update"

    def restore():
        updater._http_get = orig_http
        updater.update_support = orig_support
        updater.UPDATE_DIR = orig_update_dir
    return restore, updater.UPDATE_DIR


def test_checksum_required():
    print("download_and_stage refuses an UNVERIFIABLE download (fail-closed, §J):")
    DATA = b"not a real zip, and no checksum is published for it"
    restore, update_dir = _dl_env(lambda url, timeout: _StreamResp(DATA))
    Info = updater.UpdateInfo
    try:
        # No companion .sha256 and no API digest -> nothing to verify against.
        info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "")
        err = None
        try:
            updater.download_and_stage(info)
        except updater.UpdateError as e:
            err = str(e)
        check("no published checksum -> UpdateError (never installs unverified bytes)",
              err is not None)
        check("message says it could not be verified",
              err is not None and ("verif" in err.lower() or "checksum" in err.lower()))
        check("the unverified download was deleted",
              not (update_dir / "pkg.zip").exists())
        check("nothing was staged", not (update_dir / "staged").exists())
    finally:
        restore()


def test_zip_slip_rejected():
    print("download_and_stage rejects a zip-slip package before extracting (§J):")
    import io
    import zipfile as _zf
    buf = io.BytesIO()
    with _zf.ZipFile(buf, "w") as zf:
        zf.writestr(f"TSMIS Exporter/{updater._EXE_NAME}", b"NEW-EXE")
        zf.writestr("../evil.txt", b"PWN")          # escapes the extract dir
    zip_bytes = buf.getvalue()
    good = __import__("hashlib").sha256(zip_bytes).hexdigest()
    restore, update_dir = _dl_env(lambda url, timeout: _StreamResp(zip_bytes))
    Info = updater.UpdateInfo
    try:
        info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "",
                    asset_digest="sha256:" + good)
        err = None
        try:
            updater.download_and_stage(info)
        except updater.UpdateError as e:
            err = str(e)
        check("zip-slip member -> UpdateError", err is not None)
        check("message flags an unsafe path",
              err is not None and "unsafe" in err.lower())
        check("nothing escaped above the update dir",
              not (update_dir.parent / "evil.txt").exists())
        check("nothing was staged", not (update_dir / "staged").exists())
    finally:
        restore()


def test_download_retries_transient():
    print("download_and_stage retries a transient network failure (bounded, §J):")
    DATA = b"these bytes are not a real zip but their hash is known"
    good = __import__("hashlib").sha256(DATA).hexdigest()
    state = {"n": 0}

    def flaky_http(url, timeout):
        state["n"] += 1
        if state["n"] < 3:                          # first two attempts blow up
            raise OSError("connection reset by peer")
        return _StreamResp(DATA)

    restore, update_dir = _dl_env(flaky_http)
    Info = updater.UpdateInfo
    try:
        # Digest matches DATA -> download+verify clear; extract then fails because
        # DATA isn't a real zip (a DIFFERENT error), proving we got PAST the network.
        info = Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "",
                    asset_digest="sha256:" + good)
        err = None
        try:
            updater.download_and_stage(info)
        except updater.UpdateError as e:
            err = str(e)
        check("retried past the transient failures (reached extract)",
              err is not None and "valid app package" in err.lower())
        check("it took 3 download attempts (2 transient + 1 success)", state["n"] == 3)
    finally:
        restore()


def test_resolve_previous_paginates():
    print("resolve_previous_release paginates past the 100-release cap (§J):")
    # Page 1 = 100 releases all NEWER than the current build (none qualify) + a
    # Link: rel="next". Page 2 carries the only older release. The pre-fix single
    # fetch would never see page 2 and return None.
    page1 = [_rel(f"v0.20.{i}") for i in range(100)]
    page2 = [_rel("v0.12.0")]
    nxt = '<https://api.github.com/repos/x/releases?per_page=100&page=2>; rel="next"'

    def paged_http(url, timeout):
        if "page=2" in url:
            return _FakeReleasesResp(page2)         # last page: no Link
        return _FakeReleasesResp(page1, link=nxt)

    orig = updater._http_get
    updater._http_get = paged_http
    try:
        info = updater.resolve_previous_release(current_version="0.13.0", variant="win64")
        check("found the revert target only present on page 2 (paginated past 100)",
              info is not None and info.tag == "v0.12.0")
    finally:
        updater._http_get = orig


def test_webview_clear_frozen_only():
    print("cleanup_leftovers clears the WebView2 cache for FROZEN builds only (§J):")
    calls = {"cache": 0, "recover": 0}
    orig_cache = updater._clear_webview_caches
    orig_recover = updater._recover_store_promotions
    orig_frozen = updater.is_frozen
    orig_install = updater.install_dir
    orig_update_dir = updater.UPDATE_DIR
    updater._clear_webview_caches = lambda: calls.__setitem__("cache", calls["cache"] + 1)
    updater._recover_store_promotions = lambda: calls.__setitem__("recover", calls["recover"] + 1)
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_clean_"))
    updater.install_dir = lambda: tmp                # frozen cleanup operates on an empty temp
    updater.UPDATE_DIR = tmp / "nonexistent-update"
    try:
        updater.is_frozen = lambda: False
        updater.cleanup_leftovers()
        check("dev launch: store-promotion recovery STILL runs", calls["recover"] == 1)
        check("dev launch: WebView2 cache is NOT cleared (no per-launch churn)",
              calls["cache"] == 0)

        calls["cache"] = calls["recover"] = 0
        updater.is_frozen = lambda: True
        updater.cleanup_leftovers()
        check("frozen launch: WebView2 cache IS cleared", calls["cache"] == 1)
        check("frozen launch: store-promotion recovery runs", calls["recover"] == 1)
    finally:
        updater._clear_webview_caches = orig_cache
        updater._recover_store_promotions = orig_recover
        updater.is_frozen = orig_frozen
        updater.install_dir = orig_install
        updater.UPDATE_DIR = orig_update_dir


def test_swap_log_rotates():
    print("update_helper.log is rotated so the swap log can't grow unbounded (§J):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_log_"))
    log = tmp / "update_helper.log"
    log.write_bytes(b"x" * (updater._HELPER_LOG_MAX_BYTES + 10))   # already past the cap
    updater._swap_log(log, "line after rotation")
    check("an oversized log was rotated aside to .1",
          (tmp / "update_helper.log.1").is_file())
    fresh = log.read_text(encoding="utf-8")
    check("the fresh log holds only the new line (bounded)",
          log.stat().st_size < updater._HELPER_LOG_MAX_BYTES and "line after rotation" in fresh)
    # A small log is left alone (no rotation churn) and keeps accumulating.
    small = tmp / "small.log"
    updater._swap_log(small, "one")
    updater._swap_log(small, "two")
    check("a small log is not rotated", not (tmp / "small.log.1").exists())
    check("a small log accumulates lines",
          len(small.read_text(encoding="utf-8").splitlines()) == 2)


def _stage_with_record(update_dir, *, exe=b"STAGED-EXE", dll=b"INTERNAL-DLL"):
    """Build a staged onefolder bundle (exe + _internal/app.dll + the two readmes)
    under update_dir/staged and write the matching whole-bundle trust digest."""
    staged = update_dir / "staged"
    (staged / "_internal").mkdir(parents=True)
    (staged / updater._EXE_NAME).write_bytes(exe)
    (staged / "_internal" / "app.dll").write_bytes(dll)
    (staged / "Start Here.txt").write_text("hi", encoding="utf-8")
    (staged / "IT-README.txt").write_text("readme", encoding="utf-8")
    (update_dir / "staged.sha256").write_text(
        updater._bundle_digest(staged), encoding="ascii")
    return staged


def _apply_env(tmp):
    """Patch update_support/install_dir/LOG_DIR for an apply test; returns a restore fn."""
    orig = (updater.update_support, updater.install_dir, updater.LOG_DIR,
            updater._launch_detached)
    updater.update_support = lambda: ("ok", None)
    app = tmp / "app"
    app.mkdir(exist_ok=True)
    updater.install_dir = lambda: app
    updater.LOG_DIR = tmp

    def restore():
        (updater.update_support, updater.install_dir, updater.LOG_DIR,
         updater._launch_detached) = orig
    return restore


def test_staged_bundle_reverify():
    print("apply re-verifies the WHOLE staged bundle + fails closed (§J, P10-B01):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_reverify_"))
    update_dir = tmp / "update"
    staged = _stage_with_record(update_dir)
    restore = _apply_env(tmp)
    launches = {"n": 0}

    def fake_launch(cmd, cwd, flags):
        launches["n"] += 1
        return _FakeProc([None])                  # stays alive
    updater._launch_detached = fake_launch

    def apply_err():
        before = launches["n"]
        try:
            updater.apply_update_and_restart(staged)
            return None, launches["n"] > before
        except updater.UpdateError as e:
            return str(e), launches["n"] > before

    try:
        # 1. matching bundle -> passes the gate (swap launched)
        res = updater.apply_update_and_restart(staged)
        check("matching staged bundle passes the gate (swap launched)",
              isinstance(res, str) and res.endswith(updater._EXE_NAME))

        # 2. tampered _internal (code-bearing) -> refused, NO launch  [the P10-B01 gap]
        (staged / "_internal" / "app.dll").write_bytes(b"PWNED-INTERNAL")
        e, launched = apply_err()
        check("tampered _internal/app.dll is refused (not exe-only)",
              e is not None and "changed" in e.lower() and not launched)
        (staged / "_internal" / "app.dll").write_bytes(b"INTERNAL-DLL")

        # 3. tampered exe -> refused, NO launch
        (staged / updater._EXE_NAME).write_bytes(b"TAMPERED-EXE")
        e, launched = apply_err()
        check("tampered staged exe is refused", e is not None and not launched)
        (staged / updater._EXE_NAME).write_bytes(b"STAGED-EXE")

        # 4. an ADDED _internal file -> refused (the digest covers the whole tree)
        (staged / "_internal" / "extra.dll").write_bytes(b"SMUGGLED")
        e, launched = apply_err()
        check("an added _internal file is refused", e is not None and not launched)
        (staged / "_internal" / "extra.dll").unlink()

        # 5. MISSING trust record -> fail closed, NO launch (Codex's missing_sidecar_allowed)
        (update_dir / "staged.sha256").unlink()
        e, launched = apply_err()
        check("a MISSING trust record fails closed (no launch)",
              e is not None and "security record" in e.lower() and not launched)

        # 6. MALFORMED trust record -> fail closed, NO launch
        (update_dir / "staged.sha256").write_text("not-a-valid-hash", encoding="ascii")
        e, launched = apply_err()
        check("a MALFORMED trust record fails closed (no launch)", e is not None and not launched)

        # 7. a restored valid record passes again (proves 5/6 were the cause)
        (update_dir / "staged.sha256").write_text(
            updater._bundle_digest(staged), encoding="ascii")
        res2 = updater.apply_update_and_restart(staged)
        check("a restored valid record passes again", isinstance(res2, str))
    finally:
        restore()


def test_staged_record_mandatory():
    print("download_and_stage records the trust digest or FAILS staging (§J, P10-B01):")
    import hashlib as _hl
    zip_bytes = _build_bundle_zip()               # valid bundle zip (exe + _internal/app.dll)
    good = _hl.sha256(zip_bytes).hexdigest()
    Info = updater.UpdateInfo

    def _dig_info():
        return Info("1", "v1", "pkg.zip", "http://x/pkg.zip", 0, "", asset_digest="sha256:" + good)

    def _err(fn):
        try:
            fn()
            return None
        except updater.UpdateError as e:
            return str(e)

    # (a) a record WRITE FAILURE must fail staging AND leave no usable staged tree
    restore, update_dir = _dl_env(lambda url, timeout: _StreamResp(zip_bytes))
    orig_write = updater._write_staged_record

    def boom(_digest):
        raise OSError(13, "Permission denied")
    updater._write_staged_record = boom
    try:
        e = _err(lambda: updater.download_and_stage(_dig_info()))
        check("a trust-record WRITE FAILURE fails staging", e is not None)
        check("no usable staged tree is left (UPDATE_DIR removed)", not update_dir.exists())
    finally:
        updater._write_staged_record = orig_write
        restore()

    # (b) a digest that can't be computed (None) must also fail staging
    restore, update_dir = _dl_env(lambda url, timeout: _StreamResp(zip_bytes))
    orig_digest = updater._bundle_digest
    updater._bundle_digest = lambda staged: None
    try:
        e = _err(lambda: updater.download_and_stage(_dig_info()))
        check("an UNCOMPUTABLE digest fails staging", e is not None)
        check("no usable staged tree is left", not update_dir.exists())
    finally:
        updater._bundle_digest = orig_digest
        restore()

    # (c) the happy path records a 64-hex digest that COVERS _internal
    restore, update_dir = _dl_env(lambda url, timeout: _StreamResp(zip_bytes))
    try:
        staged = updater.download_and_stage(_dig_info())
        rec = (update_dir / "staged.sha256").read_text(encoding="ascii").strip()
        check("a valid stage records a 64-hex bundle digest",
              len(rec) == 64 and all(c in "0123456789abcdef" for c in rec))
        d_before = updater._bundle_digest(staged)
        (staged / "_internal" / "app.dll").write_bytes(b"DIFFERENT-INTERNAL")
        check("the recorded digest COVERS _internal (changes when _internal changes)",
              updater._bundle_digest(staged) != d_before)
    finally:
        restore()


def test_death_check_window():
    print("apply_update_and_restart watches a death window (not one instant, §J):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_death_"))
    update_dir = tmp / "update"
    staged = update_dir / "staged"
    staged.mkdir(parents=True)
    (staged / updater._EXE_NAME).write_bytes(b"STAGED-EXE")
    (staged / "_internal").mkdir()
    (staged / "_internal" / "app.dll").write_bytes(b"DLL")
    (update_dir / "staged.sha256").write_text(
        updater._bundle_digest(staged), encoding="ascii")

    orig_support = updater.update_support
    orig_install = updater.install_dir
    orig_logdir = updater.LOG_DIR
    orig_launch = updater._launch_detached
    orig_total = updater._DEATH_CHECK_TOTAL_S
    orig_interval = updater._DEATH_CHECK_INTERVAL_S
    updater.update_support = lambda: ("ok", None)
    app = tmp / "app"
    app.mkdir()
    updater.install_dir = lambda: app
    updater.LOG_DIR = tmp
    updater._DEATH_CHECK_TOTAL_S = 0.02              # keep the test fast
    updater._DEATH_CHECK_INTERVAL_S = 0.005
    try:
        # Alive on the first poll, then exits: a single fixed-instant check could
        # miss this; the windowed poll catches it.
        updater._launch_detached = lambda cmd, cwd, flags: _FakeProc([None, 9])
        err = None
        try:
            updater.apply_update_and_restart(staged)
        except updater.UpdateError as e:
            err = str(e)
        check("a swap process that dies inside the window is caught",
              err is not None and "exited before" in err.lower())

        # A process that stays alive across the window proceeds normally.
        updater._launch_detached = lambda cmd, cwd, flags: _FakeProc([None])
        res = updater.apply_update_and_restart(staged)
        check("a live swap process proceeds (returns the staged exe path)",
              isinstance(res, str) and res.endswith(updater._EXE_NAME))
    finally:
        updater.update_support = orig_support
        updater.install_dir = orig_install
        updater.LOG_DIR = orig_logdir
        updater._launch_detached = orig_launch
        updater._DEATH_CHECK_TOTAL_S = orig_total
        updater._DEATH_CHECK_INTERVAL_S = orig_interval


def test_rollback_message_reflects_outcome(monkeypatch_wait):
    print("a rollback dialog reflects the ACTUAL restore outcome (§J):")
    # The wording helper distinguishes full vs partial restore (the bug was an
    # unconditional 'previous version was kept' even on a partial restore).
    full = updater._rollback_dialog_text(True, "L")
    part = updater._rollback_dialog_text(False, "L")
    check("full restore -> 'was kept'", "was kept" in full)
    check("partial restore -> 'partially restored' + reinstall guidance",
          "partially restored" in part.lower() and "reinstall" in part.lower())

    # Wiring: a phase-2 failure with a CLEAN rollback surfaces the full-restore
    # dialog (restored=True), proving perform_swap routes the real outcome through
    # the helper rather than a fixed string.
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_rb_"))
    app, staged, log = tmp / "app", tmp / "staged", tmp / "swap.log"
    _make_tree(app, b"OLD-EXE", b"OLD-DLL")
    _make_tree(staged, b"NEW-EXE", b"NEW-DLL")
    monkeypatch_wait(lambda pid, t: True)
    msgs = []
    orig_box = updater._message_box
    orig_log = updater._swap_log
    orig_retry = updater._retry
    state = {"installed_seen": 0, "raised": False}

    def spy_log(log_file, message):
        if message.startswith("installed:"):
            state["installed_seen"] += 1
        return orig_log(log_file, message)

    def boom_retry(fn):
        # After the first item installs, fail the next swap op ONCE -> phase 2
        # aborts with >=1 item already moved, so the rollback has real work to undo
        # (and then completes cleanly -> restored=True).
        if state["installed_seen"] >= 1 and not state["raised"]:
            state["raised"] = True
            raise OSError(5, "Access is denied")
        return orig_retry(fn)

    updater._message_box = lambda text: msgs.append(text)
    updater._swap_log = spy_log
    updater._retry = boom_retry
    try:
        ok = updater.perform_swap(staged, app, pid=1, log_file=log,
                                  relaunch=False, show_dialog=True)
        check("the swap reported failure", ok is False)
        check("exactly one rollback dialog was shown", len(msgs) == 1)
        check("a clean rollback shows the full-restore wording (wired to outcome)",
              bool(msgs) and "was kept" in msgs[0] and "partially restored" not in msgs[0].lower())
    finally:
        updater._message_box = orig_box
        updater._swap_log = orig_log
        updater._retry = orig_retry


def main():
    orig_wait = updater._wait_pid_exit

    def monkeypatch_wait(fn):
        updater._wait_pid_exit = fn

    try:
        test_versions()
        test_expected_sha256()
        test_safe_release_url()
        test_resolve_previous_release()
        test_resolve_previous_paginates()
        test_sha256_verify(monkeypatch_wait)
        test_checksum_required()
        test_zip_slip_rejected()
        test_download_retries_transient()
        test_retry_recovers_transient_oserror()
        test_stage_rename_retries()
        test_staged_allowlist(monkeypatch_wait)
        test_missing_exe_aborts(monkeypatch_wait)
        test_webview_clear_frozen_only()
        test_swap_log_rotates()
        test_staged_bundle_reverify()
        test_staged_record_mandatory()
        test_death_check_window()
        test_rollback_message_reflects_outcome(monkeypatch_wait)
    finally:
        updater._wait_pid_exit = orig_wait

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL UPDATER CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

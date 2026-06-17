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
    reads the whole body in one call."""
    def __init__(self, payload):
        self._b = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self._b


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


def main():
    orig_wait = updater._wait_pid_exit

    def monkeypatch_wait(fn):
        updater._wait_pid_exit = fn

    try:
        test_versions()
        test_expected_sha256()
        test_safe_release_url()
        test_resolve_previous_release()
        test_sha256_verify(monkeypatch_wait)
        test_staged_allowlist(monkeypatch_wait)
        test_missing_exe_aborts(monkeypatch_wait)
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

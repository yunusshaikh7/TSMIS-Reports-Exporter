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

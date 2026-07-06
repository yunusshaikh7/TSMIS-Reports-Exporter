"""P6 (R1-N02) -- persistence hardening: settings writer dedup + atomicity, atomic
auth-at-rest write + owner ACL, and the support-bundle settings allowlist.

  * SETTINGS -- the four legacy writers (`update` / `set_site_url` / `set_batch_dest`
    / `set_matrix_baseline`) now route through the single `_atomic_write`; unknown
    keys round-trip; a failed `os.replace` raises and leaves the prior config intact
    with no `.tmp` sibling (F9-style: never truncate a good config).
  * AUTH -- `save_auth_state` writes atomically (failed `os.replace` -> prior session
    kept, no temp) and best-effort tightens the file ACL to the owner via `icacls`
    (Windows); the content stays portable plaintext JSON; an ACL failure never breaks
    the save (NOT DPAPI -- portability preserved).
  * SUPPORT BUNDLE -- `support_bundle_settings()` is an explicit allowlist (subset of
    DEFAULTS), so a future sensitive setting is NOT auto-shared; the bundle manifest
    uses it, not `all_settings()`.

Offline / no product side effects: CONFIG_FILE + AUTH are redirected to a temp dir,
`subprocess.run` (icacls) is stubbed. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_persistence.py
"""
import contextlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import settings                            # noqa: E402
import auth_nav                            # noqa: E402  (P8b: the auth-file lifecycle moved common -> auth_nav)

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def _boom(*a, **k):
    raise OSError(13, "destination locked")


_VALID_URL = "https://tsmis.dot.ca.gov/?env=prod&src=ssor"


class _Completed:
    """Minimal subprocess.CompletedProcess stand-in for the icacls stub (the real
    _restrict_to_owner reads .returncode and, on failure, .stdout)."""
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def test_settings_dedup_and_atomicity():
    print("settings: the 4 legacy writers route through _atomic_write; unknown-key round-trip; atomic:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_p6_"))
    with _patch(settings, "CONFIG_FILE", tmp / "config.json"):
        settings._cache = settings._cache_mtime = None
        # all four legacy writers route through the single _atomic_write
        calls = []
        orig = settings._atomic_write

        def _rec(data):
            calls.append(dict(data))
            orig(data)
        with _patch(settings, "_atomic_write", _rec):
            settings.update({"fast_workers": 7})
            settings.set_site_url("ssor", "prod", _VALID_URL)
            settings.set_batch_dest("C:/Out")
            settings.set_matrix_baseline("ars-test")
        check("update + set_site_url + set_batch_dest + set_matrix_baseline all call _atomic_write",
              len(calls) == 4)
        # unknown-key round-trip: a key the app doesn't know survives every writer
        settings.CONFIG_FILE.write_text(json.dumps({"unknown_future": "KEEP"}), encoding="utf-8")
        settings._cache = settings._cache_mtime = None
        settings.update({"debug_logging": True})
        settings.set_site_url("ssor", "prod", _VALID_URL)
        settings.set_batch_dest("C:/Out2")
        settings.set_matrix_baseline("ssor-prod")
        data = json.loads(settings.CONFIG_FILE.read_text(encoding="utf-8"))
        check("unknown keys survive all four writers (round-trip preserved)",
              data.get("unknown_future") == "KEEP")
        check("...and the writers' own values persisted",
              data.get("debug_logging") is True and data.get("batch_dest") == "C:/Out2"
              and data.get("matrix_baseline") == "ssor-prod" and "site_urls" in data)
        # atomic: a failed os.replace raises, leaves the prior config intact, no .tmp sibling
        before = settings.CONFIG_FILE.read_bytes()
        settings._cache = settings._cache_mtime = None
        raised = False
        with _patch(settings.os, "replace", _boom):
            try:
                settings.set_batch_dest("C:/ShouldNotLand")
            except OSError:
                raised = True
        tmps = [p.name for p in settings.CONFIG_FILE.parent.iterdir() if p.suffix == ".tmp"]
        check("a failed os.replace raises, prior config intact, no .tmp left",
              raised and settings.CONFIG_FILE.read_bytes() == before and tmps == [])
    settings._cache = settings._cache_mtime = None
    shutil.rmtree(tmp, ignore_errors=True)


def test_auth_atomic_and_acl():
    print("auth: atomic write (no-truncate) + owner ACL (icacls, best-effort, not DPAPI):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_p6auth_"))
    state = {"cookies": [{"name": "session", "value": "x"}], "origins": [{"origin": "https://a"}]}
    with _patch(auth_nav, "AUTH", tmp / "tsmis_auth.json"):
        # normal save: content round-trips (portable plaintext JSON) + ACL attempted
        recorded = []

        def _rec_run(cmd, *a, **k):
            recorded.append(list(cmd))
            return _Completed()
        with _patch(auth_nav.subprocess, "run", _rec_run):
            auth_nav.save_auth_state(state)
        check("auth content written + round-trips as the same JSON (portable)",
              json.loads(auth_nav.AUTH.read_text(encoding="utf-8")) == state)
        if os.name == "nt":
            cmd = recorded[0] if recorded else []
            tmp_arg = cmd[1] if len(cmd) > 1 else ""
            # the ACL is applied to the TEMP (a .tmp sibling) BEFORE the rename, never
            # to the live AUTH path — so the cookies are never briefly broad at AUTH
            ok = bool(recorded) and cmd[0] == "icacls" \
                and "/inheritance:r" in cmd and "/grant:r" in cmd \
                and str(auth_nav.AUTH.parent) in tmp_arg and tmp_arg.endswith(".tmp")
            check("ACL: icacls (/inheritance:r + /grant:r) hits the TEMP before the rename", ok)
        else:
            check("ACL: no-op off Windows (icacls not invoked)", recorded == [])
        # ACL is best-effort: an icacls EXCEPTION must NOT break the save
        with _patch(auth_nav.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("no icacls"))):
            auth_nav.save_auth_state(state)
        check("auth save survives an icacls exception (best-effort ACL)", auth_nav.AUTH.is_file())
        # P6-R01: a NON-ZERO icacls return (a real ACL failure, not an exception) is LOGGED
        # as a best-effort failure (rc + reason) and the save still succeeds
        logged = []
        with _patch(auth_nav.subprocess, "run",
                    lambda *a, **k: _Completed(5, "icacls: Access is denied.\n")), \
             _patch(auth_nav.log, "info", lambda m, *a, **k: logged.append(m % a if a else m)):
            auth_nav.save_auth_state(state)
        check("a non-zero icacls return is logged (rc) as best-effort failure, save still ok (P6-R01)",
              any("non-zero icacls result" in m and "rc=5" in m for m in logged) and auth_nav.AUTH.is_file())
        # _restrict_to_owner no-ops with no USERNAME (no crash, no icacls)
        rec2 = []
        with _patch(auth_nav.subprocess, "run", lambda cmd, *a, **k: rec2.append(cmd)), \
             _patch(auth_nav.os, "environ", {}):
            auth_nav._restrict_to_owner(auth_nav.AUTH)
        check("ACL: no USERNAME -> skipped (no icacls call)", rec2 == [])
        # ...and a structurally invalid USERNAME (would mis-parse the icacls account arg)
        rec3 = []
        with _patch(auth_nav.subprocess, "run", lambda cmd, *a, **k: rec3.append(cmd)), \
             _patch(auth_nav.os, "environ", {"USERNAME": "ev:il"}):
            auth_nav._restrict_to_owner(auth_nav.AUTH)
        check("ACL: an invalid USERNAME (contains ':') -> skipped (no malformed grant)", rec3 == [])
        # atomic: a failed os.replace raises, prior session kept, no temp left
        auth_nav.AUTH.write_text(json.dumps({"prior": True}), encoding="utf-8")
        before = auth_nav.AUTH.read_bytes()
        raised = False
        with _patch(auth_nav.os, "replace", _boom), _patch(auth_nav.subprocess, "run", _rec_run):
            try:
                auth_nav.save_auth_state(state)
            except OSError:
                raised = True
        tmps = [p.name for p in auth_nav.AUTH.parent.iterdir() if p.name.endswith(".tmp")]
        check("a failed os.replace raises, prior session intact, no temp left",
              raised and auth_nav.AUTH.read_bytes() == before and tmps == [])
    shutil.rmtree(tmp, ignore_errors=True)


def test_support_bundle_allowlist():
    print("support bundle: settings allowlist (subset of DEFAULTS; future keys excluded):")
    check("support_bundle_settings() == the explicit allowlist",
          set(settings.support_bundle_settings()) == set(settings._SUPPORT_BUNDLE_KEYS))
    check("allowlist is a subset of DEFAULTS (every key is a real setting)",
          set(settings._SUPPORT_BUNDLE_KEYS) <= set(settings.DEFAULTS))
    check("allowlist excludes the non-DEFAULTS keys (site_urls / batch_dest / matrix_*)",
          "site_urls" not in settings.support_bundle_settings()
          and "batch_dest" not in settings.support_bundle_settings())
    # a future DEFAULTS key NOT added to the allowlist is NOT auto-shared
    with _patch(settings, "DEFAULTS", {**settings.DEFAULTS, "future_secret_token": "leak-me"}):
        check("a future DEFAULTS key is NOT auto-included in the bundle (allowlist gates it)",
              "future_secret_token" not in settings.support_bundle_settings())
    # [neg] the import-time subset guard catches a bogus allowlist entry
    check("[neg] an allowlist key not in DEFAULTS fails the subset guard",
          not (set(settings._SUPPORT_BUNDLE_KEYS + ("bogus_key",)) <= set(settings.DEFAULTS)))
    # the bundle manifest uses the allowlist, not all_settings()
    src = (ROOT / "scripts" / "gui_settings_api.py").read_text(encoding="utf-8")  # S1 home
    check("save_support_bundle's manifest line uses support_bundle_settings()",
          "f\"settings:   {settings.support_bundle_settings()}\\n\"" in src
          and "f\"settings:   {settings.all_settings()}\\n\"" not in src)


def main():
    test_settings_dedup_and_atomicity()
    test_auth_atomic_and_acl()
    test_support_bundle_allowlist()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL PERSISTENCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

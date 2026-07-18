"""Golden check for the P13 work-PC evidence collector (scripts/evidence.py).

The RM05 credential-safety proof, offline + CI-safe (the self-test is stubbed, so no
browser launches). Plants a realistic DATA_ROOT — a saved login (tsmis_auth.json with
a secret), an Edge sign-in profile, failure dumps, the exported report data, the TSN
inputs, plus the LEGITIMATE diagnostics (logs + run reports) — then asserts the bundle:

  * INCLUDES only the allowlist (manifest, self-test output, logs, run reports, and the
    user-placed evidence files);
  * NEVER includes the saved login / profile / failure dumps / report data / TSN inputs,
    and the secret string appears NOWHERE in the zip (manifest included);
  * lists EVERY included file in the manifest (RM05 'the manifest lists every file');
  * refuses a sensitive file even when the user drops it into the evidence folder;
  * captures the self-test output — and a self-test CRASH — into the bundle without
    failing the collection (the failing output IS the evidence).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_evidence_bundle.py
"""
import sys
import tempfile
import types
import zipfile
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import evidence
import paths

_fail = []
_SECRET = "SECRET-COOKIE-do-not-leak-9f3a2b"
# Adversarial secrets planted in COPIED browser/profile/source files inside the user
# evidence folder (P13-B01): the positive allowlist must refuse them all by basename/type.
_COOKIE_SECRET = "COOKIE-SECRET-123"
_LOGIN_SECRET = "LOGIN-DB-SECRET-456"
_HTML_SECRET = "HTML-PAGE-SECRET-789"


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _plant(root):
    """A realistic DATA_ROOT: legitimate diagnostics + sensitive material everywhere."""
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "logs" / "tsmis.log").write_text("2026-06-26 decision: picked Edge\n", encoding="utf-8")
    (root / "output" / "run_reports").mkdir(parents=True, exist_ok=True)
    (root / "output" / "run_reports" / "ramp_summary_run_20260626.csv").write_text(
        "route,status\n005,saved\n", encoding="utf-8")
    # Sensitive (must NEVER be collected):
    (root / "tsmis_auth.json").write_text(
        '{"cookies":[{"name":"SSO","value":"' + _SECRET + '"}]}', encoding="utf-8")
    (root / "edge_login_profile").mkdir(parents=True, exist_ok=True)
    (root / "edge_login_profile" / "Cookies").write_text(_SECRET, encoding="utf-8")
    (root / "failures").mkdir(parents=True, exist_ok=True)
    (root / "failures" / "route005.png").write_bytes(b"\x89PNG fake screenshot")
    (root / "output" / "2026-06-26 ssor-prod" / "ramp_summary").mkdir(parents=True, exist_ok=True)
    (root / "output" / "2026-06-26 ssor-prod" / "ramp_summary" / "r5.pdf").write_bytes(b"%PDF private")
    (root / "input" / "tsn_highway_log").mkdir(parents=True, exist_ok=True)
    (root / "input" / "tsn_highway_log" / "d07.pdf").write_bytes(b"%PDF tsn")


def _point_paths_at(root, saved):
    paths.DATA_ROOT = root
    paths.OUTPUT_ROOT = root / "output"
    paths.INPUT_ROOT = root / "input"
    paths.TSN_LIBRARY_ROOT = root / "tsn_library"
    paths.LOG_DIR = root / "logs"
    paths.FAILURES_DIR = root / "failures"
    paths.AUTH = root / "tsmis_auth.json"
    paths.EDGE_LOGIN_PROFILE_DIR = root / "edge_login_profile"


def _zip_text(zf):
    """All entry names + the full decoded bytes of every entry (for a leak scan)."""
    names = zf.namelist()
    blob = b"".join(zf.read(n) for n in names)
    return names, blob


def test_credential_exclusion_and_manifest():
    print("RM05: credential-safe bundle + full manifest listing:")
    saved = (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
             paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR)
    root = Path(tempfile.mkdtemp(prefix="tsmis_ev_"))
    user = Path(tempfile.mkdtemp(prefix="tsmis_ev_user_"))
    try:
        _plant(root)
        _point_paths_at(root, saved)
        # The user EXPLICITLY places real report/TSN source files (allowed) — plus, by
        # mistake OR misguidance, a copy of the saved login AND copied browser/profile
        # DBs + an internal page's saved HTML. The positive allowlist (PDF/XLSX/XLS)
        # must accept ONLY the real source and REFUSE everything else (P13-B01).
        (user / "intersection_detail_route_005.pdf").write_bytes(
            b"%PDF-1.4\n" + b"#" + (b"A" * 80) + b"\n%%EOF")
        wb = Workbook()
        wb.active.append(["Route", "PM", "Description"])
        wb.active.append(["001", "1.000", "clean workbook"])
        wb.save(user / "tsn_statewide.xlsx")
        (user / "tsmis_auth.json").write_text('{"cookies":["' + _SECRET + '"]}', encoding="utf-8")
        (user / "Cookies").write_text(_COOKIE_SECRET, encoding="utf-8")          # browser DB
        (user / "Login Data").write_text(_LOGIN_SECRET, encoding="utf-8")        # browser DB
        (user / "Web Data").write_text("x", encoding="utf-8")
        (user / "Local State").write_text("x", encoding="utf-8")
        (user / "Cookies.pdf").write_text(_COOKIE_SECRET, encoding="utf-8")      # renamed cookie store
        (user / "captured_internal_page.html").write_text(
            "<html>" + _HTML_SECRET + " internal source</html>", encoding="utf-8")
        (user / "notes.txt").write_text("just a note (wrong format)", encoding="utf-8")

        out = root / "evidence.zip"
        res = evidence.collect(out_path=out, extra_dir=user, emit=lambda *_: None,
                               run_self_test=False)
        check("collect returned ok", res.get("ok") is True and out.is_file())

        with zipfile.ZipFile(out) as zf:
            names, blob = _zip_text(zf)
            manifest = zf.read("manifest.txt").decode("utf-8")

        # INCLUDES the allowlist.
        check("includes manifest + self_test", "manifest.txt" in names and "self_test.txt" in names)
        check("includes the diagnostic log", "logs/tsmis.log" in names)
        check("includes the run report (summary, not report data)",
              any(n.startswith("run_reports/") and n.endswith(".csv") for n in names))
        check("includes the user-placed real PDF under user_evidence/",
              "user_evidence/intersection_detail_route_005.pdf" in names)
        check("includes the user-placed real workbook (XLSX is an allowed format)",
              "user_evidence/tsn_statewide.xlsx" in names)

        # P13-B01: --evidence-dir is a POSITIVE allowlist — copied browser/profile DBs,
        # an internal page's HTML, a renamed cookie store, and a stray .txt are all REFUSED.
        for bad in ("Cookies", "Login Data", "Web Data", "Local State", "Cookies.pdf",
                    "captured_internal_page.html", "notes.txt"):
            check(f"copied non-evidence file is NOT in the bundle: {bad}",
                  not any(n.endswith("/" + bad) or n.endswith(bad) for n in names))
        check("the browser-cookie secret appears in NO bundle file", _COOKIE_SECRET.encode() not in blob)
        check("the login-DB secret appears in NO bundle file", _LOGIN_SECRET.encode() not in blob)
        check("the internal-HTML secret appears in NO bundle file", _HTML_SECRET.encode() not in blob)
        skipped = res.get("skipped_user", [])
        check("the copied browser/profile/HTML/auth files are all REFUSED (skipped_user)",
              all(any(bad in p for p in skipped)
                  for bad in ("Cookies", "Login Data", "captured_internal_page.html",
                              "tsmis_auth.json", "notes.txt")))
        check("the manifest's REFUSED section lists them with a reason",
              "REFUSED from the evidence folder" in manifest
              and "browser/profile artifact" in manifest
              and "not an allowed evidence format" in manifest)

        # NEVER includes sensitive material from DATA_ROOT — and the secret appears NOWHERE.
        check("the saved login (tsmis_auth.json) is NOT in the bundle",
              not any("tsmis_auth.json" in n for n in names))
        check("the Edge profile is NOT in the bundle", not any("edge_login_profile" in n for n in names))
        check("failure dumps are NOT in the bundle", not any("failures" in n or n.endswith(".png") for n in names))
        check("exported report data is NOT in the bundle",
              not any(n.endswith("r5.pdf") or "2026-06-26 ssor-prod" in n for n in names))
        check("TSN inputs are NOT in the bundle", not any("d07.pdf" in n for n in names))
        check("the SECRET string appears in NO bundle file (manifest included)",
              _SECRET.encode() not in blob)

        # RM05: the manifest lists EVERY included file.
        data_entries = sorted(n for n in names)
        listed = manifest.split("BUNDLE CONTENTS")[-1]
        check("manifest lists every included file",
              all(n in listed for n in data_entries))
        check("manifest records the login as present-but-excluded (not its value)",
              "DELIBERATELY EXCLUDED" in manifest and _SECRET not in manifest)
        check("user dropped a sensitive file into the evidence folder -> REFUSED",
              any("tsmis_auth.json" in p for p in res.get("skipped_user", [])))
        # CMP-AUD-086: the live-verify set is the ENABLED export reports, registry-
        # derived — the app-wide-disabled Route History placeholder (no export flow)
        # is excluded, so the set is 15 rows, not all 16 registry entries.
        import reports
        rset = evidence._report_set()
        enabled_labels = [lbl for _i, lbl, _f, _s in reports.enabled_export_reports()]
        check("live-verify set == the enabled export reports (Route History excluded)",
              rset == enabled_labels and "Route History Table" not in rset)
        check("manifest lists the live-verify set (incl. the PDF editions)",
              "Intersection Detail (PDF)" in manifest and "Highway Log (PDF)" in manifest)
    finally:
        (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
         paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR) = saved
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(user, ignore_errors=True)


def test_self_test_capture_and_crash():
    print("self-test output (and a CRASH) is captured into the bundle, never fatal:")
    saved = (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
             paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR)
    saved_mod = sys.modules.get("self_test")
    root = Path(tempfile.mkdtemp(prefix="tsmis_ev_st_"))
    try:
        _plant(root)
        _point_paths_at(root, saved)
        # Stub self_test so no browser launches: first a clean run, then a crash.
        ok_mod = types.ModuleType("self_test")
        ok_mod.run = lambda emit=None: (emit or print)("FAKE-SELFTEST-LINE-42") or 0
        sys.modules["self_test"] = ok_mod
        out = root / "ev_ok.zip"
        evidence.collect(out_path=out, emit=lambda *_: None, run_self_test=True)
        with zipfile.ZipFile(out) as zf:
            st = zf.read("self_test.txt").decode("utf-8")
        check("a passing self-test's output is captured", "FAKE-SELFTEST-LINE-42" in st)

        def _boom(emit=None):
            raise RuntimeError("simulated self-test crash")
        crash_mod = types.ModuleType("self_test")
        crash_mod.run = _boom
        sys.modules["self_test"] = crash_mod
        out2 = root / "ev_crash.zip"
        res = evidence.collect(out_path=out2, emit=lambda *_: None, run_self_test=True)
        check("a CRASHING self-test still produces a bundle (ok)", res.get("ok") is True)
        with zipfile.ZipFile(out2) as zf:
            st2 = zf.read("self_test.txt").decode("utf-8")
        check("the crash is captured in self_test.txt (the failing output IS the evidence)",
              "SELF-TEST FAILED" in st2 and "simulated self-test crash" in st2)
    finally:
        if saved_mod is not None:
            sys.modules["self_test"] = saved_mod
        else:
            sys.modules.pop("self_test", None)
        (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
         paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR) = saved
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def test_unreadable_not_listed_as_bundled():
    """P13-A01: a locked/unreadable allowlisted file (e.g. the log) is recorded under
    SKIPPED, never falsely listed under BUNDLE CONTENTS — so the manifest can't be
    diagnostically false. The allowlisted-entry writer is monkeypatched to fail for
    the log only (logs are redacted through ``writestr`` before final scanning)."""
    print("P13-A01: an unreadable allowlisted file is NOT claimed as bundled:")
    import shutil
    saved = (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
             paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR)
    real_write = evidence._write_allowlisted_entry
    root = Path(tempfile.mkdtemp(prefix="tsmis_ev_unr_"))
    try:
        _plant(root)
        _point_paths_at(root, saved)

        def _flaky_write(zf, src, arc):
            if str(arc).startswith("logs/"):
                raise OSError("simulated locked log")
            return real_write(zf, src, arc)
        evidence._write_allowlisted_entry = _flaky_write

        out = root / "ev.zip"
        res = evidence.collect(out_path=out, emit=lambda *_: None, run_self_test=False)
        check("collection still succeeds despite the locked log", res.get("ok") is True)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            manifest = zf.read("manifest.txt").decode("utf-8")
        check("the locked log is NOT in the zip", not any(n.startswith("logs/") for n in names))
        listed = manifest.split("BUNDLE CONTENTS")[-1]
        check("the manifest does NOT list the locked log under BUNDLE CONTENTS",
              "logs/tsmis.log" not in listed)
        check("the manifest records it under SKIPPED — unreadable",
              "SKIPPED — unreadable" in manifest and "logs/tsmis.log" in manifest)
    finally:
        evidence._write_allowlisted_entry = real_write
        (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
         paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR) = saved
        shutil.rmtree(root, ignore_errors=True)


def test_final_member_credential_scan():
    """CMP-AUD-117: sanitize allowlisted text and scan the exact final ZIP.

    A credential in a diagnostic log is safely redacted. A hit inside an opaque
    user-supplied PDF cannot be rewritten, so publication fails closed and a prior
    good bundle at the destination remains untouched.
    """
    print("CMP-AUD-117: final ZIP member credential scan is fail-closed:")
    import shutil
    saved = (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
             paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR)
    root = Path(tempfile.mkdtemp(prefix="tsmis_ev_scan_"))
    user = Path(tempfile.mkdtemp(prefix="tsmis_ev_scan_user_"))
    try:
        _plant(root)
        _point_paths_at(root, saved)
        log_secret = "FINAL-LOG-SECRET-123"
        (root / "logs" / "tsmis.log").write_text(
            f"request failed\nAuthorization: Bearer {log_secret}\n", encoding="utf-8")

        clean_out = root / "clean.zip"
        clean_res = evidence.collect(out_path=clean_out, emit=lambda *_: None,
                                     run_self_test=False)
        check("a text-member credential is redacted and collection succeeds",
              clean_res.get("ok") is True and clean_out.is_file())
        with zipfile.ZipFile(clean_out) as zf:
            _names, clean_blob = _zip_text(zf)
        check("the log credential appears in NO final member",
              log_secret.encode() not in clean_blob and b"[redacted]" in clean_blob)

        binary_secret = "OPAQUE-PDF-SECRET-456"
        (user / "source.pdf").write_bytes(
            b"%PDF-1.4\nAuthorization: Bearer " + binary_secret.encode() + b"\n%%EOF")
        guarded_out = root / "guarded.zip"
        with zipfile.ZipFile(guarded_out, "w") as zf:
            zf.writestr("prior-good.txt", "safe")
        unsafe_res = evidence.collect(out_path=guarded_out, extra_dir=user,
                                      emit=lambda *_: None, run_self_test=False)
        check("an opaque member credential aborts publication",
              unsafe_res.get("ok") is False)
        with zipfile.ZipFile(guarded_out) as zf:
            names = zf.namelist()
            old_blob = b"".join(zf.read(n) for n in names)
        check("a failed final scan preserves the prior good bundle",
              names == ["prior-good.txt"] and binary_secret.encode() not in old_blob)

        # XLSX is a nested ZIP. The final gate must inspect its decompressed XML,
        # not merely the opaque compressed bytes stored in the outer bundle.
        (user / "source.pdf").unlink()
        nested_secret = "NESTED-XLSX-SECRET-789"
        with zipfile.ZipFile(user / "source.xlsx", "w", zipfile.ZIP_DEFLATED) as xlsx:
            xlsx.writestr(
                "xl/sharedStrings.xml",
                f"<sst><si><t>Authorization: Bearer {nested_secret}</t></si></sst>")
        nested_out = root / "nested-guarded.zip"
        nested_res = evidence.collect(out_path=nested_out, extra_dir=user,
                                      emit=lambda *_: None, run_self_test=False)
        check("a credential compressed inside an XLSX aborts publication",
              nested_res.get("ok") is False and not nested_out.exists()
              and "!xl/sharedStrings.xml" in nested_res.get("message", ""))

        (user / "source.xlsx").unlink()
        trailing_secret = "TRAILING-XLSX-SECRET-987"
        trailing_xlsx = user / "trailing.xlsx"
        wb = Workbook()
        wb.active.append(["clean"])
        wb.save(trailing_xlsx)
        with trailing_xlsx.open("ab") as stream:
            stream.write(
                f"\nAuthorization: Bearer {trailing_secret}\n".encode("ascii"))
        trailing_out = root / "trailing-guarded.zip"
        trailing_res = evidence.collect(out_path=trailing_out, extra_dir=user,
                                        emit=lambda *_: None, run_self_test=False)
        check("credential bytes appended to an XLSX container abort publication",
              trailing_res.get("ok") is False and not trailing_out.exists()
              and trailing_secret not in trailing_res.get("message", ""))

        trailing_xlsx.unlink()
        comment_secret = "XLSX-COMMENT-SECRET-246"
        commented_xlsx = user / "commented.xlsx"
        with zipfile.ZipFile(commented_xlsx, "w", zipfile.ZIP_DEFLATED) as xlsx:
            xlsx.writestr("xl/workbook.xml", "<workbook/>")
            xlsx.comment = f"Bearer {comment_secret}".encode("ascii")
        comment_out = root / "comment-guarded.zip"
        comment_res = evidence.collect(out_path=comment_out, extra_dir=user,
                                       emit=lambda *_: None, run_self_test=False)
        check("a credential in an XLSX ZIP comment aborts publication",
              comment_res.get("ok") is False and not comment_out.exists())

        commented_xlsx.unlink()
        named = user / "access_token=FILENAME-SECRET-321.pdf"
        named.write_bytes(b"%PDF-1.4\nno credential in the body\n%%EOF")
        named_out = root / "name-guarded.zip"
        named_res = evidence.collect(out_path=named_out, extra_dir=user,
                                     emit=lambda *_: None, run_self_test=False)
        check("a credential-shaped ZIP member name aborts publication",
              named_res.get("ok") is False and not named_out.exists())

        named.unlink()
        utf16_secret = "UTF16-SECRET-654"
        (user / "utf16.pdf").write_bytes(
            b"%PDF-1.4\n" +
            f"Authorization: Bearer {utf16_secret}".encode("utf-16-le") +
            b"\n%%EOF")
        utf16_out = root / "utf16-guarded.zip"
        utf16_res = evidence.collect(out_path=utf16_out, extra_dir=user,
                                     emit=lambda *_: None, run_self_test=False)
        check("a UTF-16 credential inside an opaque member aborts publication",
              utf16_res.get("ok") is False and not utf16_out.exists())
    finally:
        (paths.DATA_ROOT, paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
         paths.LOG_DIR, paths.FAILURES_DIR, paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR) = saved
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(user, ignore_errors=True)


def main():
    test_credential_exclusion_and_manifest()
    test_self_test_capture_and_crash()
    test_unreadable_not_listed_as_bundled()
    test_final_member_credential_scan()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL EVIDENCE-BUNDLE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

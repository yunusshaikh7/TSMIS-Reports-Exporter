"""Credential-safe, no-admin evidence collector for work-PC validation (P13).

The locked-down Caltrans work PC runs only an unsigned exe from a user-writable
folder — no admin / PowerShell / cmd / scheduled tasks. `TSMIS Exporter.exe
--collect-evidence` produces ONE zip a maintainer can read to validate the v0.18.0
candidate against the live TSMIS site, without ever leaving the user folder or
collecting anything sensitive. (The acceptance itself is v0.18.1 — see
docs/work-pc-validation.md; this mode only GATHERS the evidence.)

ALLOWLIST, not denylist — the bundle contains ONLY:
  * `manifest.txt` — this PC's name in paths, OS/version/build, login STATUS (never
    the saved login itself), the allowlisted diagnostic settings, the run-folder
    list, the 8-report live-verify set, and a listing of EVERY file in the bundle;
  * the rotating diagnostic logs (the "one log upload answers it" contract);
  * the recent run reports (per-route saved/empty/failed SUMMARIES — not report data);
  * `self_test.txt` — the offline self-test output (proves the EXACT frozen exe boots
    + runs every real code path on the work PC); and
  * OPTIONALLY, real source files the user EXPLICITLY placed in an evidence folder
    (`--evidence-dir`) — each listed in the manifest.

It NEVER collects (RM05): the saved login (`paths.AUTH` / tsmis_auth.json), the Edge
sign-in profile (`paths.EDGE_LOGIN_PROFILE_DIR`), failure dumps (`paths.FAILURES_DIR`
— screenshots / page HTML may carry report content), the exported report data
(`output/<run>/…`), the TSN input PDFs (`input/`), or the TSN library. Nothing under
DATA_ROOT is walked broadly — only the explicit allowlist above is added, and a
user-placed evidence file that happens to BE one of those sensitive paths is skipped
anyway (belt-and-suspenders).

Console-free-core note: a DIAGNOSTIC DRIVER (only `gui_main` imports it). It writes
through the injected `emit` sink + returns a result dict — never print/input/sys.exit.
The heavy self-test import lives inside `collect()`, so importing this module is cheap.
"""
import logging
import time
import zipfile
from pathlib import Path

import paths
import settings
import version

log = logging.getLogger("tsmis.evidence")

# Recent run reports to include (most-recent-first); a cap so a long-lived install
# doesn't produce a giant bundle.
_MAX_RUN_REPORTS = 50

# `--evidence-dir` is a POSITIVE allowlist (P13-B01), never an arbitrary recursive
# upload: ONLY the real report / TSN-export source formats a maintainer reconciles
# against (PDF + Excel workbooks). Everything else — a copied cookie store, a login
# DB, an internal page's saved HTML — is refused, so the RM05 promise can't be undone
# by what the user drops in the folder.
_ALLOWED_EVIDENCE_EXTS = frozenset({".pdf", ".xlsx", ".xls"})
# Browser/profile DB basenames refused regardless of extension (a renamed
# "Cookies.pdf" is still a cookie store). Matched on the lower-cased full name AND stem.
_PROFILE_BASENAMES = frozenset({
    "cookies", "login data", "web data", "local state", "history", "network",
    "preferences", "secure preferences", "trust tokens", "extension cookies",
})


def _sensitive_roots():
    """The directories/files this collector MUST NEVER include (RM05). Resolved so a
    user-placed evidence file that happens to BE one of these is still skipped. The
    report data / TSN input / library are sensitive too, but they are never on the
    allowlist below, so they can only enter via `extra_dir` — which this guards."""
    out = []
    for p in (paths.AUTH, paths.EDGE_LOGIN_PROFILE_DIR, paths.FAILURES_DIR,
              paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT):
        try:
            out.append(Path(p).resolve())
        except OSError:
            out.append(Path(p))
    return out


def _is_sensitive(f, roots):
    """True if `f` is, or sits under, any sensitive root — so it must not be
    included even when the user placed it in the evidence folder."""
    try:
        rf = Path(f).resolve()
    except OSError:
        rf = Path(f)
    for r in roots:
        if rf == r or rf.is_relative_to(r):
            return True
    # Also reject anything named like the saved-login file, wherever it sits.
    return rf.name.lower() == Path(paths.AUTH).name.lower()


def _report_set():
    """The export-report families to live-verify on the work PC, derived from the
    registry (so the 8-report shape — incl. Intersection Detail (PDF) — is automatic,
    never a hand-maintained list; CR002-RM5)."""
    try:
        import reports
        return [label for label, _fmt, _spec in reports.EXPORT_REPORTS]
    except Exception as e:                       # noqa: BLE001 (diagnostic; never fatal)
        log.warning("evidence: could not read the report registry (%s: %s)",
                    type(e).__name__, e)
        return []


def _refuse_reason(f, roots):
    """Why an evidence-folder file is refused, or None to ACCEPT it. `--evidence-dir`
    is a POSITIVE allowlist (only PDF / workbook report+TSN source formats) AND a
    credential guard, so a copied cookie store, login DB, browser-profile artifact, or
    internal page source can never enter the bundle (P13-B01 / RM05), no matter what
    the user drops in the folder."""
    if _is_sensitive(f, roots):
        return "sensitive path"
    if f.name.lower() in _PROFILE_BASENAMES or f.stem.lower() in _PROFILE_BASENAMES:
        return "browser/profile artifact"
    if f.suffix.lower() not in _ALLOWED_EVIDENCE_EXTS:
        return "not an allowed evidence format (PDF/XLSX/XLS only)"
    return None


def _allowlisted_entries(extra_dir, roots, emit):
    """The (source_path, arcname) pairs to add — logs + run reports + any user-placed
    evidence. Returns (entries, skipped_user): `skipped_user` is [(path, reason)] for
    every evidence-folder file refused (a sensitive path, a browser/profile artifact,
    or a non-evidence format) — so the RM05 promise can't be undone by what the user
    drops in the folder (P13-B01)."""
    entries = []
    # tsmis*.log* covers the per-entry-point family (tsmis-gui/cli/login.log)
    # AND the legacy shared tsmis.log from older installs.
    for pattern in ("tsmis*.log*", "crash.log", "update_helper.log"):
        for f in sorted(Path(paths.LOG_DIR).glob(pattern)):
            if f.is_file():
                entries.append((f, f"logs/{f.name}"))
    run_reports = sorted((Path(paths.OUTPUT_ROOT) / "run_reports").glob("*.csv"),
                         key=lambda p: p.stat().st_mtime, reverse=True)[:_MAX_RUN_REPORTS]
    for f in run_reports:
        entries.append((f, f"run_reports/{f.name}"))

    skipped_user = []
    if extra_dir:
        ed = Path(extra_dir)
        if ed.is_dir():
            for f in sorted(ed.rglob("*")):
                if not f.is_file():
                    continue
                reason = _refuse_reason(f, roots)
                if reason:
                    skipped_user.append((str(f), reason))
                    emit(f"  REFUSED ({reason}, not bundled): {f}")
                    continue
                entries.append((f, f"user_evidence/{f.relative_to(ed).as_posix()}"))
        else:
            emit(f"  NOTE: evidence folder not found, skipping: {ed}")
    return entries, skipped_user


def _manifest(contents, unreadable, skipped_user, roots):
    """The manifest text: provenance + safety statement + the 8-report live-verify
    set + a listing of every file ACTUALLY in the bundle (RM05 — 'the manifest lists
    every included file'), plus the evidence-folder files refused and any allowlisted
    file that was unreadable (P13-A01 — so the listing is never diagnostically false).
    `contents` is the actually-written arcnames; `unreadable` is [(arc, errtype)];
    `skipped_user` is [(path, reason)]."""
    auth_present = Path(paths.AUTH).is_file()
    lines = [
        f"{version.APP_NAME} — work-PC evidence bundle",
        "",
        "SAFETY: this bundle is credential-safe. It contains the diagnostic logs, run",
        "  reports (per-route SUMMARIES, not report data), the offline self-test output,",
        "  and ONLY the report/TSN source files (PDF/Excel) you explicitly placed in",
        "  --evidence-dir — a copied cookie store, login DB, or page-source file there is",
        "  REFUSED. It NEVER contains your saved login, the Edge sign-in profile, failure dumps, the",
        "  exported report data, or the TSN inputs/library. It does include this PC's name",
        "  in file paths + selected diagnostic settings (diagnostics need them), so send",
        "  it to the TSMIS maintainer, not a public forum.",
        "",
        f"created:     {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"version:     {version.__version__}",
        f"build:       {'frozen' if paths.is_frozen() else 'dev'}",
        f"data_root:   {paths.DATA_ROOT}",
        f"output:      {paths.OUTPUT_ROOT}",
        f"login:       {'saved login file present on this PC — DELIBERATELY EXCLUDED' if auth_present else 'none'}",
        f"settings:    {settings.support_bundle_settings()}",
        "",
        "LIVE-VERIFY SET (the 8-report v0.18.0 shape — see docs/work-pc-validation.md):",
    ]
    for r in _report_set():
        lines.append(f"  - {r}")
    lines += [
        "",
        "DELIBERATELY EXCLUDED (never collected — RM05):",
        "  - saved login (tsmis_auth.json)        - Edge sign-in profile",
        "  - failure dumps (failures/)            - exported report data (output/<run>/…)",
        "  - TSN input PDFs (input/)              - TSN library",
    ]
    if skipped_user:
        lines.append("")
        lines.append(f"REFUSED from the evidence folder ({len(skipped_user)} — not an allowed "
                     "evidence format, or a sensitive/profile artifact; NEVER bundled):")
        for p, reason in skipped_user:
            lines.append(f"  [{reason}] {p}")
    if unreadable:
        lines.append("")
        lines.append(f"SKIPPED — unreadable on this PC ({len(unreadable)}; NOT in the bundle):")
        for arc, err in unreadable:
            lines.append(f"  {arc} ({err})")
    lines += ["", "BUNDLE CONTENTS (every file actually in this zip):"]
    for arc in contents:
        lines.append(f"  {arc}")
    return "\n".join(lines) + "\n"


def collect(out_path=None, extra_dir=None, emit=None, run_self_test=True,
            validation=None):
    """Build the credential-safe evidence zip. Returns a result dict:
    `{ok, path, files, excluded, skipped_user, message}`.

    `out_path` defaults to a timestamped zip in DATA_ROOT (a user-writable folder).
    `extra_dir` is the user's explicit evidence folder for real source PDFs/workbooks
    (each listed in the manifest; sensitive files there are refused). `run_self_test`
    runs the offline self-test and captures its output (the work-PC default); a caller
    that can't launch a browser passes False (the bundle still ships, noting the skip).
    Never raises for an expected failure — a locked log or a self-test crash is
    captured into the bundle, not propagated."""
    emit = emit or print
    out_path = Path(out_path) if out_path else (
        Path(paths.DATA_ROOT) / f"tsmis_evidence_{time.strftime('%Y%m%d_%H%M%S')}.zip")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    roots = _sensitive_roots()

    emit("=" * 60)
    emit(f"{version.APP_NAME} — collecting work-PC evidence (credential-safe)")
    emit("=" * 60)

    # The offline self-test (captured, never fatal): the whole point is to ship the
    # output EVEN when it fails — a failing self-test on the work PC is the evidence.
    st_lines = []
    if run_self_test:
        emit("Running the offline self-test (this exercises the real code paths)…")
        try:
            import self_test
            self_test.run(emit=st_lines.append)
        except Exception as e:                   # noqa: BLE001 (capture, don't crash collection)
            st_lines.append(f"SELF-TEST FAILED: {type(e).__name__}: {e}")
            log.warning("evidence: self-test raised (captured into the bundle)", exc_info=True)
    else:
        st_lines.append("self-test skipped (run --collect-evidence on the work PC to capture it).")
    self_test_text = "\n".join(st_lines) + "\n"

    # W1: the one-click validation manifest (counts/outcomes/folder names only —
    # never report data, per RM05). Both a readable digest and the raw JSON ride
    # in the bundle so a maintainer sees exactly what the samples produced.
    validation_txt = validation_json = None
    if validation is not None:
        try:
            import importlib
            import json as _json
            _val_mod = importlib.import_module("validation")   # not `import validation` — the param shadows it
            validation_txt = "\n".join(_val_mod.summary_lines(validation)) + "\n"
            validation_json = _json.dumps(validation, indent=2, default=str)
        except Exception as e:                   # noqa: BLE001 — the bundle still ships
            validation_txt = f"validation summary unavailable ({type(e).__name__}: {e})\n"
            log.warning("evidence: validation render failed (%s)", type(e).__name__)

    entries, skipped_user = _allowlisted_entries(extra_dir, roots, emit)

    # P13-A01: write the data entries FIRST, recording the files ACTUALLY written and
    # any that were unreadable, then write the manifest LAST from that real set — so a
    # locked/unreadable log is listed under SKIPPED, never falsely claimed as bundled.
    written, unreadable = [], []
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("self_test.txt", self_test_text)
            if validation_txt is not None:
                zf.writestr("validation.txt", validation_txt)
            if validation_json is not None:
                zf.writestr("validation.json", validation_json)
            for src, arc in entries:
                try:
                    zf.write(src, arc)
                    written.append(arc)
                except OSError as e:             # one locked file shouldn't sink the bundle
                    unreadable.append((arc, type(e).__name__))
                    emit(f"  SKIPPED (unreadable): {src} ({type(e).__name__})")
                    log.info("evidence: skipped %s (%s: %s)", src, type(e).__name__, e)
            _val_files = (["validation.txt"] if validation_txt is not None else []) \
                + (["validation.json"] if validation_json is not None else [])
            contents = ["manifest.txt", "self_test.txt"] + _val_files + written
            manifest_text = _manifest(contents, unreadable, skipped_user, roots)
            zf.writestr("manifest.txt", manifest_text)
    except OSError as e:
        msg = f"Could not write the evidence bundle to {out_path} ({type(e).__name__}: {e})."
        emit(msg)
        log.warning("evidence: %s", msg)
        return {"ok": False, "path": str(out_path), "files": 0,
                "excluded": [str(r) for r in roots],
                "skipped_user": [p for p, _r in skipped_user], "message": msg}

    total = len(written) + 2                      # + manifest.txt + self_test.txt
    emit("")
    emit(f"Evidence bundle saved ({total} files): {out_path}")
    emit("  It has logs, run reports, the self-test output and only the report/TSN "
         "source files you placed — never your saved login, profile, or report data.")
    return {"ok": True, "path": str(out_path), "files": total,
            "excluded": [str(r) for r in roots], "skipped_user": [p for p, _r in skipped_user],
            "manifest": manifest_text}

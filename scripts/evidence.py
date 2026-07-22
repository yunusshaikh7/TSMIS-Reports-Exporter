"""Credential-safe, no-admin evidence collector for work-PC validation (P13).

The locked-down Caltrans work PC runs only an unsigned exe from a user-writable
folder — no admin / PowerShell / cmd / scheduled tasks. `TSMIS Exporter.exe
--collect-evidence` produces ONE zip a maintainer can read to validate the v0.18.0
candidate against the live TSMIS site, without ever leaving the user folder or
collecting anything sensitive. (The acceptance itself is v0.18.1 — see
docs/work-pc-validation.md; this mode only GATHERS the evidence.)

The bundle has to be SELF-SUFFICIENT: a maintainer reads it once and knows why the
field PC behaved differently, without a second round trip. So it carries everything a
diagnosis needs — and, just as deliberately, none of the report data.

ALLOWLIST, not denylist — the bundle contains ONLY:
  * `manifest.txt` — this PC's name in paths, OS/version/build, login STATUS (never
    the saved login itself), the allowlisted diagnostic settings, the run-folder
    list, the export-report live-verify set, and a listing of EVERY file in the bundle;
  * `environment.txt` — the PC facts no log line carries: the **long-path policy**
    (a managed PC has it off and cannot change it — that is the dev-vs-field
    difference CMP-AUD-242 turned on), a PATH-LENGTH CENSUS against the 260-character
    limit with the longest paths named, free disk, and the data-root length every
    other path spends from;
  * `inventory.txt` — NAME/SIZE/DATE for every file under the data roots, no content.
    A name-shaped failure is invisible in a log and invisible in an artifact, but
    obvious in a listing (the v0.27.0 field bug was a 148-character basename);
  * `state/…` — the JSON sidecars that say what each artifact CLAIMS to be:
    completion/trust outcomes, provenance (source paths + digests), content
    fingerprints, evidence generation manifests, and the per-cell attempt overlay;
  * the rotating diagnostic logs (the "one log upload answers it" contract);
  * the recent run reports (per-route saved/empty/failed SUMMARIES — not report data);
  * `self_test.txt` — the offline self-test output (proves the EXACT frozen exe boots
    + runs every real code path on the work PC); and
  * OPTIONALLY, real source files the user EXPLICITLY placed in an evidence folder
    (`--evidence-dir`) — each listed in the manifest.

It NEVER collects (RM05): the saved login (`paths.AUTH` / tsmis_auth.json), the Edge
sign-in profile (`paths.EDGE_LOGIN_PROFILE_DIR`), failure dumps (`paths.FAILURES_DIR`
— screenshots / page HTML may carry report content), the exported report data
(`output/<run>/…`), the compressed comparison payloads (they carry compared ROWS —
their names and sizes appear in the inventory, their bytes never do), the TSN input
PDFs (`input/`), or the TSN library workbooks. The state sweep walks the same folders
those artifacts live in, so it matches by EXACT sidecar suffix/name — a data workbook,
a source PDF, or a payload chunk can never match — and a user-placed evidence file
that happens to BE one of the sensitive paths is skipped anyway (belt-and-suspenders).

Console-free-core note: a DIAGNOSTIC DRIVER (only `gui_main` imports it). It writes
through the injected `emit` sink + returns a result dict — never print/input/sys.exit.
The heavy self-test import lives inside `collect()`, so importing this module is cheap.
"""
import logging
import os
import tempfile
import time
import zipfile
from pathlib import Path

import credential_safety
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


# The METADATA sidecars a run leaves beside its artifacts. These carry completion
# states, producer versions, generation ids, source paths and digests — never report
# rows — and they are what a field report is usually actually about ("the comparison
# built but the Matrix hides it"). Matched by EXACT suffix / name so a data workbook,
# a source PDF, or a compressed comparison payload can never match.
_STATE_SUFFIXES = (".outcome.json", ".provenance.json", ".fingerprint.json",
                   " (evidence).json")
_STATE_NAMES = frozenset({"_attempts.json"})
# Cache/state JSON that lives directly in a `comparisons/` folder (the matrix caches
# and the per-cell attempt overlay).
_STATE_DIR_NAMES = frozenset({"comparisons"})
# One cap for every sweep. These walks are stat-only (no bytes read), so the ceiling
# exists to bound a pathological folder, not to save work — and the state sweep uses
# the SAME ceiling as the inventory so the bundle can never list a file it then
# silently declined to collect the sidecar for.
_MAX_SCAN_FILES = 20000
# Windows refuses a path at 260 unless long paths are enabled; 240 is the "getting
# close" line worth flagging before it becomes a field failure (CMP-AUD-242).
_PATH_WARN = 240
_PATH_LIMIT = 260
_LONGEST_PATHS_SHOWN = 15


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
    """The ENABLED export-report families to live-verify on the work PC, derived
    from the registry (so the set is automatic, never a hand-maintained list;
    CR002-RM5). App-wide-disabled reports are excluded — the reserved Route History
    placeholder has no export flow, so there is nothing to live-verify (CMP-AUD-086;
    the set is 15 enabled reports, not all 16 registry rows)."""
    try:
        import reports
        return [label for _i, label, _fmt, _spec in reports.enabled_export_reports()]
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


def _is_state_sidecar(f):
    """Whether `f` is one of the metadata sidecars the bundle may carry."""
    name = f.name
    if name in _STATE_NAMES and f.parent.name in _STATE_DIR_NAMES:
        return True
    return any(name.endswith(sfx) for sfx in _STATE_SUFFIXES)


def _walk_files(root, cap):
    """Every file under `root`, sorted, capped. Never reads a byte — `os.walk` +
    `stat` only, so a huge export store costs a directory scan, not a copy."""
    out, truncated = [], False
    try:
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in sorted(filenames):
                out.append(Path(dirpath) / name)
                if len(out) >= cap:
                    truncated = True
                    return sorted(out), truncated
    except OSError as e:  # silent-ok: an unreadable store is reported, never fatal
        log.info("evidence: could not walk %s (%s: %s)", root, type(e).__name__, e)
    return sorted(out), truncated


def _state_entries():
    """(source, arcname) for every metadata sidecar under the data roots.

    The artifacts themselves (workbooks, PDFs, the compressed comparison payloads)
    stay OUT — only the JSON that says what they claim to be. This is the half of a
    field report the logs cannot answer: which generation is published, whether it is
    trusted, what the last attempt did, and which sources a comparison actually read.
    """
    entries, truncated = [], False
    for root, label in ((paths.OUTPUT_ROOT, "output"),
                        (paths.TSN_LIBRARY_ROOT, "tsn_library")):
        root = Path(root)
        if not root.is_dir():
            continue
        files, was_capped = _walk_files(root, _MAX_SCAN_FILES)
        truncated = truncated or was_capped
        for f in files:
            if not _is_state_sidecar(f):
                continue
            try:
                rel = f.relative_to(root).as_posix()
            except ValueError:  # silent-ok: a walk result outside its own root is simply skipped
                continue
            entries.append((f, f"state/{label}/{rel}"))
    return entries, truncated


def _inventory_text():
    """A NAME/SIZE/MTIME listing of the data roots — no bytes, no content.

    Answers "what did this install actually produce" without shipping any of it, and
    it is how a name-shaped failure becomes visible: the v0.27.0 field bug was a
    148-character payload sidecar basename, which no log line and no artifact could
    show, but a listing shows immediately.
    """
    lines = ["File inventory — names, sizes and timestamps only. No file content.",
             ""]
    for root in (paths.OUTPUT_ROOT, paths.INPUT_ROOT, paths.TSN_LIBRARY_ROOT,
                 paths.LOG_DIR):
        root = Path(root)
        lines.append(f"[{root}]")
        if not root.is_dir():
            lines.append("  (absent)")
            lines.append("")
            continue
        files, truncated = _walk_files(root, _MAX_SCAN_FILES)
        total = 0
        for f in files:
            try:
                st = f.stat()
            except OSError:  # silent-ok: listed as unstattable rather than dropped
                lines.append(f"  {'?':>12}  {'?':<19}  {f.name}  (unreadable)")
                continue
            total += st.st_size
            when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
            try:
                rel = f.relative_to(root).as_posix()
            except ValueError:  # silent-ok: fall back to the full path in the listing
                rel = str(f)
            lines.append(f"  {st.st_size:>12,}  {when}  {rel}")
        lines.append(f"  -- {len(files):,} file(s), {total:,} bytes"
                     + ("  [TRUNCATED at the inventory cap]" if truncated else ""))
        lines.append("")
    return "\n".join(lines) + "\n"


def _long_path_policy():
    """Whether this PC allows paths past MAX_PATH. On a managed work PC this is 0 and
    cannot be changed by the user — and it is exactly the dev-vs-field difference that
    made a path-length bug invisible in development."""
    if os.name != "nt":
        return "n/a (not Windows)"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            value, _kind = winreg.QueryValueEx(key, "LongPathsEnabled")
        return (f"{int(value)} — long paths ENABLED (paths may exceed "
                f"{_PATH_LIMIT}); a managed PC usually has 0" if int(value)
                else f"0 — long paths DISABLED (a path at or past {_PATH_LIMIT} "
                     "will fail); this is the managed-PC default")
    except FileNotFoundError:
        return f"not set — treat as 0 (a path at or past {_PATH_LIMIT} will fail)"
    except OSError as e:  # silent-ok: an unreadable policy is reported, never fatal
        return f"unreadable ({type(e).__name__})"


def _environment_text():
    """The PC facts that decide whether the app can do what it was asked to.

    Every one of these has been the answer to a field report at least once, and none
    of them is visible in a log line.
    """
    import platform
    import shutil as _shutil
    lines = [
        f"{version.APP_NAME} — environment facts",
        "",
        f"app version:        {version.__version__}",
        f"build:              {'frozen exe' if paths.is_frozen() else 'dev checkout'}",
        f"os:                 {platform.platform()}",
        f"python:             {platform.python_version()}",
        f"data root:          {paths.DATA_ROOT}",
        f"long-path policy:   {_long_path_policy()}",
    ]
    try:
        usage = _shutil.disk_usage(str(paths.DATA_ROOT))
        lines.append(f"free space:         {usage.free:,} bytes of {usage.total:,}")
    except OSError as e:  # silent-ok: disk stats are a nicety, not a gate
        lines.append(f"free space:         unreadable ({type(e).__name__})")

    root = str(paths.DATA_ROOT)
    lines += [
        f"data-root length:   {len(root)} chars"
        f"  (every artifact path starts here, so this is the budget everything else"
        f" spends from {_PATH_LIMIT})",
        "",
        f"PATH-LENGTH CENSUS (the {_PATH_LIMIT}-character Windows limit):",
    ]
    files, truncated = _walk_files(paths.DATA_ROOT, _MAX_SCAN_FILES)
    if not files:
        lines.append("  (no files under the data root yet)")
        return "\n".join(lines) + "\n"
    lengths = sorted(((len(str(f)), str(f)) for f in files), reverse=True)
    over_limit = [p for n, p in lengths if n >= _PATH_LIMIT]
    over_warn = [p for n, p in lengths if _PATH_WARN <= n < _PATH_LIMIT]
    lines += [
        f"  files scanned:      {len(files):,}"
        + ("  [TRUNCATED at the inventory cap]" if truncated else ""),
        f"  longest path:       {lengths[0][0]} chars",
        f"  at or past {_PATH_LIMIT}:     {len(over_limit):,}"
        + ("   <-- THESE WILL FAIL unless long paths are enabled" if over_limit else ""),
        f"  within {_PATH_LIMIT - _PATH_WARN} of it:     {len(over_warn):,}"
        + ("   <-- at risk if the install moves deeper" if over_warn else ""),
        "",
        f"  the {min(_LONGEST_PATHS_SHOWN, len(lengths))} longest:",
    ]
    for n, p in lengths[:_LONGEST_PATHS_SHOWN]:
        flag = "  <-- OVER" if n >= _PATH_LIMIT else ("  <-- close" if n >= _PATH_WARN else "")
        lines.append(f"    {n:>4}  {p}{flag}")
    return "\n".join(lines) + "\n"


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
    state, state_truncated = _state_entries()
    if state_truncated:
        emit(f"  NOTE: more than {_MAX_SCAN_FILES:,} files under the data roots — "
             "the state sweep stopped at the cap")
    entries.extend(state)

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


def _manifest(contents, unreadable, skipped_user, roots, session=None):
    """The manifest text: provenance + safety statement + the export-report live-verify
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
        "  this PC's environment facts, a NAME/SIZE/DATE-only file inventory, the JSON",
        "  state sidecars that say what each artifact CLAIMS to be (completion, trust,",
        "  generation, source digests — never report rows), and ONLY the report/TSN",
        "  source files (PDF/Excel) you explicitly placed in --evidence-dir — a copied",
        "  cookie store, login DB, or page-source file there is REFUSED. It NEVER contains",
        "  your saved login, the Edge sign-in profile, failure dumps, the exported report",
        "  data, the compressed comparison payloads, or the TSN inputs/library. It does",
        "  include this PC's name in file paths + selected diagnostic settings",
        "  (diagnostics need them), so send it to the TSMIS maintainer, not a public forum.",
        "",
        f"created:     {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"version:     {version.__version__}",
        f"build:       {'frozen' if paths.is_frozen() else 'dev'}",
        f"data_root:   {paths.DATA_ROOT}",
        f"output:      {paths.OUTPUT_ROOT}",
        f"login:       {'saved login file present on this PC — DELIBERATELY EXCLUDED' if auth_present else 'none'}",
        f"settings:    {settings.support_bundle_settings()}",
    ]
    # Facts only a LIVE GUI session knows (which site/browser it is talking to, how it
    # signed in). The engine cannot read them, so the caller supplies them rather than
    # keeping a second bundle writer alive just to record them.
    for key, value in (session or {}).items():
        lines.append(f"{(key + ':'):<13}{value}")
    lines += [
        "",
        "LIVE-VERIFY SET (every export report — see docs/work-pc-validation.md):",
    ]
    for r in _report_set():
        lines.append(f"  - {r}")
    lines += [
        "",
        "DELIBERATELY EXCLUDED (never collected — RM05):",
        "  - saved login (tsmis_auth.json)        - Edge sign-in profile",
        "  - failure dumps (failures/)            - exported report data (output/<run>/…)",
        "  - TSN input PDFs (input/)              - TSN library workbooks/prints",
        "  - the compressed comparison payloads (.comparison-payload.zlib — they carry",
        "    compared ROWS; their names and sizes are in inventory.txt, their bytes are not)",
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


def _write_allowlisted_entry(zf, src, arc):
    """Write one allowlisted entry, redacting diagnostics that are plain text.

    Logs and run reports are useful precisely because they contain messages, so
    dropping the whole file for one credential-shaped value is needlessly harsh.
    User-provided PDF/Excel evidence is opaque and must remain byte-identical; the
    final ZIP scanner rejects publication if one of those members contains a hit.
    """
    if arc.startswith(("logs/", "run_reports/", "state/")):
        text = Path(src).read_text(encoding="utf-8", errors="replace")
        zf.writestr(arc, credential_safety.redact_text(text))
    else:
        zf.write(src, arc)


def _unlink_quiet(path):
    try:
        Path(path).unlink()
    except OSError:  # silent-ok: temp cleanup after result is already reported; prior bundle stays
        pass


def collect(out_path=None, extra_dir=None, emit=None, run_self_test=True,
            validation=None, session=None):
    """Build the credential-safe evidence zip. Returns a result dict:
    `{ok, path, files, excluded, skipped_user, message}`.

    **This is the ONE bundle writer.** Every trigger — the Settings button, the
    validate-and-package flow, and `--collect-evidence` — comes through here, so the
    allowlist, the credential redaction and the final zip scan can never apply to one
    path and not another.

    `out_path` defaults to a timestamped zip in DATA_ROOT (a user-writable folder).
    `extra_dir` is the user's explicit evidence folder for real source PDFs/workbooks
    (each listed in the manifest; sensitive files there are refused). `run_self_test`
    runs the offline self-test and captures its output (the work-PC default); a caller
    that can't launch a browser passes False (the bundle still ships, noting the skip)
    — **a caller on the GUI thread MUST pass False**, because the self-test opens a
    second WebView2 window and that is unsafe while the live GUI owns the main-thread
    loop. `session` is an optional {label: value} of facts only a live GUI session
    knows (the site it is talking to, the browser channel, how it signed in), rendered
    into the manifest so a GUI caller never needs a bundle writer of its own.
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
    self_test_text = credential_safety.redact_text("\n".join(st_lines) + "\n")

    # W1: the one-click validation manifest (counts/outcomes/folder names only —
    # never report data, per RM05). Both a readable digest and the raw JSON ride
    # in the bundle so a maintainer sees exactly what the samples produced.
    validation_txt = validation_json = None
    if validation is not None:
        try:
            import importlib
            import json as _json
            _val_mod = importlib.import_module("validation")   # not `import validation` — the param shadows it
            validation_txt = credential_safety.redact_text(
                "\n".join(_val_mod.summary_lines(validation)) + "\n")
            validation_json = credential_safety.redact_text(
                _json.dumps(validation, indent=2, default=str))
        except Exception as e:                   # noqa: BLE001 — the bundle still ships
            validation_txt = credential_safety.redact_text(
                f"validation summary unavailable ({type(e).__name__}: {e})\n")
            log.warning("evidence: validation render failed (%s)", type(e).__name__)

    entries, skipped_user = _allowlisted_entries(extra_dir, roots, emit)

    # P13-A01: write the data entries FIRST, recording the files ACTUALLY written and
    # any that were unreadable, then write the manifest LAST from that real set — so a
    # locked/unreadable log is listed under SKIPPED, never falsely claimed as bundled.
    written, unreadable = [], []
    tmp_path = None
    published_members = []
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{out_path.name}.", suffix=".tmp",
                                        dir=str(out_path.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("self_test.txt", self_test_text)
            zf.writestr("environment.txt",
                        credential_safety.redact_text(_environment_text()))
            zf.writestr("inventory.txt",
                        credential_safety.redact_text(_inventory_text()))
            if validation_txt is not None:
                zf.writestr("validation.txt", validation_txt)
            if validation_json is not None:
                zf.writestr("validation.json", validation_json)
            for src, arc in entries:
                try:
                    _write_allowlisted_entry(zf, src, arc)
                    written.append(arc)
                except OSError as e:             # one locked file shouldn't sink the bundle
                    unreadable.append((arc, type(e).__name__))
                    emit(f"  SKIPPED (unreadable): {src} ({type(e).__name__})")
                    log.info("evidence: skipped %s (%s: %s)", src, type(e).__name__, e)
            _val_files = (["validation.txt"] if validation_txt is not None else []) \
                + (["validation.json"] if validation_json is not None else [])
            contents = (["manifest.txt", "self_test.txt", "environment.txt",
                         "inventory.txt"] + _val_files + written)
            manifest_text = credential_safety.redact_text(
                _manifest(contents, unreadable, skipped_user, roots, session))
            zf.writestr("manifest.txt", manifest_text)

        with zipfile.ZipFile(tmp_path, "r") as verify_zip:
            published_members = verify_zip.namelist()
        if len(published_members) != len(set(published_members)):
            msg = ("Evidence bundle was not saved because two collected files "
                   "would have the same archive name.")
            emit(msg)
            log.warning("evidence: duplicate archive member names rejected")
            return {"ok": False, "path": str(out_path), "files": 0,
                    "excluded": [str(r) for r in roots],
                    "skipped_user": [p for p, _r in skipped_user], "message": msg}

        # CMP-AUD-117: inspect the exact, closed ZIP that would be published. Text
        # diagnostics were redacted above; an opaque PDF/XLSX hit cannot be safely
        # rewritten, so retain any prior good bundle and fail closed.
        hit = credential_safety.scan_zip_members(tmp_path)
        if hit:
            member, kind = hit
            msg = (f"Evidence bundle was not saved because credential-like content "
                   f"remained in {member} ({kind}). Remove/redact that source and retry.")
            emit(msg)
            log.warning("evidence: final credential scan rejected %s (%s)", member, kind)
            return {"ok": False, "path": str(out_path), "files": 0,
                    "excluded": [str(r) for r in roots],
                    "skipped_user": [p for p, _r in skipped_user], "message": msg}
        os.replace(tmp_path, out_path)
    except (OSError, zipfile.BadZipFile) as e:
        msg = f"Could not write the evidence bundle to {out_path} ({type(e).__name__}: {e})."
        emit(msg)
        log.warning("evidence: %s", msg)
        return {"ok": False, "path": str(out_path), "files": 0,
                "excluded": [str(r) for r in roots],
                "skipped_user": [p for p, _r in skipped_user], "message": msg}
    finally:
        if tmp_path is not None:
            _unlink_quiet(tmp_path)

    total = len(published_members)
    emit("")
    emit(f"Evidence bundle saved ({total} files): {out_path}")
    emit("  It has logs, run reports, the self-test output and only the report/TSN "
         "source files you placed — never your saved login, profile, or report data.")
    return {"ok": True, "path": str(out_path), "files": total,
            "excluded": [str(r) for r in roots], "skipped_user": [p for p, _r in skipped_user],
            "manifest": manifest_text}

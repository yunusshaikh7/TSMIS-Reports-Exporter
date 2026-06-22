"""Transactional artifact lifecycle (P2) — one leaf module for three concerns:

  * **Atomic single-file write** (`atomic_save`, `commit_workbook`) — write to a temp
    sibling, validate, then ``os.replace`` it onto the final path, so an interrupted /
    failed / locked write NEVER truncates the prior good artifact (F9). The wrapper is
    handed a TEMP path and finalizes it, so the regression-locked ``compare_core`` is
    untouched — it just writes to the path it is given; the wrapper rewrites any leaked
    temp name back out of the returned result.

  * **Journaled store promotion + startup recovery** (`promote_store`,
    `recover_promotions`) — the Export-Everything store swap (`live` <- `staging`) is
    journaled so a crash BETWEEN the two renames is repaired on the next launch from the
    retained backup: there is never a window with zero copies (F2). Recovery is
    idempotent and runs from `updater.cleanup_leftovers`.

  * **Input fingerprint** (`fingerprint`, `consolidated_fresh`) — freshness tracks input
    IDENTITY, not newest-mtime: a hash of the store's sorted ``(name, size, mtime_ns)``
    (R1-R03). A DELETED (non-newest) route changes the fingerprint though it leaves the
    newest-mtime untouched, so a stale consolidated no longer reads as fresh (F5).

Console-free (the core contract): reports via ``log`` + return values / raises, never
print/input/exit. Module-level imports are stdlib + ``events`` (the ConsolidateResult
shape); ``openpyxl`` is imported LAZILY inside ``_openable_xlsx`` (workbook validation
opens the produced file to reject a malformed/unreadable XLSX before committing it).
"""
import hashlib
import json
import logging
import os
import uuid
import zipfile
from pathlib import Path

from events import ConsolidateResult

log = logging.getLogger("tsmis.artifact_store")

# Sidecar written beside a consolidated workbook recording its inputs' fingerprint.
_FP_SUFFIX = ".fingerprint.json"
_FP_SCHEMA = 1
# fingerprint() sentinel: the folder (or a file in it) could not be read -> the caller
# must treat freshness CONSERVATIVELY (rebuild), never as a silent match.
_UNREADABLE = "unreadable"
# Names excluded from a store fingerprint: Excel lock files, our own sidecars, and the
# in-flight temp / staging siblings this module itself creates.
_FP_EXCLUDED_SUFFIXES = (_FP_SUFFIX, ".outcome.json", ".staging")
# The per-route export artifacts a store legitimately contains (P2-R01: staging must hold
# a real report file, not just any regular file). XLSX for every report; PDF for the
# Ramp Summary and Highway Log PDF stores.
_REPORT_SUFFIXES = (".xlsx", ".pdf")


def _new_token():
    """A short unique token for temp / backup names (per write, per promotion)."""
    return uuid.uuid4().hex[:12]


def _silent_unlink(path):
    """Best-effort unlink; never raises. True iff the file is gone afterwards."""
    if path is None:
        return True
    try:
        Path(path).unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _values_twin(path):
    """The values-flavor sibling compare_core derives from a picked name:
    ``<stem> (values)<suffix>`` (mirrors compare_core.run_compare)."""
    path = Path(path)
    return path.with_name(f"{path.stem} (values){path.suffix}")


# --------------------------------------------------------------------------- #
# atomic single-file write (F9)
# --------------------------------------------------------------------------- #
def atomic_save(workbook, out_path):
    """Save an openpyxl `workbook` to a temp sibling of `out_path`, then atomically
    ``os.replace`` it onto `out_path`. An interrupted or failed write (disk error, or
    the DESTINATION open in Excel -> ``PermissionError`` on ``os.replace``) leaves the
    prior `out_path` UNTOUCHED (F9: never truncate a good prior artifact). The original
    exception propagates to the caller's existing handler AFTER the temp is removed, so
    a consolidator's ``except PermissionError`` keeps reporting "file open in Excel"."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f"{out_path.stem}.tmp-{_new_token()}{out_path.suffix}")
    try:
        workbook.save(tmp)
        os.replace(tmp, out_path)
    except BaseException:
        _silent_unlink(tmp)
        raise


def _openable_xlsx(path, expect_sheet=None):
    """A produced workbook is committable iff openpyxl can actually OPEN it — so a corrupt
    ZIP or a malformed workbook part (e.g. ``xl/workbook.xml`` = ``b"not xml"``) is
    REJECTED, not just name-checked (P2-B05) — AND it has >=1 sheet (and `expect_sheet`,
    when given, is present: the per-comparison sheet contract). ``read_only`` load is lazy
    (it parses ``workbook.xml`` + the sheet list, not the cells), so it stays cheap even
    for a big live-formulas workbook. Never raises — any open/parse failure ⇒ invalid.

    The workbook is opened on a caller-owned file object closed by ``with`` (P2-R04): if
    ``load_workbook`` raises on a malformed part it would otherwise leave openpyxl's ZIP
    handle open, locking the temp on Windows so cleanup could not remove it. Closing OUR
    handle on every exit releases the OS lock regardless of where the parse failed."""
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size == 0 or not zipfile.is_zipfile(p):
            return False
        from openpyxl import load_workbook
        with open(p, "rb") as fh:                    # our handle -> closed on ANY exit (incl. raise)
            wb = load_workbook(fh, read_only=True)
            try:
                names = list(wb.sheetnames)
            finally:
                wb.close()
        if not names:
            return False
        return expect_sheet is None or expect_sheet in names
    except Exception:                                # noqa: BLE001 — open/parse failure => invalid
        return False


def _commit_one(tmp, final, validate):
    """Validate `tmp` then atomically replace it onto `final`. True iff committed.
    A missing/empty/invalid temp or a failed replace leaves `final` untouched, removes
    the temp, and returns False (never raises)."""
    tmp, final = Path(tmp), Path(final)
    if not validate(tmp):
        if not _silent_unlink(tmp):                  # P2-R04: verify the rejected temp is gone
            log.warning("artifact commit: rejected temp %s could not be removed (locked?)",
                        tmp.name)
        return False
    try:
        os.replace(tmp, final)
        return True
    except OSError as e:
        log.warning("artifact commit: could not finalize %s (%s: %s); prior kept",
                    final.name, type(e).__name__, e)
        _silent_unlink(tmp)
        return False


def _rewrite_paths(result, mapping):
    """Rewrite leaked temp paths in a ConsolidateResult's ``output_path``, ``message`` AND
    ``summary_lines`` back to their final names (so a ``.tmp-<token>`` name NEVER surfaces
    — including in an ERROR result's message, which compare_core builds from the path it
    was handed; P2-R02). The wrapper handed the producer temp paths; the user must see the
    real destinations. Applied to EVERY returned status (ok / error / cancelled)."""
    def sub(text):
        for tmp, final in mapping.items():
            text = text.replace(tmp, final)
        return text
    if getattr(result, "output_path", ""):
        result.output_path = sub(result.output_path)
    if getattr(result, "message", ""):
        result.message = sub(result.message)
    if getattr(result, "summary_lines", None):
        result.summary_lines = [sub(s) for s in result.summary_lines]
    return result


def commit_workbook(final, produce_fn, *, twin=False, expect_sheet=None, validate=None,
                    confirm_overwrite=None):
    """Run `produce_fn(temp_path)` — the EXISTING writer (compare_core via an adapter),
    pointed at a temp sibling of `final` — then validate and atomically commit it onto
    `final`. compare_core is never modified: it writes only to the temp path it is
    handed; this wrapper finalizes and rewrites the temp name out of the result (F9).
    Every returned result (ok / error / cancelled) is path-sanitized, so a ``.tmp-<token>``
    name never reaches the user (P2-R02).

    Validation OPENS the produced workbook (not a name check) and, with `expect_sheet`,
    requires that sheet — a malformed/corrupt output is rejected and the prior `final` is
    kept (P2-B05). `confirm_overwrite(path)->bool` is checked against the FINAL
    destination(s) BEFORE producing; a decline returns a ``cancelled`` result.

    `twin=True` (a ``mode="both"`` comparator): the producer writes BOTH the formulas
    workbook (the temp primary) and its ``(values)`` sibling. Per the multi-file policy
    (Q5) the **values** workbook is the single transactional artifact — committed FIRST;
    the **formulas** sibling is best-effort, committed second. If the formulas commit
    fails the result is rewritten to be TRUTHFUL: ``output_path`` points at the committed
    values workbook and the formulas line becomes a not-refreshed warning (P2-R03). A
    failure to commit the transactional (values, or the lone file) artifact leaves the
    prior `final` untouched and returns an error result."""
    final = Path(final)
    final.parent.mkdir(parents=True, exist_ok=True)
    validate = validate or (lambda p: _openable_xlsx(p, expect_sheet))
    confirm = confirm_overwrite or (lambda _p: True)
    final_twin = _values_twin(final) if twin else None
    for dest in ([final, final_twin] if twin else [final]):
        if dest.exists() and not confirm(dest):
            return ConsolidateResult(status="cancelled",
                                     message="Cancelled. Existing file kept.")
    token = _new_token()
    tmp = final.with_name(f"{final.stem}.tmp-{token}{final.suffix}")
    tmp_twin = _values_twin(tmp) if twin else None
    # Map BOTH the full temp path AND its basename -> the final equivalents: compare_core's
    # save-error message names only ``path.name`` (the basename), so a full-path-only rewrite
    # would leave the temp NAME in an error message (P2-R02). Full paths first so a basename
    # substring inside a full path is already gone by the time the basename rule runs.
    mapping = {str(tmp): str(final), tmp.name: final.name}
    if twin:
        mapping[str(tmp_twin)] = str(final_twin)
        mapping[tmp_twin.name] = final_twin.name
    try:
        result = produce_fn(tmp)
    except BaseException:
        _silent_unlink(tmp)
        _silent_unlink(tmp_twin)
        raise
    if getattr(result, "status", None) != "ok":
        _silent_unlink(tmp)               # producer cancelled/errored — nothing to commit
        _silent_unlink(tmp_twin)
        return _rewrite_paths(result, mapping)   # P2-R02: never leak the deleted temp name
    # The VALUES workbook is the single transactional artifact (twin), else the lone file.
    primary_tmp, primary_final = (tmp_twin, final_twin) if twin else (tmp, final)
    if not _commit_one(primary_tmp, primary_final, validate):
        _silent_unlink(tmp)
        _silent_unlink(tmp_twin)
        return ConsolidateResult(
            status="error",
            message=(f"Could not finalize {primary_final.name} — the produced workbook "
                     "was missing/invalid or the destination is open in Excel. The "
                     "previous file (if any) was left unchanged."))
    if twin and not _commit_one(tmp, final, validate):   # formulas sibling: best-effort
        log.warning("comparison: the live-formulas workbook for %s was not finalized; the "
                    "values workbook is committed", final.name)
        result = _rewrite_paths(result, mapping)
        # P2-R03: be TRUTHFUL — the formulas file was not written. Point output_path at the
        # committed values workbook and turn the formulas line into a not-refreshed warning
        # (any pre-existing formulas file at `final` is stale, not this comparison).
        result.output_path = str(final_twin)
        result.summary_lines = [
            ("Live-formulas file: NOT refreshed (best-effort write failed; the values "
             "workbook above is the canonical output)")
            if s.startswith("Live-formulas file:") else s
            for s in (result.summary_lines or [])]
        return result
    return _rewrite_paths(result, mapping)


# --------------------------------------------------------------------------- #
# input fingerprint (F5 / R1-R03)
# --------------------------------------------------------------------------- #
def _is_excluded(name):
    if name.startswith("~$"):                       # Excel lock file
        return True
    if ".tmp-" in name or name.endswith(".tmp"):    # our in-flight temp
        return True
    return any(name.endswith(s) for s in _FP_EXCLUDED_SUFFIXES)


def fingerprint(folder):
    """A stable identity string over the DATA files directly inside `folder`: a hash of
    the sorted ``(name, size, mtime_ns)`` tuples plus the file count. Catches a file
    added / removed / resized / re-timed — unlike a newest-mtime signal, which misses a
    DELETED (non-newest) file (F5). Excludes Excel lock files, our own sidecars
    (``.fingerprint.json`` / ``.outcome.json``), and in-flight temp / ``.staging``
    siblings; sub-directories are ignored (stores are flat per-route folders). An
    unreadable folder or file yields the ``_UNREADABLE`` sentinel so the caller rebuilds
    rather than silently matching. Never raises."""
    folder = Path(folder)
    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name)
    except OSError:
        return _UNREADABLE
    parts = []
    for e in entries:
        if _is_excluded(e.name):
            continue
        try:
            if not e.is_file():
                continue
            st = e.stat()
        except OSError:
            return _UNREADABLE
        parts.append(f"{e.name}\0{st.st_size}\0{st.st_mtime_ns}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"v{_FP_SCHEMA}:{len(parts)}:{digest}"


def _fp_sidecar(consolidated):
    return Path(str(consolidated) + _FP_SUFFIX)


# A fingerprint value that can NEVER equal a real one (`fingerprint()` returns
# ``v<schema>:<count>:<hexdigest>`` or ``_UNREADABLE``), so a sidecar carrying it always
# reads STALE — used to fail-safe an undeletable stale sidecar (P2-A02).
_FP_RACE_SENTINEL = "__race_invalidated__"


def _write_fp_sentinel(p):
    """Overwrite sidecar `p` with the non-matching race sentinel, so the workbook reads stale
    even when the old sidecar could not be removed (P2-A02). Best-effort; True iff written."""
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema_version": _FP_SCHEMA, "fingerprint": _FP_RACE_SENTINEL}, f)
        return True
    except OSError:
        return False


def _quarantine_workbook(consolidated):
    """LAST-resort A02 fail-safe: when a stale sidecar can be NEITHER removed nor overwritten,
    rename the freshly-replaced (race-suspect) workbook aside so the canonical path resolves
    MISSING — `consolidated_fresh` then reads stale (the workbook is absent) and a clean
    rebuild happens. Best-effort; True iff the workbook is no longer at its canonical path."""
    consolidated = Path(consolidated)
    q = consolidated.with_name(consolidated.name + ".race-stale")
    try:
        _silent_unlink(q)                            # clear a prior quarantine so rename won't clash
        consolidated.rename(q)
        return True
    except OSError:
        return not consolidated.exists()             # treat an already-gone workbook as quarantined


def write_consolidated_fingerprint(consolidated, store_dir, built_from=None):
    """Record `store_dir`'s input fingerprint beside `consolidated` after a successful
    build, so a later REUSE can tell whether the inputs changed (R1-R03). Atomic +
    best-effort: a write failure just means the next reuse rebuilds (fail-safe — a
    missing/unwritable sidecar reads as stale). Returns True iff the sidecar was written.

    `built_from` (P2-A02): the fingerprint captured BEFORE the build. If it differs from
    the current (post-build) fingerprint the inputs changed DURING the build, so the
    workbook may reflect a pre-change or mixed input set — do NOT publish a 'fresh'
    sidecar (the workbook reads stale and rebuilds next time). The GUI task lock already
    serializes writers; this guards an external mid-build mutation."""
    consolidated = Path(consolidated)
    fp = fingerprint(store_dir)
    if built_from is not None and built_from != fp:
        # P2-A02: the producer ALREADY replaced the workbook, so a leftover sidecar from a PRIOR
        # build could still certify it fresh (esp. if the inputs reverted to the old identity).
        # REMOVE the stale sidecar; if it can't be removed (locked), OVERWRITE it with a
        # guaranteed-non-matching sentinel so consolidated_fresh still reads stale. Log the
        # ACTUAL outcome (P2-A02) — never leave a freshly-replaced workbook reading fresh.
        # Fail-safe ladder (each rung only reached if the prior failed): remove the stale
        # sidecar -> overwrite it with a non-matching sentinel -> (P2-A02 dual-failure)
        # quarantine the replaced workbook so the canonical path resolves MISSING -> log
        # critically. The replaced workbook must NEVER stay eligible to read fresh.
        sc = _fp_sidecar(consolidated)
        if _silent_unlink(sc):
            log.warning("artifact fingerprint for %s NOT recorded — inputs changed during the "
                        "build; stale sidecar removed so the workbook rebuilds next reuse",
                        consolidated.name)
        elif _write_fp_sentinel(sc):
            log.warning("artifact fingerprint for %s NOT recorded — inputs changed mid-build and "
                        "the stale sidecar could not be removed; wrote a non-matching sentinel so "
                        "the workbook rebuilds next reuse", consolidated.name)
        elif _quarantine_workbook(consolidated):
            log.warning("artifact fingerprint for %s NOT recorded — the stale sidecar could be "
                        "neither removed nor overwritten; quarantined the replaced workbook so it "
                        "rebuilds next reuse", consolidated.name)
        else:
            log.critical("artifact fingerprint for %s NOT recorded and neither its stale sidecar "
                         "nor the replaced workbook could be invalidated — it may read fresh; "
                         "re-run", consolidated.name)
        return False
    p = _fp_sidecar(consolidated)
    tmp = p.with_name(p.name + f".tmp-{_new_token()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"schema_version": _FP_SCHEMA, "fingerprint": fp}, f)
        os.replace(tmp, p)
        return True
    except OSError as e:
        log.warning("artifact fingerprint for %s not written (%s: %s); next reuse rebuilds",
                    consolidated.name, type(e).__name__, e)
        _silent_unlink(tmp)
        return False


def _read_fp_sidecar(consolidated):
    """The recorded fingerprint string, or None when the sidecar is absent / unreadable
    / corrupt / a different schema. Never raises."""
    try:
        with open(_fp_sidecar(consolidated), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None
    if (not isinstance(meta, dict) or meta.get("schema_version") != _FP_SCHEMA
            or not isinstance(meta.get("fingerprint"), str)):
        return None
    return meta["fingerprint"]


def consolidated_fresh(consolidated, store_dir):
    """True iff `consolidated` exists AND its recorded input fingerprint matches
    `store_dir`'s CURRENT fingerprint. A missing workbook, a missing/corrupt/old
    sidecar, an unreadable store, or a fingerprint MISMATCH ⇒ False (rebuild). This is
    identity-based freshness (F5): a DELETED route changes the fingerprint even though
    the newest-mtime is untouched. A legacy workbook with no sidecar reads stale ONCE,
    rebuilds, and records the sidecar (the one-time migration). Never raises."""
    if not Path(consolidated).exists():
        return False
    recorded = _read_fp_sidecar(consolidated)
    if recorded is None:
        return False
    current = fingerprint(store_dir)
    if current == _UNREADABLE:
        return False
    return recorded == current


# --------------------------------------------------------------------------- #
# journaled store promotion + startup recovery (F2)
# --------------------------------------------------------------------------- #
_PROMOTE_DIRNAME = ".promote"
_BAK_INFIX = ".bak-"
_STAGING_SUFFIX = ".staging"


def _journal_dir(live):
    """The promotion journal dir, in the destination PARENT — never inside `live`
    (which is itself renamed), per §C.2."""
    return Path(live).parent / _PROMOTE_DIRNAME


def _rmtree(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def _rmtree_gone(path):
    """rmtree `path` (best-effort) and report whether it is GONE afterwards — True when the
    path no longer exists (removed, or never there), False when it survives (locked). Lets
    recovery observe cleanup success so it can retain the journal on a failed cleanup (P2-R05)."""
    _rmtree(path)
    try:
        return not Path(path).exists()
    except OSError:
        return False


def _finalize_journal(journal, *residue):
    """Remove `journal` ONLY after EVERY named residue dir is confirmed GONE (P2-R05) — so a
    locked backup/staging RETAINS the journal and the next launch's recovery retries the
    cleanup. Used by BOTH promote_store's completion/restore branches and recovery. Returns
    True iff the journal was removed."""
    if all(_rmtree_gone(r) for r in residue):
        _silent_unlink(journal)
        return True
    log.warning("promotion: residue cleanup incomplete; journal %s RETAINED for next-launch "
                "retry", Path(journal).name)
    return False


def _is_report_artifact(name):
    """A real per-route report file (P2-R01): a non-excluded regular name ending in a
    report suffix (.xlsx / .pdf). A `.txt` or other foreign file does NOT qualify."""
    return (not _is_excluded(name)) and name.lower().endswith(_REPORT_SUFFIXES)


def _staging_has_report_file(staged):
    """A staging dir is committable only if it exists and holds at least one REPORT artifact
    (.xlsx/.pdf) — not merely any regular file (P2-R01: a staging containing only a nested
    directory, only lock/temp/sidecar files, or only a foreign `.txt` must never replace a
    good live). Excludes Excel locks, our temp/`.staging`/sidecar names, and sub-directories."""
    try:
        staged = Path(staged)
        if not staged.is_dir():
            return False
        for e in staged.iterdir():
            try:
                if e.is_file() and _is_report_artifact(e.name):
                    return True
            except OSError:
                continue
        return False
    except OSError:
        return False


def is_usable_store(d):
    """True iff `d` is a directory that genuinely holds a report artifact — a real live
    store, not an empty placeholder or a foreign directory. Recovery treats ONLY this as
    proof that the canonical copy exists (P2-B02: a bare `exists()` is not proof); the
    worker uses it too, so a failed-promotion artifact is truthful (P2-A04)."""
    return _staging_has_report_file(d)


def _dir_is_disposable_placeholder(d):
    """True iff `d` is a directory whose every entry is disposable (an excluded temp / lock /
    sidecar name) — safe to remove when restoring a real backup over it. A directory with
    ANY sub-directory or non-excluded (incl. foreign) file is NOT disposable: that is a
    genuine conflict the recovery must NOT silently destroy (P2-B02)."""
    try:
        d = Path(d)
        if not d.is_dir():
            return False
        for e in d.iterdir():
            if e.is_dir() or not _is_excluded(e.name):
                return False
        return True
    except OSError:
        return False


def promote_store(live, staged):
    """Replace `live` with the freshly-built `staged` folder, JOURNALED so a crash between
    the renames is recoverable (F2: never zero copies, never a truncated last-good). Steps
    (§C.2): validate staging holds a report artifact -> write the journal in the destination
    parent -> rename(live -> live.bak-<token>) -> rename(staged -> live) -> delete the
    journal -> drop the backup. A failure mid-swap restores `live` from the backup and
    discards `staged`; a blocked restore RETAINS the journal + backup for next-launch
    recovery. The FIRST promotion (no prior `live`) is journaled too, so a failed rename
    retains the staging + journal rather than deleting the only completed copy (P2-B06).
    Returns True iff `live` now holds the promoted content. Never raises."""
    live, staged = Path(live), Path(staged)
    if not _staging_has_report_file(staged):
        log.warning("store promotion for %s: staging missing/empty/no-report-file — kept "
                    "last-good", live.name)
        _rmtree(staged)
        return False

    had_prior = live.exists()
    token = _new_token()
    backup = live.with_name(f"{live.name}{_BAK_INFIX}{token}")
    jdir = _journal_dir(live)
    journal = jdir / f"{token}.json"
    # P2-B07: a DURABLE, monotonic transaction generation — strictly greater than every existing
    # same-target journal (derived from the on-disk journals, NOT wall-clock), so recovery's
    # newest-`gen`-first ordering cannot be inverted by a system-clock regression across restarts.
    gen = _next_generation(jdir, live.name)
    try:
        jdir.mkdir(parents=True, exist_ok=True)
        with open(journal, "w", encoding="utf-8") as f:
            json.dump({"target": live.name, "backup": backup.name,
                       "staging": staged.name, "token": token, "gen": gen}, f)
    except OSError as e:
        # No journal -> no transactional guarantee. With a prior live, keep last-good and
        # discard the unlanded refresh. With NO prior (first promotion), attempt the rename
        # directly (nothing to lose) and RETAIN the staging on failure so a re-export
        # recovers it — never delete the only completed copy (P2-B06).
        log.warning("store promotion for %s: could not write journal (%s: %s)",
                    live.name, type(e).__name__, e)
        _silent_unlink(journal)
        if had_prior:
            _rmtree(staged)
            return False
        try:
            staged.rename(live)
            return True
        except OSError:
            log.warning("first promotion for %s: rename failed and no journal — staging "
                        "RETAINED for re-export", live.name)
            return False

    if not had_prior:
        # First promotion: no backup to make. On a rename failure RETAIN the staging + the
        # journal so recover_promotions promotes the surviving staging next launch — the
        # only completed copy is never deleted (P2-B06).
        try:
            staged.rename(live)
            _silent_unlink(journal)                  # no residue (staging consumed, no backup)
            return True
        except OSError as e:
            log.warning("first promotion for %s failed (%s: %s); staging + journal RETAINED "
                        "for next-launch recovery", live.name, type(e).__name__, e)
            return False

    try:
        live.rename(backup)                          # live -> backup
    except OSError as e:
        log.warning("store promotion for %s: could not move live aside (%s: %s) — kept last-good",
                    live.name, type(e).__name__, e)
        _silent_unlink(journal)
        _rmtree(staged)
        return False
    try:
        staged.rename(live)                          # staging -> live
    except OSError as e:
        # Death window: live is now `backup`. Restore it so we never leave zero copies.
        log.warning("store promotion for %s: could not move staging into place (%s: %s) — "
                    "restoring last-good", live.name, type(e).__name__, e)
        try:
            backup.rename(live)                      # restore: live present again
            # P2-R05: drop the journal only once the residual staging is confirmed gone — a
            # locked staging RETAINS the journal so recovery retries the cleanup.
            _finalize_journal(journal, staged)
        except OSError:
            # P2-B02: restore FAILED — live missing, backup present. RETAIN the journal +
            # backup (and staging) so the next launch's recover_promotions can restore.
            # Deleting the journal here would strand the store with zero canonical copies.
            log.error("store promotion for %s: restore from backup FAILED; journal + backup "
                      "RETAINED for next-launch recovery", live.name)
        return False
    # Commit point passed. P2-R05: drop the journal only once the backup is confirmed gone —
    # a locked backup RETAINS the journal so the next launch's recovery removes the residue.
    _finalize_journal(journal, backup)
    return True


def _trusted_journal_names(j):
    """The (target, backup, staging) basenames from a journal record IFF it is in the
    expected promotion shape — else None (P2-B04: a malformed/planted journal must never
    let recovery touch a path outside its own store). Each name must be a single basename
    (no separators / ``..`` / absolute parts) and ``backup``/``staging`` must be exactly
    ``<target>.bak-<token>`` / ``<target>.staging``."""
    if not isinstance(j, dict):
        return None
    target, backup, staging, token = (j.get("target"), j.get("backup"),
                                      j.get("staging"), j.get("token"))
    if not all(isinstance(s, str) and s for s in (target, backup, staging, token)):
        return None
    for n in (target, backup, staging):
        if n in (".", "..") or n != Path(n).name:    # reject separators / .. / absolute
            return None
    if backup != f"{target}{_BAK_INFIX}{token}" or staging != f"{target}{_STAGING_SUFFIX}":
        return None
    return target, backup, staging


def _journal_gen(journal):
    """The transaction GENERATION recorded in a journal (P2-B07), or 0 when absent / unreadable /
    non-int. Higher = newer; recovery processes a target's journals highest-`gen` first."""
    try:
        with open(journal, encoding="utf-8") as f:
            g = json.load(f).get("gen")
        return g if isinstance(g, int) and not isinstance(g, bool) else 0
    except (OSError, ValueError):
        return 0


def _next_generation(jdir, target_name):
    """The generation to stamp on a NEW promotion of `target_name`: strictly greater than EVERY
    valid existing same-target journal's generation (P2-B07). DURABLE + monotonic — derived from
    the on-disk journals under the single-writer promotion boundary, NOT wall-clock, so it cannot
    regress across application restarts or system-clock corrections (an older retained cleanup
    journal can never out-rank a later promotion). A first promotion (no prior same-target
    journal) is generation 1."""
    highest = 0
    try:
        journals = [p for p in jdir.iterdir() if p.suffix == ".json"]
    except OSError:
        return 1                                     # no .promote dir yet -> first generation
    for journal in journals:
        try:
            with open(journal, encoding="utf-8") as f:
                j = json.load(f)
        except (OSError, ValueError):
            continue                                 # junk -> recovery drops it; ignore for gen
        names = _trusted_journal_names(j)
        if names is None or names[0] != target_name:
            continue                                 # malformed / a DIFFERENT target — irrelevant
        g = j.get("gen")
        if isinstance(g, int) and not isinstance(g, bool) and g > highest:
            highest = g
    return highest + 1


def _recover_one(jdir, journal, is_owned):
    """Act on ONE promotion journal in an already-OWNERSHIP-CONFIRMED location (the caller
    `recover_promotions` proves `is_owned(store_root, None)` for `jdir.parent` BEFORE this is
    reached, so reading/deleting a journal here is always inside an app-owned store — P2-B04).
    The journal is dropped ONLY after a canonical copy is PROVEN usable — a directory holding
    a report artifact, NOT a bare ``exists()`` (P2-B02) — AND every journal-owned residue is
    confirmed GONE (P2-R05). When `live` is absent / an invalid placeholder, a valid backup
    (then a valid staging) is restored; an empty/disposable placeholder is displaced first,
    but FOREIGN content is a conflict that retains everything; a blocked restore likewise."""
    parent = jdir.parent
    try:
        with open(journal, encoding="utf-8") as f:
            j = json.load(f)
    except (OSError, ValueError):
        _silent_unlink(journal)                      # unreadable journal in OUR store — drop the junk
        return
    names = _trusted_journal_names(j)
    if names is None:
        log.warning("promotion recovery: dropping a shape-invalid journal %s in an owned store "
                    "(no path touched)", journal.name)
        _silent_unlink(journal)
        return
    if not is_owned(parent, names[0]):               # P2-B04: the TARGET must also be a known report
        log.warning("promotion recovery: ignoring journal %s — target %r is not a known report "
                    "(no path touched)", journal.name, names[0])
        return
    target, backup, staging = (parent / n for n in names)

    if is_usable_store(target):                      # canonical live genuinely present (has a report)
        _finalize_journal(journal, backup, staging)  # P2-R05: drop journal only once residue is gone
        return
    # `target` is absent OR an invalid placeholder. Restore from a valid backup, else a
    # valid surviving staging (the first-promotion case). Validate the source IS a real
    # store so we never restore garbage over nothing.
    for src_name, src in (("backup", backup), ("staging", staging)):
        if not is_usable_store(src):
            continue
        if target.exists() and not _dir_is_disposable_placeholder(target):
            log.error("promotion recovery: %s exists with foreign content — cannot restore "
                      "from %s; journal + copies RETAINED for manual resolution",
                      target.name, src_name)
            return                                   # genuine conflict — touch nothing
        if target.exists():
            _rmtree(target)                          # displace the empty / disposable placeholder
        try:
            src.rename(target)
            log.info("promotion recovery: restored %s from %s", target.name, src_name)
        except OSError as e:                         # blocked — RETAIN journal + copies for retry
            log.error("promotion recovery: could not restore %s from %s (%s: %s); retained",
                      target.name, src_name, type(e).__name__, e)
            return
        _finalize_journal(journal, backup, staging)  # the consumed source is gone; clean the other
        return
    # No usable backup or staging. Prefer RETAINING any residue (harmless, and a human can
    # inspect it) over deleting an unvalidated copy; drop the journal only when nothing is left.
    if backup.exists() or staging.exists():
        log.error("promotion recovery: no usable copy for %s; residue RETAINED for diagnosis",
                  target.name)
        return
    _silent_unlink(journal)                          # nothing recoverable — drop the journal


def recover_promotions(root, is_owned):
    """Startup recovery sweep (F2): repair any interrupted store promotion under `root`.

    `is_owned(store_root: Path, target_name | None) -> bool` is the caller-supplied OWNERSHIP
    context (P2-B04). Ownership is established from the COMPLETE LOCATION BEFORE any journal is
    read or deleted: for each discovered ``<store_root>/.promote`` the LOCATION gate
    `is_owned(store_root, None)` must pass — the updater requires `store_root` to be a DIRECT
    child of the exact recovery root AND a known ``<src>-<env>`` name — else the whole
    ``.promote`` (including any malformed journals in it) is left UNTOUCHED. So a nested,
    valid-NAME-but-wrong-LOCATION tree (e.g. ``<root>/UnrelatedProject/ssor-prod/.promote``)
    is never acted on. Inside an owned location, each shape-valid journal's TARGET is then
    validated via `is_owned(store_root, target)`.

    Journals are processed NEWEST GENERATION FIRST (by the durable monotonic ``gen``; P2-B07), so
    if two journals name the same target — an older retained-after-locked-cleanup one plus a newer
    interrupted one — the newer generation restores/keeps the true last-good first and the older
    journal can only become residue-cleanup against an already-canonical live; an older generation
    can never roll back over or delete a newer one, regardless of filesystem order OR a wall-clock
    regression (``gen`` is derived from existing journals, not the clock). There is NO journal-free
    orphan sweep. Idempotent + best-effort; never raises."""
    root = Path(root)
    try:
        promote_dirs = list(root.rglob(_PROMOTE_DIRNAME))
    except OSError:
        return
    for jdir in promote_dirs:
        if not jdir.is_dir():
            continue
        if not is_owned(jdir.parent, None):          # P2-B04: LOCATION gate BEFORE any read/delete
            log.warning("promotion recovery: skipping a non-app-owned .promote at %s (no journal "
                        "read or touched)", jdir.parent)
            continue
        try:
            journals = [p for p in jdir.iterdir() if p.suffix == ".json"]
        except OSError:
            continue
        # P2-B07: highest generation first (stable tie-break on name) — order-independent of the
        # filesystem listing AND of wall-clock, so an older same-target journal never restores
        # before the newer one even after a system-clock regression.
        for journal in sorted(journals, key=lambda p: (_journal_gen(p), p.name), reverse=True):
            _recover_one(jdir, journal, is_owned)
        try:                                         # drop the .promote dir if now empty
            jdir.rmdir()
        except OSError:
            pass

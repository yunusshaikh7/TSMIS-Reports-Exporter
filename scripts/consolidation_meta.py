"""Producer-owned outcome SIDECAR for persistent consolidated workbooks (P1-R01).

A consolidated workbook is written by several paths — the matrix store consolidation,
``ExportWorker._auto_consolidate``, the GUI/console Consolidate tab
(``ConsolidateWorker``), and the TSN-library builders — and then REUSED across
comparisons (rebuilt only when a per-route source is newer). A PARTIAL consolidation
(inputs left out) must stay flagged on every later reuse, but a reuse has no fresh
``ConsolidateResult`` to read. So every persistent writer records the producer
completion in a tiny JSON sidecar beside the workbook through THIS module — the single
write/read boundary — and reuse recovers it here, so no writer can bypass it.

Robustness:
  * the sidecar is SCHEMA-VERSIONED and written ATOMICALLY (tmp + ``os.replace``) so a
    crash mid-write can't leave a truncated file as the live sidecar;
  * read VALIDATES schema/vocabulary/types and DEGRADES SAFELY — a present-but-unusable
    sidecar reads as ``partial`` (conservative: a current-version artifact whose outcome
    can't be trusted must never render as a green ``complete``), while a workbook with NO
    sidecar reads as ``None`` (deliberate legacy back-compat -> the caller defaults to
    complete);
  * an mtime mismatch (the workbook was rebuilt by something that didn't update the
    sidecar) reads as ``None`` — treat a stale flag as absent, never as a false partial;
  * ``write_outcome`` returns a bool so a publication failure is OBSERVABLE to every
    caller (they must not announce a plain success for a non-complete artifact whose flag
    could not be recorded); and even when atomic publish, the fallback marker, AND the
    workbook deletion ALL fail, the already-written ``.tmp`` is RETAINED as a last-resort
    conservative sentinel (``read_completion`` falls back to it) so reuse never reads a
    sidecar-less non-complete workbook as green.
"""
import json
import logging
import os
from pathlib import Path

import outcome

log = logging.getLogger("tsmis.consolidation_meta")

SCHEMA_VERSION = 1
_MTIME_TOL_S = 1.0                 # THE float-mtime equality tolerance (matrix imports this)


def meta_path(consolidated):
    """The sidecar path for a consolidated workbook: ``<workbook>.outcome.json``."""
    return Path(str(consolidated) + ".outcome.json")


def _safe_mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


_ABSENT = object()                 # _read_sidecar: the file does not exist


def _read_sidecar(path, consolidated):
    """Read+VALIDATE one sidecar/sentinel file the SAME way (schema / vocabulary / type /
    mtime vs the workbook). Returns:
      * ``_ABSENT``          — the file does not exist;
      * a completion string  — valid AND mtime-current (describes THIS workbook);
      * ``outcome.PARTIAL``  — present but UNUSABLE (unreadable / corrupt / malformed):
                               conservative, a current-version artifact whose outcome can't
                               be trusted must never read green;
      * ``None``             — valid but STALE (mtime mismatch): the workbook was rebuilt /
                               the sentinel is demonstrably stale, so ignore it.
    Never raises."""
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
    except FileNotFoundError:
        return _ABSENT
    except OSError:                          # present but unreadable (locked / not a file)
        try:
            return outcome.PARTIAL if Path(path).exists() else _ABSENT
        except OSError:
            return outcome.PARTIAL
    except ValueError:                       # corrupt JSON
        return outcome.PARTIAL
    if (not isinstance(meta, dict)
            or meta.get("schema_version") != SCHEMA_VERSION
            or meta.get("completion") not in outcome.COMPLETIONS
            or isinstance(meta.get("built_at_mtime"), bool)
            or not isinstance(meta.get("built_at_mtime"), (int, float))):
        return outcome.PARTIAL               # malformed -> conservative
    cur_m = _safe_mtime(consolidated)
    if cur_m is None or abs(float(meta["built_at_mtime"]) - cur_m) > _MTIME_TOL_S:
        return None                          # stale (rebuilt / demonstrably stale) -> ignore
    return meta["completion"]


def _silent_unlink(path):
    """Best-effort unlink; True iff the file is gone afterwards."""
    try:
        Path(path).unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _mark_untrusted(p, consolidated):
    """A DURABLE conservative state when atomic publication failed AND the derived workbook
    could not be removed: a direct (non-atomic — we are already in the degraded path)
    ``partial`` sidecar carrying the workbook's current mtime, so a later reuse reads
    ``partial`` instead of a false green. One rung of the fallback ladder — if this fails,
    write_outcome retains the valid ``.tmp`` sentinel or quarantines the workbook.
    Best-effort; True iff the marker was written."""
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema_version": SCHEMA_VERSION, "completion": outcome.PARTIAL,
                       "built_at_mtime": _safe_mtime(consolidated), "untrusted": True}, f)
        return True
    except OSError as e:
        log.warning("consolidation outcome marker for %s could not be written (%s: %s); "
                    "falling back to the retained sentinel / quarantine",
                    Path(consolidated).name, type(e).__name__, e)
        return False


def _quarantine(consolidated):
    """LAST resort when a NON-complete workbook's outcome could not be recorded by ANY
    means (no published sidecar, no marker, no usable ``.tmp`` sentinel) AND the workbook
    could not be removed: RENAME it aside so the canonical path resolves as MISSING (the
    resolver rebuilds it) and it can never read as a legacy-complete cell. The data is
    preserved at the quarantine name for diagnosis. Best-effort — a truly-locked workbook
    may refuse rename too (then the residual window is logged critically by the caller)."""
    consolidated = Path(consolidated)
    q = consolidated.with_name(consolidated.name + ".unverified")
    try:
        _silent_unlink(q)                    # clear a prior quarantine so rename won't clash
        consolidated.rename(q)
        return True
    except OSError as e:
        log.error("could not quarantine %s (%s: %s)", consolidated.name, type(e).__name__, e)
        return False


def write_outcome(consolidated, result, extra=None):
    """Record `result`'s producer completion beside its workbook, ATOMICALLY — the
    boundary every persistent-consolidated writer calls right after a successful write.

    Returns True when the outcome is safely represented on disk: a trustworthy sidecar
    was published, OR the artifact is COMPLETE (an absent sidecar correctly reads
    complete), OR there was nothing to persist. Returns **False** only when a
    NON-complete (partial) artifact's flag could not be published — the caller MUST NOT
    announce a plain success, because the partial workbook may otherwise look complete.
    On that failure write_outcome still does everything it can to prevent a later false
    green: it cleans the temp file, leaves a durable conservative `partial` marker, and
    removes the derived workbook so it rebuilds. No-op (True) for a non-ok result or a
    falsy path."""
    if not consolidated or getattr(result, "status", None) != "ok":
        return True
    consolidated = Path(consolidated)
    comp = outcome.consolidate_completion_of(result)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "completion": comp,
        "skipped_inputs": int(getattr(result, "skipped_inputs", 0) or 0),
        "failed_inputs": int(getattr(result, "failed_inputs", 0) or 0),
        "built_at_mtime": _safe_mtime(consolidated),
    }
    if extra:
        payload.update(extra)          # additive producer metadata (e.g. the TSN
                                       # normalization version, D2); readers are
                                       # tolerant, so unknown keys are harmless

    p = meta_path(consolidated)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, p)                       # atomic publish — never a half file
        return True
    except OSError as e:
        log.warning("could not publish consolidation outcome for %s: %s: %s",
                    consolidated.name, type(e).__name__, e)
        if comp == outcome.COMPLETE:
            _silent_unlink(tmp)                  # harmless; absent sidecar reads complete
            return True
        # A non-complete artifact must never later read as a green complete. Fallback
        # ladder (each rung only reached if the prior one failed):
        #   1. remove the workbook -> clean rebuild;
        #   2. write a direct 'untrusted' final marker;
        #   3. retain a CONSERVATIVE .tmp sentinel — but ONLY one that itself reads
        #      `partial` (a valid+current partial, or a present-but-corrupt -> partial).
        #      A current `.tmp` that says `complete` (unrelated debris) must NOT certify
        #      THIS failed partial write, so it is rejected and the ladder continues;
        #   4. quarantine the workbook (rename) so resolvers can't select it — covers both
        #      the write-stage branch (no .tmp) AND an incompatible (complete/stale) .tmp;
        #   5. (all failed) log critically — the irreducible all-locked window.
        # read_completion validates the .tmp the same as the final sidecar, so a stale or
        # absent sentinel never forces a false partial AND never leaves a false green.
        if _silent_unlink(consolidated):
            _silent_unlink(tmp)
            return False
        if _mark_untrusted(p, consolidated):
            _silent_unlink(tmp)
            return False
        if _read_sidecar(tmp, consolidated) == outcome.PARTIAL:
            return False                         # only a CONSERVATIVE (partial) .tmp protects it
        if _quarantine(consolidated):
            return False
        log.critical("consolidation outcome for %s: could not record, remove, mark, retain a "
                     "sentinel, or quarantine the incomplete workbook; a later reuse could "
                     "read it as complete", consolidated.name)
        return False


def read_extra(consolidated, key, default=None):
    """A single additive payload field from the workbook's sidecar, tolerantly:
    absent sidecar / unreadable / corrupt / missing key -> `default`. Used for
    producer metadata like the TSN normalization version (D2) — the FAIL-SAFE
    direction is the default (an unstampable read counts as stale)."""
    p = meta_path(Path(consolidated))
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:                    # silent-ok: absent sidecar is the normal pre-stamp state
        return default
    except ValueError as e:
        log.info("sidecar for %s unreadable for %r (%s: %s); using the default",
                 Path(consolidated).name, key, type(e).__name__, e)
        return default
    return data.get(key, default) if isinstance(data, dict) else default


def read_completion(consolidated):
    """The persisted producer completion of a consolidated workbook for REUSE. Never
    raises. Returns:
      * ``None``  — no sidecar AND no sentinel (a legacy workbook), OR the workbook was
        rebuilt since the sidecar was written / a demonstrably stale sentinel (mtime
        mismatch); the caller defaults to ``complete``;
      * a completion string — the recorded, validated, current outcome;
      * ``partial`` (conservative) — a sidecar/sentinel EXISTS but is unusable (unreadable,
        unparseable, wrong schema / vocabulary / type): a current-version artifact whose
        outcome can't be trusted must never read as a green ``complete``.

    Final and ``.tmp`` are reconciled CONSERVATIVELY: a retained ``.tmp`` sentinel that
    reads ``partial`` is the most-recent, not-yet-promoted record of a FAILED partial
    publication, so it **dominates** the final sidecar — even a final that says ``complete``
    but is only stale-yet-within-tolerance (a rapid overwrite / coarse-resolution mtime).
    Otherwise the final wins (its validated value / None), then the ``.tmp``'s value. Both
    are validated the same way (so a stale sentinel is ignored, a corrupt one stays
    conservative)."""
    p = meta_path(consolidated)
    final = _read_sidecar(p, consolidated)
    if final == outcome.PARTIAL:
        return outcome.PARTIAL                   # already conservative — no need to consult the .tmp
    tmp = _read_sidecar(p.with_name(p.name + ".tmp"), consolidated)
    if tmp == outcome.PARTIAL:
        return outcome.PARTIAL                   # a retained partial sentinel DOMINATES the final
    if final is not _ABSENT:
        return final                             # completion str (complete/…) | None (stale)
    return None if tmp is _ABSENT else tmp

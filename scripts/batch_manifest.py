"""Persistent job manifest for the Export-Everything batch (B3).

A batch can span many report types x environments and take a long time, so its
progress is recorded on disk and survives an app restart (pause/resume across
days). The manifest lives under DATA_ROOT — NOT output/ — so "Delete all reports"
(which only clears output/ and input/) never removes it. Writes are atomic
(temp file + os.replace) so a crash mid-write can't leave a corrupt manifest.

Console-free and dependency-light (stdlib json only): importing it never touches
a browser or openpyxl, so the GUI can read it at startup to offer a resume.
"""
import json
import logging
import os
from pathlib import Path

from paths import DATA_ROOT

log = logging.getLogger("tsmis.batch")

MANIFEST_PATH = DATA_ROOT / "batch_job.json"
_VERSION = 2                       # v2 persists export-op KEYS (v1 was int indices)
_SUPPORTED_VERSIONS = (1, 2)       # v1 still LOADS (migrated to v2 in memory)

# v0.17 (manifest v1) stored INTEGER indices into EXPORT_REPORTS. This is the
# FROZEN map from those indices to the stable export-op keys — never a live view
# of EXPORT_REPORTS (which can re-order). A v1 manifest must always resolve to the
# reports the user actually picked under v0.17, regardless of any later re-order.
#
# Indices 0–6 are the original v0.17.1 export order and MUST stay fixed (positions
# 0–6 preserved, CR002-RM4). Index 7 (`intersection_detail_pdf`) is APPEND-ONLY: the
# v0.17.2–v0.17.8 line shipped it as the 8th export (the last int-index-format
# release), so a v0.17.8 user's v1 manifest can carry index 7 — and it must migrate
# to the right key, not be poisoned. Never re-order or insert; only append.
_V017_EXPORT_ORDER = (
    "ramp_summary", "ramp_detail", "highway_sequence", "highway_log",
    "highway_log_pdf", "intersection_summary", "intersection_detail",
    "intersection_detail_pdf",
    # v0.18.1 reserved groundwork (DISABLED) — appended, never inserted/reordered, to
    # keep this == reports.EXPORT_KEYS. A v1 manifest could never carry these indices
    # (they postdate the int-index era); if one somehow did, the loader rejects the
    # disabled key rather than poisoning it.
    "highway_detail", "highway_summary",
)

# Poison sentinel for a structurally-invalid saved entry. It is never a real export
# key, so the all-or-nothing resolver (`reports.resolve_export_keys`) rejects it and
# the batch aborts — rather than coercing or silently dropping the bad entry (§C.5).
_INVALID_KEY = "__invalid_selection__"


def _migrate_v1_reports(raw):
    """v1 integer indices -> export-op keys via the frozen v0.17 order, **1:1 and
    length-preserving**. A non-integer (bool/float/str — never coerced) or an
    out-of-range entry maps to the poison `_INVALID_KEY`; duplicates are kept. So an
    invalid or repeated legacy index rejects the whole saved selection downstream
    instead of silently running a narrower batch (§C.5)."""
    keys = []
    for i in raw if isinstance(raw, list) else []:
        if isinstance(i, bool) or not isinstance(i, int):
            log.warning("v1 manifest report entry %r is not an integer index — rejected", i)
            keys.append(_INVALID_KEY)
        elif 0 <= i < len(_V017_EXPORT_ORDER):
            keys.append(_V017_EXPORT_ORDER[i])
        else:
            log.warning("v1 manifest report index %r out of range — rejected", i)
            keys.append(_INVALID_KEY)
    return keys


def _normalize_reports(data):
    """The manifest's report selection as export-op KEYS, **1:1 with the saved list**
    (length-preserving, duplicates kept). v1 int indices migrate via the frozen
    order; a v2 entry that isn't a non-empty string maps to the poison `_INVALID_KEY`.
    Nothing is coerced, de-duplicated, or dropped here — resolution is all-or-nothing
    (§C.5), so any invalid/duplicate/unknown entry rejects the whole saved selection
    (the batch aborts, the manifest is preserved, no environment is marked done)."""
    raw = data.get("reports", [])
    if data.get("version") == 1:
        return _migrate_v1_reports(raw)
    return [k if isinstance(k, str) and k else _INVALID_KEY
            for k in (raw if isinstance(raw, list) else [])]


def build(report_keys, combos, fast, workers, auto_consolidate, dest="", created=""):
    """A fresh manifest (v2): which reports (by stable export-op KEY), which
    (src, env) combos (all 'pending'), the destination folder, and the run
    options. `combos` is an iterable of (src, env) pairs; `dest` is the
    always-current folder to refresh into. Persisting KEYS — not list positions —
    means a registry re-order never resumes the wrong report (F7 / §C.5)."""
    return {
        "version": _VERSION,
        # Canonical export-op KEYS, already validated + resolved by the caller
        # (gui_api.start_batch_export). NOT coerced here — a malformed caller value
        # would be caught by the all-or-nothing resolver, never silently stringified.
        "reports": list(report_keys),
        "fast": bool(fast),
        "workers": int(workers),
        "auto_consolidate": bool(auto_consolidate),
        "dest": dest or "",
        "created": created,
        "steps": [{"src": s, "env": e, "status": "pending"} for (s, e) in combos],
    }


def save(manifest, path=MANIFEST_PATH):
    """Atomically write the manifest (temp file + os.replace on the same dir)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load(path=MANIFEST_PATH):
    """The saved manifest, or None when absent / unreadable / wrong shape (so a
    corrupt file degrades to 'no batch to resume' rather than crashing)."""
    path = Path(path)
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.warning("batch manifest unreadable (%s) — ignoring", type(e).__name__)
        return None
    if (not isinstance(data, dict)
            or data.get("version") not in _SUPPORTED_VERSIONS
            or not isinstance(data.get("steps"), list)):
        log.warning("batch manifest shape/version unexpected — ignoring")
        return None
    # Normalize the report selection to v2 export-op KEYS in memory, migrating a
    # v1 int-index list through the FROZEN v0.17 order. The on-disk file is
    # rewritten to v2 on the next save (mark_done), so a legacy batch resumes
    # correctly and is upgraded forward exactly once (F7 / §C.5).
    data["reports"] = _normalize_reports(data)
    data["version"] = _VERSION
    return data


def clear(path=MANIFEST_PATH):
    """Remove the manifest (best-effort) — a finished or discarded batch."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:  # silent-ok: best-effort cleanup; a leftover manifest just re-offers resume
        pass


def pending(manifest):
    """The (src, env) combos not yet done, in manifest order."""
    return [(s["src"], s["env"]) for s in manifest.get("steps", [])
            if s.get("status") != "done"]


def mark_done(manifest, src, env, path=MANIFEST_PATH):
    """Mark one combo done and persist immediately, so a crash right after an
    environment finishes resumes at the NEXT environment, not this one."""
    for s in manifest.get("steps", []):
        if s.get("src") == src and s.get("env") == env:
            s["status"] = "done"
    save(manifest, path)


def is_complete(manifest):
    steps = manifest.get("steps", [])
    return bool(steps) and all(s.get("status") == "done" for s in steps)

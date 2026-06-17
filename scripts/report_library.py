"""Report freshness for the Export-Everything "always-current" destination (B3).

Scans the destination for each report type's per-route files and reports the age
of the newest one, so the GUI can show which reports are current and which are
stale (and let the user refresh just the one that's behind). Dependency-light
(stdlib only): the caller passes the (label, subdir) list, so this never imports
the report registry or the export engine.
"""
import logging
import time
from pathlib import Path

log = logging.getLogger("tsmis.batch")


def newest_mtime(dest, subdir):
    """Newest file mtime (epoch seconds) for one report subdir across all
    <dest>/<src-env>/<subdir>/ folders, or None when nothing is there. Never
    raises — an unreadable folder simply contributes nothing."""
    dest = Path(dest)
    newest = None
    try:
        children = list(dest.iterdir())
    except OSError:
        return None
    for envdir in children:
        d = envdir / subdir
        try:
            if not d.is_dir():
                continue
            for f in d.iterdir():
                try:
                    if f.is_file():
                        m = f.stat().st_mtime
                        if newest is None or m > newest:
                            newest = m
                except OSError:
                    continue
        except OSError:
            continue
    return newest


def report_ages(dest, reports, now=None):
    """Per report: presence + newest-file age in the destination.

    `reports` is a list of (label, subdir). Returns a list of dicts
    [{label, subdir, present, mtime, age_seconds}] in the same order. `now`
    (epoch) is injectable for testing."""
    now = now if now is not None else time.time()
    out = []
    for label, subdir in reports:
        m = newest_mtime(dest, subdir)
        out.append({
            "label": label,
            "subdir": subdir,
            "present": m is not None,
            "mtime": m,
            "age_seconds": (now - m) if m is not None else None,
        })
    return out

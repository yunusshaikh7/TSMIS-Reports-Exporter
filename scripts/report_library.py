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

from artifact_store import is_report_data_file   # CMP-AUD-083: the shared data-file predicate

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
                    # CMP-AUD-083: only a real report data file (.xlsx/.pdf, not a
                    # lock/temp/sidecar) marks a report present / sets its age.
                    if f.is_file() and is_report_data_file(f.name):
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


def _newest_in(d):
    """Newest report-data-file mtime directly inside one folder, or None. Excludes
    locks/temps/sidecars/unsupported extensions (CMP-AUD-083). Never raises."""
    newest = None
    try:
        for f in Path(d).iterdir():
            try:
                if f.is_file() and is_report_data_file(f.name):
                    m = f.stat().st_mtime
                    if newest is None or m > newest:
                        newest = m
            except OSError:
                continue
    except OSError:
        return None
    return newest


def cell_ages(dest, reports, env_keys, now=None):
    """Per (environment, report) freshness for the comparison matrix.

    Unlike report_ages (which takes the global newest across ALL envs), this
    looks at each <dest>/<env_key>/<subdir>/ individually. `reports` is a list
    of (label, subdir); `env_keys` is ["ssor-prod", "ars-test", ...]. Returns
    {env_key: {subdir: {present, mtime, age_seconds}}}. `now` (epoch) is
    injectable for testing. Never raises — a missing/unreadable folder is just
    'not present'."""
    now = now if now is not None else time.time()
    dest = Path(dest)
    out = {}
    for env_key in env_keys:
        per = {}
        for _label, subdir in reports:
            m = _newest_in(dest / env_key / subdir)
            per[subdir] = {
                "present": m is not None,
                "mtime": m,
                "age_seconds": (now - m) if m is not None else None,
            }
        out[env_key] = per
    return out

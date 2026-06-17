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
_VERSION = 1


def build(report_idxs, combos, fast, workers, auto_consolidate, dest="", created=""):
    """A fresh manifest: which reports, which (src, env) combos (all 'pending'),
    the destination folder, and the run options. `combos` is an iterable of
    (src, env) pairs; `dest` is the always-current folder to refresh into."""
    return {
        "version": _VERSION,
        "reports": [int(i) for i in report_idxs],
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
    if (not isinstance(data, dict) or data.get("version") != _VERSION
            or not isinstance(data.get("steps"), list)):
        log.warning("batch manifest shape unexpected — ignoring")
        return None
    return data


def clear(path=MANIFEST_PATH):
    """Remove the manifest (best-effort) — a finished or discarded batch."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
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

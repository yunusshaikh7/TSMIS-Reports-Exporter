"""Destination-ownership marker (M03) for app-created output directories.

"Delete all reports" and the journaled store recovery act on directories the app
creates INSIDE a USER-CHOSEN destination — the Export-Everything store's
``<src>-<env>`` folders and its ``comparisons`` tree. Those were trusted by NAME
alone, so a user's own folder that happened to be named, say, ``ssor-prod`` under
the same destination was indistinguishable from an app-created one. This module
drops a tiny marker into each directory the app creates there, so the app can PROVE
it owns a directory before managing/clearing it — independent of the folder name.

The marker is additive and forward-looking. Reset still recognizes the legacy
known ``<src>-<env>`` / ``comparisons`` NAMES for directories created before the
marker existed (backward-compat), AND now also trusts any directory it can prove it
created (a marker, whatever the name) — so a future store layout or report family
is cleaned up without growing the hardcoded name list, and once every install has
re-exported (stamping its store) the name fallback can be retired to fully close
the user-collision gap.

Stdlib only; console-free; never raises — a marker that can't be written simply
means that directory falls back to name-based trust.
"""
import json
import logging
from pathlib import Path

log = logging.getLogger("tsmis.owned_dir")

# A dotfile so it sorts/hides unobtrusively and never collides with a report name.
OWNER_MARKER = ".tsmis-owned.json"
_APP_TAG = "TSMIS Reports Exporter"
_SCHEMA = 1


def mark_owned(path, kind="store"):
    """Stamp the ownership marker into the EXISTING directory `path`. `kind` is a
    free label ("store" / "comparisons") recorded for diagnostics. Best-effort and
    idempotent; returns True iff the marker is present afterward. Never raises."""
    marker = Path(path) / OWNER_MARKER
    try:
        with open(marker, "w", encoding="utf-8") as f:
            json.dump({"app": _APP_TAG, "schema": _SCHEMA, "kind": kind}, f)
        return True
    except OSError as e:
        log.info("ownership marker: could not write %s (%s)", marker, type(e).__name__)
        return marker.is_file()


def is_owned(path):
    """True iff `path` carries THIS app's ownership marker (so the app provably
    created it). A missing / foreign / corrupt marker => not owned. Never raises."""
    try:
        with open(Path(path) / OWNER_MARKER, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("app") == _APP_TAG


def ensure_owned_dir(path, kind="store"):
    """Create `path` (parents OK) if needed and stamp the ownership marker. Returns
    the Path. Fully best-effort — the marker is a safety annotation, so neither the
    mkdir nor the marker write is allowed to raise into the export/matrix flow that
    creates these directories anyway (those paths have their own dir handling)."""
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.info("ownership marker: could not create %s (%s)", path, type(e).__name__)
    mark_owned(path, kind=kind)
    return path

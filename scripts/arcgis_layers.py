"""ArcGIS layer library — the manually-stocked home for the owner's own exports
of the TSMIS ArcGIS layers.

Every TSMIS report is ultimately data from the TSMIS ArcGIS layers put into
report form, so this folder is the RAW-LAYER counterpart to `tsn_library/`
(which holds report-shaped TSN ground truth). Like the TSN library it is stocked
BY HAND — the app never writes exports here, it only creates the folder, seeds a
README, and reports what is present:

    <DATA_ROOT>/arcgis_layers/
        <anything>.xlsx        one layer export workbook per drop

The delivered shape (2026-07-20 drop: `IMLayers.xlsx`, `Layers7.20.xlsx`) is a
workbook whose FIRST sheet is an `INDEX` mapping each worksheet to its layer:

    Excel Worksheet | ArcGIS Layer or Table | ArcGIS Contents Path | Data Source

…where Data Source is the FeatureServer URL + version GUID + layer id. The index
exists because Excel truncates sheet names at 31 characters ("IM Complex
Intersection Cross R" is really "…Cross Reference"), so the sheet name alone is
not the layer identity.

This module deliberately does NOT parse those workbooks. Nothing consumes the
layers yet; staging them is the whole job, and a projection written before a
consumer exists would bake in a guess. When something does consume them, read the
INDEX sheet for the layer identity rather than trusting sheet names.

Console-free: creates folders best-effort, returns dicts, never prints or raises
for ordinary "not there yet" states.
"""
import logging
from pathlib import Path

import paths

log = logging.getLogger("tsmis.arcgis_layers")

_README_NAME = "_README - where ArcGIS layer exports go.txt"

# What counts as a layer export. Kept broad on purpose — the owner decides the
# file layout (one workbook per layer, or a bundle with a sheet per layer), and
# this module only needs to say what is present.
_PATTERNS = ("*.xlsx", "*.xlsm")


def root():
    """The library root (`<DATA_ROOT>/arcgis_layers`)."""
    return paths.ARCGIS_LAYERS_ROOT


def _readme_text():
    return "\n".join([
        "TSMIS Exporter - ArcGIS layer exports",
        "=" * 48,
        "",
        "Drop your exports of the TSMIS ArcGIS layers in this folder.",
        "",
        "Every TSMIS report is data from these layers put into report form, so",
        "this folder is the raw-layer counterpart to the tsn_library folder",
        "(which holds the report-shaped TSN ground truth).",
        "",
        "Layout: one Excel workbook per drop (.xlsx). A workbook can hold one",
        "layer, or many layers as one sheet each - if it has an INDEX sheet",
        "mapping worksheet -> ArcGIS layer + data source, the app will use it.",
        "",
        "Nothing in here is read by an export or comparison yet - this is a",
        "staging area. The app never writes here; it only creates the folder",
        "and this note.",
        "",
        "This note is ignored by the app and is safe to delete.",
    ]) + "\n"


def ensure_layout():
    """Create the root and seed the README so an empty library explains itself.
    Idempotent and best-effort (swallows OSError — a missing drop-zone is a
    "nothing staged yet" state, never a startup failure). The README refreshes
    whenever its generated text changed, matching `tsn_library.ensure_layout`.
    Returns the root Path."""
    r = root()
    try:
        r.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.info("ArcGIS layer root not creatable (%s: %s)", type(e).__name__, e)
        return r
    readme = r / _README_NAME
    try:
        current = _readme_text()
        if not readme.exists() or readme.read_text(encoding="utf-8") != current:
            readme.write_text(current, encoding="utf-8")
    except OSError:               # silent-ok: the README is cosmetic guidance
        pass
    return r


def files():
    """The staged layer-export workbooks, sorted by name. Empty when the folder
    is missing or unreadable."""
    r = root()
    found = []
    for pattern in _PATTERNS:
        try:
            found += [p for p in r.glob(pattern) if p.is_file()]
        except OSError as e:
            log.info("ArcGIS layer root not readable (%s: %s)", type(e).__name__, e)
            return []
    return sorted(set(found), key=lambda p: p.name.lower())


def status():
    """What Settings shows: the root path, how many workbooks are staged, and
    their names/sizes. Never raises."""
    staged = files()
    rows = []
    for p in staged:
        try:
            size = p.stat().st_size
        except OSError:  # silent-ok: vanished/locked mid-listing — the row still
            size = None  # names the file, and this panel is informational only
        rows.append({"name": p.name, "size": size})
    return {"root": str(root()), "count": len(staged), "files": rows}


# --------------------------------------------------------------------------- #
# The drop's identity (the "Reports vs layers" library, 2026-09-02)
# --------------------------------------------------------------------------- #
# The layers are exported by hand and rarely, and every report built from them
# is built from ONE drop. A build therefore records WHICH drop it came from, and
# the library reads stale the moment the staged drop is not that one. Two facts
# name a drop:
#
#   * its CONTENT fingerprint — `artifact_store.fingerprint` over every file in
#     the folder (the v2 content identity, CMP-AUD-080: a same-size, same-time
#     replacement of a layer's bytes still changes it). Memoized in-process per
#     file, so the 350 MB drop is hashed once per session;
#   * the date it was EXPORTED. The INDEX manifest has no date column, but the
#     export tool saves every workbook of a drop in one run and openpyxl stamps
#     the file's own creation timestamp (UTC) in its document properties, so the
#     manifest's timestamp is the drop's export time. When the manifest is
#     absent or unreadable the newest file date stands in, and says so.
_INDEX_NAME = "00_INDEX.xlsx"


def _exported_from_index(index_path):
    """(ISO date, ISO timestamp) from the manifest's own document properties,
    or (None, None). openpyxl stamps `created` in UTC without a tzinfo, so it
    is converted to the local date the owner would recognise."""
    from datetime import timezone

    try:
        from openpyxl import load_workbook
        wb = load_workbook(index_path, read_only=True)
    except Exception as e:      # silent-ok: an unreadable manifest is reported as "date unknown", never raised from a status read
        log.info("arcgis drop: INDEX unreadable for its export date (%s: %s)",
                 type(e).__name__, e)
        return None, None
    try:
        created = wb.properties.created
    finally:
        wb.close()
    if created is None:
        return None, None
    local = created.replace(tzinfo=timezone.utc).astimezone()
    return local.date().isoformat(), local.replace(microsecond=0).isoformat()


def drop_info(lib_root=None):
    """The staged drop's identity: `{fingerprint, exported, exported_at,
    exported_source, files, index_present}`.

    `fingerprint` is None when the folder cannot be read (a build must then
    refuse to claim a drop). `exported` is the local ISO date the drop was
    exported, from the manifest's own timestamp (`exported_source` "index") or,
    failing that, the newest staged file's modification date ("files"); None
    with source "unknown" when nothing is staged. Never raises."""
    import artifact_store
    from datetime import datetime

    lib = Path(lib_root) if lib_root else root()
    staged = []
    try:
        staged = sorted(p for p in lib.glob("*.xlsx") if p.is_file())
    except OSError as e:  # silent-ok: an unreadable drop-zone reads as empty; the fingerprint below says unreadable
        log.info("arcgis drop: root not readable (%s: %s)", type(e).__name__, e)
    fp = artifact_store.fingerprint(lib)
    if fp == artifact_store._UNREADABLE:
        fp = None
    index_path = lib / _INDEX_NAME
    index_present = index_path.is_file()
    exported = exported_at = None
    source = "unknown"
    if index_present:
        exported, exported_at = _exported_from_index(index_path)
        if exported:
            source = "index"
    if not exported and staged:
        try:
            newest = max(p.stat().st_mtime for p in staged)
            when = datetime.fromtimestamp(newest)
            exported = when.date().isoformat()
            exported_at = when.replace(microsecond=0).isoformat()
            source = "files"
        except OSError as e:  # silent-ok: a vanished file mid-stat leaves the date unknown
            log.info("arcgis drop: file dates unreadable (%s: %s)",
                     type(e).__name__, e)
    return {"fingerprint": fp, "exported": exported, "exported_at": exported_at,
            "exported_source": source, "files": len(staged),
            "index_present": index_present}

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

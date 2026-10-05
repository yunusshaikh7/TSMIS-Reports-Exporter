"""ArcGIS layer library — the app's copy of the TSMIS ArcGIS layers.

Every TSMIS report is ultimately data from the TSMIS ArcGIS layers put into
report form, so this folder is the RAW-LAYER counterpart to `tsn_library/`
(which holds report-shaped TSN ground truth):

    <DATA_ROOT>/arcgis_layers/
        00_INDEX.xlsx              the manifest (one row per layer)
        NN_<Layer Name>.xlsx       one workbook per layer (the FILENAME is the
                                   identity; sheet names truncate at 31 chars)
        _refresh/                  the app's working folder (staging, records)
        _previous/                 the files the last refresh replaced

Since v0.46.0 the app refreshes the library itself (ArcGIS ▸ Layers;
`arcgis_refresh`), using ArcGIS Pro's own Python. A manual export in the same
shape still works: copy the per-layer files and their 00_INDEX.xlsx in
together. `clean_road_layers` reads the layers; this module owns the folder,
the manifest's every column, the checks on one exported file, and the drop's
identity every build records.

Console-free: creates folders best-effort, returns dicts, never prints or raises
for ordinary "not there yet" states.
"""
import logging
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import clean_road_layers as crl
import paths

log = logging.getLogger("tsmis.arcgis_layers")

_README_NAME = "_README - where ArcGIS layer exports go.txt"

# What counts as a layer export. Kept broad on purpose: this module only needs
# to say what is present.
_PATTERNS = ("*.xlsx", "*.xlsm")

# The manifest's two columns after the six every reader knows (v0.46.0).
INDEX_EXTRA_HEADER = ["Exported At", "Exported By"]


def root():
    """The library root (`<DATA_ROOT>/arcgis_layers`)."""
    return paths.ARCGIS_LAYERS_ROOT


def _readme_text():
    return "\n".join([
        "TSMIS Exporter - ArcGIS layer library",
        "=" * 48,
        "",
        "The TSMIS ArcGIS layers the app builds reports from: one Excel",
        "workbook per layer plus 00_INDEX.xlsx, the manifest.",
        "",
        "Refresh them from the app: ArcGIS tab > Layers > Refresh layers. The",
        "app exports every layer with ArcGIS Pro (installed and signed in on",
        "this PC) and swaps each one in as it finishes. The files a refresh",
        "replaces are kept in the _previous folder until the next refresh;",
        "_refresh is the app's working folder.",
        "",
        "A manual export still works: copy the per-layer files and their",
        "00_INDEX.xlsx in together.",
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
# the 00_INDEX.xlsx manifest, every column
# --------------------------------------------------------------------------- #
def _local_naive(created):
    """openpyxl's `created` (UTC, no tzinfo) as a local naive datetime."""
    return created.replace(tzinfo=timezone.utc).astimezone() \
        .replace(tzinfo=None, microsecond=0)


def read_index_full(lib_root=None):
    """`({layer: row}, created)`: every manifest row with all its columns
    (`file rows fields path source exported_at exported_by`, the last two None
    on a manifest older than v0.46.0) and the workbook's own creation time as a
    LOCAL datetime (None when unknown). `({}, None)` when there is no readable
    manifest. Never raises."""
    from openpyxl import load_workbook

    p = Path(lib_root or root()) / crl.INDEX_NAME
    if not p.is_file():
        return {}, None
    try:
        wb = load_workbook(p, read_only=True, data_only=True)
    except Exception as e:      # silent-ok: an unreadable manifest reads as absent; a refresh writes a new one
        log.info("arcgis_layers: INDEX unreadable (%s: %s)", type(e).__name__, e)
        return {}, None
    try:
        created = wb.properties.created
        created = _local_naive(created) if created is not None else None
        it = wb.worksheets[0].iter_rows(values_only=True)
        header = [str(c).strip() if c is not None else "" for c in next(it, ())]
        if header[:len(crl.INDEX_HEADER)] != crl.INDEX_HEADER:
            return {}, created
        col = {name: i for i, name in enumerate(header)}
        rows = {}
        for r in it:
            if not r or r[0] is None or str(r[0]).strip() == "":
                continue

            def cell(name, r=r):
                i = col.get(name)
                return r[i] if i is not None and i < len(r) else None

            layer = str(cell("ArcGIS Layer or Table") or "").strip()
            if not layer:
                continue
            at = cell("Exported At")
            rows[layer] = {
                "file": str(r[0]).strip(),
                "rows": cell("Rows Exported"),
                "fields": cell("Fields Exported"),
                "path": cell("ArcGIS Contents Path") or "",
                "source": cell("Data Source") or "",
                "exported_at": (at.replace(microsecond=0).isoformat()
                                if isinstance(at, datetime) else (str(at) if at else None)),
                "exported_by": cell("Exported By") or None,
            }
        return rows, created
    except Exception as e:      # silent-ok: a damaged manifest reads as absent, like an unreadable one
        log.info("arcgis_layers: INDEX unreadable (%s: %s)", type(e).__name__, e)
        return {}, None
    finally:
        wb.close()


def _parse_local(stamp):
    try:
        return datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):   # silent-ok: an unparseable stamp reads as unknown; callers fall back to the drop's date
        return None


def write_index(lib_root, rows):
    """Write the manifest atomically: the six columns every reader knows, then
    Exported At / Exported By. The workbook's own creation stamp is the OLDEST
    layer's export time — what a reader that knows only the stamp should
    assume about the whole library."""
    from openpyxl import Workbook

    lib = Path(lib_root)
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("INDEX")
    ws.append(crl.INDEX_HEADER + INDEX_EXTRA_HEADER)
    stamps = []
    for layer, r in sorted(rows.items(), key=lambda kv: str(kv[1].get("file", "")).lower()):
        at = r.get("exported_at")
        when = _parse_local(at) if at else None
        if when is not None:
            stamps.append(when)
        ws.append([r.get("file"), layer, r.get("rows"), r.get("fields"),
                   r.get("path") or layer, r.get("source") or "",
                   str(at) if at else None, r.get("exported_by")])
    if stamps:
        wb.properties.created = min(stamps).astimezone(timezone.utc).replace(tzinfo=None)
    wb.properties.creator = "TSMIS Exporter"
    target = lib / crl.INDEX_NAME
    tmp = lib / f"{crl.INDEX_NAME}.tmp-{os.getpid()}"
    try:
        wb.save(tmp)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:      # silent-ok: an orphan .tmp- never counts toward the drop
                pass


# --------------------------------------------------------------------------- #
# checking one exported layer file
# --------------------------------------------------------------------------- #
_ROW_TAG = re.compile(rb"<(?:[A-Za-z]\w*:)?row[\s/>]")
_SHEET_TAG = re.compile(rb"<(?:[A-Za-z]\w*:)?sheet\b[^>]*?\b(?:r:)?id=\"([^\"]+)\"")
_REL_TAG = re.compile(rb"<Relationship\b[^>]*?>")


def _first_sheet_member(z):
    """The zip member holding the workbook's FIRST worksheet."""
    names = set(z.namelist())
    try:
        wb_xml = z.read("xl/workbook.xml")
        rels = z.read("xl/_rels/workbook.xml.rels")
        m = _SHEET_TAG.search(wb_xml)
        if m:
            rid = m.group(1)
            for tag in _REL_TAG.findall(rels):
                if re.search(rb'\bId="' + re.escape(rid) + rb'"', tag):
                    t = re.search(rb'\bTarget="([^"]+)"', tag)
                    if t:
                        target = t.group(1).decode("utf-8")
                        member = target.lstrip("/") if target.startswith("/") \
                            else "xl/" + target
                        if member in names:
                            return member
    except KeyError:       # silent-ok: a workbook without the standard parts falls back below
        pass
    sheets = sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    if not sheets:
        raise ValueError("the file holds no worksheet")
    return sheets[0]


def count_sheet_rows(path):
    """Rows in the first worksheet, counted from its XML (seconds on a 100 MB
    export, where reading every cell would take minutes)."""
    n = 0
    tail = b""
    with zipfile.ZipFile(path) as z:
        with z.open(_first_sheet_member(z)) as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                buf = tail + chunk
                # A tag split across two reads is counted once: matches lying
                # wholly inside the carried-over tail were counted last time.
                n += sum(1 for m in _ROW_TAG.finditer(buf) if m.end() > len(tail))
                tail = buf[-16:]
    return n


def read_header(path):
    """The first row's column names, trailing blanks dropped."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        first = next(wb.worksheets[0].iter_rows(max_row=1, values_only=True), ())
    finally:
        wb.close()
    header = ["" if c is None else str(c).strip() for c in first]
    while header and not header[-1]:
        header.pop()
    return header


def inspect_export(path, server_rows=None):
    """`{data_rows, fields, header}` for one exported layer file. Raises
    ValueError when the file is unusable or holds FEWER data rows than ArcGIS
    counted on the server (`server_rows`) — a truncated export. More is the
    measured count/export race and passes."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("the export wrote no file")
    try:
        total = count_sheet_rows(path)
        header = read_header(path)
    except Exception as e:     # noqa: BLE001 — any unreadable workbook is one answer: unusable
        raise ValueError(f"the export is not a readable workbook "
                         f"({type(e).__name__}: {e})") from e
    if not header:
        raise ValueError("the export has no header row")
    data_rows = max(total - 1, 0)
    if server_rows is not None and data_rows < int(server_rows):
        raise ValueError(
            f"the export holds {data_rows:,} rows but ArcGIS counted "
            f"{int(server_rows):,} on the server — it looks truncated")
    return {"data_rows": data_rows, "fields": len(header), "header": header}


# --------------------------------------------------------------------------- #
# The drop's identity (the "Reports vs layers" library, 2026-09-02)
# --------------------------------------------------------------------------- #
# Every report built from the layers is built from what the library held at
# that moment, so a build records WHICH drop it came from, and reads stale the
# moment the library holds something else. Two facts name a drop:
#
#   * its CONTENT fingerprint — every layer workbook's name and bytes (the
#     manifest included), so a same-size, same-time replacement of a layer
#     still changes it (CMP-AUD-080). Only the .xlsx files count (v0.46.0): the
#     README, the app's _refresh/_previous folders and in-flight temps never
#     move it. Digests are memoized per file, so the 350 MB drop hashes once
#     per session;
#   * the date it was EXPORTED. Since v0.46.0 the manifest records each layer's
#     own export time (Exported At), and the drop's date is the OLDEST of them
#     — a reconstruction later than a layer's export would claim edits that
#     layer never saw. A manifest without that column (a manual export) dates
#     the drop by its own creation stamp; with no manifest the newest file
#     date stands in, and says so.
def _drop_fingerprint(lib, staged):
    """A content identity over the library's .xlsx files, or None when one
    cannot be read (a build then refuses to claim a drop)."""
    import hashlib

    import artifact_store

    parts = []
    for p in staged:
        try:
            parts.append(f"{p.name}\0{artifact_store.content_digest(p)}")
        except OSError as e:
            log.info("arcgis drop: %s unreadable (%s)", p.name, e)
            return None
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"xlsx1:{len(parts)}:{digest}"


def _staged_workbooks(lib):
    """The library's .xlsx files by name, or None when the folder is missing
    or unreadable (the drop then has no identity at all)."""
    try:
        if not lib.is_dir():
            return None
        return sorted((p for p in lib.glob("*.xlsx")
                       if p.is_file() and not p.name.startswith("~$")),
                      key=lambda p: p.name)
    except OSError as e:  # silent-ok: an unreadable drop-zone reads as empty
        log.info("arcgis drop: root not readable (%s: %s)", type(e).__name__, e)
        return None


def drop_info(lib_root=None):
    """The library's identity: `{fingerprint, exported, exported_at,
    exported_source, newest_at, mixed, layers, files, index_present}`.

    `fingerprint` is None when the folder cannot be read. `exported` /
    `exported_at` are the local date/time the drop was exported — the OLDEST
    layer's when the manifest records each layer ("index"), the manifest's own
    stamp for a manual export ("index"), else the newest file's date ("files");
    None with source "unknown" when nothing is staged. `layers` maps each
    layer to its own export time when the manifest records it, and `mixed`
    says the layers were exported on different days. Never raises."""
    lib = Path(lib_root) if lib_root else root()
    staged = _staged_workbooks(lib)
    fp = _drop_fingerprint(lib, staged) if staged is not None else None
    staged = staged or []
    index_path = lib / crl.INDEX_NAME
    index_present = index_path.is_file()
    rows, created = read_index_full(lib) if index_present else ({}, None)
    present = {p.name for p in staged}
    per_layer = {}
    for layer, row in rows.items():
        when = _parse_local(row.get("exported_at")) if row.get("exported_at") else None
        if when is not None and row.get("file") in present:
            per_layer[layer] = when
    exported = exported_at = newest_at = None
    source = "unknown"
    if per_layer:
        oldest, newest = min(per_layer.values()), max(per_layer.values())
        exported, exported_at = oldest.date().isoformat(), oldest.isoformat()
        newest_at = newest.isoformat()
        source = "index"
    elif created is not None:
        exported, exported_at = created.date().isoformat(), created.isoformat()
        source = "index"
    if not exported and staged:
        try:
            newest = max(p.stat().st_mtime for p in staged)
            when = datetime.fromtimestamp(newest).replace(microsecond=0)
            exported, exported_at = when.date().isoformat(), when.isoformat()
            source = "files"
        except OSError as e:  # silent-ok: a vanished file mid-stat leaves the date unknown
            log.info("arcgis drop: file dates unreadable (%s: %s)",
                     type(e).__name__, e)
    return {"fingerprint": fp, "exported": exported, "exported_at": exported_at,
            "exported_source": source, "newest_at": newest_at,
            "mixed": bool(per_layer) and newest_at[:10] != exported,
            "layers": {k: v.isoformat() for k, v in per_layer.items()},
            "files": len(staged), "index_present": index_present}


def consistent_asof(required, drop=None):
    """The latest date a build reading `required` layers can honestly be
    reconstructed at: the OLDEST of those layers' own export dates, when the
    manifest records every one of them; otherwise the drop's export date."""
    drop = drop if drop is not None else drop_info()
    stamps = drop.get("layers") or {}
    dates = [stamps.get(name) for name in required]
    if dates and all(dates):
        return min(dates)[:10]
    return drop.get("exported")

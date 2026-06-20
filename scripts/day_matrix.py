"""Compare-tab "vs TSN Matrix" engine (the day-keyed TSN comparison matrix).

A MANUAL, day-picking comparison matrix (a sibling of the Everything matrix, but
under the Compare tab): rows = report types, columns = exported DAYS the user
adds, each cell = that report's export FOR THAT DAY compared vs TSN. There is ONE
data source for the whole matrix (default ssor-prod); no cross-environment and no
live re-export — it compares specific HISTORICAL exports the user already pulled.

It SHARES the TSN compare path (`matrix.consolidate_and_compare_tsn`) and the TSN
dataset (`matrix.tsn_source`, now backed by the canonical TSN library and resolved
by each row's own `tsn_subdir`, with the user's `matrix_tsn_files` pick as an
override) with the Everything matrix — only the TSMIS source folder (a specific run
folder under output/) and the output store differ.

The matrix lists EVERY report so it's the single place TSN comparisons surface.
Highway Log (Excel) and Highway Log (PDF) are wired today; the rest (Ramp
Summary/Detail, Highway Sequence, Intersection Summary/Detail) appear greyed —
groundwork for 0.17.0, which plugs each report in by adding its TSN comparator +
per-report TSN dataset and flipping `supported` in `_day_rows()` / dispatching it
in `build_day_cell`. The store, snapshot, actions, and queue are report-agnostic;
the per-row `tsn_subdir` (from `matrix.tsn_subdir_for`) carries each report's TSN
dataset key — the old Highway-Log-only `TSN_SUBDIR` constant is gone.

Console-free like the rest of the core: progress via the Events sink, exceptions
raised — never print/input/sys.exit. Only gui_api / gui_worker drive it.
"""
import json
import logging
import os
import time
from pathlib import Path

import matrix
import reports
from paths import OUTPUT_ROOT, list_output_days, parse_run_folder

log = logging.getLogger("tsmis.day_matrix")

SOURCE_DEFAULT = "ssor-prod"
BYDAY_DIRNAME = "tsn-by-day"          # under output/comparisons/
_RESULTS_FILE = "_results.json"


# --------------------------------------------------------------------------- #
# rows + sources
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (the matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _day_rows():
    """[(row_key, label, subdir, fmt, supported, tsn_subdir)] for the vs-TSN matrix
    — EVERY report, so the matrix is the single place all TSN comparisons surface.
    Only the two Highway Log rows have a coded TSN comparator today (Excel-vs-TSN and
    PDF-vs-TSN); the rest (Ramp Summary/Detail, Highway Sequence, Intersection
    Summary/Detail) are greyed groundwork.

    `tsn_subdir` is the report's TSN dataset key (from matrix.tsn_subdir_for): both
    Highway Log rows share 'highway_log'; every other report uses its own subdir.

    0.17.0 plug-in: give a report a TSN comparator + a per-report TSN dataset, then
    flip its `supported` here and dispatch it in build_day_cell — the matrix shell,
    store, actions, and snapshot are already report-agnostic and resolve TSN per
    `tsn_subdir`."""
    out = []
    for row_key, label, subdir, _idx, adapter in reports.matrix_rows():
        tsn_subdir = matrix.tsn_subdir_for(row_key, subdir, adapter)
        if row_key == "highway_log":
            out.append((row_key, label, subdir, "excel", True, tsn_subdir))
        elif row_key == "highway_log_pdf":
            out.append((row_key, label, subdir, "pdf", True, tsn_subdir))
        else:
            out.append((row_key, label, subdir, None, False, tsn_subdir))
    # Intersection Summary/Detail have no cross-env adapter (absent from
    # matrix_rows), so add them here as greyed groundwork rows.
    for row_key, label, subdir in reports.tsn_matrix_extra_rows():
        out.append((row_key, label, subdir, None, False,
                    matrix.tsn_subdir_for(row_key, subdir, None)))
    return out


def _row_lookup():
    return {r[0]: r for r in _day_rows()}


# --------------------------------------------------------------------------- #
# paths + the by-day results cache
# --------------------------------------------------------------------------- #
def byday_root():
    return OUTPUT_ROOT / matrix.COMPARISONS_DIRNAME / BYDAY_DIRNAME


def day_folder_name(date, source):
    return f"{date} {source}"


def day_out_path(date, source, row_key):
    """The comparison VALUES workbook for one (day, report) vs TSN. Stable,
    dateless filename per cell (mtime is the freshness signal)."""
    return byday_root() / day_folder_name(date, source) / f"{row_key}_vs_tsn.xlsx"


def _results_path():
    return byday_root() / _RESULTS_FILE


def load_results():
    """{ "<date source>|<row>": {verdict, diff_cells, one_sided, built_at_mtime} }.
    Tolerant: missing/corrupt -> {} (never raises)."""
    try:
        with open(_results_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except OSError:
        return {}                            # not written yet (first run) — expected
    except ValueError as e:                  # corrupt JSON: surface it, then degrade
        log.warning("day_matrix: corrupt results cache %s (%s: %s); treating as empty",
                    _results_path(), type(e).__name__, e)
        return {}


def record_result(date, source, row_key, verdict, diff_cells, one_sided,
                  built_at_mtime):
    data = load_results()
    data[f"{day_folder_name(date, source)}|{row_key}"] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
    }
    p = _results_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, p)
    except OSError as e:
        log.warning("day_matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)


# --------------------------------------------------------------------------- #
# filesystem helpers
# --------------------------------------------------------------------------- #
def _folder_newest_mtime(p):
    """Newest non-temp file mtime in a folder, or None when empty/absent."""
    newest = None
    try:
        for e in Path(p).iterdir():
            if e.is_file() and not e.name.startswith("~$"):
                m = e.stat().st_mtime
                if newest is None or m > newest:
                    newest = m
    except OSError:
        pass
    return newest


def tsmis_dir(date, source, subdir):
    """output/<date source>/<subdir>/ — the per-route export the cell compares."""
    return OUTPUT_ROOT / day_folder_name(date, source) / subdir


def available_days(source):
    """Dates (newest first) under output/ that have a Highway Log export (Excel
    or PDF) for `source` — the add-day picker's options."""
    out, seen = [], set()
    for name in list_output_days():
        parsed = parse_run_folder(name)
        if not parsed:
            continue
        date, src, env = parsed
        if f"{src}-{env}" != source or date in seen:
            continue
        base = OUTPUT_ROOT / name
        if any(_folder_newest_mtime(base / sub) is not None
               for sub in ("highway_log", "highway_log_pdf")):
            seen.add(date)
            out.append(date)
    return out


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def day_matrix_snapshot(source, days, hidden=None, tsn_files=None, dest=None,
                        now=None):
    """Full render model for the by-day matrix. PURE stat — no workbook opened
    (counts come from the cache). `days` is the ordered list of date columns;
    `hidden` hides report rows; `tsn_files`/`dest` resolve the shared TSN dataset
    (same as the Everything matrix). Greyed rows render cmp {supported:false}."""
    now = now if now is not None else time.time()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    tsn_files = tsn_files or {}
    all_rows = _day_rows()
    rows = [r for r in all_rows if r[0] not in hidden]
    results = load_results()

    # The TSN dataset is resolved PER ROW by its tsn_subdir (both HL rows share
    # 'highway_log'), cached so each distinct dataset is resolved once. `dest` is
    # the Everything matrix's batch_dest so the by-day matrix reuses the same TSN
    # library / _tsn_input fallback + the user's matrix_tsn_files pick.
    _tsn_cache = {}

    def _tsn_for(sub):
        if sub not in _tsn_cache:
            _tsn_cache[sub] = (matrix.tsn_source(dest, sub, tsn_files.get(sub))
                               if dest else {"kind": "none"})
        return _tsn_cache[sub]

    # The single shared TSN picker shows the primary supported dataset (Highway Log
    # today). Per-row readiness still drives each cell below.
    supported_subdirs = []
    for r in all_rows:
        if r[4] and r[5] not in supported_subdirs:
            supported_subdirs.append(r[5])
    primary = supported_subdirs[0] if supported_subdirs else "highway_log"
    src_primary = _tsn_for(primary)
    tsn_meta = {"supported": True, "source_kind": src_primary.get("kind"),
                "source_path": src_primary.get("path"),
                "pdf_count": src_primary.get("pdf_count"),
                "tsn_subdir": primary, "file": tsn_files.get(primary),
                "input_dir": str(matrix.tsn_input_root(dest, primary)) if dest else None}

    cells = {}
    for row_key, _label, subdir, fmt, supported, tsn_subdir in rows:
        per = {}
        for date in days:
            tdir = tsmis_dir(date, source, subdir)
            exp_m = _folder_newest_mtime(tdir)
            export = {"present": exp_m is not None, "mtime": exp_m,
                      "age_seconds": (now - exp_m) if exp_m is not None else None}
            if not supported:
                cmp = {"supported": False}
            else:
                src_tsn = _tsn_for(tsn_subdir)
                tsn_ready = src_tsn.get("kind") in ("file", "consolidated")
                rec = results.get(f"{day_folder_name(date, source)}|{row_key}")
                srcs = [{"name": "cell", "present": exp_m is not None, "mtime": exp_m},
                        {"name": "tsn", "present": tsn_ready, "mtime": src_tsn.get("mtime")}]
                cmp = matrix._cmp_state(day_out_path(date, source, row_key), srcs, rec)
            per[date] = {"export": export, "cmp": cmp}
        cells[row_key] = per

    # Per-day "consolidated" indicator: does a reusable consolidated workbook exist
    # for the day's Highway Log export(s), and is it still fresh? Summarised across
    # the supported subdirs that actually have an export that day, so the day-column
    # header can show a badge + offer a 'refresh consolidated'.
    day_consolidated = {}
    for date in days:
        subs = {}
        for _k, _label, subdir, fmt, supported, _tsn_subdir in all_rows:
            if not supported:
                continue
            tdir = tsmis_dir(date, source, subdir)
            if _folder_newest_mtime(tdir) is None:
                continue                         # no export -> nothing to consolidate
            subs[subdir] = matrix.consolidated_state(tdir, subdir)
        exists = any(s["exists"] for s in subs.values())
        fresh = exists and all(s["fresh"] for s in subs.values() if s["exists"])
        day_consolidated[date] = {"exists": exists, "fresh": fresh}

    return {
        "source": source,
        "sources": [{"key": k, "label": matrix.default_env_label(k)} for k in sources()],
        "days": days,
        "rows": [r[0] for r in rows],
        "row_labels": {r[0]: r[1] for r in rows},
        "row_supported": {r[0]: r[4] for r in rows},
        "all_rows": [{"key": r[0], "label": r[1], "supported": r[4]} for r in all_rows],
        "hidden": sorted(hidden),
        "tsn_meta": tsn_meta,
        "cells": cells,
        "day_consolidated": day_consolidated,
    }


# --------------------------------------------------------------------------- #
# the scoped rebuild list + one-cell build (pure delegation to the shared path)
# --------------------------------------------------------------------------- #
def cells_to_rebuild(snapshot, scope="stale", row=None, date=None):
    """[(date, row_key)] to (re)build, honoring scope. 'all' = every supported
    cell with the TSMIS side present; 'stale' = only missing/stale ones. Optional
    `row` / `date` filters drive the per-row and per-column rebuilds. Skips greyed
    rows and cells whose export or TSN side is missing."""
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        for d in snapshot["days"]:
            if date and d != date:
                continue
            cmp = snapshot["cells"][row_key][d]["cmp"]
            if not cmp.get("supported") or cmp.get("missing_side"):
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((d, row_key))
    return todo


def build_day_cell(source, date, row_key, dest, events, tsn_files=None,
                   confirm_overwrite=None, force_consolidate=False,
                   also_formulas=False):
    """Build ONE (day, report) vs-TSN comparison: resolve the shared TSN dataset,
    consolidate that day's per-route export (reusing the day folder's persistent
    consolidated unless stale or `force_consolidate`), compare vs TSN, write the
    VALUES workbook to the by-day store, and cache its counts. Pure delegation to
    matrix.consolidate_and_compare_tsn (the SHARED path). Returns the
    ConsolidateResult. Raises ValueError on an unknown/greyed row or no TSN."""
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown by-day matrix row: {row_key}")
    # Validate date+source at the boundary so neither can traverse out of output/
    # even if a settings file was hand-edited (the bridge already validates the
    # normal path). The combined folder name must parse as a real run folder.
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(f"invalid date/source for the by-day matrix: {date!r} / {source!r}")
    _k, _label, subdir, fmt, supported, tsn_subdir = rows[row_key]
    if not supported:
        raise ValueError(f"no TSN comparison for {row_key} yet")
    tsn_files = tsn_files or {}
    src_tsn = matrix.tsn_source(dest, tsn_subdir, tsn_files.get(tsn_subdir))
    if src_tsn.get("kind") not in ("file", "consolidated"):
        raise ValueError("no consolidated TSN workbook available")

    out_path = day_out_path(date, source, row_key)
    result = matrix.consolidate_and_compare_tsn(
        tsmis_dir(date, source, subdir), src_tsn["path"], out_path, fmt, events,
        confirm_overwrite=confirm_overwrite, force_consolidate=force_consolidate,
        also_formulas=also_formulas)
    if result.status == "ok" and out_path.exists():
        diff_cells, one_sided = matrix.read_counts(out_path, has_route=True)
        try:
            built_at = out_path.stat().st_mtime
        except OSError:
            built_at = None
        record_result(date, source, row_key, result.verdict, diff_cells, one_sided,
                      built_at)
    return result

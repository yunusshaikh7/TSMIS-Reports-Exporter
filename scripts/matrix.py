"""Cross-environment comparison MATRIX engine (Everything tab).

A thin ORCHESTRATION layer over the already-audited cross-environment comparison
(`compare_env`) and the always-current Export-Everything store. It NEVER
recomputes report contents and NEVER touches `compare_core` — it only:

  * enumerates the report x environment cells from the store,
  * computes per-cell EXPORT freshness (newest file mtime) via report_library,
  * computes per-cell COMPARISON freshness (the comparison workbook's mtime vs
    the two source folders' newest export mtime),
  * orchestrates `compare_env.<adapter>.compare_folders(...)` to (re)build a
    cell's comparison of (report, env) against the BASELINE env, writing into
    <dest>/comparisons/<baseline>/, and
  * caches each comparison's verdict + discrepancy counts in a sidecar so the
    snapshot (which the GUI renders) stays a pure, offline filesystem read.

Console-free like the rest of the core: progress is reported through the Events
sink and exceptions are raised — never print/input/sys.exit. Only gui_api /
gui_worker drive it.
"""
import json
import logging
import os
import shutil
import time
from pathlib import Path

import report_library
import reports
from common import DATA_SOURCES, ENVIRONMENTS

log = logging.getLogger("tsmis.matrix")

BASELINE_DEFAULT = "ssor-prod"
COMPARISONS_DIRNAME = "comparisons"
_RESULTS_FILE = "_results.json"
_NEQ = " ≠ "                       # the compare_core diff marker (read-only here)
_MTIME_TOL_S = 1.0                 # float-mtime equality tolerance for the cache


# --------------------------------------------------------------------------- #
# cell identity
# --------------------------------------------------------------------------- #
def env_keys():
    """The matrix columns: every data-source/environment combo, in display order
    (ssor before ars; prod/test/dev)."""
    return [f"{s}-{e}" for s in DATA_SOURCES for e in ENVIRONMENTS]


def default_env_label(key):
    """A readable column label from an env key, with no dependency on the report
    registry: 'ssor-prod' -> 'SSOR / Prod'."""
    src, _, env = str(key).partition("-")
    return f"{src.upper()} / {env.title()}" if env else str(key).upper()


def _row_defs():
    """{row_key: (label, subdir, export_idx, adapter, has_route)} from the
    registry. has_route: the XLSX reports compare in the consolidated (Route +
    columns) shape; Ramp Summary (PDF, no sheet_name) is per-route."""
    out = {}
    for row_key, label, subdir, export_idx, adapter in reports.matrix_rows():
        has_route = getattr(adapter, "sheet_name", None) is not None
        out[row_key] = (label, subdir, export_idx, adapter, has_route)
    return out


# --------------------------------------------------------------------------- #
# paths (decision b: <dest>/comparisons/<baseline>/...) — STABLE, dateless names
# --------------------------------------------------------------------------- #
def comparisons_root(dest, baseline_key):
    return Path(dest) / COMPARISONS_DIRNAME / baseline_key


def comparison_path(dest, baseline_key, row_key, cell_key):
    """The comparison workbook for (row, cell-env) under one baseline.

    DELIBERATELY a deterministic, dateless name (NOT adapter.suggest_name, which
    embeds today's date): the matrix overwrites in place and uses the file's
    MTIME as the freshness signal, so the name must be stable across days. Do not
    'fix' this to a dated name."""
    return comparisons_root(dest, baseline_key) / f"{cell_key}_{row_key}.xlsx"


def _results_path(dest, baseline_key):
    return comparisons_root(dest, baseline_key) / _RESULTS_FILE


# --------------------------------------------------------------------------- #
# the comparison-result cache (verdict + discrepancy counts), keyed by baseline
# --------------------------------------------------------------------------- #
def load_results(dest, baseline_key):
    """{row_key: {cell_key: {verdict, diff_cells, one_sided, built_at_mtime}}}.
    Tolerant: missing/corrupt -> {} (never raises)."""
    p = _results_path(dest, baseline_key)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_results(dest, baseline_key, data):
    p = _results_path(dest, baseline_key)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, p)
    except OSError as e:
        log.warning("matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)


def record_result(dest, baseline_key, row_key, cell_key, verdict,
                  diff_cells, one_sided, built_at_mtime):
    data = load_results(dest, baseline_key)
    data.setdefault(row_key, {})[cell_key] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
    }
    _save_results(dest, baseline_key, data)


# --------------------------------------------------------------------------- #
# read discrepancy counts back from a produced VALUES workbook (no COM/F9)
# --------------------------------------------------------------------------- #
def read_counts(values_path, has_route):
    """(diff_cells, one_sided) read straight off a VALUES-flavor comparison
    workbook's Comparison sheet content: cells carrying the ' ≠ ' marker, and
    non-'Both' statuses. The values flavor stores literal results, so no Excel
    recalc is needed. Returns (None, None) if unreadable. Layout:
      has_route:  A Route | B key | C # | D A-Row | E B-Row | F Status | G Diffs | H.. fields
      flat:       A Route | B # | C A-Row | D B-Row | E Status | F Diffs | G.. fields
    """
    status_col = 6 if has_route else 5          # 1-based
    first_field = 8 if has_route else 7
    try:
        from openpyxl import load_workbook
        wb = load_workbook(values_path, read_only=True, data_only=True)
    except Exception:                            # noqa: BLE001 (best-effort read)
        return (None, None)
    try:
        ws = wb["Comparison"]
        one_sided = diff_cells = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row is None or all(v is None for v in row):
                continue
            status = row[status_col - 1] if len(row) >= status_col else None
            if status and status != "Both":
                one_sided += 1
            for ci in range(first_field - 1, len(row)):
                v = row[ci]
                if isinstance(v, str) and _NEQ in v:
                    diff_cells += 1
        return (diff_cells, one_sided)
    except Exception:                            # noqa: BLE001
        return (None, None)
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# per-cell comparison freshness (decision c: mtime staleness)
# --------------------------------------------------------------------------- #
def comparison_state(dest, baseline_key, row_key, cell_key, subdir,
                     cell_ages_map, results):
    """{built, mtime, stale, reason, missing_side, verdict, diff_cells,
    one_sided} for one non-baseline cell. STALE when the comparison file is
    missing, or either side's export mtime is newer than it. The cached
    verdict/counts are surfaced only when the cache's recorded mtime still
    matches the file (else they read as unknown and the cell shows 're-run')."""
    base_m = cell_ages_map.get(baseline_key, {}).get(subdir, {}).get("mtime")
    cell_m = cell_ages_map.get(cell_key, {}).get(subdir, {}).get("mtime")
    if base_m is None and cell_m is None:
        missing_side = "both"
    elif base_m is None:
        missing_side = "baseline"
    elif cell_m is None:
        missing_side = "cell"
    else:
        missing_side = None

    try:
        cmp_m = comparison_path(dest, baseline_key, row_key, cell_key).stat().st_mtime
    except OSError:
        cmp_m = None
    built = cmp_m is not None

    verdict = diff_cells = one_sided = None
    rec = (results.get(row_key, {}) or {}).get(cell_key)
    if built and rec and abs(float(rec.get("built_at_mtime", -1)) - cmp_m) < _MTIME_TOL_S:
        verdict = rec.get("verdict")
        diff_cells = rec.get("diff_cells")
        one_sided = rec.get("one_sided")

    if not built:
        stale, reason = True, "missing"
    else:
        newer_base = base_m is not None and base_m > cmp_m + _MTIME_TOL_S
        newer_cell = cell_m is not None and cell_m > cmp_m + _MTIME_TOL_S
        if newer_base and newer_cell:
            stale, reason = True, "both_newer"
        elif newer_base:
            stale, reason = True, "baseline_newer"
        elif newer_cell:
            stale, reason = True, "cell_newer"
        else:
            stale, reason = False, "fresh"
    return {"supported": True, "built": built, "mtime": cmp_m, "stale": stale,
            "reason": reason, "missing_side": missing_side, "verdict": verdict,
            "diff_cells": diff_cells, "one_sided": one_sided}


# --------------------------------------------------------------------------- #
# TSN / cross-format modes. The matrix only ORCHESTRATES the existing (manual)
# comparison adapters — compare_env / compare_highway_log / compare_highway_log_pdf
# are NEVER edited. TSN drops: <dest>/_tsn_input/<subdir>/; the TSN + cross-format
# comparison sheets: <dest>/comparisons/tsn/ (apart from the cross-env tree).
# --------------------------------------------------------------------------- #
TSN_INPUT_DIRNAME = "_tsn_input"
TSN_COMPARE_DIRNAME = "tsn"            # under comparisons/
_TSN_RESULTS_FILE = "_tsn_results.json"


def _safe_mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


def tsn_input_root(dest, subdir):
    """Where the user drops the TSN dataset (a consolidated workbook or the
    district PDFs). TSN is ONE dataset per report family, so both Highway Log TSN
    modes (Excel-vs-TSN, PDF-vs-TSN) share <dest>/_tsn_input/highway_log/."""
    return Path(dest) / TSN_INPUT_DIRNAME / subdir


def tsn_comparisons_root(dest):
    return Path(dest) / COMPARISONS_DIRNAME / TSN_COMPARE_DIRNAME


def tsn_source(dest, subdir, selected_file=None):
    """Resolve the TSN dataset. A user-picked `selected_file` wins (must be a real
    .xlsx). Otherwise scan <dest>/_tsn_input/<subdir>/: a consolidated .xlsx
    (newest) is used; only district PDFs -> the 'prompt to consolidate' state;
    nothing -> none. Returns {kind: file|consolidated|pdfs|none, path?, mtime?,
    pdf_count?}."""
    if selected_file:
        p = Path(selected_file)
        if p.is_file() and p.suffix.lower() == ".xlsx":
            return {"kind": "file", "path": str(p), "mtime": _safe_mtime(p)}
    root = tsn_input_root(dest, subdir)
    xlsx, pdfs = [], 0
    try:
        for e in root.iterdir():
            if not e.is_file():
                continue
            sfx = e.suffix.lower()
            if sfx == ".xlsx" and not e.name.startswith("~$"):
                xlsx.append(e)
            elif sfx == ".pdf":
                pdfs += 1
    except OSError:
        pass
    if xlsx:
        newest = max(xlsx, key=lambda q: _safe_mtime(q) or 0)
        return {"kind": "consolidated", "path": str(newest), "mtime": _safe_mtime(newest)}
    if pdfs:
        return {"kind": "pdfs", "pdf_count": pdfs}
    return {"kind": "none"}


# --- per-row comparison MODE registry -------------------------------------- #
# A row's "env" (cross-environment) mode is supported only when it has a
# compare_env folder adapter. Highway Log is TWO rows (Excel + PDF), each with its
# own TSN + cross-format modes; the other reports get one greyed "tsn" placeholder
# (no comparison code yet). A mode dict: id, label, kind ("env"|"tsn"|"self"),
# supported, env_subdir, plus tsn_subdir+fmt (tsn) or other_subdir (self).
def _row_modes(row_key, subdir, adapter):
    env = {"id": "env", "label": "Cross-environment", "kind": "env",
           "supported": adapter is not None, "env_subdir": subdir}
    if row_key == "highway_log":            # TSMIS Excel
        return [env,
                {"id": "tsn", "label": "vs TSN", "kind": "tsn", "supported": True,
                 "env_subdir": "highway_log", "tsn_subdir": "highway_log", "fmt": "excel"},
                {"id": "vs_pdf", "label": "vs TSMIS PDF", "kind": "self", "supported": True,
                 "env_subdir": "highway_log", "other_subdir": "highway_log_pdf"}]
    if row_key == "highway_log_pdf":        # TSMIS PDF (cross-env not coded -> greyed)
        return [env,
                {"id": "tsn", "label": "vs TSN", "kind": "tsn", "supported": True,
                 "env_subdir": "highway_log_pdf", "tsn_subdir": "highway_log", "fmt": "pdf"},
                {"id": "vs_excel", "label": "vs TSMIS Excel", "kind": "self", "supported": True,
                 "env_subdir": "highway_log_pdf", "other_subdir": "highway_log"}]
    return [env,
            {"id": "tsn", "label": "vs TSN", "kind": "tsn", "supported": False,
             "env_subdir": subdir, "tsn_subdir": subdir, "fmt": None}]


def _mode_by_id(modes, mode_id):
    for m in modes:
        if m["id"] == mode_id:
            return m
    return modes[0]                          # default to env


def tsn_capable(row_key):
    """True if the row offers a coded comparison beyond cross-environment (the two
    Highway Log rows). Drives the 'tsn_capable' chip hint."""
    defs = _row_defs()
    if row_key not in defs:
        return False
    _l, subdir, _i, adapter, _hr = defs[row_key]
    return any(m["kind"] != "env" and m["supported"]
               for m in _row_modes(row_key, subdir, adapter))


# --- comparison-output paths + the non-env (TSN/self) counts cache --------- #
def mode_out_path(dest, baseline_key, row_key, cell_key, mode):
    """Where a cell's comparison workbook lives. Cross-env stays under
    comparisons/<baseline>/ (existing); TSN/self modes go to comparisons/tsn/ with
    the mode in the name so flavors coexist."""
    if mode["kind"] == "env":
        return comparison_path(dest, baseline_key, row_key, cell_key)
    return tsn_comparisons_root(dest) / f"{cell_key}_{row_key}_{mode['id']}.xlsx"


def _tsn_results_path(dest):
    return tsn_comparisons_root(dest) / _TSN_RESULTS_FILE


def load_tsn_results(dest):
    """{ "<row>|<mode>": {cell_key: {verdict, diff_cells, one_sided,
    built_at_mtime}} } — the non-env (TSN/self) comparison counts cache."""
    try:
        with open(_tsn_results_path(dest), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record_tsn_result(dest, result_key, cell_key, verdict, diff_cells, one_sided,
                      built_at_mtime):
    data = load_tsn_results(dest)
    data.setdefault(result_key, {})[cell_key] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
    }
    p = _tsn_results_path(dest)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, p)
    except OSError as e:
        log.warning("matrix: could not write TSN results cache %s: %s: %s",
                    p, type(e).__name__, e)


# --- unified per-cell comparison state ------------------------------------- #
def _cmp_state(out_path, sources, rec):
    """{supported, built, mtime, stale, reason, missing_side, verdict, diff_cells,
    one_sided} for one comparison cell. `sources` is the input sides
    [{name, present, mtime}]; STALE when the workbook is missing or any present
    source is newer than it."""
    missing = [s["name"] for s in sources if not s.get("present")]
    missing_side = missing[0] if missing else None
    cmp_m = _safe_mtime(out_path)
    built = cmp_m is not None
    verdict = diff_cells = one_sided = None
    if built and rec and abs(float(rec.get("built_at_mtime", -1)) - cmp_m) < _MTIME_TOL_S:
        verdict = rec.get("verdict")
        diff_cells = rec.get("diff_cells")
        one_sided = rec.get("one_sided")
    if not built:
        stale, reason = True, "missing"
    else:
        newer = [s["name"] for s in sources
                 if s.get("mtime") is not None and s["mtime"] > cmp_m + _MTIME_TOL_S]
        stale = bool(newer)
        reason = ("both_newer" if len(newer) > 1
                  else (f"{newer[0]}_newer" if newer else "fresh"))
    return {"supported": True, "built": built, "mtime": cmp_m, "stale": stale,
            "reason": reason, "missing_side": missing_side, "verdict": verdict,
            "diff_cells": diff_cells, "one_sided": one_sided}


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def matrix_snapshot(dest, baseline_key=BASELINE_DEFAULT, envs=None,
                    env_labels=None, row_defs=None, hidden=None, hidden_envs=None,
                    row_modes=None, tsn_files=None, now=None):
    """The full render model for the matrix. PURE stat — no workbook opened (counts
    come from the caches). Per row, the SELECTED mode (`row_modes`, default 'env')
    decides each cell's comparison; `hidden`/`hidden_envs` drop rows/columns from
    the rendered+refreshed grid (still listed in all_rows/all_envs for the
    toggles). `row_defs` is injectable for tests."""
    now = now if now is not None else time.time()
    all_defs = row_defs if row_defs is not None else _row_defs()
    hidden = set(hidden or [])
    hidden_envs = set(hidden_envs or [])
    row_modes = row_modes or {}
    tsn_files = tsn_files or {}
    rows = {k: v for k, v in all_defs.items() if k not in hidden}
    all_envs = list(envs) if envs is not None else env_keys()
    envs = [e for e in all_envs if e not in hidden_envs]
    env_labels = env_labels or {k: default_env_label(k) for k in all_envs}

    # Resolve each visible row's selected mode + gather the store subdirs whose
    # freshness the cells need (the mode's env side + any 'other' side).
    sel, needed = {}, set()
    for row_key, (label, subdir, _idx, adapter, _hr) in rows.items():
        mode = _mode_by_id(_row_modes(row_key, subdir, adapter),
                           row_modes.get(row_key, "env"))
        sel[row_key] = mode
        needed.add(mode.get("env_subdir", subdir))
        if mode.get("other_subdir"):
            needed.add(mode["other_subdir"])
    ages = report_library.cell_ages(dest, [(sd, sd) for sd in needed], envs, now=now)
    results = load_results(dest, baseline_key)
    tsn_results = load_tsn_results(dest)
    _absent = {"present": False, "mtime": None, "age_seconds": None}

    cells, modes_sel, modes_avail, tsn_meta = {}, {}, {}, {}
    for row_key, (label, subdir, _idx, adapter, _hr) in rows.items():
        mode = sel[row_key]
        modes_sel[row_key] = mode["id"]
        modes_avail[row_key] = [{"id": m["id"], "label": m["label"],
                                 "kind": m["kind"], "supported": m["supported"]}
                                for m in _row_modes(row_key, subdir, adapter)]
        env_subdir = mode.get("env_subdir", subdir)
        src = None
        if mode["kind"] == "tsn":
            src = (tsn_source(dest, mode["tsn_subdir"], tsn_files.get(mode["tsn_subdir"]))
                   if mode["supported"] else {"kind": "none"})
            tsn_meta[row_key] = {"supported": mode["supported"], "fmt": mode.get("fmt"),
                                 "source_kind": src.get("kind"), "source_path": src.get("path"),
                                 "pdf_count": src.get("pdf_count"),
                                 "tsn_subdir": mode["tsn_subdir"],
                                 "file": tsn_files.get(mode["tsn_subdir"]),
                                 "input_dir": str(tsn_input_root(dest, mode["tsn_subdir"]))}
        per = {}
        for env in envs:
            export = ages.get(env, {}).get(env_subdir, _absent)
            is_baseline = (mode["kind"] == "env" and env == baseline_key)
            if not mode["supported"]:
                cmp = {"supported": False}
            elif is_baseline:
                cmp = None
            elif mode["kind"] == "env":
                cmp = comparison_state(dest, baseline_key, row_key, env, env_subdir,
                                       ages, results)
            elif mode["kind"] == "tsn":
                rec = (tsn_results.get(f"{row_key}|{mode['id']}", {}) or {}).get(env)
                sources = [{"name": "cell", "present": export["present"], "mtime": export["mtime"]},
                           {"name": "tsn",
                            "present": src.get("kind") in ("file", "consolidated"),
                            "mtime": src.get("mtime")}]
                cmp = _cmp_state(mode_out_path(dest, baseline_key, row_key, env, mode),
                                 sources, rec)
            else:                            # self: TSMIS PDF vs Excel
                other = ages.get(env, {}).get(mode["other_subdir"], _absent)
                rec = (tsn_results.get(f"{row_key}|{mode['id']}", {}) or {}).get(env)
                sources = [{"name": "cell", "present": export["present"], "mtime": export["mtime"]},
                           {"name": "other", "present": other["present"], "mtime": other["mtime"]}]
                cmp = _cmp_state(mode_out_path(dest, baseline_key, row_key, env, mode),
                                 sources, rec)
            cell = {"export": export, "is_baseline": is_baseline, "cmp": cmp}
            if mode["kind"] == "env":
                cell["comparison"] = cmp     # back-compat alias for the Stage-A UI
            per[env] = cell
        cells[row_key] = per

    return {
        "dest": str(dest),
        "baseline": baseline_key,
        "rows": list(rows.keys()),
        "row_labels": {k: rows[k][0] for k in rows},
        # Every matrix row (visible or not) for the toggle chips; `tsn_capable`
        # marks the rows with a coded comparison beyond cross-env.
        "all_rows": [{"key": k, "label": all_defs[k][0],
                      "tsn_capable": tsn_capable(k)} for k in all_defs],
        "hidden": sorted(hidden),
        "modes": modes_sel,            # row_key -> selected mode id
        "row_modes": modes_avail,      # row_key -> [{id,label,kind,supported}]
        "tsn_meta": tsn_meta,          # row_key -> TSN source summary (tsn mode only)
        "envs": list(envs),
        "all_envs": all_envs,
        "hidden_envs": sorted(hidden_envs),
        "env_labels": env_labels,
        "cells": cells,
    }


# --------------------------------------------------------------------------- #
# orchestration: build one cell's comparison (pure delegation to compare_env)
# --------------------------------------------------------------------------- #
def build_cell_comparison(dest, baseline_key, row_key, cell_key, events,
                          confirm_overwrite=None, row_defs=None):
    """Compare (row's report, cell env) against the baseline env, writing the
    VALUES workbook to comparison_path(...), and record its verdict + discrepancy
    counts in the cache. Pure delegation to the adapter's compare_folders — the
    comparison engine is untouched. Returns the ConsolidateResult.

    Raises ValueError on an unknown row_key or a baseline cell (nothing to
    compare); compare_folders itself returns a clean error result when a side
    hasn't been exported yet."""
    rows = row_defs if row_defs is not None else _row_defs()
    if row_key not in rows:
        raise ValueError(f"unknown matrix row: {row_key}")
    if cell_key == baseline_key:
        raise ValueError("the baseline column has nothing to compare against")
    _label, subdir, _idx, adapter, has_route = rows[row_key]

    dest = Path(dest)
    out_path = comparison_path(dest, baseline_key, row_key, cell_key)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # side A = the cell env, side B = the baseline (labels read "ARS-TEST vs SSOR-PROD").
    result = adapter.compare_folders(
        dest / cell_key, dest / baseline_key, out_path,
        events=events, confirm_overwrite=confirm_overwrite or (lambda _p: True),
        mode="values")

    if result.status == "ok" and out_path.exists():
        diff_cells, one_sided = read_counts(out_path, has_route)
        try:
            built_at = out_path.stat().st_mtime
        except OSError:
            built_at = None
        record_result(dest, baseline_key, row_key, cell_key, result.verdict,
                      diff_cells, one_sided, built_at)
    return result


def cells_to_rebuild(snapshot, scope="stale", row=None, env=None):
    """[(row_key, cell_key, mode_id)] to (re)compute, honoring each row's SELECTED
    mode. scope='all' = every comparable cell (both sides present); 'stale' = only
    missing/stale ones. Optional `row` / `env` filters drive the per-row and
    per-column refresh buttons. Skips the env-mode baseline column, unsupported
    (greyed) modes, and cells with a missing input side."""
    modes = snapshot.get("modes", {})
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        mode_id = modes.get(row_key, "env")
        for ev in snapshot["envs"]:
            if env and ev != env:
                continue
            cmp = snapshot["cells"][row_key][ev].get("cmp")
            if cmp is None:                      # env-mode baseline column
                continue
            if not cmp.get("supported") or cmp.get("missing_side"):
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((row_key, ev, mode_id))
    return todo


# --------------------------------------------------------------------------- #
# orchestration: consolidate the env's store folder(s) and diff via the existing
# (untouched) comparison adapters. compare_highway_log / compare_highway_log_pdf
# are file-vs-file, so the per-route env folders are consolidated first.
# --------------------------------------------------------------------------- #
def _consolidate_store_folder(subdir, env_dir, out_path, events):
    """Consolidate one Export-Everything store folder (<env>/<subdir>/, per-route
    files) into a single workbook via the report's existing consolidator (with its
    additive input_dir/out_path override). Highway Log Excel + PDF only."""
    out_path = Path(out_path)
    if subdir == "highway_log":
        import consolidate_highway_log as _m      # lazy
        _m.consolidate(events=events, confirm_overwrite=lambda _p: True,
                       input_dir=Path(env_dir), out_path=out_path)
    elif subdir == "highway_log_pdf":
        import consolidate_tsmis_highway_log_pdf as _m   # pdfplumber — lazy
        conv = out_path.parent / f".{out_path.stem}_conv"
        try:
            _m.consolidate(events=events, confirm_overwrite=lambda _p: True,
                           input_dir=Path(env_dir), out_path=out_path,
                           converted_dir=conv)
        finally:
            shutil.rmtree(conv, ignore_errors=True)
    else:
        raise ValueError(f"no store consolidator for {subdir}")


def consolidate_tsn_pdfs(dest, subdir, events=None, confirm_overwrite=None):
    """Build a consolidated TSN workbook FROM the district PDFs the user dropped in
    <dest>/_tsn_input/<subdir>/, writing it back there so the next tsn_source()
    finds it. TSN is the SAME district-PDF set for both Highway Log flavors, so
    only the 'highway_log' TSN drop folder is handled. Returns the out path."""
    if subdir != "highway_log":
        raise ValueError(f"no TSN PDF consolidator for {subdir}")
    import consolidate_tsn_highway_log as _ctsn   # pdfplumber — lazy
    in_dir = tsn_input_root(dest, subdir)
    out_path = in_dir / "tsn_highway_log_consolidated.xlsx"
    _ctsn.consolidate(events=events, confirm_overwrite=confirm_overwrite or (lambda _p: True),
                      input_dir=in_dir, out_path=out_path)
    return out_path


def build_comparison(dest, row_key, cell_key, mode_id, baseline_key, events,
                     tsn_files=None, confirm_overwrite=None, row_defs=None):
    """(Re)build one cell's comparison for the row's SELECTED mode, write the VALUES
    workbook, and cache its counts. Dispatches to the existing comparison adapters
    (never edits them). Returns the ConsolidateResult. Raises ValueError for an
    unknown row or an unsupported/greyed mode; an absent input side yields the
    adapter's clean error result."""
    rows = row_defs if row_defs is not None else _row_defs()
    if row_key not in rows:
        raise ValueError(f"unknown matrix row: {row_key}")
    _label, subdir, _idx, adapter, _hr = rows[row_key]
    mode = _mode_by_id(_row_modes(row_key, subdir, adapter), mode_id)
    if not mode["supported"]:
        raise ValueError(f"no comparison for {row_key} / {mode['id']}")

    if mode["kind"] == "env":
        return build_cell_comparison(dest, baseline_key, row_key, cell_key, events,
                                     confirm_overwrite=confirm_overwrite, row_defs=rows)

    dest = Path(dest)
    out_path = mode_out_path(dest, baseline_key, row_key, cell_key, mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tsn_files = tsn_files or {}
    tmps = []
    try:
        if mode["kind"] == "tsn":
            src = tsn_source(dest, mode["tsn_subdir"], tsn_files.get(mode["tsn_subdir"]))
            if src.get("kind") not in ("file", "consolidated"):
                raise ValueError("no consolidated TSN workbook available")
            tmp = out_path.parent / f".{cell_key}_{row_key}_{mode['id']}_a.tmp.xlsx"
            tmps.append(tmp)
            _consolidate_store_folder(mode["env_subdir"],
                                      dest / cell_key / mode["env_subdir"], tmp, events)
            import compare_highway_log as _cmp_x          # lazy — untouched adapters
            import compare_highway_log_pdf as _cmp_p
            cmp_mod = _cmp_x if mode.get("fmt") == "excel" else _cmp_p.TSMIS_PDF_VS_TSN
            result = cmp_mod.compare(tmp, src["path"], out_path, events=events,
                                     confirm_overwrite=confirm_overwrite or (lambda _p: True),
                                     mode="values")
        else:                                # self: TSMIS PDF vs Excel
            tmp_a = out_path.parent / f".{cell_key}_{row_key}_{mode['id']}_a.tmp.xlsx"
            tmp_b = out_path.parent / f".{cell_key}_{row_key}_{mode['id']}_b.tmp.xlsx"
            tmps += [tmp_a, tmp_b]
            _consolidate_store_folder(mode["env_subdir"],
                                      dest / cell_key / mode["env_subdir"], tmp_a, events)
            _consolidate_store_folder(mode["other_subdir"],
                                      dest / cell_key / mode["other_subdir"], tmp_b, events)
            # the adapter fixes PDF=side A, Excel=side B regardless of the row.
            pdf_tmp = tmp_a if mode["env_subdir"] == "highway_log_pdf" else tmp_b
            excel_tmp = tmp_b if mode["env_subdir"] == "highway_log_pdf" else tmp_a
            import compare_highway_log_pdf as _cmp_p
            result = _cmp_p.TSMIS_PDF_VS_EXCEL.compare(
                pdf_tmp, excel_tmp, out_path, events=events,
                confirm_overwrite=confirm_overwrite or (lambda _p: True), mode="values")
    finally:
        for t in tmps:
            try:
                t.unlink()
            except OSError:
                pass

    if result.status == "ok" and out_path.exists():
        diff_cells, one_sided = read_counts(out_path, has_route=True)
        record_tsn_result(dest, f"{row_key}|{mode['id']}", cell_key, result.verdict,
                          diff_cells, one_sided, _safe_mtime(out_path))
    return result

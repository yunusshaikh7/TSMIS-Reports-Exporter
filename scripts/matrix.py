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
    return {"built": built, "mtime": cmp_m, "stale": stale, "reason": reason,
            "missing_side": missing_side, "verdict": verdict,
            "diff_cells": diff_cells, "one_sided": one_sided}


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def matrix_snapshot(dest, baseline_key=BASELINE_DEFAULT, envs=None,
                    env_labels=None, row_defs=None, hidden=None, now=None):
    """The full render model for the matrix. PURE stat — no workbook is opened
    (counts come from the cache). `row_defs` is injectable for tests; otherwise
    derived from the registry. `hidden` is the set of row keys the user has
    toggled OFF — they're dropped from the rendered/refreshed rows but still
    listed in `all_rows` so the UI can offer them as toggle chips."""
    now = now if now is not None else time.time()
    all_defs = row_defs if row_defs is not None else _row_defs()
    hidden = set(hidden or [])
    rows = {k: v for k, v in all_defs.items() if k not in hidden}
    envs = envs if envs is not None else env_keys()
    env_labels = env_labels or {k: default_env_label(k) for k in envs}
    report_pairs = [(label, subdir) for label, subdir, *_ in rows.values()]
    ages = report_library.cell_ages(dest, report_pairs, envs, now=now)
    results = load_results(dest, baseline_key)

    cells = {}
    for row_key, (label, subdir, _idx, _adapter, _hr) in rows.items():
        per = {}
        for env in envs:
            export = ages.get(env, {}).get(subdir, {"present": False,
                                                    "mtime": None,
                                                    "age_seconds": None})
            is_baseline = (env == baseline_key)
            comp = None
            if not is_baseline:
                comp = comparison_state(dest, baseline_key, row_key, env, subdir,
                                        ages, results)
            per[env] = {"export": export, "is_baseline": is_baseline,
                        "comparison": comp}
        cells[row_key] = per

    return {
        "dest": str(dest),
        "baseline": baseline_key,
        "rows": list(rows.keys()),
        "row_labels": {k: rows[k][0] for k in rows},
        # Every matrix row (visible or not) so the UI can render toggle chips.
        "all_rows": [{"key": k, "label": all_defs[k][0]} for k in all_defs],
        "hidden": sorted(hidden),
        "envs": list(envs),
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


def cells_to_rebuild(snapshot, scope="stale"):
    """[(row_key, cell_key)] for non-baseline cells to (re)compute. scope='all'
    = every cell where BOTH sides are exported; scope='stale' = only those whose
    comparison is missing or stale (and both sides present). A side that was
    never exported is skipped (can't compare)."""
    baseline = snapshot["baseline"]
    todo = []
    for row_key in snapshot["rows"]:
        for env in snapshot["envs"]:
            if env == baseline:
                continue
            comp = snapshot["cells"][row_key][env]["comparison"]
            if comp is None or comp.get("missing_side"):
                continue                         # a side isn't exported -> skip
            if scope == "all" or comp.get("stale"):
                todo.append((row_key, env))
    return todo

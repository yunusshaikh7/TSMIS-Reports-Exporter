"""Compare-tab "PDF vs Excel Matrix" engine (the day-keyed self-consistency matrix).

The sibling of the by-day vs-TSN matrix (`day_matrix`), but for the internal TSMIS
PDF-vs-Excel consistency check (M2-B, v0.31.0): rows = the five dual-edition report
families, columns = exported DAYS the user adds, each cell = that day's PDF export
self-compared vs its Excel export. Both editions are consolidated from the SAME run
folder, so the two sides are same-day by construction — no TSN dataset and no
cross-environment, which is why this engine is much simpler than `day_matrix`.

Born on the `report_catalog.MATRIX` wiring (M2-A): the row set (every fmt=='pdf'
row), each family's two edition subdirs (row.row_key + row.self_other), and the self
comparator (`matrix._pdf_self_comparator`) all derive from the catalog — this matrix
is the "real addition" that proves that structure.

Own store root output/comparisons/pdf-vs-excel-by-day/, own results cache + attempts
overlay, the M1-C self-identifying names, the M1-B ETAs/logging, and the shared
queue. The per-cell build rides the SAME shared primitives the Everything matrix's
self mode uses (`matrix._ensure_consolidated` / `matrix._pdf_self_comparator` /
`matrix._settle_formulas_twin` / `matrix._published_comparison_result`) — never a
second comparison implementation.

Console-free like the rest of the core: progress via the Events sink, exceptions
raised — never print/input/sys.exit. Only gui_api / gui_worker drive it.
"""
import json
import logging
import os
import time
from pathlib import Path

import artifact_store
import cache_envelope
import consolidation_meta
import matrix
import report_catalog
from paths import (comparisons_root, day_source_dir, list_output_days,
                   parse_run_folder, today_str)

log = logging.getLogger("tsmis.pve_matrix")

SOURCE_DEFAULT = "ssor-prod"
PVE_DIRNAME = "pdf-vs-excel-by-day"          # under output/comparisons/
_RESULTS_FILE = "_results.json"
_CACHE_IDENTITY = "pdf-vs-excel-by-day"


# --------------------------------------------------------------------------- #
# rows + sources
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _pve_rows():
    """[(row_key, label, pdf_subdir, excel_subdir)] — one row per dual-edition
    family. `row_key` is the PDF subdir (unique, and what `_pdf_self_comparator`
    keys on); `label` is the family's report label; the two subdirs are the editions
    the cell self-compares. Derived from the fmt=='pdf' rows of report_catalog.MATRIX
    (M2-A), so a new dual-edition family joins here automatically once wired."""
    labels = {e.key: e.label for e in report_catalog.EXPORT}
    out = []
    for m in report_catalog.matrix_rows_meta():
        if m.fmt != "pdf" or m.self_other is None:
            continue
        out.append((m.row_key, labels.get(m.self_other, m.row_key),
                    m.row_key, m.self_other))
    return out


def _row_lookup():
    return {r[0]: r for r in _pve_rows()}


# --------------------------------------------------------------------------- #
# paths + the results cache
# --------------------------------------------------------------------------- #
def pve_root():
    return comparisons_root() / PVE_DIRNAME


def day_folder_name(date, source):
    return f"{date} {source}"


def day_out_path(date, source, row_key):
    """The self-check VALUES workbook for one (day, family). The basename embeds the
    family + day + source (M1-C) so two days' self-checks of one family can be open
    in Excel at once and a lifted file still says what it is."""
    fam = row_key[:-4] if row_key.endswith("_pdf") else row_key
    return (pve_root() / day_folder_name(date, source)
            / f"{fam}_pdf_vs_excel {date} {source}.xlsx")


def _results_path():
    return pve_root() / _RESULTS_FILE


def load_results():
    """{ "<date source>|<row>": {verdict, diff_cells, one_sided, built_at_mtime,
    completion, generation_id, input_fingerprint, source_identities,
    producer_versions} } — the by-day self-check counts cache."""
    p = _results_path()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return cache_envelope.unwrap(data, output_identity=_CACHE_IDENTITY)
    except OSError:  # silent-ok: no cache file yet (first run) — the empty map is the correct state
        return {}                            # not written yet (first run) — expected
    except ValueError as e:                  # corrupt JSON: surface it, then degrade
        log.warning("pve_matrix: corrupt results cache %s (%s: %s); treating as empty",
                    _results_path(), type(e).__name__, e)
        return {}


def record_result(date, source, row_key, verdict, diff_cells, one_sided,
                  built_at_mtime, completion=None, input_fingerprint=None,
                  source_identities=None, generation_id=None,
                  producer_versions=None, commit_guard=None):
    data = load_results()
    data[f"{day_folder_name(date, source)}|{row_key}"] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
        "completion": completion,        # P1-R01: partial inputs flagged durably
        "generation_id": generation_id,
        "input_fingerprint": input_fingerprint,
        "source_identities": source_identities or {},
        "producer_versions": producer_versions,
    }
    p = _results_path()
    tmp = p.with_name(p.name + ".tmp")

    def _require_guard(path, action):
        if not consolidation_meta.guard_allows(commit_guard, path):
            raise ValueError(
                "A PDF-vs-Excel matrix input or destination changed before the "
                f"{action}; refresh the comparison.")

    try:
        _require_guard(p.parent, "cache directory write")
        _require_guard(p, "cache write")
        _require_guard(tmp, "cache temporary write")
        p.parent.mkdir(parents=True, exist_ok=True)
        _require_guard(p, "cache write")
        _require_guard(tmp, "cache temporary write")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache_envelope.wrap(data, output_identity=_CACHE_IDENTITY), f)
        _require_guard(p, "cache publication")
        _require_guard(tmp, "cache publication")
        os.replace(tmp, p)
    except OSError as e:
        log.warning("pve_matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)
        raise ValueError(
            "The comparison workbook was created, but its PDF-vs-Excel matrix "
            "result cache could not be safely published. Refresh the cell.") from e


# --------------------------------------------------------------------------- #
# filesystem helpers
# --------------------------------------------------------------------------- #
def _folder_newest_mtime(p):
    """Newest report-data-file mtime in a folder, or None when empty/absent.
    Only a real .xlsx/.pdf export counts (CMP-AUD-083)."""
    newest = None
    try:
        entries = list(Path(p).iterdir())
    except OSError:  # silent-ok: an absent/unreadable export folder has no mtime — None IS the answer
        return None
    for e in entries:
        try:
            if e.is_file() and artifact_store.is_report_data_file(e.name):
                m = e.stat().st_mtime
                if newest is None or m > newest:
                    newest = m
        except OSError:  # silent-ok: a locked/vanished entry contributes nothing to the newest mtime
            continue
    return newest


def tsmis_dir(date, source, subdir):
    """The per-route export folder (one edition) the cell reads, resolved to the REAL
    run folder (CMP-AUD-092: a pre-v0.10 bare-date folder is found, not reconstructed)."""
    return day_source_dir(date, source) / subdir


def _edition_subdirs():
    """Every edition subdir any row reads (the 5 PDF + 5 Excel) — the union that
    decides whether a past day has anything worth adding as a column."""
    subs = set()
    for _rk, _label, pdf_sub, excel_sub in _pve_rows():
        subs.add(pdf_sub)
        subs.add(excel_sub)
    return subs


def available_days(source):
    """Dates (newest first) with an export for ANY edition of ANY family for
    `source` — the add-day picker's options. TODAY is always offered (the export-
    less today renders every cell as needs-export)."""
    edition_subs = _edition_subdirs()
    out, seen = [today_str()], {today_str()}
    for name in list_output_days():
        parsed = parse_run_folder(name)
        if not parsed:
            continue
        date, src, env = parsed
        if f"{src}-{env}" != source or date in seen:
            continue
        base = day_source_dir(date, source)
        if any(_folder_newest_mtime(base / sub) is not None for sub in edition_subs):
            seen.add(date)
            out.append(date)
    return out


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def pve_matrix_snapshot(source, days, hidden=None, dest=None, now=None,
                        row_order=None, today=None):
    """Full render model for the PDF-vs-Excel by-day matrix. PURE stat — counts come
    from the cache, no workbook opened. `days` is the ordered date columns; `hidden`
    hides family rows; `row_order` is the user's drag order. `today` (default
    today_str) is the only EXPORTABLE column. Shape-compatible with the by-day
    matrix snapshot (minus tsn_meta) so the GUI shares the render.

    Each cell needs BOTH editions exported that day; a missing edition renders the
    cell not-buildable with the needs-export affordance, honestly (a day where a
    family exported only one edition shows as needs-export)."""
    now = now if now is not None else time.time()
    today = today if today is not None else today_str()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    all_rows = _pve_rows()
    rows = [r for r in all_rows if r[0] not in hidden]
    by_key = {r[0]: r for r in rows}
    rows = [by_key[k] for k in matrix.apply_order(list(by_key.keys()), row_order)]
    results = load_results()
    attempts = matrix.load_attempts(pve_root())

    cells = {}
    for row_key, _label, pdf_sub, excel_sub in rows:
        per = {}
        for date in days:
            pdf_dir = tsmis_dir(date, source, pdf_sub)
            excel_dir = tsmis_dir(date, source, excel_sub)
            pdf_m = _folder_newest_mtime(pdf_dir)
            excel_m = _folder_newest_mtime(excel_dir)
            # "export" (for the shared render's needs-export gate) is present only
            # when BOTH editions are — a self-check needs both sides.
            both = pdf_m is not None and excel_m is not None
            newest = max([m for m in (pdf_m, excel_m) if m is not None], default=None)
            export = {"present": both, "mtime": newest,
                      "age_seconds": (now - newest) if newest is not None else None,
                      "pdf_present": pdf_m is not None,
                      "excel_present": excel_m is not None}
            rec = results.get(f"{day_folder_name(date, source)}|{row_key}")
            srcs = [{"name": "pdf", "present": pdf_m is not None, "mtime": pdf_m},
                    {"name": "excel", "present": excel_m is not None, "mtime": excel_m}]
            cmp = matrix._cmp_state(day_out_path(date, source, row_key), srcs, rec,
                                    fp_folders=(pdf_dir, excel_dir))
            attempt = matrix._last_attempt_for(
                attempts, f"{row_key}|{source}", date, cmp)
            if attempt is not None:
                cmp["last_attempt"] = attempt
            per[date] = {"export": export, "cmp": cmp}
        cells[row_key] = per

    return {
        "source": source,
        "sources": [{"key": k, "label": matrix.default_env_label(k)} for k in sources()],
        "days": days,
        "today": today,
        "rows": [r[0] for r in rows],
        "row_labels": {r[0]: r[1] for r in rows},
        "row_supported": {r[0]: True for r in rows},
        "all_rows": [{"key": r[0], "label": r[1], "supported": True} for r in all_rows],
        "hidden": sorted(hidden),
        "cells": cells,
    }


# --------------------------------------------------------------------------- #
# the scoped rebuild list + one-cell build (shared self primitives)
# --------------------------------------------------------------------------- #
def cells_to_rebuild(snapshot, scope="stale", row=None, date=None):
    """[(date, row_key)] to (re)build, honoring scope. 'all' = every cell with BOTH
    editions present; 'stale' = only missing/stale ones. Optional `row`/`date`
    filters drive the per-row / per-column rebuilds. Skips cells missing an edition."""
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        for d in snapshot["days"]:
            if date and d != date:
                continue
            cmp = snapshot["cells"][row_key][d]["cmp"]
            if not matrix.cell_buildable(cmp):    # CMP-AUD-103: shared predicate
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((d, row_key))
    return todo


def build_pve_cell(source, date, row_key, dest, events, confirm_overwrite=None,
                   force_consolidate=False, also_formulas=False, commit_guard=None):
    """Build ONE (day, family) PDF-vs-Excel self comparison: consolidate that day's
    PDF export + Excel export (reusing each day folder's persistent consolidated
    unless stale or `force_consolidate`), self-compare via the family's PDF-vs-Excel
    adapter, write the VALUES workbook to the by-day store, and cache its counts.

    Rides the SAME shared primitives the Everything matrix's self mode uses — no
    second self-comparison path. Returns the ConsolidateResult. Raises ValueError on
    an unknown row or an invalid date/source. (`dest` is unused — the self-check has
    no TSN dataset — but kept in the signature so the worker calls every matrix build
    uniformly.)"""
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown PDF-vs-Excel matrix row: {row_key}")
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(
            f"invalid date/source for the PDF-vs-Excel matrix: {date!r} / {source!r}")
    _k, _label, pdf_sub, excel_sub = rows[row_key]
    out_path = day_out_path(date, source, row_key)

    pdf_dir = tsmis_dir(date, source, pdf_sub)
    excel_dir = tsmis_dir(date, source, excel_sub)
    # CMP-AUD-098: capture both input folders' identity BEFORE the consolidate→
    # compare chain reads them (same folders/order as the snapshot fingerprints).
    fp_folders = (pdf_dir, excel_dir)
    fp_before = matrix._cell_input_fingerprint(*fp_folders)

    # Consolidate each edition from its day folder (persistent, reused unless stale),
    # then run the family's PDF-vs-Excel adapter — the shared self path.
    side_pdf, _comp_pdf = matrix._ensure_consolidated(
        pdf_dir, pdf_sub, events, force_consolidate, commit_guard=commit_guard)
    side_excel, _comp_excel = matrix._ensure_consolidated(
        excel_dir, excel_sub, events, force_consolidate, commit_guard=commit_guard)
    self_cmp = matrix._pdf_self_comparator(pdf_sub)
    result = self_cmp.compare(
        side_pdf, side_excel, out_path, events=events,
        confirm_overwrite=confirm_overwrite or (lambda _p: True),
        mode="values", commit_guard=commit_guard)
    if result.status == "ok" and out_path.exists():
        # CMP-AUD-082: refresh the live-formulas twin, or clear a stale prior one.
        matrix._settle_formulas_twin(
            lambda fp: self_cmp.compare(
                side_pdf, side_excel, fp, events=events,
                confirm_overwrite=lambda _p: True, mode="formulas",
                commit_guard=commit_guard),
            out_path, also_formulas, events,
            source_paths=(side_pdf, side_excel), commit_guard=commit_guard)
        published = matrix._published_comparison_result(out_path, result)
        typed = published.comparison_outcome
        diff_cells = typed.counts.differing_cells
        one_sided = (typed.counts.side_a_only_rows + typed.counts.side_b_only_rows)
        record_result(
            date, source, row_key, typed.verdict, diff_cells, one_sided,
            matrix._safe_mtime(out_path), completion=typed.completion,
            input_fingerprint=matrix._fingerprint_for_record(
                fp_before, fp_folders, out_path.name, events),
            generation_id=published.artifact_generation.generation_id,
            producer_versions=matrix.producer_identity(),
            commit_guard=commit_guard)
    return result

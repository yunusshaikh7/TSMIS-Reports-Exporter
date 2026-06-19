"""Single source of truth for the report registry.

Every report type appears here exactly once, so adding one is a one-place change
on the Python side: both the GUI (Export / Consolidate / Compare tabs,
`gui_api.py`) and the console multi-exporter (`export_multi.py`) read these
lists. (The `.bat`
menus are static text and are still edited by hand — see CLAUDE.md "Adding a New
Report Type".)

Kept import-light and console-free: it only pulls in the thin `export_*`
`ReportSpec` objects and the `consolidate_*` modules, so importing it never
launches a browser or does any I/O.
"""
from export_ramp_summary import SPEC as _RAMP_SUMMARY_SPEC
from export_ramp_detail import SPEC as _RAMP_DETAIL_SPEC
from export_highway_sequence import SPEC as _HIGHWAY_SEQ_SPEC
from export_highway_log import SPEC as _HIGHWAY_LOG_SPEC
from export_highway_log_pdf import SPEC as _HIGHWAY_LOG_PDF_SPEC
from export_intersection_summary import SPEC as _INT_SUMMARY_SPEC
from export_intersection_detail import SPEC as _INT_DETAIL_SPEC

import consolidate_ramp_summary as _c_ramp_summary
import consolidate_ramp_detail as _c_ramp_detail
import consolidate_highway_sequence as _c_highway_seq
import consolidate_highway_log as _c_highway_log
import consolidate_tsn_highway_log as _c_tsn_highway_log
import consolidate_tsmis_highway_log_pdf as _c_tsmis_highway_log_pdf

import compare_env as _cmp_env
import compare_highway_log as _cmp_highway_log
import compare_highway_log_pdf as _cmp_highway_log_pdf

# Export tab / multi-export: (menu label, format hint, ReportSpec).
# Order here is the display order in the GUI and the numbering in the console menu.
EXPORT_REPORTS = [
    ("TSAR: Ramp Summary", "PDF", _RAMP_SUMMARY_SPEC),
    ("TSAR: Ramp Detail", "Excel", _RAMP_DETAIL_SPEC),
    ("Highway Sequence Listing", "Excel", _HIGHWAY_SEQ_SPEC),
    ("Highway Log", "Excel", _HIGHWAY_LOG_SPEC),
    # Same "Highway Log" dropdown option, saved as a PDF via the page's Print
    # layout (hl_printAll) instead of the Excel Export button. Export-only (the
    # consolidator reads the .xlsx export; no consolidation for the PDF).
    ("Highway Log (PDF)", "PDF", _HIGHWAY_LOG_PDF_SPEC),
    # Export-only for now (no consolidation/comparison support yet). Labels
    # verified against the live page source: NO "TSAR:" prefix, and Summary
    # is an Excel export like Detail. The env check reads the dropdown for
    # every row here, so a label drift shows up there as "missing".
    ("Intersection Summary", "Excel", _INT_SUMMARY_SPEC),
    ("Intersection Detail", "Excel", _INT_DETAIL_SPEC),
]

# Consolidate tab: (menu label, module). Same order as above. Each module
# exposes consolidate(events, confirm_overwrite, day=None) plus
# input_dir_for(day) / out_path_for(day) — paths are day-dependent now that
# exports are grouped into output/<YYYY-MM-DD>/ folders, so the registry hands
# out the module rather than a single precomputed OUT_PATH.
CONSOLIDATE_REPORTS = [
    ("TSAR: Ramp Summary", _c_ramp_summary),
    ("TSAR: Ramp Detail", _c_ramp_detail),
    ("Highway Sequence Listing", _c_highway_seq),
    # The three Highway Log consolidators are grouped here, TSMIS before TSN.
    # Labels are SOURCE-explicit and parallel — "<system> Highway Log (<format>)"
    # — so the bare "Highway Log" can't be mistaken for one of the others.
    #   Input = the TSMIS "Highway Log" Excel export, output/<run>/highway_log/ (day-aware).
    ("TSMIS Highway Log (Excel)", _c_highway_log),
    #   Input = the TSMIS "Highway Log (PDF)" export, output/<run>/highway_log_pdf/
    #   (day-aware, this app's own export -- NOT a dropped folder) -- parsed into
    #   the SAME 31-column format as the Excel export, then combined (the accurate
    #   substitute for the buggy vendor Excel).
    ("TSMIS Highway Log (PDF)", _c_tsmis_highway_log_pdf),
    #   Input = TSN district PDFs the user drops into input/tsn_highway_log/ (these
    #   come from OUTSIDE the app, so this one keeps an input folder + day ignored).
    ("TSN Highway Log (PDF)", _c_tsn_highway_log),
]

# Compare tab SUB-TABS (GUI): the comparison types are grouped onto these sub-tabs
# within the Compare pane, in this order (the FIRST is the default). Every Highway
# Log comparison lives on the "Highway Log" sub-tab (v0.14.1) — cross-env HL,
# TSMIS-vs-TSN and the two PDF-sourced ones — so they're in one place instead of
# spread across the old env / TSMIS-vs-TSN / PDF split; the plain cross-environment
# report comparisons (Ramp Summary/Detail, Highway Sequence) stay on
# "Cross-environment". A row's `group` (below) names its sub-tab.
COMPARE_GROUPS = [
    ("env", "Cross-environment"),
    ("highway_log", "Highway Log"),
]

# Compare registry: (menu label, module/adapter, input kind, group). The GUI's
# per-sub-tab type lists are generated from this; the kind decides which inputs the
# pane asks for:
#   "files"   -- two workbooks; the module exposes
#                compare(path_a, path_b, out_path, events, confirm_overwrite,
#                mode) -> ConsolidateResult and suggest_name(path_a).
#   "folders" -- two export run folders; the adapter exposes
#                compare_folders(dir_a, dir_b, out_path, events,
#                confirm_overwrite, mode) -> ConsolidateResult and
#                suggest_name(dir_a, dir_b). Used by the cross-environment
#                comparisons (compare_env.py) -- no consolidation needed
#                first; the per-route files are read straight from both
#                run folders.
# `group` is one of COMPARE_GROUPS' ids (its sub-tab). Selection is by index, so
# this order is what the UI radios and start_compare* calls key on.
COMPARE_REPORTS = [
    ("TSAR: Ramp Summary — between environments", _cmp_env.RAMP_SUMMARY, "folders", "env"),
    ("TSAR: Ramp Detail — between environments", _cmp_env.RAMP_DETAIL, "folders", "env"),
    ("Highway Sequence Listing — between environments", _cmp_env.HIGHWAY_SEQUENCE, "folders", "env"),
    ("Highway Log — between environments", _cmp_env.HIGHWAY_LOG, "folders", "highway_log"),
    ("Highway Log — TSMIS vs TSN", _cmp_highway_log, "files", "highway_log"),
    # Both sides parsed from PDFs (accurate replacement for the Excel-based row
    # above — the "(PDF)" on BOTH sides makes the PDF-vs-PDF nature explicit),
    # and the PDF data diffed against the vendor Excel to expose its bug.
    ("Highway Log — TSMIS (PDF) vs TSN (PDF)", _cmp_highway_log_pdf.TSMIS_PDF_VS_TSN,
     "files", "highway_log"),
    ("Highway Log — TSMIS (PDF) vs TSMIS (Excel)",
     _cmp_highway_log_pdf.TSMIS_PDF_VS_EXCEL, "files", "highway_log"),
]

# B2 (auto-consolidate on export finish): which consolidate module handles each
# EXPORTABLE report, keyed by the export ReportSpec's output subdir so this can't
# drift from the lists above. Intersection Summary / Detail are export-only and
# have no consolidator (absent from the map -> None).
_CONSOLIDATOR_BY_SUBDIR = {
    _RAMP_SUMMARY_SPEC.subdir: _c_ramp_summary,
    _RAMP_DETAIL_SPEC.subdir: _c_ramp_detail,
    _HIGHWAY_SEQ_SPEC.subdir: _c_highway_seq,
    _HIGHWAY_LOG_SPEC.subdir: _c_highway_log,
}


def consolidator_for_spec(spec):
    """The consolidate module for an export ReportSpec, or None when the report
    is export-only (Intersection Summary / Detail). Keyed on the spec's output
    subdir."""
    return _CONSOLIDATOR_BY_SUBDIR.get(getattr(spec, "subdir", None))


def matrix_rows():
    """The cross-environment comparison MATRIX rows, derived once from the
    registry so they can't drift: every "env"-group "folders" comparison (Ramp
    Summary / Ramp Detail / Highway Sequence), mapped to its export ReportSpec so
    a matrix cell can be re-exported. Returns
    [(row_key, label, subdir, export_idx, adapter)] in registry order.
    Intersection reports have no cross-env adapter, so they never appear (this is
    the same intent as the app-wide intersection disable)."""
    by_subdir = {spec.subdir: i for i, (_l, _f, spec) in enumerate(EXPORT_REPORTS)}
    rows = []
    for _label, adapter, kind, group in COMPARE_REPORTS:
        if kind != "folders" or group != "env":
            continue
        subdir = adapter.subdir
        idx = by_subdir.get(subdir)
        disp = EXPORT_REPORTS[idx][0] if idx is not None else adapter.REPORT_NAME
        rows.append((adapter.key, disp, subdir, idx, adapter))
    return rows

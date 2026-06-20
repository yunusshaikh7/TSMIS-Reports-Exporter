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
import consolidate_intersection_detail as _c_int_detail
import consolidate_intersection_summary as _c_int_summary

import compare_env as _cmp_env
import compare_highway_log as _cmp_highway_log
import compare_highway_log_pdf as _cmp_highway_log_pdf
import compare_ramp_detail_tsn as _cmp_ramp_detail_tsn
import compare_ramp_summary_tsn as _cmp_ramp_summary_tsn
import compare_intersection_summary_tsn as _cmp_int_summary_tsn
import compare_intersection_detail_tsn as _cmp_int_detail_tsn
import compare_highway_sequence_tsn as _cmp_highway_seq_tsn

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
    ("Intersection Summary", _c_int_summary),
    ("Intersection Detail", _c_int_detail),
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
# within the Compare pane, in this order (the FIRST is the default). Two registry
# groups: "env" (Cross-environment — every report's between-environments compare,
# Highway Log included) and "tsn" (vs TSN — the file-based TSMIS-vs-TSN compares;
# Highway Log Excel/PDF today, the other reports plug in in 0.17.0). A THIRD
# sub-tab, the "vs TSN Matrix" (the day-keyed matrix, group "tsn_by_day"), is
# appended by the GUI itself — it is not a registry comparison type. A row's
# `group` (below) names its sub-tab. (v0.16.1 staging: HL's cross-env compare
# moved back to "env" and the "Highway Log" sub-tab became the general "vs TSN".)
COMPARE_GROUPS = [
    ("env", "Cross-environment"),
    ("tsn", "vs TSN"),
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
    # Highway Log's cross-environment compare now sits with the other cross-env
    # reports under "env" (v0.16.1 staging — the old "highway_log" sub-tab became
    # the general "vs TSN" group below).
    ("Highway Log — between environments", _cmp_env.HIGHWAY_LOG, "folders", "env"),
    # Intersection Summary cross-env (v0.17.0): the per-route category-summary sheet
    # is compared the AGGREGATE way (one category-count row per route) — see
    # compare_env.INTERSECTION_SUMMARY. Having a folders/env adapter promotes it from
    # a TSN-only extra row to a full Everything-matrix + by-day matrix row.
    ("TSAR: Intersection Summary — between environments",
     _cmp_env.INTERSECTION_SUMMARY, "folders", "env"),
    # Intersection Detail cross-env (v0.17.0): a flat per-route XLSX, route+PM key —
    # the standard EnvCompare flat path (like Ramp Detail). Promotes it to a full
    # Everything-matrix + by-day matrix row.
    ("TSAR: Intersection Detail — between environments",
     _cmp_env.INTERSECTION_DETAIL, "folders", "env"),
    # vs TSN (file-based). Highway Log Excel/PDF today; 0.17.0 adds the other
    # reports' "<report> — TSMIS vs TSN" rows here once their comparators exist.
    ("Highway Log — TSMIS vs TSN", _cmp_highway_log, "files", "tsn"),
    # Both sides parsed from PDFs (accurate replacement for the Excel-based row —
    # the "(PDF)" on BOTH sides makes the PDF-vs-PDF nature explicit).
    ("Highway Log — TSMIS (PDF) vs TSN (PDF)", _cmp_highway_log_pdf.TSMIS_PDF_VS_TSN,
     "files", "tsn"),
    # TSMIS (PDF) vs TSMIS (Excel) is an internal consistency check (one system,
    # one environment — the PDF export diffed against the vendor Excel to expose its
    # bug), NOT a TSN comparison, so it lives under "env", not "tsn".
    ("Highway Log — TSMIS (PDF) vs TSMIS (Excel)",
     _cmp_highway_log_pdf.TSMIS_PDF_VS_EXCEL, "files", "env"),
    # v0.17.0 vs-TSN comparators (the reference recipe). Appended at the END so the
    # registry indices above are unchanged (selection is by index). Each takes the
    # consolidated TSMIS workbook + the TSN library file ("files" kind, group "tsn").
    ("TSAR: Ramp Detail — TSMIS vs TSN", _cmp_ramp_detail_tsn, "files", "tsn"),
    # Ramp Summary is the AGGREGATE recipe (statewide category counts, not per-row):
    # TSMIS consolidated workbook summed vs the TSN statewide PDF, keyed on category.
    ("TSAR: Ramp Summary — TSMIS vs TSN", _cmp_ramp_summary_tsn, "files", "tsn"),
    # Intersection Summary is AGGREGATE too (the Ramp Summary recipe with the
    # intersection category taxonomy; CONTROL/INTERSECTION-TYPE codes diverge → one-sided).
    ("TSAR: Intersection Summary — TSMIS vs TSN", _cmp_int_summary_tsn, "files", "tsn"),
    # Intersection Detail is FLAT (the Ramp Detail recipe): route+PM key; TSMIS read
    # by position; Y/N<->1/0 booleans normalized; cross-street attrs + Date of Record context.
    ("TSAR: Intersection Detail — TSMIS vs TSN", _cmp_int_detail_tsn, "files", "tsn"),
    # Highway Sequence is FLAT with a COUNTY+PM key (CA postmiles are county-relative):
    # TSMIS consolidated read by position (prefix+PM+suffix re-glued) vs the TSN PDFs'
    # normalized workbook. FT + Description compared; HG/City/Distance are context
    # (completeness gaps + listing-granularity artifact). TSN's finer segment breaks
    # surface as one-sided rows (as for Highway Log).
    ("Highway Sequence Listing — TSMIS vs TSN", _cmp_highway_seq_tsn, "files", "tsn"),
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
    _INT_SUMMARY_SPEC.subdir: _c_int_summary,      # v0.17.0 (AGGREGATE category summer)
    _INT_DETAIL_SPEC.subdir: _c_int_detail,        # v0.17.0
}


def consolidator_for_spec(spec):
    """The consolidate module for an export ReportSpec, or None when the report
    is export-only (Intersection Summary / Detail). Keyed on the spec's output
    subdir."""
    return _CONSOLIDATOR_BY_SUBDIR.get(getattr(spec, "subdir", None))


def consolidator_for_subdir(subdir):
    """The consolidate module for an export output `subdir` (e.g. 'ramp_detail',
    'highway_log'), or None. Lets the matrix consolidate ANY report's per-route
    store generically instead of hard-coding Highway Log. NOTE: 'highway_log_pdf'
    is NOT here (it's export-only on the TSMIS side and needs a scratch
    converted_dir — the matrix handles it as a special case)."""
    return _CONSOLIDATOR_BY_SUBDIR.get(subdir)


# App-wide disable for export-only reports that aren't ready for users. ONE gate:
# the GUI report lists, the matrix, and the start guards all route through it.
# (v0.16.x) Intersection Summary/Detail export is now ENABLED — the reports are
# available on the DEVELOPMENT site (greyed in production), so users switch to the
# dev addresses via Settings ▸ "Use development site" to export them. They remain
# export-only for now; consolidate + compare-vs-TSN are groundwork (docs/roadmap).
# To disable a report app-wide again, add its subdir back to this set.
DISABLED_EXPORT_SUBDIRS = set()


def is_export_disabled(spec):
    """True if `spec` is an app-wide-disabled export report."""
    return getattr(spec, "subdir", None) in DISABLED_EXPORT_SUBDIRS


def enabled_export_reports():
    """`(idx, label, fmt, spec)` for each ENABLED export report, where `idx` is
    the position in EXPORT_REPORTS (preserved so callers keep stable indices —
    manifests / env-scan / start_export index into the full list). Drops the
    app-wide-disabled reports (Intersection)."""
    return [(i, label, fmt, spec)
            for i, (label, fmt, spec) in enumerate(EXPORT_REPORTS)
            if not is_export_disabled(spec)]


def export_reports_status():
    """`(idx, label, fmt, spec, disabled)` for EVERY export report (the full
    EXPORT_REPORTS, with its stable index). `disabled` flags the app-wide-disabled
    reports (Intersection): the GUI shows these GREYED rather than hiding them, so
    users can see they exist but can't pick them, while the start guards still
    reject a disabled index server-side."""
    return [(i, label, fmt, spec, is_export_disabled(spec))
            for i, (label, fmt, spec) in enumerate(EXPORT_REPORTS)]


def matrix_rows():
    """The cross-environment comparison MATRIX rows, derived once from the
    registry so they can't drift: every cross-environment `folders` comparison —
    Ramp Summary / Ramp Detail / Highway Sequence AND Highway Log (all group
    "env") — mapped to its export ReportSpec so a matrix cell can be re-exported.
    Returns [(row_key, label, subdir, export_idx, adapter)] in registry order.
    Only `compare_env` `folders` adapters qualify; the file-based vs-TSN
    comparisons (group "tsn") are NOT matrix rows — they drive the separate vs-TSN
    view. Intersection reports have no cross-env adapter, so they never appear
    (the same intent as the app-wide intersection disable)."""
    by_subdir = {spec.subdir: i for i, (_l, _f, spec) in enumerate(EXPORT_REPORTS)}
    rows = []
    for _label, adapter, kind, group in COMPARE_REPORTS:
        # Only the cross-env folder adapters (compare_env.*) — every report's
        # "between environments" row now lives in the "env" group, Highway Log
        # included; the file-based "tsn" rows are skipped.
        if kind != "folders" or group != "env":
            continue
        subdir = adapter.subdir
        idx = by_subdir.get(subdir)
        disp = EXPORT_REPORTS[idx][0] if idx is not None else adapter.REPORT_NAME
        rows.append((adapter.key, disp, subdir, idx, adapter))
    # Highway Log (PDF) is its OWN matrix row (separate toggle + its own modes:
    # vs TSN-PDF, vs TSMIS Excel). It has no cross-environment adapter (that
    # comparison isn't coded yet -> env mode greyed), so add it explicitly from the
    # export spec with adapter=None. row_key = its subdir, to stay distinct from the
    # Excel "highway_log" row.
    pdf_subdir = _HIGHWAY_LOG_PDF_SPEC.subdir
    pdf_idx = by_subdir.get(pdf_subdir)
    pdf_label = EXPORT_REPORTS[pdf_idx][0] if pdf_idx is not None else "Highway Log (PDF)"
    rows.append((pdf_subdir, pdf_label, pdf_subdir, pdf_idx, None))
    return rows


# Reports that belong on the vs-TSN MATRIX but have NO cross-environment adapter,
# so they're absent from matrix_rows(): Intersection Summary / Detail. They export
# today but their consolidate + TSN comparator (and a per-report TSN dataset) are
# 0.17.0 work, so the matrix shows them as greyed groundwork rows for now.
# Returns [(row_key, label, subdir)] (row_key == export subdir, like the HL rows).
# Reports that have NO cross-env (folders) adapter, so they aren't in matrix_rows()
# but still need a by-day vs-TSN row. As of v0.17.0 EVERY report has a cross-env
# adapter (Intersection Summary + Detail gained theirs), so this is now empty — kept
# as the documented extension point for any future export-only report.
_TSN_MATRIX_EXTRA = []


def tsn_matrix_extra_rows():
    return [(spec.subdir, label, spec.subdir) for label, spec in _TSN_MATRIX_EXTRA]

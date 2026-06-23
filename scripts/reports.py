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
import logging

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

log = logging.getLogger("tsmis.reports")

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
    # Intersection Summary/Detail now consolidate AND compare (cross-env + vs-TSN)
    # as of v0.17.0 — live in both matrices. Labels verified against the live page
    # source: NO "TSAR:" prefix, and Summary is an Excel export like Detail. The
    # env check reads the dropdown for every row here, so a label drift shows up
    # there as "missing".
    ("Intersection Summary", "Excel", _INT_SUMMARY_SPEC),
    ("Intersection Detail", "Excel", _INT_DETAIL_SPEC),
]

# Stable export-op KEYS (P3 / §C.5): one per EXPORT_REPORTS row, in registry
# order. Each equals the report-FAMILY key, which IS the export spec's output
# `subdir` (ramp_summary … intersection_detail). These keys — never list
# positions — are what `batch_job.json` persists and what start_export /
# start_batch_export carry, so a later registry re-order can't resume the wrong
# report (F7). Derived from the specs so they can never drift from the subdirs.
EXPORT_KEYS = tuple(spec.subdir for _label, _fmt, spec in EXPORT_REPORTS)

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

# Stable consolidation-op KEYS (P3 / §C.5): one per CONSOLIDATE_REPORTS row, in
# registry order. The three Highway Log consolidators split by source/format
# (cons:highway_log_excel / cons:highway_log_pdf / cons:tsn_highway_log); the rest
# are cons:<family>. Carried by the consolidate bridge methods instead of an index.
CONSOLIDATE_KEYS = (
    "cons:ramp_summary",
    "cons:ramp_detail",
    "cons:highway_sequence",
    "cons:intersection_summary",
    "cons:intersection_detail",
    "cons:highway_log_excel",
    "cons:highway_log_pdf",
    "cons:tsn_highway_log",
)

# Compare tab SUB-TABS (GUI): the comparison types are grouped onto these sub-tabs
# within the Compare pane, in this order (the FIRST is the default). Two registry
# groups: "env" (Cross-environment — every report's between-environments compare,
# Highway Log included) and "tsn" (vs TSN — the file-based TSMIS-vs-TSN compares;
# every report as of v0.17.0). A THIRD
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
    # Highway Log (PDF) cross-env (v0.17.0): both sides parsed from the app's PDF
    # export (the accurate Highway Log source). Kept LAST among the env-folders rows
    # so the matrix row order is unchanged (…, highway_log_pdf last). Its `subdir`
    # ("highway_log_pdf") keeps it a distinct row from the Excel "highway_log".
    ("Highway Log (PDF) — between environments",
     _cmp_env.HIGHWAY_LOG_PDF, "folders", "env"),
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
    # registry ORDER above is unchanged; selection resolves by each row's stable
    # `cmp:*` key (P3 / COMPARE_KEYS), so appending here is safe regardless of order.
    # Each takes the consolidated TSMIS workbook + the TSN library file ("files" kind,
    # group "tsn").
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

# Stable comparison-op KEYS (P3 / §C.5): one per COMPARE_REPORTS row, in registry
# order — composite cmp:<family>:<flavor>. flavor = env (cross-environment), tsn
# (TSMIS vs TSN), or the two PDF Highway Log checks (pdf_vs_tsn / pdf_vs_excel).
# The Highway Log PDF cross-env row keeps the distinct family `highway_log_pdf`
# (its own matrix subdir), so it never collides with the Excel highway_log:env.
COMPARE_KEYS = (
    "cmp:ramp_summary:env",
    "cmp:ramp_detail:env",
    "cmp:highway_sequence:env",
    "cmp:highway_log:env",
    "cmp:intersection_summary:env",
    "cmp:intersection_detail:env",
    "cmp:highway_log_pdf:env",
    "cmp:highway_log:tsn",
    "cmp:highway_log:pdf_vs_tsn",
    "cmp:highway_log:pdf_vs_excel",
    "cmp:ramp_detail:tsn",
    "cmp:ramp_summary:tsn",
    "cmp:intersection_summary:tsn",
    "cmp:intersection_detail:tsn",
    "cmp:highway_sequence:tsn",
)

# B2 (auto-consolidate on export finish): which consolidate module handles each
# EXPORTABLE report, keyed by the export ReportSpec's output subdir so this can't
# drift from the lists above. Every exportable report is here EXCEPT Highway Log
# (PDF) (highway_log_pdf) — it needs a scratch converted_dir, so the matrix and
# auto-consolidate handle it specially (absent from the map -> None).
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
    has no auto-consolidator (Highway Log (PDF), which needs a scratch
    converted_dir). Keyed on the spec's output subdir."""
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
# dev addresses via Settings ▸ "Use development site" to export them. As of
# v0.17.0 they ALSO consolidate and compare (cross-env + vs-TSN), live in both
# matrices. To disable a report app-wide again, add its subdir back to this set.
DISABLED_EXPORT_SUBDIRS = set()


def is_export_disabled(spec):
    """True if `spec` is an app-wide-disabled export report."""
    return getattr(spec, "subdir", None) in DISABLED_EXPORT_SUBDIRS


def enabled_export_reports():
    """`(idx, label, fmt, spec)` for each ENABLED export report, where `idx` is the
    DISPLAY position in EXPORT_REPORTS (current-order metadata only). As of P3 the
    GUI/persistence contract is the stable export-op KEY (= `spec.subdir`); manifests
    / start_export travel by key, not this position. Drops the app-wide-disabled
    reports (Intersection)."""
    return [(i, label, fmt, spec)
            for i, (label, fmt, spec) in enumerate(EXPORT_REPORTS)
            if not is_export_disabled(spec)]


def export_reports_status():
    """`(idx, label, fmt, spec, disabled)` for EVERY export report (the full
    EXPORT_REPORTS; `idx` is the DISPLAY position, current-order metadata only).
    `disabled` flags the app-wide-disabled reports (Intersection): the GUI shows
    these GREYED rather than hiding them, so users can see they exist but can't pick
    them, while the start guards still reject a disabled report by its stable
    export-op KEY server-side (P3)."""
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
    # Highway Log (PDF) is its OWN matrix row (distinct subdir "highway_log_pdf",
    # with its own modes: cross-env, vs TSN-PDF, vs TSMIS Excel). As of v0.17.0 it
    # HAS a cross-env adapter (compare_env.HIGHWAY_LOG_PDF, parsing both sides' PDFs),
    # so it flows through the loop above like every other env-folders row — no special
    # adapter=None append. Its prior "env greyed" state is gone.
    return rows


# Reports that have NO cross-env (folders) adapter, so they aren't in matrix_rows()
# but still need a by-day vs-TSN row. As of v0.17.0 EVERY report has a cross-env
# adapter (Intersection Summary + Detail gained theirs), so this is now empty — kept
# as the documented extension point for any future export-only report.
# Returns [(row_key, label, subdir)] (row_key == export subdir, like the HL rows).
_TSN_MATRIX_EXTRA = []


def tsn_matrix_extra_rows():
    return [(spec.subdir, label, spec.subdir) for label, spec in _TSN_MATRIX_EXTRA]


# ---- Stable-ID lookups (P3 / §C.5) ------------------------------------------
# The registry index is now only the DISPLAY order; the KEY is the contract that
# selection/resume travel on, so a registry re-order never mis-resolves a saved
# selection (F7). The matrix `row_key` is a separate, unchanged key (caches depend
# on it) and is mapped to the family key additively, not renamed.

def _index_of(keys, key):
    """The position of `key` in the tuple `keys`, or None if absent."""
    try:
        return keys.index(key)
    except ValueError:
        return None


def export_key_for_spec(spec):
    """The export-op key for an export ReportSpec (its family key == subdir)."""
    return getattr(spec, "subdir", None)


def export_index_for_key(key):
    """The EXPORT_REPORTS row index for an export-op key, or None."""
    return _index_of(EXPORT_KEYS, key)


def spec_for_export_key(key):
    """The export ReportSpec for an export-op key, or None for an unknown key."""
    i = export_index_for_key(key)
    return EXPORT_REPORTS[i][2] if i is not None else None


def resolve_export_keys(keys):
    """Resolve a sequence of export-op keys to ``(specs, invalid)``, preserving
    order. A key that is unknown, app-wide-disabled, OR a **duplicate** goes to
    `invalid` (logged). Resolution is **all-or-nothing** (§C.5): any non-empty
    `invalid` means the saved/selected set can't be honored as-is, so the caller
    MUST reject the whole set — never silently run a narrower batch — preserving the
    pending manifest and marking no environment done (F7). `specs` holds the known,
    enabled reports in order (used only when `invalid` is empty)."""
    specs, invalid, seen = [], [], set()
    for key in keys or []:
        if key in seen:
            invalid.append(key)
            log.warning("export-op key %r is a duplicate selection — rejected", key)
            continue
        seen.add(key)
        spec = spec_for_export_key(key)
        if spec is None or is_export_disabled(spec):
            invalid.append(key)
            log.warning("export-op key %r is unknown or disabled — rejected", key)
        else:
            specs.append(spec)
    return specs, invalid


def consolidate_index_for_key(key):
    """The CONSOLIDATE_REPORTS row index for a consolidation-op key, or None."""
    return _index_of(CONSOLIDATE_KEYS, key)


def compare_index_for_key(key):
    """The COMPARE_REPORTS row index for a comparison-op key, or None."""
    return _index_of(COMPARE_KEYS, key)


# Import-time integrity (a programming error if it trips, never user input):
# every tier's keys are unique and 1:1 with its registry list. The export keys
# ARE the subdirs (derived), so only length/uniqueness need asserting.
assert len(EXPORT_KEYS) == len(EXPORT_REPORTS), "EXPORT_KEYS/EXPORT_REPORTS length drift"
assert len(set(EXPORT_KEYS)) == len(EXPORT_KEYS), "duplicate EXPORT_KEYS"
assert len(CONSOLIDATE_KEYS) == len(CONSOLIDATE_REPORTS), "CONSOLIDATE_KEYS length drift"
assert len(set(CONSOLIDATE_KEYS)) == len(CONSOLIDATE_KEYS), "duplicate CONSOLIDATE_KEYS"
assert len(COMPARE_KEYS) == len(COMPARE_REPORTS), "COMPARE_KEYS length drift"
assert len(set(COMPARE_KEYS)) == len(COMPARE_KEYS), "duplicate COMPARE_KEYS"

"""The report registry — the GUI- and console-facing VIEW over `report_catalog`.

`report_catalog.py` is the single source of truth for report metadata (P4); this
module derives the registry lists the rest of the app reads (the GUI Export /
Consolidate / Compare tabs via `gui_api.py`, the console multi-exporter via
`export_multi.py`) and keeps the registry LOGIC that isn't pure metadata — the
app-wide disable gate, the matrix-row derivation, and the stable-ID lookups.

The derived EXPORT / CONSOLIDATE / COMPARE lists + keys are proven equal to the
v0.17 baseline by `build/check_report_catalog.py` (golden-assert), so deriving them
from the catalog is behavior-neutral. The console `.bat` menu has its own parity
check; adding a report is now a one-place change in `report_catalog.py`.

Console-free: importing this never launches a browser or does application runtime I/O.
It is **not** dependency-light — via `report_catalog` it eagerly imports the `export_*`
/ `consolidate_*` / `compare_*` implementation modules (transitively openpyxl /
pdfplumber / playwright), exactly as the literal registry always did.
"""
import logging

import report_catalog as _catalog

log = logging.getLogger("tsmis.reports")

# Export tab / multi-export: (menu label, format hint, ReportSpec), in display order.
EXPORT_REPORTS = _catalog.export_rows()

# Report-PICKER grouping metadata: {export key: (group, short_label)} (P-D, v0.18.1).
# Used only to render the Export-tab checklists grouped by family; everything else
# keys off the stable export key as before.
EXPORT_DISPLAY = _catalog.export_display()

# Report-PICKER display order (export keys) — distinct from the registry/matrix
# order: flat reports first in the TSMIS site's order, then the TSAR family groups.
PICKER_ORDER = _catalog.picker_order()
# W2: one family organization across every tab's picker (display-only views).
CONSOLIDATE_DISPLAY = _catalog.consolidate_display()   # (ordered keys, {key: (group, short)})
COMPARE_DISPLAY = _catalog.compare_display()           # (ordered keys, {key: family_group})

# Stable export-op KEYS (P3 / §C.5): one per EXPORT_REPORTS row, in registry order.
# Each equals the report-FAMILY key == the export spec's output `subdir`. These keys
# — never list positions — are what `batch_job.json` persists and what start_export /
# start_batch_export carry, so a later re-order can't resume the wrong report (F7).
EXPORT_KEYS = _catalog.export_keys()

# Consolidate tab: (menu label, module). Each module exposes
# consolidate(events, confirm_overwrite, day=None) + input_dir_for(day) /
# out_path_for(day) — paths are day-dependent, so the registry hands out the module.
CONSOLIDATE_REPORTS = _catalog.consolidate_rows()

# Stable consolidation-op KEYS (P3 / §C.5): one per CONSOLIDATE_REPORTS row. The
# three Highway Log consolidators split by source/format (cons:highway_log_excel /
# cons:highway_log_pdf / cons:tsn_highway_log); the rest are cons:<family>.
CONSOLIDATE_KEYS = _catalog.consolidate_keys()

# Compare tab SUB-TABS (the FIRST is the default): "env" (cross-environment) and
# "tsn" (vs TSN). A third "vs TSN Matrix" sub-tab is appended by the GUI itself.
COMPARE_GROUPS = _catalog.compare_groups()

# Compare registry: (menu label, module/adapter, input kind, group). `kind` is
# "files" (two workbooks) or "folders" (two export run folders); `group` names the
# sub-tab. Selection/routing resolve by each row's stable `cmp:*` key (P3), so this
# order is only the display order, not the contract `start_compare*` calls key on.
COMPARE_REPORTS = _catalog.compare_rows()

# Stable comparison-op KEYS (P3 / §C.5): one per COMPARE_REPORTS row — composite
# cmp:<family>:<flavor>. The Highway Log PDF cross-env row keeps the distinct family
# `highway_log_pdf` (its own matrix subdir), so it never collides with highway_log:env.
COMPARE_KEYS = _catalog.compare_keys()

# B2 (auto-consolidate on export finish): which consolidate module handles each
# EXPORTABLE report, keyed by the export ReportSpec's output subdir. Every exportable
# report EXCEPT Highway Log (PDF) (highway_log_pdf) — it needs a scratch
# converted_dir, so the matrix and auto-consolidate handle it specially (absent -> None).
_CONSOLIDATOR_BY_SUBDIR = _catalog.consolidator_by_subdir()


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
# (v0.18.1) Highway Detail / Highway Summary were RESERVED groundwork here;
# (v0.19.1) their EXPORT is now enabled (specs finalized on the Excel-sibling
# model). Where the live site still greys or lacks the pair, select_report fails
# fast per run — no per-route stall. They stay consolidate/compare/matrix-ABSENT
# until that later feature lands. The set stays as the app-wide kill switch: to
# disable a report app-wide again, add its subdir back.
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

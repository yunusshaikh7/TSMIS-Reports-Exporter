"""TSN Clean Road library builders — Highway is LIVE (v0.29.0); Intersection
and Ramp stay staged skeletons.

The owner's three TSN "clean road" extracts (2026-07-20 delivery) are the
UNDERLYING tables, not the TSAR report projections the rest of the TSN library
holds:

    CA HIGHWAYS 09.08.2025.xlsx        60,083 rows x 74 cols   THY_* fields
    CA INTERSECTIONS 09.03.2025.xlsx   16,626 rows x 55 cols   INX_* fields
    CA RAMPS 09.08.2025.xlsx           15,410 rows x 32 cols   RAM_* fields

**Highway** now has a real normalizer: the ArcGIS clean-road build
(`consolidate_clean_highway`) produces our own THY-shaped table, and
`compare_clean_highway_tsn` diffs the two, so the library slot projects the
raw extract into its reusable comparison form. The normalization is
deliberately VERBATIM — the exact 74-column header is required
(compare_tsn_common.require_exact_raw_header semantics), every cell value is
conserved byte-for-byte, and the comparator owns all format normalization at
load (the RD v4+ discipline: the library never edits source text). The
CMP-AUD-037 marker stamps the normalization version so the direct path can
refuse a stale copy.

**Intersection / Ramp** remain typed refusals: their comparisons don't exist
yet, so inventing a projection would bake in a guess. Integrating one follows
the highway pattern here plus its comparator + a `normalization_version` in
`report_catalog.TSN`.

Console-free: returns results, never prints.
"""
try:
    from openpyxl import Workbook, load_workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import clean_highway_columns as chc
import compare_clean_highway_tsn as cht
import compare_tsn_common as ctc
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"

# The label shown in the "not integrated yet" message, per staged slot.
_LABELS = {
    "clean_intersection": "Intersection",
    "clean_ramp": "Ramp",
}


def _project_highway(raw_path):
    """Read the raw TSN CA HIGHWAYS statewide workbook VERBATIM (exact
    74-column header, no formula cells, required identity claims non-blank)
    and build the success result."""
    with ctc.exact_raw_rows(
            raw_path, chc.TSN_RAW_SHEET, tuple(chc.HEADER), cht.REPORT_NAME,
            required_nonblank=("THY_COUNTY_CODE", "THY_ROUTE_NAME",
                               "THY_BEGIN_PM_AMT")) as (_header, rows_in):
        rows = [list(r) for r in rows_in]
    n_routes = len({(str(r[chc.HEADER.index("THY_ROUTE_NAME")]),
                     str(r[chc.HEADER.index("THY_ROUTE_SUFFIX_CODE")] or ""))
                    for r in rows})

    def make_result(out_name):
        return ConsolidateResult(
            status="ok",
            message=(f"Normalized {len(rows):,} TSN Clean Road Highway rows "
                     f"({n_routes} routes)."),
            summary_lines=[f"TSN Clean Road Highway: {len(rows):,} rows, "
                           f"{n_routes} routes -> {out_name}"],
            completion=outcome.COMPLETE,
            skipped_inputs=0,
            failed_inputs=0)

    return rows, make_result


def build_into_highway(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN CA HIGHWAYS extract in `raw_dir` into the normalized
    library workbook at `out_path` (sheet chc.NORMALIZED_SHEET, the verbatim
    74-column header, the CMP-AUD-037 marker). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN CA HIGHWAYS clean-road .xlsx",
        no_raw_hint="Import the 'CA HIGHWAYS' TSN clean-road extract first.",
        log_label="TSN Clean Road Highway",
        sheet=chc.NORMALIZED_SHEET,
        header=list(chc.HEADER),
        header_align={"horizontal": "center", "vertical": "center",
                      "wrap_text": True},
        project=_project_highway,
        marker_version=cht.NORMALIZATION_VERSION)


def _not_integrated(key):
    label = _LABELS[key]
    return ConsolidateResult(
        status="error",
        message=(
            f"TSN Clean Road {label}: the files are staged, but this report "
            "has no normalizer yet — its ArcGIS-side build and comparison "
            "haven't been integrated (Highway went first). The raw files stay "
            "where you put them and are counted here."),
    )


def build_into_intersection(raw_dir, out_path, events=None,
                            confirm_overwrite=None):
    """Reserved: no TSN Clean Road Intersection normalization exists yet."""
    return _not_integrated("clean_intersection")


def build_into_ramp(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Reserved: no TSN Clean Road Ramp normalization exists yet."""
    return _not_integrated("clean_ramp")

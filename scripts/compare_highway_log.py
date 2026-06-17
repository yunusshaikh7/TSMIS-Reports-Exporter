"""Build the TSMIS-vs-TSN Highway Log discrepancy workbook.

Takes a TSMIS Highway Log and a TSN Highway Log — either BOTH per-route
workbooks (31 columns, one route each) or BOTH consolidated workbooks (a
leading "Route" column, every route) — and writes the approved comparison
workbook: Summary / Spot Check / Comparison / (Routes) / Only in TSMIS /
Only in TSN / TSMIS / TSN, in the live-formulas and/or values flavors.

Since v0.10.0 the engine itself lives in compare_core.py (parameterized so
the cross-environment comparisons reuse it); this module is the Highway
Log's schema + input loading. The delegation is regression-verified: the
workbooks it writes are cell-for-cell identical to the pre-extraction
output (the format locked to the approved Route-1 sample). Comparison
semantics, sheet design and the formulas/values flavors are documented in
compare_core.py.

Console-free like the other report modules: progress via events.on_log,
overwrite via the confirm_overwrite callback, cancel honored between phases,
ConsolidateResult returned.
"""
import re
from pathlib import Path

try:
    from openpyxl import load_workbook
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from compare_core import CompareSchema, normalize_value, run_compare
from events import ConsolidateResult, Events
from paths import today_str

REPORT_NAME = "Highway Log"          # registry label (comparison type)
SHEET_NAME = "Highway Log"           # required sheet in both inputs

# The per-route Highway Log layout (TSMIS export == converted TSN file).
# Consolidated workbooks carry ["Route"] + this.
EXPECTED_HEADER = [
    "Location", "MI", "N/A", "Cnty Odom", "City", "R/U", "SPD", "TER", "H/G",
    "A/C", "LB T", "LB Lns", "LB F", "LB OT", "LB TR", "LB T-W", "LB IN",
    "LB SH", "Med TCB", "Med Wid", "RB T", "RB Lns", "RB F", "RB IN", "RB SH",
    "RB T-W", "RB OT", "RB SH", "Description", "Date of Rec", "Sig Chg. Date",
]

# The approved workbook's wording and geometry, exactly (see compare_core's
# CompareSchema): TSMIS/TSN side names, Med Wid zero-pad normalization, the
# Highway-Log-specific notes, and the sample's column widths.
_SCHEMA = CompareSchema(
    report_name="Highway Log",
    header=EXPECTED_HEADER,
    side_a="TSMIS",
    side_b="TSN",
    id_noun="location",
    id_noun_plural="locations",
    pair_noun="postmile",
    sides_noun="systems",
    medwid_fields=("Med Wid",),
    date_fields=("Date of Rec", "Sig Chg. Date"),
    data_widths={"Location": 12, "MI": 11, "Description": 26, "Date of Rec": 11},
    cmp_widths={"MI": 12, "Description": 30, "Date of Rec": 12},
    one_sided_note_extra=" (mostly TSN segment splits and TSMIS realignment "
                         "markers)",
    trim_note_extra=" — the TSMIS export pads Description with trailing blanks",
)


def suggest_name(tsmis_path):
    """Output filename suggestion: 'TSMIS_vs_TSN_Route<id>_Comparison.xlsx'
    when the picked file carries a route token, consolidated-aware otherwise."""
    stem = Path(tsmis_path).stem
    m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
    if m:
        tag = f"Route{m.group(1).lstrip('0') or '0'}"
    elif "consolidated" in stem.lower():
        tag = "Consolidated"
    else:
        tag = "Highway_Log"
    # Trailing generated-on date (A1): stamps when the comparison was built.
    return f"TSMIS_vs_TSN_{tag}_Comparison {today_str()}.xlsx"


def _load_input(path):
    """Load one Highway Log workbook -> (rows, has_route).

    Accepts the per-route layout (31 columns) and the consolidated layout
    ("Route" + 31). Raises ValueError with a user-safe message otherwise."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if SHEET_NAME not in wb.sheetnames:
            raise ValueError(
                f"{name} has no '{SHEET_NAME}' sheet — pick a Highway Log "
                f"workbook (a TSMIS export or consolidation, or a TSN file "
                f"made by the TSN Highway Log consolidation).")
        rows_iter = wb[SHEET_NAME].iter_rows(values_only=True)
        header = [v for v in next(rows_iter, [])]
        while header and header[-1] in (None, ""):
            header.pop()
        if header == EXPECTED_HEADER:
            has_route = False
        elif header == ["Route"] + EXPECTED_HEADER:
            has_route = True
        else:
            raise ValueError(
                f"{name} doesn't have the Highway Log column layout this "
                f"comparison expects — re-create it with this app, then retry.")
        n = len(header)
        rows = []
        for r in rows_iter:
            r = list(r)[:n] + [None] * max(0, n - len(r))
            if any(v is not None and str(v).strip() != "" for v in r):
                rows.append([normalize_value(v) for v in r])
        return rows, has_route
    finally:
        wb.close()


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the comparison workbook(s). Returns a ConsolidateResult (same
    contract as the consolidators, so the GUI/console drive it identically).

    `mode`: "formulas" (the live workbook — every cell recalculates),
    "values" (same sheets and look, but the bulk is plain computed RESULTS —
    opens instantly, no F9), or "both" (two files: the picked name for the
    formulas copy and '<name> (values).xlsx' next to it)."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    tsmis_path, tsn_path = Path(tsmis_path), Path(tsn_path)

    for p, side in ((tsmis_path, "TSMIS"), (tsn_path, "TSN")):
        if not p.is_file():
            return ConsolidateResult(
                status="error",
                message=f"The {side} file doesn't exist:\n{p}")

    events.on_log("=" * 60)
    events.on_log("Highway Log Comparison — TSMIS vs TSN")
    events.on_log("=" * 60)
    events.on_log(f"TSMIS: {tsmis_path.name}")
    events.on_log(f"TSN:   {tsn_path.name}")
    events.on_log("")

    try:
        rows_t, route_t = _load_input(tsmis_path)
        rows_n, route_n = _load_input(tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))
    if route_t != route_n:
        per, con = ((tsn_path, tsmis_path) if route_t else (tsmis_path, tsn_path))
        return ConsolidateResult(
            status="error",
            message=(f"The two files have different shapes: {con.name} is a "
                     f"consolidated workbook (has a Route column) but "
                     f"{per.name} is per-route. Pick two per-route files or "
                     f"two consolidated files."))

    return run_compare(_SCHEMA, rows_t, rows_n, route_t, out_path,
                       events=events, confirm_overwrite=confirm_overwrite,
                       mode=mode, name_a=tsmis_path.name, name_b=tsn_path.name)

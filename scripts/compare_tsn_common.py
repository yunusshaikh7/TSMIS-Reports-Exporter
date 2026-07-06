"""Shared substrate for the five TSMIS-vs-TSN FILE comparators (P5b / S04).

`compare_ramp_detail_tsn`, `compare_ramp_summary_tsn`, `compare_highway_sequence_tsn`,
`compare_intersection_detail_tsn`, and `compare_intersection_summary_tsn` each wrote
the SAME `compare()` skeleton — deps gate, path/existence checks, the log banner, the
load try/except, then a `compare_core.run_compare` call — differing only in the schema,
the per-report loaders, the banner text, and (for the two FLAT detail reports) a couple
of normalizers + a Notes legend sheet. This module is that shared skeleton, so each
comparator is reduced to its **schema + projector**:

  * `run_files_compare` — the registry "files"-kind `compare()` driver. The report
    supplies a `loader(tsmis_path, tsn_path) -> (rows_t, rows_n, warnings)` (it may raise
    ValueError for a bad input shape) and the static facts (schema, banner, has_route,
    deps gate); the driver owns the boilerplate and the `run_compare` hand-off.
  * `make_notes_writer` — the identical "Notes" legend sheet builder the two FLAT detail
    comparators share (title + body lines differ; styling is fixed).
  * `norm_pm` / `iso_date` — the postmile + date normalizers Ramp Detail and Intersection
    Detail share verbatim (`iso_date` also handles Intersection Detail's 2-digit TSN year).

Behavior-neutral: the strings, branch order, and `run_compare` arguments match the
per-module bodies this replaced (the five golden `check_compare_*_tsn.py` canaries are
the semantic-identity proof). The comparison engine stays in `compare_core` — this
module never touches it. Console-free; openpyxl is imported lazily (only inside the
Notes writer, which runs solely when a workbook is actually being built).
"""
import re
from pathlib import Path

from compare_core import run_compare
from events import ConsolidateResult, Events
from paths import today_str


# --------------------------------------------------------------------------- #
# shared row/name helpers (v0.19.0 R1 — the idioms every comparator copied)
# --------------------------------------------------------------------------- #
def row_has_data(row):
    """True when the row holds at least one non-blank cell — the emptiness
    predicate every loader wrote inline (`any(c is not None and str(c).strip()
    != "" ...)`); one spelling so they can't drift."""
    return bool(row) and any(c is not None and str(c).strip() != "" for c in row)


_ROUTE_TOKEN_RE = re.compile(r"route[ _-]*([0-9]+[A-Za-z]?)", re.IGNORECASE)


def suggest_route_name(path, fallback_tag, name_tag):
    """Output-filename suggestion shared by the route-aware comparators:
    '<name_tag>_<RouteN|Consolidated|fallback_tag>_Comparison <today>.xlsx'.
    The trailing generated-on date stamps when the comparison was built (A1)."""
    stem = Path(path).stem
    m = _ROUTE_TOKEN_RE.search(stem)
    tag = (f"Route{m.group(1).lstrip('0') or '0'}" if m
           else "Consolidated" if "consolidated" in stem.lower() else fallback_tag)
    return f"{name_tag}_{tag}_Comparison {today_str()}.xlsx"


def load_consolidated_rows(path, sheet_name, *, missing_sheet_hint, bad_header_msg,
                           header_ok=None, row_transform=list):
    """The consolidated-workbook loader skeleton three vs-TSN comparators wrote
    verbatim: open (user-safe ValueError on failure) -> require `sheet_name` ->
    read + strip the header -> demand a leading 'Route' column (plus the
    report's `header_ok(header)` drift guard) -> the non-empty data rows through
    `row_transform(list(row))`. Returns `(rows, True)` — the consolidated shape
    is always route-keyed. openpyxl is imported here (lazily), matching the
    module's deps posture."""
    from openpyxl import load_workbook

    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"{name} has no '{sheet_name}' sheet — {missing_sheet_hint}")
        it = wb[sheet_name].iter_rows(values_only=True)
        header = [str(c).strip() if c is not None else "" for c in (next(it, []) or [])]
        if (not header or header[0] != "Route"
                or (header_ok is not None and not header_ok(header))):
            raise ValueError(f"{name} {bad_header_msg}")
        return [row_transform(list(r)) for r in it if row_has_data(r)], True
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# shared normalizers (Ramp Detail + Intersection Detail, verbatim)
# --------------------------------------------------------------------------- #
def norm_pm(pm):
    """Postmile to one canon: strip the zero-padding TSN prints (' 000.606')
    while keeping the decimal ('0.606' stays distinct from '000.606'). A real
    numeric 0/0.0 canonicalizes to '0', NOT blank — `pm or ""` was the falsy-zero
    idiom (v0.18.3's phantom-diff root cause), and THIS normalizer feeds the
    row-ALIGNMENT keys, so a blanked 0 mis-aligned rows, not just cells."""
    s = ("" if pm is None else str(pm)).strip()
    if not s:
        return ""
    neg = s.startswith("-")
    s = s.lstrip("-").lstrip("0") or "0"
    if s.startswith("."):
        s = "0" + s
    return ("-" + s) if neg else s


def iso_date(d):
    """A Date of Record to YYYY-MM-DD across the formats the two systems print:
    TSMIS 'MM/DD/YYYY', TSN 'YYYY-MM-DD[ HH:MM:SS]', and TSN's 2-digit 'YY-MM-DD'
    (windowed at 30: >=30 -> 19xx, else 20xx)."""
    s = ("" if d is None else str(d)).strip()
    if not s:
        return ""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})$", s)             # TSN '73-10-19' (YY-MM-DD)
    if m:
        yy = int(m.group(1))
        cc = 1900 if yy >= 30 else 2000                     # 2-digit-year window
        return f"{cc + yy}-{m.group(2)}-{m.group(3)}"
    return s


# --------------------------------------------------------------------------- #
# shared Notes legend sheet (Highway Sequence + Intersection Detail)
# --------------------------------------------------------------------------- #
def make_notes_writer(title, lines, *, tab_color="ED7D31", col_width=110):
    """Return a `legend_writer(wb)` that appends the standard orange-tabbed "Notes"
    sheet: a filled white title row then one wrapped body row per line. Styling is
    fixed (Arial title/body, the 1F3864 fill, an A-column width); only `title` and
    `lines` vary per report. openpyxl is imported here (not at module import) so this
    module loads even where the comparators' deps are absent — the writer only ever
    runs while a workbook is being built (deps present)."""
    def _write(wb):
        from openpyxl.cell import WriteOnlyCell
        from openpyxl.styles import Alignment, Font, PatternFill

        ws = wb.create_sheet("Notes")
        ws.sheet_properties.tabColor = tab_color
        write_only = getattr(wb, "write_only", False)
        title_font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
        fill = PatternFill("solid", start_color="1F3864")
        body = Font(name="Arial", size=10)
        wrap = Alignment(vertical="top", wrap_text=True)

        def cell(value, font=body, f=None, align=None):
            if not write_only:
                return value
            c = WriteOnlyCell(ws, value=value)
            c.font = font
            if f:
                c.fill = f
            if align:
                c.alignment = align
            return c

        ws.column_dimensions["A"].width = col_width
        ws.append([cell(title, title_font, fill)])
        for line in lines:
            ws.append([cell(line, body, align=wrap)])
        return ws

    return _write


# --------------------------------------------------------------------------- #
# the shared compare() driver
# --------------------------------------------------------------------------- #
def run_files_compare(schema, tsmis_path, tsn_path, out_path, *, banner, has_route,
                      loader, deps_ok=True,
                      deps_msg="Required components are missing (openpyxl).",
                      side_a="TSMIS", side_b="TSN",
                      events=None, confirm_overwrite=None, mode="formulas"):
    """The registry "files"-kind `compare()` skeleton shared by every file
    comparator: a deps gate -> path coercion + existence checks -> the log banner ->
    `loader(path_a, path_b)` (may raise ValueError for a bad input shape) ->
    `compare_core.run_compare`. `loader` returns `(rows_a, rows_b, warnings)`; a
    `warnings` of None is the `run_compare` default (no unreadable inputs). Two
    opt-in extensions (defaults = the original vs-TSN behavior, so the five P5b
    comparators are untouched):

      * `side_a`/`side_b` — the two side labels used in the existence-check
        message and the banner's file lines (the PDF-sourced flavors label their
        pickers "TSMIS (PDF)" / "TSMIS (Excel)").
      * `has_route=None` — the route-ness is DYNAMIC (per-route vs consolidated
        inputs); the loader then returns `(rows_a, rows_b, warnings, has_route)`.

    Returns a `ConsolidateResult`, the same contract the GUI/console drive
    identically."""
    events = events or Events()
    if not deps_ok:
        return ConsolidateResult(status="error", message=deps_msg)
    tsmis_path, tsn_path = Path(tsmis_path), Path(tsn_path)
    for p, side in ((tsmis_path, side_a), (tsn_path, side_b)):
        if not p.is_file():
            return ConsolidateResult(status="error",
                                     message=f"The {side} file doesn't exist:\n{p}")

    events.on_log("=" * 60)
    events.on_log(banner)
    events.on_log("=" * 60)
    pad = max(len(side_a), len(side_b)) + 1
    events.on_log(f"{side_a + ':':<{pad}} {tsmis_path.name}")
    events.on_log(f"{side_b + ':':<{pad}} {tsn_path.name}")
    events.on_log("")

    try:
        loaded = loader(tsmis_path, tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))
    if has_route is None:
        rows_t, rows_n, warnings, has_route = loaded
    else:
        rows_t, rows_n, warnings = loaded

    return run_compare(schema, rows_t, rows_n, has_route, out_path,
                       events=events, confirm_overwrite=confirm_overwrite,
                       mode=mode, name_a=tsmis_path.name, name_b=tsn_path.name,
                       warnings=() if warnings is None else warnings)

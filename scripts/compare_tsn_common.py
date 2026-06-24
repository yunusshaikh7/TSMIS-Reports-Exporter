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


# --------------------------------------------------------------------------- #
# shared normalizers (Ramp Detail + Intersection Detail, verbatim)
# --------------------------------------------------------------------------- #
def norm_pm(pm):
    """Postmile to one canon: strip the zero-padding TSN prints (' 000.606')
    while keeping the decimal ('0.606' stays distinct from '000.606')."""
    s = str(pm or "").strip()
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
    s = str(d or "").strip()
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
                      events=None, confirm_overwrite=None, mode="formulas"):
    """The registry "files"-kind `compare()` skeleton shared by the five vs-TSN file
    comparators: a deps gate -> path coercion + existence checks -> the log banner ->
    `loader(tsmis_path, tsn_path)` (may raise ValueError for a bad input shape) ->
    `compare_core.run_compare`. `loader` returns `(rows_t, rows_n, warnings)`; a
    `warnings` of None is the `run_compare` default (no unreadable inputs). Returns a
    `ConsolidateResult`, the same contract the GUI/console drive identically."""
    events = events or Events()
    if not deps_ok:
        return ConsolidateResult(status="error", message=deps_msg)
    tsmis_path, tsn_path = Path(tsmis_path), Path(tsn_path)
    for p, side in ((tsmis_path, "TSMIS"), (tsn_path, "TSN")):
        if not p.is_file():
            return ConsolidateResult(status="error",
                                     message=f"The {side} file doesn't exist:\n{p}")

    events.on_log("=" * 60)
    events.on_log(banner)
    events.on_log("=" * 60)
    events.on_log(f"TSMIS: {tsmis_path.name}")
    events.on_log(f"TSN:   {tsn_path.name}")
    events.on_log("")

    try:
        rows_t, rows_n, warnings = loader(tsmis_path, tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))

    return run_compare(schema, rows_t, rows_n, has_route, out_path,
                       events=events, confirm_overwrite=confirm_overwrite,
                       mode=mode, name_a=tsmis_path.name, name_b=tsn_path.name,
                       warnings=() if warnings is None else warnings)

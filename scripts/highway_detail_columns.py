"""Single source of truth for the Highway Detail column labels + meanings.

Unlike the Highway Log, the TSMIS Highway Detail Excel export labels its 34
columns CORRECTLY (they match the report's own legend page), so no relabel
override is needed — this module exists so every Highway Detail workflow (the
Excel consolidator, the PDF-sourced consolidator, the comparisons) agrees on the
one header, and so header cells can carry the legend meanings as hover tooltips.

The meanings come from the report's OWN legend (the TSMIS legend page, verified
against the TSN OTM22220 "TSAR-HIGHWAY DETAIL" legend): each record is two
printed lines — line 1 the post mile / length / record / access-control / city
attributes with their effective dates, line 2 the description and the Left
Roadbed / Median / Right Roadbed attribute blocks, each led by its own
effective date. The legacy ADT Information block is TSN-only (the TSMIS report
intentionally omits it), so it is not part of this header.

Kept import-light (the data + recognize() need no third-party libs); the
openpyxl-based Legend/tooltip helpers guard their import so importing this
module never fails when a dependency is missing.
"""

# (group, label, plain-English meaning) — label == the export's own header text.
# group "" = an ungrouped column (no roadbed/median band over it).
COLUMNS = [
    ("", "Post Mile",
     "Postmile: prefix + mile + marker (e.g. 'R012.243', 'S000.000', '000.000E'). "
     "Prefix codes: C commercial lanes, D duplicate PM at a meandering county "
     "line, G reposting at a route end, H realignment of D, L overlap, M "
     "realignment of R, N realignment of M, R first realignment, S spur, T "
     "temporary connection. A trailing R/L marks a Right/Left independent-"
     "alignment roadbed row; a trailing E marks an equation point."),
    ("", "Length", "Distance to the next record (miles)"),
    ("", "Date of Rec", "Network date of record"),
    ("", "HG", "Highway Group: R/L independent alignment, D divided, "
               "U undivided, X unconstructed"),
    ("", "AC", "Access Control"),
    ("", "Acc-Cont Eff", "Access Control effective date"),
    ("", "City", "City code"),
    ("", "RU", "Rural / Urban (Population Code)"),
    ("", "RU Eff", "Rural/Urban (Population Code) effective date. NOTE: the "
                   "legacy TASAS/TSN report prints the ADT profile BEGIN date "
                   "in this slot, so it differs from TSN on nearly every row."),
    ("", "Description", "Feature description"),
    ("", "NA", "Non-Add Mileage ('N' when the mileage is non-add; blank "
               "otherwise — TSN prints an explicit 'A' for add mileage)"),
    ("Left Roadbed", "LB Eff", "Left roadbed — section effective date"),
    ("Left Roadbed", "LB S/T", "Left roadbed — Surface Type"),
    ("Left Roadbed", "LB #Ln", "Left roadbed — Number of Lanes"),
    ("Left Roadbed", "LB S/F", "Left roadbed — Special Feature ('Z' = none; "
                               "TSMIS leaves this blank where TSN prints Z)"),
    ("Left Roadbed", "LB OT-TO", "Left roadbed — Outside Shoulder, Total width"),
    ("Left Roadbed", "LB OT-TR", "Left roadbed — Outside Shoulder, Treated width"),
    ("Left Roadbed", "LB Wid", "Left roadbed — Traveled Way Width"),
    ("Left Roadbed", "LB IN-TO", "Left roadbed — Inside Shoulder, Total width"),
    ("Left Roadbed", "LB IN-TR", "Left roadbed — Inside Shoulder, Treated width"),
    ("Median", "Med Eff", "Median — section effective date"),
    ("Median", "Med T", "Median — Type"),
    ("Median", "Med C", "Median — Curb & Landscape"),
    ("Median", "Med B", "Median — Barrier"),
    ("Median", "Med V/WDA", "Median — Width + Variance code (e.g. '14Z', '08V')"),
    ("Right Roadbed", "RB Eff", "Right roadbed — section effective date"),
    ("Right Roadbed", "RB S/T", "Right roadbed — Surface Type"),
    ("Right Roadbed", "RB #Ln", "Right roadbed — Number of Lanes"),
    ("Right Roadbed", "RB S/F", "Right roadbed — Special Feature ('Z' = none)"),
    ("Right Roadbed", "RB IN-TO", "Right roadbed — Inside Shoulder, Total width"),
    ("Right Roadbed", "RB IN-TR", "Right roadbed — Inside Shoulder, Treated width"),
    ("Right Roadbed", "RB Wid", "Right roadbed — Traveled Way Width"),
    ("Right Roadbed", "RB OT-TO", "Right roadbed — Outside Shoulder, Total width"),
    ("Right Roadbed", "RB OT-TR", "Right roadbed — Outside Shoulder, Treated width"),
]

HEADER = [c[1] for c in COLUMNS]            # the 34 export labels (correct as-is)
ROUTE_COL = "Route"                         # leading column on consolidated workbooks

assert len(HEADER) == 34                    # layout guard (the export's 34 columns)


def recognize(header):
    """Is `header` (a loaded row-1 list, possibly with a leading 'Route') the
    Highway Detail layout? Returns has_route (bool) when recognized, else None.
    Comparison is by the full label list, so a same-width but different report
    can't sneak through."""
    if header == list(HEADER):
        return False
    if header == [ROUTE_COL] + list(HEADER):
        return True
    return None


def legend_rows():
    """Rows for the 'Legend' sheet: (group, label, meaning), in column order."""
    return [(grp, label, meaning) for grp, label, meaning in COLUMNS]


def tooltip_for(label):
    """The hover-tooltip text for a header `label` (group prefix + meaning), or
    None when the label isn't a Highway Detail column."""
    for grp, lab, meaning in COLUMNS:
        if lab == label:
            return f"[{grp}] {meaning}" if grp else meaning
    return None


# ---------------------------------------------------------------------------
# openpyxl helpers (guarded — importing this module must never need openpyxl).
# Same shapes as highway_log_columns so the consolidators/comparisons plug in
# identically. Work in both normal and write_only (streaming) workbooks.
# ---------------------------------------------------------------------------
try:
    from openpyxl.comments import Comment
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    _OPX = True
except ImportError:
    _OPX = False

_LEGEND_DARK = "1F3864"
_LEGEND_TITLE = ("Highway Detail — column legend. Each record is two printed "
                 "lines: line 1 the location/record/access/city attributes, "
                 "line 2 the description + the Left Roadbed / Median / Right "
                 "Roadbed blocks, each led by its own effective date.")


def comment_for(label):
    """An openpyxl Comment (hover tooltip) for header `label`, or None."""
    if not _OPX:
        return None
    text = tooltip_for(label)
    if text is None:
        return None
    c = Comment(text, "TSMIS Exporter")
    c.width, c.height = 320, 120
    return c


def write_legend_sheet(wb, title="Legend"):
    """Append a Legend worksheet (Group / Column / Meaning) to `wb`.
    Streaming-safe: only create_sheet + append are used, so it works on a
    write_only workbook too. No-op if openpyxl is unavailable."""
    if not _OPX:
        return None
    ws = wb.create_sheet(title)
    ws.sheet_properties.tabColor = _LEGEND_DARK
    hfont = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    hfill = PatternFill("solid", start_color=_LEGEND_DARK)
    note_font = Font(name="Arial", size=10, italic=True, color="595959")
    body = Font(name="Arial", size=10)
    wrap = Alignment(vertical="top", wrap_text=True)
    write_only = getattr(wb, "write_only", False)

    def cell(value, font=body, fill=None, align=None):
        if write_only:
            c = WriteOnlyCell(ws, value=value)
            c.font = font
            if fill:
                c.fill = fill
            if align:
                c.alignment = align
            return c
        return value

    for col, w in (("A", 16), ("B", 14), ("C", 84)):
        ws.column_dimensions[col].width = w
    ws.append([cell(_LEGEND_TITLE, note_font)])
    ws.append([cell(h, hfont, hfill) for h in ("Group", "Column", "Meaning")])
    for grp, label, meaning in legend_rows():
        ws.append([cell(grp or "—"), cell(label), cell(meaning, body, align=wrap)])
    if not write_only:
        for row in ws.iter_rows(min_row=2, max_row=2):
            for c in row:
                c.font = hfont
                c.fill = hfill
    return ws


def apply_header_tooltips(ws, first_row=1):
    """Attach the hover tooltip to each Highway Detail header cell on an
    already-written, NON-streaming sheet. No-op if openpyxl is unavailable."""
    if not _OPX:
        return
    for c in next(ws.iter_rows(min_row=first_row, max_row=first_row)):
        cm = comment_for(c.value)
        if cm is not None:
            c.comment = cm

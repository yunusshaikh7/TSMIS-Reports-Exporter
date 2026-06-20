"""Shared familiar-layout renderer for the AGGREGATE summary comparisons.

The two SUMMARY reports — Ramp Summary and Intersection Summary — compare a
single statewide category-count table per side (TSMIS vs TSN). compare_core
renders the generic Comparison sheet keyed on the category; this module adds the
FAMILIAR sheet the user knows from the source document: the same sections, in the
same order, with the same labels, now carrying both sides' counts and the
difference. It is plugged in through CompareSchema.extra_sheet_writer (opt-in, so
every non-summary comparison is byte-identical).

One renderer, two reports: each report supplies a SummarySpec (its ordered
sections + the category code/label/slug for each). The Ramp Summary spec lives
here (RAMP_SUMMARY_SPEC); Intersection Summary adds its own. The category SLUGS
match the per-route consolidator's column slugs, so the comparator can map a
consolidated TSMIS workbook's columns to the same categories the TSN PDF parses.

Streaming-safe: only create_sheet + append are used (the comparison workbook is
written in openpyxl write_only mode), mirroring highway_log_columns.write_legend_sheet.
"""
from dataclasses import dataclass, field

try:
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    _OPX = True
except ImportError:
    _OPX = False

# Section band / header colors (echo the consolidator's Combined-sheet palette).
_TITLE_FILL = "1F3864"
_SECTION_FILL = "0070C0"
_DIFF_FONT = "C00000"           # non-zero Δ
_TAB_COLOR = "00B0F0"


@dataclass(frozen=True)
class Cat:
    """One comparison category: `slug` maps to the consolidator column, `label`
    is the short familiar-block text, `key` is the unique compare key (the value
    shown in the generic Comparison sheet's key column)."""
    slug: str
    label: str
    key: str


@dataclass(frozen=True)
class Section:
    name: str
    cats: tuple


@dataclass(frozen=True)
class SummarySpec:
    """A summary report's familiar layout: ordered sections, a grand-total
    category, and TSMIS-only footnote categories (shown but not section members)."""
    report: str                       # "Ramp Summary"
    sheet_name: str                   # the familiar sheet's tab name
    title: str
    sections: tuple
    total: Cat = None                 # the grand-total row (e.g. Total Number of Ramps)
    footnotes: tuple = field(default_factory=tuple)   # TSMIS-only extras (e.g. no-linework)

    def categories(self):
        """Every COMPARED category in display order (sections then total) as
        (key, slug). Footnotes are NOT compared — they live only on the familiar
        sheet — so they are excluded here."""
        out = []
        for sec in self.sections:
            out += [(c.key, c.slug) for c in sec.cats]
        if self.total is not None:
            out.append((self.total.key, self.total.slug))
        return out

    def slug_for_key(self):
        return {k: s for k, s in self.categories()}


# =============================================================================
# Ramp Summary canonical spec (slugs == consolidate_ramp_summary column slugs)
# =============================================================================

def _c(slug, label, key):
    return Cat(slug=slug, label=label, key=key)


RAMP_SUMMARY_SPEC = SummarySpec(
    report="Ramp Summary",
    sheet_name="Summary by Category",
    title="Ramp Summary — TSMIS vs TSN by category",
    sections=(
        Section("Highway Groups", (
            _c("hwy_right",         "R - Right",         "Highway Group: R - Right"),
            _c("hwy_divided",       "D - Divided",       "Highway Group: D - Divided"),
            _c("hwy_undivided",     "U - Undivided",     "Highway Group: U - Undivided"),
            _c("hwy_unconstructed", "X - Unconstructed", "Highway Group: X - Unconstructed"),
            _c("hwy_left",          "L - Left",          "Highway Group: L - Left"),
            _c("hwy_others",        "Others",            "Highway Group: Others"),
        )),
        Section("On/Off Indicator", (
            _c("onoff_on",    "ON - On",    "On/Off: ON - On"),
            _c("onoff_off",   "OFF - Off",  "On/Off: OFF - Off"),
            _c("onoff_other", "OTH - Other","On/Off: OTH - Other"),
        )),
        Section("Population Groups", (
            _c("pop_rural_inside",  "R-RURAL -I INSIDE CITY",  "Population: R-RURAL -I INSIDE CITY"),
            _c("pop_rural_outside", "R-RURAL -O OUTSIDE CITY", "Population: R-RURAL -O OUTSIDE CITY"),
            _c("pop_urban_inside",  "U-URBAN -I INSIDE CITY",  "Population: U-URBAN -I INSIDE CITY"),
            _c("pop_urban_outside", "U-URBAN -O OUTSIDE CITY", "Population: U-URBAN -O OUTSIDE CITY"),
            _c("pop_invalid",       "-INVALID DATA",           "Population: -INVALID DATA"),
        )),
        Section("Ramp Types", (
            _c("ramp_A_frontage",    "A - Frontage Road",          "Ramp Type: A - Frontage Road"),
            _c("ramp_B_collector",   "B - Collector Road",         "Ramp Type: B - Collector Road"),
            _c("ramp_C_connector_L", "C - Connector (Left)",       "Ramp Type: C - Direct or Semi-direct Connector (Left)"),
            _c("ramp_D_diamond",     "D - Diamond Type Ramp",      "Ramp Type: D - Diamond Type Ramp"),
            _c("ramp_E_slip",        "E - Slip Ramp",              "Ramp Type: E - Slip Ramp"),
            _c("ramp_F_connector_R", "F - Connector (Right)",      "Ramp Type: F - Direct or Semi-direct Connector (Right)"),
            _c("ramp_G_loop_left",   "G - Loop (w/Left turn)",     "Ramp Type: G - Loop (w/Left turn)"),
            _c("ramp_H_buttonhook",  "H - Buttonhook Ramp",        "Ramp Type: H - Buttonhook Ramp"),
            _c("ramp_J_scissors",    "J - Scissors",               "Ramp Type: J - Scissors"),
            _c("ramp_K_split",       "K - Split Ramp",             "Ramp Type: K - Split Ramp"),
            _c("ramp_L_loop_noleft", "L - Loop without Left Turn", "Ramp Type: L - Loop without Left Turn"),
            _c("ramp_M_two_way",     "M - Two way Ramp Segment",   "Ramp Type: M - Two way Ramp Segment"),
            _c("ramp_P_dummy_paired","P - Dummy Paired",           "Ramp Type: P - Dummy Paired"),
            _c("ramp_R_rest_area",   "R - Rest Area, Vista Pt",    "Ramp Type: R - Rest Area, Vista Point, Truck Scale"),
            _c("ramp_V_dummy_volume","V - Dummy, Volume only",     "Ramp Type: V - Dummy, Volume only"),
            _c("ramp_Z_other",       "Z - Other",                  "Ramp Type: Z - Other"),
        )),
    ),
    total=_c("total_ramps", "Total Number of Ramps", "Total Number of Ramps"),
    footnotes=(
        _c("ramp_points_no_linework", "Ramp Points w/out linework",
           "Ramp Points w/out linework"),
    ),
)


# =============================================================================
# Familiar-sheet renderer (write_only-safe; plugged in via extra_sheet_writer)
# =============================================================================

def _as_int(v):
    """A count cell to int, or None when it isn't a plain number."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    s = str(v or "").strip().replace(",", "")
    try:
        return int(s)
    except ValueError:
        return None


def make_extra_sheet_writer(spec):
    """Return an extra_sheet_writer(wb, ctx) that appends `spec`'s familiar
    category-comparison sheet. ctx carries rows_a/rows_b (each [key, count]) and
    the side labels — see compare_core.CompareSchema.extra_sheet_writer."""
    def writer(wb, ctx):
        if not _OPX:
            return None
        return _render(wb, ctx, spec)
    return writer


def _render(wb, ctx, spec):
    sc = ctx["sc"]
    side_a, side_b = sc.side_a, sc.side_b          # the side LABELS ("TSMIS"/"TSN")
    file_a, file_b = ctx.get("side_a", ""), ctx.get("side_b", "")   # the source filenames
    va = {r[0]: _as_int(r[1]) for r in ctx["rows_a"]}
    vb = {r[0]: _as_int(r[1]) for r in ctx["rows_b"]}

    ws = wb.create_sheet(spec.sheet_name)
    ws.sheet_properties.tabColor = _TAB_COLOR
    write_only = getattr(wb, "write_only", False)

    title_font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    title_fill = PatternFill("solid", start_color=_TITLE_FILL)
    sec_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    sec_fill = PatternFill("solid", start_color=_SECTION_FILL)
    head_font = Font(name="Arial", size=10, bold=True)
    body = Font(name="Arial", size=10)
    diff_font = Font(name="Arial", size=10, bold=True, color=_DIFF_FONT)
    note_font = Font(name="Arial", size=9, italic=True, color="595959")
    right = Alignment(horizontal="right")
    left = Alignment(horizontal="left")

    def cell(value, font=body, fill=None, align=None):
        if not write_only:
            return value
        c = WriteOnlyCell(ws, value=value)
        c.font = font
        if fill:
            c.fill = fill
        if align:
            c.alignment = align
        return c

    for col, w in (("A", 34), ("B", 13), ("C", 13), ("D", 10)):
        ws.column_dimensions[col].width = w

    ws.append([cell(spec.title, title_font, title_fill)])
    ws.append([cell(f"Counts per category. Δ = {side_b} − {side_a}; a non-zero Δ is "
                    "flagged. Categories one system doesn't classify show 0 on that "
                    "side (e.g. TSN-only ramp types P / V).", note_font)])
    if file_a or file_b:
        ws.append([cell(f"{side_a} = {file_a}    {side_b} = {file_b}", note_font)])
    ws.append([])
    ws.append([cell("Category", head_font), cell(side_a, head_font, align=right),
               cell(side_b, head_font, align=right), cell("Δ", head_font, align=right)])

    def value_row(label, key):
        a, b = va.get(key), vb.get(key)
        delta = (b - a) if (a is not None and b is not None) else None
        differ = delta is not None and delta != 0
        f = diff_font if differ else body
        return [cell(label, body, align=left),
                cell(a, f, align=right), cell(b, f, align=right),
                cell(delta if delta is not None else "", f, align=right)]

    for sec in spec.sections:
        ws.append([cell(sec.name, sec_font, sec_fill),
                   cell("", sec_font, sec_fill), cell("", sec_font, sec_fill),
                   cell("", sec_font, sec_fill)])
        for c in sec.cats:
            ws.append(value_row(c.label, c.key))

    if spec.total is not None:
        ws.append([])
        a, b = va.get(spec.total.key), vb.get(spec.total.key)
        delta = (b - a) if (a is not None and b is not None) else None
        f = diff_font if (delta is not None and delta != 0) else head_font
        ws.append([cell(spec.total.label, head_font, align=left),
                   cell(a, f, align=right), cell(b, f, align=right),
                   cell(delta if delta is not None else "", f, align=right)])

    if spec.footnotes:
        ws.append([])
        ws.append([cell(f"Reported by {side_a} only (not a {side_b} category):", note_font)])
        for fnote in spec.footnotes:
            a = va.get(fnote.key)
            ws.append([cell(fnote.label, body, align=left),
                       cell(a, body, align=right), cell("", body), cell("", body)])
    return ws

"""build/check_summary_editions.py — the three summaries' second editions (v0.48.0).

Ramp Summary (Excel), Intersection Summary (PDF) and Highway Summary (PDF) each
consolidate into their sibling's exact workbook and compare like it. This check
drives the SHIPPED readers, consolidators and comparisons over synthetic files
generated from one set of numbers (no corpus files):

  * the Ramp Summary Excel reader returns exactly the print reader's record
    shape, and refuses a row outside the censused layout;
  * the Intersection Summary print reader reads BOTH print layouts the site has
    shipped (July: three columns, bracketed headings; October: two columns over
    two pages) count-for-count, from columns found at their NUMBER headings;
  * the Highway Summary print reader reads all 95 categories + the total (split
    across the two columns), carries RURAL-URBAN's "- O -" rows to their parent,
    records the MEDIAN TYPE sub-headings as the Excel's structural 0, and
    refuses a print missing a category;
  * each second edition's consolidated per-route sheet equals its sibling's;
  * the vs-TSN flavors give the base comparison's exact verdict on the same TSN;
  * PDF vs Excel matches when equal, counts a changed cell, and refuses swapped
    or unmarked sides;
  * the cross-environment adapters compare two run folders of each edition.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_summary_editions.py
"""
import sys
from pathlib import Path

from _checklib import Checker, scripts_path, temp_dir
from _hl_fixture_pdf import make_pdf

scripts_path()

from openpyxl import Workbook, load_workbook  # noqa: E402

import compare_env_editions as cee  # noqa: E402
import compare_highway_summary_tsn as hst  # noqa: E402
import compare_intersection_summary_tsn as ist  # noqa: E402
import compare_ramp_summary_tsn as rst  # noqa: E402
import compare_summary_editions as cse  # noqa: E402
import consolidate_highway_summary as chs  # noqa: E402
import consolidate_intersection_summary as cis  # noqa: E402
import consolidate_ramp_summary as crs  # noqa: E402
import consolidate_ramp_summary_excel as rsx  # noqa: E402
import consolidate_tsmis_highway_summary_pdf as hsp  # noqa: E402
import consolidate_tsmis_intersection_summary_pdf as isp  # noqa: E402
import highway_summary_columns as hsc  # noqa: E402
import summary_layout  # noqa: E402
from events import Events  # noqa: E402

c = Checker()
Q = dict(confirm_overwrite=lambda p: True, mode="preview")


class _Quiet(Events):
    def on_log(self, msg):
        pass


def _counts(result):
    co = getattr(result, "comparison_outcome", None)
    k = co.counts if co else None
    return {f: getattr(k, f, None) for f in ("paired_rows", "side_a_only_rows",
                                             "side_b_only_rows", "differing_cells")}


def _sheet(path, name, drop_first=False):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
    finally:
        wb.close()
    return [r[1:] for r in rows] if drop_first else rows


# --------------------------------------------------------------------------- #
# Ramp Summary (Excel)
# --------------------------------------------------------------------------- #
_RS_SECTIONS = (("Highway Groups", crs.HIGHWAY_GROUPS), ("On/Off Indicator", crs.ONOFF),
                ("Population Groups", crs.POP_GROUPS), ("Ramp Types", crs.RAMP_TYPES))
_PV = {"ramp_P_dummy_paired", "ramp_V_dummy_volume"}


def _rs_record(route, total, bump=0):
    """A self-consistent per-route record (each printed section sums to total)."""
    rec = {"route": route, "total_ramps": total, "ramp_points_no_linework": 0}
    for _name, schema in _RS_SECTIONS:
        cols = [col for col, _pat in schema if col not in _PV]
        for i, col in enumerate(cols):
            rec[col] = (total - (len(cols) - 1) + bump) if i == 0 else 1
        if bump:
            rec[cols[1]] -= bump
    return rec


def _rs_xlsx(path, rec):
    wb = Workbook()
    ws = wb.active
    ws.title = rsx.SHEET_NAME
    for line in ("TSAR - RAMPS SUMMARY", f"All Ramps on Route {rec['route']}",
                 "Reference Date: 2026-10-02", "Generated: 10/2/2026, 12:01:13 PM"):
        ws.append([line, None])
    for name, schema in _RS_SECTIONS:
        ws.append([None, None])
        ws.append([name, None])
        ws.append(["NUMBER", "CODE"])
        for col, _pat in schema:
            if col not in _PV:
                ws.append([rec[col], crs.LONG_LABELS[col]])
    ws.append([None, None])
    ws.append(["Total Number of Ramps:", rec["total_ramps"]])
    ws.append(["Ramp Points w/out linework:", rec["ramp_points_no_linework"]])
    wb.save(path)


def test_ramp_summary(tmp):
    print("Ramp Summary (Excel): the print's record, its workbook, its comparisons:")
    recs = [_rs_record("001", 40), _rs_record("005", 75)]
    day_a = tmp / "2026-10-01 ssor-prod" / "ramp_summary_excel"
    day_b = tmp / "2026-10-02 ssor-prod" / "ramp_summary_excel"
    for d in (day_a, day_b):
        d.mkdir(parents=True)
    for rec in recs:
        _rs_xlsx(day_b / f"tsar_ramp_summary_route_{rec['route']}.xlsx", rec)
        _rs_xlsx(day_a / f"tsar_ramp_summary_route_{rec['route']}.xlsx",
                 _rs_record(rec["route"], rec["total_ramps"], bump=1 if rec["route"] == "005" else 0))
    got = rsx.parse_xlsx(str(day_b / "tsar_ramp_summary_route_005.xlsx"))
    want = dict(recs[1], source_file="tsar_ramp_summary_route_005.xlsx",
                ramp_P_dummy_paired=None, ramp_V_dummy_volume=None,
                _unknown_rows=[], _duplicate_rows=[])
    c.check("parse_xlsx returns the print reader's exact record shape and values",
            got == want, {k: (got.get(k), want.get(k)) for k in set(got) | set(want)
                          if got.get(k) != want.get(k)})
    c.check("...which reconciles like a print record", crs.reconcile_problem(got) is None)
    bad = tmp / "bad.xlsx"
    _rs_xlsx(bad, recs[0])
    wb = load_workbook(bad)
    wb.active.append(["Something new the site added", 7])
    wb.save(bad)
    try:
        rsx.parse_xlsx(str(bad))
        c.check("a row outside the censused layout refuses the file", False, "no error")
    except ValueError as e:
        c.check("a row outside the censused layout refuses the file", "layout" in str(e), str(e))
    xl = tmp / "rs_excel.xlsx"
    res = rsx.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                          input_dir=day_b, out_path=xl)
    c.check("the Excel edition consolidates COMPLETE", res.status == "ok"
            and res.completion == "complete", res.message)
    pdf = tmp / "rs_pdf.xlsx"
    print_recs = [dict(r, source_file=f"tsar_ramp_summary_route_{r['route']}.pdf",
                       _unknown_rows=[], _duplicate_rows=[]) for r in recs]
    crs.build_workbook(print_recs, pdf, pdf_marker=True)
    c.check("...into the print consolidation's exact per-route sheet (bar the file names)",
            _sheet(xl, crs.SUMMARY_SHEET_NAME, True) == _sheet(pdf, crs.SUMMARY_SHEET_NAME, True))
    pve = _counts(cse.RAMP_SUMMARY_PDF_VS_EXCEL.compare(str(pdf), str(xl), str(tmp / "p.xlsx"),
                                                       events=_Quiet(), **Q))
    c.check("PDF vs Excel of the same numbers matches",
            pve == {"paired_rows": 2, "side_a_only_rows": 0, "side_b_only_rows": 0,
                    "differing_cells": 0}, pve)
    for label, a, b in (("swapped sides refuse", xl, pdf), ("an unmarked PDF side refuses", xl, xl)):
        r = cse.RAMP_SUMMARY_PDF_VS_EXCEL.compare(str(a), str(b), str(tmp / "g.xlsx"),
                                                  events=_Quiet(), **Q)
        c.check(f"PDF vs Excel: {label}", r.status == "error", r.status)
    tsn = tmp / "rs_tsn.xlsx"
    _summary_tsn(tsn, rst.NORMALIZED_SHEET, ["Category", "Count"],
                 rst._SPEC, _statewide(recs, rst._SPEC))
    base = _counts(rst.compare(str(pdf), str(tsn), str(tmp / "b.xlsx"), events=_Quiet(), **Q))
    new = _counts(cse.RAMP_SUMMARY_EXCEL_VS_TSN.compare(str(xl), str(tsn), str(tmp / "n.xlsx"),
                                                        events=_Quiet(), **Q))
    c.check("the Excel vs-TSN flavor gives the print comparison's exact verdict",
            new == base and base["paired_rows"], (base, new))
    r = cse.RAMP_SUMMARY_EXCEL_VS_TSN.compare(str(pdf), str(tsn), str(tmp / "g2.xlsx"),
                                              events=_Quiet(), **Q)
    c.check("the Excel vs-TSN flavor refuses a print consolidation", r.status == "error")
    env = _counts(cee.RAMP_SUMMARY_EXCEL.compare_folders(
        str(day_a.parent), str(day_b.parent), str(tmp / "e.xlsx"), events=_Quiet(), **Q))
    c.check("between environments: the one route that moved a ramp between two "
            "categories differs in exactly those two cells",
            env == {"paired_rows": 2, "side_a_only_rows": 0, "side_b_only_rows": 0,
                    "differing_cells": 8}, env)


def _statewide(recs, spec):
    """{category key: statewide count} for a summary spec from per-route records."""
    out = {}
    for key, slug in spec.categories_for("tsn"):
        out[key] = sum(int(r.get(slug) or 0) for r in recs)
    return out


def _summary_tsn(path, sheet, header, spec, values):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for key, _slug in spec.categories_for("tsn"):
        ws.append([key, values[key]])
    wb.save(path)


# --------------------------------------------------------------------------- #
# Intersection Summary (PDF)
# --------------------------------------------------------------------------- #
_IS = summary_layout.INTERSECTION_SUMMARY_SPEC
_RU = {"R": "R-RURAL -I INSIDE CITY", "R-O": "-O OUTSIDE CITY",
       "U": "U-URBAN -I INSIDE CITY", "U-O": "-O OUTSIDE CITY", "+": "+-INVALID DATA"}


def _is_label(sec, cat):
    """How the site prints a category (the Excel export's own wording)."""
    if sec.name == summary_layout._IS_RURAL_URBAN:
        return _RU[cat.code]
    if sec.name == "MAINLINE NUM OF LANES" and cat.code.isdigit():
        return cat.code
    return f"{cat.code}-{cat.label.split(' - ', 1)[1]}"


def _is_header(sec):
    return sec.aliases[0] if sec.aliases else sec.name     # the site prints MASTERARM


def _is_counts(total, shift=0):
    counts = {}
    for sec in _IS.sections:
        n = len(sec.cats)
        for i, cat in enumerate(sec.cats):
            counts[cat.slug] = (total - (n - 1) + shift) if i == 0 else 1
        if shift:
            counts[sec.cats[1].slug] -= shift
    return counts


def _is_block_lines(sec, counts, x, top, bracket):
    """One block's lines. The July print (`bracket`) clips every label at its
    column's edge (the real prints show 'N-NO LEFT TURN CHANNELIZAT'); only the
    leading code is identity, so the fixture clips the same way."""
    head = f"<-----{_is_header(sec)}----->" if bracket else _is_header(sec)
    lines = [(x - 3 if bracket else x, top, head)]
    sub = "LANES" if sec.name == "MAINLINE NUM OF LANES" else "CODE"
    lines += [(x, top + 12, "NUMBER"), (x + 40, top + 12, sub)]
    for j, cat in enumerate(sec.cats):
        label = _is_label(sec, cat)
        lines += [(x, top + 24 + 12 * j, str(counts[cat.slug])),
                  (x + 40, top + 24 + 12 * j, label[:22] if bracket else label)]
    return lines, top + 24 + 12 * len(sec.cats) + 14


def _is_pdf(path, route, counts, total, layout):
    cover = [(40, 40, "TASAS Selective Record Retrieval"), (40, 60, "REPORT PARAMETERS:"),
             (40, 80, "LOCATION CRITERIA:"), (40, 92, f"ROUTE {route}")]
    head = [(28, 40, "TSAR - Intersection Summary"),
            (28, 52, f"District: ALL County: ALL Route: {route} Direction: S - N"),
            (28, 64, f"Total Intersections = {total}")]
    if layout == "july":                      # three columns, one page, bracketed
        cols = [[], [], []]
        for i, sec in enumerate(_IS.sections):
            cols[i % 3].append(sec)
        page = list(head)
        for k, secs in enumerate(cols):
            top = 90
            for sec in secs:
                lines, top = _is_block_lines(sec, counts, 20 + 180 * k, top, True)
                page += lines
        make_pdf(path, [cover, page])
        return
    pages = [list(head), []]                  # two columns over two pages
    tops = {(0, 0): 90, (0, 1): 90, (1, 0): 40, (1, 1): 40}
    for i, sec in enumerate(_IS.sections):
        pg, col = (0 if i < 6 else 1), i % 2
        lines, tops[(pg, col)] = _is_block_lines(sec, counts, 46 + 287 * col,
                                                 tops[(pg, col)], False)
        pages[pg] += lines
    make_pdf(path, [cover] + pages)


def _is_xlsx(path, route, counts, total):
    wb = Workbook()
    ws = wb.active
    ws.title = cis.SHEET_NAME
    ws.append(["TSAR - Intersection Summary", None])
    ws.append([f"Route: {route}", None])
    ws.append([f"Total Intersections = {total}", None])
    for sec in _IS.sections:
        ws.append([None, None])
        ws.append([_is_header(sec), None])
        ws.append(["NUMBER", "LANES" if sec.name == "MAINLINE NUM OF LANES" else "CODE"])
        for cat in sec.cats:
            ws.append([counts[cat.slug], _is_label(sec, cat)])
    wb.save(path)


def test_intersection_summary(tmp):
    print("Intersection Summary (PDF): both print layouts, the workbook, comparisons:")
    counts, total = _is_counts(60), 60
    for layout in ("july", "october"):
        p = tmp / f"is_{layout}_route_001.pdf"
        _is_pdf(p, "001", counts, total, layout)
        route, got, got_total = isp.parse_pdf(str(p))
        c.check(f"the {layout} layout reads count-for-count (route + total too)",
                route == "001" and got_total == total and got == counts,
                {k: (got.get(k), counts.get(k)) for k in counts if got.get(k) != counts.get(k)})
        c.check(f"...and passes the strict partition validator ({layout})",
                cis.record_problem(got, got_total) is None)
    days = {}
    for tag, shift in (("2026-10-01", 1), ("2026-10-02", 0)):
        run = tmp / f"{tag} ssor-prod"
        (run / "intersection_summary_pdf").mkdir(parents=True)
        (run / "intersection_summary").mkdir(parents=True)
        for route, t in (("001", 60), ("005", 90)):
            cc = _is_counts(t, shift if route == "005" else 0)
            _is_pdf(run / "intersection_summary_pdf" / f"intersection_summary_route_{route}.pdf",
                    route, cc, t, "october")
            _is_xlsx(run / "intersection_summary" / f"intersection_summary_route_{route}.xlsx",
                     route, cc, t)
        days[tag] = run
    run = days["2026-10-02"]
    pdf_wb, xl_wb = tmp / "is_pdf.xlsx", tmp / "is_xl.xlsx"
    r1 = isp.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                         input_dir=run / "intersection_summary_pdf", out_path=pdf_wb)
    r2 = cis.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                         input_dir=run / "intersection_summary", out_path=xl_wb)
    c.check("both editions consolidate COMPLETE", r1.completion == r2.completion == "complete",
            (r1.message, r2.message))
    c.check("...into the identical per-route sheet",
            _sheet(pdf_wb, cis.SHEET_NAME) == _sheet(xl_wb, cis.SHEET_NAME))
    pve = _counts(cse.INTERSECTION_SUMMARY_PDF_VS_EXCEL.compare(
        str(pdf_wb), str(xl_wb), str(tmp / "p.xlsx"), events=_Quiet(), **Q))
    c.check("PDF vs Excel matches", pve["differing_cells"] == 0 and pve["paired_rows"] == 2, pve)
    tsn = tmp / "is_tsn.xlsx"
    recs = [{"counts": _is_counts(60)}, {"counts": _is_counts(90)}]
    flat = [dict(r["counts"]) for r in recs]
    vals = _statewide(flat, _IS)
    vals[_IS.total.key] = 150
    _summary_tsn_total(tsn, ist.NORMALIZED_SHEET, _IS, vals)
    base = _counts(ist.compare(str(xl_wb), str(tsn), str(tmp / "b.xlsx"), events=_Quiet(), **Q))
    new = _counts(cse.INTERSECTION_SUMMARY_PDF_VS_TSN.compare(
        str(pdf_wb), str(tsn), str(tmp / "n.xlsx"), events=_Quiet(), **Q))
    c.check("the print vs-TSN flavor gives the Excel comparison's exact verdict",
            new == base and base["paired_rows"], (base, new))
    env = _counts(cee.INTERSECTION_SUMMARY_PDF.compare_folders(
        str(days["2026-10-01"]), str(days["2026-10-02"]), str(tmp / "e.xlsx"),
        events=_Quiet(), **Q))
    c.check("between environments: the route that moved one intersection per block "
            "differs, the other matches",
            env["paired_rows"] == 2 and env["differing_cells"] == 2 * len(_IS.sections), env)
    # An unreadable print on one side is a skipped input: the comparison of the
    # rest is still written, but it can never read complete (fail-closed truth).
    (days["2026-10-02"] / "intersection_summary_pdf"
     / "intersection_summary_route_008.pdf").write_bytes(b"%PDF-1.4 not a real print")
    res = cee.INTERSECTION_SUMMARY_PDF.compare_folders(
        str(days["2026-10-01"]), str(days["2026-10-02"]), str(tmp / "e2.xlsx"),
        events=_Quiet(), **Q)
    c.check("between environments: an unreadable print makes the result partial, "
            "never complete",
            res.status == "ok" and res.completion == "partial" and res.skipped_inputs >= 1,
            (res.status, res.completion, res.skipped_inputs))


def _summary_tsn_total(path, sheet, spec, values):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["Category", "Count"])
    ws.append([spec.total.key, values[spec.total.key]])
    for key, _slug in spec.categories_for("tsn"):
        if key != spec.total.key:
            ws.append([key, values[key]])
    wb.save(path)


# --------------------------------------------------------------------------- #
# Highway Summary (PDF)
# --------------------------------------------------------------------------- #
def _hs_values(total_milli, shift=0):
    vals = {}
    for sec in hsc.SECTIONS:
        n = len(sec.cats)
        for i, cat in enumerate(sec.cats):
            if cat.label in ("(UNDIVIDED)", "(DIVIDED)"):
                vals[cat.slug] = 0
            elif sec.independent:
                vals[cat.slug] = 76
            else:
                vals[cat.slug] = (total_milli // 2 + shift) if i == 0 else 100
    return vals


def _miles(milli):
    return f"{milli / 1000:.3f}"


def _hs_print_label(sec, cat):
    """How the print shows a category: its label with the spacing collapsed, the
    RURAL-URBAN second rows without their parent, the MEDIAN TYPE sub-headings
    without a value."""
    text = " ".join(cat.label.split())
    if sec.name == "RURAL-URBAN" and " - O - " in text:
        return text[text.index("- O -"):]
    return text


def _hs_section_lines(sec, vals, x, top):
    lines = [(x, top, sec.name), (x, top + 11, "CODE"), (x + 200, top + 11, "MILES")]
    for j, cat in enumerate(sec.cats):
        y = top + 22 + 11 * j
        lines.append((x, y, _hs_print_label(sec, cat)))
        if cat.label not in ("(UNDIVIDED)", "(DIVIDED)"):
            lines.append((x + 200, y, _miles(vals[cat.slug])))
    return lines, top + 22 + 11 * len(sec.cats) + 12


def _hs_pdf(path, route, vals, total):
    cover = [(40, 40, "TSAR - HIGHWAY SUMMARY"), (40, 60, "REPORT PARAMETERS:"),
             (40, 80, "LOCATION CRITERIA:"), (40, 92, f"ROUTE {route}")]
    pages = [[(40, 30, "*TOTAL MILES SELECTED"), (330, 30, _miles(total))]]
    # The two columns sit at x=40 and x=320, each with its miles 200 pt right of
    # its labels (the real print's spacing keeps the longest label clear).
    layout = [("HIGHWAY GROUP", "NON-ADD"), ("ACCESS CONTROL", "RURAL-URBAN"),
              ("MEDIAN TYPE", "MEDIAN BARRIER"), ("NUMBER OF LANES", "MEDIAN WIDTH"),
              ("TERRAIN", "DESIGN SPEED")]
    by_name = {s.name: s for s in hsc.SECTIONS}
    tops = [50, 50]
    for left, right in layout:
        if tops[0] > 300 or tops[1] > 300:
            pages.append([])
            tops = [40, 40]
        for k, name in enumerate((left, right)):
            lines, tops[k] = _hs_section_lines(by_name[name], vals, 40 + 280 * k, tops[k])
            pages[-1] += lines
    make_pdf(path, [cover] + pages)


def _hs_xlsx(path, vals, total):
    wb = Workbook()
    ws = wb.active
    ws.title = hsc.SHEET_NAME
    ws.append([hsc.TITLE_LINE, None])
    ws.append([hsc.SUBTITLE_LINE, None])
    ws.append([None, None])
    ws.append([hsc.TOTAL_LABEL, total / 1000])
    for sec in hsc.SECTIONS:
        ws.append([None, None])
        ws.append([sec.name, None])
        ws.append(["Code", "Miles"])
        for cat in sec.cats:
            ws.append([cat.label, vals[cat.slug] / 1000])
    wb.save(path)


def test_highway_summary(tmp):
    print("Highway Summary (PDF): all 95 categories + the split total, the workbook:")
    vals, total = _hs_values(100_000), 100_000
    p = tmp / "highway_summary_route_005.pdf"
    _hs_pdf(p, "005", vals, total)
    route, got, got_total = hsp.parse_pdf(str(p))
    c.check("the print reads every category to the thousandth, plus the total",
            route == "005" and got_total == total and got == vals,
            {k: (got.get(k), vals.get(k)) for k in vals if got.get(k) != vals.get(k)})
    c.check("...and passes the partition validator",
            chs.record_problem(got, got_total, source=p.name) is None)
    short = tmp / "highway_summary_route_006.pdf"
    clipped = dict(vals)
    _hs_pdf(short, "006", clipped, total)
    # drop one category line from the print: re-generate without TERRAIN's 'Z' row
    cat = next(c_ for s in hsc.SECTIONS if s.name == "TERRAIN" for c_ in s.cats if c_.code == "Z")
    saved = hsc.SECTIONS
    try:
        terr = next(s for s in saved if s.name == "TERRAIN")
        import dataclasses
        trimmed = tuple(dataclasses.replace(s, cats=tuple(x for x in s.cats if x is not cat))
                        if s is terr else s for s in saved)
        hsc.SECTIONS = trimmed
        _hs_pdf(short, "006", clipped, total)
    finally:
        hsc.SECTIONS = saved
    try:
        hsp.parse_pdf(str(short))
        c.check("a print missing a category refuses", False, "no error")
    except ValueError as e:
        c.check("a print missing a category refuses, naming it", "TERRAIN" in str(e), str(e))
    days = {}
    for tag, shift in (("2026-10-01", 7), ("2026-10-02", 0)):
        run = tmp / f"{tag} ssor-prod"
        (run / "highway_summary_pdf").mkdir(parents=True)
        (run / "highway_summary").mkdir(parents=True)
        for rt in ("001", "005"):
            v = _hs_values(100_000, shift if rt == "005" else 0)
            _hs_pdf(run / "highway_summary_pdf" / f"highway_summary_route_{rt}.pdf", rt, v, total)
            _hs_xlsx(run / "highway_summary" / f"highway_summary_route_{rt}.xlsx", v, total)
        days[tag] = run
    run = days["2026-10-02"]
    pdf_wb, xl_wb = tmp / "hs_pdf.xlsx", tmp / "hs_xl.xlsx"
    r1 = hsp.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                         input_dir=run / "highway_summary_pdf", out_path=pdf_wb)
    r2 = chs.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                         input_dir=run / "highway_summary", out_path=xl_wb)
    c.check("both editions consolidate COMPLETE", r1.completion == r2.completion == "complete",
            (r1.message, r2.message))
    c.check("...into the identical per-route sheet",
            _sheet(pdf_wb, hsc.SHEET_NAME) == _sheet(xl_wb, hsc.SHEET_NAME))
    pve = _counts(cse.HIGHWAY_SUMMARY_PDF_VS_EXCEL.compare(
        str(pdf_wb), str(xl_wb), str(tmp / "p.xlsx"), events=_Quiet(), **Q))
    c.check("PDF vs Excel matches", pve["differing_cells"] == 0 and pve["paired_rows"] == 2, pve)
    tsn = tmp / "hs_tsn.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = hst.NORMALIZED_SHEET
    ws.append(["Category", "Miles"])
    ws.append([hsc.TOTAL_KEY, 2 * total / 1000])
    for cat in hsc.cats_for("tsn"):
        ws.append([cat.key, 2 * vals[cat.slug] / 1000])
    wb.save(tsn)
    base = _counts(hst.compare(str(xl_wb), str(tsn), str(tmp / "b.xlsx"), events=_Quiet(), **Q))
    new = _counts(cse.HIGHWAY_SUMMARY_PDF_VS_TSN.compare(
        str(pdf_wb), str(tsn), str(tmp / "n.xlsx"), events=_Quiet(), **Q))
    c.check("the print vs-TSN flavor gives the Excel comparison's exact verdict",
            new == base and base["paired_rows"], (base, new))
    env = _counts(cee.HIGHWAY_SUMMARY_PDF.compare_folders(
        str(days["2026-10-01"]), str(days["2026-10-02"]), str(tmp / "e.xlsx"),
        events=_Quiet(), **Q))
    c.check("between environments: the shifted route differs, the other matches",
            env["paired_rows"] == 2 and env["differing_cells"] > 0, env)


def main():
    with temp_dir("tsmis_sumed_") as tmp:
        tmp = Path(tmp)
        for name, fn in (("rs", test_ramp_summary), ("is", test_intersection_summary),
                         ("hs", test_highway_summary)):
            sub = tmp / name
            sub.mkdir()
            fn(sub)
    return c.summary()


if __name__ == "__main__":
    sys.exit(main())

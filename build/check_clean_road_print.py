"""build/check_clean_road_print.py — the Clean Road print reader (v0.48.0).

`clean_road_print.read_print` reads the site's `*_printAll` PDF back into the
Excel export's rows from the print's VECTOR structure (header cell rectangles,
glyph baselines, glyph gaps) with pypdfium2. This drives the shipped reader over
REAL Chromium prints of a synthetic Clean Road Ramp table — the same producer
(Chromium's Skia PDF backend) the site's prints come from — at two scales,
including the dense scale where neighbouring rows sit closer than pdfplumber's
3-pt default would separate:

  * every printed column is named back to its key by the site's label rule,
    and the unprinted columns come back blank;
  * every cell reads back exactly (multi-word text, dates, decimals), on every
    page (the header repeats), and the cover's ROUTE claim is returned;
  * a print with a column label the report doesn't have REFUSES by name;
  * a row carrying a cell beyond the header's columns (the site adding a body
    column without its header) refuses instead of shifting values;
  * a PDF that isn't a Clean Road print (no table), or a cover with no data
    page, refuses.

No corpus files: everything is generated here. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_clean_road_print.py
"""
import html
import sys

from _checklib import Checker, scripts_path, temp_dir

scripts_path()

import clean_road_columns as crc  # noqa: E402
import clean_road_print as crp  # noqa: E402

c = Checker()

# A subset of the Ramp print's columns, in the site's order (the reader must
# not need every column printed — the site prints only what it sources).
COLUMNS = ["RAM_NETWORK_ID", "RAM_PRIMARY_DIRECTION_CODE", "RAM_DESIGN_CODE",
           "RAM_DESIGN_DESC", "RAM_BEGIN_DATE", "RAM_COUNTY_CODE", "RAM_ROUTE_NAME",
           "RAM_PM_PREFIX_CODE", "RAM_PM_LOC_AMT", "RAM_ON_OFF_CODE",
           "RAM_DESCRIPTION", "RAM_EXTRACT_DATE"]


def _rows(n):
    out = []
    for i in range(n):
        out.append({
            "RAM_NETWORK_ID": "2",
            "RAM_PRIMARY_DIRECTION_CODE": "N" if i % 2 else "S",
            "RAM_DESIGN_CODE": "DFLG"[i % 4],
            "RAM_DESIGN_DESC": ["D- Diamond Type Ramp", "F- Direct or Semi-Direct Connector (Right)",
                                "L- Loop-w/o Left Turn", "G- Loop w/ Left Turn"][i % 4],
            "RAM_BEGIN_DATE": f"0{1 + i % 9}/2{i % 9}/19{70 + i % 30}",
            "RAM_COUNTY_CODE": "LA." if i % 3 == 0 else "ORA",
            "RAM_ROUTE_NAME": "005",
            "RAM_PM_PREFIX_CODE": "R" if i % 5 == 0 else "",
            "RAM_PM_LOC_AMT": f"{i * 0.137:.3f}".rstrip("0").rstrip(".") or "0",
            "RAM_ON_OFF_CODE": ["ON", "OFF", "Z"][i % 3],
            "RAM_DESCRIPTION": f"005/NB OFF TO {['MAIN ST', 'EL CAMINO REAL', '7TH AVE RT'][i % 3]} {i}",
            "RAM_EXTRACT_DATE": "10/02/2026",
        })
    return out


def _header_html(key, label=None):
    text = label if label is not None else crc.printed_label(key, "RAM_")
    return "<br>".join(html.escape(part) for part in text.split("\n"))


def _page(columns, rows, *, font_px, route="005S", bad_label=None, stray=False):
    head = "".join(
        f"<th>{_header_html(k, bad_label if (bad_label and i == 3) else None)}</th>"
        for i, k in enumerate(columns))
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(r[k])}</td>" for k in columns)
        + ("<td>STRAY</td>" if stray and n == 0 else "") + "</tr>"
        for n, r in enumerate(rows))
    # The site's own print CSS (styles.css .clh-table + its @media print rules,
    # 9.1 capture) and the clh_printAll structure: a cover page, then the table
    # inside .clh-print-body scaled by `zoom` (the site scales to the sheet width).
    zoom = font_px / 11.2                 # .clh-table is 0.7rem = 11.2 px
    return f"""<!doctype html><html><head><style>
html, body {{ margin: 0; background: #fff; font-family: "Segoe UI", Arial, sans-serif; }}
.rs-cover {{ page-break-after: always; font-size: 12px; }}
.clh-table {{ border-collapse: collapse; font-size: 0.7rem; white-space: nowrap; }}
.clh-table th {{ font-size: 0.58rem; text-align: center; font-weight: 700; color: #9ca3af;
  text-transform: uppercase; letter-spacing: 0.02em; padding: 0.2rem 0.4rem;
  border-bottom: 1px solid #e5e7eb; background: #fff; }}
.clh-table td {{ padding: 0.15rem 0.4rem; text-align: center; border-bottom: 1px solid #f3f4f6; }}
.clh-print-body .clh-table thead {{ display: table-header-group; }}
.clh-print-body .clh-table tbody tr {{ break-inside: avoid; }}
.clh-print-body .clh-table tbody tr:nth-child(even) {{ background: #eef0f2;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
</style></head><body><div class="clh-print-root">
<div class="rs-cover"><div>California Department of Transportation</div>
<div>Clean Road File &mdash; Ramp</div><div>LOCATION CRITERIA:</div>
<table><tr><td>ROUTE</td><td></td><td>{route}</td></tr></table></div>
<div class="clh-print-body" style="zoom:{zoom:.4f}"><div class="clh-table-wrap">
<table class="clh-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
</div></div></div></body></html>"""


def _print(page, markup, path):
    page.set_content(markup)
    page.pdf(path=str(path), format="Letter", landscape=True, print_background=True,
             margin={"top": "0.35in", "bottom": "0.35in", "left": "0.35in",
                     "right": "0.35in"})


def _launch(p):
    for channel in ("chromium", "msedge", "chrome"):
        try:
            return p.chromium.launch(headless=True, channel=channel)
        except Exception as e:  # noqa: BLE001
            print(f"  (channel {channel} unavailable: {type(e).__name__})")
    return None


def main():
    from playwright.sync_api import sync_playwright
    rows = _rows(240)
    with temp_dir("tsmis_crprint_") as tmp, sync_playwright() as p:
        browser = _launch(p)
        if browser is None:
            print("no drivable Chromium-based browser — cannot print the fixtures")
            return 1
        try:
            page = browser.new_context().new_page()
            for font_px in (7, 2.2):
                pdf = tmp / f"ramp_{font_px}.pdf"
                _print(page, _page(COLUMNS, rows, font_px=font_px), pdf)
                read = crp.read_print(pdf, crc.RAMP)
                c.check(f"[{font_px}px] the print spans several data pages (header repeats)",
                        read.pages >= 3, f"pages={read.pages}")
                c.check(f"[{font_px}px] every printed column is named back to its key",
                        list(read.printed) == COLUMNS, f"printed={read.printed}")
                c.check(f"[{font_px}px] every record reads back (none merged or lost)",
                        len(read.rows) == len(rows), f"{len(read.rows)} of {len(rows)}")
                idx = {k: i for i, k in enumerate(crc.RAMP.header)}
                bad = [(n, k, r[idx[k]], want[k]) for n, (r, want) in enumerate(zip(read.rows, rows))
                       for k in COLUMNS if r[idx[k]] != want[k]]
                c.check(f"[{font_px}px] every cell reads back exactly", not bad, f"first: {bad[:3]}")
                blank = all(r[idx[k]] == "" for r in read.rows
                            for k in crc.RAMP.header if k not in COLUMNS)
                c.check(f"[{font_px}px] the columns the print leaves out come back blank", blank)
                c.check(f"[{font_px}px] the cover's ROUTE claim is returned",
                        read.route_claim == "005S", repr(read.route_claim))
            # refusals
            pdf = tmp / "bad_label.pdf"
            _print(page, _page(COLUMNS, rows[:20], font_px=7, bad_label="BOGUS\nCOLUMN"), pdf)
            try:
                crp.read_print(pdf, crc.RAMP)
                c.check("an unknown printed column refuses", False, "no error raised")
            except ValueError as e:
                c.check("an unknown printed column refuses, naming the label",
                        "BOGUS" in str(e), str(e))
            pdf = tmp / "stray_cell.pdf"
            _print(page, _page(COLUMNS, rows[:20], font_px=7, stray=True), pdf)
            try:
                crp.read_print(pdf, crc.RAMP)
                c.check("a cell beyond the header's columns refuses", False, "no error raised")
            except ValueError as e:
                c.check("a cell beyond the header's columns refuses (text outside every column)",
                        "outside every column" in str(e), str(e))
            pdf = tmp / "cover_only.pdf"
            page.set_content("<p>LOCATION CRITERIA: ROUTE 005</p>")
            page.pdf(path=str(pdf), format="Letter", landscape=True)
            try:
                crp.read_print(pdf, crc.RAMP)
                c.check("a cover with no data page refuses", False, "no error raised")
            except ValueError as e:
                c.check("a cover with no data page refuses", "no data pages" in str(e), str(e))
            pdf = tmp / "not_a_print.pdf"
            page.set_content("<p>cover</p><div style='page-break-before:always'>"
                             "just some text, no table</div>")
            page.pdf(path=str(pdf), format="Letter", landscape=True)
            try:
                crp.read_print(pdf, crc.RAMP)
                c.check("a PDF without the print's table refuses", False, "no error raised")
            except ValueError as e:
                c.check("a PDF without the print's table refuses", "no table" in str(e), str(e))
        finally:
            browser.close()
    # The label rule is the site's: spot-check the abbreviations + the balanced split.
    c.check("label rule: PREFIX/SUFFIX abbreviate and split at the balanced cut",
            crc.printed_label("RAM_PM_PREFIX_CODE", "RAM_") == "PM_PFX\nCODE"
            and crc.printed_label("THY_LT_O_SHD_TOT_WIDTH_AMT", "THY_") == "LT_O_SHD_TOT\nWIDTH_AMT"
            and crc.printed_label("RAM_DESCRIPTION", "RAM_") == "DESCRIPTION",
            [crc.printed_label("RAM_PM_PREFIX_CODE", "RAM_"),
             crc.printed_label("THY_LT_O_SHD_TOT_WIDTH_AMT", "THY_")])
    return c.summary()


if __name__ == "__main__":
    sys.exit(main())

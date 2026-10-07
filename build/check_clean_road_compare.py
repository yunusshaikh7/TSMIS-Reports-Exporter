"""build/check_clean_road_compare.py — the site's Clean Road files vs TSN (v0.48.0).

Drives the SHIPPED path end to end on synthetic data (no corpus files): the
Excel consolidators over per-route exports in the site's layout, then the
`compare_clean_road_tsn` comparisons against TSN extracts in the raw `Sheet 1`
layout and through the TSN library's normalized copy, then the cross-
environment adapters over two run folders. Pinned:

  * the measured format reconciliations pair and equalize — county 'LA.' =
    'LA', TSN's domain-prefixed design codes ('RD' = 'D', 'IT' = 'T'), the
    signal fold (TSN 'P' = 'S'), On/Off 'Z' = 'OTH', the site's MM/DD/YYYY and
    YY-MM-DD dates against TSN datetimes, blank toll/forest = 0, a route
    suffix written in the name ('005S' + 'S' = '005S'), the equation marker 'E'
    in the postmile suffix (paired, the column itself still counted);
  * a real value difference counts, a context column difference never does,
    and a record only one side carries is one-sided;
  * the library's normalized copy reads exactly like the raw extract;
  * role gates: the print flavors require the PDF-conversion marker, the
    Excel flavors and the self-check's Excel side refuse it, and the TSN side
    refuses a site workbook or the ArcGIS build;
  * the PDF-vs-Excel self-check matches across a collapsed whitespace run;
  * between environments, a changed cell counts and a ramp the site lists in
    another route's file stays paired (keyed on the file's route token).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_clean_road_compare.py
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

from _checklib import Checker, scripts_path, temp_dir

scripts_path()

from openpyxl import Workbook, load_workbook  # noqa: E402

import clean_highway_columns as chc  # noqa: E402
import clean_road_columns as crc  # noqa: E402
import compare_clean_road_tsn as crt  # noqa: E402
import compare_env_editions as cee  # noqa: E402
import consolidate_clean_road_highway as con_hwy  # noqa: E402
import consolidate_clean_road_intersection as con_inx  # noqa: E402
import consolidate_clean_road_ramp as con_ram  # noqa: E402
import tsn_load_clean_road as tlc  # noqa: E402
from events import Events  # noqa: E402
from pdf_table_lib import write_pdf_source_marker  # noqa: E402

c = Checker()


class _Quiet(Events):
    def on_log(self, msg):
        pass


def _counts(result):
    co = getattr(result, "comparison_outcome", None)
    k = co.counts if co else None
    return {f: getattr(k, f, None) for f in ("paired_rows", "side_a_only_rows",
                                             "side_b_only_rows", "differing_cells")}


def _site_file(path, spec, rows):
    """One per-route site export: the export's own sheet + exact header, text cells."""
    wb = Workbook()
    ws = wb.active
    ws.title = spec.sheet
    ws.append(list(spec.header))
    for r in rows:
        ws.append([r.get(h, "") or None for h in spec.header])
    wb.save(path)


def _tsn_file(path, spec, rows):
    """A TSN extract in the raw layout: one visible 'Sheet 1', the exact header."""
    wb = Workbook()
    ws = wb.active
    ws.title = crc.TSN_RAW_SHEET
    ws.append(list(spec.tsn_header))
    for r in rows:
        ws.append([r.get(h) for h in spec.tsn_header])
    wb.save(path)


def _mark_pdf(src, dst):
    """A copy of a consolidated workbook stamped as a PDF conversion."""
    wb = load_workbook(src)
    write_pdf_source_marker(wb)
    wb.save(dst)


def _consolidate(mod, in_dir, out):
    res = mod.consolidate(events=_Quiet(), confirm_overwrite=lambda p: True,
                          input_dir=in_dir, out_path=out)
    c.check(f"{mod.__name__}: consolidates the per-route exports",
            res.status == "ok" and res.completion == "complete", res.message)
    return out


def _ramp(pm, **kw):
    base = {"RAM_NETWORK_ID": "2", "RAM_PRIMARY_DIRECTION_CODE": "N",
            "RAM_DESIGN_CODE": "D", "RAM_DESIGN_DESC": "D- Diamond Type Ramp",
            "RAM_BEGIN_DATE": "02/25/1976", "RAM_DISTRICT_CODE": "07",
            "RAM_COUNTY_CODE": "LA.", "RAM_ROUTE_NAME": "005", "RAM_PM_LOC_AMT": pm,
            "RAM_ON_OFF_CODE": "Z", "RAM_AREA_4_IND": "Y",
            "RAM_DESCRIPTION": f"005/NB OFF TO ST {pm}", "RAM_EXTRACT_DATE": "10/02/2026"}
    base.update(kw)
    return base


def _tsn_ramp(pm, **kw):
    base = {"RAM_ROUTE_ID": 1, "RAM_NETWORK_ID": 2, "RAM_PRIMARY_DIRECTION_CODE": "N",
            "RAM_DESIGN_CODE": "RD", "RAM_DESIGN_DESC": "Diamond Type Ramp",
            "RAM_BEGIN_DATE": datetime(1976, 2, 25), "RAM_DISTRICT_CODE": "07",
            "RAM_COUNTY_CODE": "LA", "RAM_ROUTE_NAME": "005", "RAM_PM_LOC_AMT": float(pm),
            "RAM_ON_OFF_CODE": "OTH", "RAM_AREA_4_IND": "Y",
            "RAM_DESCRIPTION": f"005/NB OFF TO ST {pm}", "RAM_ADT": 1001,
            "RAM_EXTRACT_DATE": datetime(2025, 9, 8)}
    base.update(kw)
    return base


def test_ramp(tmp):
    print("Ramp: reconciliations, a counted difference, context, one-sided, gates:")
    spec = crc.RAMP
    run = tmp / "2026-10-02 ssor-prod" / spec.key
    run.mkdir(parents=True)
    _site_file(run / "2026-10-02 ssor-prod clean_ramp_route_005.xlsx", spec,
               [_ramp("0.606"), _ramp("0.682", RAM_DESCRIPTION="005/SB  ON FR MAIN"),
                _ramp("1.5", RAM_ROUTE_NAME="007", RAM_DESIGN_DESC="label differs",
                      RAM_CITY_CODE="LA")])
    xl = _consolidate(con_ram, run, tmp / "ramp_xl.xlsx")
    tsn_dir = tmp / "tsn_ramp"
    tsn_dir.mkdir()
    _tsn_file(tsn_dir / "CA RAMPS.xlsx", spec,
              [_tsn_ramp("0.606"), _tsn_ramp("0.682", RAM_DESCRIPTION="005/SB ON FR MAIN"),
               _tsn_ramp("1.5", RAM_ROUTE_NAME="007"), _tsn_ramp("9.9")])
    raw = tsn_dir / "CA RAMPS.xlsx"
    q = dict(events=_Quiet(), confirm_overwrite=lambda p: True, mode="preview")
    got = _counts(crt.RAMP_VS_TSN.compare(str(xl), str(raw), str(tmp / "o1.xlsx"), **q))
    c.check("the reconciled ramps pair; the one real difference (a city code) counts; "
            "a run of spaces is one space; TSN's extra ramp is one-sided; the design "
            "description (context) never counts",
            got == {"paired_rows": 3, "side_a_only_rows": 0, "side_b_only_rows": 1,
                    "differing_cells": 1}, got)
    lib = tmp / "tsn_ramp_normalized.xlsx"
    res = tlc.build_into_ramp(tsn_dir, lib, events=_Quiet(), confirm_overwrite=lambda p: True)
    c.check("the TSN library normalizes the raw extract", res.status == "ok", res.message)
    got_lib = _counts(crt.RAMP_VS_TSN.compare(str(xl), str(lib), str(tmp / "o2.xlsx"), **q))
    c.check("...and the normalized copy reads exactly like the raw extract",
            got_lib == got, got_lib)
    pdf = tmp / "ramp_pdf.xlsx"
    _mark_pdf(xl, pdf)
    got_pdf = _counts(crt.RAMP_PDF_VS_TSN.compare(str(pdf), str(raw), str(tmp / "o3.xlsx"), **q))
    c.check("the print flavor reads the same rows to the same verdict",
            got_pdf == got, got_pdf)
    pve = _counts(crt.RAMP_PDF_VS_EXCEL.compare(str(pdf), str(xl), str(tmp / "o4.xlsx"), **q))
    c.check("PDF vs Excel of the same rows is a clean match",
            pve == {"paired_rows": 3, "side_a_only_rows": 0, "side_b_only_rows": 0,
                    "differing_cells": 0}, pve)
    # CMP-AUD-197 (owner ruling 2026-07-16): the Excel export serializes a CR as
    # the OOXML escape '_x000d_' (route 010's four Cactus City rest-area ramps on
    # the 10.2 delivery) and can pad an edge with tabs; the print structurally
    # carries neither, so the self-check decodes them away. vs TSN reads the cell
    # decoded the way installed Excel shows it, and the CR stays compared content.
    esc = tmp / "esc_run"
    esc.mkdir()
    plain = "010/EBOFF TO CACTUS CITY REST AREA"
    _site_file(esc / "2026-10-02 ssor-prod clean_ramp_route_005.xlsx", spec,
               [_ramp("0.606", RAM_DESCRIPTION=plain + "_x000d_"),
                _ramp("0.682", RAM_DESCRIPTION="\t005/SB ON FR MAIN\t\t")])
    esc_xl = _consolidate(con_ram, esc, tmp / "esc_xl.xlsx")
    plain_run = tmp / "plain_run"
    plain_run.mkdir()
    _site_file(plain_run / "2026-10-02 ssor-prod clean_ramp_route_005.xlsx", spec,
               [_ramp("0.606", RAM_DESCRIPTION=plain),
                _ramp("0.682", RAM_DESCRIPTION="005/SB ON FR MAIN")])
    esc_pdf = tmp / "esc_pdf.xlsx"
    _mark_pdf(_consolidate(con_ram, plain_run, tmp / "plain_xl.xlsx"), esc_pdf)
    pve = _counts(crt.RAMP_PDF_VS_EXCEL.compare(str(esc_pdf), str(esc_xl),
                                                str(tmp / "o5.xlsx"), **q))
    c.check("PDF vs Excel: the Excel file's '_x000d_' escape and edge tabs are "
            "render artifacts, never differences (CMP-AUD-197)",
            pve == {"paired_rows": 2, "side_a_only_rows": 0, "side_b_only_rows": 0,
                    "differing_cells": 0}, pve)
    c.check("vs TSN reads the escape decoded (the CR is compared content)",
            crt._value(crt._RAMP, "RAM_DESCRIPTION", plain + "_x000d_", "site", False)
            == plain + "\r", repr(crt._value(crt._RAMP, "RAM_DESCRIPTION",
                                             plain + "_x000d_", "site", False)))
    c.check("...and a literal '_x005F_x000d_' stays the literal text",
            crt._value(crt._RAMP, "RAM_DESCRIPTION", "TAG_x005F_x000d_", "site", False)
            == "TAG_x000d_")
    written = crt.RAMP_VS_TSN.compare(str(xl), str(raw), str(tmp / "ramp_vs_tsn.xlsx"),
                                      events=_Quiet(), confirm_overwrite=lambda p: True,
                                      mode="formulas")
    names = load_workbook(tmp / "ramp_vs_tsn.xlsx", read_only=True).sheetnames
    c.check("a real workbook is written, with its Notes sheet",
            written.status == "ok" and "Notes" in names and "Comparison" in names, names)
    for label, call in (
            ("the print flavor refuses an unmarked (Excel) workbook",
             lambda: crt.RAMP_PDF_VS_TSN.compare(str(xl), str(raw), str(tmp / "g1.xlsx"), **q)),
            ("the Excel flavor refuses a PDF conversion",
             lambda: crt.RAMP_VS_TSN.compare(str(pdf), str(raw), str(tmp / "g2.xlsx"), **q)),
            ("the self-check refuses swapped sides",
             lambda: crt.RAMP_PDF_VS_EXCEL.compare(str(xl), str(pdf), str(tmp / "g3.xlsx"), **q)),
            ("the TSN side refuses a consolidated site export",
             lambda: crt.RAMP_VS_TSN.compare(str(xl), str(xl), str(tmp / "g4.xlsx"), **q))):
        res = call()
        c.check(label, res.status == "error", res.status)
    return run


def test_ramp_env(tmp, run_b):
    print("Ramp between environments (keyed on the file's route token):")
    run_a = tmp / "2026-10-01 ssor-prod" / crc.RAMP.key
    run_a.mkdir(parents=True)
    src = next(run_b.glob("*.xlsx"))
    shutil.copy(src, run_a / src.name.replace("2026-10-02", "2026-10-01"))
    q = dict(events=_Quiet(), confirm_overwrite=lambda p: True, mode="preview")
    same = _counts(cee.CLEAN_RAMP.compare_folders(str(run_a.parent), str(run_b.parent),
                                                  str(tmp / "e1.xlsx"), **q))
    c.check("two identical exports match, the route-007 ramp in route 005's file included",
            same == {"paired_rows": 3, "side_a_only_rows": 0, "side_b_only_rows": 0,
                     "differing_cells": 0}, same)
    _site_file(next(run_a.glob("*.xlsx")), crc.RAMP,
               [_ramp("0.606", RAM_CITY_CODE="LA"), _ramp("0.682", RAM_DESCRIPTION="005/SB  ON FR MAIN"),
                _ramp("1.5", RAM_ROUTE_NAME="007", RAM_DESIGN_DESC="label differs",
                      RAM_CITY_CODE="LA")])
    diff = _counts(cee.CLEAN_RAMP.compare_folders(str(run_a.parent), str(run_b.parent),
                                                  str(tmp / "e2.xlsx"), **q))
    c.check("a changed cell counts", diff["differing_cells"] == 1 and diff["paired_rows"] == 3,
            diff)


def _thy(begin, end, **kw):
    base = {"THY_SEG_ORDER_ID": "150", "THY_DISTRICT_CODE": "11", "THY_COUNTY_CODE": "SD.",
            "THY_ROUTE_NAME": "005S", "THY_ROUTE_SUFFIX_CODE": "S",
            "THY_BEGIN_PM_AMT": begin, "THY_END_PM_AMT": end,
            "THY_LENGTH_MILES_AMT": f"{float(end) - float(begin):.3f}",
            "THY_LEFT_ROAD_EFF_DATE": "07/13/1973", "THY_TOLL_FOREST_CODE": "",
            "THY_HIGHWAY_GROUP_CODE": "D", "THY_EXTRACT_DATE": "10/02/2026"}
    base.update(kw)
    return base


def _tsn_thy(begin, end, **kw):
    base = {"THY_ID": 7, "THY_ELEMENT_ID": 1, "THY_SEG_ORDER_ID": 150,
            "THY_DISTRICT_CODE": "11", "THY_COUNTY_CODE": "SD", "THY_ROUTE_NAME": "005",
            "THY_ROUTE_SUFFIX_CODE": "S", "THY_BEGIN_PM_AMT": float(begin),
            "THY_END_PM_AMT": float(end), "THY_LENGTH_MILES_AMT": float(end) - float(begin),
            "THY_LEFT_ROAD_EFF_DATE": datetime(1973, 7, 13), "THY_TOLL_FOREST_CODE": 0,
            "THY_HIGHWAY_GROUP_CODE": "D", "THY_EXTRACT_DATE": datetime(2025, 9, 8)}
    base.update(kw)
    return base


def test_highway(tmp):
    print("Highway: route suffix in the name, the equation marker, toll/forest, county:")
    spec = crc.HIGHWAY
    run = tmp / "hwy" / spec.key
    run.mkdir(parents=True)
    _site_file(run / "clean_highway_route_005S.xlsx", spec,
               [_thy("0", "0.305"), _thy("0.305", "0.9", THY_PM_SUFFIX_CODE="E",
                                         THY_EQUATE_CODE="E")])
    xl = _consolidate(con_hwy, run, tmp / "hwy_xl.xlsx")
    raw = tmp / "CA HIGHWAYS.xlsx"
    _tsn_file(raw, spec, [_tsn_thy("0", "0.305"), _tsn_thy("0.305", "0.9", THY_EQUATE_CODE="E")])
    got = _counts(crt.HIGHWAY_VS_TSN.compare(str(xl), str(raw), str(tmp / "h1.xlsx"),
                                             events=_Quiet(), confirm_overwrite=lambda p: True,
                                             mode="preview"))
    c.check("both segments pair ('005S'+'S' = '005'+'S'; 'SD.' = 'SD'; the 'E' row keys "
            "with no roadbed); only the 'E' suffix cell itself differs (route-name 005S vs "
            "005 counts once per row too)",
            got["paired_rows"] == 2 and got["side_a_only_rows"] == 0
            and got["side_b_only_rows"] == 0, got)
    rows_a = crt.load_site(xl, crt.profile_for("clean_highway"), pdf=False)
    rows_b = crt.load_tsn(raw, crt.profile_for("clean_highway"))
    h = list(spec.header)
    tf = 1 + h.index("THY_TOLL_FOREST_CODE")
    dt = 1 + h.index("THY_LEFT_ROAD_EFF_DATE")
    c.check("a blank toll/forest code is TSN's 0, and dates compare as ISO dates",
            rows_a[0][tf] == rows_b[0][tf] == "0" and rows_a[0][dt] == rows_b[0][dt] == "1973-07-13",
            (rows_a[0][tf], rows_b[0][tf], rows_a[0][dt], rows_b[0][dt]))
    c.check("the route identity is shared: the outer route reads 005S on both sides",
            rows_a[0][0] == rows_b[0][0] == "005S", (rows_a[0][0], rows_b[0][0]))
    c.check("route_identity never doubles a suffix already in the name",
            crt.route_identity("005S", "S") == "005S" and crt.route_identity("5", "S") == "005S"
            and crt.route_identity("058U", "") == "058U" and crt.route_identity("001", None) == "001")


def test_intersection(tmp):
    print("Intersection: design-code prefix, signal fold, YY-MM-DD dates:")
    spec = crc.INTERSECTION
    run = tmp / "inx" / spec.key
    run.mkdir(parents=True)
    row = {"INX_CONNECTION_ID": "11050", "INX_MAIN_SEQ_ID": "1", "INX_CROSS_SEQ_ID": "2",
           "INX_DESIGN_CODE": "T", "INX_LIGHTED_BEGIN_DATE": "73-10-19", "INX_CONTROL_CODE": "S",
           "INX_ROUTE_NAME": "001", "INX_BEGIN_PM_AMT": "0.204", "INX_END_PM_AMT": "0.204",
           "INX_COUNTY_CODE": "ORA", "INX_INTERSECTION_NAME": "MAIN ST",
           "INX_EXTRACT_DATE": "10/02/2026"}
    _site_file(run / "clean_intersection_route_001.xlsx", spec, [row])
    xl = _consolidate(con_inx, run, tmp / "inx_xl.xlsx")
    raw = tmp / "CA INTERSECTIONS.xlsx"
    _tsn_file(raw, spec, [{"INX_CONNECTION_ID": 81366, "INX_MAIN_SEQ_ID": 1,
                           "INX_CROSS_SEQ_ID": 2, "INX_DESIGN_CODE": "IT",
                           "INX_LIGHTED_BEGIN_DATE": datetime(1973, 10, 19),
                           "INX_CONTROL_CODE": "P", "INX_ROUTE_NAME": "001",
                           "INX_BEGIN_PM_AMT": 0.204, "INX_END_PM_AMT": 0.204,
                           "INX_COUNTY_CODE": "ORA", "INX_INTERSECTION_NAME": "MAIN ST",
                           "INX_EXTRACT_DATE": datetime(2025, 9, 3)}])
    got = _counts(crt.INTERSECTION_VS_TSN.compare(str(xl), str(raw), str(tmp / "i1.xlsx"),
                                                  events=_Quiet(), confirm_overwrite=lambda p: True,
                                                  mode="preview"))
    c.check("'T' = 'IT', 'S' = TSN's signal sub-type 'P', '73-10-19' = 1973-10-19, and "
            "the connection id (a different id space) is context: a clean pair",
            got == {"paired_rows": 1, "side_a_only_rows": 0, "side_b_only_rows": 0,
                    "differing_cells": 0}, got)


def main():
    with temp_dir("tsmis_crcmp_") as tmp:
        tmp = Path(tmp)
        run_b = test_ramp(tmp)
        test_ramp_env(tmp, run_b)
        test_highway(tmp)
        test_intersection(tmp)
    c.check("the comparison profiles hold each report's unsourced columns as context",
            set(crc.HIGHWAY.unsourced) <= set(crt.profile_for("clean_highway").context)
            and set(crc.RAMP.unsourced) <= set(crt.profile_for("clean_ramp_pdf").context)
            and "THY_BEGIN_OFFSET_AMT" in crt.profile_for("clean_highway").context
            and set(chc.CONTEXT_COLUMNS) & set(chc.HEADER)
            <= set(crt.profile_for("clean_highway").context))
    return c.summary()


if __name__ == "__main__":
    sys.exit(main())

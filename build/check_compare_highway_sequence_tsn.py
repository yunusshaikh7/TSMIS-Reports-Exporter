"""Golden check for the TSMIS-vs-TSN Highway Sequence comparator
(scripts/compare_highway_sequence_tsn.py) — the FLAT recipe with a COUNTY+PM key.

Locks: the CompareSchema wiring (PM key; key_normalizer = county|PM; context_fields
= HG + City + Distance To Next Point; the Notes legend_writer); the normalizers
(county trailing-period strip, prefix/PM/suffix re-glue, description route-prefix
strip + whitespace collapse); the TSN PDF parser's pure helpers (x-window bucketing,
2-char flag split, route/location regex); and end-to-end that

  * the same county+PM keys together even when TSMIS writes "LA." and TSN "LA",
  * the SAME postmile in two DIFFERENT counties is NOT confused (county-relative),
  * prefix/suffix glue ("R" + "010.179" == "R010.179"; "050.025" + "E" == "050.025E"),
  * FT and Description (after the "<route>/" strip) are GENUINE diffs,
  * HG / City / Distance contribute ZERO diff cells (context), and
  * a postmile only one side lists is a one-sided row.

No PDFs / real files; CI-safe. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_highway_sequence_tsn.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_highway_sequence_tsn as hs
import consolidate_tsn_highway_sequence as ths
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []
DIFF = " ≠ "


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _write_tsmis(path, rows):
    """Synthetic CONSOLIDATED Highway Sequence: header[0]='Route'; loader reads by
    POSITION. rows = (route, county, city, prefix, pm, suffix, hg, ft, dist, desc)."""
    wb = Workbook()
    ws = wb.active
    ws.title = hs.TSMIS_SHEET
    ws.append(["Route", "County", "City", "", "PM", "", "HG", "FT",
               "Distance To Next Point", "Description"])
    for r in rows:
        ws.append(list(r))
    wb.save(path)
    wb.close()


def _write_tsn(path, rows):
    """Synthetic NORMALIZED TSN workbook: ths.NORMALIZED_HEADER, read positionally.
    rows = (route, county, pm, city, hg, ft, dist, desc)."""
    wb = Workbook()
    ws = wb.active
    ws.title = ths.NORMALIZED_SHEET
    ws.append(ths.NORMALIZED_HEADER)
    for r in rows:
        ws.append(list(r))
    wb.save(path)
    wb.close()


def _comparison(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Comparison"]
        it = ws.iter_rows(values_only=True)
        header = [("" if c is None else str(c)) for c in next(it)]
        rows = [["" if c is None else str(c) for c in r] for r in it
                if r and any(c not in (None, "") for c in r)]
        return header, rows, wb.sheetnames
    finally:
        wb.close()


def test_schema():
    print("schema + normalizers:")
    sc = hs._SCHEMA
    check("key is PM", sc.header[sc.key_field] == "PM")
    check("side names TSMIS / TSN", sc.side_a == "TSMIS" and sc.side_b == "TSN")
    check("key_normalizer set (county|PM)", sc.key_normalizer is not None)
    check("context = HG + City + Distance To Next Point",
          set(sc.context_fields) == {"HG", "City", "Distance To Next Point"})
    check("Notes legend_writer set (the indicator)", sc.legend_writer is not None)
    check("county 'LA.' -> 'LA' (period strip)", hs._norm_county("LA.") == "LA")
    check("county 'MEN' -> 'MEN' (no-op)", hs._norm_county("MEN") == "MEN")
    check("glue prefix+PM ('R' + '010.179' -> 'R010.179')",
          hs._glue_pm("R", "010.179", None) == "R010.179")
    check("glue PM+suffix ('050.025' + 'E' -> '050.025E')",
          hs._glue_pm(None, "050.025", "E") == "050.025E")
    check("desc strips '<route>/' prefix", hs._norm_desc("001/NB OFF TO X") == "NB OFF TO X")
    check("desc collapses double spaces", hs._norm_desc("SB ON  ARGYLE AV") == "SB ON ARGYLE AV")
    # key_normalizer over a consolidated-shape row [route, County, PM, City, ...]
    row = ["001", "LA", "000.500", "DAPT", "D", "H", "000.100", "JCT 5"]
    check("key_normalizer -> 'LA 000.500'", hs._key_county_pm(row, 1, hs.KEY_FIELD) == "LA 000.500")


def test_parser_helpers():
    print("TSN PDF parser helpers (no PDF):")
    check("location regex accepts 'R010.179' / '050.025E' / '000.000'",
          all(ths.LOCATION_RE.match(x) for x in ("R010.179", "050.025E", "000.000")))
    check("location regex rejects 'POSTMILE' / 'EQUATES'",
          not ths.LOCATION_RE.match("POSTMILE") and not ths.LOCATION_RE.match("EQUATES"))
    check("county regex accepts 'MEN' / 'LA.' , rejects 'OTM22025'",
          ths.COUNTY_RE.match("MEN") and ths.COUNTY_RE.match("LA.")
          and not ths.COUNTY_RE.match("OTM22025"))
    check("route norm '5' -> '005', '5S' -> '005S'",
          ths._norm_route("5") == "005" and ths._norm_route("5S") == "005S")
    # x-window bucketing: county / postmile / flag / distance / description bands
    check("bucket county x=15", ths._bucket(15) == "county")
    check("bucket postmile x=105", ths._bucket(105) == "pm")
    check("bucket flag x=185", ths._bucket(185) == "flag")
    check("bucket distance x=226", ths._bucket(226) == "dist")
    check("bucket description x=300", ths._bucket(300) == "desc")
    # flag split: 'DH' -> HG 'D', FT 'H'
    flag = "DH"
    check("flag split -> HG=D, FT=H", flag[0] == "D" and flag[1] == "H")


def test_end_to_end():
    print("end-to-end (county+PM key, county-relative, glue, context non-asserting):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_hs_tsn_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    # (route, county, city, prefix, pm, suffix, hg, ft, dist, desc)
    _write_tsmis(tsmis, [
        # LA.000.500: county period differs (LA. vs LA); HG/City/Distance differ
        #   (context); description carries the "001/" prefix; FT equal -> identical row.
        ("001", "LA.", "LACITY", None, "000.500", None, "D", "H", "000.100", "001/JCT 5"),
        # LA.001.000: a GENUINE FT diff (H vs I).
        ("001", "LA.", None, None, "001.000", None, "D", "H", "000.200", "PT A"),
        # MEN.000.000 vs ORA.000.000: same PM, different county — must NOT confuse.
        ("001", "MEN", None, None, "000.000", None, None, "H", "000.056", "BEGIN MEN"),
        ("001", "ORA", None, "R", "000.129", None, "D", "H", "000.000", "BEGIN ORA"),
        # equate suffix glue: TSMIS prefix+PM+suffix -> '050.025E'
        ("001", "MEN", None, None, "050.025", "E", None, "H", "000.076", "PT E"),
        # a TSMIS-only postmile (TSN doesn't list it) -> one-sided.
        ("001", "LA", None, None, "002.000", None, "D", "H", None, "TSMIS ONLY PT"),
    ])
    # (route, county, pm, city, hg, ft, dist, desc)
    _write_tsn(tsn, [
        ("001", "LA", "000.500", None, "U", "H", "000.050", "JCT 5"),   # FT eq, ctx differ
        ("001", "LA", "001.000", None, "U", "I", "000.090", "PT A"),    # FT diff H vs I
        ("001", "MEN", "000.000", None, "U", "H", "000.056", "BEGIN MEN"),
        ("001", "ORA", "R000.129", None, "D", "H", "000.000", "BEGIN ORA"),
        ("001", "MEN", "050.025E", None, "U", "H", "000.076", "PT E"),
        ("001", "LA", "003.000", None, "U", "H", "000.010", "TSN ONLY PT"),  # one-sided
    ])
    res = hs.compare(tsmis, tsn, out, events=Events(),
                     confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, sheets = _comparison(out)
    check("Notes sheet present (the indicator)", "Notes" in sheets)

    # The key column ("PM") shows the composite identity "COUNTY POSTMILE".
    pmcol = header.index("PM")
    cocol = header.index("County")
    by = {r[pmcol]: r for r in rows}

    ft = header.index("FT")
    desc = header.index("Description")
    check("LA 000.500 (period-normalized) keyed together — present once",
          "LA 000.500" in by)
    check("LA 000.500 FT equal (H=H) — no diff", DIFF not in by["LA 000.500"][ft])
    check("LA 000.500 Description '001/JCT 5' vs 'JCT 5' normalized equal — no diff",
          DIFF not in by["LA 000.500"][desc])
    check("LA 000.500 County column shows normalized 'LA'", by["LA 000.500"][cocol] == "LA")
    check("LA 001.000 FT H vs I is a GENUINE diff", DIFF in by["LA 001.000"][ft])
    check("MEN 000.000 and ORA R000.129 both present (county-relative, not merged)",
          "MEN 000.000" in by and "ORA R000.129" in by)
    check("MEN 000.000 not confused with ORA — its desc is BEGIN MEN",
          "BEGIN MEN" in by["MEN 000.000"][desc])
    check("equate suffix glue: MEN 050.025E keyed together (no diff on FT)",
          "MEN 050.025E" in by and DIFF not in by["MEN 050.025E"][ft])

    # context columns NEVER carry a diff marker (HG/City/Distance differ in data)
    ctx_cols = [header.index(c) for c in ("HG", "City", "Distance To Next Point")]
    ctx_diffs = sum(1 for r in rows for i in ctx_cols if DIFF in r[i])
    check("zero diff cells in any context column (HG/City/Distance)", ctx_diffs == 0)

    # one-sided rows: TSMIS 002.000 (only TSMIS) and TSN 003.000 (only TSN)
    check("Only in TSMIS + Only in TSN sheets present",
          "Only in TSMIS" in sheets and "Only in TSN" in sheets)

    total = sum(1 for r in rows for c in r if DIFF in c)
    print(f"      (rows={len(rows)}, total diff cells={total}, context diff cells={ctx_diffs})")


def main():
    test_schema()
    test_parser_helpers()
    test_end_to_end()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-HIGHWAY-SEQUENCE-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

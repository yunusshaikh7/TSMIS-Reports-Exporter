"""Golden check for the visual-evidence generator (scripts/visual_evidence.py +
scripts/evidence_highway_detail.py) — the render-free logic layer.

Locks: the row registry + the TSMIS-PDF/TSN-PDF source resolution and the
examples clamp; the caller-side gate (matrix_build.evidence_opts_for); the
sibling artifact naming (the "(formulas).xlsx" family); the adapter's LOCKSTEP
pins against the Highway Detail PDF consolidator (window counts, the postmile /
date-token regex behavior its mirrored walk relies on); the field→TSN-print
group map (complete, RB half mirrored) and the two-line TASAS regexes on
realistic print lines (prefix/roadbed/equation/optional-city/empty-description);
the span→x-box math including the empty-optional-group case; the verification
projections (PS derived, NA fold via the comparator's own projection); the
unique-key diff enumeration with the district/county sidecar; and the TSN
loader's sidecar contract (tsn_rows_with_dcr row-identical to the locked
tsn_rows_from_raw; the normalized sheet appending exactly the sidecar columns;
load_sides reading it back and refusing a sidecar-less legacy library with the
rebuild hint). Rendering itself is exercised by the frozen self-test's
render-stack step (scripts/self_test.py) — no rasterizing here; CI-safe.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_visual_evidence.py
"""
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_highway_detail_tsn as cht
import compare_highway_log as chl_cmp
import consolidate_tsmis_highway_detail_pdf as chd
import consolidate_tsn_highway_log as ctnl
import evidence_highway_detail as ehd
import evidence_highway_log as ehl
import highway_detail_columns as hdc
import highway_log_columns as hlc
import matrix_build
import tsn_load_highway_detail as tlh
import visual_evidence as ve
from openpyxl import Workbook, load_workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
print("registry + sources + clamp")
check("rows: the Highway Detail + Highway Log + Intersection Detail pairs, nothing else",
      ve.rows() == ["highway_detail", "highway_detail_pdf",
                    "highway_log", "highway_log_pdf",
                    "intersection_detail", "intersection_detail_pdf"])
check("capable() matches rows()",
      all(ve.capable(r) for r in ve.rows()) and not ve.capable("ramp_detail"))
check("TSMIS visuals come from each report's (PDF)-edition export subdir",
      ve.pdf_subdir_for("highway_detail") == "highway_detail_pdf"
      and ve.pdf_subdir_for("highway_detail_pdf") == "highway_detail_pdf"
      and ve.pdf_subdir_for("intersection_detail") == "intersection_detail_pdf"
      and ve.pdf_subdir_for("intersection_detail_pdf") == "intersection_detail_pdf"
      and ve.pdf_subdir_for("highway_log") == "highway_log_pdf"
      and ve.pdf_subdir_for("highway_log_pdf") == "highway_log_pdf")
check("TSN prints live in each report's library pdf folder — except the Highway "
      "Log, whose district prints ARE the library's raw inputs (no duplicate drop)",
      str(ve.tsn_pdf_dir("highway_detail")).replace("\\", "/")
      .endswith("tsn_library/highway_detail/pdf")
      and str(ve.tsn_pdf_dir("intersection_detail")).replace("\\", "/")
      .endswith("tsn_library/intersection_detail/pdf")
      and str(ve.tsn_pdf_dir("highway_log")).replace("\\", "/")
      .endswith("tsn_library/highway_log/raw")
      and str(ve.tsn_pdf_dir("highway_log_pdf")).replace("\\", "/")
      .endswith("tsn_library/highway_log/raw"))
check("clamp: default/garbage/low/high",
      (ve.clamp_examples(None), ve.clamp_examples("x"), ve.clamp_examples(0),
       ve.clamp_examples(99), ve.clamp_examples("7"))
      == (2, 2, 1, 10, 7))
wbp, imgp = ve.sibling_paths(Path(r"C:\x\comparisons\hd vs tsn.xlsx"))
check("sibling naming: '(evidence).xlsx' + '(evidence images)' folder",
      wbp.name == "hd vs tsn (evidence).xlsx"
      and imgp.name == "hd vs tsn (evidence images)")
avail = ve.availability()
check("availability shape (rows/tsn_pdfs/ready/dir/reports/row_reports/deps_ok)",
      set(avail) >= {"rows", "tsn_pdfs", "ready", "dir", "reports", "row_reports",
                     "deps_ok"})
check("availability reports every evidence report, per-dir + source kind",
      [r["key"] for r in avail["reports"]]
      == ["highway_detail", "highway_log", "intersection_detail"]
      and all(set(r) >= {"key", "label", "tsn_pdfs", "dir", "source"}
              for r in avail["reports"])
      and {r["key"]: r["source"] for r in avail["reports"]}
      == {"highway_detail": "pdf", "highway_log": "raw",
          "intersection_detail": "pdf"})
check("row_reports maps every capable row to its report (the per-cell action's gate)",
      avail["row_reports"] == ve.TSN_PDF_REPORT
      and set(avail["row_reports"]) == set(ve.rows()))

print("caller-side gate (matrix_build.evidence_opts_for)")
check("toggle off -> None",
      matrix_build.evidence_opts_for(None, "highway_detail", lambda s: s) is None
      and matrix_build.evidence_opts_for({"enabled": False, "examples": 5},
                                         "highway_detail", lambda s: s) is None)
check("unsupported row -> None",
      matrix_build.evidence_opts_for({"enabled": True}, "ramp_detail",
                                     lambda s: s) is None)
opts = matrix_build.evidence_opts_for({"enabled": True, "examples": 99},
                                      "highway_detail",
                                      lambda s: Path("cell") / s)
check("supported row -> resolved PDF dir + clamped examples",
      opts == {"tsmis_pdf_dir": Path("cell") / "highway_detail_pdf",
               "examples": 10})

# --------------------------------------------------------------------------- #
print("adapter LOCKSTEP pins vs the PDF consolidator")
check("window shapes: 10-cell line 1 + 25-cell line 2 == the 34 columns",
      chd.N_COLS_L1 == 10 and chd.N_COLS_L2 == 25 and len(hdc.HEADER) == 34
      and 9 + chd.N_COLS_L2 == len(hdc.HEADER))
check("postmile token regex accepts the glued forms the walk classifies on",
      all(chd.PM_TOKEN_RE.match(t)
          for t in ("S000.000", "000.000E", "R012.243R", "C043.925R"))
      and not chd.PM_TOKEN_RE.match("11 IMP 007"))
check("date-token guard: TASAS date yes, page-header date no",
      bool(chd.DATE_TOKEN_RE.search("64-01-01"))
      and not chd.DATE_TOKEN_RE.search("2026-07-07"))
check("FIELDS = every shared column except the key (PS included)",
      ehd.FIELDS == [f for f in cht.SHARED_HEADER if f != "Post Mile"]
      and "PS" in ehd.FIELDS and len(ehd.FIELDS) == 34)
check("TSN group map covers exactly FIELDS",
      set(ehd.TSN_GROUP) == set(ehd.FIELDS))
check("RB half of the TSN map is MIRRORED (inner before width before outer)",
      (ehd.TSN_GROUP["RB IN-TO"], ehd.TSN_GROUP["RB Wid"],
       ehd.TSN_GROUP["RB OT-TO"]) == ("rbto1", "rbwid", "rbto2"))

print("TSN print regexes on realistic two-line records")
l1 = "R 004.972E  000.123  11-08-01  D  F  Y15-05-18  LGNB  R  22-01-01  054062  S"
m1 = ehd.L1_RE.match(l1)
check("line 1: prefix + equation marker + sig-flagged eff + city all parse",
      bool(m1) and (m1.group("pp").strip(), m1.group("mile"), m1.group("ps"),
                    m1.group("city"), m1.group("ru"), m1.group("beg"))
      == ("R", "004.972", "E", "LGNB", "R", "22-01-01"))
l1b = "000.000  000.055  64-01-01  U  C  64-01-01  B  21-01-01  242400"
m1b = ehd.L1_RE.match(l1b)
check("line 1: bare PM, no city, no marker",
      bool(m1b) and m1b.group("pp") is None and m1b.group("ps") is None
      and m1b.group("city") is None and m1b.group("ru") == "B")
l2 = ("SANDHILLS DITCH  A  Y90-03-15  C  5  N  8  8  64  8  8  "
      "*90-03-15  H  7  F  12V  Y85-12-27  C  4  N  2  2  44  8  8")
m2 = ehd.L2_RE.match(l2)
check("line 2: desc + NA + the three sig-flagged blocks parse",
      bool(m2) and (m2.group("desc"), m2.group("na"), m2.group("lbeff"),
                    m2.group("medwda"), m2.group("rbto2"))
      == ("SANDHILLS DITCH", "A", "90-03-15", "12V", "8"))
l2e = ("A  Y90-03-15  C  5  N  8  8  64  8  8  "
       "*90-03-15  H  7  F  12V  Y85-12-27  C  4  N  2  2  44  8  8")
m2e = ehd.L2_RE.match(l2e)
check("line 2: EMPTY description still parses (the \\s* fix)",
      bool(m2e) and m2e.group("desc") == "" and m2e.group("na") == "A")
# the REAL fully-dittoed right-roadbed block from the D04 print (route 237 @
# R008.816L): width-matched '+' runs — an 8-char run for the dittoed eff DATE,
# '+++' for the 3-digit width.
l2d = ("EB 37-84K A 02-12-09 H 3 N 10 10 36 10 10 "
       "02-12-09 H 7 E 30V ++++++++ + ++ + ++ ++ +++ ++ ++")
m2d = ehd.L2_RE.match(l2d)
check("line 2: TSN width-matched DITTO runs parse (dates included)",
      bool(m2d) and (m2d.group("rbeff"), m2d.group("rbt"), m2d.group("rbln"),
                     m2d.group("rbwid"), m2d.group("rbtr2"))
      == ("++++++++", "+", "++", "+++", "++")
      and ehd.project("RB #Ln", m2d.group("rbln")) == "++"
      and ehd.project("RB Eff", m2d.group("rbeff")) == "++++++++")

print("span→box math (word-indexed line)")
ln = {"text": "AA BBB C", "offs": [(0, 2, {"x0": 10.0, "x1": 20.0}),
                                   (3, 6, {"x0": 30.0, "x1": 45.0}),
                                   (7, 8, {"x0": 55.0, "x1": 60.0})]}
check("value span boxes its words", ehd._span_box(ln, 3, 6) == (30.0, 45.0))
check("empty span boxes the neighbor gap",
      ehd._span_box(ln, 3, 3) == (21.0, 29.0))

print("verification projections")
check("PS is marker-derived", ehd.project("PS", "E") == "E"
      and ehd.project("PS", "") == "" and ehd.project("PS", None) == "")
check("other fields ride the comparator's own projection (NA fold, WDA glue)",
      ehd.project("NA", "A") == "" and ehd.project("NA", "N") == "N"
      and ehd.project("Med V/WDA", "8V") == "08V")

# --------------------------------------------------------------------------- #
print("diff enumeration (unique keys + sidecar)")
def _row(route, key, **over):
    r = [route] + [""] * len(cht.SHARED_HEADER)
    r[1 + cht.SHARED_HEADER.index("Post Mile")] = key
    for f, v in over.items():
        r[1 + cht.SHARED_HEADER.index(f)] = v
    return r

a_rows = [_row("001", "001.000", **{"LB Wid": "24"}),
          _row("001", "002.000", **{"LB Wid": "24"}),   # dup key: excluded
          _row("001", "002.000", **{"LB Wid": "25"}),
          _row("001", "003.000", **{"AC": "F"})]
b_rows = [_row("001", "001.000", **{"LB Wid": "26"}),
          _row("001", "002.000", **{"LB Wid": "24"}),
          _row("001", "003.000", **{"AC": "F"})]
sc = {("001", "001.000"): [("06", "TUL")], ("001", "003.000"): [("06", "TUL")]}
diffs = ehd.enumerate_diffs(a_rows, b_rows, sc)
check("only the unique-key LB Wid diff is enumerated, with its district",
      list(diffs) == ["LB Wid"] and len(diffs["LB Wid"]) == 1
      and diffs["LB Wid"][0]["key"] == "001.000"
      and (diffs["LB Wid"][0]["dist"], diffs["LB Wid"][0]["cnty"]) == ("06", "TUL")
      and (diffs["LB Wid"][0]["va"], diffs["LB Wid"][0]["vb"]) == ("24", "26"))

# --------------------------------------------------------------------------- #
print("TSN loader sidecar contract")
tmp = Path(tempfile.mkdtemp())
try:
    raw = tmp / "raw.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = cht.TSN_SHEET
    cols = ["DIST", "CNTY", "RTE", "RTE_SFX", "PP", "POSTMILE", "E_IND", "HG",
            "LENGTH", "REC_DATE", "AC", "ACC_EFF_DATE", "CITY", "POP_CODE",
            "BEG_DATE", "DESCRIPTION", "NON_ADD", "M_WID", "M_VA",
            "L_EFF_DATE", "L_ST", "L_NO_LANES", "L_SF", "L_OT_TOT", "L_OT_TR",
            "L_TR_WID", "L_IN_TOT", "L_IN_TR", "M_EFF_DATE", "M_TYPE_CODE",
            "M_CL", "M_BA", "R_EFF_DATE", "R_ST", "R_NO_LANES", "R_SF",
            "R_IN_TOT", "R_IN_TR", "R_TR_WID", "R_OT_TOT", "R_OT_TR"]
    ws.append(cols)
    base = {c: "" for c in cols}
    base.update(DIST="06", CNTY="TUL.", RTE="99", PP="R", POSTMILE="004.972",
                E_IND="E", HG="R", LENGTH="0.123", NON_ADD="A", M_WID="8",
                M_VA="V", DESCRIPTION="X  Y")
    ws.append([base[c] for c in cols])
    wb.save(raw)
    wb.close()

    rows_locked = cht.tsn_rows_from_raw(raw)
    rows_dcr, dcr = tlh.tsn_rows_with_dcr(raw)
    check("tsn_rows_with_dcr rows are IDENTICAL to the locked loader's",
          rows_dcr == rows_locked and len(rows_dcr) == 1)
    check("…and the sidecar carries (district, county-dot-stripped)",
          dcr == [("06", "TUL")])

    # the normalized library sheet: shared header + EXACTLY the sidecar columns
    out = tmp / "norm.xlsx"
    res = tlh.build_into(tmp, out, events=None, confirm_overwrite=lambda p: True)
    nwb = load_workbook(out)
    nws = nwb[cht.NORMALIZED_SHEET]
    hdr = [c.value for c in nws[1]]
    first = [c.value for c in nws[2]]
    nwb.close()
    check("normalized header = Route + shared + sidecar",
          res.status == "ok"
          and hdr == ["Route"] + cht.SHARED_HEADER + tlh.SIDECAR_HEADER)
    check("normalized row carries the sidecar values at the tail",
          first[-2:] == ["06", "TUL"] and first[0] == "099")

    # load_sides reads the sidecar back; the comparator side stays shared-width
    a_cons = tmp / "cons.xlsx"
    cw = Workbook()
    cs = cw.active
    cs.title = cht.TSMIS_SHEET
    cs.append(["Route"] + [f"c{i}" for i in range(1, 35)])
    cs.append(["099", "R004.972R", "000.123"] + [""] * 32)
    cw.save(a_cons)
    cw.close()
    ar, br, sc2, note = ehd.load_sides(a_cons, out)
    check("load_sides: rows in comparator shape, sidecar keyed by (route,key)",
          note is None and len(ar) == 1 and len(br) == 1
          and len(br[0]) == 1 + len(cht.SHARED_HEADER)
          and sc2.get(("099", br[0][1])) == [("06", "TUL")])
    check("both sides land on the same canonical key (roadbed-aware)",
          ar[0][1] == br[0][1] == "R004.972R")

    # a LEGACY normalized library (no sidecar) is refused with the rebuild hint
    old = tmp / "old.xlsx"
    ow = Workbook()
    os_ = ow.active
    os_.title = cht.NORMALIZED_SHEET
    os_.append(["Route"] + cht.SHARED_HEADER)
    os_.append(br[0])
    ow.save(old)
    ow.close()
    _a, _b, sc3, note3 = ehd.load_sides(a_cons, old)
    check("legacy library -> sidecar None + 'rebuild the TSN library' hint",
          sc3 is None and note3 and "rebuild the TSN library" in note3)
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Intersection Detail adapter (v0.22.0): maps + windows + LOCKSTEP")
import compare_intersection_detail_tsn as idt                # noqa: E402
import consolidate_tsmis_intersection_detail_pdf as idpdf    # noqa: E402
import evidence_intersection_detail as eid                   # noqa: E402
import tsn_load_intersection_detail as tli                   # noqa: E402

check("ID FIELDS = every shared column except the key (32, Route Suffix included)",
      eid.FIELDS == [f for f in idt.SHARED_HEADER if f != idt.KEY]
      and "Route Suffix" in eid.FIELDS and len(eid.FIELDS) == 32)
check("ID TSMIS cell map covers exactly FIELDS",
      set(eid._TSMIS_CELL) == set(eid.FIELDS))
check("ID TSN cell map covers exactly FIELDS",
      set(eid.TSN_CELL) == set(eid.FIELDS))
_l1n = {n for n, _lo, _hi in eid._L1_WIN}
_l2n = {n for n, _lo, _hi in eid._L2_WIN}
check("every TSN cell target has a fixed window on its line",
      all((n in _l1n if ln == 1 else n in _l2n)
          for ln, n in eid.TSN_CELL.values()))
check("ID TSMIS value positions mirror the comparator's (consolidated - Route)",
      eid._TSMIS_SRC == {f: p - 1 for f, p in idt._TSMIS_POS.items()})
check("Xing Line Lgth: TSMIS boxes rowB window 17, TSN boxes LINE 1's X-OVR "
      "(each side its own print position)",
      eid._TSMIS_CELL["Xing Line Lgth"] == (2, 17)
      and eid.TSN_CELL["Xing Line Lgth"] == (1, "X_CROSS_OVERRIDE"))
check("the Intrte swap mirrored: TSMIS boxes Route at rowB window 12",
      eid._TSMIS_CELL["Intrte Route"] == (2, 12)
      and eid._TSMIS_CELL["Intrte PM Suffix"] == (2, 16))
check("Route Suffix boxes the Location cell on both sides",
      eid._TSMIS_CELL["Route Suffix"] == (1, 3)
      and eid.TSN_CELL["Route Suffix"] == (1, "LOC"))
check("LOCKSTEP handles the consolidator's own pieces (rowA/rowB discriminators)",
      idpdf._is_rowA(["", "000.204", "", "12 ORA 001"] + [""] * 17)
      and bool(idpdf.INT_ROWB_RE.match("11050"))
      and bool(idpdf.OLD_PM_RE.match("0.204")))

print("ID TSN print: fixed windows, max-overlap, flag strip, LOC tokens")
check("LOC tokenizer: 3-char / dotted / 2-char counties + a route suffix",
      bool(eid._LOC_RE.match("12 ORA 001")) and bool(eid._LOC_RE.match("04 CC. 004"))
      and bool(eid._LOC_RE.match("07 LA 001")) and bool(eid._LOC_RE.match("07 LA 210U"))
      and not eid._LOC_RE.match("NB ON FROM SB RTE 5"))
_w1 = [{"t": "R", "x0": 14.0, "x1": 19.0}, {"t": "000.204", "x0": 25.0, "x1": 59.0},
       {"t": "12", "x0": 72.0, "x1": 82.0}, {"t": "ORA", "x0": 86.0, "x1": 101.0},
       {"t": "210U", "x0": 106.0, "x1": 125.0},
       {"t": "Y91-08-24", "x0": 406.0, "x1": 454.0}]
_a1 = eid._assign_win(_w1, eid._L1_WIN)
check("LOCATION is ONE window (a 2-char county can't shift the route out of it)",
      _a1["LOC"][0] == "12 ORA 210U")
check("max-overlap: a signature-flagged date leaning left stays in its DATE window",
      _a1["EFF_DATE_LT"][0] == "Y91-08-24" and _a1["TY_CT"][0] == "")
_l1 = {"page": 3, "words": _w1, "top": 100.0, "bottom": 110.0}
_w2 = [{"t": "JCT", "x0": 72.0, "x1": 86.0}, {"t": "5", "x0": 90.0, "x1": 95.0}]
_l2 = {"page": 3, "words": _w2, "top": 111.0, "bottom": 121.0}
_rec = {"l1": _l1, "a1": _a1, "l2": _l2, "a2": eid._assign_win(_w2, eid._L2_WIN),
        "dist": "12"}
check("the glued flag is stripped from the VALUE ('Y91-08-24' -> 1991-08-24)…",
      eid._tsn_raw(_rec, "Lighting Eff-Date") == "91-08-24"
      and eid.tsn_value(_rec, "Lighting Eff-Date") == "1991-08-24")
_pg, _box, _yspan, _xspan = eid.tsn_box(_rec, "Lighting Eff-Date")
check("…while the BOX keeps the printed token (flag included)",
      _pg == 3 and _box[0] <= 406.0 and _box[2] >= 454.0)
_pg2, _box2, _y2, _x2 = eid.tsn_box(_rec, "Int St Eff-Date")
check("a BLANK cell boxes its fixed template window (the window IS the cell)",
      _pg2 == 3 and 405 <= _box2[0] <= 415 and 440 <= _box2[2] <= 460
      and _box2[1] < _box2[3])
check("Route Suffix reads the LOC route token ('210U' -> 'U')",
      eid.tsn_value(_rec, "Route Suffix") == "U")

print("ID diff enumeration: unique keys, sidecar, the comparison's own trim")
def _idrow(route, pm, **over):
    r = [route] + [""] * len(idt.SHARED_HEADER)
    r[1 + idt.KEY_FIELD] = pm
    for f, v in over.items():
        r[1 + idt.SHARED_HEADER.index(f)] = v
    return r

_ar = [_idrow("001", "0.204", HG="D", Description="A  B"),
       _idrow("001", "1.000", HG="D"),      # dup key: excluded
       _idrow("001", "1.000", HG="U")]
_br = [_idrow("001", "0.204", HG="U", Description="A B"),
       _idrow("001", "1.000", HG="D")]
_sc = {("001", "0.204"): [("12", "ORA")]}
_diffs = eid.enumerate_diffs(_ar, _br, _sc)
check("only the unique-key HG diff is enumerated, with its district/county",
      list(_diffs) == ["HG"] and len(_diffs["HG"]) == 1
      and (_diffs["HG"][0]["dist"], _diffs["HG"][0]["cnty"]) == ("12", "ORA")
      and (_diffs["HG"][0]["va"], _diffs["HG"][0]["vb"]) == ("D", "U"))
check("a whitespace-run-only difference is NOT enumerated (compare_core's trim)",
      "Description" not in _diffs)

print("ID TSN loader sidecar contract")
tmp2 = Path(tempfile.mkdtemp())
try:
    raw2 = tmp2 / "raw.xlsx"
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = idt.TSN_SHEET
    cols2 = ["PP", "POST_MILE", "LOCATION", "DATE_REC", "HG", "CITY_CODE", "RU",
             "TY_INT", "TY_CT", "LT_TY", "MAIN_SM", "MAIN_LC", "MAIN_RC", "MAIN_TF",
             "MAIN_NL", "DESCRIPTION", "CS_SM", "CS_LC", "CS_RC", "CS_TF", "CS_NL",
             "EFF_DATE_INT", "EFF_DATE_CT", "EFF_DATE_LT", "EFF_DATE_ML",
             "MAIN_EFF_DATE", "MAIN_OVERRIDE", "CROSS_BEGIN_DATE", "EFF_DATE",
             "CROSS_ROUTE_NAME", "CROSS_PM_PREFIX", "CROSS_POSTMILE",
             "CROSS_PM_SUFFIX", "X_CROSS_OVERRIDE"]
    ws2.append(cols2)
    _b2 = {c: "" for c in cols2}
    _b2.update(PP="R", POST_MILE=" 000.204", LOCATION="04 CC. 004",
               DATE_REC="73-10-19", HG="D", RU="U", X_CROSS_OVERRIDE="0250")
    ws2.append([_b2[c] for c in cols2])
    wb2.save(raw2)
    wb2.close()

    rows_locked2 = idt.tsn_rows_from_raw(raw2)
    rows_dcr2, dcr2 = tli.tsn_rows_with_dcr(raw2)
    check("tsn_rows_with_dcr rows are IDENTICAL to the locked loader's",
          rows_dcr2 == rows_locked2 and len(rows_dcr2) == 1)
    check("…and the sidecar carries (district, county-dot-stripped)",
          dcr2 == [("04", "CC")])

    out2 = tmp2 / "norm.xlsx"
    res2 = tli.build_into(tmp2, out2, events=None, confirm_overwrite=lambda p: True)
    nwb2 = load_workbook(out2)
    nws2 = nwb2[idt.NORMALIZED_SHEET]
    hdr2 = [c.value for c in nws2[1]]
    first2 = [c.value for c in nws2[2]]
    nwb2.close()
    check("normalized header = Route + shared + sidecar (v3 shape, XLL included)",
          res2.status == "ok"
          and hdr2 == ["Route"] + idt.SHARED_HEADER + tli.SIDECAR_HEADER
          and "Xing Line Lgth" in hdr2 and "ML 2nd Eff-Date" not in hdr2)
    check("normalized row carries the sidecar values at the tail",
          first2[-2:] == ["04", "CC"] and first2[0] == "004")

    a_cons2 = tmp2 / "cons.xlsx"
    cw2 = Workbook()
    cs2 = cw2.active
    cs2.title = idt.TSMIS_SHEET
    cs2.append(["Route"] + [f"c{i}" for i in range(1, 35)] + ["Xing Line Lgth"])
    _r2 = [None] * 36
    _r2[0], _r2[1], _r2[2], _r2[4] = "004", "R", "000.204", "04 CC. 004"
    cs2.append(_r2)
    cw2.save(a_cons2)
    cw2.close()
    ar2, br2, sc22, note2 = eid.load_sides(a_cons2, out2)
    check("load_sides: rows in comparator shape, sidecar keyed by (route,key)",
          note2 is None and len(ar2) == 1 and len(br2) == 1
          and len(br2[0]) == 1 + len(idt.SHARED_HEADER)
          and sc22.get(("004", br2[0][1 + idt.KEY_FIELD])) == [("04", "CC")])
    check("both sides land on the same normalized PM key",
          ar2[0][1 + idt.KEY_FIELD] == br2[0][1 + idt.KEY_FIELD] == "0.204")

    old2 = tmp2 / "old.xlsx"
    ow2 = Workbook()
    os2 = ow2.active
    os2.title = idt.NORMALIZED_SHEET
    os2.append(["Route"] + idt.SHARED_HEADER)
    os2.append(br2[0])
    ow2.save(old2)
    ow2.close()
    _a2, _bx2, sc32, note32 = eid.load_sides(a_cons2, old2)
    check("legacy library -> sidecar None + 'rebuild the TSN library' hint",
          sc32 is None and note32 and "rebuild the TSN library" in note32)
finally:
    import shutil
    shutil.rmtree(tmp2, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("on-demand per-cell evidence (v0.23.0): the freshness gate")
import time                                                # noqa: E402
import matrix                                              # noqa: E402

tmp3 = Path(tempfile.mkdtemp())
try:
    store = tmp3 / "cell" / "highway_detail_pdf"
    store.mkdir(parents=True)
    consolidated = matrix.consolidated_store_path(store, "highway_detail_pdf")
    tsn = tmp3 / "tsn.xlsx"
    cmpwb = tmp3 / "cmp.xlsx"
    pdfdir = tmp3 / "pdfs"

    def _touch(p, when):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        os.utime(p, (when, when))

    def _gate_error(**over):
        try:
            matrix.run_evidence_only("highway_detail_pdf", store,
                                     "highway_detail_pdf", tsn, cmpwb, pdfdir,
                                     events=None, examples=2)
        except ValueError as e:
            return str(e)
        return None

    try:
        matrix.run_evidence_only("ramp_detail", store, "ramp_detail", tsn, cmpwb,
                                 pdfdir, events=None)
        _cap_err = None
    except ValueError as e:
        _cap_err = str(e)
    check("an evidence-incapable row is refused with the reason",
          _cap_err and "doesn't support evidence images" in _cap_err)

    err = _gate_error()
    check("missing comparison -> 'run the comparison first'",
          err and "run the comparison first" in err)

    now = time.time()
    _touch(cmpwb, now - 50)
    err = _gate_error()
    check("missing consolidated -> 'run the comparison first'",
          err and "no consolidated" in err and "run the comparison first" in err)

    # a store file NEWER than the consolidated -> the store-changed refusal
    _touch(consolidated, now - 100)
    _touch(store / "highway_detail_route_001.pdf", now - 20)
    err = _gate_error()
    check("store changed since the consolidation -> refuse with the refresh hint",
          err and "exports changed" in err and "refresh the comparison" in err)

    # consolidated fresh vs store, but NEWER than the comparison -> refuse.
    # (No fingerprint sidecar exists for this synthetic store; stub the staleness
    # probe so the mtime gates are what's under test.)
    _real_stale = matrix._consolidated_stale
    matrix._consolidated_stale = lambda *_a, **_k: False
    try:
        _touch(consolidated, now - 10)
        err = _gate_error()
        check("consolidated newer than the comparison -> refuse with the hint",
              err and "newer than" in err and "refresh the comparison" in err)

        _touch(consolidated, now - 100)
        _touch(tsn, now - 5)
        err = _gate_error()
        check("TSN workbook newer than the comparison -> refuse with the hint",
              err and "TSN workbook is newer" in err)

        # everything consistent -> the gate passes through to the generator; a
        # stubbed generate proves the call shape + the ok result + note.
        _touch(tsn, now - 200)
        import visual_evidence as _ve2
        _real_gen = _ve2.generate
        _ve2.generate = (lambda *_a, **_k:
                         {"note": "evidence: 2 example(s) across 1/1 …"})
        try:
            res = matrix.run_evidence_only(
                "highway_detail_pdf", store, "highway_detail_pdf", tsn, cmpwb,
                pdfdir, events=None, examples=2)
        finally:
            _ve2.generate = _real_gen
        check("fresh inputs -> ok result carrying the generator's note",
              res.status == "ok" and "example(s)" in (res.message or "")
              and res.summary_lines == [res.message])
    finally:
        matrix._consolidated_stale = _real_stale
finally:
    import shutil
    shutil.rmtree(tmp3, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("Highway Log adapter (v0.24.0): fields, window map, routing, ditto discipline")
check("FIELDS = every Highway Log column except the Location key",
      ehl.FIELDS == [f for f in hlc.HEADER if f != hlc.HEADER[0]]
      and len(ehl.FIELDS) == 30)
check("field -> TSN window map is positional over ROW_KEYS and complete "
      "(Description alone has no window — its own follow-on lines)",
      ehl._TSN_WIN_KEY == dict(zip(hlc.HEADER, ctnl.ROW_KEYS))
      and all(f == "Description" or ehl._TSN_WIN_KEY[f] in ehl._TSN_WINDOWS
              for f in ehl.FIELDS))
check("verification projection == the comparator's load normalization + Excel TRIM "
      "(tab-padded values compare clean, numerics match the trim)",
      ehl.project("HG", "D\t\t") == "D"
      and ehl.project("Length (MI) [MI]", " 000.075 ") == "000.075")
check("canonical key: the comparator's roadbed_canonical_location (suffix "
      "authoritative; a dittoed LEFT block tags the row R)",
      ehl._canon(["012.887R"] + [None] * 30) == "012.887R"
      and ehl._canon(["012.887"] + [None] * 9 + ["+"] * 8 + [None] * 13) == "012.887R")
check("district_index is the sentinel single-folder entry (per-print routing)",
      ehl.district_index(Path("C:/anywhere")) == {"": Path("C:/anywhere")})
# Ditto discipline: a `+`-run cell on either side is NON-ASSERTING in the
# comparison, so enumerate_diffs must never sample it — while a genuine text
# diff in the same row still enumerates.
_hl_a = ["001"] + ["012.887"] + ["a"] * 30
_hl_b = ["001"] + ["012.887"] + ["a"] * 30
_hl_a[2], _hl_b[2] = "X", "+"                       # ditto side -> non-asserting
_hl_a[3], _hl_b[3] = "Y", "Z"                       # a real diff
_diffs = ehl.enumerate_diffs([_hl_a], [_hl_b], {"routing": "per-print"})
check("enumerate_diffs skips ditto cells but keeps real diffs (compared_cell semantics)",
      hlc.HEADER[1] not in _diffs and [e["key"] for e in _diffs[hlc.HEADER[2]]] == ["012.887"]
      and _diffs[hlc.HEADER[2]][0]["dist"] == "" and _diffs[hlc.HEADER[2]][0]["cnty"] == "")
check("enumerate_diffs judges through the LIVE schema (ditto_nonasserting set)",
      chl_cmp._SCHEMA.ditto_nonasserting is True)
# load_sides refuses per-route (route-less) workbooks: evidence groups by the
# leading Route column, which a per-route export doesn't carry.
_hl_tmp = Path(tempfile.mkdtemp(prefix="tsmis_ev_hl_"))
_wb = Workbook()
_ws = _wb.active
_ws.title = chl_cmp.SHEET_NAME
_ws.append(hlc.HEADER)                              # per-route: NO Route column
_ws.append(["012.887"] + ["a"] * 30)
_wb.save(_hl_tmp / "per_route.xlsx")
_r_t, _r_n, _sc, _note = ehl.load_sides(str(_hl_tmp / "per_route.xlsx"),
                                        str(_hl_tmp / "per_route.xlsx"))
check("load_sides refuses per-route (route-less) workbooks with a clear note",
      _sc is None and "Route column" in (_note or ""))
_wb2 = Workbook()
_ws2 = _wb2.active
_ws2.title = chl_cmp.SHEET_NAME
_ws2.append([hlc.ROUTE_COL] + hlc.HEADER)           # consolidated shape
_ws2.append(["001", "012.887"] + ["a"] * 30)
_wb2.save(_hl_tmp / "consolidated.xlsx")
_r_t, _r_n, _sc2, _note2 = ehl.load_sides(str(_hl_tmp / "consolidated.xlsx"),
                                          str(_hl_tmp / "consolidated.xlsx"))
check("load_sides accepts consolidated workbooks (truthy routing sidecar, no note)",
      _sc2 == {"routing": "per-print"} and _note2 is None
      and len(_r_t) == 1 and _r_t[0][0] == "001")
import shutil as _sh
_sh.rmtree(_hl_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("engine misc")
check("reason summarizer dedupes and caps",
      ve._summarize_reasons(["a", "a", "b", "c", "d"]) == "a; b; c"
      and ve._summarize_reasons([]) == "no candidates")
check("evidence never keys off visible text (regex sanity: safe filename)",
      re.sub(r"[^A-Za-z0-9]+", "_", "Med V/WDA").strip("_") == "Med_V_WDA")

# ----------------------------------------------------------------------------- #
print("the pdf/ drop folder exists for the user (v0.21.1 — the update-day gap)")
import paths                                              # noqa: E402
import report_catalog                                     # noqa: E402
import tsn_library                                        # noqa: E402
_pdf_drop_reports = set(ve.TSN_PDF_REPORT.values()) - ve._TSN_PDFS_IN_RAW
check("every pdf/-drop TSN source is catalog-flagged evidence_pdfs (and only those)",
      {report_catalog.TSN[[e.subdir for e in report_catalog.TSN].index(r)].evidence_pdfs
       for r in _pdf_drop_reports} == {True}
      and {e.subdir for e in report_catalog.TSN if e.evidence_pdfs}
      == _pdf_drop_reports)
check("every raw-sourced evidence report is a district_pdfs TSN library (its "
      "prints ARE the raw inputs, so no pdf/ drop folder is flagged)",
      all(report_catalog.TSN[[e.subdir for e in report_catalog.TSN].index(r)].raw_kind
          == "district_pdfs"
          and not report_catalog.TSN[[e.subdir for e in report_catalog.TSN]
                                     .index(r)].evidence_pdfs
          for r in ve._TSN_PDFS_IN_RAW)
      and ve._TSN_PDFS_IN_RAW <= set(ve.TSN_PDF_REPORT.values()))
_tmp = Path(tempfile.mkdtemp())
_old_root = paths.TSN_LIBRARY_ROOT
try:
    paths.TSN_LIBRARY_ROOT = _tmp / "tsn_library"
    root = tsn_library.ensure_layout()
    pdf = root / "highway_detail" / "pdf"
    check("ensure_layout creates highway_detail/pdf/ + drops the hint",
          pdf.is_dir() and any(pdf.glob("_PUT TSN DISTRICT PDFS HERE.txt")))
    check("…and the pdf/ path == the engine's tsn_pdf_dir (one location)",
          pdf == ve.tsn_pdf_dir("highway_detail") == tsn_library.pdf_dir("highway_detail"))
    ipdf = root / "intersection_detail" / "pdf"
    check("ensure_layout creates intersection_detail/pdf/ + its hint (v0.22.0)",
          ipdf.is_dir() and any(ipdf.glob("_PUT TSN DISTRICT PDFS HERE.txt")))
    check("…and it too == the engine's tsn_pdf_dir",
          ipdf == ve.tsn_pdf_dir("intersection_detail")
          == tsn_library.pdf_dir("intersection_detail"))
    readme = root / tsn_library._README_NAME
    check("the root README documents BOTH pdf/ folders",
          readme.is_file()
          and "highway_detail/pdf/" in readme.read_text(encoding="utf-8")
          and "intersection_detail/pdf/" in readme.read_text(encoding="utf-8"))
    # an OUTDATED readme (an updated install) refreshes on the next launch
    readme.write_text("old text from a previous version\n", encoding="utf-8")
    tsn_library.ensure_layout()
    check("a stale README from an older install is refreshed",
          "highway_detail/pdf/" in readme.read_text(encoding="utf-8"))
finally:
    paths.TSN_LIBRARY_ROOT = _old_root
    import shutil as _sh
    _sh.rmtree(_tmp, ignore_errors=True)

print()
if _fail:
    print(f"FAILED: {len(_fail)} check(s):")
    for f in _fail:
        print(f"  - {f}")
    sys.exit(1)
print("check_visual_evidence: all checks passed")

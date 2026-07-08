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
import consolidate_tsmis_highway_detail_pdf as chd
import evidence_highway_detail as ehd
import highway_detail_columns as hdc
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
check("rows: both Highway Detail rows, nothing else",
      ve.rows() == ["highway_detail", "highway_detail_pdf"])
check("capable() matches rows()",
      all(ve.capable(r) for r in ve.rows()) and not ve.capable("highway_log"))
check("TSMIS visuals come from the (PDF)-edition export subdir",
      all(ve.pdf_subdir_for(r) == "highway_detail_pdf" for r in ve.rows()))
check("TSN prints live in the library's highway_detail/pdf folder",
      str(ve.tsn_pdf_dir("highway_detail")).replace("\\", "/")
      .endswith("tsn_library/highway_detail/pdf"))
check("clamp: default/garbage/low/high",
      (ve.clamp_examples(None), ve.clamp_examples("x"), ve.clamp_examples(0),
       ve.clamp_examples(99), ve.clamp_examples("7"))
      == (2, 2, 1, 10, 7))
wbp, imgp = ve.sibling_paths(Path(r"C:\x\comparisons\hd vs tsn.xlsx"))
check("sibling naming: '(evidence).xlsx' + '(evidence images)' folder",
      wbp.name == "hd vs tsn (evidence).xlsx"
      and imgp.name == "hd vs tsn (evidence images)")
avail = ve.availability()
check("availability shape (rows/tsn_pdfs/ready/dir/deps_ok)",
      set(avail) >= {"rows", "tsn_pdfs", "ready", "dir", "deps_ok"})

print("caller-side gate (matrix_build.evidence_opts_for)")
check("toggle off -> None",
      matrix_build.evidence_opts_for(None, "highway_detail", lambda s: s) is None
      and matrix_build.evidence_opts_for({"enabled": False, "examples": 5},
                                         "highway_detail", lambda s: s) is None)
check("unsupported row -> None",
      matrix_build.evidence_opts_for({"enabled": True}, "highway_log",
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
print("engine misc")
check("reason summarizer dedupes and caps",
      ve._summarize_reasons(["a", "a", "b", "c", "d"]) == "a; b; c"
      and ve._summarize_reasons([]) == "no candidates")
check("evidence never keys off visible text (regex sanity: safe filename)",
      re.sub(r"[^A-Za-z0-9]+", "_", "Med V/WDA").strip("_") == "Med_V_WDA")

print()
if _fail:
    print(f"FAILED: {len(_fail)} check(s):")
    for f in _fail:
        print(f"  - {f}")
    sys.exit(1)
print("check_visual_evidence: all checks passed")

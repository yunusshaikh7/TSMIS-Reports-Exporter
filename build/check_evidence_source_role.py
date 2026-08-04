"""Evidence is taken from the source the comparison actually READ (CMP-AUD-210,
completed by the PCOA-FINAL-004 exact-source ruling — HF-05).

Both of a report's matrix rows used to be evidenced from the PDF-edition export,
and a candidate was DROPPED whenever that print disagreed with the compared
value. CMP-AUD-210 moved the Excel-compared side onto the workbook it was
compared from; HF-05 finishes the rule for EVERY side: the vs-TSN and self
flavors render both panels from the two compared workbooks (each resolved
through that side's own comparator hook), the env flavor renders both sides'
own per-route prints, and a drawn panel string equals the compared value or is
visibly elided (PCOA-FINAL-006 — the silent `text[:26]` cut endorsed a
different string).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_evidence_source_role.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import visual_evidence as ve
from openpyxl import Workbook
from PIL import Image

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
print("which source each row was compared FROM")
check("every '_pdf' row is evidenced from the print, every other from the workbook",
      {rk: ve.tsmis_source_role(rk) for rk in sorted(ve.rows())}
      == {"highway_detail": "excel", "highway_detail_pdf": "pdf",
          "highway_log": "excel", "highway_log_pdf": "pdf",
          "highway_sequence": "excel", "highway_sequence_pdf": "pdf",
          "intersection_detail": "excel", "intersection_detail_pdf": "pdf",
          "ramp_detail": "excel", "ramp_detail_pdf": "pdf"})
check("the role covers exactly the evidence-capable rows",
      set(ve.rows()) == set(ve.TSMIS_PDF_SUBDIR))

# --------------------------------------------------------------------------- #
print("addressing the compared workbook")
_r = Path(tempfile.mkdtemp(prefix="check_ev_role_"))
try:
    _HEADER = ["Route", "Location", "Length (MI) [MI]", "City", "SPD"]
    _ROWS = [["001", "R000.129", "000.075", "DAPT", "65"],
             ["001", "R000.204", "000.027", "DAPT", "65"],
             ["037", "003.809", "000.500", "LODI", "55"]]
    _book = _r / "highway_log_consolidated 2026-07-09 ssor-prod.xlsx"
    _wb = Workbook()
    _ws = _wb.active
    _ws.title = "Highway Log"
    _ws.append(_HEADER)
    for _row in _ROWS:
        _ws.append(_row)
    _wb.save(_book)

    _rows, _header = ve._workbook_rows_at(_book, {0, 2})
    check("the header comes back verbatim", _header == _HEADER)
    check("wanted DATA rows map to their real sheet rows (header is row 1)",
          set(_rows) == {0, 2}
          and _rows[0] == ("Highway Log", 2, _ROWS[0])
          and _rows[2] == ("Highway Log", 4, _ROWS[2]))
    check("an empty request reads nothing",
          ve._workbook_rows_at(_book, set()) == ({}, []))
    check("a NAMED data sheet is honored and a missing one reads nothing",
          ve._workbook_rows_at(_book, {0}, sheet="Highway Log")[0]
          and ve._workbook_rows_at(_book, {0}, sheet="No Such Sheet") == ({}, []))
    check("column letters are the ones a user can type into the Name Box",
          [ve._column_letter(n) for n in (1, 3, 26, 27, 28, 52, 53)]
          == ["A", "C", "Z", "AA", "AB", "AZ", "BA"])

    # --------------------------------------------------------------------- #
    print("the Excel cell strip — drawn strings are the compared values "
          "(PCOA-FINAL-006)")
    _img = ve._excel_strip(_HEADER, _ROWS[0], 2, (0, 1))
    check("the strip renders and is wide enough to read",
          _img.width > 300 and _img.height > 60)
    check("it boxes the compared cell in the same red the PDF strip uses",
          (220, 20, 20) in [c[1] for c in _img.getcolors(maxcolors=100000)])
    _long = "RIVERSIDE DR OFF RAMP , OC 53-1493"
    check("panel_cell_text draws a 34-char value IN FULL — no silent cut",
          ve.panel_cell_text(_long) == (_long, False))
    _huge = "X" * (ve.PANEL_TEXT_MAX + 40)
    _drawn, _elided = ve.panel_cell_text(_huge)
    check("a pathological value elides VISIBLY: '…'-terminated prefix of itself",
          _elided and _drawn.endswith("…") and _huge.startswith(_drawn[:-1])
          and len(_drawn) == ve.PANEL_TEXT_MAX)
    _wide_img = ve._excel_strip(["Route", "Description"], ["001", _long], 1, (0,))
    check("the strip sizes its column to the FULL drawn value",
          _wide_img.width > ve._XL_CHAR_W * len(_long))

    # --------------------------------------------------------------------- #
    print("one workbook side of one example (the per-side ctx contract)")

    class Adapter:
        FIELDS = [f for f in _HEADER[1:] if f != "Location"]
        KEY_LABEL = "Location"

        @staticmethod
        def project(_field, raw):
            return str(raw or "").strip()

    def side(field, va, row_index=0, rows=None, header=None):
        ctx = {"rows": _rows if rows is None else rows,
               "header": _HEADER if header is None else header,
               "book_name": _book.name, "resolve": "excel_column_for",
               "project": "project", "index_key": "row_index",
               "value_key": "va", "label": "TSMIS (Excel)"}
        return ve._workbook_side(Adapter, {"row_index": row_index, "va": va},
                                 field, ctx)

    _img2, _label, _address, _why, _drawn = side("Length (MI) [MI]", "000.075")
    check("a matching cell renders, labelled with the workbook and its address",
          _why is None and _img2 is not None and _address == "Highway Log!C2"
          and _label == f"TSMIS (Excel)  —  {_book.name} · Highway Log!C2")
    check("the label names the SIDE and the workbook, never a print",
          "TSMIS (Excel)" in _label and "PDF" not in _label)

    _, _, _, _why2, _ = side("Length (MI) [MI]", "999.999")
    check("a cell that no longer holds the compared value is refused",
          _why2 is not None and "no longer holds" in _why2)
    _, _, _, _why3, _ = side("Length (MI) [MI]", "000.075", row_index=None)
    check("a candidate with no row position is refused", _why3 is not None)
    _, _, _, _why4, _ = side("Length (MI) [MI]", "000.075", row_index=99)
    check("a row that is not in the compared workbook is refused",
          _why4 is not None and "not found" in _why4)
    _, _, _, _why5, _ = side("Nonexistent Column", "000.075")
    check("a column that is not resolvable in this workbook edition is refused",
          _why5 is not None and "cannot be resolved" in _why5)
    _, _, _, _why6, _ = side("SPD", "65", rows={0: ("S", 2, ["001", "R000.129"])})
    check("a short workbook row is refused, never read past its end",
          _why6 is not None and "short of the compared column" in _why6)

    # THE FINDING'S CASE: the compared Excel value has no counterpart in the
    # companion print at all. The PDF route can only reject it; the Excel route
    # evidences it, because the workbook is where it was compared from.
    _img3, _label3, _addr3, _why7, _ = side("City", "LODI", row_index=2)
    check("an Excel value the companion print never carried is still "
          "evidenceable (CMP-AUD-210)",
          _why7 is None and _img3 is not None and _addr3 == "Highway Log!D4")

    # HF-05: side B of a vs-TSN example is the NORMALIZED TSN WORKBOOK panel,
    # resolved through the adapter's tsn hook — never a borrowed print.
    class TsnAdapter(Adapter):
        @staticmethod
        def tsn_excel_column_for(field, header):
            return header.index(field) if field in header else None

        @staticmethod
        def tsn_project(_field, raw):
            return str(raw or "").strip()

    _ctx_b = {"rows": _rows, "header": _HEADER, "book_name": _book.name,
              "resolve": "tsn_excel_column_for", "project": "tsn_project",
              "index_key": "row_index_b", "value_key": "vb", "label": "TSN"}
    _img4, _label4, _addr4, _why8, _ = ve._workbook_side(
        TsnAdapter, {"row_index_b": 0, "vb": "000.075"}, "Length (MI) [MI]",
        _ctx_b)
    check("the TSN side renders from the compared workbook through its own hook",
          _why8 is None and _img4 is not None
          and _label4 == f"TSN  —  {_book.name} · Highway Log!C2")
finally:
    shutil.rmtree(_r, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("every adapter carries the row position each side's Excel address needs")
_ADAPTERS = ("evidence_highway_detail", "evidence_highway_log",
             "evidence_highway_sequence", "evidence_intersection_detail",
             "evidence_ramp_detail")
for _name in _ADAPTERS:
    _src = Path(__file__).resolve().parent.parent / "scripts" / f"{_name}.py"
    _text = _src.read_text(encoding="utf-8")
    check(f"{_name}.enumerate_diffs emits both row positions",
          "row_index=ia" in _text and "row_index_b=ib" in _text)

# --------------------------------------------------------------------------- #
print("the PDF-vs-Excel self check can be illustrated")
check("generate() knows exactly the three flavors",
      ve.FLAVORS == (ve.FLAVOR_TSN, ve.FLAVOR_SELF, ve.FLAVOR_ENV))
for _name in _ADAPTERS:
    _mod = __import__(_name)
    check(f"{_name} exposes the SELF comparator's loader pair",
          callable(getattr(_mod, "load_sides_self", None)))
    for _hook in ("pdf_excel_column_for", "tsn_excel_column_for",
                  "tsn_project", "workbook_sheet"):
        check(f"{_name} exposes {_hook} (the per-edition panel resolution)",
              callable(getattr(_mod, _hook, None)))
check("every evidence row can illustrate its self check",
      all(ve.self_capable(rk) for rk in ve.rows()))

# --------------------------------------------------------------------------- #
print("the cross-environment lane (HF-10)")
check("exactly the five PDF-vs-PDF env placements are env-capable",
      sorted(ve.env_rows()) == ["highway_log_pdf", "highway_sequence_pdf",
                                "intersection_detail_pdf", "ramp_detail_pdf",
                                "ramp_summary"]
      and all(ve.env_capable(rk) for rk in ve.env_rows()))
check("ramp_summary is env-only: its vs-TSN evidence absence stays the "
      "audit-approved state", not ve.capable("ramp_summary"))
for _rk in ve.env_rows():
    _mod = ve.env_adapter_for(_rk)
    for _hook in ("env_fields", "env_locate", "env_value", "env_box",
                  "tsmis_pdf_path"):
        check(f"{_rk}'s env adapter exposes {_hook}",
              callable(getattr(_mod, _hook, None)))

# The censused defect: enumerate_diffs used to walk a HARDCODED copy of the
# vs-TSN header. The PDF-vs-Excel schema carries a column the vs-TSN one does
# not ("PM Suffix" on Highway Sequence), so every field index past it shifted
# and the engine judged the wrong column — caught only because the published
# cell disagreed. The field loop must walk the SCHEMA's own header.
import compare_highway_sequence_tsn as chsl
import evidence_highway_sequence as ehsl
from compare_core import CompareSchema

_SELF_HEADER = ["County", "PM", "PM Suffix", "City", "HG", "FT",
                "Distance To Next Point", "Description"]
_WIDE = CompareSchema(report_name="HSL self", header=_SELF_HEADER, key_field=1)


def _wide_row(ft):
    row = ["001", "MON", "028.013", "", "", "", ft, "", ""]
    return row


_diffs = ehsl.enumerate_diffs([_wide_row("U")], [_wide_row("H")], {},
                              schema=_WIDE)
check("a schema with an extra column reports the RIGHT field name",
      list(_diffs) == ["FT"])
check("...and the values are that column's, not a neighbour's",
      _diffs["FT"][0]["va"] == "U" and _diffs["FT"][0]["vb"] == "H")
check("...with both sides' row positions carried",
      _diffs["FT"][0]["row_index"] == 0 and _diffs["FT"][0]["row_index_b"] == 0)
check("the narrow vs-TSN header still walks its own columns unchanged",
      len(chsl._SCHEMA.header) + 1 == len(_SELF_HEADER))

# --------------------------------------------------------------------------- #
# The composed image tells the truth about what it drew (PCOA-FINAL-006's
# truthfulness half) and never CLIPS what it says (the RB4-A1 native-scale
# inspection found both: a title/subline cut mid-glyph at the canvas edge, and
# a long left caption overprinting the right one into an unreadable mash).
# --------------------------------------------------------------------------- #
print("the composed image: no clipping, no overprint, no silent restatement")

_note = ve._normalization_note(("64-01-01", "2004-01-01"),
                               ("1964-01-01", "2004-01-01"),
                               ("TSMIS (PDF)", "TSN"))
check("a source form the comparison normalized is DISCLOSED on the image",
      "64-01-01" in _note and "compared value" in _note
      and "TSMIS (PDF)" in _note and "2004-01-01" not in _note)
check("a DERIVED value's composite source cell is disclosed the same way "
      "(RD District is the leading component of Location)",
      "12-SD-005" in ve._normalization_note(("12-SD-005", "12"), ("12", "12"),
                                            ("TSMIS (PDF)", "TSN")))
check("a drawn value that IS the compared value adds no note",
      ve._normalization_note(("A", "B"), ("A", "B"), ("X", "Y")) == "")
check("a crop flavor (no drawn strings) adds no note",
      ve._normalization_note((None, None), ("A", "B"), ("X", "Y")) == "")
check("an ELIDED drawn value is not mistaken for a normalization difference",
      ve._normalization_note((ve.panel_cell_text(_huge)[0], None),
                             (_huge, ""), ("X", "Y")) == "")

_tiny = Image.new("RGB", (120, 40), (255, 255, 255))
_long_title = "Description — TSMIS (PDF) 'EQUATES TO END R REALIGNMENT'  vs  " \
              "TSMIS (Excel) 'END R REALIGNMENT'"
_long_sub = ("Route 046 @ 50.904 — the workbook cell Intersection Detail!F5563 "
             "and the workbook cell Intersection Detail (TSN)!G5676 re-read "
             "and verified against the compared values")
_long_label = "TSMIS (PDF)  —  tsmis_intersection_detail_pdf_consolidated " \
              "2026-07-23 ssor-prod.xlsx · Intersection Detail!F5563"
_cdir = tempfile.mkdtemp(prefix="evidence_compose_")
try:
    _st = Path(_cdir) / "s.png"
    ve._compose_stacked(_long_title, _long_sub, _long_label, _tiny,
                        "TSN — x.xlsx · A1", _tiny, _st, note=_note)
    _pr = Path(_cdir) / "p.png"
    ve._compose_pair(_long_title, _long_sub, _long_label, _tiny,
                     "TSN — x.xlsx · A1", _tiny, _pr, note=_note)
    _need = max(ve._text_w(_long_title, ve._font(26, True)),
                ve._text_w(_long_sub, ve._font(17)),
                ve._text_w(_note, ve._font(17, True)))
    _sw = Image.open(_st).width
    _pw = Image.open(_pr).width
    check("stacked: the canvas grows to hold the title/subline/note in full",
          _sw >= _need + 16)
    check("paired: the canvas grows to hold the title/subline/note in full",
          _pw >= _need + 16)
    # The left caption's own column must reach past its text, so the right
    # caption starts beyond it and the two can never overprint.
    check("paired: a long left caption cannot reach the right caption",
          _pw >= ve._text_w(_long_label, ve._font(16, True))
          + ve._text_w("TSN — x.xlsx · A1", ve._font(16, True)) + 48)
finally:
    shutil.rmtree(_cdir, ignore_errors=True)

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s):")
    for name in _fail:
        print(f"  - {name}")
    sys.exit(1)
print("check_evidence_source_role: all checks passed")

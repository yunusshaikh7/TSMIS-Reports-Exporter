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
import inspect
import os
import re
import shutil
import sys
import tempfile
import types
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
# Stated FIRST as an assertion, not an import-time crash: against a runtime
# without the exact-source rebuild this file died on the first new call and
# printed nothing, so it could not demonstrate the defect it exists to catch.
print("the exact-source contract this file depends on")
check("the engine addresses the compared workbook's rows and renders each "
      "side's panel from it (_workbook_rows_at + _workbook_side)",
      hasattr(ve, "_workbook_rows_at") and hasattr(ve, "_workbook_side"))
check("a drawn panel string is full or visibly elided (panel_cell_text)",
      hasattr(ve, "panel_cell_text"))
check("the strip's labels follow the values, and a normalized source form is "
      "disclosed (_display_header + _normalization_note)",
      hasattr(ve, "_display_header") and hasattr(ve, "_normalization_note"))

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
    check("the strip sizes its column to the MEASURED drawn value width",
          _wide_img.width >= ve._text_w(_long, ve._font(19)) + 16)
    # Wide glyphs are the case a per-character estimate under-allocates
    # (RB-4 audit: ~18 px/char inked vs a 13 px allowance) — the column must
    # hold the measured ink of an all-caps M/W-heavy value too.
    _mheavy = "WWMM MMWW WWMM MMWW WWMM"
    _mimg = ve._excel_strip(["Route", "Description"], ["001", _mheavy], 1, (0,))
    check("a wide-glyph value's column holds its MEASURED ink",
          _mimg.width >= ve._text_w(_mheavy, ve._font(19)) + 16)

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
# These hooks are PROBED, not merely counted: an existence assertion passes
# against a stub that resolves every field to column 0, which is exactly the
# wrong-cell defect the exact-source rule exists to prevent.
_FOREIGN_HEADER = [f"zzz{i}" for i in range(40)]
_NO_SUCH_FIELD = "zzz no such compared field"
_SHEET_KINDS = ("tsn", "tsmis", "pdf")

for _name in _ADAPTERS:
    _mod = __import__(_name)
    _fields = list(getattr(_mod, "FIELDS", ()) or ())
    check(f"{_name} loads both self-check sides from a print and a workbook",
          str(inspect.signature(_mod.load_sides_self))
          == "(pdf_path, excel_path)")
    for _hook in ("excel_column_for", "pdf_excel_column_for",
                  "tsn_excel_column_for"):
        _fn = getattr(_mod, _hook, None)
        check(f"{_name}.{_hook} REFUSES a header it does not recognise "
              "(no positional default onto the wrong cell)",
              _fn is not None
              and all(_fn(f, _FOREIGN_HEADER) is None for f in _fields)
              and _fn(_NO_SUCH_FIELD, _FOREIGN_HEADER) is None
              and _fn(_fields[0], []) is None)
    _tp = getattr(_mod, "tsn_project", None)
    _projected = _tp(_fields[0], "  Sample 12 ") if _tp else None
    check(f"{_name}.tsn_project is a settled projection (idempotent, and a "
          "blank cell reads as the empty string, never None)",
          _tp is not None and _tp(_fields[0], _projected) == _projected
          and _tp(_fields[0], None) == "")
    _ws = getattr(_mod, "workbook_sheet", None)
    check(f"{_name}.workbook_sheet names a sheet for every edition, with the "
          "two TSMIS-side editions sharing one sheet",
          _ws is not None
          and all(isinstance(_ws(k), str) and _ws(k) for k in _SHEET_KINDS)
          and _ws("tsmis") == _ws("pdf")
          and _ws(_NO_SUCH_FIELD) == _ws("tsmis"))
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
# The env hooks are probed the same way. `env_fields()` is the whole field
# universe the engine hands the ledger (`_FieldsView`), so env_value/env_box
# are only ever asked about a field the adapter declared — what must be proved
# here is that the declaration is well formed and that the print resolution
# honours the route it was asked for.
_ENV_SIGNATURES = {"env_locate": "(pdf_path, needed_keys)",
                   "env_value": "(rec, field)", "env_box": "(rec, field)"}
_PROBE_ROUTE = "001"
_edir = tempfile.mkdtemp(prefix="check_ev_envpath_")
try:
    for _rk in ve.env_rows():
        _mod = ve.env_adapter_for(_rk)
        _ef = list(_mod.env_fields())
        check(f"{_rk}: env_fields declares a well-formed field universe",
              bool(_ef) and len(set(_ef)) == len(_ef)
              and all(isinstance(f, str) and f for f in _ef))
        for _hook, _sig in _ENV_SIGNATURES.items():
            check(f"{_rk}: {_hook} takes the arguments the engine passes",
                  str(inspect.signature(getattr(_mod, _hook))) == _sig)
        _pp = _mod.tsmis_pdf_path(_edir, _PROBE_ROUTE)
        check(f"{_rk}: tsmis_pdf_path resolves inside the run folder, under "
              "the end-anchored per-route filename contract",
              _pp is not None
              and Path(_pp).parent == Path(_edir)
              and Path(_pp).name.endswith(f"_route_{_PROBE_ROUTE}.pdf"))
finally:
    shutil.rmtree(_edir, ignore_errors=True)

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
# The strip's header labels are POSITION-AUTHORITATIVE: a consolidated edition
# whose own labels sit beside their values (the ID PDF workbook labels value
# position 9 — a date — 'INT Type') must not draw the boxed value under a
# neighbour's label. Found by the RB4-A1 native-scale inspection.
print("the strip's header labels follow the VALUES, not the workbook's shift")
import evidence_intersection_detail as _eid6

_SHIFTED = ["Route", "P", "Post Mile", "S", "Location", "Date of Record",
            "H/G", "City Code", "R/U", "INT Type", "INT Eff-Date", "Ctrl T",
            "Ctrl Type", "Light Eff-Date", "Light T/Y", "ML Eff-Date",
            "ML S/M", "ML L/C", "ML R/C", "ML T/P", "ML N/L", "Description",
            "Main Line Lgth", "Inter Eff-Date", "Inter S", "Inter L",
            "Inter R", "Inter T", "Inter N", "Int St Eff-Date", "Intrte S",
            "Intrte Route", "Intrte Post", "Intrte Mile", "Xing P/S",
            "Xing Line Lgth"]
_fixed = ve._display_header(_eid6, _SHIFTED, _eid6.pdf_excel_column_for)
_boxed = _eid6.pdf_excel_column_for("INT Type Eff-Date", _SHIFTED)
check("the boxed value's own column is labelled with the COMPARED field",
      _boxed == 9 and _fixed[_boxed] == "INT Type Eff-Date"
      and _SHIFTED[_boxed] == "INT Type")
check("the neighbouring shifted labels are corrected too",
      _fixed[10] == "INT Type" and _fixed[12] == "Control Type")
check("a position no compared field claims keeps the workbook's own label",
      _fixed[0] == "Route" and _fixed[4] == "Location")
check("an adapter with no resolve hook leaves the header untouched",
      ve._display_header(_eid6, _SHIFTED, None) is _SHIFTED)

# A shifted layout leaves the workbook's OWN copy of a placed name sitting on a
# position no compared field claims — the classic Ramp Detail export labels
# position 11 'Description' while the Description VALUE is at 10. Drawing both
# puts two identical headers in one strip and the reader cannot tell which
# column the red box is under.
_DUP_HEADER = ["Route", "PM", "X", "Description"]
_DUP_AT = {"Route": 0, "PM": 1, "Description": 2}
_dup_adapter = types.SimpleNamespace(FIELDS=tuple(_DUP_AT), __name__="dupfix")
_dup = ve._display_header(_dup_adapter, _DUP_HEADER,
                          lambda f, _h: _DUP_AT.get(f))
check("the workbook's stale duplicate of a placed label is blanked, so one "
      "name never appears over two columns",
      _dup[2] == "Description" and _dup[3] == ""
      and _DUP_HEADER[3] == "Description")
check("...and an unclaimed position with its own distinct label is kept",
      _dup[:2] == ["Route", "PM"]
      and ve._display_header(_dup_adapter, ["Route", "PM", "X", "Y"],
                             lambda f, _h: _DUP_AT.get(f))[3] == "Y")

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

# The composed canvas is measured from its OWN INK. Sizing the assertion with
# the same width helper the composer sizes the canvas with is circular — a
# regression that halved every measurement would satisfy both sides of it.
_BG = (255, 255, 255)
_HEADER_TOP = 10                 # first title row
_CAPTION_H = 18                  # a caption line's ink band (16 px bold font)
_CAPTION_GAP = 10                # background columns that separate two captions
_PAD_MAX = 0.5                   # ink must reach past this fraction of the width


def _ink_columns(img, y0, y1):
    """Every x carrying non-background ink in the horizontal band [y0, y1)."""
    px = img.load()
    return [x for x in range(img.width)
            if any(px[x, y] != _BG for y in range(y0, min(y1, img.height)))]


def _ink_runs(cols, gap):
    """The ink columns grouped into runs separated by at least `gap` blanks."""
    runs = []
    for x in cols:
        if runs and x - runs[-1][1] <= gap:
            runs[-1][1] = x
        else:
            runs.append([x, x])
    return runs


_tiny = Image.new("RGB", (120, 40), (255, 255, 255))
_long_title = "Description — TSMIS (PDF) 'EQUATES TO END R REALIGNMENT'  vs  " \
              "TSMIS (Excel) 'END R REALIGNMENT'"
_long_sub = ("Route 046 @ 50.904 — the workbook cell Intersection Detail!F5563 "
             "and the workbook cell Intersection Detail (TSN)!G5676 re-read "
             "and verified against the compared values")
_long_label = "TSMIS (PDF)  —  tsmis_intersection_detail_pdf_consolidated " \
              "2026-07-23 ssor-prod.xlsx · Intersection Detail!F5563"
# The caption test uses a SHORT title block, so the header can never be what
# widens the canvas, and space-free captions, so each caption is one ink run.
_SHORT_TITLE = "D"
_SHORT_SUB = "r"
_L_CAP = ("TSMIS_(PDF)_tsmis_intersection_detail_pdf_consolidated_2026-07-23_"
          "ssor-prod.xlsx!Intersection_Detail!F5563")
_R_CAP = "TSN_x.xlsx!A1"
_cdir = tempfile.mkdtemp(prefix="evidence_compose_")
try:
    _st = Path(_cdir) / "s.png"
    ve._compose_stacked(_long_title, _long_sub, _long_label, _tiny,
                        "TSN — x.xlsx · A1", _tiny, _st, note=_note)
    _pr = Path(_cdir) / "p.png"
    ve._compose_pair(_long_title, _long_sub, _long_label, _tiny,
                     "TSN — x.xlsx · A1", _tiny, _pr, note=_note)
    # The title block occupies everything above the first caption row.
    _hband = (_HEADER_TOP, 84 + ve._NOTE_H - 2)
    for _name, _path in (("stacked", _st), ("paired", _pr)):
        _im = Image.open(_path)
        _cols = _ink_columns(_im, *_hband)
        check(f"{_name}: the title block's ink ends INSIDE the canvas "
              "(nothing is cut mid-glyph at the edge)",
              bool(_cols) and max(_cols) < _im.width - 1)
        check(f"{_name}: ...and the canvas is sized to that ink, not padded "
              "far past it",
              bool(_cols) and max(_cols) > _im.width * _PAD_MAX)

    # A long left caption must not reach the right one. Measured as ink: the
    # caption row must hold TWO separated runs, both inside the canvas. The
    # pre-fix composer sized each column from its IMAGE, so the left caption
    # ran under the right one and off the edge — one clipped run, not two.
    _pc = Path(_cdir) / "c.png"
    ve._compose_pair(_SHORT_TITLE, _SHORT_SUB, _L_CAP, _tiny, _R_CAP, _tiny,
                     _pc)
    _ci = Image.open(_pc)
    _cap_y = 84 + 4
    _cap_cols = _ink_columns(_ci, _cap_y, _cap_y + _CAPTION_H)
    _runs = _ink_runs(_cap_cols, _CAPTION_GAP)
    check("paired: the two captions are separate ink runs, never overprinted",
          len(_runs) == 2)
    check("paired: neither caption is cut off at the canvas edge",
          bool(_cap_cols) and max(_cap_cols) < _ci.width - 1)
    check("paired: the right caption starts past the left caption's last ink",
          len(_runs) == 2 and _runs[1][0] > _runs[0][1])
finally:
    shutil.rmtree(_cdir, ignore_errors=True)

# --------------------------------------------------------------------------- #
# The CALL SITES, not only the helpers. `_display_header` and
# `_normalization_note` are each called from exactly one place in the engine;
# deleting either line satisfies every unit assertion above. One example driven
# end to end through `_try_example` proves the strip really draws the corrected
# header and the composed image really carries the disclosure.
# --------------------------------------------------------------------------- #
print("the engine's own render path uses both (the call sites)")

# A workbook whose labels sit one position AFTER their values, the shift class
# `_display_header` exists for: position 2 holds the Eff-Date, labelled 'INT
# Type'.
_WB_HEADER = ["Route", "Post Mile", "INT Type", "INT Type Eff-Date",
              "Ctrl Type"]
_WB_AT = {"Route": 0, "Post Mile": 1, "INT Type Eff-Date": 2, "INT Type": 3,
          "Control Type": 4}
_TWO_DIGIT_YEAR = re.compile(r"^\d\d-")


def _wb_resolve(field, header):
    del header                   # this fixture resolves by name, not by shift
    return _WB_AT.get(field)


def _wb_project(field, value, **kwargs):
    """Widen a two-digit year before comparing — so the workbook cell and the
    compared value are the same fact carried in two different forms."""
    del kwargs
    text = str(value or "")
    if field == "INT Type Eff-Date" and _TWO_DIGIT_YEAR.match(text):
        return "19" + text
    return text


_ADAPTER = types.SimpleNamespace(
    __name__="check_evidence_source_role_fixture", FIELDS=tuple(_WB_AT),
    KEY_LABEL="Post Mile", project=_wb_project, tsn_project=_wb_project,
    pdf_excel_column_for=_wb_resolve, tsn_excel_column_for=_wb_resolve)

_seen_headers, _seen_notes = [], []
_real_strip = ve._excel_strip
_real_stacked = ve._compose_stacked
_real_pair = ve._compose_pair


def _rec_strip(header, values, target_index, key_indexes=(0,)):
    _seen_headers.append(list(header))
    return _real_strip(header, values, target_index, key_indexes)


def _rec_stacked(title, sub, tl, ti, bl, bi, out, note=""):
    _seen_notes.append(note)
    return _real_stacked(title, sub, tl, ti, bl, bi, out, note=note)


def _rec_pair(title, sub, ll, li, rl, ri, out, note=""):
    _seen_notes.append(note)
    return _real_pair(title, sub, ll, li, rl, ri, out, note=note)


_idir = Path(tempfile.mkdtemp(prefix="evidence_callsites_"))
ve._excel_strip, ve._compose_stacked, ve._compose_pair = (
    _rec_strip, _rec_stacked, _rec_pair)
try:
    _ex = {"route": "046", "key": "50.904", "va": "1964-01-01",
           "vb": "1964-01-02", "row_index": 0, "row_index_b": 0}
    _side_a = {"index_key": "row_index",
               "rows": {0: ("Intersection Detail", 5563,
                            ["001", "12.345", "64-01-01", "T", "S"])},
               "header": _WB_HEADER, "resolve": "pdf_excel_column_for",
               "project": "project", "value_key": "va",
               "label": "TSMIS (PDF)", "book_name": "tsmis.xlsx"}
    _side_b = {"index_key": "row_index_b",
               "rows": {0: ("Intersection Detail (TSN)", 5676,
                            ["001", "12.345", "1964-01-02", "T", "S"])},
               "header": _WB_HEADER, "resolve": "tsn_excel_column_for",
               "project": "tsn_project", "value_key": "vb",
               "label": "TSN", "book_name": "tsn.xlsx"}
    _entry, _why = ve._try_example(
        _ADAPTER, _ex, "INT Type Eff-Date", _idir, 1, {},
        side_labels=("TSMIS (PDF)", "TSN"), side_a=_side_a, side_b=_side_b)
    check("the engine renders a two-workbook example end to end",
          _why is None and bool(_entry))
    check("...and BOTH strips drew the CORRECTED header, not the workbook's",
          len(_seen_headers) == 2
          and all(h[2] == "INT Type Eff-Date" and h[3] == "INT Type"
                  for h in _seen_headers)
          and _WB_HEADER[2] == "INT Type")
    check("...and the composed images carry the normalization disclosure",
          len(_seen_notes) == 2
          and all("64-01-01" in n and "compared value" in n
                  and "TSMIS (PDF)" in n for n in _seen_notes))
    check("...on both chosen layouts, both written to disk",
          bool(_entry) and all((_idir / _entry[k]).is_file()
                               for k in ("stacked", "pair")))
finally:
    ve._excel_strip = _real_strip
    ve._compose_stacked = _real_stacked
    ve._compose_pair = _real_pair
    shutil.rmtree(_idir, ignore_errors=True)

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s):")
    for name in _fail:
        print(f"  - {name}")
    sys.exit(1)
print("check_evidence_source_role: all checks passed")

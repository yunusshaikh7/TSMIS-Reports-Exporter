"""Build the TSMIS-vs-TSN Ramp Detail discrepancy workbook.

The reference v0.17.0 vs-TSN comparator (the recipe the other reports follow).
Both sides are XLSX, but in DIFFERENT shapes, so each side has its own loader that
projects to ONE shared comparison header keyed on PM (postmile):

  * TSMIS side — the CONSOLIDATED Ramp Detail workbook (sheet "TSAR - Ramp Detail"
    with a prepended "Route" column). Its header row has blank/merged cells that
    shift the City Code / R/U / Description LABELS right of their values, so the
    columns are read BY POSITION (verified against the real export), not by name.
  * TSN side — the statewide raw DB dump (sheet "Sheet 1", 18 named columns) OR the
    library's normalized workbook ("Route" + the shared header). Route comes from
    LOCATION ("01-DN-101" -> "101").

Reconciled on real data (route 1, 272/272 ramps match by normalized PM): PR, PM,
Date of Record (-> ISO), HG, Area 4, City Code, R/U (== TSN POP), and Description
(after stripping the TSMIS leading "<route>/" prefix) all line up; every residual
is a genuine TSMIS-vs-TSN difference. The TSN-only DB columns (Ramp Name, On/Off,
Ramp Type, ADT) have no TSMIS counterpart, so they are CONTEXT fields — shown for
reference, never counted as a diff (CompareSchema.context_fields).

Console-free like the other comparators: progress via events.on_log, overwrite via
the confirm_overwrite callback, a ConsolidateResult returned. Engine in compare_core.
"""
import re
from pathlib import Path

try:
    from openpyxl import load_workbook
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_tsn_common as ctc
from compare_core import CompareSchema, normalize_value
from paths import today_str

REPORT_NAME = "Ramp Detail"
TSMIS_SHEET = "TSAR - Ramp Detail"       # the consolidated/per-route TSMIS sheet
TSN_SHEET = "Sheet 1"                     # the raw TSN statewide sheet

# The shared comparison header (key + fields), in display order. PM is the key.
# Compared fields assert; CONTEXT_FIELDS are shown but never counted as a diff.
KEY = "PM"
SHARED_HEADER = ["PR", "PM", "Date of Record", "HG", "Area 4", "City Code", "R/U",
                 "Description", "Ramp Name", "On/Off", "Ramp Type", "ADT"]
KEY_FIELD = SHARED_HEADER.index(KEY)      # 1
CONTEXT_FIELDS = ("Ramp Name", "On/Off", "Ramp Type", "ADT")   # TSN-only -> non-asserting
DATE_FIELDS = ("Date of Record",)
NORMALIZED_SHEET = "Ramp Detail (TSN)"    # the library's normalized TSN workbook sheet

_SCHEMA = CompareSchema(
    report_name="Ramp Detail",
    header=SHARED_HEADER,
    side_a="TSMIS",
    side_b="TSN",
    id_noun="ramp",
    id_noun_plural="ramps",
    pair_noun="postmile",
    sides_noun="systems",
    date_fields=DATE_FIELDS,
    data_widths={"Description": 26, "Date of Record": 11},
    cmp_widths={"Description": 30, "Date of Record": 12},
    one_sided_note_extra=" (ramps one system lists at a postmile the other doesn't)",
    key_field=KEY_FIELD,
    context_fields=CONTEXT_FIELDS,
)

_ROUTE_FROM_LOCATION = re.compile(r"^\s*\d{2}-[A-Za-z]{2,3}-(\w+)\s*$")  # "01-DN-101" -> "101"
_DESC_PREFIX = re.compile(r"^\s*\d+\s*/\s*")     # TSMIS "001/NB OFF…" -> "NB OFF…"


# --------------------------------------------------------------------------- #
# normalization (shared by both loaders)
# --------------------------------------------------------------------------- #
def _norm_route(tok):
    t = ("" if tok is None else str(tok)).strip().upper()
    m = re.fullmatch(r"(\d+)([A-Z]?)", t)
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else t


# PM + Date-of-Record canon shared with Intersection Detail, homed in
# compare_tsn_common (P5b/S04). The rd._norm_pm / rd._iso_date names are kept so the
# loaders, importers, and the golden canary still resolve them.
_norm_pm = ctc.norm_pm
_iso_date = ctc.iso_date


def _strip_desc_prefix(text):
    return _DESC_PREFIX.sub("", ("" if text is None else str(text)).strip())


def _v(x):
    return normalize_value(x)


# --------------------------------------------------------------------------- #
# TSN side: raw statewide "Sheet 1" OR the library's normalized workbook
# --------------------------------------------------------------------------- #
def _tsn_raw_row(r, h):
    """Project one raw TSN Sheet-1 row (h = {NAME: idx}) to [route, *SHARED_HEADER]."""
    def g(name):
        i = h.get(name)
        return r[i] if i is not None and i < len(r) else None
    _loc_raw = g("LOCATION")
    loc = "" if _loc_raw is None else str(_loc_raw)
    m = _ROUTE_FROM_LOCATION.match(loc)
    route = _norm_route(m.group(1)) if m else loc.strip().upper()
    return [route,
            _v(g("PR")), _norm_pm(g("PM")), _iso_date(g("DATE_OF_RECORD")),
            _v(g("HG")), _v(g("AREA_4")), _v(g("CITY_CODE")), _v(g("POP")),
            _strip_desc_prefix(g("DESCRIPTION")),
            _v(g("RAMP_NANE")), _v(g("ON_OFF")), _v(g("RAMP_TYPE")), _v(g("ADT"))]


def tsn_rows_from_raw(path):
    """Every route's rows from the raw TSN statewide workbook, consolidated shape."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        sn = TSN_SHEET if TSN_SHEET in wb.sheetnames else wb.sheetnames[0]
        it = wb[sn].iter_rows(values_only=True)
        header = list(next(it, []) or [])
        h = {str(n).strip(): i for i, n in enumerate(header) if n is not None}
        if "LOCATION" not in h or "PM" not in h:
            raise ValueError("the TSN Ramp Detail workbook is missing LOCATION/PM "
                             "columns — pick the raw 'TSAR - RAMPS DETAIL' export.")
        rows = [_tsn_raw_row(list(r), h) for r in it
                if r and any(c is not None and str(c).strip() != "" for c in r)]
        return rows
    finally:
        wb.close()


def _load_tsn(path):
    """TSN side -> (rows, has_route=True). Reads the raw statewide Sheet-1, or the
    library's already-normalized workbook (header 'Route' + SHARED_HEADER)."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        sheets = wb.sheetnames
        if NORMALIZED_SHEET in sheets:                       # normalized library copy
            it = wb[NORMALIZED_SHEET].iter_rows(values_only=True)
            next(it, None)                                   # header row
            rows = [[_v(c) for c in list(r)[:len(SHARED_HEADER) + 1]]
                    for r in it if r and any(c not in (None, "") for c in r)]
            return rows, True
    finally:
        wb.close()
    return tsn_rows_from_raw(path), True


# --------------------------------------------------------------------------- #
# TSMIS side: the consolidated Ramp Detail workbook (columns read BY POSITION)
# --------------------------------------------------------------------------- #
# Consolidated value positions (Route prepended): Route0 Location1 PR2 PM3 Date4
# blank5 HG6 Area4 7 City8 R/U9 Description10 (blank11). The header LABELS shift
# right of City Code/R/U/Description, so position — not name — is authoritative.
def _tsmis_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    return [_norm_route(at(0)),
            _v(at(2)), _norm_pm(at(3)), _iso_date(at(4)),
            _v(at(6)), _v(at(7)), _v(at(8)), _v(at(9)),
            _strip_desc_prefix(at(10)),
            "", "", "", ""]                                  # TSN-only context: blank here


def _load_tsmis(path):
    """TSMIS side -> (rows, has_route=True). The CONSOLIDATED Ramp Detail workbook
    (a leading 'Route' column). Columns are read by position (the export's header
    row is column-shifted); a header sanity-check guards against layout drift."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if TSMIS_SHEET not in wb.sheetnames:
            raise ValueError(f"{name} has no '{TSMIS_SHEET}' sheet — pick the "
                             "consolidated TSMIS Ramp Detail workbook.")
        it = wb[TSMIS_SHEET].iter_rows(values_only=True)
        header = [str(c).strip() if c is not None else "" for c in (next(it, []) or [])]
        if not header or header[0] != "Route" or "PM" not in header[:5]:
            raise ValueError(f"{name} isn't a CONSOLIDATED Ramp Detail workbook "
                             "(expected a leading 'Route' column) — consolidate the "
                             "per-route exports first.")
        rows = [_tsmis_row(list(r)) for r in it
                if r and any(c is not None and str(c).strip() != "" for c in r)]
        return rows, True
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# adapter surface (registry "files" kind)
# --------------------------------------------------------------------------- #
def suggest_name(tsmis_path):
    stem = Path(tsmis_path).stem
    m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
    tag = (f"Route{m.group(1).lstrip('0') or '0'}" if m
           else "Consolidated" if "consolidated" in stem.lower() else "Ramp_Detail")
    return f"TSMIS_vs_TSN_RampDetail_{tag}_Comparison {today_str()}.xlsx"


def _load_pair(tsmis_path, tsn_path):
    """(rows_t, rows_n, warnings) for the shared driver — the FLAT detail pair carries
    no input warnings, so run_compare uses its () default."""
    rows_t, _ = _load_tsmis(tsmis_path)
    rows_n, _ = _load_tsn(tsn_path)
    return rows_t, rows_n, None


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the Ramp Detail TSMIS-vs-TSN comparison workbook(s). `tsmis_path` is the
    consolidated TSMIS Ramp Detail workbook; `tsn_path` the TSN statewide (raw or
    normalized) workbook. Returns a ConsolidateResult."""
    return ctc.run_files_compare(
        _SCHEMA, tsmis_path, tsn_path, out_path,
        banner="Ramp Detail Comparison — TSMIS vs TSN", has_route=True,
        loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode)

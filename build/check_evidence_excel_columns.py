"""Golden check for the M2-D fix (v0.32.0): Excel-side evidence resolves the
compared column through the COMPARATOR'S OWN column resolution.

The compared field names are the COMPARISON's shared labels while the
consolidated workbook carries the SITE's labels, so the old exact-label lookup
silently dropped whole columns' Excel-side evidence (Intersection Detail: 26 of
35) and — where the export's labels sit shifted against their values (Ramp
Detail) — could box a NEIGHBOURING blank cell. Each evidence adapter now
exposes `excel_column_for(field, excel_header)`, delegating to the loader's
own exact-header gate + value-position table, so evidence and comparison can
never resolve a column differently. Locks:

  * hook == loader: every mapped position equals the comparator's own table;
  * the gate: a junk/relabelled header refuses EVERY field (None);
  * derived/context columns refuse (no single workbook cell);
  * the RD label-shift: City Code/R/U/Description resolve to the VALUE
    positions, one LEFT of their labels;
  * the seam: _tsmis_excel_side prefers the hook, keeps the exact-label
    default for adapters without one, and refuses honestly on hook-None.

The per-family REAL-corpus projection round-trip (each mapped cell's projected
value equals the loader's) ran against the 7.9/7.17 ground-truth consolidated
workbooks on 2026-07-23 — 0 mismatches over 26,320 sampled cells; Highway
Detail's real leg stays vendor-blocked (⛔ HD pre-release).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_evidence_excel_columns.py
"""
from _checklib import Checker, scripts_path

scripts_path()

import compare_highway_detail_tsn as cht
import compare_highway_sequence_tsn as chsl
import compare_intersection_detail_tsn as idt
import compare_ramp_detail_tsn as rd
import evidence_highway_detail as ehd
import evidence_highway_log as ehl
import evidence_highway_sequence as ehs
import evidence_intersection_detail as eid
import evidence_ramp_detail as erd
import highway_log_columns as hlc
import visual_evidence

c = Checker()

JUNK = ["Route", "Bogus", "Header"]


def test_intersection_detail():
    print("Intersection Detail: positions from idt._TSMIS_POS under idt._header_ok:")
    for header in (idt._TSMIS_HEADER, idt._TSMIS_HEADER_LEGACY):
        ok = all(eid.excel_column_for(f, header) == idt._TSMIS_POS[f]
                 for f in idt._TSMIS_POS)
        c.check(f"every mapped field == the loader's position ({header[1]!r} edition)",
                ok)
    c.check("the shared labels the old exact-label lookup dropped now resolve",
            eid.excel_column_for("PM", idt._TSMIS_HEADER) == 2
            and eid.excel_column_for("PR", idt._TSMIS_HEADER) == 1
            and eid.excel_column_for("HG", idt._TSMIS_HEADER) == 6)
    c.check("Location-derived fields refuse (no single workbook cell)",
            all(eid.excel_column_for(f, idt._TSMIS_HEADER) is None
                for f in ("Route Suffix", "District", "County")))
    c.check("a junk header refuses every field (the loader's own gate)",
            all(eid.excel_column_for(f, JUNK) is None for f in idt._TSMIS_POS))


def test_ramp_detail():
    print("Ramp Detail: the label-shifted export resolves by VALUE position:")
    hdr = rd._TSMIS_HEADER
    c.check("hook == the loader's own position table",
            all(erd.excel_column_for(f, hdr) == rd._TSMIS_POS[f]
                for f in ("PR", "PM", "Date of Record", "HG", "Area 4",
                          "City Code", "R/U", "Description")))
    c.check("City Code/R/U/Description sit one LEFT of their labels "
            "(the neighbouring-cell hazard)",
            erd.excel_column_for("City Code", hdr) == 8 == hdr.index("City Code") - 1
            and erd.excel_column_for("R/U", hdr) == 9 == hdr.index("R/U") - 1
            and erd.excel_column_for("Description", hdr) == 10
            == hdr.index("Description") - 1)
    c.check("District resolves to the Location cell the loader derives it from",
            erd.excel_column_for("District", hdr) == rd._TSMIS_POS["Location"])
    c.check("TSN-only context columns refuse",
            all(erd.excel_column_for(f, hdr) is None
                for f in ("Ramp Name", "On/Off", "Ramp Type", "ADT")))
    c.check("a junk header refuses every field",
            all(erd.excel_column_for(f, JUNK) is None for f in rd._TSMIS_POS))


def test_highway_detail():
    print("Highway Detail: PS + 'PM (raw)' live inside the Post Mile cell:")
    hdr = cht._TSMIS_HEADER
    c.check("hook == the loader's position table for the direct fields",
            all(ehd.excel_column_for(f, hdr) == cht._TSMIS_POS[f]
                for f in cht._TSMIS_POS))
    c.check("PS and PM (raw) both resolve to the Post Mile cell",
            ehd.excel_column_for("PS", hdr) == cht._TSMIS_POS["Post Mile"]
            == ehd.excel_column_for("PM (raw)", hdr))
    c.check("a junk header refuses every field",
            all(ehd.excel_column_for(f, JUNK) is None for f in cht._TSMIS_POS))


def test_highway_log_and_sequence():
    print("Highway Log + Highway Sequence: label positions under each loader's gate:")
    hl_hdr = ["Route"] + list(hlc.HEADER)
    c.check("HL fields resolve at their canonical positions",
            all(ehl.excel_column_for(f, hl_hdr) == 1 + hlc.HEADER.index(f)
                for f in hlc.HEADER))
    c.check("HL self 'Location (raw)' resolves to the Location cell",
            ehl.excel_column_for("Location (raw)", hl_hdr) == 1)
    c.check("an HL per-route header (no Route column) refuses",
            ehl.excel_column_for("City", list(hlc.HEADER)) is None)
    hsl_hdr = chsl._TSMIS_HEADER
    c.check("HSL fields resolve at the loader's named positions",
            all(ehs.excel_column_for(f, hsl_hdr) == p for f, p in
                (("County", 1), ("PM", 4), ("City", 2), ("HG", 6), ("FT", 7),
                 ("Distance To Next Point", 8), ("Description", 9))))
    c.check("HSL self 'PM Suffix' resolves to the UNLABELLED suffix cell",
            ehs.excel_column_for("PM Suffix", hsl_hdr) == chsl._TSMIS["suffix"]
            and hsl_hdr[chsl._TSMIS["suffix"]] == "")
    c.check("HSL junk header refuses",
            ehs.excel_column_for("PM", JUNK) is None)


class _HookAdapter:
    KEY_LABEL = "K"

    @staticmethod
    def project(_field, raw):
        return "" if raw is None else str(raw).strip()

    @staticmethod
    def excel_column_for(field, _header):
        return {"F": 2, "K": 1}.get(field)


class _PlainAdapter:
    KEY_LABEL = "K"

    @staticmethod
    def project(_field, raw):
        return "" if raw is None else str(raw).strip()


def test_seam():
    print("_tsmis_excel_side prefers the hook; default + refusal stay honest:")
    rows = {0: ("Data", 2, ["r1", "kv", "fv"])}
    header = ["Route", "K", "SiteLabel"]
    ex = {"row_index": 0, "va": "fv"}
    img, label, addr, reason = visual_evidence._tsmis_excel_side(
        _HookAdapter, ex, "F", rows, header, "book.xlsx")
    c.check("hook resolution renders from the mapped cell",
            reason is None and addr == "Data!C2", f"addr={addr} reason={reason}")
    img, label, addr, reason = visual_evidence._tsmis_excel_side(
        _HookAdapter, ex, "Unknown", rows, header, "book.xlsx")
    c.check("hook None is the honest refusal",
            img is None and "no single cell" in reason, f"reason={reason}")
    img, label, addr, reason = visual_evidence._tsmis_excel_side(
        _PlainAdapter, ex, "SiteLabel", rows, header, "book.xlsx")
    c.check("an adapter without the hook keeps the exact-label default",
            reason is None and addr == "Data!C2", f"addr={addr} reason={reason}")
    img, label, addr, reason = visual_evidence._tsmis_excel_side(
        _PlainAdapter, ex, "F", rows, header, "book.xlsx")
    c.check("exact-label miss keeps the old refusal wording",
            img is None and reason == "the compared column is not in the workbook header",
            f"reason={reason}")


if __name__ == "__main__":
    print("M2-D: the comparator-owned Excel evidence column resolution:")
    test_intersection_detail()
    test_ramp_detail()
    test_highway_detail()
    test_highway_log_and_sequence()
    test_seam()
    raise SystemExit(c.summary())

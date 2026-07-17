"""Golden check for the cross-environment RAMP DETAIL PM re-key
(scripts/compare_env.RAMP_DETAIL + compare_core).

Locks the headline finding of the 2026-06-16 ramp-comparison audit. Ramp Detail's
first column (a district-county-route Location / County) is COARSE — it repeats
for every ramp on a route — so the original "key on the first column" behavior
aligned rows POSITIONALLY within the route. One ramp inserted mid-route then
mis-paired every row after it, cascading into spurious field diffs: the real
delivered PROD-vs-TEST workbook reported 1,451 differing cells, ~99.4% of them
positional inflation; the TRUE difference was 8 cells / 4 rows + 10 one-sided
ramps. v0.11.0 set CompareSchema.key_field to the granular postmile ("PM") column
(compare_env.RAMP_DETAIL.key_col="PM"), collapsing the cascade to the truth.

check_compare_keyfield.py locks the generic key_field MECHANISM with a toy schema;
this check locks the REAL Ramp Detail adapter wiring end to end — that
RAMP_DETAIL keys on "PM", that the loader reads per-route "TSAR - Ramp Detail"
sheets, and that a mid-route insert produces ONE one-sided ramp with zero
spurious diffs through the actual compare_folders path.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_ramp_detail.py
"""
import os
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_env
from compare_core import _DIFF_MARK, count_diffs, keys_for, union_keys
from events import Events
from openpyxl import Workbook, load_workbook

# A miniature Ramp Detail route: County is the COARSE first column (identical on
# every ramp of the route); PM is the granular postmile that actually identifies
# a ramp. Side B inserts ONE new ramp (PM 2.500) in the middle and changes
# nothing else.
ROUTE = "001"
HEADER = ["County", "PM", "Ramp ID", "Lighting"]
DATA_A = [
    ["LA", "1.000", "ON-A", "Yes"],
    ["LA", "2.000", "OFF-B", "No"],
    ["LA", "3.000", "ON-C", "Yes"],
    ["LA", "4.000", "OFF-D", "No"],
]
DATA_B = [
    ["LA", "1.000", "ON-A", "Yes"],
    ["LA", "2.000", "OFF-B", "No"],
    ["LA", "2.500", "ON-NEW", "Yes"],          # inserted mid-route
    ["LA", "3.000", "ON-C", "Yes"],
    ["LA", "4.000", "OFF-D", "No"],
]
# Consolidated shape the engine compares: [route, *per-route columns].
ROWS_A = [[ROUTE] + r for r in DATA_A]
ROWS_B = [[ROUTE] + r for r in DATA_B]


def test_config_is_pm_keyed():
    """The audit-validated wiring: Ramp Detail keys on PM and reads the per-route
    'TSAR - Ramp Detail' sheets. A revert here is exactly the regression that
    re-inflated the diff count, so pin it explicitly."""
    rd = compare_env.RAMP_DETAIL
    assert rd.key_col == "PM", ("Ramp Detail must key on PM", rd.key_col)
    assert rd.sheet_name == "TSAR - Ramp Detail", rd.sheet_name
    assert rd.subdir == "ramp_detail", rd.subdir


def test_pm_key_collapses_coarse_cascade():
    """Through the REAL schema the adapter builds: coarse (first-column) keying
    cascades the single insert into spurious diffs; PM keying isolates it."""
    sc_pm = compare_env.RAMP_DETAIL._schema(HEADER, "SSOR-PROD", "SSOR-TEST")
    assert sc_pm.key_field == HEADER.index("PM"), \
        ("the adapter must resolve PM to its header index", sc_pm.key_field)
    sc_coarse = replace(sc_pm, key_field=0)

    def counts(sc, kf):
        kt = keys_for(ROWS_A, True, kf)
        kn = keys_for(ROWS_B, True, kf)
        return count_diffs(sc, ROWS_A, ROWS_B, kt, kn, union_keys(kt, kn), True)

    # Coarse County key: occ-3 and occ-4 mis-pair, the inserted ramp falls out
    # as occ-5 — 5 spurious differing cells across 2 rows + 1 one-sided.
    coarse = counts(sc_coarse, 0)
    assert coarse["both"] == 4 and coarse["n_only"] == 1, coarse
    assert coarse["diff_cells"] == 5 and coarse["diff_rows"] == 2, \
        ("coarse first-column key must cascade the mid-route insert", coarse)

    # PM key: the matched postmiles are identical, the one new postmile is
    # correctly one-sided — ZERO spurious diffs.
    pm = counts(sc_pm, sc_pm.key_field)
    assert pm["both"] == 4 and pm["t_only"] == 0 and pm["n_only"] == 1, pm
    assert pm["diff_cells"] == 0 and pm["diff_rows"] == 0, \
        ("PM key must isolate the insert to one one-sided ramp", pm)


def _write_route_file(path, sheet, header, data):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for row in data:
        ws.append(row)
    wb.save(path)
    wb.close()


def test_end_to_end_values_workbook():
    """Drive the actual compare_folders path over real per-route XLSX files and
    read the written VALUES workbook back: the mid-route insert must surface as
    exactly one one-sided ramp with zero differing cells."""
    root = Path(tempfile.mkdtemp())
    try:
        sheet = compare_env.RAMP_DETAIL.sheet_name
        a = root / "2026-06-16 ssor-prod" / "ramp_detail"
        b = root / "2026-06-16 ssor-test" / "ramp_detail"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        _write_route_file(a / f"ramp_detail_route_{ROUTE}.xlsx", sheet, HEADER, DATA_A)
        _write_route_file(b / f"ramp_detail_route_{ROUTE}.xlsx", sheet, HEADER, DATA_B)

        out = root / "cmp.xlsx"
        res = compare_env.RAMP_DETAIL.compare_folders(
            a.parent, b.parent, out, events=Events(),
            confirm_overwrite=lambda _p: True, mode="values")
        assert res.status == "ok", (res.status, res.message)
        assert res.verdict == "diff", res.verdict
        assert "DIFFERENCES FOUND" in res.summary_lines[0], res.summary_lines[0]

        wb = load_workbook(out, read_only=True, data_only=True)
        body = list(wb["Comparison"].iter_rows(values_only=True))[1:]
        wb.close()
        # has_route layout: A=Route B=PM C=# D=A Row E=B Row F=Status G=Diffs H..
        statuses = [r[5] for r in body]
        one_sided = [s for s in statuses if s and s != "Both"]
        assert len(body) == 5, ("union = 4 matched + 1 inserted", len(body))
        assert statuses.count("Both") == 4, statuses
        assert len(one_sided) == 1 and one_sided[0].endswith("only"), one_sided
        neq = sum(1 for r in body for v in r
                  if isinstance(v, str) and _DIFF_MARK in v)
        assert neq == 0, ("PM keying must leave zero differing cells", neq)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_missing_key_column_fails_closed():
    """CMP-AUD-028: a CONFIGURED identity column is mandatory. It used to log and
    fall back to column 0, so two malformed key-less workbooks paired on their
    first column and returned a clean MATCH. Every keyed adapter now refuses a
    header that lacks its key column (case/whitespace-tolerant when present); an
    unkeyed adapter still uses column 0; and the Ramp Detail end-to-end returns a
    fail-closed error instead of a false match."""
    # (a) Unit contract for every keyed adapter.
    keyed = [("RAMP_DETAIL", compare_env.RAMP_DETAIL, "PM"),
             ("HIGHWAY_SEQUENCE", compare_env.HIGHWAY_SEQUENCE, "PM"),
             ("INTERSECTION_DETAIL", compare_env.INTERSECTION_DETAIL, "Post Mile"),
             ("HIGHWAY_DETAIL", compare_env.HIGHWAY_DETAIL, "Post Mile")]
    for name, adapter, key in keyed:
        assert adapter.key_col == key, (name, adapter.key_col)
        assert adapter._resolve_key_field(["County", key, "Desc"]) == 1, (name, "present")
        # case/whitespace tolerant when present
        assert adapter._resolve_key_field(["County", f"  {key.upper()} ", "X"]) == 1, \
            (name, "case/whitespace")
        # absent -> fail-closed raise (was a silent return 0)
        try:
            adapter._resolve_key_field(["County", "Desc"])
            assert False, (name, "a missing configured key column must raise")
        except ValueError as e:
            assert key in str(e) and adapter.REPORT_NAME in str(e), (name, str(e))
    # An unkeyed adapter (key_col=None) legitimately uses the first column.
    assert compare_env.HIGHWAY_LOG.key_col is None, compare_env.HIGHWAY_LOG.key_col
    assert compare_env.HIGHWAY_LOG._resolve_key_field(["A", "B", "C"]) == 0

    # (b) End-to-end: two IDENTICAL malformed Ramp Detail folders whose header
    #     lacks PM must fail closed (an error), never a clean match.
    bad_header = [h for h in HEADER if h != "PM"]          # County, Ramp ID, Lighting
    bad_data = [[r[0]] + r[2:] for r in DATA_A]            # drop the PM cell
    root = Path(tempfile.mkdtemp())
    try:
        sheet = compare_env.RAMP_DETAIL.sheet_name
        a = root / "2026-06-16 ssor-prod" / "ramp_detail"
        b = root / "2026-06-16 ssor-test" / "ramp_detail"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        _write_route_file(a / f"ramp_detail_route_{ROUTE}.xlsx", sheet, bad_header, bad_data)
        _write_route_file(b / f"ramp_detail_route_{ROUTE}.xlsx", sheet, bad_header, bad_data)
        out = root / "cmp.xlsx"
        res = compare_env.RAMP_DETAIL.compare_folders(
            a.parent, b.parent, out, events=Events(),
            confirm_overwrite=lambda _p: True, mode="values")
        assert res.status == "error", ("must fail closed, not match", res.status)
        assert "PM" in (res.message or ""), ("names the missing key column", res.message)
        assert not out.exists(), "no workbook may be written on a fail-closed layout"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    test_config_is_pm_keyed()
    test_pm_key_collapses_coarse_cascade()
    test_end_to_end_values_workbook()
    test_missing_key_column_fails_closed()
    print("OK  COMPARE-RAMP-DETAIL-PM-KEY: Ramp Detail keys on PM; a mid-route "
          "ramp insert that cascades into 5 spurious diff cells under coarse "
          "keying collapses to ONE one-sided ramp / zero diff cells under PM "
          "keying, end to end through compare_folders.")


if __name__ == "__main__":
    main()

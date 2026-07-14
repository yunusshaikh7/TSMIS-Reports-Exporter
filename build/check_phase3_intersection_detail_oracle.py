"""Focused synthetic checks for the independent CORE-ID-78 oracle adapter.

No production report module is imported.  Synthetic workbooks prove the exact
35/36-column stream contracts and the position-authoritative TSMIS mapping; pure
adapted rows prove duplicate/tie preservation; a fake 217+1 tree exercises the
versioned selector/manifest and pre/post mutation gate.
"""
from __future__ import annotations

import ast
from decimal import Decimal
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from openpyxl import Workbook

import phase3_intersection_detail_oracle as adapter
from phase3_xlsx_stream import XlsxSchemaError


FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        FAILURES.append(name)


def expect_raises(name, exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        check(name, True, str(exc))
    except Exception as exc:
        check(name, False,
              f"raised {type(exc).__name__}, expected {exc_type.__name__}: {exc}")
    else:
        check(name, False, f"did not raise {exc_type.__name__}")


def write_xlsx(path, sheet_name, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    wb.save(path)
    wb.close()


def tsmis_row(*, description="JCT A", pm=" 000.204", location="12 ORA 210U"):
    """One current 35-cell row with sentinel values at physical positions."""
    row = [None] * len(adapter.TSMIS_HEADERS)
    row[0] = "R"                       # P -> PR
    row[1] = pm
    row[2] = "SOURCE-S-COLUMN"         # not projected as Route Suffix
    row[3] = location
    row[4] = "73-10-19"
    row[5:8] = ["D", "DAPT", "U"]
    # Shifted label/value pairs: physical INT Type / Ctrl T / Light Eff-Date
    # contain dates; each following physical cell contains the code.
    row[8], row[9] = "73-03-16", "T"
    row[10], row[11] = "73-04-17", "P"
    row[12], row[13] = "73-05-18", 1
    row[14] = "73-06-19"
    row[15:20] = [1, "N", 0, "P", 3]
    row[20], row[21] = description, "0100"
    row[22] = "73-07-20"
    row[23:28] = [1, "N", 0, "P", 2]
    row[28] = "73-08-21"
    row[29] = "SOURCE-INTRTE-S"
    row[30:35] = ["005", "R", "009.560", "L", "0250"]
    return row


def tsn_row(*, description="JCT A", pm=" 000.204", location="12 ORA 210U"):
    row = {header: None for header in adapter.TSN_HEADERS}
    row.update({
        "PP": "R", "POST_MILE": pm, "LOCATION": location,
        "DATE_REC": "73-10-19", "HG": "D", "CITY_CODE": "DAPT", "RU": "U",
        "EFF_DATE_INT": "73-03-16", "TY_INT": "T",
        "EFF_DATE_CT": "73-04-17", "TY_CT": "J",
        "EFF_DATE_LT": "73-05-18", "LT_TY": "Y",
        "EFF_DATE_ML": "73-06-19", "MAIN_SM": "Y", "MAIN_LC": "N",
        "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
        # Empirically corrected positions: XLL precedes the three TSN-only/main
        # fields, then Description/Main Override/Cross Begin.
        "X_CROSS_OVERRIDE": "0250", "MAIN_EFF_DATE": "73-06-20",
        "MAIN_ADT": 12345, "DESCRIPTION": description, "MAIN_OVERRIDE": "0100",
        "CROSS_BEGIN_DATE": "73-07-20", "CS_SM": "Y", "CS_LC": "N",
        "CS_RC": "N", "CS_TF": "P", "CS_NL": 2,
        "EFF_DATE": "73-08-21", "CROSS_ADT": 6789,
        "CROSS_ROUTE_NAME": "005", "CROSS_PM_PREFIX": "R",
        "CROSS_POSTMILE": "009.560", "CROSS_PM_SUFFIX": "L",
    })
    return [row[header] for header in adapter.TSN_HEADERS]


def by_field(row):
    return dict(zip(adapter.ASSERTED_FIELDS, row.values))


def test_exact_stream_and_projection(root):
    print("exact schemas + independent position projection:")
    tsmis = root / "intersection_detail_route_210U.xlsx"
    tsn = root / "tsn.xlsx"
    write_xlsx(tsmis, adapter.TSMIS_SHEET, adapter.TSMIS_HEADERS, [tsmis_row()])
    write_xlsx(tsn, adapter.TSN_SHEET, adapter.TSN_HEADERS, [tsn_row()])

    left = adapter.read_tsmis_workbook(tsmis)
    right = adapter.read_tsn_workbook(tsn)
    check("TSMIS stream produces one OracleRow", len(left.rows) == 1)
    check("TSN stream produces one OracleRow", len(right.rows) == 1)
    check("matching member/Location route emits no provenance diagnostic",
          left.route_diagnostics == ())
    la, rb = left.rows[0], right.rows[0]
    lv, rv = by_field(la), by_field(rb)

    check("OracleSchema key is structured Route + PM",
          tuple(rule.name for rule in adapter.ORACLE_SCHEMA.key_rules)
          == ("Route", "PM") and la.key == ("210", "0.204"), repr(la.key))
    check("PM is excluded from 32 asserting fields (not double-counted)",
          len(adapter.SHARED_HEADER) == 33
          and len(adapter.ASSERTED_FIELDS) == len(la.values) == 32
          and "PM" not in adapter.ASSERTED_FIELDS
          and all(rule.asserting for rule in adapter.ORACLE_SCHEMA.field_rules))
    check("Route Suffix derives from Location, never physical S label",
          lv["Route Suffix"] == "U" and lv["Route Suffix"] != "SOURCE-S-COLUMN")
    check("shifted INT label maps physical date then following type",
          lv["INT Type Eff-Date"] == "1973-03-16" and lv["INT Type"] == "T",
          repr((lv["INT Type Eff-Date"], lv["INT Type"])))
    check("shifted Control label maps physical date then J-P crosswalk",
          lv["Control Type Eff-Date"] == "1973-04-17"
          and lv["Control Type"] == "S",
          repr((lv["Control Type Eff-Date"], lv["Control Type"])))
    check("physical Boolean value 1 normalizes independently to Y",
          lv["Lighting"] == "Y" and lv["ML Mastarm"] == "Y")
    check("all seven position-authoritative TSMIS dates normalize",
          [lv[name] for name in (
              "Date of Record", "INT Type Eff-Date", "Control Type Eff-Date",
              "Lighting Eff-Date", "ML Eff-Date", "CS Eff-Date",
              "Int St Eff-Date",
          )] == [
              "1973-10-19", "1973-03-16", "1973-04-17", "1973-05-18",
              "1973-06-19", "1973-07-20", "1973-08-21",
          ])
    check("numeric projections are Decimal-safe and zero-pad independent",
          (lv["Main Line Length"], lv["Intrte Route"],
           lv["Intrte Postmile"], lv["Xing Line Lgth"])
          == ("100", "5", "9.56", "250"))
    check("PM key rule preserves trailing fractional zeros and negative zero",
          adapter.normalize_pm("000.5000") == "0.5000"
          and adapter.normalize_pm("-000.000") == "-0.000"
          and adapter.normalize_pm("-0") == "-0")
    check("PM key rule accepts leading-dot but leaves explicit plus raw",
          adapter.normalize_pm(".5") == "0.5"
          and adapter.normalize_pm("+06") == "+06")
    check("compared numeric rule is narrower than PM and preserves -0",
          adapter.normalize_numeric_field("0006.5000") == "6.5"
          and adapter.normalize_numeric_field("+06") == "+06"
          and adapter.normalize_numeric_field(".5") == ".5"
          and adapter.normalize_numeric_field("-000.000") == "-0")

    check("TSN exact corrected XLL position projects X_CROSS_OVERRIDE",
          rv["Xing Line Lgth"] == "250", repr(rv["Xing Line Lgth"]))
    check("TSN exact corrected Description/Main Override positions project",
          rv["Description"] == "JCT A" and rv["Main Line Length"] == "100")
    check("TSN-only ADT/MAIN_EFF fields do not enter asserted values",
          "MAIN_ADT" not in adapter.ASSERTED_FIELDS
          and "CROSS_ADT" not in adapter.ASSERTED_FIELDS
          and "MAIN_EFF_DATE" not in adapter.ASSERTED_FIELDS)
    check("both independently projected rows agree on the structured key",
          la.key == rb.key == ("210", "0.204"))


def test_excel_numeric_scalar_semantics():
    print("\nExcel binary64 numeric scalar seam:")
    artifact = Decimal("0.92100000000000004")
    text_artifact = "0.92100000000000004"
    check("numeric OOXML binary artifact uses shortest binary64 spelling",
          adapter.normalize_numeric_field(artifact) == "0.921")
    check("numeric-looking text retains exact lexical semantics",
          adapter.normalize_numeric_field(text_artifact) == text_artifact
          and adapter.normalize_pm(text_artifact) == text_artifact)
    check("PM applies the same typed numeric-cell seam",
          adapter.normalize_pm(artifact) == "0.921")

    real_difference = Decimal("0.921000000000001")
    check("nearby real 15-digit difference remains distinct",
          adapter.normalize_numeric_field(real_difference)
          == "0.921000000000001"
          and adapter.normalize_pm(real_difference) == "0.921000000000001"
          and adapter.normalize_numeric_field(real_difference)
          != adapter.normalize_numeric_field(artifact))
    check("15-digit integer boundary ignores float repr's type-only .0",
          adapter.normalize_numeric_field(Decimal("123456789012345"))
          == "123456789012345")
    check("leading fractional zeros do not consume significant-digit budget",
          adapter.normalize_numeric_field(
              Decimal("0.00000123456789012345"))
          == "1.23456789012345e-06")

    left_values = tsmis_row(pm="0.921")
    left_values[32] = "0.921"
    right_values = tsn_row(pm=artifact)
    right_values[adapter.TSN_HEADERS.index("CROSS_POSTMILE")] = artifact
    left = adapter.adapt_tsmis_values(left_values, source_index=0)
    right = adapter.adapt_tsn_values(right_values, source_index=0)
    check("typed seam is used by both PM key and report-field projection",
          left.key == right.key == ("210", "0.921")
          and by_field(left)["Intrte Postmile"]
          == by_field(right)["Intrte Postmile"] == "0.921")

    expect_raises(
        "nearby value needing 16 significant digits is refused",
        adapter.IntersectionOracleError,
        lambda: adapter.normalize_numeric_field(
            Decimal("0.9210000000000001")),
    )
    expect_raises(
        "generic greater-than-15-significant value is refused",
        adapter.IntersectionOracleError,
        lambda: adapter.normalize_pm(Decimal("1234567890123456")),
    )
    expect_raises(
        "binary64 overflow is refused",
        adapter.IntersectionOracleError,
        lambda: adapter.normalize_numeric_field(Decimal("1e400")),
    )
    expect_raises(
        "binary64 underflow is refused",
        adapter.IntersectionOracleError,
        lambda: adapter.normalize_numeric_field(Decimal("1e-400")),
    )
    expect_raises(
        "non-finite Decimal is refused before conversion",
        adapter.IntersectionOracleError,
        lambda: adapter.normalize_numeric_field(Decimal("NaN")),
    )


def test_cross_route_provenance(root):
    print("\ncross-route row retention + provenance diagnostics:")
    cross = root / "intersection_detail_route_009.xlsx"
    write_xlsx(
        cross,
        adapter.TSMIS_SHEET,
        adapter.TSMIS_HEADERS,
        [tsmis_row(description="JCT 9-RIVER ST", location="05 SCR 001")],
    )

    adapted = adapter.read_tsmis_workbook(cross)
    check("cross-route row is retained instead of rejected",
          len(adapted.rows) == 1)
    row = adapted.rows[0]
    check("retained row key derives Route from Location, not member name",
          row.key == ("001", "0.204"), repr(row.key))
    check("retained cross-route row preserves asserted values",
          by_field(row)["Description"] == "JCT 9-RIVER ST")
    check("cross-route mismatch emits one frozen structured diagnostic",
          len(adapted.route_diagnostics) == 1
          and adapter.RouteProvenanceDiagnostic.__dataclass_params__.frozen)
    diagnostic = adapted.route_diagnostics[0]
    check("diagnostic pins member token, derived token, and exact source row",
          diagnostic.member_token == "009"
          and diagnostic.derived_token == "001"
          and diagnostic.source_ref.endswith(
              "intersection_detail_route_009.xlsx#row=2"),
          repr(diagnostic))

    pure = adapter.diagnose_tsmis_route(
        tsmis_row(description="JCT 9-RIVER ST", location="05 SCR 001"),
        member_token="009",
        source_ref="synthetic#row=2",
    )
    check("optional pure validation reports the same mismatch",
          pure == adapter.RouteProvenanceDiagnostic(
              member_token="009",
              derived_token="001",
              source_ref="synthetic#row=2",
          ), repr(pure))

    original = adapter.diagnose_tsmis_route
    reader_error = None
    reread = None
    try:
        def forbidden_optional_validation(*_args, **_kwargs):
            raise AssertionError("reader called optional validation API")

        adapter.diagnose_tsmis_route = forbidden_optional_validation
        reread = adapter.read_tsmis_workbook(cross)
    except Exception as exc:
        reader_error = exc
    finally:
        adapter.diagnose_tsmis_route = original
    check("actual reader is behaviorally independent of optional validation API",
          reader_error is None
          and reread is not None
          and len(reread.rows) == 1
          and reread.route_diagnostics == adapted.route_diagnostics,
          repr(reader_error))

    normal = root / "intersection_detail_route_210U.xlsx"
    combined = adapter.read_tsmis_workbooks((normal, cross))
    check("multi-workbook adapter aggregates every route diagnostic",
          len(combined.rows) == 2
          and combined.route_diagnostics == adapted.route_diagnostics,
          repr(combined.route_diagnostics))


def test_schema_refusal(root):
    print("\nfail-closed schema refusal:")
    legacy = root / "intersection_detail_route_001.xlsx"
    legacy_headers = adapter.TSMIS_HEADERS + ("Legacy duplicate column",)
    write_xlsx(legacy, adapter.TSMIS_SHEET, legacy_headers,
               [tsmis_row(location="12 ORA 001") + ["unexpected"]])
    expect_raises("pre-July/extra-width TSMIS schema is refused",
                  XlsxSchemaError,
                  lambda: adapter.read_tsmis_workbook(legacy))

    wrong_tsn = root / "wrong-tsn.xlsx"
    headers = list(adapter.TSN_HEADERS)
    a = headers.index("X_CROSS_OVERRIDE")
    b = headers.index("MAIN_EFF_DATE")
    headers[a], headers[b] = headers[b], headers[a]
    write_xlsx(wrong_tsn, adapter.TSN_SHEET, headers, [tsn_row(location="12 ORA 001")])
    expect_raises("wrong-order TSN schema is refused even with all names present",
                  XlsxSchemaError,
                  lambda: adapter.read_tsn_workbook(wrong_tsn))


def test_duplicate_and_tie_preservation():
    print("\nduplicate assignment + tie preservation:")
    a0 = adapter.adapt_tsmis_values(
        tsmis_row(description="ALPHA"), source_index=0)
    a1 = adapter.adapt_tsmis_values(
        tsmis_row(description="BETA"), source_index=1)
    b0 = adapter.adapt_tsn_values(tsn_row(description="BETA"), source_index=0)
    b1 = adapter.adapt_tsn_values(tsn_row(description="ALPHA"), source_index=1)
    left = adapter.AdaptedSide((a0, a1), (), 2)
    right = adapter.AdaptedSide((b0, b1), (), 2)
    outcome = adapter.compare_adapted(left, right)
    trace = outcome.pairing_trace[0]
    check("same Route+PM duplicates are retained, not deduplicated",
          outcome.counts.paired_rows == 2 and len(outcome.row_results) == 2)
    check("crossed duplicates pair by exact minimum cost",
          trace.source_pairs == ((0, 1), (1, 0)) and trace.total_cost == 0,
          repr(trace))
    check("every paired row asserts exactly 32 fields",
          outcome.counts.asserted_cells == 64
          and outcome.counts.context_cells == 0,
          repr(outcome.counts))

    ta0 = adapter.adapt_tsmis_values(
        tsmis_row(description="TIE"), source_index=10)
    ta1 = adapter.adapt_tsmis_values(
        tsmis_row(description="TIE"), source_index=11)
    tb0 = adapter.adapt_tsn_values(tsn_row(description="TIE"), source_index=20)
    tb1 = adapter.adapt_tsn_values(tsn_row(description="TIE"), source_index=21)
    tied = adapter.compare_adapted(
        adapter.AdaptedSide((ta0, ta1), (), 12),
        adapter.AdaptedSide((tb0, tb1), (), 22),
    )
    check("equal-cost duplicate tie preserves lexicographic source order",
          tied.pairing_trace[0].source_pairs == ((10, 20), (11, 21)),
          repr(tied.pairing_trace[0]))


def make_fake_corpus(root):
    tsmis = (root / "ground-truth" / "Intersection Detail Bundle 7.8"
             / "intersection_detail")
    tsn = (root / "ground-truth" / "All Reports 6.19" / "TSN"
           / "Intersection Detail")
    tsmis.mkdir(parents=True)
    tsn.mkdir(parents=True)
    suffixes = {8: "U", 10: "S", 14: "U", 58: "U", 178: "S", 210: "U"}
    tokens = [f"{route:03d}{suffixes.get(route, '')}"
              for route in range(1, 219) if route != 170]
    for token in tokens:
        (tsmis / f"intersection_detail_route_{token}.xlsx").write_bytes(
            f"synthetic-{token}\n".encode("ascii"))
    (tsn / "TSAR - INTERSECTION DETAIL_TSN.xlsx").write_bytes(b"synthetic-tsn\n")
    return tsmis, tsn


def test_manifest_binding(root):
    print("\nstrict 217+1 selector + manifest binding:")
    tsmis, _tsn = make_fake_corpus(root)
    selection = adapter.select_corpus(root)
    check("selector resolves exactly 217 TSMIS + one exact TSN",
          len(selection.tsmis_files) == 217
          and selection.tsn_file.name == "TSAR - INTERSECTION DETAIL_TSN.xlsx")
    binding = adapter.capture_pre_binding(root)
    post = adapter.verify_post_binding(binding)
    check("versioned manifest has 218 ordinal records and stable pre/post digest",
          len(binding.pre_manifest.records) == 218
          and binding.pre_manifest.serialized.startswith(
              (adapter.MANIFEST_HEADER + "\n").encode("utf-8"))
          and post.sha256 == binding.pre_manifest.sha256)
    check("manifest pins the exact role/alias vocabulary",
          {record.role for record in post.records}
          == {adapter.TSMIS_ROLE, adapter.TSN_ROLE}
          and {record.root_alias for record in post.records}
          == {adapter.ID78_ALIAS, adapter.ALL619_ALIAS})

    first = tsmis / "intersection_detail_route_001.xlsx"
    first.write_bytes(first.read_bytes() + b"mutation")
    expect_raises("post-binding content mutation is rejected",
                  adapter.CorpusMutationError,
                  lambda: adapter.verify_post_binding(binding))
    unexpected = tsmis / "~$owner-lock.xlsx"
    unexpected.write_bytes(b"lock")
    expect_raises("unexpected/owner-lock direct member is refused",
                  adapter.CorpusSelectionError,
                  lambda: adapter.select_corpus(root))


def test_no_production_imports():
    print("\nindependence boundary:")
    source_path = Path(adapter.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = [name for name in imported
                 if (name.startswith("scripts") or name.startswith("compare_")
                     or name in ("intersection_detail_columns", "openpyxl"))]
    local = [name for name in imported if name.startswith("phase3_")]
    check("static imports contain no production/openpyxl report dependency",
          not forbidden, repr(forbidden))
    check("the only local runtime dependencies are the two approved helpers",
          set(local) == {"phase3_xlsx_stream", "phase3_independent_oracle"},
          repr(local))

    code = (
        "import sys; "
        f"sys.path.insert(0, {str(source_path.parent)!r}); "
        "import phase3_intersection_detail_oracle; "
        "bad=sorted(n for n in sys.modules if n=='openpyxl' or "
        "n.startswith('compare_') or n.startswith('scripts.') or "
        "n=='intersection_detail_columns'); "
        "print(repr(bad)); raise SystemExit(bool(bad))"
    )
    run = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        cwd=source_path.parent.parent, env=os.environ.copy(), check=False,
    )
    check("fresh-process adapter import loads no production/openpyxl module",
          run.returncode == 0 and run.stdout.strip() == "[]",
          f"rc={run.returncode}; out={run.stdout!r}; err={run.stderr!r}")


def main():
    root = Path(tempfile.mkdtemp(prefix="phase3_id_oracle_"))
    try:
        workbook_root = root / "workbooks"
        workbook_root.mkdir()
        test_exact_stream_and_projection(workbook_root)
        test_excel_numeric_scalar_semantics()
        test_cross_route_provenance(workbook_root)
        test_schema_refusal(workbook_root)
        test_duplicate_and_tie_preservation()
        test_manifest_binding(root / "corpus")
        test_no_production_imports()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) FAILED")
        raise SystemExit(1)
    print("\nall independent Intersection Detail oracle checks passed")


if __name__ == "__main__":
    main()

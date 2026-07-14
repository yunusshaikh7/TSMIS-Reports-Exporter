"""Permanent synthetic contract checks for the Stage-6 Ramp conservation oracle."""
from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import phase6_ramp_detail_conservation as oracle
import phase3_xlsx_stream as stream


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "build" / "phase6_ramp_detail_conservation.py"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def rejects(error_type, fn, contains=None):
    try:
        fn()
    except error_type as exc:
        if contains is not None:
            check(contains.lower() in str(exc).lower(), f"wrong rejection: {exc}")
        return
    raise AssertionError(f"expected {error_type.__name__}")


def test_independence_and_exact_schemas():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    forbidden = {
        "openpyxl", "pandas", "numpy", "compare_core", "compare_tsn_common",
        "compare_ramp_detail_tsn", "tsn_library", "tsn_load_ramp_detail",
        "visual_evidence", "evidence", "matrix_build",
    }
    check(not imports.intersection(forbidden),
          f"oracle imports production/third-party modules: {imports.intersection(forbidden)}")
    check(len(oracle.RAW_HEADERS) == 18 and len(set(oracle.RAW_HEADERS)) == 18,
          "raw schema is not exact and unique")
    check(len(oracle.NORMALIZED_HEADERS) == 15
          and len(set(oracle.NORMALIZED_HEADERS)) == 15,
          "normalized schema is not exact and unique")
    check(tuple(oracle.FIELD_DISPOSITIONS) == oracle.RAW_HEADERS,
          "field disposition order/coverage differs from the raw schema")
    targets = {
        target for disposition in oracle.FIELD_DISPOSITIONS.values()
        for target in disposition["normalized_targets"]
    }
    check(targets <= set(oracle.NORMALIZED_HEADERS),
          "a disposition points at an undeclared normalized field")
    check(oracle.FIELD_DISPOSITIONS["PM_SFX"]["kind"] == "relational"
          and oracle.FIELD_DISPOSITIONS["PM_SFX"]["normalized_requirement"]
          == "retain_independent_typed_identity_claim",
          "PM_SFX identity loss is understated")
    check(oracle.FIELD_DISPOSITIONS["SEG_ORDER_ID"]["kind"] == "relational",
          "SEG_ORDER_ID is not classified as an order relation")
    for field in ("ADT_EFF_YEAR", "EFF_DATE"):
        check(oracle.FIELD_DISPOSITIONS[field]["normalized_requirement"]
              == "retain_for_print_evidence_and_context",
              f"{field} print/evidence requirement is missing")


def test_typed_digests_and_order():
    text = [("1",), ("2",)]
    numeric = [(Decimal("1"),), ("2",)]
    check(oracle._ordered_digest(text) != oracle._ordered_digest(numeric),
          "typed digest folds Decimal and text")
    reversed_rows = list(reversed(text))
    check(oracle._ordered_digest(text) != oracle._ordered_digest(reversed_rows),
          "ordered digest ignores order")
    check(oracle._multiset_digest(text)[0] == oracle._multiset_digest(reversed_rows)[0],
          "multiset digest incorrectly depends on order")
    duplicated = [text[0], text[0]]
    check(oracle._multiset_digest(text)[0] != oracle._multiset_digest(duplicated)[0],
          "multiset digest ignores multiplicity")


def test_location_pm_date_and_description_contracts():
    district, county, route, info = oracle._parse_location("04-CC.-004")
    check((district, county, route) == ("04", "CC", "004")
          and info["county_had_trailing_period"],
          "location decomposition changed")
    rejects(oracle.ConservationError,
            lambda: oracle._parse_location("04 CC 004"), "location")
    check(oracle._norm_pm("009.600") == "9.600"
          and oracle._norm_pm("000.000") == "0.000",
          "Ramp PM canonicalization changed")
    rejects(oracle.ConservationError, lambda: oracle._norm_pm("+9.6"), "PM")
    check(oracle._iso_record_date(date(2026, 7, 12)) == "2026-07-12"
          and oracle._iso_record_date("29-01-02") == "2029-01-02"
          and oracle._iso_record_date("30-01-02") == "1930-01-02",
          "date window/canonicalization changed")
    rejects(oracle.ConservationError,
            lambda: oracle._iso_record_date("2026-02-30"), "invalid")
    check(oracle._normalize_description("505/NB ON") == "505/NB ON",
          "same-route raw Description prefix was destroyed")
    check(oracle._normalize_description("128/RUSSELL") == "128/RUSSELL",
          "different-route raw Description prefix was destroyed")
    check(oracle._normalize_description("  15/CENTRAL  ") == "15/CENTRAL",
          "authorized edge trimming changed")


def test_exact_fifteen_row_loss_manifest():
    rows = [[None] * len(oracle.NORMALIZED_HEADERS)
            for _ in range(max(item[0] for item in oracle.EXPECTED_DESCRIPTION_LOSSES) - 1)]
    expected = [list(row) for row in rows]
    route_i = oracle.NORMALIZED_HEADERS.index("Route")
    desc_i = oracle.NORMALIZED_HEADERS.index("Description")
    for source_row, route, conserved, current in oracle.EXPECTED_DESCRIPTION_LOSSES:
        ordinal = source_row - 1
        rows[ordinal - 1][route_i] = route
        rows[ordinal - 1][desc_i] = current
        expected[ordinal - 1][route_i] = route
        expected[ordinal - 1][desc_i] = conserved
    projection = oracle._projection_comparison(expected, rows)
    contract = oracle._description_loss_contract(projection, rows)
    check(contract["exact"] and projection["typed_cell_mismatch_count"] == 15,
          "exact 15-row Description loss was not classified")
    check(len(oracle.EXPECTED_DESCRIPTION_LOSSES) == 15,
          "Description-loss manifest no longer binds all 15 rows")
    changed = [list(row) for row in rows]
    changed[oracle.EXPECTED_DESCRIPTION_LOSSES[0][0] - 2][desc_i] = "DIFFERENT"
    changed_projection = oracle._projection_comparison(expected, changed)
    check(not oracle._description_loss_contract(changed_projection, changed)["exact"],
          "changed Description residue inherited the accepted manifest")
    deleted = rows[:-1]
    deletion = oracle._projection_comparison(expected, deleted)
    check(not deletion["ordered_exact"] and deletion["missing_or_extra_row_count"] == 1,
          "normalized row deletion was not detected")
    inserted = rows + [list(rows[-1])]
    insertion = oracle._projection_comparison(expected, inserted)
    check(not insertion["ordered_exact"] and insertion["missing_or_extra_row_count"] == 1,
          "normalized row insertion was not detected")


def test_identity_and_collision_contracts():
    def raw(location, pm, suffix="", description="RAMP"):
        row = [None] * len(oracle.RAW_HEADERS)
        values = {
            "RAM_CONNECTION_ID": Decimal(1), "RAMP_NANE": "RAMP",
            "LOCATION": location, "PR": "", "PM": pm, "PM_SFX": suffix,
            "DATE_OF_RECORD": date(2025, 1, 1), "HG": suffix,
            "AREA_4": "A", "CITY_CODE": "1", "POP": "R", "ON_OFF": "N",
            "ADT_EFF_YEAR": "2023", "ADT": Decimal(5), "RAMP_TYPE": "1",
            "EFF_DATE": date(2025, 1, 1), "DESCRIPTION": description,
            "SEG_ORDER_ID": Decimal(1),
        }
        for name, value in values.items():
            row[oracle.RAW_HEADERS.index(name)] = value
        return tuple(row)

    raw_rows = [raw("01-DN-101", "1.000"), raw("02-LA-101", "1.000")]
    projected = []
    info = []
    for row in raw_rows:
        p, i = oracle._project_raw_row(row)
        projected.append(p)
        info.append(i)
    census = oracle._collision_census(raw_rows, projected, info)
    check(census["route_plus_pm_cross_county"] == {
        "cross_county_keys": 1, "county_specific_identities": 2,
        "largest_county_multiplicity": 2},
        "cross-county weak identity was not exposed")
    check(census["physical_identity"]["duplicate_groups"] == 0,
          "distinct counties collapsed under full identity")


def test_physical_row_contiguity_is_reported_and_acceptance_bound():
    raw = [None] * len(oracle.RAW_HEADERS)
    values = {
        "RAM_CONNECTION_ID": Decimal(1), "RAMP_NANE": "RAMP",
        "LOCATION": "01-DN-101", "PR": "", "PM": "1.000", "PM_SFX": "",
        "DATE_OF_RECORD": date(2025, 1, 1), "HG": "", "AREA_4": "A",
        "CITY_CODE": "1", "POP": "R", "ON_OFF": "N",
        "ADT_EFF_YEAR": "2023", "ADT": Decimal(5), "RAMP_TYPE": "1",
        "EFF_DATE": date(2025, 1, 1), "DESCRIPTION": "RAMP",
        "SEG_ORDER_ID": Decimal(1),
    }
    for name, value in values.items():
        raw[oracle.RAW_HEADERS.index(name)] = value
    projected, info = oracle._project_raw_row(raw)
    identity = stream.FileIdentity("fixture", 1, 1, 1, 1, "0" * 64)
    raw_sheet = stream.StreamedSheet(
        "Sheet 1", oracle.RAW_HEADERS,
        (stream.StreamedRow(2, tuple(raw)),), "1900", identity, identity)
    normalized_sheet = stream.StreamedSheet(
        "Ramp Detail (TSN)", oracle.NORMALIZED_HEADERS,
        (stream.StreamedRow(3, projected),), "1900", identity, identity)
    census = oracle._order_and_anomalies(
        raw_sheet, [tuple(raw)], normalized_sheet, [projected], [info])
    check(census["raw_source_rows_contiguous_from_2"]
          and not census["normalized_source_rows_contiguous_from_2"],
          "gapped normalized physical row was not exposed")
    source = SOURCE.read_text(encoding="utf-8")
    check('"normalized_physical_rows_contiguous"' in source
          and '"raw_physical_rows_contiguous"' in source,
          "physical row contiguity is not part of audit_invariants")


def main():
    test_independence_and_exact_schemas()
    test_typed_digests_and_order()
    test_location_pm_date_and_description_contracts()
    test_exact_fifteen_row_loss_manifest()
    test_identity_and_collision_contracts()
    test_physical_row_contiguity_is_reported_and_acceptance_bound()
    print("OK  Stage-6 Ramp conservation: independent exact schemas, typed digests, "
          "identity/collision rules, source dispositions, and exact 15-row red manifest")


if __name__ == "__main__":
    main()

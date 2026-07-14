#!/usr/bin/env python3
"""Permanent adversarial gate for the Stage-8 Ramp Summary comparison oracle."""

from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase8_ramp_summary_comparison as oracle


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejected(callable_, message: str) -> None:
    try:
        callable_()
    except oracle.AuditError:
        return
    raise AssertionError(message)


def _write_tsn(path: Path, rows: list[tuple[str, object]]) -> None:
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Ramp Summary (TSN)"
    ws.append(["Category", "Count"])
    for row in rows:
        ws.append(row)
    workbook.save(path)
    workbook.close()


def _write_zip(path: Path, core: bytes, sheet: bytes,
               extra: tuple[str, bytes] | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("docProps/core.xml", core)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        if extra is not None:
            archive.writestr(*extra)


def _synthetic_truth() -> dict[str, object]:
    aggregate = dict(oracle.EXPECTED_TSMIS_AGGREGATE)
    tsn_counts = {}
    for key in oracle.TSN_ORDER:
        slug = oracle.KEY_TO_SLUG.get(key)
        tsn_counts[key] = aggregate[slug] if slug else 1
    return oracle._comparison_truth(aggregate, tsn_counts)


def _current_bad_product_rows(truth: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for row in truth["rows"]:
        rows.append({
            "category": row["category"],
            "status": "Both",
            "tsmis": 0 if row["category"] in (oracle.P_KEY, oracle.V_KEY)
            else row["tsmis"],
            "tsn": row["tsn"],
        })
    rows.append({
        "category": "Ramp Points w/out linework",
        "status": "TSMIS only", "tsmis": 59, "tsn": None,
    })
    return rows


def _publication_fixture(*, audit_complete: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "audit": "synthetic Stage-8 decision fixture",
        "audit_invariants": {"synthetic_audit": audit_complete},
        "source_truth_exact": audit_complete,
        "production_value_projection_exact": audit_complete,
        "production_comparison_semantics_exact": False,
        "stage8_base_oracle_complete": audit_complete,
        "comparison_end_to_end_perfect": False,
        "findings": {"product_red": [{"finding": "synthetic"}]},
    }


def main() -> int:
    for label, value in (("bool", True), ("float", 1.0),
                         ("string", "1"), ("negative", -1)):
        rejected(lambda value=value: oracle._strict_count(value, label),
                 f"strict integer gate accepted {label}")
    require(oracle._strict_count(0, "zero") == 0,
            "strict integer gate rejected zero")

    require(oracle._route_from_name(
        Path("tsar_ramp_summary_route_005S.pdf"), ".pdf") == "005S",
        "suffix route identity was truncated")
    require(oracle._route_from_name(
        Path("tsar_ramp_detail_route_010.xlsx"), ".xlsx") == "010",
        "detail filename contract rejected a valid route")
    rejected(lambda: oracle._route_from_name(
        Path("tsar_ramp_summary_route_5.pdf"), ".pdf"),
        "unpadded route filename was accepted")

    exact_universe = oracle._require_exact_route_universes(
        {"pdf": ["001", "005S", "010"],
         "xlsx": ["001", "005S", "010"]}, expected_count=3)
    require(exact_universe["all_exact"], "valid route universes did not pass")
    rejected(lambda: oracle._require_exact_route_universes(
        {"pdf": ["001", "001", "010"],
         "xlsx": ["001", "005S", "010"]}, expected_count=3),
        "duplicate route universe was accepted")
    rejected(lambda: oracle._require_exact_route_universes(
        {"pdf": ["001", "005S"], "xlsx": ["001", "005S"]},
        expected_count=3), "dropped route was accepted")
    rejected(lambda: oracle._require_exact_route_universes(
        {"pdf": ["001", "005S", "010"],
         "xlsx": ["001", "010", "005S"]}, expected_count=3),
        "route-order mutation was accepted")

    cross = oracle._cross_format(
        {"001": {"x": 1, "y": 2}}, {"001": {"x": 1, "y": 3}})
    require(cross["difference_count"] == 1,
            "cross-format cell mutation was not isolated")

    synthetic = {slug: 0 for slug, _row, _label in oracle.ALL_SOURCE}
    synthetic.update({"total_ramps": 1, "ramp_points_no_linework": 0})
    arithmetic = oracle._arithmetic({"001": synthetic}, {})
    require(len(arithmetic["unexplained_after_detail_pv"]) == 1,
            "unexplained Ramp Type residual was accepted")
    reconciled = oracle._arithmetic({"001": synthetic}, {"001": 1})
    require(not reconciled["unexplained_after_detail_pv"],
            "matching P/V evidence did not close the residual")

    detail_exact = oracle._detail_reconciliation(
        {"001": {"total_ramps": 2}, "005S": {"total_ramps": 1}},
        {"001": 2, "005S": 1}, {"001": 2, "005S": 1})
    require(detail_exact["all_exact"], "valid Summary/Detail counts did not pass")
    detail_changed = oracle._detail_reconciliation(
        {"001": {"total_ramps": 2}, "005S": {"total_ramps": 1}},
        {"001": 2, "005S": 1}, {"001": 1, "005S": 1})
    require(not detail_changed["all_exact"] and len(detail_changed["mismatches"]) == 1,
            "Detail PDF row-count mutation was accepted")

    truth = _synthetic_truth()
    corrected_rows = [
        {"category": row["category"], "status": row["status"],
         "tsmis": row["tsmis"], "tsn": row["tsn"]}
        for row in truth["rows"]
    ]
    require(not oracle._semantic_gaps(corrected_rows, truth["rows"]),
            "contract-correct one-sided P/V rows were marked defective")
    bad_rows = _current_bad_product_rows(truth)
    gap_ids = tuple(
        gap["id"] for gap in oracle._semantic_gaps(bad_rows, truth["rows"]))
    require(gap_ids == oracle.EXPECTED_PRODUCT_GAP_IDS,
            f"current product's exact three-gap contract drifted: {gap_ids!r}")
    footnote_only = corrected_rows + [bad_rows[-1]]
    require([gap["id"] for gap in oracle._semantic_gaps(
        footnote_only, truth["rows"])] == [
            "no_linework_display_metric_injected_into_comparison"],
        "footnote verdict injection was not independently detected")
    wrong_source = copy.deepcopy(corrected_rows)
    wrong_source[0]["tsmis"] += 1
    require(any(gap["id"] == "source_backed_comparison_row_mismatch"
                for gap in oracle._semantic_gaps(wrong_source, truth["rows"])),
            "source-backed comparison value mutation was accepted")

    with tempfile.TemporaryDirectory() as raw_temp:
        root = Path(raw_temp)
        valid_rows = [(key, index) for index, key in enumerate(oracle.TSN_ORDER)]
        valid_path = root / "valid.xlsx"
        _write_tsn(valid_path, valid_rows)
        loaded = oracle._load_tsn_normalized(valid_path)
        require(tuple(loaded["order"]) == oracle.TSN_ORDER,
                "valid TSN category order did not pass")

        swapped = list(valid_rows)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        swapped_path = root / "swapped.xlsx"
        _write_tsn(swapped_path, swapped)
        rejected(lambda: oracle._load_tsn_normalized(swapped_path),
                 "TSN category-order mutation was accepted")

        duplicate = list(valid_rows)
        duplicate[1] = (duplicate[0][0], duplicate[1][1])
        duplicate_path = root / "duplicate.xlsx"
        _write_tsn(duplicate_path, duplicate)
        rejected(lambda: oracle._load_tsn_normalized(duplicate_path),
                 "duplicate TSN category was accepted")

        typed = list(valid_rows)
        typed[0] = (typed[0][0], True)
        typed_path = root / "typed.xlsx"
        _write_tsn(typed_path, typed)
        rejected(lambda: oracle._load_tsn_normalized(typed_path),
                 "Boolean TSN count was accepted")

        zip_a = root / "a.xlsx"
        zip_b = root / "b.xlsx"
        zip_c = root / "c.xlsx"
        zip_d = root / "d.xlsx"
        _write_zip(zip_a, b"core-A", b"sheet-A")
        _write_zip(zip_b, b"core-B-with-a-different-compressed-length", b"sheet-A")
        _write_zip(zip_c, b"core-A", b"sheet-B")
        _write_zip(zip_d, b"core-A", b"sheet-A", ("docProps/app.xml", b"app"))
        stable_a = oracle._zip_digest_without_core(zip_a)
        stable_b = oracle._zip_digest_without_core(zip_b)
        digest_a = stable_a["canonical_member_sha256"]
        require(stable_a["excluded_members"] == ["docProps/core.xml"]
                and stable_a == stable_b,
            "core.xml-only volatility changed the stable package digest")
        require(digest_a != oracle._zip_digest_without_core(
            zip_c)["canonical_member_sha256"],
            "worksheet-member mutation escaped the stable package digest")
        require(digest_a != oracle._zip_digest_without_core(
            zip_d)["canonical_member_sha256"],
            "non-core member addition escaped the stable package digest")

        literal = root / "literal.xlsx"
        formula = root / "formula.xlsx"
        for path, value in ((literal, 2), (formula, "=1+1")):
            workbook = Workbook()
            workbook.active["A1"] = value
            workbook.save(path)
            workbook.close()
        require(oracle._workbook_semantic_digest(literal)[
            "ordered_semantic_sha256"] != oracle._workbook_semantic_digest(formula)[
                "ordered_semantic_sha256"],
            "formula/literal semantic mutation escaped the workbook digest")

    original_run = oracle.run
    original_current = oracle._publication_current
    try:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            output = root / "decision.json"
            acceptance = output.with_suffix(output.suffix + ".acceptance.json")
            rejection = output.with_suffix(output.suffix + ".rejection.json")
            acceptance.write_text('{"accepted": true}\n', encoding="utf-8")
            oracle.run = lambda _args: copy.deepcopy(
                _publication_fixture(audit_complete=True))
            oracle._publication_current = lambda *_args: (True, {})
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = oracle.main(["--output", str(output)])
            require(exit_code == 1,
                    "open semantic findings were accepted without authorization")
            require(not acceptance.exists(),
                    "rejected rerun left a stale acceptance record")
            require(rejection.exists(), "rejected rerun wrote no rejection record")
            decision = json.loads(rejection.read_text(encoding="utf-8"))
            require(decision["accepted"] is False and decision["reason"]
                    == "open_product_findings_not_authorized",
                    "open-finding rejection decision is not explicit")

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = oracle.main([
                    "--output", str(output), "--allow-open-findings"])
            require(exit_code == 0 and acceptance.exists() and not rejection.exists(),
                    "authorized open-finding decision did not accept cleanly")
            decision = json.loads(acceptance.read_text(encoding="utf-8"))
            require(decision["accepted"] is True
                    and decision["open_product_findings_authorized"] is True,
                    "acceptance does not explicitly bind open findings")

            oracle.run = lambda _args: copy.deepcopy(
                _publication_fixture(audit_complete=False))
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = oracle.main([
                    "--output", str(output), "--allow-open-findings"])
            require(exit_code == 2 and rejection.exists() and not acceptance.exists(),
                    "audit-false publication did not fail closed")
    finally:
        oracle.run = original_run
        oracle._publication_current = original_current

    print(
        "OK Stage-8 Ramp Summary gate: strict typed counts; suffix/duplicate/drop/order "
        "routes; PDF/XLSX/detail residual mutations; TSN order/duplicate/type drift; "
        "exact P/V/footnote semantic gaps; core.xml-only package volatility; workbook "
        "formula semantics; detached acceptance/rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Permanent semantic gate for the Stage-8 Highway Detail oracle."""

from __future__ import annotations

from datetime import date
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import zlib


BUILD_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_ROOT))

import phase8_highway_detail_comparison as oracle  # noqa: E402
import phase8_highway_detail_source_oracle as source  # noqa: E402


passed = 0


def require(condition: bool, message: str) -> None:
    global passed
    if not condition:
        raise AssertionError(message)
    passed += 1


def rejects(action, message: str) -> None:
    try:
        action()
    except (oracle.AuditError, ValueError, TypeError):
        require(True, message)
    else:
        raise AssertionError(message)


def detail_row(index: int, *, route: str = "001", district: str = "01",
               county: str = "AAA", pp: str = "", pm: str = "001.000",
               equation: str = "", roadbed: str = "",
               description: str = "SAME") -> oracle.DetailRow:
    values = [""] * len(oracle.SHARED_FIELDS)
    values[oracle.SHARED_FIELDS.index("PS")] = equation
    values[oracle.SHARED_FIELDS.index("Description")] = description
    return oracle.DetailRow(
        source_index=index, source="gate", source_ref=f"gate:{index}",
        route=route, district=district, county=county, complete_pp=pp,
        numeric_pm=pm, equation=equation, roadbed=roadbed,
        explicit_trailing=equation or roadbed, values=tuple(values))


def source_row(index: int, *, member: str = "001", district: str = "",
               county: str = "", postmile: str = "001.000",
               length: str = "000.100", description: str = "SAME",
               source_name: str = "TSMIS Excel") -> source.SourceRow:
    values = [""] * len(source.TSMIS_HEADERS)
    values[source.TSMIS_HEADERS.index("Post Mile")] = postmile
    values[source.TSMIS_HEADERS.index("Length")] = length
    values[source.TSMIS_HEADERS.index("HG")] = "D"
    values[source.TSMIS_HEADERS.index("Description")] = description
    return source.SourceRow(
        source_index=index, source=source_name,
        source_ref=f"{source_name}:{index}", member_route=member,
        district=district, county=county, values=tuple(values))


def publication_fixture(root: Path):
    label = "gate"
    formulas = root / f"{label}.xlsx"
    values = root / f"{label} (values).xlsx"
    formulas.write_bytes(b"formula-workbook")
    values.write_bytes(b"values-workbook")
    paths = {"formulas": formulas, "values": values}
    identities = {
        flavor: oracle._file_identity(path)
        for flavor, path in paths.items()}

    def member(flavor: str) -> dict[str, object]:
        path = paths[flavor]
        stat = path.stat()
        return {
            "canonical_path_at_write": str(path.resolve()).casefold(),
            "commit_role": (
                "canonical" if flavor == "values" else "best_effort"),
            "flavor": flavor,
            "mtime_ns": stat.st_mtime_ns,
            "path": str(path.resolve()),
            "relative_path": path.name,
            "sha256": identities[flavor]["sha256"],
            "size": stat.st_size,
        }

    members = [member("values"), member("formulas")]
    generation = {
        "completion": "complete",
        "content_digests": {
            flavor: identity["sha256"]
            for flavor, identity in identities.items()},
        "generation_id": "11111111-1111-1111-1111-111111111111",
        "members": members,
        "producer_versions": {},
        "publication_state": "committed",
        "requested_mode": "both",
    }
    counts = {
        "known": True, "paired_rows": 1,
        "side_a_only_rows": 0, "side_b_only_rows": 0,
        "differing_rows": 0, "differing_cells": 0,
        "per_field_counts": {}, "asserted_cells": 34,
        "context_cells": 0,
    }
    persisted = {
        "capped_group_diagnostics": [], "completion": "complete",
        "counts": counts, "coverage_diagnostics": [],
        "duplicate_group_count": 0, "failures": [],
        "pairing_quality": "exact", "pairing_trace": [],
        "source_identities": [], "status": "ok", "verdict": "match",
        "warnings": [],
    }
    decoded = oracle._canonical(persisted)
    compressed = zlib.compress(decoded)
    chunk_sha = oracle._sha_bytes(compressed)
    decoded_sha = oracle._sha_bytes(decoded)
    chunk_name = (
        f".cmpv3-{decoded_sha}-000000-{chunk_sha}"
        ".comparison-payload.zlib")
    chunk = root / chunk_name
    chunk.write_bytes(compressed)
    binding = oracle._sha_bytes(oracle._canonical({
        "decoded_sha256": decoded_sha, "completion": "complete",
        "skipped_inputs": 0, "failed_inputs": 0,
        "artifact_generation": generation,
    }))
    manifest = {
        "binding_sha256": binding,
        "chunks": [{
            "decoded_size": len(decoded), "relative_path": chunk_name,
            "sha256": chunk_sha, "size": len(compressed),
        }],
        "decoded_sha256": decoded_sha, "decoded_size": len(decoded),
        "encoding": "canonical-json-zlib-chunks-v1", "schema_version": 1,
    }
    for flavor, path in paths.items():
        envelope = {
            "artifact_generation": generation,
            "built_at_mtime": path.stat().st_mtime,
            "comparison_payload": manifest,
            "comparison_schema_version": 3, "completion": "complete",
            "failed_inputs": 0, "record_type": "comparison",
            "schema_version": 1,
            "self_member": next(
                item for item in members if item["flavor"] == flavor),
            "skipped_inputs": 0,
        }
        Path(str(path) + ".outcome.json").write_text(
            json.dumps(envelope), encoding="utf-8")
    witness = {"result": {
        "status": "ok", "completion": "complete", "verdict": "match",
        "skipped_inputs": 0, "failed_inputs": 0, "counts": counts,
        "warnings": [], "failures": [],
        "artifact_generation": {
            "completion": "complete", "publication_state": "committed",
            "requested_mode": "both", "members": [{
                "flavor": item["flavor"],
                "commit_role": item["commit_role"],
                "path": item["path"], "bytes": item["size"],
                "sha256": item["sha256"],
            } for item in members],
        },
    }}
    expected = {
        "counts": counts, "_pairing_trace": [],
        "_pairing_trace_semantics": [],
        "pairing_trace_sha256": oracle._sha_bytes(oracle._canonical([])),
        "independent_pairing_trace_wire_sha256": oracle._sha_bytes(
            oracle._canonical([])),
    }
    return (label, formulas, values, witness, expected, identities, chunk)


def main() -> int:
    require(
        oracle._pm_parts("R044.236E", "U")
        == ("R", "044.236", "E", ""),
        "complete PP/equation split drift")
    require(
        oracle._pm_parts("C043.925R", "R")
        == ("C", "043.925", "", "R"),
        "explicit roadbed split drift")
    require(
        oracle._pm_parts("043.925E", "L")
        == ("", "043.925", "E", "L"),
        "HG roadbed fallback with occupied equation slot drift")
    rejects(lambda: oracle._pm_parts("BAD", "D"),
            "malformed Post Mile was accepted")
    require(oracle._route("5", "s") == "005S",
            "route/suffix canonicalization drift")
    rejects(lambda: oracle._route("005SS"),
            "malformed route suffix was accepted")

    require(oracle._fixed_three(Decimal("0.0135"), "Length") == "000.014",
            "exact half-even Length rounding drift")
    require(
        oracle._fixed_three(Decimal("0.0074999999999999997"), "Length")
        == "000.007", "exact below-half Length rounding drift")
    require(oracle._project("Length", "-17.229") == "-17.229",
            "negative printed Length drift")
    require(oracle._project("Length", "3-1.234") == "3-1.234",
            "literal vendor print shape was coerced")
    require(oracle._project("NA", "A") == "",
            "TSN ordinary-add render equivalence drift")
    require(oracle._project("LB #Ln", "002") == "2",
            "zero-pad numeric render equivalence drift")
    require(oracle._project("Med V/WDA", "8v") == "08V",
            "median width/variance composition drift")
    require(oracle._project("Date of Rec", date(2026, 7, 9)) == "26-07-09",
            "typed date projection drift")
    require(oracle._project("Description", " A\t B  C ") == "A B C",
            "Description whitespace rendering drift")

    base = detail_row(0, county="AAA", pp="R", roadbed="L")
    require(base.physical_key == ("001", "AAA", "R", "001.000", "L"),
            "approved physical key shape drift")
    require(detail_row(1, equation="E").physical_key
            == detail_row(2, equation="").physical_key,
            "equation incorrectly entered physical identity")
    require(detail_row(1, county="AAA").physical_key
            != detail_row(2, county="BBB").physical_key,
            "County failed to split physical identity")
    require(detail_row(1, pp="R").physical_key
            != detail_row(2, pp="S").physical_key,
            "complete PP failed to split physical identity")
    require(detail_row(1, roadbed="R").physical_key
            != detail_row(2, roadbed="L").physical_key,
            "roadbed failed to split physical identity")
    require(detail_row(1, route="005").physical_key
            != detail_row(2, route="005S").physical_key,
            "route suffix failed to split physical identity")

    equation = oracle._comparison(
        "equation", [detail_row(0, equation="E")],
        [detail_row(10, equation="")])
    require(equation["counts"]["paired_rows"] == 1
            and equation["counts"]["per_field_counts"] == {"PS": 1},
            "equation marker was not separately asserted")
    district = oracle._comparison(
        "district", [detail_row(0, district="01")],
        [detail_row(10, district="02")])
    require(district["counts"]["per_field_counts"] == {"District": 1},
            "District ownership disagreement was hidden")

    left = [
        detail_row(0, county="AAA", description="ALPHA"),
        detail_row(1, county="BBB", description="BETA"),
    ]
    right = [
        detail_row(10, county="AAA", description="BETA"),
        detail_row(11, county="BBB", description="ALPHA"),
    ]
    county_swap = oracle._comparison("county swap", left, right)
    require(county_swap["counts"]["paired_rows"] == 2
            and county_swap["counts"]["per_field_counts"]
            == {"Description": 2},
            "cross-county similarity pairing masked a value swap")
    pp_split = oracle._comparison(
        "PP split", [detail_row(0, pp="R")], [detail_row(10, pp="S")])
    require(pp_split["counts"]["paired_rows"] == 0
            and pp_split["counts"]["side_a_only_rows"] == 1
            and pp_split["counts"]["side_b_only_rows"] == 1,
            "complete PP mutation did not become one-sided")
    roadbed_split = oracle._comparison(
        "roadbed split", [detail_row(0, roadbed="R")],
        [detail_row(10, roadbed="L")])
    require(roadbed_split["counts"]["paired_rows"] == 0
            and roadbed_split["counts"]["side_a_only_rows"] == 1
            and roadbed_split["counts"]["side_b_only_rows"] == 1,
            "roadbed mutation did not become one-sided")

    unique_excel = source_row(0, description="UNIQUE")
    ambiguous_excel = source_row(1, description="AMBIG")
    unpaired_excel = source_row(2, description="UNPAIRED")
    unique_pdf = source_row(
        10, district="01", county="AAA", description="UNIQUE",
        source_name="TSMIS PDF")
    ambiguous_pdf_a = source_row(
        11, district="01", county="AAA", description="AMBIG",
        source_name="TSMIS PDF")
    ambiguous_pdf_b = source_row(
        12, district="02", county="BBB", description="AMBIG",
        source_name="TSMIS PDF")
    attested, evidence = oracle._attest_excel_county(
        [unique_excel, ambiguous_excel, unpaired_excel],
        [unique_pdf, ambiguous_pdf_a, ambiguous_pdf_b],
        [(unique_excel, unique_pdf, "all_34_render_equal"),
         (ambiguous_excel, ambiguous_pdf_a, "all_34_render_equal")])
    require(len(attested) == 1 and attested[0].county == "AAA",
            "unique printed owner did not attest Excel County")
    require(evidence["ambiguous_cross_owner_pair_count"] == 1,
            "cross-owner identical signature was accepted")
    require(evidence["format_unpaired_excel_rows"] == 1,
            "format-unpaired Excel row was not retained")
    require(evidence["total_county_unknown_excel_rows"] == 2
            and evidence["county_inference_used"] is False,
            "Excel County unknown census drift")

    constraint_excel = [
        source_row(0, postmile="001.000", description="EXACT"),
        source_row(1, postmile="002.000", description="SINGLE"),
        source_row(2, postmile="003.000", description="TSN ONLY"),
    ]
    constraint_pdf = [
        source_row(10, district="01", county="AAA", postmile="001.000",
                   description="EXACT", source_name="TSMIS PDF"),
        source_row(11, district="02", county="BBB", postmile="001.000",
                   description="OTHER", source_name="TSMIS PDF"),
        source_row(12, district="03", county="CCC", postmile="002.000",
                   description="SINGLE", source_name="TSMIS PDF"),
    ]
    exact_constraint = [oracle._from_tsmis_source(
        constraint_excel[0], district="01", county="AAA")]
    constrained, constraint_evidence = oracle._analyze_excel_owner_constraints(
        constraint_excel, constraint_pdf,
        [detail_row(20, district="04", county="DDD", pm="003.000")],
        exact_constraint, [])
    require([(row.source_index, row.county) for row in constrained]
            == [(0, "AAA"), (1, "CCC")],
            "exact/companion-singleton owner constraint drift")
    require(constraint_evidence["unresolved_owner_rows"] == 1
            and constraint_evidence["classifications"][
                "no_companion_key_tsn_single_owner_not_promoted"] == 1
            and constraint_evidence["tsn_only_owner_promotions"] == 0,
            "TSN comparison target was used circularly to invent County")

    snapshot_excel = [source_row(0, description="SNAPSHOT")]
    snapshot_pdf = [source_row(
        10, district="01", county="NEW", description="SNAPSHOT",
        source_name="TSMIS PDF")]
    current_snapshot = [oracle._from_tsmis_source(
        snapshot_excel[0], district="01", county="NEW")]
    same_build_snapshot = [oracle._from_tsmis_source(
        snapshot_excel[0], district="01", county="OLD")]
    snapshot_rows, snapshot_evidence = (
        oracle._analyze_excel_owner_constraints(
            snapshot_excel, snapshot_pdf, [], current_snapshot,
            same_build_snapshot))
    require(snapshot_rows[0].county == "OLD"
            and snapshot_evidence["classifications"] == {
                "same_build_historical_exact_companion_unique_owner": 1},
            "same-build snapshot owner did not supersede later PDF owner")
    require(snapshot_evidence["cross_edition_owner_conflicts"] == 1
            and snapshot_evidence[
                "cross_edition_owner_conflict_ledger_sha256"]
            != oracle.hashlib.sha256().hexdigest(),
            "cross-edition owner conflict was not retained")
    current_rows, current_evidence = oracle._analyze_excel_owner_constraints(
        snapshot_excel, snapshot_pdf, [], current_snapshot, [])
    require(current_rows[0].county == "NEW"
            and current_evidence["cross_edition_owner_conflicts"] == 0,
            "historical owner was applied without same-build attestation")

    component_excel = [
        source_row(0, postmile="001.000", description="LEFT"),
        source_row(1, postmile="002.000", description="RIGHT"),
    ]
    component_pdf = [source_row(
        10, district="07", county="LA", postmile="003.000",
        description="LEFT / RIGHT", source_name="TSMIS PDF")]
    component_claims, component_evidence = (
        oracle._composite_description_owner_attestations(
            component_excel, component_pdf, {0, 1}))
    require({index: value[:2] for index, value in component_claims.items()}
            == {0: ("07", "LA"), 1: ("07", "LA")},
            "unique printed composite components did not attest owner")
    require(component_evidence["row_equivalence_claimed"] is False
            and component_evidence["uniquely_owner_attested_rows"] == 2,
            "composite component mapping manufactured row equivalence")
    changed_component = [replace(
        component_pdf[0], values=tuple(
            "LEFT + RIGHT" if index == source.TSMIS_HEADERS.index(
                "Description") else value
            for index, value in enumerate(component_pdf[0].values)))]
    changed_claims, _ = oracle._composite_description_owner_attestations(
        component_excel, changed_component, {0, 1})
    require(changed_claims == {},
            "changed composite separator/components were accepted")
    duplicate_excel = [
        component_excel[0], replace(
            component_excel[1], values=component_excel[0].values)]
    duplicate_claims, _ = oracle._composite_description_owner_attestations(
        duplicate_excel, component_pdf, {0, 1})
    require(duplicate_claims == {},
            "non-unique Excel Description received composite owner")
    duplicate_parent = [component_pdf[0], replace(
        component_pdf[0], source_index=11, source_ref="TSMIS PDF:11")]
    parent_claims, parent_evidence = (
        oracle._composite_description_owner_attestations(
            component_excel, duplicate_parent, {0, 1}))
    require(parent_claims == {}
            and parent_evidence["ambiguous_eligible_rows"] == 2,
            "multiple parent composite claims were accepted")
    blank_parent = [replace(
        component_pdf[0], district="", county="")]
    blank_claims, _ = oracle._composite_description_owner_attestations(
        component_excel, blank_parent, {0, 1})
    require(blank_claims == {},
            "blank printed composite owner was promoted")
    with tempfile.TemporaryDirectory() as empty:
        rejects(lambda: oracle._bind_historical_owner_tree(
            "pdf", Path(empty), ".pdf", exact_universe=True),
            "missing historical same-build source was accepted")

    excel_a = source_row(0, description="A")
    excel_b = source_row(1, description="B", length="000.100")
    pdf_a = source_row(
        10, district="01", county="AAA", description="A",
        source_name="TSMIS PDF")
    pdf_b = source_row(
        11, district="01", county="AAA", description="B", length="000.200",
        source_name="TSMIS PDF")
    pdf_extra = source_row(
        12, district="01", county="AAA", description="EXTRA",
        source_name="TSMIS PDF")
    public = source._source_format_alignment(
        [excel_a, excel_b], [pdf_a, pdf_b, pdf_extra])
    pairs, pair_evidence = oracle._format_pairs(
        [excel_a, excel_b], [pdf_a, pdf_b, pdf_extra], public)
    require(len(pairs) == 2 and pair_evidence["matches_public_source_oracle"],
            "independent/public format pair maps diverged")
    require(public["totals"]["all_34_render_equal"] == 1
            and public["totals"]["fields_2_through_33_render_equal"] == 1
            and public["totals"]["pdf_only_rows"] == 1,
            "two-tier source-format mapping drift")

    equivalence = oracle._indexed_oracle_equivalence_gate()
    require(equivalence == {
        **equivalence, "passed": 5, "required": 5, "exact": True},
        "indexed/original oracle semantic equivalence drift")

    require(oracle.PRODUCT_HEADER == ("Post Mile", *oracle.SHARED_FIELDS)
            and len(oracle.PRODUCT_SCHEMA.field_rules)
            == len(oracle.SHARED_FIELDS),
            "weak product schema projection drift")
    weak_left = detail_row(0, county="AAA", description="SAME")
    weak_right = detail_row(10, county="BBB", description="SAME")
    weak = oracle._product_expected(
        "weak county", "A", "B", [weak_left], [weak_right])
    require(weak["counts"]["paired_rows"] == 1
            and weak["counts"]["side_a_only_rows"] == 0
            and weak["counts"]["side_b_only_rows"] == 0,
            "observed product identity unexpectedly retained County")
    strong = oracle._comparison(
        "strong county", [weak_left], [weak_right])
    require(strong["counts"]["paired_rows"] == 0
            and strong["counts"]["side_a_only_rows"] == 1
            and strong["counts"]["side_b_only_rows"] == 1,
            "source/product identity boundary collapsed")
    weak_equation = oracle._product_expected(
        "weak equation", "A", "B", [detail_row(0, equation="E")],
        [detail_row(10, equation="")])
    require(weak_equation["counts"]["per_field_counts"] == {"PS": 1},
            "weak product oracle stopped asserting PS")
    require(oracle._raw_cell(None) == oracle._raw_cell("")
            and oracle._raw_cell(Decimal("1.00"))
            == ("Decimal", "1.00"),
            "raw consolidation cell contract drift")

    raw_values = [""] * len(oracle.RAW_HEADERS)
    raw_map = {name: index for index, name in enumerate(oracle.RAW_HEADERS)}
    for name, value in {
            "DIST": "01", "CNTY": "AAA", "RTE": "1", "RTE_SFX": "",
            "DIST_CNTY_ROUTE": "01 AAA 001", "ADT_AMT": "100",
            "PROFILE": "P", "LK_BACK_ADT": "90", "CHNGMILE": "C",
            "DVM": "D"}.items():
        raw_values[raw_map[name]] = value
    raw_claim = replace(
        detail_row(0), raw_values=tuple(raw_values),
        source_only=tuple((field, raw_values[raw_map[field]])
                          for field in oracle.SOURCE_ONLY_FIELDS))
    raw_counter = oracle._report_view_source_counter([raw_claim], raw=True)
    require(list(raw_counter) == [(
        "001", "001.000", "01 AAA 001", "100", "P", "90", "C", "D")],
        "raw Report View source-claim mapping drift")
    normalized_counter = oracle._report_view_source_counter(
        [raw_claim], raw=False)
    require(list(normalized_counter) == [
        ("001", "001.000", "", "", "", "", "", "")],
        "normalized Report View omission witness drift")
    exact_values = list(detail_row(0).values)
    exact_values[oracle.SHARED_FIELDS.index("Length")] = "000.014"
    binary_raw = replace(
        detail_row(0), values=tuple(exact_values),
        raw_values=tuple(
            Decimal("0.0135") if name == "LENGTH" else ""
            for name in oracle.RAW_HEADERS))
    projected_raw = oracle._product_loaded_raw_rows([binary_raw])[0]
    require(projected_raw.values[oracle.SHARED_FIELDS.index("Length")]
            == "000.013",
            "current binary64 raw-product Length witness drift")
    projected_normalized = oracle._product_loaded_normalized_rows(
        [detail_row(0, equation="E")])[0]
    require(projected_normalized.values[
        oracle.SHARED_FIELDS.index("PS")] == "",
        "current normalized-product PS erasure witness drift")
    require(oracle._medwid_helper_values("08V")
            == ("08V", "08", True, "0X", "8V"),
            "Med V/WDA helper-value twin drift")
    require(oracle.EXPECTED_SOURCE_COUNTS["raw_vs_normalized"] == {
        "known": True, "paired_rows": 60083, "side_a_only_rows": 0,
        "side_b_only_rows": 0, "differing_rows": 1,
        "differing_cells": 1, "per_field_counts": {"Length": 1},
        "asserted_cells": 2162988, "context_cells": 0},
        "frozen raw/normalized source count contract drift")
    require(len(oracle.EXPECTED_SOURCE_LEDGERS) == 5
            and oracle.EXPECTED_SOURCE_COUNTS["pdf_vs_tsn_raw"][
                "per_field_counts"]["District"] == 103,
            "frozen statewide source-ledger contract drift")
    require(oracle.EXPECTED_TSMIS_SOURCE["pdf_reconciliation"][
        "multigroup_line2_records"] == 1
        and oracle.EXPECTED_TSMIS_SOURCE["format_totals"][
            "paired_rows"] == 50776,
        "frozen TSMIS source/topology contract drift")

    with tempfile.TemporaryDirectory(prefix="phase8-hd-publication-gate-") as raw:
        fixture = publication_fixture(Path(raw))
        label, formulas, values, witness, expected, identities, chunk = fixture
        publication, referenced = oracle._inspect_publication_pair(
            label, formulas, values, witness, expected, identities)
        require(
            publication["persisted_counts_and_pairing_match_independent_oracle"]
            and publication["persisted_outcome"]["source_identity_count"] == 0
            and referenced == {chunk.name},
            "valid schema-v3 publication fixture was not authenticated")

        chunk_raw = chunk.read_bytes()
        chunk.write_bytes(chunk_raw + b"tamper")
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, witness, expected, identities),
            "payload chunk tamper was accepted")
        chunk.write_bytes(chunk_raw)

        value_sidecar = Path(str(values) + ".outcome.json")
        value_sidecar_raw = value_sidecar.read_bytes()
        value_payload = json.loads(value_sidecar_raw)
        value_payload["artifact_generation"]["generation_id"] = (
            "22222222-2222-2222-2222-222222222222")
        value_sidecar.write_text(json.dumps(value_payload), encoding="utf-8")
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, witness, expected, identities),
            "divergent twin generation was accepted")
        value_sidecar.write_bytes(value_sidecar_raw)

        sidecar_paths = [
            Path(str(formulas) + ".outcome.json"),
            Path(str(values) + ".outcome.json")]
        sidecar_raw = [path.read_bytes() for path in sidecar_paths]
        for path, raw_sidecar in zip(sidecar_paths, sidecar_raw):
            payload = json.loads(raw_sidecar)
            payload["comparison_payload"]["binding_sha256"] = "0" * 64
            path.write_text(json.dumps(payload), encoding="utf-8")
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, witness, expected, identities),
            "stale generation binding was accepted")
        for path, raw_sidecar in zip(sidecar_paths, sidecar_raw):
            path.write_bytes(raw_sidecar)

        wrong_expected = dict(expected)
        wrong_expected["_pairing_trace_semantics"] = [{"invented": True}]
        wrong_expected["pairing_trace_sha256"] = oracle._sha_bytes(
            oracle._canonical(wrong_expected[
                "_pairing_trace_semantics"]))
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, witness, wrong_expected, identities),
            "persisted duplicate trace disagreement was accepted")

        wrong_witness = json.loads(json.dumps(witness))
        wrong_witness["result"]["artifact_generation"]["members"][0][
            "sha256"] = "0" * 64
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, wrong_witness, expected, identities),
            "returned/persisted member disagreement was accepted")

        sentinel = Path(str(formulas) + ".outcome.json.tmp")
        sentinel.write_bytes(b"incomplete")
        rejects(lambda: oracle._inspect_publication_pair(
            label, formulas, values, witness, expected, identities),
            "publication sentinel was accepted")

    trace = {
        "key_components": ["001", "001.000"],
        "side_a_size": 1, "side_b_size": 2, "matrix_cells": 2,
        "side_a_indices": [4], "side_b_indices": [8, 9],
        "smaller_side": "a", "assignment_vector": [1],
        "pairs": [{"side_a_index": 4, "side_b_index": 9, "cost": 2}],
        "total_cost": 2, "positional_cost": 3,
        "algorithm": "rectangular-hungarian-lex-v1",
        "exact": True, "quality": "exact",
    }
    trace_semantics = oracle._persisted_trace_semantics([trace], "gate")
    require(trace_semantics[0]["source_pairs"] == [[4, 9]]
            and trace_semantics[0]["key_components"] == ["001", "001.000"],
            "production duplicate trace semantic projection drift")
    bad_vector = json.loads(json.dumps(trace))
    bad_vector["assignment_vector"] = [0]
    rejects(lambda: oracle._persisted_trace_semantics([bad_vector], "gate"),
            "assignment vector/pair disagreement was accepted")
    bad_cost = json.loads(json.dumps(trace))
    bad_cost["pairs"][0]["cost"] = 3
    rejects(lambda: oracle._persisted_trace_semantics([bad_cost], "gate"),
            "per-pair/total cost disagreement was accepted")
    bad_inventory = json.loads(json.dumps(trace))
    bad_inventory["side_b_indices"] = [9, 9]
    rejects(lambda: oracle._persisted_trace_semantics(
        [bad_inventory], "gate"),
        "duplicate side-index inventory was accepted")
    transposed_order = {
        "key_components": ["035", "007.680"],
        "side_a_size": 3, "side_b_size": 2, "matrix_cells": 6,
        "side_a_indices": [10, 11, 12], "side_b_indices": [20, 21],
        "smaller_side": "b", "assignment_vector": [2, 0],
        "pairs": [
            {"side_a_index": 12, "side_b_index": 20, "cost": 1},
            {"side_a_index": 10, "side_b_index": 21, "cost": 1},
        ],
        "total_cost": 2, "positional_cost": 3,
        "algorithm": "rectangular-hungarian-lex-v1",
        "exact": True, "quality": "exact",
    }
    require(oracle._persisted_trace_semantics(
        [transposed_order], "gate")[0]["source_pairs"]
        == [[10, 21], [12, 20]],
        "wire-order-neutral canonical source-pair mapping drift")

    sheets = ["Summary", "Comparison", "A", "B"]
    formula_counts = {
        "Summary": 3, "Comparison": 39, "A": 8, "B": 8}
    value_counts = {
        "Summary": 1, "Comparison": 2, "A": 3, "B": 3}
    require(oracle._formula_flavor_contract(
        formula_counts, value_counts, sheets,
        formula_counts, value_counts, "A", "B"),
        "valid deliberately distinct formula/value census was rejected")
    changed_formula = dict(formula_counts)
    changed_formula["A"] += 1
    require(not oracle._formula_flavor_contract(
        changed_formula, value_counts, sheets,
        formula_counts, value_counts, "A", "B"),
        "one-formula source-sheet drift was accepted")
    changed_values = dict(value_counts)
    changed_values["B"] += 1
    require(not oracle._formula_flavor_contract(
        formula_counts, changed_values, sheets,
        formula_counts, value_counts, "A", "B"),
        "one-formula values-sheet drift was accepted")
    reordered = {
        "Comparison": 39, "Summary": 3, "A": 8, "B": 8}
    require(not oracle._formula_flavor_contract(
        reordered, value_counts, sheets,
        reordered, value_counts, "A", "B"),
        "reordered formula sheet universe was accepted")
    missing = {"Summary": 3, "Comparison": 39, "A": 8}
    require(not oracle._formula_flavor_contract(
        missing, value_counts, sheets, missing, value_counts, "A", "B"),
        "missing formula sheet was accepted")
    collapsed_source = dict(formula_counts)
    collapsed_source["A"] = value_counts["A"]
    require(not oracle._formula_flavor_contract(
        collapsed_source, value_counts, sheets,
        collapsed_source, value_counts, "A", "B"),
        "collapsed formula/value source flavor was accepted")
    collapsed_comparison = dict(formula_counts)
    collapsed_comparison["Comparison"] = value_counts["Comparison"]
    require(not oracle._formula_flavor_contract(
        collapsed_comparison, value_counts, sheets,
        collapsed_comparison, value_counts, "A", "B"),
        "non-richer formula Comparison sheet was accepted")
    require(oracle._sha_bytes(oracle._canonical({"a": 1, "b": 2}))
            == oracle._sha_bytes(oracle._canonical({"b": 2, "a": 1})),
            "frozen product-object contract is mapping-order sensitive")
    require(oracle._sha_bytes(oracle._canonical({"counts": {"paired": 1}}))
            != oracle._sha_bytes(oracle._canonical(
                {"counts": {"paired": 2}})),
            "product-object count mutation did not change contract digest")

    print(json.dumps({
        "status": "pass", "assertions": passed,
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

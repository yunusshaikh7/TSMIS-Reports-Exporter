"""Permanent synthetic gate for the independent Highway Log Stage-6 oracle."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
from tempfile import TemporaryDirectory

BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_DIR))
import phase6_highway_log_conservation as oracle  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejected(callable_, label: str) -> None:
    try:
        callable_()
    except oracle.ConservationError:
        return
    raise AssertionError(f"invalid mutation admitted: {label}")


def glyph(text: str, x0: float, width: float = 1.0, top: float = 80.0):
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top}


def base_record():
    fields = {key: None for key in oracle.SOURCE_KEYS}
    fields.update({
        "location": "R001.000", "mi": "0.075", "cnty_odom": "001.000",
        "ru": "R", "spd": "55", "ter": "F", "hg": "D", "ac": "F",
        "lb_t": "++", "lb_tw": "036", "rb_t": "H", "rb_tw": "024",
        "adt_back": "010000", "adt_pp": "P", "adt_ahead": "012000",
        "rec": "640101",
    })
    return {
        "member": "fixture.pdf", "district": "01", "county": "MEN",
        "route": "001", "route_qualifier": "U", "owner_occurrence": 1,
        "physical_page": 2,
        "printed_page": 1, "line": 7, "top": "84.409", "x0": "15.520",
        "raw_text": "fixture", "sequence": 1, "fields": fields,
        "description_lines": ["FIRST", "SECOND"],
        "description": "FIRST SECOND",
        "production_description": "FIRST, SECOND",
    }


def main() -> int:
    require(len(oracle.SOURCE_KEYS) == 33, "raw source width drift")
    require(len(oracle.PROJECTED_KEYS) == 31 and len(oracle.HEADERS) == 32,
            "projected width drift")
    require([name for name, _left, _right in oracle.COLUMN_WINDOWS]
            == list(oracle.SOURCE_KEYS), "window/source order drift")
    require(all(left < right for _name, left, right in oracle.COLUMN_WINDOWS),
            "empty window admitted")
    require(all(oracle.COLUMN_WINDOWS[index][2]
                == oracle.COLUMN_WINDOWS[index + 1][1]
                for index in range(len(oracle.COLUMN_WINDOWS) - 1)),
            "window gap/overlap admitted")

    row, unassigned = oracle._assign_columns([
        glyph("A", 20), glyph("B", 21),
        glyph("1", 54), glyph("2", 55), glyph("3", 58),
        glyph("X", 454), glyph("9", 462), glyph("Y", 492),
    ])
    require(unassigned == 0, "valid glyph unassigned")
    require(row["location"] == "AB" and row["mi"] == "12 3"
            and row["adt_pp"] == "X" and row["adt_ahead"] == "9"
            and row["rec"] == "Y", "column assignment drift")
    _row, unassigned = oracle._assign_columns([glyph("X", 700)])
    require(unassigned == 1, "out-of-page glyph admitted")

    require(oracle._norm_route("1") == "001"
            and oracle._norm_route("5s") == "005S", "route normalization drift")
    rejected(lambda: oracle._norm_route("0001"), "overlong route")
    owner = oracle.GROUP_RE.fullmatch("01 MEN 101 U")
    require(owner is not None and owner.groups() == ("01", "MEN", "101", "U"),
            "four-token owner rejected")
    require(oracle.GROUP_RE.fullmatch("01 MEN 001") is not None,
            "three-token owner rejected")
    require(oracle.GROUP_RE.fullmatch("1 MEN 001") is None,
            "malformed owner admitted")

    volume = oracle._parse_total(
        "* * Volume Location Totals Length 000.070 DVM 212 "
        "County Cumulative DVM 212", 11.48)
    require(volume == {
        "kind": "volume_location", "length": "0.070", "dvm": 212,
        "county_cumulative_dvm": 212,
    }, "volume total parsing drift")
    signed = oracle._parse_total(
        "** ** CITY TOTALS (MILEAGE) TOTAL 000.000 CONST -002.100 "
        "UNCONST 002.100", 21.52)
    require(signed is not None and signed["kind"] == "mileage_summary"
            and signed["arithmetic_exact"], "signed mileage total rejected")
    fragment = oracle._parse_total("County Cumulative DVM 123,414", 297.8)
    require(fragment is not None
            and fragment["fragment_class"] == "county_cumulative_dvm_fragment",
            "volume fragment rejected")
    numeric_fragment = oracle._parse_total("089.826", 225.7)
    require(numeric_fragment is not None
            and numeric_fragment["fragment_class"] == "numeric_total_fragment",
            "numeric totals fragment rejected")
    volume_fragment = oracle._parse_total("Length 001.489 DVM 162,301", 143.832)
    require(volume_fragment is not None
            and volume_fragment["fragment_class"] == "volume_length_fragment"
            and volume_fragment["typed_numeric_or_overflow_tokens"]
            == ["1.489", 162301], "typed volume-length fragment rejected")
    require(oracle._parse_total("LENGTH PARTLY IN NEV CO", 73.4) is None
            and not oracle._total_candidate("LENGTH PARTLY IN NEV CO", 73.4),
            "authentic LENGTH Description swallowed as total")
    require(oracle._parse_total("53-1075", 73.4) is None
            and not oracle._total_candidate("53-1075", 73.4),
            "bridge description swallowed as total")
    require(oracle._parse_total("(DVMS) **********", 119.0)["kind"]
            == "total_fragment", "DVMS overflow rejected")
    require(oracle._parse_total("*** End of Report ***", 208.0)
            == {"kind": "end_of_report"}, "end marker rejected")
    require(oracle.DESCRIPTION_SEPARATOR_RE.fullmatch("-" * 23) is not None
            and oracle.DESCRIPTION_SEPARATOR_RE.fullmatch("-" * 22) is None
            and oracle.DESCRIPTION_SEPARATOR_RE.fullmatch("-" * 24) is None,
            "Description separator domain drift")
    require(oracle._parse_total("-" * 23, 73.4) is None
            and not oracle._total_candidate("-" * 23, 73.4),
            "Description separator conflated with total")

    record = base_record()
    projected = oracle._project_record(record)
    require(projected[0] == "001" and projected[2] == "000.075",
            "MI projection normalization drift")
    require(projected[16] == "36" and projected[26] == "24",
            "traveled-way projection normalization drift")
    require(projected[29] == "FIRST SECOND", "whitespace description join drift")
    production = oracle._project_record(record, production_join=True)
    require(production[29] == "FIRST, SECOND", "production join fixture drift")
    actual = [SimpleNamespace(source_row=2, values=production)]
    comparison = oracle._compare_projection([projected], actual)
    classified = oracle._classify_projection_residue(comparison, [record])
    require(comparison["typed_cell_mismatch_count"] == 1
            and classified["invented_description_comma"]["count"] == 1
            and classified["unexplained_count"] == 0,
            "description punctuation residue not exactly classified")
    bad_actual = list(production); bad_actual[1] = "999.999"
    bad = oracle._compare_projection(
        [projected], [SimpleNamespace(source_row=2, values=tuple(bad_actual))]
    )
    bad_classified = oracle._classify_projection_residue(bad, [record])
    require(bad["typed_cell_mismatch_count"] == 2
            and bad_classified["invented_description_comma"]["count"] == 1
            and bad_classified["unexplained_count"] == 1,
            "classified/unexplained mismatch accounting drift")

    require(oracle._roadbed_role(record) == "R", "left-ditto roadbed role drift")
    left = deepcopy(record)
    left["fields"]["lb_t"] = "H"; left["fields"]["rb_t"] = "+++"
    require(oracle._roadbed_role(left) == "L", "right-ditto roadbed role drift")
    combined = deepcopy(record)
    combined["fields"]["lb_t"] = "H"
    require(oracle._roadbed_role(combined) == "combined", "combined role drift")
    require(oracle._location_class("001.000") == "plain"
            and oracle._location_class("R001.000") == "leading_prefix"
            and oracle._location_class("R001.000E") == "equation_suffix",
            "location class drift")

    collisions = oracle._collision_summary([("a",), ("a",), ("b",)])
    require(collisions["duplicate_group_count"] == 1
            and collisions["rows_in_duplicate_groups"] == 2
            and collisions["max_multiplicity"] == 2,
            "collision census drift")
    require(oracle._ordered_digest([(None,)]) != oracle._ordered_digest([("",)]),
            "null/blank collapsed")
    require(oracle._ordered_digest([("a",), ("b",)])
            != oracle._ordered_digest([("b",), ("a",)]), "order mutation missed")
    require(oracle._multiset_digest([("a",), ("b",)])[0]
            == oracle._multiset_digest([("b",), ("a",)])[0],
            "multiset changed on reorder")

    dataset = oracle._dataset_digests(("First", "Second"), [(1, None), (2, "")])
    decisive_keys = (
        "row_count", "column_count", "headers_sha256",
        "ordered_typed_sha256", "multiset_typed_sha256",
    )
    dataset_expected = {key: dataset[key] for key in decisive_keys}
    require(all(oracle._dataset_contract(dataset, dataset_expected).values()),
            "valid frozen dataset contract rejected")
    for label, mutation in {
        "row count": {**dataset, "row_count": 3},
        "header": {**dataset, "headers": ["Changed", "Second"]},
        "ordered digest": {**dataset, "ordered_typed_sha256": "0" * 64},
        "multiset digest": {**dataset, "multiset_typed_sha256": "0" * 64},
        "extra schema": {**dataset, "unexpected": True},
    }.items():
        require(not all(oracle._dataset_contract(
            mutation, dataset_expected
        ).values()), f"dataset {label} mutation admitted")

    frozen_collisions = deepcopy(oracle.EXPECTED_COLLISION_CENSUS)
    require(oracle._collision_census_exact(frozen_collisions),
            "frozen collision census rejected")
    frozen_collisions["route_plus_printed_location"]["distinct_keys"] -= 1
    require(not oracle._collision_census_exact(frozen_collisions),
            "collision census mutation admitted")

    frozen_documents = deepcopy(oracle.EXPECTED_DOCUMENT_MANIFESTS)
    require(oracle._document_manifests_exact(frozen_documents),
            "frozen document manifests rejected")
    frozen_documents = list(frozen_documents)
    frozen_documents[0] = (*frozen_documents[0][:-1], "0" * 64)
    require(not oracle._document_manifests_exact(frozen_documents),
            "document manifest mutation admitted")

    parser_modules = oracle._loaded_module_manifest()
    require(all(oracle._validate_parser_module_manifest(
        parser_modules
    ).values()), "live parser-module manifest rejected")
    parser_mutations = {}
    missing_module = deepcopy(parser_modules); missing_module["members"].pop()
    parser_mutations["missing member"] = missing_module
    reordered_modules = deepcopy(parser_modules)
    reordered_modules["members"][0], reordered_modules["members"][1] = (
        reordered_modules["members"][1], reordered_modules["members"][0]
    )
    parser_mutations["member order"] = reordered_modules
    changed_module = deepcopy(parser_modules)
    changed_module["members"][0]["sha256"] = "0" * 64
    parser_mutations["member bytes"] = changed_module
    parser_mutations["root extra"] = {**parser_modules, "unexpected": True}
    for label, mutation in parser_mutations.items():
        require(not all(oracle._validate_parser_module_manifest(
            mutation, verify_files=False
        ).values()), f"parser-module {label} mutation admitted")

    coverage = oracle._field_coverage()
    require(coverage["exact"], "field coverage is not exact")
    require(set(oracle.FIELD_DISPOSITIONS) == set(oracle.RAW_ROLE_UNIVERSE)
            and len(oracle.RAW_ROLE_UNIVERSE) == 50,
            "independent raw-role universe drift")
    require(coverage["conditional_normalized_targets"] == ["Description"]
            and oracle.FIELD_DISPOSITIONS["DESCRIPTION"]["kind"] == "projected"
            and oracle.FIELD_DISPOSITIONS["DESCRIPTION_SEPARATOR"]["kind"]
            == "normalized_blank_marker", "Description role disposition drift")
    missing = deepcopy(oracle.FIELD_DISPOSITIONS); missing.pop("ADT_BACK")
    require(not oracle._field_coverage(missing)["exact"],
            "missing source-only disposition admitted")
    extra = deepcopy(oracle.FIELD_DISPOSITIONS)
    extra["INVENTED"] = oracle._disposition("source_only", (), "bad")
    require(not oracle._field_coverage(extra)["exact"], "extra disposition admitted")
    duplicate = deepcopy(oracle.FIELD_DISPOSITIONS)
    duplicate["ADT_BACK"] = oracle._disposition("source_only", ("Route",), "bad")
    require(not oracle._field_coverage(duplicate)["exact"],
            "duplicate normalized target admitted")
    bad_kind = deepcopy(oracle.FIELD_DISPOSITIONS); bad_kind["ADT_BACK"]["kind"] = "guess"
    require(not oracle._field_coverage(bad_kind)["exact"], "unknown disposition kind admitted")
    missing_separator = deepcopy(oracle.FIELD_DISPOSITIONS)
    missing_separator.pop("DESCRIPTION_SEPARATOR")
    require(not oracle._field_coverage(missing_separator)["exact"],
            "globally absent raw role admitted")
    blank_marker_without_target = deepcopy(oracle.FIELD_DISPOSITIONS)
    blank_marker_without_target["DESCRIPTION_SEPARATOR"]["normalized_targets"] = []
    require(not oracle._field_coverage(blank_marker_without_target)["exact"],
            "blank-marker target omission admitted")

    def claim(kind, page, line, owner=1, **values):
        return {
            "kind": kind, "member": "fixture.pdf", "district": "01",
            "county": "MEN", "route": "001", "route_qualifier": None,
            "owner_occurrence": owner, "physical_page": page,
            "printed_page": page - 1, "line": line, "top": "80.000",
            "x0": "10.000", "raw_text": values.pop("raw_text", kind),
            **values,
        }

    totals_fixture = [{"totals": [
        claim("volume_location", 2, 1, dvm=100, county_cumulative_dvm=100,
              length="1.000"),
        claim("volume_location", 2, 2, dvm=100, county_cumulative_dvm=199,
              length="1.000"),
        claim("volume_location", 2, 3, dvm=100, county_cumulative_dvm=300,
              length="1.000"),
        claim("volume_location", 2, 4, dvm=0, county_cumulative_dvm=0,
              length="1.000"),
        claim("volume_location", 2, 5, dvm=50, county_cumulative_dvm=50,
              length="1.000"),
        claim("volume_location", 2, 6, owner=2, dvm=9_999,
              county_cumulative_dvm=9_999, length="1.000"),
        claim("mileage_summary", 2, 7, owner=2, label="CITY TOTALS",
              total="1.000", constructed="1.000", unconstructed="0.000",
              arithmetic_exact=True),
        claim("volume_location", 3, 1, owner=2, dvm=1,
              county_cumulative_dvm=10_000, length="0.001"),
        claim("dvms_continuation", 4, 1, owner=2, dvms=10_000),
        claim("total_fragment", 4, 2, owner=2,
              fragment_class="volume_length_fragment",
              typed_numeric_or_overflow_tokens=["1.000", 10]),
        claim("volume_location", 4, 3, owner=2, dvm=10,
              county_cumulative_dvm=10_010, length="1.000"),
    ]}]
    reconciled = oracle._reconcile_totals(totals_fixture)
    require(reconciled["volume_progression_failure_count"] == 0
            and reconciled["volume_progression_delta_histogram"]
            == {-1: 1, 0: 2, 1: 1}
            and reconciled["volume_progression_reset_claim_count"] == 1,
            "owner/reset/rounding reconciliation drift")
    require(reconciled["mileage_to_dvms_pair_count"] == 1
            and reconciled["mileage_to_dvms_unpaired_summary_count"] == 0
            and reconciled["mileage_to_dvms_pairs"][0]["page_gap"] == 2
            and reconciled["volume_progression_fragment_obscured_interval_count"] == 1,
            "paginated DVMS/fragment reconciliation drift")
    failed_totals = deepcopy(totals_fixture)
    failed_totals[0]["totals"][2]["county_cumulative_dvm"] = 350
    require(oracle._reconcile_totals(failed_totals)
            ["volume_progression_failure_count"] == 1,
            "non-rounding cumulative failure admitted")
    cross_document = [
        {"totals": [claim("mileage_summary", 2, 1, label="CITY TOTALS",
                           total="1", constructed="1", unconstructed="0",
                           arithmetic_exact=True)]},
        {"totals": [claim("dvms_continuation", 2, 1, dvms=1)]},
    ]
    cross_result = oracle._reconcile_totals(cross_document)
    require(cross_result["mileage_to_dvms_pair_count"] == 0
            and cross_result["mileage_to_dvms_unpaired_summary_count"] == 1
            and cross_result[
                "mileage_to_dvms_unassociated_continuation_count"
            ] == 1
            and cross_result[
                "mileage_to_dvms_unassociated_continuation_kind_counts"
            ] == {"dvms_continuation": 1},
            "mileage/DVMS pairing crossed source documents")

    numeric_does_not_bind = [{"totals": [
        claim("mileage_summary", 2, 1, label="CITY TOTALS",
              total="1", constructed="1", unconstructed="0",
              arithmetic_exact=True),
        claim("total_fragment", 2, 2,
              fragment_class="numeric_total_fragment",
              typed_numeric_or_overflow_tokens=["89.826"]),
        claim("dvms_continuation", 2, 3, dvms=1),
    ]}]
    numeric_result = oracle._reconcile_totals(numeric_does_not_bind)
    require(numeric_result["mileage_to_dvms_pair_count"] == 1
            and numeric_result["mileage_to_dvms_pairs"][0]
            ["continuation_kind"] == "dvms_continuation"
            and numeric_result[
                "mileage_to_dvms_unassociated_continuation_count"
            ] == 0,
            "untyped numeric fragment consumed a DVMS continuation slot")

    frozen_totals = deepcopy(oracle.EXPECTED_TOTAL_RECONCILIATION)
    require(all(oracle._total_reconciliation_contract(
        frozen_totals
    ).values()), "frozen totals contract rejected")
    for label, key, value in (
        ("progression count", "volume_progression_assessable_interval_count", 0),
        ("rounding manifest", "volume_progression_rounding_manifest_sha256", "0" * 64),
        ("unassociated manifest",
         "mileage_to_dvms_unassociated_continuation_manifest_sha256", "0" * 64),
        ("pair manifest", "mileage_to_dvms_pair_manifest_sha256", "0" * 64),
    ):
        mutation = deepcopy(frozen_totals); mutation[key] = value
        require(not all(oracle._total_reconciliation_contract(
            mutation
        ).values()), f"totals {label} mutation admitted")

    limits = oracle._family_xlsx_limits()
    require(limits.max_source_bytes == 16 * 1024 * 1024
            and limits.max_xml_events == 20_000_000,
            "family XLSX limit drift")
    require(oracle.XlsxLimits().max_xml_events == 5_000_000,
            "default red-limit fixture drift")

    valid_metadata = {
        "Author": "Oracle Reports", "CreationDate": "D:20250915152304",
        "Creator": "Oracle12c AS Reports Services",
        "ModDate": "D:20250915152304", "Producer": "Oracle PDF driver",
        "Title": "otm52010.pdf",
    }
    claim = oracle.DOCUMENT_CLAIM_BINDINGS["D01 Highway Log TSN.pdf"]
    require(oracle._validate_pdf_metadata(valid_metadata, "fixture", claim)
            == valid_metadata, "valid metadata rejected")
    for label, mutation in {
        "missing": {key: value for key, value in valid_metadata.items() if key != "Author"},
        "wrong title": {**valid_metadata, "Title": "wrong.pdf"},
        "wrong member time": {**valid_metadata,
                              "CreationDate": "D:20250915152520",
                              "ModDate": "D:20250915152520"},
        "extra": {**valid_metadata, "Extra": "x"},
    }.items():
        rejected(lambda mutation=mutation: oracle._validate_pdf_metadata(
            mutation, "fixture", claim), f"metadata {label}")

    header_lines = [
        {"top": 3.0, "text": "OTM52010"},
        {"top": 13.0, "text": "Date09/15/25 California State Highway Log Page 1"},
        {"top": 32.0, "text": oracle.STATIC_PAGE_HEADER[2]},
        {"top": 42.0, "text": oracle.STATIC_PAGE_HEADER[3]},
        {"top": 51.0, "text": oracle.STATIC_PAGE_HEADER[4]},
        {"top": 70.0, "text": "01 MEN 001"},
    ]
    require(oracle._validate_page_header(header_lines, 2, "fixture")["printed_page"] == 1,
            "valid page header rejected")
    mutated_header = deepcopy(header_lines); mutated_header[1]["text"] = mutated_header[1]["text"].replace("Page 1", "Page 2")
    rejected(lambda: oracle._validate_page_header(mutated_header, 2, "fixture"),
             "wrong printed page")
    cover_lines = [{"text": text} for text in (
        "CALIFORNIA DEPARTMENT OF TRANSPORTATION", "California State Highway Log",
        "2025", "District 01",
    )]
    require(oracle._validate_cover(cover_lines, "01", "fixture")["line_count"] == 4,
            "valid cover rejected")
    rejected(lambda: oracle._validate_cover(cover_lines[:-1], "01", "fixture"),
             "missing cover role")

    source_names = [name for name, _size, _digest, _pages in oracle.RAW_BINDINGS]
    source, non_source = oracle._classify_raw_names(
        [*source_names, oracle.NON_SOURCE_BINDING[0]]
    )
    require(source == source_names and non_source == oracle.NON_SOURCE_BINDING[0],
            "raw roles classified incorrectly")
    rejected(lambda: oracle._classify_raw_names(source_names), "placeholder omitted")
    rejected(lambda: oracle._classify_raw_names(
        [*source_names, oracle.NON_SOURCE_BINDING[0], "extra.pdf"]), "extra raw role")

    raw_member_rows = [
        {"canonical_path": str(oracle.RAW_DIR / name), "size": size,
         "sha256": digest}
        for name, size, digest, _pages in oracle.RAW_BINDINGS
    ]
    sidecar = {
        "schema_version": 1,
        "completion": "complete",
        "skipped_inputs": 0,
        "failed_inputs": 0,
        "built_at_mtime": 1.25,
        "tsn_normalization_version": 4,
        "tsn_raw_manifest": {
            "version": 1,
            "algorithm": "sha256",
            "serialization": "relative_path\\tbyte_length\\tmember_sha256\\n",
            "root_scope": "report_raw_dir",
            "member_count": oracle.EXPECTED["members"],
            "byte_length": oracle.EXPECTED["raw_bytes"],
            "sha256": oracle.RAW_MANIFEST_SHA256,
            "members": [
                {"relative_path": name, "byte_length": size, "sha256": digest}
                for name, size, digest, _pages in oracle.RAW_BINDINGS
            ],
        },
        "tsn_normalized_workbook_identity": {
            "version": 1, "algorithm": "sha256",
            "byte_length": oracle.NORMALIZED_BINDING["bytes"],
            "sha256": oracle.NORMALIZED_BINDING["sha256"],
        },
        "tsn_artifact_identity_token": oracle.ARTIFACT_IDENTITY_TOKEN,
    }
    require(all(oracle._validate_sidecar(sidecar, raw_member_rows).values()),
            "exact sidecar rejected")
    sidecar_mutations = {}
    sidecar_mutations["root extra"] = {**sidecar, "extra": True}
    for label, key, value in (
        ("manifest algorithm", "algorithm", "sha512"),
        ("manifest serialization", "serialization", "json"),
        ("manifest root scope", "root_scope", "workspace"),
        ("manifest digest", "sha256", "0" * 64),
    ):
        mutation = deepcopy(sidecar)
        mutation["tsn_raw_manifest"][key] = value
        sidecar_mutations[label] = mutation
    sidecar_mutations["artifact token"] = {
        **sidecar, "tsn_artifact_identity_token": "wrong"
    }
    sidecar_mutations["build time type"] = {**sidecar, "built_at_mtime": 1}
    for label, mutation in sidecar_mutations.items():
        rejected(lambda mutation=mutation: oracle._validate_sidecar(
            mutation, raw_member_rows), f"sidecar {label}")

    require(oracle._accepted_terminal("complete"), "complete terminal rejected")
    for terminal in (True, False, None, "partial", "COMPLETE", 1):
        require(not oracle._accepted_terminal(terminal),
                f"invalid terminal admitted: {terminal!r}")

    rejected_result = {"payload": [["typed", None]]}
    try:
        oracle._finalize_invariant_result(
            rejected_result, {"first": True, "second": False}
        )
    except oracle.ConservationInvariantError as exc:
        require(exc.failed == ("second",), "failed invariant names drift")
        require(exc.diagnostic is rejected_result
                and rejected_result["accepted"] is False
                and rejected_result["stage6_family_audit_complete"] is False
                and rejected_result["terminal_status"] == "rejected_invariant_failure",
                "failed result can masquerade as accepted")
    else:
        raise AssertionError("failed invariant result admitted")
    accepted_result = {}
    require(oracle._finalize_invariant_result(
        accepted_result, {"only": True}) is accepted_result
        and accepted_result["accepted"] is True
        and accepted_result["failed_invariants"] == []
        and accepted_result["terminal_status"] == "accepted",
        "green invariant result rejected")
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        result_path = root / "accepted.json"
        acceptance_path = root / "accepted.json.acceptance.json"
        diagnostic_path = root / "accepted.json.diagnostic.json"
        result_path.write_text("result sentinel", encoding="utf-8")
        acceptance_path.write_text("acceptance sentinel", encoding="utf-8")
        identity = oracle._write_rejected_diagnostic(
            diagnostic_path,
            rejected_result,
            result_path=result_path,
            acceptance_path=acceptance_path,
        )
        require(identity.size > 0 and diagnostic_path.is_file(),
                "rejected diagnostic not published")
        require(result_path.read_text(encoding="utf-8") == "result sentinel"
                and acceptance_path.read_text(encoding="utf-8")
                == "acceptance sentinel",
                "diagnostic publication mutated accepted artifacts")
        rejected(lambda: oracle._write_rejected_diagnostic(
            result_path,
            rejected_result,
            result_path=result_path,
            acceptance_path=acceptance_path,
        ), "diagnostic/result path collision")

    manifest = json.loads(oracle.VISUAL_MANIFEST.read_text(encoding="utf-8"))
    require(oracle._validate_visual_manifest(manifest)["sample_count"] == 36,
            "valid visual manifest rejected")
    for label, mutation in {
        "missing sample": {**manifest, "samples": manifest["samples"][:-1]},
        "wrong page": deepcopy(manifest),
        "source swap": deepcopy(manifest),
        "image alias": deepcopy(manifest),
        "extra role": {**manifest, "unexpected": True},
    }.items():
        if label == "wrong page":
            mutation["samples"][0]["physical_page"] = 2
        elif label == "source swap":
            mutation["samples"][0]["source_sha256"] = "0" * 64
        elif label == "image alias":
            mutation["samples"][1]["image_sha256"] = mutation["samples"][0]["image_sha256"]
        rejected(lambda mutation=mutation: oracle._validate_visual_manifest(
            mutation, verify_files=False), f"visual {label}")

    print("PASS check_phase6_highway_log_conservation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

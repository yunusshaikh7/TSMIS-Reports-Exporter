"""Permanent synthetic gate for the independent HSL Stage-6 oracle."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_DIR))
import phase6_highway_sequence_conservation as oracle  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    # Independent line clustering must tolerate baseline jitter without mixing rows.
    words = [
        {"text": "MEN", "x0": 1.0, "top": 100.0},
        {"text": "001.000", "x0": 100.0, "top": 102.8},
        {"text": "UH", "x0": 170.0, "top": 101.2},
        {"text": "DESC", "x0": 280.0, "top": 101.0},
        {"text": "NEXT", "x0": 1.0, "top": 110.0},
    ]
    lines = oracle._cluster_words(words)
    require(len(lines) == 2 and len(lines[0]) == 4, "top clustering drift")
    buckets = oracle._bucket_words(lines[0])
    require(buckets == {"County": ["MEN"], "PM": ["001.000"],
                        "Flag": ["UH"], "Description": ["DESC"]},
            "column bucket drift")

    group = oracle.GROUP_RE.search("DIST 09 RTE 14 DIR W-E")
    require(group is not None and oracle._norm_route(group.group(2)) == "014"
            and group.group(3) == "W-E", "owner parsing drift")
    for token in ("000.000", "R012.887", "050.025E"):
        require(oracle.LOCATION_RE.fullmatch(token) is not None, f"PM rejected: {token}")
    require(oracle.LOCATION_RE.fullmatch("12.887") is None, "malformed PM admitted")

    base = {
        "district": "01", "route": "001", "direction": "S-N",
        "county": "MEN", "pm": "001.000", "city": None, "hg": "U",
        "ft": "H", "distance": "*P*", "description": "A B", "kind": "data",
    }
    require(oracle._project_record(base)[6] == "*P*", "pointer was coerced")
    unknown = {**base, "kind": "equate", "county": None,
               "distance": None, "description": "EQUATES TO"}
    require(oracle._project_record(unknown) is None, "unknown owner was invented")

    # Typed and order digests must distinguish every critical mutation.
    rows = [oracle._source_row(base), oracle._source_row(unknown)]
    require(oracle._ordered_digest(rows) != oracle._ordered_digest(list(reversed(rows))),
            "order mutation missed")
    require(oracle._multiset_digest(rows)[0]
            == oracle._multiset_digest(list(reversed(rows)))[0],
            "multiset changed on reorder")
    require(oracle._ordered_digest([(None,)]) != oracle._ordered_digest([("",)]),
            "null/blank collapsed")
    require(oracle._ordered_digest([("*P*",)]) != oracle._ordered_digest([(None,)]),
            "pointer/null collapsed")

    identity = oracle.FileIdentity("C:\\bound\\x", 10, 1, 2, 3, "a" * 64)
    volatile = replace(identity, mtime_ns=999, device=888, inode=777)
    require(oracle._stable_identity(identity) == oracle._stable_identity(volatile),
            "volatile filesystem metadata leaked into acceptance")
    require(oracle._stable_identity(identity)
            != oracle._stable_identity(replace(identity, size=11)),
            "size drift missed by stable identity")
    require(oracle._stable_identity(identity)
            != oracle._stable_identity(replace(identity, sha256="b" * 64)),
            "hash drift missed by stable identity")

    coverage = oracle._field_coverage()
    require(coverage["exact"], "field coverage is not exact")
    missing = deepcopy(oracle.FIELD_DISPOSITIONS); missing.pop("DISTANCE")
    require(not oracle._field_coverage(missing)["exact"], "missing disposition admitted")
    extra = deepcopy(oracle.FIELD_DISPOSITIONS); extra["INVENTED"] = deepcopy(extra["PM"])
    require(not oracle._field_coverage(extra)["exact"], "extra disposition admitted")
    bad = deepcopy(oracle.FIELD_DISPOSITIONS); bad["PM"]["kind"] = "guess"
    require(not oracle._field_coverage(bad)["exact"], "bad disposition kind admitted")

    source_names = [name for name, _size, _digest in oracle.RAW_BINDINGS]
    require(set(oracle.DOCUMENT_CLAIM_BINDINGS) == set(source_names),
            "per-member document binding universe differs from raw truth roles")
    source, non_source = oracle._classify_raw_names(
        [*source_names, *oracle.NON_SOURCE_NAMES]
    )
    require(source == source_names and non_source == list(oracle.NON_SOURCE_NAMES),
            "raw roles classified incorrectly")
    for invalid in (
        source_names,
        [*source_names[:-1], *oracle.NON_SOURCE_NAMES],
        [*source_names, *oracle.NON_SOURCE_NAMES, "unexpected.xlsx"],
    ):
        try:
            oracle._classify_raw_names(invalid)
        except oracle.ConservationError:
            pass
        else:
            raise AssertionError(f"invalid raw role universe admitted: {invalid[-1:]}")

    require(oracle._accepted_terminal("complete"), "complete terminal rejected")
    for invalid_terminal in (True, False, None, "partial", "COMPLETE", 1):
        require(not oracle._accepted_terminal(invalid_terminal),
                f"invalid acceptance terminal admitted: {invalid_terminal!r}")

    counters = {}
    owner_a = ("01", "001", "S-N")
    owner_b = ("01", "020", "W-E")
    require(oracle._advance_printed_page(counters, owner_a, 1) == 1
            and oracle._advance_printed_page(counters, owner_a, 2) == 2
            and oracle._advance_printed_page(counters, owner_b, 1) == 1,
            "per-owner pagination reset rejected")
    for owner, printed in ((owner_a, 4), (owner_b, 1), (("02", "020", "W-E"), 2)):
        trial = dict(counters)
        try:
            oracle._advance_printed_page(trial, owner, printed)
        except oracle.ConservationError:
            pass
        else:
            raise AssertionError(f"bad printed-page claim admitted: {owner}/{printed}")

    valid_header = [
        "OTM22025 CALIFORNIA DEPARTMENT OF TRANSPORTATION Page 1",
        "15-SEP-25 Highway Locations Ref Dt 15 SEP 2025",
        "01:05 PM",
        "DIST 01 RTE 001 DIR S-N",
        "CO. CITY POSTMILE G RF DISTANCE TO NXT POINT DESCRIPTION",
    ]
    parsed_header = oracle._exact_page_header(valid_header, "01", "01:05 PM")
    require(parsed_header["owner"] == owner_a
            and parsed_header["report_date"] == "15-SEP-25"
            and parsed_header["reference_date"] == "15 SEP 2025"
            and parsed_header["printed_page"] == 1,
            "exact page header rejected")
    invalid_headers = {
        "missing report id": [valid_header[0].replace("OTM22025 ", ""), *valid_header[1:]],
        "duplicate report id": [valid_header[0] + " OTM22025", *valid_header[1:]],
        "wrong report id": [valid_header[0].replace("OTM22025", "OTM22026"), *valid_header[1:]],
        "missing title": [valid_header[0], valid_header[1].replace(" Highway Locations", ""), *valid_header[2:]],
        "duplicate title": [valid_header[0], valid_header[1] + " Highway Locations", *valid_header[2:]],
        "wrong title": [valid_header[0], valid_header[1].replace("Highway Locations", "Highway Location"), *valid_header[2:]],
        "missing report date": [valid_header[0], valid_header[1].replace("15-SEP-25 ", ""), *valid_header[2:]],
        "duplicate report date": [valid_header[0], valid_header[1] + " 15-SEP-25", *valid_header[2:]],
        "wrong report date": [valid_header[0], valid_header[1].replace("15-SEP-25", "16-SEP-25"), *valid_header[2:]],
        "missing reference date": [valid_header[0], valid_header[1].replace(" Ref Dt 15 SEP 2025", ""), *valid_header[2:]],
        "duplicate reference date": [valid_header[0], valid_header[1] + " Ref Dt 15 SEP 2025", *valid_header[2:]],
        "wrong reference date": [valid_header[0], valid_header[1].replace("15 SEP 2025", "16 SEP 2025"), *valid_header[2:]],
        "missing generation time": [*valid_header[:2], *valid_header[3:]],
        "duplicate generation time": [*valid_header[:3], "01:05 PM", *valid_header[3:]],
        "wrong valid generation time": [*valid_header[:2], "01:06 PM", *valid_header[3:]],
        "missing printed page": [valid_header[0].replace(" Page 1", ""), *valid_header[1:]],
        "duplicate printed page": [valid_header[0].replace("Page 1", "Page 1 Page 1"), *valid_header[1:]],
        "missing owner": [*valid_header[:3], *valid_header[4:]],
        "duplicate owner": [*valid_header, "DIST 01 RTE 001 DIR S-N"],
        "wrong owner district": [*valid_header[:3], "DIST 02 RTE 001 DIR S-N", *valid_header[4:]],
        "malformed owner": [*valid_header[:3], "DIST 01 RTE 001 DIR X-X", *valid_header[4:]],
    }
    for label, invalid_header in invalid_headers.items():
        try:
            oracle._exact_page_header(invalid_header, "01", "01:05 PM")
        except oracle.ConservationError:
            pass
        else:
            raise AssertionError(f"invalid exact page header admitted ({label}): {invalid_header}")

    valid_metadata = {
        "Creator": "Oracle12c AS Reports Services",
        "CreationDate": "D:20250915130517",
        "ModDate": "D:20250915130517",
        "Producer": "Oracle PDF driver",
        "Title": "otm22025.pdf",
        "Author": "Oracle Reports",
    }
    require(oracle._validate_pdf_metadata(
        valid_metadata, "fixture", "D:20250915130517", "D:20250915130517"
    ) == valid_metadata,
            "valid PDF metadata rejected")
    d12_metadata = {
        **valid_metadata,
        "CreationDate": "D:20250915150325Z",
        "ModDate": "D:20251121111252-08'00'",
    }
    require(oracle._validate_pdf_metadata(
        d12_metadata, "D12 fixture", "D:20250915150325Z",
        "D:20251121111252-08'00'"
    ) == d12_metadata, "authentic D12 metadata suffix rejected")
    for label, mutation in {
        "collapsed D12 pair": {
            **d12_metadata,
            "ModDate": d12_metadata["CreationDate"],
        },
        "swapped D12 pair": {
            **d12_metadata,
            "CreationDate": d12_metadata["ModDate"],
            "ModDate": d12_metadata["CreationDate"],
        },
    }.items():
        try:
            oracle._validate_pdf_metadata(
                mutation, "D12 fixture", "D:20250915150325Z",
                "D:20251121111252-08'00'"
            )
        except oracle.ConservationError:
            pass
        else:
            raise AssertionError(f"invalid D12 metadata admitted ({label}): {mutation}")
    metadata_mutations = {
        **{
            f"missing {key}": {
                item_key: item_value
                for item_key, item_value in valid_metadata.items()
                if item_key != key
            }
            for key in valid_metadata
        },
        "wrong Creator": {**valid_metadata, "Creator": "Wrong"},
        "wrong Producer": {**valid_metadata, "Producer": "Wrong"},
        "wrong Title": {**valid_metadata, "Title": "Wrong"},
        "wrong Author": {**valid_metadata, "Author": "Wrong"},
        "wrong ModDate": {**valid_metadata, "ModDate": "D:20250915130518"},
        "wrong-format CreationDate": {**valid_metadata, "CreationDate": "D:20250916"},
        "valid-looking wrong-member CreationDate": {
            **valid_metadata,
            "CreationDate": "D:20250915130917",
            "ModDate": "D:20250915130917",
        },
        "extra metadata role": {**valid_metadata, "Extra": "x"},
    }
    for label, mutation in metadata_mutations.items():
        try:
            oracle._validate_pdf_metadata(
                mutation, "fixture", "D:20250915130517", "D:20250915130517"
            )
        except oracle.ConservationError:
            pass
        else:
            raise AssertionError(f"invalid PDF metadata admitted ({label}): {mutation}")

    projected = [oracle._project_record(base)]
    probes = oracle._mutation_probes(rows * 2, projected, "metadata")
    require(probes["all_detected"] and probes["detected_count"] == probes["probe_count"],
            "semantic mutation suite incomplete")

    print("PASS check_phase6_highway_sequence_conservation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Independent Stage-6 raw-to-normalized Ramp Detail conservation oracle.

This audit intentionally imports no application parser, normalizer, comparator,
schema, evidence adapter, or report constant.  It reads both XLSX files through
the generic stdlib-only OOXML reader in :mod:`phase3_xlsx_stream`, applies a
separately declared Ramp source contract, and explains every one of the 18 raw
fields.

The current accepted inputs are bound below.  A different source or normalized
generation is rejected unless the caller explicitly supplies the corresponding
expected SHA-256 and byte length.  The result separates exact projection parity
from full conservation: a workbook can reproduce all currently emitted cells
while still omitting a physical identity claim such as ``PM_SFX``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree
import zipfile

from phase3_xlsx_stream import (DATE, SCALAR, ColumnSpec, FileIdentity,
                                SheetSpec, StreamedSheet, capture_file_bytes,
                                capture_file_identity, read_sheet)


RAW_DEFAULT = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\ramp_detail\raw"
    r"\TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx")
NORMALIZED_DEFAULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7\ramp_detail\consolidated"
    r"\tsn_ramp_detail_normalized.xlsx")

RAW_BINDING = {
    "bytes": 1_590_431,
    "sha256": "3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856",
    "sheet": "Sheet 1",
    "rows": 15_410,
    "columns": 18,
}
NORMALIZED_R7_BINDING = {
    "bytes": 1_009_829,
    "sha256": "c121a9ca1bed2fad00bfc4b08bfc68fa01cd46da436d6bffa699c5579bb4f5f1",
    "sheet": "Ramp Detail (TSN)",
    "rows": 15_410,
    "columns": 15,
    "normalization_version": 3,
}
R7_WITNESS_RESULT = NORMALIZED_DEFAULT.parents[2] / "result.json"
R7_WITNESS_BINDING = {
    "bytes": 173_124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}
R7_NORMALIZED_SIDECAR = Path(str(NORMALIZED_DEFAULT) + ".outcome.json")
R7_NORMALIZED_SIDECAR_BINDING = {
    "bytes": 910,
    "sha256": "980ccd48f0c15438547b32fbb31050329fd11c94a1f199156c3b3a664f82f5b0",
}
GENERATOR_START_IDENTITY = capture_file_identity(Path(__file__))
READER_PATH = Path(__file__).with_name("phase3_xlsx_stream.py")
READER_START_IDENTITY = capture_file_identity(READER_PATH)

RAW_HEADERS = (
    "RAM_CONNECTION_ID",
    "RAMP_NANE",
    "LOCATION",
    "PR",
    "PM",
    "PM_SFX",
    "DATE_OF_RECORD",
    "HG",
    "AREA_4",
    "CITY_CODE",
    "POP",
    "ON_OFF",
    "ADT_EFF_YEAR",
    "ADT",
    "RAMP_TYPE",
    "EFF_DATE",
    "DESCRIPTION",
    "SEG_ORDER_ID",
)
NORMALIZED_HEADERS = (
    "Route",
    "PR",
    "PM",
    "Date of Record",
    "HG",
    "Area 4",
    "City Code",
    "R/U",
    "Description",
    "Ramp Name",
    "On/Off",
    "Ramp Type",
    "ADT",
    "TSN District",
    "TSN County",
)

EXPECTED_DESCRIPTION_LOSSES = (
    (11, "101", "101/169 NB OFF RAMP", "169 NB OFF RAMP"),
    (12, "101", "101/169 SB ON RAMP", "169 SB ON RAMP"),
    (13, "101", "101/169 NB ON RAMP", "169 NB ON RAMP"),
    (14, "101", "101/169 SB OFF RAMP", "169 SB OFF RAMP"),
    (299, "101", "101/222 SEP NB OFF", "222 SEP NB OFF"),
    (300, "101", "101/222 SEP SB ON", "222 SEP SB ON"),
    (305, "101", "101/222 SEP SB OFF", "222 SEP SB OFF"),
    (588, "005", "5/89 SEP 2-WAY SEG", "89 SEP 2-WAY SEG"),
    (1998, "505", "128/RUSSELL BL, SB ON", "RUSSELL BL, SB ON"),
    (2001, "505", "128/RUSSELL, SB OFF", "RUSSELL, SB OFF"),
    (3243, "101", "131/TIBURON BL, NB OFF", "TIBURON BL, NB OFF"),
    (5684, "101", "166/E MAIN ST, SB OFF", "E MAIN ST, SB OFF"),
    (9519, "210", "66/FOOTHILL WB,WB ON", "FOOTHILL WB,WB ON"),
    (9603, "405", "405/NB ON SEG SANTA FE", "NB ON SEG SANTA FE"),
    (10815, "015", "74/CENTRAL, SB OFF", "CENTRAL, SB OFF"),
)

# Every raw field has one explicit disposition.  ``source_only`` means the
# Stage-6 result binds/digests the fact but the normalized workbook does not
# carry it.  That is not silently treated as projection coverage.
FIELD_DISPOSITIONS = {
    "RAM_CONNECTION_ID": {
        "kind": "source_only",
        "role": "database record identifier",
        "normalized_targets": [],
    },
    "RAMP_NANE": {
        "kind": "projected",
        "role": "context value (source header spelling is literal)",
        "normalized_targets": ["Ramp Name"],
    },
    "LOCATION": {
        "kind": "composed",
        "role": "district/county/route physical location",
        "normalized_targets": ["Route", "TSN District", "TSN County"],
    },
    "PR": {
        "kind": "projected",
        "role": "postmile prefix / ramp identity",
        "normalized_targets": ["PR"],
    },
    "PM": {
        "kind": "composed",
        "role": "canonical postmile / ramp identity",
        "normalized_targets": ["PM"],
    },
    "PM_SFX": {
        "kind": "relational",
        "role": "postmile suffix / ramp physical identity",
        "normalized_targets": [],
        "normalized_requirement": "retain_independent_typed_identity_claim",
        "blocking_note": (
            "The current normalized schema cannot independently reconstruct "
            "this identity claim.  Equality with HG in the bound corpus is an "
            "observed source coincidence, not a universal schema contract."
        ),
    },
    "DATE_OF_RECORD": {
        "kind": "composed",
        "role": "record date canonicalized to ISO date",
        "normalized_targets": ["Date of Record"],
    },
    "HG": {
        "kind": "projected",
        "role": "highway group",
        "normalized_targets": ["HG"],
    },
    "AREA_4": {
        "kind": "projected",
        "role": "area",
        "normalized_targets": ["Area 4"],
    },
    "CITY_CODE": {
        "kind": "projected",
        "role": "city code",
        "normalized_targets": ["City Code"],
    },
    "POP": {
        "kind": "projected",
        "role": "rural/urban classification",
        "normalized_targets": ["R/U"],
    },
    "ON_OFF": {
        "kind": "projected",
        "role": "on/off context",
        "normalized_targets": ["On/Off"],
    },
    "ADT_EFF_YEAR": {
        "kind": "source_only",
        "role": "effective year qualifying ADT; printed by the accepted TSN PDF",
        "normalized_targets": [],
        "normalized_requirement": "retain_for_print_evidence_and_context",
    },
    "ADT": {
        "kind": "projected",
        "role": "traffic context",
        "normalized_targets": ["ADT"],
    },
    "RAMP_TYPE": {
        "kind": "projected",
        "role": "ramp type context",
        "normalized_targets": ["Ramp Type"],
    },
    "EFF_DATE": {
        "kind": "source_only",
        "role": "effective date printed by the accepted TSN PDF",
        "normalized_targets": [],
        "normalized_requirement": "retain_for_print_evidence_and_context",
    },
    "DESCRIPTION": {
        "kind": "composed",
        "role": "description with an optional numeric route prefix removed",
        "normalized_targets": ["Description"],
    },
    "SEG_ORDER_ID": {
        "kind": "relational",
        "role": "source ordering identifier",
        "normalized_targets": [],
        "normalized_requirement": "prove_order_relation_and_digest",
    },
}

OMITTED_FIELDS = tuple(
    name for name in RAW_HEADERS if not FIELD_DISPOSITIONS[name]["normalized_targets"])
LOCATION_RE = re.compile(r"^(\d{2})-([A-Z]{2,3}\.?)-(\d+)([A-Z]?)$")
ROUTE_RE = re.compile(r"^(\d+)([A-Z]?)$")
PM_RE = re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$")
DESC_PREFIX_RE = re.compile(r"^\s*(\d+)\s*/\s*")


class ConservationError(ValueError):
    """The bound source or conservation contract was not satisfied."""


def _typed(value: object) -> list[object]:
    """Lossless JSON form that never folds unlike scalar types together."""
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        t = value.as_tuple()
        return ["decimal", t.sign, list(t.digits), t.exponent]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat(sep=" ")]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value.hex()]
    raise TypeError(f"unsupported typed scalar: {type(value).__name__}")


def _wire(value: object) -> bytes:
    return json.dumps(_typed(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _row_wire(row: Sequence[object]) -> bytes:
    return json.dumps([_typed(value) for value in row], ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ordered_digest(rows: Iterable[Sequence[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        payload = _row_wire(row)
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b":")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _multiset_digest(rows: Iterable[Sequence[object]]) -> tuple[str, Counter[str]]:
    counts = Counter(_sha(_row_wire(row)) for row in rows)
    digest = hashlib.sha256()
    for row_digest, count in sorted(counts.items()):
        digest.update(f"{row_digest}\t{count}\n".encode("ascii"))
    return digest.hexdigest(), counts


def _field_digest(values: Sequence[object]) -> dict[str, object]:
    ordered = hashlib.sha256()
    counts: Counter[str] = Counter()
    types: Counter[str] = Counter()
    nulls = blanks = 0
    for value in values:
        payload = _wire(value)
        ordered.update(str(len(payload)).encode("ascii"))
        ordered.update(b":")
        ordered.update(payload)
        ordered.update(b"\n")
        counts[_sha(payload)] += 1
        types[_typed(value)[0]] += 1
        nulls += value is None
        blanks += value == ""
    multiset = hashlib.sha256()
    for value_digest, count in sorted(counts.items()):
        multiset.update(f"{value_digest}\t{count}\n".encode("ascii"))
    return {
        "ordered_typed_sha256": ordered.hexdigest(),
        "multiset_typed_sha256": multiset.hexdigest(),
        "distinct_typed_values": len(counts),
        "type_counts": dict(sorted(types.items())),
        "null_count": nulls,
        "empty_string_count": blanks,
    }


def _dataset_digests(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> dict[str, object]:
    multiset, counts = _multiset_digest(rows)
    return {
        "row_count": len(rows),
        "column_count": len(headers),
        "headers": list(headers),
        "ordered_typed_row_sha256": _ordered_digest(rows),
        "multiset_typed_row_sha256": multiset,
        "distinct_typed_rows": len(counts),
        "duplicate_typed_row_groups": sum(count > 1 for count in counts.values()),
        "duplicate_typed_row_occurrences_beyond_first": sum(count - 1 for count in counts.values()),
        "fields": {
            header: _field_digest([row[index] for row in rows])
            for index, header in enumerate(headers)
        },
    }


def _identity_dict(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _workbook_topology(path: Path) -> dict[str, object]:
    """Bind topology from a private immutable compressed-byte capture."""
    captured = capture_file_bytes(path)
    with zipfile.ZipFile(io.BytesIO(captured.payload), "r") as archive:
        members = [info for info in archive.infolist()
                   if info.filename == "xl/workbook.xml"]
        if len(members) != 1:
            raise ConservationError("workbook topology member is missing or duplicated")
        member = members[0]
        if member.file_size > 4 * 1024 * 1024:
            raise ConservationError("workbook topology member exceeds the size limit")
        if member.file_size and member.file_size / max(member.compress_size, 1) > 2_000:
            raise ConservationError("workbook topology member exceeds the ratio limit")
        workbook_xml = archive.read(member)
    if b"<!DOCTYPE" in workbook_xml.upper() or b"<!ENTITY" in workbook_xml.upper():
        raise ConservationError("workbook topology contains a forbidden DTD/entity")
    root = ElementTree.fromstring(workbook_xml)
    sheets = []
    date1904 = False
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1]
        if local == "workbookPr":
            date1904 = element.attrib.get("date1904", "0") in ("1", "true", "True")
        elif local == "sheet":
            sheets.append({
                "name": element.attrib.get("name"),
                "state": element.attrib.get("state", "visible"),
            })
    identity = captured.identity
    stat_token = [identity.size, identity.mtime_ns, identity.device, identity.inode]
    return {
        "sheets": sheets,
        "date_system": "1904" if date1904 else "1900",
        "pre_sha256": identity.sha256,
        "post_sha256": identity.sha256,
        "size": identity.size,
        "pre_stat": stat_token,
        "bound_stat": stat_token,
        "post_stat": stat_token,
        "capture_identity": _identity_dict(identity),
    }


def _require_binding(sheet: StreamedSheet, topology: dict[str, object], binding: dict[str, object],
                     label: str) -> None:
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    observed = (sheet.pre_identity.size, sheet.pre_identity.sha256)
    if observed != expected:
        raise ConservationError(f"{label} binding mismatch: {observed!r} != {expected!r}")
    if sheet.pre_identity != sheet.post_identity:
        raise ConservationError(f"{label} changed during worksheet read")
    if topology["pre_sha256"] != expected[1] or topology["post_sha256"] != expected[1]:
        raise ConservationError(f"{label} topology read used different bytes")
    expected_sheets = [{"name": binding["sheet"], "state": "visible"}]
    if topology["sheets"] != expected_sheets:
        raise ConservationError(
            f"{label} workbook topology mismatch: {topology['sheets']!r} != {expected_sheets!r}")


def _require_identity_binding(identity: FileIdentity, binding: dict[str, object],
                              label: str) -> None:
    observed = (identity.size, identity.sha256)
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    if observed != expected:
        raise ConservationError(f"{label} binding mismatch: {observed!r} != {expected!r}")


def _scalar(value: object) -> object:
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        if value.time() == time():
            return value.date().isoformat()
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return value


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _parse_location(value: object) -> tuple[str, str, str, dict[str, object]]:
    literal = _text(value).strip().upper()
    match = LOCATION_RE.fullmatch(literal)
    if match is None:
        raise ConservationError(f"invalid Ramp LOCATION token: {literal!r}")
    district, county_token, route_digits, suffix = match.groups()
    county = county_token.rstrip(".")
    route = f"{int(route_digits):03d}{suffix}"
    return district, county, route, {
        "literal": literal,
        "county_had_trailing_period": county_token.endswith("."),
        "route_source_digits": route_digits,
    }


def _norm_pm(value: object) -> str:
    literal = _text(value).strip()
    if not literal:
        return ""
    if not PM_RE.fullmatch(literal):
        raise ConservationError(f"invalid Ramp PM token: {literal!r}")
    negative = literal.startswith("-")
    core = literal.lstrip("-").lstrip("0") or "0"
    if core.startswith("."):
        core = "0" + core
    return ("-" if negative else "") + core


def _iso_record_date(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    literal = str(value).strip()
    for pattern in (
            re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?$"),
            re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")):
        match = pattern.fullmatch(literal)
        if match is None:
            continue
        if pattern.pattern.startswith("^(\\d{4})"):
            year, month, day = match.groups()
        else:
            month, day, year = match.groups()
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError as exc:
            raise ConservationError(
                f"invalid Ramp DATE_OF_RECORD token: {literal!r}") from exc
    match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{2})", literal)
    if match:
        year, month, day = map(int, match.groups())
        year += 1900 if year >= 30 else 2000
        try:
            return date(year, month, day).isoformat()
        except ValueError as exc:
            raise ConservationError(
                f"invalid Ramp DATE_OF_RECORD token: {literal!r}") from exc
    raise ConservationError(f"invalid Ramp DATE_OF_RECORD token: {literal!r}")


def _normalize_description(value: object) -> str:
    """Conserve the authoritative raw TSN Description.

    A leading numeric token belongs to the raw source even when it numerically
    equals the outer route parsed from ``LOCATION``.  The TSMIS representation
    has a separate, synthetic outer-route prefix; removing that TSMIS-only layer
    is a comparison-side operation and cannot justify altering raw TSN data.
    """
    return _text(value).strip()


def _project_raw_row(row: Sequence[object]) -> tuple[tuple[object, ...], dict[str, object]]:
    values = dict(zip(RAW_HEADERS, row))
    district, county, route, location_info = _parse_location(values["LOCATION"])
    projected = (
        route,
        _scalar(values["PR"]),
        _norm_pm(values["PM"]),
        _iso_record_date(values["DATE_OF_RECORD"]),
        _scalar(values["HG"]),
        _scalar(values["AREA_4"]),
        _scalar(values["CITY_CODE"]),
        _scalar(values["POP"]),
        _normalize_description(values["DESCRIPTION"]),
        _scalar(values["RAMP_NANE"]),
        _scalar(values["ON_OFF"]),
        _scalar(values["RAMP_TYPE"]),
        _scalar(values["ADT"]),
        district,
        county,
    )
    suffix = _text(values["PM_SFX"]).strip().upper()
    physical_identity = (district, county, route, _scalar(values["PR"]),
                         _norm_pm(values["PM"]), suffix)
    return projected, {
        "district": district,
        "county": county,
        "route": route,
        "pm": _norm_pm(values["PM"]),
        "pm_suffix": suffix,
        "physical_identity": physical_identity,
        "location_info": location_info,
    }


def _counter_summary(counter: Counter[tuple[object, ...]]) -> dict[str, int]:
    groups = [count for count in counter.values() if count > 1]
    return {
        "distinct": len(counter),
        "duplicate_groups": len(groups),
        "duplicate_occurrences_beyond_first": sum(count - 1 for count in groups),
        "largest_multiplicity": max(groups, default=1),
    }


def _collision_census(raw_rows: Sequence[Sequence[object]],
                      projected_rows: Sequence[Sequence[object]],
                      row_info: Sequence[dict[str, object]]) -> dict[str, object]:
    full = Counter(tuple(info["physical_identity"]) for info in row_info)
    weak_route_pm: dict[tuple[object, ...], set[str]] = defaultdict(set)
    strong_without_county: dict[tuple[object, ...], set[str]] = defaultdict(set)
    without_suffix = Counter()
    for row, info in zip(raw_rows, row_info):
        values = dict(zip(RAW_HEADERS, row))
        route_pm = (info["route"], info["pm"])
        strong = (info["route"], _scalar(values["PR"]), info["pm"], info["pm_suffix"])
        weak_route_pm[route_pm].add(str(info["county"]))
        strong_without_county[strong].add(str(info["county"]))
        without_suffix[(info["district"], info["county"], info["route"],
                        _scalar(values["PR"]), info["pm"])] += 1

    def county_collisions(groups: dict[tuple[object, ...], set[str]]) -> dict[str, int]:
        selected = [counties for counties in groups.values() if len(counties) > 1]
        return {
            "cross_county_keys": len(selected),
            "county_specific_identities": sum(len(counties) for counties in selected),
            "largest_county_multiplicity": max((len(c) for c in selected), default=1),
        }

    raw_exact = Counter(_sha(_row_wire(row)) for row in raw_rows)
    projected = Counter(_sha(_row_wire(row)) for row in projected_rows)
    omitted_indices = tuple(RAW_HEADERS.index(field) for field in OMITTED_FIELDS)
    omitted_by_projection: dict[str, set[bytes]] = defaultdict(set)
    occurrence_by_projection: Counter[str] = Counter()
    for raw, normalized in zip(raw_rows, projected_rows):
        key = _sha(_row_wire(normalized))
        omitted_by_projection[key].add(
            _row_wire(tuple(raw[index] for index in omitted_indices)))
        occurrence_by_projection[key] += 1
    lossy = [
        (key, occurrence_by_projection[key], len(source_values))
        for key, source_values in omitted_by_projection.items()
        if occurrence_by_projection[key] > 1 and len(source_values) > 1
    ]
    return {
        "physical_identity": _counter_summary(full),
        "identity_without_pm_suffix": _counter_summary(without_suffix),
        "route_plus_pm_cross_county": county_collisions(weak_route_pm),
        "route_pr_pm_suffix_cross_county": county_collisions(strong_without_county),
        "exact_raw_rows": _counter_summary(raw_exact),
        "projected_rows": _counter_summary(projected),
        "projected_collision_groups_with_distinct_omitted_facts": len(lossy),
        "projected_collision_occurrences": sum(count for _key, count, _distinct in lossy),
        "projected_collision_distinct_source_fact_sets": sum(distinct for _key, _count, distinct in lossy),
    }


def _order_and_anomalies(raw_sheet: StreamedSheet, raw_rows: Sequence[Sequence[object]],
                         normalized_sheet: StreamedSheet,
                         projected_rows: Sequence[Sequence[object]],
                         row_info: Sequence[dict[str, object]]) -> dict[str, object]:
    raw_numbers = [row.source_row for row in raw_sheet.rows]
    normalized_numbers = [row.source_row for row in normalized_sheet.rows]
    suffix_counts: Counter[str] = Counter()
    suffix_hg_mismatch = []
    hg_lr_without_suffix = 0
    nonmidnight_record_dates = 0
    description_numeric_prefixes = []
    description_equal_outer_route_count = 0
    location_periods = 0
    seg_by_route: dict[tuple[str, str, str], list[Decimal]] = defaultdict(list)
    seg_invalid = 0
    adt_eff_years: Counter[str] = Counter()
    eff_date_mismatch_count = 0
    for source_row, raw, info in zip(raw_numbers, raw_rows, row_info):
        values = dict(zip(RAW_HEADERS, raw))
        suffix = info["pm_suffix"]
        suffix_counts[suffix] += 1
        hg = _text(values["HG"]).strip().upper()
        if suffix and suffix != hg:
            suffix_hg_mismatch.append({"source_row": source_row, "pm_suffix": suffix, "hg": hg})
        if not suffix and hg in {"L", "R"}:
            hg_lr_without_suffix += 1
        if isinstance(values["DATE_OF_RECORD"], datetime) and values["DATE_OF_RECORD"].time() != time():
            nonmidnight_record_dates += 1
        description = _text(values["DESCRIPTION"]).strip()
        description_match = DESC_PREFIX_RE.match(description)
        if description_match is not None:
            route_match = ROUTE_RE.fullmatch(str(info["route"]))
            equals_outer = (
                route_match is not None
                and int(description_match.group(1)) == int(route_match.group(1)))
            description_equal_outer_route_count += bool(equals_outer)
            description_numeric_prefixes.append({
                "source_row": source_row,
                "route": info["route"],
                "description": description,
                "preserved_prefix": description_match.group(1),
                "prefix_equals_outer_route": equals_outer,
            })
        location_periods += bool(info["location_info"]["county_had_trailing_period"])
        seg = values["SEG_ORDER_ID"]
        adt_eff_years[_text(values["ADT_EFF_YEAR"]).strip()] += 1
        eff_date_mismatch_count += _typed(values["EFF_DATE"]) != _typed(
            values["DATE_OF_RECORD"])
        key = (str(info["district"]), str(info["county"]), str(info["route"]))
        if isinstance(seg, Decimal):
            seg_by_route[key].append(seg)
        else:
            seg_invalid += 1
    seg_inversions = sum(
        any(right < left for left, right in zip(values, values[1:]))
        for values in seg_by_route.values())
    route_runs = 0
    previous = None
    for info in row_info:
        current = (info["district"], info["county"], info["route"])
        if current != previous:
            route_runs += 1
            previous = current
    distinct_route_blocks = len({
        (info["district"], info["county"], info["route"]) for info in row_info})
    return {
        "raw_source_rows_contiguous_from_2": raw_numbers == list(range(2, 2 + len(raw_numbers))),
        "normalized_source_rows_contiguous_from_2": (
            normalized_numbers == list(range(2, 2 + len(normalized_numbers)))),
        "raw_identity_order_sha256": _ordered_digest(
            [tuple(info["physical_identity"]) for info in row_info]),
        "normalized_projection_order_sha256": _ordered_digest(projected_rows),
        "route_block_runs": route_runs,
        "distinct_district_county_route_blocks": distinct_route_blocks,
        "each_district_county_route_is_one_contiguous_run": route_runs == distinct_route_blocks,
        "seg_order_id_non_decimal_count": seg_invalid,
        "district_county_route_groups_with_seg_order_decrease": seg_inversions,
        "adt_eff_year_counts": dict(sorted(adt_eff_years.items())),
        "eff_date_vs_date_of_record_typed_mismatch_count": eff_date_mismatch_count,
        "pm_suffix_counts": dict(sorted(suffix_counts.items())),
        "nonblank_pm_suffix_count": sum(count for value, count in suffix_counts.items() if value),
        "pm_suffix_vs_hg_mismatch_count": len(suffix_hg_mismatch),
        "pm_suffix_vs_hg_mismatch_examples": suffix_hg_mismatch[:20],
        "hg_l_or_r_with_blank_pm_suffix_count": hg_lr_without_suffix,
        "date_of_record_nonmidnight_count": nonmidnight_record_dates,
        "description_numeric_prefix_source_count": len(description_numeric_prefixes),
        "description_numeric_prefix_equal_outer_route_count": (
            description_equal_outer_route_count),
        "description_numeric_prefix_different_outer_route_count": (
            len(description_numeric_prefixes) - description_equal_outer_route_count),
        "description_numeric_prefix_examples": description_numeric_prefixes[:20],
        "location_county_trailing_period_count": location_periods,
        "district_count": len({info["district"] for info in row_info}),
        "county_count": len({info["county"] for info in row_info}),
        "route_count": len({info["route"] for info in row_info}),
    }


def _projection_comparison(expected: Sequence[Sequence[object]],
                           actual: Sequence[Sequence[object]]) -> dict[str, object]:
    field_mismatches: Counter[str] = Counter()
    examples = []
    common = min(len(expected), len(actual))
    for index in range(common):
        left, right = expected[index], actual[index]
        for column, (a, b) in enumerate(zip(left, right)):
            if _typed(a) != _typed(b):
                field = NORMALIZED_HEADERS[column]
                field_mismatches[field] += 1
                if len(examples) < 30:
                    examples.append({
                        "ordinal": index + 1,
                        "normalized_source_row": index + 2,
                        "field": field,
                        "expected": _typed(a),
                        "actual": _typed(b),
                    })
    expected_multiset, _ = _multiset_digest(expected)
    actual_multiset, _ = _multiset_digest(actual)
    ordered_equal = len(expected) == len(actual) and not field_mismatches
    return {
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "missing_or_extra_row_count": abs(len(expected) - len(actual)),
        "typed_cell_mismatch_count": sum(field_mismatches.values()),
        "typed_cell_mismatches_by_field": dict(sorted(field_mismatches.items())),
        "mismatch_examples": examples,
        "ordered_exact": ordered_equal,
        "multiset_exact": expected_multiset == actual_multiset,
        "expected_ordered_sha256": _ordered_digest(expected),
        "actual_ordered_sha256": _ordered_digest(actual),
        "expected_multiset_sha256": expected_multiset,
        "actual_multiset_sha256": actual_multiset,
    }


def _description_loss_contract(projection: dict[str, object],
                               normalized_rows: Sequence[Sequence[object]]) -> dict[str, object]:
    route_index = NORMALIZED_HEADERS.index("Route")
    observed = []
    for item in projection["mismatch_examples"]:
        row_number = int(item["normalized_source_row"])
        ordinal = int(item["ordinal"])
        expected = item["expected"]
        actual = item["actual"]
        if (item["field"] != "Description" or expected[0] != "str"
                or actual[0] != "str" or not 1 <= ordinal <= len(normalized_rows)):
            continue
        observed.append((row_number, str(normalized_rows[ordinal - 1][route_index]),
                         str(expected[1]), str(actual[1])))
    expected = list(EXPECTED_DESCRIPTION_LOSSES)
    exact = (
        projection["typed_cell_mismatch_count"] == len(expected)
        and projection["typed_cell_mismatches_by_field"] == {
            "Description": len(expected)}
        and observed == expected
    )
    payload = json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "exact": exact,
        "expected_count": len(expected),
        "observed_count": projection["typed_cell_mismatch_count"],
        "expected_manifest_sha256": _sha(payload),
        "expected": [
            {"normalized_source_row": row, "outer_route": route,
             "conserved": conserved, "current_normalized": current}
            for row, route, conserved, current in expected
        ],
        "observed": [
            {"normalized_source_row": row, "outer_route": route,
             "conserved": conserved, "current_normalized": current}
            for row, route, conserved, current in observed
        ],
    }


def _mutation_probes(raw_rows: Sequence[Sequence[object]],
                     projected_rows: Sequence[Sequence[object]]) -> list[dict[str, object]]:
    probes = []

    reordered = list(projected_rows)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    probes.append({
        "name": "normalized row reorder",
        "detected": (_ordered_digest(reordered) != _ordered_digest(projected_rows)
                     and _multiset_digest(reordered)[0] == _multiset_digest(projected_rows)[0]),
        "expected_effect": "ordered digest changes while multiset digest remains equal",
    })

    changed_multiplicity = list(projected_rows[:-1]) + [projected_rows[0]]
    probes.append({
        "name": "drop one row and duplicate another",
        "detected": _multiset_digest(changed_multiplicity)[0] != _multiset_digest(projected_rows)[0],
        "expected_effect": "multiset digest changes even though row count remains constant",
    })

    pm_changed = [list(row) for row in projected_rows]
    pm_changed[0][NORMALIZED_HEADERS.index("PM")] = "999999.999"
    probes.append({
        "name": "projected PM value mutation",
        "detected": _ordered_digest(pm_changed) != _ordered_digest(projected_rows),
        "expected_effect": "normalized row and PM field digests change",
    })

    raw_source_only = [list(row) for row in raw_rows]
    id_index = RAW_HEADERS.index("RAM_CONNECTION_ID")
    raw_source_only[0][id_index] = _text(raw_source_only[0][id_index]) + "#MUT"
    projected_after_source_only = [_project_raw_row(row)[0] for row in raw_source_only]
    probes.append({
        "name": "source-only record identifier mutation",
        "detected": (
            _dataset_digests(RAW_HEADERS, raw_source_only)["fields"]["RAM_CONNECTION_ID"]
            ["ordered_typed_sha256"]
            != _dataset_digests(RAW_HEADERS, raw_rows)["fields"]["RAM_CONNECTION_ID"]
            ["ordered_typed_sha256"]
            and _ordered_digest(projected_after_source_only) == _ordered_digest(projected_rows)),
        "expected_effect": (
            "raw field digest changes while normalized projection remains blind; "
            "this proves why source-only digests are required"),
    })

    suffix_row = next(index for index, row in enumerate(raw_rows)
                      if _text(row[RAW_HEADERS.index("PM_SFX")]).strip())
    suffix_changed = [list(row) for row in raw_rows]
    suffix_index = RAW_HEADERS.index("PM_SFX")
    old_suffix = _text(suffix_changed[suffix_row][suffix_index]).strip().upper()
    suffix_changed[suffix_row][suffix_index] = "R" if old_suffix != "R" else "L"
    projected_after_suffix = [_project_raw_row(row)[0] for row in suffix_changed]
    probes.append({
        "name": "physical PM suffix mutation",
        "detected": (
            _dataset_digests(RAW_HEADERS, suffix_changed)["fields"]["PM_SFX"]
            ["ordered_typed_sha256"]
            != _dataset_digests(RAW_HEADERS, raw_rows)["fields"]["PM_SFX"]
            ["ordered_typed_sha256"]
            and _ordered_digest(projected_after_suffix) == _ordered_digest(projected_rows)),
        "expected_effect": (
            "raw identity changes while every current normalized cell remains equal; "
            "this is the blocking schema blind spot"),
    })

    typed = [list(row) for row in raw_rows]
    typed_index = None
    typed_column = None
    for column in range(len(RAW_HEADERS)):
        for index, row in enumerate(typed):
            if isinstance(row[column], Decimal):
                typed_index, typed_column = index, column
                break
        if typed_index is not None:
            break
    if typed_index is None or typed_column is None:
        raise ConservationError("mutation probe found no Decimal source cell")
    original = typed[typed_index][typed_column]
    typed[typed_index][typed_column] = str(original)
    probes.append({
        "name": "same-text cross-type mutation",
        "detected": _ordered_digest(typed) != _ordered_digest(raw_rows),
        "expected_effect": "typed digest distinguishes Decimal from equal-looking text",
    })

    return probes


def run(raw_path: Path, normalized_path: Path, normalized_binding: dict[str, object]) -> dict[str, object]:
    raw_spec = SheetSpec(
        RAW_BINDING["sheet"],
        tuple(ColumnSpec(header, DATE if header in {"DATE_OF_RECORD", "EFF_DATE"} else SCALAR)
              for header in RAW_HEADERS),
        exact_schema=True)
    normalized_spec = SheetSpec(
        normalized_binding["sheet"],
        tuple(ColumnSpec(header, SCALAR) for header in NORMALIZED_HEADERS),
        exact_schema=True)

    raw_topology = _workbook_topology(raw_path)
    raw_sheet = read_sheet(raw_path, raw_spec)
    _require_binding(raw_sheet, raw_topology, RAW_BINDING, "raw Ramp Detail")
    normalized_topology = _workbook_topology(normalized_path)
    normalized_sheet = read_sheet(normalized_path, normalized_spec)
    _require_binding(normalized_sheet, normalized_topology, normalized_binding,
                     "normalized Ramp Detail")
    r7_witness_pre = capture_file_identity(R7_WITNESS_RESULT)
    _require_identity_binding(r7_witness_pre, R7_WITNESS_BINDING, "r7 witness result")
    r7_sidecar_pre = capture_file_identity(R7_NORMALIZED_SIDECAR)
    _require_identity_binding(
        r7_sidecar_pre, R7_NORMALIZED_SIDECAR_BINDING, "r7 Ramp normalized sidecar")
    reader_pre = capture_file_identity(READER_PATH)

    raw_rows = [tuple(row.values) for row in raw_sheet.rows]
    normalized_rows = [tuple(row.values) for row in normalized_sheet.rows]
    if len(raw_rows) != RAW_BINDING["rows"]:
        raise ConservationError(
            f"raw row count {len(raw_rows)} != bound {RAW_BINDING['rows']}")
    if len(normalized_rows) != normalized_binding["rows"]:
        raise ConservationError(
            f"normalized row count {len(normalized_rows)} != bound {normalized_binding['rows']}")
    blank_raw = [row.source_row for row in raw_sheet.rows if not any(v not in (None, "") for v in row.values)]
    blank_normalized = [row.source_row for row in normalized_sheet.rows
                        if not any(v not in (None, "") for v in row.values)]
    if blank_raw or blank_normalized:
        raise ConservationError(
            f"physical blank data rows are forbidden: raw={blank_raw[:10]}, "
            f"normalized={blank_normalized[:10]}")

    projected_rows = []
    row_info = []
    for raw_row in raw_rows:
        projected, info = _project_raw_row(raw_row)
        projected_rows.append(projected)
        row_info.append(info)

    projection = _projection_comparison(projected_rows, normalized_rows)
    description_loss_contract = _description_loss_contract(projection, normalized_rows)
    collisions = _collision_census(raw_rows, projected_rows, row_info)
    order_anomalies = _order_and_anomalies(
        raw_sheet, raw_rows, normalized_sheet, projected_rows, row_info)
    mutations = _mutation_probes(raw_rows, projected_rows)

    blocking_findings = []
    if order_anomalies["nonblank_pm_suffix_count"]:
        blocking_findings.append({
            "id": "RD-S6-001",
            "severity": "P1",
            "status": "open",
            "title": "Normalized Ramp Detail omits the PM_SFX physical identity claim",
            "evidence": {
                "nonblank_count": order_anomalies["nonblank_pm_suffix_count"],
                "value_counts": {
                    key: value for key, value in order_anomalies["pm_suffix_counts"].items() if key
                },
                "current_pm_suffix_vs_hg_mismatches": order_anomalies[
                    "pm_suffix_vs_hg_mismatch_count"],
                "identity_without_suffix_duplicate_groups": collisions[
                    "identity_without_pm_suffix"]["duplicate_groups"],
                "full_identity_duplicate_groups": collisions[
                    "physical_identity"]["duplicate_groups"],
            },
            "requirement": (
                "Retain PM_SFX as an independently typed normalized identity claim "
                "or prove a stable authoritative derivation contract broader than this one corpus."
            ),
        })

    prefixed_descriptions = order_anomalies["description_numeric_prefix_source_count"]
    if prefixed_descriptions:
        blocking_findings.append({
            "id": "RD-S6-002",
            "severity": "P1",
            "status": "open",
            "title": "Ramp normalization removes source-backed numeric Description prefixes",
            "evidence": {
                "affected_rows": prefixed_descriptions,
                "equal_outer_route_rows": order_anomalies[
                    "description_numeric_prefix_equal_outer_route_count"],
                "different_outer_route_rows": order_anomalies[
                    "description_numeric_prefix_different_outer_route_count"],
                "examples": order_anomalies["description_numeric_prefix_examples"],
                "normalized_typed_description_mismatches": projection[
                    "typed_cell_mismatches_by_field"].get("Description", 0),
            },
            "requirement": (
                "Preserve raw TSN Description. Strip only the distinct outer-route "
                "prefix added by TSMIS when projecting the TSMIS representation."
            ),
        })

    blocking_findings.append({
        "id": "RD-S6-003",
        "severity": "P1",
        "status": "open",
        "title": "Ramp normalized bytes omit two fields printed by the accepted TSN PDF",
        "fields": ["ADT_EFF_YEAR", "EFF_DATE"],
        "evidence": {
            "adt_eff_year_counts": order_anomalies["adt_eff_year_counts"],
            "eff_date_vs_date_of_record_typed_mismatch_count": order_anomalies[
                "eff_date_vs_date_of_record_typed_mismatch_count"],
        },
        "requirement": (
            "Retain both typed source facts for PDF/evidence/context use. Their "
            "constant/equal values in this bound corpus are not universal derivation rules."
        ),
    })

    review_findings = [{
        "id": "RD-S6-004",
        "severity": "review",
        "status": "explicit_database_and_relational_disposition",
        "title": "Database identity and ordering remain audited but need not be visible",
        "fields": ["RAM_CONNECTION_ID", "SEG_ORDER_ID"],
        "requirement": (
            "Retain the typed raw digest and order proof; if normalization omits the "
            "columns, the disposition must remain explicit and mutation-tested."
        ),
    }]

    raw_digests = _dataset_digests(RAW_HEADERS, raw_rows)
    projected_digests = _dataset_digests(NORMALIZED_HEADERS, projected_rows)
    normalized_digests = _dataset_digests(NORMALIZED_HEADERS, normalized_rows)

    raw_final_identity = capture_file_identity(raw_path)
    normalized_final_identity = capture_file_identity(normalized_path)
    r7_witness_final = capture_file_identity(R7_WITNESS_RESULT)
    r7_sidecar_final = capture_file_identity(R7_NORMALIZED_SIDECAR)
    generator_final = capture_file_identity(Path(__file__))
    reader_final = capture_file_identity(READER_PATH)
    final_identities_current = (
        raw_final_identity == raw_sheet.pre_identity
        and normalized_final_identity == normalized_sheet.pre_identity
        and r7_witness_final == r7_witness_pre
        and r7_sidecar_final == r7_sidecar_pre
        and generator_final == GENERATOR_START_IDENTITY
        and reader_pre == READER_START_IDENTITY
        and reader_final == READER_START_IDENTITY
    )

    audit_invariants = {
        "source_bindings_exact": True,
        "workbook_topologies_exact": True,
        "final_source_identities_current": final_identities_current,
        "raw_schema_exact": raw_sheet.headers == RAW_HEADERS,
        "normalized_schema_exact": normalized_sheet.headers == NORMALIZED_HEADERS,
        "raw_row_count_exact": len(raw_rows) == RAW_BINDING["rows"],
        "normalized_row_count_exact": len(normalized_rows) == normalized_binding["rows"],
        "raw_physical_rows_contiguous": order_anomalies[
            "raw_source_rows_contiguous_from_2"],
        "normalized_physical_rows_contiguous": order_anomalies[
            "normalized_source_rows_contiguous_from_2"],
        "projection_residue_fully_classified": description_loss_contract["exact"],
        "full_physical_identity_unique": collisions["physical_identity"]["duplicate_groups"] == 0,
        "required_location_and_pm_valid": True,
        "mutation_probes_all_detected": all(probe["detected"] for probe in mutations),
    }
    projection_exact = projection["ordered_exact"] and projection["multiset_exact"]
    audit_complete = all(audit_invariants.values())
    normalized_full_conservation = (
        audit_complete and projection_exact and not blocking_findings)
    return {
        "schema_version": 3,
        "audit": "Stage 6 Ramp Detail raw-to-normalized conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_comparators_imported": False,
            "reader": "build/phase3_xlsx_stream.py stdlib OOXML reader",
            "permanent_reader_mutation_gate": "build/check_phase3_xlsx_stream.py",
        },
        "bindings": {
            "raw": RAW_BINDING,
            "normalized": normalized_binding,
        },
        "provenance": {
            "generator_start": _identity_dict(GENERATOR_START_IDENTITY),
            "generator_acceptance": _identity_dict(generator_final),
            "independent_reader_module_start": _identity_dict(READER_START_IDENTITY),
            "independent_reader_pre_acceptance": _identity_dict(reader_pre),
            "independent_reader_acceptance": _identity_dict(reader_final),
            "accepted_r7_witness_result": {
                "binding": R7_WITNESS_BINDING,
                "path": str(R7_WITNESS_RESULT),
                "pre": _identity_dict(r7_witness_pre),
                "acceptance": _identity_dict(r7_witness_final),
            },
            "accepted_r7_normalized_sidecar": {
                "binding": R7_NORMALIZED_SIDECAR_BINDING,
                "path": str(R7_NORMALIZED_SIDECAR),
                "pre": _identity_dict(r7_sidecar_pre),
                "acceptance": _identity_dict(r7_sidecar_final),
            },
        },
        "source_identity": {
            "raw": {
                "path": str(raw_path.resolve()),
                "topology_capture": raw_topology,
                "worksheet_pre_read": _identity_dict(raw_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(raw_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(raw_final_identity),
            },
            "normalized": {
                "path": str(normalized_path.resolve()),
                "topology_capture": normalized_topology,
                "worksheet_pre_read": _identity_dict(normalized_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(normalized_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(normalized_final_identity),
            },
        },
        "field_dispositions": FIELD_DISPOSITIONS,
        "raw_digests": raw_digests,
        "independently_projected_digests": projected_digests,
        "normalized_digests": normalized_digests,
        "projection_comparison": projection,
        "classified_projection_residue": {
            "description_prefix_loss": description_loss_contract,
        },
        "identity_and_collision_census": collisions,
        "order_and_anomaly_census": order_anomalies,
        "semantic_mutation_probes": mutations,
        "findings": {
            "blocking": blocking_findings,
            "review": review_findings,
        },
        "audit_invariants": audit_invariants,
        "projection_exact": projection_exact,
        "stage6_family_audit_complete": audit_complete,
        "normalized_full_conservation": normalized_full_conservation,
    }


def _atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", delete=False,
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp") as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _publication_revalidation(raw_path: Path, normalized_path: Path,
                              result: dict[str, object]) -> tuple[bool, dict[str, object]]:
    observed = {
        "raw": capture_file_identity(raw_path),
        "normalized": capture_file_identity(normalized_path),
        "r7_witness_result": capture_file_identity(R7_WITNESS_RESULT),
        "r7_normalized_sidecar": capture_file_identity(R7_NORMALIZED_SIDECAR),
        "generator": capture_file_identity(Path(__file__)),
        "independent_reader": capture_file_identity(READER_PATH),
    }
    expected = {
        "raw": FileIdentity(**result["source_identity"]["raw"]["acceptance_revalidation"]),
        "normalized": FileIdentity(
            **result["source_identity"]["normalized"]["acceptance_revalidation"]),
        "r7_witness_result": FileIdentity(
            **result["provenance"]["accepted_r7_witness_result"]["acceptance"]),
        "r7_normalized_sidecar": FileIdentity(
            **result["provenance"]["accepted_r7_normalized_sidecar"]["acceptance"]),
        "generator": FileIdentity(**result["provenance"]["generator_acceptance"]),
        "independent_reader": FileIdentity(
            **result["provenance"]["independent_reader_acceptance"]),
    }
    current = all(observed[name] == expected[name] for name in expected)
    return current, {
        name: {"expected": _identity_dict(expected[name]),
               "observed": _identity_dict(observed[name]),
               "current": observed[name] == expected[name]}
        for name in expected
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--normalized", type=Path, default=NORMALIZED_DEFAULT)
    parser.add_argument("--normalized-sha256", default=NORMALIZED_R7_BINDING["sha256"])
    parser.add_argument("--normalized-bytes", type=int, default=NORMALIZED_R7_BINDING["bytes"])
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-open-findings", action="store_true",
        help="exit zero when the audit is complete but documented product findings remain")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    binding = dict(NORMALIZED_R7_BINDING)
    binding["sha256"] = args.normalized_sha256.lower()
    binding["bytes"] = args.normalized_bytes
    try:
        result = run(args.raw, args.normalized, binding)
    except Exception as exc:
        failure = {
            "schema_version": 3,
            "audit": "Stage 6 Ramp Detail raw-to-normalized conservation",
            "projection_exact": False,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        payload = json.dumps(failure, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            _atomic_write_text(args.output, payload)
        if args.output:
            sys.stdout.write(json.dumps(failure, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(payload)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        probe = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="\n", delete=False,
                    dir=args.output.parent, prefix=f".{args.output.name}.",
                    suffix=".prepublish") as handle:
                probe = Path(handle.name)
                handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            publication_current, publication_detail = _publication_revalidation(
                args.raw, args.normalized, result)
        finally:
            if probe is not None:
                try:
                    probe.unlink()
                except FileNotFoundError:
                    pass
    else:
        publication_current, publication_detail = _publication_revalidation(
            args.raw, args.normalized, result)
    result["publication_revalidation"] = {
        "after_serialized_result_bytes": True,
        "all_sources_current": publication_current,
        "identities": publication_detail,
    }
    result["audit_invariants"]["publication_source_identities_current"] = (
        publication_current)
    result["stage6_family_audit_complete"] = (
        result["stage6_family_audit_complete"] and publication_current)
    result["normalized_full_conservation"] = (
        result["normalized_full_conservation"]
        and result["stage6_family_audit_complete"])
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        _atomic_write_text(args.output, payload)
        final_current, final_detail = _publication_revalidation(
            args.raw, args.normalized, result)
        if not final_current:
            result["publication_revalidation"]["all_sources_current"] = False
            result["publication_revalidation"]["post_final_write_current"] = False
            result["audit_invariants"]["publication_source_identities_current"] = False
            result["stage6_family_audit_complete"] = False
            result["normalized_full_conservation"] = False
            _atomic_write_text(
                args.output,
                json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            return 2
        result_identity = capture_file_identity(args.output)
        acceptance_path = args.output.with_suffix(args.output.suffix + ".acceptance.json")
        acceptance = {
            "schema_version": 1,
            "audit": result["audit"],
            "result": str(args.output.resolve()),
            "result_bytes": result_identity.size,
            "result_sha256": result_identity.sha256,
            "stage6_family_audit_complete": result["stage6_family_audit_complete"],
            "normalized_full_conservation": result["normalized_full_conservation"],
            "post_result_write_revalidation": final_current,
            "post_result_write_identities": final_detail,
        }
        _atomic_write_text(
            acceptance_path,
            json.dumps(acceptance, indent=2, ensure_ascii=False) + "\n")
    if args.output:
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "projection_exact": result["projection_exact"],
            "stage6_family_audit_complete": result["stage6_family_audit_complete"],
            "normalized_full_conservation": result["normalized_full_conservation"],
            "blocking_findings": len(result["findings"]["blocking"]),
            "acceptance_record": str(acceptance_path),
            "result_sha256": result_identity.sha256,
        }, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(payload)
    if not result["stage6_family_audit_complete"]:
        return 2
    if not result["normalized_full_conservation"] and not args.allow_open_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Independent Stage-6 Intersection Detail raw-to-normalized conservation oracle.

The oracle deliberately imports no application loader, normalizer, comparator,
evidence adapter, report catalog, or production schema.  It reads the exact
authoritative raw XLSX and accepted r7 normalized XLSX through the stdlib-only
``phase3_xlsx_stream`` reader, independently projects every physical row, and
gives every one of the 36 raw fields an explicit disposition.

Projection parity and full conservation are intentionally separate claims.
The current normalized workbook may exactly reproduce its declared 36-column
shape while still losing MAIN_EFF_DATE, MAIN_ADT, and CROSS_ADT.  Those source
facts remain typed, digested, mutation-tested, and reported as open product
findings; ``--allow-open-findings`` permits an otherwise complete family audit
to exit successfully without mislabelling that loss as full conservation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree
import zipfile

from phase3_xlsx_stream import (
    SCALAR,
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    StreamedSheet,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


RAW_DEFAULT = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\intersection_detail\raw"
    r"\TSAR - INTERSECTION DETAIL_TSN.xlsx"
)
NORMALIZED_DEFAULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7\intersection_detail\consolidated"
    r"\tsn_intersection_detail_normalized.xlsx"
)
NORMALIZED_SIDECAR_DEFAULT = Path(str(NORMALIZED_DEFAULT) + ".outcome.json")

RAW_BINDING = {
    "bytes": 2_920_705,
    "sha256": "5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2",
    "sheet": "Sheet 1",
    "rows": 16_626,
    "columns": 36,
}
NORMALIZED_R7_BINDING = {
    "bytes": 2_084_691,
    "sha256": "d4609c3afb8663dd89e6e2e00103d41245a0213d7e4e08fb63e961bc4035b37b",
    "sheet": "Intersection Detail (TSN)",
    "rows": 16_626,
    "columns": 36,
    "normalization_version": 3,
}
NORMALIZED_R7_SIDECAR_BINDING = {
    "bytes": 903,
    "sha256": "9a62c3341d9c78dbab7c9eef01c23c714081499dd44cdeac85ef21b1f1c2a5b8",
    "completion": "complete",
    "skipped_inputs": 0,
    "failed_inputs": 0,
    "normalization_version": 3,
    "artifact_identity_token": (
        "tsn-normalized-v1:fb78c4f10748fc757b17cbca4415da02973ae553eb97dfbdd3e9399aa1947d8a"),
}
R7_WITNESS_RESULT = NORMALIZED_DEFAULT.parents[2] / "result.json"
R7_WITNESS_BINDING = {
    "bytes": 173_124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}

RAW_HEADERS = (
    "PP", "POST_MILE", "LOCATION", "DATE_REC", "HG", "CITY_CODE", "RU",
    "EFF_DATE_INT", "TY_INT", "EFF_DATE_CT", "TY_CT", "EFF_DATE_LT", "LT_TY",
    "EFF_DATE_ML", "MAIN_SM", "MAIN_LC", "MAIN_RC", "MAIN_TF", "MAIN_NL",
    "X_CROSS_OVERRIDE", "MAIN_EFF_DATE", "MAIN_ADT", "DESCRIPTION",
    "MAIN_OVERRIDE", "CROSS_BEGIN_DATE", "CS_SM", "CS_LC", "CS_RC", "CS_TF",
    "CS_NL", "EFF_DATE", "CROSS_ADT", "CROSS_ROUTE_NAME", "CROSS_PM_PREFIX",
    "CROSS_POSTMILE", "CROSS_PM_SUFFIX",
)
NORMALIZED_HEADERS = (
    "Route", "PR", "Route Suffix", "PM", "Date of Record", "HG", "City Code",
    "R/U", "INT Type Eff-Date", "INT Type", "Control Type Eff-Date",
    "Control Type", "Lighting Eff-Date", "Lighting", "ML Eff-Date",
    "ML Mastarm", "ML Left Chan", "ML Right Chan", "ML Traffic Flow",
    "ML Num Lanes", "Description", "Main Line Length", "CS Eff-Date",
    "CS Mastarm", "CS Left Chan", "CS Right Chan", "CS Traffic Flow",
    "CS Num Lanes", "Int St Eff-Date", "Intrte Route", "Intrte PM Prefix",
    "Intrte Postmile", "Intrte PM Suffix", "Xing Line Lgth", "TSN District",
    "TSN County",
)

FIELD_DISPOSITIONS = {
    "PP": {"kind": "projected", "targets": ["PR"],
           "rule": "type-preserving scalar"},
    "POST_MILE": {"kind": "composed", "targets": ["PM"],
                  "rule": "trim; preserve sign/fraction; remove leading integer zeroes"},
    "LOCATION": {"kind": "composed",
                 "targets": ["Route", "Route Suffix", "TSN District", "TSN County"],
                 "rule": "strict DD COUNTY[.] RRR[SFX] decomposition"},
    "DATE_REC": {"kind": "composed", "targets": ["Date of Record"],
                 "rule": "ISO date"},
    "HG": {"kind": "projected", "targets": ["HG"],
           "rule": "type-preserving scalar"},
    "CITY_CODE": {"kind": "projected", "targets": ["City Code"],
                  "rule": "type-preserving scalar"},
    "RU": {"kind": "projected", "targets": ["R/U"],
           "rule": "type-preserving scalar"},
    "EFF_DATE_INT": {"kind": "composed", "targets": ["INT Type Eff-Date"],
                     "rule": "ISO date"},
    "TY_INT": {"kind": "projected", "targets": ["INT Type"],
               "rule": "type-preserving scalar"},
    "EFF_DATE_CT": {"kind": "composed", "targets": ["Control Type Eff-Date"],
                    "rule": "ISO date"},
    "TY_CT": {"kind": "composed", "targets": ["Control Type"],
              "rule": "J/K/L/M/N/P/S fold to S only"},
    "EFF_DATE_LT": {"kind": "composed", "targets": ["Lighting Eff-Date"],
                    "rule": "ISO date"},
    "LT_TY": {"kind": "composed", "targets": ["Lighting"],
              "rule": "Y/1 -> Y; N/0 -> N; preserve unknown literal"},
    "EFF_DATE_ML": {"kind": "composed", "targets": ["ML Eff-Date"],
                    "rule": "ISO date"},
    "MAIN_SM": {"kind": "composed", "targets": ["ML Mastarm"],
                "rule": "Y/1 -> Y; N/0 -> N; preserve unknown literal"},
    "MAIN_LC": {"kind": "projected", "targets": ["ML Left Chan"],
                "rule": "type-preserving scalar"},
    "MAIN_RC": {"kind": "composed", "targets": ["ML Right Chan"],
                "rule": "Y/1 -> Y; N/0 -> N; preserve unknown literal"},
    "MAIN_TF": {"kind": "projected", "targets": ["ML Traffic Flow"],
                "rule": "type-preserving scalar"},
    "MAIN_NL": {"kind": "projected", "targets": ["ML Num Lanes"],
                "rule": "type-preserving scalar; no numeric coercion"},
    "X_CROSS_OVERRIDE": {"kind": "composed", "targets": ["Xing Line Lgth"],
                         "rule": "signed decimal canon"},
    "MAIN_EFF_DATE": {"kind": "source_only", "targets": [],
                      "rule": "typed TSN second mainline effective date retained in audit"},
    "MAIN_ADT": {"kind": "source_only", "targets": [],
                 "rule": "typed TSN mainline ADT retained in audit"},
    "DESCRIPTION": {"kind": "projected", "targets": ["Description"],
                    "rule": "type-preserving text, including quotation characters"},
    "MAIN_OVERRIDE": {"kind": "composed", "targets": ["Main Line Length"],
                      "rule": "signed decimal canon"},
    "CROSS_BEGIN_DATE": {"kind": "composed", "targets": ["CS Eff-Date"],
                         "rule": "ISO date"},
    "CS_SM": {"kind": "composed", "targets": ["CS Mastarm"],
              "rule": "Y/1 -> Y; N/0 -> N; preserve unknown literal"},
    "CS_LC": {"kind": "projected", "targets": ["CS Left Chan"],
              "rule": "type-preserving scalar"},
    "CS_RC": {"kind": "composed", "targets": ["CS Right Chan"],
              "rule": "Y/1 -> Y; N/0 -> N; preserve unknown literal"},
    "CS_TF": {"kind": "projected", "targets": ["CS Traffic Flow"],
              "rule": "type-preserving scalar"},
    "CS_NL": {"kind": "projected", "targets": ["CS Num Lanes"],
              "rule": "type-preserving scalar; no numeric coercion"},
    "EFF_DATE": {"kind": "composed", "targets": ["Int St Eff-Date"],
                 "rule": "ISO date"},
    "CROSS_ADT": {"kind": "source_only", "targets": [],
                  "rule": "typed TSN cross-street ADT retained in audit"},
    "CROSS_ROUTE_NAME": {"kind": "composed", "targets": ["Intrte Route"],
                         "rule": "signed decimal canon"},
    "CROSS_PM_PREFIX": {"kind": "projected", "targets": ["Intrte PM Prefix"],
                        "rule": "type-preserving scalar"},
    "CROSS_POSTMILE": {"kind": "composed", "targets": ["Intrte Postmile"],
                       "rule": "signed decimal canon"},
    "CROSS_PM_SUFFIX": {"kind": "projected", "targets": ["Intrte PM Suffix"],
                        "rule": "type-preserving scalar"},
}

SOURCE_ONLY_FIELDS = ("MAIN_EFF_DATE", "MAIN_ADT", "CROSS_ADT")
BOOLEAN_FIELDS = ("LT_TY", "MAIN_SM", "MAIN_RC", "CS_SM", "CS_RC")
DATE_FIELDS = (
    "DATE_REC", "EFF_DATE_INT", "EFF_DATE_CT", "EFF_DATE_LT", "EFF_DATE_ML",
    "MAIN_EFF_DATE", "CROSS_BEGIN_DATE", "EFF_DATE",
)
SIGNALIZED_CODES = frozenset(("J", "K", "L", "M", "N", "P", "S"))
BOOL_MAP = {"Y": "Y", "N": "N", "1": "Y", "0": "N"}
LOCATION_RE = re.compile(r"^(\d{2}) +([A-Z]{2,3}\.?) +(\d+)([A-Z]?)$")
PM_RE = re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$")
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

EXPECTED_WITHIN_COUNTY_PP_COLLISIONS = (
    ("101", "SF", "5.45", ("", "M")),
    ("115", "IMP", "9.54", ("", "L")),
    ("132", "STA", "15.34", ("", "L")),
    ("132", "STA", "15.62", ("", "L")),
    ("184", "KER", "0", ("", "L")),
    ("218", "MON", "0.34", ("", "L")),
)


class ConservationError(ValueError):
    """The source or independent conservation contract was not satisfied."""


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        item = value.as_tuple()
        return ["decimal", item.sign, list(item.digits), item.exponent]
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


def _stat_token(info: os.stat_result) -> tuple[int, int, int, int]:
    return (int(info.st_size), int(info.st_mtime_ns), int(info.st_dev), int(info.st_ino))


def _reject_link(info: os.stat_result) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise ConservationError("workbook path may not be a symbolic link")
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if int(getattr(info, "st_file_attributes", 0) or 0) & reparse:
        raise ConservationError("workbook path may not be a reparse point")


def _hash_handle(handle) -> str:
    digest = hashlib.sha256()
    handle.seek(0)
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def _workbook_topology(path: Path) -> dict[str, object]:
    """Bind exact sheet names/visibility from a private immutable capture."""
    captured = capture_file_bytes(path)
    with zipfile.ZipFile(io.BytesIO(captured.payload), "r") as archive:
        members = [info for info in archive.infolist()
                   if info.filename == "xl/workbook.xml"]
        if len(members) != 1:
            raise ConservationError("workbook topology member is missing or duplicated")
        member = members[0]
        if member.file_size > 4 * 1024 * 1024:
            raise ConservationError("workbook topology member exceeds the size limit")
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
    token = [identity.size, identity.mtime_ns, identity.device, identity.inode]
    return {
        "sheets": sheets,
        "date_system": "1904" if date1904 else "1900",
        "pre_sha256": identity.sha256,
        "post_sha256": identity.sha256,
        "size": identity.size,
        "pre_stat": token,
        "bound_stat": token,
        "post_stat": token,
        "capture_identity": _identity_dict(identity),
    }


def _worksheet_error_references(payload: bytes) -> list[str]:
    """Return every explicit OOXML error cell in one worksheet payload."""
    root = ElementTree.fromstring(payload)
    return [
        element.attrib.get("r", "?")
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "c" and element.attrib.get("t") == "e"
    ]


def _error_cell_scan(path: Path, binding: dict[str, object], label: str) -> dict[str, object]:
    """Independently reject error cells from one private immutable capture."""
    captured = capture_file_bytes(path)
    errors = []
    worksheet_members_scanned = 0
    with zipfile.ZipFile(io.BytesIO(captured.payload), "r") as archive:
        for member in sorted(archive.namelist()):
            if not member.startswith("xl/worksheets/") or not member.endswith(".xml"):
                continue
            worksheet_members_scanned += 1
            for reference in _worksheet_error_references(archive.read(member)):
                errors.append({"member": member, "cell": reference})
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    observed = (captured.identity.size, captured.identity.sha256)
    if observed != expected:
        raise ConservationError(
            f"{label} error-cell scan binding mismatch: {observed!r} != {expected!r}")
    if errors:
        raise ConservationError(f"{label} contains forbidden error cells: {errors[:20]!r}")
    return {
        "sha256": captured.identity.sha256,
        "bytes": captured.identity.size,
        "worksheet_members_scanned": worksheet_members_scanned,
        "error_cells": [],
    }


def _read_bound_sidecar(path: Path, binding: dict[str, object]) -> tuple[FileIdentity, dict[str, object]]:
    """Read the accepted r7 outcome from one exact bound ordinary file."""
    before_path = path.lstat()
    _reject_link(before_path)
    if not stat.S_ISREG(before_path.st_mode):
        raise ConservationError("normalized outcome sidecar must be an ordinary file")
    with path.open("rb") as handle:
        bound = os.fstat(handle.fileno())
        _reject_link(bound)
        if _stat_token(bound) != _stat_token(before_path):
            raise ConservationError("normalized outcome sidecar changed while binding")
        pre_hash = _hash_handle(handle)
        handle.seek(0)
        payload = handle.read()
        if _stat_token(os.fstat(handle.fileno())) != _stat_token(bound):
            raise ConservationError("normalized outcome sidecar changed while reading")
        post_hash = _hash_handle(handle)
    after_path = path.lstat()
    _reject_link(after_path)
    if _stat_token(after_path) != _stat_token(bound) or pre_hash != post_hash:
        raise ConservationError("normalized outcome sidecar changed across read")
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    observed = (int(bound.st_size), pre_hash)
    if observed != expected or hashlib.sha256(payload).hexdigest() != pre_hash:
        raise ConservationError(
            f"normalized outcome sidecar binding mismatch: {observed!r} != {expected!r}")
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConservationError("normalized outcome sidecar is not canonical UTF-8 JSON") from exc
    raw_manifest = document.get("tsn_raw_manifest") or {}
    members = raw_manifest.get("members") or []
    workbook_identity = document.get("tsn_normalized_workbook_identity") or {}
    expected_claims = {
        "completion": binding["completion"],
        "skipped_inputs": binding["skipped_inputs"],
        "failed_inputs": binding["failed_inputs"],
        "tsn_normalization_version": binding["normalization_version"],
        "tsn_artifact_identity_token": binding["artifact_identity_token"],
    }
    actual_claims = {key: document.get(key) for key in expected_claims}
    if actual_claims != expected_claims:
        raise ConservationError(
            f"normalized outcome claims mismatch: {actual_claims!r} != {expected_claims!r}")
    if (
        raw_manifest.get("member_count") != 1
        or raw_manifest.get("byte_length") != RAW_BINDING["bytes"]
        or len(members) != 1
        or members[0].get("relative_path") != "TSAR - INTERSECTION DETAIL_TSN.xlsx"
        or members[0].get("byte_length") != RAW_BINDING["bytes"]
        or members[0].get("sha256") != RAW_BINDING["sha256"]
        or workbook_identity.get("byte_length") != NORMALIZED_R7_BINDING["bytes"]
        or workbook_identity.get("sha256") != NORMALIZED_R7_BINDING["sha256"]
    ):
        raise ConservationError("normalized outcome sidecar does not bind the accepted raw/r7 pair")
    identity = FileIdentity(
        canonical_path=str(path.absolute()), size=int(bound.st_size),
        mtime_ns=int(bound.st_mtime_ns), device=int(bound.st_dev),
        inode=int(bound.st_ino), sha256=pre_hash,
    )
    return identity, document


def _require_binding(sheet: StreamedSheet, topology: dict[str, object],
                     binding: dict[str, object], label: str) -> None:
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


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ConservationError("non-finite decimal source value")
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return str(value)


def _scalar(value: object) -> object:
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time() else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return value


def _parse_location(value: object) -> tuple[str, str, str, str, dict[str, object]]:
    literal = _text(value).strip().upper()
    match = LOCATION_RE.fullmatch(literal)
    if match is None:
        raise ConservationError(f"invalid Intersection Detail LOCATION token: {literal!r}")
    district, county_token, route_digits, suffix = match.groups()
    county = county_token[:-1] if county_token.endswith(".") else county_token
    route = f"{int(route_digits):03d}"
    return district, county, route, suffix, {
        "literal": literal,
        "county_had_trailing_period": county_token.endswith("."),
        "route_source_digits": route_digits,
    }


def _normalize_pm(value: object) -> str:
    literal = _excel_numeric_text(value).strip()
    if literal == "":
        raise ConservationError("Intersection Detail POST_MILE is blank")
    if PM_RE.fullmatch(literal) is None:
        raise ConservationError(f"invalid Intersection Detail POST_MILE token: {literal!r}")
    negative = literal.startswith("-")
    body = literal[1:] if negative else literal
    body = body.lstrip("0") or "0"
    if body.startswith("."):
        body = "0" + body
    return ("-" if negative else "") + body


def _numeric_identity_pm(value: object) -> str:
    """Canonical numeric physical identity, independent of display trailing zeroes."""
    literal = _text(value).strip()
    if literal == "" or PM_RE.fullmatch(literal) is None:
        raise ConservationError(
            f"invalid Intersection Detail identity POST_MILE token: {literal!r}")
    try:
        number = Decimal(literal)
    except InvalidOperation as exc:
        raise ConservationError(
            f"invalid Intersection Detail identity POST_MILE token: {literal!r}") from exc
    if number == 0:
        return "0"
    rendered = format(number.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _normalize_number(value: object) -> str:
    literal = _excel_numeric_text(value).strip()
    if literal == "":
        return ""
    if NUMBER_RE.fullmatch(literal) is None:
        raise ConservationError(f"invalid Intersection numeric token: {literal!r}")
    negative = literal.startswith("-")
    body = literal[1:] if negative else literal
    if "." in body:
        whole, fraction = body.split(".", 1)
        whole = whole.lstrip("0") or "0"
        fraction = fraction.rstrip("0")
        body = whole + (f".{fraction}" if fraction else "")
    else:
        body = body.lstrip("0") or "0"
    return ("-" if negative else "") + body


def _excel_numeric_text(value: object) -> str:
    """Mirror only Excel/openpyxl's numeric-cell binary64 materialization.

    ``phase3_xlsx_stream`` intentionally retains the exact OOXML decimal
    lexical.  The production writer read the authoritative workbook through
    openpyxl, so an ordinary numeric cell such as 0.92100000000000004 reached
    its narrow numeric canon as binary64 0.921.  Text that merely looks numeric
    must not receive this conversion.  Reject values whose shortest finite
    binary64 form requires more than Excel's 15 significant decimal digits.
    """
    if not isinstance(value, Decimal):
        return _text(value)
    if not value.is_finite():
        raise ConservationError("non-finite Decimal source value")
    try:
        binary64 = float(value)
    except (OverflowError, ValueError) as exc:
        raise ConservationError("XLSX numeric scalar is outside binary64 range") from exc
    if not math.isfinite(binary64):
        raise ConservationError("XLSX numeric scalar is outside finite binary64 range")
    if value != 0 and binary64 == 0.0:
        raise ConservationError("XLSX numeric scalar underflows binary64")
    shortest = repr(binary64)
    decimal = Decimal(shortest)
    significant = 1 if decimal.is_zero() else len(decimal.normalize().as_tuple().digits)
    if significant > 15:
        raise ConservationError(
            "XLSX numeric scalar requires more than 15 significant digits")
    return shortest


def _normalize_date(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    literal = _text(value).strip()
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", literal)
    if match:
        month, day, year = map(int, match.groups())
    else:
        match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?", literal)
        if match:
            year, month, day = map(int, match.groups())
        else:
            match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{2})", literal)
            if match is None:
                raise ConservationError(f"invalid Intersection Detail date token: {literal!r}")
            short, month, day = map(int, match.groups())
            year = (1900 if short >= 30 else 2000) + short
    try:
        return date(year, month, day).isoformat()
    except ValueError as exc:
        raise ConservationError(f"invalid Intersection Detail date token: {literal!r}") from exc


def _normalize_bool(value: object) -> str:
    if type(value) is bool:
        return "Y" if value else "N"
    if isinstance(value, Decimal) and value in (Decimal(0), Decimal(1)):
        literal = str(int(value))
    else:
        literal = _text(value).strip()
    return BOOL_MAP.get(literal.upper(), literal)


def _normalize_control(value: object) -> object:
    literal = _text(value).strip()
    return "S" if literal.upper() in SIGNALIZED_CODES else _scalar(value)


def _project_raw_row(row: Sequence[object]) -> tuple[tuple[object, ...], dict[str, object]]:
    if len(row) != len(RAW_HEADERS):
        raise ConservationError(f"raw row width {len(row)} != {len(RAW_HEADERS)}")
    values = dict(zip(RAW_HEADERS, row))
    district, county, route, suffix, location_info = _parse_location(values["LOCATION"])
    pm = _normalize_pm(values["POST_MILE"])
    identity_pm = _numeric_identity_pm(values["POST_MILE"])
    projected = (
        route,
        _scalar(values["PP"]),
        suffix,
        pm,
        _normalize_date(values["DATE_REC"]),
        _scalar(values["HG"]),
        _scalar(values["CITY_CODE"]),
        _scalar(values["RU"]),
        _normalize_date(values["EFF_DATE_INT"]),
        _scalar(values["TY_INT"]),
        _normalize_date(values["EFF_DATE_CT"]),
        _normalize_control(values["TY_CT"]),
        _normalize_date(values["EFF_DATE_LT"]),
        _normalize_bool(values["LT_TY"]),
        _normalize_date(values["EFF_DATE_ML"]),
        _normalize_bool(values["MAIN_SM"]),
        _scalar(values["MAIN_LC"]),
        _normalize_bool(values["MAIN_RC"]),
        _scalar(values["MAIN_TF"]),
        _scalar(values["MAIN_NL"]),
        _scalar(values["DESCRIPTION"]),
        _normalize_number(values["MAIN_OVERRIDE"]),
        _normalize_date(values["CROSS_BEGIN_DATE"]),
        _normalize_bool(values["CS_SM"]),
        _scalar(values["CS_LC"]),
        _normalize_bool(values["CS_RC"]),
        _scalar(values["CS_TF"]),
        _scalar(values["CS_NL"]),
        _normalize_date(values["EFF_DATE"]),
        _normalize_number(values["CROSS_ROUTE_NAME"]),
        _scalar(values["CROSS_PM_PREFIX"]),
        _normalize_number(values["CROSS_POSTMILE"]),
        _scalar(values["CROSS_PM_SUFFIX"]),
        _normalize_number(values["X_CROSS_OVERRIDE"]),
        district,
        county,
    )
    pp = _scalar(values["PP"])
    physical_identity = (route, county, pp, identity_pm)
    lossless_identity = (district, county, route, suffix, pp, identity_pm)
    return projected, {
        "district": district,
        "county": county,
        "route": route,
        "route_suffix": suffix,
        "pp": pp,
        "postmile": pm,
        "identity_numeric_postmile": identity_pm,
        "physical_identity": physical_identity,
        "lossless_identity": lossless_identity,
        "location_info": location_info,
    }


def _counter_summary(counter: Counter[tuple[object, ...]]) -> dict[str, int]:
    duplicates = [count for count in counter.values() if count > 1]
    return {
        "unique": len(counter),
        "duplicate_groups": len(duplicates),
        "duplicate_occurrences": sum(duplicates),
        "duplicate_occurrences_beyond_first": sum(count - 1 for count in duplicates),
        "max_multiplicity": max(counter.values(), default=0),
    }


def _key_text(key: Sequence[object]) -> str:
    return "|".join(_text(item) for item in key)


def _numeric_pm_collision_diagnostics(
        infos: Sequence[dict[str, object]]) -> dict[str, object]:
    """Return weaker-key diagnostics using one exact numeric-PM partition."""
    within_county: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    route_pm_counties: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    route_pp_pm_counties: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    for info in infos:
        route = str(info["route"])
        county = str(info["county"])
        pm = str(info["identity_numeric_postmile"])
        pp = _text(info["pp"])
        within_county[(route, county, pm)].add(pp)
        route_pm_counties[(route, pm)].add(county)
        route_pp_pm_counties[(route, pp, pm)].add(county)

    within = [
        (route, county, pm, tuple(sorted(values)))
        for (route, county, pm), values in within_county.items() if len(values) > 1
    ]
    within.sort()

    def county_summary(groups: dict[tuple[object, ...], set[str]]) -> dict[str, int]:
        multi = [counties for counties in groups.values() if len(counties) > 1]
        return {
            "multi_county_keys": len(multi),
            "county_identities": sum(len(counties) for counties in multi),
        }

    return {
        "within_county_route_pm_pp_collisions": [
            {"route": route, "county": county, "postmile": pm,
             "PP_values": list(values)}
            for route, county, pm, values in within
        ],
        "route_plus_numeric_pm_cross_county": county_summary(route_pm_counties),
        "route_plus_complete_pp_plus_pm_cross_county": county_summary(
            route_pp_pm_counties),
    }


def _collision_census(raw_rows: Sequence[Sequence[object]],
                      projected_rows: Sequence[Sequence[object]],
                      infos: Sequence[dict[str, object]]) -> dict[str, object]:
    physical = Counter(tuple(info["physical_identity"]) for info in infos)
    lossless = Counter(tuple(info["lossless_identity"]) for info in infos)
    physical_rows: defaultdict[tuple[object, ...], list[int]] = defaultdict(list)
    raw_digests: defaultdict[tuple[object, ...], set[str]] = defaultdict(set)
    for ordinal, (row, info) in enumerate(zip(raw_rows, infos), start=1):
        key = tuple(info["physical_identity"])
        physical_rows[key].append(ordinal)
        raw_digests[key].add(_sha(_row_wire(row)))
    nonidentical = [
        (key, physical_rows[key], len(raw_digests[key]))
        for key, count in physical.items()
        if count > 1 and len(raw_digests[key]) > 1
    ]

    numeric_pm_diagnostics = _numeric_pm_collision_diagnostics(infos)

    projected_groups: defaultdict[str, list[int]] = defaultdict(list)
    omitted_groups: defaultdict[str, set[str]] = defaultdict(set)
    omitted_indices = tuple(RAW_HEADERS.index(field) for field in SOURCE_ONLY_FIELDS)
    for ordinal, (raw, projected) in enumerate(zip(raw_rows, projected_rows), start=1):
        digest = _sha(_row_wire(projected))
        projected_groups[digest].append(ordinal)
        omitted_groups[digest].add(_sha(_row_wire(tuple(raw[index] for index in omitted_indices))))
    lossy_groups = [
        {"projected_row_sha256": digest,
         "occurrences": len(projected_groups[digest]),
         "distinct_source_only_claim_sets": len(omitted_groups[digest]),
         "sample_ordinals": projected_groups[digest][:10]}
        for digest in sorted(projected_groups)
        if len(omitted_groups[digest]) > 1
    ]

    return {
        "physical_identity_definition": ["base_route", "county", "complete_PP", "numeric_POST_MILE"],
        "lossless_identity_definition": [
            "district", "county", "base_route", "route_suffix", "complete_PP", "numeric_POST_MILE"
        ],
        "physical_identity": _counter_summary(physical),
        "lossless_identity": _counter_summary(lossless),
        "physical_identity_ordered_typed_sha256": _ordered_digest(
            [tuple(info["physical_identity"]) for info in infos]),
        "lossless_identity_ordered_typed_sha256": _ordered_digest(
            [tuple(info["lossless_identity"]) for info in infos]),
        "physical_identity_multiplicity_sha256": _multiset_digest(
            [tuple(info["physical_identity"]) for info in infos])[0],
        "same_identity_nonidentical": {
            "groups": len(nonidentical),
            "occurrences": sum(len(ordinals) for _key, ordinals, _distinct in nonidentical),
            "manifest": [
                {"key": _key_text(key), "ordinals": ordinals,
                 "distinct_typed_raw_rows": distinct}
                for key, ordinals, distinct in nonidentical
            ],
        },
        **numeric_pm_diagnostics,
        "normalized_identical_rows_with_distinct_source_only_facts": {
            "groups": len(lossy_groups),
            "manifest": lossy_groups,
        },
        "route_census": dict(sorted(Counter(str(info["route"]) for info in infos).items())),
        "county_census": dict(sorted(Counter(str(info["county"]) for info in infos).items())),
        "district_census": dict(sorted(Counter(str(info["district"]) for info in infos).items())),
        "route_suffix_census": dict(sorted(Counter(str(info["route_suffix"]) for info in infos).items())),
    }


def _projection_comparison(expected: Sequence[Sequence[object]],
                           actual: Sequence[Sequence[object]]) -> dict[str, object]:
    field_mismatches: Counter[str] = Counter()
    examples = []
    for ordinal, (left, right) in enumerate(zip(expected, actual), start=1):
        for column, (a, b) in enumerate(zip(left, right)):
            if _typed(a) != _typed(b):
                field = NORMALIZED_HEADERS[column]
                field_mismatches[field] += 1
                if len(examples) < 50:
                    examples.append({
                        "ordinal": ordinal,
                        "normalized_source_row": ordinal + 1,
                        "field": field,
                        "expected": _typed(a),
                        "actual": _typed(b),
                    })
    expected_multiset, _ = _multiset_digest(expected)
    actual_multiset, _ = _multiset_digest(actual)
    ordered_exact = len(expected) == len(actual) and not field_mismatches
    return {
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "missing_or_extra_row_count": abs(len(expected) - len(actual)),
        "typed_cell_mismatch_count": sum(field_mismatches.values()),
        "typed_cell_mismatches_by_field": dict(sorted(field_mismatches.items())),
        "mismatch_examples": examples,
        "ordered_exact": ordered_exact,
        "multiset_exact": expected_multiset == actual_multiset,
        "expected_ordered_sha256": _ordered_digest(expected),
        "actual_ordered_sha256": _ordered_digest(actual),
        "expected_multiset_sha256": expected_multiset,
        "actual_multiset_sha256": actual_multiset,
    }


def _domain_and_order_census(raw_sheet: StreamedSheet,
                             normalized_sheet: StreamedSheet,
                             raw_rows: Sequence[Sequence[object]],
                             projected_rows: Sequence[Sequence[object]],
                             infos: Sequence[dict[str, object]]) -> dict[str, object]:
    indices = {header: index for index, header in enumerate(RAW_HEADERS)}
    bool_domains = {}
    unknown_boolean = {}
    for field in BOOLEAN_FIELDS:
        counts = Counter(_text(row[indices[field]]).strip() for row in raw_rows)
        bool_domains[field] = dict(sorted(counts.items()))
        unknown = {
            value: count for value, count in counts.items()
            if value.upper() not in {"", "Y", "N", "0", "1"}
        }
        if unknown:
            unknown_boolean[field] = unknown
    control_counts = Counter(_text(row[indices["TY_CT"]]).strip() for row in raw_rows)
    int_type_counts = Counter(_text(row[indices["TY_INT"]]).strip() for row in raw_rows)
    date_domains = {
        field: dict(sorted(Counter(_text(row[indices[field]]).strip() for row in raw_rows).items()))
        for field in DATE_FIELDS
    }
    source_rows = [row.source_row for row in raw_sheet.rows]
    normalized_source_rows = [row.source_row for row in normalized_sheet.rows]
    return {
        "raw_physical_rows_contiguous": source_rows == list(range(2, 2 + len(source_rows))),
        "normalized_physical_rows_contiguous": (
            normalized_source_rows == list(range(2, 2 + len(normalized_source_rows)))),
        "raw_source_row_order_sha256": _ordered_digest([(value,) for value in source_rows]),
        "normalized_source_row_order_sha256": _ordered_digest(
            [(value,) for value in normalized_source_rows]),
        "projected_row_order_sha256": _ordered_digest(projected_rows),
        "physical_identity_order_sha256": _ordered_digest(
            [tuple(info["physical_identity"]) for info in infos]),
        "boolean_domains": bool_domains,
        "unknown_boolean_domains": unknown_boolean,
        "control_type_domain": dict(sorted(control_counts.items())),
        "control_type_folded_to_S_count": sum(
            count for value, count in control_counts.items() if value.upper() in SIGNALIZED_CODES),
        "intersection_type_domain": dict(sorted(int_type_counts.items())),
        "date_domains": date_domains,
        "location_county_period_count": sum(
            bool(info["location_info"]["county_had_trailing_period"]) for info in infos),
        "classified_anomalies": (
            [{"kind": "unknown_boolean_domain", "field": field, "values": values}
             for field, values in sorted(unknown_boolean.items())]
        ),
        "unclassified_anomalies": [],
    }


def _semantic_mutation_probes(raw_rows: Sequence[Sequence[object]],
                              projected_rows: Sequence[Sequence[object]],
                              infos: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    probes: list[dict[str, object]] = []

    raw_reordered = list(raw_rows)
    raw_reordered[0], raw_reordered[1] = raw_reordered[1], raw_reordered[0]
    raw_reordered_projection = [_project_raw_row(row)[0] for row in raw_reordered]
    probes.append({
        "name": "raw row reorder",
        "detected": (
            _ordered_digest(raw_reordered) != _ordered_digest(raw_rows)
            and _multiset_digest(raw_reordered)[0] == _multiset_digest(raw_rows)[0]
            and _ordered_digest(raw_reordered_projection) != _ordered_digest(projected_rows)
            and _multiset_digest(raw_reordered_projection)[0]
            == _multiset_digest(projected_rows)[0]),
        "expected_effect": "raw and independently projected order change; multiplicity does not",
    })

    raw_deleted = list(raw_rows[:-1])
    probes.append({
        "name": "raw row deletion",
        "detected": (len(raw_deleted) != len(raw_rows)
                     and _multiset_digest(raw_deleted)[0] != _multiset_digest(raw_rows)[0]),
        "expected_effect": "raw count and multiplicity digest change",
    })

    raw_inserted = list(raw_rows) + [raw_rows[0]]
    probes.append({
        "name": "raw duplicate insertion",
        "detected": (len(raw_inserted) != len(raw_rows)
                     and _multiset_digest(raw_inserted)[0] != _multiset_digest(raw_rows)[0]),
        "expected_effect": "raw count and multiplicity digest change",
    })

    raw_projected_cell = [list(row) for row in raw_rows]
    desc_index = RAW_HEADERS.index("DESCRIPTION")
    raw_projected_cell[0][desc_index] = "#STAGE6-RAW-PROJECTED-MUTATION#"
    probes.append({
        "name": "raw projected-cell mutation",
        "detected": (
            _ordered_digest(raw_projected_cell) != _ordered_digest(raw_rows)
            and _ordered_digest([_project_raw_row(row)[0] for row in raw_projected_cell])
            != _ordered_digest(projected_rows)),
        "expected_effect": "raw and independently projected row digests change",
    })

    reordered = list(projected_rows)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    probes.append({
        "name": "normalized row reorder",
        "detected": (_ordered_digest(reordered) != _ordered_digest(projected_rows)
                     and _multiset_digest(reordered)[0] == _multiset_digest(projected_rows)[0]),
        "expected_effect": "ordered digest changes while multiset digest remains equal",
    })

    deleted = list(projected_rows[:-1])
    probes.append({
        "name": "normalized row deletion",
        "detected": (len(deleted) != len(projected_rows)
                     and _multiset_digest(deleted)[0] != _multiset_digest(projected_rows)[0]),
        "expected_effect": "row count and multiset digest change",
    })

    inserted = list(projected_rows) + [projected_rows[0]]
    probes.append({
        "name": "normalized duplicate insertion",
        "detected": (len(inserted) != len(projected_rows)
                     and _multiset_digest(inserted)[0] != _multiset_digest(projected_rows)[0]),
        "expected_effect": "row count and multiplicity digest change",
    })

    projected_mutation = [list(row) for row in projected_rows]
    projected_mutation[0][NORMALIZED_HEADERS.index("Description")] = "#STAGE6-MUTATION#"
    probes.append({
        "name": "normalized projected-cell mutation",
        "detected": _ordered_digest(projected_mutation) != _ordered_digest(projected_rows),
        "expected_effect": "row and Description field digests change",
    })

    sidecar_mutation = [list(row) for row in projected_rows]
    sidecar_mutation[0][NORMALIZED_HEADERS.index("TSN County")] = "ZZZ"
    probes.append({
        "name": "normalized tail-sidecar mutation",
        "detected": _ordered_digest(sidecar_mutation) != _ordered_digest(projected_rows),
        "expected_effect": "row and TSN County field digests change",
    })

    for field in SOURCE_ONLY_FIELDS:
        mutated = [list(row) for row in raw_rows]
        field_index = RAW_HEADERS.index(field)
        target = next(index for index, row in enumerate(mutated)
                      if row[field_index] not in (None, ""))
        mutated[target][field_index] = _text(mutated[target][field_index]) + "#MUT"
        projected_after = [_project_raw_row(row)[0] for row in mutated]
        raw_before = _field_digest([row[field_index] for row in raw_rows])
        raw_after = _field_digest([row[field_index] for row in mutated])
        probes.append({
            "name": f"source-only {field} mutation",
            "detected": (
                raw_before["ordered_typed_sha256"] != raw_after["ordered_typed_sha256"]
                and _ordered_digest(projected_after) == _ordered_digest(projected_rows)),
            "expected_effect": (
                "typed raw field digest changes while visible normalized projection remains blind"),
        })

    typed = [list(row) for row in raw_rows]
    typed_location = None
    for column in range(len(RAW_HEADERS)):
        for ordinal, row in enumerate(typed):
            if isinstance(row[column], Decimal):
                typed_location = (ordinal, column)
                break
        if typed_location is not None:
            break
    if typed_location is None:
        raise ConservationError("mutation probe found no Decimal source cell")
    ordinal, column = typed_location
    typed[ordinal][column] = str(typed[ordinal][column])
    probes.append({
        "name": "same-text cross-type raw mutation",
        "detected": _ordered_digest(typed) != _ordered_digest(raw_rows),
        "expected_effect": "typed digest distinguishes Decimal from equal-looking text",
    })

    pp_mutated = [list(row) for row in raw_rows]
    pp_index = RAW_HEADERS.index("PP")
    pp_mutated[0][pp_index] = "M" if _text(pp_mutated[0][pp_index]) != "M" else "L"
    pp_projected = [_project_raw_row(row)[0] for row in pp_mutated]
    probes.append({
        "name": "ID complete-PP identity variant",
        "detected": (_ordered_digest(pp_projected) != _ordered_digest(projected_rows)
                     and _project_raw_row(pp_mutated[0])[1]["physical_identity"]
                     != infos[0]["physical_identity"]),
        "expected_effect": "both visible PR and complete physical identity change",
    })

    known_collision_index = next(
        index for index, info in enumerate(infos)
        if (str(info["route"]), str(info["county"]), str(info["postmile"]))
        == ("101", "SF", "5.450"))
    county_mutated = [list(row) for row in raw_rows]
    loc_index = RAW_HEADERS.index("LOCATION")
    old_location = _text(county_mutated[known_collision_index][loc_index])
    county_mutated[known_collision_index][loc_index] = re.sub(
        r"^(\d{2}) +[A-Z]{2,3}\.? +", r"\1 ALA ", old_location.strip().upper())
    county_projected = [_project_raw_row(row)[0] for row in county_mutated]
    probes.append({
        "name": "known weak-collision county swap",
        "detected": (
            _ordered_digest(county_projected) != _ordered_digest(projected_rows)
            and county_projected[known_collision_index][NORMALIZED_HEADERS.index("TSN County")]
            == "ALA"),
        "expected_effect": "sidecar county and lossless physical identity change",
    })

    pm_index = RAW_HEADERS.index("POST_MILE")
    trailing_zero_mutated = list(raw_rows[known_collision_index])
    original_pm = _text(trailing_zero_mutated[pm_index]).strip()
    trailing_zero_mutated[pm_index] = original_pm + "0"
    original_info = infos[known_collision_index]
    mutated_projection, mutated_info = _project_raw_row(trailing_zero_mutated)
    mutated_infos = list(infos)
    mutated_infos[known_collision_index] = mutated_info
    probes.append({
        "name": "numeric identities and weaker-key censuses ignore display-only trailing PM zero",
        "detected": (
            mutated_info["physical_identity"] == original_info["physical_identity"]
            and mutated_info["lossless_identity"] == original_info["lossless_identity"]
            and _numeric_pm_collision_diagnostics(mutated_infos)
            == _numeric_pm_collision_diagnostics(infos)
            and mutated_projection[NORMALIZED_HEADERS.index("PM")]
            != projected_rows[known_collision_index][NORMALIZED_HEADERS.index("PM")]),
        "expected_effect": (
            "numeric identities and all weaker-key censuses remain equal while display PM preserves source precision"),
    })

    duplicate_groups: defaultdict[tuple[object, ...], list[int]] = defaultdict(list)
    for index, info in enumerate(infos):
        duplicate_groups[tuple(info["physical_identity"])].append(index)
    duplicate_pair = next(indices for indices in duplicate_groups.values()
                          if len(indices) > 1
                          and projected_rows[indices[0]] != projected_rows[indices[1]])
    duplicate_reorder = list(projected_rows)
    left, right = duplicate_pair[:2]
    duplicate_reorder[left], duplicate_reorder[right] = (
        duplicate_reorder[right], duplicate_reorder[left])
    probes.append({
        "name": "same-physical-identity duplicate occurrence reorder",
        "detected": (
            _ordered_digest(duplicate_reorder) != _ordered_digest(projected_rows)
            and _multiset_digest(duplicate_reorder)[0] == _multiset_digest(projected_rows)[0]),
        "expected_effect": "occurrence order changes while multiplicity remains exact",
    })

    helper_cases = {
        "numeric_zero_distinct_from_blank": _normalize_number(Decimal(0)) == "0"
        and _normalize_number(None) == "",
        "boolean_zero_distinct_from_blank": _normalize_bool(Decimal(0)) == "N"
        and _normalize_bool(None) == "",
        "numeric_padding": _normalize_number("00058.000") == "58",
        "pm_leading_zero_only": _normalize_pm(" 000.340") == "0.340",
        "two_digit_date_window": (_normalize_date("29-12-31") == "2029-12-31"
                                  and _normalize_date("30-01-01") == "1930-01-01"),
    }
    for name, detected in helper_cases.items():
        probes.append({"name": name, "detected": detected,
                       "expected_effect": "independent edge-case contract remains exact"})

    malformed_numeric_detected = True
    for token in ("BAD", "1e3", ".5"):
        try:
            _normalize_number(token)
        except ConservationError:
            continue
        malformed_numeric_detected = False
    probes.append({
        "name": "malformed numeric domains rejected",
        "detected": malformed_numeric_detected,
        "expected_effect": "undeclared numeric lexicals cannot pass through as facts",
    })

    malformed_location_detected = False
    try:
        _parse_location("12 ORA")
    except ConservationError:
        malformed_location_detected = True
    probes.append({
        "name": "malformed LOCATION rejected",
        "detected": malformed_location_detected,
        "expected_effect": "invalid location cannot be silently generalized",
    })

    synthetic_error = (
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<sheetData><row r="1"><c r="A1" t="e"><v>#N/A</v></c></row></sheetData>'
        b'</worksheet>'
    )
    probes.append({
        "name": "required-cell OOXML error mutation",
        "detected": _worksheet_error_references(synthetic_error) == ["A1"],
        "expected_effect": "Stage 6 family admission rejects t=e rather than blessing its token as text",
    })

    return probes


def _structural_mutation_contracts(gate_execution: dict[str, object]) -> list[dict[str, object]]:
    """Persist the low-level gate that actually executed in this audit."""
    reader = Path(__file__).with_name("phase3_xlsx_stream.py")
    gate = Path(__file__).with_name("check_phase3_xlsx_stream.py")
    return [
        {
            "scope": "formula/error, duplicate/extra/header order, unsafe archive/XML",
            "enforced_by": str(reader),
            "reader_sha256": hashlib.sha256(reader.read_bytes()).hexdigest(),
            "required_separate_gate": str(gate),
            "gate_sha256": hashlib.sha256(gate.read_bytes()).hexdigest(),
            "execution_status_in_this_result": "executed_pass",
            "execution": gate_execution,
        },
        {
            "scope": (
                "source SHA/size, one visible sheet, bound-descriptor/path identity, "
                "preserved-mtime replacement and A-to-B-to-A interposition"),
            "enforced_by": "phase3_xlsx_stream.read_sheet + local topology/final revalidation",
            "required_separate_gate": str(gate),
            "gate_sha256": hashlib.sha256(gate.read_bytes()).hexdigest(),
            "execution_status_in_this_result": "executed_pass",
            "execution": gate_execution,
        },
    ]


def run(raw_path: Path, normalized_path: Path, normalized_sidecar_path: Path,
        normalized_binding: dict[str, object]) -> dict[str, object]:
    if tuple(FIELD_DISPOSITIONS) != RAW_HEADERS:
        raise ConservationError("field dispositions do not cover the exact raw schema in order")
    if len(FIELD_DISPOSITIONS) != len(RAW_HEADERS):
        raise ConservationError("field dispositions are incomplete or duplicated")

    generator_path = Path(__file__).resolve()
    reader_path = generator_path.with_name("phase3_xlsx_stream.py")
    gate_path = generator_path.with_name("check_phase3_xlsx_stream.py")
    code_initial = {
        "generator": capture_file_identity(generator_path),
        "reader": capture_file_identity(reader_path),
        "reader_mutation_gate": capture_file_identity(gate_path),
    }
    gate_process = subprocess.run(
        [sys.executable, str(gate_path)], cwd=str(generator_path.parent.parent),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
    gate_execution = {
        "command": [sys.executable, str(gate_path)],
        "exit_code": gate_process.returncode,
        "stdout": gate_process.stdout.strip(),
    }
    if gate_process.returncode != 0:
        raise ConservationError(
            f"independent reader mutation gate failed: {gate_process.stdout.strip()}")
    r7_witness_initial = capture_file_identity(R7_WITNESS_RESULT)
    if (r7_witness_initial.size, r7_witness_initial.sha256) != (
            R7_WITNESS_BINDING["bytes"], R7_WITNESS_BINDING["sha256"]):
        raise ConservationError("accepted r7 lifecycle witness binding mismatch")
    sidecar_initial, sidecar_document = _read_bound_sidecar(
        normalized_sidecar_path, NORMALIZED_R7_SIDECAR_BINDING)

    raw_spec = SheetSpec(
        RAW_BINDING["sheet"],
        tuple(ColumnSpec(header, SCALAR) for header in RAW_HEADERS),
        exact_schema=True,
    )
    normalized_spec = SheetSpec(
        normalized_binding["sheet"],
        tuple(ColumnSpec(header, SCALAR) for header in NORMALIZED_HEADERS),
        exact_schema=True,
    )

    raw_topology = _workbook_topology(raw_path)
    raw_error_scan = _error_cell_scan(raw_path, RAW_BINDING, "raw Intersection Detail")
    raw_sheet = read_sheet(raw_path, raw_spec)
    _require_binding(raw_sheet, raw_topology, RAW_BINDING, "raw Intersection Detail")
    normalized_topology = _workbook_topology(normalized_path)
    normalized_error_scan = _error_cell_scan(
        normalized_path, normalized_binding, "normalized Intersection Detail")
    normalized_sheet = read_sheet(normalized_path, normalized_spec)
    _require_binding(
        normalized_sheet, normalized_topology, normalized_binding,
        "normalized Intersection Detail",
    )

    raw_rows = [tuple(row.values) for row in raw_sheet.rows]
    normalized_rows = [tuple(row.values) for row in normalized_sheet.rows]
    if len(raw_rows) != RAW_BINDING["rows"]:
        raise ConservationError(f"raw row count {len(raw_rows)} != {RAW_BINDING['rows']}")
    if len(normalized_rows) != normalized_binding["rows"]:
        raise ConservationError(
            f"normalized row count {len(normalized_rows)} != {normalized_binding['rows']}")
    blank_raw = [row.source_row for row in raw_sheet.rows
                 if not any(value not in (None, "") for value in row.values)]
    blank_normalized = [row.source_row for row in normalized_sheet.rows
                        if not any(value not in (None, "") for value in row.values)]
    if blank_raw or blank_normalized:
        raise ConservationError(
            f"physical blank data rows are forbidden: raw={blank_raw[:10]}, "
            f"normalized={blank_normalized[:10]}")

    projected_rows = []
    infos = []
    for raw_row in raw_rows:
        projected, info = _project_raw_row(raw_row)
        projected_rows.append(projected)
        infos.append(info)

    projection = _projection_comparison(projected_rows, normalized_rows)
    collisions = _collision_census(raw_rows, projected_rows, infos)
    census = _domain_and_order_census(
        raw_sheet, normalized_sheet, raw_rows, projected_rows, infos)
    mutations = _semantic_mutation_probes(raw_rows, projected_rows, infos)

    blocking_findings = [
        {
            "id": "ID-S6-001", "severity": "P1", "status": "open",
            "title": "Normalized Intersection Detail omits MAIN_EFF_DATE",
            "field": "MAIN_EFF_DATE",
            "evidence": _field_digest(
                [row[RAW_HEADERS.index("MAIN_EFF_DATE")] for row in raw_rows]),
            "impact": (
                "The canonical normalized-library Report View path cannot supply the "
                "TSN second-mainline effective date and displays it blank."),
            "requirement": (
                "Retain the typed claim in normalized bytes (a hidden column is sufficient) "
                "or supply it through an equally immutable source-bound mechanism."),
        },
        {
            "id": "ID-S6-002", "severity": "P1", "status": "open",
            "title": "Normalized Intersection Detail omits MAIN_ADT",
            "field": "MAIN_ADT",
            "evidence": _field_digest(
                [row[RAW_HEADERS.index("MAIN_ADT")] for row in raw_rows]),
            "impact": "The canonical normalized-library Report View path displays TSN mainline ADT blank.",
            "requirement": "Retain the typed source claim for comparison context and evidence.",
        },
        {
            "id": "ID-S6-003", "severity": "P1", "status": "open",
            "title": "Normalized Intersection Detail omits CROSS_ADT",
            "field": "CROSS_ADT",
            "evidence": _field_digest(
                [row[RAW_HEADERS.index("CROSS_ADT")] for row in raw_rows]),
            "impact": "The canonical normalized-library Report View path displays TSN cross-street ADT blank.",
            "requirement": "Retain the typed source claim for comparison context and evidence.",
        },
    ]
    review_findings = [{
        "id": "ID-S6-004", "severity": "review",
        "status": "explicit_duplicate_occurrence_contract",
        "title": "Same-identity/nonidentical rows require occurrence-order preservation",
        "evidence": collisions["same_identity_nonidentical"],
        "requirement": (
            "Preserve raw occurrence order exactly; do not use weak-key similarity pairing "
            "inside the TSN normalizer."),
    }]

    # Compute every expensive fact/digest before the acceptance revalidation.
    # The identities below are therefore the final live-source/code generation
    # check, not a premature check followed by more source-derived work.
    structural_contracts = _structural_mutation_contracts(gate_execution)
    raw_digests = _dataset_digests(RAW_HEADERS, raw_rows)
    projected_digests = _dataset_digests(NORMALIZED_HEADERS, projected_rows)
    normalized_digests = _dataset_digests(NORMALIZED_HEADERS, normalized_rows)

    raw_final_identity = capture_file_identity(raw_path)
    normalized_final_identity = capture_file_identity(normalized_path)
    sidecar_final_identity = capture_file_identity(normalized_sidecar_path)
    r7_witness_final = capture_file_identity(R7_WITNESS_RESULT)
    code_final = {
        "generator": capture_file_identity(generator_path),
        "reader": capture_file_identity(reader_path),
        "reader_mutation_gate": capture_file_identity(gate_path),
    }
    final_identities_current = (
        raw_final_identity == raw_sheet.pre_identity
        and normalized_final_identity == normalized_sheet.pre_identity
        and sidecar_final_identity == sidecar_initial
        and r7_witness_final == r7_witness_initial
        and code_final == code_initial
    )

    expected_collision_manifest = [
        {"route": route, "county": county, "postmile": pm, "PP_values": list(values)}
        for route, county, pm, values in EXPECTED_WITHIN_COUNTY_PP_COLLISIONS
    ]
    audit_invariants = {
        "source_bindings_exact": True,
        "workbook_topologies_exact": True,
        "formula_and_error_cells_inadmissible": (
            not raw_error_scan["error_cells"] and not normalized_error_scan["error_cells"]),
        "r7_outcome_sidecar_exact_and_complete": (
            sidecar_document.get("completion") == "complete"
            and sidecar_document.get("skipped_inputs") == 0
            and sidecar_document.get("failed_inputs") == 0),
        "r7_lifecycle_witness_exact": r7_witness_final == r7_witness_initial,
        "reader_mutation_gate_executed_and_passed": gate_process.returncode == 0,
        "generator_reader_and_gate_generation_stable": code_final == code_initial,
        "final_source_identities_current": final_identities_current,
        "raw_schema_exact": raw_sheet.headers == RAW_HEADERS,
        "normalized_schema_exact": normalized_sheet.headers == NORMALIZED_HEADERS,
        "raw_row_count_exact": len(raw_rows) == RAW_BINDING["rows"],
        "normalized_row_count_exact": len(normalized_rows) == normalized_binding["rows"],
        "all_raw_fields_disposed_exactly_once": tuple(FIELD_DISPOSITIONS) == RAW_HEADERS,
        "zero_unexplained_projection_residue": projection["ordered_exact"],
        "ordered_and_multiset_projection_exact": (
            projection["ordered_exact"] and projection["multiset_exact"]),
        "physical_identity_expected_unique_count": (
            collisions["physical_identity"]["unique"] == 16_611),
        "same_identity_nonidentical_expected": (
            collisions["same_identity_nonidentical"]["groups"] == 15
            and collisions["same_identity_nonidentical"]["occurrences"] == 30),
        "lossless_identity_multiplicity_expected": (
            collisions["lossless_identity"]["unique"] == 16_611
            and collisions["lossless_identity"]["duplicate_groups"] == 15
            and collisions["lossless_identity"]["duplicate_occurrences"] == 30),
        "within_county_pp_collision_manifest_exact": (
            collisions["within_county_route_pm_pp_collisions"] == expected_collision_manifest),
        "route_pm_cross_county_census_exact": (
            collisions["route_plus_numeric_pm_cross_county"]
            == {"multi_county_keys": 78, "county_identities": 156}),
        "complete_pp_pm_cross_county_census_exact": (
            collisions["route_plus_complete_pp_plus_pm_cross_county"]
            == {"multi_county_keys": 71, "county_identities": 142}),
        "raw_and_normalized_physical_rows_contiguous": (
            census["raw_physical_rows_contiguous"]
            and census["normalized_physical_rows_contiguous"]),
        "no_unclassified_domain_anomalies": not census["unclassified_anomalies"],
        "mutation_probes_all_detected": all(probe["detected"] for probe in mutations),
    }
    projection_exact = projection["ordered_exact"] and projection["multiset_exact"]
    audit_complete = all(audit_invariants.values())
    normalized_full_conservation = (
        audit_complete and projection_exact and not blocking_findings)

    return {
        "schema_version": 2,
        "audit": "Stage 6 Intersection Detail raw-to-normalized conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_comparators_imported": False,
            "application_evidence_adapters_imported": False,
            "reader": "build/phase3_xlsx_stream.py stdlib OOXML reader",
            "permanent_reader_mutation_gate": "build/check_phase3_xlsx_stream.py",
        },
        "bindings": {
            "raw": RAW_BINDING,
            "normalized": normalized_binding,
            "normalized_outcome_sidecar": NORMALIZED_R7_SIDECAR_BINDING,
            "r7_lifecycle_witness": R7_WITNESS_BINDING,
        },
        "code_provenance": {
            label: {
                "initial": _identity_dict(code_initial[label]),
                "acceptance_revalidation_after_all_digests": _identity_dict(code_final[label]),
            }
            for label in code_initial
        },
        "source_identity": {
            "r7_lifecycle_witness": {
                "path": str(R7_WITNESS_RESULT.resolve()),
                "initial": _identity_dict(r7_witness_initial),
                "acceptance_revalidation_after_all_digests": _identity_dict(
                    r7_witness_final),
            },
            "raw": {
                "path": str(raw_path.resolve()),
                "topology_capture": raw_topology,
                "error_cell_scan": raw_error_scan,
                "worksheet_pre_read": _identity_dict(raw_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(raw_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(raw_final_identity),
            },
            "normalized": {
                "path": str(normalized_path.resolve()),
                "topology_capture": normalized_topology,
                "error_cell_scan": normalized_error_scan,
                "worksheet_pre_read": _identity_dict(normalized_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(normalized_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(normalized_final_identity),
            },
            "normalized_outcome_sidecar": {
                "path": str(normalized_sidecar_path.resolve()),
                "initial_read": _identity_dict(sidecar_initial),
                "accepted_claims": {
                    "completion": sidecar_document["completion"],
                    "skipped_inputs": sidecar_document["skipped_inputs"],
                    "failed_inputs": sidecar_document["failed_inputs"],
                    "tsn_normalization_version": sidecar_document["tsn_normalization_version"],
                    "tsn_artifact_identity_token": sidecar_document["tsn_artifact_identity_token"],
                },
                "acceptance_revalidation_after_all_digests": _identity_dict(
                    sidecar_final_identity),
            },
        },
        "field_dispositions": FIELD_DISPOSITIONS,
        "raw_digests": raw_digests,
        "independently_projected_digests": projected_digests,
        "normalized_digests": normalized_digests,
        "projection_comparison": projection,
        "projection_residue": {
            "unexplained_typed_cells": projection["typed_cell_mismatch_count"],
            "unexplained_rows": projection["missing_or_extra_row_count"],
            "fully_classified": projection["ordered_exact"],
        },
        "identity_and_collision_census": collisions,
        "order_domain_and_anomaly_census": census,
        "semantic_mutation_probes": mutations,
        "structural_mutation_contracts": structural_contracts,
        "findings": {"blocking": blocking_findings, "review": review_findings},
        "audit_invariants": audit_invariants,
        "projection_exact": projection_exact,
        "stage6_family_audit_complete": audit_complete,
        "normalized_full_conservation": normalized_full_conservation,
        "post_result_write_revalidation_protocol": (
            "main() re-hashes both bound sources after final result bytes are written; "
            "a drift changes the process to exit 3 and the successful result is not accepted."),
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--normalized", type=Path, default=NORMALIZED_DEFAULT)
    parser.add_argument(
        "--normalized-sidecar", type=Path, default=NORMALIZED_SIDECAR_DEFAULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-open-findings", action="store_true",
        help="exit zero when the family audit is complete but documented product findings remain",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    binding = dict(NORMALIZED_R7_BINDING)
    try:
        result = run(args.raw, args.normalized, args.normalized_sidecar, binding)
    except Exception as exc:
        failure = {
            "schema_version": 2,
            "audit": "Stage 6 Intersection Detail raw-to-normalized conservation",
            "projection_exact": False,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        payload = json.dumps(failure, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        sys.stdout.write(json.dumps(failure, ensure_ascii=False) + "\n" if args.output else payload)
        return 2

    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        post_raw = capture_file_identity(args.raw)
        post_normalized = capture_file_identity(args.normalized)
        post_sidecar = capture_file_identity(args.normalized_sidecar)
        post_r7_witness = capture_file_identity(R7_WITNESS_RESULT)
        generator_path = Path(__file__).resolve()
        post_code = {
            "generator": capture_file_identity(generator_path),
            "reader": capture_file_identity(generator_path.with_name("phase3_xlsx_stream.py")),
            "reader_mutation_gate": capture_file_identity(
                generator_path.with_name("check_phase3_xlsx_stream.py")),
        }
        raw_expected = result["source_identity"]["raw"]["acceptance_revalidation"]
        norm_expected = result["source_identity"]["normalized"]["acceptance_revalidation"]
        sidecar_expected = result["source_identity"]["normalized_outcome_sidecar"][
            "acceptance_revalidation_after_all_digests"]
        r7_witness_expected = result["source_identity"]["r7_lifecycle_witness"][
            "acceptance_revalidation_after_all_digests"]
        post_write_current = (
            _identity_dict(post_raw) == raw_expected
            and _identity_dict(post_normalized) == norm_expected
            and _identity_dict(post_sidecar) == sidecar_expected
            and _identity_dict(post_r7_witness) == r7_witness_expected
            and all(
                _identity_dict(post_code[label])
                == result["code_provenance"][label][
                    "acceptance_revalidation_after_all_digests"]
                for label in post_code
            )
        )
        result_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
        acceptance_path = args.output.with_suffix(args.output.suffix + ".acceptance.json")
        acceptance = {
            "schema_version": 1,
            "result": str(args.output.resolve()),
            "result_bytes": args.output.stat().st_size,
            "result_sha256": result_hash,
            "post_result_write_revalidation": post_write_current,
            "post_result_write_identities": {
                "raw": _identity_dict(post_raw),
                "normalized": _identity_dict(post_normalized),
                "normalized_outcome_sidecar": _identity_dict(post_sidecar),
                "r7_lifecycle_witness": _identity_dict(post_r7_witness),
                **{label: _identity_dict(identity) for label, identity in post_code.items()},
            },
        }
        acceptance_path.write_text(
            json.dumps(acceptance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not post_write_current:
            failure = {
                "schema_version": 2,
                "audit": "Stage 6 Intersection Detail raw-to-normalized conservation",
                "projection_exact": False,
                "stage6_family_audit_complete": False,
                "normalized_full_conservation": False,
                "error": {
                    "type": "SourceMutationAfterResultWrite",
                    "message": "source identity drift after result write",
                    "rejected_result_sha256": result_hash,
                    "acceptance_record": str(acceptance_path),
                },
            }
            args.output.write_text(
                json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            sys.stdout.write(json.dumps({
                "output": str(args.output),
                "post_result_write_revalidation": False,
                "error": "source identity drift after result write",
            }, ensure_ascii=False) + "\n")
            return 3
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "projection_exact": result["projection_exact"],
            "stage6_family_audit_complete": result["stage6_family_audit_complete"],
            "normalized_full_conservation": result["normalized_full_conservation"],
            "blocking_findings": len(result["findings"]["blocking"]),
            "post_result_write_revalidation": True,
            "acceptance_record": str(acceptance_path),
            "result_sha256": result_hash,
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

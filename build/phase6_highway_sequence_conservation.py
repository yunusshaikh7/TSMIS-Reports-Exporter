"""Independent Stage-6 Highway Sequence raw-PDF conservation oracle.

This audit intentionally does not import the application's Highway Sequence parser,
normalizer, comparator, evidence adapter, or family constants.  It captures the exact
authoritative D01-D12 PDF bytes, parses those private payloads with an independent
layout implementation, reads the accepted r7 workbook through the generic Phase-3
OOXML reader, and classifies every source-to-normalized residue.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from typing import Iterable, Mapping, Sequence
import zipfile

import pdfplumber

BUILD_DIR = Path(__file__).resolve().parent
REPO_ROOT = BUILD_DIR.parent
sys.path.insert(0, str(BUILD_DIR))
from phase3_xlsx_stream import (  # noqa: E402
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    XlsxLimits,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


RAW_DIR = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\highway_sequence\raw"
)
R7_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
)
R7_RUN = R7_ROOT / "raw-2026-07-12-r7"
NORMALIZED_XLSX = (
    R7_RUN / "highway_sequence" / "consolidated"
    / "tsn_highway_sequence_normalized.xlsx"
)
NORMALIZED_SIDECAR = Path(str(NORMALIZED_XLSX) + ".outcome.json")
R7_RESULT = R7_RUN / "result.json"
RESULT_DIR = R7_ROOT.parent / "phase6_tsn_conservation"
DEFAULT_RESULT = RESULT_DIR / "highway_sequence_conservation_r7.json"
FAMILY_GATE = BUILD_DIR / "check_phase6_highway_sequence_conservation.py"
READER = BUILD_DIR / "phase3_xlsx_stream.py"
READER_GATE = BUILD_DIR / "check_phase3_xlsx_stream.py"

HEADERS = (
    "Route", "County", "PM", "City", "HG", "FT",
    "Distance To Next Point", "Description",
)
SHEET_NAME = "Highway Locations (TSN)"

RAW_BINDINGS = (
    ("D01 HSL TSN.pdf", 204709, "3a4cb30340a55edae2f72d758dcda62d30e21d919ecc862ec6955d6795252a4a"),
    ("D02 HSL TSN.pdf", 288696, "f32078eb79f38fa2e4799319bd10f661ecdff669dd7c4ade18a5326723ad5d85"),
    ("D03 HSL TSN.pdf", 373387, "8c5cd4638dd4901797f9c15e6fac7f998d5bc989749f874e6eedf52f72506fb0"),
    ("D04 HSL TSN.pdf", 625052, "5facc297fd7d28e8ad760cce8d7f4699b1ee4bc7582f2a007196c0bf739bcd5a"),
    ("D05 HSL TSN.pdf", 265876, "b8246f8c28e31d0c4acc352b7148988b6a6a0d7abaf56e810943e14816389e7b"),
    ("D06 HSL TSN.pdf", 327246, "e240f038390109ca02ceb012a5e8e5b82fc8845c49be718506acb56667db3dad"),
    ("D07 HSL TSN.pdf", 555648, "c791b99789e496efb83b52850aa54e142946aaa541a91b780489fe7e0bc7ec25"),
    ("D08 HSL TSN.pdf", 370505, "f23b8e3d5a90200cc1a6285ebb40480b828673f9e5a37b06f36fe30bc9697565"),
    ("D09 HSL TSN.pdf", 103868, "c6984a7e947ff600a450e4387f318aeed4826b05249361a694fbe507d0c7c5c3"),
    ("D10 HSL TSN.pdf", 298313, "e510a575c56c5af4404968d9fe51271f79cc23377df1e5c651b45b563dbf2ed6"),
    ("D11 HSL TSN.pdf", 315238, "920e3e352c1f24be415271c9819fc8bddce8ac6ef3095684e9fe06c87cf7378b"),
    ("D12 HSL TSN.pdf", 138411, "5583c0a0b94feeddaefda8bfa35bf34657cfb9f3b8e0a8d2b047c8fc27cbcc7a"),
)
DOCUMENT_CLAIM_BINDINGS = {
    "D01 HSL TSN.pdf": {"creation_date": "D:20250915130517", "modification_date": "D:20250915130517", "generation_time": "01:05 PM"},
    "D02 HSL TSN.pdf": {"creation_date": "D:20250915130917", "modification_date": "D:20250915130917", "generation_time": "01:09 PM"},
    "D03 HSL TSN.pdf": {"creation_date": "D:20250915131153", "modification_date": "D:20250915131153", "generation_time": "01:11 PM"},
    "D04 HSL TSN.pdf": {"creation_date": "D:20250915131454", "modification_date": "D:20250915131454", "generation_time": "01:14 PM"},
    "D05 HSL TSN.pdf": {"creation_date": "D:20250915131934", "modification_date": "D:20250915131934", "generation_time": "01:19 PM"},
    "D06 HSL TSN.pdf": {"creation_date": "D:20250915132215", "modification_date": "D:20250915132215", "generation_time": "01:22 PM"},
    "D07 HSL TSN.pdf": {"creation_date": "D:20250915132712", "modification_date": "D:20250915132712", "generation_time": "01:27 PM"},
    "D08 HSL TSN.pdf": {"creation_date": "D:20250915133204", "modification_date": "D:20250915133204", "generation_time": "01:32 PM"},
    "D09 HSL TSN.pdf": {"creation_date": "D:20250915133506", "modification_date": "D:20250915133506", "generation_time": "01:35 PM"},
    "D10 HSL TSN.pdf": {"creation_date": "D:20250915133724", "modification_date": "D:20250915133724", "generation_time": "01:37 PM"},
    "D11 HSL TSN.pdf": {"creation_date": "D:20250915145958", "modification_date": "D:20250915145958", "generation_time": "02:59 PM"},
    "D12 HSL TSN.pdf": {"creation_date": "D:20250915150325Z", "modification_date": "D:20251121111252-08'00'", "generation_time": "03:03 PM"},
}
NON_SOURCE_NAMES = ("_PUT TSN FILES HERE.txt",)
NORMALIZED_BINDING = {
    "bytes": 2536901,
    "sha256": "9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041",
}
SIDECAR_BINDING = {
    "bytes": 2413,
    "sha256": "fea39608196cdc17dda2a2f585bf9faf1a569488f09c7c493a75d575893d79f0",
}
R7_RESULT_BINDING = {
    "bytes": 173124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}
EXPECTED = {
    "members": 12,
    "raw_bytes": 3866949,
    "pages": 1540,
    "cover_pages": 12,
    "data_pages": 1528,
    "source_records": 69804,
    "projected_rows": 69758,
    "data_rows": 68806,
    "equates": 998,
    "pre_county_equates": 46,
    "known_county_equates": 952,
    "routes": 263,
    "counties": 58,
    "owners": 369,
    "pointer_P": 283,
    "pointer_arrow": 282,
    "pointer_total": 565,
    "continuations": 1,
}
EXPECTED_PROJECTED_ROWS_BY_DISTRICT = {
    "01": 3541, "02": 5091, "03": 6653, "04": 11273,
    "05": 4766, "06": 5882, "07": 10152, "08": 6719,
    "09": 1695, "10": 5231, "11": 5759, "12": 2996,
}
EXPECTED_DIRECTIONS = {"S-N": 190, "W-E": 172, "E-W": 5, "N-S": 2}

Y_TOLERANCE = 3.0
WINDOWS = {
    "County": (0.0, 44.0),
    "City": (44.0, 98.0),
    "PM": (98.0, 168.0),
    "Flag": (168.0, 205.0),
    "Distance To Next Point": (205.0, 270.0),
    "Description": (270.0, 700.0),
}
LOCATION_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$")
COUNTY_RE = re.compile(r"^[A-Z]{2,4}\.?$")
NUMERIC_DISTANCE_RE = re.compile(r"^\d{1,3}\.\d{3}$")
GROUP_RE = re.compile(
    r"\bDIST\s+(\d{1,2})\s+RTE\s+([0-9A-Z]+)\s+DIR\s+([NSEW]-[NSEW])\b"
)
GROUP_LIKE_RE = re.compile(r"\bDIST\b.*\bRTE\b.*\bDIR\b", re.IGNORECASE)


class ConservationError(ValueError):
    pass


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        t = value.as_tuple()
        return ["decimal", t.sign, list(t.digits), t.exponent]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"unsupported typed value: {type(value).__name__}")


def _row_wire(row: Sequence[object]) -> bytes:
    return json.dumps([_typed(v) for v in row], ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _ordered_digest(rows: Iterable[Sequence[object]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        wire = _row_wire(row)
        h.update(len(wire).to_bytes(8, "big"))
        h.update(wire)
    return h.hexdigest()


def _multiset_digest(rows: Iterable[Sequence[object]]) -> tuple[str, Counter[str]]:
    counts = Counter(_sha(_row_wire(row)) for row in rows)
    h = hashlib.sha256()
    for digest, count in sorted(counts.items()):
        h.update(f"{digest}\t{count}\n".encode("ascii"))
    return h.hexdigest(), counts


def _field_digest(values: Sequence[object]) -> dict[str, object]:
    rows = [(value,) for value in values]
    multi, counts = _multiset_digest(rows)
    type_counts = Counter(_typed(value)[0] for value in values)
    return {
        "ordered_typed_sha256": _ordered_digest(rows),
        "multiset_typed_sha256": multi,
        "distinct_typed_values": len(counts),
        "type_counts": dict(sorted(type_counts.items())),
        "null_count": sum(value is None for value in values),
        "empty_string_count": sum(value == "" for value in values),
    }


def _dataset_digests(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> dict[str, object]:
    multiset, _ = _multiset_digest(rows)
    return {
        "row_count": len(rows),
        "column_count": len(headers),
        "headers": list(headers),
        "ordered_typed_sha256": _ordered_digest(rows),
        "multiset_typed_sha256": multiset,
        "fields": {
            header: _field_digest([row[index] for row in rows])
            for index, header in enumerate(headers)
        },
    }


def _identity_dict(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _stable_identity(identity: FileIdentity) -> dict[str, object]:
    return {
        "canonical_path": identity.canonical_path,
        "size": identity.size,
        "sha256": identity.sha256,
    }


def _require_identity(identity: FileIdentity, binding: Mapping[str, object], label: str) -> None:
    if identity.size != binding["bytes"] or identity.sha256 != binding["sha256"]:
        raise ConservationError(
            f"{label} binding mismatch: {identity.size}/{identity.sha256}"
        )


def _norm_route(token: str) -> str:
    match = re.fullmatch(r"(\d{1,3})([A-Za-z]?)", token.strip())
    if not match:
        raise ConservationError(f"invalid route token {token!r}")
    return match.group(1).zfill(3) + match.group(2).upper()


def _cluster_words(words: Sequence[Mapping[str, object]]) -> list[list[dict[str, object]]]:
    """Independent top-coordinate clustering; no production helper is imported."""
    pending = sorted((dict(word) for word in words),
                     key=lambda word: (float(word["top"]), float(word["x0"])))
    groups: list[dict[str, object]] = []
    for word in pending:
        top = float(word["top"])
        best = None
        best_delta = None
        for index in range(max(0, len(groups) - 3), len(groups)):
            delta = abs(top - float(groups[index]["mean_top"]))
            if delta <= Y_TOLERANCE and (best_delta is None or delta < best_delta):
                best, best_delta = index, delta
        if best is None:
            groups.append({"mean_top": top, "tops": [top], "words": [word]})
        else:
            group = groups[best]
            group["tops"].append(top)
            group["mean_top"] = sum(group["tops"]) / len(group["tops"])
            group["words"].append(word)
    groups.sort(key=lambda group: float(group["mean_top"]))
    return [sorted(group["words"], key=lambda word: float(word["x0"]))
            for group in groups]


def _bucket_words(words: Sequence[Mapping[str, object]]) -> dict[str, list[str]]:
    columns: dict[str, list[str]] = defaultdict(list)
    for word in words:
        x0 = float(word["x0"])
        for name, (left, right) in WINDOWS.items():
            if left <= x0 < right:
                columns[name].append(str(word["text"]))
                break
    return dict(columns)


def _advance_printed_page(counters: dict[tuple[str, str, str], int],
                          owner: tuple[str, str, str], printed_page: int) -> int:
    expected = counters.get(owner, 0) + 1
    if printed_page != expected:
        raise ConservationError(
            f"owner {owner} printed page sequence expected {expected}, got {printed_page}"
        )
    counters[owner] = expected
    return expected


def _validate_pdf_metadata(metadata: Mapping[str, object], name: str,
                           expected_creation: str,
                           expected_modification: str) -> dict[str, str]:
    actual = {str(key): str(value) for key, value in sorted(metadata.items())}
    expected_values = {
        "Creator": "Oracle12c AS Reports Services",
        "Producer": "Oracle PDF driver",
        "Title": "otm22025.pdf",
        "Author": "Oracle Reports",
    }
    if set(actual) != {*expected_values, "CreationDate", "ModDate"}:
        raise ConservationError(f"{name}: PDF metadata role universe changed")
    if any(actual.get(key) != value for key, value in expected_values.items()):
        raise ConservationError(f"{name}: PDF metadata value changed")
    creation = actual.get("CreationDate", "")
    if creation != expected_creation or actual.get("ModDate") != expected_modification:
        raise ConservationError(f"{name}: PDF creation/modification timestamp changed")
    return actual


def _exact_page_header(line_texts: Sequence[str], expected_district: str,
                       expected_generation_time: str) -> dict[str, object]:
    group_claims = []
    group_line_index = None
    for index, line_text in enumerate(line_texts):
        group = GROUP_RE.search(line_text)
        if group:
            group_claims.append((
                group.group(1).zfill(2), _norm_route(group.group(2)), group.group(3)
            ))
            group_line_index = index
    if len(group_claims) != 1 or group_line_index is None:
        raise ConservationError("data page must contain exactly one owner header")
    owner = group_claims[0]
    if owner[0] != expected_district:
        raise ConservationError(f"page owner district differs: {owner}")
    header = " ".join(line_texts[:group_line_index + 1])
    report_ids = re.findall(r"\bOTM22025\b", header)
    titles = re.findall(r"\bHighway\s+Locations\b", header)
    report_dates = re.findall(r"\b\d{2}-[A-Z]{3}-\d{2}\b", header)
    references = re.findall(r"\bRef\s+Dt\s+(\d{2}\s+[A-Z]{3}\s+\d{4})\b", header)
    times = re.findall(r"\b\d{2}:\d{2}\s+[AP]M\b", header)
    printed_pages = re.findall(r"\bPage\s+(\d+)\b", header)
    claims = (report_ids, titles, report_dates, references, times, printed_pages)
    if any(len(values) != 1 for values in claims):
        raise ConservationError("data page header roles must each occur exactly once")
    if (report_ids[0] != "OTM22025" or titles[0] != "Highway Locations"
            or report_dates[0] != "15-SEP-25"
            or references[0] != "15 SEP 2025"
            or times[0] != expected_generation_time):
        raise ConservationError("data page header value changed")
    return {
        "owner": owner,
        "report_id": report_ids[0],
        "report_title": titles[0],
        "report_date": report_dates[0],
        "reference_date": references[0],
        "generation_time": times[0],
        "printed_page": int(printed_pages[0]),
    }


def _classify_raw_names(names: Sequence[str]) -> tuple[list[str], list[str]]:
    expected_names = [name for name, _size, _sha256 in RAW_BINDINGS]
    actual_names = sorted(names)
    source_names = sorted(name for name in actual_names if name in expected_names)
    non_source_names = sorted(name for name in actual_names if name not in expected_names)
    if source_names != expected_names or non_source_names != list(NON_SOURCE_NAMES):
        raise ConservationError(
            "raw role universe differs: expected exactly 12 bound PDFs plus "
            f"{list(NON_SOURCE_NAMES)}, got {actual_names}"
        )
    return source_names, non_source_names


def _capture_raw() -> tuple[list[dict[str, object]], dict[str, bytes], list[dict[str, object]]]:
    actual_names = sorted(path.name for path in RAW_DIR.iterdir() if path.is_file())
    _source_names, non_source_names = _classify_raw_names(actual_names)
    identities: list[dict[str, object]] = []
    payloads: dict[str, bytes] = {}
    for name, size, digest in RAW_BINDINGS:
        captured = capture_file_bytes(RAW_DIR / name, max_bytes=size)
        _require_identity(captured.identity, {"bytes": size, "sha256": digest}, name)
        identities.append(_identity_dict(captured.identity))
        payloads[name] = captured.payload
    if sum(item["size"] for item in identities) != EXPECTED["raw_bytes"]:
        raise ConservationError("raw byte total changed")
    non_source = [
        _identity_dict(capture_file_identity(RAW_DIR / name))
        for name in non_source_names
    ]
    return identities, payloads, non_source


def _parse_document(name: str, payload: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    expected_district = name[1:3]
    claim_binding = DOCUMENT_CLAIM_BINDINGS.get(name)
    if claim_binding is None:
        raise ConservationError(f"{name}: document claim binding missing")
    records: list[dict[str, object]] = []
    owner_headers: list[dict[str, object]] = []
    page_claims: list[dict[str, object]] = []
    continuation_claims: list[dict[str, object]] = []
    route: str | None = None
    direction: str | None = None
    county: str | None = None
    current_district: str | None = None
    last_record: dict[str, object] | None = None
    owner_page_counters: dict[tuple[str, str, str], int] = {}
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        metadata = _validate_pdf_metadata(
            pdf.metadata or {}, name, claim_binding["creation_date"],
            claim_binding["modification_date"]
        )
        page_total = len(pdf.pages)
        cover_text = pdf.pages[0].extract_text() or ""
        cover_flat = " ".join(cover_text.split())
        required_cover = (
            "OTM22025", "Highway Locations", "Reference Date: 15-SEP-25",
            f"District: {expected_district}", "Route Breaks, Equates",
            "problem seems to be intrinsic to TSN's architecture",
        )
        missing = [claim for claim in required_cover if claim not in cover_flat]
        if missing:
            raise ConservationError(f"{name}: cover claims missing {missing}")
        policy_start = cover_flat.find("* * * N O T E * * *")
        if policy_start < 0:
            raise ConservationError(f"{name}: policy warning missing")
        policy_text = cover_flat[policy_start:]

        for pdf_page_index, page in enumerate(pdf.pages[1:], 1):
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            lines = _cluster_words(words)
            line_texts = [" ".join(str(word["text"]) for word in line) for line in lines]
            try:
                header = _exact_page_header(
                    line_texts, expected_district, claim_binding["generation_time"]
                )
            except ConservationError as exc:
                raise ConservationError(
                    f"{name} physical page {pdf_page_index + 1}: {exc}"
                ) from exc
            page_owner = header["owner"]
            printed_page_number = header["printed_page"]
            _advance_printed_page(owner_page_counters, page_owner, printed_page_number)
            page_claims.append({
                "physical_page": pdf_page_index + 1,
                "printed_page": printed_page_number,
                "owner": list(page_owner),
                "report_id": header["report_id"],
                "report_title": header["report_title"],
                "report_date": header["report_date"],
                "reference_date": header["reference_date"],
                "generation_time": header["generation_time"],
            })

            for line_index, line in enumerate(lines, 1):
                text = " ".join(str(word["text"]) for word in line)
                group = GROUP_RE.search(text)
                if group:
                    current_district = group.group(1).zfill(2)
                    if current_district != expected_district:
                        raise ConservationError(
                            f"{name} p{pdf_page_index + 1}: district {current_district}"
                        )
                    route = _norm_route(group.group(2))
                    direction = group.group(3)
                    county = None
                    last_record = None
                    owner_headers.append({
                        "district": current_district,
                        "route": route,
                        "direction": direction,
                        "physical_page": pdf_page_index + 1,
                        "printed_page": printed_page_number,
                        "line": line_index,
                    })
                    continue
                if GROUP_LIKE_RE.search(text):
                    raise ConservationError(
                        f"{name} p{pdf_page_index + 1}: malformed owner header {text!r}"
                    )
                columns = _bucket_words(line)
                county_token = (columns.get("County") or [""])[0]
                pm = next((token for token in columns.get("PM", ())
                           if LOCATION_RE.fullmatch(token)), None)
                provenance = {
                    "member": name,
                    "district": current_district,
                    "route": route,
                    "direction": direction,
                    "physical_page": pdf_page_index + 1,
                    "printed_page": printed_page_number,
                    "line": line_index,
                    "top": format(min(float(word["top"]) for word in line), ".3f"),
                    "raw_text": text,
                }
                if "EQUATES" in text and pm and not COUNTY_RE.fullmatch(county_token):
                    if route is None or direction is None or current_district is None:
                        raise ConservationError(f"{name}: unowned equate annotation")
                    record = {
                        **provenance,
                        "kind": "equate",
                        "county": county,
                        "pm": pm,
                        "city": None,
                        "hg": None,
                        "ft": None,
                        "distance": None,
                        "description": "EQUATES TO",
                    }
                    records.append(record)
                    last_record = record
                    continue
                if COUNTY_RE.fullmatch(county_token) and pm:
                    if route is None or direction is None or current_district is None:
                        raise ConservationError(f"{name}: data row precedes owner")
                    county = county_token.rstrip(".")
                    flag = "".join(columns.get("Flag", ()))
                    distances = columns.get("Distance To Next Point", ())
                    distance = distances[0] if distances else None
                    if distance is not None and not (
                        NUMERIC_DISTANCE_RE.fullmatch(distance)
                        or distance in ("*P*", "-------->")
                    ):
                        raise ConservationError(
                            f"{name} p{pdf_page_index + 1}: unknown distance {distance!r}"
                        )
                    description = " ".join(columns.get("Description", ())).strip() or None
                    record = {
                        **provenance,
                        "kind": "data",
                        "county": county,
                        "pm": pm,
                        "city": (columns.get("City") or [None])[0],
                        "hg": flag[0] if len(flag) >= 1 else None,
                        "ft": flag[1] if len(flag) >= 2 else None,
                        "distance": distance,
                        "description": description,
                    }
                    records.append(record)
                    last_record = record
                    continue
                if (last_record is not None and columns.get("Description")
                        and not columns.get("County") and not columns.get("PM")):
                    extra = " ".join(columns["Description"]).strip()
                    if extra:
                        before = last_record["description"]
                        last_record["description"] = (
                            extra if not before else f"{before} {extra}"
                        )
                        continuation_claims.append({
                            **provenance,
                            "target_identity": [
                                last_record["district"], last_record["county"],
                                last_record["route"], last_record["pm"],
                            ],
                            "before": before,
                            "continuation": extra,
                            "source_join": last_record["description"],
                        })

    unique_owners = sorted({
        (item["district"], item["route"], item["direction"])
        for item in owner_headers
    })
    return records, {
        "member": name,
        "district": expected_district,
        "page_count": page_total,
        "cover_sha256": _sha(cover_text.encode("utf-8")),
        "policy_sha256": _sha(policy_text.encode("utf-8")),
        "policy_text": policy_text,
        "pdf_metadata": metadata,
        "data_page_claims": page_claims,
        "owner_header_occurrences": owner_headers,
        "unique_owners": [list(owner) for owner in unique_owners],
        "continuations": continuation_claims,
    }


def _source_row(record: Mapping[str, object]) -> tuple[object, ...]:
    return (
        record["district"], record["route"], record["direction"],
        record["county"], record["pm"], record["city"], record["hg"],
        record["ft"], record["distance"], record["description"], record["kind"],
    )


SOURCE_HEADERS = (
    "District", "Route", "Direction", "County", "PM", "City", "HG", "FT",
    "Distance To Next Point", "Description", "Record Kind",
)


def _project_record(record: Mapping[str, object]) -> tuple[object, ...] | None:
    if record["county"] is None:
        return None
    return (
        record["route"], record["county"], record["pm"], record["city"],
        record["hg"], record["ft"], record["distance"], record["description"],
    )


def _sorted_source(records: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    by_route: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        by_route[str(record["route"])].append(record)
    return [record for route in sorted(by_route) for record in by_route[route]]


def _compare_projection(expected: Sequence[Sequence[object]], actual_rows) -> dict[str, object]:
    actual = [row.values for row in actual_rows]
    mismatches: list[dict[str, object]] = []
    for ordinal, (left, right) in enumerate(zip(expected, actual)):
        for column, (a, b) in enumerate(zip(left, right)):
            if _typed(a) != _typed(b):
                mismatches.append({
                    "ordinal": ordinal,
                    "normalized_source_row": actual_rows[ordinal].source_row,
                    "field": HEADERS[column],
                    "expected": _typed(a),
                    "actual": _typed(b),
                })
    missing_or_extra = abs(len(expected) - len(actual))
    by_field = Counter(item["field"] for item in mismatches)
    expected_multi, _ = _multiset_digest(expected)
    actual_multi, _ = _multiset_digest(actual)
    return {
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "missing_or_extra_row_count": missing_or_extra,
        "typed_cell_mismatch_count": len(mismatches),
        "typed_cell_mismatches_by_field": dict(sorted(by_field.items())),
        "mismatches": mismatches,
        "ordered_exact": not missing_or_extra and not mismatches,
        "multiset_exact": expected_multi == actual_multi,
        "expected_ordered_sha256": _ordered_digest(expected),
        "actual_ordered_sha256": _ordered_digest(actual),
        "expected_multiset_sha256": expected_multi,
        "actual_multiset_sha256": actual_multi,
    }


def _collision_summary(keys: Sequence[tuple[object, ...]]) -> dict[str, object]:
    counts = Counter(keys)
    collisions = {key: count for key, count in counts.items() if count > 1}
    return {
        "row_count": len(keys),
        "distinct_keys": len(counts),
        "duplicate_group_count": len(collisions),
        "rows_in_duplicate_groups": sum(collisions.values()),
        "max_multiplicity": max(collisions.values(), default=1),
        "multiplicity_histogram": dict(sorted(Counter(collisions.values()).items())),
        "ordered_key_digest": _ordered_digest(keys),
        "multiset_key_digest": _multiset_digest(keys)[0],
    }


def _strip_pm_affixes(pm: object) -> str:
    match = re.search(r"\d{3}\.\d{3}", str(pm or ""))
    return match.group(0) if match else str(pm or "")


FIELD_DISPOSITIONS = {
    "DISTRICT": {"kind": "source_only", "normalized_targets": [], "role": "printed district owner"},
    "ROUTE": {"kind": "projected", "normalized_targets": ["Route"], "role": "printed route owner"},
    "DIRECTION": {"kind": "source_only", "normalized_targets": [], "role": "printed route direction"},
    "COUNTY": {"kind": "projected_conditional", "normalized_targets": ["County"], "role": "printed county; explicitly unknown on pre-county equates"},
    "PM": {"kind": "projected", "normalized_targets": ["PM"], "role": "complete printed postmile"},
    "CITY": {"kind": "projected", "normalized_targets": ["City"], "role": "printed city code"},
    "HG": {"kind": "projected", "normalized_targets": ["HG"], "role": "first printed G/RF flag"},
    "FT": {"kind": "projected", "normalized_targets": ["FT"], "role": "second printed G/RF flag"},
    "DISTANCE": {"kind": "projected", "normalized_targets": ["Distance To Next Point"], "role": "numeric distance or exact pointer token"},
    "DESCRIPTION": {"kind": "projected", "normalized_targets": ["Description"], "role": "printed description with whitespace-only continuation join"},
    "RECORD_KIND": {"kind": "relational", "normalized_targets": [], "role": "data versus EQUATES TO annotation"},
    "MEMBER": {"kind": "audit_provenance", "normalized_targets": [], "role": "owning PDF member"},
    "PAGE": {"kind": "audit_provenance", "normalized_targets": [], "role": "physical and printed page"},
    "LINE": {"kind": "audit_provenance", "normalized_targets": [], "role": "line order and coordinate"},
    "RAW_TEXT": {"kind": "audit_provenance", "normalized_targets": [], "role": "exact extracted source line"},
    "REPORT_ID": {"kind": "source_only_metadata", "normalized_targets": [], "role": "OTM22025 report identity"},
    "REPORT_TITLE": {"kind": "source_only_metadata", "normalized_targets": [], "role": "Highway Locations title"},
    "REFERENCE_DATE": {"kind": "source_only_metadata", "normalized_targets": [], "role": "cover and page reference date"},
    "REPORT_DATE": {"kind": "source_only_metadata", "normalized_targets": [], "role": "printed report date"},
    "GENERATION_TIME": {"kind": "source_only_metadata", "normalized_targets": [], "role": "district generation time"},
    "PDF_METADATA": {"kind": "source_only_metadata", "normalized_targets": [], "role": "PDF creator/title/timestamps"},
    "POLICY_WARNING": {"kind": "source_only_metadata", "normalized_targets": [], "role": "source reliability and use policy"},
}


def _field_coverage(dispositions: Mapping[str, object] = FIELD_DISPOSITIONS) -> dict[str, object]:
    expected = {
        "DISTRICT", "ROUTE", "DIRECTION", "COUNTY", "PM", "CITY", "HG", "FT",
        "DISTANCE", "DESCRIPTION", "RECORD_KIND", "MEMBER", "PAGE", "LINE",
        "RAW_TEXT", "REPORT_ID", "REPORT_TITLE", "REFERENCE_DATE", "REPORT_DATE",
        "GENERATION_TIME", "PDF_METADATA", "POLICY_WARNING",
    }
    allowed = {
        "projected", "projected_conditional", "relational", "audit_provenance",
        "source_only", "source_only_metadata",
    }
    errors = []
    for field, disposition in dispositions.items():
        if set(disposition) != {"kind", "normalized_targets", "role"}:
            errors.append(f"{field}: disposition keys")
        if disposition.get("kind") not in allowed:
            errors.append(f"{field}: disposition kind")
        if not isinstance(disposition.get("normalized_targets"), list):
            errors.append(f"{field}: target type")
        if not disposition.get("role"):
            errors.append(f"{field}: role")
    targets = {target for item in dispositions.values()
               for target in item.get("normalized_targets", [])}
    return {
        "raw_role_count": len(expected),
        "declared_disposition_count": len(dispositions),
        "unexplained_raw_roles": sorted(expected - set(dispositions)),
        "extraneous_disposition_roles": sorted(set(dispositions) - expected),
        "unexplained_normalized_fields": sorted(set(HEADERS) - targets),
        "structure_errors": errors,
        "exact": (set(dispositions) == expected and targets == set(HEADERS)
                  and not errors),
    }


def _run_gate(path: Path) -> dict[str, object]:
    identity_before = capture_file_identity(path)
    completed = subprocess.run(
        [sys.executable, str(path)], cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )
    identity_after = capture_file_identity(path)
    if identity_before != identity_after or completed.returncode != 0:
        raise ConservationError(
            f"gate failed or changed: {path.name}: {completed.stdout[-2000:]}"
        )
    return {
        "path": str(path),
        "identity": _identity_dict(identity_after),
        "returncode": completed.returncode,
        "stdout_sha256": _sha(completed.stdout.encode("utf-8")),
        "stdout_tail": completed.stdout.strip().splitlines()[-1:] or [],
    }


def _loaded_module_manifest() -> dict[str, object]:
    prefixes = ("pdfplumber", "pdfminer", "PIL", "pypdfium2")
    members = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith(prefixes):
            continue
        path_text = getattr(module, "__file__", None)
        if not path_text:
            continue
        path = Path(path_text)
        if path.suffix == ".pyc" and path.with_suffix(".py").is_file():
            path = path.with_suffix(".py")
        if not path.is_file():
            continue
        identity = capture_file_identity(path)
        members.append({"module": name, **_identity_dict(identity)})
    wire = [[item["module"], item["size"], item["sha256"]] for item in members]
    return {
        "member_count": len(members),
        "manifest_sha256": _sha(_json_bytes(wire)),
        "members": members,
    }


def _validate_sidecar(document: Mapping[str, object], raw_members: Sequence[Mapping[str, object]]) -> dict[str, object]:
    raw_manifest = document.get("tsn_raw_manifest")
    if not isinstance(raw_manifest, dict):
        raise ConservationError("sidecar raw manifest missing")
    expected_members = [
        {"relative_path": name, "byte_length": size, "sha256": digest}
        for name, size, digest in RAW_BINDINGS
    ]
    checks = {
        "completion": document.get("completion") == "complete",
        "skipped_inputs": document.get("skipped_inputs") == 0,
        "failed_inputs": document.get("failed_inputs") == 0,
        "normalization_version": document.get("tsn_normalization_version") == 3,
        "manifest_members": raw_manifest.get("members") == expected_members,
        "manifest_count": raw_manifest.get("member_count") == 12,
        "manifest_bytes": raw_manifest.get("byte_length") == EXPECTED["raw_bytes"],
        "normalized_identity": document.get("tsn_normalized_workbook_identity") == {
            "version": 1, "algorithm": "sha256",
            "byte_length": NORMALIZED_BINDING["bytes"],
            "sha256": NORMALIZED_BINDING["sha256"],
        },
        "captured_raw_members": [
            [Path(item["canonical_path"]).name, item["size"], item["sha256"]]
            for item in raw_members
        ] == [[name, size, digest] for name, size, digest in RAW_BINDINGS],
    }
    if not all(checks.values()):
        raise ConservationError(f"sidecar contract failed: {checks}")
    return checks


def _validate_r7(document: Mapping[str, object]) -> dict[str, object]:
    families = document.get("families")
    family = next((item for item in families or []
                   if item.get("report") == "highway_sequence"), None)
    if not isinstance(family, dict):
        raise ConservationError("r7 Highway Sequence family missing")
    output = family.get("output") or {}
    result = family.get("result") or {}
    reuse = family.get("reuse") or {}
    checks = {
        "run_accepted": _accepted_terminal(document.get("acceptance")),
        "seven_families": document.get("completed_family_count") == 7,
        "source_stable": document.get("source_universe_stable") is True,
        "code_stable": document.get("code_provenance_stable") is True,
        "family_complete": result.get("completion") == "complete",
        "family_zero_skipped": result.get("skipped_inputs") == 0,
        "family_zero_failed": result.get("failed_inputs") == 0,
        "builder_certificate": family.get("builder_certificate_matches") is True,
        "normalization_version": family.get("normalization_version") == 3,
        "output_identity": output.get("bytes") == NORMALIZED_BINDING["bytes"]
            and output.get("sha256") == NORMALIZED_BINDING["sha256"],
        "sidecar_identity": output.get("sidecar_sha256") == SIDECAR_BINDING["sha256"],
        "rows": (output.get("sheets") or [{}])[0].get("data_rows") == EXPECTED["projected_rows"],
        "reuse_certified": reuse.get("certified") is True,
        "reuse_bytes_unchanged": reuse.get("output_unchanged") is True
            and reuse.get("sidecar_unchanged") is True,
    }
    if not all(checks.values()):
        raise ConservationError(f"r7 lifecycle contract failed: {checks}")
    return checks


def _accepted_terminal(value: object) -> bool:
    return type(value) is str and value == "complete"


def _mutation_probes(source_rows: Sequence[Sequence[object]],
                     projected_rows: Sequence[Sequence[object]],
                     metadata_digest: str) -> dict[str, object]:
    source_base = _ordered_digest(source_rows)
    projected_base = _ordered_digest(projected_rows)
    probes: dict[str, bool] = {}
    for label, column, replacement in (
        ("district", 0, "99"), ("route", 1, "999"),
        ("direction", 2, "N-S"), ("county", 3, "ZZZ"),
        ("pm", 4, "999.999"), ("distance_pointer", 8, None),
        ("description", 9, "MUTATED"), ("record_kind", 10, "mutated"),
    ):
        changed = list(source_rows)
        row = list(changed[0])
        if label == "distance_pointer":
            pointer_index = next(i for i, item in enumerate(changed)
                                 if item[8] in ("*P*", "-------->"))
            row = list(changed[pointer_index])
            row[column] = replacement
            changed[pointer_index] = tuple(row)
        else:
            row[column] = replacement
            changed[0] = tuple(row)
        probes[label] = _ordered_digest(changed) != source_base
    probes["delete_source_record"] = _ordered_digest(source_rows[:-1]) != source_base
    probes["add_source_record"] = _ordered_digest([*source_rows, source_rows[-1]]) != source_base
    swapped = list(source_rows)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    probes["source_order"] = (_ordered_digest(swapped) != source_base
                              and _multiset_digest(swapped)[0] == _multiset_digest(source_rows)[0])
    projected = list(projected_rows)
    row = list(projected[0]); row[2] = "999.999"; projected[0] = tuple(row)
    probes["projected_cell"] = _ordered_digest(projected) != projected_base
    probes["metadata"] = _sha((metadata_digest + "x").encode()) != _sha(metadata_digest.encode())
    probes["disposition_missing"] = not _field_coverage(
        {key: value for key, value in FIELD_DISPOSITIONS.items() if key != "DISTANCE"}
    )["exact"]
    return {
        "probe_count": len(probes),
        "detected_count": sum(probes.values()),
        "all_detected": all(probes.values()),
        "probes": probes,
    }


def run() -> dict[str, object]:
    code_before = {
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
    }
    reader_gate = _run_gate(READER_GATE)
    family_gate = _run_gate(FAMILY_GATE)

    raw_identities, payloads, non_source_identities = _capture_raw()
    normalized_identity = capture_file_identity(NORMALIZED_XLSX)
    sidecar_capture = capture_file_bytes(NORMALIZED_SIDECAR, max_bytes=SIDECAR_BINDING["bytes"])
    r7_capture = capture_file_bytes(R7_RESULT, max_bytes=R7_RESULT_BINDING["bytes"])
    _require_identity(normalized_identity, NORMALIZED_BINDING, "normalized workbook")
    _require_identity(sidecar_capture.identity, SIDECAR_BINDING, "normalized sidecar")
    _require_identity(r7_capture.identity, R7_RESULT_BINDING, "r7 lifecycle result")
    try:
        sidecar = json.loads(sidecar_capture.payload)
        r7 = json.loads(r7_capture.payload)
    except json.JSONDecodeError as exc:
        raise ConservationError("bound lifecycle JSON is malformed") from exc
    sidecar_checks = _validate_sidecar(sidecar, raw_identities)
    r7_checks = _validate_r7(r7)

    all_records: list[dict[str, object]] = []
    documents: list[dict[str, object]] = []
    for name, _size, _digest in RAW_BINDINGS:
        records, document = _parse_document(name, payloads[name])
        all_records.extend(records)
        documents.append(document)
    source_records = _sorted_source(all_records)
    source_rows = [_source_row(record) for record in source_records]
    projected_records = [record for record in source_records if record["county"] is not None]
    projected_rows = [_project_record(record) for record in projected_records]
    if any(row is None for row in projected_rows):
        raise ConservationError("projected record unexpectedly omitted")

    normalized_spec = SheetSpec(
        SHEET_NAME, tuple(ColumnSpec(header) for header in HEADERS),
        exact_schema=True,
    )
    normalized_sheet = read_sheet(
        NORMALIZED_XLSX, normalized_spec,
        limits=XlsxLimits(max_source_bytes=32 * 1024 * 1024),
    )
    projection = _compare_projection(projected_rows, normalized_sheet.rows)

    pointer_mismatches = [
        item for item in projection["mismatches"]
        if item["field"] == "Distance To Next Point"
        and item["expected"] in (["str", "*P*"], ["str", "-------->"])
        and item["actual"] == ["null"]
    ]
    description_mismatches = [
        item for item in projection["mismatches"] if item["field"] == "Description"
    ]
    pointer_records = [
        record for record in projected_records
        if record["distance"] in ("*P*", "-------->")
    ]
    unknown_equates = [
        record for record in source_records
        if record["kind"] == "equate" and record["county"] is None
    ]
    known_equates = [
        record for record in source_records
        if record["kind"] == "equate" and record["county"] is not None
    ]
    continuations = [item for document in documents for item in document["continuations"]]
    punctuation_exact = (
        len(description_mismatches) == 1
        and projected_records[description_mismatches[0]["ordinal"]]["district"] == "09"
        and projected_records[description_mismatches[0]["ordinal"]]["county"] == "KER"
        and projected_records[description_mismatches[0]["ordinal"]]["route"] == "014"
        and projected_records[description_mismatches[0]["ordinal"]]["pm"] == "018.365"
        and description_mismatches[0]["expected"] == [
            "str", "KEMWATER CHEMICAL PLANT - RT/FRONTAGE ROAD - LT."
        ]
        and description_mismatches[0]["actual"] == [
            "str", "KEMWATER CHEMICAL PLANT - RT/FRONTAGE, ROAD - LT."
        ]
    )
    classified = {
        "pre_county_equates_dropped": {
            "count": len(unknown_equates),
            "manifest_sha256": _sha(_json_bytes([
                {key: record[key] for key in (
                    "member", "district", "route", "direction", "physical_page",
                    "printed_page", "line", "pm", "raw_text",
                )} for record in unknown_equates
            ])),
            "manifest": [
                {key: record[key] for key in (
                    "member", "district", "route", "direction", "physical_page",
                    "printed_page", "line", "pm", "raw_text",
                )} for record in unknown_equates
            ],
            "finding": "CMP-AUD-158",
        },
        "distance_pointer_tokens_blanked": {
            "count": len(pointer_mismatches),
            "domain": dict(sorted(Counter(record["distance"] for record in pointer_records).items())),
            "manifest_sha256": _sha(_json_bytes([
                {key: record[key] for key in (
                    "member", "district", "route", "county", "pm",
                    "physical_page", "printed_page", "line", "distance",
                )} for record in pointer_records
            ])),
            "manifest": [
                {key: record[key] for key in (
                    "member", "district", "route", "county", "pm",
                    "physical_page", "printed_page", "line", "distance",
                )} for record in pointer_records
            ],
            "finding": "CMP-AUD-156",
        },
        "wrapped_description_invented_comma": {
            "count": len(description_mismatches),
            "exact": punctuation_exact,
            "mismatches": description_mismatches,
            "continuation_claims": continuations,
            "finding": "CMP-AUD-159",
        },
    }
    classified_mismatch_count = len(pointer_mismatches) + len(description_mismatches)
    unexplained = projection["typed_cell_mismatch_count"] - classified_mismatch_count

    owners = sorted({
        tuple(owner) for document in documents for owner in document["unique_owners"]
    })
    owner_direction_counts = Counter(owner[2] for owner in owners)
    projected_by_district = Counter(record["district"] for record in projected_records)
    known_keys = [(record["route"], record["county"], record["pm"])
                  for record in projected_records]
    stripped_keys = [(record["route"], record["county"], _strip_pm_affixes(record["pm"]))
                     for record in projected_records]
    no_county_keys = [(record["route"], record["pm"])
                      for record in projected_records]
    occurrences = Counter()
    occurrence_keys = []
    for key in known_keys:
        ordinal = occurrences[key]
        occurrences[key] += 1
        occurrence_keys.append((*key, ordinal))
    collision_census = {
        "full_route_county_printed_pm": _collision_summary(known_keys),
        "route_county_numeric_pm": _collision_summary(stripped_keys),
        "route_printed_pm_without_county": _collision_summary(no_county_keys),
        "occurrence_ordinal_identity": _collision_summary(occurrence_keys),
    }

    policy_digests = Counter(document["policy_sha256"] for document in documents)
    metadata_rows = []
    for document in documents:
        times = sorted({claim["generation_time"] for claim in document["data_page_claims"]})
        metadata_rows.append((
            document["member"], document["district"], "OTM22025",
            "Highway Locations", "15-SEP-25", "15 SEP 2025",
            "|".join(times), document["policy_sha256"],
            json.dumps(document["pdf_metadata"], sort_keys=True, separators=(",", ":")),
        ))
    metadata_headers = (
        "Member", "District", "Report ID", "Report Title", "Cover Reference Date",
        "Data Reference Date", "Generation Time", "Policy SHA256", "PDF Metadata",
    )
    metadata_digest = _ordered_digest(metadata_rows)
    probes = _mutation_probes(source_rows, projected_rows, metadata_digest)
    coverage = _field_coverage()

    source_provenance_rows = [(
        record["member"], record["physical_page"], record["printed_page"],
        record["line"], record["top"], record["raw_text"],
    ) for record in source_records]
    source_provenance_headers = (
        "Member", "Physical Page", "Printed Page", "Line", "Top", "Raw Text",
    )

    topology = _xlsx_topology(NORMALIZED_XLSX)
    module_manifest = _loaded_module_manifest()
    raw_after = [capture_file_identity(RAW_DIR / name) for name, _size, _digest in RAW_BINDINGS]
    non_source_after = [capture_file_identity(RAW_DIR / name) for name in NON_SOURCE_NAMES]
    code_after = {
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
    }
    tracked_current = (
        all(before == after for before, after in zip(
            [FileIdentity(**identity) for identity in raw_identities], raw_after
        ))
        and all(before == after for before, after in zip(
            [FileIdentity(**identity) for identity in non_source_identities],
            non_source_after,
        ))
        and normalized_sheet.pre_identity == normalized_sheet.post_identity
        and normalized_sheet.post_identity == capture_file_identity(NORMALIZED_XLSX)
        and sidecar_capture.identity == capture_file_identity(NORMALIZED_SIDECAR)
        and r7_capture.identity == capture_file_identity(R7_RESULT)
        and code_before == code_after
    )

    invariants = {
        "source_bindings_exact": len(raw_identities) == EXPECTED["members"],
        "source_pages_exact": sum(document["page_count"] for document in documents) == EXPECTED["pages"],
        "cover_and_data_pages_exact": len(documents) == EXPECTED["cover_pages"]
            and sum(len(document["data_page_claims"]) for document in documents) == EXPECTED["data_pages"],
        "source_record_count_exact": len(source_records) == EXPECTED["source_records"],
        "data_row_count_exact": sum(record["kind"] == "data" for record in source_records) == EXPECTED["data_rows"],
        "equate_universe_exact": len(unknown_equates) + len(known_equates) == EXPECTED["equates"]
            and len(unknown_equates) == EXPECTED["pre_county_equates"]
            and len(known_equates) == EXPECTED["known_county_equates"],
        "projected_and_normalized_rows_exact": len(projected_rows) == EXPECTED["projected_rows"]
            and len(normalized_sheet.rows) == EXPECTED["projected_rows"],
        "route_and_county_universe_exact": len({record["route"] for record in projected_records}) == EXPECTED["routes"]
            and len({record["county"] for record in projected_records}) == EXPECTED["counties"],
        "owner_universe_exact": len(owners) == EXPECTED["owners"]
            and dict(sorted(owner_direction_counts.items())) == EXPECTED_DIRECTIONS,
        "district_projected_counts_exact": dict(sorted(projected_by_district.items())) == EXPECTED_PROJECTED_ROWS_BY_DISTRICT,
        "pointer_domain_exact": len(pointer_records) == EXPECTED["pointer_total"]
            and Counter(record["distance"] for record in pointer_records)
            == Counter({"*P*": EXPECTED["pointer_P"], "-------->": EXPECTED["pointer_arrow"]}),
        "continuation_universe_exact": len(continuations) == EXPECTED["continuations"],
        "projection_residue_fully_classified": unexplained == 0
            and len(pointer_mismatches) == EXPECTED["pointer_total"]
            and punctuation_exact,
        "physical_occurrence_identity_unique": collision_census["occurrence_ordinal_identity"]["duplicate_group_count"] == 0,
        "field_dispositions_complete": coverage["exact"],
        "metadata_and_policy_exact": len(policy_digests) == 1
            and set(DOCUMENT_CLAIM_BINDINGS)
            == {name for name, _size, _digest in RAW_BINDINGS}
            and all(
                document["pdf_metadata"]["CreationDate"]
                == DOCUMENT_CLAIM_BINDINGS[document["member"]]["creation_date"]
                and document["pdf_metadata"]["ModDate"]
                == DOCUMENT_CLAIM_BINDINGS[document["member"]]["modification_date"]
                and {claim["generation_time"] for claim in document["data_page_claims"]}
                == {DOCUMENT_CLAIM_BINDINGS[document["member"]]["generation_time"]}
                for document in documents
            ),
        "normalized_physical_rows_contiguous": [row.source_row for row in normalized_sheet.rows]
            == list(range(2, EXPECTED["projected_rows"] + 2)),
        "semantic_mutations_all_detected": probes["all_detected"],
        "sidecar_contract_exact": all(sidecar_checks.values()),
        "r7_lifecycle_contract_exact": all(r7_checks.values()),
        "reader_and_family_gates_executed": reader_gate["returncode"] == 0
            and family_gate["returncode"] == 0,
        "tracked_identities_current": tracked_current,
    }
    if not all(invariants.values()):
        failed = [name for name, value in invariants.items() if not value]
        raise ConservationError(f"Stage-6 HSL invariants failed: {failed}")

    return {
        "schema_version": 1,
        "audit": "Stage 6 Highway Sequence raw-PDF-to-normalized conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_comparators_imported": False,
            "application_evidence_adapters_imported": False,
            "application_family_constants_imported": False,
            "pdf_parser": "independent pdfplumber word-coordinate parser over private captured bytes",
            "xlsx_reader": "build/phase3_xlsx_stream.py generic stdlib OOXML reader",
        },
        "bindings": {
            "raw": {"members": len(raw_identities), "bytes": EXPECTED["raw_bytes"],
                    "member_set_sha256": _sha(_json_bytes([
                        [Path(item["canonical_path"]).name, item["size"], item["sha256"]]
                        for item in raw_identities
                    ])), "member_identities": raw_identities,
                    "non_source_role": {
                        "names": list(NON_SOURCE_NAMES),
                        "identities": non_source_identities,
                        "included_in_source_totals": False,
                    }},
            "normalized": {**NORMALIZED_BINDING, "sheet": SHEET_NAME,
                           "rows": EXPECTED["projected_rows"], "columns": len(HEADERS),
                           "identity": _identity_dict(normalized_sheet.post_identity)},
            "normalized_sidecar": {**SIDECAR_BINDING,
                                   "identity": _identity_dict(sidecar_capture.identity),
                                   "contract": sidecar_checks},
            "r7_lifecycle_witness": {**R7_RESULT_BINDING,
                                     "identity": _identity_dict(r7_capture.identity),
                                     "contract": r7_checks},
        },
        "provenance": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pdfplumber": importlib.metadata.version("pdfplumber"),
            "pdfminer_six": importlib.metadata.version("pdfminer.six"),
            "loaded_parser_module_manifest": module_manifest,
            "code_identities": {name: _identity_dict(identity) for name, identity in code_after.items()},
            "executed_gates": {"reader": reader_gate, "family": family_gate},
            "xlsx_topology": topology,
        },
        "field_dispositions": FIELD_DISPOSITIONS,
        "field_coverage": coverage,
        "raw_source_digests": _dataset_digests(SOURCE_HEADERS, source_rows),
        "raw_source_provenance_digests": _dataset_digests(source_provenance_headers, source_provenance_rows),
        "document_metadata_digests": _dataset_digests(metadata_headers, metadata_rows),
        "independently_projected_digests": _dataset_digests(HEADERS, projected_rows),
        "normalized_digests": _dataset_digests(HEADERS, [row.values for row in normalized_sheet.rows]),
        "projection_comparison": projection,
        "classified_projection_residue": classified,
        "unexplained_projection_residue_count": unexplained,
        "identity_and_collision_census": {
            **collision_census,
            "owners": {"count": len(owners), "direction_counts": dict(sorted(owner_direction_counts.items())),
                       "ordered_sha256": _ordered_digest(owners)},
            "routes": len({record["route"] for record in projected_records}),
            "counties": len({record["county"] for record in projected_records}),
        },
        "order_and_anomaly_census": {
            "source_records": len(source_records),
            "projected_rows_by_district": dict(sorted(projected_by_district.items())),
            "unknown_equates": len(unknown_equates),
            "distance_pointer_tokens": dict(sorted(Counter(record["distance"] for record in pointer_records).items())),
            "continuation_count": len(continuations),
            "normalized_source_rows_contiguous": True,
        },
        "documents": documents,
        "semantic_mutation_probes": probes,
        "findings": {
            "blocking": [
                {"id": "CMP-AUD-155", "status": "verified", "fields": ["DISTRICT", "DIRECTION", "REPORT_ID", "REPORT_TITLE", "REFERENCE_DATE", "REPORT_DATE", "GENERATION_TIME", "PDF_METADATA", "POLICY_WARNING"]},
                {"id": "CMP-AUD-156", "status": "verified", "classified_cells": len(pointer_mismatches)},
                {"id": "CMP-AUD-158", "status": "verified", "classified_source_records": len(unknown_equates)},
                {"id": "CMP-AUD-159", "status": "verified", "classified_cells": len(description_mismatches)},
            ]
        },
        "audit_invariants": invariants,
        "projection_exact": projection["ordered_exact"],
        "stage6_family_audit_complete": True,
        "normalized_full_conservation": False,
    }


def _xlsx_topology(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path, "r") as archive:
        workbook = archive.read("xl/workbook.xml")
        rels = archive.read("xl/_rels/workbook.xml.rels")
        formula_cells = 0
        error_cells = 0
        for name in archive.namelist():
            if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                payload = archive.read(name)
                formula_cells += len(re.findall(br"<f(?:\s|>)", payload))
                error_cells += len(re.findall(br'<c[^>]*\bt="e"', payload))
    return {
        "workbook_xml_sha256": _sha(workbook),
        "workbook_relationships_sha256": _sha(rels),
        "formula_cell_count": formula_cells,
        "error_cell_count": error_cells,
        "exact": formula_cells == 0 and error_cells == 0,
    }


def _write_json(path: Path, document: Mapping[str, object]) -> FileIdentity:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True,
                         indent=2).encode("utf-8") + b"\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return capture_file_identity(path)


def _acceptance(result_path: Path, result_identity: FileIdentity) -> dict[str, object]:
    tracked = {
        "result": result_identity,
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
        "normalized": capture_file_identity(NORMALIZED_XLSX),
        "sidecar": capture_file_identity(NORMALIZED_SIDECAR),
        "lifecycle": capture_file_identity(R7_RESULT),
    }
    raw = [capture_file_identity(RAW_DIR / name) for name, _size, _digest in RAW_BINDINGS]
    non_source = [capture_file_identity(RAW_DIR / name) for name in NON_SOURCE_NAMES]
    return {
        "schema_version": 1,
        "decision": "accepted_stage6_family_audit",
        "result_path": str(result_path),
        "tracked_identities": {name: _stable_identity(identity) for name, identity in tracked.items()},
        "raw_member_identities": [_stable_identity(identity) for identity in raw],
        "non_source_role_identities": [_stable_identity(identity) for identity in non_source],
        "required_result_flags": {
            "stage6_family_audit_complete": True,
            "projection_exact": False,
            "normalized_full_conservation": False,
            "unexplained_projection_residue_count": 0,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--acceptance", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run()
        result_identity = _write_json(args.result, result)
        # Re-read the committed result and require the semantic flags before detached acceptance.
        committed = json.loads(args.result.read_text(encoding="utf-8"))
        if not (committed.get("stage6_family_audit_complete") is True
                and committed.get("projection_exact") is False
                and committed.get("normalized_full_conservation") is False
                and committed.get("unexplained_projection_residue_count") == 0):
            raise ConservationError("committed result flags do not satisfy the audit contract")
        acceptance_path = args.acceptance or Path(str(args.result) + ".acceptance.json")
        acceptance_identity = _write_json(
            acceptance_path, _acceptance(args.result, result_identity)
        )
    except Exception as exc:
        print(f"FAIL phase6 Highway Sequence conservation: {type(exc).__name__}: {exc}")
        return 1
    print(
        "PASS phase6 Highway Sequence conservation: "
        f"{result_identity.size} bytes {result_identity.sha256}; "
        f"acceptance {acceptance_identity.size} bytes {acceptance_identity.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

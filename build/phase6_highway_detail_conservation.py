#!/usr/bin/env python3
"""Independent Stage-6 Highway Detail raw-to-normalized conservation oracle.

The oracle imports no application parser, normalizer, comparator, evidence
adapter, or report-family constant.  It streams the exact authoritative 56-
column TSN workbook and the exact r7 normalized workbook with the generic
stdlib OOXML reader in :mod:`phase3_xlsx_stream`, projects all 60,083 rows from
an independently declared contract, and accounts for every raw field.

Projection parity and full conservation are deliberately separate.  The
current r7 workbook can reproduce its declared 38-column shape exactly while
still omitting authoritative ADT/evidence/change-flag facts needed by Report
View.  ``--allow-open-findings`` permits that documented product state to exit
zero only when the audit itself is complete and has no unexplained residue.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_EVEN, localcontext
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree
import zipfile

from phase3_xlsx_stream import (
    DATE,
    SCALAR,
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    StreamedSheet,
    XlsxLimits,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


RAW_DEFAULT = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\highway_detail\raw"
    r"\TSAR - HIGHWAY DETAIL_TSN.xlsx"
)
NORMALIZED_DEFAULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7\highway_detail\consolidated"
    r"\tsn_highway_detail_normalized.xlsx"
)
OUTPUT_DEFAULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase6_tsn_conservation"
    r"\highway_detail_conservation_r7.json"
)
R7_RESULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7\result.json"
)
R7_SIDECAR = NORMALIZED_DEFAULT.with_suffix(NORMALIZED_DEFAULT.suffix + ".outcome.json")
PDF_ORACLE_RESULT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\highway_detail_tsn_pdf_oracle_final.json"
)
GENERATOR_PATH = Path(__file__).resolve()
READER_PATH = Path(__file__).with_name("phase3_xlsx_stream.py").resolve()
READER_GATE_PATH = Path(__file__).with_name("check_phase3_xlsx_stream.py").resolve()

PROVENANCE_BINDINGS = {
    "accepted_r7_result": {
        "path": R7_RESULT, "bytes": 173_124,
        "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
    },
    "accepted_r7_highway_detail_sidecar": {
        "path": R7_SIDECAR, "bytes": 900,
        "sha256": "97a9ccff48d446eab5d4a16d4383bd7858025fd3022cf4a111cbbe0481175327",
    },
    "accepted_highway_detail_pdf_oracle": {
        "path": PDF_ORACLE_RESULT, "bytes": 664_322,
        "sha256": "540b1ce575be880f506ebc435acaabe253e238f4eba312a72a310129f4ecdc36",
    },
}

NORMALIZED_R7_SIDECAR_BINDING = {
    "bytes": 900,
    "sha256": "97a9ccff48d446eab5d4a16d4383bd7858025fd3022cf4a111cbbe0481175327",
    "completion": "complete",
    "skipped_inputs": 0,
    "failed_inputs": 0,
    "normalization_version": 2,
    "artifact_identity_token": (
        "tsn-normalized-v1:48c0009bdc5c04719f4fd837555917ff0cebd9e596ba4b0b353caab387cbfbcc"),
}

RAW_BINDING = {
    "bytes": 16_356_075,
    "sha256": "bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1",
    "sheet": "Sheet 1",
    "rows": 60_083,
    "columns": 56,
}
NORMALIZED_R7_BINDING = {
    "bytes": 8_478_589,
    "sha256": "46afd2b20c08113636eb69630065672afc1044dba02afeab445ac9f0afac34d5",
    "sheet": "Highway Detail (TSN)",
    "rows": 60_083,
    "columns": 38,
    "normalization_version": 2,
}

RAW_HEADERS = (
    "THY_ID", "DIST", "CNTY", "RTE", "RTE_SFX", "DIST_CNTY_ROUTE",
    "PP", "POSTMILE", "E_IND", "LENGTH", "REC_DATE", "HG", "AC",
    "ACC_SIG", "ACC_EFF_DATE", "CITY", "POP_CODE", "BEG_DATE",
    "ADT_AMT", "PROFILE", "BREAK_DESC", "LK_BACK_ADT", "CHNGMILE",
    "DVM", "DESCRIPTION", "NON_ADD", "LT_SIG", "L_EFF_DATE", "L_ST",
    "L_NO_LANES", "L_SF", "L_OT_TOT", "L_OT_TR", "L_TR_WID",
    "L_IN_TOT", "L_IN_TR", "MED_SIG", "M_EFF_DATE", "M_TYPE_CODE",
    "M_CL", "M_BA", "M_WID", "M_VA", "RT_SIG", "R_EFF_DATE",
    "R_ST", "R_NO_LANES", "R_SF", "R_IN_TOT", "R_IN_TR", "R_TR_WID",
    "R_OT_TOT", "R_OT_TR", "SEG_ORDER_ID", "REFERENCE_DATE",
    "EXTRACT_DATE",
)
NORMALIZED_HEADERS = (
    "Route", "Post Mile", "PS", "Length", "Date of Rec", "HG", "AC",
    "Acc-Cont Eff", "City", "RU", "RU Eff", "Description", "NA",
    "LB Eff", "LB S/T", "LB #Ln", "LB S/F", "LB OT-TO", "LB OT-TR",
    "LB Wid", "LB IN-TO", "LB IN-TR", "Med Eff", "Med T", "Med C",
    "Med B", "Med V/WDA", "RB Eff", "RB S/T", "RB #Ln", "RB S/F",
    "RB IN-TO", "RB IN-TR", "RB Wid", "RB OT-TO", "RB OT-TR",
    "TSN District", "TSN County",
)

DATE_SOURCE_FIELDS = (
    "REC_DATE", "ACC_EFF_DATE", "BEG_DATE", "L_EFF_DATE", "M_EFF_DATE",
    "R_EFF_DATE",
)
NUMERIC_NORMALIZED_FIELDS = {
    "L_NO_LANES", "L_OT_TOT", "L_OT_TR", "L_TR_WID", "L_IN_TOT",
    "L_IN_TR", "R_NO_LANES", "R_SF", "R_IN_TOT", "R_IN_TR",
    "R_TR_WID", "R_OT_TOT", "R_OT_TR",
}
DIRECT_TARGETS = {
    "HG": "HG", "AC": "AC", "CITY": "City", "POP_CODE": "RU",
    "L_ST": "LB S/T", "L_SF": "LB S/F", "M_TYPE_CODE": "Med T",
    "M_CL": "Med C", "M_BA": "Med B", "R_ST": "RB S/T",
    "R_SF": "RB S/F",
}
COMPOSED_TARGETS = {
    "LENGTH": "Length", "REC_DATE": "Date of Rec",
    "ACC_EFF_DATE": "Acc-Cont Eff", "BEG_DATE": "RU Eff",
    "DESCRIPTION": "Description", "NON_ADD": "NA",
    "L_EFF_DATE": "LB Eff", "L_NO_LANES": "LB #Ln",
    "L_OT_TOT": "LB OT-TO", "L_OT_TR": "LB OT-TR",
    "L_TR_WID": "LB Wid", "L_IN_TOT": "LB IN-TO",
    "L_IN_TR": "LB IN-TR", "M_EFF_DATE": "Med Eff",
    "R_EFF_DATE": "RB Eff", "R_NO_LANES": "RB #Ln",
    "R_IN_TOT": "RB IN-TO", "R_IN_TR": "RB IN-TR",
    "R_TR_WID": "RB Wid", "R_OT_TOT": "RB OT-TO",
    "R_OT_TR": "RB OT-TR",
}
EVIDENCE_OMISSIONS = (
    "ACC_SIG", "ADT_AMT", "PROFILE", "LK_BACK_ADT", "CHNGMILE", "DVM",
    "LT_SIG", "MED_SIG", "RT_SIG",
)


def _disposition(kind: str, targets: Sequence[str], role: str) -> dict[str, object]:
    return {"kind": kind, "normalized_targets": list(targets), "role": role}


FIELD_DISPOSITIONS: dict[str, dict[str, object]] = {
    "THY_ID": _disposition("source_only", (), "database surrogate identifier"),
    "DIST": _disposition("projected", ("TSN District",), "district identity claim"),
    "CNTY": _disposition("projected", ("TSN County",), "county identity claim"),
    "RTE": _disposition("composed", ("Route",), "three-digit route base"),
    "RTE_SFX": _disposition("composed", ("Route",), "route suffix"),
    "DIST_CNTY_ROUTE": _disposition(
        "relational", (), "exact district/county/route composite assertion"),
    "PP": _disposition("composed", ("Post Mile",), "postmile prefix"),
    "POSTMILE": _disposition("composed", ("Post Mile",), "fixed postmile"),
    "E_IND": _disposition("composed", ("PS",), "equation-marker claim"),
    "LENGTH": _disposition("composed", ("Length",), "fixed three-decimal length"),
    "REC_DATE": _disposition("composed", ("Date of Rec",), "record date"),
    "HG": _disposition(
        "projected_relational", ("HG", "Post Mile"),
        "highway group and independent-alignment roadbed claim"),
    "AC": _disposition("projected", ("AC",), "access-control code"),
    "ACC_SIG": _disposition(
        "source_only", (), "printed access-control change flag"),
    "ACC_EFF_DATE": _disposition(
        "composed", ("Acc-Cont Eff",), "access-control effective date"),
    "CITY": _disposition("projected", ("City",), "city code"),
    "POP_CODE": _disposition("projected", ("RU",), "rural/urban code"),
    "BEG_DATE": _disposition("composed", ("RU Eff",), "TSN ADT begin date"),
    "ADT_AMT": _disposition("source_only", (), "printed LK-AHD evidence value"),
    "PROFILE": _disposition("source_only", (), "printed ADT profile code"),
    "BREAK_DESC": _disposition("source_only", (), "internal break helper"),
    "LK_BACK_ADT": _disposition("source_only", (), "printed LK-BACK evidence value"),
    "CHNGMILE": _disposition("source_only", (), "printed CHANGE/MILE evidence value"),
    "DVM": _disposition("source_only", (), "printed DVM evidence value"),
    "DESCRIPTION": _disposition(
        "composed", ("Description",), "collapsed source description"),
    "NON_ADD": _disposition("composed", ("NA",), "non-add claim"),
    "LT_SIG": _disposition("source_only", (), "printed left-roadbed change flag"),
    "L_EFF_DATE": _disposition("composed", ("LB Eff",), "left-roadbed effective date"),
    "L_ST": _disposition("projected", ("LB S/T",), "left-roadbed S/T"),
    "L_NO_LANES": _disposition("composed", ("LB #Ln",), "left-roadbed lane count"),
    "L_SF": _disposition("projected", ("LB S/F",), "left-roadbed S/F"),
    "L_OT_TOT": _disposition("composed", ("LB OT-TO",), "left outside shoulder total"),
    "L_OT_TR": _disposition("composed", ("LB OT-TR",), "left outside shoulder treated"),
    "L_TR_WID": _disposition("composed", ("LB Wid",), "left traveled-way width"),
    "L_IN_TOT": _disposition("composed", ("LB IN-TO",), "left inside shoulder total"),
    "L_IN_TR": _disposition("composed", ("LB IN-TR",), "left inside shoulder treated"),
    "MED_SIG": _disposition("source_only", (), "printed median change flag"),
    "M_EFF_DATE": _disposition("composed", ("Med Eff",), "median effective date"),
    "M_TYPE_CODE": _disposition("projected", ("Med T",), "median type"),
    "M_CL": _disposition("projected", ("Med C",), "median C/L"),
    "M_BA": _disposition("projected", ("Med B",), "median B/A"),
    "M_WID": _disposition("composed", ("Med V/WDA",), "median two-digit width"),
    "M_VA": _disposition("composed", ("Med V/WDA",), "median variance code"),
    "RT_SIG": _disposition("source_only", (), "printed right-roadbed change flag"),
    "R_EFF_DATE": _disposition("composed", ("RB Eff",), "right-roadbed effective date"),
    "R_ST": _disposition("projected", ("RB S/T",), "right-roadbed S/T"),
    "R_NO_LANES": _disposition("composed", ("RB #Ln",), "right-roadbed lane count"),
    "R_SF": _disposition("projected", ("RB S/F",), "right-roadbed S/F"),
    "R_IN_TOT": _disposition("composed", ("RB IN-TO",), "right inside shoulder total"),
    "R_IN_TR": _disposition("composed", ("RB IN-TR",), "right inside shoulder treated"),
    "R_TR_WID": _disposition("composed", ("RB Wid",), "right traveled-way width"),
    "R_OT_TOT": _disposition("composed", ("RB OT-TO",), "right outside shoulder total"),
    "R_OT_TR": _disposition("composed", ("RB OT-TR",), "right outside shoulder treated"),
    "SEG_ORDER_ID": _disposition(
        "relational", (), "source order and within-DCR ordering assertion"),
    "REFERENCE_DATE": _disposition(
        "source_only_metadata", (), "authoritative reference-date singleton"),
    "EXTRACT_DATE": _disposition(
        "source_only_metadata", (), "authoritative extract-date singleton"),
}

EXPECTED_REFERENCE_DATE = date(2025, 9, 8)
EXPECTED_EXTRACT_DATE = date(2025, 9, 15)
EXPECTED_COLLISIONS = {
    "full_with_district_and_equation": {"duplicate_groups": 77, "duplicate_rows": 156},
    "district_without_equation": {"duplicate_groups": 83, "duplicate_rows": 168},
    "legacy_without_district_or_equation": {"duplicate_groups": 86, "duplicate_rows": 174},
    "route_canonical_pm_cross_county": {"cross_county_keys": 438, "county_identities": 976},
    "base_route_pp_pm_cross_county": {"cross_county_keys": 453, "county_identities": 1_008},
}

_WS_RE = re.compile(r"\s+")
_DECIMAL_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_YY_DATE_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})$")


class ConservationError(ValueError):
    """The frozen source or conservation contract was not satisfied."""


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        token = value.as_tuple()
        return ["decimal", token.sign, list(token.digits), token.exponent]
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
        digest.update(str(len(payload)).encode("ascii") + b":" + payload + b"\n")
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
        ordered.update(str(len(payload)).encode("ascii") + b":" + payload + b"\n")
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


def _scan_formula_and_error_cells(archive: zipfile.ZipFile) -> dict[str, int]:
    members = sorted(
        name for name in archive.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
        and "/_rels/" not in name
    )
    if len(members) != 1:
        raise ConservationError(
            f"bound one-sheet workbook has {len(members)} worksheet XML members")
    formula_count = error_count = 0
    with archive.open(members[0], "r") as raw:
        sheet_data = None
        for event, element in ElementTree.iterparse(raw, events=("start", "end")):
            local = element.tag.rsplit("}", 1)[-1]
            if event == "start" and local == "sheetData":
                sheet_data = element
            elif event == "end" and local == "f":
                formula_count += 1
            elif event == "end" and local == "c" and element.attrib.get("t") == "e":
                error_count += 1
            elif event == "end" and local == "row":
                element.clear()
                if sheet_data is not None:
                    sheet_data.remove(element)
    return {"formula_cell_count": formula_count, "error_cell_count": error_count}


def _workbook_topology(path: Path) -> dict[str, object]:
    captured = capture_file_bytes(path)
    with zipfile.ZipFile(BytesIO(captured.payload), "r") as archive:
        root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        cell_kinds = _scan_formula_and_error_cells(archive)
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
    if cell_kinds["formula_cell_count"] or cell_kinds["error_cell_count"]:
        raise ConservationError(
            "formula/error cells are forbidden: "
            f"{cell_kinds['formula_cell_count']} formula, "
            f"{cell_kinds['error_cell_count']} error")
    return {
        "sheets": sheets,
        "date_system": "1904" if date1904 else "1900",
        "immutable_private_capture": _identity_dict(captured.identity),
        "pre_sha256": captured.identity.sha256,
        "post_sha256": captured.identity.sha256,
        "size": captured.identity.size,
        **cell_kinds,
    }


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


def _capture_exact_identity(path: Path, binding: dict[str, object],
                            label: str) -> FileIdentity:
    identity = capture_file_identity(path)
    observed = (identity.size, identity.sha256)
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    if observed != expected:
        raise ConservationError(
            f"{label} binding mismatch: {observed!r} != {expected!r}")
    return identity


def _capture_exact_json(path: Path, binding: dict[str, object],
                        label: str) -> tuple[FileIdentity, dict[str, object]]:
    """Parse JSON only from the exact immutable bytes whose identity is bound."""
    captured = capture_file_bytes(path)
    observed = (captured.identity.size, captured.identity.sha256)
    expected = (int(binding["bytes"]), str(binding["sha256"]))
    if observed != expected:
        raise ConservationError(
            f"{label} binding mismatch: {observed!r} != {expected!r}")
    try:
        document = json.loads(captured.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConservationError(f"{label} is not canonical UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ConservationError(f"{label} JSON root must be an object")
    return captured.identity, document


def _capture_code_identities() -> dict[str, FileIdentity]:
    return {
        "generator": capture_file_identity(GENERATOR_PATH),
        "reader": capture_file_identity(READER_PATH),
        "reader_mutation_gate": capture_file_identity(READER_GATE_PATH),
    }


def _capture_tracked_identities(raw_path: Path,
                                normalized_path: Path) -> dict[str, FileIdentity]:
    return {
        "raw": capture_file_identity(raw_path),
        "normalized": capture_file_identity(normalized_path),
        "normalized_outcome_sidecar": capture_file_identity(R7_SIDECAR),
        "r7_lifecycle_witness": capture_file_identity(R7_RESULT),
        "accepted_pdf_oracle": capture_file_identity(PDF_ORACLE_RESULT),
        **_capture_code_identities(),
    }


def _execute_reader_gate(gate_identity: FileIdentity) -> dict[str, object]:
    process = subprocess.run(
        [sys.executable, str(READER_GATE_PATH)],
        cwd=str(GENERATOR_PATH.parent.parent), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=120, check=False,
    )
    stdout = process.stdout.rstrip("\r\n")
    execution = {
        "command": [sys.executable, str(READER_GATE_PATH)],
        "exit_code": process.returncode,
        "stdout": stdout,
        "stdout_utf8_sha256": _sha(stdout.encode("utf-8")),
        "gate_source_identity": _identity_dict(gate_identity),
    }
    if process.returncode != 0 or not stdout.startswith("OK  Phase-3 stdlib XLSX stream:"):
        raise ConservationError(
            f"independent reader mutation gate failed: exit={process.returncode}, "
            f"stdout={stdout!r}")
    return execution


def _r7_witness_contract(witness: dict[str, object], sidecar: dict[str, object],
                         pdf_oracle: dict[str, object]) -> dict[str, object]:
    families = [item for item in witness.get("families", [])
                if item.get("report") == "highway_detail"]
    if len(families) != 1:
        raise ConservationError(
            f"accepted r7 witness has {len(families)} Highway Detail family records")
    family = families[0]
    output = family.get("output", {})
    generated = {
        item.get("relative_path"): item
        for item in witness.get("generated_output_artifact_manifest", {}).get("members", [])
    }
    workbook_rel = "highway_detail/consolidated/tsn_highway_detail_normalized.xlsx"
    sidecar_rel = workbook_rel + ".outcome.json"
    delta_manifest = pdf_oracle.get("reconciliation", {}).get(
        "observed_delta_manifest", {})
    length_items = [
        item for item in delta_manifest.get("items", [])
        if item.get("changed_fields") == ["LENGTH"]
    ]
    expected_length_pairs = {
        item.get("identity", {}).get("postmile"):
        (item.get("xlsx_stream", [None, None, None])[2],
         item.get("pdf_stream", [None, None, None])[2])
        for item in length_items
    }
    checks = {
        "witness_acceptance_complete": witness.get("acceptance") == "complete",
        "family_builder_complete": (
            family.get("result", {}).get("status") == "ok"
            and family.get("result", {}).get("completion") == "complete"
            and family.get("result", {}).get("skipped_inputs") == 0
            and family.get("result", {}).get("failed_inputs") == 0),
        "family_output_exact": (
            output.get("bytes") == NORMALIZED_R7_BINDING["bytes"]
            and output.get("sha256") == NORMALIZED_R7_BINDING["sha256"]
            and output.get("relative_path") == workbook_rel
            and output.get("sidecar_relative_path") == sidecar_rel),
        "generated_manifest_workbook_exact": (
            generated.get(workbook_rel, {}).get("bytes") == NORMALIZED_R7_BINDING["bytes"]
            and generated.get(workbook_rel, {}).get("sha256")
            == NORMALIZED_R7_BINDING["sha256"]),
        "generated_manifest_sidecar_exact": (
            generated.get(sidecar_rel, {}).get("bytes")
            == PROVENANCE_BINDINGS["accepted_r7_highway_detail_sidecar"]["bytes"]
            and generated.get(sidecar_rel, {}).get("sha256")
            == PROVENANCE_BINDINGS["accepted_r7_highway_detail_sidecar"]["sha256"]),
        "sidecar_complete_and_zero_failures": (
            sidecar.get("completion") == "complete"
            and sidecar.get("skipped_inputs") == 0
            and sidecar.get("failed_inputs") == 0
            and sidecar.get("tsn_normalization_version")
            == NORMALIZED_R7_BINDING["normalization_version"]),
        "sidecar_workbook_identity_exact": (
            sidecar.get("tsn_normalized_workbook_identity", {}).get("byte_length")
            == NORMALIZED_R7_BINDING["bytes"]
            and sidecar.get("tsn_normalized_workbook_identity", {}).get("sha256")
            == NORMALIZED_R7_BINDING["sha256"]),
        "sidecar_raw_member_exact": sidecar.get("tsn_raw_manifest", {}).get("members") == [{
            "relative_path": "TSAR - HIGHWAY DETAIL_TSN.xlsx",
            "byte_length": RAW_BINDING["bytes"],
            "sha256": RAW_BINDING["sha256"],
        }],
        "sidecar_lifecycle_claims_exact": (
            sidecar.get("completion") == NORMALIZED_R7_SIDECAR_BINDING["completion"]
            and sidecar.get("skipped_inputs")
            == NORMALIZED_R7_SIDECAR_BINDING["skipped_inputs"]
            and sidecar.get("failed_inputs")
            == NORMALIZED_R7_SIDECAR_BINDING["failed_inputs"]
            and sidecar.get("tsn_normalization_version")
            == NORMALIZED_R7_SIDECAR_BINDING["normalization_version"]
            and sidecar.get("tsn_artifact_identity_token")
            == NORMALIZED_R7_SIDECAR_BINDING["artifact_identity_token"]),
        "accepted_pdf_oracle_exact_delta_manifest": (
            pdf_oracle.get("status") == "pass"
            and delta_manifest.get("item_count") == 443
            and delta_manifest.get("sha256")
            == "d101bc1263188dcb436a9218bad6774ab047368e819c205d1e53b9b812b56d8a"
            and delta_manifest.get("field_counts", {}).get("LENGTH") == 2),
        "accepted_pdf_oracle_two_length_items_exact": expected_length_pairs == {
            "044.228": ("000.007", "000.008"),
            "044.236": ("000.013", "000.014"),
        },
        "accepted_pdf_oracle_has_no_unexplained_allowlist_residue": (
            pdf_oracle.get("delta_allowlist", {}).get("matches") is True
            and pdf_oracle.get("reconciliation", {}).get("unresolved_cells") == 0
            and pdf_oracle.get("reconciliation", {}).get(
                "unsafe_stream_attribution_count") == 0),
        "accepted_pdf_oracle_metadata_mapping_exact": (
            pdf_oracle.get("field_to_pdf_mapping", {}).get("REFERENCE_DATE")
            == "report-parameter page / REFERENCE DATE"
            and pdf_oracle.get("field_to_pdf_mapping", {}).get("EXTRACT_DATE")
            == "report-parameter and data-page header / REPORT DATE"),
    }
    if not all(checks.values()):
        raise ConservationError(
            "accepted r7 Highway Detail result/sidecar contract failed: "
            + ", ".join(name for name, passed in checks.items() if not passed))
    return {
        "checks": checks,
        "all_exact": True,
        "artifact_identity_token": sidecar.get("tsn_artifact_identity_token"),
        "family_result": family.get("result"),
        "accepted_pdf_oracle_length_pairs": expected_length_pairs,
        "accepted_pdf_metadata_mapping": {
            field: pdf_oracle.get("field_to_pdf_mapping", {}).get(field)
            for field in ("REFERENCE_DATE", "EXTRACT_DATE")
        },
    }


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return str(value).strip()


def _route_token(rte: object, suffix: object) -> tuple[str, str, str]:
    base = _text(rte)
    if not base.isdigit():
        raise ConservationError(f"invalid Highway Detail route base: {base!r}")
    base = f"{int(base):03d}"
    tail = _text(suffix).upper()
    if tail and not re.fullmatch(r"[A-Z]", tail):
        raise ConservationError(f"invalid Highway Detail route suffix: {tail!r}")
    return base + tail, base, tail


def _decimal(value: object, label: str) -> Decimal:
    literal = _text(value)
    if not _DECIMAL_RE.fullmatch(literal):
        raise ConservationError(f"invalid {label} decimal token: {literal!r}")
    try:
        number = Decimal(literal)
    except InvalidOperation as exc:
        raise ConservationError(f"invalid {label} decimal token: {literal!r}") from exc
    if not number.is_finite():
        raise ConservationError(f"non-finite {label} decimal token: {literal!r}")
    return number


def _fixed_three(value: object, label: str) -> str:
    number = _decimal(value, label)
    with localcontext() as context:
        context.prec = max(50, len(number.as_tuple().digits) + 10)
        rounded = number.quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
    return format(rounded, "07.3f")


def _roadbed(value: object) -> str:
    token = _text(value).upper()
    return token if token in {"L", "R"} else ""


def _canonical_postmile(values: dict[str, object]) -> str:
    return (
        _text(values["PP"]).upper()
        + _fixed_three(values["POSTMILE"], "POSTMILE")
        + _roadbed(values["HG"])
    )


def _date_year(value: str) -> int:
    match = _YY_DATE_RE.fullmatch(value)
    if match is None:
        raise ConservationError(f"invalid two-digit date token: {value!r}")
    year, month, day = map(int, match.groups())
    full = 2000 + year if year <= 29 else 1900 + year
    date(full, month, day)
    return full


def _norm_date(value: object, label: str) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        token = value.strftime("%y-%m-%d")
    elif isinstance(value, date):
        token = value.strftime("%y-%m-%d")
    else:
        token = _text(value)
    if re.fullmatch(r"\++", token):
        # The authoritative legacy export uses plus signs as a visible
        # fixed-width overflow claim.  Preserve it literally; it is neither a
        # date nor a blank and is counted separately in the anomaly census.
        return token
    _date_year(token)
    return token


def _norm_num(value: object) -> str:
    token = _text(value)
    if re.fullmatch(r"\d+", token):
        return str(int(token))
    return token


def _norm_na(value: object) -> str:
    token = _text(value).upper()
    return "" if token == "A" else token


def _norm_wda(width: object, variance: object) -> str:
    token = (_text(width) + _text(variance)).upper()
    match = re.fullmatch(r"(\d+)([A-Z]?)", token)
    if match is None:
        return token
    return f"{int(match.group(1)):02d}{match.group(2)}"


def _expected_dcr(values: dict[str, object]) -> str:
    _route, base, suffix = _route_token(values["RTE"], values["RTE_SFX"])
    return (
        f"{_text(values['DIST'])}-{_text(values['CNTY'])}-{base}"
        + (f" {suffix}" if suffix else "")
    )


def _full_identity(values: dict[str, object]) -> tuple[str, ...]:
    _route, base, suffix = _route_token(values["RTE"], values["RTE_SFX"])
    return (
        _text(values["DIST"]), _text(values["CNTY"]).rstrip("."), base, suffix,
        _text(values["PP"]).upper(), _fixed_three(values["POSTMILE"], "POSTMILE"),
        _text(values["E_IND"]).upper(), _roadbed(values["HG"]),
    )


def _project_raw_row(row: Sequence[object]) -> tuple[tuple[str, ...], dict[str, object]]:
    values = dict(zip(RAW_HEADERS, row))
    route, _base, _suffix = _route_token(values["RTE"], values["RTE_SFX"])
    observed_dcr = _text(values["DIST_CNTY_ROUTE"])
    expected_dcr = _expected_dcr(values)
    if observed_dcr != expected_dcr:
        raise ConservationError(
            f"DIST_CNTY_ROUTE mismatch: {observed_dcr!r} != {expected_dcr!r}")
    direct = {target: _text(values[source]) for source, target in DIRECT_TARGETS.items()}
    composed = {
        "Length": _fixed_three(values["LENGTH"], "LENGTH"),
        "Date of Rec": _norm_date(values["REC_DATE"], "REC_DATE"),
        "Acc-Cont Eff": _norm_date(values["ACC_EFF_DATE"], "ACC_EFF_DATE"),
        "RU Eff": _norm_date(values["BEG_DATE"], "BEG_DATE"),
        "Description": _WS_RE.sub(" ", _text(values["DESCRIPTION"])),
        "NA": _norm_na(values["NON_ADD"]),
        "LB Eff": _norm_date(values["L_EFF_DATE"], "L_EFF_DATE"),
        "Med Eff": _norm_date(values["M_EFF_DATE"], "M_EFF_DATE"),
        "RB Eff": _norm_date(values["R_EFF_DATE"], "R_EFF_DATE"),
        "Med V/WDA": _norm_wda(values["M_WID"], values["M_VA"]),
    }
    for source, target in COMPOSED_TARGETS.items():
        if target in composed:
            continue
        composed[target] = _norm_num(values[source])
    by_target = {**direct, **composed}
    projected = (
        route,
        _canonical_postmile(values),
        "E" if _text(values["E_IND"]).upper() == "E" else "",
        by_target["Length"], by_target["Date of Rec"], by_target["HG"],
        by_target["AC"], by_target["Acc-Cont Eff"], by_target["City"],
        by_target["RU"], by_target["RU Eff"], by_target["Description"],
        by_target["NA"], by_target["LB Eff"], by_target["LB S/T"],
        by_target["LB #Ln"], by_target["LB S/F"], by_target["LB OT-TO"],
        by_target["LB OT-TR"], by_target["LB Wid"], by_target["LB IN-TO"],
        by_target["LB IN-TR"], by_target["Med Eff"], by_target["Med T"],
        by_target["Med C"], by_target["Med B"], by_target["Med V/WDA"],
        by_target["RB Eff"], by_target["RB S/T"], by_target["RB #Ln"],
        by_target["RB S/F"], by_target["RB IN-TO"], by_target["RB IN-TR"],
        by_target["RB Wid"], by_target["RB OT-TO"], by_target["RB OT-TR"],
        _text(values["DIST"]), _text(values["CNTY"]).rstrip("."),
    )
    return projected, {
        "identity": _full_identity(values),
        "dcr": (_text(values["DIST"]), _text(values["CNTY"]).rstrip("."), route),
        "route": route,
        "route_base": route[:3],
        "county": _text(values["CNTY"]).rstrip("."),
        "district": _text(values["DIST"]),
        "pp": _text(values["PP"]).upper(),
        "postmile": _fixed_three(values["POSTMILE"], "POSTMILE"),
        "canonical_postmile": _canonical_postmile(values),
        "equation": _text(values["E_IND"]).upper(),
        "roadbed": _roadbed(values["HG"]),
        "seg_order_id": values["SEG_ORDER_ID"],
    }


def _counter_summary(counter: Counter[tuple[object, ...]]) -> dict[str, object]:
    duplicates = [count for count in counter.values() if count > 1]
    return {
        "distinct_identities": len(counter),
        "duplicate_groups": len(duplicates),
        "duplicate_rows": sum(duplicates),
        "duplicate_occurrences_beyond_first": sum(count - 1 for count in duplicates),
        "largest_multiplicity": max(duplicates, default=1),
        "duplicate_multiplicity_distribution": dict(sorted(Counter(duplicates).items())),
        "typed_multiplicity_sha256": _multiset_digest(
            [identity for identity, count in counter.items() for _ in range(count)])[0],
    }


def _cross_county(groups: dict[tuple[object, ...], set[str]]) -> dict[str, int]:
    selected = [counties for counties in groups.values() if len(counties) > 1]
    return {
        "cross_county_keys": len(selected),
        "county_identities": sum(len(counties) for counties in selected),
        "largest_county_multiplicity": max((len(counties) for counties in selected), default=1),
    }


def _collision_census(raw_rows: Sequence[Sequence[object]],
                      row_info: Sequence[dict[str, object]]) -> dict[str, object]:
    full: Counter[tuple[object, ...]] = Counter()
    district_no_equation: Counter[tuple[object, ...]] = Counter()
    legacy: Counter[tuple[object, ...]] = Counter()
    route_canonical_pm: dict[tuple[object, ...], set[str]] = defaultdict(set)
    base_route_pp_pm: dict[tuple[object, ...], set[str]] = defaultdict(set)
    signatures: dict[tuple[object, ...], set[str]] = defaultdict(set)
    identity_ordinals: Counter[tuple[object, ...]] = Counter()
    occurrence_sequence = []
    for raw, info in zip(raw_rows, row_info):
        identity = tuple(info["identity"])
        full[identity] += 1
        identity_ordinals[identity] += 1
        occurrence_sequence.append(identity + (str(identity_ordinals[identity]),))
        signatures[identity].add(_sha(_row_wire(raw)))
        district, county, base, suffix, pp, postmile, _equation, roadbed = identity
        route = base + suffix
        district_no_equation[(district, county, route, pp, postmile, roadbed)] += 1
        legacy[(county, route, pp, postmile, roadbed)] += 1
        route_canonical_pm[(route, str(info["canonical_postmile"]))].add(county)
        base_route_pp_pm[(base, pp, postmile)].add(county)
    full_summary = _counter_summary(full)
    full_summary.update({
        "nonidentical_duplicate_groups": sum(
            len(signatures[identity]) > 1 for identity, count in full.items() if count > 1),
        "nonidentical_duplicate_rows": sum(
            count for identity, count in full.items()
            if count > 1 and len(signatures[identity]) > 1),
        "source_occurrence_order_sha256": _ordered_digest(occurrence_sequence),
    })
    return {
        "full_with_district_and_equation": full_summary,
        "district_without_equation": _counter_summary(district_no_equation),
        "legacy_without_district_or_equation": _counter_summary(legacy),
        "route_canonical_pm_cross_county": _cross_county(route_canonical_pm),
        "base_route_pp_pm_cross_county": _cross_county(base_route_pp_pm),
    }


def _physical_rows_contiguous_from_2(source_rows: Sequence[int]) -> bool:
    return list(source_rows) == list(range(2, 2 + len(source_rows)))


def _order_and_anomaly_census(raw_sheet: StreamedSheet,
                              normalized_sheet: StreamedSheet,
                              raw_rows: Sequence[Sequence[object]],
                              row_info: Sequence[dict[str, object]]) -> dict[str, object]:
    raw_numbers = [row.source_row for row in raw_sheet.rows]
    normalized_numbers = [row.source_row for row in normalized_sheet.rows]
    seg_by_dcr: dict[tuple[object, ...], list[tuple[int, Decimal]]] = defaultdict(list)
    seg_non_decimal = []
    unknown_equation: Counter[str] = Counter()
    date_overflow_domains: dict[str, Counter[str]] = defaultdict(Counter)
    unknown_date_domains: dict[str, Counter[str]] = defaultdict(Counter)
    numeric_non_digit: dict[str, Counter[str]] = defaultdict(Counter)
    code_domains: dict[str, Counter[str]] = defaultdict(Counter)
    dcr_mismatches = []
    raw_index = {name: index for index, name in enumerate(RAW_HEADERS)}
    numeric_sources = tuple(
        source for source, target in COMPOSED_TARGETS.items()
        if target not in {"Length", "Date of Rec", "Acc-Cont Eff", "RU Eff",
                          "Description", "NA", "LB Eff", "Med Eff", "RB Eff"}
    )
    for source_row, raw, info in zip(raw_numbers, raw_rows, row_info):
        values = dict(zip(RAW_HEADERS, raw))
        seg = values["SEG_ORDER_ID"]
        if isinstance(seg, Decimal):
            seg_by_dcr[tuple(info["dcr"])].append((source_row, seg))
        else:
            seg_non_decimal.append({"source_row": source_row, "typed_value": _typed(seg)})
        equation = _text(values["E_IND"]).upper()
        if equation not in {"", "E"}:
            unknown_equation[equation] += 1
        for source in numeric_sources:
            token = _text(values[source])
            if token and not token.isdigit():
                numeric_non_digit[source][token] += 1
        for source in DATE_SOURCE_FIELDS:
            token = _text(values[source])
            if re.fullmatch(r"\++", token):
                date_overflow_domains[source][token] += 1
            elif token:
                try:
                    _date_year(token)
                except (ConservationError, ValueError):
                    unknown_date_domains[source][token] += 1
        for source in ("HG", "AC", "ACC_SIG", "POP_CODE", "NON_ADD", "LT_SIG",
                       "L_ST", "L_SF", "MED_SIG", "M_TYPE_CODE", "M_CL", "M_BA",
                       "M_VA", "RT_SIG", "R_ST", "R_SF"):
            code_domains[source][_text(values[source])] += 1
        if _text(values["DIST_CNTY_ROUTE"]) != _expected_dcr(values):
            dcr_mismatches.append({
                "source_row": source_row,
                "observed": _text(values["DIST_CNTY_ROUTE"]),
                "expected": _expected_dcr(values),
            })
    inversions = []
    for dcr, values in sorted(seg_by_dcr.items()):
        for (left_row, left), (right_row, right) in zip(values, values[1:]):
            if right < left:
                inversions.append({
                    "dcr": list(dcr), "previous_source_row": left_row,
                    "previous_seg_order_id": str(left), "source_row": right_row,
                    "seg_order_id": str(right),
                })
    reference_values = Counter(
        raw[raw_index["REFERENCE_DATE"]] for raw in raw_rows)
    extract_values = Counter(raw[raw_index["EXTRACT_DATE"]] for raw in raw_rows)
    return {
        "raw_source_rows_contiguous_from_2": _physical_rows_contiguous_from_2(raw_numbers),
        "normalized_source_rows_contiguous_from_2": (
            _physical_rows_contiguous_from_2(normalized_numbers)),
        "seg_order_id_non_decimal": seg_non_decimal,
        "seg_order_inversions": inversions,
        "seg_order_inversion_count": len(inversions),
        "dcr_relation_mismatches": dcr_mismatches,
        "unknown_equation_codes": dict(sorted(unknown_equation.items())),
        "known_date_overflow_domains": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(date_overflow_domains.items())
        },
        "unknown_date_domains": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(unknown_date_domains.items())
        },
        "known_numeric_overflow_or_non_digit_domains": {
            field: dict(sorted(counts.items())) for field, counts in sorted(numeric_non_digit.items())
        },
        "code_domains": {
            field: dict(sorted(counts.items())) for field, counts in sorted(code_domains.items())
        },
        "reference_date_singleton": {
            "values": {_text(key): count for key, count in reference_values.items()},
            "exact": reference_values == Counter({EXPECTED_REFERENCE_DATE: len(raw_rows)}),
        },
        "extract_date_singleton": {
            "values": {_text(key): count for key, count in extract_values.items()},
            "exact": extract_values == Counter({EXPECTED_EXTRACT_DATE: len(raw_rows)}),
        },
        "district_count": len({str(info["district"]) for info in row_info}),
        "county_count": len({str(info["county"]) for info in row_info}),
        "route_count": len({str(info["route"]) for info in row_info}),
        "district_county_route_count": len({tuple(info["dcr"]) for info in row_info}),
        "district_counts": dict(sorted(Counter(str(info["district"]) for info in row_info).items())),
        "county_counts": dict(sorted(Counter(str(info["county"]) for info in row_info).items())),
        "route_counts": dict(sorted(Counter(str(info["route"]) for info in row_info).items())),
    }


def _projection_comparison(expected: Sequence[Sequence[object]],
                           actual: Sequence[Sequence[object]]) -> dict[str, object]:
    mismatches: Counter[str] = Counter()
    examples = []
    for ordinal, (left, right) in enumerate(zip(expected, actual), 1):
        for column, (a, b) in enumerate(zip(left, right)):
            if _typed(a) != _typed(b):
                field = NORMALIZED_HEADERS[column]
                mismatches[field] += 1
                if len(examples) < 50:
                    examples.append({
                        "ordinal": ordinal, "normalized_source_row": ordinal + 1,
                        "field": field, "expected": _typed(a), "actual": _typed(b),
                    })
    expected_multiset = _multiset_digest(expected)[0]
    actual_multiset = _multiset_digest(actual)[0]
    exact = len(expected) == len(actual) and not mismatches
    return {
        "expected_rows": len(expected), "actual_rows": len(actual),
        "missing_or_extra_row_count": abs(len(expected) - len(actual)),
        "typed_cell_mismatch_count": sum(mismatches.values()),
        "typed_cell_mismatches_by_field": dict(sorted(mismatches.items())),
        "mismatch_examples": examples,
        "ordered_exact": exact,
        "multiset_exact": expected_multiset == actual_multiset,
        "expected_ordered_sha256": _ordered_digest(expected),
        "actual_ordered_sha256": _ordered_digest(actual),
        "expected_multiset_sha256": expected_multiset,
        "actual_multiset_sha256": actual_multiset,
    }


def _length_rounding_residue(projection: dict[str, object],
                             raw_rows: Sequence[Sequence[object]],
                             normalized_rows: Sequence[Sequence[object]],
                             row_info: Sequence[dict[str, object]]) -> dict[str, object]:
    """Bind the one r7 cell where binary64 formatting loses a half-tie.

    The exact OOXML scalar is Decimal 0.0135.  Decimal half-even at three
    places and the accepted D01 vendor PDF both say 000.014; r7 says 000.013.
    This is a product defect, not an oracle exception.  Classification makes
    the audit residue exhaustive while keeping ``projection_exact`` false.
    """
    ordinal = 32_564
    raw = dict(zip(RAW_HEADERS, raw_rows[ordinal - 1]))
    actual = normalized_rows[ordinal - 1][NORMALIZED_HEADERS.index("Length")]
    identity = row_info[ordinal - 1]
    expected_mismatch = [{
        "ordinal": ordinal,
        "normalized_source_row": ordinal + 1,
        "field": "Length",
        "expected": ["str", "000.014"],
        "actual": ["str", "000.013"],
    }]
    exact = (
        projection["typed_cell_mismatch_count"] == 1
        and projection["typed_cell_mismatches_by_field"] == {"Length": 1}
        and projection["mismatch_examples"] == expected_mismatch
        and raw["LENGTH"] == Decimal("0.0135")
        and _text(raw["THY_ID"]) == "77645219"
        and identity["identity"]
        == ("01", "HUM", "096", "", "R", "044.236", "", "")
        and actual == "000.013"
    )
    manifest = {
        "raw_worksheet_row": ordinal + 1,
        "raw_thy_id": _text(raw["THY_ID"]),
        "physical_identity": list(identity["identity"]),
        "raw_typed_length": _typed(raw["LENGTH"]),
        "independent_decimal_half_even_3dp": "000.014",
        "r7_normalized_length": actual,
        "accepted_pdf_member": "D01 Highway Detail_TSN.pdf",
        "accepted_pdf_page": 91,
        "accepted_pdf_length": "000.014",
        "accepted_pdf_oracle_delta_allowlist_membership": True,
        "accepted_pdf_oracle_stored_classification": (
            "one of the two LENGTH items inside the exact 443-item seven-day delta allowlist"
        ),
        "adversarial_reclassification": (
            "proven r7 raw-to-normalized rounding defect because exact raw Decimal and "
            "authoritative PDF agree on 000.014"
        ),
    }
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return {
        "exact": exact,
        "classified_cell_count": 1 if exact else 0,
        "manifest_sha256": _sha(payload),
        "manifest": manifest,
        "adjacent_allowlist_item": {
            "raw_worksheet_row": 32_564,
            "physical_identity": ["01", "HUM", "096", "", "R", "044.228", "", ""],
            "raw_ooxml_decimal": "0.0074999999999999997",
            "independent_decimal_half_even_3dp": "000.007",
            "r7_normalized_length": "000.007",
            "accepted_pdf_length": "000.008",
            "classification": (
                "not a current raw-to-r7 mismatch; remains a possible seven-day "
                "source change or PDF-side source/rounding difference"
            ),
        },
    }


def _detached_acceptance_decision(post_current: bool,
                                  stage6_family_audit_complete: bool) -> bool:
    if type(post_current) is not bool or type(stage6_family_audit_complete) is not bool:
        raise TypeError("detached acceptance inputs must be Boolean")
    return post_current and stage6_family_audit_complete


def _mutation_probes(raw_rows: Sequence[Sequence[object]],
                     projected_rows: Sequence[Sequence[object]],
                     row_info: Sequence[dict[str, object]],
                     raw_source_rows: Sequence[int],
                     normalized_source_rows: Sequence[int]) -> list[dict[str, object]]:
    probes = []

    def add(name: str, detected: bool, effect: str) -> None:
        probes.append({"name": name, "detected": bool(detected), "expected_effect": effect})

    base_ordered = _ordered_digest(projected_rows)
    base_multiset = _multiset_digest(projected_rows)[0]
    reordered = list(projected_rows)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    add("normalized row reorder",
        _ordered_digest(reordered) != base_ordered and _multiset_digest(reordered)[0] == base_multiset,
        "ordered digest changes while multiset remains exact")
    add("normalized row deletion", _multiset_digest(projected_rows[:-1])[0] != base_multiset,
        "row count and multiset digest change")
    add("normalized row insertion/duplicate",
        _multiset_digest(list(projected_rows) + [projected_rows[0]])[0] != base_multiset,
        "multiplicity digest changes")
    projected_mutation = [list(row) for row in projected_rows]
    projected_mutation[0][NORMALIZED_HEADERS.index("Length")] = "999.999"
    add("normalized projected-cell mutation", _ordered_digest(projected_mutation) != base_ordered,
        "row and per-field typed digests change")
    sidecar_mutation = [list(projected_rows[0])]
    sidecar_mutation[0][NORMALIZED_HEADERS.index("TSN County")] += "#MUT"
    add("normalized tail-sidecar mutation",
        _ordered_digest(sidecar_mutation) != _ordered_digest([projected_rows[0]]),
        "normalized county claim changes")
    header_mutation = list(NORMALIZED_HEADERS)
    header_mutation[-1] = "TSN County MUT"
    add("normalized header mutation",
        _ordered_digest([header_mutation]) != _ordered_digest([NORMALIZED_HEADERS]),
        "exact schema/header digest changes")
    raw_gap = list(raw_source_rows)
    normalized_gap = list(normalized_source_rows)
    raw_gap[len(raw_gap) // 2] += 1
    normalized_gap[len(normalized_gap) // 2] += 1
    add("raw and normalized physical row-gap mutation",
        (_physical_rows_contiguous_from_2(raw_source_rows)
         and _physical_rows_contiguous_from_2(normalized_source_rows)
         and not _physical_rows_contiguous_from_2(raw_gap)
         and not _physical_rows_contiguous_from_2(normalized_gap)),
        "the same helper used by acceptance rejects a missing physical worksheet row")

    raw_index = {name: index for index, name in enumerate(RAW_HEADERS)}
    source_values = [row[raw_index["ADT_AMT"]] for row in raw_rows]
    source_mutated = list(source_values)
    source_mutated[0] = _text(source_mutated[0]) + "#MUT"
    add("source-only ADT evidence mutation",
        _field_digest(source_mutated)["ordered_typed_sha256"]
        != _field_digest(source_values)["ordered_typed_sha256"],
        "raw evidence digest changes while declared normalized projection is blind")

    equation_row = next(i for i, row in enumerate(raw_rows) if _text(row[raw_index["E_IND"]]) == "E")
    equation_mutated = list(raw_rows[equation_row])
    equation_mutated[raw_index["E_IND"]] = None
    eq_projection, eq_info = _project_raw_row(equation_mutated)
    add("equation-claim mutation",
        eq_projection != projected_rows[equation_row]
        and eq_info["identity"] != row_info[equation_row]["identity"],
        "PS and strong physical identity both change")

    roadbed_row = next(
        i for i, row in enumerate(raw_rows)
        if _text(row[raw_index["HG"]]).upper() in {"L", "R"})
    roadbed_mutated = list(raw_rows[roadbed_row])
    old_hg = _text(roadbed_mutated[raw_index["HG"]]).upper()
    roadbed_mutated[raw_index["HG"]] = "R" if old_hg == "L" else "L"
    rb_projection, rb_info = _project_raw_row(roadbed_mutated)
    add("HG roadbed mutation",
        rb_projection != projected_rows[roadbed_row]
        and rb_info["identity"] != row_info[roadbed_row]["identity"],
        "HG, canonical Post Mile, and strong identity change")

    weak_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, info in enumerate(row_info):
        weak_groups[(str(info["route"]), str(info["canonical_postmile"]))].append(index)
    county_pair = next(
        indices for indices in weak_groups.values()
        if len({row_info[index]["county"] for index in indices}) > 1)
    left_index = county_pair[0]
    right_index = next(
        index for index in county_pair
        if row_info[index]["county"] != row_info[left_index]["county"])
    county_mutated = list(raw_rows[left_index])
    right_values = dict(zip(RAW_HEADERS, raw_rows[right_index]))
    county_mutated[raw_index["CNTY"]] = right_values["CNTY"]
    county_mutated[raw_index["DIST"]] = right_values["DIST"]
    county_mutated[raw_index["DIST_CNTY_ROUTE"]] = _expected_dcr(
        dict(zip(RAW_HEADERS, county_mutated)))
    county_projection, county_info = _project_raw_row(county_mutated)
    add("county swap inside weak route/Post-Mile collision",
        county_projection != projected_rows[left_index]
        and county_info["identity"] != row_info[left_index]["identity"],
        "district/county sidecars and physical identity prevent unsafe pairing")

    by_identity: dict[tuple[object, ...], list[int]] = defaultdict(list)
    for index, info in enumerate(row_info):
        by_identity[tuple(info["identity"])].append(index)
    duplicate_pair = next(
        (indices[0], indices[1]) for indices in by_identity.values()
        if len(indices) > 1 and projected_rows[indices[0]] != projected_rows[indices[1]])
    duplicate_reordered = list(projected_rows)
    duplicate_reordered[duplicate_pair[0]], duplicate_reordered[duplicate_pair[1]] = (
        duplicate_reordered[duplicate_pair[1]], duplicate_reordered[duplicate_pair[0]])
    add("nonidentical duplicate occurrence reorder",
        _ordered_digest(duplicate_reordered) != base_ordered
        and _multiset_digest(duplicate_reordered)[0] == base_multiset,
        "occurrence order changes even though multiplicity remains exact")
    full_identities = [tuple(info["identity"]) for info in row_info]
    add("duplicate physical-identity occurrence insertion",
        _multiset_digest(full_identities + [full_identities[0]])[0]
        != _multiset_digest(full_identities)[0],
        "physical identity multiplicity digest changes")

    typed_index = next(
        (index, column) for column in range(len(RAW_HEADERS))
        for index, row in enumerate(raw_rows) if isinstance(row[column], Decimal))
    typed_rows = list(raw_rows)
    typed_row = list(typed_rows[typed_index[0]])
    typed_row[typed_index[1]] = str(typed_row[typed_index[1]])
    add("same-text cross-type mutation",
        _row_wire(typed_row) != _row_wire(typed_rows[typed_index[0]]),
        "typed wire distinguishes Decimal from equal-looking text")
    add("numeric zero versus blank",
        _norm_num(Decimal(0)) == "0" and _norm_num(None) == "",
        "real zero remains a claim and is not folded to blank")
    add("numeric leading-zero canonicalization",
        _norm_num("003") == "3" and _norm_num("000") == "0",
        "insignificant integer padding is removed without losing zero")
    add("two-digit date 29/30 boundary",
        _date_year("29-12-31") == 2029 and _date_year("30-01-01") == 1930,
        "the explicit 30-year window is deterministic")
    malformed_dcr = list(raw_rows[0])
    malformed_dcr[raw_index["DIST_CNTY_ROUTE"]] = "00-XXX-000"
    malformed_rejected = False
    try:
        _project_raw_row(malformed_dcr)
    except ConservationError:
        malformed_rejected = True
    add("malformed DCR relational claim", malformed_rejected,
        "DIST_CNTY_ROUTE inconsistency fails closed")
    add("median width/variance composition",
        _norm_wda(Decimal(0), "Z") == "00Z" and _norm_wda(Decimal(8), "V") == "08V",
        "zero and one-digit widths remain two-digit claims with variance")
    with localcontext() as context:
        context.rounding = ROUND_DOWN
        ambient_independent = _fixed_three(Decimal("0.0135"), "LENGTH") == "000.014"
    add("Length rounding ignores ambient ROUND_DOWN",
        ambient_independent,
        "explicit ROUND_HALF_EVEN controls the projection regardless of ambient context")
    add("Length half-even boundary probes",
        (_fixed_three(Decimal("0.0125"), "LENGTH") == "000.012"
         and _fixed_three(Decimal("0.0135"), "LENGTH") == "000.014"
         and _fixed_three(Decimal("-0.0125"), "LENGTH") == "-00.012"
         and _fixed_three(Decimal("-0.0135"), "LENGTH") == "-00.014"),
        "positive and negative half-thousandth ties select the even third decimal")
    add("stable identities cannot accept an incomplete Stage 6 audit",
        (not _detached_acceptance_decision(True, False)
         and not _detached_acceptance_decision(False, True)
         and _detached_acceptance_decision(True, True)),
        "detached acceptance requires both identity stability and family-audit completion")
    return probes


def _disposition_structure_contract() -> dict[str, object]:
    allowed_kinds = {
        "projected", "composed", "relational", "source_only",
        "source_only_metadata", "projected_relational",
    }
    errors = []
    for field in RAW_HEADERS:
        disposition = FIELD_DISPOSITIONS.get(field)
        if not isinstance(disposition, dict):
            errors.append(f"{field}: disposition is not an object")
            continue
        if set(disposition) != {"kind", "normalized_targets", "role"}:
            errors.append(f"{field}: keys are {sorted(disposition)!r}")
            continue
        kind = disposition["kind"]
        targets = disposition["normalized_targets"]
        role = disposition["role"]
        if kind not in allowed_kinds:
            errors.append(f"{field}: invalid kind {kind!r}")
        if (not isinstance(targets, list)
                or any(not isinstance(target, str) for target in targets)
                or len(targets) != len(set(targets))):
            errors.append(f"{field}: targets must be a unique string list")
            targets = []
        unknown_targets = sorted(set(targets) - set(NORMALIZED_HEADERS))
        if unknown_targets:
            errors.append(f"{field}: unknown targets {unknown_targets!r}")
        should_be_empty = kind in {"relational", "source_only", "source_only_metadata"}
        if should_be_empty != (not targets):
            errors.append(f"{field}: kind {kind!r} and target cardinality disagree")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"{field}: role must be nonblank text")
    return {
        "allowed_kinds": sorted(allowed_kinds),
        "required_keys": ["kind", "normalized_targets", "role"],
        "errors": errors,
        "exact": not errors and tuple(FIELD_DISPOSITIONS) == RAW_HEADERS,
    }


def _coverage_contract() -> dict[str, object]:
    structure = _disposition_structure_contract()
    raw_declared = set(FIELD_DISPOSITIONS)
    targets = {
        target for disposition in FIELD_DISPOSITIONS.values()
        for target in disposition["normalized_targets"]
    }
    return {
        "raw_field_count": len(RAW_HEADERS),
        "declared_disposition_count": len(FIELD_DISPOSITIONS),
        "unexplained_raw_fields": sorted(set(RAW_HEADERS) - raw_declared),
        "extraneous_disposition_fields": sorted(raw_declared - set(RAW_HEADERS)),
        "unexplained_normalized_fields": sorted(set(NORMALIZED_HEADERS) - targets),
        "declared_normalized_targets": sorted(targets),
        "disposition_structure": structure,
        "exact": (
            raw_declared == set(RAW_HEADERS)
            and targets == set(NORMALIZED_HEADERS)
            and len(FIELD_DISPOSITIONS) == len(RAW_HEADERS)
            and structure["exact"]
        ),
    }


def _expected_collision_contract(census: dict[str, object]) -> dict[str, object]:
    checks = {}
    for name, expected in EXPECTED_COLLISIONS.items():
        observed = census[name]
        checks[name] = {
            "expected": expected,
            "observed": {key: observed[key] for key in expected},
            "exact": all(observed[key] == value for key, value in expected.items()),
        }
    full = census["full_with_district_and_equation"]
    checks["strong_multiplicity_pattern"] = {
        "expected": {"2": 76, "4": 1},
        "observed": {str(key): value for key, value in full[
            "duplicate_multiplicity_distribution"].items()},
        "exact": full["duplicate_multiplicity_distribution"] == {2: 76, 4: 1},
    }
    checks["strong_nonidentical_groups"] = {
        "expected": 77, "observed": full["nonidentical_duplicate_groups"],
        "exact": full["nonidentical_duplicate_groups"] == 77,
    }
    return {"checks": checks, "all_exact": all(item["exact"] for item in checks.values())}


def run(raw_path: Path, normalized_path: Path) -> dict[str, object]:
    if set(FIELD_DISPOSITIONS) != set(RAW_HEADERS):
        raise ConservationError("all and only the 56 raw fields require dispositions")
    disposition_structure = _disposition_structure_contract()
    if not disposition_structure["exact"]:
        raise ConservationError(
            f"field disposition structure is invalid: {disposition_structure['errors']!r}")
    if normalized_path.resolve() != NORMALIZED_DEFAULT.resolve():
        raise ConservationError(
            "Highway Detail Stage 6 accepts only the exact coherent r7 normalized path")
    raw_columns = tuple(
        ColumnSpec(header, DATE if header in {"REFERENCE_DATE", "EXTRACT_DATE"} else SCALAR)
        for header in RAW_HEADERS
    )
    raw_spec = SheetSpec(RAW_BINDING["sheet"], raw_columns, exact_schema=True)
    normalized_spec = SheetSpec(
        NORMALIZED_R7_BINDING["sheet"],
        tuple(ColumnSpec(header, SCALAR) for header in NORMALIZED_HEADERS),
        exact_schema=True,
    )
    limits = XlsxLimits(max_xml_events=25_000_000)
    code_initial = _capture_code_identities()
    gate_execution = _execute_reader_gate(code_initial["reader_mutation_gate"])
    raw_initial = _capture_exact_identity(raw_path, RAW_BINDING, "raw Highway Detail")
    normalized_initial = _capture_exact_identity(
        normalized_path, NORMALIZED_R7_BINDING, "normalized Highway Detail r7")
    sidecar_initial, sidecar_document = _capture_exact_json(
        R7_SIDECAR, NORMALIZED_R7_SIDECAR_BINDING,
        "accepted r7 Highway Detail outcome sidecar")
    witness_initial, witness_document = _capture_exact_json(
        R7_RESULT, PROVENANCE_BINDINGS["accepted_r7_result"],
        "accepted r7 lifecycle witness")
    pdf_oracle_initial, pdf_oracle_document = _capture_exact_json(
        PDF_ORACLE_RESULT, PROVENANCE_BINDINGS["accepted_highway_detail_pdf_oracle"],
        "accepted Highway Detail PDF oracle")
    initial_identities = {
        "raw": raw_initial,
        "normalized": normalized_initial,
        "normalized_outcome_sidecar": sidecar_initial,
        "r7_lifecycle_witness": witness_initial,
        "accepted_pdf_oracle": pdf_oracle_initial,
        **code_initial,
    }
    r7_witness_contract = _r7_witness_contract(
        witness_document, sidecar_document, pdf_oracle_document)

    raw_topology = _workbook_topology(raw_path)
    raw_sheet = read_sheet(raw_path, raw_spec, limits=limits)
    _require_binding(raw_sheet, raw_topology, RAW_BINDING, "raw Highway Detail")
    normalized_topology = _workbook_topology(normalized_path)
    normalized_sheet = read_sheet(normalized_path, normalized_spec, limits=limits)
    _require_binding(
        normalized_sheet, normalized_topology, NORMALIZED_R7_BINDING,
        "normalized Highway Detail")

    raw_rows = [tuple(row.values) for row in raw_sheet.rows]
    normalized_rows = [tuple(row.values) for row in normalized_sheet.rows]
    if len(raw_rows) != RAW_BINDING["rows"]:
        raise ConservationError(
            f"raw row count {len(raw_rows)} != bound {RAW_BINDING['rows']}")
    if len(normalized_rows) != NORMALIZED_R7_BINDING["rows"]:
        raise ConservationError(
            f"normalized row count {len(normalized_rows)} != bound "
            f"{NORMALIZED_R7_BINDING['rows']}")
    blank_raw = [row.source_row for row in raw_sheet.rows
                 if not any(value not in (None, "") for value in row.values)]
    blank_normalized = [row.source_row for row in normalized_sheet.rows
                        if not any(value not in (None, "") for value in row.values)]
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
    length_rounding_residue = _length_rounding_residue(
        projection, raw_rows, normalized_rows, row_info)
    collisions = _collision_census(raw_rows, row_info)
    collision_contract = _expected_collision_contract(collisions)
    order_anomalies = _order_and_anomaly_census(
        raw_sheet, normalized_sheet, raw_rows, row_info)
    mutations = _mutation_probes(
        raw_rows, projected_rows, row_info,
        [row.source_row for row in raw_sheet.rows],
        [row.source_row for row in normalized_sheet.rows])
    coverage = _coverage_contract()
    raw_index = {name: index for index, name in enumerate(RAW_HEADERS)}
    evidence_nonblank = {
        field: sum(_text(row[raw_index[field]]) != "" for row in raw_rows)
        for field in EVIDENCE_OMISSIONS
    }

    blocking_findings = [{
        "id": "HD-S6-001",
        "severity": "P1",
        "status": "open",
        "title": "Normalized Highway Detail omits authoritative Report View/evidence facts",
        "fields": list(EVIDENCE_OMISSIONS),
        "evidence": {
            "nonblank_source_counts": evidence_nonblank,
            "raw_field_typed_digests": {
                field: _field_digest([row[raw_index[field]] for row in raw_rows])
                for field in EVIDENCE_OMISSIONS
            },
            "dcr_claim_rows": len(raw_rows),
            "dcr_is_exactly_reconstructible_from_retained_claims": not order_anomalies[
                "dcr_relation_mismatches"],
        },
        "requirement": (
            "Retain the nine printed evidence/change-flag fields in normalized bytes "
            "or an equally immutable source-bound representation, and make the canonical "
            "Matrix one-sided adapter carry DCR plus these facts into Report View/evidence."
        ),
    }]
    blocking_findings.append({
        "id": "HD-S6-002",
        "severity": "P1",
        "status": "open",
        "title": "r7 normalizer rounds exact half-thousandth Length incorrectly",
        "evidence": length_rounding_residue,
        "requirement": (
            "Round the exact XLSX decimal claim without a lossy binary64 conversion, "
            "rebuild Highway Detail, and correct the accepted PDF-oracle allowlist so "
            "the proven 000.014 fact is not mislabeled as a seven-day source delta."
        ),
    })
    blocking_findings.append({
        "id": "HD-S6-003",
        "severity": "P1",
        "status": "open",
        "title": "Normalized Highway Detail omits authoritative snapshot metadata",
        "fields": ["REFERENCE_DATE", "EXTRACT_DATE"],
        "evidence": {
            "typed_field_digests": {
                field: _field_digest([row[raw_index[field]] for row in raw_rows])
                for field in ("REFERENCE_DATE", "EXTRACT_DATE")
            },
            "reference_date_singleton": order_anomalies["reference_date_singleton"],
            "extract_date_singleton": order_anomalies["extract_date_singleton"],
            "accepted_pdf_mapping": r7_witness_contract[
                "accepted_pdf_metadata_mapping"],
            "accepted_source_snapshot_relation": {
                "xlsx_reference_date": "2025-09-08",
                "xlsx_extract_date": "2025-09-15",
                "pdf_reference_date": "2025-09-15",
                "pdf_report_date": "2025-09-15",
            },
        },
        "impact": (
            "The normalized artifact cannot independently prove which authoritative "
            "reference/extract snapshot supplied its rows or the exact seven-day relation "
            "to the accepted district PDF evidence."
        ),
        "requirement": (
            "Retain both typed snapshot dates in normalized bytes or an equally immutable "
            "artifact-bound representation consumed by comparison/evidence provenance."
        ),
    })
    review_findings = [{
        "id": "HD-S6-004",
        "severity": "review",
        "status": "explicit_source_only_and_relational_disposition",
        "title": "Database, helper, and ordering fields remain audited",
        "fields": [
            "THY_ID", "BREAK_DESC", "SEG_ORDER_ID",
        ],
        "requirement": (
            "Keep typed raw digests, DCR relation, and within-DCR order checks permanent "
            "even if these database/helper fields remain non-visible."
        ),
    }]

    # Every expensive source-derived digest is complete before the acceptance
    # identities below.  No live JSON is reparsed: the coherent r7/sidecar/PDF
    # documents above came only from their initial immutable byte captures.
    raw_digests = _dataset_digests(RAW_HEADERS, raw_rows)
    projected_digests = _dataset_digests(NORMALIZED_HEADERS, projected_rows)
    normalized_digests = _dataset_digests(NORMALIZED_HEADERS, normalized_rows)
    acceptance_identities = _capture_tracked_identities(raw_path, normalized_path)
    tracked_generation_current = acceptance_identities == initial_identities
    final_identities_current = (
        tracked_generation_current
        and acceptance_identities["raw"] == raw_sheet.pre_identity
        and acceptance_identities["normalized"] == normalized_sheet.pre_identity)
    projection_exact = projection["ordered_exact"] and projection["multiset_exact"]
    unexplained_projection_residue = (
        projection["typed_cell_mismatch_count"]
        - length_rounding_residue["classified_cell_count"])
    audit_invariants = {
        "source_bindings_exact": (
            raw_initial == raw_sheet.pre_identity
            and normalized_initial == normalized_sheet.pre_identity),
        "workbook_topologies_exact": True,
        "formula_and_error_cells_absent": (
            raw_topology["formula_cell_count"] == 0
            and raw_topology["error_cell_count"] == 0
            and normalized_topology["formula_cell_count"] == 0
            and normalized_topology["error_cell_count"] == 0),
        "final_source_identities_current": final_identities_current,
        "all_tracked_identities_current_after_digests": tracked_generation_current,
        "reader_mutation_gate_executed_hash_bound_and_passed": (
            gate_execution["exit_code"] == 0
            and gate_execution["gate_source_identity"]
            == _identity_dict(code_initial["reader_mutation_gate"])
            and bool(gate_execution["stdout_utf8_sha256"])),
        "accepted_r7_result_and_sidecar_contract_exact": r7_witness_contract["all_exact"],
        "raw_schema_exact": raw_sheet.headers == RAW_HEADERS,
        "normalized_schema_exact": normalized_sheet.headers == NORMALIZED_HEADERS,
        "raw_row_count_exact": len(raw_rows) == RAW_BINDING["rows"],
        "normalized_row_count_exact": (
            len(normalized_rows) == NORMALIZED_R7_BINDING["rows"]),
        "all_raw_and_normalized_fields_explained": coverage["exact"],
        "field_disposition_kind_target_role_structure_exact": (
            disposition_structure["exact"]),
        "raw_and_normalized_physical_rows_contiguous": (
            order_anomalies["raw_source_rows_contiguous_from_2"]
            and order_anomalies["normalized_source_rows_contiguous_from_2"]),
        "projection_residue_fully_classified": (
            length_rounding_residue["exact"] and unexplained_projection_residue == 0),
        "strong_and_weak_collision_censuses_exact": collision_contract["all_exact"],
        "dcr_relation_exact": not order_anomalies["dcr_relation_mismatches"],
        "seg_order_id_typed": not order_anomalies["seg_order_id_non_decimal"],
        "seg_order_nondecreasing_within_every_dcr": (
            order_anomalies["seg_order_inversion_count"] == 0),
        "reference_and_extract_date_singletons_exact": (
            order_anomalies["reference_date_singleton"]["exact"]
            and order_anomalies["extract_date_singleton"]["exact"]),
        "equation_domain_exact": not order_anomalies["unknown_equation_codes"],
        "date_domains_fully_classified": not order_anomalies["unknown_date_domains"],
        "semantic_mutation_probes_all_detected": all(probe["detected"] for probe in mutations),
    }
    audit_complete = all(audit_invariants.values())
    normalized_full_conservation = audit_complete and projection_exact and not blocking_findings
    return {
        "schema_version": 2,
        "audit": "Stage 6 Highway Detail raw-to-normalized conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_comparators_imported": False,
            "application_evidence_adapters_imported": False,
            "application_family_constants_imported": False,
            "reader": "build/phase3_xlsx_stream.py stdlib OOXML reader",
            "permanent_reader_mutation_gate": "build/check_phase3_xlsx_stream.py",
            "structural_mutations_enforced_by_reader_and_binding": [
                "source SHA/size", "sheet name/visibility", "exact header order",
                "extra/duplicate header", "formula cell", "error cell",
                "preserved-mtime replacement", "path/descriptor drift",
                "pre/post handle hash disagreement",
            ],
        },
        "bindings": {
            "raw": RAW_BINDING,
            "normalized": NORMALIZED_R7_BINDING,
            "normalized_outcome_sidecar": NORMALIZED_R7_SIDECAR_BINDING,
            "r7_lifecycle_witness": {
                key: value for key, value in PROVENANCE_BINDINGS[
                    "accepted_r7_result"].items() if key != "path"},
            "accepted_pdf_oracle": {
                key: value for key, value in PROVENANCE_BINDINGS[
                    "accepted_highway_detail_pdf_oracle"].items() if key != "path"},
        },
        "provenance": {
            "initial": {
                label: _identity_dict(identity)
                for label, identity in initial_identities.items()
            },
            "acceptance_after_all_digests": {
                label: _identity_dict(identity)
                for label, identity in acceptance_identities.items()
            },
            "all_exactly_current": tracked_generation_current,
            "reader_mutation_gate_execution": gate_execution,
            "accepted_r7_witness_contract": r7_witness_contract,
        },
        "source_identity": {
            "raw": {
                "path": str(raw_path.resolve()), "topology_capture": raw_topology,
                "worksheet_pre_read": _identity_dict(raw_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(raw_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(
                    acceptance_identities["raw"]),
            },
            "normalized": {
                "path": str(normalized_path.resolve()),
                "topology_capture": normalized_topology,
                "worksheet_pre_read": _identity_dict(normalized_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(normalized_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(
                    acceptance_identities["normalized"]),
            },
            "normalized_outcome_sidecar": {
                "path": str(R7_SIDECAR.resolve()),
                "initial_immutable_json_capture": _identity_dict(sidecar_initial),
                "acceptance_revalidation": _identity_dict(
                    acceptance_identities["normalized_outcome_sidecar"]),
            },
            "r7_lifecycle_witness": {
                "path": str(R7_RESULT.resolve()),
                "initial_immutable_json_capture": _identity_dict(witness_initial),
                "acceptance_revalidation": _identity_dict(
                    acceptance_identities["r7_lifecycle_witness"]),
            },
            "accepted_pdf_oracle": {
                "path": str(PDF_ORACLE_RESULT.resolve()),
                "initial_immutable_json_capture": _identity_dict(pdf_oracle_initial),
                "acceptance_revalidation": _identity_dict(
                    acceptance_identities["accepted_pdf_oracle"]),
            },
        },
        "field_dispositions": FIELD_DISPOSITIONS,
        "field_coverage": coverage,
        "raw_digests": raw_digests,
        "independently_projected_digests": projected_digests,
        "normalized_digests": normalized_digests,
        "projection_comparison": projection,
        "classified_projection_residue": {
            "exact_length_rounding_defect": length_rounding_residue,
        },
        "unexplained_projection_residue_count": unexplained_projection_residue,
        "identity_and_collision_census": collisions,
        "frozen_collision_contract": collision_contract,
        "order_and_anomaly_census": order_anomalies,
        "semantic_mutation_probes": mutations,
        "findings": {"blocking": blocking_findings, "review": review_findings},
        "audit_invariants": audit_invariants,
        "projection_exact": projection_exact,
        "stage6_family_audit_complete": audit_complete,
        "normalized_full_conservation": normalized_full_conservation,
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--normalized", type=Path, default=NORMALIZED_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument(
        "--allow-open-findings", action="store_true",
        help="exit zero when the audit is complete but documented product findings remain")
    return parser.parse_args(argv)


def _write_result(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    acceptance_path = args.output.with_suffix(args.output.suffix + ".acceptance.json")
    try:
        result = run(args.raw, args.normalized)
        _write_result(args.output, result)
        result_capture = capture_file_bytes(args.output)
        post_identities = _capture_tracked_identities(args.raw, args.normalized)
        expected_identities = result["provenance"]["acceptance_after_all_digests"]
        post_current = all(
            _identity_dict(identity) == expected_identities[label]
            for label, identity in post_identities.items())
        detached_accepted = _detached_acceptance_decision(
            post_current, result["stage6_family_audit_complete"])
        acceptance = {
            "schema_version": 1,
            "accepted": detached_accepted,
            "result": {
                "path": str(args.output.resolve()),
                "bytes": result_capture.identity.size,
                "sha256": result_capture.identity.sha256,
            },
            "post_result_write_revalidation": post_current,
            "stage6_family_audit_complete": result["stage6_family_audit_complete"],
            "projection_exact": result["projection_exact"],
            "normalized_full_conservation": result["normalized_full_conservation"],
            "post_result_write_identities": {
                label: _identity_dict(identity)
                for label, identity in post_identities.items()
            },
        }
        _write_result(acceptance_path, acceptance)
        final_result = capture_file_identity(args.output)
        final_identities = _capture_tracked_identities(args.raw, args.normalized)
        final_current = (
            final_result == result_capture.identity
            and final_identities == post_identities)
        if not post_current or not final_current:
            rejection = dict(acceptance)
            rejection["accepted"] = False
            rejection["post_result_write_revalidation"] = False
            rejection["final_exit_gate_current"] = final_current
            rejection["final_exit_gate_identities"] = {
                label: _identity_dict(identity)
                for label, identity in final_identities.items()
            }
            _write_result(acceptance_path, rejection)
            raise ConservationError(
                "tracked identity changed after result/acceptance write")
    except Exception as exc:
        failure = {
            "schema_version": 2,
            "audit": "Stage 6 Highway Detail raw-to-normalized conservation",
            "projection_exact": False,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        _write_result(args.output, failure)
        failure_capture = capture_file_identity(args.output)
        _write_result(acceptance_path, {
            "schema_version": 1,
            "accepted": False,
            "result": {
                "path": str(args.output.resolve()),
                "bytes": failure_capture.size,
                "sha256": failure_capture.sha256,
            },
            "post_result_write_revalidation": False,
            "stage6_family_audit_complete": False,
            "projection_exact": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })
        sys.stdout.write(json.dumps(failure, ensure_ascii=False) + "\n")
        return 2

    summary = {
        "output": str(args.output),
        "projection_exact": result["projection_exact"],
        "stage6_family_audit_complete": result["stage6_family_audit_complete"],
        "normalized_full_conservation": result["normalized_full_conservation"],
        "blocking_findings": len(result["findings"]["blocking"]),
        "post_result_write_revalidation": True,
        "acceptance_record": str(acceptance_path),
        "result_sha256": result_capture.identity.sha256,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False) + "\n")
    if not result["stage6_family_audit_complete"]:
        return 2
    if not result["normalized_full_conservation"] and not args.allow_open_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

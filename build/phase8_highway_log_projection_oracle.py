#!/usr/bin/env python3
"""Independent Stage-8 Highway Log projection comparison oracle.

This is audit code, not product code.  It reads the three frozen consolidated
workbooks through the generic Phase-3 OOXML stream reader and independently
transcribes only the Highway Log projection semantics needed for comparison:

* load-time control-whitespace replacement followed by Excel-style ASCII TRIM;
* the weak Route + roadbed-aware Location key;
* column-agnostic dynamic ``+``-run nonassertion;
* exact narrow Med-Wid canonicalization; and
* exact duplicate pairing through Phase 3's lexicographic assignment primitive.

No module below ``scripts/`` is imported.  The result is a canonical JSON audit
record written once to a caller-supplied, already-absent ``--output`` path.  A
full ``--preflight`` performs the same reads and comparisons without writing.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping, Sequence


BUILD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BUILD_ROOT.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
sys.path.insert(0, str(BUILD_ROOT))

from phase3_independent_oracle import (  # noqa: E402
    exact_lexicographic_assignment,
)
from phase3_xlsx_stream import (  # noqa: E402
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    XlsxLimits,
    XlsxStreamError,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_ROOT = VISUAL_ROOT / "phase8_highway_log_product_sources_r1"
EXCEL_INPUT = SOURCE_ROOT / "current_tsmis_excel_consolidated.xlsx"
PDF_INPUT = SOURCE_ROOT / "current_tsmis_pdf_consolidated.xlsx"
TSN_INPUT = (
    VISUAL_ROOT / "phase4_tsn_rebaseline" / "raw-2026-07-12-r7"
    / "highway_log" / "consolidated" / "tsn_highway_log_consolidated.xlsx"
)
STAGE6_ROOT = VISUAL_ROOT / "phase6_tsn_conservation"
STAGE6_RESULT = STAGE6_ROOT / "highway_log_conservation_r1.json"
STAGE6_ACCEPTANCE = Path(str(STAGE6_RESULT) + ".acceptance.json")

INPUT_BINDINGS = {
    "excel": {
        "path": EXCEL_INPUT,
        "bytes": 5_735_685,
        "sha256": "329ccf68caf0c476d9360cb69dd28c0ab78a588d0e9bd9c816d5b484444fd660",
    },
    "pdf": {
        "path": PDF_INPUT,
        "bytes": 5_684_466,
        "sha256": "17c04bb7400eded5c7b372d4ca87728735f8481fd37394c592e7dd0180f0333d",
    },
    "tsn": {
        "path": TSN_INPUT,
        "bytes": 6_663_062,
        "sha256": "fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa",
    },
}
STAGE6_BINDINGS = {
    "result": {
        "path": STAGE6_RESULT,
        "bytes": 10_879_397,
        "sha256": "f55892f3b0a0813a370aca736d56850a2eec34ab5add64a54dcaf7e25388fff4",
    },
    "acceptance": {
        "path": STAGE6_ACCEPTANCE,
        "bytes": 6_502,
        "sha256": "012f7ace10495e982aa6bb03e5c1329aef5fd6ab9d9b13d00bbca09c65c0bb61",
    },
}

HEADERS = (
    "Route", "Location", "Length (MI) [MI]", "NA [N/A]", "Cnty Odom",
    "City", "RU [R/U]", "SPD", "TER", "HG [H/G]", "AC [A/C]",
    "LB ST [LB T]", "LB # Lns [LB Lns]", "LB SF [LB F]",
    "LB OT-SH Total [LB OT]", "LB OT-SH Treated [LB TR]",
    "LB T-W Wid [LB T-W]", "LB IN-SH Total [LB IN]",
    "LB IN-SH Treated [LB SH]", "Med TY/CL/BA [Med TCB]",
    "Med Wid/Var [Med Wid]", "RB ST [RB T]", "RB # Lns [RB Lns]",
    "RB SF [RB F]", "RB IN-SH Total [RB IN]",
    "RB IN-SH Treated [RB SH]", "RB T-W Wid [RB T-W]",
    "RB OT-SH Total [RB OT]", "RB OT-SH Treated [RB SH]",
    "Description", "Date of Rec", "Sig Chg. Date",
)
SHEET_NAME = "Highway Log"
LOCATION_INDEX = HEADERS.index("Location")
MED_WID_INDEX = HEADERS.index("Med Wid/Var [Med Wid]")
COMPARED_INDICES = tuple(
    index for index in range(2, len(HEADERS))
)
COMPARED_FIELDS = tuple(HEADERS[index] for index in COMPARED_INDICES)
LEFT_BLOCK_INDICES = tuple(HEADERS.index(name) for name in (
    "LB ST [LB T]", "LB # Lns [LB Lns]", "LB SF [LB F]",
    "LB OT-SH Total [LB OT]", "LB OT-SH Treated [LB TR]",
    "LB T-W Wid [LB T-W]", "LB IN-SH Total [LB IN]",
    "LB IN-SH Treated [LB SH]",
))
RIGHT_BLOCK_INDICES = tuple(HEADERS.index(name) for name in (
    "RB ST [RB T]", "RB # Lns [RB Lns]", "RB SF [RB F]",
    "RB IN-SH Total [RB IN]", "RB IN-SH Treated [RB SH]",
    "RB T-W Wid [RB T-W]", "RB OT-SH Total [RB OT]",
    "RB OT-SH Treated [RB SH]",
))
SHEET_SPEC = SheetSpec(
    SHEET_NAME,
    tuple(ColumnSpec(header) for header in HEADERS),
    exact_schema=True,
)

EXPECTED_STAGE6_FLAGS = {
    "accepted": True,
    "normalized_full_conservation": False,
    "projection_exact": True,
    "stage6_family_audit_complete": True,
    "terminal_status": "accepted",
    "unexplained_projection_residue_count": 0,
}
EXPECTED_COLLISION_CENSUS = {
    "full_physical_occurrence_ordinal": {
        "distinct_keys": 60_083,
        "duplicate_group_count": 0,
        "max_multiplicity": 1,
        "multiplicity_histogram": {},
        "multiset_key_sha256": "be85caede2591df1133ce45d912d63b0e1f01f36fd4d7e3c0f1e74a3a2ce2b5e",
        "ordered_key_sha256": "4ae7493d3418fd91fbaec6ddb2d9d389ede3c931dab3323c96a9c591d3f1f73a",
        "row_count": 60_083,
        "rows_in_duplicate_groups": 0,
    },
    "full_physical_owner_location_roadbed": {
        "distinct_keys": 60_004,
        "duplicate_group_count": 77,
        "max_multiplicity": 4,
        "multiplicity_histogram": {"2": 76, "4": 1},
        "multiset_key_sha256": "a72f003b5c32977a8e3c73abeb9e0321cc1135a36cf31197f8fd1155e38bd4b8",
        "ordered_key_sha256": "02ad55bad41cdf2528b397a0d6697be2fc7de4f5d47914d03e387cfef25c5f41",
        "row_count": 60_083,
        "rows_in_duplicate_groups": 156,
    },
    "route_plus_printed_location": {
        "distinct_keys": 59_156,
        "duplicate_group_count": 798,
        "max_multiplicity": 10,
        "multiplicity_histogram": {
            "2": 728, "3": 51, "4": 6, "5": 3, "6": 3,
            "7": 1, "8": 3, "9": 2, "10": 1,
        },
        "multiset_key_sha256": "9f605c4f4da2a4e0d58e9033bd266ef4f33d157d9584b87e798224e509e1b05f",
        "ordered_key_sha256": "b67659c21eb03f06191be566b1fa94ef446b4e10374601ffe9f1ce6f26410b65",
        "row_count": 60_083,
        "rows_in_duplicate_groups": 1_725,
    },
    "route_plus_printed_location_plus_roadbed": {
        "distinct_keys": 59_482,
        "duplicate_group_count": 508,
        "max_multiplicity": 10,
        "multiplicity_histogram": {
            "2": 471, "3": 19, "4": 6, "5": 3, "6": 2,
            "7": 1, "8": 3, "9": 2, "10": 1,
        },
        "multiset_key_sha256": "6f407bd53a11e79d799fe9a0676c40a463f184c29d3619bfe41cfc7658920585",
        "ordered_key_sha256": "7124b786535dc76b048da59a28353c52741a65d815f6f03d1b2a586b53b1e912",
        "row_count": 60_083,
        "rows_in_duplicate_groups": 1_109,
    },
}

KNOWN_PRODUCT_FINDINGS = (
    "CMP-AUD-045", "CMP-AUD-047", "CMP-AUD-048", "CMP-AUD-049",
    "CMP-AUD-050", "CMP-AUD-066", "CMP-AUD-067", "CMP-AUD-157",
)
MAX_EXACT_MATRIX_CELLS = 100_000
_CONTROL_WHITESPACE = re.compile(r"[\t\n\r\f\v]")
_ASCII_SPACE_RUN = re.compile(r" +")
_MED_WID = re.compile(r"([0-9]+)(?:\.([0-9]+))?(.)?")
_MED_WID_SUFFIXES = frozenset(
    chr(code) for code in range(0x21, 0x7F)
    if chr(code) not in "0123456789."
)
DIGEST_SERIALIZATION = (
    "sha256 over each record as u64be(canonical-json byte length) followed by "
    "UTF-8 canonical JSON; records remain in the declared order"
)


class ProjectionAuditError(RuntimeError):
    """A frozen input, accepted chain, or projection invariant drifted."""


@dataclass(frozen=True)
class AuditRow:
    ordinal: int
    source_row: int
    values: tuple[object, ...]
    row_sha256: str


@dataclass(frozen=True)
class Dataset:
    label: str
    identity: FileIdentity
    rows: tuple[AuditRow, ...]
    summary: Mapping[str, object]


class SequenceDigest:
    """Streaming digest for a complete, ordered canonical-record manifest."""

    def __init__(self) -> None:
        self._digest = hashlib.sha256()
        self.count = 0

    def add(self, record: object) -> None:
        payload = _canonical(record)
        self._digest.update(len(payload).to_bytes(8, "big"))
        self._digest.update(payload)
        self.count += 1

    def result(self) -> dict[str, object]:
        return {"records": self.count, "sha256": self._digest.hexdigest()}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _json_bytes(value: object) -> bytes:
    return _canonical(value) + b"\n"


def _sha_object(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest_records(records: Iterable[object]) -> dict[str, object]:
    digest = SequenceDigest()
    for record in records:
        digest.add(record)
    return digest.result()


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ProjectionAuditError("non-finite decimal in workbook")
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in ("", "+0", "-0") else rendered


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null", None]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, Decimal):
        return ["decimal", _decimal_text(value)]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectionAuditError("non-finite float in workbook")
        return ["float", repr(value)]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat(sep=" ")]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat()]
    raise ProjectionAuditError(f"unsupported workbook scalar: {type(value).__name__}")


def _identity(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _require_bound(identity: FileIdentity, binding: Mapping[str, object],
                   label: str) -> None:
    if (identity.size, identity.sha256) != (
            binding["bytes"], binding["sha256"]):
        raise ProjectionAuditError(
            f"{label} identity drift: size={identity.size}, sha256={identity.sha256}")


def _capture_json(label: str, binding: Mapping[str, object]) -> tuple[
        FileIdentity, dict[str, object]]:
    capture = capture_file_bytes(
        binding["path"], max_bytes=int(binding["bytes"]))
    _require_bound(capture.identity, binding, label)
    try:
        document = json.loads(capture.payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionAuditError(f"{label} is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ProjectionAuditError(f"{label} JSON root is not an object")
    return capture.identity, document


def _validate_stage6() -> tuple[dict[str, object], dict[str, FileIdentity]]:
    result_identity, result = _capture_json(
        "Stage-6 Highway Log result", STAGE6_BINDINGS["result"])
    acceptance_identity, acceptance = _capture_json(
        "Stage-6 Highway Log acceptance", STAGE6_BINDINGS["acceptance"])

    observed_flags = {key: result.get(key) for key in EXPECTED_STAGE6_FLAGS}
    if observed_flags != EXPECTED_STAGE6_FLAGS or result.get("failed_invariants") != []:
        raise ProjectionAuditError(
            f"Stage-6 result is not its accepted red-state record: {observed_flags}")
    census = result.get("identity_and_collision_census")
    if (result.get("identity_and_collision_census_exact") is not True
            or census != EXPECTED_COLLISION_CENSUS):
        raise ProjectionAuditError("Stage-6 collision census drifted")

    if acceptance.get("decision") != "accepted_stage6_family_audit":
        raise ProjectionAuditError("Stage-6 detached decision is not accepted")
    if acceptance.get("required_result_flags") != EXPECTED_STAGE6_FLAGS:
        raise ProjectionAuditError("Stage-6 detached required flags drifted")
    tracked = acceptance.get("tracked_identities")
    if not isinstance(tracked, dict):
        raise ProjectionAuditError("Stage-6 acceptance lacks tracked identities")
    for key, binding in (
            ("result", STAGE6_BINDINGS["result"]),
            ("normalized", INPUT_BINDINGS["tsn"])):
        observed = tracked.get(key)
        if not isinstance(observed, dict) or (
                observed.get("size"), observed.get("sha256")) != (
                    binding["bytes"], binding["sha256"]):
            raise ProjectionAuditError(
                f"Stage-6 acceptance {key} binding drifted: {observed!r}")

    product_findings = result.get("findings", {}).get("product")
    if not isinstance(product_findings, list):
        raise ProjectionAuditError("Stage-6 product findings are missing")
    return ({
        "result_identity": _identity(result_identity),
        "acceptance_identity": _identity(acceptance_identity),
        "accepted_flags": observed_flags,
        "decision": acceptance["decision"],
        "collision_census": census,
        "collision_census_sha256": _sha_object(census),
        "product_findings": product_findings,
    }, {"result": result_identity, "acceptance": acceptance_identity})


def _load_normalize(value: object) -> object:
    """Independent transcription of the Highway Log input-load normalizer."""
    if type(value) is bool:
        normalized: object = "TRUE" if value else "FALSE"
    elif isinstance(value, datetime):
        normalized = (value.date().isoformat()
                      if (value.hour, value.minute, value.second, value.microsecond)
                      == (0, 0, 0, 0) else value.isoformat(sep=" "))
    elif isinstance(value, date):
        normalized = value.isoformat()
    elif isinstance(value, time):
        normalized = value.isoformat()
    else:
        normalized = value
    return (_CONTROL_WHITESPACE.sub(" ", normalized)
            if isinstance(normalized, str) else normalized)


def _row_has_data(values: Sequence[object]) -> bool:
    return any(value is not None and str(value).strip() != "" for value in values)


def _xlsx_limits() -> XlsxLimits:
    return XlsxLimits(
        max_source_bytes=16 * 1024 * 1024,
        max_xml_events=20_000_000,
    )


def _read_dataset(label: str) -> Dataset:
    binding = INPUT_BINDINGS[label]
    sheet = read_sheet(binding["path"], SHEET_SPEC, limits=_xlsx_limits())
    _require_bound(sheet.post_identity, binding, f"{label} workbook")
    if sheet.pre_identity != sheet.post_identity:
        raise ProjectionAuditError(f"{label} workbook changed across stream read")

    raw_binding_digest = SequenceDigest()
    raw_content_digest = SequenceDigest()
    normalized_binding_digest = SequenceDigest()
    normalized_content_digest = SequenceDigest()
    source_row_digest = SequenceDigest()
    raw_hashes: list[str] = []
    normalized_hashes: list[str] = []
    rows: list[AuditRow] = []
    filtered_blank_rows = 0
    all_string_or_null = True

    for streamed in sheet.rows:
        raw_typed = [_typed(value) for value in streamed.values]
        raw_hash = _sha_object(raw_typed)
        raw_hashes.append(raw_hash)
        raw_content_digest.add(raw_typed)
        raw_binding_digest.add([streamed.source_row, raw_hash])
        if not _row_has_data(streamed.values):
            filtered_blank_rows += 1
            continue
        values = tuple(_load_normalize(value) for value in streamed.values)
        if len(values) != len(HEADERS):
            raise ProjectionAuditError(f"{label} row width drifted")
        all_string_or_null = all_string_or_null and all(
            value is None or isinstance(value, str) for value in values)
        normalized_typed = [_typed(value) for value in values]
        row_hash = _sha_object(normalized_typed)
        normalized_hashes.append(row_hash)
        normalized_content_digest.add(normalized_typed)
        normalized_binding_digest.add([streamed.source_row, row_hash])
        source_row_digest.add(streamed.source_row)
        rows.append(AuditRow(
            ordinal=len(rows), source_row=streamed.source_row,
            values=values, row_sha256=row_hash,
        ))

    if not all_string_or_null:
        raise ProjectionAuditError(
            f"{label} frozen projection is no longer all string-or-null")
    summary = {
        "binding": {
            "path": str(Path(binding["path"]).resolve()),
            "bytes": binding["bytes"], "sha256": binding["sha256"],
        },
        "observed_identity": _identity(sheet.post_identity),
        "sheet": SHEET_NAME,
        "headers": list(HEADERS),
        "headers_sha256": _sha_object(list(HEADERS)),
        "streamed_data_rows": len(sheet.rows),
        "loaded_nonblank_rows": len(rows),
        "filtered_blank_rows": filtered_blank_rows,
        "all_loaded_cells_string_or_null": all_string_or_null,
        "digests": {
            "serialization": DIGEST_SERIALIZATION,
            "raw_row_content_ordered": raw_content_digest.result(),
            "raw_source_row_binding_ordered": raw_binding_digest.result(),
            "raw_row_content_multiset": _digest_records(sorted(raw_hashes)),
            "loaded_row_content_ordered": normalized_content_digest.result(),
            "loaded_source_row_binding_ordered": normalized_binding_digest.result(),
            "loaded_row_content_multiset": _digest_records(
                sorted(normalized_hashes)),
            "loaded_source_row_numbers": source_row_digest.result(),
        },
    }
    return Dataset(label, sheet.post_identity, tuple(rows), summary)


def _ascii_trim(value: object) -> str:
    """Excel TRIM's ASCII-space behavior after load normalization."""
    if value is None:
        return ""
    if type(value) is bool:
        value = "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return _ASCII_SPACE_RUN.sub(" ", str(value)).strip(" ")


def _key_ditto(value: object) -> bool:
    """Roadbed-key ditto rule: the source helper's Python-strip convention."""
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and set(text) == {"+"}


def _dynamic_ditto(value: object) -> bool:
    """Compared-cell ditto rule: already-loaded value plus ASCII TRIM."""
    text = _ascii_trim(value)
    return bool(text) and set(text) == {"+"}


def _roadbed_tag(values: Sequence[object]) -> str:
    left = sum(_key_ditto(values[index]) for index in LEFT_BLOCK_INDICES)
    right = sum(_key_ditto(values[index]) for index in RIGHT_BLOCK_INDICES)
    if left and not right:
        return "R"
    if right and not left:
        return "L"
    return ""


def _weak_key(values: Sequence[object]) -> tuple[str, str]:
    route = "" if values[0] is None else str(values[0])
    location = ("" if values[LOCATION_INDEX] is None
                else str(values[LOCATION_INDEX]).strip())
    if not route or not location:
        raise ProjectionAuditError(
            f"blank Route/Location cannot enter projection identity: {route!r}, {location!r}")
    if location[-1:] not in ("R", "L"):
        location += _roadbed_tag(values)
    return route, location


def _med_wid_normalize(text: str) -> str:
    match = _MED_WID.fullmatch(text)
    if match is None:
        return text
    whole, fraction, suffix = match.groups()
    if suffix is not None and suffix not in _MED_WID_SUFFIXES:
        return text
    whole = whole.lstrip("0") or "0"
    if fraction is not None:
        fraction = fraction.rstrip("0")
    number = whole + (f".{fraction}" if fraction else "")
    return number + (suffix or "")


def _cell_state(left: object, right: object, column: int) -> str:
    display_left = _ascii_trim(left)
    display_right = _ascii_trim(right)
    if _dynamic_ditto(display_left) or _dynamic_ditto(display_right):
        return "N"
    if column == MED_WID_INDEX:
        display_left = _med_wid_normalize(display_left)
        display_right = _med_wid_normalize(display_right)
    return "E" if display_left == display_right else "D"


def _row_states(left: AuditRow, right: AuditRow) -> str:
    return "".join(
        _cell_state(left.values[index], right.values[index], index)
        for index in COMPARED_INDICES
    )


def _row_cost(left: AuditRow, right: AuditRow) -> int:
    return _row_states(left, right).count("D")


def _groups(rows: Sequence[AuditRow]) -> tuple[
        dict[tuple[str, str], list[AuditRow]], list[tuple[str, str]]]:
    groups: dict[tuple[str, str], list[AuditRow]] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        key = _weak_key(row.values)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    return groups, order


def _collision_summary(rows: Sequence[AuditRow]) -> dict[str, object]:
    keys = [_weak_key(row.values) for row in rows]
    counts = Counter(keys)
    collisions = {key: count for key, count in counts.items() if count > 1}
    ordered = _digest_records([list(key) for key in keys])
    multiset = _digest_records(sorted(
        (list(key) for key in keys), key=lambda key: _canonical(key)))
    return {
        "row_count": len(keys),
        "distinct_keys": len(counts),
        "duplicate_group_count": len(collisions),
        "rows_in_duplicate_groups": sum(collisions.values()),
        "max_multiplicity": max(collisions.values(), default=1),
        "multiplicity_histogram": {
            str(multiplicity): count for multiplicity, count in sorted(
                Counter(collisions.values()).items())
        },
        "ordered_key_manifest": ordered,
        "multiset_key_manifest": multiset,
    }


def _exact_group_pairs(
    key: tuple[str, str], side_a: Sequence[AuditRow], side_b: Sequence[AuditRow],
) -> tuple[list[tuple[int, int]], dict[str, object]]:
    na, nb = len(side_a), len(side_b)
    matrix_cells = na * nb
    if matrix_cells > MAX_EXACT_MATRIX_CELLS:
        raise ProjectionAuditError(
            f"duplicate group {key!r} needs {matrix_cells:,} exact matrix cells")
    smaller_side = "a" if na <= nb else "b"
    if na <= nb:
        costs = [[_row_cost(left, right) for right in side_b]
                 for left in side_a]
        assignment = exact_lexicographic_assignment(costs)
        pairs = [(index, target) for index, target in enumerate(assignment)]
    else:
        costs = [[_row_cost(left, right) for left in side_a]
                 for right in side_b]
        assignment = exact_lexicographic_assignment(costs)
        pairs = [(target, index) for index, target in enumerate(assignment)]
    pair_costs = [_row_cost(side_a[a], side_b[b]) for a, b in pairs]
    total_cost = sum(pair_costs)
    positional_cost = sum(
        _row_cost(side_a[index], side_b[index])
        for index in range(min(na, nb)))
    if total_cost > positional_cost:
        raise ProjectionAuditError("exact assignment is worse than file order")
    trace_pairs = [
        {
            "side_a_ordinal": side_a[a].ordinal,
            "side_a_source_row": side_a[a].source_row,
            "side_b_ordinal": side_b[b].ordinal,
            "side_b_source_row": side_b[b].source_row,
            "cost": cost,
        }
        for (a, b), cost in zip(pairs, pair_costs)
    ]
    return pairs, {
        "key": list(key),
        "side_a_size": na,
        "side_b_size": nb,
        "smaller_side": smaller_side,
        "matrix_cells": matrix_cells,
        "assignment_vector": list(assignment),
        "pairs": trace_pairs,
        "total_cost": total_cost,
        "positional_cost": positional_cost,
        "algorithm": "rectangular-hungarian-lex-v1",
        "quality": "exact",
    }


def _one_sided_record(side: str, key: tuple[str, str], occurrence: int,
                      row: AuditRow) -> dict[str, object]:
    return {
        "side": side,
        "key": [key[0], key[1], occurrence],
        "ordinal": row.ordinal,
        "source_row": row.source_row,
        "row_sha256": row.row_sha256,
    }


def _compare(label: str, side_a: Dataset, side_b: Dataset) -> dict[str, object]:
    groups_a, order_a = _groups(side_a.rows)
    groups_b, order_b = _groups(side_b.rows)
    order = [*order_a, *(key for key in order_b if key not in groups_a)]

    pair_digest = SequenceDigest()
    state_digest = SequenceDigest()
    a_only_digest = SequenceDigest()
    b_only_digest = SequenceDigest()
    one_sided_digest = SequenceDigest()
    assignment_digest = SequenceDigest()
    field_state_digests = {field: SequenceDigest() for field in COMPARED_FIELDS}
    field_states = {field: Counter() for field in COMPARED_FIELDS}

    paired_rows = differing_rows = differing_cells = 0
    asserted_cells = context_cells = 0
    side_a_only = side_b_only = 0
    assignment_groups = assignment_matrix_cells = 0
    max_assignment_matrix_cells = 0
    exact_assignment_cost = positional_assignment_cost = 0

    for key in order:
        ga = groups_a.get(key, [])
        gb = groups_b.get(key, [])
        if not ga:
            for occurrence, row in enumerate(gb, 1):
                record = _one_sided_record("b", key, occurrence, row)
                b_only_digest.add(record)
                one_sided_digest.add(record)
                side_b_only += 1
            continue
        if not gb:
            for occurrence, row in enumerate(ga, 1):
                record = _one_sided_record("a", key, occurrence, row)
                a_only_digest.add(record)
                one_sided_digest.add(record)
                side_a_only += 1
            continue

        if len(ga) == 1 and len(gb) == 1:
            pairs = [(0, 0)]
        else:
            pairs, trace = _exact_group_pairs(key, ga, gb)
            assignment_digest.add(trace)
            assignment_groups += 1
            assignment_matrix_cells += int(trace["matrix_cells"])
            max_assignment_matrix_cells = max(
                max_assignment_matrix_cells, int(trace["matrix_cells"]))
            exact_assignment_cost += int(trace["total_cost"])
            positional_assignment_cost += int(trace["positional_cost"])

        ordered_pairs = sorted(pairs, key=lambda pair: ga[pair[0]].ordinal)
        matched_a = {a for a, _b in pairs}
        matched_b = {b for _a, b in pairs}
        for occurrence, (a, b) in enumerate(ordered_pairs, 1):
            left, right = ga[a], gb[b]
            states = _row_states(left, right)
            cost = states.count("D")
            pair_key = [key[0], key[1], occurrence]
            pair_record = {
                "key": pair_key,
                "side_a": {
                    "ordinal": left.ordinal, "source_row": left.source_row,
                    "row_sha256": left.row_sha256,
                },
                "side_b": {
                    "ordinal": right.ordinal, "source_row": right.source_row,
                    "row_sha256": right.row_sha256,
                },
                "state_mask": states,
                "cost": cost,
            }
            pair_digest.add(pair_record)
            state_digest.add({"key": pair_key, "state_mask": states})
            paired_rows += 1
            differing_cells += cost
            differing_rows += int(cost > 0)
            asserted_cells += states.count("E") + cost
            context_cells += states.count("N")
            for field, state in zip(COMPARED_FIELDS, states):
                field_states[field][state] += 1
                field_state_digests[field].add([pair_key, state])

        extra_occurrence = len(ordered_pairs)
        for position, row in enumerate(ga):
            if position in matched_a:
                continue
            extra_occurrence += 1
            record = _one_sided_record("a", key, extra_occurrence, row)
            a_only_digest.add(record)
            one_sided_digest.add(record)
            side_a_only += 1
        extra_occurrence = len(ordered_pairs)
        for position, row in enumerate(gb):
            if position in matched_b:
                continue
            extra_occurrence += 1
            record = _one_sided_record("b", key, extra_occurrence, row)
            b_only_digest.add(record)
            one_sided_digest.add(record)
            side_b_only += 1

    per_field_states = {
        field: {
            "equal": field_states[field]["E"],
            "different": field_states[field]["D"],
            "nonasserting": field_states[field]["N"],
            "state_manifest": field_state_digests[field].result(),
        }
        for field in COMPARED_FIELDS
    }
    per_field_counts = {
        field: per_field_states[field]["different"] for field in COMPARED_FIELDS
    }
    counts = {
        "known": True,
        "paired_rows": paired_rows,
        "side_a_only_rows": side_a_only,
        "side_b_only_rows": side_b_only,
        "identical_rows": paired_rows - differing_rows,
        "differing_rows": differing_rows,
        "differing_cells": differing_cells,
        "asserted_cells": asserted_cells,
        "context_cells": context_cells,
        "per_field_counts": per_field_counts,
    }
    invariants = {
        "side_a_row_conservation": paired_rows + side_a_only == len(side_a.rows),
        "side_b_row_conservation": paired_rows + side_b_only == len(side_b.rows),
        "field_differences_sum": sum(per_field_counts.values()) == differing_cells,
        "paired_state_cells": (
            asserted_cells + context_cells == paired_rows * len(COMPARED_FIELDS)),
        "pair_manifest_complete": pair_digest.count == paired_rows,
        "state_manifest_complete": state_digest.count == paired_rows,
        "side_a_only_manifest_complete": a_only_digest.count == side_a_only,
        "side_b_only_manifest_complete": b_only_digest.count == side_b_only,
        "pairing_quality_exact": True,
    }
    if not all(invariants.values()):
        raise ProjectionAuditError(f"{label} comparison invariants failed: {invariants}")

    return {
        "side_a": side_a.label,
        "side_b": side_b.label,
        "completion": "complete",
        "pairing_quality": "exact",
        "weak_key": (
            "Route plus roadbed-aware Location; source R/L suffix is authoritative, "
            "otherwise the dittoed roadbed block supplies the suffix"),
        "compared_fields": list(COMPARED_FIELDS),
        "counts": counts,
        "per_field_states": per_field_states,
        "digests": {
            "serialization": DIGEST_SERIALIZATION,
            "ordering": (
                "base-key first occurrence on side A, then unseen side B; "
                "matched pairs in side-A row order"),
            "full_pair_manifest": pair_digest.result(),
            "full_state_manifest": state_digest.result(),
            "full_side_a_only_manifest": a_only_digest.result(),
            "full_side_b_only_manifest": b_only_digest.result(),
            "full_one_sided_manifest": one_sided_digest.result(),
        },
        "duplicate_metrics": {
            "side_a_weak_key_census": _collision_summary(side_a.rows),
            "side_b_weak_key_census": _collision_summary(side_b.rows),
            "exact_assignment_group_count": assignment_groups,
            "exact_assignment_matrix_cells": assignment_matrix_cells,
            "max_exact_assignment_matrix_cells": max_assignment_matrix_cells,
            "exact_assignment_total_cost": exact_assignment_cost,
            "positional_total_cost_for_assigned_groups": positional_assignment_cost,
            "exact_assignment_improvement": (
                positional_assignment_cost - exact_assignment_cost),
            "assignment_trace_manifest": assignment_digest.result(),
            "algorithm": "rectangular-hungarian-lex-v1",
            "matrix_cap_fail_closed": MAX_EXACT_MATRIX_CELLS,
        },
        "invariants": invariants,
    }


def _semantic_mutation_self_checks() -> dict[str, object]:
    def row(location: str) -> list[object]:
        values: list[object] = ["001", location] + ["X"] * (len(HEADERS) - 2)
        return values

    suffix_row = row("010.000R")
    block_row = row("010.000")
    for index in LEFT_BLOCK_INDICES:
        block_row[index] = "++"
    flipped_row = row("010.000")
    for index in RIGHT_BLOCK_INDICES:
        flipped_row[index] = "+"

    probes = {
        "roadbed_equivalent_encodings": (
            _weak_key(suffix_row) == _weak_key(block_row)
            and _weak_key(block_row) != _weak_key(flipped_row)),
        "ditto_mutation_changes_assertion": (
            _cell_state("++", "42", HEADERS.index("SPD")) == "N"
            and _cell_state("++x", "42", HEADERS.index("SPD")) == "D"),
        "med_wid_mutation_changes_equality": (
            _cell_state("0014.00Z", "14Z", MED_WID_INDEX) == "E"
            and _cell_state("0014.00z", "14Z", MED_WID_INDEX) == "D"),
        "whitespace_mutation_is_detected": (
            _ascii_trim(_load_normalize(" A\t\tB\nC ")) == "A B C"
            and _ascii_trim(_load_normalize("A\u00a0B")) != "A B"),
        "assignment_mutation_changes_pairing": (
            exact_lexicographic_assignment(((4, 0), (0, 4))) == (1, 0)
            and exact_lexicographic_assignment(((0, 4), (4, 0))) == (0, 1)
            and exact_lexicographic_assignment(((0, 0), (0, 0))) == (0, 1)),
    }
    return {
        "probe_count": len(probes),
        "detected_count": sum(probes.values()),
        "all_detected": all(probes.values()),
        "probes": probes,
    }


def _code_identities() -> dict[str, FileIdentity]:
    return {
        "oracle": capture_file_identity(Path(__file__)),
        "xlsx_stream_reader": capture_file_identity(
            BUILD_ROOT / "phase3_xlsx_stream.py"),
        "exact_assignment_oracle": capture_file_identity(
            BUILD_ROOT / "phase3_independent_oracle.py"),
    }


def _loaded_product_modules() -> list[dict[str, str]]:
    scripts = SCRIPTS_ROOT.resolve()
    found = []
    for name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        try:
            path = Path(raw_path).resolve()
            path.relative_to(scripts)
        except (OSError, ValueError):
            continue
        found.append({"module": name, "path": str(path)})
    return found


def run_audit() -> dict[str, object]:
    code_before = _code_identities()
    self_checks = _semantic_mutation_self_checks()
    if not self_checks["all_detected"]:
        raise ProjectionAuditError(f"semantic self-check failed: {self_checks}")
    stage6, stage6_before = _validate_stage6()

    # Keep TSN once; release each TSMIS side after its independent leg.
    tsn = _read_dataset("tsn")
    input_identities: dict[str, FileIdentity] = {"tsn": tsn.identity}
    inputs: dict[str, object] = {"tsn": tsn.summary}

    excel = _read_dataset("excel")
    input_identities["excel"] = excel.identity
    inputs["excel"] = excel.summary
    excel_result = _compare("excel_vs_tsn", excel, tsn)
    del excel

    pdf = _read_dataset("pdf")
    input_identities["pdf"] = pdf.identity
    inputs["pdf"] = pdf.summary
    pdf_result = _compare("pdf_vs_tsn", pdf, tsn)
    del pdf, tsn

    input_after = {
        label: capture_file_identity(binding["path"])
        for label, binding in INPUT_BINDINGS.items()
    }
    stage6_after = {
        label: capture_file_identity(binding["path"])
        for label, binding in STAGE6_BINDINGS.items()
    }
    code_after = _code_identities()
    product_modules = _loaded_product_modules()
    invariants = {
        "semantic_mutations_detected": self_checks["all_detected"] is True,
        "input_identities_stable": input_after == input_identities,
        "stage6_identities_stable": stage6_after == stage6_before,
        "audit_code_stable": code_after == code_before,
        "no_product_modules_imported": not product_modules,
        "excel_projection_complete": (
            excel_result["completion"] == "complete"
            and excel_result["pairing_quality"] == "exact"
            and all(excel_result["invariants"].values())),
        "pdf_projection_complete": (
            pdf_result["completion"] == "complete"
            and pdf_result["pairing_quality"] == "exact"
            and all(pdf_result["invariants"].values())),
    }
    if not all(invariants.values()):
        raise ProjectionAuditError(f"projection audit invariants failed: {invariants}")

    return {
        "schema_version": 1,
        "audit": "Stage 8 Highway Log independent projection comparison oracle",
        "terminal_status": "projection_audit_complete_not_family_acceptance",
        "projection_audit_complete": True,
        "inputs": inputs,
        "inputs_after": {
            label: _identity(identity) for label, identity in input_after.items()},
        "accepted_stage6_chain": stage6,
        "comparisons": {
            "excel_vs_tsn": excel_result,
            "pdf_vs_tsn": pdf_result,
        },
        "projection_policy": {
            "load_normalization": (
                "Boolean/date/time stabilization, then TAB/LF/CR/FF/VT replacement "
                "with ASCII space; comparison uses Excel-style ASCII TRIM"),
            "weak_key": (
                "Route plus roadbed-aware Location; an existing terminal R/L is "
                "authoritative, otherwise the dittoed roadbed block supplies it"),
            "ditto": (
                "a nonempty all-plus token on either side is dynamically "
                "nonasserting in every compared field"),
            "med_wid": (
                "ASCII digits[.digits][one printable non-digit/non-dot suffix]; "
                "integer leading zeros and fractional trailing zeros are ignored"),
            "duplicate_pairing": (
                "exact rectangular Hungarian assignment with minimum difference "
                "cost followed by lexicographically smallest smaller-side vector"),
        },
        "semantic_mutation_self_checks": self_checks,
        "independence": {
            "product_modules_imported": product_modules,
            "product_modules_imported_count": len(product_modules),
            "allowed_build_dependencies": {
                label: _identity(identity)
                for label, identity in code_before.items()
            },
            "product_code_changed_by_oracle": False,
        },
        "invariants": invariants,
        "known_product_findings": list(KNOWN_PRODUCT_FINDINGS),
        "known_limitations": [
            "The projection weak key does not restore district/county/owner identity.",
            "Accepted Stage 6 records loss of owner/qualifier, ADT, totals, and provenance claims.",
            "This oracle does not certify product-generated comparison workbooks or their evidence payloads.",
        ],
        "product_comparison_perfect": False,
        "product_end_to_end_perfect": False,
        "comparison_end_to_end_perfect": False,
        "full_physical_identity_perfect": False,
        "evidence_end_to_end_exact": False,
        "stage8_family_accepted": False,
    }


def _output_path(path: Path) -> Path:
    candidate = path.expanduser().resolve(strict=False)
    if candidate.exists():
        raise ProjectionAuditError(f"output path already exists: {candidate}")
    if candidate.suffix.casefold() != ".json":
        raise ProjectionAuditError("output path must end in .json")
    if not candidate.parent.is_dir():
        raise ProjectionAuditError(
            f"output parent must already exist: {candidate.parent}")
    return candidate


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path,
        help="required absent canonical-JSON destination; parent must exist")
    parser.add_argument(
        "--preflight", action="store_true",
        help="perform the complete bound audit without writing --output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    output = _output_path(args.output)
    result = run_audit()
    excel = result["comparisons"]["excel_vs_tsn"]["counts"]
    pdf = result["comparisons"]["pdf_vs_tsn"]["counts"]
    if args.preflight:
        print(
            "PASS Highway Log projection-oracle preflight: "
            f"Excel paired={excel['paired_rows']:,}, one-sided="
            f"{excel['side_a_only_rows']:,}/{excel['side_b_only_rows']:,}; "
            f"PDF paired={pdf['paired_rows']:,}, one-sided="
            f"{pdf['side_a_only_rows']:,}/{pdf['side_b_only_rows']:,}; "
            f"output not written: {output}")
        return 0

    payload = _json_bytes(result)
    with output.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(
        "PASS Highway Log projection oracle: "
        f"Excel paired={excel['paired_rows']:,}, differences="
        f"{excel['differing_rows']:,}/{excel['differing_cells']:,}; "
        f"PDF paired={pdf['paired_rows']:,}, differences="
        f"{pdf['differing_rows']:,}/{pdf['differing_cells']:,}; "
        f"output={output}; sha256={hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProjectionAuditError, XlsxStreamError, OSError) as exc:
        print(f"FAIL Highway Log projection oracle: {type(exc).__name__}: {exc}")
        raise SystemExit(1)

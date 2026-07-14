#!/usr/bin/env python3
"""Audit Highway Sequence Summary/Spot semantics in five frozen witnesses.

This is an audit-only development checker.  It imports no product comparison,
publication, workbook-reader, or sidecar code.  Every JSON/XLSX file is first
captured once, hashed from that payload, and then inspected from the same bytes.
Filesystem identities before/after capture are mutation guards only.

The checker deliberately preserves two product-red facts:

* CMP-AUD-214: Spot Check's intended field-by-field banner is overwritten by
  the header row at row 15.
* CMP-AUD-218: Spot Check does not independently establish row identity or
  one-sided status.  C11/C12/F12 all come from Comparison, and the purportedly
  independent field audit follows those supplied rows.  A consistently wrong
  pair or a false one-sided classification can therefore make all six Agree?
  cells say OK.

Passing means the frozen product workbooks were reconstructed exactly and the
two expected defects were proved.  It is not a comparison acceptance artifact.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import xml.etree.ElementTree as ET
import zipfile


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
DEFAULT_OUTPUT = (
    VISUAL_ROOT
    / "phase8_highway_sequence_summary_spot_audit_dev_r1"
    / "result.json"
)

RESULT_SPECS = {
    "excel_vs_normalized_tsn": {
        "root": "phase8_highway_sequence_product_comparison_excel_vs_normalized_tsn_r2",
        "bytes": 16_069,
        "sha256": "b1cf6f791c18917dfb51b3f9f2d8331075091992ce3d3c3415032108ee9bec83",
        "side_a": "TSMIS",
        "side_b": "TSN",
        "source_a": "current_tsmis_excel_consolidated.xlsx",
        "source_b": "tsn_highway_sequence_normalized.xlsx",
        "one_sided_note_extra": (
            " (mostly TSN segment breaks and TSMIS realignment markers)"
        ),
    },
    "excel_vs_raw_tsn": {
        "root": "phase8_highway_sequence_product_comparison_excel_vs_raw_tsn_dev_r1",
        "bytes": 21_185,
        "sha256": "2691fe4a5d6d1ed757d788c16bed7226a7966db8c1950423daf194369e6ae58c",
        "side_a": "TSMIS",
        "side_b": "TSN",
        "source_a": "current_tsmis_excel_consolidated.xlsx",
        "source_b": "highway_sequence_raw_tsn_audit_twin.xlsx",
        "one_sided_note_extra": (
            " (mostly TSN segment breaks and TSMIS realignment markers)"
        ),
    },
    "pdf_vs_normalized_tsn": {
        "root": "phase8_highway_sequence_product_comparison_pdf_vs_normalized_tsn_r2",
        "bytes": 16_228,
        "sha256": "65d79577e9dbc7dfbce22d3d12fa4b8a670edb78b439b56b2802afeaa077a59a",
        "side_a": "TSMIS (PDF)",
        "side_b": "TSN",
        "source_a": "current_tsmis_pdf_consolidated.xlsx",
        "source_b": "tsn_highway_sequence_normalized.xlsx",
        "one_sided_note_extra": (
            " (mostly TSN segment breaks and TSMIS realignment markers)"
        ),
    },
    "pdf_vs_raw_tsn": {
        "root": "phase8_highway_sequence_product_comparison_pdf_vs_raw_tsn_dev_r1",
        "bytes": 21_346,
        "sha256": "31656c378240c30218054ae57972d5480f68aa37045140a2c9d6a3aa3e7b2b81",
        "side_a": "TSMIS (PDF)",
        "side_b": "TSN",
        "source_a": "current_tsmis_pdf_consolidated.xlsx",
        "source_b": "highway_sequence_raw_tsn_audit_twin.xlsx",
        "one_sided_note_extra": (
            " (mostly TSN segment breaks and TSMIS realignment markers)"
        ),
    },
    "pdf_vs_excel": {
        "root": "phase8_highway_sequence_product_comparison_pdf_vs_excel_r2",
        "bytes": 15_896,
        "sha256": "972ea8466903a27d2cc609769d6fead11aceb5e2dd8d1a4e653cc0b92309f581",
        "side_a": "TSMIS (PDF)",
        "side_b": "TSMIS (Excel)",
        "source_a": "current_tsmis_pdf_consolidated.xlsx",
        "source_b": "current_tsmis_excel_consolidated.xlsx",
        "one_sided_note_extra": (
            ' (mostly the equate rows — the two renders seat the "E" suffix on '
            "different rows, see Notes)"
        ),
    },
}

CREATED_DATE = "2026-07-13"
FIELDS = (
    "County", "City", "HG", "FT", "Distance To Next Point", "Description",
)
SOURCE_HEADER = (
    "Route", "County", "PM", "City", "HG", "FT",
    "Distance To Next Point", "Description",
)
SOURCE_FIELD_INDEX = (1, 3, 4, 5, 6, 7)
SOURCE_FIELD_COLUMN = ("C", "E", "F", "G", "H", "I")
COMPARISON_FIELD_COLUMN = ("H", "I", "J", "K", "L", "M")
CONTEXT_POSITIONS = frozenset((1, 2, 4))
STATE_HEADER = "__CMP_E1_STATE_V1_C001_P0000_P0005"
FRESH_HEADER = "__CMP_E2_BUILD_FRESH_V1_C001_B_J"
HELPER_RE = re.compile(r"^__CMP_E2_KEY_V1_[0-9]{8}$")
DIFF_MARK = " ≠ "
XL_MAX_ROWS = 1_048_576
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
STYLE_ATTR_RE = re.compile(rb' s="[0-9]+"')


class AuditError(RuntimeError):
    """A frozen identity or independently reconstructed workbook fact drifted."""


@dataclass(frozen=True)
class CapturedFile:
    path: Path
    payload: bytes
    identity: dict[str, object]
    fs_fingerprint: tuple[object, ...]

    @classmethod
    def capture(cls, path: Path) -> "CapturedFile":
        path = path.expanduser().resolve()
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
            raise AuditError(f"required ordinary file is absent or indirect: {path}")
        with path.open("rb") as handle:
            payload = handle.read()
        after = os.lstat(path)
        fp_before = _stat_fingerprint(before)
        fp_after = _stat_fingerprint(after)
        if fp_before != fp_after or len(payload) != before.st_size:
            raise AuditError(f"file mutated while captured: {path}")
        identity = {
            "path": str(path),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        return cls(path, payload, identity, fp_after)

    def assert_unchanged(self) -> None:
        current = os.lstat(self.path)
        if _stat_fingerprint(current) != self.fs_fingerprint:
            raise AuditError(f"captured file mutated after inspection: {self.path}")


@dataclass(frozen=True)
class Cell:
    value: object
    kind: str


@dataclass(frozen=True)
class SourceRow:
    values: tuple[object, ...]
    semantics: tuple[tuple[str, object], ...]
    helper: str
    backlink: str

    @property
    def route(self) -> str:
        return _trim(self.values[0])

    @property
    def location(self) -> str:
        return f"{_trim(self.values[1])} {_trim(self.values[2])}".strip()

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(_trim(self.values[index]) for index in SOURCE_FIELD_INDEX)


@dataclass(frozen=True)
class UnionRow:
    physical_row: int
    route: str
    location: str
    occurrence: int
    left_index: int | None
    right_index: int | None
    helper: str
    status: str
    diffs: int | None
    displays: tuple[str, ...]
    state_mask: str


def _stat_fingerprint(value: os.stat_result) -> tuple[object, ...]:
    return (
        value.st_mode, value.st_size, value.st_mtime_ns,
        getattr(value, "st_ctime_ns", None), value.st_dev, value.st_ino,
    )


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _json_line(value: object) -> bytes:
    return _canonical(value) + b"\n"


def _strict_json(capture: CapturedFile) -> dict[str, object]:
    try:
        value = json.loads(capture.payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"invalid strict JSON {capture.path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON root is not an object: {capture.path}")
    if capture.payload != _json_line(value):
        raise AuditError(f"JSON is not canonical one-line UTF-8: {capture.path}")
    return value


def _column_index(reference: str) -> int:
    match = re.match(r"^([A-Z]+)", reference)
    if match is None:
        raise AuditError(f"invalid cell reference {reference!r}")
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - 64
    return result


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _sheet_ref(name: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def _trim(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(" +", " ", str(value)).strip(" ")


class XlsxBytes:
    """Minimal read-only OOXML reader over one already-captured payload."""

    def __init__(self, captured: CapturedFile):
        self.captured = captured
        self._buffer = BytesIO(captured.payload)
        self.archive = zipfile.ZipFile(self._buffer)
        self.sheets, self.states, self.calc = self._workbook_map()
        self.shared_strings = self._load_shared_strings()

    def close(self) -> None:
        self.archive.close()
        self._buffer.close()

    def __enter__(self) -> "XlsxBytes":
        return self

    def __exit__(self, _kind, _value, _traceback) -> None:
        self.close()

    def _workbook_map(self):
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        rels = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        sheets: dict[str, str] = {}
        states: dict[str, str] = {}
        for node in workbook.findall(f"{{{NS_MAIN}}}sheets/{{{NS_MAIN}}}sheet"):
            name = node.attrib["name"]
            relation = node.attrib[f"{{{NS_REL}}}id"]
            target = targets[relation].replace("\\", "/")
            member = (
                target.lstrip("/") if target.startswith("/")
                else posixpath.normpath(posixpath.join("xl", target))
            )
            if member not in self.archive.namelist():
                raise AuditError(f"{self.captured.path.name}: absent sheet member {member}")
            sheets[name] = member
            states[name] = node.attrib.get("state", "visible")
        calc_node = workbook.find(f"{{{NS_MAIN}}}calcPr")
        calc = dict(calc_node.attrib) if calc_node is not None else {}
        return sheets, states, calc

    def _load_shared_strings(self) -> tuple[str, ...]:
        name = "xl/sharedStrings.xml"
        if name not in self.archive.namelist():
            return ()
        root = ET.fromstring(self.archive.read(name))
        values = []
        for item in root.findall(f"{{{NS_MAIN}}}si"):
            values.append("".join(
                node.text or "" for node in item.iter(f"{{{NS_MAIN}}}t")
            ))
        return tuple(values)

    def _decode_cell(self, node: ET.Element) -> Cell:
        formula = node.find(f"{{{NS_MAIN}}}f")
        if formula is not None:
            if formula.attrib:
                raise AuditError(
                    f"{self.captured.path.name}: shared/array formula not supported"
                )
            return Cell("=" + (formula.text or ""), "f")
        kind = node.attrib.get("t", "n")
        if kind == "inlineStr":
            inline = node.find(f"{{{NS_MAIN}}}is")
            value = "" if inline is None else "".join(
                item.text or "" for item in inline.iter(f"{{{NS_MAIN}}}t")
            )
            return Cell(value, "s")
        raw_node = node.find(f"{{{NS_MAIN}}}v")
        raw = None if raw_node is None else raw_node.text
        if kind == "s":
            if raw is None:
                raise AuditError("shared-string cell has no index")
            return Cell(self.shared_strings[int(raw)], "s")
        if kind in {"str", "e"}:
            return Cell("" if raw is None else raw, kind)
        if kind == "b":
            return Cell(raw == "1", "b")
        if raw in (None, ""):
            return Cell(None, "n")
        try:
            number = float(raw) if any(char in raw for char in ".Ee") else int(raw)
        except ValueError as exc:
            raise AuditError(f"invalid numeric cell {raw!r}") from exc
        return Cell(number, "n")

    def iter_rows(self, sheet: str):
        member = self.sheets.get(sheet)
        if member is None:
            raise AuditError(f"{self.captured.path.name}: missing sheet {sheet!r}")
        with self.archive.open(member) as stream:
            for _event, node in ET.iterparse(stream, events=("end",)):
                if node.tag != f"{{{NS_MAIN}}}row":
                    continue
                row_number = int(node.attrib["r"])
                cells: dict[int, Cell] = {}
                for cell_node in node.findall(f"{{{NS_MAIN}}}c"):
                    reference = cell_node.attrib.get("r")
                    if reference is None:
                        raise AuditError(f"{sheet}: cell without reference")
                    column = _column_index(reference)
                    if column in cells:
                        raise AuditError(f"{sheet}!{reference}: duplicate cell")
                    cells[column] = self._decode_cell(cell_node)
                yield row_number, cells
                node.clear()

    def sheet_cell_map(self, sheet: str) -> dict[str, tuple[str, object]]:
        result: dict[str, tuple[str, object]] = {}
        for row_number, cells in self.iter_rows(sheet):
            for column, cell in cells.items():
                coordinate = f"{_column_letter(column)}{row_number}"
                result[coordinate] = (cell.kind, cell.value)
        return result

    def styleless_member_digest(self, sheet: str) -> dict[str, object]:
        """Hash complete sheet XML after deleting only numeric style ids."""
        member = self.sheets[sheet]
        digest = hashlib.sha256()
        source_bytes = normalized_bytes = 0
        pending = b""
        with self.archive.open(member) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                source_bytes += len(chunk)
                pending += chunk
                cut = pending.rfind(b">", 0, max(0, len(pending) - 96))
                if cut < 0:
                    continue
                part, pending = pending[:cut + 1], pending[cut + 1:]
                normalized = STYLE_ATTR_RE.sub(b"", part)
                normalized_bytes += len(normalized)
                digest.update(normalized)
        normalized = STYLE_ATTR_RE.sub(b"", pending)
        normalized_bytes += len(normalized)
        digest.update(normalized)
        return {
            "member": member,
            "source_xml_bytes": source_bytes,
            "styleless_xml_bytes": normalized_bytes,
            "styleless_xml_sha256": digest.hexdigest(),
        }


def _cell_value(cells: dict[int, Cell], column: int) -> object:
    cell = cells.get(column)
    return None if cell is None else cell.value


def _cell_semantic(cells: dict[int, Cell], column: int) -> tuple[str, object]:
    cell = cells.get(column)
    return ("missing", None) if cell is None else (cell.kind, cell.value)


def _fresh_formula(snapshot: str, row: int) -> str:
    checks = []
    for column in "BCDEFGHIJ":
        current = f"${column}{row}"
        expected = f"{snapshot}!${column}{row}"
        left = f'IF(ISBLANK({current}),"",{current}&"")'
        right = f'IF(ISBLANK({expected}),"",{expected}&"")'
        checks.append(f"EXACT({left},{right})")
    return f'=IF(AND({",".join(checks)}),"OK","STALE")'


def _tail_formula(row: int) -> str:
    ranges = [f"${column}${row}:${column}${XL_MAX_ROWS}" for column in "BCDEFGHIJ"]
    return f'=IF(COUNTA({",".join(ranges)})=0,"END","STALE")'


def _source_header() -> tuple[object, ...]:
    return ("Comparison row", *SOURCE_HEADER, "Key (helper)", FRESH_HEADER)


def _snapshot_header() -> tuple[object, ...]:
    return ("Source row", *SOURCE_HEADER, "Key (helper)")


def _parse_source_sheet(
    workbook: XlsxBytes, sheet: str, snapshot: str,
) -> tuple[list[SourceRow], dict[str, object]]:
    rows: list[SourceRow] = []
    helpers: set[str] = set()
    footer_seen = False
    projection_digest = hashlib.sha256()
    expected_data_row = 2
    for row_number, cells in workbook.iter_rows(sheet):
        if row_number == 1:
            values = tuple(_cell_value(cells, column) for column in range(1, 12))
            if values != _source_header() or set(cells) != set(range(1, 12)):
                raise AuditError(f"{sheet}: exact source header/cell map drift")
            continue
        if footer_seen:
            if cells:
                raise AuditError(f"{sheet}: unexplained row after footer {row_number}")
            continue
        if row_number != expected_data_row:
            raise AuditError(f"{sheet}: source row gap at {expected_data_row}")
        # The footer has only the K sentinel formula.
        if set(cells).issubset({11}) and 11 in cells:
            expected_footer = _tail_formula(row_number)
            if cells[11] != Cell(expected_footer, "f"):
                raise AuditError(f"{sheet}!K{row_number}: tail sentinel drift")
            footer_seen = True
            continue
        if any(column > 11 for column in cells):
            raise AuditError(f"{sheet}!{row_number}: unexplained source cell")
        backlink = cells.get(1)
        helper = cells.get(10)
        fresh = cells.get(11)
        if backlink is None or backlink.kind != "f":
            raise AuditError(f"{sheet}!A{row_number}: source backlink absent")
        if (
            helper is None or helper.kind != "s"
            or not isinstance(helper.value, str)
            or HELPER_RE.fullmatch(helper.value) is None
            or helper.value in helpers
        ):
            raise AuditError(f"{sheet}!J{row_number}: helper token drift")
        if fresh != Cell(_fresh_formula(snapshot, row_number), "f"):
            raise AuditError(f"{sheet}!K{row_number}: freshness formula drift")
        values = tuple(_cell_value(cells, column) for column in range(2, 10))
        if any(cells[column].kind in {"f", "e"} for column in range(2, 10)
               if column in cells):
            raise AuditError(f"{sheet}!{row_number}: formula/error in source data")
        helpers.add(helper.value)
        semantics = tuple(
            _cell_semantic(cells, column) for column in range(2, 10)
        )
        row = SourceRow(values, semantics, helper.value, str(backlink.value))
        rows.append(row)
        projection_digest.update(_json_line([
            len(rows) - 1,
            *[list(_cell_semantic(cells, column)) for column in range(2, 10)],
            helper.value,
        ]))
        expected_data_row += 1
    if not footer_seen or not rows:
        raise AuditError(f"{sheet}: source footer/data absent")
    return rows, {
        "rows": len(rows),
        "helpers_unique": len(helpers) == len(rows),
        "ordered_typed_projection_sha256": projection_digest.hexdigest(),
        "freshness_formulas_exact": True,
        "tail_sentinel_exact": True,
    }


def _parse_snapshot(
    workbook: XlsxBytes, sheet: str, source: list[SourceRow],
) -> dict[str, object]:
    if workbook.states.get(sheet) != "veryHidden":
        raise AuditError(f"{sheet}: snapshot is not veryHidden")
    digest = hashlib.sha256()
    expected_row = 1
    observed = 0
    for row_number, cells in workbook.iter_rows(sheet):
        if row_number != expected_row:
            raise AuditError(f"{sheet}: snapshot row gap at {expected_row}")
        if row_number == 1:
            values = tuple(_cell_value(cells, column) for column in range(1, 11))
            if values != _snapshot_header() or set(cells) != set(range(1, 11)):
                raise AuditError(f"{sheet}: exact snapshot header/cell map drift")
        else:
            index = row_number - 2
            if index >= len(source):
                raise AuditError(f"{sheet}: extra snapshot row {row_number}")
            if any(column > 10 for column in cells):
                raise AuditError(f"{sheet}!{row_number}: unexplained snapshot cell")
            expected = source[index]
            if _cell_semantic(cells, 1) != ("n", index + 1):
                raise AuditError(f"{sheet}!A{row_number}: source ordinal drift")
            for offset, semantic in enumerate(expected.semantics, start=2):
                actual = _cell_semantic(cells, offset)
                if actual != semantic:
                    raise AuditError(f"{sheet}!{_column_letter(offset)}{row_number}: snapshot drift")
            if _cell_semantic(cells, 10) != ("s", expected.helper):
                raise AuditError(f"{sheet}!J{row_number}: snapshot helper drift")
            if any(cell.kind in {"f", "e"} for cell in cells.values()):
                raise AuditError(f"{sheet}!{row_number}: formula/error in snapshot")
            digest.update(_json_line([
                index + 1, *expected.values, expected.helper,
            ]))
            observed += 1
        expected_row += 1
    if observed != len(source):
        raise AuditError(f"{sheet}: snapshot/source row census drift")
    return {
        "rows": observed,
        "ordered_snapshot_sha256": digest.hexdigest(),
        "every_snapshot_row_and_value_exact": True,
    }


STATIC_LINK_RE = re.compile(
    r'^=HYPERLINK\("#(?P<sheet>(?:\'(?:[^\']|\'\')+\'|[^!]+))!'
    r'(?P<row>[0-9]+):(?P=row)",(?P<label>[0-9]+)\)$'
)


def _parse_static_link(cell: Cell | None, side: str, label: str) -> int | None:
    if cell is None or cell.value in (None, ""):
        return None
    if cell.kind != "f" or not isinstance(cell.value, str):
        raise AuditError(f"{label}: expected static hyperlink formula")
    match = STATIC_LINK_RE.fullmatch(cell.value)
    if match is None:
        raise AuditError(f"{label}: malformed static hyperlink {cell.value!r}")
    sheet = match.group("sheet")
    if sheet.startswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    row = int(match.group("row"))
    if sheet != side or row != int(match.group("label")) or row < 2:
        raise AuditError(f"{label}: hyperlink target drift")
    return row - 2


def _field_projection(
    left: SourceRow | None, right: SourceRow | None,
) -> tuple[tuple[str, ...], str]:
    if left is None and right is None:
        raise AuditError("union row has neither source")
    if left is None:
        return right.fields, "U" * len(FIELDS)
    if right is None:
        return left.fields, "U" * len(FIELDS)
    displays: list[str] = []
    states: list[str] = []
    for position, (value_a, value_b) in enumerate(
        zip(left.fields, right.fields, strict=True)
    ):
        if position in CONTEXT_POSITIONS:
            states.append("N")
            displays.append(value_a if value_a else value_b)
        elif value_a == value_b:
            states.append("E")
            displays.append(value_a)
        else:
            states.append("D")
            displays.append(
                f"{value_a or '(blank)'}{DIFF_MARK}{value_b or '(blank)'}"
            )
    return tuple(displays), "".join(states)


def _expected_value_comparison_row(
    physical_row: int, left: SourceRow | None, right: SourceRow | None,
    occurrence: int, side_a: str, side_b: str,
) -> tuple[dict[int, Cell], tuple[str, ...], str, int | None, str]:
    existing = left if left is not None else right
    route, location = existing.route, existing.location
    if left is not None and right is not None and (
        left.route != right.route or left.location != right.location
    ):
        raise AuditError(
            f"Comparison row {physical_row}: product-key mismatch across paired rows"
        )
    displays, mask = _field_projection(left, right)
    if left is None:
        status = f"{side_b} only"
    elif right is None:
        status = f"{side_a} only"
    else:
        status = "Both"
    diffs = mask.count("D") if status == "Both" else None
    result = {
        1: Cell(route, "s"), 2: Cell(location, "s"),
        3: Cell(occurrence, "n"),
        6: Cell(status, "s"),
        7: Cell(diffs, "n") if diffs is not None else Cell(None, "n"),
        14: Cell(mask, "s"),
    }
    if left is not None:
        source_row = left_index = None  # set by caller from static link
    for position, display in enumerate(displays, start=8):
        result[position] = Cell(None, "n") if display == "" else Cell(display, "s")
    return result, displays, mask, diffs, status


def _comparison_header(side_a: str, side_b: str) -> tuple[str, ...]:
    return (
        "Route", "PM", "#", f"{side_a} Row", f"{side_b} Row",
        "Status", "Diffs", *FIELDS, STATE_HEADER,
    )


def _parse_value_comparison(
    workbook: XlsxBytes, side_a: str, side_b: str,
    rows_a: list[SourceRow], rows_b: list[SourceRow],
) -> tuple[list[UnionRow], dict[str, object], UnionRow]:
    union: list[UnionRow] = []
    assigned_a: list[int | None] = [None] * len(rows_a)
    assigned_b: list[int | None] = [None] * len(rows_b)
    seen_identities: set[tuple[str, str, int]] = set()
    statuses: Counter[str] = Counter()
    per_field: Counter[str] = Counter()
    differing_rows = differing_cells = 0
    first_diff: UnionRow | None = None
    digest = hashlib.sha256()
    expected_physical = 1
    for physical_row, cells in workbook.iter_rows("Comparison"):
        if physical_row != expected_physical:
            raise AuditError(f"Comparison: row gap at {expected_physical}")
        if any(column > 14 for column in cells):
            raise AuditError(f"Comparison!{physical_row}: unexplained cell")
        if physical_row == 1:
            values = tuple(_cell_value(cells, column) for column in range(1, 15))
            if values != _comparison_header(side_a, side_b) or set(cells) != set(range(1, 15)):
                raise AuditError("Comparison: exact header/cell map drift")
            expected_physical += 1
            continue
        left_index = _parse_static_link(
            cells.get(4), side_a, f"Comparison!D{physical_row}",
        )
        right_index = _parse_static_link(
            cells.get(5), side_b, f"Comparison!E{physical_row}",
        )
        if left_index is not None and not 0 <= left_index < len(rows_a):
            raise AuditError(f"Comparison!D{physical_row}: source row out of range")
        if right_index is not None and not 0 <= right_index < len(rows_b):
            raise AuditError(f"Comparison!E{physical_row}: source row out of range")
        left = None if left_index is None else rows_a[left_index]
        right = None if right_index is None else rows_b[right_index]
        existing = left if left is not None else right
        if existing is None:
            raise AuditError(f"Comparison!{physical_row}: no source links")
        key = (existing.route, existing.location)
        occurrence_value = _cell_value(cells, 3)
        if type(occurrence_value) is not int or occurrence_value < 1:
            raise AuditError(f"Comparison!C{physical_row}: occurrence is not positive integer")
        occurrence = occurrence_value
        identity = (key[0], key[1], occurrence)
        if identity in seen_identities:
            raise AuditError(f"Comparison!{physical_row}: duplicate displayed identity {identity!r}")
        seen_identities.add(identity)
        expected, displays, mask, diffs, status = _expected_value_comparison_row(
            physical_row, left, right, occurrence, side_a, side_b,
        )
        if left is not None:
            expected[4] = Cell(
                f'=HYPERLINK("#{_sheet_ref(side_a)}!{left_index + 2}:'
                f'{left_index + 2}",{left_index + 2})', "f",
            )
        else:
            expected[4] = Cell(None, "n")
        if right is not None:
            expected[5] = Cell(
                f'=HYPERLINK("#{_sheet_ref(side_b)}!{right_index + 2}:'
                f'{right_index + 2}",{right_index + 2})', "f",
            )
        else:
            expected[5] = Cell(None, "n")
        if set(cells) != set(range(1, 15)):
            raise AuditError(f"Comparison!{physical_row}: exact cell universe drift")
        actual = cells
        if actual != expected:
            for column in range(1, 15):
                if actual[column] != expected[column]:
                    raise AuditError(
                        f"Comparison!{_column_letter(column)}{physical_row}: "
                        f"{actual[column]!r} != {expected[column]!r}"
                    )
            raise AuditError(f"Comparison!{physical_row}: unexplained row drift")
        helper = left.helper if left is not None else right.helper
        if left is not None and right is not None and left.helper != right.helper:
            raise AuditError(f"Comparison!{physical_row}: paired helper-token drift")
        item = UnionRow(
            physical_row, key[0], key[1], occurrence,
            left_index, right_index, helper, status, diffs, displays, mask,
        )
        union.append(item)
        if left_index is not None:
            if assigned_a[left_index] is not None:
                raise AuditError(f"{side_a} source row reused")
            assigned_a[left_index] = physical_row
        if right_index is not None:
            if assigned_b[right_index] is not None:
                raise AuditError(f"{side_b} source row reused")
            assigned_b[right_index] = physical_row
        statuses[status] += 1
        if status == "Both":
            if diffs:
                differing_rows += 1
                differing_cells += diffs
                if first_diff is None:
                    first_diff = item
            for position, state in enumerate(mask):
                if state == "D":
                    per_field[FIELDS[position]] += 1
        digest.update(_json_line([
            physical_row, key[0], key[1], occurrence,
            left_index, right_index, status, diffs, *displays, mask,
        ]))
        expected_physical += 1
    if first_diff is None:
        raise AuditError("Comparison: no paired differing row for Spot default")
    if any(value is None for value in assigned_a + assigned_b):
        raise AuditError("Comparison: one or more embedded source rows are unrepresented")
    for index, physical in enumerate(assigned_a):
        expected_link = f'=HYPERLINK("#Comparison!{physical}:{physical}",{physical})'
        if rows_a[index].backlink != expected_link:
            raise AuditError(f"{side_a} source backlink {index + 2} drift")
    for index, physical in enumerate(assigned_b):
        expected_link = f'=HYPERLINK("#Comparison!{physical}:{physical}",{physical})'
        if rows_b[index].backlink != expected_link:
            raise AuditError(f"{side_b} source backlink {index + 2} drift")
    routes_a = {row.route for row in rows_a}
    routes_b = {row.route for row in rows_b}
    counts = {
        "side_a_rows": len(rows_a),
        "side_b_rows": len(rows_b),
        "union_rows": len(union),
        "paired_rows": statuses["Both"],
        "side_a_only_rows": statuses[f"{side_a} only"],
        "side_b_only_rows": statuses[f"{side_b} only"],
        "route_both": len(routes_a & routes_b),
        "route_a_only": len(routes_a - routes_b),
        "route_b_only": len(routes_b - routes_a),
        "differing_rows": differing_rows,
        "identical_rows": statuses["Both"] - differing_rows,
        "differing_cells": differing_cells,
        "per_field": {field: per_field[field] for field in FIELDS},
        "ordered_reconstruction_sha256": digest.hexdigest(),
    }
    return union, counts, first_diff


def _trim_ref(side: str, column: str, row_ref: str) -> str:
    index = f"INDEX({_sheet_ref(side)}!{column}:{column},{row_ref})"
    return f'IF(ISBLANK({index}),"",TRIM({index}))'


def _field_display_formula(
    side_a: str, side_b: str, row: int, position: int,
) -> str:
    column = SOURCE_FIELD_COLUMN[position]
    left = _trim_ref(side_a, column, f"$D{row}")
    right = _trim_ref(side_b, column, f"$E{row}")
    status = f"$F{row}"
    if position in CONTEXT_POSITIONS:
        matched = f'IF({left}="",{right},{left})'
    else:
        show_left = f'IF({left}="","(blank)",{left})'
        show_right = f'IF({right}="","(blank)",{right})'
        matched = (
            f'IF(MID($N{row},{position + 1},1)="D",'
            f'{show_left}&"{DIFF_MARK}"&{show_right},{left})'
        )
    return (
        f'=IF({status}="{side_a} only",{left},'
        f'IF({status}="{side_b} only",{right},{matched}))'
    )


def _state_formula(side_a: str, side_b: str, row: int) -> str:
    parts = []
    for position, column in enumerate(SOURCE_FIELD_COLUMN):
        if position in CONTEXT_POSITIONS:
            parts.append('"N"')
        else:
            left = _trim_ref(side_a, column, f"$D{row}")
            right = _trim_ref(side_b, column, f"$E{row}")
            parts.append(f'IF(EXACT({left},{right}),"E","D")')
    return f'=IF($F{row}<>"Both",REPT("U",6),{"&".join(parts)})'


def _dynamic_link(side: str, helper: str) -> str:
    ref = _sheet_ref(side)
    match = f'MATCH("{helper}",{ref}!$J:$J,0)'
    return f'=IFERROR(HYPERLINK("#{ref}!"&{match}&":"&{match},{match}),"")'


def _expected_formula_comparison_row(
    item: UnionRow, side_a: str, side_b: str,
) -> dict[int, Cell]:
    row = item.physical_row
    result = {
        1: Cell(item.route, "s"), 2: Cell(item.location, "s"),
        3: Cell(item.occurrence, "n"),
        4: Cell(_dynamic_link(side_a, item.helper), "f"),
        5: Cell(_dynamic_link(side_b, item.helper), "f"),
        6: Cell(
            f'=IF(AND(D{row}<>"",E{row}<>""),"Both",'
            f'IF(D{row}<>"","{side_a} only","{side_b} only"))', "f",
        ),
        7: Cell(
            f'=IF(F{row}<>"Both","",SUMPRODUCT(LEN($N{row}:$N{row})-'
            f'LEN(SUBSTITUTE($N{row}:$N{row},"D",""))))', "f",
        ),
        14: Cell(_state_formula(side_a, side_b, row), "f"),
    }
    for position in range(len(FIELDS)):
        result[8 + position] = Cell(
            _field_display_formula(side_a, side_b, row, position), "f",
        )
    return result


def _parse_formula_comparison(
    workbook: XlsxBytes, side_a: str, side_b: str, union: list[UnionRow],
) -> dict[str, object]:
    digest = hashlib.sha256()
    expected_index = -1
    for physical_row, cells in workbook.iter_rows("Comparison"):
        if any(column > 14 for column in cells):
            raise AuditError(f"formula Comparison!{physical_row}: unexplained cell")
        if physical_row == 1:
            values = tuple(_cell_value(cells, column) for column in range(1, 15))
            if values != _comparison_header(side_a, side_b) or set(cells) != set(range(1, 15)):
                raise AuditError("formula Comparison exact header drift")
            continue
        expected_index += 1
        if expected_index >= len(union):
            raise AuditError("formula Comparison has extra rows")
        item = union[expected_index]
        if physical_row != item.physical_row or set(cells) != set(range(1, 15)):
            raise AuditError(f"formula Comparison row geometry drift at {physical_row}")
        expected = _expected_formula_comparison_row(item, side_a, side_b)
        if cells != expected:
            for column in range(1, 15):
                if cells.get(column) != expected[column]:
                    raise AuditError(
                        f"formula Comparison!{_column_letter(column)}{physical_row}: "
                        f"formula/value reconstruction drift"
                    )
        digest.update(_json_line([
            physical_row,
            *[[cells[column].kind, cells[column].value] for column in range(1, 15)],
        ]))
    if expected_index + 1 != len(union):
        raise AuditError("formula Comparison row census drift")
    return {
        "rows": len(union),
        "cells_reconstructed": len(union) * 14,
        "ordered_formula_cell_map_sha256": digest.hexdigest(),
        "every_formula_and_literal_cell_exact": True,
    }


def _map_put(
    target: dict[str, tuple[str, object]], coordinate: str, value: object,
) -> None:
    if coordinate in target:
        raise AuditError(f"oracle attempted duplicate cell {coordinate}")
    if isinstance(value, str):
        if value.startswith("="):
            kind = "f"
        else:
            kind = "s"
    elif type(value) is bool:
        kind = "b"
    elif isinstance(value, (int, float)):
        kind = "n"
    elif value is None:
        kind = "missing"
    else:
        raise AuditError(f"unsupported oracle cell value {value!r}")
    target[coordinate] = (kind, value)


def _freshness_summary(side: str, snapshot: str, count: int) -> list[str]:
    ref = _sheet_ref(side)
    return [
        f"COUNTA({ref}!$A:$A)-1={count}",
        f"COUNTA({snapshot}!$A:$A)-1={count}",
        f'COUNTIF({ref}!$K$2:$K${count + 1},"STALE")=0',
        f'COUNTIF({ref}!$K$2:$K${count + 1},"OK")={count}',
        f'{ref}!$K${count + 2}="END"',
    ]


def _expected_summary_map(
    spec: dict[str, object], counts: dict[str, object], *, formulas: bool,
) -> dict[str, tuple[str, object]]:
    side_a, side_b = str(spec["side_a"]), str(spec["side_b"])
    only_a, only_b = f"{side_a} only", f"{side_b} only"
    sa, sb = _sheet_ref(side_a), _sheet_ref(side_b)
    last = int(counts["union_rows"]) + 1
    result: dict[str, tuple[str, object]] = {}
    row = 2

    def line(values: dict[str, object], advance: int = 1) -> None:
        nonlocal row
        for column, value in values.items():
            _map_put(result, f"{column}{row}", value)
        row += advance

    scope = "Consolidated (all routes)" + ("" if formulas else " — VALUES copy")
    line({"B": f"{side_a} vs {side_b} — Highway Sequence — Discrepancy Report ({scope})"})
    if formulas:
        line({"B": "▶ PRESS F9 TO CALCULATE — this workbook opens uncalculated "
                    "(blank/0 cells). The first F9 takes a few minutes; let it "
                    "finish, then save."})
    freshness = "AND(" + ",".join(
        _freshness_summary(side_a, "__CMP_E2_SNAPSHOT_A", int(counts["side_a_rows"]))
        + _freshness_summary(side_b, "__CMP_E2_SNAPSHOT_B", int(counts["side_b_rows"]))
    ) + ")"
    regenerate = (
        "✗ REGENERATE REQUIRED — a source/helper row changed after this workbook "
        "was built. Displayed counts are observations under stale build-time "
        "identity/pairing and are not certified."
    )
    one_sided = int(counts["side_a_only_rows"]) + int(counts["side_b_only_rows"])
    if formulas:
        verdict = (
            f'=IF({freshness},IF(AND(SUM(Comparison!G2:G{last})=0,'
            f'COUNTIF(Comparison!F:F,"{only_a}")+COUNTIF(Comparison!F:F,"{only_b}")=0),'
            f'"✓ EVERYTHING MATCHES — all {int(counts["union_rows"]):,} locations are identical in both systems.",'
            f'"✗ DIFFERENCES FOUND — "&TEXT(SUM(Comparison!G2:G{last}),"#,##0")&'
            f'" differing cell(s), "&TEXT(COUNTIF(Comparison!F:F,"{only_a}")+'
            f'COUNTIF(Comparison!F:F,"{only_b}"),"#,##0")&'
            f'" one-sided row(s) — details below."),"{regenerate}")'
        )
    else:
        verdict = (
            f'=IF({freshness},"✗ DIFFERENCES FOUND — '
            f'{int(counts["differing_cells"]):,} differing cell(s), '
            f'{one_sided:,} one-sided row(s) — details below.","{regenerate}")'
        )
    line({"B": verdict})
    if formulas:
        line({"B": "Cell-by-cell comparison keyed on Route + PM (+ occurrence for "
                    "duplicates). Core Comparison/Summary/Spot formulas recalculate "
                    f"observed values after edits on the {side_a} / {side_b} sheets, "
                    "but row identity, duplicate assignment, and familiar views are "
                    "build-time state. ANY source/helper edit makes the Summary say "
                    "REGENERATE REQUIRED; only a newly generated workbook is certifying."})
    else:
        line({"B": "Cell-by-cell comparison keyed on Route + PM (+ occurrence for "
                    "duplicates). This copy holds plain VALUES — it opens instantly and "
                    "nothing needs calculating, but edits do NOT recalculate (the "
                    "live-formulas copy does that). The Spot Check sheet and the "
                    "SELF-CHECK rows below stay live."})
    line({"B": f"{side_a}: {spec['source_a']}      {side_b}: {spec['source_b']}      "
                f"created {CREATED_DATE}"}, advance=2)

    def banner(text: str) -> None:
        line({"B": text})

    def stat_line(label: str, formula: str, value: int) -> None:
        line({"B": label, "C": formula if formulas else value})

    banner("ROW COUNTS")
    stat_line(f"{side_a} data rows", f"=COUNTA({sa}!A:A)-1", int(counts["side_a_rows"]))
    stat_line(f"{side_b} data rows", f"=COUNTA({sb}!A:A)-1", int(counts["side_b_rows"]))
    stat_line("Union of locations compared", "=COUNT(Comparison!C:C)", int(counts["union_rows"]))
    banner("MATCH STATUS")
    stat_line("Locations in both systems", '=COUNTIF(Comparison!F:F,"Both")', int(counts["paired_rows"]))
    stat_line(
        f"In {side_a} only (missing from {side_b}) — listed on the 'Only in {side_a}' sheet",
        f'=COUNTIF(Comparison!F:F,"{only_a}")', int(counts["side_a_only_rows"]),
    )
    stat_line(
        f"In {side_b} only (missing from {side_a}) — listed on the 'Only in {side_b}' sheet",
        f'=COUNTIF(Comparison!F:F,"{only_b}")', int(counts["side_b_only_rows"]),
    )
    banner("ROUTE COVERAGE (see the Routes sheet for the per-route breakdown)")
    stat_line("Routes covered by both systems", '=COUNTIF(Routes!B:B,"Both")', int(counts["route_both"]))
    stat_line(f"Routes only in {side_a} (missing from {side_b})", f'=COUNTIF(Routes!B:B,"{only_a}")', int(counts["route_a_only"]))
    stat_line(f"Routes only in {side_b} (missing from {side_a})", f'=COUNTIF(Routes!B:B,"{only_b}")', int(counts["route_b_only"]))
    banner("FIELD-LEVEL DISCREPANCIES (matched rows)")
    stat_line(
        "Matched rows with ≥ 1 field difference",
        f'=COUNTIFS(Comparison!F2:F{last},"Both",Comparison!G2:G{last},">0")',
        int(counts["differing_rows"]),
    )
    stat_line(
        "Matched rows fully identical",
        f'=COUNTIFS(Comparison!F2:F{last},"Both",Comparison!G2:G{last},0)',
        int(counts["identical_rows"]),
    )
    stat_line("Total differing cells", f"=SUM(Comparison!G2:G{last})", int(counts["differing_cells"]))
    row += 1
    banner("DIFFERENCES BY FIELD")
    line({"B": "Field", "C": "Comparison col", "D": "# of cells differing"})
    field_first = row
    for position, (field, column) in enumerate(zip(FIELDS, COMPARISON_FIELD_COLUMN, strict=True), 1):
        value = (
            f'=SUMPRODUCT(--(MID(Comparison!$N$2:$N${last},{position},1)="D"))'
            if formulas else int(counts["per_field"][field])
        )
        line({"B": field, "C": column, "D": value})
    field_last = row - 1
    row += 1
    banner("SELF-CHECK (every row should read OK after calculation)")
    checks = [
        (
            f"Every Comparison row has a status (Both + {only_a} + {only_b})",
            f'COUNTIF(Comparison!F:F,"Both")+COUNTIF(Comparison!F:F,"{only_a}")+'
            f'COUNTIF(Comparison!F:F,"{only_b}")=COUNT(Comparison!C:C)',
        ),
        (
            f"Every row with {side_a} data found its {side_a} sheet row",
            f'COUNT(Comparison!D:D)=COUNTIF(Comparison!F:F,"Both")+'
            f'COUNTIF(Comparison!F:F,"{only_a}")',
        ),
        (
            f"Every row with {side_b} data found its {side_b} sheet row",
            f'COUNT(Comparison!E:E)=COUNTIF(Comparison!F:F,"Both")+'
            f'COUNTIF(Comparison!F:F,"{only_b}")',
        ),
        (
            f"'Only in {side_a}' sheet rows = {side_a}-only rows in the Comparison",
            f'COUNT({_sheet_ref(f"Only in {side_a}")}!C:C)='
            f'COUNTIF(Comparison!F:F,"{only_a}")',
        ),
        (
            f"'Only in {side_b}' sheet rows = {side_b}-only rows in the Comparison",
            f'COUNT({_sheet_ref(f"Only in {side_b}")}!C:C)='
            f'COUNTIF(Comparison!F:F,"{only_b}")',
        ),
        (
            "Per-field difference counts add up to the total differing cells",
            f"SUM(D{field_first}:D{field_last})=SUM(Comparison!G2:G{last})",
        ),
        ("Build-time source identity and duplicate pairing snapshot is current", freshness),
        (
            f"Routes sheet {side_a} row counts add up to the {side_a} sheet",
            f"SUM(Routes!C:C)=COUNTA({sa}!A:A)-1",
        ),
        (
            f"Routes sheet {side_b} row counts add up to the {side_b} sheet",
            f"SUM(Routes!D:D)=COUNTA({sb}!A:A)-1",
        ),
        (
            "Routes sheet 'Locations compared' adds up to the Comparison",
            "SUM(Routes!E:E)=COUNT(Comparison!C:C)",
        ),
    ]
    for label, condition in checks:
        line({"B": label, "C": f'=IF({condition},"OK","CHECK")'})
    row += 1
    banner("HOW TO READ / NOTES")
    notes = [
        "• Comparison sheet: matching values are shown in plain text; a red cell "
        f"shows  {side_a} value{DIFF_MARK}{side_b} value  where the two systems "
        "disagree for that PM and field.",
        '• "(blank)" means the cell is empty in that system. Filter the Diffs '
        "column (>0) to isolate rows needing review.",
        f"• Yellow rows exist only in {side_a}; blue rows exist only in {side_b}"
        f"{spec['one_sided_note_extra']}. Their field cells show that system's own values.",
        f"• The 'Only in {side_a}' and 'Only in {side_b}' sheets repeat every "
        "one-sided row in one place — including the rows of routes the other system "
        "doesn't carry at all (flagged 'entire route' and tinted; filter the "
        "'Missing from …' column to separate whole-route gaps from single locations). "
        "The Comparison sheet still contains the same rows in document order.",
        "• Rows pair on Route plus PM plus occurrence number. When a postmile is "
        "listed more than once, the matching instances are paired by which are MOST "
        "ALIKE (fewest differing fields), not by the order they appear — so a repeat "
        "that matches the other side's second listing isn't flagged as a difference.",
        "• Leading/trailing spaces are ignored (TRIM).",
        '• Lookups use the "Key (helper)" column (J) on each data sheet. It '
        "contains a versioned opaque build token, not flattened Route/key text, so "
        "punctuation inside identity components cannot collide.",
        "• Very-hidden E2 snapshot sheets retain the exact build-time source and "
        "helper cells. The Summary freshness check turns non-certifying after any "
        "source edit, row insertion/deletion/reorder, or helper change.",
        f"• Doubting a value? The blue row numbers in the '{side_a} Row' / "
        f"'{side_b} Row' columns are clickable — they jump to the data sheet and "
        "SELECT that whole row (it stays highlighted until you click elsewhere), and "
        "each data-sheet row links back to its Comparison row the same way. The Spot "
        "Check sheet audits any single location end to end: raw values from both "
        "systems and an independently recomputed verdict for every field.",
    ]
    if not formulas:
        notes.append(
            "• This is the VALUES copy: every number and comparison cell is a computed "
            "result, not a formula (only the Spot Check sheet and the SELF-CHECK rows "
            "stay live). If the data changes, re-create the comparison — or use the "
            "live-formulas copy, which recalculates."
        )
    notes.extend([
        "• SELF-CHECK recomputes the headline numbers a second, independent way; a "
        "CHECK there means the sheets no longer agree (e.g. rows were inserted or "
        "deleted on a data sheet) — re-create the report rather than trust the numbers.",
        "• The Routes sheet lists every route either system carries — which side covers "
        "it, row counts, and how much of it differs.",
    ])
    if formulas:
        notes.append(
            "• CALCULATION IS SET TO MANUAL (large workbook): cells show blank/0 until "
            "you press F9. The first F9 takes a few minutes — let it finish, then save "
            "to keep the results; edits afterwards only recalculate when you press F9 "
            "again. (Excel keeps the manual setting for other workbooks opened in the "
            "same session — Formulas → Calculation Options switches it back.)"
        )
    for note in notes:
        line({"B": note})
    return result


def _spot_raw(side: str, column: str, row_ref: str) -> str:
    index = f"INDEX({_sheet_ref(side)}!{column}:{column},{row_ref})"
    return f'=IF({row_ref}="","",IFERROR(IF(ISBLANK({index}),"",{index}),""))'


def _spot_expected_display(
    side_a: str, side_b: str, source_column: str, row: int, context: bool,
) -> str:
    left = _trim_ref(side_a, source_column, "$C$12")
    right = _trim_ref(side_b, source_column, "$F$12")
    independent = (
        f'IF($C$12="","{side_b} only",IF($F$12="","{side_a} only","Both"))'
    )
    if context:
        matched = f'IF({left}="",{right},{left})'
    else:
        show_left = f'IF({left}="","(blank)",{left})'
        show_right = f'IF({right}="","(blank)",{right})'
        matched = f'IF($K{row}="D",{show_left}&"{DIFF_MARK}"&{show_right},{left})'
    display = (
        f'IF({independent}="{side_a} only",{left},'
        f'IF({independent}="{side_b} only",{right},{matched}))'
    )
    return f'=IF($C$11="","",{display})'


def _expected_spot_map(
    spec: dict[str, object], counts: dict[str, object], selected: UnionRow,
    *, formulas: bool,
) -> dict[str, tuple[str, object]]:
    side_a, side_b = str(spec["side_a"]), str(spec["side_b"])
    only_a, only_b = f"{side_a} only", f"{side_b} only"
    last = int(counts["union_rows"]) + 1
    result: dict[str, tuple[str, object]] = {}

    def put(row: int, column: int, value: object) -> None:
        _map_put(result, f"{_column_letter(column)}{row}", value)

    def banner(row: int, text: str) -> None:
        put(row, 2, text)
        for column in range(3, 11):
            put(row, column, "")

    put(2, 2, "Spot Check — audit any single location")
    put(3, 2, "Every value below recomputes for the row you pick. The "
               "'Independent verdict' column re-compares the two data sheets "
               "directly (TRIM) WITHOUT reading the Comparison sheet — Agree? = OK "
               "means both computations reached the same answer.")
    put(4, 2, f"In difference cells the order is always:   {side_a} value"
               f"{DIFF_MARK}{side_b} value   ({side_a} first, {side_b} second).")
    if formulas:
        put(5, 2, "▶ PRESS F9 AFTER EVERY CHANGE — this workbook calculates manually, "
                  "so nothing updates until you do.")
    put(6, 2, f"Comparison row # to check (2–{last}):")
    put(6, 3, selected.physical_row)
    put(6, 4, "← type a row number" + (", then press F9" if formulas else " (updates instantly)"))
    put(7, 2, "…or find one:")
    put(7, 3, "Route:")
    put(7, 4, selected.route)
    put(7, 5, "PM:")
    put(7, 6, selected.location)
    put(7, 7, "Occ #:")
    put(7, 8, selected.occurrence)
    find = (
        f"SUMPRODUCT((Comparison!$A$2:$A${last}=$D$7)"
        f"*(Comparison!$B$2:$B${last}=$F$7)"
        f"*(Comparison!$C$2:$C${last}=$H$7)"
        f"*ROW(Comparison!$A$2:$A${last}))"
    )
    put(7, 9, "→ Comparison row:")
    put(7, 10, f'=IF({find}=0,"not found",{find})')
    banner(9, "WHAT THE COMPARISON SHEET SHOWS FOR THAT ROW")

    def cmp_index(column: str) -> str:
        return f"INDEX(Comparison!${column}:${column},$C$6)"

    put(10, 2, "Route:")
    put(10, 3, f'=IFERROR({cmp_index("A")},"")')
    put(10, 5, "PM:")
    put(10, 6, f'=IFERROR({cmp_index("B")},"")')
    put(10, 8, "Occurrence #:")
    put(10, 9, f'=IFERROR({cmp_index("C")},"")')
    put(11, 2, "Status:")
    put(11, 3, f'=IFERROR({cmp_index("F")},"")')
    put(11, 5, "Diffs counted:")
    put(11, 6, f'=IFERROR({cmp_index("G")},"")')
    put(12, 2, f"{side_a} sheet row:")
    put(12, 3, f'=IFERROR(IF({cmp_index("D")}="","",HYPERLINK("#'
                   f'{_sheet_ref(side_a)}!"&{cmp_index("D")}&":"&{cmp_index("D")},'
                   f'{cmp_index("D")})),"")')
    put(12, 5, f"{side_b} sheet row:")
    put(12, 6, f'=IFERROR(IF({cmp_index("E")}="","",HYPERLINK("#'
                   f'{_sheet_ref(side_b)}!"&{cmp_index("E")}&":"&{cmp_index("E")},'
                   f'{cmp_index("E")})),"")')
    put(13, 2, f'=IF($C$11="{only_a}","⚠ THIS LOCATION EXISTS ONLY IN '
                   f'{side_a} — there is no {side_b} row to compare; {side_b} values '
                   f'below are blank.",IF($C$11="{only_b}","⚠ THIS LOCATION EXISTS '
                   f'ONLY IN {side_b} — there is no {side_a} row to compare; {side_a} '
                   f'values below are blank.",""))')

    # Product defect CMP-AUD-214: this banner is written first, then B:G are
    # overwritten by headers at the same row.  H:J survive only as blank cells.
    banner(15, "FIELD BY FIELD — RECOMPUTED FROM THE DATA SHEETS "
               "(independent of the Comparison sheet)")
    headers = [
        "Field", f"{side_a} value (as stored)", f"{side_b} value (as stored)",
        "Independent verdict", f"Comparison sheet shows ({side_a}{DIFF_MARK}{side_b})",
        "Agree?",
    ]
    for offset, value in enumerate(headers, start=2):
        coordinate = f"{_column_letter(offset)}15"
        result[coordinate] = ("s", value)
    put(15, 11, "__CMP_E1_STATE_V1_SPOT_INDEPENDENT_STATE")
    put(15, 12, "__CMP_E1_STATE_V1_SPOT_EXPECTED_DISPLAY")
    put(15, 13, "__CMP_E1_STATE_V1_SPOT_COMPARISON_STATE")
    independent_status = (
        f'IF($C$12="","{only_b}",IF($F$12="","{only_a}","Both"))'
    )
    for position, (field, source_column, comparison_column) in enumerate(
        zip(FIELDS, SOURCE_FIELD_COLUMN, COMPARISON_FIELD_COLUMN, strict=True)
    ):
        row = 16 + position
        left = _trim_ref(side_a, source_column, "$C$12")
        right = _trim_ref(side_b, source_column, "$F$12")
        put(row, 2, field)
        put(row, 3, _spot_raw(side_a, source_column, "$C$12"))
        put(row, 4, _spot_raw(side_b, source_column, "$F$12"))
        put(row, 5, f'=IF($C$11="","",IF($K{row}="U",{independent_status},'
                    f'IF($K{row}="D","DIFFERENT","match")))')
        put(row, 6, f'=IFERROR(IF(ISBLANK(INDEX(Comparison!{comparison_column}:'
                    f'{comparison_column},$C$6)),"",INDEX(Comparison!{comparison_column}:'
                    f'{comparison_column},$C$6)),"")')
        put(row, 7, f'=IF($C$11="","",IF(AND(EXACT($K{row},$M{row}),'
                    f'EXACT($L{row},$F{row})),"OK","CHECK"))')
        if position in CONTEXT_POSITIONS:
            state = f'=IF($C$11="","",IF(AND($C$12<>"",$F$12<>""),"N","U"))'
        else:
            state = (
                f'=IF($C$11="","",IF(AND($C$12<>"",$F$12<>""),'
                f'IF(EXACT({left},{right}),"E","D"),"U"))'
            )
        put(row, 11, state)
        put(row, 12, _spot_expected_display(
            side_a, side_b, source_column, row, position in CONTEXT_POSITIONS,
        ))
        put(row, 13, f'=IFERROR(IF($C$11="","",MID(INDEX(Comparison!$N:$N,'
                     f'$C$6),{position + 1},1)),"")')
    put(23, 2, f"• On rows that exist in only one system the verdict column shows "
               f"'{only_a}' / '{only_b}' on every field; Agree? then verifies the "
               "displayed value against that system's data sheet.")
    put(24, 2, "• The blue row numbers jump to the source row on the data sheets "
               "and select the whole row so it stands out — it un-highlights when "
               "you click elsewhere. Each data-sheet row links back to its "
               "Comparison row. Values are shown exactly as stored (before TRIM).")
    return result


def _require_exact_map(
    label: str, observed: dict[str, tuple[str, object]],
    expected: dict[str, tuple[str, object]],
) -> str:
    if observed != expected:
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        changed = sorted(
            coordinate for coordinate in set(observed) & set(expected)
            if observed[coordinate] != expected[coordinate]
        )
        detail = {"missing": missing[:10], "extra": extra[:10], "changed": changed[:10]}
        raise AuditError(f"{label}: exact cell map drift: {detail}")
    return hashlib.sha256(_canonical([
        [coordinate, *observed[coordinate]] for coordinate in sorted(observed)
    ])).hexdigest()


def _typed_counts_from_result(record: dict[str, object]) -> dict[str, object]:
    result = record.get("result")
    if not isinstance(result, dict) or result.get("status") != "ok" or result.get("completion") != "complete":
        raise AuditError("witness result is not a complete ok terminal")
    counts = result.get("counts")
    if not isinstance(counts, dict) or counts.get("known") is not True:
        raise AuditError("witness result lacks known typed counts")
    return counts


def _compare_result_counts(
    label: str, typed: dict[str, object], observed: dict[str, object],
) -> None:
    expected = {
        "paired_rows": observed["paired_rows"],
        "side_a_only_rows": observed["side_a_only_rows"],
        "side_b_only_rows": observed["side_b_only_rows"],
        "differing_rows": observed["differing_rows"],
        "differing_cells": observed["differing_cells"],
    }
    if {key: typed.get(key) for key in expected} != expected:
        raise AuditError(f"{label}: persisted typed counts disagree with reconstruction")
    per_field = typed.get("per_field_counts")
    if not isinstance(per_field, dict):
        raise AuditError(f"{label}: typed per-field counts absent")
    expected_fields = {
        f"{index}:" + field: observed["per_field"][field]
        for index, field in zip((0, 2, 3, 4, 5, 6), FIELDS, strict=True)
    }
    if per_field != expected_fields:
        raise AuditError(f"{label}: typed per-field counts disagree")


def _bind_declared_file(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise AuditError(f"{label}: malformed identity")
    capture = CapturedFile.capture(Path(str(value["path"])))
    if capture.identity != value:
        raise AuditError(f"{label}: declared identity drift")
    capture.assert_unchanged()
    return capture.identity


def _bind_witness_result(
    label: str, spec: dict[str, object],
) -> tuple[CapturedFile, dict[str, object], dict[str, object]]:
    path = VISUAL_ROOT / str(spec["root"]) / "result.json"
    capture = CapturedFile.capture(path)
    if capture.identity["bytes"] != spec["bytes"] or capture.identity["sha256"] != spec["sha256"]:
        raise AuditError(f"{label}: frozen result identity drift")
    record = _strict_json(capture)
    if record.get("leg") != label or Path(str(record.get("output_root", ""))).resolve() != path.parent.resolve():
        raise AuditError(f"{label}: result envelope/output root drift")
    inputs = record.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise AuditError(f"{label}: result input map absent")
    after = record.get("inputs_after")
    if after != inputs:
        raise AuditError(f"{label}: runner input pre/post identities disagree")
    authenticated_inputs = {
        name: _bind_declared_file(value, f"{label} input/{name}")
        for name, value in inputs.items()
    }
    capture.assert_unchanged()
    return capture, record, authenticated_inputs


def _spot_dependency_and_mutations(
    spec: dict[str, object], spot: dict[str, tuple[str, object]],
    selected: UnionRow, rows_a: list[SourceRow], rows_b: list[SourceRow],
) -> dict[str, object]:
    side_a, side_b = str(spec["side_a"]), str(spec["side_b"])
    formulas = {coordinate: value for coordinate, (kind, value) in spot.items() if kind == "f"}
    required = {
        "C11": '=IFERROR(INDEX(Comparison!$F:$F,$C$6),"")',
        "C12": None, "F12": None,
    }
    if formulas.get("C11") != required["C11"]:
        raise AuditError("Spot C11 no longer derives status from Comparison")
    for coordinate, comparison_column in (("C12", "D"), ("F12", "E")):
        formula = str(formulas.get(coordinate, ""))
        if f"INDEX(Comparison!${comparison_column}:${comparison_column},$C$6)" not in formula:
            raise AuditError(f"Spot {coordinate} no longer derives row from Comparison")
    field_formulas = "\n".join(
        str(formulas[coordinate])
        for row in range(16, 22)
        for coordinate in (f"C{row}", f"D{row}", f"E{row}", f"G{row}", f"K{row}", f"L{row}", f"M{row}")
    )
    if not all(token in field_formulas for token in ("$C$11", "$C$12", "$F$12")):
        raise AuditError("Spot field audit lost the Comparison-derived dependency chain")
    if any(token in field_formulas for token in ("$D$7", "$F$7", "$H$7")):
        raise AuditError("Spot field audit unexpectedly uses its displayed key inputs")
    if selected.left_index is None or selected.right_index is None:
        raise AuditError("Spot default is not a paired differing row")
    left = rows_a[selected.left_index]
    original_right = rows_b[selected.right_index]
    alternative_index = next(
        index for index, row in enumerate(rows_b)
        if row.route != selected.route or row.location != selected.location
    )
    alternative_right = rows_b[alternative_index]
    wrong_displays, wrong_mask = _field_projection(left, alternative_right)

    def spot_recompute(
        supplied_left: SourceRow | None, supplied_right: SourceRow | None,
    ) -> tuple[tuple[str, ...], str]:
        """Independent Python evaluation of what Spot's K/L cells compute."""
        if supplied_left is None and supplied_right is None:
            raise AuditError("synthetic Spot mutation has neither supplied row")
        left_fields = None if supplied_left is None else supplied_left.fields
        right_fields = None if supplied_right is None else supplied_right.fields
        states: list[str] = []
        displays: list[str] = []
        for position in range(len(FIELDS)):
            value_a = "" if left_fields is None else left_fields[position]
            value_b = "" if right_fields is None else right_fields[position]
            if supplied_left is None:
                states.append("U")
                displays.append(value_b)
            elif supplied_right is None:
                states.append("U")
                displays.append(value_a)
            elif position in CONTEXT_POSITIONS:
                states.append("N")
                displays.append(value_a if value_a else value_b)
            elif value_a == value_b:
                states.append("E")
                displays.append(value_a)
            else:
                states.append("D")
                displays.append(
                    f"{value_a or '(blank)'}{DIFF_MARK}{value_b or '(blank)'}"
                )
        return tuple(displays), "".join(states)

    spot_wrong_displays, spot_wrong_mask = spot_recompute(left, alternative_right)
    wrong_pair_agree = [
        spot_state == comparison_state and spot_display == comparison_display
        for spot_state, comparison_state, spot_display, comparison_display in zip(
            spot_wrong_mask, wrong_mask,
            spot_wrong_displays, wrong_displays, strict=True,
        )
    ]
    # A false one-sided Comparison row suppresses the real right link.  Spot
    # sees C11/C12/F12 from that row, derives U from the missing F12, and agrees
    # with Comparison's equally wrong U/display cells.
    false_one_sided_displays, false_one_sided_mask = _field_projection(left, None)
    spot_one_sided_displays, spot_one_sided_mask = spot_recompute(left, None)
    false_one_sided_agree = [
        spot_state == comparison_state and spot_display == comparison_display
        for spot_state, comparison_state, spot_display, comparison_display in zip(
            spot_one_sided_mask, false_one_sided_mask,
            spot_one_sided_displays, false_one_sided_displays, strict=True,
        )
    ]
    if not all(wrong_pair_agree) or not all(false_one_sided_agree):
        raise AuditError("Spot dependency negative-control construction failed")
    return {
        "claim_is_independent": False,
        "comparison_supplies_status_cell": "C11 <- Comparison!F[C6]",
        "comparison_supplies_source_row_cells": [
            "C12 <- Comparison!D[C6]", "F12 <- Comparison!E[C6]",
        ],
        "field_audit_uses_comparison_derived_cells": ["$C$11", "$C$12", "$F$12"],
        "field_audit_does_not_use_displayed_key_inputs": ["$D$7", "$F$7", "$H$7"],
        "wrong_pair_mutation": {
            "comparison_identity_retained": [selected.route, selected.location, selected.occurrence],
            "left_source_identity": [left.route, left.location],
            "original_right_source_identity": [original_right.route, original_right.location],
            "mutated_right_source_identity": [alternative_right.route, alternative_right.location],
            "mutated_right_row": alternative_index + 2,
            "identity_is_wrong": [alternative_right.route, alternative_right.location]
            != [selected.route, selected.location],
            "comparison_state_and_display_recomputed_for_wrong_pair": True,
            "spot_agree_results": ["OK" for _ in wrong_pair_agree],
        },
        "false_one_sided_mutation": {
            "real_right_row_exists": selected.right_index + 2,
            "comparison_status_mutated_to": f"{side_a} only",
            "comparison_right_link_suppressed": True,
            "comparison_state_mask_mutated_to": false_one_sided_mask,
            "spot_agree_results": ["OK" for _ in false_one_sided_agree],
        },
        "all_twelve_consistently_wrong_mutation_checks_still_say_ok": (
            all(wrong_pair_agree) and all(false_one_sided_agree)
        ),
    }


def _mutation_self_tests() -> dict[str, bool]:
    base = {"B2": ("s", "x"), "C3": ("n", 1)}

    def rejected(candidate):
        try:
            _require_exact_map("synthetic", candidate, base)
        except AuditError:
            return True
        return False

    tests = {
        "cell_value_mutation_rejected": rejected({"B2": ("s", "y"), "C3": ("n", 1)}),
        "cell_type_mutation_rejected": rejected({"B2": ("f", "x"), "C3": ("n", 1)}),
        "missing_cell_rejected": rejected({"B2": ("s", "x")}),
        "extra_cell_rejected": rejected({**base, "D4": ("s", "extra")}),
    }
    if not all(tests.values()):
        raise AuditError("internal exact-map mutation test failed")
    return tests


def _audit_leg(label: str, spec: dict[str, object]) -> dict[str, object]:
    result_capture, record, inputs = _bind_witness_result(label, spec)
    outputs = record.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != {"formulas", "values"}:
        raise AuditError(f"{label}: output identity map drift")
    formula_capture = CapturedFile.capture(Path(str(outputs["formulas"]["path"])))
    values_capture = CapturedFile.capture(Path(str(outputs["values"]["path"])))
    if formula_capture.identity != outputs["formulas"] or values_capture.identity != outputs["values"]:
        raise AuditError(f"{label}: output workbook identity drift")
    side_a, side_b = str(spec["side_a"]), str(spec["side_b"])
    required_sheets = {
        "Summary", "Spot Check", "Comparison", "Routes",
        f"Only in {side_a}", f"Only in {side_b}", side_a, side_b,
        "Notes", "__CMP_E2_SNAPSHOT_A", "__CMP_E2_SNAPSHOT_B",
    }
    with XlsxBytes(values_capture) as values_wb, XlsxBytes(formula_capture) as formula_wb:
        if set(values_wb.sheets) != required_sheets or set(formula_wb.sheets) != required_sheets:
            raise AuditError(f"{label}: workbook sheet universe drift")
        if formula_wb.calc.get("calcMode") != "manual":
            raise AuditError(f"{label}: formula workbook is not manual-calc")
        rows_a, source_a = _parse_source_sheet(
            values_wb, side_a, "__CMP_E2_SNAPSHOT_A",
        )
        rows_b, source_b = _parse_source_sheet(
            values_wb, side_b, "__CMP_E2_SNAPSHOT_B",
        )
        snapshot_a = _parse_snapshot(
            values_wb, "__CMP_E2_SNAPSHOT_A", rows_a,
        )
        snapshot_b = _parse_snapshot(
            values_wb, "__CMP_E2_SNAPSHOT_B", rows_b,
        )
        union, counts, selected = _parse_value_comparison(
            values_wb, side_a, side_b, rows_a, rows_b,
        )
        typed = _typed_counts_from_result(record)
        _compare_result_counts(label, typed, counts)
        formula_comparison = _parse_formula_comparison(
            formula_wb, side_a, side_b, union,
        )

        summary_values = values_wb.sheet_cell_map("Summary")
        summary_formulas = formula_wb.sheet_cell_map("Summary")
        spot_values = values_wb.sheet_cell_map("Spot Check")
        spot_formulas = formula_wb.sheet_cell_map("Spot Check")
        summary_values_hash = _require_exact_map(
            f"{label} values Summary", summary_values,
            _expected_summary_map(spec, counts, formulas=False),
        )
        summary_formulas_hash = _require_exact_map(
            f"{label} formulas Summary", summary_formulas,
            _expected_summary_map(spec, counts, formulas=True),
        )
        spot_values_expected = _expected_spot_map(
            spec, counts, selected, formulas=False,
        )
        spot_formulas_expected = _expected_spot_map(
            spec, counts, selected, formulas=True,
        )
        spot_values_hash = _require_exact_map(
            f"{label} values Spot", spot_values, spot_values_expected,
        )
        spot_formulas_hash = _require_exact_map(
            f"{label} formulas Spot", spot_formulas, spot_formulas_expected,
        )
        parity_differences = {
            coordinate
            for coordinate in set(spot_values) | set(spot_formulas)
            if spot_values.get(coordinate) != spot_formulas.get(coordinate)
        }
        if parity_differences != {"B5", "D6"}:
            raise AuditError(
                f"{label}: Spot formula/value parity drift {sorted(parity_differences)}"
            )

        styleless_twins = {}
        for sheet in (side_a, side_b, "__CMP_E2_SNAPSHOT_A", "__CMP_E2_SNAPSHOT_B"):
            left = formula_wb.styleless_member_digest(sheet)
            right = values_wb.styleless_member_digest(sheet)
            if {
                key: left[key] for key in ("styleless_xml_bytes", "styleless_xml_sha256")
            } != {
                key: right[key] for key in ("styleless_xml_bytes", "styleless_xml_sha256")
            }:
                raise AuditError(f"{label}: formula/value source twin drift on {sheet}")
            styleless_twins[sheet] = left

        # CMP-AUD-214 must remain explicit and red in every current witness.
        intended_banner = (
            "FIELD BY FIELD — RECOMPUTED FROM THE DATA SHEETS "
            "(independent of the Comparison sheet)"
        )
        banner_cells = {
            "values": [
                coordinate for coordinate, (_kind, value) in spot_values.items()
                if value == intended_banner
            ],
            "formulas": [
                coordinate for coordinate, (_kind, value) in spot_formulas.items()
                if value == intended_banner
            ],
        }
        if (
            banner_cells != {"values": [], "formulas": []}
            or spot_values.get("B15") != ("s", "Field")
            or spot_formulas.get("B15") != ("s", "Field")
        ):
            raise AuditError(f"{label}: CMP-AUD-214 expected-red signature drift")
        dependency = _spot_dependency_and_mutations(
            spec, spot_values, selected, rows_a, rows_b,
        )
        formula_dependency = _spot_dependency_and_mutations(
            spec, spot_formulas, selected, rows_a, rows_b,
        )
        if formula_dependency != dependency:
            raise AuditError(f"{label}: Spot dependency differs across twins")

    formula_capture.assert_unchanged()
    values_capture.assert_unchanged()
    result_capture.assert_unchanged()
    return {
        "witness_result": result_capture.identity,
        "inputs": inputs,
        "outputs": {
            "formulas": formula_capture.identity,
            "values": values_capture.identity,
        },
        "source_sheets": {side_a: source_a, side_b: source_b},
        "snapshots": {
            "__CMP_E2_SNAPSHOT_A": snapshot_a,
            "__CMP_E2_SNAPSHOT_B": snapshot_b,
        },
        "formula_value_source_snapshot_twins": styleless_twins,
        "comparison": {
            "counts": counts,
            "values_cells_reconstructed": int(counts["union_rows"]) * 14,
            "every_values_cell_exact_to_embedded_sources": True,
            "formulas": formula_comparison,
            "source_backlinks_exact": True,
        },
        "summary": {
            "values_exact_cell_map_sha256": summary_values_hash,
            "formulas_exact_cell_map_sha256": summary_formulas_hash,
            "every_label_formula_value_and_section_boundary_exact": True,
            "counts_reconstructed_from_comparison_not_result": True,
            "typed_result_counts_agree": True,
        },
        "spot_check": {
            "selected_comparison_row": selected.physical_row,
            "selected_key": [selected.route, selected.location, selected.occurrence],
            "selected_status": selected.status,
            "selected_diffs": selected.diffs,
            "selected_state_mask": selected.state_mask,
            "selected_displays": list(selected.displays),
            "values_exact_cell_map_sha256": spot_values_hash,
            "formulas_exact_cell_map_sha256": spot_formulas_hash,
            "formula_value_parity_exact_except_documented_manual_instructions": True,
            "formula_value_parity_difference_cells": ["B5", "D6"],
            "all_six_field_states_displays_verdicts_reconstructed": True,
            "source_rows_and_snapshots_exact": True,
        },
        "expected_product_defects": {
            "CMP-AUD-214": {
                "present": True,
                "row_15_B_cell": "Field",
                "intended_banner_cells": banner_cells,
                "field_table_calculations_intact": True,
            },
            "CMP-AUD-218": dependency,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="perform the complete audit but do not write the result artifact",
    )
    args = parser.parse_args(argv)
    script_capture = CapturedFile.capture(Path(__file__))
    legs = {}
    for label, spec in RESULT_SPECS.items():
        print(f"Auditing {label} ...", flush=True)
        legs[label] = _audit_leg(label, spec)
    mutation_tests = _mutation_self_tests()
    verified = {
        "all_five_bound_witness_results_authenticated": len(legs) == 5,
        "all_ten_workbook_payloads_captured_hashed_and_inspected_from_same_bytes": True,
        "all_declared_source_inputs_authenticated": all(bool(item["inputs"]) for item in legs.values()),
        "all_values_comparison_cells_reconstructed_from_embedded_sources": all(
            item["comparison"]["every_values_cell_exact_to_embedded_sources"]
            for item in legs.values()
        ),
        "all_formula_comparison_cells_reconstructed_exactly": all(
            item["comparison"]["formulas"]["every_formula_and_literal_cell_exact"]
            for item in legs.values()
        ),
        "all_source_rows_snapshots_and_backlinks_exact": all(
            item["comparison"]["source_backlinks_exact"]
            and all(snapshot["every_snapshot_row_and_value_exact"]
                    for snapshot in item["snapshots"].values())
            for item in legs.values()
        ),
        "all_summary_cell_maps_semantically_exact_and_exhaustive": all(
            item["summary"]["every_label_formula_value_and_section_boundary_exact"]
            for item in legs.values()
        ),
        "all_spot_cell_maps_selected_rows_and_six_fields_exact": all(
            item["spot_check"]["all_six_field_states_displays_verdicts_reconstructed"]
            for item in legs.values()
        ),
        "cmp_aud_214_banner_overwrite_present_in_all_ten_workbooks": all(
            item["expected_product_defects"]["CMP-AUD-214"]["present"]
            for item in legs.values()
        ),
        "cmp_aud_218_comparison_dependency_present_in_all_ten_workbooks": all(
            not item["expected_product_defects"]["CMP-AUD-218"]["claim_is_independent"]
            for item in legs.values()
        ),
        "cmp_aud_218_wrong_pair_and_status_mutations_falsely_say_ok_everywhere": all(
            item["expected_product_defects"]["CMP-AUD-218"]
            ["all_twelve_consistently_wrong_mutation_checks_still_say_ok"]
            for item in legs.values()
        ),
        "audit_exact_map_negative_controls_pass": all(mutation_tests.values()),
        "acceptance_boundary_explicit": True,
    }
    if not all(verified.values()):
        raise AuditError("final Summary/Spot invariant is red unexpectedly")
    result = {
        "audit": "Stage 8 Highway Sequence Summary and Spot Check semantic audit",
        "status": "pass_with_expected_product_defects",
        "acceptance_artifact": False,
        "reason_not_acceptance": (
            "This development witness audits frozen current product outputs. "
            "CMP-AUD-214 and CMP-AUD-218 remain product-red, raw-TSN legs use a "
            "cache-derived development twin, and final acceptance still requires "
            "direct immutable-PDF replay plus corrected Summary/Spot workbooks."
        ),
        "checker": script_capture.identity,
        "legs": legs,
        "negative_controls": mutation_tests,
        "verified_invariants": verified,
    }
    script_capture.assert_unchanged()
    payload = _json_line(result)
    if args.dry_run:
        print(
            "PASS (dry-run) Highway Sequence Summary/Spot audit: "
            f"{len(payload):,} bytes sha256={hashlib.sha256(payload).hexdigest()}"
        )
        return 0
    output = args.output.expanduser().resolve()
    if output.exists():
        raise AuditError(f"refusing to overwrite existing audit artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=False)
    with output.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    written = CapturedFile.capture(output)
    if written.payload != payload:
        raise AuditError("written audit artifact does not equal computed payload")
    written.assert_unchanged()
    print(
        "PASS Highway Sequence Summary/Spot audit: "
        f"{written.identity['path']} ({written.identity['bytes']:,} bytes, "
        f"sha256={written.identity['sha256']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"FAIL Highway Sequence Summary/Spot audit: {exc}")
        raise SystemExit(1)

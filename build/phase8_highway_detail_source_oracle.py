#!/usr/bin/env python3
"""Independent Stage-8 Highway Detail source oracle.

This audit path deliberately imports no application parser, consolidator,
comparator, schema, or evidence module.  TSMIS Excel is read with the generic
OOXML stream reader.  TSMIS PDF is reconstructed from pdfplumber *words* and
the exact rectangle topology of each printed layout block.  Production instead
groups/assigns PDF characters and, on bandless pages, falls back to a
document-median grid.  The different extraction path is important: a product
parser must not define the facts used to certify itself.

The July 2026 Highway Detail PDF export dynamically sizes its columns once per
logical print page.  A logical page is sometimes split across two physical PDF
pages.  Only shaded rows expose cell rectangles, so one physical continuation
page can lack a 10-cell first-line band even though its 25-cell second-line
band still identifies the exact shared grid.  This oracle groups physical
pages by their printed ``Ref Date / Route / Page`` header, proves the grid is
uniform inside that block, derives the 10-cell grid from the 25-cell base grid,
and validates every observed 10-cell band against that derivation.  It never
uses a document-wide median.

The file is the source layer for the eventual full comparison/evidence gate.
``--probe-member`` is intentionally diagnostic-only and cannot produce an
accepted statewide result.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib
import json
import logging
from pathlib import Path
import re
import sys
from typing import Iterable, Sequence

import pdfplumber


BUILD_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_ROOT))

from phase3_xlsx_stream import (  # noqa: E402
    SCALAR,
    ColumnSpec,
    SheetSpec,
    read_sheet,
)


PRIVATE_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
    r"\phase8_highway_detail_private_sources_r1"
)
DEFAULT_XLSX_ROOT = PRIVATE_ROOT / "tsmis_excel"
DEFAULT_PDF_ROOT = PRIVATE_ROOT / "tsmis_pdf"
DEFAULT_OUTPUT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
    r"\phase8_highway_detail_source_oracle_draft.json"
)

TREE_BINDINGS = {
    "tsmis_excel": {
        "suffix": ".xlsx", "files": 252, "bytes": 65_195_848,
        "manifest_sha256": (
            "ca8e8a9478d00ed5514eb4026cd4b54f1d2df373bcdfff18e04898f60e852848"),
    },
    "tsmis_pdf": {
        "suffix": ".pdf", "files": 252, "bytes": 50_624_128,
        "manifest_sha256": (
            "590aad859c46be2044cc116e3a563b7f3224a13fb63039e34d49569dfd994480"),
    },
}

TSMIS_HEADERS = (
    "Post Mile", "Length", "Date of Rec", "HG", "AC", "Acc-Cont Eff",
    "City", "RU", "RU Eff", "Description", "NA", "LB Eff", "LB S/T",
    "LB #Ln", "LB S/F", "LB OT-TO", "LB OT-TR", "LB Wid", "LB IN-TO",
    "LB IN-TR", "Med Eff", "Med T", "Med C", "Med B", "Med V/WDA",
    "RB Eff", "RB S/T", "RB #Ln", "RB S/F", "RB IN-TO", "RB IN-TR",
    "RB Wid", "RB OT-TO", "RB OT-TR",
)
TSMIS_SPEC = SheetSpec(
    "Highway Detail",
    tuple(ColumnSpec(header, SCALAR) for header in TSMIS_HEADERS),
    exact_schema=True,
)

MEMBER_RE = re.compile(r"^highway_detail_route_(\d{3}[A-Za-z]?)\.(?:xlsx|pdf)$")
PRINT_HEADER_RE = re.compile(
    r"Ref\s+Date:\s*(\d{4}-\d{2}-\d{2})\s+Route\s+"
    r"(\d{1,3}[A-Za-z]?)\s+Page\s+(\d+)", re.IGNORECASE)
DCR_RE = re.compile(
    r"^(\d{1,2}|[\u2014\u2013-])\s+([A-Z]{2,3})\.?\s+(\d{1,3}[A-Z]?)$")
PM_RE = re.compile(r"^[A-Z]{0,2}\d{1,3}\.\d{3}[A-Z]{0,2}$")
LENGTH_RE = re.compile(r"^(?:\d{3}\.\d{3}|-\d{1,3}\.\d{3}|\d-\d\.\d{3})$")
DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}$")
REPORT_DATE_RE = re.compile(r"REPORT\s+DATE\s*:\s*(\d{1,2}/\d{1,2}/\d{4})")
REFERENCE_DATE_RE = re.compile(
    r"REFERENCE\s+DATE\s*:\s*(\d{1,2}/\d{1,2}/\d{4})")

PDF_LEFT_EDGE = 27.75
PDF_RIGHT_EDGE = 764.25
PDF_GRID_QUANTUM = 0.75
WORD_LINE_TOLERANCE = 2.25
WRAP_GAP_MAX = 7.5
LINE1_FROM_LINE2 = (0, 1, 3, 5, 6, 7, 9, 11, 12, 14, 25)
LINE2_HEADER_LABELS = (
    "EFF-DATE", "T", "LN", "F", "TO", "TR", "WID", "TO", "TR",
    "EFF-DATE", "T", "C", "B", "WDA", "EFF-DATE", "T", "LN", "F",
    "TO", "TR", "WID", "TO", "TR",
)
LINE1_HEADER_LABELS = (
    "POST", "MILE", "LENGTH", "RECORD", "G", "C", "EFF-DATE",
    "CODE", "U", "EFF-DATE",
)


class AuditError(RuntimeError):
    """The frozen source or its independently derived contract drifted."""


@dataclass(frozen=True)
class FileEntry:
    name: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceRow:
    source_index: int
    source: str
    source_ref: str
    member_route: str
    district: str
    county: str
    values: tuple[object, ...]

    @property
    def postmile(self) -> str:
        return _text(self.values[0])

    @property
    def weak_key(self) -> tuple[str, str]:
        return self.member_route, self.postmile


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _manifest(root: Path, suffix: str) -> tuple[dict[str, object], list[FileEntry]]:
    paths = sorted(root.glob(f"*{suffix}"), key=lambda item: item.name)
    entries = [FileEntry(path.name, path.stat().st_size, _sha_file(path))
               for path in paths]
    wire = "".join(
        f"{entry.name}\t{entry.bytes}\t{entry.sha256}\n" for entry in entries
    ).encode("utf-8")
    return ({
        "files": len(entries),
        "bytes": sum(entry.bytes for entry in entries),
        "manifest_sha256": _sha_bytes(wire),
        "serialization": "name\\tbytes\\tsha256\\n sorted by name",
    }, entries)


def _bind_tree(label: str, root: Path) -> dict[str, object]:
    expected = TREE_BINDINGS[label]
    observed, entries = _manifest(root, str(expected["suffix"]))
    for field in ("files", "bytes", "manifest_sha256"):
        if observed[field] != expected[field]:
            raise AuditError(
                f"{label} {field} drift: {observed[field]!r} != "
                f"{expected[field]!r}")
    return {
        "root": str(root.resolve()), "binding": dict(expected),
        "observed": observed, "members": [asdict(entry) for entry in entries],
    }


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _member_route(path: Path) -> str:
    match = MEMBER_RE.fullmatch(path.name)
    if match is None:
        raise AuditError(f"unexpected Highway Detail member name: {path.name}")
    token = match.group(1).upper()
    return f"{int(token[:3]):03d}{token[3:]}"


def _rows_digest(rows: Sequence[SourceRow]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical((
            row.source_index, row.source, row.source_ref, row.member_route,
            row.district, row.county, row.values,
        )))
        digest.update(b"\n")
    return digest.hexdigest()


def _multiplicity(counter: Counter[tuple[str, ...]]) -> dict[str, int]:
    duplicate = [count for count in counter.values() if count > 1]
    return {
        "unique": len(counter),
        "duplicate_groups": len(duplicate),
        "duplicate_occurrences": sum(duplicate),
        "max_multiplicity": max(counter.values(), default=0),
    }


def _row_summary(label: str, rows: Sequence[SourceRow],
                 extra: dict[str, object] | None = None) -> dict[str, object]:
    per_member = Counter(row.member_route for row in rows)
    weak = Counter(row.weak_key for row in rows)
    nulls = {
        header: sum(row.values[index] in (None, "") for row in rows)
        for index, header in enumerate(TSMIS_HEADERS)
    }
    result: dict[str, object] = {
        "label": label,
        "rows": len(rows),
        "columns": len(TSMIS_HEADERS),
        "ordered_typed_rows_sha256": _rows_digest(rows),
        "members": len(per_member),
        "per_member_counts": dict(sorted(per_member.items())),
        "weak_route_postmile_identity": _multiplicity(weak),
        "null_or_empty_by_field": nulls,
    }
    if extra:
        result.update(extra)
    return result


def _parse_excel(root: Path, probe_member: str | None) -> tuple[
        list[SourceRow], dict[str, object]]:
    rows: list[SourceRow] = []
    member_files = sorted(root.glob("*.xlsx"), key=lambda item: item.name)
    if probe_member:
        member_files = [path for path in member_files
                        if _member_route(path) == probe_member]
        if len(member_files) != 1:
            raise AuditError(
                f"probe member {probe_member} selected {len(member_files)} Excel files")
    for path in member_files:
        member = _member_route(path)
        sheet = read_sheet(path, TSMIS_SPEC)
        for physical in sheet.rows:
            if not any(value not in (None, "") for value in physical.values):
                raise AuditError(f"blank Excel row: {path.name}:{physical.source_row}")
            rows.append(SourceRow(
                source_index=len(rows), source="TSMIS Excel",
                source_ref=f"{path.name}:row {physical.source_row}",
                member_route=member, district="", county="",
                values=tuple(physical.values),
            ))
    return rows, _row_summary("TSMIS Excel", rows)


def _round_edge(value: object) -> float:
    return round(float(value), 3)


def _page_band_profiles(page) -> dict[int, Counter[tuple[float, ...]]]:
    by_band: defaultdict[tuple[float, float], list[dict[str, object]]] = (
        defaultdict(list))
    for rect in page.rects:
        width = float(rect["x1"]) - float(rect["x0"])
        height = float(rect["bottom"]) - float(rect["top"])
        if 3 < width < float(page.width) - 10 and 3 < height < 40:
            by_band[(_round_edge(rect["top"]),
                     _round_edge(rect["bottom"]))].append(rect)
    profiles = {10: Counter(), 25: Counter()}
    for cells in by_band.values():
        if len(cells) not in profiles:
            continue
        ordered = sorted(cells, key=lambda item: float(item["x0"]))
        edges = tuple(_round_edge(value) for value in (
            [ordered[0]["x0"]] + [item["x1"] for item in ordered]))
        profiles[len(cells)][edges] += 1
    return profiles


def _validate_edges(label: str, edges: Sequence[float], width: int) -> None:
    if len(edges) != width + 1:
        raise AuditError(f"{label}: {len(edges)} edges for {width} cells")
    if edges[0] != PDF_LEFT_EDGE or edges[-1] != PDF_RIGHT_EDGE:
        raise AuditError(f"{label}: outer PDF grid edges drifted: {edges[0]}, {edges[-1]}")
    if any(right <= left for left, right in zip(edges, edges[1:])):
        raise AuditError(f"{label}: grid is not strictly increasing")
    if any(abs(edge / PDF_GRID_QUANTUM - round(edge / PDF_GRID_QUANTUM)) > 0.001
           for edge in edges):
        raise AuditError(f"{label}: grid edge left the 0.75-point lattice")


def _derive_line1(line2: Sequence[float]) -> tuple[float, ...]:
    if len(line2) != 26:
        raise AuditError("cannot derive line-1 grid from a non-25-cell grid")
    return tuple(line2[index] for index in LINE1_FROM_LINE2)


def _word_lines(page) -> list[tuple[float, list[dict[str, object]]]]:
    words = page.extract_words(
        x_tolerance=1, y_tolerance=2, keep_blank_chars=False,
        use_text_flow=False)
    ordered = sorted(words, key=lambda word: (
        float(word["top"]), float(word["x0"])))
    clusters: list[list[dict[str, object]]] = []
    anchors: list[float] = []
    for word in ordered:
        top = float(word["top"])
        if not clusters or abs(top - anchors[-1]) > WORD_LINE_TOLERANCE:
            clusters.append([word])
            anchors.append(top)
        else:
            clusters[-1].append(word)
            anchors[-1] = sum(
                float(item["top"]) for item in clusters[-1]) / len(clusters[-1])
    return [(anchor, sorted(cluster, key=lambda word: float(word["x0"])))
            for anchor, cluster in zip(anchors, clusters)]


def _physical_groups(page) -> tuple[
        list[list[tuple[float, list[dict[str, object]]]]], Counter[str]]:
    lines = _word_lines(page)
    groups: list[list[tuple[float, list[dict[str, object]]]]] = []
    gaps = Counter()
    for top, words in lines:
        if groups:
            gap = top - groups[-1][-1][0]
            bucket = f"{round(gap, 1):.1f}"
            gaps[bucket] += 1
        if groups and top - groups[-1][-1][0] <= WRAP_GAP_MAX:
            groups[-1].append((top, words))
        else:
            groups.append([(top, words)])
    return groups, gaps


def _assign_line(words: Sequence[dict[str, object]],
                 edges: Sequence[float]) -> list[str]:
    cells: list[list[dict[str, object]]] = [[] for _ in range(len(edges) - 1)]
    for word in words:
        center = (float(word["x0"]) + float(word["x1"])) / 2
        index = next((position for position in range(len(edges) - 1)
                      if edges[position] <= center < edges[position + 1]), None)
        if index is None:
            if center < edges[0] or center > edges[-1]:
                continue
            index = len(edges) - 2
        cells[index].append(word)
    return [
        " ".join(str(word["text"]) for word in sorted(
            members, key=lambda item: float(item["x0"]))).strip()
        for members in cells
    ]


def _join_fragment(previous: str, fragment: str) -> str:
    if not previous:
        return fragment
    if not fragment:
        return previous
    if previous.endswith("-"):
        return previous + fragment
    return previous + " " + fragment


def _assign_group(
        group: Sequence[tuple[float, Sequence[dict[str, object]]]],
        edges: Sequence[float]) -> list[str]:
    values = [""] * (len(edges) - 1)
    for _top, words in group:
        fragments = _assign_line(words, edges)
        values = [_join_fragment(old, new)
                  for old, new in zip(values, fragments)]
    return [value.strip() for value in values]


def _group_text(
        group: Sequence[tuple[float, Sequence[dict[str, object]]]]) -> str:
    parts = []
    for _top, words in group:
        parts.extend(str(word["text"]) for word in words)
    return " ".join(parts).strip()


def _is_furniture(text: str) -> bool:
    upper = " ".join(text.upper().split())
    compact = upper.replace(" ", "")
    return bool(
        PRINT_HEADER_RE.search(text)
        or ("POSTMILE" in compact and "LENGTH" in compact)
        or ("DATEOF" in compact and "ACC-CONT" in compact and "CITY" in compact)
        or ("DATEOFHACONT" in compact and "CITY" in compact)
        or ("DATEOFHAEFF-" in compact and "CITY" in compact)
        or "LEFTROADBED" in compact
        or "RIGHTROADBED" in compact
        or ("DESCRIPTION" in compact and "MEDIAN" in compact)
        or compact.startswith("S#SOTOTT-W")
        or (compact.startswith("EFF-DATE") and "WID" in compact)
        or (compact.startswith("EFF-") and "T-W" in compact)
        or (compact.startswith("DATETLNFTOTR") and "WID" in compact)
        or compact in {"ACC-", "CONT"}
        or compact in {"N", "NA"}
        or compact.startswith("CALIFORNIADEPARTMENTOFTRANSPORTATION")
    )


def _is_line1(values: Sequence[str]) -> bool:
    return bool(
        len(values) == 10
        and PM_RE.fullmatch(values[0])
        and (not values[1] or LENGTH_RE.fullmatch(values[1]))
        and (not values[2] or DATE_RE.fullmatch(values[2]))
        and (not values[3] or len(values[3]) == 1)
        and (not values[4] or len(values[4]) == 1)
        and (not values[5] or DATE_RE.fullmatch(values[5]))
        and (not values[6] or bool(re.fullmatch(r"[A-Za-z0-9.]+", values[6])))
        and (not values[7] or len(values[7]) == 1)
        and (not values[8] or DATE_RE.fullmatch(values[8]))
        and not values[9]
    )


def _is_line2(values: Sequence[str]) -> bool:
    if len(values) != 25:
        return False
    if any(values[index] and not DATE_RE.fullmatch(values[index])
           for index in (2, 11, 16)):
        return False
    if values[1] and len(values[1]) > 2:
        return False
    # Every non-description printed cell is a single compact code/value.
    if any(" " in values[index] for index in range(1, 25)):
        return False
    return True


def _merge_line2_fragments(previous: Sequence[str],
                           fragment: Sequence[str]) -> list[str]:
    """Merge vertically continued print fragments inside their exact cells."""
    if len(previous) != 25 or len(fragment) != 25:
        raise AuditError(
            "cannot merge Highway Detail line-two fragments outside 25 cells")
    return [_join_fragment(old, new)
            for old, new in zip(previous, fragment)]


def _candidate_projection(
        document, first: int, stop: int,
        line2: Sequence[float]) -> tuple[tuple[str, ...], ...] | None:
    line1 = _derive_line1(line2)
    pending: list[str] | None = None
    projected = []
    for page_index in range(first, stop):
        groups, _gaps = _physical_groups(document.pages[page_index])
        for group in groups:
            text = _group_text(group)
            if DCR_RE.fullmatch(" ".join(text.upper().split())) or _is_furniture(text):
                continue
            first_values = _assign_group(group, line1)
            if _is_line1(first_values):
                if pending is not None:
                    projected.append(tuple(pending[:9] + [""] * 25))
                pending = first_values
                continue
            if pending is None:
                return None
            second_values = _assign_group(group, line2)
            if not _is_line2(second_values):
                return None
            projected.append(tuple(pending[:9] + second_values[:25]))
            pending = None
    if pending is not None:
        projected.append(tuple(pending[:9] + [""] * 25))
    return tuple(projected) if projected else None


def _group_tokens(
        group: Sequence[tuple[float, Sequence[dict[str, object]]]]) -> list[str]:
    tokens = []
    for _top, words in group:
        tokens.extend(str(word["text"]) for word in words)
    return tokens


def _lexical_line1(
        group: Sequence[tuple[float, Sequence[dict[str, object]]]]) -> list[str] | None:
    tokens = _group_tokens(group)
    if len(tokens) < 5 or not PM_RE.fullmatch(tokens[0]) or not LENGTH_RE.fullmatch(tokens[1]):
        return None
    validators = (
        lambda value: bool(DATE_RE.fullmatch(value)),
        lambda value: len(value) == 1,
        lambda value: len(value) == 1,
        lambda value: bool(DATE_RE.fullmatch(value)),
        lambda value: bool(re.fullmatch(r"[A-Za-z0-9.]+", value)),
        lambda value: len(value) == 1,
        lambda value: bool(DATE_RE.fullmatch(value)),
    )
    optional = (True, True, True, True, True, True, True)
    candidates = []

    def visit(field: int, token: int, values: list[str]) -> None:
        if field == len(validators):
            if token == len(tokens):
                candidates.append([tokens[0], tokens[1], *values])
            return
        if optional[field]:
            visit(field + 1, token, [*values, ""])
        if token < len(tokens) and validators[field](tokens[token]):
            visit(field + 1, token + 1, [*values, tokens[token]])

    visit(0, 2, [])
    unique = {tuple(candidate) for candidate in candidates}
    if len(unique) != 1:
        return None
    return list(next(iter(unique)))


def _lexical_line2(
        group: Sequence[tuple[float, Sequence[dict[str, object]]]]) -> list[str] | None:
    tokens = _group_tokens(group)
    alpha = lambda value: bool(re.fullmatch(r"[A-Za-z]", value))
    digit = lambda value: bool(re.fullmatch(r"\d{1,3}", value))
    compact = lambda value: bool(re.fullmatch(r"[A-Za-z0-9]{1,4}", value))
    validators = (
        lambda value: bool(DATE_RE.fullmatch(value)),  # LB Eff
        alpha, digit, alpha, digit, digit, digit, digit, digit,
        lambda value: bool(DATE_RE.fullmatch(value)),  # Med Eff
        alpha, compact, alpha, compact,
        lambda value: bool(DATE_RE.fullmatch(value)),  # RB Eff
        alpha, digit, alpha, digit, digit, digit, digit, digit,
    )

    full_candidates = []
    if len(tokens) >= 23:
        split = len(tokens) - 23
        attrs = tokens[split:]
        if all(validator(value) for validator, value in zip(validators, attrs)):
            full_candidates.append([" ".join(tokens[:split]), "", *attrs])
    if len(tokens) >= 24:
        split = len(tokens) - 24
        attrs = tokens[split + 1:]
        if (tokens[split].upper() == "N"
                and all(validator(value)
                        for validator, value in zip(validators, attrs))):
            full_candidates.append([
                " ".join(tokens[:split]), tokens[split], *attrs])
    full_unique = {tuple(candidate) for candidate in full_candidates}
    if len(full_unique) == 1:
        return list(next(iter(full_unique)))

    def assign_attributes(values: tuple[str, ...]) -> list[tuple[str, ...]]:
        @lru_cache(maxsize=None)
        def visit(field: int, token: int) -> tuple[tuple[str, ...], ...]:
            if field == len(validators):
                return ((),) if token == len(values) else ()
            found: list[tuple[str, ...]] = []
            # Every printed attribute cell is source-allowed to be blank.  The
            # token-shape sequence must nevertheless yield exactly one fill.
            for suffix in visit(field + 1, token):
                found.append(("", *suffix))
                if len(found) > 2:
                    break
            if token < len(values) and validators[field](values[token]):
                for suffix in visit(field + 1, token + 1):
                    found.append((values[token], *suffix))
                    if len(found) > 2:
                        break
            return tuple(found[:3])

        return list(visit(0, 0))

    candidates = []
    for split in range(len(tokens) + 1):
        description = " ".join(tokens[:split])
        for na_count in (0, 1):
            if na_count and (split >= len(tokens) or tokens[split].upper() != "N"):
                continue
            start = split + na_count
            for attrs in assign_attributes(tuple(tokens[start:])):
                candidates.append([
                    description, tokens[split] if na_count else "", *attrs])
                if len(candidates) > 2:
                    break
            if len(candidates) > 2:
                break
        if len(candidates) > 2:
            break
    unique = {tuple(candidate) for candidate in candidates}
    if len(unique) != 1:
        return None
    return list(next(iter(unique)))


def _lexical_projection(document, first: int, stop: int) -> tuple[
        tuple[str, ...], ...] | None:
    pending: list[str] | None = None
    projected = []
    for page_index in range(first, stop):
        groups, _gaps = _physical_groups(document.pages[page_index])
        for group in groups:
            text = _group_text(group)
            if DCR_RE.fullmatch(" ".join(text.upper().split())) or _is_furniture(text):
                continue
            first_values = _lexical_line1(group)
            if first_values is not None:
                if pending is not None:
                    return None
                pending = first_values
                continue
            if pending is None:
                return None
            second_values = _lexical_line2(group)
            if second_values is None:
                return None
            projected.append(tuple(pending[:9] + second_values[:25]))
            pending = None
    if pending is not None:
        projected.append(tuple(pending[:9] + [""] * 25))
    return tuple(projected) if projected else None


def _voronoi_edges(centers: Sequence[float]) -> tuple[float, ...] | None:
    if any(right <= left for left, right in zip(centers, centers[1:])):
        return None
    edges = (PDF_LEFT_EDGE, *(
        round((left + right) / 2, 6)
        for left, right in zip(centers, centers[1:])), PDF_RIGHT_EDGE)
    if any(right <= left for left, right in zip(edges, edges[1:])):
        return None
    return tuple(edges)


def _header_anchor_edges(page) -> tuple[
        tuple[float, ...], tuple[float, ...]] | None:
    groups, _gaps = _physical_groups(page)
    line1_centers = []
    description_centers = []
    attribute_centers = []
    for group in groups:
        words = [word for _top, line in group for word in line]
        tokens = tuple(str(word["text"]) for word in words)
        if tuple(token.upper() for token in tokens) == LINE1_HEADER_LABELS:
            line1_centers.append((
                (float(words[0]["x0"]) + float(words[1]["x1"])) / 2,
                *((float(word["x0"]) + float(word["x1"])) / 2
                  for word in words[2:]),
            ))
        if (len(tokens) >= 2 and tokens[0].upper() == "DESCRIPTION"
                and tokens[1].upper() == "A"):
            description_centers.append(tuple(
                (float(word["x0"]) + float(word["x1"])) / 2
                for word in words[:2]))
        if tuple(token.upper() for token in tokens) == LINE2_HEADER_LABELS:
            attribute_centers.append(tuple(
                (float(word["x0"]) + float(word["x1"])) / 2
                for word in words))
    if (len(set(line1_centers)) != 1
            or len(set(description_centers)) != 1
            or len(set(attribute_centers)) != 1):
        return None
    line1 = line1_centers[0]
    line2 = (*description_centers[0], *attribute_centers[0])
    if len(line1) != 9 or len(line2) != 25:
        return None
    line1_edges = _voronoi_edges(line1)
    line2_edges = _voronoi_edges(line2)
    if line1_edges is None or line2_edges is None:
        return None
    return line1_edges, line2_edges


def _header_anchor_projection(document, first: int, stop: int) -> tuple[
        tuple[tuple[str, ...], ...], dict[int, tuple[float, ...]]] | None:
    per_page_edges = {}
    pending: list[str] | None = None
    projected = []
    for page_index in range(first, stop):
        edges = _header_anchor_edges(document.pages[page_index])
        if edges is None:
            return None
        line1_edges, line2_edges = edges
        per_page_edges[page_index + 1] = {
            "line1": line1_edges, "line2": line2_edges}
        groups, _gaps = _physical_groups(document.pages[page_index])
        for group in groups:
            text = _group_text(group)
            if DCR_RE.fullmatch(" ".join(text.upper().split())) or _is_furniture(text):
                continue
            first_values = [*_assign_group(group, line1_edges), ""]
            if _is_line1(first_values):
                if pending is not None:
                    return None
                pending = first_values
                continue
            if pending is None:
                return None
            second_values = _assign_group(group, line2_edges)
            if not _is_line2(second_values):
                second_values = _lexical_line2(group)
            if second_values is None:
                return None
            projected.append(tuple(pending[:9] + second_values[:25]))
            pending = None
    if pending is not None:
        projected.append(tuple(pending[:9] + [""] * 25))
    if not projected:
        return None
    return tuple(projected), per_page_edges


def _recover_gridless_block(
        document, first: int, stop: int,
        candidates: Sequence[tuple[float, ...]], member: str,
        printed_page: object) -> tuple[tuple[float, ...] | None, dict[str, object]]:
    projections: defaultdict[
        tuple[tuple[str, ...], ...], list[tuple[float, ...]]] = defaultdict(list)
    rejected = 0
    for line2 in candidates:
        projection = _candidate_projection(document, first, stop, line2)
        if projection is None:
            rejected += 1
        else:
            projections[projection].append(line2)
    if not projections:
        anchored = _header_anchor_projection(document, first, stop)
        if anchored is not None:
            header_projection, per_page_edges = anchored
            return None, {
                "mode": "printed_header_anchor",
                "method": (
                    "all observed document grids rejected; 25 printed header "
                    "centers define assignment Voronoi edges and yield one "
                    "plausible projection"),
                "candidate_grids": len(candidates),
                "rejected_grids": rejected,
                "fitting_grids": 0,
                "projection_classes": 1,
                "projected_rows": len(header_projection),
                "projection_sha256": _sha_bytes(_canonical(header_projection)),
                "header_assignment_edges": per_page_edges,
            }
        lexical = _lexical_projection(document, first, stop)
        if lexical is None:
            raise AuditError(
                f"{member}: printed page {printed_page} has neither an "
                "invariant observed-grid projection nor a unique conservative "
                "lexical projection")
        return None, {
            "mode": "ordered_lexical",
            "method": (
                "all observed document grids rejected; exact ordered token "
                "shapes uniquely fill line 1 and a complete 23-cell attribute tail"),
            "candidate_grids": len(candidates),
            "rejected_grids": rejected,
            "fitting_grids": 0,
            "projection_classes": 1,
            "projected_rows": len(lexical),
            "projection_sha256": _sha_bytes(_canonical(lexical)),
            "lexical_projection": lexical,
        }
    if len(projections) != 1:
        raise AuditError(
            f"{member}: printed page {printed_page} gridless projection is "
            f"not unique: {len(projections)} projection classes from "
            f"{len(candidates)} observed grids")
    projection, fitting = next(iter(projections.items()))
    chosen = sorted(fitting)[0]
    return chosen, {
        "mode": "observed_grid_invariant",
        "method": (
            "enumerate every exact 25-cell grid observed in this document; "
            "accept only one invariant plausible 34-cell projection"),
        "candidate_grids": len(candidates),
        "rejected_grids": rejected,
        "fitting_grids": len(fitting),
        "projection_classes": 1,
        "projected_rows": len(projection),
        "projection_sha256": _sha_bytes(_canonical(projection)),
    }


def _print_headers(document, member: str) -> tuple[
        list[dict[str, object]], dict[str, object]]:
    starts = []
    cover_text = document.pages[0].extract_text(
        x_tolerance=1, y_tolerance=2) or ""
    report_match = REPORT_DATE_RE.search(cover_text)
    reference_match = REFERENCE_DATE_RE.search(cover_text)
    page_sizes = Counter()
    for page_index, page in enumerate(document.pages):
        page_sizes[(round(float(page.width), 3),
                    round(float(page.height), 3))] += 1
        text = page.extract_text(x_tolerance=1, y_tolerance=2) or ""
        match = PRINT_HEADER_RE.search(text)
        if match is None:
            continue
        reference, route, printed_page = match.groups()
        route = f"{int(route[:3]):03d}{route[3:].upper()}"
        if route != member:
            raise AuditError(
                f"{member}: printed header route {route} on PDF page {page_index + 1}")
        starts.append({
            "physical_index": page_index,
            "physical_page": page_index + 1,
            "reference_date": reference,
            "route": route,
            "printed_page": int(printed_page),
        })
    if not starts:
        raise AuditError(f"{member}: no printed Highway Detail page headers")
    printed = [item["printed_page"] for item in starts]
    if printed != list(range(1, len(printed) + 1)):
        raise AuditError(f"{member}: printed page sequence drift: {printed[:20]!r}")
    return starts, {
        "report_date": report_match.group(1) if report_match else None,
        "reference_date": reference_match.group(1) if reference_match else None,
        "page_sizes": {f"{width}x{height}": count
                       for (width, height), count in sorted(page_sizes.items())},
    }


def _block_grids(document, starts: Sequence[dict[str, object]],
                 member: str) -> tuple[list[dict[str, object]], dict[str, int]]:
    blocks = []
    census = Counter()
    page_profiles = [_page_band_profiles(page) for page in document.pages]
    global_line2 = sorted({
        edges for observed in page_profiles for edges in observed[25]
    })
    if not global_line2:
        raise AuditError(f"{member}: document has no 25-cell source grid")
    for ordinal, start in enumerate(starts):
        first = int(start["physical_index"])
        stop = (int(starts[ordinal + 1]["physical_index"])
                if ordinal + 1 < len(starts) else len(document.pages))
        profiles = {10: Counter(), 25: Counter()}
        per_page = []
        for page_index in range(first, stop):
            observed = page_profiles[page_index]
            per_page.append({
                "physical_page": page_index + 1,
                "line1_profiles": len(observed[10]),
                "line2_profiles": len(observed[25]),
                "line1_bands": sum(observed[10].values()),
                "line2_bands": sum(observed[25].values()),
            })
            profiles[10].update(observed[10])
            profiles[25].update(observed[25])
            if observed[10] and observed[25]:
                census["pages_with_both_grids"] += 1
            elif observed[10]:
                census["pages_with_line1_only"] += 1
            elif observed[25]:
                census["pages_with_line2_only"] += 1
            else:
                census["pages_with_neither_grid"] += 1
        recovery = None
        if not profiles[25]:
            line2, recovery = _recover_gridless_block(
                document, first, stop, global_line2, member,
                start["printed_page"])
            if line2 is None:
                if recovery.get("mode") == "printed_header_anchor":
                    census["blocks_gridless_header_anchored"] += 1
                else:
                    census["blocks_gridless_lexically_unique"] += 1
            else:
                census["blocks_gridless_uniquely_projected"] += 1
        elif len(profiles[25]) == 1:
            line2 = next(iter(profiles[25]))
        else:
            raise AuditError(
                f"{member}: printed page {start['printed_page']} has "
                f"{len(profiles[25])} distinct 25-cell grids")
        if line2 is not None:
            _validate_edges(f"{member}:printed page {start['printed_page']}:line2",
                            line2, 25)
            derived = _derive_line1(line2)
            _validate_edges(f"{member}:printed page {start['printed_page']}:line1",
                            derived, 10)
        else:
            derived = None
        if len(profiles[10]) > 1:
            raise AuditError(
                f"{member}: printed page {start['printed_page']} has "
                f"{len(profiles[10])} distinct 10-cell grids")
        if profiles[10] and next(iter(profiles[10])) != derived:
            raise AuditError(
                f"{member}: printed page {start['printed_page']} line-1 grid "
                "does not exactly merge its 25-cell base grid")
        if not profiles[10] and derived is not None:
            census["blocks_deriving_line1_from_line2"] += 1
        blocks.append({
            **start,
            "stop_physical_index": stop,
            "physical_pages": list(range(first + 1, stop + 1)),
            "line1_edges": derived,
            "line2_edges": line2,
            "line1_bands": sum(profiles[10].values()),
            "line2_bands": sum(profiles[25].values()),
            "per_page": per_page,
            "gridless_recovery": recovery,
        })
    return blocks, dict(census)


def _parse_one_pdf(path: Path, start_index: int) -> tuple[
        list[SourceRow], dict[str, object]]:
    member = _member_route(path)
    rows: list[SourceRow] = []
    current_district = ""
    current_county = ""
    pending: dict[str, object] | None = None
    stats = Counter()
    gap_census = Counter()
    unclassified = []
    dcr_sequence = []

    def flush_pending(reason: str) -> None:
        nonlocal pending
        if pending is None:
            return
        line2_groups = int(pending["line2_groups"])
        line2 = list(pending["line2"])
        if line2_groups and not _is_line2(line2):
            raise AuditError(
                f"{path.name}: merged {line2_groups} line-two print groups "
                f"are not a valid 25-cell row at physical page "
                f"{pending['physical_page']}:top {pending['top']:.3f}: "
                f"{line2!r}")
        values = tuple(pending["line1"][:9] + line2)
        if line2_groups:
            last_page = int(pending["last_line2_page"])
            last_top = float(pending["last_line2_top"])
            source_ref = (
                f"{path.name}:physical pages "
                f"{pending['physical_page']}-{last_page}:"
                f"top {pending['top']:.3f}-{last_top:.3f}")
            stats["line2_records"] += 1
            stats["line2_physical_groups"] += line2_groups
            if line2_groups > 1:
                stats["multigroup_line2_records"] += 1
                stats["multigroup_line2_physical_groups"] += line2_groups
        else:
            source_ref = (
                f"{path.name}:physical page {pending['physical_page']}:"
                f"top {pending['top']:.3f}:{reason}")
            stats["single_line_records"] += 1
        rows.append(SourceRow(
            source_index=start_index + len(rows), source="TSMIS PDF",
            source_ref=source_ref,
            member_route=member, district=str(pending["district"]),
            county=str(pending["county"]), values=values,
        ))
        pending = None

    logging.disable(logging.CRITICAL)
    with pdfplumber.open(path) as document:
        starts, metadata = _print_headers(document, member)
        blocks, grid_census = _block_grids(document, starts, member)
        for block in blocks:
            line1_edges = block["line1_edges"]
            line2_edges = block["line2_edges"]
            lexical_block = line1_edges is None or line2_edges is None
            recovery = block.get("gridless_recovery") or {}
            header_edges = {
                int(page): {
                    "line1": tuple(edges["line1"]),
                    "line2": tuple(edges["line2"]),
                }
                for page, edges in
                recovery.get("header_assignment_edges", {}).items()
            }
            for page_index in range(
                    int(block["physical_index"]),
                    int(block["stop_physical_index"])):
                groups, gaps = _physical_groups(document.pages[page_index])
                gap_census.update(gaps)
                for group in groups:
                    text = _group_text(group)
                    dcr = DCR_RE.fullmatch(" ".join(text.upper().split()))
                    if dcr is not None:
                        flush_pending("no printed attribute line before DCR")
                        district, county, route = dcr.groups()
                        route = f"{int(route[:3]):03d}{route[3:].upper()}"
                        if route != member:
                            raise AuditError(
                                f"{path.name}: DCR route {route} != member {member}")
                        current_district = (
                            f"{int(district):02d}" if district.isdigit()
                            else district)
                        current_county = county.rstrip(".")
                        dcr_sequence.append((
                            page_index + 1, round(group[0][0], 3),
                            current_district, current_county, route))
                        stats["dcr_headers"] += 1
                        continue
                    if page_index + 1 in header_edges:
                        first = [*_assign_group(
                            group, header_edges[page_index + 1]["line1"]), ""]
                    else:
                        first = (_lexical_line1(group) if lexical_block
                                 else _assign_group(group, line1_edges))
                    first_valid = bool(
                        first is not None and (
                            (lexical_block and page_index + 1 not in header_edges)
                            or _is_line1(first)))
                    if first_valid:
                        flush_pending("no printed attribute line before next record")
                        if not current_district or not current_county:
                            raise AuditError(
                                f"{path.name}: data before DCR context on page "
                                f"{page_index + 1}: {first[:3]!r}")
                        pending = {
                            "line1": first,
                            "district": current_district,
                            "county": current_county,
                            "physical_page": page_index + 1,
                            "top": group[0][0],
                            "line2": [""] * 25,
                            "line2_groups": 0,
                            "last_line2_page": None,
                            "last_line2_top": None,
                        }
                        stats["line1_records"] += 1
                        continue
                    if _is_furniture(text):
                        stats["furniture_groups"] += 1
                        continue
                    if pending is not None:
                        if page_index + 1 in header_edges:
                            second = _assign_group(
                                group, header_edges[page_index + 1]["line2"])
                            if not _is_line2(second):
                                second = _lexical_line2(group)
                        else:
                            second = (_lexical_line2(group) if lexical_block
                                      else _assign_group(group, line2_edges))
                        if second is None:
                            stats["unclassified_groups"] += 1
                            if len(unclassified) < 25:
                                unclassified.append({
                                    "physical_page": page_index + 1,
                                    "top": round(group[0][0], 3),
                                    "text": text,
                                })
                            continue
                        pending["line2"] = _merge_line2_fragments(
                            pending["line2"], second[:25])
                        pending["line2_groups"] = (
                            int(pending["line2_groups"]) + 1)
                        pending["last_line2_page"] = page_index + 1
                        pending["last_line2_top"] = group[0][0]
                        continue
                    stats["unclassified_groups"] += 1
                    if len(unclassified) < 25:
                        unclassified.append({
                            "physical_page": page_index + 1,
                            "top": round(group[0][0], 3),
                            "text": text,
                        })
        flush_pending("document end")
    if stats["line1_records"] != len(rows):
        raise AuditError(
            f"{path.name}: line1/row reconciliation drift: "
            f"{stats['line1_records']} != {len(rows)}")
    malformed = [
        row for row in rows
        if not (PM_RE.fullmatch(_text(row.values[0]))
                and (not _text(row.values[1])
                     or LENGTH_RE.fullmatch(_text(row.values[1])))
                and (not _text(row.values[2])
                     or DATE_RE.fullmatch(_text(row.values[2]))))
    ]
    if malformed:
        raise AuditError(
            f"{path.name}: emitted malformed first-line fields: "
            f"{[(row.source_ref, row.values[:9]) for row in malformed[:5]]!r}")
    return rows, {
        "member": member,
        "physical_pages": sum(metadata["page_sizes"].values()),
        "printed_pages": len(blocks),
        "metadata": metadata,
        "grid_census": grid_census,
        "grid_manifest_sha256": _sha_bytes(_canonical([
            (block["printed_page"], block["physical_pages"],
             block["line1_edges"], block["line2_edges"])
            for block in blocks
        ])),
        "gridless_recoveries": [{
            "printed_page": block["printed_page"],
            "physical_pages": block["physical_pages"],
            "recovery": block["gridless_recovery"],
        } for block in blocks if block["gridless_recovery"] is not None],
        "stats": dict(stats),
        "word_line_gap_census": dict(sorted(gap_census.items(),
                                             key=lambda item: float(item[0]))),
        "dcr_sequence_sha256": _sha_bytes(_canonical(dcr_sequence)),
        "dcr_headers": len(dcr_sequence),
        "unclassified_samples": unclassified,
    }


def _parse_one_pdf_zero(path: Path) -> tuple[list[SourceRow], dict[str, object]]:
    """Picklable deterministic worker entry point for statewide parsing."""
    return _parse_one_pdf(path, 0)


def _parse_pdf(root: Path, probe_member: str | None, workers: int) -> tuple[
        list[SourceRow], dict[str, object]]:
    rows: list[SourceRow] = []
    member_files = sorted(root.glob("*.pdf"), key=lambda item: item.name)
    if probe_member:
        member_files = [path for path in member_files
                        if _member_route(path) == probe_member]
        if len(member_files) != 1:
            raise AuditError(
                f"probe member {probe_member} selected {len(member_files)} PDF files")
    totals = Counter()
    per_file = []
    report_dates = Counter()
    reference_dates = Counter()
    if workers < 1:
        raise AuditError("PDF worker count must be positive")
    if workers > 1 and len(member_files) > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            parsed_members = list(executor.map(_parse_one_pdf_zero, member_files))
    else:
        parsed_members = [_parse_one_pdf_zero(path) for path in member_files]
    for path, (parsed, details) in zip(member_files, parsed_members):
        base = len(rows)
        parsed = [replace(row, source_index=base + index)
                  for index, row in enumerate(parsed)]
        rows.extend(parsed)
        per_file.append(details)
        totals.update(details["grid_census"])
        totals.update(details["stats"])
        report_dates[details["metadata"]["report_date"]] += 1
        reference_dates[details["metadata"]["reference_date"]] += 1
    unclassified = sum(
        int(item["stats"].get("unclassified_groups", 0)) for item in per_file)
    summary = _row_summary("TSMIS PDF", rows, {
        "reconciliation": dict(totals),
        "unclassified_groups": unclassified,
        "report_dates": dict(report_dates),
        "reference_dates": dict(reference_dates),
        "per_file": per_file,
        "extraction_independence": {
            "oracle": (
                "pdfplumber words assigned to an exact per-printed-page "
                "25-cell base grid; the 10-cell grid is relationally derived"),
            "product": (
                "pdfplumber characters assigned to page bands with a "
                "document-median fallback when either page grid is absent"),
        },
    })
    return rows, summary


def _render_cell(value: object) -> str:
    """Source-format rendering equivalence, not comparison normalization."""
    return " ".join(_text(value).replace("\u00a0", " ").split())


def _row_signature(row: SourceRow, excluded: frozenset[int]) -> tuple[str, ...]:
    return tuple(_render_cell(value) for index, value in enumerate(row.values)
                 if index not in excluded)


def _source_format_alignment(excel_rows: Sequence[SourceRow],
                             pdf_rows: Sequence[SourceRow]) -> dict[str, object]:
    """Align same-build Excel/PDF rows by order plus independent source claims.

    Tier 1 requires all 34 rendered cells.  Tier 2 is applied only inside a
    non-equal Tier-1 interval and requires every field except Post Mile and
    Length.  This exposes print-only key/length changes without letting those
    fields choose their own counterpart.  Unpaired rows remain unpaired; there
    is deliberately no positional or fuzzy fallback.
    """
    excel_by_member: defaultdict[str, list[SourceRow]] = defaultdict(list)
    pdf_by_member: defaultdict[str, list[SourceRow]] = defaultdict(list)
    for row in excel_rows:
        excel_by_member[row.member_route].append(row)
    for row in pdf_rows:
        pdf_by_member[row.member_route].append(row)
    if set(excel_by_member) != set(pdf_by_member):
        raise AuditError("TSMIS Excel/PDF member universes differ")

    totals = Counter()
    per_field = Counter()
    per_member = []
    difference_samples = []
    one_sided_samples = []
    pair_digest = hashlib.sha256()
    for member in sorted(excel_by_member):
        left = excel_by_member[member]
        right = pdf_by_member[member]
        left_full = [_row_signature(row, frozenset()) for row in left]
        right_full = [_row_signature(row, frozenset()) for row in right]
        first = SequenceMatcher(
            None, left_full, right_full, autojunk=False).get_opcodes()
        pairs: dict[int, tuple[int, str]] = {}
        paired_right = set()
        primary_replace = []
        for tag, i1, i2, j1, j2 in first:
            if tag == "equal":
                for left_index, right_index in zip(range(i1, i2), range(j1, j2)):
                    pairs[left_index] = (right_index, "all_34_render_equal")
                    paired_right.add(right_index)
            else:
                primary_replace.append((tag, i1, i2, j1, j2))
        for _tag, i1, i2, j1, j2 in primary_replace:
            left_claims = [_row_signature(row, frozenset({0, 1}))
                           for row in left[i1:i2]]
            right_claims = [_row_signature(row, frozenset({0, 1}))
                            for row in right[j1:j2]]
            second = SequenceMatcher(
                None, left_claims, right_claims, autojunk=False).get_opcodes()
            for tag, a1, a2, b1, b2 in second:
                if tag != "equal":
                    continue
                for left_offset, right_offset in zip(
                        range(a1, a2), range(b1, b2)):
                    left_index = i1 + left_offset
                    right_index = j1 + right_offset
                    if left_index in pairs or right_index in paired_right:
                        raise AuditError("non-bijective TSMIS source alignment")
                    pairs[left_index] = (
                        right_index, "fields_2_through_33_render_equal")
                    paired_right.add(right_index)

        ordered_pairs = sorted(
            (left_index, right_index, classification)
            for left_index, (right_index, classification) in pairs.items())
        if any(next_right <= right_index
               for (_left, right_index, _class),
                   (_next_left, next_right, _next_class)
               in zip(ordered_pairs, ordered_pairs[1:])):
            raise AuditError(f"{member}: source alignment is not monotonic")
        member_counts = Counter(classification for _i, _j, classification in ordered_pairs)
        different_rows = 0
        different_cells = 0
        for left_index, right_index, classification in ordered_pairs:
            left_values = left_full[left_index]
            right_values = right_full[right_index]
            diffs = [index for index, (a, b) in enumerate(
                zip(left_values, right_values)) if a != b]
            if diffs:
                different_rows += 1
                different_cells += len(diffs)
                for index in diffs:
                    per_field[TSMIS_HEADERS[index]] += 1
                if len(difference_samples) < 40:
                    difference_samples.append({
                        "member": member,
                        "excel_ref": left[left_index].source_ref,
                        "pdf_ref": right[right_index].source_ref,
                        "district": right[right_index].district,
                        "county": right[right_index].county,
                        "classification": classification,
                        "differences": [{
                            "field": TSMIS_HEADERS[index],
                            "excel": left_values[index],
                            "pdf": right_values[index],
                        } for index in diffs],
                    })
            pair_digest.update(_canonical((
                member, left_index, right_index, classification,
                right[right_index].district, right[right_index].county,
            )))
            pair_digest.update(b"\n")
        excel_only = [index for index in range(len(left)) if index not in pairs]
        pdf_only = [index for index in range(len(right)) if index not in paired_right]
        for side, indexes, source in (
                ("excel", excel_only, left), ("pdf", pdf_only, right)):
            for index in indexes:
                if len(one_sided_samples) >= 40:
                    break
                one_sided_samples.append({
                    "member": member, "side": side,
                    "source_ref": source[index].source_ref,
                    "district": source[index].district,
                    "county": source[index].county,
                    "postmile": source[index].postmile,
                    "values": [_render_cell(value) for value in source[index].values],
                })
        member_result = {
            "member": member,
            "excel_rows": len(left), "pdf_rows": len(right),
            "paired_rows": len(ordered_pairs),
            "all_34_render_equal": member_counts["all_34_render_equal"],
            "fields_2_through_33_render_equal": member_counts[
                "fields_2_through_33_render_equal"],
            "paired_differing_rows": different_rows,
            "paired_differing_cells": different_cells,
            "excel_only_rows": len(excel_only),
            "pdf_only_rows": len(pdf_only),
        }
        per_member.append(member_result)
        totals.update({key: value for key, value in member_result.items()
                       if key != "member"})

    return {
        "method": {
            "tier_1": "monotonic SequenceMatcher on all 34 render-equivalent cells",
            "tier_2": (
                "inside tier-1 non-equal intervals only, monotonic exact match "
                "on fields 2..33; no positional/fuzzy fallback"),
            "county_source": "the paired PDF row's printed DCR header",
        },
        "totals": {
            key: totals[key] for key in (
                "excel_rows", "pdf_rows", "paired_rows",
                "all_34_render_equal", "fields_2_through_33_render_equal",
                "paired_differing_rows", "paired_differing_cells",
                "excel_only_rows", "pdf_only_rows")
        },
        "per_field_paired_differences": dict(sorted(per_field.items())),
        "pair_map_sha256": pair_digest.hexdigest(),
        "per_member": per_member,
        "difference_samples": difference_samples,
        "one_sided_samples": one_sided_samples,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    probe = args.probe_member.upper() if args.probe_member else None
    if probe:
        probe = f"{int(probe[:3]):03d}{probe[3:]}"
    provenance = {
        "tsmis_excel": _bind_tree("tsmis_excel", args.xlsx_root),
        "tsmis_pdf": _bind_tree("tsmis_pdf", args.pdf_root),
    }
    excel_rows, excel = _parse_excel(args.xlsx_root, probe)
    pdf_rows, pdf = _parse_pdf(args.pdf_root, probe, args.workers)
    if (not probe and pdf["unclassified_groups"]
            and not args.diagnostic_unclassified):
        raise AuditError(
            "TSMIS PDF independent parse left "
            f"{pdf['unclassified_groups']} unclassified groups")
    result = {
        "schema_version": 1,
        "status": (
            "probe" if probe else
            "diagnostic-unclassified" if pdf["unclassified_groups"] else
            "draft-source-oracle"),
        "probe_member": probe,
        "provenance": provenance,
        "sources": {"tsmis_excel": excel, "tsmis_pdf": pdf},
        "tsmis_excel_pdf_source_alignment": _source_format_alignment(
            excel_rows, pdf_rows),
        "current_stage": (
            "independent TSMIS Excel/PDF source reconstruction; TSN and "
            "comparison/evidence layers are not yet attached"),
        "statewide_acceptance": False,
        "source_rows_available_in_memory": {
            "tsmis_excel": len(excel_rows), "tsmis_pdf": len(pdf_rows)},
    }
    return result


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx-root", type=Path, default=DEFAULT_XLSX_ROOT)
    parser.add_argument("--pdf-root", type=Path, default=DEFAULT_PDF_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--probe-member",
        help="parse one route member for diagnostics; cannot be accepted")
    parser.add_argument(
        "--workers", type=int, default=1,
        help="deterministic PDF member workers; executor.map preserves member order")
    parser.add_argument(
        "--diagnostic-unclassified", action="store_true",
        help="serialize a non-accepting statewide draft even when PDF groups remain")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run(args)
    encoded = (json.dumps(
        result, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    sys.stdout.write(json.dumps({
        "status": result["status"],
        "output": str(args.output.resolve()),
        "bytes": len(encoded),
        "sha256": _sha_bytes(encoded),
        "rows": result["source_rows_available_in_memory"],
    }, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

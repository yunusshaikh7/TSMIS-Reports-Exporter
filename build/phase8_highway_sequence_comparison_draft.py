#!/usr/bin/env python3
"""Development comparison analysis for Highway Sequence Stage 8.

This draft consumes explicitly non-acceptance row caches to iterate quickly on
identity and classification policy.  The final oracle reparses immutable sources.
No product parser, comparator, schema, or evidence module is imported.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Iterable, Mapping, Sequence

from openpyxl.utils.escape import unescape as xlsx_unescape


VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
TSMIS_CACHE = VISUAL_ROOT / "phase8_highway_sequence_source_rows_draft_r1.json"
TSN_CACHE = VISUAL_ROOT / "phase8_highway_sequence_tsn_rows_draft_r1.json"
DEFAULT_OUTPUT = VISUAL_ROOT / "phase8_highway_sequence_comparison_draft_r1.json"

CACHE_BINDINGS = {
    "tsmis": {
        "path": TSMIS_CACHE, "bytes": 49_304_637,
        "sha256": "564cf21972aeaf461811095997524c2d02f3ca4f238bb8da8b715415df2762f8",
    },
    "tsn": {
        "path": TSN_CACHE, "bytes": 28_829_216,
        "sha256": "b18d2e077b79920cb1f687f06f8193b25e1d8cd2ebeb1d071b84c22b372598a7",
    },
}

VALUE_FIELDS = ("City", "HG", "FT", "Distance To Next Point", "Description")
SAME_SOURCE_FIELDS = (
    "PM Suffix", "City", "HG", "FT", "Distance To Next Point", "Description",
)
ASSERTED_VS_TSN_FIELDS = ("FT", "Description")
CONTEXT_VS_TSN_FIELDS = ("City", "HG", "Distance To Next Point")
ROUTE_PREFIX_RE = re.compile(r"^(\d{1,3}[A-Z]?)/")
PM_RE = re.compile(r"^([A-Z]?\d{3}\.\d{3})(E?)$")


class DraftError(RuntimeError):
    pass


@dataclass(frozen=True)
class Row:
    source: str
    source_ref: str
    source_index: int
    route: str
    county: str
    pm_base: str
    pm_suffix: str
    values: tuple[str, ...]
    raw_values: tuple[object, ...]
    kind: str
    provenance: dict[str, object]

    @property
    def pm_full(self) -> str:
        return self.pm_base + self.pm_suffix

    @property
    def value_map(self) -> dict[str, str]:
        return dict(zip(VALUE_FIELDS, self.values, strict=True))


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _bind_cache(label: str) -> dict[str, object]:
    spec = CACHE_BINDINGS[label]
    path = Path(spec["path"])
    observed = {"bytes": path.stat().st_size, "sha256": _sha_file(path)}
    expected = {key: spec[key] for key in ("bytes", "sha256")}
    if observed != expected:
        raise DraftError(f"{label} development-cache identity drift: {observed}")
    return observed


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _space(value: object, *, xlsx: bool = False) -> str:
    text = _text(value)
    if xlsx:
        text = xlsx_unescape(text)
    return " ".join(text.split())


def _route(value: object) -> str:
    match = re.fullmatch(r"(\d{1,3})([A-Za-z]?)", _text(value))
    if match is None:
        raise DraftError(f"invalid route: {value!r}")
    return match.group(1).zfill(3) + match.group(2).upper()


def _county(value: object) -> str:
    return _text(value).rstrip(".").upper()


def _pm(value: object) -> tuple[str, str]:
    text = _text(value).upper()
    if not text:
        return "", ""
    match = PM_RE.fullmatch(text)
    if match is None:
        raise DraftError(f"invalid complete postmile: {value!r}")
    return match.group(1), match.group(2)


def _semantic_desc(value: object, route: str, *, xlsx: bool = False,
                   strip_route_prefix: bool = False) -> str:
    text = _space(value, xlsx=xlsx)
    if strip_route_prefix:
        match = ROUTE_PREFIX_RE.match(text)
        if match is not None and _route(match.group(1)) == route:
            # The proven TSMIS outer label may be followed by delimiter padding
            # (`005/ SEG...`).  It belongs to the label, not the Description.
            text = text[match.end():].lstrip()
    return text


def _tsmis_rows(serialized: Sequence[Mapping[str, object]], source: str) -> list[Row]:
    is_xlsx = "excel" in source
    rows = []
    for item in serialized:
        raw = tuple(item["values"])
        route = _route(item["route"])
        pm_base = _text(raw[2]).upper() + _text(raw[3]).upper()
        if pm_base and PM_RE.fullmatch(pm_base) is None:
            raise DraftError(f"{item['source_ref']}: invalid TSMIS PM {pm_base!r}")
        suffix = _text(raw[4]).upper()
        if suffix not in ("", "E"):
            raise DraftError(f"{item['source_ref']}: invalid TSMIS suffix {suffix!r}")
        values = (
            _space(raw[1], xlsx=is_xlsx),
            _space(raw[5], xlsx=is_xlsx),
            _space(raw[6], xlsx=is_xlsx),
            _space(raw[7], xlsx=is_xlsx),
            _semantic_desc(raw[8], route, xlsx=is_xlsx),
        )
        rows.append(Row(
            source=source, source_ref=str(item["source_ref"]),
            source_index=int(item["source_index"]), route=route,
            county=_county(raw[0]), pm_base=pm_base, pm_suffix=suffix,
            values=values, raw_values=raw, kind="tsmis",
            provenance={
                "member": item["member"], "page": item.get("page"),
                "top": item.get("top"),
            },
        ))
    return rows


def _raw_tsn_rows(serialized: Sequence[Mapping[str, object]]) -> tuple[list[Row], list[Row]]:
    known = []
    unknown = []
    for ordinal, item in enumerate(serialized, 1):
        route = _route(item["route"])
        pm_base, suffix = _pm(item["pm"])
        raw = (
            item.get("city"), item.get("hg"), item.get("ft"),
            item.get("distance"), item.get("description"),
        )
        row = Row(
            source="raw_tsn", source_ref=(
                f"{item['member']}:page:{item['physical_page']}:line:{item['line']}"
            ),
            source_index=ordinal, route=route, county=_county(item.get("county")),
            pm_base=pm_base, pm_suffix=suffix,
            values=(
                _space(item.get("city")), _space(item.get("hg")),
                _space(item.get("ft")), _space(item.get("distance")),
                _semantic_desc(item.get("description"), route),
            ),
            raw_values=raw, kind=str(item["kind"]),
            provenance={
                "member": item["member"], "district": item["district"],
                "direction": item["direction"],
                "physical_page": item["physical_page"],
                "printed_page": item["printed_page"], "line": item["line"],
                "top": item["top"], "raw_text": item["raw_text"],
            },
        )
        (known if row.county else unknown).append(row)
    return known, unknown


def _normalized_tsn_rows(serialized: Sequence[Mapping[str, object]]) -> list[Row]:
    rows = []
    for item in serialized:
        raw = tuple(item["values"])
        route = _route(raw[0])
        pm_base, suffix = _pm(raw[2])
        rows.append(Row(
            source="normalized_tsn",
            source_ref=f"normalized:row:{item['source_row']}",
            source_index=int(item["source_row"]), route=route,
            county=_county(raw[1]), pm_base=pm_base, pm_suffix=suffix,
            values=(
                _space(raw[3]), _space(raw[4]), _space(raw[5]),
                _space(raw[6]), _semantic_desc(raw[7], route),
            ),
            raw_values=raw, kind=(
                "equate" if _space(raw[7]).startswith("EQUATES TO") else "data"
            ),
            provenance={"normalized_source_row": item["source_row"]},
        ))
    return rows


def _same_source_values(row: Row) -> tuple[str, ...]:
    return (row.pm_suffix, *row.values)


def _tsn_values(row: Row, *, tsmis_side: bool) -> tuple[str, ...]:
    values = list(row.values)
    if tsmis_side:
        values[-1] = _semantic_desc(
            row.raw_values[8], row.route,
            xlsx="excel" in row.source, strip_route_prefix=True,
        )
    return tuple(values)


def _char_distance(left: str, right: str) -> int:
    # Exact Levenshtein distance; cached because duplicate groups reuse pairs.
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, 1):
        current = [left_index]
        for right_index, right_char in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def _cost(left_values: Sequence[str], right_values: Sequence[str],
          left_position: int, right_position: int) -> tuple[int, int, int]:
    return (
        sum(a != b for a, b in zip(left_values, right_values, strict=True)),
        sum(_char_distance(a, b) for a, b in zip(left_values, right_values, strict=True)),
        abs(left_position - right_position),
    )


def _add_cost(left: tuple[int, int, int], right: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(a + b for a, b in zip(left, right, strict=True))


def _assign_group(left: Sequence[Row], right: Sequence[Row],
                  projector: Callable[[Row], tuple[str, ...]]) -> tuple[
                      list[tuple[Row, Row]], list[Row], list[Row], tuple[int, int, int]]:
    if not left or not right:
        return [], list(left), list(right), (0, 0, 0)
    swapped = len(left) > len(right)
    small = right if swapped else left
    large = left if swapped else right
    if len(large) > 12:
        raise DraftError(f"assignment group too large for exact DP: {len(left)}x{len(right)}")
    small_values = [projector(row) for row in small]
    large_values = [projector(row) for row in large]

    @lru_cache(maxsize=None)
    def solve(index: int, used_mask: int) -> tuple[
            tuple[int, int, int], tuple[tuple[int, int], ...]]:
        if index == len(small):
            return (0, 0, 0), ()
        best = None
        for candidate in range(len(large)):
            if used_mask & (1 << candidate):
                continue
            tail_cost, tail_pairs = solve(index + 1, used_mask | (1 << candidate))
            pair_cost = _cost(
                small_values[index], large_values[candidate], index, candidate,
            )
            value = (_add_cost(pair_cost, tail_cost), ((index, candidate), *tail_pairs))
            if best is None or value < best:
                best = value
        if best is None:
            raise DraftError("assignment DP found no candidate")
        return best

    total_cost, assignments = solve(0, 0)
    used_large = {large_index for _small_index, large_index in assignments}
    pairs = []
    for small_index, large_index in assignments:
        if swapped:
            pairs.append((large[large_index], small[small_index]))
        else:
            pairs.append((small[small_index], large[large_index]))
    pairs.sort(key=lambda pair: (pair[0].source_index, pair[1].source_index))
    left_only = [row for row in left if all(row is not pair[0] for pair in pairs)]
    right_only = [row for row in right if all(row is not pair[1] for pair in pairs)]
    return pairs, left_only, right_only, total_cost


def _pair(
    left: Sequence[Row], right: Sequence[Row],
    key: Callable[[Row], tuple[str, ...]],
    projector: Callable[[Row], tuple[str, ...]],
) -> tuple[list[tuple[Row, Row]], list[Row], list[Row], dict[str, object]]:
    left_groups: dict[tuple[str, ...], list[Row]] = defaultdict(list)
    right_groups: dict[tuple[str, ...], list[Row]] = defaultdict(list)
    for row in left:
        left_groups[key(row)].append(row)
    for row in right:
        right_groups[key(row)].append(row)
    pairs = []
    left_only = []
    right_only = []
    assignment_cost = (0, 0, 0)
    duplicate_traces = []
    for identity in sorted(set(left_groups) | set(right_groups)):
        group_left = left_groups.get(identity, [])
        group_right = right_groups.get(identity, [])
        group_pairs, group_left_only, group_right_only, group_cost = _assign_group(
            group_left, group_right, projector,
        )
        pairs.extend(group_pairs)
        left_only.extend(group_left_only)
        right_only.extend(group_right_only)
        assignment_cost = _add_cost(assignment_cost, group_cost)
        if len(group_left) > 1 or len(group_right) > 1:
            duplicate_traces.append({
                "identity": identity,
                "left": [row.source_ref for row in group_left],
                "right": [row.source_ref for row in group_right],
                "pairs": [[a.source_ref, b.source_ref] for a, b in group_pairs],
                "left_only": [row.source_ref for row in group_left_only],
                "right_only": [row.source_ref for row in group_right_only],
                "cost": group_cost,
            })
    pairs.sort(key=lambda pair: (pair[0].route, pair[0].source_index, pair[1].source_index))
    left_only.sort(key=lambda row: (row.route, row.source_index))
    right_only.sort(key=lambda row: (row.route, row.source_index))
    return pairs, left_only, right_only, {
        "left_key_groups": len(left_groups), "right_key_groups": len(right_groups),
        "duplicate_groups": len(duplicate_traces),
        "assignment_cost": assignment_cost,
        "duplicate_trace_sha256": hashlib.sha256(_json_bytes(duplicate_traces)).hexdigest(),
        "duplicate_traces": duplicate_traces,
    }


def _comparison(
    left: Sequence[Row], right: Sequence[Row], label: str,
    key_policy: str,
) -> dict[str, object]:
    if key_policy == "same_source_base_pm":
        key = lambda row: (row.route, row.county, row.pm_base)
        projector = _same_source_values
        fields = SAME_SOURCE_FIELDS
        left_values = right_values = _same_source_values
        asserted = set(fields)
    elif key_policy == "full_pm_vs_tsn":
        key = lambda row: (row.route, row.county, row.pm_full)
        left_values = lambda row: _tsn_values(row, tsmis_side=True)
        right_values = lambda row: _tsn_values(row, tsmis_side=False)
        projector = lambda row: (
            left_values(row) if row.kind == "tsmis"
            else right_values(row)
        )
        fields = VALUE_FIELDS
        asserted = set(ASSERTED_VS_TSN_FIELDS)
    elif key_policy == "base_pm_vs_tsn_probe":
        key = lambda row: (row.route, row.county, row.pm_base)
        left_values = lambda row: _tsn_values(row, tsmis_side=True)
        right_values = lambda row: _tsn_values(row, tsmis_side=False)
        projector = lambda row: (
            left_values(row) if row.kind == "tsmis"
            else right_values(row)
        )
        fields = VALUE_FIELDS
        asserted = set(ASSERTED_VS_TSN_FIELDS)
    else:
        raise DraftError(f"unknown key policy {key_policy}")

    pairs, left_only, right_only, pairing = _pair(left, right, key, projector)
    all_field_counts: Counter[str] = Counter()
    asserted_field_counts: Counter[str] = Counter()
    differing_pairs = []
    all_differing_rows = asserted_differing_rows = 0
    for left_row, right_row in pairs:
        left_projected = left_values(left_row)
        right_projected = right_values(right_row)
        differing = [
            field for field, a, b in zip(fields, left_projected, right_projected, strict=True)
            if a != b
        ]
        asserted_differing = [field for field in differing if field in asserted]
        if differing:
            all_differing_rows += 1
            all_field_counts.update(differing)
        if asserted_differing:
            asserted_differing_rows += 1
            asserted_field_counts.update(asserted_differing)
        if differing:
            differing_pairs.append({
                "identity": key(left_row),
                "left_ref": left_row.source_ref, "right_ref": right_row.source_ref,
                "left_pm_full": left_row.pm_full, "right_pm_full": right_row.pm_full,
                "left_values": left_projected, "right_values": right_projected,
                "differing_fields": differing,
                "asserted_differing_fields": asserted_differing,
                "left_kind": left_row.kind, "right_kind": right_row.kind,
            })
    return {
        "label": label, "key_policy": key_policy, "fields": list(fields),
        "asserted_fields": sorted(asserted),
        "context_fields": [field for field in fields if field not in asserted],
        "left_rows": len(left), "right_rows": len(right), "paired_rows": len(pairs),
        "left_only_rows": len(left_only), "right_only_rows": len(right_only),
        "all_field_differing_rows": all_differing_rows,
        "all_field_difference_cells": sum(all_field_counts.values()),
        "all_field_difference_counts": dict(sorted(all_field_counts.items())),
        "asserted_differing_rows": asserted_differing_rows,
        "asserted_difference_cells": sum(asserted_field_counts.values()),
        "asserted_field_difference_counts": dict(sorted(asserted_field_counts.items())),
        "left_only": [
            {"ref": row.source_ref, "route": row.route, "county": row.county,
             "pm": row.pm_full, "values": projector(row), "kind": row.kind}
            for row in left_only
        ],
        "right_only": [
            {"ref": row.source_ref, "route": row.route, "county": row.county,
             "pm": row.pm_full, "values": projector(row), "kind": row.kind}
            for row in right_only
        ],
        "differing_pairs": differing_pairs,
        "pairing": pairing,
    }


def _raw_vs_normalized(raw: Sequence[Row], normalized: Sequence[Row]) -> dict[str, object]:
    if len(raw) != len(normalized):
        raise DraftError("raw projected and normalized row counts differ")
    differences = []
    fields = ("Route", "County", "PM", *VALUE_FIELDS)
    counts: Counter[str] = Counter()
    for ordinal, (left, right) in enumerate(zip(raw, normalized, strict=True), 1):
        left_values = (left.route, left.county, left.pm_full, *left.values)
        right_values = (right.route, right.county, right.pm_full, *right.values)
        differing = [
            field for field, a, b in zip(fields, left_values, right_values, strict=True)
            if a != b
        ]
        if differing:
            counts.update(differing)
            differences.append({
                "ordinal": ordinal, "raw_ref": left.source_ref,
                "normalized_ref": right.source_ref,
                "raw_values": left_values, "normalized_values": right_values,
                "differing_fields": differing,
            })
    return {
        "rows": len(raw), "differing_rows": len(differences),
        "difference_cells": sum(counts.values()),
        "field_difference_counts": dict(sorted(counts.items())),
        "differences": differences,
    }


def _same_source_events(excel: Sequence[Row], pdf: Sequence[Row]) -> dict[str, object]:
    excel_groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    pdf_groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    for row in excel:
        excel_groups[(row.route, row.county, row.pm_base)].append(row)
    for row in pdf:
        pdf_groups[(row.route, row.county, row.pm_base)].append(row)
    excel_by_occurrence = {
        (*identity, index): row
        for identity, rows in excel_groups.items()
        for index, row in enumerate(rows, 1)
    }
    pdf_by_occurrence = {
        (*identity, index): row
        for identity, rows in pdf_groups.items()
        for index, row in enumerate(rows, 1)
    }
    pdf_by_route: dict[str, list[Row]] = defaultdict(list)
    for row in pdf:
        pdf_by_route[row.route].append(row)
    row_identity = {
        id(row): (*identity, index)
        for identity, rows in pdf_groups.items()
        for index, row in enumerate(rows, 1)
    }
    classes: Counter[str] = Counter()
    events = []
    linked_pdf_e_refs = set()
    for route, rows in pdf_by_route.items():
        for index, annotation in enumerate(rows):
            if not annotation.values[-1].startswith("EQUATES TO"):
                continue
            if index + 1 >= len(rows):
                raise DraftError(f"PDF equate is final route row: {annotation.source_ref}")
            following = rows[index + 1]
            annotation_identity = row_identity[id(annotation)]
            following_identity = row_identity[id(following)]
            excel_annotation = excel_by_occurrence[annotation_identity]
            excel_following = excel_by_occurrence[following_identity]
            if annotation.pm_suffix or following.pm_suffix != "E":
                raise DraftError(f"PDF equate topology changed: {annotation.source_ref}")
            linked_pdf_e_refs.add(following.source_ref)
            state = (
                excel_annotation.pm_suffix, annotation.pm_suffix,
                excel_following.pm_suffix, following.pm_suffix,
            )
            if state == ("", "", "E", "E"):
                category = "same_convention"
            elif state == ("E", "", "", "E"):
                category = "suffix_moved_between_annotation_and_following"
            elif state == ("", "", "", "E"):
                category = "pdf_only_suffix_on_following"
            else:
                raise DraftError(f"unknown equate seating class {state}: {annotation.source_ref}")
            classes[category] += 1
            events.append({
                "category": category,
                "pdf_annotation_ref": annotation.source_ref,
                "excel_annotation_ref": excel_annotation.source_ref,
                "pdf_following_ref": following.source_ref,
                "excel_following_ref": excel_following.source_ref,
                "annotation_identity": annotation_identity,
                "following_identity": following_identity,
                "excel_annotation_suffix": excel_annotation.pm_suffix,
                "pdf_annotation_suffix": annotation.pm_suffix,
                "excel_following_suffix": excel_following.pm_suffix,
                "pdf_following_suffix": following.pm_suffix,
            })
    unlinked_pdf_e = [
        row.source_ref for row in pdf
        if row.pm_suffix == "E" and row.source_ref not in linked_pdf_e_refs
    ]
    return {
        "equate_events": len(events), "classes": dict(sorted(classes.items())),
        "unlinked_pdf_e_rows": unlinked_pdf_e,
        "event_ledger_sha256": hashlib.sha256(_json_bytes(events)).hexdigest(),
        "events": events,
    }


def main() -> int:
    bindings = {label: _bind_cache(label) for label in CACHE_BINDINGS}
    tsmis_document = json.loads(TSMIS_CACHE.read_bytes())
    tsn_document = json.loads(TSN_CACHE.read_bytes())
    serialized_tsmis = tsmis_document["rows"]
    excel = _tsmis_rows(serialized_tsmis["current_tsmis_excel"], "current_tsmis_excel")
    historical_excel = _tsmis_rows(
        serialized_tsmis["historical_tsmis_excel_7_8"],
        "historical_tsmis_excel_7_8",
    )
    pdf = _tsmis_rows(serialized_tsmis["current_tsmis_pdf"], "current_tsmis_pdf")
    raw_tsn, unknown_tsn = _raw_tsn_rows(tsn_document["raw_records"])
    normalized_tsn = _normalized_tsn_rows(tsn_document["normalized"]["rows"])

    source_parity = _comparison(
        excel, pdf, "current TSMIS Excel vs PDF semantic-row parity",
        "same_source_base_pm",
    )
    events = _same_source_events(excel, pdf)
    raw_normalized = _raw_vs_normalized(raw_tsn, normalized_tsn)
    comparisons = {
        "excel_vs_raw_tsn_full_pm": _comparison(
            excel, raw_tsn, "current TSMIS Excel vs authoritative raw TSN", "full_pm_vs_tsn",
        ),
        "pdf_vs_raw_tsn_full_pm": _comparison(
            pdf, raw_tsn, "current TSMIS PDF vs authoritative raw TSN", "full_pm_vs_tsn",
        ),
        "excel_vs_normalized_tsn_full_pm": _comparison(
            excel, normalized_tsn, "current TSMIS Excel vs normalized TSN", "full_pm_vs_tsn",
        ),
        "pdf_vs_normalized_tsn_full_pm": _comparison(
            pdf, normalized_tsn, "current TSMIS PDF vs normalized TSN", "full_pm_vs_tsn",
        ),
        "historical_excel_vs_raw_tsn_full_pm": _comparison(
            historical_excel, raw_tsn,
            "historical July-8 TSMIS Excel vs authoritative raw TSN",
            "full_pm_vs_tsn",
        ),
        "historical_excel_vs_normalized_tsn_full_pm": _comparison(
            historical_excel, normalized_tsn,
            "historical July-8 TSMIS Excel vs normalized TSN",
            "full_pm_vs_tsn",
        ),
        "excel_vs_raw_tsn_base_pm_probe": _comparison(
            excel, raw_tsn, "identity probe: Excel vs raw TSN without E suffix", "base_pm_vs_tsn_probe",
        ),
        "pdf_vs_raw_tsn_base_pm_probe": _comparison(
            pdf, raw_tsn, "identity probe: PDF vs raw TSN without E suffix", "base_pm_vs_tsn_probe",
        ),
    }
    result = {
        "audit": "Stage 8 Highway Sequence comparison development analysis",
        "not_an_acceptance_artifact": True,
        "bindings": bindings,
        "datasets": {
            "current_tsmis_excel": len(excel), "current_tsmis_pdf": len(pdf),
            "historical_tsmis_excel_7_8": len(historical_excel),
            "raw_tsn_known_county": len(raw_tsn),
            "raw_tsn_unknown_county": len(unknown_tsn),
            "normalized_tsn": len(normalized_tsn),
        },
        "raw_tsn_unknown_county_records": [asdict(row) for row in unknown_tsn],
        "same_source_parity": source_parity,
        "same_source_equate_events": events,
        "raw_vs_normalized_tsn": raw_normalized,
        "tsmis_vs_tsn": comparisons,
    }
    DEFAULT_OUTPUT.write_bytes(_json_bytes(result))
    print(
        "PASS Highway Sequence comparison draft: "
        f"same-source {source_parity['paired_rows']:,} paired / "
        f"{source_parity['left_only_rows']}/{source_parity['right_only_rows']} one-sided; "
        f"raw TSN {len(raw_tsn):,}+{len(unknown_tsn)} unknown; output {DEFAULT_OUTPUT}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DraftError as exc:
        print(f"FAIL Highway Sequence comparison draft: {exc}")
        raise SystemExit(1)

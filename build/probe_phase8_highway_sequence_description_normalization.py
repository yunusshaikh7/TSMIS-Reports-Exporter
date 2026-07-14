#!/usr/bin/env python3
"""Source-bound development probe for Highway Sequence Description handling.

This is deliberately *not* an acceptance oracle.  It consumes two frozen JSON
row caches to make a narrow CMP-AUD-204/205 proof inexpensive to replay.  The
final Highway Sequence acceptance artifact must independently reparse the
immutable Excel/PDF/TSN sources.

No product parser or comparator is imported.  The current product module is
identity-bound, and its leading-numeric-prefix rewrite is modeled locally so
that the affected source population can be measured without trusting the code
under audit.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Callable, Iterable, Mapping, Sequence

from openpyxl.utils.escape import unescape as xlsx_unescape


REPO_ROOT = Path(__file__).resolve().parents[1]
VISUAL_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd"
)
SOURCE_CACHE = VISUAL_ROOT / "phase8_highway_sequence_source_rows_draft_r1.json"
TSN_CACHE = VISUAL_ROOT / "phase8_highway_sequence_tsn_rows_draft_r1.json"
NORMALIZED_TSN = (
    VISUAL_ROOT
    / "phase4_tsn_rebaseline"
    / "raw-2026-07-12-r7"
    / "highway_sequence"
    / "consolidated"
    / "tsn_highway_sequence_normalized.xlsx"
)
PRODUCT_MODULE = REPO_ROOT / "scripts" / "compare_highway_sequence_tsn.py"
DEFAULT_OUTPUT = (
    VISUAL_ROOT
    / "phase8_highway_sequence_description_normalization_probe_r1.json"
)

EXPECTED_IDENTITIES = {
    "source_row_cache": {
        "path": SOURCE_CACHE,
        "bytes": 49_304_637,
        "sha256": "564cf21972aeaf461811095997524c2d02f3ca4f238bb8da8b715415df2762f8",
    },
    "tsn_row_cache": {
        "path": TSN_CACHE,
        "bytes": 28_829_216,
        "sha256": "b18d2e077b79920cb1f687f06f8193b25e1d8cd2ebeb1d071b84c22b372598a7",
    },
    "accepted_normalized_tsn": {
        "path": NORMALIZED_TSN,
        "bytes": 2_536_901,
        "sha256": "9dc84c661a9284131baf928767e210a6d708c0a338819fca2b69b907f85dd041",
    },
    "product_compare_highway_sequence_tsn": {
        "path": PRODUCT_MODULE,
        "bytes": 12_464,
        "sha256": "08ae1592a060ca8b6be9bf5d6521629c66460e6d4b5381fbde3425cffaeaea03",
    },
}

EXPECTED_CAPTURE_MANIFEST = {
    "bytes": 145_434,
    "sha256": "6f41566c350797f135916e0d5b9f0de434e000faa5882ae1309d866f87cc6534",
}
EXPECTED_LEDGER = {
    "wire_bytes": 7_517,
    "sha256": "5dacffd43c62ea8001796e5b4d87d1290b07cd7084861f26cf8cf047d452eab7",
    "content_sorted_sha256": (
        "59f3afe3336d07daaf5fd6e228b060ab5e822c1040f2e21e3dd2fca88b9d11e7"
    ),
}
EXPECTED_PADDING_KEYS = (
    ("005", "ORA", "020.746"),
    ("070", "YUB", "000.204"),
    ("073", "ORA", "016.689"),
)
EXPECTED_COLLAPSED_DUPLICATE_KEYS = (
    ("028", "PLA", "009.880"),
    ("145", "FRE", "033.129"),
)

PREFIX_RE = re.compile(r"^(\d{1,3}[A-Z]?)/")
PREFIX_WITH_PADDING_RE = re.compile(r"^(\d{1,3}[A-Z]?)/(\s+)")
PM_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}E?$")
VALUE_FIELDS = ("City", "HG", "FT", "Distance To Next Point", "Description")


class ProbeError(RuntimeError):
    """A source binding or expected corpus invariant failed."""


@dataclass(frozen=True)
class Row:
    source: str
    source_ref: str
    source_index: int
    route: str
    county: str
    pm: str
    values: tuple[str, ...]
    raw_description: str
    xlsx_description: bool

    @property
    def description(self) -> str:
        return self.values[-1]

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.route, self.county, self.pm


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeError(message)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def _identity(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise ProbeError(f"identity-bound input is a symlink: {path}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ProbeError(f"identity-bound input is not an ordinary file: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": info.st_size,
        "sha256": _sha_file(path),
        "mtime_ns": info.st_mtime_ns,
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def _bind_inputs() -> dict[str, dict[str, object]]:
    observed: dict[str, dict[str, object]] = {}
    for label, expected in EXPECTED_IDENTITIES.items():
        item = _identity(Path(expected["path"]))
        _require(
            item["bytes"] == expected["bytes"]
            and item["sha256"] == expected["sha256"]
            and item["path"] == str(Path(expected["path"]).resolve()),
            f"{label} identity drift: {item}",
        )
        observed[label] = item
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
        raise ProbeError(f"invalid route: {value!r}")
    return match.group(1).zfill(3) + match.group(2).upper()


def _county(value: object) -> str:
    return _text(value).rstrip(".").upper()


def _semantic_tsmis_description(
    value: object, route: str, *, xlsx: bool, trim_padding: bool
) -> str:
    text = _space(value, xlsx=xlsx)
    match = PREFIX_RE.match(text)
    if match is not None and _route(match.group(1)) == route:
        text = text[match.end():]
        if trim_padding:
            text = text.lstrip()
    return text


def _product_description(value: object) -> str:
    """Local model of the exact identity-bound product's symmetric rewrite."""
    text = _text(value)
    text = re.sub(r"[\t\n\r\f\v]", " ", text).strip()
    return re.sub(r"\s+", " ", PREFIX_RE.sub("", text)).strip()


def _tsmis_rows(
    serialized: Sequence[Mapping[str, object]], source: str
) -> list[Row]:
    is_xlsx = "excel" in source
    rows: list[Row] = []
    for item in serialized:
        raw = list(item["values"])
        _require(len(raw) == 9, f"{item['source_ref']}: TSMIS row width drift")
        route = _route(item["route"])
        pm = (_text(raw[2]) + _text(raw[3]) + _text(raw[4])).upper()
        # TSMIS contains a small number of report rows with a genuinely blank PM;
        # keep that source fact as the empty key component rather than inventing one.
        _require(
            pm == "" or bool(PM_RE.fullmatch(pm)),
            f"{item['source_ref']}: invalid PM {pm!r}",
        )
        raw_description = _text(raw[8])
        rows.append(Row(
            source=source,
            source_ref=str(item["source_ref"]),
            source_index=int(item["source_index"]),
            route=route,
            county=_county(raw[0]),
            pm=pm,
            values=(
                _space(raw[1], xlsx=is_xlsx),
                _space(raw[5], xlsx=is_xlsx),
                _space(raw[6], xlsx=is_xlsx),
                _space(raw[7], xlsx=is_xlsx),
                _semantic_tsmis_description(
                    raw[8], route, xlsx=is_xlsx, trim_padding=True
                ),
            ),
            raw_description=raw_description,
            xlsx_description=is_xlsx,
        ))
    return rows


def _raw_tsn_rows(
    serialized: Sequence[Mapping[str, object]],
) -> tuple[list[Row], list[Row]]:
    known: list[Row] = []
    unknown: list[Row] = []
    for ordinal, item in enumerate(serialized, 1):
        pm = _text(item.get("pm")).upper()
        _require(bool(PM_RE.fullmatch(pm)), f"raw TSN row {ordinal}: invalid PM {pm!r}")
        description = _space(item.get("description"))
        row = Row(
            source="raw_tsn",
            source_ref=(
                f"{item['member']}:page:{item['physical_page']}:line:{item['line']}"
            ),
            source_index=ordinal,
            route=_route(item["route"]),
            county=_county(item.get("county")),
            pm=pm,
            values=(
                _space(item.get("city")),
                _space(item.get("hg")),
                _space(item.get("ft")),
                _space(item.get("distance")),
                description,
            ),
            raw_description=_text(item.get("description")),
            xlsx_description=False,
        )
        (known if row.county else unknown).append(row)
    return known, unknown


def _normalized_tsn_rows(serialized: Sequence[Mapping[str, object]]) -> list[Row]:
    rows: list[Row] = []
    for item in serialized:
        raw = list(item["values"])
        _require(len(raw) == 8, f"normalized TSN row {item['source_row']}: width drift")
        pm = _text(raw[2]).upper()
        _require(
            bool(PM_RE.fullmatch(pm)),
            f"normalized TSN row {item['source_row']}: invalid PM {pm!r}",
        )
        rows.append(Row(
            source="normalized_tsn",
            source_ref=f"normalized:row:{item['source_row']}",
            source_index=int(item["source_row"]),
            route=_route(raw[0]),
            county=_county(raw[1]),
            pm=pm,
            values=tuple(_space(value) for value in raw[3:8]),
            raw_description=_text(raw[7]),
            xlsx_description=False,
        ))
    return rows


def _char_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    return _char_distance_unequal(left, right)


@lru_cache(maxsize=None)
def _char_distance_unequal(left: str, right: str) -> int:
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


def _pair_cost(
    left: Row, right: Row, left_position: int, right_position: int
) -> tuple[int, int, int]:
    return (
        sum(a != b for a, b in zip(left.values, right.values, strict=True)),
        sum(
            _char_distance(a, b)
            for a, b in zip(left.values, right.values, strict=True)
        ),
        abs(left_position - right_position),
    )


def _add_cost(
    left: tuple[int, int, int], right: tuple[int, int, int]
) -> tuple[int, int, int]:
    return tuple(a + b for a, b in zip(left, right, strict=True))


def _assign_group(
    left: Sequence[Row], right: Sequence[Row]
) -> tuple[list[tuple[Row, Row]], list[Row], list[Row], tuple[int, int, int]]:
    if not left or not right:
        return [], list(left), list(right), (0, 0, 0)
    swapped = len(left) > len(right)
    small = right if swapped else left
    large = left if swapped else right
    _require(
        len(large) <= 12,
        f"exact-DP duplicate group exceeds audited cap: {len(left)}x{len(right)}",
    )

    @lru_cache(maxsize=None)
    def solve(
        index: int, used_mask: int
    ) -> tuple[tuple[int, int, int], tuple[tuple[int, int], ...]]:
        if index == len(small):
            return (0, 0, 0), ()
        best = None
        for candidate in range(len(large)):
            if used_mask & (1 << candidate):
                continue
            tail_cost, tail_pairs = solve(index + 1, used_mask | (1 << candidate))
            if swapped:
                pair_cost = _pair_cost(
                    large[candidate], small[index], candidate, index
                )
            else:
                pair_cost = _pair_cost(
                    small[index], large[candidate], index, candidate
                )
            value = (
                _add_cost(pair_cost, tail_cost),
                ((index, candidate), *tail_pairs),
            )
            if best is None or value < best:
                best = value
        if best is None:
            raise ProbeError("exact-DP assignment found no candidate")
        return best

    total_cost, assignments = solve(0, 0)
    pairs: list[tuple[Row, Row]] = []
    for small_index, large_index in assignments:
        if swapped:
            pairs.append((large[large_index], small[small_index]))
        else:
            pairs.append((small[small_index], large[large_index]))
    pairs.sort(key=lambda pair: (pair[0].source_index, pair[1].source_index))
    paired_left = {id(pair[0]) for pair in pairs}
    paired_right = {id(pair[1]) for pair in pairs}
    return (
        pairs,
        [row for row in left if id(row) not in paired_left],
        [row for row in right if id(row) not in paired_right],
        total_cost,
    )


def _pair(
    left: Sequence[Row], right: Sequence[Row]
) -> tuple[list[tuple[Row, Row]], list[Row], list[Row], dict[str, object]]:
    left_groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    right_groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    for row in left:
        left_groups[row.identity].append(row)
    for row in right:
        right_groups[row.identity].append(row)

    pairs: list[tuple[Row, Row]] = []
    left_only: list[Row] = []
    right_only: list[Row] = []
    assignment_cost = (0, 0, 0)
    duplicate_groups = 0
    for identity in sorted(set(left_groups) | set(right_groups)):
        group_left = left_groups.get(identity, [])
        group_right = right_groups.get(identity, [])
        if len(group_left) > 1 or len(group_right) > 1:
            duplicate_groups += 1
        group_pairs, group_left_only, group_right_only, group_cost = _assign_group(
            group_left, group_right
        )
        pairs.extend(group_pairs)
        left_only.extend(group_left_only)
        right_only.extend(group_right_only)
        assignment_cost = _add_cost(assignment_cost, group_cost)
    pairs.sort(
        key=lambda pair: (
            pair[0].route, pair[0].source_index, pair[1].source_index
        )
    )
    left_only.sort(key=lambda row: (row.route, row.source_index))
    right_only.sort(key=lambda row: (row.route, row.source_index))
    return pairs, left_only, right_only, {
        "duplicate_groups": duplicate_groups,
        "assignment_cost": list(assignment_cost),
    }


def _false_clean_record(left: Row, right: Row) -> dict[str, object] | None:
    if left.description == right.description or PREFIX_RE.match(right.description) is None:
        return None
    stripped_tsn = _product_description(right.description)
    if stripped_tsn != left.description:
        return None
    _require(
        _product_description(left.raw_description) == stripped_tsn,
        f"{left.identity}: modeled product sides do not actually false-clean",
    )
    return {
        "identity": list(left.identity),
        "tsmis": left.description,
        "tsn": right.description,
    }


def _probe_leg(left: Sequence[Row], right: Sequence[Row], label: str) -> dict[str, object]:
    pairs, left_only, right_only, pairing = _pair(left, right)
    description_differences = 0
    buggy_description_differences = 0
    false_clean: list[dict[str, object]] = []
    references: list[dict[str, object]] = []
    padding_pair_keys: set[tuple[str, str, str]] = set()
    for left_row, right_row in pairs:
        if left_row.description != right_row.description:
            description_differences += 1
        buggy_description = _semantic_tsmis_description(
            left_row.raw_description,
            left_row.route,
            xlsx=left_row.xlsx_description,
            trim_padding=False,
        )
        if buggy_description != right_row.description:
            buggy_description_differences += 1
        if (
            left_row.identity in EXPECTED_PADDING_KEYS
            and buggy_description != left_row.description
            and left_row.description == right_row.description
        ):
            padding_pair_keys.add(left_row.identity)
        record = _false_clean_record(left_row, right_row)
        if record is not None:
            false_clean.append(record)
            references.append({
                "identity": list(left_row.identity),
                "tsmis_ref": left_row.source_ref,
                "tsn_ref": right_row.source_ref,
            })

    content_sorted = sorted(
        false_clean,
        key=lambda item: (tuple(item["identity"]), item["tsmis"], item["tsn"]),
    )
    return {
        "label": label,
        "left_rows": len(left),
        "right_rows": len(right),
        "paired_rows": len(pairs),
        "left_only_rows": len(left_only),
        "right_only_rows": len(right_only),
        "key_policy": "Route + normalized County + complete prefix/base/suffix PM",
        "assignment": pairing,
        "description_difference_rows": description_differences,
        "buggy_untrimmed_description_difference_rows": buggy_description_differences,
        "padding_artifact_delta": (
            buggy_description_differences - description_differences
        ),
        "padding_artifact_pair_keys": [list(key) for key in sorted(padding_pair_keys)],
        "product_false_clean_rows": len(false_clean),
        "product_false_clean_content_sorted_sha256": _sha_bytes(
            _canonical(content_sorted)
        ),
        "product_false_clean_records": false_clean,
        "product_false_clean_references": references,
    }


def _prefix_population(rows: Sequence[Row], label: str) -> dict[str, object]:
    selected = [row for row in rows if PREFIX_RE.match(row.description)]
    records = []
    owning = 0
    cross_route = 0
    changed = 0
    nested = []
    for row in selected:
        match = PREFIX_RE.match(row.description)
        if match is None:
            raise ProbeError("internal prefix population error")
        token_route = _route(match.group(1))
        relation = "owning-route" if token_route == row.route else "cross-route"
        if relation == "owning-route":
            owning += 1
        else:
            cross_route += 1
        product = _product_description(row.description)
        changed += product != row.description
        nested_prefix = PREFIX_RE.match(product) is not None
        record = {
            "identity": list(row.identity),
            "description": row.description,
            "prefix_token": match.group(1),
            "relation": relation,
            "product_description": product,
            "nested_prefix_survives": nested_prefix,
        }
        records.append(record)
        if nested_prefix:
            nested.append({**record, "source_ref": row.source_ref})

    context_multiset = sorted(
        [list(row.identity) + [row.description] for row in selected]
    )
    description_multiset = sorted(row.description for row in selected)
    return {
        "label": label,
        "rows": len(selected),
        "distinct_descriptions": len(set(description_multiset)),
        "owning_route_prefixes": owning,
        "cross_route_prefixes": cross_route,
        "changed_by_product": changed,
        "numeric_prefixes_remaining_after_product": len(nested),
        "context_multiset_sha256": _sha_bytes(_canonical(context_multiset)),
        "description_multiset_sha256": _sha_bytes(_canonical(description_multiset)),
        "context_multiset": context_multiset,
        "description_multiset": description_multiset,
        "nested_prefix_records": nested,
        "records": sorted(
            records,
            key=lambda item: (
                tuple(item["identity"]), item["description"], item["relation"]
            ),
        ),
    }


def _collapsed_duplicate_distinctions(rows: Sequence[Row]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    for row in rows:
        groups[row.identity].append(row)
    collapsed = []
    for identity, group in groups.items():
        product_groups: dict[str, set[str]] = defaultdict(set)
        for row in group:
            product_groups[_product_description(row.description)].add(row.description)
        for product, originals in product_groups.items():
            if len(originals) > 1 and any(PREFIX_RE.match(item) for item in originals):
                collapsed.append({
                    "identity": list(identity),
                    "product_description": product,
                    "source_descriptions": sorted(originals),
                })
    return sorted(collapsed, key=lambda item: tuple(item["identity"]))


def _padding_artifacts(rows: Sequence[Row]) -> list[dict[str, object]]:
    artifacts = []
    for row in rows:
        raw = _space(row.raw_description, xlsx=row.xlsx_description)
        match = PREFIX_WITH_PADDING_RE.match(raw)
        if match is None or _route(match.group(1)) != row.route:
            continue
        artifacts.append({
            "identity": list(row.identity),
            "source_ref": row.source_ref,
            "raw_description": row.raw_description,
            "untrimmed_projection": _semantic_tsmis_description(
                row.raw_description,
                row.route,
                xlsx=row.xlsx_description,
                trim_padding=False,
            ),
            "corrected_projection": row.description,
            "separator_whitespace_length": len(match.group(2)),
        })
    return sorted(artifacts, key=lambda item: tuple(item["identity"]))


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def run(output: Path) -> dict[str, object]:
    input_before = _bind_inputs()
    with SOURCE_CACHE.open("r", encoding="utf-8") as handle:
        source_document = json.load(handle)
    with TSN_CACHE.open("r", encoding="utf-8") as handle:
        tsn_document = json.load(handle)

    _require(
        source_document.get("not_an_acceptance_artifact") is True,
        "source-row cache lost its non-acceptance marker",
    )
    _require(
        tsn_document.get("not_an_acceptance_artifact") is True,
        "TSN-row cache lost its non-acceptance marker",
    )
    _require(
        source_document.get("capture_manifest") == EXPECTED_CAPTURE_MANIFEST,
        "source-row cache capture-manifest binding drift",
    )
    declared_normalized = tsn_document.get("bindings", {}).get("normalized", {})
    _require(
        declared_normalized.get("canonical_path") == str(NORMALIZED_TSN)
        and declared_normalized.get("size") == 2_536_901
        and declared_normalized.get("sha256")
        == EXPECTED_IDENTITIES["accepted_normalized_tsn"]["sha256"],
        "TSN cache no longer binds the accepted normalized workbook identity",
    )

    source_rows = source_document.get("rows")
    _require(isinstance(source_rows, dict), "source cache row envelope drift")
    excel = _tsmis_rows(source_rows["current_tsmis_excel"], "current_tsmis_excel")
    pdf = _tsmis_rows(source_rows["current_tsmis_pdf"], "current_tsmis_pdf")
    historical_excel = _tsmis_rows(
        source_rows["historical_tsmis_excel_7_8"],
        "historical_tsmis_excel_7_8",
    )
    raw_tsn, raw_unknown_county = _raw_tsn_rows(tsn_document["raw_records"])
    normalized_tsn = _normalized_tsn_rows(tsn_document["normalized"]["rows"])

    _require(len(excel) == 60_494, "current Excel row census drift")
    _require(len(pdf) == 60_493, "current PDF row census drift")
    _require(len(historical_excel) == 60_493, "historical Excel row census drift")
    _require(len(raw_tsn) == 69_758, "known-county raw TSN row census drift")
    _require(len(raw_unknown_county) == 46, "unknown-county raw TSN census drift")
    _require(len(normalized_tsn) == 69_758, "normalized TSN row census drift")

    raw_prefix = _prefix_population(raw_tsn, "authoritative raw TSN")
    normalized_prefix = _prefix_population(
        normalized_tsn, "accepted normalized TSN"
    )
    for prefix_result in (raw_prefix, normalized_prefix):
        _require(prefix_result["rows"] == 154, "numeric-prefix census drift")
        _require(
            prefix_result["owning_route_prefixes"] == 108,
            "owning-route numeric-prefix census drift",
        )
        _require(
            prefix_result["cross_route_prefixes"] == 46,
            "cross-route numeric-prefix census drift",
        )
        _require(
            prefix_result["changed_by_product"] == 154,
            "product no longer changes every numeric-prefix TSN Description",
        )
        _require(
            prefix_result["numeric_prefixes_remaining_after_product"] == 2,
            "nested-prefix residue census drift",
        )
    _require(
        raw_prefix["context_multiset"] == normalized_prefix["context_multiset"],
        "raw/normalized TSN numeric-prefix contextual multiset drift",
    )
    _require(
        raw_prefix["description_multiset"]
        == normalized_prefix["description_multiset"],
        "raw/normalized TSN numeric-prefix Description multiset drift",
    )

    collapsed_raw = _collapsed_duplicate_distinctions(raw_tsn)
    collapsed_normalized = _collapsed_duplicate_distinctions(normalized_tsn)
    _require(
        collapsed_raw == collapsed_normalized,
        "raw/normalized collapsed duplicate distinction drift",
    )
    _require(
        tuple(tuple(item["identity"]) for item in collapsed_raw)
        == EXPECTED_COLLAPSED_DUPLICATE_KEYS,
        "product-collapsed duplicate-key census drift",
    )

    padding = {
        "current_tsmis_excel": _padding_artifacts(excel),
        "current_tsmis_pdf": _padding_artifacts(pdf),
        "historical_tsmis_excel_7_8": _padding_artifacts(historical_excel),
    }
    for label, artifacts in padding.items():
        _require(
            tuple(tuple(item["identity"]) for item in artifacts)
            == EXPECTED_PADDING_KEYS,
            f"{label}: route/slash/padding artifact census drift",
        )
        _require(
            all(
                item["untrimmed_projection"].startswith(" ")
                and not item["corrected_projection"].startswith(" ")
                for item in artifacts
            ),
            f"{label}: delimiter-padding correction behavior drift",
        )

    legs = {
        "excel_vs_raw_tsn": _probe_leg(excel, raw_tsn, "Excel vs raw TSN"),
        "excel_vs_normalized_tsn": _probe_leg(
            excel, normalized_tsn, "Excel vs normalized TSN"
        ),
        "pdf_vs_raw_tsn": _probe_leg(pdf, raw_tsn, "PDF vs raw TSN"),
        "pdf_vs_normalized_tsn": _probe_leg(
            pdf, normalized_tsn, "PDF vs normalized TSN"
        ),
    }
    expected_leg_counts = {
        "excel_vs_raw_tsn": (57_072, 3_422, 12_686, 4_894),
        "excel_vs_normalized_tsn": (57_072, 3_422, 12_686, 4_894),
        "pdf_vs_raw_tsn": (57_505, 2_988, 12_253, 4_916),
        "pdf_vs_normalized_tsn": (57_505, 2_988, 12_253, 4_916),
    }
    for label, leg in legs.items():
        expected = expected_leg_counts[label]
        observed = (
            leg["paired_rows"], leg["left_only_rows"],
            leg["right_only_rows"], leg["description_difference_rows"],
        )
        _require(observed == expected, f"{label}: pairing/Description census drift")
        _require(
            leg["buggy_untrimmed_description_difference_rows"] == expected[3] + 3,
            f"{label}: CMP-AUD-205 three-row delta drift",
        )
        _require(
            leg["padding_artifact_pair_keys"]
            == [list(key) for key in EXPECTED_PADDING_KEYS],
            f"{label}: padding rows did not reconcile exactly",
        )
        _require(
            leg["product_false_clean_rows"] == 81,
            f"{label}: CMP-AUD-204 false-clean census drift",
        )
        _require(
            leg["product_false_clean_content_sorted_sha256"]
            == EXPECTED_LEDGER["content_sorted_sha256"],
            f"{label}: false-clean content ledger drift",
        )

    canonical_records = legs["excel_vs_raw_tsn"]["product_false_clean_records"]
    canonical_wire = _canonical(canonical_records)
    _require(len(canonical_wire) == EXPECTED_LEDGER["wire_bytes"], "ledger wire length drift")
    _require(
        _sha_bytes(canonical_wire) == EXPECTED_LEDGER["sha256"],
        "canonical 81-row false-clean ledger digest drift",
    )

    input_after = _bind_inputs()
    _require(input_after == input_before, "an identity-bound input changed during probe")

    result: dict[str, object] = {
        "audit": "Highway Sequence Description normalization development probe",
        "artifact_status": "NON_ACCEPTANCE_DEVELOPMENT_PROBE",
        "acceptance_eligible": False,
        "not_an_acceptance_artifact": (
            "This probe consumes frozen development row caches. Final acceptance "
            "must independently reparse immutable raw Excel/PDF/TSN sources."
        ),
        "findings": ["CMP-AUD-204", "CMP-AUD-205"],
        "inputs_before": input_before,
        "inputs_after": input_after,
        "cache_chain": {
            "source_capture_manifest": EXPECTED_CAPTURE_MANIFEST,
            "accepted_normalized_tsn_declared_by_tsn_cache": declared_normalized,
        },
        "modeled_product_rule": {
            "module": str(PRODUCT_MODULE.resolve()),
            "module_sha256": input_before[
                "product_compare_highway_sequence_tsn"
            ]["sha256"],
            "description_prefix_regex": PREFIX_RE.pattern,
            "application": (
                "The bound product applies one symmetric leading-prefix deletion "
                "to both TSMIS and TSN Description values."
            ),
            "product_code_was_not_imported": True,
        },
        "source_census": {
            "current_tsmis_excel": len(excel),
            "current_tsmis_pdf": len(pdf),
            "historical_tsmis_excel_7_8": len(historical_excel),
            "raw_tsn_known_county": len(raw_tsn),
            "raw_tsn_unknown_county": len(raw_unknown_county),
            "normalized_tsn": len(normalized_tsn),
        },
        "numeric_prefix_population": {
            "raw": raw_prefix,
            "normalized": normalized_prefix,
            "raw_and_normalized_context_multisets_identical": True,
            "raw_and_normalized_description_multisets_identical": True,
            "product_collapsed_duplicate_distinctions": collapsed_raw,
        },
        "tsmis_route_slash_padding_artifacts": padding,
        "comparison_legs": legs,
        "canonical_false_clean_ledger": {
            "definition": (
                "Fresh exact-DP Excel-vs-raw pairs in (left route, left source "
                "index, right source index) order; retain Description differences "
                "whose TSN value starts ^(digits{1,3}[A-Z]?)/ and whose first-prefix "
                "deletion plus outer whitespace normalization equals TSMIS; project "
                "only identity, tsmis, and tsn."
            ),
            "serialization": (
                "json.dumps(records, ensure_ascii=False, sort_keys=True, "
                "separators=(',', ':')).encode('utf-8'); no trailing newline"
            ),
            "rows": len(canonical_records),
            "wire_bytes": len(canonical_wire),
            "sha256": _sha_bytes(canonical_wire),
            "content_sorted_sha256": EXPECTED_LEDGER["content_sorted_sha256"],
            "records": canonical_records,
        },
        "invariants": {
            "all_input_identities_stable": True,
            "raw_normalized_prefix_multisets_identical": True,
            "numeric_prefix_rows_each_form": 154,
            "owning_route_prefix_rows_each_form": 108,
            "cross_route_prefix_rows_each_form": 46,
            "product_changed_prefix_rows_each_form": 154,
            "nested_prefix_rows_remaining_each_form": 2,
            "product_collapsed_duplicate_locations": 2,
            "route_slash_padding_artifacts_each_tsmis_form": 3,
            "false_clean_rows_each_current_leg": 81,
            "canonical_ledger_wire_bytes": 7_517,
            "canonical_ledger_sha256": EXPECTED_LEDGER["sha256"],
            "corrected_excel_description_differences_each_tsn_form": 4_894,
            "corrected_pdf_description_differences_each_tsn_form": 4_916,
            "all_checks_passed": True,
        },
    }
    payload = _canonical(result, newline=True)
    _write_atomic(output, payload)
    print(json.dumps({
        "status": "PASS",
        "output": str(output.resolve()),
        "bytes": len(payload),
        "sha256": _sha_bytes(payload),
        "false_clean_rows_per_leg": 81,
        "description_differences": {
            "excel": 4_894,
            "pdf": 4_916,
        },
    }, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    run(arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Independent Phase-3 comparison oracle.

This module deliberately depends only on the Python standard library.  It owns a
small typed model for source rows, canonical cell equality, structured keys,
duplicate assignment, and aggregate counts.  Raw workbook extraction belongs in a
separate adapter; the oracle accepts only already-extracted raw records.

It is test evidence, not application code.  No application comparison, loader,
normalizer, sidecar, or workbook result is an input to this implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any, Iterable, Mapping, Optional, Protocol, Sequence, Tuple


ORDINARY = "ordinary"
MED_WID = "med_wid"
PAIR_CAP = 100_000
_KINDS = frozenset((ORDINARY, MED_WID))
_ASCII_SPACE_RUN = re.compile(r" +")
_MED_WID_TOKEN = re.compile(
    r"(?P<number>[0-9]+(?:\.[0-9]+)?)(?P<suffix>.?)")


@dataclass(frozen=True)
class ValueRule:
    """One key/field normalization rule."""

    name: str
    kind: str = ORDINARY

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("a value rule requires a stable name")
        if self.kind not in _KINDS:
            raise ValueError(f"unsupported equality kind: {self.kind!r}")


@dataclass(frozen=True)
class FieldRule(ValueRule):
    """One displayed field; context fields are non-asserting."""

    asserting: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if type(self.asserting) is not bool:
            raise ValueError("asserting must be a Boolean")


@dataclass(frozen=True)
class OracleSchema:
    """Structured key and displayed-field contract for one oracle run."""

    key_rules: Tuple[ValueRule, ...]
    field_rules: Tuple[FieldRule, ...]

    def __post_init__(self) -> None:
        if not self.key_rules:
            raise ValueError("at least one structured key component is required")
        if any(not isinstance(rule, ValueRule) for rule in self.key_rules):
            raise TypeError("key_rules must contain ValueRule objects")
        if any(not isinstance(rule, FieldRule) for rule in self.field_rules):
            raise TypeError("field_rules must contain FieldRule objects")
        names = [rule.name for rule in self.field_rules]
        if len(names) != len(set(names)):
            raise ValueError("field names must be unique")


@dataclass(frozen=True)
class OracleRow:
    """One source row after extraction but before oracle normalization."""

    source_index: int
    key: Tuple[Any, ...]
    values: Tuple[Any, ...]
    source_ref: str = ""

    def __post_init__(self) -> None:
        if (isinstance(self.source_index, bool)
                or not isinstance(self.source_index, int)
                or self.source_index < 0):
            raise ValueError("source_index must be a non-negative integer")
        if not isinstance(self.key, tuple) or not isinstance(self.values, tuple):
            raise TypeError("OracleRow key and values must be tuples")


class RawRecordAdapter(Protocol):
    """Extraction seam for a later independently implemented corpus reader.

    The adapter may interpret raw column names and side-specific layouts, but it
    must return an :class:`OracleRow`; it must not call an application comparator,
    loader, normalizer, or prior comparison workbook.
    """

    def adapt(self, raw_record: Mapping[str, Any], *, side: str,
              source_index: int, schema: OracleSchema) -> OracleRow:
        ...


@dataclass(frozen=True, order=True)
class NormalizedValue:
    """Hashable canonical scalar.  Blank includes empty/space-only text, not zero."""

    kind: str
    text: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("blank", "text"):
            raise ValueError(f"invalid normalized value kind: {self.kind!r}")
        if self.kind == "blank" and self.text:
            raise ValueError("blank values cannot carry text")


@dataclass(frozen=True)
class CellResult:
    raw_a: Any
    raw_b: Any
    normalized_a: NormalizedValue
    normalized_b: NormalizedValue
    asserting: bool
    equal: bool
    display: str

    @property
    def counts_as_difference(self) -> bool:
        return self.asserting and not self.equal


@dataclass(frozen=True)
class RowResult:
    source_index_a: int
    source_index_b: int
    key: Tuple[NormalizedValue, ...]
    cells: Tuple[CellResult, ...]
    differing_fields: Tuple[str, ...]


@dataclass(frozen=True)
class PairingTrace:
    key: Tuple[NormalizedValue, ...]
    side_a_size: int
    side_b_size: int
    smaller_side: str
    assignment_vector: Tuple[int, ...]
    source_pairs: Tuple[Tuple[int, int], ...]
    total_cost: int
    algorithm: str
    quality: str
    exact: bool
    matrix_cells: int


@dataclass(frozen=True)
class CappedDiagnostic:
    key: Tuple[NormalizedValue, ...]
    side_a_size: int
    side_b_size: int
    cap: int
    fallback: str
    fallback_cost: int


@dataclass(frozen=True)
class OracleCounts:
    known: bool
    paired_rows: int
    side_a_only_rows: int
    side_b_only_rows: int
    differing_rows: int
    differing_cells: int
    per_field_counts: Mapping[str, int] = field(default_factory=dict)
    asserted_cells: int = 0
    context_cells: int = 0

    def __post_init__(self) -> None:
        if type(self.known) is not bool:
            raise ValueError("known must be a Boolean")
        values = (
            self.paired_rows, self.side_a_only_rows, self.side_b_only_rows,
            self.differing_rows, self.differing_cells,
            self.asserted_cells, self.context_cells,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in values):
            raise ValueError("oracle counts must be non-negative integers")
        if self.differing_rows > self.paired_rows:
            raise ValueError("differing rows cannot exceed paired rows")
        if self.differing_cells > self.asserted_cells:
            raise ValueError("differing cells cannot exceed asserted cells")
        if any(not isinstance(name, str) or not name
               or isinstance(value, bool) or not isinstance(value, int) or value < 0
               for name, value in self.per_field_counts.items()):
            raise ValueError("per-field counts must be named non-negative integers")
        if sum(self.per_field_counts.values()) != self.differing_cells:
            raise ValueError("per-field counts must sum to differing_cells")


@dataclass(frozen=True)
class OracleOutcome:
    completion: str
    verdict: str
    counts: OracleCounts
    row_results: Tuple[RowResult, ...]
    side_a_only_indices: Tuple[int, ...]
    side_b_only_indices: Tuple[int, ...]
    pairing_trace: Tuple[PairingTrace, ...]
    pairing_quality: str
    capped_diagnostics: Tuple[CappedDiagnostic, ...]

    def __post_init__(self) -> None:
        if self.completion not in ("complete", "partial", "no_data"):
            raise ValueError("unsupported oracle completion")
        if self.verdict not in ("match", "diff", "unknown"):
            raise ValueError("unsupported oracle verdict")
        if self.pairing_quality not in ("exact", "capped"):
            raise ValueError("unsupported pairing quality")
        if self.completion == "partial" and self.verdict == "match":
            raise ValueError("a partial oracle result cannot certify a match")
        if self.completion == "no_data" and self.verdict != "unknown":
            raise ValueError("no_data must have an unknown verdict")
        if self.verdict == "match" and (
                self.counts.differing_cells
                or self.counts.side_a_only_rows
                or self.counts.side_b_only_rows):
            raise ValueError("match verdict contradicts structured counts")
        if bool(self.capped_diagnostics) != (self.pairing_quality == "capped"):
            raise ValueError("capped diagnostics and quality must agree")


@dataclass(frozen=True)
class GroupPairing:
    pairs: Tuple[Tuple[int, int], ...]
    unmatched_a: Tuple[int, ...]
    unmatched_b: Tuple[int, ...]
    trace: PairingTrace
    capped_diagnostic: Optional[CappedDiagnostic] = None


def adapt_raw_records(raw_records: Iterable[Mapping[str, Any]],
                      adapter: RawRecordAdapter, *, side: str,
                      schema: OracleSchema) -> Tuple[OracleRow, ...]:
    """Apply an external raw-record adapter and validate its narrow output."""
    if side not in ("a", "b"):
        raise ValueError("side must be 'a' or 'b'")
    rows = []
    for source_index, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, Mapping):
            raise TypeError("raw records must be mappings")
        row = adapter.adapt(raw_record, side=side, source_index=source_index,
                            schema=schema)
        if not isinstance(row, OracleRow):
            raise TypeError("raw-record adapter must return OracleRow")
        if row.source_index != source_index:
            raise ValueError("adapter changed the stable source index")
        _validate_row(row, schema)
        rows.append(row)
    return tuple(rows)


def compare_raw_records(schema: OracleSchema,
                        raw_a: Iterable[Mapping[str, Any]],
                        raw_b: Iterable[Mapping[str, Any]],
                        adapter: RawRecordAdapter, *,
                        pair_cap: int = PAIR_CAP) -> OracleOutcome:
    """Raw-record entry point reserved for independently extracted corpus rows."""
    rows_a = adapt_raw_records(raw_a, adapter, side="a", schema=schema)
    rows_b = adapt_raw_records(raw_b, adapter, side="b", schema=schema)
    return compare_rows(schema, rows_a, rows_b, pair_cap=pair_cap)


def _ascii_space_normalize(text: str) -> str:
    return _ASCII_SPACE_RUN.sub(" ", text.strip(" "))


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite numerics are not comparable source values")
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if rendered in ("-0", "+0", ""):
        return "0"
    return rendered


def _number_text(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numerics are not comparable source values")
        return _decimal_text(Decimal(repr(value)))
    raise TypeError("not a supported numeric value")


def normalize_value(value: Any, kind: str = ORDINARY) -> NormalizedValue:
    """Apply the approved typed D2 scalar policy without application helpers."""
    if kind not in _KINDS:
        raise ValueError(f"unsupported equality kind: {kind!r}")
    if value is None:
        return NormalizedValue("blank")
    if type(value) is bool:
        normalized = NormalizedValue("text", "TRUE" if value else "FALSE")
    elif isinstance(value, (int, float, Decimal)):
        normalized = NormalizedValue("text", _number_text(value))
    elif isinstance(value, datetime):
        normalized = NormalizedValue("text", value.isoformat(sep=" "))
    elif isinstance(value, (date, time)):
        normalized = NormalizedValue("text", value.isoformat())
    elif isinstance(value, str):
        text = _ascii_space_normalize(value)
        normalized = (NormalizedValue("blank") if text == ""
                      else NormalizedValue("text", text))
    else:
        raise TypeError(f"unsupported raw value type: {type(value).__name__}")

    if kind != MED_WID or normalized.kind == "blank":
        return normalized
    match = _MED_WID_TOKEN.fullmatch(normalized.text)
    if match is None:
        return normalized
    suffix = match.group("suffix")
    if suffix and not ("!" <= suffix <= "~"
                       and suffix not in "0123456789."):
        return normalized
    try:
        number = _decimal_text(Decimal(match.group("number")))
    except (InvalidOperation, ValueError):
        return normalized
    return NormalizedValue("text", number + suffix)


def _render(value: NormalizedValue) -> str:
    return "(blank)" if value.kind == "blank" else value.text


def compare_cell(raw_a: Any, raw_b: Any, rule: FieldRule) -> CellResult:
    left = normalize_value(raw_a, rule.kind)
    right = normalize_value(raw_b, rule.kind)
    equal = left == right
    if equal:
        display = _render(left)
    elif rule.asserting:
        display = f"{_render(left)} ≠ {_render(right)}"
    else:
        display = _render(left if left.kind != "blank" else right)
    return CellResult(
        raw_a=raw_a, raw_b=raw_b,
        normalized_a=left, normalized_b=right,
        asserting=rule.asserting, equal=equal, display=display)


def canonical_key(row: OracleRow,
                  schema: OracleSchema) -> Tuple[NormalizedValue, ...]:
    _validate_row(row, schema)
    return tuple(normalize_value(value, rule.kind)
                 for value, rule in zip(row.key, schema.key_rules))


def _validate_row(row: OracleRow, schema: OracleSchema) -> None:
    if len(row.key) != len(schema.key_rules):
        raise ValueError("row key width does not match the oracle schema")
    if len(row.values) != len(schema.field_rules):
        raise ValueError("row value width does not match the oracle schema")


def compare_row(row_a: OracleRow, row_b: OracleRow,
                schema: OracleSchema,
                key: Optional[Tuple[NormalizedValue, ...]] = None) -> RowResult:
    _validate_row(row_a, schema)
    _validate_row(row_b, schema)
    key_a = canonical_key(row_a, schema)
    key_b = canonical_key(row_b, schema)
    if key_a != key_b:
        raise ValueError("cannot compare rows with different canonical keys")
    if key is not None and key != key_a:
        raise ValueError("provided canonical key disagrees with the rows")
    cells = tuple(compare_cell(a, b, rule) for a, b, rule in
                  zip(row_a.values, row_b.values, schema.field_rules))
    differing = tuple(rule.name for rule, cell in zip(schema.field_rules, cells)
                      if cell.counts_as_difference)
    return RowResult(
        source_index_a=row_a.source_index,
        source_index_b=row_b.source_index,
        key=key_a, cells=cells, differing_fields=differing)


def row_cost(row_a: OracleRow, row_b: OracleRow,
             schema: OracleSchema) -> int:
    """Duplicate-pair cost: asserting unequal cells only."""
    _validate_row(row_a, schema)
    _validate_row(row_b, schema)
    return sum(compare_cell(a, b, rule).counts_as_difference
               for a, b, rule in
               zip(row_a.values, row_b.values, schema.field_rules))


def exact_lexicographic_assignment(
        cost_matrix: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    """Exact rectangular assignment with a mathematical lexicographic tie rule.

    Rows are the smaller side and columns the larger side.  The encoded integer
    objective is ``total_cost`` followed by the base-(m+1) assignment vector.
    A rectangular Hungarian solver minimizes that objective in O(n²m) time and
    O(nm) input plus O(m) workspace; it never pads to a square matrix.
    """
    n = len(cost_matrix)
    if n == 0:
        return ()
    m = len(cost_matrix[0])
    if m == 0 or n > m:
        raise ValueError("assignment matrix must have 0 < rows <= columns")
    for row in cost_matrix:
        if len(row) != m:
            raise ValueError("assignment matrix is ragged")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in row):
            raise ValueError("assignment costs must be non-negative integers")

    base = m + 1
    primary = base ** n
    lex_weights = tuple(base ** (n - 1 - i) for i in range(n))

    def encoded(i: int, j: int) -> int:
        return cost_matrix[i][j] * primary + j * lex_weights[i]

    # Hungarian potentials for a rectangular n-by-m matrix (n <= m).
    u = [0] * (n + 1)
    v = [0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv: list[Optional[int]] = [None] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta: Optional[int] = None
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = encoded(i0 - 1, j - 1) - u[i0] - v[j]
                if minv[j] is None or cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if (delta is None or minv[j] < delta
                        or (minv[j] == delta and j < j1)):
                    delta = minv[j]
                    j1 = j
            if delta is None:
                raise RuntimeError("rectangular assignment has no augmenting column")
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                elif minv[j] is not None:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    assignment = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            assignment[p[j] - 1] = j - 1
    if any(value < 0 for value in assignment):
        raise RuntimeError("rectangular assignment is incomplete")
    return tuple(assignment)


def pair_group(rows_a: Sequence[OracleRow], rows_b: Sequence[OracleRow],
               schema: OracleSchema, key: Tuple[NormalizedValue, ...], *,
               pair_cap: int = PAIR_CAP) -> GroupPairing:
    """Pair one same-key group exactly, or fail closed above the product cap."""
    if not rows_a or not rows_b:
        raise ValueError("pair_group requires at least one row on each side")
    if isinstance(pair_cap, bool) or not isinstance(pair_cap, int) or pair_cap < 1:
        raise ValueError("pair_cap must be a positive integer")
    for row in tuple(rows_a) + tuple(rows_b):
        _validate_row(row, schema)
        if canonical_key(row, schema) != key:
            raise ValueError("pair group contains a foreign key")

    na, nb = len(rows_a), len(rows_b)
    small_is_a = na <= nb
    small = rows_a if small_is_a else rows_b
    large = rows_b if small_is_a else rows_a
    smaller_side = "a" if small_is_a else "b"
    matrix_cells = na * nb

    if matrix_cells > pair_cap:
        assignment = tuple(range(len(small)))
        pairs = (tuple((i, j) for i, j in enumerate(assignment)) if small_is_a
                 else tuple((j, i) for i, j in enumerate(assignment)))
        total = sum(row_cost(rows_a[a], rows_b[b], schema) for a, b in pairs)
        unmatched_a = tuple(i for i in range(na)
                            if i not in {a for a, _ in pairs})
        unmatched_b = tuple(i for i in range(nb)
                            if i not in {b for _, b in pairs})
        source_pairs = tuple((rows_a[a].source_index, rows_b[b].source_index)
                             for a, b in sorted(pairs))
        trace = PairingTrace(
            key=key, side_a_size=na, side_b_size=nb,
            smaller_side=smaller_side, assignment_vector=assignment,
            source_pairs=source_pairs, total_cost=total,
            algorithm="positional-above-cap", quality="capped", exact=False,
            matrix_cells=matrix_cells)
        diagnostic = CappedDiagnostic(
            key=key, side_a_size=na, side_b_size=nb, cap=pair_cap,
            fallback="positional", fallback_cost=total)
        return GroupPairing(tuple(sorted(pairs)), unmatched_a, unmatched_b,
                            trace, diagnostic)

    costs = [
        [row_cost(a, b, schema) if small_is_a else row_cost(b, a, schema)
         for b in large]
        for a in small
    ]
    assignment = exact_lexicographic_assignment(costs)
    pairs = (tuple((i, j) for i, j in enumerate(assignment)) if small_is_a
             else tuple((j, i) for i, j in enumerate(assignment)))
    pairs = tuple(sorted(pairs))
    total = sum(row_cost(rows_a[a], rows_b[b], schema) for a, b in pairs)
    unmatched_a = tuple(i for i in range(na) if i not in {a for a, _ in pairs})
    unmatched_b = tuple(i for i in range(nb) if i not in {b for _, b in pairs})
    positional = sum(row_cost(rows_a[i], rows_b[i], schema)
                     for i in range(min(na, nb)))
    if total > positional:
        raise AssertionError("exact assignment is worse than positional pairing")
    source_pairs = tuple((rows_a[a].source_index, rows_b[b].source_index)
                         for a, b in pairs)
    trace = PairingTrace(
        key=key, side_a_size=na, side_b_size=nb,
        smaller_side=smaller_side, assignment_vector=assignment,
        source_pairs=source_pairs, total_cost=total,
        algorithm="rectangular-hungarian-lex-v1", quality="exact", exact=True,
        matrix_cells=matrix_cells)
    return GroupPairing(pairs, unmatched_a, unmatched_b, trace)


def compare_rows(schema: OracleSchema, rows_a: Sequence[OracleRow],
                 rows_b: Sequence[OracleRow], *,
                 pair_cap: int = PAIR_CAP) -> OracleOutcome:
    """Compute typed counts and pairing evidence from independently extracted rows."""
    groups_a: dict[Tuple[NormalizedValue, ...], list[OracleRow]] = {}
    groups_b: dict[Tuple[NormalizedValue, ...], list[OracleRow]] = {}
    order: list[Tuple[NormalizedValue, ...]] = []
    # CMP-AUD-187: `order` keeps deterministic ENCOUNTER order; `seen` answers
    # first-seen membership in O(1). The old test was
    # `key not in groups_a and key not in groups_b and key not in order`, whose
    # three parts are equivalent: a key enters `order` only in the iteration that
    # also files it into one of the group dicts, so at the top of every iteration
    # set(order) == set(groups_a) | set(groups_b) == seen. Scanning the list made
    # a 60,083-key Highway Detail leg quadratic (746s in comparison alone).
    seen: set[Tuple[NormalizedValue, ...]] = set()
    for row, groups in tuple((row, groups_a) for row in rows_a) + tuple(
            (row, groups_b) for row in rows_b):
        _validate_row(row, schema)
        key = canonical_key(row, schema)
        if key not in seen:
            seen.add(key)
            order.append(key)
        groups.setdefault(key, []).append(row)

    paired_rows = side_a_only = side_b_only = 0
    differing_rows = differing_cells = 0
    asserted_cells = context_cells = 0
    per_field = {rule.name: 0 for rule in schema.field_rules if rule.asserting}
    row_results = []
    side_a_indices = []
    side_b_indices = []
    traces = []
    diagnostics = []

    for key in order:
        ga = groups_a.get(key, [])
        gb = groups_b.get(key, [])
        if not ga:
            side_b_only += len(gb)
            side_b_indices.extend(row.source_index for row in gb)
            continue
        if not gb:
            side_a_only += len(ga)
            side_a_indices.extend(row.source_index for row in ga)
            continue
        paired = pair_group(ga, gb, schema, key, pair_cap=pair_cap)
        traces.append(paired.trace)
        if paired.capped_diagnostic is not None:
            diagnostics.append(paired.capped_diagnostic)
        for a_pos, b_pos in paired.pairs:
            result = compare_row(ga[a_pos], gb[b_pos], schema, key)
            row_results.append(result)
            paired_rows += 1
            asserted_cells += sum(rule.asserting for rule in schema.field_rules)
            context_cells += sum(not rule.asserting for rule in schema.field_rules)
            if result.differing_fields:
                differing_rows += 1
            for field_name in result.differing_fields:
                per_field[field_name] += 1
                differing_cells += 1
        side_a_only += len(paired.unmatched_a)
        side_b_only += len(paired.unmatched_b)
        side_a_indices.extend(ga[i].source_index for i in paired.unmatched_a)
        side_b_indices.extend(gb[i].source_index for i in paired.unmatched_b)

    no_data = not rows_a and not rows_b
    completion = "no_data" if no_data else "partial" if diagnostics else "complete"
    verdict = ("unknown" if no_data else
               "match" if completion == "complete" and differing_cells == 0
               and side_a_only == 0 and side_b_only == 0 else "diff")
    counts = OracleCounts(
        known=True, paired_rows=paired_rows,
        side_a_only_rows=side_a_only, side_b_only_rows=side_b_only,
        differing_rows=differing_rows, differing_cells=differing_cells,
        per_field_counts={name: count for name, count in per_field.items() if count},
        asserted_cells=asserted_cells, context_cells=context_cells)
    return OracleOutcome(
        completion=completion, verdict=verdict, counts=counts,
        row_results=tuple(row_results),
        side_a_only_indices=tuple(side_a_indices),
        side_b_only_indices=tuple(side_b_indices),
        pairing_trace=tuple(traces),
        pairing_quality="capped" if diagnostics else "exact",
        capped_diagnostics=tuple(diagnostics))

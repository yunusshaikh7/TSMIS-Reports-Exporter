"""Typed, dependency-light contracts for comparison truth and artifact state.

The application historically returned comparison truth through a mixture of
``ConsolidateResult`` fields and human-readable summary text.  These dataclasses are
the additive migration boundary: producers can publish structured state while legacy
callers continue to receive the original result object.

``unknown`` is deliberately fail-closed.  It exists only while legacy producers are
being migrated and is never considered complete or comparable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from functools import wraps
import json
import math
import re
from typing import Any, Dict, Mapping, Optional, Tuple, Type, TypeVar, Union


UNKNOWN = "unknown"
CONTRACT_SCHEMA_VERSION = 2
COMPLETIONS = frozenset({
    "complete", "partial", "no_data", "cancelled", "failed", UNKNOWN,
})
STATUSES = frozenset({"ok", "cancelled", "error", UNKNOWN})
VERDICTS = frozenset({"match", "diff", UNKNOWN})
PUBLICATION_STATES = frozenset({
    "committed", "partial", "failed", "cancelled", UNKNOWN,
})
ATTEMPT_STATES = frozenset({
    "attempted", "succeeded", "partial", "failed", "cancelled",
})
PAIRING_QUALITIES = frozenset({
    UNKNOWN, "exact", "heuristic", "ambiguous", "capped",
})
PAIRING_TRACE_QUALITIES = frozenset({"exact", "capped"})
EXACT_PAIRING_ALGORITHM = "rectangular-hungarian-lex-v1"
CAPPED_PAIRING_ALGORITHM = "positional-above-cap"
CAPPED_FALLBACK_POLICY = "positional"


def _require_choice(name: str, value: str, choices) -> None:
    if value not in choices:
        raise ValueError(f"{name} must be one of {sorted(choices)!r}, got {value!r}")


def _require_count(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_exact_count(name: str, value: int, *, positive: bool = False) -> None:
    """Validate an engine-owned index/count without accepting int subclasses."""
    if type(value) is not int or value < (1 if positive else 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be a {qualifier} integer")


def _require_exact_fields(value: Mapping[str, Any], names, label: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    expected = frozenset(names)
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{label} has a non-canonical shape; missing={missing!r}, "
            f"extra={extra!r}")


def _canonical_key_components(value) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("key_components must be an array")
    items = tuple(value)
    if not items:
        raise ValueError("key_components must not be empty")
    if any(type(item) is not str for item in items):
        raise ValueError("key_components must contain only strings")
    return items


def _canonical_indices(name: str, value) -> Tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an array")
    items = tuple(value)
    for index, item in enumerate(items):
        _require_exact_count(f"{name}[{index}]", item)
    if len(set(items)) != len(items):
        raise ValueError(f"{name} must not contain duplicate source indices")
    return items


def _strings(value) -> Tuple[str, ...]:
    return tuple(str(item) for item in (value or ()))


def _mapping(value) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("expected an object")
    return dict(value)


def _rows(value) -> Tuple[Any, ...]:
    return tuple(
        tuple(_restore_row_value(item) for item in row)
        if isinstance(row, (list, tuple)) else row
        for row in (value or ()))


_PHYSICAL_COMPONENT_NAMES = ("route", "county", "postmile")
_PHYSICAL_KEY_TAG = "comparison-contract/physical-key/v1"


def _nonblank_string(name: str, value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_json_scalar(name: str, value: Any) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float and math.isfinite(value):
        return
    raise ValueError(
        f"{name} must be None, bool, int, finite float, or string")


def _json_scalar_token(value: Any) -> Tuple[type, Any]:
    """Type- and sign-exact equality token for the accepted scalar domain."""
    if type(value) is float:
        return (float, value.hex())
    return (type(value), value)


@dataclass(frozen=True, eq=False)
class RawIdentityClaim:
    """One lossless source claim used to derive a physical identity."""

    name: str
    value: Any

    def __post_init__(self) -> None:
        _nonblank_string("raw identity claim name", self.name)
        _require_json_scalar("raw identity claim value", self.value)

    def __eq__(self, other) -> bool:
        return (type(other) is RawIdentityClaim
                and self.name == other.name
                and _json_scalar_token(self.value)
                == _json_scalar_token(other.value))

    def __hash__(self) -> int:
        return hash((self.name, _json_scalar_token(self.value)))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RawIdentityClaim":
        names = ("name", "value")
        _require_exact_fields(value, names, "raw identity claim")
        return cls(name=value["name"], value=value["value"])


@dataclass(frozen=True)
class PhysicalIdentity:
    """Canonical physical geometry plus lossless, non-identifying evidence.

    Equality and hashing intentionally use only the ordered canonical
    route/county/postmile components. Raw claims can differ between sources
    without turning the same physical location into two keys. ``display`` is
    deterministically rebuilt from those components; the separate PhysicalKey
    string retains source-cell presentation.
    """

    canonical_components: Tuple[Tuple[str, str], ...]
    raw_claims: Tuple[RawIdentityClaim, ...] = field(
        compare=False, hash=False)
    display: str = field(compare=False, hash=False)

    def __post_init__(self) -> None:
        components = self.canonical_components
        if type(components) is not tuple or len(components) != 3:
            raise ValueError(
                "canonical_components must be the ordered route/county/postmile tuple")
        normalized = []
        for index, component in enumerate(components):
            if type(component) is not tuple or len(component) != 2:
                raise ValueError(
                    "each canonical component must be a (name, value) tuple")
            component_name, component_value = component
            expected_name = _PHYSICAL_COMPONENT_NAMES[index]
            if (type(component_name) is not str
                    or component_name != expected_name):
                raise ValueError(
                    "canonical_components must be ordered exactly as "
                    "route/county/postmile")
            normalized.append((
                component_name,
                _nonblank_string(
                    f"canonical {component_name} value", component_value),
            ))
        claims = self.raw_claims
        if type(claims) is not tuple or not claims:
            raise ValueError(
                "raw_claims must be a non-empty tuple of RawIdentityClaim records")
        if any(type(claim) is not RawIdentityClaim for claim in claims):
            raise ValueError(
                "raw_claims must contain only RawIdentityClaim records")
        _nonblank_string("display", self.display)
        object.__setattr__(self, "canonical_components", tuple(normalized))
        object.__setattr__(
            self, "display", " / ".join(value for _name, value in normalized))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PhysicalIdentity":
        names = ("canonical_components", "raw_claims", "display")
        _require_exact_fields(value, names, "physical identity")
        raw_components = value["canonical_components"]
        raw_claims = value["raw_claims"]
        if not isinstance(raw_components, (list, tuple)):
            raise ValueError("canonical_components must be an array")
        if not isinstance(raw_claims, (list, tuple)):
            raise ValueError("raw_claims must be an array")
        if any(not isinstance(claim, Mapping) for claim in raw_claims):
            raise ValueError("every serialized raw identity claim must be an object")
        return cls(
            canonical_components=tuple(
                tuple(component) if isinstance(component, (list, tuple))
                else component
                for component in raw_components),
            raw_claims=tuple(
                RawIdentityClaim.from_dict(claim) for claim in raw_claims),
            display=value["display"],
        )


class PhysicalKey(str):
    """A source-cell string whose key semantics are a PhysicalIdentity."""

    def __new__(cls, display: str, physical_identity: PhysicalIdentity):
        _nonblank_string("physical key display", display)
        if type(physical_identity) is not PhysicalIdentity:
            raise ValueError("physical_identity must be a PhysicalIdentity")
        value = super().__new__(cls, display)
        object.__setattr__(value, "_physical_identity", physical_identity)
        return value

    @property
    def physical_identity(self) -> PhysicalIdentity:
        return self._physical_identity

    def __setattr__(self, name, value) -> None:
        raise AttributeError("PhysicalKey is immutable")

    def __eq__(self, other) -> bool:
        if not isinstance(other, PhysicalKey):
            return False
        return self.physical_identity == other.physical_identity

    def __ne__(self, other) -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash(self.physical_identity)

    @staticmethod
    def _ordered_identity(other):
        if not isinstance(other, PhysicalKey):
            raise TypeError(
                "PhysicalKey ordering requires another PhysicalKey")
        return other.physical_identity.canonical_components

    def __lt__(self, other) -> bool:
        return (self.physical_identity.canonical_components
                < self._ordered_identity(other))

    def __le__(self, other) -> bool:
        return (self.physical_identity.canonical_components
                <= self._ordered_identity(other))

    def __gt__(self, other) -> bool:
        return (self.physical_identity.canonical_components
                > self._ordered_identity(other))

    def __ge__(self, other) -> bool:
        return (self.physical_identity.canonical_components
                >= self._ordered_identity(other))

    def __reduce_ex__(self, protocol):
        # dataclasses.asdict deep-copies row values. Keep the attachment when a
        # LoadedSide carrying PhysicalKey cells crosses that serialization seam.
        return (type(self), (str(self), self.physical_identity))


def make_physical_identity(route: str, county: str, postmile: str,
                           raw_claims: Tuple[RawIdentityClaim, ...],
                           display: str) -> PhysicalIdentity:
    """Build the one canonical route/county/postmile identity shape."""
    return PhysicalIdentity(
        canonical_components=(
            ("route", route),
            ("county", county),
            ("postmile", postmile),
        ),
        raw_claims=raw_claims,
        display=display,
    )


def physical_key(display: str,
                 physical_identity: PhysicalIdentity) -> PhysicalKey:
    """Attach typed physical identity to a source-visible string cell."""
    return PhysicalKey(display, physical_identity)


def physical_identity_from_key(row, off: int,
                               key_field: int) -> Optional[PhysicalIdentity]:
    """Return a row key's attached identity, or None for a legacy scalar key."""
    value = row[off + key_field]
    if isinstance(value, PhysicalKey):
        return value.physical_identity
    return None


def _restore_row_value(value: Any) -> Any:
    """Restore tagged PhysicalKey cells nested in LoadedSide rows."""
    if isinstance(value, Mapping) and value.get("type") == _PHYSICAL_KEY_TAG:
        names = ("type", "display", "physical_identity")
        _require_exact_fields(value, names, "physical key cell")
        identity = value["physical_identity"]
        if not isinstance(identity, Mapping):
            raise ValueError("physical key identity must be an object")
        return physical_key(
            value["display"], PhysicalIdentity.from_dict(identity))
    if isinstance(value, list):
        return [_restore_row_value(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _restore_row_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class SourceIdentity:
    """Stable identity claims for one effective comparison source."""

    recipe_key: str = ""
    report_key: str = ""
    role: str = ""
    format: str = ""
    canonical_path: str = ""
    content_digest: str = ""
    producer_version: str = ""
    parser_version: str = ""
    normalizer_version: str = ""
    selection_kind: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceIdentity":
        return cls(**{name: str(value.get(name, "") or "")
                      for name in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LoadedSide:
    """Rows plus the coverage and provenance claims made by one loader."""

    rows: Tuple[Any, ...] = ()
    declared_schema: Tuple[str, ...] = ()
    route_universe: Tuple[str, ...] = ()
    record_universe: Tuple[str, ...] = ()
    completion: str = UNKNOWN
    warnings: Tuple[str, ...] = ()
    failures: Tuple[str, ...] = ()
    skipped_inputs: int = 0
    failed_inputs: int = 0
    source_identity: Optional[SourceIdentity] = None
    raw_identity_claims: Mapping[str, Any] = field(default_factory=dict)
    display_metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_choice("completion", self.completion, COMPLETIONS)
        _require_count("skipped_inputs", self.skipped_inputs)
        _require_count("failed_inputs", self.failed_inputs)
        if (self.completion == "complete"
                and (self.warnings or self.failures
                     or self.skipped_inputs or self.failed_inputs)):
            raise ValueError(
                "a complete loaded side cannot report skipped/failed input issues")

    @property
    def is_comparable(self) -> bool:
        return self.completion in ("complete", "partial")

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LoadedSide":
        identity = value.get("source_identity")
        return cls(
            rows=_rows(value.get("rows")),
            declared_schema=_strings(value.get("declared_schema")),
            route_universe=_strings(value.get("route_universe")),
            record_universe=_strings(value.get("record_universe")),
            completion=str(value.get("completion", UNKNOWN) or UNKNOWN),
            warnings=_strings(value.get("warnings")),
            failures=_strings(value.get("failures")),
            skipped_inputs=value.get("skipped_inputs", 0),
            failed_inputs=value.get("failed_inputs", 0),
            source_identity=(SourceIdentity.from_dict(identity)
                             if isinstance(identity, Mapping) else None),
            raw_identity_claims=_mapping(value.get("raw_identity_claims")),
            display_metrics=_mapping(value.get("display_metrics")),
        )


@dataclass(frozen=True)
class ComparisonCounts:
    """Machine-readable discrepancy counts produced by the comparison engine."""

    known: bool = False
    paired_rows: int = 0
    side_a_only_rows: int = 0
    side_b_only_rows: int = 0
    differing_rows: int = 0
    differing_cells: int = 0
    per_field_counts: Mapping[str, int] = field(default_factory=dict)
    asserted_cells: int = 0
    context_cells: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.known, bool):
            raise ValueError("known must be a boolean")
        for name in ("paired_rows", "side_a_only_rows", "side_b_only_rows",
                     "differing_rows", "differing_cells", "asserted_cells",
                     "context_cells"):
            _require_count(name, getattr(self, name))
        for name, count in self.per_field_counts.items():
            if not isinstance(name, str):
                raise ValueError("per_field_counts keys must be strings")
            _require_count(f"per_field_counts[{name!r}]", count)
        if not self.known:
            if (self.paired_rows or self.side_a_only_rows
                    or self.side_b_only_rows or self.differing_rows
                    or self.differing_cells or self.per_field_counts
                    or self.asserted_cells or self.context_cells):
                raise ValueError("unknown counts cannot carry numeric claims")
        else:
            if self.differing_rows > self.paired_rows:
                raise ValueError("differing_rows cannot exceed paired_rows")
            if sum(self.per_field_counts.values()) != self.differing_cells:
                raise ValueError(
                    "known per_field_counts must sum to differing_cells")

    @property
    def identical_rows(self) -> int:
        return self.paired_rows - self.differing_rows if self.known else 0

    @property
    def side_a_rows(self) -> int:
        return self.paired_rows + self.side_a_only_rows

    @property
    def side_b_rows(self) -> int:
        return self.paired_rows + self.side_b_only_rows

    @property
    def union_rows(self) -> int:
        return self.paired_rows + self.side_a_only_rows + self.side_b_only_rows

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["per_field_counts"] = dict(self.per_field_counts)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ComparisonCounts":
        per_field = value.get("per_field_counts") or {}
        if not isinstance(per_field, Mapping):
            raise ValueError("per_field_counts must be an object")
        return cls(
            known=value.get("known", False),
            paired_rows=value.get("paired_rows", 0),
            side_a_only_rows=value.get("side_a_only_rows", 0),
            side_b_only_rows=value.get("side_b_only_rows", 0),
            differing_rows=value.get("differing_rows", 0),
            differing_cells=value.get("differing_cells", 0),
            per_field_counts={str(k): v for k, v in per_field.items()},
            asserted_cells=value.get("asserted_cells", 0),
            context_cells=value.get("context_cells", 0),
        )


@dataclass(frozen=True)
class PairingPair:
    """One selected pair of original/source rows and its asserting-cell cost."""

    side_a_index: int
    side_b_index: int
    cost: int

    def __post_init__(self) -> None:
        _require_exact_count("side_a_index", self.side_a_index)
        _require_exact_count("side_b_index", self.side_b_index)
        _require_exact_count("cost", self.cost)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PairingPair":
        names = ("side_a_index", "side_b_index", "cost")
        _require_exact_fields(value, names, "pairing pair")
        return cls(**{name: value[name] for name in names})


@dataclass(frozen=True)
class PairingTrace:
    """Canonical evidence for one same-key rectangular assignment.

    ``side_*_indices`` retain each group's original/source row indices in file
    order.  ``assignment_vector`` is deliberately local: element ``i`` is the
    larger-side group position paired to smaller-side group position ``i``.
    ``pairs`` is the exact global reconstruction of that vector, in the same
    smaller-side order.  Carrying both forms makes transpose, ordering, and
    local/global-index mistakes independently rejectable at the contract edge.
    """

    key_components: Tuple[str, ...]
    side_a_size: int
    side_b_size: int
    matrix_cells: int
    side_a_indices: Tuple[int, ...]
    side_b_indices: Tuple[int, ...]
    smaller_side: str
    assignment_vector: Tuple[int, ...]
    pairs: Tuple[PairingPair, ...]
    total_cost: int
    positional_cost: int
    algorithm: str
    exact: bool
    quality: str

    def __post_init__(self) -> None:
        key = _canonical_key_components(self.key_components)
        side_a_indices = _canonical_indices(
            "side_a_indices", self.side_a_indices)
        side_b_indices = _canonical_indices(
            "side_b_indices", self.side_b_indices)
        vector = _canonical_indices("assignment_vector", self.assignment_vector)
        if not isinstance(self.pairs, (list, tuple)):
            raise ValueError("pairs must be an array")
        pairs = tuple(self.pairs)
        if any(type(pair) is not PairingPair for pair in pairs):
            raise ValueError("pairs must contain only PairingPair records")

        object.__setattr__(self, "key_components", key)
        object.__setattr__(self, "side_a_indices", side_a_indices)
        object.__setattr__(self, "side_b_indices", side_b_indices)
        object.__setattr__(self, "assignment_vector", vector)
        object.__setattr__(self, "pairs", pairs)

        _require_exact_count("side_a_size", self.side_a_size, positive=True)
        _require_exact_count("side_b_size", self.side_b_size, positive=True)
        _require_exact_count("matrix_cells", self.matrix_cells, positive=True)
        _require_exact_count("total_cost", self.total_cost)
        _require_exact_count("positional_cost", self.positional_cost)
        if type(self.exact) is not bool:
            raise ValueError("exact must be a boolean")
        _require_choice("quality", self.quality, PAIRING_TRACE_QUALITIES)
        if type(self.algorithm) is not str or not self.algorithm:
            raise ValueError("algorithm must be a non-empty string")

        if self.side_a_size != len(side_a_indices):
            raise ValueError("side_a_size must equal len(side_a_indices)")
        if self.side_b_size != len(side_b_indices):
            raise ValueError("side_b_size must equal len(side_b_indices)")
        if self.matrix_cells != self.side_a_size * self.side_b_size:
            raise ValueError("matrix_cells must equal side_a_size * side_b_size")

        expected_smaller = (
            "a" if self.side_a_size <= self.side_b_size else "b")
        if self.smaller_side != expected_smaller:
            raise ValueError(
                "smaller_side must be 'a' when side A is no larger, else 'b'")
        smaller_size = min(self.side_a_size, self.side_b_size)
        larger_size = max(self.side_a_size, self.side_b_size)
        if len(vector) != smaller_size:
            raise ValueError(
                "assignment_vector must contain one entry per smaller-side row")
        if any(index >= larger_size for index in vector):
            raise ValueError(
                "assignment_vector contains an out-of-range larger-side index")
        if len(pairs) != smaller_size:
            raise ValueError("pairs must contain one pair per smaller-side row")

        reconstructed = []
        for smaller_index, larger_index in enumerate(vector):
            if self.smaller_side == "a":
                a_index = side_a_indices[smaller_index]
                b_index = side_b_indices[larger_index]
            else:
                a_index = side_a_indices[larger_index]
                b_index = side_b_indices[smaller_index]
            reconstructed.append((a_index, b_index))
        actual_pairs = tuple(
            (pair.side_a_index, pair.side_b_index) for pair in pairs)
        if actual_pairs != tuple(reconstructed):
            raise ValueError(
                "pairs must exactly reconstruct assignment_vector in "
                "smaller-side order")
        if len(set(actual_pairs)) != len(actual_pairs):
            raise ValueError("pairs must not contain duplicate original pairs")
        if self.total_cost != sum(pair.cost for pair in pairs):
            raise ValueError("total_cost must equal the sum of selected pair costs")

        if self.exact:
            if self.quality != "exact":
                raise ValueError("an exact trace must have quality='exact'")
            if self.algorithm != EXACT_PAIRING_ALGORITHM:
                raise ValueError(
                    f"an exact trace must use {EXACT_PAIRING_ALGORITHM!r}")
            if self.total_cost > self.positional_cost:
                raise ValueError(
                    "exact pairing cannot cost more than positional pairing")
        else:
            if self.quality != "capped":
                raise ValueError("a non-exact D3 trace must have quality='capped'")
            if self.algorithm != CAPPED_PAIRING_ALGORITHM:
                raise ValueError(
                    f"a capped trace must use {CAPPED_PAIRING_ALGORITHM!r}")
            if vector != tuple(range(smaller_size)):
                raise ValueError(
                    "a capped trace must use deterministic positional fallback")
            if self.total_cost != self.positional_cost:
                raise ValueError(
                    "a capped positional trace must report its positional cost")

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PairingTrace":
        names = (
            "key_components", "side_a_size", "side_b_size", "matrix_cells",
            "side_a_indices", "side_b_indices", "smaller_side",
            "assignment_vector", "pairs", "total_cost", "positional_cost",
            "algorithm", "exact", "quality",
        )
        _require_exact_fields(value, names, "pairing trace")
        raw_pairs = value["pairs"]
        if not isinstance(raw_pairs, (list, tuple)):
            raise ValueError("pairs must be an array")
        if any(not isinstance(pair, Mapping) for pair in raw_pairs):
            raise ValueError("every serialized pairing pair must be an object")
        return cls(
            key_components=value["key_components"],
            side_a_size=value["side_a_size"],
            side_b_size=value["side_b_size"],
            matrix_cells=value["matrix_cells"],
            side_a_indices=value["side_a_indices"],
            side_b_indices=value["side_b_indices"],
            smaller_side=value["smaller_side"],
            assignment_vector=value["assignment_vector"],
            pairs=tuple(PairingPair.from_dict(pair) for pair in raw_pairs),
            total_cost=value["total_cost"],
            positional_cost=value["positional_cost"],
            algorithm=value["algorithm"],
            exact=value["exact"],
            quality=value["quality"],
        )


@dataclass(frozen=True)
class CappedGroupDiagnostic:
    """Fail-closed evidence for one group above the exact-assignment cap."""

    key_components: Tuple[str, ...]
    side_a_size: int
    side_b_size: int
    matrix_cells: int
    cap: int
    fallback_policy: str
    fallback_cost: int

    def __post_init__(self) -> None:
        key = _canonical_key_components(self.key_components)
        object.__setattr__(self, "key_components", key)
        _require_exact_count("side_a_size", self.side_a_size, positive=True)
        _require_exact_count("side_b_size", self.side_b_size, positive=True)
        _require_exact_count("matrix_cells", self.matrix_cells, positive=True)
        _require_exact_count("cap", self.cap, positive=True)
        _require_exact_count("fallback_cost", self.fallback_cost)
        if self.matrix_cells != self.side_a_size * self.side_b_size:
            raise ValueError("matrix_cells must equal side_a_size * side_b_size")
        if self.matrix_cells <= self.cap:
            raise ValueError("a capped group must be strictly above the cap")
        if self.fallback_policy != CAPPED_FALLBACK_POLICY:
            raise ValueError(
                f"fallback_policy must be {CAPPED_FALLBACK_POLICY!r}")

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CappedGroupDiagnostic":
        names = (
            "key_components", "side_a_size", "side_b_size", "matrix_cells",
            "cap", "fallback_policy", "fallback_cost",
        )
        _require_exact_fields(value, names, "capped-group diagnostic")
        return cls(**{name: value[name] for name in names})


@dataclass(frozen=True)
class ComparisonOutcome:
    """The comparison's status, coverage, verdict, counts, and diagnostics."""

    status: str = "ok"
    completion: str = UNKNOWN
    verdict: str = UNKNOWN
    counts: ComparisonCounts = field(default_factory=ComparisonCounts)
    warnings: Tuple[str, ...] = ()
    failures: Tuple[str, ...] = ()
    source_identities: Tuple[SourceIdentity, ...] = ()
    pairing_trace: Tuple[PairingTrace, ...] = ()
    duplicate_group_count: int = 0
    pairing_quality: str = UNKNOWN
    capped_group_diagnostics: Tuple[CappedGroupDiagnostic, ...] = ()
    coverage_diagnostics: Tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.pairing_trace, (list, tuple)):
            raise ValueError("pairing_trace must be an array")
        traces = tuple(self.pairing_trace)
        if any(type(item) is not PairingTrace for item in traces):
            raise ValueError(
                "pairing_trace must contain only PairingTrace records")

        if not isinstance(self.capped_group_diagnostics, (list, tuple)):
            raise ValueError("capped_group_diagnostics must be an array")
        typed_diagnostics = []
        migrated_coverage = []
        for item in self.capped_group_diagnostics:
            if type(item) is CappedGroupDiagnostic:
                typed_diagnostics.append(item)
            elif (isinstance(item, Mapping)
                  and item.get("kind") == "loaded_side_coverage"):
                # Phase-2 producers temporarily published loaded-side coverage
                # through this field.  Preserve those current callers and old
                # sidecars, but canonicalize the object into the new semantic
                # field.  No other mapping shape is guessed or reclassified.
                migrated_coverage.append(dict(item))
            else:
                raise ValueError(
                    "capped_group_diagnostics must contain only "
                    "CappedGroupDiagnostic records")

        if not isinstance(self.coverage_diagnostics, (list, tuple)):
            raise ValueError("coverage_diagnostics must be an array")
        coverage = []
        for item in self.coverage_diagnostics:
            if not isinstance(item, Mapping):
                raise ValueError(
                    "coverage_diagnostics must contain only objects")
            coverage.append(dict(item))
        coverage.extend(migrated_coverage)

        diagnostics = tuple(typed_diagnostics)
        object.__setattr__(self, "pairing_trace", traces)
        object.__setattr__(self, "capped_group_diagnostics", diagnostics)
        object.__setattr__(self, "coverage_diagnostics", tuple(coverage))

        _require_choice("status", self.status, STATUSES)
        _require_choice("completion", self.completion, COMPLETIONS)
        _require_choice("verdict", self.verdict, VERDICTS)
        _require_choice("pairing_quality", self.pairing_quality,
                        PAIRING_QUALITIES)
        _require_exact_count("duplicate_group_count", self.duplicate_group_count)
        if self.duplicate_group_count != len(traces):
            raise ValueError(
                "duplicate_group_count must equal the persisted duplicate trace count")
        if self.status == "error" and self.completion not in ("failed", UNKNOWN):
            raise ValueError("an error outcome cannot claim successful completion")
        if self.status == "cancelled" and self.completion not in ("cancelled", UNKNOWN):
            raise ValueError("a cancelled outcome must have cancelled/unknown completion")
        if self.status == "ok" and self.completion in ("failed", "cancelled"):
            raise ValueError("an ok outcome cannot be failed or cancelled")
        if self.completion in ("complete", "partial"):
            if not self.counts.known or self.verdict not in ("match", "diff"):
                raise ValueError(
                    "complete/partial comparison outcomes require known counts and verdict")
            if self.pairing_quality not in ("exact", "capped"):
                raise ValueError(
                    "a comparable comparison requires exact or capped pairing quality")
        if self.completion == "complete" and self.pairing_quality != "exact":
            raise ValueError("a complete comparison requires exact pairing quality")
        if self.verdict == "match" and self.completion != "complete":
            raise ValueError("only a complete comparison may claim a match")
        if self.verdict == "match" and self.counts.known:
            if (self.counts.differing_cells or self.counts.side_a_only_rows
                    or self.counts.side_b_only_rows):
                raise ValueError("a match verdict contradicts the structured counts")
        if self.pairing_quality == "capped":
            if self.completion != "partial" or self.verdict != "diff":
                raise ValueError(
                    "capped pairing must be partial and conservatively non-match")
            if not traces:
                raise ValueError(
                    "capped pairing requires a populated typed pairing trace")

        trace_keys = [trace.key_components for trace in traces]
        if len(set(trace_keys)) != len(trace_keys):
            raise ValueError("pairing_trace must contain at most one trace per key")
        used_a = [index for trace in traces for index in trace.side_a_indices]
        used_b = [index for trace in traces for index in trace.side_b_indices]
        if len(set(used_a)) != len(used_a):
            raise ValueError(
                "side-A source indices must not appear in multiple pairing traces")
        if len(set(used_b)) != len(used_b):
            raise ValueError(
                "side-B source indices must not appear in multiple pairing traces")

        if traces:
            if (not self.counts.known
                    or self.completion not in ("complete", "partial")
                    or self.verdict not in ("match", "diff")):
                raise ValueError(
                    "a populated pairing trace requires a comparable typed outcome")
            derived_quality = (
                "capped" if any(trace.quality == "capped" for trace in traces)
                else "exact")
            if self.pairing_quality != derived_quality:
                raise ValueError(
                    "pairing_quality must agree with the populated pairing trace")
            if self.counts.known:
                traced_pairs = sum(len(trace.pairs) for trace in traces)
                traced_cost = sum(trace.total_cost for trace in traces)
                traced_diff_rows = sum(
                    pair.cost > 0 for trace in traces for pair in trace.pairs)
                # E2 persists assignment evidence for duplicate groups only;
                # ordinary 1x1 keys need no assignment decision and would make
                # statewide sidecars needlessly enormous. The trace must remain
                # a truthful subset of the global counts, never exceed them.
                if traced_pairs > self.counts.paired_rows:
                    raise ValueError(
                        "pairing trace pair total exceeds structured paired_rows")
                if traced_cost > self.counts.differing_cells:
                    raise ValueError(
                        "pairing trace cost exceeds structured differing_cells")
                if traced_diff_rows > self.counts.differing_rows:
                    raise ValueError(
                        "nonzero-cost trace pairs exceed structured differing_rows")
                traced_a_only = sum(
                    trace.side_a_size - len(trace.pairs) for trace in traces)
                traced_b_only = sum(
                    trace.side_b_size - len(trace.pairs) for trace in traces)
                if traced_a_only > self.counts.side_a_only_rows:
                    raise ValueError(
                        "trace-implied side-A leftovers exceed structured counts")
                if traced_b_only > self.counts.side_b_only_rows:
                    raise ValueError(
                        "trace-implied side-B leftovers exceed structured counts")

        capped_traces = {
            trace.key_components: trace for trace in traces
            if trace.quality == "capped"
        }
        diagnostic_keys = [item.key_components for item in diagnostics]
        if len(set(diagnostic_keys)) != len(diagnostic_keys):
            raise ValueError(
                "capped_group_diagnostics must contain at most one item per key")
        if set(diagnostic_keys) != set(capped_traces):
            raise ValueError(
                "capped traces and capped-group diagnostics must correspond exactly")
        for item in diagnostics:
            trace = capped_traces[item.key_components]
            if ((item.side_a_size, item.side_b_size, item.matrix_cells,
                 item.fallback_cost)
                    != (trace.side_a_size, trace.side_b_size,
                        trace.matrix_cells, trace.total_cost)):
                raise ValueError(
                    "capped-group diagnostic dimensions/cost contradict its trace")

    @property
    def is_complete(self) -> bool:
        return (self.status == "ok" and self.completion == "complete"
                and self.verdict in ("match", "diff") and self.counts.known
                and self.pairing_quality == "exact")

    @property
    def is_comparable(self) -> bool:
        return (self.status == "ok"
                and self.completion in ("complete", "partial")
                and self.verdict in ("match", "diff") and self.counts.known
                and self.pairing_quality in ("exact", "capped"))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ComparisonOutcome":
        counts = value.get("counts")
        identities = value.get("source_identities") or ()
        if not isinstance(identities, (list, tuple)):
            raise ValueError("source_identities must be an array")
        if any(not isinstance(item, Mapping) for item in identities):
            raise ValueError("every source identity must be an object")
        if counts is not None and not isinstance(counts, Mapping):
            raise ValueError("counts must be an object")
        pairing_trace = value.get("pairing_trace") or ()
        diagnostics = value.get("capped_group_diagnostics") or ()
        coverage = value.get("coverage_diagnostics") or ()
        if not isinstance(pairing_trace, (list, tuple)):
            raise ValueError("pairing_trace must be an array")
        if not isinstance(diagnostics, (list, tuple)):
            raise ValueError("capped_group_diagnostics must be an array")
        if not isinstance(coverage, (list, tuple)):
            raise ValueError("coverage_diagnostics must be an array")
        if any(not isinstance(item, Mapping) for item in pairing_trace):
            raise ValueError("every serialized pairing trace must be an object")
        if any(not isinstance(item, Mapping) for item in diagnostics):
            raise ValueError(
                "every serialized capped-group diagnostic must be an object")
        if any(not isinstance(item, Mapping) for item in coverage):
            raise ValueError("every coverage diagnostic must be an object")

        typed_diagnostics = []
        legacy_coverage = []
        for item in diagnostics:
            if item.get("kind") == "loaded_side_coverage":
                legacy_coverage.append(dict(item))
            else:
                typed_diagnostics.append(CappedGroupDiagnostic.from_dict(item))
        return cls(
            status=str(value.get("status", "ok") or "ok"),
            completion=str(value.get("completion", UNKNOWN) or UNKNOWN),
            verdict=str(value.get("verdict", UNKNOWN) or UNKNOWN),
            counts=(ComparisonCounts.from_dict(counts)
                    if isinstance(counts, Mapping) else ComparisonCounts()),
            warnings=_strings(value.get("warnings")),
            failures=_strings(value.get("failures")),
            source_identities=tuple(
                SourceIdentity.from_dict(item) for item in identities),
            pairing_trace=tuple(
                PairingTrace.from_dict(item) for item in pairing_trace),
            duplicate_group_count=value.get("duplicate_group_count", 0),
            pairing_quality=str(value.get("pairing_quality", UNKNOWN) or UNKNOWN),
            capped_group_diagnostics=tuple(typed_diagnostics),
            coverage_diagnostics=(tuple(dict(item) for item in coverage)
                                  + tuple(legacy_coverage)),
        )


@dataclass(frozen=True)
class ArtifactGeneration:
    """The exact members committed together as one comparison generation."""

    generation_id: str = ""
    members: Tuple[Mapping[str, Any], ...] = ()
    content_digests: Mapping[str, str] = field(default_factory=dict)
    completion: str = UNKNOWN
    producer_versions: Mapping[str, str] = field(default_factory=dict)
    publication_state: str = UNKNOWN
    requested_mode: str = ""

    def __post_init__(self) -> None:
        _require_choice("completion", self.completion, COMPLETIONS)
        _require_choice("publication_state", self.publication_state,
                        PUBLICATION_STATES)
        members = tuple(self.members)
        if self.publication_state == UNKNOWN and not members:
            return
        if (not isinstance(self.generation_id, str)
                or not self.generation_id.strip()):
            raise ValueError("a published generation requires a generation_id")
        if self.requested_mode not in ("formulas", "values", "both"):
            raise ValueError("a published generation requires a valid requested_mode")
        if self.completion == UNKNOWN:
            raise ValueError("a published generation cannot have unknown completion")
        if not members:
            raise ValueError("a published generation requires at least one member")

        flavors = []
        relative_paths = []
        for member in members:
            if not isinstance(member, Mapping):
                raise ValueError("every artifact member must be an object")
            required = {
                "flavor", "relative_path", "path", "canonical_path_at_write",
                "commit_role", "sha256", "size", "mtime_ns",
            }
            if not required.issubset(member):
                raise ValueError("artifact member is missing required identity fields")
            flavor = member["flavor"]
            if flavor not in ("formulas", "values"):
                raise ValueError("artifact member has an invalid flavor")
            relative = member["relative_path"]
            if (not isinstance(relative, str) or not relative
                    or relative in (".", "..") or "/" in relative
                    or "\\" in relative or ":" in relative):
                raise ValueError("artifact member relative_path must be a safe basename")
            if (not isinstance(member["path"], str) or not member["path"]
                    or not isinstance(member["canonical_path_at_write"], str)
                    or not member["canonical_path_at_write"]):
                raise ValueError("artifact member paths must be non-empty strings")
            role = member["commit_role"]
            if role not in ("canonical", "best_effort"):
                raise ValueError("artifact member has an invalid commit_role")
            digest = member["sha256"]
            if (not isinstance(digest, str)
                    or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
                raise ValueError("artifact member sha256 must be lowercase hexadecimal")
            _require_count("artifact member size", member["size"])
            _require_count("artifact member mtime_ns", member["mtime_ns"])
            flavors.append(flavor)
            relative_paths.append(relative.casefold())
        if len(set(flavors)) != len(flavors):
            raise ValueError("artifact member flavors must be unique")
        if len(set(relative_paths)) != len(relative_paths):
            raise ValueError("artifact member relative paths must be unique")

        expected_flavors = {
            "formulas": ("formulas",),
            "values": ("values",),
            # The formulas member is approved best-effort; values alone is a
            # complete canonical generation when its write does not succeed.
            "both": (("values",), ("values", "formulas")),
        }[self.requested_mode]
        flavor_tuple = tuple(flavors)
        if self.requested_mode == "both":
            valid_flavors = flavor_tuple in expected_flavors
        else:
            valid_flavors = flavor_tuple == expected_flavors
        if not valid_flavors:
            raise ValueError("artifact members do not match requested_mode/order")
        for index, member in enumerate(members):
            expected_role = ("canonical" if index == 0 else "best_effort")
            if member["commit_role"] != expected_role:
                raise ValueError("artifact member commit roles are inconsistent")
        digest_map = dict(self.content_digests)
        if digest_map != {member["flavor"]: member["sha256"] for member in members}:
            raise ValueError("content_digests must exactly mirror artifact members")

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArtifactGeneration":
        members = value.get("members") or ()
        if not isinstance(members, (list, tuple)):
            raise ValueError("members must be an array")
        if any(not isinstance(item, Mapping) for item in members):
            raise ValueError("every artifact member must be an object")
        return cls(
            generation_id=str(value.get("generation_id", "") or ""),
            members=tuple(dict(item) for item in members),
            content_digests={str(k): str(v) for k, v in
                             _mapping(value.get("content_digests")).items()},
            completion=str(value.get("completion", UNKNOWN) or UNKNOWN),
            producer_versions={str(k): str(v) for k, v in
                               _mapping(value.get("producer_versions")).items()},
            publication_state=str(
                value.get("publication_state", UNKNOWN) or UNKNOWN),
            requested_mode=str(value.get("requested_mode", "") or ""),
        )


@dataclass(frozen=True)
class AttemptState:
    """State of the current attempt, independent of the last committed artifact."""

    state: str = "attempted"
    message: str = ""
    generation_id: str = ""

    def __post_init__(self) -> None:
        _require_choice("state", self.state, ATTEMPT_STATES)

    @property
    def succeeded(self) -> bool:
        return self.state == "succeeded"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AttemptState":
        return cls(state=str(value.get("state", "attempted") or "attempted"),
                   message=str(value.get("message", "") or ""),
                   generation_id=str(value.get("generation_id", "") or ""))


ContractType = Union[
    RawIdentityClaim, PhysicalIdentity,
    SourceIdentity, LoadedSide, ComparisonCounts, ComparisonOutcome,
    PairingPair, PairingTrace, CappedGroupDiagnostic,
    ArtifactGeneration, AttemptState,
]
T = TypeVar("T", bound=ContractType)

_TYPES: Dict[str, Type[ContractType]] = {
    cls.__name__: cls for cls in (
        RawIdentityClaim, PhysicalIdentity,
        SourceIdentity, LoadedSide, ComparisonCounts, ComparisonOutcome,
        PairingPair, PairingTrace, CappedGroupDiagnostic,
        ArtifactGeneration, AttemptState,
    )
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, PhysicalKey):
        return {
            "type": _PHYSICAL_KEY_TAG,
            "display": str(value),
            "physical_identity": _jsonable(value.physical_identity),
        }
    if is_dataclass(value):
        return {
            item.name: _jsonable(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def to_dict(value: ContractType) -> Dict[str, Any]:
    """Return a tagged JSON-ready representation for a contract object."""
    if type(value) not in tuple(_TYPES.values()):
        raise TypeError(f"unsupported comparison contract type: {type(value).__name__}")
    return {"schema_version": CONTRACT_SCHEMA_VERSION,
            "type": type(value).__name__, "value": value.to_dict()}


def from_dict(value: Mapping[str, Any]) -> ContractType:
    """Restore a tagged contract representation produced by :func:`to_dict`."""
    if not isinstance(value, Mapping):
        raise ValueError("comparison contract payload must be an object")
    # CMP-AUD-238: the envelope is exactly {schema_version, type, value}. An unknown
    # extra field is a malformed payload, not something to silently ignore.
    _require_exact_fields(value, ("schema_version", "type", "value"),
                          "comparison contract envelope")
    if value.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ValueError("unsupported comparison contract schema_version")
    cls = _TYPES.get(value.get("type"))
    body = value.get("value")
    if cls is None or not isinstance(body, Mapping):
        raise ValueError("comparison contract payload has an unknown type/value")
    return cls.from_dict(body)


def to_json(value: ContractType) -> str:
    return json.dumps(to_dict(value), sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _reject_nonfinite(literal: str):
    # CMP-AUD-238: json.loads accepts NaN/Infinity by default; to_json forbids them
    # (allow_nan=False), so accepting them on read is an asymmetric contract that can
    # decode a payload it can never re-encode. Reject at the parse layer.
    raise ValueError(
        f"comparison contract payload contains a non-finite literal ({literal})")


def _reject_duplicate_keys(pairs):
    # CMP-AUD-238: default json.loads silently keeps the last of duplicate object keys.
    seen: Dict[str, Any] = {}
    for key, val in pairs:
        if key in seen:
            raise ValueError(
                f"comparison contract payload has a duplicate key: {key!r}")
        seen[key] = val
    return seen


def from_json(text: str) -> ContractType:
    return from_dict(json.loads(
        text, parse_constant=_reject_nonfinite,
        object_pairs_hook=_reject_duplicate_keys))


def loaded_side_from_legacy(rows, *, declared_schema=(), route_universe=(),
                            record_universe=(), completion=UNKNOWN, warnings=(),
                            failures=(), skipped_inputs=0, failed_inputs=0,
                            source_identity=None, raw_identity_claims=None,
                            display_metrics=None) -> LoadedSide:
    """Wrap one legacy row-list loader result without inferring coverage."""
    if isinstance(rows, LoadedSide):
        return rows
    return LoadedSide(
        rows=_rows(rows), declared_schema=_strings(declared_schema),
        route_universe=_strings(route_universe),
        record_universe=_strings(record_universe), completion=completion,
        warnings=_strings(warnings), failures=_strings(failures),
        skipped_inputs=skipped_inputs, failed_inputs=failed_inputs,
        source_identity=source_identity,
        raw_identity_claims=_mapping(raw_identity_claims),
        display_metrics=_mapping(display_metrics),
    )


def comparison_outcome_from_legacy(result, *, counts=None, warnings=(),
                                   failures=(), source_identities=(),
                                   pairing_trace=(), duplicate_group_count=0,
                                   pairing_quality=UNKNOWN,
                                   capped_group_diagnostics=(),
                                   coverage_diagnostics=()) -> ComparisonOutcome:
    """Adapt a legacy ``ConsolidateResult`` without parsing summary prose.

    Missing completion on an otherwise-successful legacy result becomes ``unknown``;
    it is intentionally *not* inferred as complete.  Error and cancellation status are
    safe, structural signals and are normalized to failed/cancelled respectively.
    """
    existing = getattr(result, "comparison_outcome", None)
    if isinstance(existing, ComparisonOutcome):
        return existing
    status = getattr(result, "status", UNKNOWN)
    status = status if status in STATUSES else UNKNOWN
    completion = getattr(result, "completion", None)
    # Structural terminal status dominates contradictory/missing legacy fields.
    # This is the safe reducer for CMP-AUD-116: ``error + complete`` can never
    # survive adaptation as a completed comparison.
    if status == "cancelled":
        completion = "cancelled"
    elif status == "error":
        completion = "failed"
    elif completion not in COMPLETIONS:
        completion = UNKNOWN
    verdict = getattr(result, "verdict", None)
    if verdict not in VERDICTS:
        verdict = UNKNOWN
    typed_counts = (counts if isinstance(counts, ComparisonCounts)
                    else ComparisonCounts())
    normalized_pairing_quality = str(pairing_quality or UNKNOWN)
    if status == "ok" and completion in ("complete", "partial"):
        if (not typed_counts.known or verdict not in ("match", "diff")
                or normalized_pairing_quality not in ("exact", "capped")):
            completion, verdict = UNKNOWN, UNKNOWN
    elif completion not in ("complete", "partial"):
        verdict = UNKNOWN
    typed_failures = _strings(failures)
    if status == "error" and not typed_failures:
        message = getattr(result, "message", "")
        if message:
            typed_failures = (str(message),)
    return ComparisonOutcome(
        status=status, completion=completion, verdict=verdict,
        counts=typed_counts,
        warnings=_strings(warnings), failures=typed_failures,
        source_identities=tuple(source_identities or ()),
        pairing_trace=tuple(pairing_trace or ()),
        duplicate_group_count=duplicate_group_count,
        pairing_quality=normalized_pairing_quality,
        capped_group_diagnostics=tuple(capped_group_diagnostics or ()),
        coverage_diagnostics=tuple(coverage_diagnostics or ()),
    )


def finalize_comparison_result(result):
    """Attach fail-closed typed state at a public comparison boundary.

    Successful comparison artifact transactions already carry their exact
    :class:`ComparisonOutcome`, :class:`ArtifactGeneration`, and
    :class:`AttemptState`.  Earlier terminal branches (missing input, malformed
    shape, declined overwrite, dependency failure, or commit failure) historically
    returned a bare ``ConsolidateResult``.  Normalize those structural outcomes
    without parsing summary text and without inventing an artifact generation.

    The legacy outer ``completion`` is synchronized only for error/cancelled or
    absent/invalid values.  A successful but unstructured legacy result keeps its
    compatibility fields while its typed outcome remains ``unknown`` and therefore
    unusable by strict consumers.
    """
    typed = comparison_outcome_from_legacy(result)
    result.comparison_outcome = typed

    status = getattr(result, "status", UNKNOWN)
    legacy_completion = getattr(result, "completion", None)
    if status in ("error", "cancelled") or legacy_completion not in COMPLETIONS:
        result.completion = typed.completion

    attempt = getattr(result, "attempt_state", None)
    if not isinstance(attempt, AttemptState):
        if typed.status == "cancelled" or typed.completion == "cancelled":
            state = "cancelled"
        elif typed.status == "error" or typed.completion in ("failed", "no_data"):
            state = "failed"
        elif typed.completion == "partial":
            state = "partial"
        elif typed.is_complete:
            state = "succeeded"
        else:
            # A public call has returned, so "attempted" would misleadingly imply
            # work is still in flight.  Unknown/unstructured terminal truth failed
            # to produce a trustworthy comparison result.
            state = "failed"
        result.attempt_state = AttemptState(
            state=state, message=str(getattr(result, "message", "") or ""))
    return result


def comparison_result_boundary(fn):
    """Decorate one public comparison driver so every returned path is typed."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        return finalize_comparison_result(fn(*args, **kwargs))
    return wrapped

"""Independent current-schema Intersection Detail adapter for the Phase-3 oracle.

This is acceptance evidence, not application code.  It imports only the generic
stdlib XLSX stream and independent comparison oracle in ``build/``.  Report
schemas, physical projections, and normalizers are intentionally re-declared
here; no production loader, comparator, catalog, sidecar, or prior comparison
workbook is consulted at runtime.

The TSMIS July-2026 export has 35 columns whose labels are not fully aligned to
their values.  Its projection is therefore physical-position authoritative.
The raw TSN workbook has one exact 36-column ``Sheet 1`` schema.  Both sides
produce :class:`OracleRow` values keyed by structured ``(Route, PM)``.  PM is an
identity component and is not double-counted: the remaining 32 shared fields are
all asserting.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import math
from pathlib import Path
import re
import stat
from typing import Iterable, Optional, Sequence, Tuple

from phase3_independent_oracle import (
    FieldRule,
    OracleRow,
    OracleSchema,
    ValueRule,
    compare_rows,
)
from phase3_xlsx_stream import (
    SCALAR,
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    XlsxLimits,
    capture_file_identity,
    read_sheet,
)


CANARY_ID = "CORE-ID-78-XLSX-TSN"
MANIFEST_HEADER = "# tsmis-comparison-canary-manifest-v1"
TSMIS_ROLE = "tsmis_xlsx"
TSN_ROLE = "tsn_xlsx"
ID78_ALIAS = "id78"
ALL619_ALIAS = "all619"

TSMIS_SHEET = "Intersection Detail"
TSN_SHEET = "Sheet 1"

# Exact July-2026 site export.  Dates are text in the bound corpus; every column
# is deliberately SCALAR.  Semantic date positions are normalized below.
TSMIS_HEADERS = (
    "P", "Post Mile", "S", "Location", "Date of Record", "H/G",
    "City Code", "R/U", "INT Type", "INT Eff-Date", "Ctrl T",
    "Ctrl Type", "Light Eff-Date", "Light T/Y", "ML Eff-Date",
    "ML S/M", "ML L/C", "ML R/C", "ML T/P", "ML N/L",
    "Description", "Main Line Lgth", "Inter Eff-Date", "Inter S",
    "Inter L", "Inter R", "Inter T", "Inter N", "Int St Eff-Date",
    "Intrte S", "Intrte Route", "Intrte Post", "Intrte Mile",
    "Xing P/S", "Xing Line Lgth",
)

# Exact SHA-bound raw TSN header, independently enumerated on 2026-07-12.  The
# early synthetic application fixtures omitted MAIN_ADT/CROSS_ADT and placed
# X_CROSS_OVERRIDE later; that shape is not accepted here.
TSN_HEADERS = (
    "PP", "POST_MILE", "LOCATION", "DATE_REC", "HG", "CITY_CODE", "RU",
    "EFF_DATE_INT", "TY_INT", "EFF_DATE_CT", "TY_CT", "EFF_DATE_LT",
    "LT_TY", "EFF_DATE_ML", "MAIN_SM", "MAIN_LC", "MAIN_RC", "MAIN_TF",
    "MAIN_NL", "X_CROSS_OVERRIDE", "MAIN_EFF_DATE", "MAIN_ADT",
    "DESCRIPTION", "MAIN_OVERRIDE", "CROSS_BEGIN_DATE", "CS_SM", "CS_LC",
    "CS_RC", "CS_TF", "CS_NL", "EFF_DATE", "CROSS_ADT",
    "CROSS_ROUTE_NAME", "CROSS_PM_PREFIX", "CROSS_POSTMILE",
    "CROSS_PM_SUFFIX",
)

SHARED_HEADER = (
    "PR", "Route Suffix", "PM", "Date of Record", "HG", "City Code", "R/U",
    "INT Type Eff-Date", "INT Type", "Control Type Eff-Date", "Control Type",
    "Lighting Eff-Date", "Lighting", "ML Eff-Date", "ML Mastarm",
    "ML Left Chan", "ML Right Chan", "ML Traffic Flow", "ML Num Lanes",
    "Description", "Main Line Length", "CS Eff-Date", "CS Mastarm",
    "CS Left Chan", "CS Right Chan", "CS Traffic Flow", "CS Num Lanes",
    "Int St Eff-Date", "Intrte Route", "Intrte PM Prefix", "Intrte Postmile",
    "Intrte PM Suffix", "Xing Line Lgth",
)
ASSERTED_FIELDS = tuple(field for field in SHARED_HEADER if field != "PM")

if len(TSMIS_HEADERS) != 35 or len(TSN_HEADERS) != 36:
    raise AssertionError("Intersection Detail source schemas have the wrong width")
if len(SHARED_HEADER) != 33 or len(ASSERTED_FIELDS) != 32:
    raise AssertionError("Intersection Detail oracle field schema has the wrong width")

ORACLE_SCHEMA = OracleSchema(
    key_rules=(ValueRule("Route"), ValueRule("PM")),
    field_rules=tuple(FieldRule(field, asserting=True) for field in ASSERTED_FIELDS),
)

TSMIS_SPEC = SheetSpec(
    TSMIS_SHEET,
    tuple(ColumnSpec(header, SCALAR) for header in TSMIS_HEADERS),
    exact_schema=True,
)
TSN_SPEC = SheetSpec(
    TSN_SHEET,
    tuple(ColumnSpec(header, SCALAR) for header in TSN_HEADERS),
    exact_schema=True,
)


class IntersectionOracleError(ValueError):
    """A report-specific source value or physical projection is invalid."""


class CorpusSelectionError(ValueError):
    """The fixed canary member selector did not resolve exactly."""


class CorpusMutationError(ValueError):
    """The selected canary member set/content changed across a binding."""


# Consolidated production once prepended Route; these zero-based positions are
# the original 35-column per-route cells.  The first three effective-date labels
# are visibly shifted: physical INT Type/Ctrl T/Light Eff-Date cells contain the
# dates, and the following cells contain the codes.  Never map these by semantic
# label.
_TSMIS_POSITION = {
    "PR": 0,
    "PM": 1,
    "Date of Record": 4,
    "HG": 5,
    "City Code": 6,
    "R/U": 7,
    "INT Type Eff-Date": 8,
    "INT Type": 9,
    "Control Type Eff-Date": 10,
    "Control Type": 11,
    "Lighting Eff-Date": 12,
    "Lighting": 13,
    "ML Eff-Date": 14,
    "ML Mastarm": 15,
    "ML Left Chan": 16,
    "ML Right Chan": 17,
    "ML Traffic Flow": 18,
    "ML Num Lanes": 19,
    "Description": 20,
    "Main Line Length": 21,
    "CS Eff-Date": 22,
    "CS Mastarm": 23,
    "CS Left Chan": 24,
    "CS Right Chan": 25,
    "CS Traffic Flow": 26,
    "CS Num Lanes": 27,
    "Int St Eff-Date": 28,
    "Intrte Route": 30,
    "Intrte PM Prefix": 31,
    "Intrte Postmile": 32,
    "Intrte PM Suffix": 33,
    "Xing Line Lgth": 34,
}
_TSMIS_LOCATION_POSITION = 3

_TSN_COLUMN = {
    "PR": "PP",
    "PM": "POST_MILE",
    "Date of Record": "DATE_REC",
    "HG": "HG",
    "City Code": "CITY_CODE",
    "R/U": "RU",
    "INT Type Eff-Date": "EFF_DATE_INT",
    "INT Type": "TY_INT",
    "Control Type Eff-Date": "EFF_DATE_CT",
    "Control Type": "TY_CT",
    "Lighting Eff-Date": "EFF_DATE_LT",
    "Lighting": "LT_TY",
    "ML Eff-Date": "EFF_DATE_ML",
    "ML Mastarm": "MAIN_SM",
    "ML Left Chan": "MAIN_LC",
    "ML Right Chan": "MAIN_RC",
    "ML Traffic Flow": "MAIN_TF",
    "ML Num Lanes": "MAIN_NL",
    "Description": "DESCRIPTION",
    "Main Line Length": "MAIN_OVERRIDE",
    "CS Eff-Date": "CROSS_BEGIN_DATE",
    "CS Mastarm": "CS_SM",
    "CS Left Chan": "CS_LC",
    "CS Right Chan": "CS_RC",
    "CS Traffic Flow": "CS_TF",
    "CS Num Lanes": "CS_NL",
    "Int St Eff-Date": "EFF_DATE",
    "Intrte Route": "CROSS_ROUTE_NAME",
    "Intrte PM Prefix": "CROSS_PM_PREFIX",
    "Intrte Postmile": "CROSS_POSTMILE",
    "Intrte PM Suffix": "CROSS_PM_SUFFIX",
    "Xing Line Lgth": "X_CROSS_OVERRIDE",
}
_TSN_INDEX = {header: index for index, header in enumerate(TSN_HEADERS)}

_DATE_FIELDS = frozenset((
    "Date of Record", "INT Type Eff-Date", "Control Type Eff-Date",
    "Lighting Eff-Date", "ML Eff-Date", "CS Eff-Date", "Int St Eff-Date",
))
_BOOLEAN_FIELDS = frozenset((
    "Lighting", "ML Mastarm", "ML Right Chan", "CS Mastarm", "CS Right Chan",
))
_NUMERIC_FIELDS = frozenset((
    "Main Line Length", "Intrte Route", "Intrte Postmile", "Xing Line Lgth",
))
_SIGNALIZED = frozenset(("J", "K", "L", "M", "N", "P", "S"))
_BOOL = {"Y": "Y", "N": "N", "1": "Y", "0": "N"}
_PM_NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_FIELD_NUMBER = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_LOCATION = re.compile(
    r"[ ]*[0-9]{1,2}[ ]+[A-Z]{2,3}\.?[ ]+([0-9]+)([A-Z]?)[ ]*")
_MEMBER = re.compile(r"intersection_detail_route_([0-9]{3}[A-Z]?)\.xlsx")
_EXPECTED_SUFFIXED_ROUTES = frozenset(("008U", "010S", "014U", "058U", "178S", "210U"))


def _ascii_strip(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise IntersectionOracleError("non-finite Decimal source value")
        return format(value, "f")
    return str(value).strip(" ")


def _shortest_excel_numeric_text(value) -> str:
    """Materialize an XLSX numeric scalar like openpyxl's binary64 path.

    The independent XLSX stream preserves numeric OOXML lexicals as Decimal,
    while the application reader exposes ordinary Excel numbers as Python
    binary64 floats.  Only Decimal takes this typed seam: text that happens to
    look numeric must retain its exact lexical semantics.

    Conversion is intentionally narrow.  The binary64 result must be finite,
    non-underflowing, and expressible with at most Excel's 15 significant
    decimal digits in Python's shortest round-trip spelling.  This admits known
    OOXML binary artifacts such as 0.92100000000000004 -> 0.921 without turning
    the oracle into a general lossy decimal coercion.
    """
    if not isinstance(value, Decimal):
        return _ascii_strip(value)
    if not value.is_finite():
        raise IntersectionOracleError("non-finite Decimal source value")
    try:
        binary64 = float(value)
    except (OverflowError, ValueError) as exc:
        raise IntersectionOracleError(
            "XLSX numeric scalar is outside binary64 range") from exc
    if not math.isfinite(binary64):
        raise IntersectionOracleError(
            "XLSX numeric scalar is outside finite binary64 range")
    if value != 0 and binary64 == 0.0:
        raise IntersectionOracleError("XLSX numeric scalar underflows binary64")

    shortest = repr(binary64)
    shortest_decimal = Decimal(shortest)
    significant_digits = (
        1 if shortest_decimal.is_zero()
        else len(shortest_decimal.normalize().as_tuple().digits)
    )
    if significant_digits > 15:
        raise IntersectionOracleError(
            "XLSX numeric scalar requires more than 15 significant digits")
    return shortest


def normalize_numeric_field(value) -> str:
    """Current compared-field rule: narrow optional-minus decimal text.

    Leading integer zeros and trailing fractional zeros are insignificant.
    Explicit plus and leading-dot forms are outside the grammar and remain raw.
    A negative zero remains negative, matching the current report projection.
    """
    text = _shortest_excel_numeric_text(value)
    if text == "":
        return ""
    if _FIELD_NUMBER.fullmatch(text) is None:
        return text
    negative = text.startswith("-")
    body = text[1:] if negative else text
    if "." in body:
        whole, fraction = body.split(".", 1)
        whole = whole.lstrip("0") or "0"
        fraction = fraction.rstrip("0")
        body = whole + (f".{fraction}" if fraction else "")
    else:
        body = body.lstrip("0") or "0"
    return ("-" if negative else "") + body


def normalize_pm(value) -> str:
    """Current PM identity rule, independently encoded.

    Strip integer leading zeros, preserve fractional trailing zeros, accept an
    optional minus, turn a leading decimal into ``0.x``, and preserve negative
    zero.  Explicit-plus or otherwise non-PM text stays raw so it cannot be
    silently paired with a valid numeric key.
    """
    text = _shortest_excel_numeric_text(value)
    if text == "":
        raise IntersectionOracleError("Intersection Detail row has a blank PM key")
    if _PM_NUMBER.fullmatch(text) is None:
        return text
    negative = text.startswith("-")
    body = text[1:] if negative else text
    body = body.lstrip("0") or "0"
    if body.startswith("."):
        body = "0" + body
    return ("-" if negative else "") + body


def split_route(value) -> Tuple[str, str]:
    text = _ascii_strip(value).upper().replace("-", " ")
    match = _LOCATION.fullmatch(text)
    if match is None:
        raise IntersectionOracleError(f"invalid district/county/route LOCATION: {text!r}")
    return f"{int(match.group(1)):03d}", match.group(2)


def normalize_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _ascii_strip(value)
    if text == "":
        return ""
    match = re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})", text)
    if match:
        year, month, day = int(match.group(3)), int(match.group(1)), int(match.group(2))
    else:
        match = re.match(r"([0-9]{4})-([0-9]{2})-([0-9]{2})(?:[ T].*)?$", text)
        if match:
            year, month, day = map(int, match.groups())
        else:
            match = re.fullmatch(r"([0-9]{2})-([0-9]{2})-([0-9]{2})", text)
            if match is None:
                return text
            short, month, day = map(int, match.groups())
            year = (1900 if short >= 30 else 2000) + short
    try:
        return date(year, month, day).isoformat()
    except ValueError as exc:
        raise IntersectionOracleError(f"invalid report date: {text!r}") from exc


def normalize_bool(value) -> str:
    if type(value) is bool:
        return "Y" if value else "N"
    text = _ascii_strip(value)
    if isinstance(value, Decimal) and value in (Decimal(0), Decimal(1)):
        text = str(int(value))
    return _BOOL.get(text.upper(), text)


def normalize_control_type(value) -> str:
    text = _ascii_strip(value)
    return "S" if text.upper() in _SIGNALIZED else text


def _project(field: str, raw):
    if field == "PM":
        return normalize_pm(raw)
    if field in _DATE_FIELDS:
        return normalize_date(raw)
    if field in _BOOLEAN_FIELDS:
        return normalize_bool(raw)
    if field == "Control Type":
        return normalize_control_type(raw)
    if field in _NUMERIC_FIELDS:
        return normalize_numeric_field(raw)
    return raw


def _oracle_row(projected: dict[str, object], *, route: str,
                source_index: int, source_ref: str) -> OracleRow:
    pm = projected["PM"]
    return OracleRow(
        source_index=source_index,
        key=(route, pm),
        values=tuple(projected[field] for field in ASSERTED_FIELDS),
        source_ref=source_ref,
    )


def adapt_tsmis_values(values: Sequence[object], *, source_index: int,
                       source_ref: str = "") -> OracleRow:
    """Adapt one exact 35-cell TSMIS row by physical value position."""
    if len(values) != len(TSMIS_HEADERS):
        raise IntersectionOracleError(
            f"TSMIS row width {len(values)} != {len(TSMIS_HEADERS)}")
    route, suffix = split_route(values[_TSMIS_LOCATION_POSITION])
    projected = {
        field: (suffix if field == "Route Suffix"
                else _project(field, values[_TSMIS_POSITION[field]]))
        for field in SHARED_HEADER
    }
    return _oracle_row(projected, route=route, source_index=source_index,
                       source_ref=source_ref)


def adapt_tsn_values(values: Sequence[object], *, source_index: int,
                     source_ref: str = "") -> OracleRow:
    """Adapt one exact 36-cell raw TSN row by its pinned header projection."""
    if len(values) != len(TSN_HEADERS):
        raise IntersectionOracleError(
            f"TSN row width {len(values)} != {len(TSN_HEADERS)}")
    route, suffix = split_route(values[_TSN_INDEX["LOCATION"]])
    projected = {
        field: (suffix if field == "Route Suffix"
                else _project(field, values[_TSN_INDEX[_TSN_COLUMN[field]]]))
        for field in SHARED_HEADER
    }
    return _oracle_row(projected, route=route, source_index=source_index,
                       source_ref=source_ref)


def _row_has_data(values: Sequence[object]) -> bool:
    return any(value is not None and value != "" for value in values)


@dataclass(frozen=True, order=True)
class RouteProvenanceDiagnostic:
    """Non-blocking evidence that a row's Location crosses member routes."""

    member_token: str
    derived_token: str
    source_ref: str


def diagnose_tsmis_route(
        values: Sequence[object], *, member_token: str,
        source_ref: str = "") -> Optional[RouteProvenanceDiagnostic]:
    """Return a Location/member mismatch without adapting or rejecting the row.

    This is an optional pure validation API.  The workbook reader deliberately
    does not call it: reader correctness and row retention cannot be changed by
    callers wrapping, replacing, or otherwise opting into this validation.
    """
    if len(values) != len(TSMIS_HEADERS):
        raise IntersectionOracleError(
            f"TSMIS row width {len(values)} != {len(TSMIS_HEADERS)}")
    if re.fullmatch(r"[0-9]{3}[A-Z]?", member_token) is None:
        raise IntersectionOracleError("invalid TSMIS member route token")
    route, suffix = split_route(values[_TSMIS_LOCATION_POSITION])
    derived_token = f"{route}{suffix}"
    if member_token == derived_token:
        return None
    return RouteProvenanceDiagnostic(
        member_token=member_token,
        derived_token=derived_token,
        source_ref=source_ref,
    )


@dataclass(frozen=True)
class AdaptedSide:
    rows: Tuple[OracleRow, ...]
    source_identities: Tuple[FileIdentity, ...]
    next_source_index: int
    route_diagnostics: Tuple[RouteProvenanceDiagnostic, ...] = ()


def _start_index(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("start_index must be a non-negative integer")
    return value


def read_tsmis_workbook(path, *, start_index: int = 0,
                         limits: Optional[XlsxLimits] = None) -> AdaptedSide:
    start_index = _start_index(start_index)
    source = Path(path)
    match = _MEMBER.fullmatch(source.name)
    if match is None:
        raise CorpusSelectionError(
            "TSMIS canary member name does not match the exact route grammar")
    streamed = read_sheet(source, TSMIS_SPEC, limits=limits)
    rows = []
    route_diagnostics = []
    next_index = start_index
    member_token = match.group(1)
    suffix_position = ASSERTED_FIELDS.index("Route Suffix")
    for raw in streamed.rows:
        if not _row_has_data(raw.values):
            continue
        source_ref = f"{streamed.pre_identity.canonical_path}#row={raw.source_row}"
        row = adapt_tsmis_values(
            raw.values,
            source_index=next_index,
            source_ref=source_ref,
        )
        rows.append(row)
        derived_token = f"{row.key[0]}{row.values[suffix_position]}"
        if member_token != derived_token:
            route_diagnostics.append(RouteProvenanceDiagnostic(
                member_token=member_token,
                derived_token=derived_token,
                source_ref=source_ref,
            ))
        next_index += 1
    return AdaptedSide(
        rows=tuple(rows),
        source_identities=(streamed.pre_identity,),
        next_source_index=next_index,
        route_diagnostics=tuple(route_diagnostics),
    )


def read_tsmis_workbooks(paths: Iterable[Path], *, start_index: int = 0,
                          limits: Optional[XlsxLimits] = None) -> AdaptedSide:
    next_index = _start_index(start_index)
    selected = tuple(sorted((Path(path) for path in paths), key=lambda path: path.name))
    names = [path.name.casefold() for path in selected]
    if len(names) != len(set(names)):
        raise CorpusSelectionError("duplicate/case-colliding TSMIS member paths")
    rows = []
    identities = []
    route_diagnostics = []
    for path in selected:
        adapted = read_tsmis_workbook(path, start_index=next_index, limits=limits)
        rows.extend(adapted.rows)
        identities.extend(adapted.source_identities)
        route_diagnostics.extend(adapted.route_diagnostics)
        next_index = adapted.next_source_index
    return AdaptedSide(
        tuple(rows), tuple(identities), next_index, tuple(route_diagnostics))


def read_tsn_workbook(path, *, start_index: int = 0,
                      limits: Optional[XlsxLimits] = None) -> AdaptedSide:
    next_index = _start_index(start_index)
    streamed = read_sheet(path, TSN_SPEC, limits=limits)
    rows = []
    for raw in streamed.rows:
        if not _row_has_data(raw.values):
            continue
        rows.append(adapt_tsn_values(
            raw.values,
            source_index=next_index,
            source_ref=f"{streamed.pre_identity.canonical_path}#row={raw.source_row}",
        ))
        next_index += 1
    return AdaptedSide(
        rows=tuple(rows),
        source_identities=(streamed.pre_identity,),
        next_source_index=next_index,
    )


def compare_adapted(tsmis: AdaptedSide, tsn: AdaptedSide):
    if not isinstance(tsmis, AdaptedSide) or not isinstance(tsn, AdaptedSide):
        raise TypeError("compare_adapted requires two AdaptedSide values")
    return compare_rows(ORACLE_SCHEMA, tsmis.rows, tsn.rows)


@dataclass(frozen=True, order=True)
class ManifestRecord:
    role: str
    root_alias: str
    relative_path: str
    length: int
    sha256: str

    @property
    def line(self) -> str:
        return (f"{self.role}\t{self.root_alias}\t{self.relative_path}\t"
                f"{self.length}\t{self.sha256}")


@dataclass(frozen=True)
class ManifestSnapshot:
    records: Tuple[ManifestRecord, ...]
    serialized: bytes
    sha256: str
    source_bytes: int


@dataclass(frozen=True)
class CorpusSelection:
    corpus_root: Path
    id78_root: Path
    all619_root: Path
    tsmis_files: Tuple[Path, ...]
    tsn_file: Path


@dataclass(frozen=True)
class CorpusBinding:
    corpus_root: Path
    pre_manifest: ManifestSnapshot


def _reject_reparse(info) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise CorpusSelectionError("canary source may not be a symbolic link")
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if int(getattr(info, "st_file_attributes", 0) or 0) & reparse:
        raise CorpusSelectionError("canary source may not be a reparse point")


def _require_directory(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise CorpusSelectionError(f"missing canary directory: {path}") from exc
    _reject_reparse(info)
    if not stat.S_ISDIR(info.st_mode):
        raise CorpusSelectionError(f"canary path is not a directory: {path}")


def _require_regular(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise CorpusSelectionError(f"missing canary file: {path}") from exc
    _reject_reparse(info)
    if not stat.S_ISREG(info.st_mode):
        raise CorpusSelectionError(f"canary path is not an ordinary file: {path}")


def select_corpus(corpus_root) -> CorpusSelection:
    """Resolve the exact 217+1 CORE-ID-78 raw-member set, without hashing it."""
    root = Path(corpus_root).absolute()
    id78 = root / "ground-truth" / "Intersection Detail Bundle 7.8"
    all619 = root / "ground-truth" / "All Reports 6.19"
    tsmis_dir = id78 / "intersection_detail"
    tsn_dir = all619 / "TSN" / "Intersection Detail"
    for directory in (root, id78, all619, tsmis_dir, tsn_dir):
        _require_directory(directory)

    tsmis_entries = tuple(tsmis_dir.iterdir())
    for entry in tsmis_entries:
        _require_regular(entry)
        if _MEMBER.fullmatch(entry.name) is None:
            raise CorpusSelectionError(
                f"unexpected direct TSMIS canary member: {entry.name!r}")
    tsmis_files = tuple(sorted(tsmis_entries, key=lambda path: path.name))
    if len(tsmis_files) != 217:
        raise CorpusSelectionError(
            f"expected 217 TSMIS route workbooks, found {len(tsmis_files)}")
    tokens = [_MEMBER.fullmatch(path.name).group(1) for path in tsmis_files]
    if len(tokens) != len(set(tokens)):
        raise CorpusSelectionError("duplicate TSMIS route token in canary member set")
    suffixed = {token for token in tokens if token[-1:].isalpha()}
    if suffixed != _EXPECTED_SUFFIXED_ROUTES:
        raise CorpusSelectionError(
            f"TSMIS suffixed-route universe changed: {sorted(suffixed)!r}")
    if "170" in tokens:
        raise CorpusSelectionError("route 170 unexpectedly reappeared in the ID-78 canary")
    folded = [path.name.casefold() for path in tsmis_files]
    if len(folded) != len(set(folded)):
        raise CorpusSelectionError("case-colliding TSMIS canary member names")

    exact_tsn = tsn_dir / "TSAR - INTERSECTION DETAIL_TSN.xlsx"
    tsn_entries = tuple(tsn_dir.iterdir())
    if len(tsn_entries) != 1 or tsn_entries[0].name != exact_tsn.name:
        raise CorpusSelectionError("TSN canary directory must contain only the exact raw workbook")
    _require_regular(exact_tsn)
    return CorpusSelection(root, id78, all619, tsmis_files, exact_tsn)


def capture_manifest(selection: CorpusSelection) -> ManifestSnapshot:
    """Capture the versioned deterministic content manifest for one selection."""
    if not isinstance(selection, CorpusSelection):
        raise TypeError("selection must be a CorpusSelection")
    inputs = [
        (TSMIS_ROLE, ID78_ALIAS, selection.id78_root, path)
        for path in selection.tsmis_files
    ] + [(TSN_ROLE, ALL619_ALIAS, selection.all619_root, selection.tsn_file)]
    records = []
    for role, alias, alias_root, path in inputs:
        identity = capture_file_identity(path)
        try:
            relative = path.relative_to(alias_root).as_posix()
        except ValueError as exc:
            raise CorpusSelectionError("selected member escaped its root alias") from exc
        if any(char in relative for char in ("\t", "\r", "\n")):
            raise CorpusSelectionError("manifest path contains a forbidden control character")
        records.append(ManifestRecord(
            role=role,
            root_alias=alias,
            relative_path=relative,
            length=identity.size,
            sha256=identity.sha256.lower(),
        ))
    records = tuple(sorted(records, key=lambda record: record.line))
    text = MANIFEST_HEADER + "\n" + "\n".join(record.line for record in records) + "\n"
    serialized = text.encode("utf-8")
    return ManifestSnapshot(
        records=records,
        serialized=serialized,
        sha256=hashlib.sha256(serialized).hexdigest(),
        source_bytes=sum(record.length for record in records),
    )


def capture_pre_binding(corpus_root) -> CorpusBinding:
    selection = select_corpus(corpus_root)
    return CorpusBinding(selection.corpus_root, capture_manifest(selection))


def verify_post_binding(binding: CorpusBinding) -> ManifestSnapshot:
    """Re-enumerate/re-hash and require exact membership/content stability."""
    if not isinstance(binding, CorpusBinding):
        raise TypeError("binding must be a CorpusBinding")
    try:
        current = capture_manifest(select_corpus(binding.corpus_root))
    except (CorpusSelectionError, OSError) as exc:
        raise CorpusMutationError(f"canary member set changed: {exc}") from exc
    if current.serialized != binding.pre_manifest.serialized:
        raise CorpusMutationError(
            f"canary input manifest changed: {binding.pre_manifest.sha256} -> {current.sha256}")
    return current

"""Generic stdlib-only streaming XLSX reader for independent Phase-3 evidence.

The reader resolves an exact worksheet through the OPC workbook relationships,
streams XML one row at a time, and projects only a caller-declared schema.  It
does not know any report family, production loader, comparison output, or corpus
path.  Numeric values remain :class:`~decimal.Decimal`; dates are converted only
when a column is explicitly declared as a date.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_EVEN
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
from typing import BinaryIO, Iterator, Optional, Sequence, Tuple
from xml.etree import ElementTree
import zipfile


SCALAR = "scalar"
DATE = "date"
_VALUE_KINDS = frozenset((SCALAR, DATE))
_CELL_REF = re.compile(r"([A-Z]+)([1-9][0-9]*)")
_SPREADSHEET_NAMESPACES = frozenset((
    "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "http://purl.oclc.org/ooxml/spreadsheetml/main",
))
_OFFICE_REL_NAMESPACES = frozenset((
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "http://purl.oclc.org/ooxml/officeDocument/relationships",
))
_PACKAGE_REL_NAMESPACES = frozenset((
    "http://schemas.openxmlformats.org/package/2006/relationships",
    "http://purl.oclc.org/ooxml/package/relationships",
))
_WORKSHEET_REL_TYPES = frozenset(
    namespace + "/worksheet" for namespace in _OFFICE_REL_NAMESPACES)
_WORKBOOK = "xl/workbook.xml"
_WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
_SHARED_STRINGS = "xl/sharedStrings.xml"
_STYLES = "xl/styles.xml"
_XML_FORBIDDEN = (b"<!DOCTYPE", b"<!ENTITY")
_DAY_MICROSECONDS = 86_400_000_000
_BUILTIN_DATE_FORMAT_IDS = frozenset(
    tuple(range(14, 23)) + tuple(range(27, 37))
    + tuple(range(45, 48)) + tuple(range(50, 59)))


class XlsxStreamError(ValueError):
    """Base class for a rejected independent XLSX input."""


class XlsxSecurityError(XlsxStreamError):
    """The archive/XML exceeded a safety boundary or used an unsafe construct."""


class XlsxSchemaError(XlsxStreamError):
    """The requested sheet/header/cell contract was not satisfied."""


class XlsxMutationError(XlsxStreamError):
    """The source identity or digest changed during capture/read."""


@dataclass(frozen=True)
class XlsxLimits:
    max_source_bytes: int = 512 * 1024 * 1024
    max_archive_members: int = 1_024
    max_member_uncompressed: int = 128 * 1024 * 1024
    max_total_uncompressed: int = 512 * 1024 * 1024
    max_compression_ratio: int = 2_000
    max_xml_depth: int = 64
    max_xml_events: int = 5_000_000
    max_shared_strings: int = 1_000_000
    max_rows: int = 1_048_576
    max_columns: int = 16_384
    max_cell_text: int = 1_000_000

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ColumnSpec:
    """One required header and its independently declared scalar kind."""

    header: str
    value_kind: str = SCALAR

    def __post_init__(self) -> None:
        if not isinstance(self.header, str) or not self.header:
            raise ValueError("column header must be a non-empty string")
        if self.value_kind not in _VALUE_KINDS:
            raise ValueError(f"unsupported column value kind: {self.value_kind!r}")


@dataclass(frozen=True)
class SheetSpec:
    """Exact worksheet and header-row projection contract."""

    sheet_name: str
    columns: Tuple[ColumnSpec, ...]
    header_row: int = 1
    exact_schema: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.sheet_name, str) or not self.sheet_name:
            raise ValueError("sheet_name must be a non-empty exact name")
        if not self.columns or any(not isinstance(c, ColumnSpec) for c in self.columns):
            raise ValueError("columns must contain at least one ColumnSpec")
        headers = [column.header for column in self.columns]
        if len(headers) != len(set(headers)):
            raise ValueError("declared headers must be unique")
        if (isinstance(self.header_row, bool)
                or not isinstance(self.header_row, int) or self.header_row < 1):
            raise ValueError("header_row must be a positive integer")
        if type(self.exact_schema) is not bool:
            raise ValueError("exact_schema must be a Boolean")


@dataclass(frozen=True)
class FileIdentity:
    canonical_path: str
    size: int
    mtime_ns: int
    device: int
    inode: int
    sha256: str


@dataclass(frozen=True)
class CapturedFile:
    """One private immutable payload plus the exact live source identity it captured."""

    identity: FileIdentity
    payload: bytes


@dataclass(frozen=True)
class StreamedRow:
    source_row: int
    values: Tuple[object, ...]


@dataclass(frozen=True)
class StreamedSheet:
    sheet_name: str
    headers: Tuple[str, ...]
    rows: Tuple[StreamedRow, ...]
    date_system: str
    pre_identity: FileIdentity
    post_identity: FileIdentity


class _GuardedXmlReader:
    """Scan the streamed bytes for constructs this evidence reader never needs."""

    def __init__(self, raw: BinaryIO):
        self._raw = raw
        self._tail = b""
        self._prefix = raw.read(4096)
        self._prefix_offset = 0
        self._validate_encoding(self._prefix)

    @staticmethod
    def _validate_encoding(prefix: bytes) -> None:
        if (prefix.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff",
                              b"\xff\xfe\x00\x00")) or b"\x00" in prefix):
            raise XlsxSecurityError("only UTF-8 XLSX XML is supported")
        text = prefix[3:] if prefix.startswith(b"\xef\xbb\xbf") else prefix
        stripped = text.lstrip(b" \t\r\n")
        if stripped.startswith(b"<?xml"):
            end = stripped.find(b"?>")
            if end < 0:
                raise XlsxSecurityError("XLSX XML declaration exceeds the prefix limit")
            declaration = stripped[:end + 2]
            match = re.search(
                br"encoding\s*=\s*(['\"])([^'\"]+)\1", declaration,
                flags=re.IGNORECASE)
            if match is not None and match.group(2).decode("ascii", "ignore").casefold() not in (
                    "utf-8", "utf8"):
                raise XlsxSecurityError("only UTF-8 XLSX XML is supported")

    def read(self, size: int = -1) -> bytes:
        if self._prefix_offset < len(self._prefix):
            if size is None or size < 0:
                data = self._prefix[self._prefix_offset:] + self._raw.read()
                self._prefix_offset = len(self._prefix)
            else:
                end = min(len(self._prefix), self._prefix_offset + size)
                data = self._prefix[self._prefix_offset:end]
                self._prefix_offset = end
                if len(data) < size:
                    data += self._raw.read(size - len(data))
        else:
            data = self._raw.read(size)
        probe = (self._tail + data).upper()
        if any(token in probe for token in _XML_FORBIDDEN):
            raise XlsxSecurityError("DTD/entity declarations are forbidden in XLSX XML")
        self._tail = probe[-16:]
        return data


def _stat_token(info) -> Tuple[int, int, int, int]:
    return (int(info.st_size), int(info.st_mtime_ns),
            int(info.st_dev), int(info.st_ino))


def _path_lstat(path: Path):
    return path.lstat()


def _reject_link_or_reparse(info) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise XlsxSecurityError("XLSX source may not be a symbolic link")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = int(getattr(info, "st_file_attributes", 0) or 0)
    if attributes & reparse_flag:
        raise XlsxSecurityError("XLSX source may not be a reparse point")


def _verify_bound_path(path: Path, bound_info) -> None:
    """Require the pathname to still name the exact regular open file."""
    current = _path_lstat(path)
    _reject_link_or_reparse(current)
    if not stat.S_ISREG(current.st_mode):
        raise XlsxSecurityError("XLSX source must be a regular file")
    if _stat_token(current) != _stat_token(bound_info):
        raise XlsxMutationError("XLSX pathname no longer names the bound open file")


def _open_bound_source(path):
    """Open once, then bind the path's non-link identity to that descriptor."""
    candidate = Path(path).absolute()
    initial = _path_lstat(candidate)
    _reject_link_or_reparse(initial)
    if not stat.S_ISREG(initial.st_mode):
        raise XlsxSecurityError("XLSX source must be a regular file")
    handle = candidate.open("rb")
    try:
        bound = os.fstat(handle.fileno())
        if not stat.S_ISREG(bound.st_mode):
            raise XlsxSecurityError("bound XLSX handle is not a regular file")
        _verify_bound_path(candidate, bound)
    except Exception:
        handle.close()
        raise
    return candidate, handle, bound


def _hash_bound_handle(handle: BinaryIO, bound_info, *, chunk_size: int) -> str:
    before = os.fstat(handle.fileno())
    if _stat_token(before) != _stat_token(bound_info):
        raise XlsxMutationError("bound XLSX handle changed before hashing")
    handle.seek(0)
    digest = hashlib.sha256()
    while True:
        block = handle.read(chunk_size)
        if not block:
            break
        digest.update(block)
    after = os.fstat(handle.fileno())
    if _stat_token(after) != _stat_token(bound_info):
        raise XlsxMutationError("bound XLSX handle changed while hashing")
    return digest.hexdigest()


def _copy_bound_handle(handle: BinaryIO, bound_info, *, chunk_size: int,
                       max_bytes: int) -> Tuple[bytes, str]:
    """Copy one live handle into private bytes and hash exactly the copied payload."""
    before = os.fstat(handle.fileno())
    if _stat_token(before) != _stat_token(bound_info):
        raise XlsxMutationError("bound XLSX handle changed before private capture")
    handle.seek(0)
    digest = hashlib.sha256()
    payload = bytearray()
    while True:
        block = handle.read(chunk_size)
        if not block:
            break
        if len(payload) + len(block) > max_bytes:
            raise XlsxSecurityError("compressed XLSX source exceeds the capture-size limit")
        payload.extend(block)
        digest.update(block)
    after = os.fstat(handle.fileno())
    if _stat_token(after) != _stat_token(bound_info):
        raise XlsxMutationError("bound XLSX handle changed during private capture")
    return bytes(payload), digest.hexdigest()


def _file_identity(path: Path, bound_info, digest: str) -> FileIdentity:
    return FileIdentity(
        canonical_path=str(path), size=int(bound_info.st_size),
        mtime_ns=int(bound_info.st_mtime_ns), device=int(bound_info.st_dev),
        inode=int(bound_info.st_ino), sha256=digest)


def capture_file_identity(path, *, chunk_size: int = 1024 * 1024) -> FileIdentity:
    """Hash one bound regular-file handle and reject path/descriptor drift."""
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    candidate, handle, bound = _open_bound_source(path)
    try:
        digest = _hash_bound_handle(handle, bound, chunk_size=chunk_size)
        _verify_bound_path(candidate, bound)
        return _file_identity(candidate, bound, digest)
    finally:
        handle.close()


def capture_file_bytes(path, *, chunk_size: int = 1024 * 1024,
                       max_bytes: int = 512 * 1024 * 1024) -> CapturedFile:
    """Return private immutable bytes only when pre/capture/post identities agree."""
    for name, value in (("chunk_size", chunk_size), ("max_bytes", max_bytes)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    candidate, handle, bound = _open_bound_source(path)
    try:
        pre_digest = _hash_bound_handle(handle, bound, chunk_size=chunk_size)
        payload, capture_digest = _copy_bound_handle(
            handle, bound, chunk_size=chunk_size, max_bytes=max_bytes)
        post_digest = _hash_bound_handle(handle, bound, chunk_size=chunk_size)
        _verify_bound_path(candidate, bound)
        if not pre_digest == capture_digest == post_digest:
            raise XlsxMutationError(
                "XLSX bytes changed across pre-hash/private-capture/post-hash")
        return CapturedFile(
            identity=_file_identity(candidate, bound, capture_digest),
            payload=payload)
    finally:
        handle.close()


def _safe_member_name(name: str) -> bool:
    if not name or "\\" in name or ":" in name or name.startswith("/"):
        return False
    parts = PurePosixPath(name).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def _validate_archive(archive: zipfile.ZipFile, limits: XlsxLimits) -> set[str]:
    infos = archive.infolist()
    if len(infos) > limits.max_archive_members:
        raise XlsxSecurityError("XLSX archive contains too many members")
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise XlsxSecurityError("XLSX archive contains duplicate member names")
    folded_names = [name.casefold() for name in names]
    if len(folded_names) != len(set(folded_names)):
        raise XlsxSecurityError("XLSX archive contains case-colliding member names")
    total = 0
    for info in infos:
        if not _safe_member_name(info.filename):
            raise XlsxSecurityError(f"unsafe XLSX member name: {info.filename!r}")
        if info.flag_bits & 0x1:
            raise XlsxSecurityError("encrypted XLSX members are not supported")
        if info.file_size > limits.max_member_uncompressed:
            raise XlsxSecurityError("XLSX member exceeds the uncompressed-size limit")
        total += info.file_size
        if total > limits.max_total_uncompressed:
            raise XlsxSecurityError("XLSX archive exceeds the total uncompressed-size limit")
        if info.file_size and info.file_size / max(info.compress_size, 1) > limits.max_compression_ratio:
            raise XlsxSecurityError("XLSX member exceeds the compression-ratio limit")
    available = set(names)
    for required in (_WORKBOOK, _WORKBOOK_RELS):
        if required not in available:
            raise XlsxSchemaError(f"XLSX archive is missing {required}")
    return available


def _xml_events(archive: zipfile.ZipFile, member: str,
                limits: XlsxLimits) -> Iterator[Tuple[str, ElementTree.Element]]:
    """Yield checked start/end events without materializing a document tree."""
    try:
        raw = archive.open(member, "r")
    except KeyError as exc:
        raise XlsxSchemaError(f"XLSX archive is missing {member}") from exc
    depth = 0
    event_count = 0
    try:
        guarded = _GuardedXmlReader(raw)
        try:
            parser = ElementTree.iterparse(guarded, events=("start", "end"))
            for event, element in parser:
                event_count += 1
                if event_count > limits.max_xml_events:
                    raise XlsxSecurityError("XLSX XML exceeds the event limit")
                if event == "start":
                    depth += 1
                    if depth > limits.max_xml_depth:
                        raise XlsxSecurityError("XLSX XML exceeds the nesting-depth limit")
                yield event, element
                if event == "end":
                    depth -= 1
        except ElementTree.ParseError as exc:
            raise XlsxStreamError(f"malformed XLSX XML member {member}: {exc}") from exc
    finally:
        raw.close()


def _tag_parts(tag: str) -> Tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _local_name(tag: str) -> str:
    return _tag_parts(tag)[1]


def _workbook_catalog(archive: zipfile.ZipFile, limits: XlsxLimits):
    sheets = []
    date_system = "1900"
    spreadsheet_ns = None
    critical = {"workbook", "workbookPr", "sheets", "sheet"}
    for event, element in _xml_events(archive, _WORKBOOK, limits):
        namespace, local = _tag_parts(element.tag)
        if event == "start" and local == "workbook":
            if namespace not in _SPREADSHEET_NAMESPACES:
                raise XlsxSchemaError("workbook root uses an unsupported namespace")
            spreadsheet_ns = namespace
        if local in critical and spreadsheet_ns is not None and namespace != spreadsheet_ns:
            raise XlsxSchemaError(f"workbook element {local!r} uses the wrong namespace")
        if event != "end":
            continue
        if local == "workbookPr":
            value = str(element.attrib.get("date1904", "0")).lower()
            if value in ("1", "true"):
                date_system = "1904"
            elif value not in ("0", "false", ""):
                raise XlsxSchemaError("workbook date1904 flag is invalid")
        elif local == "sheet":
            name = element.attrib.get("name")
            rel_values = []
            for attr_name, attr_value in element.attrib.items():
                attr_ns, attr_local = _tag_parts(attr_name)
                if attr_local == "id":
                    if attr_ns not in _OFFICE_REL_NAMESPACES:
                        raise XlsxSchemaError(
                            "workbook sheet relationship uses the wrong namespace")
                    rel_values.append(attr_value)
            rel_id = rel_values[0] if len(rel_values) == 1 else None
            if not name or not rel_id:
                raise XlsxSchemaError("workbook sheet entry is missing name/relationship")
            sheets.append((name, rel_id))
        element.clear()
    if spreadsheet_ns is None:
        raise XlsxSchemaError("workbook root element is missing")
    if not sheets:
        raise XlsxSchemaError("workbook contains no sheets")
    rel_ids = [rel_id for _name, rel_id in sheets]
    if len(rel_ids) != len(set(rel_ids)):
        raise XlsxSchemaError("multiple workbook sheets reuse one relationship ID")
    return tuple(sheets), date_system


def _relationship_catalog(archive: zipfile.ZipFile, limits: XlsxLimits):
    relationships = {}
    seen_ids = set()
    package_ns = None
    critical = {"Relationships", "Relationship"}
    for event, element in _xml_events(archive, _WORKBOOK_RELS, limits):
        namespace, local = _tag_parts(element.tag)
        if event == "start" and local == "Relationships":
            if namespace not in _PACKAGE_REL_NAMESPACES:
                raise XlsxSchemaError("relationship root uses an unsupported namespace")
            package_ns = namespace
        if local in critical and package_ns is not None and namespace != package_ns:
            raise XlsxSchemaError(f"relationship element {local!r} uses the wrong namespace")
        if event != "end" or local != "Relationship":
            continue
        rel_id = element.attrib.get("Id")
        target = element.attrib.get("Target")
        rel_type = element.attrib.get("Type", "")
        if not rel_id:
            raise XlsxSchemaError("workbook relationship is missing its ID")
        if rel_id in seen_ids:
            raise XlsxSchemaError("duplicate workbook relationship ID")
        seen_ids.add(rel_id)
        if rel_id and target and rel_type in _WORKSHEET_REL_TYPES:
            relationships[rel_id] = target
        element.clear()
    if package_ns is None:
        raise XlsxSchemaError("relationship root element is missing")
    return relationships


def _resolve_sheet_member(archive: zipfile.ZipFile, limits: XlsxLimits,
                          available: set[str], exact_name: str):
    sheets, date_system = _workbook_catalog(archive, limits)
    matches = [(name, rel_id) for name, rel_id in sheets if name == exact_name]
    if len(matches) != 1:
        if not matches:
            raise XlsxSchemaError(f"workbook has no exact sheet named {exact_name!r}")
        raise XlsxSchemaError(f"workbook has duplicate sheets named {exact_name!r}")
    relationships = _relationship_catalog(archive, limits)
    rel_id = matches[0][1]
    if rel_id not in relationships:
        raise XlsxSchemaError("selected sheet relationship is missing or is not a worksheet")
    target = relationships[rel_id]
    if target.startswith("/"):
        member = posixpath.normpath(target.lstrip("/"))
    else:
        member = posixpath.normpath(posixpath.join("xl", target))
    if (not member.startswith("xl/") or not _safe_member_name(member)
            or member not in available):
        raise XlsxSchemaError("selected sheet relationship target is unsafe or missing")
    return member, date_system


def _text_parts(element: ElementTree.Element, spreadsheet_ns: str) -> str:
    parts = []
    for node in element.iter():
        namespace, local = _tag_parts(node.tag)
        if local == "t":
            if namespace != spreadsheet_ns:
                raise XlsxSchemaError("string text element uses the wrong namespace")
            parts.append(node.text or "")
    return "".join(parts)


def _shared_strings(archive: zipfile.ZipFile, limits: XlsxLimits,
                    available: set[str]) -> Tuple[str, ...]:
    if _SHARED_STRINGS not in available:
        return ()
    values = []
    shared_root = None
    spreadsheet_ns = None
    critical = {"sst", "si", "r", "t"}
    for event, element in _xml_events(archive, _SHARED_STRINGS, limits):
        namespace, local = _tag_parts(element.tag)
        if event == "start" and local == "sst":
            if namespace not in _SPREADSHEET_NAMESPACES:
                raise XlsxSchemaError("shared-string root uses an unsupported namespace")
            spreadsheet_ns = namespace
            shared_root = element
        if local in critical and spreadsheet_ns is not None and namespace != spreadsheet_ns:
            raise XlsxSchemaError(f"shared-string element {local!r} uses the wrong namespace")
        if event == "end" and local == "si":
            text = _text_parts(element, spreadsheet_ns)
            if len(text) > limits.max_cell_text:
                raise XlsxSecurityError("shared string exceeds the text-size limit")
            values.append(text)
            if len(values) > limits.max_shared_strings:
                raise XlsxSecurityError("shared-string table exceeds the entry limit")
            element.clear()
            if shared_root is not None:
                shared_root.remove(element)
    if spreadsheet_ns is None:
        raise XlsxSchemaError("shared-string root element is missing")
    return tuple(values)


def _date_format_code(format_code: str) -> bool:
    """Recognize Excel date/time tokens while ignoring literals/conditions."""
    kept = []
    i = 0
    quoted = False
    while i < len(format_code):
        char = format_code[i]
        if char == '"':
            quoted = not quoted
            i += 1
            continue
        if quoted:
            i += 1
            continue
        if char in ("\\", "_", "*"):
            i += 2
            continue
        if char == "[":
            end = format_code.find("]", i + 1)
            if end < 0:
                return False
            content = format_code[i + 1:end].strip().casefold()
            if content and set(content) <= {"h", "m", "s"}:
                kept.append(content)
            i = end + 1
            continue
        kept.append(char)
        i += 1
    if quoted:
        return False
    normalized = "".join(kept).casefold()
    return bool(re.search(r"am/pm|a/p|[ymdhs]", normalized))


def _date_styles(archive: zipfile.ZipFile, limits: XlsxLimits,
                 available: set[str]) -> Tuple[bool, ...]:
    """Return whether each cellXfs style carries a recognized date/time format."""
    if _STYLES not in available:
        return (False,)
    custom_formats = {}
    style_format_ids = []
    in_cell_xfs = False
    spreadsheet_ns = None
    critical = {"styleSheet", "numFmts", "numFmt", "cellXfs", "xf"}
    for event, element in _xml_events(archive, _STYLES, limits):
        namespace, local = _tag_parts(element.tag)
        if event == "start" and local == "styleSheet":
            if namespace not in _SPREADSHEET_NAMESPACES:
                raise XlsxSchemaError("style root uses an unsupported namespace")
            spreadsheet_ns = namespace
        if local in critical and spreadsheet_ns is not None and namespace != spreadsheet_ns:
            raise XlsxSchemaError(f"style element {local!r} uses the wrong namespace")
        if event == "start" and local == "cellXfs":
            in_cell_xfs = True
            continue
        if event != "end":
            continue
        if local == "numFmt":
            raw_id = element.attrib.get("numFmtId", "")
            code = element.attrib.get("formatCode")
            try:
                format_id = int(raw_id)
            except ValueError as exc:
                raise XlsxSchemaError("custom number format has an invalid ID") from exc
            if format_id < 0 or code is None or format_id in custom_formats:
                raise XlsxSchemaError("custom number format is missing/duplicated")
            custom_formats[format_id] = code
        elif local == "xf" and in_cell_xfs:
            raw_id = element.attrib.get("numFmtId", "0")
            try:
                format_id = int(raw_id)
            except ValueError as exc:
                raise XlsxSchemaError("cell style has an invalid number-format ID") from exc
            if format_id < 0:
                raise XlsxSchemaError("cell style number-format ID cannot be negative")
            style_format_ids.append(format_id)
        elif local == "cellXfs":
            in_cell_xfs = False
        element.clear()
    if spreadsheet_ns is None:
        raise XlsxSchemaError("style root element is missing")
    if not style_format_ids:
        return (False,)
    return tuple(
        format_id in _BUILTIN_DATE_FORMAT_IDS
        or (format_id in custom_formats
            and _date_format_code(custom_formats[format_id]))
        for format_id in style_format_ids)


def _column_number(letters: str, limits: XlsxLimits) -> int:
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - ord("A") + 1
        if value > limits.max_columns:
            raise XlsxSecurityError("worksheet column exceeds the configured limit")
    return value


def _cell_coordinate(reference: str, limits: XlsxLimits) -> Tuple[int, int]:
    match = _CELL_REF.fullmatch(reference or "")
    if match is None:
        raise XlsxSchemaError(f"invalid or missing cell coordinate: {reference!r}")
    column = _column_number(match.group(1), limits)
    row = int(match.group(2))
    if row > limits.max_rows:
        raise XlsxSecurityError("worksheet row exceeds the configured limit")
    return row, column


def _row_cells(row_element: ElementTree.Element, row_number: int,
               limits: XlsxLimits, spreadsheet_ns: str):
    cells = {}
    last_column = 0
    for element in row_element:
        namespace, local = _tag_parts(element.tag)
        if local != "c":
            continue
        if namespace != spreadsheet_ns:
            raise XlsxSchemaError("worksheet cell uses the wrong namespace")
        cell_row, column = _cell_coordinate(element.attrib.get("r", ""), limits)
        if cell_row != row_number:
            raise XlsxSchemaError("cell coordinate disagrees with its worksheet row")
        if column <= last_column or column in cells:
            raise XlsxSchemaError("worksheet cells are duplicated or out of order")
        last_column = column
        cells[column] = element
    return cells


def _child(element: ElementTree.Element, name: str, spreadsheet_ns: str):
    found = []
    for child in element:
        namespace, local = _tag_parts(child.tag)
        if local != name:
            continue
        if namespace != spreadsheet_ns:
            raise XlsxSchemaError(f"worksheet {name!r} element uses the wrong namespace")
        found.append(child)
    if len(found) > 1:
        raise XlsxSchemaError(f"worksheet cell contains duplicate {name!r} elements")
    return found[0] if found else None


def _cell_raw_value(cell: ElementTree.Element, shared: Sequence[str],
                    limits: XlsxLimits, *, forbid_formula: bool):
    spreadsheet_ns, local = _tag_parts(cell.tag)
    if local != "c" or spreadsheet_ns not in _SPREADSHEET_NAMESPACES:
        raise XlsxSchemaError("required cell uses an unsupported namespace")
    formula = _child(cell, "f", spreadsheet_ns)
    if formula is not None and forbid_formula:
        raise XlsxSchemaError(
            f"formula is forbidden in required source cell {cell.attrib.get('r', '?')}")
    cell_type = cell.attrib.get("t", "n")
    value_element = _child(cell, "v", spreadsheet_ns)
    lexical = "" if value_element is None or value_element.text is None else value_element.text
    if len(lexical) > limits.max_cell_text:
        raise XlsxSecurityError("cell value exceeds the text-size limit")

    if cell_type == "inlineStr":
        inline = _child(cell, "is", spreadsheet_ns)
        text = "" if inline is None else _text_parts(inline, spreadsheet_ns)
        if len(text) > limits.max_cell_text:
            raise XlsxSecurityError("inline string exceeds the text-size limit")
        return text, cell_type
    if cell_type == "s":
        try:
            index = int(lexical)
        except ValueError as exc:
            raise XlsxSchemaError("shared-string cell has an invalid index") from exc
        if index < 0 or index >= len(shared):
            raise XlsxSchemaError("shared-string index is out of range")
        return shared[index], cell_type
    if cell_type == "b":
        if lexical not in ("0", "1"):
            raise XlsxSchemaError("Boolean cell must contain 0 or 1")
        return lexical == "1", cell_type
    if cell_type == "e":
        raise XlsxSchemaError(
            f"error is forbidden in required source cell {cell.attrib.get('r', '?')}: "
            f"{lexical or '(blank error)'}")
    if cell_type in ("str", "d"):
        return lexical, cell_type
    if cell_type not in ("n", ""):
        raise XlsxSchemaError(f"unsupported XLSX cell type: {cell_type!r}")
    if lexical == "":
        return None, "n"
    try:
        return Decimal(lexical), "n"
    except InvalidOperation as exc:
        raise XlsxSchemaError("numeric cell is not a valid decimal lexical value") from exc


def _iso_date(text: str):
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        if "T" in candidate or " " in candidate:
            return datetime.fromisoformat(candidate)
        return date.fromisoformat(candidate)
    except ValueError as exc:
        raise XlsxSchemaError("declared ISO date cell is invalid") from exc


def _excel_serial(value: Decimal, date_system: str):
    if not value.is_finite() or value < 0:
        raise XlsxSchemaError("declared Excel date serial must be finite and non-negative")
    day_number = int(value.to_integral_value(rounding=ROUND_FLOOR))
    fraction = value - Decimal(day_number)
    if date_system == "1900":
        if day_number == 60:
            raise XlsxSchemaError("fictional Excel 1900-02-29 serial is unsupported")
        adjusted = day_number if day_number < 60 else day_number - 1
        base = date(1899, 12, 31)
    elif date_system == "1904":
        adjusted = day_number
        base = date(1904, 1, 1)
    else:
        raise XlsxSchemaError("unknown workbook date system")
    micros = int((fraction * Decimal(_DAY_MICROSECONDS)).to_integral_value(
        rounding=ROUND_HALF_EVEN))
    whole_days, micros = divmod(micros, _DAY_MICROSECONDS)
    day_value = base + timedelta(days=adjusted + whole_days)
    if micros == 0:
        return day_value
    return datetime.combine(day_value, time()) + timedelta(microseconds=micros)


def _declared_value(cell: Optional[ElementTree.Element], column: ColumnSpec,
                    shared: Sequence[str], limits: XlsxLimits, date_system: str,
                    date_styles: Sequence[bool]):
    if cell is None:
        return None
    value, cell_type = _cell_raw_value(cell, shared, limits, forbid_formula=True)
    if column.value_kind == SCALAR or value is None or cell_type == "e":
        return value
    if cell_type == "n" and isinstance(value, Decimal):
        raw_style = cell.attrib.get("s", "0")
        try:
            style_index = int(raw_style)
        except ValueError as exc:
            raise XlsxSchemaError("declared date cell has an invalid style index") from exc
        if (style_index < 0 or style_index >= len(date_styles)
                or not date_styles[style_index]):
            raise XlsxSchemaError(
                f"numeric date column {column.header!r} lacks a recognized date/time style")
        return _excel_serial(value, date_system)
    if cell_type == "d" and isinstance(value, str):
        return _iso_date(value)
    raise XlsxSchemaError(
        f"declared date column {column.header!r} contains a non-date cell")


def _header_projection(cells, spec: SheetSpec, shared, limits):
    observed = []
    seen = set()
    for column_number, cell in cells.items():
        value, _cell_type = _cell_raw_value(
            cell, shared, limits, forbid_formula=True)
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise XlsxSchemaError("worksheet headers must be text")
        if value in seen:
            raise XlsxSchemaError(f"duplicate worksheet header: {value!r}")
        seen.add(value)
        observed.append((column_number, value))
    expected = tuple(column.header for column in spec.columns)
    observed_names = tuple(name for _number, name in observed)
    missing = tuple(name for name in expected if name not in seen)
    if missing:
        raise XlsxSchemaError(f"worksheet is missing required headers: {missing!r}")
    if spec.exact_schema and observed_names != expected:
        raise XlsxSchemaError(
            f"worksheet header schema/order mismatch: {observed_names!r} != {expected!r}")
    position_by_name = {name: number for number, name in observed}
    return tuple(position_by_name[column.header] for column in spec.columns)


def _stream_worksheet(archive: zipfile.ZipFile, member: str, spec: SheetSpec,
                      shared: Sequence[str], limits: XlsxLimits,
                      date_system: str,
                      date_styles: Sequence[bool]) -> Tuple[StreamedRow, ...]:
    positions = None
    rows = []
    last_row = 0
    sheet_data = None
    spreadsheet_ns = None
    critical = {"worksheet", "sheetData", "row", "c", "f", "v", "is", "r", "t"}
    for event, element in _xml_events(archive, member, limits):
        namespace, local = _tag_parts(element.tag)
        if event == "start" and local == "worksheet":
            if namespace not in _SPREADSHEET_NAMESPACES:
                raise XlsxSchemaError("worksheet root uses an unsupported namespace")
            spreadsheet_ns = namespace
        if local in critical and spreadsheet_ns is not None and namespace != spreadsheet_ns:
            raise XlsxSchemaError(f"worksheet element {local!r} uses the wrong namespace")
        if event == "start" and local == "sheetData":
            sheet_data = element
        if event != "end" or local != "row":
            continue
        raw_number = element.attrib.get("r", "")
        try:
            row_number = int(raw_number)
        except ValueError as exc:
            raise XlsxSchemaError("worksheet row has an invalid/missing number") from exc
        if row_number < 1 or row_number <= last_row:
            raise XlsxSchemaError("worksheet rows are duplicated or out of order")
        if row_number > limits.max_rows:
            raise XlsxSecurityError("worksheet row exceeds the configured limit")
        last_row = row_number
        cells = _row_cells(element, row_number, limits, spreadsheet_ns)
        if row_number == spec.header_row:
            positions = _header_projection(cells, spec, shared, limits)
        elif row_number > spec.header_row:
            if positions is None:
                raise XlsxSchemaError("declared header row is missing")
            if spec.exact_schema:
                declared_positions = set(positions)
                for column_number, undeclared_cell in cells.items():
                    if column_number in declared_positions:
                        continue
                    undeclared_value, _cell_type = _cell_raw_value(
                        undeclared_cell, shared, limits, forbid_formula=True)
                    if undeclared_value not in (None, ""):
                        raise XlsxSchemaError(
                            "exact-schema row contains nonempty data beneath an "
                            "empty or undeclared header")
            values = tuple(
                _declared_value(cells.get(position), column, shared, limits,
                                date_system, date_styles)
                for position, column in zip(positions, spec.columns))
            rows.append(StreamedRow(source_row=row_number, values=values))
            if len(rows) > limits.max_rows:
                raise XlsxSecurityError("worksheet data-row count exceeds the limit")
        element.clear()
        if sheet_data is not None:
            sheet_data.remove(element)
    if positions is None:
        raise XlsxSchemaError("declared header row is missing")
    if spreadsheet_ns is None:
        raise XlsxSchemaError("worksheet root element is missing")
    return tuple(rows)


def read_sheet(path, spec: SheetSpec, *,
               limits: Optional[XlsxLimits] = None) -> StreamedSheet:
    """Read one exact worksheet and verify source identity before and after.

    XML is streamed with ``iterparse``; only the selected row values are retained.
    The bound live descriptor is pre-hashed, copied and hashed into a private immutable
    compressed payload, then post-hashed after that private payload is parsed.  Any
    pre/capture/post, stat, or pathname disagreement rejects the result instead of
    blessing a mixed or synchronized A-to-B-to-A generation.
    """
    if not isinstance(spec, SheetSpec):
        raise TypeError("spec must be a SheetSpec")
    limits = limits or XlsxLimits()
    if not isinstance(limits, XlsxLimits):
        raise TypeError("limits must be XlsxLimits")
    candidate, handle, bound = _open_bound_source(path)
    try:
        pre_digest = _hash_bound_handle(handle, bound, chunk_size=1024 * 1024)
        pre = _file_identity(candidate, bound, pre_digest)
        payload, capture_digest = _copy_bound_handle(
            handle, bound, chunk_size=1024 * 1024,
            max_bytes=limits.max_source_bytes)
        if capture_digest != pre_digest:
            raise XlsxMutationError(
                "XLSX private capture differs from the pre-hash")
        try:
            with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
                available = _validate_archive(archive, limits)
                member, date_system = _resolve_sheet_member(
                    archive, limits, available, spec.sheet_name)
                shared = _shared_strings(archive, limits, available)
                date_styles = _date_styles(archive, limits, available)
                rows = _stream_worksheet(
                    archive, member, spec, shared, limits, date_system,
                    date_styles)
        except zipfile.BadZipFile as exc:
            raise XlsxStreamError("source is not a readable XLSX ZIP archive") from exc
        if _stat_token(os.fstat(handle.fileno())) != _stat_token(bound):
            raise XlsxMutationError("bound XLSX handle changed while private bytes were parsed")
        post_digest = _hash_bound_handle(handle, bound, chunk_size=1024 * 1024)
        _verify_bound_path(candidate, bound)
        post = _file_identity(candidate, bound, post_digest)
        if pre != post or post_digest != capture_digest:
            raise XlsxMutationError(
                "bound XLSX SHA-256 changed across private capture/parsing")
    finally:
        handle.close()
    return StreamedSheet(
        sheet_name=spec.sheet_name,
        headers=tuple(column.header for column in spec.columns),
        rows=rows, date_system=date_system,
        pre_identity=pre, post_identity=post)

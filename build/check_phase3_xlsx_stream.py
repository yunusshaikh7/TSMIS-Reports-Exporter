"""Synthetic adversarial checks for the stdlib-only Phase-3 XLSX stream."""
from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import phase3_xlsx_stream as stream


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "build" / "phase3_xlsx_stream.py"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def rejects(error_type, fn, contains=None):
    try:
        fn()
    except error_type as exc:
        if contains is not None:
            check(contains.lower() in str(exc).lower(),
                  f"wrong rejection text: {exc}")
        return
    raise AssertionError(f"expected {error_type.__name__}")


def fake_stat(info, **changes):
    values = {
        "st_mode": info.st_mode,
        "st_size": info.st_size,
        "st_mtime_ns": info.st_mtime_ns,
        "st_dev": info.st_dev,
        "st_ino": info.st_ino,
        "st_file_attributes": getattr(info, "st_file_attributes", 0),
    }
    values.update(changes)
    return SimpleNamespace(**values)


def workbook_xml(sheets, *, date1904=False, preamble=""):
    entries = "".join(
        f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(sheets, 1))
    flag = ' date1904="1"' if date1904 else ""
    return (f'{preamble}<workbook xmlns="{NS}" xmlns:r="{REL}">'
            f'<workbookPr{flag}/><sheets>{entries}</sheets></workbook>')


def rels_xml(count):
    entries = "".join(
        f'<Relationship Id="rId{i}" '
        f'Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, count + 1))
    return f'<Relationships xmlns="{PKG_REL}">{entries}</Relationships>'


def shared_xml(values):
    entries = "".join(f'<si><t xml:space="preserve">{value}</t></si>'
                      for value in values)
    return f'<sst xmlns="{NS}" count="{len(values)}" uniqueCount="{len(values)}">{entries}</sst>'


def styles_xml(date_format_code=None):
    if date_format_code is None:
        formats = ""
        date_format_id = 14
    else:
        formats = (f'<numFmts count="1"><numFmt numFmtId="164" '
                   f'formatCode="{date_format_code}"/></numFmts>')
        date_format_id = 164
    return (f'<styleSheet xmlns="{NS}">{formats}'
            f'<cellXfs count="2"><xf numFmtId="0"/>'
            f'<xf numFmtId="{date_format_id}" applyNumberFormat="1"/>'
            f'</cellXfs></styleSheet>')


def sheet_xml(rows):
    return f'<worksheet xmlns="{NS}"><sheetData>{"".join(rows)}</sheetData></worksheet>'


def row(number, cells):
    return f'<row r="{number}">{"".join(cells)}</row>'


def cell(ref, value=None, *, kind=None, formula=None, inline_parts=None, style=None):
    type_attr = f' t="{kind}"' if kind else ""
    style_attr = f' s="{style}"' if style is not None else ""
    formula_xml = f'<f>{formula}</f>' if formula is not None else ""
    if kind == "inlineStr":
        parts = inline_parts if inline_parts is not None else (str(value or ""),)
        body = "".join(f'<r><t>{part}</t></r>' for part in parts)
        return f'<c r="{ref}"{type_attr}{style_attr}>{formula_xml}<is>{body}</is></c>'
    value_xml = "" if value is None else f'<v>{value}</v>'
    return f'<c r="{ref}"{type_attr}{style_attr}>{formula_xml}{value_xml}</c>'


def write_xlsx(path, sheets, *, shared=(), date1904=False,
               workbook_preamble="", duplicate_member=None,
               compression=zipfile.ZIP_DEFLATED, include_styles=True,
               date_format_code=None, workbook_payload=None,
               rels_payload=None, styles_payload=None, shared_payload=None):
    path = Path(path)
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        archive.writestr("xl/workbook.xml", workbook_payload if workbook_payload is not None
                         else workbook_xml(
                             tuple(name for name, _xml in sheets), date1904=date1904,
                             preamble=workbook_preamble))
        archive.writestr("xl/_rels/workbook.xml.rels",
                         rels_payload if rels_payload is not None else rels_xml(len(sheets)))
        if shared_payload is not None:
            archive.writestr("xl/sharedStrings.xml", shared_payload)
        elif shared:
            archive.writestr("xl/sharedStrings.xml", shared_xml(shared))
        if include_styles:
            archive.writestr("xl/styles.xml",
                             styles_payload if styles_payload is not None
                             else styles_xml(date_format_code))
        for index, (_name, xml) in enumerate(sheets, 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
        if duplicate_member is not None:
            archive.writestr(duplicate_member, b"duplicate")
    return path


def main_spec(*, exact=True):
    return stream.SheetSpec(
        "Data",
        (
            stream.ColumnSpec("ID"),
            stream.ColumnSpec("Shared"),
            stream.ColumnSpec("Inline"),
            stream.ColumnSpec("Flag"),
            stream.ColumnSpec("Error"),
            stream.ColumnSpec("Number"),
            stream.ColumnSpec("When", stream.DATE),
        ),
        exact_schema=exact)


def primary_rows(*, formula=False, duplicate_header=False, extra_header=False,
                 reorder_header=False, date_value="61", header_formula=False,
                 date_style=1, hidden_data=False, trailing_data=False,
                 error_cell=False):
    shared_header = 2 if reorder_header else 1
    inline_header = 1 if reorder_header else 2
    headers = (
        cell("A1", 0, kind="s", formula="1+1" if header_formula else None),
        cell("C1", shared_header, kind="s"),
        cell("E1", inline_header, kind="s"),
        cell("G1", 3, kind="s"),
        cell("I1", 4, kind="s"),
        cell("K1", 5, kind="s"),
        cell("M1", 6 if not duplicate_header else 5, kind="s"),
    ) + ((cell("O1", 7, kind="s"),) if extra_header else ())
    row2 = (
        cell("A2", "alpha", kind="inlineStr"),
    ) + ((cell("B2", "hidden", kind="str"),) if hidden_data else ()) + (
        cell("C2", 8, kind="s"),
        cell("E2", kind="inlineStr", inline_parts=("in", "line")),
        cell("G2", 1, kind="b"),
        cell("I2", "#N/A", kind="e" if error_cell else "str"),
        cell("K2", "12345678901234567890.125", formula="2+2" if formula else None),
        cell("M2", date_value, style=date_style),
    ) + ((cell("O2", "trailing", kind="str"),) if trailing_data else ())
    return (
        row(1, headers),
        row(2, row2),
        row(3, (cell("A3", "beta", kind="str"),
                cell("M3", "61.5", style=date_style))),
        row(4, (cell("A4", "gamma", kind="str"), cell("K4", "5"))),
    )


SHARED = ("ID", "Shared", "Inline", "Flag", "Error", "Number", "When",
          "Unexpected", " shared text ")


def test_forbidden_imports():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "__import__"):
            raise AssertionError("dynamic imports are forbidden")
    allowed = {
        "__future__", "dataclasses", "datetime", "decimal", "hashlib", "pathlib",
        "io", "os", "posixpath", "re", "stat", "typing", "xml", "zipfile",
    }
    check(imports <= allowed, f"non-stdlib/undeclared imports: {imports - allowed}")
    forbidden = (
        "open" + "pyxl", "pandas", "numpy", "compare" + "_core",
        "compare" + "_env", "comparison" + "_contract",
        "consolidation" + "_meta", "matrix" + "_state",
    )
    lowered = source.lower()
    check(not any(name.lower() in lowered for name in forbidden),
          "streaming layer names a forbidden production/third-party dependency")


def test_types_sparse_dates_and_sheet_resolution(root):
    data = sheet_xml(primary_rows())
    other = sheet_xml((row(1, (cell("A1", "Other", kind="str"),)),))
    path = write_xlsx(root / "primary.xlsx", (("Data", data), ("Other", other)),
                      shared=SHARED)
    result = stream.read_sheet(path, main_spec())
    check(result.sheet_name == "Data" and result.date_system == "1900",
          "exact sheet/date-system resolution failed")
    check(result.pre_identity == result.post_identity
          and len(result.pre_identity.sha256) == 64,
          "pre/post file identity was not bound")
    first = result.rows[0]
    check(first.source_row == 2, "source row identity was lost")
    check(first.values[0] == "alpha"
          and first.values[1] == " shared text "
          and first.values[2] == "inline",
          "shared/inline strings were not decoded exactly")
    check(first.values[3] is True and type(first.values[3]) is bool,
          "actual Boolean typing was lost")
    check(first.values[4] == "#N/A", "error-looking ordinary text did not remain text")
    check(first.values[5] == Decimal("12345678901234567890.125"),
          "numeric lexical precision did not remain Decimal")
    check(first.values[6] == date(1900, 3, 1), "1900 date serial conversion failed")
    check(result.rows[1].values[6] == datetime(1900, 3, 1, 12),
          "fractional 1900 date serial conversion failed")
    check(result.rows[2].values[1:5] == (None, None, None, None)
          and result.rows[2].values[5] == Decimal(5)
          and result.rows[2].values[6] is None,
          "sparse coordinates did not project as explicit blanks")

    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(path, replace(main_spec(), sheet_name="data")),
            "no exact sheet")
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(path, replace(main_spec(), sheet_name="Missing")),
            "no exact sheet")


def test_1904_and_declared_dates(root):
    data = sheet_xml((
        row(1, (cell("A1", "When", kind="str"),)),
        row(2, (cell("A2", "0", style=1),)),
        row(3, (cell("A3", "0.5", style=1),)),
        row(4, (cell("A4", "2026-07-12T03:04:05", kind="d"),)),
    ))
    spec = stream.SheetSpec("Dates", (stream.ColumnSpec("When", stream.DATE),))
    path = write_xlsx(root / "dates1904.xlsx", (("Dates", data),), date1904=True)
    result = stream.read_sheet(path, spec)
    check(result.date_system == "1904"
          and result.rows[0].values == (date(1904, 1, 1),)
          and result.rows[1].values == (datetime(1904, 1, 1, 12),)
          and result.rows[2].values == (datetime(2026, 7, 12, 3, 4, 5),),
          "declared 1904/numeric/ISO dates were decoded incorrectly")

    bad = sheet_xml((row(1, (cell("A1", "When", kind="str"),)),
                     row(2, (cell("A2", "60", style=1),))))
    bad_path = write_xlsx(root / "fictional-date.xlsx", (("Dates", bad),))
    rejects(stream.XlsxSchemaError, lambda: stream.read_sheet(bad_path, spec),
            "1900-02-29")

    custom_path = write_xlsx(
        root / "custom-date.xlsx", (("Dates", data),), date1904=True,
        date_format_code="yyyy-mm-dd hh:mm:ss")
    check(stream.read_sheet(custom_path, spec).rows[0].values == (date(1904, 1, 1),),
          "custom date numFmt was not recognized")

    non_date_path = write_xlsx(
        root / "numeric-not-date.xlsx", (("Data", sheet_xml(primary_rows())),),
        shared=SHARED, date_format_code="0.000")
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(non_date_path, main_spec()),
            "lacks a recognized date/time style")

    unstyled_path = write_xlsx(
        root / "unstyled-date.xlsx",
        (("Data", sheet_xml(primary_rows(date_style=0))),), shared=SHARED)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(unstyled_path, main_spec()),
            "lacks a recognized date/time style")


def test_schema_and_formula_refusal(root):
    for label, rows, message in (
            ("duplicate", primary_rows(duplicate_header=True), "duplicate"),
            ("extra", primary_rows(extra_header=True), "schema/order"),
            ("reordered", primary_rows(reorder_header=True), "schema/order"),
            ("formula", primary_rows(formula=True), "formula is forbidden"),
            ("header-formula", primary_rows(header_formula=True), "formula is forbidden"),
            ("error", primary_rows(error_cell=True), "error is forbidden")):
        path = write_xlsx(root / f"{label}.xlsx", (("Data", sheet_xml(rows)),),
                          shared=SHARED)
        rejects(stream.XlsxSchemaError, lambda p=path: stream.read_sheet(p, main_spec()),
                message)

    missing_shared = tuple(value for value in SHARED if value != "When")
    missing_rows = list(primary_rows())
    # M1 points at an out-of-range shared string instead of the required header.
    path = write_xlsx(root / "missing.xlsx", (("Data", sheet_xml(missing_rows)),),
                      shared=missing_shared)
    rejects(stream.XlsxSchemaError, lambda: stream.read_sheet(path, main_spec()),
            "missing required headers")

    # Non-exact mode admits extra headers but still requires every declared header.
    extra_path = write_xlsx(root / "extra-allowed.xlsx",
                            (("Data", sheet_xml(primary_rows(extra_header=True))),),
                            shared=SHARED)
    allowed = stream.read_sheet(extra_path, main_spec(exact=False))
    check(len(allowed.rows) == 3, "non-exact schema did not admit an extra header")

    for label, rows in (
            ("empty-header-data", primary_rows(hidden_data=True)),
            ("trailing-data", primary_rows(trailing_data=True))):
        hidden_path = write_xlsx(
            root / f"{label}.xlsx", (("Data", sheet_xml(rows)),), shared=SHARED)
        rejects(stream.XlsxSchemaError,
                lambda p=hidden_path: stream.read_sheet(p, main_spec()),
                "beneath an empty or undeclared header")
        check(len(stream.read_sheet(hidden_path, main_spec(exact=False)).rows) == 3,
              "non-exact projection should ignore intentionally undeclared cells")


def test_encoding_and_namespace_guards(root):
    data = sheet_xml(primary_rows())
    sheets = (("Data", data),)
    normal_workbook = workbook_xml(("Data",))

    utf8_decl = ('<?xml version="1.0" encoding="UTF-8"?>' + normal_workbook)
    utf8_path = write_xlsx(root / "utf8-declared.xlsx", sheets, shared=SHARED,
                           workbook_payload=utf8_decl)
    check(len(stream.read_sheet(utf8_path, main_spec()).rows) == 3,
          "ordinary Office-compatible UTF-8 XML declaration was rejected")

    utf16_path = write_xlsx(root / "utf16.xlsx", sheets, shared=SHARED,
                            workbook_payload=normal_workbook.encode("utf-16"))
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(utf16_path, main_spec()), "only UTF-8")
    latin_path = write_xlsx(
        root / "latin-declared.xlsx", sheets, shared=SHARED,
        workbook_payload=('<?xml version="1.0" encoding="ISO-8859-1"?>'
                          + normal_workbook))
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(latin_path, main_spec()), "only UTF-8")

    wrong_root = normal_workbook.replace(f'xmlns="{NS}"', 'xmlns="urn:evil"', 1)
    wrong_root_path = write_xlsx(
        root / "wrong-workbook-ns.xlsx", sheets, shared=SHARED,
        workbook_payload=wrong_root)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_root_path, main_spec()), "namespace")

    spoofed_sheet = normal_workbook.replace(
        '<sheet name=', '<evil:sheet xmlns:evil="urn:evil" name=', 1)
    spoofed_sheet_path = write_xlsx(
        root / "spoofed-sheet-element.xlsx", sheets, shared=SHARED,
        workbook_payload=spoofed_sheet)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(spoofed_sheet_path, main_spec()), "wrong namespace")

    wrong_office_rel = normal_workbook.replace(
        f'xmlns:r="{REL}"', 'xmlns:r="urn:evil"', 1)
    wrong_office_path = write_xlsx(
        root / "wrong-office-rel-ns.xlsx", sheets, shared=SHARED,
        workbook_payload=wrong_office_rel)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_office_path, main_spec()), "wrong namespace")

    wrong_package_rel = rels_xml(1).replace(
        f'xmlns="{PKG_REL}"', 'xmlns="urn:evil"', 1)
    wrong_package_path = write_xlsx(
        root / "wrong-package-rel-ns.xlsx", sheets, shared=SHARED,
        rels_payload=wrong_package_rel)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_package_path, main_spec()), "namespace")

    wrong_sheet_root = data.replace(f'xmlns="{NS}"', 'xmlns="urn:evil"', 1)
    wrong_sheet_path = write_xlsx(
        root / "wrong-worksheet-ns.xlsx", (("Data", wrong_sheet_root),), shared=SHARED)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_sheet_path, main_spec()), "namespace")

    wrong_shared = shared_xml(SHARED).replace(
        f'xmlns="{NS}"', 'xmlns="urn:evil"', 1)
    wrong_shared_path = write_xlsx(
        root / "wrong-shared-ns.xlsx", sheets, shared_payload=wrong_shared)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_shared_path, main_spec()), "namespace")

    wrong_styles = styles_xml().replace(f'xmlns="{NS}"', 'xmlns="urn:evil"', 1)
    wrong_styles_path = write_xlsx(
        root / "wrong-styles-ns.xlsx", sheets, shared=SHARED,
        styles_payload=wrong_styles)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(wrong_styles_path, main_spec()), "namespace")


def test_zip_xml_limits_and_identity(root):
    path = write_xlsx(root / "limits.xlsx", (("Data", sheet_xml(primary_rows())),),
                      shared=SHARED)
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_archive_members=2)),
            "too many members")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_member_uncompressed=64)),
            "uncompressed-size")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_total_uncompressed=100)),
            "total uncompressed-size")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_compression_ratio=1)),
            "compression-ratio")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_xml_depth=2)),
            "nesting-depth")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_xml_events=10)),
            "event limit")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(path, main_spec(),
                                      limits=stream.XlsxLimits(max_shared_strings=2)),
            "shared-string")

    dtd_path = write_xlsx(
        root / "doctype.xlsx", (("Data", sheet_xml(primary_rows())),), shared=SHARED,
        workbook_preamble='<!DOCTYPE workbook [<!ENTITY x "boom">]>')
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(dtd_path, main_spec()), "forbidden")

    duplicate = root / "duplicate-member.xlsx"
    # zipfile emits a warning for this deliberately malformed fixture; suppressing it
    # is unnecessary for correctness, but construct it manually in a warnings context.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        write_xlsx(duplicate, (("Data", sheet_xml(primary_rows())),), shared=SHARED,
                   duplicate_member="xl/workbook.xml")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(duplicate, main_spec()), "duplicate member")

    case_collision = root / "case-colliding-member.xlsx"
    write_xlsx(case_collision, (("Data", sheet_xml(primary_rows())),), shared=SHARED,
               duplicate_member="XL/WORKBOOK.XML")
    rejects(stream.XlsxSecurityError,
            lambda: stream.read_sheet(case_collision, main_spec()), "case-colliding")

    duplicate_sheet = write_xlsx(
        root / "duplicate-sheet.xlsx",
        (("Data", sheet_xml(primary_rows())),
         ("Data", sheet_xml(primary_rows()))), shared=SHARED)
    rejects(stream.XlsxSchemaError,
            lambda: stream.read_sheet(duplicate_sheet, main_spec()),
            "duplicate sheets")

    real_zip = stream.zipfile.ZipFile
    zip_sources = []

    def recording_zip(source, *args, **kwargs):
        zip_sources.append(source)
        return real_zip(source, *args, **kwargs)

    with patch.object(stream.zipfile, "ZipFile", side_effect=recording_zip):
        stream.read_sheet(path, main_spec())
    check(len(zip_sources) == 1 and isinstance(zip_sources[0], stream.io.BytesIO),
          "ZipFile did not parse a private immutable byte capture")

    actual = path.lstat()
    drifted = fake_stat(actual, st_ino=actual.st_ino + 1)
    with patch.object(stream, "_path_lstat", side_effect=(actual, actual, drifted)):
        rejects(stream.XlsxMutationError,
                lambda: stream.read_sheet(path, main_spec()), "no longer names")

    link_stat = fake_stat(actual, st_mode=stat.S_IFLNK | 0o777)
    with patch.object(stream, "_path_lstat", return_value=link_stat):
        rejects(stream.XlsxSecurityError,
                lambda: stream.read_sheet(path, main_spec()), "symbolic link")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    reparse_stat = fake_stat(actual, st_file_attributes=reparse_flag)
    with patch.object(stream, "_path_lstat", return_value=reparse_stat):
        rejects(stream.XlsxSecurityError,
                lambda: stream.read_sheet(path, main_spec()), "reparse point")


def test_same_object_a_to_b_to_a_interposition(root):
    rows_a = sheet_xml(primary_rows())
    rows_b = rows_a.replace("alpha", "omega")
    path = write_xlsx(
        root / "interposition.xlsx", (("Data", rows_a),), shared=SHARED,
        compression=zipfile.ZIP_STORED)
    other = write_xlsx(
        root / "interposition-b.xlsx", (("Data", rows_b),), shared=SHARED,
        compression=zipfile.ZIP_STORED)
    bytes_a = path.read_bytes()
    bytes_b = other.read_bytes()
    check(len(bytes_a) == len(bytes_b) and bytes_a != bytes_b,
          "interposition fixtures are not distinct equal-size workbooks")
    original_stat = path.stat()
    real_copy = stream._copy_bound_handle

    def replace_same_object(payload):
        with path.open("r+b") as mutable:
            mutable.seek(0)
            mutable.write(payload)
            mutable.truncate()
            mutable.flush()
        Path(path).touch()
        import os
        os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    def capture_b_then_restore_a(handle, bound, *, chunk_size, max_bytes):
        replace_same_object(bytes_b)
        captured = real_copy(
            handle, bound, chunk_size=chunk_size, max_bytes=max_bytes)
        replace_same_object(bytes_a)
        return captured

    with patch.object(stream, "_copy_bound_handle", side_effect=capture_b_then_restore_a):
        rejects(stream.XlsxMutationError,
                lambda: stream.read_sheet(path, main_spec()), "private capture")
    check(path.read_bytes() == bytes_a,
          "A-to-B-to-A capture fixture did not restore the source")

    real_stream = stream._stream_worksheet

    def mutate_live_during_private_parse(*args, **kwargs):
        replace_same_object(bytes_b)
        try:
            return real_stream(*args, **kwargs)
        finally:
            replace_same_object(bytes_a)

    with patch.object(stream, "_stream_worksheet",
                      side_effect=mutate_live_during_private_parse):
        result = stream.read_sheet(path, main_spec())
    check(result.rows[0].values[0] == "alpha"
          and result.pre_identity.sha256 == result.post_identity.sha256,
          "live A-to-B-to-A mutation changed rows parsed from the private capture")


def main():
    test_forbidden_imports()
    with tempfile.TemporaryDirectory(prefix="phase3_xlsx_stream_") as raw:
        root = Path(raw)
        test_types_sparse_dates_and_sheet_resolution(root)
        test_1904_and_declared_dates(root)
        test_schema_and_formula_refusal(root)
        test_encoding_and_namespace_guards(root)
        test_zip_xml_limits_and_identity(root)
        test_same_object_a_to_b_to_a_interposition(root)
    print("OK  Phase-3 stdlib XLSX stream: exact sheets/schema, typed sparse cells, "
          "declared dates, formula/error refusal, archive/XML limits, immutable private "
          "capture with A-to-B-to-A rejection, and forbidden production/third-party imports")


if __name__ == "__main__":
    main()

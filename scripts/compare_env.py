"""Cross-environment comparison: the same report exported from two different
data source / environment combinations (e.g. SSOR-prod vs ARS-prod, or
SSOR-prod today vs SSOR-prod last month), compared cell-for-cell.

Inputs are two RUN FOLDERS (output/<YYYY-MM-DD src-env>/ — or a report
subfolder picked directly). No consolidation step is needed first: the
per-route files of the chosen report are read straight from both folders
and merged in memory exactly the way the consolidators would (Route column
prepended, header locked from the first readable file), then handed to the
proven compare_core engine — so the output is the same approved discrepancy
workbook the TSMIS-vs-TSN comparison produces, with the environment names
("SSOR-PROD", "ARS-DEV", …) as the two sides.

One adapter per report type (REPORTS / the per-report constants below):
  * Ramp Detail / Highway Sequence / Highway Log — per-route XLSX exports,
    compared in the consolidated shape (Route + the report's own columns;
    the column layout is locked from the files and must match between the
    two folders). Highway Log keeps its Med Wid zero-pad normalization.
  * Ramp Summary — per-route PDFs, parsed with the consolidator's own parser
    (consolidate_ramp_summary.parse_pdf) into one row per route, compared
    route-by-route (the route is the row key).

Console-free, same contract as the other comparison modules: progress via
events.on_log, overwrite via confirm_overwrite, cancel honored per file and
inside the engine, ConsolidateResult returned. The GUI's Compare tab drives
this through the COMPARE_REPORTS registry ("folders" input kind).
"""
import logging
import re
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

try:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
    _XLSX_OK = True
except ImportError:
    _XLSX_OK = False

# Route-key normalizer: the Ramp Summary route can come from the PDF title
# (unpadded, "1") or the filename ("001"); zero-pad the numeric part so the two
# sides key consistently and a route doesn't split into two one-sided rows.
_ROUTE_KEY_RE = re.compile(r"^(\d+)(\w*)$")


def _norm_route_key(token):
    m = _ROUTE_KEY_RE.match(str(token).strip())
    return m.group(1).zfill(3) + m.group(2).upper() if m else str(token).strip().upper()

import compare_highway_log as _hl
import consolidate_intersection_summary as _is
import consolidate_ramp_summary as _rs
from compare_core import CompareSchema, normalize_value, run_compare
from events import ConsolidateResult, Events
from paths import OUTPUT_ROOT, parse_run_folder, today_str

log = logging.getLogger("tsmis.compare")

# Pull the route token out of "<prefix>_route_<ROUTE>.<ext>" (same rule as
# consolidate_xlsx_base, extended to PDFs for the Ramp Summary).
_ROUTE_FROM_NAME = re.compile(r"_route_(\w+)\.(?:xlsx|pdf)$", re.IGNORECASE)


def _route_from_name(path):
    m = _ROUTE_FROM_NAME.search(path.name)
    return m.group(1).upper() if m else path.stem


def side_label(folder):
    """A short side name for one input folder, used as that side's sheet/tab
    name and in every label: run folders become "SSOR-PROD" style; anything
    else falls back to a sanitized folder name."""
    folder = Path(folder)
    parsed = parse_run_folder(folder.name)
    if parsed is None and folder.parent != folder:
        parsed = parse_run_folder(folder.parent.name)   # report subdir picked
    if parsed:
        _day, src, env = parsed
        return f"{src}-{env}".upper()
    clean = re.sub(r"[\[\]\*\?:/\\']+", " ", folder.name).strip()
    return (clean or "FOLDER")[:20]


# Excel caps sheet names at 31 chars; the longest sheet we derive from a side
# label is "Only in <label>" (8 + label), so a side label must fit in 23.
_SIDE_LABEL_CAP = 31 - len("Only in ")          # = 23


def _cap_label(s, limit=_SIDE_LABEL_CAP):
    """Cap a derived side label to `limit` chars WITHOUT dropping its trailing
    distinguisher. The labels built below end in the part that keeps two
    same-source sides apart -- a run date (" 2026-06-11") or an " (A)"/" (B)"
    suffix. A plain end-truncation (s[:limit]) would cut exactly that, collapsing
    two distinct sides into the same prefix (then the A/B fallback fires and the
    real provenance is lost). Trim the BASE and keep the suffix instead."""
    if len(s) <= limit:
        return s
    m = re.search(r"(?: \d{4}-\d{2}-\d{2}| \([AB]\))$", s)
    if not m:
        return s[:limit]
    suffix = m.group(0)
    keep = max(0, limit - len(suffix))
    return (s[:m.start()][:keep] + suffix)[:limit]


def _side_labels(dir_a, dir_b):
    """Distinct side names for the two folders. Same src-env on both sides
    (e.g. prod today vs prod last month) gets the run date appended; still
    identical falls back to A/B suffixes (sheet names must differ)."""
    la, lb = side_label(dir_a), side_label(dir_b)
    if la == lb:
        for folder, label in ((dir_a, la), (dir_b, lb)):
            parsed = parse_run_folder(Path(folder).name) \
                or parse_run_folder(Path(folder).parent.name)
            if parsed:
                day = parsed[0]
                if folder is dir_a:
                    la = f"{label} {day}"
                else:
                    lb = f"{label} {day}"
    if la == lb:
        la, lb = f"{la} (A)", f"{lb} (B)"
    # Cap so the longest derived sheet name ("Only in <label>", 8 + label) fits
    # Excel's 31-char limit. _cap_label trims the BASE, not the trailing
    # distinguisher (run date / (A)/(B)), so two same-source sides stay distinct
    # under the cap; fall back to Side A/B only if they still collide.
    la, lb = _cap_label(la), _cap_label(lb)
    if la == lb:
        la, lb = "Side A", "Side B"
    return la, lb


def _find_input_dir(base, subdir, pattern):
    """The folder actually holding the report files: <base>/<subdir> when the
    user picked a run folder, else <base> itself (they browsed straight to a
    report folder). Returns (dir, files) — files possibly empty."""
    base = Path(base)
    for candidate in (base / subdir, base):
        files = sorted(candidate.glob(pattern)) if candidate.is_dir() else []
        if files:
            return candidate, files
    return base / subdir, []


# ---------------------------------------------------------------------------
# Input loaders
# ---------------------------------------------------------------------------

def _load_xlsx_side(folder, label, subdir, sheet_name, report_name, events,
                    expected_header=None):
    """Read every per-route XLSX under one side into consolidated-shape rows
    ([route, *row]) the way the consolidators do: the header is locked from
    the first readable file (or must equal `expected_header` when the report
    pins one); files that disagree are skipped LOUDLY. Returns
    (rows, header, skipped) — `skipped` is the list of "<side> <file>: <reason>"
    strings that the caller folds into the comparison's incompleteness warning,
    so a route unreadable on a side can never masquerade as a clean match.
    Raises ValueError with a user-safe message when nothing is readable."""
    in_dir, files = _find_input_dir(folder, subdir, "*.xlsx")
    if not files:
        raise ValueError(
            f"No {report_name} files were found for the {label} side:\n{in_dir}\n\n"
            f"Export the {report_name} report on that environment first.")
    header = list(expected_header) if expected_header else None
    rows = []
    skipped = []
    for i, p in enumerate(files, 1):
        if events.is_cancelled():
            raise ValueError("Cancelled by user.")
        try:
            wb = load_workbook(p, read_only=True, data_only=True)
        except Exception as e:
            events.on_log(f"  [{label}] {p.name}: could not open "
                          f"({type(e).__name__}); skipping")
            skipped.append(f"{label} {p.name}: could not open "
                           f"({type(e).__name__})")
            continue
        try:
            if sheet_name not in wb.sheetnames:
                events.on_log(f"  [{label}] {p.name}: sheet '{sheet_name}' "
                              "missing; skipping")
                skipped.append(f"{label} {p.name}: sheet '{sheet_name}' missing")
                continue
            rows_iter = wb[sheet_name].iter_rows(values_only=True)
            h = [v for v in next(rows_iter, [])]
            while h and h[-1] in (None, ""):
                h.pop()
            # Give INTERNAL unnamed columns a stable, identifiable label (the
            # Highway Sequence export has real but header-less columns) so they
            # don't show as blank fields in the Summary/Comparison. Positional,
            # so it's consistent across files (the h != header check still holds).
            h = [v if (v is not None and str(v).strip() != "")
                 else f"(col {get_column_letter(i + 1)})" for i, v in enumerate(h)]
            if header is None:
                header = h
            if h != header:
                events.on_log(f"  [{label}] {p.name}: column layout differs; "
                              "skipping")
                skipped.append(f"{label} {p.name}: column layout differs from "
                               "the other files")
                continue
            route = _route_from_name(p)
            n = len(header)
            count = 0
            for r in rows_iter:
                r = list(r)[:n] + [None] * max(0, n - len(r))
                if any(v is not None and str(v).strip() != "" for v in r):
                    rows.append([route] + [normalize_value(v) for v in r])
                    count += 1
            events.on_log(f"  [{label}] [{i:>3}/{len(files)}] {p.name} "
                          f"+{count} rows")
        finally:
            wb.close()
    if not rows:
        raise ValueError(
            f"No readable {report_name} files were found for the {label} "
            f"side in:\n{in_dir}")
    if skipped:
        events.on_log(f"  [{label}] note: {len(skipped)} file(s) skipped "
                      "(details above).")
    return rows, header, skipped


# The Ramp Summary's comparison columns: the consolidator's own field order
# and display labels (Source + the formula-only Audit columns excluded — the
# comparison recomputes everything itself).
_RS_FIELDS = [(col, disp) for group, cols in _rs.GROUPS
              for col, disp in cols
              if group not in ("Source", "Audit")]
RS_HEADER = ["Route"] + [disp for _col, disp in _RS_FIELDS]


def _load_ramp_summary_side(folder, label, events):
    """Parse every per-route Ramp Summary PDF on one side into per-route-shape
    rows ([route, *numeric fields] — the route IS the row key). Slow-ish
    (~1-2 s per PDF), so progress is logged per file and cancel is honored.
    Returns (rows, skipped) — `skipped` lists the PDFs that wouldn't parse, so
    the caller can flag the comparison as incomplete rather than silently
    dropping a route."""
    in_dir, files = _find_input_dir(folder, "ramp_summary", "*.pdf")
    if not files:
        raise ValueError(
            f"No Ramp Summary PDFs were found for the {label} side:\n{in_dir}\n\n"
            "Export the Ramp Summary report on that environment first.")
    rows = []
    skipped = []
    for i, p in enumerate(files, 1):
        if events.is_cancelled():
            raise ValueError("Cancelled by user.")
        try:
            record = _rs.parse_pdf(p)
        except Exception as e:
            events.on_log(f"  [{label}] {p.name}: could not parse "
                          f"({type(e).__name__}); skipping")
            log.warning("env compare: %s parse failed", p, exc_info=True)
            skipped.append(f"{label} {p.name}: could not parse "
                           f"({type(e).__name__})")
            continue
        if not _rs.record_has_data(record):
            # One-page / truncated PDF: a route but no ramp figures. Skip it
            # (an all-blank route would otherwise compare as a phantom match).
            events.on_log(f"  [{label}] {p.name}: no ramp data "
                          "(one-page / truncated PDF?); skipping")
            skipped.append(f"{label} {p.name}: no ramp data "
                           "(one-page / truncated PDF?)")
            continue
        route = _norm_route_key(record.get("route") or _route_from_name(p))
        rows.append([route] + [record.get(col) for col, _disp in _RS_FIELDS])
        events.on_log(f"  [{label}] [{i:>3}/{len(files)}] {p.name} "
                      f"(route {route})")
    if not rows:
        raise ValueError(
            f"No readable Ramp Summary PDFs were found for the {label} side "
            f"in:\n{in_dir}")
    if skipped:
        events.on_log(f"  [{label}] note: {len(skipped)} PDF(s) skipped "
                      "(details above).")
    return rows, skipped


# Intersection Summary's comparison columns: Total + one column per canonical
# category (the consolidator's category key as the header), in spec order.
_IS_FIELDS = [(c.slug, c.key) for c in _is._CATS]
IS_HEADER = ["Route", "Total Intersections"] + [key for _slug, key in _IS_FIELDS]


def _load_intersection_summary_side(folder, label, events):
    """Parse every per-route Intersection Summary XLSX on one side into per-route-
    shape rows ([route, total, *category counts] — the route IS the row key), reusing
    the consolidator's own block-walk parser (consolidate_intersection_summary
    .parse_route) so the two sides can't drift from each other or the consolidation.
    Returns (rows, skipped); raises ValueError when nothing is readable."""
    in_dir, files = _find_input_dir(folder, "intersection_summary", "*.xlsx")
    files = [p for p in files if not p.name.startswith("~$")]
    if not files:
        raise ValueError(
            f"No Intersection Summary files were found for the {label} side:\n{in_dir}"
            "\n\nExport the Intersection Summary report on that environment first.")
    rows, skipped = [], []
    for i, p in enumerate(files, 1):
        if events.is_cancelled():
            raise ValueError("Cancelled by user.")
        try:
            route, counts, total = _is.parse_route(str(p))
        except Exception as e:
            events.on_log(f"  [{label}] {p.name}: could not parse "
                          f"({type(e).__name__}); skipping")
            log.warning("env compare: %s parse failed", p, exc_info=True)
            skipped.append(f"{label} {p.name}: could not parse ({type(e).__name__})")
            continue
        if not _is.record_has_data({"counts": counts}):
            events.on_log(f"  [{label}] {p.name}: no intersection data; skipping")
            skipped.append(f"{label} {p.name}: no intersection data")
            continue
        rkey = _norm_route_key(route)
        rows.append([rkey, total] + [counts.get(slug, 0) for slug, _k in _IS_FIELDS])
        events.on_log(f"  [{label}] [{i:>3}/{len(files)}] {p.name} (route {rkey})")
    if not rows:
        raise ValueError(
            f"No readable Intersection Summary files were found for the {label} "
            f"side in:\n{in_dir}")
    if skipped:
        events.on_log(f"  [{label}] note: {len(skipped)} file(s) skipped (details above).")
    return rows, skipped


def _load_highway_log_pdf_side(folder, label, events):
    """Parse one side's Highway Log PDFs (folder/highway_log_pdf/*.pdf) into
    consolidated-shape 31-column rows: convert them to per-route XLSX with the HL-PDF
    consolidator's own parser in a temp dir, then read those flat like any XLSX side.
    Returns (rows, header, skipped). The PDF is the ACCURATE Highway Log source (the
    vendor Excel drops rows), so this is the preferred cross-env Highway Log."""
    import consolidate_tsmis_highway_log_pdf as _hlpdf
    import highway_log_columns as hlc
    in_dir, pdfs = _find_input_dir(folder, _hlpdf.SUBDIR, "*.pdf")
    if not pdfs:
        raise ValueError(
            f"No Highway Log (PDF) files were found for the {label} side:\n{in_dir}"
            "\n\nExport the Highway Log (PDF) report on that environment first.")
    conv = Path(tempfile.mkdtemp(prefix="hlpdf_env_conv_"))
    combined_dir = Path(tempfile.mkdtemp(prefix="hlpdf_env_out_"))
    try:
        res = _hlpdf.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                 input_dir=in_dir, out_path=combined_dir / "_combined.xlsx",
                                 converted_dir=conv)
        if res.status == "cancelled":
            raise ValueError("Cancelled by user.")
        if res.status != "ok":
            raise ValueError(res.message or "Could not parse the Highway Log PDFs.")
        # The per-route XLSX now sit in `conv` (the combined file is in combined_dir,
        # excluded). Read them flat with the corrected 31-column header pinned.
        return _load_xlsx_side(conv, label, "_perroute_", _hlpdf.SHEET_NAME,
                               "Highway Log (PDF)", events, expected_header=hlc.HEADER)
    finally:
        shutil.rmtree(conv, ignore_errors=True)
        shutil.rmtree(combined_dir, ignore_errors=True)


def _load_intersection_detail_pdf_side(folder, label, events):
    """Parse one side's Intersection Detail PDFs (folder/intersection_detail_pdf/*.pdf)
    into consolidated-shape 36-column rows: convert them to per-route XLSX with the
    Int-Detail-PDF consolidator's own parser in a temp dir, then read those flat like
    any XLSX side. Returns (rows, header, skipped). The exact parallel of
    _load_highway_log_pdf_side — both PDF sides are parsed offline the same way the
    PDF-vs-TSN comparison parses them, so the cross-env comparison is consistent."""
    import consolidate_tsmis_intersection_detail_pdf as _idpdf
    import intersection_detail_columns as idc
    in_dir, pdfs = _find_input_dir(folder, _idpdf.SUBDIR, "*.pdf")
    if not pdfs:
        raise ValueError(
            f"No Intersection Detail (PDF) files were found for the {label} side:\n{in_dir}"
            "\n\nExport the Intersection Detail (PDF) report on that environment first.")
    conv = Path(tempfile.mkdtemp(prefix="idpdf_env_conv_"))
    combined_dir = Path(tempfile.mkdtemp(prefix="idpdf_env_out_"))
    try:
        res = _idpdf.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                 input_dir=in_dir, out_path=combined_dir / "_combined.xlsx",
                                 converted_dir=conv)
        if res.status == "cancelled":
            raise ValueError("Cancelled by user.")
        if res.status != "ok":
            raise ValueError(res.message or "Could not parse the Intersection Detail PDFs.")
        # The per-route XLSX now sit in `conv` (the combined file is in combined_dir,
        # excluded). Read them flat with the 36-column Intersection Detail header pinned.
        return _load_xlsx_side(conv, label, "_perroute_", _idpdf.SHEET_NAME,
                               "Intersection Detail (PDF)", events, expected_header=idc.HEADER)
    finally:
        shutil.rmtree(conv, ignore_errors=True)
        shutil.rmtree(combined_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Per-report adapters
# ---------------------------------------------------------------------------

class EnvCompare:
    """One report type's cross-environment comparison (a COMPARE_REPORTS
    "folders" entry): compare_folders(dir_a, dir_b, out_path, …) +
    suggest_name(dir_a, dir_b)."""

    def __init__(self, key, report_name, subdir, sheet_name=None,
                 expected_header=None, base_schema=None, key_col=None,
                 force_header=None, side_loader=None, agg_header=None,
                 flat_pdf_loader=None):
        self.key = key                        # "ramp_summary" | "ramp_detail" | …
        self.REPORT_NAME = report_name
        self.subdir = subdir
        self.sheet_name = sheet_name          # None = an aggregate (PDF/category) path
        self.expected_header = expected_header
        # Aggregate-per-route path: a custom (folder,label,events)->(rows,skipped)
        # loader that yields ONE [route, *fields] row per route (route is the key,
        # has_route=False), with `agg_header` as the schema header. Used by the
        # category-summary reports (Intersection Summary) whose per-route sheet
        # isn't a flat header+rows table. (Ramp Summary keeps its own PDF path.)
        self.side_loader = side_loader
        self.agg_header = agg_header
        # Flat path (has_route=True) whose source is PDFs, not XLSX: a
        # (folder,label,events)->(rows,header,skipped) loader used instead of
        # _load_xlsx_side. Highway Log (PDF) uses it to parse each side's PDFs.
        self.flat_pdf_loader = flat_pdf_loader
        self.base_schema = base_schema        # report-specific schema extras
        # When set, the DISPLAY header is forced to this (the loaded files are
        # accepted as-is and compared by POSITION). Highway Log uses it so the
        # vendor-mislabeled Excel exports still compare but show CORRECTED labels.
        self.force_header = force_header
        # The column NAME to key rows on, when the report's FIRST column is too
        # coarse to identify a row (e.g. Highway Sequence / Ramp Detail lead
        # with County / a district-county-route Location that repeats for
        # hundreds of rows; the postmile "PM" column is the real identity).
        # Resolved to a header index per loaded layout; falls back to the first
        # column (the original behavior) when the named column isn't present.
        self.key_col = key_col

    def suggest_name(self, dir_a, dir_b):
        la, lb = _side_labels(Path(dir_a), Path(dir_b))
        safe = lambda s: re.sub(r"[^\w\-]+", "_", s).strip("_")
        # The generated-on date (A1): the side labels already carry each side's
        # export date + src-env, so this stamps WHEN the comparison was built.
        return (f"{safe(la)}_vs_{safe(lb)}_"
                f"{safe(self.REPORT_NAME)}_Comparison {today_str()}.xlsx")

    def _resolve_key_field(self, header):
        """Index of the configured key column in this loaded header, matched on
        the stripped name; 0 (the first column) when none is configured or the
        name isn't present (so layout drift degrades to the old behavior rather
        than crashing)."""
        if not self.key_col:
            return 0
        want = self.key_col.strip().casefold()
        for i, name in enumerate(header):
            if name is not None and str(name).strip().casefold() == want:
                return i
        log.warning("env compare %s: key column %r not found in header %r; "
                    "falling back to the first column", self.key, self.key_col,
                    header)
        return 0

    def _schema(self, header, la, lb):
        # Force the corrected display header when configured (Highway Log); the
        # data is positional, so relabeling for display can't shift columns.
        if self.force_header is not None and len(self.force_header) == len(header):
            header = list(self.force_header)
        base = self.base_schema or CompareSchema(
            report_name=self.REPORT_NAME, header=header,
            id_noun="row", id_noun_plural="rows")
        widths = dict(base.data_widths) or {header[0]: 12}
        if "Description" in header and "Description" not in widths:
            widths["Description"] = 26
        cmp_widths = dict(base.cmp_widths)
        if "Description" in header and "Description" not in cmp_widths:
            cmp_widths["Description"] = 30
        return replace(base, header=header, side_a=la, side_b=lb,
                       sides_noun="environments",
                       data_widths=widths, cmp_widths=cmp_widths,
                       key_field=self._resolve_key_field(header),
                       one_sided_note_extra="", trim_note_extra="")

    def compare_folders(self, dir_a, dir_b, out_path, events=None,
                        confirm_overwrite=None, mode="formulas"):
        """Compare the report's per-route files in run folder `dir_a` against
        `dir_b` and write the discrepancy workbook(s) to `out_path`. Returns
        a ConsolidateResult (same contract as the consolidators)."""
        events = events or Events()
        if not _XLSX_OK:
            return ConsolidateResult(
                status="error",
                message="Required components are missing (openpyxl).")
        if (self.sheet_name is None and self.side_loader is None
                and not getattr(_rs, "_DEPS_OK", False)):
            return ConsolidateResult(
                status="error",
                message="Required components are missing (pdfplumber).")
        dir_a, dir_b = Path(dir_a), Path(dir_b)
        for side, d in (("first", dir_a), ("second", dir_b)):
            if not d.is_dir():
                return ConsolidateResult(
                    status="error",
                    message=f"The {side} folder doesn't exist:\n{d}")
        if dir_a.resolve() == dir_b.resolve():
            return ConsolidateResult(
                status="error",
                message="Pick two DIFFERENT folders — both sides point at "
                        f"the same one:\n{dir_a}")
        la, lb = _side_labels(dir_a, dir_b)

        events.on_log("=" * 60)
        events.on_log(f"{self.REPORT_NAME} Comparison — {la} vs {lb}")
        events.on_log("=" * 60)
        events.on_log(f"{la}: {dir_a}")
        events.on_log(f"{lb}: {dir_b}")
        events.on_log("")

        try:
            if self.side_loader is not None:  # aggregate per-route XLSX (Intersection Summary)
                rows_a, skip_a = self.side_loader(dir_a, la, events)
                rows_b, skip_b = self.side_loader(dir_b, lb, events)
                header, has_route = self.agg_header, False
            elif self.sheet_name is None:     # Ramp Summary: PDFs, route-keyed
                rows_a, skip_a = _load_ramp_summary_side(dir_a, la, events)
                rows_b, skip_b = _load_ramp_summary_side(dir_b, lb, events)
                header, has_route = RS_HEADER, False
            else:                             # flat (has_route=True): XLSX, or PDF-sourced
                def _flat_load(d, lab):
                    if self.flat_pdf_loader is not None:
                        return self.flat_pdf_loader(d, lab, events)
                    return _load_xlsx_side(d, lab, self.subdir, self.sheet_name,
                                           self.REPORT_NAME, events,
                                           expected_header=self.expected_header)
                rows_a, header, skip_a = _flat_load(dir_a, la)
                rows_b, header_b, skip_b = _flat_load(dir_b, lb)
                if header != header_b:
                    return ConsolidateResult(
                        status="error",
                        message=(f"The two folders' {self.REPORT_NAME} files "
                                 "have different column layouts — compare "
                                 "exports made by the same app version."))
                # rows are consolidated-shape ([route, *row]); the schema
                # header stays the per-route column list (the engine adds
                # the Route column itself in the has_route layout).
                has_route = True
        except ValueError as e:
            msg = str(e)
            status = "cancelled" if msg == "Cancelled by user." else "error"
            return ConsolidateResult(status=status, message=msg)

        # Files unreadable on EITHER side make the comparison incomplete — pass
        # them through so the verdict can't certify a clean match and the
        # workbook + summary list exactly what was left out.
        warnings = skip_a + skip_b
        if warnings:
            events.on_log(f"⚠ {len(warnings)} input file(s) skipped across both "
                          "sides — the comparison will be flagged incomplete.")

        events.on_log("")
        sc = self._schema(header, la, lb)
        return run_compare(sc, rows_a, rows_b, has_route, out_path,
                           events=events, confirm_overwrite=confirm_overwrite,
                           mode=mode, name_a=str(dir_a.name), name_b=str(dir_b.name),
                           warnings=warnings)


# Highway Log: keep the Med Wid rule, the sample's widths, and the column
# tooltips + Legend (inherited from _hl._SCHEMA); the other XLSX reports lock
# their layout from the files. The vendor Excel exports carry the OLD mislabeled
# header, so the cross-env loader accepts the files as-is (lock from files) and
# force_header relabels the display to the CORRECTED header (positional).
# key_normalizer is cleared: cross-env compares two TSMIS exports (SAME roadbed
# encoding — both suffix the Location), so the roadbed-unifying key is unnecessary
# and would only perturb the validated cross-env output. It is a TSMIS-vs-TSN tool.
_HL_BASE = replace(_hl._SCHEMA, one_sided_note_extra="", trim_note_extra="",
                   key_normalizer=None)

RAMP_SUMMARY = EnvCompare(
    "ramp_summary", "Ramp Summary", "ramp_summary",
    base_schema=CompareSchema(
        report_name="Ramp Summary", header=RS_HEADER,
        id_noun="route", id_noun_plural="routes",
        scope_flat="All routes (one row per route)"))
RAMP_DETAIL = EnvCompare(
    "ramp_detail", "Ramp Detail", "ramp_detail", sheet_name="TSAR - Ramp Detail",
    key_col="PM")
HIGHWAY_SEQUENCE = EnvCompare(
    "highway_sequence", "Highway Sequence", "highway_sequence",
    sheet_name="Highway Locations", key_col="PM")
HIGHWAY_LOG = EnvCompare(
    "highway_log", "Highway Log", "highway_log", sheet_name=_hl.SHEET_NAME,
    base_schema=_HL_BASE, force_header=_hl.EXPECTED_HEADER)
# Intersection Summary: the per-route export is a CATEGORY-summary sheet (not a flat
# table), so it's compared the AGGREGATE way (one row of category counts per route,
# route-keyed) via the consolidator's own block-walk parser — the analog of Ramp
# Summary's PDF path, but XLSX.
INTERSECTION_SUMMARY = EnvCompare(
    "intersection_summary", "Intersection Summary", "intersection_summary",
    side_loader=_load_intersection_summary_side, agg_header=IS_HEADER,
    base_schema=CompareSchema(
        report_name="Intersection Summary", header=IS_HEADER,
        id_noun="route", id_noun_plural="routes",
        scope_flat="All routes (one row per route)"))
# Intersection Detail: a flat per-route XLSX (sheet "Intersection Detail"), keyed on
# the postmile, so it uses the standard flat path like Ramp Detail / Highway Sequence.
# (The export header is offset within each type/eff-date pair, but BOTH env sides share
# the identical layout, so the position-wise comparison is valid; intersections sharing
# a postmile pair by data similarity in compare_core. id_noun = intersection.)
INTERSECTION_DETAIL = EnvCompare(
    "intersection_detail", "Intersection Detail", "intersection_detail",
    sheet_name="Intersection Detail", key_col="Post Mile",
    base_schema=CompareSchema(
        report_name="Intersection Detail", header=["Post Mile"],
        id_noun="intersection", id_noun_plural="intersections", pair_noun="postmile"))
# Highway Log (PDF) cross-env: same Highway Log schema as the Excel row (Med Wid rule,
# corrected labels, ditto/roadbed), but BOTH sides are parsed from the app's own PDF
# export — the accurate Highway Log source (the vendor Excel drops rows), so this is
# the preferred cross-env Highway Log. flat_pdf_loader parses each side's PDFs first.
HIGHWAY_LOG_PDF = EnvCompare(
    "highway_log_pdf", "Highway Log (PDF)", "highway_log_pdf",
    sheet_name=_hl.SHEET_NAME, base_schema=_HL_BASE,
    force_header=_hl.EXPECTED_HEADER, flat_pdf_loader=_load_highway_log_pdf_side)
# Intersection Detail (PDF) cross-env: the same flat per-route shape as the Excel
# Intersection Detail row (sheet "Intersection Detail", keyed on Post Mile), but BOTH
# sides are parsed from the app's own PDF export — the exact parallel of HIGHWAY_LOG_PDF.
# No force_header: unlike the vendor-mislabeled Highway Log Excel, the Intersection
# Detail header is native, so the PDF and Excel sides already share the 36-col layout.
INTERSECTION_DETAIL_PDF = EnvCompare(
    "intersection_detail_pdf", "Intersection Detail (PDF)", "intersection_detail_pdf",
    sheet_name="Intersection Detail", key_col="Post Mile",
    base_schema=CompareSchema(
        report_name="Intersection Detail (PDF)", header=["Post Mile"],
        id_noun="intersection", id_noun_plural="intersections", pair_noun="postmile"),
    flat_pdf_loader=_load_intersection_detail_pdf_side)

# Default save location for cross-environment comparison workbooks (the GUI
# aims its save dialog here; "Delete all reports" clears it).
DEFAULT_OUT_DIR = OUTPUT_ROOT / "comparisons"

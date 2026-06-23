"""Canonical TSN library — the ONE fixed home the whole app references for each
report's TSN source data.

The six TSN reports essentially never change, so rather than scatter them across
per-run drop folders (the legacy ``input/tsn_highway_log/`` and the matrix's
``<dest>/_tsn_input/<subdir>/``), each report's TSN data lives under
``<DATA_ROOT>/tsn_library/<report>/``:

    raw/           the RAW TSN file(s) exactly as exported — district PDFs, a
                   statewide PDF, or a statewide XLSX (the format is the report's
                   own, see tsn-parsers.md).
    consolidated/  the GENERATED consolidated / normalized Excel, built once from
                   the raw and reused for every comparison. A couple of TSN
                   reports are PDFs, so this Excel is what the comparison engine
                   actually reads.

Every consolidator / comparator / matrix DEFAULTS to this library — the per-row
``tsn_subdir`` IS the report key here. An explicit user file-pick stays an
override (``resolve(report, selected_file=...)``). The legacy Highway Log
locations are honored as read-only fallbacks so existing installs keep working
until imported.

Console-free (no print / input / sys.exit): functions return dicts /
ConsolidateResult or raise. The report's own builder/consolidator imports are LAZY
(resolved inside build_consolidated). As of P4 this module imports `report_catalog`
to derive its descriptors, which (like the registry) transitively pulls openpyxl /
pdfplumber — so importing tsn_library is console-free but not dependency-light.
"""
import importlib
import shutil
from dataclasses import dataclass
from pathlib import Path

import consolidation_meta
import paths
import report_catalog as _catalog
from events import ConsolidateResult, Events


@dataclass(frozen=True)
class TsnReport:
    """One TSN report's library descriptor — the single place that knows its raw
    format and how to build its consolidated/normalized Excel."""
    subdir: str            # report key == the matrix's per-row tsn_subdir token
    label: str             # human label for the Settings status panel
    raw_glob: str          # "*.pdf" | "*.xlsx" — what counts as a raw file
    raw_kind: str          # "district_pdfs" | "statewide_pdf" | "statewide_xlsx"
    consolidated_name: str # filename written into consolidated/
    builder: str           # "module:function"; func(raw_dir, out_path, events, confirm_overwrite)


# Registry — DERIVED from report_catalog (the report-metadata SoT, P4), so each
# report's TSN descriptor lives in exactly one place. Highway Log shipped first in
# v0.17.0; the format facts come from the raw 6.19 ground-truth set (see
# docs/tsn-parsers.md). Keyed by subdir, in catalog (registration) order.
_REPORTS = {
    e.subdir: TsnReport(
        subdir=e.subdir,
        label=e.label,
        raw_glob=e.raw_glob,
        raw_kind=e.raw_kind,
        consolidated_name=e.consolidated_name,
        builder=e.builder,
    )
    for e in _catalog.tsn_entries()
}


# --------------------------------------------------------------------------- #
# Registry accessors
# --------------------------------------------------------------------------- #
def reports():
    """Every registered TSN report descriptor, in registration order."""
    return list(_REPORTS.values())


def is_registered(report):
    return report in _REPORTS


def get(report):
    """The descriptor for `report`, or raise ValueError for an unknown key."""
    try:
        return _REPORTS[report]
    except KeyError:
        raise ValueError(f"unknown TSN report: {report!r}")


# --------------------------------------------------------------------------- #
# Filesystem layout
# --------------------------------------------------------------------------- #
def raw_dir(report):
    return paths.tsn_library_raw_dir(report)


def consolidated_path(report):
    return paths.tsn_library_consolidated_path(report, get(report).consolidated_name)


def _safe_mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


def _raw_files(report):
    """Sorted raw files for `report` (matching its raw_glob), Excel lock-files
    (~$…) skipped. Empty list when none / the folder doesn't exist yet."""
    try:
        return sorted(p for p in raw_dir(report).glob(get(report).raw_glob)
                      if p.is_file() and not p.name.startswith("~$"))
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# On-disk skeleton — make a fresh/empty library self-documenting so the user
# can SEE where each report's TSN files go before importing the first one. The
# hint/README files are plain .txt, so the *.pdf/*.xlsx readers never see them.
# --------------------------------------------------------------------------- #
_README_NAME = "_README - where TSN files go.txt"
_RAW_HINT_NAME = "_PUT TSN FILES HERE.txt"

_RAW_KIND_DESC = {
    "district_pdfs": "the per-district PDF files (one PDF per Caltrans district)",
    "statewide_pdf": "the single statewide PDF",
    "statewide_xlsx": "the single statewide Excel workbook",
}


def _raw_kind_desc(spec):
    return _RAW_KIND_DESC.get(spec.raw_kind, f"the raw TSN file(s) ({spec.raw_glob})")


def _raw_hint_text(spec):
    return (
        f"{spec.label} - TSN source files\n"
        f"{'=' * 48}\n\n"
        f"Put {_raw_kind_desc(spec)} here.\n"
        f"Expected file type: {spec.raw_glob}\n\n"
        f"Then, in the app: Settings -> TSN reports -> Rebuild ({spec.label}),\n"
        "which builds the workbook the comparison actually reads. (The Import\n"
        "button there can also copy the file(s) in here for you.)\n\n"
        "This note is ignored by the app and is safe to delete.\n"
    )


def _readme_text():
    lines = [
        "TSMIS Exporter - TSN report library",
        "=" * 48,
        "",
        "This folder is where the app looks for each report's TSN source data",
        "(the 'ground truth' your TSMIS exports are compared against).",
        "",
        "Each report has its own folder. Drop that report's TSN file(s) into its",
        "'raw' subfolder, then rebuild it in  Settings -> TSN reports.",
        "",
        "Report folder  ->  what to drop in its raw/ subfolder:",
        "",
    ]
    for spec in reports():
        lines.append(f"  {spec.subdir}/raw/   {spec.label}")
        lines.append(f"      {_raw_kind_desc(spec)}  ({spec.raw_glob})")
    lines += [
        "",
        "The 'consolidated' subfolder is generated by the app — leave it alone.",
        "This note is ignored by the app and is safe to delete.",
    ]
    return "\n".join(lines) + "\n"


def ensure_layout():
    """Create the on-disk skeleton so an empty library is self-documenting: the
    root, each report's raw/ folder, a per-report hint file naming the expected
    format, and a root README mapping every report to its folder. Idempotent and
    best-effort — never overwrites raw data, only seeds the hint into a raw/
    folder that has no real files yet (so it won't fight a user who deleted it
    after adding data), and swallows OSError. Returns the library root Path."""
    root = paths.TSN_LIBRARY_ROOT
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return root
    for spec in reports():
        rd = raw_dir(spec.subdir)
        try:
            rd.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if not _raw_files(spec.subdir):                  # only hint an empty raw/
            hint = rd / _RAW_HINT_NAME
            if not hint.exists():
                try:
                    hint.write_text(_raw_hint_text(spec), encoding="utf-8")
                except OSError:
                    pass
    readme = root / _README_NAME
    if not readme.exists():
        try:
            readme.write_text(_readme_text(), encoding="utf-8")
        except OSError:
            pass
    return root


# --------------------------------------------------------------------------- #
# Legacy fallbacks (Highway Log only) — honored read-only until the user imports
# the raw into the library, so existing installs never break. Computed lazily from
# paths.* at call time (so a test that redirects OUTPUT_ROOT/INPUT_ROOT is honored).
# --------------------------------------------------------------------------- #
def _legacy_consolidated(report):
    if report == "highway_log":
        return paths.OUTPUT_ROOT / "tsn_highway_log_consolidated.xlsx"
    return None


def _legacy_raw_dir(report):
    if report == "highway_log":
        return paths.INPUT_ROOT / "tsn_highway_log"
    return None


def _resolve_legacy_global(report):
    """The pre-library global locations for `report` (consolidated workbook, then
    raw drop folder). Returns the tsn_source-shaped dict, or {kind:none}."""
    cons = _legacy_consolidated(report)
    if cons and cons.is_file():
        return {"kind": "consolidated", "path": str(cons),
                "mtime": _safe_mtime(cons), "legacy": True}
    raw = _legacy_raw_dir(report)
    if raw:
        n = sum(1 for p in raw.glob("*.pdf")) if raw.is_dir() else 0
        if n:
            return {"kind": "pdfs", "pdf_count": n, "legacy": True}
    return {"kind": "none"}


def _resolve_dest_drop(legacy_dest, report):
    """The matrix's dest-scoped drop <dest>/_tsn_input/<report>/ — a consolidated
    .xlsx (newest) wins, else district PDFs -> 'pdfs', else none. Mirrors
    matrix.tsn_source so an existing _tsn_input keeps resolving during cutover."""
    root = Path(legacy_dest) / "_tsn_input" / report
    xlsx, pdfs = [], 0
    try:
        for e in root.iterdir():
            if not e.is_file():
                continue
            sfx = e.suffix.lower()
            if sfx == ".xlsx" and not e.name.startswith("~$"):
                xlsx.append(e)
            elif sfx == ".pdf":
                pdfs += 1
    except OSError:
        pass
    if xlsx:
        newest = max(xlsx, key=lambda q: _safe_mtime(q) or 0)
        return {"kind": "consolidated", "path": str(newest),
                "mtime": _safe_mtime(newest), "legacy": True}
    if pdfs:
        return {"kind": "pdfs", "pdf_count": pdfs, "legacy": True}
    return {"kind": "none"}


# --------------------------------------------------------------------------- #
# Status (drives the Settings ▸ TSN reports panel)
# --------------------------------------------------------------------------- #
def status(report):
    """{report, label, raw_present, raw_count, raw_newest_mtime,
        consolidated_present, consolidated_mtime, current}.

    `current` is True iff a consolidated workbook exists AND is at least as new as
    every raw file (the staleness rule the matrix uses for its stores) — i.e. the
    reusable Excel reflects the current raw. A registered report with no raw in
    the library reports raw_present=False (the user must import it)."""
    spec = get(report)
    raws = _raw_files(report)
    raw_mtimes = [m for m in (_safe_mtime(p) for p in raws) if m is not None]
    raw_newest = max(raw_mtimes) if raw_mtimes else None
    cons = consolidated_path(report)
    cons_exists = cons.is_file()
    cons_mtime = _safe_mtime(cons) if cons_exists else None
    current = bool(cons_exists and raws and cons_mtime is not None
                   and raw_newest is not None and cons_mtime >= raw_newest)
    return {
        "report": report,
        "label": spec.label,
        "raw_kind": spec.raw_kind,
        "raw_present": bool(raws),
        "raw_count": len(raws),
        "raw_newest_mtime": raw_newest,
        "consolidated_present": cons_exists,
        "consolidated_path": str(cons),
        "consolidated_mtime": cons_mtime,
        "current": current,
    }


def all_status():
    """status() for every registered report, in registration order."""
    return [status(r.subdir) for r in reports()]


# --------------------------------------------------------------------------- #
# Import + build
# --------------------------------------------------------------------------- #
def import_raw(report, src_paths, move=False):
    """Copy (or move) user-picked raw file(s) into the report's raw/ folder — the
    only way raw enters the library. Returns the landed paths. Raises
    FileNotFoundError for a missing source; ValueError for an unknown report OR a
    file whose extension doesn't match the report's raw_glob (else it would land
    in raw/ but be invisible to the glob-based reader — a silent import-vs-ignore
    mismatch)."""
    spec = get(report)  # validate + read the expected extension
    want = spec.raw_glob.lower().lstrip("*")          # "*.pdf" -> ".pdf"
    dest = raw_dir(report)
    dest.mkdir(parents=True, exist_ok=True)
    landed = []
    for src in src_paths:
        src = Path(src)
        if not src.is_file():
            raise FileNotFoundError(f"TSN raw file not found: {src}")
        if want and src.suffix.lower() != want:
            raise ValueError(f"{src.name} is not a {want} file — {spec.label} "
                             f"expects {spec.raw_glob}.")
        target = dest / src.name
        if move:
            shutil.move(str(src), str(target))
        else:
            shutil.copy2(str(src), str(target))
        landed.append(target)
    return landed


def build_consolidated(report, events=None, confirm_overwrite=None, force=False):
    """Build (or reuse) the report's consolidated/normalized Excel from its raw.
    Reuses the existing workbook when it is already current and not `force`.
    Resolves the report's builder lazily (so pdfplumber/openpyxl load only here)
    and delegates to it with the library's raw/out paths — the consolidator is
    untouched. Returns a ConsolidateResult."""
    spec = get(report)
    if not force and status(report)["current"]:
        return ConsolidateResult(
            status="ok",
            message="TSN consolidated workbook is already current; reused.",
            summary_lines=[f"{spec.label}: consolidated is up to date (reused)."],
        )
    raws = _raw_files(report)
    if not raws:
        return ConsolidateResult(
            status="error",
            message=(f"No raw {spec.label} files in:\n{raw_dir(report)}\n\n"
                     "Import the raw TSN file(s) first (Settings ▸ TSN reports)."),
        )
    mod_name, func_name = spec.builder.split(":")
    builder = getattr(importlib.import_module(mod_name), func_name)
    out = consolidated_path(report)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = builder(raw_dir(report), out, events=events,
                     confirm_overwrite=confirm_overwrite)
    # P1-B05: persist the builder's producer completion beside the generated workbook
    # through the shared boundary, so a PARTIAL TSN normalization (categories / district
    # PDFs left out) stays flagged when resolve() reuses the consolidated workbook. A
    # False return = a non-complete normalization's flag could NOT be recorded
    # (publication failed): the build cannot claim a safely persisted artifact, so report
    # an error result rather than the success-shaped one (the worker/UI surfaces it).
    if not consolidation_meta.write_outcome(out, result):
        return ConsolidateResult(
            status="error",
            message=(f"{spec.label}: the consolidation finished but its outcome could not "
                     "be recorded; the incomplete workbook was discarded — re-run."))
    return result


# --------------------------------------------------------------------------- #
# Shared single-file normalizer (the tsn_load_* family substrate, S04/R1-N01)
#
# The four single-file TSN loaders (tsn_load_ramp_summary / _ramp_detail /
# _intersection_summary / _intersection_detail) all share ONE skeleton: find the
# newest raw export in raw/, parse it via the report's own projector (which lives in
# the matching compare_*_tsn module), then write a small normalized write-only
# workbook (one sheet, a styled header, the projected rows) atomically. Only the
# glob, projection, header, and result text differ per report — that per-report glue
# stays in the thin tsn_load_* shim; this factory owns the rest. compare_core is
# untouched and the builder strings (tsn_load_*:build_into) are preserved.
# --------------------------------------------------------------------------- #
def _newest_raw(rdir, glob):
    """The newest non-temp file in `rdir` matching `glob` (the single statewide
    export a tsn_load_* normalizes), or None."""
    cands = [p for p in Path(rdir).glob(glob)
             if p.is_file() and not p.name.startswith("~$")]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def _write_normalized_workbook(sheet, header, header_align, rows):
    """A write-only workbook: one `sheet`, the styled `header` row (the shared
    TSN-library blue header + the report's own Alignment kwargs), then `rows`."""
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet)
    head_fill = PatternFill("solid", start_color="305496")
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    align = Alignment(**header_align)
    cells = []
    for label in header:
        c = WriteOnlyCell(ws, value=label)
        c.fill, c.font, c.alignment = head_fill, head_font, align
        cells.append(c)
    ws.append(cells)
    for r in rows:
        ws.append(r)
    return wb


def build_normalized(raw_dir, out_path, *, glob, deps_ok, deps_msg, no_raw_what,
                     no_raw_hint, log_label, sheet, header, header_align, project,
                     events=None, confirm_overwrite=None):
    """Shared driver for the single-file TSN normalizers (S04). Finds the newest
    `glob` file in `raw_dir`, parses it via `project`, and writes the normalized
    workbook (one `sheet`, the styled `header`, then the projected rows) to
    `out_path` atomically (F9: temp + os.replace, never truncating a prior file).

    `project(raw_path)` returns `(rows, make_result)`:
      * `rows`                 -- the iterable of data rows appended under `header`;
      * `make_result(out_name)` -- builds the success ConsolidateResult, so each
        report keeps its own message / summary_lines / producer completion.
    The deps gate (`deps_ok`/`deps_msg`), missing-raw message (`No raw {no_raw_what}
    found ...` + `no_raw_hint`), overwrite-confirm, parse-error wrapping, and the
    PermissionError save guard are identical across the family and live here.
    Returns a ConsolidateResult; `compare_core` is untouched."""
    events = events or Events()
    if not deps_ok:
        return ConsolidateResult(status="error", message=deps_msg)
    raw = _newest_raw(raw_dir, glob)
    if raw is None:
        return ConsolidateResult(
            status="error",
            message=f"No raw {no_raw_what} found in:\n{raw_dir}\n\n{no_raw_hint}")
    out_path = Path(out_path)
    confirm = confirm_overwrite or (lambda _p: True)
    if out_path.exists() and not confirm(out_path):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

    events.on_log(f"Normalizing {log_label}: {raw.name}")
    try:
        rows, make_result = project(str(raw))
    except Exception as e:
        return ConsolidateResult(
            status="error",
            message=f"Could not read {raw.name}: {type(e).__name__}: {e}")

    try:
        wb = _write_normalized_workbook(sheet, header, header_align, rows)
    except ImportError:
        # The `deps_ok` probe is a single `from openpyxl import Workbook`; this is the
        # centralized backstop for a partial/frozen-pruned openpyxl whose WriteOnlyCell /
        # styles symbols are missing — return the shim's friendly deps message, never crash
        # (P5-A01). Kept here (not 4 broadened probes) so the writing skeleton stays in one place.
        return ConsolidateResult(status="error", message=deps_msg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import artifact_store
    try:
        artifact_store.atomic_save(wb, out_path)    # F9: temp + os.replace (never truncate prior)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out_path.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))
    return make_result(out_path.name)


# --------------------------------------------------------------------------- #
# Resolve (the matrices' single TSN entry point)
# --------------------------------------------------------------------------- #
def resolve(report, selected_file=None, legacy_dest=None):
    """Resolve the TSN dataset for `report` (the matrices' single entry point) and
    attach the persisted producer `completion` (P1-B05) to any path-bearing source —
    so a PARTIAL generated TSN workbook (categories / district PDFs left out) flags the
    comparison even when reused. `completion` is None for a user-picked file or a
    workbook with no sidecar (deliberate: a user pick / legacy workbook reads complete)."""
    r = _resolve_source(report, selected_file, legacy_dest)
    if r.get("path"):
        r = {**r, "completion": consolidation_meta.read_completion(r["path"])}
    return r


def _resolve_source(report, selected_file=None, legacy_dest=None):
    """Resolve the TSN dataset for `report`, returning the same contract as
    matrix.tsn_source: {kind: file|consolidated|pdfs|raw|none, path?, mtime?,
    pdf_count?, raw_count?}. Resolution order:
      1. an explicit user-picked `selected_file` (a real .xlsx) — always wins;
      2. the library's generated consolidated workbook;
      3. the library's raw file(s) -> 'pdfs' (PDF raw) / 'raw' (xlsx raw): the
         'import is present but build the consolidated first' state;
      4. the dest-scoped legacy drop <dest>/_tsn_input/<report>/ (back-compat);
      5. the global legacy locations (Highway Log only);
      6. none.
    """
    if selected_file:
        p = Path(selected_file)
        if p.is_file() and p.suffix.lower() == ".xlsx":
            return {"kind": "file", "path": str(p), "mtime": _safe_mtime(p)}

    if is_registered(report):
        cons = consolidated_path(report)
        if cons.is_file():
            return {"kind": "consolidated", "path": str(cons), "mtime": _safe_mtime(cons)}
        raws = _raw_files(report)
        if raws:
            spec = get(report)
            if spec.raw_kind in ("district_pdfs", "statewide_pdf"):
                return {"kind": "pdfs", "pdf_count": len(raws)}
            return {"kind": "raw", "raw_count": len(raws), "raw_kind": spec.raw_kind}

    if legacy_dest is not None:
        r = _resolve_dest_drop(legacy_dest, report)
        if r["kind"] != "none":
            return r

    r = _resolve_legacy_global(report)
    if r["kind"] != "none":
        return r

    return {"kind": "none"}

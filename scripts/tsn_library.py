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
ConsolidateResult or raise. Consolidator imports are LAZY (inside
build_consolidated) so importing this module never pulls pdfplumber / openpyxl.
"""
import importlib
import shutil
from dataclasses import dataclass
from pathlib import Path

import paths
from events import ConsolidateResult


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


# Registry — reports are added here as their library builder lands in v0.17.0.
# Highway Log ships first (its builder already exists: consolidate_tsn_highway_log
# .build_into). The format facts come from the raw 6.19 ground-truth set; see
# docs/tsn-parsers.md.
_REPORTS = {
    "highway_log": TsnReport(
        subdir="highway_log",
        label="TSN Highway Log",
        raw_glob="*.pdf",
        raw_kind="district_pdfs",
        consolidated_name="tsn_highway_log_consolidated.xlsx",
        builder="consolidate_tsn_highway_log:build_into",
    ),
    "ramp_detail": TsnReport(
        subdir="ramp_detail",
        label="TSN Ramp Detail",
        raw_glob="*.xlsx",
        raw_kind="statewide_xlsx",
        consolidated_name="tsn_ramp_detail_normalized.xlsx",
        builder="tsn_load_ramp_detail:build_into",
    ),
    "ramp_summary": TsnReport(
        subdir="ramp_summary",
        label="TSN Ramp Summary",
        raw_glob="*.pdf",
        raw_kind="statewide_pdf",
        consolidated_name="tsn_ramp_summary_normalized.xlsx",
        builder="tsn_load_ramp_summary:build_into",
    ),
    "intersection_summary": TsnReport(
        subdir="intersection_summary",
        label="TSN Intersection Summary",
        raw_glob="*.pdf",
        raw_kind="statewide_pdf",
        consolidated_name="tsn_intersection_summary_normalized.xlsx",
        builder="tsn_load_intersection_summary:build_into",
    ),
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
    FileNotFoundError for a missing source; ValueError for an unknown report."""
    get(report)  # validate
    dest = raw_dir(report)
    dest.mkdir(parents=True, exist_ok=True)
    landed = []
    for src in src_paths:
        src = Path(src)
        if not src.is_file():
            raise FileNotFoundError(f"TSN raw file not found: {src}")
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
    return builder(raw_dir(report), out, events=events,
                   confirm_overwrite=confirm_overwrite)


# --------------------------------------------------------------------------- #
# Resolve (the matrices' single TSN entry point)
# --------------------------------------------------------------------------- #
def resolve(report, selected_file=None, legacy_dest=None):
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

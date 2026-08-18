"""Normalize the raw TSN Highway Detail statewide workbook into the canonical
TSN library's reusable comparison form.

The TSN Highway Detail source is a single statewide XLSX ("Sheet 1", 56 DB
columns, every route). "Consolidating" it = projecting it once to the shared
comparison shape ([Route] + the vs-TSN header) so every comparison reads a
small ready workbook instead of re-parsing the 60k-row dump. The projection
(route from RTE+RTE_SFX, the canonical roadbed-aware Post Mile, NA/zero-pad/
length/median normalization) lives in compare_highway_detail_tsn; this module
supplies the report-specific glue and delegates the shared find-raw/write/save
skeleton to tsn_library.build_normalized (S04).

Console-free; openpyxl only.
"""
import re
from datetime import date

try:
    from openpyxl import Workbook, load_workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_highway_detail_tsn as hdt
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"

# Sidecar columns APPENDED after the shared header. v2 carried the TSN district
# + county; **v4 widens it** (CMP-AUD-133) so the normalized library also
# conserves the Report View's TSN-only facts (the DCR cell + the five-value ADT
# block — before v4 a library-sourced comparison blanked all six) and the
# source-only raw columns the projection to SHARED_HEADER otherwise dropped.
# compare_highway_detail_tsn owns the contract; this mirrors it, and
# check_tsn_normalization_marker gates the mirror. The comparison's loader slices
# the sidecar off (_normalized_row reads exactly the shared width); the
# visual-evidence generator reads district/county to find a row's district print.
SIDECAR_HEADER = list(hdt._NORMALIZED_SIDECARS)

# CMP-AUD-142: an ISO date the raw dump prints once for the WHOLE extract.
_EXTRACT_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _extract_date(values, column):
    """The ONE value `column` carries across the whole dump, validated.

    CMP-AUD-142 requires these to be exact source facts, so anything ambiguous is
    a hard error rather than a guess: the column must be non-blank, single-valued,
    and a real calendar date. A dump carrying two reference dates is two snapshots
    stapled together — exactly the state a normalized library must not average
    over silently."""
    seen = {v for v in values if v}
    if not seen:
        raise ValueError(
            f"The TSN Highway Detail export carries no {column} value — it cannot "
            "be normalized without knowing which snapshot it is.")
    if len(seen) > 1:
        raise ValueError(
            f"The TSN Highway Detail export carries {len(seen)} different {column} "
            f"values ({', '.join(sorted(seen)[:3])}) — it is not one snapshot.")
    value = seen.pop()
    if not _EXTRACT_DATE_RE.match(value):
        raise ValueError(
            f"The TSN Highway Detail export's {column} is not a calendar date "
            f"({value!r}).")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"The TSN Highway Detail export's {column} is not a real date "
            f"({value!r}).")
    return value


def _rows_with_sidecar(path):
    """The raw statewide projection (hdt.tsn_rows_from_raw's rows, same order)
    PLUS each row's SIDECAR_HEADER values and the two per-row extract-date
    claims — one pass, in a separate loop so the comparator's regression-locked
    loader stays untouched. Returns (rows, sidecars, ref_dates, ext_dates)."""
    _s = hdt._s
    raw_for = hdt.SIDECAR_RAW_COLUMNS
    with hdt.ctc.exact_raw_rows(
            path, hdt.TSN_SHEET, hdt.TSN_RAW_HEADER, hdt.REPORT_NAME,
            required_nonblank=("DIST", "CNTY", "RTE", "POSTMILE")) as (header, rows_in):
        h = {n: i for i, n in enumerate(header)}

        def g(r, col):
            i = h.get(col)
            return _s(r[i]) if i is not None and i < len(r) else ""

        rows, side, ref_dates, ext_dates = [], [], [], []
        for r in rows_in:
            rows.append(hdt._tsn_row(r, h))
            dist, cnty = g(r, "DIST"), g(r, "CNTY").rstrip(".")
            # The printed DCR cell: the source's own DIST_CNTY_ROUTE when it has
            # one, else assembled from the three parts it always carries — the
            # SAME rule the raw-workbook Report View path already used.
            dcr = g(r, "DIST_CNTY_ROUTE") or "-".join(
                t for t in (dist, cnty, g(r, "RTE") + g(r, "RTE_SFX")) if t)
            side.append([dist, cnty]
                        + [dcr if col == "TSN DCR" else g(r, raw_for[col])
                           for col in SIDECAR_HEADER[2:]])
            ref_dates.append(g(r, "REFERENCE_DATE")[:10])
            ext_dates.append(g(r, "EXTRACT_DATE")[:10])
        return rows, side, ref_dates, ext_dates


def tsn_rows_with_dcr(path):
    """The raw statewide projection PLUS each row's (district, county) — the
    long-standing narrow view the visual-evidence adapter reads to find a row's
    district print. Deliberately does NOT validate the extract dates: evidence
    must keep working on a dump whose provenance the library build would refuse."""
    rows, side, _ref, _ext = _rows_with_sidecar(path)
    return rows, [(sc[0], sc[1]) for sc in side]


def tsn_rows_with_sidecar(path):
    """The raw statewide projection PLUS the FULL v4 sidecar and the validated
    extract-level provenance (CMP-AUD-133 / CMP-AUD-142). Returns
    (rows, sidecars, provenance)."""
    rows, side, ref_dates, ext_dates = _rows_with_sidecar(path)
    provenance = [
        (hdt.PROV_REFERENCE_DATE, _extract_date(ref_dates, "REFERENCE_DATE")),
        (hdt.PROV_EXTRACT_DATE, _extract_date(ext_dates, "EXTRACT_DATE")),
    ]
    return rows, side, provenance


def _project(raw_path):
    """Read the statewide workbook into the consolidated [Route]+SHARED_HEADER
    (+ sidecar) rows, the extract-level provenance, and the success result."""
    base, side, provenance = tsn_rows_with_sidecar(raw_path)
    rows = [row + sc for row, sc in zip(base, side)]
    n_routes = len({r[0] for r in rows})

    def make_result(out_name):
        return ConsolidateResult(
            status="ok",
            message=f"Normalized {len(rows)} TSN Highway Detail rows ({n_routes} routes).",
            summary_lines=[f"TSN Highway Detail: {len(rows)} rows, {n_routes} routes "
                           f"-> {out_name}"],
            completion=outcome.COMPLETE,
            skipped_inputs=0,
            failed_inputs=0)

    return rows, make_result, provenance


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Highway Detail statewide workbook in `raw_dir` into
    the normalized workbook at `out_path` (sheet hdt.NORMALIZED_SHEET, header
    ['Route'] + hdt.SHARED_HEADER). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN Highway Detail .xlsx",
        no_raw_hint="Import the statewide 'TSAR - HIGHWAY DETAIL' TSN export first.",
        log_label="TSN Highway Detail",
        sheet=hdt.NORMALIZED_SHEET,
        header=["Route"] + hdt.SHARED_HEADER + SIDECAR_HEADER,
        header_align={"horizontal": "center", "vertical": "center", "wrap_text": True},
        project=_project,
        marker_version=hdt.NORMALIZATION_VERSION)   # CMP-AUD-037 direct-path freshness marker

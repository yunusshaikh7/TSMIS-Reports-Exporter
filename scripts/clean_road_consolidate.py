"""The shared consolidation glue for the six SITE Clean Road editions (v0.48.0).

Each Clean Road report has an Excel edition and a print edition; both
consolidate into the SAME workbook shape — one sheet named like the export's
own sheet, a leading "Route" column, then the export's exact header — so every
comparison reads either edition through one loader:

  * Excel (`consolidate_clean_road_<kind>`): a thin wrapper over the shared
    per-route XLSX core, like every other flat report.
  * Print (`consolidate_tsmis_clean_<kind>_pdf`): each route's print is read by
    `clean_road_print`, written as a per-route workbook in the Excel export's
    layout (columns the print doesn't carry stay blank — the site leaves them
    blank in the Excel too), then combined by the same core through the shared
    `run_pdf_conversion` driver, which also stamps the PDF-conversion marker.

The route of a print is its cover page's own "LOCATION CRITERIA: ROUTE <r>"
claim; the filename token only corroborates it (CMP-AUD-049).

Not the ArcGIS build: `consolidate_clean_highway` is the app's OWN CA HIGHWAYS
table built from the layer library; these read the site's exports.
Console-free.
"""
import re
from pathlib import Path

try:
    import openpyxl  # noqa: F401 — the deps gate covers the XLSX side
    _XLSX_OK = True
except ImportError:
    _XLSX_OK = False

import clean_road_print as crp
import outcome
from consolidate_xlsx_base import consolidate_xlsx
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)
from pdf_table_lib import (norm_route, reconcile_route_identity,
                           run_pdf_conversion, write_route_workbook)

_ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]{0,2})", re.IGNORECASE)


def excel_filename(spec):
    """'clean_road_highway_consolidated.xlsx' — named for the report, not the
    `clean_highway` export key, so it can never be mistaken for the ArcGIS
    build's CA HIGHWAYS workbook."""
    return f"clean_road_{spec.key.split('_', 1)[1]}_consolidated.xlsx"


def pdf_filename(spec):
    """'tsmis_clean_highway_pdf_consolidated.xlsx' — the PDF consolidators'
    `tsmis_<subdir>_consolidated.xlsx` convention (a Reset target)."""
    return f"tsmis_{spec.pdf_key}_consolidated.xlsx"


def input_dir_for(subdir, day):
    """The per-route exports for `day`; None = the legacy flat layout."""
    return (output_day_dir(day) / subdir) if day else OUTPUT_ROOT / subdir


def out_path_for(filename, day, legacy):
    """The consolidated workbook for `day`; None = the legacy location."""
    if not day:
        return legacy
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(filename, day)


def consolidate_excel(spec, *, events=None, confirm_overwrite=None, day=None,
                      input_dir=None, out_path=None, commit_guard=None,
                      report_name, legacy_out):
    """Combine every per-route Clean Road Excel export of `spec`."""
    day = day or latest_output_day()
    return consolidate_xlsx(
        input_dir=Path(input_dir) if input_dir else input_dir_for(spec.key, day),
        out_path=(Path(out_path) if out_path
                  else out_path_for(excel_filename(spec), day, legacy_out)),
        sheet_name=spec.sheet, report_name=report_name,
        title=f"{report_name} Consolidation",
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard)


def _write_route(spec):
    def write(rows, out_file):
        # Empty strings become None so blank cells match the Excel export's.
        write_route_workbook(rows, out_file, sheet_name=spec.sheet,
                             header=list(spec.header),
                             row_values=lambda r: [v if v else None for v in r],
                             pdf_source_marker=True)
    return write


def consolidate_pdf(spec, *, events=None, confirm_overwrite=None, day=None,
                    input_dir=None, out_path=None, converted_dir=None,
                    commit_guard=None, report_name, legacy_out, legacy_converted):
    """Read every per-route Clean Road print of `spec` into the Excel export's
    layout and combine them (the PDF-conversion marker rides the result)."""
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(spec.pdf_key, day)
    out = Path(out_path) if out_path else out_path_for(pdf_filename(spec), day, legacy_out)
    conv = Path(converted_dir) if converted_dir else legacy_converted

    def convert_one(p, prefix, ev, ctx):
        if ev.is_cancelled():
            return ("cancelled",)
        name_m = _ROUTE_FROM_NAME.search(p.stem)
        name_route = norm_route(name_m.group(1)) if name_m else None
        read = crp.read_print(p, spec)
        if not read.rows:
            ev.on_log(f"{prefix} no {spec.noun_plural} found; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        claims = [norm_route(read.route_claim)] if read.route_claim else []
        route = reconcile_route_identity(
            p.name, name_route, claims, ev, ctx,
            claim_desc="the cover page's \"ROUTE <r>\" line")
        if route is None:
            return ("skip",)
        ctx["rows"] = ctx.get("rows", 0) + len(read.rows)
        return ("ok", route, read.rows)

    def finalize(result, ctx):
        # A failed print is invisible downstream, so ESCALATE to a
        # producer-owned partial — never promoted / compared as complete.
        if ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))

    deps_ok = _XLSX_OK and crp._DEPS_OK
    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=deps_ok,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=report_name,
        banner_title=f"{report_name} Conversion",
        export_hint=(f"Export the '{spec.label.replace('Clean Road ', 'Clean Road: ')} "
                     "(PDF)' report first (it saves the per-route prints there), "
                     "then run this again."),
        unreadable_hint=(f"Are they the {spec.label} prints (the site's Print "
                         "button for this report)?"),
        converted_prefix=f"tsmis_{spec.pdf_key}",
        convert_one=convert_one, write_one=_write_route(spec),
        finalize=finalize,
        consolidate_kwargs=dict(sheet_name=spec.sheet, report_name=report_name,
                                title=f"{report_name} Consolidation"))

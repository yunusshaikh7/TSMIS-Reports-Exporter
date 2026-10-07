"""Cross-environment adapters for the editions integrated in v0.48.0.

The same `compare_env.EnvCompare` machinery every other report rides — two run
folders, the per-route files read straight from both, compared cell for cell
with the environments as the two sides (and, through the baseline matrix, one
environment against an earlier day of itself):

  * Ramp Summary (Excel) — one row of category counts per route, parsed by
    `consolidate_ramp_summary_excel.parse_xlsx` (the PDF row's exact record and
    integrity gate);
  * Intersection Summary (PDF) / Highway Summary (PDF) — the same per-route
    aggregate rows as their Excel siblings, parsed from the prints by the
    v0.48.0 consolidators' own readers;
  * the six Clean Road editions — flat per-route tables keyed on the record's
    physical location (route · county · PM prefix · postmile · roadbed, the
    comparison's own key); the prints are read into the Excel layout by
    their consolidator in a scratch folder first, exactly like the other
    print editions.

Kept in its own module so `compare_env` doesn't grow past its size; the
catalog references these instances like any other EnvCompare. Console-free.
"""
import logging
import shutil
import tempfile
from pathlib import Path

import clean_road_columns as crc
import compare_clean_road_tsn as crt
import compare_env as ce
import consolidate_highway_summary as _hs
import consolidate_tsmis_clean_highway_pdf as _crh_pdf
import consolidate_tsmis_clean_intersection_pdf as _cri_pdf
import consolidate_tsmis_clean_ramp_pdf as _crr_pdf
import consolidate_intersection_summary as _is
import consolidate_ramp_summary as _rs
import highway_summary_columns as _hsc
from compare_core import CompareSchema

log = logging.getLogger("tsmis.compare")


def _aggregate_side(folder, label, events, *, subdir, glob, noun, parse, accept):
    """Shared per-route aggregate loader: every file of one side -> one row per
    route, through `parse(path)` -> `accept(path, parsed)` (the family's own
    has-data + integrity gates; returns (row, skip_reason))."""
    in_dir, files = ce._find_input_dir(folder, subdir, glob)
    if not files:
        raise ValueError(
            f"No {noun} files were found for the {label} side:\n{in_dir}\n\n"
            f"Export the {noun} report on that environment first.")
    rows, skipped = [], []
    for i, p in enumerate(files, 1):
        if events.is_cancelled():
            raise ValueError("Cancelled by user.")
        try:
            parsed = parse(str(p))
        except Exception as e:
            events.on_log(f"  [{label}] {p.name}: could not parse "
                          f"({type(e).__name__}); skipping")
            log.warning("env compare: %s parse failed", p, exc_info=True)
            skipped.append(f"{label} {p.name}: could not parse ({type(e).__name__})")
            continue
        row, why = accept(p, parsed)
        if row is None:
            events.on_log(f"  [{label}] {p.name}: {why}; skipping")
            skipped.append(f"{label} {p.name}: {why}")
            continue
        rows.append(row)
        events.on_log(f"  [{label}] [{i:>3}/{len(files)}] {p.name} (route {row[0]})")
    if not rows:
        raise ValueError(f"No readable {noun} files were found for the {label} "
                         f"side in:\n{in_dir}")
    if skipped:
        events.on_log(f"  [{label}] note: {len(skipped)} file(s) skipped (details above).")
    return rows, skipped


# --------------------------------------------------------------------------- #
# Ramp Summary (Excel)
# --------------------------------------------------------------------------- #
def _accept_ramp(p, record):
    if not _rs.record_has_data(record):
        return None, "no ramp data (truncated export?)"
    route = ce._norm_route_key(record.get("route") or ce._route_from_name(p))
    problem = _rs.reconcile_problem(record)
    if problem:
        return None, f"route {route} doesn't reconcile ({problem})"
    return [route] + [record.get(col) for col, _disp in ce._RS_FIELDS], None


def _load_ramp_summary_excel_side(folder, label, events):
    import consolidate_ramp_summary_excel as rsx
    return _aggregate_side(folder, label, events, subdir=rsx.SUBDIR, glob="*.xlsx",
                           noun="Ramp Summary (Excel)", parse=rsx.parse_xlsx,
                           accept=_accept_ramp)


RAMP_SUMMARY_EXCEL = ce.EnvCompare(
    "ramp_summary_excel", "Ramp Summary (Excel)", "ramp_summary_excel",
    side_loader=_load_ramp_summary_excel_side, agg_header=ce.RS_HEADER,
    base_schema=CompareSchema(
        report_name="Ramp Summary (Excel)", header=ce.RS_HEADER,
        id_noun="route", id_noun_plural="routes",
        scope_flat="All routes (one row per route)"))


# --------------------------------------------------------------------------- #
# Intersection Summary (PDF) / Highway Summary (PDF)
# --------------------------------------------------------------------------- #
def _accept_intersection(p, parsed):
    route, counts, total = parsed
    if not _is.record_has_data({"counts": counts}):
        return None, "no intersection data"
    problem = _is.record_problem(counts, total)
    if problem:
        return None, f"route {route} — {problem}"
    return ([ce._norm_route_key(route), total]
            + [counts.get(slug, 0) for slug, _k in ce._IS_FIELDS]), None


def _load_intersection_summary_pdf_side(folder, label, events):
    import consolidate_tsmis_intersection_summary_pdf as isp
    return _aggregate_side(folder, label, events, subdir=isp.SUBDIR, glob="*.pdf",
                           noun="Intersection Summary (PDF)", parse=isp.parse_pdf,
                           accept=_accept_intersection)


def _accept_highway(p, parsed):
    route, values, total = parsed
    if not _hs.record_has_data({"total": total, "values": values}):
        return None, "no mileage"
    problem = _hs.record_problem(values, total, source=p.name)
    if problem:
        return None, f"route {route} — {problem}"
    return ([ce._norm_route_key(route), _hsc.miles(total)]
            + [_hsc.miles(values.get(c.slug, 0)) for c in _hsc.CATS]), None


def _load_highway_summary_pdf_side(folder, label, events):
    import consolidate_tsmis_highway_summary_pdf as hsp
    return _aggregate_side(folder, label, events, subdir=hsp.SUBDIR, glob="*.pdf",
                           noun="Highway Summary (PDF)", parse=hsp.parse_pdf,
                           accept=_accept_highway)


INTERSECTION_SUMMARY_PDF = ce.EnvCompare(
    "intersection_summary_pdf", "Intersection Summary (PDF)",
    "intersection_summary_pdf",
    side_loader=_load_intersection_summary_pdf_side, agg_header=ce.IS_HEADER,
    discovery_glob="*.pdf",
    base_schema=CompareSchema(
        report_name="Intersection Summary (PDF)", header=ce.IS_HEADER,
        id_noun="route", id_noun_plural="routes",
        scope_flat="All routes (one row per route)"))

HIGHWAY_SUMMARY_PDF = ce.EnvCompare(
    "highway_summary_pdf", "Highway Summary (PDF)", "highway_summary_pdf",
    side_loader=_load_highway_summary_pdf_side, agg_header=ce.HS_HEADER,
    discovery_glob="*.pdf",
    base_schema=CompareSchema(
        report_name="Highway Summary (PDF)", header=ce.HS_HEADER,
        id_noun="route", id_noun_plural="routes",
        scope_flat="All routes (one row per route)"))


# --------------------------------------------------------------------------- #
# the six Clean Road editions
# --------------------------------------------------------------------------- #
def _clean_road_keys(spec):
    """The cross-env key builder: the vs-TSN comparison's own physical key
    (route · county · PM prefix · postmile · roadbed), built per row from the
    export's columns."""
    profile = crt.profile_for(spec.key)

    def builder(header, key_field):
        if list(header) != list(spec.header):
            log.warning("env compare %s: unexpected header; falling back to the "
                        "plain postmile key", spec.key)
            return None

        def normalizer(row, off, _kf):
            vals = list(row[off:off + len(spec.header)])
            vals += [None] * (len(spec.header) - len(vals))
            # The route is the file's own token (column 0): two exports of one
            # route file pair row for row, and the engine requires the key's
            # route to equal it (a ramp the site lists under another route's
            # file stays in that file's universe on both sides).
            route = "" if row[0] is None else str(row[0])
            return crt._key(profile, vals, f"{spec.label} route {route}", route=route)[1]
        return normalizer
    return builder


def _clean_road_pdf_side(spec, module):
    def load(folder, label, events):
        in_dir, pdfs = ce._find_input_dir(folder, spec.pdf_key, "*.pdf")
        if not pdfs:
            raise ValueError(
                f"No {spec.label} (PDF) files were found for the {label} side:\n"
                f"{in_dir}\n\nExport the {spec.label} (PDF) report on that "
                "environment first.")
        conv = Path(tempfile.mkdtemp(prefix=f"{spec.pdf_key}_env_conv_"))
        combined_dir = Path(tempfile.mkdtemp(prefix=f"{spec.pdf_key}_env_out_"))
        try:
            res = module.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                     input_dir=in_dir,
                                     out_path=combined_dir / "_combined.xlsx",
                                     converted_dir=conv)
            if res.status == "cancelled":
                raise ValueError("Cancelled by user.")
            if res.status != "ok":
                raise ValueError(res.message or f"Could not read the {spec.label} prints.")
            loaded = ce._load_xlsx_side(conv, label, "_perroute_", spec.sheet,
                                        f"{spec.label} (PDF)", events,
                                        expected_header=list(spec.header))
            return ce._pdf_loaded_side(res, loaded, label=label,
                                       report_name=f"{spec.label} (PDF)",
                                       source_pdf_count=len(pdfs))
        finally:
            shutil.rmtree(conv, ignore_errors=True)
            shutil.rmtree(combined_dir, ignore_errors=True)
    return load


def _clean_road_excel(spec):
    return ce.EnvCompare(
        spec.key, spec.label, spec.key, sheet_name=spec.sheet,
        expected_header=list(spec.header), key_col=spec.pm_col,
        physical_key_builder=_clean_road_keys(spec),
        base_schema=CompareSchema(report_name=spec.label, header=list(spec.header),
                                  id_noun=spec.noun, id_noun_plural=spec.noun_plural))


def _clean_road_pdf(spec, module):
    return ce.EnvCompare(
        spec.pdf_key, f"{spec.label} (PDF)", spec.pdf_key, sheet_name=spec.sheet,
        key_col=spec.pm_col, flat_pdf_loader=_clean_road_pdf_side(spec, module),
        physical_key_builder=_clean_road_keys(spec),
        base_schema=CompareSchema(report_name=f"{spec.label} (PDF)",
                                  header=list(spec.header),
                                  id_noun=spec.noun, id_noun_plural=spec.noun_plural))


CLEAN_HIGHWAY = _clean_road_excel(crc.HIGHWAY)
CLEAN_INTERSECTION = _clean_road_excel(crc.INTERSECTION)
CLEAN_RAMP = _clean_road_excel(crc.RAMP)
CLEAN_HIGHWAY_PDF = _clean_road_pdf(crc.HIGHWAY, _crh_pdf)
CLEAN_INTERSECTION_PDF = _clean_road_pdf(crc.INTERSECTION, _cri_pdf)
CLEAN_RAMP_PDF = _clean_road_pdf(crc.RAMP, _crr_pdf)

"""ArcGIS-tab "Reports vs layers" matrix engine (the by-day layer-build matrix).

The fifth matrix, and the main view of the ArcGIS tab (2026-09-02): rows = every
TSMIS report the layer library renders (the `arcgis_reports` registry — the two
rendered so far plus the rows still waiting on a build, so the whole report set
is visible and says what is missing), columns = exported DAYS the user adds,
each cell = OUR report built from the layers vs the app's own consolidated
export of that day. Both sides are TSMIS, so they should agree.

ONE build per report, like the TSN library (owner decision 2026-09-02): the
layers are exported by hand and rarely, every day column compares against the
same built workbook, and each build records the layer DROP it came from — its
export date and its content fingerprint — so the library reads a build stale
the moment a fresher drop is staged. A build is a reconstruction as of a date:
the drop's own export date unless the owner sets one, and the comparison's
Notes state that date beside the export day, because across a gap the
comparison measures network change on top of any real difference.

Own store root output/comparisons/arcgis-by-day/, own results cache + attempts
overlay, the M1-C self-identifying names, the shared job queue. The per-cell
build rides the SAME shared primitives the other matrices use
(`matrix._ensure_consolidated` for the export side, `matrix._settle_formulas_twin`,
`matrix._published_comparison_result`) and the report's own registered
comparator — never a second comparison implementation.

Console-free like the rest of the core: progress via the Events sink, exceptions
raised — never print/input/sys.exit. Only gui_api / gui_worker drive it.
"""
import json
import logging
import os
import time
from pathlib import Path

import arcgis_layers
import arcgis_reports
import artifact_store
import cache_envelope
import clean_road_layers as crl
import consolidation_meta
import matrix
import outcome
import output_state
from paths import (comparisons_root, day_source_dir, list_output_days,
                   parse_run_folder, today_str)

log = logging.getLogger("tsmis.arcgis_matrix")

SOURCE_DEFAULT = "ssor-prod"
AG_DIRNAME = "arcgis-by-day"                 # under output/comparisons/
_RESULTS_FILE = "_results.json"
_CACHE_IDENTITY = "arcgis-by-day"


# --------------------------------------------------------------------------- #
# rows + sources
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _ag_rows():
    """[(row_key, label, code, subdirs, buildable, comparable, why)] — one row
    per registry report, in registry order. `subdirs` are the export editions
    the cell can read as the TSMIS side, preferred first."""
    out = []
    for r in arcgis_reports.labels():
        subdirs = arcgis_reports.spec(r["key"]).subdirs if r["comparable"] else ()
        out.append((r["key"], r["label"], r["code"], subdirs, r["buildable"],
                    r["comparable"], r["why"]))
    return out


def _row_lookup():
    return {r[0]: r for r in _ag_rows()}


def row_keys():
    """The valid row keys, straight off the registry — no filesystem."""
    return set(arcgis_reports.KEYS)


# --------------------------------------------------------------------------- #
# paths + the results cache
# --------------------------------------------------------------------------- #
def ag_root():
    return comparisons_root() / AG_DIRNAME


def day_folder_name(date, source):
    return f"{date} {source}"


def day_out_path(date, source, row_key):
    """The VALUES workbook for one (day, report). The basename embeds the report,
    the day and the source (M1-C) so two days' comparisons of one report can be
    open in Excel at once and a lifted file still says what it is."""
    return (ag_root() / day_folder_name(date, source)
            / f"{row_key}_vs_layers {date} {source}.xlsx")


def _results_path():
    return output_state.state_file(ag_root(), _RESULTS_FILE)


def _results_read_path():
    return output_state.named_read_file(ag_root(), _RESULTS_FILE)


def load_results():
    """{ "<date source>|<row>": {verdict, diff_cells, one_sided, built_at_mtime,
    completion, generation_id, input_fingerprint, source_identities,
    producer_versions} } — the by-day counts cache."""
    p = _results_read_path()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return cache_envelope.unwrap(data, output_identity=_CACHE_IDENTITY)
    except OSError:  # silent-ok: no cache file yet (first run) — the empty map is the correct state
        return {}
    except ValueError as e:                  # corrupt JSON: surface it, then degrade
        log.warning("arcgis_matrix: corrupt results cache %s (%s: %s); treating as empty",
                    p, type(e).__name__, e)
        return {}


def record_result(date, source, row_key, verdict, diff_cells, one_sided,
                  built_at_mtime, completion=None, input_fingerprint=None,
                  source_identities=None, generation_id=None,
                  producer_versions=None, commit_guard=None):
    data = load_results()
    data[f"{day_folder_name(date, source)}|{row_key}"] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
        "completion": completion,
        "generation_id": generation_id,
        "input_fingerprint": input_fingerprint,
        "source_identities": source_identities or {},
        "producer_versions": producer_versions,
    }
    p = _results_path()
    tmp = p.with_name(p.name + ".tmp")

    if output_state.ensure_state_dir(ag_root(), commit_guard) != p.parent:
        raise ValueError("The organized Reports-vs-layers matrix state directory "
                         "is unavailable.")

    def _require_guard(path, action):
        if not consolidation_meta.guard_allows(commit_guard, path):
            raise ValueError(
                "A Reports-vs-layers matrix input or destination changed before "
                f"the {action}; refresh the comparison.")

    try:
        _require_guard(p.parent, "cache directory write")
        _require_guard(p, "cache write")
        _require_guard(tmp, "cache temporary write")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache_envelope.wrap(data, output_identity=_CACHE_IDENTITY), f)
        _require_guard(p, "cache publication")
        _require_guard(tmp, "cache publication")
        os.replace(tmp, p)
    except OSError as e:
        log.warning("arcgis_matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)
        raise ValueError(
            "The comparison workbook was created, but its Reports-vs-layers "
            "matrix result cache could not be safely published. Refresh the "
            "cell.") from e


# --------------------------------------------------------------------------- #
# the export side (a run folder's edition) — filesystem helpers
# --------------------------------------------------------------------------- #
_folder_newest_mtime = artifact_store.newest_report_file_mtime


def tsmis_dir(date, source, subdir):
    """The per-route export folder (one edition) the cell reads, resolved to the
    REAL run folder (CMP-AUD-092: a pre-v0.10 bare-date folder is found)."""
    return day_source_dir(date, source) / subdir


def _export_side(date, source, subdirs):
    """(subdir, folder, newest mtime) of the edition the cell reads for `date`:
    the first PRESENT edition in preference order. With none present the first
    edition's (absent) folder is returned with mtime None, so the cell still has
    a real path to fingerprint and reads "not exported"."""
    for sub in subdirs:
        d = tsmis_dir(date, source, sub)
        m = _folder_newest_mtime(d)
        if m is not None:
            return sub, d, m
    first = subdirs[0] if subdirs else "_none"
    return (subdirs[0] if subdirs else None), tsmis_dir(date, source, first), None


def _all_subdirs():
    subs = []
    for _rk, _label, _code, subdirs, _b, _c, _why in _ag_rows():
        subs += [s for s in subdirs if s not in subs]
    return subs


def available_days(source):
    """Dates (newest first) with an export of ANY comparable row's edition for
    `source` — the add-day picker's options. There is no export action on this
    matrix, so a day is offered only when something is on disk for it."""
    subs = _all_subdirs()
    out, seen = [], set()
    for name in list_output_days():
        parsed = parse_run_folder(name)
        if not parsed:
            continue
        date, src, env = parsed
        if f"{src}-{env}" != source or date in seen:
            continue
        base = day_source_dir(date, source)
        if any(_folder_newest_mtime(base / sub) is not None for sub in subs):
            seen.add(date)
            out.append(date)
    return out


def available_day_reports(source):
    """{date: [code, ...]} for every day `available_days` offers — which
    comparable reports are ACTUALLY exported that day (either edition), as the
    catalog's short codes in row order. The add-day picker's per-option tags."""
    rows = _ag_rows()
    present = artifact_store.exported_subdirs_by_day(source, _all_subdirs())
    out = {}
    for date, found in present.items():
        tags = [code for _rk, _label, code, subdirs, _b, _c, _why in rows
                if any(s in found for s in subdirs)]
        out[date] = tags
    return out


# --------------------------------------------------------------------------- #
# the library: ONE build per report, tied to the drop it was built from
# --------------------------------------------------------------------------- #
def _build_identity(path):
    """The built workbook's content identity (memoized per file in-process), or
    None when unreadable — a cell compared against it then reads stale rather
    than silently matching."""
    try:
        return artifact_store.content_digest(Path(path))
    except OSError as e:  # silent-ok: an unreadable build has no identity; the cell reads stale
        log.info("arcgis_matrix: build %s unreadable (%s: %s)", path,
                 type(e).__name__, e)
        return None


def build_state(key, drop=None, inventory=None):
    """The library entry for one report's SINGLE build: whether the lane can
    build it at all, whether it is built, its as-of date and record count, the
    drop it was built from and whether that is still the staged drop, and
    whether its outcome record makes it comparable right now."""
    s = arcgis_reports.spec(key)
    st = {"key": key, "label": s.label, "available": s.build is not None,
          "comparable": s.compare is not None and bool(s.exports),
          "why": s.why, "built": False}
    if s.build is None:
        return st
    inventory = inventory if inventory is not None else crl.inventory()
    st["missing_layers"] = [n for n in s.build.REQUIRED_LAYERS
                            if n not in inventory["present"]]
    path = Path(s.build.OUT_PATH)
    st["path"] = str(path)
    if not path.is_file():
        return st
    st["built"] = True
    st["mtime"] = matrix._safe_mtime(path)
    record = consolidation_meta.read_outcome(path)
    trusted = bool(record is not None and record.trusted and record.current)
    st["trusted"] = trusted
    st["completion"] = record.completion if record is not None else None
    extra = consolidation_meta.read_extra(path, s.build.SIDECAR_KEY, {}) or {}
    if not isinstance(extra, dict):
        extra = {}
    st["asof"] = extra.get("asof") or None
    st["rows"] = extra.get("rows")
    st["routes"] = extra.get("routes")
    rec_drop = extra.get("layer_drop") or {}
    if not isinstance(rec_drop, dict):
        rec_drop = {}
    st["drop_exported"] = rec_drop.get("exported") or None
    st["drop_fingerprint"] = rec_drop.get("fingerprint") or None
    current = (drop if drop is not None else arcgis_layers.drop_info()).get("fingerprint")
    st["drop_current"] = bool(current and st["drop_fingerprint"] == current)
    st["comparable_now"] = trusted and outcome.comparable(st["completion"])
    st["identity"] = _build_identity(path)
    if not st["comparable_now"]:
        st["stale"], st["stale_reason"] = True, "outcome_untrusted"
    elif not st["drop_current"]:
        st["stale"], st["stale_reason"] = True, "drop_changed"
    else:
        st["stale"], st["stale_reason"] = False, ""
    return st


def library_snapshot():
    """The layer library as the tab shows it: the staged drop's identity and
    stock vs the manifest, plus every registry report's build state."""
    drop = arcgis_layers.drop_info()
    inv = crl.inventory()
    return {
        "root": str(crl.root()),
        "drop": drop,
        "expected": len(crl.EXPECTED_LAYERS),
        "staged": len(inv["present"]),
        "missing": inv["missing"],
        "unknown": inv["unknown"],
        "index_present": inv["index"] is not None,
        "builds": {k: build_state(k, drop, inv) for k in arcgis_reports.KEYS},
    }


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def ag_matrix_snapshot(source, days, hidden=None, now=None, row_order=None,
                       today=None, library=None):
    """Full render model for the Reports-vs-layers by-day matrix. PURE stat —
    counts come from the cache, no workbook opened. `days` is the ordered date
    columns; `hidden` hides report rows; `row_order` is the user's drag order.
    Shape-compatible with the other by-day matrix snapshots so the GUI shares
    the cell render, plus `library` (the drop + every row's build state).

    A cell needs the report BUILT from the layers (a trusted, comparable
    outcome) and an export of it that day; a row the lane cannot compare yet
    renders unsupported with its reason."""
    now = now if now is not None else time.time()
    today = today if today is not None else today_str()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    all_rows = _ag_rows()
    rows = [r for r in all_rows if r[0] not in hidden]
    by_key = {r[0]: r for r in rows}
    rows = [by_key[k] for k in matrix.apply_order(list(by_key.keys()), row_order)]
    results = load_results()
    attempts = matrix.load_attempts(ag_root())
    library = library if library is not None else library_snapshot()
    builds = library.get("builds", {})

    cells = {}
    for row_key, _label, _code, subdirs, _buildable, comparable, why in rows:
        bs = builds.get(row_key, {})
        layers_ok = bool(bs.get("built") and bs.get("comparable_now"))
        per = {}
        for date in days:
            sub, export_dir, export_m = _export_side(date, source, subdirs)
            export = {"present": export_m is not None, "mtime": export_m,
                      "age_seconds": (now - export_m) if export_m is not None else None,
                      "subdir": sub}
            if not comparable:
                cmp = {"supported": False, "why": why}
            else:
                rec = results.get(f"{day_folder_name(date, source)}|{row_key}")
                srcs = [{"name": "layers", "present": layers_ok,
                         "mtime": bs.get("mtime"), "identity": bs.get("identity")},
                        {"name": "export", "present": export_m is not None,
                         "mtime": export_m}]
                cmp = matrix._cmp_state(day_out_path(date, source, row_key), srcs,
                                        rec, fp_folders=(export_dir,))
                attempt = matrix._last_attempt_for(
                    attempts, f"{row_key}|{source}", date, cmp)
                if attempt is not None:
                    cmp["last_attempt"] = attempt
            per[date] = {"export": export, "cmp": cmp}
        cells[row_key] = per

    return {
        "source": source,
        "sources": [{"key": k, "label": matrix.default_env_label(k)} for k in sources()],
        "days": days,
        "today": today,
        "rows": [r[0] for r in rows],
        "row_labels": {r[0]: r[1] for r in rows},
        "row_supported": {r[0]: r[5] for r in rows},
        "all_rows": [{"key": r[0], "label": r[1], "code": r[2], "supported": r[5],
                      "buildable": r[4], "why": r[6]} for r in all_rows],
        "hidden": sorted(hidden),
        "cells": cells,
        "library": library,
    }


# --------------------------------------------------------------------------- #
# the scoped rebuild list + one-cell build + the report build
# --------------------------------------------------------------------------- #
def cells_to_rebuild(snapshot, scope="stale", row=None, date=None):
    """[(date, row_key)] to (re)build, honoring scope. 'all' = every buildable
    cell; 'stale' = only missing/stale ones. Optional `row`/`date` filters drive
    the per-row / per-column rebuilds. Skips unsupported rows and cells missing
    a side."""
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        for d in snapshot["days"]:
            if date and d != date:
                continue
            cmp = snapshot["cells"][row_key][d]["cmp"]
            if not matrix.cell_buildable(cmp):    # CMP-AUD-103: shared predicate
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((d, row_key))
    return todo


def _require_row(row_key):
    if not arcgis_reports.is_report(row_key):
        raise ValueError(f"unknown Reports-vs-layers matrix row: {row_key}")
    return arcgis_reports.spec(row_key)


def build_cell(source, date, row_key, events, confirm_overwrite=None,
               force_consolidate=False, also_formulas=False, commit_guard=None):
    """Build ONE (day, report) comparison: consolidate that day's export of the
    report (reusing the day folder's persistent consolidated unless stale or
    `force_consolidate`), diff the report's SINGLE layer build against it via
    the report's registered comparator, write the VALUES workbook to the by-day
    store, and cache its counts.

    Returns the ConsolidateResult. Raises ValueError on an unknown or
    uncomparable row, an invalid date/source, a missing/untrusted build, or a
    day with no export of the report."""
    s = _require_row(row_key)
    if not (s.compare is not None and s.exports):
        raise ValueError(f"{s.label}: {s.why}.")
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(
            f"invalid date/source for the Reports-vs-layers matrix: {date!r} / {source!r}")
    bs = build_state(row_key)
    if not bs.get("built"):
        raise ValueError(f"Build {s.label} from the layers first — the comparison "
                         "reads it as the ArcGIS side.")
    if not bs.get("comparable_now"):
        raise ValueError(f"The {s.label} layer build's outcome record is missing "
                         "or untrusted — rebuild it before comparing.")
    sub, export_dir, export_m = _export_side(date, source, s.subdirs)
    if export_m is None:
        raise ValueError(f"No {s.label} export for {date} {source}.")
    out_path = day_out_path(date, source, row_key)

    # CMP-AUD-098: capture the export folder's identity BEFORE the consolidate→
    # compare chain reads it (same folder as the snapshot fingerprints); the
    # layer side is one file, carried as its content identity.
    fp_folders = (export_dir,)
    fp_before = matrix._cell_input_fingerprint(*fp_folders)
    layers_identity = bs.get("identity")
    build_path = Path(bs["path"])

    side_export, _comp = matrix._ensure_consolidated(
        export_dir, sub, events, force_consolidate, commit_guard=commit_guard)
    events.on_log(f"  {s.label}: layer build as of {bs.get('asof') or '?'} "
                  f"(drop exported {bs.get('drop_exported') or '?'}) vs the "
                  f"{date} {source} export ({sub})")
    result = s.compare.compare(
        str(build_path), str(side_export), out_path, events=events,
        confirm_overwrite=confirm_overwrite or (lambda _p: True),
        mode="values", commit_guard=commit_guard)
    if result.status == "ok" and out_path.exists():
        # CMP-AUD-082: refresh the live-formulas twin, or clear a stale prior one.
        matrix._settle_formulas_twin(
            lambda fp: s.compare.compare(
                str(build_path), str(side_export), fp, events=events,
                confirm_overwrite=lambda _p: True, mode="formulas",
                commit_guard=commit_guard),
            out_path, also_formulas, events,
            source_paths=(build_path, Path(side_export)), commit_guard=commit_guard)
        published = matrix._published_comparison_result(out_path, result)
        typed = published.comparison_outcome
        diff_cells = typed.counts.differing_cells
        one_sided = (typed.counts.side_a_only_rows + typed.counts.side_b_only_rows)
        record_result(
            date, source, row_key, typed.verdict, diff_cells, one_sided,
            matrix._safe_mtime(out_path), completion=typed.completion,
            input_fingerprint=matrix._fingerprint_for_record(
                fp_before, fp_folders, out_path.name, events),
            source_identities=({"layers": layers_identity}
                               if layers_identity else None),
            generation_id=published.artifact_generation.generation_id,
            producer_versions=matrix.producer_identity(),
            commit_guard=commit_guard)
    return result


def build_report(row_key, events, asof=None, confirm_overwrite=None):
    """Build (or rebuild) a report's SINGLE layer build. `asof` is the
    reconstruction date; empty means the staged drop's own export date — the
    layers as exported — never the TSN extract's date (that default belongs to
    the Clean Road vs TSN lane only).

    Gates on the report's OWN required layers, not the whole manifest. Returns
    the build's ConsolidateResult; raises ValueError for a row the lane cannot
    build, missing layers, or an unknown as-of."""
    s = _require_row(row_key)
    if s.build is None:
        raise ValueError(f"{s.label} cannot be built from the layers yet ({s.why}).")
    inv = crl.inventory()
    missing = [n for n in s.build.REQUIRED_LAYERS if n not in inv["present"]]
    if missing:
        raise ValueError(
            "The ArcGIS layer library is missing the layer(s) this report is "
            "built from:\n\n  " + "\n  ".join(missing)
            + "\n\nDrop those layer exports into the arcgis_layers folder and "
              "build again.")
    drop = arcgis_layers.drop_info()
    asof = (asof or "").strip() or drop.get("exported")
    if not asof:
        raise ValueError("The staged drop's export date is unknown — enter an "
                         "as-of date (YYYY-MM-DD) to build.")
    events.on_log(f"Building {s.label} from the ArcGIS layers as of {asof}"
                  + (f" (drop exported {drop['exported']})"
                     if drop.get("exported") else ""))
    return s.build.consolidate(events=events,
                               confirm_overwrite=confirm_overwrite or (lambda _p: True),
                               asof=asof)

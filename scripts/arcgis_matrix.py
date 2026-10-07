"""ArcGIS-tab "Reports vs ArcGIS" matrix engine (the by-day matrix against the
ArcGIS report builds), plus the ArcGIS reports library it reads.

The fifth matrix (2026-09-02; renamed from "Reports vs layers" in v0.47.0):
rows = every EXPORT EDITION of every TSMIS report in the `arcgis_reports`
registry — the Excel export and the print (PDF) edition are separate rows, and
the reports still waiting on a build are listed too, so the whole report set is
visible and says what is missing — columns = exported DAYS the user adds, each
cell = that day's consolidated export vs the report's ArcGIS build. Both sides
are TSMIS, so they should agree.

ONE ArcGIS build per report (owner decisions 2026-09-02 / 2026-10-05): the
build lives on the ArcGIS ▸ ArcGIS reports tab and is refreshed there in place,
and every row of the report — both editions, every day — compares against it
automatically: `arcgis_side(report)` is the newest ArcGIS build of that report,
so nothing on the matrix picks or builds it. Each build records the layer DROP
it came from (its export date + content fingerprint), so the library reads a
build out of date the moment the layers are refreshed. A build is a
reconstruction as of a date — the layers' own export date unless the owner sets
one — and the comparison's Notes state that date beside the export day, because
across a gap the comparison measures network change on top of any real
difference.

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
from collections import namedtuple
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
import paths
from paths import (comparisons_root, day_run_label, day_source_dir,
                   parse_run_folder, run_days_for, today_str)

log = logging.getLogger("tsmis.arcgis_matrix")

SOURCE_DEFAULT = "ssor-prod"
AG_DIRNAME = "arcgis-by-day"                 # under output/comparisons/
REPORTS_DIRNAME = "arcgis_reports"           # under output/ — the report builds
_RESULTS_FILE = "_results.json"
_CACHE_IDENTITY = "arcgis-by-day"
_BUILD_ATTEMPTS_KEY = "build"                # the builds' row in the attempts overlay
BUILD_OK = matrix.ATTEMPT_OK                 # record_build_attempt(key, BUILD_OK) clears it

# One matrix row: an export edition of a registry report. `subdirs` is the one
# export folder the cell reads (empty when the row cannot compare); `family` is
# the report whose ArcGIS build it is compared against.
Row = namedtuple("Row", "key label code subdirs buildable comparable why family")


# --------------------------------------------------------------------------- #
# rows + sources
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _ag_rows():
    """[Row] — one per export edition, family by family in registry order."""
    out = []
    for e in arcgis_reports.editions():
        out.append(Row(e.key, e.label, e.code, (e.subdir,) if e.comparable else (),
                       arcgis_reports.can_build(e.family), e.comparable, e.why,
                       e.family))
    return out


def _row_lookup():
    return {r.key: r for r in _ag_rows()}


def row_keys():
    """The valid row keys (the export editions), straight off the registry —
    no filesystem."""
    return set(arcgis_reports.edition_keys())


# --------------------------------------------------------------------------- #
# paths + the results cache
# --------------------------------------------------------------------------- #
def ag_root():
    return comparisons_root() / AG_DIRNAME


def day_folder_name(date, source):
    """The run-folder name the (date, source) column reads, TSMIS site tag
    included when the export recorded one (paths.day_run_label)."""
    return day_run_label(date, source)


def day_out_path(date, source, row_key):
    """The VALUES workbook for one (day, report). The basename embeds the report,
    the day and the source (M1-C) so two days' comparisons of one report can be
    open in Excel at once and a lifted file still says what it is — the day part
    is the run folder's own name, TSMIS site tag included (v0.49.0)."""
    name = day_folder_name(date, source)
    return ag_root() / name / f"{row_key}_vs_layers {name}.xlsx"


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
        raise ValueError("The organized Reports-vs-ArcGIS matrix state directory "
                         "is unavailable.")

    def _require_guard(path, action):
        if not consolidation_meta.guard_allows(commit_guard, path):
            raise ValueError(
                "A Reports-vs-ArcGIS matrix input or destination changed before "
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
            "The comparison workbook was created, but its Reports-vs-ArcGIS "
            "matrix result cache could not be safely published. Refresh the "
            "cell.") from e


# --------------------------------------------------------------------------- #
# the export side (a run folder's edition) — filesystem helpers
# --------------------------------------------------------------------------- #
_folder_newest_mtime = artifact_store.newest_report_file_mtime


def tsmis_dir(date, source, subdir):
    """The per-route export folder (one edition) the cell reads, resolved to the
    REAL run folder: the TSMIS site `source` points at now, else one from before
    the site was recorded (CMP-AUD-092: a pre-v0.10 bare-date folder is found)."""
    return day_source_dir(date, source) / subdir


def _export_side(date, source, subdirs):
    """(subdir, folder, newest mtime) of the edition the cell reads for `date`.
    A row is ONE edition, so `subdirs` holds its one folder (kept a sequence for
    the shape the rows share). Absent, the folder is still returned with mtime
    None, so the cell has a real path to fingerprint and reads "not exported"."""
    for sub in subdirs:
        d = tsmis_dir(date, source, sub)
        m = _folder_newest_mtime(d)
        if m is not None:
            return sub, d, m
    first = subdirs[0] if subdirs else "_none"
    return (subdirs[0] if subdirs else None), tsmis_dir(date, source, first), None


def _all_subdirs():
    subs = []
    for r in _ag_rows():
        subs += [s for s in r.subdirs if s not in subs]
    return subs


def available_days(source):
    """Dates (newest first) with an export of ANY comparable row's edition for
    `source` from the TSMIS site it points at now (or from before the site was
    recorded) — the add-day picker's options. There is no export action on this
    matrix, so a day is offered only when something is on disk for it."""
    subs = _all_subdirs()
    out = []
    for date, base in run_days_for(source):
        if any(_folder_newest_mtime(base / sub) is not None for sub in subs):
            out.append(date)
    return out


def available_day_reports(source):
    """{date: [code, ...]} for every day `available_days` offers — which
    comparable editions are ACTUALLY exported that day, as the catalog's short
    codes in row order. The add-day picker's per-option tags."""
    rows = _ag_rows()
    present = artifact_store.exported_subdirs_by_day(source, _all_subdirs())
    out = {}
    for date, found in present.items():
        out[date] = [r.code for r in rows if any(s in found for s in r.subdirs)]
    return out


# --------------------------------------------------------------------------- #
# the ArcGIS reports library: ONE build per report, tied to the drop it was
# built from, refreshed in place on the ArcGIS reports tab
# --------------------------------------------------------------------------- #
def reports_root():
    """The folder the report builds live in (output/arcgis_reports/). Clean
    Road Highway's CA HIGHWAYS workbook keeps its own folder; the builds' last
    refresh attempts are recorded here for every report."""
    return paths.OUTPUT_ROOT / REPORTS_DIRNAME


def load_build_attempts():
    """{report key: {status, reason, at}} — the last refresh of a report that
    did NOT land (failed or cancelled). A refresh that finishes clears it."""
    cells = matrix.load_attempts(reports_root()).get(_BUILD_ATTEMPTS_KEY)
    return dict(cells) if isinstance(cells, dict) else {}


def record_build_attempt(key, status, reason=None):
    """Remember (or clear, on `BUILD_OK`) the last refresh attempt of one
    report. Diagnostic state: a lost record only costs the tab its line."""
    return matrix.record_attempt(reports_root(), _BUILD_ATTEMPTS_KEY, key, status,
                                 reason=reason)
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


def build_state(key, drop=None, inventory=None, attempts=None):
    """The library entry for one report's SINGLE build: whether the lane can
    build it at all, whether it is built, its as-of date and record count, the
    drop it was built from and whether that is still the staged drop, whether
    its outcome record makes it comparable right now, and the last refresh
    that did not land (`last_attempt`, absent when the last one did)."""
    s = arcgis_reports.spec(key)
    st = {"key": key, "label": s.label, "code": s.code,
          "available": s.build is not None,
          "comparable": s.compare is not None and bool(s.exports),
          "why": s.why, "built": False,
          "editions": [{"key": e.key, "label": e.label, "code": e.code,
                        "comparable": e.comparable, "why": e.why}
                       for e in arcgis_reports.editions_of(key)]}
    if s.build is None:
        return st
    attempts = attempts if attempts is not None else load_build_attempts()
    if isinstance(attempts.get(key), dict):
        st["last_attempt"] = attempts[key]
    inventory = inventory if inventory is not None else crl.inventory()
    st["layers"] = list(s.build.REQUIRED_LAYERS)
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


def arcgis_side(key, drop=None, inventory=None, attempts=None):
    """The ArcGIS build a report's rows compare against: the newest ArcGIS build
    of that report. There is one per report, refreshed in place on the ArcGIS
    reports tab, so this is its build state — the one place to change if a
    report ever keeps more than one."""
    return build_state(key, drop, inventory, attempts)


def library_snapshot():
    """The layer library as the tab shows it: the staged drop's identity and
    stock vs the manifest, plus every registry report's ArcGIS build."""
    drop = arcgis_layers.drop_info()
    inv = crl.inventory()
    attempts = load_build_attempts()
    return {
        "root": str(crl.root()),
        "drop": drop,
        "expected": len(crl.EXPECTED_LAYERS),
        "staged": len(inv["present"]),
        "missing": inv["missing"],
        "unknown": inv["unknown"],
        "index_present": inv["index"] is not None,
        "builds": {k: arcgis_side(k, drop, inv, attempts)
                   for k in arcgis_reports.KEYS},
    }


def reports_snapshot():
    """The ArcGIS reports tab's render model: the layer library (drop identity +
    stock) and one row per registry report — its build, the editions compared
    against it, and the folder the builds live in. Pure filesystem."""
    lib = library_snapshot()
    rows = [lib["builds"][k] for k in arcgis_reports.KEYS]
    return {**lib, "reports": rows,
            "reports_root": str(reports_root()),
            "buildable": sum(1 for r in rows if r["available"]),
            "built": sum(1 for r in rows if r.get("built"))}


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def ag_matrix_snapshot(source, days, hidden=None, now=None, row_order=None,
                       today=None, library=None):
    """Full render model for the Reports-vs-ArcGIS by-day matrix. PURE stat —
    counts come from the cache, no workbook opened. `days` is the ordered date
    columns; `hidden` hides edition rows; `row_order` is the user's drag order.
    Shape-compatible with the other by-day matrix snapshots so the GUI shares
    the cell render, plus `library` (the drop + every report's ArcGIS build)
    and `row_family` (which report's build each row compares against).

    A cell needs the report's ArcGIS build (a trusted, comparable outcome) and
    an export of that edition that day; a row the lane cannot compare yet
    renders unsupported with its reason."""
    now = now if now is not None else time.time()
    today = today if today is not None else today_str()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    all_rows = _ag_rows()
    rows = [r for r in all_rows if r.key not in hidden]
    by_key = {r.key: r for r in rows}
    rows = [by_key[k] for k in matrix.apply_order(list(by_key.keys()), row_order)]
    results = load_results()
    attempts = matrix.load_attempts(ag_root())
    library = library if library is not None else library_snapshot()
    builds = library.get("builds", {})

    cells = {}
    for r in rows:
        bs = builds.get(r.family, {})
        arcgis_ok = bool(bs.get("built") and bs.get("comparable_now"))
        per = {}
        for date in days:
            sub, export_dir, export_m = _export_side(date, source, r.subdirs)
            export = {"present": export_m is not None, "mtime": export_m,
                      "age_seconds": (now - export_m) if export_m is not None else None,
                      "subdir": sub}
            if not r.comparable:
                cmp = {"supported": False, "why": r.why}
            else:
                rec = results.get(f"{day_folder_name(date, source)}|{r.key}")
                srcs = [{"name": "layers", "present": arcgis_ok,
                         "mtime": bs.get("mtime"), "identity": bs.get("identity")},
                        {"name": "export", "present": export_m is not None,
                         "mtime": export_m}]
                cmp = matrix._cmp_state(day_out_path(date, source, r.key), srcs,
                                        rec, fp_folders=(export_dir,))
                attempt = matrix._last_attempt_for(
                    attempts, f"{r.key}|{source}", date, cmp)
                if attempt is not None:
                    cmp["last_attempt"] = attempt
            per[date] = {"export": export, "cmp": cmp}
        cells[r.key] = per

    return {
        "source": source,
        "sources": matrix.day_source_options(sources()),
        "day_hosts": matrix.day_hosts(source, days),
        "days": days,
        "today": today,
        "rows": [r.key for r in rows],
        "row_labels": {r.key: r.label for r in rows},
        "row_supported": {r.key: r.comparable for r in rows},
        "row_family": {r.key: r.family for r in all_rows},
        "all_rows": [{"key": r.key, "label": r.label, "code": r.code,
                      "supported": r.comparable, "buildable": r.buildable,
                      "why": r.why, "family": r.family} for r in all_rows],
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
    """(edition, its report's resolved spec) for a matrix row key."""
    if not arcgis_reports.is_edition(row_key):
        raise ValueError(f"unknown Reports-vs-ArcGIS matrix row: {row_key}")
    e = arcgis_reports.edition(row_key)
    return e, arcgis_reports.spec(e.family)


def _require_report(key):
    if not arcgis_reports.is_report(key):
        raise ValueError(f"unknown ArcGIS report: {key}")
    return arcgis_reports.spec(key)


def build_cell(source, date, row_key, events, confirm_overwrite=None,
               force_consolidate=False, also_formulas=False, commit_guard=None):
    """Build ONE (day, edition) comparison: consolidate that day's export of the
    edition (reusing the day folder's persistent consolidated unless stale or
    `force_consolidate`), diff the report's ArcGIS build against it via the
    report's registered comparator, write the VALUES workbook to the by-day
    store, and cache its counts.

    Returns the ConsolidateResult. Raises ValueError on an unknown or
    uncomparable row, an invalid date/source, a missing/untrusted build, or a
    day with no export of the edition."""
    e, s = _require_row(row_key)
    if not e.comparable:
        raise ValueError(f"{e.label}: {e.why}.")
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(
            f"invalid date/source for the Reports-vs-ArcGIS matrix: {date!r} / {source!r}")
    bs = arcgis_side(e.family)
    if not bs.get("built"):
        raise ValueError(f"Build the {s.label} ArcGIS report first (ArcGIS ▸ ArcGIS "
                         "reports) — the comparison reads it as the ArcGIS side.")
    if not bs.get("comparable_now"):
        raise ValueError(f"The {s.label} ArcGIS report's outcome record is missing "
                         "or untrusted — refresh it before comparing.")
    sub, export_dir, export_m = _export_side(date, source, (e.subdir,))
    if export_m is None:
        raise ValueError(f"No {e.label} export for {date} {source}.")
    out_path = day_out_path(date, source, row_key)

    # CMP-AUD-098: capture the export folder's identity BEFORE the consolidate→
    # compare chain reads it (same folder as the snapshot fingerprints); the
    # ArcGIS side is one file, carried as its content identity.
    fp_folders = (export_dir,)
    fp_before = matrix._cell_input_fingerprint(*fp_folders)
    layers_identity = bs.get("identity")
    build_path = Path(bs["path"])

    side_export, _comp = matrix._ensure_consolidated(
        export_dir, sub, events, force_consolidate, commit_guard=commit_guard)
    events.on_log(f"  {e.label}: the {date} {source} export vs the ArcGIS report "
                  f"as of {bs.get('asof') or '?'} (layers exported "
                  f"{bs.get('drop_exported') or '?'})")
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
    """Build (or refresh) a report's SINGLE ArcGIS build. `row_key` is the
    REPORT (registry family) key. `asof` is the reconstruction date; empty
    means the staged drop's own export date — the layers as exported — never
    the TSN extract's date (that default belongs to the Clean Road vs TSN lane
    only).

    Gates on the report's OWN required layers, not the whole manifest. The
    default as-of is the OLDEST export date among those layers (v0.46.0: a
    partly refreshed library records each layer's own export time) — never a
    date later than one of its layers was read. Returns the build's
    ConsolidateResult; raises ValueError for a report the lane cannot build,
    missing layers, or an unknown as-of."""
    s = _require_report(row_key)
    if s.build is None:
        raise ValueError(f"{s.label} cannot be built from the layers yet ({s.why}).")
    inv = crl.inventory()
    missing = [n for n in s.build.REQUIRED_LAYERS if n not in inv["present"]]
    if missing:
        raise ValueError(
            "The ArcGIS layer library is missing the layer(s) this report is "
            "built from:\n\n  " + "\n  ".join(missing)
            + "\n\nRefresh them on the ArcGIS ▸ Layers tab and build again.")
    drop = arcgis_layers.drop_info()
    asof = (asof or "").strip() or arcgis_layers.consistent_asof(
        s.build.REQUIRED_LAYERS, drop)
    if not asof:
        raise ValueError("The layer library's export date is unknown — enter an "
                         "as-of date (YYYY-MM-DD) to build.")
    events.on_log(f"Building {s.label} from the ArcGIS layers as of {asof}"
                  + (f" (drop exported {drop['exported']})"
                     if drop.get("exported") else ""))
    return s.build.consolidate(events=events,
                               confirm_overwrite=confirm_overwrite or (lambda _p: True),
                               asof=asof)

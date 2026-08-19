"""Compare-tab "vs Baseline" matrix engine (day-vs-baseline comparisons).

A MANUAL, day-picking comparison matrix (a sibling of the "vs TSN" by-day
matrix): rows = report types, columns = exported DAYS the user adds, each cell =
that day's per-route export compared against a BASELINE copy of the SAME report
— an earlier day's run folder, or the Export-Everything store ("All Reports
(current)") for the same source. Same-format by construction: each row's
compare_env adapter reads the report's own subdir on BOTH sides (an Excel row
reads Excel per-route files, a PDF row parses the PDF exports), so an Excel
edition can never be diffed against a PDF baseline.

There is NO consolidation step and NO TSN dataset here: compare_folders reads
the per-route files straight from both folders — the classic Compare tab's
"export folders" path, matrix-ified — and the produced workbook is the same
approved discrepancy workbook every other comparison writes. One data source
for the whole matrix (default ssor-prod); no live re-export (it compares
HISTORICAL exports; the vs TSN matrix owns exporting today's column).

Console-free like the rest of the core: progress via the Events sink,
exceptions raised — never print/input/sys.exit. Only gui_api / gui_worker
drive it.
"""
import json
import logging
import os
import re
import time
from pathlib import Path

import artifact_store   # CMP-AUD-083: the shared accepted-data-file predicate
import cache_envelope
import consolidation_meta
import matrix
import outcome
import reports
import output_state
from events import ConsolidateResult
from paths import (OUTPUT_ROOT, day_source_dir, list_output_days,
                   parse_run_folder)

log = logging.getLogger("tsmis.baseline_matrix")

SOURCE_DEFAULT = "ssor-prod"
BASELINE_BYDAY_DIRNAME = "baseline-by-day"     # under output/comparisons/
STORE_BASELINE = "store"                       # the Export-Everything store id
_DAY_PREFIX = "day:"
_RESULTS_FILE = "_results.json"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --------------------------------------------------------------------------- #
# rows + sources + baseline identity
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (the matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _rows():
    """[(row_key, label, subdir, supported)] — every cross-env matrix row (all 13
    report types as of v0.37.0; `supported` mirrors the CROSS-ENV adapter's
    presence — NOT vs-TSN support — so a future adapter-less row greys instead of
    crashing. Highway Summary is supported here despite having no TSN comparator:
    a baseline comparison diffs two pulls of the SAME report, which needs only the
    cross-env adapter it has)."""
    return [(row_key, label, subdir, adapter is not None)
            for row_key, label, subdir, _idx, adapter in reports.matrix_rows()]


def _row_lookup():
    return {r[0]: r for r in _rows()}


def row_keys():
    """The valid row keys, straight off the registry — no filesystem, no TSN
    library. Validation-only callers (show/hide a report, persist a row order)
    used to read `baseline_matrix_snapshot()["all_rows"]` for exactly this set, which
    dragged a full stat pass through every chip click; the row catalog never
    depended on any of it."""
    return {r[0] for r in _rows()}


def parse_baseline(baseline_id):
    """("day", "<date>") / ("store", None) from a baseline id, or None for an
    unset/unknown id. The date shape is checked here; whether "<date> <source>"
    is a REAL run folder is checked where the source is known (the boundary)."""
    if baseline_id == STORE_BASELINE:
        return ("store", None)
    if (isinstance(baseline_id, str) and baseline_id.startswith(_DAY_PREFIX)
            and _DATE_RE.fullmatch(baseline_id[len(_DAY_PREFIX):])):
        return ("day", baseline_id[len(_DAY_PREFIX):])
    return None


def baseline_token(baseline_id):
    """The filename-safe token a cell workbook carries for its baseline
    ("store", or the baseline date)."""
    parsed = parse_baseline(baseline_id)
    if parsed is None:
        return None
    kind, date = parsed
    return STORE_BASELINE if kind == "store" else date


def baseline_dir(source, baseline_id, dest):
    """The folder holding the baseline side's report subdirs: a run folder for a
    day baseline, or the store's <dest>/<source>/ live folder. None for an
    unset/invalid id (callers render "pick a baseline")."""
    parsed = parse_baseline(baseline_id)
    if parsed is None:
        return None
    kind, date = parsed
    if kind == "store":
        return Path(dest) / source if dest else None
    if not parse_run_folder(day_folder_name(date, source)):
        return None
    return day_source_dir(date, source)      # CMP-AUD-092: real folder (legacy incl.)


def baseline_label(source, baseline_id):
    """The side label a cell comparison carries for its baseline (capped by
    compare_env; distinct from the day side's "<SOURCE> <date>")."""
    parsed = parse_baseline(baseline_id)
    if parsed is None:
        return None
    kind, date = parsed
    return (f"{source.upper()} (store)" if kind == "store"
            else f"{source.upper()} {date}")


# --------------------------------------------------------------------------- #
# paths + the results cache
# --------------------------------------------------------------------------- #
def byday_root():
    return OUTPUT_ROOT / matrix.COMPARISONS_DIRNAME / BASELINE_BYDAY_DIRNAME


def day_folder_name(date, source):
    return f"{date} {source}"


def out_path(date, source, row_key, baseline_id):
    """The comparison VALUES workbook for one (day, report) vs one baseline.

    The name carries the day + source + baseline token, so it is unique both
    across baselines (switching baselines never clobbers the other's) AND across
    day columns — two days' comparisons of the same report open in Excel together
    (which refuses duplicate basenames; M1-B/c12). Still stable per cell (`date`
    is the cell's column, not today), so mtime freshness is unchanged. (Pre-v0.30
    cells used `<row>_vs_<token>.xlsx`; they rebuild once under the new name.)"""
    token = baseline_token(baseline_id)
    return (byday_root() / day_folder_name(date, source)
            / f"{row_key}_vs_{token} {date} {source}.xlsx")


def _results_path():
    return output_state.state_file(byday_root(), _RESULTS_FILE)


def _results_read_path():
    return output_state.named_read_file(byday_root(), _RESULTS_FILE)


def load_results():
    """{ "<date source>|<row>|<baseline-id>": {verdict, diff_cells, one_sided,
    built_at_mtime, completion, input_fingerprint} }. Tolerant: missing/corrupt
    -> {} (never raises)."""
    p = _results_read_path()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return cache_envelope.unwrap(data, output_identity="baseline-by-day")
    except OSError:  # silent-ok: not written yet (first run) — the expected empty-cache state
        return {}
    except ValueError as e:                  # corrupt JSON: surface it, then degrade
        log.warning("baseline_matrix: corrupt results cache %s (%s: %s); "
                    "treating as empty", p, type(e).__name__, e)
        return {}


def _result_key(date, source, row_key, baseline_id):
    return f"{day_folder_name(date, source)}|{row_key}|{baseline_id}"


def record_result(date, source, row_key, baseline_id, verdict, diff_cells,
                  one_sided, built_at_mtime, completion=None,
                  input_fingerprint=None, generation_id=None,
                  producer_versions=None):
    data = load_results()
    data[_result_key(date, source, row_key, baseline_id)] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
        "completion": completion,
        "generation_id": generation_id,
        # Both sides are multi-file folders, so the identity fingerprint covers
        # BOTH (a route deleted on either side hides from the mtime check).
        "input_fingerprint": input_fingerprint,
        # CMP-AUD-084: the semantic producer version — a shipped comparator/parser
        # change reads the cell stale via the shared matrix._staleness gate.
        "producer_versions": producer_versions,
    }
    p = _results_path()
    if output_state.ensure_state_dir(byday_root()) != p.parent:
        raise ValueError("The organized baseline Matrix state directory is unavailable.")

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache_envelope.wrap(data, output_identity="baseline-by-day"), f)
        os.replace(tmp, p)
    except OSError as e:
        log.warning("baseline_matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)
        raise ValueError(
            "The comparison workbook was created, but its baseline result cache "
            "could not be safely published. Refresh the cell.") from e


# --------------------------------------------------------------------------- #
# filesystem helpers
# --------------------------------------------------------------------------- #
def _folder_newest_mtime(p):
    """Newest report-data-file mtime in a folder, or None when empty/absent.
    CMP-AUD-083: only a real .xlsx/.pdf export counts — a folder holding only a
    lock, sidecar, or notes file is NOT an export and never a fresher signal."""
    newest = None
    try:
        entries = list(Path(p).iterdir())
    except OSError:  # silent-ok: an absent/unreadable folder IS the "no export" answer
        return None
    for e in entries:
        try:
            if e.is_file() and artifact_store.is_report_data_file(e.name):
                m = e.stat().st_mtime
                if newest is None or m > newest:
                    newest = m
        except OSError:  # silent-ok: a locked/vanished entry contributes nothing
            continue
    return newest


def tsmis_dir(date, source, subdir):
    """The per-route export the cell compares, resolved to the REAL run folder
    (CMP-AUD-092: a pre-v0.10 legacy bare-date folder included)."""
    return day_source_dir(date, source) / subdir


def available_days(source):
    """Dates (newest first) under output/ that have an export for ANY matrix
    report for `source` — the add-day AND baseline pickers' day options. No
    "today" special: this matrix compares historical exports only (the vs TSN
    matrix owns exporting today's column)."""
    subs = [r[2] for r in _rows() if r[3]]
    out, seen = [], set()
    for name in list_output_days():
        parsed = parse_run_folder(name)
        if not parsed:
            continue
        date, src, env = parsed
        if f"{src}-{env}" != source or date in seen:
            continue
        base = OUTPUT_ROOT / name
        if any(_folder_newest_mtime(base / sub) is not None for sub in subs):
            seen.add(date)
            out.append(date)
    return out


def _present_count(folder, rows):
    """How many of the matrix reports have files under `folder` (per-day /
    store coverage shown in the baseline picker)."""
    if folder is None:
        return 0
    return sum(1 for _k, _l, sub, ok in rows if ok
               and _folder_newest_mtime(Path(folder) / sub) is not None)


def baseline_options(source, dest):
    """The baseline picker's options: the Export-Everything store (when it holds
    anything for this source) + every exported day, each with how many of the
    matrix reports it covers — the "which days have an old copy" answer."""
    rows = _rows()
    total = sum(1 for r in rows if r[3])
    opts = []
    store_dir = Path(dest) / source if dest else None
    store_n = _present_count(store_dir, rows)
    if store_n:
        opts.append({"id": STORE_BASELINE, "label": "All Reports store",
                     "present": store_n, "total": total})
    for date in available_days(source):
        n = _present_count(day_source_dir(date, source), rows)
        opts.append({"id": f"{_DAY_PREFIX}{date}", "label": date,
                     "present": n, "total": total})
    return opts


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def baseline_matrix_snapshot(source, days, baseline_id, hidden=None, dest=None,
                             now=None, row_order=None):
    """Full render model for the vs-Baseline matrix. PURE stat — no workbook
    opened (counts come from the cache). `days` is the ordered list of date
    columns; `baseline_id` is "store" / "day:<date>" / None (unset — cells
    render pick-a-baseline); `hidden` hides report rows; `row_order` is the
    user's drag-to-reorder preference; `dest` is the Everything store root (the
    "store" baseline lives under it)."""
    now = now if now is not None else time.time()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    all_rows = _rows()
    rows = [r for r in all_rows if r[0] not in hidden]
    by_key = {r[0]: r for r in rows}
    rows = [by_key[k] for k in matrix.apply_order(list(by_key.keys()), row_order)]
    results = load_results()

    parsed = parse_baseline(baseline_id)
    bdir = baseline_dir(source, baseline_id, dest)
    bl_date = parsed[1] if parsed and parsed[0] == "day" else None
    # Per-row baseline presence: which reports the baseline actually holds —
    # the per-report half of "which days have an old copy of this report".
    bl_rows = {}
    for row_key, _label, subdir, supported in rows:
        m = _folder_newest_mtime(bdir / subdir) if (bdir and supported) else None
        bl_rows[row_key] = {"present": m is not None, "mtime": m}

    cells = {}
    attempts = matrix.load_attempts(byday_root())
    for row_key, _label, subdir, supported in rows:
        per = {}
        for date in days:
            tdir = tsmis_dir(date, source, subdir)
            exp_m = _folder_newest_mtime(tdir)
            export = {"present": exp_m is not None, "mtime": exp_m,
                      "age_seconds": (now - exp_m) if exp_m is not None else None}
            if not supported:
                cmp = {"supported": False}
            elif date == bl_date:
                # the baseline's own column: nothing to compare against itself
                cmp = {"supported": True, "is_baseline": True}
            else:
                bl = bl_rows[row_key]
                rec = results.get(_result_key(date, source, row_key, baseline_id)) \
                    if parsed else None
                srcs = [{"name": "cell", "present": exp_m is not None, "mtime": exp_m},
                        {"name": "baseline", "present": bool(bl["present"]),
                         "mtime": bl["mtime"]}]
                # BOTH sides are multi-file folders — fingerprint both so a route
                # deleted on either side reads the cell stale (F5/P2).
                cmp = matrix._cmp_state(
                    out_path(date, source, row_key, baseline_id) if parsed else "",
                    srcs, rec,
                    fp_folders=(tdir, bdir / subdir) if bdir else (tdir,))
                # CMP-AUD-089: render the durable last-attempt overlay here too.
                attempt = matrix._last_attempt_for(
                    attempts, f"{row_key}|{source}|{baseline_id}", date, cmp)
                if attempt is not None:
                    cmp["last_attempt"] = attempt
            per[date] = {"export": export, "cmp": cmp}
        cells[row_key] = per

    return {
        "source": source,
        "sources": [{"key": k, "label": matrix.default_env_label(k)} for k in sources()],
        "days": days,
        "baseline": {
            "id": baseline_id if parsed else None,
            "kind": parsed[0] if parsed else None,
            "date": bl_date,
            "label": baseline_label(source, baseline_id) if parsed else None,
            "dir": str(bdir) if bdir else None,
            "present": bl_rows,
        },
        "rows": [r[0] for r in rows],
        "row_labels": {r[0]: r[1] for r in rows},
        "row_supported": {r[0]: r[3] for r in rows},
        "all_rows": [{"key": r[0], "label": r[1], "supported": r[3]} for r in all_rows],
        "hidden": sorted(hidden),
        "cells": cells,
    }


# --------------------------------------------------------------------------- #
# the scoped rebuild list + one-cell build
# --------------------------------------------------------------------------- #
def cells_to_rebuild(snapshot, scope="stale", row=None, date=None):
    """[(date, row_key)] to (re)build, honoring scope. 'all' = every supported
    cell with both sides present; 'stale' = only missing/stale ones. Optional
    `row` / `date` filters drive the per-row and per-column rebuilds. Skips
    greyed rows, the baseline's own column, and cells missing either side."""
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        for d in snapshot["days"]:
            if date and d != date:
                continue
            cmp = snapshot["cells"][row_key][d]["cmp"]
            # CMP-AUD-103: shared buildability predicate (+ the baseline's own column).
            if cmp.get("is_baseline") or not matrix.cell_buildable(cmp):
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((d, row_key))
    return todo


def build_baseline_cell(source, date, row_key, baseline_id, dest, events,
                        confirm_overwrite=None, also_formulas=False,
                        evidence=None):
    """Build ONE (day, report) vs-baseline comparison: side A = the day's run
    folder, side B = the baseline (an earlier run folder or the store), compared
    by the row's own compare_env adapter — per-route files read straight from
    both folders, no consolidation. Writes the VALUES workbook to the
    baseline-by-day store (atomic commit; F9) and caches its counts. Returns the
    ConsolidateResult. Raises ValueError on an unknown/greyed row, a bad
    date/baseline, or the baseline's own day.

    `evidence` ({'enabled','examples','layout'}) requests the visual-evidence
    decoration on the `_pdf`-family rows (v0.38.3). Both sides here are per-route
    TSMIS prints from two folders — structurally the SAME pair the cross-
    environment lane illustrates, only picked by DAY instead of by environment —
    so it rides `visual_evidence`'s env flavor unchanged, sources bound to the
    comparison's own recorded provenance. Additive, never a gate: the comparison
    result is identical with it on or off."""
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown baseline-matrix row: {row_key}")
    # Validate date+source at the boundary so neither can traverse out of
    # output/ even if the settings file was hand-edited.
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(f"invalid date/source for the baseline matrix: "
                         f"{date!r} / {source!r}")
    _k, _label, subdir, supported = rows[row_key]
    if not supported:
        raise ValueError(f"no cross-environment adapter for {row_key} yet")
    parsed = parse_baseline(baseline_id)
    if parsed is None:
        raise ValueError("no baseline picked yet")
    bdir = baseline_dir(source, baseline_id, dest)
    if bdir is None:
        raise ValueError(f"invalid baseline for the baseline matrix: {baseline_id!r}")
    if parsed == ("day", date):
        raise ValueError("that day IS the baseline — nothing to compare")
    adapter = {r[0]: r[4] for r in reports.matrix_rows()}[row_key]

    dir_a = day_source_dir(date, source)     # CMP-AUD-092: real folder (legacy incl.)
    dest_path = out_path(date, source, row_key, baseline_id)
    labels = (f"{source.upper()} {date}", baseline_label(source, baseline_id))
    source_paths = (dir_a, bdir)
    # CMP-AUD-098: capture the input identity BEFORE the comparator reads.
    fp_folders = (tsmis_dir(date, source, subdir), bdir / subdir)
    fp_before = matrix._cell_input_fingerprint(*fp_folders)

    # side A = the day under test, side B = the baseline (labels read
    # "SSOR-PROD 2026-07-09 vs SSOR-PROD 2026-06-20"). The public adapter owns
    # the single atomic transaction; a redundant outer transaction would reject
    # the adapter's legitimate inner publication as a temp-identity replacement.
    result = adapter.compare_folders(
        dir_a, bdir, dest_path, events=events,
        confirm_overwrite=confirm_overwrite or (lambda _p: True),
        mode="values", labels=labels)
    if (also_formulas and result.status == "ok"
            and matrix._twin_inputs_unchanged(fp_before, fp_folders,
                                              dest_path.name, events)):
        matrix._settle_formulas_twin(lambda fp: adapter.compare_folders(
            dir_a, bdir, fp, events=events,
            confirm_overwrite=lambda _p: True, mode="formulas", labels=labels),
            dest_path, True, events, source_paths=source_paths)
    elif result.status == "ok":
        # CMP-AUD-082: values-only / inputs-changed refresh -> clear a stale twin.
        matrix._clear_stale_formulas_twin(dest_path, events, source_paths=source_paths)

    if result.status == "ok" and dest_path.exists():
        published = matrix._published_comparison_result(dest_path, result)
        typed = published.comparison_outcome
        diff_cells = typed.counts.differing_cells
        one_sided = (typed.counts.side_a_only_rows
                     + typed.counts.side_b_only_rows)
        try:
            built_at = dest_path.stat().st_mtime
        except OSError:  # silent-ok: no mtime just means the cached record can't certify freshness
            built_at = None
        # CMP-AUD-098: the PRE-comparison capture is recorded — a mid-build
        # mutation therefore reads immediately stale, never fresh.
        record_result(date, source, row_key, baseline_id, typed.verdict,
                      diff_cells, one_sided, built_at,
                      completion=typed.completion,
                      input_fingerprint=matrix._fingerprint_for_record(
                          fp_before, fp_folders, dest_path.name, events),
                      generation_id=published.artifact_generation.generation_id,
                      producer_versions=matrix.producer_identity())
        matrix._run_env_evidence(row_key, dest_path, evidence, events, result,
                                 None)
    return result


def run_baseline_evidence_only(source, date, row_key, baseline_id, dest, events,
                               examples=None, layout=None):
    """On-demand evidence for ONE vs-Baseline cell's EXISTING comparison (the
    per-cell camera). Compares nothing; the freshness gates mirror the
    Everything matrix's env camera exactly — the comparison must exist with a
    trusted, current, COMPLETE committed generation whose id matches this
    matrix's own cache, and neither side's export folder may have changed since
    it was built. The two compared folders come from the comparison's own
    recorded provenance inside the generator (the exact-source rule), never from
    anything recomputed here."""
    import visual_evidence
    if not visual_evidence.env_capable(row_key):
        raise ValueError("this report doesn't support evidence images")
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown baseline-matrix row: {row_key}")
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(f"invalid date/source for the baseline matrix: "
                         f"{date!r} / {source!r}")
    _k, _label, subdir, supported = rows[row_key]
    if not supported:
        raise ValueError(f"no cross-environment adapter for {row_key} yet")
    parsed = parse_baseline(baseline_id)
    if parsed is None:
        raise ValueError("no baseline picked yet")
    if parsed == ("day", date):
        raise ValueError("that day IS the baseline — nothing to illustrate")
    bdir = baseline_dir(source, baseline_id, dest)
    if bdir is None:
        raise ValueError(f"invalid baseline for the baseline matrix: {baseline_id!r}")

    dest_path = out_path(date, source, row_key, baseline_id)
    if not dest_path.exists():
        raise ValueError("build the comparison first — evidence illustrates an "
                         "existing comparison")
    record = consolidation_meta.read_comparison_outcome(dest_path)
    if (record is None or not record.trusted or not record.current
            or record.comparison_outcome is None):
        raise ValueError("the comparison workbook has no trusted, current "
                         "generation record — refresh the comparison first")
    generation = record.artifact_generation
    cached = load_results().get(_result_key(date, source, row_key, baseline_id))
    if (not cached or generation is None
            or cached.get("generation_id") != generation.generation_id):
        raise ValueError("the comparison is not the one the matrix recorded — "
                         "refresh the comparison first")
    if record.comparison_outcome.completion != outcome.COMPLETE:
        raise ValueError(matrix._partial_comparison_reason(
            record.comparison_outcome))
    # The export-changed gate ALWAYS evaluates: a cell cached before fingerprints
    # were recorded refuses rather than skipping the gate (the env camera's rule).
    fp_folders = (tsmis_dir(date, source, subdir), bdir / subdir)
    if cached.get("input_fingerprint") is None:
        raise ValueError("the matrix cache records no input fingerprint for "
                         "this comparison — refresh the comparison first")
    if matrix._cell_input_fingerprint(*fp_folders) != cached.get("input_fingerprint"):
        raise ValueError("the exports changed since the comparison was built — "
                         "refresh the comparison first")

    ev = visual_evidence.generate(
        row_key, None, None, dest_path, None, events,
        examples=visual_evidence.clamp_examples(examples),
        layout=visual_evidence.normalize_layout(layout),
        flavor=visual_evidence.FLAVOR_ENV)
    # The same post-render generation re-check the other cameras make: a refresh
    # landing mid-render would leave images of generation N under a manifest
    # digesting generation N+1.
    after = consolidation_meta.read_comparison_outcome(dest_path)
    if (after is None or not after.trusted
            or after.artifact_generation != record.artifact_generation):
        raise ValueError(
            "the comparison generation changed while evidence was rendering — "
            "refresh the comparison and evidence")
    note = ev.get("note") or "evidence run finished"
    return ConsolidateResult(status="ok", message=note, summary_lines=[note])


def evidence_path(date, source, row_key, baseline_id):
    """The '(evidence).xlsx' sibling of one cell's comparison, or None when the
    cell identity doesn't resolve. Existence is the caller's question."""
    if not parse_baseline(baseline_id) or row_key not in _row_lookup():
        return None
    if not parse_run_folder(day_folder_name(date, source)):
        return None
    import visual_evidence
    return visual_evidence.sibling_paths(out_path(date, source, row_key,
                                                  baseline_id))[0]

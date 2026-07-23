"""Compare-tab "vs TSN Matrix" engine (the day-keyed TSN comparison matrix).

A MANUAL, day-picking comparison matrix (a sibling of the Everything matrix, but
under the Compare tab): rows = report types, columns = exported DAYS the user
adds, each cell = that report's export FOR THAT DAY compared vs TSN. There is ONE
data source for the whole matrix (default ssor-prod); no cross-environment and no
live re-export — it compares specific HISTORICAL exports the user already pulled.

It SHARES the TSN compare path (`matrix.consolidate_and_compare_tsn`) and the TSN
dataset (`matrix.tsn_source`, now backed by the canonical TSN library and resolved
by each row's own `tsn_subdir`, with the user's `matrix_tsn_files` pick as an
override) with the Everything matrix — only the TSMIS source folder (a specific run
folder under output/) and the output store differ.

The matrix lists EVERY report so it's the single place TSN comparisons surface. As
of v0.17.0 ALL reports are wired (Highway Log Excel/PDF, Ramp Summary/Detail,
Highway Sequence, Intersection Summary/Detail) — each row's `supported` flag comes
from `matrix.tsn_supported()`, so adding a report's TSN comparator flips it on here
automatically; nothing is greyed. The store, snapshot, actions, and queue are
report-agnostic; the per-row `tsn_subdir` (from `matrix.tsn_subdir_for`) carries
each report's TSN dataset key — the old Highway-Log-only `TSN_SUBDIR` constant is gone.

Console-free like the rest of the core: progress via the Events sink, exceptions
raised — never print/input/sys.exit. Only gui_api / gui_worker drive it.
"""
import json
import logging
import os
import time
from pathlib import Path

import artifact_store   # CMP-AUD-083: the shared accepted-data-file predicate
import cache_envelope
import consolidation_meta
import matrix
import reports
from paths import (OUTPUT_ROOT, day_source_dir, list_output_days,
                   parse_run_folder, today_str)

log = logging.getLogger("tsmis.day_matrix")

SOURCE_DEFAULT = "ssor-prod"
BYDAY_DIRNAME = "tsn-by-day"          # under output/comparisons/
_RESULTS_FILE = "_results.json"


# --------------------------------------------------------------------------- #
# rows + sources
# --------------------------------------------------------------------------- #
def sources():
    """The data-source options (the matrix columns are days WITHIN one source)."""
    return matrix.env_keys()


def _day_rows():
    """[(row_key, label, subdir, fmt, supported, tsn_subdir)] for the vs-TSN matrix
    — EVERY report, so the matrix is the single place all TSN comparisons surface.
    As of v0.17.0 every report has a coded TSN comparator: each row's `supported`
    flag derives from `matrix.tsn_supported(row_key)` (the two Highway Log rows also
    carry an explicit fmt — Excel-vs-TSN / PDF-vs-TSN), so nothing is greyed.

    `tsn_subdir` is the report's TSN dataset key (from matrix.tsn_subdir_for): both
    Highway Log rows share 'highway_log'; every other report uses its own subdir.

    Plug-in contract: a new report flips on automatically once it has a TSN
    comparator (matrix.tsn_comparator_for) + a per-report TSN dataset — the matrix
    shell, store, actions, and snapshot are report-agnostic and resolve TSN per
    `tsn_subdir`, and build_day_cell dispatches generically."""
    out = []
    for row_key, label, subdir, _idx, adapter in reports.matrix_rows():
        tsn_subdir = matrix.tsn_subdir_for(row_key, subdir, adapter)
        # `supported` ALWAYS derives from the single tsn_supported registry
        # (CMP-AUD-013) — the two Highway Log rows + the five PDF rows differ only
        # in their explicit fmt, never in whether support is hardcoded. Patching
        # tsn_comparator_for now flips every row here; no hand-written True shadows
        # it. Every report has a coded comparator today, so all rows stay live.
        if row_key == "highway_log":
            out.append((row_key, label, subdir, "excel",
                        matrix.tsn_supported(row_key), tsn_subdir))
        elif row_key in ("highway_log_pdf", "intersection_detail_pdf",
                         "highway_detail_pdf", "highway_sequence_pdf",
                         "ramp_detail_pdf"):
            out.append((row_key, label, subdir, "pdf",
                        matrix.tsn_supported(row_key), tsn_subdir))
        else:
            out.append((row_key, label, subdir, None,
                        matrix.tsn_supported(row_key), tsn_subdir))
    # Reports with no cross-env adapter (absent from matrix_rows) still get a
    # by-day vs-TSN row here. EMPTY today — every report has an env adapter —
    # kept as the documented extension point for a future export-only report.
    for row_key, label, subdir in reports.tsn_matrix_extra_rows():
        out.append((row_key, label, subdir, None,
                    matrix.tsn_supported(row_key),
                    matrix.tsn_subdir_for(row_key, subdir, None)))
    return out


def _row_lookup():
    return {r[0]: r for r in _day_rows()}


# --------------------------------------------------------------------------- #
# paths + the by-day results cache
# --------------------------------------------------------------------------- #
def byday_root():
    return OUTPUT_ROOT / matrix.COMPARISONS_DIRNAME / BYDAY_DIRNAME


def day_folder_name(date, source):
    return f"{date} {source}"


def day_out_path(date, source, row_key):
    """The comparison VALUES workbook for one (day, report) vs TSN.

    The basename embeds the day + source — not just the parent folder — so two
    days' comparisons of the SAME report can be open in Excel at once (Excel
    refuses two workbooks with the same basename, even from different folders;
    M1-B/c12). The name is still STABLE per cell: `date` is the cell's own column,
    never today, so the overwrite-in-place + mtime-freshness model is unchanged.
    (Pre-v0.30 cells used the dateless `<row>_vs_tsn.xlsx`; they read as
    not-built once and rebuild under the new name.)"""
    return (byday_root() / day_folder_name(date, source)
            / f"{row_key}_vs_tsn {date} {source}.xlsx")


def _results_path():
    return byday_root() / _RESULTS_FILE


def load_results():
    """{ "<date source>|<row>": {verdict, diff_cells, one_sided, built_at_mtime} }.
    Tolerant: missing/corrupt -> {} (never raises)."""
    try:
        with open(_results_path(), encoding="utf-8") as f:
            data = json.load(f)
        return cache_envelope.unwrap(data, output_identity="tsn-by-day")
    except OSError:
        return {}                            # not written yet (first run) — expected
    except ValueError as e:                  # corrupt JSON: surface it, then degrade
        log.warning("day_matrix: corrupt results cache %s (%s: %s); treating as empty",
                    _results_path(), type(e).__name__, e)
        return {}


def record_result(date, source, row_key, verdict, diff_cells, one_sided,
                  built_at_mtime, completion=None, input_fingerprint=None,
                  source_identities=None, generation_id=None,
                  producer_versions=None, commit_guard=None):
    data = load_results()
    data[f"{day_folder_name(date, source)}|{row_key}"] = {
        "verdict": verdict, "diff_cells": diff_cells,
        "one_sided": one_sided, "built_at_mtime": built_at_mtime,
        "completion": completion,        # P1-R01: partial inputs flagged durably
        "generation_id": generation_id,
        # P2/F5: the day's TSMIS store-folder identity at build time; a later snapshot
        # reads the cell stale when it differs. Absent on legacy records (mtime only).
        "input_fingerprint": input_fingerprint,
        "source_identities": source_identities or {},
        # CMP-AUD-084: the semantic producer version — a shipped comparator/parser
        # change reads the cell stale via the shared matrix._staleness gate.
        "producer_versions": producer_versions,
    }
    p = _results_path()
    tmp = p.with_name(p.name + ".tmp")

    def _require_guard(path, action):
        if not consolidation_meta.guard_allows(commit_guard, path):
            raise ValueError(
                "The TSN source generation or by-day destination changed before "
                f"the {action}; refresh the comparison.")

    try:
        _require_guard(p.parent, "cache directory write")
        _require_guard(p, "cache write")
        _require_guard(tmp, "cache temporary write")
        p.parent.mkdir(parents=True, exist_ok=True)
        _require_guard(p, "cache write")
        _require_guard(tmp, "cache temporary write")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache_envelope.wrap(data, output_identity="tsn-by-day"), f)
        _require_guard(p, "cache publication")
        _require_guard(tmp, "cache publication")
        os.replace(tmp, p)
    except OSError as e:
        log.warning("day_matrix: could not write results cache %s: %s: %s",
                    p, type(e).__name__, e)
        raise ValueError(
            "The comparison workbook was created, but its by-day result cache "
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
    except OSError:
        return None
    for e in entries:
        try:
            if e.is_file() and artifact_store.is_report_data_file(e.name):
                m = e.stat().st_mtime
                if newest is None or m > newest:
                    newest = m
        except OSError:
            continue          # a locked/vanished entry contributes nothing
    return newest


def tsmis_dir(date, source, subdir):
    """The per-route export the cell compares, resolved to the REAL run folder
    (CMP-AUD-092: a pre-v0.10 legacy bare-date folder is found instead of a
    reconstructed '<date> <source>' that never existed)."""
    return day_source_dir(date, source) / subdir


def available_days(source):
    """Dates (newest first) under output/ that have an export for ANY supported
    vs-TSN report for `source` — the add-day picker's options. Supported subdirs
    come from _day_rows (every report with a coded comparator — all of them as of
    v0.17.0).

    TODAY is always offered, exports or not (W3): today's column is the one the
    matrix itself can export INTO, so requiring an export first was circular —
    the user had to run an export elsewhere just to make the column appear. An
    export-less today renders every cell as missing-its-export with the per-cell
    Export action live."""
    supported_subs = [r[2] for r in _day_rows() if r[4]]
    out, seen = [today_str()], {today_str()}
    for name in list_output_days():
        parsed = parse_run_folder(name)
        if not parsed:
            continue
        date, src, env = parsed
        if f"{src}-{env}" != source or date in seen:
            continue
        base = OUTPUT_ROOT / name
        if any(_folder_newest_mtime(base / sub) is not None for sub in supported_subs):
            seen.add(date)
            out.append(date)
    return out


# --------------------------------------------------------------------------- #
# the snapshot the GUI renders (pure filesystem read)
# --------------------------------------------------------------------------- #
def day_matrix_snapshot(source, days, hidden=None, tsn_files=None, dest=None,
                        now=None, row_order=None, today=None):
    """Full render model for the by-day matrix. PURE stat — no workbook opened
    (counts come from the cache). `days` is the ordered list of date columns;
    `hidden` hides report rows; `row_order` is the user's drag-to-reorder row
    preference; `tsn_files`/`dest` resolve the shared TSN dataset (same as the
    Everything matrix). Greyed rows render cmp {supported:false}.

    `today` (default `today_str()`) is the one date that is EXPORTABLE from the
    matrix — the UI gates the export action on `day == today`. Past columns are
    export-locked so each day's pull stays the immutable record you hand the
    vendor; you can still consolidate + compare them. (`today` is a param so the
    golden check can pin it.)"""
    now = now if now is not None else time.time()
    today = today if today is not None else today_str()
    source = source if source in sources() else SOURCE_DEFAULT
    days = [d for d in (days or []) if isinstance(d, str)]
    hidden = set(hidden or [])
    import tsn_library                              # lazy: canonical explicit choices
    tsn_files, _selection_map_changed = tsn_library.canonicalize_selections(
        tsn_files or {})
    all_rows = _day_rows()
    rows = [r for r in all_rows if r[0] not in hidden]
    by_key = {r[0]: r for r in rows}
    rows = [by_key[k] for k in matrix.apply_order(list(by_key.keys()), row_order)]
    results = load_results()

    # The TSN dataset is resolved PER ROW by its tsn_subdir (both HL rows share
    # 'highway_log'), cached so each distinct dataset is resolved once. `dest` is
    # the Everything matrix's batch_dest so the by-day matrix reuses the same TSN
    # library / _tsn_input fallback + the user's matrix_tsn_files pick.
    _tsn_cache = {}

    def _tsn_for(sub):
        sub = tsn_library.canonical_dataset_key(sub)
        if sub not in _tsn_cache:
            _tsn_cache[sub] = (matrix.tsn_source(dest, sub, tsn_files.get(sub))
                               if dest else {"kind": "none"})
        return _tsn_cache[sub]

    # PER-ROW TSN dataset summaries — one picker per report row, exactly like the
    # Everything matrix. Each report has its OWN TSN source (Highway Log district
    # PDFs, Ramp Detail statewide workbook, Intersection XLSX, …), so a single
    # shared picker was both unnamed and incomplete. Keyed by row_key over the
    # visible rows; cells resolve the same per-report source via _tsn_for below.
    tsn_meta = {}
    for row_key, _label, _subdir, fmt, supported, tsn_subdir in rows:
        if not supported:
            continue
        src = _tsn_for(tsn_subdir)
        tsn_key = tsn_library.canonical_dataset_key(tsn_subdir)
        tsn_meta[row_key] = {
            "supported": True, "fmt": fmt,
            "source_kind": src.get("kind"), "source_path": src.get("path"),
            "pdf_count": src.get("pdf_count"),
            "tsn_subdir": tsn_key,
            "file": tsn_library.selection_path(tsn_files.get(tsn_key)),
            "selected_path": src.get("selected_path"),
            "selection_missing": src.get("kind") == "missing_explicit",
            "selection_reason": src.get("selection_reason"),
            # A dead app-owned pick from a previous install was ignored in favor
            # of the canonical library (field fix 2026-07-22) — picker note.
            "stale_selection_ignored": src.get("stale_selection_ignored"),
            # CMP-AUD-010: the REAL raw-PDF folder + origin (library vs legacy drop).
            "source_legacy": bool(src.get("legacy")),
            "input_dir": (matrix.tsn_input_dir_for(dest, tsn_key, src)
                          if dest else None)}

    cells = {}
    attempts = matrix.load_attempts(byday_root())
    for row_key, _label, subdir, fmt, supported, tsn_subdir in rows:
        per = {}
        for date in days:
            tdir = tsmis_dir(date, source, subdir)
            exp_m = _folder_newest_mtime(tdir)
            export = {"present": exp_m is not None, "mtime": exp_m,
                      "age_seconds": (now - exp_m) if exp_m is not None else None}
            if not supported:
                cmp = {"supported": False}
            else:
                src_tsn = _tsn_for(tsn_subdir)
                tsn_ready = src_tsn.get("kind") in ("file", "consolidated")
                rec = results.get(f"{day_folder_name(date, source)}|{row_key}")
                srcs = [{"name": "cell", "present": exp_m is not None, "mtime": exp_m},
                        {"name": "tsn", "present": tsn_ready,
                         # CMP-AUD-081: a stale canonical library resolves this to
                         # None (status nulls the token when not current) -> stale.
                         "mtime": src_tsn.get("mtime"),
                         "identity": src_tsn.get("identity_token"),
                         "identity_required": True}]
                # F5/P2: fingerprint the day's TSMIS store folder so a deleted route reads
                # the cell stale (the TSN side is a file, captured by mtime).
                cmp = matrix._cmp_state(day_out_path(date, source, row_key), srcs, rec,
                                        fp_folders=(tdir,))
                # CMP-AUD-089: the same durable last-attempt overlay the Everything
                # matrix renders — a failed/stopped/incomplete rebuild marks the cell
                # here too instead of vanishing behind the previous result.
                attempt = matrix._last_attempt_for(
                    attempts, f"{row_key}|{source}", date, cmp)
                if attempt is not None:
                    cmp["last_attempt"] = attempt
            per[date] = {"export": export, "cmp": cmp}
        cells[row_key] = per

    # Per-day "consolidated" indicator: does a reusable consolidated workbook exist
    # for the day's export(s), and is it still fresh? The header shows a badge +
    # offers 'refresh consolidated'.
    # CMP-AUD-093: describe EXACTLY the universe that action can act on. The forced
    # rebuild selects only VISIBLE, TSN-comparable cells, so counting hidden rows or
    # rows with no TSN made the badge promise a fix the action silently no-ops (a
    # zero-target request drained as "success" while the badge stayed stale). Iterate
    # the visible `rows` and require a ready TSN dataset — the same gate cells_to_rebuild
    # applies (a missing-TSN cell has missing_side="tsn" and is never a target).
    day_consolidated = {}
    for date in days:
        subs = {}
        for _k, _label, subdir, fmt, supported, _tsn_subdir in rows:
            if not supported:
                continue
            if _tsn_for(_tsn_subdir).get("kind") not in ("file", "consolidated"):
                continue                         # no TSN -> the action can't target it
            tdir = tsmis_dir(date, source, subdir)
            if _folder_newest_mtime(tdir) is None:
                continue                         # no export -> nothing to consolidate
            subs[subdir] = matrix.consolidated_state(tdir, subdir)
        # F5/CT-7: `subs` holds every supported subdir that HAS an export that day, so a
        # missing consolidation for any of them means the day is NOT fully consolidated.
        # The old `all(... if s["exists"])` skipped the missing ones, so a day with one
        # consolidated report read 'fresh' while another's consolidation was absent.
        # `actionable`: the refresh-consolidated action has at least one target this
        # day (a visible, TSN-ready, exported cell). When false the UI must NOT offer
        # the action — clicking it would resolve zero targets and silently drain.
        actionable = bool(subs)
        exists = any(s["exists"] for s in subs.values())
        fresh = actionable and all(s["exists"] and s["fresh"] for s in subs.values())
        day_consolidated[date] = {"exists": exists, "fresh": fresh,
                                  "actionable": actionable}

    return {
        "source": source,
        "sources": [{"key": k, "label": matrix.default_env_label(k)} for k in sources()],
        "days": days,
        "today": today,                  # the only EXPORTABLE column (past = locked)
        "rows": [r[0] for r in rows],
        "row_labels": {r[0]: r[1] for r in rows},
        "row_supported": {r[0]: r[4] for r in rows},
        "all_rows": [{"key": r[0], "label": r[1], "supported": r[4]} for r in all_rows],
        "hidden": sorted(hidden),
        "tsn_meta": tsn_meta,
        "cells": cells,
        "day_consolidated": day_consolidated,
    }


# --------------------------------------------------------------------------- #
# the scoped rebuild list + one-cell build (pure delegation to the shared path)
# --------------------------------------------------------------------------- #
def cells_to_rebuild(snapshot, scope="stale", row=None, date=None):
    """[(date, row_key)] to (re)build, honoring scope. 'all' = every supported
    cell with the TSMIS side present; 'stale' = only missing/stale ones. Optional
    `row` / `date` filters drive the per-row and per-column rebuilds. Skips greyed
    rows and cells whose export or TSN side is missing."""
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


def evidence_for_day_cell(source, date, row_key, dest, events, tsn_files=None,
                          examples=None, layout=None, commit_guard=None):
    """On-demand evidence for one by-day cell's EXISTING vs-TSN comparison.
    Resolves the same paths build_day_cell uses — but consolidates nothing,
    compares nothing, and does NOT heal the TSN library (a heal would rebuild
    it newer than the comparison and the freshness gate would then rightly
    refuse; a version-stale library needs a comparison refresh anyway)."""
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown by-day matrix row: {row_key}")
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(f"invalid date\\source for the by-day matrix: {date!r} / {source!r}")
    _k, _label, subdir, _fmt, supported, tsn_subdir = rows[row_key]
    if not supported:
        raise ValueError(f"no TSN comparison for {row_key} yet")
    import tsn_library
    tsn_files, _selection_map_changed = tsn_library.canonicalize_selections(
        tsn_files or {})
    tsn_key = tsn_library.canonical_dataset_key(tsn_subdir)
    src_tsn = matrix.tsn_source(dest, tsn_key, tsn_files.get(tsn_key))
    if src_tsn.get("kind") == "missing_explicit":
        raise ValueError(tsn_library.explicit_selection_problem(src_tsn))
    if src_tsn.get("kind") not in ("file", "consolidated"):
        raise ValueError("no consolidated TSN workbook available")
    token, source_identity_check = matrix.tsn_identity_check_for(
        tsn_key, src_tsn)
    source_workbook_identity = matrix.tsn_expected_workbook_identity(
        tsn_key, src_tsn, token)
    record = load_results().get(
        f"{day_folder_name(date, source)}|{row_key}")
    expected_generation_id = matrix.require_cached_tsn_identity(record, token)
    import visual_evidence                               # lazy: pulls PIL/pdfium
    result = matrix.run_evidence_only(
        row_key, tsmis_dir(date, source, subdir), subdir, src_tsn["path"],
        day_out_path(date, source, row_key),
        tsmis_dir(date, source, visual_evidence.pdf_subdir_for(row_key)),
        events, examples=examples, layout=layout, commit_guard=commit_guard,
        source_identity_check=source_identity_check,
        expected_generation_id=expected_generation_id,
        source_workbook_identity=source_workbook_identity,
        live_tsn_path=src_tsn["path"])
    if src_tsn.get("selection"):
        tsn_library.require_explicit_selection(src_tsn["selection"])
    return result


def build_day_cell(source, date, row_key, dest, events, tsn_files=None,
                   confirm_overwrite=None, force_consolidate=False,
                   also_formulas=False, evidence=None, commit_guard=None):
    """Build ONE (day, report) vs-TSN comparison: resolve the shared TSN dataset,
    consolidate that day's per-route export (reusing the day folder's persistent
    consolidated unless stale or `force_consolidate`), compare vs TSN, write the
    VALUES workbook to the by-day store, and cache its counts. Pure delegation to
    matrix.consolidate_and_compare_tsn (the SHARED path). Returns the
    ConsolidateResult. Raises ValueError on an unknown/greyed row or no TSN."""
    rows = _row_lookup()
    if row_key not in rows:
        raise ValueError(f"unknown by-day matrix row: {row_key}")
    # Validate date+source at the boundary so neither can traverse out of output/
    # even if a settings file was hand-edited (the bridge already validates the
    # normal path). The combined folder name must parse as a real run folder.
    if not parse_run_folder(day_folder_name(date, source)):
        raise ValueError(f"invalid date/source for the by-day matrix: {date!r} / {source!r}")
    _k, _label, subdir, fmt, supported, tsn_subdir = rows[row_key]
    if not supported:
        raise ValueError(f"no TSN comparison for {row_key} yet")
    import tsn_library
    tsn_files, _selection_map_changed = tsn_library.canonicalize_selections(
        tsn_files or {})
    tsn_key = tsn_library.canonical_dataset_key(tsn_subdir)
    src_tsn = matrix.tsn_source(dest, tsn_key, tsn_files.get(tsn_key))
    if src_tsn.get("kind") == "missing_explicit":
        raise ValueError(tsn_library.explicit_selection_problem(src_tsn))
    if src_tsn.get("kind") not in ("file", "consolidated"):
        raise ValueError("no consolidated TSN workbook available")
    if src_tsn.get("kind") == "consolidated":
        # CMP-AUD-035: a typed freshness error is terminal. Never interpret it
        # as the current/no-op None case and never compare stale consolidated bytes.
        healed = tsn_library.ensure_current(tsn_key, events, source=src_tsn)
        if healed is not None:
            if healed.status != "ok":
                raise ValueError(
                    healed.message
                    or "the TSN library is not certifiably current; comparison stopped")
        src_tsn = matrix.tsn_source(dest, tsn_key, tsn_files.get(tsn_key))
        if src_tsn.get("kind") != "consolidated":
            raise ValueError(
                "the canonical TSN source changed while it was being certified")
    tsn_token, source_identity_check = matrix.tsn_identity_check_for(
        tsn_key, src_tsn)
    source_workbook_identity = matrix.tsn_expected_workbook_identity(
        tsn_key, src_tsn, tsn_token)

    out_path = day_out_path(date, source, row_key)
    # CMP-AUD-098: capture the day's TSMIS store-folder identity BEFORE the
    # consolidate→compare chain reads it.
    fp_folders = (tsmis_dir(date, source, subdir),)
    fp_before = matrix._cell_input_fingerprint(*fp_folders)
    result = matrix.consolidate_and_compare_tsn(
        tsmis_dir(date, source, subdir), src_tsn["path"], out_path, row_key, subdir,
        events, confirm_overwrite=confirm_overwrite, force_consolidate=force_consolidate,
        also_formulas=also_formulas,
        evidence_opts=matrix.evidence_opts_for(
            evidence, row_key, lambda sub: tsmis_dir(date, source, sub)),
        explicit_selection=src_tsn.get("selection"),
        commit_guard=commit_guard,
        source_identity_check=source_identity_check,
        source_workbook_identity=source_workbook_identity)
    # P1-B05: reduce the TSN side too — a partial TSN consolidation (categories /
    # district PDFs left out) flags the by-day cell partial just like a partial TSMIS side.
    if result.status == "ok" and out_path.exists():
        matrix._require_source_identity(
            source_identity_check, "recording the by-day comparison cache")
        cache_guard = matrix._compose_source_guard(
            commit_guard, source_identity_check)
        # F4: detect the layout from the produced workbook — the aggregate reports
        # (Ramp / Intersection Summary) emit a flat sheet that a hardcoded
        # has_route=True would read one column off (0 diffs). The header decides.
        published = matrix._published_comparison_result(out_path, result)
        typed = published.comparison_outcome
        diff_cells = typed.counts.differing_cells
        one_sided = (typed.counts.side_a_only_rows
                     + typed.counts.side_b_only_rows)
        try:
            built_at = out_path.stat().st_mtime
        except OSError:
            built_at = None
        # F5/P2: record the day's TSMIS store-folder identity so a deleted route reads
        # the reused cell stale (same folder _cmp_state fingerprints in the snapshot).
        # CMP-AUD-098: the PRE-comparison capture is recorded — a mid-build
        # mutation therefore reads immediately stale, never fresh.
        record_result(date, source, row_key, typed.verdict, diff_cells, one_sided,
                      built_at, completion=typed.completion,
                      input_fingerprint=matrix._fingerprint_for_record(
                          fp_before, fp_folders, out_path.name, events),
                      source_identities=(
                          {"tsn": tsn_token}),
                      generation_id=published.artifact_generation.generation_id,
                      producer_versions=matrix.producer_identity(),
                      commit_guard=cache_guard)
    return result

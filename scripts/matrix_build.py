"""The matrix BUILD side (S4 / ARC-03, split from matrix.py).

(Re)building comparison cells: the live-formulas twin policy, the store-folder
consolidation for the TSN modes, and `build_comparison` — the mode dispatcher
the GUI workers and the one-click validation drive. Collaborators that the
verification suite (or a future caller) monkeypatches on the `matrix` facade
are looked up through the facade AT CALL TIME (`_m.<name>`), so patching
`matrix.read_counts` / `matrix._ensure_consolidated` / … keeps intercepting
these internal calls exactly as it did before the split.
"""
import logging
import shutil
from pathlib import Path

import consolidation_meta
import outcome
import reports

import artifact_store
from events import ConsolidateResult
from matrix_state import (_MTIME_TOL_S, _cell_input_fingerprint, _mode_by_id,
                          _pdf_self_comparator, _row_defs, _row_modes,
                          _safe_mtime, comparison_path, mode_out_path,
                          record_result, record_tsn_result, tsn_input_root,
                          tsn_source)

class _FacadeProxy:
    """Resolves `_m.<name>` through the `matrix` facade AT CALL TIME (a lazy
    import, so there is no module-level matrix <-> matrix_build cycle). This is
    what keeps `matrix.<name>` the one true monkeypatch point for the names the
    verification suite stubs."""
    def __getattr__(self, name):
        import matrix
        return getattr(matrix, name)


_m = _FacadeProxy()       # the facade; resolved at call time (see the docstring)

log = logging.getLogger("tsmis.matrix")

# --------------------------------------------------------------------------- #
# optional live-formulas twin (opt-in). The matrix's offline counts + freshness
# all key off the VALUES workbook at the canonical out_path (compare_core is
# regression-locked, so we can't make mode="both" put values there). So when the
# user opts in, we ALSO write a recalculating formulas copy to a "(formulas)"
# sibling via a second compare pass — best-effort, never failing the values cell.
# --------------------------------------------------------------------------- #
def _formulas_sibling(out_path):
    out_path = Path(out_path)
    return out_path.with_name(f"{out_path.stem} (formulas){out_path.suffix}")


# The live-formulas twin rewrites the whole comparison as live formulas; for the largest
# report (Intersection Detail, ~17k rows) that is millions of formulas and minutes of
# wall-clock ON TOP OF the values workbook that already holds every value. Past this many
# Comparison-sheet rows the matrix skips the twin and says so — keeping the bulk rebuild
# responsive. (The manual Compare tab path doesn't go through here, so an explicitly
# requested single live-formulas comparison is unaffected.)
_FORMULAS_TWIN_MAX_ROWS = 12_000


def _comparison_row_count(values_path):
    """Data-row count of a values workbook's Comparison sheet (read-only — the dimension
    is read from the sheet, not by scanning cells), or None if it can't be read. None ⇒
    the caller writes the twin anyway (never skip the twin on an uncertain probe)."""
    from openpyxl import load_workbook           # lazy: openpyxl stays off GUI startup
    try:
        wb = load_workbook(values_path, read_only=True)
    except Exception as e:                       # noqa: BLE001 (best-effort probe)
        log.debug("formulas-twin probe: can't open %s (%s: %s)",
                  values_path, type(e).__name__, e)
        return None
    try:
        ws = wb["Comparison"] if "Comparison" in wb.sheetnames else wb.worksheets[0]
        n = ws.max_row
    except Exception as e:                       # noqa: BLE001
        log.debug("formulas-twin probe: can't size %s (%s: %s)",
                  values_path, type(e).__name__, e)
        n = None
    finally:
        try:
            wb.close()
        except Exception:                        # noqa: BLE001
            pass
    return (n - 1) if isinstance(n, int) and n > 0 else None   # minus the header row


def _try_formulas(compare_call, out_path, events=None):
    """Run `compare_call(formulas_path)` (mode='formulas') beside the values copy,
    committed ATOMICALLY (the adapter writes a temp; commit_workbook validates +
    os.replace) so an interrupted formulas write never truncates a prior good sibling
    (F9). Best-effort: a failure here must NOT fail the already-written values cell — but it
    is LOGGED (P2-A03: a validation/finalization failure RETURNS status='error' rather than
    raising, so the returned result is inspected, not just exceptions).

    Skipped for very large comparisons (`_FORMULAS_TWIN_MAX_ROWS`): there the twin is
    millions of formulas and minutes of work, and the values workbook — already committed —
    holds every value. The skip is announced (events + log) so the absent twin is never a
    silent surprise."""
    rows = _comparison_row_count(out_path)
    # read the limit through the facade — it's a TUNABLE the twin-guard check
    # (and a hotfix) can set as matrix._FORMULAS_TWIN_MAX_ROWS
    if rows is not None and rows > _m._FORMULAS_TWIN_MAX_ROWS:
        msg = (f"Skipping the live-formulas copy of {Path(out_path).name} "
               f"({rows:,} rows, over the {_m._FORMULAS_TWIN_MAX_ROWS:,}-row limit). The "
               f"values workbook has every value; build a live-formulas copy of this "
               f"comparison on its own if you need one.")
        if events is not None:
            events.on_log(msg)
        log.info("matrix: %s", msg)
        return
    try:
        res = artifact_store.commit_workbook(_formulas_sibling(out_path),
                                             lambda tmp: compare_call(tmp),
                                             expect_sheet="Comparison")
        if getattr(res, "status", None) != "ok":
            log.warning("matrix: live-formulas workbook for %s not refreshed (%s)",
                        Path(out_path).name, getattr(res, "message", "") or "commit failed")
    except Exception as e:                       # noqa: BLE001
        log.warning("matrix: live-formulas workbook for %s not written (%s: %s)",
                    Path(out_path).name, type(e).__name__, e)


# --------------------------------------------------------------------------- #
# orchestration: build one cell's comparison (pure delegation to compare_env)
# --------------------------------------------------------------------------- #
def build_cell_comparison(dest, baseline_key, row_key, cell_key, events,
                          confirm_overwrite=None, row_defs=None, also_formulas=False):
    """Compare (row's report, cell env) against the baseline env, writing the
    VALUES workbook to comparison_path(...), and record its verdict + discrepancy
    counts in the cache. Pure delegation to the adapter's compare_folders — the
    comparison engine is untouched. Returns the ConsolidateResult. With
    `also_formulas`, also writes a live-formulas twin beside the values copy.

    Raises ValueError on an unknown row_key or a baseline cell (nothing to
    compare); compare_folders itself returns a clean error result when a side
    hasn't been exported yet."""
    rows = row_defs if row_defs is not None else _row_defs()
    if row_key not in rows:
        raise ValueError(f"unknown matrix row: {row_key}")
    if cell_key == baseline_key:
        raise ValueError("the baseline column has nothing to compare against")
    _label, subdir, _idx, adapter, _hr = rows[row_key]   # _hr: layout is detected from the workbook (O4)

    dest = Path(dest)
    out_path = comparison_path(dest, baseline_key, row_key, cell_key)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # side A = the cell env, side B = the baseline (labels read "ARS-TEST vs SSOR-PROD").
    # F9: the adapter writes a temp; commit_workbook validates + os.replaces it onto
    # out_path so an interrupted compare never truncates the prior cross-env cell.
    result = artifact_store.commit_workbook(
        out_path,
        lambda tmp: adapter.compare_folders(
            dest / cell_key, dest / baseline_key, tmp, events=events,
            confirm_overwrite=lambda _p: True, mode="values"),
        expect_sheet="Comparison",
        confirm_overwrite=confirm_overwrite or (lambda _p: True))
    if also_formulas and result.status == "ok":
        _try_formulas(lambda fp: adapter.compare_folders(
            dest / cell_key, dest / baseline_key, fp, events=events,
            confirm_overwrite=lambda _p: True, mode="formulas"), out_path, events)

    if result.status == "ok" and out_path.exists():
        # O4: detect the layout from the produced workbook, not the row's declared
        # has_route — an aggregate cross-env adapter (Ramp/Intersection Summary) can
        # have a sheet_name yet emit a flat sheet, which would otherwise read as 0 diffs.
        diff_cells, one_sided = _m.read_counts(out_path)
        try:
            built_at = out_path.stat().st_mtime
        except OSError:
            built_at = None
        # F5/P2: record the inputs' identity (cell + baseline export folders, in that
        # order) so a later snapshot reads the cell stale when a route changed.
        record_result(dest, baseline_key, row_key, cell_key, result.verdict,
                      diff_cells, one_sided, built_at,
                      completion=result.completion or outcome.COMPLETE,
                      input_fingerprint=_cell_input_fingerprint(
                          dest / cell_key / subdir, dest / baseline_key / subdir))
    return result


def cells_to_rebuild(snapshot, scope="stale", row=None, env=None):
    """[(row_key, cell_key, mode_id)] to (re)compute, honoring each row's SELECTED
    mode. scope='all' = every comparable cell (both sides present); 'stale' = only
    missing/stale ones. Optional `row` / `env` filters drive the per-row and
    per-column refresh buttons. Skips the env-mode baseline column, unsupported
    (greyed) modes, and cells with a missing input side."""
    modes = snapshot.get("modes", {})
    todo = []
    for row_key in snapshot["rows"]:
        if row and row_key != row:
            continue
        mode_id = modes.get(row_key, "env")
        for ev in snapshot["envs"]:
            if env and ev != env:
                continue
            cmp = snapshot["cells"][row_key][ev].get("cmp")
            if cmp is None:                      # env-mode baseline column
                continue
            if not cmp.get("supported") or cmp.get("missing_side"):
                continue
            if scope == "all" or cmp.get("stale"):
                todo.append((row_key, ev, mode_id))
    return todo


# --------------------------------------------------------------------------- #
# orchestration: consolidate the env's store folder(s) and diff via the existing
# (untouched) comparison adapters. compare_highway_log / compare_highway_log_pdf
# are file-vs-file, so the per-route env folders are consolidated first.
# --------------------------------------------------------------------------- #
def _pdf_store_consolidator(subdir):
    """The consolidator module for a PDF-sourced report — Highway Log (PDF) and
    Intersection Detail (PDF), the two reports deliberately absent from
    reports.consolidator_for_subdir because they need a scratch converted_dir to
    parse the PDFs first. Used by BOTH _consolidate_store_folder and
    _consolidated_filename so a PDF report is wired in ONE place — a matrix/by-day row
    whose subdir resolved no consolidated filename was the v0.17.4 by-day crash class."""
    if subdir == "highway_log_pdf":
        import consolidate_tsmis_highway_log_pdf as _m       # pdfplumber — lazy
        return _m
    if subdir == "intersection_detail_pdf":
        import consolidate_tsmis_intersection_detail_pdf as _m
        return _m
    if subdir == "highway_detail_pdf":
        import consolidate_tsmis_highway_detail_pdf as _m
        return _m
    if subdir == "highway_sequence_pdf":
        import consolidate_tsmis_highway_sequence_pdf as _m
        return _m
    if subdir == "ramp_detail_pdf":
        import consolidate_tsmis_ramp_detail_pdf as _m
        return _m
    return None


def _consolidate_store_folder(subdir, env_dir, out_path, events):
    """Consolidate one Export-Everything store folder (<env>/<subdir>/, per-route
    files) into a single workbook via the report's existing consolidator (with its
    additive input_dir/out_path override). Registry-driven via
    reports.consolidator_for_subdir, so any consolidatable report works; the PDF
    Highway Log is the one special case (needs a scratch converted_dir).

    Returns the consolidator's ConsolidateResult (F3) so callers can honor its
    completion — its `status`/`completion` decides whether the output is safe to
    compare and cache as a fresh result."""
    out_path = Path(out_path)
    # P2-A02: capture the inputs' identity BEFORE the build, so write_consolidated_fingerprint
    # can refuse to certify the workbook "fresh" if an external writer changed the source folder
    # mid-build (the GUI task lock already serializes our own writers).
    fp_before = artifact_store.fingerprint(env_dir)
    pdf_mod = _pdf_store_consolidator(subdir)
    if pdf_mod is not None:
        # Highway Log (PDF) / Intersection Detail (PDF): parse the per-route PDFs into
        # a scratch converted_dir first, then combine — they have no entry in
        # consolidator_for_subdir for exactly this reason.
        conv = out_path.parent / f".{out_path.stem}_conv"
        try:
            res = pdf_mod.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                      input_dir=Path(env_dir), out_path=out_path,
                                      converted_dir=conv)
        finally:
            shutil.rmtree(conv, ignore_errors=True)
    else:
        import reports                               # lazy (avoid import cycle)
        mod = reports.consolidator_for_subdir(subdir)
        if mod is None:
            raise ValueError(f"no store consolidator for {subdir}")
        # F3: RETURN the ConsolidateResult so callers can honor its completion — a
        # failed / no-data consolidation must not be compared or cached as fresh.
        res = mod.consolidate(events=events, confirm_overwrite=lambda _p: True,
                              input_dir=Path(env_dir), out_path=out_path)
    # P1-R01: persist the producer completion beside the consolidated workbook through
    # the shared boundary so a later REUSE (no fresh ConsolidateResult) still knows it
    # was built from partial inputs. No-op unless an output was produced (status ok). A
    # False return = a non-complete artifact's flag could NOT be recorded (publication
    # failed): the operation cannot claim a safely persisted artifact, so raise — the
    # comparison surfaces not-refreshed and keeps the prior cell rather than diffing a
    # workbook that might read complete.
    if not consolidation_meta.write_outcome(out_path, res):
        raise ValueError(f"the {subdir} consolidation finished but its outcome could not "
                         "be recorded; the incomplete workbook was invalidated — re-run")
    # P2/F5: record the source folder's input fingerprint beside the workbook so a later
    # reuse rebuilds when the inputs' IDENTITY changed (a route added / removed / resized),
    # not just when the newest mtime advanced (_consolidated_stale via consolidated_fresh).
    # P2-A02: pass the pre-build fingerprint — if the inputs changed during the build, the
    # workbook is NOT certified fresh (it rebuilds next reuse) rather than stamped wrong.
    if getattr(res, "status", None) == "ok":
        artifact_store.write_consolidated_fingerprint(out_path, env_dir, built_from=fp_before)
    return res


def consolidate_tsn_pdfs(dest, subdir, events=None, confirm_overwrite=None):
    """Build a consolidated TSN workbook FROM the district PDFs the user dropped in
    <dest>/_tsn_input/<subdir>/, writing it back there so the next tsn_source()
    finds it. TSN is the SAME district-PDF set for both Highway Log flavors, so
    only the 'highway_log' TSN drop folder is handled. Returns the out path."""
    if subdir != "highway_log":
        raise ValueError(f"no TSN PDF consolidator for {subdir}")
    import consolidate_tsn_highway_log as _ctsn   # pdfplumber — lazy
    in_dir = tsn_input_root(dest, subdir)
    out_path = in_dir / "tsn_highway_log_consolidated.xlsx"
    res = _ctsn.consolidate(events=events, confirm_overwrite=confirm_overwrite or (lambda _p: True),
                            input_dir=in_dir, out_path=out_path)
    # P1-B05: honor the producer result. A failed / no-data / cancelled TSN consolidation
    # must NOT return a success-shaped path — its worker would log "TSN workbook ready"
    # with errors=0. Raise the consolidator's own message so the worker reports a
    # not-refreshed failure (errors>0) and the prior workbook is kept untouched.
    if not outcome.comparable(outcome.consolidate_completion_of(res)):
        raise ValueError(res.message or f"the {subdir} TSN consolidation did not complete")
    # A partial set (some district PDFs left out) stays usable but flagged — persist the
    # producer completion beside the workbook so the matrix flags it on reuse. If the
    # flag could not be recorded (publication failed), the partial workbook was
    # invalidated — raise so the worker reports a not-refreshed failure (never a
    # success-shaped path to a workbook that would read complete).
    if not consolidation_meta.write_outcome(out_path, res):
        raise ValueError(f"the {subdir} TSN consolidation finished but its outcome could "
                         "not be recorded; the incomplete workbook was discarded — re-run")
    return out_path


# --- persistent (reusable) consolidated workbooks ------------------------- #
# v0.16.x: instead of consolidating a per-route store folder to a throwaway temp
# on EVERY comparison, persist the consolidated workbook into the run/store
# folder's `consolidated/` dir — the SAME filename + location the Consolidate tab
# uses — and REUSE it until the per-route files change. So: re-exporting a report
# makes its consolidated stale (a source file is newer) → the next comparison
# re-consolidates; only changing the comparison mechanism (not the data) reuses
# the existing consolidated. A force flag rebuilds it on demand.
def _consolidated_filename(subdir):
    pdf_mod = _pdf_store_consolidator(subdir)
    if pdf_mod is not None:
        return pdf_mod.FILENAME
    mod = reports.consolidator_for_subdir(subdir)
    if mod is None:
        raise ValueError(f"no consolidated filename for {subdir}")
    return mod.FILENAME


def consolidated_store_path(store_dir, subdir):
    """The PERSISTENT consolidated workbook for a per-route store folder: a sibling
    `consolidated/` dir, date/env-stamped via the parent run-folder name (so a day
    folder gets a stamped name and matches the Consolidate-tab output; the always-
    current Everything store, whose parent is just `<src-env>`, gets the plain
    name)."""
    from paths import stamped_consolidated_filename     # lazy (avoid import cycle)
    parent = Path(store_dir).parent
    name = stamped_consolidated_filename(_consolidated_filename(subdir), parent.name)
    return parent / "consolidated" / name


def consolidated_state(store_dir, subdir):
    """{exists, fresh, path} for a store folder's persistent consolidated — drives
    the 'consolidated for this day' indicator. fresh = present AND its inputs' IDENTITY
    is unchanged since it was built (the artifact_store input fingerprint, not a
    newest-mtime check — see _consolidated_stale; P2/F5)."""
    p = consolidated_store_path(store_dir, subdir)
    return {"exists": p.exists(), "fresh": not _m._consolidated_stale(p, store_dir),
            "path": str(p)}


def _consolidated_stale(consolidated, store_dir):
    """True when the persistent consolidated must be REBUILT: missing/unreadable, OR its
    inputs' IDENTITY changed since it was built — a route file added / removed / resized /
    re-timed (F5/R1-R03, via artifact_store's input fingerprint). The old signal was the
    store's NEWEST mtime, which missed a DELETED non-newest route: the consolidated then
    read as fresh though it still carried the gone route's rows. A legacy consolidated
    with no fingerprint sidecar reads stale ONCE, rebuilds, and records the sidecar (the
    one-time migration). Never raises."""
    return not artifact_store.consolidated_fresh(consolidated, store_dir)


def evidence_opts_for(evidence, row_key, dir_for_subdir):
    """Resolve one cell's visual-evidence request: None unless the user toggle
    is on AND the row supports evidence. `dir_for_subdir` maps a TSMIS export
    subdir to THIS cell's folder for it (the Everything matrix and the by-day
    matrix lay their stores out differently — each caller passes its own
    mapping, the resolution logic lives once here)."""
    if not (evidence and evidence.get("enabled")):
        return None
    import visual_evidence                               # lazy: pulls PIL/pdfium
    if not visual_evidence.capable(row_key):
        return None
    return {"tsmis_pdf_dir": dir_for_subdir(visual_evidence.pdf_subdir_for(row_key)),
            "examples": visual_evidence.clamp_examples(evidence.get("examples"))}


def run_evidence_only(row_key, store_dir, subdir, tsn_path, comparison_path,
                      tsmis_pdf_dir, events, examples=None):
    """Generate/refresh the evidence set for an EXISTING vs-TSN comparison — the
    on-demand per-cell action (the toggle-driven decoration runs inside
    consolidate_and_compare_tsn as the comparison is built). Runs regardless of
    the evidence toggle; `examples` is engine-clamped.

    The FRESHNESS GATE is what keeps the on-demand path honest: the generator
    re-enumerates the differences from the CURRENT consolidated + TSN artifacts,
    so if either moved on since the comparison was built, the images could
    illustrate a diff set the workbook doesn't carry. It therefore REFUSES —
    with a "refresh the comparison" hint — when the store changed under the
    consolidated workbook, or when the consolidated/TSN workbook is newer than
    the comparison. Returns a ConsolidateResult; raises ValueError with the
    actionable reason for every not-runnable case."""
    import visual_evidence                               # lazy: pulls PIL/pdfium
    if not visual_evidence.capable(row_key):
        raise ValueError("this report doesn't support evidence images")
    comparison_path = Path(comparison_path)
    tsn_path = Path(tsn_path)
    consolidated = consolidated_store_path(store_dir, subdir)
    if not comparison_path.exists():
        raise ValueError("no comparison workbook for this cell yet — run the "
                         "comparison first")
    if not consolidated.exists():
        raise ValueError(f"no consolidated {subdir} workbook for this cell — "
                         "run the comparison first")
    refresh_hint = ("— refresh the comparison instead (it regenerates the "
                    "evidence set when the Evidence images option is on, or "
                    "run this action again after)")
    if _m._consolidated_stale(consolidated, store_dir):
        raise ValueError(f"the {subdir} exports changed since the comparison "
                         f"was built {refresh_hint}")
    cmp_mtime = _safe_mtime(comparison_path) or 0
    if (_safe_mtime(consolidated) or 0) > cmp_mtime + _MTIME_TOL_S:
        raise ValueError(f"the consolidated {subdir} workbook is newer than "
                         f"this comparison {refresh_hint}")
    if (_safe_mtime(tsn_path) or 0) > cmp_mtime + _MTIME_TOL_S:
        raise ValueError(f"the TSN workbook is newer than this comparison "
                         f"{refresh_hint}")
    ev = visual_evidence.generate(
        row_key, consolidated, tsn_path, comparison_path, tsmis_pdf_dir, events,
        examples=visual_evidence.clamp_examples(examples))
    note = ev.get("note") or "evidence run finished"
    return ConsolidateResult(status="ok", message=note, summary_lines=[note])


def evidence_for_cell(dest, row_key, cell_key, baseline_key, events,
                      tsn_files=None, examples=None):
    """On-demand evidence for one Everything-matrix cell's EXISTING vs-TSN
    comparison. Resolves the same paths build_comparison's tsn branch uses —
    but consolidates nothing, compares nothing, and does NOT heal the TSN
    library (a heal would rebuild it newer than the comparison and the
    freshness gate would then rightly refuse; a version-stale library needs a
    comparison refresh anyway)."""
    rows = _row_defs()
    if row_key not in rows:
        raise ValueError(f"unknown matrix row: {row_key}")
    _label, subdir, _idx, adapter, _hr = rows[row_key]
    mode = _mode_by_id(_row_modes(row_key, subdir, adapter), "tsn")
    if not mode["supported"]:
        raise ValueError(f"no TSN comparison for {row_key}")
    dest = Path(dest)
    tsn_files = tsn_files or {}
    src = tsn_source(dest, mode["tsn_subdir"], tsn_files.get(mode["tsn_subdir"]))
    if src.get("kind") not in ("file", "consolidated"):
        raise ValueError("no consolidated TSN workbook available")
    import visual_evidence                               # lazy: pulls PIL/pdfium
    return run_evidence_only(
        row_key, dest / cell_key / mode["env_subdir"], mode["env_subdir"],
        src["path"], mode_out_path(dest, baseline_key, row_key, cell_key, mode),
        dest / cell_key / visual_evidence.pdf_subdir_for(row_key),
        events, examples=examples)


# Producer-completion persistence for the persistent consolidated workbook lives in
# the shared `consolidation_meta` boundary (P1-R01) — every persistent writer (matrix
# store consolidation, auto-consolidate, the GUI/console Consolidate tab, TSN-library
# builds) records the outcome there, and reuse recovers it, so no writer can bypass it.
def consolidate_and_compare_tsn(tsmis_store_dir, tsn_path, out_path, row_key, subdir,
                                events, confirm_overwrite=None, force_consolidate=False,
                                also_formulas=False, evidence_opts=None):
    """The SHARED TSN compare path used by BOTH matrices (the Everything matrix's
    latest-store cells AND the Compare tab's by-day cells).

    Consolidate a per-route TSMIS store folder (`tsmis_store_dir`, the `subdir`
    report) into its PERSISTENT `consolidated/` workbook (reused when still fresh;
    rebuilt when the inputs' IDENTITY changed — a route added/removed/resized, the
    artifact_store fingerprint — or `force_consolidate`), then compare it vs
    the consolidated TSN workbook with the row's comparator (`_m.tsn_comparator_for(
    row_key)` — Highway Log Excel/PDF, Ramp Detail, …), writing the VALUES workbook
    to `out_path`. Returns the ConsolidateResult. Pure delegation to the untouched
    consolidate_* / compare_* adapters; the matrices differ only by the source
    folder + the output path. (For HL the output is semantically identical to the prior
    fmt-keyed path — same consolidator + same comparator; the P2 atomic-write wrapper only
    changes the write mechanism, not the workbook content.)"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmp_mod = _m.tsn_comparator_for(row_key)
    if cmp_mod is None:
        raise ValueError(f"no TSN comparator for {row_key}")
    consolidated = consolidated_store_path(tsmis_store_dir, subdir)
    cres = None
    if force_consolidate or _m._consolidated_stale(consolidated, tsmis_store_dir):
        cres = _m._consolidate_store_folder(subdir, Path(tsmis_store_dir), consolidated, events)
    # F3: honor the consolidation outcome instead of silently discarding it. A
    # failed / no-data / cancelled consolidation must NOT feed a comparison or be
    # cached as fresh — raise the consolidator's OWN message (clearer than the
    # generic backstop below), so the cell surfaces exactly why it didn't refresh
    # and the prior cached comparison is left untouched (not overwritten with a
    # result built from incomplete inputs). A partial consolidation still compares.
    # cres is None when the existing consolidated was fresh and reused.
    if cres is not None and not outcome.comparable(outcome.consolidate_completion_of(cres)):
        raise ValueError(cres.message or f"the {subdir} consolidation did not complete")
    # Backstop: a consolidator can return without raising yet write nothing (an
    # empty store folder). Catch that here so the failure names the consolidation
    # step instead of the compare adapter erroring on a missing/empty input.
    if not consolidated.exists() or consolidated.stat().st_size == 0:
        raise ValueError(f"nothing to compare — no {subdir} export found in "
                         f"{tsmis_store_dir}")
    # F9: the comparator writes to a temp path; commit_workbook validates + os.replaces
    # it onto out_path, so an interrupted/failed compare never truncates the prior cell.
    # compare_core is untouched — it just writes to the temp it is handed.
    result = artifact_store.commit_workbook(
        out_path,
        lambda tmp: cmp_mod.compare(consolidated, str(tsn_path), tmp, events=events,
                                    confirm_overwrite=lambda _p: True, mode="values"),
        expect_sheet="Comparison",
        confirm_overwrite=confirm_overwrite or (lambda _p: True))
    if also_formulas and result.status == "ok":
        _try_formulas(lambda fp: cmp_mod.compare(
            consolidated, str(tsn_path), fp, events=events,
            confirm_overwrite=lambda _p: True, mode="formulas"), out_path, events)
    # P1-R01: a PARTIAL TSMIS consolidation (inputs left out) still compares, but the
    # diff is over INCOMPLETE inputs — flag the comparison so the caller records the
    # cell as partial. `cres` is set only when we (re)consolidated THIS call; when the
    # existing consolidated was REUSED (`cres` is None) recover the producer completion
    # from the sidecar so a reused partial stays flagged instead of silently reading
    # as a fresh, complete cell.
    if result.status == "ok":
        comp = (outcome.consolidate_completion_of(cres) if cres is not None
                else consolidation_meta.read_completion(consolidated))
        if comp == outcome.PARTIAL:
            result.completion = outcome.PARTIAL
    # Visual evidence is a DECORATION of a finished comparison: it renders
    # highlighted PDF snippets for sampled diffs next to the workbook. It never
    # changes the comparison's status/completion/counts, and any failure only
    # logs + notes (the comparison already succeeded). `evidence_opts` is set by
    # the callers when the user's toggle is on AND the row supports it.
    if result.status == "ok" and evidence_opts:
        try:
            import visual_evidence                       # lazy: pulls PIL/pdfium
            ev = visual_evidence.generate(
                row_key, consolidated, tsn_path, out_path,
                evidence_opts["tsmis_pdf_dir"], events,
                examples=evidence_opts.get("examples"))
            if ev.get("note"):
                result.summary_lines = list(result.summary_lines) + [ev["note"]]
        except Exception as e:                           # noqa: BLE001
            log.warning("evidence generation for %s skipped", row_key, exc_info=True)
            msg = str(e).splitlines()[0] if str(e) else type(e).__name__
            events.on_log(f"  evidence images skipped — {msg}")
            result.summary_lines = list(result.summary_lines) + [
                f"evidence images skipped — {msg}"]
    return result


def _ensure_consolidated(store_dir, subdir, events, force):
    """Return (persistent consolidated workbook path, its producer completion) for a
    store folder, rebuilding when stale or forced. Shared by the self (PDF-vs-Excel)
    path. F3: raises a clear ValueError when a rebuild did not complete (failed/
    no-data/cancelled), so the self comparison names the consolidation failure instead
    of erroring later on a missing/stale input. P1-R01: the completion is the fresh
    build's (when rebuilt) or the persisted sidecar's (when reused), so a partial side
    stays flagged through the self comparison."""
    p = consolidated_store_path(store_dir, subdir)
    comp = None
    if force or _m._consolidated_stale(p, store_dir):
        cres = _m._consolidate_store_folder(subdir, Path(store_dir), p, events)
        if cres is not None and not outcome.comparable(outcome.consolidate_completion_of(cres)):
            raise ValueError(cres.message or f"the {subdir} consolidation did not complete")
        comp = outcome.consolidate_completion_of(cres) if cres is not None else None
    if comp is None:                       # reused (or rebuild gave no result) -> sidecar
        comp = consolidation_meta.read_completion(p)
    return p, comp


def build_comparison(dest, row_key, cell_key, mode_id, baseline_key, events,
                     tsn_files=None, confirm_overwrite=None, row_defs=None,
                     force_consolidate=False, also_formulas=False, evidence=None):
    """(Re)build one cell's comparison for the row's SELECTED mode, write the VALUES
    workbook, and cache its counts. Dispatches to the existing comparison adapters
    (never edits them). Returns the ConsolidateResult. Raises ValueError for an
    unknown row or an unsupported/greyed mode; an absent input side yields the
    adapter's clean error result. `force_consolidate` rebuilds the persistent
    consolidated even when it looks fresh; `also_formulas` writes a live-formulas
    twin beside the values copy. `evidence` ({'enabled','examples'}) requests the
    visual-evidence decoration on a TSN-mode cell of a supported row."""
    rows = row_defs if row_defs is not None else _row_defs()
    if row_key not in rows:
        raise ValueError(f"unknown matrix row: {row_key}")
    _label, subdir, _idx, adapter, _hr = rows[row_key]
    mode = _mode_by_id(_row_modes(row_key, subdir, adapter), mode_id)
    if not mode["supported"]:
        raise ValueError(f"no comparison for {row_key} / {mode['id']}")

    if mode["kind"] == "env":
        return _m.build_cell_comparison(dest, baseline_key, row_key, cell_key, events,
                                     confirm_overwrite=confirm_overwrite, row_defs=rows,
                                     also_formulas=also_formulas)

    dest = Path(dest)
    out_path = mode_out_path(dest, baseline_key, row_key, cell_key, mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tsn_files = tsn_files or {}
    if mode["kind"] == "tsn":
        src = tsn_source(dest, mode["tsn_subdir"], tsn_files.get(mode["tsn_subdir"]))
        if src.get("kind") not in ("file", "consolidated"):
            raise ValueError("no consolidated TSN workbook available")
        if src.get("kind") == "consolidated":
            # D2 auto-heal: a version/mtime-stale library rebuilds from raw
            # BEFORE the comparison reads it (else a normalizer fix silently
            # "looks unfixed" until a manual Settings rebuild).
            import tsn_library                           # lazy: no import cycle
            healed = tsn_library.ensure_current(mode["tsn_subdir"], events)
            if healed is not None:
                if healed.status != "ok":
                    raise ValueError(healed.message
                                     or "the TSN library rebuild failed")
                src = tsn_source(dest, mode["tsn_subdir"],
                                 tsn_files.get(mode["tsn_subdir"]))
        result = _m.consolidate_and_compare_tsn(
            dest / cell_key / mode["env_subdir"], src["path"], out_path,
            row_key, mode["env_subdir"], events, confirm_overwrite=confirm_overwrite,
            force_consolidate=force_consolidate, also_formulas=also_formulas,
            evidence_opts=evidence_opts_for(evidence, row_key,
                                            lambda sub: dest / cell_key / sub))
        # P1-B05: the TSN side can ALSO be partial (a TSN builder left categories /
        # district PDFs out). consolidate_and_compare_tsn reduced the TSMIS side; reduce
        # the TSN side here (its completion rides on the resolved source) so the cell
        # flags partial when EITHER input was incomplete.
        if result.status == "ok" and src.get("completion") == outcome.PARTIAL:
            result.completion = outcome.PARTIAL
    else:                                # self: TSMIS PDF vs Excel (persisted both sides)
        side_env, comp_env = _m._ensure_consolidated(dest / cell_key / mode["env_subdir"],
                                                  mode["env_subdir"], events, force_consolidate)
        side_other, comp_other = _m._ensure_consolidated(dest / cell_key / mode["other_subdir"],
                                                      mode["other_subdir"], events, force_consolidate)
        # the adapter fixes PDF=side A, Excel=side B regardless of the row. The PDF
        # side is whichever subdir ends with `_pdf` (env on the …_pdf row, other on the
        # Excel row); the comparator is that family's PDF-vs-Excel adapter.
        env_is_pdf = mode["env_subdir"].endswith("_pdf")
        pdf_subdir = mode["env_subdir"] if env_is_pdf else mode["other_subdir"]
        pdf_c = side_env if env_is_pdf else side_other
        excel_c = side_other if env_is_pdf else side_env
        _self_cmp = _pdf_self_comparator(pdf_subdir)
        result = artifact_store.commit_workbook(
            out_path,
            lambda tmp: _self_cmp.compare(
                pdf_c, excel_c, tmp, events=events,
                confirm_overwrite=lambda _p: True, mode="values"),
            expect_sheet="Comparison",
            confirm_overwrite=confirm_overwrite or (lambda _p: True))
        if also_formulas and result.status == "ok":
            _try_formulas(lambda fp: _self_cmp.compare(
                pdf_c, excel_c, fp, events=events,
                confirm_overwrite=lambda _p: True, mode="formulas"), out_path, events)
        # P1-R01: a PARTIAL side means the self comparison diffed INCOMPLETE inputs —
        # propagate it (either side partial -> the cell records partial) so a self
        # comparison can't hide that one side was built from incomplete inputs.
        if result.status == "ok" and outcome.PARTIAL in (comp_env, comp_other):
            result.completion = outcome.PARTIAL

    if result.status == "ok" and out_path.exists():
        # F4: detect the layout from the produced workbook. This path serves EVERY
        # report's vs-TSN/self comparison — Highway Log modes are Route-keyed, but
        # the aggregate reports (Ramp / Intersection Summary) emit a FLAT sheet, so
        # a hardcoded has_route=True read their Status/Diffs one column off and
        # reported 0 diffs. The header tells us the real layout regardless of mode.
        diff_cells, one_sided = _m.read_counts(out_path)
        # F5/P2: fingerprint the cell's TSMIS source folder(s) in the SAME order the
        # snapshot's _cmp_state does (env first; + 'other' for the self PDF-vs-Excel mode),
        # so a route added/removed/resized reads the reused cell stale.
        if mode["kind"] == "tsn":
            fp_folders = (dest / cell_key / mode["env_subdir"],)
        else:                                # self: TSMIS PDF vs Excel (both folders)
            fp_folders = (dest / cell_key / mode["env_subdir"],
                          dest / cell_key / mode["other_subdir"])
        record_tsn_result(dest, f"{row_key}|{mode['id']}", cell_key, result.verdict,
                          diff_cells, one_sided, _safe_mtime(out_path),
                          completion=result.completion or outcome.COMPLETE,
                          input_fingerprint=_cell_input_fingerprint(*fp_folders))
    return result

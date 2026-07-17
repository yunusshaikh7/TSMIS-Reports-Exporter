"""One-click validation (W1, v0.19.0): process every sample already on this PC
through the REAL pipeline and record the outcomes.

The automated replacement for the manual work-PC ride-along: instead of the user
running ad-hoc exports and a command-line evidence flag, ONE Settings button
runs this and ships the result inside the credential-safe evidence bundle
(evidence.collect(validation=...)). Three stages:

  1. environment  — version/build/pins + the selected site (facts only).
  2. tsn_library  — per registered report: freshness status, the D2 auto-heal
                    (ensure_current), status after. A stale library that heals
                    here is itself useful evidence.
  3. comparisons  — for every matrix row with a coded vs-TSN comparison, run
                    the REAL matrix build (matrix.build_comparison, mode 'tsn')
                    against the Export-Everything store for every environment
                    that has that report's data — refreshing the user's actual
                    matrix cells AND recording status/verdict/counts/timings.

This REWRITES the user's live matrix comparison cells for the samples it
processes (the same transactional path the matrix Refresh button uses) — that is
the "process the real samples" promise, disclosed to the user before it runs.

Everything RECORDED is COUNTS + OUTCOMES + folder NAMES — never report data
(the bundle's RM05 promise). Console-free: events + return value only; the
should_cancel poll cancels BETWEEN cells AND before every mutating TSN
heal/build (CMP-AUD-120 — a pre-cancelled run never rewrites a library),
and the events sink's is_cancelled (wired by the worker) cancels DURING a
long single comparison or build.
"""
import logging
import platform
import time
from pathlib import Path

import credential_safety
import consolidation_meta
import matrix
import outcome
import reports as _reports
import settings
import tsn_library
import version
from events import Events
from paths import is_frozen
from site_target import DATA_SOURCES, ENVIRONMENTS

log = logging.getLogger("tsmis.validation")

# The vs-TSN mode id every registered comparison row is validated through.
_TSN_MODE = "tsn"

def _scrub(msg):
    """Redact complete credential values from a user/error message (RM05)."""
    return credential_safety.redact_text(msg)


# tsn_library.resolve kinds that mean "TSN data is present for this report".
_TSN_PRESENT_KINDS = ("consolidated", "file", "pdfs", "raw")


def _env_stage():
    return {
        "app_version": version.__version__,
        "build": "frozen" if is_frozen() else "dev",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "site": "-".join(map(str, _site())),
        "playwright_pin": version.PLAYWRIGHT_VERSION,
    }


def _site():
    try:
        from site_target import get_site
        return get_site()
    except Exception as e:  # noqa: BLE001 — validation must degrade, not die
        log.info("validation: site unreadable (%s: %s)", type(e).__name__, e)
        return ("unknown", "unknown")


def _tsn_stage(events, should_cancel):
    """Per registered report: freshness before, the D2 heal attempt, freshness
    after. Cancellation is polled BEFORE every heal (CMP-AUD-120): a cancelled
    validation may keep READING statuses for the record, but it never rewrites
    a canonical library; the not-attempted state is recorded explicitly."""
    out = []
    for spec in tsn_library.reports():
        before = tsn_library.status(spec.subdir)
        healed = None
        cancelled_before = bool(should_cancel())
        if (not cancelled_before
                and before["consolidated_present"] and before["raw_present"]
                and not before["current"]):
            events.on_log(f"Validation: rebuilding the {spec.label} TSN library…")
            res = tsn_library.ensure_current(spec.subdir, events=events)
            healed = getattr(res, "status", None) if res is not None else None
        after = tsn_library.status(spec.subdir) if healed else before
        out.append({
            "report": spec.subdir,
            "raw_count": before["raw_count"],
            "consolidated_present": before["consolidated_present"],
            "current_before": before["current"],
            "cancelled_before_heal": cancelled_before,
            "healed": healed,
            "current_after": after["current"],
            "normalization_version": spec.normalization_version,
        })
    return out


def _envs_with_data(dest, subdir):
    """The store's <src>-<env> children that hold files for `subdir` (names only).

    Only REAL environment folders count. The store also holds non-environment
    children — the `_tsn_input` TSN drop folder, `comparisons` — and a TSN
    workbook sitting under one of those must never be validated as if it were a
    TSMIS export (the v0.19.0 field bug: `_tsn_input/highway_log/` became a
    phantom environment and its TSN file failed the layout check).
    """
    known = {f"{s}-{e}" for s in DATA_SOURCES for e in ENVIRONMENTS}
    found = []
    try:
        children = sorted(p for p in Path(dest).iterdir()
                          if p.is_dir() and p.name in known)
    except OSError as e:
        log.info("validation: store unreadable (%s: %s)", type(e).__name__, e)
        return found
    for child in children:
        d = child / subdir
        try:
            if d.is_dir() and any(f.is_file() and not f.name.startswith("~$")
                                  for f in d.iterdir()):
                found.append(child.name)
        except OSError:  # silent-ok: an unreadable env dir simply isn't offered
            continue
    return found


def _ensure_tsn_ready(subdir, events, selected_file=None, source=None):
    """True when `subdir` has TSN data the comparison can read — healing a
    stale library, and FIRST-BUILDING a present-but-unconsolidated (raw/pdfs)
    one (CMP-AUD-118: `ensure_current` deliberately returns None when nothing
    is consolidated yet, so raw-only data needs the explicit first-build path;
    it is imported-awaiting-build capability, never a false 'no TSN data')."""
    if not tsn_library.is_registered(subdir):
        return False
    src = source or (tsn_library.resolve(subdir, selected_file)
                     if selected_file else tsn_library.resolve(subdir))
    kind = src.get("kind")
    if kind in ("pdfs", "raw"):
        events.on_log(f"Validation: consolidating the {subdir} TSN library…")
        res = tsn_library.ensure_current(subdir, events=events)
        if res is None:
            res = tsn_library.build_consolidated(subdir, events=events)
        return getattr(res, "status", None) == "ok"
    return kind in _TSN_PRESENT_KINDS


def _run_one(dest, row_key, env, baseline, events, tsn_files=None):
    """One (report, env) comparison against the live store → a result record.
    Never raises — a failing family is recorded, not propagated."""
    events.on_log(f"Validation: comparing {row_key} ({env}) vs TSN…")
    t0 = time.monotonic()
    rec = {"row": row_key, "env": env}
    try:
        res = matrix.build_comparison(dest, row_key, env, _TSN_MODE, baseline, events,
                                      tsn_files=tsn_files or {})
        rec["status"] = res.status
        if res.status != "ok":
            rec["classification"] = (
                "cancelled" if res.status == "cancelled" else "failed")
            rec["completion"] = (
                outcome.CANCELLED if res.status == "cancelled" else outcome.FAILED)
            rec["message"] = _scrub((res.message or "").splitlines()[0][:200])
        else:
            out_path = getattr(res, "output_path", None)
            if not out_path:
                raise ValueError(
                    "comparison returned success without a committed output path")
            try:
                published = consolidation_meta.require_published_comparison(
                    out_path, res)
            except ValueError as e:
                rec["classification"] = "untrusted"
                rec["completion"] = "unknown"
                rec["message"] = _scrub(str(e).splitlines()[0][:200])
            else:
                typed = published.comparison_outcome
                counts = typed.counts
                rec.update({
                    "classification": ("ok" if typed.completion == outcome.COMPLETE
                                       else "partial"),
                    "completion": typed.completion,
                    "verdict": typed.verdict,
                    "counts_known": counts.known,
                    "paired_rows": counts.paired_rows,
                    "side_a_only_rows": counts.side_a_only_rows,
                    "side_b_only_rows": counts.side_b_only_rows,
                    "differing_rows": counts.differing_rows,
                    "diff_cells": counts.differing_cells,
                    "one_sided": counts.side_a_only_rows + counts.side_b_only_rows,
                    "asserted_cells": counts.asserted_cells,
                    "context_cells": counts.context_cells,
                    "skipped_inputs": published.skipped_inputs,
                    "failed_inputs": published.failed_inputs,
                    "generation_id": published.artifact_generation.generation_id,
                })
    except ValueError as e:
        rec["status"] = "error"
        rec["classification"] = "failed"
        rec["completion"] = outcome.FAILED
        rec["message"] = _scrub(str(e).splitlines()[0][:200])
    except Exception as e:  # noqa: BLE001 — one family must not sink the run
        log.warning("validation: %s/%s raised (%s: %s)", row_key, env,
                    type(e).__name__, e)
        rec["status"] = "error"
        rec["classification"] = "failed"
        rec["completion"] = outcome.FAILED
        rec["message"] = _scrub(f"{type(e).__name__}: {str(e).splitlines()[0][:160]}")
    rec["seconds"] = round(time.monotonic() - t0, 1)
    return rec


def _comparisons_stage(events, should_cancel):
    dest = settings.get_batch_dest()
    if not Path(dest).is_dir():
        return {"skipped": "no Export-Everything store yet (run an export first)",
                "cells": []}
    baseline = settings.get_matrix_baseline()
    raw_selections = settings.get_matrix_tsn_selections()
    tsn_files, selections_changed = tsn_library.canonicalize_selections(raw_selections)
    if selections_changed:
        settings.set_matrix_tsn_selections(tsn_files)
    cells = []
    tsn_rows = [(row_key, subdir, tsn_library.canonical_dataset_key(
                 matrix.tsn_subdir_for(row_key, subdir, adapter)))
                for row_key, _label, subdir, _idx, adapter in _reports.matrix_rows()]
    tsn_ready = {}
    for row_key, subdir, tsn_subdir in tsn_rows:
        if should_cancel():
            cells.append({"row": row_key, "skipped": "cancelled"})
            break
        selected = tsn_files.get(tsn_subdir)
        if tsn_subdir not in tsn_ready:
            selected_src = (tsn_library.resolve(tsn_subdir, selected)
                            if selected else tsn_library.resolve(tsn_subdir))
            ready = (False if selected_src.get("kind") == "missing_explicit"
                     else _ensure_tsn_ready(tsn_subdir, events, selected,
                                            source=selected_src))
            tsn_ready[tsn_subdir] = (selected_src, ready)
        selected_src, ready = tsn_ready[tsn_subdir]
        if selected_src.get("kind") == "missing_explicit":
            cells.append({"row": row_key,
                          "skipped": tsn_library.explicit_selection_problem(selected_src)})
            continue
        if not ready:
            cells.append({"row": row_key, "skipped": "no TSN data in the library"})
            continue
        envs = _envs_with_data(dest, subdir)
        if not envs:
            cells.append({"row": row_key, "skipped": "no TSMIS export in the store"})
            continue
        for env in envs:
            if should_cancel():
                cells.append({"row": row_key, "env": env, "skipped": "cancelled"})
                break
            cells.append(_run_one(dest, row_key, env, baseline, events,
                                  tsn_files=tsn_files))
    return {"dest_name": Path(dest).name, "baseline": baseline, "cells": cells}


def _is_full_ok(cell):
    return bool(
        cell.get("status") == "ok"
        and cell.get("classification") == "ok"
        and cell.get("completion") == outcome.COMPLETE
        and cell.get("verdict") in ("match", "diff")
        and cell.get("counts_known") is True
        and isinstance(cell.get("generation_id"), str)
        and cell.get("generation_id"))


def run_validation(events=None, should_cancel=None):
    """The full validation manifest (see the module docstring). Never raises for
    a per-family failure — each is recorded; the bundle ships what happened."""
    events = events or Events()
    should_cancel = should_cancel or (lambda: False)
    t0 = time.monotonic()
    events.on_log("Validation: recording the environment…")
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "environment": _env_stage()}
    events.on_log("Validation: checking the TSN library…")
    manifest["tsn_library"] = _tsn_stage(events, should_cancel)
    events.on_log("Validation: processing the sample comparisons…")
    manifest["comparisons"] = _comparisons_stage(events, should_cancel)
    all_cells = manifest["comparisons"]["cells"]
    ran = [c for c in all_cells if "status" in c]
    full_ok = [c for c in ran if _is_full_ok(c)]
    partial = [c for c in ran if c.get("classification") == "partial"]
    untrusted = [c for c in ran if c.get("classification") == "untrusted"]
    cancelled_cells = [c for c in ran if c.get("classification") == "cancelled"]
    failed = [c for c in ran if c.get("classification") == "failed"]
    blocked = [c for c in all_cells if "status" not in c]
    manifest["totals"] = {
        "comparisons_expected": len(all_cells),
        "comparisons_run": len(ran),
        "comparisons_ok": len(full_ok),               # COMPLETE only — a full, trustable pass
        "comparisons_partial": len(partial),          # ran ok but on incomplete inputs
        "comparisons_untrusted": len(untrusted),
        "comparisons_failed": len(failed),
        "comparisons_cancelled": len(cancelled_cells),
        "comparisons_blocked": len(blocked),
        "cancelled": should_cancel(),
        "seconds": round(time.monotonic() - t0, 1),
    }
    tail = f", {len(partial)} partial" if partial else ""
    events.on_log(f"Validation: {len(full_ok)} of {len(ran)} sample comparisons OK"
                  f"{tail} ({manifest['totals']['seconds']}s).")
    return manifest


def _tsn_state_text(r):
    """The complete CMP-AUD-119 truth table — the heal ATTEMPT is never hidden.

    A rebuild that ran is always disclosed (even when it reached current), a
    rebuild that ran but did NOT reach current is an alarm rather than a
    certification, raw awaiting its first build is a blocked capability rather
    than absent data, and a heal skipped because the user had already
    cancelled says so."""
    healed = r.get("healed")
    if healed == "ok":
        return ("HEALED → current" if r["current_after"]
                else "HEAL RAN BUT STILL STALE")
    if healed is not None:
        return f"HEAL {str(healed).upper()}"     # failed / cancelled / partial
    if r.get("cancelled_before_heal") and not r["current_before"]:
        return "cancelled before heal"
    if r["current_after"]:
        return "current"
    if not r["consolidated_present"]:
        return ("raw imported, awaiting first build" if r["raw_count"]
                else "no data")
    return ("STALE (no raw to rebuild from)" if not r["raw_count"]
            else "STALE")


def summary_lines(manifest):
    """A short human-readable digest for the bundle's report text."""
    env = manifest["environment"]
    lines = [f"app v{env['app_version']} ({env['build']}) · python {env['python']} · "
             f"site {env['site']}"]
    for r in manifest["tsn_library"]:
        lines.append(f"TSN {r['report']}: {_tsn_state_text(r)} "
                     f"(raw files: {r['raw_count']})")
    comps = manifest["comparisons"]
    if comps.get("skipped"):
        lines.append(f"comparisons: {comps['skipped']}")
    for c in comps["cells"]:
        if c.get("skipped"):
            lines.append(f"{c['row']}: skipped — {c['skipped']}")
        elif c.get("status") == "ok":
            classification = c.get("classification")
            partial = classification == "partial"
            qual = " (PARTIAL inputs)" if partial else ""
            if classification == "untrusted" or c.get("diff_cells") is None:
                det = ("UNTRUSTED — "
                       + c.get("message", "outcome metadata unavailable"))
            else:
                det = (f"ok{qual} — {c['diff_cells']:,} diff cells / "
                       f"{c['one_sided']:,} one-sided")
            lines.append(f"{c['row']} ({c.get('env')}): {det} [{c.get('seconds')}s]")
        else:
            lines.append(f"{c['row']} ({c.get('env')}): {c.get('status')} — "
                         f"{c.get('message', '')} [{c.get('seconds')}s]")
    t = manifest["totals"]
    part = f", {t['comparisons_partial']} partial" if t.get("comparisons_partial") else ""
    lines.append(f"TOTAL: {t['comparisons_ok']}/{t['comparisons_run']} fully OK{part} in "
                 f"{t['seconds']}s" + (" (CANCELLED)" if t["cancelled"] else ""))
    return lines

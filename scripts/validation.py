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
should_cancel poll cancels BETWEEN cells and the events sink's is_cancelled
(wired by the worker) cancels DURING a long single comparison.
"""
import logging
import platform
import time
from pathlib import Path

import matrix
import outcome
import reports as _reports
import settings
import tsn_library
import version
from events import Events
from paths import is_frozen

log = logging.getLogger("tsmis.validation")

# The vs-TSN mode id every registered comparison row is validated through.
_TSN_MODE = "tsn"
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


def _tsn_stage(events):
    out = []
    for spec in tsn_library.reports():
        before = tsn_library.status(spec.subdir)
        healed = None
        if before["consolidated_present"] and before["raw_present"] and not before["current"]:
            events.on_log(f"Validation: rebuilding the {spec.label} TSN library…")
            res = tsn_library.ensure_current(spec.subdir, events=events)
            healed = getattr(res, "status", None) if res is not None else None
        after = tsn_library.status(spec.subdir) if healed else before
        out.append({
            "report": spec.subdir,
            "raw_count": before["raw_count"],
            "consolidated_present": before["consolidated_present"],
            "current_before": before["current"],
            "healed": healed,
            "current_after": after["current"],
            "normalization_version": spec.normalization_version,
        })
    return out


def _envs_with_data(dest, subdir):
    """The store's <src-env> children that hold files for `subdir` (names only)."""
    found = []
    try:
        children = sorted(p for p in Path(dest).iterdir() if p.is_dir())
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


def _ensure_tsn_ready(subdir, events):
    """True when `subdir` has TSN data the comparison can read — healing a
    present-but-unconsolidated (raw/pdfs) library first so it counts as a real
    comparison rather than a false 'no consolidated workbook' ERROR."""
    if not tsn_library.is_registered(subdir):
        return False
    src = tsn_library.resolve(subdir)
    kind = src.get("kind")
    if kind in ("pdfs", "raw"):
        events.on_log(f"Validation: consolidating the {subdir} TSN library…")
        res = tsn_library.ensure_current(subdir, events=events)
        return getattr(res, "status", None) == "ok"
    return kind in _TSN_PRESENT_KINDS


def _run_one(dest, row_key, env, baseline, events):
    """One (report, env) comparison against the live store → a result record.
    Never raises — a failing family is recorded, not propagated."""
    events.on_log(f"Validation: comparing {row_key} ({env}) vs TSN…")
    t0 = time.monotonic()
    rec = {"row": row_key, "env": env}
    try:
        res = matrix.build_comparison(dest, row_key, env, _TSN_MODE, baseline, events)
        rec["status"] = res.status
        rec["completion"] = getattr(res, "completion", None) or outcome.COMPLETE
        out_path = getattr(res, "output_path", None)
        if res.status == "ok" and out_path:
            diff_cells, one_sided = matrix.read_counts(out_path)
            rec["diff_cells"] = diff_cells
            rec["one_sided"] = one_sided
            if diff_cells is None:
                rec["counts_unreadable"] = True
        elif res.status != "ok":
            rec["message"] = (res.message or "").splitlines()[0][:200]
    except ValueError as e:
        rec["status"] = "error"
        rec["message"] = str(e).splitlines()[0][:200]
    except Exception as e:  # noqa: BLE001 — one family must not sink the run
        log.warning("validation: %s/%s raised (%s: %s)", row_key, env,
                    type(e).__name__, e)
        rec["status"] = "error"
        rec["message"] = f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"
    rec["seconds"] = round(time.monotonic() - t0, 1)
    return rec


def _comparisons_stage(events, should_cancel):
    dest = settings.get_batch_dest()
    if not Path(dest).is_dir():
        return {"skipped": "no Export-Everything store yet (run an export first)",
                "cells": []}
    baseline = settings.get_matrix_baseline()
    cells = []
    tsn_rows = [(row_key, subdir) for row_key, _label, subdir, _idx, _ad
                in _reports.matrix_rows()]
    for row_key, subdir in tsn_rows:
        if should_cancel():
            cells.append({"row": row_key, "skipped": "cancelled"})
            break
        if not _ensure_tsn_ready(subdir, events):
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
            cells.append(_run_one(dest, row_key, env, baseline, events))
    return {"dest_name": Path(dest).name, "baseline": baseline, "cells": cells}


def _is_full_ok(cell):
    return cell.get("status") == "ok" and cell.get("completion", outcome.COMPLETE) == outcome.COMPLETE


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
    manifest["tsn_library"] = _tsn_stage(events)
    events.on_log("Validation: processing the sample comparisons…")
    manifest["comparisons"] = _comparisons_stage(events, should_cancel)
    ran = [c for c in manifest["comparisons"]["cells"] if "status" in c]
    full_ok = [c for c in ran if _is_full_ok(c)]
    partial = [c for c in ran if c.get("status") == "ok" and not _is_full_ok(c)]
    manifest["totals"] = {
        "comparisons_run": len(ran),
        "comparisons_ok": len(full_ok),               # COMPLETE only — a full, trustable pass
        "comparisons_partial": len(partial),          # ran ok but on incomplete inputs
        "comparisons_failed": len(ran) - len(full_ok) - len(partial),
        "cancelled": should_cancel(),
        "seconds": round(time.monotonic() - t0, 1),
    }
    tail = f", {len(partial)} partial" if partial else ""
    events.on_log(f"Validation: {len(full_ok)} of {len(ran)} sample comparisons OK"
                  f"{tail} ({manifest['totals']['seconds']}s).")
    return manifest


def summary_lines(manifest):
    """A short human-readable digest for the bundle's report text."""
    env = manifest["environment"]
    lines = [f"app v{env['app_version']} ({env['build']}) · python {env['python']} · "
             f"site {env['site']}"]
    for r in manifest["tsn_library"]:
        state = "current" if r["current_after"] else (
            "HEALED" if r["healed"] == "ok" else
            "no data" if not r["consolidated_present"] else "STALE")
        lines.append(f"TSN {r['report']}: {state} (raw files: {r['raw_count']})")
    comps = manifest["comparisons"]
    if comps.get("skipped"):
        lines.append(f"comparisons: {comps['skipped']}")
    for c in comps["cells"]:
        if c.get("skipped"):
            lines.append(f"{c['row']}: skipped — {c['skipped']}")
        elif c.get("status") == "ok":
            partial = c.get("completion", outcome.COMPLETE) != outcome.COMPLETE
            qual = " (PARTIAL inputs)" if partial else ""
            if c.get("counts_unreadable") or c.get("diff_cells") is None:
                det = "ok — counts could not be read from the workbook"
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

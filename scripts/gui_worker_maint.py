"""The maintenance / Settings GUI workers (S2 / ARC-02, split from gui_worker.py).

reset_targets/measure_targets + ResetWorker (Delete all reports),
ChromiumWorker (built-in browser download/delete), ValidationWorker (the
one-click validate-and-package flow), UpdateWorker (the one-click update), and
the launch-time CheckWorker. Verbatim moves; gui_worker re-exports.
"""
import logging
import re
import threading
import time
from pathlib import Path

import owned_dir
import safe_delete
from common import BROWSER_CHANNELS, CHANNEL_LABELS, check_browsers
from events import Events
from paths import (DOWNLOADED_BROWSERS_DIR, FAILURES_DIR, INPUT_ROOT,
                   OUTPUT_ROOT, parse_run_folder)

log = logging.getLogger("tsmis.gui")

# is left alone — only content this app generates is ever deleted.
_LEGACY_OUTPUT_DIRS = ("ramp_summary", "ramp_detail", "highway_sequence",
                       "highway_log", "highway_log_pdf", "intersection_detail_pdf",
                       "consolidated", "tsn_highway_log", "tsmis_highway_log_pdf",
                       "tsmis_intersection_detail_pdf", "run_reports", "comparisons")


def reset_targets(include_input=False, warnings=None):
    """The folders/files "Delete all reports" removes, as (label, Path) pairs
    that currently exist. Reports only — logs, the saved login, the Edge
    sign-in profile and the app's settings are NEVER in this list."""
    targets = []
    try:
        for p in sorted(OUTPUT_ROOT.iterdir()):
            if p.is_dir() and parse_run_folder(p.name):
                targets.append((f"export run folder '{p.name}'", p))
    except OSError:
        pass
    for name in _LEGACY_OUTPUT_DIRS:
        p = OUTPUT_ROOT / name
        if p.is_dir():
            targets.append((f"output folder '{name}'", p))
    for fname, lbl in (("tsn_highway_log_consolidated.xlsx", "TSN consolidated workbook"),
                       ("tsmis_highway_log_pdf_consolidated.xlsx",
                        "TSMIS Highway Log (PDF) consolidated workbook"),
                       ("tsmis_intersection_detail_pdf_consolidated.xlsx",
                        "TSMIS Intersection Detail (PDF) consolidated workbook")):
        p = OUTPUT_ROOT / fname
        if p.is_file():
            targets.append((lbl, p))
    # The Export Everything "always-current" store (configurable destination,
    # default output/All Reports (current)) holds generated reports too. The
    # destination is user-chosen and NOT validated as app-owned, so NEVER rmtree
    # it wholesale — only its known "<src-env>/" children (the exact folders the
    # batch writer creates, BatchWorker out_base = dest/"<src>-<env>"). Any
    # foreign files the user keeps alongside the store are left untouched.
    try:
        from settings import get_batch_dest
        from common import DATA_SOURCES, ENVIRONMENTS
        bdest = Path(get_batch_dest())
        known = {f"{s}-{e}" for s in DATA_SOURCES for e in ENVIRONMENTS}
        if bdest.is_dir():
            for child in sorted(bdest.iterdir()):
                if not child.is_dir():
                    continue
                # SEC-02 (v0.19.0): the ownership MARKER is now REQUIRED — it
                # proves the app created this dir, whatever its name. The legacy
                # name fallback (retired; it stamped-on-sight through v0.18.x) let
                # a user folder that merely LOOKED like a store dir (e.g. their
                # own 'ssor-prod') be deleted. An unmarked dir with a store-like
                # name is now SURFACED as a warning and left untouched.
                by_name = child.name in known or child.name == "comparisons"
                if owned_dir.is_owned(child):
                    targets.append(
                        (f"Export Everything store: {child.name}", child))
                elif by_name:
                    log.warning("reset: %s looks like a store folder but has no "
                                "ownership marker; leaving it untouched", child)
                    if warnings is not None:
                        warnings.append(
                            f"'{child.name}' looks like a store folder but isn't "
                            "marked as created by this app — left untouched "
                            "(delete it manually if it is one)")
    except Exception as e:
        # The delete list is a PROMISE -- if the store can't be enumerated the
        # preview must say so, not silently omit it (the user would believe
        # everything was removed).
        log.warning("reset: could not inspect the Export Everything store "
                    "(%s: %s)", type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        if warnings is not None:
            warnings.append("the Export Everything store could not be "
                            "inspected — its reports may not be listed")
    if FAILURES_DIR.is_dir():
        targets.append(("failure screenshots", FAILURES_DIR))
    if include_input:
        p = INPUT_ROOT / "tsn_highway_log"
        if p.is_dir():
            targets.append(("TSN input PDFs", p))
        # The Export-Everything store's TSN drops (user-placed TSN datasets) are
        # inputs too, so they only clear with include_input (the generated TSN
        # comparison sheets under comparisons/tsn are covered by "comparisons").
        # Deliberately NAME-based (unlike the store children above): the app never
        # CREATES _tsn_input — the user drops files into it — so an ownership
        # marker can't exist; the include_input gate + the preview line make this
        # an explicit, visible choice.
        try:
            from settings import get_batch_dest
            tsn_in = Path(get_batch_dest()) / "_tsn_input"
            if tsn_in.is_dir():
                targets.append(("Export Everything store: _tsn_input", tsn_in))
        except Exception as e:
            log.warning("reset: could not inspect the store's _tsn_input "
                        "(%s: %s)", type(e).__name__, str(e).splitlines()[0] if str(e) else "")
            if warnings is not None:
                warnings.append("the store's _tsn_input folder could not be "
                                "inspected — TSN drops may not be listed")
    return targets


def measure_targets(targets):
    """(file_count, total_bytes) across the target list. Best-effort."""
    files = 0
    size = 0
    for _label, path in targets:
        try:
            if path.is_file():
                files += 1
                size += path.stat().st_size
                continue
            for f in path.rglob("*"):
                if f.is_file():
                    files += 1
                    try:
                        size += f.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return files, size


class ValidationWorker(threading.Thread):
    """W1 one-click validation: runs validation.run_validation over the on-disk
    samples (the automated work-PC ride-along), then builds the credential-safe
    evidence bundle carrying the manifest. Cancellable between comparison cells.
    Posts ('log', ...) progress + one final ('validate_done', {ok, path, ...})."""

    def __init__(self, queue, cancel_event=None):
        super().__init__(daemon=True, name="validate")
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        import validation
        import evidence
        should_cancel = (lambda: self.cancel is not None and self.cancel.is_set())
        # is_cancelled lets a long SINGLE comparison stop mid-flight (compare_core
        # polls it); should_cancel stops BETWEEN cells. Both read the one event.
        events = Events(on_log=lambda t: self.q.put(("log", t)),
                        is_cancelled=should_cancel)
        # ONE terminal is guaranteed no matter what fails (validation OR the bundle
        # build) — an un-posted validate_done would wedge the single-task gate.
        terminal = {"ok": False, "message": "validation did not complete"}
        try:
            manifest = validation.run_validation(events=events,
                                                 should_cancel=should_cancel)
            self.q.put(("log", "Building the evidence bundle (logs + the "
                               "validation manifest)…"))
            # run_self_test=False: the validation manifest IS this button's
            # evidence. The offline self-test launches a browser + a SECOND
            # WebView2 window, which is unsafe to do from a worker thread while
            # the live GUI already owns the main-thread webview loop. The
            # standalone `--collect-evidence` process keeps the self-test (it
            # exits before any window opens).
            res = evidence.collect(emit=lambda ln: self.q.put(("log", ln)),
                                   run_self_test=False, validation=manifest)
            totals = manifest.get("totals", {})
            terminal = {
                "ok": bool(res.get("ok")),
                "path": res.get("path"),
                "comparisons_run": totals.get("comparisons_run", 0),
                "comparisons_ok": totals.get("comparisons_ok", 0),
                "cancelled": totals.get("cancelled", False),
            }
        except Exception as e:                   # noqa: BLE001 — never wedge the gate
            log.warning("validation worker failed (%s: %s)", type(e).__name__,
                        str(e).splitlines()[0] if str(e) else "")
            self.q.put(("log", f"Validation could not run: {type(e).__name__}."))
            terminal = {"ok": False, "message": f"{type(e).__name__}: {e}"}
        finally:
            self.q.put(("validate_done", terminal))


class ResetWorker(threading.Thread):
    """"Delete all reports": removes every generated report (run folders,
    legacy flat folders, consolidated/comparison output, run reports, failure
    screenshots, TSN conversions — and the TSN input PDFs only when asked).
    Logs, the saved login and the app settings always survive. Files an open
    Excel still holds are reported, never silently skipped. Posts progress as
    ('log', ...) lines and one final ('reset_done', {files, mb, errors})."""

    def __init__(self, queue, include_input=False, cancel_event=None):
        super().__init__(daemon=True, name="reset")
        self.q = queue
        self.include_input = include_input
        self.cancel = cancel_event

    def run(self):
        targets = reset_targets(self.include_input)
        files, size = measure_targets(targets)
        errors = []
        cancelled = False
        ui = logging.getLogger("tsmis.ui")
        log.info("reset: deleting %d target(s), %d file(s), %.1f MB (input=%s)",
                 len(targets), files, size / 1e6, self.include_input)
        for label, path in targets:
            # Cancellable between targets (a partial delete is harmless -- a
            # re-run removes the rest). The current folder finishes first.
            if self.cancel is not None and self.cancel.is_set():
                cancelled = True
                self.q.put(("log", "  Cancelled — stopped after the current item."))
                break
            failures = []

            def on_error(_fn, p, _exc):
                failures.append(str(p))

            try:
                if path.is_file():
                    path.unlink()
                else:
                    # Junction/symlink-safe: a reparse point INSIDE (or AS) a
                    # target is unlinked, never recursed through, so "Delete all
                    # reports" can never escape into a link's target outside the
                    # folder being cleared (safe_delete; same onerror contract as
                    # shutil.rmtree so locked files are still reported).
                    safe_delete.scoped_rmtree(path, onerror=on_error)
            except OSError as e:
                failures.append(f"{path} ({type(e).__name__})")
            if failures:
                msg = (f"Could not delete {len(failures)} item(s) from {label} — "
                       "a file is probably open in Excel.")
                errors.append(msg)
                ui.info("reset: %s: %s", msg, failures[:5])
                self.q.put(("log", f"  {msg}"))
            else:
                self.q.put(("log", f"  Deleted {label}."))
        # Report what was ACTUALLY freed (before − what remains), so files held
        # open in Excel (or skipped by a cancel) aren't counted as deleted.
        remaining_files, remaining_size = measure_targets(targets)
        freed_files = max(0, files - remaining_files)
        freed_size = max(0, size - remaining_size)
        self.q.put(("reset_done", {"files": freed_files,
                                   "mb": round(freed_size / 1e6, 1),
                                   "errors": errors, "cancelled": cancelled}))


class ChromiumWorker(threading.Thread):
    """Download or delete the app-owned Built-in Chromium (Settings tab).

    Download drives the BUNDLED Playwright Node driver exactly the way
    `playwright install chromium --no-shell` would — that works in the frozen
    app (where there is no `python -m playwright`) and in dev runs alike —
    aimed at paths.DOWNLOADED_BROWSERS_DIR via PLAYWRIGHT_BROWSERS_PATH, so
    the browser lands in the app's own data folder (survives one-click
    updates, removable from the same Settings section). Installer progress is
    forwarded to the log (throttled); no console window is flashed. Delete
    removes ONLY that folder — never the with-browser bundle's
    `_internal\\ms-playwright`. Cancel (the shared cancel_event) kills the
    download; Playwright downloads to a temp name first, so a killed install
    can simply be retried.

    Posts ("log", …) progress + one ("chromium_done",
    {ok, action, cancelled, error})."""

    def __init__(self, queue, action, cancel_event):
        super().__init__(daemon=True, name="chromium")
        self.q = queue
        self.action = action            # "download" | "delete"
        self.cancel = cancel_event

    def run(self):
        out = {"ok": False, "action": self.action, "cancelled": False,
               "error": None}
        try:
            if self.action == "download":
                out["cancelled"] = not self._download()
                out["ok"] = not out["cancelled"]
            else:
                self._delete()
                out["ok"] = True
        except Exception as e:
            log.exception("chromium %s failed", self.action)
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            out["error"] = reason
        self.q.put(("chromium_done", out))

    def _download(self):
        """Run the bundled driver's installer. Returns False when cancelled."""
        import os
        import subprocess

        from playwright._impl._driver import compute_driver_executable
        try:
            from playwright._impl._driver import get_driver_env
            env = dict(get_driver_env())
        except ImportError:
            env = dict(os.environ)
        cmd = compute_driver_executable()
        cmd = list(cmd) if isinstance(cmd, (list, tuple)) else [str(cmd)]
        DOWNLOADED_BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(DOWNLOADED_BROWSERS_DIR)
        log.info("chromium: download starting -> %s (driver %s)",
                 DOWNLOADED_BROWSERS_DIR, cmd[0])
        self.q.put(("log", "Downloading the Built-in Chromium (~170 MB)…"))
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            cmd + ["install", "chromium", "--no-shell"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=env, creationflags=creationflags)
        last_emit = 0.0
        last_line = ""
        try:
            for line in proc.stdout:
                if self.cancel.is_set():
                    proc.kill()
                    proc.wait()
                    log.info("chromium: download cancelled by user")
                    self.q.put(("log", "Download cancelled."))
                    return False
                # The installer colors its output; ANSI codes would land in
                # the log pane as "[2m" noise.
                line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
                if not line:
                    continue
                last_line = line
                now = time.monotonic()
                if now - last_emit >= 2.0:        # the installer is chatty
                    self.q.put(("log", f"  {line}"))
                    last_emit = now
        finally:
            proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            log.warning("chromium: installer exited %s (last: %s)", rc, last_line)
            raise RuntimeError(
                "The browser download didn't complete (check the network / "
                "VPN connection and try again).")
        if not any(DOWNLOADED_BROWSERS_DIR.glob("chromium-*")):
            raise RuntimeError("The download finished but no browser was "
                               "found afterwards (details in the log).")
        log.info("chromium: download complete")
        return True

    def _delete(self):
        import shutil
        if not DOWNLOADED_BROWSERS_DIR.is_dir():
            self.q.put(("log", "There was no downloaded browser to remove."))
            return
        failures = []
        shutil.rmtree(DOWNLOADED_BROWSERS_DIR,
                      onerror=lambda _fn, p, _exc: failures.append(str(p)))
        if failures or DOWNLOADED_BROWSERS_DIR.exists():
            log.warning("chromium: delete left %d item(s): %s",
                        len(failures), failures[:5])
            raise RuntimeError(
                "Some browser files couldn't be removed — close the app and "
                "delete the data\\ms-playwright folder by hand, or restart "
                "and try again.")
        log.info("chromium: downloaded browser deleted")


class UpdateWorker(threading.Thread):
    """Drives the one-click update (updater.py) off the GUI thread: action
    "check" compares the latest GitHub release tag to this build; action
    "download" streams + stages the matching release zip. Network + disk
    only, no Playwright. Posts ('update_status', {phase, ...}) — the dict is
    the GUI's whole update state; see gui_api._on_update_status.

    `manual` marks a user-initiated check (the outcome is shown in the log
    pane; the automatic launch check stays quiet unless an update exists).
    """

    def __init__(self, queue, action, manual=False, info=None):
        super().__init__(daemon=True, name="update")
        self.q = queue
        self.action = action            # "check" | "download" | "revert"
        self.manual = manual
        self.info = info                # UpdateInfo (required for "download")

    def run(self):
        import updater                  # lazy; stdlib-only module
        revert = self.action == "revert"
        try:
            if self.action == "check":
                info = updater.check_for_update()
                if info is None:
                    self.q.put(("update_status", {"phase": "none",
                                                  "manual": self.manual}))
                    return
                self.q.put(("update_status", {
                    "phase": "available",
                    "version": info.version,
                    "url": info.release_url,
                    "size_mb": round(info.asset_size / 1e6) or None,
                    "can_apply": updater.update_support()[0] == "ok",
                    "manual": self.manual,
                    "_info": info,      # kept Python-side; stripped before JS
                }))
                return

            if revert:
                # Resolve the newest full release older than this build, then
                # stage it through the SAME proven download path as an update.
                self.info = updater.resolve_previous_release()
                if self.info is None:
                    self.q.put(("update_status", {
                        "phase": "none", "manual": True, "revert": True,
                        "note": "no earlier version was found to revert to"}))
                    return

            last_pct = -1               # "download" / "revert"

            def on_progress(done, total):
                nonlocal last_pct
                pct = min(100, int(done * 100 / total)) if total else 0
                if pct != last_pct:
                    last_pct = pct
                    self.q.put(("update_status", {
                        "phase": "downloading", "progress": pct,
                        "version": self.info.version,
                        "url": self.info.release_url, "can_apply": True,
                        "revert": revert}))

            staged = updater.download_and_stage(self.info, on_progress=on_progress)
            self.q.put(("update_status", {
                "phase": "staged", "version": self.info.version,
                "url": self.info.release_url, "can_apply": True,
                "staged": str(staged), "revert": revert}))
        except updater.UpdateError as e:
            log.warning("update %s failed: %s", self.action, e)
            self.q.put(("update_status", {
                "phase": "failed", "note": str(e),
                "manual": self.manual or self.action in ("download", "revert"),
                "revert": revert}))
        except Exception as e:
            log.exception("update worker crashed (%s)", self.action)
            self.q.put(("update_status", {
                "phase": "failed", "note": f"{type(e).__name__}: {e}",
                "manual": self.manual or self.action in ("download", "revert"),
                "revert": revert}))


# --- startup readiness checks -------------------------------------------------
# (Login isn't checked here -- the header status row + Log in button own it.)


def _check_output():
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        probe = OUTPUT_ROOT / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return ("ok", "Output folder: writable")
    except Exception:
        return ("bad", "Output folder: NOT writable")


def _check_tools():
    try:
        import pdfplumber  # noqa: F401
        import openpyxl    # noqa: F401
        return ("ok", "Report tools (PDF/Excel): ready")
    except Exception as e:
        return ("bad", f"Report tools: missing ({type(e).__name__})")


class CheckWorker(threading.Thread):
    """Runs the launch-time readiness checks off the GUI pump thread, posting each
    result as ('check', (key, status, text)) and a final ('checks_done', dict).

    The instant checks (login, output folder, PDF/Excel tools) are posted first;
    the browser probes are slower (each launches a headless browser) so they land
    a couple seconds later. status is one of 'ok' | 'bad'.
    """

    def __init__(self, queue):
        super().__init__(daemon=True, name="checks")
        self.q = queue

    def run(self):
        for key, fn in (("output", _check_output), ("tools", _check_tools)):
            try:
                status, text = fn()
            except Exception as e:
                status, text = "bad", f"{key}: error ({type(e).__name__})"
            if status != "ok":
                log.warning("readiness check %s: %s", key, text)
            self.q.put(("check", (key, status, text)))

        try:
            results = check_browsers()           # {channel: ok|missing|broken}
        except Exception:
            log.exception("browser readiness check crashed")
            results = {ch: "broken" for ch in BROWSER_CHANNELS}
        detail = {"ok": "ready", "missing": "not installed",
                  "broken": "found, but this tool can't control it (it may be too new)"}
        for ch in BROWSER_CHANNELS:
            status = results.get(ch, "broken")
            self.q.put(("check", (f"browser_{ch}", "ok" if status == "ok" else "bad",
                                   f"{CHANNEL_LABELS[ch]}: {detail[status]}")))
        self.q.put(("checks_done", results))

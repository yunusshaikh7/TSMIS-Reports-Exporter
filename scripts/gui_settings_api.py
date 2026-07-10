"""GuiSettingsMixin — extracted verbatim from gui_api.GuiApi (S1 / ARC-02, v0.19.0):
settings get/set + maintenance (reset, validate, debug logging, evidence)
and the built-in Chromium download/delete flow.
Composition only — every `self._*` it touches lives on GuiApi.
"""
import logging
import secrets
import time
from pathlib import Path

import webview

import settings
import updater
from common import (BROWSER_CHANNELS, CHANNEL_LABELS, DATA_SOURCES,
                    DATA_SOURCE_LABELS, ENVIRONMENTS, ENVIRONMENT_LABELS,
                    clear_auth, default_site_url, dev_site_url, get_site,
                    has_valid_auth)
from exporter_parallel import MAX_WORKERS
from gui_endpoint import _api_method, _task_endpoint, pick_path
from gui_worker import (ChromiumWorker, ConsolidateWorker, ResetWorker,
                        ValidationWorker, measure_targets, reset_targets)
from logging_setup import active_log_file, set_debug_logging
from paths import (BUNDLED_BROWSERS_DIR, DATA_ROOT, DOWNLOADED_BROWSERS_DIR,
                   FAILURES_DIR, LOG_DIR, OUTPUT_ROOT, TSN_LIBRARY_ROOT,
                   is_frozen, list_output_days)
from version import __version__

log = logging.getLogger("tsmis.gui")
ui_log = logging.getLogger("tsmis.ui")


class GuiSettingsMixin:
    # ---- settings & maintenance -----------------------------------------------

    def _site_url_rows(self):
        """All six (src, env) combos with their effective / default URLs —
        the Settings tab's editable "site addresses" list."""
        overrides = settings.all_site_urls()
        rows = []
        for src in DATA_SOURCES:
            for env in ENVIRONMENTS:
                key = f"{src}-{env}"
                default = default_site_url(src, env)
                custom = overrides.get(key)
                rows.append({
                    "key": key, "source": src, "environment": env,
                    "label": f"{DATA_SOURCE_LABELS[src]} · {ENVIRONMENT_LABELS[env]}",
                    "default": default,
                    "url": custom or default,
                    "custom": bool(custom),
                })
        return rows

    _chromium_size_cache = None      # (downloaded, size_mb) — PRF-02; a full
                                     # rglob over ~10k browser files costs ~0.5 s,
                                     # and the answer only changes on download/
                                     # delete (ChromiumWorker invalidates it).

    def _chromium_state(self):
        """What the Settings tab's Built-in Chromium section shows."""
        bundled = bool(BUNDLED_BROWSERS_DIR and BUNDLED_BROWSERS_DIR.is_dir())
        downloaded = False
        size_mb = 0
        try:
            if DOWNLOADED_BROWSERS_DIR.is_dir():
                downloaded = any(DOWNLOADED_BROWSERS_DIR.glob("chromium-*"))
                if downloaded:
                    cached = type(self)._chromium_size_cache
                    if cached is not None and cached[0] == downloaded:
                        size_mb = cached[1]
                    else:
                        size_mb = round(sum(
                            f.stat().st_size
                            for f in DOWNLOADED_BROWSERS_DIR.rglob("*") if f.is_file()
                        ) / 1e6)
                        type(self)._chromium_size_cache = (downloaded, size_mb)
        except OSError as e:
            # best-effort sizing — the Settings panel still renders (downloaded may
            # read False / 0 MB); log so a recurring read failure is diagnosable (P7a).
            log.info("settings: couldn't inspect the downloaded Chromium (%s: %s)",
                     type(e).__name__, e)
        return {
            "bundled": bundled,
            "downloaded": downloaded,
            "downloaded_mb": size_mb,
            # whether THIS process can already use a Built-in Chromium
            # (channels are probed at startup; changes need a restart)
            "active": "chromium" in BROWSER_CHANNELS,
            "dir": str(DOWNLOADED_BROWSERS_DIR),
        }

    @_api_method
    def get_settings(self):
        """Everything the Settings tab shows: the saved knobs plus read-only
        build/paths facts (so problems are diagnosable from the screen)."""
        auth_state = "saved login" if has_valid_auth() else (
            "automatic sign-in" if self._device_ok else "none")
        return {
            "values": settings.all_settings(),
            "defaults": dict(settings.DEFAULTS),
            "site_urls": self._site_url_rows(),
            "chromium": self._chromium_state(),
            # Which Chromium-class browser does exports/fast/login-capture. The
            # Settings control only matters when BOTH exist (else it's just info);
            # Edge is the implicit one-click path, never listed here.
            "export_browser": {
                "value": settings.get_export_browser() or "auto",
                "chrome_ok": self._checks.get("browser_chrome", {}).get("status") == "ok",
                "chromium_present": "chromium" in BROWSER_CHANNELS,
                "labels": {c: CHANNEL_LABELS[c] for c in ("chromium", "chrome")},
            },
            "tsn_library": self._tsn_library_status(),
            "tsn_library_root": str(TSN_LIBRARY_ROOT),   # the on-disk TSN home

            "meta": {
                "version": __version__,
                "build": "portable app" if is_frozen() else "development run",
                "variant": ("with built-in browser"
                            if "chromium" in BROWSER_CHANNELS else "system browser"),
                "data_root": str(DATA_ROOT),
                "output_root": str(OUTPUT_ROOT),
                "log_file": str(active_log_file()),
                "failures_dir": str(FAILURES_DIR),
                "auth_state": auth_state,
                "max_workers": MAX_WORKERS,
                # "ok" = writable packaged install (can self-update/revert);
                # "link" = read-only; "off" = dev run. Gates the Revert control.
                "update_support": updater.update_support()[0],
            },
        }

    @_api_method
    def set_site_url(self, source, environment, url):
        """Save (or clear, with an empty value) one environment's TSMIS
        address. Applies to the very next sign-in / export / verify — the
        stopgap for "the site moved before an app update shipped"."""
        url = (url or "").strip()
        if url == default_site_url(source, environment):
            url = ""                      # typing the default back = no override
        try:
            settings.set_site_url(source, environment, url)
        except ValueError as e:
            return {"error": str(e), "site_urls": self._site_url_rows()}
        label = f"{DATA_SOURCE_LABELS.get(source, source)} / " \
                f"{ENVIRONMENT_LABELS.get(environment, environment)}"
        if url:
            self._emit_log(f"Site address for {label} changed to {url} "
                           "(used from the next sign-in or export on).")
        else:
            self._emit_log(f"Site address for {label} reset to the default.")
        return {"ok": True, "site_urls": self._site_url_rows()}

    @_api_method
    def apply_site_preset(self, preset):
        """Point ALL six site addresses at a preset in one click: 'dev' (the
        development host tsmis-dev.dot.ca.gov — where Intersection reports are
        available) or 'prod' (clear every override → the built-in production
        addresses). Returns the refreshed site-URL rows for the Settings list."""
        if preset not in ("dev", "prod"):
            return {"error": "Unknown site preset."}
        failed = []
        for src in DATA_SOURCES:
            for env in ENVIRONMENTS:
                url = dev_site_url(src, env) if preset == "dev" else ""
                try:
                    settings.set_site_url(src, env, url)
                except ValueError as e:
                    failed.append(f"{src}-{env}: {e}")
        if failed:
            self._emit_log("Some site addresses couldn't be set: " + "; ".join(failed))
            return {"error": "Some addresses couldn't be set — see the log.",
                    "site_urls": self._site_url_rows()}
        self._emit_log("All site addresses set to the "
                       + ("development site (tsmis-dev.dot.ca.gov) — Intersection "
                          "reports are available there." if preset == "dev"
                          else "built-in production addresses."))
        self._push_state()
        return {"ok": True, "site_urls": self._site_url_rows()}

    # ---- Built-in Chromium download / delete -----------------------------------

    def _start_chromium(self, action, start_log):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("chromium")   # claim + bump epoch (gate already checked)
        self.cancel_event.clear()
        self._emit_log(start_log)
        self._set_dot("busy", "Working on the Built-in Chromium…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": ("Downloading the Built-in Chromium…"
                              if action == "download" else
                              "Removing the Built-in Chromium…")})
        self._push_state()
        ChromiumWorker(self._gated_queue(), action, self.cancel_event).start()
        return {"ok": True}

    @_api_method
    def download_chromium(self):
        """Download the Built-in Chromium into the app's data folder (the
        same browser the with-browser variant ships; ~170 MB). Restart to
        select it — browsers are probed at startup."""
        if self._chromium_state()["downloaded"]:
            return {"error": "A downloaded Built-in Chromium is already here. "
                             "Delete it first to re-download."}
        ui_log.info("chromium: user started download")
        return self._start_chromium(
            "download", "Downloading the Built-in Chromium (~170 MB)…")

    @_api_method
    def delete_chromium(self):
        """Remove the DOWNLOADED Built-in Chromium (the with-browser bundle's
        own copy is part of the app and is never touched)."""
        if not self._chromium_state()["downloaded"]:
            return {"error": "There is no downloaded Built-in Chromium to remove."}
        ui_log.info("chromium: user started delete")
        return self._start_chromium(
            "delete", "Removing the downloaded Built-in Chromium…")

    def _on_chromium_done(self, payload):
        # PRF-02: a download/delete changed the browser tree — drop the size cache.
        type(self)._chromium_size_cache = None
        if payload.get("cancelled"):
            self._emit_log("Built-in Chromium download cancelled.")
        elif not payload.get("ok"):
            msg = payload.get("error") or "Something went wrong (see the log)."
            self._emit_log(f"ERROR: {msg}")
            self._emit_modal("error", "Built-in Chromium", msg)
        elif payload.get("action") == "download":
            self._emit_log("Built-in Chromium downloaded. Restart the app, then "
                           "pick it under Settings ▸ Export browser (browsers "
                           "are probed at startup).")
            self._emit_modal("info", "Built-in Chromium downloaded",
                             "The browser is in place. Restart the app, then "
                             "choose it under Settings ▸ Export browser.")
        else:
            self._emit_log("Downloaded Built-in Chromium removed."
                           + (" Restart the app to finish switching back to "
                              "Edge/Chrome." if self._chromium_state()["active"]
                              else ""))
        self._set_dot("ok" if self._authed else "bad", "Done")
        # Refresh the Settings tab's section (JS swaps in the new state).
        self._emit({"t": "settings", "s": self.get_settings()})
        self._end_task()

    @_api_method
    def set_setting(self, key, value):
        """Persist one setting and apply any live side effect. Timeouts and
        the worker default are read at run start, so they apply to the next
        run; verbose logging switches immediately; DevTools applies on the
        next launch."""
        new = settings.update({key: value})
        if key == "debug_logging":
            set_debug_logging(new["debug_logging"])
        if key == "fast_workers":
            # The matrix corner spinner reads this back from the snapshot
            # (matrix_fast.workers); push so an unrelated state event can't revert it.
            self._push_state()
        ui_log.info("settings: %s = %r", key, new.get(key))
        return {"ok": True, "values": new}

    @_api_method
    def reset_preview(self, include_input=False):
        """What "Delete all reports" would remove right now — shown in the
        confirm dialog so the user approves a concrete list, not a vibe. Also
        issues the single-use confirm token start_reset requires (server-side
        gate: the delete can't run unless a preview was shown for the same
        include_input)."""
        include_input = bool(include_input)
        warns = []
        targets = reset_targets(include_input, warnings=warns)
        files, size = measure_targets(targets)
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._reset_token = (token, include_input)
        # Enumeration warnings ride the LABEL list only (no path -> the dialog
        # renders them as plain lines); the delete path never sees them.
        return {"targets": [label for label, _p in targets]
                           + [f"⚠ {w}" for w in warns],
                # The concrete paths too, so the confirm dialog shows EXACTLY
                # what will be deleted (the labels alone hid the real location of
                # the user-chosen Export Everything store).
                "paths": [str(p) for _label, p in targets],
                "files": files, "mb": round(size / 1e6, 1), "token": token}

    @_api_method
    def start_reset(self, include_input=False, confirm_token=None):
        """Delete all generated reports. Server-side confirmation: requires the
        single-use token reset_preview issued for the SAME include_input, so a
        direct bridge call can't skip the preview the user approved. Logs, the
        saved login and the settings always survive."""
        include_input = bool(include_input)
        with self._lock:
            expected = self._reset_token
            self._reset_token = None        # single-use: consume it either way
        if not expected or confirm_token != expected[0] or expected[1] != include_input:
            ui_log.warning("reset: refused — no matching confirmation (a preview "
                           "must be shown first)")
            return {"error": "Please confirm the delete from the dialog "
                             "(open 'Delete all reports' again)."}
        err = self._claim_task_error("reset")
        if err:
            return err
        ui_log.info("reset: user confirmed delete-all-reports (input=%s)",
                    include_input)
        self.cancel_event.clear()
        self._emit_log("Deleting all reports…")
        self._set_dot("busy", "Deleting reports…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Deleting reports…"})
        self._push_state()
        ResetWorker(self._gated_queue(), include_input=include_input,
                    cancel_event=self.cancel_event).start()
        return {"ok": True}

    def _on_reset_done(self, payload):
        if payload.get("errors"):
            self._emit_log(f"Deleted {payload['files']} file(s) "
                           f"({payload['mb']} MB), but some items couldn't be "
                           "removed:")
            for line in payload["errors"]:
                self._emit_log(f"  {line}")
            self._emit_modal("warning", "Some files couldn't be deleted",
                             "Close any report files still open in Excel, "
                             "then run 'Delete all reports' again.")
        elif payload.get("cancelled"):
            self._emit_log(f"Cancelled — deleted {payload['files']} file(s) "
                           f"({payload['mb']} MB) before stopping. Logs, your "
                           "login and settings were kept.")
        else:
            self._emit_log(f"Done — deleted {payload['files']} file(s), "
                           f"freed {payload['mb']} MB. Logs, your login and "
                           "settings were kept.")
        self._set_dot("ok" if self._authed else "bad", "Done")
        self._end_task()

    @_task_endpoint("validate")
    def run_validation(self):
        """W1: one-click validation — process every on-disk sample through the
        REAL comparison pipeline, then package the outcomes into the
        credential-safe evidence bundle. The automated replacement for the manual
        work-PC ride-along (no command line, no ad-hoc exports). Cancellable."""
        self.cancel_event.clear()
        self._emit_log("Validating: processing the samples on this PC…")
        self._set_dot("busy", "Validating…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Validating the samples…"})
        self._push_state()
        ValidationWorker(self._gated_queue(),
                         cancel_event=self.cancel_event).start()
        return {"ok": True}

    def _on_validate_done(self, payload):
        if payload.get("ok"):
            ran = payload.get("comparisons_run", 0)
            ok = payload.get("comparisons_ok", 0)
            partial = payload.get("comparisons_partial", 0)
            tail = " (cancelled early)" if payload.get("cancelled") else ""
            ptail = f", {partial} on partial inputs" if partial else ""
            self._emit_log(f"Validation complete{tail}: {ok} of {ran} sample "
                           f"comparisons fully OK{ptail}. Evidence bundle saved:")
            self._emit_log(f"  {payload.get('path')}")
            self._emit_modal("info", "Validation complete",
                             f"Processed {ran} sample comparison(s); {ok} fully "
                             f"succeeded{ptail}{tail}.\n\nThe evidence bundle "
                             "(everything a maintainer needs) was saved to:\n"
                             f"{payload.get('path')}")
        else:
            self._emit_log("Validation could not complete: "
                           f"{payload.get('message', 'unknown error')}")
            self._emit_modal("warning", "Validation didn't finish",
                             payload.get("message", "See the log for details."))
        self._set_dot("ok" if self._authed else "bad", "Done")
        self._end_task()

    @_api_method
    def capture_site_source(self):
        """Capture the ACTIVE site's report-page source into a dated folder
        under output/site-capture/ — the rendered DOM, the raw page HTML, and
        every same-origin script/stylesheet (the maintainer's manual
        devtools ▸ Sources walk, one click). Signs in with the saved session
        (or device sign-in) and runs on the shared single-task slot so
        progress shows in the activity log like any other run."""
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        src, env = get_site()
        self._emit_log(f"Capturing the website source ({src.upper()}-{env.upper()})…")
        self._set_dot("busy", "Capturing site source…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Capturing site source…"})
        self._push_state()

        def _run(events=None, confirm_overwrite=None, day=None):   # noqa: ARG001
            import site_capture                    # lazy: pulls playwright
            return site_capture.capture(events=events)

        ConsolidateWorker(_run, self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    @_api_method
    def open_site_captures_folder(self):
        """Open the site-capture output root (created on first use)."""
        import site_capture                        # lazy (light, but keep parity)
        root = site_capture.capture_root()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError:  # silent-ok: creation is a courtesy; the open below falls back to output/
            pass
        self._open_folder(root if root.is_dir() else OUTPUT_ROOT)
        return {"ok": True}

    @_api_method
    def save_support_bundle(self):
        """Zip the diagnostics a maintainer needs (rotating logs, run reports,
        settings, a manifest) to a user-chosen location.

        What it does NOT contain: the saved login / browser profiles / failure
        dumps (FAILURES_DIR) are never added. What it DOES contain, by design:
        the rotating logs and the manifest, which include this PC's name in file
        paths, the OS version, and an ALLOWLISTED subset of diagnostic settings
        (settings.support_bundle_settings(), not all_settings() — so no site_urls /
        batch_dest / future sensitive key leaks) — diagnostics need those. So it's
        safe to send to the TSMIS maintainer, not "safe to post publicly"; the
        user-facing wording below says so plainly."""
        import io
        import platform
        import zipfile

        default = f"tsmis_support_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        picked = pick_path(self._window,
            webview.SAVE_DIALOG, save_filename=default,
            file_types=("Zip archive (*.zip)",))
        if not picked:
            return {"cancelled": True}
        out = Path(picked)

        manifest = io.StringIO()
        src, env = get_site()
        manifest.write(f"TSMIS Exporter support bundle\n"
                       f"NOTE: includes this PC's name in file paths, the OS\n"
                       f"  version and selected diagnostic settings (diagnostics need them);\n"
                       f"  NO saved login, browser profile, or failure dumps.\n"
                       f"  Send it to the TSMIS maintainer, not a public forum.\n"
                       f"created:    {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                       f"version:    {__version__}\n"
                       f"build:      {'frozen' if is_frozen() else 'dev'}\n"
                       f"python:     {platform.python_version()}\n"
                       f"os:         {platform.platform()}\n"
                       f"data_root:  {DATA_ROOT}\n"
                       f"output:     {OUTPUT_ROOT}\n"
                       f"site:       src={src} env={env}\n"
                       f"browsers:   {list(BROWSER_CHANNELS)} (picked: {self._channel})\n"
                       f"login:      {'saved file' if has_valid_auth() else 'none'}"
                       f"{' + device sign-in' if self._device_ok else ''}\n"
                       f"settings:   {settings.support_bundle_settings()}\n"
                       f"run folders: {list_output_days() or '(none)'}\n")
        added = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.txt", manifest.getvalue())
            for pattern, arc in (("tsmis.log*", "logs"), ("crash.log", "logs"),
                                 ("update_helper.log", "logs")):
                for f in sorted(LOG_DIR.glob(pattern)):
                    try:
                        zf.write(f, f"{arc}/{f.name}")
                        added += 1
                    except OSError as e:
                        # one locked/unreadable log shouldn't sink the whole bundle —
                        # skip it, but log which so a maintainer knows it's absent (P7a).
                        ui_log.info("support bundle: skipped %s (%s: %s)",
                                    f.name, type(e).__name__, e)
            reports = sorted((OUTPUT_ROOT / "run_reports").glob("*.csv"),
                             key=lambda p: p.stat().st_mtime, reverse=True)[:50]
            for f in reports:
                try:
                    zf.write(f, f"run_reports/{f.name}")
                    added += 1
                except OSError as e:
                    ui_log.info("support bundle: skipped run report %s (%s: %s)",
                                f.name, type(e).__name__, e)
        ui_log.info("support bundle saved: %s (%d files)", out, added)
        self._emit_log(f"Support bundle saved ({added} files): {out}")
        self._emit_log("  It has logs, run reports and selected diagnostic settings "
                       "(and this PC's name in paths) — never your password or saved "
                       "login. Send it to the TSMIS maintainer.")
        return {"saved": str(out)}

    @_api_method
    def clear_saved_login(self):
        """Settings-tab action: forget the saved session (the file is deleted;
        automatic device sign-in, when available, is unaffected)."""
        removed = clear_auth()
        with self._lock:
            self._authed = False
        self._refresh_auth()
        self._emit_log("Saved login deleted — click 'Log in' to sign in again."
                       if removed else "There was no saved login to delete.")
        self._push_state()
        return {"ok": True, "removed": removed}

    @_api_method
    def open_failures_folder(self):
        self._open_folder(FAILURES_DIR)
        return {"ok": True}

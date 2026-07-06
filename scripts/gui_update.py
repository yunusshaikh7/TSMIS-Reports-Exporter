"""GuiUpdateMixin — the one-click in-app update endpoints (S1 / ARC-02).

Extracted verbatim from gui_api.GuiApi (v0.19.0): the version-chip check, the
download/stage/apply flow driven by UpdateWorker, and the update-state pushes.
Composition only — GuiApi mixes this in; every `self._*` it touches lives on
GuiApi (the queue, the state push, the coordinator proxies).
"""
import logging
import os
import threading
import time
import webbrowser

import updater
from gui_endpoint import _api_method
from gui_worker import UpdateWorker

log = logging.getLogger("tsmis.gui")
ui_log = logging.getLogger("tsmis.ui")


class GuiUpdateMixin:
    # ---- one-click update ------------------------------------------------------

    @_api_method
    def check_updates(self):
        """Manual re-check (clicking the version chip)."""
        with self._lock:
            phase = self._update.get("phase")
            revert = self._update.get("revert", False)
        if phase in ("checking", "downloading", "applying"):
            return {"ok": True}              # already busy with update work
        if phase == "staged":
            self._emit_log("A download is already ready — click "
                           + ("‘Restart to revert’" if revert else "‘Restart to update’")
                           + " in the title bar to install it.")
            return {"ok": True}
        self._start_update_check(manual=True)
        return {"ok": True}

    @_api_method
    def update_start(self):
        """Download + stage the offered update. Allowed during a run (network
        and disk only); the restart itself is gated on no task running."""
        with self._lock:
            if self._update.get("phase") != "available" or not self._update.get("can_apply"):
                return {"error": "No update is ready to install."}
            info = self._update_info
            if info is None:
                return {"error": "No update is ready to install."}
            self._update = {"phase": "downloading", "progress": 0,
                            "version": info.version, "url": info.release_url,
                            "can_apply": True}
        size = f" ({round(info.asset_size / 1e6)} MB)" if info.asset_size else ""
        self._emit_log(f"Downloading update v{info.version}{size}…")
        self._push_state()
        UpdateWorker(self._q, "download", info=info).start()
        return {"ok": True}

    @_api_method
    def update_apply(self):
        """Restart into the staged update: launch the swap helper, then close
        this window (the helper waits for our PID before touching files)."""
        with self._lock:
            if self._task:
                return {"error": "Finish or cancel the running task first."}
            if self._update.get("phase") != "staged":
                return {"error": "No downloaded update is ready."}
            staged = self._update.get("staged")
            self._update = dict(self._update, phase="applying")
        ui_log.info("update: user chose Restart to update")
        try:
            updater.apply_update_and_restart(staged)
        except updater.UpdateError as e:
            with self._lock:
                self._update = {"phase": "failed", "note": str(e)}
            self._emit_log(f"Update problem: {e} (details are in the log file)")
            self._push_state()
            return {"error": str(e)}
        self._emit_log("Restarting to finish the update — the app will close "
                       "and reopen by itself…")
        self._push_state()
        threading.Thread(target=self._close_for_update, daemon=True,
                         name="update-restart").start()
        return {"ok": True}

    def _close_for_update(self):
        time.sleep(1.2)                  # let the sender flush the goodbye line
        try:
            self._window.destroy()       # webview.start() returns; process exits
        except Exception:
            log.warning("window destroy failed; force-exiting so the update "
                        "helper can proceed", exc_info=True)
            os._exit(0)

    @_api_method
    def open_release_page(self):
        # Constrain to our own GitHub repo: release_url is API-sourced (html_url),
        # and webbrowser.open on an attacker-influenced value could launch an
        # arbitrary handler. safe_release_url falls back to the constant page.
        url = updater.safe_release_url(self._update.get("url"))
        ui_log.info("opening release page: %s", url)
        webbrowser.open(url)
        return {"ok": True}

    @_api_method
    def revert_to_previous(self):
        """Download + stage the PREVIOUS full release and (after the user clicks
        Restart) swap to it — the Settings "revert to previous version" control.
        Reuses the one-click update pipeline (resolve a specific older tag, then
        the same verify/stage/swap), so the riskiest code is unchanged. Only a
        writable packaged install can self-swap; a read-only / dev install must
        download the older zip from the releases page instead. The download is
        allowed mid-run (network + disk only, like a forward update); the restart
        that applies it stays gated on no task (update_apply)."""
        if updater.update_support()[0] != "ok":
            return {"error": "This install can't revert itself — open the releases "
                             "page and extract an earlier version into a writable folder."}
        with self._lock:
            phase = self._update.get("phase")
            if phase in ("checking", "downloading", "applying"):
                return {"error": "An update or revert is already in progress."}
            if phase == "staged":
                # Don't silently discard a download the user already staged.
                return {"error": "A download is already staged — restart to apply it, "
                                 "or reopen the app first, then revert."}
            self._update = {"phase": "downloading", "progress": 0, "revert": True}
        ui_log.info("revert: user chose 'Revert to previous version'")
        self._emit_log("Reverting to the previous version — finding it and downloading…")
        self._push_state()
        UpdateWorker(self._q, "revert", manual=True).start()
        return {"ok": True}

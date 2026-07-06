"""GuiAuthMixin — extracted verbatim from gui_api.GuiApi (S1 / ARC-02, v0.19.0):
the login flow, the idle verify-environment screenshot, and the
Settings/title-bar environment access scan.
Composition only — every `self._*` it touches lives on GuiApi.
"""
import time

from common import (DATA_SOURCES, DATA_SOURCE_LABELS, ENVIRONMENTS,
                    ENVIRONMENT_LABELS, get_site)
from gui_endpoint import _api_method      # the shared js_api decorator
from gui_worker import EnvCheckWorker, EnvScanWorker, LoginWorker


class GuiAuthMixin:
    # ---- login -----------------------------------------------------------------

    @_api_method
    def start_login(self):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("login")   # claim + bump epoch (gate already checked)
            self._login_phase = "starting"
        self.login_done.clear()
        self.login_cancel.clear()
        self._set_dot("busy", "Signing in…")
        self._emit_log("Starting sign-in…")
        self._push_state()
        LoginWorker(self._gated_queue(), self.login_done, self.login_cancel).start()
        return {"ok": True}

    @_api_method
    def finish_login(self):
        with self._lock:
            self._login_phase = "saving"
        self.login_done.set()
        self._set_dot("busy", "Saving session…")
        self._push_state()
        return {"ok": True}

    @_api_method
    def cancel_login(self):
        with self._lock:
            self._login_phase = "cancelling"
        self.login_cancel.set()
        self.login_done.set()
        self._push_state()
        return {"ok": True}

    # ---- verify environment (idle screenshot) ---------------------------------

    @_api_method
    def verify_environment(self):
        """Open TSMIS headless exactly like an export would, read which data
        source / environment the page ACTUALLY loaded, and screenshot it —
        proof the automation lands on the selected site without running an
        export. Needs a login (saved or automatic), like an export."""
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("envcheck")   # claim + bump epoch (gate already checked)
        src, env = get_site()
        label = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        self._emit_log(f"Verifying environment: opening TSMIS on {label}…")
        self._set_dot("busy", f"Checking {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Checking {label}…"})
        self._push_state()
        EnvCheckWorker(self._gated_queue()).start()
        return {"ok": True}

    def _on_env_shot(self, payload):
        """EnvCheckWorker's single result message → log + preview modal."""
        src, env = get_site()
        want = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        if payload.get("error"):
            self._emit_log(f"Environment check failed: {payload['error']}")
            self._emit_modal("warning", "Environment check failed", payload["error"])
        elif payload.get("env"):
            got = (f"{DATA_SOURCE_LABELS.get(payload['src'], payload['src'])} / "
                   f"{ENVIRONMENT_LABELS.get(payload['env'], payload['env'])}")
            if payload.get("matches"):
                self._emit_log(f"Environment check: the page is running {got} "
                               "— matches your selection.")
            else:
                self._emit_log(f"WARNING: the page is running {got}, but "
                               f"{want} is selected. Exports would hit {got}.")
        else:
            self._emit_log("Environment check: signed in, but the page didn't "
                           "report which site it loaded (screenshot attached).")
        if payload.get("img") or payload.get("error") is None:
            self._emit({"t": "preview", "w": 0, "img": payload.get("img"),
                        "note": "Verify environment",
                        "url": payload.get("url"), "env_info": {
                            "ok": payload.get("ok"),
                            "env": payload.get("env"), "src": payload.get("src"),
                            "matches": payload.get("matches"),
                            "wanted": want}})
        self._end_task()

    # ---- environment access scan (Settings + title-bar chip) -------------------

    @_api_method
    def check_environments(self):
        """Probe EVERY data source / environment combination headless, like an
        export would: does sign-in complete, does the page load the right
        site, and can the report form pull data. Verdicts stream into the
        Settings rows and the title-bar access chip as each site finishes.
        Needs a login (saved or automatic), like an export."""
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("envscan")   # claim + bump epoch (gate already checked)
            for src in DATA_SOURCES:
                for env in ENVIRONMENTS:
                    key = f"{src}-{env}"
                    self._env_access[key] = {
                        "key": key, "source": src, "environment": env,
                        "label": f"{DATA_SOURCE_LABELS[src]} / "
                                 f"{ENVIRONMENT_LABELS[env]}",
                        "status": "checking", "detail": "Checking…",
                        "url": "", "checked_at": ""}
        self.cancel_event.clear()
        self._emit_log("Checking sign-in and report access for every "
                       "environment (six sites — this can take a few minutes)…")
        self._set_dot("busy", "Checking environments…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Checking all environments…"})
        self._push_state()
        EnvScanWorker(self._gated_queue(), self.cancel_event).start()
        return {"ok": True}

    def _on_env_access(self, payload):
        """One site's verdict → state snapshot + a log line. The quiet
        background active-env check sets `quiet` to update the flags silently
        (no per-combo log line)."""
        entry = dict(payload)
        quiet = entry.pop("quiet", False)
        entry["checked_at"] = time.strftime("%H:%M")
        with self._lock:
            self._env_access[entry["key"]] = entry
        if not quiet:
            mark = "OK" if entry["status"] == "ok" else "PROBLEM"
            self._emit_log(f"  {entry['label']}: {mark} — {entry['detail']}")
        self._push_state()

    def _on_env_scan_done(self, payload):
        with self._lock:
            # A cancelled scan leaves later sites untouched — back to "not
            # checked", never a stale spinner.
            for key in [k for k, v in self._env_access.items()
                        if v.get("status") == "checking"]:
                del self._env_access[key]
        if payload.get("error"):
            self._emit_log(f"Environment check stopped: {payload['error']}")
        elif payload.get("cancelled"):
            self._emit_log("Environment check cancelled.")
        else:
            ok, total = payload.get("ok", 0), payload.get("total", 0)
            if ok == total:
                self._emit_log(f"Environment check done: all {total} sites OK.")
            else:
                self._emit_log(f"Environment check done: {ok} of {total} sites "
                               "OK — details next to each address in Settings.")
        self._end_task()

"""The environment / sign-in GUI workers (S2 / ARC-02, split from gui_worker.py).

EnvCheckWorker (the idle Verify environment screenshot), EnvScanWorker (the
Settings/title-bar access scan), ActiveEnvCheckWorker (the quiet background
one-click check, supersedable), LoginWorker (saved-session capture + the Edge
device fallback), and env_verdict. Verbatim moves; gui_worker re-exports.
"""
import base64
import logging
import queue as queue_mod
import threading
import time

from common import (
    _CONFIG_JS, LOGIN_BROWSER_ARGS, AuthError, BrowserNotFoundError,
    PreflightError, SiteUnreachableError, BROWSER_CHANNELS, CHANNEL_LABELS,
    DATA_SOURCES, DATA_SOURCE_LABELS,
    ENVIRONMENTS, ENVIRONMENT_LABELS, resolve_parallel_channel,
    auth_state, check_browsers, get_site, get_url, has_valid_auth,
    is_logged_in,
    capture_edge_login_state_from_profiles, capture_edge_login_state_over_cdp,
    capture_storage_state_if_logged_in, get_preferred_channel,
    launch_edge_login_context, navigate_with_auth, new_authed_browser,
    new_login_context, page_url_for_display, preflight,
    save_auth_state, set_thread_site, storage_state_is_portable,
)
from events import Events

log = logging.getLogger("tsmis.gui")

class EnvCheckWorker(threading.Thread):
    """The idle "Verify environment" action: open TSMIS headless exactly the
    way an export would (saved session, else device sign-in), read which data
    source / environment the app ACTUALLY loaded (the page's CONFIG — the
    same source _site_params_ok trusts), and screenshot the page so the user
    can see the site's own SSOR/ARS + env label with their own eyes.

    Always posts one ('env_shot', dict) message — also on failure (with
    `error` set) — so the GUI task state can never wedge."""

    def __init__(self, queue):
        super().__init__(daemon=True, name="envcheck")
        self.q = queue

    def run(self):
        from playwright.sync_api import sync_playwright
        out = {"ok": False, "img": None, "env": None, "src": None,
               "matches": None, "url": get_url(), "error": None}
        want_src, want_env = get_site()
        log.info("env check: starting (selected src=%s env=%s)", want_src, want_env)
        try:
            with sync_playwright() as p:
                browser, _ctx, page = new_authed_browser(p)
                try:
                    navigate_with_auth(page)
                    # The address the screenshot will show: the page's REAL
                    # URL (token fragment stripped), not just the intended one.
                    out["url"] = page_url_for_display(page) or out["url"]
                    if not is_logged_in(page):
                        out["error"] = ("Sign-in didn't complete, so the report "
                                        "page couldn't be checked. Log in, then "
                                        "try again.")
                    else:
                        out["ok"] = True
                        try:
                            got = page.evaluate(_CONFIG_JS)   # [env, src] or None
                        except Exception:
                            got = None
                        if got:
                            out["env"], out["src"] = got[0], got[1]
                            out["matches"] = (got == [want_env, want_src])
                    try:
                        out["img"] = base64.b64encode(
                            page.screenshot(type="jpeg", quality=70)).decode("ascii")
                    except Exception as e:
                        log.info("env check: screenshot failed (%s)", type(e).__name__)
                finally:
                    browser.close()
        except (AuthError, BrowserNotFoundError, PreflightError) as e:
            out["error"] = str(e)            # messages are already user-safe
        except Exception as e:
            log.exception("env check crashed")
            out["error"] = f"{type(e).__name__}: {e}"
        log.info("env check: done ok=%s page env=%s src=%s matches=%s url=%s "
                 "error=%s", out["ok"], out["env"], out["src"], out["matches"],
                 out["url"], out["error"] or "-")
        self.q.put(("env_shot", out))


# Availability of each report type in the #customReport dropdown, WITHOUT
# clicking anything (the li.cs-option items are in the DOM whether the list is
# open or not). The site sometimes greys single report types out; the exact
# disable convention isn't pinned, so every common signal counts — a class
# containing "disabled", the disabled/data-disabled attributes, aria-disabled,
# or pointer-events:none — and each non-ok option's class string goes to the
# log so a different convention shows up in one upload. Returns null when the
# option list can't be read at all (callers must treat that as "unknown",
# never as "everything is missing").
_REPORT_OPTIONS_JS = """(items) => {
  const els = Array.from(document.querySelectorAll('#customReport li.cs-option'));
  if (!els.length) return null;
  const out = {};
  for (const item of items) {
    const label = item.label, value = item.value;
    // Match by the stable data-value first (robust to the flat->nested menu
    // migration, where a grouped report's leaf text is just "Detail"/"Summary"),
    // then fall back to exact / substring text for a menu without data-value.
    let el = value ? els.find((li) => li.getAttribute('data-value') === value) : null;
    if (!el) el = els.find((li) => (li.textContent || '').trim() === label);
    if (!el) el = els.find((li) => (li.textContent || '').includes(label));
    if (!el) { out[label] = { state: 'missing' }; continue; }
    // On the nested menu a leaf is disabled by greying its parent flyout row
    // (the Highway "coming soon" group), so weigh the parent's class too.
    const parent = el.closest('.cs-parent');
    const cls = (el.className || '') + (parent ? ' ' + (parent.className || '') : '');
    const greyed = /(^|[\\s_-])disabled([\\s_-]|$)/i.test(cls)
      || el.hasAttribute('disabled')
      || el.getAttribute('aria-disabled') === 'true'
      || el.hasAttribute('data-disabled')
      || getComputedStyle(el).pointerEvents === 'none';
    out[label] = { state: greyed ? 'greyed' : 'ok', cls };
  }
  return out;
}"""


def env_verdict(config_readable, reports_readable):
    """Fail-closed verdict for a combo that signed in AND pulled report data:
    returns (status, detail). If the site's CONFIG (the environment
    confirmation) or its report-type list couldn't be read, report "unverified"
    (a future contract change must never read as a silent green "ok") naming what
    couldn't be confirmed; otherwise "ok". Pure -> unit-tested directly (the rest
    of the scan needs a live browser)."""
    unconfirmed = []
    if not config_readable:
        unconfirmed.append("the environment couldn't be confirmed from the site")
    if not reports_readable:
        unconfirmed.append("the report-type list couldn't be read "
                           "(only one type was checked)")
    if unconfirmed:
        return "unverified", ("Signed in and pulled report data, but "
                              + "; ".join(unconfirmed) + ".")
    return "ok", "Sign-in and report data OK."


class EnvScanWorker(threading.Thread):
    """The "Check all environments" scan (Settings button + the automatic
    run after startup/sign-in): probe EVERY data source / environment
    combination headless, the way an export would — does sign-in complete,
    does the page load the requested site, can the report form pull data,
    and is every report type offered? The page ships its whole form in
    static HTML even signed out, so form presence proves nothing; only a
    real preflight (report picked, District fanned out, the site's own data
    round-trip enabling the County dropdown) shows report access — "signs in
    fine but can't actually pull reports" is exactly the failure this exists
    to surface.

    FAST on purpose (it runs unprompted after startup): combos are drained
    from a shared queue by up to 3 scanner threads, each owning its own
    Playwright/browser (the fast-mode idiom — the sync API is thread-affine)
    and pinning its target via common.set_thread_site, so the user's header
    selection is never touched and parallel combos can't race each other.
    Device sign-in mode (no saved auth file) caps the scan to ONE thread:
    the persistent Edge profile can only be open in one browser — the same
    rule fast mode applies.

    Posts one ("env_access", dict) per combo AS IT FINISHES (the Settings
    rows and the title-bar chip update live), then ("env_access_done", dict).
    Cancel is honored BETWEEN combos — each combo is already bounded by the
    sign-in budget and the preflight/county timeouts."""

    MAX_SCANNERS = 3

    def __init__(self, queue, cancel_event):
        super().__init__(daemon=True, name="envscan")
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        from reports import EXPORT_REPORTS
        # (registry label for the verdict/UI, dropdown option text to probe &
        # select). These DIFFER for "Highway Log (PDF)": its dropdown option is the
        # same "Highway Log" the Excel export uses (the PDF is that report saved a
        # different way), so probing the registry label would never match the
        # dropdown and would falsely flag it "missing" on every environment.
        report_specs = [(label, getattr(spec, "label", None) or label,
                         getattr(spec, "data_value", None))
                        for label, _fmt, spec in EXPORT_REPORTS]
        combos = [(s, e) for s in DATA_SOURCES for e in ENVIRONMENTS]
        n = min(self.MAX_SCANNERS, len(combos)) if has_valid_auth() else 1
        if n > 1:
            n = self._parallel_scanners(n)
        log.info("env scan: starting (%d combos, %d scanner browser(s), "
                 "report types %s)", len(combos), n, [r for r, _d, _v in report_specs])
        work = queue_mod.Queue()
        for combo in combos:
            work.put(combo)
        results = {}                      # key -> result dict (lock-protected)
        fatals = []
        lock = threading.Lock()

        def scanner(worker_no):
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    browser = page = None
                    try:
                        while not self.cancel.is_set():
                            try:
                                src, env = work.get_nowait()
                            except queue_mod.Empty:
                                break
                            set_thread_site(src, env)
                            if browser is None:
                                # Scanners run several saved-session browsers
                                # at once -> the parallel channel (not Edge).
                                browser, _ctx, page = new_authed_browser(
                                    p, parallel=True)
                            out = self.check_one(page, src, env, report_specs)
                            with lock:
                                results[out["key"]] = out
                            self.q.put(("env_access", out))
                    finally:
                        set_thread_site(None, None)
                        if browser is not None:
                            try:
                                browser.close()
                            except Exception as e:
                                log.info("env scan: browser close failed "
                                         "(%s: %s)", type(e).__name__,
                                         str(e).splitlines()[0] if str(e) else "")
            except (AuthError, BrowserNotFoundError) as e:
                # This scanner is out; the others keep draining the queue.
                log.warning("env scan: scanner %d stopped (%s: %s)",
                            worker_no, type(e).__name__, e)
                with lock:
                    fatals.append(str(e))    # messages are already user-safe
            except Exception as e:
                log.exception("env scan: scanner %d crashed", worker_no)
                with lock:
                    fatals.append(f"{type(e).__name__}: {e}")

        threads = [threading.Thread(target=scanner, args=(i + 1,),
                                    daemon=True, name=f"envscan-w{i + 1}")
                   for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        cancelled = self.cancel.is_set()
        fatal = fatals[0] if fatals and len(fatals) == n else None
        if fatal and not cancelled:
            # EVERY scanner died (e.g. no usable login at all): fill the
            # unchecked combos so no row is left saying "checking".
            for src, env in combos:
                key = f"{src}-{env}"
                if key in results:
                    continue
                out = {"key": key, "source": src, "environment": env,
                       "label": f"{DATA_SOURCE_LABELS[src]} / "
                                f"{ENVIRONMENT_LABELS[env]}",
                       "status": "error", "detail": fatal, "url": "",
                       "reports": {}}
                results[key] = out
                self.q.put(("env_access", out))
        ok = sum(1 for r in results.values() if r["status"] == "ok")
        log.info("env scan: done ok=%d/%d cancelled=%s fatal=%s",
                 ok, len(results), cancelled, fatal or "-")
        self.q.put(("env_access_done",
                    {"ok": ok, "done": len(results), "total": len(combos),
                     "cancelled": cancelled, "error": fatal}))

    def _parallel_scanners(self, n):
        """Parallel scanning only when the parallel channel is an unmanaged
        Chromium (Built-in Chromium / Chrome + a saved login): if the only
        usable browser is managed Edge, three concurrent sessions are the
        exact failure fast mode hit in the field — scan serially instead.
        The resolution is probed once and cached, so this costs ~a second
        the first time and nothing after."""
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                channel = resolve_parallel_channel(p)
        except Exception as e:
            log.info("env scan: parallel channel pre-check failed (%s) — "
                     "scanning serially", type(e).__name__)
            return 1
        if channel == "msedge":
            log.info("env scan: only managed Edge is usable — scanning "
                     "serially (no concurrent Edge sessions)")
            return 1
        return n

    @staticmethod
    def check_one(page, src, env, report_labels, *, budget_s=60):
        """One combo's verdict — shared by this scan (all six combos) and the
        quiet ActiveEnvCheckWorker (the selected combo). Never raises: the answer
        (crashes included) rides in the returned dict's status/detail; the WHY is
        in the log and the auth/preflight dumps the shared gates already write.
        `budget_s` bounds the sign-in loop (short for the background check)."""
        label = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        out = {"key": f"{src}-{env}", "source": src, "environment": env,
               "label": label, "status": "error", "detail": "", "url": "",
               "reports": {}}
        t0 = time.monotonic()
        try:
            try:
                navigate_with_auth(page, budget_s=budget_s)
            except SiteUnreachableError as e:
                # Don't read page.url here: the failed goto leaves the page
                # parked on the PREVIOUS combo's address.
                out["status"], out["detail"] = "unreachable", str(e)
                return out
            out["url"] = page_url_for_display(page)
            if not is_logged_in(page):
                signals = auth_state(page).get("signals")
                denied = (isinstance(signals, dict) and
                          str(signals.get("accessDenied", "")).startswith("visible"))
                if denied:
                    out["status"] = "denied"
                    out["detail"] = ("Signs in, but TSMIS reports access "
                                     "denied on this site.")
                else:
                    out["status"] = "no_signin"
                    out["detail"] = "Sign-in didn't complete on this site."
                return out
            got = None
            try:
                got = page.evaluate(_CONFIG_JS)          # [env, src] or None
            except Exception as e:
                log.info("env check: CONFIG probe failed (%s: %s)",
                         type(e).__name__, str(e).splitlines()[0] if str(e) else "")
            # _CONFIG_JS returns null when the site's CONFIG can't be read (a
            # future rename), so None here = "couldn't confirm the environment".
            config_readable = got is not None
            if got and got != [env, src]:
                out["status"] = "wrong_site"
                out["detail"] = (f"The page loaded {(got[1] or '?').upper()} / "
                                 f"{(got[0] or '?').upper()} instead — check "
                                 "this row's address.")
                return out
            # Which of the report types is actually offered? The site
            # sometimes greys single types out. None readable = unknown
            # (keep the old first-report probe), never "all missing".
            # Probe the dropdown by the OPTION TEXT (de-duplicated — the Excel and
            # PDF Highway Log share one "Highway Log" option), and key the verdict
            # by the registry label the UI reads. None readable = unknown (keep the
            # old first-report probe), never "all missing".
            pairs = list(dict.fromkeys((drop, dv) for _reg, drop, dv in report_labels))
            probe = [{"label": d, "value": v} for d, v in pairs]
            options = None
            try:
                options = page.evaluate(_REPORT_OPTIONS_JS, probe)
            except Exception as e:
                log.info("env scan: %s report dropdown read failed (%s)",
                         out["key"], type(e).__name__)
            if options:
                out["reports"] = {reg: options.get(drop, {}).get("state", "missing")
                                  for reg, drop, _dv in report_labels}
                for reg, drop, _dv in report_labels:
                    state = out["reports"][reg]
                    if state != "ok":
                        log.info("env scan: %s report %r is %s (class=%r)",
                                 out["key"], reg, state,
                                 options.get(drop, {}).get("cls", ""))
            # An AVAILABLE (option text, data-value) pair, for the preflight
            # round-trip (preflight SELECTS the report by text + stable id).
            avail = [(drop, dv) for reg, drop, dv in report_labels
                     if out["reports"].get(reg) == "ok"]
            off = [reg for reg, state in out["reports"].items() if state != "ok"]
            if options and not avail:
                out["status"] = "no_reports"
                out["detail"] = ("Signs in, but every report type is greyed "
                                 "out or missing here.")
                return out
            try:
                # The data probe, on the first AVAILABLE report type: County
                # only enables once the site's own route/county round-trip
                # answers (the form itself is static).
                sel_drop, sel_dv = (avail[0] if avail
                                    else (probe[0]["label"], probe[0]["value"]))
                preflight(page, sel_drop, sel_dv)
            except PreflightError:
                out["status"] = "no_reports"
                out["detail"] = ("Signs in, but the report form couldn't load "
                                 "its data — reports would fail here.")
                return out
            if off:
                out["status"] = "reports_off"
                out["detail"] = ("Sign-in and report data OK, but unavailable "
                                 "here: " + ", ".join(off) + ".")
                return out
            # Clean sign-in + working report data. The fail-closed verdict logic
            # (don't claim a green "ok" when the site's CONFIG or report list
            # couldn't be read) is a pure mapping, factored out so it's unit
            # tested directly (the rest of this method needs a live browser).
            out["status"], out["detail"] = env_verdict(config_readable,
                                                        options is not None)
            return out
        except Exception as e:
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            log.warning("env scan: %s check crashed (%s: %s)", out["key"],
                        type(e).__name__, reason)
            out["detail"] = f"The check failed unexpectedly ({reason})."
            return out
        finally:
            log.info("env scan: %s -> %s in %.1fs (%s)", out["key"],
                     out["status"], time.monotonic() - t0, out["detail"] or "-")


class _Superseded(Exception):
    """Internal: the quiet env check yielded to a user task (B8)."""


class ActiveEnvCheckWorker(threading.Thread):
    """The QUIET, single-combo env check for the CURRENTLY selected site, run
    unprompted on app start and after an env switch. Where EnvScanWorker probes
    all six combos on the user's command, this checks just ONE — the selected
    src/env — in the background to:
      • prove Edge one-click / device sign-in works (so the title-bar chip lights
        without anyone pressing "Log in"), and
      • refresh that env's report availability, feeding the Export-tab AND the
        matrix warning flags.
    Single browser, short sign-in budget so a managed PC's silent SSO completes
    but an unreachable machine fails fast. Pins its own thread site so the user's
    live header selection is never touched. QUIET on every failure (no modal) — a
    failed check simply doesn't light the chip. `seq` lets a newer env switch
    supersede a result still in flight.

    Posts ("env_access", verdict) [verdict["quiet"]=True] then
    ("active_env_done", {seq, key, signed_in, via_device})."""

    BUDGET_S = 20        # sign-in budget: enough for silent SSO, short on failure

    def __init__(self, queue, src, env, seq, supersede=None):
        super().__init__(daemon=True, name="activeenv")
        self.q = queue
        self.src = src
        self.env = env
        self.seq = seq
        # B8: a user task wanting the Edge profile sets this; the check yields
        # at its next seam instead of holding the profile for the full budget.
        self.supersede = supersede or threading.Event()

    def run(self):
        from reports import EXPORT_REPORTS
        from playwright.sync_api import sync_playwright
        report_specs = [(label, getattr(spec, "label", None) or label,
                         getattr(spec, "data_value", None))
                        for label, _fmt, spec in EXPORT_REPORTS]
        key = f"{self.src}-{self.env}"
        had_file = has_valid_auth()        # classify device vs saved-file sign-in
        signed_in = False
        set_thread_site(self.src, self.env)
        try:
            if self.supersede.is_set():
                log.info("active env check: superseded before launch; yielding")
                raise _Superseded()
            with sync_playwright() as p:
                browser = None
                try:
                    # Non-parallel: a saved file → the chosen Chromium browser;
                    # no file → the device Edge context (the path that PROVES the
                    # one-click). Either way a 3-tuple whose first item .close()s.
                    browser, _ctx, page = new_authed_browser(p)
                    if self.supersede.is_set():
                        log.info("active env check: superseded after launch; "
                                 "yielding the Edge profile")
                        raise _Superseded()
                    verdict = EnvScanWorker.check_one(page, self.src, self.env,
                                                      report_specs,
                                                      budget_s=self.BUDGET_S)
                    verdict["quiet"] = True    # suppress the per-combo scan log line
                    if not self.supersede.is_set():
                        self.q.put(("env_access", verdict))
                        signed_in = verdict["status"] not in (
                            "no_signin", "denied", "unreachable", "error")
                finally:
                    if browser is not None:
                        try:
                            browser.close()
                        except Exception as e:
                            log.info("active env check: browser close failed "
                                     "(%s: %s)", type(e).__name__,
                                     str(e).splitlines()[0] if str(e) else "")
        except _Superseded:  # silent-ok: the yield point above already logged it
            pass
        except Exception as e:
            log.info("active env check: %s quiet failure (%s: %s)", key,
                     type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        finally:
            set_thread_site(None, None)
        # via_device only when we signed in WITHOUT a saved file — that's the
        # path that actually exercised (and so proves) Edge one-click.
        self.q.put(("active_env_done",
                    {"seq": self.seq, "key": key, "signed_in": signed_in,
                     "via_device": signed_in and not had_file}))


class LoginWorker(threading.Thread):
    """Opens a headed browser for SSO+MFA, waits for the user to signal done
    (done_event, set by a GUI button), then saves the storage_state.

    cancel_event also sets done_event to unblock the wait; if cancel is set the
    session is NOT saved.
    """

    def __init__(self, queue, done_event, cancel_event):
        super().__init__(daemon=True, name="login")
        self.q = queue
        self.done = done_event
        self.cancel = cancel_event

    _CANCELLED = object()

    def run(self):
        from playwright.sync_api import sync_playwright
        log = logging.getLogger("tsmis.login")
        try:
            with sync_playwright() as p:
                # The quiet background active-env check now OWNS silent Edge
                # one-click sign-in. The button's job is to CAPTURE a portable
                # saved login (what fast mode needs, and what normal exports
                # restore) via a headed window in the chosen Chromium-class
                # browser — Chrome by default (preferred when installed), or the
                # Built-in Chromium when that's the pick or Chrome is absent.
                pref = get_preferred_channel()          # 'chrome'|'chromium'|None
                log.info("login: starting (export browser: %s)",
                         pref or "auto (Chrome-first)")
                order = (["chromium", "chrome"] if pref == "chromium"
                         else ["chrome", "chromium"])
                for ch in order:
                    if ch == "chromium" and "chromium" not in BROWSER_CHANNELS:
                        continue
                    try:
                        browser = p.chromium.launch(headless=False, channel=ch,
                                                    args=LOGIN_BROWSER_ARGS)
                    except Exception as e:
                        log.info("login: %s launch failed (%s)", ch, type(e).__name__)
                        continue
                    self._run_login_in_browser(browser, CHANNEL_LABELS[ch], log)
                    return

                # No Chrome/Chromium could open (an Edge-only managed PC): fall
                # back to the persistent-profile Edge recapture, validating the
                # capture is portable before saving (a Windows device-broker/PRT
                # session can't be reused elsewhere -> device mode instead).
                self.q.put(("log", "No Chrome/Chromium browser is available; "
                                   "signing in with Microsoft Edge..."))
                edge_state = self._try_edge_persistent_login(p, log)
                if edge_state is self._CANCELLED:
                    self.q.put(("cancelled", None))
                    return
                if edge_state:
                    # A capture from the live Edge profile can still be useless:
                    # when Edge signed in through the Windows device broker (PRT)
                    # the session never reaches the cookie jar, so the saved file
                    # would not log in anywhere else. Prove the capture works the
                    # way the engine will use it before saving it.
                    self.q.put(("log", "Checking that the captured sign-in can be "
                                       "reused for exports..."))
                    if storage_state_is_portable(p, edge_state,
                                                 should_cancel=self.cancel.is_set):
                        self._save_state(edge_state)
                        self.q.put(("login_saved", None))
                        log.info("login: SAVED via Edge recapture")
                        return
                    # Device-bound capture: don't save it, but exports can still
                    # sign themselves in live (device mode).
                    log.info("login: Edge capture device-bound (not portable); "
                             "device mode")
                    self.q.put(("login_device_ok", None))
                    return
                self.q.put(("error", ("general",
                            "No usable web browser was found to sign in. Install "
                            "Google Chrome or Microsoft Edge, then try again.")))
        except BrowserNotFoundError as e:
            self.q.put(("error", ("general", str(e))))
        except Exception as e:
            log.exception("login worker crashed")
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))

    def _try_edge_persistent_login(self, p, log):
        ctx = None
        cdp_url = None
        try:
            ctx, cdp_url = launch_edge_login_context(p)
        except Exception as e:
            log.info("login: experimental Edge launch unavailable (%s)", type(e).__name__)
            self.q.put(("log", "Experimental Edge sign-in could not open; "
                               "using Google Chrome fallback."))
            return None

        self.done.clear()
        self.q.put(("login_open", None))
        self.q.put(("log", "Experimental Edge sign-in opened. Finish signing in, "
                           "then click \"I've finished logging in.\""))
        log.info("login: experimental Edge persistent profile opened")

        while not self.done.wait(0.2):
            pass

        if self.cancel.is_set():
            self._safe_close_context(ctx)
            log.info("login: cancelled during experimental Edge sign-in")
            return self._CANCELLED

        try:
            state = capture_storage_state_if_logged_in(ctx)
            if state:
                self._safe_close_context(ctx)
                log.info("login: experimental Edge captured from live context")
                return state
        except Exception as e:
            log.info("login: live Edge context capture failed (%s)", type(e).__name__)

        self.q.put(("log", "Edge did not expose a live session; trying to recapture "
                           "the work-profile state..."))
        state = capture_edge_login_state_over_cdp(p, cdp_url,
                                                  should_cancel=self.cancel.is_set)
        if state:
            self._safe_close_context(ctx)
            log.info("login: experimental Edge captured over CDP")
            return state

        self._safe_close_context(ctx)
        state, profile_name = capture_edge_login_state_from_profiles(
            p, should_cancel=self.cancel.is_set)
        if state:
            log.info("login: experimental Edge captured from profile %s", profile_name)
            return state

        log.info("login: experimental Edge capture failed")
        return None

    def _run_login_in_browser(self, browser, label, log):
        """Drive a normal (non-persistent) headed sign-in in `browser` and save
        the session once a real TSMIS login is seen. Used for the Built-in
        Chromium path and the Chrome fallback."""
        # Pre-granted local-network-access context: otherwise Chrome prompts
        # per sign-in and an unanswered prompt blocks the signed-in UI, so the
        # login is never detected (see common.LOGIN_BROWSER_ARGS).
        ctx = new_login_context(browser)
        page = ctx.new_page()
        page.goto(get_url())
        self.done.clear()
        self.q.put(("login_open", None))
        self.q.put(("log", f"Sign-in window opened in {label}."))

        # Wait for the user to finish (the "I've finished" button sets
        # self.done) OR to close the whole browser window. Capture the session
        # the instant a real TSMIS login appears, so closing the window AFTER
        # signing in still saves it.
        #
        # ROBUSTNESS: the SSO/MFA sign-in navigates, can open a popup, and may
        # replace the original tab, and a single Playwright call can blip
        # mid-redirect. So we must NOT treat one ctx.cookies() error -- nor the
        # *original* tab closing -- as "the user gave up" (that bug once slammed
        # the window shut the instant a password went through and reported
        # "cancelled"). The only reliable "user closed the window" signal is
        # that NO tabs remain open in the context (the SSO dance always keeps
        # >= 1 tab), with a long all-calls-failing streak as a backstop for a
        # truly dead connection.
        captured = None
        closed = False
        blips = 0
        while not self.done.wait(0.3):
            try:
                ctx.cookies()                   # pump Playwright events
                blips = 0
            except Exception:
                blips += 1      # transient mid-redirect blip, or gone -- decided below
            try:
                open_pages = [pg for pg in ctx.pages if not pg.is_closed()]
            except Exception:
                open_pages = None   # context momentarily unavailable; re-check next tick
            if (open_pages is not None and len(open_pages) == 0) or blips >= 20:
                closed = True   # every tab gone (or ~6s unreachable) -> window closed
                break
            if captured is None:
                try:
                    if self._any_logged_in(ctx):
                        captured = ctx.storage_state()
                except Exception:
                    pass        # mid-navigation; retry on the next tick

        if closed:
            self.q.put(("log", "Login window closed - checking your sign-in..."))

        if self.cancel.is_set():
            self._safe_close(browser)
            self.q.put(("cancelled", None))
            log.info("login: cancelled during %s sign-in", label)
            return

        if not closed:
            try:
                if self._any_logged_in(ctx):
                    captured = ctx.storage_state()
            except Exception:
                pass
        self._safe_close(browser)

        if captured:
            self._save_state(captured)
            self.q.put(("login_saved", None))
            log.info("login: SAVED via %s", label)
        elif closed:
            self.q.put(("cancelled", None))
            log.info("login: %s window closed without capture", label)
        else:
            self.q.put(("login_failed", None))
            log.info("login: %s finished without detected login", label)

    @staticmethod
    def _any_logged_in(ctx):
        """True if ANY page in the context is the logged-in TSMIS report page
        (SSO sometimes lands it in a popup / new tab, not the original page)."""
        for pg in ctx.pages:
            try:
                if is_logged_in(pg):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _safe_close(browser):
        try:
            browser.close()
        except Exception as e:
            # best-effort cleanup — never fail login on a close hiccup, but log the
            # type+first line so a recurring leak shows up in one log upload (P7a).
            log.info("login: browser close failed (%s: %s)", type(e).__name__, e)

    @staticmethod
    def _safe_close_context(ctx):
        try:
            ctx.close()
        except Exception as e:
            log.info("login: context close failed (%s: %s)", type(e).__name__, e)

    @staticmethod
    def _save_state(state):
        save_auth_state(state)          # logs path + cookie count

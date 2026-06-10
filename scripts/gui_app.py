"""Main window for the TSMIS Reports Exporter GUI.

Owns the Tk widgets and the queue pump. All browser/file work runs on worker
threads (gui_worker); this module only reacts to the messages they post, on the
Tk main thread. The engines stay console-free -- the GUI is just another driver
of the same Events seam used by the .bat flow.
"""
import os
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import gui_theme as theme
import run_report
from gui_theme import DOT, PALETTE
from gui_worker import CheckWorker, ConsolidateWorker, ExportWorker, LoginWorker
from exporter_parallel import DEFAULT_WORKERS, MAX_WORKERS

from paths import LOG_DIR, OUTPUT_ROOT
from version import APP_NAME, __version__
from common import (
    BROWSER_CHANNELS, CHANNEL_LABELS, ROUTES, AuthError, clear_auth, parse_routes,
    require_valid_auth, set_preferred_channel,
)

# The report list lives in one place (reports.py) so the GUI and the console
# multi-exporter can't drift. EXPORT_REPORTS = [(label, fmt, spec)],
# CONSOLIDATE_REPORTS = [(label, consolidate_fn, OUT_PATH)].
from reports import EXPORT_REPORTS, CONSOLIDATE_REPORTS

CONSOLIDATED_DIR = OUTPUT_ROOT / "consolidated"

PAD = 14


def _app_icon_path():
    """Path to the bundled app icon (.ico), or None. Frozen: it's bundled into
    _internal via sys._MEIPASS; in dev it's build/app.ico. Best-effort -- a
    missing icon must never stop the GUI from launching."""
    base = getattr(sys, "_MEIPASS", None)
    candidates = []
    if base:
        candidates.append(Path(base) / "app.ico")
    candidates.append(Path(__file__).resolve().parent.parent / "build" / "app.ico")
    return next((c for c in candidates if c.exists()), None)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        # Window/taskbar icon (best-effort; default= so dialogs inherit it).
        try:
            _ico = _app_icon_path()
            if _ico:
                self.iconbitmap(default=str(_ico))
        except Exception:
            pass
        # Window size is computed from the laid-out content at the end of __init__
        # so the log pane is never squeezed to nothing (see the sizing block).

        self.fonts = theme.fonts()
        theme.apply(self)

        self.q = Queue()
        self.task = None                       # None | "export" | "consolidate" | "login"
        self._authed = False
        self.cancel_event = threading.Event()
        self.skip_event = threading.Event()
        self.login_done = threading.Event()
        self.login_cancel = threading.Event()

        # One checkbox per report type so several can be exported at once. First
        # report ticked by default so a selection always exists.
        self.export_vars = [tk.BooleanVar(value=(i == 0)) for i in range(len(EXPORT_REPORTS))]
        self.cons_choice = tk.IntVar(value=0)
        self.fast_mode = tk.BooleanVar(value=False)        # experimental parallel export
        self.fast_workers = tk.IntVar(value=DEFAULT_WORKERS)

        self._active_specs = []         # specs of the run in progress
        self._last_results = []         # [(spec, RunResult), ...] of the last export (enables "Save run report")
        self._run_start = None          # monotonic start of the current run (elapsed timer)
        self._timer_job = None          # after() id for the 1 Hz elapsed-time ticker
        self._check_detail = {}         # check key -> latest detail text (shown as a tooltip)
        self._tip = None                # the active tooltip Toplevel, if any

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)         # log row expands

        self._build_header()                   # header now hosts the compact readiness strip
        self._build_notebook()
        self._build_progress()
        self._build_log()
        self._build_footer()

        self._inputs = [
            self.btn_login,
            self.btn_export_start, self.btn_cons_start,
            self.fast_check,
            self.routes_entry, self.btn_choose_routes,
            self.browser_combo, self.btn_recheck,
            *self.export_checks, *self.cons_radios,
        ]
        # Run-only controls start disabled (no task is running, no result yet).
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel,
                  self.btn_save_report):
            w.state(["disabled"])
        self._sync_fast_controls()             # spinner follows the fast-mode checkbox

        # Size to the laid-out content so EVERYTHING (incl. the log) shows at
        # launch, and keep that as the floor so the weighted log row can't be
        # squeezed to zero. Width is fixed (the footer path would otherwise force
        # an absurdly wide window); height follows the content.
        self.update_idletasks()
        # The header check strip grows a dot when the Built-in Chromium channel
        # is present; give that variant a little more width.
        win_w = 700 if len(BROWSER_CHANNELS) > 2 else 680
        win_h = self.winfo_reqheight()
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(620, win_h)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_auth()
        self.after(100, self._drain)
        self.start_checks()                    # run the readiness checks on launch

    # ---- widget construction ------------------------------------------------

    def _build_header(self):
        h = ttk.Frame(self, style="Header.TFrame", padding=(PAD, 12))
        h.grid(row=0, column=0, sticky="ew")
        h.columnconfigure(0, weight=1)

        ttk.Label(h, text=APP_NAME, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(h, text=f"v{__version__}", style="HeaderMuted.TLabel").grid(row=0, column=1, sticky="e")

        status = ttk.Frame(h, style="Header.TFrame")
        status.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.dot = ttk.Label(status, text="●", style="Dot.TLabel", foreground=DOT["unknown"])
        self.dot.grid(row=0, column=0, padx=(0, 6))
        self.status_text = ttk.Label(status, text="Checking session…", style="Status.TLabel")
        self.status_text.grid(row=0, column=1)

        btns = ttk.Frame(h, style="Header.TFrame")
        btns.grid(row=1, column=1, sticky="e", pady=(6, 0))
        self.btn_login = ttk.Button(btns, text="Log in", command=self.start_login)
        self.btn_login.grid(row=0, column=0)
        self.btn_login_cancel = ttk.Button(btns, text="Cancel", command=self.cancel_login)
        self.btn_login_cancel.grid(row=0, column=1, padx=(8, 0))
        self.btn_login_cancel.grid_remove()

        # Compact readiness strip lives in the header (browser switcher + dots).
        self._build_check_strip(h)

    def _build_check_strip(self, parent):
        """A small readiness row inside the header: a browser switcher (default
        Edge) and a green/red dot for each browser + output folder + report
        tools. Hovering a dot shows the detail. Filled in on launch by
        CheckWorker (see start_checks)."""
        strip = ttk.Frame(parent, style="Header.TFrame")
        strip.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        strip.columnconfigure(3, weight=1)          # spacer pushes Re-check to the right

        self._check_items = {}
        self._label_to_channel = {CHANNEL_LABELS[c]: c for c in BROWSER_CHANNELS}

        ttk.Label(strip, text="Browser", style="HeaderMuted.TLabel").grid(row=0, column=0, sticky="w")
        self.browser_combo = ttk.Combobox(
            strip, state="readonly", width=17,
            values=[CHANNEL_LABELS[c] for c in BROWSER_CHANNELS])
        # Default to the first channel launch_browser would resolve: the
        # Built-in Chromium when this install carries one, otherwise Edge.
        self.browser_combo.set(CHANNEL_LABELS[BROWSER_CHANNELS[0]])
        self.browser_combo.grid(row=0, column=1, sticky="w", padx=(6, 16))
        self.browser_combo.bind("<<ComboboxSelected>>", self._on_browser_pick)

        checks = ttk.Frame(strip, style="Header.TFrame")
        checks.grid(row=0, column=2, sticky="w")
        _short = {"chromium": "Chromium", "msedge": "Edge", "chrome": "Chrome"}
        check_dots = [(f"browser_{c}", _short.get(c, CHANNEL_LABELS[c]))
                      for c in BROWSER_CHANNELS]
        check_dots += [("output", "Output"), ("tools", "Tools")]
        for i, (key, label) in enumerate(check_dots):
            dot = ttk.Label(checks, text="●", style="Dot.TLabel", foreground=DOT["unknown"])
            dot.grid(row=0, column=2 * i, padx=(14 if i else 0, 3))
            lab = ttk.Label(checks, text=label, style="HeaderMuted.TLabel")
            lab.grid(row=0, column=2 * i + 1)
            self._check_items[key] = (dot, None, label)
            self._check_detail[key] = f"{label}: checking…"
            self._attach_tip(dot, key)
            self._attach_tip(lab, key)

        self.btn_recheck = ttk.Button(strip, text="Re-check", width=9, command=self.start_checks)
        self.btn_recheck.grid(row=0, column=4, sticky="e")

    # ---- tiny hover tooltip (for the compact check dots) --------------------

    def _attach_tip(self, widget, key):
        widget.bind("<Enter>", lambda _e, k=key, w=widget: self._show_tip(w, k))
        widget.bind("<Leave>", lambda _e: self._hide_tip())

    def _show_tip(self, widget, key):
        self._hide_tip()
        text = self._check_detail.get(key)
        if not text:
            return
        self._tip = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        try:
            tw.attributes("-topmost", True)
        except tk.TclError:
            pass
        tw.wm_geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty() + widget.winfo_height() + 3}")
        tk.Label(tw, text=text, bg=PALETTE["surface"], fg=PALETTE["text"],
                 relief="solid", borderwidth=1, padx=6, pady=2,
                 font=self.fonts["small"]).pack()

    def _hide_tip(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

    def _build_notebook(self):
        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(10, 8))

        # Export tab
        ex = ttk.Frame(nb, padding=(PAD, 10))
        ex.columnconfigure(0, weight=1)
        row = 0
        ttk.Label(ex, text="REPORTS TO EXPORT  (tick one or more)", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, 6))
        row += 1
        self.export_checks = []
        for i, (label, fmt, _spec) in enumerate(EXPORT_REPORTS):
            cb = ttk.Checkbutton(ex, text=f"{label}   ·   {fmt}", variable=self.export_vars[i])
            cb.grid(row=row, column=0, sticky="w")
            self.export_checks.append(cb)
            row += 1

        # Route selection. Blank = all routes (the default); otherwise the chosen
        # subset, typed in or picked from the full list via "Choose…".
        ttk.Label(ex, text="ROUTES", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 2))
        row += 1
        routes = ttk.Frame(ex)
        routes.grid(row=row, column=0, sticky="ew")
        routes.columnconfigure(0, weight=1)
        self.routes_entry = ttk.Entry(routes)
        self.routes_entry.grid(row=0, column=0, sticky="ew")
        self.routes_entry.bind("<KeyRelease>", self._update_route_feedback)
        self.btn_choose_routes = ttk.Button(routes, text="Choose…", command=self._choose_routes)
        self.btn_choose_routes.grid(row=0, column=1, padx=(8, 0))
        row += 1
        self.route_feedback = ttk.Label(ex, text="Leave blank to export all routes.",
                                        style="Muted.TLabel", wraplength=460, justify="left")
        self.route_feedback.grid(row=row, column=0, sticky="w", pady=(4, 0))
        row += 1

        # Experimental "fast mode": run several browsers at once.
        fast = ttk.Frame(ex)
        fast.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1
        self.fast_check = ttk.Checkbutton(
            fast, text="⚡ Fast mode (experimental) — run", variable=self.fast_mode,
            command=self._sync_fast_controls)
        self.fast_check.grid(row=0, column=0, sticky="w")
        self.fast_spin = ttk.Spinbox(fast, from_=2, to=MAX_WORKERS, width=3,
                                     textvariable=self.fast_workers)
        self.fast_spin.grid(row=0, column=1, padx=(6, 6))
        ttk.Label(fast, text="browsers at once").grid(row=0, column=2, sticky="w")
        ttk.Label(ex, text="Faster, but heavier on your PC; 3–4 recommended. "
                           "Per-route Skip is off in fast mode.",
                  style="Muted.TLabel", wraplength=600, justify="left").grid(
            row=row, column=0, sticky="w", pady=(3, 0))
        row += 1

        actions = ttk.Frame(ex)
        actions.grid(row=row, column=0, sticky="w", pady=(12, 0))
        self.btn_export_start = ttk.Button(actions, text="Start export", style="Accent.TButton",
                                           command=self.start_export)
        self.btn_export_start.grid(row=0, column=0)
        self.btn_export_skip = ttk.Button(actions, text="Skip route", command=self.skip_current)
        self.btn_export_skip.grid(row=0, column=1, padx=(8, 0))
        self.btn_export_cancel = ttk.Button(actions, text="Cancel", command=self.cancel_current)
        self.btn_export_cancel.grid(row=0, column=2, padx=(8, 0))
        self.btn_save_report = ttk.Button(actions, text="Save run report…",
                                          command=self.save_report)
        self.btn_save_report.grid(row=0, column=3, padx=(8, 0))
        nb.add(ex, text="Export")

        # Consolidate tab
        co = ttk.Frame(nb, padding=(PAD, 10))
        co.columnconfigure(0, weight=1)
        ttk.Label(co, text="REPORT TO CONSOLIDATE (combine downloaded files)",
                  style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.cons_radios = []
        for i, (label, _fn, _out) in enumerate(CONSOLIDATE_REPORTS):
            rb = ttk.Radiobutton(co, text=label, value=i, variable=self.cons_choice)
            rb.grid(row=1 + i, column=0, sticky="w")
            self.cons_radios.append(rb)
        ttk.Label(co, text="Combines the per-route files already in the output folder "
                           "into one workbook.", style="Muted.TLabel").grid(
            row=1 + len(CONSOLIDATE_REPORTS), column=0, sticky="w", pady=(8, 0))

        dest = ttk.Frame(co)
        dest.grid(row=2 + len(CONSOLIDATE_REPORTS), column=0, sticky="ew", pady=(10, 0))
        dest.columnconfigure(0, weight=1)
        ttk.Label(dest, text=f"Saved to:  {CONSOLIDATED_DIR}", style="Muted.TLabel",
                  wraplength=440, justify="left").grid(row=0, column=0, sticky="w")
        ttk.Button(dest, text="Open folder",
                   command=self._open_consolidated_folder).grid(row=0, column=1, sticky="e", padx=(8, 0))

        actions = ttk.Frame(co)
        actions.grid(row=3 + len(CONSOLIDATE_REPORTS), column=0, sticky="w", pady=(PAD, 0))
        self.btn_cons_start = ttk.Button(actions, text="Start consolidation", style="Accent.TButton",
                                         command=self.start_consolidate)
        self.btn_cons_start.grid(row=0, column=0)
        self.btn_cons_cancel = ttk.Button(actions, text="Cancel", command=self.cancel_current)
        self.btn_cons_cancel.grid(row=0, column=1, padx=(8, 0))
        nb.add(co, text="Consolidate")

    def _build_progress(self):
        f = ttk.Frame(self, padding=(PAD, 0))
        f.grid(row=2, column=0, sticky="ew")
        f.columnconfigure(0, weight=1)
        self.progress_route = ttk.Label(f, text="Idle", style="TLabel")
        self.progress_route.grid(row=0, column=0, sticky="w")
        self.counts = ttk.Label(f, text="", style="Muted.TLabel")
        self.counts.grid(row=0, column=1, sticky="e")
        self.progress = ttk.Progressbar(f, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.elapsed = ttk.Label(f, text="", style="Muted.TLabel")
        self.elapsed.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _build_log(self):
        f = ttk.Frame(self, padding=(PAD, 6))
        f.grid(row=3, column=0, sticky="nsew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        self.log_widget = ScrolledText(f, height=6, wrap="word",
                                       bg=PALETTE["log_bg"], fg=PALETTE["log_fg"],
                                       relief="solid", borderwidth=1,
                                       font=self.fonts["mono"], padx=8, pady=6)
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        self.log_widget.configure(state="disabled")
        self.log_widget.tag_configure("error", foreground=PALETTE["danger"])
        self.log_widget.tag_configure("ok", foreground=PALETTE["success"])

    def _build_footer(self):
        f = ttk.Frame(self, padding=(PAD, 0, PAD, PAD))
        f.grid(row=4, column=0, sticky="ew")
        f.columnconfigure(0, weight=1)
        ttk.Label(f, text=f"All files are saved under:  {OUTPUT_ROOT}",
                  style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        btns = ttk.Frame(f)
        btns.grid(row=0, column=1, sticky="e")
        ttk.Button(btns, text="Open output folder",
                   command=self._open_output_folder).grid(row=0, column=0)
        ttk.Button(btns, text="Logs", command=self._open_logs_folder).grid(row=0, column=1, padx=(8, 0))

    # ---- small helpers ------------------------------------------------------

    def set_dot(self, state, text):
        self.dot.config(foreground=DOT[state])
        self.status_text.config(text=text)

    def log(self, text):
        tag = ""
        upper = text.upper()
        if "FAIL" in upper or "ERROR" in upper:
            tag = "error"
        elif "saved" in text or "Output file" in text or "Output:" in text:
            tag = "ok"
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text + "\n", tag)
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _login_label(self):
        return "Re-login" if self._authed else "Log in"

    def _clear_progress(self):
        self.progress.config(value=0)
        self.counts.config(text="")
        self.progress_route.config(text="Working…")

    def _sync_fast_controls(self):
        """Enable the worker-count spinner only when fast mode is checked."""
        self.fast_spin.state(["!disabled"] if self.fast_mode.get() else ["disabled"])

    def _update_route_feedback(self, *_):
        """Live hint under the Routes entry: blank = all routes, otherwise the
        parsed count, or the validation error while the user is still typing."""
        raw = self.routes_entry.get().strip()
        if not raw:
            self.route_feedback.config(text="Leave blank to export all routes.")
            return
        try:
            chosen = parse_routes(raw)
        except ValueError as e:
            self.route_feedback.config(text=str(e))
            return
        self.route_feedback.config(text=f"{len(chosen)} route(s) selected.")

    def _choose_routes(self):
        """Modal picker: multi-select routes from the full list and write the
        chosen set back into the Routes entry (blank entry = all routes)."""
        dlg = tk.Toplevel(self)
        dlg.title("Choose routes")
        dlg.transient(self)
        dlg.columnconfigure(0, weight=1)
        dlg.rowconfigure(1, weight=1)

        ttk.Label(dlg, text="Select one or more routes "
                            "(Ctrl/Shift-click for multiple):",
                  wraplength=280, justify="left").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=PAD, pady=(PAD, 6))

        lb = tk.Listbox(dlg, selectmode="extended", activestyle="none", height=18,
                        bg=PALETTE["log_bg"], fg=PALETTE["log_fg"], font=self.fonts["mono"],
                        highlightthickness=0, borderwidth=1, relief="solid")
        lb.grid(row=1, column=0, sticky="nsew", padx=(PAD, 0))
        sb = ttk.Scrollbar(dlg, orient="vertical", command=lb.yview)
        sb.grid(row=1, column=1, sticky="ns", padx=(0, PAD))
        lb.configure(yscrollcommand=sb.set)
        for r in ROUTES:
            lb.insert("end", r)

        try:                                    # pre-select whatever is in the entry
            current = set(parse_routes(self.routes_entry.get()))
        except ValueError:
            current = set()
        for i, r in enumerate(ROUTES):
            if r in current:
                lb.selection_set(i)
        sel = lb.curselection()
        if sel:
            lb.see(sel[0])

        def apply_and_close():
            chosen = [ROUTES[i] for i in lb.curselection()]
            self.routes_entry.delete(0, "end")
            self.routes_entry.insert(0, ", ".join(chosen))
            self._update_route_feedback()
            dlg.destroy()

        bar = ttk.Frame(dlg, padding=(PAD, 8))
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(bar, text="Select all",
                   command=lambda: lb.selection_set(0, "end")).grid(row=0, column=0)
        ttk.Button(bar, text="Clear",
                   command=lambda: lb.selection_clear(0, "end")).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(bar, text="Cancel", command=dlg.destroy).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(bar, text="OK", style="Accent.TButton",
                   command=apply_and_close).grid(row=0, column=3, padx=(6, 0))

        # Open at the size the content needs -- the four-button bar is wider than
        # the list -- and keep that as the minimum so the buttons can't be
        # clipped or shrunk out of view.
        dlg.update_idletasks()
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
        dlg.grab_set()

    # ---- elapsed-run timer (shown beneath the progress bar) ------------------

    @staticmethod
    def _fmt_elapsed(seconds):
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def _start_timer(self):
        self._run_start = time.monotonic()
        self.elapsed.config(text="Elapsed  00:00")
        self._tick_timer()

    def _tick_timer(self):
        if self._run_start is None:
            return
        self.elapsed.config(text=f"Elapsed  {self._fmt_elapsed(time.monotonic() - self._run_start)}")
        self._timer_job = self.after(1000, self._tick_timer)   # re-schedule each second

    def _stop_timer(self):
        """Cancel the ticker and freeze the label on the final elapsed time."""
        if self._timer_job is not None:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        if self._run_start is not None:
            self.elapsed.config(text=f"Elapsed  {self._fmt_elapsed(time.monotonic() - self._run_start)}")
            self._run_start = None

    def refresh_auth(self):
        try:
            require_valid_auth()
            self._authed = True
            self.set_dot("ok", "Session ready")
        except AuthError:
            self._authed = False
            self.set_dot("bad", "No saved login — click Log in")
        self.btn_login.config(text=self._login_label())

    # ---- startup readiness checks -------------------------------------------

    def start_checks(self):
        """Run the launch-time readiness checks on a worker thread (browser
        probing is Playwright work and must not touch the Tk thread)."""
        if self.task:                          # never probe mid export/login
            return
        for key, (dot, txt, short) in self._check_items.items():
            dot.config(foreground=DOT["busy"])
            self._check_detail[key] = f"{short}: checking…"
            if txt is not None:
                txt.config(text=f"{short}: checking…")
        self.btn_recheck.state(["disabled"])
        CheckWorker(self.q).start()

    def _set_check(self, key, status, text=None):
        item = self._check_items.get(key)
        if not item:
            return
        dot, txt, _short = item
        dot.config(foreground=DOT.get(status, DOT["unknown"]))
        if text:
            self._check_detail[key] = text          # shown as the hover tooltip
        if txt is not None and text is not None:    # (header dots have no inline text label)
            txt.config(text=text)

    def _on_checks_done(self, results):
        if not self.task:
            self.btn_recheck.state(["!disabled"])
        # If the *selected* browser isn't usable, tell the user what will happen.
        sel = self._label_to_channel.get(self.browser_combo.get())
        usable = [c for c in BROWSER_CHANNELS if results.get(c) == "ok"]
        if sel and results.get(sel) != "ok":
            if usable:
                self.log(f"Note: {CHANNEL_LABELS[sel]} can't be used right now — "
                         f"exports will use {CHANNEL_LABELS[usable[0]]} instead.")
            else:
                self.log("Warning: no usable web browser was found. Install Microsoft "
                         "Edge (or Google Chrome) before running an export.")

    def _on_browser_pick(self, _evt=None):
        channel = self._label_to_channel.get(self.browser_combo.get())
        if channel:
            set_preferred_channel(channel)     # tried first; the other stays a fallback
            self.log(f"Browser set to {self.browser_combo.get()} "
                     "(the other is still used as a fallback if needed).")

    # ---- run-state toggling -------------------------------------------------

    def _set_running(self, task):
        self.task = task
        for w in self._inputs:
            w.state(["disabled"])
        self.fast_spin.state(["disabled"])     # not in _inputs; managed alongside its checkbox
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel,
                  self.btn_save_report):
            w.state(["disabled"])
        if task == "export":
            self.btn_export_skip.state(["!disabled"])
            self.btn_export_cancel.state(["!disabled"])
            self.progress.config(mode="determinate", value=0)
        elif task == "consolidate":
            self.btn_cons_cancel.state(["!disabled"])
            self.progress.config(mode="indeterminate")
            self.progress.start(12)
        self._start_timer()

    def _end_task(self):
        self._stop_timer()
        if str(self.progress.cget("mode")) == "indeterminate":
            self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.task = None
        for w in self._inputs:
            w.state(["!disabled"])
        self._sync_fast_controls()             # restore the spinner to match the checkbox
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel):
            w.state(["disabled"])
        # "Save run report" stays available between runs while a result exists.
        self.btn_save_report.state(["!disabled"] if self._last_results else ["disabled"])
        self.btn_login.config(text=self._login_label(), command=self.start_login)
        self.btn_login_cancel.grid_remove()
        self.progress_route.config(text="Idle")

    # ---- actions ------------------------------------------------------------

    def start_export(self):
        if not self._authed:
            messagebox.showinfo("Login needed", "Please log in first, then start the export.")
            return
        specs = [EXPORT_REPORTS[i][2] for i, v in enumerate(self.export_vars) if v.get()]
        if not specs:
            messagebox.showinfo("Pick a report", "Tick at least one report to export.")
            return
        raw = self.routes_entry.get().strip()
        if raw:
            try:
                run_routes = parse_routes(raw)
            except ValueError as e:
                messagebox.showerror("Check routes", f"{e}\n\nExample: 5, 99, 101")
                return
        else:
            run_routes = list(ROUTES)
        workers = 1
        if self.fast_mode.get():
            try:
                workers = max(2, min(int(self.fast_workers.get()), MAX_WORKERS))
            except (tk.TclError, ValueError):
                workers = DEFAULT_WORKERS
        self._active_specs = specs
        self.cancel_event.clear()
        self.skip_event.clear()
        self._clear_progress()
        names = ", ".join(s.label for s in specs)
        msg = f"Starting export: {names}"
        if len(run_routes) != len(ROUTES):
            msg += f"   ·   {len(run_routes)} routes"
        if workers > 1:
            msg += f"   ·   FAST MODE ({workers} browsers)"
        self.log(msg)
        self._set_running("export")
        if workers > 1:
            # Per-route Skip is meaningless with several routes in flight.
            self.btn_export_skip.state(["disabled"])
        self.set_dot("busy",
                     f"Exporting {len(specs)} report(s)…" if len(specs) > 1
                     else f"Exporting {specs[0].label}…")
        ExportWorker(specs, self.q, self.cancel_event, self.skip_event,
                     workers=workers, routes=run_routes).start()

    def start_consolidate(self):
        label, fn, out_path = CONSOLIDATE_REPORTS[self.cons_choice.get()]
        if out_path.exists() and not messagebox.askyesno(
                "Overwrite?",
                f"A consolidated workbook already exists:\n\n{out_path}\n\nOverwrite it?"):
            self.log("Consolidation cancelled (kept existing file).")
            return
        self.cancel_event.clear()
        self._clear_progress()
        self.log(f"Starting consolidation: {label}")
        self._set_running("consolidate")
        self.set_dot("busy", f"Consolidating {label}…")
        ConsolidateWorker(fn, self.q, self.cancel_event, lambda _p: True).start()

    def skip_current(self):
        if self.task == "export":
            self.skip_event.set()
            self.log("Skip requested — will move on once the current wait ends.")

    def cancel_current(self):
        if self.task in ("export", "consolidate"):
            self.cancel_event.set()
            self.log("Cancel requested…")

    def start_login(self):
        self.login_done.clear()
        self.login_cancel.clear()
        for w in self._inputs:
            w.state(["disabled"])
        self.btn_login.config(text="Opening browser…")
        self.set_dot("busy", "Opening browser…")
        self.task = "login"
        self.log("Opening a browser window for sign-in…")
        LoginWorker(self.q, self.login_done, self.login_cancel).start()

    def finish_login(self):
        self.login_done.set()
        self.btn_login.config(text="Saving…")
        self.btn_login.state(["disabled"])
        self.btn_login_cancel.grid_remove()
        self.set_dot("busy", "Saving session…")

    def cancel_login(self):
        self.login_cancel.set()
        self.login_done.set()
        self.btn_login.config(text="Cancelling…")
        self.btn_login.state(["disabled"])
        self.btn_login_cancel.grid_remove()

    def _open_output_folder(self):
        self._open_folder(OUTPUT_ROOT)

    def _open_consolidated_folder(self):
        self._open_folder(CONSOLIDATED_DIR)

    def _open_logs_folder(self):
        self._open_folder(LOG_DIR)

    def save_report(self):
        """Save a copy of the last run's per-route report to a chosen location.
        For a multi-report run this is one combined CSV (the Report column keeps
        the rows distinguishable). Every run is also auto-saved per report under
        output/run_reports/."""
        if not self._last_results:
            return
        if len(self._last_results) == 1:
            spec, _result = self._last_results[0]
            default = f"run_report_{spec.subdir}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            default = f"run_report_multi_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            title="Save run report",
            defaultextension=".csv",
            initialfile=default,
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        try:
            if len(self._last_results) == 1:
                spec, result = self._last_results[0]
                run_report.write_run_report(result, spec.label, Path(path))
            else:
                run_report.write_run_report_multi(
                    [(spec.label, result) for spec, result in self._last_results], Path(path))
            self.log(f"Run report saved: {path}")
        except Exception as e:
            messagebox.showerror("Could not save report", str(e))

    def _open_folder(self, folder):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))           # Windows
        except Exception as e:
            messagebox.showerror("Could not open folder", str(e))

    # ---- queue pump ---------------------------------------------------------

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                self._handle(kind, payload)
        except Empty:
            pass
        self.after(100, self._drain)

    def _handle(self, kind, payload):
        if kind == "log":
            self.log(payload)
        elif kind == "progress":
            self._update_progress(payload)
        elif kind == "export_done":
            self._finish_export(payload)
        elif kind == "export_partial":
            # A multi-report run errored partway; keep the completed reports so
            # "Save run report…" still covers them. The following "error" message
            # handles the dialog + resets the run state.
            self._last_results = payload
        elif kind == "consolidate_done":
            self._finish_consolidate(payload)
        elif kind == "login_open":
            self._on_login_open()
        elif kind == "login_saved":
            self._on_login_saved()
        elif kind == "login_failed":
            self._on_login_failed()
        elif kind == "check":
            self._set_check(*payload)
        elif kind == "checks_done":
            self._on_checks_done(payload)
        elif kind == "cancelled":
            self.log("Cancelled.")
            self.set_dot("ok" if self._authed else "bad", "Idle")
            self._end_task()
        elif kind == "error":
            self._on_error(payload)

    def _update_progress(self, d):
        self.progress.config(maximum=d["total"], value=d["done"])
        label = d.get("report", "")
        head = ""
        if d.get("report_n", 1) > 1:                 # several report types this run
            head = f"[{d.get('report_i', '?')}/{d['report_n']}] {label}  ·  "
        elif label:
            head = f"{label}  ·  "
        self.progress_route.config(text=f"{head}Route {d['route']}   ·   {d['done']}/{d['total']}")
        self.counts.config(text=(f"saved {d['saved']}   already had {d['exists']}   "
                                 f"empty {d['empty']}   skipped {d['skipped']}   failed {d['failed']}"))

    def _finish_export(self, results):
        # results is [(spec, RunResult), ...] -- one entry per report type run
        # (partial if cancelled before the later reports started).
        self._last_results = results
        self.log("")
        if not results:
            self.log("No reports completed.")
            self.set_dot("ok", "Session ready")
            self._end_task()
            return
        total_saved = total_failed = 0
        for spec, result in results:
            handled = (result.saved + len(result.exists) + len(result.empty)
                       + len(result.user_skipped) + len(result.failed))
            total_saved += result.saved
            total_failed += len(result.failed)
            prefix = f"{spec.label}: " if len(results) > 1 else "Done. "
            self.log(f"{prefix}{handled} routes handled — saved {result.saved}, "
                     f"already had {len(result.exists)}, empty {len(result.empty)}, "
                     f"skipped {len(result.user_skipped)}, failed {len(result.failed)}.")
            if result.failed:
                self.log(f"  Failed routes: {result.failed}")
            if result.report_path:
                self.log(f"  Run report auto-saved: {result.report_path}")
        if len(results) > 1:
            self.log(f"All reports done — total saved {total_saved}, total failed {total_failed}.")
        self.set_dot("ok", "Session ready")
        self._end_task()

    def _finish_consolidate(self, result):
        if result.status == "ok":
            for line in result.summary_lines:
                self.log(line)
            self.set_dot("ok" if self._authed else "bad", "Done")
        elif result.status == "cancelled":
            self.log(result.message or "Cancelled.")
        else:
            self.log(f"ERROR: {result.message}")
            messagebox.showerror("Consolidation failed", result.message)
        self._end_task()

    def _on_login_open(self):
        self.btn_login.state(["!disabled"])
        self.btn_login.config(text="I've finished logging in", command=self.finish_login)
        self.btn_login_cancel.grid()
        self.set_dot("busy", "Waiting — finish sign-in in the browser")
        self.log("Browser opened. Complete sign-in (SSO + MFA), then click "
                 "‘I've finished logging in’.")

    def _on_login_saved(self):
        self.log("Session saved.")
        self.refresh_auth()
        self._end_task()

    def _on_login_failed(self):
        self.log("Login wasn't completed — no new session was saved.")
        messagebox.showinfo(
            "Login not completed",
            "It doesn't look like you finished signing in, so no session was saved.\n\n"
            "Click 'Log in' and complete sign-in until the TSMIS report page loads — "
            "then either click “I've finished logging in” or just close the "
            "browser window, and your session will be saved.")
        self.refresh_auth()                    # dot reflects whatever session we actually have
        self._end_task()

    def _on_error(self, payload):
        kind, message = payload
        self.log(f"ERROR: {message}")
        if kind == "auth":
            clear_auth()
            self._authed = False
            self.set_dot("bad", "No saved login — click Log in")
            messagebox.showwarning("Login needed",
                                   f"{message}\n\nClick 'Log in' to sign in again.")
        else:
            self.set_dot("bad", "Error")
            messagebox.showerror("Error", f"{message}\n\nMore details are in the log file.")
        self._end_task()

    def _on_close(self):
        # Unblock any worker so it can exit cleanly, then close.
        self.cancel_event.set()
        self.login_cancel.set()
        self.login_done.set()
        self._stop_timer()                     # cancel the pending ticker before teardown
        self._hide_tip()
        self.destroy()

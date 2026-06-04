"""Main window for the TSMIS Reports Exporter GUI.

Owns the Tk widgets and the queue pump. All browser/file work runs on worker
threads (gui_worker); this module only reacts to the messages they post, on the
Tk main thread. The engines stay console-free -- the GUI is just another driver
of the same Events seam used by the .bat flow.
"""
import os
import threading
from queue import Empty, Queue

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import gui_theme as theme
from gui_theme import DOT, PALETTE
from gui_worker import ConsolidateWorker, ExportWorker, LoginWorker

from paths import LOG_DIR, OUTPUT_ROOT
from version import APP_NAME, __version__
from common import AuthError, clear_auth, require_valid_auth

from export_ramp_summary import SPEC as SUMMARY_SPEC
from export_ramp_detail import SPEC as DETAIL_SPEC
from export_highway_sequence import SPEC as HIGHWAY_SPEC
import consolidate_ramp_summary as c_summary
import consolidate_ramp_detail as c_detail
import consolidate_highway_sequence as c_highway

# (label, format hint, ReportSpec)
EXPORT_REPORTS = [
    ("TSAR: Ramp Summary", "PDF", SUMMARY_SPEC),
    ("TSAR: Ramp Detail", "Excel", DETAIL_SPEC),
    ("Highway Sequence Listing", "Excel", HIGHWAY_SPEC),
]
# (label, consolidate_fn, OUT_PATH)
CONSOLIDATE_REPORTS = [
    ("TSAR: Ramp Summary", c_summary.consolidate, c_summary.OUT_PATH),
    ("TSAR: Ramp Detail", c_detail.consolidate, c_detail.OUT_PATH),
    ("Highway Sequence Listing", c_highway.consolidate, c_highway.OUT_PATH),
]

CONSOLIDATED_DIR = OUTPUT_ROOT / "consolidated"

PAD = 14


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("660x740")
        self.minsize(580, 620)

        self.fonts = theme.fonts()
        theme.apply(self)

        self.q = Queue()
        self.task = None                       # None | "export" | "consolidate" | "login"
        self._authed = False
        self.cancel_event = threading.Event()
        self.skip_event = threading.Event()
        self.login_done = threading.Event()
        self.login_cancel = threading.Event()

        self.export_choice = tk.IntVar(value=0)
        self.cons_choice = tk.IntVar(value=0)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)         # log row expands

        self._build_header()
        self._build_notebook()
        self._build_progress()
        self._build_log()
        self._build_footer()

        self._inputs = [
            self.btn_login,
            self.btn_export_start, self.btn_cons_start,
            *self.export_radios, *self.cons_radios,
        ]
        # Run-only controls start disabled (no task is running yet).
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel):
            w.state(["disabled"])

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_auth()
        self.after(100, self._drain)

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

    def _build_notebook(self):
        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))

        # Export tab
        ex = ttk.Frame(nb, padding=PAD)
        ex.columnconfigure(0, weight=1)
        ttk.Label(ex, text="REPORT TO EXPORT (all routes)", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        self.export_radios = []
        for i, (label, fmt, _spec) in enumerate(EXPORT_REPORTS):
            rb = ttk.Radiobutton(ex, text=f"{label}   ·   {fmt}", value=i, variable=self.export_choice)
            rb.grid(row=1 + i, column=0, sticky="w")
            self.export_radios.append(rb)
        actions = ttk.Frame(ex)
        actions.grid(row=1 + len(EXPORT_REPORTS), column=0, sticky="w", pady=(PAD, 0))
        self.btn_export_start = ttk.Button(actions, text="Start export", style="Accent.TButton",
                                           command=self.start_export)
        self.btn_export_start.grid(row=0, column=0)
        self.btn_export_skip = ttk.Button(actions, text="Skip route", command=self.skip_current)
        self.btn_export_skip.grid(row=0, column=1, padx=(8, 0))
        self.btn_export_cancel = ttk.Button(actions, text="Cancel", command=self.cancel_current)
        self.btn_export_cancel.grid(row=0, column=2, padx=(8, 0))
        nb.add(ex, text="Export")

        # Consolidate tab
        co = ttk.Frame(nb, padding=PAD)
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

    def _build_log(self):
        f = ttk.Frame(self, padding=(PAD, PAD))
        f.grid(row=3, column=0, sticky="nsew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        self.log_widget = ScrolledText(f, height=12, wrap="word",
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

    def refresh_auth(self):
        try:
            require_valid_auth()
            self._authed = True
            self.set_dot("ok", "Session ready")
        except AuthError:
            self._authed = False
            self.set_dot("bad", "No saved login — click Log in")
        self.btn_login.config(text=self._login_label())

    # ---- run-state toggling -------------------------------------------------

    def _set_running(self, task):
        self.task = task
        for w in self._inputs:
            w.state(["disabled"])
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel):
            w.state(["disabled"])
        if task == "export":
            self.btn_export_skip.state(["!disabled"])
            self.btn_export_cancel.state(["!disabled"])
            self.progress.config(mode="determinate", value=0)
        elif task == "consolidate":
            self.btn_cons_cancel.state(["!disabled"])
            self.progress.config(mode="indeterminate")
            self.progress.start(12)

    def _end_task(self):
        if str(self.progress.cget("mode")) == "indeterminate":
            self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.task = None
        for w in self._inputs:
            w.state(["!disabled"])
        for w in (self.btn_export_skip, self.btn_export_cancel, self.btn_cons_cancel):
            w.state(["disabled"])
        self.btn_login.config(text=self._login_label(), command=self.start_login)
        self.btn_login_cancel.grid_remove()
        self.progress_route.config(text="Idle")

    # ---- actions ------------------------------------------------------------

    def start_export(self):
        if not self._authed:
            messagebox.showinfo("Login needed", "Please log in first, then start the export.")
            return
        spec = EXPORT_REPORTS[self.export_choice.get()][2]
        self.cancel_event.clear()
        self.skip_event.clear()
        self._clear_progress()
        self.log(f"Starting export: {spec.label}")
        self._set_running("export")
        self.set_dot("busy", f"Exporting {spec.label}…")
        ExportWorker(spec, self.q, self.cancel_event, self.skip_event).start()

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
        elif kind == "consolidate_done":
            self._finish_consolidate(payload)
        elif kind == "login_open":
            self._on_login_open()
        elif kind == "login_saved":
            self._on_login_saved()
        elif kind == "cancelled":
            self.log("Cancelled.")
            self.set_dot("ok" if self._authed else "bad", "Idle")
            self._end_task()
        elif kind == "error":
            self._on_error(payload)

    def _update_progress(self, d):
        self.progress.config(maximum=d["total"], value=d["done"])
        self.progress_route.config(text=f"Route {d['route']}   ·   {d['done']}/{d['total']}")
        self.counts.config(text=(f"saved {d['saved']}    empty {d['empty']}    "
                                 f"skipped {d['skipped']}    failed {d['failed']}"))

    def _finish_export(self, result):
        self.log("")
        self.log(f"Done. Saved {result.saved}, empty {len(result.empty)}, "
                 f"skipped {len(result.user_skipped)}, failed {len(result.failed)}.")
        if result.failed:
            self.log(f"Failed routes: {result.failed}")
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
        self.destroy()

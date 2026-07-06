"""GuiCompareMixin — extracted verbatim from gui_api.GuiApi (S1 / ARC-02, v0.19.0):
consolidate run/preview and the file/env comparison endpoints (pickers,
suggested names, run/cancel).
Composition only — every `self._*` it touches lives on GuiApi.
"""
import logging
from pathlib import Path

import webview

import artifact_store
from gui_endpoint import _api_method      # the shared js_api decorator
from gui_worker import ConsolidateWorker
from paths import OUTPUT_ROOT, list_output_days, list_output_days_for_report
from reports import (COMPARE_REPORTS, CONSOLIDATE_REPORTS,
                     compare_index_for_key, consolidate_index_for_key)

ui_log = logging.getLogger("tsmis.ui")


class GuiCompareMixin:
    # ---- consolidate -------------------------------------------------------------

    @_api_method
    def consolidate_info(self, report_key, day):
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        _label, mod = row
        out = mod.out_path_for(day)
        info = {"dest_dir": str(out.parent), "out_path": str(out),
                "exists": out.exists()}
        # Reports whose input is user-supplied (TSN PDFs) advertise it so the
        # pane can say where the files go and offer to open that folder.
        note = getattr(mod, "INPUT_NOTE", None)
        if note:
            info["input_note"] = note
            info["input_dir"] = str(mod.input_dir_for(day or None))
        return info

    @_api_method
    def open_consolidate_input(self, report_key):
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        _label, mod = row
        in_dir = getattr(mod, "INPUT_DIR", None)
        if in_dir is None:
            return {"error": "This report has no input folder."}
        self._open_folder(in_dir)
        return {"ok": True}

    @_api_method
    def decline_overwrite(self):
        self._emit_log("Consolidation cancelled (kept existing file).")
        return {"ok": True}

    @_api_method
    def start_consolidate(self, report_key, day):
        # Validate the report KEY + day BEFORE claiming the slot -- otherwise a bad
        # key would leave self._task set, wedging the task gate "consolidate"
        # forever (every later action blocked until restart).
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        label, mod = row
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        self._emit_log(f"Starting consolidation: {label}" + (f"   ·   {day}" if day else ""))
        self._set_dot("busy", f"Consolidating {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Consolidating {label}…"})
        self._push_state()
        # Overwrite was resolved by the UI before start (consolidate_info +
        # confirm dialog), so the injected callback just says yes.
        ConsolidateWorker(mod.consolidate, self._gated_queue(), self.cancel_event,
                          lambda _p: True, day=day).start()
        return {"ok": True}

    # ---- comparisons (TSMIS vs TSN files / env vs env run folders) -----------------

    @_api_method
    def pick_compare_file(self, side):
        """Native open dialog for one comparison input. `side` is "TSMIS" or
        "TSN" (display only). Returns {"path": ...} or {"cancelled": True}."""
        picked = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            return {"cancelled": True}
        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        ui_log.info("compare: %s file picked: %s", side, path)
        return {"path": str(path)}

    @_api_method
    def pick_compare_folder(self, side):
        """Native folder dialog for one cross-environment comparison side
        (for folders outside output/ — the dropdowns list the run folders)."""
        picked = self._window.create_file_dialog(
            webview.FOLDER_DIALOG, directory=str(OUTPUT_ROOT))
        if not picked:
            return {"cancelled": True}
        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        ui_log.info("compare: side %s folder picked: %s", side, path)
        return {"path": str(path)}

    def _save_dialog_for_compare(self, directory, suggested):
        """Shared save dialog — the native dialog also owns the overwrite
        question. Returns a Path or None (cancelled)."""
        picked = self._window.create_file_dialog(
            webview.SAVE_DIALOG, directory=str(directory),
            save_filename=suggested,
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            ui_log.info("compare: save dialog cancelled")
            return None
        return Path(picked[0] if isinstance(picked, (list, tuple)) else picked)

    @staticmethod
    def _compare_mode(want_formulas, want_values):
        if not want_formulas and not want_values:
            return None
        return ("both" if want_formulas and want_values
                else "formulas" if want_formulas else "values")

    def _launch_compare(self, label, mode, out, run_fn):
        # The task slot was already claimed by the caller (before the save
        # dialog), so a second click can't slip in while the dialog is open.
        self.cancel_event.clear()
        kinds = {"both": "values + live formulas", "formulas": "live formulas",
                 "values": "values"}[mode]
        self._emit_log(f"Starting comparison: {label} ({kinds})")
        ui_log.info("compare: %s mode=%s out=%s", label, mode, out)
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Comparing — {label}…"})
        self._push_state()
        # F9: the comparator writes to a temp path; commit_workbook validates + os.replaces
        # it onto the picked name (compare_core untouched). For mode="both" the VALUES
        # workbook is the single transactional artifact (committed first) and the formulas
        # sibling is best-effort, so an interrupted run never leaves a values copy without
        # its twin (or a truncated picked file). The OS save dialog already confirmed the
        # destination, so the inner confirm is a pass-through.
        def committed(events=None, confirm_overwrite=None, day=None):
            return artifact_store.commit_workbook(
                out,
                lambda tmp: run_fn(tmp, events=events,
                                   confirm_overwrite=lambda _p: True, day=day),
                twin=(mode == "both"), expect_sheet="Comparison")
        ConsolidateWorker(committed, self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    def _begin_compare(self, label, mode, save_dir, suggest, build):
        """Shared claim → save-dialog → launch tail for the two compare endpoints
        (P7b unify of start_compare / start_compare_env). Claims the single-task gate
        BEFORE the blocking save dialog so a second click is rejected at once. `suggest`
        is a *lazy* default-name callable evaluated INSIDE the claim (preserving the
        pre-P7b ordering where suggest_name ran after the claim), so a suggest-name /
        dialog / launch-prep error releases the gate and can never wedge it.
        `build(out_path, events, confirm_overwrite, day)` is the comparator call
        (`mod.compare` / `adapter.compare_folders`)."""
        err = self._claim_task_error("compare")
        if err:
            return err
        try:
            out = self._save_dialog_for_compare(save_dir, suggest())
            if out is None:
                self._release_task()
                return {"cancelled": True}
            return self._launch_compare(label, mode, out, build)
        except Exception:
            self._release_task()        # a suggest-name/dialog/launch error must not wedge the gate
            raise

    @_api_method
    def start_compare(self, report_key, tsmis_path, tsn_path,
                      want_formulas=True, want_values=False):
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, mod, kind, _group = row[:4]
        if kind != "files":
            return {"error": "This comparison type takes folders, not files."}
        if not tsmis_path or not tsn_path:
            return {"error": "Pick both files first (a TSMIS and a TSN workbook)."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        return self._begin_compare(
            label, mode, Path(tsmis_path).parent,
            lambda: mod.suggest_name(tsmis_path),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                mod.compare(tsmis_path, tsn_path, out_path, events=events,
                            confirm_overwrite=confirm_overwrite, mode=mode))

    @_api_method
    def get_compare_folders(self, report_key):
        """Run folders that contain the chosen cross-env report (the compare
        folder dropdowns call this on report-type change so only usable runs are
        offered — A2). 'files'-kind comparisons and adapters without a subdir
        return all folders (their dropdowns aren't shown). Pure filesystem stat;
        no task lock, no browser."""
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"folders": list_output_days()}
        _label, adapter, kind, _group = row[:4]
        subdir = getattr(adapter, "subdir", None)
        if kind != "folders" or not subdir:
            return {"folders": list_output_days()}
        return {"folders": list_output_days_for_report(subdir)}

    @_api_method
    def start_compare_env(self, report_key, dir_a, dir_b,
                          want_formulas=True, want_values=False):
        """Cross-environment comparison: two run folders (names from the
        dropdowns resolve under output/; Browse… hands in absolute paths)."""
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, adapter, kind, _group = row[:4]
        if kind != "folders":
            return {"error": "This comparison type takes files, not folders."}
        if not dir_a or not dir_b:
            return {"error": "Pick both export folders first."}
        # A dropdown hands in a run-folder NAME (resolved under output/, with
        # traversal rejected); Browse… hands in an absolute path the user
        # explicitly chose, used as-is.
        try:
            pa = Path(dir_a) if Path(dir_a).is_absolute() else self._resolve_under_output(dir_a)
            pb = Path(dir_b) if Path(dir_b).is_absolute() else self._resolve_under_output(dir_b)
        except ValueError as e:
            return {"error": str(e)}
        # A2 server-side guard mirroring the filtered dropdowns: a run folder
        # picked from the list must actually hold this report's export (Browse…
        # absolute paths are the user's explicit choice and skip this).
        subdir = getattr(adapter, "subdir", None)
        if subdir:
            for raw, p in ((dir_a, pa), (dir_b, pb)):
                if Path(raw).is_absolute():
                    continue
                sub = p / subdir
                try:
                    present = sub.is_dir() and any(sub.iterdir())
                except OSError:
                    present = False
                if not present:
                    return {"error": f"The folder “{raw}” has no {label} export "
                                     "to compare — pick one that does."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        import compare_env
        compare_env.DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
        return self._begin_compare(
            label, mode, compare_env.DEFAULT_OUT_DIR,
            lambda: adapter.suggest_name(pa, pb),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                adapter.compare_folders(pa, pb, out_path, events=events,
                                        confirm_overwrite=confirm_overwrite,
                                        mode=mode))

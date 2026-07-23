"""GuiCompareMixin — extracted verbatim from gui_api.GuiApi (S1 / ARC-02, v0.19.0):
consolidate run/preview and the file/env comparison endpoints (pickers,
suggested names, run/cancel).
Composition only — every `self._*` it touches lives on GuiApi.
"""
import logging
import secrets
from pathlib import Path

import webview

import artifact_store
from gui_endpoint import _api_method, pick_path   # + the dialog unwrap
from gui_worker import ConsolidateWorker
from paths import (OUTPUT_ROOT, list_output_days, list_output_days_for_report,
                   manual_comparisons_dir)
from reports import (COMPARE_REPORTS, CONSOLIDATE_REPORTS,
                     compare_index_for_key, compare_input_accepts_suffix,
                     compare_input_extensions,
                     consolidate_index_for_key)

ui_log = logging.getLogger("tsmis.ui")


def _comparison_overwrite_authorizer(out, mode, confirmed_twin=None, *,
                                     picked_was_existing=False):
    """Authorize only destinations whose overwrite decision the user made.

    The picked output is owned by the native Save dialog, but only if it already
    existed when that dialog returned (and therefore was the path the dialog
    confirmed).  If it was absent and appears later, fail closed.  In ``both`` mode the
    automatically derived values sibling is a separate decision: it is allowed
    only after the server-bound confirmation for that exact pathname.  Returning
    False also makes a values sibling that appears after the initial check fail
    closed instead of being silently overwritten.
    """
    destinations = artifact_store.comparison_output_paths(out, mode)
    picked = artifact_store.canonical_path_identities((destinations[0],))
    twin = (artifact_store.canonical_path_identities((destinations[1],))
            if len(destinations) == 2 else None)
    confirmed = (artifact_store.canonical_path_identities((confirmed_twin,))
                 if confirmed_twin is not None else None)
    if confirmed is not None and confirmed != twin:
        raise ValueError("The comparison overwrite confirmation no longer matches "
                         "the derived values workbook.")

    def authorize(path):
        identity = artifact_store.canonical_path_identities((path,))
        if identity == picked:
            return bool(picked_was_existing)
        return twin is not None and confirmed == twin and identity == twin

    return authorize


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
        else:
            # Offer only the run-folder days where THIS report was actually
            # exported, so the picker never lists a day the report is absent from.
            subdir = getattr(mod, "SUBDIR", None)
            if subdir:
                info["days"] = list_output_days_for_report(subdir)
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
    def pick_compare_file(self, side, key=None):
        """Native open dialog for one comparison input. `side` is "TSMIS" or
        "TSN" (also the picker slot). `key` is the selected `cmp:*` recipe key;
        it selects the native filter so the recipe/side that accepts a raw TSN PDF
        offers it (CMP-AUD-073). Returns {"path": ...} or {"cancelled": True}."""
        file_types = tuple(compare_input_extensions(key, side))
        picked = pick_path(self._window,
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=file_types)
        if not picked:
            return {"cancelled": True}
        ui_log.info("compare: %s file picked: %s", side, picked)
        return {"path": picked}

    @_api_method
    def pick_compare_folder(self, side):
        """Native folder dialog for one cross-environment comparison side
        (for folders outside output/ — the dropdowns list the run folders)."""
        picked = pick_path(self._window, 
            webview.FOLDER_DIALOG, directory=str(OUTPUT_ROOT))
        if not picked:
            return {"cancelled": True}
        ui_log.info("compare: side %s folder picked: %s", side, picked)
        return {"path": picked}

    def _save_dialog_for_compare(self, directory, suggested):
        """Shared save dialog — the native dialog also owns the overwrite
        question. Returns a Path or None (cancelled)."""
        picked = pick_path(self._window, 
            webview.SAVE_DIALOG, directory=str(directory),
            save_filename=suggested,
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            ui_log.info("compare: save dialog cancelled")
            return None
        return Path(picked)

    @staticmethod
    def _compare_mode(want_formulas, want_values):
        if not want_formulas and not want_values:
            return None
        return ("both" if want_formulas and want_values
                else "formulas" if want_formulas else "values")

    def _launch_compare(self, label, mode, out, run_fn, source_paths=(), *,
                        captured_sources=None, confirmed_twin=None,
                        picked_was_existing=False):
        # The task slot was already claimed by the caller (before the save
        # dialog), so a second click can't slip in while the dialog is open.
        self.cancel_event.clear()
        kinds = {"both": "values + live formulas", "formulas": "live formulas",
                 "values": "values"}[mode]
        self._emit_log(f"Starting comparison: {label} ({kinds})")
        ui_log.info("compare: %s mode=%s out=%s", label, mode, out)
        # Name both compared inputs in the log (M1-B) — "one log upload answers
        # it": a standalone comparison used to record only its output path, so a
        # bad result couldn't be traced back to which files it read.
        for i, path in enumerate(source_paths, start=1):
            ui_log.info("compare:   input %d: %s", i, path)
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Comparing — {label}…"})
        self._push_state()
        # The public comparator owns the one atomic transaction (including
        # values-first mode="both" semantics).  Wrapping it in a second
        # commit_workbook would make its legitimate inner os.replace look exactly
        # like an attacker replacing the outer reserved temp.  The OS save dialog
        # already confirmed the picked destination; the derived values sibling has
        # its own explicit path-bound decision, and an unconfirmed sibling that
        # appears late is denied by the callback passed straight through.
        confirm_destination = _comparison_overwrite_authorizer(
            out, mode, confirmed_twin=confirmed_twin,
            picked_was_existing=picked_was_existing)

        def committed(events=None, confirm_overwrite=None, day=None):
            # Revalidate the identities captured immediately after the native
            # dialog (and again after any derived-twin human confirmation) at
            # worker entry.  The direct comparator then carries its own capture
            # through loading and final publication.
            artifact_store.ensure_outputs_do_not_alias_sources(
                artifact_store.comparison_output_paths(out, mode), source_paths,
                captured_sources=captured_sources,
                require_sources_current=True)
            result = run_fn(out, events=events,
                            confirm_overwrite=confirm_destination, day=day)
            # Preserve operation identity even for early comparator errors that
            # have no typed outcome yet, so the shared terminal UI never calls a
            # comparison failure a consolidation failure.
            try:
                result.operation_kind = "comparison"
            except (AttributeError, TypeError):  # silent-ok: immutable legacy/test shims lack the additive marker
                pass
            return result
        ConsolidateWorker(committed, self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    def _begin_compare(self, label, mode, save_dir, suggest, build, source_paths=()):
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
            # Earliest observable state after the native dialog returns.  If the
            # picked path was absent here, any later appearance was not an overwrite
            # that the dialog could have confirmed and must fail closed.
            picked_was_existing = out.exists()
            source_paths = tuple(source_paths or ())
            captured_sources = artifact_store.capture_source_identities(source_paths)
            destinations = artifact_store.comparison_output_paths(out, mode)
            # Source safety takes precedence over overwrite consent: never ask the
            # user to approve a path that is itself one of the selected inputs.
            artifact_store.ensure_outputs_do_not_alias_sources(
                destinations, source_paths, captured_sources=captured_sources,
                require_sources_current=True)

            if mode == "both" and destinations[1].exists():
                twin = destinations[1]
                token = secrets.token_urlsafe(16)
                # No launch endpoint parameters are accepted later.  Retain the
                # exact closure, paths, mode and source identities selected now,
                # under the already-claimed task slot.
                pending = {
                    "token": token,
                    "label": label,
                    "mode": mode,
                    "out": Path(out),
                    "build": build,
                    "source_paths": source_paths,
                    "captured_sources": captured_sources,
                    "twin": Path(twin),
                    "picked_was_existing": picked_was_existing,
                }
                with self._lock:
                    self._compare_overwrite_token = pending
                ui_log.info("compare: awaiting overwrite confirmation for derived "
                            "values workbook: %s", twin)
                return {
                    "confirm_required": True,
                    "confirm_token": token,
                    "path": str(twin),
                    "message": (
                        "The automatically created values workbook already exists:"
                        f"\n\n{twin}\n\nOverwrite this exact file? The formulas "
                        "workbook remains the file selected in the Save dialog."
                    ),
                }

            # No values sibling existed at the decision point.  Pass no approval:
            # commit_workbook will refuse it if one appears before publication.
            return self._launch_compare(
                label, mode, out, build, source_paths,
                captured_sources=captured_sources, confirmed_twin=None,
                picked_was_existing=picked_was_existing)
        except Exception:
            self._release_task()        # a suggest-name/dialog/launch error must not wedge the gate
            raise

    @_api_method
    def confirm_compare_overwrite(self, confirm_token=None, accepted=False):
        """Resolve the parked derived-values overwrite decision exactly once.

        The token selects an operation stored wholly on the server; callers cannot
        submit replacement inputs, output, mode, or comparator parameters here.
        """
        with self._lock:
            pending = self._compare_overwrite_token
            if not pending or confirm_token != pending["token"]:
                ui_log.warning("compare: refused stale or mismatched derived-values "
                               "overwrite confirmation")
                return {"error": "That comparison confirmation is no longer valid. "
                                 "Start the comparison again."}
            self._compare_overwrite_token = None       # matching token: single-use

        if accepted is not True:
            self._emit_log(f"Comparison cancelled (kept existing file: "
                           f"{pending['twin']}).")
            self._release_task()
            return {"cancelled": True}

        try:
            destinations = artifact_store.comparison_output_paths(
                pending["out"], pending["mode"])
            if (len(destinations) != 2
                    or artifact_store.canonical_path_identities((destinations[1],))
                    != artifact_store.canonical_path_identities((pending["twin"],))):
                raise ValueError("The derived values workbook changed after the "
                                 "confirmation prompt.")
            # Re-check after the human think-time.  A source-alias introduced while
            # the prompt was open wins over consent and aborts before any worker runs.
            artifact_store.ensure_outputs_do_not_alias_sources(
                destinations, pending["source_paths"],
                captured_sources=pending["captured_sources"],
                require_sources_current=True)
            return self._launch_compare(
                pending["label"], pending["mode"], pending["out"],
                pending["build"], pending["source_paths"],
                captured_sources=pending["captured_sources"],
                confirmed_twin=pending["twin"],
                picked_was_existing=pending["picked_was_existing"])
        except Exception:
            self._release_task()
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
        # CMP-AUD-016: preflight existence + type/role for the recipe BEFORE the task
        # is claimed and the Save dialog opens — a stale (deleted/moved) or wrong-type
        # selection carried over from another recipe is refused here with a clear
        # message, not deep in the adapter after the run already owns the gate. (The
        # comparator still enforces its own loader contract on top of this.)
        for role, side, p in (("TSMIS", "tsmis", tsmis_path), ("TSN", "tsn", tsn_path)):
            fp = Path(p)
            if not fp.is_file():
                return {"error": f"The selected {role} file no longer exists — "
                                 "pick it again (it may have moved or been deleted)."}
            if not compare_input_accepts_suffix(report_key, side, fp.suffix):
                return {"error": f"The selected {role} file isn't a supported type "
                                 "for this comparison — pick the right file."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        # c14: a manual comparison auto-defaults into output/comparisons/manual/
        # (self-identifying name via suggest_name), so ad-hoc comparisons land in
        # one predictable place instead of beside whatever file was picked. The
        # native dialog still lets the user redirect ("Save elsewhere…").
        save_dir = manual_comparisons_dir()
        save_dir.mkdir(parents=True, exist_ok=True)
        return self._begin_compare(
            label, mode, save_dir,
            lambda: mod.suggest_name(tsmis_path),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                mod.compare(tsmis_path, tsn_path, out_path, events=events,
                            confirm_overwrite=confirm_overwrite, mode=mode),
            source_paths=(tsmis_path, tsn_path))

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
        # c14: cross-env manual comparisons also auto-default into
        # output/comparisons/manual/ (was the shared comparisons/ root).
        save_dir = manual_comparisons_dir()
        save_dir.mkdir(parents=True, exist_ok=True)
        return self._begin_compare(
            label, mode, save_dir,
            lambda: adapter.suggest_name(pa, pb),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                adapter.compare_folders(pa, pb, out_path, events=events,
                                        confirm_overwrite=confirm_overwrite,
                                        mode=mode),
            source_paths=(pa, pb))

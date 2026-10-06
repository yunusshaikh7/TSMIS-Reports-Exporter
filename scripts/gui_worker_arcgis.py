"""Workers for the ArcGIS tab: the layer refresh and the ArcGIS Pro check
(Layers, v0.46.0) and the ArcGIS report refresh (ArcGIS reports, v0.47.0).

All three ride the shared matrix queue: one job at a time, cancelled by the
same Cancel, and nothing else reads the layer library while a refresh swaps
files in. Progress goes out as ('matrix_cell', …) — the row is the layer being
exported, or the report being built — and each run ends with exactly one
('matrix_done', …) whose `label` names it in the log ("Layer refresh" /
"ArcGIS Pro check" / "ArcGIS report refresh").
"""
import logging
import threading
import time

import outcome
from events import Events

log = logging.getLogger("tsmis.gui")


def _done_payload(label, attempted, succeeded, failed, cancelled, started):
    return {"label": label, "done": succeeded, "total": attempted,
            "errors": failed, "cancelled": cancelled, "attempted": attempted,
            "succeeded": succeeded, "failed": failed if not cancelled else 0,
            "cancelled_cells": (attempted - succeeded - failed) if cancelled else 0,
            "partial_cells": 0, "elapsed_s": round(time.monotonic() - started, 1)}


class ArcgisLayerRefreshWorker(threading.Thread):
    """Refresh `layers` (None = all 40) from the feature service with ArcGIS
    Pro, swapping each finished layer into the library."""

    def __init__(self, layers, queue, cancel_event):
        super().__init__(daemon=True, name="arcgis-layer-refresh")
        self.layers = layers
        self.q = queue
        self.cancel = cancel_event

    def _progress(self, p):
        self.q.put(("matrix_cell", {
            "row": p.get("layer"), "cell": None, "done": p.get("done", 0),
            "total": p.get("total", 0), "elapsed_s": p.get("elapsed_s"),
            "eta_s": None}))

    def run(self):
        import arcgis_refresh                         # lazy: pulls openpyxl

        started = time.monotonic()
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        total = len(self.layers or arcgis_refresh.LIBRARY_LAYERS)
        res = None
        try:
            res = arcgis_refresh.refresh(self.layers, events=events,
                                         cancel_event=self.cancel,
                                         on_progress=self._progress)
            if res.status == "error":
                self.q.put(("log", f"Layer refresh could not start: {res.message}"))
        except Exception as e:                       # noqa: BLE001
            log.exception("arcgis layer refresh crashed")
            self.q.put(("log", f"Layer refresh failed ({type(e).__name__}): {e}"))
        finally:
            layers = res.layers if res is not None else []
            succeeded = sum(1 for r in layers if r.get("status") == "exported")
            failed = sum(1 for r in layers if r.get("status") == "failed")
            if res is None or res.status == "error":
                failed = max(failed, 1)
            if succeeded:
                self.q.put(("log", "Next: the ArcGIS reports were built from the old "
                                   "layers — refresh them on ArcGIS ▸ ArcGIS reports."))
            self.q.put(("matrix_done", _done_payload(
                "Layer refresh", total, succeeded, failed,
                self.cancel.is_set(), started)))


class ArcgisProProbeWorker(threading.Thread):
    """Start ArcGIS Pro's Python, read and export the 27-row SHS Tolls layer,
    and compare it with the library's own copy."""

    def __init__(self, queue, cancel_event):
        super().__init__(daemon=True, name="arcgis-pro-check")
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        import arcgis_refresh

        started = time.monotonic()
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        ok = False
        try:
            ok = bool(arcgis_refresh.probe(events=events,
                                           cancel_event=self.cancel).get("ok"))
        except Exception as e:                       # noqa: BLE001
            log.exception("arcgis pro check crashed")
            self.q.put(("log", f"ArcGIS Pro check failed ({type(e).__name__}): {e}"))
        finally:
            self.q.put(("matrix_done", _done_payload(
                "ArcGIS Pro check", 1, 1 if ok else 0, 0 if ok else 1,
                self.cancel.is_set(), started)))


class ArcgisReportBuildWorker(threading.Thread):
    """Refresh ArcGIS report builds inside the matrix queue — `row_keys` are the
    reports, built one after another — so they line up with the comparisons
    that read them and are cancellable the same way. Offline (openpyxl over the
    layer library; a statewide Highway Detail build runs 25-30 minutes).

    Each report's outcome is recorded for the ArcGIS reports tab (a failed or
    cancelled refresh keeps its line until a later one lands), progress goes out
    as ('matrix_cell', …) with the report being built, and the run ends with ONE
    ('matrix_done', …) labelled "ArcGIS report refresh". A build that did not
    finish `ok` (failed, cancelled, or the layers refused) is reported as such —
    never as a success. Cancel stops between reports as well as inside one."""

    def __init__(self, row_keys, asof, queue, cancel_event):
        super().__init__(daemon=True, name="arcgis-report-build")
        self.row_keys = ([row_keys] if isinstance(row_keys, str)
                         else list(row_keys or []))
        self.asof = asof
        self.q = queue
        self.cancel = cancel_event

    def _record(self, key, status, reason=""):
        import arcgis_matrix
        try:
            arcgis_matrix.record_build_attempt(key, status, reason)
        except Exception as e:                       # noqa: BLE001 - diagnostic only
            log.warning("arcgis: build attempt for %s not recorded (%s: %s)",
                        key, type(e).__name__, e)

    def _build_one(self, key, events):
        """Build one report; returns 'ok' / 'partial' / 'failed' / 'cancelled'."""
        import arcgis_matrix                          # lazy: pulls the layer builds
        import arcgis_reports

        label = arcgis_reports.label_of(key)
        try:
            res = arcgis_matrix.build_report(key, events, asof=self.asof)
            if getattr(res, "status", None) != "ok":
                raise ValueError(getattr(res, "message", None)
                                 or f"the {label} build did not finish")
        except Exception as e:                       # noqa: BLE001
            if self.cancel.is_set():
                self.q.put(("log", f"ArcGIS report refresh stopped: {label}."))
                self._record(key, "cancelled", "the refresh was cancelled")
                return "cancelled"
            log.exception("arcgis report build (%s) crashed", key)
            self.q.put(("log", f"{label} ArcGIS report failed "
                               f"({type(e).__name__}): {e}"))
            self._record(key, "error", str(e) or type(e).__name__)
            return "failed"
        self._record(key, arcgis_matrix.BUILD_OK)
        self.q.put(("log", f"{label} ArcGIS report ready: {res.output_path}"))
        return ("ok" if outcome.consolidate_completion_of(res) == outcome.COMPLETE
                else "partial")

    def run(self):
        import arcgis_reports

        started = time.monotonic()
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        total = len(self.row_keys)
        counts = {"ok": 0, "partial": 0, "failed": 0, "cancelled": 0}
        try:
            for i, key in enumerate(self.row_keys):
                if self.cancel.is_set():
                    break
                self.q.put(("matrix_cell", {
                    "row": arcgis_reports.label_of(key), "cell": None, "done": i,
                    "total": total, "elapsed_s": round(time.monotonic() - started, 1),
                    "eta_s": None}))
                counts[self._build_one(key, events)] += 1
        finally:
            cancelled = self.cancel.is_set()
            succeeded = counts["ok"] + counts["partial"]
            self.q.put(("matrix_done", {
                "label": "ArcGIS report refresh",
                "done": succeeded, "total": total,
                "errors": counts["failed"] + counts["cancelled"],
                "cancelled": cancelled, "attempted": total,
                "succeeded": succeeded,
                "failed": counts["failed"],
                "cancelled_cells": (total - succeeded - counts["failed"]
                                    if cancelled else 0),
                "partial_cells": counts["partial"],
                "elapsed_s": round(time.monotonic() - started, 1)}))

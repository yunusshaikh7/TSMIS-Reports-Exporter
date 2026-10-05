"""Workers for the ArcGIS ▸ Layers tab (v0.46.0): the layer refresh and the
ArcGIS Pro check.

Both ride the shared matrix queue like the layer builds (gui_worker_matrix's
ArcgisReportBuildWorker): one job at a time, cancelled by the same Cancel, and
nothing else reads the layer library while a refresh swaps files in. Progress
goes out as ('matrix_cell', …) — the row is the layer being exported — and
each run ends with exactly one ('matrix_done', …) whose `label` names it in the
log ("Layer refresh" / "ArcGIS Pro check").
"""
import logging
import threading
import time

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

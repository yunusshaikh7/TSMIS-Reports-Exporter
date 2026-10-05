"""GuiArcgisLayersMixin — the ArcGIS ▸ Layers tab's endpoints (v0.46.0).

The tab manages the app's own copy of the TSMIS layers (`arcgis_layers/`):
every library layer with its row count, export time and the builds that read
it, plus the two jobs that replace the manual export —

  * **Refresh layers** — ArcGIS Pro's own Python exports the chosen layers
    (default: all 40) from the feature service and each finished one is
    checked and swapped in (`arcgis_refresh.refresh`);
  * **Check ArcGIS Pro** — a quick end-to-end check: start ArcPy, read and
    export the 27-row SHS Tolls layer, compare it with the library's copy.

Both ride the shared matrix queue (kinds `arcgis_refresh` / `arcgis_probe`),
so they line up behind or ahead of the layer builds and comparisons, never run
beside them, and stop with the same Cancel. ArcGIS Pro's python.exe is found
automatically; "Choose python.exe…" overrides it on a PC where it isn't.
Composition only — every `self._*` it touches lives on GuiApi.
"""
import logging
import os
from pathlib import Path

import webview

import settings
from gui_endpoint import _api_method, pick_path
from gui_worker_arcgis import ArcgisLayerRefreshWorker, ArcgisProProbeWorker

ui_log = logging.getLogger("tsmis.ui")

_LAYER_JOBS = ("arcgis_refresh", "arcgis_probe")


class GuiArcgisLayersMixin:
    @_api_method
    def arcgis_layers_info(self):
        """The Layers tab's payload: the library (every layer + the run
        records), ArcGIS Pro's status, and whether a layer job is running or
        queued. Pure filesystem; no task lock."""
        import arcgis_pro
        import arcgis_refresh

        info = arcgis_refresh.library_status()
        info["pro"] = arcgis_pro.status()
        with self._lock:
            cur = self._current_job
            queued = sum(1 for j in self._queue if j.get("kind") in _LAYER_JOBS)
        info["running"] = (cur.get("kind") if cur and cur.get("kind") in _LAYER_JOBS
                           else None)
        info["queued"] = queued
        return info

    @_api_method
    def refresh_arcgis_layers(self, layers=None):
        """Queue a refresh of `layers` (a list of layer names; empty = all)."""
        import arcgis_pro
        import arcgis_refresh

        if layers is not None and not isinstance(layers, (list, tuple)):
            return {"error": "Pick the layers to refresh."}
        try:
            names = arcgis_refresh.resolve_layers(layers or None)
        except ValueError as e:
            return {"error": str(e)}
        python, _how = arcgis_pro.resolve_python()
        if not python:
            return {"error": arcgis_refresh.no_python_message()}
        every = len(names) == len(arcgis_refresh.LIBRARY_LAYERS)
        label = ("Refresh all ArcGIS layers" if every
                 else f"Refresh {len(names)} ArcGIS layer{'s' if len(names) != 1 else ''}")
        job = self._make_job("arcgis_refresh", "cell", label, which="arcgis",
                             layers=None if every else names)
        return self._enqueue_matrix_job(job)

    @_api_method
    def check_arcgis_pro(self):
        """Queue the quick ArcGIS Pro check."""
        import arcgis_pro
        import arcgis_refresh

        python, _how = arcgis_pro.resolve_python()
        if not python:
            return {"error": arcgis_refresh.no_python_message()}
        job = self._make_job("arcgis_probe", "cell", "Check ArcGIS Pro", which="arcgis")
        return self._enqueue_matrix_job(job)

    @_api_method
    def choose_arcgis_python(self):
        """Native open dialog for ArcGIS Pro's python.exe (for a PC where it
        isn't found automatically). Returns {ok, pro} / {cancelled} / {error}."""
        import arcgis_pro

        start = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ArcGIS"
        picked = pick_path(self._window, webview.OPEN_DIALOG, allow_multiple=False,
                           directory=str(start if start.is_dir() else Path.home()),
                           file_types=("Programs (*.exe)",))
        if not picked:
            return {"cancelled": True}
        path = Path(picked)
        if path.name.lower() != "python.exe":
            return {"error": "Choose ArcGIS Pro's python.exe — usually "
                             r"C:\Program Files\ArcGIS\Pro\bin\Python\envs"
                             r"\arcgispro-py3\python.exe."}
        settings.set_arcgis_python(str(path))
        self._emit_log(f"ArcGIS Pro's Python set to {path}.")
        return {"ok": True, "pro": arcgis_pro.status()}

    @_api_method
    def clear_arcgis_python(self):
        """Forget the chosen python.exe and find ArcGIS Pro automatically."""
        import arcgis_pro

        settings.set_arcgis_python("")
        self._emit_log("ArcGIS Pro's Python: finding it automatically again.")
        return {"ok": True, "pro": arcgis_pro.status()}

    # -- the queue's dispatch hooks (called by gui_matrix's dispatcher) -------- #
    def _dispatch_arcgis_refresh_job(self, job):
        import arcgis_refresh

        layers = job.get("layers")
        total = len(layers) if layers else len(arcgis_refresh.LIBRARY_LAYERS)
        with self._lock:
            self._matrix = {"phase": "layers", "row": None, "cell": None,
                            "done": 0, "total": total}
        self._emit_log(f"{job['label']}…")
        self._set_dot("busy", "Refreshing the ArcGIS layers…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": job["label"] + "…", "workers": 1})
        ArcgisLayerRefreshWorker(layers, self._gated_queue(), self.cancel_event).start()
        return True

    def _dispatch_arcgis_probe_job(self, job):
        with self._lock:
            self._matrix = {"phase": "probe", "row": None, "cell": None,
                            "done": 0, "total": 1}
        self._emit_log(f"{job['label']}…")
        self._set_dot("busy", "Checking ArcGIS Pro…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": job["label"] + "…", "workers": 1})
        ArcgisProProbeWorker(self._gated_queue(), self.cancel_event).start()
        return True

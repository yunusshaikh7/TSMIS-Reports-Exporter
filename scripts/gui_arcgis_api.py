"""GuiArcgisMixin — the ArcGIS tab's endpoints (v0.29.0; reports sub-tab v0.39.0).

The tab owns everything built FROM the ArcGIS layer library, in two sub-tabs:

  * **Clean Road** — the layer-library status (the agreed 40-layer manifest vs
    what's staged), the CA HIGHWAYS overlay build (`consolidate_clean_highway`),
    and the ArcGIS-vs-TSN comparison (`compare_clean_highway_tsn`).
    Intersections and Ramps surface as staged skeletons only.
  * **Reports vs layers** — the same layers rendered as a TSMIS REPORT and
    diffed against the app's own export of it. Highway Detail is the first:
    `arcgis_report_highway_detail` projects the CA HIGHWAYS build onto the
    report's 34 columns, `compare_highway_detail_arcgis` diffs that against a
    chosen export day's consolidated workbook. Unlike vs-TSN this is TSMIS vs
    TSMIS, so the two sides SHOULD agree — which is why the endpoints surface
    the build's as-of date beside the export day rather than hiding a mismatch
    that would make the comparison measure network change, not correctness.

Both comparisons ride the shared `_begin_compare` claim → save-dialog → launch
tail like every other comparison (formulas + values twins included).
Composition only — every `self._*` it touches lives on GuiApi.
"""
import functools
import logging
from pathlib import Path

from gui_endpoint import _api_method
from gui_worker import ConsolidateWorker

ui_log = logging.getLogger("tsmis.ui")


class GuiArcgisMixin:
    @_api_method
    def arcgis_status(self):
        """The ArcGIS tab's one status payload: library stock vs the 40-layer
        manifest, the CA HIGHWAYS build/TSN readiness, and the staged
        skeletons. Pure filesystem; no task lock, no browser."""
        import clean_road_layers as crl
        import consolidate_clean_highway as cch
        import consolidation_meta
        import tsn_library

        lib = crl.inventory()
        highway_missing = [n for n in cch.HIGHWAY_LAYERS
                           if n not in lib["present"]]
        built = cch.OUT_PATH
        built_info = {"exists": built.is_file(), "path": str(built)}
        if built_info["exists"]:
            record = consolidation_meta.read_outcome(built)
            if record is not None and record.current:
                built_info["completion"] = record.completion
            built_info.update(self._arcgis_built_marker(built))
        default_asof = None
        tsn_raw = False
        try:
            raw_root = Path(tsn_library.raw_dir("clean_highway"))
            tsn_raw = any(p.is_file() and not p.name.startswith("~$")
                          for p in raw_root.glob("*.xlsx"))
            if tsn_raw:
                default_asof = cch.resolve_default_asof().isoformat()
        except (OSError, ValueError) as e:
            ui_log.info("arcgis: default as-of unavailable (%s: %s)",
                        type(e).__name__, e)
        return {
            "root": str(crl.root()),
            "expected": len(crl.EXPECTED_LAYERS),
            "staged": len(lib["present"]),
            "missing": lib["missing"],
            "unknown": lib["unknown"],
            "index_present": lib["index"] is not None,
            "highway": {
                "layers_ok": not highway_missing,
                "missing": highway_missing,
                "built": built_info,
                "tsn_raw": tsn_raw,
                "default_asof": default_asof,
            },
        }

    @staticmethod
    def _arcgis_built_marker(path):
        """The built workbook's own as-of/build facts from its marker sheet
        (absent/unreadable facts read as unknown, never invented)."""
        import clean_highway_columns as chc
        try:
            from openpyxl import load_workbook
            wb = load_workbook(path, read_only=True, data_only=True)
            try:
                if chc.ARC_MARKER_SHEET not in wb.sheetnames:
                    return {}
                facts = {}
                for r in wb[chc.ARC_MARKER_SHEET].iter_rows(values_only=True):
                    if not r or r[0] is None:
                        continue
                    key = str(r[0]).strip()
                    if key == "As-of date":
                        facts["asof"] = str(r[1])
                    elif key == "Build version":
                        facts["build_version"] = r[1]
                return facts
            finally:
                wb.close()
        except Exception as e:      # silent-ok: a status card probe; an unreadable marker shows as unknown, the build/compare paths still gate hard
            ui_log.info("arcgis: built marker unreadable (%s: %s)",
                        type(e).__name__, e)
            return {}

    # ------------------------------------------------------------------ #
    # Reports vs layers (v0.39.0) — the same library rendered as a report
    # ------------------------------------------------------------------ #
    @_api_method
    def arcgis_report_status(self):
        """The Reports sub-tab's one status payload: the report's OWN source
        table (with its as-of date), our built report, and the export days
        available as the TSMIS side. Pure filesystem; no task lock.

        `source` is this report's own build (v0.39.2), not the Clean Road
        workbook — the report no longer reads that. The key name is unchanged so
        the sub-tab's status card keeps working."""
        import arcgis_report_highway_detail as ah
        import consolidate_highway_detail as chd
        import paths

        src_path = ah.OUT_DIR / ah.SOURCE_TABLE
        source = {"exists": src_path.is_file(), "path": str(src_path)}
        if source["exists"]:
            source.update(self._arcgis_built_marker(src_path))
        built = {"exists": ah.OUT_PATH.is_file(), "path": str(ah.OUT_PATH)}
        if built["exists"]:
            try:
                built.update(ah.report_facts(ah.OUT_PATH))
            except Exception as e:      # silent-ok: a status-card probe; unreadable facts read as unknown and the build/compare paths still gate hard
                ui_log.info("arcgis report: marker unreadable (%s: %s)",
                            type(e).__name__, e)
        days = []
        for day in paths.list_output_days_for_report(chd.SUBDIR):
            p = chd.out_path_for(day)
            if p and Path(p).is_file():
                days.append({"day": day, "path": str(p)})
        return {
            "reports": [{"key": "highway_detail", "label": "Highway Detail"}],
            "source": source,
            "built": built,
            "days": days,
            "out_dir": str(ah.OUT_DIR),
        }

    @_api_method
    def start_arcgis_report_build(self, asof=None):
        """Build Highway Detail FROM THE LAYERS (v0.39.2 — it no longer needs,
        or reads, the Clean Road build). `asof` is the reconstruction date:
        set it to the export day you mean to compare against, or the comparison
        measures network change instead of correctness. Empty resolves the same
        way the Clean Road build's does, from the staged TSN extract.

        The destination is app-owned (output/arcgis_reports) and a rebuild
        replaces it by design."""
        import arcgis_report_highway_detail as ah
        import clean_road_layers as crl

        missing = crl.inventory().get("missing") or []
        if missing:
            return {"error": "The ArcGIS layer library is missing "
                             f"{len(missing)} layer(s) this report needs — "
                             "stock them and try again."}
        asof = (asof or "").strip() or None
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        self._emit_log(f"Starting ArcGIS report build: {ah.REPORT_NAME}")
        self._set_dot("busy", "Building the report from the layers…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Building Highway Detail from the ArcGIS layers"
                             + (f" as of {asof}…" if asof else "…")})
        self._push_state()
        ConsolidateWorker(functools.partial(ah.consolidate, asof=asof),
                          self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    @_api_method
    def start_arcgis_report_compare(self, day=None, want_formulas=True,
                                    want_values=True):
        """Compare our ArcGIS-built Highway Detail against the consolidated
        TSMIS export for `day`. The save dialog owns the destination."""
        import arcgis_report_highway_detail as ah
        import compare_highway_detail_arcgis as cmp_arc
        import consolidate_highway_detail as chd
        import paths

        if not ah.OUT_PATH.is_file():
            return {"error": "Build the Highway Detail report from the layers "
                             "first — the comparison reads it as the ArcGIS side."}
        day = (day or "").strip()
        if day not in paths.list_output_days_for_report(chd.SUBDIR):
            return {"error": "Pick an export day that has a Highway Detail export."}
        tsmis = chd.out_path_for(day)
        if not (tsmis and Path(tsmis).is_file()):
            return {"error": f"{day} has no CONSOLIDATED Highway Detail workbook "
                             "yet — consolidate that day first (Consolidate tab)."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live "
                             "formulas)."}

        def build(out_path, events=None, confirm_overwrite=None, day=None):
            return cmp_arc.compare(str(ah.OUT_PATH), str(tsmis), out_path,
                                   events=events,
                                   confirm_overwrite=confirm_overwrite, mode=mode)

        return self._begin_compare(
            f"Highway Detail — ArcGIS vs TSMIS {day}", mode,
            paths.arcgis_comparisons_dir(),
            lambda: cmp_arc.suggest_name(ah.OUT_PATH), build,
            source_paths=(ah.OUT_PATH, Path(tsmis)))

    @_api_method
    def open_arcgis_reports_folder(self):
        import arcgis_report_highway_detail as ah
        ah.OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._open_folder(ah.OUT_DIR)
        return {"ok": True}

    @_api_method
    def open_arcgis_layers_folder(self):
        import arcgis_layers
        arcgis_layers.ensure_layout()
        self._open_folder(arcgis_layers.root())
        return {"ok": True}

    @_api_method
    def open_arcgis_output_folder(self):
        import consolidate_clean_highway as cch
        cch.OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._open_folder(cch.OUT_DIR)
        return {"ok": True}

    @_api_method
    def start_arcgis_build(self, asof=None):
        """Build the CA HIGHWAYS clean-road workbook from the layer library.
        `asof` is an optional ISO date; empty resolves to the staged TSN
        extract's own date. The destination is app-owned
        (output/arcgis_cleanroad) and a rebuild replaces it by design."""
        import consolidate_clean_highway as cch

        asof = (asof or "").strip() or None
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        label = "Clean Road Highway (ArcGIS)"
        self._emit_log(f"Starting ArcGIS build: {label}"
                       + (f"   ·   as of {asof}" if asof else ""))
        self._set_dot("busy", "Building from ArcGIS layers…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Building Clean Road Highway from the ArcGIS "
                             "layers…"})
        self._push_state()

        def build(events=None, confirm_overwrite=None, day=None):
            return cch.consolidate(events=events,
                                   confirm_overwrite=confirm_overwrite,
                                   day=day, asof=asof)

        ConsolidateWorker(build, self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    @_api_method
    def start_arcgis_compare(self, want_formulas=True, want_values=True):
        """Compare the built CA HIGHWAYS workbook against the TSN clean-road
        extract. The TSN library normalization builds (or reuses) inside the
        worker; the save dialog owns the destination + overwrite question."""
        import compare_clean_highway_tsn as cht
        import consolidate_clean_highway as cch
        import paths
        import tsn_library

        built = cch.OUT_PATH
        if not built.is_file():
            return {"error": "Build the Clean Road Highway workbook first — "
                             "the comparison reads it as the ArcGIS side."}
        try:
            raw_root = Path(tsn_library.raw_dir("clean_highway"))
            has_raw = any(p.is_file() and not p.name.startswith("~$")
                          for p in raw_root.glob("*.xlsx"))
        except OSError:  # silent-ok: a pure presence probe — an unreadable raw folder reads as not-staged and the endpoint returns the stage-it-first message
            has_raw = False
        if not has_raw:
            return {"error": "Stage the TSN CA HIGHWAYS extract in the TSN "
                             "library first (Settings → TSN reports → Clean "
                             "Road Highway)."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live "
                             "formulas)."}
        tsn_path = Path(tsn_library.consolidated_path("clean_highway"))

        def build(out_path, events=None, confirm_overwrite=None, day=None):
            res = tsn_library.build_consolidated(
                "clean_highway", events=events, confirm_overwrite=lambda p: True)
            if res.status != "ok":
                return res
            return cht.compare(built, tsn_path, out_path, events=events,
                               confirm_overwrite=confirm_overwrite, mode=mode)

        sources = tuple(p for p in (built, tsn_path) if p.is_file())
        # M2-E: auto-save to the standardized output/comparisons/arcgis/ (beside the
        # manual folder) instead of the ArcGIS build output dir; "Save elsewhere…" stays.
        return self._begin_compare(
            "Clean Road Highway — ArcGIS vs TSN", mode, paths.arcgis_comparisons_dir(),
            lambda: cht.suggest_name(built), build, source_paths=sources)

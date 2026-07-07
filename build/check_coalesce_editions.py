"""Golden check for dual-edition coalescing (v0.19.2).

When both editions of one on-site report are selected (Excel + the print-layout
PDF, same data_value), the export must GENERATE the report ONCE per route and save
BOTH files off that single render — never generate it twice. Locks:

  * grouping   — _coalesce_groups pairs same-data_value specs, keeps solos, order;
  * ordering   — the page-rebuilding (PDF Print) save runs LAST, after the
                 DOM-preserving Export-button save (else the Export button is gone);
  * one gen    — _process_route_combined clicks Generate ONCE, then saves every
                 edition; the shared outcome lands in each edition's result;
  * empty/fail — an empty route saves nothing and records empty for both; a site
                 error records failed for both;
  * guards     — run_export_combined rejects <2 editions or a data_value mismatch.

Stdlib only; no browser, no network. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_coalesce_editions.py
"""
from pathlib import Path

from _checklib import Checker, FakeEvents, patch, scripts_path, temp_dir

scripts_path()

import exporter
import gui_worker_export as gwe
from events import RunResult
from exporter import ReportSpec, save_highway_log_pdf, save_via_export_button

c = Checker()


class _Ev(FakeEvents):
    """FakeEvents + the sink methods the engine's per-route path calls."""
    worker_no = 0

    def __init__(self):
        super().__init__()
        self.routes = []

    def on_status(self, *_a):
        pass

    def on_route(self, route, status):
        self.routes.append((route, status))


class _Loc:
    def __init__(self, page, kind):
        self.page, self.kind = page, kind

    def select_option(self, v):
        self.page.route_selected = v

    def click(self):
        if self.kind == "generate":
            self.page.generate_clicks += 1


class _Page:
    """A page that only records what the generation step does to it."""
    def __init__(self):
        self.generate_clicks = 0
        self.route_selected = None

    def get_by_label(self, _label, exact=False):
        return _Loc(self, "route")

    def get_by_role(self, _role, name=None):
        return _Loc(self, "generate" if name == "Generate" else "other")

    def wait_for_timeout(self, _ms):
        pass


def _spec(subdir, save, *, empty=False, data_value="highway_log", label="Highway Log"):
    return ReportSpec(
        label=label, subdir=subdir, data_value=data_value,
        filename=lambda r, _s=subdir: f"{_s}_{r}." + ("pdf" if _s.endswith("pdf") else "xlsx"),
        wait_js=lambda r: "() => true",
        is_empty=lambda _p, _e=empty: _e,
        save=save)


def _recording_save(tag, log):
    def _save(page, out_path, timeout_ms=None):
        log.append(tag)
        Path(out_path).write_bytes(b"PK\x03\x04d" if str(out_path).endswith(".xlsx") else b"%PDFd")
    return _save


def test_grouping():
    print("_coalesce_groups pairs same-data_value editions, keeps order:")
    excel = _spec("highway_log", save_via_export_button)
    pdf = _spec("highway_log_pdf", save_highway_log_pdf)
    ramp = _spec("ramp_detail", save_via_export_button, data_value="Ramp_Detail",
                 label="Ramp Detail")
    # Editions not adjacent in the selection still coalesce (grouped by data_value).
    groups = gwe._coalesce_groups([excel, ramp, pdf])
    c.check("solo report stays a group of one",
            [len(g) for g in groups] == [2, 1] and groups[1][0].subdir == "ramp_detail",
            f"groups={[[s.subdir for s in g] for g in groups]}")
    c.check("both HL editions coalesce into one group",
            {s.subdir for s in groups[0]} == {"highway_log", "highway_log_pdf"})
    c.check("group label notes both editions",
            gwe._group_label(groups[0]) == "Highway Log (Excel + PDF)"
            and gwe._group_label(groups[1]) == "Ramp Detail")
    c.check("a lone edition is NOT coalesced (group of one)",
            [len(g) for g in gwe._coalesce_groups([excel, ramp])] == [1, 1])


def test_save_order():
    print("the page-rebuilding (PDF) save is ordered LAST:")
    c.check("save_via_export_button does NOT rebuild the page",
            not exporter._save_rebuilds_page(_spec("highway_log", save_via_export_button)))
    c.check("the PDF Print-capture saves DO rebuild the page",
            exporter._save_rebuilds_page(_spec("highway_log_pdf", save_highway_log_pdf)))
    # The exact sort run_export_combined uses (PDF spec given first, must sort last).
    specs = [_spec("highway_log_pdf", save_highway_log_pdf),
             _spec("highway_log", save_via_export_button)]
    order = sorted(range(len(specs)), key=lambda i: exporter._save_rebuilds_page(specs[i]))
    c.check("Excel sorts before PDF regardless of selection order",
            [specs[i].subdir for i in order] == ["highway_log", "highway_log_pdf"])


def _run_route(base_spec, targets, results, *, err=None):
    """Drive _process_route_combined once with a faked generation + saves."""
    ev = _Ev()
    page = _Page()
    with patch(exporter, "_ensure_report_armed", lambda *a, **k: None), \
         patch(exporter, "wait_with_skip_option", lambda *a, **k: True), \
         patch(exporter, "_build_wait_condition", lambda spec, route: "() => true"), \
         patch(exporter, "report_error_text", lambda _p: err), \
         patch(exporter, "maybe_screenshot", lambda *a, **k: None), \
         patch(exporter, "_capture_failure", lambda *a, **k: None), \
         patch(exporter, "_recover_or_stop", lambda *a, **k: True):
        keep = exporter._process_route_combined(
            page, base_spec, "001", "[1/1] Route 001:", targets, ev, results, 60000)
    return ev, page, keep


def test_one_generation_saves_both():
    print("_process_route_combined: ONE generate, BOTH editions saved in order:")
    with temp_dir("tsmis_coal_") as tmp:
        log = []
        excel = _spec("highway_log", _recording_save("excel", log))
        pdf = _spec("highway_log_pdf", _recording_save("pdf", log))
        targets = [(excel, tmp / "hl.xlsx"), (pdf, tmp / "hl.pdf")]   # pre-ordered: Excel, PDF
        results = [RunResult(), RunResult()]
        ev, page, keep = _run_route(excel, targets, results)
        c.check("Generate clicked exactly ONCE for both editions",
                page.generate_clicks == 1, f"clicks={page.generate_clicks}")
        c.check("both editions saved, Export-button save BEFORE the PDF rebuild",
                log == ["excel", "pdf"], f"order={log}")
        c.check("both files written to disk",
                (tmp / "hl.xlsx").exists() and (tmp / "hl.pdf").exists())
        c.check("the shared 'saved' outcome landed in EACH edition's result",
                results[0].saved == 1 and results[1].saved == 1)
        c.check("the UI was notified ONCE (one unit of progress)",
                ev.routes == [("001", "saved")], f"routes={ev.routes}")
        c.check("run continues", keep is True)


def test_empty_and_error():
    print("empty route saves nothing (both empty); a site error fails both:")
    with temp_dir("tsmis_coal2_") as tmp:
        log = []
        excel = _spec("highway_log", _recording_save("excel", log), empty=True)
        pdf = _spec("highway_log_pdf", _recording_save("pdf", log), empty=True)
        results = [RunResult(), RunResult()]
        _run_route(excel, [(excel, tmp / "e.xlsx"), (pdf, tmp / "e.pdf")], results)
        c.check("empty route: NO saves, both editions recorded empty",
                log == [] and results[0].empty == ["001"] and results[1].empty == ["001"])

        log2, results2 = [], [RunResult(), RunResult()]
        ex2 = _spec("highway_log", _recording_save("excel", log2))
        pd2 = _spec("highway_log_pdf", _recording_save("pdf", log2))
        _run_route(ex2, [(ex2, tmp / "x.xlsx"), (pd2, tmp / "x.pdf")], results2, err="TSMIS boom")
        c.check("a site error fails BOTH editions (no partial save)",
                results2[0].failed == ["001"] and results2[1].failed == ["001"] and log2 == [])


def test_guards():
    print("run_export_combined rejects bad edition sets:")
    excel = _spec("highway_log", save_via_export_button)
    c.check("a single edition is rejected (use run_export)",
            _raises(lambda: exporter.run_export_combined([excel])))
    mixed = _spec("intersection_detail", save_via_export_button, data_value="intersection_detail")
    c.check("editions with different data_value are rejected",
            _raises(lambda: exporter.run_export_combined([excel, mixed])))


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("dual-edition coalescing (v0.19.2):")
    test_grouping()
    test_save_order()
    test_one_generation_saves_both()
    test_empty_and_error()
    test_guards()
    raise SystemExit(c.summary())

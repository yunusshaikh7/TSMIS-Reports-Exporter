"""Golden check for the website-source capture (v0.26.0): the pure helpers —
traversal-proof flat filenames, the same-origin filter, the manifest writer —
and the gui_api endpoint wiring (worker stubbed; no browser, no network).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_site_capture.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_api
import gui_settings_api
import site_capture

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


class _FakeWorker:
    last = None

    def __init__(self, *args, **kwargs):
        _FakeWorker.last = (args, kwargs)

    def start(self):
        self.started = True


def main():
    print("filenames — flat, readable, traversal-proof:")
    sn = site_capture._safe_name
    check("path segments keep provenance via '__'",
          sn("https://x/a/Scripts/customreport.js") == "a__Scripts__customreport.js")
    check("root/empty paths get a name",
          sn("https://x/") == "index" and sn("https://x") == "index")
    check("traversal + separators neutralized",
          "/" not in sn("https://x/../../etc/passwd")
          and "\\" not in sn("https://x/a%5C..%5Cb")
          and ".." not in sn("https://x/../../etc/passwd").replace("__", "_"))
    check("a query string suffixes instead of colliding",
          sn("https://x/a.js?v=1") != sn("https://x/a.js")
          and sn("https://x/a.js?v=1") != sn("https://x/a.js?v=2"))
    check("length capped", len(sn("https://x/" + "a" * 500)) <= 120)

    print("same-origin filter:")
    so = site_capture._same_origin
    page = "https://tsmis.example.gov/reports/page.aspx"
    check("same host+scheme accepted",
          so("https://tsmis.example.gov/Scripts/a.js", page))
    check("third-party / scheme / subdomain rejected",
          not so("https://cdn.other.com/a.js", page)
          and not so("http://tsmis.example.gov/a.js", page)
          and not so("https://evil.tsmis.example.gov.attacker.io/a.js", page))

    print("manifest writer:")
    d = Path(tempfile.mkdtemp(prefix="tsmis_cap_"))
    try:
        site_capture._write_manifest(d, "https://x/p", "ssor", "prod",
                                     [("page (rendered DOM).html", 10)],
                                     [("https://x/a.js", "HTTP 404")],
                                     note="INCOMPLETE — TimeoutError")
        text = (d / "_capture_info.txt").read_text(encoding="utf-8")
        check("manifest carries site, files, failures, the note, and the "
              "local-only wording",
              "ssor-prod" in text and "page (rendered DOM).html" in text
              and "HTTP 404" in text and "INCOMPLETE" in text
              and "Caltrans-internal" in text)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("gui_api endpoint wiring (worker stubbed):")
    saved = gui_settings_api.ConsolidateWorker
    gui_settings_api.ConsolidateWorker = _FakeWorker
    try:
        a = gui_api.GuiApi()
        r = a.capture_site_source()
        check("capture claims the single-task slot and starts the worker",
              r.get("ok") is True and a._task == "consolidate"
              and isinstance(_FakeWorker.last, tuple))
        check("a second call while busy is refused",
              bool(a.capture_site_source().get("error")))
        a._end_task()
        opened = []
        a._open_folder = lambda p: opened.append(Path(p))
        check("open-captures-folder opens the capture root",
              a.open_site_captures_folder().get("ok") is True
              and opened[-1].name == site_capture.CAPTURE_DIRNAME)
    finally:
        gui_settings_api.ConsolidateWorker = saved

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL SITE-CAPTURE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

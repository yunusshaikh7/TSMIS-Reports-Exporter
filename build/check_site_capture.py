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

    print("clean names — the site's own file names, collision-safe:")
    cn = site_capture._clean_name
    taken = {}
    n1 = cn("https://x/shared.js?v=2026-08-19%2009%3A35", taken); taken[n1] = "https://x/shared.js?v=2026-08-19%2009%3A35"
    check("basename, cache-buster query dropped", n1 == "shared.js")
    check("the same URL keeps its name", cn("https://x/shared.js?v=2026-08-19%2009%3A35", taken) == "shared.js")
    n2 = cn("https://x/Scripts/shared.js", taken)
    check("a DIFFERENT url wanting a taken name falls back to the flattened spelling",
          n2 != "shared.js" and n2 == site_capture._safe_name("https://x/Scripts/shared.js"))
    check("traversal neutralized",
          "/" not in cn("https://x/../../etc/passwd", {}) and ".." not in cn("https://x/a/..%2F..", {}))

    print("reference discovery — relative names in page text and scripts:")
    fr = site_capture._find_refs
    page = "https://tsmis-dev.dot.ca.gov/index.html?env=dev&src=ars"
    html = ("<script src=\"https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js\"></script>"
            "<link rel=\"stylesheet\" href=\"styles.css\"><img src=\"caltranslogo.png\">"
            "document.write('<scr'+'ipt src=\"config.js' + _v + '\"></scr'+'ipt>' +"
            "'<scr'+'ipt src=\"clean_highway.js' + _v + '\"></scr'+'ipt>');")
    refs = fr(html, page)
    names = [u.rsplit("/", 1)[-1] for u in refs]
    check("finds the stylesheet, image and document.write'd modules",
          names == ["styles.css", "caltranslogo.png", "config.js", "clean_highway.js"])
    check("resolves against the page (same origin, query-free)",
          refs[0] == "https://tsmis-dev.dot.ca.gov/styles.css")
    check("an absolute CDN URL's own file name is NOT a site reference",
          not any("xlsx" in u for u in refs))
    js = ("// See DEBUG.md for the reference. const u = `${window.location.origin}/index.html`;"
          " fetch(`${CONFIG.mapServiceUrl}/85/query?f=json`); data.error.message; /\\.js$/.test(x);"
          " const rows = results.map(r => r); const d = await resp.json(); codes.map (c => c);"
          " const s = 'shared.js'; const s2 = 'shared.js'; //# sourceMappingURL=shared.js.map")
    refs2 = [u.rsplit("/", 1)[-1] for u in fr(js, page)]
    check("scripts: a markdown note, root-relative index.html and a source map found; "
          "JS syntax (`f=json`, `.message`, a `\\.js` regex, `.map(`/`.json(` calls) "
          "ignored; duplicates collapsed",
          refs2 == ["DEBUG.md", "index.html", "shared.js", "shared.js.map"])
    check("canonical identity drops the cache-buster",
          site_capture._canonical("https://x/a.js?v=1#f") == site_capture._canonical("https://x/a.js"))

    print("build date + manifest:")
    check("BUILD_DATE parsed from the page",
          site_capture._build_date("<script>const BUILD_DATE = '2026-08-19 09:35';</script>")
          == "2026-08-19 09:35" and site_capture._build_date("<p>no stamp</p>") is None)
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
        site_capture._write_manifest(d, "https://x/p", "ssor", "dev",
                                     [("shared.js", 10, "ab" * 32)], [],
                                     build_date="2026-08-19 09:35",
                                     config={"env": "dev", "src": "ars", "service": "https://x/M"},
                                     foreign=["https://cdn.sheetjs.com/x.js"])
        text = (d / "_capture_info.txt").read_text(encoding="utf-8")
        check("manifest carries the build date, CONFIG, a sha256 per file and the "
              "third-party list",
              "2026-08-19 09:35" in text and "env=dev src=ars" in text
              and "sha256=" + "ab" * 32 in text and "cdn.sheetjs.com" in text)
        # evidence.py is the ONE zip writer in the app (check_evidence_bundle pins
        # it); the capture hands over a FOLDER, never an archive of internal source.
        src_text = (ROOT / "scripts" / "site_capture.py").read_text(encoding="utf-8")
        check("the capture writes no archive (zipfile is not imported)",
              "zipfile" not in src_text)
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

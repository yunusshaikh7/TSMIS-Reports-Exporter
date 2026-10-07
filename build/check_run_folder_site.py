"""Golden check for v0.49.0: every export run folder records the TSMIS site it
came from ('2026-10-07 ssor-prod dev-site'). Reports wait on the dev site until
they are approved and then move to the main site, so the same source and
environment can be exported from either, and the two are different evidence: a
dev-site export and a main-site export of the same day must never share a folder,
and nothing that reads the folders may pass one for the other. The folders from
before the site was recorded ('2026-10-02 ssor-prod', and the pre-v0.10 bare
dates) must stay readable.

Driven through the shipped entry points with real folders on disk (no browser,
no site): the host classification, the name / parse round trip, the readers'
precedence (own site > not recorded > bare date; never the other site), the
matrices' day pickers, labels and comparison names, a REAL run_export into the
default dated layout from the dev site and then the main site, the
between-folders compare's side labels, and the evidence-path budget at the
work-PC install depth (the tag lengthens every comparison path).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_run_folder_site.py
"""
import csv
import threading
from pathlib import Path

from _checklib import Checker, patch, pinned_site, scripts_path, temp_dir

scripts_path()

import artifact_store
import baseline_matrix
import compare_env
import day_matrix
import exporter
import matrix
import paths
import run_report
import site_target
import visual_evidence
from events import Events
from exporter import ReportSpec

c = Checker()

DAY = "2026-10-07"
MAIN_URL = site_target.default_site_url("ssor", "prod")
DEV_URL = site_target.dev_site_url("ssor", "prod")
XLSX_HEAD = b"PK\x03\x04data"          # what _head_is_complete accepts for .xlsx


def _export(folder, subdir="ramp_detail"):
    """Plant one real-looking per-route export under `folder`/`subdir`."""
    p = folder / subdir / f"{folder.name} tsar_ramp_detail_route_101.xlsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(XLSX_HEAD)
    return p


def test_host_kind():
    print("site_target.host_kind — which TSMIS host an address is on:")
    c.check("the built-in address is the main site",
            site_target.host_kind(MAIN_URL) == "main")
    c.check("the dev-site preset address is the dev site",
            site_target.host_kind(DEV_URL) == "dev")
    c.check("any other host (a Settings custom address) reads as other",
            site_target.host_kind(
                "https://tsmis-uat.dot.ca.gov/index.html?env=prod&src=ssor") == "other")
    c.check("an unparseable address never raises (reads as other)",
            site_target.host_kind(None) == "other"
            and site_target.host_kind("") == "other")
    with pinned_site("dev"):
        c.check("host_kind_for follows the Settings address (dev preset on)",
                site_target.host_kind_for("ars", "test") == "dev")
        c.check("get_url and combo_url agree with it",
                site_target.host_kind(site_target.combo_url("ssor", "prod")) == "dev")
    with pinned_site("main"):
        c.check("host_kind_for with no custom address is the main site",
                site_target.host_kind_for("ssor", "prod") == "main")


def test_names_round_trip():
    print("run-folder names: the site tag round-trips; junk never parses:")
    ok = True
    for host in site_target.HOST_KINDS:
        name = paths.run_folder_name("ssor", "prod", DAY, host)
        ok = ok and name == f"{DAY} ssor-prod {host}-site" \
            and paths.parse_run_folder(name) == (DAY, "ssor", "prod") \
            and paths.run_folder_host(name) == host
    c.check("main / dev / other tags build, parse and read back", ok)
    c.check("an untagged v0.10-v0.48 folder parses, site not recorded",
            paths.parse_run_folder(f"{DAY} ssor-prod") == (DAY, "ssor", "prod")
            and paths.run_folder_host(f"{DAY} ssor-prod") is None)
    c.check("a pre-v0.10 bare date still reads as ssor-prod, site not recorded",
            paths.parse_run_folder(DAY) == (DAY, "ssor", "prod")
            and paths.run_folder_host(DAY) is None)
    junk = [f"{DAY} ssor-prod dev", f"{DAY} ssor-prod foo-site",
            f"{DAY} ssor-prod dev-site extra", "2026-02-31 ssor-prod dev-site",
            f"{DAY} ssor-prod  dev-site", f"{DAY}  ssor-prod dev-site"]
    c.check("an unknown tag, a missing '-site', trailing text or an impossible "
            "date is not a run folder",
            all(paths.parse_run_folder(n) is None and paths.run_folder_host(n) is None
                for n in junk))
    for host, tag in (("main", "main-site"), ("dev", "dev-site"), ("other", "other-site")):
        with pinned_site(host):
            c.check(f"an export with the {host} address writes '<day> ssor-prod {tag}'",
                    paths.output_run_dir("ssor", "prod", DAY).name
                    == f"{DAY} ssor-prod {tag}")
    with temp_dir("tsmis_rfs_names_") as tmp:
        run = tmp / f"{DAY} ssor-prod dev-site"
        sub = run / "highway_log"
        sub.mkdir(parents=True)
        c.check("per-route files carry the full tagged run name",
                paths.resolve_route_file(sub, "highway_log_route_3.xlsx").name
                == f"{DAY} ssor-prod dev-site highway_log_route_3.xlsx")
    c.check("the consolidated workbook is stamped with it too",
            paths.stamped_consolidated_filename(
                "highway_log_consolidated.xlsx", f"{DAY} ssor-prod dev-site")
            == f"highway_log_consolidated {DAY} ssor-prod dev-site.xlsx")


def test_reader_precedence():
    print("readers: own site > not recorded > bare date, never the other site:")
    with temp_dir("tsmis_rfs_read_") as tmp, patch(paths, "OUTPUT_ROOT", tmp):
        for name in (f"{DAY} ssor-prod dev-site", f"{DAY} ssor-prod main-site",
                     "2026-10-02 ssor-prod", "2026-06-11",
                     "2026-09-25 ssor-prod main-site", "2026-09-24 ars-prod dev-site"):
            (tmp / name).mkdir()
        dsd = paths.day_source_dir
        c.check("the same day on two sites resolves to each site's own folder",
                dsd(DAY, "ssor-prod", "dev").name == f"{DAY} ssor-prod dev-site"
                and dsd(DAY, "ssor-prod", "main").name == f"{DAY} ssor-prod main-site")
        c.check("a folder from before the site was recorded reads from either site",
                dsd("2026-10-02", "ssor-prod", "dev").name == "2026-10-02 ssor-prod"
                and dsd("2026-10-02", "ssor-prod", "main").name == "2026-10-02 ssor-prod")
        c.check("a pre-v0.10 bare date still resolves (CMP-AUD-092)",
                dsd("2026-06-11", "ssor-prod", "dev").name == "2026-06-11")
        other = dsd("2026-09-25", "ssor-prod", "dev")
        c.check("a main-site export is NEVER read as the dev site's",
                other.name == "2026-09-25 ssor-prod dev-site" and not other.exists())
        with pinned_site("dev"):
            c.check("no host given -> the host the source points at now",
                    dsd(DAY, "ssor-prod").name == f"{DAY} ssor-prod dev-site")
            c.check("the labels: tagged, unrecorded, and the bare date's old label",
                    paths.day_run_label(DAY, "ssor-prod") == f"{DAY} ssor-prod dev-site"
                    and paths.day_run_label("2026-10-02", "ssor-prod")
                    == "2026-10-02 ssor-prod"
                    and paths.day_run_label("2026-06-11", "ssor-prod")
                    == "2026-06-11 ssor-prod")
            c.check("a day with no export labels as the folder its export would create",
                    paths.day_run_label("2026-11-01", "ssor-prod")
                    == "2026-11-01 ssor-prod dev-site")
            c.check("days offered for the dev site: its own + unrecorded, newest first",
                    [d for d, _f in paths.run_days_for("ssor-prod")]
                    == [DAY, "2026-10-02", "2026-06-11"])
            c.check("each offered day carries exactly the folder the cells read",
                    all(f == dsd(d, "ssor-prod") for d, f in paths.run_days_for("ssor-prod")))
            c.check("another source's folders are never offered",
                    [d for d, _f in paths.run_days_for("ars-prod")] == ["2026-09-24"])
        with pinned_site("main"):
            c.check("days offered for the main site include its main-only day",
                    [d for d, _f in paths.run_days_for("ssor-prod")]
                    == [DAY, "2026-10-02", "2026-09-25", "2026-06-11"])
            c.check("and drop the dev-site-only day of another source",
                    paths.run_days_for("ars-prod") == [])
        for bad_date, bad_src in (("../2026-10-07", "ssor-prod"),
                                  (DAY, "ssor-prod/../x"), ("2026-99-99", "ssor-prod")):
            label = paths.day_run_label(bad_date, bad_src)
            c.check(f"a crafted column ({bad_date!r}, {bad_src!r}) never parses",
                    paths.parse_run_folder(label) is None, label)


def test_matrices():
    print("matrices: pickers, labels and comparison files follow the site:")
    with temp_dir("tsmis_rfs_mx_") as tmp, patch(paths, "OUTPUT_ROOT", tmp), \
            patch(day_matrix, "OUTPUT_ROOT", tmp), patch(baseline_matrix, "OUTPUT_ROOT", tmp):
        _export(tmp / f"{DAY} ssor-prod dev-site")
        _export(tmp / f"{DAY} ssor-prod main-site")
        _export(tmp / "2026-10-02 ssor-prod")
        _export(tmp / "2026-09-25 ssor-prod main-site")
        with pinned_site("dev"):
            days = day_matrix.available_days("ssor-prod")
            c.check("vs TSN picker (dev site): today + its own day + the unrecorded one",
                    days == [paths.today_str(), DAY, "2026-10-02"], str(days))
            c.check("vs Baseline picker (dev site): never the main-only day",
                    baseline_matrix.available_days("ssor-prod") == [DAY, "2026-10-02"])
            c.check("the per-day report tags read the same folders",
                    sorted(artifact_store.exported_subdirs_by_day(
                        "ssor-prod", ["ramp_detail"])) == ["2026-10-02", DAY])
            dev_out = day_matrix.day_out_path(DAY, "ssor-prod", "ramp_detail")
            c.check("the comparison folder and workbook name carry the site",
                    dev_out.parent.name == f"{DAY} ssor-prod dev-site"
                    and dev_out.name == f"ramp_detail_vs_tsn {DAY} ssor-prod dev-site.xlsx")
            c.check("an unrecorded day keeps its pre-v0.49 comparison name",
                    day_matrix.day_out_path("2026-10-02", "ssor-prod", "ramp_detail").name
                    == "ramp_detail_vs_tsn 2026-10-02 ssor-prod.xlsx")
            c.check("vs Baseline names follow the run folder too",
                    baseline_matrix.out_path(DAY, "ssor-prod", "ramp_detail",
                                             "day:2026-10-02").name
                    == f"ramp_detail_vs_2026-10-02 {DAY} ssor-prod dev-site.xlsx")
            c.check("day_hosts: the site each column's folder records",
                    matrix.day_hosts("ssor-prod", [DAY, "2026-10-02"])
                    == {DAY: "dev", "2026-10-02": None})
            opts = matrix.day_source_options(["ssor-prod", "ars-test"])
            c.check("the source picker names the site the matrix reads",
                    opts[0] == {"key": "ssor-prod", "label": "SSOR / Prod · dev site",
                                "host": "dev"}
                    and opts[1]["label"] == "ARS / Test · dev site")
            snap = day_matrix.day_matrix_snapshot("ssor-prod", [DAY, "2026-10-02"],
                                                  today=DAY)
            c.check("the vs-TSN snapshot carries day_hosts + labelled sources",
                    snap["day_hosts"] == {DAY: "dev", "2026-10-02": None}
                    and snap["sources"][0]["label"] == "SSOR / Prod · dev site")
            ramp = snap["cells"]["ramp_detail"]
            c.check("the cells read the dev-site and the unrecorded exports",
                    ramp[DAY]["export"]["present"] and ramp["2026-10-02"]["export"]["present"])
        with pinned_site("main"):
            main_out = day_matrix.day_out_path(DAY, "ssor-prod", "ramp_detail")
            c.check("the same day on the main site gets its OWN comparison file",
                    main_out != dev_out
                    and main_out.name == f"ramp_detail_vs_tsn {DAY} ssor-prod main-site.xlsx")
            c.check("vs Baseline picker (main site) offers the main-only day",
                    baseline_matrix.available_days("ssor-prod")
                    == [DAY, "2026-10-02", "2026-09-25"])
            c.check("result-cache keys differ per site for the same day",
                    day_matrix.day_folder_name(DAY, "ssor-prod")
                    == f"{DAY} ssor-prod main-site")


class _FakePage:
    def wait_for_timeout(self, _ms):
        pass


class _FakeBrowser:
    def close(self):
        pass


class _FakePW:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _spec():
    def save(_page, out_path, _timeout_ms=None):
        Path(out_path).write_bytes(XLSX_HEAD)

    return ReportSpec(
        label="Highway Log", subdir="highway_log", data_value="highway_log",
        filename=lambda r: f"highway_log_route_{r}.xlsx",
        wait_js=lambda r: "() => true", is_empty=lambda _p: False, save=save)


def test_shipped_export():
    print("run_export (shipped path, default dated layout): dev then main site:")
    today = paths.today_str()
    gen = []
    lock = threading.Lock()

    def fake_generate(_page, _spec, route, _prefix, _events, _timeout):
        with lock:
            gen.append(route)
        return "ready"

    with temp_dir("tsmis_rfs_exp_") as tmp:
        url = {"now": DEV_URL}
        ps = [
            patch(paths, "OUTPUT_ROOT", tmp),
            patch(run_report, "RUN_REPORTS_DIR", tmp / "run_reports"),
            patch(exporter, "FAILURES_DIR", tmp / "_failures"),
            patch(exporter, "sync_playwright", lambda: _FakePW()),
            patch(exporter, "new_authed_browser",
                  lambda _p, parallel=False: (_FakeBrowser(), None, _FakePage())),
            patch(exporter, "navigate_with_auth", lambda *_a, **_k: None),
            patch(exporter, "require_signed_in", lambda *_a, **_k: None),
            patch(exporter, "require_site_params", lambda *_a, **_k: None),
            patch(exporter, "preflight", lambda *_a, **_k: None),
            patch(exporter, "has_valid_auth", lambda: True),
            patch(exporter, "get_site", lambda: ("ssor", "prod")),
            patch(exporter, "get_url", lambda: url["now"]),
            patch(exporter, "_generate_route", fake_generate),
            patch(exporter, "maybe_screenshot", lambda *_a, **_k: None),
        ]
        ctx = []
        try:
            for p in ps:
                p.__enter__()
                ctx.append(p)
            r1 = exporter.run_export(_spec(), Events(), routes=["001", "002"])
            dev_dir = tmp / f"{today} ssor-prod dev-site" / "highway_log"
            c.check("the dev-site run lands in '<today> ssor-prod dev-site'",
                    Path(r1.output_dir) == dev_dir and r1.saved == 2,
                    f"output_dir={r1.output_dir}")
            c.check("its per-route files carry the tagged run name",
                    sorted(p.name for p in dev_dir.iterdir())
                    == [f"{today} ssor-prod dev-site highway_log_route_001.xlsx",
                        f"{today} ssor-prod dev-site highway_log_route_002.xlsx"])
            report = Path(r1.report_path or "")
            rows = list(csv.reader(report.open(encoding="utf-8"))) if report.is_file() else []
            c.check("the run report is tagged with the site in its name",
                    "_ssor-prod_dev-site_run_" in report.name, report.name)
            c.check("and says which site every route came from",
                    rows and rows[0] == ["Report", "Route", "Status", "Run At", "Site"]
                    and all(r[4] == f"dev site: {DEV_URL}" for r in rows[1:])
                    and len(rows) == 3, str(rows[:2]))

            url["now"] = MAIN_URL
            gen.clear()
            r2 = exporter.run_export(_spec(), Events(), routes=["001", "002"])
            main_dir = tmp / f"{today} ssor-prod main-site" / "highway_log"
            c.check("the same day from the main site gets its OWN folder",
                    Path(r2.output_dir) == main_dir and r2.saved == 2)
            c.check("it never resumes over the dev-site files (both routes pulled again)",
                    gen == ["001", "002"] and r2.exists == [], f"gen={gen}")
            c.check("the dev-site folder is untouched",
                    len(list(dev_dir.iterdir())) == 2)
            c.check("a combined run's default folders carry the site too",
                    exporter._combined_output_dirs([_spec()], None, "ssor", "prod", "dev")
                    == [tmp / f"{today} ssor-prod dev-site" / "highway_log"])
        finally:
            for p in reversed(ctx):
                p.__exit__(None, None, None)


def test_compare_labels():
    print("between-folders compare: the site names the two sides when it differs:")
    with temp_dir("tsmis_rfs_cmp_") as tmp:
        dev = tmp / f"{DAY} ssor-prod dev-site"
        main = tmp / f"{DAY} ssor-prod main-site"
        old = tmp / "2026-10-02 ssor-prod"
        c.check("dev vs main of the same source: 'SSOR-PROD DEV' / 'SSOR-PROD MAIN'",
                compare_env._side_labels(dev, main) == ("SSOR-PROD DEV", "SSOR-PROD MAIN"))
        c.check("the same when a report subfolder was picked",
                compare_env._side_labels(dev / "ramp_detail", main / "ramp_detail")
                == ("SSOR-PROD DEV", "SSOR-PROD MAIN"))
        c.check("same site, two days: the dates tell them apart",
                compare_env._side_labels(dev, tmp / "2026-10-01 ssor-prod dev-site")
                == ("SSOR-PROD 2026-10-07", "SSOR-PROD 2026-10-01"))
        c.check("a side whose site was never recorded falls back to the dates",
                compare_env._side_labels(dev, old)
                == ("SSOR-PROD 2026-10-07", "SSOR-PROD 2026-10-02"))
        c.check("the sheet-name cap keeps the site suffix",
                compare_env._cap_label("X" * 30 + " MAIN").endswith(" MAIN"))


# The managed work PC's output root, `C:\Users\<7-char id>\Downloads\Apps\TSMIS
# Exporter\output` — the depth check_comparison_path_limits measured (its 97-char
# tsn-by-day parent minus '\comparisons\tsn-by-day\2026-07-09 ssor-prod'). That
# machine has LongPathsEnabled=0, so every path must stay under 260.
_FIELD_OUTPUT_ROOT_LEN = 97 - len("\\comparisons\\tsn-by-day\\2026-07-09 ssor-prod")
# A generous evidence image name: the longest compared header among the
# evidence-capable reports is 22 characters once made filename-safe
# ('LB_OT_SH_Treated_LB_TR'); 30 leaves room for a longer one.
_IMAGE_NAME = f"{'H' * 30}_99_stacked.png"


def _deepest_evidence(path, root):
    """The deepest path an evidence render writes for one comparison workbook,
    measured at the field output root: an image in the published image folder,
    or in the temporary folder it renders into first (visual_evidence's mkdtemp
    prefix + 8 random characters), whichever is longer."""
    img_dir = visual_evidence.sibling_paths(path)[1]
    tmp_name = visual_evidence.IMAGE_TMP_PREFIX + "x" * 8
    parent = _FIELD_OUTPUT_ROOT_LEN + 1 + len(str(img_dir.parent.relative_to(root)))
    folder = max(len(img_dir.name), len(tmp_name))
    return parent + 1 + folder + 1 + len(_IMAGE_NAME)


def test_evidence_path_budget():
    print("evidence paths fit the work PC's 260-character limit with the longest tag:")
    with temp_dir("tsmis_rfs_len_") as tmp, patch(paths, "OUTPUT_ROOT", tmp), \
            patch(day_matrix, "OUTPUT_ROOT", tmp), patch(baseline_matrix, "OUTPUT_ROOT", tmp), \
            pinned_site("other"):
        tsn_rows = visual_evidence.rows()
        env_rows = [r for r in tsn_rows if visual_evidence.env_capable(r)]
        worst_tsn = max(_deepest_evidence(
            day_matrix.day_out_path("2026-07-09", src, row), tmp)
            for row in tsn_rows for src in ("ssor-prod", "ssor-test"))
        worst_bl = max(_deepest_evidence(
            baseline_matrix.out_path("2026-07-09", src, row, "day:2026-07-01"), tmp)
            for row in env_rows for src in ("ssor-prod", "ssor-test"))
        c.check("vs-TSN evidence (deepest image, 'other-site' tag) < 260",
                worst_tsn < 260, f"{worst_tsn} characters")
        c.check("vs-Baseline evidence (deepest image, 'other-site' tag) < 260",
                worst_bl < 260, f"{worst_bl} characters")
        print(f"      deepest at the field root: vs TSN {worst_tsn}, "
              f"vs Baseline {worst_bl} (limit 260)")


def main():
    test_host_kind()
    test_names_round_trip()
    test_reader_precedence()
    test_matrices()
    test_shipped_export()
    test_compare_labels()
    test_evidence_path_budget()
    raise SystemExit(c.summary())


if __name__ == "__main__":
    main()

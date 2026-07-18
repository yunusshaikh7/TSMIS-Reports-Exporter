"""CMP-AUD-049 (converter + evidence halves): a per-route PDF's own route
claim is the authoritative identity; the filename token merely corroborates.

Every TSMIS per-route PDF identifies its own route in-document — the page
banners ("Route: 004 …" on Highway Sequence / Ramp Detail, "Ref Date: …
Route 004 Page N" on Highway Detail), the Highway Log cover's "Route 006"
line, and Intersection Detail's cover "ROUTE : 020" parameter (its
per-record Location cells canNOT identify the document — an intersection
with another route prints the OTHER route's mainline, so multi-route
Location sets are normal; censused statewide, 118 of 217 prints). The
converters used to trust the FILENAME (Highway Log even logged a
disagreement warning and then used the filename anyway), so a renamed or
mixed-up file was silently absorbed under the wrong route.

Now `pdf_table_lib.reconcile_route_identity` enforces, in every family's
convert_one:
  * no in-document route claim        -> named FAILED input (PARTIAL);
  * conflicting in-document claims    -> named FAILED input (PARTIAL);
  * filename token != document claim  -> named FAILED input (PARTIAL);
  * token-less filename + clean claim -> converts under the DOCUMENT's route;
  * agreement                         -> converts (unchanged).

The rule pins drive each family's real consolidate() with parse_pdf stubbed;
the parser-capture pins build minimal positioned-text PDFs (via
build/_hl_fixture_pdf.make_pdf) and run the REAL parsers, proving the Highway
Sequence / Ramp Detail banner capture and the Highway Detail geometry-less
banner capture; the Intersection Detail Location regex is pinned on the
censused corpus shapes (incl. the two-letter counties' trailing period:
"07 LA. 001"). CI-safe: no local data, no browser.
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import consolidate_tsmis_highway_detail_pdf as hd  # noqa: E402
import consolidate_tsmis_highway_log_pdf as hl  # noqa: E402
import consolidate_tsmis_highway_sequence_pdf as hsl  # noqa: E402
import consolidate_tsmis_intersection_detail_pdf as idp  # noqa: E402
import consolidate_tsmis_ramp_detail_pdf as rd  # noqa: E402
import outcome  # noqa: E402
from _hl_fixture_pdf import make_pdf  # noqa: E402
from events import Events  # noqa: E402

failures = []


def check(label, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + label
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


# =============================================================================
# The shared helper's own contract
# =============================================================================

def helper_pins():
    print("reconcile_route_identity:")
    try:
        from pdf_table_lib import reconcile_route_identity
    except ImportError:
        check("pdf_table_lib.reconcile_route_identity exists", False)
        return
    logs = []
    ev = Events(on_log=logs.append)

    ctx = {"failed": []}
    r = reconcile_route_identity("x.pdf", "001", [], ev, ctx, claim_desc="the banner")
    check("no claim -> None + named failed",
          r is None and ctx["failed"] == ["x.pdf"]
          and any("does not identify" in ln for ln in logs), str(logs))

    ctx = {"failed": []}
    r = reconcile_route_identity("x.pdf", None, ["001", "002"], ev, ctx,
                                 claim_desc="the banner")
    check("conflicting claims -> None + named failed",
          r is None and ctx["failed"] == ["x.pdf"])

    ctx = {"failed": []}
    logs.clear()
    r = reconcile_route_identity("x.pdf", "002", ["005"], ev, ctx,
                                 claim_desc="the banner")
    check("filename/document disagreement -> None + named failed, both routes logged",
          r is None and ctx["failed"] == ["x.pdf"]
          and any("002" in ln and "005" in ln for ln in logs), str(logs))

    ctx = {"failed": []}
    r = reconcile_route_identity("x.pdf", None, ["007", "007"], ev, ctx,
                                 claim_desc="the banner")
    check("token-less filename + one claim -> the document's route",
          r == "007" and ctx["failed"] == [])

    ctx = {"failed": []}
    r = reconcile_route_identity("x.pdf", "009", ["009"], ev, ctx,
                                 claim_desc="the banner")
    check("agreement -> the route", r == "009" and ctx["failed"] == [])


# =============================================================================
# The rule inside every family's convert_one (parse_pdf stubbed)
# =============================================================================

def _stats_2tuple(base, claims):
    return dict(base, doc_routes=sorted(set(claims)))


FAMILIES = [
    # (key, module, filename prefix, row width, base stats, claim transport)
    ("highway_sequence", hsl, "highway_sequence_route_", 9,
     {"emitted": 1, "pages": 1, "data_pages": 1,
      "unclassified": 0, "stray_frags": 0, "bad_tokens": 0}, "stats"),
    ("ramp_detail", rd, "tsar_ramp_detail_route_", 13,
     {"emitted": 1, "pages": 1, "data_pages": 1,
      "unclassified": 0, "stray_frags": 0, "bad_tokens": 0}, "stats"),
    ("highway_detail", hd, "highway_detail_route_", 34,
     {"emitted": 1, "pages": 1, "orphans": 0, "single_line": 0,
      "fallback_pages": []}, "stats"),
    ("intersection_detail", idp, "intersection_detail_route_", 35,
     {"emitted": 1, "pages": 1, "orphans": 0, "vestigial": 0,
      "old_layout": 0}, "stats"),
    ("highway_log", hl, "highway_log_route_", 31,
     {"emitted": 1, "pages": 1, "skipped_no_geometry": 0,
      "stale_geometry_pages": 0, "carried_validated_pages": 0}, "route3"),
]


def _family_rows(ncols):
    """One valid-shaped row list for the family (contents are irrelevant to
    the identity rule — every family's claims ride stats or the 3-tuple)."""
    return [["000.000"] + ["x"] * (ncols - 1)]


def _run_family(mod, transport, ncols, base_stats, in_files, tmp):
    """Drive mod.consolidate() over in_files (name -> claim list) with
    parse_pdf stubbed to hand each document its claims."""
    in_dir = tmp / "in"
    in_dir.mkdir(parents=True)
    for name in in_files:
        (in_dir / name).write_bytes(b"%PDF-1.4\n%%EOF")
    logs = []

    def fake_parse(path, events, pdf_name=""):
        claims = in_files[Path(path).name]
        rows = _family_rows(ncols)
        if transport == "route3":
            return (claims[0] if claims else None), rows, dict(base_stats)
        return rows, _stats_2tuple(base_stats, claims)

    saved = mod.parse_pdf
    mod.parse_pdf = fake_parse
    try:
        res = mod.consolidate(
            events=Events(on_log=logs.append),
            confirm_overwrite=lambda _p: True,
            input_dir=in_dir, out_path=tmp / "combined.xlsx",
            converted_dir=tmp / "conv")
    finally:
        mod.parse_pdf = saved
    return res, logs, tmp / "conv"


def rule_pins():
    for key, mod, prefix, ncols, base_stats, transport in FAMILIES:
        print(f"{key} convert_one:")
        root = Path(tempfile.mkdtemp(prefix=f"tsmis_rid_{key}_"))
        try:
            # S1: filename says 002, the document says 005 -> named failed,
            # the good file still converts, completion PARTIAL.
            res, logs, conv = _run_family(
                mod, transport, ncols, base_stats,
                {f"{prefix}001.pdf": ["001"], f"{prefix}002.pdf": ["005"]},
                root / "s1")
            check(f"{key}: filename/document mismatch is a named FAILED input",
                  res.status == "ok" and res.completion == outcome.PARTIAL
                  and res.failed_inputs == 1
                  and any(f"{prefix}002.pdf" in ln for ln in res.summary_lines),
                  f"{res.status}/{res.completion} {res.summary_lines}")
            check(f"{key}: ...the mismatched file did NOT convert under either route",
                  not list(conv.glob("*_route_002.xlsx"))
                  and not list(conv.glob("*_route_005.xlsx")))
            check(f"{key}: ...both routes are named in the log",
                  any("002" in ln and "005" in ln for ln in logs))

            # S2: the document never identifies itself -> named failed.
            res, logs, conv = _run_family(
                mod, transport, ncols, base_stats,
                {f"{prefix}001.pdf": ["001"], f"{prefix}003.pdf": []},
                root / "s2")
            check(f"{key}: a document with no in-document route is a named FAILED input",
                  res.status == "ok" and res.completion == outcome.PARTIAL
                  and res.failed_inputs == 1
                  and any(f"{prefix}003.pdf" in ln for ln in res.summary_lines),
                  f"{res.status}/{res.completion} {res.summary_lines}")

            # S3: the document contradicts itself (impossible for the Highway
            # Log cover, whose first match pins the single claim).
            if transport != "route3":
                res, logs, conv = _run_family(
                    mod, transport, ncols, base_stats,
                    {f"{prefix}001.pdf": ["001"],
                     f"{prefix}004.pdf": ["004", "007"]},
                    root / "s3")
                check(f"{key}: conflicting in-document claims are a named FAILED input",
                      res.status == "ok" and res.completion == outcome.PARTIAL
                      and res.failed_inputs == 1
                      and any(f"{prefix}004.pdf" in ln for ln in res.summary_lines),
                      f"{res.status}/{res.completion} {res.summary_lines}")

            # S4: token-less filename, clean claim -> converts under the
            # DOCUMENT's route (the filename merely corroborates).
            res, logs, conv = _run_family(
                mod, transport, ncols, base_stats,
                {"export.pdf": ["007"]}, root / "s4")
            check(f"{key}: a token-less filename converts under the document's route",
                  res.status == "ok" and res.completion == outcome.COMPLETE
                  and res.failed_inputs == 0
                  and bool(list(conv.glob("*_route_007.xlsx"))),
                  f"{res.status}/{res.completion} {[p.name for p in conv.glob('*.xlsx')]}")

            # S5: agreement converts COMPLETE with no failures.
            res, logs, conv = _run_family(
                mod, transport, ncols, base_stats,
                {f"{prefix}009.pdf": ["009"]}, root / "s5")
            check(f"{key}: agreement still converts COMPLETE",
                  res.status == "ok" and res.completion == outcome.COMPLETE
                  and res.failed_inputs == 0,
                  f"{res.status}/{res.completion} {res.message}")
        finally:
            shutil.rmtree(root, ignore_errors=True)


# =============================================================================
# Parser capture: the REAL parsers read the claims from real (fixture) PDFs
# =============================================================================

def _hsl_page(banner_route, data_pm="001.000"):
    """One Highway Sequence data page: banner + the 7 header words + one row."""
    return [
        (30, 45, f"District: 10 Route: {banner_route} Direction: W - E"),
        (30, 78, "COUNTY"), (90, 78, "CITY"), (160, 78, "PM"), (210, 78, "HG"),
        (240, 78, "FT"), (270, 78, "NEXT"), (340, 78, "DESCRIPTION"),
        (30, 100, "ALP"), (152, 100, data_pm), (210, 100, "D"),
        (240, 100, "H"), (262, 100, "002.000"), (340, 100, "TEST POINT"),
    ]


def _rd_page(banner_route):
    """One Ramp Detail data page: banner + the anchored stacked header (the
    prefix 'E' and the U/F/Y tail letters between their anchors) + one row."""
    return [
        (30, 6, f"Route: {banner_route} Direction: W - E"),
        (30, 51, "LOCATION"), (75, 51, "E"), (100, 51, "PM"),
        (140, 51, "RECORD"), (200, 51, "AREA"), (250, 51, "CITY"),
        (290, 51, "CODE"), (320, 51, "U"), (335, 51, "F"), (350, 51, "Y"),
        (370, 51, "DESCRIPTION"),
        (30, 70, "04-CC-004"), (95, 70, "000.198"), (135, 70, "10/01/1996"),
        (182, 70, "D"), (195, 70, "Y"), (250, 70, "HER"), (318, 70, "U"),
        (333, 70, "N"), (348, 70, "H"), (370, 70, "TEST RAMP"),
    ]


def parser_pins():
    print("real-parser banner capture:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_rid_parse_"))
    try:
        p = tmp / "hsl.pdf"
        make_pdf(p, [_hsl_page("004")])
        rows, stats = hsl.parse_pdf(str(p), Events())
        check("HSL: the page banner's route lands in stats['doc_routes']",
              stats.get("doc_routes") == ["004"], str(stats))
        check("HSL: ...and the data row still parses (banner stays out of the rows)",
              len(rows) == 1 and rows[0][3] == "001.000"
              and stats["unclassified"] == 0, str(rows))

        p = tmp / "hsl2.pdf"
        make_pdf(p, [_hsl_page("004"), _hsl_page("007", data_pm="002.000")])
        _rows, stats = hsl.parse_pdf(str(p), Events())
        check("HSL: pages claiming different routes BOTH surface",
              stats.get("doc_routes") == ["004", "007"], str(stats))

        p = tmp / "rd.pdf"
        make_pdf(p, [_rd_page("004")])
        rows, stats = rd.parse_pdf(str(p), Events())
        check("RD: the page banner's route lands in stats['doc_routes']",
              stats.get("doc_routes") == ["004"], str(stats))
        check("RD: ...and the data row still parses",
              len(rows) == 1 and rows[0][2] == "000.198"
              and stats["unclassified"] == 0, str(rows))

        p = tmp / "hd.pdf"
        make_pdf(p, [[(30, 3, "Ref Date: 2026-07-10 Route 004 Page 1")]])
        rows, stats = hd.parse_pdf(str(p), Events())
        check("HD: the banner claim survives even when no grid geometry exists",
              rows == [] and stats.get("doc_routes") == ["004"], str(stats))

        suffixed = tmp / "hsl3.pdf"
        make_pdf(suffixed, [_hsl_page("005S")])
        _rows, stats = hsl.parse_pdf(str(suffixed), Events())
        check("HSL: a suffixed route's banner claim keeps its letter",
              stats.get("doc_routes") == ["005S"], str(stats))

        # ID: the cover's ROUTE parameter identifies even a record-less,
        # grid-less print (an intersection-less route's export); the
        # per-record Location cells are deliberately NOT the claim (an
        # intersection with another route prints the OTHER route's mainline).
        p = tmp / "id.pdf"
        make_pdf(p, [[(37, 78, "REPORT PARAMETERS:"),
                      (37, 141, "ROUTE : 020")]])
        rows, stats = idp.parse_pdf(str(p), Events())
        check("ID: the cover ROUTE parameter survives a grid-less print",
              rows == [] and stats.get("doc_routes") == ["020"], str(stats))
        p = tmp / "id178.pdf"
        make_pdf(p, [[(37, 141, "ROUTE : 178S")]])
        _rows, stats = idp.parse_pdf(str(p), Events())
        check("ID: a suffixed cover parameter keeps its letter",
              stats.get("doc_routes") == ["178S"], str(stats))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def evidence_adapter_pins():
    """CMP-AUD-049 (evidence half): every evidence adapter's locate_tsmis must
    refuse — RouteIdentityError — a per-route PDF whose own claims don't
    confirm the route the filename (= the engine's expected route) names, so
    a renamed foreign-route PDF can never be captioned as the requested
    route. Positive twins prove agreement still locates (an empty found dict
    on an empty needed_keys set, no raise)."""
    print("evidence adapters (locate_tsmis identity):")
    try:
        from pdf_table_lib import RouteIdentityError
    except ImportError:
        check("pdf_table_lib.RouteIdentityError exists", False)
        return
    import evidence_highway_detail as ehd
    import evidence_highway_log as ehl
    import evidence_highway_sequence as ehsl
    import evidence_intersection_detail as eid
    import evidence_ramp_detail as erd

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_rid_ev_"))

    def expect_raise(label, fn):
        try:
            fn()
        except RouteIdentityError:
            check(label, True)
        except Exception as e:  # noqa: BLE001 — the pin reports what happened
            check(label, False, f"raised {type(e).__name__}: {e}")
        else:
            check(label, False, "did not raise")

    try:
        # HSL: banner 007 inside a file named route_004.
        p = tmp / "highway_sequence_route_004.pdf"
        make_pdf(p, [_hsl_page("007")])
        expect_raise("HSL adapter refuses a banner/filename mismatch",
                     lambda: ehsl.locate_tsmis(p, set()))
        p2 = tmp / "highway_sequence_route_007.pdf"
        make_pdf(p2, [_hsl_page("007")])
        check("HSL adapter locates under agreement (no raise)",
              ehsl.locate_tsmis(p2, set()) == {})

        # RD: banner 007 inside a file named route_004.
        p = tmp / "tsar_ramp_detail_route_004.pdf"
        make_pdf(p, [_rd_page("007")])
        expect_raise("RD adapter refuses a banner/filename mismatch",
                     lambda: erd.locate_tsmis(p, set()))
        p2 = tmp / "tsar_ramp_detail_route_007.pdf"
        make_pdf(p2, [_rd_page("007")])
        check("RD adapter locates under agreement (no raise)",
              erd.locate_tsmis(p2, set()) == {})

        # HD: the banner claim binds even a geometry-less document.
        p = tmp / "highway_detail_route_002.pdf"
        make_pdf(p, [[(30, 3, "Ref Date: 2026-07-10 Route 004 Page 1")]])
        expect_raise("HD adapter refuses a banner/filename mismatch",
                     lambda: ehd.locate_tsmis(p, set()))
        p2 = tmp / "highway_detail_route_004.pdf"
        make_pdf(p2, [[(30, 3, "Ref Date: 2026-07-10 Route 004 Page 1")]])
        check("HD adapter locates under agreement (no raise)",
              dict(ehd.locate_tsmis(p2, set())) == {})

        # HL: the cover claim.
        p = tmp / "highway_log_route_002.pdf"
        make_pdf(p, [[(100, 300, "Route 005")]])
        expect_raise("HL adapter refuses a cover/filename mismatch",
                     lambda: ehl.locate_tsmis(p, set()))
        p2 = tmp / "highway_log_route_005.pdf"
        make_pdf(p2, [[(100, 300, "Route 005")]])
        check("HL adapter locates under agreement (no raise)",
              dict(ehl.locate_tsmis(p2, set())) == {})

        # ID: the cover parameter decides — a record-less print with a
        # matching cover verifies; a mismatched or cover-less one refuses.
        p = tmp / "intersection_detail_route_004.pdf"
        make_pdf(p, [[(100, 300, "NOT AN INTERSECTION PRINT")]])
        expect_raise("ID adapter refuses a document with no identity",
                     lambda: eid.locate_tsmis(p, set()))
        p = tmp / "intersection_detail_route_002.pdf"
        make_pdf(p, [[(37, 141, "ROUTE : 020")]])
        expect_raise("ID adapter refuses a cover/filename mismatch",
                     lambda: eid.locate_tsmis(p, set()))
        p2 = tmp / "intersection_detail_route_020.pdf"
        make_pdf(p2, [[(37, 141, "ROUTE : 020")]])
        check("ID adapter locates under agreement (no raise)",
              dict(eid.locate_tsmis(p2, set())) == {})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # The engine excludes (never captions) an identity-refused PDF: the
    # extracted locate loop turns RouteIdentityError into a missing route +
    # a loud note, and other errors keep their unreadable path.
    import visual_evidence as ve
    if not hasattr(ve, "_locate_tsmis_sources"):
        check("visual_evidence._locate_tsmis_sources exists", False)
        return

    class _StubAdapter:
        REPORT_LABEL = "Stub"

        @staticmethod
        def tsmis_pdf_path(pdf_dir, route):
            return Path(pdf_dir) / f"stub_route_{route}.pdf"

        @staticmethod
        def locate_tsmis(pdf_path, keys):
            if "002" in pdf_path.name:
                raise RouteIdentityError(f"{pdf_path.name}: claims route 005")
            return {"k": ["rec"]}

    tmp2 = Path(tempfile.mkdtemp(prefix="tsmis_rid_ev2_"))
    try:
        for name in ("stub_route_001.pdf", "stub_route_002.pdf"):
            (tmp2 / name).write_bytes(b"%PDF-1.4\n%%EOF")
        logs = []
        loc, missing = ve._locate_tsmis_sources(
            _StubAdapter, {"001": {"k"}, "002": {"k"}, "003": {"k"}}, tmp2,
            Events(on_log=logs.append))
        check("engine: the identity-refused PDF is excluded, not captioned",
              "002" in missing and "002" not in loc
              and any("claims route 005" in ln for ln in logs), str(logs))
        check("engine: the confirmed PDF still locates; the absent one is missing",
              loc.get("001") == {"k": ["rec"]} and "003" in missing)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)


def id_cover_pins():
    print("Intersection Detail cover-parameter claims (spaceless line text):")
    pat = getattr(idp, "COVER_ROUTE_RE", None)
    if pat is None:
        check("idp.COVER_ROUTE_RE exists", False)
        return
    for text, want in [
        ("ROUTE:020", "020"),
        ("ROUTE:178S", "178S"),         # suffixed route keeps its letter
        ("ROUTE:ALL", None),            # a statewide print is NOT per-route
        ("REFERENCEDATE:7/10/2026", None),
        ("COUNTY:ALL", None),
        ("", None),
    ]:
        m = pat.match(text)
        got = m.group(1) if m else None
        check(f"COVER_ROUTE_RE({text!r}) -> {want!r}", got == want, repr(got))


helper_pins()
rule_pins()
parser_pins()
evidence_adapter_pins()
id_cover_pins()

if failures:
    print(f"\nFAILED: {len(failures)}")
    sys.exit(1)
print("\nPDF route identity (CMP-AUD-049, converter + evidence halves): PASS")

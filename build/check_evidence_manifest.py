"""The durable evidence generation record and its two-phase publication.

CMP-AUD-106/109/098 are one contract: an evidence set is a workbook, an image
folder and a manifest that all describe the SAME generation, published together
or not at all. This check drives that contract from three sides —

  * the manifest as data: round-trip, and the shapes it must refuse;
  * `describe`, the reader a restart or a toggled-off rebuild depends on —
    current / stale / incomplete / absent / unreadable;
  * the real publication, including the case the previous divert-both path could
    not reach: the workbook commits and THEN the image folder turns out to be
    locked. The set must roll back whole, because a new workbook standing beside
    old images is evidence for a generation that never existed.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_evidence_manifest.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import _checklib
import compare_highway_detail_tsn as cht
import evidence_highway_detail as ehd
import evidence_manifest as em
import visual_evidence as ve
from PIL import Image

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def refuses(fn, *a, **k):
    try:
        fn(*a, **k)
    except em.EvidenceManifestError:
        return True
    return False


class Ev:
    """Cancellable on demand, so a test can cancel at a CHOSEN stage rather than
    guessing how many times the engine polls before it gets there."""

    def __init__(self):
        self.cancelled = False

    def is_cancelled(self):
        return self.cancelled

    def on_log(self, _m):
        pass


# --------------------------------------------------------------------------- #
print("the manifest as data")
_r = Path(tempfile.mkdtemp(prefix="check_ev_manifest_"))
_cmp = _r / "hd vs tsn.xlsx"
_cmp.write_bytes(b"a comparison workbook")
_wb, _img = ve.sibling_paths(_cmp)
_man = em.manifest_path(_cmp)

check("the manifest sibling costs no more path than the workbook does "
      "(the field install is already at the MAX_PATH budget, CMP-AUD-242)",
      len(_man.name) == len(_wb.name) and _man.name.endswith("(evidence).json"))
check("evidence_manifest names the same siblings visual_evidence publishes",
      em.sibling_artifacts(_cmp) == ve.sibling_paths(_cmp))

_built = em.build(state=em.STATE_NO_DIFFERENCES, report="Highway Detail",
                  comparison_path=_cmp, ledger_digest="d" * 64,
                  reader_version=1, difference_cells=0, differing_columns=0,
                  seed="0000abcd", layout="pair", examples=2, note="clean")
check("a no-artifact manifest round-trips",
      em.loads(em.dumps(_built)) == _built)
check("...and names the comparison by CONTENT, not by mtime",
      _built.comparison.sha256
      == ve.artifact_store.content_digest(_cmp)
      and _built.comparison.size == _cmp.stat().st_size)
check("dumps is canonical (stable across two builds of the same state)",
      em.dumps(_built) == em.dumps(em.loads(em.dumps(_built))))

check("an unknown state is refused at build",
      refuses(em.build, state="whatever", report="x", comparison_path=_cmp,
              ledger_digest="", reader_version=1, difference_cells=0,
              differing_columns=0))
_payload = _built.as_payload()
check("a foreign version is refused",
      refuses(em.loads, em.json.dumps({**_payload, "version": 99})))
check("an unknown state is refused at load",
      refuses(em.loads, em.json.dumps({**_payload, "state": "nope"})))
check("a 'rendered' manifest with no workbook is refused",
      refuses(em.loads, em.json.dumps({**_payload, "state": em.STATE_RENDERED})))
check("a no-artifact manifest that names a workbook is refused",
      refuses(em.loads, em.json.dumps(
          {**_payload, "workbook": {"name": "x", "size": 1, "sha256": "f" * 64}})))
check("a member with a short digest is refused",
      refuses(em.loads, em.json.dumps(
          {**_payload, "comparison": {"name": "x", "size": 1, "sha256": "f"}})))
check("a member with a negative size is refused",
      refuses(em.loads, em.json.dumps(
          {**_payload, "comparison": {"name": "x", "size": -1, "sha256": "f" * 64}})))
check("a non-list read_set is refused",
      refuses(em.loads, em.json.dumps({**_payload, "read_set": {}})))
check("text that is not JSON is refused", refuses(em.loads, "{not json"))

# --------------------------------------------------------------------------- #
print("describe: what the evidence beside a comparison currently claims")
check("no manifest -> absent", em.describe(_cmp)["status"] == em.ABSENT)
_man.write_text(em.dumps(_built), encoding="utf-8")
check("a no-artifact manifest with nothing surviving -> current",
      em.describe(_cmp)["status"] == em.CURRENT
      and em.describe(_cmp)["state"] == em.STATE_NO_DIFFERENCES)
_wb.write_bytes(b"a prior red evidence workbook")
check("a surviving workbook beside a no-artifact manifest -> incomplete",
      em.describe(_cmp)["status"] == em.INCOMPLETE
      and "survives" in em.describe(_cmp)["reason"])
_wb.unlink()
_cmp.write_bytes(b"a REBUILT comparison workbook")
check("the comparison's bytes changed -> stale (the toggled-off rebuild)",
      em.describe(_cmp)["status"] == em.STALE)
_man.write_text("{ this is not a manifest", encoding="utf-8")
check("an unparseable manifest -> unreadable, never treated as current",
      em.describe(_cmp)["status"] == em.UNREADABLE)
_man.unlink()

# --------------------------------------------------------------------------- #
print("two-phase publication: the whole set, or the prior one")


def publish_case(name, lock):
    """One publication attempt against a planted PRIOR generation."""
    root = _r / name
    root.mkdir()
    cmp_path = root / "hd vs tsn.xlsx"
    cmp_path.write_bytes(b"comparison " + name.encode())
    wb, img = ve.sibling_paths(cmp_path)
    man = em.manifest_path(cmp_path)
    wb.write_bytes(b"OLD workbook")
    img.mkdir()
    (img / "old.png").write_bytes(b"old image")
    # The prior manifest describes the prior set exactly.
    prior = em.build(state=em.STATE_RENDERED, report="HD",
                     comparison_path=cmp_path, ledger_digest="a" * 64,
                     reader_version=1, difference_cells=1, differing_columns=1,
                     workbook=wb, images=(em.member_for(img / "old.png"),))
    man.write_text(em.dumps(prior), encoding="utf-8")
    tmp = root / "rendered"
    tmp.mkdir()
    Image.new("RGB", (30, 15), "white").save(tmp / "Description_1_pair.png")
    entries = [{"field": "Description", "route": "001", "key": "1.0",
                "va": "A", "vb": "B", "note": "",
                "pair": "Description_1_pair.png"}]
    info = {"report": "HD", "comparison": cmp_path.name, "examples": 1,
            "seed": "00000000", "tsmis_dir": "A", "tsn_dir": "B"}

    def manifest_for(published_wb, published_images):
        return em.build(
            state=em.STATE_RENDERED, report="HD", comparison_path=cmp_path,
            ledger_digest="b" * 64, reader_version=1, difference_cells=2,
            differing_columns=1, workbook=published_wb,
            images=tuple(em.member_for(p)
                         for p in sorted(Path(published_images).iterdir())
                         if p.is_file()))

    real_replace = ve.os.replace
    blocked = {"n": 0}

    def replace(src, dst):
        target = {"workbook": wb, "images": img}.get(lock)
        if (target is not None and Path(dst) == target
                and Path(src).parent == root and not blocked["n"]):
            blocked["n"] += 1
            raise PermissionError(f"simulated {lock} locked open")
        return real_replace(src, dst)

    ve.os.replace = replace
    try:
        res = ve._publish_evidence_set(
            wb, img, tmp, entries, {}, info, "pair", (cmp_path,),
            ve.artifact_store.capture_source_identities((cmp_path,)), None,
            None, ve.owned_dir.directory_identity(tmp), man, manifest_for)
    finally:
        ve.os.replace = real_replace
    return cmp_path, wb, img, man, res


_c, _w, _i, _m, _res = publish_case("happy", lock=None)
check("nothing locked -> workbook, images and manifest all promote",
      _res["status"] == "promoted" and _res["workbook"] == str(_w)
      and _res["manifest"] == str(_m) and _res["note"] is None
      and _w.read_bytes() != b"OLD workbook"
      and not (_i / "old.png").exists() and _m.is_file())
_desc = em.describe(_c)
check("...and the published set describes itself as current",
      _desc["status"] == em.CURRENT and _desc["state"] == em.STATE_RENDERED)
check("...the manifest vouches for the bytes that actually LANDED",
      _desc["manifest"].workbook.sha256
      == ve.artifact_store.content_digest(_w)
      and [x.name for x in _desc["manifest"].images]
      == ["Description_1_pair.png"])
check("no quarantine or staging debris survives a clean publication",
      not [p.name for p in _c.parent.iterdir()
           if ".old-" in p.name or ".tmp-" in p.name or ".new-" in p.name])

_c, _w, _i, _m, _res = publish_case("wb_locked", lock="workbook")
check("workbook locked -> the SET diverts, nothing claimed at canonical",
      _res["status"] == "diverted" and _res["workbook"] is None
      and _res["folder"] is None and _res["manifest"] is None)
check("...the PRIOR workbook, images and manifest are all restored",
      _w.read_bytes() == b"OLD workbook"
      and (_i / "old.png").read_bytes() == b"old image" and _m.is_file())
check("...and the restored manifest still describes the restored set",
      em.describe(_c)["status"] == em.CURRENT)

# The residual half of CMP-AUD-109: the workbook commits, and only then does the
# image folder turn out to be locked. A committed workbook used to be
# unrecallable, so the canonical pair became new-workbook / old-images.
_c, _w, _i, _m, _res = publish_case("img_locked", lock="images")
check("images locked AFTER the workbook committed -> the set still diverts",
      _res["status"] == "diverted" and _res["workbook"] is None
      and _res["folder"] is None)
check("...the workbook is WITHDRAWN, so the OLD one is back at canonical",
      _w.read_bytes() == b"OLD workbook")
check("...the OLD images stay at canonical (never a new-wb / old-images mix)",
      (_i / "old.png").read_bytes() == b"old image")
check("...the withdrawn workbook is still available to the user, with its "
      "extension intact",
      any(p.suffix == ".xlsx" and ".new-" in p.name
          for p in _c.parent.iterdir()))
check("...the PRIOR manifest is restored and still describes the prior set",
      _m.is_file() and em.describe(_c)["status"] == em.CURRENT)
check("...and the note says what happened, rather than claiming success",
      "withdrawn" in (_res["note"] or ""))

# --------------------------------------------------------------------------- #
print("end to end: every terminal state records itself (CMP-AUD-106)")
_HD_ROW = ["001"] + ["0.100"] + ["x"] * (len(cht.SHARED_HEADER) - 1)
_DESC = 1 + cht.SHARED_HEADER.index("Description")


def hd_row(desc=None):
    row = list(_HD_ROW)
    if desc is not None:
        row[_DESC] = desc
    return row


def run_generate(name, rows_a, rows_b, proposals, locate=None,
                 cancel_at_locate=False, plant_prior=True):
    """Drive the SHIPPED generate() over a real published comparison."""
    root = _r / name
    root.mkdir()
    cmp_path = root / "day vs tsn.xlsx"
    _checklib.build_published_comparison(cmp_path, cht._SCHEMA, rows_a, rows_b)
    wb, img = ve.sibling_paths(cmp_path)
    man = em.manifest_path(cmp_path)
    if plant_prior:
        wb.write_bytes(b"PRIOR red evidence workbook")
        img.mkdir()
        (img / "prior.png").write_bytes(b"prior image")
        man.write_text(em.dumps(em.build(
            state=em.STATE_RENDERED, report="HD", comparison_path=cmp_path,
            ledger_digest="c" * 64, reader_version=1, difference_cells=9,
            differing_columns=1, workbook=wb,
            images=(em.member_for(img / "prior.png"),))), encoding="utf-8")
    cons = root / "cons.xlsx"; cons.write_bytes(b"consolidated")
    tsn = root / "tsn.xlsx"; tsn.write_bytes(b"tsn")
    tdir = root / "tsmis_pdf"; tdir.mkdir()
    (tdir / "highway_detail_route_001.pdf").write_bytes(b"%PDF tsmis")
    ndir = root / "tsn_pdf"; ndir.mkdir()
    (ndir / "d01.pdf").write_bytes(b"%PDF tsn")
    saved = (ehd.load_sides, ehd.enumerate_diffs, ve.tsn_pdf_dir,
             ve._locate_tsmis_sources)
    ehd.load_sides = lambda _c, _t: ([], [], {"ok": 1}, None)
    ehd.enumerate_diffs = lambda _x, _y, _s: proposals
    ve.tsn_pdf_dir = lambda _rk: ndir
    events = Ev()
    if locate is not None:
        ve._locate_tsmis_sources = locate
    saved_index = ehd.district_index
    if cancel_at_locate:
        # Cancel once the sources have been located — the render boundary, where
        # a late cancel must still leave the previous set untouched. Hooked on
        # district_index because BOTH source roles reach it (the Excel role
        # never calls _locate_tsmis_sources).
        def cancel_then_index(*_a, **_k):
            events.cancelled = True
            return {}
        ehd.district_index = cancel_then_index
    try:
        res = ve.generate("highway_detail", cons, tsn, cmp_path, tdir, events)
    finally:
        ehd.district_index = saved_index
        (ehd.load_sides, ehd.enumerate_diffs, ve.tsn_pdf_dir,
         ve._locate_tsmis_sources) = saved
    return cmp_path, wb, img, man, res


_PROPOSAL = {"Description": [dict(
    route="001", key="0.100", field="Description", va="ALPHA", vb="BETA",
    dist="01", cnty="ALA", pub_key="0.100", display="ALPHA ≠ BETA")]}

# match: a rebuilt comparison with no differences at all.
_c, _w, _i, _m, _res = run_generate("clean", [hd_row()], [hd_row()], {})
check("a clean comparison records 'no_differences'",
      _res["manifest_state"] == em.STATE_NO_DIFFERENCES and _m.is_file()
      and em.read(_m).state == em.STATE_NO_DIFFERENCES)
check("...the prior red set no longer survives at its canonical name",
      not _w.exists() and not _i.exists())
check("...and a reader (a RESTART, holding no state) agrees it is current",
      em.describe(_c)["status"] == em.CURRENT)
check("...the recorded ledger digest is the published comparison's own",
      len(em.read(_m).ledger_digest) == 64)

# differences exist, but none can be photographed: the PDFs never resolve.
_c, _w, _i, _m, _res = run_generate(
    "no_examples", [hd_row("ALPHA")], [hd_row("BETA")], _PROPOSAL,
    locate=lambda *a, **k: ({}, {"001"}))
check("a run that renders nothing records 'no_examples', not 'no_differences'",
      _res["manifest_state"] == em.STATE_NO_EXAMPLES
      and em.read(_m).state == em.STATE_NO_EXAMPLES)
check("...it still reports the published difference count",
      em.read(_m).difference_cells == 1 and em.read(_m).differing_columns == 1)
check("...the prior red set is retired here too",
      not _w.exists() and not _i.exists()
      and em.describe(_c)["status"] == em.CURRENT)

# the duplicate-only shape (CMP-AUD-108) is a no_examples state as well
_c, _w, _i, _m, _res = run_generate(
    "dup_only", [hd_row("A1"), hd_row("A2")], [hd_row("B1"), hd_row("B2")], {})
check("a duplicate-only comparison records 'no_examples' with its counts",
      _res["manifest_state"] == em.STATE_NO_EXAMPLES
      and em.read(_m).difference_cells == 2)

# cancellation: keep-last-good, and the prior record stays truthful.
_c, _w, _i, _m, _res = run_generate(
    "cancelled", [hd_row("ALPHA")], [hd_row("BETA")], _PROPOSAL,
    cancel_at_locate=True)
check("cancellation publishes nothing and records nothing",
      "cancelled" in _res["note"] and "manifest_state" not in _res)
check("...the prior evidence AND its manifest are left exactly as they were",
      _w.read_bytes() == b"PRIOR red evidence workbook"
      and (_i / "prior.png").exists()
      and em.read(_m).difference_cells == 9)

# a first run with no prior set still records its state
_c, _w, _i, _m, _res = run_generate(
    "first_run", [hd_row()], [hd_row()], {}, plant_prior=False)
check("a first run with nothing to retire still records its state",
      _m.is_file() and em.describe(_c)["status"] == em.CURRENT)

shutil.rmtree(_r, ignore_errors=True)

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s):")
    for name in _fail:
        print(f"  - {name}")
    sys.exit(1)
print("check_evidence_manifest: all checks passed")

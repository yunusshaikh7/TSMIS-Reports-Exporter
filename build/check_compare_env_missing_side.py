"""Golden check for the cross-environment MISSING-SIDE preflight (PCOA-FINAL-015).

`compare_folders` already discovers both sides' member lists before it loads
anything, but it used to hand side A to its loader first and only reach side B's
"nothing was exported here" refusal afterwards. On a statewide PDF family that
meant parsing 217-252 prints before reporting that the OTHER side has no export
at all: 429.4 s (Intersection Detail (PDF) cross-environment), 438.6 s (the same
family on Baseline) and 1,229.7 s (Highway Detail (PDF) on Everything ENV), where
a missing FIRST side already errored in 0.0 s.

Locks:
  * side A is never loaded when side B discovered no inputs — asserted on the
    LOADER, not the clock, so the guarantee does not depend on machine speed
    (the elapsed-time assertion rides along as the finding's own criterion);
  * the refusal is BYTE-FOR-BYTE the message side B's own loader raises, for
    every registered cross-environment family. The preflight refuses by CALLING
    that loader on the empty side, so the two can never drift;
  * an empty-but-present side B and an absent side B still read the same;
  * when BOTH sides are empty, side A still refuses first (the pre-fix verdict);
  * a side that discovered files is never pre-empted — `_find_input_dir` already
    drops Excel's `~$` owner-lock stubs (CMP-AUD-029), so "discovered nothing"
    and "the loader will refuse" are the same predicate for every family.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_env_missing_side.py
"""
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_env
import consolidate_highway_log as hl
import consolidate_tsmis_intersection_detail_pdf as idpdf
import highway_log_columns as hlc
from events import Events
from openpyxl import Workbook

# The pre-fix path hands side A to its loader, which logs a stack trace for every
# unparseable fixture. Silence it: the assertions are the output that matters.
logging.disable(logging.CRITICAL)

_fail = []

# The finding's own acceptance bar. Kept well above the real cost of a discovery
# refusal (milliseconds) so the assertion measures the DEFECT, not the machine.
MISSING_SIDE_BUDGET_S = 5.0
# Enough per-route files on side A that a pre-fix run visibly parses them.
SIDE_A_ROUTES = 12


def check(name, cond, detail=""):
    suffix = f"  -> {detail}" if (not cond and detail) else ""
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}{suffix}")
    if not cond:
        _fail.append(name)


def _adapters():
    """Every registered cross-environment folder adapter, keyed by its op key."""
    import report_catalog as rc
    return [(c.key, c.adapter) for c in rc.COMPARE if c.kind == "folders"]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def _write_highway_log_side(root, routes=SIDE_A_ROUTES):
    """A side the XLSX loader can really read: `routes` per-route Highway Log
    workbooks carrying the canonical 31-column header."""
    d = root / "highway_log"
    d.mkdir(parents=True, exist_ok=True)
    for n in range(1, routes + 1):
        wb = Workbook()
        ws = wb.active
        ws.title = hl.SHEET_NAME
        ws.append(list(hlc.HEADER))
        values = [""] * len(hlc.HEADER)
        values[0] = f"R{n:03d}.000"
        ws.append(values)
        wb.save(d / f"highway_log_route_{n:03d}.xlsx")
    return d


def _write_intersection_detail_pdf_side(root, routes=SIDE_A_ROUTES):
    """A PDF-sourced side. The bytes only have to make the loader ENTER its
    parse: this check asserts the loader is never called at all, so the PDFs
    need to be discoverable, not parseable."""
    d = root / idpdf.SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    for n in range(1, routes + 1):
        (d / f"intersection_detail_route_{n:03d}.pdf").write_bytes(
            b"%PDF-1.4\n% not a real print\n")
    return d


# --------------------------------------------------------------------------- #
# 1. Side A is never loaded when side B has nothing
# --------------------------------------------------------------------------- #
class _LoaderSpy:
    """Wrap every side loader this adapter could reach and record the folders it
    was asked to read. The preflight is allowed to enter the EMPTY side's loader
    (that is how it borrows the loader's own refusal); entering side A's is the
    defect.

    Both surfaces have to be wrapped. `_load_xlsx_side` is resolved from the
    module globals at call time, but `side_loader` / `flat_pdf_loader` were bound
    onto the adapter when the config was constructed — patching only the module
    would leave every PDF-sourced family (the 429 s / 1,229.7 s witnesses)
    unmeasured and the check green against the defect."""

    NAMES = ("_load_xlsx_side", "_load_ramp_summary_side",
             "_load_intersection_summary_side", "_load_highway_summary_side",
             "_load_highway_log_pdf_side", "_load_highway_detail_pdf_side",
             "_load_intersection_detail_pdf_side",
             "_load_highway_sequence_pdf_side", "_load_ramp_detail_pdf_side")

    def __init__(self, adapter=None):
        self.folders = []
        self._adapter = adapter
        self._saved = {}
        self._saved_bound = {}

    def _wrap(self, original):
        def spy(*args, **kwargs):
            self.folders.append(Path(args[0]).resolve(strict=False))
            return original(*args, **kwargs)
        return spy

    def __enter__(self):
        for name in self.NAMES:
            original = getattr(compare_env, name)
            self._saved[name] = original
            setattr(compare_env, name, self._wrap(original))
        for attr in ("side_loader", "flat_pdf_loader"):
            bound = getattr(self._adapter, attr, None) if self._adapter else None
            if bound is not None:
                self._saved_bound[attr] = bound
                setattr(self._adapter, attr, self._wrap(bound))
        return self

    def __exit__(self, *exc):
        for name, original in self._saved.items():
            setattr(compare_env, name, original)
        for attr, original in self._saved_bound.items():
            setattr(self._adapter, attr, original)
        return False

    def touched(self, folder):
        return Path(folder).resolve(strict=False) in self.folders


def _run(adapter, dir_a, dir_b, out):
    return adapter.compare_folders(str(dir_a), str(dir_b), str(out),
                                   events=Events(), confirm_overwrite=lambda _p: True,
                                   mode="values")


def test_side_a_is_not_parsed(root):
    print("side A is never loaded when side B discovered no inputs:")
    for label, adapter, write_side in (
            ("Highway Log (XLSX-sourced)", compare_env.HIGHWAY_LOG,
             _write_highway_log_side),
            ("Intersection Detail (PDF-sourced)", compare_env.INTERSECTION_DETAIL_PDF,
             _write_intersection_detail_pdf_side)):
        for shape in ("absent", "empty"):
            base = root / f"{adapter.key}-{shape}"
            a, b = base / "A", base / "B"
            write_side(a)
            b.mkdir(parents=True, exist_ok=True)
            if shape == "empty":
                (b / adapter.subdir).mkdir(parents=True, exist_ok=True)
            spy = _LoaderSpy(adapter)
            started = time.perf_counter()
            with spy:
                res = _run(adapter, a, b, base / "out.xlsx")
            elapsed = time.perf_counter() - started
            check(f"{label} / side B {shape}: refused", res.status == "error",
                  f"status={res.status!r} message={res.message!r}")
            check(f"{label} / side B {shape}: side A was never loaded",
                  not spy.touched(a),
                  "the first side was handed to its loader before the second "
                  "side's emptiness was checked")
            check(f"{label} / side B {shape}: refused in under "
                  f"{MISSING_SIDE_BUDGET_S:g} s",
                  elapsed < MISSING_SIDE_BUDGET_S, f"took {elapsed:.1f} s")
            check(f"{label} / side B {shape}: the message names the SECOND side",
                  "B" in (res.message or "").splitlines()[0],
                  f"message={res.message!r}")


# --------------------------------------------------------------------------- #
# 2. The refusal is the loader's own message, for every registered family
# --------------------------------------------------------------------------- #
def _loader_refusal(adapter, folder, label):
    """What this adapter's own loader says about a side with no inputs."""
    try:
        adapter._side_loader_fn()(Path(folder), label, Events())
    except ValueError as e:
        return str(e)
    return None


def test_message_is_the_loaders_own(root):
    print("every family's missing-side refusal is its LOADER's own message:")
    for key, adapter in _adapters():
        base = root / f"msg-{key.replace(':', '_')}"
        a, b = base / "A", base / "B"
        # Side A carries one discoverable file of the adapter's own kind, so the
        # preflight (not side A's loader) decides the outcome.
        pattern = adapter._discovery_pattern()
        src = a / adapter.subdir
        src.mkdir(parents=True, exist_ok=True)
        (src / f"route_001{pattern[1:]}").write_bytes(b"x")
        b.mkdir(parents=True, exist_ok=True)
        want = _loader_refusal(adapter, b, "B")
        check(f"{key}: its loader refuses an empty side", want is not None)
        res = _run(adapter, a, b, base / "out.xlsx")
        check(f"{key}: the comparison returns that exact message",
              res.status == "error" and res.message == want,
              f"got {res.message!r}\n         want {want!r}")


# --------------------------------------------------------------------------- #
# 3. The pre-fix verdicts that must NOT change
# --------------------------------------------------------------------------- #
def test_both_empty_still_refuses_on_side_a(root):
    print("when BOTH sides are empty, side A still refuses first (unchanged):")
    for key, adapter in _adapters():
        base = root / f"both-{key.replace(':', '_')}"
        a, b = base / "A", base / "B"
        a.mkdir(parents=True, exist_ok=True)
        b.mkdir(parents=True, exist_ok=True)
        want = _loader_refusal(adapter, a, "A")
        res = _run(adapter, a, b, base / "out.xlsx")
        check(f"{key}: refuses with side A's message",
              res.status == "error" and res.message == want,
              f"got {res.message!r}\n         want {want!r}")


def test_discovery_is_the_loader_predicate(root):
    """`_effective_source_files` is what the preflight consults, so it must be
    empty EXACTLY when the loader would refuse. `_find_input_dir` already drops
    `~$` owner-lock stubs, so a side holding nothing but a lock file is empty to
    both — the one case the plan warned could differ."""
    print("'discovered nothing' == 'the loader refuses', including ~$ stubs:")
    for key, adapter in _adapters():
        base = root / f"lock-{key.replace(':', '_')}"
        d = base / adapter.subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / f"~$route_001{adapter._discovery_pattern()[1:]}").write_bytes(b"x")
        empty = not adapter._effective_source_files(base)
        refuses = _loader_refusal(adapter, base, "A") is not None
        check(f"{key}: a ~$-only side is empty to discovery AND to the loader",
              empty and refuses, f"discovered_empty={empty} loader_refuses={refuses}")


def test_valid_comparison_is_unchanged(root):
    """The preflight must not touch a run where both sides have inputs."""
    print("a comparison with inputs on both sides still runs normally:")
    base = root / "valid"
    a, b = base / "A", base / "B"
    _write_highway_log_side(a, routes=2)
    _write_highway_log_side(b, routes=2)
    out = base / "out.xlsx"
    res = _run(compare_env.HIGHWAY_LOG, a, b, out)
    check("Highway Log: both sides present -> ok", res.status == "ok",
          f"status={res.status!r} message={res.message!r}")
    check("Highway Log: it wrote its workbook", out.exists())


def main():
    print("=== cross-environment missing-side preflight (PCOA-FINAL-015) ===")
    with tempfile.TemporaryDirectory(prefix="cmp_missing_side_") as tmp:
        root = Path(tmp)
        test_side_a_is_not_parsed(root)
        test_message_is_the_loaders_own(root)
        test_both_empty_still_refuses_on_side_a(root)
        test_discovery_is_the_loader_predicate(root)
        test_valid_comparison_is_unchanged(root)
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MISSING-SIDE PREFLIGHT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

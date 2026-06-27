"""Golden check for the P4 report-metadata catalog (`scripts/report_catalog.py`).

Proves the catalog is the single source of truth WITHOUT behavior drift:

* DERIVE — `reports.py` and `tsn_library.py` expose EXACTLY the catalog's views.
* GOLDEN EQUIVALENCE + EXECUTION IDENTITY — the catalog's metadata AND the exact
  objects (each export key's `ReportSpec`, each comparison key's adapter, each
  consolidate op's module, each auto-consolidator's module) equal an INDEPENDENT
  baseline this check imports itself. The identity assertions are factored into
  helpers, and the NEGATIVE self-tests run wrong-adapter / wrong-spec / wrong-module
  / missing-function inputs THROUGH those same helpers, asserting rejection (R1-T05).
* .BAT PARITY — the ordered `displayed-label / choice / goto / block / module` chain
  equals the registry order, WITHOUT dictionary collapse. EVERY raw `:label` is
  enumerated (not just label-then-python pairs) and each block's ordered control flow
  is retained: each dispatched goto-target must be defined exactly once, its block body
  (up to the NEXT label) must invoke exactly the intended consolidator, AND it must then
  terminate (`exit /b` / `exit` / `goto :eof`) before that next label. So a duplicate
  `:label` with an intervening command before a WRONG python call (CMD runs the FIRST
  matching label) AND a missing terminator that would fall through into the next
  consolidator are both caught. Negatives: wrong label, duplicate dispatch, immediate
  duplicate block, duplicate-label uniqueness, swapped goto, a raw duplicate-label
  decoy, and a removed block terminator (R1-M01).
* MOCK PARITY — the GUI `#mock`'s report lists match the REAL bridge payload
  (`gui_api._report_list_payload()`, a PURE builder) FIELD-FOR-FIELD: export
  (key, idx, label, fmt, disabled), consolidate (key, label, fmt), groups (id,
  label), compare (key, label, kind, group, file_a_label, file_b_label); the mock's
  separate `CONS_REPORTS` routing list is asserted equal to the registry; and the
  bridge's compare `subdir` (server-side, not mock-rendered) is cross-checked.

Console-free and side-effect-free: it imports the report modules (so openpyxl /
pdfplumber) to build the independent oracle, but performs NO filesystem write, NO
background-thread start, NO browser/network, and NEVER constructs `GuiApi`
(`test_no_side_effects` guards this — P4-R05). Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_report_catalog.py
"""
import importlib
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import report_catalog as cat
import reports
import tsn_library

# --- INDEPENDENT identity oracle: import the expected objects ourselves.
from export_ramp_summary import SPEC as _S_ramp_summary
from export_ramp_detail import SPEC as _S_ramp_detail
from export_highway_sequence import SPEC as _S_highway_sequence
from export_highway_log import SPEC as _S_highway_log
from export_highway_log_pdf import SPEC as _S_highway_log_pdf
from export_intersection_summary import SPEC as _S_intersection_summary
from export_intersection_detail import SPEC as _S_intersection_detail
from export_intersection_detail_pdf import SPEC as _S_intersection_detail_pdf
from export_highway_detail import SPEC as _S_highway_detail
from export_highway_summary import SPEC as _S_highway_summary
import consolidate_ramp_summary as _con_ramp_summary
import consolidate_ramp_detail as _con_ramp_detail
import consolidate_highway_sequence as _con_highway_sequence
import consolidate_highway_log as _con_highway_log
import consolidate_tsmis_highway_log_pdf as _con_tsmis_pdf
import consolidate_tsn_highway_log as _con_tsn_hl
import consolidate_intersection_summary as _con_int_summary
import consolidate_intersection_detail as _con_int_detail
import consolidate_tsmis_intersection_detail_pdf as _con_tsmis_int_detail_pdf
import compare_env as _ce
import compare_highway_log as _chl
import compare_highway_log_pdf as _chlp
import compare_intersection_detail_pdf as _cidp
import compare_ramp_detail_tsn as _crd_tsn
import compare_ramp_summary_tsn as _crs_tsn
import compare_intersection_summary_tsn as _cis_tsn
import compare_intersection_detail_tsn as _cid_tsn
import compare_highway_sequence_tsn as _chs_tsn

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
# FROZEN v0.17 baseline — the APPROVED snapshot, independent of the catalog.
# --------------------------------------------------------------------------- #
_EXPORT = [  # (key, label, fmt, expected ReportSpec)
    ("ramp_summary", "TSAR: Ramp Summary", "PDF", _S_ramp_summary),
    ("ramp_detail", "TSAR: Ramp Detail", "Excel", _S_ramp_detail),
    ("highway_sequence", "Highway Sequence Listing", "Excel", _S_highway_sequence),
    ("highway_log", "Highway Log", "Excel", _S_highway_log),
    ("highway_log_pdf", "Highway Log (PDF)", "PDF", _S_highway_log_pdf),
    ("intersection_summary", "Intersection Summary", "Excel", _S_intersection_summary),
    ("intersection_detail", "Intersection Detail", "Excel", _S_intersection_detail),
    ("intersection_detail_pdf", "Intersection Detail (PDF)", "PDF", _S_intersection_detail_pdf),
    # v0.18.1 reserved Highway groundwork (DISABLED) — appended.
    ("highway_detail", "Highway Detail", "Excel", _S_highway_detail),
    ("highway_summary", "Highway Summary", "Excel", _S_highway_summary),
]
_CONSOLIDATE = [  # (key, label, expected module)
    ("cons:ramp_summary", "TSAR: Ramp Summary", _con_ramp_summary),
    ("cons:ramp_detail", "TSAR: Ramp Detail", _con_ramp_detail),
    ("cons:highway_sequence", "Highway Sequence Listing", _con_highway_sequence),
    ("cons:intersection_summary", "Intersection Summary", _con_int_summary),
    ("cons:intersection_detail", "Intersection Detail", _con_int_detail),
    ("cons:intersection_detail_pdf", "TSMIS Intersection Detail (PDF)", _con_tsmis_int_detail_pdf),
    ("cons:highway_log_excel", "TSMIS Highway Log (Excel)", _con_highway_log),
    ("cons:highway_log_pdf", "TSMIS Highway Log (PDF)", _con_tsmis_pdf),
    ("cons:tsn_highway_log", "TSN Highway Log (PDF)", _con_tsn_hl),
]
_COMPARE = [  # (key, label, kind, group, expected adapter)
    ("cmp:ramp_summary:env", "TSAR: Ramp Summary — between environments", "folders", "env", _ce.RAMP_SUMMARY),
    ("cmp:ramp_detail:env", "TSAR: Ramp Detail — between environments", "folders", "env", _ce.RAMP_DETAIL),
    ("cmp:highway_sequence:env", "Highway Sequence Listing — between environments", "folders", "env", _ce.HIGHWAY_SEQUENCE),
    ("cmp:highway_log:env", "Highway Log — between environments", "folders", "env", _ce.HIGHWAY_LOG),
    ("cmp:intersection_summary:env", "TSAR: Intersection Summary — between environments", "folders", "env", _ce.INTERSECTION_SUMMARY),
    ("cmp:intersection_detail:env", "TSAR: Intersection Detail — between environments", "folders", "env", _ce.INTERSECTION_DETAIL),
    ("cmp:highway_log_pdf:env", "Highway Log (PDF) — between environments", "folders", "env", _ce.HIGHWAY_LOG_PDF),
    ("cmp:intersection_detail_pdf:env", "Intersection Detail (PDF) — between environments", "folders", "env", _ce.INTERSECTION_DETAIL_PDF),
    ("cmp:highway_log:tsn", "Highway Log — TSMIS vs TSN", "files", "tsn", _chl),
    ("cmp:highway_log:pdf_vs_tsn", "Highway Log — TSMIS (PDF) vs TSN (PDF)", "files", "tsn", _chlp.TSMIS_PDF_VS_TSN),
    ("cmp:highway_log:pdf_vs_excel", "Highway Log — TSMIS (PDF) vs TSMIS (Excel)", "files", "env", _chlp.TSMIS_PDF_VS_EXCEL),
    ("cmp:ramp_detail:tsn", "TSAR: Ramp Detail — TSMIS vs TSN", "files", "tsn", _crd_tsn),
    ("cmp:ramp_summary:tsn", "TSAR: Ramp Summary — TSMIS vs TSN", "files", "tsn", _crs_tsn),
    ("cmp:intersection_summary:tsn", "TSAR: Intersection Summary — TSMIS vs TSN", "files", "tsn", _cis_tsn),
    ("cmp:intersection_detail:tsn", "TSAR: Intersection Detail — TSMIS vs TSN", "files", "tsn", _cid_tsn),
    ("cmp:intersection_detail:pdf_vs_tsn", "Intersection Detail — TSMIS (PDF) vs TSN", "files", "tsn", _cidp.TSMIS_PDF_VS_TSN),
    ("cmp:intersection_detail:pdf_vs_excel", "Intersection Detail — TSMIS (PDF) vs TSMIS (Excel)", "files", "env", _cidp.TSMIS_PDF_VS_EXCEL),
    ("cmp:highway_sequence:tsn", "Highway Sequence Listing — TSMIS vs TSN", "files", "tsn", _chs_tsn),
]
_AUTO_CONS = {
    "ramp_summary": _con_ramp_summary, "ramp_detail": _con_ramp_detail,
    "highway_sequence": _con_highway_sequence, "highway_log": _con_highway_log,
    "intersection_summary": _con_int_summary, "intersection_detail": _con_int_detail,
}
_TSN = [
    ("highway_log", "TSN Highway Log", "*.pdf", "district_pdfs",
     "tsn_highway_log_consolidated.xlsx", "consolidate_tsn_highway_log:build_into"),
    ("ramp_detail", "TSN Ramp Detail", "*.xlsx", "statewide_xlsx",
     "tsn_ramp_detail_normalized.xlsx", "tsn_load_ramp_detail:build_into"),
    ("ramp_summary", "TSN Ramp Summary", "*.pdf", "statewide_pdf",
     "tsn_ramp_summary_normalized.xlsx", "tsn_load_ramp_summary:build_into"),
    ("intersection_summary", "TSN Intersection Summary", "*.pdf", "statewide_pdf",
     "tsn_intersection_summary_normalized.xlsx", "tsn_load_intersection_summary:build_into"),
    ("intersection_detail", "TSN Intersection Detail", "*.xlsx", "statewide_xlsx",
     "tsn_intersection_detail_normalized.xlsx", "tsn_load_intersection_detail:build_into"),
    ("highway_sequence", "TSN Highway Sequence", "*.pdf", "district_pdfs",
     "tsn_highway_sequence_normalized.xlsx", "consolidate_tsn_highway_sequence:build_into"),
]


# ---- Identity / resolution helpers (the production assertions AND the negatives
#      run the same code) ------------------------------------------------------
def _export_specs_match(entries, baseline):
    return (len(entries) == len(baseline)
            and all(e.spec is exp and e.spec.subdir == k
                    for e, (k, _l, _f, exp) in zip(entries, baseline)))


def _compare_adapters_match(entries, baseline):
    return (len(entries) == len(baseline)
            and all(c.adapter is a for c, (_k, _l, _ki, _g, a) in zip(entries, baseline)))


def _consolidate_modules_match(entries, baseline):
    return (len(entries) == len(baseline)
            and all(c.module is m for c, (_k, _l, m) in zip(entries, baseline)))


def _auto_cons_match(mapping, baseline):
    return set(mapping) == set(baseline) and all(mapping[s] is baseline[s] for s in baseline)


def _builders_callable(refs):
    ok = True
    for ref in refs:
        try:
            mod_name, func_name = ref.split(":", 1)
            target = getattr(importlib.import_module(mod_name), func_name, None)
        except (AttributeError, ImportError, TypeError, ValueError):
            target = None
        ok = ok and callable(target)
    return ok


def test_reports_derive_from_catalog():
    print("DERIVE: reports.py / tsn_library.py expose exactly the catalog views:")
    check("EXPORT_REPORTS == catalog.export_rows()", reports.EXPORT_REPORTS == cat.export_rows())
    check("EXPORT_KEYS == catalog.export_keys()", reports.EXPORT_KEYS == cat.export_keys())
    check("CONSOLIDATE_REPORTS == catalog.consolidate_rows()",
          reports.CONSOLIDATE_REPORTS == cat.consolidate_rows())
    check("CONSOLIDATE_KEYS == catalog.consolidate_keys()",
          reports.CONSOLIDATE_KEYS == cat.consolidate_keys())
    check("COMPARE_GROUPS == catalog.compare_groups()", reports.COMPARE_GROUPS == cat.compare_groups())
    check("COMPARE_REPORTS == catalog.compare_rows()", reports.COMPARE_REPORTS == cat.compare_rows())
    check("COMPARE_KEYS == catalog.compare_keys()", reports.COMPARE_KEYS == cat.compare_keys())
    check("_CONSOLIDATOR_BY_SUBDIR == catalog.consolidator_by_subdir()",
          reports._CONSOLIDATOR_BY_SUBDIR == cat.consolidator_by_subdir())
    check("tsn_library._REPORTS derives from catalog.tsn_entries()",
          [(r.subdir, r.label, r.raw_glob, r.raw_kind, r.consolidated_name, r.builder)
           for r in tsn_library.reports()]
          == [(e.subdir, e.label, e.raw_glob, e.raw_kind, e.consolidated_name, e.builder)
              for e in cat.tsn_entries()])


def test_golden_equivalence():
    print("GOLDEN: catalog metadata + execution identity == the FROZEN baseline:")
    check("EXPORT (key, label, fmt) == baseline",
          [(e.key, e.label, e.fmt) for e in cat.EXPORT] == [(k, l, f) for k, l, f, _s in _EXPORT])
    check("CONSOLIDATE (key, label) == baseline",
          [(c.key, c.label) for c in cat.CONSOLIDATE] == [(k, l) for k, l, _m in _CONSOLIDATE])
    check("COMPARE (key, label, kind, group) == baseline",
          [(c.key, c.label, c.kind, c.group) for c in cat.COMPARE]
          == [(k, l, ki, g) for k, l, ki, g, _a in _COMPARE])
    check("TSN descriptors == baseline",
          [(t.subdir, t.label, t.raw_glob, t.raw_kind, t.consolidated_name, t.builder)
           for t in cat.TSN] == _TSN)
    check("EXPORT spec IDENTITY == baseline", _export_specs_match(cat.EXPORT, _EXPORT))
    check("COMPARE adapter IDENTITY == baseline", _compare_adapters_match(cat.COMPARE, _COMPARE))
    check("CONSOLIDATE module IDENTITY == baseline", _consolidate_modules_match(cat.CONSOLIDATE, _CONSOLIDATE))
    check("AUTO-CONSOLIDATOR module IDENTITY == baseline",
          _auto_cons_match(cat.consolidator_by_subdir(), _AUTO_CONS))
    check("every TSN builder module:function is callable", _builders_callable(cat.tsn_builder_refs()))


def test_negative_self_tests():
    print("NEGATIVE: mutated inputs run THROUGH the production helpers and are rejected:")
    bad_cmp = list(cat.COMPARE)
    bad_cmp[0] = bad_cmp[0]._replace(adapter=_ce.RAMP_DETAIL)        # wrong adapter
    check("[neg] _compare_adapters_match rejects a wrong adapter",
          not _compare_adapters_match(bad_cmp, _COMPARE))
    bad_auto = dict(cat.consolidator_by_subdir())
    bad_auto["ramp_summary"] = _con_ramp_detail                      # wrong auto-consolidator
    check("[neg] _auto_cons_match rejects a wrong module", not _auto_cons_match(bad_auto, _AUTO_CONS))
    bad_exp = list(cat.EXPORT)
    bad_exp[0] = bad_exp[0]._replace(spec=_S_ramp_detail)            # wrong spec
    check("[neg] _export_specs_match rejects a wrong spec", not _export_specs_match(bad_exp, _EXPORT))
    bad_con = list(cat.CONSOLIDATE)
    bad_con[0] = bad_con[0]._replace(module=_con_ramp_detail)        # wrong consolidate module
    check("[neg] _consolidate_modules_match rejects a wrong module",
          not _consolidate_modules_match(bad_con, _CONSOLIDATE))
    check("[neg] _builders_callable rejects a missing function",
          not _builders_callable(("consolidate_tsn_highway_log:no_such_func",)))


# ---- .bat parsing (ordered, RAW — every label + ordered block control flow) -
# An UNCONDITIONAL block terminator (no `if` prefix) that prevents fall-through into
# the next label. `exit /b` is the repository form; `exit` and `goto :eof` are the
# other explicitly-accepted terminal transfers.
_TERMINATOR = re.compile(r"(?i)^(?:exit\s*/b(?:\s+\d+)?|exit(?:\s+\d+)?|goto\s+:eof)\s*$")
_CONSOLIDATOR = re.compile(r"python\s+scripts\\(consolidate_\w+)\.py")


def _parse_bat(bat):
    """Ordered/raw extraction with NO dictionary collapse.

    Returns (menu, dispatch, labels, blocks):
      menu     ordered [(number, displayed-text)] from the `echo  N. ...` rows
      dispatch ordered [(number, goto-target)] from the `if ... goto` rows
      labels   ordered [label] for EVERY raw `:label` definition CMD can target
      blocks   ordered [(label, events)] per raw label, where `events` is the ordered
               control flow from that label to the NEXT label (exactly what CMD runs):
               `("cons", module)` for a consolidator call, `("term", line)` for an
               unconditional block terminator.
    """
    menu, dispatch, labels, blocks = [], [], [], []
    cur, events = None, None
    for ln in bat.splitlines():
        s = ln.strip()
        ml = re.match(r":(\w+)", s)                   # a raw label DEFINITION (`::` is a comment)
        if ml:
            if cur is not None:
                blocks.append((cur, events))
            cur, events = ml.group(1), []
            labels.append(cur)
            continue
        mm = re.match(r"echo\s+(\d+)\.\s+(.+)", s)
        if mm:
            menu.append((mm.group(1), mm.group(2).strip()))
            continue
        md = re.match(r'if\s+/i\s+"%choice%"=="(\d+)"\s+goto\s+(\w+)', s)
        if md:
            dispatch.append((md.group(1), md.group(2)))
            continue
        if cur is not None:
            mc = _CONSOLIDATOR.match(s)
            if mc:
                events.append(("cons", mc.group(1)))
            elif _TERMINATOR.match(s):
                events.append(("term", s))
    if cur is not None:
        blocks.append((cur, events))
    return menu, dispatch, labels, blocks


def _first(pairs):
    d = {}
    for k, v in pairs:
        d.setdefault(k, v)            # CMD runs the FIRST matching branch
    return d


def _first_block(blocks):
    d = {}
    for label, events in blocks:
        d.setdefault(label, events)   # CMD jumps to the FIRST block defining a label
    return d


def _block_mods(events):
    return [m for kind, m in events if kind == "cons"]


def _bat_chain(nums, dispatch, blocks):
    """choice -> first goto -> first block -> the block's SOLE consolidator.

    A block whose body up to the next label invokes zero or 2+ consolidators yields
    None (invalid), enforcing 'exactly the intended consolidator'.
    """
    df, fb = _first(dispatch), _first_block(blocks)
    out = []
    for n in nums:
        mods = _block_mods(fb.get(df.get(n)) or [])
        out.append(mods[0] if len(mods) == 1 else None)
    return out


def _terminates_after_consolidator(events):
    """Exactly one consolidator, then an unconditional terminator before the next label.

    Guards CMD fall-through: a block missing `exit /b` (etc.) runs the intended
    consolidator and then keeps executing into the NEXT label's consolidator.
    """
    cons = [i for i, (k, _v) in enumerate(events) if k == "cons"]
    term = [i for i, (k, _v) in enumerate(events) if k == "term"]
    return len(cons) == 1 and any(t > cons[0] for t in term)


def _all_blocks_terminate(dispatch, blocks):
    """Every dispatched block invokes its sole consolidator and then terminates."""
    fb = _first_block(blocks)
    return all(_terminates_after_consolidator(fb.get(t) or []) for _n, t in dispatch)


def _dispatch_exact(dispatch, nums):
    """Exactly one dispatch row for every displayed choice, in the same order."""
    return [n for n, _target in dispatch] == nums


def _targets_defined_once(labels, dispatch):
    """Every dispatched goto-target is defined by exactly one raw `:label`."""
    counts = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    return all(counts.get(t, 0) == 1 for _n, t in dispatch)


def _labels_match(menu, expected_labels):
    """Displayed text is exactly the registry label plus an optional `(format...)` note."""
    if len(menu) != len(expected_labels):
        return False
    for (_number, rest), label in zip(menu, expected_labels):
        if not rest.startswith(label):
            return False
        suffix = rest[len(label):].strip()
        if suffix and not (suffix.startswith("(") and suffix.endswith(")")):
            return False
    return True


def test_bat_parity():
    print(".BAT PARITY: ordered label/choice/goto/block/module chain == registry (R1-M01):")
    bat = (ROOT / "4. consolidate (combine reports).bat").read_text(encoding="utf-8", errors="replace")
    menu, dispatch, labels, blocks = _parse_bat(bat)
    nums = [str(i) for i in range(1, len(cat.CONSOLIDATE) + 1)]
    exp_modules = [c.module.__name__ for c in cat.CONSOLIDATE]
    exp_labels = [c.label for c in cat.CONSOLIDATE]
    term = [("cons", "consolidate_intersection_detail"), ("term", "exit /b 0")]  # well-formed block
    check("menu shows choices 1..N in order", [n for n, _r in menu] == nums)
    check("dispatch rows are exactly choices 1..N in order (no duplicate/extra branch)",
          _dispatch_exact(dispatch, nums))
    check("every dispatched goto-target is defined by exactly one raw label",
          _targets_defined_once(labels, dispatch))
    check("displayed labels exactly match the registry labels, in order",
          _labels_match(menu, exp_labels))
    check("ordered choice->block->sole-consolidator chain (FIRST match) == registry order",
          _bat_chain(nums, dispatch, blocks) == exp_modules)
    check("every dispatched block terminates after its consolidator (no fall-through)",
          _all_blocks_terminate(dispatch, blocks))
    check("both Intersection consolidators are dispatched (closed drift)",
          {"consolidate_intersection_summary", "consolidate_intersection_detail"}
          <= set(_bat_chain(nums, dispatch, blocks)))
    # NEGATIVES — every still-green variant Codex demonstrated across rounds 2-4.
    bad_menu = list(menu)
    bad_menu[3] = (bad_menu[3][0], "Intersection Detail (XLSX)")     # choice 4 mislabeled
    check("[neg] a wrong displayed label is caught", not _labels_match(bad_menu, exp_labels))
    dup_dispatch = [("4", "intersection_detail")] + dispatch         # first-wrong + correct dup
    check("[neg] a duplicate/first-wrong dispatch fails exactly-one",
          not _dispatch_exact(dup_dispatch, nums))
    check("[neg] ...and its FIRST-match chain mismatches the registry",
          _bat_chain(nums, dup_dispatch, blocks) != exp_modules)
    dup_blocks = [("intersection_summary", term)] + blocks           # first-wrong duplicate block
    check("[neg] an immediate duplicate label block (first-wrong) mismatches via FIRST match",
          _bat_chain(nums, dispatch, dup_blocks) != exp_modules)
    check("[neg] a duplicate dispatched-target label fails uniqueness",
          not _targets_defined_once(labels + ["intersection_summary"], dispatch))
    swapped = [(n, {"4": "intersection_detail", "5": "intersection_summary"}.get(n, t))
               for n, t in dispatch]                                  # swap choice 4<->5 goto
    check("[neg] a swapped choice->goto is caught", _bat_chain(nums, swapped, blocks) != exp_modules)
    # (round 3) a RAW duplicate `:label` whose first body has an intervening `rem`
    # before a WRONG python call — CMD's goto reaches the first (wrong) block.
    decoy = (":intersection_summary\n"
             "rem decoy comment\n"
             "python scripts\\consolidate_intersection_detail.py\n"
             "pause\nexit /b 0\n\n")
    bad_bat = bat.replace(":intersection_summary\n", decoy + ":intersection_summary\n", 1)
    _bm, b_disp, b_labels, b_blocks = _parse_bat(bad_bat)
    check("[neg] a raw duplicate label (intervening rem + wrong call) fails uniqueness",
          not _targets_defined_once(b_labels, b_disp))
    check("[neg] ...and CMD's FIRST-match block runs the WRONG consolidator",
          _bat_chain(nums, b_disp, b_blocks) != exp_modules)
    # NEW (round 4): a block missing its terminator falls through into the next
    # consolidator. The module chain stays green; only the termination guard catches it.
    no_term = bat.replace(
        "python scripts\\consolidate_intersection_summary.py\npause\nexit /b 0\n",
        "python scripts\\consolidate_intersection_summary.py\npause\n", 1)
    _nm, nt_disp, _nl, nt_blocks = _parse_bat(no_term)
    check("[neg] a removed block terminator (fall-through risk) fails the termination guard",
          not _all_blocks_terminate(nt_disp, nt_blocks))
    check("[neg] ...while the module chain alone stays green (termination is a distinct guard)",
          _bat_chain(nums, nt_disp, nt_blocks) == exp_modules)


# ---- Mock parity (vs the PURE bridge payload, field-for-field) ---------------
def _mock_objs(text, block_re):
    m = re.search(block_re, text, re.DOTALL)
    if not m:
        return None
    objs = []
    for chunk in m.group(1).split("}"):
        fields = dict(re.findall(r'(\w+):\s*"([^"]*)"', chunk))        # quoted string fields
        for k, v in re.findall(r'(\w+):\s*(true|false)\b', chunk):     # boolean fields (e.g. disabled)
            fields[k] = (v == "true")
        if fields:
            objs.append(fields)
    return objs


def test_mock_parity():
    print("MOCK PARITY: #mock report lists == the PURE bridge payload, field-for-field:")
    import gui_api
    be = gui_api._report_list_payload()                              # pure; NO GuiApi (P4-R05)
    mockjs = (ROOT / "scripts" / "ui" / "mock.js").read_text(encoding="utf-8")  # P9: mock moved app.js -> mock.js

    # idx is the position in the (picker-ordered) REPORTS array; `disabled` is per-entry
    # (the map defaults it false, each entry may override — e.g. the reserved Highway pair).
    rep = _mock_objs(mockjs, r"const REPORTS = \[(.*?)\];")
    fe_export = [(o["key"], i, o["label"], o["fmt"], bool(o.get("disabled", False)))
                 for i, o in enumerate(rep or [])]
    be_export = [(r["key"], r["idx"], r["label"], r["fmt"], r["disabled"]) for r in be["reports"]]
    check("mock export (key, idx, label, fmt, disabled) == bridge", fe_export == be_export)

    cons = _mock_objs(mockjs, r"cons_reports:\s*\[(.*?)\],")
    fe_cons = [(o["key"], o["label"], o["fmt"]) for o in (cons or [])]
    be_cons = [(r["key"], r["label"], r["fmt"]) for r in be["cons_reports"]]
    check("mock consolidate (key, label, fmt) == bridge", fe_cons == be_cons)

    grp = _mock_objs(mockjs, r"compare_groups:\s*\[(.*?)\],")
    fe_grp = [(o["id"], o["label"]) for o in (grp or [])]
    be_grp = [(g["id"], g["label"]) for g in be["compare_groups"]]
    check("mock compare groups (id, label) == bridge", fe_grp == be_grp)

    cmp_ = _mock_objs(mockjs, r"compare_reports:\s*\[(.*?)\],")
    fe_cmp = [(o["key"], o["label"], o["kind"], o["group"],
               o.get("file_a_label", "TSMIS"), o.get("file_b_label", "TSN")) for o in (cmp_ or [])]
    be_cmp = [(r["key"], r["label"], r["kind"], r["group"], r["file_a_label"], r["file_b_label"])
              for r in be["compare_reports"]]
    check("mock compare (key, label, kind, group, file_a, file_b) == bridge", fe_cmp == be_cmp)

    # The mock's SEPARATE CONS_REPORTS routing list (used by consByKey) must equal the registry.
    routing = _mock_objs(mockjs, r"const CONS_REPORTS = \[(.*?)\];")
    fe_routing = [(o["key"], o["label"]) for o in (routing or [])]
    check("mock CONS_REPORTS routing (key, label) == catalog consolidate",
          fe_routing == [(c.key, c.label) for c in cat.CONSOLIDATE])

    # Bridge `subdir` is server-side metadata (not mock-rendered; the frontend resolves
    # folders via get_compare_folders). Cross-check it matches each compare key's family.
    sub_ok = all(r["subdir"] == (r["key"].split(":")[1] if r["kind"] == "folders" else None)
                 for r in be["compare_reports"])
    check("bridge compare subdir matches the key family (folders) / None (files)", sub_ok)

    # NEGATIVES: each compared field actually participates (a mutated copy != the bridge).
    mx = [list(t) for t in fe_export]; mx[0][4] = (not mx[0][4]) if mx[0][4] is not None else True
    check("[neg] a changed export `disabled` is caught", [tuple(x) for x in mx] != be_export)
    mc = [list(t) for t in fe_cmp]; mc[7][4] = "WRONG"               # a files row's file_a_label
    check("[neg] a changed compare file_a_label is caught", [tuple(x) for x in mc] != be_cmp)
    check("[neg] a changed CONS_REPORTS label is caught",
          [("cons:ramp_summary", "WRONG")] + fe_routing[1:]
          != [(c.key, c.label) for c in cat.CONSOLIDATE])


def test_no_side_effects():
    print("SAFETY: the parity path writes nothing, starts no thread, never builds GuiApi (P4-R05):")
    import gui_api
    calls = {"ensure_layout": 0, "thread_start": 0, "guiapi_init": 0}
    saved = (tsn_library.ensure_layout, threading.Thread.start, gui_api.GuiApi.__init__)
    tsn_library.ensure_layout = lambda *a, **k: calls.__setitem__("ensure_layout", calls["ensure_layout"] + 1)
    threading.Thread.start = lambda self, *a, **k: calls.__setitem__("thread_start", calls["thread_start"] + 1)
    gui_api.GuiApi.__init__ = lambda self, *a, **k: calls.__setitem__("guiapi_init", calls["guiapi_init"] + 1)
    try:
        before = threading.active_count()
        _ = gui_api._report_list_payload()          # the EXACT call test_mock_parity makes
        after = threading.active_count()
    finally:
        tsn_library.ensure_layout, threading.Thread.start, gui_api.GuiApi.__init__ = saved
    check("the parity payload call writes no TSN library (ensure_layout = 0)", calls["ensure_layout"] == 0)
    check("the parity payload call starts no background thread", calls["thread_start"] == 0 and after == before)
    check("the parity payload call never constructs GuiApi", calls["guiapi_init"] == 0)


def main():
    test_reports_derive_from_catalog()
    test_golden_equivalence()
    test_negative_self_tests()
    test_bat_parity()
    test_mock_parity()
    test_no_side_effects()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL REPORT-CATALOG CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

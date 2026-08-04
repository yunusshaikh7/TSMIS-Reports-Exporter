"""RB4-A1 — the one executable acceptance run for hotfix bundle RB-4 (HF-05 + HF-10).

Drives the exact end-user paths the GUI workers drive — matrix.build_comparison
(Everything vs-TSN / SELF / ENV cells with the worker's own owned-dir leases and
commit guard), day_matrix.build_day_cell (By Day vs-TSN), the on-demand cameras
(matrix.evidence_for_cell / day_matrix.evidence_for_day_cell), and the classic
Compare tab + PDF-vs-Excel by-day silent controls — against the frozen 2026-07-23
and 2026-07-09 pulls, and retains one machine-readable, hash-bound result set.

Phases (run in order; `--phase all` for base-or-head sweeps is deliberate NOT
offered — each phase is invoked explicitly so the retained logs name what ran):

  provision   copy the frozen inputs into per-side acceptance stores (base/head)
              and the TSN library copy, hashing every provisioned file
  generate    run the full cell set for one side (--side base|head) against one
              scripts tree (--tree; defaults to this repo). The base side runs
              against a `git archive` export of the recorded base commit so the
              pre-fix defect signatures bind to that exact runtime
  census      app-free recount of the retained audit evidence sets and the
              base-side sets: truncation population, read-set composition,
              prose declarations (the PCOA-FINAL-004/-006 defect signatures)

Every result lands under the acceptance root as JSON; the final manifest/verifier
(rb4-verify-manifest.py at the audit docs root) binds the whole set to the
acceptance head. This driver is acceptance tooling, not app runtime: it prints.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
# fixed identities
# --------------------------------------------------------------------------- #
RUN_ID_DEFAULT = "RB4-A1"
ROOT_DEFAULT = Path(r"C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-05\rb4-a1")
HF10_RETAIN = Path(r"C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-10\rb4-a1")

FROZEN = {
    "pull_2026_07_23": Path(r"C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-claude-independent-2026-07-23\raw-extract\2026-07-23 ssor-prod"),
    "pull_2026_07_09_ssor": Path(r"C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ssor-prod"),
    "pull_2026_07_09_ars": Path(r"C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9\2026-07-09 ars-prod"),
    "tsn_library": Path(r"C:\Users\Yunus\Downloads\TSMIS\tsn_library"),
}
AUDIT_EVERYTHING = Path(r"C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-claude-independent-2026-07-23\everything-dest\comparisons\tsn")
AUDIT_BYDAY = Path(r"C:\Users\Yunus\Projects\TSMIS-Reports-Exporter\output\comparisons\tsn-by-day\2026-07-23 ssor-prod")

# The everything-store provisioning — the Stage 1B layout the audit measured:
# ssor-prod <- the 2026-07-23 pull, ssor-test <- the 2026-07-09 ssor pull,
# ars-prod <- the 2026-07-09 ars outage-substitute (ID/IS only).
# highway_detail is EXCLUDED everywhere: pre-release (owner 2026-07-21), its
# artifacts are not ground truth and RB-4 must not generate from them.
ENV_PROVISION = {
    "ssor-prod": ("pull_2026_07_23", (
        "highway_log", "highway_log_pdf", "highway_sequence",
        "highway_sequence_pdf", "intersection_detail", "intersection_detail_pdf",
        "intersection_summary", "intersection_summary_pdf",
        "ramp_detail", "ramp_detail_pdf", "ramp_summary", "ramp_summary_excel")),
    "ssor-test": ("pull_2026_07_09_ssor", (
        "highway_log", "highway_log_pdf", "highway_sequence",
        "highway_sequence_pdf", "intersection_detail", "intersection_detail_pdf",
        "intersection_summary", "ramp_detail", "ramp_detail_pdf",
        "ramp_summary", "ramp_summary_excel")),
    "ars-prod": ("pull_2026_07_09_ars", (
        "intersection_detail", "intersection_detail_pdf",
        "intersection_summary", "intersection_summary_pdf")),
}
# By Day inputs: one run folder (the frozen 2026-07-23 pull), same subdir set.
BYDAY_DAY, BYDAY_SOURCE = "2026-07-23", "ssor-prod"
TSN_LIB_REPORTS = ("highway_log", "highway_sequence", "intersection_detail",
                   "intersection_summary", "ramp_detail", "ramp_summary")

# The complete evidence-relevant cell set (highway_detail excluded, pre-release).
TSN_ROWS = ("highway_log", "highway_log_pdf", "highway_sequence",
            "highway_sequence_pdf", "intersection_detail",
            "intersection_detail_pdf", "ramp_detail", "ramp_detail_pdf")
# The self mode rides each PDF row (`vs_excel`); Highway Log's Excel row also
# offers the symmetric `vs_pdf` — exactly the audit's observed self sets.
SELF_CELLS = (("highway_log", "vs_pdf"),) + tuple(
    (r, "vs_excel") for r in TSN_ROWS if r.endswith("_pdf"))
# The five Everything ENV PDF-vs-PDF cells (PCOA-FINAL-007), paired the way the
# audit measured them: ID-PDF against the ars-prod outage substitute, the rest
# against the 2026-07-09 ssor pull provisioned as ssor-test.
ENV_CELLS = (("highway_log_pdf", "ssor-test"),
             ("highway_sequence_pdf", "ssor-test"),
             ("ramp_detail_pdf", "ssor-test"),
             ("ramp_summary", "ssor-test"),
             ("intersection_detail_pdf", "ars-prod"))
BASELINE = "ssor-prod"
EVIDENCE_REQUEST = {"enabled": True, "examples": 2, "layout": "both"}

_CHUNK = 1 << 20


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {path}")


def tree_stamp(tree):
    """The tree-under-test's exact git head + runtime dirty state — the
    self-stamp every retained result carries so exact-head identity lives in
    the record itself (the RB-2 lesson), not only in the manifest's assertion.
    An exported base tree has no .git: (None, None). Dirtiness is judged over
    the RUNTIME roots only, so docs-side edits never poison a head stamp."""
    import subprocess
    try:
        head = subprocess.run(("git", "-C", str(tree), "rev-parse", "HEAD"),
                              capture_output=True, text=True)
        if head.returncode != 0:
            return None, None
        status = subprocess.run(
            ("git", "-C", str(tree), "status", "--porcelain", "--",
             "scripts", "version.py", "requirements.txt", "build"),
            capture_output=True, text=True)
        dirty = (bool(status.stdout.strip()) if status.returncode == 0
                 else None)
        return head.stdout.strip(), dirty
    except OSError:
        return None, None


class Tee:
    """Mirror stdout/stderr into the retained per-phase log."""

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(path, "a", encoding="utf-8")
        self._stdout = sys.stdout

    def write(self, text):
        self._stdout.write(text)
        self._f.write(text)
        self._f.flush()

    def flush(self):
        self._stdout.flush()
        self._f.flush()


# --------------------------------------------------------------------------- #
# provision
# --------------------------------------------------------------------------- #
def _copy_tree_hashed(src, dst, inventory, source_key):
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        shutil.copyfile(p, target)
        inventory.append({"path": str(target), "source": str(p),
                          "source_key": source_key,
                          "size": target.stat().st_size,
                          "sha256": sha256_of(target)})
        n += 1
    return n


def phase_provision(root, sides, tree):
    sys.path.insert(0, str(Path(tree) / "scripts"))
    import owned_dir
    t0 = time.time()
    inventory = []
    lib = root / "lib" / "tsn_library"
    if lib.exists():
        print(f"  lib already provisioned at {lib} — leaving as-is")
    else:
        for report in TSN_LIB_REPORTS:
            n = _copy_tree_hashed(FROZEN["tsn_library"] / report, lib / report,
                                  inventory, f"tsn_library/{report}")
            print(f"  lib {report}: {n} file(s)")
    for side in sides:
        store = root / side / "store"
        out = root / side / "output"
        for env, (src_key, subdirs) in ENV_PROVISION.items():
            # The Everything worker leases each cell's env store as an EXISTING
            # app-owned root (require_existing_owned_dir_lease), so the replica
            # store must be created exactly the way the app creates one.
            if owned_dir.ensure_owned_dir(store / env, kind="store") is None:
                raise SystemExit(f"could not create owned store dir {store / env}")
            for sub in subdirs:
                n = _copy_tree_hashed(FROZEN[src_key] / sub, store / env / sub,
                                      inventory, f"{src_key}/{sub}")
            print(f"  {side}/store/{env}: provisioned {len(subdirs)} subdir(s)")
        day_dir = out / f"{BYDAY_DAY} {BYDAY_SOURCE}"
        src_key, subdirs = ENV_PROVISION["ssor-prod"]
        for sub in subdirs:
            _copy_tree_hashed(FROZEN[src_key] / sub, day_dir / sub,
                              inventory, f"{src_key}/{sub}")
        print(f"  {side}/output/{day_dir.name}: provisioned {len(subdirs)} subdir(s)")
    write_json(root / "results" / "provision.json", {
        "run_id": RUN_ID_DEFAULT, "elapsed_s": round(time.time() - t0, 1),
        "sides": list(sides), "files": inventory, "count": len(inventory)})
    print(f"provision done: {len(inventory)} file(s) in {time.time() - t0:.0f}s")


# --------------------------------------------------------------------------- #
# generate — runs INSIDE the tree under test
# --------------------------------------------------------------------------- #
def _sandbox(tree, root, side):
    scripts = str(Path(tree) / "scripts")
    sys.path.insert(0, scripts)
    import paths, settings, day_matrix  # noqa: E401
    side_root = root / side
    paths.OUTPUT_ROOT = side_root / "output"
    day_matrix.OUTPUT_ROOT = side_root / "output"
    paths.TSN_LIBRARY_ROOT = root / "lib" / "tsn_library"
    cfg = root / "config" / f"config-{side}.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    settings.CONFIG_FILE = cfg
    settings._cache = settings._cache_mtime = None
    (side_root / "output").mkdir(parents=True, exist_ok=True)
    return side_root


def _events(module_events, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "a", encoding="utf-8")

    def on_log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line)
        f.write(line + "\n")
        f.flush()

    return module_events.Events(on_log=on_log, is_cancelled=lambda: False)


def _typed_counts(consolidation_meta, path):
    """The strict typed sidecar read the matrix itself trusts."""
    rec = consolidation_meta.read_comparison_outcome(path)
    if rec is None:
        return {"present": False}
    oc = rec.comparison_outcome
    out = {"present": True, "trusted": bool(rec.trusted),
           "current": bool(rec.current)}
    if oc is not None:
        for k in ("verdict", "completion", "pairing_quality"):
            out[k] = str(getattr(oc, k, None))
        counts = getattr(oc, "counts", None)
        if counts is not None:
            for k in ("known", "paired_rows", "side_a_only_rows",
                      "side_b_only_rows", "differing_rows", "differing_cells",
                      "asserted_cells", "context_cells"):
                out[k] = getattr(counts, k, None)
            out["per_field_counts"] = dict(getattr(counts, "per_field_counts",
                                                   {}) or {})
    gen = getattr(rec, "artifact_generation", None)
    out["generation_id"] = getattr(gen, "generation_id", None)
    return out


def _evidence_state(path):
    """App-free look at one comparison's evidence siblings."""
    p = Path(path)
    wb = p.with_name(f"{p.stem} (evidence){p.suffix}")
    imgs = p.with_name(f"{p.stem} (evidence images)")
    man = p.with_name(f"{p.stem} (evidence).json")
    state = {"workbook": wb.exists(), "images": imgs.is_dir(),
             "manifest": man.exists(), "png_count": 0, "manifest_state": None,
             "read_set": None}
    if state["images"]:
        state["png_count"] = sum(1 for _ in imgs.glob("*.png"))
    if state["manifest"]:
        try:
            payload = json.loads(man.read_text(encoding="utf-8"))
            state["manifest_state"] = payload.get("state")
            state["read_set"] = [m.get("name") for m in payload.get("read_set", [])]
        except (OSError, ValueError) as e:
            state["manifest_state"] = f"unreadable: {type(e).__name__}"
    return state


def phase_generate(root, side, tree, run_id, kinds=None, label=""):
    side_root = _sandbox(tree, root, side)
    import events as events_mod
    import matrix
    import day_matrix
    import owned_dir
    import consolidation_meta
    import tsn_library

    dest = side_root / "store"
    tag = f"{side}-{label}" if label else side
    log_path = root / "logs" / f"generate-{tag}.log"
    ev = _events(events_mod, log_path)
    commit, dirty = tree_stamp(tree)
    results = {"run_id": run_id, "side": side, "tree": str(tree), "label": label,
               "tree_commit": commit, "tree_runtime_dirty": dirty,
               "python": sys.version.split()[0], "cells": [], "started": time.time()}

    def kind_on(kind):
        return kinds is None or kind in kinds

    # The Settings rebuild entry, once per dataset (the owner-plan's "TSN
    # libraries rebuild once"): a dataset with no consolidated workbook is
    # BUILT here — the matrix heals stale libraries but never creates one.
    for report in ("highway_log", "highway_sequence", "intersection_detail",
                   "ramp_detail"):
        try:
            res = tsn_library.build_consolidated(report, events=ev)
            print(f"  tsn build {report}: {res.status} — {res.message}")
        except Exception as e:  # noqa: BLE001 — recorded; cells then refuse
            print(f"  tsn build {report}: EXCEPTION {type(e).__name__}: {e}")

    comparisons_lease = owned_dir.require_owned_dir_lease(
        dest / matrix.COMPARISONS_DIRNAME, kind="comparisons")
    active = {"store": None}

    def target_guard(path=None, *, anchor_path=None, anchor_identity=None,
                     directory_identity=None):
        leases = [x for x in (comparisons_lease, active["store"]) if x is not None]
        if not leases or not all(x.is_current() for x in leases):
            return False
        if path is None:
            return True
        return any(x.is_safe_descendant(
            path, anchor_path=anchor_path, anchor_identity=anchor_identity,
            directory_identity=directory_identity) for x in leases)

    def run_cell(kind, row_key, cell_key, mode_id, fn):
        started = time.time()
        entry = {"kind": kind, "row": row_key, "cell": cell_key, "mode": mode_id}
        print(f"=== {side} · {kind} · {row_key} · {cell_key} · {mode_id} ===")
        try:
            res = fn()
            entry["status"] = res.status
            entry["message"] = getattr(res, "message", "")
            entry["summary_lines"] = list(getattr(res, "summary_lines", ()) or ())
        except Exception as e:  # noqa: BLE001 — recorded, run continues
            entry["status"] = "exception"
            entry["error"] = f"{type(e).__name__}: {e}"
            entry["traceback"] = traceback.format_exc()
            print(entry["traceback"])
        entry["elapsed_s"] = round(time.time() - started, 1)
        results["cells"].append(entry)
        write_json(root / "results" / f"generation-{tag}.json", results)
        return entry

    # 1) Everything vs-TSN cells (evidence toggle ON, worker-parity leases).
    for row in TSN_ROWS if kind_on("everything-tsn") else ():
        def build_tsn(row=row):
            active["store"] = owned_dir.require_existing_owned_dir_lease(
                dest / BASELINE, kind="store")
            try:
                return matrix.build_comparison(
                    str(dest), row, BASELINE, "tsn", BASELINE, events=ev,
                    tsn_files={}, also_formulas=True,
                    evidence=dict(EVIDENCE_REQUEST), commit_guard=target_guard)
            finally:
                active["store"] = None
        entry = run_cell("everything-tsn", row, BASELINE, "tsn", build_tsn)
        cmp_path = (dest / matrix.COMPARISONS_DIRNAME / "tsn"
                    / f"{BASELINE}_{row}_tsn.xlsx")
        entry["comparison_path"] = str(cmp_path)
        entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
        entry["evidence"] = _evidence_state(cmp_path)
        write_json(root / "results" / f"generation-{tag}.json", results)

    # 2) Everything SELF cells (the toggle-driven self decoration).
    for row, mode_id in SELF_CELLS if kind_on("everything-self") else ():
        def build_self(row=row, mode_id=mode_id):
            active["store"] = owned_dir.require_existing_owned_dir_lease(
                dest / BASELINE, kind="store")
            try:
                return matrix.build_comparison(
                    str(dest), row, BASELINE, mode_id, BASELINE, events=ev,
                    tsn_files={}, also_formulas=True,
                    evidence=dict(EVIDENCE_REQUEST), commit_guard=target_guard)
            finally:
                active["store"] = None
        entry = run_cell("everything-self", row, BASELINE, mode_id, build_self)
        cmp_path = (dest / matrix.COMPARISONS_DIRNAME / "tsn"
                    / f"{BASELINE}_{row}_{mode_id}.xlsx")
        entry["comparison_path"] = str(cmp_path)
        entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
        entry["evidence"] = _evidence_state(cmp_path)
        write_json(root / "results" / f"generation-{tag}.json", results)

    # 3) Everything ENV cells — the five PDF-vs-PDF placements (PCOA-FINAL-007).
    #    At base this proves the comparisons run and NO evidence artifact exists;
    #    at head it exercises the new lane end to end.
    for row, other_env in ENV_CELLS if kind_on("everything-env") else ():
        cmp_path = (dest / matrix.COMPARISONS_DIRNAME / BASELINE
                    / f"{other_env}_{row}.xlsx")
        if side == "head":
            # HF-10 criterion 3: the env comparison's counts are identical with
            # evidence on and off. The OFF pass runs FIRST so the final store
            # state (and every evidence binding) belongs to the ON pass.
            def build_env_off(row=row, other_env=other_env):
                return matrix.build_comparison(
                    str(dest), row, other_env, "env", BASELINE, events=ev,
                    tsn_files={}, also_formulas=True,
                    evidence=None, commit_guard=target_guard)
            entry = run_cell("everything-env-off", row, other_env, "env",
                             build_env_off)
            entry["comparison_path"] = str(cmp_path)
            entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
            entry["evidence"] = _evidence_state(cmp_path)
            write_json(root / "results" / f"generation-{tag}.json", results)

        def build_env(row=row, other_env=other_env):
            return matrix.build_comparison(
                str(dest), row, other_env, "env", BASELINE, events=ev,
                tsn_files={}, also_formulas=True,
                evidence=dict(EVIDENCE_REQUEST), commit_guard=target_guard)
        entry = run_cell("everything-env", row, other_env, "env", build_env)
        entry["comparison_path"] = str(cmp_path)
        entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
        entry["evidence"] = _evidence_state(cmp_path)
        write_json(root / "results" / f"generation-{tag}.json", results)

    # 4) By Day vs-TSN cells (no commit guard — the day lane is app-private).
    for row in TSN_ROWS if kind_on("byday") else ():
        def build_day(row=row):
            return day_matrix.build_day_cell(
                BYDAY_SOURCE, BYDAY_DAY, row, str(dest), ev, tsn_files={},
                also_formulas=True, evidence=dict(EVIDENCE_REQUEST))
        entry = run_cell("byday-tsn", row, f"{BYDAY_DAY} {BYDAY_SOURCE}", "tsn",
                         build_day)
        cmp_path = day_matrix.day_out_path(BYDAY_DAY, BYDAY_SOURCE, row)
        entry["comparison_path"] = str(cmp_path)
        entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
        entry["evidence"] = _evidence_state(cmp_path)
        write_json(root / "results" / f"generation-{tag}.json", results)

    # 5) Silent controls: the classic Compare tab result shape is exercised by
    #    the by-day PDF-vs-Excel matrix (same self comparator, no evidence) —
    #    build one PvE cell per family and assert no evidence sibling appears.
    import pdf_excel_matrix
    for fam_row in (("highway_log_pdf", "highway_sequence_pdf",
                     "intersection_detail_pdf", "ramp_detail_pdf")
                    if kind_on("pve") else ()):
        def build_pve(fam_row=fam_row):
            return pdf_excel_matrix.build_pve_cell(
                BYDAY_SOURCE, BYDAY_DAY, fam_row, str(dest), ev,
                also_formulas=False)
        entry = run_cell("pve-byday", fam_row, f"{BYDAY_DAY} {BYDAY_SOURCE}",
                         "vs_excel", build_pve)
        try:
            cmp_path = pdf_excel_matrix.day_out_path(BYDAY_DAY, BYDAY_SOURCE,
                                                     fam_row)
            entry["comparison_path"] = str(cmp_path)
            entry["evidence"] = _evidence_state(cmp_path)
        except Exception as e:  # noqa: BLE001
            entry["path_error"] = f"{type(e).__name__}: {e}"
        write_json(root / "results" / f"generation-{tag}.json", results)

    # 6) Whole-tree evidence sweep: every evidence artifact under the side root,
    #    so absences are proved by enumeration, not assumption.
    hits = sorted(str(p) for p in side_root.rglob("*evidence*"))
    results["evidence_sweep"] = hits
    results["finished"] = time.time()
    results["elapsed_s"] = round(results["finished"] - results["started"], 1)
    write_json(root / "results" / f"generation-{tag}.json", results)
    print(f"generate {side} done in {results['elapsed_s']:.0f}s — "
          f"{len(results['cells'])} cell(s), {len(hits)} evidence path(s)")


# --------------------------------------------------------------------------- #
# census — app-free defect-signature recount (PCOA-FINAL-004/-006)
# --------------------------------------------------------------------------- #
def _workbook_summary_rows(path):
    """(header_line3, legend_texts, [(field, route_key, va, vb)]) from one
    evidence workbook, via openpyxl only."""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Summary"]
        rows = []
        line3 = ""
        for r, row in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
            if r == 3:
                line3 = str(row[0] or "")
            if r >= 6 and row and row[0]:
                field, key = str(row[0]), str(row[1] or "")
                if key.startswith("no verifiable example"):
                    continue
                rows.append((field, key, str(row[2] or ""), str(row[3] or "")))
        legends = []
        for name in wb.sheetnames:
            if name in ("Summary", "Ledger"):
                continue
            ws2 = wb[name]
            for r, row in enumerate(ws2.iter_rows(min_row=2, max_row=2,
                                                  values_only=True), 2):
                if row and row[0]:
                    legends.append(str(row[0]))
                break
        return line3, legends, rows
    finally:
        wb.close()


def _census_one_root(root_dir, label):
    sets = []
    for man in sorted(Path(root_dir).glob("*(evidence).json")):
        stem = man.name[: -len(" (evidence).json")]
        payload = json.loads(man.read_text(encoding="utf-8"))
        read_set = [m.get("name", "") for m in payload.get("read_set", [])]
        entry = {"root": label, "set": stem, "state": payload.get("state"),
                 "read_set_pdf": sum(1 for n in read_set
                                     if n.lower().endswith(".pdf")),
                 "read_set_xlsx": sum(1 for n in read_set
                                      if n.lower().endswith(".xlsx")),
                 "read_set": read_set, "examples": [],
                 "truncated_examples": [], "summary_line3": None,
                 "legends": []}
        wb = man.with_name(f"{stem} (evidence).xlsx")
        if wb.exists():
            line3, legends, rows = _workbook_summary_rows(wb)
            entry["summary_line3"] = line3
            entry["legends"] = sorted(set(legends))
            for field, key, va, vb in rows:
                item = {"field": field, "at": key, "va_len": len(va),
                        "vb_len": len(vb)}
                entry["examples"].append(item)
                # The pre-fix Excel panel draws value[:26] with no ellipsis, so
                # any Excel-side value longer than 26 chars is drawn WRONG.
                if len(va) > 26 or len(vb) > 26:
                    entry["truncated_examples"].append(
                        {"field": field, "at": key, "va": va, "vb": vb})
        sets.append(entry)
    return sets


def phase_cameras(root, side, tree, run_id):
    """The ON-DEMAND per-cell cameras — the other end-user evidence path: the
    Everything vs-TSN camera, the By Day camera, and (at head) the HF-10 env
    camera, each regenerating evidence for an EXISTING comparison under the
    freshness gates."""
    side_root = _sandbox(tree, root, side)
    import events as events_mod
    import matrix
    import day_matrix
    import owned_dir
    dest = side_root / "store"
    ev = _events(events_mod, root / "logs" / f"cameras-{side}.log")
    commit, dirty = tree_stamp(tree)
    results = {"run_id": run_id, "side": side, "tree": str(tree), "cells": [],
               "tree_commit": commit, "tree_runtime_dirty": dirty,
               "started": time.time()}
    lease = owned_dir.require_existing_owned_dir_lease(
        dest / matrix.COMPARISONS_DIRNAME, kind="comparisons")

    def guard(path=None, *, anchor_path=None, anchor_identity=None,
              directory_identity=None):
        if not lease.is_current():
            return False
        if path is None:
            return True
        return lease.is_safe_descendant(
            path, anchor_path=anchor_path, anchor_identity=anchor_identity,
            directory_identity=directory_identity)

    def run(kind, row, cell, fn):
        entry = {"kind": kind, "row": row, "cell": cell}
        print(f"=== camera {side} · {kind} · {row} · {cell} ===")
        started = time.time()
        try:
            res = fn()
            entry["status"] = res.status
            entry["message"] = getattr(res, "message", "")
        except Exception as e:  # noqa: BLE001
            entry["status"] = "exception"
            entry["error"] = f"{type(e).__name__}: {e}"
            entry["traceback"] = traceback.format_exc()
            print(entry["traceback"])
        entry["elapsed_s"] = round(time.time() - started, 1)
        results["cells"].append(entry)
        write_json(root / "results" / f"cameras-{side}.json", results)

    for row in TSN_ROWS:
        run("camera-tsn", row, BASELINE,
            lambda row=row: matrix.evidence_for_cell(
                str(dest), row, BASELINE, BASELINE, ev, tsn_files={},
                commit_guard=guard))
        run("camera-byday", row, f"{BYDAY_DAY} {BYDAY_SOURCE}",
            lambda row=row: day_matrix.evidence_for_day_cell(
                BYDAY_SOURCE, BYDAY_DAY, row, str(dest), ev, tsn_files={}))
    if side == "head":
        for row, other_env in ENV_CELLS:
            run("camera-env", row, other_env,
                lambda row=row, other_env=other_env: matrix.evidence_for_cell(
                    str(dest), row, other_env, BASELINE, ev, tsn_files={},
                    commit_guard=guard, mode_id="env"))
    results["elapsed_s"] = round(time.time() - results["started"], 1)
    write_json(root / "results" / f"cameras-{side}.json", results)


def _summary_rows_of(wb_path):
    """App-free read of one evidence workbook: (source_lines, legends,
    example rows [(field, at, va, vb)], has_ledger)."""
    from openpyxl import load_workbook
    wb = load_workbook(wb_path, read_only=True, data_only=True)
    try:
        ws = wb["Summary"]
        src_lines, rows = [], []
        for r, row in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
            if r in (3, 4) and row and row[0]:
                src_lines.append(str(row[0]))
            if r >= 7 and row and row[0]:
                key = str(row[1] or "")
                if key.startswith("no verifiable example"):
                    continue
                rows.append((str(row[0]), key, str(row[2] or ""),
                             str(row[3] or "")))
        legends = []
        for name in wb.sheetnames:
            if name in ("Summary", "Ledger"):
                continue
            for row in wb[name].iter_rows(min_row=2, max_row=2,
                                          values_only=True):
                if row and row[0]:
                    legends.append(str(row[0]))
                break
        return src_lines, sorted(set(legends)), rows, "Ledger" in wb.sheetnames
    finally:
        wb.close()


def phase_counts(root, side, tree, run_id):
    """Re-read every placement's strict typed sidecar into one counts table —
    the base/head invariance record and the audit-count cross-check."""
    side_root = _sandbox(tree, root, side)
    import consolidation_meta
    import day_matrix
    store = side_root / "store"
    commit, dirty = tree_stamp(tree)
    out = {"run_id": run_id, "side": side, "tree": str(tree),
           "tree_commit": commit, "tree_runtime_dirty": dirty, "cells": {}}
    for row in TSN_ROWS:
        p = store / "comparisons" / "tsn" / f"{BASELINE}_{row}_tsn.xlsx"
        out["cells"][f"everything-tsn|{row}"] = _typed_counts(
            consolidation_meta, p)
    for row, mode_id in SELF_CELLS:
        p = store / "comparisons" / "tsn" / f"{BASELINE}_{row}_{mode_id}.xlsx"
        out["cells"][f"everything-self|{row}|{mode_id}"] = _typed_counts(
            consolidation_meta, p)
    for row, other_env in ENV_CELLS:
        p = store / "comparisons" / BASELINE / f"{other_env}_{row}.xlsx"
        out["cells"][f"everything-env|{row}"] = _typed_counts(
            consolidation_meta, p)
    for row in TSN_ROWS:
        p = day_matrix.day_out_path(BYDAY_DAY, BYDAY_SOURCE, row)
        out["cells"][f"byday|{row}"] = _typed_counts(consolidation_meta, p)
    write_json(root / "results" / f"counts-{side}.json", out)


def phase_validate(root, side, tree, run_id):
    """The programmatic 100 % validation over every retained head evidence set:
    manifest member integrity, exact-source read-set binding against each
    comparison's own provenance, truthful source lines + legends, panel-text
    fidelity census, env geometry re-derivation, and the silent-lane sweep."""
    side_root = _sandbox(tree, root, side)
    import compare_env
    import compare_tsn_common as ctc
    import evidence_manifest as em
    import visual_evidence as ve

    problems = []
    commit, dirty = tree_stamp(tree)
    out = {"run_id": run_id, "side": side, "tree": str(tree),
           "tree_commit": commit, "tree_runtime_dirty": dirty, "sets": [],
           "problems": problems}

    def note(setrec, cond, what):
        setrec.setdefault("checks", []).append(
            {"ok": bool(cond), "what": what})
        if not cond:
            problems.append(f"{setrec['comparison']}: {what}")

    def validate_set(cmp_path, flavor, row_key=None):
        man_path = em.manifest_path(cmp_path)
        rec = {"comparison": str(cmp_path), "flavor": flavor,
               "manifest": man_path.exists()}
        out["sets"].append(rec)
        if not man_path.exists():
            note(rec, False, "manifest missing")
            return
        man = em.read(man_path)
        rec["state"] = man.state
        desc = em.describe(cmp_path, verify_members=True)
        note(rec, desc["status"] == em.CURRENT,
             f"manifest describes CURRENT (got {desc['status']})")
        prov = ctc.read_comparison_provenance(cmp_path)
        note(rec, isinstance(prov, dict), "provenance sidecar present")
        if not isinstance(prov, dict):
            return
        sides = prov["inputs"]
        members = list(man.read_set)
        if flavor == "env":
            resolved = []
            for s in sides:
                d, _files = compare_env._find_input_dir(
                    Path(s["selection"]), row_key, "*.pdf")
                census = {m["name"]: (m["size"], m["mtime_ns"])
                          for m in s.get("members", [])}
                resolved.append((Path(d).resolve(), census))
            for m in members:
                mp = Path(m.name)
                parent = mp.resolve().parent
                match = next((c for d, c in resolved if parent == d), None)
                st = mp.stat() if mp.is_file() else None
                note(rec, match is not None,
                     f"read-set member under a compared side dir: {mp.name}")
                note(rec, st is not None and match is not None
                     and match.get(mp.name) == (st.st_size, st.st_mtime_ns),
                     f"read-set member in that side's census: {mp.name}")
        elif man.state == em.STATE_RENDERED:
            want = {str(Path(s["selection"]).resolve()): s["sha256"]
                    for s in sides}
            got = {str(Path(m.name).resolve()): m.sha256 for m in members}
            note(rec, got == want,
                 "read set == the comparison's two recorded documents "
                 f"(got {len(got)} member(s))")
        else:
            # A generation that rendered nothing (no differences to
            # illustrate) opened no source document, so its read set is
            # EMPTY by construction — requiring the two documents here would
            # demand a claim the generation never made. The state itself is
            # the assertion, and it is checked above via em.describe.
            note(rec, not members,
                 f"a non-rendered generation ({man.state}) claims no read "
                 f"set (got {len(members)} member(s))")
        if man.state != em.STATE_RENDERED:
            return
        wb_path = ve.sibling_paths(cmp_path)[0]
        src_lines, legends, rows, has_ledger = _summary_rows_of(wb_path)
        note(rec, has_ledger, "Ledger sheet present")
        want_lines = [f"Compared {s['role']}: {s['selection']}" for s in sides]
        note(rec, src_lines == want_lines,
             f"source lines are the provenance selections ({src_lines!r})")
        want_legend = ve._legend_for(
            ve.FLAVOR_ENV if flavor == "env" else ve.FLAVOR_TSN)
        note(rec, all(lg == want_legend for lg in legends),
             "image-sheet legends state the true sources")
        rec["examples"] = len(rows)
        # Panel-text fidelity census: values past the panel bound draw as a
        # visibly elided prefix (panel_cell_text) — legal under HF-05, so the
        # over-limit examples are LISTED for the native-scale image inspection
        # rather than failed; the drawn-string decision itself is unit-locked
        # in check_visual_evidence.
        rec["elided_examples"] = [
            [f, a] for f, a, va, vb in rows
            if len(va) > ve.PANEL_TEXT_MAX or len(vb) > ve.PANEL_TEXT_MAX]
        rec["values_over_26"] = sum(
            1 for _f, _a, va, vb in rows for v in (va, vb) if len(v) > 26)
        if flavor == "env":
            adapter = ve.env_adapter_for(row_key)
            rederived = 0
            for field, at, va, vb in rows:
                route, _, key = at.partition(" @ ")
                key = key or route
                vals = []
                boxes_ok = True
                for d, _census in resolved:
                    pdf = adapter.tsmis_pdf_path(d, route)
                    recs = adapter.env_locate(Path(pdf), {key})
                    got_recs = recs.get(key) or recs.get(route) or []
                    if len(got_recs) != 1:
                        boxes_ok = False
                        break
                    r0 = got_recs[0]
                    box = adapter.env_box(r0, field)
                    if box is None:
                        boxes_ok = False
                        break
                    _pg, cell, yspan, _xs = box
                    if cell[1] < yspan[0] - 3 or cell[3] > yspan[1] + 3:
                        boxes_ok = False
                        break
                    vals.append(adapter.env_value(r0, field))
                match = (boxes_ok and (vals[0] or "") == va
                         and (vals[1] or "") == vb)
                note(rec, match, f"env re-derivation matches ({field} @ {at})")
                rederived += bool(match)
            rec["env_rederived"] = rederived
        return

    store = side_root / "store"
    tsn_dir = store / "comparisons" / "tsn"
    for man in sorted(tsn_dir.glob("*(evidence).json")):
        cmp_path = man.with_name(man.name.replace(" (evidence).json", ".xlsx"))
        flavor = ("self" if "_vs_pdf" in cmp_path.name
                  or "_vs_excel" in cmp_path.name else "tsn")
        validate_set(cmp_path, flavor)
    for row_key, other_env in ENV_CELLS:
        cmp_path = (store / "comparisons" / BASELINE
                    / f"{other_env}_{row_key}.xlsx")
        if em.manifest_path(cmp_path).exists() or cmp_path.exists():
            validate_set(cmp_path, "env", row_key=row_key)
    byday = (side_root / "output" / "comparisons" / "tsn-by-day"
             / f"{BYDAY_DAY} {BYDAY_SOURCE}")
    for man in sorted(byday.glob("*(evidence).json")):
        cmp_path = man.with_name(man.name.replace(" (evidence).json", ".xlsx"))
        validate_set(cmp_path, "tsn")
    # The silent lanes: nothing evidence-like anywhere under the PvE tree.
    pve_tree = side_root / "output" / "comparisons" / "pdf-vs-excel-by-day"
    stray = sorted(str(p) for p in pve_tree.rglob("*evidence*")) if pve_tree.is_dir() else []
    out["pve_stray"] = stray
    if stray:
        problems.append(f"PvE tree holds evidence artifacts: {stray}")
    out["problem_count"] = len(problems)
    write_json(root / "results" / f"validate-{side}.json", out)
    print(f"validate {side}: {len(out['sets'])} set(s), "
          f"{len(problems)} problem(s)")
    if problems:
        for p in problems[:20]:
            print("  PROBLEM:", p)
        raise SystemExit(1)


def phase_excel(root, side, tree, run_id):
    """Open every retained evidence workbook in INSTALLED Excel: it must open
    clean (no repair), with its image sheets and Ledger intact."""
    side_root = _sandbox(tree, root, side)
    import win32com.client  # type: ignore
    books = sorted((side_root / "store" / "comparisons").rglob("*(evidence).xlsx"))
    books += sorted((side_root / "output" / "comparisons").rglob("*(evidence).xlsx"))
    commit, dirty = tree_stamp(tree)
    out = {"run_id": run_id, "side": side, "tree": str(tree),
           "tree_commit": commit, "tree_runtime_dirty": dirty,
           "books": [], "problems": []}
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        for b in books:
            entry = {"path": str(b)}
            try:
                wb = excel.Workbooks.Open(str(b), UpdateLinks=0, ReadOnly=True,
                                          CorruptLoad=0)
                sheets = [s.Name for s in wb.Sheets]
                entry["sheets"] = len(sheets)
                entry["has_ledger"] = "Ledger" in sheets
                entry["pictures"] = sum(
                    wb.Sheets(n).Shapes.Count for n in sheets
                    if n not in ("Summary", "Ledger"))
                wb.Close(SaveChanges=False)
                entry["opened"] = True
            except Exception as e:  # noqa: BLE001
                entry["opened"] = False
                entry["error"] = f"{type(e).__name__}: {e}"
                out["problems"].append(str(b))
            out["books"].append(entry)
            print(f"  excel {b.name}: opened={entry.get('opened')} "
                  f"sheets={entry.get('sheets')} pics={entry.get('pictures')}")
    finally:
        excel.Quit()
    write_json(root / "results" / f"excel-{side}.json", out)
    if out["problems"]:
        raise SystemExit(1)


def phase_checks_at_base(root, tree, head_tree):
    """Run the HEAD's extended evidence checks against the BASE scripts tree —
    the red half of red→green. Every new assertion must fail there with the
    recorded defect signature; the head run of the same files must pass."""
    import subprocess
    base_tree = Path(tree)
    checks = ("check_visual_evidence.py", "check_evidence_source_role.py",
              "check_evidence_manifest.py", "check_evidence_excel_columns.py",
              "check_evidence_literal_cells.py", "check_matrix.py",
              "check_pdf_excel_matrix.py")
    stage = root / "base-red"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    # The checks resolve scripts/ relative to their own location, so the stage
    # mirrors the tree: the BASE runtime (scripts + version.py) with only the
    # HEAD's check files overlaid into the base build/.
    shutil.copytree(base_tree / "scripts", stage / "scripts")
    shutil.copyfile(base_tree / "version.py", stage / "version.py")
    build_dir = stage / "build"
    shutil.copytree(base_tree / "build", build_dir)
    for name in checks + ("_checklib.py",):
        shutil.copyfile(Path(head_tree) / "build" / name, build_dir / name)
    commit, dirty = tree_stamp(head_tree)
    out = {"base_tree": str(base_tree), "head_tree": str(head_tree),
           "head_tree_commit": commit, "head_tree_runtime_dirty": dirty,
           "results": {}}
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for name in checks:
        proc = subprocess.run(
            [sys.executable, str(build_dir / name)], cwd=str(stage),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env)
        fails = [ln for ln in (proc.stdout or "").splitlines()
                 if "FAIL" in ln][:40]
        tail = (proc.stdout or "").splitlines()[-8:]
        err_tail = (proc.stderr or "").splitlines()[-6:]
        out["results"][name] = {"exit": proc.returncode, "fail_lines": fails,
                                "stdout_tail": tail, "stderr_tail": err_tail}
        print(f"  base-red {name}: exit={proc.returncode} "
              f"({len(fails)} FAIL line(s))")
    write_json(root / "results" / "base-red-checks.json", out)


def phase_census(root):
    out = {"audit_everything": _census_one_root(AUDIT_EVERYTHING,
                                                "audit-everything"),
           "audit_byday": _census_one_root(AUDIT_BYDAY, "audit-byday"),
           "base_everything": [], "base_byday": []}
    base_tsn = root / "base" / "store" / "comparisons" / "tsn"
    if base_tsn.is_dir():
        out["base_everything"] = _census_one_root(base_tsn, "base-everything")
    base_byday = (root / "base" / "output" / "comparisons" / "tsn-by-day"
                  / f"{BYDAY_DAY} {BYDAY_SOURCE}")
    if base_byday.is_dir():
        out["base_byday"] = _census_one_root(base_byday, "base-byday")
    for key in list(out):
        sets = out[key]
        out[f"{key}_totals"] = {
            "sets": len(sets),
            "examples": sum(len(s["examples"]) for s in sets),
            "truncated": sum(len(s["truncated_examples"]) for s in sets),
            "sets_with_pdf_read_members": sum(
                1 for s in sets if s["read_set_pdf"]),
        }
    write_json(root / "results" / "prefix-defect-census.json", out)


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=RUN_ID_DEFAULT)
    ap.add_argument("--phase", required=True,
                    choices=("provision", "generate", "cameras", "census",
                             "checks-at-base", "validate", "excel", "counts"))
    ap.add_argument("--side", choices=("base", "head"),
                    help="generate: which acceptance side to run")
    ap.add_argument("--tree", default=str(REPO),
                    help="generate: the scripts tree under test")
    ap.add_argument("--root", default=str(ROOT_DEFAULT))
    ap.add_argument("--cells", default="",
                    help="generate: comma list of cell kinds to run "
                         "(everything-tsn,everything-self,everything-env,"
                         "byday,pve); empty = all")
    ap.add_argument("--label", default="",
                    help="generate: suffix for the results/log files so a "
                         "partial re-run never clobbers a prior record")
    args = ap.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = Tee(root / "logs" / f"driver-{args.phase}"
                                  f"{('-' + args.side) if args.side else ''}.log")
    print(f"— run_rb4_acceptance {args.run_id} · phase={args.phase}"
          f" side={args.side} tree={args.tree} at {time.strftime('%F %T')}")
    if args.phase == "provision":
        phase_provision(root, ("base", "head"), Path(args.tree))
    elif args.phase == "generate":
        if not args.side:
            ap.error("--side is required for generate")
        kinds = tuple(k for k in args.cells.split(",") if k) or None
        phase_generate(root, args.side, Path(args.tree), args.run_id,
                       kinds=kinds, label=args.label)
    elif args.phase == "cameras":
        if not args.side:
            ap.error("--side is required for cameras")
        phase_cameras(root, args.side, Path(args.tree), args.run_id)
    elif args.phase == "census":
        phase_census(root)
    elif args.phase == "checks-at-base":
        phase_checks_at_base(root, Path(args.tree), REPO)
    elif args.phase == "counts":
        if not args.side:
            ap.error("--side is required for counts")
        phase_counts(root, args.side, Path(args.tree), args.run_id)
    elif args.phase == "validate":
        if not args.side:
            ap.error("--side is required for validate")
        phase_validate(root, args.side, Path(args.tree), args.run_id)
    elif args.phase == "excel":
        if not args.side:
            ap.error("--side is required for excel")
        phase_excel(root, args.side, Path(args.tree), args.run_id)
    print(f"— phase {args.phase} complete at {time.strftime('%F %T')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

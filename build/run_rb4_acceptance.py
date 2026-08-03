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
SELF_CELLS = tuple((r, "vs_pdf" if not r.endswith("_pdf") else "vs_excel")
                   for r in TSN_ROWS)
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
        for k in ("verdict", "completion", "paired", "only_a", "only_b",
                  "diff_rows", "diff_cells", "pairing_quality"):
            out[k] = getattr(oc, k, None)
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


def phase_generate(root, side, tree, run_id):
    side_root = _sandbox(tree, root, side)
    import events as events_mod
    import matrix
    import day_matrix
    import owned_dir
    import consolidation_meta

    dest = side_root / "store"
    log_path = root / "logs" / f"generate-{side}.log"
    ev = _events(events_mod, log_path)
    results = {"run_id": run_id, "side": side, "tree": str(tree),
               "python": sys.version.split()[0], "cells": [], "started": time.time()}

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
        write_json(root / "results" / f"generation-{side}.json", results)
        return entry

    # 1) Everything vs-TSN cells (evidence toggle ON, worker-parity leases).
    for row in TSN_ROWS:
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
        write_json(root / "results" / f"generation-{side}.json", results)

    # 2) Everything SELF cells (the toggle-driven self decoration).
    for row, mode_id in SELF_CELLS:
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
        write_json(root / "results" / f"generation-{side}.json", results)

    # 3) Everything ENV cells — the five PDF-vs-PDF placements (PCOA-FINAL-007).
    #    At base this proves the comparisons run and NO evidence artifact exists;
    #    at head it exercises the new lane end to end.
    for row, other_env in ENV_CELLS:
        def build_env(row=row, other_env=other_env):
            return matrix.build_comparison(
                str(dest), row, other_env, "env", BASELINE, events=ev,
                tsn_files={}, also_formulas=True,
                evidence=dict(EVIDENCE_REQUEST), commit_guard=target_guard)
        entry = run_cell("everything-env", row, other_env, "env", build_env)
        cmp_path = (dest / matrix.COMPARISONS_DIRNAME / BASELINE
                    / f"{other_env}_{row}.xlsx")
        entry["comparison_path"] = str(cmp_path)
        entry["typed"] = _typed_counts(consolidation_meta, cmp_path)
        entry["evidence"] = _evidence_state(cmp_path)
        write_json(root / "results" / f"generation-{side}.json", results)

    # 4) By Day vs-TSN cells (no commit guard — the day lane is app-private).
    for row in TSN_ROWS:
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
        write_json(root / "results" / f"generation-{side}.json", results)

    # 5) Silent controls: the classic Compare tab result shape is exercised by
    #    the by-day PDF-vs-Excel matrix (same self comparator, no evidence) —
    #    build one PvE cell per family and assert no evidence sibling appears.
    import pdf_excel_matrix
    for fam_row in ("highway_log", "highway_sequence", "intersection_detail",
                    "ramp_detail"):
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
        write_json(root / "results" / f"generation-{side}.json", results)

    # 6) Whole-tree evidence sweep: every evidence artifact under the side root,
    #    so absences are proved by enumeration, not assumption.
    hits = sorted(str(p) for p in side_root.rglob("*evidence*"))
    results["evidence_sweep"] = hits
    results["finished"] = time.time()
    results["elapsed_s"] = round(results["finished"] - results["started"], 1)
    write_json(root / "results" / f"generation-{side}.json", results)
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
                    choices=("provision", "generate", "census"))
    ap.add_argument("--side", choices=("base", "head"),
                    help="generate: which acceptance side to run")
    ap.add_argument("--tree", default=str(REPO),
                    help="generate: the scripts tree under test")
    ap.add_argument("--root", default=str(ROOT_DEFAULT))
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
        phase_generate(root, args.side, Path(args.tree), args.run_id)
    elif args.phase == "census":
        phase_census(root)
    print(f"— phase {args.phase} complete at {time.strftime('%F %T')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

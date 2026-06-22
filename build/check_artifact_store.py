"""CT-4 / CT-5 / CT-8 / CT-8b + fingerprint — the transactional artifact lifecycle
(scripts/artifact_store.py, P2).

Exercises the leaf module's three concerns with fault injection — NOT just happy paths:
  * atomic single-file write (CT-8): an interrupted/failed write never truncates a prior
    good artifact; no temp-name leak;
  * multi-file commit (CT-8b / R1-T02): values-canonical / formulas-best-effort; a 1st
    (values) or 2nd (formulas) save failure leaves the right state; no temp name surfaces
    in the result; overwrite-confirm honored against the FINAL path;
  * journaled store promotion + startup recovery (CT-4 / CT-5 / R1-T01): validate-before-
    commit, restore-from-backup on a death between renames, clean stale residue,
    idempotent;
  * input fingerprint (R1-R03): a DELETED file changes the identity (which a newest-mtime
    signal misses); missing/corrupt sidecar => stale.

Real openpyxl (a valid workbook is what `commit_workbook` validates); no browser/network.
Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_artifact_store.py
"""
import contextlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]   # scripts + repo root (updater -> version)

import artifact_store as a            # noqa: E402
from events import ConsolidateResult  # noqa: E402
from openpyxl import Workbook         # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


# Ownership predicate for recover_promotions (P2-B04). The MECHANICS tests seed their own
# store roots, so they accept all shape-valid journals; the ownership test passes a realistic one.
def _OWN_ALL(_store_root, _target):
    return True


@contextlib.contextmanager
def _patch(obj, attr, value):
    sentinel = object()
    old = getattr(obj, attr, sentinel)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        if old is sentinel:
            delattr(obj, attr)
        else:
            setattr(obj, attr, value if False else old)


class _OsShim:
    """A stand-in for artifact_store's `os` whose `replace` raises for a target path
    substring; everything else delegates to the real os (scoped to artifact_store)."""
    def __init__(self, fail_substr):
        self._fail = fail_substr

    def replace(self, src, dst):
        if self._fail and self._fail in str(dst):
            raise OSError(13, "simulated locked destination")
        return os.replace(src, dst)

    def __getattr__(self, name):
        return getattr(os, name)


def _xlsx(path, sheet=None):
    wb = Workbook()
    if sheet:
        wb.active.title = sheet
    wb.active["A1"] = "x"
    wb.save(str(path))


def _malformed_xlsx(path):
    """A ZIP that CONTAINS ``xl/workbook.xml`` (so a name-only check would pass) but whose
    workbook part is not valid XML — openpyxl cannot open it (the P2-B05 repro)."""
    import zipfile
    with zipfile.ZipFile(str(path), "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/workbook.xml", b"not xml")


def _workbook_with_bad_sheet(path):
    """A valid XLSX (valid ZIP + valid workbook.xml) whose ``xl/worksheets/sheet1.xml`` is
    corrupt XML — only OPENING the workbook detects it (the P2-R04 repro)."""
    import zipfile
    good = Path(str(path) + ".good.xlsx")
    _xlsx(good, sheet="Comparison")
    with zipfile.ZipFile(good) as zin:
        data = {n: zin.read(n) for n in zin.namelist()}
    member = next(n for n in data if n.startswith("xl/worksheets/") and n.endswith(".xml"))
    data[member] = b"<worksheet><unclosed"
    with zipfile.ZipFile(str(path), "w") as zout:
        for n, d in data.items():
            zout.writestr(n, d)
    good.unlink()


@contextlib.contextmanager
def _fail_rename_when(should_fail):
    """Temporarily make ``Path.rename`` raise for (self, target) pairs matching
    `should_fail`, delegating otherwise — to drive the rollback/recovery failure paths."""
    orig = Path.rename

    def _r(self, target):
        if should_fail(self, Path(target)):
            raise OSError(13, "simulated rename failure")
        return orig(self, target)
    Path.rename = _r
    try:
        yield
    finally:
        Path.rename = orig


def _no_temp_leak(folder):
    return not any(".tmp-" in p.name for p in Path(folder).iterdir())


# --------------------------------------------------------------------------- #
def test_atomic_save(tmp):                                    # CT-8
    print("CT-8 atomic_save — an interrupted write never truncates the prior file:")
    d = tmp / "atomic"; d.mkdir()
    final = d / "out.xlsx"
    _xlsx(final)
    prior = final.read_bytes()

    # A failed os.replace (destination locked) must leave the prior file intact + raise.
    wb = Workbook(); wb.active["A1"] = "new"
    raised = False
    with _patch(a, "os", _OsShim("out.xlsx")):
        try:
            a.atomic_save(wb, final)
        except OSError:
            raised = True
    check("a failed replace raises", raised)
    check("...the prior workbook is byte-for-byte preserved", final.read_bytes() == prior)
    check("...no temp file leaked", _no_temp_leak(d))

    # A clean save replaces atomically.
    wb2 = Workbook(); wb2.active["A1"] = "fresh"
    a.atomic_save(wb2, final)
    check("a clean save replaces the file", final.exists() and final.read_bytes() != prior)
    check("...still no temp leak", _no_temp_leak(d))


def test_commit_single(tmp):                                  # CT-8 (single-file commit)
    print("CT-8 commit_workbook (single) — validate + rewrite + preserve-on-failure:")
    d = tmp / "single"; d.mkdir()
    final = d / "cmp.xlsx"

    def produce_ok(t):
        _xlsx(t)
        return ConsolidateResult(status="ok", output_path=str(t),
                                 summary_lines=[f"Values file: {t}"])
    res = a.commit_workbook(final, produce_ok)
    check("status ok", res.status == "ok")
    check("output_path rewritten to the FINAL name (no temp)",
          res.output_path == str(final) and ".tmp-" not in res.output_path)
    check("summary line rewritten (no temp name)",
          all(".tmp-" not in s for s in res.summary_lines) and str(final) in res.summary_lines[0])
    check("the workbook exists at the final path", final.exists())
    check("no temp leak", _no_temp_leak(d))

    # A producer that writes an INVALID file is rejected (not committed over a prior).
    _xlsx(final); prior = final.read_bytes()

    def produce_garbage(t):
        Path(t).write_text("not a workbook")
        return ConsolidateResult(status="ok", output_path=str(t))
    res = a.commit_workbook(final, produce_garbage)
    check("an invalid produced workbook -> error result", res.status == "error")
    check("...the prior file is preserved", final.read_bytes() == prior)
    check("...no temp leak", _no_temp_leak(d))

    # A producer that returns a non-ok result commits nothing.
    def produce_err(t):
        _xlsx(t)
        return ConsolidateResult(status="error", message="boom")
    res = a.commit_workbook(final, produce_err)
    check("a non-ok producer result is returned untouched", res.status == "error")
    check("...the prior file is still preserved", final.read_bytes() == prior)
    check("...no temp leak", _no_temp_leak(d))

    # Overwrite confirm is checked against the FINAL path (declined -> cancelled).
    def produce_should_not_run(t):
        produce_should_not_run.ran = True            # noqa
        _xlsx(t)
        return ConsolidateResult(status="ok", output_path=str(t))
    produce_should_not_run.ran = False
    res = a.commit_workbook(final, produce_should_not_run, confirm_overwrite=lambda _p: False)
    check("confirm declined on an existing final -> cancelled", res.status == "cancelled")
    check("...the producer never ran", produce_should_not_run.ran is False)
    check("...the prior file is preserved", final.read_bytes() == prior)


def test_commit_twin(tmp):                                    # CT-8b / R1-T02
    print("CT-8b commit_workbook (mode=both) — values-canonical, formulas best-effort:")
    d = tmp / "twin"; d.mkdir()
    final = d / "cmp.xlsx"                            # the picked name = formulas primary
    final_values = a._values_twin(final)

    def produce_both(t):
        _xlsx(t)                                      # formulas (primary)
        _xlsx(a._values_twin(t))                      # values twin
        return ConsolidateResult(status="ok", output_path=str(t),
                                 summary_lines=[f"Live-formulas file: {t}",
                                                f"Values file: {a._values_twin(t)}"])

    # Happy path: both committed; BOTH returned paths rewritten; no temp leak.
    res = a.commit_workbook(final, produce_both, twin=True)
    check("status ok", res.status == "ok")
    check("formulas committed to the picked name", final.exists())
    check("values committed to the (values) sibling", final_values.exists())
    check("output_path rewritten (formulas final, no temp)",
          res.output_path == str(final) and ".tmp-" not in res.output_path)
    check("both summary paths rewritten (no temp names)",
          all(".tmp-" not in s for s in res.summary_lines)
          and any(str(final_values) in s for s in res.summary_lines))
    check("no temp leak", _no_temp_leak(d))

    # 1st save fails: the VALUES (transactional) commit fails -> error, prior kept, no leak.
    _xlsx(final); _xlsx(final_values)
    pf, pv = final.read_bytes(), final_values.read_bytes()
    with _patch(a, "os", _OsShim("(values)")):
        res = a.commit_workbook(final, produce_both, twin=True)
    check("values-commit failure -> error result", res.status == "error")
    check("...the prior values workbook is preserved", final_values.read_bytes() == pv)
    check("...the prior formulas workbook is preserved (untouched)", final.read_bytes() == pf)
    check("...no temp leak (both temps cleaned)", _no_temp_leak(d))

    # 2nd save fails: values commits; the FORMULAS sibling is best-effort -> ok, no leak.
    final.unlink(); final_values.unlink()
    with _patch(a, "os", _OsShim("cmp.xlsx")):       # fail only the formulas (picked-name) replace
        res = a.commit_workbook(final, produce_both, twin=True)
    check("formulas-commit failure -> still ok (values is canonical)", res.status == "ok")
    check("...the values workbook IS committed", final_values.exists())
    check("...the formulas workbook is NOT present (best-effort skipped)", not final.exists())
    check("...no temp leak", _no_temp_leak(d))


def test_fingerprint(tmp):                                    # CT-6 (unit) / R1-R03
    print("fingerprint — identity over (name,size,mtime); a DELETE changes it:")
    store = tmp / "store"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"a" * 10)
    (store / "r2.xlsx").write_bytes(b"b" * 20)
    fp0 = a.fingerprint(store)
    check("stable across calls", a.fingerprint(store) == fp0)

    (store / "r3.xlsx").write_bytes(b"c" * 5)
    fp_add = a.fingerprint(store)
    check("adding a file changes the fingerprint", fp_add != fp0)

    (store / "r3.xlsx").unlink()
    check("removing it returns to the original", a.fingerprint(store) == fp0)

    (store / "r2.xlsx").write_bytes(b"b" * 21)        # resize
    check("resizing a file changes the fingerprint", a.fingerprint(store) != fp0)

    check("excludes ~$ lock / .outcome.json / .fingerprint.json siblings",
          (lambda: ((store / "~$r1.xlsx").write_bytes(b"x"),
                    (store / "r1.xlsx.outcome.json").write_text("{}"),
                    a.fingerprint(store) == a.fingerprint(store))[-1])())
    check("an absent folder -> the UNREADABLE sentinel (caller rebuilds)",
          a.fingerprint(tmp / "nope") == a._UNREADABLE)


def test_consolidated_fresh(tmp):                             # CT-6 (the freshness gate)
    print("consolidated_fresh — a deleted route reads STALE (newest-mtime missed it):")
    store = tmp / "cstore"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"a" * 10)
    (store / "r2.xlsx").write_bytes(b"b" * 20)
    (store / "r3.xlsx").write_bytes(b"c" * 30)
    consolidated = tmp / "combined.xlsx"
    _xlsx(consolidated)

    check("no sidecar yet -> stale (legacy/one-time migration)",
          a.consolidated_fresh(consolidated, store) is False)
    a.write_consolidated_fingerprint(consolidated, store)
    check("after recording the fingerprint -> fresh", a.consolidated_fresh(consolidated, store))

    # Delete a NON-newest route: newest-mtime is unchanged, but identity changed.
    (store / "r1.xlsx").unlink()
    check("a DELETED route -> stale (the F5 fix)",
          a.consolidated_fresh(consolidated, store) is False)

    # Re-record, then a missing workbook is stale regardless of the sidecar.
    a.write_consolidated_fingerprint(consolidated, store)
    check("re-recorded -> fresh again", a.consolidated_fresh(consolidated, store))
    consolidated.unlink()
    check("a missing consolidated workbook -> stale", a.consolidated_fresh(consolidated, store) is False)
    _xlsx(consolidated)

    # A corrupt sidecar reads stale (never a false-fresh).
    a.write_consolidated_fingerprint(consolidated, store)
    a._fp_sidecar(consolidated).write_text("{ not json")
    check("a corrupt fingerprint sidecar -> stale", a.consolidated_fresh(consolidated, store) is False)


def _seed_store(parent, name="live", files=("r1.xlsx", "r2.xlsx")):
    d = parent / name
    d.mkdir(parents=True)
    for f in files:
        (d / f).write_bytes(b"data-" + f.encode())
    return d


def test_promote_validate(tmp):                               # CT-5
    print("CT-5 promote_store — validate before commit; locked live keeps last-good:")
    base = tmp / "p_validate"; base.mkdir()
    live = _seed_store(base, "live")
    prior = sorted(p.name for p in live.iterdir())

    # Empty staging is never promoted.
    empty_stage = base / "live.staging"; empty_stage.mkdir()
    check("empty staging -> not promoted", a.promote_store(live, empty_stage) is False)
    check("...live preserved", sorted(p.name for p in live.iterdir()) == prior)
    check("...empty staging cleaned", not empty_stage.exists())

    # Missing staging is never promoted.
    check("missing staging -> not promoted", a.promote_store(live, base / "gone.staging") is False)
    check("...live still preserved", sorted(p.name for p in live.iterdir()) == prior)

    # A locked live (the live->backup rename fails) keeps last-good, discards staging.
    stage = base / "live.staging2"; stage.mkdir()
    (stage / "new.xlsx").write_bytes(b"new")
    with _patch(a, "os", _OsShim("")):               # os passthrough; force the rename to fail
        orig_rename = Path.rename

        def _locked_rename(self, target):
            if self.name == "live" and ".bak-" in Path(target).name:
                raise OSError(13, "live locked")
            return orig_rename(self, target)
        with _patch(Path, "rename", _locked_rename):
            ok = a.promote_store(live, stage)
    check("a locked live -> not promoted (kept)", ok is False)
    check("...live still has the ORIGINAL files", sorted(p.name for p in live.iterdir()) == prior)
    check("...staging discarded", not stage.exists())

    # Clean promotion when nothing blocks it.
    stage3 = base / "live.staging3"; stage3.mkdir()
    (stage3 / "fresh.xlsx").write_bytes(b"fresh")
    check("a clean promotion succeeds", a.promote_store(live, stage3) is True)
    check("...live now holds the staged content", (live / "fresh.xlsx").exists()
          and not (live / "r1.xlsx").exists())
    # The journal FILE and backup are gone; the (possibly shared) empty `.promote` dir is
    # left for recover_promotions to rmdir (sibling stores share it — rmdir'ing it
    # mid-promotion would race a concurrent journal write).
    check("...no backup / journal residue left",
          not any(".bak-" in p.name for p in base.iterdir())
          and not list((base / ".promote").glob("*.json")))


def test_recovery(tmp):                                       # CT-4 / R1-T01
    print("CT-4 recover_promotions — seed each dead-process state; recovery repairs it:")
    import json

    # State A: death BETWEEN the renames — live missing, backup present, journal present.
    base = tmp / "rec_a"; base.mkdir()
    backup = _seed_store(base, "live.bak-tok")
    stage = base / "live.staging"; stage.mkdir(); (stage / "x").write_bytes(b"x")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "tok.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-tok", "staging": "live.staging", "token": "tok"}))
    a.recover_promotions(base, _OWN_ALL)
    check("live RESTORED from the backup", (base / "live").exists()
          and (base / "live" / "r1.xlsx").exists())
    check("...backup consumed", not backup.exists())
    check("...staging + journal cleaned", not stage.exists() and not (jdir / "tok.json").exists())
    check("...idempotent (a second sweep is a no-op)",
          (a.recover_promotions(base, _OWN_ALL), (base / "live").exists())[-1])

    # State B: promotion COMPLETED (live present) but residue remains — clean it, keep live.
    base = tmp / "rec_b"; base.mkdir()
    live = _seed_store(base, "live")
    stale_backup = _seed_store(base, "live.bak-old")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "old.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-old", "staging": "live.staging", "token": "old"}))
    a.recover_promotions(base, _OWN_ALL)
    check("live (present) is kept", (base / "live" / "r1.xlsx").exists())
    check("...stale backup cleaned", not stale_backup.exists())
    check("...journal removed", not (jdir / "old.json").exists())

    # State C (P2-B04): orphan *.staging / *.bak-* with NO journal are now LEFT UNTOUCHED —
    # `root` may be a user destination with unrelated folders, so the journal-free sweep that
    # guessed at app ownership was removed (harmless residue is preferable to deleting data).
    base = tmp / "rec_c"; base.mkdir()
    _seed_store(base, "live")
    orphan_stage = base / "live.staging"; orphan_stage.mkdir(); (orphan_stage / "x").write_bytes(b"x")
    orphan_bak = _seed_store(base, "live.bak-orphan")
    a.recover_promotions(base, _OWN_ALL)
    check("orphan staging with no journal is NOT swept (B04-safe)", orphan_stage.exists())
    check("orphan backup with no journal is NOT swept (B04-safe)", orphan_bak.exists())
    check("live untouched", (base / "live" / "r1.xlsx").exists())

    # State D: a corrupt journal is dropped, never raises.
    base = tmp / "rec_d"; base.mkdir()
    _seed_store(base, "live")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "bad.json").write_text("{ not json")
    a.recover_promotions(base, _OWN_ALL)
    check("a corrupt journal is dropped (no raise)", not (jdir / "bad.json").exists())


def test_b05_malformed(tmp):                                  # P2-B05
    print("P2-B05 commit validation OPENS the workbook (rejects a malformed/unreadable part):")
    d = tmp / "b05"; d.mkdir()
    final = d / "cmp.xlsx"
    _xlsx(final, sheet="Comparison"); prior = final.read_bytes()

    # A ZIP that contains xl/workbook.xml but whose part is garbage — name-check would pass.
    def produce_malformed(t):
        _malformed_xlsx(t)
        return ConsolidateResult(status="ok", output_path=str(t))
    res = a.commit_workbook(final, produce_malformed, expect_sheet="Comparison")
    check("a ZIP-shaped but unreadable workbook -> error (not committed)", res.status == "error")
    check("...the valid prior workbook is preserved", final.read_bytes() == prior)
    check("...and it is still openable by openpyxl", a._openable_xlsx(final, "Comparison"))
    check("no temp leak", _no_temp_leak(d))

    # A readable workbook MISSING the expected sheet is rejected too.
    def produce_wrong_sheet(t):
        _xlsx(t, sheet="NotComparison")
        return ConsolidateResult(status="ok", output_path=str(t))
    res = a.commit_workbook(final, produce_wrong_sheet, expect_sheet="Comparison")
    check("a workbook missing the expected sheet -> error", res.status == "error")
    check("...prior preserved", final.read_bytes() == prior)


def test_r02_no_temp_leak(tmp):                               # P2-R02
    print("P2-R02 an ERROR result never leaks the deleted temp path (message/output/summary):")
    d = tmp / "r02"; d.mkdir()
    final = d / "cmp.xlsx"

    def produce_err_with_path(t):
        # compare_core builds its save-error message from the path it was handed (a temp).
        return ConsolidateResult(status="error", output_path=str(t),
                                 message=f"Could not save {Path(t).name}.",
                                 summary_lines=[f"Values file: {t}"])
    res = a.commit_workbook(final, produce_err_with_path)
    leaked = (".tmp-" in (res.message or "") or ".tmp-" in (res.output_path or "")
              or any(".tmp-" in s for s in (res.summary_lines or [])))
    check("the error result carries NO .tmp-<token> in any field", not leaked)
    check("...message names the FINAL file instead", final.name in (res.message or ""))
    check("no temp leak on disk", _no_temp_leak(d))


def test_r03_formulas_truthful(tmp):                          # P2-R03
    print("P2-R03 a best-effort formulas failure returns a TRUTHFUL values-canonical result:")
    d = tmp / "r03"; d.mkdir()
    final = d / "cmp.xlsx"                            # picked name = formulas primary
    final_values = a._values_twin(final)

    def produce_both(t):
        _xlsx(t, sheet="Comparison")                 # formulas
        _xlsx(a._values_twin(t), sheet="Comparison") # values twin
        return ConsolidateResult(status="ok", output_path=str(t),
                                 summary_lines=[f"Live-formulas file: {t}",
                                                f"Values file: {a._values_twin(t)}"])
    with _patch(a, "os", _OsShim("cmp.xlsx")):       # fail ONLY the formulas (picked-name) replace
        res = a.commit_workbook(final, produce_both, twin=True, expect_sheet="Comparison")
    check("status ok (values is canonical)", res.status == "ok")
    check("the values workbook IS committed", final_values.exists())
    check("the formulas workbook is NOT present", not final.exists())
    check("output_path points at the committed VALUES file (truthful)",
          res.output_path == str(final_values))
    check("the formulas summary line is a NOT-refreshed warning (no false claim)",
          any("NOT refreshed" in s for s in res.summary_lines)
          and not any(s.startswith(f"Live-formulas file: {final}") for s in res.summary_lines))
    check("no temp leak", _no_temp_leak(d))


def test_r01_directory_staging(tmp):                          # P2-R01
    print("P2-R01 a staging dir with no eligible report FILE is never promoted:")
    base = tmp / "r01"; base.mkdir()
    live = _seed_store(base, "live")
    prior = sorted(p.name for p in live.iterdir())
    stage = base / "live.staging"; (stage / "nested").mkdir(parents=True)   # only a subdir
    (stage / "~$lock.xlsx").write_bytes(b"x")        # + a lock file (excluded)
    check("directory-only / lock-only staging -> not promoted", a.promote_store(live, stage) is False)
    check("...the valid prior file set is preserved", sorted(p.name for p in live.iterdir()) == prior)


def test_b02_failed_rollback(tmp):                            # P2-B02
    print("P2-B02 a failed inline rollback RETAINS the journal so recovery can retry:")
    base = tmp / "b02a"; base.mkdir()
    _seed_store(base, "live")
    stage = base / "live.staging"; stage.mkdir(); (stage / "new.xlsx").write_bytes(b"new")
    # live->backup succeeds; staged->live and backup->live (restore) both fail.
    with _fail_rename_when(lambda s, t: t.name == "live"):
        ok = a.promote_store(base / "live", stage)
    check("promotion returns False", ok is False)
    check("...live is missing (death window) and a backup remains",
          not (base / "live").exists() and any(".bak-" in p.name for p in base.iterdir()))
    check("...the JOURNAL was RETAINED (not deleted) for retry",
          bool(list((base / ".promote").glob("*.json"))))
    a.recover_promotions(base, _OWN_ALL)                       # next launch
    check("the next-launch recovery RESTORES live from the retained backup",
          (base / "live").exists() and (base / "live" / "r1.xlsx").exists())

    print("P2-B02 a blocked first recovery retains the journal; the second succeeds:")
    base = tmp / "b02b"; base.mkdir()
    import json
    backup = _seed_store(base, "live.bak-tok")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "tok.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-tok", "staging": "live.staging", "token": "tok"}))
    with _fail_rename_when(lambda s, t: t.name == "live"):    # restore blocked
        a.recover_promotions(base, _OWN_ALL)
    check("first (blocked) sweep did NOT restore", not (base / "live").exists())
    check("...and RETAINED the journal + backup", backup.exists()
          and bool(list(jdir.glob("*.json"))))
    a.recover_promotions(base, _OWN_ALL)                       # unblocked second launch
    check("the second sweep restores live", (base / "live").exists()
          and (base / "live" / "r1.xlsx").exists())


def test_b04_traversal(tmp):                                  # P2-B04
    print("P2-B04 an untrusted journal cannot make recovery touch a path outside the store:")
    import json
    # The traversal target resolves to base/../victim (OUTSIDE the scanned store), and `live`
    # exists so the cleanup branch (`_rmtree(backup)` / `_rmtree(staging)`) would fire.
    cases = (("backup-traversal", {"target": "live", "backup": "../victim",
                                   "staging": "live.staging", "token": "t"}),
             ("staging-traversal", {"target": "live", "backup": "live.bak-t",
                                    "staging": "../victim", "token": "t"}),
             ("wrong-token-restore", {"target": "live", "backup": "live.bak-EVIL",
                                      "staging": "live.staging", "token": "t"}))
    for label, rec in cases:
        root = tmp / ("b04_" + label); root.mkdir()
        base = root / "store"; _seed_store(base, "live")        # target exists (cleanup path)
        victim = _seed_store(root, "victim")                    # base/../victim — out of store
        jdir = base / ".promote"; jdir.mkdir()
        (jdir / "t.json").write_text(json.dumps(rec))
        a.recover_promotions(base, _OWN_ALL)
        check(f"[{label}] the out-of-store victim dir is UNTOUCHED",
              victim.exists() and (victim / "r1.xlsx").exists())
        check(f"[{label}] the in-store live is preserved", (base / "live" / "r1.xlsx").exists())
        check(f"[{label}] the untrusted journal is dropped", not list(jdir.glob("*.json")))


def test_b02_invalid_target(tmp):                             # P2-B02 (round 2)
    print("P2-B02 recovery does NOT delete a valid backup when an INVALID placeholder is at live:")
    import json
    # (a) empty placeholder at live + valid backup -> displace placeholder, restore backup.
    base = tmp / "b02inv_a"; base.mkdir()
    (base / "live").mkdir()                          # empty placeholder — NOT a usable store
    backup = _seed_store(base, "live.bak-tok")       # the only real report data
    stage = _seed_store(base, "live.staging")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "tok.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-tok", "staging": "live.staging", "token": "tok"}))
    a.recover_promotions(base, _OWN_ALL)
    check("live now holds the restored report data (backup not deleted)",
          (base / "live" / "r1.xlsx").exists())
    check("...backup + staging + journal cleaned after a proven restore",
          not backup.exists() and not stage.exists() and not list(jdir.glob("*.json")))

    # (b) a placeholder with FOREIGN content + valid backup -> conflict: retain, touch nothing.
    base = tmp / "b02inv_b"; base.mkdir()
    ph = base / "live"; ph.mkdir(); (ph / "user_notes.txt").write_text("keep me")
    backup = _seed_store(base, "live.bak-tok")
    jdir = base / ".promote"; jdir.mkdir()
    (jdir / "tok.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-tok", "staging": "live.staging", "token": "tok"}))
    a.recover_promotions(base, _OWN_ALL)
    check("a foreign-content placeholder is NOT destroyed", (ph / "user_notes.txt").exists())
    check("...the valid backup is RETAINED (conflict, not deleted)",
          backup.exists() and (backup / "r1.xlsx").exists())
    check("...the journal is RETAINED for manual resolution", bool(list(jdir.glob("*.json"))))


def test_b04_orphan_survives(tmp):                            # P2-B04 (round 2)
    print("P2-B04 an unrelated *.bak-* / *.staging directory with NO journal survives recovery:")
    root = tmp / "userdest"; root.mkdir()
    project = _seed_store(root, "Project")                    # a real same-prefix 'live' sibling
    photos = root / "Project.bak-family-photos"; photos.mkdir()
    (photos / "keep.txt").write_text("precious")              # unrelated user data, no journal
    other_stage = root / "Other.staging"; other_stage.mkdir(); (other_stage / "x.txt").write_text("x")
    a.recover_promotions(root, _OWN_ALL)
    check("the unrelated *.bak-* directory is UNTOUCHED", (photos / "keep.txt").exists())
    check("the unrelated *.staging directory is UNTOUCHED", other_stage.exists())
    check("the live sibling is untouched", (project / "r1.xlsx").exists())


def test_b06_first_promotion(tmp):                            # P2-B06
    print("P2-B06 a failed FIRST-ever promotion keeps the only copy + recovers it next launch:")
    base = tmp / "b06"; base.mkdir()
    live = base / "live"                                      # NO prior live
    stage = _seed_store(base, "live.staging")
    with _fail_rename_when(lambda s, t: t.name == "live"):    # the only rename (staging->live) fails
        ok = a.promote_store(live, stage)
    check("first promotion returns False", ok is False)
    check("...live was NOT created", not live.exists())
    check("...the staging (the ONLY completed copy) is RETAINED, not deleted",
          stage.exists() and (stage / "r1.xlsx").exists())
    check("...a journal was written so recovery can complete it", bool(list((base / ".promote").glob("*.json"))))
    a.recover_promotions(base, _OWN_ALL)                                # next launch
    check("recovery PROMOTES the surviving staging to live", (live / "r1.xlsx").exists())
    check("...staging consumed + journal cleared",
          not stage.exists() and not list((base / ".promote").glob("*.json")))


def test_r01_wrong_extension(tmp):                            # P2-R01 (round 2)
    print("P2-R01 staging with only a non-report file (.txt) is NOT promoted:")
    base = tmp / "r01ext"; base.mkdir()
    live = _seed_store(base, "live")
    prior = sorted(p.name for p in live.iterdir())
    stage = base / "live.staging"; stage.mkdir(); (stage / "notes.txt").write_text("not a report")
    check(".txt-only staging -> not promoted", a.promote_store(live, stage) is False)
    check("...the valid prior .xlsx store is preserved",
          sorted(p.name for p in live.iterdir()) == prior)
    # A real report artifact DOES promote (control).
    base = tmp / "r01ext_ok"; base.mkdir()
    live = _seed_store(base, "live")
    stage = base / "live.staging"; stage.mkdir(); (stage / "r9.xlsx").write_bytes(b"real")
    check("control: a .xlsx staging DOES promote", a.promote_store(live, stage) is True)


def test_r04_malformed_sheet(tmp):                            # P2-R04
    print("P2-R04 a malformed worksheet is rejected, prior preserved, NO locked temp residue:")
    d = tmp / "r04"; d.mkdir()
    final = d / "cmp.xlsx"
    _xlsx(final, sheet="Comparison"); prior = final.read_bytes()

    def produce_bad_sheet(t):
        _workbook_with_bad_sheet(Path(t))
        return ConsolidateResult(status="ok", output_path=str(t))
    res = a.commit_workbook(final, produce_bad_sheet, expect_sheet="Comparison")
    check("a corrupt-worksheet workbook -> error (rejected)", res.status == "error")
    check("...the valid prior workbook is preserved", final.read_bytes() == prior)
    check("...NO temp residue remains (handle released, temp removed)", _no_temp_leak(d))


def test_a02_revert_race(tmp):                                # P2-A02 (round 2)
    print("P2-A02 a detected build race REMOVES the stale sidecar (no false-fresh after replace):")
    store = tmp / "a02r"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"identity-B")
    consolidated = tmp / "a02r_combined.xlsx"; _xlsx(consolidated)
    a.write_consolidated_fingerprint(consolidated, store)     # sidecar certifies identity B
    check("freshly recorded -> fresh", a.consolidated_fresh(consolidated, store))
    # A rebuild STARTED from identity A; the producer already replaced the workbook; the inputs
    # then reverted EXACTLY to B before publication. The old B sidecar must NOT certify it.
    ok = a.write_consolidated_fingerprint(consolidated, store, built_from="v1:0:identityA")
    check("the race is detected (returns False)", ok is False)
    check("...the stale sidecar was REMOVED so the workbook reads stale + rebuilds",
          a.consolidated_fresh(consolidated, store) is False)


def test_b07_two_journals_generation_aware(tmp):              # P2-B07
    print("P2-B07 two same-target journals: recovery keeps the NEWEST last-good (any order):")
    import json
    # The reachable interrupted two-generation state: a V1->V2 promotion whose backup cleanup was
    # locked left an OLDER journal (gen=1, backup=V1); a later V2->V3 promotion was interrupted after
    # live->backup (NEWER journal gen=2, backup=V2=the true last-good, shared det staging=V3, live
    # ABSENT). Vary which journal NAME the older/newer get, so the durable `gen` (not the filesystem
    # order) is what guarantees newest-first in BOTH encounter orders.
    for older_name, newer_name in (("a.json", "z.json"), ("z.json", "a.json")):
        tag = f"{older_name}-{newer_name}"
        root = tmp / ("b07_" + tag); root.mkdir()
        store_root = root / "ssor-prod"; store_root.mkdir()
        jdir = store_root / ".promote"; jdir.mkdir()

        def _store(name, content):
            d = store_root / name; d.mkdir()
            (d / "r.xlsx").write_text(content)
            return d
        bak_v1 = _store("highway_log.bak-t1", "V1")
        _store("highway_log.bak-t2", "V2")                   # the NEWER backup = the true last-good
        staging_v3 = _store("highway_log.staging", "V3")     # shared det staging (newer, interrupted)
        (jdir / older_name).write_text(json.dumps(
            {"target": "highway_log", "backup": "highway_log.bak-t1",
             "staging": "highway_log.staging", "token": "t1", "gen": 1}))
        (jdir / newer_name).write_text(json.dumps(
            {"target": "highway_log", "backup": "highway_log.bak-t2",
             "staging": "highway_log.staging", "token": "t2", "gen": 2}))

        def _is_owned(sr, target):
            return sr.name == "ssor-prod" and (target is None or target == "highway_log")
        a.recover_promotions(root, _is_owned)

        live = store_root / "highway_log"
        check(f"[{tag}] live holds the NEWEST proven last-good V2",
              live.is_dir() and (live / "r.xlsx").read_text() == "V2")
        check(f"[{tag}] the older generation V1 backup is gone (never restored over V2)",
              not bak_v1.exists())
        check(f"[{tag}] the un-promoted V3 staging is gone", not staging_v3.exists())
        check(f"[{tag}] both journals are cleared", not list(jdir.glob("*.json")))


def test_b07_durable_generation(tmp):                         # P2-B07 (round 6)
    print("P2-B07 the transaction generation is DURABLE (derived from journals, not wall-clock):")
    import json
    base = tmp / "gen_unit"; base.mkdir()
    jdir = base / ".promote"; jdir.mkdir()
    check("no prior same-target journal -> generation 1", a._next_generation(jdir, "live") == 1)
    (jdir / "j1.json").write_text(json.dumps(
        {"target": "live", "backup": "live.bak-x", "staging": "live.staging", "token": "x", "gen": 7}))
    check("a prior gen=7 same-target journal -> next is 8 (max+1)", a._next_generation(jdir, "live") == 8)
    (jdir / "j2.json").write_text(json.dumps(
        {"target": "elsewhere", "backup": "elsewhere.bak-y", "staging": "elsewhere.staging",
         "token": "y", "gen": 99}))
    check("a DIFFERENT target's higher gen is ignored", a._next_generation(jdir, "live") == 8)

    # Two REAL same-target promotions: the 2nd's journal generation is strictly GREATER, derived
    # from the on-disk journals — so it NEVER regresses even if the wall clock moves backward
    # between them (the round-6 repro). The 1st journal is retained (its backup cleanup is locked),
    # so both coexist for the comparison.
    live = tmp / "gen_real" / "ssor-prod" / "highway_log"; live.mkdir(parents=True)
    (live / "r.xlsx").write_text("V1")
    pjdir = live.parent / ".promote"
    orig_rmtree = a._rmtree

    def _block_bak(p):
        if a._BAK_INFIX in Path(p).name:
            return                                           # the renamed-aside backup is "locked"
        return orig_rmtree(p)

    def _promote(content):
        stage = live.with_name("highway_log.staging"); stage.mkdir(exist_ok=True)
        (stage / "r.xlsx").write_text(content)
        with _patch(a, "_rmtree", _block_bak):
            a.promote_store(live, stage)
    _promote("V2")                                           # gen 1, journal retained (backup locked)
    _promote("V3")                                           # gen 2, journal retained
    gens = sorted(a._journal_gen(p) for p in pjdir.glob("*.json"))
    check("two same-target journals coexist (both backups locked)", len(gens) == 2)
    check("their generations are strictly increasing 1,2 (a small counter, not a timestamp)",
          gens == [1, 2])


def test_b04_unowned_journal(tmp):                            # P2-B04 (rounds 3 + 4)
    print("P2-B04 ownership is LOCATION-based: a nested valid-NAME store is rejected before any read:")
    import json
    root = tmp / "userroot"; root.mkdir()

    # The updater's exact-root predicate: the store root must be a DIRECT child of THIS recovery
    # root, a known <src>-<env> name, and (with a target) a known export subdir.
    owned_roots = {"ssor-prod", "ars-test"}
    owned_targets = {"highway_log", "ramp_summary"}

    def _is_owned(store_root, target):
        if store_root.parent.resolve() != root.resolve():
            return False
        if store_root.name not in owned_roots:
            return False
        return target is None or target in owned_targets

    # (1) Round-4 repro: a valid `<src>-<env>` NAME nested one level too deep (wrong LOCATION) —
    # <root>/UnrelatedProject/ssor-prod/.promote with a SHAPE-VALID journal for a real target.
    nested_parent = root / "UnrelatedProject" / "ssor-prod"
    target = _seed_store(nested_parent, "ramp_summary")     # a usable store (r1.xlsx)
    backup = _seed_store(nested_parent, "ramp_summary.bak-tok")   # unrelated user data
    stage = _seed_store(nested_parent, "ramp_summary.staging")
    njdir = nested_parent / ".promote"; njdir.mkdir()
    njournal = njdir / "tok.json"
    njournal.write_text(json.dumps(
        {"target": "ramp_summary", "backup": "ramp_summary.bak-tok",
         "staging": "ramp_summary.staging", "token": "tok"}))
    # (2) A nested MALFORMED journal at a wrong location must ALSO be left untouched.
    mal_parent = root / "Other" / "ars-test"; mal_parent.mkdir(parents=True)
    mjdir = mal_parent / ".promote"; mjdir.mkdir()
    mjournal = mjdir / "bad.json"; mjournal.write_text("{ not json")
    # (3) Owned direct-child control: <root>/ssor-prod/.promote (live missing) -> restores.
    owned_root = root / "ssor-prod"; owned_root.mkdir()
    _seed_store(owned_root, "highway_log.bak-t2")           # backup; live (target) is missing
    ojdir = owned_root / ".promote"; ojdir.mkdir()
    (ojdir / "t2.json").write_text(json.dumps(
        {"target": "highway_log", "backup": "highway_log.bak-t2",
         "staging": "highway_log.staging", "token": "t2"}))

    a.recover_promotions(root, _is_owned)

    check("the nested valid-name target is UNTOUCHED (wrong location)", (target / "r1.xlsx").exists())
    check("the nested backup is UNTOUCHED", (backup / "r1.xlsx").exists())
    check("the nested staging is UNTOUCHED", (stage / "r1.xlsx").exists())
    check("the nested shape-valid journal is left in place (not ours)", njournal.exists())
    check("the nested MALFORMED journal is NOT deleted (outside an owned location)", mjournal.exists())
    check("control: the OWNED direct-child journal restored its target from backup",
          (owned_root / "highway_log" / "r1.xlsx").exists())


def test_r05_promote_cleanup(tmp):                            # P2-R05 (round 4: the promote_store path)
    print("P2-R05 promote_store retains the journal when its OWN residue cleanup fails:")
    orig_rmtree = a._rmtree

    # (a) successful promotion (prior exists) with a LOCKED backup -> journal RETAINED.
    base = tmp / "r05p_a"; base.mkdir()
    live = _seed_store(base, "live")                         # a prior live store
    stage = base / "live.staging"; stage.mkdir(); (stage / "r9.xlsx").write_bytes(b"new")

    def _block_bak(p):
        if a._BAK_INFIX in Path(p).name:
            return                                           # the renamed-aside backup is "locked"
        return orig_rmtree(p)
    with _patch(a, "_rmtree", _block_bak):
        ok = a.promote_store(live, stage)
    check("the promotion still succeeds (new data is live)",
          ok is True and (live / "r9.xlsx").exists())
    check("...the un-removable backup survived", any(a._BAK_INFIX in p.name for p in base.iterdir()))
    check("...the journal was RETAINED for next-launch cleanup",
          bool(list((base / ".promote").glob("*.json"))))
    a.recover_promotions(base, _OWN_ALL)                     # a later, unblocked sweep cleans it
    check("a later recovery removes the leftover backup",
          not any(a._BAK_INFIX in p.name for p in base.iterdir()))
    check("...and then drops the journal", not list((base / ".promote").glob("*.json")))

    # (b) inline restore (staging->live fails, restore succeeds) with a LOCKED staging -> RETAINED.
    base = tmp / "r05p_b"; base.mkdir()
    live = _seed_store(base, "live")
    stage = base / "live.staging"; stage.mkdir(); (stage / "r9.xlsx").write_bytes(b"new")

    def _fail_stage_to_live(s, t):                           # only staging->live fails (force restore)
        return t.name == "live" and s.name.endswith(a._STAGING_SUFFIX)

    def _block_stage_rm(p):
        if Path(p).name.endswith(a._STAGING_SUFFIX):
            return                                           # the residual staging is "locked"
        return orig_rmtree(p)
    with _fail_rename_when(_fail_stage_to_live), _patch(a, "_rmtree", _block_stage_rm):
        ok = a.promote_store(live, stage)
    check("the inline restore kept last-good live", (live / "r1.xlsx").exists() and ok is False)
    check("...the un-removable staging survived", stage.exists())
    check("...the journal was RETAINED (residue cleanup incomplete)",
          bool(list((base / ".promote").glob("*.json"))))


def test_a02_dual_failure_quarantine(tmp):                    # P2-A02 (round 4)
    print("P2-A02 if BOTH sidecar removal AND sentinel write fail, the workbook is quarantined:")
    store = tmp / "a02d"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"identity-B")
    consolidated = tmp / "a02d_combined.xlsx"; _xlsx(consolidated)
    a.write_consolidated_fingerprint(consolidated, store)    # sidecar certifies identity B
    check("freshly recorded -> fresh", a.consolidated_fresh(consolidated, store))
    orig_unlink = a._silent_unlink

    def _block_sidecar(p):
        if str(p).endswith(a._FP_SUFFIX):
            return False                                     # the sidecar is "locked" (can't unlink)
        return orig_unlink(p)
    with _patch(a, "_silent_unlink", _block_sidecar), \
         _patch(a, "_write_fp_sentinel", lambda _p: False):  # AND the sentinel write fails
        ok = a.write_consolidated_fingerprint(consolidated, store, built_from="v1:0:identityA")
    check("the race still returns False", ok is False)
    check("...the replaced workbook was QUARANTINED (canonical path now missing)",
          not consolidated.exists())
    check("...so consolidated_fresh reads STALE despite the un-removable sidecar",
          a.consolidated_fresh(consolidated, store) is False)


def test_r05_cleanup_failure_retains_journal(tmp):            # P2-R05
    print("P2-R05 a failed residue cleanup RETAINS the journal so a later sweep retries:")
    import json
    orig_rmtree = a._rmtree

    # (a) usable target + a backup whose removal fails -> journal retained, retried later.
    base = tmp / "r05a"; base.mkdir()
    _seed_store(base, "live")                                # a usable canonical target
    backup = _seed_store(base, "live.bak-tok")
    jdir = base / ".promote"; jdir.mkdir()
    jpath = jdir / "tok.json"
    jpath.write_text(json.dumps(
        {"target": "live", "backup": "live.bak-tok", "staging": "live.staging", "token": "tok"}))

    def _block_backup(p):
        if Path(p).name == "live.bak-tok":
            return                                           # simulate a locked backup (not removed)
        return orig_rmtree(p)
    with _patch(a, "_rmtree", _block_backup):
        a.recover_promotions(base, _OWN_ALL)
    check("the un-removable backup survived", backup.exists())
    check("...and the journal was RETAINED (cleanup incomplete)", jpath.exists())
    a.recover_promotions(base, _OWN_ALL)                     # a later, unblocked sweep
    check("a later sweep removes the backup", not backup.exists())
    check("...and then drops the journal", not jpath.exists())

    # (b) after a RESTORE, a residual staging that can't be removed retains the journal.
    base = tmp / "r05b"; base.mkdir()
    backup = _seed_store(base, "live.bak-t")                 # target missing -> restore from backup
    stage = _seed_store(base, "live.staging")
    jdir = base / ".promote"; jdir.mkdir()
    jpath = jdir / "t.json"
    jpath.write_text(json.dumps(
        {"target": "live", "backup": "live.bak-t", "staging": "live.staging", "token": "t"}))

    def _block_staging(p):
        if Path(p).name == "live.staging":
            return                                           # locked staging
        return orig_rmtree(p)
    with _patch(a, "_rmtree", _block_staging):
        a.recover_promotions(base, _OWN_ALL)
    check("the restore succeeded (live present)", (base / "live" / "r1.xlsx").exists())
    check("...but the un-removable staging RETAINS the journal", jpath.exists() and stage.exists())


def test_a02_sidecar_unremovable(tmp):                        # P2-A02 (round 3)
    print("P2-A02 an un-removable stale sidecar is overwritten with a non-matching sentinel:")
    store = tmp / "a02s"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"identity-B")
    consolidated = tmp / "a02s_combined.xlsx"; _xlsx(consolidated)
    a.write_consolidated_fingerprint(consolidated, store)    # sidecar certifies identity B
    check("freshly recorded -> fresh", a.consolidated_fresh(consolidated, store))
    orig_unlink = a._silent_unlink

    def _block_sidecar(p):
        if str(p).endswith(a._FP_SUFFIX):
            return False                                     # simulate a locked sidecar (not removed)
        return orig_unlink(p)
    with _patch(a, "_silent_unlink", _block_sidecar):
        ok = a.write_consolidated_fingerprint(consolidated, store, built_from="v1:0:identityA")
    check("the race still returns False", ok is False)
    check("...and the workbook reads STALE despite the un-removable sidecar (sentinel written)",
          a.consolidated_fresh(consolidated, store) is False)


def test_a02_build_race(tmp):                                 # P2-A02
    print("P2-A02 a fingerprint is NOT certified fresh when inputs changed during the build:")
    store = tmp / "a02"; store.mkdir()
    (store / "r1.xlsx").write_bytes(b"a" * 10)
    consolidated = tmp / "a02_combined.xlsx"; _xlsx(consolidated)
    fp_before = a.fingerprint(store)
    (store / "r2.xlsx").write_bytes(b"b" * 10)    # an input changed AFTER fp_before was captured
    ok = a.write_consolidated_fingerprint(consolidated, store, built_from=fp_before)
    check("the sidecar is NOT written (the build raced an input change)", ok is False)
    check("...so the workbook reads stale and rebuilds next reuse",
          a.consolidated_fresh(consolidated, store) is False)
    ok2 = a.write_consolidated_fingerprint(consolidated, store, built_from=a.fingerprint(store))
    check("no race (before == after) -> the sidecar IS written",
          ok2 is True and a.consolidated_fresh(consolidated, store))


def test_b03_updater_recovers_batch_dest(tmp):                # P2-B03
    print("P2-B03 startup recovery sweeps the configured batch destination, not just OUTPUT_ROOT:")
    import updater
    import paths
    import settings
    swept = []
    custom = tmp / "custom_batch_dest"
    with _patch(a, "recover_promotions", lambda r, _own: swept.append(Path(r))), \
         _patch(settings, "get_batch_dest", lambda: str(custom)):
        updater._recover_store_promotions()
    swept_resolved = {p.resolve() if p.exists() else p for p in swept}
    check("OUTPUT_ROOT is swept", Path(paths.OUTPUT_ROOT) in swept
          or Path(paths.OUTPUT_ROOT).resolve() in swept_resolved)
    check("the CUSTOM batch destination (outside OUTPUT_ROOT) is also swept", custom in swept)

    # Deduplication: when the batch dest == OUTPUT_ROOT, the sweep runs once.
    swept.clear()
    with _patch(a, "recover_promotions", lambda r, _own: swept.append(Path(r))), \
         _patch(settings, "get_batch_dest", lambda: str(paths.OUTPUT_ROOT)):
        updater._recover_store_promotions()
    check("the batch-dest == OUTPUT_ROOT case sweeps exactly once (deduped)", len(swept) == 1)


def main():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_atomic_save(tmp)
        test_commit_single(tmp)
        test_commit_twin(tmp)
        test_b05_malformed(tmp)
        test_r02_no_temp_leak(tmp)
        test_r03_formulas_truthful(tmp)
        test_fingerprint(tmp)
        test_consolidated_fresh(tmp)
        test_promote_validate(tmp)
        test_r01_directory_staging(tmp)
        test_r01_wrong_extension(tmp)
        test_r04_malformed_sheet(tmp)
        test_b02_failed_rollback(tmp)
        test_b02_invalid_target(tmp)
        test_b04_traversal(tmp)
        test_b04_orphan_survives(tmp)
        test_b04_unowned_journal(tmp)
        test_b06_first_promotion(tmp)
        test_b07_two_journals_generation_aware(tmp)
        test_b07_durable_generation(tmp)
        test_r05_cleanup_failure_retains_journal(tmp)
        test_r05_promote_cleanup(tmp)
        test_a02_build_race(tmp)
        test_a02_revert_race(tmp)
        test_a02_sidecar_unremovable(tmp)
        test_a02_dual_failure_quarantine(tmp)
        test_b03_updater_recovers_batch_dest(tmp)
        test_recovery(tmp)
    print()
    if _failures:
        print(f"FAILED {len(_failures)} check(s): {_failures}")
        return 1
    print("All artifact_store checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

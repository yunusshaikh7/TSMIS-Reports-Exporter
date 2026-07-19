"""Golden check for W1 one-click validation (scripts/validation.py + the
evidence-bundle integration).

Locks the automated work-PC ride-along: run_validation processes the on-disk
samples through the REAL matrix comparison path, records COUNTS/OUTCOMES/folder
NAMES only (never report data — RM05), degrades instead of crashing on a bad
family, honors should_cancel between cells, and evidence.collect ships the
manifest as validation.txt + validation.json in the credential-safe bundle.

Stdlib + openpyxl; no browser, no network. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_validation.py
"""
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_ROOT, "scripts"), _ROOT]   # scripts + repo root (version.py)

import evidence
import outcome
import validation
from events import ConsolidateResult, Events

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


class _Patch:
    def __init__(self, obj, name, value):
        self.obj, self.name, self.value = obj, name, value

    def __enter__(self):
        self.old = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *a):
        setattr(self.obj, self.name, self.old)


def _published(completion="complete", diff_cells=0, one_sided=0,
               skipped_inputs=0, failed_inputs=0):
    counts = SimpleNamespace(
        known=True,
        paired_rows=10,
        side_a_only_rows=one_sided,
        side_b_only_rows=0,
        differing_rows=min(diff_cells, 10),
        differing_cells=diff_cells,
        asserted_cells=20,
        context_cells=0,
    )
    typed = SimpleNamespace(
        completion=completion,
        verdict=("match" if completion == "complete"
                 and diff_cells == 0 and one_sided == 0 else "diff"),
        counts=counts,
    )
    return SimpleNamespace(
        trusted=True,
        current=True,
        comparison_outcome=typed,
        artifact_generation=SimpleNamespace(generation_id="g-test"),
        skipped_inputs=skipped_inputs,
        failed_inputs=failed_inputs,
    )


def _store(root, rows_per_env):
    """A fake Export-Everything store: {env: [subdir, ...]} -> files on disk."""
    for env, subs in rows_per_env.items():
        for sub in subs:
            d = root / env / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / "route_001.xlsx").write_bytes(b"PK\x03\x04data")


def test_manifest_and_cancel():
    print("validation manifest — real pipeline, counts only, cancellable:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_val_"))
    dest = tmp / "store"
    # `_tsn_input` + `comparisons` are DECOYS: real stores hold these
    # non-environment children, and a workbook inside them must never be
    # validated as a TSMIS export (the v0.19.0 field bug — the TSN drop folder
    # became phantom environment "_tsn_input").
    _store(dest, {"ssor-prod": ["highway_log"], "ssor-dev": ["highway_log"],
                  "_tsn_input": ["highway_log"], "comparisons": ["highway_log"]})

    calls = []

    def fake_build(dest_, row, env, mode, baseline, events, **kw):
        calls.append((row, env, mode))
        return ConsolidateResult(status="ok", completion=outcome.COMPLETE,
                                 output_path=str(dest / "cmp.xlsx"))

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", fake_build), \
         _Patch(validation.consolidation_meta, "require_published_comparison",
                lambda p, r: _published(diff_cells=969)), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())

    ran = man["comparisons"]["cells"]
    check("both envs' comparisons ran through matrix.build_comparison",
          [(c["row"], c["env"]) for c in ran]
          == [("highway_log", "ssor-dev"), ("highway_log", "ssor-prod")]
          or sorted((c["row"], c["env"]) for c in ran)
          == [("highway_log", "ssor-dev"), ("highway_log", "ssor-prod")])
    check("non-environment store children are NOT phantom envs (_tsn_input bug)",
          not [c for c in ran if c.get("env") in ("_tsn_input", "comparisons")],
          f"phantom cells: {[(c['row'], c.get('env')) for c in ran]}")
    check("counts recorded (969 diff cells), status ok",
          all(c.get("diff_cells") == 969 and c["status"] == "ok" for c in ran))
    check("totals tally", man["totals"]["comparisons_ok"] == 2
          and man["totals"]["comparisons_run"] == 2)

    # a manifest carries NO report data — only counts / names / outcomes
    blob = json.dumps(man)
    check("manifest is credential-safe (no route payload, only counts/names)",
          "route_001" not in blob and "PK" not in blob)

    # cancel after the first cell
    seen = {"n": 0}

    def cancel_after_one():
        seen["n"] += 1
        return seen["n"] > 1

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", fake_build), \
         _Patch(validation.consolidation_meta, "require_published_comparison",
                lambda p, r: _published(diff_cells=1)), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man2 = validation.run_validation(events=Events(),
                                         should_cancel=cancel_after_one)
    check("should_cancel stops the run early",
          man2["totals"]["cancelled"] is True
          and any(c.get("skipped") == "cancelled" for c in man2["comparisons"]["cells"]))


def test_degrades_on_family_error():
    print("validation degrades (records) a failing family, never crashes:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_valerr_"))
    dest = tmp / "store"
    _store(dest, {"ssor-prod": ["highway_log"]})

    def boom(*a, **k):
        raise RuntimeError("adapter exploded")

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports
    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", boom), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())
    cell = man["comparisons"]["cells"][0]
    check("a raising adapter is recorded as an error cell (not a crash)",
          cell["status"] == "error" and "RuntimeError" in cell["message"])
    check("totals count the failure", man["totals"]["comparisons_failed"] == 1)

    # An error MESSAGE is copied into the bundle — it must stay credential-safe
    # (RM05: paths/names are allowed; auth tokens / cookies / report data are not).
    def boom_creds(*a, **k):
        raise RuntimeError("could not read C:\\Users\\bob\\r.xlsx; "
                           "access_token=SECRETXYZ cookie=SID=abc123")
    with _Patch(_matrix, "build_comparison", boom_creds), \
         _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r: {"kind": "consolidated"}), \
         _Patch(_tsn, "reports", lambda: []):
        man2 = validation.run_validation(events=Events())
    blob = (json.dumps(man2) + "\n".join(validation.summary_lines(man2))).lower()
    check("error-message credential VALUES are redacted from the manifest",
          "secretxyz" not in blob and "abc123" not in blob and "[redacted]" in blob,
          "an error message leaked a token/cookie value into the credential-safe bundle")
    check("the harmless path in the same message is preserved (RM05: paths OK)",
          "r.xlsx" in blob)

    # CMP-AUD-117: labels/schemes must consume the WHOLE credential value. The
    # old regex redacted only the word "Bearer" in an Authorization header and
    # ignored bare schemes/JWTs entirely, leaving the actual secret in the ZIP.
    scrub_cases = [
        ("Authorization: Bearer SECRET-ABC-123", ("SECRET-ABC-123",)),
        ("Proxy-Authorization=Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
         ("QWxhZGRpbjpvcGVuIHNlc2FtZQ==",)),
        ("retry with Bearer BARE-TOKEN-456", ("BARE-TOKEN-456",)),
        ("retry with Bearer abc", ("abc",)),
        ("retry with Bearer AB$CD", ("AB$CD",)),
        ("Authorization: Bearer\r\n FOLDED-SECRET-789",
         ("FOLDED-SECRET-789",)),
        ("Cookie: SID=cookie-secret; theme=dark", ("cookie-secret",)),
        ("https://x.invalid/?access_token=QUERY-SECRET&mode=1", ("QUERY-SECRET",)),
        ("jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
         "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
         ("eyJhbGciOiJIUzI1NiJ9", "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")),
    ]
    for raw, secrets in scrub_cases:
        cleaned = validation._scrub(raw)
        check(f"credential form is fully scrubbed: {raw.split()[0]}",
              all(secret not in cleaned for secret in secrets)
              and "[redacted]" in cleaned,
              f"scrubbed value still leaked: {cleaned!r}")


def test_evidence_carries_manifest():
    print("evidence.collect ships validation.txt + validation.json:")
    man = {
        "generated": "now",
        "environment": {"app_version": "0.19.0", "build": "dev", "python": "3.11",
                        "platform": "x", "site": "ssor-prod", "playwright_pin": "1.60.0"},
        "tsn_library": [{"report": "highway_log", "raw_count": 3,
                         "consolidated_present": True, "current_before": True,
                         "healed": None, "current_after": True,
                         "normalization_version": 2}],
        "comparisons": {"dest_name": "store", "baseline": "ssor-prod",
                        "cells": [{"row": "highway_log", "env": "ssor-prod",
                                   "status": "ok", "completion": "complete",
                                   "diff_cells": 969, "one_sided": 0, "seconds": 4.2}]},
        "totals": {"comparisons_run": 1, "comparisons_ok": 1, "comparisons_failed": 0,
                   "cancelled": False, "seconds": 5.0},
    }
    out = Path(tempfile.mkdtemp(prefix="tsmis_valev_")) / "ev.zip"
    res = evidence.collect(out_path=out, emit=lambda l: None,
                           run_self_test=False, validation=man)
    check("bundle built ok", res.get("ok"))
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        check("validation.txt + validation.json in the bundle",
              "validation.txt" in names and "validation.json" in names)
        digest = z.read("validation.txt").decode()
        check("digest is human-readable (names/counts, no raw data)",
              "app v0.19.0" in digest and "969" in digest and "route_001" not in digest)
        rt = json.loads(z.read("validation.json"))
        check("json round-trips the manifest", rt["totals"]["comparisons_ok"] == 1)
        check("returned member count equals the actual ZIP member count",
              res.get("files") == len(names))


def test_trust_semantics():
    """A PARTIAL comparison is NOT counted as a full OK; a present-but-raw TSN
    library is HEALED (not errored); unreadable counts are flagged, not shown as
    a clean success. These are the trust properties the bundle exists to prove."""
    print("validation trust semantics — partial/heal/unreadable-counts:")
    check("missing completion/counts/generation can never default to full OK",
          not validation._is_full_ok({"status": "ok"})
          and not validation._is_full_ok({
              "status": "ok", "classification": "ok",
              "completion": "complete", "counts_unreadable": True}))
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_valtrust_"))
    dest = tmp / "store"
    _store(dest, {"ssor-prod": ["highway_log", "intersection_detail"]})

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports

    # highway_log -> a PARTIAL ok; intersection_detail -> ok but counts unreadable
    def build(dest_, row, env, mode, baseline, events, **kw):
        if row == "highway_log":
            return ConsolidateResult(status="ok", completion=outcome.PARTIAL,
                                     output_path=str(dest / "p.xlsx"))
        return ConsolidateResult(status="ok", completion=outcome.COMPLETE,
                                 output_path=str(dest / "c.xlsx"))

    healed = {"n": 0}

    def ensure_current(sub, events=None):
        healed["n"] += 1
        return ConsolidateResult(status="ok", message="rebuilt")

    def require_published(path, _result):
        if str(path).endswith("c.xlsx"):
            raise ValueError("typed counts/generation are unreadable")
        return _published(completion=outcome.PARTIAL, diff_cells=3,
                          skipped_inputs=1)

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_matrix, "build_comparison", build), \
         _Patch(validation.consolidation_meta, "require_published_comparison",
                require_published), \
         _Patch(_reports, "matrix_rows",
                lambda: [("highway_log", "Highway Log", "highway_log", 0, object()),
                         ("intersection_detail", "Int Detail", "intersection_detail", 1, object())]), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve",
                lambda r: {"kind": "raw"} if r == "highway_log" else {"kind": "consolidated"}), \
         _Patch(_tsn, "ensure_current", ensure_current), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())

    t = man["totals"]
    check("a PARTIAL comparison is NOT a full OK (partial tallied separately)",
          t["comparisons_ok"] == 0 and t["comparisons_partial"] == 1
          and t["comparisons_untrusted"] == 1
          and t["comparisons_run"] == 2, f"totals={t}")
    check("a present-but-raw TSN library is HEALED before comparing (not errored)",
          healed["n"] >= 1)
    dig = "\n".join(validation.summary_lines(man))
    check("digest flags the PARTIAL cell", "PARTIAL inputs" in dig)
    check("digest flags unreadable typed metadata (not a bare success)",
          "UNTRUSTED" in dig and "unreadable" in dig)


def test_tsn_stage_heals_stale_library():
    """_tsn_stage (the D2 auto-heal stage) is the only state-MUTATING stage;
    exercise it directly (the other tests patch reports() to []). A stale
    present-raw library heals; a current one is left alone."""
    print("validation _tsn_stage — freshness + D2 heal:")
    import tsn_library as _tsn

    class _Spec:
        def __init__(self, subdir, nv):
            self.subdir, self.normalization_version, self.label = subdir, nv, subdir

    statuses = {
        "stale_lib": {"consolidated_present": True, "raw_present": True,
                      "current": False, "raw_count": 5},
        "fresh_lib": {"consolidated_present": True, "raw_present": True,
                      "current": True, "raw_count": 3},
    }
    healed = []

    def status(sub):
        # after a heal the stale one reports current
        s = dict(statuses[sub])
        if sub == "stale_lib" and healed:
            s["current"] = True
        return s

    def ensure_current(sub, events=None):
        healed.append(sub)
        return ConsolidateResult(status="ok", message="rebuilt")

    with _Patch(_tsn, "reports", lambda: [_Spec("stale_lib", 2), _Spec("fresh_lib", 2)]), \
         _Patch(_tsn, "status", status), \
         _Patch(_tsn, "ensure_current", ensure_current):
        rows = validation._tsn_stage(Events(), lambda: False)

    by = {r["report"]: r for r in rows}
    check("a stale present-raw library is HEALED and reads current after",
          by["stale_lib"]["healed"] == "ok" and by["stale_lib"]["current_after"] is True
          and healed == ["stale_lib"])
    check("a already-current library is left alone (no heal)",
          by["fresh_lib"]["healed"] is None)
    check("each row records the normalization version",
          by["stale_lib"]["normalization_version"] == 2)

    # CMP-AUD-120: a pre-cancelled validation must never rewrite a library.
    healed.clear()
    with _Patch(_tsn, "reports", lambda: [_Spec("stale_lib", 2)]), \
         _Patch(_tsn, "status", lambda sub: dict(statuses[sub])), \
         _Patch(_tsn, "ensure_current", ensure_current):
        rows = validation._tsn_stage(Events(), lambda: True)
    check("CMP-AUD-120: pre-cancelled validation attempts NO heal",
          healed == [] and rows[0]["healed"] is None
          and rows[0]["cancelled_before_heal"] is True)
    check("CMP-AUD-120/119: the digest says 'cancelled before heal', not STALE",
          validation._tsn_state_text(rows[0]) == "cancelled before heal")


def test_tsn_state_truth_table():
    """CMP-AUD-119: the digest never hides a heal attempt or invents success."""
    print("validation TSN digest truth table (CMP-AUD-119):")
    base = {"raw_count": 3, "consolidated_present": True,
            "current_before": False, "cancelled_before_heal": False}
    t = validation._tsn_state_text
    check("healed to current is disclosed as HEALED, not bare 'current'",
          t({**base, "healed": "ok", "current_after": True})
          == "HEALED → current")
    check("a heal that did NOT reach current is an alarm, never HEALED",
          t({**base, "healed": "ok", "current_after": False})
          == "HEAL RAN BUT STILL STALE")
    check("a failed heal says HEAL FAILED",
          t({**base, "healed": "error", "current_after": False})
          == "HEAL ERROR")
    check("a cancelled heal says HEAL CANCELLED",
          t({**base, "healed": "cancelled", "current_after": False})
          == "HEAL CANCELLED")
    check("an untouched current library still reads 'current'",
          t({**base, "current_before": True, "healed": None,
             "current_after": True}) == "current")
    check("raw-only data is a blocked capability, not absent data "
          "(CMP-AUD-118)",
          t({**base, "consolidated_present": False, "healed": None,
             "current_after": False}) == "raw imported, awaiting first build")
    check("genuinely empty library reads 'no data'",
          t({**base, "consolidated_present": False, "raw_count": 0,
             "healed": None, "current_after": False}) == "no data")
    check("stale with no raw to rebuild from says so",
          t({**base, "raw_count": 0, "healed": None,
             "current_after": False}) == "STALE (no raw to rebuild from)")


def test_ensure_tsn_ready_first_build():
    """CMP-AUD-118: raw-only libraries get the explicit first build."""
    print("validation raw-only first build (CMP-AUD-118):")
    import tsn_library as _tsn
    built = []

    def build_consolidated(sub, events=None):
        built.append(sub)
        return ConsolidateResult(status="ok", message="first build")

    with _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r, *_a: {"kind": "raw"}), \
         _Patch(_tsn, "ensure_current", lambda r, events=None: None), \
         _Patch(_tsn, "build_consolidated", build_consolidated):
        ready = validation._ensure_tsn_ready("ramp_detail", Events())
    check("raw-only + no consolidated triggers the FIRST build and is ready",
          ready is True and built == ["ramp_detail"])

    built.clear()
    with _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", lambda r, *_a: {"kind": "raw"}), \
         _Patch(_tsn, "ensure_current", lambda r, events=None: None), \
         _Patch(_tsn, "build_consolidated",
                lambda r, events=None: ConsolidateResult(
                    status="error", message="bad raw")):
        ready = validation._ensure_tsn_ready("ramp_detail", Events())
    check("a failing first build reports not-ready (never a silent skip)",
          ready is False)


def test_missing_explicit_tsn_is_not_substituted():
    """CMP-AUD-105: validation honors shared TSN keys for every PDF row."""
    print("validation fails closed on deleted explicit TSN selections (all PDF rows):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_valpick_"))
    dest = tmp / "store"
    _store(dest, {"ssor-prod": ["highway_log"]})
    pdf_rows = [
        ("highway_log_pdf", "Highway Log (PDF)", "highway_log_pdf", 0, object()),
        ("intersection_detail_pdf", "Intersection Detail (PDF)",
         "intersection_detail_pdf", 0, object()),
        ("highway_detail_pdf", "Highway Detail (PDF)", "highway_detail_pdf", 0, object()),
        ("highway_sequence_pdf", "Highway Sequence (PDF)",
         "highway_sequence_pdf", 0, object()),
        ("ramp_detail_pdf", "Ramp Detail (PDF)", "ramp_detail_pdf", 0, object()),
    ]
    bases = {
        "highway_log_pdf": "highway_log",
        "intersection_detail_pdf": "intersection_detail",
        "highway_detail_pdf": "highway_detail",
        "highway_sequence_pdf": "highway_sequence",
        "ramp_detail_pdf": "ramp_detail",
    }
    selections = {
        base: {"version": 1, "path": str(tmp / f"deleted-{base}.xlsx"),
               "identity": {"sha256": "0" * 64, "size": 1,
                            "mtime_ns": 1, "file_id": "1:1"}}
        for base in set(bases.values())
    }
    built = []
    resolved = []

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports

    def resolve(_report, selected_file=None):
        resolved.append((_report, selected_file))
        if selected_file:
            return {"kind": "missing_explicit",
                    "selected_path": selected_file["path"],
                    "selection_reason": "missing"}
        return {"kind": "consolidated", "path": str(tmp / "canonical.xlsx")}

    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_settings, "get_matrix_tsn_selections", lambda: selections), \
         _Patch(_matrix, "build_comparison", lambda *a, **k: built.append((a, k))), \
         _Patch(_reports, "matrix_rows", lambda: pdf_rows), \
         _Patch(_tsn, "is_registered", lambda r: True), \
         _Patch(_tsn, "resolve", resolve), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())

    cells = man["comparisons"]["cells"]
    check("validation records all five shared selected files as blocked",
          len(cells) == 5 and all(
              "selected TSN" in cell.get("skipped", "")
              and "re-pick" in cell.get("skipped", "").lower()
              and "clear" in cell.get("skipped", "").lower()
              for cell in cells))
    check("validation resolves PDF rows through their five base TSN dataset keys",
          {report for report, selected in resolved if selected}
          == set(bases.values()))
    check("validation never builds against the available fallback", not built)


def test_007_full_capability_coverage():
    """CMP-AUD-007: validation must cover EVERY comparable row (incl. the five PDF
    rows through their BASE-family TSN dataset), pass the selected TSN files into
    build_comparison, and count blocked capabilities separately — never present
    'ok of ran' while a capability was silently omitted. Positive-path pin
    (the base-family mapping for the blocked case is pinned by
    test_missing_explicit_tsn_is_not_substituted)."""
    print("CMP-AUD-007: every capability covered + selected TSN files passed through:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_val007_"))
    dest = tmp / "store"
    # A PDF row with store data (2 envs), a base row with data (1 env), and a row
    # with NO store data (must be BLOCKED, never silently dropped from the count).
    _store(dest, {"ssor-prod": ["highway_log_pdf", "highway_detail"],
                  "ars-prod": ["highway_log_pdf"]})
    rows = [
        ("highway_log_pdf", "Highway Log (PDF)", "highway_log_pdf", 0, object()),
        ("highway_detail", "Highway Detail", "highway_detail", 0, object()),
        ("ramp_summary", "Ramp Summary", "ramp_summary", 0, object()),   # no data
    ]
    # A user-selected TSN workbook keyed by the PDF row's BASE family (highway_log).
    selection = {"version": 1, "path": str(tmp / "picked-hl.xlsx"),
                 "identity": {"sha256": "0" * 64, "size": 1,
                              "mtime_ns": 1, "file_id": "1:1"}}
    selections = {"highway_log": selection}

    build_calls = []
    resolved_subdirs = []
    # Only the BASE families are TSN-registered (PDF subdirs never are) — so the
    # PDF row runs ONLY when readiness is resolved through its canonical base key.
    # This makes the mapping the difference between run and blocked (red→green).
    registered = {"highway_log", "highway_detail", "ramp_summary"}

    def fake_build(dest_, row, env, mode, baseline, events, **kw):
        build_calls.append((row, env, mode, kw.get("tsn_files")))
        return ConsolidateResult(status="ok", completion=outcome.COMPLETE,
                                 output_path=str(dest / "cmp.xlsx"))

    def fake_resolve(report, selected_file=None):
        resolved_subdirs.append(report)
        return {"kind": "consolidated", "path": str(tmp / "canonical.xlsx")}

    import matrix as _matrix
    import settings as _settings
    import tsn_library as _tsn
    import reports as _reports
    with _Patch(_settings, "get_batch_dest", lambda: str(dest)), \
         _Patch(_settings, "get_matrix_baseline", lambda: "ssor-prod"), \
         _Patch(_settings, "get_matrix_tsn_selections", lambda: selections), \
         _Patch(_settings, "set_matrix_tsn_selections", lambda v: None), \
         _Patch(_matrix, "build_comparison", fake_build), \
         _Patch(validation.consolidation_meta, "require_published_comparison",
                lambda p, r: _published(diff_cells=0)), \
         _Patch(_reports, "matrix_rows", lambda: rows), \
         _Patch(_tsn, "is_registered", lambda r: r in registered), \
         _Patch(_tsn, "resolve", fake_resolve), \
         _Patch(_tsn, "canonicalize_selections", lambda s: (s, False)), \
         _Patch(_tsn, "reports", lambda: []):
        man = validation.run_validation(events=Events())

    cells = man["comparisons"]["cells"]
    ran = [c for c in cells if "status" in c]
    blocked = [c for c in cells if "skipped" in c]
    run_rows = {c["row"] for c in ran}
    check("the PDF row RUNS a comparison (mapped to its base family), never omitted",
          "highway_log_pdf" in run_rows and "highway_detail" in run_rows)
    check("TSN readiness resolved through the PDF row's BASE family key (not the PDF subdir)",
          "highway_log" in resolved_subdirs and "highway_log_pdf" not in resolved_subdirs)
    check("the selected TSN files were passed into every build_comparison call",
          bool(build_calls) and all(bc[3] and "highway_log" in bc[3] for bc in build_calls))
    check("a capability with no store data is BLOCKED, not silently dropped",
          any(c["row"] == "ramp_summary" and "skipped" in c for c in cells))
    check("the denominator counts every capability (expected = run + blocked, both shown)",
          man["totals"]["comparisons_expected"] == len(cells)
          and man["totals"]["comparisons_run"] == len(ran)
          and man["totals"]["comparisons_blocked"] == len(blocked)
          and len(blocked) >= 1 and len(ran) >= 2)


def test_worker_always_posts_terminal():
    """The ValidationWorker MUST post exactly one validate_done no matter what
    fails — an un-posted terminal wedges the single-task gate. Drive it with an
    evidence.collect that RAISES (the path outside the old try/except)."""
    print("ValidationWorker guarantees a terminal (gate-safety):")
    import queue as _queue
    import gui_worker
    import validation as _val
    import evidence as _ev

    q = _queue.Queue()
    with _Patch(_val, "run_validation", lambda events=None, should_cancel=None: {"totals": {}}), \
         _Patch(_ev, "collect", lambda **k: (_ for _ in ()).throw(RuntimeError("bundle boom"))):
        w = gui_worker.ValidationWorker(q)
        w.run()   # synchronous run (no .start()) so the queue is fully drained
    kinds = []
    while not q.empty():
        kinds.append(q.get_nowait()[0])
    terminals = [k for k in kinds if k == "validate_done"]
    check("a raising evidence.collect still posts exactly one validate_done",
          len(terminals) == 1, f"terminals={terminals} all={kinds}")

    q2 = _queue.Queue()
    totals = {
        "comparisons_run": 4, "comparisons_ok": 1,
        "comparisons_partial": 1, "comparisons_untrusted": 1,
        "comparisons_failed": 1, "comparisons_cancelled": 0,
        "comparisons_blocked": 2, "cancelled": False,
    }
    with _Patch(_val, "run_validation",
                lambda events=None, should_cancel=None: {"totals": totals}), \
         _Patch(_ev, "collect",
                lambda **k: {"ok": False, "message": "disk full"}):
        gui_worker.ValidationWorker(q2).run()
    payloads = []
    while not q2.empty():
        kind, payload = q2.get_nowait()
        if kind == "validate_done":
            payloads.append(payload)
    check("false collector result preserves its message and every outcome bucket",
          len(payloads) == 1 and payloads[0].get("message") == "disk full"
          and payloads[0].get("comparisons_partial") == 1
          and payloads[0].get("comparisons_untrusted") == 1
          and payloads[0].get("comparisons_failed") == 1
          and payloads[0].get("comparisons_blocked") == 2)


if __name__ == "__main__":
    print("W1 one-click validation:")
    test_manifest_and_cancel()
    test_degrades_on_family_error()
    test_evidence_carries_manifest()
    test_trust_semantics()
    test_tsn_stage_heals_stale_library()
    test_tsn_state_truth_table()
    test_ensure_tsn_ready_first_build()
    test_missing_explicit_tsn_is_not_substituted()
    test_007_full_capability_coverage()
    test_worker_always_posts_terminal()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")

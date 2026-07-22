"""CMP-AUD-080 — durable CONTENT identity for every effective source.

The v1 folder fingerprint hashed (name, size, mtime_ns), so replacing a source
file with different same-length bytes and restoring its timestamp produced the
same fingerprint and the cached "match / 0 differences" stayed fresh. Evidence
adapters cached parsed TSN prints on the same metadata-only key.

Everything here drives the SHIPPED readers — artifact_store.fingerprint,
matrix_state's freshness, artifact_store.consolidated_fresh and the two
evidence print indexes — against the audit's exact tamper: same size, same
mtime_ns, same file id, different bytes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import artifact_store as a  # noqa: E402
import matrix_state  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        if detail:
            print(f"       {detail}")
        _failures.append(name)


def _tamper_in_place(path: Path, filler: bytes = b"Z") -> bool:
    """The audit's case: overwrite with different bytes of the SAME length, then
    put the timestamps back. Returns True when stat is byte-identical after."""
    path = Path(path)
    before = os.stat(path)
    data = path.read_bytes()
    with open(path, "r+b") as f:
        f.write(filler * len(data))
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = os.stat(path)
    return ((before.st_size, before.st_mtime_ns, before.st_ino)
            == (after.st_size, after.st_mtime_ns, after.st_ino))


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_content_identity_"))

    print("the source fingerprint is CONTENT, not metadata:")
    store = tmp / "store"
    store.mkdir()
    (store / "route_001.xlsx").write_bytes(b"A" * 4096)
    (store / "route_002.xlsx").write_bytes(b"B" * 2048)
    fp0 = a.fingerprint(store)
    check("a fingerprint is produced and carries the v2 content schema",
          fp0.startswith("v2:2:"), fp0)
    identical = _tamper_in_place(store / "route_001.xlsx")
    check("the fixture reproduces the audit's tamper (stat byte-identical)",
          identical)
    fp1 = a.fingerprint(store)
    check("same-size, timestamp-restored content replacement CHANGES the fingerprint",
          fp0 != fp1, f"{fp0} -> {fp1}")
    check("an unchanged folder still fingerprints identically (no false staleness)",
          a.fingerprint(store) == fp1)

    print("the digest memo is change-token validated, never stat-only:")
    probe = tmp / "probe.bin"
    probe.write_bytes(b"A" * 8192)
    d0 = a.content_digest(probe)
    check("a repeat digest of an untouched file is served from the memo",
          a.content_digest(probe) == d0)
    _tamper_in_place(probe, b"Q")
    check("the memo does NOT serve a stale digest after a same-metadata rewrite",
          a.content_digest(probe) != d0)
    # A change token is only as fine as the clock that stamps it, so back-to-back
    # rewrites CAN share a ChangeTime (a CI runner produced exactly that). The
    # guarantee is therefore asserted directly — a same-metadata rewrite is never
    # served from the memo, whichever way the stamp fell — and the racy-window
    # rule that makes it hold is asserted on its own below.
    for i, filler in enumerate((b"R", b"S", b"T", b"U", b"V")):
        expected = a.content_digest(probe)
        identical = _tamper_in_place(probe, filler)
        check(f"same-tick rewrite #{i + 1}: the memo still cannot serve it stale",
              identical and a.content_digest(probe) != expected)
    if os.name == "nt":
        st = os.stat(probe)
        token = a._change_token(probe, st)
        check("a Windows change token is available for memo validation",
              token is not None)
        check("a just-changed file is NOT memoizable (the racy window)",
              a._memoizable(token) is False, repr(token))
        # ChangeTime cannot be backdated through any ordinary API (setting times
        # IS a change), so the window's far side is asserted on the pure
        # predicate, with a synthetic stamp one hour in the past.
        hour_ago = a._FILETIME_EPOCH_TICKS + (time.time_ns() // 100) - 36_000_000_000
        check("a file whose change stamp is an hour old IS memoizable",
              a._memoizable(token[:-1] + (hour_ago,)) is True)
        check("a token with no change stamp is never memoizable",
              a._memoizable(None) is False)

    print("the memo really is consulted once a file settles:")
    settled = tmp / "settled.bin"
    settled.write_bytes(b"S" * 4096)
    time.sleep(1.1)                       # past _RACY_WINDOW_NS — the one real wait
    first = a.content_digest(settled)
    key = os.path.normcase(str(settled))
    check("a settled file's digest is stored in the memo", key in a._DIGEST_MEMO,
          f"memo keys: {len(a._DIGEST_MEMO)}")
    if key in a._DIGEST_MEMO:
        token, _value = a._DIGEST_MEMO[key]
        a._DIGEST_MEMO[key] = (token, "sentinel-not-a-real-digest")
        check("a matching token short-circuits the re-read (the memo is live)",
              a.content_digest(settled) == "sentinel-not-a-real-digest")
        a._DIGEST_MEMO[key] = (token, first)
        _tamper_in_place(settled, b"Z")
        check("...and the tampered file still bypasses that memo entry",
              a.content_digest(settled) != first)

    print("matrix freshness reads the tamper as STALE:")
    fp_before = matrix_state._cell_input_fingerprint(store)
    record = {"input_fingerprint": fp_before}
    check("an untouched store is not reported changed",
          not matrix_state._inputs_changed(True, record, store))
    _tamper_in_place(store / "route_002.xlsx", b"Y")
    check("a same-metadata source replacement reports the cell's inputs changed",
          matrix_state._inputs_changed(True, record, store))

    print("the consolidated workbook's freshness sidecar follows content too:")
    consolidated = tmp / "consolidated.xlsx"
    consolidated.write_bytes(b"workbook")
    a.write_consolidated_fingerprint(consolidated, store)
    check("a just-built consolidated reads fresh", a.consolidated_fresh(consolidated, store))
    _tamper_in_place(store / "route_001.xlsx", b"X")
    check("a same-metadata input replacement makes the consolidated stale",
          not a.consolidated_fresh(consolidated, store))

    print("legacy metadata-only records migrate to stale exactly once:")
    legacy = tmp / "legacy.xlsx"
    legacy.write_bytes(b"workbook")
    sidecar = Path(str(legacy) + ".fingerprint.json")
    sidecar.write_text(json.dumps(
        {"schema_version": 1, "fingerprint": "v1:2:whatever"}), encoding="utf-8")
    check("a v1 fingerprint sidecar reads stale (one-time rebuild)",
          not a.consolidated_fresh(legacy, store))
    a.write_consolidated_fingerprint(legacy, store)
    check("the rebuilt sidecar is v2 and reads fresh",
          json.loads(sidecar.read_text(encoding="utf-8"))["schema_version"] == 2
          and a.consolidated_fresh(legacy, store))
    check("a v1 fingerprint string can never equal a v2 one",
          not a.fingerprint(store).startswith("v1:"))

    print("evidence print indexes are keyed on content identity:")
    import evidence_intersection_detail as eid
    import evidence_ramp_detail as erd
    for label, mod in (("Intersection Detail", eid), ("Ramp Detail", erd)):
        print_pdf = tmp / f"{label.replace(' ', '_')}.pdf"
        print_pdf.write_bytes(b"%PDF-1.4 not really a pdf" + b" " * 200)
        seeded = {"sig": a.content_digest(print_pdf), "records": {},
                  "districts": set(), "sentinel": label}
        mod._INDEX_CACHE[str(print_pdf)] = seeded
        check(f"{label}: an unchanged print is served from the parse cache",
              mod._print_index(print_pdf) is seeded)
        _tamper_in_place(print_pdf, b"#")
        try:
            mod._print_index(print_pdf)
            served_stale = True
        except Exception:                        # noqa: BLE001 - re-parse of a fake PDF
            served_stale = False
        check(f"{label}: a same-metadata print replacement is NOT served stale",
              not served_stale)


if __name__ == "__main__":
    print("CMP-AUD-080 content identity for sources, caches and evidence:")
    main()
    if _failures:
        print(f"\n{len(_failures)} check(s) FAILED")
        raise SystemExit(1)
    print("all good")

"""One versioned envelope for the matrix / by-day comparison CACHES (R1-R15).

The Everything matrix and the Compare-by-day view cache each comparison's verdict
+ discrepancy counts in a JSON sidecar so a snapshot stays a pure, offline
filesystem read. This wraps every such cache in ONE versioned envelope, so a
future format change is a single forward rebuild: an old (unversioned) cache, a
foreign file, or a different ``schema_version`` reads as EMPTY -- the matrix simply
recomputes -- never as corrupt, and the old file is left in place until a
successful recompute overwrites it.

P1 established the envelope (``counts`` in ``payload``). P2 extends the SAME
envelope with input-identity freshness (R1-R03): an optional envelope-level
``input_fingerprint`` slot (for a future single-output cache), while the matrix /
by-day caches -- which are MULTI-CELL (many cells per file) -- carry a PER-CELL
``input_fingerprint`` inside each payload record (the right granularity: one cell's
inputs changing must not invalidate the whole grid). They pass ``input_fingerprint
=None`` at the envelope level.

``SCHEMA_VERSION`` is the single FINAL released value carrying both the P1 fields and
the P2 fingerprint: P1 and P2 ship together with no intermediate version cut, so an
upgrading user (whose v0.17 caches are raw, unversioned dicts) rebuilds exactly ONCE
(RR3-C3).

On-disk shape:
    {"schema_version": N, "output_identity": <str>,
     "input_fingerprint": <str|"">, "payload": <the results dict>}
"""

# Bump ONLY when the cached record shape changes incompatibly; an older value then
# reads as empty (a one-time rebuild). v2 is the single released v0.18 value: it
# carries the P1 outcome fields AND the P2 per-cell input fingerprints, so the
# v0.17->v0.18 upgrade rebuilds the caches exactly once.
SCHEMA_VERSION = 2


def wrap(payload, output_identity="", input_fingerprint=None):
    """Envelope a results dict for writing. ``output_identity`` records which output
    the cache belongs to (e.g. the baseline key / day root). ``input_fingerprint`` is
    an OPTIONAL whole-cache input identity for a single-output cache; the multi-cell
    matrix / by-day caches pass None and carry per-cell fingerprints in the records."""
    return {"schema_version": SCHEMA_VERSION,
            "output_identity": str(output_identity),
            "input_fingerprint": "" if input_fingerprint is None else str(input_fingerprint),
            "payload": payload if isinstance(payload, dict) else {}}


def unwrap(obj, output_identity=None, input_fingerprint=None):
    """The payload dict from a CURRENT-version envelope, else ``{}``.

    An old raw dict (no ``schema_version``), a foreign object, or a different
    ``schema_version`` -> ``{}`` (rebuild from scratch). When ``output_identity`` is
    given, a mismatch also reads as empty (the cache is for a different output); when
    ``input_fingerprint`` is given (a single-output cache), a mismatch reads as empty
    too (the inputs changed). The matrix / by-day callers pass None for both (the cache
    path scopes by baseline/day and per-cell freshness is per record), so their only
    migration trigger is the version bump."""
    if not isinstance(obj, dict) or obj.get("schema_version") != SCHEMA_VERSION:
        return {}
    if output_identity is not None and obj.get("output_identity") != str(output_identity):
        return {}
    if input_fingerprint is not None and obj.get("input_fingerprint") != str(input_fingerprint):
        return {}
    payload = obj.get("payload")
    return payload if isinstance(payload, dict) else {}

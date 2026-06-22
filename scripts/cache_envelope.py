"""One versioned envelope for the matrix / by-day comparison CACHES (R1-R15).

The Everything matrix and the Compare-by-day view cache each comparison's verdict
+ discrepancy counts in a JSON sidecar so a snapshot stays a pure, offline
filesystem read. This wraps every such cache in ONE versioned envelope, so a
future format change is a single forward rebuild: an old (unversioned) cache, a
foreign file, or a different ``schema_version`` reads as EMPTY -- the matrix simply
recomputes -- never as corrupt, and the old file is left in place until a
successful recompute overwrites it.

P1 establishes the envelope and carries ``counts`` (the existing verdict/diff
records, in ``payload``). P2 extends the SAME envelope with ``input_fingerprint``;
the released ``schema_version`` is the single final value carrying both, so an
upgrading user rebuilds exactly once (RR3-C3).

On-disk shape:
    {"schema_version": N, "output_identity": <str>, "payload": <the results dict>}
"""

# Bump ONLY when the cached record shape changes incompatibly; an older value then
# reads as empty (a one-time rebuild). P2 will set the single released value.
SCHEMA_VERSION = 1


def wrap(payload, output_identity=""):
    """Envelope a results dict for writing. ``output_identity`` records which output
    the cache belongs to (e.g. the baseline key / day root) for future identity
    checks; it is recorded now and consulted by P2."""
    return {"schema_version": SCHEMA_VERSION,
            "output_identity": str(output_identity),
            "payload": payload if isinstance(payload, dict) else {}}


def unwrap(obj, output_identity=None):
    """The payload dict from a CURRENT-version envelope, else ``{}``.

    An old raw dict (no ``schema_version``), a foreign object, or a different
    ``schema_version`` -> ``{}`` (rebuild from scratch). When ``output_identity`` is
    given, a mismatch also reads as empty (the cache is for a different output);
    P1 callers pass None (the cache path already scopes by baseline/day), so the
    only P1 migration trigger is the version."""
    if not isinstance(obj, dict) or obj.get("schema_version") != SCHEMA_VERSION:
        return {}
    if output_identity is not None and obj.get("output_identity") != str(output_identity):
        return {}
    payload = obj.get("payload")
    return payload if isinstance(payload, dict) else {}

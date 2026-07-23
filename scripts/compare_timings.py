"""Best-effort per-comparison DURATIONS, for the live ETA on the matrices and the
Compare tab (M1-B).

Diagnostic only: a read/write failure here never affects a comparison artifact,
its cache, or a published outcome. Samples are keyed by ``"<row_key>|<mode>"``
(e.g. ``"highway_log|tsn"``) — a report's vs-TSN build takes a characteristic
time regardless of which day/env/dest it ran in, so one small app-private file of
recent samples per key gives a useful estimate that carries across runs.

The store keeps the last ``_KEEP`` samples per key and estimates with their
median (robust to the odd slow run). No sample, no estimate — the caller shows
elapsed only rather than inventing a number.
"""
import json
import logging
import os

import paths

log = logging.getLogger("tsmis.gui")

_VERSION = 1
_KEEP = 20                                  # recent samples kept per key
_FILE = paths.CONFIG_FILE.parent / "compare_timings.json"


def _load():
    """The ``{key: [seconds, ...]}`` map, or ``{}`` on any read/shape problem."""
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # silent-ok: no/*corrupt* timings file is the normal first-run state — a missing ETA only costs a number, never truth
        return {}
    if not isinstance(data, dict) or data.get("v") != _VERSION:
        return {}
    samples = data.get("samples")
    return samples if isinstance(samples, dict) else {}


def _save(samples):
    try:
        _FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _FILE.with_name(_FILE.name + ".tmp")
        tmp.write_text(json.dumps({"v": _VERSION, "samples": samples}),
                       encoding="utf-8")
        os.replace(tmp, _FILE)
    except OSError as e:                     # diagnostic only — never raise
        log.debug("compare timings not saved (%s: %s)", type(e).__name__, e)


def record(key, seconds):
    """Append one measured cell duration for ``key`` (newest first, bounded)."""
    if not key or seconds is None or seconds < 0:
        return
    samples = _load()
    prev = samples.get(key)
    prev = [float(x) for x in prev if isinstance(x, (int, float))] if isinstance(prev, list) else []
    samples[key] = ([float(seconds)] + prev)[:_KEEP]
    _save(samples)


def _median(values):
    vals = sorted(v for v in values if isinstance(v, (int, float)) and v >= 0)
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0


def estimate_key(key, samples=None):
    """Median historical duration (seconds) for one cell key, or ``None``."""
    samples = _load() if samples is None else samples
    lst = samples.get(key)
    return _median(lst) if isinstance(lst, list) else None


def estimate_seconds(keys, fallback=None):
    """Rough total seconds for a run over ``keys`` (a list of ``"<row>|<mode>"``).

    Each key contributes its own median where known; an unknown key contributes
    ``fallback`` (e.g. this run's running average) or, absent that, the global
    median across all recorded samples. Returns ``None`` only when nothing at all
    is known (no history AND no fallback), so the UI can show elapsed-only.
    """
    keys = list(keys)
    if not keys:
        return 0.0
    samples = _load()
    global_median = _median([v for lst in samples.values()
                             if isinstance(lst, list) for v in lst])
    per_key = {k: estimate_key(k, samples) for k in set(keys)}
    if all(per_key[k] is None for k in per_key) and fallback is None and global_median is None:
        return None
    total = 0.0
    for k in keys:
        v = per_key.get(k)
        if v is None:
            v = fallback if fallback is not None else (global_median or 0.0)
        total += v
    return total

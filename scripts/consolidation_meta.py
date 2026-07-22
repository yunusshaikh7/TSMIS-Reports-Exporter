"""Producer-owned outcome SIDECAR for persistent consolidated workbooks (P1-R01).

A consolidated workbook is written by several paths — the matrix store consolidation,
``ExportWorker._auto_consolidate``, the GUI/console Consolidate tab
(``ConsolidateWorker``), and the TSN-library builders — and then REUSED across
comparisons (rebuilt only when a per-route source is newer). A PARTIAL consolidation
(inputs left out) must stay flagged on every later reuse, but a reuse has no fresh
``ConsolidateResult`` to read. So every persistent writer records the producer
completion in a tiny JSON sidecar beside the workbook through THIS module — the single
write/read boundary — and reuse recovers it here, so no writer can bypass it.

Robustness:
  * the sidecar is SCHEMA-VERSIONED and written ATOMICALLY (tmp + ``os.replace``) so a
    PROCESS INTERRUPTION mid-write can't leave a truncated file as the live sidecar.
    Sudden-power-loss durability is NOT claimed (CMP-AUD-131): temp contents are
    flushed but directory entries are not fsynced, so a power cut may lose or tear a
    just-installed file — the read side fails closed on anything malformed or
    inconsistent, which is the conservative sentinel through that unproven boundary;
  * read VALIDATES schema/vocabulary/types and DEGRADES SAFELY — a present-but-unusable
    sidecar reads as ``partial`` (conservative: a current-version artifact whose outcome
    can't be trusted must never render as a green ``complete``), while a workbook with NO
    sidecar reads as ``None`` (deliberate legacy back-compat -> the caller defaults to
    complete);
  * an mtime mismatch (the workbook was rebuilt by something that didn't update the
    sidecar) reads as ``None`` — treat a stale flag as absent, never as a false partial;
  * ``write_outcome`` returns a bool so a publication failure is OBSERVABLE to every
    caller (they must not announce a plain success for a non-complete artifact whose flag
    could not be recorded); and even when atomic publish, the fallback marker, AND the
    workbook deletion ALL fail, the already-written ``.tmp`` is RETAINED as a last-resort
    conservative sentinel (``read_completion`` falls back to it) so reuse never reads a
    sidecar-less non-complete workbook as green.
"""
import ast
import contextlib
import json
import hashlib
import logging
import math
import os
import re
import secrets
import stat
import threading
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional

import outcome
from comparison_contract import ArtifactGeneration, AttemptState, ComparisonOutcome

log = logging.getLogger("tsmis.consolidation_meta")

SCHEMA_VERSION = 1
COMPARISON_SCHEMA_VERSION = 3
_SUPPORTED_COMPARISON_SCHEMA_VERSIONS = frozenset({2, 3})
_MTIME_TOL_S = 1.0                 # THE float-mtime equality tolerance (matrix imports this)
_MAX_COMPARISON_SIDECAR_BYTES = 16 * 1024 * 1024
_COMPARISON_PAYLOAD_SCHEMA_VERSION = 1
_COMPARISON_PAYLOAD_ENCODING = "canonical-json-zlib-chunks-v1"
_COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES = 4 * 1024 * 1024
_MAX_COMPARISON_PAYLOAD_CHUNK_BYTES = 5 * 1024 * 1024
# The measured 41,000-trace boundary is 16,795,872 decoded bytes in five
# chunks.  Four times that real boundary leaves room for materially larger
# comparisons without accepting an effectively unbounded in-process decode.
_MAX_COMPARISON_PAYLOAD_DECODED_BYTES = 64 * 1024 * 1024
# One MiB beyond the decoded ceiling admits zlib framing/worst-case expansion
# for incompressible JSON while keeping the compressed resource budget bounded.
_MAX_COMPARISON_PAYLOAD_COMPRESSED_BYTES = 65 * 1024 * 1024
# The measured boundary expands 16.836:1.  A 32:1 ceiling gives just under 2x
# measured headroom while rejecting practical highly-compressible zlib bombs
# during manifest validation, before any sibling is opened or decompressed.
_MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO = 32
_MAX_COMPARISON_PAYLOAD_CHUNKS = (
    _MAX_COMPARISON_PAYLOAD_DECODED_BYTES
    + _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES - 1
) // _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES
_COMPARISON_PAYLOAD_SUFFIX = ".comparison-payload.zlib"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMPARISON_PUBLICATION_LOCK_NAME = ".tsmis-comparison-publication.lock"
_COMPARISON_PUBLICATION_LOCK_TIMEOUT_S = 60.0
_PAYLOAD_FALLBACK_SLOT_COUNT = 8
_PAYLOAD_BASENAME_RE = re.compile(
    r"^\.cmpv3-[0-9a-f]{64}-[0-9]{6}-[0-9a-f]{64}"
    r"(?:-f-(?:0[0-7]|[0-9a-f]{64}-[0-9a-f]{16}))?"
    r"\.comparison-payload\.zlib$")
_PAYLOAD_FALLBACK_NONCE_RE = re.compile(r"^[0-9a-f]{16}$")
_PUBLICATION_LOCAL_LOCKS = {}
_PUBLICATION_LOCAL_LOCKS_GUARD = threading.Lock()

# Windows/NTFS accepts long *paths* for a long-path-aware process, but each
# individual filename component still has this independent UTF-16 limit.  Python
# ``len`` counts Unicode code points, so it is not sufficient for non-BMP names.
_WINDOWS_COMPONENT_MAX_UTF16_UNITS = 255
_COMPARISON_META_SUFFIX = ".outcome.json"
_COMPARISON_SENTINEL_SUFFIX = ".tmp"
_COMPARISON_METADATA_TEMP_PREFIX = ".cmpmeta.tmp-"
_COMPARISON_METADATA_TEMP_TOKEN_BYTES = 16


def _windows_utf16_units(value):
    """Return Windows filename units (UTF-16 code units), never code points."""
    if not isinstance(value, str):
        raise ValueError("Windows filename component must be text")
    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError as e:
        raise ValueError(
            "Windows filename component contains an unpaired Unicode surrogate") from e


def _require_windows_component(value, label):
    """Reject a component Windows cannot represent, with an actionable delta."""
    units = _windows_utf16_units(value)
    if units > _WINDOWS_COMPONENT_MAX_UTF16_UNITS:
        excess = units - _WINDOWS_COMPONENT_MAX_UTF16_UNITS
        raise ValueError(
            f"comparison {label} filename is too long for Windows: {value!r} "
            f"uses {units} UTF-16 code units (limit "
            f"{_WINDOWS_COMPONENT_MAX_UTF16_UNITS}). Choose a shorter output "
            f"workbook name by at least {excess} UTF-16 code unit"
            f"{'s' if excess != 1 else ''}")
    return value


def _comparison_metadata_component_names(workbook):
    """Return the exact member/final-sidecar/fixed-sentinel basenames."""
    workbook = Path(workbook)
    sidecar = Path(str(workbook) + _COMPARISON_META_SUFFIX)
    sentinel = sidecar.with_name(sidecar.name + _COMPARISON_SENTINEL_SUFFIX)
    return workbook.name, sidecar.name, sentinel.name


def validate_comparison_metadata_paths(workbook):
    """Validate all workbook-derived comparison metadata components.

    This is both the producer's preflight primitive and the metadata boundary's
    defensive check.  It intentionally does not constrain the total path: the
    packaged executable is long-path-aware and Windows policy owns that separate
    capability decision.
    """
    member, sidecar, sentinel = _comparison_metadata_component_names(workbook)
    _require_windows_component(member, "workbook")
    _require_windows_component(sidecar, "sidecar")
    _require_windows_component(sentinel, "fixed publication sentinel")
    return member, sidecar, sentinel


def _comparison_metadata_temp_basename(token):
    """Short unpredictable temp name; independent of the selected workbook."""
    expected_chars = _COMPARISON_METADATA_TEMP_TOKEN_BYTES * 2
    if (not isinstance(token, str) or len(token) != expected_chars
            or any(char not in "0123456789abcdef" for char in token)):
        raise ValueError("comparison metadata temp token is malformed")
    return f"{_COMPARISON_METADATA_TEMP_PREFIX}{token}"


# Keep comparison metadata's implementation temp comfortably below the component
# ceiling.  Final sidecar/sentinel limits are checked against the selected name.
assert (_windows_utf16_units(_comparison_metadata_temp_basename(
            "0" * (_COMPARISON_METADATA_TEMP_TOKEN_BYTES * 2)))
        <= _WINDOWS_COMPONENT_MAX_UTF16_UNITS - 64)


def _payload_primary_basename(decoded_sha, index, digest):
    """Exact schema-v3 content-addressed primary basename."""
    return (f".cmpv3-{decoded_sha}-{index:06d}-{digest}"
            f"{_COMPARISON_PAYLOAD_SUFFIX}")


def _payload_slot_basename(decoded_sha, index, digest, slot):
    """Exact bounded deterministic conflict-slot basename newly written by v3."""
    return (f".cmpv3-{decoded_sha}-{index:06d}-{digest}-f-{slot:02d}"
            f"{_COMPARISON_PAYLOAD_SUFFIX}")


# New names retain substantial headroom (the legacy binding+nonce read shape is
# intentionally longer).  Runtime generation and manifest parsing validate each
# actual component as well, so this cannot be bypassed under ``python -O``.
_NEW_PAYLOAD_PRIMARY_MAX_NAME = _payload_primary_basename(
    "0" * 64, 999999, "0" * 64)
_NEW_PAYLOAD_SLOT_MAX_NAME = _payload_slot_basename(
    "0" * 64, 999999, "0" * 64, _PAYLOAD_FALLBACK_SLOT_COUNT - 1)
assert max(_windows_utf16_units(_NEW_PAYLOAD_PRIMARY_MAX_NAME),
           _windows_utf16_units(_NEW_PAYLOAD_SLOT_MAX_NAME)) \
       <= _WINDOWS_COMPONENT_MAX_UTF16_UNITS - 64


def meta_path(consolidated):
    """The sidecar path for a consolidated workbook: ``<workbook>.outcome.json``."""
    return Path(str(consolidated) + _COMPARISON_META_SUFFIX)


def _safe_mtime(p):
    try:
        return Path(p).stat().st_mtime
    except OSError:
        return None


_ABSENT = object()                 # _read_sidecar: the file does not exist
_STALE = object()                  # valid record, but for an older workbook generation
_COMPARISON = object()             # record_type=comparison: use the strict generation reader


@dataclass(frozen=True)
class ConsolidationOutcome:
    """One validated, mtime-coupled consolidation outcome.

    ``trusted`` is false for an emergency ``untrusted`` marker and for metadata
    whose contents cannot be validated. Such a record is always exposed as
    ``partial`` and never supplies invented counters. ``current`` is true for
    every returned record; demonstrably stale records are not returned by
    :func:`read_outcome`. ``source`` is ``sidecar`` or ``sentinel``.
    """

    completion: str
    skipped_inputs: Optional[int]
    failed_inputs: Optional[int]
    trusted: bool
    current: bool
    diagnostic: Optional[str]
    source: str


@dataclass(frozen=True)
class ComparisonSidecarOutcome:
    """Strict read result for one member of a comparison generation.

    Typed fields are ``None`` when publication or validation is untrusted. The
    compatibility completion is then always ``partial``; callers never receive a
    green typed claim from a malformed, incomplete, or cross-member-inconsistent
    generation.
    """

    completion: str
    skipped_inputs: Optional[int]
    failed_inputs: Optional[int]
    trusted: bool
    current: bool
    diagnostic: Optional[str]
    source: str
    comparison_outcome: Optional[ComparisonOutcome]
    artifact_generation: Optional[ArtifactGeneration]
    self_member: Optional[Mapping[str, Any]]


def guard_allows(commit_guard, path):
    """Evaluate an optional target-aware filesystem guard fail-closed."""
    if commit_guard is None:
        return True
    try:
        return bool(commit_guard(Path(path)))
    except TypeError:
        # Compatibility for pre-existing no-argument commit guards.
        try:
            return bool(commit_guard())
        except Exception as e:  # noqa: BLE001 - callback failure denies mutation
            log.error("consolidation destination guard failed (%s: %s)",
                      type(e).__name__, e)
            return False
    except Exception as e:  # noqa: BLE001 - callback failure denies mutation
        log.error("consolidation destination guard failed (%s: %s)",
                  type(e).__name__, e)
        return False


def _untrusted_outcome(source, diagnostic):
    """Return a fail-closed record without inventing unavailable counters."""
    return ConsolidationOutcome(
        completion=outcome.PARTIAL,
        skipped_inputs=None,
        failed_inputs=None,
        trusted=False,
        current=True,
        diagnostic=diagnostic,
        source=source,
    )


def _read_sidecar(path, consolidated, source="sidecar"):
    """Read and validate one sidecar/sentinel in one mtime-coupled operation.

    Returns ``_ABSENT``, ``_STALE``, or a :class:`ConsolidationOutcome`. A
    present record that cannot be validated becomes an untrusted ``partial``
    outcome and is never confused with absent legacy metadata. Never raises.
    """
    try:
        meta = _read_strict_json(path)
    except ValueError as e:
        return _untrusted_outcome(source, f"outcome metadata is unusable: {e}")
    if meta is _ABSENT:
        return _ABSENT

    if not isinstance(meta, dict):
        return _untrusted_outcome(source, "outcome metadata must be a JSON object")
    schema = meta.get("schema_version")
    if isinstance(schema, bool) or not isinstance(schema, int) or schema != SCHEMA_VERSION:
        return _untrusted_outcome(source, "outcome metadata has an unsupported schema_version")
    record_type = meta.get("record_type")
    if record_type == "comparison":
        return _COMPARISON
    if record_type is not None:
        return _untrusted_outcome(source, "outcome metadata has an invalid record_type")
    completion = meta.get("completion")
    if not isinstance(completion, str) or completion not in outcome.COMPLETIONS:
        return _untrusted_outcome(source, "outcome metadata has an invalid completion")
    built_at = meta.get("built_at_mtime")
    if isinstance(built_at, bool) or not isinstance(built_at, (int, float)):
        return _untrusted_outcome(source, "outcome metadata has an invalid built_at_mtime")
    try:
        built_at_float = float(built_at)
    except (OverflowError, ValueError):
        return _untrusted_outcome(source, "outcome metadata has an invalid built_at_mtime")
    if not math.isfinite(built_at_float):
        return _untrusted_outcome(source, "outcome metadata has an invalid built_at_mtime")

    cur_m = _safe_mtime(consolidated)
    if (cur_m is None or not math.isfinite(float(cur_m))
            or abs(built_at_float - cur_m) > _MTIME_TOL_S):
        return _STALE                        # rebuilt / demonstrably stale -> ignore

    marker = meta.get("untrusted", False)
    if not isinstance(marker, bool):
        return _untrusted_outcome(source, "outcome metadata has an invalid untrusted flag")

    missing = object()
    skipped = meta.get("skipped_inputs", missing)
    failed = meta.get("failed_inputs", missing)
    # The emergency marker intentionally has no counters. Keep its completion but
    # never convert unknown counts into a misleading zero.
    if marker and completion == outcome.PARTIAL and skipped is missing and failed is missing:
        return ConsolidationOutcome(
            completion=outcome.PARTIAL,
            skipped_inputs=None,
            failed_inputs=None,
            trusted=False,
            current=True,
            diagnostic="producer marked outcome metadata untrusted; input counts unavailable",
            source=source,
        )
    if skipped is missing or failed is missing:
        return _untrusted_outcome(source, "outcome metadata is missing input counters")
    if (isinstance(skipped, bool) or not isinstance(skipped, int) or skipped < 0
            or isinstance(failed, bool) or not isinstance(failed, int) or failed < 0):
        return _untrusted_outcome(
            source, "outcome metadata input counters must be non-negative integers")
    if completion == outcome.COMPLETE and (skipped or failed):
        return _untrusted_outcome(
            source, "complete outcome metadata cannot report skipped or failed inputs")
    if marker:
        return ConsolidationOutcome(
            completion=outcome.PARTIAL,
            skipped_inputs=skipped,
            failed_inputs=failed,
            trusted=False,
            current=True,
            diagnostic="producer marked outcome metadata untrusted",
            source=source,
        )
    return ConsolidationOutcome(
        completion=completion,
        skipped_inputs=skipped,
        failed_inputs=failed,
        trusted=True,
        current=True,
        diagnostic=None,
        source=source,
    )


def _silent_unlink(path):
    """Best-effort unlink; True iff the file is gone afterwards."""
    try:
        Path(path).unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _mark_untrusted(p, consolidated, commit_guard=None):
    """A DURABLE conservative state when atomic publication failed AND the derived workbook
    could not be removed: a direct (non-atomic — we are already in the degraded path)
    ``partial`` sidecar carrying the workbook's current mtime, so a later reuse reads
    ``partial`` instead of a false green. One rung of the fallback ladder — if this fails,
    write_outcome retains the valid ``.tmp`` sentinel or quarantines the workbook.
    Best-effort; True iff the marker was written."""
    if not guard_allows(commit_guard, p):
        return False
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema_version": SCHEMA_VERSION, "completion": outcome.PARTIAL,
                       "built_at_mtime": _safe_mtime(consolidated), "untrusted": True}, f)
        return True
    except OSError as e:
        log.warning("consolidation outcome marker for %s could not be written (%s: %s); "
                    "falling back to the retained sentinel / quarantine",
                    Path(consolidated).name, type(e).__name__, e)
        return False


def _quarantine(consolidated, commit_guard=None):
    """LAST resort when a NON-complete workbook's outcome could not be recorded by ANY
    means (no published sidecar, no marker, no usable ``.tmp`` sentinel) AND the workbook
    could not be removed: RENAME it aside so the canonical path resolves as MISSING (the
    resolver rebuilds it) and it can never read as a legacy-complete cell. The data is
    preserved at the quarantine name for diagnosis. Best-effort — a truly-locked workbook
    may refuse rename too (then the residual window is logged critically by the caller)."""
    consolidated = Path(consolidated)
    q = consolidated.with_name(consolidated.name + ".unverified")
    if (not guard_allows(commit_guard, consolidated)
            or not guard_allows(commit_guard, q)):
        return False
    try:
        _silent_unlink(q)                    # clear a prior quarantine so rename won't clash
        consolidated.rename(q)
        return True
    except OSError as e:
        log.error("could not quarantine %s (%s: %s)", consolidated.name, type(e).__name__, e)
        return False


def _app_version_from_file():
    """Read ``__version__`` from ``version.py`` beside ``scripts/`` without executing
    it — the fallback for isolated check contexts that put only ``scripts/`` on
    ``sys.path`` (``version.py`` lives one level up at the repo root). Parsed with
    ``ast`` so nothing in the file runs. ``"unknown"`` on any failure: a STABLE value
    that both stamps and compares equal (a safe no-op of the version gate), never a
    false-stale signal."""
    try:
        src = (Path(__file__).resolve().parent.parent / "version.py").read_text(
            encoding="utf-8")
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        return str(ast.literal_eval(node.value))
    except (OSError, ValueError, SyntaxError):  # silent-ok: fall through to the stable sentinel
        pass
    return "unknown"


def producer_app_version():
    """The app release that built a persistent consolidated workbook (CMP-AUD-084).

    Stamped in every outcome sidecar so a consolidation built by an OLDER parser /
    consolidator re-parses once after an upgrade — otherwise a corrected comparator
    would keep reading pre-fix rows from an unchanged-raw-inputs workbook. A shipped
    parser fix always rides a new release, so the app version is the semantic signal.
    Also the single ``{"app": ...}`` value the matrix cache records bind (via
    ``matrix_state.producer_identity``), so the comparison-cache and consolidation
    freshness gates agree. ``version.py`` is dependency-free; isolated checks that omit
    the repo root from ``sys.path`` fall back to reading it by path."""
    try:
        import version
        return str(version.__version__)
    except ModuleNotFoundError:  # silent-ok: scripts-only sys.path -> read version.py by file
        return _app_version_from_file()


def write_outcome(consolidated, result, extra=None, commit_guard=None):
    """Record `result`'s producer completion beside its workbook, ATOMICALLY — the
    boundary every persistent-consolidated writer calls right after a successful write.

    Returns True when the outcome is safely represented on disk: a trustworthy sidecar
    was published, OR the artifact is COMPLETE (an absent sidecar correctly reads
    complete), OR there was nothing to persist. Returns **False** only when a
    NON-complete (partial) artifact's flag could not be published — the caller MUST NOT
    announce a plain success, because the partial workbook may otherwise look complete.
    On that failure write_outcome still does everything it can to prevent a later false
    green: it cleans the temp file, leaves a durable conservative `partial` marker, and
    removes the derived workbook so it rebuilds. No-op (True) for a non-ok result or a
    falsy path."""
    if not consolidated or getattr(result, "status", None) != "ok":
        return True
    consolidated = Path(consolidated)
    comp = outcome.consolidate_completion_of(result)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "completion": comp,
        "skipped_inputs": int(getattr(result, "skipped_inputs", 0) or 0),
        "failed_inputs": int(getattr(result, "failed_inputs", 0) or 0),
        "built_at_mtime": _safe_mtime(consolidated),
        # CMP-AUD-084: the semantic producer version; `matrix._consolidated_stale`
        # rebuilds a workbook stamped by an older parser/consolidator once on upgrade.
        "producer_app_version": producer_app_version(),
    }
    if extra:
        payload.update(extra)          # additive producer metadata (e.g. the TSN
                                       # normalization version, D2); readers are
                                       # tolerant, so unknown keys are harmless

    p = meta_path(consolidated)
    tmp = p.with_name(p.name + ".tmp")
    if (not guard_allows(commit_guard, consolidated)
            or not guard_allows(commit_guard, p)
            or not guard_allows(commit_guard, tmp)):
        log.warning("consolidation outcome for %s: destination changed; no sidecar write",
                    consolidated.name)
        return False
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        if (not guard_allows(commit_guard, consolidated)
                or not guard_allows(commit_guard, p)
                or not guard_allows(commit_guard, tmp)):
            # Never clean through a pathname whose authority was lost. If the
            # original directory moved, the temp stays with that original object.
            return False
        os.replace(tmp, p)                       # atomic publish — never a half file
        return True
    except OSError as e:
        log.warning("could not publish consolidation outcome for %s: %s: %s",
                    consolidated.name, type(e).__name__, e)
        if comp == outcome.COMPLETE:
            if guard_allows(commit_guard, tmp):
                _silent_unlink(tmp)              # harmless; absent sidecar reads complete
            return guard_allows(commit_guard, consolidated)
        # A non-complete artifact must never later read as a green complete. Fallback
        # ladder (each rung only reached if the prior one failed):
        #   1. remove the workbook -> clean rebuild;
        #   2. write a direct 'untrusted' final marker;
        #   3. retain a CONSERVATIVE .tmp sentinel — but ONLY one that itself reads
        #      `partial` (a valid+current partial, or a present-but-corrupt -> partial).
        #      A current `.tmp` that says `complete` (unrelated debris) must NOT certify
        #      THIS failed partial write, so it is rejected and the ladder continues;
        #   4. quarantine the workbook (rename) so resolvers can't select it — covers both
        #      the write-stage branch (no .tmp) AND an incompatible (complete/stale) .tmp;
        #   5. (all failed) log critically — the irreducible all-locked window.
        # read_completion validates the .tmp the same as the final sidecar, so a stale or
        # absent sentinel never forces a false partial AND never leaves a false green.
        if (guard_allows(commit_guard, consolidated)
                and _silent_unlink(consolidated)):
            if guard_allows(commit_guard, tmp):
                _silent_unlink(tmp)
            return False
        if _mark_untrusted(p, consolidated, commit_guard):
            if guard_allows(commit_guard, tmp):
                _silent_unlink(tmp)
            return False
        if (guard_allows(commit_guard, tmp)
                and guard_allows(commit_guard, consolidated)):
            sentinel = _read_sidecar(tmp, consolidated, source="sentinel")
            if (isinstance(sentinel, ConsolidationOutcome)
                    and sentinel.completion == outcome.PARTIAL):
                return False                     # only a CONSERVATIVE (partial) .tmp protects it
        if _quarantine(consolidated, commit_guard):
            return False
        log.critical("consolidation outcome for %s: could not record, remove, mark, retain a "
                     "sentinel, or quarantine the incomplete workbook; a later reuse could "
                     "read it as complete", consolidated.name)
        return False


def read_extra(consolidated, key, default=None):
    """A single additive payload field from the workbook's sidecar, tolerantly:
    absent sidecar / unreadable / corrupt / missing key -> `default`. Used for
    producer metadata like the TSN normalization version (D2) — the FAIL-SAFE
    direction is the default (an unstampable read counts as stale)."""
    p = meta_path(Path(consolidated))
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:                    # silent-ok: absent sidecar is the normal pre-stamp state
        return default
    except ValueError as e:
        log.info("sidecar for %s unreadable for %r (%s: %s); using the default",
                 Path(consolidated).name, key, type(e).__name__, e)
        return default
    return data.get(key, default) if isinstance(data, dict) else default


def _is_nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _entry_identity(st):
    return (getattr(st, "st_dev", None), getattr(st, "st_ino", None),
            stat.S_IFMT(st.st_mode))


def _has_binding_identity(st):
    return (getattr(st, "st_dev", None) is not None
            and getattr(st, "st_ino", None) not in (None, 0))


def _ordinary_file_stat(path):
    """lstat one ordinary, non-reparse file; return None when unprovable."""
    try:
        st = Path(path).stat(follow_symlinks=False)
    except (OSError, ValueError):  # silent-ok: unverifiable file state fails closed as absent/untrusted
        return None
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (not stat.S_ISREG(st.st_mode) or not _has_binding_identity(st)
            or bool(getattr(st, "st_file_attributes", 0) & reparse)):
        return None
    return st


def _ordinary_directory_identity(path):
    """Identity of one ordinary, non-reparse directory, or ``None``."""
    try:
        st = Path(path).stat(follow_symlinks=False)
    except (OSError, ValueError):  # silent-ok: unprovable parent identity denies the lease
        return None
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (not stat.S_ISDIR(st.st_mode) or not _has_binding_identity(st)
            or bool(getattr(st, "st_file_attributes", 0) & reparse)):
        return None
    return _entry_identity(st)


def _unlink_through_verified_handle(path, expected_identity):
    """Delete exactly the verified inode through a Windows handle (CMP-AUD-130).

    Pathname stat-then-unlink has a race: a same-path replacement between the
    identity check and the ``unlink`` deletes the FOREIGN file. Here the
    identity is verified on the very handle whose delete-on-close disposition
    performs the removal, so the check and the deletion are bound to one file
    object — a replacement present at open time is observed as an identity
    mismatch and retained untouched, and a replacement racing in AFTER the
    disposition is set survives at the name while only our inode dies.

    Returns ``"deleted"``, ``"absent"``, ``"retained"`` (mismatch, reparse,
    directory, or any uncertainty — fail closed, keep the file), or
    ``"unsupported"`` (non-Windows/ctypes-less: callers keep their documented
    best-effort pathname semantics).
    """
    if os.name != "nt":
        return "unsupported"
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:  # silent-ok: no ctypes -> documented best-effort fallback
        return "unsupported"

    class _ByHandleInfo(ctypes.Structure):
        _fields_ = [("dwFileAttributes", wintypes.DWORD),
                    ("ftCreationTime", wintypes.FILETIME),
                    ("ftLastAccessTime", wintypes.FILETIME),
                    ("ftLastWriteTime", wintypes.FILETIME),
                    ("dwVolumeSerialNumber", wintypes.DWORD),
                    ("nFileSizeHigh", wintypes.DWORD),
                    ("nFileSizeLow", wintypes.DWORD),
                    ("nNumberOfLinks", wintypes.DWORD),
                    ("nFileIndexHigh", wintypes.DWORD),
                    ("nFileIndexLow", wintypes.DWORD)]

    class _DispositionInfo(ctypes.Structure):
        _fields_ = [("DeleteFile", wintypes.BOOLEAN)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel32.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_ByHandleInfo)]
    kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    DELETE, FILE_READ_ATTRIBUTES = 0x00010000, 0x0080
    SHARE_ALL, OPEN_EXISTING = 0x7, 3
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    NOT_ORDINARY = 0x400 | 0x10          # reparse point / directory
    handle = kernel32.CreateFileW(
        ctypes.c_wchar_p(os.fspath(path)), DELETE | FILE_READ_ATTRIBUTES,
        SHARE_ALL, None, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, None)
    if handle is None or handle == wintypes.HANDLE(-1).value:
        # ERROR_FILE_NOT_FOUND / ERROR_PATH_NOT_FOUND == verified absence.
        return ("absent" if ctypes.get_last_error() in (2, 3) else "retained")
    try:
        info = _ByHandleInfo()
        if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
            return "retained"
        identity = (info.dwVolumeSerialNumber,
                    (info.nFileIndexHigh << 32) | info.nFileIndexLow,
                    stat.S_IFREG)
        if (info.dwFileAttributes & NOT_ORDINARY
                or identity != tuple(expected_identity)):
            return "retained"
        disposition = _DispositionInfo(True)
        if not kernel32.SetFileInformationByHandle(
                handle, 4,                       # FileDispositionInfo
                ctypes.byref(disposition), ctypes.sizeof(disposition)):
            return "retained"
        return "deleted"
    finally:
        kernel32.CloseHandle(handle)


def _publication_lock_key(parent):
    """Canonical local-process key for one comparison output directory."""
    parent = Path(parent)
    try:
        resolved = parent.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise OSError("comparison publication parent cannot be resolved") from e
    return os.path.normcase(os.path.abspath(os.fspath(resolved)))


def _try_publication_os_lock(fd):
    """Try one crash-released exclusive byte-range lock without blocking."""
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (OSError, ValueError):  # silent-ok: busy/unsupported OS lock is retried then denied
        return False


def _release_publication_os_lock(fd):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except (OSError, ValueError):  # silent-ok: closing the fd still releases the process lock
        pass


@dataclass(frozen=True)
class _ComparisonPublicationLease:
    parent: Path
    parent_identity: tuple
    lock_path: Path
    lock_identity: tuple
    fd: int


def _publication_lease_current(lease, commit_guard=None):
    """Revalidate the held lock, its namespace, and the caller's ownership."""
    try:
        opened = os.fstat(lease.fd)
    except (OSError, ValueError):  # silent-ok: a broken held fd makes the lease non-current
        return False
    current_lock = _ordinary_file_stat(lease.lock_path)
    return (
        _ordinary_directory_identity(lease.parent) == lease.parent_identity
        and stat.S_ISREG(opened.st_mode)
        and _entry_identity(opened) == lease.lock_identity
        and current_lock is not None
        and _entry_identity(current_lock) == lease.lock_identity
        and guard_allows(commit_guard, lease.parent)
        and guard_allows(commit_guard, lease.lock_path)
    )


@contextlib.contextmanager
def _comparison_publication_lease(parent, commit_guard=None):
    """Serialize all comparison metadata mutation in one sibling directory.

    The permanent lock file is never unlinked.  The keyed Python lock covers
    overlapping threads, while the byte-range lock is released automatically if
    a process exits or crashes.  Keeping both is deliberate: platform file-lock
    semantics for two handles in one process are not a portable thread mutex.
    """
    parent = Path(parent)
    key = _publication_lock_key(parent)
    with _PUBLICATION_LOCAL_LOCKS_GUARD:
        local_lock = _PUBLICATION_LOCAL_LOCKS.setdefault(key, threading.Lock())
    if not local_lock.acquire(timeout=_COMPARISON_PUBLICATION_LOCK_TIMEOUT_S):
        raise TimeoutError("comparison publication local lock timed out")

    fd = None
    os_locked = False
    try:
        parent_identity = _ordinary_directory_identity(parent)
        lock_path = parent / _COMPARISON_PUBLICATION_LOCK_NAME
        if (parent_identity is None
                or not guard_allows(commit_guard, parent)
                or not guard_allows(commit_guard, lock_path)):
            raise OSError("comparison publication parent/lock is not authorized")
        flags = (os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
                 | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0))
        fd = os.open(lock_path, flags, 0o600)
        opened = os.fstat(fd)
        current = _ordinary_file_stat(lock_path)
        if (not stat.S_ISREG(opened.st_mode) or not _has_binding_identity(opened)
                or current is None
                or _entry_identity(current) != _entry_identity(opened)):
            raise OSError("comparison publication lock is not an ordinary bound file")
        lock_identity = _entry_identity(opened)

        deadline = time.monotonic() + _COMPARISON_PUBLICATION_LOCK_TIMEOUT_S
        while not _try_publication_os_lock(fd):
            if (time.monotonic() >= deadline
                    or _ordinary_directory_identity(parent) != parent_identity
                    or not guard_allows(commit_guard, parent)
                    or not guard_allows(commit_guard, lock_path)):
                raise TimeoutError("comparison publication process lock timed out")
            time.sleep(0.05)
        os_locked = True
        lease = _ComparisonPublicationLease(
            parent=parent, parent_identity=parent_identity,
            lock_path=lock_path, lock_identity=lock_identity, fd=fd)
        if not _publication_lease_current(lease, commit_guard):
            raise OSError("comparison publication lease changed during acquisition")
        yield lease
    finally:
        if os_locked and fd is not None:
            _release_publication_os_lock(fd)
        if fd is not None:
            try:
                os.close(fd)
            except OSError:  # silent-ok: process teardown also releases the lock
                pass
        local_lock.release()


def _bound_file_digest(path):
    """Return a stable ordinary file's sha256/size/mtime facts, or None."""
    path = Path(path)
    before = _ordinary_file_stat(path)
    if before is None:
        return None
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0))
    try:
        fd = os.open(path, flags)
    except (OSError, ValueError):  # silent-ok: an unopenable member cannot be certified
        return None
    digest = hashlib.sha256()
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode) or not _has_binding_identity(opened)
                or _entry_identity(opened) != _entry_identity(before)):
            return None
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    except OSError:  # silent-ok: an incomplete digest is rejected by returning None
        return None
    finally:
        try:
            os.close(fd)
        except OSError:  # silent-ok: descriptor cleanup cannot restore trust or change the verdict
            pass
    after = _ordinary_file_stat(path)
    if (after is None or _entry_identity(after) != _entry_identity(opened)
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns):
        return None
    return {
        "sha256": digest.hexdigest(),
        "size": opened.st_size,
        "mtime_ns": opened.st_mtime_ns,
        "mtime": opened.st_mtime,
    }


def _reject_json_constant(value):
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _read_bound_bytes(path, max_bytes, label="sidecar"):
    """Identity-bind and read one bounded ordinary file, or return ``_ABSENT``."""
    path = Path(path)
    before = _ordinary_file_stat(path)
    if before is None:
        try:
            path.lstat()
        except (FileNotFoundError, NotADirectoryError):
            return _ABSENT
        except (OSError, ValueError) as e:
            raise ValueError(f"{label} presence could not be verified") from e
        raise ValueError(f"{label} is not an ordinary file")
    if before.st_size > max_bytes:
        raise ValueError(f"{label} exceeds its size limit")
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0))
    try:
        fd = os.open(path, flags)
    except (OSError, ValueError) as e:
        raise ValueError(f"{label} is present but unreadable") from e
    try:
        opened = os.fstat(fd)
        if (_entry_identity(opened) != _entry_identity(before)
                or not stat.S_ISREG(opened.st_mode)
                or not _has_binding_identity(opened)):
            raise ValueError(f"{label} identity changed while opening")
        raw = bytearray()
        while len(raw) <= max_bytes:
            chunk = os.read(fd, min(1024 * 1024,
                                    max_bytes + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > max_bytes:
            raise ValueError(f"{label} exceeds its size limit")
    except OSError as e:
        raise ValueError(f"{label} could not be read completely") from e
    finally:
        try:
            os.close(fd)
        except OSError:  # silent-ok: descriptor cleanup after a completed/failed read is best-effort
            pass
    after = _ordinary_file_stat(path)
    if (after is None or _entry_identity(after) != _entry_identity(opened)
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns):
        raise ValueError(f"{label} changed while it was being read")
    return bytes(raw)


def _decode_strict_json(raw, label="sidecar"):
    """Strictly decode UTF-8 JSON with duplicate keys/non-finite values rejected."""
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object,
                          parse_constant=_reject_json_constant)
    except (UnicodeError, ValueError, RecursionError) as e:
        raise ValueError(f"{label} is not strict UTF-8 JSON") from e


def _read_strict_json(path):
    """Identity-bind and strictly decode one bounded JSON sidecar."""
    raw = _read_bound_bytes(
        path, _MAX_COMPARISON_SIDECAR_BYTES, "sidecar")
    if raw is _ABSENT:
        return _ABSENT
    return _decode_strict_json(raw, "sidecar")


def _canonical_json_bytes(payload):
    """One canonical UTF-8 JSON representation used by envelopes and payloads."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _matches_canonical_json(payload, raw):
    """Compare canonical encoder output to ``raw`` without joining a second copy.

    The decoded JSON object and aggregate input bytes are necessarily resident
    for typed validation.  Canonicality must not add another payload-sized bytes
    object on top: ``iterencode`` output is UTF-8 encoded in bounded text slices
    and compared directly against a read-only view of the existing aggregate.
    """
    encoder = json.JSONEncoder(
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False)
    view = memoryview(raw)
    offset = 0
    try:
        for piece in encoder.iterencode(payload):
            # CPython commonly emits small pieces, but does not promise a size
            # bound (one very large JSON string can be one piece).  Bound the
            # additional UTF-8 bytes even in that adversarial shape.
            for start in range(0, len(piece), 64 * 1024):
                encoded = piece[start:start + 64 * 1024].encode("utf-8")
                end = offset + len(encoded)
                if end > len(view) or view[offset:end] != encoded:
                    return False
                offset = end
    except (TypeError, ValueError, RecursionError, UnicodeError):  # silent-ok: encoder failure is noncanonical
        return False
    return offset == len(view)


def _atomic_write_bytes(path, raw, commit_guard=None, *, max_bytes,
                        short_comparison_temp=False):
    """Publish bounded bytes through an unpredictable, exclusively-created temp."""
    path = Path(path)
    if type(raw) is not bytes or len(raw) > max_bytes:
        return False
    if (not guard_allows(commit_guard, path.parent)
            or not guard_allows(commit_guard, path)):
        return False

    tmp = None
    expected = None
    for _attempt in range(32):
        token = secrets.token_hex(_COMPARISON_METADATA_TEMP_TOKEN_BYTES)
        candidate = path.with_name(
            _comparison_metadata_temp_basename(token)
            if short_comparison_temp
            else f".{path.name}.tmp-{token}")
        if not guard_allows(commit_guard, candidate):
            return False
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0))
        try:
            fd = os.open(candidate, flags, 0o600)
        except FileExistsError:  # silent-ok: unpredictable collision retries
            continue
        except OSError:  # silent-ok: inability to reserve denies publication
            return False
        try:
            opened = os.fstat(fd)
            if not _has_binding_identity(opened) or not stat.S_ISREG(opened.st_mode):
                raise OSError("exclusive metadata temp lacks a binding file identity")
            expected = _entry_identity(opened)
            with os.fdopen(fd, "wb", closefd=True) as stream:
                stream.write(raw)
                stream.flush()
        except OSError:  # silent-ok: failed write enters identity-bound cleanup
            try:
                os.close(fd)
            except OSError:  # silent-ok: descriptor may already be closed
                pass
            current = _ordinary_file_stat(candidate)
            if (current is not None and _entry_identity(current) == expected
                    and guard_allows(commit_guard, candidate)):
                try:
                    candidate.unlink()
                except OSError:  # silent-ok: non-authoritative temp residue
                    pass
            return False
        tmp = candidate
        break
    if tmp is None:
        return False

    published = False
    try:
        current = _ordinary_file_stat(tmp)
        if (current is None or _entry_identity(current) != expected
                or current.st_size != len(raw)
                or not guard_allows(commit_guard, path.parent)
                or not guard_allows(commit_guard, path)
                or not guard_allows(commit_guard, tmp)):
            return False
        os.replace(tmp, path)
        published = True
        return True
    except OSError:  # silent-ok: failed replacement remains observable
        return False
    finally:
        if not published:
            current = _ordinary_file_stat(tmp)
            if (current is not None and _entry_identity(current) == expected
                    and guard_allows(commit_guard, tmp)):
                try:
                    tmp.unlink()
                except OSError:  # silent-ok: non-authoritative temp residue
                    pass


def _atomic_write_json(path, payload, commit_guard=None):
    """Publish JSON through an unpredictable, exclusively-created temp sibling."""
    try:
        raw = _canonical_json_bytes(payload)
    except (TypeError, ValueError, RecursionError):  # silent-ok: unserializable metadata is never published
        return False
    return _atomic_write_bytes(
        path, raw, commit_guard, max_bytes=_MAX_COMPARISON_SIDECAR_BYTES,
        short_comparison_temp=(isinstance(payload, Mapping)
                               and payload.get("record_type") == "comparison"))


_MEMBER_KEYS = frozenset({
    "flavor", "relative_path", "path", "canonical_path_at_write",
    "commit_role", "sha256", "size", "mtime_ns",
})
_COMPARISON_FINAL_KEYS_V2 = frozenset({
    "schema_version", "record_type", "comparison_schema_version",
    "completion", "skipped_inputs", "failed_inputs", "built_at_mtime",
    "self_member", "comparison_outcome", "artifact_generation",
})
_COMPARISON_FINAL_KEYS_V3 = frozenset({
    "schema_version", "record_type", "comparison_schema_version",
    "completion", "skipped_inputs", "failed_inputs", "built_at_mtime",
    "self_member", "comparison_payload", "artifact_generation",
})
_COMPARISON_SENTINEL_KEYS = frozenset({
    "schema_version", "record_type", "comparison_schema_version",
    "publication_sentinel", "untrusted", "completion", "skipped_inputs",
    "failed_inputs", "built_at_mtime", "generation_id", "self_member",
})
_COMPARISON_PAYLOAD_MANIFEST_KEYS = frozenset({
    "schema_version", "encoding", "decoded_size", "decoded_sha256",
    "binding_sha256", "chunks",
})
_COMPARISON_PAYLOAD_CHUNK_KEYS = frozenset({
    "relative_path", "size", "sha256", "decoded_size",
})


def _safe_relative_member(value):
    if (not isinstance(value, str) or not value
            or value in (".", "..") or "/" in value or "\\" in value
            or ":" in value or value[-1] in (" ", ".")
            or any(ord(char) < 32 for char in value)
            or Path(value).name != value
            or Path(value).suffix.casefold() != ".xlsx"):
        raise ValueError("member relative_path must be one .xlsx basename")
    validate_comparison_metadata_paths(Path(value))
    return value


def _strict_member(value):
    if not isinstance(value, Mapping) or set(value) != _MEMBER_KEYS:
        raise ValueError("artifact member has missing or unknown fields")
    flavor = value.get("flavor")
    if flavor not in ("formulas", "values"):
        raise ValueError("artifact member flavor must be formulas or values")
    relative = _safe_relative_member(value.get("relative_path"))
    provenance = value.get("path")
    canonical = value.get("canonical_path_at_write")
    if (not isinstance(provenance, str) or not provenance
            or not isinstance(canonical, str) or not canonical):
        raise ValueError("artifact member provenance paths must be non-empty strings")
    # ``artifact_store._resolved_identity`` intentionally applies Windows
    # normcase to the canonical path.  Compare basenames under that same path
    # identity rule; a safe uppercase filename must not become unpublishable
    # merely because its canonical identity is lowercase.
    relative_key = os.path.normcase(relative)
    if (os.path.normcase(Path(provenance).name) != relative_key
            or os.path.normcase(Path(canonical).name) != relative_key):
        raise ValueError("artifact member provenance basename is inconsistent")
    role = value.get("commit_role")
    if role not in ("canonical", "best_effort"):
        raise ValueError("artifact member commit_role is invalid")
    digest = value.get("sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ValueError("artifact member sha256 must be 64 lowercase hex characters")
    size = value.get("size")
    mtime_ns = value.get("mtime_ns")
    if not _is_nonnegative_int(size) or not _is_nonnegative_int(mtime_ns):
        raise ValueError("artifact member size/mtime_ns must be non-negative integers")
    return {
        "flavor": flavor,
        "relative_path": relative,
        "path": provenance,
        "canonical_path_at_write": canonical,
        "commit_role": role,
        "sha256": digest,
        "size": size,
        "mtime_ns": mtime_ns,
    }


def _strict_comparison_outcome(value):
    if not isinstance(value, Mapping):
        raise ValueError("comparison_outcome must be an object")
    typed = ComparisonOutcome.from_dict(value)
    if typed.to_dict() != dict(value):
        raise ValueError("comparison_outcome is not a canonical typed payload")
    if (typed.status != "ok" or typed.completion not in (outcome.COMPLETE, outcome.PARTIAL)
            or typed.verdict not in ("match", "diff") or not typed.counts.known):
        raise ValueError("comparison_outcome does not describe a committed comparison")
    if typed.completion == outcome.COMPLETE and (typed.warnings or typed.failures):
        raise ValueError("complete comparison_outcome cannot report warnings/failures")
    return typed


def _strict_artifact_generation(value, comparison_completion):
    if not isinstance(value, Mapping):
        raise ValueError("artifact_generation must be an object")
    typed = ArtifactGeneration.from_dict(value)
    if typed.to_dict() != dict(value):
        raise ValueError("artifact_generation is not a canonical typed payload")
    if (not typed.generation_id or typed.generation_id.strip() != typed.generation_id
            or len(typed.generation_id) > 256):
        raise ValueError("artifact generation_id is invalid")
    if typed.completion != comparison_completion:
        raise ValueError("artifact/comparison completion claims disagree")
    if typed.publication_state != "committed":
        raise ValueError("artifact generation is not committed")
    if typed.requested_mode not in ("formulas", "values", "both"):
        raise ValueError("artifact generation requested_mode is invalid")
    if not typed.members or len(typed.members) > 2:
        raise ValueError("artifact generation must contain one or two members")
    members = tuple(_strict_member(item) for item in typed.members)
    flavors = tuple(member["flavor"] for member in members)
    if len(set(flavors)) != len(flavors):
        raise ValueError("artifact generation contains duplicate member flavors")
    if typed.requested_mode == "formulas" and flavors != ("formulas",):
        raise ValueError("formulas generation must contain one formulas member")
    if typed.requested_mode == "values" and flavors != ("values",):
        raise ValueError("values generation must contain one values member")
    if typed.requested_mode == "both" and "values" not in flavors:
        raise ValueError("both generation must contain its canonical values member")
    for member in members:
        expected_role = ("best_effort" if typed.requested_mode == "both"
                         and member["flavor"] == "formulas" else "canonical")
        if member["commit_role"] != expected_role:
            raise ValueError("artifact member commit_role contradicts requested_mode")
    digests = dict(typed.content_digests)
    if set(digests) != set(flavors):
        raise ValueError("content_digests keys must exactly match member flavors")
    for member in members:
        if digests.get(member["flavor"]) != member["sha256"]:
            raise ValueError("content_digests does not mirror the member sha256")
    return typed, members


def _strict_payload_manifest(value):
    """Validate one schema-v1 manifest for the canonical outcome payload.

    The primary name remains stable for cross-generation deduplication. New
    writers use one of eight bounded content-addressed fallback slots when that
    primary contains conflicting bytes. Legacy binding+nonce fallback names are
    still accepted on read so already-published schema-v1 manifests remain valid.
    """
    if (not isinstance(value, Mapping)
            or set(value) != _COMPARISON_PAYLOAD_MANIFEST_KEYS):
        raise ValueError("comparison payload manifest has missing or unknown fields")
    if (type(value.get("schema_version")) is not int
            or value.get("schema_version") != _COMPARISON_PAYLOAD_SCHEMA_VERSION
            or value.get("encoding") != _COMPARISON_PAYLOAD_ENCODING):
        raise ValueError("comparison payload manifest schema/encoding is invalid")
    decoded_size = value.get("decoded_size")
    decoded_sha = value.get("decoded_sha256")
    binding_sha = value.get("binding_sha256")
    if (not _is_nonnegative_int(decoded_size) or decoded_size <= 0
            or decoded_size > _MAX_COMPARISON_PAYLOAD_DECODED_BYTES):
        raise ValueError("comparison payload decoded_size is invalid")
    if not isinstance(decoded_sha, str) or _SHA256_RE.fullmatch(decoded_sha) is None:
        raise ValueError("comparison payload decoded_sha256 is invalid")
    if not isinstance(binding_sha, str) or _SHA256_RE.fullmatch(binding_sha) is None:
        raise ValueError("comparison payload binding_sha256 is invalid")
    chunks = value.get("chunks")
    if (not isinstance(chunks, (list, tuple)) or not chunks
            or len(chunks) > _MAX_COMPARISON_PAYLOAD_CHUNKS):
        raise ValueError("comparison payload chunks are missing or excessive")

    normalized = []
    decoded_total = 0
    compressed_total = 0
    names = set()
    for index, item in enumerate(chunks):
        if (not isinstance(item, Mapping)
                or set(item) != _COMPARISON_PAYLOAD_CHUNK_KEYS):
            raise ValueError("comparison payload chunk has missing or unknown fields")
        relative = item.get("relative_path")
        size = item.get("size")
        digest = item.get("sha256")
        chunk_decoded = item.get("decoded_size")
        if (not isinstance(relative, str)
                or _PAYLOAD_BASENAME_RE.fullmatch(relative) is None
                or Path(relative).name != relative):
            raise ValueError("comparison payload chunk path is unsafe")
        _require_windows_component(relative, "payload chunk")
        if (not _is_nonnegative_int(size) or size <= 0
                or size > _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES):
            raise ValueError("comparison payload chunk size is invalid")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise ValueError("comparison payload chunk sha256 is invalid")
        if (not _is_nonnegative_int(chunk_decoded) or chunk_decoded <= 0
                or chunk_decoded > _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES):
            raise ValueError("comparison payload chunk decoded_size is invalid")
        primary_relative = _payload_primary_basename(
            decoded_sha, index, digest)
        fallback_prefix = (
            f".cmpv3-{decoded_sha}-{index:06d}-{digest}-f-")
        if relative != primary_relative:
            if (not relative.startswith(fallback_prefix)
                    or not relative.endswith(_COMPARISON_PAYLOAD_SUFFIX)):
                raise ValueError(
                    "comparison payload chunks are reordered or misnamed")
            fallback_key = relative[
                len(fallback_prefix):-len(_COMPARISON_PAYLOAD_SUFFIX)]
            slot_names = {f"{slot:02d}"
                          for slot in range(_PAYLOAD_FALLBACK_SLOT_COUNT)}
            legacy_prefix = f"{binding_sha}-"
            legacy_nonce = (fallback_key[len(legacy_prefix):]
                            if fallback_key.startswith(legacy_prefix) else "")
            if (fallback_key not in slot_names
                    and _PAYLOAD_FALLBACK_NONCE_RE.fullmatch(legacy_nonce) is None):
                raise ValueError(
                    "comparison payload fallback slot/name is malformed")
        name_key = os.path.normcase(relative)
        if name_key in names:
            raise ValueError("comparison payload chunk names must be unique")
        names.add(name_key)
        if index < len(chunks) - 1:
            if chunk_decoded != _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES:
                raise ValueError("non-final payload chunks must have canonical decoded size")
        decoded_total += chunk_decoded
        compressed_total += size
        if compressed_total > _MAX_COMPARISON_PAYLOAD_COMPRESSED_BYTES:
            raise ValueError("comparison payload compressed total exceeds its limit")
        normalized.append({
            "relative_path": relative,
            "size": size,
            "sha256": digest,
            "decoded_size": chunk_decoded,
        })
    if decoded_total != decoded_size:
        raise ValueError("comparison payload chunk sizes do not equal decoded_size")
    if decoded_total > compressed_total * _MAX_COMPARISON_PAYLOAD_EXPANSION_RATIO:
        raise ValueError(
            "comparison payload decoded-to-compressed expansion exceeds its limit")
    return {
        "schema_version": _COMPARISON_PAYLOAD_SCHEMA_VERSION,
        "encoding": _COMPARISON_PAYLOAD_ENCODING,
        "decoded_size": decoded_size,
        "decoded_sha256": decoded_sha,
        "binding_sha256": binding_sha,
        "chunks": normalized,
    }


def _comparison_payload_binding_sha256(
        decoded_sha, completion, skipped_inputs, failed_inputs,
        artifact_generation):
    """Bind external outcome bytes to the exact common generation envelope."""
    return hashlib.sha256(_canonical_json_bytes({
        "decoded_sha256": decoded_sha,
        "completion": completion,
        "skipped_inputs": skipped_inputs,
        "failed_inputs": failed_inputs,
        "artifact_generation": artifact_generation,
    })).hexdigest()


def _preflight_comparison_payload(
        outcome_payload, *, completion, skipped_inputs, failed_inputs,
        artifact_generation):
    """Canonicalize/compress the typed outcome without mutating the filesystem."""
    try:
        raw = _canonical_json_bytes(outcome_payload)
    except (TypeError, ValueError, RecursionError) as e:
        raise ValueError("comparison outcome could not be canonically encoded") from e
    if not raw or len(raw) > _MAX_COMPARISON_PAYLOAD_DECODED_BYTES:
        raise ValueError("comparison outcome exceeds the decoded payload size limit")
    decoded_sha = hashlib.sha256(raw).hexdigest()
    binding_sha = _comparison_payload_binding_sha256(
        decoded_sha, completion, skipped_inputs, failed_inputs,
        artifact_generation)
    chunks = []
    payloads = []
    compressed_total = 0
    for index, start in enumerate(
            range(0, len(raw), _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES)):
        decoded = raw[start:start + _COMPARISON_PAYLOAD_DECODED_CHUNK_BYTES]
        compressed = zlib.compress(decoded, level=6)
        if (not compressed
                or len(compressed) > _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES):
            raise ValueError("comparison payload chunk exceeds its compressed size limit")
        compressed_total += len(compressed)
        if compressed_total > _MAX_COMPARISON_PAYLOAD_COMPRESSED_BYTES:
            raise ValueError("comparison payload compressed total exceeds its limit")
        digest = hashlib.sha256(compressed).hexdigest()
        relative = _payload_primary_basename(decoded_sha, index, digest)
        _require_windows_component(relative, "payload chunk")
        chunks.append({
            "relative_path": relative,
            "size": len(compressed),
            "sha256": digest,
            "decoded_size": len(decoded),
        })
        payloads.append((relative, compressed))
    manifest = _strict_payload_manifest({
        "schema_version": _COMPARISON_PAYLOAD_SCHEMA_VERSION,
        "encoding": _COMPARISON_PAYLOAD_ENCODING,
        "decoded_size": len(raw),
        "decoded_sha256": decoded_sha,
        "binding_sha256": binding_sha,
        "chunks": chunks,
    })
    return manifest, tuple(payloads)


def _payload_chunk_state(path, raw, descriptor, commit_guard=None):
    """Classify a destination as absent, exact, conflicting, or guard-denied."""
    path = Path(path)
    if (not guard_allows(commit_guard, path.parent)
            or not guard_allows(commit_guard, path)):
        return "denied"
    existing = _ordinary_file_stat(path)
    if existing is None:
        try:
            path.lstat()
        except (FileNotFoundError, NotADirectoryError):  # silent-ok: verified absence
            return "absent"
        except (OSError, ValueError):  # silent-ok: unverifiable presence is not publishable
            return "denied"
        return "conflict"             # symlink/reparse/directory/unknown entry
    try:
        current = _read_bound_bytes(
            path, _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES,
            "comparison payload chunk")
    except ValueError:  # silent-ok: unreadable content-addressed entry is conflicting
        return "conflict"
    if (guard_allows(commit_guard, path.parent)
            and guard_allows(commit_guard, path)
            and current is not _ABSENT
            and len(current) == descriptor["size"]
            and hashlib.sha256(current).hexdigest() == descriptor["sha256"]
            and current == raw):
        return "exact"
    return "conflict"


def _install_payload_temp_no_replace(source, destination):
    """Atomically install one complete sibling without replacing a destination."""
    if os.name == "nt":
        # Windows rename is atomic and fails when destination already exists.
        os.rename(source, destination)
    else:
        # POSIX rename replaces, so an atomic hard-link creation is the no-replace
        # primitive.  Both paths are siblings and therefore on the same filesystem.
        os.link(source, destination, follow_symlinks=False)


def _unlink_bound_payload_temp(path, expected_identity, commit_guard=None):
    """Best-effort cleanup bound to the temp inode we created (CMP-AUD-130).

    On Windows the removal happens through an identity-verified handle, so a
    same-path replacement racing in after the stat below is retained
    untouched. Elsewhere this remains pathname stat-then-unlink — best effort
    ONLY (the check and the unlink are not atomic there), acceptable for an
    unpredictable, non-authoritative temp name.
    """
    current = _ordinary_file_stat(path)
    if (current is None or _entry_identity(current) != expected_identity
            or not guard_allows(commit_guard, Path(path).parent)
            or not guard_allows(commit_guard, path)):
        return
    if _unlink_through_verified_handle(path, expected_identity) != "unsupported":
        return
    try:
        Path(path).unlink()
    except OSError:  # silent-ok: an unpredictable, non-authoritative temp cannot poison retry
        pass


def _publish_payload_chunk(path, raw, descriptor, commit_guard=None):
    """Install a content-addressed chunk process-interruption-safely, or
    reuse exact bytes.

    The deterministic final name is never opened for writing.  Bytes are fully
    written, fsynced, and identity-validated at an unpredictable sibling temp,
    then installed atomically without replacement.  A kill before install can
    leave only a non-authoritative temp; a kill after install leaves complete
    bytes.  A raced destination is reusable only when it is byte-identical.
    Sudden POWER LOSS is not covered (CMP-AUD-131): the parent directory entry
    is never fsynced, so the installed name may not survive a power cut —
    readers fail closed on missing or hash-mismatched chunks, which keeps the
    unproven durability boundary conservative rather than certified.
    """
    path = Path(path)
    if (type(raw) is not bytes
            or len(raw) != descriptor["size"]
            or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]):
        return False
    initial = _payload_chunk_state(path, raw, descriptor, commit_guard)
    if initial == "exact":
        return True
    if initial != "absent":
        return False

    tmp = None
    expected_identity = None
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
             | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0))
    for _attempt in range(32):
        # Keep the temp basename short: a strict conflict-fallback final is close
        # to Windows' 255-character component limit before a temp token is added.
        candidate = path.with_name(
            f".cmpv3-payload.tmp-{secrets.token_hex(16)}")
        if (not guard_allows(commit_guard, path.parent)
                or not guard_allows(commit_guard, path)
                or not guard_allows(commit_guard, candidate)):
            return False
        try:
            fd = os.open(candidate, flags, 0o600)
        except FileExistsError:  # silent-ok: unpredictable temp collision retries
            continue
        except OSError:  # silent-ok: inability to reserve a temp denies publication
            return False
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or not _has_binding_identity(opened):
                raise OSError("exclusive payload temp lacks a binding file identity")
            expected_identity = _entry_identity(opened)
            offset = 0
            view = memoryview(raw)
            while offset < len(raw):
                written = os.write(fd, view[offset:])
                if not isinstance(written, int) or written <= 0:
                    raise OSError("payload temp write made no progress")
                offset += written
            os.fsync(fd)
        except OSError:  # silent-ok: failed temp write enters identity-bound cleanup
            try:
                os.close(fd)
            except OSError:  # silent-ok: descriptor cleanup cannot make a temp authoritative
                pass
            _unlink_bound_payload_temp(candidate, expected_identity, commit_guard)
            return False
        try:
            os.close(fd)
        except OSError:  # silent-ok: close failure denies install and enters guarded cleanup
            _unlink_bound_payload_temp(candidate, expected_identity, commit_guard)
            return False
        tmp = candidate
        break
    if tmp is None:
        return False

    try:
        temp_stat = _ordinary_file_stat(tmp)
        if (temp_stat is None
                or _entry_identity(temp_stat) != expected_identity
                or temp_stat.st_size != len(raw)
                or not guard_allows(commit_guard, path.parent)
                or not guard_allows(commit_guard, path)
                or not guard_allows(commit_guard, tmp)):
            return False
        try:
            temp_bytes = _read_bound_bytes(
                tmp, _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES,
                "comparison payload temp")
        except ValueError:  # silent-ok: an unprovable temp is never installed
            return False
        if (temp_bytes is _ABSENT or temp_bytes != raw
                or hashlib.sha256(temp_bytes).hexdigest() != descriptor["sha256"]):
            return False

        try:
            _install_payload_temp_no_replace(tmp, path)
        except OSError:  # silent-ok: install race/failure may reuse only exact final bytes
            return _payload_chunk_state(
                path, raw, descriptor, commit_guard) == "exact"

        final_stat = _ordinary_file_stat(path)
        if (final_stat is None
                or _entry_identity(final_stat) != expected_identity
                or not guard_allows(commit_guard, path.parent)
                or not guard_allows(commit_guard, path)):
            return False
        try:
            current = _read_bound_bytes(
                path, _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES,
                "comparison payload chunk")
        except ValueError:  # silent-ok: post-install validation failure denies publication
            return False
        return (current is not _ABSENT and current == raw
                and len(current) == descriptor["size"]
                and hashlib.sha256(current).hexdigest() == descriptor["sha256"])
    finally:
        _unlink_bound_payload_temp(tmp, expected_identity, commit_guard)


def _publish_payload_chunk_with_fallback(
        parent, raw, descriptor, index, decoded_sha, commit_guard=None):
    """Publish the stable primary or one bounded content-addressed slot.

    Slot names deliberately omit generation binding: the chunk bytes are already
    content-addressed and the envelope separately binds their decoded outcome to
    the exact generation. This lets a completed/crash-residue slot be reused and
    bounds hostile-primary disk growth to eight alternatives per chunk.
    """
    parent = Path(parent)
    primary = parent / descriptor["relative_path"]
    if _publish_payload_chunk(primary, raw, descriptor, commit_guard):
        return dict(descriptor)
    if _payload_chunk_state(primary, raw, descriptor, commit_guard) != "conflict":
        return None

    for slot in range(_PAYLOAD_FALLBACK_SLOT_COUNT):
        relative = _payload_slot_basename(
            decoded_sha, index, descriptor["sha256"], slot)
        _require_windows_component(relative, "payload conflict slot")
        fallback = dict(descriptor)
        fallback["relative_path"] = relative
        path = parent / relative
        if _publish_payload_chunk(path, raw, fallback, commit_guard):
            return fallback
        # Only a proven conflicting entry advances to another bounded slot.
        # Guard denial or an absent-but-uninstallable path fails closed.
        if _payload_chunk_state(path, raw, fallback, commit_guard) != "conflict":
            return None
    return None


def _read_comparison_payload(manifest, parent):
    """Strictly reconstruct one canonical typed outcome from bounded zlib chunks."""
    manifest = _strict_payload_manifest(manifest)
    parent = Path(parent)
    decoded_all = bytearray()
    for descriptor in manifest["chunks"]:
        chunk_path = parent / descriptor["relative_path"]
        compressed = _read_bound_bytes(
            chunk_path, _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES,
            "comparison payload chunk")
        if compressed is _ABSENT:
            raise ValueError("comparison payload chunk is missing")
        if (len(compressed) != descriptor["size"]
                or hashlib.sha256(compressed).hexdigest() != descriptor["sha256"]):
            raise ValueError("comparison payload chunk digest/size is inconsistent")
        try:
            decoder = zlib.decompressobj()
            decoded = decoder.decompress(
                compressed, descriptor["decoded_size"] + 1)
        except zlib.error as e:
            raise ValueError("comparison payload chunk cannot be decompressed") from e
        if (len(decoded) != descriptor["decoded_size"]
                or not decoder.eof or decoder.unused_data
                or decoder.unconsumed_tail):
            raise ValueError(
                "comparison payload chunk is truncated, trailing, or exceeds decoded_size")
        decoded_all.extend(decoded)
        if len(decoded_all) > _MAX_COMPARISON_PAYLOAD_DECODED_BYTES:
            raise ValueError("comparison payload decoded bytes exceed their limit")
    raw = decoded_all
    if (len(raw) != manifest["decoded_size"]
            or hashlib.sha256(raw).hexdigest() != manifest["decoded_sha256"]):
        raise ValueError("comparison payload aggregate digest/size is inconsistent")
    value = _decode_strict_json(raw, "comparison payload")
    if not _matches_canonical_json(value, raw):
        raise ValueError("comparison payload JSON is not canonical")
    return _strict_comparison_outcome(value)


def _prepare_comparison_publication(result):
    typed_outcome = getattr(result, "comparison_outcome", None)
    typed_generation = getattr(result, "artifact_generation", None)
    if typed_generation is None:
        if getattr(result, "status", None) != "ok":
            return None                 # no committed generation exists to describe
        raise ValueError("successful comparison result is missing artifact generation metadata")
    if (not isinstance(typed_outcome, ComparisonOutcome)
            or not isinstance(typed_generation, ArtifactGeneration)):
        raise ValueError("comparison result is missing typed outcome/generation metadata")
    outcome_payload = typed_outcome.to_dict()
    generation_payload = typed_generation.to_dict()
    strict_outcome = _strict_comparison_outcome(outcome_payload)
    strict_generation, members = _strict_artifact_generation(
        generation_payload, strict_outcome.completion)
    skipped = getattr(result, "skipped_inputs", None)
    failed = getattr(result, "failed_inputs", None)
    if not _is_nonnegative_int(skipped) or not _is_nonnegative_int(failed):
        raise ValueError("comparison result input counters are invalid")
    if getattr(result, "completion", None) != strict_outcome.completion:
        raise ValueError("legacy and typed comparison completion claims disagree")
    if strict_outcome.completion == outcome.COMPLETE and (skipped or failed):
        raise ValueError("complete comparison result reports skipped/failed inputs")

    payload_manifest, payload_chunks = _preflight_comparison_payload(
        outcome_payload,
        completion=strict_outcome.completion,
        skipped_inputs=skipped,
        failed_inputs=failed,
        artifact_generation=generation_payload)
    prepared = []
    parent_key = None
    for member in members:
        actual_path = Path(member["path"])
        if actual_path.name != member["relative_path"]:
            raise ValueError("member path does not end in relative_path")
        this_parent = os.path.normcase(os.path.abspath(str(actual_path.parent)))
        if parent_key is None:
            parent_key = this_parent
        elif this_parent != parent_key:
            raise ValueError("comparison generation members must be sibling workbooks")
        actual = _bound_file_digest(actual_path)
        if actual is None:
            raise ValueError(f"comparison member is missing/unreadable: {actual_path.name}")
        if (actual["sha256"] != member["sha256"]
                or actual["size"] != member["size"]
                or actual["mtime_ns"] != member["mtime_ns"]):
            raise ValueError(f"comparison member changed before sidecar publication: {actual_path.name}")
        prepared.append((member, actual_path, actual))
    publication = {
        "outcome": strict_outcome,
        "generation": strict_generation,
        "outcome_payload": outcome_payload,
        "generation_payload": generation_payload,
        "skipped_inputs": skipped,
        "failed_inputs": failed,
        "members": tuple(prepared),
        "payload_manifest": payload_manifest,
        "payload_chunks": payload_chunks,
        "payload_parent": prepared[0][1].parent,
    }
    # All bounded JSON envelopes are encoded before the first sentinel mutates
    # the destination. A scale/resource rejection therefore leaves existing
    # metadata byte-exact and creates no misleading in-progress sentinel.
    try:
        for member, _workbook, facts in publication["members"]:
            sentinel_raw = _canonical_json_bytes(
                _comparison_sentinel_payload(publication, member, facts))
            final_raw = _canonical_json_bytes(
                _comparison_final_payload(publication, member, facts))
            if (len(sentinel_raw) > _MAX_COMPARISON_SIDECAR_BYTES
                    or len(final_raw) > _MAX_COMPARISON_SIDECAR_BYTES):
                raise ValueError("comparison envelope exceeds its metadata size limit")
    except (TypeError, ValueError, RecursionError) as e:
        raise ValueError("comparison envelopes could not be canonically encoded") from e
    return publication


def _comparison_sentinel_payload(prepared, member, facts):
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "comparison",
        "comparison_schema_version": COMPARISON_SCHEMA_VERSION,
        "publication_sentinel": True,
        "untrusted": True,
        "completion": outcome.PARTIAL,
        "skipped_inputs": 0,
        "failed_inputs": 0,
        "built_at_mtime": facts["mtime"],
        "generation_id": prepared["generation"].generation_id,
        "self_member": dict(member),
    }


def _comparison_final_payload(prepared, member, facts):
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "comparison",
        "comparison_schema_version": COMPARISON_SCHEMA_VERSION,
        "completion": prepared["outcome"].completion,
        "skipped_inputs": prepared["skipped_inputs"],
        "failed_inputs": prepared["failed_inputs"],
        "built_at_mtime": facts["mtime"],
        "self_member": dict(member),
        "comparison_payload": dict(prepared["payload_manifest"]),
        "artifact_generation": prepared["generation_payload"],
    }


def _comparison_final_payload_v2(prepared, member, facts):
    """Legacy inline schema-v2 fixture/migration representation; never newly written."""
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "comparison",
        "comparison_schema_version": 2,
        "completion": prepared["outcome"].completion,
        "skipped_inputs": prepared["skipped_inputs"],
        "failed_inputs": prepared["failed_inputs"],
        "built_at_mtime": facts["mtime"],
        "self_member": dict(member),
        "comparison_outcome": prepared["outcome_payload"],
        "artifact_generation": prepared["generation_payload"],
    }


def _sentinel_path(workbook):
    final = meta_path(workbook)
    return final.with_name(final.name + ".tmp")


def _safe_unlink_sidecar(path, commit_guard=None):
    """Remove one sidecar bound to the inode observed here (CMP-AUD-130).

    On Windows the removal happens through an identity-verified handle: the
    identity check and the deletion apply to one file object, so a same-path
    replacement racing in after ``before`` was captured is retained untouched
    and reported as ``False`` (uncertain — fail closed). Elsewhere the legacy
    pathname unlink remains, honestly best-effort between its own stat and
    unlink.
    """
    path = Path(path)
    before = _ordinary_file_stat(path)
    if before is None:
        try:
            path.lstat()
        except (FileNotFoundError, NotADirectoryError):  # silent-ok: already absent satisfies unlink
            return True
        except OSError:  # silent-ok: uncertain sidecar identity fails closed
            return False
        return False
    if not guard_allows(commit_guard, path):
        return False
    current = _ordinary_file_stat(path)
    if current is None or _entry_identity(current) != _entry_identity(before):
        return False
    disposition = _unlink_through_verified_handle(path, _entry_identity(before))
    if disposition == "absent":
        return True
    if disposition == "retained":
        return False
    if disposition == "deleted":
        try:
            path.lstat()
        except (FileNotFoundError, NotADirectoryError):  # silent-ok: verified absence is success
            return True
        except OSError:  # silent-ok: unverifiable post-unlink state fails closed
            return False
        return False                      # a foreign object reappeared: uncertain
    try:
        path.unlink()
    except FileNotFoundError:  # silent-ok: concurrent absence satisfies unlink
        return True
    except OSError:  # silent-ok: unlink failure remains observable as False
        return False
    try:
        path.lstat()
    except (FileNotFoundError, NotADirectoryError):  # silent-ok: verified absence is success
        return True
    except OSError:  # silent-ok: unverifiable post-unlink state fails closed
        return False
    return False


_PAYLOAD_COLLECT_GRACE_SECONDS = 15 * 60
_PAYLOAD_CHUNK_SHA_RE = re.compile(
    r"^\.cmpv3-[0-9a-f]{64}-[0-9]{6}-([0-9a-f]{64})")


def _live_payload_chunk_references(parent):
    """Union of chunk names referenced by every sibling metadata record.

    ``None`` aborts collection conservatively: a present publication sentinel
    means a protected or mid-flight state exists, and an unreadable or
    malformed sibling record means the live-reference set is unknowable — in
    either case everything is retained (CMP-AUD-127).
    """
    try:
        entries = list(os.scandir(parent))
    except OSError:  # silent-ok: unlistable parent makes references unknowable -> retain all
        return None
    if any(entry.name.endswith(_COMPARISON_META_SUFFIX
                                + _COMPARISON_SENTINEL_SUFFIX)
           for entry in entries):
        return None
    live = set()
    for entry in entries:
        if not entry.name.endswith(_COMPARISON_META_SUFFIX):
            continue
        try:
            record = _read_strict_json(Path(entry.path))
        except (ValueError, OSError):  # silent-ok: unreadable sibling record -> retain all
            return None
        if record is _ABSENT or not isinstance(record, Mapping):
            continue
        manifest = record.get("comparison_payload")
        if manifest is None:
            continue          # inline v2 / untrusted markers reference nothing
        try:
            manifest = _strict_payload_manifest(manifest)
        except (TypeError, ValueError):  # silent-ok: malformed manifest -> retain all
            return None
        live.update(chunk["relative_path"] for chunk in manifest["chunks"])
    return live


def _collect_superseded_payload_chunks(parent, lease, commit_guard=None):
    """Reclaim provably superseded schema-v3 payload chunks (CMP-AUD-127).

    Runs only immediately after a fully validated publication, under the same
    exclusive parent lease. Conservative by construction: any publication
    sentinel, unreadable sibling record, guard denial, young mtime (the grace
    window), non-ordinary file, content that does not match the digest
    embedded in the chunk's OWN name, or handle-verification failure retains
    the candidate — a retained orphan is logged, never an error, and a
    collection problem can never turn a successful publication into failure.
    Only exact reserved-namespace basenames are candidates (near-match
    ``.zlib`` files are invisible here), and every removal goes through the
    identity-verified handle primitive, never a broad pathname unlink.
    """
    parent = Path(parent)
    try:
        if (not _publication_lease_current(lease, commit_guard)
                or not guard_allows(commit_guard, parent)):
            return
        live = _live_payload_chunk_references(parent)
        if live is None:
            return
        now = time.time()
        collected = retained = 0
        for entry in os.scandir(parent):
            name = entry.name
            if not _PAYLOAD_BASENAME_RE.match(name) or name in live:
                continue
            path = parent / name
            candidate_stat = _ordinary_file_stat(path)
            if (not guard_allows(commit_guard, path)
                    or candidate_stat is None
                    or now - candidate_stat.st_mtime
                        < _PAYLOAD_COLLECT_GRACE_SECONDS):
                retained += 1
                continue
            digest = _PAYLOAD_CHUNK_SHA_RE.match(name)
            try:
                raw = _read_bound_bytes(
                    path, _MAX_COMPARISON_PAYLOAD_CHUNK_BYTES,
                    "superseded comparison payload chunk")
            except ValueError:  # silent-ok: an over-limit candidate is retained evidence
                retained += 1
                continue
            if (raw is _ABSENT or digest is None
                    or hashlib.sha256(raw).hexdigest() != digest.group(1)):
                retained += 1     # mismatched chunk: retained as evidence
                continue
            if (not _publication_lease_current(lease, commit_guard)
                    or _unlink_through_verified_handle(
                        path, _entry_identity(candidate_stat)) != "deleted"):
                retained += 1
                continue
            collected += 1
        if collected or retained:
            log.info("comparison payload collection under %s: %d superseded "
                     "chunk(s) reclaimed, %d candidate(s) retained",
                     parent, collected, retained)
    except Exception as e:  # silent-ok: collection may never fail a publication
        log.warning("comparison payload collection skipped: %s: %s",
                    type(e).__name__, e)


def _protect_comparison_members(prepared, commit_guard=None):
    """Best-effort conservative protection after sentinel establishment fails."""
    fully_protected = True
    for member, workbook, _facts in prepared["members"]:
        sentinel = _read_comparison_candidate(
            _sentinel_path(workbook), workbook, "sentinel")
        if isinstance(sentinel, ComparisonSidecarOutcome):
            continue
        final = meta_path(workbook)
        if _mark_untrusted(final, workbook, commit_guard):
            continue
        if _quarantine(workbook, commit_guard):
            continue
        fully_protected = False
        log.critical("comparison generation %s: could not mark or quarantine unprotected "
                     "member %s", prepared["generation"].generation_id,
                     member["relative_path"])
    return fully_protected


def _validate_published_finals(prepared):
    first_member, _first_workbook, first_facts = prepared["members"][0]
    expected = _shared_comparison_payload(
        _comparison_final_payload(prepared, first_member, first_facts))
    expected_members = prepared["generation_payload"]["members"]
    for index, (_member, workbook, _facts) in enumerate(prepared["members"]):
        candidate = _read_comparison_candidate(meta_path(workbook), workbook, "sidecar")
        if not isinstance(candidate, _ParsedComparison):
            return False
        member = prepared["members"][index][0]
        if (candidate.comparison_schema_version != COMPARISON_SCHEMA_VERSION
                or _shared_comparison_payload(candidate.payload) != expected
                or candidate.payload.get("artifact_generation", {}).get("members") != expected_members
                or candidate.comparison_outcome is not None
                or candidate.artifact_generation != prepared["generation"]
                or dict(candidate.self_member) != member):
            return False
    return True


def _publication_stopped(stage, detail=""):
    """Name the one fail-closed publication gate that fired, then report failure.

    Every gate below is deliberately conservative: it refuses rather than
    publishing a generation it cannot prove. That is correct, but a bare
    ``return False`` leaves the user with "could not be safely published" and
    leaves the log with nothing — the failure becomes undiagnosable from a log
    upload, which the log-every-decision rule exists to prevent. Naming the gate
    changes no control flow; it only makes the refusal answerable.
    """
    log.error("comparison publication stopped at %s%s", stage,
              f": {detail}" if detail else "")
    return False


def _prepared_publication_current(prepared, lease, commit_guard=None):
    """Revalidate the lease and every committed workbook after lock waiting."""
    if (lease.parent != Path(prepared["payload_parent"])
            or not _publication_lease_current(lease, commit_guard)):
        return _publication_stopped(
            "revalidation", "the publication lease is no longer current")
    for member, workbook, _facts in prepared["members"]:
        actual = _bound_file_digest(workbook)
        if actual is None:
            return _publication_stopped(
                "revalidation",
                f"committed member could not be re-read ({member['relative_path']})")
        if (actual["sha256"] != member["sha256"]
                or actual["size"] != member["size"]
                or actual["mtime_ns"] != member["mtime_ns"]):
            return _publication_stopped(
                "revalidation",
                f"committed member changed after commit ({member['relative_path']}; "
                f"sha256 {member['sha256'][:12]}->{actual['sha256'][:12]}, "
                f"size {member['size']}->{actual['size']}, "
                f"mtime_ns {member['mtime_ns']}->{actual['mtime_ns']})")
    if not _publication_lease_current(lease, commit_guard):
        return _publication_stopped(
            "revalidation", "the publication lease expired during revalidation")
    return True


def write_comparison_outcomes(result, commit_guard=None):
    """Atomically publish one typed outcome beside every committed generation member.

    A fixed conservative ``.outcome.json.tmp`` sentinel is established for every
    member before any final sidecar is replaced. It remains until all final records,
    peer tables, and workbook digests validate. Any failed/partial publication leaves
    the generation fail-closed; workbook bytes are read for hashing and never resaved.
    Returns ``True`` only when every final is trusted and every sentinel is gone.
    A terminal result with no generation is a no-op. A coarse ``error`` that still
    carries a committed values generation is published from its typed truth.
    """
    try:
        prepared = _prepare_comparison_publication(result)
    except (TypeError, ValueError, OSError) as e:
        log.error("comparison outcome publication rejected: %s", e)
        return False
    if prepared is None:
        return True

    try:
        with _comparison_publication_lease(
                prepared["payload_parent"], commit_guard) as lease:
            if not _prepared_publication_current(prepared, lease, commit_guard):
                return False
            return _write_comparison_outcomes_prepared(
                prepared, commit_guard, lease)
    except (OSError, TimeoutError, ValueError) as e:
        log.error("comparison publication lease rejected: %s", e)
        return False


def _write_comparison_outcomes_prepared(prepared, commit_guard, lease):
    """Mutate one prepared generation while its parent lease is held."""

    # Phase 1: establish conservative fixed sentinels for the complete member set.
    for _member, workbook, facts in prepared["members"]:
        if (not _publication_lease_current(lease, commit_guard)
                or not guard_allows(commit_guard, workbook)
                or not _atomic_write_json(
                    _sentinel_path(workbook),
                    _comparison_sentinel_payload(prepared, _member, facts),
                    commit_guard)):
            _protect_comparison_members(prepared, commit_guard)
            return _publication_stopped(
                "phase 1 (sentinel write)",
                f"could not establish the sentinel beside {_member['relative_path']}")
    for member, workbook, _facts in prepared["members"]:
        try:
            sentinel_raw = _read_strict_json(_sentinel_path(workbook))
        except ValueError:  # silent-ok: unreadable sentinel cannot certify this attempt
            sentinel_raw = None
        if (not _publication_lease_current(lease, commit_guard)
                or sentinel_raw
                    != _comparison_sentinel_payload(prepared, member, _facts)):
            _protect_comparison_members(prepared, commit_guard)
            return _publication_stopped(
                "phase 1 (sentinel readback)",
                f"the sentinel beside {member['relative_path']} did not read back "
                f"exactly (present={sentinel_raw is not None})")

    # Phase 2: publish the one shared, content-addressed canonical outcome payload.
    # The stable primary preserves normal cross-generation deduplication. A
    # conflicting primary selects one of eight deterministic exact-byte slots;
    # neither the primary nor a slot is ever replaced.
    # Every workbook remains sentinel-protected throughout.
    descriptors = prepared["payload_manifest"]["chunks"]
    payloads = prepared["payload_chunks"]
    if len(descriptors) != len(payloads):
        return _publication_stopped(
            "phase 2 (payload manifest)",
            f"{len(descriptors)} chunk descriptors vs {len(payloads)} chunks")
    published_descriptors = []
    for index, (descriptor, (relative, raw)) in enumerate(
            zip(descriptors, payloads)):
        if (not _publication_lease_current(lease, commit_guard)
                or relative != descriptor["relative_path"]):
            # all sentinels intentionally retained
            return _publication_stopped(
                "phase 2 (chunk order)",
                f"chunk {index} path/lease mismatch ({relative!r})")
        published = _publish_payload_chunk_with_fallback(
            prepared["payload_parent"], raw, descriptor, index,
            prepared["payload_manifest"]["decoded_sha256"],
            commit_guard)
        if published is None:
            # all sentinels intentionally retained
            return _publication_stopped(
                "phase 2 (chunk publish)",
                f"chunk {index} could not be published ({relative!r})")
        published_descriptors.append(published)
    published_manifest = dict(prepared["payload_manifest"])
    published_manifest["chunks"] = published_descriptors
    if not _publication_lease_current(lease, commit_guard):
        return _publication_stopped(
            "phase 2 (post-chunk lease)", "the publication lease expired")
    try:
        prepared["payload_manifest"] = _strict_payload_manifest(published_manifest)
    except (TypeError, ValueError) as e:  # no malformed path may enter a final envelope
        return _publication_stopped(
            "phase 2 (manifest validation)", f"{type(e).__name__}: {e}")
    try:
        persisted_outcome = _read_comparison_payload(
            prepared["payload_manifest"], prepared["payload_parent"])
    except (TypeError, ValueError, OSError) as e:  # persisted payload must validate exactly
        return _publication_stopped(
            "phase 2 (payload readback)", f"{type(e).__name__}: {e}")
    if persisted_outcome != prepared["outcome"]:
        return _publication_stopped(
            "phase 2 (payload equality)",
            "the persisted outcome did not equal the prepared outcome")
    del persisted_outcome

    # Phase 3: sequential final publication is safe because every fixed sentinel
    # dominates read_completion/read_comparison_outcome until the entire set validates.
    for member, workbook, facts in prepared["members"]:
        if (not _publication_lease_current(lease, commit_guard)
                or not guard_allows(commit_guard, workbook)
                or not _atomic_write_json(
                    meta_path(workbook),
                    _comparison_final_payload(prepared, member, facts),
                    commit_guard)):
            # all sentinels intentionally retained
            return _publication_stopped(
                "phase 3 (final sidecar write)",
                f"could not write the final record beside {member['relative_path']}")
    if not _publication_lease_current(lease, commit_guard):
        return _publication_stopped(
            "phase 3 (final lease)", "the publication lease expired")
    if not _validate_published_finals(prepared):
        # all sentinels intentionally retained
        return _publication_stopped(
            "phase 3 (final validation)",
            "the published final records did not validate as a peer set")

    # Phase 4: re-hash immediately before releasing the conservative sentinels: publishing
    # metadata must never mutate or accidentally replace a comparison workbook.
    for member, workbook, _before in prepared["members"]:
        if not _publication_lease_current(lease, commit_guard):
            return _publication_stopped(
                "phase 4 (re-hash lease)", "the publication lease expired")
        now = _bound_file_digest(workbook)
        if now is None:
            return _publication_stopped(
                "phase 4 (re-hash)",
                f"committed member could not be re-read ({member['relative_path']})")
        if (now["sha256"] != member["sha256"]
                or now["size"] != member["size"]
                or now["mtime_ns"] != member["mtime_ns"]):
            return _publication_stopped(
                "phase 4 (re-hash)",
                f"the workbook changed while metadata published "
                f"({member['relative_path']}; "
                f"sha256 {member['sha256'][:12]}->{now['sha256'][:12]}, "
                f"size {member['size']}->{now['size']}, "
                f"mtime_ns {member['mtime_ns']}->{now['mtime_ns']})")

    # Removing one sentinel may fail after earlier removals. That remains safe:
    # strict peer validation observes any surviving sentinel and marks every member
    # untrusted/partial. Success is claimed only after all are proven absent.
    all_removed = True
    for _member, workbook, _facts in prepared["members"]:
        if (not _publication_lease_current(lease, commit_guard)
                or not _safe_unlink_sidecar(
                    _sentinel_path(workbook), commit_guard)):
            all_removed = False
    if not all_removed:
        return _publication_stopped(
            "phase 5 (sentinel removal)",
            "a conservative sentinel could not be removed; the members stay untrusted")

    exact_records = True
    trusted_winner = None
    failed_member = None
    for member, workbook, _facts in prepared["members"]:
        if not _publication_lease_current(lease, commit_guard):
            return _publication_stopped(
                "phase 5 (readback lease)", "the publication lease expired")
        record = read_comparison_outcome(workbook)
        own = (
            record is not None and record.trusted and record.current
            and record.source == "sidecar"
            and record.comparison_outcome == prepared["outcome"]
            and record.artifact_generation == prepared["generation"]
            and record.self_member is not None
            and dict(record.self_member) == member
        )
        if not own:
            exact_records = False
            failed_member = (
                f"{member['relative_path']} (record={'absent' if record is None else 'present'}"
                + ("" if record is None else
                   f", trusted={record.trusted}, current={record.current}, "
                   f"source={record.source!r}")
                + ")")
            if (record is not None and record.trusted and record.current
                    and record.source == "sidecar"
                    and record.artifact_generation is not None):
                trusted_winner = record.artifact_generation.generation_id
            break
    if exact_records:
        # The publication is fully validated; reclaim provably superseded
        # payload chunks under this same lease (CMP-AUD-127). Collection is
        # conservative and can never turn this success into failure.
        _collect_superseded_payload_chunks(
            prepared["payload_parent"], lease, commit_guard)
        return True
    if trusted_winner is not None:
        # A different fully trusted generation won. Never poison, overwrite, or
        # quarantine it merely to make this superseded attempt look successful.
        log.error("comparison generation %s was superseded by trusted generation %s",
                  prepared["generation"].generation_id, trusted_winner)
        return False

    # A non-trusted race/tamper appeared after cleanup. Re-establish this
    # attempt's conservative sentinel only while its exact lease remains current.
    if _publication_lease_current(lease, commit_guard):
        for m2, w2, f2 in prepared["members"]:
            _atomic_write_json(_sentinel_path(w2),
                               _comparison_sentinel_payload(prepared, m2, f2),
                               commit_guard)
        _protect_comparison_members(prepared, commit_guard)
    return _publication_stopped(
        "phase 5 (final readback)",
        "a published record did not read back as this generation's own trusted "
        f"sidecar: {failed_member or 'unknown member'}")


def _comparison_untrusted(diagnostic, source="sidecar", self_member=None):
    member = (MappingProxyType(dict(self_member))
              if isinstance(self_member, Mapping) else None)
    return ComparisonSidecarOutcome(
        completion=outcome.PARTIAL,
        skipped_inputs=None,
        failed_inputs=None,
        trusted=False,
        current=True,
        diagnostic=diagnostic,
        source=source,
        comparison_outcome=None,
        artifact_generation=None,
        self_member=member,
    )


@dataclass(frozen=True)
class _ParsedComparison:
    payload: Mapping[str, Any]
    members: tuple
    comparison_schema_version: int
    completion: str
    skipped_inputs: int
    failed_inputs: int
    source: str
    comparison_outcome: Optional[ComparisonOutcome]
    artifact_generation: ArtifactGeneration
    self_member: Mapping[str, Any]
    payload_manifest: Optional[Mapping[str, Any]]


def _trusted_comparison(parsed, typed_outcome):
    """Materialize a public trusted record after all generation checks pass."""
    return ComparisonSidecarOutcome(
        completion=parsed.completion,
        skipped_inputs=parsed.skipped_inputs,
        failed_inputs=parsed.failed_inputs,
        trusted=True,
        current=True,
        diagnostic=None,
        source=parsed.source,
        comparison_outcome=typed_outcome,
        artifact_generation=parsed.artifact_generation,
        self_member=MappingProxyType(dict(parsed.self_member)),
    )


def _comparison_mtime_state(meta, workbook):
    built_at = meta.get("built_at_mtime") if isinstance(meta, Mapping) else None
    if isinstance(built_at, bool) or not isinstance(built_at, (int, float)):
        return "malformed"
    try:
        built_at = float(built_at)
    except (OverflowError, ValueError):  # silent-ok: malformed mtime is an explicit untrusted state
        return "malformed"
    current = _safe_mtime(workbook)
    if not math.isfinite(built_at):
        return "malformed"
    if current is None or not math.isfinite(float(current)):
        return "stale"
    return "stale" if abs(built_at - current) > _MTIME_TOL_S else "current"


def _parse_comparison_payload(meta, workbook, source):
    """Validate one local final/sentinel without recursively reading peers."""
    if not isinstance(meta, Mapping):
        return _comparison_untrusted("comparison sidecar must be a JSON object", source)
    comparison_schema = meta.get("comparison_schema_version")
    if source == "sentinel":
        expected_keys = _COMPARISON_SENTINEL_KEYS
    elif comparison_schema == 2:
        expected_keys = _COMPARISON_FINAL_KEYS_V2
    elif comparison_schema == 3:
        expected_keys = _COMPARISON_FINAL_KEYS_V3
    else:
        expected_keys = frozenset()
    if set(meta) != expected_keys:
        return _comparison_untrusted(
            "comparison sidecar has missing or unknown outer fields", source)
    schema = meta.get("schema_version")
    if (not isinstance(schema, int) or isinstance(schema, bool)
            or schema != SCHEMA_VERSION
            or meta.get("record_type") != "comparison"
            or not isinstance(comparison_schema, int)
            or isinstance(comparison_schema, bool)
            or comparison_schema not in _SUPPORTED_COMPARISON_SCHEMA_VERSIONS):
        return _comparison_untrusted("comparison sidecar schema/type is invalid", source)
    mtime_state = _comparison_mtime_state(meta, workbook)
    if mtime_state == "stale":
        return _STALE
    if mtime_state != "current":
        return _comparison_untrusted("comparison sidecar built_at_mtime is invalid", source)

    if source == "sentinel":
        if (meta.get("publication_sentinel") is not True
                or meta.get("untrusted") is not True
                or meta.get("completion") != outcome.PARTIAL
                or not _is_nonnegative_int(meta.get("skipped_inputs"))
                or meta.get("skipped_inputs") != 0
                or not _is_nonnegative_int(meta.get("failed_inputs"))
                or meta.get("failed_inputs") != 0
                or not isinstance(meta.get("generation_id"), str)
                or not meta.get("generation_id")):
            return _comparison_untrusted(
                "comparison publication sentinel is malformed", source)
        try:
            member = _strict_member(meta.get("self_member"))
        except (TypeError, ValueError):  # silent-ok: malformed sentinel member remains untrusted
            member = None
        return _comparison_untrusted(
            "comparison generation publication is incomplete (sentinel present)",
            source, self_member=member)

    if meta.get("publication_sentinel") is not None or meta.get("untrusted") is not None:
        return _comparison_untrusted("published comparison sidecar has sentinel fields", source)
    completion = meta.get("completion")
    skipped = meta.get("skipped_inputs")
    failed = meta.get("failed_inputs")
    if (completion not in (outcome.COMPLETE, outcome.PARTIAL)
            or not _is_nonnegative_int(skipped)
            or not _is_nonnegative_int(failed)):
        return _comparison_untrusted("comparison compatibility outcome is malformed", source)
    if completion == outcome.COMPLETE and (skipped or failed):
        return _comparison_untrusted(
            "complete comparison sidecar reports skipped or failed inputs", source)
    try:
        manifest = None
        if comparison_schema == 2:
            typed_outcome = _strict_comparison_outcome(
                meta.get("comparison_outcome"))
            typed_generation, members = _strict_artifact_generation(
                meta.get("artifact_generation"), typed_outcome.completion)
        else:
            # The small envelope carries generation/workbook identity while the
            # potentially large canonical outcome lives once in strict sibling
            # chunks. Validate the generation first so manifest path authority
            # never comes from an untyped/contradictory envelope.
            typed_generation, members = _strict_artifact_generation(
                meta.get("artifact_generation"), completion)
            manifest = _strict_payload_manifest(meta.get("comparison_payload"))
            expected_binding = _comparison_payload_binding_sha256(
                manifest["decoded_sha256"], completion, skipped, failed,
                typed_generation.to_dict())
            if manifest["binding_sha256"] != expected_binding:
                raise ValueError(
                    "comparison payload is not bound to this generation envelope")
            # Do not touch compressed siblings here.  ``read_comparison_outcome``
            # first validates every peer envelope, manifest binding, and workbook
            # identity, then decodes this one shared manifest exactly once.
            typed_outcome = None
        self_member = _strict_member(meta.get("self_member"))
    except (TypeError, ValueError, KeyError) as e:
        return _comparison_untrusted(f"comparison sidecar typed payload is invalid: {e}", source)
    if typed_outcome is not None and typed_outcome.completion != completion:
        return _comparison_untrusted("typed and compatibility completion disagree", source)
    matches = [member for member in members if member == self_member]
    if len(matches) != 1 or self_member["relative_path"] != Path(workbook).name:
        return _comparison_untrusted("self_member does not identify this workbook", source)
    actual = _bound_file_digest(workbook)
    if actual is None:
        return _comparison_untrusted("comparison workbook identity/content is unreadable", source)
    if (actual["sha256"] != self_member["sha256"]
            or actual["size"] != self_member["size"]
            or actual["mtime_ns"] != self_member["mtime_ns"]):
        return _comparison_untrusted("comparison workbook does not match self_member", source)
    return _ParsedComparison(
        payload=dict(meta), members=members,
        comparison_schema_version=comparison_schema,
        completion=completion, skipped_inputs=skipped,
        failed_inputs=failed, source=source,
        comparison_outcome=typed_outcome,
        artifact_generation=typed_generation,
        self_member=MappingProxyType(dict(self_member)),
        payload_manifest=(MappingProxyType(dict(manifest))
                          if manifest is not None else None))


def _read_comparison_candidate(sidecar, workbook, source):
    try:
        meta = _read_strict_json(sidecar)
    except ValueError as e:
        return _comparison_untrusted(f"comparison {source} is unreadable: {e}", source)
    if meta is _ABSENT:
        return _ABSENT
    # A consolidation marker may be the emergency fail-safe after comparison
    # publication could not establish its own sentinel. Never trust it as a
    # comparison record, even if its top-level completion says complete.
    if not isinstance(meta, Mapping) or meta.get("record_type") != "comparison":
        mtime_state = _comparison_mtime_state(meta, workbook)
        if mtime_state == "stale":
            return _STALE
        return _comparison_untrusted(
            "sidecar is not a validated comparison-generation record", source)
    return _parse_comparison_payload(meta, workbook, source)


def _shared_comparison_payload(payload):
    return {key: value for key, value in payload.items()
            if key not in ("self_member", "built_at_mtime")}


def _validate_comparison_peers(workbook, parsed):
    """Validate the full generation, then decode one shared v3 payload once."""
    workbook = Path(workbook)
    parent = workbook.parent
    common = _shared_comparison_payload(parsed.payload)
    expected_generation = parsed.artifact_generation.generation_id
    for member in parsed.members:
        try:
            relative = _safe_relative_member(member["relative_path"])
        except (TypeError, ValueError) as e:
            return _comparison_untrusted(f"unsafe generation member path: {e}")
        peer = parent / relative             # serialized absolute paths are NEVER lookup authority
        actual = _bound_file_digest(peer)
        if (actual is None or actual["sha256"] != member["sha256"]
                or actual["size"] != member["size"]
                or actual["mtime_ns"] != member["mtime_ns"]):
            return _comparison_untrusted(
                f"generation member {relative!r} is missing or content-mismatched")

        peer_meta = meta_path(peer)
        peer_sentinel = _read_comparison_candidate(
            peer_meta.with_name(peer_meta.name + ".tmp"), peer, "sentinel")
        if peer_sentinel is not _ABSENT and peer_sentinel is not _STALE:
            return _comparison_untrusted(
                f"generation member {relative!r} still has an incomplete publication sentinel")
        peer_final = _read_comparison_candidate(peer_meta, peer, "sidecar")
        if not isinstance(peer_final, _ParsedComparison):
            return _comparison_untrusted(
                f"generation member {relative!r} has no trusted current peer sidecar")
        if (_shared_comparison_payload(peer_final.payload) != common
                or peer_final.comparison_schema_version
                    != parsed.comparison_schema_version
                or dict(peer_final.self_member) != member
                or peer_final.artifact_generation.generation_id != expected_generation):
            return _comparison_untrusted(
                f"generation member {relative!r} sidecar disagrees with its peers")

    typed_outcome = parsed.comparison_outcome
    if parsed.comparison_schema_version == 3:
        try:
            typed_outcome = _read_comparison_payload(
                parsed.payload_manifest, parent)
        except (TypeError, ValueError, OSError) as e:
            return _comparison_untrusted(
                f"comparison sidecar typed payload is invalid: {e}")
    if typed_outcome is None or typed_outcome.completion != parsed.completion:
        return _comparison_untrusted(
            "typed and compatibility completion disagree")
    return _trusted_comparison(parsed, typed_outcome)


def read_comparison_outcome(path) -> Optional[ComparisonSidecarOutcome]:
    """Strictly read one complete comparison generation member.

    Returns ``None`` only when comparison metadata is absent or demonstrably stale.
    Any current malformed record, current publication sentinel, missing peer,
    digest mismatch, unsafe relative path, or cross-member disagreement returns an
    untrusted ``partial`` record with typed fields set to ``None``.
    """
    path = Path(path)
    try:
        validate_comparison_metadata_paths(path)
    except ValueError as e:
        return _comparison_untrusted(
            f"comparison member/sidecar path is invalid: {e}")
    final_path = meta_path(path)
    # A current/malformed sentinel dominates before a v3 final is decoded. This
    # both preserves fail-closed publication semantics and prevents an incomplete
    # generation from making readers decompress a potentially large payload.
    sentinel = _read_comparison_candidate(
        final_path.with_name(final_path.name + ".tmp"), path, "sentinel")
    if isinstance(sentinel, ComparisonSidecarOutcome):
        return sentinel
    final = _read_comparison_candidate(final_path, path, "sidecar")
    if isinstance(final, ComparisonSidecarOutcome):
        return final
    if isinstance(final, _ParsedComparison):
        return _validate_comparison_peers(path, final)
    return None


def require_published_comparison(path, result) -> ComparisonSidecarOutcome:
    """Return one successful result's exact trusted persisted comparison record.

    Structural terminal state wins over every legacy field. A caller may consume
    verdict/counts/completion only when the returned typed objects, succeeded
    attempt, committed generation, and strict sidecar all agree.
    """
    if getattr(result, "status", None) != "ok":
        raise ValueError("the comparison attempt did not finish successfully")
    typed = getattr(result, "comparison_outcome", None)
    generation = getattr(result, "artifact_generation", None)
    attempt = getattr(result, "attempt_state", None)
    if (not isinstance(typed, ComparisonOutcome)
            or not isinstance(generation, ArtifactGeneration)
            or not isinstance(attempt, AttemptState)):
        raise ValueError("the comparison result is missing typed publication state")
    if (not typed.is_comparable
            or generation.publication_state != "committed"
            or generation.completion != typed.completion
            or attempt.state != "succeeded"
            or attempt.generation_id != generation.generation_id):
        raise ValueError("the comparison result has contradictory publication state")

    record = read_comparison_outcome(path)
    if record is None:
        raise ValueError("the comparison generation sidecar is missing")
    if (not record.trusted or not record.current
            or record.comparison_outcome is None
            or record.artifact_generation is None):
        raise ValueError(record.diagnostic
                         or "the comparison generation sidecar is untrusted")
    if (record.comparison_outcome != typed
            or record.artifact_generation != generation):
        raise ValueError(
            "the returned comparison disagrees with its persisted generation")
    return record


def _comparison_as_consolidation(path):
    record = read_comparison_outcome(path)
    if record is None:
        return None
    return ConsolidationOutcome(
        completion=record.completion,
        skipped_inputs=(record.skipped_inputs if record.trusted else None),
        failed_inputs=(record.failed_inputs if record.trusted else None),
        trusted=record.trusted,
        current=record.current,
        diagnostic=record.diagnostic,
        source=record.source,
    )


def read_outcome(consolidated) -> Optional[ConsolidationOutcome]:
    """Return one validated, current consolidation outcome, or ``None``.

    ``None`` means there is no record for this workbook generation (absent legacy
    metadata or a demonstrably stale record). Present malformed or unreadable
    metadata returns a current, untrusted ``partial`` record with a diagnostic.
    A partial ``.tmp`` sentinel dominates a non-partial final; otherwise a present
    final is authoritative, preserving the completion-only reader's precedence.

    Coupled fields come from the same JSON read and workbook-mtime check. Callers
    must not reconstruct this outcome using separate :func:`read_extra` calls.
    Never raises.
    """
    p = meta_path(consolidated)
    final = _read_sidecar(p, consolidated, source="sidecar")
    if final is _COMPARISON:
        return _comparison_as_consolidation(consolidated)
    if (isinstance(final, ConsolidationOutcome)
            and final.completion == outcome.PARTIAL):
        return final

    tmp = _read_sidecar(p.with_name(p.name + ".tmp"), consolidated, source="sentinel")
    if tmp is _COMPARISON:
        return _comparison_as_consolidation(consolidated)
    if (isinstance(tmp, ConsolidationOutcome)
            and tmp.completion == outcome.PARTIAL):
        return tmp
    if final is not _ABSENT:
        return None if final is _STALE else final
    if tmp is _ABSENT or tmp is _STALE:
        return None
    return tmp


def read_completion(consolidated):
    """The persisted producer completion of a consolidated workbook for REUSE. Never
    raises. Returns:
      * ``None``  — no sidecar AND no sentinel (a legacy workbook), OR the workbook was
        rebuilt since the sidecar was written / a demonstrably stale sentinel (mtime
        mismatch); the caller defaults to ``complete``;
      * a completion string — the recorded, validated, current outcome;
      * ``partial`` (conservative) — a sidecar/sentinel EXISTS but is unusable (unreadable,
        unparseable, wrong schema / vocabulary / type): a current-version artifact whose
        outcome can't be trusted must never read as a green ``complete``.

    Final and ``.tmp`` are reconciled CONSERVATIVELY: a retained ``.tmp`` sentinel that
    reads ``partial`` is the most-recent, not-yet-promoted record of a FAILED partial
    publication, so it **dominates** the final sidecar — even a final that says ``complete``
    but is only stale-yet-within-tolerance (a rapid overwrite / coarse-resolution mtime).
    Otherwise the final wins (its validated value / None), then the ``.tmp``'s value. Both
    are validated the same way (so a stale sentinel is ignored, a corrupt one stays
    conservative)."""
    record = read_outcome(consolidated)
    return None if record is None else record.completion

"""Credential redaction + final-member scanning for diagnostic artifacts.

The validation manifest and evidence ZIP are intentionally shareable with a
maintainer.  They may contain paths and diagnostics, but never authorization
values, cookies, tokens, passwords, or JWTs.  Keep the policy in this small leaf
module so producers and the final publication gate use the same definitions.

Stdlib only; console-free.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path


_REDACTED = "[redacted]"

# Whole credential-bearing headers. Consume the complete value and any folded
# continuation lines: redacting only "Bearer" leaves the actual secret behind.
_HEADER_RE = re.compile(
    r"(?im)\b(authorization|proxy-authorization|cookie|set-cookie)"
    r"[ \t]*[:=][ \t]*[^\r\n]*(?:\r?\n[ \t]+[^\r\n]*)*"
)

# Standalone HTTP authentication schemes found outside a labelled header.
_SCHEME_RE = re.compile(
    r"(?i)\b(bearer|basic|negotiate|ntlm)\s+"
    r"(?!\[redacted\])(\S+)"
)

# Common key/value credentials, including URL query parameters.  Stop before a
# query/cookie delimiter so harmless trailing fields remain useful diagnostics.
_KEY_RE = re.compile(
    r"(?i)\b(access_token|refresh_token|id_token|session_token|sessionid|"
    r"client_secret|api_key|token|sid|password|pwd|secret)"
    r"\s*[:=]\s*([^\s&;,\r\n]+)"
)

# JWT shape (three base64url components).  A token need not start with ``ey``.
_JWT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"(?![A-Za-z0-9_-])"
)

_HASH_TOKEN_RE = re.compile(
    r"(?i)#(?:access_token|refresh_token|id_token|session_token|token|"
    r"auth|code|oauth_state|state)\s*[=:]\s*(?!\[redacted\])[^\s&#]+"
)


def redact_text(value):
    """Return ``value`` with complete credential values replaced.

    ``None`` and empty strings retain their original shape for the validation
    call sites.  The operation is idempotent: already-redacted values stay safe.
    """
    if not value:
        return value
    text = str(value)
    text = _HEADER_RE.sub(lambda m: f"{m.group(1)}={_REDACTED}", text)
    text = _SCHEME_RE.sub(lambda m: f"{m.group(1)} {_REDACTED}", text)
    text = _JWT_RE.sub(_REDACTED, text)
    text = _KEY_RE.sub(lambda m: f"{m.group(1)}={_REDACTED}", text)
    return _HASH_TOKEN_RE.sub(f"#{_REDACTED}", text)


def sensitive_kind(text, *, allow_hash=True):
    """The first credential class still present in ``text``, else ``None``."""
    if not text:
        return None
    for match in _HEADER_RE.finditer(text):
        value = re.split(r"[:=]", match.group(0), maxsplit=1)[-1].strip().lower()
        if value != _REDACTED:
            return "authorization header"
    if _SCHEME_RE.search(text):
        return "authentication scheme"
    if _JWT_RE.search(text):
        return "JWT"
    for match in _KEY_RE.finditer(text):
        if match.group(2).strip().lower() != _REDACTED:
            return "credential key/value"
    if allow_hash and _HASH_TOKEN_RE.search(text):
        return "URL fragment token"
    return None


def _scan_text_encodings(data, *, allow_hash):
    """Scan lossless single-byte text plus both UTF-16 byte orders/alignments."""
    hit = sensitive_kind(data.decode("latin-1", errors="ignore"),
                         allow_hash=allow_hash)
    if hit:
        return hit
    # Windows diagnostics and embedded document strings can be UTF-16 without a
    # BOM. Try both alignments because a credential need not start at byte zero.
    for encoding in ("utf-16-le", "utf-16-be"):
        for offset in (0, 1):
            hit = sensitive_kind(data[offset:].decode(encoding, errors="ignore"),
                                 allow_hash=allow_hash)
            if hit:
                return hit
    return None


def _scan_stream(stream, chunk_size=64 * 1024, overlap=4096, *, allow_hash=True):
    """Scan an arbitrary binary stream for single-byte and UTF-16 credentials.

    Latin-1 is a lossless byte-to-character mapping for ASCII patterns; both
    UTF-16 byte orders/alignments cover Windows-origin diagnostics. A bounded
    overlap catches a value split across chunks without loading a statewide
    workbook/PDF into memory.
    """
    tail = b""
    while True:
        block = stream.read(chunk_size)
        if not block:
            return None
        data = tail + block
        hit = _scan_text_encodings(data, allow_hash=allow_hash)
        if hit:
            return hit
        tail = data[-overlap:]


_NESTED_ZIP_SUFFIXES = frozenset((".xlsx", ".xlsm", ".xltx", ".xltm"))
_TEXT_SUFFIXES = frozenset((
    ".txt", ".log", ".csv", ".tsv", ".json", ".xml", ".rels", ".vml",
    ".html", ".htm", ".js", ".css", ".yaml", ".yml",
))


def _scan_zip(zf, prefix="", nested=False):
    """Scan one archive and the compressed XML inside Office workbooks.

    An XLSX is itself a ZIP. Scanning only its outer compressed bytes can miss a
    credential stored plainly in ``sharedStrings.xml``. The spooled copy stays
    in memory for small workbooks and spills to a temporary file for statewide
    ones, keeping the final publication gate bounded in RAM.
    """
    archive_hit = _scan_text_encodings(zf.comment or b"", allow_hash=True)
    if archive_hit:
        archive_name = f"{prefix}<archive-comment>"
        return archive_name, f"credential in ZIP comment ({archive_hit})"

    for info in zf.infolist():
        if info.is_dir():
            continue
        member = f"{prefix}{info.filename}"
        name_hit = sensitive_kind(info.filename)
        if name_hit:
            return member, f"credential in member name ({name_hit})"
        comment_hit = _scan_text_encodings(info.comment or b"", allow_hash=True)
        if comment_hit:
            return member, f"credential in member comment ({comment_hit})"
        # ZIP extra fields are binary metadata, so use the strong labelled/scheme/
        # JWT checks but not the broad URL-fragment heuristic.
        extra_hit = _scan_text_encodings(info.extra or b"", allow_hash=False)
        if extra_hit:
            return member, f"credential in member metadata ({extra_hit})"
        suffix = Path(info.filename).suffix.casefold()

        # The evidence allowlist admits XLSX files. Their outer bytes are a ZIP
        # container, not text: applying the broad URL-fragment heuristic to
        # compressed data creates false positives. Inspect the decompressed
        # members exactly once instead.
        if not nested and suffix in _NESTED_ZIP_SUFFIXES:
            try:
                with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as spool:
                    with zf.open(info, "r") as source:
                        shutil.copyfileobj(source, spool, length=64 * 1024)
                    # Scan the exact outer member bytes as well as its decompressed
                    # OOXML parts. This catches plaintext appended after the inner
                    # ZIP's end record while avoiding binary URL-fragment false hits.
                    spool.seek(0)
                    raw_hit = _scan_stream(spool, allow_hash=False)
                    if raw_hit:
                        return member, f"credential in raw Office member ({raw_hit})"
                    spool.seek(0)
                    if not zipfile.is_zipfile(spool):
                        return member, "unscannable Office workbook"
                    spool.seek(0)
                    with zipfile.ZipFile(spool, "r") as inner:
                        hit = _scan_zip(inner, prefix=f"{member}!", nested=True)
                if hit:
                    return hit
            except (OSError, RuntimeError, zipfile.BadZipFile):
                return member, "unscannable Office workbook"
            continue

        try:
            with zf.open(info, "r") as stream:
                # URL-fragment syntax is meaningful in diagnostics/OOXML text,
                # not arbitrary PDF/image bytes. The labelled/scheme/JWT guards
                # still scan binary members (including UTF-16 strings).
                hit = _scan_stream(stream, allow_hash=suffix in _TEXT_SUFFIXES)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            return member, "unscannable archive member"
        if hit:
            return member, hit
    return None


def scan_zip_members(path):
    """Return ``(member, kind)`` for the first unsafe final ZIP member, else None."""
    with zipfile.ZipFile(Path(path), "r") as zf:
        return _scan_zip(zf)

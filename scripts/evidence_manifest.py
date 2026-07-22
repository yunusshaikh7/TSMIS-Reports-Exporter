"""The durable per-comparison evidence generation record (CMP-AUD-106/109/098).

An evidence set is three artifacts that have to agree: the workbook, the image
folder, and this manifest. The manifest is the LAST member of the same two-phase
commit, so its presence proves the whole set landed. It records

  * which comparison generation the set describes — the comparison workbook's
    CONTENT digest plus the published ledger digest read out of that workbook's
    own cells (CMP-AUD-208), never an mtime;
  * the exact PDF READ SET the images were rendered from — path, size and
    SHA-256 of the private snapshot every locate/render call actually read
    (CMP-AUD-098), so "which bytes is this a picture of" has a durable answer;
  * a digest for every published member, so a torn or partially replaced set is
    detectable rather than merely unlikely.

A run that publishes NO artifacts still writes a manifest: `no_differences` and
`no_examples` are current states, not the absence of one. That is what lets a
reader tell "this comparison has nothing to illustrate" apart from "the evidence
never ran", and it is why `describe` treats a surviving workbook beside a
no-artifact manifest as an inconsistent set instead of as evidence.

The module is pure state: it decides nothing about sampling and renders nothing.
"""
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import artifact_store

log = logging.getLogger("tsmis")

MANIFEST_VERSION = 1

# What the generation produced. The three no-artifact states are as real as the
# rendered one — each is a claim about the CURRENT comparison.
STATE_RENDERED = "rendered"                # workbook + images published
STATE_NO_DIFFERENCES = "no_differences"    # the published comparison counts none
STATE_NO_EXAMPLES = "no_examples"          # differences exist, none photographable
STATE_DIVERTED = "diverted"                # the set could not reach canonical
STATES = frozenset({STATE_RENDERED, STATE_NO_DIFFERENCES, STATE_NO_EXAMPLES,
                    STATE_DIVERTED})
_ARTIFACT_STATES = frozenset({STATE_RENDERED})

# What `describe` found on disk.
ABSENT = "absent"            # no manifest — evidence never ran here
CURRENT = "current"          # the manifest describes THIS comparison, set intact
STALE = "stale"              # the comparison changed under the evidence set
INCOMPLETE = "incomplete"    # the manifest and the artifacts disagree
UNREADABLE = "unreadable"    # present but not a manifest we can trust


class EvidenceManifestError(ValueError):
    """A manifest that cannot be trusted to describe anything."""


def manifest_path(comparison_path):
    """The manifest sibling of a comparison workbook.

    Deliberately the same length as the '(evidence).xlsx' sibling: the field
    install depth is already at the Windows MAX_PATH budget (CMP-AUD-242), so a
    third sibling may not cost a single character more than the ones that fit.
    """
    p = Path(comparison_path)
    return p.with_name(f"{p.stem} (evidence).json")


@dataclass(frozen=True)
class Member:
    """One file the manifest is willing to vouch for."""
    name: str
    size: int
    sha256: str

    def as_payload(self):
        return {"name": self.name, "size": self.size, "sha256": self.sha256}

    @staticmethod
    def from_payload(raw, where):
        if not isinstance(raw, dict):
            raise EvidenceManifestError(f"{where} is not an object")
        try:
            name, size, sha = raw["name"], raw["size"], raw["sha256"]
        except KeyError as e:
            raise EvidenceManifestError(f"{where} has no {e.args[0]}") from None
        if not isinstance(name, str) or not name:
            raise EvidenceManifestError(f"{where} has no usable name")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise EvidenceManifestError(f"{where} has no usable size")
        if not isinstance(sha, str) or len(sha) != 64:
            raise EvidenceManifestError(f"{where} has no usable sha256")
        return Member(name=name, size=size, sha256=sha)


def member_for(path, name=None):
    """Measure one existing file. Raises OSError when it cannot be read."""
    path = Path(path)
    return Member(name=name or path.name, size=path.stat().st_size,
                  sha256=artifact_store.content_digest(path))


@dataclass(frozen=True)
class EvidenceManifest:
    version: int
    state: str
    report: str
    comparison: Member
    ledger_digest: str
    reader_version: int
    difference_cells: int
    differing_columns: int
    read_set: tuple
    workbook: object            # Member or None
    images: tuple
    seed: str
    layout: str
    examples: int
    note: str

    @property
    def claims_artifacts(self):
        return self.state in _ARTIFACT_STATES

    def as_payload(self):
        return {
            "version": self.version,
            "state": self.state,
            "report": self.report,
            "comparison": self.comparison.as_payload(),
            "ledger_digest": self.ledger_digest,
            "reader_version": self.reader_version,
            "difference_cells": self.difference_cells,
            "differing_columns": self.differing_columns,
            "read_set": [m.as_payload() for m in self.read_set],
            "workbook": self.workbook.as_payload() if self.workbook else None,
            "images": [m.as_payload() for m in self.images],
            "seed": self.seed,
            "layout": self.layout,
            "examples": self.examples,
            "note": self.note,
        }


def build(*, state, report, comparison_path, ledger_digest, reader_version,
          difference_cells, differing_columns, read_set=(), workbook=None,
          images=(), seed="", layout="", examples=0, note=""):
    """Assemble a manifest. `comparison_path`/`workbook` are measured here so a
    caller cannot record a digest it did not take."""
    if state not in STATES:
        raise EvidenceManifestError(f"unknown evidence state: {state!r}")
    return EvidenceManifest(
        version=MANIFEST_VERSION, state=state, report=str(report),
        comparison=member_for(comparison_path),
        ledger_digest=str(ledger_digest or ""),
        reader_version=int(reader_version or 0),
        difference_cells=int(difference_cells or 0),
        differing_columns=int(differing_columns or 0),
        read_set=tuple(read_set),
        workbook=(member_for(workbook) if workbook is not None else None),
        images=tuple(images), seed=str(seed or ""), layout=str(layout or ""),
        examples=int(examples or 0), note=str(note or ""))


def dumps(manifest):
    """Canonical text: sorted keys and a readable indent — a user may open it."""
    return json.dumps(manifest.as_payload(), sort_keys=True, indent=2,
                      ensure_ascii=False) + "\n"


def loads(text):
    try:
        raw = json.loads(text)
    except (ValueError, TypeError) as e:
        raise EvidenceManifestError(f"not readable JSON: {e}") from None
    if not isinstance(raw, dict):
        raise EvidenceManifestError("not a manifest object")
    version = raw.get("version")
    if version != MANIFEST_VERSION:
        raise EvidenceManifestError(
            f"manifest version {version!r} is not {MANIFEST_VERSION}")
    state = raw.get("state")
    if state not in STATES:
        raise EvidenceManifestError(f"unknown evidence state: {state!r}")
    workbook = raw.get("workbook")
    if state in _ARTIFACT_STATES and workbook is None:
        raise EvidenceManifestError(
            f"a {state!r} manifest names no workbook")
    if state not in _ARTIFACT_STATES and workbook is not None:
        raise EvidenceManifestError(
            f"a {state!r} manifest may not name a workbook")
    for key in ("read_set", "images"):
        if not isinstance(raw.get(key), list):
            raise EvidenceManifestError(f"{key} is not a list")
    return EvidenceManifest(
        version=MANIFEST_VERSION, state=state, report=str(raw.get("report", "")),
        comparison=Member.from_payload(raw.get("comparison"), "comparison"),
        ledger_digest=str(raw.get("ledger_digest", "")),
        reader_version=int(raw.get("reader_version") or 0),
        difference_cells=int(raw.get("difference_cells") or 0),
        differing_columns=int(raw.get("differing_columns") or 0),
        read_set=tuple(Member.from_payload(m, f"read_set[{i}]")
                       for i, m in enumerate(raw["read_set"])),
        workbook=(Member.from_payload(workbook, "workbook")
                  if workbook is not None else None),
        images=tuple(Member.from_payload(m, f"images[{i}]")
                     for i, m in enumerate(raw["images"])),
        seed=str(raw.get("seed", "")), layout=str(raw.get("layout", "")),
        examples=int(raw.get("examples") or 0), note=str(raw.get("note", "")))


def read(path):
    """Parse a manifest file. Returns None when it is not there; raises
    EvidenceManifestError when it is there but cannot be trusted."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:  # silent-ok: "no manifest" is a reported state, not an error
        return None
    except OSError as e:
        raise EvidenceManifestError(f"could not be read: {e}") from None
    return loads(text)


def _member_matches(path, member):
    """Whether `path` is still exactly the bytes the manifest vouched for."""
    try:
        if path.stat().st_size != member.size:
            return False
        return artifact_store.content_digest(path) == member.sha256
    except OSError:  # silent-ok: a member we cannot read is a member that does not match
        return False


def describe(comparison_path, verify_members=True):
    """What the evidence beside `comparison_path` currently claims.

    Returns {status, state, reason, manifest} where `status` is one of
    absent/current/stale/incomplete/unreadable. A stale result means the
    comparison's bytes changed since the evidence was generated — the case a
    rebuild with the evidence toggle OFF produces, and the reason evidence
    freshness may never be judged by mtime alone.
    """
    comparison_path = Path(comparison_path)
    man_path = manifest_path(comparison_path)
    try:
        manifest = read(man_path)
    except EvidenceManifestError as e:
        return {"status": UNREADABLE, "state": None, "manifest": None,
                "reason": f"the evidence manifest {man_path.name} {e}"}
    if manifest is None:
        return {"status": ABSENT, "state": None, "manifest": None,
                "reason": "no evidence manifest beside this comparison"}
    out = {"status": CURRENT, "state": manifest.state, "manifest": manifest,
           "reason": ""}
    if not _member_matches(comparison_path, manifest.comparison):
        out["status"] = STALE
        out["reason"] = ("the comparison workbook changed after this evidence "
                         "was generated")
        return out
    if not verify_members:
        return out
    wb_path, img_dir = sibling_artifacts(comparison_path)
    if manifest.claims_artifacts:
        if not _member_matches(wb_path, manifest.workbook):
            out["status"] = INCOMPLETE
            out["reason"] = "the evidence workbook is missing or changed"
            return out
        for image in manifest.images:
            if not _member_matches(img_dir / image.name, image):
                out["status"] = INCOMPLETE
                out["reason"] = f"the evidence image {image.name} is missing or changed"
                return out
        return out
    # A no-artifact state claims the canonical set was retired. A survivor means
    # the retirement failed (locked open) and the folder still shows evidence
    # for a generation the manifest says produced none.
    for path, label in ((wb_path, "workbook"), (img_dir, "image folder")):
        if os.path.lexists(path):
            out["status"] = INCOMPLETE
            out["reason"] = (f"a prior evidence {label} survives beside a "
                             f"'{manifest.state}' manifest")
            return out
    return out


def sibling_artifacts(comparison_path):
    """(workbook, image folder) — the naming the evidence engine publishes to.

    Kept here as well as in `visual_evidence.sibling_paths` so a manifest can be
    described without importing the render stack (pdfplumber/Pillow); the two
    are pinned equal by `check_visual_evidence`.
    """
    p = Path(comparison_path)
    return (p.with_name(f"{p.stem} (evidence){p.suffix}"),
            p.with_name(f"{p.stem} (evidence images)"))

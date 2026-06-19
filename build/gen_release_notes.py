#!/usr/bin/env python3
"""Assemble the GitHub release notes for one version.

Notes = the shared header (build/release_notes_header.md) + that version's
section from CHANGELOG.md. This keeps every release short and specific to its
own version instead of reprinting the whole project history.

Usage:
    python build/gen_release_notes.py v0.14.3            # print to stdout
    python build/gen_release_notes.py v0.14.3 -o notes.md

Exits non-zero (failing the release) if the version has no CHANGELOG section,
so a release can never go out with empty or stale notes.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def section_for(tag: str, changelog: str) -> str:
    """Return the CHANGELOG body under '## <tag>' up to the next '## ' heading."""
    lines = changelog.splitlines()
    # Match '## v0.14.3' with an optional ' — date' suffix.
    head = re.compile(r"^##\s+" + re.escape(tag) + r"(?:\s|$)")
    start = next((i for i, ln in enumerate(lines) if head.match(ln)), None)
    if start is None:
        return ""
    out = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        out.append(ln)
    return "\n".join(out).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", help="release tag, e.g. v0.14.3")
    ap.add_argument("-o", "--output", help="write to this file instead of stdout")
    args = ap.parse_args()

    header = (ROOT / "build" / "release_notes_header.md").read_text(encoding="utf-8").strip()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    section = section_for(args.tag, changelog)
    if not section:
        sys.stderr.write(
            f"ERROR: no '## {args.tag}' section in CHANGELOG.md. "
            f"Add the section before releasing {args.tag}.\n"
        )
        return 1

    notes = f"{header}\n\n## What's new in {args.tag}\n\n{section}\n"
    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

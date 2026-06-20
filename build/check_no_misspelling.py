"""Guard: the product name is TSMIS (Transportation System Management Information
System). The transposition 'TMSIS' is a recurring typo that has slipped into
comments, docs, and notes. This check FAILS the build if that misspelling appears
anywhere in the tracked source/docs, so a typo can never ship.

The forbidden token is assembled at runtime ("T" + "MSIS") so this guard file
does not match itself; the search is case-insensitive, so 'Tmsis'/'tmsis' are
caught too. 'TSMIS' (the correct spelling) is never a false positive — the needle
is a distinct character sequence.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_no_misspelling.py
"""
import os
import re
import sys

NEEDLE = "T" + "MSIS"                      # the forbidden transposition
_RX = re.compile(NEEDLE, re.IGNORECASE)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories never scanned (build artifacts, deps, generated/user data, VCS).
_SKIP_DIRS = {".git", ".venv", "venv", "dist", "build_out", "__pycache__",
              "node_modules", "output", "input", ".claude", ".idea", ".vscode"}
# Only these text kinds are scanned (skips xlsx/pdf/png/etc. binary fixtures).
_TEXT_EXT = {".py", ".md", ".txt", ".bat", ".ps1", ".spec", ".yml", ".yaml",
             ".js", ".css", ".html", ".json", ".cfg", ".ini", ".toml"}

_SELF = os.path.basename(__file__)


def _iter_files():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if name == _SELF:
                continue                   # defense-in-depth (needle is split anyway)
            if os.path.splitext(name)[1].lower() in _TEXT_EXT:
                yield os.path.join(root, name)


def find_offenders():
    offenders = []
    for path in _iter_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if _RX.search(line):
                        rel = os.path.relpath(path, REPO).replace("\\", "/")
                        offenders.append((rel, lineno, line.strip()))
        except OSError:
            continue
    return offenders


def main():
    offenders = find_offenders()
    if offenders:
        print(f"FAIL  product-name guard: found the '{NEEDLE}' misspelling "
              f"(should be 'TSMIS') in {len(offenders)} place(s):")
        for rel, lineno, text in offenders:
            print(f"  {rel}:{lineno}: {text[:120]}")
        sys.exit(1)
    print("OK  product-name guard: no '" + NEEDLE + "' misspelling anywhere "
          "(the name is always TSMIS).")


if __name__ == "__main__":
    main()

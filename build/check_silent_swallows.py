"""Tripwire: every swallowed exception in scripts/ logs (or is explicitly waived).

The project contract ("one log upload answers it", CLAUDE.md): each decision
point and every swallowed exception logs at least `type(e).__name__` + the first
message line. This check walks every `except` handler in scripts/*.py with AST
and fails on a SILENT swallow — a handler that neither logs, raises, nor calls
the events sink, and just pass/return/continue/assigns.

A deliberate last-resort site (e.g. the logging system itself failing, or a
cleanup inside an already-reported error path) is waived IN PLACE with a marker
comment on the `except` line:

    except OSError:                      # silent-ok: <why this may stay quiet>

The reason is mandatory — a bare `silent-ok` fails. Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_silent_swallows.py
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

_MARKER = re.compile(r"#\s*silent-ok:\s*(\S.*)$")
_LOGGY_ATTRS = {"debug", "info", "warning", "error", "exception", "critical", "log"}
_SINK_ATTRS = {"on_log", "on_status", "on_route"}


def _catches_importerror(handler):
    """The module-top deps-gate pattern (`except ImportError: _OK = False`) is a
    core convention — the absence is reported later via the deps message."""
    t = handler.type
    names = []
    if isinstance(t, ast.Name):
        names = [t.id]
    elif isinstance(t, ast.Tuple):
        names = [e.id for e in t.elts if isinstance(e, ast.Name)]
    return "ImportError" in names or "ModuleNotFoundError" in names


def _is_silent(handler):
    """True iff the exception truly VANISHES: no raise, no call of any kind
    (logging, events sink, onerror routing, or converting to an error result all
    involve a call), and only pass/continue/break/constant returns/assigns."""
    if _catches_importerror(handler):
        return False
    for node in ast.walk(handler):
        if isinstance(node, (ast.Raise, ast.Call)):
            return False
        if isinstance(node, ast.Return) and node.value is not None:
            v = node.value
            empty_container = (isinstance(v, (ast.List, ast.Tuple, ast.Dict))
                               and not getattr(v, "elts", getattr(v, "keys", None)))
            if not (isinstance(v, ast.Constant) or empty_container
                    or (isinstance(v, ast.UnaryOp) and isinstance(v.operand, ast.Constant))):
                return False               # returns a computed value: a conversion, not a swallow
    return True


BASELINE = Path(__file__).with_name("silent_swallows_baseline.txt")


def _load_baseline():
    """file.py:function-qualified entries accepted as PRE-EXISTING debt (not an
    endorsement — the Part-2 refactor waves burn this list down; new code can't
    add to it). Entries are `file.py:<handler line>`; regenerate after intended
    changes with --write-baseline and review the diff."""
    if not BASELINE.is_file():
        return set()
    return {l.strip() for l in BASELINE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


def main():
    write_baseline = "--write-baseline" in sys.argv
    baseline = set() if write_baseline else _load_baseline()
    offenders, keys, waived, grandfathered = [], [], 0, 0
    for p in sorted(SCRIPTS.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            offenders.append(f"{p.name}: does not parse ({e})")
            continue
        # innermost enclosing def per line -> a line-drift-stable baseline key
        funcs = sorted(
            ((n.lineno, max(getattr(n, "end_lineno", n.lineno), n.lineno), n.name)
             for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
            key=lambda t: t[1] - t[0])

        def _func_of(line):
            for lo, hi, name in funcs:
                if lo <= line <= hi:
                    return name
            return "<module>"

        per_func = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for h in node.handlers:
                if not _is_silent(h):
                    continue
                # the marker may sit on the `except` line or the line above it
                probe = " ".join(lines[max(0, h.lineno - 2):h.lineno])
                if _MARKER.search(probe):
                    waived += 1
                    continue
                fn = _func_of(h.lineno)
                per_func[fn] = per_func.get(fn, 0) + 1
                key = f"{p.name}:{fn}:{per_func[fn]}"
                keys.append(key)
                if key in baseline:
                    grandfathered += 1
                else:
                    offenders.append(f"{key}  (line {h.lineno})")
    if write_baseline:
        BASELINE.write_text(
            "# Pre-existing silent exception swallows, grandfathered as DEBT (not an\n"
            "# endorsement): the check blocks NEW ones; these get a log line or a\n"
            "# `# silent-ok:` marker as their files are touched (Part-2 waves).\n"
            "# Key: file.py:<enclosing function>:<ordinal within that function>.\n"
            + "\n".join(sorted(keys)) + "\n", encoding="utf-8")
        print(f"baseline written: {len(keys)} entries -> {BASELINE.name}")
        return 0
    stale = len(baseline) - grandfathered
    print(f"scanned scripts/*.py: {waived} waived (silent-ok), "
          f"{grandfathered} grandfathered ({stale} baseline entries no longer "
          f"match — prune when convenient), {len(offenders)} NEW silent swallow(s)")
    if offenders:
        print("NEW SILENT SWALLOWS (log it, raise, waive in place with "
              "`# silent-ok: <why>`, or — for a deliberate carry-over — "
              "regenerate the baseline and review its diff):")
        for o in offenders:
            print("  " + o)
        return 1
    print("all good")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Diagnostic check: APP_MODULES is the complete, reachable flat-module inventory.

`build/app.spec` carries a HAND-MAINTAINED `APP_MODULES` list -- every flat
`scripts/*.py` module (plus the repo-root `version.py`) declared as a PyInstaller
hidden import, because many are imported lazily / dynamically and the static
analysis alone would not collect them. That list silently drifted: `matrix`,
`day_matrix`, and `report_library` exist and are imported at runtime but were
absent from it (F6). They happen to be collected today via a transitive static
import, but the documented "list every flat module" packaging contract is broken,
and the next time one of those imports becomes function-local the module would
drop out of the frozen bundle with no warning.

This guard makes the packaging inventory an enforced contract, INDEPENDENT of the
spec it validates (it discovers the real `scripts/*.py` inventory itself rather
than trusting a list derived from the same place):
  * COMPLETENESS -- every shipped flat module (minus an explicit denylist) is
    declared in APP_MODULES  (this is the F6 tripwire).
  * NO STRAYS     -- every APP_MODULES entry maps to a real source file.
  * NO DUPLICATES.
  * REACHABILITY  -- every declared module is importable/locatable on the same
    pathex PyInstaller uses (`scripts/` + repo root).

The frozen `--self-test` gate (build.ps1 -SelfTest -> the exact shipped exe) is
the runtime half of the same contract; this offline check is the fast tripwire.

Pure stdlib (ast + importlib only); no app code is executed. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_app_modules.py
"""
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SPEC = ROOT / "build" / "app.spec"

# Flat scripts/*.py modules that intentionally do NOT need an APP_MODULES entry.
# Empty today: every flat scripts/ module is a runtime module the bundle must
# carry. Kept as the documented exception point (add a name here, with a reason,
# only if a flat module is genuinely never imported by the frozen app).
_DENYLIST = frozenset()

# Modules APP_MODULES legitimately carries that are NOT under scripts/ (repo-root
# files reachable via pathex=[SCRIPTS, REPO_ROOT]).
_ROOT_MODULES = frozenset({"version"})

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _parse_app_modules(spec_text):
    """Extract the APP_MODULES list literal from app.spec via AST. The spec can't
    be exec'd -- it references PyInstaller globals (SPECPATH, Analysis, ...) -- so
    we statically read just the list of string literals."""
    tree = ast.parse(spec_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "APP_MODULES" for t in node.targets):
            return list(ast.literal_eval(node.value))
    raise AssertionError("APP_MODULES assignment not found in build/app.spec")


def _diagnose(app_modules, inventory):
    """Return (duplicates, missing, stray) for an APP_MODULES list against a flat
    `scripts/` module inventory (set of stems). `missing` = a shipped module not
    declared (the F6 failure); `stray` = a declared name with no source file."""
    expected = (set(inventory) - _DENYLIST) | _ROOT_MODULES
    declared = set(app_modules)
    dups = sorted({m for m in app_modules if app_modules.count(m) > 1})
    missing = sorted(expected - declared)
    stray = sorted(declared - expected)
    return dups, missing, stray


def _locatable(name):
    """True if `import name` would resolve on the PyInstaller pathex (scripts/ +
    repo root). Uses find_spec, so the module is NOT executed."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _self_tests():
    """Prove the diagnosis actually catches each failure mode (a real future
    drift must not slip past -- the F6 omission did, for lack of this check)."""
    print("diagnosis self-tests (detection is real, not vacuous):")
    inv = {"alpha", "beta", "gamma"}
    full = sorted(inv | _ROOT_MODULES)
    dups, missing, stray = _diagnose(full, inv)
    check("a complete, unique APP_MODULES passes clean", not dups and not missing and not stray)
    _, missing, _ = _diagnose([m for m in full if m != "beta"], inv)
    check("a shipped module missing from APP_MODULES is caught (the F6 mode)", missing == ["beta"])
    _, _, stray = _diagnose(full + ["ghost"], inv)
    check("an APP_MODULES entry with no source file is caught", stray == ["ghost"])
    dups, _, _ = _diagnose(full + ["alpha"], inv)
    check("a duplicate APP_MODULES entry is caught", dups == ["alpha"])


def main():
    _self_tests()
    print()
    app_modules = _parse_app_modules(SPEC.read_text(encoding="utf-8"))
    inventory = {p.stem for p in SCRIPTS.glob("*.py")}
    print(f"app.spec APP_MODULES: {len(app_modules)} entries; "
          f"scripts/ flat inventory: {len(inventory)} modules")

    dups, missing, stray = _diagnose(app_modules, inventory)
    check("APP_MODULES has no duplicates", not dups)
    if dups:
        print("   duplicated:", dups)
    check("every shipped flat scripts/ module is declared in APP_MODULES (F6)", not missing)
    if missing:
        print("   MISSING from APP_MODULES:", missing)
    check("no APP_MODULES entry lacks a scripts/ or root source file", not stray)
    if stray:
        print("   stray (no source file):", stray)

    # Reachability: every declared module must resolve on the pathex PyInstaller
    # uses. Put scripts/ + repo root in front, like app.spec's pathex.
    sys.path[:0] = [str(SCRIPTS), str(ROOT)]
    unreachable = sorted(m for m in app_modules if not _locatable(m))
    check("every APP_MODULES entry is importable/locatable on pathex", not unreachable)
    if unreachable:
        print("   unreachable:", unreachable)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL APP-MODULE PACKAGING CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

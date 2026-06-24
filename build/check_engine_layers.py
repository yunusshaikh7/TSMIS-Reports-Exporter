"""P8b: engine-layer decomposition lock (browser_channels / auth_nav / report_nav /
edge_device / session) + the common re-export-shim contract.

P8b moves the rest of common.py (the field-hardened browser / auth / Edge-device /
session flows) into a verified acyclic DAG of flat modules, behind the common shim.
This check locks the STRUCTURE the move must preserve:

  1. Shim parity: `from common import X` yields the SAME object the owning module
     defines (a re-export, not a copy) for every moved public name — the import
     surface is byte-identical.
  2. No upward import: no engine module imports `common` at load time, so the shim
     is strictly one-way (common -> layers, never layers -> common).
  3. DAG layering: each engine module's module-level sibling imports stay within its
     allowed lower set (leaves + paths + the engine layers below it), so the
     decomposition matches the approved §E DAG (leaves -> channels/auth -> report ->
     edge -> session). Acyclicity itself is enforced by check_import_direction.
  4. Thread-agnostic engine: no engine module pulls in `threading` at module level.
     The Playwright sync API is thread-affine; thread ownership lives with the
     calling worker (gui_worker), NOT the engine library. The verbatim move keeps
     every page-touching body unchanged, so the thread-affinity contract is
     preserved; this assertion is the static tripwire that a later edit doesn't
     smuggle shared threading into the engine layer.

Pure stdlib (ast + import); no browser, no network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_engine_layers.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path[:0] = [str(SCRIPTS), str(ROOT)]

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


# Public names each engine module owns + the shim must re-export. This is the §E-named
# public DAG surface: every name §E lists for a layer, including the two helpers no
# in-repo consumer imports today (`dump_auth_failure`, `open_edge_device_context`) — the
# shim contract is "re-export all of the above" (§E), so parity locks them too (P8b-R01).
OWNS = {
    "browser_channels": ["BROWSER_CHANNELS", "CHANNEL_LABELS", "LOGIN_BROWSER_ARGS",
        "check_browsers", "get_preferred_channel", "init_preferred_channel_from_settings",
        "set_preferred_channel", "launch_browser", "new_login_context", "resolve_parallel_channel"],
    "auth_nav": ["clear_auth", "require_valid_auth", "has_valid_auth", "save_auth_state",
        "_auth_file_age_hours", "auth_state", "navigate_with_auth", "is_logged_in",
        "require_signed_in", "require_site_params", "dump_auth_failure", "_CONFIG_JS",
        "page_url_for_display"],
    "report_nav": ["ERROR_JS", "EXPORT_READY_JS", "maybe_screenshot", "preflight",
        "report_error_text", "select_report", "wait_with_skip_option"],
    "edge_device": ["capture_edge_login_state_from_profiles", "capture_edge_login_state_over_cdp",
        "capture_storage_state_if_logged_in", "launch_edge_login_context",
        "open_edge_device_context", "storage_state_is_portable", "try_device_sso_login"],
    "session": ["new_authed_browser"],
}

LEAVES = {"errors", "site_target", "timeouts", "routes", "paths"}
# Allowed module-level sibling imports per engine module (leaves + the lower engine layers).
ALLOWED = {
    "browser_channels": LEAVES,
    "auth_nav": LEAVES,
    "report_nav": LEAVES | {"auth_nav"},
    "edge_device": LEAVES | {"auth_nav", "browser_channels"},
    "session": LEAVES | {"auth_nav", "browser_channels", "edge_device", "report_nav"},
}
ENGINE = set(OWNS)


def _module_level_imports(path):
    """scripts-sibling modules imported at MODULE LOAD time (descends module-scope
    try/if/with, skips function/class bodies) + a flag for `threading`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    local = {p.stem for p in SCRIPTS.glob("*.py")}
    sib, threads = set(), False

    def visit(node):
        nonlocal threads
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(child, ast.Import):
                for a in child.names:
                    top = a.name.split(".")[0]
                    if top == "threading":
                        threads = True
                    if top in local:
                        sib.add(top)
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                top = child.module.split(".")[0]
                if top == "threading":
                    threads = True
                if top in local:
                    sib.add(top)
            visit(child)

    visit(tree)
    return sib, threads


def test_shim_parity():
    print("shim parity: common re-exports the SAME engine objects (import surface intact):")
    import common
    import importlib
    for mod, names in OWNS.items():
        m = importlib.import_module(mod)
        for n in names:
            check(f"common.{n} is {mod}.{n}", getattr(common, n) is getattr(m, n))


def test_layering_and_no_upward():
    print("DAG layering: engine modules import only leaves + lower engine layers (never common):")
    for mod in OWNS:
        sib, _ = _module_level_imports(SCRIPTS / f"{mod}.py")
        engine_sib = sib & (ENGINE | LEAVES)
        check(f"{mod} does NOT import common", "common" not in sib)
        extra = engine_sib - ALLOWED[mod]
        check(f"{mod} imports only its allowed lower set ({sorted(engine_sib) or 'none'})", not extra)
        if extra:
            print(f"      DISALLOWED: {sorted(extra)}")


def test_thread_agnostic_engine():
    print("thread-agnostic engine: no engine module pulls in threading at module level:")
    for mod in OWNS:
        _, threads = _module_level_imports(SCRIPTS / f"{mod}.py")
        check(f"{mod} has no module-level threading (affinity owned by the caller)", not threads)


def main():
    test_shim_parity()
    test_layering_and_no_upward()
    test_thread_agnostic_engine()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL ENGINE-LAYER CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

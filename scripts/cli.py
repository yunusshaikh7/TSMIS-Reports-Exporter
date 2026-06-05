"""Console adapters for the engines.

Wires the engines' Events callbacks to print()/msvcrt/input() and handles the
console UX (AuthError messaging, the overwrite prompt) so the existing batch
files keep working unchanged after the refactor. The engines themselves never
touch the console -- only this module does.
"""
import os
import sys

from common import AUTH, ROUTES, AuthError, BrowserNotFoundError, PreflightError, clear_auth, parse_routes
from events import Events
from logging_setup import setup_logging

try:
    import msvcrt  # Windows: read keystrokes without blocking
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False


# --- export console flow ------------------------------------------------------

def _drain_skip_key():
    """True if 'S' was pressed since the last check (Windows console only)."""
    if not _HAS_KEYBOARD:
        return False
    pressed = False
    while msvcrt.kbhit():
        try:
            ch = msvcrt.getwch()
        except Exception:
            ch = ""
        if ch and ch.lower() == "s":
            pressed = True
    return pressed


def _console_events():
    return Events(on_log=print, should_skip=_drain_skip_key)


def _resolve_routes_console():
    """Decide which routes to export in the console flow. Returns None for
    "all routes", otherwise a validated route list.

    Honors the TSMIS_ROUTES environment variable if set (a comma/space list, or
    'all'/empty to mean all routes); otherwise prompts interactively, re-asking
    on invalid input. Pressing Enter (or EOF, e.g. a non-interactive window)
    means all routes, so the default behavior is unchanged.
    """
    env = os.environ.get("TSMIS_ROUTES")
    if env is not None and env.strip():
        if env.strip().lower() == "all":
            return None
        try:
            return parse_routes(env)
        except ValueError as e:
            print(f"TSMIS_ROUTES ignored: {e}")   # fall through to the prompt

    while True:
        try:
            raw = input(
                "Routes to export -- press Enter for ALL, or list specific "
                "routes (e.g. 5, 99, 101): "
            ).strip()
        except EOFError:
            return None
        if not raw or raw.lower() == "all":
            return None
        try:
            return parse_routes(raw)
        except ValueError as e:
            print(f"  {e}  Try again, or press Enter to export all routes.")


def _report_bad_auth(reason):
    """Mirror the original handle_bad_auth console UX."""
    print()
    print("=" * 60)
    print("LOGIN PROBLEM")
    print("=" * 60)
    print(f"Reason: {reason}")
    print()
    if clear_auth():
        print(f"Deleted stale session file: {AUTH.name}")
    print()
    print('Next step:  Close this window, then run  "2. login (update login).bat"')
    print("=" * 60)
    input("\nPress Enter to exit...")
    sys.exit(1)


def run_cli(spec, title):
    """Run one report export as a console program. Used by the export_*.py
    entry points and therefore by '3. run_export (main script).bat'.

    If the TSMIS_FAST_WORKERS environment variable is set to a number > 1
    (e.g. by '5. fast export (experimental).bat'), the experimental parallel
    engine runs several browsers at once instead of the proven sequential one."""
    from exporter import run_export  # lazy: avoids importing Playwright for consolidation

    setup_logging()

    workers = 1
    if os.environ.get("TSMIS_FAST_WORKERS", "").strip():
        from exporter_parallel import resolve_worker_count
        workers = resolve_worker_count()

    routes = _resolve_routes_console()          # None = all routes
    run_routes = ROUTES if routes is None else routes
    selected = len(run_routes)

    print("=" * 60)
    if routes is None:
        print(f"{title} -- {selected} routes")
    else:
        print(f"{title} -- {selected} of {len(ROUTES)} routes: {', '.join(run_routes)}")
    if workers > 1:
        print(f"FAST MODE (experimental): {workers} browsers in parallel")
    print("=" * 60)
    if workers == 1 and _HAS_KEYBOARD:
        print("Tip: press 'S' to skip a route that is taking too long.")
    print()

    try:
        if workers > 1:
            from exporter_parallel import run_export_parallel
            result = run_export_parallel(spec, _console_events(), workers=workers, routes=run_routes)
        else:
            result = run_export(spec, _console_events(), routes=run_routes)
    except AuthError as e:
        _report_bad_auth(str(e))
        return
    except (PreflightError, BrowserNotFoundError) as e:
        print()
        print("=" * 60)
        print(f"PROBLEM: {e}")
        print("=" * 60)
        input("\nPress Enter to exit...")
        sys.exit(1)

    already = len(result.exists)
    total = result.saved + already + len(result.empty) + len(result.user_skipped) + len(result.failed)
    print()
    print("=" * 60)
    print(f"Saved this run:  {result.saved}")
    print(f"Already had:     {already} (saved in a previous run)")
    print(f"Empty (no data): {len(result.empty)} {result.empty if result.empty else ''}")
    print(f"Skipped by user: {len(result.user_skipped)} {result.user_skipped if result.user_skipped else ''}")
    print(f"Failed:          {len(result.failed)} {result.failed if result.failed else ''}")
    print(f"Routes handled:  {total} of {selected}")
    print(f"Output folder:   {result.output_dir}")
    print("=" * 60)


# --- consolidate console flow -------------------------------------------------

def _confirm_overwrite_console(path):
    """Y/N overwrite prompt for the console flow. EOF (window closed) -> No,
    so double-clicking the BAT and closing it doesn't look like a crash."""
    print()
    print("A consolidated workbook already exists at:")
    print(f"   {path}")
    try:
        ans = input("Overwrite it? [Y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def run_consolidate_cli(consolidate_fn):
    """Run one consolidator as a console program. Used by the consolidate_*.py
    entry points and therefore by '4. consolidate (combine reports).bat'.

    The consolidator logs its own progress through Events.on_log and returns a
    ConsolidateResult; this shim renders the outcome and sets the exit code.
    """
    setup_logging()
    result = consolidate_fn(
        events=Events(on_log=print),
        confirm_overwrite=_confirm_overwrite_console,
    )

    if result.status == "cancelled":
        print(result.message or "Cancelled.")
        return
    if result.status == "error":
        print()
        print("=" * 60)
        print(f"ERROR: {result.message}")
        print("=" * 60)
        sys.exit(1)

    print()
    print("=" * 60)
    for line in result.summary_lines:
        print(line)
    print("=" * 60)

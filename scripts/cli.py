"""Console adapter for the export engine.

Wires the engine's Events callbacks to print()/msvcrt and handles AuthError
the way the .bat workflow expects (message + clear the stale file + exit), so
the existing batch files keep working unchanged after the refactor.
"""
import sys

from common import AUTH, ROUTES, AuthError, clear_auth
from events import Events
from exporter import run_export

try:
    import msvcrt  # Windows: read keystrokes without blocking
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False


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
    entry points and therefore by '3. run_export (main script).bat'."""
    print("=" * 60)
    print(f"{title} -- {len(ROUTES)} routes")
    print("=" * 60)
    if _HAS_KEYBOARD:
        print("Tip: press 'S' to skip a route that is taking too long.")
    print()

    try:
        result = run_export(spec, _console_events())
    except AuthError as e:
        _report_bad_auth(str(e))
        return

    print()
    print("=" * 60)
    print(f"Saved this run:  {result.saved}")
    print(f"Empty (skipped): {len(result.empty)} {result.empty if result.empty else ''}")
    print(f"Skipped by user: {len(result.user_skipped)} {result.user_skipped if result.user_skipped else ''}")
    print(f"Failed:          {len(result.failed)} {result.failed if result.failed else ''}")
    print(f"Output folder:   {result.output_dir}")
    print("=" * 60)

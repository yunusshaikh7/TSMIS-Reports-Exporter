"""Console adapters for the engines.

Wires the engines' Events callbacks to print()/msvcrt/input() and handles the
console UX (AuthError messaging, the overwrite prompt) so the existing batch
files keep working unchanged after the refactor. The engines themselves never
touch the console -- only this module does.
"""
import logging
import os
import re
import sys

from common import AUTH, ROUTES, AuthError, BrowserNotFoundError, PreflightError, clear_auth, parse_routes
from events import Events
from logging_setup import setup_logging

try:
    import msvcrt  # Windows: read keystrokes without blocking
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False

# Console status lines are mirrored into tsmis.log (like the GUI's log pane),
# so a .bat run leaves the same diagnosable trail as the desktop app.
ui_log = logging.getLogger("tsmis.ui")
log = logging.getLogger("tsmis.cli")


def _echo(line=""):
    """print() that also lands in the file log (blank lines skipped there)."""
    print(line)
    if str(line).strip():
        ui_log.info("%s", line)


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
    return Events(on_log=_echo, should_skip=_drain_skip_key)


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
    log.warning("run stopped: AuthError: %s", reason)
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


def _resolve_workers():
    """Worker count for the console flow: TSMIS_FAST_WORKERS if set (>1 -> the
    experimental parallel engine), else 1 (the proven sequential engine)."""
    if os.environ.get("TSMIS_FAST_WORKERS", "").strip():
        from exporter_parallel import resolve_worker_count
        return resolve_worker_count()
    return 1


def _run_one_export(spec, events, workers, run_routes):
    """Run one report's export, dispatching to the parallel engine when
    workers > 1 else the sequential one. Imports are lazy so consolidation never
    pulls in Playwright. Raises AuthError / PreflightError / BrowserNotFoundError
    like the engines."""
    if workers > 1:
        from exporter_parallel import run_export_parallel
        return run_export_parallel(spec, events, workers=workers, routes=run_routes)
    from exporter import run_export
    return run_export(spec, events, routes=run_routes)


def _print_export_summary(result, selected):
    """Print the per-report outcome block shared by the single and multi flows."""
    already = len(result.exists)
    total = result.saved + already + len(result.empty) + len(result.user_skipped) + len(result.failed)
    _echo(f"Saved this run:  {result.saved}")
    _echo(f"Already had:     {already} (saved in a previous run)")
    _echo(f"Empty (no data): {len(result.empty)} {result.empty if result.empty else ''}")
    _echo(f"Skipped by user: {len(result.user_skipped)} {result.user_skipped if result.user_skipped else ''}")
    _echo(f"Failed:          {len(result.failed)} {result.failed if result.failed else ''}")
    _echo(f"Routes handled:  {total} of {selected}")
    _echo(f"Output folder:   {result.output_dir}")


def run_cli(spec, title):
    """Run one report export as a console program. Used by the export_*.py
    entry points and therefore by '3. run_export (main script).bat'.

    If the TSMIS_FAST_WORKERS environment variable is set to a number > 1
    (e.g. by '5. fast export (experimental).bat'), the experimental parallel
    engine runs several browsers at once instead of the proven sequential one."""
    setup_logging()
    workers = _resolve_workers()

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
        result = _run_one_export(spec, _console_events(), workers, run_routes)
    except AuthError as e:
        _report_bad_auth(str(e))
        return
    except (PreflightError, BrowserNotFoundError) as e:
        log.warning("run stopped: %s: %s", type(e).__name__, e)
        print()
        print("=" * 60)
        print(f"PROBLEM: {e}")
        print("=" * 60)
        input("\nPress Enter to exit...")
        sys.exit(1)

    print()
    print("=" * 60)
    _print_export_summary(result, selected)
    print("=" * 60)


def _select_reports_console(report_options):
    """Choose which report types to export. report_options is an ordered list of
    (label, spec); returns the chosen subset in menu order.

    Enter / 'A' / 'all' (or EOF) = all; otherwise numbers like '1,3'. Honors the
    TSMIS_REPORTS env var (numbers or 'all'). Re-prompts on invalid input."""
    n = len(report_options)

    def parse(sel):
        sel = sel.strip().lower()
        if sel in ("", "a", "all"):
            return list(report_options)
        chosen_idx, bad = set(), []
        for tok in (t for t in re.split(r"[\s,;]+", sel) if t):
            if tok.isdigit() and 1 <= int(tok) <= n:
                chosen_idx.add(int(tok) - 1)
            else:
                bad.append(tok)
        if bad:
            raise ValueError("Not valid choice(s): " + ", ".join(bad))
        return [opt for i, opt in enumerate(report_options) if i in chosen_idx]  # menu order

    env = os.environ.get("TSMIS_REPORTS")
    if env is not None and env.strip():
        try:
            return parse(env)
        except ValueError as e:
            print(f"TSMIS_REPORTS ignored: {e}")   # fall through to the prompt

    print("Which report types do you want to export?")
    for i, (label, _spec) in enumerate(report_options, 1):
        print(f"   {i}. {label}")
    while True:
        try:
            raw = input("Enter numbers (e.g. 1,3), or A for all: ").strip()
        except EOFError:
            return list(report_options)
        try:
            chosen = parse(raw)
        except ValueError as e:
            print(f"  {e}  Try again.")
            continue
        if chosen:
            return chosen
        print("  Please choose at least one report.")


def run_cli_multi(report_options, title="TSMIS Multi-Report Export"):
    """Export SEVERAL report types in one console run. report_options is an
    ordered list of (label, spec). Prompts which reports + which routes once, then
    runs each selected report with the proven engine (sequential, or fast mode if
    TSMIS_FAST_WORKERS is set). Backs the 'Several / all report types' BAT option."""
    setup_logging()
    workers = _resolve_workers()

    chosen = _select_reports_console(report_options)
    if not chosen:
        print("No reports selected.")
        return

    routes = _resolve_routes_console()          # None = all routes
    run_routes = ROUTES if routes is None else routes
    selected = len(run_routes)

    print()
    print("=" * 60)
    print(f"{title}: {len(chosen)} report type(s)")
    for label, _spec in chosen:
        print(f"   - {label}")
    if routes is None:
        print(f"Routes: all ({selected})")
    else:
        print(f"Routes: {selected} of {len(ROUTES)}: {', '.join(run_routes)}")
    if workers > 1:
        print(f"FAST MODE (experimental): {workers} browsers in parallel")
    print("=" * 60)
    if workers == 1 and _HAS_KEYBOARD:
        print("Tip: press 'S' to skip a route that is taking too long.")

    results = []
    for i, (label, spec) in enumerate(chosen, 1):
        print()
        print("#" * 60)
        print(f"# Report {i} of {len(chosen)}:  {label}")
        print("#" * 60)
        try:
            result = _run_one_export(spec, _console_events(), workers, run_routes)
        except AuthError as e:
            _report_bad_auth(str(e))             # a bad session breaks every report -> stop
            return
        except (PreflightError, BrowserNotFoundError) as e:
            log.warning("run stopped: %s: %s", type(e).__name__, e)
            print()
            print("=" * 60)
            print(f"PROBLEM: {e}")
            print("=" * 60)
            input("\nPress Enter to exit...")
            sys.exit(1)
        results.append((label, result))
        print()
        _print_export_summary(result, selected)

    print()
    print("=" * 60)
    print(f"ALL DONE -- {len(results)} report type(s)")
    for label, r in results:
        line = (f"  {label}: saved {r.saved}, already {len(r.exists)}, "
                f"empty {len(r.empty)}, skipped {len(r.user_skipped)}, failed {len(r.failed)}")
        print(line + (f"  -> {r.failed}" if r.failed else ""))
    print(f"Total saved this run: {sum(r.saved for _, r in results)}; "
          f"total failed: {sum(len(r.failed) for _, r in results)}")
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


def _resolve_day_console():
    """Pick which export run folder to consolidate.

    Run folders are named "<YYYY-MM-DD> <src>-<env>" (legacy bare-date folders
    read as ssor-prod). Honors TSMIS_DAY (a folder name, or a bare date — the
    newest run folder of that date wins); otherwise prompts only when several
    run folders exist (Enter / EOF = newest). Returns the chosen folder name,
    or None when none exist yet (the consolidators then fall back to the
    legacy flat layout)."""
    from paths import list_output_days, resolve_day_choice
    env = os.environ.get("TSMIS_DAY", "").strip()
    if env:
        return resolve_day_choice(env)
    days = list_output_days()
    if not days:
        return None
    if len(days) == 1:
        return days[0]
    print()
    print("Export folders found:")
    for i, d in enumerate(days, 1):
        print(f"  {i}. {d}" + ("   (newest)" if i == 1 else ""))
    try:
        raw = input("Which one? [Enter = newest]: ").strip()
    except EOFError:
        raw = ""
    if raw in days:
        return raw
    if raw.isdigit() and 1 <= int(raw) <= len(days):
        return days[int(raw) - 1]
    return days[0]


def run_consolidate_cli(consolidate_fn):
    """Run one consolidator as a console program. Used by the consolidate_*.py
    entry points and therefore by '4. consolidate (combine reports).bat'.

    The consolidator logs its own progress through Events.on_log and returns a
    ConsolidateResult; this shim renders the outcome and sets the exit code.
    """
    setup_logging()
    day = _resolve_day_console()
    log.info("consolidate start: %s (day=%s)",
             getattr(consolidate_fn, "__module__", consolidate_fn),
             day or "legacy/newest")
    if day:
        print(f"Consolidating the {day} exports.")
    result = consolidate_fn(
        events=Events(on_log=_echo),
        confirm_overwrite=_confirm_overwrite_console,
        day=day,
    )
    log.info("consolidate done: status=%s output=%s message=%s",
             result.status, result.output_path or "-", result.message or "-")

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
        _echo(line)
    print("=" * 60)

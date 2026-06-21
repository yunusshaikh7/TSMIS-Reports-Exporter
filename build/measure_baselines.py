"""Record P0 performance baselines (R1-A01) reproducibly.

Two measurements, both with R1-A01 metadata (environment, data shape, repeats,
percentile):

  * process-COLD GUI startup -- a FRESH Python process per repeat that times
    `import gui_api` (the eager dependency-graph import F11 / the P10 lazy-import
    work target) AND the stubbed `GuiApi() + get_initial_state()` construction.
  * WARM matrix snapshot -- `matrix_info()` on an already-constructed instance,
    modules pre-imported.

This is a measurement TOOL, not a pass/fail check (it prints numbers and exits 0),
so it is intentionally named `measure_*` and is NOT wired into checks.yml. Run:

    build\\.venv\\Scripts\\python.exe build\\measure_baselines.py [--repeats N]

The update check and browser probes are stubbed so the number reflects
deterministic startup, not GitHub network / browser-probe latency.
"""
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _cold_once():
    """Run in a FRESH process: time `import gui_api`, then the stubbed
    initial-state construction. Prints 'import_ms init_ms total_ms'."""
    sys.path[:0] = [str(SCRIPTS), str(ROOT)]
    t0 = time.perf_counter()
    import gui_api
    t_import = (time.perf_counter() - t0) * 1000
    gui_api.GuiApi._start_update_check = lambda self: None     # no GitHub network
    gui_api.GuiApi._start_checks_locked = lambda self: None    # no browser-probe threads
    t1 = time.perf_counter()
    a = gui_api.GuiApi()
    a.get_initial_state()
    t_init = (time.perf_counter() - t1) * 1000
    print(f"{t_import:.2f} {t_init:.2f} {t_import + t_init:.2f}")


def _pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def _row(name, xs):
    print(f"{name:46s} min={min(xs):8.2f} median={statistics.median(xs):8.2f} "
          f"p95={_pct(xs, 0.95):8.2f} max={max(xs):8.2f}")


def main(repeats):
    print("=== ENVIRONMENT (R1-A01) ===")
    print(f"python : {platform.python_version()} ({platform.architecture()[0]})")
    print(f"os     : {platform.system()} {platform.release()} ({platform.machine()})")

    imp, ini, tot = [], [], []
    for _ in range(repeats):
        out = subprocess.run(
            [sys.executable, str(Path(__file__)), "--cold-once"],
            capture_output=True, text=True, check=True).stdout.split()
        a, b, c = (float(x) for x in out[-3:])
        imp.append(a)
        ini.append(b)
        tot.append(c)

    sys.path[:0] = [str(SCRIPTS), str(ROOT)]
    import gui_api
    import settings
    dest = settings.get_batch_dest()
    ndays = (len([p for p in Path(dest).glob("*") if p.is_dir()])
             if dest and Path(dest).exists() else 0)
    a = gui_api.GuiApi()
    warm = []
    for _ in range(repeats):
        t = time.perf_counter()
        a.matrix_info()
        warm.append((time.perf_counter() - t) * 1000)

    print("\n=== DATA SHAPE ===")
    print(f"batch_dest day-folders: {ndays}; matrix baseline: {a._current_baseline()}")
    print(f"\n=== BASELINES (ms; {repeats} repeats) ===")
    print("process-COLD (fresh process each; INCLUDES import gui_api):")
    _row("  import gui_api", imp)
    _row("  stubbed GuiApi()+get_initial_state", ini)
    _row("  TOTAL cold startup", tot)
    print("WARM (in-process, modules pre-imported):")
    _row("  matrix_info()", warm)


if __name__ == "__main__":
    if "--cold-once" in sys.argv:
        _cold_once()
    else:
        reps = 7
        if "--repeats" in sys.argv:
            reps = int(sys.argv[sys.argv.index("--repeats") + 1])
        main(reps)

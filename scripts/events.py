"""Lightweight, dependency-free seams between the engines and whatever is
driving them (the console shim today, the GUI later).

The engine never prints, prompts, or exits: it pushes status through an
Events sink and returns a RunResult. The console shim wires these callbacks to
print()/msvcrt; the GUI will wire them to a queue + widgets.
"""
from dataclasses import dataclass, field
from typing import List


def _noop_log(message):
    pass


def _noop_route(route, status):
    pass


def _never():
    return False


def _noop_status(worker, text):
    pass


def _never_shot(worker):
    return False


def _noop_screenshot(worker, image, note, url=""):
    pass


class Events:
    """Callbacks the engine uses to report progress and check for control input.

    on_log:       human-readable status line (console prints it; GUI appends it
                  to a log pane).
    on_route:     per-route outcome; status is one of
                  {"saved", "empty", "skipped", "failed", "exists"}.
    should_skip:  return True to skip the route currently being waited on.
    is_cancelled: return True to stop the whole run before the next route.
    is_paused:    return True to HOLD the run between routes (B1 pause/resume);
                  the engine spins at the between-route point until it clears or
                  the run is cancelled. Honored in fast mode too (all workers
                  park between their routes).

    Live browser-status / preview seam (GUI status rows; the console flow
    leaves these as no-ops):

    worker_no:          which browser this sink reports for — 1 in the
                        sequential engine; fast mode wraps the shared sink in
                        per-worker Events carrying each worker's number.
    on_status(worker, text):
                        one-line "what this browser is doing right now"
                        (distinct from on_log: statuses REPLACE each other,
                        log lines accumulate).
    screenshot_wanted(worker) -> bool:
                        polled by the engine at safe points on the worker's
                        own thread (Playwright is thread-affine); True means
                        "snap the page now". Implementations must clear the
                        request before returning True (one request = one shot).
    on_screenshot(worker, image, note, url):
                        the requested capture — `image` is JPEG bytes (or None
                        when the capture failed; `note` then says why), `url`
                        the page's address at capture time ("" when unknown).

    All default to harmless no-ops, so Events() is a valid silent sink.
    """

    def __init__(self, on_log=None, on_route=None, should_skip=None, is_cancelled=None,
                 on_status=None, screenshot_wanted=None, on_screenshot=None,
                 is_paused=None, worker_no=1):
        self.on_log = on_log or _noop_log
        self.on_route = on_route or _noop_route
        self.should_skip = should_skip or _never
        self.is_cancelled = is_cancelled or _never
        self.on_status = on_status or _noop_status
        self.screenshot_wanted = screenshot_wanted or _never_shot
        self.on_screenshot = on_screenshot or _noop_screenshot
        self.is_paused = is_paused or _never
        self.worker_no = worker_no


@dataclass
class RunResult:
    """Outcome of one export run."""
    saved: int = 0
    empty: List[str] = field(default_factory=list)
    user_skipped: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    exists: List[str] = field(default_factory=list)   # already on disk from a previous run
    output_dir: str = ""
    # Ordered (route, status) for every route processed this run -- the data
    # behind the saved run report. status is one of:
    # saved | empty | skipped | failed | exists.
    per_route: List = field(default_factory=list)
    report_path: str = ""           # where the run report CSV was auto-saved
    # Orthogonal outcome contract (P1 / outcome.py), producer/store-owned. Default
    # None for intra-version safety: a path that hasn't set them reads as "absent"
    # (consumers fall back to inferring/`complete`). `completion` is one of
    # outcome.COMPLETIONS; `artifact` one of outcome.ARTIFACTS (set by the store
    # swap layer that knows promoted vs previous_preserved).
    completion: str = None
    artifact: str = None


@dataclass
class ConsolidateResult:
    """Outcome of one consolidation run.

    status is one of:
      "ok"        -- workbook written; summary_lines describe the result.
      "cancelled" -- user declined (e.g. the overwrite prompt) or cancelled
                     mid-run; message says why.
      "error"     -- could not complete; message explains it and is safe to
                     show to the user as-is.

    The engine fills summary_lines with its own report-specific summary so the
    console shim and the GUI can display results without re-deriving them.

    Comparisons additionally set `verdict`: "match" when the two sides are
    identical (no differing cells, no one-sided rows), "diff" otherwise —
    summary_lines[0] is then the human verdict line.  During the typed-outcome
    migration this legacy field remains for compatibility, but production UI
    state is accepted only through the trusted returned/persisted comparison
    generation; consolidators leave it None.
    """
    status: str = "ok"
    message: str = ""
    output_path: str = ""
    summary_lines: List[str] = field(default_factory=list)
    verdict: str = None            # None | "match" | "diff" (comparisons only)
    # Orthogonal outcome contract (P1 / outcome.py), PRODUCER-owned. `status` stays
    # the coarse ok/cancelled/error; `completion` adds the finer `partial` axis a
    # status="ok"-with-skipped run hid (one of outcome.COMPLETIONS; None on a path
    # that predates this, inferred from `status` by outcome.consolidate_completion_of).
    # The structured counts behind a `partial`: inputs left out of the output.
    completion: str = None
    skipped_inputs: int = 0        # inputs with no data / left out
    failed_inputs: int = 0         # inputs that failed to parse/read
    # Phase-2 comparison migration.  These remain optional so every legacy
    # constructor and consolidator keeps its exact call surface.  Comparison
    # producers fill them with objects from comparison_contract; consumers use
    # the fail-closed adapter when a legacy producer leaves them absent.
    comparison_outcome: object = None
    artifact_generation: object = None
    attempt_state: object = None

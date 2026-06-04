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


class Events:
    """Callbacks the engine uses to report progress and check for control input.

    on_log:       human-readable status line (console prints it; GUI appends it
                  to a log pane).
    on_route:     per-route outcome; status is one of
                  {"saved", "empty", "skipped", "failed", "exists"}.
    should_skip:  return True to skip the route currently being waited on.
    is_cancelled: return True to stop the whole run before the next route.

    All default to harmless no-ops, so Events() is a valid silent sink.
    """

    def __init__(self, on_log=None, on_route=None, should_skip=None, is_cancelled=None):
        self.on_log = on_log or _noop_log
        self.on_route = on_route or _noop_route
        self.should_skip = should_skip or _never
        self.is_cancelled = is_cancelled or _never


@dataclass
class RunResult:
    """Outcome of one export run."""
    saved: int = 0
    empty: List[str] = field(default_factory=list)
    user_skipped: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    output_dir: str = ""


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
    """
    status: str = "ok"
    message: str = ""
    output_path: str = ""
    summary_lines: List[str] = field(default_factory=list)

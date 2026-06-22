"""The orthogonal export/consolidation OUTCOME contract (R1-B01 / R1-D01).

Two independent axes, both PRODUCER-OWNED and never inferred from human-readable
``summary_lines``:

  completion -- did the work cover everything it should have?
    complete  -- full coverage; the artifact may be promoted / cached / compared
    partial   -- some routes/inputs failed or were skipped; usable but incomplete
    no_data   -- the source returned nothing for everything (not an error, not a
                 success): a signed-in env that yields no data for any route
    cancelled -- the user stopped it mid-run
    failed    -- could not produce a usable result (an exception, or every input
                 failed to parse)

  artifact -- what happened to the on-disk artifact THIS run?
    promoted           -- a COMPLETE refresh replaced the live store copy
    new_unpromoted     -- written directly to a dated run folder (no store gating)
    previous_preserved -- the prior live copy was KEPT (a partial/failed/cancelled
                          refresh did NOT clobber last-good)
    none               -- nothing was written

``RunResult`` / ``ConsolidateResult`` (events.py) carry these as additive string
fields; THIS module owns the vocabulary + the pure mapping from structured counts
to a ``completion``. Downstream gating -- promote (F1), cache/compare (F3), the
green completion card -- keys on these fields, never on text. events.py stays
dependency-free: it declares the fields; producers set them using these constants.
"""

# --- completion vocabulary --------------------------------------------------
COMPLETE = "complete"
PARTIAL = "partial"
NO_DATA = "no_data"
CANCELLED = "cancelled"
FAILED = "failed"
COMPLETIONS = frozenset({COMPLETE, PARTIAL, NO_DATA, CANCELLED, FAILED})

# --- artifact vocabulary ----------------------------------------------------
PROMOTED = "promoted"
NEW_UNPROMOTED = "new_unpromoted"
PREVIOUS_PRESERVED = "previous_preserved"
NONE = "none"
ARTIFACTS = frozenset({PROMOTED, NEW_UNPROMOTED, PREVIOUS_PRESERVED, NONE})


def export_completion(saved, exists, empty, skipped, failed, cancelled=False):
    """Map an export run's structured COUNTS to a ``completion`` (§C.1, Q1).

    Precedence: cancelled > (failed | skipped) -> partial > present -> complete >
    no_data. ``saved``/``exists`` mean a route file is present; ``empty`` is a
    valid per-route no-data; ``failed``/``skipped`` mean incomplete coverage. All
    arguments are integer counts. NEVER reads summary text."""
    if cancelled:
        return CANCELLED
    if failed or skipped:
        return PARTIAL
    if (saved + exists) > 0:
        return COMPLETE
    if empty > 0:
        return NO_DATA
    return NO_DATA                      # nothing at all -> nothing fresh to promote


def run_completion(result, cancelled=False):
    """``completion`` for a RunResult (counts read off the structured fields)."""
    return export_completion(
        result.saved, len(result.exists), len(result.empty),
        len(result.user_skipped), len(result.failed), cancelled=cancelled)


def reduce_completion(completions, cancelled=False, aborted=False):
    """Reduce several reports' PER-REPORT completions into one RUN-level completion
    (R1-B07 / P1-B04). A run is ``complete`` ONLY if every report is complete —
    never re-derived from summed counts, where one complete report's saved>0 would
    mask another report's no_data. ``cancelled`` (the run was stopped) and
    ``aborted`` (a multi-report run that did NOT finish every selected report, e.g.
    an exception after an earlier report) are never complete. A mix of complete +
    no_data is ``partial`` (some data, some none — not green)."""
    if cancelled:
        return CANCELLED
    comps = list(completions)
    if aborted:                                  # incomplete report coverage
        return FAILED if FAILED in comps else PARTIAL
    if not comps:
        return NO_DATA
    if all(c == COMPLETE for c in comps):
        return COMPLETE
    if any(c in (FAILED, PARTIAL) for c in comps):
        return PARTIAL
    if any(c == CANCELLED for c in comps):
        return CANCELLED
    if all(c == NO_DATA for c in comps):
        return NO_DATA
    return PARTIAL                               # mixed complete + no_data -> not green


def consolidate_completion(wrote, skipped_inputs, failed_inputs,
                           cancelled=False, errored=False):
    """``completion`` for a consolidation (§C.1, Q3, producer-owned).

    ``wrote`` = at least one input made it into the output; ``skipped_inputs`` /
    ``failed_inputs`` = inputs left out (no data / parse failure). ``errored`` (no
    usable output produced) -> failed; ``cancelled`` -> cancelled; some-in but
    some-left-out -> partial; everything in -> complete; nothing in and not an
    error -> no_data."""
    if cancelled:
        return CANCELLED
    if errored:
        return FAILED
    if not wrote:
        return NO_DATA
    if skipped_inputs or failed_inputs:
        return PARTIAL
    return COMPLETE


def consolidate_completion_of(result):
    """The producer-set ``completion`` of a ConsolidateResult, or a safe inference
    from its legacy ``status`` when a producer hasn't set it (intra-version
    back-compat): ok->complete, cancelled->cancelled, error->failed."""
    c = getattr(result, "completion", None)
    if c in COMPLETIONS:
        return c
    status = getattr(result, "status", "ok")
    if status == "cancelled":
        return CANCELLED
    if status == "error":
        return FAILED
    return COMPLETE


def promotable(completion):
    """Only a COMPLETE result may replace the live store copy / be cached as
    fresh (the F1 promote gate, the F3 cache gate)."""
    return completion == COMPLETE


def comparable(completion):
    """A consolidation may feed a comparison unless it failed or yielded no data
    (§C.1: failed/no_data -> do not compare; partial -> compare but flag)."""
    return completion not in (FAILED, NO_DATA, CANCELLED)


def artifact_after_store(completion, in_store):
    """The ``artifact`` outcome of an export run's store handling.

    ``in_store`` = an always-current destination (staging->live swap) is in play.
    A complete refresh promotes; anything else keeps the prior live copy
    (previous_preserved). Without a store, files are written directly to the dated
    run folder (new_unpromoted)."""
    if not in_store:
        return NEW_UNPROMOTED
    return PROMOTED if promotable(completion) else PREVIOUS_PRESERVED

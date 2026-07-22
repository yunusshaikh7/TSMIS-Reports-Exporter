"""What is TRUE about a comparison, for the evidence generator (208/209/108).

`published_comparison` decodes and authenticates the cells a comparison
PUBLISHED. This module is the layer above it: it accounts for that published
universe in full, and decides which proposed examples may be illustrated.

The split is the point. `visual_evidence` locates rows in PDFs, rasterizes them
and publishes an artifact set — none of which should be able to decide what a
comparison found. Truth comes from the published cells (CMP-AUD-208), it is
accounted for before any sample is drawn (CMP-AUD-209), and a difference that
cannot be photographed unambiguously is NAMED rather than dropped
(CMP-AUD-108).

Console-free; the caller owns the `Events` sink.
"""
import logging
from collections import Counter

import published_comparison

log = logging.getLogger("tsmis.evidence")


def published_universe(comparison_path, adapter, events):
    """Read the comparison that was PUBLISHED and account for all of it.

    Returns ``(published, ledger, digest, fields_with_differences)``. The
    differences come from the committed workbook's own cells — per-column state
    masks and anchored counts — not from a second execution of the loaders that
    produced them (CMP-AUD-208). The ledger is complete and hash-bound BEFORE
    any sample is drawn (CMP-AUD-209). A column whose differences all live
    inside duplicate groups is still a differing column, and only the published
    counts decide that (CMP-AUD-108).
    """
    published = published_comparison.read(comparison_path,
                                          is_cancelled=events.is_cancelled)
    published.require_fields(adapter.FIELDS)
    ledger = published.ledger()
    events.on_log(
        f"  evidence: published comparison — {ledger.difference_cells:,} "
        f"counted difference(s) across {len(ledger.fields_with_differences())} "
        f"column(s), {ledger.one_sided_rows:,} one-sided row(s), "
        f"{ledger.duplicate_groups:,} repeated-key group(s)")
    fields = [f for f in adapter.FIELDS if ledger.differences(f)]
    return published, ledger, ledger.digest(), fields


# --------------------------------------------------------------------------- #
# reconciliation: an adapter PROPOSES a row; the published cell decides
# --------------------------------------------------------------------------- #
REJECT_NO_ROW = "no published row carries that identity"
REJECT_NOT_SOLO = "the published row shares its key with another row"
REJECT_NOT_COUNTED = "the published cell is not a counted difference"
REJECT_TEXT = "the re-parsed value disagrees with the published cell"


def reconcile(published, diffs):
    """Bind every proposed candidate to the cell the comparison PUBLISHED.

    A second execution of the product loaders is no longer evidence on its own
    (CMP-AUD-208): it may only PROPOSE a row to photograph. The published
    generation decides whether that photograph may be taken — one row at that
    identity, state ``D`` at that column, and published text equal to the
    engine's own composition of the two values. Returns
    ``({field: [candidate]}, {field: Counter(reason)})``.
    """
    kept, rejects = {}, {}
    for field, examples in diffs.items():
        try:
            position = published.position_of(field)
        except published_comparison.PublishedComparisonError:
            rejects[field] = Counter({REJECT_NO_ROW: len(examples)})
            continue
        good, why = [], Counter()
        for ex in examples:
            row = published.row_at(ex["route"], ex.get("pub_key"), 1)
            if row is None:
                why[REJECT_NO_ROW] += 1
            elif not published.is_solo(row):
                why[REJECT_NOT_SOLO] += 1
            elif row.state(position) != published_comparison.STATE_DIFFERENT:
                why[REJECT_NOT_COUNTED] += 1
            elif row.value(position) != ex.get("display"):
                why[REJECT_TEXT] += 1
            else:
                good.append({**ex, "published_row": row.excel_row,
                             "published_occurrence": row.occurrence,
                             "published_state": row.state(position),
                             "published_token": row.token})
        if good:
            kept[field] = good
        if why:
            rejects[field] = why
    return kept, rejects


def unrenderable_reason(entry, rejected):
    """Why a column with published differences has NO candidate to sample.

    CMP-AUD-108: a difference that exists only inside a duplicate group is a
    NAMED per-column miss, never a silent zero.
    """
    if entry is not None and entry.differences and not entry.solo_differences:
        return (f"all {entry.differences:,} published difference(s) sit in "
                "repeated-key groups — the comparison pairs them by identity, "
                "but no single row can be photographed unambiguously")
    if rejected:
        detail = ", ".join(f"{why} ({n:,})"
                           for why, n in rejected.most_common(3))
        return f"the published comparison refused every candidate — {detail}"
    return None


def attach_source_rows(published, entries):
    """Name each rendered item's two PERSISTED source rows (CMP-AUD-208).

    Resolved through the comparison's own opaque row token, the same handle
    Spot Check MATCHes into each side's literal key-helper column — never
    Comparison's hyperlinks, which carry no cached value in a values workbook.
    """
    tokens = [e.get("published_token") for e in entries]
    try:
        resolved = published.source_rows(tokens)
    except published_comparison.PublishedComparisonError as e:
        log.warning("evidence: source rows unresolved (%s: %s)",
                    type(e).__name__, e)
        return
    for entry in entries:
        found = resolved.get(entry.get("published_token")) or {}
        entry["source_rows"] = tuple(
            (side, found.get(side)) for side in published.side_labels)


def ledger_rows(ledger, adapter_fields, sampled):
    """The exhaustive per-column accounting written beside the images."""
    rows = []
    for name in adapter_fields:
        entry = ledger.for_field(name)
        if entry is None:
            continue
        rows.append((name, entry.differences, entry.solo_differences,
                     entry.duplicate_differences, entry.context_cells,
                     entry.equal_cells, entry.one_sided_cells,
                     sampled.get(name, 0)))
    return rows

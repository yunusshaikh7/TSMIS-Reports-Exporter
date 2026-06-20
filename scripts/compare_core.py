"""The shared discrepancy-workbook engine behind every comparison type.

Extracted (v0.10.0) from compare_highway_log.py — the approved TSMIS-vs-TSN
Highway Log workbook — and parameterized with a CompareSchema so the SAME
proven engine also builds the cross-environment comparisons (e.g. SSOR-prod
vs ARS-prod) for any report whose rows are "one key column + N data fields".
compare_highway_log delegates here with its original schema; its output is
regression-verified cell-for-cell identical to the pre-extraction engine, so
DO NOT change formula or label text here without re-running that check
(see CLAUDE.md — the per-route format is locked to the approved sample).

What the engine builds (sheet for sheet, same as the approved design):
  Summary       row counts, match status, per-field diff counts, live
                SELF-CHECK rows, notes
  Spot Check    one row audited field-by-field with an independent verdict
  Comparison    one row per (Route,) key + occurrence, document order;
                matched values shown, differences as "a ≠ b" in red
  Only in <A> / Only in <B>   every one-sided row, pulled onto its own tab
  Routes        (consolidated shape only) per-route coverage stats
  <A> / <B>     the two inputs + live "Key (helper)" lookup columns

Two flavors via mode= ("formulas" | "values" | "both"): formulas = every
cell a live Excel formula (consolidated ships calcMode=manual — ~2M formulas);
values = the same sheets/links/colors with the bulk precomputed by the same
Python mirror that powers the run summary, so the flavors can never disagree.

Inputs arrive as ROWS (the callers own file loading/validation): per-route
shape = [key, f1..fn]; consolidated shape = [route, key, f1..fn].

Streaming (write_only) workbook rules apply throughout: sheets created in
display order, freeze/widths/filter/CF set before rows, styled cells are
WriteOnlyCells. Console-free; progress via events.on_log, cancel honored at
the usual cadence, ConsolidateResult returned.
"""
import difflib
import itertools
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.comments import Comment
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

# Tint for a dittoed roadbed cell on the data sheets (a soft lavender, distinct
# from the diff/one-sided fills); only applied when a schema supplies a
# ditto_resolver (Highway Log), so other comparisons' data sheets are unchanged.
_DITTO_FILL = "E4DFEC"

from events import ConsolidateResult, Events

# Styling shared by all sheets (colors taken from the approved sample; the
# Only-in tab colors echo the Comparison sheet's yellow/blue row tints).
_DARK = "1F3864"            # header band / banners
_TAB_COLORS = {"summary": "808080", "spot": "7030A0", "comparison": "C00000",
               "routes": "ED7D31", "only_a": "BF8F00", "only_b": "2E75B6",
               "side_a": "4472C4", "side_b": "70AD47"}
_DIFF_MARK = " ≠ "          # appears ONLY in differing cells; counts key on it

_PROGRESS_EVERY = 10_000    # log + cancel-check cadence on big workbooks

XL_MAX_ROWS, XL_MAX_COLS = 1_048_576, 16_384   # Excel worksheet hard limits


def excel_limit_error(n_rows, n_cols):
    """A user-safe message when a workbook would exceed Excel's worksheet
    limits, else None. Checked before writing so a too-large comparison fails
    cleanly instead of openpyxl raising mid-write (row cap) or silently
    dropping columns (column cap)."""
    if n_rows > XL_MAX_ROWS:
        return (f"This comparison needs {n_rows:,} rows, past Excel's "
                f"{XL_MAX_ROWS:,}-row limit. Compare a smaller scope (e.g. "
                "per-route files, or one report at a time).")
    if n_cols > XL_MAX_COLS:
        return (f"This report has {n_cols:,} columns, past Excel's "
                f"{XL_MAX_COLS:,}-column limit.")
    return None


@dataclass
class CompareSchema:
    """Everything report-specific the engine needs.

    The defaults reproduce the approved TSMIS-vs-TSN Highway Log wording —
    new comparison types override the data-shape fields and the side names.
    """
    report_name: str                  # "Highway Log" — titles/messages
    header: list                      # per-route columns: [key, f1..fn]
    side_a: str = "TSMIS"             # side A sheet/tab name (also in formulas)
    side_b: str = "TSN"               # side B sheet/tab name
    # The row-identity noun used in labels ("location" for the Highway Log,
    # "row" for generic reports, "route" for the Ramp Summary).
    id_noun: str = "location"
    id_noun_plural: str = "locations"
    pair_noun: str = ""               # the duplicate-key example noun in the
                                      # pairing note ("postmile"); "" = id_noun
    sides_noun: str = "systems"       # "both systems" / "both environments"
    medwid_fields: tuple = ()         # field NAMES normalized like Med Wid
    date_fields: tuple = ()           # field NAMES date-formatted on Spot Check
    data_widths: dict = field(default_factory=dict)   # field name -> data-sheet width
    cmp_widths: dict = field(default_factory=dict)    # field name -> comparison width
    scope_flat: str = "Per-route"     # Summary scope label, per-route shape
    scope_consolidated: str = "Consolidated (all routes)"
    one_sided_note_extra: str = ""    # appended to the yellow/blue note
    trim_note_extra: str = ""         # appended to the TRIM note
    # Which header column is the row-identity key (rows align/pair on it).
    # Default 0 = the first column, the original behavior. Reports whose first
    # column is coarse (e.g. cross-env Highway Sequence inherits County, which
    # repeats for hundreds of rows) point this at a granular column (postmile)
    # so rows align by identity instead of positionally within the coarse
    # group. The column stays in its display position everywhere — only the
    # identity used for alignment + the Comparison sheet's lead column change.
    key_field: int = 0
    # Optional per-report decoration (default None = the byte-identical original
    # output; only the Highway Log comparisons set these, so other comparisons
    # and the regression-locked fixtures are unchanged):
    #   header_comment — callable(label) -> openpyxl Comment | None, attached as a
    #     hover tooltip to each column-label header cell (Comparison / Only-in /
    #     data sheets).
    #   legend_writer  — callable(wb) run after the sheets, before save (e.g. to
    #     append a column-Legend sheet).
    header_comment: object = None
    legend_writer: object = None
    # When True, a cell whose value is a "+"-run ditto marker ('+', '++', '+++')
    # is NON-ASSERTING: it never counts as a difference against the other side
    # (its real value is compared on the paired roadbed's own row). Only the
    # Highway Log comparisons set this; for every other comparison it is False,
    # so the equality formula, the Spot Check verdict, and the Python mirrors are
    # byte-identical to the regression-locked output. See
    # docs/highway_log/comparison-study.md and highway_log_columns.is_ditto.
    ditto_nonasserting: bool = False
    # Optional DISPLAY-only resolver: callable(rows, has_route) ->
    # {row_index: {col_in_row: resolved_value}} for each dittoed cell. When set
    # (Highway Log), the data sheets keep the raw ditto in the cell (the
    # non-asserting diff depends on detecting the '+'-run) but tint it and attach
    # a comment with the paired-roadbed value, so a reviewer sees what each
    # `+`/`++` resolved to. None for every other comparison -> data sheets stay
    # byte-identical.
    ditto_resolver: object = None
    # Optional KEY normalizer: callable(row, off, key_field) -> str, the canonical
    # identity token used for matching/alignment IN PLACE OF the raw key-column
    # value. When None (every comparison except TSMIS-vs-TSN Highway Log), the raw
    # key-column string is used exactly as before, so the union, helper keys, and
    # MATCH lookups are byte-identical and the regression lock holds. The Highway
    # Log TSMIS-vs-TSN schemas set it to highway_log_columns.roadbed_canonical_
    # location so a divided segment's roadbed row keys identically whether the
    # source suffixes the Location (PDF/Excel) or dittos a block (TSN). The DATA
    # sheets still show each source's raw Location; only the key token is unified.
    key_normalizer: object = None
    # Optional CONTEXT fields: field NAMES that are SHOWN but never asserted on —
    # they never count as a difference and never get the ≠ mark / diff highlight.
    # Used for columns that exist on only one side (e.g. the TSN Ramp Detail DB
    # columns ADT / Ramp Type that the TSMIS report has no counterpart for): the
    # comparison still displays the value (coalescing the non-blank side) so a
    # reviewer sees it, but it contributes zero diff cells. Default () -> is_context
    # is always False, so every existing comparison (and the regression-locked
    # Route-1=969 Highway Log canary) is byte-identical.
    context_fields: tuple = ()
    # Optional EXTRA sheet writer: callable(wb, ctx) run after the standard sheets,
    # before save — like legend_writer but with a context dict ({rows_a, rows_b,
    # has_route, sc, side_a, side_b}) so a report can append a FAMILIAR-LAYOUT sheet
    # (e.g. the Ramp Summary category-count rollup) rendered from the compared rows.
    # Default None -> no extra sheet, byte-identical to before.
    extra_sheet_writer: object = None

    @property
    def n_fields(self):
        return len(self.header) - 1

    @property
    def field_indices(self):
        """Header indices shown as data fields — every column except the key,
        in display order. key_field == 0 gives [1, 2, …, n] (the original
        behavior, so the default path is byte-identical)."""
        return [i for i in range(len(self.header)) if i != self.key_field]

    def is_medwid(self, field_idx):
        return self.header[field_idx] in self.medwid_fields

    def is_context(self, field_idx):
        """True for a non-asserting CONTEXT field (shown, never counted as a diff)."""
        return self.header[field_idx] in self.context_fields

    def sheet_names(self, has_route):
        names = ["Summary", "Spot Check", "Comparison"]
        if has_route:
            names.append("Routes")
        names += [f"Only in {self.side_a}", f"Only in {self.side_b}",
                  self.side_a, self.side_b]
        return names


def _sref(name):
    """`name` as an Excel formula sheet reference: bare when it's a plain
    identifier (keeps TSMIS/TSN formulas byte-identical to the approved
    sample), quoted otherwise ('SSOR-PROD', 'Only in TSMIS')."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) \
            and not re.fullmatch(r"[A-Za-z]{1,3}\d{1,7}", name):
        return name
    return "'" + name.replace("'", "''") + "'"


# =============================================================================
# Keys + union (document-order diff merge)
# =============================================================================

def keys_for(rows, has_route, key_field=0, key_normalizer=None):
    """[(route, key, occurrence), ...] in file order (route "" for the
    per-route shape). Occurrence repeats of the same (route, key) are
    numbered 1.., exactly like the sheets' live helper column.

    `key_field` picks WHICH header column is the identity key (default 0 = the
    first column, the original behavior). The raw row carries a leading Route
    when has_route, so the key sits at r[(1 if has_route else 0) + key_field].

    `key_normalizer` (opt-in; None = byte-identical original behavior) is a
    callable(row, off, key_field) -> str returning the canonical identity token
    used IN PLACE OF the raw key-column string (the Highway Log roadbed key)."""
    seen = {}
    out = []
    off = 1 if has_route else 0
    koff = off + key_field
    for r in rows:
        route = "" if not has_route or r[0] is None else str(r[0])
        if key_normalizer is not None:
            loc = key_normalizer(r, off, key_field)
        else:
            loc = "" if r[koff] is None else str(r[koff])
        k = (route, loc)
        seen[k] = seen.get(k, 0) + 1
        out.append((route, loc, seen[k]))
    return out


def union_keys(keys_t, keys_n):
    """The union of the two key sequences in DOCUMENT order, grouped by route:
    side A's routes in side-A order (B-only routes appended in B order),
    and within each route a diff-style alignment of the two row sequences.

    Common keys appear exactly once (first position wins — a key can fall
    outside the aligner's 'equal' blocks when one file lists it out of
    sequence; seen in the field: TSMIS printed 059.739 after 059.759 while
    TSN kept it in order). The Excel MATCH lookups pair each union row with
    both files regardless of where it sits. Aligning per route keeps the
    matcher fast on consolidated inputs (50k+ rows)."""
    by_route_t, by_route_n = {}, {}
    for k in keys_t:
        by_route_t.setdefault(k[0], []).append(k)
    for k in keys_n:
        by_route_n.setdefault(k[0], []).append(k)

    out = []
    seen = set()

    def emit(keys):
        for k in keys:
            if k not in seen:
                seen.add(k)
                out.append(k)

    routes = list(by_route_t) + [r for r in by_route_n if r not in by_route_t]
    for route in routes:
        seq_t = by_route_t.get(route, [])
        seq_n = by_route_n.get(route, [])
        if not seq_t or not seq_n:
            emit(seq_t or seq_n)
            continue
        sm = difflib.SequenceMatcher(None, seq_t, seq_n, autojunk=False)
        for op, a0, a1, b0, b1 in sm.get_opcodes():
            if op == "equal" or op == "delete":
                emit(seq_t[a0:a1])
            elif op == "insert":
                emit(seq_n[b0:b1])
            else:                       # replace: side-A block, then side-B block
                emit(seq_t[a0:a1])
                emit(seq_n[b0:b1])
    return out


# =============================================================================
# Python mirror of the workbook's comparison semantics (for the run summary;
# the formulas workbook recomputes everything live)
# =============================================================================

def normalize_value(v):
    """Canonicalize a freshly-LOADED cell so the comparison is type-stable and
    the two output flavors can't disagree. A real date/datetime is rendered to a
    fixed ISO string: Excel's TRIM of a live date is locale/number-format
    dependent and would diverge from Python's str(datetime) (e.g. "2/25/1976"
    vs "1976-02-25 00:00:00"), so the formulas flavor and the values flavor
    would compute different results for the SAME cell. Stringifying at load time
    means the engine only ever sees text — both flavors agree, and a date that
    is genuinely equal on both sides compares equal. Everything else (numbers,
    text) is returned unchanged. Callers (the loaders) apply this per cell."""
    if isinstance(v, datetime):
        if (v.hour, v.minute, v.second, v.microsecond) == (0, 0, 0, 0):
            return v.date().isoformat()
        return v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, time):       # a time-only cell would otherwise reach the
        return v.isoformat()      # data sheet typed (Excel) vs str() (values)
    return v


def _xl_trim(v):
    """Excel TRIM: text form, edge spaces stripped, internal runs collapsed."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(" +", " ", str(v)).strip(" ")


def _is_plus_run(v):
    """True if `v` is a Highway Log ditto marker — a non-empty run of only '+'
    ('+', '++', '+++'). Mirrors highway_log_columns.is_ditto, kept local so the
    generic engine carries no Highway-Log import; gated by
    CompareSchema.ditto_nonasserting so it is inert for every other comparison."""
    if v is None:
        return False
    s = str(v).strip()
    return bool(s) and set(s) == {"+"}


def _medwid_norm(t):
    """Mirror the Med Wid formula: VALUE() the whole code, else VALUE() all but
    the last character and keep that suffix, else the raw text — so '0Z',
    '00Z' and '06V'/'6V' compare as equals."""
    def num(s):
        if re.fullmatch(r"\d+(\.\d+)?", s):
            f = float(s)
            return str(int(f)) if f.is_integer() else str(f)
        return None
    n = num(t)
    if n is not None:
        return n
    if t:
        n = num(t[:-1])
        if n is not None:
            return n + t[-1]
    return t


# =============================================================================
# Similarity pairing for duplicate keys
# =============================================================================
# Rows that share a key (same Route + key field) used to pair by FILE ORDER:
# first-with-first, second-with-second. When a key legitimately repeats (two
# segments at the same postmile), that mis-paired a row with the wrong twin and
# reported phantom differences — the row that actually matched the OTHER side's
# second instance looked like a difference. Instead, within each duplicate group
# present on BOTH sides, pair the rows that are actually the MOST ALIKE (fewest
# differing fields) and give matched pairs the same occurrence #. The optimal
# assignment's total difference count is <= any positional assignment's (file
# order is just one assignment), so this can only REMOVE phantom diffs, never add
# one.

_PAIR_GROUP_CAP = 100_000     # product len_t*len_n above which we keep file order
_PAIR_EXACT_PERMS = 5040      # exact (brute-force) assignment up to 7! permutations


def _row_diff_count(sc, rt, rn, off):
    """Differing compared-fields between two rows, using the comparison's own
    normalization (TRIM + Med Wid) — identical to the per-row diff the workbook
    counts. This is the similarity cost: lower = more alike."""
    d = 0
    for f in sc.field_indices:
        if sc.is_context(f):
            continue                     # context = non-asserting (never a diff)
        va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
        if sc.ditto_nonasserting and (_is_plus_run(va) or _is_plus_run(vb)):
            continue                     # ditto = non-asserting
        if sc.is_medwid(f):
            va, vb = _medwid_norm(va), _medwid_norm(vb)
        if va != vb:
            d += 1
    return d


def _min_cost_pairs(cost):
    """Min-total-cost 1:1 assignment over a (rows x cols) cost matrix, returning
    min(rows, cols) (row, col) pairs (every member of the smaller side matched).
    Exact for small groups (the realistic case — a key repeats a handful of
    times) via permutation search with pruning; a greedy fallback bounds the rare
    pathological pile. Lexicographic search means the positional assignment is
    tried first, so ties keep file order — deterministic, and both output flavors
    plus the golden checks agree."""
    nr = len(cost)
    nc = len(cost[0]) if nr else 0
    if nr == 0 or nc == 0:
        return []
    flip = nr > nc                          # work with rows = the smaller side
    if flip:
        cost = [[cost[r][c] for r in range(nr)] for c in range(nc)]
        nr, nc = nc, nr
    if math.perm(nc, nr) <= _PAIR_EXACT_PERMS:
        best_total, best = None, None
        for perm in itertools.permutations(range(nc), nr):
            total = 0
            for r in range(nr):
                total += cost[r][perm[r]]
                if best_total is not None and total >= best_total:
                    break                   # prune: non-negative costs only grow
            else:
                best_total, best = total, [(r, perm[r]) for r in range(nr)]
        pairs = best or []                  # defensive: there is always >=1 perm
    else:                                   # greedy: lowest-cost pair first
        order = sorted((cost[r][c], r, c) for r in range(nr) for c in range(nc))
        used_r, used_c, pairs = set(), set(), []
        for _, r, c in order:
            if r in used_r or c in used_c:
                continue
            used_r.add(r); used_c.add(c); pairs.append((r, c))
            if len(pairs) == nr:
                break
    return [(c, r) for (r, c) in pairs] if flip else pairs


def pair_occurrences_by_similarity(sc, rows_t, rows_n, keys_t, keys_n,
                                   has_route, events=None):
    """Re-number the occurrence component of DUPLICATE keys so that, within each
    (route, key) group present on BOTH sides, rows pair by data SIMILARITY (the
    most-alike rows share an occurrence #) instead of by file order. Matched
    pairs are numbered 1.. in side-A file order; the larger side's leftovers get
    higher, side-unique occurrence numbers (so they stay one-sided). Groups with
    no duplicate, or a key on only one side, are untouched (occurrence # = file
    order, exactly as before). Returns new (keys_t, keys_n)."""
    off = 1 if has_route else 0
    grp_t, grp_n = {}, {}
    for i, k in enumerate(keys_t):
        grp_t.setdefault((k[0], k[1]), []).append(i)
    for i, k in enumerate(keys_n):
        grp_n.setdefault((k[0], k[1]), []).append(i)

    out_t, out_n = list(keys_t), list(keys_n)
    capped = 0
    for grp, tis in grp_t.items():
        nis = grp_n.get(grp)
        if not nis or (len(tis) == 1 and len(nis) == 1):
            continue                        # key on one side only, or no duplicate
        if len(tis) * len(nis) > _PAIR_GROUP_CAP:
            capped += 1                     # absurd pile — keep file order
            continue
        cost = [[_row_diff_count(sc, rows_t[ti], rows_n[ni], off) for ni in nis]
                for ti in tis]
        pairs = _min_cost_pairs(cost)       # (a, b) indices into tis / nis
        route, loc = grp
        matched_t = {a for a, _ in pairs}
        matched_n = {b for _, b in pairs}
        occ = 0
        for a, b in sorted(pairs, key=lambda ab: tis[ab[0]]):   # side-A file order
            occ += 1
            out_t[tis[a]] = (route, loc, occ)
            out_n[nis[b]] = (route, loc, occ)
        extra = occ
        for a in range(len(tis)):           # unmatched side-A rows, file order
            if a not in matched_t:
                extra += 1
                out_t[tis[a]] = (route, loc, extra)
        extra = occ
        for b in range(len(nis)):           # unmatched side-B rows, file order
            if b not in matched_n:
                extra += 1
                out_n[nis[b]] = (route, loc, extra)
    if capped and events is not None:
        events.on_log(f"  Note: {capped} key group(s) repeat too many times to "
                      "similarity-pair; kept file order for those.")
    return out_t, out_n


def count_diffs(sc, rows_t, rows_n, keys_t, keys_n, union, has_route):
    """Counts matching what the workbook's formulas will compute: overall
    totals, per-field difference counts, per-route aggregates (consolidated),
    and the FIRST matched-with-differences Comparison row (the Spot Check
    sheet's default). The same numbers back the run summary AND become the
    literal cells of the values workbook, so the two output flavors can
    never disagree."""
    off = 1 if has_route else 0          # data fields start after Route
    by_t = {k: rows_t[i] for i, k in enumerate(keys_t)}
    by_n = {k: rows_n[i] for i, k in enumerate(keys_n)}
    both = t_only = n_only = diff_rows = identical = diff_cells = 0
    first_diff_row = None
    field_diffs = {f: 0 for f in sc.field_indices}
    route = {}                           # consolidated: per-route aggregates

    def rstat(rid):
        return route.setdefault(rid, {"t_rows": 0, "n_rows": 0, "locs": 0,
                                      "matched": 0, "withdiffs": 0, "cells": 0})
    if has_route:
        for k in keys_t:
            rstat(k[0])["t_rows"] += 1
        for k in keys_n:
            rstat(k[0])["n_rows"] += 1
    for i, k in enumerate(union):
        rt, rn = by_t.get(k), by_n.get(k)
        rs = rstat(k[0]) if has_route else None
        if rs is not None:
            rs["locs"] += 1
        if rt is None:
            n_only += 1
            continue
        if rn is None:
            t_only += 1
            continue
        both += 1
        if rs is not None:
            rs["matched"] += 1
        row_diffs = 0
        for f in sc.field_indices:                # every column but the key
            if sc.is_context(f):
                continue                          # context = non-asserting (never a diff)
            va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
            if sc.ditto_nonasserting and (_is_plus_run(va) or _is_plus_run(vb)):
                continue                          # ditto = non-asserting
            if sc.is_medwid(f):
                va, vb = _medwid_norm(va), _medwid_norm(vb)
            if va != vb:
                row_diffs += 1
                field_diffs[f] += 1
        diff_cells += row_diffs
        if rs is not None:
            rs["cells"] += row_diffs
            if row_diffs:
                rs["withdiffs"] += 1
        if row_diffs:
            diff_rows += 1
            if first_diff_row is None:
                first_diff_row = i + 2
        else:
            identical += 1
    return {"both": both, "t_only": t_only, "n_only": n_only,
            "diff_rows": diff_rows, "identical": identical,
            "diff_cells": diff_cells, "first_diff_row": first_diff_row,
            "field_diffs": field_diffs, "route": route}


# =============================================================================
# Layout: column geometry for the two input shapes
# =============================================================================

class _Layout:
    """Column letters for both workbook shapes.

    per-route:    data sheets  Comparison row=A (back-link), key=B,
                  fields C.., key helper at the end
    consolidated: data sheets  Comparison row=A (back-link), Route=B,
                  key=C, fields D.., key helper at the end
    """

    def __init__(self, sc, has_route):
        self.sc = sc
        self.has_route = has_route
        self.off = 1 if has_route else 0
        self.n_fields = sc.n_fields
        # The identity key column (header index) + the fields shown on the
        # Comparison sheet (every other column, in display order). key_field
        # == 0 reproduces the original [1..n] field order exactly.
        self.key_field = sc.key_field
        self.field_indices = sc.field_indices
        self._field_pos = {f: pos for pos, f in enumerate(self.field_indices)}
        # statuses as they appear in cells/formulas/CF
        self.only_a = f"{sc.side_a} only"
        self.only_b = f"{sc.side_b} only"
        # data sheets: a leading "Comparison row" back-link column, then the
        # input's columns (ALL of them, in their original order — the key
        # column stays in place there), then the live key helper
        self.data_header = (["Route"] if has_route else []) + list(sc.header)
        self.back_col = "A"                                  # back-link column
        self.route_data_col = "B" if has_route else None     # Route on data sheets
        self.key_col = get_column_letter(len(self.data_header) + 2)
        self.data_last_col = get_column_letter(len(self.data_header) + 1)
        # comparison sheet: the key column leads (pulled to the identity slot),
        # the remaining columns follow as fields in display order
        self.id_headers = ((["Route"] if has_route else [])
                           + [sc.header[self.key_field], "#", f"{sc.side_a} Row",
                              f"{sc.side_b} Row", "Status", "Diffs"])
        self.f0 = len(self.id_headers) + 1            # first field column index
        self.first_field_col = get_column_letter(self.f0)
        self.last_field_col = get_column_letter(self.f0 + self.n_fields - 1)
        c = [get_column_letter(i + 1) for i in range(len(self.id_headers))]
        if has_route:
            (self.c_route, self.c_loc, self.c_occ, self.c_trow, self.c_nrow,
             self.c_status, self.c_diffs) = c
        else:
            self.c_route = None
            (self.c_loc, self.c_occ, self.c_trow, self.c_nrow,
             self.c_status, self.c_diffs) = c

    def data_col(self, field_idx):
        """Data-sheet column letter for header[field_idx] (the data sheets
        carry a leading "Comparison row" link column)."""
        return get_column_letter(field_idx + 2 + self.off)

    def field_pos(self, field_idx):
        """0-based position of header[field_idx] among the displayed fields."""
        return self._field_pos[field_idx]

    def field_col(self, field_idx):
        """Comparison-sheet column letter for header[field_idx]."""
        return get_column_letter(self.f0 + self._field_pos[field_idx])

    def key_expr(self, r):
        """The lookup key for Comparison row r (matches the helper column)."""
        if self.has_route:
            return f"${self.c_route}{r}&\"|\"&${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"
        return f"${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"



# =============================================================================
# Workbook writing
# =============================================================================

def _trim_ref(sheet, col, row_ref):
    return f'TRIM(INDEX({_sref(sheet)}!{col}:{col},{row_ref}))'


def _row_link(side, key, lay):
    """The '<side> Row' cell: the matched data-sheet row number as a CLICKABLE
    link, so a doubter can eyeball the source values instead of trusting the
    lookup. The link targets the ENTIRE ROW ("57:57"), so Excel selects the
    whole row on arrival — a temporary highlight that clears on the next
    click — while the view stays at the frozen left columns.
    (A bounded range like A57:AH57 made Excel scroll to the range's RIGHT
    edge when it didn't fit the window — measured via COM on real Excel;
    row-only references keep scrollColumn at home.) HYPERLINK's friendly
    value is the MATCH number itself, so the cell still counts as a number
    (the Summary SELF-CHECK relies on COUNT) — the MATCH is computed three
    times (range start, range end, display)."""
    s = _sref(side)
    m = f'MATCH({key},{s}!${lay.key_col}:${lay.key_col},0)'
    return f'=IFERROR(HYPERLINK("#{s}!"&{m}&":"&{m},{m}),"")'


def _row_link_value(side, row_num, lay):
    """_row_link with the row number known at build time (values workbook):
    same whole-row jump-and-select, no MATCH."""
    return f'=HYPERLINK("#{_sref(side)}!{row_num}:{row_num}",{row_num})'


def _link_font():
    return Font(name="Arial", size=10, color="0563C1", underline="single")


def _medwid_ref(sheet, col, row_ref):
    """The zero-padding-normalized form of a Med Wid cell (see _medwid_norm)."""
    t = _trim_ref(sheet, col, row_ref)
    return (f'IFERROR(VALUE({t})&"",'
            f'IFERROR(VALUE(LEFT({t},LEN({t})-1))&RIGHT({t},1),{t}))')


def _isditto_xl(trim_ref):
    """Excel expression: TRUE when an already-TRIM'd cell ref is a ditto marker
    (non-empty and only '+' characters) — the formula twin of _is_plus_run."""
    return f'AND({trim_ref}<>"",SUBSTITUTE({trim_ref},"+","")="")'


def _eq_with_ditto(sc, eq, trim_t, trim_n):
    """Wrap an equality expression so a ditto on EITHER side counts as equal
    (non-asserting), when the schema enables it. Otherwise returns `eq`
    unchanged, so non-Highway-Log comparisons stay byte-identical."""
    if sc.ditto_nonasserting:
        return f'OR({_isditto_xl(trim_t)},{_isditto_xl(trim_n)},{eq})'
    return eq


def _field_formula(lay, r, field_idx):
    """Comparison cell formula for data field `field_idx` (1-based into the
    header) on Comparison row `r`: the matched value when the two systems
    agree, 'a ≠ b' when they differ, and on single-side rows (tinted
    yellow/blue) that system's own value, so the row's data is still readable
    instead of blank. Excel's IF evaluates only the taken branch, so the
    absent side's INDEX (whose row ref is "") is never computed on
    single-side rows."""
    sc = lay.sc
    col = lay.data_col(field_idx)
    ct, cs = f"${lay.c_trow}{r}", f"${lay.c_nrow}{r}"
    t, n = _trim_ref(sc.side_a, col, ct), _trim_ref(sc.side_b, col, cs)
    if sc.is_context(field_idx):
        # Context field: non-asserting — never a ≠. Show whichever side has a value
        # (coalesce A→B), and on a one-sided row that side's own value.
        st = f"${lay.c_status}{r}"
        coalesce = f'IF({t}="",{n},{t})'
        return (f'=IF({st}="{lay.only_a}",{t},IF({st}="{lay.only_b}",{n},{coalesce}))')
    if sc.is_medwid(field_idx):
        eq = f'{_medwid_ref(sc.side_a, col, ct)}={_medwid_ref(sc.side_b, col, cs)}'
    else:
        eq = f"{t}={n}"
    eq = _eq_with_ditto(sc, eq, t, n)        # ditto = non-asserting (HL only)
    show_t = f'IF({t}="","(blank)",{t})'
    show_n = f'IF({n}="","(blank)",{n})'
    st = f"${lay.c_status}{r}"
    return (f'=IF({st}="{lay.only_a}",{t},IF({st}="{lay.only_b}",{n},IF({eq},{t},'
            f'{show_t}&"{_DIFF_MARK}"&{show_n})))')


def _field_value(sc, rt, rn, off, f):
    """What _field_formula DISPLAYS, computed in Python — the values
    workbook's cell for header[f]. `rt`/`rn` are the raw input rows
    (None when that side lacks the key); returns "" for an empty result."""
    if rt is None:                       # B-only row: that side's own value
        return _xl_trim(rn[f + off])
    if rn is None:                       # A-only row
        return _xl_trim(rt[f + off])
    va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
    if sc.is_context(f):
        return va if va else vb          # context = non-asserting: coalesce, never ≠
    if sc.ditto_nonasserting and (_is_plus_run(va) or _is_plus_run(vb)):
        return va                        # ditto = non-asserting: show side A's value
    ca, cb = va, vb
    if sc.is_medwid(f):
        ca, cb = _medwid_norm(va), _medwid_norm(vb)
    if ca == cb:
        return va
    return f"{va or '(blank)'}{_DIFF_MARK}{vb or '(blank)'}"


# The workbook is written in openpyxl's STREAMING (write_only) mode: the
# consolidated comparison carries ~2 million formula cells, which the normal
# in-memory mode cannot save in reasonable time or RAM (the consolidators use
# the same mode for the same reason). Streaming rules: sheets are created in
# display order, freeze/widths/filter/CF are set before rows are appended,
# and styled cells are WriteOnlyCells.

# Spreadsheet formula-injection guard. A free-text value beginning with one of
# these would be interpreted by Excel as a formula (the classic CSV/XLSX
# injection vector — a malicious Description like "=cmd|'/C calc'!A1" runs on
# open). `guard=True` on a cell forces such a value to a STRING cell so Excel
# shows it verbatim and never executes it. The value is kept byte-for-byte
# (only the cell TYPE changes), so equal sides still compare equal and clean
# data is written exactly as before — the regression lock is unaffected.
_FORMULA_LEAD = ("=", "+", "-", "@")


def is_formula_injection(value):
    """True when `value` is text Excel might evaluate as a formula."""
    return isinstance(value, str) and value[:1] in _FORMULA_LEAD


def _styled(ws, value, font, fill=None, align=None, guard=False):
    c = WriteOnlyCell(ws, value=value)
    c.font = font
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    if guard and is_formula_injection(value):
        c.data_type = "s"          # never let user text become a live formula
    return c


def _header_row(ws, values, comment_fn=None):
    font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", start_color=_DARK)
    align = Alignment(horizontal="center", vertical="bottom", wrap_text=True)
    cells = [_styled(ws, v, font, fill, align) for v in values]
    if comment_fn is not None:                # attach hover tooltips (HL columns)
        for c in cells:
            cm = comment_fn(c.value)
            if cm is not None:
                c.comment = cm
    return cells


def _apply_field_widths(ws, widths, col_for, lay):
    """Set column widths from a {field name -> width} schema dict. Applies to
    EVERY column with that name (header.index would width only the first of a
    duplicate name); skips a column only when col_for can't place it — the
    Comparison/Only-in field_col raises for the key index, while the data
    sheet's data_col places the key column fine (so its width is kept)."""
    for name, width in widths.items():
        for idx, h in enumerate(lay.sc.header):
            if h != name:
                continue
            try:
                col = col_for(idx)
            except (KeyError, ValueError):
                continue
            ws.column_dimensions[col].width = width


def _write_data_sheet(wb, name, tab_color, rows, lay, events, cmp_rows,
                      helper_keys=None):
    """One input copied to its sheet, with a leading 'Comparison row' LINK
    back to where each row appears on the Comparison sheet (column A — so a
    reviewer who jumped here from a row link has a one-click way back, right
    where they land) and the live 'Key (helper)' column at the end. The link
    target is a literal (cmp_rows[i]), consistent with the workbook's
    design: the comparison's row universe is fixed at build time, only the
    VALUES are live."""
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = tab_color
    body_font = Font(name="Arial", size=10)
    link_font = _link_font()

    # Keep the back-link + Route + key column in view while scrolling fields.
    ws.freeze_panes = "D2" if lay.has_route else "C2"
    ws.auto_filter.ref = f"A1:{lay.data_last_col}{len(rows) + 1}"
    ws.column_dimensions[lay.key_col].width = 14
    ws.column_dimensions[lay.back_col].width = 13
    if lay.has_route:
        ws.column_dimensions[lay.route_data_col].width = 8
    _apply_field_widths(ws, lay.sc.data_widths, lay.data_col, lay)

    ws.append(_header_row(ws, ["Comparison row"] + lay.data_header + ["Key (helper)"],
                          lay.sc.header_comment))
    # DISPLAY-only ditto resolution (Highway Log): {row_index: {col_in_row:
    # resolved}} — keeps the raw `++` in the cell (the non-asserting diff needs
    # it) but tints it and shows the paired-roadbed value on hover. None elsewhere.
    fills = (lay.sc.ditto_resolver(rows, lay.has_route)
             if lay.sc.ditto_resolver is not None else None)
    ditto_fill = PatternFill("solid", start_color=_DITTO_FILL) if fills else None
    for r, row in enumerate(rows, start=2):
        u = cmp_rows[r - 2]
        # Whole-row target: the jump selects the entire Comparison row
        # (temporary highlight until the next click) WITHOUT scrolling
        # right, same as the forward row links.
        cells = [_styled(ws, f'=HYPERLINK("#Comparison!{u}:{u}",{u})', link_font)]
        # Raw input values are guarded: a Description like "=cmd…" stays text,
        # never a live formula (the field FORMULAS read these via TRIM/INDEX, so
        # guarding here protects both flavors at the source).
        cells += [_styled(ws, v, body_font, guard=True) for v in row]
        row_fills = fills.get(r - 2) if fills else None
        if row_fills:                        # mark each dittoed cell in this row
            for col_in_row, resolved in row_fills.items():
                c = cells[1 + col_in_row]    # cells[0] is the back-link
                c.fill = ditto_fill
                shown = resolved if resolved not in (None, "") else "(no paired value found)"
                c.comment = Comment(
                    f"Ditto ('{c.value}') — value is on the paired roadbed's row; "
                    f"resolves to: {shown}. Not counted as a difference.",
                    "TSMIS Exporter")
        # Both flavors write a LITERAL key (the comparison's row universe is
        # build-time static): a live COUNTIFS mis-numbers blank key fields, and
        # the literal always matches the Comparison sheet's stored occurrence #.
        # Guard the helper key too: a key like "=X" would otherwise become a
        # live formula here, breaking the Comparison MATCH lookups (which search
        # for the literal "=X|1") AND splitting the two flavors. Guarding stores
        # the literal string the lookups expect.
        cells.append(_styled(ws, helper_keys[r - 2], body_font, guard=True))
        ws.append(cells)
        if (r - 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  {name} sheet: {r - 1:,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _write_comparison(wb, union, lay, events, vals=None):
    """The big sheet. `vals` None = live formulas (the default workbook);
    else the values model (run_compare builds it) and every cell is the
    computed RESULT — identical text, no formulas, links kept."""
    sc = lay.sc
    ws = wb.create_sheet("Comparison")
    ws.sheet_properties.tabColor = _TAB_COLORS["comparison"]
    body_font = Font(name="Arial", size=10)

    last = len(union) + 1
    ws.row_dimensions[1].height = 45.75
    ws.freeze_panes = f"{lay.first_field_col}2"
    ws.auto_filter.ref = f"A1:{lay.last_field_col}{last}"
    if lay.has_route:
        ws.column_dimensions["A"].width = 8
    ws.column_dimensions[lay.c_loc].width = 12
    ws.column_dimensions[lay.c_occ].width = 4
    ws.column_dimensions[lay.c_trow].width = 7
    ws.column_dimensions[lay.c_status].width = 11
    ws.column_dimensions[lay.c_diffs].width = 6
    _apply_field_widths(ws, sc.cmp_widths, lay.field_col, lay)

    # Conditional formatting (same look as the sample, diff detection keyed on
    # the ≠ marker): red diff cells, yellow A-only rows, blue B-only rows,
    # bold red Diffs count when > 0.
    f1 = lay.first_field_col
    full = f"A2:{lay.last_field_col}{last}"
    fields = f"{f1}2:{lay.last_field_col}{last}"
    ws.conditional_formatting.add(fields, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("{_DIFF_MARK}",{f1}2))'],
        fill=PatternFill(bgColor="FFC7CE"),
        font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=[f'${lay.c_status}2="{lay.only_a}"'], fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=[f'${lay.c_status}2="{lay.only_b}"'], fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"{lay.c_diffs}2:{lay.c_diffs}{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        font=Font(color="C00000", bold=True)))

    link_font = _link_font()
    link_cols = {3, 4} if lay.has_route else {2, 3}   # trow / nrow positions
    ws.append(_header_row(ws, lay.id_headers
                          + [sc.header[i] for i in lay.field_indices],
                          lay.sc.header_comment))
    for i, (route, loc, occ) in enumerate(union):
        r = i + 2
        if vals is None:
            key = lay.key_expr(r)
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link(sc.side_a, key, lay),
                _row_link(sc.side_b, key, lay),
                f'=IF(AND({lay.c_trow}{r}<>"",{lay.c_nrow}{r}<>""),"Both",'
                f'IF({lay.c_trow}{r}<>"","{lay.only_a}","{lay.only_b}"))',
                # Diffs counts cells carrying the ≠ marker (matched cells show
                # the value, so "non-blank" no longer means "different").
                f'=IF({lay.c_status}{r}<>"Both","",SUMPRODUCT(--ISNUMBER(SEARCH('
                f'"{_DIFF_MARK}",{lay.first_field_col}{r}:{lay.last_field_col}{r}))))',
            ]
            row += [_field_formula(lay, r, f)
                    for f in lay.field_indices]
        else:
            k = (route, loc, occ)
            rt, rn = vals["by_t"].get(k), vals["by_n"].get(k)
            tr, nr = vals["row_t"].get(k), vals["row_n"].get(k)
            status = ("Both" if rt is not None and rn is not None
                      else lay.only_a if rt is not None else lay.only_b)
            fields, ndiff = [], 0
            for f in lay.field_indices:
                v = _field_value(sc, rt, rn, vals["off"], f)
                if _DIFF_MARK in v:
                    ndiff += 1
                fields.append(v if v != "" else None)
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link_value(sc.side_a, tr, lay) if tr else None,
                _row_link_value(sc.side_b, nr, lay) if nr else None,
                status,
                ndiff if status == "Both" else None,
            ] + fields
        # Guard literal cells against formula injection without touching our own
        # formulas: in the formulas flavor only the key/route id cells are
        # literals (everything else is an =formula or a HYPERLINK link); in the
        # values flavor every non-link cell is a literal. (HYPERLINK cells must
        # stay formulas, so they're never guarded.)
        if vals is None:
            guard_set = {0} if lay.has_route else set()
            guard_set.add(1 if lay.has_route else 0)         # the key (loc) cell
        else:
            guard_set = set(range(len(row))) - link_cols
        ws.append([_styled(ws, v, link_font if j in link_cols else body_font,
                           guard=(j in guard_set))
                   for j, v in enumerate(row)])
        if (i + 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  Comparison sheet: {i + 1:,} of {len(union):,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _write_spot_check(wb, lay, n_union, default_row, default_key,
                      manual_calc=False):
    """'Spot Check': one row under a microscope, for reviewers who doubt
    the formulas. Type any Comparison row number (or find one by its key)
    and the sheet lays that row out field by field — the RAW values from
    both data sheets next to an INDEPENDENTLY recomputed verdict (same
    TRIM / Med Wid rules, computed straight from the data sheets, never
    reading the Comparison sheet's answer) and an Agree? column that flags
    any disagreement with what the Comparison sheet displays. On one-sided
    rows the verdict column carries the status itself (tinted) plus a loud
    callout line — the Status cell alone is easy to miss — and Agree? still
    verifies the displayed value against that system's data sheet. Opens
    pre-set to `default_row`, the first matched row with differences."""
    sc = lay.sc
    a, b = sc.side_a, sc.side_b
    ws = wb.create_sheet("Spot Check")
    ws.sheet_properties.tabColor = _TAB_COLORS["spot"]
    ws.sheet_view.showGridLines = False

    title_font = Font(name="Arial", size=14, bold=True, color=_DARK)
    note_font = Font(name="Arial", size=10, color="595959")
    banner_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    banner_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)
    bold_font = Font(name="Arial", size=10, bold=True)
    alert_font = Font(name="Arial", size=11, bold=True, color="C00000")
    input_font = Font(name="Arial", size=11, bold=True)
    input_fill = PatternFill("solid", start_color="FFF2CC")
    link_font = _link_font()
    center = Alignment(horizontal="center")
    right = Alignment(horizontal="right")

    last = n_union + 1
    inp = "$C$6"                                   # the row-number input cell
    trow_cell, nrow_cell = "$C$12", "$F$12"        # matched data-sheet rows
    status = "$C$11"                               # the row's status cell
    F_FIRST = 16                                   # first field row
    F_LAST = F_FIRST + lay.n_fields - 1
    has_medwid = bool(sc.medwid_fields)

    for col, w in (("A", 2), ("B", 19), ("C", 24), ("D", 24), ("E", 17),
                   ("F", 30), ("G", 9), ("H", 16), ("I", 16), ("J", 16)):
        ws.column_dimensions[col].width = w
    # Verdict / agreement colors. One-sided verdicts tint like the
    # Comparison sheet's yellow/blue rows so the situation is unmissable.
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=['"DIFFERENT"'],
        font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=[f'"{lay.only_a}"'],
        fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=[f'"{lay.only_b}"'],
        fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"G{F_FIRST}:G{F_LAST}", CellIsRule(
        operator="equal", formula=['"CHECK"'],
        fill=PatternFill(bgColor="FFC7CE"), font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(f"G{F_FIRST}:G{F_LAST}", CellIsRule(
        operator="equal", formula=['"OK"'], font=Font(color="2E7D32", bold=True)))

    grid = {}

    def put(rc, value, font=body_font, fill=None, align=None, fmt=None):
        grid[rc] = (value, font, fill, align, fmt)

    def banner(row, text):
        put((row, 2), text, banner_font, banner_fill)
        for c in range(3, 11):                     # extend the band to col J
            put((row, c), "", banner_font, banner_fill)

    # --- intro + inputs --------------------------------------------------
    put((2, 2), f"Spot Check — audit any single {sc.id_noun}", title_font)
    put((3, 2), "Every value below recomputes for the row you pick. The "
                "'Independent verdict' column re-compares the two data sheets "
                "directly (TRIM" + (" + the Med Wid rule" if has_medwid else "")
                + ") WITHOUT reading the "
                "Comparison sheet — Agree? = OK means both computations "
                "reached the same answer.", note_font)
    put((4, 2), f"In difference cells the order is always:   "
                f"{a} value{_DIFF_MARK}{b} value   ({a} first, {b} second).",
        bold_font)
    if manual_calc:
        put((5, 2), "▶ PRESS F9 AFTER EVERY CHANGE — this workbook calculates "
                    "manually, so nothing updates until you do.", alert_font)
    put((6, 2), f"Comparison row # to check (2–{last}):", bold_font)
    put((6, 3), default_row, input_font, input_fill, center)
    put((6, 4), "← type a row number" + (", then press F9" if manual_calc
                                         else " (updates instantly)"), note_font)
    d_route, d_loc, d_occ = default_key
    key_label = sc.header[lay.key_field]
    if lay.has_route:
        put((7, 2), "…or find one:", note_font)
        put((7, 3), "Route:", bold_font, None, right)
        put((7, 4), d_route, body_font, input_fill, center, "@")
        put((7, 5), f"{key_label}:", bold_font, None, right)
        put((7, 6), d_loc, body_font, input_fill, center, "@")
        put((7, 7), "Occ #:", bold_font, None, right)
        put((7, 8), d_occ, body_font, input_fill, center)
        find = (f"SUMPRODUCT((Comparison!$A$2:$A${last}=$D$7)"
                f"*(Comparison!${lay.c_loc}$2:${lay.c_loc}${last}=$F$7)"
                f"*(Comparison!${lay.c_occ}$2:${lay.c_occ}${last}=$H$7)"
                f"*ROW(Comparison!$A$2:$A${last}))")
        put((7, 9), "→ Comparison row:", bold_font, None, right)
        put((7, 10), f'=IF({find}=0,"not found",{find})', bold_font, None, center)
    else:
        put((7, 2), "…or find one:", note_font)
        put((7, 3), f"{key_label}:", bold_font, None, right)
        put((7, 4), d_loc, body_font, input_fill, center, "@")
        put((7, 5), "Occ #:", bold_font, None, right)
        put((7, 6), d_occ, body_font, input_fill, center)
        find = (f"SUMPRODUCT((Comparison!$A$2:$A${last}=$D$7)"
                f"*(Comparison!$B$2:$B${last}=$F$7)"
                f"*ROW(Comparison!$A$2:$A${last}))")
        put((7, 7), "→ Comparison row:", bold_font, None, right)
        put((7, 8), f'=IF({find}=0,"not found",{find})', bold_font, None, center)

    # --- what the Comparison sheet says ----------------------------------
    def cmp_idx(col):
        return f"INDEX(Comparison!${col}:${col},{inp})"

    banner(9, "WHAT THE COMPARISON SHEET SHOWS FOR THAT ROW")
    if lay.has_route:
        put((10, 2), "Route:", bold_font)
        put((10, 3), f'=IFERROR({cmp_idx(lay.c_route)},"")', body_font)
    put((10, 5), f"{key_label}:", bold_font)
    put((10, 6), f'=IFERROR({cmp_idx(lay.c_loc)},"")', body_font)
    put((10, 8), "Occurrence #:", bold_font)
    put((10, 9), f'=IFERROR({cmp_idx(lay.c_occ)},"")', body_font)
    put((11, 2), "Status:", bold_font)
    put((11, 3), f'=IFERROR({cmp_idx(lay.c_status)},"")', bold_font)
    put((11, 5), "Diffs counted:", bold_font)
    put((11, 6), f'=IFERROR({cmp_idx(lay.c_diffs)},"")', bold_font)
    put((12, 2), f"{a} sheet row:", bold_font)
    put((12, 3), f'=IFERROR(IF({cmp_idx(lay.c_trow)}="","",'
                 f'HYPERLINK("#{_sref(a)}!"&{cmp_idx(lay.c_trow)}&'
                 f'":"&{cmp_idx(lay.c_trow)},'
                 f'{cmp_idx(lay.c_trow)})),"")', link_font)
    put((12, 5), f"{b} sheet row:", bold_font)
    put((12, 6), f'=IFERROR(IF({cmp_idx(lay.c_nrow)}="","",'
                 f'HYPERLINK("#{_sref(b)}!"&{cmp_idx(lay.c_nrow)}&'
                 f'":"&{cmp_idx(lay.c_nrow)},'
                 f'{cmp_idx(lay.c_nrow)})),"")', link_font)
    # Loud one-sided callout: the Status cell alone is easy to miss.
    put((13, 2), f'=IF({status}="{lay.only_a}","⚠ THIS {sc.id_noun.upper()} EXISTS ONLY IN '
                 f'{a} — there is no {b} row to compare; {b} values below '
                 f'are blank.",IF({status}="{lay.only_b}","⚠ THIS {sc.id_noun.upper()} EXISTS '
                 f'ONLY IN {b} — there is no {a} row to compare; {a} '
                 f'values below are blank.",""))', alert_font)

    # --- field-by-field ---------------------------------------------------
    banner(15, "FIELD BY FIELD — RECOMPUTED FROM THE DATA SHEETS "
               "(independent of the Comparison sheet)")
    headers = ["Field", f"{a} value (as stored)", f"{b} value (as stored)",
               "Independent verdict", f"Comparison sheet shows "
               f"({a}{_DIFF_MARK}{b})", "Agree?"]
    if has_medwid:
        headers += [f"{a} Med-Wid normalized", f"{b} Med-Wid normalized"]
    for j, h in enumerate(headers):
        put((F_FIRST - 1, 2 + j), h,
            Font(name="Arial", size=10, bold=True, color="FFFFFF"),
            banner_fill, Alignment(horizontal="center", wrap_text=True))

    def raw(side, col, row_ref):
        idx = f"INDEX({_sref(side)}!{col}:{col},{row_ref})"
        return (f'=IF({row_ref}="","",IFERROR(IF(ISBLANK({idx}),"",{idx}),""))')

    for pos, f in enumerate(lay.field_indices):
        r = F_FIRST + pos
        col = lay.data_col(f)
        fcol = lay.field_col(f)
        is_date = sc.header[f] in sc.date_fields
        fmt = "mm/dd/yyyy" if is_date else None
        trim_t = _trim_ref(a, col, trow_cell)
        trim_n = _trim_ref(b, col, nrow_cell)
        if sc.is_medwid(f):
            eq = (f'{_medwid_ref(a, col, trow_cell)}='
                  f'{_medwid_ref(b, col, nrow_cell)}')
            put((r, 8), f'=IF({trow_cell}="","",'
                        f'{_medwid_ref(a, col, trow_cell)})', body_font,
                None, center)
            put((r, 9), f'=IF({nrow_cell}="","",'
                        f'{_medwid_ref(b, col, nrow_cell)})', body_font,
                None, center)
        else:
            eq = f"{trim_t}={trim_n}"
        eq = _eq_with_ditto(sc, eq, trim_t, trim_n)   # ditto = non-asserting (HL only)
        if sc.is_context(f):
            eq = "TRUE"                                # context = non-asserting: always 'match'
        put((r, 2), sc.header[f], bold_font)
        put((r, 3), raw(a, col, trow_cell), body_font, None, None, fmt)
        put((r, 4), raw(b, col, nrow_cell), body_font, None, None, fmt)
        # One-sided rows: the verdict carries the status itself (tinted via
        # CF) so the situation shows in every field row, not just up top.
        put((r, 5), f'=IF({status}="","",IF({status}<>"Both",{status},'
                    f'IF({eq},"match","DIFFERENT")))', body_font, None, center)
        put((r, 6), f'=IFERROR(INDEX(Comparison!{fcol}:{fcol},{inp}),"")',
            body_font)
        # Agree?: matched rows — recomputed verdict vs the ≠ marker;
        # one-sided rows — the displayed value must equal that system's own
        # (trimmed) value, so the column stays meaningful there too.
        put((r, 7), f'=IF({status}="","",IF({status}="Both",'
                    f'IF((E{r}="DIFFERENT")=ISNUMBER(SEARCH("{_DIFF_MARK}",'
                    f'F{r})),"OK","CHECK"),IF({status}="{lay.only_a}",'
                    f'IF({trim_t}=F{r},"OK","CHECK"),'
                    f'IF({trim_n}=F{r},"OK","CHECK"))))', body_font, None, center)

    put((F_LAST + 2, 2),
        "• On rows that exist in only one system the verdict column shows "
        f"'{lay.only_a}' / '{lay.only_b}' on every field; Agree? then verifies the "
        "displayed value against that system's data sheet.", note_font)
    put((F_LAST + 3, 2),
        "• The blue row numbers jump to the source row on the data sheets "
        "and select the whole row so it stands out — it un-highlights when "
        "you click elsewhere. Each data-sheet row links back to its "
        "Comparison row. Values are shown exactly as stored (before TRIM).",
        note_font)

    # Emit the sparse grid (append-only streaming sheet).
    n_rows = max(r for r, _c in grid)
    n_cols = max(c for _r, c in grid)
    for r in range(1, n_rows + 1):
        cells = []
        for c in range(1, n_cols + 1):
            if (r, c) in grid:
                value, font, fill, align, fmt = grid[(r, c)]
                cell = _styled(ws, value, font, fill, align)
                if fmt:
                    cell.number_format = fmt
                cells.append(cell)
            else:
                cells.append(None)
        ws.append(cells)
    return ws


def _write_only_sheet(wb, side, other, tab_color, keys, lay, events, vals=None):
    """'Only in <side>': every one-sided union row, in union order, with the
    full field data pulled LIVE from that system's data sheet (same
    MATCH-on-helper-key + INDEX pattern as the Comparison sheet, so the tab
    recalculates with edits). Consolidated mode adds a "Missing from <other>"
    column — "entire route" (tinted: the other system lacks the whole route)
    vs "this <noun> only" — so wholly-missing routes can't be overlooked."""
    sc = lay.sc
    name = f"Only in {side}"
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = tab_color
    body_font = Font(name="Arial", size=10)

    id_headers = ((["Route"] if lay.has_route else [])
                  + [sc.header[lay.key_field], "#", f"{side} Row"]
                  + ([f"Missing from {other}"] if lay.has_route else []))
    n_id = len(id_headers)
    # fields follow the id columns in display order; a header index maps to its
    # position among the displayed fields (key_field == 0 → n_id + field_idx,
    # the original mapping).
    fcol = lambda fi: get_column_letter(n_id + 1 + lay.field_pos(fi))
    first_field = get_column_letter(n_id + 1)
    last_field = get_column_letter(n_id + lay.n_fields)
    last = len(keys) + 1
    c = [get_column_letter(i + 1) for i in range(n_id)]
    if lay.has_route:
        c_route, c_loc, c_occ, c_row, c_why = c
    else:
        c_route = c_why = None
        c_loc, c_occ, c_row = c

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = f"{first_field}2"
    ws.auto_filter.ref = f"A1:{last_field}{last}"
    if lay.has_route:
        ws.column_dimensions[c_route].width = 8
        ws.column_dimensions[c_why].width = 18
    ws.column_dimensions[c_loc].width = 12
    ws.column_dimensions[c_occ].width = 4
    ws.column_dimensions[c_row].width = 9
    _apply_field_widths(ws, sc.cmp_widths, fcol, lay)
    if lay.has_route and keys:
        # Whole-route gaps stand out; single-location gaps stay plain. Colors
        # mirror the Comparison sheet's one-sided row tints. (`keys` can be
        # EMPTY when the two sides match perfectly — common between
        # environments — and an empty tab's CF range "A2:..1" is invalid.)
        tint = "FFE699" if side == sc.side_a else "BDD7EE"
        ws.conditional_formatting.add(f"A2:{last_field}{last}", FormulaRule(
            formula=[f'${c_why}2="entire route"'], fill=PatternFill(bgColor=tint)))

    link_font = _link_font()
    link_col = 3 if lay.has_route else 2              # the "<side> Row" position
    if vals is not None:
        own_rows = vals["row_t"] if side == sc.side_a else vals["row_n"]
        own_by = vals["by_t"] if side == sc.side_a else vals["by_n"]
        other_routes = vals["routes_n"] if side == sc.side_a else vals["routes_t"]
    ws.append(_header_row(ws, id_headers
                          + [sc.header[i] for i in lay.field_indices],
                          lay.sc.header_comment))
    for i, (route, loc, occ) in enumerate(keys):
        r = i + 2
        if vals is None:
            if lay.has_route:
                key = f'${c_route}{r}&"|"&${c_loc}{r}&"|"&${c_occ}{r}'
            else:
                key = f'${c_loc}{r}&"|"&${c_occ}{r}'
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link(side, key, lay),
            ]
            if lay.has_route:
                rc = lay.route_data_col      # Route on the data sheets (B)
                row.append(f'=IF(COUNTIF({_sref(other)}!${rc}:${rc},$A{r})=0,'
                           f'"entire route","this {sc.id_noun} only")')
            rr = f"${c_row}{r}"
            row += [f'=IF({rr}="","",{_trim_ref(side, lay.data_col(f), rr)})'
                    for f in lay.field_indices]
        else:
            k = (route, loc, occ)
            own = own_by[k]
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link_value(side, own_rows[k], lay),
            ]
            if lay.has_route:
                row.append("entire route" if route not in other_routes
                           else f"this {sc.id_noun} only")
            row += [(_xl_trim(own[f + vals["off"]]) or None)
                    for f in lay.field_indices]
        # Same injection guard as the Comparison sheet: in the formulas flavor
        # only the key/route id cells are literals; in the values flavor every
        # non-link cell is. The "<side> Row" HYPERLINK must stay a formula.
        if vals is None:
            guard_set = {0} if lay.has_route else set()
            guard_set.add(1 if lay.has_route else 0)         # the key (loc) cell
        else:
            guard_set = set(range(len(row))) - {link_col}
        ws.append([_styled(ws, v, link_font if j == link_col else body_font,
                           guard=(j in guard_set))
                   for j, v in enumerate(row)])
        if (i + 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  {name} sheet: {i + 1:,} of {len(keys):,} rows…")
            if events.is_cancelled():
                return None
    return ws


def route_coverage(keys_t, keys_n):
    """Route lists, ordered as the union orders them: side A's route order,
    then B-only routes in B order. Returns (all_routes, both, t_only,
    n_only) — each a list of route ids."""
    rt = list(dict.fromkeys(k[0] for k in keys_t))
    rn = list(dict.fromkeys(k[0] for k in keys_n))
    set_t, set_n = set(rt), set(rn)
    all_routes = rt + [r for r in rn if r not in set_t]
    return (all_routes,
            [r for r in all_routes if r in set_t and r in set_n],
            [r for r in rt if r not in set_n],
            [r for r in rn if r not in set_t])


def _write_routes(wb, all_routes, lay, vals=None):
    """Consolidated mode only: one row per route with LIVE coverage stats —
    which system has it, how many rows each side carries, and how much of it
    differs. The route ids are the row universe (literals, like the
    Comparison sheet's keys); every count is a formula."""
    sc = lay.sc
    Noun = sc.id_noun_plural.capitalize()
    ws = wb.create_sheet("Routes")
    ws.sheet_properties.tabColor = _TAB_COLORS["routes"]
    body_font = Font(name="Arial", size=10)
    last = len(all_routes) + 1
    st, df = lay.c_status, lay.c_diffs

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:H{last}"
    for col, w in (("A", 8), ("B", 12), ("C", 12), ("D", 12),
                   ("E", 16), ("F", 16), ("G", 18), ("H", 14)):
        ws.column_dimensions[col].width = w
    ws.row_dimensions[1].height = 30
    # Status colors match the Comparison sheet; red counts where differences exist.
    ws.conditional_formatting.add(f"A2:H{last}", FormulaRule(
        formula=[f'$B2="{lay.only_a}"'], fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(f"A2:H{last}", FormulaRule(
        formula=[f'$B2="{lay.only_b}"'], fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"G2:H{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        font=Font(color="C00000", bold=True)))

    ws.append(_header_row(ws, [
        "Route", "Status", f"{sc.side_a} rows", f"{sc.side_b} rows",
        f"{Noun} compared", f"Matched {sc.id_noun_plural}",
        f"{Noun} w/ differences", "Differing cells"]))
    rc = lay.route_data_col                  # Route on the data sheets (B)
    sa, sb = _sref(sc.side_a), _sref(sc.side_b)
    for i, route in enumerate(all_routes):
        r = i + 2
        if vals is None:
            cells = (
                route,
                f'=IF(AND(C{r}>0,D{r}>0),"Both",IF(C{r}>0,"{lay.only_a}","{lay.only_b}"))',
                f'=COUNTIF({sa}!${rc}:${rc},$A{r})',
                f'=COUNTIF({sb}!${rc}:${rc},$A{r})',
                f'=COUNTIF(Comparison!$A:$A,$A{r})',
                f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both")',
                f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both",'
                f'Comparison!${df}:${df},">0")',
                f'=SUMIF(Comparison!$A:$A,$A{r},Comparison!${df}:${df})',
            )
        else:
            rs = vals["counts"]["route"][route]
            cells = (
                route,
                ("Both" if rs["t_rows"] and rs["n_rows"]
                 else lay.only_a if rs["t_rows"] else lay.only_b),
                rs["t_rows"], rs["n_rows"], rs["locs"], rs["matched"],
                rs["withdiffs"], rs["cells"],
            )
        # Guard only the route-id cell (cell 0): a route like "=X" would become
        # a live formula. The other cells are our own =formulas (formulas flavor)
        # or safe literals (values flavor) and must NOT be forced to text.
        ws.append([_styled(ws, v, body_font, guard=(j == 0))
                   for j, v in enumerate(cells)])
    return ws


def _write_summary(wb, name_a, name_b, n_union, lay, vals=None, warnings=()):
    """`vals` None = live-formula stats; else the values model and every
    stat is its literal number. The SELF-CHECK rows stay LIVE in both
    flavors — in the values workbook they recount the literal sheets, so
    they still prove the written numbers are internally consistent.

    `warnings` (input files that were unreadable/skipped on one or both sides)
    makes the report honest about incompleteness: a clean "everything matches"
    is downgraded to a loud "could not compare everything" banner and the skips
    are listed in the notes. Empty warnings → byte-identical to before."""
    sc = lay.sc
    a, b = sc.side_a, sc.side_b
    noun, nouns = sc.id_noun, sc.id_noun_plural
    Nouns = nouns.capitalize()
    ws = wb.create_sheet("Summary")
    ws.sheet_properties.tabColor = _TAB_COLORS["summary"]
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["B"].width = 46
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 20

    title_font = Font(name="Arial", size=14, bold=True, color=_DARK)
    note_font = Font(name="Arial", size=10, color="595959")
    banner_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    banner_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)
    bold_font = Font(name="Arial", size=10, bold=True)
    center = Alignment(horizontal="center")
    last = n_union + 1                              # Comparison data end row
    loc_col = lay.data_col(lay.key_field)  # key column on the data sheets
    st, df = lay.c_status, lay.c_diffs
    sa, sb = _sref(a), _sref(b)

    # Streaming sheets are append-only: build a sparse (row, col) grid first,
    # emit it row by row at the end.
    grid = {}
    row = [1]                                       # 1-slot mutable cursor

    def put(col, value, font=body_font, fill=None, align=None):
        grid[(row[0], col)] = (value, font, fill, align)

    def line(*cells, advance=1):
        for col, value, *style in cells:
            put(col, value, *style)
        row[0] += advance

    def banner(text):
        line((2, text, banner_font, banner_fill))

    def stat(label, formula, value=None):
        line((2, label),
             (3, formula if vals is None else value, bold_font, None, center))

    c = None if vals is None else vals["counts"]
    scope = (sc.scope_consolidated if lay.has_route else sc.scope_flat) \
        + ("" if vals is None else " — VALUES copy")
    manual_banner = lay.has_route and vals is None
    # THE VERDICT — the one-line answer most comparisons exist for ("did
    # anything change between the two sides?"). Live in the formulas flavor
    # (recomputes with edits / after F9; blank until then in manual mode), a
    # literal in the values flavor. Green/red via CF keyed on the ✓/✗ glyph.
    verdict_row = 4 if manual_banner else 3
    verdict_font = Font(name="Arial", size=12, bold=True)
    ws.conditional_formatting.add(f"B{verdict_row}", FormulaRule(
        formula=[f'LEFT($B${verdict_row},1)="✓"'],
        fill=PatternFill(bgColor="C6EFCE"), font=Font(color="2E7D32", bold=True)))
    ws.conditional_formatting.add(f"B{verdict_row}", FormulaRule(
        formula=[f'LEFT($B${verdict_row},1)="✗"'],
        fill=PatternFill(bgColor="FFC7CE"), font=Font(color="9C0006", bold=True)))
    match_text = (f"✓ EVERYTHING MATCHES — all {n_union:,} {nouns} are "
                  f"identical in both {sc.sides_noun}.")
    if warnings:
        # Some inputs couldn't be read — a clean "match" can't be certified.
        # Leads with ✗ so the existing red conditional-format applies (no new
        # CF rule, so the no-warnings path stays byte-identical).
        match_text = (f"✗ COULD NOT COMPARE EVERYTHING — {len(warnings)} input "
                      f"file(s) were unreadable and skipped; of the {n_union:,} "
                      f"{nouns} that WERE compared, all match. See the notes.")
    if vals is None:
        diff_cells_ref = f"SUM(Comparison!{df}2:{df}{last})"
        one_sided_ref = (f'COUNTIF(Comparison!{st}:{st},"{lay.only_a}")'
                         f'+COUNTIF(Comparison!{st}:{st},"{lay.only_b}")')
        verdict_cell = (
            f'=IF(AND({diff_cells_ref}=0,{one_sided_ref}=0),"{match_text}",'
            f'"✗ DIFFERENCES FOUND — "&TEXT({diff_cells_ref},"#,##0")&'
            f'" differing cell(s), "&TEXT({one_sided_ref},"#,##0")&'
            f'" one-sided row(s) — details below.")')
    else:
        one_sided = c["t_only"] + c["n_only"]
        verdict_cell = (match_text if c["diff_cells"] == 0 and one_sided == 0
                        else f"✗ DIFFERENCES FOUND — {c['diff_cells']:,} "
                             f"differing cell(s), {one_sided:,} one-sided "
                             "row(s) — details below.")
    row[0] = 2
    line((2, f"{a} vs {b} — {sc.report_name} — Discrepancy Report ({scope})", title_font))
    if manual_banner:
        # The big formulas workbook ships UNCALCULATED (manual mode): every
        # cell shows blank/0 until F9. Without a loud banner that reads as
        # broken data. (The values copy calculates nothing — no banner.)
        line((2, "▶ PRESS F9 TO CALCULATE — this workbook opens uncalculated "
                 "(blank/0 cells). The first F9 takes a few minutes; let it "
                 "finish, then save.",
              Font(name="Arial", size=11, bold=True, color="C00000")))
    assert row[0] == verdict_row            # the CF above targets this cell
    line((2, verdict_cell, verdict_font))
    line((2, "Cell-by-cell comparison keyed on "
             + (f"Route + {sc.header[lay.key_field]}" if lay.has_route
                else sc.header[lay.key_field])
             + " (+ occurrence for duplicates). "
             + (f"All formulas are live: edits on the {a} / {b} sheets "
                "recalculate everything." if vals is None else
                "This copy holds plain VALUES — it opens instantly and "
                "nothing needs calculating, but edits do NOT recalculate "
                "(the live-formulas copy does that). The Spot Check sheet "
                "and the SELF-CHECK rows below stay live."), note_font))
    line((2, f"{a}: {name_a}      {b}: {name_b}      "
             f"created {date.today().isoformat()}", note_font), advance=2)

    banner("ROW COUNTS")
    stat(f"{a} data rows", f"=COUNTA({sa}!{lay.back_col}:{lay.back_col})-1",
         None if vals is None else vals["n_t"])
    stat(f"{b} data rows", f"=COUNTA({sb}!{lay.back_col}:{lay.back_col})-1",
         None if vals is None else vals["n_n"])
    stat(f"Union of {nouns} compared",
         f"=COUNT(Comparison!{lay.c_occ}:{lay.c_occ})", n_union)
    banner("MATCH STATUS")
    stat(f"{Nouns} in both {sc.sides_noun}", f'=COUNTIF(Comparison!{st}:{st},"Both")',
         c and c["both"])
    stat(f"In {a} only (missing from {b}) — listed on the 'Only in {a}' sheet",
         f'=COUNTIF(Comparison!{st}:{st},"{lay.only_a}")', c and c["t_only"])
    stat(f"In {b} only (missing from {a}) — listed on the 'Only in {b}' sheet",
         f'=COUNTIF(Comparison!{st}:{st},"{lay.only_b}")', c and c["n_only"])
    if lay.has_route:
        banner("ROUTE COVERAGE (see the Routes sheet for the per-route breakdown)")
        stat(f"Routes covered by both {sc.sides_noun}", '=COUNTIF(Routes!B:B,"Both")',
             None if vals is None else vals["r_both"])
        stat(f"Routes only in {a} (missing from {b})",
             f'=COUNTIF(Routes!B:B,"{lay.only_a}")',
             None if vals is None else vals["r_t_only"])
        stat(f"Routes only in {b} (missing from {a})",
             f'=COUNTIF(Routes!B:B,"{lay.only_b}")',
             None if vals is None else vals["r_n_only"])
    banner("FIELD-LEVEL DISCREPANCIES (matched rows)")
    stat("Matched rows with ≥ 1 field difference",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},">0")', c and c["diff_rows"])
    stat("Matched rows fully identical",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},0)', c and c["identical"])
    stat("Total differing cells", f"=SUM(Comparison!{df}2:{df}{last})",
         c and c["diff_cells"])
    row[0] += 1

    banner("DIFFERENCES BY FIELD")
    line((2, "Field", bold_font), (3, "Comparison col", bold_font),
         (4, "# of cells differing", bold_font))
    f_start = row[0]
    for f in lay.field_indices:
        col = lay.field_col(f)
        line((2, sc.header[f]), (3, col),
             (4, f'=COUNTIF(Comparison!{col}2:{col}{last},"*{_DIFF_MARK}*")'
              if vals is None else c["field_diffs"][f],
              bold_font, None, center))
    f_end = row[0] - 1
    row[0] += 1

    # Live cross-checks: each headline number recomputed a second, independent
    # way. Any row reading CHECK means a formula no longer points where it
    # should (the classic cause: rows inserted/deleted on a data sheet).
    banner("SELF-CHECK (every row should read OK after calculation)")
    only_occ = "C" if lay.has_route else "B"          # occurrence (#) col on Only-in tabs
    only_a_ref = _sref(f"Only in {a}")
    only_b_ref = _sref(f"Only in {b}")

    def check(label, cond):
        line((2, label), (3, f'=IF({cond},"OK","CHECK")', bold_font, None, center))

    union_count = f"COUNT(Comparison!{lay.c_occ}:{lay.c_occ})"
    check(f"Every Comparison row has a status (Both + {lay.only_a} + {lay.only_b})",
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"{lay.only_a}")'
          f'+COUNTIF(Comparison!{st}:{st},"{lay.only_b}")={union_count}')
    check(f"Every row with {a} data found its {a} sheet row",
          f'COUNT(Comparison!{lay.c_trow}:{lay.c_trow})='
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"{lay.only_a}")')
    check(f"Every row with {b} data found its {b} sheet row",
          f'COUNT(Comparison!{lay.c_nrow}:{lay.c_nrow})='
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"{lay.only_b}")')
    check(f"'Only in {a}' sheet rows = {a}-only rows in the Comparison",
          f"COUNT({only_a_ref}!{only_occ}:{only_occ})="
          f'COUNTIF(Comparison!{st}:{st},"{lay.only_a}")')
    check(f"'Only in {b}' sheet rows = {b}-only rows in the Comparison",
          f"COUNT({only_b_ref}!{only_occ}:{only_occ})="
          f'COUNTIF(Comparison!{st}:{st},"{lay.only_b}")')
    check("Per-field difference counts add up to the total differing cells",
          f'SUM(D{f_start}:D{f_end})=SUM(Comparison!{df}2:{df}{last})')
    if lay.has_route:
        check(f"Routes sheet {a} row counts add up to the {a} sheet",
              f"SUM(Routes!C:C)=COUNTA({sa}!{lay.back_col}:{lay.back_col})-1")
        check(f"Routes sheet {b} row counts add up to the {b} sheet",
              f"SUM(Routes!D:D)=COUNTA({sb}!{lay.back_col}:{lay.back_col})-1")
        check(f"Routes sheet '{Nouns} compared' adds up to the Comparison",
              f"SUM(Routes!E:E)={union_count}")
    row[0] += 1

    banner("HOW TO READ / NOTES")
    notes = [
        "• Comparison sheet: matching values are shown in plain text; a red "
        f"cell shows  {a} value{_DIFF_MARK}{b} value  where the two {sc.sides_noun} "
        f"disagree for that {sc.header[lay.key_field]} and field.",
        '• "(blank)" means the cell is empty in that system. Filter the Diffs '
        "column (>0) to isolate rows needing review.",
        f"• Yellow rows exist only in {a}; blue rows exist only in {b}"
        f"{sc.one_sided_note_extra}. Their "
        "field cells show that system's own values.",
        f"• The 'Only in {a}' and 'Only in {b}' sheets repeat every "
        "one-sided row in one place — including the rows of routes the other "
        "system doesn't carry at all"
        + (" (flagged 'entire route' and tinted; filter the 'Missing from …' "
           "column to separate whole-route gaps from single locations)"
           if lay.has_route else "")
        + ". The Comparison sheet still contains the same rows in document "
        "order.",
        "• Rows pair on " + ("Route plus " if lay.has_route else "")
        + f"{sc.header[lay.key_field]} plus occurrence number. When a "
        f"{sc.pair_noun or noun} is listed more than once, the matching "
        "instances are paired by which are MOST ALIKE (fewest differing "
        "fields), not by the order they appear — so a repeat that matches the "
        "other side's second listing isn't flagged as a difference.",
        f"• Leading/trailing spaces are ignored (TRIM){sc.trim_note_extra}.",
        f'• Lookups use the "Key (helper)" column ({lay.key_col}) on each '
        'data sheet: ' + ("Route, " if lay.has_route else "")
        + f'{sc.header[lay.key_field]} & "|" & occurrence #.',
    ]
    if warnings:
        shown = warnings[:20]
        notes.append(
            f"• ⚠ INCOMPLETE COMPARISON — {len(warnings)} input file(s) could not "
            "be read and were left OUT of this comparison, so anything in them "
            "is neither matched nor flagged. Re-export/repair them and re-run "
            "before trusting a clean result:")
        for w in shown:
            notes.append(f"     – {w}")
        if len(warnings) > len(shown):
            notes.append(f"     – …and {len(warnings) - len(shown)} more "
                         "(see the run log).")
    if sc.medwid_fields:
        notes.append(
            "• Med Wid is compared after normalizing zero-padding in the numeric "
            f"part ({a} 0Z = {b} 00Z, 6V = 06V, etc.), since the two systems "
            "format this code differently. All other fields compare exactly.")
    notes.append(
        f"• Doubting a value? The blue row numbers in the '{a} Row' / "
        f"'{b} Row' columns are clickable — they jump to the data sheet and "
        "SELECT that whole row (it stays highlighted until you click "
        "elsewhere), and each data-sheet row links back to its Comparison "
        f"row the same way. The Spot Check sheet audits any single {noun} "
        "end to end: raw values from both systems and an independently "
        "recomputed verdict for every field.")
    if vals is not None:
        notes.append(
            "• This is the VALUES copy: every number and comparison cell is "
            "a computed result, not a formula (only the Spot Check sheet and "
            "the SELF-CHECK rows stay live). If the data changes, re-create "
            "the comparison — or use the live-formulas copy, which "
            "recalculates.")
    notes.append(
        "• SELF-CHECK recomputes the headline numbers a second, independent "
        "way; a CHECK there means the sheets no longer agree (e.g. rows were "
        "inserted or deleted on a data sheet) — re-create the report rather "
        "than trust the numbers.")
    if lay.has_route:
        notes.append(
            "• The Routes sheet lists every route either system carries — "
            "which side covers it, row counts, and how much of it differs.")
        if vals is None:
            notes.append(
                "• CALCULATION IS SET TO MANUAL (large workbook): cells show "
                "blank/0 until you press F9. The first F9 takes a few minutes — "
                "let it finish, then save to keep the results; edits afterwards "
                "only recalculate when you press F9 again. (Excel keeps the "
                "manual setting for other workbooks opened in the same session — "
                "Formulas → Calculation Options switches it back.)")
    for note in notes:
        line((2, note, note_font))

    # Emit the grid (append-only streaming sheet).
    n_rows = max(r for r, _c in grid)
    n_cols = max(c for _r, c in grid)
    for r in range(1, n_rows + 1):
        cells = []
        for c in range(1, n_cols + 1):
            if (r, c) in grid:
                value, font, fill, align = grid[(r, c)]
                cells.append(_styled(ws, value, font, fill, align))
            else:
                cells.append(None)
        ws.append(cells)


def run_compare(sc, rows_t, rows_n, has_route, out_path, *, events=None,
                confirm_overwrite=None, mode="formulas",
                name_a="", name_b="", warnings=()):
    """Build the comparison workbook(s) from two loaded row sets. Returns a
    ConsolidateResult (same contract as the consolidators, so the GUI/console
    drive it identically). The CALLER owns input loading + shape validation;
    `rows_t`/`rows_n` are side A / side B in the schema's column order.

    `mode`: "formulas" (the live workbook — every cell recalculates),
    "values" (same sheets and look, but the bulk is plain computed RESULTS —
    opens instantly, no F9; links, conditional formatting, the Spot Check
    sheet and the SELF-CHECK rows are kept), or "both" (two files: the picked
    name for the formulas copy and '<name> (values).xlsx' next to it).

    `warnings`: input files the caller couldn't read (one per string). When
    non-empty the comparison is INCOMPLETE — the verdict can never be a clean
    "match" (forced to "diff"), the workbook banner says so, and the skipped
    files are listed. Empty → unchanged (the regression-locked default)."""
    warnings = list(warnings)
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    confirm = confirm_overwrite or (lambda _p: True)
    out = Path(out_path)
    a, b = sc.side_a, sc.side_b

    sheets = sc.sheet_names(has_route)
    for sheet in sheets:
        if len(sheet) > 31:
            return ConsolidateResult(
                status="error",
                message=(f"The sheet name '{sheet}' is longer than Excel's "
                         "31-character limit — shorten the side labels."))
    # Excel sheet names must be unique case-insensitively. A side literally named
    # like a fixed sheet ("Summary"/"Comparison"/"Routes"/"Only in …") would
    # collide and openpyxl would raise mid-write; fail early with guidance.
    seen_sheets = {}
    for sheet in sheets:
        low = sheet.casefold()
        if low in seen_sheets:
            return ConsolidateResult(
                status="error",
                message=(f"The side name '{sheet}' collides with another sheet "
                         f"('{seen_sheets[low]}') — pick different side labels "
                         "(avoid Summary / Comparison / Routes / Spot Check / "
                         "'Only in …')."))
        seen_sheets[low] = sheet

    modes = {"formulas": ("formulas",), "values": ("values",),
             "both": ("formulas", "values")}.get(mode)
    if modes is None:
        return ConsolidateResult(status="error",
                                 message=f"Unknown comparison mode: {mode}")
    out_paths = {m: out for m in modes}
    if len(modes) > 1:                  # the values twin sits next to the pick
        out_paths["values"] = out.with_name(f"{out.stem} (values){out.suffix}")

    for m in modes:
        if out_paths[m].exists() and not confirm(out_paths[m]):
            return ConsolidateResult(status="cancelled",
                                     message="Cancelled. Existing file kept.")

    if not rows_t or not rows_n:
        return ConsolidateResult(
            status="error",
            message="One of the inputs has no data rows — nothing to compare.")
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    lay = _Layout(sc, has_route)
    keys_t = keys_for(rows_t, has_route, sc.key_field, sc.key_normalizer)
    keys_n = keys_for(rows_n, has_route, sc.key_field, sc.key_normalizer)
    # Pair duplicate keys by data similarity, not file order, so a row that
    # actually matches the other side's SECOND instance isn't reported as a
    # difference against its FIRST (can only remove phantom diffs, never add).
    keys_t, keys_n = pair_occurrences_by_similarity(
        sc, rows_t, rows_n, keys_t, keys_n, has_route, events)
    union = union_keys(keys_t, keys_n)

    # Excel hard limits: openpyxl would raise mid-write past the row cap (losing
    # the partial file) and silently lose columns past the column cap.
    biggest = max(len(union), len(rows_t), len(rows_n)) + 1   # + header row
    # Widest sheet actually written: the Comparison sheet (id cols + fields) is
    # 3 wider than the data sheet (back-link + columns + key helper).
    n_cols = max(len(lay.data_header) + 2, len(lay.id_headers) + lay.n_fields)
    limit_err = excel_limit_error(biggest, n_cols)
    if limit_err:
        return ConsolidateResult(status="error", message=limit_err)

    counts = count_diffs(sc, rows_t, rows_n, keys_t, keys_n, union, has_route)
    events.on_log(f"{a} rows: {len(rows_t):,}   {b} rows: {len(rows_n):,}   "
                  f"union: {len(union):,} {sc.id_noun_plural}"
                  + (f" across {len({k[0] for k in union})} routes" if has_route else ""))
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    # Shared model for every output flavor (parsed/aligned/counted ONCE).
    spot_row = counts.get("first_diff_row") or 2
    all_routes = r_both = r_t_only = r_n_only = None
    if has_route:
        all_routes, r_both, r_t_only, r_n_only = route_coverage(keys_t, keys_n)
    set_t, set_n = set(keys_t), set(keys_n)
    only_t = [k for k in union if k not in set_n]
    only_n = [k for k in union if k not in set_t]
    union_row = {k: i + 2 for i, k in enumerate(union)}   # data row -> Comparison row
    cmp_rows_t = [union_row[k] for k in keys_t]
    cmp_rows_n = [union_row[k] for k in keys_n]

    cancelled = ConsolidateResult(status="cancelled", message="Cancelled by user.")
    for m in modes:
        path = out_paths[m]
        if m == "values":
            # Everything the formulas would display, precomputed: the writers
            # emit literal results instead of formulas (links/CF/Spot Check/
            # SELF-CHECK stay live). Same _xl_trim/_medwid_norm mirror as the
            # run summary, so the two flavors can never disagree.
            vals = {
                "off": 1 if has_route else 0,
                "by_t": {k: rows_t[i] for i, k in enumerate(keys_t)},
                "by_n": {k: rows_n[i] for i, k in enumerate(keys_n)},
                "row_t": {k: i + 2 for i, k in enumerate(keys_t)},
                "row_n": {k: i + 2 for i, k in enumerate(keys_n)},
                "routes_t": {k[0] for k in keys_t},
                "routes_n": {k[0] for k in keys_n},
                "counts": counts,
                "n_t": len(rows_t), "n_n": len(rows_n),
                "r_both": len(r_both) if has_route else 0,
                "r_t_only": len(r_t_only) if has_route else 0,
                "r_n_only": len(r_n_only) if has_route else 0,
            }
            hk_t = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_t]
            hk_n = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_n]
            events.on_log(f"Writing the VALUES workbook: {path.name}")
        else:
            # The live-formulas flavor now ALSO writes literal lookup keys (the
            # same ones the values flavor uses), not a live COUNTIFS occurrence.
            # A blank key field made the COUNTIFS mis-number occurrences (Excel's
            # blank-criterion quirk), so those rows' lookups failed and the
            # SELF-CHECK read CHECK. Literal keys always match the Comparison
            # sheet's literal occurrence #, and the row universe is build-time
            # static by design anyway (only the field VALUES are live).
            vals = None
            hk_t = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_t]
            hk_n = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_n]
            events.on_log(f"Writing the live-formulas workbook: {path.name}")

        # Streaming workbook (see the note above _styled): sheets are created
        # in display order; Summary first so it's the active sheet on open.
        wb = Workbook(write_only=True)
        if has_route and m == "formulas":
            # ~2M live formulas: in automatic mode Excel would recalculate
            # for minutes on open AND after every edit. Ship the workbook in
            # MANUAL calculation mode instead — it opens instantly showing
            # blanks/zeros, the user presses F9 once (the one unavoidable big
            # calc), saves, and from then on opens are instant and edits
            # don't hang. calcOnSave off so saving doesn't sneak the big calc
            # back in. (Per-route files and the VALUES copy stay automatic.)
            wb.calculation.calcMode = "manual"
            wb.calculation.calcOnSave = False
            wb.calculation.fullCalcOnLoad = False
        _write_summary(wb, name_a, name_b, len(union), lay, vals=vals,
                       warnings=warnings)
        _write_spot_check(wb, lay, len(union), spot_row, union[spot_row - 2],
                          manual_calc=(has_route and m == "formulas"))
        if _write_comparison(wb, union, lay, events, vals=vals) is None:
            return cancelled
        if has_route:
            _write_routes(wb, all_routes, lay, vals=vals)
        # The one-sided rows again, on their own tabs (union order): the rows
        # of routes the other system lacks entirely plus the rows missing
        # from the other side within shared routes.
        if _write_only_sheet(wb, a, b, _TAB_COLORS["only_a"], only_t, lay,
                             events, vals=vals) is None:
            return cancelled
        if _write_only_sheet(wb, b, a, _TAB_COLORS["only_b"], only_n, lay,
                             events, vals=vals) is None:
            return cancelled
        if _write_data_sheet(wb, a, _TAB_COLORS["side_a"], rows_t, lay, events,
                             cmp_rows_t, helper_keys=hk_t) is None:
            return cancelled
        if _write_data_sheet(wb, b, _TAB_COLORS["side_b"], rows_n, lay, events,
                             cmp_rows_n, helper_keys=hk_n) is None:
            return cancelled
        if sc.legend_writer is not None:     # append a column-Legend sheet (HL)
            sc.legend_writer(wb)
        if sc.extra_sheet_writer is not None:  # append a familiar-layout rollup sheet
            sc.extra_sheet_writer(wb, {"rows_a": rows_t, "rows_b": rows_n,
                                       "has_route": has_route, "sc": sc,
                                       "side_a": name_a, "side_b": name_b})
        events.on_log("Saving…")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            wb.save(path)
        except PermissionError:
            return ConsolidateResult(
                status="error",
                message=(f"Could not save {path.name}.\n\n"
                         "The file is probably open in Excel. Close it and try again."))

    def _route_list(label, routes):
        shown = ", ".join(routes[:15]) + (", …" if len(routes) > 15 else "")
        return f"{label} ({len(routes)}): {shown}" if routes else f"{label}: none"

    # The quick answer first: most comparisons exist to confirm "nothing
    # changed", so say so in one loud line (mirrored by the workbook's
    # Summary verdict; the GUI also keys its result dialog on `verdict`).
    one_sided = counts["t_only"] + counts["n_only"]
    matches = counts["diff_cells"] == 0 and one_sided == 0
    # Unreadable inputs make the comparison INCOMPLETE: a clean match can't be
    # certified, so the verdict is never "match" when files were skipped.
    incomplete = bool(warnings)
    if matches and not incomplete:
        verdict_line = (f"✓ EVERYTHING MATCHES — all {len(union):,} "
                        f"{sc.id_noun_plural} are identical in both "
                        f"{sc.sides_noun}.")
    elif matches and incomplete:
        verdict_line = (f"⚠ COULD NOT COMPARE EVERYTHING — {len(warnings)} input "
                        f"file(s) were unreadable and skipped; the {len(union):,} "
                        f"{sc.id_noun_plural} that WERE compared all match.")
    else:
        verdict_line = (f"✗ DIFFERENCES FOUND — {counts['diff_cells']:,} "
                        f"differing cell(s) on {counts['diff_rows']:,} "
                        f"matched row(s); {counts['t_only']:,} row(s) only "
                        f"in {a}, {counts['n_only']:,} only in {b}.")

    Nouns = sc.id_noun_plural.capitalize()
    lines = [
        verdict_line,
        f"{Nouns} in both {sc.sides_noun}:   {counts['both']:,}",
        f"In {a} only / in {b} only: {counts['t_only']:,} / {counts['n_only']:,} "
        "(each listed on its own 'Only in …' sheet)",
        f"Matched rows with differences: {counts['diff_rows']:,} "
        f"({counts['diff_cells']:,} differing cells); "
        f"{counts['identical']:,} fully identical",
    ]
    if has_route:
        lines += [
            f"Routes covered by both {sc.sides_noun}: {len(r_both)}",
            _route_list(f"Routes only in {a} (missing from {b})", r_t_only),
            _route_list(f"Routes only in {b} (missing from {a})", r_n_only),
            "Those routes' rows are included — tinted 'entire route' on the "
            "'Only in …' sheets; per-route breakdown on the Routes sheet.",
        ]
        if "formulas" in modes:
            lines.append(
                "Note: the live-formulas workbook opens in MANUAL calculation "
                "— press F9 in Excel to calculate (first time takes a few "
                "minutes), then save. The Summary's SELF-CHECK rows should "
                "all read OK." + ("  The values copy opens ready — nothing "
                                  "to calculate." if "values" in modes else ""))
    if incomplete:
        lines.append(f"⚠ {len(warnings)} input file(s) skipped (unreadable) and "
                     "left OUT of this comparison — re-export/repair and re-run:")
        for w in warnings[:20]:
            lines.append(f"    – {w}")
        if len(warnings) > 20:
            lines.append(f"    – …and {len(warnings) - 20} more (see the log).")
    if "formulas" in modes:
        lines.append(f"Live-formulas file: {out_paths['formulas']}")
    if "values" in modes:
        lines.append(f"Values file: {out_paths['values']}")
    primary = out_paths["formulas" if "formulas" in modes else "values"]
    # Incomplete ⇒ never certify a clean match (GUI greens only on "match").
    verdict = "diff" if (incomplete or not matches) else "match"
    return ConsolidateResult(status="ok", output_path=str(primary),
                             summary_lines=lines, verdict=verdict)

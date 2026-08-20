# Comparison speed — the record

**Status: SHIPPED in v0.40.0, extended in v0.40.1.** This is the project
record, not an open plan.

Started on `codex/vs-tsn-comparison-speed` (2026-08-19, four commits), taken over
and reshaped 2026-08-20. Read this before touching `compare_core._styled_cell` or
`artifact_store.comparison_counts`; the behavior itself is documented in
[comparison-engine.md](../comparison-engine.md) §2b.

---

## The goal and the boundary

Make repeated comparisons materially faster. The boundary was never negotiable:
**no optimization may change the produced workbook.** Acceptance is byte-identical
stable OOXML package members plus an exact typed outcome, proved on the real
corpus through the shipped comparators — not on a fixture, and not by reasoning.

That boundary turned out to decide the shape of the whole change. Everything
that satisfied it shipped unconditionally; the one thing that did not was
dropped rather than hidden behind a toggle.

---

## What shipped

### 1. Composite cell styles are registered once

`_styled_cell` is called 1,339,433 times in a statewide Ramp Detail run, and each
call re-walked openpyxl's style descriptors to hash and index components the
writers had already handed out. It now registers each distinct
(font, fill, alignment, border) set once per workbook and copies the resulting
`StyleArray`.

Three properties make that output-neutral, and all three are locked by
`build/check_compare_style_cache.py`:

- each cell owns its `StyleArray` (guards, ditto tint and explicit number
  formats mutate cells after construction);
- the cache is keyed by component identity AND retains the components, so a
  recycled `id()` is impossible rather than unlikely;
- style is bound before the value, because openpyxl sets `number_format` while
  binding a date.

### 2. The commit stops reading its own output through openpyxl — twice

`comparison_counts` now streams the finished package directly — resolving the
Comparison sheet through real relationships, decoding only the cell types the
values contract carries, enforcing the same Status/Diffs schema. On the 30.8 MB
Intersection Detail artifact that is 16.9 s → 5.0 s.

Profiling then turned up the bigger half, which the originating branch did not
see. **`_openable_xlsx` is not cheap**, whatever its docstring claimed
("``read_only`` load is lazy … so it stays cheap even for a big live-formulas
workbook"). openpyxl sizes every read-only sheet the moment it is constructed,
and openpyxl's own write-only writer emits no `<dimension>` — so sizing parses
each worksheet **to its end**. Measured on real artifacts: **10.3 s on the
30.8 MB Intersection Detail comparison, 44.2 s on the statewide 120 MB Highway
Detail one**, on every typed comparison commit.

Since the streamed pass already proves everything that gate proves — openable,
at least one sheet, the Comparison sheet present — a typed comparison's VALUES
artifact now takes ONE package pass instead of an openpyxl load plus a count
read. The gate itself is untouched for everything else (ordinary consolidations
still use it, and it is still what decides a refusal), and its docstring now
says what it actually costs.

It is stricter than openpyxl in several ways, and on a commit gate strictness is
a hazard, not a virtue: refusing a good workbook would stop a real comparison
publishing. So it never decides a refusal — anything it declines falls through
to `_comparison_counts_openpyxl`, which stays the authority on rejection. The
one place the streamed reader could have been LOOSER than openpyxl (cell type
`d`, where openpyxl yields a datetime the Status contract rejects and a text
decode would have accepted it) is refused outright.

`_openable_xlsx` was deliberately left alone: its `read_only` load is already
lazy, and it gates ordinary consolidations too, which should not pay for a full
package walk to answer a question they already answer cheaply.

---

## What was deliberately NOT taken

The originating branch also reused one attempt-local TSN certification, skipping
four `_require_source_identity` checkpoints in `matrix_build` /
`day_matrix` and replacing them with a single guard at the cache `os.replace`.

Its own benchmark priced the entire identity surface at **0.298 s → 0.075 s**.
Against a ~60 s saving on one statewide comparison that is roughly 0.3% of the
improvement, in exchange for weakening the CMP-AUD source-identity contract at
capture, comparison, publish and cache-record. It was dropped whole. Every
checkpoint runs exactly as it did in v0.39.3.

Dropping it had a second effect worth recording: with the identity relaxation
gone, nothing left in the change is a tradeoff, so the **"Fast vs TSN
(experimental)" toggle went too** — along with its setting, both matrix
checkboxes, the mock branch, and the `comparison_serializer` cache-identity
split. A default-off toggle over an output-equivalent optimization is a code
path nobody runs; unconditional means every family benefits (cross-environment,
vs-Baseline, PDF-vs-Excel and the ArcGIS comparisons, not only vs-TSN) and the
whole check suite exercises it.

Also dropped, unstarted from the original plan:

- **A TSN-library normalized-row cache.** Real, but it is a new persistent cache
  with its own identity/version/staleness surface — a separate piece of work
  with its own audit, not a rider on a serializer change.
- **A "Compact comparison" toggle** that would omit audit/duplicate surfaces.
  That is an output-contract change, which is the one thing this project was not
  allowed to do.

---

## Measured (2026-08-20, shipped comparators, values mode)

**Read the method before the numbers.** This box is the owner's daily driver —
`Get-CimInstance Win32_Processor` reported 56% load with no benchmark running
(Discord, Spotify, Chrome, Steam). Single-run absolutes are therefore not
comparable across the session: the same `_openable_xlsx` call on the same 120 MB
artifact measured 44 s, then 71 s, then 79 s. **Alternate the two trees on the
same inputs and take paired medians** — never a before-then-after pair.

| Measurement | v0.39.3 | v0.40.0 | Reduction |
|---|---:|---:|---:|
| Intersection Detail statewide, 3 paired rounds (medians) | 569.9 s | 346.6 s | 39.2% |
| Intersection Detail statewide, quiet-moment pair | 202.6 s | 127.9 s | 36.9% |
| Highway Detail statewide (single runs, load-contaminated) | 813.4 s | 531.4 / 561.5 s | — |
| Comparison counts on the 30.8 MB artifact, back to back | 16.9 s | 5.0 s | 70.4% |
| `_openable_xlsx` on the 30.8 MB / 120 MB artifacts | 10.3 s / 44–79 s | removed from the commit | — |

The two claims that do NOT depend on machine load:

- **Output is identical.** The interleaved run asserted the package digest on
  every one of its six statewide Intersection Detail runs and found ONE distinct
  value. Statewide Highway Detail (48,477 paired rows, 120.6 MB, 27 members) was
  byte-identical to v0.39.3's output. Highway Log route 1 matched in BOTH
  flavors. Blessed canaries unchanged: HD **160,347** differing cells (the
  CMP-AUD-244 figure), ID **21,675 / 687**, HL **969 / 87**.
- **A commit makes ZERO openpyxl loads of its own output**, against two full
  reads before. A count, not a duration — asserted in
  `check_comparison_artifact_schema`.

Inputs: `ground-truth/Intersection Detail Bundle 7.8/intersection_detail` (217
route exports) vs `tsn_library/intersection_detail/raw/TSAR - INTERSECTION
DETAIL_TSN.xlsx`; `ground-truth/HD + HS Release 8.17/2026-08-17
ssor-prod/highway_detail` (252 route exports) vs `tsn_library/highway_detail/raw/
TSAR - HIGHWAY DETAIL_TSN.xlsx`; `ground-truth/inputs/tsmis_highway_log_route
1.xlsx` vs `tsn_highway_log_route 1 v5.xlsx`.

Harness: `build/benchmark_vs_tsn_speed.py` (`--writer historical` swaps
`_styled_cell` back to the pre-cache sequence for the A/B).

---

## v0.40.1 — the duplicate input reads (roadmap E6a)

Both sides were read twice: the loader read the consolidated TSMIS workbook and
the TSN workbook, then the Report View re-opened and re-parsed the same two
files for its own columns — **14.0 s on Intersection Detail, 27.9 s on Highway
Detail**. They now ride the read the comparison already performs.
Interleaved, 3 paired rounds, statewide Intersection Detail: **229.2 s →
191.7 s (16.4%, 1.20x)**, one package digest across all six runs. See
[comparison-engine.md](../comparison-engine.md) §2b for the two rules that keep
it a speed change.

## Where the remaining time goes — measured, and why it stops here

An undistorted phase breakdown of the 129 s Intersection Detail comparison
(wrapping each writer, no profiler):

| Phase | Seconds | Share |
|---|---:|---:|
| `_write_data_sheet` (the two visible source sheets) | 31.0 | 24% |
| `_write_snapshot_sheet` (the two hidden integrity snapshots) | 21.9 | 17% |
| `_write_report_view` | 20.5 | 16% |
| `_write_comparison` | 16.4 | 13% |
| input loading (both sides) | 12.0 | 9% |
| everything else (pairing, diffing, commit, counts, provenance) | 27.3 | 21% |

**Writing is 70% of a comparison, with no hot spot** — four writers, each
serializing content the workbook must contain. The one available lever on the
serializer itself was `lxml` (openpyxl uses it when installed): measured, it
produces **different bytes** and is worth **~2%**, so it fails the acceptance
bar and buys nothing, quite apart from adding a compiled dependency to the
frozen work-PC bundle.

So the tuning is finished. The only change left that is worth an order of
magnitude is **not writing a workbook at all** — a matrix refresh that
recomputes a cell's verdict and counts and skips serialization. That is a
product decision, not a performance one: the matrix's green state is bound to a
committed artifact generation, so a counts-only result cannot be recorded as a
normal cached cell and would need its own clearly marked, non-certifying state.
The roadmap carries that note under section E.

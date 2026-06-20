# Per-report TSN formats & comparison schemas

The single home for what we learn about each report's **TSN** source — its file
format, how its columns map to the TMSIS export, the comparison **key**, the
normalization rules, any ditto/roadbed analog, and the **approved sample counts**
that lock the comparator. This is the cross-report sibling of the Highway Log deep
dives (which stay under [highway_log/](highway_log/columns.md)).

**Status:** stubbed for the **v0.17.0** effort. Each section below is filled in from
the **raw ground-truth files** (the TSN *and* TMSIS version of every report) as that
report's consolidator + vs-TSN comparator is built and audited flawless. Until a
section is filled, that report shows greyed in the vs-TSN matrix. Process + audit
recipe: [v0.17.0-prompt.md](v0.17.0-prompt.md) and
[verification-and-testing.md](verification-and-testing.md).

> **Rule (from [lessons.md](lessons.md)):** consolidate/compare **from raw**, and
> reconcile both files **by hand first** — the schema comes from the data, never a
> guess. The TMSIS website source + the raw files (LOCAL ONLY under
> `C:\Users\Yunus\Downloads\TSMIS\…`) are the ground truth; never commit them.

## Per-report record (fill during 0.17.0)

For each report, record: **TSN format** (PDF/XLSX, per-route vs per-district, single
sheet vs many) · **column → TMSIS mapping** (a table) · **comparison key** (route /
PM / county / composite) · **normalization** (zero-padding, date→ISO, whitespace,
case) · **ditto/roadbed analog** (does the `+`/`++` or roadbed split apply?) ·
**drop folder** (`input/tsn_<subdir>/` or a file pick) · **consolidator** module ·
**comparator** module + `CompareSchema` · **golden check** · **approved counts** (the
report's own "Route-1 canary" — the first user-approved sample, never to regress).

### Ramp Summary — TSN
- **TSMIS side:** standalone PDF parse (`consolidate_ramp_summary.parse_pdf`, word-position; 14 ramp types × 6 highway groups × on/off × population groups). Key = route.
- **TSN format:** _TBD — inspect raw file._  **Open Q:** does a TSN ramp-type/count doc exist in the same shape (per-route? per-district? same 14×6×3×5 schema)?
- Mapping / key / normalization / ditto / counts: _TBD._

### Ramp Detail — TSN
- **TSMIS side:** per-route XLSX, sheet `TSAR - Ramp Detail`, consolidated via `consolidate_xlsx_base`. Comparison key = **PM** (postmile), not the coarse first column.
- **TSN format:** _TBD — inspect raw file (XLSX? PDF? sheet name? columns?)._
- Mapping / key / normalization / counts: _TBD._

### Highway Sequence Listing — TSN
- **TSMIS side:** per-route XLSX, sheet `Highway Locations`, consolidated via `consolidate_xlsx_base`. Comparison key = **PM**. Note: some TMSIS columns are **unnamed** → `compare_env` labels them `(col X)`; a TSN consolidator must align/label the same way.
- **TSN format:** _TBD — inspect raw file._
- Mapping / key / normalization / counts: _TBD._

### Intersection Summary — TSN
- **TSMIS side:** XLSX export, **sheet name UNCONFIRMED** (check the real export / the website source) — no consolidator exists yet.
- **TSN format:** _TBD — entirely unknown; inspect raw file._
- Consolidator / mapping / key / normalization / counts: _TBD._

### Intersection Detail — TSN
- **TSMIS side:** XLSX export, **sheet name UNCONFIRMED** — no consolidator exists yet. Likely carries a free-text **Description** column → formula-injection guard required.
- **TSN format:** _TBD — entirely unknown; inspect raw file._
- Consolidator / mapping / key / normalization / counts: _TBD._

### Highway Log — TSN (reference, already built)
Fully documented elsewhere — this is the recipe the others follow:
- Format + parsers: [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (TSN char-window parser + the 3 description guards).
- 31 corrected columns: [highway_log/columns.md](highway_log/columns.md).
- The `+`/`++` ditto domain + roadbed split: [highway_log/comparison-study.md](highway_log/comparison-study.md).
- Approved canary: **Route-1 = 299 both / 969 diff cells** (never regress; see
  [verification-and-testing.md](verification-and-testing.md)).

# Changelog

All notable changes to TSMIS Reports Exporter, newest first. Each GitHub
release shows only its own section (see `build/gen_release_notes.py`).

## Unreleased — ships with the comparison-perfection completion release

### Changed
- **Evidence images now come with a complete difference ledger.** The evidence
  workbook has a new **Ledger** sheet listing, for every compared column, how
  many differences the comparison counted, how many of those sit on a row that
  can be photographed on its own, how many sit inside a repeated postmile, plus
  the context, identical and one-sided cell counts and the whole row universe.
  The pictures illustrate that record — they no longer stand in for it. Each
  example also names the exact Comparison row, occurrence and state it came
  from, and the two source rows behind it, so a reviewer can jump straight from
  an image to the cell it proves.

### Added
- **Evidence for the PDF-vs-Excel self check.** Comparing a report's two TSMIS
  editions against each other can now produce images like every other
  comparison: the PDF side as a highlighted page snippet, the Excel side as its
  own workbook cell. Turn Evidence images on and build the comparison.

### Changed
- **Excel comparisons are illustrated from the Excel export.** Evidence used to
  draw the TSMIS side of every comparison from the printable PDF edition, even
  when the comparison had read the Excel export — and it silently skipped any
  value where the two editions disagreed. So the differences most worth seeing,
  the ones the print doesn't carry at all, were exactly the ones that never got
  a picture. An Excel comparison now shows the workbook cell it actually
  compared, named down to the sheet and cell reference so you can open it and
  look. Excel-side runs are also much faster: they no longer open all 252
  companion PDFs to illustrate a workbook.
- **Every evidence set now says which comparison it belongs to.** A small
  `(evidence).json` record beside the comparison names the exact comparison,
  the source files the pictures were taken from, and every image it published.
  If you rebuild a comparison without regenerating the images, the leftover set
  is recognisable as belonging to the previous one instead of looking current.

### Fixed
- **Evidence images and their workbook can no longer disagree.** If the images
  folder was open when a refresh finished, you could end up with a new evidence
  workbook sitting beside the previous run's pictures. Both now publish
  together or neither does: the previous set stays exactly as it was and the
  new one is saved alongside with a note.
- **A run that finds nothing to illustrate now records that.** Previously, when
  a rebuilt comparison had nothing photographable, the old images were simply
  left where they were. The prior set is now retired and the run records what
  it found, so "nothing to illustrate" and "images were never generated" are
  no longer indistinguishable.
- **Evidence no longer says "no differing columns" when there are some.** When
  every difference in a column happened to sit at a postmile that repeats, the
  images step reported nothing to illustrate — which read as "the two systems
  agree". It now reports the column, the count, and why no single row could be
  photographed for it.
- **Evidence is checked against the comparison it illustrates.** Every candidate
  image is matched to the published cell it claims to show and is dropped unless
  the comparison independently agrees the cell differs and holds the same
  values. Previously the images were produced by re-reading the two reports a
  second time, so a reading mistake could show up identically in the comparison
  and in its "proof".
- **A broken export can no longer destroy a good consolidated workbook.** If a
  report had been consolidated successfully and you then re-ran it with one
  route's export damaged, the partial rebuild replaced the good workbook — the
  routes that had been in it were simply gone, and the comparison that followed
  diffed the reduced file. The consolidated workbook is now the last COMPLETE
  one: a rebuild that comes back incomplete keeps the good file untouched, saves
  what it managed to build beside it as a clearly-named `(attempt)` copy you can
  open, and tells you which exports to fix. Nothing is compared until the
  rebuild completes, so a stale-but-complete workbook is never quietly diffed
  against today's exports either. The first time you consolidate a report there
  is nothing to protect, so a partial first build still lands and is still
  flagged amber.
- **A rebuild that failed or was stopped no longer disappears from the grid.**
  Refreshing a comparison that then crashed, or that you cancelled, left the
  previous green cell exactly as it was the moment the grid redrew — the failure
  survived only as a line in the log. Each cell now remembers its last refresh
  attempt across restarts: the previous result stays visible and unchanged (it
  is still the last good answer), with a marked edge and a "last refresh failed
  / stopped / incomplete" note until a successful rebuild replaces it. The
  end-of-run message counts what actually happened — attempted, succeeded,
  failed, cancelled, incomplete — instead of reporting a cancelled cell as done.
- **Changed source files can no longer hide behind an unchanged timestamp.**
  Freshness compared file names, sizes and timestamps, so a route file replaced
  with different content of the same length and its timestamp put back looked
  untouched and the old "match / 0 differences" stayed green. Freshness now
  reads the files' actual content, with a per-file cache validated against a
  Windows change signal that a restored timestamp cannot fake, and which is not
  trusted for a file that changed in the last second — measured on a full
  statewide export folder, this costs about as much as the old check once warm.
  The same fix applies to the cached TSN print used for evidence images. The
  first refresh after updating re-checks every report once.
- **A comparison workbook that could not be read is now refused instead of
  saved.** A comparison whose sheet was missing its `Status`/`Diffs` columns —
  or had no rows at all while reporting rows — could still replace a good
  workbook and then read as an empty, unusable result in the matrix. Such a
  workbook is now rejected at save time with a clear message, and the previous
  file is kept.
- **Comparisons now publish from any install folder — the 260-character Windows
  path limit no longer hides them.** The v0.27.0 field failure (every by-day
  comparison built its workbook and then vanished from the matrix) came down to
  one filename: each comparison stores its trust metadata in a content-addressed
  sidecar whose name was ~167 characters, so at a normal install depth the full
  path passed 260 characters. A managed work PC cannot lift that limit, the
  metadata write was refused, and the matrix — correctly — declined to show a
  comparison it could not certify. The workaround was moving the whole app to a
  short path like `C:\TSMIS`. The sidecar names now carry 16-character
  abbreviations of their two digests instead of the full 64 (the full digests
  are still recorded and verified inside the metadata itself, so nothing about
  integrity checking changed), which keeps the deepest published path well under
  the limit at the real install depth. Existing comparisons written under the
  old long names remain fully readable; the next rebuild of a comparison simply
  publishes under the short names. The moved-to-`C:\TSMIS` workaround is no
  longer necessary, and the release gate now proves the fix unconditionally —
  including on machines where long paths are allowed and the old test could
  never fail.

## v0.27.4 — 2026-07-21

### Fixed
- **A rebuilt TSN report stayed "consolidated STALE" forever.** Rebuilding the
  Highway Log library succeeded every time — 380 files, 60,083 rows, nothing
  skipped or failed — and the report still read out of date one second later, so
  "rebuild it" was advice that could never work. The library build writes an
  authoritative build record holding the normalizer version, the raw-source
  manifest and two identity bindings, and verifies it. The consolidation driver
  then wrote its own generic build record **over** it, which cannot reconstruct
  any of those four facts — so the normalizer version vanished and the freshness
  check correctly refused a record that no longer had one. Comparisons were
  already exempt from that second write; the TSN library build is now exempt on
  the same basis. Any producer that publishes its own verified record keeps it.

  After updating, rebuild each affected TSN report **once** — the stale reading
  was the record, not the workbook, and this time it will clear and stay clear.

## v0.27.3 — 2026-07-21

### Fixed
- **"Built by an older normalizer" now says which versions.** A Highway Log
  rebuild that completed cleanly — 380 files, 60,083 rows, nothing skipped or
  failed — still reported the report as out of date, in the same second, and
  again after a restart. "Rebuild it" is useless advice when a rebuild has just
  run. That verdict is a single yes/no built from two numbers that were never
  shown: the normalizer version recorded when the library was built, and the
  version this app expects. Both are reported now, and three cases that used to
  read identically are distinguished — a genuinely older stamp ("built by
  normalizer version 3, this app expects 5"), a build record carrying no version
  at all, and a version stored in an unusable form. No freshness logic changed;
  the same libraries are current as before.

## v0.27.2 — 2026-07-21

### Fixed
- **A TSN report that isn't current now says why.** "consolidated STALE" was one
  word covering eight independent conditions, so a library that had never been
  built, one built by a superseded normalizer, one whose raw files had changed,
  and one whose build record no longer matched its workbook all looked identical
  — and none of them said what to do. Reported from the field: a Highway Log
  rebuild that completed cleanly (380 files, 60,083 rows, nothing skipped or
  failed) still read STALE afterwards, with no way to tell why from the panel.
  The freshness check already decided every condition separately and simply
  discarded the answer at the display boundary. Each report now reports the first
  failing condition, in plain terms and with the action it implies, on the panel
  and in the log. **No freshness logic changed** — exactly the same libraries are
  current as before; only the explanation is new.

### If the vs-TSN matrix shows no comparisons
Unchanged from v0.27.1, repeated because it is the most likely thing you will
hit: comparison workbooks build correctly but the matrix hides them when their
trust metadata cannot be written, and the usual cause is the Windows
260-character path limit. This is now confirmed from a real install
(`path_len=265`). **Move the app to a shorter folder path** — for example
`C:\TSMIS\TSMIS Exporter\` — and re-run. The comparison workbooks themselves are
valid and readable under `output\comparisons\tsn-by-day\` in the meantime. A
permanent fix that shortens the internal file name is in progress.

## v0.27.1 — 2026-07-21

Diagnoses the v0.27.0 field failure where **every comparison built but never
appeared on the matrix**, and fixes four smaller things reported alongside it.

### If your comparisons stopped appearing on the matrix — read this
The comparison workbooks were built correctly and are still on disk; only the
trust metadata beside them failed to publish, and the matrix refuses to show a
comparison it cannot certify. You can open the workbooks directly under
`output\comparisons\tsn-by-day\`.

The likely cause is the **Windows 260-character path limit**. v0.27.0 writes a
content-addressed sidecar whose file name is long, so on a deep install path —
for example under `Downloads\Apps\…` — the full path can exceed 260 characters.
A PC without long-path support (the default on managed machines, and not
changeable without an administrator) refuses the write, and v0.27.0 reported that
only as "could not be safely published".

**The workaround is to move the app to a shorter folder path** — something like
`C:\TSMIS\TSMIS Exporter\` — and re-run the comparison.

This release does **not** yet shorten the sidecar name; that changes a persisted
format and is being done separately with a full re-verification. What it does is
make the failure name itself, so the log now says exactly which file failed, how
long its path was, and what to do about it.

### Fixed
- **Comparison publication failures are diagnosable.** Every fail-closed gate in
  the publication path — about seventeen of them — used to return silently, so a
  field failure left nothing in the log. Each now names the gate it stopped at
  and prints the values that decided it (which member, which phase, the
  before/after sha256, size and mtime, and the full path with its length). A
  refusal caused by the path limit says so and names the remedy. No gate changed
  what it accepts or refuses; only the refusal became answerable.
- **The TSN reports panel stayed STALE after a rebuild.** The panel refreshed
  only when its own Rebuild button started the work. The comparison matrix
  rebuilds an out-of-date TSN dataset on its own before comparing, and that path
  never triggered the refresh — so Highway Log and Highway Sequence kept reading
  STALE until the app was restarted. The refresh now follows the rebuild
  finishing, whoever started it.

### Added
- **Rebuild all out of date** (Settings ▸ TSN reports). After an update moves a
  normalizer version, every affected report reads out of date and had to be
  rebuilt one at a time. The new button does them in a single run, targeting
  exactly the reports the per-report Rebuild would, and reports the first failure
  rather than the last result so an early failure cannot hide behind a later
  success. Nothing out of date disables the button instead of reporting an error.
- **The TSN panel reports evidence prints too.** A report can need two separate
  things: the raw files its consolidated workbook is built from, and the TSN
  prints the evidence images are cropped from. The panel only showed the first,
  so "all green" said nothing about whether evidence could render. Each report
  now also reports its prints — present, missing, or covered by the same raw it
  already builds from (Highway Log and Highway Sequence, which never need a
  second copy).
- **The background sign-in check announces itself.** On startup the app quietly
  checks the saved sign-in, and that check holds the single-task slot — so a
  click during it was refused with "try again in a few seconds" and no visible
  reason. It now says when it starts and when it finishes.

## v0.27.0 — 2026-07-19

Evidence images become configurable, and the comparison engine lands the first
large batch of the source-first correctness audit — 219 of 241 findings closed
across the comparison, matrix, TSN-normalization and PDF-identity paths. **Several
comparisons now report different — more correct — numbers than v0.26.2**, and the
TSN libraries rebuild once on first use. Read "After updating" at the end of this
section before reconciling anything against an older run.

### Added
- **Pick the evidence image layout.** The evidence controls on both comparison
  matrices (vs TSN and by-day) carry a layout dropdown beside the "generate
  images" toggle: **side by side** (the default), **stacked**, or **both**. Only
  the layout(s) you pick are rendered — choosing one instead of both roughly
  halves the image count and the render time for a large evidence set. The choice
  persists across runs and is captured when a job is queued, so changing it
  mid-queue can't retarget work already in flight.
- **The evidence workbook splits its examples by comparison column.** Instead of
  one combined sheet of every sampled difference, the workbook now opens one tab
  **per comparison column** (Description, Length, ADT…), each holding just that
  column's examples. Sheet names are de-duplicated and legal, and the Summary tab
  lists which layouts were rendered.

### Changed — comparison results change
These are corrections, not regressions: each was proved cell-for-cell against an
independent oracle and both workbook flavors on the real statewide corpus. Counts
that differ from a v0.26.2 run differ because the old number was wrong.
- **Highway Sequence pairs on physical identity, and "PM Suffix" is a compared
  column.** PDF↔Excel rows now pair on route/county/prefix/base postmile with the
  suffix asserted rather than folded, making the statewide corpus exact:
  60,493 paired / 0 PDF-only / 1 Excel-only.
- **Highway Sequence Descriptions compare verbatim.** The old symmetric strip rule
  removed text the TSN extract genuinely carries (including its 154 numeric
  prefixes); TSMIS strips only its own-route label. Both sides are now compared as
  printed.
- **Duplicate rows are assigned by a typed, auditable objective.** When a key
  matches several rows, occurrences are paired by minimizing an approved
  source-identity tuple (compared-field differences, then character edit distance,
  then position gap) instead of file order — context and ditto cells decide *which*
  occurrences correspond, while verdicts and counts stay assertion-only. Above the
  100,000-cell cap the output is explicitly partial diagnosis and can never read
  green.
- **The TSN Highway Log and Highway Sequence normalizers were rebuilt from raw
  source.** Highway Log v5 keys detached suffixed-route group headers ("07 LA 005 S")
  as the suffixed route — 317 statewide rows are no longer misattributed — and
  conserves asterisk-leading printed Descriptions (four statewide rows that were
  each a manufactured false difference). Highway Sequence v4 is source-exact at
  69,804 rows including the 46 blank-county equates and 565 pointer tokens.
- **A PDF's own route claim is authoritative.** All five PDF converters and the
  evidence adapters read identity from the document itself (page banners, the
  Intersection Detail cover parameter, the Highway Log cover line) instead of
  inferring it from the filename, and refuse duplicate or blank route claims by
  naming both source PDFs. Verified refusal-free across all 1,099 statewide
  per-route documents.
- **PDF-vs-Excel self-checks project both sides verbatim.** The same-source flavors
  no longer rewrite values for display — Highway Detail surfaces "PM (raw)" and
  verbatim NA, Highway Log surfaces "Location (raw)", and Intersection Detail's
  J→S fold is gone — so a self-check reports what the two files actually say.
- **Ramp Detail postmiles are canonical.** `9.6`, `9.600` and `009.600` are one
  ramp for physical identity (statewide census: zero pairing changes, 1,755
  display texts canonicalized), and the vs-TSN loader decodes the Excel export's
  OOXML escapes so encoding artifacts stop reading as data differences.

### Fixed
- **Evidence images no longer invent differences.** Every adapter now enumerates
  differences through the comparison's own `compared_cell` decision, so
  Excel-trimmed whitespace, Med-Wid equivalents and context/ditto cells can't be
  sampled as diffs.
- **Evidence is bound to the exact PDFs it was rendered from.** Candidate PDFs are
  digested before parsing and re-verified before publishing, so a same-size,
  same-timestamp file swap mid-render aborts instead of shipping mismatched images.
- **A clean rebuild retires its stale evidence.** When a rebuilt comparison has no
  differing columns, the previous run's red evidence workbook and image folder are
  removed instead of being left behind to look current.
- **The evidence workbook and its images publish as one set.** If the workbook is
  locked (open in Excel), the images divert alongside it, so you can never end up
  with a new workbook pointing at old images or the reverse.
- **Matrix and by-day cells report honestly.** Real day-folder identity and source
  reconciliation, a locked running-day removal, an accurate consolidation badge,
  correctly scoped rebuilds, a both-missing state, and the captured run date
  threaded end to end. Caches invalidate on a semantic producer version, and
  formula twins are bound to the generation that produced them.
- **Compare-tab dispatch matches what the buttons promise.** One shared
  buildability predicate behind the bulk selector, the explicit Build button and
  the queue; canonical TSN consolidate routing by origin; a Cancel lock on the
  Compare sub-tab; a queue-capable day export; and classic comparison inputs bound
  to their recipe with a preflight.
- **An auth or browser failure keeps runnable offline jobs** in the queue instead
  of clearing them.
- **A folder comparison refuses a run-root vs its own report-subfolder alias**
  (statewide census: zero false rejections).
- **The Highway Log PDF parser recovers asterisk-leading Descriptions** — the
  mirror of the TSN fix — dropping the statewide Description difference class from
  5 to 1.
- **Spot Check matches rows independently.** It key-token-matches both source rows
  itself and flags any disagreement with the Comparison sheet's stored links or
  status, so a forged row link reads CHECK.

### After updating
- **The TSN libraries rebuild once** on first use (Highway Sequence v4, Highway Log
  v5, Ramp Detail v5, Intersection Detail v5, Highway Detail v3). The vs-TSN
  comparisons refuse a pre-current library with a rebuild hint rather than
  comparing against stale normalization.
- **PDF-sourced workbooks made before this version re-consolidate once** — every
  PDF-sourced workbook now carries a conversion marker that the TSMIS (PDF)
  comparison role requires and the TSMIS (Excel) role rejects.
- **Don't reconcile this version's comparison counts against a v0.26.2 run.**
  Re-run both sides on this version first; the differences listed above are
  intentional corrections.

## v0.26.2 — 2026-07-10

### Fixed
- **Highway Log (PDF) days no longer read "inputs incomplete" for a routine
  print artifact.** A Highway Log print page whose only data rows are unshaded
  carries no cell-rectangle band of its own (plain zebra-row parity, ~280 pages
  per statewide export), so the parser reads it with the previous page's column
  geometry — and since v0.19.0 ANY such page conservatively marked the whole
  consolidation partial, which turned every Highway Log (PDF) matrix cell amber
  ("inputs incomplete") even though nothing was missing. The carry is now
  VALIDATED per page instead of blanket-flagged: every printed token's
  characters must land inside one column window (the same char-center test the
  parser assigns by) and the row's Location cell must still be a clean postmile
  token. A validated page is ordinary output (an info line reports the count);
  only a page whose text genuinely does not fit the carried geometry — a
  changed table layout — keeps the ⚠ warning and the partial flag. Verified
  statewide on two full export sets (551 carried pages, all validated; emitted
  rows byte-identical to the previous parser on every affected route; both
  end-to-end consolidations complete). After updating, force one re-consolidate
  per amber day column (the day header's consolidate badge) — the cell then
  clears to its real green/red.

## v0.26.1 — 2026-07-10

### Fixed
- **Evidence images: invisible quote-character differences are now labeled.** A
  difference whose two values differ only in quote characters — a doubled apostrophe
  (`''F'' ST`) on one side vs a real quotation mark (`"F" ST`) on the other — prints
  near-identically, so the evidence header looked like it flagged two equal values
  (field report: the Intersection Detail Description at KER 046 @ 50.904, the single
  such row statewide). The difference is real — the systems genuinely store different
  characters — and the image header now says so on a dark-red third line naming both
  sides' characters in words; the evidence workbook captions carry the same note. The
  Intersection Detail comparison's Notes sheet documents that quote characters compare
  literally (both systems share the `''X''` convention on every other quoted-letter row,
  so no normalization is applied — folding would hide a genuine data edit).

## v0.26.0 — 2026-07-10

Ramp Detail (PDF) — the last export-only print edition — is now fully integrated:
it consolidates, compares against TSN and against its own Excel edition, lives in
both matrices, and renders evidence images. Blessed on the first real work-PC print
set (`All Reports 7.9`, 126 routes): every one of its 15,216 rows parses back
row-for-row against the same-day Excel exports. This release also adds a third
comparison matrix — **vs Baseline** — that diffs any exported day of a report
against an earlier pull of the same report, and fixes the evidence images'
cropped snippets.

- **New: the "vs Baseline Matrix"** (Compare tab, beside the vs TSN Matrix). Rows =
  all 12 comparison-integrated reports, columns = exported days you add, each cell =
  that day's export compared against a **baseline** you pick — an earlier day's run
  folder, or the Export-Everything store — for the same source. Same format on both
  sides by construction (Excel vs Excel, PDF vs PDF: each row reads its own report
  subdir on both sides). The baseline picker shows how many reports each candidate
  day holds ("2026-06-11 · 9/12 reports"), missing copies render per cell, and the
  baseline's own column is marked. No consolidation and no TSN dataset needed — the
  per-route files are read straight from both folders, exactly like the classic
  cross-environment compare, and each cell writes the same discrepancy workbook
  (optionally with a live-formulas copy) into
  `output/comparisons/baseline-by-day/`. Switching baselines never clobbers another
  baseline's comparisons — each is its own artifact.
- **Evidence images no longer crop the interesting part.** Each snippet is now a
  full-width band of the page instead of a crop hugged to the record's own text —
  previously a difference on a BLANK cell could have its red box clipped off the
  image's edge (Highway Sequence showed it most), and neighbor rows' longer text
  was cut mid-word. Verified on 99 regenerated examples across Highway Sequence and
  Ramp Detail, both layouts; all five evidence reports inherit the fix.
- **New: one-click website source capture** (Settings ▸ "Capture website source").
  Signs in with the saved session, opens the current site's report page, and saves
  the rendered page, the raw HTML, and every same-origin script/stylesheet into a
  dated folder under `output/site-capture/` with a manifest — the manual
  devtools ▸ Sources download walk, automated. The capture is local diagnostic
  data for the maintainer; the app never bundles or uploads it.
- **Highway Detail (PDF) parses the July-2026 prints completely.** On the first
  real prod print set, three record shapes the parser had never seen dropped 254
  records as "unpaired lines" (the consolidation went partial): rows whose roadbed
  blocks carry codes but no effective dates, rows whose printed date lands across
  a shifted column grid, and outdented equate descriptions that START with a
  postmile-shaped token (each previously orphaned the real record and minted a
  phantom one). All three parse now and a record that genuinely prints no
  attribute line would be kept with blank attribute columns instead of dropped.
  Re-verified statewide on the same 252-print set: the consolidation completes
  cleanly (0 unpaired lines, was 254 + partial), 50,171 of 50,730 matched rows
  fully identical to the same-day Excel export, and the leftover one-sided rows
  fell from an unattributable 1,273 to 1,019 — nearly all the new sparse
  attribute-only rows at repeated postmiles, where the two renders' duplicate-row
  pairing differs; each is listed on the workbook's "Only in …" sheets.

- **TSMIS Ramp Detail (PDF) consolidator.** Parses the per-route prints into the
  Excel export's exact column layout — plus the two columns the print carries that
  the **Excel export drops**: the On/Off indicator and the Ramp Type letter. The
  print also renders empty fields visibly ("-" marks and a "NO RAMP LINEAR EVENT"
  message on the 59 statewide ramp points without linework) where the Excel leaves
  blanks; values are kept verbatim in the workbook and projected at compare time.
- **Two new comparison flavors.** TSMIS (PDF) vs TSN — where On/Off and Ramp Type
  are actually COMPARED against TSN's database (the Excel edition has nothing to
  compare there; ~151 more verified cells statewide) — and TSMIS (PDF) vs TSMIS
  (Excel), the internal consistency check: on the same-day statewide pair,
  **15,212 of 15,216 ramps fully identical, zero one-sided** — the only 4
  differing cells are literal "_x000d_" line-break escapes the Excel carries and
  the print omits.
- **Evidence images for both Ramp Detail rows.** The statewide TSN Ramp Detail
  print (500 pages) is indexed once and each differing cell renders as highlighted
  snippets from both prints, parse-back-verified (the TSN template censused
  400/400 records against the raw extract). The TSN Ramp Detail library gains
  District/County evidence columns (normalization v3 — rebuilds itself on next
  use).
- Matrix rows in BOTH matrices (cross-env / vs TSN / vs TSMIS Excel), the
  Consolidate-tab + console-menu entries, and the picker/coalescing behavior
  carried over unchanged.

## v0.25.2 — 2026-07-09

Hotfix for a field crash: exporting both editions of a report together (outside fast
mode) crashed immediately with "TypeError: expected str, bytes or os.PathLike object,
not NoneType" — before the browser even opened.

- **Coalesced exports work from the plain Export tab again.** Selecting an
  Excel + PDF pair of one report in a normal (sequential) export crashed while
  working out the output folders; the bug had been latent since coalescing shipped in
  v0.19.2 because fast mode runs editions separately and Export Everything supplies
  its own folders — a plain paired export was the one path that tripped it. Each
  edition now falls back to its dated run folder exactly like a single-report export.
  Locked by a new regression test.

## v0.25.1 — 2026-07-09

Every enabled report now exports in BOTH formats the site offers, and the site's
brand-new Route History Table shows up in the picker (greyed) so you know it exists.

- **TSAR: Ramp Summary (Excel).** Ramp Summary was the one report the app could only
  save as a PDF — yet the site's action bar has always had an Export button for it.
  It's now wired: a new "Summary (Excel)" edition under the Ramp group saves the same
  count tables as a per-route workbook. Selecting both Ramp Summary editions generates
  each route once and saves both files off it, like every other edition pair.
- **Intersection Summary (PDF).** The last report without a print edition gets one: a
  new "Summary (PDF)" edition under the Intersection group captures the site's own
  Print layout (cover page + the count tables) as a portrait Letter PDF, matching how
  the other five print editions mirror their Excel siblings. Coalesces with the Excel
  edition too.
- **Route History Table appears — greyed.** The TSMIS dev site added a "Route History
  Table" report on 2026-07-09. It isn't exportable (on the site it's an embedded
  report-server page with no export control), so the app lists it greyed in the picker
  — you can see the site gained it, and the moment the site gives it an export path a
  future update can turn it on without re-plumbing anything.
- Both new editions are export-only for now (their siblings already consolidate and
  compare the same data); they appear in Export Everything automatically.

## v0.25.0 — 2026-07-09

The Highway Sequence Listing (PDF) edition grows up — parser, comparisons, matrix row,
and evidence images, all verified against the first real statewide print set — and the
Intersection Summary consolidator absorbs the site's July rename before it could
mis-count anything in the field.

- **Highway Sequence (PDF) is fully integrated.** The print edition added in v0.24.0
  now consolidates ("TSMIS Highway Sequence (PDF)" on the Consolidate tab and in the
  console menu), compares, and appears as its own row in BOTH matrices with the full
  three modes: cross-environment, vs TSN, and vs TSMIS Excel. The parser was
  censused-first against the entire 252-route statewide set from a real work PC and
  parses back against the Excel edition at 60,493/60,493 rows — every residual
  difference class is explained and documented in the comparison's Notes sheets.
- **The print catches what the Excel export drops.** The statewide census found a
  location whose Description the Excel export silently omits while the print carries it
  (route 037 at postmile 003.809) — exactly the defect class the PDF↔Excel self-check
  exists to surface, and the same reason the Highway Log's PDF edition was born.
- **The PDF edition actually pairs BETTER against TSN.** The site's print renders
  equate points the same way TSN's own prints do (an "EQUATES TO …" annotation row plus
  the "E" suffix on the equated postmile), so the Excel edition's by-design "H ≠ blank"
  feature-type class largely disappears: statewide, 434 more locations match and ~600
  fewer cells differ than the Excel-vs-TSN comparison. Each flavor's Notes sheet
  explains its own by-design classes.
- **Evidence images for the Highway Sequence.** Both Highway Sequence rows can now
  render sampled vs-TSN differences as highlighted snippets from both PDFs — the same
  parse-back-verified workflow as Highway Detail, Intersection Detail and Highway Log.
  No new drop folder: the TSN side reads the SAME district prints your TSN Highway
  Sequence library is already built from (`tsn_library/highway_sequence/raw`), so if
  your vs-TSN comparison works, evidence is ready today.
- **Intersection Summary survives the July site update.** The site renamed one block
  header ("MAINLINE MASTARM" → "MAINLINE MASTERARM"), which silently emptied that block
  and mis-filed its "no data" count under Lanes when consolidating a fresh export. The
  parser now accepts both spellings (all workbook text keeps the original), verified on
  a fresh 217-route statewide export. And because that failure was silent, the
  consolidator gained a tripwire: every category block must sum to the route's total
  intersections (they all do, statewide, in both eras — except Highway Group, which the
  site itself under-counts and is exempt), so a future renamed header or brand-new code
  fails loudly with the block named instead of writing wrong numbers.

## v0.24.0 — 2026-07-09

Highway Log joins the evidence-images club, two new PDF print editions arrive, every
vs-TSN comparison got a standards audit against fresh statewide data, and the evidence
toggle now explains itself report by report.

- **Evidence images for the Highway Log.** Both Highway Log rows (Excel and PDF-sourced)
  can now render sampled vs-TSN differences as highlighted snippets from both PDFs —
  the same parse-back-verified workflow as Highway Detail and Intersection Detail,
  ditto-aware (a `+`-run "see paired roadbed" cell is never sampled, exactly as the
  comparison never counts it). No new drop folder: the TSN side reads the SAME district
  prints your TSN Highway Log library is already built from (`tsn_library/highway_log/raw`),
  so if your vs-TSN comparison works, evidence is ready today. The TSMIS side illustrates
  from the Highway Log (PDF) export, like the other reports.
- **Two new print editions: Highway Sequence Listing (PDF) and TSAR: Ramp Detail (PDF).**
  The same on-site reports as their Excel siblings, saved via the site's own Print layout
  (portrait for the Sequence Listing, landscape for Ramp Detail — matching their TSN
  prints). Ticking an Excel + PDF pair still generates each route once and saves both
  files. Export-only for now: their print-layout consolidators, comparisons, and evidence
  come once real work-PC PDFs verify the parse (the same staged path Highway Detail took).
- **The evidence toggle is no longer a mystery switch.** Both matrix pages now list, under
  the toggle, exactly what it will do: a ✓ line per report whose TSN prints are in place
  ("will generate"), a ○ line naming the exact drop folder for one that isn't, and one
  line naming the reports with no evidence support at all. Supported rows also carry a
  small camera badge on their row header (lit = ready, dimmed = tooltip names the folder),
  so you can tell at a glance — before running anything — which comparisons get images.
- **Comparison audit against fresh statewide data.** The Highway Sequence Listing
  comparison was re-verified end-to-end on a fresh 2026-07-08 statewide export (252
  routes): the TSN district-print parser reproduces the installed library byte-for-byte,
  and every count lands within a hair of the blessed baseline (the deltas are exactly the
  ~54 locations TSMIS added since June). A census of its differing cells confirmed the
  known classes — no new artifacts. Its Notes sheet now also explains why nearly all FT
  differences are the by-design "EQUATES TO" pairings.
- **Ramp Detail comparison hardening.** Its notes are now a proper Notes sheet in the
  workbook (key, normalizations, why the four TSN-only columns are context-only); a
  stale TSN library can no longer feed unnormalized postmiles/dates through the
  comparison (they re-normalize at compare time, proven a no-op on a fresh library across
  15,410 real rows); and the consolidated-workbook gate also checks width, not just the
  PM label. Ramp Summary's familiar sheet gained its own notes (the P/V dummy classes and
  the TSMIS-only footnote). No comparison numbers change.
- **Small clarity fixes everywhere.** A disabled "Create comparison…" button now says why
  on hover; the (PDF) editions in the report picker explain what a print edition is; and
  the Compare tab's "What you'll get" mentions the evidence-image workflow and where it
  lives.

## v0.23.0 — 2026-07-08

- **Evidence images on demand — no re-compare.** Every built, up-to-date vs-TSN cell of an
  evidence-capable report (Highway Detail, Intersection Detail) now has a camera action on both
  matrix pages: it generates — or refreshes — the "… (evidence).xlsx" and image folder for that
  cell's EXISTING comparison, without re-running the comparison and regardless of the "Evidence
  images" toggle. Use it when you compared with the toggle off, want a different example count,
  or just dropped the TSN prints in.
- **It refuses to lie.** If the exports, the consolidated workbook, or the TSN workbook changed
  since the comparison was built, the action declines with a "refresh the comparison" message
  instead of rendering images for a diff set the workbook doesn't carry. The camera only appears
  on fresh cells of reports whose TSN prints are in place.

## v0.22.1 — 2026-07-08

- **Both image layouts in the evidence workbook.** "… (evidence).xlsx" now carries two image
  tabs — **Evidence (stacked)** for reading top-to-bottom and **Evidence (side-by-side)** for
  copying straight into a report — instead of stacked-only (the side-by-side files previously
  lived only in the images folder). Applies to both Highway Detail and Intersection Detail
  evidence sets; the workbook grows accordingly (both layouts embedded).

## v0.22.0 — 2026-07-08

Intersection Detail catches up with the site's July 2026 report overhaul — and gets evidence
images, the second report after Highway Detail.

- **The new Intersection Detail format is fully supported.** The site's July 2026 update reshaped
  the report (35 columns: the duplicated second "ML Eff-Date" is gone; the tail is now
  "Xing P/S" + "Xing Line Lgth"; postmiles print zero-padded; booleans are Y/N; the print gained
  cover pages and per-record intersection numbers). The Excel consolidator, the PDF consolidator,
  and all three comparison flavors (vs TSN, PDF vs TSN, PDF vs Excel) now read that format —
  verified statewide against a same-run 217-route export pair (16,459 rows; PDF↔Excel
  cell-identical apart from whitespace the comparison already normalizes).
- **Pre-update workbooks and PDFs are refused, not mis-read.** The old 36-column layout can't be
  read by the new positions without silently mis-mapping every column from Description on, so the
  comparators and the PDF parser detect it and say to re-export instead. Consolidated workbooks
  and comparison results produced before the update remain readable as they are.
- **The comparison itself got dramatically cleaner** — the site fixed most of what used to differ
  wholesale. Date of Record and the INT/Control/Lighting effective dates now match TSN on ≥99.9%
  of rows (the old systematic ~1-day offset is gone), booleans match natively, the Location now
  carries the route suffix, and the cross-street completeness gap shrank from ~37% to ~1%. The
  one wholesale-structural column left is **Int St Eff-Date** (TSN stores a 2022 bulk refresh
  stamp where TSMIS now keeps the historical date), plus a smaller ML/CS eff-date resurvey gap
  (~12% / ~3%). "Xing Line Lgth" (TSN's X_CROSS_OVERRIDE) is newly exported and newly compared;
  the second ML eff-date TSMIS no longer exports appears TSN-only (blue) on the Report View. The
  statewide baseline drops from ~163k differing cells to **21,675** (16,199 matched
  intersections), and the Notes sheet was rewritten to describe the new reality.
- **Report View "Major" counts follow the data now.** Date of Record and INT/Control/Lighting
  eff-date differences count as Major (they're genuine conflicts now); Int St / ML / CS Eff-Date
  and the route suffix stay red-but-not-Major (structural). All differences still render red and
  count in "Diffs".
- **Evidence images for Intersection Detail.** The same verified screenshot-and-circle automation
  Highway Detail got in v0.21.0 now covers both Intersection Detail rows. Drop the **statewide
  TSN Intersection Detail print** (one PDF — any filename) into the TSN library's
  `intersection_detail/pdf/` folder (the app creates it), keep the day's "Intersection Detail
  (PDF)" export alongside the Excel one, and the shared "Evidence images" option covers this
  report too. The TSN side of every example is located on the print's fixed column template —
  validated statewide (16,584/16,584 records; 30 of 32 columns parse back 100.0% identical to
  the TSN extract, the rest are print truncations the verifier correctly skips). The matrix
  option's hint now reports each report's PDF folder separately.
- Rebuild the TSN library once after updating (the app prompts): the stored Intersection Detail
  projection moves to the new shape and records each row's district/county for evidence.

## v0.21.1 — 2026-07-08

Hotfix: the folder v0.21.0's release notes told you to drop the TSN district PDFs into now
actually appears.

- **The `highway_detail/pdf/` drop folder is created by the app.** v0.21.0 looked for the TSN
  district prints there but never created the folder, so an updated install had nowhere to drop
  them. The TSN library now creates it on startup (and from Settings ▸ "Open TSN library folder"),
  with a hint file inside explaining what goes there — and the library's README refreshes on
  update instead of staying frozen at the version that first wrote it.
- **The evidence toggle wakes up when you come back.** After dropping the PDFs, re-entering the
  Everything matrix or the by-day matrix re-checks for them — no restart needed to un-grey the
  "Evidence images" option.

## v0.21.0 — 2026-07-08

**Evidence images** — the manual "screenshot both PDFs and circle the cell" workflow, automated.
When a Highway Detail vs-TSN comparison finds differences, the app can now render the proof for
you: for every differing column it samples random example rows (random routes, not just the first),
finds that exact cell in **both** source PDFs — the TSMIS "Highway Detail (PDF)" export and the TSN
district print — and produces captioned images with the cell boxed in red on each side.

- **Turn it on from either matrix page.** A shared "Evidence images" option (with a per-column
  example count, 1–10) lives under *Comparison output* on the Everything matrix and the Compare
  tab's by-day matrix. When it's on, each supported vs-TSN comparison also writes a
  **"… (evidence).xlsx"** — a summary plus every image embedded — and a **"… (evidence images)"**
  folder holding each example in two layouts: stacked (easy reading) and side-by-side (ready to
  paste into a report). Both writes keep the previous set if anything fails or a file is open.
- **What you need in place.** Drop the TSN Highway Detail **district PDFs** into the TSN library's
  `highway_detail/pdf/` folder (any filenames — the app reads each file's own district header),
  and have the day's **Highway Detail (PDF)** export alongside the Excel one. The option stays
  greyed with a hint until the PDFs are in place. Rebuild the TSN library once after updating
  (Settings ▸ TSN reports — the app will prompt; the library now records each row's district so
  evidence can find the right print).
- **Every example is verified before it's shown.** The cell is parsed back out of each PDF and
  normalized exactly like the comparison — an image can never show something other than what was
  compared, so the evidence set doubles as an end-to-end spot-check of the comparison itself.
  Candidates that fail (for example the known case where the PDF and Excel exports came from
  different site builds) are skipped, with the reason recorded in the workbook.
- Applies to both Highway Detail rows (Excel-based and PDF-based vs TSN). Other reports can join
  once they have PDF editions on both sides.
- The portable app now ships the PDF-rendering pieces this needs (about 20 MB larger); the
  build's self-test proves the render path works before anything is released.

## v0.20.0 — 2026-07-07

Highway Detail is now a fully integrated report: consolidate it, compare it against TSN, check its
two exports against each other, and see it in both matrices — the same treatment every other report
gets. The schema and every comparison rule were verified against a full statewide export set (252
routes / 51,243 rows), the statewide TSN "TSAR - HIGHWAY DETAIL" extract (60,083 rows), and all 12
TSN district PDFs.

- **Consolidate Highway Detail.** Two new consolidators, exactly like the Highway Log /
  Intersection Detail pairs: **Highway Detail** combines the per-route Excel exports (with a hover
  legend explaining every column), and **TSMIS Highway Detail (PDF)** parses the app's own PDF
  export into the identical 34-column format.
- **Compare Highway Detail against TSN.** A new TSMIS-vs-TSN comparison with the full discrepancy
  workbook — Summary / Spot Check / Comparison / Routes / Only-in tabs — plus a **Report View**
  sheet that replicates the printed two-line TASAS record with every difference in red (the
  Intersection Detail treatment), and a **Notes** sheet documenting every normalization applied.
  The TSN side lives in the TSN library (Settings ▸ TSN reports): import the statewide
  "TSAR - HIGHWAY DETAIL" Excel extract once and every comparison reuses it. (The TSN district
  PDFs were cross-checked against that extract — 57,647 records, every shared field ≥99.9%
  identical — so the machine-readable Excel is the library source.)
- **Rows pair correctly across the two systems' different conventions.** TSMIS tags an
  independent-alignment roadbed by gluing R/L onto the postmile ("000.080R") where TSN prints a
  bare postmile and says R/L in the Highway Group column — the comparison unifies the two, so
  routes like 282 and 880S match row-for-row instead of showing as all-missing. The equation
  marker "E", which the two systems attach to different rows, is compared as its own "PS" column
  instead of splitting rows apart. TSN's explicit "A" (add mileage) matches TSMIS's blank, its
  unpadded numbers match TSMIS's zero-padded ones ("2" = "02"), and its raw-precision lengths
  match the printed 3-decimal miles.
- **Check the PDF export against the Excel export.** "Highway Detail — TSMIS (PDF) vs TSMIS
  (Excel)" diffs the two renders of the same report so you can prove both exports carry the same
  data; "TSMIS (PDF) vs TSN" covers the PDF side against TSN. Both mirror the existing Highway
  Log / Intersection Detail checks.
- **In both matrices.** Highway Detail and Highway Detail (PDF) are rows in the Everything matrix
  (cross-environment) and the vs-TSN by-day matrix, with the same auto-consolidate and freshness
  behavior as every other report. Highway Summary remains export-only until its schema can be
  verified the same way.

## v0.19.3 — 2026-07-07

A field fix for the new Highway Detail export.

- **Highway Detail no longer re-selects the report on every route.** Because Highway Detail sits in
  the site's new grouped "Highway ▸ Detail" menu, the app's per-route safety check kept mistaking the
  short menu label ("Detail") for a changed selection and re-picking the report on every single route
  — flooding the log with "report form drifted" and slowing the run. The check now confirms the report
  by its stable id instead of the on-screen text, so it stays quiet on the happy path while still
  catching a genuinely reset form. Exports were always correct; this just removes the wasted work and
  the noise. (Applies to both the Excel and PDF editions of Highway Detail.)

## v0.19.2 — 2026-07-07

Two export improvements for the new Highway Detail report.

- **Highway Detail can now be exported as a PDF.** Alongside its Excel export (added in v0.19.1),
  Highway Detail now has a print-layout **PDF** edition — the same page-per-route Print output that
  Highway Log and Intersection Detail already offer. It appears next to the Excel version on the
  Export tab.
- **Selecting both editions of a report no longer runs it twice.** When you tick both the Excel and
  the PDF version of the same report (Highway Log, Intersection Detail, or Highway Detail), the app
  now loads each route **once** and saves both files from that single result — instead of generating
  the whole report a second time. Faster, and easier on the TSMIS server. (Fast mode still runs each
  edition on its own for now.)

## v0.19.1 — 2026-07-06

Two things: the Highway Detail / Highway Summary exports go live, and a validation glitch found
on the work PC is fixed. Comparison numbers are unchanged.

- **Highway Detail and Highway Summary can now be exported.** These two reports — previously listed
  as "coming soon" — are now on the Export tab and in Export Everything, exactly like the others.
  (Consolidating and comparing them against TSN comes in a later update.) Where the site still has
  them turned off, the app says so clearly and skips them instead of stalling.
- **"Validate & package results" no longer reports a phantom error.** On a PC that keeps TSN
  Highway Log files inside the export store, validation mistakenly treated that drop folder as an
  export environment and flagged a false error for it. Validation now only checks real export
  environments.

## v0.19.0 — 2026-07-06

Usability and trust improvements, plus the structural cleanup groundwork. No change to how any
comparison is calculated (the numbers are identical to v0.18.5 — re-blessed).

- **One-click validation.** A new **Settings ▸ "Validate & package results"** button runs every
  report already on this PC through the real comparison pipeline and saves everything a maintainer
  needs — outcomes, TSN freshness, logs, and a per-comparison summary — into one file. It confirms
  first (it refreshes those comparison cells and can take a few minutes), shows progress, and can
  be cancelled. This replaces the old command-line evidence step.
- **The same report organization everywhere.** The Consolidate and Compare tabs now group reports
  into the same Ramp / Intersection / Highway families as the Export tab, so a report sits in the
  same place on every tab.
- **Add today to the by-day matrix before exporting.** Today's column now appears in the vs-TSN
  by-day matrix even before you've exported anything for it — so you can export straight into it
  from the matrix instead of having to export elsewhere first.
- **Matrix panels stay usable while a comparison runs.** On smaller/laptop screens the two panels
  on the right no longer shrink to unusable sizes when a job is in progress.
- **Under the hood: the structural cleanup.** The whole codebase was reorganized for the next
  features without changing behavior: every comparator now rides one shared engine skeleton, the
  PDF parsers share one table library, the big GUI files split into focused modules, and adding a
  new report family (Highway Detail/Summary is reserved) is now a proven recipe with its own
  automated check. The comparison engine's numbers were re-verified cell-for-cell against the real
  statewide data (2.79M cells identical; the approved counts unchanged).
- **Safety hardening.** "Delete all reports" now only ever deletes folders this app itself created
  (a look-alike folder is flagged and left alone); an update re-verifies its download's integrity
  one final time right before installing; and the Export Everything destination is validated when
  you pick it (a network share or missing folder is refused with a clear message).

## v0.18.5 — 2026-07-03

The audit release: every confirmed finding from the full-repo audit, with no new features.
Highlights (the full map is `docs/planning/fable5-repo-improvement-audit.md`):

- **Comparisons self-heal after app updates.** The TSN library now records which
  normalization version built it; when an update improves the comparison rules, the affected
  report rebuilds itself from your raw TSN files the next time a comparison runs (previously a
  fix could silently "look unfixed" until a manual Settings ▸ Rebuild).
- **A real 0 never reads as blank.** The remaining places where a numeric zero (a postmile,
  a route token) could blank out — mis-aligning or falsely flagging rows — now keep it.
  Verified cell-for-cell identical on the real statewide data (canary unchanged).
- **Big comparisons skip the live-formulas twin again.** The v0.18.2 skip for 12k+-row
  comparisons had shipped inert; it now actually skips (and is locked by a test that runs it
  against a real workbook). The Intersection Detail "Report View" also builds faster.
- **Consolidating with a file open in Excel no longer reads incomplete.** Excel's `~$` lock
  stubs were being counted as unreadable inputs, demoting a healthy consolidation to partial.
- **Compare tab: Browse… no longer overrides your later folder picks.** A custom folder
  stays available in the dropdown but never silently wins over a run folder you selected after.
- **Starting a task during the background sign-in check now says so** ("try again in a few
  seconds") instead of failing with a browser error — and the check steps aside for you.
- **An interrupted update can no longer strand a mixed install.** If the swap is killed
  mid-rename (power loss), the next launch completes it or rolls it back — it used to delete
  the recovery pieces.
- **Quieter, more answerable logs.** The GUI, console and login flows write separate log
  files (simultaneous runs used to silently drop lines), every swallowed error now logs its
  reason, and the delete-all preview warns if part of the store couldn't be inspected.
- **Quality-of-life:** modals keep keyboard focus; route pickers and tabs are
  keyboard-operable; empty TSN imports error instead of producing an empty "complete"
  library; the release pipeline now refuses to publish if any check fails.

## v0.18.4 — 2026-06-29

A fix for the comparison matrices' job queue.

- **The queue no longer shows a finished job as still "running."** After a matrix or by-day
  (vs-TSN) comparison finished — or was cancelled — its row could stay in the queue panel
  marked "running" (in both the Everything and by-day matrices) until you started another job,
  and it couldn't be cleared. The work always actually finished; only the panel was stale. It
  now updates the moment a job ends.

## v0.18.3 — 2026-06-29

Two corrections to the Intersection Detail vs-TSN comparison, found in field use.

- **No more false "intersecting-route postmile" differences.** When a crossing route's postmile
  is 0 in both systems, the comparison was flagging it as a difference — TSN's numeric 0 was being
  read as blank while TSMIS showed "0.000". It now reads 0 on both sides and matches; a genuinely
  missing value still flags as before.
- **One-sided intersections are now labelled, not shown as all-red.** In the Intersection Detail
  "Report View", an intersection that exists in only one system is marked **"TSMIS only" / "TSN
  only"** (a coloured band) instead of appearing as an ordinary row with every field flagged red —
  matching how the main comparison sheet already shows them.

## v0.18.2 — 2026-06-29

A small follow-up to v0.18.1: it makes the largest comparison (Intersection Detail vs TSN)
feel responsive instead of frozen, speeds up bulk comparison rebuilds, and surfaces the
route's letter suffix in the Intersection Detail "Report View".

- **The big comparison no longer looks stuck.** Building the Intersection Detail vs-TSN
  workbook (by far the largest — about 17,000 rows) used to go quiet for a few minutes during
  its final "Report View" step, which looked like a freeze. It now shows steady progress the
  whole way through, so you can see it's still working — and **Stop takes effect sooner**.
- **Faster bulk comparison rebuilds.** When the matrix rebuilds comparisons, the optional
  live-formulas copy is now skipped for very large reports (it's millions of live formulas and
  several minutes of extra work). The normal workbook still contains **every value**, and the
  log notes when the copy was skipped. You can still build a live-formulas copy of a single
  comparison yourself from the Compare tab.
- **Route Suffix now shows in the Intersection Detail "Report View".** The route's letter
  suffix (e.g. the "U" in "210U") now sits next to the route in the printed-style Report View
  and turns red when TSMIS and TSN disagree — matching the "Route Suffix" column already on the
  Comparison tab.

## v0.18.1 — 2026-06-26

A field-validated follow-up to v0.18.0: it keeps exports working as the TSMIS site
changes its report menu, tidies the report list, and fixes two issues found in use.

- **Keeps working as the TSMIS site reorganizes its report menu.** The site is moving its
  report dropdown to grouped fly-out menus (Ramp / Highway / Intersection), already live on
  the development site. The exporter now picks each report by its stable id, so it works on
  both the current production menu and the new grouped one — your exports keep running
  through the changeover, with nothing for you to do.
- **The report list is grouped like the website.** Highway Log, Highway Log (PDF) and
  Highway Sequence stay at the top; the Ramp and Intersection reports are tucked under their
  own headings, matching how the TSMIS site now lists them.
- **Highway Detail and Highway Summary are listed as "coming soon."** The site is adding two
  new reports; you'll see them greyed under a "Highway" heading so you know they're on the
  way — they switch on here as soon as the site enables them.
- **The matrix queue clears properly.** After a matrix or by-day job finished, a leftover
  item could linger in the queue and couldn't be cleared or cancelled. The queue now always
  reflects what's actually running.
- **Clearer comparison heading.** In the Intersection Detail comparison, the column that
  flags a route's letter suffix (e.g. "210U" vs "210") is now labelled **"Route Suffix"**
  instead of "Roadbed" — the figures are unchanged, only the heading is clearer.

## v0.18.0 — 2026-06-26

A big under-the-hood overhaul for reliability and maintainability — plus one new
report. The day-to-day workflow is unchanged; what changed is how carefully the tool
treats your results when something goes wrong, and how the app is built and updated.

- **New report: Intersection Detail (PDF).** Alongside the Excel "Intersection Detail",
  you can now export it as a PDF — exactly the way Highway Log already offers both. It
  consolidates into one workbook and compares (between environments, vs TSN, and
  PDF-vs-Excel) like every other report, and it appears on both matrices.
- **A partial run never looks "finished" anymore.** If some routes or inputs fail or
  come back empty, the result is now clearly marked **incomplete** (amber on the matrix)
  instead of green — and an incomplete refresh is never cached or compared as if it were
  complete. You always know whether a column is the full picture.
- **A failed refresh never clobbers your last good copy.** Consolidated workbooks are now
  written transactionally (write-then-swap): if a refresh is interrupted or fails midway,
  the previous good file is kept intact rather than left half-written.
- **A safer self-updater.** An update now **refuses to install** unless its download
  matches a published checksum (no more "install it anyway"), re-checks the staged files
  one last time right before swapping them in, rejects any tampered archive, retries a
  flaky download, and can still roll back to an older version far down the release list.
- **Reset stays inside the app's own folders.** "Reset" / cleanup now refuses to follow a
  junction or symlink out of the app's data area, so it can only ever clear what it owns.
- **Under the hood.** The engine, the GUI bridge, and the report registry were
  reorganized into many small, single-purpose modules with a single report catalog as the
  source of truth; the full automated test suite now runs against the **exact** packaged
  executable, and the build is pinned to a verified dependency set so every release is
  reproducible. No change you need to do anything about — just a sturdier foundation.

## v0.17.1 — 2026-06-21

A quick fix-up of issues found using v0.17.0 on the matrices.

- **No more blank space below the matrices.** A hidden control in the Matrix-options
  panel was stretching the page so it could scroll down into a large empty area below
  the window. The panel's fast-mode / comparison-output toggles are now contained, so
  the matrix tabs stay put.
- **The Matrix-options panel is usable again.** On shorter screens it was being squeezed
  into a tiny scrolling sliver while the activity log hogged the space — now the options
  (queue, day columns, set-all modes, report toggles, fast mode) get the room and the log
  shrinks to a compact status strip.
- **Stop / Clear now work quickly when sign-in is failing or slow.** A matrix export that
  couldn't sign in used to ignore **Stop all** / **Clear queued** until its sign-in
  attempt timed out; both now interrupt the sign-in within about a second (normal and
  fast mode), so a stuck queue clears right away instead of feeling frozen.
- **The TSN "Choose…" picker opens to the TSN library.** Picking a TSN workbook on either
  matrix now starts in that report's own folder inside the TSN library, instead of the old
  per-run input location.
- **The TSN library is now self-documenting.** It starts as a ready-made folder tree —
  each report has its own `…/<report>/raw/` folder with a short note saying which file(s)
  to drop there, plus a README — so it's clear where to put your TSN reports before you
  import the first one. **Open folder** (Settings ▸ TSN reports) creates this tree on
  demand too.

## v0.17.0 — 2026-06-20

- **Every report now compares against TSN — not just Highway Log.** Ramp Summary,
  Ramp Detail, Highway Sequence, Highway Log (Excel and PDF), and Intersection
  Summary & Detail each have a TSMIS-vs-TSN comparison, live in **both** the Everything
  matrix and the by-day "vs TSN" matrix. The rows that used to be greyed "coming next
  update" are now active, and **"Set all to vs TSN"** switches every report at once.
- **And every report compares between environments.** Intersection Summary/Detail and
  Highway Log (PDF) gained their cross-environment comparison too, so the grid is now
  complete: every report × {between environments, vs TSN}, plus Highway Log's
  PDF-vs-Excel self-check.
- **Intersection Summary & Detail now consolidate** into a single workbook like every
  other report — so they can be compared and reused, not just exported.
- **A home for your TSN data.** Each report's TSN source (district PDFs or a statewide
  workbook) lives in one fixed folder, managed from a new **Settings ▸ TSN reports**
  panel: import the raw file(s) once, click **Rebuild**, and a status dot shows whether
  the comparison data is current. The panel shows the folder location with an
  **Open folder** button, and on the matrix each report has its own TSN picker.
- **One-stop "Export today" on the vs-TSN-by-day matrix.** A new **Export today →**
  button (and per-row / per-cell ↻) pulls a fresh, dated column for every report and
  automatically consolidates and compares each one against TSN — filling the column in
  one go. Only today is exportable; past days stay as the immutable record you pulled.
  Fast mode, worker count, and pause/skip all apply.
- **Sign-in and browser, made obvious.** Edge one-click sign-in is now checked quietly
  in the background (on launch and when you switch site), so the indicator lights up by
  itself. The **Log in** button now simply opens Google Chrome to save a reusable login.
  The old Browser dropdown is gone — the title bar shows a read-only **"Export via …"**
  indicator of what's actually exporting, and the one real choice (Built-in Chromium vs
  installed Chrome, Chrome by default) moved to **Settings ▸ Export browser**. Microsoft
  Edge is still used for one-click sign-in and as a fallback.
- **The matrices warn you before an export fails.** When the environment check has found
  a report greyed-out or missing on a site, both matrices now flag that report/cell amber
  — the same warning the Export tab shows — so a doomed comparison is obvious up front.
- **Drag to reorder.** Rows and columns on both matrices can be dragged into the order
  you prefer; the order is remembered.
- **Divided-roadbed routes match correctly.** Intersection rows whose TSN route carries a
  roadbed suffix (e.g. 210U vs 210) are now matched to their TSMIS counterpart, with a
  note when the suffix is the only difference.
- **Reliability + polish.** The Highway Log PDF reader now flags an incomplete parse
  instead of silently dropping rows; a thorough UI-consistency pass; and a large new set
  of automated checks across every new comparison.

## v0.16.1 — 2026-06-19

- **The TSN comparison view is now a full matrix that covers every report.** The
  Compare tab's sub-tabs are now **Cross-environment**, **vs TSN**, and **vs TSN
  Matrix**. The matrix (formerly "TSN by day") fills the screen like the Everything
  matrix and lists every report — Highway Log works today; Ramp Summary/Detail,
  Highway Sequence, and Intersection Summary/Detail appear greyed until their TSN
  comparison is added in the next update. (Highway Log's between-environments
  comparison moved back onto "Cross-environment" with the other reports.)
- **Pause, resume, and skip a matrix re-export — and watch it live.** A matrix
  re-export now shows the same per-route progress and live preview as the Export tab,
  and you can pause/resume or skip a stuck route without cancelling the whole run.
- **Pick the number of browsers for matrix Fast mode.** A browser-count picker sits
  next to the Fast mode toggle (shared with the Export tab and Settings, so it's one
  value).
- **Consolidated workbooks are saved and reused.** A comparison reuses the day's
  existing consolidated workbook instead of rebuilding it every time; a small
  indicator shows whether one exists and is current, with one click to refresh it.
- **Optional live-formulas copy of any comparison.** A toggle writes an auditable,
  recalculating workbook beside the plain values copy; each matrix remembers its own
  setting.
- **Export Intersection Summary & Detail.** These are greyed on the production TSMIS
  site but available on the development site — a new **Settings ▸ "Use development
  site"** switch points the app there (and back).
- **Fits short, wide laptop screens.** The comparison matrices no longer scroll after
  a couple of rows — the grid reclaims the surrounding space and shows all rows.
- **Polish.** The matrix-options checkboxes now match the rest of the app (no stray
  white boxes in dark mode), plus accessibility and reliability fixes across both
  matrices.

## v0.16.0 — 2026-06-19

- **Queue up matrix work instead of waiting.** On the Everything tab's
  Comparison matrix, a second action no longer says "a task is already running" —
  it joins a **queue** that runs one job at a time and moves on by itself. The
  queue is shown right on the matrix, and you can reorder it, remove a job, clear
  what's waiting, or stop everything. Line up a re-export and a rebuild, or several
  cells in a row, and walk away.
- **Two clear buttons on every row and column.** Each report row and each
  environment column now has **two** buttons with distinct icons: one **re-exports**
  that report/environment live from TSMIS, the other **rebuilds its comparisons** —
  so the bulk "refresh" you want is never ambiguous. (Re-exporting a whole row or
  column asks first, since it pulls many reports from TSMIS.)
- **Fast mode for matrix re-exports.** A new **Fast mode** toggle on the matrix
  runs re-exports with several browsers at once (the same speed-up the Export tab
  has), for when you're refreshing a lot at once.
- **New: compare exports day-by-day against TSN.** A new **"TSN by day"** sub-tab
  on the Compare tab lets you pick specific exported **days** and compare each one's
  Highway Log against TSN side by side — e.g. the 17th vs TSN next to the 18th vs
  TSN. Pick a data source, add the days you want as columns, and build each cell;
  it reuses the same TSN dataset and comparison engine as the Everything matrix.
  Highway Log (Excel and PDF) works now; the other reports appear greyed until their
  TSN comparison is added.

## v0.15.0 — 2026-06-19

- **New: a comparison matrix on the Everything tab.** A new **Comparison
  matrix** sub-tab shows every report against every data source / environment at
  a glance — each cell is colour-coded by how many differences it found (green
  for identical, shading from amber to red as differences grow), alongside the
  export date and a
  one-click link to open that comparison workbook. Choose the baseline to compare
  everything against; refresh a single cell, a whole row, a whole column, or every
  stale comparison at once; and cancel a long refresh and resume it later. Your
  matrix setup — the baseline, which reports and environments are shown, and the
  comparison mode per row — is remembered between sessions.
- **Compare the Highway Log against TSN, right in the matrix.** The Highway Log
  now appears as two rows — **Excel** and **PDF** — and each can compare
  cross-environment, against **TSN**, or Excel-vs-PDF. Drop the district TSN PDFs
  into the Everything folder and the matrix offers to consolidate them for you, or
  point a row at a consolidated TSN workbook; the file in use is shown right under
  the report name. (TSN comparisons for Ramp Summary, Ramp Detail and the Highway
  Sequence Listing appear greyed for now — groundwork for a later version.)
- **Choose what's on the matrix.** Toggle which report types and which
  environments appear, so the grid stays as compact or as complete as you need.
- **Intersection reports are clearly marked as not-yet-supported.** The two
  Intersection reports now show greyed-out everywhere (they're export-only, with no
  comparison), instead of quietly behaving differently from the rest.
- **A top-to-bottom visual polish.** Cleaner, more consistent buttons, dropdowns
  and file pickers across every tab — all readable in both light and dark mode —
  plus quick, non-intrusive animations throughout: panes, lists, the activity log
  and the light/dark switch now ease in smoothly (and fully respect the system's
  "reduce motion" setting).

## v0.14.3 — 2026-06-19

- **A "for IT" page now ships in the app folder.** Every download now
  includes an **`IT-README.txt`** next to `Start Here.txt` — a plain-language page
  for whoever in IT or security reviews the tool: what it connects to, what it
  reads and writes, how the saved login is handled, and why a portable,
  self-updating, unsigned in-house app is safe to run. It rides app updates, so
  the page stays current from this version on.

## v0.14.2 — 2026-06-18

- **Consolidate tab cleanup.** The three Highway Log consolidations now
  have clear, parallel names — **TSMIS Highway Log (Excel)**, **TSMIS Highway Log
  (PDF)**, **TSN Highway Log (PDF)** — so the plain "Highway Log" can't be confused
  for the others. The **TSMIS Highway Log (PDF)** consolidation now reads the app's
  own "Highway Log (PDF)" export straight from the output folder (with the Export-day
  picker, like the Excel one) instead of a redundant drop folder — you no longer copy
  the app's own exports into an input folder. The "Export day" picker is now hidden
  for the one report it doesn't apply to (TSN, whose district PDFs come from outside
  the app).
- **A few UI labels now match what actually happens.** The environment
  check no longer wrongly flags **Highway Log (PDF)** as unavailable on every site
  (it shares the "Highway Log" dropdown option, so it now follows that report's
  result); the Export Everything description says it writes to your chosen
  destination folder (not "dated run folders"); the auto-consolidate note lists every
  report that has no consolidator; and **Delete all reports** now also clears the
  Highway-Log-PDF outputs and the Export Everything store, so a "fresh start" really
  is one.

## v0.14.1 — 2026-06-18

- **Highway Log comparisons in one place.** The Compare tab now has a
  **Highway Log** sub-tab gathering every Highway Log comparison — TSMIS vs TSN, the
  two PDF-sourced comparisons, and across environments — beside a
  **Cross-environment** sub-tab for the plain report comparisons, instead of the old
  three-way split. (v0.14.0 briefly made this a separate top-level tab; v0.14.1
  moves it to a sub-tab inside Compare.)

## v0.14.0 — 2026-06-18

- **An accurate Highway Log, sourced from the PDF.** The site's Highway
  Log **Excel** export is buggy — it drops rows and whole roadbed-geometry
  columns, expands the report's "same as the other roadbed" `+` markers into
  numbers, and mis-attaches descriptions. A new consolidation parses the Highway
  Log **PDF** export instead (drop the per-route PDFs into
  `input\tsmis_highway_log_pdf`), producing the same 31-column workbook **without**
  those export errors — verified row-for-row against all 252 routes.
- **Highway Log columns are correctly labeled.** The vendor Excel export
  mislabeled most Highway Log columns (e.g. "N/A" is really **Non-Add Mileage**;
  the cryptic roadbed codes are surface type, shoulder widths, lane counts, …; it
  even reused "RB SH" for two different columns). Every Highway Log workbook now
  uses the **report's own legend** labels, with the old label kept in `[brackets]`,
  a hover tooltip on every column, and a **Legend** sheet explaining each one. This
  is a relabel only — the data and comparison results are unchanged.
- **Divided-highway rows now line up correctly.** On a divided highway
  each segment has two rows (one per roadbed). TSMIS marks the roadbed in the
  location (`R021.466R`/`…L`); the TSN log marks it a different way. The comparison
  used to treat these as *different* locations, so the same physical roadbed row
  showed up as **"only in TSMIS" + "only in TSN"** instead of being compared —
  hiding thousands of genuine differences. It now recognizes the roadbed on both
  sides and pairs them, surfacing those differences (audited against the source
  PDFs — every pairing is the correct roadbed, none crossed).
- **"Same as the other roadbed" markers are handled.** A roadbed column
  printed as `+`/`++` means "this roadbed's value is on the paired row" — a
  pointer, not a value. Comparisons now treat it as such (it is **never** counted
  as a difference, on either source), and a comparison cell that resolved a `+`
  shows what it points to in a hover note.

## v0.13.1 — 2026-06-17

- **Highway Log can now be exported as a PDF.** A new **Highway Log
  (PDF)** report exports each route's Highway Log as a print-formatted PDF — the
  same layout the site's Print button produces (cover page + every page) — into
  `output/…/highway_log_pdf/`, alongside the existing Excel export. Tick it on the
  Export tab like any other report.
- **Comparisons match repeated locations correctly.** When a TSMIS-vs-TSN
  or cross-environment comparison had two rows at the **same location** (e.g. two
  `001 R000.129` segments), it used to pair them in the order they appear —
  first-with-first, second-with-second — so a row that actually matched the other
  side's *second* listing was wrongly flagged as different. It now pairs repeated
  locations by **which rows are most alike** (the most fields matching), not by
  order. The row's identity is unchanged (same Route + location); only the pairing
  of repeats is smarter. This can only *remove* false differences, never add one —
  on a full Highway Log comparison it cleared ~3,600 phantom differing cells.

## v0.13.0 — 2026-06-17

- **A clearer window, and it tells you what's happening.** The right
  side of the window now follows the whole run: before you start, a **summary of
  exactly what will happen** (which reports, how many routes, where it saves);
  while it runs, progress that spells out **exactly what's running** — for a
  single export the report and route, and for **Export Everything** the
  environment it's on (e.g. "Environment 2 of 6 · SSOR / Test"), the report
  within it, the route, an **estimated time remaining**, and a row of
  per-environment markers showing which are done, which is running, and which are
  still queued (so it's finally easy to see where a big run is at); and when it
  finishes, a **completion summary** with one-click **Open folder** and **Retry
  failed routes** (just the ones that failed, not the whole run). The window also
  **flashes in the taskbar when a run finishes** so you can look away and come
  back — turn that off in Settings if you'd rather it didn't. The header was
  tidied up and the report/environment checkboxes are now fully keyboard-friendly.
- **Revert to the previous version.** Settings now has a **Revert to
  previous version** button: if an update ever causes trouble, one click
  reinstalls the release just before this one, through the exact same verified
  download-and-swap the normal update uses (your reports, login and settings stay
  put). It only appears on installs the app can update itself.
- **Two separate "check environments automatically" switches.** The old
  single setting is now two: **after sign-in** (on by default) and **after the
  app starts** (off by default) — so the background environment check can run when
  you sign in without also running every single launch.
- **Compare tab is split into sub-tabs.** The two comparison kinds —
  **Cross-environment** and **TSMIS vs TSN** — are now on their own sub-tabs
  (cross-environment shown first), instead of sharing one long list.
- **Export Everything labels every file by environment.** Files in the
  always-current store are now named with their source/environment up front
  (e.g. `ssor-prod tsar_ramp_detail_route_5.xlsx`, and the combined workbook the
  same way), so a file copied out of the folder still says which environment it
  came from. The Everything tab also **colour-codes** report types and
  environments the last environment check flagged — amber for "may be limited",
  red for "would fail" — and now greys out during an environment check like the
  other tabs.

## v0.12.0 — 2026-06-17

- **Export Everything — one always-current set of reports.** A new
  **Everything** tab exports the report types you tick across the environments you
  tick into a single folder you choose (default **All Reports (current)**). Re-run
  it any time to refresh: it overwrites that folder in place, so it always holds
  the latest of every report. A **Saved reports** list shows how old each report
  is and flags any that are lagging behind the rest, with a one-click **Refresh**
  for just that report — plus pause/resume and resume-after-restart for the long
  full runs.
- **Pause / Resume a running export.** A new **Pause** button holds the
  run between routes and **Resume** picks it back up — separate from Skip (one
  route) and Cancel (stop the run). Works in fast mode too.
- **Auto-consolidate when an export finishes.** An optional checkbox
  builds the combined workbook automatically right after the export, so the
  Consolidate step happens for you.
- **Self-describing filenames.** Consolidated and comparison files now
  carry the date + source/environment in the filename, so a file copied out of
  its folder still says exactly which run it came from.
- **Compare tab lists only relevant folders.** The cross-environment
  folder pickers now show only export runs that actually contain the report type
  you picked, instead of every run folder.
- **Buttons never cut off.** The Start / Pause / Cancel bar stays pinned
  and visible while the report list scrolls, and the tab row no longer crowds.

## v0.11.1 — 2026-06-16

- **Flawless TSN Highway Log conversion.** The TSN district-PDF → Excel
  converter now transcribes feature descriptions perfectly across all 12
  districts — totals-block footer text and page furniture can no longer leak into
  a segment's Description. This removes ~1,000 false-positive "differences" from
  the TSMIS-vs-TSN Highway Log comparison (what remains is all genuine data
  differences). Real descriptions that merely contain words like "UNCONST" or
  "TOTAL" are now kept correctly.
- **Ramp Summary audit cell explains itself.** When a route's parsed
  section sub-totals don't add up to its stated total, the consolidated workbook's
  Audit cell now names the section that's short (e.g. "⚠ Source ≠ total: Ramp
  Types") instead of a bare red result — making clear it's a quirk in the source
  PDF's own numbers on a few dense routes, not a tool error.

## v0.11.0 — 2026-06-16

- **Comparisons are far more accurate.** Comparing the same report
  across two environments used to flag large numbers of "differences" that were
  really just rows shifting position — one missing point near the top made
  everything below it look changed. Comparisons now line rows up by their
  **postmile** (a row's real identity) instead of the coarser county, so a
  Highway Sequence comparison that used to show ~15,800 differing cells now
  shows ~5,000 genuine ones; only real differences remain.
- **A comparison never claims "everything matches" when it couldn't read a
  file.** If an input file is unreadable it's no longer silently
  skipped: the result says **"Comparison incomplete"** and the workbook lists
  exactly what was left out — instead of a misleading green "everything
  matches" that quietly ignored the missing data.
- **Cleaner TSN Highway Log conversion.** Totals-block text (running
  mileage, "CUMULATIVE", "TOTAL CONST UNCONST", …) no longer leaks into the
  Description column — which also removes the false differences it was causing
  in the TSMIS-vs-TSN comparison.
- **Empty routes no longer stall the export.** When a route has
  nothing to download, the tool now moves on within about a minute instead of
  waiting out the full multi-minute time limit, so a long run with many empty
  routes finishes much sooner. Empty Intersection reports are recognized
  correctly too.
- **Damaged or locked output files are handled.** A half-written or
  unreadable file left by an interrupted run is re-downloaded rather than
  trusted as "already done", and a file you happen to have open in Excel during
  a resume no longer breaks the run.
- **A failed report can't overwrite a good one.** If a Ramp Summary
  PDF fails to parse (or is a stub one-page file), the tool keeps the good
  workbook you already had instead of replacing it with a blank one.
- **Safer updates.** Before installing, the in-app update now verifies
  the downloaded file with a checksum and installs only the expected files —
  extra protection against a corrupted or tampered download. Sign-in tokens are
  also scrubbed from the saved session and the logs.
- **Spreadsheet safety.** Free-text fields that begin with `=`, `+`,
  `-` or `@` are stored as plain text so they can't run as spreadsheet formulas,
  and comparisons guard against Excel's row/column limits and duplicate sheet
  names instead of failing partway through.

## v0.10.4 — 2026-06-12

- **Intersection reports fixed.** The two new report types now match
  the site exactly: the menu entries are **Intersection Summary** and
  **Intersection Detail** (the site doesn't use a "TSAR:" prefix for them),
  and Summary exports as an **Excel** file like Detail. The environment check
  no longer reports them missing.
- **See both sign-in paths at a glance.** The title bar now shows
  two small indicators: **Saved login** (the session file captured via
  Chrome / Built-in Chromium — what exports use, required for fast mode;
  age in the tooltip) and **Edge one-click** (green once the hands-free
  Windows sign-in has worked this session, amber when it's set up but not
  yet used, grey when never set up).
- **The Dev / testing update channel was removed.** Updates come
  only from full releases on this page. The Update channel switch is gone
  from Settings; nothing else changes.

## v0.10.3 — 2026-06-12

- **Updates install reliably now.** The 0.10.2 update could fail
  halfway on some PCs and leave a confusing half-installed app ("says 0.10.2
  but features are missing") or quietly fall back to the old version. The
  install now prepares the whole new version next to the old one first and
  swaps it in with instant renames — it either fully installs or fully
  doesn't, a failed attempt says so the next time the update is offered, and
  the interface shown is always the one actually installed (no more stale
  screens after an update). The first launch after an update is also more
  patient: instead of a scary error while Windows checks the new files, it
  shows "Still starting…" and finishes by itself.
- **The environment check runs by itself.** After the app starts (or
  you sign in), it quietly verifies sign-in + report access on all six sites
  in the background — several at once when Google Chrome / the Built-in
  Chromium and a saved login are available, one at a time otherwise — and
  the title-bar chip + Settings rows fill in. Turn it off in Settings. The
  Export tab also flags any report type the current site has greyed out.
- **Two new reports: TSAR Intersection Summary & Detail.** Exported
  like the ramp pair (Summary → PDF, Detail → Excel) into their own folders.
  Consolidation/comparison for them comes later.
- **Fast mode no longer trips over managed Edge.** Parallel browsers
  (fast mode and the environment check) now run in the Built-in Chromium /
  Google Chrome; Microsoft Edge keeps the one-click sign-in and is only used
  for parallel work when nothing else is available.

## v0.10.2 — 2026-06-12

- **The new TSMIS address is built in.** The report site moved to
  `tsmis.dot.ca.gov`; this version points there out of the box for all six
  source/environment combinations. If you had entered the new address in
  Settings as a stopgap, that custom entry keeps working — clear the box to
  fall back to the (now identical) built-in default.
- **Check sign-in + report access for every environment.**
  Settings ▸ **Check all environments** opens each of the six sites
  (SSOR/ARS × Prod/Test/Dev) in the background exactly like an export and
  verifies that sign-in completes, the right site loaded, the report form
  can actually pull data, and **all four report types are offered** (the
  site sometimes greys one out). Verdicts land next to each address as they
  finish — green OK, amber "Reports limited" naming the unavailable report
  types, red for sign-in/data/site failures, full detail in the tooltip —
  and a title-bar chip ("Envs 5/6") shows the overall picture; click it to
  jump to the rows. Built for the "signs in fine but can't pull reports"
  situation, so a broken environment is a 2-minute check instead of a
  wasted export run.
- **Screenshots show their address.** The per-browser Preview and
  the Verify-environment screenshot now display the page's web address above
  the image, so which site/environment the browser is really on is readable
  in plain text (sign-in tokens never appear).
- **A Dev / testing update channel.** Settings ▸ Update channel —
  leave it on **Stable releases** (the default; nothing changes for you).
  Pick **Dev / testing builds** only when asked to try a fix: the title-bar
  update button then offers quick prerelease test builds, clearly labeled
  everywhere, and the next stable release returns the install to normal
  automatically.

## v0.10.1 — 2026-06-12

- **The one-click update now works on locked-down PCs.** On machines
  where PowerShell is blocked for standard users (common on managed work
  PCs), the previous updater downloaded the new version and then silently
  failed to install it — the app closed and the download just sat in
  `data\update`. The install step no longer uses PowerShell, cmd, scripts or
  admin rights at all: the downloaded new version installs itself. It also
  fails LOUDLY now — if the install step can't even start, the app stays
  open on the old version and says so instead of closing into nothing.
  **If an update left you stranded before:** install this version manually
  once (download the zip, replace the app's `TSMIS Exporter.exe`,
  `_internal` and `Start Here.txt` — your `data\` and `output\` stay put);
  from then on the green Update button does the whole job.

## v0.10.0 — 2026-06-12

- **Comparisons answer the real question first.** Every comparison
  now leads with a verdict — **“✓ EVERYTHING MATCHES”** in green when the two
  sides are identical (the expected outcome between environments), or
  **“✗ DIFFERENCES FOUND — N differing cells, M one-sided rows”**. It shows
  three ways: a dialog the moment the comparison finishes, the first line of
  the run log, and a big colored banner at the top of the workbook's Summary
  (live formula in the formulas flavor, so it stays current after edits and F9).
- **Change a TSMIS address without waiting for an update.** Settings
  lists the page address for all six source/environment combinations; edit
  one if a site moves and it's used by the very next sign-in, export or
  Verify. Custom addresses are marked; clearing the box restores the
  built-in default.
- **Download the Built-in Chromium from Settings.** The standard
  (smaller) app can now fetch the same unmanaged browser the “with-browser”
  download ships (~170 MB, into the app's data folder — it survives updates)
  and remove it again later. Handy when managed-Edge sign-in misbehaves and
  installing Chrome isn't an option; restart the app after and “Built-in
  Chromium” appears in the Browser dropdown.
- **Compare environments against each other.** The Compare tab now
  also compares the SAME report exported from two different places — SSOR vs
  ARS, prod vs dev/test, or today vs an older run. Pick the report type and
  two export folders (e.g. `2026-06-11 ssor-prod` vs `2026-06-11 ars-prod`);
  the per-route files are read straight from both — **no consolidation step
  needed** — and you get the same trusted discrepancy workbook as the
  TSMIS-vs-TSN comparison, with the environment names as the two sides.
  Works for all four reports: Ramp Detail, Highway Sequence and Highway Log
  compare their Excel exports; **Ramp Summary compares its PDFs** (parsed
  with the same engine the consolidator uses), one row per route. Routes
  missing from one environment are flagged "entire route", and the live
  SELF-CHECK rows prove the numbers in Excel itself.
- **Exports are labeled by environment.** Runs now land in
  `output\<date> <source>-<environment>\` (e.g. `2026-06-11 ssor-prod`), so
  exports from different sites never mix or overwrite — that's what makes
  the environment comparison possible. Older bare-date folders are read as
  ssor-prod everywhere (consolidation included); run-report CSVs carry the
  same tag.
- **See what every browser is doing.** During an export, the
  progress card shows one live status row per browser (current route, phase,
  elapsed) — fast mode shows all of them. Each row has a **Preview** button
  that pops an actual screenshot of that browser's page, so you can see the
  sign-in state, the report being built, and the site's own **SSOR / ARS +
  environment label** with your own eyes.
- **Verify the environment without exporting.** A **Verify** button
  next to the environment dropdowns opens TSMIS in the background exactly
  like an export would (signed in), reads which data source / environment
  the page ACTUALLY loaded, and shows a screenshot with a clear
  matches-your-selection verdict — catch a wrong-environment setup before
  spending hours exporting.
- **A Settings tab.** Reliability knobs (per-route time limits,
  county wait, default fast-mode browser count — raise them when the server
  is slow), debugging tools (verbose logging, DevTools, a one-click
  **support bundle** zip with logs + run reports and **never your login**),
  quick folder shortcuts, forget-saved-login, and **Delete all reports** —
  one button clears every generated file for a fresh start after showing
  exactly what will be removed; logs, login and settings always survive.

## v0.9.0 — 2026-06-12

- **Comparison: a fast values copy.** The Compare tab now offers two
  outputs — tick one or both. The **values workbook** holds plain computed
  results: it opens instantly with everything already filled in (no F9, no
  manual-calculation mode, about a third the size) and keeps all the
  navigation links, colors, the Spot Check sheet and the live self-checks.
  The **live-formulas workbook** stays the fully auditable version where
  every cell recalculates. With both ticked, the values copy is saved next
  to the other as "… (values).xlsx". Both are built from the same comparison
  pass, so they can never disagree.
- **Comparison: missing routes front and center + self-checks.** The
  TSMIS-vs-TSN workbook gains two new sheets — **Only in TSMIS** and **Only
  in TSN** — collecting every one-sided row in one place instead of leaving
  them scattered through the 50k-row Comparison sheet. Routes one system
  lacks entirely are flagged **"entire route"** and tinted, so missing-route
  coverage is impossible to overlook (filter the "Missing from …" column to
  separate whole-route gaps from single locations). The Summary also gains a
  **SELF-CHECK section**: each headline number is recomputed a second,
  independent way and shows OK/CHECK after you press F9 — proof that every
  formula still points at the right rows.
- **Comparison: built for skeptics.** Don't trust a red cell? The
  row numbers in the TSMIS Row / TSN Row columns are now **clickable** —
  they jump to the data sheet and **select the whole source row** so it
  stands out until you click elsewhere, and every data-sheet row links back
  to its Comparison row the same way. A new **Spot Check** sheet audits any
  single location end to end: type a row number (or find one by route +
  location) and every field shows the raw stored values from both systems
  next to an **independently recomputed verdict** — calculated straight from
  the data sheets, never reading the Comparison's answer — with an Agree?
  column that flags any disagreement. One-sided rows announce themselves on
  every field line (not just the status cell), difference cells are labeled
  **TSMIS first, TSN second**, and consolidated workbooks show a bold
  press-F9 reminder.
- **The app updates itself.** When a new version is published here, a
  green **Update to vX.Y.Z** button appears in the app's title bar: one click
  downloads it (picking the right variant automatically), then **Restart to
  update** swaps it in and reopens the app — reports, login and settings stay
  exactly where they are, and a failed swap rolls back to the old version.
  The version chip next to the app name re-checks on demand. PCs where the
  app folder is read-only get a button that opens this download page instead.
  (In-app updates also skip the zip "Unblock" problem entirely.)

## v0.8.2 — 2026-06-11

- **Comparison: single-side rows now show their data.** Rows that
  exist only in TSMIS (yellow) or only in TSN (blue) used to have blank
  field cells; they now display that system's own values, so what's missing
  from the other system is readable at a glance.

## v0.8.1 — 2026-06-11

- **Fix: the downloaded app now starts without unblocking the zip.**
  Extracting the release zip without right-click → Unblock tags every file
  as "from the internet", and Windows then refuses to load parts of the new
  interface — v0.8.0 died on launch with "Failed to resolve
  Python.Runtime…". The app now removes that flag from its own files at
  startup, so a plain download-extract-run works. (Unblocking the zip first
  is still good practice for SmartScreen.)

## v0.8.0 — 2026-06-11

- **TSN Highway Log + comparison.** The Consolidate tab gains **TSN
  Highway Log**: drop TSN district PDFs into `input\tsn_highway_log` and it
  converts them into TSMIS-format per-route Excel files plus one combined
  workbook. A new **Compare tab** then builds a TSMIS-vs-TSN discrepancy
  workbook from two per-route Highway Logs **or two consolidated ones (all
  routes)** — matching values shown plainly, differences highlighted in red,
  with live Excel formulas throughout (edit a value and the report
  recalculates). Consolidated comparisons add a **Routes sheet** (which
  routes each system covers, what's missing where, per-route diff counts)
  and open in **manual calculation** so the big workbook appears instantly —
  press **F9** once to calculate, then save.
- **A brand-new interface.** The window was rebuilt from scratch:
  a cleaner two-column layout (settings on the left, live progress + activity
  log on the right), per-route progress with running counts, clearer sign-in
  status, a searchable route picker, and a **System / Light / Dark theme
  toggle**. Most importantly it now **fits any screen** — on small or
  low-resolution displays the layout stacks and scrolls instead of cutting
  off the bottom buttons. (Under the hood the UI is rendered by Edge
  WebView2, which is part of Windows 10/11 — nothing extra to install; all
  export logic is unchanged.)
- **Chrome sign-in no longer nags about local network access.**
  Saving a login with Google Chrome used to require clicking "Allow" on the
  "access devices on your local network?" prompt every single time — and
  missing it meant the session silently didn't save. The sign-in windows now
  pre-grant that permission, same as the exports always have.

## v0.7.6 — 2026-06-11

- **The log now tells the whole story.** Every run writes a detailed
  trail to `data\logs\tsmis.log`: which build/PC produced it, every sign-in
  step, which browser was picked and why a fallback happened, what was clicked
  in the app, each route's outcome with timing and file size, and a full
  traceback for any crash (even ones the window can't show). Errors name the
  specific step that failed — so one log upload answers what used to take a
  back-and-forth.

## v0.7.5 — 2026-06-11

- **Sign-in works on the new TSMIS site.** Field diagnostics finally
  showed the sign-in was SUCCEEDING — and the tool's own post-sign-in
  "right data source?" check was then reloading the page, which destroys the
  app's memory-only session and strands the browser at the portal sign-in
  page. That check misread the app's config (it's not a `window` property)
  so it reloaded every time. Fixed: the config is read correctly, a reload
  happens only on a real env/src mismatch and is followed by a fresh sign-in
  pass, the IdP hop is driven directly via the portal's own SAML URL, and the
  log breadcrumbs every step of each sign-in attempt.
- **Pick the data source and environment.** Two new header dropdowns choose
  **SSOR or ARS** and **Prod / Test / Dev** (defaults: SSOR + Prod) — the tool
  now drives the new TSMIS site, one page for every combination. Console flow:
  set `TSMIS_SRC` / `TSMIS_ENV`.
- **Each day's exports get their own folder.** Files now land in
  `output\<YYYY-MM-DD>\<report>\`, so tomorrow's run starts fresh instead of
  skipping over today's files. The Consolidate tab gained an **Export day**
  picker (newest first, newest by default; console prompts, Enter = newest),
  and the combined workbook is saved in that day's `consolidated\` folder.
  Exports made with older versions are still found when no dated folders exist.
- **Fast mode is greyed out without a saved login**, with an explanation:
  automatic Edge sign-in runs one browser at a time (the sign-in profile can't
  be shared), so parallel runs need a saved session (e.g. sign in with Chrome).
- **Hands-free sign-in on managed Caltrans PCs** (since v0.6): after one normal
  Edge sign-in, login and exports sign themselves in automatically — no
  password, no window. Chrome stays on the manual sign-in path.
- First run: if Windows warns about an unknown publisher, choose
  "More info" → "Run anyway" (in-house unsigned tool). If downloaded as a zip,
  right-click → Properties → Unblock before extracting.

## v0.7.4 — 2026-06-11

- **Sign-in works on the new TSMIS site.** The portal showed its "Caltrans Azure
  AD" button before the button's click handler was wired up, so the tool's early
  click landed dead. It now keeps clicking each second until the page actually
  moves, and after several dead clicks drives the sign-in hop directly via the
  portal's own SAML URL. The Edge sign-in window also pre-grants the
  local-network permission.
- **Fits small screens.** The window caps its height to the screen and can be
  shrunk — the log pane absorbs the difference instead of the bottom buttons
  being cut off.

## v0.7.3 — 2026-06-11

- **Sign-in detection hardened, plus diagnostics.** Stronger signed-in detection
  (several post-sign-in signals, robust visibility checks) and deep sign-in
  diagnostics: the log records the app version and every sign-in attempt's
  outcome, and a failed sign-in saves a screenshot + page snapshot under
  `data\failures\` so problems can be pinpointed from one run.

## v0.7.2 — 2026-06-11

- **Sign-in works on the new TSMIS site.** The new app never shows a signed-out
  page — it redirects through the portal OAuth flow on every load and keeps its
  token in page memory only. The tool now rides that flow: it polls for the app's
  real post-sign-in state and clicks "Caltrans Azure AD" the moment the portal
  renders it, so saved Chrome sessions and the hands-free Edge sign-in work again
  (0.7.0/0.7.1 raced the redirect or watched for the wrong signals).

## v0.7.1 — 2026-06-11

- **Sign-in fix for the new report page.** The new page shows its own "Sign In
  with ArcGIS" button instead of redirecting, and renders the report form even
  when signed out — both broke automatic sign-in (Edge and Chrome) in 0.7.0. The
  tool now clicks the full chain (app button → portal page → "Caltrans Azure AD",
  popup-tolerant) and detects sign-in from the app's own state.

## v0.7.0 — 2026-06-11

- **Pick the data source and environment.** Two new header dropdowns choose
  **SSOR or ARS** and **Prod / Test / Dev** (defaults: SSOR + Prod) — the tool
  now drives the new TSMIS site, one page for every combination. Console flow:
  set `TSMIS_SRC` / `TSMIS_ENV`.

## v0.6.1 — 2026-06-10

- **Hands-free sign-in, refined.** After one normal Edge sign-in (which primes
  the app's own Edge profile), the tool signs in automatically — no password, no
  window — and exports can even start with **no saved login at all**: the export
  reopens that Edge profile, clicks "Caltrans Azure AD" itself, and Windows signs
  it in. Edge only (Chrome stays on the manual path); automatic sign-in runs one
  browser at a time, so save a login to use fast mode.

## v0.6.0 — 2026-06-10

- **Hands-free sign-in on managed Caltrans PCs.** The tool signs in
  **automatically** with Microsoft Edge and your Windows account — no password,
  no browser window. Each headless browser clicks "Caltrans Azure AD" itself and
  Windows signs it in (Edge only — Chrome stays on the manual sign-in path). The
  local-network permission the TSMIS site needs is pre-granted in every automated
  browser.

## v0.5.1 — 2026-06-10

- **Managed-Edge sign-in hardened.** Recovers the session even when org-managed
  Edge relaunches itself into the work profile mid-SSO (live capture, then CDP
  re-attach, then on-disk profile recapture), with a Google Chrome fallback if
  nothing was captured.

## v0.5.0 — 2026-06-10

- **Managed-Edge sign-in fixed.** Sign-in opens Edge with a durable app-owned
  profile and recovers the session even when org-managed Edge relaunches into the
  work profile mid-SSO, with a Google Chrome fallback if nothing was captured.

## v0.4.1 — 2026-06-05

- **Edge/Chrome login fixed.** Signing in no longer cancels itself the moment
  your password/MFA goes through — the session saves reliably.
- **A broken route fails fast.** If TSMIS itself errors on a route, it's recorded
  as Failed in seconds with the site's message instead of hanging for minutes.
- **Friendlier to IT / Defender.** Proper version details, an icon, and a
  no-admin manifest; the download is stripped of third-party documentation that
  could trip data-loss-prevention scanners.

## v0.4.0 — 2026-06-05

- **New report: Highway Log.** Bulk-export the Highway Log for every route
  (XLSX), plus a matching consolidator to combine them.
- **Export several report types at once.** Tick any combination (or all) and they
  run back-to-back in one go.
- **Cancel actually cancels now.** It stops the report it's currently working on
  right away instead of waiting for that route to finish first.
- **Fast mode is sturdier.** If one browser hits a snag the others keep going,
  and any routes that get dropped are retried rather than silently skipped.

## v0.3.0 — 2026-06-05

- **Much smaller — ~587 MB → ~148 MB.** No longer bundles Chromium; it uses the
  **Microsoft Edge (or Chrome) already installed** on the machine. This also
  fixes the SharePoint/DLP "blocked file" problem from the old bundled doc files.
- **Browser picker + startup checks in the header.** Choose Edge or Chrome, with
  readiness dots for the browser, output folder, and report tools.
- **Choose which routes to export.** Leave the Routes box blank for all, or type
  a few (e.g. `5, 99, 101`).
- **Automatic retry.** Routes that fail get one more patient, one-at-a-time
  attempt at the end of the run.
- **Login fixes.** Confirms you actually signed in before saving, and closing the
  sign-in window no longer leaves the app stuck on "Waiting…".

## v0.2.0 — 2026-06-04

- **Experimental fast mode.** Run several headless browsers at once to export
  routes in parallel (default 3, up to 30; each uses ~0.5 GB RAM).
- **Live elapsed timer** beneath the progress bar during a run.
- **Clearer run summary.** Adds an "already had" count for routes saved on a
  previous run, so the numbers reconcile to the full route count.

## v0.1.0-preview — 2026-06-04

- **Initial preview build.** First portable Windows release — no install, no
  Python required. Sign in with your Caltrans `@dot.ca.gov` account + MFA, export
  a report for every route, consolidate the per-route files into one workbook, and
  save a per-route outcome CSV. Bundles its own Chromium. Preview build, pending
  live verification against TSMIS.

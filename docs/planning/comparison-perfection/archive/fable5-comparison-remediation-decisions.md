# Comparison remediation — D1–D7 decision record (Fable 5)

> **Archived — historical.** Superseded by the current surface: [COMPLETION-PLAN.md](../COMPLETION-PLAN.md) (plan & status) and [README.md](../README.md). Kept verbatim as point-in-time history; counts/hashes here reflect when it was written.

Date: 2026-07-11
Scope: resolves the seven domain-policy gates in
`docs/planning/comparison-perfection/comparison-remediation-plan.md` before implementation. No product code,
ledger, or plan file was modified. Every premise below was re-verified in code this
session unless explicitly labelled **[memory]** (remembered intent, not repository
evidence) or **[probe]** (a fresh read-only measurement over the local ground-truth
data, commands retained in the session scratchpad).

New empirical inputs produced for this record:

- **[probe]** County-collision census over the real raw TSN extracts —
  (route, postmile) identities spanning ≥2 counties:
  Ramp Detail **81 / 15,328** identities (15,410 rows, `TSAR - RAMPS
  DETAIL_TSN_11.04.2025IT.xlsx`; e.g. route 101 @ 047.851 in both HUM and SCL);
  Intersection Detail **78 / 16,527** (16,626 rows, 6.19 extract; e.g. route 1 @
  009.851 in LA and ORA); Highway Detail **453 / 59,091** (60,083 rows, 7.7 extract,
  key = RTE + PP+POSTMILE; e.g. 001 @ R000.170 in ORA and SB). The HD number is an
  upper bound (my probe key omits the pm_canon roadbed letter), but multi-county
  identities demonstrably exist in every family, including HD.
- Live-Excel COM + Python fixture results from the second-opinion session (three-way
  count disagreement; greedy-worse-than-positional 8×8) remain the D2/D3 base evidence.

---

## D1 — partial canonical artifact and cache policy

**Selected policy: keep-last-complete canonical + distinct unpromoted partial
generation (the plan's recommended option), with the cache defined as "last committed
trustworthy generation plus a separate latest-attempt overlay."**

Concretely:

1. The canonical consolidated path always holds the **last complete generation**. A
   partial (or failed/cancelled/no-data) refresh never replaces it.
2. A useful partial attempt is published under a distinct unpromoted identity (e.g.
   a ` (partial)`-suffixed sibling or generation-addressed name — naming is an
   implementation choice, but it must be visibly non-canonical and carry its own
   outcome metadata).
3. Freshness of the canonical artifact is judged against the current source
   fingerprint as today — so when a partial attempt exists, the canonical complete
   artifact reads **stale (superseded inputs), never fresh-current**. The stale reason
   must name the partial attempt ("inputs changed; last refresh was partial —
   retry"). This is the guard against "stale complete data looks current".
4. Comparisons may read the partial generation only through an explicit,
   completion-carrying path (`outcome.comparable()` semantics: partial → compare but
   flag end-to-end); the resulting cell/cache/workbook/evidence all carry
   `completion=partial` and render amber with no checkmark and no "match" main text,
   and remain selected by "Refresh stale".
5. **Caches represent the last committed generation** (with its completion), never a
   bare latest attempt; a separate `AttemptState` records the most recent
   failed/cancelled/partial attempt so it is durable without erasing last-good
   (CMP-AUD-089). Export-store promotion stays complete-only (unchanged).

**Repository evidence.** The conflict is real and must be settled exactly here:
`docs/planning/v0.18.0/05-claude-final-plan.md:268-278` specifies replace-and-flag for
consolidations ("`partial` ⇒ compare but flag"; keep-last-good listed only for the
export store) and `:271` allows "cache records … `complete|partial`";
`consolidate_xlsx_base.py:276-314` implements it (partial commits onto the canonical
path; "status stays ok so the file that WAS produced is still offered", `:289-294`),
and `matrix_build.py:289-290` stamps a fresh fingerprint for any `status=ok` including
partial. Against that, the **current published contracts** say the opposite:
`CLAUDE.md` ("a partial/failed/cancelled refresh keeps last-good (never clobbers
it)"), `docs/engine-and-reliability.md:83-84` ("a partial run can never be promoted,
cached, or shown green"), and `outcome.promotable()`'s own docstring
(`outcome.py:131-134`: "Only a COMPLETE result may replace the live store copy / be
cached as fresh (the F1 promote gate, the F3 cache gate)"). The defects that exist
under *either* contract: renderer `✓ match` main text on partial
(`ui-matrix.js:296-299`), partial cells excluded from Refresh-stale
(`matrix_state.py:248-259` + `matrix_build.py:203`), the day consolidation badge
ignoring completion (`matrix_build.py:353-360`), and evidence publishing partial
silently.

**Why keep-last-complete wins.** (a) It is what the currently published user-facing
contract already promises — choosing it means no doc weakening, only code catching up;
(b) plan invariant 6 ("old bytes are preserved until a replacement generation is
validated") already mandates the machinery, so replace-and-flag would leave that
invariant half-true for the most common artifact class; (c) the 085 false-green class
dies structurally (a partial can never sit at the canonical path) instead of by flag
discipline across five consumers; (d) the operational cost — a transient unreadable
file (an Excel owner lock, CMP-AUD-029) demoting a refresh — is mitigated because the
complete artifact survives and the retry is one click.

**[memory]** The v0.26.2 field episode (work-PC HL-PDF days blanket-flagged partial by
over-eager escalation, requiring manual force re-consolidation per day) cuts both
ways: it shows partial states must be *retryable in place* (point 4/5 above) and that
false-partial classification is as painful as false-complete — the producer-side
accuracy work in Phase 4 is what actually retires that pain.

**Compatibility/migration.** Existing canonical workbooks whose sidecar says
`partial` (rare) read as unpromoted attempts: stale, retryable, never green — no file
deletion (`consolidation_meta.read_completion`'s conservative ladder,
`consolidation_meta.py:229-256`, already supports this). First-ever consolidation of a
day/store that ends partial has no prior complete generation: publish the partial
generation as the only (unpromoted) artifact and let comparisons read it flagged.
`CLAUDE.md`/`engine-and-reliability.md` keep their sentences; the v0.18 plan is
history and stays unedited.

**Canary impact.** None on comparison counts. Matrix render/state checks change
(`check_mx_partial_render`, `check_matrix*`: partial cells become stale-selectable,
main text loses `✓ match`); the golden checks that lock partial-cache-fresh behavior
are `expectation-to-change`.

**Confidence:** high on the policy; medium on the unpromoted-artifact naming (pick
during Phase 5 design).

**User question.** Only one: for the *comparison* workbook itself (not the
consolidation), when its inputs are partial, do you want the comparison still written
to the normal cell path (flagged partial, as today) or also generation-suffixed? I
recommend the normal path + flags — comparisons are cheap to rebuild and their cache
carries the truth — but it is a visible-artifact choice you may care about.

---

## D2 — canonical equality

**Selected policy: the current Python `compared_cell` semantics become the written
canonical contract; formulas are regenerated to mirror them exactly. Python is
authoritative; Excel is a projection.** This is deliberately the
minimum-semantic-change option: it freezes today's values/Python behavior (keeping
Route-1 = 969 and every statewide values canary), and moves all divergence cost into
the live-formulas re-bless that Phase 3 requires anyway.

Truth table (all comparisons operate on load-normalized text):

| Case | Rule | Today (Python) | Today (live Excel) |
|---|---|---|---|
| Letter case (`ABC` vs `abc`) | **Different** (case-sensitive; mirror via `EXACT`) | different (`compare_core.py:391`) | equal — changes |
| Whitespace | Edge-strip + internal ASCII-space runs collapse (TRIM semantics, `compare_core.py:319-325`); **tabs/CR/LF/NBSP normalized to a single space at load by every loader** (generalizing `compare_highway_log.py`'s tab rule; fixes the 047 class; Excel-expressible because it happens before the workbook) | partial (per-loader drift) | TRIM only |
| Numeric vs text (`5` vs `"5"`) | **Equal** — numerics stringify canonically at load; integral floats drop `.0` (`5.0`≡`"5"`); non-integral keep Python repr (`0.5`≢`".5"`) | equal | equal |
| Booleans | Normalize at load to text `TRUE`/`FALSE`; boolean TRUE ≡ text `TRUE`, ≢ `true` (case rule applies after normalization) | different | equal |
| >15 significant digits | **Exact text equality.** New writer guard: numerics beyond 15 significant digits are written as text cells (Excel itself corrupts them at parse; without this the mirror is impossible) | exact | rounded |
| Blank vs zero | **Distinct.** Blank ≡ blank only; display `(blank)`; Spot Check "Comparison sheet shows" gains the `ISBLANK` wrap (`compare_core.py:1162` today lacks the guard `raw()` has at `:1129-1131`) | distinct | Spot Check shows 0 |
| Literal Excel errors (`#N/A` etc.) | **Literal text**, compared as text (`#N/A`≡`#N/A`, ≢`OK`). The literal-cell guard extends from `_FORMULA_LEAD` (`compare_core.py:749-754`) to `openpyxl ERROR_CODES` so error text can never become a live error cell | text | live error, hidden diff |
| `≠` marker in source data | Content only. Diffs counts, CF, Summary, `read_counts` all consume structured per-cell state, never `SEARCH` (`compare_core.py:894-897,923-924,937`; `matrix_state.py:191`) | miscounts | miscounts |
| Med-Wid numeric part | Zero-pad-insensitive unsigned `digits[.digits]` (`0Z`≡`00Z`, `06V`≡`6V`) | equal | equal |
| Med-Wid signed / leading-decimal (`-06V`, `.50`) | **Not numeric — compare as raw text** (`-06V`≢`-6V`, `.50`≢`0.5`). Signed medians and bare-decimal widths are not legitimate report values; treating them as numbers (Excel `VALUE`) launders anomalies | different | equal — changes |
| Med-Wid suffix case (`6v` vs `6V`) | **Different** (suffix case-sensitive) | different | equal — changes |

The formulas flavor re-implements `_medwid_norm`'s exact branches with
`EXACT`/`LEFT`/`RIGHT`/digit tests instead of `VALUE` as a second engine
(`compare_core.py:665-669` today), and the Diffs column becomes a sum of per-field
equality expressions rather than a marker scan. Acceptance is the three-surface gate:
Python counts = values Summary = live `CalculateFullRebuild` Summary = Comparison Diffs
= Spot Check = Report View input, per adversarial fixture.

**Rationale for case sensitivity** (the one genuinely contestable row): both source
systems are uppercase-normalized; a case difference is a real data anomaly the tool
exists to surface. **[memory]** The v0.26.1 quote-note episode is the precedent — a
coworker-visible "identical-looking" diff (`''F'' ST` vs `"F" ST`) was a real data
edit, and the product answer was to *label* the invisible class, not normalize it
away. Case differences are the same class.

**Compatibility/migration.** Values workbooks and all Python-side counts:
byte/count-identical on real data (the changed rows above affect only adversarial
inputs — pre-flight: sweep the statewide consolidated/TSN workbooks for `" ≠ "`,
mixed-case pairs, error tokens, >15-digit numerics; expected zero occurrences).
Live-formulas workbooks change formula text — the regression lock's re-bless
procedure applies (cell-for-cell COM value-agreement proof on
`ground-truth/inputs`), with the formula-text delta reviewed once.

**Canary impact.** Route-1 969 unchanged; live-formula Summary totals move *toward*
the values totals wherever they previously disagreed (that is the point). Any live
delta on real data must be explained by one of the table rows above.

**Confidence:** high. **User question:** confirm case-sensitivity (recommended
different) and the Med-Wid signed/leading-decimal "raw text" rows — these are the only
rows where a defensible alternative exists (Excel-compatible leniency), and they were
chosen to keep Python counts stable and anomalies visible.

---

## D3 — duplicate pairing

**Selected policy: exact minimum-cost assignment for every group within the existing
product cap, via a pure-Python Hungarian algorithm; deterministic; monotonicity
guard; capped groups stay file order with a structured note.**

- Groups with `perm(nc, nr) ≤ 5040` keep the existing exhaustive search (byte-stable
  behavior + tie handling; `compare_core.py:422-432`).
- Larger groups up to the existing `len_t × len_n ≤ 100,000` cap
  (`_PAIR_GROUP_CAP`, `compare_core.py:372`) switch from greedy (`:433-441`) to an
  O(n³) Hungarian assignment (pure stdlib, ~100 lines; 316×316 worst case is
  well under a second). Rectangular groups: pad the smaller side with zero-cost
  virtual rows (equivalent to today's min-side matching); matched pairs are numbered
  in side-A file order exactly as now (`:477`), unmatched leftovers keep the existing
  side-unique numbering.
- Tie-breaking: deterministic by construction (stable input order = file order; the
  implementation must be scan-order deterministic; where multiple optima exist the
  first found in row-major order wins). Both flavors and goldens therefore agree.
- **Monotonicity guard (hard):** after assignment, if `total > positional_total`,
  fall back to file order. For a correct Hungarian this is a free assertion (optimal ≤
  any assignment); it exists so no future edit can reintroduce the proven failure —
  my 8×8 fixture where greedy scored 56 vs file-order 8 becomes the pinned regression.
- Above the cap: file order (unchanged), but the result carries a structured
  `pairing_capped_groups` count and a workbook note; it does **not** demote
  completion (coverage is complete; pairing quality is the caveat).
- The pairing trace (group → matched index pairs) is persisted with the result for
  evidence (CMP-AUD-108) per Phase-3 E2.

**Repository evidence.** `_min_cost_pairs` docstring claims monotonicity the greedy
branch does not have (`compare_core.py:366-370, 406-441`); the fixture above proves
it. **[memory + repo]** The v0.18 plan deferred this exact item pending "a locked-
engine change + full cell re-proof" (`05-claude-final-plan.md:754`) — Phase 3 *is*
that re-proof cycle, so the deferral reason dissolves; this record satisfies the
"explicit separate user decision" it asked for, pending your sign-off.

**Compatibility/migration.** None on disk. **Canary impact:** any real dataset with
≥8-duplicate groups may see diff counts *decrease* (greedy → optimal). Route-1 and
each statewide canary must be re-measured; every delta must be attributable to a
specific duplicate group's improved pairing (the re-bless explains them cell-by-cell).
HD's known repeated-PM tie-break follow-up (v0.26.0 roadmap note) is expected to be
the visible beneficiary.

**Confidence:** high. **User question:** none — but note this is a locked-engine
change and lands only inside Phase 3's re-proof gate.

---

## D4 — Ramp/Intersection (and Highway Detail) row identity

**Selected policy: county joins the identity tuple wherever a postmile is the key,
because California postmiles are county-relative. Exact tuples:**

| Report | Identity tuple (all flavors: env, Excel↔TSN, PDF↔TSN, PDF↔Excel) | County source |
|---|---|---|
| Highway Sequence | (Route, County, glued prefix+PM+suffix) — **already implemented** for vs-TSN (`compare_highway_sequence_tsn.py:18-22, 114-123`); extend to cross-env + PDF flavors | own County column both sides |
| Ramp Detail | (Route, **County**, `norm_pm(PM)`) | TSN `LOCATION` `"01-DN-101"` (`compare_ramp_detail_tsn.py:89`); TSMIS consolidated Location col 1 — currently skipped (`:199-205`) |
| Intersection Detail | (base Route, **County**, `norm_pm(PM)`); Route Suffix stays a compared column (existing design, `compare_intersection_detail_tsn.py:183-198`); the explicit consolidated Route and `S` fields become validated source claims per CMP-AUD-070 | both sides' Location token `"12 ORA 001"` (`:168`; TSN `LOCATION`) |
| Highway Detail | (Route, **County where available**, `pm_canon`) — TSN and PDF-sourced TSMIS sides adopt county now; the **Excel-sourced TSMIS side cannot** (no county column in the 34-column export, `compare_highway_detail_tsn.py:88-96`) — see the open question | TSN `CNTY` (DCR block); TSMIS-PDF DCR line (e.g. `"11 IMP 007"`, per CMP-AUD-049 evidence); TSMIS Excel: **none** |

**Repository evidence / probe.** The domain rule is stated verbatim in the repo:
"CALIFORNIA postmiles are COUNTY-RELATIVE (a route restarts at 000.000 in each
county), so route+PM is NOT unique across a route — the key is route + county +
postmile" (`compare_highway_sequence_tsn.py:18-22`). The probe quantifies the
exposure on real data: RD 81, ID 78, HD 453 multi-county identities (header of this
document). **I dispute the ledger's HD exemption** (CMP-AUD-045: "Highway Detail's
canonical glued postmile … is not affected"): the 453 real collisions include
prefixed keys (`001 @ R000.170` in ORA and SB), and `pm_canon`'s roadbed letter
(`compare_highway_detail_tsn.py:156-164`) encodes roadbed, not county, so it cannot
separate them in general. The practical mitigation HD does have is that duplicate
groups pair by similarity within document order — which is exactly the masking
mechanism CMP-AUD-045 demonstrates elsewhere.

**Compatibility/migration.** Key changes alter row alignment → all affected canaries
re-bless (expected: one-sided pairs *split* per county — strictly refining, like the
roadbed key: "can split, never merge", `docs/comparison-engine.md:257`). The
normalized TSN libraries must start carrying county as a first-class column where
they don't (`normalization_version` bumps for `ramp_detail`, `intersection_detail`,
and `highway_detail` per the D2/D4 rebuild rule; the ledger notes RD/ID libraries
already retain county/district sidecars that loaders slice away — CMP-AUD-045).
Duplicate-pairing (D3) then operates within the refined groups.

**Canary impact.** RD/ID/HSL/HD statewide counts change where the 81/78/453
identities previously cross-paired: expect small shifts in both/one-sided/diff-cell
counts, each explainable as a county split. Route-1 HL is unaffected (HL's key is the
roadbed-canonical Location, not a bare PM).

**Confidence:** high for HSL/RD/ID; medium for HD.

**User questions (domain owner):** (1) For HD Excel-vs-TSN, is there an authoritative
TSMIS-side county derivation you trust — e.g. the county token printed in the per-route
report body/DCR that the Excel export preserves anywhere, or an official county-
boundary postmile table? If not, HD Excel-vs-TSN keeps (Route, pm_canon) with the 453-
identity exposure documented and similarity pairing scoped per county on the TSN side
only where determinable. (2) Confirm county participates as a *key component* (my
selection) rather than a compared column only — the probe says yes, but it changes
one-sided counts on re-bless.

---

## D5 — aggregate taxonomy (Ramp footnote, P/V)

**Selected policy: the footnote is excluded metadata; P/V are TSN-only structural
categories (`sides="tsn"`), emitted one-sided by design; the engine's verdict
semantics are unchanged.**

1. `Ramp Points w/out linework` never enters the comparison universe — it renders on
   the familiar sheet only. This is already the written contract in three places:
   `summary_layout.py:69-75` ("TSMIS-only footnote categories"), `:79-82`
   ("Footnotes are NOT compared — they live only on the familiar sheet"), and the
   shipped Notes text `:163-168` ("shown below the table and never compared"). The
   defect is one emit path (`compare_ramp_summary_tsn.py:175-186` appends it;
   CMP-AUD-024); the fix is consuming `SummarySpec.side_categories`/`categories()`
   as designed.
2. Ramp Types `P - Dummy Paired` and `V - Dummy, Volume only` get `sides="tsn"`
   (`summary_layout.py:152,154` currently default `"both"`), using the exact
   mechanism the Intersection Summary diverged codes already use (`Cat.sides`,
   `:48-52`, "user chose one-sided, no crosswalk") and matching the shipped Notes
   text ("they stay one-sided by design", `:164-165`). Absent-from-TSMIS is
   structural, **not** an explicit zero: a `0 vs count` "Both" row asserts agreement
   the TSMIS report never expresses.
3. Verdict: structural one-sided rows continue to make the verdict `diff`, exactly as
   Intersection Summary's accepted 58/8/0 design does today. No new "structural
   one-sided doesn't block match" tier — that would be a locked-engine
   status-vocabulary change affecting IS too.

**Compatibility/migration.** Aggregate loaders/emitters only; no engine change.
**Canary impact (Ramp Summary, from the chunk-12 baseline 31 both / 1 TSMIS-only / 0
TSN-only / 27 differing):** footnote row disappears (TSMIS-only 1 → 0); P and V move
Both → TSN-only (both 31 → 29, TSN-only 0 → 2); differing/diff-cell counts drop by the
two `0 vs count` cells. Verdict remains `diff` on real data (P/V carry real TSN
counts). Re-bless with these exact expected deltas.

**Confidence:** high — this is enforcing already-documented intent.

**User question:** none required. Optional future item: whether you *want* a Ramp
Summary that reads `match` when only structural rows remain — if yes, that is a new
engine feature to schedule deliberately (it would also change IS), not part of this
remediation.

---

## D6 — PDF↔Excel self-check asserted fields

> **Superseded Highway Sequence identity detail (source proof 2026-07-13):** this
> advisory response correctly selected a same-source asserted-field profile, but its
> statement below that equate seating should remain one-sided inherited the historical
> 7.8-Excel/first-7.9-PDF fixture. The complete same-run event ledger proves
> PDF↔Excel identity is Route + County + prefix + base PM + occurrence, with suffix
> asserted: 272 two-row moves (544 suffix cells) plus five PDF-only suffixes. Full PM
> including suffix remains correct for vs-TSN. See CMP-AUD-199; this note preserves the
> original second-opinion record while preventing it from overriding later source fact.

Governing rule (applies to all five): **a same-source flavor gets its own projection
profile containing render-equivalences only** (whitespace/tab normalization, zero-pad
numeric normalization, date-format canon) — never cross-SYSTEM crosswalks, whose whole
purpose is reconciling TSN encodings (CMP-AUD-067). Per comparator:

1. **Highway Log PDF↔Excel** (`compare_highway_log_pdf.py:44-46,76-81` — reuses the
   approved HL schema wholesale). Asserted: all 30 data fields. Retained: Med Wid rule
   (both renders zero-pad differently) and **ditto non-asserting** (`+`-runs are a
   print convention on either render; asserting them floods non-differences).
   Retained: the roadbed-canonical key for pairing. **Changed:** the raw Location text
   must additionally be asserted (as a compared value or a dedicated raw-identity
   column) so the known ~11-row Excel suffix-drop export bug
   (`docs/comparison-engine.md:271-273`) is flagged instead of laundered by the HG
   inference (the 067 case). Rationale: identical source, identical conventions —
   the only legitimate differences are render artifacts, which are exactly what this
   check exists to catch.
2. **Highway Sequence PDF↔Excel** (`compare_highway_sequence_pdf.py:101-105` —
   currently clones the vs-TSN schema, inheriting HG/City/Distance-to-next as
   context). **Asserted: all 7 non-key fields** — the three suppressions' documented
   rationales are explicitly TSN-granularity arguments
   (`compare_highway_sequence_tsn.py:49-57`) that cannot apply when both sides are
   TSMIS renderings (CMP-AUD-065's false-clean). No Description prefix stripping;
   assert raw. Expected new signal: the equate-row seating differences already noted
   in the one-sided note (`:139-140`) stay one-sided, not field diffs.
3. **Highway Detail PDF↔Excel** (wrapper over the base schema; `CONTEXT_FIELDS = ()`
   — "position-aligned: nothing suppressed", `compare_highway_detail_tsn.py:98`).
   Asserted: all 34 non-key fields (unchanged). **Changed:** the same-source loaders
   drop the TSN-only crosswalks — NA blank≡`A`, WDA merge, and pm_canon's HG-derived
   roadbed inference for suffix-less tokens (each hid a real render difference in
   CMP-AUD-067). Retained: `NUMERIC_FIELDS` zero-pad normalization (`:101-104`) and
   date canon — genuine render variance. The known real residue (the newer-build
   ' / '-merged descriptions; the 2,484/2,487 canary) keeps flagging — that is the
   check working. **[memory]** v0.20.0 explicitly valued this self-check for
   surfacing exactly that export discrepancy.
4. **Intersection Detail PDF↔Excel** (wrapper; `CONTEXT_FIELDS = ()` per the recorded
   **user decision 2026-06-24**, `compare_intersection_detail_tsn.py:87,102-108`).
   Asserted: all fields (unchanged). **Changed:** the compare-time J→S signal
   crosswalk (`_project`, applied to both sides) is removed for the self-check — raw
   control-type codes are asserted (067's `J` vs `A` displayed as rewritten `S ≠ A`).
   Date canon retained (both renders print the same format; the projection is
   idempotent there). **[memory]** The v0.26.1 quote-note decision (quotes compare
   literally; the Notes sheet documents it) is the same philosophy: same-source
   flavors surface bytes.
5. **Ramp Detail PDF↔Excel** (`compare_ramp_detail_pdf.py:236-243` — inherits the
   base schema untouched). Asserted: the 7 shared non-key fields (PR, Date of Record,
   HG, Area 4, City Code, R/U, Description). **Context (correctly): Ramp Name,
   On/Off, Ramp Type, ADT** — the Excel export genuinely lacks them (consolidated
   positions, `compare_ramp_detail_tsn.py:198-201`), so asserting would manufacture
   blank-vs-value noise; the PDF↔TSN flavor is where On/Off + Ramp Type are asserted
   (`:229-234`) and stays unchanged. The `_x000d_` escape residuals keep flagging —
   genuine render artifact (v0.26.0 canary's 4 residuals). Description prefix
   handling: both sides share the TSMIS convention; assert raw.

**Compatibility/canaries.** HL and RD self-checks: expected no count change on the
existing blessed pairs except where the newly-asserted raw Location (HL) exposes the
~11 known Excel suffix-drop rows — an expected, explainable increase. HSL self-check:
counts rise wherever HG/City/Distance genuinely differ between renders — re-bless on
the 7.9 print set and record the delta. HD/ID: deltas only where the removed
crosswalks were masking render differences; each must be enumerated at re-bless.
Every change lands per family inside its Phase-4 L-batch with mutation fixtures
proving each un-suppressed field flips the verdict.

**Confidence:** high (HL ditto retention and RD context set are the two judgment
calls; both rest on hard column-availability facts).

**User question:** none blocking. Flag for awareness: HSL self-check will stop
reading "identical 59,082-class" clean if the two renders really disagree on
City/HG/Distance — if the first re-bless shows large legitimate render variance
there, you get to choose between accepting the noise or moving specific fields back
to context *with a written render-variance rationale* (not a TSN rationale).

---

## D7 — classic accepted input shapes

**Selected policy: narrow to the truth; expose the one already-implemented capability
the picker blocks; build nothing new.**

1. Accepted shapes become registry-owned per recipe/role (extensions + shape + hint
   text), rendered per selected recipe. The universal "two per-route workbooks or two
   consolidated workbooks" hint (`ui-compare.js:144-153`, CMP-AUD-074) is wrong for
   14 of 17 file recipes and is replaced by per-recipe text.
2. Per-route + consolidated dual-shape remains advertised **only** for the three
   Highway Log recipes — the only adapters with dynamic route-ness
   (`compare_tsn_common.py:188-190,214-215`; `compare_highway_log.py` loader).
3. The Ramp Summary and Intersection Summary vs-TSN recipes' TSN role gains the
   `*.pdf` filter and matching hint: the raw statewide-PDF path is already implemented
   and production-tested in both parsers (`compare_ramp_summary_tsn.py:97-112,
   212-221`; `compare_intersection_summary_tsn.py:147-160,249-257`; CMP-AUD-073
   verified the branches) — the XLSX-only picker (`gui_compare_api.py:92-102`, no
   key/role passed) is the only blocker. This is unblocking existing support, not new
   surface.
4. No other raw/per-route loader support is added. **[memory]** This matches standing
   scope decisions: 1b/5b were deliberately left export-only because their siblings
   already consolidate/compare; nothing in the field history shows a per-route
   comparison workflow for the non-HL reports.
5. Selection state binds to (recipe key, role) and clears/restores on recipe change;
   endpoints preflight existence/type/shape before claiming the task (the CMP-AUD-016
   fixes, scoped per the verified nuance that folder-dropdown picks already get a
   membership preflight at `gui_compare_api.py:246-257` while file recipes and
   Browse-absolute paths get none).

**Compatibility/migration.** UI + picker only; stable recipe keys unchanged; no
artifact or canary impact. **Confidence:** high. **User question:** confirm you have
no desired per-route comparison workflow for non-HL reports (if one exists, name the
report and it becomes a scoped feature request, not part of remediation).

---

## Plan-review answers

### Are Phase-1 safety batches S1–S5 safe to begin unchanged?

**Yes — all five are decision-independent and safe to start now**, with four
execution notes:

- **S1:** put the alias check *inside* `artifact_store.commit_workbook` (plus the
  pre-dialog UI check), so matrix/day/evidence callers inherit it; the plan's wording
  permits this — make it explicit in the batch. Windows hardlink/junction detection =
  resolved paths + `os.path.samefile` (file-ID based); evidence siblings
  (`visual_evidence.sibling_paths`) must be in the checked destination set.
- **S2:** shipping "legacy markers untrusted for deletion" before the Phase-5 marker
  v2 migration means Reset temporarily cannot delete stores stamped by v0.19–v0.26
  (`gui_worker_maint.py:86-89` currently trusts any marker). That is the correct
  fail-closed direction; accept the degradation knowingly and say it in the Reset
  preview ("created before this version — left untouched; re-export to re-adopt, or
  delete manually"). Keep the existing unmarked-name warning path (`:90-97`) as is.
- **S4:** define fail-closed precisely: on any scanner hit the bundle is written
  *redacted* or not written at all, with the offending member named — never shipped
  with a warning. Expect and accept false-positive friction in log-heavy bundles.
- **S5:** blocking a missing explicit TSN selection needs a small snapshot/UI state
  ("selection missing — re-pick or clear") on all three matrices + validation; still
  Phase-1-sized, but touch `matrix_state`/`ui-matrix.js` deliberately, not just the
  resolver (`tsn_library.py:617-620`).

### Is any dependency or migration step incorrectly ordered?

Four adjustments, none structural:

1. **Report View self-check row (Phase 7 V1) must move its *Summary-side* half into
   Phase 3 E1.** "Add Report View to independent Summary self-checks" changes
   regression-locked Summary label/formula text; as scheduled it forces a *second*
   locked-engine re-bless epoch after Phase 3's. Add the self-check row (even if it
   initially reads a placeholder/parity value) during E1's one re-bless; Phase 7 then
   only re-points Report View content.
2. **CMP-AUD-075 is double-migrated as written.** Phase 2 publishes per-member
   outcome sidecars in the v1 format; Phase 5 replaces them with the comparison
   manifest. Either scope Phase 2 to the in-memory result (all committed members
   reported) plus the *existing single sidecar's* correctness, or accept writing the
   twin's v1 sidecar knowing Phase 5 rewrites the format. Pick one in the batch
   description so the twin-sidecar format doesn't ship twice by accident.
3. **`ensure_current`'s contract is touched twice** (Phase 4 L2's "rebuild stale
   libraries rather than compare-time patching", CMP-AUD-037; Phase 8 A1's raw-only
   first-build, CMP-AUD-118). Define the one new contract (current / stale-rebuild /
   first-build / no-raw) in L2 and have A1 consume it, or you will re-litigate the
   None-return semantics (`tsn_library.py:457-469`) twice.
4. **S2 ↔ marker-v2 gap** (above) is an accepted ordering consequence, not an error —
   record it as such in Phase 0's decision log so the Reset behavior change isn't
   mistaken for a regression in the field.

Everything else orders correctly: Phase 2 before 3 (structured counts exist before
`read_counts` is replaced), Phase 3 before 4 (engine accepts richer keys before
loaders supply county), Phase 4 before 5 (loader truth before identity epoch), Phase 5
before 6/7 (generation identity before matrix adoption and evidence binding).

### Is the 120-finding primary coverage mapping missing or materially misplaced?

All 120 IDs appear exactly once in the index (independently tallied). Three material
issues:

1. **Index vs narrative "primary" conflicts.** CMP-AUD-114/116 are indexed Phase 2
   but Phase 8 A2 lists "Primary findings: 011, 114–116, 119"; CMP-AUD-115 is indexed
   Phase 5 but appears in the same A2 list; M1 lists 083–085/087/105 as "primary"
   though the index assigns them Phase 5/Phase 1. Harmless if everyone reads the
   index as authoritative — say so explicitly in the plan's index preamble, or the
   closure audit will double-count.
2. **Phase 4 batch assignment of 047–050 is contradictory and, as indexed, violates
   invariant 10.** The index buckets 046–050 under "Phase 4 generic loaders" (L1)
   while L4's narrative claims 047–050. CMP-AUD-047/048 are Highway-Log-specific
   (`compare_highway_log.py`, `highway_log_columns.recognize`) and belong in L4;
   CMP-AUD-049/050 span all five PDF families plus `pdf_table_lib`/Ramp-Summary
   consolidation — they need either a named shared-PDF-conversion contract batch or
   explicit per-family slices (my recommendation: a small "L0-PDF shared conversion
   contract" batch for the `pdf_table_lib` route-universe/duplicate rules, then
   per-family provenance enforcement inside L4–L7).
3. **CMP-AUD-066 and 067 are indexed narrower than their verified surface.** 066
   ("Phase 4 Highway Log provenance") applies to HSL/HD/ID wrappers too
   (`compare_highway_sequence_pdf.py`, `compare_highway_detail_pdf.py`,
   `compare_intersection_detail_pdf.py` accepted wrong-role inputs); 067 (indexed L7)
   is the cross-family D6 implementation spanning L4–L7. Both should be split per
   family or explicitly marked cross-batch with per-family acceptance, or four of the
   five families' fixes have no scheduled home.

One smaller note: CMP-AUD-010's correction half ("preserve source origin and real
path in `tsn_meta`") is Phase-5-shaped metadata work consumed by the Phase-6 fix;
keep 010 in Phase 6 but add the `tsn_meta` fields to the Phase-5 schema list so M1
doesn't invent them ad hoc.

---

## Decision summary

| Gate | Selection | Confidence | Open user item |
|---|---|---|---|
| D1 | Keep-last-complete canonical + unpromoted partial generation; caches = last committed generation + attempt overlay; export-store unchanged | High | Comparison-workbook partial naming (recommend: normal path + flags) |
| D2 | Current Python semantics become the written contract; formulas mirror via EXACT-based generation; errors literal; >15-digit as text; marker = content | High | Confirm case-sensitive + Med-Wid strict rows |
| D3 | Hungarian exact assignment ≤ existing cap; monotonicity guard; capped groups file-order + structured note; trace persisted | High | Sign off locked-engine re-proof (satisfies the v0.18 deferral condition) |
| D4 | County joins the key for HSL (done), RD, ID, and HD-where-derivable; probe: 81/78/453 real multi-county identities | High (RD/ID/HSL), Medium (HD) | HD Excel-side county derivation? Key-component confirmation |
| D5 | Footnote display-only; P/V `sides="tsn"` one-sided by design; verdict semantics unchanged | High | None (optional future: structural-match tier) |
| D6 | Same-source flavors assert everything both renders carry; render-equivalence-only projection; RD keeps its 4 Excel-absent context fields; HL keeps ditto+MedWid + asserts raw Location | High | Awareness: HSL self-check counts will rise |
| D7 | Narrow hints/filters to registry truth; expose the existing Summary raw-PDF path; no new loaders; bind selection to recipe+role | High | Confirm no non-HL per-route workflow exists |

S1–S5: begin unchanged (four execution notes). Plan ordering: sound with four
adjustments (Report View self-check row into E1; 075 single-migration scoping;
one `ensure_current` contract; S2 gap recorded as accepted). Coverage index: complete
but fix the index-vs-narrative "primary" conflicts and re-home 047–050/066/067 before
Phase 4 batching.

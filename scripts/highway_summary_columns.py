"""Single source of truth for the Highway Summary layout — sections, codes, and
the strict reader every Highway Summary workflow shares.

Highway Summary is the app's first MILES-measured aggregate report. Its per-route
export is not a row-per-record table but a fixed statistics document: a
"TOTAL MILES SELECTED" scalar followed by 10 category sections, each a
`Code | Miles` block. Censused on the 2026-08-17 statewide prod delivery
(252 routes): ONE skeleton across every file — same sheet name, same 129x2
shape, same section order, same 95 code rows, values numeric with at most three
decimals.

Why the taxonomy lives here and not in `summary_layout`: that module is the shared
spec/renderer for the aggregate summaries, but its `parse_count` contract requires
whole numbers, so the MILES layout is written down here — the same role
`highway_detail_columns` plays for Highway Detail. The consolidator, the
cross-environment loader AND the vs-TSN comparator all read through
`values_from_rows` / this taxonomy, so no two paths can drift (the CMP-AUD-018
rule). `summary_spec()` projects it into a `summary_layout.SummarySpec` so the
vs-TSN comparison renders the SAME familiar sheet the other two aggregates use,
via that module's opt-in measure mode (v0.37.0) — which leaves the two COUNT
specs byte-identical.

Each category also carries the WITHIN-SECTION `code` both systems share. TSMIS and
TSN spell every label differently, so the vs-TSN comparison pairs on the code, not
the text; `sides` marks the three categories only TSMIS classifies.

Miles are carried internally as exact integer THOUSANDTHS. The export prints at
most three decimals, so thousandths are lossless, and statewide rollups sum
exactly instead of accumulating binary-float error.

Kept import-light: the data + the readers need no third-party libs.
"""
import re
from dataclasses import dataclass

# The scalar that leads every per-route sheet.
TOTAL_LABEL = "TOTAL MILES SELECTED"
TOTAL_KEY = "Total Miles"

SHEET_NAME = "Highway Summary"            # the export's own sheet name
ROUTE_COL = "Route"

# The report's own title/subtitle lines (skipped by the reader, asserted by
# `recognize_sheet` so a different report cannot be read as this one).
TITLE_LINE = "TSAR - Highway Summary"
SUBTITLE_LINE = "'HIGHWAY INVENTORY'"     # the export writes it quoted
_COLUMN_HEADER = ("Code", "Miles")        # each section's own header row

# --------------------------------------------------------------------------- #
# The censused skeleton: ordered sections, each with its ordered code rows.
# Transcribed FROM the 2026-08-17 statewide delivery (all 252 routes agree) —
# `build/check_highway_summary_layout.py` re-proves it against real exports.
# --------------------------------------------------------------------------- #
SECTIONS_RAW = (
    ("HIGHWAY GROUP", (
        "R- RIGHT  IND ALIGN",
        "L- LEFT  IND ALIGN",
        "X- UNCONSTRUCTED",
        "U- UNDIVIDED",
        "D- DIVIDED",
    )),
    ("ACCESS CONTROL", (
        "C- CONVENTIONAL",
        "E- EXPRESSWAY",
        "F- FREEWAY",
        "S- ONE-WAY CITY STREET",
        "Z- NOT REPORTED",
        "+- NO DATA GIVEN",
    )),
    ("RURAL-URBAN", (
        "R- RURAL - I - INSIDE CITY",
        "R- RURAL - O - OUTSIDE CITY",
        "U- URBAN - I - INSIDE CITY",
        "U- URBAN - O - OUTSIDE CITY",
        "--INVALID DATA",
    )),
    ("NON-ADD", (
        "N Non-Add",
    )),
    ("MEDIAN TYPE", (
        "(UNDIVIDED)",
        "A- NOT SEPARATED OR STRIPED",
        "B- STRIPED",
        "C- REVERSIBLE PEAK HR LANES",
        "(DIVIDED)",
        "E- REVERSIBLE PEAK HR LANES",
        "F- TWO WAY LEFT TURN LANE",
        "G- CONTINUOUS LEFT TURN LANE",
        "H- PAVED MEDIAN",
        "J- UNPAVED MEDIAN",
        "K- SEPARATE GRADES",
        "L- SEPARATE GRADE WITH WALL",
        "M- SAWTOOTH - UNPAVED",
        "N- SAWTOOTH - PAVED",
        "P- DITCH",
        "Q- SEPARATE STRUCTURES",
        "R- RAILROAD",
        "S- BUS LANES",
        "T- PAVED AREA USED BY TRAFFIC",
        "U- BOTH BUS LANE AND RR",
        "V- CONTAINS SEP REV. PK HR LN",
        "Z- OTHER",
    )),
    ("MEDIAN BARRIER", (
        "A- CABLE",
        "B- CABLE WITH MESH GLARE SCREEN",
        "C- METAL BEAM",
        "D- METAL BEAM WITH GLARE SCREEN",
        "E- CONCRETE",
        "F- CONCRETE WITH GLARE SCREEN",
        "G- BRIDGE BARRIER RAILING",
        "H- CHAIN LINK FENCE",
        "J- GUARDRAIL IN MEDIAN BOTH WAYS",
        "K- GUARDRAIL IN MEDIAN - LEFT",
        "L- GUARDRAIL IN MEDIAN -RIGHT",
        "M- TWO WAY ONE LANE ROAD",
        "N- THRIE BEAM",
        "P- THRIE BEAM WITH GLARE SCREEN",
        "Q- CONCRETE BARRIER, BOTH ROADWAYS",
        "R- CONCRETE BARRIER, LEFT ROADWAY",
        "S- CONCRETE BARRIER, RIGHT ROADWAY",
        "X- BARRIERS EXTERNAL",
        "Y- OTHER (NOT LISTED ABOVE)",
        "Z- NO BARRIER",
        "+- NO DATA GIVEN",
    )),
    ("MEDIAN WIDTH", (
        "0  -  4",
        "5  -  9",
        "10  -  14",
        "15  -  19",
        "20  -  24",
        "25  -  29",
        "30  -  34",
        "35  -  39",
        "40  -  44",
        "45  -  49",
        "50  -  54",
        "55  -  59",
        "60  -  99",
        "- NO DATA",
    )),
    ("NUMBER OF LANES", (
        "1  -  3",
        "4  -  5",
        "6  -  7",
        "8  -  9",
        "10  -  11",
        "12  -  UP",
    )),
    ("TERRAIN", (
        "F- FLAT",
        "M- MOUNTAINOUS",
        "R- ROLLING",
        "Z- NOT REPORTED",
    )),
    ("DESIGN SPEED", (
        "0  -  29",
        "30  -  34",
        "35  -  39",
        "40  -  44",
        "45  -  49",
        "50  -  54",
        "55  -  59",
        "60  -  64",
        "65  -  69",
        "70  -  100",
        "- NO DATA",
    )),
)

# Sections whose category miles are NOT a partition of the route total. NON-ADD
# reports non-add mileage, a SUBSET marker that is independent of the total (it
# never equalled the total on any of the 252 censused routes). Every other
# section is a partition — but a BOUNDED one: on the 2026-08-17 delivery six
# routes tabulate less than their total (HIGHWAY GROUP on 099/101/125/170/905,
# MEDIAN TYPE on 099/101/170/180, NUMBER OF LANES on 101), which is the site's
# own tabulation, not a parse loss. A section summing ABOVE the total is
# impossible and is refused (see `partition_problem`).
INDEPENDENT_SECTIONS = frozenset({"NON-ADD"})

_WS = re.compile(r"\s+")
_SLUG = re.compile(r"[^a-z0-9]+")


def norm_label(text):
    """A code/section label as compared: whitespace collapsed, upper-cased.

    Matching is deliberately whitespace- and case-insensitive: the export's
    cosmetic double spaces ('R- RIGHT  IND ALIGN') are not identity, so a
    spacing tweak must not fail a route, while a real code change still does.
    """
    return _WS.sub(" ", str(text or "")).strip().upper()


def _slug(text):
    return _SLUG.sub("_", str(text).lower()).strip("_")


@dataclass(frozen=True)
class Cat:
    """One category row: `label` is the export's own text (display), `key` is the
    unique section-qualified compare key (the consolidated column header), and
    `slug` is the stable internal identifier.

    `code` is the WITHIN-SECTION identity both systems share — the leading letter
    (`R`, `+`), the normalized range (`0-4`), or a compound (`R-O`). TSMIS and TSN
    spell the same category differently (`R- RIGHT  IND ALIGN` vs `R-RIGHT IND
    ALIGN`; `A- NOT SEPARATED OR STRIPED` vs `A-NOT SEPARATED OR STRIPED (A )`),
    so the code — not the label — is what the vs-TSN comparison pairs on.

    `sides` says which system classifies the category: "both" (compared), or
    "tsmis" for the two TSMIS-only ones (see `_TSMIS_ONLY`)."""
    section: str
    label: str
    key: str
    slug: str
    norm: str          # norm_label(label) — what the reader matches on
    code: str
    sides: str = "both"


@dataclass(frozen=True)
class Section:
    name: str
    cats: tuple
    norm: str

    @property
    def independent(self):
        return self.name in INDEPENDENT_SECTIONS


# Categories only ONE system tabulates (censused on the 2026-08-17 TSMIS release
# + the 2025-09-15 statewide TSN print, `Highway Summary Statewide_TSN.pdf`):
#
#  * MEDIAN TYPE `(UNDIVIDED)` / `(DIVIDED)` — group SUB-HEADERS, not measurements.
#    TSN prints them as bare labels with no mileage column; the TSMIS export emits
#    them as rows whose value is 0 on every one of the 252 routes (verified
#    statewide). Comparing a structural 0 against an absent label would invent a
#    match, so they stay TSMIS-only and land under 'Only in TSMIS'.
#  * DESIGN SPEED `- NO DATA` — the TSN print has no such row at all (MEDIAN WIDTH
#    does, so this is a per-section fact, not a print-wide one).
_TSMIS_ONLY = {
    ("MEDIAN TYPE", "(UNDIVIDED)"),
    ("MEDIAN TYPE", "(DIVIDED)"),
    ("DESIGN SPEED", "- NO DATA"),
}

# The within-section code for a TSMIS label. Range sections key on the normalized
# range itself; RURAL-URBAN needs its parent letter (both '-O' rows would collide
# on 'O'); everything else keys on the leading letter / '+'.
_RANGE_SECTIONS = frozenset({"MEDIAN WIDTH", "NUMBER OF LANES", "DESIGN SPEED"})
_LETTER_RE = re.compile(r"^([A-Z+])\s*-")
_RANGE_RE = re.compile(r"^(\S+)\s*-\s*(\S+)$")


def range_code(text):
    """A `LOW - HIGH` range as its canonical code ('0-4'), or None."""
    m = _RANGE_RE.match(_WS.sub(" ", str(text or "")).strip())
    return f"{m.group(1)}-{m.group(2)}".upper() if m else None


def _code_for(section, label):
    up = norm_label(label)
    if section == "NON-ADD":
        return "N"
    if section == "RURAL-URBAN":
        if up.startswith("-"):                      # '--INVALID DATA'
            return "INVALID"
        parent = up[0]                              # R / U
        return f"{parent}-O" if " - O " in f" {up} " or "- O -" in up else parent
    if section in _RANGE_SECTIONS:
        code = range_code(label)
        if code is not None:
            return code
        return up                                   # '- NO DATA'
    m = _LETTER_RE.match(up)
    if m:
        return m.group(1)
    return up                                       # '(UNDIVIDED)' / '(DIVIDED)'


def _build_sections():
    out = []
    for name, labels in SECTIONS_RAW:
        cats = tuple(
            Cat(section=name,
                label=_WS.sub(" ", label).strip(),
                key=f"{name}: {_WS.sub(' ', label).strip()}",
                slug=f"hs_{_slug(name)}_{_slug(label)}",
                norm=norm_label(label),
                code=_code_for(name, label),
                sides=("tsmis" if (name, _WS.sub(" ", label).strip()) in _TSMIS_ONLY
                       else "both"))
            for label in labels)
        out.append(Section(name=name, cats=cats, norm=norm_label(name)))
    return tuple(out)


SECTIONS = _build_sections()
CATS = tuple(c for s in SECTIONS for c in s.cats)

# The consolidated per-route sheet's header: Route, the total, then every
# category key in source order.
HEADER = [ROUTE_COL, TOTAL_KEY] + [c.key for c in CATS]

assert len(SECTIONS) == 10, "the censused Highway Summary has 10 sections"
assert len(CATS) == 95, "the censused Highway Summary has 95 category rows"
assert len({c.key for c in CATS}) == len(CATS), "category keys must be unique"
assert len({c.slug for c in CATS}) == len(CATS), "category slugs must be unique"
assert TOTAL_KEY not in {c.key for c in CATS}, "the total key must not collide"
# The code is the vs-TSN pairing identity, so it must be unique WITHIN a section
# (across sections it repeats by design — 'Z' is both a Terrain and a Median code).
for _s in SECTIONS:
    assert len({c.code for c in _s.cats}) == len(_s.cats), (
        f"{_s.name}: category codes must be unique within a section")
assert sum(1 for c in CATS if c.sides == "tsmis") == len(_TSMIS_ONLY), (
    "every _TSMIS_ONLY entry must match exactly one category label")


def cats_for(side):
    """The categories a `side` ('tsmis' | 'tsn') classifies. A category the other
    system doesn't have is omitted here for that side, so it lands in the
    comparison's 'Only in …' sheet instead of being compared against nothing."""
    return tuple(c for c in CATS if c.sides in ("both", side))


def code_index(side="tsn"):
    """{(section, code): Cat} for the categories `side` classifies."""
    return {(c.section, c.code): c for c in cats_for(side)}


TOTAL_SLUG = "hs_total_miles"

# The TSN print's own footnotes, and the measured consequence. Shown on the
# familiar sheet so a reader never mistakes the total row for a like-for-like
# comparison.
TOTAL_SEMANTICS_NOTE = (
    "TOTAL MILES SELECTED is NOT like-for-like: the TSN print states '* Non-Add "
    "Mileage not included' and '* Unconstructed Mileage not included', and its "
    "figures bear that out (its Highway Group sums to exactly the total PLUS its "
    "unconstructed mileage). The TSMIS export applies no such exclusion. Measured "
    "on the bound pair: TSMIS reports 0.000 unconstructed miles statewide, TSN "
    "1,289.296. A difference on the total row is therefore expected."
)


def summary_spec():
    """This layout as a `summary_layout.SummarySpec`, so the vs-TSN comparison
    renders the SAME familiar 'Summary by Category' sheet the other two aggregate
    summaries use. Built here (rather than restating the taxonomy in
    summary_layout) so `SECTIONS_RAW` stays the one place the layout is written
    down. Carries the MILES measure reader/format — the shared renderer's default
    is the integer COUNT behavior the other two specs keep."""
    import summary_layout as _sl

    def _read(v):
        """A miles cell as a float for display, or None when it isn't a number
        (an absent or masked source value must stay blank, never become 0)."""
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).replace(",", "").strip())
        # A non-numeric cell on a DISPLAY sheet must render BLANK — not crash,
        # and never 0. The COMPARED values are parsed strictly by `parse_miles`,
        # which does raise; this reader only feeds the familiar sheet.
        except ValueError:  # silent-ok: an unreadable display cell stays blank (CMP-AUD-021)
            return None

    sections = tuple(
        _sl.Section(name=s.name,
                    cats=tuple(_sl.Cat(slug=c.slug, label=c.label, key=c.key,
                                       code=c.code, sides=c.sides)
                               for c in s.cats))
        for s in SECTIONS)
    return _sl.SummarySpec(
        report="Highway Summary",
        sheet_name="Summary by Category",
        title="Highway Summary — TSMIS vs TSN by category (statewide miles)",
        sections=sections,
        total=_sl.Cat(slug=TOTAL_SLUG, label=TOTAL_LABEL, key=TOTAL_KEY, code=""),
        notes=(TOTAL_SEMANTICS_NOTE,
               "Mileage is compared to three decimals — what both systems print. "
               "The TSN print carries a Daily Vehicle Miles column and an AVERAGE "
               "DAILY TRAFFIC section that the TSMIS export does not tabulate at "
               "all; neither is compared.",
               "MEDIAN TYPE '(UNDIVIDED)' and '(DIVIDED)' are group sub-headers "
               "the TSMIS export emits as 0 on every route and the TSN print does "
               "not measure, and the TSN print has no DESIGN SPEED '- NO DATA' "
               "row; all three stay one-sided by design."),
        value_reader=_read,
        value_format=r"#,##0.000",
        measure_noun="Miles",
    )

_SECTION_BY_NORM = {s.norm: s for s in SECTIONS}


def recognize(header):
    """Is `header` (a loaded row-1 list) the CONSOLIDATED Highway Summary layout?
    Returns True when recognized, else None. Compared by the full label list so a
    same-width different report cannot sneak through."""
    return True if list(header) == list(HEADER) else None


# --------------------------------------------------------------------------- #
# strict value parsing
# --------------------------------------------------------------------------- #
MILLI = 1000                        # miles are carried as integer thousandths
_MAX_DECIMALS = 3


def parse_miles(value, *, source, category):
    """One miles cell as exact integer THOUSANDTHS.

    A mileage must be a non-negative number with at most three decimals (what
    the export prints). Booleans, over-precise values, and any other text raise
    ValueError naming the source and category — malformed data must never
    silently coerce into a different distance."""
    from decimal import Decimal, InvalidOperation
    if isinstance(value, bool):
        raise ValueError(f"{source}: the {category!r} mileage is a boolean "
                         f"({value!r}), not a number")
    if isinstance(value, (int, float)):
        try:
            d = Decimal(str(value))
        except InvalidOperation:            # nan / inf reach here as text
            raise ValueError(f"{source}: the {category!r} mileage {value!r} is "
                             "not a finite number") from None
    elif isinstance(value, str):
        s = value.strip().replace(",", "")
        if not s:
            raise ValueError(f"{source}: the {category!r} mileage cell is empty text")
        try:
            d = Decimal(s)
        except InvalidOperation:
            raise ValueError(f"{source}: the {category!r} mileage {value!r} is "
                             "not a number") from None
    else:
        raise ValueError(f"{source}: the {category!r} mileage has unsupported "
                         f"type {type(value).__name__}")
    if not d.is_finite():
        raise ValueError(f"{source}: the {category!r} mileage {value!r} is not finite")
    if d < 0:
        raise ValueError(f"{source}: the {category!r} mileage {d} is negative")
    if -d.as_tuple().exponent > _MAX_DECIMALS:
        raise ValueError(f"{source}: the {category!r} mileage {value!r} carries "
                         f"more than {_MAX_DECIMALS} decimals — the export prints "
                         "three, so this layout is not the one this app reads")
    return int((d * MILLI).to_integral_value())


def miles(milli_value):
    """Integer thousandths back to a miles float for display/workbook cells."""
    return milli_value / MILLI


def values_from_rows(rows, *, source):
    """Read one per-route Highway Summary sheet.

    `rows` is the sheet's (col A, col B) value pairs in order. Returns
    `(total_milli, {slug: milli})`.

    The skeleton is STRICT: the sections and their code rows must appear in the
    censused order, complete, with nothing extra. That exactness is the tripwire
    — the site renaming a section, adding a code, or dropping rows fails the
    route loudly here instead of silently producing a table that compares clean
    against an equally-broken other side. Raises ValueError naming `source` and
    the first difference.
    """
    total = None
    expected = [(s, c) for s in SECTIONS for c in (None,) + s.cats]
    seen = []
    values = {}
    cur = None

    for a, b in rows:
        a_s = str(a).strip() if a is not None else ""
        b_blank = b is None or str(b).strip() == ""
        if not a_s:
            # A spacer row is blank in BOTH columns. A value with no label cannot
            # be attributed to a category, and the skeleton check below would not
            # see it (it never enters `seen`), so refuse here rather than let an
            # unattributable mileage pass unnoticed.
            if not b_blank:
                raise ValueError(
                    f"{source}: the mileage {b!r} appears with no category label — "
                    "the export layout has changed; this app needs an update for it")
            continue
        norm_a = norm_label(a_s)
        if norm_a in (norm_label(TITLE_LINE), norm_label(SUBTITLE_LINE)):
            continue
        if (norm_a == norm_label(_COLUMN_HEADER[0])
                and norm_label(b) == norm_label(_COLUMN_HEADER[1])):
            continue
        if norm_a == norm_label(TOTAL_LABEL):
            if total is not None:
                raise ValueError(f"{source}: {TOTAL_LABEL!r} appears twice")
            total = parse_miles(b, source=source, category=TOTAL_LABEL)
            continue
        if b_blank:                              # a bare label = a section heading
            section = _SECTION_BY_NORM.get(norm_a)
            if section is None:
                raise ValueError(
                    f"{source}: unknown section heading {a_s!r} — the export "
                    "layout has changed; this app needs an update for it")
            cur = section
            seen.append((section, None))
            continue
        if cur is None:
            raise ValueError(f"{source}: the value row {a_s!r} appears before any "
                             "section heading — unexpected layout")
        cat = next((c for c in cur.cats if c.norm == norm_a), None)
        if cat is None:
            raise ValueError(
                f"{source}: unknown {cur.name} category {a_s!r} — the export "
                "layout has changed; this app needs an update for it")
        if cat.slug in values:
            raise ValueError(f"{source}: the {cur.name} category {a_s!r} appears "
                             "twice — refusing to read an ambiguous table")
        values[cat.slug] = parse_miles(b, source=source, category=cat.key)
        seen.append((cur, cat))

    if total is None:
        raise ValueError(f"{source}: no {TOTAL_LABEL!r} row was found — the export "
                         "layout has changed; this app needs an update for it")
    if seen != expected:
        raise ValueError(f"{source}: {_first_skeleton_difference(expected, seen)}")
    return total, values


def _first_skeleton_difference(expected, seen):
    """A human-readable description of the first skeleton deviation."""
    def name(entry):
        section, cat = entry
        return f"section {section.name!r}" if cat is None else f"{section.name}: {cat.label!r}"

    for i, exp in enumerate(expected):
        if i >= len(seen):
            return (f"the sheet ends early — expected {name(exp)} after "
                    f"{len(seen)} rows; the export layout has changed")
        if seen[i] != exp:
            return (f"expected {name(exp)} but found {name(seen[i])} — the export "
                    "layout has changed; this app needs an update for it")
    return (f"the sheet has {len(seen) - len(expected)} unexpected extra row(s) — "
            "the export layout has changed")


def partition_problem(total, values, *, source):
    """The strict partition problem for one parsed route, or None when sound.

    Every section except `INDEPENDENT_SECTIONS` tabulates a SUBSET of the route
    total: it may sum below (measured on six routes of the 252-route census —
    the site's own tabulation) but never above. A section summing above the
    total means rows were misattributed, so the route is refused."""
    for section in SECTIONS:
        if section.independent:
            continue
        ssum = sum(values.get(c.slug, 0) for c in section.cats)
        if ssum > total:
            return (f"the {section.name!r} block sums {miles(ssum):,.3f} miles, "
                    f"MORE than the route total {miles(total):,.3f} — the export "
                    "layout may have changed; refusing a table that cannot "
                    "reconcile")
    _ = source                                    # named for caller symmetry
    return None


def partition_notes(total, values):
    """Display-only note lines for sections that tabulate BELOW the route total
    (the censused bounded residuals). Never a warning — the residual is the
    site's own, and is exposed rather than fabricated into a category."""
    notes = []
    for section in SECTIONS:
        if section.independent:
            continue
        ssum = sum(values.get(c.slug, 0) for c in section.cats)
        if ssum < total:
            notes.append(f"'{section.name}': {miles(ssum):,.3f} of "
                         f"{miles(total):,.3f} miles tabulated "
                         f"({miles(total - ssum):,.3f} not classified by the site).")
    return notes

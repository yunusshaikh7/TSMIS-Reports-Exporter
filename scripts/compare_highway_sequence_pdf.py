"""PDF-sourced Highway Sequence comparisons (mirrors compare_highway_detail_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine.
The PDF-consolidated TSMIS workbook has the IDENTICAL 10-column layout the Excel
export produces (Route + the 9 export columns, the postmile prefix/suffix in
their two unnamed columns), so both flavors read it BY POSITION:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN, riding compare_highway_sequence_tsn's
    loaders/schema unchanged (full glued-postmile identity incl. the equate
    suffix; TSMIS own-route label stripped; TSN Descriptions verbatim). At
    EQUATE points the print uses the SAME convention the TSN prints do, so the
    PDF side pairs BETTER there than the Excel side.
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel), the same-report
    self-check. CMP-AUD-199: the two renders seat the equate "E" suffix on
    DIFFERENT rows of an equate pair BY DESIGN, so the suffix is NOT identity
    here — rows key on Route + County + the prefixed postmile WITHOUT the
    suffix, and "PM Suffix" is its own compared column (each moved equate = two
    honest suffix cells instead of four fabricated one-sided rows; the census
    proved one route-152 duplicate group where suffix-glued keys silently
    swapped two different physical rows). Both sides are the same system, so
    EVERY column is asserted (no context suppression) and Descriptions are
    compared verbatim (no route-label stripping on either side).

Each flavor owns its Notes sheet; the engine's formula/label text is untouched,
so the compare_core regression lock stays intact. The GUI's Compare tab drives
these through COMPARE_REPORTS ("files" input kind); `file_a_label`/
`file_b_label` name the two file pickers.
"""
import re
from dataclasses import replace

import compare_highway_sequence_tsn as _hsl
import compare_tsn_common as ctc
from compare_core import CompareSchema, keys_for
from compare_tsn_common import (load_consolidated_rows, run_files_compare,
                                suggest_route_name)

# The vs-TSN notes, adjusted for the PDF-sourced TSMIS side: the key/context/
# description bullets carry over; the equate bullet describes the PRINT
# convention (which matches TSN's, unlike the Excel export's).
_NOTES_PDF_VS_TSN_TITLE = "Highway Sequence — TSMIS (PDF) vs TSN: comparison notes"
_NOTES_PDF_VS_TSN = (
    "Rows are keyed on Route + County + Postmile. California postmiles are "
    "county-relative (a route restarts at 000.000 in each county it crosses), so "
    "the postmile alone is not unique across a route — County is part of the key.",
    "The postmile carries a glued realignment prefix (\"R000.129\") and/or an equate "
    "suffix (\"050.025E\"); the TSMIS prefix/PM/suffix columns are re-glued to match.",
    "A handful of rows print with NO county (46 statewide TSN \"EQUATES TO\" "
    "annotations that appear before the route's first county-bearing row — TSN's own "
    "cover warns equate ownership may be wrong) or NO postmile (five TSMIS rows). "
    "They key under the explicit \"(county not printed)\" / \"(no postmile printed)\" "
    "markers and surface honestly, usually one-sided — never dropped or backfilled.",
    "One-sided rows are expected and honest: TSN lists every segment break (including "
    "unnamed ones), while TSMIS omits most unnamed breaks.",
    "At EQUATE points the TSMIS print uses the SAME convention as the TSN print — an "
    "annotation row at the realignment postmile with no feature type, plus the \"E\" "
    "suffix on the equated plain postmile — so equates mostly pair up cleanly here. "
    "The annotation descriptions still differ on purpose: the TSMIS print writes "
    "\"EQUATES TO <label>\" (or just \"EQUATES TO\") where TSN writes the bare "
    "\"EQUATES TO\".",
    "Descriptions: the TSMIS export prepends the row's own route as a label "
    "(\"001/NB OFF TO DOHENY PK RD\") — that label alone is stripped before "
    "comparing. TSN text is compared VERBATIM: TSN's numeric route prefixes "
    "(including ones naming a DIFFERENT route) are authoritative source claims, so "
    "TSMIS \"103 SEP 53-145\" vs TSN \"1/103 SEP 53-145\" is a REAL difference.",
    "EVERY column is compared, including three that are noisy for a STRUCTURAL "
    "reason rather than a data disagreement (owner decision 2026-08-10; they were "
    "context columns before): HG — TSMIS leaves the highway-group blank for whole "
    "counties while TSN always fills it, so expect many blank-vs-U cells; City — TSN "
    "assigns a city code far more aggressively than TSMIS; and Distance To Next Point "
    "— measured to each system's OWN next listed point, and since TSN lists more "
    "breaks its gap is usually smaller (TSN also prints pointer markers \"*P*\" and "
    "\"-------->\" there, conserved verbatim). Read differences in those three as "
    "listing/assignment differences unless the rest of the row agrees.",
)

# The PDF-vs-Excel self-check notes (CMP-AUD-199): the same report rendered two
# ways — identity excludes the moving equate suffix, every column is asserted.
_NOTES_PDF_VS_EXCEL_TITLE = ("Highway Sequence — TSMIS (PDF) vs TSMIS (Excel): "
                             "comparison notes")
_NOTES_PDF_VS_EXCEL = (
    "Both sides are TSMIS — the same report rendered two ways (the site's Print "
    "layout vs the Excel export). Apart from the by-design classes below, every "
    "cell should match; a residual difference means the two renders genuinely "
    "disagree (the statewide census caught the Excel export dropping a "
    "Description that the print carries).",
    "Rows are keyed on Route + County + the prefixed postmile WITHOUT its equate "
    "suffix; \"PM Suffix\" is its own compared column, because the two renders "
    "seat the \"E\" on DIFFERENT rows of an equate pair (keying on the glued "
    "suffix instead would fabricate four one-sided rows per moved equate, and "
    "the census proved one route-152 duplicate group where it silently swapped "
    "two different physical rows).",
    "EQUATE relations are NORMALIZED before comparing (owner ruling 2026-07-26; "
    "the relation count is on the Summary and at the end of these notes). A "
    "postmile equation is ONE fact spelled two ways: the print writes an "
    "annotation line \"EQUATES TO <label>\" with HG / FT / Distance / suffix "
    "blank and the \"E\" on the equated postmile, while the Excel export folds "
    "the label, the segment's flags and often the \"E\" itself onto the "
    "realignment record. Each render's OWN marker is removed (the print's "
    "\"EQUATES TO \" prefix; the export's label-less \"PM EQUATION\"), the "
    "annotation line's HG / FT are dropped because the print structurally has "
    "none there, and the relation's suffix is seated on its target row. Before "
    "this rule the class published 3,707 differing cells statewide that were "
    "spelling, not data.",
    "What the equate rule does NOT hide: the landmark label itself (a changed "
    "label is still a difference), the target row's own HG / FT / Distance / "
    "Description, and an \"E\" that only ONE render carries anywhere in the "
    "relation — statewide seven of those remain, and every one is a real "
    "disagreement about whether the marker exists at all. The rule fires only "
    "where the PRINT declared an equate, and only on that relation's two rows. "
    "Where a postmile carries MORE THAN ONE row, each render matches the "
    "relation to its own row by content; a group it cannot resolve that way is "
    "left completely alone, so a neighbouring record that merely shares the "
    "postmile is never rewritten.",
    "EVERY column is compared here (no context columns): both sides are the same "
    "system, so an HG/City/Distance disagreement is a real render difference, not "
    "a listing artifact. Descriptions are compared verbatim on both sides (no "
    "route-label stripping — both renders print the same labels).",
    "The print is an HTML render, so whitespace runs inside a Description collapse "
    "to one space; the comparison collapses both sides, so padding never counts. "
    "The same-source rule also decodes the Excel export's OOXML escapes (a "
    "handful of cells carry an encoded line break, \"_x000d_\") and ignores edge "
    "tab padding — encoding artifacts one render structurally cannot carry are "
    "never counted as data differences.",
)


# --------------------------------------------------------------------------- #
# the same-source (PDF vs Excel) shape — CMP-AUD-199
# --------------------------------------------------------------------------- #
SS_HEADER = ["County", "PM", "PM Suffix", "City", "HG", "FT",
             "Distance To Next Point", "Description"]
SS_KEY_FIELD = SS_HEADER.index("PM")           # 1


def _tsmis_row_same_source(r):
    """One consolidated TSMIS row in the same-source shape: the key is the
    prefixed postmile WITHOUT the equate suffix (the suffix moves between the
    two renders of one equate pair), the suffix is its own compared cell, and
    the Description keeps its route label (both renders print it)."""
    def at(i):
        return r[i] if i < len(r) else None
    route = _hsl._v(at(0))
    county_raw = at(1)
    prefix, pm, suffix = at(3), at(4), at(5)
    key = _hsl._physical_pm_key(
        route, county_raw, _hsl._glue_pm(prefix, pm, None),
        (("route", _hsl._raw_text(at(0))),
         ("county", _hsl._raw_text(county_raw)),
         ("postmile_prefix", _hsl._raw_text(prefix)),
         ("postmile", _hsl._raw_text(pm)),
         ("postmile_suffix", _hsl._raw_text(suffix))),
        "the consolidated TSMIS workbook")
    return [route,
            _hsl._norm_county(county_raw),
            key,
            _hsl._v(suffix),
            _hsl._v(at(2)),
            _hsl._v(at(6)),
            _hsl._v(at(7)),
            _hsl._v(at(8)),
            _hsl._desc_plain(at(9))]


def _load_tsmis_same_source(path):
    return load_consolidated_rows(
        path, _hsl.TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Highway Sequence workbook.",
        bad_header_msg="isn't a CONSOLIDATED Highway Sequence workbook "
                       "(expected a leading 'Route' column) — consolidate first.",
        row_transform=_tsmis_row_same_source)


# --------------------------------------------------------------------------- #
# the equate relation - HF-06 / PCOA-FINAL-011
# --------------------------------------------------------------------------- #
# A postmile EQUATION is ONE fact the two renders spell differently by design.
# The print writes it the way the TSN prints do - an annotation line at the
# realignment postmile carrying "EQUATES TO <label>" with the flag, distance
# and suffix cells structurally BLANK, followed by the equated postmile's own
# line carrying the "E" suffix. The Excel export has no annotation convention
# at all: it folds the marker, the label, the segment's flags and (about a
# quarter of the time) the "E" itself onto the realignment record.
#
# Measured on the frozen 2026-07-23 statewide pull (60,254 rows both sides):
# 1,119 relations, and the two spellings accounted for 3,707 of the 3,714
# differing cells the self check published - FT 1,119, Description 1,119,
# HG 929, PM Suffix 540. Every one of the 1,119 print annotation lines had
# HG / FT / Distance / suffix blank, and every Description paired exactly:
# 693 as "EQUATES TO <label>" against the Excel export's bare "<label>", and
# 426 as a bare "EQUATES TO" against the Excel export's "PM EQUATION" - the
# two renders' spellings of an equation carrying no landmark label.
#
# So each render's OWN marker is removed and the relation's suffix is seated
# in ONE canonical place, and what is left is compared exactly as before. The
# rule is deliberately narrow and FAILS OPEN: it fires only where the print
# declared an equate, only on that relation's two rows, and it never touches
# a value the print did not structurally omit. Nothing about equality changes
# - the rows the engine sees do - so both output flavors agree by
# construction and compare_core is untouched.
_SS_ROUTE, _SS_COUNTY, _SS_PM, _SS_SUFFIX = 0, 1, 2, 3
_SS_CITY, _SS_HG, _SS_FT, _SS_DIST, _SS_DESC = 4, 5, 6, 7, 8

# The print's marker, and the Excel export's spelling of a label-less equation.
EQUATE_MARKER = "EQUATES TO"
EQUATE_GENERIC_LABEL = "PM EQUATION"
_EQUATE_ANNOTATION_RE = re.compile(r"^" + EQUATE_MARKER + r"(?:\s+(.*))?$")
# The flags the print's annotation line never carries and the Excel export
# repeats from the segment. Distance is blank in BOTH renders, so it is not
# here: it never differed and must keep being compared.
_EQUATE_ANNOTATION_FLAGS = (_SS_HG, _SS_FT)


def _cell(value):
    return "" if value is None else str(value).strip()


def _equate_label(description):
    """The equate's LABEL as the PRINT spells it ("" for a bare marker), or
    None when this Description is not the print's own annotation text."""
    match = _EQUATE_ANNOTATION_RE.match(description)
    return None if match is None else (match.group(1) or "").strip()


def _is_print_annotation(row):
    """True for the print's equate ANNOTATION line: an "EQUATES TO ..."
    Description with the suffix, flag and distance cells all blank. The blank
    structure is REQUIRED, not assumed - a print that one day carried a flag
    there is not this class, and its cells stay compared."""
    return (_equate_label(_cell(row[_SS_DESC])) is not None
            and not _cell(row[_SS_SUFFIX])
            and not _cell(row[_SS_HG])
            and not _cell(row[_SS_FT])
            and not _cell(row[_SS_DIST]))


def _is_annotation_for(row, label):
    """True when `row` is EITHER render's annotation line for a relation whose
    print label is `label`.

    This is the CONTENT test that says which row of a duplicate postmile group
    a relation actually owns (RB5-R1-001). The print writes its own marker
    ("EQUATES TO <label>"); the Excel export writes the label alone - or
    "PM EQUATION" for a label-less equation - and leaves Distance blank there.
    """
    description = _cell(row[_SS_DESC])
    if _is_print_annotation(row):
        return _equate_label(description) == label
    return (not _cell(row[_SS_DIST])
            and description == (label or EQUATE_GENERIC_LABEL))


def _resolve_annotation(rows, group, label, print_group_size):
    """This render's row index for the relation's annotation line, or None
    when that correspondence is not unambiguous.

    RB5-R1-001: occurrence ordinals are assigned in each file's OWN order and
    are not a cross-source correspondence - the engine pairs duplicate keys by
    similarity afterwards, so an ordinal can address a different physical row
    on each side. A postmile carrying exactly one row on both sides IS that
    row (which keeps a genuinely relabelled annotation canonicalized, so a
    real label change still reports as exactly one difference); anything else
    is resolved by CONTENT, and a group with no single matching candidate is
    left alone entirely.
    """
    if len(group) == 1 and print_group_size == 1:
        return group[0]
    candidates = [index for index in group
                  if _is_annotation_for(rows[index], label)]
    return candidates[0] if len(candidates) == 1 else None


def _target_signature(row):
    """A target row's identity apart from the suffix that moves between the
    two renders - the cells that make it THIS segment rather than another row
    listed at the same postmile."""
    return tuple(_cell(row[column])
                 for column in (_SS_CITY, _SS_HG, _SS_FT, _SS_DIST, _SS_DESC))


def _resolve_target(rows, group, print_group_size, signature):
    """This render's row index for the relation's equated postmile, or None
    when a duplicate group gives no single answer.

    A postmile carrying one row on both sides IS that row. Otherwise the
    corresponding occurrence is found the way the engine finds one - by the
    row's own content (`signature`, taken from the print's target row) - and
    only then by which row carries an equate suffix, since a render that
    already seats the marker here has named the row itself. Two candidates,
    or none, means the correspondence is unknown and the relation is left
    alone (RB5-R1-001).
    """
    if len(group) == 1 and print_group_size == 1:
        return group[0]
    matched = [index for index in group
               if _target_signature(rows[index]) == signature]
    if len(matched) == 1:
        return matched[0]
    suffixed = [index for index in group if _cell(rows[index][_SS_SUFFIX])]
    return suffixed[0] if len(suffixed) == 1 else None


def _postmile_groups(rows):
    """`{(route, physical key): [row index, ...]}` - the duplicate groups the
    engine itself later pairs by similarity. The occurrence ordinal is
    deliberately dropped: it orders rows WITHIN one file and says nothing
    about which row of the OTHER file corresponds (RB5-R1-001)."""
    groups = {}
    for index, identity in enumerate(keys_for(rows, True, SS_KEY_FIELD)):
        groups.setdefault(identity[:2], []).append(index)
    return groups


def _equate_relations(rows_print):
    """Every equate relation the PRINT declares, as (annotation postmile,
    label, target postmile or None, and the print's group size at each).

    Only the print carries the marker, so the print declares the relation and
    each render then resolves it against its OWN rows, by postmile and content
    - never by a file-order ordinal (RB5-R1-001). The target is the next row
    of the same route carrying an equate suffix, searched forward and stopping
    at the next annotation: the equated postmile is normally the very next
    line (1,112 of 1,119 statewide) but a left/right alignment branch can
    delay it (two relations, by 8 and 9 rows), and five relations print no
    suffix at all.
    """
    identities = keys_for(rows_print, True, SS_KEY_FIELD)
    groups = _postmile_groups(rows_print)
    relations = []
    for i, row in enumerate(rows_print):
        if not _is_print_annotation(row):
            continue
        target = None
        for j in range(i + 1, len(rows_print)):
            if rows_print[j][_SS_ROUTE] != row[_SS_ROUTE]:
                break
            if _cell(rows_print[j][_SS_SUFFIX]):
                target = j
                break
            if _is_print_annotation(rows_print[j]):
                break
        annotation_pm = identities[i][:2]
        target_pm = None if target is None else identities[target][:2]
        relations.append((
            annotation_pm,
            _equate_label(_cell(row[_SS_DESC])),
            target_pm,
            len(groups[annotation_pm]),
            1 if target_pm is None else len(groups[target_pm]),
            () if target is None else _target_signature(rows_print[target])))
    return relations


def _canonicalize_equates(rows, relations):
    """One render's declared equate relations reduced to the canonical form.

    Applied to BOTH renders with the SAME relation list, per side and without
    consulting the other, so nothing here can force two sides to agree:

      1. the marker - each render drops only its OWN spelling of it, keeping
         every landmark label it printed (the print's "EQUATES TO " prefix;
         the Excel export's label-less "PM EQUATION");
      2. the annotation line's HG / FT - blanked, because the print
         structurally has none there and the Excel export is repeating the
         segment's flags, which the target row still carries and still
         compares on both sides;
      3. the equate suffix - seated on the relation's TARGET row, which is
         where the print and the TSN prints put it. A render that carries no
         suffix anywhere in the relation still ends up with none, so a marker
         only ONE render carries is still reported as a difference.

    Every row is located through `_resolve_annotation` / `_resolve_target`,
    which refuse a duplicate postmile group they cannot resolve by content
    (RB5-R1-001). A relation this render does not carry, cannot resolve, or
    whose two rows BOTH carry a suffix is left untouched - the honest reading
    when the canonical row or seat is unknown. Refusing can only leave a
    difference visible; it can never invent agreement.
    """
    groups = _postmile_groups(rows)
    out = [list(row) for row in rows]
    # Every index is resolved against the ORIGINAL rows, never the partly
    # canonicalized copy, so one relation's rewrite can never move where the
    # next relation believes its rows are.
    for (annotation_pm, label, target_pm,
         print_ann, print_tgt, signature) in relations:
        index = _resolve_annotation(
            rows, groups.get(annotation_pm, ()), label, print_ann)
        if index is None:
            continue                                   # absent or ambiguous
        annotation = out[index]
        description = _cell(annotation[_SS_DESC])
        own_label = _equate_label(description)
        if own_label is not None:                      # the print's marker
            annotation[_SS_DESC] = own_label
        elif description == EQUATE_GENERIC_LABEL:      # the export's marker
            annotation[_SS_DESC] = ""
        for column in _EQUATE_ANNOTATION_FLAGS:
            annotation[column] = ""
        if target_pm is None:
            continue
        target_index = _resolve_target(
            rows, groups.get(target_pm, ()), print_tgt, signature)
        if target_index is None:
            continue
        target = out[target_index]
        annotation_suffix = _cell(annotation[_SS_SUFFIX])
        target_suffix = _cell(target[_SS_SUFFIX])
        if annotation_suffix and target_suffix:
            continue                                   # ambiguous seat
        annotation[_SS_SUFFIX] = ""
        target[_SS_SUFFIX] = annotation_suffix or target_suffix
    return out


def canonicalize_equate_pair(rows_print, rows_excel):
    """`(rows_print, rows_excel, relation_count)` with every equate relation
    the PRINT declares reduced to its canonical form on BOTH sides."""
    relations = _equate_relations(rows_print)
    return (_canonicalize_equates(rows_print, relations),
            _canonicalize_equates(rows_excel, relations),
            len(relations))


def _equate_disclosure(counter):
    """The run-resolved disclosure line for the Summary and the Notes."""
    def line():
        count = counter.get("relations")
        if count is None:
            return ""
        return (f"Equate relations normalized: {count:,}. A postmile EQUATION "
                "is one fact the two renders spell differently by design - the "
                "print writes an \"EQUATES TO <label>\" annotation line with "
                "the flags blank and the \"E\" suffix on the equated "
                "postmile; the Excel export folds the label, the flags and "
                "often the \"E\" onto the realignment record. Each render's "
                "own marker is removed, the annotation line's HG/FT are "
                "dropped (the print has none) and the relation's suffix is "
                "seated on its target row BEFORE comparing, so the spelling is "
                "not counted as a data difference. Labels, the target row's "
                "own values and a suffix only ONE render carries anywhere in "
                "the relation are still compared and still reported.")
    return line


_SS_SCHEMA = CompareSchema(
    report_name=_hsl.REPORT_NAME,
    header=SS_HEADER,
    side_a="TSMIS (PDF)",
    side_b="TSMIS (Excel)",
    id_noun="location",
    id_noun_plural="locations",
    pair_noun="postmile",
    sides_noun="renders",
    data_widths={"County": 8, "PM": 12, "PM Suffix": 10, "Description": 26},
    cmp_widths={"PM": 12, "PM Suffix": 10, "Description": 30},
    key_field=SS_KEY_FIELD,
)


class _HighwaySequenceFileCompare:
    """One Highway-Sequence file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_a`/`load_b` are the two sides'
    loaders; `tsn_claims=True` folds the normalized TSN workbook's persisted
    source claims (CMP-AUD-155) into the Notes per run."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_a, load_b,
                 base_schema, notes_title, notes_lines, tsn_claims=False,
                 one_sided_note_extra=None, same_source=False,
                 excel_side_b=False):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_a = load_a
        self._load_b = load_b
        self._excel_side_b = excel_side_b   # CMP-AUD-066 role enforcement
        self._notes_title = notes_title
        self._notes_lines = notes_lines
        self._tsn_claims = tsn_claims
        # PDF-vs-Excel self-check (owner ruling 2026-07-16, the CMP-AUD-197
        # class): decode the Excel export's OOXML escapes + drop edge tab
        # padding at load — render artifacts, not data differences. The vs-TSN
        # legs keep their oracle-exact byte semantics.
        self._same_source = same_source
        # Source Files: side A is the PDF export (.pdf); side B is the Excel export
        # (.xlsx) for the same-source self-check, else the statewide TSN (no source).
        schema = replace(base_schema, side_a=side_a, side_b=side_b,
                         legend_writer=ctc.make_notes_writer(
                             notes_title, notes_lines),
                         source_file_a=("highway_sequence", _hsl.TSMIS_SHEET, "pdf"),
                         source_file_b=(("highway_sequence", _hsl.TSMIS_SHEET, "xlsx")
                                        if same_source else ()))
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Highway_Sequence", self._name_tag)

    def _schema_for(self, path_b, run=None):
        if self._same_source and run is not None:
            # HF-06: the equate-relation count is only knowable once both
            # renders are loaded, so the disclosure is a CALLABLE resolved when
            # the Summary and the Notes sheet are written. `run` is created per
            # compare() call, so two concurrent matrix workers driving this
            # shared adapter never see each other's count.
            note = _equate_disclosure(run)
            return replace(
                self._schema, disclosure_notes=(note,),
                legend_writer=ctc.make_notes_writer(
                    self._notes_title, tuple(self._notes_lines) + (note,)))
        if not self._tsn_claims:
            return self._schema
        return _hsl._schema_with_claims(
            path_b, schema=self._schema, title=self._notes_title,
            lines=self._notes_lines)

    def _load_pair(self, path_a, path_b, run=None):
        # CMP-AUD-066: the "TSMIS (PDF)" side must carry the PDF-conversion
        # marker; a vs-Excel second side must not (the TSN side keeps its own
        # v4 normalization gate inside _load_tsn).
        ctc.require_pdf_source(path_a, self.file_a_label, "Highway Sequence")
        if self._excel_side_b:
            ctc.reject_pdf_source(path_b, self.file_b_label, "Highway Sequence")
        rows_a, _ = self._load_a(path_a)
        rows_b, _ = self._load_b(path_b)
        if self._same_source:
            rows_a = ctc.same_source_render_rows(rows_a)
            rows_b = ctc.same_source_render_rows(rows_b)
            # HF-06 / PCOA-FINAL-011: the equate relation is canonicalized
            # AFTER the render decode (so an encoded line break inside a
            # Description is already resolved) and BEFORE the engine sees the
            # rows — so the values and formulas flavors agree by construction
            # and compare_core's equality is untouched.
            rows_a, rows_b, relations = canonicalize_equate_pair(rows_a, rows_b)
            if run is not None:
                run["relations"] = relations
        return rows_a, rows_b, None

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        run = {}          # per-CALL state; these adapters are module singletons
        return run_files_compare(
            self._schema_for(path_b, run), path_a, path_b, out_path,
            banner=(f"Highway Sequence Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=True,
            loader=lambda a, b: self._load_pair(a, b, run),
            deps_ok=_hsl._DEPS_OK,
            side_a=self.file_a_label, side_b=self.file_b_label,
            events=events, confirm_overwrite=confirm_overwrite, mode=mode,
            commit_guard=commit_guard)


TSMIS_PDF_VS_TSN = _HighwaySequenceFileCompare(
    report_name="Highway Sequence — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_HighwaySequence",
    load_a=_hsl._load_tsmis, load_b=_hsl._load_tsn,
    base_schema=_hsl._SCHEMA,
    notes_title=_NOTES_PDF_VS_TSN_TITLE, notes_lines=_NOTES_PDF_VS_TSN,
    tsn_claims=True)

TSMIS_PDF_VS_EXCEL = _HighwaySequenceFileCompare(
    report_name="Highway Sequence — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_HighwaySequence",
    load_a=_load_tsmis_same_source, load_b=_load_tsmis_same_source,
    base_schema=_SS_SCHEMA,
    notes_title=_NOTES_PDF_VS_EXCEL_TITLE, notes_lines=_NOTES_PDF_VS_EXCEL,
    one_sided_note_extra=(" (a row genuinely present in only one render — the "
                          "by-design equate suffix moves now pair up and surface "
                          "as PM Suffix cells, see Notes)"),
    same_source=True, excel_side_b=True)

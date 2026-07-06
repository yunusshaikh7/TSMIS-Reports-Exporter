"""The ONE source of truth for report metadata + the app's report-module references.

Owns report/capability metadata ONLY — each report's display labels, formats, output
subdir, and the export / consolidate / compare / TSN-library module references it
uses. It deliberately does NOT own:
  * packaging reachability — `build/check_app_modules.py` + the frozen `--self-test`
    gate are the independent packaging contract (R1-B05/D02);
  * any test oracle — the fake-site fixtures + approved snapshots stay independent
    (R1-D05/R13), and `build/check_report_catalog.py` compares this catalog to a
    FROZEN v0.17 baseline rather than deriving its expectations from here.

`reports.py` and `tsn_library.py` DERIVE their registry views from this module, and
the GUI mock's report lists are checked against it — so a report's metadata lives in
exactly one place (closing the "add a report = edit N files" drift; the console
`.bat` menu now has a parity check too). The golden-equivalence check proves the
derived EXPORT / CONSOLIDATE / COMPARE lists + stable keys equal the v0.17 baseline,
so this consolidation is behavior-neutral.

Console-free: importing the catalog never launches a browser or does application
runtime I/O. It is **not** dependency-light, though — it eagerly imports the
`export_*` / `consolidate_*` / `compare_*` implementation modules (so a frozen build
collects them and they stay reachable), which transitively pulls openpyxl / pdfplumber
/ playwright, exactly as the literal registry it replaces always did. The TSN builders
are kept as lazy ``"module:function"`` strings (resolved in `tsn_library`), so the
catalog doesn't ALSO import the `tsn_load_*` normalizers eagerly.
"""
from collections import namedtuple

from export_ramp_summary import SPEC as _RAMP_SUMMARY_SPEC
from export_ramp_detail import SPEC as _RAMP_DETAIL_SPEC
from export_highway_sequence import SPEC as _HIGHWAY_SEQ_SPEC
from export_highway_log import SPEC as _HIGHWAY_LOG_SPEC
from export_highway_log_pdf import SPEC as _HIGHWAY_LOG_PDF_SPEC
from export_intersection_summary import SPEC as _INT_SUMMARY_SPEC
from export_intersection_detail import SPEC as _INT_DETAIL_SPEC
from export_intersection_detail_pdf import SPEC as _INT_DETAIL_PDF_SPEC
# Reserved groundwork (v0.18.1) — the coming "Highway" TSAR group; DISABLED, see below.
from export_highway_detail import SPEC as _HIGHWAY_DETAIL_SPEC
from export_highway_summary import SPEC as _HIGHWAY_SUMMARY_SPEC

import consolidate_ramp_summary as _c_ramp_summary
import consolidate_ramp_detail as _c_ramp_detail
import consolidate_highway_sequence as _c_highway_seq
import consolidate_highway_log as _c_highway_log
import consolidate_tsn_highway_log as _c_tsn_highway_log
import consolidate_tsmis_highway_log_pdf as _c_tsmis_highway_log_pdf
import consolidate_intersection_detail as _c_int_detail
import consolidate_tsmis_intersection_detail_pdf as _c_tsmis_int_detail_pdf
import consolidate_intersection_summary as _c_int_summary

import compare_env as _cmp_env
import compare_highway_log as _cmp_highway_log
import compare_highway_log_pdf as _cmp_highway_log_pdf
import compare_intersection_detail_pdf as _cmp_int_detail_pdf
import compare_ramp_detail_tsn as _cmp_ramp_detail_tsn
import compare_ramp_summary_tsn as _cmp_ramp_summary_tsn
import compare_intersection_summary_tsn as _cmp_int_summary_tsn
import compare_intersection_detail_tsn as _cmp_int_detail_tsn
import compare_highway_sequence_tsn as _cmp_highway_seq_tsn

# Per-tier descriptors. `key` is the stable export/consolidation/comparison-op key
# (P3 / §C.5); the rest is display + the module/adapter the op runs.
# `group` / `short_label` are report-PICKER display metadata (P-D, v0.18.1): the
# family a report nests under (Ramp / Intersection / Highway) and the leaf label
# shown under that header, or None for a flat top-level report shown by its full
# label. Display-only — the stable key, EXPORT order, and the matrix/consolidate/
# compare derivations are unaffected.
ExportEntry = namedtuple("ExportEntry", "key label fmt spec group short_label",
                         defaults=(None, None))
ConsolidateEntry = namedtuple("ConsolidateEntry", "key label module")
CompareEntry = namedtuple("CompareEntry", "key label adapter kind group")
# normalization_version: bump WHENEVER a report's TSN normalizer/parser changes
# behavior. The library stores ALREADY-NORMALIZED values, so an old build must
# read as stale and auto-rebuild from raw (D2) — a silent mismatch shipped wrong
# comparison numbers twice (v0.17.6, v0.18.3).
TsnEntry = namedtuple(
    "TsnEntry",
    "subdir label raw_glob raw_kind consolidated_name builder normalization_version",
    defaults=(1,))

# ----------------------------------------------------------------------------- #
# The authoritative, ORDERED report metadata. Order == display order (the GUI
# tabs + the console menu); the stable key is the persistence/selection contract.
# ----------------------------------------------------------------------------- #

# Export tab / multi-export. The export-op key == the report-FAMILY key == the
# spec's output `subdir` (asserted below).
EXPORT = (
    ExportEntry("ramp_summary", "TSAR: Ramp Summary", "PDF", _RAMP_SUMMARY_SPEC,
                group="Ramp", short_label="Summary"),
    ExportEntry("ramp_detail", "TSAR: Ramp Detail", "Excel", _RAMP_DETAIL_SPEC,
                group="Ramp", short_label="Detail"),
    ExportEntry("highway_sequence", "Highway Sequence Listing", "Excel", _HIGHWAY_SEQ_SPEC),
    ExportEntry("highway_log", "Highway Log", "Excel", _HIGHWAY_LOG_SPEC),
    # Same "Highway Log" dropdown option, saved as a PDF via the page's Print layout
    # (hl_printAll) instead of the Excel Export button. Export-only (the consolidator
    # reads the .xlsx export; no consolidation for the PDF).
    ExportEntry("highway_log_pdf", "Highway Log (PDF)", "PDF", _HIGHWAY_LOG_PDF_SPEC),
    # Intersection Summary/Detail consolidate AND compare (cross-env + vs-TSN) as of
    # v0.17.0 — live in both matrices. Labels verified against the live page source:
    # NO "TSAR:" prefix, and Summary is an Excel export like Detail.
    ExportEntry("intersection_summary", "Intersection Summary", "Excel", _INT_SUMMARY_SPEC,
                group="Intersection", short_label="Summary"),
    ExportEntry("intersection_detail", "Intersection Detail", "Excel", _INT_DETAIL_SPEC,
                group="Intersection", short_label="Detail"),
    # Same "Intersection Detail" dropdown option, saved as a PDF via the page's Print
    # layout (intd_printAll) instead of the Excel Export button — the exact parallel of
    # Highway Log (PDF). Appended LAST so the 7 existing export-op keys keep positions
    # 0–6 (the manifest-v1 integer-index compatibility contract, CR002-RM4).
    ExportEntry("intersection_detail_pdf", "Intersection Detail (PDF)", "PDF", _INT_DETAIL_PDF_SPEC,
                group="Intersection", short_label="Detail (PDF)"),
    # Reserved groundwork (v0.18.1): the coming "Highway" TSAR group (Highway Detail /
    # Summary), cs-disabled on the dev site as of 2026-06-25. Appended LAST (stable-id
    # append-only) and app-wide DISABLED (reports.DISABLED_EXPORT_SUBDIRS) — shown
    # greyed in the picker, rejected server-side, and absent from the matrices /
    # consolidate / compare (they have no adapter or consolidator yet). fmt is a
    # placeholder (Excel) until the site enables the report.
    ExportEntry("highway_detail", "Highway Detail", "Excel", _HIGHWAY_DETAIL_SPEC,
                group="Highway", short_label="Detail"),
    ExportEntry("highway_summary", "Highway Summary", "Excel", _HIGHWAY_SUMMARY_SPEC,
                group="Highway", short_label="Summary"),
)

# Consolidate tab. The three Highway Log consolidators split by source/format
# (cons:highway_log_excel / cons:highway_log_pdf / cons:tsn_highway_log), TSMIS
# before TSN; the rest are cons:<family>. Each module exposes consolidate(...) +
# input_dir_for(day) / out_path_for(day).
CONSOLIDATE = (
    ConsolidateEntry("cons:ramp_summary", "TSAR: Ramp Summary", _c_ramp_summary),
    ConsolidateEntry("cons:ramp_detail", "TSAR: Ramp Detail", _c_ramp_detail),
    ConsolidateEntry("cons:highway_sequence", "Highway Sequence Listing", _c_highway_seq),
    ConsolidateEntry("cons:intersection_summary", "Intersection Summary", _c_int_summary),
    ConsolidateEntry("cons:intersection_detail", "Intersection Detail", _c_int_detail),
    #   Input = this app's own "Intersection Detail (PDF)" export, parsed into the SAME
    #   36-column format (the print-layout substitute for the Excel export). Grouped
    #   next to its Excel sibling, like the two Highway Log consolidators below.
    ConsolidateEntry("cons:intersection_detail_pdf", "TSMIS Intersection Detail (PDF)",
                     _c_tsmis_int_detail_pdf),
    #   Input = the TSMIS "Highway Log" Excel export, output/<run>/highway_log/.
    ConsolidateEntry("cons:highway_log_excel", "TSMIS Highway Log (Excel)", _c_highway_log),
    #   Input = this app's own "Highway Log (PDF)" export, parsed into the SAME
    #   31-column format (the accurate substitute for the buggy vendor Excel).
    ConsolidateEntry("cons:highway_log_pdf", "TSMIS Highway Log (PDF)", _c_tsmis_highway_log_pdf),
    #   Input = TSN district PDFs dropped into input/tsn_highway_log/ (from OUTSIDE
    #   the app, so this one keeps an input folder + day ignored).
    ConsolidateEntry("cons:tsn_highway_log", "TSN Highway Log (PDF)", _c_tsn_highway_log),
)

# Compare tab SUB-TABS (the FIRST is the default). "env" = cross-environment,
# "tsn" = file-based TSMIS-vs-TSN. A third "vs TSN Matrix" sub-tab is appended by
# the GUI itself (not a registry comparison type).
COMPARE_GROUPS = (
    ("env", "Cross-environment"),
    ("tsn", "vs TSN"),
)

# Compare registry. `kind` is "files" (two workbooks) or "folders" (two export run
# folders); `group` names the sub-tab. The comparison-op key is composite
# cmp:<family>:<flavor>. Selection/routing resolve by that key (P3), so this order
# is only the display order — the env-folder rows first (they drive the matrix),
# then the file-based vs-TSN/self rows.
COMPARE = (
    CompareEntry("cmp:ramp_summary:env", "TSAR: Ramp Summary — between environments",
                 _cmp_env.RAMP_SUMMARY, "folders", "env"),
    CompareEntry("cmp:ramp_detail:env", "TSAR: Ramp Detail — between environments",
                 _cmp_env.RAMP_DETAIL, "folders", "env"),
    CompareEntry("cmp:highway_sequence:env", "Highway Sequence Listing — between environments",
                 _cmp_env.HIGHWAY_SEQUENCE, "folders", "env"),
    CompareEntry("cmp:highway_log:env", "Highway Log — between environments",
                 _cmp_env.HIGHWAY_LOG, "folders", "env"),
    CompareEntry("cmp:intersection_summary:env", "TSAR: Intersection Summary — between environments",
                 _cmp_env.INTERSECTION_SUMMARY, "folders", "env"),
    CompareEntry("cmp:intersection_detail:env", "TSAR: Intersection Detail — between environments",
                 _cmp_env.INTERSECTION_DETAIL, "folders", "env"),
    # Highway Log (PDF) cross-env — both sides parsed from the app's PDF export. Kept
    # LAST among the env-folders rows so the matrix row order is unchanged; its
    # distinct family `highway_log_pdf` keeps it a separate row from the Excel one.
    CompareEntry("cmp:highway_log_pdf:env", "Highway Log (PDF) — between environments",
                 _cmp_env.HIGHWAY_LOG_PDF, "folders", "env"),
    # Intersection Detail (PDF) cross-env — both sides parsed from the app's PDF
    # export. Kept LAST among the env-folders rows so the existing matrix row order is
    # unchanged; its distinct family `intersection_detail_pdf` keeps it a separate row
    # from the Excel one (the exact parallel of Highway Log (PDF) above).
    CompareEntry("cmp:intersection_detail_pdf:env", "Intersection Detail (PDF) — between environments",
                 _cmp_env.INTERSECTION_DETAIL_PDF, "folders", "env"),
    # vs TSN (file-based).
    CompareEntry("cmp:highway_log:tsn", "Highway Log — TSMIS vs TSN",
                 _cmp_highway_log, "files", "tsn"),
    CompareEntry("cmp:highway_log:pdf_vs_tsn", "Highway Log — TSMIS (PDF) vs TSN (PDF)",
                 _cmp_highway_log_pdf.TSMIS_PDF_VS_TSN, "files", "tsn"),
    # TSMIS (PDF) vs TSMIS (Excel) is an internal consistency check (one system, one
    # environment), NOT a TSN comparison — so it lives under "env", not "tsn".
    CompareEntry("cmp:highway_log:pdf_vs_excel", "Highway Log — TSMIS (PDF) vs TSMIS (Excel)",
                 _cmp_highway_log_pdf.TSMIS_PDF_VS_EXCEL, "files", "env"),
    # v0.17.0 vs-TSN comparators (the reference recipe), appended at the END.
    CompareEntry("cmp:ramp_detail:tsn", "TSAR: Ramp Detail — TSMIS vs TSN",
                 _cmp_ramp_detail_tsn, "files", "tsn"),
    CompareEntry("cmp:ramp_summary:tsn", "TSAR: Ramp Summary — TSMIS vs TSN",
                 _cmp_ramp_summary_tsn, "files", "tsn"),
    CompareEntry("cmp:intersection_summary:tsn", "TSAR: Intersection Summary — TSMIS vs TSN",
                 _cmp_int_summary_tsn, "files", "tsn"),
    CompareEntry("cmp:intersection_detail:tsn", "TSAR: Intersection Detail — TSMIS vs TSN",
                 _cmp_int_detail_tsn, "files", "tsn"),
    # Intersection Detail PDF-sourced comparisons — the exact parallel of the two
    # Highway Log PDF file-rows above. PDF-vs-TSN is a vs-TSN check ("tsn"); PDF-vs-Excel
    # is an internal one-system consistency check, so it lives under "env" like HL's.
    CompareEntry("cmp:intersection_detail:pdf_vs_tsn", "Intersection Detail — TSMIS (PDF) vs TSN",
                 _cmp_int_detail_pdf.TSMIS_PDF_VS_TSN, "files", "tsn"),
    CompareEntry("cmp:intersection_detail:pdf_vs_excel", "Intersection Detail — TSMIS (PDF) vs TSMIS (Excel)",
                 _cmp_int_detail_pdf.TSMIS_PDF_VS_EXCEL, "files", "env"),
    CompareEntry("cmp:highway_sequence:tsn", "Highway Sequence Listing — TSMIS vs TSN",
                 _cmp_highway_seq_tsn, "files", "tsn"),
)

# B2 auto-consolidate: which consolidate module handles each EXPORTABLE report,
# keyed by the export ReportSpec's output subdir. Every exportable report EXCEPT
# Highway Log (PDF) (it needs a scratch converted_dir, handled specially by the
# matrix / auto-consolidate). Ordered like EXPORT for a stable map.
_AUTO_CONSOLIDATOR = (
    ("ramp_summary", _c_ramp_summary),
    ("ramp_detail", _c_ramp_detail),
    ("highway_sequence", _c_highway_seq),
    ("highway_log", _c_highway_log),
    ("intersection_summary", _c_int_summary),
    ("intersection_detail", _c_int_detail),
)

# Canonical TSN library descriptors — each report's TSN source format + the lazy
# "module:function" builder that normalizes its raw into the consolidated Excel the
# comparison reads. Builders stay strings so the catalog doesn't ALSO import the
# tsn_load_* normalizers eagerly (the consolidate_*/compare_* modules above already
# pull openpyxl/pdfplumber, so the catalog is console-free but not dependency-light).
TSN = (
    # v3: the route-token normalizer was reconciled onto pdf_table_lib.norm_route
    # (a short SUFFIXED token now pads like TSMIS: '5S' -> '005S'; over-padded
    # digits collapse). Identical on the ordinary 'n/nn/nnn[X]' tokens real
    # district PDFs print, but the route KEYS the stored library, so the bump
    # re-keys any stored library on its next use (D2 auto-rebuild).
    TsnEntry("highway_log", "TSN Highway Log", "*.pdf", "district_pdfs",
             "tsn_highway_log_consolidated.xlsx", "consolidate_tsn_highway_log:build_into", normalization_version=3),
    TsnEntry("ramp_detail", "TSN Ramp Detail", "*.xlsx", "statewide_xlsx",
             "tsn_ramp_detail_normalized.xlsx", "tsn_load_ramp_detail:build_into", normalization_version=2),
    TsnEntry("ramp_summary", "TSN Ramp Summary", "*.pdf", "statewide_pdf",
             "tsn_ramp_summary_normalized.xlsx", "tsn_load_ramp_summary:build_into", normalization_version=2),
    TsnEntry("intersection_summary", "TSN Intersection Summary", "*.pdf", "statewide_pdf",
             "tsn_intersection_summary_normalized.xlsx", "tsn_load_intersection_summary:build_into", normalization_version=2),
    TsnEntry("intersection_detail", "TSN Intersection Detail", "*.xlsx", "statewide_xlsx",
             "tsn_intersection_detail_normalized.xlsx", "tsn_load_intersection_detail:build_into", normalization_version=2),
    TsnEntry("highway_sequence", "TSN Highway Sequence", "*.pdf", "district_pdfs",
             "tsn_highway_sequence_normalized.xlsx", "consolidate_tsn_highway_sequence:build_into", normalization_version=2),
)


# ----------------------------------------------------------------------------- #
# Derived views — the exact shapes reports.py / tsn_library.py consume. Returning
# fresh lists/tuples keeps every caller's object identity (and prevents a caller
# mutating the authoritative data).
# ----------------------------------------------------------------------------- #
def export_rows():
    """`[(label, fmt, spec), ...]` — the EXPORT_REPORTS shape, in display order."""
    return [(e.label, e.fmt, e.spec) for e in EXPORT]


def export_keys():
    """`(export-op key, ...)` parallel to export_rows() (== the family subdirs)."""
    return tuple(e.key for e in EXPORT)


def export_display():
    """`{export key: (group, short_label)}` — the report-PICKER grouping metadata.
    `group` is the family a report nests under (Ramp / Intersection / Highway), or
    None for a flat top-level report (Highway Log / Highway Log (PDF) / Highway
    Sequence). `short_label` is the leaf label shown under a group header (e.g.
    "Detail"), or None to show the full label. Display-only — the stable export key,
    EXPORT order, and the matrix/consolidate/compare derivations are unaffected."""
    return {e.key: (e.group, e.short_label) for e in EXPORT}


# Report-PICKER display order (P-D): the order the Export-tab checklists render — the
# flat top-level reports first in the TSMIS SITE's order (Highway Log, its PDF, then
# Highway Sequence), then the TSAR family groups (Ramp, Intersection) in registry
# order. DISTINCT from the registry/matrix order (the matrix keeps the PDF rows last);
# every EXPORT key appears exactly once (asserted at import).
_PICKER_ORDER = (
    "highway_log", "highway_log_pdf", "highway_sequence",
    "ramp_summary", "ramp_detail",
    "intersection_summary", "intersection_detail", "intersection_detail_pdf",
    # The reserved (disabled) Highway group renders last — "coming soon", greyed.
    "highway_detail", "highway_summary",
)


def picker_order():
    """The export keys in report-PICKER display order (see `_PICKER_ORDER`)."""
    return _PICKER_ORDER


# ----------------------------------------------------------------------------- #
# W2 (v0.19.0): ONE family organization across every tab's report picker — the
# Consolidate radios and the Compare radios mirror the Export picker: flat
# top-level reports first in the SITE's order, then the family groups, each
# family's entries contiguous. Display-only: the registry orders (matrix rows,
# batch manifest, stable keys) are untouched.
# ----------------------------------------------------------------------------- #
_PICKER_FAMILY_ALIAS = {
    # The Consolidate tab's Highway Log INPUT VARIANTS all belong to the
    # highway_log family slot for ordering (their labels carry the variant), so
    # the three HL consolidators (Excel, PDF, TSN PDF) group contiguously.
    "highway_log_excel": "highway_log",
    "highway_log_pdf": "highway_log",
    "tsn_highway_log": "highway_log",
}


def _picker_family(key):
    """The EXPORT family a cons:/cmp: key belongs to for picker grouping/order
    ('cons:highway_log_excel' -> 'highway_log'; 'cmp:ramp_detail:tsn' ->
    'ramp_detail'). An unknown family sorts after every known one, flat."""
    token = key.split(":", 2)[1] if ":" in key else key
    return _PICKER_FAMILY_ALIAS.get(token, token)


def _picker_pos(key):
    fam = _picker_family(key)
    return _PICKER_ORDER.index(fam) if fam in _PICKER_ORDER else len(_PICKER_ORDER)


def consolidate_display():
    """(ordered keys, {key: (group, short_label)}) for the Consolidate tab —
    the Export picker's family order + grouping. An exact-family consolidator
    inherits the family's group/short; the Highway Log input variants stay flat
    with their full (variant-naming) labels."""
    disp = export_display()
    keys = consolidate_keys()
    order = tuple(sorted(keys, key=lambda k: (_picker_pos(k), keys.index(k))))
    meta = {}
    for k in keys:
        token = k.split(":", 2)[1]
        fam = _picker_family(k)
        g, s = disp.get(fam, (None, None))
        meta[k] = (g, s) if (token == fam and fam in disp) else (g, None)
    return order, meta


def compare_display():
    """(ordered keys, {key: family_group}) for the Compare tab's radio lists —
    the same family order/grouping WITHIN each comparison-type sub-tab. Labels
    stay full (several flavors of one family can share a sub-tab, so a family
    short would collide); the family header + order carry the organization."""
    disp = export_display()
    keys = compare_keys()
    order = tuple(sorted(keys, key=lambda k: (_picker_pos(k), keys.index(k))))
    meta = {k: disp.get(_picker_family(k), (None, None))[0] for k in keys}
    return order, meta


def consolidate_rows():
    """`[(label, module), ...]` — the CONSOLIDATE_REPORTS shape."""
    return [(c.label, c.module) for c in CONSOLIDATE]


def consolidate_keys():
    """`(consolidation-op key, ...)` parallel to consolidate_rows()."""
    return tuple(c.key for c in CONSOLIDATE)


def compare_groups():
    """`[(id, label), ...]` — the COMPARE_GROUPS shape."""
    return [tuple(g) for g in COMPARE_GROUPS]


def compare_rows():
    """`[(label, adapter, kind, group), ...]` — the COMPARE_REPORTS shape."""
    return [(c.label, c.adapter, c.kind, c.group) for c in COMPARE]


def compare_keys():
    """`(comparison-op key, ...)` parallel to compare_rows()."""
    return tuple(c.key for c in COMPARE)


def consolidator_by_subdir():
    """`{export subdir: consolidate module}` for the auto-consolidatable reports."""
    return {subdir: module for subdir, module in _AUTO_CONSOLIDATOR}


def tsn_entries():
    """The TSN library descriptors, in registration order (for tsn_library)."""
    return TSN


def consolidate_module_names():
    """The console-runnable `consolidate_*` module names referenced by the
    Consolidate tier — the set the `4. consolidate (combine reports).bat` menu must
    cover (the menu↔registry parity contract, R1-M01)."""
    return tuple(c.module.__name__ for c in CONSOLIDATE)


def tsn_builder_refs():
    """The lazy ``"module:function"`` TSN builder references (the only dynamically
    imported report modules) — for the dynamic-import resolvability check (R1-T05)."""
    return tuple(t.builder for t in TSN)


# ----------------------------------------------------------------------------- #
# Import-time integrity — the catalog's OWN invariants (a programming error if they
# trip, never user input). The golden-equivalence check separately proves the
# derived views equal the frozen v0.17 baseline.
# ----------------------------------------------------------------------------- #
def _assert_unique(name, keys, n):
    assert len(keys) == n, f"{name}: {len(keys)} entries, expected {n}"
    assert len(set(keys)) == len(keys), f"{name}: duplicate key"


_assert_unique("EXPORT", export_keys(), len(EXPORT))
_assert_unique("CONSOLIDATE", consolidate_keys(), len(CONSOLIDATE))
_assert_unique("COMPARE", compare_keys(), len(COMPARE))
# The export-op key IS the family key IS the spec's output subdir.
assert export_keys() == tuple(e.spec.subdir for e in EXPORT), "EXPORT key != spec.subdir"
# Every auto-consolidator subdir is a real exportable family.
assert {s for s, _m in _AUTO_CONSOLIDATOR} <= set(export_keys()), "auto-consolidator subdir is not an export key"
# Every export key appears in the picker order exactly once (so a new report can't be
# silently dropped from the Export-tab checklists).
assert set(_PICKER_ORDER) == set(export_keys()) and len(_PICKER_ORDER) == len(EXPORT), \
    "_PICKER_ORDER must cover every EXPORT key exactly once"

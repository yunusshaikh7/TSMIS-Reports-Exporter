"""TSN Clean Road (Highway / Intersection / Ramp) -- STAGED library slots, no
normalizer yet.

The owner delivered three TSN "clean road" extracts on 2026-07-20
(`_inbox/Cleanroad/TSN_Cleanroad_files/`, filed under
`ground-truth/TSN Clean Road 9.2025/`):

    CA HIGHWAYS 09.08.2025.xlsx        60,083 rows x 74 cols   THY_* fields
    CA INTERSECTIONS 09.03.2025.xlsx   16,626 rows x 55 cols   INX_* fields
    CA RAMPS 09.08.2025.xlsx           15,410 rows x 32 cols   RAM_* fields

These are the UNDERLYING clean-road tables, not the TSAR report projections the
existing TSN library holds. Measured fact: `CA HIGHWAYS` carries exactly the same
60,083 records as `tsn_library/highway_detail/raw/TSAR - HIGHWAY DETAIL_TSN.xlsx`
but 74 columns instead of 56 -- same record universe, more fields. So these are a
NEW library source, not a duplicate of an existing one, and they pair with the
site's new (still greyed) Clean Road report types -- see `export_clean_road.py`.

WHAT THIS MODULE IS: the reserved builder for those three library slots, so the
app creates `tsn_library/clean_highway|clean_intersection|clean_ramp/raw/` with
hint files, counts what the owner drops there, and shows the slots in
Settings -> TSN reports. It deliberately does NOT normalize anything: the target
shape is decided by the comparison these will feed, and no Clean Road report
exports from the site yet, so there is nothing to compare against. Inventing a
projection now would bake in a guess the source facts can't support.

Each builder therefore returns a typed `status="error"` ConsolidateResult naming
the state plainly, rather than writing a workbook that would read as a real
normalization. It is reached only when raw files ARE present (`tsn_library
.build_consolidated` short-circuits an empty raw/ before the builder runs).

TO INTEGRATE ONE: write its projection here (the `tsn_load_ramp_detail` /
`tsn_load_highway_detail` pattern -- `tsn_library.build_normalized` with a
`project` callback, a shared header module, and a normalization marker), bump the
slot's `normalization_version` in `report_catalog.TSN`, and add its comparator.
Console-free: returns results, never prints.
"""
from events import ConsolidateResult

# The label shown in the "not integrated yet" message, per library slot.
_LABELS = {
    "clean_highway": "Highway",
    "clean_intersection": "Intersection",
    "clean_ramp": "Ramp",
}


def _not_integrated(key):
    label = _LABELS[key]
    return ConsolidateResult(
        status="error",
        message=(
            f"TSN Clean Road {label}: the files are staged, but this report has "
            "no normalizer yet — the TSMIS site still greys the matching Clean "
            "Road report, so there is nothing to compare it against. The raw "
            "files stay where you put them and are counted here."),
    )


def build_into_highway(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Reserved: no TSN Clean Road Highway normalization exists yet."""
    return _not_integrated("clean_highway")


def build_into_intersection(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Reserved: no TSN Clean Road Intersection normalization exists yet."""
    return _not_integrated("clean_intersection")


def build_into_ramp(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Reserved: no TSN Clean Road Ramp normalization exists yet."""
    return _not_integrated("clean_ramp")

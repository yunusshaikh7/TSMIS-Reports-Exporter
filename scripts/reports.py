"""Single source of truth for the report registry.

Every report type appears here exactly once, so adding one is a one-place change
on the Python side: both the GUI (Export + Consolidate tabs, `gui_app.py`) and
the console multi-exporter (`export_multi.py`) read these lists. (The `.bat`
menus are static text and are still edited by hand — see CLAUDE.md "Adding a New
Report Type".)

Kept import-light and console-free: it only pulls in the thin `export_*`
`ReportSpec` objects and the `consolidate_*` modules, so importing it never
launches a browser or does any I/O.
"""
from export_ramp_summary import SPEC as _RAMP_SUMMARY_SPEC
from export_ramp_detail import SPEC as _RAMP_DETAIL_SPEC
from export_highway_sequence import SPEC as _HIGHWAY_SEQ_SPEC
from export_highway_log import SPEC as _HIGHWAY_LOG_SPEC

import consolidate_ramp_summary as _c_ramp_summary
import consolidate_ramp_detail as _c_ramp_detail
import consolidate_highway_sequence as _c_highway_seq
import consolidate_highway_log as _c_highway_log
import consolidate_tsn_highway_log as _c_tsn_highway_log

# Export tab / multi-export: (menu label, format hint, ReportSpec).
# Order here is the display order in the GUI and the numbering in the console menu.
EXPORT_REPORTS = [
    ("TSAR: Ramp Summary", "PDF", _RAMP_SUMMARY_SPEC),
    ("TSAR: Ramp Detail", "Excel", _RAMP_DETAIL_SPEC),
    ("Highway Sequence Listing", "Excel", _HIGHWAY_SEQ_SPEC),
    ("Highway Log", "Excel", _HIGHWAY_LOG_SPEC),
]

# Consolidate tab: (menu label, module). Same order as above. Each module
# exposes consolidate(events, confirm_overwrite, day=None) plus
# input_dir_for(day) / out_path_for(day) — paths are day-dependent now that
# exports are grouped into output/<YYYY-MM-DD>/ folders, so the registry hands
# out the module rather than a single precomputed OUT_PATH.
CONSOLIDATE_REPORTS = [
    ("TSAR: Ramp Summary", _c_ramp_summary),
    ("TSAR: Ramp Detail", _c_ramp_detail),
    ("Highway Sequence Listing", _c_highway_seq),
    ("Highway Log", _c_highway_log),
    # Input = TSN district PDFs dropped into input/tsn_highway_log (vendor
    # snapshots, not dated exports) -- the module ignores the day picker and
    # exposes INPUT_NOTE/INPUT_DIR so the GUI can point users at the folder.
    ("TSN Highway Log", _c_tsn_highway_log),
]

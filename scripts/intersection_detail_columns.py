"""The canonical 36-column Intersection Detail header — one source of truth.

This is exactly the header the site's Intersection Detail Excel export writes
(`intd_exportToExcel` in the TSMIS page source), verified against a real export.
The PDF consolidator (`consolidate_tsmis_intersection_detail_pdf`) builds its
per-route workbooks from this so they line up column-for-column with the Excel
export and the TSN side; the comparison adapters read the same list so a column
can't drift between the producers and the comparers.

Column order note: the site emits the intersecting-route pair as 'Intrte S' THEN
'Intrte Route' — the reverse of their left-to-right order in the printed PDF. The
PDF consolidator maps the two PDF cells onto these positions, so this order is the
contract both sides honor.
"""

HEADER = [
    "P", "Post Mile", "S", "Location", "Date of Record", "H/G", "City Code", "R/U",
    "INT Type", "INT Eff-Date",
    "Ctrl T", "Ctrl Type",
    "Light Eff-Date", "Light T/Y",
    "ML Eff-Date",
    "ML S/M", "ML L/C", "ML R/C", "ML T/P", "ML N/L", "ML Eff-Date",
    "Description", "Main Line Lgth",
    "Inter Eff-Date", "Inter S", "Inter L", "Inter R", "Inter T", "Inter N",
    "Int St Eff-Date",
    "Intrte S", "Intrte Route", "Intrte Post", "Intrte Mile",
    "Xing Rte", "Xing S",
]

# Index of the free-text Description column (the one the formula-injection guard and
# the wider column width key on).
DESC_IDX = HEADER.index("Description")          # 21

assert len(HEADER) == 36, "Intersection Detail header must be 36 columns"
